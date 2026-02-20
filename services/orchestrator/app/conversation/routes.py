"""
Conversation management route handlers.

Endpoints:
    GET    /conversations              – List active conversations
    DELETE /conversations/{session_id} – Delete a conversation
    POST   /conversations/cleanup      – Cleanup old conversations
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
import logging

from ..shared.schemas import (
    ConversationsResponse,
    ConversationInfo,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/conversations",
    response_model=ConversationsResponse,
    summary="List active conversations",
    description="Get list of active conversation sessions",
)
async def list_conversations() -> ConversationsResponse:
    """List all active conversation sessions."""
    try:
        from ..shared.container.container import get_container

        container = get_container()
        conversation_manager = container.get_conversation_manager()

        if hasattr(conversation_manager, "get_active_sessions"):
            active_sessions = conversation_manager.get_active_sessions()
            conversations = []
            for session_id in active_sessions:
                context = await conversation_manager.get_context(session_id)
                if context:
                    conversations.append(
                        ConversationInfo(
                            session_id=session_id,
                            message_count=len(context.messages),
                            created_at=context.metadata.get("created_at") if context.metadata else None,
                            updated_at=context.metadata.get("updated_at") if context.metadata else None,
                        )
                    )
            return ConversationsResponse(conversations=conversations, total_count=len(conversations))

        return ConversationsResponse(conversations=[], total_count=0)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving conversations: {str(e)}")


@router.delete(
    "/conversations/{session_id}",
    summary="Delete conversation",
    description="Delete a specific conversation session",
)
async def delete_conversation(session_id: str) -> dict:
    """Delete a specific conversation session."""
    try:
        from ..shared.container.container import get_container

        container = get_container()
        conversation_manager = container.get_conversation_manager()
        success = await conversation_manager.delete_context(session_id)

        if success:
            return {"message": f"Conversation {session_id} deleted successfully"}
        raise HTTPException(status_code=404, detail=f"Conversation {session_id} not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")


@router.post(
    "/conversations/cleanup",
    summary="Cleanup old conversations",
    description="Remove old conversation sessions",
)
async def cleanup_conversations(
    max_age_hours: int = 24,
    background_tasks: BackgroundTasks = None,
) -> dict:
    """Cleanup old conversation sessions."""
    try:
        from ..shared.container.container import get_container

        container = get_container()
        conversation_manager = container.get_conversation_manager()

        if hasattr(conversation_manager, "cleanup_old_contexts"):
            if background_tasks:

                async def cleanup_task():
                    return await conversation_manager.cleanup_old_contexts(max_age_hours)

                background_tasks.add_task(cleanup_task)
                return {"message": "Cleanup started in background"}

            cleaned_count = await conversation_manager.cleanup_old_contexts(max_age_hours)
            return {"message": f"Cleaned up {cleaned_count} old conversations"}

        return {"message": "Cleanup not supported by current conversation manager"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during cleanup: {str(e)}")
