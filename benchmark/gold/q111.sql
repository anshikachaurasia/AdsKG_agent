SELECT gender, SUM(clicks) / SUM(impressions) AS ctr FROM agg_campaign_daily_by_audience WHERE campaign_id = 7850 AND event_date = '2017-05-10' GROUP BY gender ORDER BY gender
