SELECT d.ad_id, d.clicks, a.price FROM agg_ad_daily d JOIN dim_ad a ON a.ad_id = d.ad_id WHERE d.campaign_id = 275463 AND d.event_date = '2017-05-12' ORDER BY d.clicks DESC LIMIT 1
