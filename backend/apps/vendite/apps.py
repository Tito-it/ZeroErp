from django.apps import AppConfig


class VenditeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.vendite"

    # Scopo: Hook di boot Django. Registra esplicitamente i context
    #        builder documentali del dominio vendite (Tranche J motore
    #        documentale). L'import scatena `register_builder(...)` a
    #        livello modulo, popolando il registry centrale di
    #        `apps.documenti.services.context_builders`. Nessuna
    #        auto-discovery via signal — pattern coerente con le
    #        decisioni di progetto e con `pipeline_task_registry_impl`.
    def ready(self) -> None:
        # Import locale per evitare side-effects al parse di apps.py.
        # `noqa: F401` — l'import e' richiesto per i side-effects di
        # registrazione, non per l'uso del simbolo.
        from apps.vendite.services import (  # noqa: F401
            contratto_document_context_builder,
            preventivo_document_context_builder,
        )
