SELECT SUM(e.is_click) / COUNT(*) AS ctr FROM fact_ad_events e JOIN dim_user u ON u.user_id = e.user_id WHERE e.campaign_id = 134678 AND u.shopping_depth = 3 AND e.event_date = '2017-05-09'
