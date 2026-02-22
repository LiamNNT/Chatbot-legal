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
                "Mình là **Đậu Đậu** 🫘 - chatbot AI của Trường Đại học Công nghệ Thông tin (UIT), ĐHQG-HCM.\n\n"
                "Mình được tạo ra để hỗ trợ sinh viên và phụ huynh giải đáp thắc mắc về:\n\n"
                "- 📚 Quy chế đào tạo, quy định học vụ\n"
                "- 📝 Đăng ký học phần, chương trình đào tạo\n"
                "- 🎓 Thông tin tuyển sinh, học phí\n"
                "- 💡 Các câu hỏi về UIT\n\n"
                "Cần hỗ trợ gì thì cứ hỏi mình nhé! 😊"
            )

    # Greetings
    greeting_patterns = ["xin chào", "hello", "hi", "chào bạn", "chào"]
    for p in greeting_patterns:
        if q == p or q.startswith(p + " ") or q.startswith(p + ","):
            return (
                "Chào bạn! 👋\n\n"
                "Mình là **Đậu Đậu** 🫘 - chatbot của UIT.\n\n"
                "Mình có thể giúp bạn tìm hiểu về quy chế đào tạo, "
                "đăng ký học phần, thông tin tuyển sinh và nhiều thứ khác về UIT.\n\n"
                "Bạn cần hỏi gì nào? 😊"
            )

    # Thank you
    thanks_patterns = ["cảm ơn", "thanks", "thank you", "cám ơn"]
    for p in thanks_patterns:
        if p in q:
            return (
                "Không có gì đâu bạn! 😊\n\n"
                "Nếu cần hỏi thêm điều gì về UIT, cứ nhắn mình nhé! 💪"
            )

    # Goodbye
    bye_patterns = ["tạm biệt", "bye", "goodbye", "chào tạm biệt"]
    for p in bye_patterns:
        if p in q:
            return (
                "Tạm biệt bạn! 👋\n\n"
                "Chúc bạn học tập tốt! "
                "Khi nào cần hỗ trợ thì quay lại hỏi Đậu Đậu nhé! 🫘😊"
            )

    # Simple acknowledgments
    simple_patterns = ["ok", "oke", "được", "vâng", "dạ", "ừ"]
    for p in simple_patterns:
        if q == p:
            return "Dạ, bạn cần mình giúp gì thêm không? 😊"

    return None
