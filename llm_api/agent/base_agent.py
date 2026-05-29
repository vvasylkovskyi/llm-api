import logging
import os
import sys

import litellm

logger = logging.getLogger(__name__)

env_var_key = "ANTHROPIC_API_KEY"
api_key: str | None = os.getenv(env_var_key)

if not api_key:
    logger.fatal(f"Fatal Error: The '{env_var_key}' environment variable is missing.")
    sys.exit(1)


class BaseAgent:
    system_prompt: str = ""
    model: str = "anthropic/claude-haiku-4-5-20251001"

    async def run(self, input_message: str) -> str:
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": input_message})

        response = await litellm.acompletion(model=self.model, messages=messages)
        return response.choices[0].message.content
