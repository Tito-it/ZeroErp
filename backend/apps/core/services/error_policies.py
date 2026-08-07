# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il registro delle policy errore — ma non piu' l'elenco: le REGOLE.
#        Da qui si risponde a «che status HTTP e che reazione della pagina
#        corrisponde a questo codice errore», derivandoli dalla CLASSE del
#        codice invece che scrivendoli uno per uno.
#
#        COM'ERA, FINO AL 2026-08-07. Un dizionario di 659 voci scritte a mano,
#        ognuna con status, ui_action e messaggio. Il difetto non era la
#        dimensione: era che lo status di un codice NON ERA DECIDIBILE da
#        nessuna parte se non riscrivendolo, e chi non lo riscriveva prendeva un
#        ripiego silenzioso a 400. E' il filone raccontato in
#        `docs/it/dev/work-in-progress/brief-db-be-classe-codici-errore.md`.
#
#        COM'E' ORA. Il significato («che cosa E' questo errore») e' un dato del
#        database — `config.codici_errore.classe`, otto valori — e arriva qui
#        dentro `error_policies_generated.py`. Lo status e la ui_action si
#        DERIVANO da quella classe con le due tabelle di questo file: otto righe
#        invece di 659.
#
#        I QUATTRO MODULI, separati per QUANDO CAMBIANO e non per contenuto:
#          error_policies_generated.py  codice -> classe (658)   a ogni seed DB
#          error_policies.py (questo)   classe -> status, ui     quasi mai
#          error_ui_overrides.py        le 176 ui fuori default  scelte di UI
#          error_messages_fallback.py   i messaggi senza %s      finche' esistono
#
#        IL CANCELLO CHE GUARDA QUESTO REGISTRO. Sui codici errore devono andare
#        d'accordo tre elenchi: il catalogo `config.messaggi_errore`, i codici
#        usati dal Python, e la classe di ciascuno. Il terzo lato — i codici che
#        il DB puo' nominare contro questo registro — e' presidiato da
#        `apps/core/tests/test_error_codes_db_policy_guardrail.py`; il lato dei
#        punti di chiamata da `test_error_codes_declared_guardrail.py`. I due
#        insiemi si sfilano per vie diverse (nel 2026-08-04 erano sfilati di 28
#        codici) e servono entrambi.
# ------------------------------------------------------------


from dataclasses import dataclass

from apps.core.services.error_messages_fallback import USER_MESSAGE_FALLBACK
from apps.core.services.error_policies_generated import CLASSE_PER_CODICE
from apps.core.services.error_ui_overrides import UI_ACTION_OVERRIDE

# ── Il vocabolario delle classi ──────────────────────────────────────────────
# Otto valori, gli stessi di `config.classi_errore`. Non sono inventati: vengono
# dalle 659 decisioni gia' prese nel cantiere del terzo lato.
CLASSI_ERRORE: frozenset[str] = frozenset(
    {
        "DATO_ERRATO",
        "CONFLITTO_STATO",
        "NON_TROVATO",
        "TECNICO",
        "NON_PERMESSO",
        "NON_ESEGUIBILE",
        "NON_DISPONIBILE",
        "AVVISO",
    }
)

# ── classe -> status HTTP ────────────────────────────────────────────────────
# La mappa sta lato backend e non lato DB perche' e' TRASPORTO, non dominio: il
# database non deve sapere cosa sia un 409. Gli status vengono da RFC 9110, non
# da una convenzione di progetto (api.md §Gli status in uso).
#
# ⚠️ `AVVISO` NON C'E', E NON E' UNA DIMENTICANZA. Un avviso (famiglia `W_`) non
# rifiuta niente: il DB lo scrive nel diario con `fn_log_error_only` e non lo
# solleva mai, quindi non raggiunge nessun client e non ha uno status da avere.
# Se un codice `AVVISO` arriva fin qui, qualcosa a monte l'ha sollevato: si
# solleva `ClasseErroreSenzaStatus` invece di inventare una risposta. Vedi il
# perche' nel commento di `_deriva`.
HTTP_PER_CLASSE: dict[str, int] = {
    "DATO_ERRATO": 400,
    "CONFLITTO_STATO": 409,
    "NON_TROVATO": 404,
    "TECNICO": 500,
    "NON_PERMESSO": 403,
    "NON_ESEGUIBILE": 422,
    "NON_DISPONIBILE": 501,
}

# ── classe -> ui_action di default ───────────────────────────────────────────
# ⚠️ La ui_action NON si deriva dalla classe, e il numero conta: restano 176
# override su 658. Su `DATO_ERRATO`, la classe piu' numerosa, il default e' un
# lancio di moneta — 117 contro 117 — perche' il discriminante non e' la classe
# ma DOVE manca il dato: sul form in corso (campo evidenziato) o sull'entita'
# collegata (banner). E' un'informazione che la classe non porta.
# Il default scelto e' il banner: promettere un campo da evidenziare che non
# esiste e' peggio del contrario.
UI_ACTION_PER_CLASSE: dict[str, str] = {
    "DATO_ERRATO": "show_error_banner",
    "CONFLITTO_STATO": "show_error_banner",
    "NON_TROVATO": "show_empty_state",
    "TECNICO": "show_error_banner",
    "NON_PERMESSO": "show_error_banner",
    "NON_ESEGUIBILE": "show_error_banner",
    "NON_DISPONIBILE": "show_error_banner",
}

# ── I cinque codici fuori dal vocabolario di dominio ─────────────────────────
# Non sono «senza classe»: sono fuori dal percorso che la classe governa. I
# quattro 401 li costruisce `JwtAuditMiddleware` e non passano dall'exception
# handler; il 502 e' l'unico caso in cui un provider ESTERNO risponde male, che
# e' letteralmente la definizione RFC del 502 (normalizzarlo a 500 perderebbe
# l'unica informazione utile leggendo i log).
# A catalogo prendono `TECNICO` con la ragione in `note`; qui lo status resta
# scritto a mano, quindi la classe che il DB assegnera' loro non cambia la
# risposta.
HTTP_PER_CODICE: dict[str, int] = {
    "E_JWT_SENZA_IDENTITA": 401,
    "E_IDENTITA_NON_ATTIVA": 401,
    "E_AUTHENTICATION_FAILED": 401,
    "E_NOT_AUTHENTICATED": 401,
    "E_AI_PROVIDER_ERROR": 502,
}

# Ripiego di ultima istanza sul messaggio: un codice registrato senza voce in
# `USER_MESSAGE_FALLBACK`. Non dovrebbe accadere — c'e' un test che lo presidia —
# e se accade e' meglio una frase neutra che un KeyError sul percorso d'errore.
_MESSAGGIO_MANCANTE = "Errore durante l'operazione."


class ClasseErroreSenzaStatus(RuntimeError):
    """La classe di un codice non ha uno status HTTP: non si ripiega, si solleva."""


# Registro centrale mapping errore -> comportamento API/UI.


@dataclass(frozen=True)
class ErrorPolicy:
    code: str
    http_status: int
    ui_action: str
    user_message: str


class ErrorPolicyRegistry:
    """Policy centralizzate per evitare mapping duplicato nei moduli API."""

    # Memoria delle policy gia' derivate: `resolve` sta sul percorso di ogni
    # errore, e la derivazione e' pura (stessi input -> stesso output).
    _CACHE: dict[str, ErrorPolicy] = {}

    # Scopo: Deriva la policy di un codice REGISTRATO dalla sua classe.
    #        ⚠️ Qui vive la garanzia del brief §4.2: classe senza status mappato
    #        => eccezione, MAI un ripiego. Prima di questo passo `resolve` non
    #        falliva mai e un avviso sfuggito al cancello sarebbe diventato un
    #        500 tecnico col messaggio soppresso — cioe' esattamente il difetto
    #        `E_DATABASE` da cui e' nato tutto il filone. La garanzia sta in
    #        queste due righe: senza, non c'e'.
    @classmethod
    def _deriva(cls, code: str, classe: str) -> ErrorPolicy:
        http_status = HTTP_PER_CODICE.get(code) or HTTP_PER_CLASSE.get(classe)
        ui_action = UI_ACTION_OVERRIDE.get(code) or UI_ACTION_PER_CLASSE.get(classe)
        if http_status is None or ui_action is None:
            raise ClasseErroreSenzaStatus(
                f"il codice {code} ha classe {classe!r}, che non ha "
                f"{'uno status HTTP' if http_status is None else 'una ui_action di default'} "
                f"in error_policies.py. Se e' un avviso (famiglia W_) non doveva "
                f"essere sollevato: si scrive nel log, non si alza. Se e' una "
                f"classe nuova, va aggiunta alle tabelle di questo modulo."
            )
        return ErrorPolicy(
            code=code,
            http_status=http_status,
            ui_action=ui_action,
            user_message=USER_MESSAGE_FALLBACK.get(code, _MESSAGGIO_MANCANTE),
        )

    # Scopo: Risolve la policy per un codice errore. Per codici applicativi
    # (E_*) non registrati usa fallback 400 con messaggio dal DB, non 500 generico.
    #
    # ⚠️ I DUE RIPIEGHI RESTANO, e non e' una svista. Sono cio' che tiene in
    # piedi i codici NUOVI che il team DB sta creando (lo split di
    # `E_VALIDAZIONE`) finche' il generatore del passo B-5 non e' in servizio:
    # un codice appena seminato a catalogo non ha ancora una classe qui dentro.
    # Il momento di ridiscuterli e' quando il file generato arriva davvero dal
    # DB, non prima.
    @classmethod
    def resolve(cls, code: str) -> ErrorPolicy:
        policy = cls._CACHE.get(code)
        if policy is not None:
            return policy

        classe = CLASSE_PER_CODICE.get(code)
        if classe is not None:
            policy = cls._deriva(code, classe)
            cls._CACHE[code] = policy
            return policy

        # Codici applicativi E_* non registrati: errore business (400), non tecnico (500)
        if code.startswith("E_") and code != "E_GENERICO":
            return ErrorPolicy(
                code=code,
                http_status=400,
                ui_action="show_error_banner",
                user_message="Errore di validazione.",
            )
        return cls.resolve("E_GENERICO")

    # Scopo: Verifica se un codice errore ha una policy registrata, cioe' se ha
    #        una classe dichiarata. E' la domanda che fa il cancello del terzo
    #        lato: «questo codice, che il DB puo' nominare, e' stato deciso?».
    @classmethod
    def has(cls, code: str) -> bool:
        return code in CLASSE_PER_CODICE

    # Scopo: La classe di un codice, o None se non registrato. E' il dato che
    #        distingue un guasto da un rifiuto legittimo — la domanda che
    #        `dbops.error_log` non sa ancora fare (brief §12).
    @classmethod
    def classe_di(cls, code: str) -> str | None:
        return CLASSE_PER_CODICE.get(code)

    # Scopo: L'insieme dei codici registrati. Serve ai presidi che contano il
    #        registro per accorgersi se la misura si e' degradata.
    @classmethod
    def codici_registrati(cls) -> frozenset[str]:
        return frozenset(CLASSE_PER_CODICE)


# `E_GENERICO` e' il pavimento di tutto il percorso d'errore: se non e'
# registrato, il ripiego finale di `resolve` non ha dove atterrare. Meglio
# accorgersene all'avvio che sul primo errore non gestito in produzione.
if "E_GENERICO" not in CLASSE_PER_CODICE:  # pragma: no cover — invariante di boot
    raise ClasseErroreSenzaStatus(
        "E_GENERICO non e' in CLASSE_PER_CODICE: il ripiego finale di "
        "ErrorPolicyRegistry.resolve non ha dove atterrare."
    )
