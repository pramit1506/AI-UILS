from app.tools.base_tool import BaseTool
from app.tools.context import ToolExecutionContext
from app.tools.registry import tool_registry

from app.tools.save_log import SaveLogTool
from app.tools.edit_log import EditLogTool
from app.tools.summarize_log import SummarizeLogTool
from app.tools.search_logs import SearchLogsTool
from app.tools.completeness_checker import CompletenessCheckerTool

# Register all universal logging tools
tool_registry.register(SaveLogTool())
tool_registry.register(EditLogTool())
tool_registry.register(SummarizeLogTool())
tool_registry.register(SearchLogsTool())
tool_registry.register(CompletenessCheckerTool())

__all__ = ["BaseTool", "ToolExecutionContext", "tool_registry"]
