from automation.opportunity_monitor import config


def test_edgewater_origin_is_a_lat_lon_pair():
    lat, lon = config.EDGEWATER_ORIGIN
    assert 38.0 < lat < 40.0
    assert -78.0 < lon < -75.0


def test_max_commute_radius_is_positive():
    assert config.MAX_COMMUTE_RADIUS_MILES > 0


def test_red_flag_keywords_is_nonempty_list_of_strings():
    assert len(config.RED_FLAG_KEYWORDS) > 0
    assert all(isinstance(k, str) for k in config.RED_FLAG_KEYWORDS)


def test_target_career_pages_is_a_list():
    assert isinstance(config.TARGET_CAREER_PAGES, list)


def test_fit_score_alert_threshold():
    assert config.FIT_SCORE_ALERT_THRESHOLD == 80
