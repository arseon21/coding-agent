import argparse
import logging
import sys
from src.agents.code_agent import CodeAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.core.config import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="AI SDLC Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Команды агентов")

    # Команда для Code Agent
    code_parser = subparsers.add_parser("code-agent")
    code_parser.add_argument("--issue-number", type=int, help="ID задачи для реализации")
    code_parser.add_argument("--pr-number", type=int, help="ID PR для исправления ошибок по ревью")

    # Команда для Reviewer Agent
    review_parser = subparsers.add_parser("reviewer-agent")
    review_parser.add_argument("--pr-number", type=int, required=True, help="ID PR для ревью")

    args = parser.parse_args()

    try:
        if args.command == "code-agent":
            agent = CodeAgent(config)
            if args.issue_number:
                logger.info(f"Начинаю работу над Issue #{args.issue_number}")
                agent.run(args.issue_number)
            elif args.pr_number:
                logger.info(f"Исправляю ошибки в PR #{args.pr_number} на основе ревью")
                agent.fix_pr(args.pr_number)
        
        elif args.command == "reviewer-agent":
            reviewer = ReviewerAgent(config)
            logger.info(f"Запускаю ревью PR #{args.pr_number}")
            reviewer.run_review(args.pr_number)
            
        else:
            parser.print_help()

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()