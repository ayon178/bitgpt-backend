#!/usr/bin/env python3
"""
Test script for the updated Global Earnings API
Tests the new slot-wise structure with phase-wise downlines
"""

import requests
import json

def test_global_earnings_api():
    """Test the updated /global/earnings/{user_id} API"""
    
    base_url = 'http://localhost:8000'
    user_id = '68fb4822f0ff667f3198072a'
    
    print('🧪 Testing Updated Global Earnings API')
    print('=' * 50)
    
    # Test with PHASE-1
    print('\n📋 Testing with phase=PHASE-1:')
    try:
        response = requests.get(f'{base_url}/global/earnings/{user_id}?phase=PHASE-1')
        if response.status_code == 200:
            data = response.json()
            print(f'✅ Status: {response.status_code}')
            print(f'📊 Response Structure:')
            print(f'   - User ID: {data.get("data", {}).get("user_id")}')
            print(f'   - User Name: {data.get("data", {}).get("user_name")}')
            print(f'   - Total Slots: {data.get("data", {}).get("total_slots")}')
            
            slots = data.get('data', {}).get('slots', [])
            for slot in slots:
                print(f'\n   🎯 Slot {slot.get("slot_no")}:')
                phases = slot.get('phases', {})
                for phase_name, phase_data in phases.items():
                    print(f'      📍 {phase_name}:')
                    print(f'         - Is Root: {phase_data.get("is_root")}')
                    print(f'         - Downlines Count: {len(phase_data.get("downlines", []))}')
                    if phase_data.get('user_position'):
                        print(f'         - Level: {phase_data["user_position"].get("level")}')
                        print(f'         - Position: {phase_data["user_position"].get("position")}')
        else:
            print(f'❌ Error: {response.status_code} - {response.text}')
    except Exception as e:
        print(f'❌ Exception: {e}')
    
    print('\n' + '=' * 50)
    print('🧪 Testing with phase=PHASE-2:')
    
    # Test with PHASE-2
    try:
        response = requests.get(f'{base_url}/global/earnings/{user_id}?phase=PHASE-2')
        if response.status_code == 200:
            data = response.json()
            print(f'✅ Status: {response.status_code}')
            print(f'📊 Response Structure:')
            print(f'   - User ID: {data.get("data", {}).get("user_id")}')
            print(f'   - User Name: {data.get("data", {}).get("user_name")}')
            print(f'   - Total Slots: {data.get("data", {}).get("total_slots")}')
            
            slots = data.get('data', {}).get('slots', [])
            for slot in slots:
                print(f'\n   🎯 Slot {slot.get("slot_no")}:')
                phases = slot.get('phases', {})
                for phase_name, phase_data in phases.items():
                    print(f'      📍 {phase_name}:')
                    print(f'         - Is Root: {phase_data.get("is_root")}')
                    print(f'         - Downlines Count: {len(phase_data.get("downlines", []))}')
                    if phase_data.get('user_position'):
                        print(f'         - Level: {phase_data["user_position"].get("level")}')
                        print(f'         - Position: {phase_data["user_position"].get("position")}')
        else:
            print(f'❌ Error: {response.status_code} - {response.text}')
    except Exception as e:
        print(f'❌ Exception: {e}')
    
    print('\n' + '=' * 50)
    print('🧪 Testing without phase parameter (all phases):')
    
    # Test without phase parameter
    try:
        response = requests.get(f'{base_url}/global/earnings/{user_id}')
        if response.status_code == 200:
            data = response.json()
            print(f'✅ Status: {response.status_code}')
            print(f'📊 Response Structure:')
            print(f'   - User ID: {data.get("data", {}).get("user_id")}')
            print(f'   - User Name: {data.get("data", {}).get("user_name")}')
            print(f'   - Total Slots: {data.get("data", {}).get("total_slots")}')
            
            slots = data.get('data', {}).get('slots', [])
            for slot in slots:
                print(f'\n   🎯 Slot {slot.get("slot_no")}:')
                phases = slot.get('phases', {})
                for phase_name, phase_data in phases.items():
                    print(f'      📍 {phase_name}:')
                    print(f'         - Is Root: {phase_data.get("is_root")}')
                    print(f'         - Downlines Count: {len(phase_data.get("downlines", []))}')
                    if phase_data.get('user_position'):
                        print(f'         - Level: {phase_data["user_position"].get("level")}')
                        print(f'         - Position: {phase_data["user_position"].get("position")}')
        else:
            print(f'❌ Error: {response.status_code} - {response.text}')
    except Exception as e:
        print(f'❌ Exception: {e}')

if __name__ == "__main__":
    test_global_earnings_api()
