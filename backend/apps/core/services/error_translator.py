# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Traduzione errori applicativi.
# ------------------------------------------------------------


import re
from dataclasses import asdict, dataclass
from typing import Any

from django.conf import settings
from django.db import DatabaseError

from apps.core.services.db_error_fields import (
    Bersaglio,
    app_error_code_from_text,
    bersagli_envelope,
    diagnostica_db,
)
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.services.request_context import get_request_id
from apps.core.services.service_errors import E_VALIDATION_INPUT, ServiceError

# Translator centralizzato: converte errori Python/DB in payload API uniforme.


# Il nome di un campo e' un identificatore scritto nel codice del service
# (`require_string(payload, "nome")`), non un dato dell'utente. Il filtro qui
# sotto non e' quindi una difesa da un attacco: e' il guard che impedisce a un
# chiamante che passasse una chiave dinamica di far rimbalzare al client
# qualcosa che l'utente ha scritto. Costa una regex e toglie la domanda.
_FIELD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.\-]{0,63}$")


# Scopo: un nome di campo in tupla, o None. ⚠️ Dal 2026-08-24 il punto che
#        valorizzava `fields` dal database non passa piu' di qui (legge
#        `DiagnosticaDb.fields`): resta il solo lato Python, e la funzione
#        resta perche' e' li' che la convenzione `context={"field": ...}` si
#        traduce in envelope.
def _campi(nome: str | None) -> tuple[str, ...] | None:
    return (nome,) if nome else None


@dataclass(frozen=True)
class ApiError:
    code: str
    message: str
    detail: str | None = None
    technical_message: str | None = None
    hint: str | None = None
    tx_id: str | None = None
    retryable: bool = False
    ui_action: str | None = None
    # I campi del form che l'operatore deve correggere. E' l'informazione senza
    # la quale `ui_action = highlight_form_fields` non e' azionabile: dice
    # «evidenzia il campo» senza dire quale. Vedi §12 del piano.
    fields: tuple[str, ...] | None = None
    # ⭐ IL BERSAGLIO: su QUALE cosa l'errore e' successo, dal 2026-08-24.
    # `fields` dice quale campo correggere DENTRO la pagina in cui l'operatore
    # gia' si trova; `targets` dice a quale ALTRA cosa deve andare — ed e' la
    # differenza fra evidenziare un input e disegnare un gesto.
    # Brief: `brief-db-bersaglio-errore.md` (§2, §4.4, §7-bis).
    targets: tuple[Bersaglio, ...] | None = None

    # Scopo: Converte ServiceError in struttura dict serializzabile per envelope API.
    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # `fields` come lista: un JSON non ha le tuple, e il client legge un array.
        if data.get("fields") is not None:
            data["fields"] = list(data["fields"])
        # ⚠️ `asdict` scende ricorsivamente nelle dataclass annidate, quindi
        # `targets` qui e' gia' una lista di dict — ma con le chiavi ITALIANE
        # dell'oggetto interno (`tipo`/`id`). L'envelope parla inglese, e la
        # traduzione vive in un posto solo: `bersagli_envelope`.
        # ⚠️ Si riassegna SEMPRE, anche a `None`: una tupla VUOTA passerebbe il
        # `is not None` e finirebbe nell'envelope come `"targets": []`, cioe'
        # una chiave presente che non dice niente. Il filtro qui sotto la toglie
        # solo se e' None.
        data["targets"] = bersagli_envelope(self.targets)
        return {k: v for k, v in data.items() if v is not None}


class ErrorTranslator:
    """Traduce eccezioni applicative/DB in un envelope errore coerente per le API."""

    # Scopo: Traduce una eccezione in envelope API pubblico applicando policy e sanitizzazione dettagli.
    @staticmethod
    def to_api_error(exc: Exception) -> ApiError:
        # Errori applicativi standard: passa codice/messaggio senza perdere metadati.
        if isinstance(exc, ServiceError):
            return ErrorTranslator._apply_policy(
                ApiError(
                code=exc.code,
                message=exc.message,
                detail=exc.detail or str(exc),
                hint=exc.hint,
                tx_id=exc.tx_id,
                retryable=exc.retryable,
                # ⚠️ PRECEDENZA: il `context={"field": ...}` scritto a mano dal
                # service vince sul campo derivato dal database. E' l'esplicito
                # del chiamante contro un ripiego — la stessa regola che il DB
                # applica dando la precedenza a `campo` su `parametro`.
                fields=ErrorTranslator._campi_da_correggere(exc.context) or exc.fields,
                targets=exc.targets,
                )
            )

        # Input non valido (query param malformati, parsing fallito): 400.
        if isinstance(exc, (ValueError, TypeError)):
            message = str(exc) or "Input non valido."
            return ErrorTranslator._apply_policy(ApiError(
                code=E_VALIDATION_INPUT,
                message=message,
                detail=message,
                retryable=False,
            ))

        # Errori DB: prova a estrarre dettaglio tecnico (DETAIL/HINT/sqlstate).
        if isinstance(exc, DatabaseError):
            return ErrorTranslator._apply_policy(ErrorTranslator._from_database_error(exc))

        message = str(exc) or "Errore non gestito."
        return ErrorTranslator._apply_policy(ApiError(
            code="E_GENERICO",
            message=message,
            detail=message,
            retryable=False,
        ))

    # Scopo: Risolve lo status HTTP finale da codice errore e policy applicate.
    @staticmethod
    def get_http_status(api_error: ApiError) -> int:
        return ErrorPolicyRegistry.resolve(api_error.code).http_status

    # Scopo: ⭐ I campi del form che l'operatore deve correggere, presi dal
    #        `context` del ServiceError. Passo 1 del §12 del piano BE.
    #
    #        ⚠️ SI LEGGE SOLO LA CHIAVE `field`, e non tutte le chiavi del
    #        context. La differenza decide se il dato e' vero o rumore: il
    #        `context` e' una borsa diagnostica che finisce in `dbops.error_log`
    #        — dentro ci sono anche `lotto_id`, `contratto_id`, `order_dir`, che
    #        NON sono campi di un form. Mandarli tutti direbbe al frontend di
    #        evidenziare cose che sull'ecran non esistono.
    #        La convenzione `context={"field": <nome>}` esiste gia' in **114
    #        punti di chiamata**, validator centralizzati compresi: qui non se ne
    #        inventa una, se ne trasmette una che c'era e si fermava al log.
    #
    #        ⚠️ E si manda il NOME, mai il valore: nel context c'e' anche il dato
    #        che l'utente ha scritto, e non ha nessun motivo di tornare indietro.
    @staticmethod
    def _campi_da_correggere(context: dict[str, Any] | None) -> tuple[str, ...] | None:
        if not context:
            return None
        nome = context.get("field")
        if not isinstance(nome, str) or not _FIELD_RE.match(nome):
            return None
        return _campi(nome)

    # Scopo: Applica policy error code -> status/retry/hint al payload errore.
    @staticmethod
    def _apply_policy(api_error: ApiError) -> ApiError:
        policy = ErrorPolicyRegistry.resolve(api_error.code)
        expose_technical = getattr(settings, "API_EXPOSE_TECHNICAL_DETAILS", False)
        is_technical = ErrorTranslator.is_technical_code(api_error.code)
        detail = ErrorTranslator._sanitize_public_detail(api_error)
        # `message` resta sempre business/safe per stabilita` client/UI.
        public_message = policy.user_message if is_technical else (api_error.message or policy.user_message)
        # In debug esponi il dettaglio tecnico reale, mantenendo `message` business.
        technical_message = (
            (api_error.detail or api_error.message)
            if is_technical and expose_technical
            else None
        )
        return ApiError(
            code=api_error.code,
            message=public_message,
            detail=detail,
            technical_message=technical_message,
            # ⛔ SU UN CODICE TECNICO IL SUGGERIMENTO NON ESCE (2026-09-09), ed
            # e' la condizione perche' il campo sia MOSTRABILE a video: da oggi
            # il frontend lo rende sotto il messaggio d'errore.
            #
            # `hint` e' la `soluzione` che il team DB scrive a catalogo PER IL
            # CODICE sollevato, e `script.fn_log_and_raise_error` la consegna nel
            # canale `HINT` dell'eccezione. Su questi tre codici quel canale non
            # porta la soluzione di nessun catalogo: `E_DATABASE` ed `E_GENERICO`
            # nascono da un'eccezione che di dominio non e', quindi li' `HINT` e'
            # quello che PostgreSQL scrive per lo SVILUPPATORE, in inglese
            # («Perhaps you meant to reference the column ...»).
            #
            # ⭐ La misura e' `is_technical` e NON lo status, e la differenza e' di
            #    modello, non di prudenza. Un codice di CLASSE `TECNICO` e'
            #    registrato a catalogo, quindi una `soluzione` scritta apposta ce
            #    l'ha — «segnalare al supporto citando il request_id» e' proprio
            #    cio' che serve a chi legge un 500 — e toglierla butterebbe via
            #    una frase scritta per quel caso. ⇒ Qui la regola diverge da
            #    quella del bersaglio qui sotto, che invece guarda ANCHE lo
            #    status: un gesto su un 500 non c'e', una frase si'.
            #
            # ⚠️ La regola in una riga: *il suggerimento accompagna il messaggio;
            #    dove il messaggio non e' piu' quello dell'errore — qui lo
            #    sostituisce `policy.user_message` e il dettaglio lo sostituisce
            #    `_sanitize_public_detail` — il suggerimento accompagnerebbe
            #    un'altra frase.*
            hint=None if is_technical else api_error.hint,
            tx_id=api_error.tx_id,
            retryable=api_error.retryable,
            ui_action=policy.ui_action,
            # ⚠️ Va ricopiato: questo metodo COSTRUISCE UN ApiError NUOVO, e
            # quello che non si nomina qui sparisce. E' il punto in cui il campo
            # si perdeva prima ed e' il punto in cui si perderebbe di nuovo.
            fields=api_error.fields,
            # ⛔ SUL 5xx IL BERSAGLIO NON ESCE. E' la regola Q-E del brief letta
            # dal lato che consegna: il bersaglio e' un GESTO per l'operatore, e
            # dove il guasto non e' suo non c'e' nessun gesto da offrirgli.
            #
            # ⚠️ DUE MISURE, E SERVONO ENTRAMBE — la prima stesura ne usava una
            # sola ed era sbagliata. Non sono ridondanti: rispondono a domande
            # diverse, e nessuna delle due contiene l'altra.
            #   · `policy.http_status >= 500` e' la regola Q-E vera, quella che
            #     parla della CLASSE di catalogo: i codici di classe `TECNICO`
            #     sono **79**, piu' `NON_DISPONIBILE` (501) ed `ERRORE_ESTERNO`
            #     (502), che hanno la stessa proprieta'. `policy` e' gia' stata
            #     risolta qui sopra, quindi non costa niente.
            #   · `is_technical` e' l'insieme di TRE codici scritti a mano che
            #     decide se NASCONDERE il dettaglio. Offrire un gesto su un
            #     errore di cui rifiutiamo di mostrare il dettaglio sarebbe
            #     incoerente — e sono codici che di classe non sono `TECNICO`:
            #     misurato, `E_DATABASE` ed `E_PIPELINE` sono `DATO_ERRATO`,
            #     cioe' **400**. (E' un'incoerenza di catalogo che precede
            #     questo cantiere: qui non si corregge, si tiene solo conto che
            #     lo status da solo non li prende.)
            # ⛔ Con la sola prima misura il bersaglio sarebbe uscito su
            #    `E_DATABASE`; con la sola seconda, su 76 codici `TECNICO` su 79.
            targets=(
                None
                if is_technical or policy.http_status >= 500
                else api_error.targets
            ),
        )

    # Scopo: Sanitizza i dettagli tecnici non esponibili in risposta pubblica.
    @staticmethod
    def _sanitize_public_detail(api_error: ApiError) -> str | None:
        # Per errori tecnici non esporre stack SQL/PLpgSQL al client, anche in debug:
        # in debug il dettaglio tecnico va in `technical_message`.
        if ErrorTranslator.is_technical_code(api_error.code):
            request_id = get_request_id()
            if request_id:
                return f"Dettaglio tecnico non esposto. Usa request_id={request_id} per supporto."
            return "Dettaglio tecnico non esposto. Usa request_id per supporto."

        return api_error.detail

    # Scopo: Determina se il codice errore appartiene alla categoria tecnica/non funzionale.
    @staticmethod
    def is_technical_code(code: str) -> bool:
        return code in {"E_PIPELINE", "E_DATABASE", "E_GENERICO"}

    # Scopo: Converte eccezioni DB in ApiError coerente con il contratto errori core.
    # Cerca codici errore applicativi (E_*) nel messaggio DB per preservare
    # i codici lanciati da fn_log_and_raise_error e applicare le policy corrette.
    @staticmethod
    def _from_database_error(exc: DatabaseError) -> ApiError:
        # message_primary contiene solo il messaggio RAISE, senza stack PL/pgSQL
        raw_message = str(exc) or "Errore durante l'operazione database."
        # ⭐ UNA lettura sola (BB `diagnostica_db`, 2026-08-24): questo metodo
        #    era l'unico dei cinque punti di traduzione a leggere TUTTO — ed e'
        #    anche l'unico che quasi nessun errore percorre, perche' vale solo
        #    per il `DatabaseError` che arriva NUDO al middleware. Da qui in poi
        #    leggono tutti la stessa cosa.
        diag = diagnostica_db(exc, text=raw_message)

        # Codice di dominio: campo strutturato per primo (`CONSTRAINT` su
        # SQLSTATE P0001, dal 2026-08-05), testo come ripiego per i RAISE
        # diretti che non passano da `script.fn_log_and_raise_error`.
        # Vedi `apps/core/services/db_error_fields.py` per il contratto.
        if diag.codice:
            code = diag.codice
            # Per errori applicativi usa il messaggio pulito (senza stack)
            message = diag.messaggio or raw_message
        else:
            code = "E_DATABASE_RETRYABLE" if diag.retryable else "E_DATABASE"
            message = raw_message

        return ApiError(
            code=code,
            message=message,
            detail=diag.detail,
            hint=diag.hint,
            retryable=diag.retryable,
            # Il campo da correggere, se il DB l'ha detto: `RAISE ... USING
            # COLUMN` nelle funzioni PL/pgSQL, oppure PostgreSQL stesso su una
            # violazione NOT NULL.
            fields=diag.fields,
            # Il bersaglio, se il DB l'ha detto: `RAISE ... USING DATATYPE`,
            # forma `TIPO:id[,TIPO:id]`. Contratto valido solo dentro `P0001`.
            targets=diag.bersagli or None,
        )

    # Scopo: Estrae un codice errore applicativo E_* dal messaggio di eccezione DB.
    #        Delegatore su `db_error_fields.app_error_code_from_text`: e' il solo
    #        RIPIEGO testuale, la lettura primaria e' il campo strutturato in
    #        `_from_database_error`. Resta come metodo perche' e' chiamato dai
    #        test e da chi ha in mano il testo e non l'eccezione.
    @staticmethod
    def _extract_app_error_code(message: str) -> str | None:
        return app_error_code_from_text(message)
