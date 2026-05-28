from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, JSON, create_engine
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

# URL di connessione a PostgreSQL (Per ora usiamo SQLite per testare subito senza configurare server)
# Quando andrai live su OVH/Hetzner, cambierai solo questa stringa!
SQLALCHEMY_DATABASE_URL = "sqlite:///./eushield_mvp.db" 

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()

# ==========================================
# 1. UTENTI & PROGETTI (Punto 2, 3 e 10)
# ==========================================
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    projects = relationship("Project", back_populates="owner")

class Project(Base):
    __tablename__ = "projects"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    domain = Column(String, index=True) # es. mioshop.it
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User", back_populates="projects")
    scans = relationship("Scan", back_populates="project")
    policies = relationship("Policy", back_populates="project")

# ==========================================
# 2. SCANSIONI E TRACKER (Punto 4, 5, 6 e "Classifiche Europee")
# ==========================================
class Scan(Base):
    __tablename__ = "scans"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    risk_score = Column(Integer) # es. 62
    total_cookies = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="scans")
    trackers = relationship("ScanTracker", back_populates="scan")

class ScanTracker(Base):
    """Questa è la tabella 'Miniera d'oro' per le tue statistiche e classifiche"""
    __tablename__ = "scan_trackers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"))
    tracker_name = Column(String, index=True) # es. "Meta Pixel", "Google Analytics"
    category = Column(String) # es. "Marketing", "Analytics", "High Risk" (Punto 6)
    
    scan = relationship("Scan", back_populates="trackers")

# ==========================================
# 3. CONSENT LOGS - Il vero scudo GDPR (Punto 7 e 11)
# ==========================================
class ConsentLog(Base):
    __tablename__ = "consent_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    ip_hash = Column(String) # IP anonimizzato per legge
    action = Column(String) # "accepted", "rejected", "customized"
    preferences = Column(JSON, nullable=True) # es. {"analytics": true, "marketing": false}
    created_at = Column(DateTime, default=datetime.utcnow)

# ==========================================
# 4. PRIVACY POLICY E DSAR (Punto 8 e 9)
# ==========================================
class Policy(Base):
    __tablename__ = "policies"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    answers_json = Column(JSON) # Le risposte al Wizard
    html_content = Column(String) # Il testo legale generato
    version = Column(Integer, default=1)
    
    project = relationship("Project", back_populates="policies")

class DsarRequest(Base):
    __tablename__ = "dsar_requests"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    user_email = Column(String) # L'email del visitatore che fa la richiesta
    request_type = Column(String) # access, delete, rectify
    status = Column(String, default="pending") # pending, resolved
    created_at = Column(DateTime, default=datetime.utcnow)

# Crea fisicamente le tabelle nel database
Base.metadata.create_all(bind=engine)

from sqlalchemy.orm import sessionmaker

# Creiamo la fabbrica delle sessioni per parlare con il DB
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)