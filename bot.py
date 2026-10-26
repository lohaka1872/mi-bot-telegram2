import os
import ipaddress
import asyncio
import phonenumbers
import requests

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.environ["BOT_TOKEN"]

MENU = ReplyKeyboardMarkup(
    [
        ["🌐 Consultar IP", "🖼️ Recibir fotos"],
        ["📍 Compartir ubicación", "📱 Consultar teléfono"],
    ],
    resize_keyboard=True,
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Bienvenido! Elige una opción:",
        reply_markup=MENU,
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 Foto recibida. La he recibido en este chat."
    )

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = update.message.location
    await update.message.reply_text(
        f"📍 Ubicación compartida:\n"
        f"https://maps.google.com/?q={loc.latitude},{loc.longitude}"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text.strip()

    if text == "🌐 Consultar IP":
        context.user_data["mode"] = "ip"
        await msg.reply_text("Escribe una dirección IP pública.")
        return

    if text == "🖼️ Recibir fotos":
        await msg.reply_text(
            "Envíame aquí las fotos que quieras compartir."
        )
        return

    if text == "📍 Compartir ubicación":
        await msg.reply_text(
            "Pulsa el botón de abajo para compartir tu ubicación.",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton(
                    "📍 Enviar mi ubicación",
                    request_location=True,
                )]],
                resize_keyboard=True,
            ),
        )
        return

    if text == "📱 Consultar teléfono":
        context.user_data["mode"] = "phone"
        await msg.reply_text(
            "Escribe un número colombiano con +57, por ejemplo +573001234567."
        )
        return

    mode = context.user_data.get("mode")

    if mode == "ip":
        context.user_data.pop("mode", None)
        try:
            ip = ipaddress.ip_address(text)
            if not ip.is_global:
                await msg.reply_text("Introduce una IP pública.")
                return

            data = await asyncio.to_thread(
                lambda: requests.get(
                    f"https://ipwho.is/{ip}", timeout=10
                ).json()
            )

            if not data.get("success"):
                await msg.reply_text("No se pudo consultar esa IP.")
                return

            await msg.reply_text(
                f"IP: {ip}\n"
                f"País: {data.get('country')}\n"
                f"Región: {data.get('region')}\n"
                f"Ciudad aproximada: {data.get('city')}\n"
                f"Proveedor: {data.get('connection', {}).get('isp')}\n\n"
                "La ubicación por IP es aproximada."
            )
        except Exception:
            await msg.reply_text("La IP no es válida o no se pudo consultar.")
        return

    if mode == "phone":
        context.user_data.pop("mode", None)
        try:
            if not text.startswith("+57"):
                await msg.reply_text("Solo se aceptan números con prefijo +57.")
                return

            number = phonenumbers.parse(text, None)
            await msg.reply_text(
                f"Número: {phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)}\n"
                f"País: Colombia\n"
                f"Formato válido: {phonenumbers.is_valid_number(number)}\n"
                f"Región asociada: {phonenumbers.region_code_for_number(number)}\n\n"
                "El titular, su dirección y su ubicación exacta no se obtienen con esta consulta."
            )
        except Exception:
            await msg.reply_text("No pude interpretar ese número.")
        return

    await msg.reply_text("Elige una opción del menú o escribe /start.")

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    print("Bot iniciado correctamente.")

    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
