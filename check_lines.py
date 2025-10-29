#!/usr/bin/env python3
"""Check specific lines in service.py"""
import sys

with open('modules/fund_distribution/service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    
print(f"Total lines: {len(lines)}")
print(f"\nLine 297: {repr(lines[296])}")
print(f"Line 298: {repr(lines[297])}")
print(f"Line 299: {repr(lines[298])}")
print(f"Line 300: {repr(lines[299])}")
print(f"Line 301: {repr(lines[300])}")

# Check for any non-ASCII characters
for i in range(295, 303):
    line = lines[i] if i < len(lines) else ""
    non_ascii = [c for c in line if ord(c) > 127]
    if non_ascii:
        print(f"\nLine {i+1} has non-ASCII chars: {non_ascii}")

