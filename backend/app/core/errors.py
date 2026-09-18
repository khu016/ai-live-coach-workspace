class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def not_found(message: str = "资源不存在") -> AppError:
    return AppError("NOT_FOUND", message, 404)


def bad_request(message: str) -> AppError:
    return AppError("BAD_REQUEST", message, 400)


def conflict(message: str) -> AppError:
    return AppError("CONFLICT", message, 409)
