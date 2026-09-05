from reddit_growth.drafter import add_utm

def test_add_utm():
    u = add_utm("https://easyloanworld.com/test/", subreddit="personalfinance", thread_id="t3_abc")
    assert "utm_source=reddit" in u
    assert "utm_medium=organic" in u
    assert "personalfinance_t3_abc" in u
