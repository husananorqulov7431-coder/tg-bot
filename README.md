# Telegram AI Content Agent

GitHub Actions asosidagi AI/IT Telegram kontent agenti.

## Pipeline

1. Ochiq Telegram manbalaridan oxirgi postlarni yig'adi.
2. OmniRoute orqali AI tahlil qiladi.
3. Uzbek Latin formatida original post yaratadi.
4. Quality gate orqali `PUBLISH` yoki `REJECT` qarorini oladi.
5. `PUBLISH` bo'lsa Telegram kanalga yuboradi.

## Asosiy fayllar

- `bot.py` — source collection + Telegram publishing
- `ai_engine.py` — OmniRoute API client, JSON parsing va transient retry
- `config/sources.json` — manbalar va lookback sozlamalari
- `config/style_guide.md` — brand voice
- `prompts/content_system.md` — AI system prompt
- `.github/workflows/telegram-post.yml` — asosiy publisher
- `.github/workflows/omniroute-local.yml` — OmniRoute'ni qo'lda vaqtincha ochish uchun test workflow
- `index.html` + `.github/workflows/pages.yml` — GitHub Pages mini UI

## GitHub Secrets

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_TARGET`
- `OMNIROUTE_API_KEY`

## Muhim

GitHub-hosted runner har ishga tushganda yangi muhit yaratadi. OmniRoute provider ulanishlari SQLite/data papkasida saqlanadi; faqat Endpoint API keyni secretga qo'yish provider OAuth holatini yangi runnerga ko'chirmaydi. Shuning uchun Antigravity kabi OAuth provider uchun alohida persistent OmniRoute instance yoki provider credential/data bootstrap kerak.

Legacy kodlar `archive/legacy/` ichiga ko'chirilgan va asosiy pipeline'dan chiqarilgan.
