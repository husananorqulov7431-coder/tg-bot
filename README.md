# Telegram Auto Post

Daily Telegram publisher for @teleposttestuz.

## Schedule
21:30 Asia/Tashkent = 16:30 UTC.

## Sources
- https://t.me/javohir_webdev
- https://t.me/mohirdev
- https://t.me/naxalov
- https://t.me/aicreatorsuz

## Required GitHub Secret
Create repository secret:

TELEGRAM_BOT_TOKEN

The token must never be committed to the repository.

## Current status
The GitHub Actions bridge is ready. The current version collects recent public Telegram posts and sends a test-formatted digest. An AI generation layer and image generation layer require an external model/API or another connected execution service; a ChatGPT subscription itself does not expose its subscription access as an OpenAI API key for GitHub Actions.
