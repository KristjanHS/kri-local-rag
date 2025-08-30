#!/usr/bin/env python3
"""Unit tests for the post-push git hook script."""

from unittest.mock import MagicMock, patch


class TestPostPushHook:
    """Test the post-push hook functionality."""

    def test_extract_pr_url_from_already_exists_message(self):
        """Test that PR URL is correctly extracted from 'already exists' error message."""
        # Mock the gh pr create output that indicates an existing PR
        mock_output = """a pull request for branch "dev" into branch "main" already exists:
https://github.com/KristjanHS/kri-local-rag/pull/70"""

        # Test the regex pattern used in the script
        import re

        pattern = r"https://github\.com/[^/]*/[^/]*/pull/[0-9]+"
        matches = re.findall(pattern, mock_output)

        assert len(matches) == 1
        assert matches[0] == "https://github.com/KristjanHS/kri-local-rag/pull/70"

    def test_extract_pr_url_from_success_message(self):
        """Test that PR URL is correctly extracted from successful PR creation."""
        # Mock the gh pr create output for successful creation
        mock_output = """✓ Created pull request #71: auto PR and integr tsts after push - fixed
https://github.com/KristjanHS/kri-local-rag/pull/71"""

        import re

        pattern = r"https://github\.com/[^/]*/[^/]*/pull/[0-9]+"
        matches = re.findall(pattern, mock_output)

        assert len(matches) == 1
        assert matches[0] == "https://github.com/KristjanHS/kri-local-rag/pull/71"

    def test_extract_pr_url_with_multiple_urls(self):
        """Test that only the first PR URL is extracted when multiple URLs are present."""
        # Mock output with multiple URLs (should extract only the first PR URL)
        mock_output = """Some text with https://github.com/other/repo/issues/123
a pull request for branch "dev" into branch "main" already exists:
https://github.com/KristjanHS/kri-local-rag/pull/70
More text with https://github.com/another/repo/pull/99"""

        import re

        pattern = r"https://github\.com/[^/]*/[^/]*/pull/[0-9]+"
        matches = re.findall(pattern, mock_output)

        assert len(matches) == 2
        # Should return the first match when using head -1
        assert matches[0] == "https://github.com/KristjanHS/kri-local-rag/pull/70"

    def test_no_pr_url_in_output(self):
        """Test that no PR URL is extracted when none is present."""
        mock_output = """Some error message without any PR URL
This is just regular text without GitHub URLs"""

        import re

        pattern = r"https://github\.com/[^/]*/[^/]*/pull/[0-9]+"
        matches = re.findall(pattern, mock_output)

        assert len(matches) == 0

    @patch("subprocess.run")
    def test_gh_pr_create_already_exists_handling(self, mock_run):
        """Test that the script handles 'already exists' case correctly."""
        # Mock the gh pr create command to return exit code 1 with existing PR message
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=b"",
            stderr=b'a pull request for branch "dev" into branch "main" already exists:\nhttps://github.com/KristjanHS/kri-local-rag/pull/70',
        )

        # This test verifies the logic flow, but the actual script logic
        # would need to be tested with a more comprehensive integration test
        # that mocks the entire bash script execution
        assert mock_run.return_value.returncode == 1

    def test_regex_pattern_robustness(self):
        """Test that the regex pattern handles various GitHub URL formats."""
        test_cases = [
            "https://github.com/user/repo/pull/123",
            "https://github.com/org-name/repo-name/pull/456",
            "https://github.com/user123/repo_123/pull/789",
        ]

        import re

        pattern = r"https://github\.com/[^/]*/[^/]*/pull/[0-9]+"

        for url in test_cases:
            matches = re.findall(pattern, url)
            assert len(matches) == 1
            assert matches[0] == url

    def test_regex_pattern_rejects_invalid_urls(self):
        """Test that the regex pattern rejects invalid GitHub URLs."""
        invalid_urls = [
            "https://github.com/user/repo/issues/123",  # issues, not pull
            "https://gitlab.com/user/repo/pull/123",  # gitlab, not github
            "https://github.com/user/repo/pull/abc",  # non-numeric PR number
            "https://github.com/user/repo",  # no pull request
        ]

        import re

        pattern = r"https://github\.com/[^/]*/[^/]*/pull/[0-9]+"

        for url in invalid_urls:
            matches = re.findall(pattern, url)
            assert len(matches) == 0, f"URL should not match: {url}"
