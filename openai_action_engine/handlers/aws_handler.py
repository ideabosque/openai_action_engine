# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import os
import zipfile
from typing import Optional

from botocore.exceptions import ClientError

from .config_handler import Config  # Import Config class


def download_module(logger: logging.Logger, module_name: str) -> Optional[str]:
    """
    Download a module ZIP file from the configured S3 bucket.
    Args:
        logger (logging.Logger): Logger instance for logging information.
        module_name (str): Name of the module to download.

    Returns:
        Optional[str]: Path to the downloaded ZIP file, or None if an error occurred.
    """
    try:
        if not Config.funct_bucket_name:
            logger.error("S3 bucket name is not configured.")
            return None

        key = f"{module_name}.zip"
        zip_path = os.path.join(Config.funct_zip_path, key)

        # Ensure the ZIP path directory exists
        os.makedirs(Config.funct_zip_path, exist_ok=True)

        logger.info(
            f"Downloading module from S3: bucket={Config.funct_bucket_name}, key={key}"
        )
        Config.aws_s3.download_file(Config.funct_bucket_name, key, zip_path)
        logger.info(f"Successfully downloaded {key} from S3 to {zip_path}")
        return zip_path
    except ClientError as e:
        logger.error(f"ClientError while downloading {module_name}: {e}")
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error while downloading {module_name}: {e}")
        raise e


def extract_module(logger: logging.Logger, zip_path: str) -> Optional[str]:
    """
    Extract a module ZIP file to the configured extraction path.
    Args:
        logger (logging.Logger): Logger instance for logging information.
        zip_path (str): Path to the ZIP file to extract.

    Returns:
        Optional[str]: Path to the extracted module, or None if an error occurred.
    """
    try:
        if not os.path.exists(zip_path):
            logger.error(f"ZIP file not found: {zip_path}")
            raise Exception(f"ZIP file not found: {zip_path}")

        # Ensure the extraction directory exists
        os.makedirs(Config.funct_extract_path, exist_ok=True)

        logger.info(f"Extracting ZIP file: {zip_path}")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(Config.funct_extract_path)
        logger.info(f"Successfully extracted module to {Config.funct_extract_path}")
        return Config.funct_extract_path
    except zipfile.BadZipFile as e:
        logger.error(f"BadZipFile error while extracting {zip_path}: {e}")
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error while extracting {zip_path}: {e}")
        raise e


def download_and_extract_module(
    logger: logging.Logger, module_name: str
) -> Optional[str]:
    """
    Download and extract a module from S3.
    Combines downloading the module as a ZIP file and extracting it.
    Args:
        logger (logging.Logger): Logger instance for logging information.
        module_name (str): Name of the module to download and extract.

    Returns:
        Optional[str]: Path to the extracted module, or None if an error occurred.
    """
    logger.info(f"Initiating download and extraction for module: {module_name}")

    # Download the module
    zip_path = download_module(logger, module_name)
    if not zip_path:
        logger.error(f"Failed to download module {module_name}")
        return None

    # Extract the module
    extracted_path = extract_module(logger, zip_path)
    if not extracted_path:
        logger.error(f"Failed to extract module {module_name}")
        return None

    logger.info(
        f"Module {module_name} downloaded and extracted successfully to {extracted_path}"
    )
    return extracted_path


def module_exists(logger: logging.Logger, module_name: str) -> bool:
    """
    Check if the specified module exists in the extracted path.
    Args:
        logger (logging.Logger): Logger instance for logging information.
        module_name (str): Name of the module to check.

    Returns:
        bool: True if the module exists, False otherwise.
    """
    module_dir = os.path.join(Config.funct_extract_path, module_name)
    if os.path.exists(module_dir) and os.path.isdir(module_dir):
        logger.info(f"Module {module_name} found in {Config.funct_extract_path}.")
        return True
    logger.info(f"Module {module_name} not found in {Config.funct_extract_path}.")
    return False
