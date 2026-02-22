"""
Knowledge Graph builders — pluggable graph construction strategies.

To add a new builder (e.g. rule-based, hybrid):
  1. Create a new file in this directory (e.g. rule_builder.py)
  2. Implement the builder with extract() method returning entities and relations
  3. Register it in the container
"""
