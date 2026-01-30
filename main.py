import argparse
import logging
import os
import sys

# Добавляем src в путь, чтобы видеть пакеты (core, agents)
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from core.config import AppConfig, config
from agents.code_agent import CodeAgent
from agents.reviewer_agent import ReviewerAgent

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="AI Coding Agent Entry Point")
    subparsers = parser.add_subparsers(dest='command', help='Available commands', required=True)

    # === Команда solve (Code Agent) ===
    solve_parser = subparsers.add_parser('solve', help='Solve an issue')
    solve_parser.add_argument('--issue-id', type=int, required=True, help='Issue ID to solve')

    # === Команда review (Reviewer Agent) ===
    review_parser = subparsers.add_parser('review', help='Review a Pull Request')
    review_parser.add_argument('--pr-number', type=int, required=True, help='PR Number to review')
    
    # Парсим аргументы
    args = parser.parse_args()

    # Загружаем конфиг
    try:
        # В PDF методе load() есть логирование, оно сработает здесь
        AppConfig.load()
    except Exception as e:
        logger.critical(f"Config load failed: {e}")
        sys.exit(1)

    # Логика выбора агента
    if args.command == 'solve':
        logger.info(f"Starting Code Agent for Issue #{args.issue_id}")
        try:
            # Передаем глобальный config, как требует init CodeAgent в PDF
            agent = CodeAgent(config)
            agent.run(args.issue_id)
        except Exception as e:
            logger.error(f"Code Agent failed: {e}", exc_info=True)
            sys.exit(1)

    elif args.command == 'review':
        logger.info(f"Starting Reviewer Agent for PR #{args.pr_number}")
        try:
            # ReviewerAgent в PDF инициализирует конфиг внутри себя, аргументы не нужны
            agent = ReviewerAgent(config)
            agent.run_review(args.pr_number)
        except Exception as e:
            logger.error(f"Reviewer Agent failed: {e}", exc_info=True)
            sys.exit(1)

if __name__ == "__main__":
    main()