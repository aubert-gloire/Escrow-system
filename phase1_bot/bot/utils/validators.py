"""
Validators for input validation
"""

import re
from typing import Tuple


class AddressValidator:
    """Validate cryptocurrency addresses."""
    
    # Bitcoin address pattern (P2PKH, P2SH, Bech32)
    BTC_PATTERN = re.compile(r"^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$")
    
    # Ethereum/USDT address pattern
    ETH_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")
    
    # Litecoin address pattern
    LTC_PATTERN = re.compile(r"^[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}$")
    
    @staticmethod
    def validate_btc_address(address: str) -> Tuple[bool, str]:
        """Validate Bitcoin address."""
        if not address or len(address) < 26:
            return False, "Invalid Bitcoin address format"
        
        if not AddressValidator.BTC_PATTERN.match(address):
            return False, "Bitcoin address must start with 1, 3, or bc1"
        
        return True, "✅ Valid Bitcoin address"
    
    @staticmethod
    def validate_eth_address(address: str) -> Tuple[bool, str]:
        """Validate Ethereum address."""
        if not address or len(address) != 42:
            return False, "Ethereum address must be 42 characters"
        
        if not AddressValidator.ETH_PATTERN.match(address):
            return False, "Invalid Ethereum address format (must be 0x...)"
        
        return True, "✅ Valid Ethereum address"
    
    @staticmethod
    def validate_usdt_address(address: str) -> Tuple[bool, str]:
        """Validate USDT address (same as Ethereum)."""
        return AddressValidator.validate_eth_address(address)
    
    @staticmethod
    def validate_ltc_address(address: str) -> Tuple[bool, str]:
        """Validate Litecoin address."""
        if not address or len(address) < 26:
            return False, "Invalid Litecoin address format"
        
        if not AddressValidator.LTC_PATTERN.match(address):
            return False, "Litecoin address must start with L or M"
        
        return True, "✅ Valid Litecoin address"
    
    @staticmethod
    def validate_address(address: str, currency: str) -> Tuple[bool, str]:
        """Validate address for given currency."""
        if not address:
            return False, "Address cannot be empty"
        
        address = address.strip()
        
        if currency == "BTC":
            return AddressValidator.validate_btc_address(address)
        elif currency == "USDT":
            return AddressValidator.validate_usdt_address(address)
        elif currency == "LTC":
            return AddressValidator.validate_ltc_address(address)
        else:
            return False, f"Unsupported currency: {currency}"


class AmountValidator:
    """Validate deal amounts."""
    
    @staticmethod
    def validate_amount(amount_str: str, max_amount: float = 100000) -> Tuple[bool, float, str]:
        """Validate and parse deal amount."""
        try:
            amount = float(amount_str)
            
            if amount <= 0:
                return False, 0, "Amount must be greater than 0"
            
            if amount > max_amount:
                return False, 0, f"Amount exceeds maximum of {max_amount}"
            
            return True, amount, f"✅ Valid amount: {amount}"
        except ValueError:
            return False, 0, "Invalid amount format. Please enter a number."


class TxHashValidator:
    """Validate transaction hashes."""
    
    @staticmethod
    def validate_tx_hash(tx_hash: str, currency: str) -> Tuple[bool, str]:
        """Validate transaction hash."""
        if not tx_hash or len(tx_hash) < 32:
            return False, "Invalid transaction hash"
        
        # Basic format check (alphanumeric only)
        if not re.match(r"^[a-fA-F0-9]{32,}$", tx_hash):
            return False, "Transaction hash must be hexadecimal"
        
        return True, f"✅ Transaction hash recorded"
