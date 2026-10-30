SELECT SUM(e.is_click) AS clicks FROM fact_ad_events e JOIN dim_user u ON u.user_id = e.user_id WHERE e.advertiser_id = 76808 AND u.city_level = 1 AND e.event_date = '2017-05-11'
