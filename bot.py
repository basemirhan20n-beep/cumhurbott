import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

active_coops = {}
coop_counter = 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Merhaba! Koop oluşturmak için bir para miktarı gir:\n\n"
        "Örnek: *100* veya *250*",
        parse_mode='Markdown'
    )

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global coop_counter
    text = update.message.text.strip().replace(',', '.').replace('₺', '').replace('$', '')

    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        return

    coop_counter += 1
    coop_id = str(coop_counter)

    active_coops[coop_id] = {
        'amount': amount,
        'members': [],
        'chat_id': update.message.chat_id,
    }

    keyboard = [[InlineKeyboardButton(
        f"🤝 Koopa Katıl ({amount:.0f}₺)  —  0/4",
        callback_data=f"join_{coop_id}"
    )]]

    await update.message.reply_text(
        f"💰 *{amount:.0f}₺ Koop Oluşturuldu!*\n\n"
        f"👥 Katılımcılar: 0/4\n\n"
        f"_4 kişi katılınca ekip otomatik kurulur._",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def join_coop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    coop_id = query.data.split('_')[1]

    if coop_id not in active_coops:
        await query.answer("❌ Bu koop artık mevcut değil!", show_alert=True)
        return

    coop = active_coops[coop_id]
    user = query.from_user

    if any(m['id'] == user.id for m in coop['members']):
        await query.answer("⚠️ Zaten bu koopa katıldın!", show_alert=True)
        return

    coop['members'].append({
        'id': user.id,
        'name': user.full_name,
    })

    count = len(coop['members'])
    amount = coop['amount']
    members_text = '\n'.join([f"{i+1}. {m['name']}" for i, m in enumerate(coop['members'])])

    if count < 4:
        keyboard = [[InlineKeyboardButton(
            f"🤝 Koopa Katıl ({amount:.0f}₺)  —  {count}/4",
            callback_data=f"join_{coop_id}"
        )]]

        await query.edit_message_text(
            f"💰 *{amount:.0f}₺ Koop*\n\n"
            f"👥 Katılımcılar: {count}/4\n"
            f"{members_text}\n\n"
            f"_{4 - count} kişi daha bekleniyor..._",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        await query.answer(f"✅ Koopa katıldın! ({count}/4)")

    else:
        members_text = '\n'.join([f"✅ {i+1}. {m['name']}" for i, m in enumerate(coop['members'])])

        await query.edit_message_text(
            f"🎉 *{amount:.0f}₺ Koop Tamamlandı!*\n\n"
            f"👥 *Ekip:*\n{members_text}\n\n"
            f"💰 *Toplam Koop:* {amount * 4:.0f}₺\n\n"
            f"🚀 Ekibiniz hazır, başarılar!",
            parse_mode='Markdown'
        )
        await query.answer("🎉 Ekip tamamlandı!")
        del active_coops[coop_id]

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount))
    app.add_handler(CallbackQueryHandler(join_coop, pattern=r'^join_'))
    print("✅ Bot başlatıldı...")
    app.run_polling()

if __name__ == '__main__':
    main()
