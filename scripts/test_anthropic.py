#!/usr/bin/env python3
"""Quick test to verify Anthropic API key works."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from afq.config import Config
from afq.utils import get_logger

import anthropic

log = get_logger("test_anthropic")


def main():
    cfg = Config.load()
    try:
        cfg.validate_stage3()
    except ValueError as e:
        log.error(f"Config error: {e}")
        log.info("Make sure .env has ANTHROPIC_API_KEY set.")
        return

    log.info(f"Testing Anthropic API with model: {cfg.claude_model}")
    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)

    message = client.messages.create(
        model=cfg.claude_model,
        max_tokens=200,
        messages=[
            {
                "role": "user",
                "content": (
                    "In one sentence, what is 'roundaboutness' in Austrian "
                    "economics as described by Eugen von Böhm-Bawerk?"
                ),
            }
        ],
    )

    response = message.content[0].text
    log.info(f"Response: {response}")
    log.info(f"Usage: {message.usage.input_tokens} in, {message.usage.output_tokens} out")
    log.info("Anthropic API connection verified.")


if __name__ == "__main__":
    main()
