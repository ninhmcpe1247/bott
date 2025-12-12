# bot.py
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "8279709205:AAH_QDH0IQTMHpcOi6BQldE8nW8Q7tC9cX4"   # <<< DÙNG TOKEN TRỰC TIẾP
DOMAIN = "http://127.0.0.1:5000"  # sửa sau nếu có backend

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Mở MiniApp", web_app=WebAppInfo(url=f"{DOMAIN}/app"))]
    ]
    await update.message.reply_text("Chào! Nhấn nút để mở ứng dụng:", reply_markup=InlineKeyboardMarkup(keyboard))

if __name__ == "__main__":
    if not TOKEN:
        print("Thiếu TOKEN!")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Bot running...")
    app.run_polling()
