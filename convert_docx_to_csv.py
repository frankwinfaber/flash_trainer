"""Convert the Dutch History flashcard DOCX to a structured CSV file."""

import csv
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


def extract_paragraphs(docx_path: str) -> list[str]:
    """Extract all paragraph texts from a .docx file."""
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(docx_path) as z:
        tree = ET.parse(z.open("word/document.xml"))
    paragraphs = []
    for p in tree.findall(".//w:p", ns):
        text = "".join(r.text or "" for r in p.findall(".//w:t", ns))
        paragraphs.append(text.strip())
    return paragraphs


def parse_flashcards(paragraphs: list[str]) -> list[dict]:
    """Parse paragraphs into structured flashcard records."""
    cards = []
    # Pattern to detect numbered questions like "1. What..." or "20. Why..."
    q_pattern = re.compile(r"^\d+\.\s+(.+)")
    # Pattern to detect lecture headers like "lecture 3" or "Lecture 11"
    lecture_pattern = re.compile(r"^[Ll]ecture\s+(\d+)$")

    current_section = "Mock"
    current_mode = "mock"  # mock, multiple choice, essay
    current_lecture = ""
    i = 0

    while i < len(paragraphs):
        line = paragraphs[i]

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Detect section switches
        if line.lower() == "multiple choice":
            current_mode = "multiple_choice"
            i += 1
            continue

        if line.lower() in ("open and essay questions", "open and essay question"):
            current_mode = "essay"
            i += 1
            continue

        if line.lower() == "exam questions":
            i += 1
            continue

        if line.lower() == "mock":
            current_mode = "mock"
            current_section = "Mock"
            i += 1
            continue

        # Detect lecture headers
        lecture_match = lecture_pattern.match(line)
        if lecture_match:
            lecture_num = lecture_match.group(1)
            if current_mode == "multiple_choice":
                current_section = "Multiple Choice"
            elif current_mode == "essay":
                current_section = "Essay"
            i += 1
            continue

        # Detect a numbered question
        q_match = q_pattern.match(line)
        if q_match:
            question = q_match.group(1)

            # Collect answer lines (everything until next numbered question,
            # section header, lecture header, or empty-then-header)
            answer_lines = []
            i += 1
            while i < len(paragraphs):
                next_line = paragraphs[i]
                # Stop if we hit another numbered question
                if q_pattern.match(next_line):
                    break
                # Stop if we hit a section header
                if next_line.lower() in (
                    "multiple choice",
                    "open and essay questions",
                    "open and essay question",
                    "exam questions",
                    "mock",
                ):
                    break
                # Stop if we hit a lecture header
                if lecture_pattern.match(next_line):
                    break
                # Skip empty lines between answer and next question
                if not next_line:
                    # Peek ahead: if next non-empty is a question or header, stop
                    j = i + 1
                    while j < len(paragraphs) and not paragraphs[j]:
                        j += 1
                    if j >= len(paragraphs):
                        break
                    peek = paragraphs[j]
                    if (
                        q_pattern.match(peek)
                        or lecture_pattern.match(peek)
                        or peek.lower()
                        in (
                            "multiple choice",
                            "open and essay questions",
                            "open and essay question",
                            "exam questions",
                            "mock",
                        )
                    ):
                        break
                    # Otherwise it's a gap inside a multi-line answer, skip blank
                    i += 1
                    continue

                answer_lines.append(next_line)
                i += 1

            answer = "\n".join(answer_lines)
            cards.append(
                {"section": current_section, "question": question, "answer": answer}
            )
            continue

        # Fallback: skip unrecognized lines
        i += 1

    return cards


def main():
    docx_path = Path(__file__).parent / "data" / "Flashcard questions Dutch history.docx"
    out_path = Path(__file__).parent / "data" / "flashcards.csv"

    paragraphs = extract_paragraphs(str(docx_path))
    cards = parse_flashcards(paragraphs)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["section", "question", "answer"])
        writer.writeheader()
        writer.writerows(cards)

    print(f"Wrote {len(cards)} flashcards to {out_path}")

    # Summary by section
    sections = {}
    for card in cards:
        sections[card["section"]] = sections.get(card["section"], 0) + 1
    for section, count in sections.items():
        print(f"  {section}: {count}")


if __name__ == "__main__":
    main()
