from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    
    status_code = 400

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class DomainError(AppError):
    """Base for client-safe application errors."""


class InvalidCredentialsError(DomainError):
    status_code = 401


class DatabaseNotFoundError(DomainError):
    status_code = 404


class UnsafeSqlError(DomainError):
    status_code = 422

class DatabaseConnectionError(DomainError):
    status_code = 400
    
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)

