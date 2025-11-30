#!/usr/bin/env python3
"""
Script to fix middle child detection in fund_distribution/service.py
Adds 'placement_level == 2' check to line 234
"""

import re

file_path = "modules/fund_distribution/service.py"

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the specific line
# Old: if placed_under_user_id and placement_position is not None and int(placement_position) % 3 == 1:
# New: if placed_under_user_id and placement_level == 2 and placement_position is not None and int(placement_position) % 3 == 1:

old_pattern = r'if placed_under_user_id and placement_position is not None and int\(placement_position\) % 3 == 1:'
new_line = 'if placed_under_user_id and placement_level == 2 and placement_position is not None and int(placement_position) % 3 == 1:'

# Also update the comment and print statement
old_comment = '# This applies to ANY level, not just Level 2.'
new_comment = '# CRITICAL FIX: Only apply to Level 2 (where middle 3 rule applies)'

old_print = 'print(f"[MATRIX ROUTING] Middle child detected (pos {placement_position}). Routing to 2nd upline.")'
new_print = 'print(f"[MATRIX ROUTING] Level 2 Middle child detected (pos {placement_position}). Routing to 2nd upline.")'

content = re.sub(old_comment, new_comment, content)
content = re.sub(old_pattern, new_line, content)
content = re.sub(re.escape(old_print), new_print, content)

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed middle child detection - added Level 2 check")
