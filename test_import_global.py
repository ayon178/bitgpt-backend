#!/usr/bin/env python3
"""Test import of global service"""
try:
    from modules.global.service import GlobalService
    print("✅ GlobalService import successful")
except SyntaxError as e:
    print(f"❌ Syntax error: {e}")
except Exception as e:
    print(f"❌ Import error: {e}")
