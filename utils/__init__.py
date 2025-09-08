def program_default_currency(program: str) -> str:
    """Return default currency code for a given program."""
    mapping = {
        'binary': 'BNB',
        'matrix': 'USDT',
        'global': 'USD',
    }
    return mapping.get(program, 'USDT')

def ensure_currency_for_program(program: str, currency: str) -> str:
    """Ensure currency matches program; if empty or mismatch, use default."""
    default = program_default_currency(program)
    return currency or default

