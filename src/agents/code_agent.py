import os
import json
import logging
import re
from typing import Dict, Any

import click
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
    def __init__(self, config):
        self.config = config
        self.github = GitHubManager(
            token=config.github_token,
            repo_name=config.repo_name
        )
        self.llm = LLMClient()
        # Инициализация LLM через твой метод init
        if hasattr(self.llm, 'init'):
            try:
                # Пробуем без аргументов (если берет из env)
                self.llm.init()
            except TypeError:
                # Если требует api_key
                self.llm.init(api_key=config.llm_api_key)

        self.excluded_dirs = {".git", "venv", "__pycache__", "node_modules", ".idea"}

    def _get_project_context(self) -> str:
        """Собирает контекст существующих файлов."""
        context = []
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]
            for file in files:
                if file.endswith((".py", ".md")):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            context.append(f"FILE: {path}\n{f.read()}\n---\n")
                    except: continue
        return "\n".join(context)

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Извлекает JSON из ответа YandexGPT."""
        if not text:
            return {"files_to_create": [], "files_to_modify": []}
        try:
            match = re.search(r"(\{[\s\S]*\})", text)
            json_str = match.group(1) if match else text
            return json.loads(json_str.strip())
        except Exception as e:
            logger.error(f"Ошибка парсинга JSON: {e}. Сырой текст: {text}")
            return {"files_to_create": [], "files_to_modify": []}

def run(self, issue_number: int, pr_number: int = None):
        try:
            logger.info(f"=== [START] Code Agent | Issue #{issue_number} ===")

            # 1. Читаем Issue
            issue_data = self.github.get_issue(issue_number)
            title = issue_data.get("title", "No Title") if isinstance(issue_data, dict) else getattr(issue_data, "title", "No Title")
            body = issue_data.get("body", "") if isinstance(issue_data, dict) else getattr(issue_data, "body", "")

            # 2. Собираем контекст проекта
            context = self._get_project_context()

            # 3. Настраиваем промпт в зависимости от того, создаем мы или исправляем
            if pr_number:
                logger.info(f"Режим исправления для PR #{pr_number}")
                # Получаем текущий код и комментарии ревьюера
                diff = self.github.get_pr_diff(pr_number)
                # (Важно: добавь метод get_issue_comments в git_utils, если его нет)
                comments = self.github.get_issue(pr_number) 
                
                system_role = (
                    "Ты — Senior Python Developer. Твоя задача — ИСПРАВИТЬ ошибки в коде согласно замечаниям ревьюера.\n"
                    "Отвечай ТОЛЬКО в формате JSON."
                )
                prompt = (
                    f"Исправь ошибки в коде для задачи: {title}\n"
                    f"Замечания ревьюера: {comments}\n"
                    f"Текущие изменения (diff):\n{diff}\n"
                    f"Контекст проекта:\n{context}"
                )
            else:
                logger.info(f"Режим создания нового решения")
                system_role = (
                    "Ты — Senior Python Developer. \n"
                    "Весь программный код внутри JSON-полей должен быть представлен как одна строка, где все переносы строк заменены на символ \\n, а внутренние двойные кавычки экранированы.\n"
                    "Формат: {\"files_to_create\": [{\"path\": \"...\", \"content\": \"...\"}], \"files_to_modify\": []}"
                )
                prompt = (
                    f"Реши задачу: {title}\n"
                    f"Описание: {body}\n\n"
                    f"Контекст проекта:\n{context}"
                )

            logger.info("Запрос к YandexGPT за решением...")
            raw_response = self.llm.get_response(prompt, system_role=system_role)
            
            # 4. Применяем изменения
            changes = self._parse_json_response(raw_response)
            
            # Переключаемся на ветку (create_branch в PDF умеет переключаться на существующую)
            branch_name = f"fix/issue-{issue_number}"
            self.github.create_branch(branch_name)

            applied_any = False
            # ... далее твой код применения изменений (циклы for f in changes...)
            for f in changes.get("files_to_create", []):
                path = f["path"]
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "w", encoding="utf-8") as fd:
                    fd.write(f["content"])
                logger.info(f"Файл создан: {path}")
                applied_any = True

            for f in changes.get("files_to_modify", []):
                path = f["path"]
                if os.path.exists(path):
                    with open(path, "w", encoding="utf-8") as fd:
                        fd.write(f["content"])
                    logger.info(f"Файл обновлен: {path}")
                    applied_any = True

            if not applied_any:
                logger.warning("Изменения не были применены. Проверь ответ LLM.")

            # 5. Commit & Push (твой объединенный метод)
            commit_message = f"Fix #{issue_number}: {title}"
            logger.info(f"Коммит и пуш в ветку {branch_name}...")
            self.github.commit_and_push(branch_name, commit_message)

            # 6. Pull Request (позиционные аргументы)
            logger.info("Создание Pull Request...")
            pr_url = self.github.create_pull_request(
                f"Fix: {title}",                 # title
                f"Automated fix for #{issue_number}",  # body
                branch_name,                     # head
                "main"                           # base
            )
            
            logger.info(f"Прошло успешно! PR: {pr_url}")

        except Exception as e:
            logger.error(f"Критическая ошибка: {e}", exc_info=True)

@click.command()
@click.option("--issue-number", type=int, required=True)
def main(issue_number: int):
    agent = CodeAgent()
    agent.run(issue_number)

if __name__ == "__main__":
    main()