import sys
import os
from pathlib import Path

# Добавляем путь к src в sys.path, чтобы Python видел модуль core
current_dir = Path(__file__).resolve().parent
src_path = current_dir.parent
if str(src_path) not in sys.path:
    sys.path.append(str(src_path))

# Импортируем готовый объект конфигурации и менеджер
from core.config import config
from core.git_utils import GitHubManager

def test_workflow():
    print("--- Инициализация ---")
    
    # ПЕРЕДАЕМ ДАННЫЕ ИЗ CONFIG
    try:
        manager = GitHubManager(
            token=config.github_token, 
            repo_name=config.repo_name,
            local_path="." 
        )
        print(f"Успешное подключение к репозиторию: {config.repo_name}")
    except Exception as e:
        print(f"Ошибка инициализации менеджера: {e}")
        return

    # 3. Чтение Issue (проверьте, что в репо есть Issue #1)
    try:
        issue_data = manager.get_issue(1)
        print(f"Issue #1 прочитан: {issue_data['title']}")
    except Exception as e:
        print(f"Инфо: Не удалось прочитать Issue #1: {e}")

    # 4. Создание ветки
    branch_name = "feature/test-agent-git-utils"
    print(f"\n--- Создание ветки {branch_name} ---")
    manager.create_branch(branch_name)

    # 5. Имитация изменения кода
    with open("agent_test.log", "a") as f:
        f.write("\nTest commit by AI Agent Manager")
    
    # 6. Коммит и Пуш
    print("\n--- Commit & Push ---")
    manager.commit_and_push(branch_name, "chore: test git utils logic")

    # 7. Создание PR
    print("\n--- Создание PR ---")
    try:
        pr_number = manager.create_pull_request(
            title="Test PR from Agent",
            body="Checking GitHubManager functionality.",
            head_branch=branch_name,
            base_branch="main" 
        )
        if pr_number:
            manager.post_comment_to_pr(pr_number, "Блок GitUtils работает корректно.")
            print(f"Тест завершен успешно! PR №{pr_number} создан.")
    except Exception as e:
        print(f"Ошибка PR: {e}")

if __name__ == "__main__":
    test_workflow()