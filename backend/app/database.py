from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_sqlite_schema(engine):
    """Automatically adds newly added columns to SQLite tables if upgrading an existing db."""
    try:
        with engine.connect() as conn:
            cur = conn.connection.cursor()

            # analysis_runs
            cols = [c[1] for c in cur.execute("PRAGMA table_info(analysis_runs)").fetchall()]
            if cols:
                if "started_at" not in cols:
                    cur.execute("ALTER TABLE analysis_runs ADD COLUMN started_at TIMESTAMP")
                if "completed_at" not in cols:
                    cur.execute("ALTER TABLE analysis_runs ADD COLUMN completed_at TIMESTAMP")
                if "model_version" not in cols:
                    cur.execute("ALTER TABLE analysis_runs ADD COLUMN model_version VARCHAR DEFAULT 'v1.0-offline'")

            # findings
            cols_f = [c[1] for c in cur.execute("PRAGMA table_info(findings)").fetchall()]
            if cols_f:
                if "dataset_version_id" not in cols_f:
                    cur.execute("ALTER TABLE findings ADD COLUMN dataset_version_id VARCHAR DEFAULT 'v1.0-offline'")
                if "rule_id" not in cols_f:
                    cur.execute("ALTER TABLE findings ADD COLUMN rule_id VARCHAR")
                if "nist_csf_category" not in cols_f:
                    cur.execute("ALTER TABLE findings ADD COLUMN nist_csf_category VARCHAR")
                if "mitre_attack_technique" not in cols_f:
                    cur.execute("ALTER TABLE findings ADD COLUMN mitre_attack_technique VARCHAR")

            # capability_scores
            cols_c = [c[1] for c in cur.execute("PRAGMA table_info(capability_scores)").fetchall()]
            if cols_c:
                if "baseline_json" not in cols_c:
                    cur.execute("ALTER TABLE capability_scores ADD COLUMN baseline_json TEXT")
                if "confidence" not in cols_c:
                    cur.execute("ALTER TABLE capability_scores ADD COLUMN confidence FLOAT DEFAULT 0.85")
                if "trend" not in cols_c:
                    cur.execute("ALTER TABLE capability_scores ADD COLUMN trend VARCHAR DEFAULT 'STABLE'")

            conn.connection.commit()
    except Exception as e:
        # Non-SQLite or fresh database
        pass


def init_db():
    import app.models  # ensure models registered
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_schema(engine)

