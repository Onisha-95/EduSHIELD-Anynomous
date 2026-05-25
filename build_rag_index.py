"""
BUILD RAG INDEX
===============
Run this after run_ingestion.py to build the ChromaDB vector index.

Usage:
    cd guard_agent_system
    python3 build_rag_index.py

What it does:
    1. Connects to Neo4j
    2. Pulls all 1,405 facts
    3. Embeds each with sentence-transformers (all-MiniLM-L6-v2)
    4. Stores in ChromaDB at data/chroma_index/
    5. Tests retrieval on 5 sample queries
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

from core.neo4j_client import Neo4jKGClient
from core.rag_system    import RAGSystem
from config import (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
                    NEO4J_DATABASE, CHROMA_PATH)

def main():
    print("\
" + "="*60)
    print("   RAG INDEX BUILDER")
    print("="*60)

    # Connect to Neo4j
    print("\
 Connecting to Neo4j...")
    kg = Neo4jKGClient(
        uri=NEO4J_URI, user=NEO4J_USER,
        password=NEO4J_PASSWORD, database=NEO4J_DATABASE
    )

    stats = kg.get_stats()
    print(f"   KG contains: {stats['concepts']} concepts, {stats['facts']} facts")

    if stats["facts"] == 0:
        print("[x] No facts in KG — run python3 run_ingestion.py first.")
        return

    # Build RAG index
    rag = RAGSystem(kg, CHROMA_PATH)
    total = rag.build_index()

    if total == 0:
        print("[x] Index build failed.")
        return

    # Test retrieval on sample queries
    test_queries = [
        "what is a while loop",
        "how do if statements work",
        "what are variables",
        "what is a function",
        "how does a for loop work",
    ]
    rag.test_retrieval(test_queries)

    print("="*60)
    print(f"[ok] RAG index ready at: {CHROMA_PATH}")
    print(f"   {total} facts indexed and searchable")
    print("="*60 + "\
")

    kg.close()

if __name__ == "__main__":
    main()