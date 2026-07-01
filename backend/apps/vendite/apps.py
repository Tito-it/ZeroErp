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
            offerta_document_context_builder,
            ordine_document_context_builder,
            preventivo_document_context_builder,
        )

        # Registra gli handler flusso del dominio vendite nel registry pratiche.
        # Lazy qui (non a livello modulo) per non creare la dipendenza di import
        # pratiche→vendite: e' vendite a registrarsi su pratiche al boot.
        from apps.pratiche.services.handler_registry import register_handler
        from apps.vendite.handlers.accetta_preventivo_handler import AccettaPreventivoHandler
        from apps.vendite.handlers.post_smistamento_handler import PostSmistamentoHandler
        from apps.vendite.handlers.push_preventivo_handler import PushPreventivoHandler

        register_handler("vendita.push_preventivo", PushPreventivoHandler)
        # Handler di completamento (template_flussi_handler_eventi): accetta il
        # preventivo collegato al COMPLETATO+POSITIVO di APPROVAZIONE_CLIENTE.
        register_handler("vendita.accetta_preventivo", AccettaPreventivoHandler)
        # Handler di completamento SMISTAMENTO (COMPLETATO + esito MERCE_PRESENTE,
        # bivio-per-esito rev.3): merce-only, aggancia l'ordine merce alla pratica
        # come sorgente COLLEGATO. NON crea flussi a valle: 9013/9014 sono
        # obbligatori-su-ramo e compaiono via roadmap/prerequisiti.
        register_handler("vendita.post_smistamento", PostSmistamentoHandler)
