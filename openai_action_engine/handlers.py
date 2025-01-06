#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import os
import re
import sys
import traceback
import zipfile
from typing import Any, Callable, Dict, List, Optional, Tuple

import boto3
import yaml

from silvaengine_utility import Utility

title = None
version = None
configuration = None
functions = None
aws_s3 = None

funct_bucket_name = None
funct_zip_path = None
funct_extract_path = None


def handlers_init(logger: logging.Logger, **setting: Dict[str, Any]) -> None:
    global title, version, configuration, functions
    global aws_s3
    global funct_bucket_name, funct_zip_path, funct_extract_path
    try:
        _set_parameters(setting)
        _initialize_aws_services(setting)
        _setup_function_paths(setting)
    except Exception as e:
        logger.exception(e)
        raise e


def _set_parameters(setting: Dict[str, Any]) -> None:
    global title, version, configuration, functions
    title = setting["title"]
    version = setting["version"]
    configuration = setting["configuration"]
    functions = setting["functions"]


def _initialize_aws_services(setting: Dict[str, Any]) -> None:
    global aws_s3
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

    aws_s3 = boto3.client("s3", **aws_credentials)


def _setup_function_paths(setting: Dict[str, Any]) -> None:
    global funct_bucket_name, funct_zip_path, funct_extract_path
    funct_bucket_name = setting.get("funct_bucket_name")
    funct_zip_path = setting.get("funct_zip_path", "/tmp/funct_zips")
    funct_extract_path = setting.get("funct_extract_path", "/tmp/functs")
    os.makedirs(funct_zip_path, exist_ok=True)
    os.makedirs(funct_extract_path, exist_ok=True)


def generate_swagger_yaml(logger: logging.Logger) -> str:
    try:
        swagger = {
            "openapi": "3.0.0",
            "info": {
                "title": title,
                "version": version,
            },
            "paths": {},
        }

        # Type mappings for OpenAPI
        type_mapping = {
            "string": "string",
            "integer": "integer",
            "float": "number",
            "boolean": "boolean",
            "date": "string",
            "datetime": "string",
            "list": "array",
            "dict": "object",
        }

        def handle_properties(properties):
            """Recursively handle properties for dict or list."""
            result = {}
            for prop in properties:
                prop_type = type_mapping.get(prop["type"], "string")
                if prop_type == "array" and "child_type" in prop:
                    # Handle nested list
                    child_type = type_mapping.get(prop["child_type"], "string")
                    nested_properties = {}
                    if child_type == "object" and "properties" in prop:
                        nested_properties = handle_properties(prop["properties"])
                    result[prop["name"]] = {
                        "type": "array",
                        "items": {
                            "type": child_type,
                            "properties": (
                                nested_properties if child_type == "object" else None
                            ),
                        },
                    }
                elif prop_type == "object" and "properties" in prop:
                    # Handle nested dict
                    result[prop["name"]] = {
                        "type": "object",
                        "properties": handle_properties(prop["properties"]),
                    }
                else:
                    # Handle primitive types
                    result[prop["name"]] = {"type": prop_type}
            return result

        # Add functions to the Swagger paths
        for function in functions:
            path = function["path"]
            method = function["method"].lower()
            summary = function.get("summary", "No summary provided")
            function_name = function.get("function_name", "unknownFunction")
            parameters = []
            request_body = None
            response = {}

            # Handle parameters
            for param in function["parameters"]:
                if method in ["post", "put", "patch"] and param["in"] == "body":
                    # Add to requestBody
                    if request_body is None:
                        request_body = {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object", "properties": {}}
                                }
                            },
                        }
                    request_body["content"]["application/json"]["schema"]["properties"][
                        param["name"]
                    ] = {
                        "type": type_mapping.get(param["type"], "string"),
                    }
                else:
                    param_schema = {"type": type_mapping.get(param["type"], "string")}
                    parameters.append(
                        {
                            "name": param["name"],
                            "in": param["in"],
                            "required": param["required"],
                            "schema": param_schema,
                        }
                    )

            # Handle response
            response_config = function["response"]
            if response_config["type"] == "list":
                # Array response
                child_type = type_mapping.get(response_config["child_type"], "string")
                item_properties = {}
                if child_type == "object" and "properties" in response_config:
                    item_properties = handle_properties(response_config["properties"])
                response = {
                    "description": "Success",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {
                                    "type": child_type,
                                    "properties": (
                                        item_properties
                                        if child_type == "object"
                                        else None
                                    ),
                                },
                            }
                        }
                    },
                }
            elif response_config["type"] == "dict":
                # Object response
                properties = handle_properties(response_config["properties"])
                response = {
                    "description": "Success",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": properties,
                            }
                        }
                    },
                }

            # Build the path
            if path not in swagger["paths"]:
                swagger["paths"][path] = {}

            path_data = {
                "summary": summary,
                "operationId": function_name,
                "parameters": parameters,
                "response": response,
            }

            # Include requestBody for POST/PUT/PATCH
            if request_body:
                path_data["requestBody"] = request_body

            swagger["paths"][path][method] = path_data

        return yaml.dump(swagger, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        log = traceback.format_exc()
        logger.error(log)
        raise e


def module_exists(logger: logging.Logger, module_name: str) -> bool:
    """Check if the module exists in the specified path."""
    module_dir = os.path.join(funct_extract_path, module_name)
    if os.path.exists(module_dir) and os.path.isdir(module_dir):
        logger.info(f"Module {module_name} found in {funct_extract_path}.")
        return True
    logger.info(f"Module {module_name} not found in {funct_extract_path}.")
    return False


def download_and_extract_module(logger: logging.Logger, module_name: str) -> None:
    """Download and extract the module from S3 if not already extracted."""
    key = f"{module_name}.zip"
    zip_path = f"{funct_zip_path}/{key}"

    logger.info(f"Downloading module from S3: bucket={funct_bucket_name}, key={key}")
    aws_s3.download_file(funct_bucket_name, key, zip_path)
    logger.info(f"Downloaded {key} from S3 to {zip_path}")

    # Extract the ZIP file
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(funct_extract_path)
    logger.info(f"Extracted module to {funct_extract_path}")


def get_action_function(
    logger: logging.Logger, function_name: str
) -> Optional[Callable]:
    try:
        action_functions = list(
            filter(lambda x: x["function_name"] == function_name, functions)
        )
        if len(action_functions) == 0:
            return None

        action_function = action_functions[0]

        # Check if the module exists
        if not module_exists(logger, action_function["module_name"]):
            # Download and extract the module if it doesn't exist
            download_and_extract_module(logger, action_function["module_name"])

        # Add the extracted module to sys.path
        module_path = f"{funct_extract_path}/{action_function['module_name']}"
        if module_path not in sys.path:
            sys.path.append(module_path)

        action_function_class = getattr(
            __import__(action_function["module_name"]),
            action_function["class_name"],
        )

        return getattr(
            action_function_class(
                logger,
                **Utility.json_loads(
                    Utility.json_dumps(
                        dict(configuration, **action_function["configuration"])
                        if action_function.get("configuration")
                        else configuration
                    )
                ),
            ),
            function_name,
        )
    except Exception as e:
        log = traceback.format_exc()
        logger.error(log)
        raise e


def get_function_name_and_path_parameters(
    logger: logging.Logger, path: str
) -> Tuple[str:Any]:
    try:
        for function in functions:
            # Replace placeholders with regex patterns for path parameters
            pattern = re.sub(r"{(\w+)}", r"(?P<\1>[^/]+)", function["path"])
            match = re.fullmatch(pattern, path)
            if match:
                return (
                    function["function_name"],
                    match.groupdict(),
                )  # Return function and extracted params
        return None, None

    except Exception as e:
        log = traceback.format_exc()
        logger.error(log)
        raise e
