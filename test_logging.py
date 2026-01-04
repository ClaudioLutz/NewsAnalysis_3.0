from newsanalysis.utils.logging import setup_logging, get_logger
setup_logging()
logger = get_logger(__name__)
logger.info("test", model="gpt-4o-mini", enabled=True)
print("Success\!")