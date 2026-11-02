# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il giro delle sistemazioni — che cosa si fa del denaro di troppo.
# Note: ⭐ **Il cantiere non inventa nessuna macchina**: le tre destinazioni
#       usano meccanismi che esistevano gia' tutti — un fondo fattura
#       `origine = MANUALE` per il riporto, una distinta a importi negativi per
#       il rimborso, una distinta sul centro dedicato con due righe che sommano
#       a zero per la compensazione. Mancavano **l'elenco e il registro**.
#
#       🔴 E il backend qui fa **meno** di quanto sembri: registra una decisione
#       (un `INSERT`) e chiama due funzioni madri. Non sceglie la strada, non
#       verifica l'eccedenza, non muove denaro.
# ------------------------------------------------------------

import json
import logging
from typing import Any

from apps.core.api.payload_validators import envelope_da_offset
from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import validate_order_params
from apps.core.services.payload_helpers import (
    PayloadValidator,
    make_db_errors_translator,
)
from apps.pagamenti.db.pagamenti_repository import (
    ECCEDENZE_SORT_COLUMNS,
    PagamentiRepository,
)
from apps.pagamenti.services._helpers import (
    E_FATTURA_NON_TROVATA,
    E_VALIDAZIONE,
)

logger = logging.getLogger(__name__)

_FN = "pagamenti.sistemazioni_service"

E_SISTEMAZIONE_NON_TROVATA = "E_SISTEMAZIONE_NON_TROVATA"

_PAYLOAD = PayloadValidator(validation_code=E_VALIDAZIONE, function_name=_FN)

_db_errors = make_db_errors_translator(
    fn_prefix=_FN,
    fallback_code=E_VALIDAZIONE,
    fallback_message="Violazione di vincolo su una sistemazione.",
    fk_constraints={
        "fk_sistemazioni_fattura_origine": (E_VALIDAZIONE, "Documento di origine non valido."),
        "fk_sistemazioni_fattura_destinazione": (
            E_VALIDAZIONE,
            "Documento di destinazione non valido.",
        ),
        "fk_sistemazioni_cliente": (E_VALIDAZIONE, "Cliente non valido."),
        "fk_sistemazioni_contabile": (E_VALIDAZIONE, "Distinta contabile non valida."),
    },
)

# ⭐ Le tre destinazioni, a vocabolario chiuso. Non sono tre modi di scrivere la
#    stessa cosa: producono **due specie diverse** di oggetto (un fondo oppure
#    una distinta), ed e' la ragione per cui l'esito ha due colonne e non una.
DESTINAZIONE_RIPORTO = "RIPORTO"
DESTINAZIONE_RIMBORSO = "RIMBORSO"
DESTINAZIONE_COMPENSAZIONE = "COMPENSAZIONE"
DESTINAZIONI: tuple[str, ...] = (
    DESTINAZIONE_RIPORTO,
    DESTINAZIONE_RIMBORSO,
    DESTINAZIONE_COMPENSAZIONE,
)

# Le destinazioni che vogliono un secondo documento: il denaro va **da qualche
# parte**. ⛔ Sul rimborso e' VIETATO — li' il denaro esce dal sistema, e un
# secondo documento non esiste.
DESTINAZIONI_CON_DESTINATARIO: frozenset[str] = frozenset(
    {DESTINAZIONE_RIPORTO, DESTINAZIONE_COMPENSAZIONE}
)

# Chi e' in credito, sul filtro dell'elenco: il cliente (ha pagato piu' del
# dovuto) oppure l'azienda (un documento a credito su cui e' entrato denaro).
CHI_E_IN_CREDITO: tuple[str, ...] = ("CLIENTE", "AZIENDA")


# ══════════════════════════════════════════════════════════════════
#  L'elenco
# ══════════════════════════════════════════════════════════════════

# Scopo: I documenti su cui e' entrato piu' del dovuto.
# ⭐ Si guarda **per cliente**, ed e' l'ordinamento di default: la decisione si
#    prende guardando il cliente (D15-b) — compensare significa mettere insieme
#    due documenti suoi, e un elenco ordinato per documento la nasconde.
def list_eccedenze(
    *,
    chi_e_in_credito: str | None = None,
    billing_account_id: int | None = None,
    search: str | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> dict[str, Any]:
    ErrorManager.require(
        chi_e_in_credito is None or chi_e_in_credito in CHI_E_IN_CREDITO,
        code=E_VALIDAZIONE,
        message="Valore non riconosciuto per «chi e' in credito».",
        detail=f"Ammessi: {', '.join(CHI_E_IN_CREDITO)}.",
        context={"parametro": "chi_e_in_credito", "chi_e_in_credito": chi_e_in_credito},
        function_name=f"{_FN}.list_eccedenze",
    )
    order_by, order_dir = validate_order_params(
        order_by or "eccedenza_cliente",
        order_dir or "desc",
        allowed_columns=frozenset(ECCEDENZE_SORT_COLUMNS),
        error_code=E_VALIDAZIONE,
        function_name=f"{_FN}.list_eccedenze",
    )

    repository = PagamentiRepository()
    results, total = repository.list_eccedenze(
        chi_e_in_credito=chi_e_in_credito,
        billing_account_id=billing_account_id,
        search=search,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    return envelope_da_offset(results, total, limit=limit, offset=offset)


# ══════════════════════════════════════════════════════════════════
#  L'atto
# ══════════════════════════════════════════════════════════════════

# Scopo: Legge l'atto o solleva il 404 di dominio.
def _sistemazione_o_404(repository: PagamentiRepository, sistemazione_id: int) -> dict[str, Any]:
    atto = repository.get_sistemazione(sistemazione_id)
    ErrorManager.require(
        atto is not None,
        code=E_SISTEMAZIONE_NON_TROVATA,
        message="Sistemazione non trovata.",
        detail=f"sistemazione_id={sistemazione_id}",
        function_name=_FN,
    )
    assert atto is not None
    return atto


# Scopo: Registra la decisione su un'eccedenza.
# ⚠️ **Registrare non e' eseguire**: l'atto nasce in bozza, e il denaro si muove
#    solo alla conferma. Fra i due momenti puo' arrivare un altro incasso — ed e'
#    la ragione per cui il controllo dell'eccedenza sta LA' e non qui: verificarla
#    adesso darebbe una garanzia che scade.
# 🔴 Cliente ed emittente NON arrivano dal payload: si **derivano** dalla fattura
#    di origine. Il guard del database li verifica con un codice TECNICO apposta,
#    perche' «non li sceglie una persona in un modulo, li deriva chi costruisce
#    l'atto» — e un dato dichiarato male da un modulo non lo sa correggere chi
#    legge il messaggio.
def crea_sistemazione(payload: dict[str, Any]) -> dict[str, Any]:
    _PAYLOAD.validate_allowed_keys(
        payload,
        allowed=frozenset(
            {"fattura_origine_id", "destinazione", "importo",
             "fattura_destinazione_id", "motivo", "meta"}
        ),
    )
    fattura_origine_id = _PAYLOAD.require_positive_int(
        payload,
        "fattura_origine_id",
        message="Il documento con l'eccedenza e' obbligatorio.",
    )
    destinazione = _PAYLOAD.require_string(payload, "destinazione").upper()
    ErrorManager.require(
        destinazione in DESTINAZIONI,
        code=E_VALIDAZIONE,
        message="Destinazione non riconosciuta.",
        detail=f"Ammesse: {', '.join(DESTINAZIONI)}.",
        context={"field": "destinazione", "destinazione": destinazione},
        function_name=f"{_FN}.crea_sistemazione",
    )
    importo = _PAYLOAD.require_decimal(payload, "importo")
    fattura_destinazione_id = _PAYLOAD.optional_positive_int(
        payload, "fattura_destinazione_id"
    )
    motivo = _PAYLOAD.optional_string(payload, "motivo")

    # ⚠️ Le due regole sul destinatario le tiene anche il database (un `CHECK`),
    #    e sono ripetute qui per una ragione sola: farle arrivare a chi compila
    #    come «campo mancante» invece che come violazione di vincolo. ⛔ Non e'
    #    una seconda sede della regola — se il `CHECK` cambiasse, il rifiuto
    #    arriverebbe comunque, solo meno leggibile.
    if destinazione in DESTINAZIONI_CON_DESTINATARIO:
        ErrorManager.require(
            fattura_destinazione_id is not None,
            code=E_VALIDAZIONE,
            message="Serve il documento su cui portare il credito.",
            detail=f"{destinazione} richiede fattura_destinazione_id.",
            context={"field": "fattura_destinazione_id"},
            function_name=f"{_FN}.crea_sistemazione",
        )
    else:
        ErrorManager.require(
            fattura_destinazione_id is None,
            code=E_VALIDAZIONE,
            message="In un rimborso il denaro esce: non c'e' un secondo documento.",
            detail="RIMBORSO non ammette fattura_destinazione_id.",
            context={"field": "fattura_destinazione_id"},
            function_name=f"{_FN}.crea_sistemazione",
        )

    repository = PagamentiRepository()
    riferimenti = repository.get_riferimenti_fattura(fattura_origine_id)
    ErrorManager.require(
        riferimenti is not None,
        code=E_FATTURA_NON_TROVATA,
        message="Documento con l'eccedenza non trovato.",
        detail=f"fattura_origine_id={fattura_origine_id}",
        function_name=f"{_FN}.crea_sistemazione",
    )
    assert riferimenti is not None

    with _db_errors("crea_sistemazione"):
        sistemazione_id = repository.create_sistemazione(
            destinazione=destinazione,
            importo=importo,
            fattura_origine_id=fattura_origine_id,
            fattura_destinazione_id=fattura_destinazione_id,
            cliente_soggetto_ruolo_id=riferimenti["cliente_soggetto_ruolo_id"],
            emittente_soggetto_ruolo_id=riferimenti["emittente_soggetto_ruolo_id"],
            motivo=motivo,
            meta=json.dumps(_PAYLOAD.optional_meta(payload, "meta") or {}),
        )
    return {"sistemazione": _sistemazione_o_404(repository, sistemazione_id)}


# Scopo: Il dettaglio di un atto.
def get_sistemazione(sistemazione_id: int) -> dict[str, Any]:
    repository = PagamentiRepository()
    return {"sistemazione": _sistemazione_o_404(repository, sistemazione_id)}


# Scopo: Gli atti registrati su un documento, in envelope `results` + `count`.
# ⛔ `count` NON e' `len(results)`. Era `len(atti)`, cioe' un numero derivato
#    dalle righe: non puo' dire niente SULLE righe, e come asserzione per il
#    guard anti-troncamento del frontend sarebbe un'eco
#    (`rows.length === rows.length`, sempre vero).
# ⭐ E dal 2026-09-02 non e' nemmeno una SECONDA query: la pagina e il totale
#    escono da UNA valutazione (`COUNT(*) OVER ()`). Due valutazioni dello stesso
#    predicato possono non concordare — fra l'una e l'altra qualcuno registra un
#    atto — e la lista direbbe «3 di 4» avendone in mano 3 su 3.
def list_sistemazioni_fattura(
    fattura_id: int,
    *,
    limit: int | None = None,
    offset: int = 0,
    order_by: str | None = None,
    order_dir: str | None = None,
) -> dict[str, Any]:
    repository = PagamentiRepository()
    atti, totale = repository.list_sistemazioni_fattura(
        fattura_id,
        limit=limit, offset=offset, order_by=order_by, order_dir=order_dir,
    )
    return {"results": atti, "count": totale}


# ══════════════════════════════════════════════════════════════════
#  I due verbi
# ══════════════════════════════════════════════════════════════════

# Scopo: Esegue l'atto: la decisione diventa un fatto.
# ⭐ Una sola `SELECT` sulla madre, che sceglie la strada e ci mette sopra il
#    denaro. ⛔ Il backend non dispatcha le tre destinazioni: le tre strade sono
#    un ramo DENTRO la funzione, e riscriverlo qui sarebbe una seconda sede.
# ⚠️ Il **canale del rimborso** si chiede QUI e non alla registrazione: da quale
#    conto esce il bonifico e' una decisione del momento in cui si paga.
def conferma_sistemazione(sistemazione_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    _PAYLOAD.validate_allowed_keys(payload, allowed=frozenset({"ente_incasso_id"}))
    ente_incasso_id = _PAYLOAD.optional_positive_int(payload, "ente_incasso_id")

    repository = PagamentiRepository()
    _sistemazione_o_404(repository, sistemazione_id)
    with _db_errors("conferma_sistemazione"):
        esito = repository.conferma_sistemazione(
            sistemazione_id, ente_incasso_id=ente_incasso_id
        )
    # La funzione risponde sempre una riga: se non lo facesse, il contratto
    # sarebbe cambiato sotto — e tacere su un atto che ha mosso del denaro e' la
    # cosa peggiore.
    ErrorManager.require(
        esito is not None,
        code="E_PAGAMENTI_CHIAMATA_NON_VALIDA",
        message="La conferma non ha prodotto nessun esito.",
        detail="pagamenti.fn_conferma_sistemazione non ha restituito righe.",
        function_name=f"{_FN}.conferma_sistemazione",
    )
    assert esito is not None
    return {
        "esito": esito,
        "sistemazione": _sistemazione_o_404(repository, sistemazione_id),
    }


# Scopo: Scarta l'atto, lasciandolo a registro con la sua ragione.
# ⚠️ Il motivo e' obbligatorio **se l'atto non ne aveva gia' uno**: lo pretende
#    il guard sui dati, e la ragione e' che una decisione scartata senza un
#    perche' non si ricostruisce. Qui non si duplica quella regola: si passa il
#    motivo e si lascia parlare il database, che sa se ce n'era gia' uno.
def annulla_sistemazione(sistemazione_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    _PAYLOAD.validate_allowed_keys(payload, allowed=frozenset({"motivo"}))
    motivo = _PAYLOAD.optional_string(payload, "motivo")

    repository = PagamentiRepository()
    _sistemazione_o_404(repository, sistemazione_id)
    with _db_errors("annulla_sistemazione"):
        repository.annulla_sistemazione(sistemazione_id, motivo=motivo)
    return {"sistemazione": _sistemazione_o_404(repository, sistemazione_id)}
