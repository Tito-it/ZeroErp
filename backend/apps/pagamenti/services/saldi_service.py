# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La BASE DEI SALDI — l'unico posto del backend che legge le funzioni di
#        saldo del database e le espone in una forma sola.
# Note: 🔴 Non e' «il pannello saldo della fattura»: e' la base, e la fattura ne
#       e' il primo consumatore. Decisione di Tid del 2026-08-24: *«il drawer
#       fattura non e' l'unico posto dove vedere queste informazioni; dovra'
#       nascere una funzione che dia anche il saldo del cliente, quindi
#       qualsiasi cosa faremo deve essere una base unica per i saldi»*.
#
#       ⛔ Nessun altro modulo interroga `fn_get_saldo_*` per conto suo. Un
#       saldo calcolato in due posti diverge alla prima regola nuova, e sono
#       numeri su cui qualcuno decide se sollecitare un cliente.
#
#       ⭐ I LIVELLI SONO TRE fin dall'inizio — documento, rata, cliente — anche
#       se il terzo si accende dopo: la forma nasce capace di reggerlo, non si
#       riapre per aggiungerlo.
# ------------------------------------------------------------

from datetime import date
from decimal import Decimal
from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import validate_order_params
from apps.pagamenti.db.pagamenti_repository import (
    RATE_SORT_COLUMNS,
    PagamentiRepository,
)
from apps.pagamenti.services._helpers import (
    E_FATTURA_NON_TROVATA,
    E_RATA_NON_TROVATA,
    E_VALIDAZIONE,
)
from apps.pagamenti.types import SaldoRow

_FN = "pagamenti.saldi_service"

# `E_RATA_NON_TROVATA` e `E_FATTURA_NON_TROVATA` vengono da `_helpers`, la sede
# condivisa coi service che li sollevano allo stesso modo (dal 2026-09-17 la
# rata la solleva anche «righe da rate»). Restano importati qui perche' i test
# e i chiamanti li leggono da questo modulo.

# ⭐ IL VOCABOLARIO, e vale a ogni livello. Una schermata sceglie QUALI numeri
#    accendere; ⛔ nessuna li rinomina e nessuna li ricalcola.
#
#   residuo        quanto manca ancora da regolare. E' la domanda che uno si fa.
#   in_lavorazione denaro gia' digitato su una distinta e NON ancora registrato:
#                  non abbassa il residuo, e vederlo spiega perche'.
#   incassato      di quanto e' stato registrato, quanto e' entrato DAVVERO in
#                  banca — i centri interni (fondi, compensazioni) sono esclusi.
#                  ⚠️ `None` dove il database non lo sa ancora dire.
CAMPI_SALDO: tuple[str, ...] = ("residuo", "in_lavorazione", "incassato")


# Scopo: Compone la forma unica a partire dai numeri che il livello sa dare.
def _saldo(
    *,
    residuo: Decimal | None,
    in_lavorazione: Decimal | None,
    incassato: Decimal | None,
    has_movimenti: bool,
    livello: str,
    riferimento_id: int,
) -> SaldoRow:
    return {  # type: ignore[return-value]
        "livello": livello,
        "riferimento_id": riferimento_id,
        "residuo": residuo,
        "in_lavorazione": in_lavorazione,
        "incassato": incassato,
        "has_movimenti": has_movimenti,
    }


# ══════════════════════════════════════════════════════════════════
#  Livello DOCUMENTO
# ══════════════════════════════════════════════════════════════════

# Scopo: Il saldo di una fattura.
# ⭐ Dal 2026-08-29 risponde TUTTI E TRE i numeri. Fino a ieri `incassato` era
#    `None` con la nota «il database ne risponde due»: la nota era vera quando fu
#    scritta e ha smesso di esserlo il 25/08, quando la richiesta DB-10 — fatta
#    da questo stesso cantiere — e' atterrata. ⚠️ *Una richiesta esaudita e non
#    raccolta e' peggio di una non fatta: il documento dice che manca, il
#    database ce l'ha, e nessuno dei due mente da solo.*
# ⛔ Resta il divieto che quella nota portava, e vale per sempre: l'`incassato`
#    del documento NON si somma dalle rate. Una riga contabile puo' avere fattura
#    SENZA rata — il fondo fattura e' esattamente cosi' — e quel denaro non
#    comparirebbe in nessuna somma di rate. Un numero incompleto che si presenta
#    come completo e' peggio di un numero assente.
# ⭐ `escludi_riga_id` dal 2026-09-18 (P-6 del brief D19): «prima di se'» anche
#    sul documento — la riga senza rata (il fondo fattura e' cosi') che si sta
#    correggendo non si conta piu' addosso. Fino a quel giorno il pannello lo
#    DICHIARAVA («comprende anche questa riga») invece di fingere; ora la
#    funzione lo sa fare e la dichiarazione non serve piu'.
def saldo_documento(
    fattura_id: int, *, escludi_riga_id: int | None = None
) -> SaldoRow:
    repository = PagamentiRepository()
    # ⭐ Una lettura sola per i due numeri: separate leggerebbero due istanti
    #    diversi, e un residuo di prima accanto a un «in lavorazione» di dopo
    #    sono due numeri veri che insieme raccontano una cosa falsa.
    numeri = repository.get_saldo_documento(
        fattura_id, escludi_riga_id=escludi_riga_id
    )
    # ℹ️ Il 404 di un documento inesistente lo solleva GIA' il database
    #    (`E_FATTURA_NON_TROVATA`) e arriva al client tradotto senza passare di
    #    qui. Questo guard copre l'altro caso — una risposta VUOTA — che
    #    altrimenti diventerebbe un KeyError sul percorso d'errore.
    ErrorManager.require(
        numeri is not None,
        code=E_FATTURA_NON_TROVATA,
        message="Fattura non trovata.",
        detail=f"fattura_id={fattura_id}",
        function_name=f"{_FN}.saldo_documento",
    )
    assert numeri is not None
    return _saldo(
        residuo=numeri["saldo"],
        in_lavorazione=numeri["in_lavorazione"],
        incassato=numeri["incassato"],
        has_movimenti=bool(numeri["has_movimenti"]),
        livello="DOCUMENTO",
        riferimento_id=fattura_id,
    )


# ══════════════════════════════════════════════════════════════════
#  Livello RATA
# ══════════════════════════════════════════════════════════════════

# Scopo: Il saldo di una rata.
# ⚠️ `escludi_riga_id` chiede lo spazio PRIMA DI SE': serve a sapere se una
#    riga ci sta senza contarsi addosso. Dal 2026-09-18 lo sa fare anche il
#    documento: stesso nome, stessa domanda.
def saldo_rata(
    scadenza_id: int, *, escludi_riga_id: int | None = None
) -> SaldoRow:
    repository = PagamentiRepository()
    riga = repository.get_saldo_rata(scadenza_id, escludi_riga_id=escludi_riga_id)
    ErrorManager.require(
        riga is not None,
        code=E_RATA_NON_TROVATA,
        message="Rata non trovata.",
        detail=f"scadenza_id={scadenza_id}",
        function_name=f"{_FN}.saldo_rata",
    )
    assert riga is not None
    return _saldo(
        residuo=riga["saldo"],
        in_lavorazione=riga["in_lavorazione"],
        incassato=riga["incassato"],
        has_movimenti=bool(riga["has_movimenti"]),
        livello="RATA",
        riferimento_id=scadenza_id,
    )


# Scopo: Le rate di un documento, ciascuna col suo saldo — la risposta alla
#        domanda «su quale rata metto questi soldi?».
# ⭐ Un giro solo e non uno per rata: il form dell'abbinamento le mostra tutte
#    insieme, e N chiamate per disegnare un menu sono N modi di essere lenti.
def saldi_rate_documento(fattura_id: int) -> dict[str, Any]:
    repository = PagamentiRepository()
    rate = repository.list_rate_con_saldo(fattura_id)
    return {"count": len(rate), "results": rate}


# Scopo: L'ELENCO PAGINATO DELLE RATE col saldo dalla base unica — la quarta
#        lettura di questo modulo (D19-c, 2026-09-17): la sorgente del picker
#        della distinta e, domani, dello scadenzario.
# ⭐ Sta QUI e non in `pagamenti_service` perche' la domanda e' «quanto resta su
#    ogni rata», e a rispondere e' la base dei saldi: le tre colonne della
#    risposta (`residuo · in_lavorazione · incassato`) sono `CAMPI_SALDO`, con
#    gli stessi nomi del pannello — una schermata sceglie quali accendere,
#    nessuna li rinomina.
# ⚠️ Offset-based (`limit`/`offset`), come `fatture/{id}/sistemazioni/`: e' la
#    lingua di `useSearchTable` e di `createListaStore`, e la lista e' montata
#    su `<ListaConfigurabile>`. Le liste piu' vecchie del dominio sono
#    page-based; la conversione la fa lo store, in un posto solo.
# ⛔ `order_dir` puo' arrivare `None` (assente): senza verso esplicito decide
#    il repository — e su una colonna DATA il verso naturale e' DESC.
# ⚠️ NESSUN criterio e' obbligatorio QUI: il picker lo pretende nel frontend
#    (cliente o numero fattura, D19-c), lo scadenzario no — e' la stessa rotta.
# ⚠️ `solo_aperte` e' SUPPORTATO dal 2026-09-17 (P-3 consegnata): «aperta» =
#    `residuo <> 0` (Q-B di Tid). Il piano lo dava «accettato e dichiarato non
#    supportato finche' P-3 non c'e'»; P-3 c'e'.
# ⭐ `natura_doc_codice`: il vocabolario e' del catalogo
#    (`config.nature_doc_fiscale.codice_interno`) ed e' APERTO — le nature si
#    seminano — quindi qui si accetta qualunque codice e un valore inesistente
#    da' una lista vuota, che e' la risposta giusta: un elenco cablato sarebbe
#    una seconda sede. Il maiuscolo lo mette QUESTO service, com'e' scritto a
#    catalogo — la view lo passa com'e'.
def list_rate(
    *,
    auth_user_id: int | None,
    billing_account_id: int | None = None,
    fattura_numero: int | None = None,
    serie: str | None = None,
    anno: int | None = None,
    search: str | None = None,
    solo_aperte: bool | None = None,
    solo_numerate: bool | None = None,
    data_scadenza_da: date | None = None,
    data_scadenza_a: date | None = None,
    natura_doc_codice: str | None = None,
    limit: int,
    offset: int = 0,
    order_by: str | None = None,
    order_dir: str | None = None,
) -> dict[str, Any]:
    # ⭐ `nullable=True`: «non specificato» e' legittimo e l'ordine lo decide il
    #    repository (il default a catalogo, `data_scadenza ASC`). Fuori
    #    whitelist e' un 400 col campo, non un 500 sul `ORDER BY`.
    order_by, order_dir = validate_order_params(
        order_by, order_dir,
        allowed_columns=RATE_SORT_COLUMNS,
        error_code=E_VALIDAZIONE,
        function_name=f"{_FN}.list_rate",
        nullable=True,
    )
    # ⛔ Nessun 400 sotto soglia (brief-db-be-fe-ricerca-soglia-per-lista §6 a,
    #    Tid 2026-09-26): il termine corto lo ignora il BB di ricerca, sulla soglia che il catalogo della
    #    lista dichiara — la stessa che il frontend legge per non mandarlo. Un
    #    controllo qui sarebbe una seconda sede della stessa soglia.
    repository = PagamentiRepository()
    results, total = repository.list_rate_paginata(
        auth_user_id=auth_user_id,
        billing_account_id=billing_account_id,
        fattura_numero=fattura_numero,
        serie=serie,
        anno=anno,
        search=search,
        solo_aperte=bool(solo_aperte),
        # ⭐ `None` (parametro ASSENTE) significa «applica la regola», non
        #    «falso»: `solo_numerate` e' un perimetro di dominio — la rata di una
        #    bozza non e' un credito — e un perimetro che si accende solo quando
        #    il client se lo ricorda non e' un perimetro. ⛔ Qui NON si usa
        #    `bool(...)`, che mapperebbe l'assenza su `False` come per
        #    `solo_aperte`: quello e' un filtro vero, questo no. Chi vuole anche
        #    le bozze passa `False` esplicito.
        solo_numerate=True if solo_numerate is None else bool(solo_numerate),
        data_scadenza_da=data_scadenza_da,
        data_scadenza_a=data_scadenza_a,
        natura_doc_codice=natura_doc_codice.upper() if natura_doc_codice else None,
        order_by=order_by,
        order_dir=order_dir,
        limit=limit,
        offset=offset,
    )
    return {"count": total, "results": results}


# ══════════════════════════════════════════════════════════════════
#  Livello CLIENTE — dichiarato, non ancora acceso
# ══════════════════════════════════════════════════════════════════
#
# 📮 Il terzo livello e' previsto (decisione di Tid, §2.7 del brief BE/FE) e non
#    si scrive adesso. ⭐ Ma il suo prerequisito NON manca piu': DB-10 e'
#    atterrata il 25/08 e da oggi `saldo_documento` risponde anche l'`incassato`
#    — cioe' il numero che «quanto mi deve questo cliente» pretende e che, fino a
#    ieri, sarebbe stato sommato mancante.
# ⭐ Quando si accendera' nasce QUI e nessun'altra sede cambia: e' il punto di
#    avere una base sola. ⛔ E si sommeranno i DOCUMENTI, mai le rate — vale a
#    ogni livello la ragione scritta su `saldo_documento`.
