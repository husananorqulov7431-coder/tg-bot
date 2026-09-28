import json
import os
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API = "https://openrouter.ai/api/v1/chat/completions"

def generate(items):
    key = os.environ["OPENROUTER_API_KEY"]
    model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    style = (ROOT / "config/style_guide.md").read_text(encoding="utf-8")
    system = (ROOT / "prompts/content_system.md").read_text(encoding="utf-8")
    material = "\n\n--- SOURCE ---\n".join(
        "URL: " + x["url"] + "\nTEXT:\n" + x["text"] for x in items
    )
    user = (
        "Choose one useful AI/IT topic from the sources. Rewrite it as original Uzbek Latin Telegram content. "
        "Do not copy the source. Keep facts tied to the source. Return JSON only with status, analysis, post, image_prompt, source_url.\n\n"
        + "STYLE GUIDE:\n" + style + "\n\nSOURCE MATERIAL:\n" + material
    )
    r = requests.post(
        API,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], "temperature": 0.7, "max_tokens": 2500},
        timeout=90,
    )
    r.raise_for_status()
    data = r.json()
    print("OpenRouter model:", data.get("model", model))
    text = data["choices"][0]["message"]["content"].strip()
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)
