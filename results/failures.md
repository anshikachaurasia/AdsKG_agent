| Failure type | A | B | C | D | E | E_memory | All |
|---|---|---|---|---|---|---|---|
| wrong_calculation | 5 | 6 | 4 | 7 | 2 | 2 | 26 |
| missing_connecting_table | 0 | 5 | 10 | 3 | 0 | 0 | 18 |
| strict_grading | 3 | 3 | 2 | 3 | 6 | 0 | 17 |
| wrong_lookalike | 0 | 4 | 5 | 2 | 2 | 0 | 13 |
| not_sure | 0 | 0 | 1 | 2 | 6 | 4 | 13 |
| wrong_time_window | 0 | 1 | 0 | 0 | 1 | 0 | 2 |
| wrong_join | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| made_up_column | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| **wrong answers** | 8 | 19 | 23 | 17 | 17 | 7 | 91 |

**Examples (first per version and type):**

- **A / wrong_calculation** (q046, medium): For campaign 94399 yesterday, what CTR did heavy shoppers have? → Used shopping_depth = 5 instead of the correct 3 for heavy shoppers, applying the wrong filter.
- **A / strict_grading** (q052, medium): Brand 268781: clicks from users with the highest spending level, 6-12 May? → Returned a daily breakdown instead of a single total, so the format didn’t match the expected answer.
- **B / missing_connecting_table** (q045, medium): What was the CTR among heavy shoppers (shopping depth 3) for campaign 350441 on 6 May 2017? → They didn’t join dim_user to filter shopping_depth=3, instead using an aggregate audience table.
- **B / wrong_calculation** (q046, medium): For campaign 94399 yesterday, what CTR did heavy shoppers have? → Filtered on age_level='heavy_shoppers' in an aggregate table instead of using shopping_depth=3 for heavy shoppers, leading to a wrong/missing audience filter.
- **B / wrong_lookalike** (q050, medium): Brand 57197: clicks from users with the highest spending level, 6-12 May? → Used agg_brand_daily (all users) instead of joining events to dim_user to filter spending_level=3, so it counted all clicks.
- **B / strict_grading** (q069, medium): Which ad in campaign 401781 got the most clicks yesterday, and what is its price? → Returned the correct ad and price but omitted the clicks column required by the gold answer
- **B / wrong_time_window** (q099, tricky): How many clicks has campaign 390070 had today so far? → Used the live last-6h table, giving only the past 6 hours instead of today so far.
- **C / wrong_lookalike** (q038, easy): Number of campaigns for advertiser 125660? → Used agg_campaign_daily to count campaigns instead of dim_advertiser.num_campaigns, missing campaigns without daily rows and yielding 8 vs 9.
- **C / missing_connecting_table** (q044, medium): Yesterday's clicks for advertiser 179351, only ads in category 8973? → Did not join the dim_ad lookup to filter category_id, instead misusing campaign_id and agg_campaign_daily.
- **C / made_up_column** (q053, medium): Break down advertiser 56209's estimated value yesterday by product category. → They referenced a.category_id in agg_ad_daily, which doesn’t exist; category must come via a lookup (e.g., dim_ad).
- **C / wrong_calculation** (q061, medium): How many clicks did advertiser 76808 get from users in city level 1 on 11 May 2017? → Returned a constant 0 instead of summing clicks with the required joins and filters.
- **C / not_sure** (q077, medium): How many unique male users saw campaign 258700 on 6 May 2017? → Returned a dummy NULL instead of querying any tables, effectively no SQL
- **C / strict_grading** (q103, tricky): How many clicks did campaign 163082 get in the week starting Monday 8 May? → Returned only clicks without the required days_in_week column though the value was correct.
- **D / not_sure** (q045, medium): What was the CTR among heavy shoppers (shopping depth 3) for campaign 350441 on 6 May 2017? → Returned a placeholder SELECT with WHERE FALSE instead of attempting the required query
- **D / wrong_calculation** (q048, medium): For campaign 134678 on 9 May 2017, what CTR did heavy shoppers have? → Used age_level='heavy' instead of identifying heavy shoppers via shopping_depth (dim_user), applying the wrong filter for CTR.
- **D / missing_connecting_table** (q049, medium): How many clicks did brand 224935 get from high-spending users (spending level 3) from 6 to 12 May? → Did not join dim_user to filter spending_level=3, instead aggregating from agg_brand_daily without the needed user lookup.
- **D / strict_grading** (q065, medium): On which day of the week did campaign 298303 get the most clicks (6-12 May)? → Returned only the weekday without the clicks column expected by the gold answer.
- **D / wrong_lookalike** (q067, medium): On which day of the week did campaign 51757 get the most clicks (6-12 May)? → Used agg_campaign_daily_valid (valid traffic) instead of agg_campaign_daily (all clicks), changing the result.
- **E / wrong_lookalike** (q003, easy): What was the CTR of campaign 112525 on 7 May 2017? → Used agg_campaign_daily_valid instead of agg_campaign_daily, giving CTR for valid traffic rather than overall.
- **E / strict_grading** (q033, easy): Which ad placement had the higher CTR on 8 May 2017? → It found the correct top placement but omitted LIMIT 1 and returned extra columns/rows.
- **E / not_sure** (q048, medium): For campaign 134678 on 9 May 2017, what CTR did heavy shoppers have? → gave no SQL
- **E / wrong_calculation** (q074, medium): Total weekend clicks for campaign 355976 (Saturdays and Sundays, final days)? → Returned per-day rows instead of summing to the total weekend clicks.
- **E / wrong_time_window** (q104, tricky): Weekly clicks for campaign 293527, week of 8 May? → Did not filter to the week starting 2017-05-08 and returned multiple weeks instead of only that week.
- **E_memory / not_sure** (q033, easy): Which ad placement had the higher CTR on 8 May 2017? → gave no SQL
- **E_memory / wrong_calculation** (q053, medium): Break down advertiser 56209's estimated value yesterday by product category. → Used SUM(price) from fact_ad_events instead of the est_value metric from the daily aggregate for estimated value.
- **E_memory / wrong_join** (q059, medium): Which brand in category 4307 had the most clicks yesterday? → Joined brand-level totals to dim_ad on brand_id, duplicating rows per ad in the category and inflating the summed clicks.
