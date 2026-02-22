"""
Knowledge Graph module — Legal Knowledge Graph for Vietnamese law.

Structure:
    models.py         — Domain models (NodeType, EdgeType, GraphNode, etc.)
    schema_mapper.py  — Schema format conversion
    routes.py         — FastAPI routes

    stores/           — Pluggable graph database backends
        base.py       — GraphRepository ABC
        neo4j_store.py — Neo4j implementation

    builders/         — Pluggable graph construction strategies
        config.py     — Builder configuration
        llm_builder.py — LLM-based entity/relation extraction

To add a new graph store or builder, implement the ABC and register in container.
"""
