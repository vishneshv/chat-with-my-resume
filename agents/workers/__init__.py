"""
Worker-style integrations (logical layer).

Execution is centralized in `graph.nodes.tool_executor_node`, which calls:
- Resume / KB → `tools.rag_tool.search_knowledge_base`
- GitHub → `tools.github_tool` helpers

Add dedicated modules here when a worker needs its own orchestration logic.
"""
