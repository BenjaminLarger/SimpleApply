#!/usr/bin/env python3
"""Test placeholder regex replacement."""

import re

def test_regex_replacement():
    """Test if the regex patterns work correctly."""

    # Test the exact HTML from the template
    html_snippet = """  <h3 style="padding-left: 6pt; text-indent: 0pt; text-align: left;"><!-- PROJECT 1 TITLE --> <span style="font-weight: normal; font-size: 10pt;"><span style="color: #666;"><!-- PROJECT 1 TYPE --></span></span></h3>
  <p style="padding-left: 6pt; text-indent: 0pt; text-align: left;"><!-- PROJECT 1 DESCRIPTION --></p>"""

    replacements = {
        "PROJECT 1 TITLE": "Multi-Model Chat Interface",
        "PROJECT 1 TYPE": "Side Project",
        "PROJECT 1 DESCRIPTION": "Built a comprehensive AI chat system...",
    }

    print("=" * 80)
    print("TESTING PLACEHOLDER REGEX REPLACEMENT")
    print("=" * 80)

    print("\n1. Original HTML:")
    print(html_snippet)

    print("\n2. Replacements to make:")
    for k, v in replacements.items():
        print(f"   {k} -> {v}")

    result = html_snippet
    for placeholder, value in replacements.items():
        # This is the exact code from template_processor.py
        comment_pattern = f"<!--\\s*{re.escape(placeholder)}\\s*-->"
        print(f"\n3. Testing pattern for '{placeholder}':")
        print(f"   Pattern: {comment_pattern}")

        # Test if pattern matches
        if re.search(comment_pattern, result, flags=re.IGNORECASE):
            print(f"   ✓ Pattern MATCHES in HTML")
            result = re.sub(comment_pattern, value, result, flags=re.IGNORECASE)
            print(f"   ✓ Replacement done")
        else:
            print(f"   ✗ Pattern DOES NOT MATCH")
            # Debug: show what we're trying to match
            print(f"   Looking for: {comment_pattern}")
            print(f"   In HTML: {html_snippet[:200]}...")

    print("\n4. Final result:")
    print(result)

    # Check for remaining placeholders
    remaining = ["<!-- PROJECT 1 TITLE -->", "<!-- PROJECT 1 TYPE -->", "<!-- PROJECT 1 DESCRIPTION -->"]
    for placeholder in remaining:
        if placeholder in result:
            print(f"   ✗ UNFILLED: {placeholder}")
        else:
            print(f"   ✓ FILLED: {placeholder}")

if __name__ == "__main__":
    test_regex_replacement()
