SELECT SUM(d.clicks) AS clicks FROM agg_ad_daily d JOIN dim_ad a ON a.ad_id = d.ad_id WHERE a.advertiser_id = 215611 AND a.category_id = 4385 AND d.event_date = '2017-05-12'
