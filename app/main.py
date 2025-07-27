import fitz  # PyMuPDF
import json
import os
import re


def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(.)\1{2,}", r"\1", text)  # collapse repeated chars
    return text.strip(" :–-").strip()


def get_text_blocks(page):
    blocks = page.get_text("dict")["blocks"]
    results = []

    for block in blocks:
        if "lines" not in block:
            continue

        block_text = ""
        sizes = []

        for line in block["lines"]:
            for span in line["spans"]:
                if not span.get("text").strip():
                    continue
                block_text += span["text"].strip() + " "
                sizes.append(span["size"])

        text = clean_text(block_text)
        if text and sizes:
            avg_size = sum(sizes) / len(sizes)
            y_pos = block["bbox"][1]
            results.append((text, avg_size, y_pos))

    return results


def build_title_from_first_page(doc):
    page = doc[0]
    blocks = get_text_blocks(page)
    if not blocks:
        return "Untitled Document"

    # Take the top-most non-empty block with reasonable length
    blocks.sort(key=lambda x: x[2])  # sort by Y-position
    for text, _, _ in blocks:
        if 3 <= len(text.split()) <= 12:
            return text
    return "Untitled Document"


def classify_heading(text, size):
    if len(text.split()) > 25 or not text[0].isalpha():
        return None
    if size >= 16:
        return "H1"
    elif size >= 14:
        return "H2"
    elif size >= 12:
        return "H3"
    elif size >= 10:
        return "H4"
    return None


def extract_headings(doc):
    headings = []
    seen = set()

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = get_text_blocks(page)

        for text, size, _ in blocks:
            text = clean_text(text)
            if text in seen:
                continue
            seen.add(text)

            level = classify_heading(text, size)
            if level:
                headings.append({
                    "level": level,
                    "text": text,
                    "page": page_num + 1
                })

    return headings


def process_pdf_file(pdf_path, output_path):
    doc = fitz.open(pdf_path)
    headings = extract_headings(doc)

    # Try extracting title from first page heading if possible
    title = build_title_from_first_page(doc)

    # If the extracted title is also in headings, remove it from headings
    headings = [h for h in headings if h["text"] != title]

    json_data = {
        "title": title,
        "outline": headings
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)


if __name__ == "__main__":
    input_dir = "/app/input"
    output_dir = "/app/output"

    for file in os.listdir(input_dir):
        if file.endswith(".pdf"):
            pdf_path = os.path.join(input_dir, file)
            json_path = os.path.join(output_dir, file.replace(".pdf", ".json"))
            process_pdf_file(pdf_path, json_path)
