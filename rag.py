"""
Package alias for RAG department.
Allows lowercase `import rag` and `from rag import ...` to work identically to `RAG`.
"""
import sys
import RAG

sys.modules["rag"] = RAG
sys.modules["rag.config"] = sys.modules.get("RAG.config")
sys.modules["rag.rag_database"] = sys.modules.get("RAG.rag_database")
sys.modules["rag.rag_service"] = sys.modules.get("RAG.rag_service")
sys.modules["rag.llm_client"] = sys.modules.get("RAG.llm_client")
sys.modules["rag.analytics"] = sys.modules.get("RAG.analytics")
sys.modules["rag.strategy_knowledge_data"] = sys.modules.get("RAG.strategy_knowledge_data")

from RAG import *
