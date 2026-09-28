import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
API = "https://openrouter.ai/api/v1/chat/completions"

def _extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"): lines = lines[1:]
        if lines and lines[-1].strip() == "```": lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for i, char in enumerate(text):
            if char != "{": continue
            try:
                obj, _ = decoder.raw_decode(text[i:])
                return obj
            except json.JSONDecodeError:
                continue
    raise RuntimeError("Model returned invalid JSON: " + text[:3000])

def generate(items):
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is missing. Check GitHub Actions secrets.")
    style = (ROOT / "config/style_guide.md").read_text(encoding="utf-8")
    system = (ROOT / "prompts/content_system.md").read_text(encoding="utf-8")
    material = "\n\n--- SOURCE ---\n".join("URL: " + x["url"] + "\nTEXT:\n" + x["text"] for x in items)
    user = ("Choose one useful AI/IT topic from the sources. Rewrite it as original Uzbek Latin Telegram content. "
            "Do not copy the source. Keep facts tied to the source. Return ONE JSON object only. "
            "No markdown fences. Required keys: status, analysis, post, image_prompt, source_url.\n\n" +
            "STYLE GUIDE:\n" + style + "\n\nSOURCE MATERIAL:\n" + material)
    payload = {"model": model, "messages": [{"role":"system","content":system},{"role":"user","content":user}], "temperature":0.7, "max_tokens":2500}
    headers = {"Authorization":"Bearer " + key, "Content-Type":"application/json", "HTTP-Referer":"https://github.com/husananorqulov7431-coder/tg-bot", "X-Title":"Uzbek AI Content Agent"}
    print("OpenRouter model:", model)
    print("OpenRouter request: starting")
    try:
        r = requests.post(API, headers=headers, json=payload, timeout=90)
    except requests.RequestException as exc:
        raise RuntimeError("OpenRouter network error: " + str(exc)) from exc
    print("OpenRouter HTTP:", r.status_code)
    if not r.ok:
        print("OpenRouter error:", r.text[:4000])
        raise RuntimeError("OpenRouter HTTP " + str(r.status_code))
    try:
        data = r.json()
    except ValueError as exc:
        raise RuntimeError("OpenRouter returned non-JSON HTTP response") from exc
    if "error" in data:
        raise RuntimeError("OpenRouter returned error: " + json.dumps(data["error"], ensure_ascii=False))
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter returned no choices: " + json.dumps(data, ensure_ascii=False)[:4000])
    message = choices[0].get("message") or {}
    text = message.get("content")
    if isinstance(text, list):
        text = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in text)
    if not text:
        raise RuntimeError("OpenRouter returned empty content: " + json.dumps(message, ensure_ascii=False)[:4000])
    result = _extract_json(text)
    if not isinstance(result, dict): raise RuntimeError("Model JSON root must be an object")
    required = ("status","analysis","post","image_prompt","source_url")
    missing = [key for key in required if key not in result]
    if missing: raise RuntimeError("Model JSON missing keys: " + ", ".join(missing))
    print("OpenRouter response: valid JSON")
    return result