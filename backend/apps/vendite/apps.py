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
            ddt_document_context_builder,
            fattura_document_context_builder,
            offerta_document_context_builder,
            ordine_document_context_builder,
            preventivo_document_context_builder,
        )

        # Registra gli handler flusso del dominio vendite nel registry pratiche.
        # Lazy qui (non a livello modulo) per non creare la dipendenza di import
        # pratiche→vendite: e' vendite a registrarsi su pratiche al boot.
        from apps.pratiche.services.handler_registry import register_handler
        from apps.vendite.handlers.post_smistamento_handler import PostSmistamentoHandler

        # NB: l'handler `vendita.accetta_preventivo` e' stato RITIRATO (GUIDA D4,
        # inversione handler->proiezione): «Accetta/Rifiuta» in-pratica agisce sul
        # documento standalone (`preventivi_service.cambia_stato_da_pratica`) e il
        # milestone avanza da solo via trigger DB `pratiche.fn_reconcile_sorgente`.
        # Nessun binding handler-eventi da registrare per l'accettazione preventivo.
        # Handler di completamento SMISTAMENTO (COMPLETATO + esito MERCE_PRESENTE,
        # bivio-per-esito rev.3): merce-only, aggancia l'ordine merce alla pratica
        # come sorgente COLLEGATO. NON crea flussi a valle: 9013/9014 sono
        # obbligatori-su-ramo e compaiono via roadmap/prerequisiti.
        register_handler("vendita.post_smistamento", PostSmistamentoHandler)

        # Registra l'handler del job coda-lavori FATTURAZIONE_GIRO (C-3): il
        # giro di fatturazione on-demand. Dispatch controllato
        # (handler_code=fatturazione_giro_default → funzione), come i context
        # builder: registrazione esplicita al boot, mai auto-discovery.
        from apps.vendite.services.fatturazione_giro_handler import (
            register as register_fatturazione_giro,
        )
        register_fatturazione_giro()
