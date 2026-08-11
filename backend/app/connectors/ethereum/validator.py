"""
Ethereum (EVM) wallet address validation.

Validates standard EVM address formats:
- 0x-prefixed 40-character hexadecimal strings
- Case-insensitive (supports checksummed and lowercase addresses)

Does NOT handle:
- Private keys
- Seed phrases
"""

import re
from typing import Optional


def validate_ethereum_address(address: str) -> bool:
    """
    Validate an Ethereum/EVM wallet address format.
    
    Args:
        address: The Ethereum address to validate
        
    Returns:
        True if the address appears to be a valid EVM address format
    """
    if not address or not isinstance(address, str):
        return False
    
    address = address.strip()
    
    # Must match 0x followed by 40 hex characters
    pattern = r"^0x[a-fA-F0-9]{40}$"
    return bool(re.match(pattern, address))


def get_address_type(address: str) -> Optional[str]:
    """
    Determine the type of EVM address.
    """
    if not validate_ethereum_address(address):
        return None
    return "evm_account"
