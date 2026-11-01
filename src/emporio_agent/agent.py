from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from emporio_agent.config import OPENAI_API_KEY, OPENAI_MODEL
from emporio_agent.prompts import SYSTEM_PROMPT
from emporio_agent.tools import TOOL_DEFINITIONS, dispatch_tool

MAX_TOOL_ROUNDS = 8


class EmporioAgent:
    def __init__(self) -> None:
        if not OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY não configurada. Copie .env.example para .env e defina a chave."
            )
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    def reset(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def chat(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})

        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=self.messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
            )
            msg = response.choices[0].message
            assistant_payload: dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
            if msg.tool_calls:
                assistant_payload["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            self.messages.append(assistant_payload)

            if not msg.tool_calls:
                return msg.content or ""

            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                tool_result = dispatch_tool(tc.function.name, args)
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_result,
                    }
                )

        return "Desculpe, não consegui concluir a consulta. Tente reformular ou fale com nosso atendimento humano."

    def export_transcript(self) -> str:
        lines = ["# Transcrição da sessão\n"]
        for m in self.messages:
            role = m["role"]
            if role == "system":
                continue
            if role == "tool":
                lines.append(f"\n**[tool result]**\n```\n{m.get('content', '')}\n```\n")
                continue
            content = m.get("content") or ""
            if m.get("tool_calls"):
                lines.append(f"\n**assistant** (chamou ferramentas)\n")
            else:
                lines.append(f"\n**{role}**\n{content}\n")
        return "".join(lines)
