"""V28 provider-neutral creative agent services.

The package deliberately exposes bounded JSON events and registered tool calls only.
It never executes model-provided code, selectors, SQL, paths, or network destinations.
"""
from .config import AgentConfig
from .service import AgentService, AgentServiceError
from .storage import ensure_agent_schema
from .tools import tool_catalog

__all__ = ["AgentConfig", "AgentService", "AgentServiceError", "ensure_agent_schema", "tool_catalog"]
