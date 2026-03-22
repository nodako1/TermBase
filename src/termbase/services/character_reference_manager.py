from __future__ import annotations

from pathlib import Path

from termbase.errors import AssetValidationError
from termbase.models import CharacterReferenceSet, CharacterRoleReferences, ExpressionName, RoleName


EXPRESSIONS: tuple[ExpressionName, ...] = (
    "neutral",
    "happy",
    "smile",
    "surprised",
    "confused",
    "explaining",
    "serious",
    "thinking",
    "sad",
    "angry",
)

ROLES: tuple[RoleName, ...] = ("teacher", "student")


def _expected_files(role: RoleName) -> dict[ExpressionName, str]:
    return {expression: f"{role}_{index:02d}_{expression}.png" for index, expression in enumerate(EXPRESSIONS, start=1)}


def _validate_role(root_dir: Path, role: RoleName) -> CharacterRoleReferences:
    role_dir = root_dir / role
    if not role_dir.exists():
        raise AssetValidationError(f"missing role directory: {role_dir}")

    missing_files: list[str] = []
    expressions: dict[ExpressionName, Path] = {}
    for expression, file_name in _expected_files(role).items():
        file_path = role_dir / file_name
        if not file_path.exists():
            missing_files.append(file_name)
            continue
        if file_path.suffix.lower() != ".png":
            raise AssetValidationError(f"reference image must be PNG: {file_path}")
        expressions[expression] = file_path

    if missing_files:
        joined = ", ".join(missing_files)
        raise AssetValidationError(f"missing {role} reference files: {joined}")

    return CharacterRoleReferences(role=role, directory=role_dir, expressions=expressions)


def validate_character_references(root_dir: Path) -> CharacterReferenceSet:
    resolved_root_dir = root_dir.expanduser().resolve(strict=False)
    if not resolved_root_dir.exists():
        raise AssetValidationError(f"character reference root directory not found: {root_dir}")

    teacher = _validate_role(resolved_root_dir, "teacher")
    student = _validate_role(resolved_root_dir, "student")
    return CharacterReferenceSet(root_directory=resolved_root_dir, teacher=teacher, student=student)

