import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
API = "https://openrouter.ai/api/v1/chat/completions"

def generate(items):
    key = os.environ["OPENROUTER_API_KEY"].strip()
    model = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()
    if not key: raise RuntimeError("OPENROUTER_API_KEY is empty")
    style = (ROOT / "config/style_guide.md").read_text(encoding="utf-8")
    system = (ROOT / "prompts/content_system.md").read_text(encoding="utf-8")
    material = "\n\n--- SOURCE ---\n".join("URL: " + x["url"] + "\nTEXT:\n" + x["text"] for x in items)
    user = ("Choose one useful AI/IT topic from the sources. Rewrite it as original Uzbek Latin Telegram content. Do not copy the source. Keep facts tied to the source. Return one JSON object only. No markdown fences. Required keys: status, analysis, post, image_prompt, source_url.\n\n" + "STYLE GUIDE:\n" + style + "\n\nSOURCE MATERIAL:\n" + material)
    payload = {"model": model, "messages": [{"role":"system","content":system},{"role":"user","content":user}], "temperature":0.7, "max_tokens":2500, "response_format":{"type":"json_object"}}
    r = requests.post(API, headers={"Authorization":"Bearer " + key,"Content-Type":"application/json","HTTP-Referer":"https://github.com/husananorqulov7431-coder/tg-bot","X-Title":"Uzbek AI Content Agent"}, json=payload, timeout=90)
    print("OpenRouter HTTP:", r.status_code)
    if not r.ok: print("OpenRouter error:", r.text[:4000]); r.raise_for_status()
    data = r.json(); print("OpenRouter model:", data.get("model", model))
    if "error" in data: raise RuntimeError("OpenRouter returned error: " + json.dumps(data["error"], ensure_ascii=False))
    choices = data.get("choices") or []
    if not choices: raise RuntimeError("OpenRouter returned no choices: " + json.dumps(data, ensure_ascii=False)[:4000])
    message = choices[0].get("message") or {}; text = message.get("content")
    if isinstance(text, list): text = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in text)
    if not text: raise RuntimeError("OpenRouter returned empty content: " + json.dumps(message, ensure_ascii=False)[:4000])
    text = text.strip().replace("```json", "", 1).replace("```", "").strip()
    try: return json.loads(text)
    except json.JSONDecodeError as exc: print("Invalid JSON from model:", text[:5000]); raise RuntimeError("Model returned invalid JSON") from exc
