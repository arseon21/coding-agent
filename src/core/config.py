import os
import logging
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Исправляем путь к .env, чтобы он всегда находился относительно этого файла
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Настройка базового логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# ИСПРАВЛЕНО: используем name вместо name
logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class AppConfig:
    github_token: str
    llm_api_key: str
    repo_name: str
    log_level: str = "INFO"

    @classmethod
    def load(cls) -> "AppConfig":
        logger.info("Loading configuration...")

        github_token = os.getenv("GITHUB_TOKEN")
        llm_api_key = os.getenv("YANDEX_API_KEY")
        repo_name = os.getenv("REPO_NAME")
        log_level = os.getenv("LOG_LEVEL", "INFO")

        missing_vars = []
        if not github_token: missing_vars.append("GITHUB_TOKEN")
        if not llm_api_key: missing_vars.append("YANDEX_API_KEY")
        if not repo_name: missing_vars.append("REPO_NAME")

        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info("Configuration loaded successfully.")
        
        return cls(
            github_token=github_token, 
            llm_api_key=llm_api_key,   
            repo_name=repo_name,       
            log_level=log_level
        )

# Глобальный объект конфигурации
try:
    config = AppConfig.load()
except ValueError as e:
    logger.critical(f"Failed to load config: {e}")
    # Важно: для CLI инструмента лучше бросать исключение дальше, 
    # чтобы процесс завершился с ненулевым кодом выхода
    raise