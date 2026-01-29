import os
import json
import logging
import re
from typing import List, Dict, Any, Optional

import click
from core.config import settings
from core.git_utils import GitHubManager
from core.llm_client import LLMClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

class CodeAgent:
    """
    Агент-разработчик, который читает Issue, анализирует контекст,
    генерирует код и создает Pull Request.
    """

    def __init__(self):
        self.github = GitHubManager(
            token=settings.github_token,
            repo_name=settings.repo_name
        )
        self.llm = LLMClient(api_key=settings.llm_api_key)
        self.excluded_dirs = {".git", "venv", "__pycache__", ".idea", ".vscode", "dist", "build"}

    def _get_project_context(self) -> str:
        """
        Сканирует проект и собирает содержимое файлов для контекста LLM.
        """
        logger.info("Сбор контекста проекта...")
        context = []
        for root, dirs, files in os.walk("."):
            # Исключаем ненужные директории
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]
            
            for file in files:
                if file.endswith((".py", ".md", ".yml", ".yaml", "Dockerfile", ".txt")):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                            context.append(f"--- FILE: {path} ---\n{content}\n")
                    except Exception as e:
                        logger.warning(f"Не удалось прочитать файл {path}: {e}")
        
        return "\n".join(context)

    def _parse_llm_json(self, raw_response: str) -> Dict[str, Any]:
        """
        Парсит JSON из ответа LLM, очищая его от Markdown-разметки.
        """
        try:
            # Используем более явное имя переменной regex_match
            regex_match = re.search(r"```json\s*([\s\S]*?)\s*```", raw_response)
            
            if regex_match:
                json_str = regex_match.group(1).strip()
            else:
                json_str = raw_response.strip()
                
            return json.loads(json_str)
        except (json.JSONDecodeError, AttributeError, Exception) as e:
            logging.error(f"Ошибка парсинга JSON: {e}. Ответ LLM: {raw_response}")
            raise ValueError("LLM вернула невалидный JSON формат.")

    def _apply_changes(self, changes: Dict[str, List[Dict[str, str]]]):
        """
        Физически записывает изменения на диск.
        """
        # Создание новых файлов
        for file_info in changes.get("files_to_create", []):
            path = file_info["path"]
            content = file_info["content"]
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Создан файл: {path}")

        # Модификация существующих
        for file_info in changes.get("files_to_modify", []):
            path = file_info["path"]
            content = file_info["content"]
            if os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"Обновлен файл: {path}")
            else:
                logger.warning(f"Файл {path} не найден для модификации, пропускаю.")

    def run(self, issue_number: int):
        """
        Основной цикл работы агента.
        """
        try:
            logger.info(f"=== Запуск Code Agent для Issue #{issue_number} ===")

            # Шаг 1: Получаем Issue
            issue = self.github.get_issue(issue_number)
            if isinstance(issue, dict):
                issue_body = issue.get("body") or ""
                issue_title = issue.get("title") or "No Title"
            else:
                issue_body = getattr(issue, "body", "") or ""
                issue_title = getattr(issue, "title", "Unknown")

            logger.info(f"Задача: {issue_title}")

            # Шаг 2: Собираем контекст
            project_context = self._get_project_context()

            # Шаг 3 & 4: Запрос к LLM
            system_prompt = (
                "Ты — Senior AI Developer. Тебе дана задача (Issue) и текущий код проекта.\n"
                "Твоя цель: предложить изменения в коде для решения задачи.\n"
                "Ответ должен быть СТРОГО в формате JSON:\n"
                "{\n"
                "  \"files_to_create\": [{\"path\": \"file_path\", \"content\": \"...\"}],\n"
                "  \"files_to_modify\": [{\"path\": \"file_path\", \"content\": \"...\"}]\n"
                "}\n"
                "Пиши только чистый код в content, без комментариев вне JSON."
            )
            
            user_prompt = (
                f"ISSUE TITLE: {issue_title}\n"
                f"ISSUE DESCRIPTION:\n{issue_body}\n\n"
                f"CURRENT PROJECT CODE:\n{project_context}"
            )

            logger.info("Запрос к LLM за решением...")
            raw_response = self.llm.generate(system_prompt, user_prompt)
            
            # Обработка JSON с ретраем (простая логика)
            try:
                changes = self._parse_llm_json(raw_response)
            except ValueError:
                logger.warning("Попытка повторного запроса (retry) из-за невалидного JSON...")
                raw_response = self.llm.generate(system_prompt, f"Твой предыдущий ответ был невалидным JSON. Повтори еще раз строго по формату. Задача: {issue_title}")
                changes = self._parse_llm_json(raw_response)

            # Шаг 5: Применение изменений
            branch_name = f"fix/issue-{issue_number}"
            self.github.create_branch(branch_name)
            self._apply_changes(changes)

            # Шаг 6: Git операции
            logger.info("Коммит и пуш изменений...")
            self.github.commit_all(f"Ref #{issue_number}: {issue_title}")
            #self.github.push(branch_name)
            
            pr_body = f"Автоматический Pull Request для решения задачи #{issue_number}.\n\n{issue_body}"
            pr_url = self.github.create_pull_request(
                title=f"Fix: {issue_title}",
                body=pr_body,
                head=branch_name,
                base="main"
            )
            
            logger.info(f"успешно! PR создан: {pr_url}")

        except Exception as e:
            logger.error(f"Ошибка в работе агента: {e}", exc_info=True)
            raise

@click.command()
@click.option("--issue-number", type=int, required=True, help="Номер Issue из GitHub")
def main(issue_number: int):
    agent = CodeAgent()
    agent.run(issue_number)

if __name__ == "__main__":
    main()