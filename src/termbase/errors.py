class TermBaseError(Exception):
    exit_code = 1


class ConfigValidationError(TermBaseError):
    exit_code = 2


class AssetValidationError(TermBaseError):
    exit_code = 3


class LLMRequestError(TermBaseError):
    exit_code = 4


class OpenAIRequestError(LLMRequestError):
    exit_code = 4


class ImageGenerationError(TermBaseError):
    exit_code = 5


class GeminiRequestError(TermBaseError):
    exit_code = 6


class ImagenRequestError(TermBaseError):
    exit_code = 10


class OutputWriteError(TermBaseError):
    exit_code = 7


class AudioGenerationError(TermBaseError):
    exit_code = 8


class OverlayCompositionError(TermBaseError):
    exit_code = 9
