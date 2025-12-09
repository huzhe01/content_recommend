"""
Parse LLM output to extract final grades for HN commenters.
"""

import re
import sys


def parse_grades(text: str) -> dict[str, str]:
    """
    Parse the "Final grades" section from LLM output.

    Expected format:
    Final grades
    - username1: A+
    - username2: B
    ...

    Returns dict mapping username -> grade
    """
    grades = {}

    # Find the "Final grades" section
    # Look for "Final grades" header (case-insensitive, may have ## markdown)
    pattern = r'(?:^|\n)(?:#+ *)?Final grades\s*\n'
    match = re.search(pattern, text, re.IGNORECASE)

    if not match:
        print("Warning: Could not find 'Final grades' section")
        return grades

    # Extract everything after the header
    grades_section = text[match.end():]

    # Parse each line that looks like "- username: grade" or "* username: grade"
    line_pattern = r'^[\-\*]\s*([^:]+):\s*([A-F][+-]?)'

    for line in grades_section.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Stop if we hit a new section (header or references)
        if line.startswith('#') or line.startswith('['):
            break

        match = re.match(line_pattern, line)
        if match:
            username = match.group(1).strip()
            grade = match.group(2).strip()
            grades[username] = grade

    return grades


def grade_to_numeric(grade: str) -> float:
    """Convert letter grade to numeric value for aggregation."""
    base = {
        'A': 4.0,
        'B': 3.0,
        'C': 2.0,
        'D': 1.0,
        'F': 0.0,
    }

    if not grade:
        return 0.0

    letter = grade[0].upper()
    modifier = grade[1] if len(grade) > 1 else ''

    value = base.get(letter, 0.0)

    if modifier == '+':
        value += 0.3
    elif modifier == '-':
        value -= 0.3

    return value


def main():
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, 'r') as f:
            text = f.read()
    else:
        # Default to output.txt
        with open('output.txt', 'r') as f:
            text = f.read()

    grades = parse_grades(text)

    if not grades:
        print("No grades found!")
        return

    print(f"Parsed {len(grades)} grades:\n")

    # Sort by grade (best first)
    sorted_grades = sorted(grades.items(), key=lambda x: grade_to_numeric(x[1]), reverse=True)

    for username, grade in sorted_grades:
        numeric = grade_to_numeric(grade)
        print(f"  {username}: {grade} ({numeric:.1f})")

    # Summary stats
    print(f"\n--- Summary ---")
    numeric_grades = [grade_to_numeric(g) for g in grades.values()]
    avg = sum(numeric_grades) / len(numeric_grades)
    print(f"Average GPA: {avg:.2f}")
    print(f"Highest: {sorted_grades[0][0]} ({sorted_grades[0][1]})")
    print(f"Lowest: {sorted_grades[-1][0]} ({sorted_grades[-1][1]})")


if __name__ == "__main__":
    main()
