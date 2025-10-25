#!/usr/bin/env python3
"""
Example of the updated Global Earnings API response structure
This shows how the new slot-wise API will return data
"""

def show_api_response_structure():
    """Show the expected API response structure"""
    
    print('📋 Updated Global Earnings API Response Structure')
    print('=' * 60)
    print('Endpoint: GET /global/earnings/{user_id}?phase=PHASE-1')
    print('=' * 60)
    
    example_response = {
        "status": "success",
        "data": {
            "user_id": "68fb4822f0ff667f3198072a",
            "user_name": "Test User",
            "user_email": "test@example.com",
            "total_slots": 2,
            "slots": [
                {
                    "slot_no": 1,
                    "slot_info": "Slot 1",
                    "phases": {
                        "PHASE-1": {
                            "phase": "PHASE-1",
                            "user_position": {
                                "level": 1,
                                "position": "1",
                                "parent_id": None,
                                "upline_id": None,
                                "activation_date": "2024-01-15T10:30:00"
                            },
                            "is_root": True,
                            "downlines": [
                                {
                                    "user_id": "68fb48a8f0ff667f31980760",
                                    "name": "Downline User 1",
                                    "email": "downline1@example.com",
                                    "level": 2,
                                    "position": "1",
                                    "activation_date": "2024-01-15T11:00:00"
                                },
                                {
                                    "user_id": "68fb3a8ff9de528de8f9014c",
                                    "name": "Downline User 2",
                                    "email": "downline2@example.com",
                                    "level": 2,
                                    "position": "2",
                                    "activation_date": "2024-01-15T11:30:00"
                                }
                            ]
                        }
                    }
                },
                {
                    "slot_no": 2,
                    "slot_info": "Slot 2",
                    "phases": {
                        "PHASE-1": {
                            "phase": "PHASE-1",
                            "user_position": {
                                "level": 1,
                                "position": "1",
                                "parent_id": None,
                                "upline_id": None,
                                "activation_date": "2024-01-16T09:00:00"
                            },
                            "is_root": True,
                            "downlines": []
                        }
                    }
                }
            ]
        }
    }
    
    print('📊 Example Response Structure:')
    print(json.dumps(example_response, indent=2))
    
    print('\n' + '=' * 60)
    print('🔍 Key Features:')
    print('=' * 60)
    print('✅ Slots Array: Returns all slots for the user')
    print('✅ Phase-wise Data: Each slot contains PHASE-1 and PHASE-2 data')
    print('✅ Root Detection: Shows if user is root in specific phase/slot')
    print('✅ Downlines Array: Shows all downlines if user is root')
    print('✅ User Position: Shows level, position, parent info')
    print('✅ Phase Filtering: Can filter by phase=PHASE-1 or PHASE-2')
    
    print('\n' + '=' * 60)
    print('🎯 Use Cases:')
    print('=' * 60)
    print('1. Frontend can display slot-wise earnings')
    print('2. Show phase-wise tree structure')
    print('3. Display downlines when user is root')
    print('4. Track user progression across slots')
    print('5. Phase-specific data filtering')

if __name__ == "__main__":
    import json
    show_api_response_structure()
