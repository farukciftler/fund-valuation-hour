# Ön analiz planı — yabancı hisse fonlarının fiyatı hangi saati yansıtıyor?

> **Açık kopya notu.** Bu dosya, plan commit edildiği hâliyle yayınlanır; tek fark,
> yazarın kendi varlıklarına ait fon kodlarının `▮▮▮` ile maskelenmesidir
> (5 yer). English translation: `PLAN.en.md`.
> §7'deki "ham indirmeler `veri/` altında saklanır ve analiz onlardan koşar" cümlesi fon
> fiyatları için aynen geçerlidir; piyasa barları yerine bu kopyada onlardan türetilen
> getiri serileri durur (README, "Market data").

**Yazıldı:** 2026-11-24, analizden ÖNCE. Bu dosyanın commit'i zaman damgasıdır.
**Durum beyanı:** Bu plan yazılırken aşağıdaki 12 fonun fiyat serisine
**bakılmadı**; yalnız TEFAS'ın fon listesinden (`fonGetir`) unvanları okundu.

Bu çalışma yalnız **kamuya açık veri** kullanır (TEFAS fiyatları, Yahoo vadeli
ve endeks barları). Kişisel defterden hiçbir şey girmez.

---

## 1. Nereden çıktı

Kişisel defterdeki tek bir fon (▮▮▮) üzerinde yapılan keşifsel ölçüm (H23,
03.10.2026, 500 fiyat günü): fonun T günü fiyatını, ABD'nin T−1 **kapanışı**
R² = 0,15 ile; T−1 günü **18:00 TSİ**'deki vadeli fiyatı R² = 0,53 ile
açıklıyor. Etki iki zaman yarısında aynı saatte.

Bu **keşifseldir** ve tek fondur. Aşağıdaki plan, aynı soruyu o fonla ilgisi
olmayan bir fon evreninde, tanımı baştan sabitlenmiş biçimde sorar.
**▮▮▮ doğrulayıcı kümeye girmez**; yalnız "keşif fonu" olarak ayrı raporlanır.

Süren H26 testi (▮▮▮/▮▮▮/▮▮▮, n = 40 fiyat günü) bu plandan bağımsızdır ve
bu çalışmada **raporlanmaz**.

## 2. Evren (dondu)

TEFAS `fonGetir` listesinde (24.11.2026) unvanında hem `YABANCI` hem `HİSSE`
geçen fonlar. On iki fon:

`AOY` `AFA` `AFV` `AFS` `AFT` `GBC` `GUH` `GBG` `YAY` `ZSF` `ARE` `TMG`

Bir fon, pencerede **150'den az** kullanılabilir fiyat günü veriyorsa elenir
ve elendiği raporlanır. Başka fon eklenmez, çıkarılmaz.

## 3. Veri ve pencere

- **Fon fiyatı:** TEFAS `fonFiyatBilgiGetir`, tarihli. Getiri = ardışık iki
  yayınlanmış fiyatın oranı − 1.
- **Sürücü (saatlik):** Yahoo 1 saatlik barlar, 730 gün. Bar zaman damgası
  barın **başlangıcıdır**; `h` = başlangıç + 1 saat, TSİ (UTC+3), sabit.
- **Sürücü eşlemesi (unvandan, baştan):** unvanında `TEKNOLOJİ` geçen fon →
  `NQ=F`; diğerleri → `ES=F`.
- **Kur bacağı:** fon TL fiyatlandığı için `TRY=X` aynı saatte eklenir:
  `x = r_sürücü(h) + r_kur(h)`.
- **Pencere:** saatlik verinin kapsadığı ilk günden **2026-11-20**'ye kadar
  olan fiyat günleri. Bitiş tarihi bu planda sabittir.
- **Zaman yarıları:** kullanılabilir satırların ilk ve ikinci yarısı.

## 4. Adaylar ve referans

- **Aday (h, k):** `h` = sürücü ve kur serilerinde ortak her saatlik bar
  bitişi; `k ∈ {0, 1, 2}` işlem günü gecikme.
  `x_t = P(gün t−k, saat h) / P(gün t−k−1, saat h) − 1`.
- **İşlem günü:** sürücü serisinde o saatte bar bulunan TSİ takvim günü.
- **n < 150** olan aday elenir.
- **Referans (geleneksel hizalama):** nakit endeksin (`^GSPC` ya da `^NDX`)
  **günlük kapanış** getirisi + `TRY=X` günlük getirisi, `k ∈ {0, 1, 2}`.
  Üç hizalamanın **en yüksek R² vereni** referanstır. Bu, geleneksel yaklaşımın
  lehine seçilmiş muhafazakâr bir karşılaştırmadır.
- ΔR² her aday için referansla **aynı satırlarda** hesaplanır.

## 5. Hipotezler ve ölçütler

**P1 — saat.** Fonların çoğunda en iyi aday `k = 1` ve `h ∈ [17:00, 19:00]`.
Ölçüt: 12 fonun **en az 7'sinde**.

**P2 — büyüklük ve kararlılık.** En iyi aday referansı `ΔR² ≥ 0,05` ile geçer
**ve** iki zaman yarısının en iyi saati tüm örneklemin en iyi saatinin ±1 saat
içindedir. Ölçüt: **en az 7 fonda** ikisi birden.
Saat taraması çoklu karşılaştırmadır; P1 ve P2 için **p değeri raporlanmaz**.

**P3 — ayırt edici test (saat taraması YOK, çapa sabit 18:00).**
`L_{t−2}` = sürücünün `t−2` günü 18:00'den o günün ABD kapanışına getirisi
(geç seans). `E_{t−1}` = `t−2` kapanışından `t−1` 18:00'e getiri.
Regresyon: `fon_t = a + b_E · E_{t−1} + b_L · L_{t−2} + e`.

- Fon `t−1` **18:00**'i fiyatlıyorsa: `b_L > 0` ve `b_L ≈ b_E`.
- Fon `t−1` **kapanışını** fiyatlıyorsa: `L_{t−2}` zaten bir önceki günün
  fiyatındadır, `b_L ≈ 0`.

Test: `b_L > 0`, tek yönlü, heteroskedastisiteye dayanıklı (HC1) standart hata,
α = 0,05. Ölçüt: **en az 7 fonda** anlamlı. Ayrıca fonlar arası işaret testi
raporlanır. Bu test için kur bacağı eklenmez (iki pencerenin kur getirisi
ayrı tanımlanamıyor); sağlamlık olarak eklenmiş hâli de verilir.

**P4 — ölçüm sonucu.** Geleneksel hizalamayla tahmin edilen piyasa betası,
en iyi saatle tahmin edilenden küçüktür. Ölçüt: **en az 10 fonda**
`β_referans < β_en iyi`.

## 6. Yorum kuralları (sonuç görülmeden)

- **Mekanizma iddiası yok.** Ölçülen şey bir korelasyon örüntüsüdür; "değerleme
  saati 18:00'dir" iddiası ancak mevzuat ya da izahname metniyle desteklenirse
  yazılır.
- **Arbitraj iddiası yok**, emir kesim saati ve fiyatlama (ileri/geri) kuralı
  doğrulanmadan. İleri fiyatlama varsa bulgu bir **ölçüm** bulgusudur
  (eşzamansız getiri, yanlı beta), sömürülebilir bir fırsat değil.
- Sürücüsü ABD olmayan fonlarda (Avrupa, çok ülkeli) zayıf sonuç hipotezi
  çürütmez, sürücü eşlemesinin kabalığını gösterir; bu fonlar tabloda
  işaretlenir ama **paydadan çıkarılmaz**.
- Ölçütlerden biri tutmazsa öyle raporlanır. Evren, sürücü eşlemesi, pencere
  ve eşikler sonuçtan sonra değiştirilmez; değişen her şey "plan dışı" diye
  etiketlenir.

## 7. Bilinen kısıtlar (baştan)

- Saatlik çözünürlük: gerçek an ±30 dk.
- ABD yaz/kış saati geçişi nakit seansı TSİ'de bir saat kaydırır; vadeli
  işlemler neredeyse 24 saat açık olduğu için saat etiketi sabit kalır.
- Yahoo barları sonradan düzeltilebilir; ham indirmeler `veri/` altında
  saklanır ve analiz onlardan koşar.
- Fonların gerçek bölgesel dağılımı bilinmiyor; sürücü unvandan atanıyor.
