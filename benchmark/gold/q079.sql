SELECT COUNT(DISTINCT e.user_id) AS unique_users FROM fact_ad_events e JOIN dim_user u ON u.user_id = e.user_id WHERE e.campaign_id = 258678 AND u.gender = 'male' AND e.event_date = '2017-05-09'
