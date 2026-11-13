# iskur-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/iskur-mcp

İŞKUR (iskur.gov.tr) — Türkiye İş Kurumu için resmi olmayan **salt okunur** MCP sunucusu. Esube portalındaki açık iş ilanlarını arayın (anahtar kelime, şehir, tarih aralığı, çalışma şekli, eğitim, sayfalama), bir iş ilanının detayını alın (açıklama, aranan nitelikler, meslek, deneyim, eğitim), 81 ili listeleyin ve İŞKUR'un resmi duyurularını okuyun.

> Mohammad Abbasi tarafından "Turkey MCP factory" (Sepehr tarzı pipeline) kapsamında geliştirildi. İŞKUR veya Türkiye İş Kurumu ile bağlantısı yoktur.

**Not:** İşveren adları sitede giriş gerektirdiği için asla döndürülmez; detay sayfasında son başvuru tarihi veya şehir bulunmaz — bunlar arama sonuçlarından gelir. Arama bir WebForms postback'idir ve yavaştır (~40 saniye), bu yüzden ilk sayfayı ve dar filtreleri tercih edin.

## Yapay zekâ ajanları için

MCP istemci yapılandırmanıza ekleyin (stdio):

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

Ya da yerelde çalıştırın: `python -m iskur_mcp.server` (`mcp<2`, `curl-cffi` gerekir).

## Araçlar

| Araç | Açıklama |
|------|----------|
| `iskur_search_jobs` | Açık iş ilanlarında arama — `keyword` (örn. "garson"), `city` adı veya kodu (örn. "İstanbul" / "34"), `date_range` ("all" / "last_24h" / "last_week" / "last_15d"), `work_type` ("all" / "full" / "part"), `education` ("any" / "illiterate" / "literate" / "primary" / "middle" / "high" / "associate" / "bachelor" / "master" / "phd"), `page` (sayfa başına 15, toplam + sayfa sayısı döndürülür), `limit` 1..15 |
| `iskur_latest_jobs` | Son 24 saatte yayınlanan işler, isteğe bağlı olarak bir `city` içinde; `limit` 1..15 |
| `iskur_get_job` | Bir ilanın detayı — `job_no` (örn. "00009899349"): açıklama, nitelikler, meslek, deneyim, en az/en fazla eğitim |
| `iskur_list_cities` | 81 il — kod + ad (örn. "34" İstanbul, "6" Ankara) |
| `iskur_list_announcements` | İŞKUR'un resmi duyuruları; `limit` 1..10 |
| `iskur_health` | İŞKUR iş portalına erişilip erişilemediğini kontrol eder (ok / blocked / error) |

Örnek çıktı (`iskur_search_jobs` / "garson", İstanbul, 2026-11-13):

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

## Nasıl çalışır?

İş arama esube.iskur.gov.tr adresindedir (`/Istihdam/AcikIsIlanAra.aspx`, klasik ASP.NET WebForms): önce form GET ile alınır (oturum çerezleri + `__VIEWSTATE` ailesi), sonra `__EVENTTARGET=ctl04$ctlAcikIsPageCommand$CommandItem_Search` ile POST yapılır. Sonuçlar `ctl04_ctlGridAcikIslerListeDetail` tablosunda, sayfa başına 15 satır; her satırda `PopupJobDetails('<jobno>','Özel','0')` başlık bağlantısı, sektör / süre / çalışma şekli span'leri, `Label9` (açık pozisyon), `ctlCalismaYeriDL` ("İl Geneli Başvuru (Çalışma Yeri: İSTANBUL / SARIYER)"), `ctlSonBasvuruTarihi` (son başvuru) ve `ctlSonBasvuruDL` ("17 Gün Kaldı") bulunur; "Toplam Kayıt: 63" toplamdır, sayfa atlama `txtCurrentPage` + `btnChangeCurrentPage` ile yapılır. İş detayı düz bir GET'tir (`AcikIsIlanDetay.aspx?uiID=...&isyeriTuru=Özel`, ~2 sn, çerez gerekmez): `ctlGenelSartlar` (açıklama), `ctlGenelSartlar2` (nitelikler), `ctlMeslekLabel` (meslek) + deneyim span'leri, `ctlOgrenimAsgari` / `ctlOgrenimAzami` (eğitim). Duyurular `www.iskur.gov.tr/duyurular/` adresinden düz GET ile alınır (`<li class="clearfix">`, `<div class="date">` ve `/duyurular/...` bağlantısı). Aktarım Chrome TLS kimliğine bürünme (`curl-cffi`, `chrome120` + dönüşüm) kullanır; arama postback'i 180 sn zaman aşımı ve yeni oturumla bir yeniden deneme alır; istekler ~0,8 sn arayla yapılır; her şey salt okunurdur.

## Kurulum

```bash
uvx iskur-mcp==0.1.0   # doğrudan çalıştır (uv gerekir)
# veya
pip install iskur-mcp==0.1.0
iskur-mcp    # MCP sunucusunu stdio üzerinde başlatır
```

## Testler

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Çevrimdışı testler kaydedilmiş fixture'larla çalışır (gerçek sayfalar, 2026-11-13); canlı testler esube.iskur.gov.tr ve www.iskur.gov.tr adreslerine gider (arama postback'i yavaştır, çağrı başına ~40 sn — canlı testler ~3 dakika sürer). Derleme anında testler yeşildir (sayılar için repoya bakın) ve bir MCP stdio smoke testi vardır.

## Yol haritası

- Meslek otomatik tamamlama araması (formun `ctlMeslek` alanı)
- Kamu ilanları (sektör radyosu ile)
- TYP / İŞKUR Gençlik programı ilanları (IstIupArama / TypArama)

## Lisans

MIT — bkz. [LICENSE](LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
