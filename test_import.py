#!/usr/bin/env python3
"""Test import of fund_distribution service"""
try:
    from modules.fund_distribution.service import FundDistributionService
    print("✅ Import successful")
except SyntaxError as e:
    print(f"❌ Syntax error: {e}")
except Exception as e:
    print(f"❌ Import error: {e}")
