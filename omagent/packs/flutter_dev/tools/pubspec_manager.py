from pathlib import Path
from typing import Any
import yaml
from omagent.tools.base import Tool


class PubspecManagerTool(Tool):
    """Read and modify pubspec.yaml for Flutter projects."""

    @property
    def name(self) -> str:
        return "pubspec_manager"

    @property
    def description(self) -> str:
        return (
            "Read, add, remove, or update dependencies in a Flutter project's pubspec.yaml. "
            "Also shows current project configuration (name, version, SDK constraints)."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "Path to the Flutter project root containing pubspec.yaml.",
                },
                "action": {
                    "type": "string",
                    "enum": ["read", "add_dependency", "remove_dependency", "set_version"],
                    "description": "Action to perform (default: read).",
                },
                "package_name": {
                    "type": "string",
                    "description": "Package name (for add/remove actions).",
                },
                "version": {
                    "type": "string",
                    "description": "Version constraint (for add action, e.g., '^2.0.0').",
                },
                "dev": {
                    "type": "boolean",
                    "description": "If true, target dev_dependencies instead (default: false).",
                },
            },
            "required": ["project_path"],
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        project_path = Path(input["project_path"])
        pubspec_path = project_path / "pubspec.yaml"
        action = input.get("action", "read")

        if not pubspec_path.exists():
            return {"error": f"pubspec.yaml not found at {pubspec_path}"}

        try:
            with open(pubspec_path) as f:
                data = yaml.safe_load(f)

            if action == "read":
                return {
                    "output": "pubspec.yaml loaded",
                    "name": data.get("name"),
                    "version": data.get("version"),
                    "description": data.get("description"),
                    "sdk_constraint": data.get("environment", {}).get("sdk"),
                    "flutter_constraint": data.get("environment", {}).get("flutter"),
                    "dependencies": data.get("dependencies", {}),
                    "dev_dependencies": data.get("dev_dependencies", {}),
                }

            elif action == "add_dependency":
                pkg = input.get("package_name")
                ver = input.get("version", "any")
                is_dev = input.get("dev", False)

                if not pkg:
                    return {"error": "package_name required for add_dependency"}

                dep_key = "dev_dependencies" if is_dev else "dependencies"
                if dep_key not in data:
                    data[dep_key] = {}
                data[dep_key][pkg] = ver

                with open(pubspec_path, "w") as f:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False)

                return {"output": f"Added {pkg}: {ver} to {dep_key}"}

            elif action == "remove_dependency":
                pkg = input.get("package_name")
                if not pkg:
                    return {"error": "package_name required for remove_dependency"}

                removed_from = []
                for key in ["dependencies", "dev_dependencies"]:
                    if key in data and pkg in data[key]:
                        del data[key][pkg]
                        removed_from.append(key)

                if not removed_from:
                    return {"error": f"Package '{pkg}' not found in dependencies"}

                with open(pubspec_path, "w") as f:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False)

                return {"output": f"Removed {pkg} from {', '.join(removed_from)}"}

            elif action == "set_version":
                ver = input.get("version")
                if not ver:
                    return {"error": "version required for set_version"}
                data["version"] = ver

                with open(pubspec_path, "w") as f:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False)

                return {"output": f"Set project version to {ver}"}

            else:
                return {"error": f"Unknown action: {action}"}

        except Exception as e:
            return {"error": f"pubspec operation failed: {e}"}
