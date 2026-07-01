from utils.logger import logger

class AppBaseError(Exception):
    def __init__(self, status_code:int,detail:str):
        self.status_code = status_code
        self.detail = detail

class AuthFailedError(AppBaseError):
    def __init__(self, status_code=401, detail="Login failed!"):
        super().__init__(status_code, detail)

class ForbiddenError(AppBaseError):
    def __init__(self, status_code=403, detail="You dont have permission to do this!"):
        super().__init__(status_code, detail)

class NotFoundError(AppBaseError):
    def __init__(self, status_code=404, detail="Not found!"):
        super().__init__(status_code, detail)

class UserAlreadyExistsError(AppBaseError):
    def __init__(self, status_code=409, detail="User with this email already exists!"):
        super().__init__(status_code, detail)

class DataValidationError(AppBaseError):
    def __init__(self, status_code=422, detail="Invalid data fromat!"):
        super().__init__(status_code, detail)

class GoneError(AppBaseError):
    def __init__(self, status_code=410, detail="Resource is not available!"):
        super().__init__(status_code, detail)

class TokenError(AppBaseError):
    def __init__(
                self, 
                status_code=401,
                detail="Could not validate credentials",
                headers = {"WWW-Authenticate": "Bearer"}
                ):
        super().__init__(status_code, detail)
        self.headers = headers