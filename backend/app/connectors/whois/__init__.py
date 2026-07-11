"""
connectors/whois/

WHOIS connector module for OSINT aggregator (Section 11.2 connector
implementation).

This module implements the WHOIS lookup connector, one of the six
reference connectors specified in Section 4.1 of MASTER_DESIGN.md.

The connector accepts DOMAIN identifiers only, performs WHOIS lookups
using the python-whois library, and returns raw responses without
normalization or database interaction.
"""

from .connector import WhoisConnector

__all__ = ["WhoisConnector"]
