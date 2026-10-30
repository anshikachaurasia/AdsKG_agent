SELECT age_level, SUM(clicks) / SUM(impressions) AS ctr FROM agg_campaign_daily_by_audience WHERE campaign_id = 71712 AND event_date = '2017-05-12' GROUP BY age_level ORDER BY age_level
