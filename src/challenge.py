from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import hashlib
import yaml


@dataclass
class Challenge:
    key: str
    category: str
    name: str
    description: str | None
    difficulty: str | None
    status: str | None
    wave: str | None
    authors: List[str]
    tags: List[str]
    challenge_path: str
    file_hash: str

    @staticmethod
    def collect_from_repo(challenge_root: Path, repo_path: Path) -> List["Challenge"]:
        challenges: List["Challenge"] = []
        if not challenge_root.is_dir():
            return challenges

        for challenge_file in challenge_root.rglob("challenge.yml"):
            try:
                metadata = yaml.safe_load(challenge_file.read_text())
            except yaml.YAMLError:
                continue

            if not isinstance(metadata, dict):
                continue

            relative = challenge_file.parent.relative_to(repo_path)
            relative_parts = relative.parts
            if len(relative_parts) < 2:
                continue
            category = relative_parts[1]
            name = relative_parts[-1]

            key = metadata.get("key")
            if not key:
                continue

            description_value = metadata.get("description")
            description = (
                description_value.strip()
                if isinstance(description_value, str)
                else None
            )

            def to_list(value: Any) -> List[str]:
                if isinstance(value, list):
                    return [str(item).strip() for item in value if item]
                if isinstance(value, str):
                    item = value.strip()
                    return [item] if item else []
                return []

            authors = to_list(metadata.get("authors"))
            tags = to_list(metadata.get("tags"))

            difficulty_value = metadata.get("difficulty")
            difficulty = str(difficulty_value).strip() if difficulty_value else None

            status_value = metadata.get("status")
            status = str(status_value).strip() if status_value else None

            wave_value = metadata.get("wave")
            wave = str(wave_value).strip() if wave_value else None

            challenges.append(
                Challenge(
                    key=key,
                    category=category,
                    name=name,
                    description=description,
                    difficulty=difficulty,
                    status=status,
                    wave=wave,
                    authors=authors,
                    tags=tags,
                    challenge_path=str(relative),
                    file_hash=hashlib.sha256(challenge_file.read_bytes()).hexdigest(),
                )
            )

        return challenges
