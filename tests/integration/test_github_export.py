"""Integration tests for GitHub export functionality."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

pytestmark = pytest.mark.integration

from docomatic.services.document_service import DocumentService
from docomatic.services.export_service import (
    ExportConfig,
    ExportFormat,
    ExportService,
    GitHubAPIError,
    GitHubAuthenticationError,
)
from docomatic.services.section_service import SectionService


@pytest.fixture
def mock_github_repo():
    """Create a mock GitHub repository."""
    repo = MagicMock()
    repo.default_branch = "main"
    
    # Mock file operations
    repo.get_contents = Mock(side_effect=Exception("File not found"))  # Default: file doesn't exist
    repo.create_file = Mock(return_value={"commit": {"sha": "mock_commit_sha"}})
    repo.update_file = Mock(return_value={"commit": {"sha": "mock_commit_sha"}})
    
    # Mock branch operations
    default_branch = MagicMock()
    default_branch.commit.sha = "default_sha"
    repo.get_branch = Mock(return_value=default_branch)
    repo.create_git_ref = Mock(return_value=None)
    
    # Mock commits
    commit = MagicMock()
    commit.sha = "mock_commit_sha"
    repo.get_commits = Mock(return_value=[commit])
    
    return repo


@pytest.fixture
def mock_github():
    """Create a mock GitHub client."""
    github = MagicMock()
    return github


class TestGitHubExportSingleFile:
    """Test exporting documents as single Markdown files."""

    @patch("docomatic.services.export_service.Github")
    def test_export_document_single_file(
        self, mock_github_class, temp_db, mock_github, mock_github_repo
    ):
        """Test exporting a document as a single Markdown file."""
        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_github_repo

        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)

            # Create document with sections
            doc = doc_service.create_document(
                title="Test Document", metadata={"version": "1.0"}
            )

            section1 = section_service.create_section(
                document_id=doc.id, heading="Introduction", body="This is the introduction."
            )
            section2 = section_service.create_section(
                document_id=doc.id, heading="Main Content", body="This is the main content."
            )
            nested = section_service.create_section(
                document_id=doc.id,
                heading="Details",
                body="Detailed information.",
                parent_section_id=section2.id,
            )

            # Export to GitHub
            export_service = ExportService(session, "mock_token")
            result = export_service.export_document(
                document_id=doc.id,
                repo_owner="test",
                repo_name="repo",
                config=ExportConfig(format=ExportFormat.SINGLE_FILE),
            )

            assert result["status"] == "success"
            assert len(result["files_created"]) == 1
            assert result["files_created"][0] == "docs/test-document.md"
            assert "commit_sha" in result
            assert "Test Document" in result["message"]

            # Verify GitHub API was called
            mock_github.get_repo.assert_called_once_with("test/repo")
            mock_github_repo.create_file.assert_called_once()
            call_args = mock_github_repo.create_file.call_args
            assert call_args[0][0] == "docs/test-document.md"
            assert "Test Document" in call_args[0][1]  # commit message
            assert "# Test Document" in call_args[0][2]  # content

    @patch("docomatic.services.export_service.Github")
    def test_export_document_with_metadata(
        self, mock_github_class, temp_db, mock_github, mock_github_repo
    ):
        """Test exporting document with metadata in frontmatter."""
        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_github_repo

        with temp_db.session() as session:
            doc_service = DocumentService(session)

            doc = doc_service.create_document(
                title="Document with Metadata",
                metadata={"author": "test", "version": "1.0", "tags": ["test", "docs"]},
            )

            # Export with metadata
            export_service = ExportService(session, "mock_token")
            config = ExportConfig(format=ExportFormat.SINGLE_FILE, include_metadata=True)
            result = export_service.export_document(
                document_id=doc.id, repo_owner="test", repo_name="repo", config=config
            )

            assert result["status"] == "success"
            # Verify frontmatter was included
            call_args = mock_github_repo.create_file.call_args
            content = call_args[0][2]
            assert "---" in content
            assert "author: test" in content or 'author: "test"' in content
            assert "version: 1.0" in content


class TestGitHubExportMultiFile:
    """Test exporting documents as multiple files (one per section)."""

    @patch("docomatic.services.export_service.Github")
    def test_export_document_multi_file(
        self, mock_github_class, temp_db, mock_github, mock_github_repo
    ):
        """Test exporting document as multiple files (one per top-level section)."""
        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_github_repo

        with temp_db.session() as session:
            doc_service = DocumentService(session)
            section_service = SectionService(session)

            doc = doc_service.create_document(title="Multi-File Document")

            section1 = section_service.create_section(
                document_id=doc.id, heading="Section 1", body="Content 1"
            )
            section2 = section_service.create_section(
                document_id=doc.id, heading="Section 2", body="Content 2"
            )
            nested = section_service.create_section(
                document_id=doc.id,
                heading="Nested",
                body="Nested content",
                parent_section_id=section1.id,
            )

            # Export as multiple files
            export_service = ExportService(session, "mock_token")
            config = ExportConfig(format=ExportFormat.MULTI_FILE)
            result = export_service.export_document(
                document_id=doc.id, repo_owner="test", repo_name="repo", config=config
            )

            assert result["status"] == "success"
            assert len(result["files_created"]) == 2
            assert all("section" in f.lower() for f in result["files_created"])

            # Verify multiple files were created
            assert mock_github_repo.create_file.call_count == 2


class TestGitHubExportErrorHandling:
    """Test error handling in GitHub export."""

    @patch("docomatic.services.export_service.Github")
    def test_export_nonexistent_document(self, mock_github_class, temp_db):
        """Test exporting non-existent document raises error."""
        mock_github_class.return_value = MagicMock()

        with temp_db.session() as session:
            export_service = ExportService(session, "mock_token")

            with pytest.raises(Exception):  # NotFoundError
                export_service.export_document(
                    document_id="nonexistent-id",
                    repo_owner="test",
                    repo_name="repo",
                )

    @patch("docomatic.services.export_service.Github")
    def test_export_github_authentication_error(
        self, mock_github_class, temp_db, mock_github
    ):
        """Test handling GitHub authentication errors."""
        from github import GithubException

        mock_github_class.return_value = mock_github
        # Simulate authentication error
        mock_github.get_repo.side_effect = GithubException(
            status=401, data={"message": "Bad credentials"}, headers={}
        )

        with temp_db.session() as session:
            doc_service = DocumentService(session)
            doc = doc_service.create_document(title="Test Document")

            export_service = ExportService(session, "invalid_token")
            with pytest.raises(GitHubAuthenticationError):
                export_service.export_document(
                    document_id=doc.id, repo_owner="test", repo_name="repo"
                )

    @patch("docomatic.services.export_service.Github")
    def test_export_github_api_error(self, mock_github_class, temp_db, mock_github):
        """Test handling GitHub API errors."""
        from github import GithubException

        mock_github_class.return_value = mock_github
        # Simulate API error
        mock_github.get_repo.side_effect = GithubException(
            status=500, data={"message": "Internal server error"}, headers={}
        )

        with temp_db.session() as session:
            doc_service = DocumentService(session)
            doc = doc_service.create_document(title="Test Document")

            export_service = ExportService(session, "mock_token")
            with pytest.raises(GitHubAPIError):
                export_service.export_document(
                    document_id=doc.id, repo_owner="test", repo_name="repo"
                )

    @patch("docomatic.services.export_service.Github")
    def test_export_nonexistent_repository(
        self, mock_github_class, temp_db, mock_github
    ):
        """Test exporting to non-existent repository raises error."""
        from github import GithubException

        mock_github_class.return_value = mock_github
        # Simulate repository not found
        mock_github.get_repo.side_effect = GithubException(
            status=404, data={"message": "Not Found"}, headers={}
        )

        with temp_db.session() as session:
            doc_service = DocumentService(session)
            doc = doc_service.create_document(title="Test Document")

            export_service = ExportService(session, "mock_token")
            with pytest.raises(Exception):  # NotFoundError
                export_service.export_document(
                    document_id=doc.id, repo_owner="test", repo_name="nonexistent"
                )


class TestGitHubExportFormats:
    """Test different export formats and options."""

    @patch("docomatic.services.export_service.Github")
    def test_export_with_custom_path(
        self, mock_github_class, temp_db, mock_github, mock_github_repo
    ):
        """Test exporting with custom file path."""
        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_github_repo

        with temp_db.session() as session:
            doc_service = DocumentService(session)
            doc = doc_service.create_document(title="Custom Path Document")

            export_service = ExportService(session, "mock_token")
            config = ExportConfig(format=ExportFormat.SINGLE_FILE, base_path="custom/path")
            result = export_service.export_document(
                document_id=doc.id, repo_owner="test", repo_name="repo", config=config
            )

            assert result["status"] == "success"
            assert result["files_created"][0].startswith("custom/path/")

    @patch("docomatic.services.export_service.Github")
    def test_export_with_branch(
        self, mock_github_class, temp_db, mock_github, mock_github_repo
    ):
        """Test exporting to a specific branch."""
        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_github_repo

        with temp_db.session() as session:
            doc_service = DocumentService(session)
            doc = doc_service.create_document(title="Branch Document")

            export_service = ExportService(session, "mock_token")
            config = ExportConfig(format=ExportFormat.SINGLE_FILE, branch="export-branch")
            result = export_service.export_document(
                document_id=doc.id, repo_owner="test", repo_name="repo", config=config
            )

            assert result["status"] == "success"
            # Verify branch was checked/created
            mock_github_repo.get_branch.assert_called()

    @patch("docomatic.services.export_service.Github")
    def test_export_file_naming_conventions(
        self, mock_github_class, temp_db, mock_github, mock_github_repo
    ):
        """Test different file naming conventions."""
        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_github_repo

        with temp_db.session() as session:
            doc_service = DocumentService(session)
            doc = doc_service.create_document(title="Test Document With Spaces")

            export_service = ExportService(session, "mock_token")

            # Test kebab-case (default)
            config = ExportConfig(format=ExportFormat.SINGLE_FILE, file_naming="kebab-case")
            result = export_service.export_document(
                document_id=doc.id, repo_owner="test", repo_name="repo", config=config
            )
            assert "test-document-with-spaces" in result["files_created"][0]

            # Reset mock
            mock_github_repo.create_file.reset_mock()

            # Test snake_case
            config = ExportConfig(format=ExportFormat.SINGLE_FILE, file_naming="snake_case")
            result = export_service.export_document(
                document_id=doc.id, repo_owner="test", repo_name="repo", config=config
            )
            assert "test_document_with_spaces" in result["files_created"][0]

    @patch("docomatic.services.export_service.Github")
    def test_export_without_metadata(
        self, mock_github_class, temp_db, mock_github, mock_github_repo
    ):
        """Test exporting without metadata."""
        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_github_repo

        with temp_db.session() as session:
            doc_service = DocumentService(session)
            doc = doc_service.create_document(
                title="No Metadata Document", metadata={"author": "test"}
            )

            export_service = ExportService(session, "mock_token")
            config = ExportConfig(format=ExportFormat.SINGLE_FILE, include_metadata=False)
            result = export_service.export_document(
                document_id=doc.id, repo_owner="test", repo_name="repo", config=config
            )

            assert result["status"] == "success"
            # Verify no frontmatter
            call_args = mock_github_repo.create_file.call_args
            content = call_args[0][2]
            assert not content.startswith("---")
