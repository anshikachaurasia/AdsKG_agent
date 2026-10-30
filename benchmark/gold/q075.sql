SELECT SUM(c.clicks) AS clicks FROM agg_campaign_daily c JOIN dim_date d ON d.date = c.event_date WHERE c.campaign_id = 298353 AND d.weekday IN ('Saturday', 'Sunday')
