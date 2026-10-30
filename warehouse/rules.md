# Fixed rules for the warehouse (M1)

Written **before** any test question. Do not change these after the benchmark (M3) is frozen.

| # | Rule | Value |
|---|---|---|
| 1 | Time zone | All times are **China time (UTC+8)**. Raw `time_stamp` is Unix seconds. |
| 2 | Data window | 2017-05-06 00:00 → 2017-05-13 23:59 (8 days) |
| 3 | "Now" | **2017-05-13 23:59** (last minute of the data) |
| 4 | "Today" / "yesterday" | Today = 2017-05-13, yesterday = 2017-05-12 |
| 5 | Final daily & weekly tables | Stop at **yesterday** (2017-05-12) — like a real 1-day reporting delay |
| 6 | Hourly tables | Include today, so today's hours are **incomplete / provisional** |
| 7 | Live tables (`live_*`) | Only the **last 6 hours**: 2017-05-13 18:00 → 23:59 |
| 8 | Week | Starts on **Monday**. The data has only part of two weeks, so weekly tables carry `days_in_week`. |
| 9 | Impression / view | One row in `raw_sample` = one ad shown to one user |
| 10 | Click | `clk = 1` |
| 11 | CTR | clicks ÷ impressions |
| 12 | Suspicious click | A user with **more than 5 clicks in the same clock hour** → all their impressions/clicks in that hour are suspicious (≈ 3.6% of clicks) |
| 13 | Valid traffic (`*_valid` tables) | All traffic **minus** suspicious user-hours |
| 14 | Reach | Number of **unique users** who saw the ad (not impressions) |
| 15 | Estimated value | clicks × item price. **An estimate** — the data has no spend or revenue. |
| 16 | Missing brand | 29% of ads have no brand → `brand_id` is NULL; brand tables skip them |
| 17 | Missing user profile | 1.5M impressions have no user profile → audience fields show `'unknown'` |
| 18 | Names | IDs stay as numbers. No made-up names for brands, campaigns or placements. |
| 19 | Gender codes | 1 = male, 2 = female (from `final_gender_code`) |
