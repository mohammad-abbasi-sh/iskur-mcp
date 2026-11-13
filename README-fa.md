# iskur-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/iskur-mcp

سرور MCP غیررسمی و **فقط‌خواندنی** برای İŞKUR (سازمان کاریابی ترکیه، iskur.gov.tr). جست‌وجو در آگهی‌های شغلی آزاد از پورتال esube (کلیدواژه، شهر، بازهٔ زمانی، نوع کار، تحصیلات، صفحه‌بندی)، دریافت جزئیات یک آگهی (توضیحات، مهارت‌های موردنیاز، شغل، تجربه، تحصیلات)، فهرست ۸۱ استان، و خواندن اطلاعیه‌های رسمی İŞKUR.

> ساختهٔ محمد عباسی در چارچوب «کارخانهٔ MCP ترکیه» (خط لوله به سبک سپهر). وابسته به İŞKUR یا سازمان کاریابی ترکیه نیست.

**توجه:** نام کارفرما در سایت نیازمند ورود است و هرگز برگردانده نمی‌شود؛ صفحهٔ جزئیات مهلت یا شهر ندارد — این‌ها از نتایج جست‌وجو می‌آیند. جست‌وجو یک postback وب‌فرم است و کند است (حدود ۴۰ ثانیه)، پس صفحهٔ اول و فیلترهای محدود را ترجیح دهید.

## برای ایجنت‌های هوش مصنوعی

به پیکربندی کلاینت MCP خود اضافه کنید (stdio):

```json
{
  "mcpServers": {
    "iskur": {
      "command": "uvx",
      "args": ["iskur-mcp==0.1.0"]
    }
  }
}
```

یا به‌صورت محلی اجرا کنید: `python -m iskur_mcp.server` (نیازمند `mcp<2` و `curl-cffi`).

## ابزارها

| ابزار | توضیح |
|------|-------|
| `iskur_search_jobs` | جست‌وجو در آگهی‌های شغلی آزاد — `keyword` (مثل «garson»)، `city` نام یا کد استان (مثل «İstanbul» یا «34»)، `date_range` («all» / «last_24h» / «last_week» / «last_15d»)، `work_type` («all» / «full» / «part»)، `education` («any» / «illiterate» / «literate» / «primary» / «middle» / «high» / «associate» / «bachelor» / «master» / «phd»)، `page` (۱۵ آگهی در هر صفحه، مجموع و تعداد صفحات برگردانده می‌شود)، `limit` از ۱ تا ۱۵ |
| `iskur_latest_jobs` | آگهی‌های ۲۴ ساعت گذشته، اختیاری در یک `city`؛ `limit` از ۱ تا ۱۵ |
| `iskur_get_job` | جزئیات یک آگهی — `job_no` (مثل «00009899349»): توضیحات، مهارت‌ها، شغل، تجربه، حداقل/حداکثر تحصیلات |
| `iskur_list_cities` | ۸۱ استان — کد + نام (مثل «34» استانبول، «6» آنکارا) |
| `iskur_list_announcements` | اطلاعیه‌های رسمی İŞKUR؛ `limit` از ۱ تا ۱۰ |
| `iskur_health` | بررسی در دسترس بودن پورتال شغلی İŞKUR (ok / blocked / error) |

خروجی نمونه (`iskur_search_jobs` / «garson»، استانبول، ۲۰۲۶-۱۱-۱۳):

```json
{"keyword": "garson", "city": "İstanbul", "page": 1, "page_count": 5,
 "total": 63,
 "jobs": [{"job_no": "00009899349", "title": "Servis Elemanı (Garson)",
  "sector": "Özel", "period": "Daimi", "work_type": "Tam Zamanlı",
  "open_positions": 1,
  "location": {"city": "İSTANBUL", "district": "SARIYER"},
  "deadline": "30.11.2026", "days_left": "17 Gün Kaldı",
  "url": "https://esube.iskur.gov.tr/Istihdam/AcikIsIlanDetay.aspx?uiID=00009899349&isyeriTuru=%C3%96zel"}]}
```

## نحوهٔ کار

جست‌وجوی شغل در esube.iskur.gov.tr است (`/Istihdam/AcikIsIlanAra.aspx`، وب‌فرم کلاسیک ASP.NET): اول فرم با GET گرفته می‌شود (کوکی‌های نشست + خانوادهٔ `__VIEWSTATE`)، بعد با `__EVENTTARGET=ctl04$ctlAcikIsPageCommand$CommandItem_Search` پست می‌شود. نتایج در جدول `ctl04_ctlGridAcikIslerListeDetail`، ۱۵ سطر در هر صفحه؛ هر سطر یک پیوند عنوان `PopupJobDetails('<jobno>','Özel','0')`، spanهای بخش / مدت / نوع کار، `Label9` (موقعیت‌های آزاد)، `ctlCalismaYeriDL` («İl Geneli Başvuru (Çalışma Yeri: İSTANBUL / SARIYER)»)، `ctlSonBasvuruTarihi` (مهلت) و `ctlSonBasvuruDL` («17 Gün Kaldı») دارد؛ «Toplam Kayıt: 63» مجموع است و پرش بین صفحات با `txtCurrentPage` + `btnChangeCurrentPage` انجام می‌شود. جزئیات شغل یک GET ساده است (`AcikIsIlanDetay.aspx?uiID=...&isyeriTuru=Özel`، حدود ۲ ثانیه، بدون کوکی): `ctlGenelSartlar` (توضیحات)، `ctlGenelSartlar2` (مهارت‌ها)، `ctlMeslekLabel` (شغل) + spanهای تجربه، `ctlOgrenimAsgari` / `ctlOgrenimAzami` (تحصیلات). اطلاعیه‌ها با GET ساده از `www.iskur.gov.tr/duyurular/` گرفته می‌شوند (`<li class="clearfix">` با `<div class="date">` و پیوند `/duyurular/...`). انتقال با جعل هویت TLS کروم (`curl-cffi`، `chrome120` با چرخش) انجام می‌شود؛ postback جست‌وجو مهلت ۱۸۰ ثانیه‌ای و یک تلاش مجدد با نشست تازه دارد؛ درخواست‌ها با فاصلهٔ حدود ۰٫۸ ثانیه ارسال می‌شوند؛ همه‌چیز فقط‌خواندنی است.

## نصب

```bash
uvx iskur-mcp==0.1.0   # اجرای مستقیم (نیازمند uv)
# یا
pip install iskur-mcp==0.1.0
iskur-mcp    # سرور MCP را روی stdio راه می‌اندازد
```

## تست‌ها

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

تست‌های آفلاین روی فیکسچرهای ضبط‌شده اجرا می‌شوند (صفحات واقعی، ۲۰۲۶-۱۱-۱۳)؛ تست‌های زنده به esube.iskur.gov.tr و www.iskur.gov.tr می‌روند (postback جست‌وجو کند است، حدود ۴۰ ثانیه برای هر فراخوانی — تست‌های زنده حدود ۳ دقیقه طول می‌کشند). تست‌ها در زمان ساخت سبز بودند (تعدادها در ریپو) و یک تست smoke از نوع MCP stdio هم هست.

## نقشهٔ راه

- جست‌وجوی تکمیل خودکار شغل (فیلد `ctlMeslek` فرم)
- آگهی‌های بخش دولتی (کamu) با رادیوی بخش
- آگهی‌های برنامه‌های TYP / جوانان İŞKUR (IstIupArama / TypArama)

## مجوز

MIT — ببینید [LICENSE](LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
