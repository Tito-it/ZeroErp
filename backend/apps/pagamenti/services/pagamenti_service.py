# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facciata del dominio `pagamenti` — le distinte contabili e le loro
#        righe. Orchestrazione sottile: validazione del payload, traduzione
#        degli errori del database, composizione della risposta.
# Note: 🔴 Il backend qui e' sottile PER OBBLIGO, non per stile. Le regole di
#       questo dominio vivono in quindici guard e due matrici di transizione
#       dentro PostgreSQL: riscriverle qui significherebbe avere due sedi che
#       divergono al primo aggiornamento. Il service NON decide se una
#       transizione e' ammessa, se una distinta quadra, se una rata ha
#       capienza: chiede, e traduce la risposta.
#
#       ⛔ E in particolare NON compone piu' scritture: il posting e' UNA SOLA
#       `SELECT pagamenti.fn_posta_contabile(...)`, atomica per costruzione.
#       Un guardrail AST in CI vede il livello repository e boccerebbe la
#       build, ma la regola non e' la rete: e' che quelle due scritture non
#       devono esistere.
# ------------------------------------------------------------

import json
import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction

from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import (
    validate_order_params,
    validate_pagination,
)
from apps.core.services.payload_helpers import (
    PayloadValidator,
    make_db_errors_translator,
)
from apps.pagamenti.db.pagamenti_repository import (
    DISTINTE_SORT_COLUMNS,
    RATE_FUORI_CAPIENZA_SORT_COLUMNS,
    RIGHE_SORT_COLUMNS,
    PagamentiRepository,
)
from apps.pagamenti.types import DistintaRow, RicevutaPosting, RigaContabileRow

logger = logging.getLogger(__name__)

_FN = "pagamenti.pagamenti_service"

# Codice di validazione del payload di questo dominio. ⭐ Seminato dal team DB
# il 2026-08-25 su richiesta del backend: fino ad allora si usava il generico
# `E_VALIDATION_INPUT`, e il passaggio e' costato — come previsto — una riga.
# ⚠️ Il nome e' `..._VALIDATION` (come `E_VENDITE_VALIDATION`), non
# `..._VALIDAZIONE`: il catalogo tiene le due forme e questa e' quella scelta.
E_VALIDAZIONE = "E_PAGAMENTI_VALIDATION"

# Codici di dominio gia' a catalogo che il backend solleva da se': sono i due
# casi in cui l'oggetto non c'e' (o il perimetro non lo lascia vedere, e i due
# restano volutamente indistinguibili).
E_DISTINTA_NON_TROVATA = "E_CONTABILE_NON_TROVATA"
E_RIGA_NON_TROVATA = "E_RIGA_CONTABILE_NON_TROVATA"
# Lo stato chiesto non risolve a catalogo (assente o non attivo). ⭐ TECNICO e
# non «dato sbagliato»: chi ha fatto la richiesta non puo' rimediare — manca
# una riga di configurazione, e la mette chi amministra il database.
E_STATO_NON_CONFIGURATO = "E_CONTABILE_STATO_NON_CONFIGURATO"

_PAYLOAD = PayloadValidator(validation_code=E_VALIDAZIONE, function_name=_FN)

# Traduzione degli errori del database in errori parlanti. ⚠️ I guard di
# `pagamenti` sollevano gia' codici registrati con la loro frase: il traduttore
# li fa passare INTATTI e serve per le violazioni di vincolo (FK), dove il
# database parla il linguaggio dei nomi di vincolo e non quello di chi legge.
_FK_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "fk_vendite_contabili_centro": (E_VALIDAZIONE, "Centro di riscossione non valido."),
    "fk_vendite_contabili_ente": (E_VALIDAZIONE, "Canale di incasso non valido."),
    "fk_vendite_contabili_righe_contabile": (
        E_VALIDAZIONE,
        "Distinta contabile non valida.",
    ),
    "fk_vendite_contabili_righe_fattura": (E_VALIDAZIONE, "Fattura non valida."),
    "fk_vendite_contabili_righe_billing_account": (
        E_VALIDAZIONE,
        "Cliente (billing account) non valido.",
    ),
    "fk_vendite_contabili_righe_scadenza": (E_VALIDAZIONE, "Rata non valida."),
}

_db_errors = make_db_errors_translator(
    fn_prefix=_FN,
    fallback_code=E_VALIDAZIONE,
    fallback_message="Violazione di vincolo sulla distinta contabile.",
    fk_constraints=_FK_CONSTRAINTS,
)

# ⭐ Vocabolario chiuso: gli stati che una PERSONA puo' chiedere sulla testata.
# ⛔ `CHIUSA` non c'e', e non e' una dimenticanza: la chiusura e' una
#    CONSEGUENZA del registrare, non un gesto a parte — la scrive la funzione
#    madre. Un pulsante «chiudi» rimetterebbe in mano a qualcuno una decisione
#    che il database prende da se'.
# ⛔ `IMPORTATA` nemmeno: la scrive l'import, che non esiste ancora.
STATI_DISTINTA_RICHIEDIBILI: tuple[str, ...] = ("VALIDATA", "BOZZA", "ANNULLATA")

# Gli stati che una persona puo' chiedere su una riga. `POSTATA` non c'e': la
# scrive il posting. `IMPORTATA` la scrive l'import.
STATI_RIGA_RICHIEDIBILI: tuple[str, ...] = (
    "DA_ABBINARE",
    "ABBINATA",
    "SOSPESA",
    "SCARTATA",
)

# Le origini che il backend puo' creare. ⭐ Solo `MANUALE`: `GENERATA` la scrive
# il giro dei fondi fattura, `AUTOMATICA` l'import.
ORIGINE_MANUALE = "MANUALE"

# Gli stati in cui i due oggetti NASCONO. Sono codici di catalogo, non id: gli
# id sono seminati e non si scrivono a mano da nessuna parte.
# ⭐ La riga nasce `DA_ABBINARE` perche' quando il denaro arriva non si sa
#    ancora di chi sia, e quello stato dice esattamente questo.
STATO_DISTINTA_INIZIALE = "BOZZA"
STATO_RIGA_INIZIALE = "DA_ABBINARE"
# Lo stato in cui l'abbinamento porta la riga: e' lo stesso gesto, non due.
STATO_RIGA_ABBINATA = "ABBINATA"

# ⭐ Le due code del riconciliatore, e sono DUE MESTIERI (D12-f): `DA_ABBINARE`
#    e' lavoro non ancora fatto, `SOSPESA` e' lavoro fatto che ha trovato un
#    ostacolo. Due voci di menu, una lista sola con il filtro gia' impostato.
CODE_RIGHE: dict[str, tuple[str, ...]] = {
    "DA_ABBINARE": ("DA_ABBINARE",),
    "SOSPESE": ("SOSPESA",),
    # La terza voce non e' una coda: e' il modo di guardarle insieme quando
    # serve, e non compare in nessun menu.
    "TUTTE": ("DA_ABBINARE", "SOSPESA"),
}

# I due motivi per cui una rata esce dalla banda di capienza.
MOTIVI_FUORI_CAPIENZA: tuple[str, ...] = ("SOVRA_INCASSATA", "MOVIMENTO_CONTRARIO")

# Campi della testata che una persona compila. ⛔ Lo stato non e' qui: quello e'
# un'azione, e ha il suo endpoint.
_CAMPI_DISTINTA_PATCH: tuple[str, ...] = (
    "data_contabile",
    "ente_incasso_id",
    "importo_dichiarato",
    "meta",
)

# I FATTI di una riga (come sono arrivati i soldi) e le decisioni che non sono
# un'azione di dominio. ⛔ `fattura_id`, `billing_account_id` e `scadenza_id`
# NON sono qui: abbinare e' un verbo, e porta con se' la forzatura.
_CAMPI_RIGA_PATCH: tuple[str, ...] = (
    "importo",
    "riferimento_ente",
    "data_pagamento",
    "data_valuta",
    "data_operazione",
    "motivo_sospeso",
    "meta",
)


# ══════════════════════════════════════════════════════════════════
#  Helper locali
# ══════════════════════════════════════════════════════════════════

# Scopo: Estrae un importo dal payload come Decimal esatto.
# ⚠️ Passa da `str`: `Decimal(0.1)` porta dentro l'errore del float, e su un
#    importo di denaro quell'errore poi si somma. Il float in ingresso e'
#    ammesso (il JSON non ha decimali) ma si converte sempre dalla sua forma
#    testuale.
# Nota: candidato all'estrazione se ne nasce una seconda occorrenza — oggi e'
#    la prima, e la regola del 2 dice di non astrarre prima.
def _decimal_da_payload(
    payload: dict[str, Any], key: str, *, obbligatorio: bool
) -> Decimal | None:
    raw = payload.get(key)
    if raw is None:
        ErrorManager.require(
            not obbligatorio,
            code=E_VALIDAZIONE,
            message=f"Campo '{key}' obbligatorio.",
            context={"field": key},
            function_name=_FN,
        )
        return None

    # `True` sommerebbe come 1, e un flag scambiato per un importo non lo
    # segnalerebbe nessuno.
    _rifiuta_importo(raw, key, condizione=isinstance(raw, bool))

    try:
        valore = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        _rifiuta_importo(raw, key, condizione=True)
        raise AssertionError("unreachable")  # pragma: no cover

    # ⚠️ `Decimal("NaN")` e `Decimal("Infinity")` si costruiscono senza
    # protestare, e un JSON puo' portarli. Un importo non finito arriverebbe
    # fino alla colonna numeric, dove ogni somma che lo incontra diventa NaN —
    # e un totale NaN non si vede: si legge come un campo vuoto.
    _rifiuta_importo(raw, key, condizione=not valore.is_finite())
    return valore


# Scopo: Rifiuta un valore che non e' un importo, con la stessa frase ovunque.
def _rifiuta_importo(raw: Any, key: str, *, condizione: bool) -> None:
    if not condizione:
        return
    ErrorManager.raise_error(
        code=E_VALIDAZIONE,
        message=f"Campo '{key}' non e' un importo valido.",
        detail=f"Valore ricevuto: {raw!r}",
        context={"field": key, key: str(raw)},
        function_name=_FN,
    )


# Scopo: Serializza `meta` per il passaggio a una colonna jsonb.
def _meta_json(payload: dict[str, Any]) -> str:
    meta = _PAYLOAD.optional_meta(payload, "meta")
    return json.dumps(meta or {})


# Scopo: L'involucro paginato, uguale per tutte le liste del dominio.
def _risposta_paginata(
    results: list[Any], total: int, page: int, page_size: int
) -> dict[str, Any]:
    return {
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size else 0,
        "results": results,
    }


# Scopo: Legge la distinta o solleva il 404 di dominio.
# ⚠️ «Non esiste» e «non la vedi» danno la stessa risposta, ed e' voluto: dire
#    «esiste ma non e' tua» racconterebbe a un operatore fuori perimetro che
#    quel documento c'e'.
def _distinta_o_404(repository: PagamentiRepository, contabile_id: int) -> DistintaRow:
    distinta = repository.get_distinta(contabile_id)
    ErrorManager.require(
        distinta is not None,
        code=E_DISTINTA_NON_TROVATA,
        message="Distinta contabile non trovata.",
        detail=f"contabile_id={contabile_id}",
        function_name=_FN,
    )
    assert distinta is not None
    return distinta


# Scopo: Legge la riga o solleva il 404 di dominio.
def _riga_o_404(repository: PagamentiRepository, riga_id: int) -> RigaContabileRow:
    riga = repository.get_riga(riga_id)
    ErrorManager.require(
        riga is not None,
        code=E_RIGA_NON_TROVATA,
        message="Riga contabile non trovata.",
        detail=f"riga_id={riga_id}",
        function_name=_FN,
    )
    assert riga is not None
    return riga


# Scopo: Compone i campi da aggiornare leggendo SOLO le chiavi presenti nel
#        payload — un PATCH che non nomina un campo non lo tocca.
def _campi_presenti(
    payload: dict[str, Any],
    consentiti: tuple[str, ...],
    *,
    lettori: dict[str, Any],
) -> dict[str, Any]:
    _PAYLOAD.validate_allowed_keys(payload, allowed=frozenset(consentiti))
    campi: dict[str, Any] = {}
    for chiave in consentiti:
        if chiave in payload:
            campi[chiave] = lettori[chiave](payload)
    return campi


# ══════════════════════════════════════════════════════════════════
#  Distinte — lettura
# ══════════════════════════════════════════════════════════════════

# Scopo: Elenco paginato delle distinte contabili.
# Perimetro: la RLS dello schema; il filtro data ha il floor standard delle
#        liste (lo applica il chiamante, non questo service).
def list_distinte(
    *,
    stato: str | None = None,
    origine: str | None = None,
    centro_riscossione_id: int | None = None,
    ente_incasso_id: int | None = None,
    data_da: date | None = None,
    data_a: date | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    order_by, order_dir = validate_order_params(
        order_by or "data_contabile",
        (order_dir or "desc").lower(),
        allowed_columns=frozenset(DISTINTE_SORT_COLUMNS),
        error_code=E_VALIDAZIONE,
        function_name=f"{_FN}.list_distinte",
    )
    offset = validate_pagination(
        page, page_size, error_code=E_VALIDAZIONE, function_name=f"{_FN}.list_distinte"
    )

    repository = PagamentiRepository()
    results, total = repository.list_distinte(
        stato_codice=stato,
        origine=origine,
        centro_riscossione_id=centro_riscossione_id,
        ente_incasso_id=ente_incasso_id,
        data_da=data_da,
        data_a=data_a,
        order_by=order_by,
        order_dir=order_dir,
        limit=page_size,
        offset=offset,
    )
    return _risposta_paginata(results, total, page, page_size)


# Scopo: Dettaglio di una distinta: testata, totali derivati, righe e i due
#        cataloghi di stato — in un round-trip solo.
# ⭐ I cataloghi viaggiano col dettaglio e non si cablano nel frontend: quali
#    stati si possono chiedere, quali pretendono fattura e cliente, quali
#    occupano spazio su una rata lo dice il database.
def get_distinta(contabile_id: int) -> dict[str, Any]:
    repository = PagamentiRepository()
    distinta = _distinta_o_404(repository, contabile_id)
    return {
        "distinta": distinta,
        "righe": repository.list_righe(contabile_id),
        "stati_distinta": repository.list_stati_distinta(),
        "stati_riga": repository.list_stati_riga(),
        # ⭐ Gli elenchi sono DUE, e servono entrambi: il drawer disegna il
        # percorso della testata e quello della riga nella stessa schermata.
        # Prima ne viaggiava uno solo, e il form della riga sarebbe finito a
        # cablarsi il proprio — cioe' a tenere una copia del vocabolario.
        "stati_richiedibili": {
            "distinta": list(STATI_DISTINTA_RICHIEDIBILI),
            "riga": list(STATI_RIGA_RICHIEDIBILI),
        },
    }


# ══════════════════════════════════════════════════════════════════
#  Distinte — scrittura
# ══════════════════════════════════════════════════════════════════

# Scopo: Apre la distinta manuale di lavoro dell'operatore.
# ⭐ E' un *get or create*: se l'operatore riapre con gli stessi dati (stessa
#    giornata, stesso canale, stessa persona) il database NON ne crea una
#    seconda — gli ridà la sua. E' cio' che rende inutile qualunque lock.
# ⚠️ Da cui `gia_popolata` nella risposta: dice che la distinta restituita ha
#    gia' delle righe, e serve al frontend per annunciarlo. ⛔ NON significa
#    «riaperta»: una distinta esistente e vuota e' indistinguibile da una
#    appena creata, e il caso e' innocuo.
def crea_distinta(payload: dict[str, Any]) -> dict[str, Any]:
    _PAYLOAD.validate_allowed_keys(
        payload,
        allowed=frozenset(
            {"centro_riscossione_id", "data_contabile", "ente_incasso_id",
             "importo_dichiarato", "meta"}
        ),
    )
    centro_riscossione_id = _PAYLOAD.require_positive_int(
        payload,
        "centro_riscossione_id",
        message="Il centro di riscossione e' obbligatorio per aprire una distinta.",
    )
    data_contabile = _PAYLOAD.require_date(
        payload,
        "data_contabile",
        message="La data contabile e' obbligatoria per aprire una distinta.",
    )
    ente_incasso_id = _PAYLOAD.optional_positive_int(payload, "ente_incasso_id")
    importo_dichiarato = _decimal_da_payload(
        payload, "importo_dichiarato", obbligatorio=False
    )

    repository = PagamentiRepository()
    # 🔴 DUE scritture, e devono essere UNA unita'. Il totale dichiarato non e'
    # un parametro della funzione madre, quindi si scrive subito dopo — ma una
    # distinta che nascesse SENZA il suo dichiarato sarebbe una distinta la cui
    # quadratura non scatta mai: il controllo esisterebbe e non direbbe niente,
    # che e' il modo peggiore in cui puo' mancare.
    # ⚠️ `ATOMIC_REQUESTS` non e' attivo in questo progetto: senza questo blocco
    # le due scritture sarebbero due transazioni separate.
    with transaction.atomic(), _db_errors("crea_distinta"):
        contabile_id = repository.get_or_create_distinta(
            centro_riscossione_id=centro_riscossione_id,
            data_contabile=data_contabile,
            ente_incasso_id=ente_incasso_id,
            origine=ORIGINE_MANUALE,
            codice_stato_interno=STATO_DISTINTA_INIZIALE,
            meta=_meta_json(payload),
        )
        if importo_dichiarato is not None:
            repository.update_distinta(
                contabile_id, {"importo_dichiarato": importo_dichiarato}
            )

    dettaglio = get_distinta(contabile_id)
    dettaglio["gia_popolata"] = bool(dettaglio["distinta"]["righe_totali"])
    return dettaglio


# Scopo: Aggiorna i campi compilabili della testata.
def aggiorna_distinta(contabile_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repository = PagamentiRepository()
    _distinta_o_404(repository, contabile_id)

    campi = _campi_presenti(
        payload,
        _CAMPI_DISTINTA_PATCH,
        lettori={
            "data_contabile": lambda p: _PAYLOAD.require_date(p, "data_contabile"),
            "ente_incasso_id": lambda p: _PAYLOAD.optional_positive_int(
                p, "ente_incasso_id"
            ),
            "importo_dichiarato": lambda p: _decimal_da_payload(
                p, "importo_dichiarato", obbligatorio=False
            ),
            "meta": lambda p: _meta_json(p),
        },
    )
    if campi:
        with _db_errors("aggiorna_distinta"):
            repository.update_distinta(contabile_id, campi)
    return get_distinta(contabile_id)


# Scopo: Chiede un cambio di stato sulla testata.
# ⚠️ Il backend verifica solo che lo stato chiesto sia uno di quelli che una
#    PERSONA puo' chiedere. Se il passaggio sia ammesso da dove la distinta si
#    trova adesso lo dice la matrice delle transizioni, e le altre tre
#    condizioni (quadratura col dichiarato, riapertura solo se manuale,
#    chiusura con righe ancora pronte) le dicono i loro guard: ⛔ riscriverle
#    qui vorrebbe dire tenerle allineate a mano per sempre.
def cambia_stato_distinta(contabile_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    _PAYLOAD.validate_allowed_keys(payload, allowed=frozenset({"nuovo_stato"}))
    nuovo_stato = _PAYLOAD.require_string(payload, "nuovo_stato").upper()
    ErrorManager.require(
        nuovo_stato in STATI_DISTINTA_RICHIEDIBILI,
        code=E_VALIDAZIONE,
        message="Stato non richiedibile su una distinta contabile.",
        detail=(
            f"Ammessi: {', '.join(STATI_DISTINTA_RICHIEDIBILI)}. "
            "CHIUSA non si chiede: la scrive la registrazione."
        ),
        context={"field": "nuovo_stato", "nuovo_stato": nuovo_stato},
        function_name=f"{_FN}.cambia_stato_distinta",
    )

    repository = PagamentiRepository()
    _distinta_o_404(repository, contabile_id)
    with _db_errors("cambia_stato_distinta"):
        toccate = repository.set_stato_distinta(contabile_id, nuovo_stato)
    # 🔴 Zero righe toccate NON e' un successo silenzioso: la distinta esiste
    # (l'abbiamo appena letta), quindi a non risolvere e' il CODICE DI STATO.
    # Senza questo controllo la risposta sarebbe un 200 con lo stato invariato
    # — l'operatore vedrebbe «fatto» su un gesto che non e' avvenuto.
    ErrorManager.require(
        toccate > 0,
        code=E_STATO_NON_CONFIGURATO,
        message="Stato distinta contabile non configurato.",
        detail=f"codice_interno={nuovo_stato} assente o non attivo a catalogo.",
        function_name=f"{_FN}.cambia_stato_distinta",
    )
    return get_distinta(contabile_id)


# ══════════════════════════════════════════════════════════════════
#  Righe
# ══════════════════════════════════════════════════════════════════

# Scopo: Le righe di una distinta.
def list_righe(contabile_id: int) -> dict[str, Any]:
    repository = PagamentiRepository()
    _distinta_o_404(repository, contabile_id)
    righe = repository.list_righe(contabile_id)
    return {"count": len(righe), "results": righe}


# Scopo: Aggiunge una riga alla distinta — un importo arrivato.
# ⭐ Nasce `DA_ABBINARE`: quando il denaro arriva non si sa ancora di chi sia,
#    e quello stato dice esattamente questo. Chi sa gia' la fattura la abbina
#    subito dopo, col verbo dell'abbinamento.
def crea_riga(contabile_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    _PAYLOAD.validate_allowed_keys(
        payload,
        allowed=frozenset(
            {"importo", "riferimento_ente", "data_pagamento", "data_valuta",
             "data_operazione", "motivo_sospeso", "meta"}
        ),
    )
    importo = _decimal_da_payload(payload, "importo", obbligatorio=True)
    assert importo is not None

    repository = PagamentiRepository()
    _distinta_o_404(repository, contabile_id)
    with _db_errors("crea_riga"):
        riga_id = repository.create_riga(
            contabile_id=contabile_id,
            importo=importo,
            codice_stato_interno=STATO_RIGA_INIZIALE,
            riferimento_ente=_PAYLOAD.optional_string(payload, "riferimento_ente"),
            data_pagamento=_PAYLOAD.optional_date(payload, "data_pagamento"),
            data_valuta=_PAYLOAD.optional_date(payload, "data_valuta"),
            data_operazione=_PAYLOAD.optional_date(payload, "data_operazione"),
            motivo_sospeso=_PAYLOAD.optional_string(payload, "motivo_sospeso"),
            meta=_meta_json(payload),
        )
    return {"riga": _riga_o_404(repository, riga_id)}


# Scopo: Aggiorna i FATTI di una riga.
# ⛔ Non l'abbinamento: quello e' un verbo, perche' porta con se' la rata e la
#    forzatura, e perche' un abbinamento e' una decisione — non la correzione
#    di un dato che era stato digitato male.
def aggiorna_riga(riga_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    repository = PagamentiRepository()
    _riga_o_404(repository, riga_id)

    campi = _campi_presenti(
        payload,
        _CAMPI_RIGA_PATCH,
        lettori={
            "importo": lambda p: _decimal_da_payload(p, "importo", obbligatorio=True),
            "riferimento_ente": lambda p: _PAYLOAD.optional_string(
                p, "riferimento_ente"
            ),
            "data_pagamento": lambda p: _PAYLOAD.optional_date(p, "data_pagamento"),
            "data_valuta": lambda p: _PAYLOAD.optional_date(p, "data_valuta"),
            "data_operazione": lambda p: _PAYLOAD.optional_date(p, "data_operazione"),
            "motivo_sospeso": lambda p: _PAYLOAD.optional_string(p, "motivo_sospeso"),
            "meta": lambda p: _meta_json(p),
        },
    )
    if campi:
        with _db_errors("aggiorna_riga"):
            repository.update_riga(riga_id, campi)
    return {"riga": _riga_o_404(repository, riga_id)}


# Scopo: Chiede un cambio di stato su una riga.
# ⚠️ Come sulla testata: il backend guarda solo il vocabolario, i guard fanno
#    il resto — compreso rifiutare `ABBINATA` su una riga che non dice a quale
#    fattura e a quale cliente appartiene.
def cambia_stato_riga(riga_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    _PAYLOAD.validate_allowed_keys(
        payload, allowed=frozenset({"nuovo_stato", "motivo_sospeso"})
    )
    nuovo_stato = _PAYLOAD.require_string(payload, "nuovo_stato").upper()
    ErrorManager.require(
        nuovo_stato in STATI_RIGA_RICHIEDIBILI,
        code=E_VALIDAZIONE,
        message="Stato non richiedibile su una riga contabile.",
        detail=(
            f"Ammessi: {', '.join(STATI_RIGA_RICHIEDIBILI)}. "
            "POSTATA non si chiede: la scrive la registrazione."
        ),
        context={"field": "nuovo_stato", "nuovo_stato": nuovo_stato},
        function_name=f"{_FN}.cambia_stato_riga",
    )
    motivo_sospeso = _PAYLOAD.optional_string(payload, "motivo_sospeso")

    repository = PagamentiRepository()
    _riga_o_404(repository, riga_id)
    with _db_errors("cambia_stato_riga"):
        # Il motivo accompagna la sospensione nello stesso giro: sospendere
        # senza dire perche' lascia la riga in una coda dove il prossimo che
        # la guarda non sa che cosa si era gia' capito.
        if motivo_sospeso is not None:
            repository.update_riga(riga_id, {"motivo_sospeso": motivo_sospeso})
        toccate = repository.set_stato_riga(riga_id, nuovo_stato)
    # Stessa ragione della testata: la riga esiste, quindi a non risolvere e'
    # il codice di stato — e un 200 sopra un gesto non avvenuto e' peggio di
    # un errore.
    ErrorManager.require(
        toccate > 0,
        code=E_STATO_NON_CONFIGURATO,
        message="Stato riga contabile non configurato.",
        detail=f"codice_interno={nuovo_stato} assente o non attivo a catalogo.",
        function_name=f"{_FN}.cambia_stato_riga",
    )
    return {"riga": _riga_o_404(repository, riga_id)}


# ══════════════════════════════════════════════════════════════════
#  L'abbinamento — il verbo che porta il denaro alla rata
# ══════════════════════════════════════════════════════════════════

# Scopo: Imputa una riga a una fattura, e quando c'e' a una rata.
# ⭐ E' un VERBO e non un PATCH, per due ragioni: porta con se' la rata e la
#    forzatura, ed e' una DECISIONE — non la correzione di un dato che era
#    stato digitato male.
# ⚠️ La rata resta FACOLTATIVA anche su una riga abbinata: la riga del fondo
#    fattura ha fattura si' e rata no, ed e' un caso normale.
# 🔴 Il doppio tempo della capienza (D14-d) passa di qui e il backend NON lo
#    interpreta: il primo tentativo arriva senza `forzata`, il guard del
#    database rifiuta con la ragione e i numeri, e la conferma dell'operatore
#    torna con `forzata = true`. ⛔ Il backend non decide che cosa sia
#    forzabile — se lo facesse, sarebbe una seconda sede della regola.
def abbina_riga(riga_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    _PAYLOAD.validate_allowed_keys(
        payload,
        allowed=frozenset(
            {"fattura_id", "billing_account_id", "scadenza_id", "forzata",
             "motivo_forzatura"}
        ),
    )
    fattura_id = _PAYLOAD.require_positive_int(
        payload, "fattura_id", message="La fattura e' obbligatoria per abbinare."
    )
    billing_account_id = _PAYLOAD.require_positive_int(
        payload,
        "billing_account_id",
        message="Il cliente e' obbligatorio per abbinare.",
    )
    scadenza_id = _PAYLOAD.optional_positive_int(payload, "scadenza_id")
    forzata = _PAYLOAD.optional_bool(payload, "forzata") or False
    motivo_forzatura = _PAYLOAD.optional_string(payload, "motivo_forzatura")
    # ⚠️ Un motivo senza forzatura e' una nota che nessuno leggera' mai: la
    #    colonna esiste per spiegare una forzatura, e scriverla su una riga non
    #    forzata lascerebbe a registro una spiegazione di un gesto mai fatto.
    ErrorManager.require(
        forzata or motivo_forzatura is None,
        code=E_VALIDAZIONE,
        message="Il motivo si scrive solo insieme alla forzatura.",
        detail="motivo_forzatura richiede forzata = true.",
        context={"field": "motivo_forzatura"},
        function_name=f"{_FN}.abbina_riga",
    )

    repository = PagamentiRepository()
    _riga_o_404(repository, riga_id)
    with _db_errors("abbina_riga"):
        toccate = repository.abbina_riga(
            riga_id=riga_id,
            fattura_id=fattura_id,
            billing_account_id=billing_account_id,
            scadenza_id=scadenza_id,
            forzata=forzata,
            motivo_forzatura=motivo_forzatura,
            codice_stato_interno=STATO_RIGA_ABBINATA,
        )
    ErrorManager.require(
        toccate > 0,
        code=E_STATO_NON_CONFIGURATO,
        message="Stato riga contabile non configurato.",
        detail=f"codice_interno={STATO_RIGA_ABBINATA} assente o non attivo.",
        function_name=f"{_FN}.abbina_riga",
    )
    return {"riga": _riga_o_404(repository, riga_id)}


# ══════════════════════════════════════════════════════════════════
#  Le due code, e l'elenco che rende onesta la forzatura
# ══════════════════════════════════════════════════════════════════

# Scopo: La coda del riconciliatore: le righe di TUTTE le distinte in uno degli
#        stati chiesti.
# ⭐ `coda` sceglie il mestiere, non lo stato: chi entra da «Da abbinare» vede
#    solo quelle, chi entra da «Sospese» solo le sue — ma la definizione a
#    catalogo e' una sola.
def list_coda_righe(
    *,
    coda: str | None = None,
    billing_account_id: int | None = None,
    data_da: date | None = None,
    data_a: date | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    chiave = (coda or "TUTTE").upper()
    ErrorManager.require(
        chiave in CODE_RIGHE,
        code=E_VALIDAZIONE,
        message="Coda non riconosciuta.",
        detail=f"Ammesse: {', '.join(CODE_RIGHE)}.",
        context={"field": "coda", "coda": chiave},
        function_name=f"{_FN}.list_coda_righe",
    )
    order_by, order_dir = validate_order_params(
        order_by or "data_pagamento",
        (order_dir or "desc").lower(),
        allowed_columns=frozenset(RIGHE_SORT_COLUMNS),
        error_code=E_VALIDAZIONE,
        function_name=f"{_FN}.list_coda_righe",
    )
    offset = validate_pagination(
        page, page_size, error_code=E_VALIDAZIONE,
        function_name=f"{_FN}.list_coda_righe",
    )

    repository = PagamentiRepository()
    results, total = repository.list_righe_coda(
        stati=CODE_RIGHE[chiave],
        billing_account_id=billing_account_id,
        data_da=data_da,
        data_a=data_a,
        order_by=order_by,
        order_dir=order_dir,
        limit=page_size,
        offset=offset,
    )
    return _risposta_paginata(results, total, page, page_size)


# Scopo: Le rate uscite dalla banda di capienza.
# 🔴 Senza questo elenco la forzatura sarebbe «un modo per nascondere, non per
#    registrare»: e' la ragione per cui la vista e il guard che permette di
#    forzare stanno nello stesso lotto.
def list_rate_fuori_capienza(
    *,
    motivo: str | None = None,
    billing_account_id: int | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    # Fail-fast sul vocabolario chiuso: un motivo inventato darebbe una lista
    # vuota, che su due soli valori possibili e' indistinguibile da «non c'e'
    # niente fuori capienza» — cioe' dalla risposta piu' rassicurante.
    ErrorManager.require(
        motivo is None or motivo in MOTIVI_FUORI_CAPIENZA,
        code=E_VALIDAZIONE,
        message="Motivo non riconosciuto.",
        detail=f"Ammessi: {', '.join(MOTIVI_FUORI_CAPIENZA)}.",
        context={"field": "motivo", "motivo": motivo},
        function_name=f"{_FN}.list_rate_fuori_capienza",
    )
    order_by, order_dir = validate_order_params(
        order_by or "data_scadenza",
        (order_dir or "desc").lower(),
        allowed_columns=frozenset(RATE_FUORI_CAPIENZA_SORT_COLUMNS),
        error_code=E_VALIDAZIONE,
        function_name=f"{_FN}.list_rate_fuori_capienza",
    )
    offset = validate_pagination(
        page, page_size, error_code=E_VALIDAZIONE,
        function_name=f"{_FN}.list_rate_fuori_capienza",
    )

    repository = PagamentiRepository()
    results, total = repository.list_rate_fuori_capienza(
        motivo=motivo,
        billing_account_id=billing_account_id,
        order_by=order_by,
        order_dir=order_dir,
        limit=page_size,
        offset=offset,
    )
    return _risposta_paginata(results, total, page, page_size)


# ══════════════════════════════════════════════════════════════════
#  Registrazione (posting)
# ══════════════════════════════════════════════════════════════════

# Scopo: L'anteprima della registrazione — la fotografia di che cosa succede
#        se si preme adesso.
# ⭐ E' cio' che l'operatore vede PRIMA di premere, ed e' cio' che poi
#    DICHIARA: i due numeri di questa risposta sono quelli da rimandare
#    indietro nella registrazione.
def anteprima_registrazione(contabile_id: int) -> dict[str, Any]:
    repository = PagamentiRepository()
    distinta = _distinta_o_404(repository, contabile_id)
    righe = repository.list_righe(contabile_id)
    # Le righe che restano indietro, con il loro stato: non un numero solo, ma
    # il motivo per cui non partono — «due righe non registrabili» senza dire
    # quali obbliga l'operatore a cercarle a mano.
    non_registrabili = [
        {
            "id": riga["id"],
            "importo": riga["importo"],
            "stato_codice": riga["stato_codice"],
            "stato_descrizione": riga["stato_descrizione"],
        }
        for riga in righe
        if not riga["stato_is_postabile"]
    ]
    return {
        "contabile_id": contabile_id,
        "stato_codice": distinta["stato_codice"],
        "righe_registrabili": distinta["righe_registrabili"],
        "totale_registrabile": distinta["totale_registrabile"],
        "righe_non_registrabili": non_registrabili,
        "importo_dichiarato": distinta["importo_dichiarato"],
        "scarto_dichiarato": distinta["scarto_dichiarato"],
    }


# Scopo: Registra la distinta — il gesto che trasforma il denaro dichiarato in
#        denaro registrato, e da cui i saldi smettono di mentire.
# ⭐ Una sola `SELECT` sulla funzione madre. ⛔ Nessun `transaction.atomic()`,
#    nessun ciclo, nessuna lettura-poi-scrittura.
# ⚠️ La dichiarazione (`righe_attese` + `totale_atteso`) e' facoltativa ma
#    LEGATA: o tutti e due o nessuno. Mezza dichiarazione non si puo'
#    verificare, e accettarla significherebbe registrare senza controllo
#    credendo di averlo fatto.
# ⛔ E l'esito risale INTATTO: `NULLA_DA_POSTARE` non e' un errore e non si
#    trasforma in uno. Se il backend lo facesse, il database scriverebbe nel
#    registro degli errori un errore che non e' un errore — ed e' la ragione
#    esatta per cui la funzione madre e' stata scritta cosi'.
def registra_distinta(contabile_id: int, payload: dict[str, Any]) -> RicevutaPosting:
    _PAYLOAD.validate_allowed_keys(
        payload, allowed=frozenset({"righe_attese", "totale_atteso"})
    )
    # ⚠️ NON `optional_positive_int`: **zero e' una dichiarazione legittima**.
    # L'anteprima puo' mostrare zero righe registrabili, e in quel caso la
    # coppia (0, 0) e' esattamente cio' che l'operatore ha davanti — il
    # database risponde `NULLA_DA_POSTARE`, che e' un esito e non un errore.
    # Rifiutarla qui avrebbe trasformato una risposta vera in un 400 con una
    # frase falsa («deve essere un intero positivo»).
    # ℹ️ Il tetto e' quello dello smallint: una distinta con piu' di 32.767
    #    righe non e' un caso reale, e se lo diventasse con l'import si allarga
    #    qui — un errore parlante, non un troncamento silenzioso.
    righe_attese = _PAYLOAD.optional_smallint(payload, "righe_attese", min_val=0)
    totale_atteso = _decimal_da_payload(payload, "totale_atteso", obbligatorio=False)
    ErrorManager.require(
        (righe_attese is None) == (totale_atteso is None),
        code=E_VALIDAZIONE,
        message="La dichiarazione va passata intera: righe attese e totale atteso.",
        detail=(
            "Mezza dichiarazione non e' verificabile: o si passano entrambi i "
            "valori, o nessuno dei due."
        ),
        context={"field": "righe_attese"},
        function_name=f"{_FN}.registra_distinta",
    )

    repository = PagamentiRepository()
    _distinta_o_404(repository, contabile_id)
    with _db_errors("registra_distinta"):
        return repository.posta_contabile(
            contabile_id=contabile_id,
            righe_attese=righe_attese,
            totale_atteso=totale_atteso,
        )
