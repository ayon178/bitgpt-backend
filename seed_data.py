#!/usr/bin/env python3
"""
Seed Data Script for BitGPT MLM Platform
This script populates the database with initial data
"""

import os
import sys
from decimal import Decimal

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.db import connect_to_db
from modules.slot import SlotCatalog
from modules.blockchain import SystemConfig

def seed_slot_catalog():
    """Seed the slot catalog with 16 binary slots"""
    
    # Binary slot data based on your documentation
    slots = [
        {"slot_no": 1, "name": "Explorer", "price": Decimal("0.0022"), "program": "binary", "level": 1},
        {"slot_no": 2, "name": "Contributor", "price": Decimal("0.0044"), "program": "binary", "level": 2},
        {"slot_no": 3, "name": "Subscriber", "price": Decimal("0.0088"), "program": "binary", "level": 3},
        {"slot_no": 4, "name": "Dreamer", "price": Decimal("0.0176"), "program": "binary", "level": 4},
        {"slot_no": 5, "name": "Planner", "price": Decimal("0.0352"), "program": "binary", "level": 5},
        {"slot_no": 6, "name": "Challenger", "price": Decimal("0.0704"), "program": "binary", "level": 6},
        {"slot_no": 7, "name": "Adventurer", "price": Decimal("0.1408"), "program": "binary", "level": 7},
        {"slot_no": 8, "name": "Game-Shifter", "price": Decimal("0.2816"), "program": "binary", "level": 8},
        {"slot_no": 9, "name": "Organizer", "price": Decimal("0.5632"), "program": "binary", "level": 9},
        {"slot_no": 10, "name": "Leader", "price": Decimal("1.1264"), "program": "binary", "level": 10},
        {"slot_no": 11, "name": "Vanguard", "price": Decimal("2.2528"), "program": "binary", "level": 11},
        {"slot_no": 12, "name": "Center", "price": Decimal("4.5056"), "program": "binary", "level": 12},
        {"slot_no": 13, "name": "Climax", "price": Decimal("9.0112"), "program": "binary", "level": 13},
        {"slot_no": 14, "name": "Eternity", "price": Decimal("18.0224"), "program": "binary", "level": 14},
        {"slot_no": 15, "name": "King", "price": Decimal("36.0448"), "program": "binary", "level": 15},
        {"slot_no": 16, "name": "Commander", "price": Decimal("72.0896"), "program": "binary", "level": 16}
    ]
    
    print("🌱 Seeding Slot Catalog...")
    
    for slot_data in slots:
        # Check if slot already exists
        existing_slot = SlotCatalog.objects(slot_no=slot_data["slot_no"], program=slot_data["program"]).first()
        
        if existing_slot:
            print(f"✅ Slot {slot_data['slot_no']} ({slot_data['name']}) already exists")
        else:
            slot = SlotCatalog(**slot_data)
            slot.save()
            print(f"✅ Created Slot {slot_data['slot_no']}: {slot_data['name']} - ${slot_data['price']}")
    
    print("🎯 Slot Catalog seeding completed!")

def seed_matrix_slots():
    """Seed matrix slots (1-15) with $10 base price"""
    
    matrix_slots = []
    base_price = Decimal("10.00")
    
    for i in range(1, 16):
        # Matrix slots have progressive pricing
        price = base_price * (Decimal("1.1") ** (i - 1))  # 10% increase per level
        matrix_slots.append({
            "slot_no": i,
            "name": f"Matrix Level {i}",
            "price": price.quantize(Decimal("0.01")),
            "program": "matrix",
            "level": i
        })
    
    print("🌱 Seeding Matrix Slots...")
    
    for slot_data in matrix_slots:
        existing_slot = SlotCatalog.objects(slot_no=slot_data["slot_no"], program=slot_data["program"]).first()
        
        if existing_slot:
            print(f"✅ Matrix Slot {slot_data['slot_no']} already exists")
        else:
            slot = SlotCatalog(**slot_data)
            slot.save()
            print(f"✅ Created Matrix Slot {slot_data['slot_no']}: {slot_data['name']} - ${slot_data['price']}")
    
    print("🎯 Matrix Slots seeding completed!")

def seed_global_slots():
    """Seed global matrix slots (1-10) with progressive pricing"""
    
    global_slots = []
    base_price = Decimal("50.00")  # Global matrix base price
    
    for i in range(1, 11):
        # Global slots have progressive pricing
        price = base_price * (Decimal("1.2") ** (i - 1))  # 20% increase per level
        global_slots.append({
            "slot_no": i,
            "name": f"Global Phase {i}",
            "price": price.quantize(Decimal("0.01")),
            "program": "global",
            "level": i
        })
    
    print("🌱 Seeding Global Matrix Slots...")
    
    for slot_data in global_slots:
        existing_slot = SlotCatalog.objects(slot_no=slot_data["slot_no"], program=slot_data["program"]).first()
        
        if existing_slot:
            print(f"✅ Global Slot {slot_data['slot_no']} already exists")
        else:
            slot = SlotCatalog(**slot_data)
            slot.save()
            print(f"✅ Created Global Slot {slot_data['slot_no']}: {slot_data['name']} - ${slot_data['price']}")
    
    print("🎯 Global Matrix Slots seeding completed!")

def seed_system_config():
    """Seed system configuration"""
    
    configs = [
        # Binary Distribution (Total 100%)
        {
            "config_key": "binary_distribution_spark",
            "config_value": "8",
            "description": "Binary Spark Bonus percentage"
        },
        {
            "config_key": "binary_distribution_royal_captain",
            "config_value": "4",
            "description": "Binary Royal Captain percentage"
        },
        {
            "config_key": "binary_distribution_president",
            "config_value": "3",
            "description": "Binary President Reward percentage"
        },
        {
            "config_key": "binary_distribution_leadership",
            "config_value": "5",
            "description": "Binary Leadership Stipend percentage"
        },
        {
            "config_key": "binary_distribution_jackpot",
            "config_value": "5",
            "description": "Binary Jackpot Entry percentage"
        },
        {
            "config_key": "binary_distribution_partner",
            "config_value": "10",
            "description": "Binary Partner Incentive percentage"
        },
        {
            "config_key": "binary_distribution_level",
            "config_value": "60",
            "description": "Binary Level Payout percentage"
        },
        {
            "config_key": "binary_distribution_shareholders",
            "config_value": "5",
            "description": "Binary Shareholders percentage"
        },
        
        # Matrix Distribution (Total 100%)
        {
            "config_key": "matrix_distribution_spark",
            "config_value": "8",
            "description": "Matrix Spark Bonus percentage"
        },
        {
            "config_key": "matrix_distribution_royal_captain",
            "config_value": "4",
            "description": "Matrix Royal Captain percentage"
        },
        {
            "config_key": "matrix_distribution_president",
            "config_value": "3",
            "description": "Matrix President Reward percentage"
        },
        {
            "config_key": "matrix_distribution_shareholders",
            "config_value": "5",
            "description": "Matrix Shareholders percentage"
        },
        {
            "config_key": "matrix_distribution_newcomer",
            "config_value": "20",
            "description": "Matrix Newcomer Growth Support percentage"
        },
        {
            "config_key": "matrix_distribution_mentorship",
            "config_value": "10",
            "description": "Matrix Mentorship Bonus percentage"
        },
        {
            "config_key": "matrix_distribution_partner",
            "config_value": "10",
            "description": "Matrix Partner Incentive percentage"
        },
        {
            "config_key": "matrix_distribution_level",
            "config_value": "40",
            "description": "Matrix Level Payout percentage"
        },
        
        # Global Distribution (Total 110%)
        {
            "config_key": "global_distribution_level",
            "config_value": "40",
            "description": "Global Level + Partner Incentive percentage (30% + 10%)"
        },
        {
            "config_key": "global_distribution_profit",
            "config_value": "30",
            "description": "Global Profit percentage"
        },
        {
            "config_key": "global_distribution_royal_captain",
            "config_value": "15",
            "description": "Global Royal Captain Bonus percentage"
        },
        {
            "config_key": "global_distribution_president",
            "config_value": "15",
            "description": "Global President Reward percentage"
        },
        {
            "config_key": "global_distribution_triple_entry",
            "config_value": "5",
            "description": "Global Triple Entry Reward percentage"
        },
        {
            "config_key": "global_distribution_shareholders",
            "config_value": "5",
            "description": "Global Shareholders percentage"
        },
        
        # Spark Bonus Distribution (Matrix Slots 1-14)
        {
            "config_key": "spark_slot_1_percentage",
            "config_value": "15",
            "description": "Spark Bonus Slot 1 percentage"
        },
        {
            "config_key": "spark_slot_2_percentage",
            "config_value": "10",
            "description": "Spark Bonus Slot 2 percentage"
        },
        {
            "config_key": "spark_slot_3_percentage",
            "config_value": "10",
            "description": "Spark Bonus Slot 3 percentage"
        },
        {
            "config_key": "spark_slot_4_percentage",
            "config_value": "10",
            "description": "Spark Bonus Slot 4 percentage"
        },
        {
            "config_key": "spark_slot_5_percentage",
            "config_value": "10",
            "description": "Spark Bonus Slot 5 percentage"
        },
        {
            "config_key": "spark_slot_6_percentage",
            "config_value": "7",
            "description": "Spark Bonus Slot 6 percentage"
        },
        {
            "config_key": "spark_slot_7_percentage",
            "config_value": "6",
            "description": "Spark Bonus Slot 7 percentage"
        },
        {
            "config_key": "spark_slot_8_percentage",
            "config_value": "6",
            "description": "Spark Bonus Slot 8 percentage"
        },
        {
            "config_key": "spark_slot_9_percentage",
            "config_value": "6",
            "description": "Spark Bonus Slot 9 percentage"
        },
        {
            "config_key": "spark_slot_10_percentage",
            "config_value": "4",
            "description": "Spark Bonus Slot 10 percentage"
        },
        {
            "config_key": "spark_slot_11_percentage",
            "config_value": "4",
            "description": "Spark Bonus Slot 11 percentage"
        },
        {
            "config_key": "spark_slot_12_percentage",
            "config_value": "4",
            "description": "Spark Bonus Slot 12 percentage"
        },
        {
            "config_key": "spark_slot_13_percentage",
            "config_value": "4",
            "description": "Spark Bonus Slot 13 percentage"
        },
        {
            "config_key": "spark_slot_14_percentage",
            "config_value": "4",
            "description": "Spark Bonus Slot 14 percentage"
        },
        
        # Binary Level Distribution (60% of total)
        {
            "config_key": "binary_level_1_percentage",
            "config_value": "30",
            "description": "Binary Level 1 payout percentage (of 60%)"
        },
        {
            "config_key": "binary_level_2_percentage",
            "config_value": "10",
            "description": "Binary Level 2 payout percentage (of 60%)"
        },
        {
            "config_key": "binary_level_3_percentage",
            "config_value": "10",
            "description": "Binary Level 3 payout percentage (of 60%)"
        },
        {
            "config_key": "binary_level_4_percentage",
            "config_value": "5",
            "description": "Binary Level 4 payout percentage (of 60%)"
        },
        {
            "config_key": "binary_level_5_percentage",
            "config_value": "5",
            "description": "Binary Level 5 payout percentage (of 60%)"
        },
        {
            "config_key": "binary_level_6_percentage",
            "config_value": "5",
            "description": "Binary Level 6 payout percentage (of 60%)"
        },
        {
            "config_key": "binary_level_7_percentage",
            "config_value": "5",
            "description": "Binary Level 7 payout percentage (of 60%)"
        },
        {
            "config_key": "binary_level_8_percentage",
            "config_value": "5",
            "description": "Binary Level 8 payout percentage (of 60%)"
        },
        {
            "config_key": "binary_level_9_percentage",
            "config_value": "5",
            "description": "Binary Level 9 payout percentage (of 60%)"
        },
        {
            "config_key": "binary_level_10_percentage",
            "config_value": "5",
            "description": "Binary Level 10 payout percentage (of 60%)"
        },
        {
            "config_key": "binary_level_11_percentage",
            "config_value": "3",
            "description": "Binary Level 11 payout percentage (of 60%)"
        },
        {
            "config_key": "binary_level_12_percentage",
            "config_value": "3",
            "description": "Binary Level 12 payout percentage (of 60%)"
        },
        {
            "config_key": "binary_level_13_percentage",
            "config_value": "3",
            "description": "Binary Level 13 payout percentage (of 60%)"
        },
        {
            "config_key": "binary_level_14_percentage",
            "config_value": "2",
            "description": "Binary Level 14 payout percentage (of 60%)"
        },
        {
            "config_key": "binary_level_15_percentage",
            "config_value": "2",
            "description": "Binary Level 15 payout percentage (of 60%)"
        },
        {
            "config_key": "binary_level_16_percentage",
            "config_value": "2",
            "description": "Binary Level 16 payout percentage (of 60%)"
        },
        
        # Matrix Level Distribution (40% of total)
        {
            "config_key": "matrix_level_1_percentage",
            "config_value": "10",
            "description": "Matrix Level 1 payout percentage (of 40%)"
        },
        {
            "config_key": "matrix_level_2_percentage",
            "config_value": "10",
            "description": "Matrix Level 2 payout percentage (of 40%)"
        },
        {
            "config_key": "matrix_level_3_percentage",
            "config_value": "15",
            "description": "Matrix Level 3 payout percentage (of 40%)"
        },
        {
            "config_key": "matrix_level_4_percentage",
            "config_value": "25",
            "description": "Matrix Level 4 payout percentage (of 40%)"
        },
        {
            "config_key": "matrix_level_5_percentage",
            "config_value": "40",
            "description": "Matrix Level 5 payout percentage (of 40%)"
        },
        
        # Leadership Stipend Distribution (Binary Slots 10-16)
        {
            "config_key": "leadership_slot_10_percentage",
            "config_value": "1.5",
            "description": "Leadership Stipend Slot 10 percentage"
        },
        {
            "config_key": "leadership_slot_11_percentage",
            "config_value": "1",
            "description": "Leadership Stipend Slot 11 percentage"
        },
        {
            "config_key": "leadership_slot_12_percentage",
            "config_value": "0.5",
            "description": "Leadership Stipend Slot 12 percentage"
        },
        {
            "config_key": "leadership_slot_13_percentage",
            "config_value": "0.5",
            "description": "Leadership Stipend Slot 13 percentage"
        },
        {
            "config_key": "leadership_slot_14_percentage",
            "config_value": "0.5",
            "description": "Leadership Stipend Slot 14 percentage"
        },
        {
            "config_key": "leadership_slot_15_percentage",
            "config_value": "0.5",
            "description": "Leadership Stipend Slot 15 percentage"
        },
        {
            "config_key": "leadership_slot_16_percentage",
            "config_value": "0.5",
            "description": "Leadership Stipend Slot 16 percentage"
        },
        
        # Jackpot Distribution
        {
            "config_key": "jackpot_open_winners_percentage",
            "config_value": "50",
            "description": "Jackpot Open Winners pool percentage"
        },
        {
            "config_key": "jackpot_top_sellers_percentage",
            "config_value": "30",
            "description": "Jackpot Top 20 Sellers pool percentage"
        },
        {
            "config_key": "jackpot_top_buyers_percentage",
            "config_value": "10",
            "description": "Jackpot Top 20 Buyers pool percentage"
        },
        {
            "config_key": "jackpot_newcomers_percentage",
            "config_value": "10",
            "description": "Jackpot Newcomers pool percentage"
        },
        
        # Newcomer Growth Support Distribution
        {
            "config_key": "newcomer_first_percentage",
            "config_value": "40",
            "description": "Newcomer Growth Support 1st place percentage"
        },
        {
            "config_key": "newcomer_second_percentage",
            "config_value": "35",
            "description": "Newcomer Growth Support 2nd place percentage"
        },
        {
            "config_key": "newcomer_third_percentage",
            "config_value": "25",
            "description": "Newcomer Growth Support 3rd place percentage"
        }
    ]
    
    print("🌱 Seeding System Configuration...")
    
    for config_data in configs:
        existing_config = SystemConfig.objects(config_key=config_data["config_key"]).first()
        
        if existing_config:
            print(f"✅ Config {config_data['config_key']} already exists")
        else:
            config = SystemConfig(**config_data)
            config.save()
            print(f"✅ Created Config: {config_data['config_key']} = {config_data['config_value']}%")
    
    print("🎯 System Configuration seeding completed!")

def main():
    """Main seeding function"""
    print("🚀 Starting BitGPT MLM Platform Data Seeding...")
    print("=" * 50)
    
    try:
        # Connect to database
        connect_to_db()
        print("✅ Database connected successfully!")
        
        # Seed all data
        seed_slot_catalog()
        print()
        
        seed_matrix_slots()
        print()
        
        seed_global_slots()
        print()
        
        seed_system_config()
        print()
        
        print("🎉 All data seeding completed successfully!")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
