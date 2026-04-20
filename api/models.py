from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Faculty(Base):
    __tablename__ = "faculties"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    code = Column(String, unique=True, index=True)
    
    departments = relationship("Department", back_populates="faculty", cascade="all, delete-orphan")

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    faculty_id = Column(Integer, ForeignKey("faculties.id"))
    
    faculty = relationship("Faculty", back_populates="departments")
    groups = relationship("Group", back_populates="department", cascade="all, delete-orphan")

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    course = Column(Integer, default=1)
    dept_id = Column(Integer, ForeignKey("departments.id"))
    
    department = relationship("Department", back_populates="groups")
    users = relationship("User", back_populates="group")
    subject_links = relationship("SubjectGroupLink", back_populates="group", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    fname = Column(String)
    lname = Column(String)
    role = Column(String) # admin, teacher, student
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    active = Column(Boolean, default=True)
    color = Column(String, default="#3b82f6")
    
    group = relationship("Group", back_populates="users")
    taught_subjects = relationship("Subject", back_populates="teacher")
    submissions = relationship("Submission", back_populates="student")
    test_results = relationship("TestResult", back_populates="student")

class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    credits = Column(Integer, default=3)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    
    teacher = relationship("User", back_populates="taught_subjects")
    group_links = relationship("SubjectGroupLink", back_populates="subject", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="subject", cascade="all, delete-orphan")
    tests = relationship("Test", back_populates="subject", cascade="all, delete-orphan")

class SubjectGroupLink(Base):
    __tablename__ = "subject_groups"
    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    group_id = Column(Integer, ForeignKey("groups.id"))
    
    subject = relationship("Subject", back_populates="group_links")
    group = relationship("Group", back_populates="subject_links")

class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    max_score = Column(Integer, default=100)
    deadline = Column(DateTime)
    types = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    
    subject = relationship("Subject", back_populates="assignments")
    submissions = relationship("Submission", back_populates="assignment", cascade="all, delete-orphan")

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String)
    comment = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="submitted") # submitted, graded
    score = Column(Integer, nullable=True)
    teacher_comment = Column(Text, nullable=True)
    
    assignment_id = Column(Integer, ForeignKey("assignments.id"))
    student_id = Column(Integer, ForeignKey("users.id"))
    
    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("User", back_populates="submissions")

class Test(Base):
    __tablename__ = "tests"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    attempts = Column(Integer, default=1)
    passing_score = Column(Integer, default=60)
    days = Column(Integer, default=7)
    created_at = Column(DateTime, default=datetime.utcnow)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    
    subject = relationship("Subject", back_populates="tests")
    questions = relationship("Question", back_populates="test", cascade="all, delete-orphan")
    results = relationship("TestResult", back_populates="test", cascade="all, delete-orphan")

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text)
    opts = Column(Text) # JSON string array
    correct = Column(String)
    diff = Column(String) # easy, medium, hard
    time = Column(Integer, default=45)
    test_id = Column(Integer, ForeignKey("tests.id"))
    
    test = relationship("Test", back_populates="questions")

class TestResult(Base):
    __tablename__ = "test_results"
    id = Column(Integer, primary_key=True, index=True)
    score = Column(Integer)
    easy_stats = Column(String)
    mid_stats = Column(String)
    hard_stats = Column(String)
    date = Column(DateTime, default=datetime.utcnow)
    cheat_count = Column(Integer, default=0)
    
    test_id = Column(Integer, ForeignKey("tests.id"))
    student_id = Column(Integer, ForeignKey("users.id"))
    
    test = relationship("Test", back_populates="results")
    student = relationship("User", back_populates="test_results")

class Mistake(Base):
    __tablename__ = "mistakes"
    id = Column(Integer, primary_key=True, index=True)
    q_text = Column(Text)
    user_ans = Column(String)
    correct_ans = Column(String)
    diff = Column(String)
    explanation = Column(Text, nullable=True)

    test_id = Column(Integer, ForeignKey("tests.id"))
    student_id = Column(Integer, ForeignKey("users.id"))

class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    day = Column(String)       # Dushanba..Shanba
    period = Column(Integer)   # 1-7
    room = Column(String, nullable=True)
    week_type = Column(String, default="har")  # har, toq, juft

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    body = Column(Text)
    reply = Column(Text, nullable=True)
    status = Column(String, default="new")  # new, read, replied
    created_at = Column(DateTime, default=datetime.utcnow)

class Poll(Base):
    __tablename__ = "polls"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    options = Column(Text)     # JSON string list
    created_by = Column(Integer, ForeignKey("users.id"))
    target_role = Column(String, default="all")  # all, student, teacher
    deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PollResponse(Base):
    __tablename__ = "poll_responses"
    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer, ForeignKey("polls.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    answer_idx = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
