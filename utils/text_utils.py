import re
from thefuzz import fuzz
from typing import List # Import List for type hinting
from datetime import datetime # Ensure datetime is imported

def normalize_text(text: str) -> str:
    """Normalize text by converting to lowercase, removing punctuation, and standardizing whitespace."""
    if not text:
        return ""
    result = text.lower()
    result = re.sub(r'[^\w\s]', '', result)
    result = re.sub(r'\s+', ' ', result).strip()
    return result

def fuzzy_match(model: str, text: str, threshold: int = 90) -> bool:
    if not model or not text:
        return False
    
    if " " not in model:
        for word in text.split():
            if fuzz.ratio(model, word) >= threshold:
                return True
    
    return fuzz.partial_ratio(model, text) >= threshold

def check_post_for_pen_models(submission_text: str, pen_models_to_find: List[str]) -> List[str]:
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

def format_bolded_excerpt(text: str, terms_to_bold: list[str]) -> str:
    """
    Formats a text excerpt by bolding specified terms and merging overlapping bolded segments.

    Args:
        text: The text to format.
        terms_to_bold: A list of terms to bold within the text.

    Returns:
        The formatted text with specified terms bolded.
    """
    if not text or not terms_to_bold:
        return text

    # Find all occurrences of terms to bold, case-insensitive
    bold_indices = []
    for term in terms_to_bold:
        start_index = 0
        while start_index < len(text):
            pos = text.lower().find(term.lower(), start_index)
            if pos == -1:
                break
            bold_indices.append((pos, pos + len(term)))
            start_index = pos + 1

    if not bold_indices:
        return text

    # Sort by start index
    bold_indices.sort()

    # Merge overlapping/adjacent bold segments
    merged_bold_segments = []
    if bold_indices:
        current_start, current_end = bold_indices[0]

        for next_start, next_end in bold_indices[1:]:
            if next_start <= current_end:  # Overlap or adjacent
                current_end = max(current_end, next_end)
            else:
                merged_bold_segments.append((current_start, current_end))
                current_start, current_end = next_start, next_end
        merged_bold_segments.append((current_start, current_end))

    # Construct the result string with bolding
    result = []
    last_pos = 0
    for start, end in merged_bold_segments:
        result.append(text[last_pos:start])  # Add text before bold segment
        result.append(f"**{text[start:end]}**")  # Add bolded segment
        last_pos = end
    result.append(text[last_pos:])  # Add any remaining text

    return "".join(result)

def find_fuzzy_match_position(model: str, text: str, threshold: int = 90):
    """Find the position and matched text, prioritizing exact matches over fuzzy matches."""
    if not model or not text:
        return None
    
    # PRIORITY 1: Try case-insensitive exact match on original text first
    model_lower = model.lower()
    text_lower = text.lower()
    exact_pos = text_lower.find(model_lower)
    if exact_pos >= 0:
        return {'start': exact_pos, 'end': exact_pos + len(model), 'matched_text': text[exact_pos:exact_pos + len(model)]}
    
    # PRIORITY 2: Try normalized exact match
    normalized_model = normalize_text(model)
    normalized_text = normalize_text(text)
    normalized_pos = normalized_text.find(normalized_model)
    if normalized_pos >= 0:
        # Try to find a case-insensitive match in the original text for the normalized version
        # This is a simplified approach - look for the model with some flexibility
        words_to_find = model.split()
        text_words = text.split()
        
        for i in range(len(text_words) - len(words_to_find) + 1):
            window_words = text_words[i:i + len(words_to_find)]
            window_text = ' '.join(window_words)
            if normalize_text(window_text) == normalized_model:
                window_start = text.find(window_text)
                if window_start >= 0:
                    return {'start': window_start, 'end': window_start + len(window_text), 'matched_text': window_text}
    
    # PRIORITY 3: Only use fuzzy matching as fallback with higher threshold
    # For single words
    if " " not in normalized_model:
        words = text.split()
        current_pos = 0
        for word in words:
            if fuzz.ratio(normalized_model, normalize_text(word)) >= threshold:
                word_start = text.find(word, current_pos)
                if word_start >= 0:
                    return {'start': word_start, 'end': word_start + len(word), 'matched_text': word}
            current_pos += len(word) + 1
    
    # For multi-word models, use partial ratio with higher threshold
    if fuzz.partial_ratio(normalized_model, normalized_text) >= threshold:
        # Find the best matching substring in the original text
        best_match = None
        best_score = 0
        
        # Try different window sizes around the model length
        for window_size in range(len(model) - 3, len(model) + 10):
            if window_size <= 0:
                continue
            for i in range(len(text) - window_size + 1):
                substring = text[i:i + window_size]
                score = fuzz.partial_ratio(normalized_model, normalize_text(substring))
                if score >= threshold and score > best_score:
                    best_score = score
                    best_match = {'start': i, 'end': i + window_size, 'matched_text': substring}
        
        return best_match
    
    return None

def find_all_match_positions(model: str, text: str, threshold: int = 90):
    """Find ALL positions where a model matches in the text, both exact and fuzzy."""
    if not model or not text:
        return []
    
    matches = []
    
    # PRIORITY 1: Find all case-insensitive exact matches
    model_lower = model.lower()
    text_lower = text.lower()
    start_pos = 0
    while True:
        exact_pos = text_lower.find(model_lower, start_pos)
        if exact_pos == -1:
            break
        matches.append({
            'start': exact_pos, 
            'end': exact_pos + len(model), 
            'matched_text': text[exact_pos:exact_pos + len(model)],
            'type': 'exact'
        })
        start_pos = exact_pos + 1
    
    # If we found exact matches, prioritize those and skip fuzzy matching
    if matches:
        return matches
    
    # PRIORITY 2: Find all normalized exact matches
    normalized_model = normalize_text(model)
    normalized_text = normalize_text(text)
    
    words_to_find = model.split()
    text_words = text.split()
    
    for i in range(len(text_words) - len(words_to_find) + 1):
        window_words = text_words[i:i + len(words_to_find)]
        window_text = ' '.join(window_words)
        if normalize_text(window_text) == normalized_model:
            window_start = text.find(window_text)
            if window_start >= 0:
                # Check if we already have this match
                is_duplicate = any(
                    abs(match['start'] - window_start) < 5 for match in matches
                )
                if not is_duplicate:
                    matches.append({
                        'start': window_start, 
                        'end': window_start + len(window_text), 
                        'matched_text': window_text,
                        'type': 'normalized'
                    })
    
    # If we found normalized matches, use those
    if matches:
        return matches
    
    # PRIORITY 3: Find fuzzy matches as fallback
    # For single words
    if " " not in normalized_model:
        words = text.split()
        current_pos = 0
        for word in words:
            if fuzz.ratio(normalized_model, normalize_text(word)) >= threshold:
                word_start = text.find(word, current_pos)
                if word_start >= 0:
                    matches.append({
                        'start': word_start, 
                        'end': word_start + len(word), 
                        'matched_text': word,
                        'type': 'fuzzy'
                    })
            current_pos += len(word) + 1
    
    # For multi-word models
    elif fuzz.partial_ratio(normalized_model, normalized_text) >= threshold:
        # Find all good fuzzy matches
        for window_size in range(len(model) - 3, len(model) + 10):
            if window_size <= 0:
                continue
            for i in range(len(text) - window_size + 1):
                substring = text[i:i + window_size]
                score = fuzz.partial_ratio(normalized_model, normalize_text(substring))
                if score >= threshold:
                    # Check if we already have this match or a similar one
                    is_duplicate = any(
                        abs(match['start'] - i) < 5 for match in matches
                    )
                    if not is_duplicate:
                        matches.append({
                            'start': i, 
                            'end': i + window_size, 
                            'matched_text': substring,
                            'type': 'fuzzy'
                        })
    
    return matches

def format_discord_message(submission_title: str, combined_text: str, found_pen_models: list[str], permalink: str) -> str:
    message_parts = ["=" * 30]  # Visual separator to distinguish posts

    # Strip existing bold formatting from the text to avoid confusion
    cleaned_text = re.sub(r'\*\*(.*?)\*\*', r'\1', combined_text)

    # Collect ALL matches for all pen models
    all_matches = []
    for model in found_pen_models:
        model_matches = find_all_match_positions(model, cleaned_text)
        for match in model_matches:
            match['model'] = model  # Add which model this match belongs to
            all_matches.append(match)
    
    # Create context windows around each match
    context_windows = []
    for match in all_matches:
        start = max(0, match['start'] - 10)
        end = min(len(cleaned_text), match['end'] + 60)
        context_windows.append({
            'start': start, 
            'end': end, 
            'match': match
        })

    # Sort windows by start position
    context_windows.sort(key=lambda x: x['start'])

    # Merge overlapping windows and collect all matches
    merged_windows = []
    if context_windows:
        current_window = context_windows[0]
        current_window['matches'] = [current_window['match']]  # Initialize matches list

        for next_window in context_windows[1:]:
            if next_window['start'] <= current_window['end']:
                # Windows overlap, extend the current window and add the match
                current_window['end'] = max(current_window['end'], next_window['end'])
                current_window['matches'].append(next_window['match'])
            else:
                # No overlap, add the current window and start a new one
                merged_windows.append(current_window)
                current_window = next_window
                current_window['matches'] = [current_window['match']]  # Initialize matches list
        merged_windows.append(current_window) # Add the last window

    # Create a single concatenated excerpt line
    excerpt_parts = []
    for window_data in merged_windows:
        start, end = window_data['start'], window_data['end']
        excerpt_raw = cleaned_text[start:end].strip()
        # Remove extra whitespace and normalize spacing
        excerpt_clean = ' '.join(excerpt_raw.split())
        
        # Collect all matched text in this window for bolding
        matches_to_bold = []
        for match in window_data['matches']:
            matches_to_bold.append(match['matched_text'])
        
        # Bold the matched text within this specific excerpt
        bolded_excerpt = format_bolded_excerpt(excerpt_clean, matches_to_bold)
        excerpt_parts.append(bolded_excerpt)

    # Join all excerpts with ellipses
    if excerpt_parts:
        concatenated_excerpts = ".....".join(excerpt_parts)
        message_parts.append(f".....{concatenated_excerpts}.....")

    # Add blank line for separation
    message_parts.append("")

    # Add timestamp and permalink
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message_parts.append(f"Processed at: {current_time}")
    message_parts.append(f"<https://www.reddit.com{permalink}>")

    return "\n".join(message_parts)