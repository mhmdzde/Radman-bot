# 🔋 بات تلگرام مدیریت پروژه EV Charging

## ساختار فایل‌ها

```
ev_bot/
├── bot.py          ← کد اصلی بات
├── database.py     ← دیتابیس SQLite و توابع CRUD
├── requirements.txt
└── ev_project.db   ← (خودکار ساخته می‌شه)
```

---

## راه‌اندازی روی سرور

### ۱. نصب پیش‌نیازها
```bash
pip install -r requirements.txt
```

### ۲. ساخت بات در تلگرام
- به @BotFather پیام بده
- `/newbot` بزن و اسم و یوزرنیم انتخاب کن
- توکن رو کپی کن

### ۳. تنظیم توکن
```bash
export BOT_TOKEN="توکن_بات_خودت"
```
یا مستقیم داخل `bot.py` جایگزین کن:
```python
TOKEN = "توکن_بات_خودت"
```

### ۴. اجرا
```bash
python bot.py
```

### ۵. اجرای دائمی با systemd (لینوکس)
```ini
# /etc/systemd/system/evbot.service
[Unit]
Description=EV Project Telegram Bot
After=network.target

[Service]
WorkingDirectory=/path/to/ev_bot
ExecStart=/usr/bin/python3 bot.py
Environment=BOT_TOKEN=توکن_بات_خودت
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable evbot
sudo systemctl start evbot
```

---

## قابلیت‌های بات

| دستور | توضیح |
|-------|-------|
| `/start` | منوی اصلی |
| 📊 داشبورد | آمار کلی پروژه، فازها، اعضا |
| 📋 همه تسک‌ها | لیست کل تسک‌ها با امکان کلیک |
| 👤 تسک‌های من | تسک‌های مسئول فعلی |
| 🔴 تسک‌های فوری | فیلتر فوری |
| 🔍 فیلتر فاز | تسک‌های هر فاز |
| 🔍 فیلتر فرد | تسک‌های هر عضو |
| ➕ افزودن تسک | افزودن تسک جدید (مرحله به مرحله) |

### داخل هر تسک:
- تغییر وضعیت (باز / در جریان / انجام شده / معلق / فوری)
- ویرایش یادداشت
- ویرایش لینک مستندات
- حذف تسک

---

## جدول‌های دیتابیس

```sql
members  → اعضای تیم
phases   → فازهای پروژه
tasks    → تسک‌ها (اصلی‌ترین جدول)
meetings → جلسات و مصوبات
```
