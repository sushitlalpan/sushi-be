import os
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse
from backend.fastapi.core.init_settings import global_settings

def setup_cors(app):
    # Check if we should allow all origins (for debugging)
    allow_all_origins = os.getenv("ALLOW_ALL_ORIGINS", "false").lower() == "true"
    
    if allow_all_origins:
        print("⚠️ WARNING: CORS is set to allow ALL origins. Only use this for debugging!")
        origins = ["*"]
        allow_credentials = False  # Can't use credentials with wildcard origins
    else:
        # Define allowed origins from environment variables
        origins = [
            global_settings.CLIENT_URL,
            "http://localhost",
            "http://localhost:5000", 
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5000",
            "http://127.0.0.1:8000"
        ]
        
        # Add API_BASE_URL if it's different from CLIENT_URL and not empty
        if global_settings.API_BASE_URL and global_settings.API_BASE_URL != global_settings.CLIENT_URL:
            origins.append(global_settings.API_BASE_URL)
        
        # Add additional origins from environment variable
        additional_origins = os.getenv("ADDITIONAL_CORS_ORIGINS", "")
        if additional_origins:
            origins.extend([origin.strip() for origin in additional_origins.split(",")])
        
        # Remove empty strings and duplicates
        origins = list(set([origin for origin in origins if origin]))
        allow_credentials = True
    
    print(f"🌐 CORS allowed origins: {origins}")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "*",
            "Authorization",
            "Content-Type", 
            "Accept",
            "Accept-Language",
            "Accept-Encoding",
            "Connection",
            "User-Agent"
        ],
        expose_headers=["*"]
    )

def setup_session(app):
    # Add session middleware with a custom expiration time (e.g., 30 minutes)
    app.add_middleware(SessionMiddleware, 
                       secret_key="your_secret_key", 
                       max_age=1800)  # 1800 seconds = 30 minutes

async def doc_protect_middleware(request: Request, call_next):
    if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
        if not request.session.get('authenticated'):
            return RedirectResponse(url="/login")
    response = await call_next(request)
    return response

def setup_https_redirect(app):
    """HTTPS redirect disabled - Railway handles SSL termination."""
    print("ℹ️ HTTPS redirect disabled (Railway handles SSL termination)")

async def ensure_https_redirect_middleware(request: Request, call_next):
    """
    Middleware to ensure redirects use HTTPS in production while avoiding redirect loops.
    Only applies to Railway production environment.
    """
    response = await call_next(request)
    
    # Only apply in production (Railway provides RAILWAY_PROJECT_ID when deployed)
    if os.getenv("RAILWAY_PROJECT_ID") and response.status_code in (301, 302, 307, 308):
        # Check if this is a redirect response
        if "location" in response.headers:
            location = response.headers["location"]
            # Convert HTTP redirects to HTTPS
            if location.startswith("http://"):
                response.headers["location"] = location.replace("http://", "https://", 1)
                print(f"🔄 Converted redirect from HTTP to HTTPS: {location}")
    
    return response

def setup_redirect_protocol_fix(app):
    """Add middleware to fix redirect protocols in production."""
    if os.getenv("RAILWAY_PROJECT_ID"):
        app.middleware("http")(ensure_https_redirect_middleware)
        print("🔧 Redirect protocol fix enabled for production")

def add_doc_protect(app):
    app.middleware("http")(doc_protect_middleware)