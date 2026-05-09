# راهنمای شروع سریع

ربات دانلود فایل تلگرام خود را در ۵ دقیقه راه‌اندازی کنید.

## ۱. دریافت توکن ربات تلگرام

1. در تلگرام [@BotFather](https://t.me/BotFather) را جستجو کنید
2. دستور `/newbot` را ارسال کنید
3. طبق دستورالعمل‌ها ربات خود را ایجاد کنید
4. توکن ربات را کپی کنید (شبیه `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

## ۲. دریافت آیدی کاربری تلگرام خود

1. در تلگرام [@userinfobot](https://t.me/userinfobot) را جستجو کنید
2. هر پیامی به ربات ارسال کنید
3. آیدی کاربری خود را کپی کنید (فقط اعداد)

## ۳. کلون و راه‌اندازی

```bash
# به دایرکتوری پروژه‌های خود بروید
cd /path/to/telegram-file-bot

# ایجاد محیط مجازی (لینوکس/مک)
python3 -m venv venv
source venv/bin/activate

# نصب وابستگی‌ها
pip install -r requirements.txt
```

## ۴. پیکربندی

```bash
# کپی الگوی محیط
cp .env.example .env

# ویرایش فایل .env
nano .env
```

این متغیرهای مورد نیاز را تنظیم کنید:
```
TELEGRAM_BOT_TOKEN=توکن_ربات_شما
ADMIN_USER_ID=آیدی_تلگرام_شما
```

اختیاری اما توصیه می‌شود:
```
TEMP_DOWNLOAD_DIR=/path/to/downloads
LOG_FILE=/path/to/logs/bot.log
```

## ۵. تست راه‌اندازی

```bash
# اجرای اسکریپت تست
python test_setup.py
```

هر مشکلی که گزارش می‌شود را برطرف کنید.

## ۶. اجرای ربات

```bash
# شروع ربات
python bot.py
```

باید این را ببینید:
```
INFO - Starting Telegram File Download Bot...
INFO - Application started
```

## ۷. تست ربات

1. تلگرام را باز کنید و ربات خود را (با نام کاربری) جستجو کنید
2. دستور `/start` را ارسال کنید
3. یک URL دانلود برای تست ارسال کنید

URLهای نمونه برای تست:
- فایل کوچک: `https://example.com/small-file.zip`
- تصویر: `https://example.com/image.jpg`
- هر لینک دانلود مستقیم

## ۸. استقرار در VPS (اختیاری)

برای استفاده تولیدی، روی VPS خود استقرار دهید:

1. **آپلود در VPS**:
```bash
# روی ماشین محلی خود
scp -r telegram-file-bot user@your-vps-ip:/opt/
```

2. **راه‌اندازی در VPS**:
```bash
# اتصال SSH به VPS
ssh user@your-vps-ip

# مسیریابی به پروژه
cd /opt/telegram-file-bot

# اجرای راه‌اندازی
chmod +x setup.sh
./setup.sh

# پیکربندی
nano .env
```

3. **نصب به عنوان سرویس**:
```bash
# ویرایش فایل‌های سرویس
nano telegram-file-bot.service
# مسیرها و کاربر را به‌روز کنید

# نصب سرویس
sudo cp telegram-file-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram-file-bot
sudo systemctl start telegram-file-bot
```

برای دستورالعمل‌های استقرار دقیق، [DEPLOYMENT.md](DEPLOYMENT.md) را ببینید.

## مشکلات رایج

### ربات پاسخ نمی‌دهد
- توکن ربات صحیح است را بررسی کنید
- بررسی کنید که گفتگوی خود را با ربات شروع کرده‌اید (`/start`)
- لاگ‌ها را بررسی کنید: `tail -f logs/bot.log`

### شکست دانلود
- URL معتبر و قابل دسترسی است را بررسی کنید
- اتصال اینترنت VPS را بررسی کنید
- مجوزهای دایرکتوری موقت را بررسی کنید

### شکست فایل‌های بزرگ
- فضای دیسک VPS را بررسی کنید
- تایم‌اوت را در `.env` افزایش دهید
- از روش دانلود جایگزین استفاده کنید

### مشکلات مخصوص ویندوز
- از `venv\Scripts\activate` به جای `source venv/bin/activate` استفاده کنید
- از بک‌اسلش برای مسیرها در `.env` استفاده کنید
- در صورت نیاز، Command Prompt را به عنوان Administrator اجرا کنید

## دور زدن شبکه برای ایران

راه‌اندازی شما قبلاً شامل موارد زیر است:

### ابزارهای فعلی یکپارچه شده

1. **LatestReleaseMirror**: استفاده برای آینه‌سازی ریلیزهای گیت‌هاب
```bash
# روی VPS اجرا کنید
python mirror_releases.py --repo target/repo --output /opt/mirrored
```

2. **MasterDnsVPN**: ادامه استفاده برای دسترسی تلگرام
```bash
# اطمینان حاصل کنید که تونل‌سازی DNS در حال اجرا است
# ربات از طریق این اتصال کار خواهد کرد
```

3. **MasterHttpRelayVPN-RUST**: استفاده برای ترافیک HTTP در صورت نیاز
```bash
# پیکربندی ربات برای استفاده از رله
HTTP_PROXY=http://localhost:RELAY_PORT
```

## مراحل بعدی

1. **پیکربندی جایگزین گیت‌هاب** (توصیه می‌شود)
   - ایجاد توکن دسترسی شخصی گیت‌هاب
   - ایجاد ریپازیتوری خصوصی
   - افزودن به `.env`:
     ```
     GITHUB_TOKEN=توکن_گیت‌هاب_شما
     GITHUB_REPO=نام_کاربری/نام_ریپازیتوری_شما
     ```

2. **فعال‌سازی سرور HTTP** (برای فایل‌های بزرگ)
   - تنظیم در `.env`:
     ```
     ENABLE_HTTP_SERVER=True
     HTTP_SERVER_PORT=8080
     ```

3. **راه‌اندازی نظارت**
   - لاگ‌ها را به‌طور منظم بررسی کنید
   - فضای دیسک را نظارت کنید
   - چرخش لاگ را تنظیم کنید

4. **سخت‌افزار امنیتی**
   - رمز عبور قوی ادمین استفاده کنید
   - محدودیت نرخ را فعال کنید
   - فایروال را روی VPS پیکربندی کنید

## پشتیبانی

- لاگ‌ها را برای خطاها بررسی کنید
- `python test_setup.py` را برای تأیید پیکربندی اجرا کنید
- [DEPLOYMENT.md](DEPLOYMENT.md) را برای راه‌اندازی VPS مرور کنید
- [README.md](README.md) را برای مستندات دقیق بررسی کنید

## لایسنس

MIT License