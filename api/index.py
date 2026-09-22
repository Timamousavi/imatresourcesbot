import csv
import html
import io
import os
from urllib.parse import quote

import httpx
from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI(title="IMAT Study Resources Bot")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
SHEET_URL = os.getenv("GOOGLE_SHEET_CSV_URL", "")
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
API = f"https://api.telegram.org/bot{TOKEN}"
KINDS = {"book": "📚 Books", "note": "📝 Notes", "past_paper": "🧪 Past Papers"}


async def telegram(method: str, payload: dict):
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f"{API}/{method}", json=payload)
        response.raise_for_status()
        return response.json()


async def resources():
    if not SHEET_URL:
        return []
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        response = await client.get(SHEET_URL)
        response.raise_for_status()
    rows = csv.DictReader(io.StringIO(response.text.lstrip("\ufeff")))
    result = []
    for row in rows:
        row = {str(k).strip().lower(): (v or "").strip() for k, v in row.items()}
        if row.get("active", "yes").lower() in {"yes", "true", "1", "y"} and row.get("drive_url"):
            result.append(row)
    return result


def keyboard(rows):
    return {"inline_keyboard": rows}


def home_keyboard():
    return keyboard([
        [{"text": "📚 Books", "callback_data": "kind|book"}, {"text": "📝 Notes", "callback_data": "kind|note"}],
        [{"text": "🧪 Past Papers", "callback_data": "kind|past_paper"}],
    ])


def render(items, heading):
    blocks = [f"<b>{html.escape(heading)}</b>"]
    for item in items[:8]:
        title = html.escape(item.get("title") or "Untitled resource")
        meta = " • ".join(html.escape(item.get(x, "")) for x in ("subject", "topic", "year") if item.get(x))
        description = html.escape(item.get("description", ""))
        url = html.escape(item["drive_url"], quote=True)
        block = f'<b>{title}</b>\n{meta}'
        if description:
            block += f"\n{description}"
        block += f'\n<a href="{url}">Open resource ↗</a>'
        blocks.append(block)
    return "\n\n".join(blocks)


async def send(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    await telegram("sendMessage", payload)


async def handle_message(message):
    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()
    first_name = html.escape(message.get("from", {}).get("first_name", "student"))
    if text.startswith("/start"):
        await send(chat_id, f"<b>Welcome, {first_name}! 👋</b>\n\nFind trusted IMAT books, notes and past papers. Choose a category or send a search phrase.", home_keyboard())
        return
    if text.startswith("/help"):
        await send(chat_id, "<b>Commands</b>\n/start — Resource menu\n/search genetics — Search resources\n/latest — Recently added")
        return
    data = await resources()
    if text.startswith("/latest"):
        await send(chat_id, render(list(reversed(data))[:8], "Recently added"))
        return
    term = text.removeprefix("/search").strip() if text.startswith("/search") else text
    if not term:
        await send(chat_id, "Try: <code>/search cell biology</code>")
        return
    words = term.casefold().split()
    matches = [r for r in data if all(w in " ".join(r.values()).casefold() for w in words)]
    if matches:
        await send(chat_id, render(matches, f'Search results for “{term}”'))
    else:
        await send(chat_id, f'No resource found for “{html.escape(term)}”. Try a broader keyword.')


async def handle_callback(query):
    await telegram("answerCallbackQuery", {"callback_query_id": query["id"]})
    chat_id = query["message"]["chat"]["id"]
    message_id = query["message"]["message_id"]
    action = query.get("data", "")
    data = await resources()
    if action == "home":
        payload = {"chat_id": chat_id, "message_id": message_id, "text": "<b>IMAT Resources Bot</b>\nChoose a category:", "parse_mode": "HTML", "reply_markup": home_keyboard()}
    elif action.startswith("kind|"):
        kind = action.split("|", 1)[1]
        subjects = sorted({r.get("subject", "General") for r in data if r.get("type", "note").lower() == kind})
        rows = [[{"text": s, "callback_data": f"subject|{kind}|{quote(s, safe='')}"}] for s in subjects]
        rows.append([{"text": "← Main menu", "callback_data": "home"}])
        payload = {"chat_id": chat_id, "message_id": message_id, "text": f"<b>{KINDS.get(kind, kind.title())}</b>\nChoose a subject:", "parse_mode": "HTML", "reply_markup": keyboard(rows)}
    elif action.startswith("subject|"):
        from urllib.parse import unquote
        _, kind, encoded_subject = action.split("|", 2)
        subject = unquote(encoded_subject)
        matches = [r for r in data if r.get("type", "note").lower() == kind and r.get("subject", "General") == subject]
        payload = {"chat_id": chat_id, "message_id": message_id, "text": render(matches, f"{KINDS.get(kind, kind.title())} · {subject}"), "parse_mode": "HTML", "disable_web_page_preview": True, "reply_markup": keyboard([[{"text": "← Categories", "callback_data": "home"}]])}
    else:
        return
    await telegram("editMessageText", payload)


@app.get("/")
async def health():
    return {"status": "ok", "service": "IMAT Study Resources Bot"}


@app.post("/api/webhook")
async def webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    if WEBHOOK_SECRET and x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    update = await request.json()
    if "message" in update:
        await handle_message(update["message"])
    elif "callback_query" in update:
        await handle_callback(update["callback_query"])
    return {"ok": True}
