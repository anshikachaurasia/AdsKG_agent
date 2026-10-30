SELECT d.weekday, c.clicks FROM agg_campaign_daily c JOIN dim_date d ON d.date = c.event_date WHERE c.campaign_id = 288940 ORDER BY c.clicks DESC LIMIT 1
