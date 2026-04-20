import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from typing import List, Dict, Any

from .database import engine, get_db
from . import models, schemas, auth

models.Base.metadata.create_all(bind=engine)

def ensure_demo_users(db: Session):
    # Ensure tables exist
    models.Base.metadata.create_all(bind=engine)
    
    def seed_user(email, password, fname, lname, role, color):
        u = db.query(models.User).filter(models.User.email == email).first()
        if not u:
            db.add(models.User(
                email=email, hashed_password=auth.get_password_hash(password),
                fname=fname, lname=lname, role=role, color=color
            ))
            db.commit()

    seed_user("admin@edu.uz", "admin123", "Super", "Admin", "admin", "#3b82f6")
    seed_user("teacher@edu.uz", "teach123", "O'qituvchi", "Demo", "teacher", "#10b981")
    seed_user("student@edu.uz", "stud123", "Talaba", "Demo", "student", "#8b5cf6")

app = FastAPI(title="EduAssess Full-Stack API")

from fastapi.responses import JSONResponse
from fastapi.requests import Request
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = f"{type(exc).__name__}: {str(exc)}\n{traceback.format_exc()}"
    print(error_msg)
    return JSONResponse(status_code=500, content={"detail": error_msg})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/debug/seed")
def manual_seed(db: Session = Depends(get_db)):
    try:
        ensure_demo_users(db)
        users = db.query(models.User).all()
        return {"status": "success", "user_count": len(users), "users": [u.email for u in users]}
    except Exception as e:
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}

@app.get("/api/debug/users")
def debug_users(db: Session = Depends(get_db)):
    try:
        users = db.query(models.User).all()
        return [{"id": u.id, "email": u.email, "role": u.role} for u in users]
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/debug/db-url")
def debug_db_url():
    url = os.getenv("DATABASE_URL", "NOT_SET")
    return {"url_prefix": url[:15] if url else "Empty", "full_len": len(url) if url else 0}

@app.get("/api/health")
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running!"}

@app.get("/api/debug/ping")
@app.get("/debug/ping")
def ping():
    return {"ping": "pong"}

# --- AUTH ROUTES ---
@app.post("/api/auth/login")
@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Ensure demo users exist
    ensure_demo_users(db)
    
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login topilmadi: {form_data.username}. Seedlash uchun /api/debug/seed manziliga o'ting.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Parol noto'g'ri",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.active:
        raise HTTPException(status_code=400, detail="Foydalanuvchi faol emas")
        
    access_token = auth.create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {
            "id": user.id, "email": user.email, "fname": user.fname, 
            "lname": user.lname, "role": user.role, "color": user.color,
            "groupId": user.group_id
        }
    }

# --- BULK DATA ROUTE (For initial hydration) ---
# To minimize frontend refactoring, frontend can fetch all data on load
@app.get("/api/data")
def get_all_data(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    faculties = db.query(models.Faculty).all()
    departments = db.query(models.Department).all()
    groups = db.query(models.Group).all()
    users = db.query(models.User).all()
    subjects = db.query(models.Subject).all()
    assignments = db.query(models.Assignment).all()
    submissions = db.query(models.Submission).all()
    tests = db.query(models.Test).all()
    results = db.query(models.TestResult).all()
    mistakes = db.query(models.Mistake).all()
    
    # Needs transformation to match frontend DB structure
    def to_dict(obj):
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    
    def transform_subject(s):
        d = to_dict(s)
        d['teacherId'] = s.teacher_id
        d['groupIds'] = [link.group_id for link in s.group_links]
        return d
    
    out_users = []
    for u in users:
        ud = to_dict(u)
        ud['groupId'] = u.group_id
        ud.pop('hashed_password')
        out_users.append(ud)

    out_tests = []
    for t in tests:
        td = to_dict(t)
        td['subjectId'] = t.subject_id
        td['passingScore'] = getattr(t, 'passing_score', 60)
        td['questions'] = [{"id": q.id, "text": q.text, "opts": eval(q.opts), "correct": q.correct, "diff": q.diff, "time": q.time} for q in t.questions]
        out_tests.append(td)

    # Simplified mappings
    return {
        "faculties": [to_dict(x) for x in faculties],
        "departments": [{"id": x.id, "name": x.name, "facultyId": x.faculty_id} for x in departments],
        "groups": [{"id": x.id, "name": x.name, "deptId": x.dept_id, "course": x.course} for x in groups],
        "users": out_users,
        "subjects": [transform_subject(x) for x in subjects],
        "assignments": [{"id": x.id, "subjectId": x.subject_id, "title": x.title, "desc": x.description, "maxScore": x.max_score, "deadline": x.deadline.isoformat() if x.deadline else None, "types": x.types, "createdAt": x.created_at.isoformat()} for x in assignments],
        "submissions": [{"id": x.id, "assignmentId": x.assignment_id, "studentId": x.student_id, "fileName": x.file_name, "comment": x.comment, "status": x.status, "score": x.score, "teacherComment": x.teacher_comment, "submittedAt": x.submitted_at.isoformat()} for x in submissions],
        "tests": out_tests,
        "results": [{"id": x.id, "testId": x.test_id, "studentId": x.student_id, "score": x.score, "easy": x.easy_stats, "mid": x.mid_stats, "hard": x.hard_stats, "cheatCount": x.cheat_count, "date": x.date.isoformat()} for x in results],
        "mistakes": [{"id": x.id, "q": x.q_text, "userAns": x.user_ans, "correct": x.correct_ans, "diff": x.diff, "explanation": x.explanation, "studentId": x.student_id, "testId": x.test_id} for x in mistakes]
    }

# --- ACTIONS ---
from pydantic import BaseModel
class GenericPayload(BaseModel):
    action: str
    data: Dict[str, Any]

@app.post("/api/action")
def perform_action(payload: GenericPayload, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    action = payload.action
    d = payload.data
    
    if action == "saveUser":
        if "id" in d and d["id"]:
            u = db.query(models.User).filter(models.User.id == d["id"]).first()
            if u:
                u.fname = d['fname']
                u.lname = d['lname']
                u.email = d['email']
                u.role = d['role']
                u.group_id = d.get('groupId')
                if 'pass' in d and d['pass']:
                    u.hashed_password = auth.get_password_hash(d['pass'])
        else:
            u = models.User(
                fname=d['fname'], lname=d['lname'], email=d['email'],
                role=d['role'], group_id=d.get('groupId'), active=True,
                color=d.get('color', '#3b82f6'),
                hashed_password=auth.get_password_hash(d['pass'])
            )
            db.add(u)
        db.commit()
    elif action == "toggleUser":
        u = db.query(models.User).filter(models.User.id == d["id"]).first()
        if u:
            u.active = not u.active
            db.commit()
            
    elif action == "saveFaculty":
        f = models.Faculty(name=d["name"], code=d["code"])
        db.add(f)
        db.commit()
    elif action == "deleteFaculty":
        f = db.query(models.Faculty).filter(models.Faculty.id == d["id"]).first()
        if f: db.delete(f); db.commit()
        
    elif action == "saveDept":
        dp = models.Department(name=d["name"], faculty_id=d["facultyId"])
        db.add(dp)
        db.commit()
    elif action == "deleteDept":
        dp = db.query(models.Department).filter(models.Department.id == d["id"]).first()
        if dp: db.delete(dp); db.commit()
        
    elif action == "saveGroup":
        g = models.Group(name=d["name"], course=d["course"], dept_id=d["deptId"])
        db.add(g)
        db.commit()
    elif action == "deleteGroup":
        g = db.query(models.Group).filter(models.Group.id == d["id"]).first()
        if g: db.delete(g); db.commit()
        
    elif action == "saveSubject":
        s = models.Subject(name=d["name"], credits=d["credits"], teacher_id=d["teacherId"])
        db.add(s)
        db.commit()
        db.refresh(s)
        for gid in d["groupIds"]:
            db.add(models.SubjectGroupLink(subject_id=s.id, group_id=gid))
        db.commit()
    elif action == "deleteSubject":
        s = db.query(models.Subject).filter(models.Subject.id == d["id"]).first()
        if s: db.delete(s); db.commit()

    elif action == "saveAssignment":
        import datetime
        a = models.Assignment(
            title=d["title"], description=d.get("desc",""), max_score=d["maxScore"],
            types=d.get("types",""), subject_id=d["subjectId"]
        )
        if "deadline" in d:
            a.deadline = datetime.datetime.fromisoformat(d["deadline"])
        db.add(a)
        db.commit()
    
    elif action == "submitGrade":
        sub = db.query(models.Submission).filter(models.Submission.id == d["id"]).first()
        if sub:
            sub.score = d["score"]
            sub.teacher_comment = d.get("comment","")
            sub.status = "graded"
            db.commit()
            
    elif action == "saveQuiz":
        t = models.Test(
            title=d["title"], attempts=d["attempts"], days=d["days"],
            passing_score=d["passingScore"], subject_id=d["subjectId"]
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        for q in d["questions"]:
            qn = models.Question(
                text=q["text"], opts=str(q["opts"]), correct=q["correct"],
                diff=q["diff"], time=q.get("time", 45), test_id=t.id
            )
            db.add(qn)
        db.commit()

    elif action == "submitAssignment":
        s = models.Submission(
            assignment_id=d["assignmentId"], student_id=current_user.id,
            file_name=d["fileName"], comment=d.get("comment","")
        )
        db.add(s)
        db.commit()

    elif action == "submitTest":
        import datetime
        r = models.TestResult(
            test_id=d["testId"], student_id=current_user.id, score=d["score"],
            easy_stats=d["easy"], mid_stats=d["mid"], hard_stats=d["hard"],
            cheat_count=d.get("cheatCount", 0), date=datetime.datetime.utcnow()
        )
        db.add(r)
        
        if "mistakes" in d:
            for m in d["mistakes"]:
                db.add(models.Mistake(
                    q_text=m["q"], user_ans=m["userAns"], correct_ans=m["correct"],
                    diff=m["diff"], explanation=m.get("explanation",""),
                    test_id=d["testId"], student_id=current_user.id
                ))
        db.commit()
        
    return {"message": "Success"}
