import re
from thefuzz import fuzz

def normalize_text(text: str) -> str:
    """Normalize text by converting to lowercase, removing punctuation, and standardizing whitespace."""
    if not text:
        return ""
    result = text.lower()
    result = re.sub(r'[^\w\s]', '', result)
    result = re.sub(r'\s+', ' ', result).strip()
    return result

def fuzzy_match(model: str, text: str, threshold: int = 80) -> bool:
    if not model or not text:
        return False
    
    if " " not in model:
        for word in text.split():
            if fuzz.ratio(model, word) >= threshold:
                return True
    
    return fuzz.partial_ratio(model, text) >= threshold

def check_post_for_pen_models(submission_text: str, pen_models_to_find: list[str]) -> list[str]:
    if not submission_text or not pen_models_to_find:
        return []

    normalized_body = normalize_text(submission_text)
    found_models = []
    
    for model in pen_models_to_find:
        normalized_model = normalize_text(model)
        
        if normalized_model in normalized_body:
            # print how the match was found
            print(f"Exact match found for {model} in {submission_text}")
            found_models.append(model)
        elif fuzzy_match(normalized_model, normalized_body):
            print(f"Fuzzy match found for {model} in {submission_text}")
            found_models.append(model)
    
    return found_models 