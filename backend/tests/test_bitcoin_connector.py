"""
Test suite for the Bitcoin OSINT connector.

Tests address validation, blockchain data retrieval, normalization,
error handling, and integration with the existing investigation pipeline.

Uses mocked HTTP responses - does NOT make live calls to Blockstream API.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.connectors.bitcoin import BitcoinConnector
from app.connectors.bitcoin.validator import (
    validate_bitcoin_address,
    get_address_type,
)
from app.connectors.types import Identifier, IdentifierType, ConnectorStatus
from app.connectors.registry import registry
from app.connectors.base import BaseConnector
from app.normalizers.bitcoin import BitcoinNormalizer
from app.normalizers.types import FactType


class TestBitcoinAddressValidation:
    """Test Bitcoin address format validation."""
    
    def test_valid_legacy_p2pkh_address(self):
        """Test valid legacy P2PKH address (1...)."""
        address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Genesis block
        assert validate_bitcoin_address(address)
        assert get_address_type(address) == "legacy_p2pkh"
    
    def test_valid_p2sh_address(self):
        """Test valid P2SH address (3...)."""
        address = "3J98t1WpEZ73CNmYviecrnyiWrnqRhWNLy"
        assert validate_bitcoin_address(address)
        assert get_address_type(address) == "p2sh"
    
    def test_valid_bech32_segwit_address(self):
        """Test valid Bech32 SegWit address (bc1q...)."""
        address = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
        assert validate_bitcoin_address(address)
        assert get_address_type(address) == "bech32_segwit_v0"
    
    def test_valid_taproot_address(self):
        """Test valid Taproot address (bc1p...)."""
        address = "bc1pmzfrwwndsqmk5yh69yjr5lfgfg4ev8c0tsc06e"
        assert validate_bitcoin_address(address)
        assert get_address_type(address) == "bech32_segwit_v1_taproot"
    
    def test_invalid_address_format(self):
        """Test invalid Bitcoin address."""
        assert not validate_bitcoin_address("invalid_address")
        assert not validate_bitcoin_address("1234567890")
        assert not validate_bitcoin_address("bc1invalid")
    
    def test_rejects_private_key(self):
        """Test that private keys are rejected."""
        # 64-char hex string (private key format)
        private_key = "E9873D79C6D87DC0FB6A5778633389F4453213303DA61F20BD67FC233AA33262"
        assert not validate_bitcoin_address(private_key)
    
    def test_rejects_wif_private_key(self):
        """Test that WIF private keys are rejected."""
        wif_key = "5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ"
        assert not validate_bitcoin_address(wif_key)
    
    def test_rejects_seed_phrase(self):
        """Test that seed phrases are rejected."""
        seed = "witch collapse practice feed shame open despair creek road again ice least"
        assert not validate_bitcoin_address(seed)
    
    def test_empty_address(self):
        """Test empty address handling."""
        assert not validate_bitcoin_address("")
        assert not validate_bitcoin_address(None)


class TestBitcoinConnectorRegistration:
    """Test that the Bitcoin connector is properly registered."""
    
    def test_connector_is_registered(self):
        """Verify the connector is in the global registry."""
        registered = registry.get_connector("bitcoin")
        assert registered is BitcoinConnector
    
    def test_connector_registered_for_wallet_type(self):
        """Verify the connector is registered for WALLET_ADDRESS identifier type."""
        connectors = registry.get_connectors_for_identifier_type(IdentifierType.WALLET_ADDRESS)
        assert BitcoinConnector in connectors
    
    def test_connector_not_registered_for_other_types(self):
        """Verify the connector is NOT registered for non-wallet types."""
        for id_type in [
            IdentifierType.EMAIL,
            IdentifierType.PHONE,
            IdentifierType.USERNAME,
            IdentifierType.DOMAIN,
            IdentifierType.IP,
            IdentifierType.IMAGE,
        ]:
            connectors = registry.get_connectors_for_identifier_type(id_type)
            assert BitcoinConnector not in connectors


class TestBitcoinConnectorStructure:
    """Test the connector's class structure and configuration."""
    
    def test_subclasses_base_connector(self):
        """Verify BitcoinConnector inherits from BaseConnector."""
        assert issubclass(BitcoinConnector, BaseConnector)
    
    def test_has_correct_name(self):
        """Verify the connector has the correct name."""
        assert BitcoinConnector.name == "bitcoin"
    
    def test_supported_identifier_types(self):
        """Verify only WALLET_ADDRESS is supported."""
        assert BitcoinConnector.supported_identifier_types == frozenset(
            {IdentifierType.WALLET_ADDRESS}
        )
    
    def test_has_timeout_configured(self):
        """Verify timeout is configured (blockchain APIs can be slow)."""
        assert BitcoinConnector.timeout_seconds > 0
        assert BitcoinConnector.timeout_seconds >= 20.0  # Should be at least 20 seconds


class TestBitcoinConnectorExecution:
    """Test the connector's fetch behavior with mocked responses."""
    
    @pytest.mark.asyncio
    async def test_fetch_valid_address_with_balance(self):
        """Test fetching data for a valid address with balance."""
        connector = BitcoinConnector()
        identifier = Identifier(
            value="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            type=IdentifierType.WALLET_ADDRESS
        )
        
        # Mock API responses
        mock_stats = {
            "chain_stats": {
                "funded_txo_sum": 100000000,  # 1 BTC received
                "spent_txo_sum": 50000000,     # 0.5 BTC spent
                "tx_count": 10,
            },
            "mempool_stats": {
                "funded_txo_sum": 0,
                "spent_txo_sum": 0,
            },
        }
        
        mock_txs = [
            {
                "txid": "abc123",
                "status": {"block_time": 1609459200},
                "vin": [],
                "vout": [{"scriptpubkey_address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh", "value": 10000000}],
            }
        ]
        
        mock_utxos = [
            {"txid": "def456", "vout": 0, "value": 50000000}
        ]
        
        with patch.object(connector, "_get_address_stats", new=AsyncMock(return_value=mock_stats)), \
             patch.object(connector, "_get_address_transactions", new=AsyncMock(return_value=mock_txs)), \
             patch.object(connector, "_get_address_utxos", new=AsyncMock(return_value=mock_utxos)):
            
            result = await connector.fetch(identifier)
            
            assert result["valid"] is True
            assert result["address_type"] == "bech32_segwit_v0"
            assert result["balance_confirmed_satoshi"] == 50000000
            assert result["tx_count"] == 10
            assert result["total_received_satoshi"] == 100000000
            assert result["total_sent_satoshi"] == 50000000
            assert len(result["transactions"]) > 0
            assert len(result["utxos"]) > 0
            assert result["error"] is None
    
    @pytest.mark.asyncio
    async def test_fetch_invalid_address(self):
        """Test fetching data for an invalid address."""
        connector = BitcoinConnector()
        identifier = Identifier(
            value="invalid_address",
            type=IdentifierType.WALLET_ADDRESS
        )
        
        result = await connector.fetch(identifier)
        
        assert result["valid"] is False
        assert result["error"] == "Invalid Bitcoin address format"
        assert result["balance_confirmed_satoshi"] == 0
    
    @pytest.mark.asyncio
    async def test_fetch_address_not_found(self):
        """Test fetching data for valid but unused address."""
        connector = BitcoinConnector()
        identifier = Identifier(
            value="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            type=IdentifierType.WALLET_ADDRESS
        )
        
        # Mock empty responses (address exists but has no activity)
        mock_stats = {
            "chain_stats": {
                "funded_txo_sum": 0,
                "spent_txo_sum": 0,
                "tx_count": 0,
            },
            "mempool_stats": {
                "funded_txo_sum": 0,
                "spent_txo_sum": 0,
            },
        }
        
        with patch.object(connector, "_get_address_stats", new=AsyncMock(return_value=mock_stats)), \
             patch.object(connector, "_get_address_transactions", new=AsyncMock(return_value=[])), \
             patch.object(connector, "_get_address_utxos", new=AsyncMock(return_value=[])):
            
            result = await connector.fetch(identifier)
            
            assert result["valid"] is True
            assert result["tx_count"] == 0
            assert result["balance_confirmed_satoshi"] == 0
            assert len(result["transactions"]) == 0
            assert result["error"] is None
    
    @pytest.mark.asyncio
    async def test_fetch_http_429_rate_limit(self):
        """Test handling of HTTP 429 rate limit error."""
        connector = BitcoinConnector()
        identifier = Identifier(
            value="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            type=IdentifierType.WALLET_ADDRESS
        )
        
        # Mock HTTP 429 error
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 429
        error = httpx.HTTPStatusError("Rate limited", request=MagicMock(), response=mock_response)
        
        with patch.object(connector, "_get_address_stats", side_effect=error):
            result = await connector.fetch(identifier)
            
            assert result["valid"] is True
            assert "Rate limited" in result["error"]
            assert "429" in result["error"]
    
    @pytest.mark.asyncio
    async def test_fetch_http_500_server_error(self):
        """Test handling of HTTP 500 server error."""
        connector = BitcoinConnector()
        identifier = Identifier(
            value="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            type=IdentifierType.WALLET_ADDRESS
        )
        
        # Mock HTTP 500 error
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 500
        error = httpx.HTTPStatusError("Server error", request=MagicMock(), response=mock_response)
        
        with patch.object(connector, "_get_address_stats", side_effect=error):
            result = await connector.fetch(identifier)
            
            assert result["valid"] is True
            assert "server error" in result["error"].lower()
            assert "500" in result["error"]
    
    @pytest.mark.asyncio
    async def test_fetch_timeout(self):
        """Test handling of request timeout."""
        connector = BitcoinConnector()
        identifier = Identifier(
            value="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            type=IdentifierType.WALLET_ADDRESS
        )
        
        # Mock timeout
        import httpx
        with patch.object(connector, "_get_address_stats", side_effect=httpx.TimeoutException("Timeout")):
            result = await connector.fetch(identifier)
            
            assert result["valid"] is True
            assert "timed out" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_fetch_network_error(self):
        """Test handling of network error."""
        connector = BitcoinConnector()
        identifier = Identifier(
            value="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            type=IdentifierType.WALLET_ADDRESS
        )
        
        # Mock network error
        import httpx
        with patch.object(connector, "_get_address_stats", side_effect=httpx.RequestError("Connection failed")):
            result = await connector.fetch(identifier)
            
            assert result["valid"] is True
            assert "Network error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_run_produces_envelope(self):
        """Verify run() produces a RawResponseEnvelope."""
        connector = BitcoinConnector()
        identifier = Identifier(
            value="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            type=IdentifierType.WALLET_ADDRESS
        )
        
        # Mock minimal response
        mock_data = {
            "chain_stats": {"funded_txo_sum": 0, "spent_txo_sum": 0, "tx_count": 0},
            "mempool_stats": {"funded_txo_sum": 0, "spent_txo_sum": 0},
        }
        
        with patch.object(connector, "_get_address_stats", new=AsyncMock(return_value=mock_data)), \
             patch.object(connector, "_get_address_transactions", new=AsyncMock(return_value=[])), \
             patch.object(connector, "_get_address_utxos", new=AsyncMock(return_value=[])):
            
            envelope = await connector.run(identifier)
            
            assert envelope.connector_name == "bitcoin"
            assert envelope.identifier == identifier
            assert envelope.status == ConnectorStatus.SUCCEEDED
            assert envelope.raw_payload is not None
            assert isinstance(envelope.raw_payload, dict)


class TestBitcoinNormalizer:
    """Test the Bitcoin normalizer."""
    
    def test_normalizer_is_registered(self):
        """Verify the normalizer is registered."""
        from app.normalizers.registry import normalizer_registry
        normalizer = normalizer_registry.get_normalizer("bitcoin")
        assert normalizer is BitcoinNormalizer
    
    def test_normalize_valid_address_with_balance(self):
        """Test normalization of address with balance."""
        normalizer = BitcoinNormalizer()
        
        raw_payload = {
            "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "valid": True,
            "address_type": "bech32_segwit_v0",
            "balance_confirmed_satoshi": 100000000,  # 1 BTC
            "balance_unconfirmed_satoshi": 0,
            "tx_count": 5,
            "total_received_satoshi": 200000000,
            "total_sent_satoshi": 100000000,
            "transactions": [],
            "utxos": [],
            "first_seen": 1609459200,
            "last_seen": 1640995200,
            "error": None,
        }
        
        facts = normalizer.normalize(raw_payload)
        
        # Should produce multiple facts
        assert len(facts) > 0
        
        # Check wallet address fact
        wallet_facts = [f for f in facts if f.fact_type == FactType.WALLET_ADDRESS]
        assert len(wallet_facts) == 1
        assert wallet_facts[0].value == "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
        assert wallet_facts[0].confidence == 1.00
        
        # Check balance fact
        balance_facts = [f for f in facts if f.fact_type == FactType.GENERIC and "BTC" in f.value and "balance" in f.metadata.get("data_type", "")]
        assert len(balance_facts) > 0
        
        # Check transaction count fact
        tx_facts = [f for f in facts if "transaction" in f.value.lower()]
        assert len(tx_facts) > 0
    
    def test_normalize_invalid_address(self):
        """Test normalization of invalid address."""
        normalizer = BitcoinNormalizer()
        
        raw_payload = {
            "address": "invalid_address",
            "valid": False,
            "address_type": None,
            "error": "Invalid Bitcoin address format",
        }
        
        facts = normalizer.normalize(raw_payload)
        
        # Should still produce wallet fact for audit trail
        assert len(facts) == 1
        assert facts[0].fact_type == FactType.WALLET_ADDRESS
        assert facts[0].confidence < 0.5  # Low confidence for invalid
    
    def test_normalize_transaction_for_timeline(self):
        """Test that transaction facts include timeline data."""
        normalizer = BitcoinNormalizer()
        
        raw_payload = {
            "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "valid": True,
            "address_type": "bech32_segwit_v0",
            "balance_confirmed_satoshi": 0,
            "balance_unconfirmed_satoshi": 0,
            "tx_count": 1,
            "total_received_satoshi": 10000000,
            "total_sent_satoshi": 10000000,
            "transactions": [
                {
                    "txid": "abc123",
                    "status": {"block_time": 1609459200},
                    "vin": [],
                    "vout": [
                        {
                            "scriptpubkey_address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
                            "value": 10000000
                        }
                    ],
                }
            ],
            "utxos": [],
            "error": None,
        }
        
        facts = normalizer.normalize(raw_payload)
        
        # Check for transaction facts with occurred_at timestamps
        tx_facts = [f for f in facts if f.occurred_at is not None and "Transaction" in f.value]
        assert len(tx_facts) > 0
        assert isinstance(tx_facts[0].occurred_at, datetime)


class TestBitcoinConnectorBehavior:
    """Test connector behavior and constraints."""
    
    def test_does_not_access_database(self):
        """Verify the connector does NOT import or use database modules."""
        import inspect
        from app.connectors.bitcoin import connector as bitcoin_module
        
        source = inspect.getsource(bitcoin_module)
        
        # Should not import database-related modules
        assert "from app.db" not in source
        assert "from app.models" not in source
        assert "from app.repositories" not in source
        assert "Session" not in source
        assert "sessionmaker" not in source
    
    def test_does_not_normalize(self):
        """Verify the connector does NOT perform normalization."""
        import inspect
        from app.connectors.bitcoin import connector as bitcoin_module
        
        source = inspect.getsource(bitcoin_module)
        
        # Should not import normalization modules
        assert "from app.normalization" not in source
        assert "NormalizedFact" not in source
    
    def test_does_not_handle_private_keys(self):
        """Verify the connector does NOT handle private keys."""
        import inspect
        from app.connectors.bitcoin import validator as validator_module
        
        source = inspect.getsource(validator_module)
        
        # Should explicitly reject private keys
        assert "private" in source.lower()
        assert "seed" in source.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
