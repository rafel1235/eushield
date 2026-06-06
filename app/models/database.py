from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, JSON, create_engine
from sqlalchemy.orm import declarative_base, relationship
import uuid
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./eushield_mvp.db" 

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    projects = relationship("Project", back_populates="owner")

class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    domain_name = Column(String, index=True) 
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="projects")
    scans = relationship("Scan", back_populates="project")
    policies = relationship("Policy", back_populates="project")

class Scan(Base):
    __tablename__ = "scans"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"))
    risk_score = Column(Integer) 
    total_cookies = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    project = relationship("Project", back_populates="scans")
    trackers = relationship("ScanTracker", back_populates="scan")

class ScanTracker(Base):
    __tablename__ = "scan_trackers"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"))
    tracker_name = Column(String, index=True) 
    category = Column(String) 
    scan = relationship("Scan", back_populates="trackers")

class ConsentLog(Base):
    __tablename__ = "consent_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"))
    ip_hash = Column(String) 
    action = Column(String) 
    preferences = Column(JSON, nullable=True) 
    created_at = Column(DateTime, default=datetime.utcnow)

class Policy(Base):
    __tablename__ = "policies"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"))
    answers_json = Column(JSON) 
    html_content = Column(String) 
    version = Column(Integer, default=1)
    project = relationship("Project", back_populates="policies")

class DsarRequest(Base):
    __tablename__ = "dsar_requests"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"))
    user_email = Column(String) 
    request_type = Column(String) 
    status = Column(String, default="pending") 
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

from sqlalchemy.orm import sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)