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
from typing import Any


from apps.config.db.sorgenti_repository import SorgentiRepository
from apps.config.sorgenti import (
    SORGENTE_COMMESSA,
    SORGENTE_CONTRATTO,
    SORGENTE_DDT_VENDITA,
    SORGENTE_FATTURA,
    SORGENTE_OFFERTA_COMMERCIALE,
    SORGENTE_ORDINE_VENDITA,
    SORGENTE_PREVENTIVO,
    SORGENTE_RESO_VENDITA,
)
from apps.core.db._helpers import richiedi_codice_a_vocabolario
from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT
from apps.core.api.payload_validators import envelope_da_offset
from apps.core.services.payload_helpers import translate_db_errors
from apps.core.services.capability_blob import capabilities_o_vuoto
from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import (
    validate_enum_param,
    validate_order_params,
)
from apps.core.services.parameter_service import ParameterService
from apps.core.services.partitioned_note_service import contatori_documento
from apps.core.services.testata_guard import pagina_dopo_testata
from apps.vendite.db.fatture_repository import FattureRepository
from apps.vendite.db.note_repositories import NOTE_REPO_FATTURA
from apps.vendite.db.vendite_repository import (
    GIORNALE_GRAVITA,
    GIORNALE_SORT_COLUMNS,
    LOTTO_FATTURE_SORT_COLUMNS,
    LOTTO_GRUPPI_SORT_COLUMNS,
    MOTIVO_NON_FATTURATA_RESIDUO,
    DASH_APERTO_AREE,
    DASH_APERTO_FASI,
    FASI_DOCUMENTO,
    DASH_BACKLOG_CLASSI,
    DASH_COMPETENZA_STADI,
    DASH_FATTURAZIONE_AREE,
    DASH_FATTURAZIONE_AREE_EURO,
    FONDI_DA_DECIDERE_MOTIVI,
    STATI_ESECUZIONE_DOCUMENTO,
    STATI_ESECUZIONE_LOTTO,
    VenditeRepository,
)
from apps.vendite.services._lotto_perimetro import lotto_visibile
from apps.vendite.types import (
    DashApertoDocumentoRow,
    DashApertoRiepilogoRow,
    DashBacklogDocumentoRow,
    DashCompetenzaAttivitaRow,
    DashCompetenzaResiduoRow,
    DashCompetenzaCommessaRow,
    DashCompetenzaErroreRow,
    DashCompetenzaGruppoRow,
    FondoFatturaDaDecidereRow,
    LottoFattureRow,
    LottoGruppoRow,
    LottoListRow,
)

logger = logging.getLogger(__name__)

# ⚠️ DUE ELENCHI SULLO STESSO REQUISITO, e devono restare allineati: qui si
# valida l'input (400 parlante al chiamante), nel repository si traduce in SQL
# (`LOTTO_FATTURE_SORT_COLUMNS`). Il presidio e' il test `test_..._order_by_fuori_whitelist`.
# ⭐ Derivato dal repository invece di riscritto: alla terza aggiunta di colonna
# (BE-1, 2026-08-22, da 3 a 11) copiare i nomi a mano sarebbe stato il modo
# sicuro per farne divergere uno — e la divergenza si vede solo dal lato che
# rifiuta, cioe' come «ordinamento non ammesso» su una colonna che c'e'.
_SORT_BY_VALIDI: tuple[str, ...] = tuple(LOTTO_FATTURE_SORT_COLUMNS)


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
#        Senza `max_rows` la finestra e' quella chiesta: dal 2026-10-21 le
#        liste parlano `limit`/`offset` (la view li legge con `pagina_da_query`,
#        che li riporta nei limiti), e la traduzione da `page`/`page_size` che
#        stava qui non c'e' piu'.
def _paging_o_export(
    *, limit: int, offset: int, max_rows: int | None, function_name: str,
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
    return limit, offset


# Scopo: wrapper di dominio su `validate_order_params` — riempie l'`error_code`
#        di vendite e ammette l'assenza (`None` = ordine di default del
#        repository, cioe' quello dichiarato a catalogo).
#
# ⭐ E' un WRAPPER, non un secondo guard: la prima stesura di questa passata
#    riscriveva i due `ErrorManager.require` in casa, e il BB che li fa esisteva
#    da giugno — usato tredici volte, una delle quali in QUESTO stesso file
#    (`fn_list_lotto_fatture`). Il catalogo BB e' la prima difesa contro questa
#    specie di duplicato, e va letto PRIMA di estrarre, non dopo.
#    Stessa forma di `_validate_enum` qui sotto, per la stessa ragione.
#
# ⭐ Nessun `lower()` qui: dal 2026-09-26 il BB giudica la direzione con
#    `order_dir_ammessa` (maiuscole e spazi ammessi ovunque). Il `lower()` che
#    stava qui compensava il confronto case-sensitive di allora.
def _valida_ordinamento(
    order_by: str | None,
    order_dir: str | None,
    *,
    whitelist: dict[str, str],
    function_name: str,
) -> None:
    validate_order_params(
        order_by,
        order_dir,
        allowed_columns=whitelist,
        error_code="E_VENDITE_VALIDATION",
        function_name=function_name,
        nullable=True,
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


# La data piu' vecchia che il filtro «ritardo» delle dashboard puo' chiedere
# (brief-db-parametro-data-minima-ritardo-dashboard, decisione di Tid 2026-10-08).
_PARAM_RITARDO_DATA_MINIMA = "VENDITE_DASHBOARD_RITARDO_DATA_MINIMA"


# Scopo: La soglia «da oltre N giorni» delle dashboard aperto e backlog (lista
#        ed export): assente, oppure un intero > 0 che non porti `oggi - N`
#        prima di VENDITE_DASHBOARD_RITARDO_DATA_MINIMA. Fuori ->
#        E_VENDITE_VALIDATION; niente normalizzazione silenziosa (DL-17).
# ⭐ Il pavimento e' una scelta di DOMINIO (quanto indietro ha senso chiedere),
#    non il tipo: il tetto `integer` di `qp_int_optional` resta, ma da solo
#    lasciava passare N per cui `oggi - N giorni` esce da `timestamp`
#    (`DataError`, cioe' un 500 al posto di un 400).
# ⭐ Si legge il DEFAULT del parametro, non la cascata (D-1 del brief: limite
#    uguale per tutti, nessun override previsto).
# ⭐ Il confronto e' fra interi di giorni, mai `oggi - timedelta(N)`: con N
#    enorme sarebbe Python a sollevare (OverflowError), di nuovo un 500.
# ℹ️ Regola del 2: fino al 2026-10-09 il solo `> 0` era copiato nelle due
#    dashboard, con due detail diversi.
def _valida_ritardo_giorni(
    ritardo_giorni: int | None,
    *,
    function_name: str,
) -> None:
    if ritardo_giorni is None:
        return
    ErrorManager.require(
        ritardo_giorni > 0,
        code="E_VENDITE_VALIDATION",
        message="Parametro ritardo_giorni non valido.",
        detail="ritardo_giorni deve essere un intero positivo (o assente).",
        context={"ritardo_giorni": ritardo_giorni},
        function_name=function_name,
    )
    data_minima = ParameterService().get_default_date(_PARAM_RITARDO_DATA_MINIMA)
    massimo = (oggi_aziendale() - data_minima).days
    ErrorManager.require(
        ritardo_giorni <= massimo,
        code="E_VENDITE_VALIDATION",
        message="Parametro ritardo_giorni non valido.",
        detail=(
            f"Il ritardo non puo' risalire prima del {data_minima.isoformat()}: "
            f"oggi al massimo {massimo} giorni."
        ),
        context={
            "ritardo_giorni": ritardo_giorni,
            "data_minima": data_minima.isoformat(),
        },
        function_name=function_name,
    )


# Scopo: L'envelope di una lista dei cruscotti, con la pagina EFFETTIVAMENTE
#        servita: il repository (`_query_paged_view`) riporta un offset oltre
#        la fine all'ultima pagina (rientro da pagina stantia, in una sola
#        valutazione della union), e l'envelope deve dichiarare quella — il FE
#        la adotta (`usePagedDashFetch` sincronizza la pagina dalla risposta).
# ⚠️ Solo per le liste il cui repository riporta l'offset; le altre usano
#    `envelope_da_offset` diretto.
def _envelope_pagina_effettiva(
    results: list, total_count: int, *, limit: int, offset: int,
) -> dict[str, Any]:
    envelope = envelope_da_offset(results, total_count, limit=limit, offset=offset)
    if total_count > 0 and limit > 0:
        envelope["page"] = min(envelope["page"], math.ceil(total_count / limit))
    else:
        envelope["page"] = 1
    return envelope


# Scopo: I filtri della lista lotti che la query non sa rifiutare, validati in
#        un posto solo per la lista e per il suo export (gemelli: un filtro
#        sbagliato e' un 400 in entrambi, mai una lista o un file vuoti).
#        - `stato_lotto` nel suo vocabolario (`config.stati_lotto_job`);
#        - ⛔ «Recuperi del mese» ha senso solo RISPETTO A UN MESE: senza,
#          il predicato diventa `competenza_mese < NULL`, cioe' zero righe.
def _valida_filtri_lotti(
    *,
    stato_lotto: str | None,
    competenza_mese: date | None,
    solo_recuperi_mese: bool,
    function_name: str,
) -> None:
    # Il vocabolario dello stato del job e' una tabella (`config.stati_lotto_job`,
    # F-4): si legge da li', non da una costante che la ricopia.
    richiedi_codice_a_vocabolario(
        "config.stati_lotto_job", "codice_interno", stato_lotto,
        codice_errore="E_VENDITE_VALIDATION", parametro="stato_lotto",
        function_name=function_name,
    )
    ErrorManager.require(
        not solo_recuperi_mese or competenza_mese is not None,
        code="E_VENDITE_VALIDATION",
        message="Parametri non validi.",
        detail="competenza_mese obbligatoria per i recuperi del mese",
        context={"parametro": "competenza_mese"},
        function_name=function_name,
        log_to_db=False,
    )


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
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    solo_recuperi_mese: bool = False,
    includi_annullati: bool = False,
) -> dict[str, Any]:
    _valida_filtri_lotti(
        stato_lotto=stato_lotto,
        competenza_mese=competenza_mese,
        solo_recuperi_mese=solo_recuperi_mese,
        function_name="vendite.vendite_service.fn_list_lotti",
    )
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
        limit=limit,
        offset=offset,
        solo_recuperi_mese=solo_recuperi_mese,
        includi_annullati=includi_annullati,
    )
    risposta = envelope_da_offset(results, total_count, limit=limit, offset=offset)
    # ⭐ La ripartizione per stato viaggia NELLA STESSA risposta della lista, e
    #    non su un endpoint suo: cosi' i pulsanti-filtro e le righe sotto
    #    vengono dalla stessa valutazione del perimetro e non possono
    #    raccontare due cose diverse. Due chiamate separate potrebbero non
    #    concordare — basta un lotto che cambia stato fra l'una e l'altra — e i
    #    chip direbbero 5 dove la lista ne mostra 4.
    # ⚠️ Il perimetro e' quello della lista MENO il filtro stato: `stato_lotto`
    #    non si passa. Contandolo, scelto uno stato gli altri andrebbero a zero
    #    e i loro pulsanti sparirebbero — vedi `_lotti_where`.
    risposta["stati"] = [
        {"stato_lotto": stato, "n_lotti": n}
        for stato, n in sorted(
            repository.count_lotti_per_stato(
                competenza_mese=competenza_mese,
                utility_id=utility_id,
                area_geografica_id=area_geografica_id,
                tipo_doc_fiscale_id=tipo_doc_fiscale_id,
                emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
                auth_user_id=auth_user_id,
                solo_recuperi_mese=solo_recuperi_mese,
                includi_annullati=includi_annullati,
            ).items()
        )
    ]
    # ⭐ Quanti lotti annullati il perimetro sta NASCONDENDO (2026-09-12): senza
    #    questo numero «mese pulito» e «tre lotti annullati» si leggono uguali.
    #    A interruttore acceso non c'e' niente di nascosto, e il conteggio non si
    #    paga. Stesso perimetro della lista, stato compreso: e' «quante righe
    #    QUESTO filtro lascia fuori» (pattern `archiviate_count` delle code).
    risposta["annullati_count"] = 0 if includi_annullati else repository.count_lotti_annullati(
        competenza_mese=competenza_mese,
        utility_id=utility_id,
        stato_lotto=stato_lotto,
        area_geografica_id=area_geografica_id,
        tipo_doc_fiscale_id=tipo_doc_fiscale_id,
        emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
        auth_user_id=auth_user_id,
        solo_recuperi_mese=solo_recuperi_mese,
    )
    return risposta


# Scopo: Estrae i lotti per l'EXPORT (CSV/XLSX), con gli stessi filtri e lo
#        stesso ordinamento della lista a video — così il file rispecchia ciò
#        che l'operatore stava guardando.
#
#        Perché non passa da `fn_list_lotti`: quella riceve la finestra della
#        lista, che la view riporta al tetto di 200 righe (`pagina_da_query`).
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
    solo_recuperi_mese: bool = False,
    includi_annullati: bool = False,
) -> tuple[list[LottoListRow], int]:
    # ⛔ Stessi filtri della lista, validati dallo stesso helper: un filtro
    #    sbagliato e' un 400 anche qui, mai un file VUOTO consegnato come se
    #    fosse la risposta.
    _valida_filtri_lotti(
        stato_lotto=stato_lotto,
        competenza_mese=competenza_mese,
        solo_recuperi_mese=solo_recuperi_mese,
        function_name="vendite.vendite_service.fn_export_lotti",
    )
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
        solo_recuperi_mese=solo_recuperi_mese,
        includi_annullati=includi_annullati,
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
def fn_lotti_mensile(
    *, anno: int, auth_user_id: int | None = None, includi_annullati: bool = False,
) -> dict[str, Any]:
    ErrorManager.require(
        isinstance(anno, int) and _DASH_ANNO_MIN <= anno <= _DASH_ANNO_MAX,
        code="E_VENDITE_VALIDATION",
        message="Anno non valido.",
        detail=f"anno deve essere un intero tra {_DASH_ANNO_MIN} e {_DASH_ANNO_MAX}.",
        context={"anno": anno},
        function_name="vendite.vendite_service.fn_lotti_mensile",
    )
    repository = VenditeRepository()
    per_mese = repository.count_lotti_per_mese(
        anno=anno, auth_user_id=auth_user_id, includi_annullati=includi_annullati,
    )
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
#        Il blob viaggia intatto SOTTO `capabilities`, non fuso nella testata
#        (api.md §«Il blob sta SOTTO `capabilities`», 2026-09-23). ⚠️ Fuso,
#        il suo `tipo_lotto` sovrascriveva quello della testata: stesso valore
#        oggi, ma era una collisione che nessuno avrebbe visto cambiare.
#
#        Fallback graceful (pattern offerte/contratti): se il capability layer
#        e' rotto (DatabaseError) si logga e si ritorna la testata con
#        `capabilities` VUOTO — la chiave c'e' sempre.
#        Il FE degrada a sola consultazione (nessuna azione), ma l'operatore
#        vede comunque il lotto — una rottura delle capability non deve
#        impedire la lettura dell'entita'.
def fn_get_lotto(*, lotto_id: int, auth_user_id: int | None = None) -> dict[str, Any]:
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
    lotto = lotto_visibile(
        lotto_id=lotto_id, auth_user_id=auth_user_id,
        function_name="vendite.vendite_service.fn_get_lotto", repository=repository,
    )
    result = dict(lotto)
    result["capabilities"] = capabilities_o_vuoto(
        lambda: repository.get_available_actions_lotto(lotto_id),
        funzione="fn_available_actions_lotto", entita_id=lotto_id, logger=logger,
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
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    max_rows: int | None = None,
) -> dict[str, Any]:
    # ⭐ L'helper condiviso, non un `if` scritto qui: l'export SALTA la
    # paginazione invece di violarne il tetto, ed e' la stessa regola di tutte
    # le altre liste esportabili del modulo.
    limit, offset = _paging_o_export(
        limit=limit, offset=offset, max_rows=max_rows,
        function_name="vendite.vendite_service.fn_list_lotto_fatture",
    )
    # ⛔ Colonna e direzione col BB `validate_order_params` (2026-09-26), non
    #    con due `_validate_enum`: la direzione aveva qui un suo insieme
    #    `("asc", "desc")` case-sensitive, cioe' `DESC` era un 400 su questa
    #    lista e passava sulle altre. Il BB giudica con `order_dir_ammessa`.
    # `nullable`: una direzione assente resta None, e il verso lo decide il BB
    # del repository (`sql_order_clause`: date DESC). Fino al 2026-10-20 il
    # default era `"asc"` e la regola non arrivava mai alla query (§6.1).
    order_by, order_dir = validate_order_params(
        order_by,
        order_dir,
        allowed_columns=_SORT_BY_VALIDI,
        error_code="E_VENDITE_VALIDATION",
        function_name="vendite.vendite_service.fn_list_lotto_fatture",
        nullable=True,
    )
    # ⛔ Il vocabolario della FATTURA (non quello del documento, che ha in piu'
    #    ESCLUSO): prima un valore sbagliato — anche `OK`, che la doc stessa
    #    proponeva — rispondeva lista vuota (2026-10-20).
    _validate_enum(
        stato_esecuzione, allowed=STATI_ESECUZIONE_LOTTO, param_name="stato_esecuzione",
        function_name="vendite.vendite_service.fn_list_lotto_fatture",
    )
    # ⛔ Il cancello di perimetro PRIMA dell'elenco (vedi `_lotto_perimetro`):
    #    lo scope nella query da solo dava `200 []` su un lotto fuori perimetro.
    repository = VenditeRepository()
    lotto_visibile(
        lotto_id=lotto_id, auth_user_id=auth_user_id,
        function_name="vendite.vendite_service.fn_list_lotto_fatture", repository=repository,
    )
    results: list[LottoFattureRow]
    results, total_count = repository.list_lotto_fatture(
        lotto_id=lotto_id,
        stato_esecuzione=stato_esecuzione,
        auth_user_id=auth_user_id,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
        max_rows=max_rows,
    )
    return envelope_da_offset(results, total_count, limit=limit, offset=offset)


# Scopo: I DOCUMENTI CHE UN LOTTO HA PRESO IN CARICO, con l'esito di ciascuno.
# Obiettivo: rispondere a «quale documento di questo giro non e' passato, e
#        perche'» — la domanda a cui la scheda «Documenti» non puo' rispondere,
#        perche' elenca le FATTURE e un documento caduto prima di diventarne una
#        non ha niente a cui appendersi (brief-db-esito-gruppo-lotto §0).
# Perimetro: sola lettura; il cancello di scope e' la TESTATA del lotto —
#        ne' `fatturazione_lotti_gruppi` ne' `fatturazione_lotti_esiti` hanno
#        RLS, `fatturazione_lotti` si'.
# Risultato: dict con count, page, page_size, total_pages, results.
def fn_list_lotto_gruppi(
    *,
    lotto_id: int,
    auth_user_id: int | None = None,
    stato_esecuzione: str | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    max_rows: int | None = None,
) -> dict[str, Any]:
    # ⚠️ Il vocabolario del DOCUMENTO, non quello comune: questa lista legge
    #    `fatturazione_lotti_esiti`, che dal 2026-09-08 ammette anche `ESCLUSO`.
    #    Con l'elenco comune il filtro «uscito dal giro» rispondeva **400 a una
    #    domanda buona** — il difetto in LETTURA che il cancello del vocabolario
    #    dichiara nella propria intestazione.
    _validate_enum(
        stato_esecuzione,
        allowed=STATI_ESECUZIONE_DOCUMENTO,
        param_name="stato_esecuzione",
        function_name="vendite.vendite_service.fn_list_lotto_gruppi",
    )
    _valida_ordinamento(
        order_by, order_dir,
        whitelist=LOTTO_GRUPPI_SORT_COLUMNS,
        function_name="vendite.vendite_service.fn_list_lotto_gruppi",
    )
    limit, offset = _paging_o_export(
        limit=limit, offset=offset, max_rows=max_rows,
        function_name="vendite.vendite_service.fn_list_lotto_gruppi",
    )
    # ⛔ Il cancello di perimetro PRIMA dell'elenco (vedi `_lotto_perimetro`).
    repository = VenditeRepository()
    lotto_visibile(
        lotto_id=lotto_id, auth_user_id=auth_user_id,
        function_name="vendite.vendite_service.fn_list_lotto_gruppi", repository=repository,
    )
    results: list[LottoGruppoRow]
    results, total_count = repository.list_lotto_gruppi(
        lotto_id=lotto_id,
        auth_user_id=auth_user_id,
        stato_esecuzione=stato_esecuzione,
        sort_by=order_by,
        # La direzione assente resta assente: la decide il BB della lista
        # (date DESC), non un `"asc"` scritto qui (2026-10-20, §6.1).
        sort_dir=order_dir,
        limit=limit,
        offset=offset,
        max_rows=max_rows,
    )
    # ⛔ NIENTE `perimetro_dichiarato`, e la sua sparizione e' il segno che il
    #    database ha risolto il problema invece di spostarlo (rev 2026-09-07).
    #    Serviva a distinguere «questo lotto non ha lavorato niente» da «questo
    #    lotto non dichiara un perimetro», perche' la lista leggeva il solo
    #    perimetro e i giri di massa non ne scrivono uno. Ora la lista legge
    #    ANCHE gli esiti, che ci sono su entrambi i tipi di giro: zero righe ha
    #    un significato solo — di questo lotto non risulta nessun documento.
    # ⚠️ Tolto e non lasciato «per compatibilita'»: un campo che non discrimina
    #    piu' niente e' peggio di un campo assente, perche' chi lo legge crede
    #    che discrimini.
    return envelope_da_offset(results, total_count, limit=limit, offset=offset)


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
) -> dict[str, Any]:
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
def fn_dash_aperto_riepilogo() -> dict[str, Any]:
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
    aree: list[dict[str, Any]] = []
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
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    # Export (BB `build_dash_export_response`): valorizzato = perimetro intero
    # in una volta, paginazione saltata. Assente = lista paginata di sempre.
    max_rows: int | None = None,
) -> dict[str, Any]:
    # ⛔ `area` e `fase` nel loro vocabolario, o un 400 sul campo: un valore
    #    sbagliato finiva nel WHERE e la lista rispondeva vuota con un 200
    #    (2026-10-20) — e col passaggio delle aree ai codici sorgente un client
    #    rimasto a `ORDINI` non avrebbe avuto nessun segnale.
    # ⚠️ Il vocabolario e' quello del MODELLO, non la whitelist del pivot: una
    #    sorgente vera fuori da `DASH_APERTO_AREE` (o una fase fuori da
    #    `DASH_APERTO_FASI`) e' la riga «extra» che il riepilogo accoda apposta
    #    (fail-visible), e il suo drill-down deve continuare a mostrarla.
    #    `COMMESSA` e `CHIUSO` sono codici veri che la vista non contiene: lista
    #    vuota legittima, non un errore.
    richiedi_codice_a_vocabolario(
        "config.sorgenti", "codice_interno", area,
        codice_errore="E_VENDITE_VALIDATION", parametro="area",
        function_name="vendite.vendite_service.fn_dash_aperto_documenti",
    )
    _validate_enum(
        fase, allowed=FASI_DOCUMENTO, param_name="fase",
        function_name="vendite.vendite_service.fn_dash_aperto_documenti",
    )
    _valida_ritardo_giorni(
        ritardo_giorni,
        function_name="vendite.vendite_service.fn_dash_aperto_documenti",
    )
    # Ordinamento server-side (convenzione order_by/order_dir come le liste
    # standard): whitelist della lista + direzione asc/desc, fail-fast 400 —
    # nessun input grezzo entra nell'ORDER BY. Assenti -> ordine di default
    # (i piu' "in essere da" prima) deciso dal repository.
    _valida_ordinamento(
        order_by, order_dir,
        whitelist=VenditeRepository.DASH_APERTO_SORT_COLUMNS,
        function_name="vendite.vendite_service.fn_dash_aperto_documenti",
    )
    limit, offset = _paging_o_export(
        limit=limit, offset=offset, max_rows=max_rows,
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
    return _envelope_pagina_effettiva(
        results, total_count, limit=limit, offset=offset,
    )


# La natura che si separa dalla copertura. Letterale UNICO: il vocabolario vive
# nel CHECK di `vendite.commesse_attivita.tipo_movimento` (NORMALE | RETTIFICA |
# ONERE) e un typo qui non romperebbe niente a runtime — filtrerebbe zero righe
# e il grafico tornerebbe a compensare in silenzio, cioe' il difetto di partenza.
TIPO_MOVIMENTO_RETTIFICA = "RETTIFICA"


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
    # ⭐ LA COPERTURA SI MISURA IN VALORE ASSOLUTO (2026-08-20, correzione di
    # Tid). Il saldo con segno non serve a rispondere «quanto del mese e' stato
    # portato a documento», perche' una nota di credito da emettere e' LAVORO DA
    # FARE quanto una fattura da emettere — vale meno zero euro di ricavo, ma
    # vale un documento da produrre.
    #
    # Le due misure sbagliate, in ordine di scoperta:
    #   · somma con segno       -> ad agosto il residuo era −29,50 e il grafico
    #                              segnava 101%. E con una fattura di pari
    #                              importo il residuo andrebbe a ZERO: «niente
    #                              da fare» con due documenti da produrre.
    #   · rettifiche ESCLUSE    -> il primo rimedio, e diceva 100%. Toglierle
    #                              dal conto le fa sparire come lavoro: e'
    #                              «coperto» mentre due note di credito
    #                              aspettano. Sbagliato allo stesso modo.
    # In assoluto agosto dice 99%, che e' la verita': quasi tutto fatturato,
    # resta 29,50 da accreditare.
    #
    # ⚠️ L'assoluto si prende sulla RIGA, non sull'aggregato: da quando
    # `tipo_movimento` e' nella grana (changeSet 20260820-07) ogni riga e'
    # OMOGENEA di segno — misurato: NORMALE e ONERE tutti positivi, RETTIFICA
    # tutti negativi. Sull'aggregato, positivi e negativi si annullerebbero
    # PRIMA dell'assoluto, cioe' la compensazione rientrerebbe dalla finestra.
    valore_abs: Decimal = Decimal(0)
    valore_fatturato_abs: Decimal = Decimal(0)
    # La quota RETTIFICA resta tracciata a parte, ma per DICHIARARLA sotto il
    # grafico: il donut dice quanto manca, questa dice che cos'e' quel che manca.
    n_rettifiche: int = 0
    valore_rettifiche: Decimal = Decimal(0)
    # Breakdown 3a per stato fattura. ⚠️ DIZIONARIO e non lista: da quando
    # `tipo_movimento` e' nella grana della vista (changeSet 20260820-07) lo
    # stesso stato arriva su PIU' righe — a luglio 2026 il bucket
    # FATTURATA/EMESSA si spezza in NORMALE (25 att.) + ONERE (1 att., 5.000 €).
    # Con l'`append` di prima quello stato compariva DUE VOLTE nel payload.
    # 🔴 E si vedeva solo su luglio: ad agosto la cardinalita' non cambia
    # affatto, quindi provare il solo mese del rilievo avrebbe detto «a posto».
    stati_fattura_per_stato: dict[str | None, dict[str, Any]] = field(default_factory=dict)
    # ⭐ La quota RESIDUA dentro `EMESSA_NON_FATTURATA`. Sta a parte e non
    # sostituisce il totale, perche' la card deve dire DUE cose: quanto lavoro
    # e' fermo in quello stadio, e quanta parte di quel lavoro **chiede
    # un'azione**. Le altre due situazioni dello stadio — giro in corso,
    # senza attivita' fatturabile — non chiedono niente, e
    # sommarle al residuo darebbe un numero solo per rimedi opposti.
    n_residui: int = 0
    valore_residui: Decimal = Decimal(0)
    # ⭐ Il lavoro che un GIRO ANCORA IN CORSO sta trattenendo, e che quindi
    # `n_attivita` non conta piu' (changeSet `20260909-67`). Stessa forma della
    # quota residua qui sopra, e per la stessa ragione: la card deve dire DUE
    # cose — quanto lavoro si puo' prendere, e quanto ce n'e' che non si puo'
    # prendere perche' e' gia' in mano a qualcuno.
    # ⛔ Senza questa meta' il numero cala e nessuno sa di quanto: «non c'e'
    # niente da fare» e «c'e' del lavoro in un giro vivo» si leggerebbero
    # uguali. Era il difetto del collaudo 09-09 girato di 180 gradi — li' la
    # card diceva 4 su un elenco di 3, qui direbbe 3 senza spiegare il quarto.
    n_trattenute: int = 0
    valore_trattenuto: Decimal = Decimal(0)


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
) -> dict[str, Any]:
    display = cella.valore_fatturato if stadio == "FATTURATA" else cella.valore
    return {
        "stadio": stadio,
        "n_attivita": cella.n_attivita,
        "valore": str(cella.valore),
        "valore_fatturato": str(cella.valore_fatturato),
        "valore_display": str(display),
        "n_in_ritardo": cella.n_in_ritardo,
        "valore_in_ritardo": str(cella.valore_in_ritardo),
        # ⭐ La quota che CHIEDE UN'AZIONE dentro lo stadio. Contratto
        # SIMMETRICO come tutto il resto della cella (DL-8): il campo c'e' su
        # ogni stadio e vale 0 dove non si applica — il frontend rende, non
        # deduce. Su `EMESSA_NON_FATTURATA` e' la meta' su cui vive il verbo
        # «Riporta da emettere»; l'altra meta' (n_attivita - n_residui) e'
        # transito legittimo e non va toccata.
        "n_residui": cella.n_residui,
        "valore_residui": str(cella.valore_residui),
        # ⭐ La quota TRATTENUTA da un giro ancora in corso. Contratto
        # simmetrico come il resto: il campo c'e' su ogni stadio e vale 0 dove
        # non si applica — e su `DA_EMETTERE` e' l'unico posto in cui la card
        # puo' spiegare perche' il suo numero e' piu' piccolo dell'elenco che
        # l'operatore ricorda.
        "n_trattenute": cella.n_trattenute,
        "valore_trattenuto": str(cella.valore_trattenuto),
        # Le voci del breakdown, serializzate qui una volta sola: dentro la
        # cella i valori restano Decimal (si sommano fra loro), fuori sono
        # stringhe come ogni altro importo del payload.
        "stati_fattura": [
            {k: (str(v) if isinstance(v, Decimal) else v) for k, v in voce.items()}
            for voce in cella.stati_fattura_per_stato.values()
        ],
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
) -> dict[str, Any]:
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
        cella.valore_abs += abs(Decimal(r["valore"]))
        cella.valore_fatturato_abs += abs(Decimal(r["valore_fatturato"]))
        if r["tipo_movimento"] == TIPO_MOVIMENTO_RETTIFICA:
            cella.n_rettifiche += r["n_attivita"]
            cella.valore_rettifiche += Decimal(r["valore"])
        # ⚠️ Si guarda il MOTIVO, non lo stadio: e' il motivo a dire se quella
        #    quota chiede un'azione. Sugli altri stadi e' `None` e la condizione
        #    e' falsa da se', senza bisogno di nominare `EMESSA_NON_FATTURATA`
        #    — cosi' il giorno che il vocabolario cresce non c'e' un secondo
        #    posto da aggiornare.
        if r.get("motivo_non_fatturata") == MOTIVO_NON_FATTURATA_RESIDUO:
            cella.n_residui += r["n_attivita"]
            # ⛔ NETTO, non assoluto: questo numero si legge SOTTO `valore` nella
            #    stessa card e SOPRA una lista che mostra il valore con segno.
            #    Con l'assoluto un residuo di RETTIFICA — che il verbo tocca
            #    eccome (Q-8) — direbbe «di cui 1 · 500,00 €» sotto un totale di
            #    -500,00 €: due meta' che non si sommano al tutto, e chi guarda
            #    non ha modo di capire quale delle due mente. L'assoluto ha una
            #    sede sola in questa funzione ed e' `valore_abs`, che serve al
            #    donut di copertura — dove non compensare e' proprio il punto.
            cella.valore_residui += Decimal(r["valore"])
        # ⭐ La quota che un giro in corso trattiene. ⚠️ Arriva GIA' esclusa da
        #    `n_attivita` e da `valore` (il `FILTER` sta nella vista): qui non
        #    si sottrae niente, si DICHIARA quanto e' stato tolto.
        cella.n_trattenute += r["n_attivita_trattenute"]
        cella.valore_trattenuto += Decimal(r["valore_trattenuto"])
        if r["stadio"] == "FATTURATA":
            # Una voce per STATO FATTURA, con i movimenti sommati dentro: il
            # breakdown risponde a «di cio' che e' fatturato, in che stato sono
            # le fatture», e la natura del movimento non e' quella domanda.
            voce = cella.stati_fattura_per_stato.get(r["stato_fattura_codice_interno"])
            if voce is None:
                voce = {
                    "stato_fattura_codice_interno": r["stato_fattura_codice_interno"],
                    "stato_fattura_codice": r["stato_fattura_codice"],
                    "n_attivita": 0,
                    "valore": Decimal(0),
                    "valore_fatturato": Decimal(0),
                    "n_in_ritardo": 0,
                    "valore_in_ritardo": Decimal(0),
                }
                cella.stati_fattura_per_stato[r["stato_fattura_codice_interno"]] = voce
            voce["n_attivita"] += r["n_attivita"]
            voce["valore"] += Decimal(r["valore"])
            voce["valore_fatturato"] += Decimal(r["valore_fatturato"])
            voce["n_in_ritardo"] += r["n_in_ritardo"]
            voce["valore_in_ritardo"] += Decimal(r["valore_in_ritardo"])

    mesi: list[dict[str, Any]] = []
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
        # ⭐ LA MISURA DI COPERTURA, in VALORE ASSOLUTO. I tre totali qui sopra
        # restano il NETTO e non cambiano (li leggono altri consumatori): questi
        # si aggiungono, e sono quelli che il grafico deve usare.
        # Ogni documento da produrre pesa per quello che vale, qualunque sia il
        # suo verso: il rapporto non puo' superare il 100% per costruzione, e
        # niente si compensa con niente.
        rettifiche_valore = sum((c.valore_rettifiche for _, c in celle_mese), Decimal(0))
        rettifiche_n = sum(c.n_rettifiche for _, c in celle_mese)
        copertura_fatturato = sum(
            (c.valore_fatturato_abs for _, c in celle_mese), Decimal(0)
        )
        # ⭐ Il residuo si legge in DUE VOCI SIMMETRICHE, non in una sola con una
        # nota a margine: «da addebitare» (le fatture da emettere) e «da
        # accreditare» (le note di credito da emettere). Sono lo stesso verbo —
        # produrre un documento — in due direzioni opposte, e chi guarda deve
        # poterle leggere con la stessa forma. La loro somma e' il residuo del
        # donut: nessuna delle due sta fuori dal conto.
        copertura_da_accreditare = sum(
            (abs(c.valore_rettifiche) for s, c in celle_mese if s != "FATTURATA"),
            Decimal(0),
        )
        copertura_da_fatturare = sum(
            (c.valore_abs for s, c in celle_mese if s != "FATTURATA"), Decimal(0)
        )
        copertura_da_addebitare = copertura_da_fatturare - copertura_da_accreditare
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
                    # La copertura in ASSOLUTO (ogni documento da produrre pesa
                    # per quello che vale, qualunque verso abbia) e le
                    # rettifiche dichiarate a parte, perche' il grafico dice
                    # QUANTO manca e questa dice CHE COSA manca.
                    "copertura_fatturato": str(copertura_fatturato),
                    # Il residuo intero (denominatore del donut) e le sue due
                    # voci: `da_addebitare + da_accreditare == da_fatturare`.
                    "copertura_da_fatturare": str(copertura_da_fatturare),
                    "copertura_da_addebitare": str(copertura_da_addebitare),
                    "copertura_da_accreditare": str(copertura_da_accreditare),
                    "rettifiche_valore": str(rettifiche_valore),
                    "rettifiche_n": rettifiche_n,
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
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> dict[str, Any]:
    _validate_enum(
        stadio,
        allowed=DASH_COMPETENZA_STADI,
        param_name="stadio",
        function_name="vendite.vendite_service.fn_dash_competenza_attivita",
    )
    # Ordinamento server-side (convenzione order_by/order_dir come le liste
    # standard): whitelist della lista + direzione asc/desc, fail-fast 400 —
    # nessun input grezzo entra nell'ORDER BY. Assenti -> default repository.
    _valida_ordinamento(
        order_by, order_dir,
        whitelist=VenditeRepository.DASH_COMPETENZA_ATTIVITA_SORT_COLUMNS,
        function_name="vendite.vendite_service.fn_dash_competenza_attivita",
    )
    repository = VenditeRepository()
    results: list[DashCompetenzaAttivitaRow]
    results, total_count = repository.list_dash_competenza_attivita(
        competenza_mese=competenza_mese.replace(day=1),
        stadio=stadio,
        solo_ritardo=solo_ritardo,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    # Pagina EFFETTIVA, non quella richiesta: il repository clampa l'offset
    # all'ultima pagina reale, quindi l'envelope deve dichiarare la pagina che
    # le righe rappresentano davvero. Era l'ultimo dei sei endpoint dei
    # cruscotti a non farlo.
    return _envelope_pagina_effettiva(
        results, total_count, limit=limit, offset=offset,
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
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    # Export (BB `build_dash_export_response`): valorizzato = perimetro intero
    # in una volta, paginazione saltata. Assente = lista paginata di sempre.
    max_rows: int | None = None,
) -> dict[str, Any]:
    _validate_enum(
        stadio,
        allowed=DASH_COMPETENZA_STADI,
        param_name="stadio",
        function_name="vendite.vendite_service.fn_dash_competenza_commesse",
    )
    _valida_ordinamento(
        order_by, order_dir,
        whitelist=VenditeRepository.DASH_COMPETENZA_COMMESSE_SORT_COLUMNS,
        function_name="vendite.vendite_service.fn_dash_competenza_commesse",
    )
    limit, offset = _paging_o_export(
        limit=limit, offset=offset, max_rows=max_rows,
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
    return _envelope_pagina_effettiva(
        results, total_count, limit=limit, offset=offset,
    )


# Numero massimo di attivita' per una sola chiamata del verbo. ⚠️ Non e' una
# soglia di prestazione: e' che oltre un certo punto «riporta indietro N righe»
# smette di essere un gesto che una persona ha guardato. La lista pagina a 200,
# ed e' lo stesso tetto.
MAX_ATTIVITA_RIPORTO = 200


# Scopo: Legge i motivi che impediscono il riporto, senza tentarlo. Serve
#        all'interfaccia per SPIEGARE invece di far fallire: il codice
#        `E_ATTIVITA_GIA_DA_EMETTERE` dichiara a catalogo che incontrarlo
#        significa che l'elenco a schermo era invecchiato.
# Risultato: {"motivi": [...]} — lista vuota se il verbo e' ammesso su tutte.
def fn_check_attivita_riportabili(*, attivita_fatturabili_ids: list[int]) -> dict[str, Any]:
    function_name = "vendite.vendite_service.fn_check_attivita_riportabili"
    ids = _valida_ids_riporto(attivita_fatturabili_ids, function_name=function_name)
    repository = VenditeRepository()
    with translate_db_errors(
        context={"op": function_name, "n_attivita": len(ids)},
        fallback_code="E_VENDITE_VALIDATION",
        fallback_message="Verifica delle attivita' da riportare non riuscita.",
    ):
        motivi = repository.check_attivita_riportabili_da_emettere(ids)
    return {"motivi": motivi}


# Scopo: «Riporta da emettere» — rimette in coda di fatturazione un elenco di
#        attivita' RESIDUE, cioe' rimaste senza fattura dopo che il documento
#        che le conteneva e' stato eliminato.
# Perimetro e risultato atteso: delega alla madre DB, che fa le due scritture e
#        l'evento di registro in una transazione sola. Il perimetro lo decide il
#        database (`fattura_riga_id IS NULL` + lucchetto + `COMPLETED`), non
#        questo service: ricalcolarlo qui sarebbe una seconda implementazione, e
#        la divergenza sarebbe silenziosa.
#        ⛔ SINCRONO: nessuna coda. Accodarlo per simmetria con «Rendi
#        definitive» importerebbe il problema della dedup, che qui non esiste.
# Risultato: {"riportate": n, "riemesse_attivita": n}.
def fn_riporta_attivita_da_emettere(
    *, attivita_fatturabili_ids: list[int],
) -> dict[str, Any]:
    function_name = "vendite.vendite_service.fn_riporta_attivita_da_emettere"
    ids = _valida_ids_riporto(attivita_fatturabili_ids, function_name=function_name)
    repository = VenditeRepository()
    # ⭐ `translate_db_errors` e non `raise_from_database_error`, ed e' una
    #    scelta: il secondo accetta il codice del database solo se il chiamante
    #    lo ha DICHIARATO in un elenco locale — cioe' una seconda copia del
    #    catalogo. I motivi qui sono cinque oggi; il vocabolario di questo
    #    dominio e' gia' cresciuto da tre a quattro valori senza che il backend
    #    lo sapesse, e una copia si sarebbe disallineata in silenzio.
    #    Cosi' invece un codice nuovo arriva all'operatore com'e', col suo
    #    messaggio, la sua `soluzione` e il suo BERSAGLIO — che qui non e' un
    #    dettaglio: la madre lo compone (prima la COMMESSA, poi la FATTURA) ed e'
    #    cio' che trasforma «non si puo'» in «apri la fattura 820».
    with translate_db_errors(
        context={"op": function_name, "n_attivita": len(ids)},
        fallback_code="E_VENDITE_VALIDATION",
        fallback_message="Riporto delle attivita' non riuscito.",
    ):
        return repository.riporta_attivita_da_emettere(ids)


# Scopo: normalizza e valida l'elenco di id del verbo, in una sede sola.
# ⛔ L'elenco VUOTO si rifiuta, e non e' pedanteria: passandolo, la madre
#    solleverebbe comunque (`E_ATTIVITA_RIPORTO_SELEZIONE_VUOTA`, TECNICO), ma
#    fermarlo qui evita un 500 per un errore di chiamante. E soprattutto un
#    elenco vuoto che passasse darebbe «zero attivita' riportate», cioe' un
#    messaggio identico a quello di un'operazione riuscita che non aveva niente
#    da fare — la stessa forma di silenzio che questo cantiere sta chiudendo.
def _valida_ids_riporto(ids: object, *, function_name: str) -> list[int]:
    ErrorManager.require(
        isinstance(ids, list) and len(ids) > 0,
        code="E_VENDITE_VALIDATION",
        message="Selezionare almeno un'attivita' da riportare.",
        detail="attivita_fatturabili_ids deve essere una lista non vuota.",
        context={"field": "attivita_fatturabili_ids"},
        function_name=function_name,
    )
    assert isinstance(ids, list)
    ErrorManager.require(
        all(isinstance(i, int) and not isinstance(i, bool) and i > 0 for i in ids),
        code="E_VENDITE_VALIDATION",
        message="Elenco di attivita' non valido.",
        detail="Ogni elemento di attivita_fatturabili_ids deve essere un intero positivo.",
        context={"field": "attivita_fatturabili_ids"},
        function_name=function_name,
    )
    ErrorManager.require(
        len(ids) <= MAX_ATTIVITA_RIPORTO,
        code="E_VENDITE_VALIDATION",
        message=f"Troppe attivita' selezionate (massimo {MAX_ATTIVITA_RIPORTO}).",
        detail=f"Ricevute {len(ids)} attivita'.",
        context={"field": "attivita_fatturabili_ids"},
        function_name=function_name,
    )
    # Dedup con ordine preservato: due volte lo stesso id e' la stessa riga, e
    # la madre lo tratterebbe una volta sola — ma il conteggio a video direbbe
    # un numero diverso da quello che si e' spuntato.
    return list(dict.fromkeys(ids))


# Scopo: Elenco dei RESIDUI di un mese di competenza — le attivita' fatturabili
#        rimaste senza fattura e che nessun giro riprendera' da solo. E'
#        l'elenco su cui agisce il verbo «Riporta da emettere», e la ragione per
#        cui esiste una lista invece di un contatore: il verbo agisce per riga,
#        quindi l'operatore deve vedere COSA sta riportando.
# Perimetro: sola lettura; scope emittente DB-side (vista `security_invoker`,
#        fail-closed senza GUC operatore). ⛔ Il filtro `RESIDUO` sta nel
#        repository e viene dalla vista: non si ricalcola qui.
# Risultato: dict con count, page, page_size, total_pages, results.
def fn_dash_competenza_residui(
    *,
    competenza_mese: date,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    # Export (BB `build_dash_export_response`), come le liste sorelle.
    max_rows: int | None = None,
) -> dict[str, Any]:
    # ⚠️ Nessun parametro `stadio`: la lista E' uno stadio, anzi una delle
    #    tre situazioni dentro `EMESSA_NON_FATTURATA`. Accettarlo darebbe
    #    all'invocante l'illusione di poter allargare il perimetro del verbo.
    _valida_ordinamento(
        order_by, order_dir,
        whitelist=VenditeRepository.DASH_COMPETENZA_RESIDUI_SORT_COLUMNS,
        function_name="vendite.vendite_service.fn_dash_competenza_residui",
    )
    limit, offset = _paging_o_export(
        limit=limit, offset=offset, max_rows=max_rows,
        function_name="vendite.vendite_service.fn_dash_competenza_residui",
    )
    repository = VenditeRepository()
    results: list[DashCompetenzaResiduoRow]
    results, total_count = repository.list_dash_competenza_residui(
        competenza_mese=competenza_mese.replace(day=1),
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    return _envelope_pagina_effettiva(
        results, total_count, limit=limit, offset=offset,
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
# Scopo: il codice leggibile di un registro di fatturazione — serve alla riga
#        «Filtri applicati» dell'export, dove un `registro_id=4` non dice niente
#        a chi apre il foglio un mese dopo su un'altra macchina.
# Risultato: il codice, oppure `None` se l'id non esiste (e allora chi chiama
#        lascia il valore grezzo: meglio un id di un'etichetta inventata).
def fn_get_registro_codice(registro_id: int) -> str | None:
    return VenditeRepository().get_registro_codice(int(registro_id))


# Etichetta di ripiego del sezionale quando il gruppo ne tocca piu' di uno.
# ⛔ ITALIANO NEL BACKEND, ed e' una deroga consapevole (D-4, decisa con Tid).
#    Il progetto compone le etichette nel FE via i18n — «cliente non
#    determinabile» e' fatto cosi' — ma quella strada lascerebbe la cella VUOTA
#    nell'export, che condivide questa stessa proiezione e legge i valori
#    grezzi (`ui.lista_colonna.campo_sorgente`), senza passare da nessuno slot.
#    Un export che tace dove la lista dice qualcosa e' peggio di un export che
#    parla una lingua sola.
# ⭐ E il FE NON legge questa stringa: ricompone la propria da `registri_n`
#    (chiave `col_registro_multi`), quindi a video resta bilingue. Le due
#    versioni non possono divergere perche' dipendono dallo STESSO numero, non
#    l'una dall'altra.
# ⚠️ Il giorno in cui l'export sapra' la lingua del richiedente, questa
#    funzione e' il posto da cui togliere la deroga — non ce ne sono altre.
_ETICHETTA_MULTI_REGISTRO = "Più sezionali ({n})"


# Scopo: scrive nel `registro_codice` delle righe multi-sezionale l'etichetta
#        che l'export mostrera'. Muta le righe in posto: sono gia' dizionari
#        appena costruiti dal repository, e copiarle per una sola chiave
#        sarebbe rumore.
# ⚠️ La condizione e' `registri_n > 1`, NON `registro_codice is None`: quel NULL
#        ha DUE significati (piu' sezionali, oppure nessuno risolvibile — il
#        caso `{NULL}`, che la vista conta comunque 1) e trattarli allo stesso
#        modo direbbe «sono piu' di uno» su un gruppo che di sezionali non ne ha
#        nemmeno uno.
def _marca_gruppi_multi_registro(results: list[DashCompetenzaGruppoRow]) -> None:
    for riga in results:
        if int(riga.get("registri_n") or 0) > 1 and riga.get("registro_codice") is None:
            riga["registro_codice"] = _ETICHETTA_MULTI_REGISTRO.format(
                n=riga["registri_n"],
            )


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
    # Filtro SEZIONALE (D-5): l'asse e' `registri_ids`, non il codice — un
    # gruppo che tocca due sezionali deve comparire sotto ENTRAMBE le voci.
    # `registro_non_risolvibile` e' la voce «sezionale non determinabile», cioe'
    # l'ASSENZA del valore: stessa forma del filtro cliente, e per lo stesso
    # motivo (un id sentinella in un campo che porta chiavi vere prima o poi
    # finisce confrontato con una PK).
    registro_id: int | None = None,
    registro_non_risolvibile: bool = False,
    search: str | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    # Export (BB `build_dash_export_response`): valorizzato = perimetro intero
    # in una volta, paginazione saltata. Assente = lista paginata di sempre.
    max_rows: int | None = None,
) -> dict[str, Any]:
    _validate_enum(
        stadio,
        allowed=DASH_COMPETENZA_STADI,
        param_name="stadio",
        function_name="vendite.vendite_service.fn_dash_competenza_gruppi",
    )
    _valida_ordinamento(
        order_by, order_dir,
        whitelist=VenditeRepository.DASH_COMPETENZA_GRUPPI_SORT_COLUMNS,
        function_name="vendite.vendite_service.fn_dash_competenza_gruppi",
    )
    # ⚠️ Ricerca sotto la soglia: si IGNORA, non si solleva e non si svuota la
    # lista. Il termine arriva mentre l'operatore sta ancora digitando — un 400
    # al secondo carattere sarebbe un errore per un'azione legittima, e una
    # lista vuota gli direbbe «non c'e' niente» quando la verita' e' «non ti ho
    # ancora cercato».
    # ⭐ Dal 2026-09-24 la soglia la applica SOLO il BB `add_ricerca_full_condition`
    #    nel repository (vale anche per l'export): qui il termine passa com'e'.
    #    Il gate che stava qui era una seconda sede dello stesso 3
    #    (`SEARCH_MIN_LEN`, ritirato col passaggio al BB).
    limit, offset = _paging_o_export(
        limit=limit, offset=offset, max_rows=max_rows,
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
        registro_id=registro_id,
        registro_non_risolvibile=registro_non_risolvibile,
        search=search,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    _marca_gruppi_multi_registro(results)
    payload = _envelope_pagina_effettiva(
        results, total_count, limit=limit, offset=offset,
    )
    # ⭐ EXPORT: si fermano qui. Riepilogo e facet servono all'INTERFACCIA — i
    #    totali sopra la lista e le tre tendine — e `build_dash_export_response`
    #    dall'envelope legge soltanto `results` e `count`. Calcolarli su una
    #    chiamata che scorre fino a 10.000 righe sono cinque aggregazioni
    #    buttate, sulla richiesta piu' pesante delle sei.
    # ⚠️ `max_rows` valorizzato = export: e' l'unico chiamante che lo passa
    #    (`build_dash_export_response`), ed e' anche l'unico che salta la
    #    paginazione. Se un giorno ne nascesse un secondo che vuole i totali,
    #    troverebbe le chiavi ASSENTI — un KeyError, non un numero sbagliato.
    if max_rows is not None:
        return payload
    # Due perimetri DIVERSI nella stessa risposta, ed e' voluto:
    #  - `riepilogo` SEGUE tutti i filtri (tipo, cliente, sezionale, ricerca):
    #    e' la riconciliazione della lista che l'utente sta guardando, e un
    #    totale che descrive un perimetro diverso dalle righe sopra di se' e'
    #    peggio di nessun totale;
    #  - le TRE facet e `n_gruppi_perimetro` NON li seguono: devono mostrare
    #    tutte le voci disponibili anche quando una e' selezionata, altrimenti
    #    scegliendo «Preventivi» le altre sparirebbero dalla tendina e non si
    #    potrebbe piu' cambiare idea senza azzerare il filtro alla cieca.
    #    ⚠️ Tutte sul perimetro BASE (competenza+stadio) e non una sull'altra:
    #    se `clienti` seguisse il tipo e `tipi` no, le due tendine
    #    racconterebbero perimetri diversi e il conteggio cambierebbe a seconda
    #    dell'ORDINE in cui l'operatore sceglie i filtri.
    #
    # ⭐ UNA SOLA LETTURA (2026-08-26). Erano cinque query, una per blocco, e
    #    ognuna rileggeva la vista da capo: ~1,46 s dei ~2,47 s dell'endpoint.
    #    I due perimetri ora convivono dentro la stessa query — vedi
    #    `get_dash_competenza_gruppi_accessori`, dove sono due CTE distinte.
    payload.update(
        repository.get_dash_competenza_gruppi_accessori(
            competenza_mese=competenza,
            stadio=stadio,
            tipo_gruppo=tipo_gruppo,
            ba_fatturazione_id=ba_fatturazione_id,
            ba_non_determinabile=ba_non_determinabile,
            registro_id=registro_id,
            registro_non_risolvibile=registro_non_risolvibile,
            search=search,
        )
    )
    # ℹ️ `n_gruppi_perimetro` arriva dallo stesso blocco: e' il conteggio del
    #    perimetro BASE, e serve alla voce «Tutti i sezionali» della tendina,
    #    che non puo' ricavarlo da nessun altro numero della risposta —
    #    sommare le voci della facet SOVRASTIMA (un gruppo su due sezionali e'
    #    contato sotto entrambi, ed e' giusto che lo sia), e `riepilogo` segue
    #    i filtri.
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
    aree: list[dict[str, Any]] = field(default_factory=list)


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
def fn_dash_backlog_riepilogo() -> dict[str, Any]:
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

    classi: list[dict[str, Any]] = []
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
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    # Export (BB `build_dash_export_response`): valorizzato = perimetro intero
    # in una volta, paginazione saltata. Assente = lista paginata di sempre.
    max_rows: int | None = None,
) -> dict[str, Any]:
    _validate_enum(
        area,
        allowed=DASH_FATTURAZIONE_AREE,
        param_name="area",
        function_name="vendite.vendite_service.fn_dash_backlog_documenti",
    )
    # Filtro "fermo da oltre N giorni": stessa regola del ritardo della
    # Situazione aperta, nella stessa sede.
    _valida_ritardo_giorni(
        ritardo_giorni,
        function_name="vendite.vendite_service.fn_dash_backlog_documenti",
    )
    # Ordinamento server-side (convenzione order_by/order_dir come le liste
    # standard): whitelist della lista + direzione asc/desc, fail-fast 400 —
    # nessun input grezzo entra nell'ORDER BY. Assenti -> default repository
    # (i piu' "fermo da" prima).
    _valida_ordinamento(
        order_by, order_dir,
        whitelist=VenditeRepository.DASH_BACKLOG_SORT_COLUMNS,
        function_name="vendite.vendite_service.fn_dash_backlog_documenti",
    )
    limit, offset = _paging_o_export(
        limit=limit, offset=offset, max_rows=max_rows,
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
    return _envelope_pagina_effettiva(
        results, total_count, limit=limit, offset=offset,
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
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    # Export (BB `build_dash_export_response`): valorizzato = perimetro intero
    # in una volta, paginazione saltata. Assente = lista paginata di sempre.
    max_rows: int | None = None,
) -> dict[str, Any]:
    # Ordinamento server-side (8° lotto liste, 2026-08-03): whitelist +
    # direzione validate qui, fail-fast 400 — stessa forma delle altre liste
    # dash. Assenti -> ordine storico (eventi recenti prima).
    _valida_ordinamento(
        order_by, order_dir,
        whitelist=VenditeRepository.DASH_COMPETENZA_ERRORI_SORT_COLUMNS,
        function_name="vendite.vendite_service.fn_dash_competenza_errori",
    )
    limit, offset = _paging_o_export(
        limit=limit, offset=offset, max_rows=max_rows,
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
    return _envelope_pagina_effettiva(
        results, total_count, limit=limit, offset=offset,
    )


# Tipi documento con endpoint /passaggi/ (nodo lineage con vista di dominio).
# COMMESSA aggiunta nella Fase C (genealogia inversa, design §7.3): non ha una
# lista/CRUD propria, ma il suo nodo lineage è consultabile via drawer leggero
# (sorgenti che l'hanno generata + fatture a valle).
#
# ⭐ FATTURA entra il 2026-08-21, e la decisione Q4 che la teneva fuori
# («capolinea, nessuna superficie propria») era vera quando è stata presa e non
# lo è più, per DUE ragioni indipendenti:
#   1. la superficie ora c'è — il drawer di consultazione della fattura esiste
#      dal 2026-07-29, ed è già la destinazione delle tappe FATTURA negli altri
#      pannelli: mancava solo il pannello sul documento stesso;
#   2. il capolinea non è più tale — l'arco N (fattura rettificata → nota di
#      credito, changeSet 20260821-02) le dà un discendente.
# ⚠️ Resta vero che la fattura non ha discendenti nel grafo FORWARD: l'arco N è
# un ramo di ritorno. Il valore del pannello qui è quindi la direzione INDIETRO
# — «da dove viene questo documento» — non la frontiera, che per una fattura
# indica sempre sé stessa. Misurato sulla fattura 835: 7 archi indietro (tre
# commesse, tre ordini, un preventivo), 1 avanti (la nota di credito).
LINEAGE_TIPI_DOCUMENTO: tuple[str, ...] = (
    SORGENTE_PREVENTIVO,
    SORGENTE_OFFERTA_COMMERCIALE,
    SORGENTE_ORDINE_VENDITA,
    SORGENTE_CONTRATTO,
    SORGENTE_DDT_VENDITA,
    SORGENTE_RESO_VENDITA,
    SORGENTE_COMMESSA,
    SORGENTE_FATTURA,
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
) -> dict[str, Any]:
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
    sorgente = SorgentiRepository().get_sorgente_attiva(tipo_codice)
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
    pratica: dict[str, Any] | None = None
    if nodo["pratica_id"] is not None:
        pratica = {
            "pratica_id": nodo["pratica_id"],
            "pratica_numero": nodo["pratica_numero"],
            "n_pratiche": nodo["n_pratiche"],
        }

    # Frontiera normalizzata: la summary, per costruzione, per un nodo senza
    # discendenti indica il nodo stesso -> per il FE e' "non transitato" (None).
    frontiera: dict[str, Any] | None = None
    is_self = (
        nodo["frontiera_tipo_id"] == nodo["tipo_id"]
        and nodo["frontiera_uid"] == nodo["uid"]
    )
    if nodo["is_transitato"] and nodo["frontiera_tipo_id"] is not None and not is_self:
        frontiera = {
            "tipo_codice_interno": nodo["frontiera_tipo_codice_interno"],
            # ⚠️ La frontiera puo' essere una nota di credito (arco G dalla
            # commessa): senza la natura il FE la etichetterebbe «Fattura».
            # E' l'invariante che il pgTAP del DB ha corretto (§44.5): «una NC
            # non e' mai frontiera di un altro nodo» e' FALSO.
            "natura_doc_codice_interno": nodo["frontiera_natura_doc_codice_interno"],
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
            "tipo_codice_interno": nodo["tipo_codice_interno"],
            "codice": nodo["codice"],
            "stato_codice_interno": nodo["stato_codice_interno"],
            "stato_descrizione": nodo["stato_descrizione"],
            "fase": nodo["fase"],
            "is_abortito": nodo["is_abortito"],
            "is_transitato": nodo["is_transitato"],
            "n_discendenti_diretti": nodo["n_discendenti_diretti"],
            "n_discendenti_attivi": nodo["n_discendenti_attivi"],
            "n_sorgenti": nodo["n_sorgenti"],
            # La natura distingue la nota di credito dalla fattura: sono lo
            # stesso tipo documento e, senza, il pannello scrive due volte
            # «Fattura · EMESSA» per due documenti diversi.
            "natura_doc_codice_interno": nodo["natura_doc_codice_interno"],
            # ⭐ Il codice della radice: per una fattura e' l'informazione che
            # conta davvero, perche' la frontiera indica sempre se stessa (nodo
            # terminale del grafo forward). Dice «da dove viene».
            "root_codice": nodo["root_codice"],
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
_FN_FATTURA_GIORNALE = "vendite.vendite_service.get_fattura_giornale"
_FN_FATTURA_RIGHE = "vendite.vendite_service.list_fattura_righe_pagina"


# Scopo: IL CANCELLO di ogni lettura di una fattura: id valido, poi la testata
#        letta con lo scope applicativo (`auth_user_id`, sommato alla RLS).
#        Ritorna la testata; inesistente e fuori scope danno la STESSA
#        risposta, un 404: distinguerli confermerebbe l'esistenza di una
#        fattura di un altro emittente (api.md §Scope emittente).
# ⭐ Regola del 2 (2026-09-28, lotto C del brief-db-liste-righe-documento):
#    dettaglio e giornale lo scrivevano ciascuno per intero, e la lista delle
#    righe sarebbe stata la terza copia.
# ⛔ I satelliti (righe, giornale, rettifiche) si leggono DOPO: `vendite.
#    fatture` ha la RLS, alcuni satelliti no.
def _testata_fattura_o_404(
    repository: VenditeRepository,
    fattura_id: int,
    *,
    auth_user_id: int | None,
    function_name: str,
) -> dict[str, Any]:
    ErrorManager.require(
        bool(fattura_id and fattura_id > 0),
        code="E_VENDITE_VALIDATION",
        message="Parametri non validi.",
        detail="fattura_id obbligatorio e > 0",
        context={"fattura_id": fattura_id},
        function_name=function_name,
        log_to_db=True,
    )
    testata = repository.get_fattura_testata(fattura_id, auth_user_id=auth_user_id)
    if testata is None:
        ErrorManager.raise_error(
            code="E_FATTURA_NON_TROVATA",
            message="Fattura non trovata.",
            detail=f"Nessuna fattura accessibile con id={fattura_id}",
            context={"fattura_id": fattura_id},
            function_name=function_name,
            log_to_db=True,
        )
    assert testata is not None
    return testata


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
#    e `fatture_riepiloghi_iva` hanno le proprie policy. Verificato: 8 righe
#    reali, **0** visibili senza GUC — prima erano 8 su 8.
#    Forma delle policy dal 2026-10-21 (perimetro una volta per istruzione,
#    risolutore per riga, sempre sulla fattura della riga):
#      - operatore `FOR ALL`: `script.fn_scope_ef_perimetro` sull'emittente
#        della fattura (`script.fn_resolve_emittente_fiscale_id`, modo `fattura`);
#      - portale `FOR SELECT`: `script.fn_scope_sr_perimetro` sul cliente della
#        fattura (`script.fn_resolve_controparte_sr_id`, modo `fattura`). Il
#        perimetro pretende l'identita' nella veste del gate: un contesto GUC
#        incoerente da' zero righe, cioe' 404 qui sotto.
#    Gli adattatori `fn_scope_*_via_fattura` non stanno piu' nelle policy
#    (`fn_scope_ba_ownership_via_fattura` ritirata con 20261021-40).
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
) -> dict[str, Any]:
    repository = VenditeRepository()

    # 1. IL CANCELLO (`_testata_fattura_o_404`).
    testata = _testata_fattura_o_404(
        repository, fattura_id,
        auth_user_id=auth_user_id, function_name=_FN_FATTURA_DETTAGLIO,
    )

    # 2. Solo ORA i satelliti: la testata ha gia' autorizzato l'accesso.
    #    Il conteggio note passa dal service del BB note (`count_per_target`,
    #    nato "per badge UI" e finora senza consumer): stessa porta della lista
    #    note esposta dall'API, quindi un domani i due perimetri non possono
    #    divergere. Oggi non filtra su `visibile`, esattamente come la lista
    #    (`include_invisible=True` di default) — il badge non "salta" quando il
    #    sub-drawer note si aggiorna da solo.
    return {
        "fattura": dict(testata),
        # ⭐ Le righe dalla STESSA vista della lista a video
        #    (`vw_fattura_righe_lista`, lettura completa): primo livello, e i
        #    componenti esposti di un kit dentro il padre (`componenti`). Una
        #    sede sola per «quali righe ha questa fattura» (lotto C, 2026-09-28).
        #    Oggi le legge il drawer delle note, per il selettore di riga.
        "righe": FattureRepository().list_righe(fattura_id),
        "riepilogo_iva": repository.list_fattura_riepilogo_iva(fattura_id),
        "scadenze": repository.list_fattura_scadenze(fattura_id),
        # Legame documentale della nota di credito, nei due versi (B7). ⚠️ Sta
        # QUI, dopo il cancello: `vendite.fatture` ha la RLS,
        # `fatture_rettifiche` no — leggerlo prima esporrebbe il numero di un
        # documento fuori perimetro.
        "rettifiche": repository.get_fattura_rettifiche(fattura_id),
        # ⭐ LE ORIGINI: i documenti a monte che la fattura cita, dal lettore
        #    del DB (`vendite.fn_fattura_origini`, BE-1 di brief-modello-
        #    documento-vendita §15.11.1), nell'ordine in cui arrivano. Lo
        #    STESSO lettore della stampa: video e carta citano gli stessi
        #    documenti. Dopo il cancello: la funzione e' INVOKER.
        "origini": repository.list_fattura_origini(fattura_id),
        # ⭐ L'ERRORE VIVO del documento — la riga ERROR piu' recente e non
        #    ritirata del suo giornale, o `None` — per il banner in testa al
        #    drawer. Sta nel DETTAGLIO e non nella Storia (2026-09-27): da
        #    quando la Storia e' la lista a catalogo `vendite.giornale`, la sua
        #    pagina e' ordinata dal preset o dall'operatore, e il banner che
        #    prendeva «il primo ERROR della pagina» avrebbe taciuto appena
        #    l'errore fosse scivolato fuori. ⛔ Non e' una capability (non dice
        #    cosa si PUO' fare, dice com'e' il documento): per questo non sta
        #    sotto `capabilities` (api.md §Capability) ma accanto agli altri
        #    satelliti, dopo il cancello della testata.
        "errore_vivo": repository.get_giornale_errore_vivo(
            entity_type="FATTURA", entity_id=fattura_id,
        ),
        "contatori": contatori_documento(NOTE_REPO_FATTURA, fattura_id),
    }


# =====================================================================
# Fondi fattura — elenco dei casi che chiedono una persona (BE-3)
# =====================================================================

_FN_FONDI_DA_DECIDERE = "vendite.vendite_service.fn_fondi_fattura_da_decidere"


# Scopo: i controlli COMUNI ai tre lettori del giornale — paginazione e
#        ordinamento — prima di toccare il database.
# ⭐ ESTRATTO il 2026-09-27 (regola del 2): da quel giorno i tre lettori sono la
#    STESSA lista a catalogo (`vendite.giornale`, brief-db-liste-datatable-
#    grezze §3.1) con lo stesso contratto `limit`/`offset`/`order_by`/
#    `order_dir`, e tre copie degli stessi due controlli divergono al primo
#    ritocco — la Storia di un documento che accetta un ordinamento che il
#    trasversale rifiuta, sulla stessa colonna della stessa lista.
# ⛔ Un `order_by` fuori whitelist e' un 400: `_giornale_order_clause`
#    ripiegherebbe sul default senza dirlo — una lista ordinata diversamente da
#    come e' stata chiesta non solleva niente.
def _valida_lettura_giornale(
    *,
    limit: int,
    offset: int,
    order_by: str | None,
    order_dir: str | None,
    function_name: str,
) -> None:
    ErrorManager.require(
        int(limit) > 0 and int(offset) >= 0,
        code="E_VENDITE_VALIDATION",
        message="Parametri di paginazione non validi.",
        detail=f"limit={limit}, offset={offset}",
        function_name=function_name,
    )
    _valida_ordinamento(order_by, order_dir, whitelist=GIORNALE_SORT_COLUMNS, function_name=function_name)


# Scopo: l'envelope paginato standard dei tre lettori del giornale, piu' il
#        conteggio delle segnalazioni RITIRATE che il filtro sta nascondendo.
# ⚠️ `ritirate_nascoste` e' gia' deciso dal chiamante (zero quando le ritirate
#    sono incluse: li' non c'e' niente di nascosto da dichiarare). E il totale e'
#    quello che l'elenco MOSTRA, non quello che esiste: e' su di lui che pagina
#    il client — mai sotto zero, perche' sul lotto e' una sottrazione e un
#    `count` negativo romperebbe il paginatore senza nessun errore.
def _envelope_giornale(
    righe: list[dict[str, Any]],
    *,
    total_count: int,
    limit: int,
    offset: int,
    ritirate_nascoste: int,
) -> dict[str, Any]:
    envelope = envelope_da_offset(
        righe, max(0, int(total_count)), limit=int(limit), offset=int(offset),
    )
    envelope["ritirate_count"] = ritirate_nascoste
    return envelope


# Scopo: UNA PAGINA delle righe di una fattura, per la lista configurabile
#        `vendite.fattura_righe` (brief-db-liste-righe-documento, lotto C).
#        «Leggi prima la testata» (BB core `pagina_dopo_testata`): fuori
#        scope e' un 404, non una lista vuota (la vista e' `security_invoker`
#        e risponderebbe zero righe). `auth_user_id` e' dello scope della
#        testata; il resto e' il contratto della lista.
def list_fattura_righe_pagina(
    fattura_id: int,
    *,
    auth_user_id: int | None = None,
    **opzioni: Any,
) -> tuple[list[dict[str, Any]], int]:
    return pagina_dopo_testata(
        lambda: _testata_fattura_o_404(
            VenditeRepository(), fattura_id,
            auth_user_id=auth_user_id, function_name=_FN_FATTURA_RIGHE,
        ),
        FattureRepository().list_righe_pagina, fattura_id, **opzioni,
    )


# Scopo: IL GIORNALE DI UNA FATTURA — «cosa e' successo a questo documento, in
#        ordine di tempo». Sola lettura, elenco paginato dalla vista cucita
#        `script.vw_giornale_entita` (Passo A del filone osservabilita').
#
# ⭐ PRIMO CONSUMATORE DELLA VISTA, e quindi anche il suo collaudo: fino al
#    2026-08-24 non l'aveva interrogata nessuno, e il suo perimetro era
#    verificato dal pgTAP e non dall'uso.
# ⭐ Dal 2026-09-27 e' la lista a catalogo `vendite.giornale` (la stessa del
#    trasversale, decisione di Tid) filtrata sulla fattura: contratto di lista
#    standard (`limit`/`offset`/`order_by`/`order_dir`), ordine di partenza del
#    preset (`quando desc`). Il banner d'errore del drawer non legge piu' da
#    qui: ha la sua fonte nel dettaglio (`errore_vivo`).
#
# 🔴 IL CANCELLO E' LA TESTATA, e non e' una precauzione ridondante. La vista e'
#    `security_invoker`, quindi su una fattura fuori scope la RLS la farebbe
#    rispondere ZERO RIGHE — cioe' «a questo documento non e' successo niente»
#    invece di «questo documento non lo vedi». Sono due frasi diverse e non
#    devono leggersi uguali: stesso ordine di lettura di `get_fattura_dettaglio`
#    e degli altri pannelli satellite della fattura.
#
# ⛔ NIENTE AGGREGATI, nessuna finestra temporale, nessun conteggio per periodo:
#    quelli sono il Passo B e hanno prerequisiti loro. Qui si risponde a una
#    domanda sola.
def get_fattura_giornale(
    *,
    fattura_id: int,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    order_by: str | None = None,
    order_dir: str | None = None,
    includi_ritirate: bool = False,
    auth_user_id: int | None = None,
) -> dict[str, Any]:
    _valida_lettura_giornale(
        limit=limit, offset=offset, order_by=order_by, order_dir=order_dir,
        function_name=_FN_FATTURA_GIORNALE,
    )
    repository = VenditeRepository()

    # 1. IL CANCELLO (`_testata_fattura_o_404`).
    _testata_fattura_o_404(
        repository, fattura_id,
        auth_user_id=auth_user_id, function_name=_FN_FATTURA_GIORNALE,
    )

    # 2. Solo ORA il giornale: la testata ha gia' autorizzato l'accesso.
    # ⭐ LE RITIRATE SI NASCONDONO (decisione di Tid, 2026-08-24): una
    #    segnalazione ritirata e' quella di un tentativo poi rifatto, e sul caso
    #    misurato e' LETTERALMENTE la stessa frase di quella viva — mostrarle
    #    entrambe fa credere che sia successo due volte.
    # ⛔ Il filtro sta QUI e non nel client: la lista e' paginata lato server, e
    #    filtrare a valle filtrerebbe solo la pagina visibile.
    # ⚠️ `ritirate_count` non e' un accessorio: senza, «nessun evento» e «tre
    #    eventi, tutti superati» si leggono uguali — ed e' proprio il caso in cui
    #    la differenza conta.
    # ⚠️ Il quarto valore (`info_vive`) qui non si usa: sul documento singolo il
    #    pannello mostra TUTTE le gravita', quindi non c'e' nessuna INFO
    #    nascosta da dichiarare. Il corpo e' condiviso col giornale del lotto,
    #    dove invece le INFO si filtrano.
    righe, vive, ritirate, _info_vive = repository.list_giornale_entita(
        entity_type="FATTURA",
        entity_id=fattura_id,
        limit=limit,
        offset=offset,
        escludi_ritirate=not includi_ritirate,
        sort_by=order_by,
        sort_dir=order_dir,
    )
    envelope = _envelope_giornale(
        righe,
        total_count=vive + ritirate if includi_ritirate else vive,
        limit=limit,
        offset=offset,
        ritirate_nascoste=0 if includi_ritirate else ritirate,
    )
    envelope["fattura_id"] = fattura_id
    return envelope


_FN_LOTTO_GIORNALE = "vendite.vendite_service.get_lotto_giornale"


# Scopo: LA STORIA DI UN LOTTO — il lotto piu' le sue fatture, di default senza
#        le righe INFO. Secondo consumatore di `script.vw_giornale_entita`, e
#        dal 2026-09-27 la stessa lista a catalogo (`vendite.giornale`) della
#        Storia della fattura e del trasversale.
#
# ⭐ «Che cos'e' un caso» e' una decisione di Tid del 2026-08-24, e non era una
#    scelta di schermata: un pannello limitato all'entita' LOTTO sarebbe onesto
#    e nel giorno in cui serve **non conterrebbe la risposta**. Misurato sul
#    6260: il lotto ripete «Esito fatture lotto · WARN», il motivo sta sulla
#    FATTURA perche' la sua entita' e' la fattura (rilievo R-3).
#
# ⛔ Il pannello si e' potuto scrivere solo dal 2026-08-24 19:33, quando il team
#    DB ha applicato R-1: qui i registri sono TRE, e con l'orario di transazione
#    le righe di una stessa transazione uscivano tutte con lo stesso istante —
#    una timeline che mostra una sequenza mai avvenuta e non sembra rotta.
#
# ⚠️ Le INFO si nascondono ma si CONTANO: un elenco filtrato e un elenco completo
#    si leggono uguali. Stessa regola gia' applicata alle ritirate. Il filtro
#    «solo problemi» e' del LOTTO e solo suo: sul documento singolo le righe
#    sono poche e si mostrano tutte.
def get_lotto_giornale(
    *,
    lotto_id: int,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    order_by: str | None = None,
    order_dir: str | None = None,
    includi_info: bool = False,
    includi_ritirate: bool = False,
    auth_user_id: int | None = None,
) -> dict[str, Any]:
    ErrorManager.require(
        bool(lotto_id and lotto_id > 0),
        code="E_VENDITE_VALIDATION",
        message="Parametri non validi.",
        detail="lotto_id obbligatorio e > 0",
        context={"lotto_id": lotto_id},
        function_name=_FN_LOTTO_GIORNALE,
        log_to_db=True,
    )
    _valida_lettura_giornale(
        limit=limit, offset=offset, order_by=order_by, order_dir=order_dir,
        function_name=_FN_LOTTO_GIORNALE,
    )
    repository = VenditeRepository()

    # 1. IL CANCELLO. ⛔ Non e' ridondante con la RLS: la vista del giornale non
    #    ha un perimetro emittente proprio per le righe di entita' FATTURA, e
    #    senza questo passaggio un id fuori scope riceverebbe «zero righe» —
    #    che si legge come «lotto senza storia», non come «non lo puoi vedere».
    #    Inesistente e fuori scope danno la STESSA risposta, per non confermare
    #    l'esistenza del lotto di un altro emittente.
    lotto_visibile(
        lotto_id=lotto_id, auth_user_id=auth_user_id,
        function_name=_FN_LOTTO_GIORNALE, repository=repository,
    )

    # 2. Solo ORA il giornale: il lotto e' gia' stato autorizzato.
    righe, vive, ritirate, info_vive = repository.list_giornale_lotto(
        lotto_id=lotto_id,
        limit=limit,
        offset=offset,
        escludi_ritirate=not includi_ritirate,
        escludi_info=not includi_info,
        sort_by=order_by,
        sort_dir=order_dir,
    )

    # ⚠️ Il totale e' quello che l'elenco MOSTRA, non quello che esiste: e' su
    #    di lui che pagina il client. I due numeri nascosti viaggiano a parte.
    total_count = vive
    if includi_ritirate:
        total_count += ritirate
    if not includi_info:
        total_count -= info_vive
    envelope = _envelope_giornale(
        righe,
        total_count=total_count,
        limit=limit,
        offset=offset,
        ritirate_nascoste=0 if includi_ritirate else ritirate,
    )
    envelope["lotto_id"] = lotto_id
    # ⭐ Quante righe di routine il filtro tiene fuori. Senza, «un lotto con
    #    tre problemi» e «un lotto con tre problemi e 173 passi andati bene»
    #    si leggono identici.
    envelope["info_count"] = 0 if includi_info else info_vive
    return envelope


_FN_GIORNALE = "vendite.vendite_service.get_giornale_trasversale"


# Scopo: il GIORNALE TRASVERSALE — la Storia di tutte le entita' insieme,
#        filtrata per gravita' (pezzo G dell'osservabilita', 2026-09-19):
#        valida i vocabolari, delega al terzo lettore della vista e compone
#        l'envelope paginato standard piu' `ritirate_count`.
# ⛔ NESSUN cancello di testata: qui non c'e' UNA entita' da autorizzare prima
#    di leggere — il perimetro lo applica la vista (`security_invoker`) riga
#    per riga e nei conteggi, e la lista sta dietro il cancello di perimetro
#    emittente della view (`lista_codice = "vendite.giornale"`). Fuori scope la
#    riga non c'e', e `count` dice il numero VISTO.
# ⚠️ `gravita`/`registro` fuori vocabolario -> 400: e' un contratto dichiarato,
#    e un valore ignoto che rispondesse «zero righe» sarebbe un errore educato
#    che nessuno vede. Il vocabolario di `registro` e' `config.registri_giornale`
#    (tutte le righe, ritirate comprese: le righe vecchie si leggono).
def get_giornale_trasversale(
    *,
    gravita: list[str] | None = None,
    registri: list[str] | None = None,
    entity_type: str | None = None,
    data_da: date | None = None,
    data_a: date | None = None,
    filo: str | None = None,
    solo_vive: bool = True,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    order_by: str | None = None,
    order_dir: str | None = None,
) -> dict[str, Any]:
    gravita_richiesta = [g.upper() for g in (gravita or []) if g] or ["ERROR"]
    ErrorManager.require(
        all(g in GIORNALE_GRAVITA for g in gravita_richiesta),
        code="E_VENDITE_VALIDATION",
        message="Parametro gravita non valido.",
        detail=f"gravita={gravita_richiesta}, ammessi={list(GIORNALE_GRAVITA)}",
        context={"parametro": "gravita"},
        function_name=_FN_GIORNALE,
    )
    registri_richiesti = [r.upper() for r in (registri or []) if r] or None
    repository = VenditeRepository()
    # ⭐ Il vocabolario dei registri e' `config.registri_giornale`, letto dal
    #    catalogo — non una costante: la sede e' una (brief-db-registri-
    #    giornale-catalogo). Si legge solo quando il filtro c'e'.
    if registri_richiesti is not None:
        registri_ammessi = repository.registri_giornale_ammessi()
        ErrorManager.require(
            all(r in registri_ammessi for r in registri_richiesti),
            code="E_VENDITE_VALIDATION",
            message="Parametro registro non valido.",
            detail=f"registro={registri_richiesti}, ammessi={sorted(registri_ammessi)}",
            context={"parametro": "registro"},
            function_name=_FN_GIORNALE,
        )
    _valida_lettura_giornale(
        limit=limit, offset=offset, order_by=order_by, order_dir=order_dir,
        function_name=_FN_GIORNALE,
    )
    # ⛔ Il tipo di entita' nel suo vocabolario, o un 400 sul campo: fino al
    #    2026-10-20 un codice ignoto rispondeva zero righe, cioe' «niente di
    #    andato storto». Tipi ritirati (`obsoleto_dal`) ammessi: il diario li porta.
    tipo_entita = richiedi_codice_a_vocabolario(
        "config.tipi_entita", "codice", entity_type.upper() if entity_type else None,
        codice_errore="E_VENDITE_VALIDATION", parametro="entity_type",
    )
    righe, vive, ritirate, _info_vive = repository.list_giornale_trasversale(
        gravita=gravita_richiesta,
        registri=registri_richiesti,
        entity_type=tipo_entita,
        data_da=data_da,
        data_a=data_a,
        filo=filo,
        solo_vive=solo_vive,
        limit=limit,
        offset=offset,
        # ⭐ Il default (assente = `None`) lo decide il repository: il TEMPO,
        #    dal piu' recente (`GIORNALE_ORDINE_DEFAULT`), come le due Storie.
        sort_by=order_by,
        sort_dir=order_dir,
    )
    # ⚠️ Il totale e' quello che l'elenco MOSTRA: le vive, piu' le ritirate se
    #    le si e' chieste. `info_vive` qui non entra: le INFO non sono mai
    #    nascoste da un filtro implicito (o si chiedono con `gravita`, o no).
    return _envelope_giornale(
        righe,
        total_count=vive + (0 if solo_vive else ritirate),
        limit=limit,
        offset=offset,
        ritirate_nascoste=ritirate if solo_vive else 0,
    )


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
    # ⛔ `limit`/`offset` come ogni lista (decisione Tid 2026-10-20,
    #    brief-be-verifica-documentazione-api §A4): fino a quel giorno questa
    #    paginava con `page`/`page_size`. Il clamp lo fa `parse_list_params`.
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    # Export: valorizzato = perimetro intero in una volta, paginazione saltata
    # (BB `_paging_o_export`). Assente = la lista paginata di sempre.
    max_rows: int | None = None,
) -> dict[str, Any]:
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
        order_dir or "desc",
        allowed_columns=frozenset(VenditeRepository.FONDI_DA_DECIDERE_SORT_COLUMNS),
        error_code="E_VENDITE_VALIDATION",
        function_name=_FN_FONDI_DA_DECIDERE,
    )
    if max_rows is not None:
        limit, offset = _paging_o_export(
            limit=limit, offset=offset, max_rows=max_rows,
            function_name=_FN_FONDI_DA_DECIDERE,
        )

    repository = VenditeRepository()
    results: list[FondoFatturaDaDecidereRow]
    results, total_count = repository.list_fondi_fattura_da_decidere(
        motivo=motivo,
        auth_user_id=auth_user_id,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    return _envelope_pagina_effettiva(results, total_count, limit=limit, offset=offset)


_FN_CANCELLA_FONDO = "vendite.vendite_service.fn_cancella_fondo_fattura"


# Scopo: Cancella un atto di fondo fattura che non e' ancora diventato un fatto
#        — oppure lascia che il database dica perche' non si puo'.
#        BE-4 di brief-db-fondo-fattura-ricalcolo-e-governo §9.3, su D-21.
# Contesto: il gesto serve alla popolazione `NON_PIU_CAPIENTE` dell'elenco «da
#        decidere» — l'atto AUTOMATICA che il giro non riesce piu' ad applicare
#        e che nessuna sistemazione trattiene. ⛔ Il riporto sbagliato NON passa
#        di qui: si disfa annullando la sistemazione che lo ha creato
#        (`POST /pagamenti/sistemazioni/{id}/annulla/`), e se qualcuno ci prova
#        lo dice il database con `E_FONDO_TRATTENUTO_DA_SISTEMAZIONE`.
# Perimetro: si CANCELLA e non si annulla — un atto che non e' mai diventato un
#        fatto non lascia una riga di registro, lascia il posto vuoto che aveva
#        prima (G-1, Tid 2026-08-29). La scelta e' gia' quella del reset dal
#        changeSet 20260821-54.
# Risultato: dict con i tre contatori della madre.
#
# ⭐ `translate_db_errors` e non un elenco locale di codici ammessi, per la
#    stessa ragione gia' scritta su `fn_riporta_attivita_da_emettere`: il
#    predicato ha SEI motivi e ne aveva quattro nel piano — due sono nati
#    scrivendo il changeSet. Una copia del catalogo in Python si sarebbe
#    disallineata in silenzio proprio su quei due. Cosi' invece il codice arriva
#    all'operatore com'e', con la sua `soluzione`, il suo BERSAGLIO (la fattura,
#    sorgente o figlia secondo il motivo) e la `cause` nel contesto — che e' cio'
#    che distingue i tre motivi che parlano di denaro fra loro.
def fn_cancella_fondo_fattura(*, fondo_source_id: int) -> dict[str, Any]:
    # ⚠️ `not isinstance(..., bool)` non e' pedanteria: in Python `bool` e'
    #    SOTTOCLASSE di `int`, quindi `isinstance(True, int)` e' vero e
    #    `True > 0` pure — un `True` arrivato per sbaglio sarebbe passato al
    #    database come booleano, e il rifiuto sarebbe un errore di tipo invece
    #    che il messaggio giusto.
    ErrorManager.require(
        isinstance(fondo_source_id, int)
        and not isinstance(fondo_source_id, bool)
        and fondo_source_id > 0,
        code="E_VENDITE_VALIDATION",
        message="Identificativo del fondo non valido.",
        detail=f"fondo_source_id ricevuto: {fondo_source_id!r}",
        function_name=_FN_CANCELLA_FONDO,
    )
    repository = VenditeRepository()
    with translate_db_errors(
        context={"op": _FN_CANCELLA_FONDO, "fondo_source_id": fondo_source_id},
        fallback_code="E_VENDITE_VALIDATION",
        fallback_message="Cancellazione del fondo fattura non riuscita.",
    ):
        conteggi = repository.cancella_fondo_fattura(fondo_source_id)
    return {"status": "deleted", "fondo_source_id": fondo_source_id, **conteggi}


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
) -> dict[str, Any]:
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

    # Livello 1 — il riassunto per riga d'ordine. C'e' su ENTRAMBI i lati
    # (rev 2026-08-19, rilievo in-app di Tid): dal DDT sono le righe d'ordine
    # che QUELLA spedizione ha toccato, e servono a leggere i due livelli
    # insieme — «la riga d'ordine nel complesso sta cosi', questa spedizione
    # cosi'». Prima erano assenti sul DDT e le due schermate raccontavano due
    # storie diverse dello stesso fatto.
    # ⚠️ Una riga di DDT senza origine ordine (`origine <> 'ORDINE_VENDITA'`) non ha
    # riga d'ordine: la sezione resta piu' corta delle partite, ed e' corretto.
    # Lista vuota e non `None`: il frontend itera sempre.
    righe_ordine = repository.list_situazione_merce_ordine(
        ordine_id=ordine_id, ddt_id=ddt_id
    )

    return {
        # ⭐ Il CONTESTO e' dato, non deduzione. Con `righe_ordine` popolata su
        # entrambi i lati, «quale delle due liste e' il saldo del documento» non
        # si puo' piu' leggere dal fatto che una sia vuota — e sbagliarlo
        # significa contare, sul DDT, il saldo dell'INTERA riga d'ordine
        # (tutte le sue spedizioni) al posto di questa. Il consumatore riceve la
        # risposta, non l'indovinello.
        # Il valore e' il codice di `config.sorgenti` del documento (dal
        # 2026-10-19, brief-db-grammatica-unica-documenti lotto 2a).
        "contesto": (
            SORGENTE_ORDINE_VENDITA if ordine_id is not None else SORGENTE_DDT_VENDITA
        ),
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


# Scopo: LA LISTA FATTURE — la settima del ciclo attivo, sullo stampo delle sei
#        sorelle. Facade sottile sul repository: la sorgente è la vista
#        canonica `vendite.vw_fatture_lista`, e la validazione dei parametri di
#        lista la fa `parse_list_params` alla porta.
#
# ⚠️ Sola lettura, e non è una svista: la fattura si produce dalla pipeline di
#    fatturazione, non da un form. Qui non esiste nessun verbo di scrittura.
def list_fatture_rows(
    *,
    stato_codice: str | None = None,
    billing_account_id: int | None = None,
    id_fiscale: str | None = None,
    utility_id: int | None = None,
    natura_doc_codice: str | None = None,
    data_da: date | None = None,
    data_al: date | None = None,
    search: str | None = None,
    auth_user_id: int | None = None,
    limit: int,
    offset: int,
    order_by: str = "data",
    order_dir: str = "desc",
    max_limit: int = MAX_LIMIT,
) -> tuple[list[dict[str, Any]], int]:
    # ⛔ Il filtro di stato esiste nel vocabolario, o e' un 400 sul campo: un
    #    valore sbagliato finiva nel WHERE e la lista rispondeva vuota con un
    #    200 (2026-10-20). Codici dismessi ammessi: i documenti vecchi li portano.
    richiedi_codice_a_vocabolario(
        "config.stati_doc_fiscale", "codice_interno", stato_codice,
        codice_errore="E_VENDITE_VALIDATION", parametro="stato_codice_interno",
    )
    richiedi_codice_a_vocabolario(
        "config.nature_doc_fiscale", "codice_interno", natura_doc_codice,
        codice_errore="E_VENDITE_VALIDATION", parametro="natura_doc_codice",
    )
    return FattureRepository().list_fatture(
        stato_codice=stato_codice,
        billing_account_id=billing_account_id,
        id_fiscale=id_fiscale,
        utility_id=utility_id,
        natura_doc_codice=natura_doc_codice,
        data_da=data_da,
        data_al=data_al,
        search=search,
        auth_user_id=auth_user_id,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_dir=order_dir,
        max_limit=max_limit,
    )
