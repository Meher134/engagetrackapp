import asyncio
from backend.db.db import students_collection, lecturers_collection
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed():
    await students_collection.delete_many({})
    await lecturers_collection.delete_many({})

    await students_collection.insert_one({
        "roll_number": "S123",
        "first_name": "Alice",
        "last_name": "Student",
        "email": "alice@student.com",
        "phone": "1234567890",
        "password_hash": pwd.hash("student123"),
        "class_ids": [],
        "completed_class_ids": []
    })

    await lecturers_collection.insert_one({
        "employee_id": "L456",
        "first_name": "Bob",
        "last_name": "Lecturer",
        "email": "bob@lecturer.com",
        "phone": "0987654321",
        "password_hash": pwd.hash("lecturer456"),
        "current_class_ids": [],
        "total_classes_taught": 0
    })

asyncio.run(seed())
