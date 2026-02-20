from typing import Dict, Any
from ..shared.exceptions import (
    OrchestrationDomainException,
    AgentProcessingFailedException,
    RAGRetrievalFailedException,
    ContextManagementFailedException
)


class ExceptionMessageHandler:

    @staticmethod
    def get_user_message(exception: OrchestrationDomainException) -> str:
        if isinstance(exception, AgentProcessingFailedException):
            return "Xin lỗi, đã có lỗi xảy ra khi xử lý yêu cầu của bạn. Vui lòng thử lại sau."
        elif isinstance(exception, RAGRetrievalFailedException):
            return "Không thể tìm kiếm thông tin từ cơ sở dữ liệu. Vui lòng thử lại hoặc liên hệ hỗ trợ."
        elif isinstance(exception, ContextManagementFailedException):
            return "Đã có lỗi với phiên trò chuyện. Vui lòng bắt đầu cuộc trò chuyện mới."
        else:
            return "Đã có lỗi hệ thống. Vui lòng thử lại sau hoặc liên hệ hỗ trợ kỹ thuật."
    
    @staticmethod
    def get_error_details(exception: OrchestrationDomainException) -> Dict[str, Any]:
        return {
            "error_code": exception.error_code,
            "details": exception.details,
            "cause": str(exception.cause) if exception.cause else None,
            "exception_type": type(exception).__name__
        }
    
    @staticmethod 
    def get_http_status_code(exception: OrchestrationDomainException) -> int:
        if isinstance(exception, AgentProcessingFailedException):
            return 503
        elif isinstance(exception, RAGRetrievalFailedException):
            return 503  
        elif isinstance(exception, ContextManagementFailedException):
            return 500  
        else:
            return 500  
    
    @staticmethod
    def create_fallback_response(
        exception: OrchestrationDomainException,
        session_id: str,
        user_query: str
    ) -> Dict[str, Any]:
        user_message = ExceptionMessageHandler.get_user_message(exception)
        
        return {
            "response": user_message,
            "session_id": session_id,
            "is_error_response": True,
            "error_handled": True,
            "original_query": user_query,
            "suggested_actions": [
                "Thử lại yêu cầu sau vài phút",
                "Đơn giản hoá câu hỏi của bạn", 
                "Liên hệ hỗ trợ kỹ thuật nếu lỗi tiếp tục xảy ra"
            ]
        }