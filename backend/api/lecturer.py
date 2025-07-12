from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from backend.db.db import classes_collection, students_collection, lecturers_collection, sessions_collection, engagement_metrics_collection, typing_logs_collection
from fastapi.responses import HTMLResponse
from datetime import datetime
from bson import ObjectId

router = APIRouter()
templates = Jinja2Templates(directory="frontend/lecturer_dashboard/templates")

@router.get("/lecturer/dashboard", response_class=HTMLResponse)
async def lecturer_dashboard(request: Request):
    flash_message = request.cookies.get("flash_message")

    employee_id = await _get_employee_id_from_session(request)
    if not employee_id:
        return RedirectResponse("/login", status_code=302)

    lecturer = await lecturers_collection.find_one({"employee_id": employee_id})
    if not lecturer:
        return RedirectResponse("/login", status_code=302)

    all_classes = await classes_collection.find({"employee_id": employee_id}).to_list(length=100)

    current_classes = []
    completed_classes = []

    for cls in all_classes:
        session_exists = await sessions_collection.find_one({"class_id": cls["_id"]})
        if session_exists:
            completed_classes.append(cls)
        else:
            current_classes.append(cls)

    response = templates.TemplateResponse("lecturer_dashboard.html", {
        "request": request,
        "lecturer": lecturer,
        "current_classes": current_classes,
        "completed_classes": completed_classes,
        "flash_message": flash_message
    })

    if flash_message:
        response.delete_cookie("flash_message")

    return response




@router.get("/lecturer/add-class", response_class=HTMLResponse)
async def add_class_form(request: Request):
    students = await students_collection.find({}).to_list(length=100)
    return templates.TemplateResponse("add_class.html", 
    {
        "request": request,
        "students": students
    })

@router.post("/lecturer/add-class")
async def add_class(
    request: Request,
    class_id: str = Form(...),
    subject: str = Form(...),
    student_ids: list[str] = Form(default=[])
):
    employee_id = await _get_employee_id_from_session(request)
    if not employee_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    class_doc = {
        "class_id": class_id,
        "subject": subject,
        "employee_id": employee_id,
        "student_ids": student_ids,
        "created_at": datetime.utcnow()
    }

    await classes_collection.insert_one(class_doc)

    for sid in student_ids:
        await students_collection.update_one(
            {"roll_number": sid},
            {"$addToSet": {"class_ids": class_id}}
        )
    await lecturers_collection.update_one(
        {"employee_id": employee_id},
        {
            "$addToSet": {"current_class_ids": class_id},
            "$inc": {"total_classes_taught": 1}
        }
    )

    return RedirectResponse(url="/lecturer/dashboard", status_code=303)



@router.post("/lecturer/class/{class_id}/start-session")
async def start_session(class_id: str):
    if not ObjectId.is_valid(class_id):
        raise HTTPException(status_code=400, detail="Invalid class ID")

    class_obj_id = ObjectId(class_id)

    existing_sessions = await sessions_collection.find({"class_id": class_obj_id}).to_list(length=100)
    if existing_sessions:
        session_ids = [session["_id"] for session in existing_sessions]
        await sessions_collection.delete_many({"_id": {"$in": session_ids}})
        await classes_collection.update_one(
            {"_id": class_obj_id},
            {"$pull": {"sessions": {"$in": session_ids}}}
        )

    new_session = {
        "class_id": class_obj_id,
        "date": datetime.utcnow(),
        "transcript_text": "",
        "audio_path": ""
    }
    result = await sessions_collection.insert_one(new_session)

    await classes_collection.update_one(
        {"_id": class_obj_id},
        {"$push": {"sessions": result.inserted_id}}
    )

    return {
        "session_id": str(result.inserted_id),
        "message": "New session started successfully"
    }

@router.post("/lecturer/class/{class_id}/session/{session_id}/upload-transcript")
async def upload_transcript(
    class_id: str,
    session_id: str,
    transcript_text: str = Form(...)
):
    if not (ObjectId.is_valid(class_id) and ObjectId.is_valid(session_id)):
        raise HTTPException(status_code=400, detail="Invalid IDs")

    result = await sessions_collection.update_one(
        {"_id": ObjectId(session_id), "class_id": ObjectId(class_id)},
        {"$set": {"transcript_text": transcript_text}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")

    response = RedirectResponse(url="/lecturer/dashboard", status_code=303)
    response.set_cookie(key="flash_message", value="Transcript saved successfully!", max_age=5)  # cookie lasts 5 seconds
    return response

@router.get("/lecturer/class/{class_id}/record-lecture")
async def record_lecture_ui(request: Request, class_id: str):
    return templates.TemplateResponse("record_lecture2.html", {"request": request, "class_id": class_id})


async def _get_employee_id_from_session(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user_doc = await lecturers_collection.find_one({"_id": ObjectId(user_id)})
    return user_doc["employee_id"] if user_doc else None


@router.get("/lecturer/analytics/class/{class_id}", response_class=HTMLResponse)
async def class_analytics(request: Request, class_id: str):
    if not ObjectId.is_valid(class_id):
        return HTMLResponse("Invalid class ID", status_code=400)

    class_obj = await classes_collection.find_one({"_id": ObjectId(class_id)})
    if not class_obj:
        return HTMLResponse("Class not found", status_code=404)

    student_rolls = class_obj.get("student_ids", [])
    sessions = class_obj.get("sessions", [])
    if not sessions:
        return HTMLResponse("No sessions recorded yet.", status_code=404)

    logs = await typing_logs_collection.find({
        "session_id": {"$in": sessions}
    }).to_list(length=200)

    all_students = await students_collection.find(
        {"roll_number": {"$in": student_rolls}}
    ).to_list(length=100)

    submitted_student_ids = {str(log["student_id"]) for log in logs}
    submitted_students = [s for s in all_students if str(s["_id"]) in submitted_student_ids]
    non_submitted_students = [s for s in all_students if str(s["_id"]) not in submitted_student_ids]


    total_students = len(all_students)
    engagement_sum = 0

    for log in logs:
        score = log.get("analysis_report", {}).get("engagement_score", -1)
        if score == 1:
            engagement_sum += 1
        elif score == 0:
            engagement_sum += 0.5
        else: 
            engagement_sum += 0

    avg_engagement = (engagement_sum / total_students) * 100 if total_students > 0 else 0

    return templates.TemplateResponse("class_analytics.html", {
        "request": request,
        "class_obj": class_obj,
        "submitted_students": submitted_students,
        "non_submitted_students": non_submitted_students,
        "avg_engagement": round(avg_engagement, 2)
    })



@router.get("/lecturer/class/{class_id}/manage", response_class=HTMLResponse)
async def manage_class_page(request: Request, class_id: str):
    user_id = request.session.get("user_id")
    lecturer = await lecturers_collection.find_one({"_id": ObjectId(user_id)})
    
    class_obj = await classes_collection.find_one({"class_id": class_id})
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found.")

    current_students = await students_collection.find(
        {"roll_number": {"$in": class_obj["student_ids"]}}
    ).to_list(length=100)

    all_students = await students_collection.find().to_list(length=100)
    available_students = [s for s in all_students if s["roll_number"] not in class_obj["student_ids"]]

    return templates.TemplateResponse("manage_class.html", {
        "request": request,
        "class_obj": class_obj,
        "current_students": current_students,
        "available_students": available_students
    })

@router.post("/lecturer/class/{class_id}/update-students")
async def update_class_students(
    request: Request,
    class_id: str,
    add_student_ids: list[str] = Form(default=[]),
    remove_student_ids: list[str] = Form(default=[])
):
    class_doc = await classes_collection.find_one({"class_id": class_id})
    if not class_doc:
        raise HTTPException(status_code=404, detail="Class not found.")

    await classes_collection.update_one(
        {"class_id": class_id},
        {"$addToSet": {"student_ids": {"$each": add_student_ids}}}
    )
    for sid in add_student_ids:
        await students_collection.update_one(
            {"roll_number": sid},
            {"$addToSet": {"class_ids": class_id}}
        )

    await classes_collection.update_one(
        {"class_id": class_id},
        {"$pull": {"student_ids": {"$in": remove_student_ids}}}
    )
    for sid in remove_student_ids:
        await students_collection.update_one(
            {"roll_number": sid},
            {"$pull": {"class_ids": class_id}}
        )

    return RedirectResponse(f"/lecturer/class/{class_id}/manage", status_code=303)


@router.get("/lecturer/analytics/student/{student_id}/class/{class_id}", response_class=HTMLResponse)
async def view_student_engagement(request: Request, student_id: str, class_id: str):
    student = await students_collection.find_one({"_id": ObjectId(student_id)})
    class_doc = await classes_collection.find_one({"_id": ObjectId(class_id)})
    session = await sessions_collection.find_one({"class_id": ObjectId(class_id)})

    if not (student and class_doc and session):
        return HTMLResponse("Data not found", status_code=404)

    typing_log = await typing_logs_collection.find_one({
        "student_id": ObjectId(student_id),
        "session_id": session["_id"]
    })

    essay_text = ""
    if typing_log:
        raw_log = typing_log.get("raw_log", {})
        essay_text = raw_log.get("essay_text", "")
        existing_feedback = typing_log.get("feedback", "")
    else:
        existing_feedback = ""

    return templates.TemplateResponse("student_engagement_detail.html", {
        "request": request,
        "student": student,
        "class_": class_doc,
        "typing_log": typing_log,
        "essay_text": essay_text,
        "feedback": existing_feedback
    })


@router.post("/lecturer/analytics/student/{student_id}/class/{class_id}/feedback")
async def submit_feedback(
    student_id: str,
    class_id: str,
    feedback: str = Form(...)
):
    session = await sessions_collection.find_one({"class_id": ObjectId(class_id)})

    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    result = await typing_logs_collection.update_one(
        {"student_id": ObjectId(student_id), "session_id": session["_id"]},
        {"$set": {"feedback": feedback}}
    )

    if result.modified_count == 0:
        return JSONResponse({"message": "Feedback not saved."}, status_code=400)

    return RedirectResponse(
        url=f"/lecturer/analytics/student/{student_id}/class/{class_id}",
        status_code=303
    )
