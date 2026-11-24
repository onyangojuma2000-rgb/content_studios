import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from pipeline import ContentPipeline, PipelineError, InputError

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
app.config["JSON_SORT_KEYS"] = False

log_dir = BASE_DIR / "logs"
log_dir.mkdir(exist_ok=True)
handler = RotatingFileHandler(log_dir / "app.log", maxBytes=1_000_000, backupCount=3)
handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

def get_pipeline():
    return ContentPipeline(
        api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
    )

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "content-pipeline"})

@app.post("/generate")
def generate():
    payload = request.get_json(silent=True) or request.form
    source = str(payload.get("source", "topic")).strip().lower()
    value = str(payload.get("value", "")).strip()
    audience = str(payload.get("audience", "Small business owners and general readers")).strip()
    tone = str(payload.get("tone", "Professional and engaging")).strip()

    if source not in {"topic", "url"}:
        return jsonify({"error": "Choose either Topic or URL as the input type."}), 400
    if not value:
        return jsonify({"error": "Enter a topic or a URL first."}), 400
    if len(value) > 2000:
        return jsonify({"error": "Input is too long. Keep it under 2,000 characters."}), 400
    if len(audience) > 180 or len(tone) > 100:
        return jsonify({"error": "Audience or tone is too long."}), 400

    try:
        result = get_pipeline().generate(
            source_type=source, value=value, audience=audience, tone=tone
        )
        app.logger.info("Content package generated: source=%s", source)
        return jsonify({"result": result})
    except InputError as exc:
        return jsonify({"error": str(exc)}), 400
    except PipelineError as exc:
        app.logger.warning("Generation failed: %s", exc)
        return jsonify({"error": str(exc)}), 502
    except Exception:
        app.logger.exception("Unexpected generation error")
        return jsonify({"error": "Something went wrong. Please try again."}), 500

@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "Request is too large."}), 413

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
