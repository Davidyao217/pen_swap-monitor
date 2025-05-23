import os

# Load target models from env, lowercase for matching
TARGETS = [t.strip().lower() for t in os.getenv("TARGET_MODELS", "").split(",") if t.strip()]

WTS_KEYWORD = "wts"

def matches(submission) -> bool:
    text = f"{submission.title} {getattr(submission, 'selftext', '')}".lower()
    if WTS_KEYWORD not in text:
        return False
    return any(model in text for model in TARGETS)