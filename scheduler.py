from datetime import date, timedelta


INTERVALS = {0: 1, 1: 2, 2: 4, 3: 7, 4: 15, 5: 30}


def interval_for_level(level: int) -> int:
    return INTERVALS[max(0, min(5, level))]


def schedule_new_word(current_level: int, rating: str) -> dict:
    today = date.today()
    if rating == "know":
        level, days, wrong, red = max(current_level, 2), 4, 0, False
    elif rating == "vague":
        level, days, wrong, red = max(current_level, 1), 2, 0, False
    elif rating == "dont_know":
        level, days, wrong, red = 0, 1, 1, True
    else:
        raise ValueError(f"Unknown new-word rating: {rating}")
    return {
        "level": level,
        "next_review_date": (today + timedelta(days=days)).isoformat(),
        "wrong_increment": wrong,
        "mark_red": red,
    }


def schedule_review(current_level: int, rating: str) -> dict:
    today = date.today()
    if rating == "forgot":
        level, days, wrong, red = max(0, current_level - 1), 1, 1, True
    elif rating == "vague":
        level, days, wrong, red = current_level, 2, 0, False
    elif rating == "remembered":
        level, wrong, red = min(5, current_level + 1), 0, False
        days = interval_for_level(level)
    elif rating == "easy":
        level, wrong, red = min(5, current_level + 2), 0, False
        days = interval_for_level(level)
    else:
        raise ValueError(f"Unknown review rating: {rating}")
    return {
        "level": level,
        "next_review_date": (today + timedelta(days=days)).isoformat(),
        "wrong_increment": wrong,
        "mark_red": red,
    }
