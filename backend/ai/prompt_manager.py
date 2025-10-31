from __future__ import annotations

from typing import Dict


class PromptManager:
    def __init__(self):
        self._templates: Dict[str, str] = {}

    def register(self, name: str, template: str) -> None:
        self._templates[name] = template

    def render(self, name: str, **kwargs) -> str:
        tpl = self._templates.get(name, "")
        return tpl.format(**kwargs)


