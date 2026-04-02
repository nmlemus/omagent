# omagent/core/orchestrator.py
import asyncio
import uuid
import logging
from typing import Any

from omagent.core.loop import AgentLoop
from omagent.core.registry import ToolRegistry
from omagent.core.session import Session, SessionStore
from omagent.core.permissions import PermissionPolicy
from omagent.core.hooks import HookRunner
from omagent.core.events import TextDeltaEvent, DoneEvent
from omagent.providers.litellm_provider import LiteLLMProvider

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Manages sub-agent spawning and coordination.

    A supervisor agent can delegate tasks to sub-agents,
    each using a different domain pack with a fresh session.
    """

    def __init__(self, store: SessionStore | None = None, journal=None):
        self.store = store or SessionStore()
        self.journal = journal
        self._active_agents: dict[str, AgentLoop] = {}

    async def spawn_agent(
        self,
        pack_name: str,
        task: str,
        context_summary: str = "",
    ) -> dict[str, Any]:
        """
        Spawn a sub-agent with a specific pack and run a single task.

        Args:
            pack_name: Domain pack to use (e.g., "data_science", "flutter_dev")
            task: The task/prompt for the sub-agent
            context_summary: Brief context from the supervisor (fresh session, not shared)

        Returns:
            {"agent_id": str, "result": str, "is_error": bool}
        """
        agent_id = uuid.uuid4().hex[:12]

        if self.journal:
            self.journal.log_sub_agent_start(agent_id, pack_name, task)

        try:
            # Build sub-agent with the requested pack
            registry = ToolRegistry()
            policy = PermissionPolicy()

            # Try to load domain pack
            system_prompt = f"You are a sub-agent. {context_summary}"
            try:
                from omagent.packs.loader import DomainPackLoader
                loader = DomainPackLoader()
                pack = loader.load(pack_name)
                system_prompt = pack.system_prompt
                if context_summary:
                    system_prompt += f"\n\nContext from supervisor: {context_summary}"
                registry.register_many(pack.tools)
                policy.load_pack_permissions(pack.permissions)
            except FileNotFoundError:
                # Fallback: load builtin tools
                from omagent.tools.builtin import ReadFileTool, WriteFileTool, ListDirTool, BashTool
                registry.register_many([ReadFileTool(), WriteFileTool(), ListDirTool(), BashTool()])

            session = Session(id=f"sub-{agent_id}", pack_name=pack_name)
            provider = LiteLLMProvider()

            loop = AgentLoop(
                session=session,
                registry=registry,
                provider=provider,
                policy=PermissionPolicy(
                    # Sub-agents auto-approve everything (supervised by parent)
                    overrides={name: "auto" for name in registry.names()}
                ),
                hooks=HookRunner(),
                system_prompt=system_prompt,
                store=self.store,
            )

            self._active_agents[agent_id] = loop

            # Run the sub-agent and collect results
            result_text = ""
            async for event in loop.run(task):
                if isinstance(event, TextDeltaEvent):
                    result_text += event.content
                elif isinstance(event, DoneEvent):
                    break

            del self._active_agents[agent_id]

            if self.journal:
                self.journal.log_sub_agent_done(agent_id, pack_name, is_error=False)

            return {
                "agent_id": agent_id,
                "pack_name": pack_name,
                "result": result_text,
                "is_error": False,
            }

        except Exception as e:
            logger.error("Sub-agent %s failed: %s", agent_id, e)
            self._active_agents.pop(agent_id, None)
            if self.journal:
                self.journal.log_sub_agent_done(agent_id, pack_name, is_error=True)
            return {
                "agent_id": agent_id,
                "pack_name": pack_name,
                "result": str(e),
                "is_error": True,
            }

    async def run_parallel(
        self,
        tasks: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        """
        Run multiple sub-agents in parallel.

        Args:
            tasks: List of {"pack": str, "task": str, "context": str}

        Returns:
            List of results from each sub-agent.
        """
        coros = [
            self.spawn_agent(
                pack_name=t["pack"],
                task=t["task"],
                context_summary=t.get("context", ""),
            )
            for t in tasks
        ]
        return await asyncio.gather(*coros)

    @property
    def active_count(self) -> int:
        return len(self._active_agents)
