import re
from pathlib import Path
from typing import List


def parse_steps_from_text(raw_text: str) -> List[str]:
    lines = [line.strip() for line in raw_text.splitlines()]
    lines = [line for line in lines if line]
    steps: List[str] = []
    step_pattern = re.compile(r"^step\s*\d+\s*:\s*(.+)$", re.IGNORECASE)
    for line in lines:
        match = step_pattern.match(line)
        if match:
            steps.append(match.group(1).strip())
        else:
            steps.append(line)
    return steps


def read_steps_file(file_path: Path) -> List[str]:
    content = file_path.read_text(encoding="utf-8")
    return parse_steps_from_text(content)


