"""
HN Time Capsule - Fetch and parse Hacker News frontpage from 10 years ago.
"""

import html
import json
import os
import re
import time
import urllib.request
import urllib.error
from html.parser import HTMLParser
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Article:
    rank: int
    title: str
    url: str
    hn_url: str
    points: int
    author: str
    comment_count: int
    item_id: str


@dataclass
class Comment:
    id: str
    author: str
    text: str
    children: list = field(default_factory=list)


class HNFrontpageParser(HTMLParser):
    """Parse HN frontpage HTML to extract article listings.

    Note: We scrape HTML because the HN API doesn't have a
    "frontpage for date X" endpoint.
    """

    def __init__(self):
        super().__init__()
        self.articles = []
        self.current_article = {}
        self.in_titleline = False
        self.in_title_link = False
        self.in_subline = False
        self.in_score = False
        self.in_user = False
        self.in_subline_links = False
        self.current_rank = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == "span" and attrs_dict.get("class") == "rank":
            self.in_titleline = True

        if tag == "span" and attrs_dict.get("class") == "titleline":
            self.in_titleline = True

        if self.in_titleline and tag == "a" and "href" in attrs_dict:
            if not self.current_article.get("title"):
                self.current_article["url"] = attrs_dict["href"]
                self.in_title_link = True

        if tag == "span" and attrs_dict.get("class") == "subline":
            self.in_subline = True

        if self.in_subline:
            if tag == "span" and attrs_dict.get("class") == "score":
                self.in_score = True
            if tag == "a" and attrs_dict.get("class") == "hnuser":
                self.in_user = True
            if tag == "a" and "href" in attrs_dict and "item?id=" in attrs_dict["href"]:
                href = attrs_dict["href"]
                item_id = href.split("item?id=")[-1]
                self.current_article["item_id"] = item_id
                self.current_article["hn_url"] = f"https://news.ycombinator.com/{href}"
                self.in_subline_links = True

    def handle_data(self, data):
        data = data.strip()
        if not data:
            return

        if self.in_title_link:
            self.current_article["title"] = data

        if self.in_score:
            try:
                self.current_article["points"] = int(data.split()[0])
            except (ValueError, IndexError):
                self.current_article["points"] = 0

        if self.in_user:
            self.current_article["author"] = data

        if self.in_subline_links:
            if "comment" in data.lower():
                try:
                    self.current_article["comment_count"] = int(data.split()[0])
                except (ValueError, IndexError):
                    self.current_article["comment_count"] = 0
            elif data.lower() == "discuss":
                self.current_article["comment_count"] = 0

        if data.endswith(".") and data[:-1].isdigit():
            self.current_rank = int(data[:-1])
            self.current_article["rank"] = self.current_rank

    def handle_endtag(self, tag):
        if tag == "a":
            self.in_title_link = False
            self.in_user = False
            self.in_subline_links = False
        if tag == "span":
            self.in_score = False
            if self.in_titleline:
                self.in_titleline = False
        if tag == "tr" and self.in_subline:
            self.in_subline = False
            if self.current_article.get("title") and self.current_article.get("item_id"):
                self.articles.append(Article(
                    rank=self.current_article.get("rank", 0),
                    title=self.current_article.get("title", ""),
                    url=self.current_article.get("url", ""),
                    hn_url=self.current_article.get("hn_url", ""),
                    points=self.current_article.get("points", 0),
                    author=self.current_article.get("author", ""),
                    comment_count=self.current_article.get("comment_count", 0),
                    item_id=self.current_article.get("item_id", ""),
                ))
            self.current_article = {}


def fetch_url(url: str, retries: int = 3) -> str:
    """Fetch URL content with retry logic."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    req = urllib.request.Request(url, headers=headers)

    for attempt in range(retries):
        try:
            if attempt > 0:
                wait_time = 2 ** attempt
                print(f"  Retry {attempt}/{retries} after {wait_time}s...")
                time.sleep(wait_time)
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 403 and attempt < retries - 1:
                continue
            raise
    raise Exception(f"Failed to fetch {url} after {retries} retries")


def clean_html_to_text(text: str) -> str:
    """Convert HN comment HTML to clean markdown-ish text."""
    text = html.unescape(text)
    text = re.sub(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', r'[\2](\1)', text)
    text = re.sub(r'<i>([^<]+)</i>', r'*\1*', text)
    text = re.sub(r'<b>([^<]+)</b>', r'**\1**', text)
    text = re.sub(r'<code>([^<]+)</code>', r'`\1`', text)
    text = re.sub(r'<pre><code>([^<]+)</code></pre>', r'\n```\n\1\n```\n', text)
    text = text.replace("<p>", "\n\n").replace("</p>", "")
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


class ArticleTextParser(HTMLParser):
    """Extract main text content from article HTML."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.in_body = False
        self.skip_tags = {'script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript', 'iframe'}
        self.skip_depth = 0
        self.in_paragraph = False

    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self.skip_depth += 1
        if tag == 'body':
            self.in_body = True
        if tag in ('p', 'div', 'article', 'section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.in_paragraph = True
        if tag == 'br':
            self.text_parts.append('\n')

    def handle_endtag(self, tag):
        if tag in self.skip_tags and self.skip_depth > 0:
            self.skip_depth -= 1
        if tag in ('p', 'div', 'article', 'section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.text_parts.append('\n\n')
            self.in_paragraph = False

    def handle_data(self, data):
        if self.skip_depth > 0:
            return
        text = data.strip()
        if text:
            self.text_parts.append(text + ' ')

    def get_text(self) -> str:
        text = ''.join(self.text_parts)
        # Clean up whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' +\n', '\n', text)
        return text.strip()


@dataclass
class ArticleContent:
    """Fetched article content."""
    text: str
    error: str | None = None
    truncated: bool = False


MAX_ARTICLE_CHARS = 15000  # ~3-4k tokens, reasonable context for LLM


def fetch_article_content(url: str) -> ArticleContent:
    """Fetch and extract text content from an article URL."""
    # Skip non-http URLs (e.g., pdfs, HN items)
    if not url.startswith(('http://', 'https://')):
        return ArticleContent(text="", error="Not a web URL")

    # Skip known problematic patterns
    if any(x in url for x in ['.pdf', 'youtube.com', 'youtu.be', 'twitter.com', 'x.com']):
        return ArticleContent(text="", error=f"Skipped URL type: {url.split('/')[2]}")

    print(f"Fetching article: {url}")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            # Check content type
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type and 'application/xhtml' not in content_type:
                return ArticleContent(text="", error=f"Not HTML: {content_type}")

            # Read with size limit (5MB)
            data = response.read(5 * 1024 * 1024)

            # Try to decode
            try:
                page_html = data.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    page_html = data.decode('latin-1')
                except UnicodeDecodeError:
                    return ArticleContent(text="", error="Failed to decode content")

        # Parse HTML to text
        page_html = html.unescape(page_html)
        parser = ArticleTextParser()
        try:
            parser.feed(page_html)
        except Exception as e:
            return ArticleContent(text="", error=f"HTML parse error: {e}")

        text = parser.get_text()

        # Check if we got meaningful content
        if len(text) < 100:
            return ArticleContent(text="", error="Article too short or failed to extract")

        # Truncate if too long
        truncated = False
        if len(text) > MAX_ARTICLE_CHARS:
            # Try to truncate at a sentence boundary
            truncate_at = text.rfind('. ', MAX_ARTICLE_CHARS - 500, MAX_ARTICLE_CHARS)
            if truncate_at == -1:
                truncate_at = MAX_ARTICLE_CHARS
            text = text[:truncate_at + 1]
            truncated = True

        return ArticleContent(text=text, truncated=truncated)

    except urllib.error.HTTPError as e:
        return ArticleContent(text="", error=f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        return ArticleContent(text="", error=f"URL error: {e.reason}")
    except TimeoutError:
        return ArticleContent(text="", error="Timeout")
    except Exception as e:
        return ArticleContent(text="", error=f"Error: {type(e).__name__}: {e}")


def fetch_frontpage(day: str) -> list[Article]:
    """Fetch HN frontpage for a specific day (YYYY-MM-DD format)."""
    url = f"https://news.ycombinator.com/front?day={day}"
    print(f"Fetching: {url}")
    page_html = fetch_url(url)
    parser = HNFrontpageParser()
    parser.feed(page_html)
    return parser.articles


def fetch_comments(item_id: str) -> list[Comment]:
    """Fetch all comments for an HN item using Algolia API (single request)."""
    url = f"https://hn.algolia.com/api/v1/items/{item_id}"
    print(f"Fetching comments via Algolia: {url}")

    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    def parse_children(children) -> list[Comment]:
        """Recursively parse nested comment structure from Algolia."""
        comments = []
        for child in children:
            if child.get("type") != "comment":
                continue
            if child.get("text") is None:  # deleted comment
                continue

            comment = Comment(
                id=str(child.get("id", "")),
                author=child.get("author") or "[deleted]",
                text=clean_html_to_text(child.get("text", "")),
                children=parse_children(child.get("children", [])),
            )
            comments.append(comment)
        return comments

    return parse_children(data.get("children", []))


def get_date_10_years_ago() -> str:
    """Get today's date minus 10 years in YYYY-MM-DD format."""
    today = date.today()
    return today.replace(year=today.year - 10).isoformat()


def print_comment_tree(comments: list[Comment], indent: int = 0):
    """Print comments in a tree structure (for debugging)."""
    for comment in comments:
        prefix = "  " * indent
        text_preview = comment.text[:100].replace("\n", " ")
        if len(comment.text) > 100:
            text_preview += "..."
        print(f"{prefix}[{comment.author}]: {text_preview}")
        if comment.children:
            print_comment_tree(comment.children, indent + 1)


def comments_to_markdown(comments: list[Comment], indent: int = 0) -> str:
    """Convert comment tree to markdown format."""
    lines = []
    for comment in comments:
        prefix = "  " * indent
        lines.append(f"{prefix}- **{comment.author}**: {comment.text}")
        if comment.children:
            lines.append(comments_to_markdown(comment.children, indent + 1))
    return "\n\n".join(lines)


PROMPT_TEMPLATE = """The following is an article that appeared on Hacker News 10 years ago, and the discussion thread.

Let's use our benefit of hindsight now:

1. What ended up happening to this topic? (research the topic briefly and write a summary)
2. Give out awards for "Most prescient" and "Most wrong" comments, considering what happened.
3. Mention any other fun or notable aspects of the article or discussion.
4. At the end, please give out grades to specific people for their comments, considering what happened.

As for the format of (4), use the header "Final grades" and follow it with simply an unordered list of people and their grades in the format of "name: grade". Here is an example:

Final grades
- speckx: A+
- tosh: A
- keepamovin: A
- bgwalter: D
- fsflover: F

Your list may contain more people of course than just this toy example. Please follow the format exactly because I will be parsing it programmatically. The idea is that I will accumulate the grades for each account to identify the accounts that were over long periods of time the most prescient or the most wrong.

---

"""


def article_to_markdown(article: Article, article_content: ArticleContent, comments: list[Comment]) -> str:
    """Convert article and comments to a markdown document with LLM prompt."""
    lines = [
        PROMPT_TEMPLATE,
        f"# {article.title}",
        "",
        "## Article Info",
        "",
        f"- **Original URL**: {article.url}",
        f"- **HN Discussion**: {article.hn_url}",
        f"- **Points**: {article.points}",
        f"- **Submitted by**: {article.author}",
        f"- **Comments**: {article.comment_count}",
        "",
    ]

    # Article content section
    lines.append("## Article Content")
    lines.append("")

    if article_content.error:
        lines.append(f"*Could not fetch article: {article_content.error}*")
    else:
        if article_content.truncated:
            lines.append(f"*Note: Article truncated to ~{MAX_ARTICLE_CHARS} characters*")
            lines.append("")
        lines.append(article_content.text)

    lines.append("")
    lines.append("## HN Discussion")
    lines.append("")
    lines.append(comments_to_markdown(comments))

    return "\n".join(lines)


def main():
    target_date = get_date_10_years_ago()
    print(f"HN Time Capsule - Looking back to {target_date}\n")

    articles = fetch_frontpage(target_date)

    print(f"Found {len(articles)} articles:\n")
    print("-" * 80)

    for article in articles:
        print(f"{article.rank:2}. {article.title}")
        print(f"    Points: {article.points} | Author: {article.author} | Comments: {article.comment_count}")
        print(f"    URL: {article.url}")
        print(f"    HN:  {article.hn_url}")
        print()

    # Demo: fetch and convert one article
    print("\n" + "=" * 80)
    print("Demo: Converting article #20 (Satoshi/Craig Wright story)")
    print("=" * 80 + "\n")

    test_article = next((a for a in articles if "Satoshi" in a.title), None)
    if test_article:
        print(f"Article: {test_article.title}")
        print(f"Item ID: {test_article.item_id}")

        # Fetch article content
        article_content = fetch_article_content(test_article.url)
        if article_content.error:
            print(f"Article fetch: {article_content.error}")
        else:
            print(f"Article fetched: {len(article_content.text)} chars" +
                  (" (truncated)" if article_content.truncated else ""))

        # Fetch comments
        comments = fetch_comments(test_article.item_id)
        print(f"Fetched {sum(1 for _ in _count_comments(comments))} comments\n")

        print("Preview (first 3 top-level comments):")
        print("-" * 40)
        print_comment_tree(comments[:3])

        # Save markdown
        markdown = article_to_markdown(test_article, article_content, comments)
        os.makedirs("output", exist_ok=True)
        filename = f"output/{test_article.item_id}.md"
        with open(filename, "w") as f:
            f.write(markdown)
        print(f"\nSaved to: {filename} ({len(markdown)} bytes)")


def _count_comments(comments: list[Comment]):
    """Generator to count all comments in tree."""
    for c in comments:
        yield c
        yield from _count_comments(c.children)


if __name__ == "__main__":
    main()
