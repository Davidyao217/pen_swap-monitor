import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
import os

# Adjust Python path to import modules from the 'main' directory
# This assumes the test script is in 'main/tests' and 'main' is a top-level package source.
# It adds the parent directory of 'main' (i.e., the workspace root) to sys.path.
workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, workspace_root)

# Add the main directory to sys.path so we can import directly from utils
main_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, main_dir)

from utils.text_utils import format_discord_message # Direct import avoiding package loading

class TestTextUtils(unittest.TestCase):

    def test_format_discord_message_scenario(self):
        submission_title = "WTS CONUS (world negotiable) Custom PEEK pen, YStudio, Benu, Oversized Waterman Emblem, Sailor X Pentonote Realo, Pilot Myu, MCI Schmidt nib"
        submission_selftext = (
            "If you chat me, please say so in your comment; I can only see it on my computer and don't log in there regularly.\n\n"
            "I'm willing to ship overseas, but we will have to discuss shipping before that happens. $10 shipping for a single pen to the USA, and I will combine shipping for multiple pens.\n\n"
            "I'm refining my collection to only pens I use, or am eager to use, and some of these are just not for me.\n\n"
            "Pens in verification photo, from left to right (see below for details, I tried numbering but reddit isn't cooperating):\n\n"
            "Custom PEEK pen from Eureka,\n\n"
            "Y Studio Classic,\n\n"
            "Benu Grand Scepter,\n\n"
            "oversized Waterman Emblem pen,\n\n"
            "Sailor x Pentonote Realo Sorayu no Iro,\n\n"
            "Pilot Myu\n\n"
            "(bottom row) MCI Schmidt nib\n\n"
            "Custom PEEK pen from Eureka Pens (no markings on the nib, probably F or M) $125, B Condition Note: this pen ONLY takes Pilot converters. The cartridges don't fit. The nib is not a nib unit, and cannot be changed.\n\n"
            "PENDING Y Studio Classic <M> $75, B condition\n\n"
            "Benu Grand Scepter (I can't find markings for the nib size, but it's probably a F or M) $75, B condition\n\n"
            "Oversized Waterman Emblem Pen (no marking on the nib) $80, Parts Photos of nib The nib on this one seems fairly fine, and it's somewhat stiff. It's also HUGE. Similar in size to a modern number 8 nib. The body is in very rough shape.\n\n"
            "Pentonote x Sailor Realo Sorayu no Iro <M> $400, B condition Image 1, Image 2\n\n"
            "Pilot Myu <FM> $200, B condition additional photos I understand this nib size is rare. I have used this pen with shimmer ink, so you may encounter shimmer particles from time to time. There is some scratching consistent with use where the cap sits when the pen is closed.\n\n"
            "Schmidt FH452 nib unit <MCI> $50, D for custom grind additional photos Medium nib custom ground by FPNibs.com to a cursive italic with a star breather hole."
        )
        combined_text = f"{submission_title} {submission_selftext}"
        # Use the search terms provided by the user as the 'found_pen_models'
        found_pen_models = ["vanishing point", "pilot custom", "brass nib"]
        permalink = "/r/fountainpens/comments/xyz123/test_post"

        # Mock datetime.now() for a predictable timestamp
        mock_dt_now = datetime(2023, 10, 26, 10, 30, 0)
        
        # The format_discord_message function itself imports datetime and calls .now()
        # So we need to patch 'utils.text_utils.datetime'
        with patch('utils.text_utils.datetime') as mock_datetime_module:
            mock_datetime_module.now.return_value = mock_dt_now
            
            actual_message = format_discord_message(
                submission_title=submission_title,
                combined_text=combined_text,
                found_pen_models=found_pen_models,
                permalink=permalink
            )

        print(actual_message)

if __name__ == '__main__':
    unittest.main()
