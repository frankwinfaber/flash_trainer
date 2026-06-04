"""Convert 3 new Word documents to CSV flashcard sets."""

import csv
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def extract_paragraphs(docx_path):
    with zipfile.ZipFile(docx_path) as z:
        tree = ET.parse(z.open("word/document.xml"))
    return [
        "".join(r.text or "" for r in p.findall(".//w:t", NS)).strip()
        for p in tree.findall(".//w:p", NS)
    ]


def parse_mc_flashcards(paragraphs):
    """
    Modern History MC questions doc.
    Sections: Test 1 / Test 2 / Test 3
    Format: alternating question/answer lines, with occasional extra-explanation
    lines after some answers (starting with "It did", "It was", "So it", etc.).
    """
    section_pattern = re.compile(r"^[Tt]est\s+\d+$")
    EXTRA_STARTERS = (
        "It did", "It was", "Did not", "They were", "So it",
        "What is true", "Running water", "The work", "He was not",
        "It resulted", "It included", "It had", "It is not",
    )

    cards = []
    current_section = "Test 1"
    i = 2  # skip title and author

    while i < len(paragraphs):
        line = paragraphs[i]
        if not line:
            i += 1
            continue

        if section_pattern.match(line):
            current_section = line.title()
            i += 1
            continue

        # Treat this line as a question
        question = line
        i += 1

        # Skip any blank lines before answer
        while i < len(paragraphs) and not paragraphs[i]:
            i += 1
        if i >= len(paragraphs):
            break

        answer_lines = [paragraphs[i]]
        i += 1

        # Collect optional extra-explanation lines that follow the short answer
        while i < len(paragraphs):
            nxt = paragraphs[i]
            if not nxt:
                i += 1
                continue
            if section_pattern.match(nxt):
                break
            if any(nxt.startswith(s) for s in EXTRA_STARTERS):
                answer_lines.append(nxt)
                i += 1
            else:
                break

        cards.append({
            "section": current_section,
            "question": question,
            "answer": "\n".join(answer_lines),
        })

    return cards


def parse_practice_flashcards(paragraphs):
    """
    Practice Questions Modern History doc.
    Sections: Chapter 1: ..., Chapter 2: ..., etc.
    Format: clean alternating question/answer lines.
    """
    chapter_pattern = re.compile(r"^Chapter\s+\d+:", re.IGNORECASE)

    cards = []
    current_section = ""
    i = 2  # skip title and author

    while i < len(paragraphs):
        line = paragraphs[i]
        if not line:
            i += 1
            continue

        if chapter_pattern.match(line):
            current_section = line
            i += 1
            continue

        question = line
        i += 1

        while i < len(paragraphs) and not paragraphs[i]:
            i += 1
        if i >= len(paragraphs):
            break

        answer = paragraphs[i]
        i += 1

        if current_section and question and answer:
            cards.append({
                "section": current_section,
                "question": question,
                "answer": answer,
            })

    return cards


def parse_regions_flashcards(docx_path):
    """
    Regions flashcards doc.
    Uses 13 Word tables, each preceded by a paragraph with the section name.
    Table headers (row 0) are skipped; remaining rows are Q/A pairs.
    """
    HEADER_CELLS = {"question/ term", "question", "answer", "term"}
    SKIP_PARAS = {"regions flashcards set"}

    with zipfile.ZipFile(docx_path) as z:
        tree = ET.parse(z.open("word/document.xml"))
    root = tree.getroot()
    body = root.find(".//w:body", NS)

    cards = []
    current_section = "General"

    for child in body:
        tag = child.tag.split("}")[1] if "}" in child.tag else child.tag

        if tag == "p":
            text = "".join(r.text or "" for r in child.findall(".//w:t", NS)).strip()
            if text and text.lower() not in SKIP_PARAS:
                # "lectures part" → "Lectures", others capitalised as-is
                if text.lower() == "lectures part":
                    current_section = "Lectures"
                elif text.lower() == "articles":
                    # container label; next paragraph will be the actual section name
                    pass
                else:
                    current_section = text.title()

        elif tag == "tbl":
            rows = child.findall(".//w:tr", NS)
            for row in rows:
                cells = row.findall(".//w:tc", NS)
                cell_texts = [
                    "".join(r.text or "" for r in c.findall(".//w:t", NS)).strip()
                    for c in cells
                ]
                if len(cell_texts) < 2:
                    continue
                q, a = cell_texts[0], cell_texts[1]
                # Skip header rows
                if q.lower() in HEADER_CELLS or a.lower() in HEADER_CELLS:
                    continue
                if q and a:
                    cards.append({
                        "section": current_section,
                        "question": q,
                        "answer": a,
                    })

    return cards


def write_csv(cards, out_path):
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["section", "question", "answer"])
        writer.writeheader()
        writer.writerows(cards)

    sections = {}
    for card in cards:
        sections[card["section"]] = sections.get(card["section"], 0) + 1

    print(f"Wrote {len(cards)} flashcards to {out_path}")
    for section, count in sections.items():
        print(f"  {section}: {count}")


def main():
    data_dir = Path(__file__).parent / "data"
    input_dir = data_dir / "input"

    print("=== Modern History MC ===")
    mc_paras = extract_paragraphs(input_dir / "Modern History MC questions.docx")
    mc_cards = parse_mc_flashcards(mc_paras)
    write_csv(mc_cards, data_dir / "modern_history_mc.csv")

    print("\n=== Practice Questions Modern History ===")
    pq_paras = extract_paragraphs(input_dir / "Practice Questions Modern History.docx")
    pq_cards = parse_practice_flashcards(pq_paras)
    write_csv(pq_cards, data_dir / "modern_history_practice.csv")

    print("\n=== Regions Flashcards ===")
    reg_cards = parse_regions_flashcards(input_dir / "Regions flashcards set.docx")
    write_csv(reg_cards, data_dir / "regions.csv")


if __name__ == "__main__":
    main()
