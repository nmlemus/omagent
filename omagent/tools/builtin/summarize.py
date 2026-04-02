from typing import Any
from omagent.tools.base import Tool


class SummarizeTool(Tool):
    """Summarize the current conversation context. Available in all packs."""

    def __init__(self, summarizer=None, session=None):
        self._summarizer = summarizer
        self._session = session

    @property
    def name(self) -> str:
        return "summarize_context"

    @property
    def description(self) -> str:
        return (
            "Summarize the current conversation history to free up context space. "
            "Use when the conversation is getting long or you need to consolidate findings. "
            "Returns the generated summary."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "focus": {
                    "type": "string",
                    "description": "Optional focus area for the summary (e.g., 'data analysis findings').",
                },
            },
            "required": [],
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        if not self._summarizer or not self._session:
            return {"error": "Summarizer not configured"}

        try:
            result = await self._summarizer.summarize(self._session.messages)
            if result["summary"]:
                self._session.messages = result["messages"]
                self._session.summary = result["summary"]
                return {
                    "output": f"Summarized {result['messages_summarized']} messages. {result['messages_kept']} recent messages kept.",
                    "summary": result["summary"],
                }
            return {"output": "No summarization needed — conversation is within limits."}
        except Exception as e:
            return {"error": f"Summarization failed: {e}"}
