from fastapi import HTTPException, status, Request

from app.core.context import RequestContext
from app.db.user_repo import UserRepo


class AuthService:
    """Service for handling authentication and creating request contexts"""
    
    def __init__(self, user_repo: UserRepo):
        self.user_repo = user_repo
    
    def authenticate(
        self,
        request: Request,
        require_openrouter_key: bool = True,
    ) -> RequestContext:
        """
        Authenticate a request and return RequestContext.
        
        Args:
            request: FastAPI Request object
            require_openrouter_key: Whether to require X-OpenRouter-API-Key header
            
        Returns:
            RequestContext with user_id and openrouter_api_key
            
        Raises:
            HTTPException: 401 if authentication fails
        """
        # Get API key
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key",
            )
        
        # Validate API key and get user
        user = self.user_repo.get_user_by_api_key(api_key)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        
        # Get OpenRouter API key if required
        openrouter_api_key = None
        if require_openrouter_key:
            openrouter_api_key = request.headers.get("X-OpenRouter-API-Key")
            if not openrouter_api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing OpenRouter API key",
                )
        
        return RequestContext(
            user_id=user.id,
            openrouter_api_key=openrouter_api_key or "",
        )

