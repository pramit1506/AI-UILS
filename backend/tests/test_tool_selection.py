"""Tool-selection precedence tests.

Covers the fix for the audit finding that the tool-selection LLM's choice
(`ToolSelectionOutput.tool_name`) was ignored downstream: if that second-stage
selection names a DIFFERENT, registry-validated tool than the pending
selection, the newer selection must win for execution and the stale
`pending_tool` must be cleared.
"""
import pytest
from unittest.mock import patch

from app.graph.nodes import tool_selection_node
from app.graph.router import route_after_tool_selection
from app.graph.state import ToolSelectionOutput
from app.schemas.decision import DecisionOutput
from app.schemas.draft import DynamicLogDraft
from app.shared.enums import AgentAction, ToolReadiness, AgentState, ToolName
from app.tools.registry import tool_registry
from app.tools.save_log import SaveLogTool
from app.tools.search_logs import SearchLogsTool


class _StubLLM:
    """LLM provider stub whose structured output is fixed by the test."""

    def __init__(self, output):
        self._output = output

    async def generate_structured(self, messages=None, schema=None, **kwargs):
        return self._output


class _StubContextBuilder:
    async def build(self, state, **kwargs):
        return ""


@pytest.fixture(autouse=True)
def registered_tools():
    # Ensure the registry has the two tools the tests exercise.
    for tool in (SaveLogTool(), SearchLogsTool()):
        if not tool_registry.get_tool(tool.name):
            tool_registry.register(tool)


def _base_state(decision: DecisionOutput) -> dict:
    return {
        "request_id": "test-req",
        "conversation_id": "test-conv",
        "user_message": "actually, search my saved logs instead",
        "detected_intent": "save_log",
        "selected_tool": ToolName.SAVE_LOG,
        "pending_tool": ToolName.SAVE_LOG,
        "log_draft": DynamicLogDraft(schema_name="Invoice", domain="Finance", fields={"total_amount": "$10.00"}),
        "tool_arguments": None,
        "decision_output": decision,
        "metadata": {},
    }


@pytest.mark.asyncio
async def test_tool_selection_llm_choice_overrides_pending_tool():
    """Pending tool is save_log, but the tool-selection LLM validates and picks
    search_logs → the final selection must be search_logs and the stale
    pending_tool must be cleared so tool_execution_node uses the new tool."""
    stub_output = ToolSelectionOutput(
        tool_name=ToolName.SEARCH_LOGS,
        tool_arguments={"query": "invoices", "scope": "own"},
    )
    decision = DecisionOutput(
        action=AgentAction.CONTINUE,
        tool_readiness=ToolReadiness.NOT_APPLICABLE,
        decision_confidence=1.0,
        next_state=AgentState.IDLE,
    )

    with patch("app.graph.nodes.get_llm_provider", return_value=_StubLLM(stub_output)), \
         patch("app.graph.nodes.context_builder", _StubContextBuilder()):
        result = await tool_selection_node(_base_state(decision))

    assert result["selected_tool"] == ToolName.SEARCH_LOGS
    assert result["pending_tool"] is None
    # Downstream routing executes the FINAL selection.
    final_state = dict(_base_state(decision), **result)
    assert route_after_tool_selection(final_state) == "tool_execution_node"


@pytest.mark.asyncio
async def test_tool_selection_llm_choice_matching_pending_is_kept():
    """When the tool-selection LLM agrees with the pending tool, the pending
    selection is simply confirmed (no override, pending_left alone)."""
    stub_output = ToolSelectionOutput(
        tool_name=ToolName.SAVE_LOG,
        tool_arguments={"fields": {"total_amount": "$10.00"}},
    )
    decision = DecisionOutput(
        action=AgentAction.CONTINUE,
        tool_readiness=ToolReadiness.NOT_APPLICABLE,
        decision_confidence=1.0,
        next_state=AgentState.IDLE,
    )

    with patch("app.graph.nodes.get_llm_provider", return_value=_StubLLM(stub_output)), \
         patch("app.graph.nodes.context_builder", _StubContextBuilder()):
        result = await tool_selection_node(_base_state(decision))

    assert result["selected_tool"] == ToolName.SAVE_LOG
    assert "pending_tool" not in result


@pytest.mark.asyncio
async def test_tool_selection_clears_unresolvable_selection():
    """Registry validation: a stale/invalid selection is cleared so the router
    sends the turn to response_node instead of tool execution."""
    decision = DecisionOutput(
        action=AgentAction.EXECUTE_TOOL,
        tool_readiness=ToolReadiness.READY,
        decision_confidence=1.0,
        next_state=AgentState.READY_TO_EXECUTE,
    )
    state = _base_state(decision)
    # Simulate a stale/invalid pending selection (pending_tool lives in the
    # unvalidated graph TypedDict, so an invalid name can reach the node).
    state["selected_tool"] = "bogus_tool"
    state["pending_tool"] = "bogus_tool"

    result = await tool_selection_node(state)

    assert result["selected_tool"] is None
    assert result["pending_tool"] is None
    final_state = dict(state, **result)
    assert route_after_tool_selection(final_state) == "response_node"


@pytest.mark.asyncio
async def test_tool_selection_execute_path_uses_final_selection():
    """Deterministic EXECUTE_TOOL path: the executed tool is the registry-
    validated final selection, which tool_execution_node reads from state."""
    decision = DecisionOutput(
        action=AgentAction.EXECUTE_TOOL,
        tool_readiness=ToolReadiness.READY,
        selected_tool=ToolName.SAVE_LOG,
        decision_confidence=1.0,
        next_state=AgentState.READY_TO_EXECUTE,
    )

    with patch("app.graph.nodes.context_builder", _StubContextBuilder()):
        result = await tool_selection_node(_base_state(decision))

    assert result["selected_tool"] == ToolName.SAVE_LOG
    assert result["tool_arguments"].get("schema_name") == "Invoice"
    assert result["tool_arguments"].get("fields") == {"total_amount": "$10.00"}
