"""
Verify earning amounts are correct
"""
from core.db import connect_to_db
from modules.wallet.service import WalletService
from modules.wallet.model import WalletLedger
from bson import ObjectId
from decimal import Decimal

def verify():
    connect_to_db()
    
    user_id = "68dc13a98b174277bc40cc12"
    user_oid = ObjectId(user_id)
    
    print("Manual calculation from database:")
    print("=" * 60)
    
    # Get all credits
    all_credits = WalletLedger.objects(user_id=user_oid, type='credit').only('amount', 'currency', 'reason')
    
    binary_total = {"USDT": Decimal('0'), "BNB": Decimal('0')}
    matrix_total = {"USDT": Decimal('0'), "BNB": Decimal('0')}
    global_total = {"USDT": Decimal('0'), "BNB": Decimal('0')}
    
    binary_count = 0
    matrix_count = 0
    global_count = 0
    
    for entry in all_credits:
        reason = str(entry.reason or '').lower()
        currency = str(entry.currency or 'USDT').upper()
        amount = Decimal(str(entry.amount or 0))
        
        if reason.startswith('binary_'):
            if currency not in binary_total:
                binary_total[currency] = Decimal('0')
            binary_total[currency] += amount
            binary_count += 1
        elif reason.startswith('matrix_'):
            if currency not in matrix_total:
                matrix_total[currency] = Decimal('0')
            matrix_total[currency] += amount
            matrix_count += 1
        elif reason.startswith('global_'):
            if currency not in global_total:
                global_total[currency] = Decimal('0')
            global_total[currency] += amount
            global_count += 1
    
    print(f"\nBinary: {binary_count} transactions")
    for curr, amt in binary_total.items():
        if amt > 0:
            print(f"  {curr}: {float(amt)}")
    
    print(f"\nMatrix: {matrix_count} transactions")
    for curr, amt in matrix_total.items():
        if amt > 0:
            print(f"  {curr}: {float(amt)}")
    
    print(f"\nGlobal: {global_count} transactions")
    for curr, amt in global_total.items():
        if amt > 0:
            print(f"  {curr}: {float(amt)}")
    
    print("\n" + "=" * 60)
    print("API Response:")
    print("=" * 60)
    
    service = WalletService()
    result = service.get_earning_statistics(user_id)
    
    if result.get("success"):
        data = result['data']
        print(f"\nBinary: {data['binary']['total_earnings']}")
        print(f"Matrix: {data['matrix']['total_earnings']}")
        print(f"Global: {data['global']['total_earnings']}")
        
        print("\n" + "=" * 60)
        print("MATCH CHECK:")
        print("=" * 60)
        
        # Check if they match
        api_binary_usdt = data['binary']['total_earnings']['USDT']
        api_binary_bnb = data['binary']['total_earnings']['BNB']
        api_matrix_usdt = data['matrix']['total_earnings']['USDT']
        api_matrix_bnb = data['matrix']['total_earnings']['BNB']
        api_global_usdt = data['global']['total_earnings']['USDT']
        api_global_bnb = data['global']['total_earnings']['BNB']
        
        print(f"Binary USDT: {float(binary_total.get('USDT', 0))} == {api_binary_usdt} ? {abs(float(binary_total.get('USDT', 0)) - api_binary_usdt) < 0.001}")
        print(f"Binary BNB: {float(binary_total.get('BNB', 0))} == {api_binary_bnb} ? {abs(float(binary_total.get('BNB', 0)) - api_binary_bnb) < 0.001}")
        print(f"Matrix USDT: {float(matrix_total.get('USDT', 0))} == {api_matrix_usdt} ? {abs(float(matrix_total.get('USDT', 0)) - api_matrix_usdt) < 0.001}")
        print(f"Matrix BNB: {float(matrix_total.get('BNB', 0))} == {api_matrix_bnb} ? {abs(float(matrix_total.get('BNB', 0)) - api_matrix_bnb) < 0.001}")
        print(f"Global USDT: {float(global_total.get('USDT', 0))} == {api_global_usdt} ? {abs(float(global_total.get('USDT', 0)) - api_global_usdt) < 0.001}")
        print(f"Global BNB: {float(global_total.get('BNB', 0))} == {api_global_bnb} ? {abs(float(global_total.get('BNB', 0)) - api_global_bnb) < 0.001}")

if __name__ == "__main__":
    verify()

