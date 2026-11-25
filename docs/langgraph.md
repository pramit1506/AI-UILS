# Conversation workflow

Each chat turn is handled by LangGraph. The turn starts by processing the request and determining intent. Capture then extracts a draft from the document, while explicit saved-record searches use the authenticated search tool. A reviewed save sends the draft directly to the save tool.

For a conversational editing turn, the graph may extract field changes, ask a clarification question, or execute a tool. The response includes the updated draft, changed fields, and any clarification or tool result. Structured model output is validated before use. If every eligible model route fails, the capture flow can return a basic draft and identify it as a local fallback.

Signed-in conversation checkpoints are scoped to the account. Guests have a separate in-memory graph and need an account to persist the record.

See the [conversation API](conversation_api.md) for request and response details.
