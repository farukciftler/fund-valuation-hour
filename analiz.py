#!/usr/bin/env python3
"""Yabanci hisse fonlarinin fiyati hangi saati yansitiyor?

On analiz plani: PLAN.md (commit 6125210, 2026-11-24). Tanimlar BURADA
DEGISTIRILMEZ; plandan sapan her sey ciktida "plan disi" diye etiketlenir.

Yalniz kamuya acik veri. Standart kutuphane + numpy.

    python3 analiz.py --indir     # ham veriyi veri/ altina indir (bir kez)
    python3 analiz.py --turet     # ham piyasa barlarindan getiri serilerini uret
    python3 analiz.py             # veri/ uzerinden analiz -> sonuc.json

Analiz, piyasa verisini ham barlardan degil veri/piyasa_getirileri.json'dan
okur. O dosya --turet ile ham barlardan uretilir ve analizin kullandigi her
getiriyi, analizin eskiden hesapladigi ifadeyle ayni ifadeyle tasir; sonuclar
birebir aynidir. Sebep: ham barlar veri saglayicinin dosyalari, acik kopyada
yeniden dagitilmiyor. Fon fiyatlari (TEFAS) ham haliyle arsivdedir.
"""
import argparse
import bisect
import json
import math
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta

import numpy as np

BURASI = os.path.dirname(os.path.abspath(__file__))
VERI = os.path.join(BURASI, "veri")
TURETILMIS = os.path.join(VERI, "piyasa_getirileri.json")
TSI = timedelta(hours=3)

# --- PLAN §2: evren (dondu) -------------------------------------------------
EVREN = ["AOY", "AFA", "AFV", "AFS", "AFT", "GBC", "GUH", "GBG", "YAY", "ZSF", "ARE", "TMG"]


def _kesif_kodu():
    """Kesif fonunun kodu YAYINLANMAZ: fon, atif yapilan anonim veri setindeki
    varliklardan biridir. Ozel kopyada KESIF.txt'ten (ya da ORIGIN_FUND ortam
    degiskeninden) okunur; acik kopyada ikisi de yoktur ve arsivlenmis bes
    sayi (kesif_fonu.json) oldugu gibi tasinir."""
    yol = os.path.join(BURASI, "KESIF.txt")
    return os.environ.get("ORIGIN_FUND") or (open(yol).read().strip() if os.path.exists(yol) else "")


KESIF_FONU = _kesif_kodu()              # dogrulayici kumeye GIRMEZ
KESIF_DOSYA = os.path.join(BURASI, "kesif_fonu.json")
# --- PLAN §3 ----------------------------------------------------------------
PENCERE_SON = "2026-11-20"
CAPA = "18:00"                          # P3'un sabit capasi
MIN_N = 150
ESIK_DR2 = 0.05
SURUCU = {"NQ": ("NQ%3DF", "%5ENDX"), "ES": ("ES%3DF", "%5EGSPC")}   # (vadeli, nakit)
KUR = "TRY%3DX"


def _json(url, body=None, hdr=None):
    h = {"User-Agent": "Mozilla/5.0"}
    h.update(hdr or {})
    req = urllib.request.Request(url, data=body, headers=h)
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())


# ----------------------------------------------------------------- indirme --
def indir():
    os.makedirs(VERI, exist_ok=True)
    kayit = {"indirildi": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+03:00"), "dosyalar": {}}
    th = {"Content-Type": "application/json", "Origin": "https://www.tefas.gov.tr"}
    liste = _json("https://www.tefas.gov.tr/api/funds/fonGetir", b"{}", th)
    json.dump(liste, open(os.path.join(VERI, "tefas_fonGetir.json"), "w"), ensure_ascii=False)
    for kod in EVREN + ([KESIF_FONU] if KESIF_FONU else []):
        d = _json("https://www.tefas.gov.tr/api/funds/fonFiyatBilgiGetir",
                  json.dumps({"fonKodu": kod, "periyod": "36"}).encode(), th)
        json.dump(d, open(os.path.join(VERI, f"tefas_{kod}.json"), "w"), ensure_ascii=False)
        kayit["dosyalar"][f"tefas_{kod}.json"] = len(d.get("resultList") or [])
        time.sleep(1.0)
    semboller = {KUR}
    for v, n in SURUCU.values():
        semboller |= {v, n}
    for s in sorted(semboller):
        for aralik, kapsam in (("1h", "730d"), ("1d", "5y")):
            d = _json(f"https://query1.finance.yahoo.com/v8/finance/chart/{s}"
                      f"?range={kapsam}&interval={aralik}")
            json.dump(d, open(os.path.join(VERI, f"yahoo_{aralik}_{s}.json"), "w"))
            kayit["dosyalar"][f"yahoo_{aralik}_{s}.json"] = len(d["chart"]["result"][0]["timestamp"])
            time.sleep(1.0)
    json.dump(kayit, open(os.path.join(VERI, "INDIRME.json"), "w"), indent=1)
    print(json.dumps(kayit, indent=1))


# ------------------------------------------------------------------ okuma --
def yahoo(aralik, sembol):
    d = json.load(open(os.path.join(VERI, f"yahoo_{aralik}_{sembol}.json")))
    r = d["chart"]["result"][0]
    return r["timestamp"], r["indicators"]["quote"][0]["close"]


def saatlik(sembol):
    """{(TSI tarih, 'HH:MM'): kapanis}; etiket = bar baslangici + 1 saat."""
    out = {}
    for t, c in zip(*yahoo("1h", sembol)):
        if c is None:
            continue
        son = datetime.utcfromtimestamp(t) + timedelta(hours=1) + TSI
        out[(son.strftime("%Y-%m-%d"), son.strftime("%H:%M"))] = float(c)
    return out


def gunluk(sembol):
    out = {}
    for t, c in zip(*yahoo("1d", sembol)):
        if c is not None:
            out[(datetime.utcfromtimestamp(t) + TSI).strftime("%Y-%m-%d")] = float(c)
    return out


def abd_ofset(utc):
    """ABD dogu saati ofseti (saat): yaz -4, kis -5. DST: Mart'in 2. Pazar'i
    02:00 yerel -> Kasim'in 1. Pazar'i 02:00 yerel."""
    y = utc.year
    mar = datetime(y, 3, 8)
    mar += timedelta(days=(6 - mar.weekday()) % 7)          # Mart'in 2. Pazar'i
    kas = datetime(y, 11, 1)
    kas += timedelta(days=(6 - kas.weekday()) % 7)          # Kasim'in 1. Pazar'i
    bas = mar + timedelta(hours=7)                          # 02:00 EST = 07:00 UTC
    bit = kas + timedelta(hours=6)                          # 02:00 EDT = 06:00 UTC
    return -4 if bas <= utc < bit else -5


def abd_kapanis(sembol):
    """{ABD (ET) tarihi: vadelinin 16:00 ET'de BITEN saatlik barinin kapanisi}."""
    out = {}
    for t, c in zip(*yahoo("1h", sembol)):
        if c is None:
            continue
        bit = datetime.utcfromtimestamp(t) + timedelta(hours=1)
        et = bit + timedelta(hours=abd_ofset(bit))
        if et.strftime("%H:%M") == "16:00":
            out[et.strftime("%Y-%m-%d")] = float(c)
    return out


def tefas(kod):
    d = json.load(open(os.path.join(VERI, f"tefas_{kod}.json")))
    return sorted((r["tarih"], float(r["fiyat"])) for r in (d.get("resultList") or [])
                  if r.get("tarih") and r.get("fiyat") is not None and float(r["fiyat"]) > 0)


def unvanlar():
    d = json.load(open(os.path.join(VERI, "tefas_fonGetir.json")))
    return {x["fonKodu"]: x["fonUnvan"] for x in d["resultList"]}


# --------------------------------------------------------------- yardimci --
def seri_getiri(gf):
    g = sorted(gf)
    return g, {b: gf[b] / gf[a] - 1 for a, b in zip(g, g[1:])}


def seri(satirlar):
    """[[gun, getiri | None], ...] -> (gunler, {gun: getiri}). Ilk gunun
    getirisi yoktur (None); gun listesinde yine de durur."""
    return [g for g, _ in satirlar], {g: r for g, r in satirlar if r is not None}


def turet():
    """Ham barlardan analizin kullandigi getiri serilerini uretir.

    Her getiri, analizin tanimladigi ifadeyle hesaplanir ve yuvarlanmaz:
      saatlik[s][h]  : P(gun, h) / P(h'de bari olan onceki gun, h) - 1
      gunluk[s]      : ardisik iki gunluk kapanisin orani - 1
      capa[vadeli]   : gun d icin  E = P(d, 18:00) / ABD_kapanis(onceki) - 1
                                   L = ABD_kapanis(d) / P(d, 18:00) - 1
                                   kur = kur(d, 18:00) / kur(onceki, 18:00) - 1
                       'onceki' = hem 18:00 bari hem ABD kapanisi olan onceki gun
    """
    vadeliler = sorted(v for v, _ in SURUCU.values())
    nakitler = sorted(n for _, n in SURUCU.values())
    out = {"not": "Derived from the archived raw bars by analiz.py --turet; unrounded.",
           "ham_indirme": json.load(open(os.path.join(VERI, "INDIRME.json")))["indirildi"],
           "capa_saati": CAPA, "saatlik": {}, "gunluk": {}, "capa": {}}
    H = {s: saatlik(s) for s in [KUR] + vadeliler}
    for s, sd in H.items():
        saat = {}
        for h in sorted({h for _, h in sd}):
            gunler, get = seri_getiri({g: v for (g, hh), v in sd.items() if hh == h})
            saat[h] = [[g, get.get(g)] for g in gunler]
        out["saatlik"][s] = {"ilk_gun": min(g for g, _ in sd), "saat": saat}
    for s in [KUR] + nakitler:
        gunler, get = seri_getiri(gunluk(s))
        out["gunluk"][s] = [[g, get.get(g)] for g in gunler]
    Kcap = {g: v for (g, hh), v in H[KUR].items() if hh == CAPA}
    for v in vadeliler:
        A = {g: x for (g, hh), x in H[v].items() if hh == CAPA}
        C = abd_kapanis(v)
        gunler = sorted(set(A) & set(C))
        rows = []
        for i, d in enumerate(gunler):
            p = gunler[i - 1] if i else None
            rows.append([d,
                         (A[d] / C[p] - 1) if p else None,
                         C[d] / A[d] - 1,
                         (Kcap[d] / Kcap[p] - 1) if p and d in Kcap and p in Kcap else None])
        out["capa"][v] = rows
    json.dump(out, open(TURETILMIS, "w"))
    print(f"{TURETILMIS}: {os.path.getsize(TURETILMIS) / 1e6:.1f} MB; "
          + ", ".join(f"{s} {sum(len(x) for x in d['saat'].values())} saatlik getiri"
                      for s, d in out["saatlik"].items()))


def piyasa():
    return json.load(open(TURETILMIS))


def D(gunler, t, k):
    """t'ye gore k'inci islem gunu (k=0: t'nin kendisi, yoksa None)."""
    i = bisect.bisect_left(gunler, t)
    if k == 0:
        return t if i < len(gunler) and gunler[i] == t else None
    i -= k
    return gunler[i] if i >= 0 else None


def ols(X, y, hc1=False):
    """X: (n, p) sabit DAHIL. Doner: beta, r2, se (HC1 istenirse dayanikli).

    Carpimlar einsum ile: bu makinedeki numpy/Accelerate ikilisi `@` icin
    sahte "divide by zero / overflow" uyarisi uretiyor. Sonuc `dogrula()` ile
    saf Python hesabina karsi sinanir.
    """
    X = np.asarray(X, float); y = np.asarray(y, float)
    n, p = X.shape
    XtX = np.einsum("ni,nj->ij", X, X)
    Xty = np.einsum("ni,n->i", X, y)
    XtX_inv = np.linalg.inv(XtX)
    b = np.einsum("ij,j->i", XtX_inv, Xty)
    e = y - np.einsum("ni,i->n", X, b)
    ss_res = float(np.einsum("n,n->", e, e))
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    if hc1:
        meat = np.einsum("ni,n,nj->ij", X, e ** 2, X)
        V = np.einsum("ij,jk,kl->il", XtX_inv, meat, XtX_inv) * n / (n - p)
    else:
        V = XtX_inv * ss_res / (n - p)
    return b, r2, np.sqrt(np.diag(V))


def dogrula():
    """Tek degiskenli OLS'u saf Python'la yeniden hesapla ve karsilastir."""
    rng = np.random.default_rng(7)
    x = rng.normal(size=300); y = 0.6 * x + rng.normal(scale=0.5, size=300)
    b, r2, _ = ols(np.column_stack([np.ones(300), x]), y)
    mx, my = sum(x) / 300, sum(y) / 300
    sxy = sum((a - mx) * (c - my) for a, c in zip(x, y)); sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((c - my) ** 2 for c in y)
    assert abs(b[1] - sxy / sxx) < 1e-9 and abs(r2 - sxy ** 2 / (sxx * syy)) < 1e-9, "OLS uyusmuyor"


def tek(x, y):
    b, r2, _ = ols(np.column_stack([np.ones(len(x)), x]), y)
    return r2, float(b[1])


def norm_sf(z):
    return 0.5 * math.erfc(z / math.sqrt(2))


def saat_fark(a, b):
    d = abs(int(a[:2]) * 60 + int(a[3:]) - int(b[:2]) * 60 - int(b[3:]))
    return min(d, 1440 - d) / 60


def binom_ust(k, n):
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


# ---------------------------------------------------------------- analiz --
def fon_analiz(kod, unvan, P):
    tek_surucu = "NQ" if "TEKNOLOJ" in unvan.upper().replace("İ", "I") else "ES"
    vadeli, nakit = SURUCU[tek_surucu]
    sd, kd = P["saatlik"][vadeli], P["saatlik"][KUR]
    nav = [x for x in tefas(kod) if x[0] <= PENCERE_SON]
    y = {b: pb / pa - 1 for (a, pa), (b, pb) in zip(nav, nav[1:])}
    ilk = max(sd["ilk_gun"], kd["ilk_gun"])
    tarihler = [t for t, _ in nav if t in y and t > ilk]
    cikti = {"fon": kod, "unvan": unvan, "surucu": tek_surucu,
             "fiyat_gunu": len(tarihler)}
    if len(tarihler) < MIN_N:
        cikti["elendi"] = f"pencerede {len(tarihler)} fiyat gunu (< {MIN_N})"
        return cikti
    cikti["ilk"], cikti["son"] = tarihler[0], tarihler[-1]

    # --- referans: gunluk kapanis (nakit endeks + kur), k in {0,1,2}; en iyisi
    rg = [seri(P["gunluk"][nakit]), seri(P["gunluk"][KUR])]

    def toplam(bacaklar, t, k):
        s = 0.0
        for gunler, get in bacaklar:
            d = D(gunler, t, k)
            if d is None or d not in get:
                return None
            s += get[d]
        return s

    ref = {}
    for k in (0, 1, 2):
        rows = [(t, toplam(rg, t, k)) for t in tarihler]
        rows = [r for r in rows if r[1] is not None]
        r2, beta = tek([r[1] for r in rows], [y[r[0]] for r in rows])
        ref[k] = {"k": k, "n": len(rows), "r2": round(r2, 4), "beta": round(beta, 4)}
    ref_k = max(ref, key=lambda k: ref[k]["r2"])
    ref_x = {t: toplam(rg, t, ref_k) for t in tarihler}
    cikti["referans"] = {"secilen_k": ref_k, "hizalamalar": [ref[k] for k in (0, 1, 2)]}

    # --- adaylar: saatlik (vadeli + kur), k in {0,1,2}
    saatler = sorted(set(sd["saat"]) & set(kd["saat"]))
    adaylar = []
    for h in saatler:
        bac = [seri(s["saat"][h]) for s in (sd, kd)]
        for k in (0, 1, 2):
            satir = [(t, toplam(bac, t, k), ref_x[t]) for t in tarihler]
            satir = [s for s in satir if s[1] is not None and s[2] is not None]
            if len(satir) < MIN_N:
                continue
            ys = [y[s[0]] for s in satir]
            r2, beta = tek([s[1] for s in satir], ys)
            r2r, betar = tek([s[2] for s in satir], ys)
            yari = len(satir) // 2
            y1 = tek([s[1] for s in satir[:yari]], ys[:yari])[0]
            y2 = tek([s[1] for s in satir[yari:]], ys[yari:])[0]
            adaylar.append({"h": h, "k": k, "n": len(satir), "r2": round(r2, 4),
                            "beta": round(beta, 4), "ref_r2": round(r2r, 4),
                            "ref_beta": round(betar, 4), "dr2": round(r2 - r2r, 4),
                            "r2_yari1": round(y1, 4), "r2_yari2": round(y2, 4)})
    en = max(adaylar, key=lambda a: a["dr2"])
    e1 = max(adaylar, key=lambda a: a["r2_yari1"])
    e2 = max(adaylar, key=lambda a: a["r2_yari2"])
    kararli = saat_fark(e1["h"], en["h"]) <= 1 and saat_fark(e2["h"], en["h"]) <= 1
    cikti["en_iyi"] = en
    cikti["yarilar"] = {"yari1": {"h": e1["h"], "k": e1["k"]}, "yari2": {"h": e2["h"], "k": e2["k"]}}
    cikti["P1_saat"] = bool(en["k"] == 1 and "17:00" <= en["h"] <= "19:00")
    cikti["P2_buyukluk_kararlilik"] = bool(en["dr2"] >= ESIK_DR2 and kararli)
    cikti["P4_beta"] = bool(en["ref_beta"] < en["beta"])
    cikti["egri_k1"] = [{"h": a["h"], "r2": a["r2"], "n": a["n"]} for a in adaylar if a["k"] == 1]

    # --- P3: sabit capa 18:00. fon_t = a + bE*E_{s} + bL*L_{s'} ;
    #     s = t'den onceki surucu gunu, s' = s'den onceki surucu gunu.
    capa = {d: (E, L) for d, E, L, _ in P["capa"][vadeli]}
    gunler = [d for d, *_ in P["capa"][vadeli]]
    rows = []
    for t in tarihler:
        s = D(gunler, t, 1)
        s2 = D(gunler, s, 1) if s else None
        if not s or not s2:
            continue
        E = capa[s][0]                  # t-2 kapanisindan t-1 18:00'e
        L = capa[s2][1]                 # t-2'nin gec seansi
        rows.append((y[t], E, L))
    if len(rows) >= MIN_N:
        yy = [r[0] for r in rows]
        X = np.column_stack([np.ones(len(rows)), [r[1] for r in rows], [r[2] for r in rows]])
        b, r2, se = ols(X, yy, hc1=True)
        z = float(b[2] / se[2])
        cikti["P3"] = {"n": len(rows), "b_E": round(float(b[1]), 4), "se_E": round(float(se[1]), 4),
                       "b_L": round(float(b[2]), 4), "se_L": round(float(se[2]), 4),
                       "z_L": round(z, 2), "p_tek_yonlu": norm_sf(z), "r2": round(r2, 4),
                       "anlamli": bool(norm_sf(z) < 0.05 and b[2] > 0)}
    return cikti


def main():
    dogrula()
    P = piyasa()
    U = unvanlar()
    fonlar = [fon_analiz(k, U[k], P) for k in EVREN]
    if KESIF_FONU and os.path.exists(os.path.join(VERI, f"tefas_{KESIF_FONU}.json")):
        k = fon_analiz(KESIF_FONU, U[KESIF_FONU], P)
        kesif = {"fon": "[withheld]",
                 "not": "identity withheld; these five figures are all the paper reports for it",
                 "en_iyi": {x: k["en_iyi"][x] for x in ("h", "k", "r2", "ref_r2")},
                 "P3": {x: k["P3"][x] for x in ("b_L", "z_L")}}
        json.dump(kesif, open(KESIF_DOSYA, "w"), indent=1)
    else:
        kesif = json.load(open(KESIF_DOSYA))
    gecerli = [f for f in fonlar if "elendi" not in f]

    def say(alan):
        return sum(1 for f in gecerli if f.get(alan))
    p3 = [f["P3"] for f in gecerli if "P3" in f]
    ozet = {
        "evren": len(EVREN), "gecerli_fon": len(gecerli),
        "elenen": [{"fon": f["fon"], "neden": f["elendi"]} for f in fonlar if "elendi" in f],
        "P1": {"tutan": say("P1_saat"), "esik": 7},
        "P2": {"tutan": say("P2_buyukluk_kararlilik"), "esik": 7},
        "P3": {"anlamli": sum(1 for x in p3 if x["anlamli"]), "esik": 7,
               "b_L_pozitif": sum(1 for x in p3 if x["b_L"] > 0), "n_fon": len(p3),
               "isaret_testi_p": binom_ust(sum(1 for x in p3 if x["b_L"] > 0), len(p3)) if p3 else None,
               "b_L_medyan": float(np.median([x["b_L"] for x in p3])) if p3 else None,
               "b_E_medyan": float(np.median([x["b_E"] for x in p3])) if p3 else None},
        "P4": {"tutan": say("P4_beta"), "esik": 10},
        "dr2_medyan": float(np.median([f["en_iyi"]["dr2"] for f in gecerli])),
        "ref_r2_medyan": float(np.median([f["en_iyi"]["ref_r2"] for f in gecerli])),
        "en_iyi_r2_medyan": float(np.median([f["en_iyi"]["r2"] for f in gecerli])),
    }
    sonuc = {"plan": "PLAN.md, commit 6125210 (2026-11-24)",
             "veri_indirme": json.load(open(os.path.join(VERI, "INDIRME.json")))["indirildi"],
             "pencere_son": PENCERE_SON, "ozet": ozet, "fonlar": fonlar,
             "kesif_fonu_AYRI": kesif}
    json.dump(sonuc, open(os.path.join(BURASI, "sonuc.json"), "w"), ensure_ascii=False, indent=1)
    print(f"{'fon':4s} {'sur':3s} {'n':>4s} {'ref k':>5s} {'ref R2':>7s} {'en iyi':>9s} {'R2':>6s} "
          f"{'dR2':>7s} {'yarilar':>13s} {'P1':>3s} {'P2':>3s} {'b_E':>6s} {'b_L':>6s} {'z_L':>6s} {'P4':>3s}")
    for f in fonlar:
        if "elendi" in f:
            print(f"{f['fon']:4s} ELENDI: {f['elendi']}")
            continue
        e, p = f["en_iyi"], f.get("P3", {})
        print(f"{f['fon']:4s} {f['surucu']:3s} {e['n']:4d} {f['referans']['secilen_k']:5d} "
              f"{e['ref_r2']:7.3f} {e['h']+'/k'+str(e['k']):>9s} {e['r2']:6.3f} {e['dr2']:+7.3f} "
              f"{f['yarilar']['yari1']['h']+'/'+f['yarilar']['yari2']['h']:>13s} "
              f"{'+' if f['P1_saat'] else '-':>3s} {'+' if f['P2_buyukluk_kararlilik'] else '-':>3s} "
              f"{p.get('b_E', float('nan')):6.3f} {p.get('b_L', float('nan')):6.3f} "
              f"{p.get('z_L', float('nan')):6.2f} {'+' if f['P4_beta'] else '-':>3s}")
    print(f"kesif fonu (AYRI, kimligi sakli): en iyi {kesif['en_iyi']['h']}/k{kesif['en_iyi']['k']} "
          f"R2 {kesif['en_iyi']['r2']:.3f} ref {kesif['en_iyi']['ref_r2']:.3f} "
          f"b_L {kesif['P3']['b_L']:.3f} z_L {kesif['P3']['z_L']:.2f}")
    print(json.dumps(ozet, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", action="store_true")
    ap.add_argument("--turet", action="store_true")
    a = ap.parse_args()
    if a.indir:
        indir()
    elif a.turet:
        turet()
    else:
        main()
