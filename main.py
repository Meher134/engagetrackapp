import os
import sys
import traceback
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware

print("Starting FastAPI app...")

try:
    load_dotenv()
    app = FastAPI()
    
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SESSION_SECRET_KEY")
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


    from backend.api import auth, student, lecturer
    

    app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
    app.include_router(auth.router)
    app.include_router(student.router)
    app.include_router(lecturer.router)

    print("App initialized successfully")

except Exception as e:
    print("CRASH DURING STARTUP")
    traceback.print_exc()
    sys.exit(1)
