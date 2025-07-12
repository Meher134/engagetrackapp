from fastapi import APIRouter, Request, Form
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from backend.db.db import students_collection, typing_logs_collection, essays_collection,sessions_collection, classes_collection
from bson import ObjectId
from datetime import datetime
from backend.services.engagement_engine import evaluate_engagement
from backend.services.question_answering import answer_question_from_transcript
from starlette.middleware.sessions import SessionMiddleware

router = APIRouter()
templates = Jinja2Templates(directory="frontend/student_dashboard/templates")

@router.get("/student/typing-test")
async def typing_test_ui(request: Request):
    if not request.session.get("user_id") or request.session.get("role") != "student":
        return RedirectResponse("/login")

    return templates.TemplateResponse("typing_test.html", {
        "request": request,
        "student_id": request.session["user_id"]
    })


@router.post("/student/typing-test")
async def submit_typing_data(request: Request):
    try:
        data = await request.json()
        student_id = request.session.get("user_id")
        if not student_id:
            return JSONResponse({"error": "Not logged in"}, status_code=401)

        session_id = request.session.get("active_session_id")
        essay_text = data.get("essay_text", "")  

        student = await students_collection.find_one({"_id": ObjectId(student_id)})
        session = await sessions_collection.find_one({"_id": ObjectId(session_id)})

        if not student or not session:
            return JSONResponse({"error": "Invalid student or session"}, status_code=404)

        lecture_text = session.get("transcript_text", "")
        class_id = session.get("class_id")

        essay_doc = {
            "essay_text": essay_text,
            "typing_data": data.get("typing_data", {}),
            "lecture_text": lecture_text
        }

        report = await evaluate_engagement(essay_doc)

        await typing_logs_collection.insert_one({
            "student_id": ObjectId(student_id),
            "session_id": ObjectId(session_id),
            "raw_log": data,
            "analysis_report": report,
            "timestamp": datetime.utcnow()
        })

        if class_id:
            await students_collection.update_one(
                {"_id": ObjectId(student_id)},
                {"$addToSet": {"completed_class_ids": ObjectId(class_id)}}  
            )

        return JSONResponse({
            "status": "success",
            "message": "Typing log analyzed and evaluated.",
            "report": report
        })
    

    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)



@router.get("/student/dashboard", response_class=HTMLResponse)
async def student_dashboard(request: Request):
    user_id, role = request.session.get("user_id"), request.session.get("role")

    if role != "student":
        return RedirectResponse("/login", status_code=302)

    student = await students_collection.find_one({"_id": ObjectId(user_id)})
    if not student:
        return RedirectResponse("/login", status_code=302)

    enrolled_classes = await classes_collection.find(
        {"class_id": {"$in": student["class_ids"]}}
    ).to_list(length=100)

    completed_classes = await classes_collection.find(
        {"_id": {"$in": student["completed_class_ids"]}}
    ).to_list(length=100)

    completed_class_ids = {cls["class_id"] for cls in completed_classes if "class_id" in cls}

    # Remove any class from enrolled_classes that is also in completed_classes
    enrolled_classes = [
        cls for cls in enrolled_classes if cls.get("class_id") not in completed_class_ids
    ]

    return templates.TemplateResponse("student_dashboard.html", {
        "request": request,
        "student": student,
        "enrolled_classes": enrolled_classes,
        "completed_classes": completed_classes
    })


@router.get("/student/class/{class_id}/submit-essay")
async def prepare_typing_test(request: Request, class_id: str):
    user_id, role = request.session.get("user_id"), request.session.get("role")

    if role != "student":
        return RedirectResponse("/login", status_code=302)

    student = await students_collection.find_one({"_id": ObjectId(user_id)})
    if not student:
        return RedirectResponse("/login", status_code=302)

    class_doc = await classes_collection.find_one({"class_id": class_id})
    if not class_doc:
        # Class doesn't exist
        return templates.TemplateResponse("student_dashboard.html", {
            "request": request,
            "student": student,
            "error": f"Class '{class_id}' not found."
        })

    class_obj_id = class_doc["_id"] 


    session = await sessions_collection.find_one({"class_id": class_obj_id})
    if not session:
        request.session["flash_error"] = f"No session recorded yet for class {class_id}."
        return RedirectResponse("/student/dashboard", status_code=302)

  
    request.session["active_session_id"] = str(session["_id"])

    return RedirectResponse("/student/typing-test", status_code=302)


@router.get("/student/class/{class_id}/view-feedback", response_class=HTMLResponse)
async def view_feedback_detail(request: Request, class_id: str):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=302)

    student = await students_collection.find_one({"_id": ObjectId(user_id)})
    class_doc = await classes_collection.find_one({"class_id": class_id})
    session = await sessions_collection.find_one({"class_id": class_doc["_id"]}) if class_doc else None

    typing_log = await typing_logs_collection.find_one({
        "student_id": ObjectId(user_id),
        "session_id": session["_id"] if session else None
    }) if session else None

    essay_text = typing_log.get("raw_log", {}).get("essay_text", "") if typing_log else "Not found"
    transcript_text = session.get("transcript_text", "") if session else "Not available"
    feedback = typing_log.get("feedback", "No feedback provided.") if typing_log else "No feedback yet."
    score = typing_log.get("analysis_report", {}).get("engagement_score", -2)

    if score == -2:
        score_text = "Not evaluated"
    elif score == 0:
        score_text = "Moderate engagement"
    elif score == -1:
        score_text = "No engagement"
    else:
        score_text = "High engagement"

    return templates.TemplateResponse("student_feedback_detail.html", {
        "request": request,
        "class_": class_doc,
        "essay_text": essay_text,
        "transcript_text": transcript_text,
        "feedback": feedback,
        "score_text": score_text
    })
