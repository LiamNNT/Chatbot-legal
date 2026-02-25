"""
Direct response templates for social greetings.

No LLM call needed — returns hardcoded Vietnamese responses
for greetings, identity questions, thanks, and goodbyes.
"""

from typing import Optional


def get_direct_response(query: str, intent: str) -> Optional[str]:
    """
    Return a canned response for social greetings, or *None* if the
    query should be handled by the normal LLM pipeline.
    """
    q = query.lower().strip()

    # Identity questions
    identity_patterns = [
        "bạn là ai", "bạn là gì", "mày là ai",
        "who are you", "bạn tên gì", "tên bạn là gì",
    ]
    for p in identity_patterns:
        if p in q:
            return (
                "Chào bạn! 👋\n\n"
                "Mình là **Trợ lý Pháp luật AI** ⚖️ - chatbot chuyên hỗ trợ tra cứu và giải đáp về văn bản pháp luật Việt Nam.\n\n"
                "Mình có thể giúp bạn tìm hiểu về:\n\n"
                "- 📜 Luật, Nghị định, Thông tư, Quyết định\n"
                "- ⚖️ Quy định pháp luật, điều khoản cụ thể\n"
                "- 🔍 Tra cứu chế tài, hình phạt, mức xử phạt\n"
                "- 💡 Giải đáp thắc mắc về quyền và nghĩa vụ pháp lý\n\n"
                "Cần hỗ trợ gì thì cứ hỏi mình nhé! 😊"
            )

    # Greetings
    greeting_patterns = ["xin chào", "hello", "hi", "chào bạn", "chào"]
    for p in greeting_patterns:
        if q == p or q.startswith(p + " ") or q.startswith(p + ","):
            return (
                "Chào bạn! 👋\n\n"
                "Mình là **Trợ lý Pháp luật AI** ⚖️.\n\n"
                "Mình có thể giúp bạn tra cứu luật, nghị định, thông tư, "
                "quy định pháp luật và giải đáp các thắc mắc pháp lý.\n\n"
                "Bạn cần hỏi gì nào? 😊"
            )

    # Thank you
    thanks_patterns = ["cảm ơn", "thanks", "thank you", "cám ơn"]
    for p in thanks_patterns:
        if p in q:
            return (
                "Không có gì đâu bạn! 😊\n\n"
                "Nếu cần tra cứu thêm quy định pháp luật, cứ nhắn mình nhé! 💪"
            )

    # Goodbye
    bye_patterns = ["tạm biệt", "bye", "goodbye", "chào tạm biệt"]
    for p in bye_patterns:
        if p in q:
            return (
                "Tạm biệt bạn! 👋\n\n"
                "Chúc bạn mọi điều tốt đẹp! "
                "Khi nào cần hỗ trợ tra cứu pháp luật thì quay lại nhé! ⚖️😊"
            )

    # Simple acknowledgments
    simple_patterns = ["ok", "oke", "được", "vâng", "dạ", "ừ"]
    for p in simple_patterns:
        if q == p:
            return "Dạ, bạn cần mình giúp gì thêm không? 😊"

    return None
