# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I canali di incasso — da dove i soldi arrivano.
# Note: 🔴 Non e' un pannello di configurazione qualunque. Il **conto** che un
#       canale porta e' il punto da cui il database ricava DI CHI SONO i soldi
#       arrivati prima della fattura: con due partite IVA attive, un canale
#       agganciato al conto sbagliato non da' errore — sposta il denaro nel
#       perimetro di un altro emittente, e non se ne accorge nessuno.
#
#       ⭐ Per questo l'elenco dei conti da scegliere e' FILTRATO (BE-8): solo
#       quelli con `uso = 'INCASSO'` del soggetto. Il database rifiuta gli altri
#       con un errore parlante, ma un elenco che li propone fa sbagliare — e chi
#       sbaglia se ne accorge dopo aver compilato tutto il resto.
# ------------------------------------------------------------

import json
import logging
from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import validate_order_params, validate_pagination
from apps.core.services.payload_helpers import (
    PayloadValidator,
    make_db_errors_translator,
)
from apps.pagamenti.db.pagamenti_repository import (
    ENTI_INCASSO_SORT_COLUMNS,
    PagamentiRepository,
)
from apps.pagamenti.services._helpers import E_VALIDAZIONE, risposta_paginata

logger = logging.getLogger(__name__)

_FN = "pagamenti.enti_incasso_service"

# 🔴 **A catalogo manca un `E_ENTE_INCASSO_NON_TROVATO`**, e non se ne inventa
# uno: un codice non registrato non fallisce — `resolve()` lo manda su
# `E_GENERICO` e un 404 diventa un **500**. Nel progetto non esiste nemmeno un
# NON_TROVATO generico: ogni dominio ha il suo, ed e' la convenzione.
# ⚠️ Nel frattempo si usa il codice di validazione del dominio: la classe e'
# `DATO_ERRATO` (400) e non `NON_TROVATO` (404), quindi lo **stato HTTP e' meno
# preciso del vero** — ma il messaggio e' giusto e nessuna richiesta finisce in
# un errore di server. E' un ripiego dichiarato, non una scelta.
# 📮 Chiesto al team DB insieme ai seed: quando arriva, cambia SOLO questa riga
#    (e' lo stesso giro gia' fatto con `E_PAGAMENTI_VALIDATION`).
E_ENTE_NON_TROVATO = E_VALIDAZIONE

_PAYLOAD = PayloadValidator(validation_code=E_VALIDAZIONE, function_name=_FN)

_db_errors = make_db_errors_translator(
    fn_prefix=_FN,
    fallback_code=E_VALIDAZIONE,
    fallback_message="Violazione di vincolo su un canale di incasso.",
    unique_constraints={
        "uq_enti_incasso_codice": (E_VALIDAZIONE, "Codice canale gia' usato."),
    },
    fk_constraints={
        "fk_enti_incasso_centro_riscossione": (
            E_VALIDAZIONE,
            "Centro di riscossione non valido.",
        ),
        "fk_enti_incasso_conto_incasso": (
            E_VALIDAZIONE,
            "Conto di incasso non valido.",
        ),
        "fk_enti_incasso_soggetto_ruolo": (E_VALIDAZIONE, "Soggetto non valido."),
        "fk_enti_incasso_bank_branch": (E_VALIDAZIONE, "Filiale non valida."),
    },
)

# ⭐ I quattro tipi di canale, a vocabolario chiuso (`CHECK` a database).
TIPO_BANCA = "BANCA"
TIPI: tuple[str, ...] = (TIPO_BANCA, "POSTE", "PSP", "ALTRO")

# I campi che una persona compila. ⛔ `codice_interno` non c'e': e' la chiave
# stabile con cui il resto del sistema nomina il canale, e cambiarla romperebbe
# i riferimenti senza che niente lo dica.
_CAMPI = (
    "codice",
    "descrizione",
    "tipo",
    "attivo",
    "centro_riscossione_id",
    "soggetto_ruolo_id",
    "bank_branch_id",
    "soggetto_ruolo_conto_bancario_id",
    "formato_flusso",
    "regole_match",
    "meta",
)


# ══════════════════════════════════════════════════════════════════
#  Lettura
# ══════════════════════════════════════════════════════════════════

# Scopo: L'elenco dei canali di incasso.
def list_enti_incasso(
    *,
    tipo: str | None = None,
    centro_riscossione_id: int | None = None,
    attivo: bool | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    _valida_tipo(tipo, obbligatorio=False)
    order_by, order_dir = validate_order_params(
        order_by or "codice",
        (order_dir or "asc").lower(),
        allowed_columns=frozenset(ENTI_INCASSO_SORT_COLUMNS),
        error_code=E_VALIDAZIONE,
        function_name=f"{_FN}.list_enti_incasso",
    )
    offset = validate_pagination(
        page, page_size, error_code=E_VALIDAZIONE,
        function_name=f"{_FN}.list_enti_incasso",
    )

    repository = PagamentiRepository()
    results, total = repository.list_enti_incasso(
        tipo=tipo,
        centro_riscossione_id=centro_riscossione_id,
        attivo=attivo,
        order_by=order_by,
        order_dir=order_dir,
        limit=page_size,
        offset=offset,
    )
    return risposta_paginata(results, total, page, page_size)


# Scopo: Legge il canale o solleva il 404 di dominio.
def _ente_o_404(repository: PagamentiRepository, ente_id: int) -> dict[str, Any]:
    ente = repository.get_ente_incasso(ente_id)
    ErrorManager.require(
        ente is not None,
        code=E_ENTE_NON_TROVATO,
        message="Canale di incasso non trovato.",
        detail=f"ente_incasso_id={ente_id}",
        function_name=_FN,
    )
    assert ente is not None
    return ente


# Scopo: Il dettaglio di un canale.
def get_ente_incasso(ente_id: int) -> dict[str, Any]:
    repository = PagamentiRepository()
    return {"ente_incasso": _ente_o_404(repository, ente_id)}


# Scopo: I conti che si possono agganciare a un canale di quel soggetto.
# 🔴 **Filtrato su `uso = 'INCASSO'`** (BE-8), e non e' comodita': l'unicita'
#    «un conto INCASSO -> un solo soggetto» vive SOLO sulle righe con
#    quell'uso. Un canale appeso al conto dei pagamenti starebbe fuori da quella
#    garanzia, e «un conto -> un solo emittente» tornerebbe a essere
#    un'assunzione senza che nessun errore lo dica.
# ⚠️ Se l'elenco torna vuoto NON e' un errore: significa che quel soggetto non
#    ha ancora un conto di incasso censito **a livello di ruolo**. E' la
#    condizione voluta da D5 — si fallisce alla configurazione — e la schermata
#    deve dirlo, perche' un menu vuoto senza spiegazione sembra un guasto.
def list_conti_incasso(soggetto_ruolo_id: int) -> dict[str, Any]:
    repository = PagamentiRepository()
    conti = repository.list_conti_incasso(soggetto_ruolo_id)
    return {
        "count": len(conti),
        "results": conti,
        # ⭐ Il motivo del vuoto viaggia con la risposta: senza, la schermata
        #    dovrebbe indovinarlo — e indovinerebbe «nessun conto», che e' vero
        #    ma non dice che cosa fare.
        "nessun_conto_di_incasso": not conti,
    }


# ══════════════════════════════════════════════════════════════════
#  Scrittura
# ══════════════════════════════════════════════════════════════════

# Scopo: Valida il tipo contro il vocabolario chiuso.
def _valida_tipo(tipo: str | None, *, obbligatorio: bool) -> str | None:
    if tipo is None:
        ErrorManager.require(
            not obbligatorio,
            code=E_VALIDAZIONE,
            message="Il tipo di canale e' obbligatorio.",
            context={"field": "tipo"},
            function_name=_FN,
        )
        return None
    valore = tipo.upper()
    ErrorManager.require(
        valore in TIPI,
        code=E_VALIDAZIONE,
        message="Tipo di canale non riconosciuto.",
        detail=f"Ammessi: {', '.join(TIPI)}.",
        context={"field": "tipo", "tipo": valore},
        function_name=_FN,
    )
    return valore


# Scopo: Legge dal payload i campi presenti, con la loro conversione.
def _campi_dal_payload(payload: dict[str, Any], *, creazione: bool) -> dict[str, Any]:
    _PAYLOAD.validate_allowed_keys(payload, allowed=frozenset(_CAMPI))
    lettori: dict[str, Any] = {
        "codice": lambda p: _PAYLOAD.require_string(p, "codice", max_len=50),
        "descrizione": lambda p: _PAYLOAD.require_string(p, "descrizione"),
        "tipo": lambda p: _valida_tipo(
            _PAYLOAD.require_string(p, "tipo"), obbligatorio=True
        ),
        "attivo": lambda p: _PAYLOAD.optional_bool(p, "attivo"),
        "centro_riscossione_id": lambda p: _PAYLOAD.optional_positive_int(
            p, "centro_riscossione_id"
        ),
        "soggetto_ruolo_id": lambda p: _PAYLOAD.optional_positive_int(
            p, "soggetto_ruolo_id"
        ),
        "bank_branch_id": lambda p: _PAYLOAD.optional_positive_int(p, "bank_branch_id"),
        "soggetto_ruolo_conto_bancario_id": lambda p: _PAYLOAD.require_positive_int(
            p,
            "soggetto_ruolo_conto_bancario_id",
            message="Il conto di incasso e' obbligatorio su ogni canale.",
        ),
        "formato_flusso": lambda p: _PAYLOAD.optional_string(p, "formato_flusso"),
        "regole_match": lambda p: json.dumps(
            _PAYLOAD.optional_meta(p, "regole_match") or {}
        ),
        "meta": lambda p: json.dumps(_PAYLOAD.optional_meta(p, "meta") or {}),
    }
    campi = {c: lettori[c](payload) for c in _CAMPI if c in payload}

    if creazione:
        # ⚠️ Il conto e' obbligatorio su TUTTI i tipi, non solo su `BANCA`: un
        #    canale `POSTE`, `PSP` o `ALTRO` senza conto sarebbe lo stesso
        #    difetto travestito, con la coda invisibile spostata su un altro
        #    tipo. Il dato c'e': un conto postale ha un IBAN, e il saldo di un
        #    PSP arriva sul conto di accredito dell'emittente.
        for obbligatorio in ("codice", "descrizione", "tipo",
                             "soggetto_ruolo_conto_bancario_id"):
            ErrorManager.require(
                obbligatorio in campi,
                code=E_VALIDAZIONE,
                message=f"Campo '{obbligatorio}' obbligatorio.",
                context={"field": obbligatorio},
                function_name=f"{_FN}.crea_ente_incasso",
            )

    # ⚠️ La filiale e' un fatto DIVERSO dal conto, e vale solo per la banca: su
    #    `POSTE`, `PSP` e `ALTRO` il database la pretende NULL. Ripetuto qui per
    #    farlo arrivare come «campo di troppo» invece che come violazione di un
    #    `CHECK` — ⛔ non e' una seconda sede della regola.
    tipo = campi.get("tipo")
    if tipo is not None and "bank_branch_id" in campi:
        if tipo == TIPO_BANCA:
            ErrorManager.require(
                campi["bank_branch_id"] is not None,
                code=E_VALIDAZIONE,
                message="Su un canale di tipo BANCA la filiale e' obbligatoria.",
                context={"field": "bank_branch_id"},
                function_name=_FN,
            )
        else:
            ErrorManager.require(
                campi["bank_branch_id"] is None,
                code=E_VALIDAZIONE,
                message=f"Su un canale di tipo {tipo} la filiale non si indica.",
                detail="bank_branch_id ammesso solo su BANCA.",
                context={"field": "bank_branch_id"},
                function_name=_FN,
            )
    elif tipo == TIPO_BANCA and creazione:
        ErrorManager.require(
            False,
            code=E_VALIDAZIONE,
            message="Su un canale di tipo BANCA la filiale e' obbligatoria.",
            context={"field": "bank_branch_id"},
            function_name=_FN,
        )
    return campi


# Scopo: Crea un canale di incasso.
def crea_ente_incasso(payload: dict[str, Any]) -> dict[str, Any]:
    campi = _campi_dal_payload(payload, creazione=True)
    repository = PagamentiRepository()
    with _db_errors("crea_ente_incasso"):
        ente_id = repository.create_ente_incasso(campi)
    return {"ente_incasso": _ente_o_404(repository, ente_id)}


# Scopo: Aggiorna un canale di incasso.
def aggiorna_ente_incasso(ente_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repository = PagamentiRepository()
    _ente_o_404(repository, ente_id)
    campi = _campi_dal_payload(payload, creazione=False)
    if campi:
        with _db_errors("aggiorna_ente_incasso"):
            repository.update_ente_incasso(ente_id, campi)
    return {"ente_incasso": _ente_o_404(repository, ente_id)}
