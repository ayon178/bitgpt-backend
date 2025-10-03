"""
Direct test of earning statistics to see where time is spent
"""
from core.db import connect_to_db
from modules.wallet.service import WalletService
import time

def test():
    connect_to_db()
    print("Database connected")
    print("-" * 60)
    
    service = WalletService()
    user_id = "68dc13a98b174277bc40cc12"
    
    # First call
    print("\n1st API call:")
    start = time.time()
    result = service.get_earning_statistics(user_id)
    end = time.time()
    print(f"External measured time: {end - start:.3f}s")
    print(f"Success: {result.get('success')}")
    
    # Second call
    print("\n2nd API call:")
    start = time.time()
    result = service.get_earning_statistics(user_id)
    end = time.time()
    print(f"External measured time: {end - start:.3f}s")
    print(f"Success: {result.get('success')}")

if __name__ == "__main__":
    test()

