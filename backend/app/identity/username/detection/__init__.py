"""
Detection strategies for username platforms.

Each strategy implements a different method for determining
whether a username exists on a platform.
"""

# Import strategies to register them
from . import strategies  # noqa: F401

__all__ = ['strategies']
