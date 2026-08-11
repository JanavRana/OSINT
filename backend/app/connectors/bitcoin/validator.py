"""
Bitcoin address validation.

Validates common Bitcoin address formats:
- Legacy P2PKH (1...)
- P2SH (3...)
- Bech32 SegWit (bc1...)

Does NOT handle:
- Private keys
- Seed phrases
- Wallet recovery
"""

import re
from typing import Optional


def validate_bitcoin_address(address: str) -> bool:
    """
    Validate a Bitcoin address format.
    
    Args:
        address: The Bitcoin address to validate
        
    Returns:
        True if the address appears to be a valid Bitcoin address format
    """
    if not address or not isinstance(address, str):
        return False
    
    address = address.strip()
    
    # Check for private keys or seed phrases (reject immediately)
    if _looks_like_private_key_or_seed(address):
        return False
    
    # Legacy P2PKH addresses (1...)
    if _is_legacy_p2pkh(address):
        return True
    
    # P2SH addresses (3...)
    if _is_p2sh(address):
        return True
    
    # Bech32 SegWit addresses (bc1...)
    if _is_bech32(address):
        return True
    
    return False


def get_address_type(address: str) -> Optional[str]:
    """
    Determine the type of Bitcoin address.
    
    Args:
        address: The Bitcoin address
        
    Returns:
        Address type string or None if invalid
    """
    if not validate_bitcoin_address(address):
        return None
    
    address = address.strip()
    
    if address.startswith('1'):
        return "legacy_p2pkh"
    elif address.startswith('3'):
        return "p2sh"
    elif address.startswith('bc1q'):
        return "bech32_segwit_v0"
    elif address.startswith('bc1p'):
        return "bech32_segwit_v1_taproot"
    elif address.startswith('bc1'):
        return "bech32_segwit"
    
    return "unknown"


def _looks_like_private_key_or_seed(text: str) -> bool:
    """Check if the input looks like a private key or seed phrase."""
    text = text.strip()
    
    # Private keys are typically 64 hex characters or start with specific prefixes
    if len(text) == 64 and all(c in '0123456789abcdefABCDEF' for c in text):
        return True
    
    # WIF private keys
    if text.startswith(('5', 'K', 'L')) and len(text) in (51, 52):
        return True
    
    # Seed phrases contain multiple words
    words = text.split()
    if len(words) in (12, 15, 18, 21, 24):
        # Likely a seed phrase
        return True
    
    # Extended private keys
    if text.startswith(('xprv', 'yprv', 'zprv', 'tprv')):
        return True
    
    return False


def _is_legacy_p2pkh(address: str) -> bool:
    """
    Validate legacy P2PKH address (starts with 1).
    
    Legacy addresses are 26-35 characters, base58 encoded.
    """
    if not address.startswith('1'):
        return False
    
    if not (26 <= len(address) <= 35):
        return False
    
    # Base58 character set (excludes 0, O, I, l to avoid confusion)
    base58_pattern = r'^[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]+$'
    return bool(re.match(base58_pattern, address))


def _is_p2sh(address: str) -> bool:
    """
    Validate P2SH address (starts with 3).
    
    P2SH addresses are 26-35 characters, base58 encoded.
    """
    if not address.startswith('3'):
        return False
    
    if not (26 <= len(address) <= 35):
        return False
    
    base58_pattern = r'^[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]+$'
    return bool(re.match(base58_pattern, address))


def _is_bech32(address: str) -> bool:
    """
    Validate Bech32 SegWit address (starts with bc1).
    
    Bech32 addresses use lowercase letters and numbers, no mixed case.
    Length varies but typically 42-62 characters for mainnet.
    """
    if not address.startswith('bc1'):
        return False
    
    # Bech32 must be all lowercase or all uppercase (but lowercase is standard)
    if address != address.lower() and address != address.upper():
        return False
    
    address_lower = address.lower()
    
    if not (42 <= len(address_lower) <= 90):
        return False
    
    # Bech32 character set
    bech32_charset = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
    
    # After 'bc1', rest should be bech32 characters
    payload = address_lower[3:]
    return all(c in bech32_charset for c in payload)
