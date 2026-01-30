import argparse
import logging
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from core.config import AppConfig, config
from agents.code_agent import CodeAgent
from agents.reviewer_agent import ReviewerAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="AI Coding Agent Entry Point")
    subparsers = parser.add_subparsers(dest='command', help='Available commands', required=True)

    solve_parser = subparsers.add_parser('solve', help='Решение для issue')
    solve_parser.add_argument('--issue-id', type=int, required=True, help='Issue ID to solve')

    review_parser = subparsers.add_parser('review', help='Review Pull Request')
    review_parser.add_argument('--pr-number', type=int, required=True, help='PR Number to review')
    
    args = parser.parse_args()

    try:
        AppConfig.load()
    except Exception as e:
        logger.critical(f"Config загрузка провалилась {e}")
        sys.exit(1)

    if args.command == 'solve':
        logger.info(f"Запуск Code Agent для Issue #{args.issue_id}")
        try:
            agent = CodeAgent(config)
            agent.run(args.issue_id)
        except Exception as e:
            logger.error(f"Code Agent остановился {e}", exc_info=True)
            sys.exit(1)

    elif args.command == 'review':
        logger.info(f"Старт Reviewer Agent для PR #{args.pr_number}")
        try:
            agent = ReviewerAgent(config)
            agent.run_review(args.pr_number)
        except Exception as e:
            logger.error(f"Reviewer Agent остановился {e}", exc_info=True)
            sys.exit(1)

if __name__ == "__main__":
    main()