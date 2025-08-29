#!/usr/bin/env python3
"""
Download required NLTK data packages for the application.

This script handles NLTK data downloads with proper error handling
and suppresses the RuntimeWarning that occurs due to import order
during Docker builds.
"""

import logging
import os
import sys
import warnings
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

# Suppress the specific RuntimeWarning about module import order
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*found in sys.modules after import.*")


def download_nltk_data(download_dir: Optional[str] = None) -> bool:
    """
    Download required NLTK data packages.

    Args:
        download_dir: Directory to download NLTK data to. If None, uses NLTK_DATA env var.

    Returns:
        True if all downloads succeeded, False otherwise.
    """
    try:
        import nltk

        # Set download directory
        if download_dir:
            nltk_data_dir = Path(download_dir)
        elif "NLTK_DATA" in os.environ:
            nltk_data_dir = Path(os.environ["NLTK_DATA"])
        else:
            nltk_data_dir = Path.home() / "nltk_data"

        # Ensure directory exists
        nltk_data_dir.mkdir(parents=True, exist_ok=True)

        # Required packages for UnstructuredMarkdownLoader and text processing
        required_packages = [
            "punkt_tab",  # Sentence tokenization (modern NLTK 3.8.2+)
            "averaged_perceptron_tagger_eng",  # POS tagging for English
        ]

        logger.info(f"Downloading NLTK data to: {nltk_data_dir}")

        success = True
        for package in required_packages:
            try:
                logger.info(f"Downloading {package}...")
                result = nltk.download(package, download_dir=str(nltk_data_dir), quiet=False)
                if result:
                    logger.info(f"✓ Successfully downloaded {package}")
                else:
                    logger.error(f"✗ Failed to download {package}")
                    success = False
            except Exception as e:
                logger.error(f"✗ Error downloading {package}: {e}")
                success = False

        if success:
            logger.info("✓ All NLTK data packages downloaded successfully!")
        else:
            logger.error("✗ Some NLTK data packages failed to download")

        return success

    except ImportError as e:
        logger.error(f"✗ Error importing NLTK: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        return False


def main():
    """Main entry point for the script."""
    download_dir = sys.argv[1] if len(sys.argv) > 1 else None
    success = download_nltk_data(download_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
