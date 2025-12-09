#!/usr/bin/env python3
"""Direct test to check if Graph Adapter is initialized in container"""
import requests

BASE_URL = "http://localhost:8001/api/v1"

# Make a simple request to trigger container initialization
response = requests.get(f"{BASE_URL}/health")
print(f"Health check: {response.json()}")

# Now check logs from the orchestrator terminal to see Graph Adapter initialization
print("\n" + "="*80)
print("Check the 'conda' terminal for logs about Graph Adapter initialization")
print("Look for messages like:")
print("  - '🔗 Connecting to Neo4j: bolt://localhost:7687'")
print("  - '✓ Neo4j Graph Adapter initialized successfully'")
print("  - '⚠ Could not import Neo4jGraphAdapter'")
print("  - '⚠ Could not connect to Neo4j'")
print("="*80)
