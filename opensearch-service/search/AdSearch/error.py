class AdSearchError(Exception):
    """
    Custom exception class for AdSearch
    """

    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

    def __str__(self):
        error_message = f"AdSearchError: {self.args[0]}"
        if self.status_code is not None:
            error_message += f" Status Code: {self.status_code}"
        if self.response is not None:
            error_message += f" Response: {self.response}"
        return error_message
