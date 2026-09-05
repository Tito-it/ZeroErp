from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    # Scopo: Hook di boot Django. Registra gli handler della coda lavori che
    #        appartengono a `core` — cioe' quelli il cui lavoro non e' di un
    #        dominio applicativo ma del framework.
    # ⚠️ Import LOCALE, non a livello modulo: `apps.py` viene letto prima che il
    #    registro delle app sia pronto, e un import in cima si tirerebbe dietro
    #    mezza applicazione al parse.
    def ready(self) -> None:
        # Handler del job CHIUSURA_SCADENZE (lotto 4): il lavoro che fino al
        # 2026-09-04 girava dentro il job pgAgent. Registrazione esplicita,
        # come per i due handler della fatturazione — mai auto-discovery.
        from apps.core.services.coda_lavori.chiusura_scadenze_handler import (
            register as register_chiusura_scadenze,
        )
        register_chiusura_scadenze()
