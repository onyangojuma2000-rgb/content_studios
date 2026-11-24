# Content Studio — AI Content Pipeline

A Flask application that turns a topic or public webpage into a structured content package:
- One 500–700 word blog post draft
- Five distinct X (Twitter) posts
- One LinkedIn post
- SEO meta description and key points

**Who it helps:** Digital marketing agencies, social media managers, content teams and small businesses.

**Technology:** Python, Flask, Claude Haiku 4.5, HTML, CSS, JavaScript, BeautifulSoup and Pytest.

## Features
- Topic input or public webpage URL extraction
- Audience and writing-tone controls
- Separate tabs for blog, X posts and LinkedIn
- Copy buttons for each content format
- Input validation, safe URL checks, request limits and useful error messages
- Retry handling for temporary AI service errors
- Rotating application logs
- Automated tests

## Run locally (Windows PowerShell)

```powershell
# 1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
python -m pip install -r requirements.txt

# 3. Create your environment file
Copy-Item .env.example .env
```

Open `.env` and add your own Anthropic API key. Never commit `.env` or share your API key.

```powershell
# 4. Start the application
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## Run tests

```powershell
python -m pytest -v
```

The tests mock the AI service; they do not consume API credits.

## Deploy to Render

- **Runtime:** Python
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT`

Add these environment variables in Render:
- `ANTHROPIC_API_KEY` — your private Anthropic API key
- `ANTHROPIC_MODEL` — `claude-haiku-4-5-20251001`
- `MAX_RETRIES` — `3`

Do not manually set `PORT` on Render; Render supplies it.

## Important usage notes
- Topic mode creates a draft from the model's existing knowledge; it does **not** perform live web research.
- URL mode extracts readable text from a public HTML webpage. Some sites block automated requests or render their content with JavaScript.
- The output is an editable first draft, not a fact-checking or publishing system. Review facts, links, brand voice and platform limits before publishing.
- Do not submit private, confidential or copyrighted material unless you have permission to use it.
- A monthly KES 5,000 service offer should specify a fair usage allowance, revision policy and whether API usage is included. It is not an automatic or guaranteed market price.

## Suggested agency service package
**KES 5,000 per month — Starter Content Package (proposed offer)**

Suggested scope: up to 8 content packages per month, each containing one blog draft, five X posts and one LinkedIn post. Includes light editing and one revision per package. Client approves all content before publication. AI API costs, live research, images, scheduling and posting are excluded unless separately agreed.

## Project structure

```text
content_pipeline/
├── app.py
├── pipeline.py
├── requirements.txt
├── .env.example
├── README.md
├── templates/
│   └── index.html
├── static/
│   ├── css/style.css
│   └── js/app.js
├── tests/
│   └── test_pipeline.py
└── logs/
```

## Portfolio summary
**What it does:** Converts a topic or webpage into a blog article and social media content.
**Who it helps:** Marketing agencies and small businesses.
**Why it matters:** Reduces repetitive drafting work and helps teams prepare content for multiple channels faster.
