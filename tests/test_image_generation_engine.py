from termbase.services.image_generation_engine import (
    _normalize_gemini_image_config,
    _normalize_gemini_seed,
    _normalize_openai_image_size,
)


def test_normalize_openai_image_size_returns_portrait_size() -> None:
    width, height = _normalize_openai_image_size(832, 1216)

    assert (width, height) == (1024, 1536)


def test_normalize_openai_image_size_returns_landscape_size() -> None:
    width, height = _normalize_openai_image_size(1536, 1024)

    assert (width, height) == (1536, 1024)


def test_normalize_gemini_image_config_returns_portrait_1k() -> None:
    aspect_ratio, image_size, dimensions = _normalize_gemini_image_config(832, 1216)

    assert aspect_ratio == "9:16"
    assert image_size == "1K"
    assert dimensions == (768, 1376)


def test_normalize_gemini_image_config_returns_landscape_2k() -> None:
    aspect_ratio, image_size, dimensions = _normalize_gemini_image_config(2000, 1100)

    assert aspect_ratio == "16:9"
    assert image_size == "2K"
    assert dimensions == (2752, 1536)


def test_normalize_gemini_seed_fits_signed_int32() -> None:
    assert _normalize_gemini_seed(2214068903) == 66585256