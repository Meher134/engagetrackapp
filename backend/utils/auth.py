from fastapi import Request
from bson import ObjectId

async def get_current_user(request: Request):
    user_id = request.cookies.get("user_id")
    role = request.cookies.get("role")
    
    if not user_id or not role:
        return None, None

    try:
        return ObjectId(user_id), role
    except:
        return None, None
