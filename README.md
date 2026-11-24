# Which hour does a fund price?

Pre-analysis plan, code and archived data for

> A. F. Ciftler, *Which Hour Does a Fund Price? Non-Synchronous Fund Valuation
> and the Evaluation of Forecasting Systems: Pre-Registered Evidence from
> Türkiye*, November 2026.

A mutual fund's daily price carries a date, not a time. For a fund that holds
United States shares and is valued in Istanbul, the hour of valuation decides
which New York session each published return contains. This repository
measures that hour for the 12 funds on Türkiye's fund platform whose
registered names mark them as foreign-equity funds, under a plan written
before their prices were downloaded.

Only public data are used: dated fund prices from the platform's price
service, and futures, index and exchange-rate bars from a public quote
service.

## Outcome of the four pre-registered criteria

Generated from `sonuc.json` when this copy was exported.

| | Criterion | Needed | Met in |
|---|---|---|---|
| P1 | best alignment is day *t*−1, hour between 17:00 and 19:00 Istanbul time | 7 of 12 funds | 7 |
| P2 | gain in R² of at least 0.05 over the best daily alignment, and a stable hour across the two halves of the sample | 7 | 9 |
| P3 | the late New York session of day *t*−2 enters the return dated *t* (anchor fixed at 18:00, no search over hours) | 7 | 12 |
| P4 | market beta from the daily alignment is smaller than from the hour alignment | 10 | 12 |

P1 is met exactly at its threshold. The paper says so and discusses why.

## Files

The code was written in Turkish and is published as it was run. Names are
kept so that the plan, the code and the output refer to the same things.

| File | What it is |
|---|---|
| `PLAN.md` | The pre-analysis plan, in Turkish, as committed. See "Redactions" below |
| `PLAN.en.md` | English translation of the plan, made after the analysis for readers |
| `analiz.py` | The plan's analysis. Without arguments it reads `veri/` and writes `sonuc.json`. `--indir` downloads the raw data again; `--turet` recomputes the market return series from raw bars |
| `saglamlik.py` | Checks that are **not** in the plan (placebo, exchange-rate leg, daylight-saving split). Writes `saglamlik.json` and the figure coordinates |
| `sayilar.py` | Generates every number, both tables and the figure the manuscript reads: `paper/numbers.tex` (numbers and table rows, as macros) and `paper/sekil_egri.tex` (figure coordinates) |
| `sonuc.json`, `saglamlik.json` | Output of the two analysis scripts |
| `kesif_fonu.json` | Five archived figures for the originating fund. See "Redactions" |
| `veri/` | What the analysis runs on: the fund-price downloads as received (`tefas_*.json`), the market return series (`piyasa_getirileri.json`), and the download record `INDIRME.json` |
| `paper/` | LaTeX source of the manuscript. It contains no hand-typed data figure |

A short glossary: *evren* universe, *sürücü* driver (the futures contract a
fund is paired with), *çapa* anchor hour, *kur* exchange rate, *yarı* half,
*sağlamlık* robustness, *keşif fonu* originating fund, *plan dışı* outside the
plan, *elendi* dropped.

## Reproduce

Python 3.11 and numpy are the only requirements.

```bash
pip install numpy==2.0.2
python3 analiz.py && python3 saglamlik.py && python3 sayilar.py
git diff --stat -- paper/      # prints nothing if the numbers reproduce
```

The analysis reads the archived files in `veri/`. CI repeats the three commands on
every push and fails if anything the manuscript reads has changed, then builds
the PDF and the arXiv source package.

## Market data: return series, not the vendor's bars

The futures, index and exchange-rate bars came from a public quote service
whose terms restrict redistribution, so the bar files are not in this
repository. `veri/piyasa_getirileri.json` holds what the analysis needs from
them, computed by `analiz.py --turet` and not rounded:

- `saatlik`: for each instrument and each hourly label, the return between
  that hour on consecutive days on which the hour has a bar;
- `gunluk`: daily close-to-close returns;
- `capa`: for each futures contract and day, the return from the previous New
  York close to 18:00 Istanbul time, the return from 18:00 to that day's New
  York close, and the exchange-rate return between the two 18:00 readings.

The analysis was first run on the bars and then on this file; `sonuc.json`,
`saglamlik.json` and everything the manuscript reads came out identical.
`veri/INDIRME.json` still lists the bar files, because it is the record of what
was downloaded. To start from bars, run `python3 analiz.py --indir` and then
`--turet`. The service can revise historical bars, so a fresh download is not
guaranteed to reproduce the archived series.

## What a reader cannot verify from this repository

**The order of plan and download.** The plan was committed to the author's
private working repository on 2026-11-24 at 10:11:33 (UTC+03:00) (commit `6125210`). The
download record `veri/INDIRME.json` is stamped 2026-11-24 at 10:12:53 (UTC+03:00). That
repository also holds unrelated personal records and is not public. Both
timestamps are the author's own, and this repository's history starts after
both.

**The originating fund.** The study began with one fund, which is not in the
sample. That fund is one of the assets of an anonymised dataset the paper
cites, so its identity is withheld here. The five figures the paper reports
for it are archived in `kesif_fonu.json` and cannot be regenerated from the
public files. Everything about the 12 funds in the sample can.

## Redactions

The public copy of `PLAN.md` differs from the committed plan in one way: fund
codes of the author's own holdings are replaced by `▮▮▮`. The entry for the
originating fund's price file is likewise masked in `veri/INDIRME.json`, and
that file is not in `veri/`. Nothing else was changed.

## Licence

Code: MIT (`LICENSE`). The fund-price files in `veri/` are public data from
the fund platform, archived as received so that the analysis can be repeated;
the return series are derived from a quote service's data. Neither is covered
by the licence, and both remain subject to their sources' terms.

This is a measurement study. Nothing in it is investment advice.
