from collections import OrderedDict
import time
from typing import Optional, Dict, Any, List
from app.schemas.memory import ConversationSummary, ConversationMetadata, Message

# Maximum number of conversations kept in the in-memory store. When exceeded,
# the least-recently-used conversations are evicted (see LRU note below).
MAX_CONVERSATIONS = 200

# In-memory store for now to avoid database migrations during phase 2C.
# Can be replaced with SQLAlchemy models later.
#
# Bounded LRU cache: each entry is {"_access": <stamp>, ...data}. On every
# access/save the key is moved to the end of the OrderedDict; when the store
# grows beyond MAX_CONVERSATIONS, the oldest (least recently used) entries at
# the front are evicted so memory usage stays bounded.
_conversations_db: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
_access_counter = 0


def _get_entry(conversation_id: str, field: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch a conversation entry, refreshing its LRU position and stamp."""
    global _access_counter
    conv = _conversations_db.get(conversation_id)
    if conv is None:
        return None
    # Move to end to mark as most recently used.
    _conversations_db.move_to_end(conversation_id)
    _access_counter += 1
    conv["_access"] = _access_counter
    if field is not None and field not in conv:
        return None
    return conv


def _put_entry(conversation_id: str) -> Dict[str, Any]:
    """Create or refresh a conversation entry and enforce the LRU bound."""
    global _access_counter
    conv = _conversations_db.get(conversation_id)
    if conv is None:
        conv = {"messages": [], "metadata": {}}
        _conversations_db[conversation_id] = conv
    else:
        _conversations_db.move_to_end(conversation_id)
    _access_counter += 1
    conv["_access"] = _access_counter
    # Evict oldest (least recently used) conversations beyond the cap.
    while len(_conversations_db) > MAX_CONVERSATIONS:
        _conversations_db.popitem(last=False)
    return conv

class ConversationRepository:
    """
    Repository for persisting conversation history, summaries, and metadata.
    Currently uses an in-memory store to avoid database migrations, but provides 
    an asynchronous interface suitable for future database integration.
    """
    
    async def get_summary(self, conversation_id: str) -> Optional[ConversationSummary]:
        conv = _get_entry(conversation_id, "summary")
        if conv:
            return ConversationSummary.model_validate(conv["summary"])
        return None

    async def save_summary(self, conversation_id: str, summary: ConversationSummary) -> None:
        _put_entry(conversation_id)["summary"] = summary.model_dump()

    async def get_metadata(self, conversation_id: str) -> Optional[ConversationMetadata]:
        conv = _get_entry(conversation_id, "metadata")
        if conv:
            # Reconstruct from dict
            return ConversationMetadata.model_validate(conv["metadata"])
        return None

    async def save_metadata(self, conversation_id: str, metadata: ConversationMetadata) -> None:
        _put_entry(conversation_id)["metadata"] = metadata.model_dump()

    async def get_messages(self, conversation_id: str, limit: Optional[int] = None) -> List[Message]:
        conv = _get_entry(conversation_id)
        if not conv or "messages" not in conv:
            return []
        messages = [Message.model_validate(m) for m in conv["messages"]]
        if limit:
            return messages[-limit:]
        return messages

    async def append_message(self, conversation_id: str, message: Message) -> None:
        _put_entry(conversation_id)["messages"].append(message.model_dump())

    async def get_resolved_entities(self, conversation_id: str) -> Dict[str, Any]:
        conv = _get_entry(conversation_id)
        if conv and "resolved_entities" in conv:
            return conv["resolved_entities"]
        return {}

    async def save_resolved_entities(self, conversation_id: str, entities: Dict[str, Any]) -> None:
        _put_entry(conversation_id)["resolved_entities"] = entities

conversation_repository = ConversationRepository()
