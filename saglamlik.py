#!/usr/bin/env python3
"""PLAN DISI saglamlik kontrolleri. Ana sonuc analiz.py'dedir; buradaki hicbir
sey on kayitli degildir ve makalede "exploratory / not pre-specified" diye
etiketlenir. Sonuclar goruldukten SONRA yazildi (2026-11-24).

    python3 saglamlik.py  ->  saglamlik.json, sekil_egri.tex
"""
import json
import os
from datetime import datetime, timedelta

import numpy as np

import analiz as A

BURASI = os.path.dirname(os.path.abspath(__file__))


def yaz_saati(tarih):
    """TSI tarihindeki 18:00 ani ABD yaz saatinde mi (EDT)?"""
    utc = datetime.strptime(tarih, "%Y-%m-%d") + timedelta(hours=15)
    return A.abd_ofset(utc) == -4


def main():
    A.dogrula()
    P = A.piyasa()
    ana = json.load(open(os.path.join(BURASI, "sonuc.json")))
    cikti = {"not": "PLAN DISI - kesifsel", "fonlar": []}
    for f in ana["fonlar"]:
        kod = f["fon"]
        vadeli = A.SURUCU[f["surucu"]][0]
        sd, kd = P["saatlik"][vadeli], P["saatlik"][A.KUR]
        nav = [x for x in A.tefas(kod) if x[0] <= A.PENCERE_SON]
        y = {b: pb / pa - 1 for (a, pa), (b, pb) in zip(nav, nav[1:])}
        ilk = max(sd["ilk_gun"], kd["ilk_gun"])
        tarihler = [t for t, _ in nav if t in y and t > ilk]
        capa = {d: (E_, L_, fx_) for d, E_, L_, fx_ in P["capa"][vadeli]}
        gunler = [d for d, *_ in P["capa"][vadeli]]
        rows = []
        for t in tarihler:
            s = A.D(gunler, t, 1)
            s2 = A.D(gunler, s, 1) if s else None
            if not s or not s2:
                continue
            E = capa[s][0]
            L2 = capa[s2][1]                     # t-2'nin gec seansi (fiyatta olmali)
            L1 = capa[s][1]                      # t-1'in gec seansi (degerlemeden SONRA)
            fx = capa[s][2]                      # kur, t-2 18:00 -> t-1 18:00
            rows.append((t, y[t], E, L2, L1, fx))
        yy = np.array([r[1] for r in rows])
        one = np.ones(len(rows))
        # 1) plasebo: t-1'in gec seansi degerleme anindan sonra olusur -> katsayi ~0
        b, r2, se = A.ols(np.column_stack([one, [r[2] for r in rows], [r[3] for r in rows],
                                           [r[4] for r in rows]]), yy, hc1=True)
        plasebo = {"b_L_onceki": round(float(b[2]), 4), "b_L_sonraki": round(float(b[3]), 4),
                   "se_sonraki": round(float(se[3]), 4), "z_sonraki": round(float(b[3] / se[3]), 2)}
        # 2) P3 + kur bacagi
        rk = [r for r in rows if r[5] is not None]
        bk, r2k, sek = A.ols(np.column_stack([np.ones(len(rk)), [r[2] for r in rk],
                                              [r[3] for r in rk], [r[5] for r in rk]]),
                             [r[1] for r in rk], hc1=True)
        kurlu = {"n": len(rk), "b_E": round(float(bk[1]), 4), "b_L": round(float(bk[2]), 4),
                 "z_L": round(float(bk[2] / sek[2]), 2), "b_kur": round(float(bk[3]), 4),
                 "r2": round(r2k, 4)}
        # 3) yalniz t-2 gec seansi: fon tarihinden >= 1 islem gunu once bilinen bilgi
        r2_L = A.tek([r[3] for r in rows], yy)[0]
        # 4) yaz / kis saati: en iyi TSI saati kayiyor mu? (k = 1, surucu + kur)
        mevsim = {}
        saatler = sorted(set(sd["saat"]) & set(kd["saat"]))
        for ad, secim in (("yaz_EDT", True), ("kis_EST", False)):
            en = None
            for h in saatler:
                bac = [A.seri(s["saat"][h]) for s in (sd, kd)]
                sat = []
                for t in tarihler:
                    tot = 0.0
                    for gl, get in bac:
                        d = A.D(gl, t, 1)
                        if d is None or d not in get:
                            tot = None
                            break
                        tot += get[d]
                    d1 = A.D(bac[0][0], t, 1)
                    if tot is not None and d1 and yaz_saati(d1) == secim:
                        sat.append((tot, y[t]))
                if len(sat) < 100:
                    continue
                r2h = A.tek([a for a, _ in sat], [b_ for _, b_ in sat])[0]
                if en is None or r2h > en["r2"]:
                    en = {"h": h, "r2": round(r2h, 4), "n": len(sat)}
            mevsim[ad] = en
        cikti["fonlar"].append({"fon": kod, "surucu": f["surucu"], "n": len(rows),
                                "plasebo": plasebo, "kurlu_P3": kurlu,
                                "r2_yalniz_gec_seans": round(r2_L, 4), "mevsim": mevsim,
                                "beta_ref": f["en_iyi"]["ref_beta"], "beta_en_iyi": f["en_iyi"]["beta"]})
    F = cikti["fonlar"]
    cikti["ozet"] = {
        "plasebo_z_abs_gt_1.96": sum(1 for f in F if abs(f["plasebo"]["z_sonraki"]) > 1.96),
        "plasebo_b_medyan": float(np.median([f["plasebo"]["b_L_sonraki"] for f in F])),
        "kurlu_bL_pozitif_z_gt_1.645": sum(1 for f in F if f["kurlu_P3"]["z_L"] > 1.645),
        "r2_yalniz_gec_seans_medyan": float(np.median([f["r2_yalniz_gec_seans"] for f in F])),
        "beta_ref_medyan": float(np.median([f["beta_ref"] for f in F])),
        "beta_en_iyi_medyan": float(np.median([f["beta_en_iyi"] for f in F])),
        "mevsim_ayni_saat": sum(1 for f in F if f["mevsim"]["yaz_EDT"] and f["mevsim"]["kis_EST"]
                                and f["mevsim"]["yaz_EDT"]["h"] == f["mevsim"]["kis_EST"]["h"]),
    }
    json.dump(cikti, open(os.path.join(BURASI, "saglamlik.json"), "w"), ensure_ascii=False, indent=1)
    print(f"{'fon':4s} {'bL(t-2)':>8s} {'bL(t-1)':>8s} {'z':>6s} | {'kurlu bL':>8s} {'z':>6s} {'b_kur':>6s} | "
          f"{'R2(L)':>6s} | {'yaz':>11s} {'kis':>11s} | {'b_ref':>6s} {'b_iyi':>6s}")
    for f in F:
        p, k, m = f["plasebo"], f["kurlu_P3"], f["mevsim"]
        ms = lambda x: f"{x['h']} {x['r2']:.2f}" if x else "-"
        print(f"{f['fon']:4s} {p['b_L_onceki']:8.3f} {p['b_L_sonraki']:8.3f} {p['z_sonraki']:6.2f} | "
              f"{k['b_L']:8.3f} {k['z_L']:6.2f} {k['b_kur']:6.2f} | {f['r2_yalniz_gec_seans']:6.3f} | "
              f"{ms(m['yaz_EDT']):>11s} {ms(m['kis_EST']):>11s} | {f['beta_ref']:6.3f} {f['beta_en_iyi']:6.3f}")
    print(json.dumps(cikti["ozet"], indent=1))

    # sekil: R2 egrisi (k = 1), saat ekseni. pgfplots koordinatlari.
    satirlar = ["% URETILDI: saglamlik.py - elle duzenleme"]
    for f in ana["fonlar"]:
        pts = " ".join(f"({int(e['h'][:2]) + int(e['h'][3:]) / 60:.1f},{e['r2']:.4f})"
                       for e in f["egri_k1"] if e["h"].endswith(":00"))
        stil = "thick" if f["surucu"] == "NQ" else "thin"
        satirlar.append(f"\\addplot[{stil}, mark=none] coordinates {{{pts}}}; % {f['fon']}")
    open(os.path.join(BURASI, "sekil_egri.tex"), "w").write("\n".join(satirlar) + "\n")


if __name__ == "__main__":
    main()
