from apps.core.services.error_manager import ErrorManager
from apps.core.services.error_policies import (
    ClasseErroreSenzaStatus,
    ErrorPolicy,
    ErrorPolicyRegistry,
)
from apps.core.services.error_translator import ApiError, ErrorTranslator
from apps.core.services.service_errors import ServiceError

# I tre moduli-dato del registro errori (`error_policies_generated`,
# `error_ui_overrides`, `error_messages_fallback`) NON si esportano qui: si
# leggono attraverso `ErrorPolicyRegistry`, che e' il punto unico. Chi importa
# il dizionario direttamente si porta via il ripiego e la derivazione.
__all__ = [
    "ApiError",
    "ErrorTranslator",
    "ServiceError",
    "ErrorManager",
    "ErrorPolicy",
    "ErrorPolicyRegistry",
    "ClasseErroreSenzaStatus",
]
