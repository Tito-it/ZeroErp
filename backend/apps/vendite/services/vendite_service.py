# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade applicativa generica per lo schema vendite (liste, ricerche, stato entita').
# ------------------------------------------------------------

# Contiene operazioni facade generiche sullo schema vendite,
# non legate a un sottodominio specifico (pipeline, reset, ecc.).

import math
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import validate_enum_param, validate_pagination
from apps.vendite.db.vendite_repository import (
    DASH_APERTO_AREE,
    DASH_APERTO_FASI,
    DASH_BACKLOG_CLASSI,
    DASH_COMPETENZA_STADI,
    DASH_FATTURAZIONE_AREE,
    DASH_FATTURAZIONE_AREE_EURO,
    VenditeRepository,
)
from apps.vendite.types import (
    DashApertoDocumentoRow,
    DashApertoRiepilogoRow,
    DashBacklogDocumentoRow,
    DashCompetenzaAttivitaRow,
    DashCompetenzaErroreRow,
    LottoFattureRow,
    LottoListRow,
)

_SORT_BY_VALIDI: tuple[str, ...] = ("fattura_id", "nominativo", "totale_doc")
_SORT_DIR_VALIDI: tuple[str, ...] = ("asc", "desc")


# Scopo: Valida page/page_size con E_VENDITE_VALIDATION e restituisce l'offset calcolato.
# Riutilizzabile da tutte le funzioni di lista dello schema vendite.
def _validate_pagination(page: int, page_size: int, function_name: str) -> int:
    return validate_pagination(
        page, page_size, error_code="E_VENDITE_VALIDATION", function_name=function_name,
    )


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
        limit=page_size,
        offset=offset,
    )
    return _build_list_response(results, total_count, page, page_size)


# Scopo: Restituisce elenco fatture di un lotto con decodifiche, filtri e ordinamento opzionali.
# Obiettivo: esporre lista paginata per lotto con validazione parametri.
# Perimetro: sola lettura; delega query a VenditeRepository.
# Risultato: dict con count, page, page_size, total_pages, results.
def fn_list_lotto_fatture(
    *,
    lotto_id: int,
    stato_esecuzione: str | None = None,
    esclusa: bool | None = None,
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
        esclusa=esclusa,
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
    # Scopo: Accumulatore tipizzato del pivot Situazione aperta per
    #        (area, fase): somme native su Decimal/int, serializzazione a
    #        stringa UNA volta in uscita.
    n_documenti: int = 0
    n_aperti: int = 0
    valore_totale: Decimal = Decimal(0)
    valore_transitato: Decimal = Decimal(0)


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
        "n_aperti": cella.n_aperti,
        "valore_totale": str(cella.valore_totale) if con_valori else None,
        "valore_transitato": str(cella.valore_transitato) if con_valori else None,
    }


# Scopo: Restituisce il riepilogo della Situazione aperta (stock documenti
#        senza asse temporale, §6-bis design due-lenti): le 4 aree documento
#        SEMPRE presenti nell'ordine del funnel, ognuna con totali di area e
#        griglia per fase normalizzata (4 fasi SEMPRE presenti nell'ordine del
#        ciclo di vita — DL-13: la vista e' neutra, il FE decide quali card
#        mostrare), piu' il vocabolario `fasi` top-level (alimenta i filtri FE
#        senza contrabbandarlo dalla griglia di un'area). Aree o fasi NON in
#        whitelist emesse dalla vista vengono accodate dopo le note, MAI perse
#        in silenzio (fail-visible); un'area extra che porta VALORI li espone
#        (decisione data-driven, non la whitelist euro statica: niente euro
#        persi in silenzio).
# Perimetro: sola lettura; scope emittente DB-side (RLS invoker).
# Risultato: dict {aree: [{area, n_documenti, n_aperti, valore_totale,
#        valore_transitato, fasi: [...]}] x4+, fasi: [...] x4+}.
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
        cella.n_aperti += r["n_aperti"]
        if r["valore_totale"] is not None:
            cella.valore_totale += Decimal(r["valore_totale"])
            aree_con_valori.add(r["area"])
        if r["valore_transitato"] is not None:
            cella.valore_transitato += Decimal(r["valore_transitato"])
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
            totale.n_aperti += c.n_aperti
            totale.valore_totale += c.valore_totale
            totale.valore_transitato += c.valore_transitato
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


# Scopo: Restituisce il drill-down paginato della Situazione aperta: stock
#        dei documenti vivi delle 4 aree, ordinati per "in essere da" (i piu'
#        vecchi prima), con filtri opzionali area/fase e solo_aperti (default
#        True: la pagina e' la "Situazione aperta" — il giudizio sospeso dei
#        contratti conta aperto; False = fotografia completa, CHIUSO
#        transitati inclusi). NESSUNO dei due filtri e' whitellistato, di
#        proposito (coerenza fail-visible col riepilogo, che accoda aree e
#        fasi fuori whitelist E le rende cliccabili come card FE): un'area o
#        fase futura resta drillabile senza toccare il BE; un valore
#        sconosciuto — o COMMESSE, esclusa dal WHERE della vista — da' lista
#        vuota, mai 400.
# Perimetro: sola lettura; scope emittente DB-side (RLS invoker).
# Risultato: dict con count, page, page_size, total_pages, results.
def fn_dash_aperto_documenti(
    *,
    area: str | None = None,
    fase: str | None = None,
    solo_aperti: bool | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, object]:
    # UNICA definizione del default di pagina (None = parametro omesso):
    # la view passa il raw, il FE manda sempre un valore esplicito.
    solo_aperti = True if solo_aperti is None else solo_aperti
    offset = _validate_pagination(
        page, page_size, "vendite.vendite_service.fn_dash_aperto_documenti"
    )
    repository = VenditeRepository()
    results: list[DashApertoDocumentoRow]
    results, total_count = repository.list_dash_aperto_documenti(
        area=area,
        fase=fase,
        solo_aperti=solo_aperti,
        limit=page_size,
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
def _cella_stadio_payload(stadio: str, cella: _CellaCompetenza) -> dict[str, object]:
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
                "stadi": [_cella_stadio_payload(s, c) for s, c in celle_mese],
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
    page: int = 1,
    page_size: int = 50,
) -> dict[str, object]:
    _validate_enum(
        stadio,
        allowed=DASH_COMPETENZA_STADI,
        param_name="stadio",
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
        limit=page_size,
        offset=offset,
    )
    return _build_list_response(results, total_count, page, page_size)


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
    page: int = 1,
    page_size: int = 50,
) -> dict[str, object]:
    _validate_enum(
        area,
        allowed=DASH_FATTURAZIONE_AREE,
        param_name="area",
        function_name="vendite.vendite_service.fn_dash_backlog_documenti",
    )
    offset = _validate_pagination(
        page, page_size, "vendite.vendite_service.fn_dash_backlog_documenti"
    )
    repository = VenditeRepository()
    results: list[DashBacklogDocumentoRow]
    results, total_count = repository.list_dash_backlog_documenti(
        classe=classe,
        area=area,
        limit=page_size,
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
    page: int = 1,
    page_size: int = 50,
) -> dict[str, object]:
    offset = _validate_pagination(
        page, page_size, "vendite.vendite_service.fn_dash_competenza_errori"
    )
    repository = VenditeRepository()
    results: list[DashCompetenzaErroreRow]
    results, total_count = repository.list_dash_competenza_errori(
        competenza_mese=(
            competenza_mese.replace(day=1) if competenza_mese is not None else None
        ),
        limit=page_size,
        offset=offset,
    )
    return _build_list_response(
        results, total_count, _pagina_effettiva(page, page_size, total_count), page_size
    )
