#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, List, Tuple

from silvaengine_utility import Utility

from .handlers.config import SYSTEM_CONSTANTS, Config
from .handlers.function_handler import (
    execute_function,
    get_function_name_and_path_parameters,
)
from .handlers.swagger_generator import generate_swagger_yaml


# Hook function applied to deployment
def deploy() -> List:
    return [
        {
            "service": "OpenAI Action Engine",
            "class": "OpenaiActionEngine",
            "functions": {
                "openai_action_dispatch": {
                    "is_static": False,
                    "label": "Openai Action Dispatch",
                    "type": "RequestResponse",
                    "support_methods": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                    "is_auth_required": False,
                    "is_graphql": False,
                    "settings": "openai_action_engine",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
            },
        }
    ]


class OpenaiActionEngine(object):
    def __init__(self, logger: logging.Logger, **setting: Dict[str, Any]) -> None:
        """
        Initializes the OpenAI Action Engine.
        Args:
            logger (logging.Logger): Logger instance for logging.
            **settings (Dict[str, Any]): Configuration dictionary.
        """
        # Initialize configuration via the Config class
        Config.initialize(logger, **setting)

        self.logger = logger
        self.setting = setting

    def openai_action_dispatch(self, **kwargs: Dict[str, Any]) -> Any:
        path = "/" + kwargs.pop("path")
        if path is None:
            raise Exception("path is required!!")
        self.logger.info(f"path = {path}")

        kwargs = dict(
            {k: v for k, v in self.setting.items() if k not in SYSTEM_CONSTANTS},
            **kwargs,
        )

        if path.find("openapi.yaml") != -1:
            return generate_swagger_yaml(self.logger)
        else:
            function_name, path_parameters = get_function_name_and_path_parameters(
                self.logger, path
            )
            kwargs = dict(kwargs, **path_parameters)

            return execute_function(self.logger, function_name, **kwargs)
