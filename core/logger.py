import logging
import os

# Define the logging level and format
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# Create a logger object
logger = logging.getLogger(__name__)

# Create a file handler for logging
log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

file_handler = logging.FileHandler(f"{log_directory}/app.log")
file_handler.setLevel(logging.ERROR)

# Create a logging format for the file handler
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s')
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)
