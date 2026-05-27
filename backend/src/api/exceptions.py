"""异常处理"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.models.schemas import ErrorResponse

class APIException(Exception):
    """API异常基类"""
    def __init__(self, code: int, message: str, detail: str = None):
        self.code = code
        self.message = message
        self.detail = detail

class BadRequestException(APIException):
    def __init__(self, message: str = "Bad Request", detail: str = None):
        super().__init__(400, message, detail)

class UnauthorizedException(APIException):
    def __init__(self, message: str = "Unauthorized", detail: str = None):
        super().__init__(401, message, detail)

class ForbiddenException(APIException):
    def __init__(self, message: str = "Forbidden", detail: str = None):
        super().__init__(403, message, detail)

class NotFoundException(APIException):
    def __init__(self, message: str = "Not Found", detail: str = None):
        super().__init__(404, message, detail)

class ServerException(APIException):
    def __init__(self, message: str = "Internal Server Error", detail: str = None):
        super().__init__(500, message, detail)

def setup_exception_handlers(app: FastAPI):
    """设置异常处理器"""
    
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        return JSONResponse(
            status_code=exc.code,
            content=ErrorResponse(
                code=exc.code,
                message=exc.message,
                detail=exc.detail
            ).model_dump()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                code=500,
                message="Internal Server Error",
                detail=str(exc)
            ).model_dump()
        )
