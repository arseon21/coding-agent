import os
import json
import logging
import re
from typing import Dict, Any

import click
# Используем объект config из core.config
from core.config import config
from core.git_utils import GitHubManager
from core.llm_client import LLMClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

class CodeAgent:
    """
    Агент, адаптированный под твою реализацию LLMClient и GitHubManager.
    """

    def __init__(self):
        # 1. GitHubManager инициализируется через токен из конфига
        self.github = GitHubManager(
            token=config.github_token,
            repo_name=config.repo_name
        )

        # 2. Инициализация твоего LLMClient (двухэтапная, как в твоем коде)
        self.llm = LLMClient()
        try:
            # Твой метод называется init() и он берет данные из env внутри себя
            self.llm.__init__() 
            logger.info("LLMClient успешно инициализирован методом .init()")
        except Exception as e:
            logger.error(f"Ошибка при вызове LLMClient.init(): {e}")
            raise

        self.excluded_dirs = {".git", "venv", "__pycache__", "node_modules", ".idea"}

    def _get_project_context(self) -> str:
        """Сбор контекста проекта (файлов) для LLM."""
        context = []
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]
            for file in files:
                if file.endswith((".py", ".md", "Dockerfile")):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            context.append(f"--- FILE: {path} ---\n{f.read()}\n")
                    except Exception:
                        continue
        return "\n".join(context)

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Безопасное извлечение JSON из ответа YandexGPT."""
        if not text:
            return {"files_to_create": [], "files_to_modify": []}
        try:
            # Ищем блок JSON в тексте
            match = re.search(r"(\{[\s\S]*\})", text)
            clean_text = match.group(1) if match else text
            return json.loads(clean_text.strip())
        except Exception as e:
            logger.error(f"Ошибка парсинга JSON. Ответ модели: {text}")
            return {"files_to_create": [], "files_to_modify": []}

    def run(self, issue_number: int):
        """Основной рабочий цикл агента."""
        try:
            logger.info(f"=== Запуск Code Agent для Issue #{issue_number} ===")

            # ШАГ 1: Получаем Issue (через твой GitHubManager)
            issue_data = self.github.get_issue(issue_number)
            if isinstance(issue_data, dict):
                title = issue_data.get("title", "No Title")
                body = issue_data.get("body", "")
            else:
                title = getattr(issue_data, "title", "No Title")
                body = getattr(issue_data, "body", "")

            logger.info(f"Задача принята: {title}")

            # ШАГ 2: Собираем текущий код
            context = self._get_project_context()

            # ШАГ 3: Запрос к LLM (через твой метод get_response)
            system_role = (
                "Ты — Senior Python Developer. Отвечай ТОЛЬКО в формате JSON.\n"
                "Структура: {\"files_to_create\": [], \"files_to_modify\": []}"
            )
            prompt = (
                f"Реши задачу: {title}\nОписание: {body}\n\n"
                f"Контекст проекта:\n{context}\n\n"
                "Верни JSON с изменениями."
            )

            logger.info("Отправка запроса в YandexGPT...")
            # Вызов твоего метода: get_response(prompt, system_role)
            raw_response = self.llm.get_response(prompt, system_role=system_role)

            # ШАГ 4: Парсинг ответа
            changes = self._parse_json_response(raw_response)

            # ШАГ 5: Применение изменений в локальные файлы
            branch_name = f"fix/issue-{issue_number}"
            self.github.create_branch(branch_name)

            for f in changes.get("files_to_create", []):
                path = f["path"]
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "w", encoding="utf-8") as fd:
                    fd.write(f["content"])
                logger.info(f"Создан файл: {path}")

            for f in changes.get("files_to_modify", []):
                path = f["path"]
                if os.path.exists(path):
                    with open(path, "w", encoding="utf-8") as fd:
                        fd.write(f["content"])
                    logger.info(f"Обновлен файл: {path}")

            # ШАГ 6: Git commit, push и PR
            self.github.commit_all(f"Fix #{issue_number}: {title}")
            self.github.push(branch_name)
            
            pr_url = self.github.create_pull_request(
                title=f"Fix: {title}",
                body=f"Автоматический Pull Request для задачи #{issue_number}",
                head=branch_name,
                base="main"
            )
            logger.info(f"Успех! Pull Request создан: {pr_url}")

        except Exception as e:
            logger.error(f"Критическая ошибка в CodeAgent: {e}", exc_info=True)

@click.command()
@click.option("--issue-number", type=int, required=True, help="Номер Issue из GitHub")
def main(issue_number: int):
    agent = CodeAgent()
    agent.run(issue_number)

if __name__ == "__main__":
    main()