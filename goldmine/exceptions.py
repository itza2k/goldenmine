class AppError(Exception):
    """User-facing application error."""


class PermissionDenied(AppError):
    pass


class ValidationError(AppError):
    pass


class AuthError(AppError):
    pass


class NotFoundError(AppError):
    pass
