from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette import status


class AppError(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail: str = "Internal Server Error"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.default_detail
        super().__init__(detail)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Not Found"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Forbidden"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Unauthorized"


class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Bad Request"


class TooManyRequestsError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Too Many Requests"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def register_error_handlers(app: FastAPI):
    app.add_exception_handler(AppError, app_error_handler)
