
import sys
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
import json

# Add backend directory to sys.path
backend_dir = Path("/home/einzlth/Projects/openSDLC/backend")
sys.path.append(str(backend_dir))

from app.db.models import Run, Step
from app.models.responses import RunSummary
from app.db import repository as repo

def check_data():
    db_path = backend_dir / "data" / "opensdlc.db"
    if not db_path.exists():
        print(f"DB not found at {db_path}")
        return

    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        db_runs = session.scalars(select(Run)).all()
        run_ids = [r.run_id for r in db_runs]
        step_counts = repo.count_steps_by_run(session, run_ids)

        for r in db_runs:
            try:
                summary = RunSummary(
                    run_id=r.run_id,
                    pipeline_name=r.pipeline_name,
                    status=r.status,
                    created_at=r.created_at,
                    finished_at=r.finished_at,
                    steps_completed=step_counts.get(str(r.run_id), 0),
                    error=r.error,
                )
                print(f"SUCCESS: {r.run_id}")
            except Exception as e:
                print(f"FAILURE: {r.run_id} - {str(e)}")
                # Detailed check
                print(f"  run_id: {type(r.run_id)} = {r.run_id}")
                print(f"  created_at: {type(r.created_at)} = {r.created_at}")
                print(f"  status: {type(r.status)} = {r.status}")

if __name__ == "__main__":
    check_data()
