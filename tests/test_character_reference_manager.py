from pathlib import Path

from termbase.services.character_reference_manager import validate_character_references


def test_validate_character_references_passes_for_current_assets() -> None:
    references = validate_character_references(Path("assets/character_refs"))

    assert references.root_directory.is_absolute()
    assert references.teacher.directory.name == "teacher"
    assert references.student.directory.name == "student"
    assert len(references.teacher.expressions) == 10
    assert len(references.student.expressions) == 10
