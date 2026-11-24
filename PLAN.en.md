# Pre-analysis plan: which hour does the price of a foreign-equity fund reflect?

> **This is a translation.** The plan was written and committed in Turkish
> (`PLAN.md`). This English version was made after the analysis so that
> readers who do not read Turkish can check the plan against the paper. Where
> the two differ, `PLAN.md` governs. Masked fund codes (`▮▮▮`) are masked in
> both. The sentence in §7 about raw downloads holds as written for the fund
> prices; for the market bars this copy holds the return series derived from
> them instead (README, "Market data").

**Written:** 2026-11-24, BEFORE the analysis. The commit of this file is its
timestamp.
**Statement of status:** while this plan was being written, the price series
of the 12 funds below were **not looked at**; only their registered names were
read from TEFAS's fund list (`fonGetir`).

This study uses **public data only** (TEFAS prices, Yahoo futures and index bars). Nothing from the personal ledger enters it.

---

## 1. Where it came from

An exploratory measurement on a single fund in a personal ledger (▮▮▮)
(H23, 3 October 2026, 500 price days): the fund's price on day T is explained
by the United States **close** of T−1 with R² = 0.15, and by the futures price
at **18:00 Istanbul time** on T−1 with R² = 0.53. The effect sits at the same
hour in both halves of the period.

This is **exploratory** and it is one fund. The plan below asks the same
question in a universe of funds unrelated to that one, with definitions fixed
in advance. **▮▮▮ does not enter the confirmatory set**; it is reported
separately, only as the "originating fund".

The ongoing H26 test (▮▮▮/▮▮▮/▮▮▮, n = 40 price days) is independent of this
plan and is **not reported** in this study.

## 2. Universe (frozen)

Funds in the TEFAS `fonGetir` list (24 November 2026) whose registered
name contains both `YABANCI` (foreign) and `HİSSE` (equity). Twelve funds:

`AOY` `AFA` `AFV` `AFS` `AFT` `GBC` `GUH` `GBG` `YAY` `ZSF` `ARE` `TMG`

A fund that gives **fewer than 150** usable price days in the window is
dropped, and the drop is reported. No other fund is added or removed.

## 3. Data and window

- **Fund price:** TEFAS `fonFiyatBilgiGetir`, dated. Return =
  ratio of two consecutive published prices − 1.
- **Driver (hourly):** Yahoo 1-hour bars, 730 days. A bar's
  timestamp is the **start** of the bar; `h` = start + 1 hour, Istanbul time
  (UTC+3), fixed.
- **Driver pairing (from the name, in advance):** a fund with `TEKNOLOJİ`
  (technology) in its name → `NQ=F`; all others → `ES=F`.
- **Exchange-rate leg:** because the fund is priced in lira, `TRY=X` at the
  same hour is added: `x = r_driver(h) + r_fx(h)`.
- **Window:** price days from the first day covered by the hourly data up to
  **2026-11-20**. The end date is fixed in this plan.
- **Halves:** the first and second half of the usable rows.

## 4. Candidates and reference

- **Candidate (h, k):** `h` = every hourly bar end common to the driver and
  exchange-rate series; `k ∈ {0, 1, 2}` trading days of lag.
  `x_t = P(day t−k, hour h) / P(day t−k−1, hour h) − 1`.
- **Trading day:** an Istanbul calendar day on which the driver series has a
  bar at that hour.
- A candidate with **n < 150** is dropped.
- **Reference (conventional alignment):** the **daily close** return of the
  cash index (`^GSPC` or `^NDX`) plus the daily return of `TRY=X`, for
  `k ∈ {0, 1, 2}`. The alignment with the **highest R²** of the three is the
  reference. This is a conservative comparison chosen in favour of the
  conventional approach.
- ΔR² is computed for each candidate on the **same rows** as the reference.

## 5. Hypotheses and criteria

**P1 — hour.** In most funds the best candidate has `k = 1` and
`h ∈ [17:00, 19:00]`. Criterion: in **at least 7** of the 12 funds.

**P2 — size and stability.** The best candidate beats the reference by
`ΔR² ≥ 0.05` **and** the best hour of each half lies within ±1 hour of the
best hour of the full sample. Criterion: both, in **at least 7 funds**.
The scan over hours is a multiple comparison; **no p-value is reported** for
P1 and P2.

**P3 — the discriminating test (NO scan over hours; anchor fixed at 18:00).**
`L_{t−2}` = the driver's return from 18:00 on day `t−2` to that day's United
States close (the late session). `E_{t−1}` = the return from the close of
`t−2` to 18:00 on `t−1`.
Regression: `fund_t = a + b_E · E_{t−1} + b_L · L_{t−2} + e`.

- If the fund prices **18:00** of `t−1`: `b_L > 0` and `b_L ≈ b_E`.
- If the fund prices the **close** of `t−1`: `L_{t−2}` is already in the
  previous day's price, so `b_L ≈ 0`.

Test: `b_L > 0`, one-sided, heteroskedasticity-robust (HC1) standard error,
α = 0.05. Criterion: significant in **at least 7 funds**. A sign test across
funds is reported as well. No exchange-rate leg is added for this test (the
exchange-rate return of the two windows cannot be defined separately); the
version with it added is given as a robustness check.

**P4 — a consequence for measurement.** The market beta estimated with the
conventional alignment is smaller than the one estimated with the best hour.
Criterion: `β_reference < β_best` in **at least 10 funds**.

## 6. Rules of interpretation (before seeing results)

- **No claim about mechanism.** What is measured is a pattern of correlation;
  the statement "the valuation hour is 18:00" is written only if regulation or
  prospectus text supports it.
- **No claim of arbitrage** unless the order cut-off time and the pricing rule
  (forward or backward) are verified. Under forward pricing the finding is a
  finding about **measurement** (non-synchronous returns, biased beta), not an
  exploitable opportunity.
- In funds whose driver is not the United States (Europe, multi-country), a
  weak result does not refute the hypothesis; it shows that the driver pairing
  is coarse. These funds are marked in the table but **not removed from the
  denominator**.
- If a criterion fails, it is reported as failed. The universe, the driver
  pairing, the window and the thresholds are not changed after the result;
  anything that changes is labelled "outside the plan".

## 7. Known limitations (in advance)

- Hourly resolution: the true moment is known to ±30 minutes.
- The United States daylight-saving change moves the cash session by one hour
  in Istanbul time; futures trade almost around the clock, so the hour label
  stays fixed.
- Yahoo bars can be revised later; the raw downloads are kept under
  `veri/` and the analysis runs from them.
- The funds' actual regional allocation is unknown; the driver is assigned
  from the name.
