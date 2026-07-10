from datetime import date, timedelta


# Successive-relearning stages tuned for vocabulary retention.
# Flow: same-day active recall for weak new words, then 1, 2, 4, 7, 15,
# 30, 60, and 120 day reviews. This keeps early reviews dense, where
# forgetting is fastest, and gradually stretches intervals after successful
# recall.
INTERVALS = {0: 1, 1: 1, 2: 2, 3: 4, 4: 7, 5: 15, 6: 30, 7: 60, 8: 120}
MAX_STAGE = max(INTERVALS)


def interval_for_stage(stage: int) -> int:
    return INTERVALS[max(0, min(MAX_STAGE, stage))]


def status_for(stage: int, times_studied: int) -> str:
    if times_studied == 0:
        return "Unseen"
    if stage <= 1:
        return "Learning"
    if stage <= 6:
        return "Reviewing"
    return "Mastered"


def _result(stage: int, days: int, wrong: int = 0, correct: bool = False) -> dict:
    return {
        "level": max(0, min(MAX_STAGE, stage)),
        "next_review_date": (date.today() + timedelta(days=days)).isoformat(),
        "wrong_increment": wrong,
        "correct": correct,
    }


def schedule_new_word(current_stage: int, rating: str) -> dict:
    if rating == "know":
        return _result(max(current_stage, 1), 1, correct=True)
    if rating == "vague":
        # A vague/unknown new word remains due today for one active-recall retry.
        return _result(0, 0)
    if rating == "dont_know":
        return _result(0, 0, wrong=1)
    raise ValueError(f"Unknown new-word rating: {rating}")


def schedule_review(current_stage: int, rating: str) -> dict:
    if rating == "forgot":
        return _result(0, 1, wrong=1)
    if rating == "vague":
        new_stage = max(0, current_stage - 1)
        return _result(new_stage, 1)
    if rating == "remembered":
        new_stage = min(MAX_STAGE, current_stage + 1)
        return _result(new_stage, interval_for_stage(new_stage), correct=True)
    if rating == "easy":
        new_stage = min(MAX_STAGE, current_stage + 2)
        return _result(new_stage, interval_for_stage(new_stage), correct=True)
    raise ValueError(f"Unknown review rating: {rating}")
