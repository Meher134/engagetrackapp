from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from backend.db.db import students_collection, lecturers_collection
from passlib.context import CryptContext
from passlib.hash import bcrypt
import re 
from fastapi.templating import Jinja2Templates
from bson import ObjectId
import re
router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
templates = Jinja2Templates(directory="frontend/templates")

@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login_post(
    request: Request,
    role: str = Form(...),
    identifier: str = Form(...),
    password: str = Form(...)
):

    if role == "student":
        user = await students_collection.find_one({"roll_number": identifier})
        dashboard = "/student/dashboard"
    elif role == "lecturer":
        user = await lecturers_collection.find_one({"employee_id": identifier})
        dashboard = "/lecturer/dashboard"
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid role"})

    if not user or not pwd_context.verify(password, user["password_hash"]):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})


    request.session["user_id"] = str(user["_id"])
    request.session["role"] = role
    request.session["name"] = user["first_name"]

    return RedirectResponse(url=dashboard, status_code=302)
def is_password_strong(password: str) -> bool:

    pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{8,}$"
    return re.match(pattern, password) is not None

@router.get("/signup")
async def signup_form(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@router.post("/signup")
async def signup_user(
    request: Request,
    role: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    identifier: str = Form(...),
    password: str = Form(...)
):
    if not is_password_strong(password):
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Password must be at least 8 characters long and include 1 uppercase letter, 1 lowercase letter, 1 digit, and 1 special character.",
            "role": role,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "identifier": identifier
        })

    hashed_password = bcrypt.hash(password)

    if role == "student":
        exists = await students_collection.find_one({"roll_number": identifier})
        if exists:
            return templates.TemplateResponse("signup.html", {"request": request, "error": "Roll number already exists"})

        student_doc = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "roll_number": identifier,
            "password_hash": hashed_password,
            "class_ids": [],
            "completed_class_ids": [],
            "typing_baseline_log": {}
        }
        await students_collection.insert_one(student_doc)

    elif role == "lecturer":
        exists = await lecturers_collection.find_one({"employee_id": identifier})
        if exists:
            return templates.TemplateResponse("signup.html", {"request": request, "error": "Lecturer ID already exists"})

        lecturer_doc = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "employee_id": identifier,
            "password_hash": hashed_password,
            "current_class_ids": [],
            "total_classes_taught": 0
        }
        await lecturers_collection.insert_one(lecturer_doc)

    else:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Invalid role"})

    return RedirectResponse("/login", status_code=302)

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)
