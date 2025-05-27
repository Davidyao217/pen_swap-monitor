import re
from thefuzz import fuzz
from typing import List # Import List for type hinting
from datetime import datetime # Ensure datetime is imported
from collections import defaultdict
import os
import tempfile
import threading
import shutil

# File operation lock to prevent race conditions
_file_lock = threading.Lock()

def validate_pen_name_input(name: str, max_length: int = 100) -> tuple[bool, str]:
    """
    Validate pen name input from users.
    
    Args:
        name: The pen name to validate
        max_length: Maximum allowed length
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, "Pen name cannot be empty"
    
    name = name.strip()
    
    if len(name) > max_length:
        return False, f"Pen name too long (max {max_length} characters)"
    
    # Check for dangerous characters that could break file format
    dangerous_chars = ['|', '\n', '\r', '\t']
    for char in dangerous_chars:
        if char in name:
            return False, f"Pen name cannot contain '{char}' character"
    
    return True, ""

def validate_aliases_input(aliases_str: str, max_aliases: int = 20, max_alias_length: int = 50) -> tuple[bool, str, List[str]]:
    """
    Validate and parse aliases input from users.
    
    Args:
        aliases_str: Comma-separated aliases string
        max_aliases: Maximum number of aliases allowed
        max_alias_length: Maximum length per alias
        
    Returns:
        tuple: (is_valid, error_message, parsed_aliases_list)
    """
    if not aliases_str or not aliases_str.strip():
        return False, "Aliases cannot be empty", []
    
    # Parse aliases
    raw_aliases = [alias.strip() for alias in aliases_str.split(',')]
    valid_aliases = []
    
    for alias in raw_aliases:
        if not alias:
            continue  # Skip empty aliases
            
        if len(alias) > max_alias_length:
            return False, f"Alias '{alias}' too long (max {max_alias_length} characters)", []
        
        # Check for dangerous characters
        dangerous_chars = ['|', '\n', '\r', '\t']
        for char in dangerous_chars:
            if char in alias:
                return False, f"Alias '{alias}' cannot contain '{char}' character", []
        
        valid_aliases.append(alias.lower())
    
    if len(valid_aliases) > max_aliases:
        return False, f"Too many aliases (max {max_aliases} allowed)", []
    
    if len(set(valid_aliases)) != len(valid_aliases):
        return False, "Duplicate aliases not allowed", []
    
    return True, "", valid_aliases

def atomic_write_file(file_path: str, content: str) -> bool:
    """
    Atomically write content to a file to prevent corruption.
    
    Args:
        file_path: Path to the target file
        content: Content to write
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create a temporary file in the same directory
        temp_dir = os.path.dirname(file_path)
        with tempfile.NamedTemporaryFile(
            mode='w', 
            encoding='utf-8', 
            dir=temp_dir, 
            delete=False,
            suffix='.tmp'
        ) as temp_file:
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())  # Ensure data is written to disk
            temp_path = temp_file.name
        
        # Atomically replace the original file
        shutil.move(temp_path, file_path)
        return True
        
    except Exception as e:
        print(f"Error in atomic write to {file_path}: {e}")
        # Clean up temp file if it exists
        try:
            if 'temp_path' in locals():
                os.unlink(temp_path)
        except:
            pass
        return False

class BidirectionalMap:
    def __init__(self):
        # Maps one key to a set of many values
        self._one_to_many = {}
        # Maps many values back to one key
        self._many_to_one = {}
    
    def add(self, key, value):
        """
        Add a bidirectional mapping between key and value, ensuring data consistency.
        If value is already mapped to another key, it will be remapped to this key.
        """
        # Ensure consistent string type and normalization
        key = str(key).strip()
        value = str(value).strip().lower()
        
        # Check if value is already mapped to a different key
        if value in self._many_to_one and self._many_to_one[value] != key:
            old_key = self._many_to_one[value]
            print(f"Warning: Value '{value}' already mapped to '{old_key}', remapping to '{key}'")
            # Remove from old key's set if it exists
            if old_key in self._one_to_many and value in self._one_to_many[old_key]:
                self._one_to_many[old_key].remove(value)
                # Clean up empty sets
                if not self._one_to_many[old_key]:
                    del self._one_to_many[old_key]
        
        # Add to one-to-many mapping
        if key not in self._one_to_many:
            self._one_to_many[key] = set()
        self._one_to_many[key].add(value)
        
        # Add to many-to-one mapping
        self._many_to_one[value] = key
    
    def get_values(self, key):
        """Get all values associated with a key."""
        self._auto_repair()  # Ensure map is consistent before access
        return self._one_to_many.get(key, set())
    
    def get_key(self, value):
        """Get the key associated with a value."""
        self._auto_repair()  # Ensure map is consistent before access
        return self._many_to_one.get(value)
    
    def keys(self):
        """Returns all unique keys in the one-to-many mapping."""
        self._auto_repair()  # Ensure map is consistent before access
        return self._one_to_many.keys()
    
    def values(self):
        """Returns all unique values in the many-to-one mapping."""
        self._auto_repair()  # Ensure map is consistent before access
        return self._many_to_one.keys()
    
    def items(self):
        """Returns all key-value pairs as a list of tuples."""
        self._auto_repair()  # Ensure map is consistent before access
        result = []
        for key in self._one_to_many:
            for value in self._one_to_many[key]:
                result.append((key, value))
        return result
    
    def validate(self):
        """
        Validate and repair the bidirectional map for consistency.
        Returns list of issues fixed.
        """
        issues_fixed = []
        
        # Check for values in many-to-one that aren't in one-to-many
        for value, key in list(self._many_to_one.items()):
            if key not in self._one_to_many:
                # Key is missing, add it with this value
                self._one_to_many[key] = {value}
                issues_fixed.append(f"Added missing key '{key}' for value '{value}'")
            elif value not in self._one_to_many[key]:
                # Value is missing from key's set
                self._one_to_many[key].add(value)
                issues_fixed.append(f"Added missing value '{value}' to key '{key}'")
        
        # Check for orphaned keys (keys with empty value sets)
        for key in list(self._one_to_many.keys()):
            if not self._one_to_many[key]:
                del self._one_to_many[key]
                issues_fixed.append(f"Removed orphaned key '{key}' with no values")
        
        # Check for values in one-to-many that aren't in many-to-one
        for key, values in list(self._one_to_many.items()):
            for value in list(values):
                if value not in self._many_to_one:
                    self._many_to_one[value] = key
                    issues_fixed.append(f"Added missing mapping from value '{value}' to key '{key}'")
                elif self._many_to_one[value] != key:
                    # Value maps to a different key than expected
                    correct_key = self._many_to_one[value]
                    self._one_to_many[key].remove(value)
                    issues_fixed.append(f"Fixed inconsistency: value '{value}' mapped to '{correct_key}', not '{key}'")
        
        return issues_fixed
    
    def _auto_repair(self):
        """Automatically repair the map if needed, with minimal logging."""
        issues = self.validate()
        if issues:
            print(f"Auto-repaired {len(issues)} map issues")
    
    def repair_from_file(self, file_path):
        """
        Completely rebuild the map from the source file to ensure consistency.
        Returns number of entries loaded.
        """
        # Clear existing data
        self._one_to_many.clear()
        self._many_to_one.clear()
        
        entries_loaded = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '|' not in line:
                        continue
                    
                    formal_name, aliases_str = line.split('|', 1)
                    formal_name = formal_name.strip()
                    
                    if not formal_name:
                        continue
                    
                    # Parse aliases
                    aliases = [alias.strip().lower() for alias in aliases_str.split(',') if alias.strip()]
                    
                    # Add to map
                    for alias in aliases:
                        self.add(formal_name, alias)
                    
                    entries_loaded += 1
            
            print(f"Rebuilt map from file with {entries_loaded} entries")
            
        except Exception as e:
            print(f"Error rebuilding map from file: {e}")
        
        return entries_loaded
    
    def __repr__(self):
        return f"BidirectionalMap with {len(self._one_to_many)} keys and {len(self._many_to_one)} values"

# Get the path to the pen aliases file
def get_aliases_file_path():
    """Get the absolute path to the pen aliases file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    main_dir = os.path.dirname(current_dir)  # Go up from utils/ to main/
    return os.path.join(main_dir, 'pen_aliases.txt')

def get_monitoring_file_path():
    """Get the absolute path to the monitoring list file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    main_dir = os.path.dirname(current_dir)  # Go up from utils/ to main/
    return os.path.join(main_dir, 'monitoring_list.txt')

def load_pen_aliases_from_file(file_path: str) -> BidirectionalMap:
    """
    Load pen aliases from a text file.
    File format: formal_name|alias1,alias2,alias3
    """
    pen_map = BidirectionalMap()
    
    if not os.path.exists(file_path):
        print(f"Creating new pen aliases file at {file_path}")
        # Create empty file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# Fountain Pen Aliases\n")
            f.write("# Format: formal_name|alias1,alias2,alias3\n\n")
        return pen_map
    
    try:
        print(f"Loading pen aliases from file: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):  # Skip empty lines and comments
                    continue
                
                if '|' not in line:
                    print(f"Warning: Invalid format on line {line_num}: {line}")
                    continue
                
                formal_name, aliases_str = line.split('|', 1)
                formal_name = formal_name.strip()
                
                if not formal_name:
                    print(f"Warning: Empty formal name on line {line_num}")
                    continue
                
                # Parse aliases (comma-separated)
                aliases = [alias.strip().lower() for alias in aliases_str.split(',') if alias.strip()]
                print(f"Loading line {line_num}: '{formal_name}' with {len(aliases)} aliases")
                
                # Add to mapping
                for alias in aliases:
                    pen_map.add(formal_name, alias)
        
        # Validate the map for consistency
        issues_fixed = pen_map.validate()
        if issues_fixed:
            print(f"Fixed {len(issues_fixed)} consistency issues in the pen map:")
            for issue in issues_fixed:
                print(f"  - {issue}")
                
        all_keys = sorted(list(pen_map.keys()))
        print(f"Loaded {len(all_keys)} pens with aliases from {file_path}")
        print(f"Pens loaded: {all_keys}")
    except Exception as e:
        print(f"Error loading pen aliases from {file_path}: {e}")
    
    return pen_map

def save_pen_aliases_to_file(pen_map: BidirectionalMap, file_path: str):
    """
    Save pen aliases to a text file using atomic writes.
    File format: formal_name|alias1,alias2,alias3
    """
    try:
        with _file_lock:
            # Build content in memory first
            lines = []
            for formal_name in sorted(pen_map.keys()):
                aliases = sorted(pen_map.get_values(formal_name))
                aliases_str = ','.join(aliases)
                lines.append(f"{formal_name}|{aliases_str}\n")
            
            content = ''.join(lines)
            
            # Atomically write the file
            if atomic_write_file(file_path, content):
                print(f"✅ Saved {len(pen_map.keys())} pens to {file_path}")
            else:
                print(f"❌ Failed to save pen aliases to {file_path}")
                
    except Exception as e:
        print(f"❌ Error saving pen aliases to {file_path}: {e}")

# Initialize the pen names mapping from file
pen_names_map = load_pen_aliases_from_file(get_aliases_file_path())

def find_matching_pen_names(user_input: str, max_results: int = 4, threshold: int = 75) -> List[str]:
    """
    Find formal pen names that best match the user input using fuzzy matching.
    Returns a list of formal pen names sorted by match quality.
    """
    if not user_input:
        return []
    
    user_input_normalized = normalize_text(user_input)
    user_input_lower = user_input.lower().strip()
    scores = {}
    
    # For short inputs, increase the threshold to avoid false matches
    if len(user_input) <= 4:
        threshold = max(threshold, 85)  # Use at least 85% threshold for short inputs
    
    # Calculate the best fuzzy match score for each formal pen name
    for formal_name in pen_names_map.keys():
        best_score = 0
        match_type = "fuzzy"  # Track what type of match this is
        
        # PRIORITY 1: Check for exact case-insensitive match with formal name
        if formal_name.lower() == user_input_lower:
            best_score = 100
            match_type = "exact_formal"
        
        # PRIORITY 2: Check for exact case-insensitive match with any alias
        if best_score < 100:
            casual_names = pen_names_map.get_values(formal_name)
            for casual_name in casual_names:
                if casual_name.lower() == user_input_lower:
                    best_score = 99
                    match_type = "exact_alias"
                    break
        
        # PRIORITY 3: Check for normalized exact match with formal name
        if best_score < 99:
            formal_normalized = normalize_text(formal_name)
            if formal_normalized == user_input_normalized:
                best_score = 98
                match_type = "normalized_formal"
        
        # PRIORITY 4: Check for normalized exact match with any alias
        if best_score < 98:
            casual_names = pen_names_map.get_values(formal_name)
            for casual_name in casual_names:
                casual_normalized = normalize_text(casual_name)
                if casual_normalized == user_input_normalized:
                    best_score = 97
                    match_type = "normalized_alias"
                    break
                # Additional check: match exact word
                elif casual_normalized.split() and user_input_normalized in casual_normalized.split():
                    best_score = 96
                    match_type = "exact_word_match"
                    break
        
        # PRIORITY 5: Check for exact word match in formal name
        if best_score < 96:
            formal_normalized = normalize_text(formal_name)
            formal_words = formal_normalized.split()
            if user_input_normalized in formal_words:
                best_score = 95
                match_type = "formal_word_match"
        
        # PRIORITY 6: Fuzzy matching as fallback
        if best_score < 95:
            casual_names = pen_names_map.get_values(formal_name)
            
            # Check aliases first
            for casual_name in casual_names:
                casual_normalized = normalize_text(casual_name)
                
                # Calculate length difference
                length_diff = len(user_input_normalized) - len(casual_normalized)
                
                # Exact substring match has higher priority for short inputs
                if len(user_input) <= 4 and user_input_normalized in casual_normalized:
                    # Only count as high match if it's a standalone word
                    if user_input_normalized in casual_normalized.split():
                        # Give higher score for standalone word
                        score = 94
                    else:
                        # Substring match but not a word - lower priority
                        words = casual_normalized.split()
                        # Check if any word starts with the input
                        if any(word.startswith(user_input_normalized) for word in words):
                            score = 90
                        else:
                            # Penalize substring matches that aren't word boundaries
                            score = 80
                else:
                    # Be much more strict about partial matches when input is longer
                    if length_diff > 5:  # User input is significantly longer
                        # Only use ratio score, no partial matching
                        ratio_score = fuzz.ratio(user_input_normalized, casual_normalized)
                        # Apply a strong penalty for length differences
                        penalty_factor = max(0.5, 1.0 - (length_diff * 0.05))
                        score = ratio_score * penalty_factor
                    elif length_diff > 0:  # User input is slightly longer
                        # Use both ratio and partial, but with penalty
                        ratio_score = fuzz.ratio(user_input_normalized, casual_normalized)
                        partial_score = fuzz.partial_ratio(user_input_normalized, casual_normalized)
                        base_score = max(ratio_score, partial_score)
                        penalty_factor = max(0.8, 1.0 - (length_diff * 0.1))
                        score = base_score * penalty_factor
                    else:  # User input is shorter or equal length
                        # Normal fuzzy matching
                        ratio_score = fuzz.ratio(user_input_normalized, casual_normalized)
                        partial_score = fuzz.partial_ratio(user_input_normalized, casual_normalized)
                        score = max(ratio_score, partial_score)
                
                best_score = max(best_score, score)
            
            # Also check against the formal name itself with same logic
            formal_normalized = normalize_text(formal_name)
            
            # Exact substring match has higher priority for short inputs
            if len(user_input) <= 4 and user_input_normalized in formal_normalized:
                # Only count as high match if it's a standalone word
                if user_input_normalized in formal_normalized.split():
                    # Give higher score for standalone word
                    formal_score = 93  # Slightly lower than alias word match
                else:
                    # Substring match but not a word - lower priority
                    words = formal_normalized.split()
                    # Check if any word starts with the input
                    if any(word.startswith(user_input_normalized) for word in words):
                        formal_score = 89
                    else:
                        # Penalize substring matches that aren't word boundaries
                        formal_score = 79
            else:
                # Length difference handling
                length_diff = len(user_input_normalized) - len(formal_normalized)
                
                if length_diff > 5:  # User input is significantly longer
                    ratio_score = fuzz.ratio(user_input_normalized, formal_normalized)
                    penalty_factor = max(0.5, 1.0 - (length_diff * 0.05))
                    formal_score = ratio_score * penalty_factor
                elif length_diff > 0:  # User input is slightly longer
                    ratio_score = fuzz.ratio(user_input_normalized, formal_normalized)
                    partial_score = fuzz.partial_ratio(user_input_normalized, formal_normalized)
                    base_score = max(ratio_score, partial_score)
                    penalty_factor = max(0.8, 1.0 - (length_diff * 0.1))
                    formal_score = base_score * penalty_factor
                else:  # User input is shorter or equal length
                    ratio_score = fuzz.ratio(user_input_normalized, formal_normalized)
                    partial_score = fuzz.partial_ratio(user_input_normalized, formal_normalized)
                    formal_score = max(ratio_score, partial_score)
                
            best_score = max(best_score, formal_score)
        
        if best_score >= threshold:
            scores[formal_name] = (best_score, match_type)
    
    # Sort by score (highest first), then by match type priority
    match_type_priority = {
        "exact_formal": 1,
        "exact_alias": 2, 
        "normalized_formal": 3,
        "normalized_alias": 4,
        "exact_word_match": 5,
        "formal_word_match": 6,
        "fuzzy": 7
    }
    
    sorted_matches = sorted(
        scores.items(), 
        key=lambda x: (-x[1][0], match_type_priority.get(x[1][1], 8))
    )
    
    return [formal_name for formal_name, (score, match_type) in sorted_matches[:max_results]]

def get_all_search_terms_for_pens(formal_names: List[str]) -> List[str]:
    """
    Get all casual names and aliases for the given formal pen names.
    This is what we'll actually search for in posts.
    """
    search_terms = []
    
    for formal_name in formal_names:
        # Add the formal name itself
        search_terms.append(formal_name)
        # Add all casual names/aliases
        casual_names = pen_names_map.get_values(formal_name)
        search_terms.extend(casual_names)
    
    return list(set(search_terms))  # Remove duplicates

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

def format_bolded_excerpt(text: str, terms_to_bold: List[str]) -> str:
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

def truncate_discord_message(message: str, max_length: int = 2000) -> str:
    """
    Safely truncate a Discord message to fit within character limits.
    
    Args:
        message: The message to potentially truncate
        max_length: Maximum allowed character length (Discord limit is 2000)
        
    Returns:
        str: The message, truncated if necessary with a clear indication
    """
    if len(message) <= max_length:
        return message
    
    # Reserve space for truncation indicator
    truncation_text = "\n\n... [Message truncated due to length limit]"
    available_length = max_length - len(truncation_text)
    
    if available_length < 100:  # Too short to be useful
        return "❌ Message too long to display properly."
    
    # Try to truncate at a natural breaking point (line break)
    truncated = message[:available_length]
    
    # Look for the last complete line
    last_newline = truncated.rfind('\n')
    if last_newline > available_length // 2:  # If we find a reasonable break point
        truncated = truncated[:last_newline]
    
    return truncated + truncation_text

def format_discord_message(submission_title: str, combined_text: str, found_pen_models: List[str], permalink: str) -> str:
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

    # Join all parts and truncate if necessary
    full_message = "\n".join(message_parts)
    return truncate_discord_message(full_message)

def interactive_pen_selection(user_input: str) -> List[str]:
    """
    Interactive function that takes user input, finds matching pen names,
    asks for confirmation, and returns the final search terms.
    """
    print(f"\nSearching for: '{user_input}'")
    
    # Find matching formal pen names
    matches = find_matching_pen_names(user_input)
    
    if not matches:
        print("❌ No matching pen names found.")
        return []
    
    print(f"\n📝 Found {len(matches)} potential matches:")
    for i, formal_name in enumerate(matches, 1):
        casual_names = list(pen_names_map.get_values(formal_name))
        print(f"{i}. {formal_name}")
        print(f"   Aliases: {', '.join(casual_names)}")
    
    # Get user confirmation
    while True:
        try:
            response = input(f"\nSelect pen(s) to search for (1-{len(matches)}, comma-separated, or 'all'): ").strip()
            
            if response.lower() == 'all':
                selected_pens = matches
                break
            elif response.lower() in ['none', 'cancel', 'quit']:
                return []
            else:
                # Parse comma-separated numbers
                indices = [int(x.strip()) for x in response.split(',')]
                if all(1 <= idx <= len(matches) for idx in indices):
                    selected_pens = [matches[idx-1] for idx in indices]
                    break
                else:
                    print(f"❌ Please enter numbers between 1 and {len(matches)}")
        except ValueError:
            print("❌ Please enter valid numbers separated by commas")
    
    print(f"\n✅ Selected pen(s): {', '.join(selected_pens)}")
    
    # Get all search terms for the selected pens
    search_terms = get_all_search_terms_for_pens(selected_pens)
    print(f"🔍 Will search for: {', '.join(search_terms)}")
    
    return search_terms

def add_new_pen_mapping(formal_name: str, casual_names: List[str]):
    """
    Add a new pen and its casual names to the mapping and save to file.
    Useful for expanding the database on the fly.
    """
    for casual_name in casual_names:
        pen_names_map.add(formal_name, casual_name.lower())
    
    # Save to file
    save_pen_aliases_to_file(pen_names_map, get_aliases_file_path())
    print(f"✅ Added {formal_name} with aliases: {', '.join(casual_names)}")

def add_aliases_to_pen(formal_name: str, new_aliases: List[str]):
    """
    Add new aliases to an existing pen and save to file.
    """
    for alias in new_aliases:
        pen_names_map.add(formal_name, alias.lower())
    
    # Save to file
    save_pen_aliases_to_file(pen_names_map, get_aliases_file_path())
    print(f"✅ Added aliases to {formal_name}: {', '.join(new_aliases)}")

def remove_aliases_from_pen(formal_name: str, aliases_to_remove: List[str]) -> tuple[List[str], List[str]]:
    """
    Remove aliases from an existing pen and save to file.
    Returns (removed_aliases, not_found_aliases).
    """
    current_aliases = pen_names_map.get_values(formal_name)
    removed_aliases = []
    not_found_aliases = []
    
    for alias in aliases_to_remove:
        alias_lower = alias.lower()
        if alias_lower in current_aliases:
            # Remove from both mappings
            pen_names_map._one_to_many[formal_name].discard(alias_lower)
            if alias_lower in pen_names_map._many_to_one:
                del pen_names_map._many_to_one[alias_lower]
            removed_aliases.append(alias)
        else:
            not_found_aliases.append(alias)
    
    # Save to file if any changes were made
    if removed_aliases:
        save_pen_aliases_to_file(pen_names_map, get_aliases_file_path())
        print(f"✅ Removed aliases from {formal_name}: {', '.join(removed_aliases)}")
    
    return removed_aliases, not_found_aliases

def remove_pen_completely(formal_name: str) -> tuple[bool, List[str]]:
    """
    Remove a pen completely from the database (formal name and all aliases).
    Returns (success, removed_aliases_list).
    """
    if formal_name not in pen_names_map.keys():
        return False, []
    
    # Get all aliases before removing
    aliases = list(pen_names_map.get_values(formal_name))
    
    # Remove all aliases from the many-to-one mapping
    for alias in aliases:
        if alias in pen_names_map._many_to_one:
            del pen_names_map._many_to_one[alias]
    
    # Remove the formal name from the one-to-many mapping
    if formal_name in pen_names_map._one_to_many:
        del pen_names_map._one_to_many[formal_name]
    
    # Save to file
    save_pen_aliases_to_file(pen_names_map, get_aliases_file_path())
    print(f"✅ Completely removed {formal_name} and {len(aliases)} aliases from database")
    
    return True, aliases

def load_monitoring_from_file(file_path: str) -> List[str]:
    """
    Load monitoring list from a text file.
    File format: one search term per line
    """
    monitoring_list = []
    
    if not os.path.exists(file_path):
        print(f"Creating new monitoring file at {file_path}")
        # Create empty file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# Fountain Pen Monitoring List\n")
            f.write("# One search term per line\n\n")
        return monitoring_list
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):  # Skip empty lines and comments
                    continue
                monitoring_list.append(line)
        
        print(f"Loaded {len(monitoring_list)} monitoring terms from {file_path}")
    except Exception as e:
        print(f"Error loading monitoring list from {file_path}: {e}")
    
    return monitoring_list

def save_monitoring_to_file(monitoring_list: List[str], file_path: str):
    """
    Save monitoring list to a text file using atomic writes.
    File format: one search term per line
    """
    try:
        with _file_lock:
            # Build content in memory first
            lines = [
                "# Fountain Pen Monitoring List\n",
                "# One search term per line\n\n"
            ]
            
            for term in sorted(set(monitoring_list)):  # Remove duplicates and sort
                lines.append(f"{term}\n")
            
            content = ''.join(lines)
            
            # Atomically write the file
            if atomic_write_file(file_path, content):
                print(f"✅ Saved {len(set(monitoring_list))} monitoring terms to {file_path}")
            else:
                print(f"❌ Failed to save monitoring list to {file_path}")
                
    except Exception as e:
        print(f"❌ Error saving monitoring list to {file_path}: {e}")

# Global monitoring list loaded from file
_monitoring_list = load_monitoring_from_file(get_monitoring_file_path())

def get_monitoring_list() -> List[str]:
    """Get the current monitoring list."""
    return _monitoring_list.copy()

def add_to_monitoring(search_terms: List[str]) -> int:
    """
    Add search terms to monitoring list and save to file.
    Returns number of new terms added.
    """
    global _monitoring_list
    original_set = set(_monitoring_list)
    new_terms = [term for term in search_terms if term not in original_set]
    
    if new_terms:
        _monitoring_list.extend(new_terms)
        save_monitoring_to_file(_monitoring_list, get_monitoring_file_path())
    
    return len(new_terms)

def remove_from_monitoring(search_terms: List[str]) -> int:
    """
    Remove search terms from monitoring list and save to file.
    Returns number of terms removed.
    """
    global _monitoring_list
    original_count = len(_monitoring_list)
    _monitoring_list = [term for term in _monitoring_list if term not in search_terms]
    removed_count = original_count - len(_monitoring_list)
    
    if removed_count > 0:
        save_monitoring_to_file(_monitoring_list, get_monitoring_file_path())
    
    return removed_count

def clear_all_monitoring() -> int:
    """
    Clear all monitoring and save to file.
    Returns number of terms removed.
    """
    global _monitoring_list
    removed_count = len(_monitoring_list)
    _monitoring_list = []
    save_monitoring_to_file(_monitoring_list, get_monitoring_file_path())
    return removed_count

def add_formal_pens_to_monitoring(formal_names: List[str]) -> int:
    """
    Add formal pen names to monitoring list and save to file.
    Only stores formal names, not aliases.
    Returns number of new formal names added.
    """
    global _monitoring_list
    original_set = set(_monitoring_list)
    new_formal_names = [name for name in formal_names if name not in original_set]
    
    if new_formal_names:
        _monitoring_list.extend(new_formal_names)
        save_monitoring_to_file(_monitoring_list, get_monitoring_file_path())
    
    return len(new_formal_names)

def remove_formal_pens_from_monitoring(formal_names: List[str]) -> int:
    """
    Remove formal pen names from monitoring list and save to file.
    Returns number of formal names removed.
    """
    global _monitoring_list
    original_count = len(_monitoring_list)
    _monitoring_list = [name for name in _monitoring_list if name not in formal_names]
    removed_count = original_count - len(_monitoring_list)
    
    if removed_count > 0:
        save_monitoring_to_file(_monitoring_list, get_monitoring_file_path())
    
    return removed_count

def get_all_monitoring_search_terms() -> List[str]:
    """
    Get all search terms for currently monitored formal pen names.
    This expands formal names into all their aliases for actual searching.
    """
    all_search_terms = []
    
    for formal_name in _monitoring_list:
        if formal_name in pen_names_map.keys():
            # Get all search terms for this formal pen name
            search_terms = get_all_search_terms_for_pens([formal_name])
            all_search_terms.extend(search_terms)
    
    return list(set(all_search_terms))  # Remove duplicates

def reload_pen_aliases_from_file() -> tuple[bool, str]:
    """
    Reload pen aliases from the file, updating the global pen_names_map.
    Returns (success, message).
    """
    global pen_names_map
    
    try:
        file_path = get_aliases_file_path()
        print(f"Reloading pen aliases from: {file_path}")
        
        # Use the more reliable repair_from_file method that rebuilds the map from scratch
        old_count = len(pen_names_map._one_to_many)
        entries_loaded = pen_names_map.repair_from_file(file_path)
        new_count = len(pen_names_map._one_to_many)
        
        # Perform a validation check after loading to ensure consistency
        issues_fixed = pen_names_map.validate()
        if issues_fixed:
            print(f"Fixed {len(issues_fixed)} additional issues after reload")
        
        message = f"✅ Reloaded pen aliases: {new_count} pens (was {old_count})"
        if issues_fixed:
            message += f" and fixed {len(issues_fixed)} consistency issues"
        print(message)
        return True, message
        
    except Exception as e:
        error_msg = f"❌ Failed to reload pen aliases: {e}"
        print(error_msg)
        return False, error_msg

def reload_monitoring_from_file() -> tuple[bool, str]:
    """
    Reload monitoring list from the file, updating the global _monitoring_list.
    Returns (success, message).
    """
    global _monitoring_list
    
    try:
        file_path = get_monitoring_file_path()
        new_monitoring_list = load_monitoring_from_file(file_path)
        
        old_count = len(_monitoring_list)
        _monitoring_list = new_monitoring_list
        new_count = len(_monitoring_list)
        
        message = f"✅ Reloaded monitoring list: {new_count} pens (was {old_count})"
        print(message)
        return True, message
        
    except Exception as e:
        error_msg = f"❌ Failed to reload monitoring list: {e}"
        print(error_msg)
        return False, error_msg