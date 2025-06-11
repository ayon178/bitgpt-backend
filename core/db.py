import mongoengine
from core.config import MONGO_URI

import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("pymongo").setLevel(logging.CRITICAL)


def connect_to_db():
    try:
        mongoengine.connect(db="tutor", host=MONGO_URI)
        client = mongoengine.get_connection()
        client.server_info()
        logging.info("Successfully connected to MongoDB!")
    except Exception as e:
        logging.error(f"Error connecting to MongoDB: {e}")