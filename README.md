# xenreg — Registration Check Bot

Bot Telegram untuk ngecek apakah nomor telepon bisa daftar Telegram tanpa SMS fee.

**Cara kerja:**
- 3 container Redroid (Android emulator) berjalan paralel
- Official Telegram APK + MicroG (Google Play Services palsu)
- Deteksi otomatis: OTP_SENT, PAYMENT_REQUIRED, CALL_VERIFICATION, EMAIL_VERIFICATION, ADD_EMAIL, OTP_APP, INVALID_NUMBER

## Setup

1. Copy credential: `cp config.example.py config.py` dan isi token/API credentials
2. Jalankan: `python3 reg_bot.py`

## Dependencies
- Python 3.8+
- `telethon`, `requests`
- ADB (Android Debug Bridge)
- Docker dengan Redroid image (`redroid-gapps:11.0.0`)
