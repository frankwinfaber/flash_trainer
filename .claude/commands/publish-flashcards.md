# Publish New Flashcards

Convert any new Word documents in `data/input/` to CSV flashcard sets, validate the app still works, then commit, push, and verify the live deployment picked them up.

## Step 1 — Find new documents

List all `.docx` files in `data/input/` and all `.csv` files in `data/`. A DOCX is **new** if no CSV in `data/` was produced from it yet.

To detect this, run:
```bash
python -c "
import glob, os
docx = {os.path.splitext(os.path.basename(f))[0].lower(): f for f in glob.glob('data/input/*.docx')}
csv  = {os.path.splitext(os.path.basename(f))[0].lower(): f for f in glob.glob('data/*.csv')}
print('DOCXs:', list(docx.keys()))
print('CSVs: ', list(csv.keys()))
"
```

Cross-reference by name similarity. If unsure whether a DOCX has been converted, inspect its content and compare with existing CSVs.

## Step 2 — Inspect each new DOCX

For each unmatched DOCX extract its paragraphs to understand the structure:

```bash
python -c "
import zipfile, xml.etree.ElementTree as ET
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with zipfile.ZipFile('data/input/FILENAME.docx') as z:
    tree = ET.parse(z.open('word/document.xml'))
paragraphs = [
    ''.join(r.text or '' for r in p.findall('.//w:t', ns)).strip()
    for p in tree.findall('.//w:p', ns)
]
for i, p in enumerate(paragraphs[:60]):
    print(f'{i:3}: {repr(p)}')
print(f'Total: {len(paragraphs)}')
"
```

Identify which format the DOCX uses:

| Format | Signs | Conversion approach |
|--------|-------|---------------------|
| **Numbered Q&A** | Lines like `1. What is...` followed by answer lines | Use the existing `parse_flashcards()` logic from `convert_docx_to_csv.py` (handles Mock / Multiple Choice / Essay sections) |
| **Term / Definition table** | Alternating: term line, definition line | Skip title + header rows, then read pairs |
| **Other** | Inspect and adapt | Parse accordingly |

## Step 3 — Convert to CSV

The CSV **must** have exactly these columns: `section`, `question`, `answer`.

- `section` — the category or topic group shown in the section picker (e.g. `"Mock"`, `"Multiple Choice"`, `"Historical Research"`, `"Early Modern"`). A single-topic doc can use one section name for all rows.
- `question` — the term or question text.
- `answer` — the definition or answer text (may be multi-line; use `\n` between lines).

Name the output file after the document, snake_cased, in `data/`. Examples:
- `Early modern flashcards.docx` → `data/early_modern_flashcards.csv`
- `Timeline Early Modern.docx` → `data/timeline_early_modern.csv`

Write and run a one-off Python conversion script inline (no need to save a permanent script file unless the user asks). Print the card count and a sample of the output for review before writing the CSV.

## Step 4 — Validate the CSV

```bash
python -c "
import pandas as pd
df = pd.read_csv('data/NEWFILE.csv')
assert list(df.columns) == ['section', 'question', 'answer'], f'Wrong columns: {df.columns.tolist()}'
assert len(df) > 0, 'Empty CSV'
assert df['question'].notna().all(), 'Null questions'
assert df['answer'].notna().all(), 'Null answers'
print(f'OK: {len(df)} cards, sections: {df[\"section\"].unique().tolist()}')
"
```

## Step 5 — Smoke-test the app

Run a quick import and discovery check (does not start the full Streamlit server):

```bash
python -c "
import glob, os
csv_files = sorted(glob.glob('data/*.csv'))
for path in csv_files:
    name = os.path.splitext(os.path.basename(path))[0]
    display = name.replace('_', ' ').replace('-', ' ').title()
    print(f'  {display} → {path}')
"
```

Also do a syntax check on the app:
```bash
python -m py_compile app.py && echo 'syntax OK'
```

If either command fails, fix the issue before continuing.

## Step 6 — Commit and push

Stage only the new CSV file(s):
```bash
git add data/<newfile>.csv
git commit -m "Add <Human-readable set name> flashcard set (<N> cards)"
git push
```

Do **not** add the Co-Authored-By trailer. Do not commit the source `.docx` files unless the user explicitly asks.

## Step 7 — Check the live app

Streamlit Cloud auto-deploys from the `main` branch. After pushing, fetch the live app to confirm it is still responding:

```
WebFetch: https://flashtrainer.streamlit.app
```

If the page returns an error or the "taking longer than normal" message, report it to the user. If it responds (login page or app content visible), report success and note that the new flashcard set will appear in the dropdown after the deploy finishes (usually within 1–2 minutes).
