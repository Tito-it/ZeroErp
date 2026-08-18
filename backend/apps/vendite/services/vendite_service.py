# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa generica per lo schema vendite (liste, ricerche, stato entita').
# ------------------------------------------------------------

# Contiene operazioni facade generiche sullo schema vendite,
# non legate a un sottodominio specifico (pipeline, reset, ecc.).

import logging
import math
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from django.db import DatabaseError

from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import (
    validate_enum_param,
    validate_order_params,
    validate_pagination,
)
from apps.core.services.partitioned_note_service import PartitionedNoteService
from apps.vendite.db.note_repositories import NOTE_REPO_FATTURA
from apps.vendite.db.vendite_repository import (
    DASH_APERTO_AREE,
    DASH_APERTO_FASI,
    DASH_BACKLOG_CLASSI,
    DASH_COMPETENZA_STADI,
    DASH_FATTURAZIONE_AREE,
    DASH_FATTURAZIONE_AREE_EURO,
    FONDI_DA_DECIDERE_MOTIVI,
    SEARCH_MIN_LEN,
    VenditeRepository,
)
from apps.vendite.types import (
    DashApertoDocumentoRow,
    DashApertoRiepilogoRow,
    DashBacklogDocumentoRow,
    DashCompetenzaAttivitaRow,
    DashCompetenzaCommessaRow,
    DashCompetenzaErroreRow,
    DashCompetenzaGruppoRow,
    FondoFatturaDaDecidereRow,
    LottoFattureRow,
    LottoListRow,
)

logger = logging.getLogger(__name__)

_SORT_BY_VALIDI: tuple[str, ...] = ("fattura_id", "nominativo", "totale_doc")
_SORT_DIR_VALIDI: tuple[str, ...] = ("asc", "desc")


# Scopo: Valida page/page_size con E_VENDITE_VALIDATION e restituisce l'offset calcolato.
# Riutilizzabile da tutte le funzioni di lista dello schema vendite.
def _validate_pagination(page: int, page_size: int, function_name: str) -> int:
    return validate_pagination(
        page, page_size, error_code="E_VENDITE_VALIDATION", function_name=function_name,
    )


# Scopo: Risolve (limit, offset) per le liste dei cruscotti, distinguendo il
#        giro PAGINATO da quello di EXPORT.
#
#        `max_rows` valorizzato = export: si vuole l'intero perimetro in una
#        volta, quindi limit=max_rows e offset=0. La validazione di
#        paginazione va SALTATA, non allargata: il tetto di 200 righe per
#        pagina e' un guard di interfaccia (nessuna DataTable ne chiede di
#        piu') e allentarlo nel validatore condiviso lo indebolirebbe per
#        tutte le liste del progetto. Il tetto dell'export e' un altro
#        (`EXPORT_MAX_ROWS`) e lo presidia il building block di export.
#
#        Senza `max_rows` il comportamento e' identico a prima.
def _paging_o_export(
    *, page: int, page_size: int, max_rows: int | None, function_name: str,
) -> tuple[int, int]:
    if max_rows is not None:
        ErrorManager.require(
            max_rows > 0,
            code="E_VENDITE_VALIDATION",
            message="Parametro max_rows non valido.",
            detail="max_rows deve essere un intero positivo.",
            context={"max_rows": max_rows},
            function_name=function_name,
        )
        return max_rows, 0
    return page_size, _validate_pagination(page, page_size, function_name)


# Scopo: Valida un parametro enum con E_VENDITE_VALIDATION (whitelist del
# chiamante). Riutilizzabile da tutte le funzioni di lista dello schema vendite.
def _validate_enum(
    value: str | None,
    *,
    allowed: tuple[str, ...],
    param_name: str,
    function_name: str,
    nullable: bool = True,
    log_to_db: bool = False,
) -> str | None:
    return validate_enum_param(
        value,
        allowed=allowed,
        param_name=param_name,
        error_code="E_VENDITE_VALIDATION",
        function_name=function_name,
        nullable=nullable,
        log_to_db=log_to_db,
    )


# Scopo: Costruisce l'envelope di risposta paginata standard.
# Riutilizzabile da tutte le funzioni di lista dello schema vendite.
def _build_list_response(
    results: list,
    total_count: int,
    page: int,
    page_size: int,
) -> dict[str, object]:
    total_pages = math.ceil(total_count / page_size) if page_size > 0 else 0
    return {
        "count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "results": results,
    }


# Scopo: Pagina effettivamente servita dopo il clamp SQL dell'offset
#        all'ultima pagina (_query_paged_view, rientro da pagina stantia in
#        una sola valutazione della union): l'envelope deve dichiarare la
#        pagina reale, che il FE adotta (usePagedDashFetch sincronizza
#        page dalla risposta).
def _pagina_effettiva(page: int, page_size: int, total_count: int) -> int:
    if total_count <= 0 or page_size <= 0:
        return 1
    return min(page, math.ceil(total_count / page_size))


# Scopo: Restituisce elenco lotti paginato con decodifica e filtri opzionali.
# Obiettivo: esporre lista generica lotti con validazione paginazione.
# Perimetro: sola lettura; delega query a VenditeRepository.
# Risultato: dict con count, page, page_size, total_pages, results.
def fn_list_lotti(
    *,
    competenza_mese: date | None = None,
    utility_id: int | None = None,
    stato_lotto: str | None = None,
    area_geografica_id: int | None = None,
    tipo_doc_fiscale_id: int | None = None,
    emittente_soggetto_ruolo_id: int | None = None,
    auth_user_id: int | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, object]:
    offset = _validate_pagination(page, page_size, "vendite.vendite_service.fn_list_lotti")
    repository = VenditeRepository()
    results: list[LottoListRow]
    results, total_count = repository.list_lotti(
        competenza_mese=competenza_mese,
        utility_id=utility_id,
        stato_lotto=stato_lotto,
        area_geografica_id=area_geografica_id,
        tipo_doc_fiscale_id=tipo_doc_fiscale_id,
        emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
        auth_user_id=auth_user_id,
        order_by=order_by,
        order_dir=order_dir,
        limit=page_size,
        offset=offset,
    )
    return _build_list_response(results, total_count, page, page_size)


# Scopo: Estrae i lotti per l'EXPORT (CSV/XLSX), con gli stessi filtri e lo
#        stesso ordinamento della lista a video — così il file rispecchia ciò
#        che l'operatore stava guardando.
#
#        Perché non passa da `fn_list_lotti`: quella valida `page_size` con
#        `validate_pagination`, che impone il tetto di 200 righe della lista.
#        L'export ne ha bisogno di più, e chiede `EXPORT_MAX_ROWS + 1` di
#        proposito: la riga in eccesso serve a **rilevare** il superamento del
#        limite (`build_export_response` solleva `E_UI_EXPORT_LIMIT_EXCEEDED`)
#        invece di consegnare un file troncato in silenzio.
# Perimetro: sola lettura; scope emittente applicato in repository come la lista.
# Risultato: tuple (righe, conteggio totale) da passare a `build_export_response`.
def fn_export_lotti(
    *,
    competenza_mese: date | None = None,
    utility_id: int | None = None,
    stato_lotto: str | None = None,
    area_geografica_id: int | None = None,
    tipo_doc_fiscale_id: int | None = None,
    emittente_soggetto_ruolo_id: int | None = None,
    auth_user_id: int | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    max_rows: int,
) -> tuple[list[LottoListRow], int]:
    repository = VenditeRepository()
    return repository.list_lotti(
        competenza_mese=competenza_mese,
        utility_id=utility_id,
        stato_lotto=stato_lotto,
        area_geografica_id=area_geografica_id,
        tipo_doc_fiscale_id=tipo_doc_fiscale_id,
        emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
        auth_user_id=auth_user_id,
        order_by=order_by,
        order_dir=order_dir,
        limit=max_rows,
        offset=0,
        max_limit=max_rows,
    )


# Range anni accettato (mirror del clamp FE useDashMesiNav): fuori range → 400,
# non una query su un anno assurdo. Vive qui perché la validazione è del service.
_DASH_ANNO_MIN = 2000
_DASH_ANNO_MAX = 2100


# Scopo: Conteggio lotti generati per mese di competenza di un anno — alimenta il
#        badge per-mese della sidebar anno/mese del registro lotti (stile Lente
#        Competenza). Fotografia completa (nessun filtro stato, decisione UX).
#        Ritorna sempre i 12 mesi (0-riempiti) in ordine, ognuno con la sua
#        competenza (YYYY-MM-01, chiave stabile per il componente FE) e n_lotti.
#        Scope emittente applicato in repo (RLS + whitelist), come la lista.
def fn_lotti_mensile(*, anno: int, auth_user_id: int | None = None) -> dict[str, object]:
    ErrorManager.require(
        isinstance(anno, int) and _DASH_ANNO_MIN <= anno <= _DASH_ANNO_MAX,
        code="E_VENDITE_VALIDATION",
        message="Anno non valido.",
        detail=f"anno deve essere un intero tra {_DASH_ANNO_MIN} e {_DASH_ANNO_MAX}.",
        context={"anno": anno},
        function_name="vendite.vendite_service.fn_lotti_mensile",
    )
    repository = VenditeRepository()
    per_mese = repository.count_lotti_per_mese(anno=anno, auth_user_id=auth_user_id)
    mesi = [
        {
            "competenza_mese": f"{anno:04d}-{mese:02d}-01",
            "n_lotti": per_mese.get(mese, 0),
        }
        for mese in range(1, 13)
    ]
    return {"anno": anno, "mesi": mesi}


# Scopo: Restituisce la testata di un singolo lotto (dettaglio drawer diagnostico,
#        cockpit Fase B). Scope emittente applicato in repo: lotto fuori scope o
#        inesistente → E_LOTTO_NOT_FOUND (404), indistinguibili per non leakare
#        l'esistenza (coerente RLS operatori).
#
#        Dal 2026-08-04 la testata porta anche il blob CAPABILITY letto da
#        `script.fn_available_actions_lotto`: quali verbi di governo sono
#        disponibili sul lotto, quali abilitati e — quando non lo sono — perche'
#        (`enabled` + `reasons`). E' la stessa sorgente che le due fn di
#        mutazione usano per sollevare, quindi il drawer NON ricalcola nulla:
#        prima quelle condizioni erano cinque `computed` in LottoDrawer.vue e
#        avevano gia' prodotto un pulsante-vicolo-cieco (in-app, 2026-07-31).
#        ⚠️ ORDINE VINCOLANTE: il blob si legge DOPO `get_lotto`, che e' l'unico
#        cancello di scope — `fn_available_actions_lotto` non filtra per
#        emittente. Stesso ordine di lettura della fattura (api.md §dettaglio).
#
#        Collisione di chiavi: il blob porta `tipo_lotto`, che la testata ha
#        gia'. E' lo stesso valore letto dalla stessa colonna, quindi il merge
#        e' innocuo; `stato_codice` (blob) e `stato_doc_fiscale_codice`
#        (testata) sono nomi diversi per lo stesso codice, come per le sorelle.
#
#        Fallback graceful (pattern offerte/contratti): se il capability layer
#        e' rotto (DatabaseError) si logga e si ritorna la testata SENZA blob.
#        Il FE degrada a sola consultazione (nessuna azione), ma l'operatore
#        vede comunque il lotto — una rottura delle capability non deve
#        impedire la lettura dell'entita'.
def fn_get_lotto(*, lotto_id: int, auth_user_id: int | None = None) -> dict[str, object]:
    ErrorManager.require(
        bool(lotto_id and lotto_id > 0),
        code="E_LOTTO_PARAMETRO_NON_COERENTE",
        message="Parametri non validi.",
        detail="lotto_id obbligatorio e > 0",
        context={"lotto_id": lotto_id},
        function_name="vendite.vendite_service.fn_get_lotto",
        log_to_db=True,
    )
    repository = VenditeRepository()
    lotto = repository.get_lotto(lotto_id=lotto_id, auth_user_id=auth_user_id)
    if lotto is None:
        ErrorManager.raise_error(
            code="E_LOTTO_NON_TROVATO",
            message="Lotto non trovato.",
            detail=f"Nessun lotto accessibile con id={lotto_id}",
            context={"lotto_id": lotto_id},
            function_name="vendite.vendite_service.fn_get_lotto",
            log_to_db=True,
        )
    assert lotto is not None
    result = dict(lotto)
    try:
        result.update(repository.get_available_actions_lotto(lotto_id))
    except DatabaseError as exc:
        logger.warning(
            "fn_available_actions_lotto fallita per lotto_id=%s: %s. "
            "Dettaglio ritornato senza blob capability (drawer in sola consultazione).",
            lotto_id, exc,
        )
    return result


# Scopo: Restituisce elenco fatture di un lotto con decodifiche, filtri e ordinamento opzionali.
# Obiettivo: esporre lista paginata per lotto con validazione parametri.
# Perimetro: sola lettura; delega query a VenditeRepository.
# Risultato: dict con count, page, page_size, total_pages, results.
def fn_list_lotto_fatture(
    *,
    lotto_id: int,
    stato_esecuzione: str | None = None,
    auth_user_id: int | None = None,
    sort_by: str = "fattura_id",
    sort_dir: str = "asc",
    page: int = 1,
    page_size: int = 50,
) -> dict[str, object]:
    offset = _validate_pagination(page, page_size, "vendite.vendite_service.fn_list_lotto_fatture")
    _validate_enum(
        sort_by,
        allowed=_SORT_BY_VALIDI,
        param_name="sort_by",
        function_name="vendite.vendite_service.fn_list_lotto_fatture",
        nullable=False,
        log_to_db=True,
    )
    _validate_enum(
        sort_dir,
        allowed=_SORT_DIR_VALIDI,
        param_name="sort_dir",
        function_name="vendite.vendite_service.fn_list_lotto_fatture",
        nullable=False,
        log_to_db=True,
    )
    repository = VenditeRepository()
    results: list[LottoFattureRow]
    results, total_count = repository.list_lotto_fatture(
        lotto_id=lotto_id,
        stato_esecuzione=stato_esecuzione,
        auth_user_id=auth_user_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=page_size,
        offset=offset,
    )
    return _build_list_response(results, total_count, page, page_size)


# Range anni ammesso per i cruscotti fatturazione (Lente 1: anno libero
# validato con range sensato).
_DASH_ANNO_MIN = 2000
_DASH_ANNO_MAX = 2100


@dataclass
class _CellaAperto:
    # Scopo: Accumulatore tipizzato del pivot serbatoio pre-commessa per
    #        (area, fase): somme native su Decimal/int, serializzazione a
    #        stringa UNA volta in uscita.
    n_documenti: int = 0
    valore_totale: Decimal = Decimal(0)


# Scopo: Serializza i campi condivisi di una cella della Situazione aperta.
#        UNICO punto di serializzazione, usato sia per le celle area×fase sia
#        per i totali di area: il contratto resta simmetrico per costruzione.
#        Per le aree con valori il valore assente e' "0" (il FE non distingue
#        "cella vuota" da "totale zero"); per le aree a conteggi resta None
#        (DL-11).
def _cella_aperto_fields(
    cella: _CellaAperto, *, con_valori: bool
) -> dict[str, object]:
    return {
        "n_documenti": cella.n_documenti,
        "valore_totale": str(cella.valore_totale) if con_valori else None,
    }


# Scopo: Restituisce il riepilogo del serbatoio pre-commessa (stock documenti
#        aperti-non-chiusi senza asse temporale, §6-ter design due-lenti): le 4
#        aree documento SEMPRE presenti nell'ordine del funnel, ognuna con
#        totali di area e griglia per fase normalizzata (3 fasi vive SEMPRE
#        presenti nell'ordine del ciclo di vita — DL-13: la vista e' neutra, il
#        FE decide quali card mostrare), piu' il vocabolario `fasi` top-level
#        (alimenta i filtri FE senza contrabbandarlo dalla griglia di un'area).
#        Aree o fasi NON in whitelist emesse dalla vista vengono accodate dopo
#        le note, MAI perse in silenzio (fail-visible); un'area extra che porta
#        VALORI li espone (decisione data-driven, non la whitelist euro statica:
#        niente euro persi in silenzio).
# Perimetro: sola lettura; scope emittente DB-side (RLS invoker).
# Risultato: dict {aree: [{area, n_documenti, valore_totale, fasi: [...]}] x4+,
#        fasi: [...] x3+}.
def fn_dash_aperto_riepilogo() -> dict[str, object]:
    repository = VenditeRepository()
    rows: list[DashApertoRiepilogoRow] = repository.list_dash_aperto_riepilogo()

    celle: dict[tuple[str, str], _CellaAperto] = {}
    aree_extra: list[str] = []
    fasi_extra: list[str] = []
    aree_con_valori: set[str] = set()
    for r in rows:
        cella = celle.setdefault((r["area"], r["fase"]), _CellaAperto())
        cella.n_documenti += r["n_documenti"]
        if r["valore_totale"] is not None:
            cella.valore_totale += Decimal(r["valore_totale"])
            aree_con_valori.add(r["area"])
        if r["area"] not in DASH_APERTO_AREE and r["area"] not in aree_extra:
            aree_extra.append(r["area"])
        if r["fase"] not in DASH_APERTO_FASI and r["fase"] not in fasi_extra:
            fasi_extra.append(r["fase"])

    fasi_tutte = list(DASH_APERTO_FASI) + fasi_extra
    aree: list[dict[str, object]] = []
    for area in list(DASH_APERTO_AREE) + aree_extra:
        # Aree euro note sempre con valori (zero esplicito anche a vuoto);
        # un'area extra li espone se la vista li fornisce.
        con_valori = area in DASH_FATTURAZIONE_AREE_EURO or area in aree_con_valori
        celle_area = [
            (fase, celle.get((area, fase), _CellaAperto())) for fase in fasi_tutte
        ]
        totale = _CellaAperto()
        for _, c in celle_area:
            totale.n_documenti += c.n_documenti
            totale.valore_totale += c.valore_totale
        aree.append(
            {
                "area": area,
                **_cella_aperto_fields(totale, con_valori=con_valori),
                "fasi": [
                    {"fase": f, **_cella_aperto_fields(c, con_valori=con_valori)}
                    for f, c in celle_area
                ],
            }
        )
    return {"aree": aree, "fasi": fasi_tutte}


# Scopo: Restituisce il drill-down paginato del serbatoio pre-commessa: stock
#        dei documenti aperti-non-chiusi delle 5 aree, ordinati per "in essere
#        da" (i piu' vecchi prima), con filtri opzionali area/fase e
#        ritardo_giorni ("aperti da oltre N giorni" su data documento — DL-17,
#        soglia SOLO sul drill-down: le card del riepilogo restano la
#        fotografia completa). NESSUNO dei filtri area/fase e' whitellistato, di
#        proposito (coerenza fail-visible col riepilogo, che accoda aree e fasi
#        fuori whitelist E le rende cliccabili come card FE): un'area o fase
#        futura resta drillabile senza toccare il BE; un valore sconosciuto — o
#        COMMESSE, esclusa dal WHERE della vista — da' lista vuota, mai 400.
# Perimetro: sola lettura; scope emittente DB-side (RLS invoker).
# Risultato: dict con count, page, page_size, total_pages, results.
def fn_dash_aperto_documenti(
    *,
    area: str | None = None,
    fase: str | None = None,
    ritardo_giorni: int | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    page: int = 1,
    page_size: int = 50,
    # Export (BB `build_dash_export_response`): valorizzato = perimetro intero
    # in una volta, paginazione saltata. Assente = lista paginata di sempre.
    max_rows: int | None = None,
) -> dict[str, object]:
    # Filtro ritardo opzionale: se presente deve essere un intero > 0 (una
    # soglia di giorni non-positiva non ha senso; niente normalizzazione
    # silenziosa — DL-17).
    ErrorManager.require(
        ritardo_giorni is None or ritardo_giorni > 0,
        code="E_VENDITE_VALIDATION",
        message="Parametro ritardo_giorni non valido.",
        detail="Deve essere un intero maggiore di zero.",
        context={"ritardo_giorni": ritardo_giorni},
        function_name="vendite.vendite_service.fn_dash_aperto_documenti",
    )
    # Ordinamento server-side (convenzione order_by/order_dir come le liste
    # standard): whitelist della lista + direzione asc/desc, fail-fast 400 —
    # nessun input grezzo entra nell'ORDER BY. Assenti -> ordine di default
    # (i piu' "in essere da" prima) deciso dal repository.
    ErrorManager.require(
        order_by is None or order_by in VenditeRepository.DASH_APERTO_SORT_COLUMNS,
        code="E_VENDITE_VALIDATION",
        message="Colonna di ordinamento non valida.",
        detail=(
            f"order_by='{order_by}' non ammesso. Valori: "
            f"{', '.join(sorted(VenditeRepository.DASH_APERTO_SORT_COLUMNS))}."
        ),
        context={"order_by": order_by},
        function_name="vendite.vendite_service.fn_dash_aperto_documenti",
    )
    ErrorManager.require(
        order_dir is None or order_dir.lower() in ("asc", "desc"),
        code="E_VENDITE_VALIDATION",
        message="Direzione di ordinamento non valida.",
        detail="order_dir deve essere 'asc' o 'desc'.",
        context={"order_dir": order_dir},
        function_name="vendite.vendite_service.fn_dash_aperto_documenti",
    )
    limit, offset = _paging_o_export(
        page=page, page_size=page_size, max_rows=max_rows,
        function_name="vendite.vendite_service.fn_dash_aperto_documenti",
    )
    repository = VenditeRepository()
    results: list[DashApertoDocumentoRow]
    results, total_count = repository.list_dash_aperto_documenti(
        area=area,
        fase=fase,
        ritardo_giorni=ritardo_giorni,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    return _build_list_response(
        results, total_count, _pagina_effettiva(page, page_size, total_count), page_size
    )


@dataclass
class _CellaCompetenza:
    # Scopo: Accumulatore tipizzato del pivot Lente 1 per (mese, stadio):
    #        somme native su Decimal/int, serializzazione a stringa UNA volta
    #        in uscita (niente round-trip str↔Decimal per riga).
    n_attivita: int = 0
    valore: Decimal = Decimal(0)
    valore_fatturato: Decimal = Decimal(0)
    n_in_ritardo: int = 0
    valore_in_ritardo: Decimal = Decimal(0)
    stati_fattura: list[dict[str, object]] = field(default_factory=list)


# Scopo: Serializza una cella-stadio nel payload API. Contratto SIMMETRICO su
#        tutti gli stadi (concentrico DL-8): stessi campi ovunque, valorizzati
#        dove hanno senso (valore_fatturato solo su FATTURATA, ritardo solo
#        sugli stadi emessi, stati_fattura popolata solo su FATTURATA).
#        `valore_display` incapsula la decisione DB-6 (Tid 2026-07-06) in un
#        punto solo: la misura da mostrare e' l'imponibile riga per il
#        fatturato, il teorico prezzo_snapshot×quantita per il resto del
#        funnel — il FE rende, non decide.
# Stati della seconda misura delle card (conteggio fatture). Costanti e non
# literal sparsi: sono contratto verso il FE, che ci decide cosa rendere.
DASH_FATTURE_OK = "OK"
DASH_FATTURE_NON_APPLICABILE = "NON_APPLICABILE"
DASH_FATTURE_ERRORE = "ERRORE"


# Scopo: decide `(n_fatture, stato)` di una cella. E' qui che le tre situazioni
#        restano tre e non collassano in «manca il numero»:
#          · stadio fuori dai calcolabili (DA_EMETTERE/DA_APPROVARE: la chiave
#            documento non esiste ancora) -> NON_APPLICABILE, la card tace;
#          · calcolo fallito su quello stadio                -> ERRORE, la card avvisa;
#          · cella VUOTA (nessuna attivita')                 -> NON_APPLICABILE:
#            «0 fatture» sotto «0 attivita'» sarebbe rumore, non informazione;
#          · altrimenti -> OK, col conteggio (che puo' legittimamente essere 0:
#            attivita' presenti e nessuna fattura ancora prodotta).
#
#        ⚠️ L'ordine dei rami conta, e va nel verso CONTROintuitivo: la cella
#        vuota si valuta PRIMA del guasto. Il motivo e' che il calcolo fallisce
#        per l'intero anno, non per un mese: segnalare l'errore anche dove non
#        c'e' nulla da contare riempirebbe la griglia di avvertimenti — fino a
#        12, quasi tutti su mesi vuoti — e il guasto vero annegherebbe nei
#        propri falsi positivi. Con zero attivita' non ci sono fatture da
#        prevedere, quindi tacere non nasconde niente. L'avvertimento resta
#        dove sarebbe servito un numero.
def _stato_fatture_cella(
    stadio: str,
    cella: _CellaCompetenza,
    competenza: str,
    fatture_per_cella: dict[tuple[str, str], int],
    stadi_ko: set[str],
) -> tuple[int | None, str]:
    if stadio not in VenditeRepository.DASH_STADI_CON_CONTEGGIO_FATTURE:
        return None, DASH_FATTURE_NON_APPLICABILE
    if cella.n_attivita == 0:
        return None, DASH_FATTURE_NON_APPLICABILE
    if stadio in stadi_ko:
        return None, DASH_FATTURE_ERRORE
    return fatture_per_cella.get((competenza, stadio), 0), DASH_FATTURE_OK


def _cella_stadio_payload(
    stadio: str,
    cella: _CellaCompetenza,
    n_fatture: int | None = None,
    n_fatture_stato: str = DASH_FATTURE_NON_APPLICABILE,
) -> dict[str, object]:
    display = cella.valore_fatturato if stadio == "FATTURATA" else cella.valore
    return {
        "stadio": stadio,
        "n_attivita": cella.n_attivita,
        "valore": str(cella.valore),
        "valore_fatturato": str(cella.valore_fatturato),
        "valore_display": str(display),
        "n_in_ritardo": cella.n_in_ritardo,
        "valore_in_ritardo": str(cella.valore_in_ritardo),
        "stati_fattura": cella.stati_fattura,
        # Seconda misura della card: quante FATTURE, non quante attivita'.
        # `0` -> la card dice zero; `None` -> non c'e' un numero, e il PERCHE'
        # lo dice `n_fatture_stato`. Collassare `0` su `None` direbbe «non lo
        # sappiamo» dove sappiamo benissimo che sono zero.
        "n_fatture": n_fatture,
        # Perche' il numero non c'e', in modo ESPLICITO invece che deducibile:
        #   · OK              -> `n_fatture` e' valorizzato e attendibile;
        #   · NON_APPLICABILE -> per questo stadio non si calcola per progetto
        #                        (DA_EMETTERE: la chiave documento non esiste
        #                        ancora) oppure la cella e' vuota -> la card tace;
        #   · ERRORE          -> il calcolo doveva riuscire e NON e' riuscito
        #                        -> la card lo segnala all'operatore.
        # Senza questo campo gli ultimi due sarebbero indistinguibili a video, e
        # un guasto avrebbe l'aspetto del comportamento normale.
        "n_fatture_stato": n_fatture_stato,
    }


# Scopo: Restituisce l'aggregata annuale della Lente 1 Competenza: 12 mesi
#        SEMPRE presenti, ognuno coi 4 stadi del funnel in ordine fisso
#        (commessa → fattura), il breakdown per stato documento fiscale del
#        fatturato (blocco 3a, dati non colonne: pivot del formato lungo), i
#        totali di copertura del mese e il conteggio errori vivi (blocco 4).
#        Eventuali stadi NON in whitelist emessi dalla vista vengono accodati
#        dopo i 4 noti, MAI persi in silenzio (fail-visible, stesso principio
#        anti-drift della lookup motivi_fermo): aggregata e drill-down non
#        possono divergere senza segnale.
# Perimetro: sola lettura; scope emittente DB-side (GUC fail-closed in vista).
# Risultato: dict {anno, mesi: [{competenza_mese, stadi, totali, n_errori}] x12}.
def fn_dash_competenza_mensile(
    *,
    anno: int,
) -> dict[str, object]:
    ErrorManager.require(
        _DASH_ANNO_MIN <= anno <= _DASH_ANNO_MAX,
        code="E_VENDITE_VALIDATION",
        message="Parametro anno fuori range.",
        detail=f"Valori ammessi: {_DASH_ANNO_MIN}-{_DASH_ANNO_MAX}",
        context={"anno": anno},
        function_name="vendite.vendite_service.fn_dash_competenza_mensile",
    )
    repository = VenditeRepository()
    rows = repository.list_dash_competenza_mensile(anno=anno)
    errori_per_mese = repository.count_dash_competenza_errori_mensile(anno=anno)
    # Conteggio fatture per (mese, stadio): una sola lettura per l'intera
    # griglia, come gli errori — non una query per cella. `stadi_ko` sono gli
    # stadi il cui calcolo e' fallito: restano distinti da quelli che non si
    # calcolano per progetto (vedi `_stato_fatture_cella`).
    fatture_per_cella, stadi_ko = repository.count_dash_competenza_fatture_mensile(
        anno=anno,
    )

    # Pivot del formato lungo: accumula per (mese, stadio); le righe FATTURATA
    # (una per stato fattura, gia' ordinate per ordine stato dal repository)
    # alimentano anche il breakdown 3a. Gli stadi fuori whitelist vengono
    # registrati per l'accodamento fail-visible in coda al mese.
    celle: dict[tuple[str, str], _CellaCompetenza] = {}
    stadi_extra: dict[str, list[str]] = {}
    for r in rows:
        key = (r["competenza_mese"], r["stadio"])
        cella = celle.get(key)
        if cella is None:
            cella = _CellaCompetenza()
            celle[key] = cella
            if r["stadio"] not in DASH_COMPETENZA_STADI:
                stadi_extra.setdefault(r["competenza_mese"], []).append(r["stadio"])
        cella.n_attivita += r["n_attivita"]
        cella.valore += Decimal(r["valore"])
        cella.valore_fatturato += Decimal(r["valore_fatturato"])
        cella.n_in_ritardo += r["n_in_ritardo"]
        cella.valore_in_ritardo += Decimal(r["valore_in_ritardo"])
        if r["stadio"] == "FATTURATA":
            cella.stati_fattura.append(
                {
                    "stato_fattura_codice_interno": r["stato_fattura_codice_interno"],
                    "stato_fattura_codice": r["stato_fattura_codice"],
                    "n_attivita": r["n_attivita"],
                    "valore": r["valore"],
                    "valore_fatturato": r["valore_fatturato"],
                    "n_in_ritardo": r["n_in_ritardo"],
                    "valore_in_ritardo": r["valore_in_ritardo"],
                }
            )

    mesi: list[dict[str, object]] = []
    for mese_num in range(1, 13):
        competenza = date(anno, mese_num, 1).isoformat()
        stadi_mese = list(DASH_COMPETENZA_STADI) + stadi_extra.get(competenza, [])
        celle_mese = [
            (stadio, celle.get((competenza, stadio), _CellaCompetenza()))
            for stadio in stadi_mese
        ]
        # Totali di copertura del mese (blocco riepilogo, DB-6): il "fatturato"
        # e' l'imponibile riga; il "da fatturare" resta sul teorico degli stadi
        # non ancora fatturati. Calcolati qui (non nel FE): la scelta della
        # misura e' dominio, il FE rende soltanto.
        totale_teorico = sum((c.valore for _, c in celle_mese), Decimal(0))
        totale_fatturato = sum((c.valore_fatturato for _, c in celle_mese), Decimal(0))
        da_fatturare = sum(
            (c.valore for s, c in celle_mese if s != "FATTURATA"), Decimal(0)
        )
        mesi.append(
            {
                "competenza_mese": competenza,
                "stadi": [
                    _cella_stadio_payload(
                        s, c,
                        *_stato_fatture_cella(
                            s, c, competenza, fatture_per_cella, stadi_ko,
                        ),
                    )
                    for s, c in celle_mese
                ],
                "totali": {
                    "valore_teorico": str(totale_teorico),
                    "valore_fatturato": str(totale_fatturato),
                    "valore_da_fatturare": str(da_fatturare),
                    "n_in_ritardo": sum(c.n_in_ritardo for _, c in celle_mese),
                },
                "n_errori": errori_per_mese.get(competenza, 0),
            }
        )
    return {"anno": anno, "mesi": mesi}


# Scopo: Restituisce il drill-down paginato delle attivita' di un mese di
#        competenza (Lente 1, grana attivita'), con filtro opzionale per
#        stadio del funnel e per recuperi tardivi (emessa_in_ritardo).
#        La competenza viene normalizzata al 1° del mese (bucket mensile).
# Perimetro: sola lettura; scope emittente DB-side (GUC fail-closed in vista).
# Risultato: dict con count, page, page_size, total_pages, results.
def fn_dash_competenza_attivita(
    *,
    competenza_mese: date,
    stadio: str | None = None,
    solo_ritardo: bool = False,
    order_by: str | None = None,
    order_dir: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, object]:
    _validate_enum(
        stadio,
        allowed=DASH_COMPETENZA_STADI,
        param_name="stadio",
        function_name="vendite.vendite_service.fn_dash_competenza_attivita",
    )
    # Ordinamento server-side (convenzione order_by/order_dir come le liste
    # standard): whitelist della lista + direzione asc/desc, fail-fast 400 —
    # nessun input grezzo entra nell'ORDER BY. Assenti -> default repository.
    ErrorManager.require(
        order_by is None
        or order_by in VenditeRepository.DASH_COMPETENZA_ATTIVITA_SORT_COLUMNS,
        code="E_VENDITE_VALIDATION",
        message="Colonna di ordinamento non valida.",
        detail=(
            f"order_by='{order_by}' non ammesso. Valori: "
            f"{', '.join(sorted(VenditeRepository.DASH_COMPETENZA_ATTIVITA_SORT_COLUMNS))}."
        ),
        context={"order_by": order_by},
        function_name="vendite.vendite_service.fn_dash_competenza_attivita",
    )
    ErrorManager.require(
        order_dir is None or order_dir.lower() in ("asc", "desc"),
        code="E_VENDITE_VALIDATION",
        message="Direzione di ordinamento non valida.",
        detail="order_dir deve essere 'asc' o 'desc'.",
        context={"order_dir": order_dir},
        function_name="vendite.vendite_service.fn_dash_competenza_attivita",
    )
    offset = _validate_pagination(
        page, page_size, "vendite.vendite_service.fn_dash_competenza_attivita"
    )
    repository = VenditeRepository()
    results: list[DashCompetenzaAttivitaRow]
    results, total_count = repository.list_dash_competenza_attivita(
        competenza_mese=competenza_mese.replace(day=1),
        stadio=stadio,
        solo_ritardo=solo_ritardo,
        order_by=order_by,
        order_dir=order_dir,
        limit=page_size,
        offset=offset,
    )
    # Pagina EFFETTIVA, non quella richiesta: il repository clampa l'offset
    # all'ultima pagina reale, quindi l'envelope deve dichiarare la pagina che
    # le righe rappresentano davvero. Era l'ultimo dei sei endpoint dei
    # cruscotti a non farlo.
    return _build_list_response(
        results, total_count, _pagina_effettiva(page, page_size, total_count), page_size
    )


# Scopo: Drill-down AGGREGATO per commessa della Lente 1 (DEC-4): una riga per
#        commessa nel perimetro (mese + stadio + solo_ritardo) invece della grana
#        attivita' — risolve la commessa "ripetuta" nella lista; il dettaglio a
#        grana attivita' vive nel drawer di gestione. Stessa validazione della
#        lista a grana attivita' (stadio whitelist, order_by/order_dir, pagina).
# Perimetro: sola lettura; scope emittente DB-side (GUC fail-closed nella vista).
# Risultato: dict con count (n commesse), page, page_size, total_pages, results.
def fn_dash_competenza_commesse(
    *,
    competenza_mese: date,
    stadio: str | None = None,
    solo_ritardo: bool = False,
    order_by: str | None = None,
    order_dir: str | None = None,
    page: int = 1,
    page_size: int = 50,
    # Export (BB `build_dash_export_response`): valorizzato = perimetro intero
    # in una volta, paginazione saltata. Assente = lista paginata di sempre.
    max_rows: int | None = None,
) -> dict[str, object]:
    _validate_enum(
        stadio,
        allowed=DASH_COMPETENZA_STADI,
        param_name="stadio",
        function_name="vendite.vendite_service.fn_dash_competenza_commesse",
    )
    ErrorManager.require(
        order_by is None
        or order_by in VenditeRepository.DASH_COMPETENZA_COMMESSE_SORT_COLUMNS,
        code="E_VENDITE_VALIDATION",
        message="Colonna di ordinamento non valida.",
        detail=(
            f"order_by='{order_by}' non ammesso. Valori: "
            f"{', '.join(sorted(VenditeRepository.DASH_COMPETENZA_COMMESSE_SORT_COLUMNS))}."
        ),
        context={"order_by": order_by},
        function_name="vendite.vendite_service.fn_dash_competenza_commesse",
    )
    ErrorManager.require(
        order_dir is None or order_dir.lower() in ("asc", "desc"),
        code="E_VENDITE_VALIDATION",
        message="Direzione di ordinamento non valida.",
        detail="order_dir deve essere 'asc' o 'desc'.",
        context={"order_dir": order_dir},
        function_name="vendite.vendite_service.fn_dash_competenza_commesse",
    )
    limit, offset = _paging_o_export(
        page=page, page_size=page_size, max_rows=max_rows,
        function_name="vendite.vendite_service.fn_dash_competenza_commesse",
    )
    repository = VenditeRepository()
    results: list[DashCompetenzaCommessaRow]
    results, total_count = repository.list_dash_competenza_commesse(
        competenza_mese=competenza_mese.replace(day=1),
        stadio=stadio,
        solo_ritardo=solo_ritardo,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    return _build_list_response(
        results, total_count, _pagina_effettiva(page, page_size, total_count), page_size
    )


# Scopo: Elenco dei GRUPPI FATTURABILI di un mese/stadio — l'unita' su cui
#        agisce l'emissione mirata. Restituisce la pagina E il riepilogo di
#        perimetro nella STESSA risposta: la riga di totali («7 documenti · 29
#        attivita' · 12.500 €») e' la sola riconciliazione onesta con la card
#        del funnel, e tenerla in un secondo endpoint significherebbe due
#        chiamate che possono raccontare due momenti diversi.
# Perimetro: sola lettura; scope emittente DB-side (viste security_invoker,
#        fail-closed senza GUC operatore).
# Risultato: dict con count, page, page_size, total_pages, results, riepilogo.
def fn_dash_competenza_gruppi(
    *,
    competenza_mese: date,
    stadio: str | None = None,
    tipo_gruppo: str | None = None,
    # Filtro CLIENTE (D-3): l'asse e' il BA di FATTURAZIONE, cioe' lo stesso
    # elemento che `fn_build_fattura_key` mette in chiave. `ba_non_determinabile`
    # e' la voce «cliente non determinabile» (D-5) — l'ASSENZA di quel valore, non
    # un id sentinella: un 0 o un -1 in un campo che porta chiavi vere prima o poi
    # finisce confrontato con una PK.
    ba_fatturazione_id: int | None = None,
    ba_non_determinabile: bool = False,
    search: str | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    page: int = 1,
    page_size: int = 50,
    # Export (BB `build_dash_export_response`): valorizzato = perimetro intero
    # in una volta, paginazione saltata. Assente = lista paginata di sempre.
    max_rows: int | None = None,
) -> dict[str, object]:
    _validate_enum(
        stadio,
        allowed=DASH_COMPETENZA_STADI,
        param_name="stadio",
        function_name="vendite.vendite_service.fn_dash_competenza_gruppi",
    )
    ErrorManager.require(
        order_by is None
        or order_by in VenditeRepository.DASH_COMPETENZA_GRUPPI_SORT_COLUMNS,
        code="E_VENDITE_VALIDATION",
        message="Colonna di ordinamento non valida.",
        detail=(
            f"order_by='{order_by}' non ammesso. Valori: "
            f"{', '.join(sorted(VenditeRepository.DASH_COMPETENZA_GRUPPI_SORT_COLUMNS))}."
        ),
        context={"order_by": order_by},
        function_name="vendite.vendite_service.fn_dash_competenza_gruppi",
    )
    ErrorManager.require(
        order_dir is None or order_dir.lower() in ("asc", "desc"),
        code="E_VENDITE_VALIDATION",
        message="Direzione di ordinamento non valida.",
        detail="order_dir deve essere 'asc' o 'desc'.",
        context={"order_dir": order_dir},
        function_name="vendite.vendite_service.fn_dash_competenza_gruppi",
    )
    # ⚠️ Ricerca sotto la soglia: si IGNORA, non si solleva e non si svuota la
    # lista. Il termine arriva mentre l'operatore sta ancora digitando — un 400
    # al secondo carattere sarebbe un errore per un'azione legittima, e una
    # lista vuota gli direbbe «non c'e' niente» quando la verita' e' «non ti ho
    # ancora cercato». Il filtro entra al terzo carattere (SEARCH_MIN_LEN, la
    # soglia sta nel repository perche' vale anche per l'export).
    termine = (search or "").strip()
    search_attiva = len(termine) >= SEARCH_MIN_LEN
    search_param = termine if search_attiva else None
    limit, offset = _paging_o_export(
        page=page, page_size=page_size, max_rows=max_rows,
        function_name="vendite.vendite_service.fn_dash_competenza_gruppi",
    )
    repository = VenditeRepository()
    competenza = competenza_mese.replace(day=1)
    results: list[DashCompetenzaGruppoRow]
    results, total_count = repository.list_dash_competenza_gruppi(
        competenza_mese=competenza,
        stadio=stadio,
        tipo_gruppo=tipo_gruppo,
        ba_fatturazione_id=ba_fatturazione_id,
        ba_non_determinabile=ba_non_determinabile,
        search=search_param,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    payload = _build_list_response(
        results, total_count, _pagina_effettiva(page, page_size, total_count), page_size
    )
    # Due perimetri DIVERSI nella stessa risposta, ed e' voluto:
    #  - `riepilogo` SEGUE tutti i filtri (tipo, cliente, ricerca): e' la
    #    riconciliazione della lista che l'utente sta guardando, e un totale che
    #    descrive un perimetro diverso dalle righe sopra di se' e' peggio di
    #    nessun totale;
    #  - `tipi` e `clienti` (le due facet) NON li seguono: devono mostrare tutte
    #    le voci disponibili anche quando una e' selezionata, altrimenti
    #    scegliendo «Preventivi» le altre sparirebbero dalla tendina e non si
    #    potrebbe piu' cambiare idea senza azzerare il filtro alla cieca.
    #    ⚠️ Entrambe sul perimetro BASE (competenza+stadio) e non una sull'altra:
    #    se `clienti` seguisse il tipo e `tipi` no, le due tendine
    #    racconterebbero perimetri diversi e il conteggio cambierebbe a seconda
    #    dell'ORDINE in cui l'operatore sceglie i filtri.
    payload["riepilogo"] = repository.get_dash_competenza_gruppi_riepilogo(
        competenza_mese=competenza,
        stadio=stadio,
        tipo_gruppo=tipo_gruppo,
        ba_fatturazione_id=ba_fatturazione_id,
        ba_non_determinabile=ba_non_determinabile,
        search=search_param,
    )
    payload["tipi"] = repository.list_dash_competenza_gruppi_tipi(
        competenza_mese=competenza,
        stadio=stadio,
    )
    payload["clienti"] = repository.list_dash_competenza_gruppi_clienti(
        competenza_mese=competenza,
        stadio=stadio,
    )
    return payload


@dataclass
class _ClasseBacklog:
    # Scopo: Accumulatore tipizzato del pivot riepilogo backlog per classe
    #        (somme su Decimal/int, serializzazione a stringa in uscita).
    #        anzianita_max_giorni resta None finche' nessuna riga ha una
    #        anzianita' nota: "eta' sconosciuta" NON e' "0 giorni".
    n_documenti: int = 0
    valore_fermo_tot: Decimal = Decimal(0)
    unita_ferme_tot: int = 0
    anzianita_max_giorni: int | None = None
    aree: list[dict[str, object]] = field(default_factory=list)


# Scopo: Restituisce i contatori di testata della Lente 2 Backlog: le 3
#        classi di azionabilita' SEMPRE presenti nell'ordine UI del design
#        (🟠 recuperabile · 🔵 sollecito cliente · 🔴 anomalia), ognuna con
#        totale documenti/valore/unita'/anzianita' massima e il dettaglio per
#        area. Eventuali classi NON in whitelist emesse dalla vista vengono
#        accodate dopo le 3 note, MAI perse in silenzio (fail-visible, stesso
#        principio della Lente 1 e della lookup motivi_fermo).
# Perimetro: sola lettura; scope emittente DB-side (RLS invoker + GUC).
# Risultato: dict {classi: [{classe, n_documenti, valore_fermo_tot,
#        unita_ferme_tot, anzianita_max_giorni, aree: [...]}]}.
def fn_dash_backlog_riepilogo() -> dict[str, object]:
    repository = VenditeRepository()
    rows = repository.list_dash_backlog_riepilogo()

    acc: dict[str, _ClasseBacklog] = {}
    classi_extra: list[str] = []
    for r in rows:
        classe = acc.get(r["classe"])
        if classe is None:
            classe = _ClasseBacklog()
            acc[r["classe"]] = classe
            if r["classe"] not in DASH_BACKLOG_CLASSI:
                classi_extra.append(r["classe"])
        classe.n_documenti += r["n_documenti"]
        if r["valore_fermo_tot"] is not None:
            classe.valore_fermo_tot += Decimal(r["valore_fermo_tot"])
        classe.unita_ferme_tot += r["unita_ferme_tot"]
        if r["anzianita_max_giorni"] is not None:
            classe.anzianita_max_giorni = max(
                classe.anzianita_max_giorni or 0, r["anzianita_max_giorni"]
            )
        classe.aree.append(
            {
                "area": r["area"],
                "n_documenti": r["n_documenti"],
                "valore_fermo_tot": r["valore_fermo_tot"],
                "unita_ferme_tot": r["unita_ferme_tot"],
                "anzianita_max_giorni": r["anzianita_max_giorni"],
            }
        )

    classi: list[dict[str, object]] = []
    for nome in list(DASH_BACKLOG_CLASSI) + classi_extra:
        c = acc.get(nome, _ClasseBacklog())
        classi.append(
            {
                "classe": nome,
                "n_documenti": c.n_documenti,
                "valore_fermo_tot": str(c.valore_fermo_tot),
                "unita_ferme_tot": c.unita_ferme_tot,
                "anzianita_max_giorni": c.anzianita_max_giorni,
                "aree": c.aree,
            }
        )
    return {"classi": classi}


# Scopo: Restituisce la lista paginata del backlog (Lente 2): documenti
#        non-collegati non-verdi per anzianita' (i piu' vecchi prima), con
#        filtri opzionali per classe di azionabilita' e area del funnel.
#        Il filtro classe NON e' whitellistato di proposito (coerenza
#        fail-visible col riepilogo, che accoda le classi fuori whitelist):
#        una classe futura del CHECK di config.motivi_fermo resta drillabile
#        senza toccare il BE; una classe inesistente da' lista vuota, mai 400.
#        L'area invece e' strutturale (discriminante fissa della union) e
#        resta whitellistata.
# Perimetro: sola lettura; scope emittente DB-side (RLS invoker + GUC).
# Risultato: dict con count, page, page_size, total_pages, results.
def fn_dash_backlog_documenti(
    *,
    classe: str | None = None,
    area: str | None = None,
    ritardo_giorni: int | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    page: int = 1,
    page_size: int = 50,
    # Export (BB `build_dash_export_response`): valorizzato = perimetro intero
    # in una volta, paginazione saltata. Assente = lista paginata di sempre.
    max_rows: int | None = None,
) -> dict[str, object]:
    _validate_enum(
        area,
        allowed=DASH_FATTURAZIONE_AREE,
        param_name="area",
        function_name="vendite.vendite_service.fn_dash_backlog_documenti",
    )
    # Filtro "fermo da oltre N giorni": soglia positiva o assente (una soglia
    # non-positiva non ha senso; niente normalizzazione silenziosa). Speculare
    # al filtro ritardo della Situazione aperta.
    ErrorManager.require(
        ritardo_giorni is None or ritardo_giorni > 0,
        code="E_VENDITE_VALIDATION",
        message="Parametro ritardo_giorni non valido.",
        detail="ritardo_giorni deve essere un intero positivo (o assente).",
        context={"ritardo_giorni": ritardo_giorni},
        function_name="vendite.vendite_service.fn_dash_backlog_documenti",
    )
    # Ordinamento server-side (convenzione order_by/order_dir come le liste
    # standard): whitelist della lista + direzione asc/desc, fail-fast 400 —
    # nessun input grezzo entra nell'ORDER BY. Assenti -> default repository
    # (i piu' "fermo da" prima).
    ErrorManager.require(
        order_by is None or order_by in VenditeRepository.DASH_BACKLOG_SORT_COLUMNS,
        code="E_VENDITE_VALIDATION",
        message="Colonna di ordinamento non valida.",
        detail=(
            f"order_by='{order_by}' non ammesso. Valori: "
            f"{', '.join(sorted(VenditeRepository.DASH_BACKLOG_SORT_COLUMNS))}."
        ),
        context={"order_by": order_by},
        function_name="vendite.vendite_service.fn_dash_backlog_documenti",
    )
    ErrorManager.require(
        order_dir is None or order_dir.lower() in ("asc", "desc"),
        code="E_VENDITE_VALIDATION",
        message="Direzione di ordinamento non valida.",
        detail="order_dir deve essere 'asc' o 'desc'.",
        context={"order_dir": order_dir},
        function_name="vendite.vendite_service.fn_dash_backlog_documenti",
    )
    limit, offset = _paging_o_export(
        page=page, page_size=page_size, max_rows=max_rows,
        function_name="vendite.vendite_service.fn_dash_backlog_documenti",
    )
    repository = VenditeRepository()
    results: list[DashBacklogDocumentoRow]
    results, total_count = repository.list_dash_backlog_documenti(
        classe=classe,
        area=area,
        ritardo_giorni=ritardo_giorni,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    return _build_list_response(
        results, total_count, _pagina_effettiva(page, page_size, total_count), page_size
    )


# Scopo: Restituisce la lista paginata degli errori vivi della fatturazione
#        (blocco 4 Lente 1: task run in ERRORE non superati + fatture
#        critical), con filtro opzionale per mese di competenza (normalizzato
#        al 1° del mese).
# Perimetro: sola lettura; scope emittente DB-side (GUC fail-closed in vista).
# Risultato: dict con count, page, page_size, total_pages, results.
def fn_dash_competenza_errori(
    *,
    competenza_mese: date | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    page: int = 1,
    page_size: int = 50,
    # Export (BB `build_dash_export_response`): valorizzato = perimetro intero
    # in una volta, paginazione saltata. Assente = lista paginata di sempre.
    max_rows: int | None = None,
) -> dict[str, object]:
    # Ordinamento server-side (8° lotto liste, 2026-08-03): whitelist +
    # direzione validate qui, fail-fast 400 — stessa forma delle altre liste
    # dash. Assenti -> ordine storico (eventi recenti prima).
    ErrorManager.require(
        order_by is None
        or order_by in VenditeRepository.DASH_COMPETENZA_ERRORI_SORT_COLUMNS,
        code="E_VENDITE_VALIDATION",
        message="Colonna di ordinamento non valida.",
        detail=(
            f"order_by='{order_by}' non ammesso. Valori: "
            f"{', '.join(sorted(VenditeRepository.DASH_COMPETENZA_ERRORI_SORT_COLUMNS))}."
        ),
        context={"order_by": order_by},
        function_name="vendite.vendite_service.fn_dash_competenza_errori",
    )
    ErrorManager.require(
        order_dir is None or order_dir.lower() in ("asc", "desc"),
        code="E_VENDITE_VALIDATION",
        message="Direzione di ordinamento non valida.",
        detail="order_dir deve essere 'asc' o 'desc'.",
        context={"order_dir": order_dir},
        function_name="vendite.vendite_service.fn_dash_competenza_errori",
    )
    limit, offset = _paging_o_export(
        page=page, page_size=page_size, max_rows=max_rows,
        function_name="vendite.vendite_service.fn_dash_competenza_errori",
    )
    repository = VenditeRepository()
    results: list[DashCompetenzaErroreRow]
    results, total_count = repository.list_dash_competenza_errori(
        competenza_mese=(
            competenza_mese.replace(day=1) if competenza_mese is not None else None
        ),
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    return _build_list_response(
        results, total_count, _pagina_effettiva(page, page_size, total_count), page_size
    )


# Tipi documento con endpoint /passaggi/ (nodo lineage con vista di dominio).
# COMMESSA aggiunta nella Fase C (genealogia inversa, design §7.3): non ha una
# lista/CRUD propria, ma il suo nodo lineage è consultabile via drawer leggero
# (sorgenti che l'hanno generata + fatture a valle). FATTURA resta nodo
# terminale senza endpoint (Q4: capolinea, nessuna superficie propria).
LINEAGE_TIPI_DOCUMENTO: tuple[str, ...] = (
    "PREVENTIVO",
    "OFFERTA_COMMERCIALE",
    "ORDINE_VENDITA",
    "CONTRATTO",
    "DDT_VENDITA",
    "RESO_VENDITA",
    "COMMESSA",
)


# Scopo: Orchestrazione del pannello "Passaggi" (genealogia documento):
#        valida il tipo, traduce il doc_id di dominio nella chiave nodo
#        polimorfa (key_selector da config.sorgenti), legge la summary
#        lineage (nodo + pratica + frontiera) e il traversal in ENTRAMBE
#        le direzioni (origine + destinazioni, decisione P-2 del brief).
# Perimetro: sola lettura; RLS emittente applicata dalle viste invoker.
# Risultato: dict {nodo, pratica|None, frontiera|None, avanti[], indietro[]}.
def get_documento_passaggi(
    tipo_codice: str, documento_id: int
) -> dict[str, object]:
    _validate_enum(
        tipo_codice,
        allowed=LINEAGE_TIPI_DOCUMENTO,
        param_name="tipo_codice",
        function_name="get_documento_passaggi",
        nullable=False,
    )
    ErrorManager.require(
        isinstance(documento_id, int) and documento_id > 0,
        code="E_VENDITE_VALIDATION",
        message="Identificativo documento non valido.",
        detail=f"documento_id={documento_id!r}",
        function_name="get_documento_passaggi",
        log_to_db=False,
    )

    repo = VenditeRepository()

    # Sorgente dal vocabolario (id + key_selector + target_table): assenza =
    # seed config incoerente, non input utente.
    sorgente = repo.get_lineage_sorgente(tipo_codice)
    ErrorManager.require(
        sorgente is not None,
        code="E_VENDITE_VALIDATION",
        message="Tipo documento non configurato in config.sorgenti.",
        detail=f"tipo_codice={tipo_codice}",
        function_name="get_documento_passaggi",
    )
    assert sorgente is not None

    # Chiave nodo nativa polimorfa: id::text oppure uid dalla tabella target.
    node_uid = repo.resolve_lineage_node_uid(
        target_table=sorgente["target_table"],
        key_selector=sorgente["key_selector"],
        doc_id=documento_id,
    )
    ErrorManager.require(
        node_uid is not None,
        code="E_VENDITE_NOT_FOUND",
        message="Documento non trovato.",
        detail=f"tipo_codice={tipo_codice} documento_id={documento_id}",
        function_name="get_documento_passaggi",
        log_to_db=False,
    )
    assert node_uid is not None

    nodo = repo.get_lineage_nodo(tipo_id=sorgente["id"], node_uid=node_uid)
    ErrorManager.require(
        nodo is not None,
        code="E_VENDITE_NOT_FOUND",
        message="Documento non trovato.",
        detail=f"tipo_codice={tipo_codice} documento_id={documento_id}",
        function_name="get_documento_passaggi",
        log_to_db=False,
    )
    assert nodo is not None

    # Pratica difensiva (Q5): oggetto solo se collegata.
    pratica: dict[str, object] | None = None
    if nodo["pratica_id"] is not None:
        pratica = {
            "pratica_id": nodo["pratica_id"],
            "pratica_numero": nodo["pratica_numero"],
            "n_pratiche": nodo["n_pratiche"],
        }

    # Frontiera normalizzata: la summary, per costruzione, per un nodo senza
    # discendenti indica il nodo stesso -> per il FE e' "non transitato" (None).
    frontiera: dict[str, object] | None = None
    is_self = (
        nodo["frontiera_tipo_id"] == nodo["tipo_id"]
        and nodo["frontiera_uid"] == nodo["uid"]
    )
    if nodo["is_transitato"] and nodo["frontiera_tipo_id"] is not None and not is_self:
        frontiera = {
            "tipo_codice": nodo["frontiera_tipo_codice"],
            "codice": nodo["frontiera_codice"],
            "stato_codice_interno": nodo["frontiera_stato_codice_interno"],
            "fase": nodo["frontiera_fase"],
            "n_discendenti_attivi": nodo["n_discendenti_attivi"],
        }

    avanti = repo.list_lineage_passaggi(
        tipo_id=sorgente["id"], node_uid=node_uid, direzione="avanti"
    )
    indietro = repo.list_lineage_passaggi(
        tipo_id=sorgente["id"], node_uid=node_uid, direzione="indietro"
    )

    return {
        "nodo": {
            "tipo_codice": nodo["tipo_codice"],
            "codice": nodo["codice"],
            "stato_codice_interno": nodo["stato_codice_interno"],
            "stato_descrizione": nodo["stato_descrizione"],
            "fase": nodo["fase"],
            "is_abortito": nodo["is_abortito"],
            "is_transitato": nodo["is_transitato"],
            "n_discendenti_diretti": nodo["n_discendenti_diretti"],
            "n_discendenti_attivi": nodo["n_discendenti_attivi"],
            "n_sorgenti": nodo["n_sorgenti"],
        },
        "pratica": pratica,
        "frontiera": frontiera,
        "avanti": avanti,
        "indietro": indietro,
    }


# ------------------------------------------------------------------
# Dettaglio fattura (drawer di consultazione)
# brief-be-fe-drawer-fattura §5
# ------------------------------------------------------------------

_FN_FATTURA_DETTAGLIO = "vendite.vendite_service.get_fattura_dettaglio"


# Scopo: Documento fattura completo per la consultazione a video: testata
#        (cliente + emittente + pagamento + totali gia' decodificati), righe,
#        riepilogo IVA e piano rate, in una sola risposta.
#        Perimetro: SOLA LETTURA, nessun ricalcolo. Gli stessi quattro lettori
#        alimentano il contesto del PDF (`FatturaDocumentContextBuilder`), quindi
#        video e stampa raccontano lo stesso documento per costruzione — regola
#        R17, non disciplina del chiamante.
#        Risultato: {fattura, righe, riepilogo_iva, scadenze, contatori}.
#        `contatori` alimenta i badge della barra azioni del drawer senza un
#        secondo round-trip: oggi solo `note` (il sub-drawer note e' separato e
#        il padre non ne carica la lista). E' un dict e non uno scalare
#        `note_count` per reggere i prossimi badge (documenti generati,
#        allegati) senza cambiare la shape della risposta.
#
# ⚠️ ORDINE VINCOLANTE — testata PRIMA, 404, poi i satelliti.
#    `vendite.fatture` ha la RLS attiva (`rls_fatture_ef_whitelist` +
#    `rls_fatture_ba_ownership`) e il ruolo dell'app vi e' soggetto: una fattura
#    fuori scope non e' leggibile e qui diventa 404.
#
#    Aggiornamento 2026-07-29: dal changeset RLS satelliti anche `fatture_righe`
#    e `fatture_riepiloghi_iva` hanno le proprie policy (operatore `FOR ALL` via
#    `fn_scope_ef_whitelist_via_fattura`, portale `FOR SELECT` via
#    `fn_scope_ba_ownership_via_fattura`). Verificato: 8 righe reali, **0**
#    visibili senza GUC — prima erano 8 su 8.
#    L'ordine resta vincolante, ma per due ragioni diverse da prima:
#      1. e' il 404 unificato — senza il cancello si restituirebbe un documento
#         a meta' (testata assente, satelliti vuoti) invece di un errore netto;
#      2. i satelliti protetti sono DUE, non tutti: `note_fatture`,
#         `fatture_indirizzi`, `fatture_fondi_fattura`, `fatture_sdi` restano
#         senza policy. Qualunque lettura futura che li aggiunga qui e' coperta
#         solo dal fatto che si passa prima dalla testata. E' esattamente il
#         caso del conteggio note aggiunto per il badge: `note_fatture` non ha
#         RLS, quindi quel COUNT su una fattura fuori scope risponderebbe —
#         non lo fa solo perche' il cancello sopra ha gia' chiuso con 404.
#    Cfr. brief-db-rls-satelliti-fattura-portale (chiuso 2026-07-29).
def get_fattura_dettaglio(
    *,
    fattura_id: int,
    auth_user_id: int | None = None,
) -> dict[str, object]:
    ErrorManager.require(
        bool(fattura_id and fattura_id > 0),
        code="E_VENDITE_VALIDATION",
        message="Parametri non validi.",
        detail="fattura_id obbligatorio e > 0",
        context={"fattura_id": fattura_id},
        function_name=_FN_FATTURA_DETTAGLIO,
        log_to_db=True,
    )
    repository = VenditeRepository()

    # 1. IL CANCELLO. Scope applicativo (auth_user_id) sommato alla RLS.
    testata = repository.get_fattura_testata(fattura_id, auth_user_id=auth_user_id)
    if testata is None:
        # Inesistente e fuori scope danno la STESSA risposta: un 404 che
        # distinguesse i due casi confermerebbe l'esistenza di una fattura di
        # un altro emittente (api.md §Scope emittente).
        ErrorManager.raise_error(
            code="E_FATTURA_NON_TROVATA",
            message="Fattura non trovata.",
            detail=f"Nessuna fattura accessibile con id={fattura_id}",
            context={"fattura_id": fattura_id},
            function_name=_FN_FATTURA_DETTAGLIO,
            log_to_db=True,
        )
    assert testata is not None

    # 2. Solo ORA i satelliti: la testata ha gia' autorizzato l'accesso.
    #    Il conteggio note passa dal service del BB note (`count_per_target`,
    #    nato "per badge UI" e finora senza consumer): stessa porta della lista
    #    note esposta dall'API, quindi un domani i due perimetri non possono
    #    divergere. Oggi non filtra su `visibile`, esattamente come la lista
    #    (`include_invisible=True` di default) — il badge non "salta" quando il
    #    sub-drawer note si aggiorna da solo.
    return {
        "fattura": dict(testata),
        "righe": repository.list_fattura_righe(fattura_id),
        "riepilogo_iva": repository.list_fattura_riepilogo_iva(fattura_id),
        "scadenze": repository.list_fattura_scadenze(fattura_id),
        "contatori": {
            "note": PartitionedNoteService(repo=NOTE_REPO_FATTURA).count_per_target(
                target_id=fattura_id,
            ),
        },
    }


# =====================================================================
# Fondi fattura — elenco dei casi che chiedono una persona (BE-3)
# =====================================================================

_FN_FONDI_DA_DECIDERE = "vendite.vendite_service.fn_fondi_fattura_da_decidere"


# Scopo: Restituisce l'elenco paginato dei fondi fattura «da decidere»
#        (vendite.vw_fondi_fattura_da_decidere), filtrabile per motivo.
# Obiettivo: dare una sede alle quattro situazioni in cui il giro automatico si
#        FERMA e lascia la scelta a una persona. Non e' un cruscotto di
#        controllo: e' la coda del lavoro che l'automatismo non puo' fare.
# Perimetro: SOLA LETTURA. Nessun ricalcolo del fondo in Python e nessuna
#        scrittura — la promessa di F-1 (il fondo e' un ATTO, scritto una volta
#        e mai riscritto) cade nel momento in cui un secondo posto tocca un
#        importo. Il BE chiama e legge.
# Risultato: dict con count, page, page_size, total_pages, results.
def fn_fondi_fattura_da_decidere(
    *,
    motivo: str | None = None,
    auth_user_id: int | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, object]:
    # Filtro motivo sulla whitelist ORDINATA dei quattro motivi della vista:
    # fail-fast 400 invece di una lista vuota silenziosa, che su un vocabolario
    # chiuso e' indistinguibile da «non c'e' niente da decidere».
    _validate_enum(
        motivo,
        allowed=FONDI_DA_DECIDERE_MOTIVI,
        param_name="motivo",
        function_name=_FN_FONDI_DA_DECIDERE,
    )
    # Ordinamento: default risolti QUI (data, desc) e validati col BB condiviso
    # `validate_order_params` — non un'altra copia inline del blocco
    # order_by/order_dir (regola del 2: in questo file ce n'erano gia' sei).
    order_by, order_dir = validate_order_params(
        order_by or "data",
        (order_dir or "desc").lower(),
        allowed_columns=frozenset(VenditeRepository.FONDI_DA_DECIDERE_SORT_COLUMNS),
        error_code="E_VENDITE_VALIDATION",
        function_name=_FN_FONDI_DA_DECIDERE,
    )
    offset = _validate_pagination(page, page_size, _FN_FONDI_DA_DECIDERE)

    repository = VenditeRepository()
    results: list[FondoFatturaDaDecidereRow]
    results, total_count = repository.list_fondi_fattura_da_decidere(
        motivo=motivo,
        auth_user_id=auth_user_id,
        order_by=order_by,
        order_dir=order_dir,
        limit=page_size,
        offset=offset,
    )
    return _build_list_response(
        results, total_count, _pagina_effettiva(page, page_size, total_count), page_size
    )


# ══════════════════════════════════════════════════════════════════
#  Situazione merce (pannello ordine/DDT)
#  brief-design-situazione-merce-ordine + brief-design-partita-merce-
#  generalizzata §21.2. Sola lettura: nessun verbo, nessun side-effect.
# ══════════════════════════════════════════════════════════════════

_FN_SITUAZIONE_MERCE = "vendite.vendite_service.get_situazione_merce"


# Scopo: Compone la «situazione della merce» di UN documento — ordine o DDT —
#        in un round-trip solo.
# Contesto: e' il pannello del cantiere 2. Le fonti sono quattro viste DB della
#        partita generalizzata, tutte `security_invoker=on`: la RLS del
#        chiamante si applica da sola e NON si passa `auth_user_id`.
# Input: esattamente uno fra `ordine_id` e `ddt_id`.
# Output: dict con `righe_ordine` (livello 1, solo lato ordine), `partite`
#        (livello 2), `accrediti` e `riconsegne` (le due code di lavoro).
# Regole:
#  - il cancello di perimetro e' la TESTATA (`vendite.ordini` / `vendite.ddt`
#    hanno la RLS, le righe no): documento invisibile → 404, indistinguibile da
#    inesistente, come il dettaglio fattura;
#  - ⛔ NON si ri-traduce il verso del saldo: `stato` arriva gia' tradotto dalle
#    viste (sei valori sull'ordine, sei sulla partita) — due traduzioni
#    divergono e diventano due frasi per lo stesso numero;
#  - ⛔ NON si trasforma `differenza = NULL` in `0`: NULL significa «il conto non
#    si applica» (riga mai spedita, causale non fatturabile, conto non
#    calcolabile). Un `COALESCE` qui rimetterebbe dentro i falsi allarmi che il
#    cantiere della partita ha appena tolto.
# Dipendenze DB: `vw_situazione_merce_ordine`, `vw_partite_merce`,
#        `vw_resi_da_accreditare`, `vw_resi_da_riconsegnare`.
def get_situazione_merce(
    *,
    ordine_id: int | None = None,
    ddt_id: int | None = None,
) -> dict[str, object]:
    # Guard di programmazione, non di input utente: le due view di dominio
    # passano sempre e solo il proprio id.
    ErrorManager.require(
        (ordine_id is None) != (ddt_id is None),
        code="E_VENDITE_VALIDATION",
        message="Situazione merce: indicare un ordine oppure un DDT.",
        detail=f"ordine_id={ordine_id} ddt_id={ddt_id}",
        function_name=_FN_SITUAZIONE_MERCE,
    )

    repository = VenditeRepository()

    # Cancello di perimetro PRIMA di qualunque lettura di dettaglio: le viste
    # sotto leggono righe che la RLS non protegge da sole, e senza questo passo
    # un documento fuori scope tornerebbe un pannello VUOTO invece di un 404 —
    # cioe' «non ho il permesso di saperlo» presentato come «non c'e' nulla».
    if ordine_id is not None:
        ErrorManager.require(
            repository.exists_ordine(ordine_id),
            code="E_VENDITE_NOT_FOUND",
            message="Ordine non trovato.",
            detail=f"ordine_id={ordine_id}",
            function_name=_FN_SITUAZIONE_MERCE,
        )
    else:
        # Il guard in testa garantisce che qui `ddt_id` sia valorizzato; l'assert
        # e' per il type checker (convenzione AGENTS.md post-require).
        assert ddt_id is not None
        ErrorManager.require(
            repository.exists_ddt(ddt_id),
            code="E_VENDITE_NOT_FOUND",
            message="DDT non trovato.",
            detail=f"ddt_id={ddt_id}",
            function_name=_FN_SITUAZIONE_MERCE,
        )

    # Livello 1 — il riassunto per riga d'ordine. Esiste SOLO sul lato ordine:
    # sul DDT la domanda e' «cosa e' successo a QUESTA spedizione» (§5.1 del
    # brief pannello), e le righe d'ordine che il DDT non ha toccato non
    # c'entrano. Lista vuota e non `None`: il frontend itera sempre.
    righe_ordine: list[dict[str, object]] = []
    if ordine_id is not None:
        righe_ordine = repository.list_situazione_merce_ordine(ordine_id)

    return {
        "righe_ordine": righe_ordine,
        "partite": repository.list_partite_merce(
            ordine_id=ordine_id, ddt_id=ddt_id
        ),
        "accrediti": repository.list_situazione_merce_accrediti(
            ordine_id=ordine_id, ddt_id=ddt_id
        ),
        "riconsegne": repository.list_situazione_merce_riconsegne(
            ordine_id=ordine_id, ddt_id=ddt_id
        ),
    }
