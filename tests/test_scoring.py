import time
from reddit_growth.scoring import score_opportunity, lexical_similarity


def test_high_intent_recent_thread_scores_higher():
    now = time.time()
    high = {"title": "Should I refinance my student loan? Any advice?", "body": "Looking for a better APR and lender comparison", "created_utc": now - 3600, "num_comments": 4, "ups": 8}
    low = {"title": "Random update", "body": "Just sharing a thought", "created_utc": now - 7*86400, "num_comments": 60, "ups": 200}
    hs, _ = score_opportunity(high, now)
    ls, _ = score_opportunity(low, now)
    assert hs > ls
    assert hs >= 60


def test_similarity():
    assert lexical_similarity("student loan refinance rates", "private student loan refinancing guide") > 0
