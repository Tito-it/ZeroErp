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

        # Handler del job NOTIFICA_DIGEST_MUTO (2026-09-11): la guardia
        # reciproca del digest dei presidi — lo accoda il job pgAgent
        # `guardiano_digest`, lo spedisce il drenatore. Il tipo di coda e'
        # seedato spento finche' questa riga non e' in release.
        from apps.core.services.coda_lavori.notifica_digest_muto_handler import (
            register as register_notifica_digest_muto,
        )
        register_notifica_digest_muto()

        # Handler del job ESEGUI_PROCESSO (2026-09-15): «Esegui ora» su una
        # sveglia di deploy — lo accoda il verbo `processi/<codice>/esegui-ora/`
        # con l'identita' di chi preme, lo esegue il drenatore come
        # sottoprocesso `run-command.sh <comando>`. Il tipo di coda e' seedato
        # spento finche' questa riga non e' in release (brief §10.4).
        from apps.core.services.coda_lavori.esegui_processo_handler import (
            register as register_esegui_processo,
        )
        register_esegui_processo()

        # Estensioni drf-spectacular: si registrano per IMPORT, alla definizione
        # della sottoclasse. Senza questa riga lo schema OpenAPI non dichiara
        # nessuno `securityScheme` e descrive l'intera API come anonima
        # (607 avvisi W001 il 2026-09-09). Vedi `api/openapi_extensions.py`.
        # ⚠️ `noqa: F401` e' il caso in cui un import "inutilizzato" e' il
        #    lavoro: serve l'effetto collaterale, non il nome.
        from apps.core.api import openapi_extensions  # noqa: F401
