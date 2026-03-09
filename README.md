<div dir="rtl">

<div align="center">

# 🚢 LOGIPORT
### نظام إدارة العمليات اللوجستية

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11-blue?logo=python)](https://python.org)
[![PySide6](https://img.shields.io/badge/UI-PySide6%20%2F%20Qt6-green)](https://doc.qt.io/qtforpython/)
[![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy%202.0-red)](https://www.sqlalchemy.org/)
[![Version](https://img.shields.io/badge/Version-1.0.0-orange)](version.py)

نظام سطح مكتب شامل لإدارة المعاملات اللوجستية — مواد، عملاء، فواتير، قوائم تعبئة

**العربية · English · Türkçe**

</div>

---

## ✨ المميزات الرئيسية

- **إدارة المعاملات** — استيراد / تصدير / ترانزيت مع ترقيم ذكي تلقائي
- **إدارة العملاء والشركات** — ملفات كاملة مع بيانات الاتصال
- **توليد المستندات** — فواتير وقوائم تعبئة بصيغ HTML و PDF
- **لوحة تحكم تحليلية** — إحصائيات فورية ورسوم بيانية
- **دعم متعدد اللغات** — عربي وإنجليزي وتركي مع دعم RTL كامل
- **نظام صلاحيات** — إدارة مستخدمين مع أدوار ومستويات وصول
- **وضع مظلم / فاتح** — ثيم احترافي مع تأثيرات زجاجية

---

## 🖥️ متطلبات التشغيل

| المتطلب | الإصدار |
|---------|---------|
| Python | 3.10 أو 3.11 |
| نظام التشغيل | Windows 10 / 11 |

---

## 🚀 التثبيت والتشغيل

```bash
# 1. انسخ المستودع
git clone https://github.com/ahmedsalih99/LOGIPORT-V1.0.0.git
cd LOGIPORT-V1.0.0

# 2. أنشئ بيئة افتراضية (اختياري لكن مُوصى به)
python -m venv venv
venv\Scripts\activate

# 3. ثبّت المكتبات
pip install -r requirements.txt

# 4. شغّل التطبيق
python main.py
```

### أول تشغيل
عند الفتح لأول مرة ستظهر **نافذة الإعداد الأولي** لإنشاء حساب المسؤول (Admin).

---

## 📄 توليد PDF

يعتمد التطبيق على **QtWebEngine** لتوليد ملفات PDF — وهو مضمَّن تلقائياً مع `PySide6` ولا يحتاج أي تثبيت إضافي.

> توليد PDF يعمل مباشرةً بعد `pip install -r requirements.txt` بدون أي خطوات إضافية.

---

## 🗂️ هيكل المشروع

```
LOGIPORT/
├── main.py              # نقطة الدخول
├── main.spec            # إعدادات PyInstaller للبناء
├── version.py           # رقم الإصدار
├── requirements.txt     # المكتبات المطلوبة
├── installer.iss        # إعدادات Inno Setup للمثبّت
├── config/              # إعدادات التطبيق والثيم
├── core/                # المنطق الأساسي (i18n، ثيم، إعدادات)
├── database/            # النماذج والـ CRUD وBootstrap
│   ├── models/
│   └── crud/
├── services/            # طبقة الخدمات (PDF، مستندات، بحث)
├── ui/                  # واجهة المستخدم (PySide6)
│   ├── dialogs/
│   ├── tabs/
│   └── widgets/
├── documents/           # builders وقوالب HTML للمستندات
│   ├── builders/
│   └/templates/
├── hooks/               # hooks لـ PyInstaller
├── utils/               # أدوات مساعدة
└── tests/               # اختبارات
```

---

## 🔧 التقنيات المستخدمة

| التقنية | الاستخدام |
|---------|-----------|
| PySide6 / Qt6 | واجهة المستخدم |
| QtWebEngine | توليد PDF (مضمَّن مع PySide6) |
| SQLAlchemy 2.0 | قاعدة البيانات ORM |
| SQLite | قاعدة البيانات |
| Jinja2 | قوالب المستندات |
| openpyxl | تصدير Excel |
| bcrypt | تشفير كلمات المرور |

---

## 📦 بيانات المستخدم

يحفظ التطبيق قاعدة البيانات والإعدادات في:
```
Windows: %APPDATA%\LOGIPORT\
```

---

## 🏗️ بناء المثبّت (للمطورين)

```bash
# 1. بناء EXE
pyinstaller main.spec

# 2. إنشاء المثبّت (يتطلب Inno Setup 6)
# افتح installer.iss في Inno Setup وانقر Build
```

---

<div align="center">
صُنع بـ ❤️ بواسطة <a href="https://github.com/ahmedsalih99">ahmedsalih99</a>
</div>

</div>