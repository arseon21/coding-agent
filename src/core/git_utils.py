import os
import logging
from typing import Optional, Dict, Tuple, Union
from pathlib import Path

# Сторонние библиотеки
from git import Repo, GitCommandError, InvalidGitRepositoryError  # type: ignore
from github import Github, GithubException, Auth
from github.Repository import Repository
from github.PullRequest import PullRequest

# Настройка логирования
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class GitHubManager:
    """
    Класс для управления взаимодействием с GitHub API и локальным Git-репозиторием.
    Объединяет возможности PyGithub (Remote API) и GitPython (Local Operations).
    """

    def __init__(self, token: str, repo_name: str, local_path: str = "."):
        """
        Инициализация менеджера.

        Args:
            token (str): Personal Access Token (PAT) для GitHub.
            repo_name (str): Имя репозитория в формате "owner/repo".
            local_path (str): Путь к локальной директории проекта. По умолчанию текущая папка.
        """
        self.token = token
        self.repo_name = repo_name
        self.local_path = Path(local_path).resolve()

        # Инициализация клиента GitHub API
        try:
            auth = Auth.Token(token)
            self.github_client = Github(auth=auth)
            self.remote_repo: Repository = self.github_client.get_repo(repo_name)
            logger.info(f"Успешное подключение к удаленному репозиторию: {repo_name}")
        except GithubException as e:
            logger.error(f"Ошибка подключения к GitHub API: {e}")
            raise

        # Инициализация локального Git репозитория
        try:
            self.local_repo = Repo(self.local_path)
            logger.info(f"Локальный репозиторий инициализирован в: {self.local_path}")
            self._configure_git_user()
        except InvalidGitRepositoryError:
            logger.error(f"Директория {self.local_path} не является Git-репозиторием.")
            raise
        except Exception as e:
            logger.error(f"Ошибка инициализации локального Git: {e}")
            raise

    def _configure_git_user(self) -> None:
        """Настраивает имя пользователя и email для коммитов агента."""
        with self.local_repo.config_writer() as git_config:
            if not git_config.has_option("user", "email"):
                git_config.set_value("user", "email", "agent@ai-bot.com")
            if not git_config.has_option("user", "name"):
                git_config.set_value("user", "name", "AI Coding Agent")

    def _update_remote_url_with_token(self) -> None:
        """
        Обновляет URL origin, добавляя токен для HTTPS аутентификации.
        Необходимо для выполнения git push из контейнера без SSH ключей.
        """
        origin = self.local_repo.remote(name="origin")
        url = origin.url
        # Если это HTTPS URL и токена еще нет
        if url.startswith("https://") and "@" not in url:
            new_url = url.replace("https://", f"https://{self.token}@")
            origin.set_url(new_url)
            logger.debug("Remote origin URL обновлен с использованием токена аутентификации.")

    def get_issue(self, issue_number: int) -> Dict[str, str]:
        """
        Получает информацию об Issue по его номеру.

        Args:
            issue_number (int): Номер Issue.

        Returns:
            Dict[str, str]: Словарь с ключами 'title', 'body', 'url'.
        """
        try:
            issue = self.remote_repo.get_issue(number=issue_number)
            logger.info(f"Получен Issue #{issue_number}: {issue.title}")
            return {
                "title": issue.title,
                "body": issue.body or "",
                "url": issue.html_url
            }
        except GithubException as e:
            logger.error(f"Не удалось получить Issue #{issue_number}: {e}")
            raise

    def create_branch(self, branch_name: str) -> None:
        """
        Создает новую ветку в локальном репозитории и переключается на неё.

        Args:
        branch_name (str): Название новой ветки.
        """
        try:
            current = self.local_repo.active_branch
            logger.info(f"Текущая ветка: {current.name}")

            # Проверяем, существует ли ветка
            if branch_name in self.local_repo.heads:
                logger.warning(f"Ветка {branch_name} уже существует. Переключаемся на неё.")
                new_branch = self.local_repo.heads[branch_name]
                new_branch.checkout()
            else:
                # Создаем ветку от текущего HEAD
                new_branch = self.local_repo.create_head(branch_name)
                new_branch.checkout()
                logger.info(f"Создана и активирована ветка: {branch_name}")
        except GitCommandError as e:
            logger.error(f"Git ошибка при создании ветки {branch_name}: {e}")
            raise

    def commit_and_push(self, branch_name: str, commit_message: str) -> None:
        """
        Индексирует все изменения, создает коммит и пушит в удаленный репозиторий.

        Args:
            branch_name (str): Имя ветки, в которую пушим.
            commit_message (str): Текст коммита.
        """
        try:
            if not self.local_repo.is_dirty(untracked_files=True):
                logger.warning("Нет изменений для коммита.")
                return

            # git add .
            self.local_repo.git.add(A=True)
            
            # git commit -m "..."
            self.local_repo.index.commit(commit_message)
            logger.info(f"Сделан коммит: {commit_message}")

            # Обновляем URL для доступа по токену
            self._update_remote_url_with_token()

            # git push origin <branch_name>
            origin = self.local_repo.remote(name="origin")
            origin.push(refspec=f"{branch_name}:{branch_name}")
            logger.info(f"Изменения отправлены в remote origin/{branch_name}")

        except GitCommandError as e:
            logger.error(f"Ошибка при выполнении git commit/push: {e}")
            raise

    def create_pull_request(
        self, title: str, body: str, head_branch: str, base_branch: str = "main"
    ) -> Optional[int]:
        """
        Создает Pull Request через GitHub API.

        Args:
            title (str): Заголовок PR.
            body (str): Описание PR.
            head_branch (str): Ветка с изменениями (source).
            base_branch (str): Целевая ветка (target).

        Returns:
            Optional[int]: Номер созданного PR или None в случае ошибки.
        """
        try:
            pr = self.remote_repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch
            )
            logger.info(f"PR успешно создан: {pr.html_url} (№{pr.number})")
            return pr.number
        except GithubException as e:
            logger.error(f"Ошибка при создании PR: {e}")
            # Часто падает, если PR уже существует, полезно залогировать детали
            if e.status == 422:
                logger.error("Вероятно, PR для этой ветки уже существует.")
            raise

    def post_comment_to_pr(self, pr_number: int, comment: str) -> None:
        """
        Оставляет комментарий в Pull Request (фактически в Issue, так как PR это расширенный Issue).

        Args:
            pr_number (int): Номер PR.
            comment (str): Текст комментария.
        """
        try:
            # В GitHub API комментарии к PR часто обрабатываются как комментарии к Issue
            issue = self.remote_repo.get_issue(number=pr_number)
            issue.create_comment(comment)
            logger.info(f"Комментарий добавлен к PR #{pr_number}")
        except GithubException as e:
            logger.error(f"Ошибка при добавлении комментария к PR #{pr_number}: {e}")
            raise