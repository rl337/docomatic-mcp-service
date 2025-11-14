"""Export service for exporting documents to GitHub as Markdown files."""

import json
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from github import Github, GithubException
from sqlalchemy.orm import Session

from docomatic.exceptions import DatabaseError, NotFoundError, ValidationError
from docomatic.models.document import Document
from docomatic.models.section import Section
from docomatic.services.document_service import DocumentService
from docomatic.services.section_service import SectionService


class ExportFormat(str, Enum):
    """Export format options."""

    SINGLE_FILE = "single"
    MULTI_FILE = "multi"


@dataclass
class ExportConfig:
    """Configuration for document export."""

    format: ExportFormat = ExportFormat.SINGLE_FILE
    file_naming: str = "kebab-case"  # kebab-case, snake_case, or preserve
    directory_structure: str = "flat"  # flat or hierarchical
    include_metadata: bool = True
    convert_internal_links: bool = True
    preserve_external_links: bool = True
    base_path: str = "docs"  # Base directory in repository
    branch: Optional[str] = None  # Optional branch name (creates if doesn't exist)


class GitHubExportError(Exception):
    """Base exception for GitHub export errors."""

    pass


class GitHubAuthenticationError(GitHubExportError):
    """Raised when GitHub authentication fails."""

    pass


class GitHubAPIError(GitHubExportError):
    """Raised when GitHub API operations fail."""

    pass


class ExportService:
    """Service for exporting documents to GitHub as Markdown files."""

    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds

    def __init__(self, session: Session, github_token: str):
        """
        Initialize export service.

        Args:
            session: Database session
            github_token: GitHub personal access token or OAuth token
        """
        self.session = session
        self.github = Github(github_token)
        self.document_service = DocumentService(session)
        self.section_service = SectionService(session)

    def export_document(
        self,
        document_id: str,
        repo_owner: str,
        repo_name: str,
        config: Optional[ExportConfig] = None,
    ) -> dict[str, Any]:
        """
        Export a document to GitHub as Markdown file(s).

        Args:
            document_id: Document ID to export
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            config: Optional export configuration

        Returns:
            Dictionary with export results:
            - status: "success" or "error"
            - files_created: List of file paths created
            - commit_sha: Commit SHA (if created)
            - message: Status message

        Raises:
            NotFoundError: If document is not found
            ValidationError: If parameters are invalid
            GitHubAuthenticationError: If GitHub authentication fails
            GitHubAPIError: If GitHub API operations fail
        """
        if not document_id or not isinstance(document_id, str):
            raise ValidationError("Document ID must be a non-empty string", "document_id")
        if not repo_owner or not isinstance(repo_owner, str):
            raise ValidationError("Repository owner must be a non-empty string", "repo_owner")
        if not repo_name or not isinstance(repo_name, str):
            raise ValidationError("Repository name must be a non-empty string", "repo_name")

        config = config or ExportConfig()

        try:
            # Get document with sections
            document = self.document_service.get_document(
                document_id, include_sections=True, include_links=True
            )

            # Get repository
            repo = self._get_repository(repo_owner, repo_name)

            # Handle branch if specified
            if config.branch:
                self._ensure_branch(repo, config.branch)

            # Export based on format
            if config.format == ExportFormat.SINGLE_FILE:
                result = self._export_single_file(document, repo, config)
            else:
                result = self._export_multi_file(document, repo, config)

            return result

        except (NotFoundError, ValidationError, GitHubAuthenticationError, GitHubAPIError):
            raise
        except Exception as e:
            raise GitHubAPIError(f"Failed to export document: {str(e)}") from e

    def _export_single_file(
        self, document: Document, repo: Any, config: ExportConfig
    ) -> dict[str, Any]:
        """Export document as a single Markdown file."""
        # Generate file path
        filename = self._generate_filename(document.title, config.file_naming)
        file_path = f"{config.base_path}/{filename}.md"

        # Convert document to Markdown
        markdown_content = self._document_to_markdown(document, config, single_file=True)

        # Create or update file
        commit_message = f"Export document: {document.title}"
        commit_sha = self._create_or_update_file(
            repo, file_path, markdown_content, commit_message, config.branch
        )

        return {
            "status": "success",
            "files_created": [file_path],
            "commit_sha": commit_sha,
            "message": f"Exported document '{document.title}' as single file: {file_path}",
        }

    def _export_multi_file(
        self, document: Document, repo: Any, config: ExportConfig
    ) -> dict[str, Any]:
        """Export document as multiple files (one per top-level section)."""
        files_created = []
        commit_messages = []

        # Get top-level sections
        top_level_sections = [
            s for s in document.sections if s.parent_section_id is None
        ]
        top_level_sections.sort(key=lambda s: s.order_index)

        if not top_level_sections:
            # No sections, create a single file with just the document title
            filename = self._generate_filename(document.title, config.file_naming)
            file_path = f"{config.base_path}/{filename}.md"
            markdown_content = f"# {document.title}\n\n"
            if config.include_metadata and document.meta:
                markdown_content += self._metadata_to_frontmatter(document.meta)
            commit_message = f"Export document: {document.title}"
            commit_sha = self._create_or_update_file(
                repo, file_path, markdown_content, commit_message, config.branch
            )
            return {
                "status": "success",
                "files_created": [file_path],
                "commit_sha": commit_sha,
                "message": f"Exported document '{document.title}' (no sections) as: {file_path}",
            }

        # Export each top-level section as a separate file
        for section in top_level_sections:
            # Generate file path
            if config.directory_structure == "hierarchical":
                # Use document title as base directory
                doc_dir = self._sanitize_path(document.title, config.file_naming)
                filename = self._generate_filename(section.heading, config.file_naming)
                file_path = f"{config.base_path}/{doc_dir}/{filename}.md"
            else:
                # Flat structure
                filename = self._generate_filename(section.heading, config.file_naming)
                file_path = f"{config.base_path}/{filename}.md"

            # Convert section to Markdown (including nested sections)
            markdown_content = self._section_to_markdown(
                section, config, include_children=True, is_root=True
            )

            # Add document metadata if configured
            if config.include_metadata and document.meta:
                frontmatter = self._metadata_to_frontmatter(document.meta)
                markdown_content = frontmatter + markdown_content

            # Create or update file
            commit_message = f"Export section: {section.heading}"
            commit_sha = self._create_or_update_file(
                repo, file_path, markdown_content, commit_message, config.branch
            )
            files_created.append(file_path)
            commit_messages.append(commit_message)

        return {
            "status": "success",
            "files_created": files_created,
            "commit_sha": commit_sha,  # Last commit SHA
            "message": f"Exported document '{document.title}' as {len(files_created)} files",
        }

    def _document_to_markdown(
        self, document: Document, config: ExportConfig, single_file: bool = True
    ) -> str:
        """Convert document to Markdown format."""
        markdown = ""

        # Add frontmatter if configured
        if config.include_metadata and document.meta:
            markdown += self._metadata_to_frontmatter(document.meta)

        # Add document title
        markdown += f"# {document.title}\n\n"

        # Add sections
        top_level_sections = [
            s for s in document.sections if s.parent_section_id is None
        ]
        top_level_sections.sort(key=lambda s: s.order_index)

        for section in top_level_sections:
            markdown += self._section_to_markdown(
                section, config, include_children=True, is_root=False
            )
            markdown += "\n"

        return markdown

    def _section_to_markdown(
        self,
        section: Section,
        config: ExportConfig,
        include_children: bool = True,
        is_root: bool = False,
        level: int = 1,
    ) -> str:
        """Convert section to Markdown format."""
        markdown = ""

        # Determine heading level
        heading_level = level if not is_root else 1
        heading_prefix = "#" * (heading_level + 1)  # +1 because document title is h1

        # Add section heading
        markdown += f"{heading_prefix} {section.heading}\n\n"

        # Add section body
        body = section.body
        if config.convert_internal_links:
            body = self._convert_internal_links(body, config)
        markdown += f"{body}\n\n"

        # Add child sections if configured
        # Note: child_sections might be empty list if no children, or None if not loaded
        if include_children and hasattr(section, "child_sections") and section.child_sections:
            child_sections = sorted(section.child_sections, key=lambda s: s.order_index)
            for child in child_sections:
                markdown += self._section_to_markdown(
                    child, config, include_children=True, is_root=False, level=level + 1
                )

        return markdown

    def _convert_internal_links(self, content: str, config: ExportConfig) -> str:
        """
        Convert internal links in content.

        Internal links might reference sections or documents.
        For now, we preserve them as-is or convert to relative paths.
        """
        # This is a placeholder - actual implementation would parse Markdown links
        # and convert internal references to appropriate paths
        # For now, we just return the content as-is
        return content

    def _metadata_to_frontmatter(self, metadata: dict[str, Any]) -> str:
        """Convert metadata dictionary to YAML frontmatter."""
        frontmatter = "---\n"
        for key, value in metadata.items():
            if isinstance(value, (list, dict)):
                frontmatter += f"{key}: {json.dumps(value)}\n"
            elif isinstance(value, str):
                # Escape special characters
                escaped_value = value.replace('"', '\\"')
                frontmatter += f'{key}: "{escaped_value}"\n'
            else:
                frontmatter += f"{key}: {value}\n"
        frontmatter += "---\n\n"
        return frontmatter

    def _generate_filename(self, title: str, naming: str) -> str:
        """Generate filename from title based on naming convention."""
        if naming == "preserve":
            return self._sanitize_path(title)
        elif naming == "kebab-case":
            return self._to_kebab_case(title)
        elif naming == "snake_case":
            return self._to_snake_case(title)
        else:
            return self._to_kebab_case(title)  # Default

    def _sanitize_path(self, path: str, naming: str = "kebab-case") -> str:
        """Sanitize path for filesystem use."""
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"|?*]', "", path)
        sanitized = sanitized.strip()
        if naming == "kebab-case":
            return self._to_kebab_case(sanitized)
        elif naming == "snake_case":
            return self._to_snake_case(sanitized)
        return sanitized

    def _to_kebab_case(self, text: str) -> str:
        """Convert text to kebab-case."""
        # Replace spaces and underscores with hyphens
        text = re.sub(r'[\s_]+', '-', text)
        # Remove special characters
        text = re.sub(r'[^a-zA-Z0-9-]', '', text)
        # Convert to lowercase
        text = text.lower()
        # Remove multiple consecutive hyphens
        text = re.sub(r'-+', '-', text)
        # Remove leading/trailing hyphens
        text = text.strip('-')
        return text

    def _to_snake_case(self, text: str) -> str:
        """Convert text to snake_case."""
        # Replace spaces and hyphens with underscores
        text = re.sub(r'[\s-]+', '_', text)
        # Remove special characters
        text = re.sub(r'[^a-zA-Z0-9_]', '', text)
        # Convert to lowercase
        text = text.lower()
        # Remove multiple consecutive underscores
        text = re.sub(r'_+', '_', text)
        # Remove leading/trailing underscores
        text = text.strip('_')
        return text

    def _get_repository(self, owner: str, name: str) -> Any:
        """Get GitHub repository with retry logic."""
        for attempt in range(self.MAX_RETRIES):
            try:
                repo = self.github.get_repo(f"{owner}/{name}")
                return repo
            except GithubException as e:
                if e.status == 401:
                    raise GitHubAuthenticationError(
                        "GitHub authentication failed. Check your token."
                    ) from e
                if e.status == 404:
                    raise NotFoundError("Repository", f"{owner}/{name}") from e
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue
                raise GitHubAPIError(f"Failed to get repository: {str(e)}") from e
        raise GitHubAPIError("Failed to get repository after retries")

    def _ensure_branch(self, repo: Any, branch_name: str) -> None:
        """Ensure branch exists, create if it doesn't."""
        try:
            repo.get_branch(branch_name)
        except GithubException as e:
            if e.status == 404:
                # Branch doesn't exist, create it
                try:
                    default_branch = repo.default_branch
                    source_sha = repo.get_branch(default_branch).commit.sha
                    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source_sha)
                except GithubException as create_error:
                    raise GitHubAPIError(
                        f"Failed to create branch '{branch_name}': {str(create_error)}"
                    ) from create_error
            else:
                raise GitHubAPIError(f"Failed to check branch '{branch_name}': {str(e)}") from e

    def _create_or_update_file(
        self,
        repo: Any,
        file_path: str,
        content: str,
        commit_message: str,
        branch: Optional[str] = None,
    ) -> str:
        """Create or update a file in the repository with retry logic."""
        for attempt in range(self.MAX_RETRIES):
            try:
                # Check if file exists
                try:
                    file = repo.get_contents(file_path, ref=branch) if branch else repo.get_contents(file_path)
                    # File exists, update it
                    repo.update_file(
                        file_path,
                        commit_message,
                        content,
                        file.sha,
                        branch=branch,
                    )
                except GithubException as e:
                    if e.status == 404:
                        # File doesn't exist, create it
                        repo.create_file(
                            file_path,
                            commit_message,
                            content,
                            branch=branch,
                        )
                    else:
                        raise

                # Get the latest commit SHA
                commits = repo.get_commits(path=file_path, sha=branch if branch else repo.default_branch, per_page=1)
                return commits[0].sha

            except GithubException as e:
                if e.status == 401:
                    raise GitHubAuthenticationError(
                        "GitHub authentication failed. Check your token."
                    ) from e
                if e.status == 403:
                    raise GitHubAPIError(
                        "GitHub API permission denied. Check repository permissions."
                    ) from e
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue
                raise GitHubAPIError(f"Failed to create/update file '{file_path}': {str(e)}") from e

        raise GitHubAPIError("Failed to create/update file after retries")
