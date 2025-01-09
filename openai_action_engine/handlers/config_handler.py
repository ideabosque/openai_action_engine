# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import os
from typing import Any, Dict

import boto3

# Global constants
SYSTEM_CONSTANTS = [
    "region_name",
    "aws_access_key_id",
    "aws_secret_access_key",
    "title",
    "version",
    "configuration",
    "functions",
    "funct_bucket_name",
    "funct_zip_path",
    "funct_extract_path",
]


class Config:
    """
    Centralized Configuration Class
    Manages shared configuration variables across the application.
    """

    title = None
    version = None
    servers = None
    base_path = None
    configuration = None
    functions = None
    aws_s3 = None

    funct_bucket_name = None
    funct_zip_path = "/tmp/funct_zips"
    funct_extract_path = "/tmp/functs"

    @classmethod
    def initialize(cls, logger: logging.Logger, **setting: Dict[str, Any]) -> None:
        """
        Initialize configuration setting.
        Args:
            logger (logging.Logger): Logger instance for logging.
            **setting (Dict[str, Any]): Configuration dictionary.
        """
        try:
            cls._set_parameters(setting)
            cls._initialize_aws_services(setting)
            cls._setup_function_paths(setting)
            logger.info("Configuration initialized successfully.")
        except Exception as e:
            logger.exception("Failed to initialize configuration.")
            raise e

    @classmethod
    def _set_parameters(cls, setting: Dict[str, Any]) -> None:
        """
        Set application-level parameters.
        Args:
            setting (Dict[str, Any]): Configuration dictionary.
        """
        cls.title = setting["title"]
        cls.version = setting["version"]
        cls.servers = setting["servers"]
        cls.base_path = setting["base_path"]
        cls.configuration = setting["configuration"]
        cls.functions = setting["functions"]

    @classmethod
    def _initialize_aws_services(cls, setting: Dict[str, Any]) -> None:
        """
        Initialize AWS services, such as the S3 client.
        Args:
            setting (Dict[str, Any]): Configuration dictionary.
        """
        if all(
            setting.get(k)
            for k in ["region_name", "aws_access_key_id", "aws_secret_access_key"]
        ):
            aws_credentials = {
                "region_name": setting["region_name"],
                "aws_access_key_id": setting["aws_access_key_id"],
                "aws_secret_access_key": setting["aws_secret_access_key"],
            }
        else:
            aws_credentials = {}

        cls.aws_s3 = boto3.client("s3", **aws_credentials)

    @classmethod
    def _setup_function_paths(cls, setting: Dict[str, Any]) -> None:
        """
        Set up function paths for downloading and extracting modules.
        Args:
            setting (Dict[str, Any]): Configuration dictionary.
        """
        cls.funct_bucket_name = setting.get("funct_bucket_name")
        cls.funct_zip_path = setting.get("funct_zip_path", cls.funct_zip_path)
        cls.funct_extract_path = setting.get(
            "funct_extract_path", cls.funct_extract_path
        )

        os.makedirs(cls.funct_zip_path, exist_ok=True)
        os.makedirs(cls.funct_extract_path, exist_ok=True)
