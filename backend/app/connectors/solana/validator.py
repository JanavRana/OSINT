"""
Solana wallet address validation.

Validates standard Solana address formats:
- Base58 encoded string between 32 and 44 characters
- Excludes non-Base58 characters (0, O, I, l)
"""

import re
from typing import Optional


def validate_solana_address(address: str) -> bool:
    """
    Validate a Solana wallet address format.
    
    Args:
        address: The Solana address to validate
        
    Returns:
        True if the address appears to be a valid Solana address format
    """
    if not address or not isinstance(address, str):
        return False
    
    address = address.strip()
    
    # Exclude EVM (0x...) and Bitcoin prefixes (1..., 3..., bc1...)
    if address.startswith(("0x", "1", "3", "bc1", "ltc1")):
        return False
    
    if not (32 <= len(address) <= 44):
        return False
    
    # Base58 character set
    base58_pattern = r"^[1-9A-HJ-NP-Za-km-z]{32,44}$"
    return bool(re.match(base58_pattern, address))


def get_address_type(address: str) -> Optional[str]:
    """
    Determine the type of Solana address.
    """
    if not validate_solana_address(address):
        return None
    return "solana_account"
