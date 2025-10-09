class SetupError(Exception):
    def __init__(self, message="A custom error occurred."):
        self.message = message
        super().__init__(self.message)
