import os
import sys

import pandas as pd

# Ensure the application module is importable
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from kooyong_app_address_checker import parse_street_name, check_street_match


def test_parse_street_name_handles_numbers_prefixes_and_commas():
    assert parse_street_name("145 Camberwell Road") == "camberwell road"
    assert parse_street_name("Unit 2 15 Main St") == "15 main st"
    assert parse_street_name("30 Example Ave, Kew") == "example ave"


def test_check_street_match():
    data = {
        "street_lower": ["camberwell road", "munro street"],
        "street_name": ["Camberwell Road", "Munro Street"],
        "suburb": ["Hawthorn East", "Kew"],
    }
    df = pd.DataFrame(data)

    match, name, suburbs = check_street_match("camberwell road", df)
    assert match is True
    assert name == "Camberwell Road"
    assert suburbs == [{"street_name": "Camberwell Road", "suburb": "Hawthorn East"}]

    match, name, suburbs = check_street_match("nonexistent", df)
    assert match is False
    assert name is None
    assert suburbs == []

