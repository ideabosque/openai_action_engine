# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict

import yaml

from .config_handler import Config  # Import Config class

# Mapping from data types to OpenAPI schema types
TYPE_MAPPING = {
    "string": "string",
    "integer": "integer",
    "float": "number",
    "boolean": "boolean",
    "date": "string",
    "datetime": "string",
    "list": "array",
    "dict": "object",
}


def generate_swagger_yaml(logger: logging.Logger) -> str:
    """
    Generates the Swagger YAML for the application.
    Args:
        logger (logging.Logger): Logger instance for logging.

    Returns:
        str: The generated Swagger YAML as a string.
    """
    try:
        logger.info("Generating Swagger YAML...")

        # Base Swagger configuration
        swagger = {
            "openapi": "3.1.0",
            "info": {
                "title": Config.title,
                "version": Config.version,
            },
            "servers": [{"url": server} for server in Config.servers],
            "paths": {},
        }

        # Generate paths and methods from functions
        for function in Config.functions:
            path = Config.base_path + function["path"]
            method = function["method"].lower()
            summary = function.get("summary", "No summary provided")
            function_name = function.get("function_name", "unknownFunction")

            # Request parameters and body
            parameters = []
            request_body = None
            response = {}

            for param in function["parameters"]:
                if method in ["post", "put", "patch"] and param["in"] == "body":
                    if request_body is None:
                        request_body = {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object", "properties": {}}
                                }
                            },
                        }
                    if "properties" in param:
                        request_body["content"]["application/json"]["schema"][
                            "properties"
                        ][param["name"]] = {
                            "type": TYPE_MAPPING.get(param["type"], "string"),
                            "properties": _handle_properties(param.get("properties")),
                        }
                    else:
                        request_body["content"]["application/json"]["schema"][
                            "properties"
                        ][param["name"]] = {
                            "type": TYPE_MAPPING.get(param["type"], "string")
                        }
                else:
                    parameters.append(
                        {
                            "name": param["name"],
                            "in": param["in"],
                            "required": param["required"],
                            "schema": {
                                "type": TYPE_MAPPING.get(param["type"], "string")
                            },
                        }
                    )

            # Response schema
            response_config = function["response"]
            if response_config["type"] == "list":
                response = {
                    "description": "Success",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": _build_response_schema(response_config),
                            }
                        }
                    },
                }
            elif response_config["type"] == "dict":
                response = {
                    "description": "Success",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": _handle_properties(
                                    response_config["properties"]
                                ),
                            }
                        }
                    },
                }

            # Add the operation to the path
            if path not in swagger["paths"]:
                swagger["paths"][path] = {}
            swagger["paths"][path][method] = {
                "summary": summary,
                "operationId": function_name,
                "parameters": parameters,
                "responses": {"200": response},
                **({"requestBody": request_body} if request_body else {}),
            }

        # Convert to YAML
        logger.info("Swagger YAML generated successfully.")
        return yaml.dump(swagger, default_flow_style=False, allow_unicode=True)

    except Exception as e:
        logger.exception("Failed to generate Swagger YAML.")
        raise e


def _handle_properties(properties: Any) -> Dict[str, Any]:
    """
    Recursively handle nested properties for schemas.
    Args:
        properties (Any): List or dictionary of properties.

    Returns:
        Dict[str, Any]: OpenAPI-compatible schema properties.
    """
    result = {}
    for prop in properties:
        prop_type = TYPE_MAPPING.get(prop["type"], "string")
        if prop_type == "array" and "child_type" in prop:
            child_type = TYPE_MAPPING.get(prop["child_type"], "string")
            nested_properties = (
                _handle_properties(prop["properties"]) if "properties" in prop else {}
            )
            result[prop["name"]] = {
                "type": "array",
                "items": {
                    "type": child_type,
                    "properties": nested_properties if child_type == "object" else None,
                },
            }
        elif prop_type == "object" and "properties" in prop:
            result[prop["name"]] = {
                "type": "object",
                "properties": _handle_properties(prop["properties"]),
            }
        else:
            result[prop["name"]] = {"type": prop_type}
    return result


def _build_response_schema(response_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Builds the response schema based on the configuration.
    Args:
        response_config (Dict[str, Any]): The response configuration.

    Returns:
        Dict[str, Any]: OpenAPI-compatible schema.
    """
    child_type = TYPE_MAPPING.get(response_config.get("child_type"), "string")
    if child_type == "object" and "properties" in response_config:
        return {
            "type": "object",
            "properties": _handle_properties(response_config["properties"]),
        }
    return {"type": child_type}
