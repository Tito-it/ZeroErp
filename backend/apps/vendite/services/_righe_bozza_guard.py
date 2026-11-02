# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «Le righe di un documento si toccano solo in bozza», detto dal
#        Python PRIMA di scrivere, con il codice e la frase che il database
#        usa per rifiutare la stessa cosa: `E_RIGA_DOC_NON_BOZZA`.
# ------------------------------------------------------------

# PERCHE' ESISTE (decisione B di Tid, 2026-09-22, brief-db-partita-merce-per-
# documento §12.4). Dal 22-09 il database rifiuta INSERT/UPDATE/DELETE sulle
# righe di un documento fuori bozza con un building block solo
# (`vendite.trgfn_doc_righe_lock_fuori_bozza`, allora montato su `ddt_righe`,
# `contratti_righe` e — per il solo DELETE — `ordini_righe`) e un codice solo.
# I pre-check Python della stessa regola erano QUATTORDICI siti in tre service
# e rispondevano con TRE codici diversi (`E_DDT_STATO_TRANSIZIONE`,
# `E_ORD_STATO_TRANSIZIONE`, `E_PREV_STATO_NON_MODIFICABILE`) e frasi
# generiche: lo stesso rifiuto con due nomi a seconda di chi lo diceva.
#
# ⭐ La regola e' UNA e ha un nome a catalogo: chiunque la sollevi la chiama
# cosi'. Il pre-check resta — e' un 409 «prima di scrivere», defense-in-depth
# come il filtro di scope. Dal 2026-10-08 il DB copre TUTTI i documenti che
# lo chiamano (brief-db-righe-e-componenti-debiti-residui, D-1): componenti
# delle tre famiglie (`20261008-34`), righe d'ordine e di preventivo sulle tre
# porte (`20261008-90`/`-91`). Il pre-check e' quindi un doppione CON LO STESSO
# CODICE, e toglierlo sarebbe neutro per l'API.
# ⚠️ Sulle righe d'ordine il DB ha UN'eccezione che questo BB non ha:
# `data_consegna_confermata` resta scrivibile in CONFERMATO/PARZIALMENTE_EVASO.
# Qui non si ricopia: la portera' il verbo dedicato, che legge la capability
# dal DB (brief-db-ordine-data-consegna-confermata-capability) e non passa da
# questo guard. `aggiorna_riga` resta «solo in bozza» per tutte le colonne.
#
# ⚠️ La frase e' composta qui con i tre valori del catalogo (etichetta del
# documento, stato, verbo) — e' il caso in cui il chiamante i valori li ha, e
# il ripiego senza segnaposto di `error_messages_fallback` resta per il diario.
# Il template sta in `FRASE_CATALOGO` nella STESSA forma del catalogo (`%s`),
# e il test e2e `test_righe_bozza_guard` lo confronta con
# `config.messaggi_errore` sul DB vero: una copia senza presidio diverge in
# silenzio, e qui la copia e' voluta (niente round-trip a DB per un 409).
# L'etichetta segue `script.fn_get_stato_testata_documento`: «DDT <numero>»,
# con `#<id>` quando il numero non c'e' (in bozza e' il caso normale, non un
# residuo). ⚠️ Perche' l'etichetta sia quella del DB anche sui COMPONENTI, le
# letture `load_componente_with_scope` portano `numero`: senza, «DDT #131» su
# un DDT emesso — che il numero ce l'ha sempre — e nessun errore a dirlo.
# ⭐ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2a): il
# chiamante nomina il documento col codice di `config.sorgenti` (`SORGENTE_*`),
# che e' il `TG_ARGV[0]` del trigger e quindi il valore di `documento` nel
# `context`. Prima passava la PAROLA dell'etichetta («Ordine») e il contesto
# ne era il maiuscolo: dopo il 2a il DB scrive `ORDINE_VENDITA` e il Python
# `ORDINE`, due lingue nel diario per lo stesso rifiuto. Codice e parola
# sono due cose: la parola sta in `PAROLA_ETICHETTA`, una sede sola (prima
# era un letterale in ciascuno dei 17 chiamanti). Il preventivo porta anche
# la revisione, come l'etichetta del DB («Preventivo 2026/00012 rev. 1»).

from collections.abc import Mapping
from typing import Any, Literal

from apps.config.sorgenti import (
    SORGENTE_CONTRATTO,
    SORGENTE_DDT_VENDITA,
    SORGENTE_ORDINE_VENDITA,
    SORGENTE_PREVENTIVO,
    SORGENTE_RESO_VENDITA,
)
from apps.core.services.error_manager import ErrorManager

# Lo stato in cui le righe si toccano. E' il default del BB a DB
# (`TG_ARGV[2]`, `'DRAFT'`) e il valore che i tre service usavano nei loro
# `_STATI_RIGHE_MODIFICABILI = {"DRAFT"}`.
STATO_BOZZA = "DRAFT"

# I verbi della frase a catalogo e l'operazione SQL che ciascuno traduce: la
# stessa tabella del trigger (`CASE TG_OP WHEN 'INSERT' THEN 'aggiungere' …`),
# letta al contrario. Nel `context` esce l'operazione, come fa il trigger:
# il diario (`dbops.error_log`) deve leggere `operazione = 'DELETE'` sia dal
# guard a DB sia da questo, non due vocabolari sulla stessa chiave.
Verbo = Literal["aggiungere", "modificare", "togliere"]
OPERAZIONE_PER_VERBO: dict[str, str] = {
    "aggiungere": "INSERT",
    "modificare": "UPDATE",
    "togliere": "DELETE",
}

CODICE = "E_RIGA_DOC_NON_BOZZA"

# I documenti le cui righe passano da questo guard, coi codici di
# `config.sorgenti`. ⭐ `Literal` perche' le costanti `SORGENTE_*` sono `Final`:
# mypy rifiuta un codice fuori elenco (o un codice corto) gia' al chiamante.
DocumentoRighe = Literal[
    "DDT_VENDITA", "ORDINE_VENDITA", "PREVENTIVO", "CONTRATTO", "RESO_VENDITA",
]

# La parola con cui `script.fn_get_stato_testata_documento` apre l'etichetta.
# Le chiavi sono quelle di `DocumentoRighe` (presidio in `test_righe_bozza_guard`).
PAROLA_ETICHETTA: dict[str, str] = {
    SORGENTE_DDT_VENDITA: "DDT",
    SORGENTE_ORDINE_VENDITA: "Ordine",
    SORGENTE_PREVENTIVO: "Preventivo",
    SORGENTE_CONTRATTO: "Contratto",
    SORGENTE_RESO_VENDITA: "Reso",
}

# Il template di `config.messaggi_errore` per `CODICE` (lingua `it`), com'e':
# etichetta, stato, verbo. Presidiato sul DB vero dal test e2e.
FRASE_CATALOGO = (
    "%s non e' piu' in bozza (stato %s): le sue righe si possono %s "
    "solo finche' e' in bozza."
)


# Scopo: L'etichetta del documento come la compone il DB: «DDT 2026/00012»,
#        oppure «DDT #131» quando `numero` e' NULL (bozza mai numerata); il
#        preventivo con la revisione («Preventivo 2026/00012 rev. 1»), che il
#        DB aggiunge perche' le revisioni condividono il numero.
#        ⚠️ Una lettura del preventivo senza `rev` e' un lettore rotto: KeyError.
def _etichetta(documento: str, testata: Mapping[str, Any], documento_id: int) -> str:
    numero = testata.get("numero")
    etichetta = f"{PAROLA_ETICHETTA[documento]} {numero if numero else f'#{int(documento_id)}'}"
    if documento == SORGENTE_PREVENTIVO:
        etichetta += f" rev. {testata['rev']}"
    return etichetta


# Scopo: Rifiuta con `E_RIGA_DOC_NON_BOZZA` (409, banner) se la testata non e'
#        in bozza. `documento` e' il codice di `config.sorgenti` (`SORGENTE_*`,
#        uno di `DocumentoRighe`), `verbo` uno dei tre di `OPERAZIONE_PER_VERBO`,
#        `testata` una lettura che porta `stato_codice_interno` e `numero`
#        (per il preventivo anche `rev`).
# Perimetro e risultato atteso: nessun ritorno; solleva `ServiceError` col
#        codice del DB, la frase a catalogo composta coi tre valori e un
#        `context` con le chiavi E i valori del trigger (documento col codice
#        della sorgente, testata_id, stato, operazione SQL) — senza `field`:
#        su un conflitto di stato non c'e' un input da accendere.
#        ⚠️ Un verbo o un documento fuori catalogo, o una testata senza
#        `stato_codice_interno` (o senza `rev` sul preventivo) sono errori del
#        CHIAMANTE (un lettore che non porta lo stato), non della richiesta:
#        escono come eccezione Python (500 dal middleware), non come un 409
#        con un buco nella frase. Un `assert` non basterebbe: sparisce con `-O`.
def richiedi_righe_in_bozza(
    testata: Mapping[str, Any],
    *,
    documento: DocumentoRighe,
    documento_id: int,
    verbo: Verbo,
    function_name: str,
) -> None:
    try:
        operazione = OPERAZIONE_PER_VERBO[verbo]
    except KeyError:
        raise ValueError(f"verbo fuori catalogo: {verbo!r}") from None
    if documento not in PAROLA_ETICHETTA:
        raise ValueError(f"documento fuori catalogo: {documento!r}")
    stato = str(testata["stato_codice_interno"])
    if stato == STATO_BOZZA:
        return
    # L'etichetta si compone solo sul ramo del rifiuto: in bozza non serve, e
    # una lettura leggera (che in bozza non porta `rev`) non deve sollevare.
    ErrorManager.raise_error(
        code=CODICE,
        message=FRASE_CATALOGO % (_etichetta(documento, testata, documento_id), stato, verbo),
        detail=f"stato={stato}",
        context={
            "documento": documento,
            "testata_id": int(documento_id),
            "stato": stato,
            "operazione": operazione,
        },
        function_name=function_name,
    )
