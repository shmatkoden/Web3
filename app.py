import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from groq import Groq

# === секрети з оточення ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
GROQ_MODEL     = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# Render автоматично підставляє свою публічну URL у цю змінну
PUBLIC_URL = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("WEBHOOK_BASE_URL")
PORT = int(os.getenv("PORT", "10000"))  # Render задає PORT сам

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise RuntimeError("Не задані TELEGRAM_TOKEN/GROQ_API_KEY у змінних середовища")

client = Groq(api_key=GROQ_API_KEY)

# === просте меню ===
KBD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("Студент"), KeyboardButton("IT-технології")],
        [KeyboardButton("Контакти"), KeyboardButton("Prompt ChatGPT")],
    ],
    resize_keyboard=True,
)

STUDENT = "Прізвище: Шматко\nГрупа: ІО-22"
IT = ("• ШІ та ML\n"
      "• Хмари (AWS, GCP, Azure)\n"
      "• Docker / Kubernetes\n"
      "• Django / FastAPI / React\n"
      "• PostgreSQL / MongoDB / Redis\n"
      "• DevOps, CI/CD")
CONTACTS = "Тел.: +380066767875\nE-mail: smatkoden@gmail.com"
HINT = "Надішліть свій запит (prompt)."

def ask_groq(prompt: str) -> str:
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "Відповідай стисло українською, по суті."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
        max_tokens=700,
    )
    return (resp.choices[0].message.content or "").strip()

# === хендлери ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Вітаю! Оберіть розділ 👇", reply_markup=KBD)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Натисніть /start і користуйтесь меню 🙂", reply_markup=KBD)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()

    if text.lower() == "студент":
        await update.message.reply_text(STUDENT, reply_markup=KBD)
    elif text.lower() == "it-технології":
        await update.message.reply_text(IT, reply_markup=KBD)
    elif text.lower() == "контакти":
        await update.message.reply_text(CONTACTS, reply_markup=KBD)
    elif text.lower() == "prompt chatgpt":
        context.user_data["gpt"] = True
        await update.message.reply_text(HINT, reply_markup=KBD)
    else:
        if context.user_data.get("gpt"):
            await update.message.reply_chat_action("typing")
            try:
                answer = ask_groq(text)
                context.user_data["gpt"] = False
                await update.message.reply_text(answer, reply_markup=KBD)
            except Exception as e:
                context.user_data["gpt"] = False
                await update.message.reply_text(f"⚠️ Помилка: {e}", reply_markup=KBD)
        else:
            await update.message.reply_text("Оберіть пункт меню ⤵️", reply_markup=KBD)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    if PUBLIC_URL:
        # Webhook-режим для Render Web Service
        webhook_url = f"{PUBLIC_URL.rstrip('/')}/{TELEGRAM_TOKEN}"
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_TOKEN,
            webhook_url=webhook_url,
            drop_pending_updates=True,
        )
    else:
        # Локально можна запускати polling
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()