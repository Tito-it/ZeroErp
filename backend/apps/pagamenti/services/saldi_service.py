# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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

from decimal import Decimal
from typing import Any

from apps.core.services.error_manager import ErrorManager
from apps.pagamenti.db.pagamenti_repository import PagamentiRepository
from apps.pagamenti.services._helpers import E_FATTURA_NON_TROVATA
from apps.pagamenti.types import SaldoRow

_FN = "pagamenti.saldi_service"

# Codice gia' a catalogo: la rata non esiste (o il perimetro non la lascia
# vedere, e i due restano indistinguibili). Il gemello della fattura sta in
# `_helpers`, condiviso coi due service che lo sollevano allo stesso modo.
E_RATA_NON_TROVATA = "E_RATA_NON_TROVATA"

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
def saldo_documento(fattura_id: int) -> SaldoRow:
    repository = PagamentiRepository()
    # ⭐ Una lettura sola per i due numeri: separate leggerebbero due istanti
    #    diversi, e un residuo di prima accanto a un «in lavorazione» di dopo
    #    sono due numeri veri che insieme raccontano una cosa falsa.
    numeri = repository.get_saldo_documento(fattura_id)
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

# Scopo: Il saldo di una rata — l'unico livello che oggi risponde tutti e tre
#        i numeri.
# ⚠️ `escludi_riga_id` chiede lo spazio PRIMA DI SE': serve a sapere se una
#    riga ci sta senza contarsi addosso.
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
