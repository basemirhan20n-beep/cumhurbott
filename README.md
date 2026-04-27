# 🤖 KoopBot

Kooperatif projeleri için otomatik ekip kurma botu.

## Kurulum

```bash
pip install -r requirements.txt
```

## Çalıştırma

```bash
python bot.py
```

## Deploy (Railway / Render / VPS)

1. Bu klasörü GitHub'a yükle
2. Railway.app veya Render.com'da yeni proje aç
3. Environment variable olarak şunu ekle:
   ```
   BOT_TOKEN=senin_token_buraya
   ```
4. Start command: `python bot.py`

## Komutlar

| Komut | Açıklama |
|---|---|
| /start | Ana menü |
| /yardim | Yardım |
| /katil | Koop projesine katıl |
| /cik | Bekleme listesinden çık |
| /bekleyenler `<kod>` | Kooptaki bekleyenler |
| /ekipler | Son kurulan ekipler |

## Nasıl Çalışır?

1. Kullanıcı `/katil` yazar
2. Koop kodunu girer (örn: `PROJE2024`)
3. Ödeme miktarını girer (örn: `500`)
4. 4 kişi dolunca bot otomatik ekip kurar ve herkese bildirim gönderir

## Dosyalar

- `bot.py` → Ana bot kodu
- `database.py` → SQLite veritabanı
- `.env` → Token (GitHub'a yükleme!)
- `requirements.txt` → Kütüphaneler
