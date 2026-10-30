SELECT gender, SUM(clicks) / SUM(impressions) AS ctr FROM agg_campaign_daily_by_audience WHERE campaign_id = 101417 AND event_date = '2017-05-07' GROUP BY gender ORDER BY gender
