#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility entrypoint for deepseek_api_client.py."""

from deepseek_api_client import DeepSeekChatApp, DeepSeekClient, DeepSeekV4Client, launch_gui, main


__all__ = [
    "DeepSeekChatApp",
    "DeepSeekClient",
    "DeepSeekV4Client",
    "launch_gui",
    "main",
]


if __name__ == "__main__":
    main()
