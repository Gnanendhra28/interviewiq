class IdentityApplicationService:
    def __init__(self):
        pass

    async def authenticate_user(self, email: str):
        return {"email": email, "authenticated": True}
