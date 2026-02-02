class PipelineError(Exception):
    """Base exception for vendite pipeline services."""


class PipelineValidationError(PipelineError):
    """Raised when required pipeline inputs are missing or invalid."""


class PipelineTaskNotAllowedError(PipelineError):
    """Raised when a pipeline task requests a non-whitelisted function."""


class PipelineTaskNotImplementedError(PipelineError):
    """Raised when a pipeline task is not yet implemented in Django."""
