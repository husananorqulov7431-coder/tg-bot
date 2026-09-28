import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
DEFAULT_BASE_URL = "http://127.0.0.1:20128/v1"


def _extract_json(text):
    text = (text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for i, char in enumerate(text):
            if char != "{":
                continue
            try:
                obj, _ = decoder.raw_decode(text[i:])
                return obj
            except json.JSONDecodeError:
                continue
    raise RuntimeError("OmniRoute model returned invalid JSON: " + text[:3000])


def _content(message):
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("text"):
                parts.append(str(part["text"]))
            elif part:
                parts.append(str(part))
        return "".join(parts)
    return str(content) if content else ""


def generate(items):
    key = os.getenv("OMNIROUTE_API_KEY", "").strip()
    base_url = os.getenv("OMNIROUTE_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    model = os.getenv("OMNIROUTE_MODEL", "auto").strip() or "auto"
    if not key:
        raise RuntimeError("OMNIROUTE_API_KEY is missing. Add the OmniRoute endpoint key to GitHub Secrets.")

    style = (ROOT / "config/style_guide.md").read_text(encoding="utf-8")
    system = (ROOT / "prompts/content_system.md").read_text(encoding="utf-8")
    material = "\n\n--- SOURCE ---\n".join("URL: " + x["url"] + "\nTEXT:\n" + x["text"] for x in items)
    user = (
        "Choose one useful AI/IT topic from the supplied sources. "
        "Rewrite it as original Uzbek Latin Telegram content. "
        "Do not copy the source text. Keep factual claims tied to the source. "
        "Return ONE JSON object only, with no markdown fences. "
        "Required keys: status, analysis, post, image_prompt, source_url.\n\n"
        "STYLE GUIDE:\n" + style + "\n\nSOURCE MATERIAL:\n" + material
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.7,
        "max_tokens": 2500,
    }
    headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    endpoint = base_url + "/chat/completions"

    print("OmniRoute base URL:", base_url)
    print("OmniRoute model:", model)
    print("OmniRoute request: starting")
    response = None
    last_error = None

    # OmniRoute may return 502 when a routed provider temporarily fails.
    # Retry the same request before giving up.
    for attempt in range(3):
        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
        except requests.RequestException as exc:
            last_error = exc
            print(f"OmniRoute network error (attempt {attempt + 1}/3):", exc)
            continue

        print(f"OmniRoute HTTP (attempt {attempt + 1}/3):", response.status_code)
        if response.ok:
            break

        print("OmniRoute error:", response.text[:4000])
        if response.status_code not in (429, 500, 502, 503, 504):
            raise RuntimeError("OmniRoute HTTP " + str(response.status_code))

    if response is None:
        raise RuntimeError("OmniRoute network error: " + str(last_error))

    if not response.ok:
        raise RuntimeError("OmniRoute HTTP " + str(response.status_code))

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError("OmniRoute returned non-JSON response") from exc

    if "error" in data:
        raise RuntimeError("OmniRoute returned error: " + json.dumps(data["error"], ensure_ascii=False))
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("OmniRoute returned no choices: " + json.dumps(data, ensure_ascii=False)[:4000])

    message = choices[0].get("message") or {}
    text = _content(message)
    if not text:
        raise RuntimeError("OmniRoute returned empty content: " + json.dumps(message, ensure_ascii=False)[:4000])

    result = _extract_json(text)
    if not isinstance(result, dict):
        raise RuntimeError("Model JSON root must be an object")
    required = ("status", "analysis", "post", "image_prompt", "source_url")
    missing = [x for x in required if x not in result]
    if missing:
        raise RuntimeError("Model JSON missing keys: " + ", ".join(missing))
    print("OmniRoute response: valid JSON")
    return result
