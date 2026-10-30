-- M1: build the 28 warehouse tables from the 3 raw tables.
-- Raw tables (already loaded): raw_sample, ad_feature, user_profile
-- Rules used here are written in warehouse/rules.md


-- =====================================================================
-- STEP 1. DIMENSION TABLES ("who / what" lookup tables)
-- =====================================================================

-- 1. One row per ad
CREATE OR REPLACE TABLE dim_ad AS
SELECT
    adgroup_id  AS ad_id,
    campaign_id,
    customer    AS advertiser_id,
    brand       AS brand_id,       -- NULL for 29% of ads
    cate_id     AS category_id,
    price
FROM ad_feature;

-- 2. One row per campaign
CREATE OR REPLACE TABLE dim_campaign AS
SELECT
    campaign_id,
    advertiser_id,
    COUNT(*) AS num_ads
FROM dim_ad
GROUP BY campaign_id, advertiser_id;

-- 3. One row per advertiser
CREATE OR REPLACE TABLE dim_advertiser AS
SELECT
    advertiser_id,
    COUNT(DISTINCT campaign_id) AS num_campaigns,
    COUNT(*)                    AS num_ads
FROM dim_ad
GROUP BY advertiser_id;

-- 4. One row per user (readable column names)
CREATE OR REPLACE TABLE dim_user AS
SELECT
    user_id,
    CASE final_gender_code WHEN 1 THEN 'male' WHEN 2 THEN 'female' ELSE 'unknown' END AS gender,
    age_level,                       -- 0 (youngest) .. 6
    pvalue_level         AS spending_level,   -- 1 low .. 3 high, NULL = unknown
    shopping_level       AS shopping_depth,   -- 1 light .. 3 heavy
    occupation           AS is_student,       -- 1 = student
    new_user_class_level AS city_level,       -- 1 .. 4
    cms_segid            AS micro_group_id,
    cms_group_id         AS group_id
FROM user_profile;

-- 5. One row per ad placement (where on the site the ad was shown)
CREATE OR REPLACE TABLE dim_placement AS
SELECT
    pid      AS placement_id,
    COUNT(*) AS total_impressions
FROM raw_sample
GROUP BY pid;


-- =====================================================================
-- STEP 2. EVENT TABLE (one row per ad shown) + suspicious-click list
-- =====================================================================

-- 6. Every impression, with China time and ad details already joined in
CREATE OR REPLACE TABLE fact_ad_events AS
SELECT
    to_timestamp(r.time_stamp) AT TIME ZONE 'Asia/Shanghai'                      AS event_time,
    CAST(to_timestamp(r.time_stamp) AT TIME ZONE 'Asia/Shanghai' AS DATE)        AS event_date,
    date_trunc('hour', to_timestamp(r.time_stamp) AT TIME ZONE 'Asia/Shanghai')  AS event_hour,
    r.user_id,
    r.adgroup_id AS ad_id,
    a.campaign_id,
    a.advertiser_id,
    a.brand_id,
    a.category_id,
    r.pid        AS placement_id,
    r.clk        AS is_click,
    a.price
FROM raw_sample r
JOIN dim_ad a ON a.ad_id = r.adgroup_id;

-- 7. User-hours with more than 5 clicks (rule 12) = suspicious
CREATE OR REPLACE TABLE ref_suspicious_user_hours AS
SELECT
    user_id,
    event_hour,
    SUM(is_click) AS clicks_in_hour
FROM fact_ad_events
GROUP BY user_id, event_hour
HAVING SUM(is_click) > 5;

-- Helper view: events with suspicious user-hours removed (not counted as a table)
CREATE OR REPLACE VIEW v_valid_events AS
SELECT e.*
FROM fact_ad_events e
ANTI JOIN ref_suspicious_user_hours s
    ON s.user_id = e.user_id AND s.event_hour = e.event_hour;

-- 8. Calendar: one row per day in the data
CREATE OR REPLACE TABLE dim_date AS
SELECT
    event_date                          AS date,
    dayname(event_date)                 AS weekday,
    date_trunc('week', event_date)      AS week_start,   -- Monday
    event_date = DATE '2017-05-13'      AS is_today,
    event_date < DATE '2017-05-13'      AS is_final       -- final = up to yesterday
FROM fact_ad_events
GROUP BY event_date;


-- =====================================================================
-- STEP 3. GRAIN FAMILY: same numbers at hourly / daily / weekly level
--   hourly  = includes today (today is incomplete)
--   daily / weekly = FINAL, stop at yesterday 2017-05-12
-- =====================================================================

-- 9. Ad x hour
CREATE OR REPLACE TABLE agg_ad_hourly AS
SELECT
    event_hour, ad_id, campaign_id,
    COUNT(*)                 AS impressions,
    SUM(is_click)            AS clicks,
    SUM(is_click) / COUNT(*) AS ctr,
    SUM(is_click * price)    AS est_value
FROM fact_ad_events
GROUP BY event_hour, ad_id, campaign_id;

-- 10. Ad x day (final)
CREATE OR REPLACE TABLE agg_ad_daily AS
SELECT
    event_date, ad_id, campaign_id,
    COUNT(*)                 AS impressions,
    SUM(is_click)            AS clicks,
    SUM(is_click) / COUNT(*) AS ctr,
    SUM(is_click * price)    AS est_value
FROM fact_ad_events
WHERE event_date <= DATE '2017-05-12'
GROUP BY event_date, ad_id, campaign_id;

-- 11. Ad x week (final)
CREATE OR REPLACE TABLE agg_ad_weekly AS
SELECT
    date_trunc('week', event_date) AS week_start, ad_id, campaign_id,
    COUNT(DISTINCT event_date)     AS days_in_week,
    COUNT(*)                       AS impressions,
    SUM(is_click)                  AS clicks,
    SUM(is_click) / COUNT(*)       AS ctr,
    SUM(is_click * price)          AS est_value
FROM fact_ad_events
WHERE event_date <= DATE '2017-05-12'
GROUP BY week_start, ad_id, campaign_id;

-- 12. Campaign x hour
CREATE OR REPLACE TABLE agg_campaign_hourly AS
SELECT
    event_hour, campaign_id, advertiser_id,
    COUNT(*)                 AS impressions,
    SUM(is_click)            AS clicks,
    SUM(is_click) / COUNT(*) AS ctr,
    SUM(is_click * price)    AS est_value
FROM fact_ad_events
GROUP BY event_hour, campaign_id, advertiser_id;

-- 13. Campaign x day (final)
CREATE OR REPLACE TABLE agg_campaign_daily AS
SELECT
    event_date, campaign_id, advertiser_id,
    COUNT(*)                 AS impressions,
    SUM(is_click)            AS clicks,
    SUM(is_click) / COUNT(*) AS ctr,
    SUM(is_click * price)    AS est_value
FROM fact_ad_events
WHERE event_date <= DATE '2017-05-12'
GROUP BY event_date, campaign_id, advertiser_id;

-- 14. Campaign x week (final)
CREATE OR REPLACE TABLE agg_campaign_weekly AS
SELECT
    date_trunc('week', event_date) AS week_start, campaign_id, advertiser_id,
    COUNT(DISTINCT event_date)     AS days_in_week,
    COUNT(*)                       AS impressions,
    SUM(is_click)                  AS clicks,
    SUM(is_click) / COUNT(*)       AS ctr,
    SUM(is_click * price)          AS est_value
FROM fact_ad_events
WHERE event_date <= DATE '2017-05-12'
GROUP BY week_start, campaign_id, advertiser_id;

-- 15. Advertiser x day (final)
CREATE OR REPLACE TABLE agg_advertiser_daily AS
SELECT
    event_date, advertiser_id,
    COUNT(*)                 AS impressions,
    SUM(is_click)            AS clicks,
    SUM(is_click) / COUNT(*) AS ctr,
    SUM(is_click * price)    AS est_value
FROM fact_ad_events
WHERE event_date <= DATE '2017-05-12'
GROUP BY event_date, advertiser_id;

-- 16. Brand x day (final; ads with no brand are skipped)
CREATE OR REPLACE TABLE agg_brand_daily AS
SELECT
    event_date, brand_id,
    COUNT(*)                 AS impressions,
    SUM(is_click)            AS clicks,
    SUM(is_click) / COUNT(*) AS ctr,
    SUM(is_click * price)    AS est_value
FROM fact_ad_events
WHERE event_date <= DATE '2017-05-12' AND brand_id IS NOT NULL
GROUP BY event_date, brand_id;

-- 17. Category x day (final)
CREATE OR REPLACE TABLE agg_category_daily AS
SELECT
    event_date, category_id,
    COUNT(*)                 AS impressions,
    SUM(is_click)            AS clicks,
    SUM(is_click) / COUNT(*) AS ctr,
    SUM(is_click * price)    AS est_value
FROM fact_ad_events
WHERE event_date <= DATE '2017-05-12'
GROUP BY event_date, category_id;

-- 18. Placement x day (final)
CREATE OR REPLACE TABLE agg_placement_daily AS
SELECT
    event_date, placement_id,
    COUNT(*)                 AS impressions,
    SUM(is_click)            AS clicks,
    SUM(is_click) / COUNT(*) AS ctr,
    SUM(is_click * price)    AS est_value
FROM fact_ad_events
WHERE event_date <= DATE '2017-05-12'
GROUP BY event_date, placement_id;


-- =====================================================================
-- STEP 4. TRAFFIC-QUALITY FAMILY: same as above but suspicious traffic removed
-- =====================================================================

-- 19. Ad x day, valid traffic only (final)
CREATE OR REPLACE TABLE agg_ad_daily_valid AS
SELECT
    event_date, ad_id, campaign_id,
    COUNT(*)                 AS impressions,
    SUM(is_click)            AS clicks,
    SUM(is_click) / COUNT(*) AS ctr,
    SUM(is_click * price)    AS est_value
FROM v_valid_events
WHERE event_date <= DATE '2017-05-12'
GROUP BY event_date, ad_id, campaign_id;

-- 20. Campaign x hour, valid traffic only
CREATE OR REPLACE TABLE agg_campaign_hourly_valid AS
SELECT
    event_hour, campaign_id, advertiser_id,
    COUNT(*)                 AS impressions,
    SUM(is_click)            AS clicks,
    SUM(is_click) / COUNT(*) AS ctr,
    SUM(is_click * price)    AS est_value
FROM v_valid_events
GROUP BY event_hour, campaign_id, advertiser_id;

-- 21. Campaign x day, valid traffic only (final)
CREATE OR REPLACE TABLE agg_campaign_daily_valid AS
SELECT
    event_date, campaign_id, advertiser_id,
    COUNT(*)                 AS impressions,
    SUM(is_click)            AS clicks,
    SUM(is_click) / COUNT(*) AS ctr,
    SUM(is_click * price)    AS est_value
FROM v_valid_events
WHERE event_date <= DATE '2017-05-12'
GROUP BY event_date, campaign_id, advertiser_id;


-- =====================================================================
-- STEP 5. REACH FAMILY: unique PEOPLE, not impressions
-- (unique users cannot be added up across days, so these are separate tables)
-- =====================================================================

-- 22. Campaign x day: unique users (final)
CREATE OR REPLACE TABLE reach_campaign_daily AS
SELECT
    event_date, campaign_id,
    COUNT(DISTINCT user_id)                                    AS unique_users,
    COUNT(DISTINCT CASE WHEN is_click = 1 THEN user_id END)    AS unique_clickers
FROM fact_ad_events
WHERE event_date <= DATE '2017-05-12'
GROUP BY event_date, campaign_id;

-- 23. Campaign, whole final period (2017-05-06 .. 2017-05-12)
CREATE OR REPLACE TABLE reach_campaign_total AS
SELECT
    campaign_id,
    COUNT(DISTINCT user_id)                                    AS unique_users,
    COUNT(DISTINCT CASE WHEN is_click = 1 THEN user_id END)    AS unique_clickers,
    COUNT(*) / COUNT(DISTINCT user_id)                         AS avg_frequency
FROM fact_ad_events
WHERE event_date <= DATE '2017-05-12'
GROUP BY campaign_id;

-- 24. Brand x day: unique users (final)
CREATE OR REPLACE TABLE reach_brand_daily AS
SELECT
    event_date, brand_id,
    COUNT(DISTINCT user_id)                                    AS unique_users,
    COUNT(DISTINCT CASE WHEN is_click = 1 THEN user_id END)    AS unique_clickers
FROM fact_ad_events
WHERE event_date <= DATE '2017-05-12' AND brand_id IS NOT NULL
GROUP BY event_date, brand_id;


-- =====================================================================
-- STEP 6. AUDIENCE: campaign split by gender and age (final)
-- =====================================================================

-- 25. Campaign x day x gender x age
CREATE OR REPLACE TABLE agg_campaign_daily_by_audience AS
SELECT
    e.event_date, e.campaign_id,
    COALESCE(u.gender, 'unknown')            AS gender,
    COALESCE(CAST(u.age_level AS VARCHAR), 'unknown') AS age_level,
    COUNT(*)                                 AS impressions,
    SUM(e.is_click)                          AS clicks,
    SUM(e.is_click) / COUNT(*)               AS ctr
FROM fact_ad_events e
LEFT JOIN dim_user u ON u.user_id = e.user_id
WHERE e.event_date <= DATE '2017-05-12'
GROUP BY ALL;


-- =====================================================================
-- STEP 7. FRESHNESS FAMILY: LIVE tables = last 6 hours only
-- (2017-05-13 18:00 .. 23:59, incomplete day)
-- =====================================================================

-- 26. Ad, last 6 hours
CREATE OR REPLACE TABLE live_ad_last6h AS
SELECT
    ad_id, campaign_id,
    COUNT(*)                 AS impressions,
    SUM(is_click)            AS clicks,
    SUM(is_click) / COUNT(*) AS ctr,
    SUM(is_click * price)    AS est_value
FROM fact_ad_events
WHERE event_time >= TIMESTAMP '2017-05-13 18:00:00'
GROUP BY ad_id, campaign_id;

-- 27. Campaign, last 6 hours
CREATE OR REPLACE TABLE live_campaign_last6h AS
SELECT
    campaign_id, advertiser_id,
    COUNT(*)                 AS impressions,
    SUM(is_click)            AS clicks,
    SUM(is_click) / COUNT(*) AS ctr,
    SUM(is_click * price)    AS est_value
FROM fact_ad_events
WHERE event_time >= TIMESTAMP '2017-05-13 18:00:00'
GROUP BY campaign_id, advertiser_id;

-- 28. Campaign unique users, last 6 hours
CREATE OR REPLACE TABLE live_reach_campaign_last6h AS
SELECT
    campaign_id,
    COUNT(DISTINCT user_id)                                    AS unique_users,
    COUNT(DISTINCT CASE WHEN is_click = 1 THEN user_id END)    AS unique_clickers
FROM fact_ad_events
WHERE event_time >= TIMESTAMP '2017-05-13 18:00:00'
GROUP BY campaign_id;
