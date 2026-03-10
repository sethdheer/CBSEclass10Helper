## Class 10 CBSE Maths Question Repeater

This project is a small web application that helps Class 10 students analyze previous year **CBSE Mathematics** question papers in PDF form and see the **most frequently repeated questions, chapter-wise**.

Students can:

- **Upload** one or more Class 10 Maths question paper PDFs
- Click a big **MATHEMATICS** button to run the analysis
- Click individual **chapter buttons** (e.g. `CH1 - Real Numbers`) to see repeated questions for that chapter

The UI is designed to be simple, clean, and friendly for Class 10 students.

---

## Tech stack

- **Backend**: Flask (Python)
- **PDF parsing + figure previews**: PyMuPDF (fits better for diagrams)
- **Frontend**: HTML + vanilla JavaScript + CSS

---

## Project structure

- `app.py` – Flask application, PDF analysis & routes
- `templates/index.html` – main UI
- `static/style.css` – styling for a modern, student-friendly look
- `requirements.txt` – Python dependencies

---

## Getting started

### 1. Create and activate a virtual environment (recommended)

From the project folder:

```bash
cd /Users/admin/Downloads/my_first_app
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the app

```bash
python app.py
```

Then open your browser and go to:

```text
http://127.0.0.1:5000/
```

---

## Install as an app (PWA)

Once the site is hosted on the internet (or running locally), students can install it:

- **Android (Chrome)**: open the site → menu → **Install app**
- **iPhone (Safari)**: open the site → Share → **Add to Home Screen**
- **Laptop (Chrome/Edge)**: open the site → install icon in address bar → **Install**

This adds the app to the home screen / desktop and opens it in an app-like window.

---

## How it works (high level)

1. **PDF upload**  
   You can select multiple PDF files using the file picker.

2. **MATHEMATICS button**  
   When you click the `MATHEMATICS` button, the app:
   - reads all the PDFs
   - extracts text from each page
   - splits the text into likely questions
   - normalizes question text (removes numbers like `1.` / `Q1)`, lowercases, etc.)
   - counts how many times each question appears

3. **Chapter detection**  
   Each question is roughly assigned to a chapter using simple **keyword matching** based on CBSE Class 10 Maths chapters (Real Numbers, Polynomials, Quadratic Equations, etc.).

4. **Results**  
   For every chapter, the app shows the **top repeated questions** (question text only).  
   If the question’s page contains a **figure/diagram**, the app also shows a **page preview image** so students can see the diagram.

> Note: The chapter detection and question splitting are heuristic-based and will not be perfect, but they give a useful starting point for spotting repeated questions.

---

## Customization ideas

- Improve question splitting rules for your specific paper format
- Fine-tune chapter keyword lists for better classification
- Add support for other subjects (e.g., Science, English) with their own main buttons and chapter lists
- Style the page with your school colors and logo

