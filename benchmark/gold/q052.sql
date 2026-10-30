SELECT SUM(e.is_click) AS clicks FROM fact_ad_events e JOIN dim_user u ON u.user_id = e.user_id WHERE e.brand_id = 268781 AND u.spending_level = 3 AND e.event_date <= '2017-05-12'
