import os
import sys
import traceback

# Ensure the api/ directory is in the Python path so local modules are found
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.requests import Request

STARTUP_ERROR = None

try:
    from fastapi import Depends, HTTPException, status
    from fastapi.middleware.cors import CORSMiddleware
    from sqlalchemy.orm import Session
    from typing import List, Dict, Any
    from pydantic import BaseModel

    from database import engine, get_db
    import models, schemas, auth
except Exception as _e:
    STARTUP_ERROR = traceback.format_exc()

app = FastAPI(title="EduAssess Full-Stack API")

@app.get("/api/health")
@app.get("/health")
def health_check():
    if STARTUP_ERROR:
        return {"status": "error", "startup_error": STARTUP_ERROR}
    return {"status": "ok", "message": "Backend is running!"}

if STARTUP_ERROR:
    # Minimal app — only health works, startup error is exposed
    pass
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        error_msg = f"{type(exc).__name__}: {str(exc)}\n{traceback.format_exc()}"
        print(error_msg)
        return JSONResponse(status_code=500, content={"detail": error_msg})

    def ensure_demo_users(db):
        try:
            models.Base.metadata.create_all(bind=engine)
            # Quick schema check — if users table has wrong columns, reset
            db.execute(__import__('sqlalchemy').text("SELECT username FROM users LIMIT 1"))
        except Exception:
            db.rollback()
            models.Base.metadata.drop_all(bind=engine)
            models.Base.metadata.create_all(bind=engine)

        def seed_user(username, password, fname, lname, role, color):
            u = db.query(models.User).filter(models.User.username == username).first()
            if not u:
                db.add(models.User(
                    username=username, hashed_password=auth.get_password_hash(password),
                    fname=fname, lname=lname, role=role, color=color
                ))
                db.commit()

        seed_user("admin@edu.uz", "admin123", "Super", "Admin", "admin", "#3b82f6")

    @app.get("/api/debug/seed")
    def manual_seed(db=Depends(get_db)):
        try:
            ensure_demo_users(db)
            users = db.query(models.User).all()
            return {"status": "success", "user_count": len(users), "users": [u.username for u in users]}
        except Exception as e:
            return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}

    @app.get("/api/debug/users")
    def debug_users(db=Depends(get_db)):
        try:
            users = db.query(models.User).all()
            return [{"id": u.id, "username": u.username, "role": u.role} for u in users]
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/debug/db-url")
    def debug_db_url():
        url = os.getenv("DATABASE_URL", "NOT_SET")
        return {"url_prefix": url[:15] if url else "Empty", "full_len": len(url) if url else 0}

    @app.get("/api/config")
    def get_config():
        return {"groqKey": os.getenv("GROQ_KEY", "").strip()}

    @app.get("/api/debug/ping")
    @app.get("/debug/ping")
    def ping():
        return {"ping": "pong"}

    class LoginSchema(BaseModel):
        username: str
        password: str

    @app.post("/api/auth/login")
    @app.post("/auth/login")
    async def login(request: Request, db=Depends(get_db)):
        try:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                data = await request.json()
                username = data.get("username")
                password = data.get("password")
            else:
                form = await request.form()
                username = form.get("username")
                password = form.get("password")

            if not username or not password:
                raise HTTPException(status_code=422, detail="Login va parol kiritilmadi")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Ma'lumotlarni o'qishda xato: {str(e)}")

        ensure_demo_users(db)

        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Login topilmadi: {username}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not auth.verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Parol noto'g'ri",
                headers={"WWW-Authenticate": "Bearer"},
            )

        from datetime import timedelta
        access_token = auth.create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(days=30)
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id, "username": user.username, "fname": user.fname,
                "lname": user.lname, "role": user.role, "color": user.color,
                "groupId": user.group_id
            }
        }

    @app.get("/api/data")
    def get_all_data(db=Depends(get_db), current_user=Depends(auth.get_current_user)):
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
        schedules = db.query(models.Schedule).all()
        messages = db.query(models.Message).all()
        polls = db.query(models.Poll).all()
        poll_responses = db.query(models.PollResponse).all()

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
            "schedules": [{"id": x.id, "groupId": x.group_id, "subjectId": x.subject_id, "day": x.day, "period": x.period, "room": x.room, "weekType": x.week_type} for x in schedules],
            "messages": [{"id": x.id, "fromUserId": x.from_user_id, "title": x.title, "body": x.body, "reply": x.reply, "status": x.status, "createdAt": x.created_at.isoformat()} for x in messages],
            "polls": [{"id": x.id, "title": x.title, "options": eval(x.options), "createdBy": x.created_by, "targetRole": x.target_role, "deadline": x.deadline.isoformat() if x.deadline else None, "createdAt": x.created_at.isoformat()} for x in polls],
            "pollResponses": [{"id": x.id, "pollId": x.poll_id, "userId": x.user_id, "answerIdx": x.answer_idx} for x in poll_responses],
            "mistakes": [{"id": x.id, "q": x.q_text, "userAns": x.user_ans, "correct": x.correct_ans, "diff": x.diff, "explanation": x.explanation, "studentId": x.student_id, "testId": x.test_id} for x in mistakes]
        }

    from pydantic import BaseModel as _BaseModel

    class GenericPayload(_BaseModel):
        action: str
        data: Dict[str, Any]

    @app.post("/api/action")
    def perform_action(payload: GenericPayload, db=Depends(get_db), current_user=Depends(auth.get_current_user)):
        action = payload.action
        d = payload.data

        if action == "saveUser":
            password = d.get('pass')
            edit_id = d.get('id')
            u = db.query(models.User).get(edit_id) if edit_id else None
            if u:
                u.fname = d['fname']; u.lname = d['lname']; u.username = d['username']
                u.role = d['role']; u.group_id = d.get('groupId')
                if password:
                    u.hashed_password = auth.get_password_hash(password)
            else:
                u = models.User(
                    fname=d['fname'], lname=d['lname'], username=d['username'],
                    role=d['role'], group_id=d.get('groupId'), active=True,
                    color=d.get('color', '#3b82f6'),
                    hashed_password=auth.get_password_hash(password)
                )
                db.add(u)
            db.commit()
        elif action == "toggleUser":
            u = db.query(models.User).filter(models.User.id == d["id"]).first()
            if u:
                u.active = not u.active
                db.commit()
        elif action == "deleteUser":
            uid = d["id"]
            db.query(models.Mistake).filter(models.Mistake.student_id == uid).delete()
            db.query(models.PollResponse).filter(models.PollResponse.user_id == uid).delete()
            db.query(models.Message).filter(models.Message.from_user_id == uid).delete()
            db.query(models.TestResult).filter(models.TestResult.student_id == uid).delete()
            db.query(models.Submission).filter(models.Submission.student_id == uid).delete()
            u = db.query(models.User).filter(models.User.id == uid).first()
            if u:
                db.delete(u)
                db.commit()
        elif action == "saveFaculty":
            db.add(models.Faculty(name=d["name"], code=d["code"])); db.commit()
        elif action == "deleteFaculty":
            f = db.query(models.Faculty).filter(models.Faculty.id == d["id"]).first()
            if f: db.delete(f); db.commit()
        elif action == "saveDept":
            db.add(models.Department(name=d["name"], faculty_id=d["facultyId"])); db.commit()
        elif action == "deleteDept":
            dp = db.query(models.Department).filter(models.Department.id == d["id"]).first()
            if dp: db.delete(dp); db.commit()
        elif action == "saveGroup":
            db.add(models.Group(name=d["name"], course=d["course"], dept_id=d["deptId"])); db.commit()
        elif action == "deleteGroup":
            g = db.query(models.Group).filter(models.Group.id == d["id"]).first()
            if g: db.delete(g); db.commit()
        elif action == "saveSubject":
            s = models.Subject(name=d["name"], credits=d["credits"], teacher_id=d["teacherId"])
            db.add(s); db.commit(); db.refresh(s)
            for gid in d["groupIds"]:
                db.add(models.SubjectGroupLink(subject_id=s.id, group_id=gid))
            db.commit()
        elif action == "deleteSubject":
            s = db.query(models.Subject).filter(models.Subject.id == d["id"]).first()
            if s: db.delete(s); db.commit()
        elif action == "saveAssignment":
            import datetime
            a = models.Assignment(
                title=d["title"], description=d.get("desc", ""), max_score=d["maxScore"],
                types=d.get("types", ""), subject_id=d["subjectId"]
            )
            if "deadline" in d:
                a.deadline = datetime.datetime.fromisoformat(d["deadline"])
            db.add(a); db.commit()
        elif action == "submitGrade":
            sub = db.query(models.Submission).filter(models.Submission.id == d["id"]).first()
            if sub:
                sub.score = d["score"]; sub.teacher_comment = d.get("comment", "")
                sub.status = "graded"; db.commit()
        elif action == "saveQuiz":
            t = models.Test(
                title=d["title"], attempts=d["attempts"], days=d["days"],
                passing_score=d["passingScore"], subject_id=d["subjectId"]
            )
            db.add(t); db.commit(); db.refresh(t)
            for q in d["questions"]:
                db.add(models.Question(
                    text=q["text"], opts=str(q["opts"]), correct=q["correct"],
                    diff=q["diff"], time=q.get("time", 45), test_id=t.id
                ))
            db.commit()
        elif action == "submitAssignment":
            db.add(models.Submission(
                assignment_id=d["assignmentId"], student_id=current_user.id,
                file_name=d["fileName"], comment=d.get("comment", "")
            )); db.commit()
        elif action == "saveSchedule":
            db.add(models.Schedule(
                group_id=d["groupId"], subject_id=d["subjectId"],
                day=d["day"], period=d["period"],
                room=d.get("room", ""), week_type=d.get("weekType", "har")
            )); db.commit()
        elif action == "deleteSchedule":
            s = db.query(models.Schedule).filter(models.Schedule.id == d["id"]).first()
            if s: db.delete(s); db.commit()
        elif action == "sendMessage":
            db.add(models.Message(
                from_user_id=current_user.id, title=d["title"], body=d["body"]
            )); db.commit()
        elif action == "replyMessage":
            m = db.query(models.Message).filter(models.Message.id == d["id"]).first()
            if m: m.reply = d["reply"]; m.status = "replied"; db.commit()
        elif action == "markMessageRead":
            m = db.query(models.Message).filter(models.Message.id == d["id"]).first()
            if m and m.status == "new": m.status = "read"; db.commit()
        elif action == "createPoll":
            db.add(models.Poll(
                title=d["title"], options=str(d["options"]),
                created_by=current_user.id, target_role=d.get("targetRole", "all")
            )); db.commit()
        elif action == "deletePoll":
            p = db.query(models.Poll).filter(models.Poll.id == d["id"]).first()
            if p: db.delete(p); db.commit()
        elif action == "answerPoll":
            existing = db.query(models.PollResponse).filter(
                models.PollResponse.poll_id == d["pollId"],
                models.PollResponse.user_id == current_user.id
            ).first()
            if not existing:
                db.add(models.PollResponse(
                    poll_id=d["pollId"], user_id=current_user.id, answer_idx=d["answerIdx"]
                )); db.commit()
        elif action == "updateProfile":
            u = db.query(models.User).filter(models.User.id == d["id"]).first()
            if not u:
                raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
            u.fname = d.get("fname", u.fname)
            u.lname = d.get("lname", u.lname)
            u.username = d.get("username", u.username)
            if d.get("pass"):
                u.hashed_password = auth.get_password_hash(d["pass"])
            db.commit()
        elif action == "submitTest":
            import datetime
            r = models.TestResult(
                test_id=d["testId"], student_id=current_user.id, score=d["score"],
                easy_stats=d["easy"], mid_stats=d["mid"], hard_stats=d["hard"],
                cheat_count=d.get("cheatCount", 0), date=datetime.datetime.utcnow()
            )
            db.add(r)
            for m in d.get("mistakes", []):
                db.add(models.Mistake(
                    q_text=m["q"], user_ans=m["userAns"], correct_ans=m["correct"],
                    diff=m["diff"], explanation=m.get("explanation", ""),
                    test_id=d["testId"], student_id=current_user.id
                ))
            db.commit()

        return {"message": "Success"}
