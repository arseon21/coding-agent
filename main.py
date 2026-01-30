import sys
import argparse
import os

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    # Команда solve
    solve_parser = subparsers.add_parser('solve')
    solve_parser.add_argument('--issue-id', type=str)

    # Команда review
    review_parser = subparsers.add_parser('review')
    review_parser.add_argument('--pr-id', type=str)
    review_parser.add_argument('--test-log', type=str)

    args = parser.parse_args()

    if args.command == 'solve':
        print(f"[MOCK AGENT] I am solving issue #{args.issue_id}")
        print(f"Key present: {'Yes' if os.environ.get('LLM_API_KEY') else 'No'}")
        # Тут в будущем будет git commit & git push
        
    elif args.command == 'review':
        print(f"🕵️ [MOCK REVIEWER] Checking PR #{args.pr_id}")
        if args.test_log:
            try:
                with open(args.test_log, 'r') as f:
                    print("Test Logs Content:\n", f.read())
            except FileNotFoundError:
                print("Test log file not found!")
    else:
        print("Unknown command")

if __name__ == "__main__":
    main()