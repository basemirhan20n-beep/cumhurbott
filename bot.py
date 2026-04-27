"""
KoopBot — Kooperatif Proje Yönetim Botu
"""

import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters,
    ContextTypes
)
import database as db

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

KOOP_SAYISI = 4  # Ekip için kaç kişi dolması gerekiyor

# ConversationHandler adımları
KOOP_KODU, KOOP_PARA = range(2)

# ──────────────────────────────────────────────────────────
#  YARDIMCI FONKSİYONLAR
# ──────────────────────────────────────────────────────────

def kullanici_kaydet(update: Update):
    u = update.effective_user
    db.kayit_et(u.id, u.username or "", u.full_name or "")

def ana_menu_butonlari():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Koop'a Katıl", callback_data="koop_katil")],
        [
            InlineKeyboardButton("👥 Bekleyenler", callback_data="bekleyen_liste"),
            InlineKeyboardButton("🏆 Ekipler",     callback_data="ekip_listesi"),
        ],
        [InlineKeyboardButton("❓ Yardım", callback_data="yardim")],
    ])

def iptal_butonu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ İptal", callback_data="iptal")]
    ])

# ──────────────────────────────────────────────────────────
#  /start
# ──────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kullanici_kaydet(update)
    isim = update.effective_user.first_name
    metin = (
        f"👋 Merhaba *{isim}*!\n\n"
        "Ben *KoopBot*'um — Kooperatif projeler için otomatik ekip kurma botuyum.\n\n"
        f"📌 *Nasıl çalışır?*\n"
        f"1️⃣ Koop kodunu gir\n"
        f"2️⃣ Ödeme miktarını gir\n"
        f"3️⃣ {KOOP_SAYISI} kişi dolunca bot otomatik ekip oluşturur ✅\n\n"
        "Aşağıdan seçim yap 👇"
    )
    await update.message.reply_text(metin, parse_mode="Markdown",
                                    reply_markup=ana_menu_butonlari())

# ──────────────────────────────────────────────────────────
#  /yardim
# ──────────────────────────────────────────────────────────

async def yardim_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    metin = (
        "📖 *Komutlar*\n\n"
        "/start — Ana menü\n"
        "/yardim — Bu mesaj\n"
        "/katil — Koop projesine katıl\n"
        "/cik — Bekleme listesinden çık\n"
        "/bekleyenler `<koop_kodu>` — Kooptaki bekleyenler\n"
        "/ekipler — Son kurulan ekipler\n\n"
        "📌 *Koop Kodu nedir?*\n"
        "Aynı projeye katılmak isteyen kişilerin ortak kullandığı kod.\n"
        "Örnek: `PROJE2024`, `KOOP-A1`"
    )
    await update.message.reply_text(metin, parse_mode="Markdown",
                                    reply_markup=ana_menu_butonlari())

# ──────────────────────────────────────────────────────────
#  /katil — ConversationHandler
# ──────────────────────────────────────────────────────────

async def katil_baslat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Adım 1: Koop kodunu sor"""
    kullanici_kaydet(update)
    # Callback query üzerinden mi yoksa komuttan mı geldi?
    if update.callback_query:
        await update.callback_query.answer()
        send = update.callback_query.message.reply_text
    else:
        send = update.message.reply_text

    await send(
        "📝 *Adım 1/2 — Koop Kodu*\n\n"
        "Katılmak istediğin koop kodunu yaz:\n"
        "_(örnek: PROJE2024)_",
        parse_mode="Markdown",
        reply_markup=iptal_butonu()
    )
    return KOOP_KODU

async def koop_kodu_al(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Adım 2: Ödeme miktarını sor"""
    kodu = update.message.text.strip().upper()
    if len(kodu) < 2:
        await update.message.reply_text("⚠️ Geçersiz kod, tekrar gir:")
        return KOOP_KODU

    ctx.user_data["koop_kodu"] = kodu
    mevcut = db.koop_bekleyenleri_getir(kodu)

    await update.message.reply_text(
        f"✅ Koop kodu: *{kodu}*\n"
        f"👥 Şu an bekliyenler: *{len(mevcut)}/{KOOP_SAYISI}*\n\n"
        "💰 *Adım 2/2 — Ödeme Miktarı*\n\n"
        "Ödeyeceğin miktarı yaz _(sadece rakam, örnek: 500)_:",
        parse_mode="Markdown",
        reply_markup=iptal_butonu()
    )
    return KOOP_PARA

async def koop_para_al(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kaydı tamamla, dolunca ekip kur"""
    metin = update.message.text.strip().replace(",", ".").replace("₺", "").replace("TL", "")
    try:
        para = float(metin)
        if para <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Geçersiz miktar. Sadece rakam gir (örnek: 500):")
        return KOOP_PARA

    koop_kodu = ctx.user_data["koop_kodu"]
    user_id   = update.effective_user.id

    # Kaydet
    db.koop_ekle(user_id, koop_kodu, para)
    bekleyenler = db.koop_bekleyenleri_getir(koop_kodu)

    kalan = KOOP_SAYISI - len(bekleyenler)

    if kalan > 0:
        await update.message.reply_text(
            f"✅ *Kayıt Tamam!*\n\n"
            f"📌 Koop Kodu: `{koop_kodu}`\n"
            f"💰 Ödeme: *{para:,.2f} ₺*\n"
            f"👥 Doluluk: *{len(bekleyenler)}/{KOOP_SAYISI}*\n"
            f"⏳ Ekip için *{kalan} kişi daha* bekleniyor...",
            parse_mode="Markdown",
            reply_markup=ana_menu_butonlari()
        )
    else:
        # ✅ DOLDU — Ekip kur!
        await ekip_kur(update, ctx, koop_kodu, bekleyenler)

    return ConversationHandler.END

async def ekip_kur(update, ctx, koop_kodu, bekleyenler):
    """4 kişi dolunca ekibi otomatik kur ve herkese bildir"""
    uyeler = [(row["user_id"], row["para"]) for row in bekleyenler]
    ekip_id = db.ekip_olustur(koop_kodu, uyeler)
    _, ekip_uyeler = db.ekip_getir(ekip_id)

    toplam = sum(u["para"] for u in ekip_uyeler)

    # Ekip kartı
    uye_satirlari = ""
    for i, u in enumerate(ekip_uyeler, 1):
        mention = f"@{u['username']}" if u["username"] else u["full_name"]
        uye_satirlari += f"  {i}. {mention} — *{u['para']:,.2f} ₺*\n"

    ekip_mesaji = (
        f"🎉 *EKİP KURULDU!*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Koop Kodu: `{koop_kodu}`\n"
        f"🆔 Ekip No: *#{ekip_id}*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👥 *Üyeler:*\n"
        f"{uye_satirlari}"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Toplam: *{toplam:,.2f} ₺*"
    )

    buton = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Ekip Detayı", callback_data=f"ekip_{ekip_id}")],
        [InlineKeyboardButton("➕ Yeni Koop", callback_data="koop_katil")],
    ])

    # Tüm ekip üyelerine bildir
    for u in ekip_uyeler:
        try:
            await ctx.bot.send_message(
                chat_id=u["user_id"],
                text=ekip_mesaji,
                parse_mode="Markdown",
                reply_markup=buton
            )
        except Exception:
            pass  # Kullanıcı bota yazmayadabilir

async def katil_iptal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "❌ İşlem iptal edildi.", reply_markup=ana_menu_butonlari()
        )
    else:
        await update.message.reply_text(
            "❌ İşlem iptal edildi.", reply_markup=ana_menu_butonlari()
        )
    return ConversationHandler.END

# ──────────────────────────────────────────────────────────
#  /cik — Bekleme listesinden çık
# ──────────────────────────────────────────────────────────

async def cik_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.koop_listeden_cikar(user_id)
    await update.message.reply_text(
        "✅ Tüm bekleme listelerinden çıkarıldın.",
        reply_markup=ana_menu_butonlari()
    )

# ──────────────────────────────────────────────────────────
#  /bekleyenler <koop_kodu>
# ──────────────────────────────────────────────────────────

async def bekleyenler_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "⚠️ Kullanım: `/bekleyenler KOOP_KODU`", parse_mode="Markdown"
        )
        return

    koop_kodu = ctx.args[0].strip().upper()
    bekleyenler = db.koop_bekleyenleri_getir(koop_kodu)

    if not bekleyenler:
        await update.message.reply_text(f"❌ `{koop_kodu}` kodunda bekleyen yok.",
                                         parse_mode="Markdown")
        return

    satirlar = ""
    for i, b in enumerate(bekleyenler, 1):
        u = db.kullanici_getir(b["user_id"])
        mention = f"@{u['username']}" if u and u["username"] else (u["full_name"] if u else str(b["user_id"]))
        satirlar += f"  {i}. {mention} — *{b['para']:,.2f} ₺*\n"

    await update.message.reply_text(
        f"👥 *{koop_kodu}* — Bekleyenler ({len(bekleyenler)}/{KOOP_SAYISI})\n\n"
        f"{satirlar}",
        parse_mode="Markdown"
    )

# ──────────────────────────────────────────────────────────
#  /ekipler
# ──────────────────────────────────────────────────────────

async def ekipler_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ekipler = db.tum_ekipler()
    if not ekipler:
        await update.message.reply_text("Henüz oluşturulmuş ekip yok.")
        return

    butonlar = []
    for e in ekipler:
        tarih = e["olusturma"][:10]
        butonlar.append([
            InlineKeyboardButton(
                f"#{e['id']} — {e['koop_kodu']} ({tarih})",
                callback_data=f"ekip_{e['id']}"
            )
        ])

    await update.message.reply_text(
        "🏆 *Son Ekipler*\n\nDetay görmek için birine tıkla:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(butonlar)
    )

# ──────────────────────────────────────────────────────────
#  CALLBACK QUERY HANDLER
# ──────────────────────────────────────────────────────────

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "yardim":
        metin = (
            "📖 *Komutlar*\n\n"
            "/start — Ana menü\n"
            "/yardim — Yardım\n"
            "/katil — Koop'a katıl\n"
            "/cik — Listeden çık\n"
            "/bekleyenler `<kod>` — Bekleyenleri gör\n"
            "/ekipler — Son ekipler\n\n"
            "📌 Aynı koop kodunu kullanan "
            f"{KOOP_SAYISI} kişi dolunca ekip otomatik kurulur."
        )
        await q.message.reply_text(metin, parse_mode="Markdown",
                                    reply_markup=ana_menu_butonlari())

    elif data == "bekleyen_liste":
        ekipler = db.tum_ekipler()
        # Tüm bekleyen koop kodlarını listele
        # Basit: kullanıcıya /bekleyenler komutu hatırlat
        await q.message.reply_text(
            "👥 Belirli bir kooptaki bekleyenleri görmek için:\n\n"
            "`/bekleyenler KOOP_KODU`\n\n"
            "_(örnek: /bekleyenler PROJE2024)_",
            parse_mode="Markdown"
        )

    elif data == "ekip_listesi":
        ekipler = db.tum_ekipler()
        if not ekipler:
            await q.message.reply_text("Henüz oluşturulmuş ekip yok.")
            return
        butonlar = []
        for e in ekipler:
            tarih = e["olusturma"][:10]
            butonlar.append([
                InlineKeyboardButton(
                    f"#{e['id']} — {e['koop_kodu']} ({tarih})",
                    callback_data=f"ekip_{e['id']}"
                )
            ])
        await q.message.reply_text(
            "🏆 *Son Ekipler*:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(butonlar)
        )

    elif data.startswith("ekip_"):
        ekip_id = int(data.split("_")[1])
        ekip, uyeler = db.ekip_getir(ekip_id)
        if not ekip:
            await q.message.reply_text("❌ Ekip bulunamadı.")
            return
        toplam = sum(u["para"] for u in uyeler)
        satirlar = ""
        for i, u in enumerate(uyeler, 1):
            mention = f"@{u['username']}" if u["username"] else u["full_name"]
            satirlar += f"  {i}. {mention} — *{u['para']:,.2f} ₺*\n"
        await q.message.reply_text(
            f"🏆 *Ekip #{ekip_id}*\n"
            f"📌 Koop Kodu: `{ekip['koop_kodu']}`\n"
            f"📅 Kurulma: {ekip['olusturma'][:16]}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👥 *Üyeler:*\n{satirlar}"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Toplam: *{toplam:,.2f} ₺*",
            parse_mode="Markdown"
        )

    elif data == "iptal":
        await q.message.reply_text("❌ İşlem iptal edildi.",
                                    reply_markup=ana_menu_butonlari())

# ──────────────────────────────────────────────────────────
#  GENEL MESAJ HANDLER
# ──────────────────────────────────────────────────────────

async def genel_mesaj(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kullanici_kaydet(update)
    await update.message.reply_text(
        "🤖 Menüden bir seçenek seç ya da /katil yazarak koop projesine katıl!",
        reply_markup=ana_menu_butonlari()
    )

# ──────────────────────────────────────────────────────────
#  ANA
# ──────────────────────────────────────────────────────────

def main():
    db.init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    # Koop katılım konuşması
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("katil", katil_baslat),
            CallbackQueryHandler(katil_baslat, pattern="^koop_katil$"),
        ],
        states={
            KOOP_KODU: [MessageHandler(filters.TEXT & ~filters.COMMAND, koop_kodu_al)],
            KOOP_PARA: [MessageHandler(filters.TEXT & ~filters.COMMAND, koop_para_al)],
        },
        fallbacks=[
            CommandHandler("iptal", katil_iptal),
            CallbackQueryHandler(katil_iptal, pattern="^iptal$"),
        ],
    )

    app.add_handler(CommandHandler("start",       start))
    app.add_handler(CommandHandler("yardim",      yardim_cmd))
    app.add_handler(CommandHandler("cik",         cik_cmd))
    app.add_handler(CommandHandler("bekleyenler", bekleyenler_cmd))
    app.add_handler(CommandHandler("ekipler",     ekipler_cmd))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, genel_mesaj))

    print("🤖 KoopBot başlatıldı...")
    app.run_polling()

if __name__ == "__main__":
    main()
