class DomainException(Exception):
    def __init__(self, message: str):
        self.message = message
        print(self.message)
        super().__init__(self.message)


class NotFoundException(DomainException):
    def __init__(self, message: str):
        print(message)
        super().__init__(message)
