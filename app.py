import os
import tempfile
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF
from flask import Flask, jsonify, render_template, request, send_from_directory


app = Flask(__name__)

GENERATED_ASSETS: Dict[str, str] = {}


CHAPTER_KEYWORDS: Dict[str, List[str]] = {
    "CH1 - Real Numbers": ["real number", "euclid", "fundamental theorem of arithmetic", "hcf", "lcm", "irrational"],
    "CH2 - Polynomials": ["polynomial", "zeros of polynomial", "quadratic polynomial", "cubic polynomial"],
    "CH3 - Pair of Linear Equations in Two Variables": [
        "pair of linear equations",
        "simultaneous equations",
        "two variables",
        "elimination method",
        "substitution method",
        "cross multiplication",
    ],
    "CH4 - Quadratic Equations": ["quadratic equation", "ax^2+bx+c", "discriminant", "nature of roots"],
    "CH5 - Arithmetic Progressions": ["arithmetic progression", "a.p.", "ap", "common difference", "nth term", "sum of first"],
    "CH6 - Triangles": ["similar triangles", "similarity", "basic proportionality theorem", "bpt", "pythagoras"],
    "CH7 - Coordinate Geometry": ["coordinate geometry", "distance formula", "section formula", "area of triangle"],
    "CH8 - Introduction to Trigonometry": ["trigonometry", "trigonometric ratio", "sin", "cos", "tan"],
    "CH9 - Applications of Trigonometry": ["height and distance", "angle of elevation", "angle of depression"],
    "CH10 - Circles": ["circle", "tangent", "secant", "point of contact"],
    "CH11 - Constructions": ["construction", "draw", "bisect"],
    "CH12 - Areas Related to Circles": ["area of circle", "sector", "segment", "arc length"],
    "CH13 - Surface Areas and Volumes": ["surface area", "volume", "cuboid", "cube", "cylinder", "cone", "sphere"],
    "CH14 - Statistics": ["mean", "median", "mode", "ogive", "cumulative frequency"],
    "CH15 - Probability": ["probability", "event", "favourable outcomes"],
}


def extract_pages_from_pdfs(files) -> List[Dict]:
    """
    Returns a list of page dicts:
    {
      "page_key": "pdf0_p1",
      "text": "...",
      "preview_filename": Optional[str],
    }
    """
    pages: List[Dict] = []
    for pdf_idx, f in enumerate(files):
        try:
            data = f.read()
            doc = fitz.open(stream=data, filetype="pdf")
        except Exception:
            continue

        for page_idx in range(len(doc)):
            page = doc.load_page(page_idx)
            text = page.get_text("text") or ""

            has_images = bool(page.get_images(full=True))
            has_drawings = False
            try:
                has_drawings = bool(page.get_drawings())
            except Exception:
                has_drawings = False

            pages.append(
                {
                    "page_key": f"pdf{pdf_idx}_p{page_idx+1}",
                    "pdf_index": pdf_idx,
                    "page_number": page_idx + 1,
                    "text": text,
                    "has_figure": has_images or has_drawings,
                    "preview_filename": None,
                    "doc": doc,  # keep reference for rendering later
                }
            )

    return pages


def generate_page_previews(pages: List[Dict], token: str) -> Dict[str, str]:
    """
    Generate PNG previews for pages that likely contain figures.
    Returns mapping page_key -> preview URL.
    """
    out_dir = Path(tempfile.mkdtemp(prefix="pdf_assets_"))
    GENERATED_ASSETS[token] = str(out_dir)

    page_to_url: Dict[str, str] = {}
    for p in pages:
        if not p.get("has_figure"):
            continue
        try:
            doc = p["doc"]
            page = doc.load_page(p["page_number"] - 1)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            filename = f'{p["page_key"]}.png'
            filepath = out_dir / filename
            pix.save(str(filepath))
            page_to_url[p["page_key"]] = f"/generated/{token}/{filename}"
        except Exception:
            continue
    return page_to_url


def normalize_question(q: str) -> str:
    q = q.strip()
    # Remove leading question numbers like "1.", "Q1)", "(a)", etc.
    while True:
        original = q
        for prefix in ["q.", "q)", "q:", "ques.", "question"]:
            if q.lower().startswith(prefix):
                q = q[len(prefix) :].lstrip()
        # Remove simple numeric / alpha prefixes
        if len(q) > 3 and (q[0].isdigit() or q[0].isalpha()) and q[1] in [".", ")", "]"]:
            q = q[2:].lstrip()
        if q == original:
            break
    return " ".join(q.split()).lower()


def split_into_questions(text: str) -> List[str]:
    # Heuristic: build question chunks separated by blank lines / question endings.
    candidates: List[str] = []
    buffer: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if buffer:
                chunk = " ".join(buffer).strip()
                if chunk:
                    candidates.append(chunk)
                buffer = []
            continue
        buffer.append(stripped)
        if stripped.endswith("?"):
            chunk = " ".join(buffer).strip()
            if chunk:
                candidates.append(chunk)
            buffer = []

    if buffer:
        chunk = " ".join(buffer).strip()
        if chunk:
            candidates.append(chunk)

    # Filter out very short chunks
    return [c for c in candidates if len(c.split()) >= 4]


def guess_chapter(question: str) -> str:
    q_lower = question.lower()
    best_chapter = "Uncategorized"
    best_hits = 0
    for chapter, keywords in CHAPTER_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in q_lower)
        if hits > best_hits:
            best_hits = hits
            best_chapter = chapter
    return best_chapter


def analyze_questions_with_figures(
    pages: List[Dict],
    page_preview_urls: Dict[str, str],
    top_n: int = 10,
) -> Dict[str, List[Dict]]:
    """
    Returns:
      { chapter: [ { "question": str, "figure": Optional[str] } ] }

    We still use repetition counts to decide "most repeated",
    but we don't expose counts in the UI by default.
    """
    normalized_to_rep: Dict[str, Dict] = {}
    counts: Counter = Counter()

    for p in pages:
        for q in split_into_questions(p.get("text", "")):
            norm = normalize_question(q)
            if not norm:
                continue
            counts[norm] += 1
            if norm not in normalized_to_rep:
                normalized_to_rep[norm] = {
                    "question": q.strip(),
                    "page_key": p["page_key"],
                    "page_number": p["page_number"],
                }

    chapter_buckets: Dict[str, List[Tuple[Dict, int]]] = defaultdict(list)
    for norm_q, freq in counts.most_common():
        rep = normalized_to_rep.get(norm_q)
        if not rep:
            continue
        chapter = guess_chapter(rep["question"])
        figure_url = page_preview_urls.get(rep["page_key"])
        chapter_buckets[chapter].append(
            (
                {
                    "question": rep["question"],
                    "figure": figure_url,
                    "page": rep["page_number"],
                },
                freq,
            )
        )

    result: Dict[str, List[Dict]] = {}
    for chapter, items in chapter_buckets.items():
        result[chapter] = [item for item, _freq in items[:top_n]]
    return result


@app.route("/")
def index():
    return render_template("index.html", chapters=list(CHAPTER_KEYWORDS.keys()))

@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory("static", "manifest.webmanifest", mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker():
    # Must be served from root for correct scope control
    return send_from_directory("static", "sw.js", mimetype="text/javascript")


@app.route("/generated/<token>/<path:filename>")
def generated(token: str, filename: str):
    base = GENERATED_ASSETS.get(token)
    if not base:
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(base, filename)


@app.route("/analyze", methods=["POST"])
def analyze():
    files = request.files.getlist("pdfs")
    if not files:
        return jsonify({"error": "Please upload at least one PDF."}), 400

    pages = extract_pages_from_pdfs(files)
    # Close docs after we’re done generating previews & extracting questions
    if not any((p.get("text") or "").strip() for p in pages):
        return jsonify({"error": "Could not extract text from the provided PDFs."}), 400

    token = uuid.uuid4().hex
    page_preview_urls = generate_page_previews(pages, token)
    chapter_data = analyze_questions_with_figures(pages, page_preview_urls)

    # Cleanup doc references (avoid keeping open file handles)
    closed = set()
    for p in pages:
        doc = p.get("doc")
        # Important: don't use truthiness on PyMuPDF Document; it calls __len__()
        # and can raise if the document has already been closed.
        if doc is None:
            continue
        doc_id = id(doc)
        if doc_id in closed:
            continue
        try:
            doc.close()
        except Exception:
            pass
        closed.add(doc_id)

    # Convert to a JSON-serializable structure
    result = {
        "token": token,
        "chapters": chapter_data,
    }
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)

