import asyncio
import logging
from typing import Any
from omagent.tools.base import Tool

logger = logging.getLogger(__name__)


class JupyterExecuteTool(Tool):
    """Execute Python code in a persistent Jupyter kernel."""

    def __init__(self):
        self._kernel_manager = None
        self._kernel_client = None

    @property
    def name(self) -> str:
        return "jupyter_execute"

    @property
    def description(self) -> str:
        return (
            "Execute Python code in a persistent Jupyter kernel. "
            "The kernel maintains state across calls (variables, imports persist). "
            "Returns stdout, stderr, and any display outputs (images, HTML, etc). "
            "Use for data analysis, computation, and visualization."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute in the Jupyter kernel.",
                }
            },
            "required": ["code"],
        }

    async def _ensure_kernel(self) -> None:
        """Start kernel if not running."""
        if self._kernel_manager is not None:
            return

        from jupyter_client import AsyncKernelManager

        self._kernel_manager = AsyncKernelManager(kernel_name="python3")
        await self._kernel_manager.start_kernel()
        self._kernel_client = self._kernel_manager.client()
        self._kernel_client.start_channels()
        # Wait for kernel to be ready
        try:
            await asyncio.wait_for(
                self._kernel_client.wait_for_ready(), timeout=30
            )
        except asyncio.TimeoutError:
            logger.error("Kernel failed to start within 30s")
            raise

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        code = input.get("code", "")
        if not code.strip():
            return {"error": "No code provided"}

        try:
            await self._ensure_kernel()
        except Exception as e:
            return {"error": f"Failed to start kernel: {e}"}

        try:
            msg_id = self._kernel_client.execute(code)
        except Exception as e:
            return {"error": f"Failed to submit code: {e}"}

        stdout_parts = []
        stderr_parts = []
        outputs = []
        error_info = None

        # Collect output messages
        timeout = 120  # seconds
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(
                        self._kernel_client.get_iopub_msg(), timeout=timeout
                    )
                except asyncio.TimeoutError:
                    return {"error": f"Execution timed out after {timeout}s", "stdout": "".join(stdout_parts)}

                msg_type = msg["msg_type"]
                content = msg["content"]

                if msg_type == "stream":
                    if content["name"] == "stdout":
                        stdout_parts.append(content["text"])
                    elif content["name"] == "stderr":
                        stderr_parts.append(content["text"])

                elif msg_type == "execute_result":
                    data = content.get("data", {})
                    outputs.append({
                        "type": "execute_result",
                        "text": data.get("text/plain", ""),
                        "html": data.get("text/html"),
                    })

                elif msg_type == "display_data":
                    data = content.get("data", {})
                    output = {"type": "display_data"}
                    if "text/plain" in data:
                        output["text"] = data["text/plain"]
                    if "image/png" in data:
                        output["image_base64"] = data["image/png"]
                    if "text/html" in data:
                        output["html"] = data["text/html"]
                    outputs.append(output)

                elif msg_type == "error":
                    error_info = {
                        "ename": content.get("ename", ""),
                        "evalue": content.get("evalue", ""),
                        "traceback": content.get("traceback", []),
                    }

                elif msg_type == "status" and content.get("execution_state") == "idle":
                    break

        except Exception as e:
            return {"error": f"Error collecting output: {e}"}

        result: dict[str, Any] = {
            "stdout": "".join(stdout_parts),
        }
        if stderr_parts:
            result["stderr"] = "".join(stderr_parts)
        if outputs:
            result["outputs"] = outputs
        if error_info:
            result["error"] = error_info
        if not error_info:
            result["output"] = result["stdout"] or (
                outputs[0].get("text", "") if outputs else "Code executed successfully"
            )

        return result

    async def shutdown(self) -> None:
        """Shut down the kernel."""
        if self._kernel_client:
            self._kernel_client.stop_channels()
        if self._kernel_manager:
            await self._kernel_manager.shutdown_kernel(now=True)
            self._kernel_manager = None
            self._kernel_client = None
