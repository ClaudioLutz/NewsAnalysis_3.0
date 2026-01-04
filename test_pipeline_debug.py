import asyncio
import sys
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from newsanalysis.core.config import Config, PipelineConfig
from newsanalysis.database.connection import DatabaseConnection, init_database
from newsanalysis.pipeline.orchestrator import PipelineOrchestrator
from newsanalysis.utils.logging import setup_logging

try:
    # Setup
    config = Config()
    setup_logging(log_level="DEBUG", log_format="json")

    print("Initializing database...")
    db = DatabaseConnection(config.db_path)

    print("Creating orchestrator...")
    pipeline_config = PipelineConfig(mode="full", limit=5)
    orchestrator = PipelineOrchestrator(
        config=config,
        db=db,
        pipeline_config=pipeline_config,
    )

    print("Running pipeline...")
    stats = asyncio.run(orchestrator.run())

    print(f"SUCCESS! Stats: {stats}")

except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
finally:
    if 'db' in locals():
        db.close()
