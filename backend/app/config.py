import os

from dotenv import load_dotenv


load_dotenv()


class Settings:

    APP_NAME = "AI Power Grid Fault Localization"

    VERSION = "1.0.0"

    DATABASE_URL = os.getenv("DATABASE_URL")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    HOST = "0.0.0.0"

    PORT = 8000

    DEBUG = True


settings = Settings()