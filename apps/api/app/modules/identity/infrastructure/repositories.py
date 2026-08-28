class UserRepository:
    def __init__(self, session):
        self.session = session

    async def get_by_email(self, email: str):
        return None
