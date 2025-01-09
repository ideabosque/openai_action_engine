# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"


import logging
import os
import re
import sys
import traceback
from typing import Callable, Dict, Optional, Tuple

from silvaengine_utility import Utility  # Reuse existing utility functions

from .aws_handler import download_and_extract_module, module_exists
from .config_handler import Config  # Import Config class


def load_action_function(
    logger: logging.Logger, function_name: str
) -> Optional[Callable]:
    """
    Dynamically load the specified function from a module.
    Args:
        logger (logging.Logger): Logger instance for logging information.
        function_name (str): Name of the function to load.

    Returns:
        Optional[Callable]: Callable object of the function if successful, None otherwise.
    """
    try:
        # Find the function configuration
        action_functions = list(
            filter(lambda x: x["function_name"] == function_name, Config.functions)
        )
        if not action_functions:
            logger.error(f"Function {function_name} not found in configuration.")
            return None

        action_function = action_functions[0]
        module_name = action_function["module_name"]

        # Ensure the module exists locally
        if not module_exists(logger, module_name):
            logger.info(f"Downloading and extracting module {module_name}.")
            if not download_and_extract_module(logger, module_name):
                logger.error(f"Failed to load module {module_name}.")
                return None

        # Add the module path to sys.path
        module_path = os.path.join(Config.funct_extract_path, module_name)
        if module_path not in sys.path:
            sys.path.append(module_path)

        # Import the module and retrieve the class
        logger.info(f"Loading module {module_name}.")
        module = __import__(module_name)
        class_name = action_function["class_name"]
        action_function_class = getattr(module, class_name)

        # Instantiate the class and retrieve the function
        instance = action_function_class(
            logger,
            **Utility.json_loads(
                Utility.json_dumps(
                    dict(
                        Config.configuration, **action_function.get("configuration", {})
                    )
                )
            ),
        )
        return getattr(instance, function_name)

    except Exception as e:
        logger.error(
            f"Failed to load function {function_name}: {traceback.format_exc()}"
        )
        return None


def get_function_name_and_path_parameters(
    logger: logging.Logger, path: str
) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """
    Extract the function name and path parameters from a URL path.
    Args:
        logger (logging.Logger): Logger instance for logging information.
        path (str): The URL path.

    Returns:
        Tuple[Optional[str], Optional[Dict[str, str]]]: The function name and path parameters, or (None, None) if not found.
    """
    try:
        for function in Config.functions:
            # Replace placeholders with regex patterns for path parameters
            pattern = re.sub(r"{(\w+)}", r"(?P<\1>[^/]+)", function["path"])
            match = re.fullmatch(pattern, path)
            if match:
                return function["function_name"], match.groupdict()
        return None, None
    except Exception as e:
        logger.error(
            f"Error extracting function name and parameters: {traceback.format_exc()}"
        )
        raise e


def execute_function(
    logger: logging.Logger, function_name: str, **kwargs
) -> Optional[Dict]:
    """
    Execute the specified function with the given parameters.
    Args:
        logger (logging.Logger): Logger instance for logging information.
        function_name (str): Name of the function to execute.
        **kwargs: Parameters to pass to the function.

    Returns:
        Optional[Dict]: The result of the function execution, or None if an error occurs.
    """
    try:
        action_function = load_action_function(logger, function_name)
        if not action_function:
            logger.exception(f"{function_name} is not supported!!")
            raise Exception(f"{function_name} is not supported")

        logger.info(f"Executing function {function_name} with parameters: {kwargs}")
        result = action_function(**kwargs)
        return (
            Utility.json_dumps(result) if isinstance(result, (dict, list)) else result
        )
    except Exception as e:
        logger.error(
            f"Failed to execute function {function_name}: {traceback.format_exc()}"
        )
        raise e
