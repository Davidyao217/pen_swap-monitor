import unittest
import sys
import os

# Add the main directory to sys.path so we can import directly from utils
main_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, main_dir)

from utils.text_utils import (
    find_matching_pen_names, 
    get_all_search_terms_for_pens,
    pen_names_map,
    add_new_pen_mapping
)

class TestPenSearch(unittest.TestCase):

    def test_exact_match(self):
        """Test exact matches work correctly."""
        matches = find_matching_pen_names("vanishing point")
        self.assertIn("Pilot Vanishing Point", matches)
        self.assertEqual(matches[0], "Pilot Vanishing Point")  # Should be first/best match

    def test_abbreviation_match(self):
        """Test abbreviations work correctly."""
        matches = find_matching_pen_names("vp")
        self.assertIn("Pilot Vanishing Point", matches)
        
        matches = find_matching_pen_names("l2k")
        self.assertIn("Lamy 2000", matches)

    def test_partial_match(self):
        """Test partial matches work correctly."""
        matches = find_matching_pen_names("custom")
        # Should match both Custom 74 and Custom Heritage 92
        formal_names = [match for match in matches]
        self.assertTrue(any("Custom 74" in name for name in formal_names))
        self.assertTrue(any("Custom Heritage 92" in name for name in formal_names))

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        matches1 = find_matching_pen_names("VANISHING POINT")
        matches2 = find_matching_pen_names("vanishing point")
        matches3 = find_matching_pen_names("Vanishing Point")
        
        self.assertEqual(matches1, matches2)
        self.assertEqual(matches2, matches3)

    def test_search_terms_generation(self):
        """Test that search terms are generated correctly."""
        formal_names = ["Pilot Vanishing Point"]
        search_terms = get_all_search_terms_for_pens(formal_names)
        
        expected_terms = {
            "Pilot Vanishing Point",
            "vanishing point", 
            "vp", 
            "pilot vp", 
            "pilot vanishing"
        }
        
        self.assertTrue(expected_terms.issubset(set(search_terms)))

    def test_no_matches(self):
        """Test behavior when no matches are found."""
        matches = find_matching_pen_names("completely fake pen name xyz")
        self.assertEqual(matches, [])

    def test_fuzzy_threshold(self):
        """Test fuzzy matching respects threshold."""
        # Should match with default threshold
        matches = find_matching_pen_names("vanishing", threshold=70)
        self.assertTrue(len(matches) > 0)
        
        # Should not match with high threshold
        matches = find_matching_pen_names("vanishing", threshold=95)
        self.assertEqual(len(matches), 0)

    def test_max_results_limit(self):
        """Test that max_results parameter works."""
        matches = find_matching_pen_names("pilot", max_results=2)
        self.assertTrue(len(matches) <= 2)

    def test_add_new_pen_mapping(self):
        """Test adding new pen mappings."""
        # Add a test pen
        add_new_pen_mapping("Test Pen Model", ["test pen", "tp", "test model"])
        
        # Verify it can be found
        matches = find_matching_pen_names("test pen")
        self.assertIn("Test Pen Model", matches)
        
        # Verify search terms include all aliases
        search_terms = get_all_search_terms_for_pens(["Test Pen Model"])
        expected_aliases = {"test pen", "tp", "test model", "Test Pen Model"}
        self.assertTrue(expected_aliases.issubset(set(search_terms)))

    def test_bidirectional_mapping(self):
        """Test that the bidirectional mapping works correctly."""
        # Test one-to-many
        casual_names = pen_names_map.get_values("Pilot Vanishing Point")
        self.assertIn("vp", casual_names)
        self.assertIn("vanishing point", casual_names)
        
        # Test many-to-one
        formal_name = pen_names_map.get_key("vp")
        self.assertEqual(formal_name, "Pilot Vanishing Point")

if __name__ == '__main__':
    unittest.main() 