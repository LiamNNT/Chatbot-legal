"""
Knowledge Graph stores — pluggable graph database backends.

To add a new store (e.g. Neptune, NetworkX for testing):
  1. Create a new file in this directory (e.g. networkx_store.py)
  2. Implement the GraphRepository ABC from base.py
  3. Register it in the container
"""

from .base import GraphRepository  # noqa: F401
