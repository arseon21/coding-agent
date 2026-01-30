import argparse
import logging
import re
from typing import Optional

from core.config import config
from core.git_utils import GitHubManager
from core.llm_client import LLMClient

logger = logging.getLogger(__name__)

class ReviewerAgent:
    def __init__(self,config):
        self.config = config
        self.gh_manager = GitHubManager(
            token=config.github_token,
            repo_name=config.repo_name
        )
        self.llm = LLMClient()

    def _extract_issue_number(self, pr_body: str) -> Optional[int]:
        """Пытается найти номер Issue в описании PR (например, 'Fixes #12')."""
        match = re.search(r'#(\d+)', pr_body)
        return int(match.group(1)) if match else None

    def run_review(self, pr_number: int, issue_number: Optional[int] = None):
        """Основной цикл работы ревьюера."""
        try:
            logger.info(f"Начало ревью для PR #{pr_number}")
            
            # Шаг 1: Получаем данные PR
            pr = self.gh_manager.get_pull_request(pr_number)
            diff = self.gh_manager.get_pr_diff(pr_number)
            
            if len(diff) > 20000: # Лимит для LLM (примерный)
                logger.warning("Diff слишком большой для анализа.")
                self.gh_manager.post_comment_to_pr(pr_number, "⚠️ Diff is too large for automated AI review.")
                return

            # Шаг 2: Получаем Issue
            target_issue_id = issue_number or self._extract_issue_number(pr.body or "")
            issue_text = "Описание задачи отсутствует."
            if target_issue_id:
                issue_data = self.gh_manager.get_issue(target_issue_id)
                issue_text = f"Title: {issue_data['title']}\nBody: {issue_data['body']}"

            # Шаг 3: Формируем промпт для LLM
            system_prompt = "Ты — Senior Code Reviewer. Ты должен провести тщательный анализ кода."
            prompt = f"""
Проверь Pull Request на соответствие задаче.

ЗАДАЧА (ISSUE):
{issue_text}

ИЗМЕНЕНИЯ (DIFF):
{diff}

КРИТЕРИИ ПРОВЕРКИ:
1. Соответствует ли код задаче?
2. Нет ли в коде явных багов или проблем с безопасностью?
3. Соответствует ли код стилю Python (Type hints, логирование, именование)?

ВЕРНИ ОТЧЕТ В ФОРМАТЕ:
### Отчет ревьюера
[Твой анализ]

Вердикт: APPROVE или REQUEST_CHANGES
"""

            # Запрос к LLM
            review_report = self.llm.get_response(prompt, system_prompt)

            # Шаг 4: Публикация вердикта
            self.gh_manager.post_comment_to_pr(pr_number, review_report)
            
            # Логика изменения статуса PR (Review Verdict)
            if "REQUEST_CHANGES" in review_report:
                logger.warning(f"PR #{pr_number} отклонен ревьюером.")
                # Здесь можно добавить вызов API для блокировки PR, если нужно
            else:
                logger.info(f"PR #{pr_number} одобрен.")

        except Exception as e:
            logger.error(f"Критическая ошибка при ревью PR #{pr_number}: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description="AI Reviewer Agent")
    parser.add_argument("--pr-number", type=int, required=True, help="Номер Pull Request")
    parser.add_argument("--issue-number", type=int, help="Номер Issue (опционально)")
    
    args = parser.parse_args()
    
    agent = ReviewerAgent()
    agent.run_review(args.pr_number, args.issue_number)

if __name__ == "__main__":
    main()