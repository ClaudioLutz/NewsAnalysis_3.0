from newsanalysis.utils.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

try:
    logger.info("test_message", model="gpt-4o-mini", enabled=True)
    print("SUCCESS: Logging with keyword arguments works!")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
