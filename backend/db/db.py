from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URL)
db = client["student_engagement_db"]

students_collection = db["students"]
lecturers_collection = db["lecturers"]
essays_collection = db["essays"]
classes_collection = db["classes"]
sessions_collection = db["sessions"]
engagement_metrics_collection = db["engagement_metrics"]
typing_logs_collection = db["typing_logs"]
