import unittest
import sys
import os

# Add the main directory to sys.path so we can import directly from utils
main_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, main_dir)

from utils.text_utils import find_matching_pen_names, get_all_search_terms_for_pens

class TestDiscordIntegration(unittest.TestCase):
    """Test that the pen search functions work correctly for Discord integration."""

    def test_search_workflow(self):
        """Test the complete search workflow that would happen in Discord."""
        # Simulate user typing "vp" in Discord
        user_query = "vp"
        
        # Find matches (this is what /search_pen does)
        matches = find_matching_pen_names(user_query, max_results=4)
        
        # Should find Pilot Vanishing Point
        self.assertTrue(len(matches) > 0)
        self.assertIn("Pilot Vanishing Point", matches)
        
        # Get search terms for monitoring (this is what happens when user clicks "Set Monitoring")
        search_terms = get_all_search_terms_for_pens(matches)
        
        # Should include all the aliases
        expected_terms = {"Pilot Vanishing Point", "vanishing point", "vp", "pilot vp", "pilot vanishing"}
        self.assertTrue(expected_terms.issubset(set(search_terms)))

    def test_multiple_pen_workflow(self):
        """Test workflow with multiple pen searches."""
        queries = ["custom", "lamy"]
        all_formal_names = []
        
        for query in queries:
            matches = find_matching_pen_names(query, max_results=2)
            all_formal_names.extend(matches)
        
        # Should find multiple pens
        self.assertTrue(len(all_formal_names) > 0)
        
        # Get combined search terms
        search_terms = get_all_search_terms_for_pens(all_formal_names)
        
        # Should have many search terms
        self.assertTrue(len(search_terms) > len(all_formal_names))

    def test_no_match_scenario(self):
        """Test what happens when Discord user searches for non-existent pen."""
        user_query = "nonexistent fakepen model 9999"
        
        matches = find_matching_pen_names(user_query)
        
        # Should return empty list
        self.assertEqual(matches, [])
        
        # Getting search terms for empty list should return empty list
        search_terms = get_all_search_terms_for_pens(matches)
        self.assertEqual(search_terms, [])

    def test_case_insensitive_discord_search(self):
        """Test that Discord searches are case insensitive."""
        queries = ["VP", "vp", "Vp", "vP"]
        
        results = []
        for query in queries:
            matches = find_matching_pen_names(query)
            results.append(matches)
        
        # All should return the same results
        for i in range(1, len(results)):
            self.assertEqual(results[0], results[i])

    def test_partial_match_scenarios(self):
        """Test various partial matching scenarios that Discord users might try."""
        test_cases = [
            ("vanishing", "Pilot Vanishing Point"),
            ("custom", "Pilot Custom 74"),  # Should match either Custom 74 or Custom Heritage 92
            ("sailor", "Sailor Pro Gear"),  # Should match either Pro Gear or 1911
            ("montblanc", "Montblanc 146"),  # Should match Montblanc models
        ]
        
        for query, expected_match in test_cases:
            matches = find_matching_pen_names(query)
            
            # Should find at least one match
            self.assertTrue(len(matches) > 0, f"No matches found for '{query}'")
            
            # The expected pen should be in the results (or a related one)
            found_related = any(expected_match.split()[0] in match for match in matches)
            self.assertTrue(found_related, f"No related match found for '{query}' (expected something related to '{expected_match}')")

if __name__ == '__main__':
    unittest.main() 