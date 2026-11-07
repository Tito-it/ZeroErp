# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB generico per lo schema vendite (query, liste, decodifiche).
# ------------------------------------------------------------

# Contiene operazioni generiche sullo schema vendite che non appartengono
# a nessun sottodominio specifico (pipeline, reset, ecc.).

import logging
import re
from datetime import date
from collections.abc import Sequence
from typing import Any

from django.db import DatabaseError, connection, transaction

from apps.config.sorgenti import (
    SORGENTE_COMMESSA,
    SORGENTE_CONTRATTO,
    SORGENTE_DDT_VENDITA,
    SORGENTE_OFFERTA_COMMERCIALE,
    SORGENTE_ORDINE_VENDITA,
    SORGENTE_PREVENTIVO,
    SORGENTE_RESO_VENDITA,
)
from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT
from apps.core.db._helpers import (
    colonna_ordinamento,
    sql_order_direction_lista,
    limiti_pagina,
    RicercaFull,
    add_ricerca_full_condition,
    call_jsonb_fn,
    conta_con_perimetro,
    fetch_paged_with_total,
    iso_or_none,
    jsonb_out,
    predicato_giorno_operativo,
    query_paged_view,
    row_to_dict,
    rows_to_list,
    sql_lateral_primo_motivo,
    sql_order_clause,
    sql_order_direction,
    sql_tiebreak_direction,
)
from apps.core.services.system_context import connection_role_bypasses_rls
# ⚠️ Un repository di dominio che importa da `apps.ui`: e' la sede UNICA del
#    tetto dell'export, e la dipendenza e' su una costante, non su un servizio.
#    Il modulo importa solo stdlib e `apps.core` — nessun ciclo.
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.core.db.emittente_scope_helpers import add_emittente_scope_condition
from apps.core.services.error_manager import ErrorManager
from apps.vendite.db._coda_documento_filtro import (
    lettura_coda_per_documento,
    sorgente_per_documento,
)
from apps.vendite.db._data_documento_sql import (
    SQL_DATA_DOCUMENTO_CORRENTE,
    costruisci_perimetro_lotti_numerabili,
)
from apps.vendite.types import (
    DashApertoDocumentoRow,
    DashApertoRiepilogoRow,
    DashBacklogDocumentoRow,
    DashBacklogRiepilogoRow,
    DashCompetenzaAttivitaRow,
    DashCompetenzaResiduoRow,
    DashCompetenzaCommessaRow,
    DashCompetenzaErroreRow,
    DashCompetenzaGruppoRow,
    DashCompetenzaMensileRow,
    FondoFatturaDaDecidereRow,
    LineageNodoRow,
    LineagePassaggioRow,
    LottoFattureRow,
    LottoGruppoRow,
    LottoListRow,
)


# La testata del lotto nella mappa del modello del documento
# (`script.fn_doc_stato_modello`): la leggono la catena dei permessi
# (`PassaggioDocumento`) e la proiezione della riga di lotto (`azioni_permesse`).
# ⚠️ Sta qui, accanto alla lettura del lotto, e non in `pipeline_repository`:
#    di la' si arriva gia' a questo modulo (via `commesse_repository`), e
#    l'import inverso sarebbe un ciclo.
TESTATA_LOTTI = "vendite.fatturazione_lotti"

# Lo stato fiscale della NUMERAZIONE («Rendi definitive»): l'arrivo del passaggio
# `numera` del lotto (EMESSA -> DEFINITIVA), la fine della catena che numera e
# lo stato da cui il lotto si ristampa (`ristampa_lotto`, `ristampabile` della
# riga). ⚠️ Nessuna colonna del vocabolario lo dice (non e' l'emissione ne'
# l'annullo): come la `CONFERMATO` del reso, e' lo stato di arrivo di un verbo.
# Una sede, qui accanto alla testata e per la stessa ragione (il ciclo d'import).
STATO_DEFINITIVA = "DEFINITIVA"

logger = logging.getLogger(__name__)

# Whitelist colonne ordinamento per list_lotto_fatture; mai interpolate direttamente.
# Colonne ordinabili dei DOCUMENTI del lotto: chiave esposta al FE ->
# espressione SQL. Mai interpolate direttamente: solo i valori di questa mappa
# entrano nella query.
#
# ⭐ LA CHIAVE E' IL NOME DEL CAMPO NEL PAYLOAD, e non un sinonimo. Il seed di
# `ui.lista_colonna` dichiara `campo_sorgente`, e la lista configurabile manda
# QUELLO come `order_by`: se la chiave qui si chiamasse diversamente, la
# freccetta comparirebbe sull'intestazione e non ordinerebbe niente — un
# controllo che si vede e non funziona, peggio di un controllo assente.
# E' il motivo per cui `nominativo` e' diventato `ragione_sociale_completa`
# (richiesta BE-1 del team DB, 2026-08-22): il vecchio nome non esisteva in
# nessun payload.
#
# ⚠️ Il NUCLEO ordina sempre (regola delle liste standard): numero, data,
# identificativo fiscale e stati. Prima ne erano ordinabili 3 su 11, cioe' la
# lista sarebbe nata con cinque colonne di nucleo rotte.
# Il tetto delle righe esportabili delle liste del DRAWER LOTTO (documenti del
# lotto e documenti presi in carico). Il tetto di PAGINA (`MAX_LIMIT`)
# resta dov'e': sono due limiti diversi per due usi diversi, e confonderli
# significa o una pagina enorme o un file troncato.
#
# ⛔ SI DERIVA, non si riscrive, ed e' una correzione del 2026-09-06: qui c'era
#    un `10_000` scritto a mano, cioe' una SECONDA copia di
#    `apps.ui.services.lista_export_service.EXPORT_MAX_ROWS` — lo stesso numero
#    su cui il guard dell'export decide se il file e' completo.
#    ⚠️ Il difetto che due copie producono e' MUTO: alzando il tetto in una sola
#    sede, il guard lascerebbe passare un perimetro piu' grande mentre il
#    repository continuerebbe a troncare — un file con 10.000 righe consegnato
#    come completo. Nessun errore, nessun test rosso.
# 📌 Restano DUE copie dello stesso numero, dichiarate e non mie:
#    `_ATTIVITA_EXPORT_MAX_ROWS` (commesse_repository) e
#    `_DRAWER_EXPORT_MAX_ROWS` (pipeline_repository). Vanno nella stessa
#    direzione, ma toccano liste che questo cantiere non attraversa.
_LOTTO_EXPORT_MAX_ROWS = EXPORT_MAX_ROWS

# ⭐ Le colonne ordinabili del GIORNALE di un'entita', e sono due sole di
# proposito: la gravita' (default) e il tempo. ⛔ Non e' una lista ridotta «per
# ora»: `registro`, `chi` e `cosa` raggrupperebbero, non ordinerebbero — e su un
# elenco paginato un raggruppamento a video e' un ordinamento che mente.
# ⚠️ Il valore `rango` non e' una colonna della vista: e' il rango calcolato
# nella CTE, perche' il vocabolario e' testuale e in ordine alfabetico ERROR
# verrebbe PRIMA di INFO e WARN — una scala che non e' una scala.
# ⭐ Pubblica dal 2026-09-19 (pezzo G): la legge il presidio delle liste
#    configurabili (`test_liste_configurabili_seed._LISTE`) per la lista
#    `vendite.giornale`, e la view per la descrizione OpenAPI di `order_by`.
#    Le chiavi sono i `campo_sorgente` del catalogo: le due colonne che
#    ordinano davvero. Un nome solo, non un alias: due nomi per lo stesso dict
#    sono la forma in cui uno dei due smette di essere quello letto.
GIORNALE_SORT_COLUMNS: dict[str, str] = {
    "gravita": "rango",
    "quando": "quando",
}

# ⭐ L'ORDINE DI PARTENZA DEL GIORNALE, uno per i TRE lettori: il tempo, dal piu'
#    recente — lo stesso del preset `giornale_default` di `vendite.giornale`.
#    Dal 2026-09-27 (brief-db-liste-datatable-grezze §3.1, decisione di Tid) la
#    Storia della fattura e quella del lotto sono la STESSA lista a catalogo del
#    giornale trasversale, e una lista non parte in due modi a seconda della
#    scheda da cui la si apre.
# ⚠️ Fino a quel giorno la Storia di un'entita' partiva dalla GRAVITA' (Tid,
#    2026-08-24): «c'e' qualcosa che non va?» e' ora il banner della fattura,
#    che ha una fonte sua (`get_giornale_errore_vivo`) e non dipende piu'
#    dall'ordine della pagina. La gravita' resta a un clic sulla colonna.
# ⭐ La leggono le view (`parse_list_params(default_order=...)`) e
#    `_giornale_order_clause` qui sotto: un nome solo, o le due sedi del
#    default divergono al primo ritocco.
GIORNALE_ORDINE_DEFAULT = "quando"

# ⛔ I REGISTRI che la vista cuce NON stanno piu' qui (2026-09-19, brief-db-
#    registri-giornale-catalogo): fino a quel giorno `GIORNALE_REGISTRI` era la
#    seconda delle tre sedi che non si conoscevano (i letterali dei rami
#    `UNION ALL`, questa costante, l'array del frontend), e un ramo nuovo
#    entrava nella vista lasciando le altre due indietro senza nessun errore.
#    La sede e' `config.registri_giornale` (pgTAP `test-giornale-registri-
#    catalogo-v1` la lega alla vista nei due versi): il filtro `registro` si
#    valida con `VenditeRepository.registri_giornale_ammessi()`, il frontend
#    legge la tendina dal lookup generico. Il quinto registro = un `UNION ALL`
#    + una riga di CSV, e qui non cambia niente.
# Le tre gravita' normalizzate della vista. ⚠️ `NULL` non e' una quarta: e' il
# segnale di «un vincolo si e' allargato e la mappa e' rimasta indietro», e
# viaggia INSIEME a `ERROR` (pesa come un ERROR, vedi `rango_gravita`).
GIORNALE_GRAVITA: tuple[str, ...] = ("ERROR", "WARN", "INFO")


# Scopo: la clausola `ORDER BY` del giornale di un'entita', a partire dalla
#        colonna chiesta e dal verso. ⭐ E' una funzione PURA perche' e' la parte
#        che si sbaglia in silenzio: un ordinamento storto non solleva niente e
#        a video somiglia a un ordinamento giusto. Cosi' si prova senza DB.
# ⚠️ Non concatena mai `NULLS ...` a mano: la direzione la compone
#    `sql_order_direction`, che i NULL li porta gia' con se' (BB di casa).
# ⚠️ Una colonna fuori whitelist ricade sul default (`GIORNALE_ORDINE_DEFAULT`):
#    qui e' l'ultima rete, non il cancello — i service la rifiutano PRIMA con un
#    400 (`_valida_ordinamento`), perche' un ordine diverso da quello chiesto
#    non solleva niente.
def _giornale_order_clause(sort_by: str | None, sort_dir: str | None) -> str:
    direzione = sql_order_direction(sort_dir, default_desc=True)
    colonna = colonna_ordinamento(sort_by, GIORNALE_SORT_COLUMNS) or GIORNALE_SORT_COLUMNS[GIORNALE_ORDINE_DEFAULT]
    if colonna == "rango":
        # ⚠️ Dentro la stessa gravita' ordina il TEMPO, sempre dal piu' recente,
        #    e NON segue il verso scelto: «i piu' gravi, e fra quelli i piu'
        #    recenti» resta la lettura utile anche guardando dal meno grave.
        #    `riga_id` chiude come sempre — e' il rimedio a R-1, il tempo da
        #    solo non ordina (default `now()` = timestamp di transazione).
        return f"t.rango_gravita {direzione}, t.quando DESC, t.riga_id DESC"
    return f"t.quando {direzione}, t.riga_id {sql_tiebreak_direction(direzione)}"

LOTTO_FATTURE_SORT_COLUMNS: dict[str, str] = {
    "fattura_id": "fllf.fattura_id",
    "numero": "f.numero",
    "serie": "f.serie",
    "data": "f.data",
    "ragione_sociale_completa": "srd.ragione_sociale_completa",
    "id_fiscale_univoco_cf_piva": "srd.id_fiscale_univoco_cf_piva",
    "natura_doc_descrizione": "ndf.descrizione",
    "stato_doc_fiscale_descrizione": "sdf.descrizione",
    "stato_esecuzione": "fllf.stato_esecuzione",
    "totale_doc": "f.totale_doc",
    "totale_a_pagare": "f.totale_a_pagare",
}
# Le colonne DATA di `LOTTO_FATTURE_SORT_COLUMNS`: senza direzione indicata
# partono DESC (regola Tid 2026-09-02, `colonne_desc` di `sql_order_clause`).
LOTTO_FATTURE_SORT_COLONNE_DATA: frozenset[str] = frozenset({"data"})

# Ordinamenti ammessi sui GRUPPI di un lotto — i documenti che il lotto ha
# preso in carico, con l'esito di ciascuno (brief-db-esito-gruppo-lotto §6).
#
# ⚠️ Le chiavi sono i nomi di OUTPUT della SELECT, non le colonne fisiche: le
# quattro di identita' escono da un'aggregazione (`ref`), e ordinare per
# l'espressione riscritta invece che per l'alias e' il modo in cui una copia
# diverge dall'originale (api.md §whitelist di ordinamento).
# ⛔ `errore_messaggio` NON e' ordinabile, ed e' una scelta: mettere in ordine
#    alfabetico delle frasi non risponde a nessuna domanda. La sua riga a
#    catalogo e' `ordinabile = f`, e i due versi di
#    `test_liste_configurabili_seed` tengono le due cose allineate.
LOTTO_GRUPPI_SORT_COLUMNS: dict[str, str] = {
    "riferimento": "riferimento",
    "tipo_gruppo": "tipo_gruppo",
    "stato_esecuzione": "stato_esecuzione",
    "errore_codice": "errore_codice",
    "errore_quando": "errore_quando",
    "commessa_codice": "commessa_codice",
}

# Aree della famiglia dash fatturazione, nell'ordine del funnel (brief
# brief-design-dashboard-fatturazione §4 + §6-quater design due-lenti,
# DL-21/24). Allineate al discriminante `area` della union
# vendite.vw_dash_fatturazione_documenti (6 aree documento) + il ramo RESI
# che vive SOLO nel Backlog (union dedicata in vw_dash_backlog_documenti,
# fuori dal funnel pre-commessa). Usate dalla Lente 2 Backlog (che include
# commesse e resi).
# ⭐ L'area e' il codice della SORGENTE (`config.sorgenti.codice_interno`): dal
#    2026-10-20 le viste `vw_dash_*` non scrivono piu' il plurale (`ORDINI`,
#    `RESI`…), ritirato col sotto-giro 2d di brief-db-grammatica-unica-documenti
#    (G-6). Quali aree mostra la dashboard resta una scelta di presentazione,
#    ed e' questa tupla.
DASH_FATTURAZIONE_AREE: tuple[str, ...] = (
    SORGENTE_PREVENTIVO,
    SORGENTE_ORDINE_VENDITA,
    SORGENTE_DDT_VENDITA,
    SORGENTE_OFFERTA_COMMERCIALE,
    SORGENTE_CONTRATTO,
    SORGENTE_COMMESSA,
    SORGENTE_RESO_VENDITA,
)

# Aree con valore monetario (imponibile, decisione D-4). Offerte e contratti
# restano a conteggi (decisioni D-2/D-3 confermate da DL-11), resi idem
# (DL-24: nessun importo sui resi in questa slice): valore_* = NULL.
DASH_FATTURAZIONE_AREE_EURO: frozenset[str] = frozenset(
    {SORGENTE_PREVENTIVO, SORGENTE_ORDINE_VENDITA, SORGENTE_DDT_VENDITA, SORGENTE_COMMESSA}
)

# Aree della Situazione aperta (stock documenti, §6-bis/§6-quater design
# due-lenti): le 5 aree documento nell'ordine del funnel — NIENTE commesse
# (coperte dalla Lente 1), NIENTE resi (DL-24: REVERSE_FLOW, non serbatoio).
# Il DDT entra con la popolazione ristretta del resolver (DL-21: solo DDT
# con ruolo di fatturazione). Allineate al WHERE di
# vendite.vw_dash_aperto_documenti.
DASH_APERTO_AREE: tuple[str, ...] = (
    SORGENTE_PREVENTIVO,
    SORGENTE_ORDINE_VENDITA,
    SORGENTE_DDT_VENDITA,
    SORGENTE_OFFERTA_COMMERCIALE,
    SORGENTE_CONTRATTO,
)

# Fasi VIVE del serbatoio pre-commessa (v2, DL-15/16): solo aperti-non-chiusi
# → niente CHIUSO. Ordine = maturita' verso la commessa (DL-10): bozza interna
# → palla al cliente → da lavorare. Non tutte le aree emettono tutte le fasi
# (es. ORDINI non ha IN_ATTESA): il pivot le espone comunque tutte (griglia
# simmetrica, il FE decide quali card mostrare — DL-13).
# Il vocabolario INTERO della fase normalizzata dei documenti: specchio del
# CHECK `chk_stati_doc_*_fase`, uguale su tutte le `config.stati_doc_*`
# (presidio: `core/tests/db/test_specchi_dei_check_db`). `DASH_APERTO_FASI`
# qui sotto ne e' il sottoinsieme VIVO, quello che il pivot mostra.
FASI_DOCUMENTO: tuple[str, ...] = ("APERTO", "IN_ATTESA", "IN_CORSO", "CHIUSO")

DASH_APERTO_FASI: tuple[str, ...] = (
    "APERTO",
    "IN_ATTESA",
    "IN_CORSO",
)

# Stadi del funnel Lente 1 Competenza, nell'ordine commessa → fattura (brief
# brief-db-fatturazione-due-lenti §4.1). Allineati al CASE `stadio` di
# vendite.vw_dash_competenza_attivita. Il primo stadio ha una costante puntuale:
# e' il perimetro dell'approvazione massiva A-2 (un solo owner del letterale).
# Valore SINTETICO di `tipo_gruppo` per le righe sourceless (oneri di
# commessa): non e' un `config.sorgenti.codice_interno` ma il COALESCE della
# vista vw_dash_competenza_gruppi. Costante e non letterale sparso: e' il
# discriminante degli oneri nel riepilogo e nel filtro per tipo, ed e' anche il
# motivo per cui la tendina non si puo' costruire da `config.sorgenti` (dove
# questo valore non esiste).
TIPO_GRUPPO_ONERI = "ONERI_COMMESSA"

# Colonne su cui la ricerca libera della lista GRUPPI (D-6) SA cercare; quali
# cerca davvero, per questo operatore, lo dice il catalogo a ogni ricerca
# (`add_ricerca_full_condition`, brief-be-ricerca-full-liste-residue §2).
# Sono cinque perche' l'operatore fa due domande diverse — «dammi tutto di
# questo cliente» e «dov'e' finito ORD0005174» — e la seconda non si risponde
# con un filtro strutturato.
# ⭐ 2026-09-24 (passo 7 del brief): la lista cercava senza che il catalogo lo
#    dichiarasse (§7-bis); il seed del team DB ha acceso le cinque colonne e la
#    ricerca e' passata dal BB. ⛔ Ritirati nello stesso giro
#    `DASH_COMPETENZA_GRUPPI_SEARCH_COLUMNS` (l'elenco cablato) e
#    `SEARCH_MIN_LEN` (un 3 scritto qui accanto a quello del BB, cioe' la
#    seconda sede che il suo stesso commento diceva di non volere): la soglia e'
#    quella del BB, che vale anche per l'export perche' sta nel repository.
# ⚠️ Costo dichiarato, non scoperto dopo: quattro di queste hanno un indice
#    trigram a monte (ragione sociale, id fiscale, codice BA, codice commessa),
#    `riferimento` NO — e' un `COALESCE` il cui primo ramo si risolve per riga
#    (`vendite.fn_get_sorgente_documento_ref`, una tabella), quindi va valutato
#    per ogni gruppo del perimetro PRIMA di poter filtrare. Resta dentro perche'
#    e' la domanda che l'operatore fa davvero; se un mese pieno non reggesse, il
#    rimedio NON e' togliere il campo ma ancorare la ricerca alla sorgente del
#    documento (DL-2 del brief, aperto).
_RICERCA_DASH_COMPETENZA_GRUPPI = RicercaFull(
    "vendite.dash_competenza_gruppi",
    ("riferimento", "cliente_display", "commessa_codice", "ba_codice_fatturazione", "id_fiscale"),
)

# Vocabolario dell'esito di esecuzione dentro un lotto — specchio Python del
# CHECK `chk_lotti_gruppi_stato_esecuzione` (e del gemello sulle fatture del
# lotto: D-2 del brief-db-esito-gruppo-lotto li tiene IDENTICI, perche' due
# colonne che rispondono alla stessa domanda a due livelli non possono parlare
# due lingue).
# ⚠️ `NULL` NON e' in questa tupla ed e' voluto: e' l'assenza di risposta —
# «nessuno l'ha detto» — non un valore del vocabolario. Un filtro su «mai
# tentati» sarebbe una domanda diversa, e la si porrebbe con un altro
# parametro, non con una quinta voce qui dentro.
# ⭐ I due valori che il codice NOMINA vivono in una costante ciascuno, e la
#    tupla li riusa: cosi' «l'elenco ammesso» e «il valore che scrivo» non
#    possono divergere. Gli altri due (`PENDING`, `RUNNING`) nessuno li scrive
#    ne' li confronta — restano stringhe dell'elenco finche' non serviranno.
STATO_ESECUZIONE_ERRORE = "ERRORE"
STATO_ESECUZIONE_COMPLETED = "COMPLETED"
# ⭐ Il surplus DICHIARATO del livello DOCUMENTO: l'operatore ha tolto questo
#    documento dal giro (`vendite.fn_escludi_documento_da_giro`, 2026-09-08).
#    Una FATTURA quello stato non lo puo' avere — quando un documento esce, la
#    sua bozza viene cancellata e la riga di ponte sparisce: non esiste una
#    fattura «esclusa ma ancora li'».
STATO_ESECUZIONE_ESCLUSO = "ESCLUSO"
# Il vocabolario COMUNE ai due livelli — documento preso in carico e fattura
# prodotta rispondono alla stessa domanda, e la D-2 di
# `brief-db-esito-gruppo-lotto` li vuole nella stessa lingua.
STATI_ESECUZIONE_LOTTO: tuple[str, ...] = (
    "PENDING",
    "RUNNING",
    STATO_ESECUZIONE_COMPLETED,
    STATO_ESECUZIONE_ERRORE,
)
# ⛔ IL LIVELLO DOCUMENTO E' IL COMUNE PIU' IL SURPLUS, e si scrive cosi' —
#    per SOMMA, non come una seconda lista — perche' il giorno che il
#    vocabolario comune cresce, questo cresce con lui senza che nessuno se ne
#    ricordi. Due elenchi scritti a mano divergono al primo valore nuovo.
# ⚠️ E la divergenza fra i due livelli e' LEGITTIMA ma DICHIARATA: il cancello
#    `test_esito_esecuzione_lotto_guardrail` non confronta piu' «identici» ma
#    «identici a meno di questo surplus», che e' la stessa forma decisa dal
#    team DB per il pgTAP gemello (brief-db-uscita-documento-dal-giro §7-bis).
STATI_ESECUZIONE_DOCUMENTO: tuple[str, ...] = (
    *STATI_ESECUZIONE_LOTTO,
    STATO_ESECUZIONE_ESCLUSO,
)

# ⛔ `STATI_LOTTO` (lo specchio del CHECK `chk_fatturazione_lotti_stato_job`) e'
#    ritirato il 2026-10-27: lo stato del job e' un vocabolario in tabella
#    (`config.stati_lotto_job`, FK sul codice dal `20261027-05`, F-4 di
#    brief-modello-documento-vendita §15), e il filtro della lista lotti lo
#    legge da li' (`richiedi_codice_a_vocabolario`). Il CHECK non c'e' piu'.

DASH_STADIO_DA_APPROVARE = "DA_APPROVARE"
DASH_COMPETENZA_STADI: tuple[str, ...] = (
    DASH_STADIO_DA_APPROVARE,
    "DA_EMETTERE",
    "EMESSA_NON_FATTURATA",
    "FATTURATA",
)

# ⭐ L'unico dei tre valori di `motivo_non_fatturata` (vocabolario chiuso
# della vista `vw_dash_competenza_attivita`, changeSet 20260826-54; a TRE
# valori dal 20260912-36: dentro EMESSA_NON_FATTURATA la riga e' EMESSA per
# costruzione, quindi «in attesa del lotto» non esiste) che CHIEDE
# un'azione: le altre due situazioni — GIRO_IN_CORSO,
# SENZA_ATTIVITA_FATTURABILE — sono «niente da fare».
# ⛔ Vive QUI, in una sede sola, e si passa come PARAMETRO SQL: il letterale
# embedded e' la lezione gia' pagata sullo stadio (vedi
# TIPO_INDIRIZZO_FATTURAZIONE qui sotto). Il service la importa invece di
# riscriverla — due copie dello stesso valore, una in SQL e una in Python,
# divergono senza che niente fallisca: la lista mostrerebbe un perimetro e la
# card ne conterebbe un altro.
# Presidio (DB provvisto): `tests/db/test_motivo_non_fatturata_locale` — il
# valore e' fra quelli che la vista emette, e ogni valore emesso ha la sua
# etichetta nei locales.
MOTIVO_NON_FATTURATA_RESIDUO = "RESIDUO"

# Codice stabile (codice_interno di config.tipi_indirizzi) dello slot letto
# nella testata fattura per la stampa: indirizzo di fatturazione del cliente,
# dalla riga FATT del satellite congelato `fatture_indirizzi`. Costante passata
# come parametro SQL (mai letterale embedded — lezione review A+B sul letterale
# stadio). La gemella TIPO_INDIRIZZO_SEDE_LEGALE e' stata RITIRATA con la Fase 2
# satelliti (2026-07-31): la sede dell'emittente ora arriva gia' risolta dentro
# `emittente_snapshot->'sede'`, congelata a DB — qui non si risolve piu' nulla.
TIPO_INDIRIZZO_FATTURAZIONE = "FATT"

# Classi di azionabilita' della Lente 2 Backlog, nell'ordine di esposizione UI
# del design (§5: contatori 🟠 recuperabile · 🔵 sollecito cliente · 🔴
# anomalia). Il FISIOLOGICO 🟢 e' escluso a monte dalla vista. Allineate al
# CHECK di config.motivi_fermo (DL-6).
DASH_BACKLOG_CLASSI: tuple[str, ...] = (
    "RECUPERABILE",
    "SOLLECITO_CLIENTE",
    "ANOMALIA",
)

# Motivi di `vendite.vw_fondi_fattura_da_decidere` (D-10 di
# brief-db-fondo-fattura-ricalcolo-e-governo), nell'ordine in cui la vista li
# produce. Il vocabolario e' chiuso PER COSTRUZIONE — sono letterali nei rami
# della UNION, nessun dato li genera — quindi questa tupla e' un mirror: se la
# vista guadagna un motivo, va aggiornata insieme.
# ⚠️ In PostgreSQL non esiste un CHECK su una vista: il presidio del vocabolario
# e' il pgTAP che asserisce l'insieme dei motivi, non un vincolo.
# ⚠️ L'ordine entra nel `detail` dell'errore di validazione del filtro: e'
# l'elenco che legge chi ha sbagliato a scriverlo.
FONDI_DA_DECIDERE_MOTIVI: tuple[str, ...] = (
    "PROPOSTA_SENZA_ATTO",
    "IMPORTO_NON_CORRISPONDENTE",
    "NON_PIU_CAPIENTE",
    "UTILITY_NON_ATTRIBUIBILE",
)


# I due versi del legame documentale della nota di credito, come coppia di
# COLONNE di `vendite.fatture_rettifiche`: (colonna da filtrare, colonna da
# raggiungere). ⭐ Sede unica del ribaltamento — il verso non si scrive due
# volte dentro una query, dove le due copie possono divergere.
#   rettifica      : da una NC, i documenti che rettifica
#   rettificata_da : da una fattura, le note che la rettificano
_RETTIFICHE_VERSI: dict[str, tuple[str, str]] = {
    "rettifica": ("fattura_id", "rettificata_id"),
    "rettificata_da": ("rettificata_id", "fattura_id"),
}


# Colonne che gli AGGREGATI del contorno lista-gruppi leggono (riepilogo, tre
# facet, conteggio di perimetro). ⚠️ Sono solo quelle degli aggregati: cio' che
# serve ai FILTRI lo dichiara `_where_gruppi_filtri`, accanto al predicato che
# lo usa — e solo quando quel filtro e' davvero attivo.
_ACCESSORI_COLONNE_AGGREGATI = (
    "g.tipo_gruppo",
    "g.documento_apribile",
    "g.n_attivita",
    "g.valore",
    "g.ba_fatturazione_id",
    "g.cliente_fatturazione_display",
    "g.ba_codice_fatturazione",
    "g.id_fiscale",
    "g.registri_ids",
    # ⭐ `20260909-66`: il riepilogo ESCLUDE i gruppi trattenuti e li dichiara.
    #    Serve agli aggregati, quindi sta qui.
    "g.emissione_blocco_reason",
)

# I lotti ANNULLATI nel perimetro della lista (2026-09-12): fuori di default
# (`esclusi`), dentro a richiesta (`inclusi`), e SOLO loro per contare quanti
# ne restano fuori (`solo`). Il predicato e' il flag di catalogo
# `config.stati_doc_fiscale.is_abortito`, letto dalla JOIN `sdf` che la lista
# ha gia': ⛔ mai il `codice_interno`, che e' vocabolario del database.
LOTTI_ANNULLATI_ESCLUSI = "esclusi"
LOTTI_ANNULLATI_INCLUSI = "inclusi"
LOTTI_ANNULLATI_SOLO = "solo"
# `COALESCE`: un lotto senza stato fiscale (`stato_doc_fiscale_id` e' nullable)
# non e' abortito — la `LEFT JOIN` lo lascerebbe a NULL, e `NULL IS FALSE` e'
# falso: sparirebbe dalla lista senza che nessuno l'abbia annullato.
_LOTTI_COND_NON_ABORTITO = "COALESCE(sdf.is_abortito, FALSE) IS FALSE"
_LOTTI_COND_ABORTITO = "sdf.is_abortito IS TRUE"
# La JOIN che porta `sdf` — una sola, composta dentro `_LOTTO_JOINS` e riusata
# dal calendario, che ha un perimetro suo (l'anno) e non passa dalla lista.
_LOTTI_JOIN_SDF = """
            LEFT JOIN config.stati_doc_fiscale sdf
                ON sdf.id = fl.stato_doc_fiscale_id"""
# ⭐ LA SEDE UNICA di «quale condizione per quale valore»: chi compone un
#    perimetro (la lista con `_lotti_conditions`, il calendario con l'anno)
#    chiede qui e non nomina i frammenti. `None` = nessuna condizione.
_LOTTI_COND_PER_ANNULLATI: dict[str, str | None] = {
    LOTTI_ANNULLATI_ESCLUSI: _LOTTI_COND_NON_ABORTITO,
    LOTTI_ANNULLATI_INCLUSI: None,
    LOTTI_ANNULLATI_SOLO: _LOTTI_COND_ABORTITO,
}


# Scopo: la forma a due valori che vedono service e view (`includi_annullati`)
#        tradotta nei tre del repository. Il terzo (`solo`) non e' un'opzione
#        del chiamante: lo usa solo `count_lotti_annullati`.
def _annullati_da_flag(includi_annullati: bool) -> str:
    return LOTTI_ANNULLATI_INCLUSI if includi_annullati else LOTTI_ANNULLATI_ESCLUSI


# Scopo: la condizione SQL sull'abortito per un valore dell'enum, o `None`.
#        Un valore inventato e' un errore, non un elenco vuoto.
def _condizione_annullati(annullati: str) -> str | None:
    if annullati not in _LOTTI_COND_PER_ANNULLATI:
        raise ValueError(f"annullati: valore non ammesso {annullati!r}")
    return _LOTTI_COND_PER_ANNULLATI[annullati]


class VenditeRepository:

    # Scopo: Query paginata su vista/union costosa in UNA valutazione con
    #        CLAMP all'ultima pagina (il service dichiara la pagina effettiva
    #        nell'envelope). Estratto 2026-07-07 (regola del 2, ok Tid) per
    #        aperto/backlog/errori; PROMOSSO a BB core 2026-07-18
    #        (`apps.core.db._helpers.query_paged_view`, ok Tid): qui resta il
    #        delegatore per i call-site interni.
    def _query_paged_view(
        self,
        *,
        select_sql: str,
        order_by: str,
        params: list[Any],
        limit: int,
        offset: int,
    ) -> tuple[list[tuple], int]:
        return query_paged_view(
            select_sql=select_sql,
            order_by=order_by,
            params=params,
            limit=limit,
            offset=offset,
        )

    # Scopo: Aggiunge la condizione WHERE per scope emittente (convenzione SR:
    #        colonne <ruolo>_soggetto_ruolo_id). Delega al BB condiviso
    #        `add_emittente_scope_condition` (array risolto UNA volta in
    #        Python, non per riga — estrazione regola-del-2 dai 5 repo).
    @staticmethod
    def _add_scope_emittente(
        auth_user_id: int | None,
        field: str,
        conditions: list[str],
        params: list[Any],
    ) -> None:
        add_emittente_scope_condition(
            conditions, params,
            auth_user_id=auth_user_id,
            column=field,
            convention="sr",
        )

    # Scopo: Restituisce elenco lotti paginato con JOIN decodifica e filtri opzionali.
    # Obiettivo: lista generica fatturazione_lotti con decodifiche config.
    # Proiezione + JOIN + mapping condivisi da list_lotti e get_lotto (la testata
    # del dettaglio è la stessa riga della lista: nessuna vista/colonna nuova).
    _LOTTO_SELECT_COLS = f"""
                fl.id,
                fl.codice,
                fl.competenza_mese,
                fl.tipo_lotto,
                fl.utility_id,
                u.descrizione      AS utility_descrizione,
                fl.stato_lotto,
                fl.stato_operativo,
                fl.stato_doc_fiscale_id,
                sdf.descrizione    AS stato_doc_fiscale_descrizione,
                sdf.codice_interno AS stato_doc_fiscale_codice,
                fl.tipo_doc_fiscale_id,
                tdf.descrizione    AS tipo_doc_fiscale_descrizione,
                fl.area_geografica_id,
                agf.descrizione    AS area_geografica_descrizione,
                fl.emittente_soggetto_ruolo_id,
                fl.data_insert,
                fl.user_insert,
                s_ef.ragione_sociale_completa AS emittente_ragione_sociale,
                -- ⭐ QUANTI documenti e QUANTO valgono, sulla riga del lotto
                -- (richiesta di Tid, 2026-08-24). Prima il lotto diceva com'e'
                -- andato e non quanto pesa: per sapere se erano tre fatture o
                -- trecento bisognava aprirlo.
                -- ⚠️ Sotto-query e non JOIN + GROUP BY: un JOIN sul ponte
                -- moltiplicherebbe la riga del lotto per il numero delle sue
                -- fatture, e ogni altra colonna andrebbe aggregata a sua volta.
                -- ⚠️ `COALESCE` sulla somma e non sul conteggio: un lotto senza
                -- documenti vale ZERO euro (0 e' il totale giusto), ma
                -- `count(*)` gia' torna 0 da se'. Sul totale il COALESCE serve
                -- perche' `sum()` su zero righe da' NULL, che a video
                -- diventerebbe un trattino dove il numero c'e' ed e' zero.
                (SELECT count(*)
                   FROM vendite.fatturazione_lotti_fatture lf_c
                  WHERE lf_c.lotto_id = fl.id)                    AS n_fatture,
                (SELECT COALESCE(sum(f_t.totale_doc), 0)
                   FROM vendite.fatturazione_lotti_fatture lf_t
                   JOIN vendite.fatture f_t ON f_t.id = lf_t.fattura_id
                  WHERE lf_t.lotto_id = fl.id)                    AS totale_documenti,
                -- ⭐ «C'e' un errore grave nel dettaglio»: UN SOLO documento
                -- fallito basta ad accendere il segnale sulla riga del lotto
                -- (richiesta di Tid, 2026-08-21). E' la forma dei gestionali a
                -- lotti: la testata avvisa, il dettaglio spiega.
                -- ⚠️ EXISTS e non un COUNT: la riga di lista deve dire SE, non
                -- QUANTI — e un EXISTS si ferma al primo che trova invece di
                -- percorrere tutti i log di tutte le fatture del lotto.
                -- ⚠️ Due sorgenti come la guardia PRE-1: il ponte in ERRORE
                -- **oppure** un log critico non ritirato. Guardarne una sola
                -- lascerebbe spenta la spia proprio nei casi che l'altra copre.
                -- 📌 Costo misurato con EXPLAIN ANALYZE (2026-08-21): il
                -- pianificatore trasforma l'EXISTS interno in un SubPlan
                -- HASHATO eseguito UNA volta (`loops=1`), non per riga — 0,177
                -- ms su 46 lotti. Non e' una N+1 travestita.
                EXISTS (
                    SELECT 1
                      FROM vendite.fatturazione_lotti_fatture lf_err
                     WHERE lf_err.lotto_id = fl.id
                       AND (
                            lf_err.stato_esecuzione = 'ERRORE'
                            OR EXISTS (
                                SELECT 1
                                  FROM vendite.fatture_log fl_log
                                 WHERE fl_log.fattura_id = lf_err.fattura_id
                                   AND fl_log.status = 'C'
                                   AND fl_log.disabilitato IS FALSE
                            )
                       )
                ) AS ha_errori_gravi,
                -- ⭐ Il lotto e' stato riportato in lavorazione e il giro non ha
                -- ancora rifatto lo step (`riaperto_il` si spegne appena il
                -- runner lo onora, `azzera_riaperto_il`). Serve al FE per
                -- NOMINARE giusto la prossima esecuzione: su un lotto riaperto
                -- il prossimo run RIFA' lo step corrente e il lotto resta in
                -- DRAFT — chiamarlo «Avanza step» e rispondere «Pipeline
                -- avanzata» dice una cosa falsa (collaudo NC resi, 2026-08-22).
                -- ⚠️ Il verdetto resta del runner (`is_lotto_riaperto`): questo
                -- e' lo STESSO predicato letto per la presentazione, non una
                -- seconda regola. Se il criterio cambiasse, cambia di la'.
                (fl.riaperto_il IS NOT NULL) AS riaperto,
                -- ⭐ LA DATA DICHIARATA DEL LOTTO (BE-1, brief numerazione §4
                -- DB-4). Facoltativa: vuota = vince la politica del registro
                -- (`registri_fatturazione.politica_data_documento`), che il DB
                -- applica in `fn_calcola_data_documento` alla creazione della
                -- testata. Qui si espone il valore DICHIARATO, non quello
                -- calcolato: sono due cose diverse e mostrarle come una sola
                -- direbbe che una scelta e' stata fatta quando non lo e'.
                fl.data_documento,
                -- ⭐ LA SOGLIA DI CONGELAMENTO, presa dal CATALOGO e non da
                -- una lista di codici scritta a mano. Serve al gate dei verbi di
                -- pipeline (`useLottoAzioni.verbiPipeline`), che finora leggeva
                -- `stato_doc_fiscale_codice !== 'DRAFT'`: era l'ennesima copia
                -- della soglia che `D33` ha portato a leggere
                -- `config.stati_doc_fiscale.congela_fiscale`, e l'ultima copia
                -- fuori dal database e' gia' stata tolta dallo stesso file Vue
                -- il 2026-08-31 (F5), per lo stesso motivo: una copia in un
                -- template il DB non la vede, e il giorno che il confine si
                -- sposta non fallisce — propone un verbo che verra' rifiutato.
                -- ⚠️ Il JOIN c'e' gia' (`sdf`): e' una colonna in piu' sulla
                -- stessa riga, non un accesso nuovo.
                -- ⚠️ In coda alla proiezione DI PROPOSITO: il mapper e'
                -- posizionale e un indice sbagliato non fallisce, legge la
                -- colonna accanto (difetto reale del 2026-08-25 su `riaperto`).
                -- Inserirla in mezzo rinumererebbe 24 posizioni per ottenere una
                -- lettura piu' bella.
                sdf.congela_fiscale AS stato_congela_fiscale,
                -- ⭐ QUANTI DOCUMENTI IL LOTTO HA PRESO IN CARICO E QUANTI SONO
                -- ANDATI A BUON FINE (richiesta di Tid, 2026-09-12). Fino a
                -- quel giorno la riga di lista diceva solo `n_fatture`, e i
                -- presi in carico si vedevano SOLO nel drawer: un lotto in
                -- `ERRORE` con zero fatture non diceva «zero su due».
                -- ⛔ NON e' `n_fatture` diviso per i presi in carico, ed e' la
                -- scelta che sembra ovvia: le fatture SPARISCONO con l'annullo
                -- (il ponte viene cancellato, gli esiti restano) e possono
                -- essere MENO dei presi in carico anche a giro riuscito —
                -- `fn_build_fattura_key` fonde piu' gruppi in un documento.
                -- Misurato sui lotti dal 07-09: 10 lotti con «fatture < presi»
                -- e tutti gli esiti COMPLETED. Quel rapporto direbbe anomalia
                -- su ogni lotto annullato e su ogni fusione.
                -- ⇒ Si contano gli ESITI, che sono il fatto: `presi` = righe di
                -- `fatturazione_lotti_esiti` non `ESCLUSO` (l'operatore ha
                -- dichiarato che quel documento e' uscito dal giro — stesso
                -- criterio di `documenti_presi_in_carico_count` nel riepilogo),
                -- `completati` = esiti `COMPLETED`. Il client mostra il
                -- rapporto SOLO quando differiscono.
                -- ⚠️ Sotto-query come le due sorelle qui sopra, per la stessa
                -- ragione: un JOIN sugli esiti moltiplicherebbe la riga.
                -- ⚠️ In coda alla proiezione, come impone il mapper posizionale.
                (SELECT count(*)
                   FROM vendite.fatturazione_lotti_esiti e_p
                  WHERE e_p.lotto_id = fl.id
                    AND e_p.stato_esecuzione <> '{STATO_ESECUZIONE_ESCLUSO}') AS n_presi_in_carico,
                (SELECT count(*)
                   FROM vendite.fatturazione_lotti_esiti e_c
                  WHERE e_c.lotto_id = fl.id
                    AND e_c.stato_esecuzione = '{STATO_ESECUZIONE_COMPLETED}') AS n_esiti_completati,
                -- ⭐ La PK dell'emittente (2026-09-27, brief-db-liste-datatable-
                -- grezze): il lotto porta il SOGGETTO-RUOLO, ma le liste aperte
                -- dal suo drawer (i documenti di una fattura del lotto) passano
                -- il cancello di perimetro con `emittente_fiscale_id`, la PK.
                -- Due id diversi, non intercambiabili
                -- (feedback_emittente_pk_vs_soggetto_ruolo). ⚠️ In coda, come
                -- impone il mapper posizionale.
                ef_pk.id AS emittente_fiscale_id,
                -- ⭐ I PASSAGGI CHE L'OPERATORE PUO' FARE DA QUESTO STATO
                -- (brief-modello-documento-vendita §15.14, 2026-10-27): le
                -- `action_key` del lettore del modello, che applica il permesso
                -- della riga del passaggio. Il kebab propone un verbo di stato
                -- SOLO se compare qui: chi non ha l'azione non lo vede, come
                -- nel dettaglio (le capability leggono lo stesso lettore).
                -- ⚠️ Non e' il verdetto: le precondizioni (`fn_check_*`) le
                -- legge il click, dal dettaglio (`eseguiVerificato`).
                -- ⚠️ Lo stato e non l'id del documento: il permesso dipende
                -- dall'utente e dall'azione, e la riga lo stato ce l'ha gia'.
                -- Stato NULL -> nessuna riga -> array vuoto.
                -- ⚠️ In coda, come impone il mapper posizionale.
                ARRAY(
                    SELECT ap.action_key
                      FROM script.fn_doc_azioni_permesse(
                               '{TESTATA_LOTTI}'::regclass, fl.stato_doc_fiscale_id) ap
                     ORDER BY ap.action_key
                ) AS azioni_permesse,
                -- ⭐ SI RISTAMPA? (proposta del kebab): lo STESSO predicato con
                -- cui `ristampa_lotto` accetta o rifiuta, sulla stessa costante.
                -- La ristampa non e' un passaggio di stato (stampare e' leggere,
                -- I-4), quindi `azioni_permesse` non la porta. Prima il kebab
                -- confrontava il codice dello stato con un `'DEFINITIVA'` scritto
                -- nel frontend: una terza copia.
                -- ⚠️ In coda, come impone il mapper posizionale.
                (sdf.codice_interno = '{STATO_DEFINITIVA}') AS ristampabile
    """  # noqa: S608 — costanti di modulo STATO_ESECUZIONE_*, TESTATA_LOTTI e STATO_DEFINITIVA letterali

    _LOTTO_JOINS = f"""
            LEFT JOIN config.utilities u
                ON u.id = fl.utility_id{_LOTTI_JOIN_SDF}
            LEFT JOIN config.tipi_doc_fiscale tdf
                ON tdf.id = fl.tipo_doc_fiscale_id
            LEFT JOIN vendite.area_geografica_fatturazione agf
                ON agf.id = fl.area_geografica_id
            -- Emittente della riga (P-4, Fase E). ⚠️ Qui NON c'e' una vista da
            -- estendere: la lista nasce da SQL diretto sulla tabella, quindi
            -- la JOIN che le altre cinque liste hanno nel DB, lotti ce l'ha
            -- qui. Il dato di partenza c'e' gia' (`emittente_soggetto_ruolo_id`,
            -- NOT NULL): manca solo il nome. Stessa catena delle sei viste
            -- documento — soggetto_ruolo -> soggetto.
            LEFT JOIN anagrafiche.soggetti_ruoli sr_ef
                ON sr_ef.id = fl.emittente_soggetto_ruolo_id
            LEFT JOIN anagrafiche.soggetti s_ef
                ON s_ef.id = sr_ef.soggetto_id
            -- La PK dall'emittente soggetto-ruolo: `soggetto_ruolo_id` e' UNIQUE
            -- su `emittenti_fiscali` (uq_emittenti_fiscali_ruolo), quindi la
            -- JOIN non moltiplica la riga e il conteggio della lista resta
            -- quello della tabella madre.
            LEFT JOIN anagrafiche.emittenti_fiscali ef_pk
                ON ef_pk.soggetto_ruolo_id = fl.emittente_soggetto_ruolo_id
    """

    # Scopo: mappa una riga (ordine di _LOTTO_SELECT_COLS) in LottoListRow.
    @staticmethod
    def _map_lotto_row(row: tuple) -> LottoListRow:
        return {
            "id": int(row[0]),
            "codice": str(row[1]),
            "competenza_mese": row[2].isoformat() if row[2] is not None else None,
            "tipo_lotto": str(row[3]),
            "utility_id": None if row[4] is None else int(row[4]),
            "utility_descrizione": row[5],
            "stato_lotto": str(row[6]),
            "stato_operativo": str(row[7]),
            "stato_doc_fiscale_id": None if row[8] is None else int(row[8]),
            "stato_doc_fiscale_descrizione": row[9],
            "stato_doc_fiscale_codice": row[10],
            "tipo_doc_fiscale_id": int(row[11]),
            "tipo_doc_fiscale_descrizione": row[12],
            "area_geografica_id": None if row[13] is None else int(row[13]),
            "area_geografica_descrizione": row[14],
            "emittente_soggetto_ruolo_id": None if row[15] is None else int(row[15]),
            "data_insert": row[16].isoformat() if row[16] is not None else None,
            "user_insert": str(row[17]),
            # ⛔ La chiave DEVE restare `emittente_ragione_sociale`: e' il
            # `campo_sorgente` dichiarato a catalogo (riga 483 di
            # `lista_colonna.csv`). Se diverge, la colonna si spunta e resta
            # vuota — cioe' SEMBRA la garanzia che il flag `multi_emittente`
            # pretende, senza esserlo.
            "emittente_ragione_sociale": row[18],
            "n_fatture": int(row[19]),
            # ⚠️ Stringa e non float, come ogni importo che esce da qui: un
            # totale fiscale non passa da un binario a virgola mobile.
            "totale_documenti": str(row[20]),
            "ha_errori_gravi": bool(row[21]),
            # ⛔ ERA `bool(row[20])`, cioe' `totale_documenti`, corretto il
            #    2026-08-25. L'indice sbagliato non dava nessun errore: leggeva
            #    un NUMERIC e lo passava a `bool()`, quindi il flag valeva
            #    «questo lotto ha un totale diverso da zero». Misurato sui dati
            #    veri prima di correggere, ed era INVERTITO sul caso che conta:
            #    il lotto 6034 e' riaperto e vale 0 -> diceva `false`; i lotti
            #    7132/7133/7515/4213 non sono riaperti e valgono qualcosa ->
            #    dicevano `true`.
            # ⚠️ E' esattamente il difetto che il commento della colonna dice di
            #    voler impedire: su un lotto riaperto il prossimo giro RIFA' lo
            #    step, e chiamarlo «Avanza step» dice una cosa falsa.
            "riaperto": bool(row[22]),
            "data_documento": row[23].isoformat() if row[23] is not None else None,
            # ⚠️ `None` conservato e non appiattito a `False`: il JOIN sullo
            # stato e' LEFT (un lotto senza stato resta una riga), e «non lo so»
            # non e' «non congela». Il gate FE e' fail-closed su questo campo.
            "stato_congela_fiscale": None if row[24] is None else bool(row[24]),
            # I due conteggi degli ESITI (2026-09-12): quanti presi in carico e
            # quanti andati a buon fine. Zero e zero su un lotto senza esiti
            # (giri precedenti al 07-09): il client non mostra niente.
            "n_presi_in_carico": int(row[25]),
            "n_esiti_completati": int(row[26]),
            "emittente_fiscale_id": None if row[27] is None else int(row[27]),
            # Mai `None`: `ARRAY(subquery)` senza righe e' l'array vuoto.
            "azioni_permesse": list(row[28]),
            # Lotto senza stato (LEFT JOIN vuoto): NULL -> non si ristampa.
            "ristampabile": row[29] is True,
        }

    # Colonne ordinabili della lista lotti: chiave esposta al FE -> espressione
    # SQL. Whitelist: nell'ORDER BY entrano solo chiavi note piu' la direzione
    # ASC/DESC, mai input utente grezzo. Stessa convenzione di
    # DASH_APERTO_SORT_COLUMNS e di `_ORDER_COLS_CONTRATTI`.
    #
    # ⚠️ La chiave e' il `campo_sorgente` del catalogo, NON il `codice` logico.
    # `<ListaConfigurabile>` monta le Column con `:field="col.campo_sorgente"`,
    # quindi `event.sortField` — e con esso `store.filters.order_by` — porta il
    # nome FISICO. Chiavare sui codici logici farebbe fallire con 400 proprio le
    # colonne in cui i due nomi divergono (`utility` vs `utility_descrizione`).
    #
    # Deve restare allineata al catalogo `vendite.lotti`: una colonna marcata
    # `ordinabile = t` nel seed ma assente qui mostra una freccia che non ordina;
    # il contrario lascia inutilizzabile una colonna ordinabile. `azioni` non c'e'
    # per costruzione (tipo_colonna='azione', nessun campo_sorgente).
    LOTTI_SORT_COLUMNS = {
        "codice": "fl.codice",
        "competenza_mese": "fl.competenza_mese",
        "tipo_lotto": "fl.tipo_lotto",
        "tipo_doc_fiscale_descrizione": "tdf.descrizione",
        "utility_descrizione": "u.descrizione",
        "area_geografica_descrizione": "agf.descrizione",
        "stato_lotto": "fl.stato_lotto",
        "stato_operativo": "fl.stato_operativo",
        "stato_doc_fiscale_descrizione": "sdf.descrizione",
        "data_insert": "fl.data_insert",
        "user_insert": "fl.user_insert",
        # ⭐ La data documento DICHIARATA sul lotto. Entra qui perche' il seed
        # della colonna la dichiara `ordinabile = t`: senza questa voce la
        # freccia a video risponderebbe 400 — ed e' lo stesso difetto che il
        # 2026-08-25 ha colpito la lista resi con `fase`/`pratica_numero`,
        # trovato dal presidio del seed e non a occhio.
        # ⚠️ La CHIAVE e' il `campo_sorgente` del catalogo, non il `codice`
        # logico: qui i due coincidono, ma e' proprio dove divergono che quel
        # difetto nasce (`pratica` vs `pratica_numero`).
        "data_documento": "fl.data_documento",
        # ⭐ Quanti documenti e quanto valgono (colonne accese dal team DB il
        # 2026-08-24). ⚠️ Il VALORE è la sotto-query per intero, non l'alias di
        # SELECT: l'`ORDER BY` gira su una query con JOIN e un alias qui
        # sarebbe ambiguo. La CHIAVE resta il `campo_sorgente` del catalogo.
        "n_fatture": (
            "(SELECT count(*) FROM vendite.fatturazione_lotti_fatture lf_o"
            "  WHERE lf_o.lotto_id = fl.id)"
        ),
        "totale_documenti": (
            "(SELECT COALESCE(sum(f_o.totale_doc), 0)"
            "   FROM vendite.fatturazione_lotti_fatture lf_o2"
            "   JOIN vendite.fatture f_o ON f_o.id = lf_o2.fattura_id"
            "  WHERE lf_o2.lotto_id = fl.id)"
        ),
        # Emittente (Fase E). ⚠️ Il VALORE e' l'espressione SQL, non l'alias:
        # in questa whitelist le altre voci sono qualificate (`fl.codice`,
        # `tdf.descrizione`) perche' l'ORDER BY gira su una query con JOIN, e
        # un alias di SELECT qui sarebbe ambiguo con la colonna omonima del
        # soggetto. La CHIAVE resta il `campo_sorgente` del catalogo.
        "emittente_ragione_sociale": "s_ef.ragione_sociale_completa",
    }

    # Scopo: Costruisce il `WHERE` (clausola + parametri) della lista lotti —
    #        la SOLA sede del perimetro, condivisa da lista, conteggio totale e
    #        breakdown per stato.
    # Obiettivo: che le tre query non possano descrivere insiemi diversi.
    # Perimetro: pura, nessun I/O.
    # Risultato: tuple (clausola WHERE gia' composta o stringa vuota, params).
    #
    # ⛔ Estratta il 2026-09-03 e NON per togliere righe: api.md §«Il `count`
    #    non si deriva mai dalle righe» chiede di **condividere** il frammento
    #    `FROM`+`WHERE` fra la query dei dati e quella che conta, non di
    #    riscriverlo. Con i chip per stato le query diventano tre, e tre copie
    #    di un perimetro divergono al primo filtro aggiunto — in silenzio, con i
    #    numeri dei chip che smettono di tornare con la lista sotto.
    #
    # ⭐ `includi_stato=False` serve ai chip, ed e' la ragione per cui il flag
    #    esiste invece di un secondo costruttore: il breakdown deve contare il
    #    perimetro SENZA il filtro che i chip stessi pilotano. Contandolo
    #    dentro, scelto «BOZZA» gli altri stati andrebbero a 0, i loro chip
    #    sparirebbero (si rendono solo sopra zero) e non ci sarebbe piu' modo di
    #    tornare indietro con un click — lo stesso interruttore tolto dalle card
    #    della Lente Competenza. Gli altri filtri (mese, recuperi, utility…)
    #    restano: sono il contesto, non l'asse dei chip.
    #
    # ⭐ `annullati` (2026-09-12, decisione di Tid): un lotto il cui stato
    #    fiscale e' ABORTITO (`config.stati_doc_fiscale.is_abortito`, oggi
    #    `ANNULLATA`) e' un guscio — l'annullo e' un rollback che cancella le
    #    fatture, rimette le attivita' «da emettere» e chiude i task run — e
    #    NON e' lavoro: di default sta FUORI dal perimetro, come le archiviate
    #    delle code. ⚠️ Ed e' peggio che rumore: i chip sono per `stato_lotto`
    #    (operativo), che l'annullo di proposito non tocca (rev 2026-09-07), quindi
    #    un lotto annullato restava sotto «Errore» o «Completato» — un chip «3
    #    Errore» in cui uno e' un errore gia' disfatto. ⛔ Il criterio e' il FLAG
    #    di catalogo, mai `codice_interno = 'ANNULLATA'`: il vocabolario e' del
    #    database. Tre valori, perche' il conteggio di cio' che resta fuori
    #    (`count_lotti_annullati`) vuole il perimetro ROVESCIATO sulla sola
    #    condizione dell'abortito e identico su tutto il resto.
    def _lotti_where(
        self,
        *,
        competenza_mese: date | None,
        utility_id: int | None,
        stato_lotto: str | None,
        area_geografica_id: int | None,
        tipo_doc_fiscale_id: int | None,
        emittente_soggetto_ruolo_id: int | None,
        auth_user_id: int | None,
        solo_recuperi_mese: bool,
        includi_stato: bool = True,
        annullati: str = LOTTI_ANNULLATI_ESCLUSI,
    ) -> tuple[str, list[Any]]:
        conditions, params = self._lotti_conditions(
            competenza_mese=competenza_mese,
            utility_id=utility_id,
            stato_lotto=stato_lotto,
            area_geografica_id=area_geografica_id,
            tipo_doc_fiscale_id=tipo_doc_fiscale_id,
            emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
            auth_user_id=auth_user_id,
            solo_recuperi_mese=solo_recuperi_mese,
            includi_stato=includi_stato,
            annullati=annullati,
        )
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        return where_clause, params

    # Scopo: le condizioni del perimetro lotti, ancora SEPARATE: servono cosi'
    #        a `conta_con_perimetro`, che le vuole a pezzi. `_lotti_where` e' il
    #        suo involucro, e non esiste una terza sede.
    def _lotti_conditions(
        self,
        *,
        competenza_mese: date | None,
        utility_id: int | None,
        stato_lotto: str | None,
        area_geografica_id: int | None,
        tipo_doc_fiscale_id: int | None,
        emittente_soggetto_ruolo_id: int | None,
        auth_user_id: int | None,
        solo_recuperi_mese: bool,
        includi_stato: bool = True,
        annullati: str = LOTTI_ANNULLATI_ESCLUSI,
    ) -> tuple[list[str], list[Any]]:
        conditions: list[str] = []
        params: list[Any] = []
        cond_annullati = _condizione_annullati(annullati)
        if cond_annullati is not None:
            conditions.append(cond_annullati)

        # Costruzione WHERE dinamica; ogni filtro è parametrizzato.
        # ⭐ LA SCHEDA «RECUPERI DEL MESE» E' QUESTA STESSA LISTA con UNA
        #    condizione diversa: i lotti di competenza PRECEDENTE che hanno
        #    emesso documenti NEL mese filtrato. Colonne, decodifiche, whitelist
        #    di ordinamento e seed restano gli stessi — quindi le due schede
        #    mostrano le stesse informazioni e permettono le stesse azioni **per
        #    costruzione**. Una seconda lista scritta a parte divergerebbe al
        #    primo ritocco.
        #
        # ⚠️ Il caso che la motiva: una commessa di competenza GIUGNO fatturata
        #    ad AGOSTO produce un documento con data agosto dentro un lotto di
        #    giugno. Chi lavora sul mese di agosto non lo trova, perche' lo
        #    cerca — giustamente — per la data del documento e non per la
        #    competenza della commessa.
        if solo_recuperi_mese:
            conditions.append("fl.competenza_mese < %s")
            params.append(competenza_mese)
            conditions.append(
                """
                EXISTS (
                    SELECT 1
                      FROM vendite.fatturazione_lotti_fatture lf_r
                      JOIN vendite.fatture f_r ON f_r.id = lf_r.fattura_id
                     WHERE lf_r.lotto_id = fl.id
                       AND date_trunc('month', f_r.data)::date = %s
                )
                """
            )
            params.append(competenza_mese)
        elif competenza_mese is not None:
            conditions.append("fl.competenza_mese = %s")
            params.append(competenza_mese)
        if utility_id is not None:
            conditions.append("fl.utility_id = %s")
            params.append(utility_id)
        if includi_stato and stato_lotto is not None:
            conditions.append("fl.stato_lotto = %s")
            params.append(stato_lotto)
        if area_geografica_id is not None:
            conditions.append("fl.area_geografica_id = %s")
            params.append(area_geografica_id)
        if tipo_doc_fiscale_id is not None:
            conditions.append("fl.tipo_doc_fiscale_id = %s")
            params.append(tipo_doc_fiscale_id)
        if emittente_soggetto_ruolo_id is not None:
            conditions.append("fl.emittente_soggetto_ruolo_id = %s")
            params.append(emittente_soggetto_ruolo_id)

        self._add_scope_emittente(
            auth_user_id, "fl.emittente_soggetto_ruolo_id", conditions, params
        )
        return conditions, params

    # Scopo: QUANTI lotti annullati il perimetro della lista sta NASCONDENDO.
    # Obiettivo: che «mese pulito» e «tre lotti annullati» non si leggano
    #            uguali: il numero va accanto all'interruttore che li mostra.
    # Perimetro: STESSO della lista — mese, recuperi, stato, utility, scope —
    #            con la sola condizione dell'abortito rovesciata. Sola lettura.
    # Risultato: int.
    #
    # ⛔ Non e' derivabile dalla lista: quelle righe il suo `WHERE` le ha gia'
    #    escluse. E' il caso per cui esiste il BB `conta_con_perimetro`
    #    (archiviate delle code, ritirate del giornale): una valutazione sua,
    #    sul frammento `FROM` + condizioni che la lista possiede.
    def count_lotti_annullati(
        self,
        *,
        competenza_mese: date | None,
        utility_id: int | None = None,
        stato_lotto: str | None = None,
        area_geografica_id: int | None = None,
        tipo_doc_fiscale_id: int | None = None,
        emittente_soggetto_ruolo_id: int | None = None,
        auth_user_id: int | None = None,
        solo_recuperi_mese: bool = False,
    ) -> int:
        conditions, params = self._lotti_conditions(
            competenza_mese=competenza_mese,
            utility_id=utility_id,
            stato_lotto=stato_lotto,
            area_geografica_id=area_geografica_id,
            tipo_doc_fiscale_id=tipo_doc_fiscale_id,
            emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
            auth_user_id=auth_user_id,
            solo_recuperi_mese=solo_recuperi_mese,
            annullati=LOTTI_ANNULLATI_SOLO,
        )
        return conta_con_perimetro(
            f"FROM vendite.fatturazione_lotti fl {self._LOTTO_JOINS}",
            conditions,
            params,
        )

    # Scopo: Conteggio lotti RAGGRUPPATI PER STATO sul perimetro della lista —
    #        alimenta i pulsanti-filtro «5 Bozza · 4 In esecuzione …» del
    #        registro lotti (stesso pattern dei chip per area della Lente
    #        Backlog).
    # Obiettivo: dare all'operatore, prima di filtrare, la ripartizione di cio'
    #            che sta guardando.
    # Perimetro: sola lettura; STESSO `WHERE` della lista — mese e
    #            `recuperi_mese` compresi, filtro stato escluso (vedi
    #            `_lotti_where`). Scope emittente identico (RLS + whitelist).
    # Risultato: dict {stato_lotto: n_lotti}, solo stati presenti.
    #
    # ⛔ Non e' derivabile a valle dalle righe consegnate: la lista e' PAGINATA,
    #    quindi contare i `results` darebbe la ripartizione della pagina e non
    #    del mese. E' la stessa forma che api.md vieta per il `count` — un
    #    numero derivato dalle righe non dice niente sulle righe.
    #
    # ⚠️ Le JOIN restano anche se il `WHERE` non le usa: oggi sono tutte LEFT e
    #    non possono togliere righe, ma il giorno in cui una diventasse INNER
    #    per una decodifica la lista si accorcerebbe e i chip no — e la
    #    differenza si vedrebbe solo come due numeri che non tornano. Il costo
    #    e' cinque LEFT JOIN su FK indicizzate; la divergenza silenziosa no.
    def count_lotti_per_stato(
        self,
        *,
        competenza_mese: date | None,
        utility_id: int | None = None,
        area_geografica_id: int | None = None,
        tipo_doc_fiscale_id: int | None = None,
        emittente_soggetto_ruolo_id: int | None = None,
        auth_user_id: int | None = None,
        solo_recuperi_mese: bool = False,
        includi_annullati: bool = False,
    ) -> dict[str, int]:
        where_clause, params = self._lotti_where(
            competenza_mese=competenza_mese,
            utility_id=utility_id,
            stato_lotto=None,
            area_geografica_id=area_geografica_id,
            tipo_doc_fiscale_id=tipo_doc_fiscale_id,
            emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
            auth_user_id=auth_user_id,
            solo_recuperi_mese=solo_recuperi_mese,
            includi_stato=False,
            annullati=_annullati_da_flag(includi_annullati),
        )
        sql = f"""
            SELECT fl.stato_lotto, COUNT(*)
            FROM vendite.fatturazione_lotti fl
            {self._LOTTO_JOINS}
            {where_clause}
            GROUP BY fl.stato_lotto
        """  # noqa: S608 — WHERE da _lotti_where (clausole letterali con %s), JOIN da costante _LOTTO_JOINS, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        # Uno stato NULL non e' uno stato: non ha una voce a catalogo e non
        # sarebbe filtrabile, quindi non diventa un pulsante.
        return {row[0]: int(row[1]) for row in rows if row[0] is not None}

    # Perimetro: solo lettura; nessun side-effect.
    # Risultato: tuple (lista LottoListRow, conteggio totale).
    def list_lotti(
        self,
        *,
        competenza_mese: date | None,
        utility_id: int | None,
        stato_lotto: str | None,
        area_geografica_id: int | None,
        tipo_doc_fiscale_id: int | None,
        emittente_soggetto_ruolo_id: int | None,
        auth_user_id: int | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
        max_limit: int = MAX_LIMIT,
        solo_recuperi_mese: bool = False,
        includi_annullati: bool = False,
    ) -> tuple[list[LottoListRow], int]:
        # Il cap standard (MAX_LIMIT, fonte unica in core/db/_helpers)
        # protegge la lista a video; l'export lo alza esplicitamente (fino a
        # EXPORT_MAX_ROWS + 1, per poter *rilevare* il superamento del limite
        # invece di troncare in silenzio). Resta un cap passato dal chiamante:
        # nessun percorso senza tetto.
        safe_limit, safe_offset = limiti_pagina(limit, offset, tetto=max_limit)

        where_clause, params = self._lotti_where(
            competenza_mese=competenza_mese,
            utility_id=utility_id,
            stato_lotto=stato_lotto,
            area_geografica_id=area_geografica_id,
            tipo_doc_fiscale_id=tipo_doc_fiscale_id,
            emittente_soggetto_ruolo_id=emittente_soggetto_ruolo_id,
            auth_user_id=auth_user_id,
            solo_recuperi_mese=solo_recuperi_mese,
            annullati=_annullati_da_flag(includi_annullati),
        )

        joins = self._LOTTO_JOINS

        count_sql = f"""
            SELECT COUNT(*)
            FROM vendite.fatturazione_lotti fl
            {joins}
            {where_clause}
        """  # noqa: S608 — WHERE da _lotti_where (clausole letterali con %s), JOIN da costante _LOTTO_JOINS, valori come parametri

        # ORDER BY server-side (corretto su TUTTE le pagine, non solo su quella
        # visibile): colonna dalla whitelist + direzione, con tiebreak stabile
        # su fl.id per una paginazione deterministica anche a parita' di valore.
        # order_by assente o non ammesso -> ordine storico (il piu' recente
        # prima), cioe' esattamente il comportamento precedente: la lista non
        # cambia aspetto finche' l'utente non tocca un'intestazione.
        sort_col = colonna_ordinamento(order_by, self.LOTTI_SORT_COLUMNS)
        # ⛔ Direzione risolta PRIMA del ramo (2026-09-26): il ramo storico la
        #    ignora, e un `order_dir` estraneo passava muto (il service non la
        #    valida). Il BB la rifiuta anche quando poi non la si usa.
        direction = sql_order_direction_lista(order_by, order_dir, colonne=self.LOTTI_SORT_COLUMNS)
        if sort_col is not None:
            tiebreak_dir = sql_tiebreak_direction(direction)
            order_clause = f"ORDER BY {sort_col} {direction}, fl.id {tiebreak_dir}"
        else:
            order_clause = "ORDER BY fl.data_insert DESC, fl.id DESC"

        data_sql = f"""
            SELECT {self._LOTTO_SELECT_COLS}
            FROM vendite.fatturazione_lotti fl
            {joins}
            {where_clause}
            {order_clause}
            LIMIT %s OFFSET %s
        """  # noqa: S608 — WHERE da _lotti_where (clausole letterali con %s), JOIN da costante _LOTTO_JOINS, valori come parametri; ORDER BY da whitelist LOTTI_SORT_COLUMNS + sql_order_direction

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, params + [safe_limit, safe_offset])
            rows = cursor.fetchall()

        result: list[LottoListRow] = [self._map_lotto_row(row) for row in rows]
        return result, total_count

    # Scopo: Conteggio lotti per mese di competenza di un anno (mese 1..12 → n).
    # Obiettivo: alimentare il badge per-mese della sidebar anno/mese del
    #            registro lotti (stile Lente Competenza). Fotografia completa:
    #            NESSUN filtro stato (il badge conta i lotti generati, non quelli
    #            dello stato filtrato — decisione UX). Scope emittente identico
    #            alla lista (RLS + whitelist applicativa via _add_scope_emittente).
    # Perimetro: sola lettura, nessun side-effect. Righe con competenza_mese NULL
    #            escluse dal confronto sull'anno (non sono di alcun mese).
    # ⭐ Gli ANNULLATI restano fuori come dalla lista (2026-09-12): un guscio
    #    non e' un lotto «generato» che chieda lavoro nel mese. ⚠️ Non passa da
    #    `_lotti_where` — il perimetro qui e' l'ANNO, non un mese — ma la
    #    condizione la chiede alla STESSA sede della lista
    #    (`_condizione_annullati`) e la `JOIN` su `sdf` e' la stessa costante:
    #    questo metodo non nomina nessun frammento, quindi non puo' divergere
    #    dalla lista al primo stato abortito nuovo (revisione 2026-09-12: prima
    #    ricopiava frammento e JOIN, «dichiarati» ma pur sempre due copie).
    def count_lotti_per_mese(
        self, *, anno: int, auth_user_id: int | None = None,
        includi_annullati: bool = False,
    ) -> dict[int, int]:
        conditions: list[str] = ["EXTRACT(YEAR FROM fl.competenza_mese) = %s"]
        params: list[Any] = [anno]
        cond_annullati = _condizione_annullati(_annullati_da_flag(includi_annullati))
        if cond_annullati is not None:
            conditions.append(cond_annullati)
        self._add_scope_emittente(
            auth_user_id, "fl.emittente_soggetto_ruolo_id", conditions, params
        )
        where_clause = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT EXTRACT(MONTH FROM fl.competenza_mese)::int AS mese, COUNT(*)
            FROM vendite.fatturazione_lotti fl{_LOTTI_JOIN_SDF}
            {where_clause}
            GROUP BY 1
        """  # noqa: S608 — where da frammenti interni, valori parametrizzati
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return {int(r[0]): int(r[1]) for r in cursor.fetchall()}

    # Scopo: Lotti in stato fiscale EMESSA per la competenza data → candidati
    #        alla numerazione di PERIMETRO (C-4). Query PURA (id+codice): lo
    #        `stato_doc_fiscale_id` EMESSA lo risolve+guarda il chiamante (handler,
    #        service layer), non il repo. Scope operatore via RLS — il chiamante
    #        gira sotto `operator_identity_context`, la policy
    #        `rls_fatturazione_lotti_ef_whitelist` filtra agli emittenti
    #        dell'operatore. NESSUN limite: no silent cap (i lotti EMESSA di un
    #        mese sono pochi, uno per terna emittente/tipo); il perimetro deve
    #        essere completo, non troncato.
    # Perimetro: sola lettura; nessun side-effect.
    # ⭐ L'ORDINE E' PER DATA DOCUMENTO, NON PER ID (BE-3, brief numerazione
    #    decisione 6). Il cancello di `fn_get_next_progressivo` rifiuta una data
    #    anteriore all'ultimo numero emesso sul sezionale: numerando per id di
    #    lotto, cioe' nell'ordine in cui i lotti sono NATI, un lotto piu' vecchio
    #    ma con data piu' recente prende il numero prima e blocca gli altri.
    # ⚠️ Non e' teoria: il giro del 2026-08-05 ha numerato sei lotti in un solo
    #    atto e ha comunque prodotto un'inversione (numero 2 al 21/07, numero 3
    #    al 19/06) proprio perche' ordinava per id.
    # ⚠️ `min(f.data)` delle fatture SENZA numero, non `fl.data_documento`: la
    #    data dichiarata puo' essere vuota (vince la politica del registro) e la
    #    data vera del documento e' quella che il cancello confrontera'.
    # ⛔ Il frammento NON e' scritto qui: viene da `_data_documento_sql`, perche'
    #    il dialog della numerazione legge lo STESSO valore per dire «i documenti
    #    portano oggi il ...». Due copie e il dialog racconterebbe un ordine
    #    diverso da quello con cui il giro numera davvero.
    # ⚠️ `NULLS LAST`: un lotto senza fatture da numerare non ha una data da
    #    confrontare — va in coda, non in testa.
    # ⭐ DUE PERIMETRI, e l'ordinamento vale per entrambi: anche su una selezione
    #    fatta a mano i lotti si numerano in ordine di data documento, o il
    #    cancello di sequenza rifiuta il secondo. La selezione decide QUALI, mai
    #    in che ordine.
    def list_lotti_numerabili(
        self,
        *,
        stato_doc_fiscale_id: int,
        competenza_mese: date | None = None,
        lotti_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        perimetro, par_perimetro = costruisci_perimetro_lotti_numerabili(
            lotti_alias="fl",
            stato_doc_fiscale_id=stato_doc_fiscale_id,
            competenza_mese=competenza_mese,
            lotti_ids=lotti_ids,
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT fl.id, fl.codice
                  FROM vendite.fatturazione_lotti fl
                  LEFT JOIN LATERAL (
                      {data_corrente}
                  ) d(data_doc) ON TRUE
                 WHERE {perimetro}
                 ORDER BY d.data_doc NULLS LAST, fl.id
                """.format(  # noqa: S608 — costante SQL_DATA_DOCUMENTO_CORRENTE + perimetro da costruisci_perimetro_lotti_numerabili, valori come parametri
                    data_corrente=SQL_DATA_DOCUMENTO_CORRENTE.format(lotto="fl.id"),
                    perimetro=perimetro,
                ),
                par_perimetro,
            )
            return [
                {"id": int(row[0]), "codice": row[1]}
                for row in cursor.fetchall()
            ]

    # Scopo: L'AZIENDA (ruolo dell'emittente, `emittente_soggetto_ruolo_id`)
    #        di ciascun gruppo fatturabile chiesto, per la competenza: serve a
    #        dividere un'emissione mirata in un lavoro per azienda (BE10 a di
    #        brief-db-revisione-dbops). Ritorna `{gruppo_key: [sr_id, ...]}` per
    #        le sole chiavi trovate.
    # Perimetro: sola lettura su `vw_dash_competenza_gruppi` (security_invoker):
    #        lo scope emittente lo applica la vista, quindi un gruppo fuori
    #        perimetro NON torna — per chi chiede è un gruppo che non c'è.
    # ⭐ La sorgente è quella dell'elenco «Da emettere» da cui l'operatore ha
    #    spuntato le chiavi, con lo stesso filtro di competenza
    #    (`g.competenza_mese = %s`): la risposta parla delle righe che ha visto.
    # ⚠️ Una lista e non un valore: un gruppo parzialmente fatturato sta su più
    #    righe (una per stadio, vedi la vista), e il chiamante deve poter
    #    vedere che l'azienda è UNA invece di prenderne una a caso.
    # ⛔ Solo le due colonne che servono: il costo della vista dipende da cosa le
    #    si chiede (vedi `get_dash_competenza_gruppi_accessori`).
    # ⛔ Un ruolo NULL resta nella lista come None, non si scarta né si
    #    converte: la colonna viene da una vista, e un `int(None)` sarebbe un
    #    500. Così il gruppo arriva al chiamante come «azienda non
    #    attribuibile» e diventa il suo 400 parlante.
    def aziende_dei_gruppi(
        self, *, competenza_mese: date, chiavi: Sequence[str],
    ) -> dict[str, list[int | None]]:
        if not chiavi:
            return {}
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT g.gruppo_key,
                       array_agg(DISTINCT g.emittente_soggetto_ruolo_id)
                  FROM vendite.vw_dash_competenza_gruppi g
                 WHERE g.competenza_mese = %s
                   AND g.gruppo_key = ANY(%s::text[])
                 GROUP BY g.gruppo_key
                """,
                [competenza_mese, list(chiavi)],
            )
            return {
                str(r[0]): [None if x is None else int(x) for x in r[1]]
                for r in cursor.fetchall()
            }

    # Scopo: L'AZIENDA (`emittente_soggetto_ruolo_id`) di ciascun lotto
    #        chiesto: serve a dividere «Rendi definitive» su una selezione in un
    #        lavoro per azienda (BE10 a). Ritorna `{lotto_id: sr_id}` per i soli
    #        lotti trovati.
    # Perimetro: sola lettura; la policy dei lotti filtra al perimetro di chi
    #        chiede, quindi un lotto fuori perimetro non torna.
    def aziende_dei_lotti(self, *, lotti_ids: Sequence[int]) -> dict[int, int]:
        if not lotti_ids:
            return {}
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT fl.id, fl.emittente_soggetto_ruolo_id
                  FROM vendite.fatturazione_lotti fl
                 WHERE fl.id = ANY(%s::bigint[])
                """,
                [[int(i) for i in lotti_ids]],
            )
            return {int(r[0]): int(r[1]) for r in cursor.fetchall()}

    # Scopo: Restituisce il dettaglio testata di un singolo lotto (stessa
    #        proiezione della lista), con scope emittente applicato: un lotto
    #        fuori scope torna None → il BE risponde 404 (indistinguibile da id
    #        inesistente, coerente con la RLS operatori, api.md §scope).
    # Perimetro: sola lettura; nessun side-effect.
    def get_lotto(
        self, *, lotto_id: int, auth_user_id: int | None = None,
    ) -> LottoListRow | None:
        conditions: list[str] = ["fl.id = %s"]
        params: list[Any] = [lotto_id]
        self._add_scope_emittente(
            auth_user_id, "fl.emittente_soggetto_ruolo_id", conditions, params
        )
        where_clause = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT {self._LOTTO_SELECT_COLS}
            FROM vendite.fatturazione_lotti fl
            {self._LOTTO_JOINS}
            {where_clause}
        """  # noqa: S608 — colonne/JOIN da costanti di classe, WHERE letterale + BB scope emittente, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
        if row is None:
            return None
        return self._map_lotto_row(row)

    # Scopo: Capability del lotto per il detail API (wrapper su
    #        `script.fn_available_actions_lotto`, ottava della famiglia
    #        fn_available_actions_*): `available_actions` con enabled/reasons,
    #        `can_change_state`, `stato_codice`, `tipo_lotto`.
    #        ⚠️ NESSUNO scope qui: la fn non filtra per emittente. Il cancello
    #        e' la `get_lotto` sopra (RLS + whitelist applicativa), che il
    #        service chiama PRIMA — chiamare questa su un id fuori scope
    #        risponderebbe capability di un lotto che l'operatore non vede.
    # Perimetro: sola lettura; `{}` se il lotto non esiste (fn → NULL).
    def get_available_actions_lotto(self, lotto_id: int) -> dict[str, Any]:
        return call_jsonb_fn("script.fn_available_actions_lotto", int(lotto_id))

    # Scopo: Restituisce le celle non vuote (area × fase) del serbatoio
    #        pre-commessa. Il completamento a griglia 5 aree × 3 fasi
    #        (celle vuote = zeri, DL-13) e' a carico del service — qui NON si
    #        duplica, si legge solo cio' che esiste.
    # Perimetro: sola lettura su vw_dash_aperto_riepilogo v2 (security_invoker →
    #        la RLS emittente sulle 5 aree documento filtra da sola; perimetro
    #        aperti-non-chiusi gia' nella vista, DL-15).
    # Risultato: lista piatta DashApertoRiepilogoRow (≤ 12 righe).
    def list_dash_aperto_riepilogo(self) -> list[DashApertoRiepilogoRow]:
        sql = """
            SELECT
                area,
                fase,
                n_documenti,
                valore_totale
            FROM vendite.vw_dash_aperto_riepilogo
            ORDER BY area, fase
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

        result: list[DashApertoRiepilogoRow] = []
        for row in rows:
            result.append(
                {
                    "area": str(row[0]),
                    "fase": str(row[1]),
                    "n_documenti": int(row[2]),
                    "valore_totale": str(row[3]) if row[3] is not None else None,
                }
            )
        return result

    # Scopo: Restituisce il drill-down paginato del serbatoio pre-commessa
    #        (vw_dash_aperto_documenti v2: 5 aree documento, perimetro
    #        aperti-non-chiusi lato vista), con filtri opzionali area/fase e
    #        ritardo_giorni ("aperti da oltre N giorni" su data_riferimento,
    #        DL-17). anzianita_giorni derivata in SELECT (GREATEST). Ordinamento
    #        BE-side (le viste non garantiscono ORDER): piu' vecchio prima, poi
    #        valore.
    # Perimetro: sola lettura; scope emittente interamente DB-side (RLS
    #        invoker sulle 5 aree documento). Una sola valutazione della
    #        union + clamp offset via _query_paged_view.
    # Risultato: tuple (lista DashApertoDocumentoRow, conteggio totale).
    # Colonne ordinabili del drill-down Situazione aperta: chiave esposta al FE
    # (allineata al `field` della colonna DataTable) -> colonna della CTE
    # `righe`. Whitelist: nell'ORDER BY entrano solo chiavi note + direzione
    # ASC/DESC, mai input utente grezzo (no SQL injection). Convenzione
    # order_by/order_dir come le liste standard (fn_search_soggetti_universale).
    DASH_APERTO_SORT_COLUMNS = {
        "anzianita_giorni": "anzianita_giorni",
        "codice": "codice",
        "cliente_display": "cliente_display",
        "valore_totale": "valore_totale",
        # Estese 2026-08-03 (passata BE dashboard, 8° lotto liste): `stato_codice`
        # chiude il nucleo *stato* (la lista mostra la colonna e nasceva con la
        # freccia morta); `area`/`fase` per simmetria col gemello backlog, che
        # ordina `area` da subito — stessa colonna a video, stesso comportamento.
        "area": "area",
        "fase": "fase",
        "stato_codice": "stato_codice",
        # Emittente (P-4, Fase E del brief perimetro-emittente): la riga di
        # catalogo e' `ordinabile = t`, e il presidio
        # `test_liste_configurabili_seed` lega catalogo e whitelist nei DUE
        # versi — la chiave e' il CAMPO FISICO, non il `codice` della colonna.
        "emittente_ragione_sociale": "emittente_ragione_sociale",
    }

    def list_dash_aperto_documenti(
        self,
        *,
        area: str | None,
        fase: str | None,
        ritardo_giorni: int | None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[DashApertoDocumentoRow], int]:
        conditions: list[str] = []
        params: list[Any] = []
        if area is not None:
            conditions.append("d.area = %s")
            params.append(area)
        if fase is not None:
            conditions.append("d.fase = %s")
            params.append(fase)
        # Filtro "aperti da oltre N giorni" su data documento (DL-17): soglia
        # solo sul drill-down (le card restano la fotografia completa). Costo
        # DB zero — nessuna funzione temporale sul totale delle card.
        if ritardo_giorni is not None:
            conditions.append(
                "d.data_riferimento <= (SELECT script.fn_data_operativa()) - make_interval(days => %s)"
            )
            params.append(ritardo_giorni)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        select_sql = f"""
            SELECT
                d.area,
                d.documento_id,
                d.documento_uid,
                d.codice,
                d.cliente_display,
                d.fase,
                d.stato_codice_interno,
                d.stato_codice,
                d.valore_totale,
                d.unita_totali,
                GREATEST(((SELECT script.fn_data_operativa()) - d.data_riferimento), 0) AS anzianita_giorni,
                d.motivo_fermo,
                d.data_riferimento,
                -- Emittente (P-4, Fase E). ⛔ L'alias deve restare
                -- `emittente_ragione_sociale`: e' il `campo_sorgente`
                -- del catalogo, e la lista ha `vista_sql = NULL` —
                -- il campo lo porta questo SELECT o non arriva.
                d.emittente_ragione_sociale
            FROM vendite.vw_dash_aperto_documenti d
            {where_clause}
        """  # noqa: S608 — WHERE da clausole letterali con %s, valori come parametri

        # ORDER BY server-side (corretto su TUTTE le pagine, non solo quella
        # visibile): colonna dalla whitelist DASH_APERTO_SORT_COLUMNS + direzione
        # ASC/DESC, con tiebreak stabile (area, documento_id) per paginazione
        # deterministica. order_by assente/non ammesso -> ordine storico
        # "in essere da" (i piu' vecchi prima).
        sort_col = colonna_ordinamento(order_by, self.DASH_APERTO_SORT_COLUMNS)
        if sort_col is not None:
            direction = sql_order_direction_lista(order_by, order_dir, colonne=self.DASH_APERTO_SORT_COLUMNS)
            tiebreak_dir = sql_tiebreak_direction(direction)
            order_clause = (
                f"ORDER BY {sort_col} {direction}, "
                f"area ASC, documento_id {tiebreak_dir}"
            )
        else:
            order_clause = """
            ORDER BY data_riferimento ASC NULLS LAST,
                     valore_totale DESC NULLS LAST,
                     area ASC, documento_id ASC
            """

        rows, total_count = self._query_paged_view(
            select_sql=select_sql,
            order_by=order_clause,
            params=params,
            limit=limit,
            offset=offset,
        )

        result: list[DashApertoDocumentoRow] = []
        for row in rows:
            result.append(
                {
                    "area": str(row[0]),
                    "documento_id": int(row[1]),
                    "documento_uid": None if row[2] is None else str(row[2]),
                    "codice": None if row[3] is None else str(row[3]),
                    "cliente_display": None if row[4] is None else str(row[4]),
                    "fase": None if row[5] is None else str(row[5]),
                    "stato_codice_interno": None if row[6] is None else str(row[6]),
                    "stato_codice": None if row[7] is None else str(row[7]),
                    "valore_totale": str(row[8]) if row[8] is not None else None,
                    "unita_totali": None if row[9] is None else int(row[9]),
                    "anzianita_giorni": int(row[10]),
                    "motivo_fermo": None if row[11] is None else str(row[11]),
                    "data_riferimento": (
                        row[12].isoformat() if row[12] is not None else None
                    ),
                    # Emittente (P-4, Fase E): chiave = `campo_sorgente`
                    # del catalogo, o la colonna resta vuota a video.
                    "emittente_ragione_sociale": row[13],
                }
            )
        return result, total_count

    # Scopo: Restituisce le righe non vuote (mese × stadio × stato fattura)
    #        dell'aggregata Lente 1 Competenza per un anno, in formato lungo.
    #        Il pivot ai 4 blocchi (griglia 12 mesi × 4 stadi + breakdown stato
    #        fattura) e' a carico del service — qui si legge solo cio' che esiste.
    # Perimetro: sola lettura su vw_dash_competenza_mensile (invoker + scope GUC
    #        fail-closed nel resolver attivita'). Decode etichetta stato fattura
    #        via JOIN su codice_interno (display field BE-side).
    # Risultato: lista piatta DashCompetenzaMensileRow ordinata per mese/stadio/
    #        ordine stato.
    def list_dash_competenza_mensile(self, *, anno: int) -> list[DashCompetenzaMensileRow]:
        sql = """
            SELECT
                m.competenza_mese,
                m.stadio,
                m.stato_fattura_codice_interno,
                sdf.codice          AS stato_fattura_codice,
                m.tipo_movimento,
                m.n_attivita,
                m.valore_tot,
                m.valore_fatturato_tot,
                m.n_in_ritardo,
                m.valore_in_ritardo,
                -- ⭐ La dimensione arrivata col `20260826-55`, IN CODA di
                --    proposito: le righe si leggono per POSIZIONE, quindi una
                --    colonna infilata in mezzo sposta in silenzio tutte quelle
                --    dopo — e `int(row[5])` che diventa una stringa non e' un
                --    errore di sintassi, e' un numero sbagliato a video.
                --    Serve alla card «Emesse non fatturate», che senza di lei
                --    somma DUE cose con rimedi opposti: il RESIDUO, che chiede
                --    un'azione, e il transito legittimo, su cui non si fa nulla.
                m.motivo_non_fatturata,
                -- ⭐ Le due colonne del `20260909-67`, IN CODA come la
                --    precedente e per la stessa ragione: qui si legge per
                --    POSIZIONE.
                -- ⛔ E vanno LETTE, non solo lasciate arrivare: da quel
                --    changeSet `n_attivita` ESCLUDE le attivita' trattenute da
                --    un lotto in gioco, e senza la dichiarazione il numero
                --    cala in silenzio — che e' il difetto di partenza girato
                --    di 180 gradi (la card diceva 4 dove la lista ne mostrava
                --    3; adesso direbbe 3 senza spiegare il quarto).
                m.n_attivita_trattenute,
                m.valore_trattenuto
            FROM vendite.vw_dash_competenza_mensile m
            LEFT JOIN config.stati_doc_fiscale sdf
                ON sdf.codice_interno = m.stato_fattura_codice_interno
            WHERE m.competenza_mese >= make_date(%s, 1, 1)
              AND m.competenza_mese <  (make_date(%s, 1, 1) + interval '1 year')
            ORDER BY m.competenza_mese, m.stadio,
                     sdf.ordine NULLS LAST, m.stato_fattura_codice_interno,
                     m.tipo_movimento
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [anno, anno])
            rows = cursor.fetchall()

        result: list[DashCompetenzaMensileRow] = []
        for row in rows:
            result.append(
                {
                    "competenza_mese": row[0].isoformat(),
                    "stadio": str(row[1]),
                    "stato_fattura_codice_interno": None if row[2] is None else str(row[2]),
                    "stato_fattura_codice": None if row[3] is None else str(row[3]),
                    "tipo_movimento": str(row[4]),
                    "n_attivita": int(row[5]),
                    "valore": str(row[6]) if row[6] is not None else "0",
                    "valore_fatturato": str(row[7]) if row[7] is not None else "0",
                    "n_in_ritardo": int(row[8]),
                    "valore_in_ritardo": str(row[9]) if row[9] is not None else "0",
                    "motivo_non_fatturata": None if row[10] is None else str(row[10]),
                    "n_attivita_trattenute": int(row[11]),
                    # ⚠️ Stringa e non numero: e' denaro, e un `numeric` che
                    #    passa da JSON diventa un float. Stessa regola di
                    #    `valore` qui sopra.
                    "valore_trattenuto": str(row[12]) if row[12] is not None else "0",
                }
            )
        return result

    # Scopo: Conteggio FATTURE per (mese, stadio) della Lente 1 — la seconda
    #        misura delle card, accanto alle attivita'. Serve perche' le due
    #        grane divergono di molto e in modo non intuitivo: a luglio 2026,
    #        18 gruppi fatturabili hanno prodotto 6 fatture (una ne conteneva
    #        10). Chi legge «n attivita'» come «n fatture» sbaglia sempre, e
    #        di parecchio.
    # Perimetro: parte SEMPRE da `vw_dash_competenza_attivita`, che porta con
    #        se' lo scope emittente (GUC fail-closed) e le esclusioni di
    #        dominio: una query diretta sulle tabelle dovrebbe replicarli, e
    #        prima o poi divergerebbe.
    # Risultato: tupla `(conteggi, stadi_in_errore)`.
    #        · `conteggi`: {(competenza_mese_iso, stadio): n_fatture}
    #        · `stadi_in_errore`: gli stadi il cui calcolo e' FALLITO.
    #
    # ⚠️ I due esiti «non ho un numero» NON sono lo stesso esito, ed e' il
    #    motivo per cui questo metodo ritorna due cose invece di un dict solo:
    #      · lo stadio non e' calcolabile PER PROGETTO (DA_EMETTERE: la chiave
    #        documento non esiste ancora) -> la card tace, ed e' corretto;
    #      · il calcolo doveva riuscire e si e' ROTTO -> la card deve DIRLO.
    #    Fonderli su un unico «assente» ripeterebbe, un livello piu' in la',
    #    lo stesso appiattimento che qui sotto si evita fra `None` e `0`: il
    #    guasto prenderebbe l'aspetto del comportamento normale (rilievo di
    #    Tid, 2026-08-03).
    #
    # ⚠️ DUE MISURE DI NATURA DIVERSA, deliberatamente nello stesso metodo ma
    #    con due query:
    #    · FATTURATA          -> conteggio CERTO: le fatture esistono.
    #    · EMESSA_NON_FATTURATA -> PREVISIONE, calcolata con la funzione
    #      autoritativa `fn_build_fattura_key` sulle attivita' gia' emesse
    #      (che a questo stadio esistono come `attivita_fatturabili`): non e'
    #      una stima, e' la stessa chiave che il generatore usera'. Per lo
    #      stadio DA_EMETTERE la stessa cosa NON e' possibile — quelle righe
    #      sono `commesse_attivita` senza `attivita_fatturabili`, e la chiave
    #      si calcola solo da li': riscriverla altrove sarebbe un secondo
    #      risolutore delle condizioni di pagamento (vietato, brief scadenze
    #      §8) proprio sulle dimensioni che spaccano o uniscono le fatture.
    # Stadi per cui questo metodo SA produrre un conteggio. Vive qui, accanto
    # alle due query che lo rendono vero, e non nel service: e' il service a
    # doverlo chiedere al repository, altrimenti la stessa conoscenza starebbe
    # scritta in due posti e il giorno in cui una terza query si aggiunge
    # (previsione DA_EMETTERE, quando il DB esporra' la chiave a monte) uno
    # dei due resterebbe indietro in silenzio.
    DASH_STADI_CON_CONTEGGIO_FATTURE = frozenset(
        {"FATTURATA", "EMESSA_NON_FATTURATA"}
    )

    def count_dash_competenza_fatture_mensile(
        self, *, anno: int,
    ) -> tuple[dict[tuple[str, str], int], set[str]]:
        out: dict[tuple[str, str], int] = {}
        errori: set[str] = set()

        # --- FATTURATA: dato certo, nessuna funzione, nessun rischio.
        sql_reali = """
            SELECT competenza_mese, COUNT(DISTINCT fattura_id)::integer
            FROM vendite.vw_dash_competenza_attivita
            WHERE stadio = 'FATTURATA' AND fattura_id IS NOT NULL
              AND competenza_mese >= make_date(%s, 1, 1)
              AND competenza_mese <  (make_date(%s, 1, 1) + interval '1 year')
            GROUP BY competenza_mese
        """
        with connection.cursor() as cursor:
            cursor.execute(sql_reali, [anno, anno])
            for row in cursor.fetchall():
                out[(row[0].isoformat(), "FATTURATA")] = int(row[1])

        # --- EMESSA_NON_FATTURATA: previsione esatta, ma BEST-EFFORT.
        # `fn_build_fattura_key` e' VOLATILE (chiamata per riga) e SOLLEVA su
        # attivita' con chiave incompleta (BA mancante). Su un cruscotto —
        # la prima schermata che l'operatore apre — una singola riga
        # malformata renderebbe illeggibile l'INTERA pagina: sarebbe un
        # fail-closed nel posto sbagliato. Savepoint isolato: se salta,
        # si perde una misura secondaria, non il cruscotto.
        sql_previste = """
            SELECT v.competenza_mese,
                   COUNT(DISTINCT vendite.fn_build_fattura_key(af.id))::integer
            FROM vendite.vw_dash_competenza_attivita v
            JOIN vendite.attivita_fatturabili af
              ON af.commessa_attivita_id = v.commessa_attivita_id
            WHERE v.stadio = 'EMESSA_NON_FATTURATA'
              AND v.competenza_mese >= make_date(%s, 1, 1)
              AND v.competenza_mese <  (make_date(%s, 1, 1) + interval '1 year')
            GROUP BY v.competenza_mese
        """
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(sql_previste, [anno, anno])
                    for row in cursor.fetchall():
                        out[(row[0].isoformat(), "EMESSA_NON_FATTURATA")] = int(row[1])
        except DatabaseError as exc:
            # Lo stadio entra in `errori`: il service lo tradurra' in uno stato
            # ESPLICITO verso il FE, che mostrera' un avvertimento invece di
            # tacere come fa sugli stadi non calcolabili per progetto.
            errori.add("EMESSA_NON_FATTURATA")
            # Traccia a DB oltre che nel file di log: un warning che vive solo
            # in un file rotante sul server e' una ricevuta che nessuno ritira.
            ErrorManager.log_error_only(
                code="E_VENDITE_DASH_PREVISIONE_FATTURE_FALLITA",
                context={
                    "anno": anno,
                    "stadio": "EMESSA_NON_FATTURATA",
                    "errore": str(exc)[:500],
                },
                area="vendite",
                function_name=(
                    "vendite.VenditeRepository."
                    "count_dash_competenza_fatture_mensile"
                ),
            )
            logger.warning(
                "Previsione fatture EMESSA_NON_FATTURATA non calcolabile "
                "(anno=%s): la card lo segnalera' all'operatore.",
                anno, exc_info=True,
            )

        return out, errori

    # Scopo: Restituisce il conteggio errori vivi (blocco 4 Lente 1) per mese
    #        di competenza di un anno — alimenta il semaforo/badge mensile
    #        senza caricare l'intera lista errori.
    # Perimetro: sola lettura su vw_dash_competenza_errori (scope GUC in vista).
    #        Il bucket mensile e' normalizzato con date_trunc: a differenza di
    #        commesse_attivita, fatturazione_lotti.competenza_mese NON ha un
    #        CHECK primo-del-mese, e una chiave a meta' mese non matcherebbe
    #        mai la griglia del service (errore invisibile).
    # Risultato: dict {competenza_mese_iso: n_errori} dei soli mesi con errori.
    def count_dash_competenza_errori_mensile(self, *, anno: int) -> dict[str, int]:
        sql = """
            SELECT date_trunc('month', competenza_mese)::date AS mese,
                   COUNT(*)::integer
            FROM vendite.vw_dash_competenza_errori
            WHERE competenza_mese >= make_date(%s, 1, 1)
              AND competenza_mese <  (make_date(%s, 1, 1) + interval '1 year')
            GROUP BY 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [anno, anno])
            rows = cursor.fetchall()
        return {row[0].isoformat(): int(row[1]) for row in rows}

    # Scopo: Restituisce il drill-down paginato delle attivita' di un mese di
    #        competenza (Lente 1, grana attivita'), con filtro opzionale per
    #        stadio del funnel e per recuperi tardivi.
    # Perimetro: sola lettura su vw_dash_competenza_attivita (scope GUC
    #        fail-closed in vista); decode articolo via JOIN (display field).
    # Risultato: tuple (lista DashCompetenzaAttivitaRow, conteggio totale).
    # Colonne ordinabili del drill-down attivita' Lente 1 Competenza: chiave FE
    # (field colonna DataTable) -> espressione SQL. Note: la cella "articolo"
    # mostra la descrizione (fallback codice) -> si ordina per il valore
    # mostrato; la data si ordina per la COLONNA data (non la stringa gg/mm/aaaa
    # del FE). Whitelist: nell'ORDER BY solo chiavi note + ASC/DESC (no injection).
    # NB: nomi di OUTPUT della SELECT (senza alias di tabella): l'ORDER BY di
    # `query_paged_view` si applica alla CTE `righe`, non alle tabelle sorgente.
    DASH_COMPETENZA_ATTIVITA_SORT_COLUMNS = {
        "commessa_codice": "commessa_codice",
        "cliente_display": "cliente_display",
        "articolo_codice": "COALESCE(articolo_descrizione, articolo_codice)",
        "data_attivita": "data_attivita",
        "valore": "valore",
    }

    def list_dash_competenza_attivita(
        self,
        *,
        competenza_mese: date,
        stadio: str | None,
        solo_ritardo: bool,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[DashCompetenzaAttivitaRow], int]:
        conditions: list[str] = ["a.competenza_mese = %s"]
        params: list[Any] = [competenza_mese]
        if stadio is not None:
            conditions.append("a.stadio = %s")
            params.append(stadio)
        if solo_ritardo:
            conditions.append("a.emessa_in_ritardo IS TRUE")

        where_clause = "WHERE " + " AND ".join(conditions)

        # ORDER BY server-side (corretto su TUTTE le pagine): colonna dalla
        # whitelist + direzione ASC/DESC, tiebreak stabile (commessa,
        # commessa_attivita_id). order_by assente/non ammesso -> default storico
        # (valore DESC).
        sort_col = colonna_ordinamento(order_by, self.DASH_COMPETENZA_ATTIVITA_SORT_COLUMNS)
        # Direzione risolta PRIMA del ramo: il default (valore DESC) deve
        # avere il tiebreak coerente quanto la colonna scelta dall'utente.
        # `commessa_codice` raggruppa (resta ASC), `commessa_attivita_id` e' la
        # chiave tecnica univoca e segue la direzione (2026-08-03).
        direction = sql_order_direction_lista(
            order_by, order_dir, colonne=self.DASH_COMPETENZA_ATTIVITA_SORT_COLUMNS, default_desc=True,
        )
        tiebreak_dir = sql_tiebreak_direction(direction)
        tiebreak = f"commessa_codice ASC, commessa_attivita_id {tiebreak_dir}"
        if sort_col is not None:
            order_clause = f"ORDER BY {sort_col} {direction}, {tiebreak}"
        else:
            order_clause = f"ORDER BY valore DESC NULLS LAST, {tiebreak}"

        select_sql = f"""
            SELECT
                a.commessa_attivita_id,
                a.commessa_id,
                a.commessa_codice,
                a.cliente_display,
                a.articolo_id,
                art.codice          AS articolo_codice,
                art.descrizione     AS articolo_descrizione,
                a.data_attivita,
                a.quantita,
                a.stadio,
                a.stato_approvazione,
                a.stato_emissione,
                a.valore,
                a.data_emissione,
                a.emessa_in_ritardo,
                a.sospesa,
                a.posticipa_al,
                a.fattura_id,
                a.fattura_anno,
                a.fattura_serie,
                a.fattura_numero,
                a.lotto_id,
                a.stato_fattura_codice_interno,
                a.stato_fattura_codice,
                a.valore_fatturato,
                a.fattura_critical
            FROM vendite.vw_dash_competenza_attivita a
            LEFT JOIN catalogo.articoli art
                ON art.id = a.articolo_id
            {where_clause}
        """  # noqa: S608 — WHERE da clausole letterali con %s, valori come parametri

        # Una sola valutazione della vista (CTE materializzata + COUNT(*) OVER)
        # con CLAMP dell'offset all'ultima pagina reale, come le altre liste dei
        # cruscotti: il service dichiara poi la pagina effettiva nell'envelope.
        rows, total_count = self._query_paged_view(
            select_sql=select_sql,
            order_by=order_clause,
            params=params,
            limit=limit,
            offset=offset,
        )

        result: list[DashCompetenzaAttivitaRow] = []
        for row in rows:
            result.append(
                {
                    "commessa_attivita_id": int(row[0]),
                    "commessa_id": int(row[1]),
                    "commessa_codice": None if row[2] is None else str(row[2]),
                    "cliente_display": None if row[3] is None else str(row[3]),
                    "articolo_id": None if row[4] is None else str(row[4]),
                    "articolo_codice": None if row[5] is None else str(row[5]),
                    "articolo_descrizione": None if row[6] is None else str(row[6]),
                    "data_attivita": row[7].isoformat() if row[7] is not None else None,
                    "quantita": str(row[8]) if row[8] is not None else None,
                    "stadio": str(row[9]),
                    "stato_approvazione": None if row[10] is None else str(row[10]),
                    "stato_emissione": None if row[11] is None else str(row[11]),
                    "valore": str(row[12]) if row[12] is not None else None,
                    "data_emissione": row[13].isoformat() if row[13] is not None else None,
                    "emessa_in_ritardo": None if row[14] is None else bool(row[14]),
                    "sospesa": None if row[15] is None else bool(row[15]),
                    "posticipa_al": row[16].isoformat() if row[16] is not None else None,
                    "fattura_id": None if row[17] is None else int(row[17]),
                    "fattura_anno": None if row[18] is None else int(row[18]),
                    "fattura_serie": None if row[19] is None else str(row[19]),
                    "fattura_numero": None if row[20] is None else int(row[20]),
                    "lotto_id": None if row[21] is None else int(row[21]),
                    "stato_fattura_codice_interno": None if row[22] is None else str(row[22]),
                    "stato_fattura_codice": None if row[23] is None else str(row[23]),
                    "valore_fatturato": str(row[24]) if row[24] is not None else None,
                    "fattura_critical": bool(row[25]),
                }
            )
        return result, total_count

    # Colonne ordinabili della lista dei RESIDUI (`ui.lista_definizione` 49).
    # ⚠️ Le chiavi sono i `campo_sorgente` del catalogo, non i `codice` delle
    # colonne: due divergono (`articolo` -> `articolo_codice`,
    # `lotto_provenienza` -> `lotto_provenienza_codice`) e il presidio
    # `apps/core/tests/test_liste_configurabili_seed.py` lega catalogo e
    # whitelist nei DUE versi — una colonna `ordinabile = t` fuori whitelist fa
    # rosso (la freccia a video risponderebbe 400) e una in whitelist marcata
    # `ordinabile = f` fa rosso pure lei.
    DASH_COMPETENZA_RESIDUI_SORT_COLUMNS = {
        "commessa_codice": "commessa_codice",
        "cliente_display": "cliente_display",
        "articolo_codice": "articolo_codice",
        "articolo_descrizione": "articolo_descrizione",
        "competenza_mese": "competenza_mese",
        "data_attivita": "data_attivita",
        "valore": "valore",
        "lotto_provenienza_codice": "lotto_provenienza_codice",
        "motivo_non_fatturata": "motivo_non_fatturata",
        "emittente_ragione_sociale": "emittente_ragione_sociale",
    }

    # Scopo: Elenco dei RESIDUI di un mese di competenza — le attivita' che una
    #        fattura non ce l'hanno piu' e che nessun giro riprendera' da solo.
    #        E' l'oggetto del verbo «Riporta da emettere»: la lista esiste
    #        perche' il verbo agisce per riga, e l'operatore deve vedere COSA
    #        sta riportando.
    # Perimetro: sola lettura su `vw_dash_competenza_attivita`, che e'
    #        `security_invoker` e fail-closed senza GUC operatore. Lo scope non
    #        si aggiunge qui: sta gia' nella vista, sul JOIN con
    #        `vendite.commesse_attivita` — `vendite.attivita_fatturabili` NON ha
    #        row level security, quindi leggerla da sola sarebbe fail-open.
    # Risultato: tuple (righe, conteggio totale).
    def list_dash_competenza_residui(
        self,
        *,
        competenza_mese: date,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[DashCompetenzaResiduoRow], int]:
        # ⛔ IL PERIMETRO E' `motivo_non_fatturata = 'RESIDUO'`, e non e' un
        #    filtro di comodo: lo stadio `EMESSA_NON_FATTURATA` contiene TRE
        #    situazioni con rimedi diversi, e solo questa chiede un'azione. Le
        #    altre due — `GIRO_IN_CORSO`,
        #    `SENZA_ATTIVITA_FATTURABILE` — sono «niente da fare», e proporre il
        #    verbo su di loro significherebbe disfare emissioni corrette oppure
        #    (l'ultima) offrirlo su una riga la cui chiave e' NULL.
        #    Il discriminante lo calcola la VISTA, che lo ricava con lo stesso
        #    `IS DISTINCT FROM` di `script.fn_check_attivita_riportabile_da_emettere`:
        #    ricalcolarlo qui sarebbe una seconda implementazione, e la
        #    divergenza sarebbe silenziosa (la lista proporrebbe il verbo su una
        #    riga che la mutazione rifiuta).
        conditions = ["a.competenza_mese = %s", "a.motivo_non_fatturata = %s"]
        params: list[Any] = [competenza_mese, MOTIVO_NON_FATTURATA_RESIDUO]
        where_clause = "WHERE " + " AND ".join(conditions)

        sort_col = colonna_ordinamento(order_by, self.DASH_COMPETENZA_RESIDUI_SORT_COLUMNS)
        # ⚠️ Senza `order_dir` le colonne data partono DESC (regola «date DESC»,
        #    inferita dal nome con `e_chiave_data`, 2026-10-20), le altre ASC; la
        #    stessa direzione vale per il TIEBREAK — altrimenti la primaria
        #    salirebbe e lo spareggio scenderebbe, cioe' dentro lo stesso mese
        #    l'elenco andrebbe al contrario di come e' stato chiesto (e' il
        #    difetto corretto in 30 punti il 2026-08-03).
        direction = sql_order_direction_lista(order_by, order_dir, colonne=self.DASH_COMPETENZA_RESIDUI_SORT_COLUMNS)
        tiebreak_dir = sql_tiebreak_direction(direction)
        # ⚠️ Il tiebreak e' `attivita_fatturabile_id`: e' la chiave del verbo,
        #    quindi l'unica univoca su questa lista — e su un elenco da cui si
        #    SELEZIONA, una paginazione non deterministica farebbe agire su
        #    righe diverse da quelle spuntate.
        tiebreak = f"commessa_codice ASC, attivita_fatturabile_id {tiebreak_dir}"
        if sort_col is not None:
            order_clause = f"ORDER BY {sort_col} {direction}, {tiebreak}"
        else:
            # ⭐ Il default e' `competenza_mese` ASC, fedele
            #    all'`ordinamento_default` del preset a catalogo — e deve
            #    coincidere con quello che il frontend manda, altrimenti
            #    l'export (che non passa dai filtri a video) darebbe un ordine
            #    diverso dalla schermata e nessuno se ne accorgerebbe aprendo
            #    il foglio.
            # ⚠️ MA su questa lista quella colonna e' COSTANTE: il perimetro e'
            #    un mese solo (`a.competenza_mese = %s`), quindi l'ordine che si
            #    vede lo decide per intero il tiebreak — commessa, poi chiave.
            #    Si scrive lo stesso, e per due ragioni: e' cio' che il catalogo
            #    dichiara (divergere sarebbe un contratto non mantenuto), e il
            #    giorno che il filtro si allargasse a un intervallo la clausola
            #    e' gia' quella giusta. ⛔ Quel che NON si puo' dire e' «i piu'
            #    vecchi in cima»: dentro un mese solo non c'e' nessun ordine di
            #    anzianita' da leggere qui.
            order_clause = f"ORDER BY competenza_mese {direction}, {tiebreak}"

        # ⚠️ `attivita_fatturabile_id` si proietta ma NON e' a catalogo: serve al
        #    verbo, non all'occhio (§7.4 del brief DB). Toglierlo dalla SELECT
        #    lascerebbe una lista che si puo' guardare e non azionare.
        select_sql = f"""
            SELECT
                a.attivita_fatturabile_id,
                a.commessa_attivita_id,
                a.commessa_id,
                a.commessa_codice,
                a.cliente_display,
                a.articolo_codice,
                a.articolo_descrizione,
                a.competenza_mese,
                a.data_attivita,
                a.quantita,
                a.valore,
                a.lotto_provenienza_id,
                a.lotto_provenienza_codice,
                a.motivo_non_fatturata,
                a.emittente_ragione_sociale
            FROM vendite.vw_dash_competenza_attivita a
            {where_clause}
        """  # noqa: S608 — WHERE da clausole letterali con %s, valori come parametri

        rows, total_count = self._query_paged_view(
            select_sql=select_sql,
            order_by=order_clause,
            params=params,
            limit=limit,
            offset=offset,
        )

        result: list[DashCompetenzaResiduoRow] = []
        for row in rows:
            result.append(
                {
                    "attivita_fatturabile_id": None if row[0] is None else int(row[0]),
                    "commessa_attivita_id": int(row[1]),
                    "commessa_id": int(row[2]),
                    "commessa_codice": None if row[3] is None else str(row[3]),
                    "cliente_display": None if row[4] is None else str(row[4]),
                    "articolo_codice": None if row[5] is None else str(row[5]),
                    "articolo_descrizione": None if row[6] is None else str(row[6]),
                    "competenza_mese": row[7].isoformat() if row[7] is not None else None,
                    "data_attivita": row[8].isoformat() if row[8] is not None else None,
                    "quantita": str(row[9]) if row[9] is not None else None,
                    "valore": str(row[10]) if row[10] is not None else None,
                    "lotto_provenienza_id": None if row[11] is None else int(row[11]),
                    "lotto_provenienza_codice": None if row[12] is None else str(row[12]),
                    "motivo_non_fatturata": None if row[13] is None else str(row[13]),
                    "emittente_ragione_sociale": None if row[14] is None else str(row[14]),
                }
            )
        return result, total_count

    # Colonne di ordinamento ammesse per il drill-down AGGREGATO per commessa.
    # Su aggregati si ordina per gli aggregati, non per le colonne di riga.
    DASH_COMPETENZA_COMMESSE_SORT_COLUMNS = {
        "commessa_codice": "commessa_codice",
        "cliente_display": "cliente_display",
        "n_attivita": "n_attivita",
        "valore_tot": "valore_tot",
        "data_attivita_max": "data_attivita_max",
        # Emittente (P-4, Fase E del brief perimetro-emittente): la riga di
        # catalogo e' `ordinabile = t`, e il presidio
        # `test_liste_configurabili_seed` lega catalogo e whitelist nei DUE
        # versi — la chiave e' il CAMPO FISICO, non il `codice` della colonna.
        "emittente_ragione_sociale": "emittente_ragione_sociale",
    }

    # Scopo: Drill-down AGGREGATO per commessa (DEC-4) — una riga per commessa nel
    #        perimetro corrente (competenza_mese + stadio + solo_ritardo), con
    #        n attivita', totali valore/fatturato, estremi data e recuperi tardivi.
    #        Sostituisce la lista a grana attivita' quando l'operatore vuole la
    #        fotografia per commessa; il dettaglio resta nel drawer di gestione.
    # Perimetro: sola lettura su vw_dash_competenza_attivita (scope GUC in vista).
    # Risultato: tuple (lista DashCompetenzaCommessaRow, conteggio commesse).
    def list_dash_competenza_commesse(
        self,
        *,
        competenza_mese: date,
        stadio: str | None,
        solo_ritardo: bool,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[DashCompetenzaCommessaRow], int]:
        conditions: list[str] = ["a.competenza_mese = %s"]
        params: list[Any] = [competenza_mese]
        if stadio is not None:
            conditions.append("a.stadio = %s")
            params.append(stadio)
        if solo_ritardo:
            conditions.append("a.emessa_in_ritardo IS TRUE")

        where_clause = "WHERE " + " AND ".join(conditions)

        # ORDER BY server-side sugli aggregati (corretto su TUTTE le pagine):
        # colonna dalla whitelist + direzione, tiebreak stabile su commessa.
        # Assente/non ammesso -> default valore_tot DESC (le commesse piu' pesanti
        # prima), coerente col default a grana attivita'.
        sort_col = colonna_ordinamento(order_by, self.DASH_COMPETENZA_COMMESSE_SORT_COLUMNS)
        # sql_order_direction ritorna gia' 'ASC NULLS FIRST'/'DESC NULLS LAST':
        # NON aggiungere un secondo NULLS (errore di sintassi PG). Direzione
        # risolta prima del ramo cosi' anche il default DESC ha il tiebreak
        # coerente; `commessa_codice` raggruppa, `commessa_id` segue.
        direction = sql_order_direction_lista(
            order_by, order_dir, colonne=self.DASH_COMPETENZA_COMMESSE_SORT_COLUMNS, default_desc=True,
        )
        tiebreak_dir = sql_tiebreak_direction(direction)
        tiebreak = f"commessa_codice ASC, commessa_id {tiebreak_dir}"
        if sort_col is not None:
            order_clause = f"ORDER BY {sort_col} {direction}, {tiebreak}"
        else:
            order_clause = f"ORDER BY valore_tot DESC NULLS LAST, {tiebreak}"

        select_sql = f"""
            SELECT
                a.commessa_id,
                a.commessa_codice,
                a.cliente_display,
                COUNT(*)                                         AS n_attivita,
                COUNT(*) FILTER (WHERE a.emessa_in_ritardo IS TRUE) AS n_in_ritardo,
                SUM(a.valore)                                   AS valore_tot,
                SUM(a.valore_fatturato)                         AS valore_fatturato_tot,
                MIN(a.data_attivita)                            AS data_attivita_min,
                MAX(a.data_attivita)                            AS data_attivita_max,
                a.emittente_ragione_sociale
            FROM vendite.vw_dash_competenza_attivita a
            {where_clause}
            GROUP BY a.commessa_id, a.commessa_codice, a.cliente_display,
                     a.emittente_ragione_sociale
        """  # noqa: S608 — WHERE da clausole letterali con %s, valori come parametri
        # ⚠️ `emittente_ragione_sociale` entra nel GROUP BY, e non e' indolore:
        #    se una commessa avesse attivita' di emittenti DIVERSI si
        #    spezzerebbe in piu' righe: i totali resterebbero giusti e il
        #    conteggio delle commesse no, cioe' una regressione silenziosa.
        #    Non succede — l'emittente e' una colonna della COMMESSA
        #    (`co.emittente_soggetto_ruolo_id` nella vista), non dell'attivita',
        #    quindi e' funzionalmente dipendente da `commessa_id`. Domanda posta
        #    al team DB nel brief di Fase E e risposta «si', per costruzione».
        #    Presidiato dal test `commesse_una_riga_per_commessa`.

        # UNA sola valutazione della vista: prima il COUNT delle commesse
        # distinte era una seconda scansione con lo stesso GROUP BY. Qui il
        # `COUNT(*) OVER ()` della CTE conta le RIGHE raggruppate, che sono
        # esattamente le commesse distinte — stesso numero, meta' del lavoro.
        # In piu' arriva il CLAMP dell'offset: prima il service dichiarava la
        # pagina EFFETTIVA mentre il repository serviva quella RICHIESTA, e su
        # una pagina stantia l'envelope diceva «pagina 2» con zero righe — il
        # frontend ripiegava sulla pagina 1, cioe' nel posto sbagliato.
        rows, total_count = self._query_paged_view(
            select_sql=select_sql,
            order_by=order_clause,
            params=params,
            limit=limit,
            offset=offset,
        )

        result: list[DashCompetenzaCommessaRow] = []
        for row in rows:
            result.append(
                {
                    "commessa_id": int(row[0]),
                    "commessa_codice": None if row[1] is None else str(row[1]),
                    "cliente_display": None if row[2] is None else str(row[2]),
                    "n_attivita": int(row[3]),
                    "n_in_ritardo": int(row[4]),
                    "valore_tot": str(row[5]) if row[5] is not None else None,
                    "valore_fatturato_tot": str(row[6]) if row[6] is not None else None,
                    "data_attivita_min": row[7].isoformat() if row[7] is not None else None,
                    "data_attivita_max": row[8].isoformat() if row[8] is not None else None,
                    # Emittente (P-4, Fase E): chiave = `campo_sorgente` del
                    # catalogo, o la colonna resta vuota a video.
                    "emittente_ragione_sociale": row[9],
                }
            )
        return result, total_count

    # Colonne ordinabili dell'elenco GRUPPI FATTURABILI: chiave FE (field del
    # DataTable) -> colonna di OUTPUT della CTE `righe` (senza alias di
    # tabella: l'ORDER BY di `query_paged_view` si applica alla CTE, non alla
    # vista). Whitelist: nell'ORDER BY solo chiavi note + ASC/DESC (no injection).
    DASH_COMPETENZA_GRUPPI_SORT_COLUMNS = {
        "riferimento": "riferimento",
        "tipo_gruppo": "tipo_gruppo",
        "cliente_display": "cliente_display",
        "commessa_codice": "commessa_codice",
        "n_attivita": "n_attivita",
        "valore": "valore",
        "data_attivita_max": "data_attivita_max",
        # Colonne cliente di fatturazione (BE-5, brief-db-dash-competenza-gruppi
        # §D-4). ⚠️ Queste due chiavi e le righe 476/477 del CSV
        # `ui/lista_colonna.csv` sono UN SOLO passo: il presidio
        # `apps/core/tests/test_liste_configurabili_seed.py` lega catalogo e
        # whitelist nei DUE versi — una colonna `ordinabile = t` fuori whitelist
        # fa rosso (la freccia a video risponderebbe 400), e una in whitelist
        # marcata `ordinabile = f` fa rosso pure lei. Separarli rende la CI rossa
        # in un verso o nell'altro.
        "ba_codice_fatturazione": "ba_codice_fatturazione",
        "id_fiscale": "id_fiscale",
        # Emittente (P-4, brief perimetro-emittente passo 6 / BE-2). Stessa
        # coppia inscindibile delle due righe qui sopra: la colonna
        # `emittente_fiscale` del catalogo (`ui/lista_colonna.csv`, lista
        # `vendite.dash_competenza_gruppi`) e' `ordinabile = t`, quindi senza
        # questa voce
        # il presidio `test_liste_configurabili_seed` e' rosso in un verso — e
        # la freccia a video risponderebbe 400.
        # ⚠️ La chiave e' il CAMPO FISICO (`emittente_ragione_sociale`), non il
        # `codice` della colonna a catalogo (`emittente_fiscale`): il secondo
        # verso dello stesso presidio verifica proprio questo.
        "emittente_ragione_sociale": "emittente_ragione_sociale",
        # Sezionale previsto e data prevista (BE-2, brief
        # brief-db-registro-e-data-prevista-in-competenza). Stessa coppia
        # inscindibile delle voci qui sopra: le righe 553/554 del CSV
        # `ui/lista_colonna.csv` sono `ordinabile = t`, e il presidio
        # `test_liste_configurabili_seed` lega catalogo e whitelist nei DUE
        # versi. Il DB le ha consegnate sapendo che restavano rosse fino a qui.
        # ⚠️ La chiave e' il `campo_sorgente`, non il `codice` a catalogo: la
        # colonna del registro si chiama `registro` a catalogo e
        # `registro_codice` sulla vista — la whitelist vuole il secondo.
        # ⚠️ Ordinare per `registro_codice` mette insieme, in fondo, i gruppi
        # multi-sezionale e quelli non risolvibili: sulla vista sono entrambi
        # NULL. E' l'unico ordinamento possibile (il primo gruppo un codice non
        # ce l'ha) ed e' anche quello utile: le righe da guardare finiscono
        # vicine.
        "registro_codice": "registro_codice",
        "data_documento_prevista": "data_documento_prevista",
        # ═══ L'ESITO DELL'ULTIMO TENTATIVO (changeSet DB `20260906-12`,
        #     brief-db-esito-gruppo-lotto R-3) ═════════════════════════════
        # Stessa coppia inscindibile delle voci qui sopra: le righe 724/725/
        # 727/728 del CSV `ui/lista_colonna.csv` sono `ordinabile = t`, e il
        # presidio `test_liste_configurabili_seed` lega catalogo e whitelist
        # nei DUE versi — una qui senza la sua riga a catalogo e' rossa quanto
        # il contrario.
        # ⭐ `ultimo_esito` e' l'ordinamento che serve davvero: mette in cima le
        #    righe su cui un giro ha gia' provato e ha fallito, che sono le
        #    uniche su cui l'operatore ha qualcosa da fare.
        # ⛔ `ultimo_errore_messaggio` NON e' qui, ed e' una scelta: ordinare
        #    alfabeticamente delle frasi non risponde a nessuna domanda. La sua
        #    riga a catalogo e' `ordinabile = f`, e i due versi del presidio
        #    la tengono fuori da entrambe le parti.
        "ultimo_esito": "ultimo_esito",
        "ultimo_errore_codice": "ultimo_errore_codice",
        "ultimo_errore_quando": "ultimo_errore_quando",
        "ultimo_lotto_codice": "ultimo_lotto_codice",
    }

    # Scopo: Elenco dei GRUPPI FATTURABILI di un mese/stadio — l'unita' su cui
    #        l'operatore decide nella card «Da emettere»: un documento sorgente
    #        (PRV-0012, CTR-0007…) oppure gli oneri di una commessa, che
    #        documento non hanno e altrimenti resterebbero lavoro invisibile e
    #        non azionabile. La `gruppo_key` esposta qui e' la STESSA che si
    #        rimanda al POST di emissione mirata: nessun mapping, nessuna
    #        possibilita' che elenco e criterio divergano.
    # Perimetro: sola lettura su vw_dash_competenza_gruppi (security_invoker:
    #        lo scope emittente e' applicato dalla vista, fail-closed senza GUC).
    # Risultato: tuple (lista DashCompetenzaGruppoRow, conteggio totale).
    # Scopo: predicato comune dell'elenco gruppi (lista + riepilogo), cosi' i
    #        totali non possono descrivere un perimetro diverso dalle righe che
    #        stanno sopra. `tipo_gruppo` e' opzionale: il filtro «tipo
    #        documento/sorgente» del cockpit. NON lo usa la facet, che deve
    #        vedere tutti i tipi anche quando uno e' selezionato (altrimenti
    #        scegliendo «Preventivi» le altre voci sparirebbero dalla tendina e
    #        non si potrebbe piu' cambiare idea).
    # ⚠️ `ba_fatturazione_id` e `ba_non_determinabile` sono ALTERNATIVI e non si
    #        sommano: il secondo e' la voce «cliente non determinabile» (D-5), che
    #        e' l'assenza del primo. Rappresentarla con un id sentinella (0, -1)
    #        avrebbe messo un valore finto in un campo che porta chiavi vere —
    #        e prima o poi qualcuno lo confronta con una PK.
    # ⚠️ La ricerca sotto la soglia del BB viene IGNORATA (non svuota la
    #        lista): policy ricerca e paginazione. La soglia sta nel BB, cioe'
    #        nel repository, perche' il repository e' chiamato anche dall'export.
    # Scopo: il perimetro BASE — competenza e stadio, e nient'altro.
    # ⭐ Separato dagli altri filtri perche' i due insiemi rispondono a domande
    #    diverse: la lista e i totali seguono TUTTI i filtri, le tre facet solo
    #    questo. Finche' `_where_gruppi` era una funzione sola, l'unico modo di
    #    avere il perimetro base era chiamarla senza gli altri argomenti — cioe'
    #    una seconda esecuzione della query piu' cara del giro.
    @staticmethod
    def _where_gruppi_base(
        *, competenza_mese: date, stadio: str | None,
    ) -> tuple[list[str], list[Any]]:
        conditions: list[str] = ["g.competenza_mese = %s"]
        params: list[Any] = [competenza_mese]
        if stadio is not None:
            conditions.append("g.stadio = %s")
            params.append(stadio)
        return conditions, params

    # Scopo: i filtri SCELTI dall'operatore (tipo, cliente, sezionale, ricerca),
    #        cioe' cio' che restringe il perimetro base.
    # ⚠️ Le condizioni restano prefissate `g.`: si applicano sulla vista come su
    #        una CTE che porti lo stesso alias. E' la proprieta' che permette di
    #        filtrare un perimetro gia' letto invece di rileggerlo.
    # ⭐ Torna anche le COLONNE che legge, e non e' zavorra: chi filtra un
    #    perimetro gia' materializzato (`get_dash_competenza_gruppi_accessori`)
    #    deve sapere quali colonne portarsi dietro. Dichiararle QUI — accanto al
    #    predicato che le usa — e' l'unico modo perche' non si dimentichino: il
    #    primo tentativo teneva l'elenco altrove e si e' rotto sulla RICERCA
    #    LIBERA, che guarda cinque colonne di cui tre non erano previste.
    #    Chi aggiunge un filtro aggiunge la sua condizione e le sue colonne
    #    nello stesso punto, o non compila.
    @staticmethod
    def _where_gruppi_filtri(
        *,
        tipo_gruppo: str | None = None,
        ba_fatturazione_id: int | None = None,
        ba_non_determinabile: bool = False,
        registro_id: int | None = None,
        registro_non_risolvibile: bool = False,
        search: str | None = None,
    ) -> tuple[list[str], list[Any], list[str]]:
        conditions: list[str] = []
        params: list[Any] = []
        colonne: list[str] = []
        if tipo_gruppo is not None:
            conditions.append("g.tipo_gruppo = %s")
            params.append(tipo_gruppo)
            colonne.append("g.tipo_gruppo")
        if ba_non_determinabile:
            conditions.append("g.ba_fatturazione_id IS NULL")
            colonne.append("g.ba_fatturazione_id")
        elif ba_fatturazione_id is not None:
            conditions.append("g.ba_fatturazione_id = %s")
            params.append(ba_fatturazione_id)
            colonne.append("g.ba_fatturazione_id")
        # ── Filtro SEZIONALE (D-5) ────────────────────────────────────────
        # ⛔ `= ANY(g.registri_ids)` e NON `g.registro_codice = %s`, ed e' la
        #    decisione portante del filtro: un gruppo che tocca due sezionali
        #    deve comparire sotto ENTRAMBE le voci, e sulla seconda colonna e'
        #    NULL — quindi con un filtro sul codice sparirebbe da tutte e due.
        #    E' anche la ragione per cui la vista espone l'array e non solo il
        #    codice.
        # ⚠️ `registro_non_risolvibile` e' ALTERNATIVO, non aggiuntivo: e'
        #    l'ASSENZA del valore (stessa forma di `ba_non_determinabile`), e
        #    si scrive come array vuoto o di soli NULL — non come un id
        #    sentinella, che prima o poi finisce confrontato con una PK.
        #    `cardinality(...) = 0` non basterebbe: `array_agg(DISTINCT)`
        #    conserva i NULL, quindi un gruppo interamente non risolvibile ha
        #    `{NULL}`, cardinalita' 1.
        if registro_non_risolvibile:
            conditions.append(
                "NOT EXISTS (SELECT 1 FROM unnest(g.registri_ids) r WHERE r IS NOT NULL)"
            )
            colonne.append("g.registri_ids")
        elif registro_id is not None:
            conditions.append("%s = ANY(g.registri_ids)")
            params.append(registro_id)
            colonne.append("g.registri_ids")
        # ── Ricerca libera (BB) ───────────────────────────────────────────
        # Il BB scrive l'OR in UN solo gruppo parentesizzato: senza le
        # parentesi l'OR si legherebbe all'ultima AND della catena e il filtro
        # mese/stadio smetterebbe di valere per i rami successivi — una
        # ricerca che allarga il perimetro invece di restringerlo.
        # ⭐ Le COLONNE da portarsi dietro solo se il BB ha davvero aggiunto
        #    una condizione (termine sopra soglia): «solo quando l'operatore ha
        #    digitato qualcosa», come prima. Si dichiarano TUTTE quelle che il
        #    repository sa cercare, non le sole accese: il catalogo si legge
        #    dentro il BB, e un superinsieme non puo' mai mancarne una. Sono le
        #    stesse cinque che la CTE `base` si portava dietro prima del BB.
        prima = len(conditions)
        add_ricerca_full_condition(
            conditions, params, search, _RICERCA_DASH_COMPETENZA_GRUPPI, alias="g",
        )
        if len(conditions) > prima:
            colonne.extend(_RICERCA_DASH_COMPETENZA_GRUPPI.espressioni("g").values())
        return conditions, params, colonne

    # Scopo: il predicato COMPLETO (base + filtri), com'era prima della
    #        separazione. Firma e comportamento invariati: e' cio' che usano
    #        lista, totali e conteggi.
    # ⚠️ L'ordine e' portante — base PRIMA dei filtri — perche' i parametri
    #        viaggiano posizionali e devono seguire l'ordine in cui i segnaposto
    #        compaiono nel testo SQL.
    @staticmethod
    def _where_gruppi(
        *,
        competenza_mese: date,
        stadio: str | None,
        tipo_gruppo: str | None = None,
        ba_fatturazione_id: int | None = None,
        ba_non_determinabile: bool = False,
        registro_id: int | None = None,
        registro_non_risolvibile: bool = False,
        search: str | None = None,
    ) -> tuple[list[str], list[Any]]:
        cond_base, par_base = VenditeRepository._where_gruppi_base(
            competenza_mese=competenza_mese, stadio=stadio,
        )
        cond_filtri, par_filtri, _colonne = VenditeRepository._where_gruppi_filtri(
            tipo_gruppo=tipo_gruppo,
            ba_fatturazione_id=ba_fatturazione_id,
            ba_non_determinabile=ba_non_determinabile,
            registro_id=registro_id,
            registro_non_risolvibile=registro_non_risolvibile,
            search=search,
        )
        # Le colonne non servono qui: chi interroga la VISTA le ha tutte. Sono
        # per chi filtra un perimetro gia' materializzato.
        return cond_base + cond_filtri, par_base + par_filtri

    def list_dash_competenza_gruppi(
        self,
        *,
        competenza_mese: date,
        stadio: str | None,
        tipo_gruppo: str | None = None,
        ba_fatturazione_id: int | None = None,
        ba_non_determinabile: bool = False,
        registro_id: int | None = None,
        registro_non_risolvibile: bool = False,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[DashCompetenzaGruppoRow], int]:
        conditions, params = self._where_gruppi(
            competenza_mese=competenza_mese, stadio=stadio, tipo_gruppo=tipo_gruppo,
            ba_fatturazione_id=ba_fatturazione_id,
            ba_non_determinabile=ba_non_determinabile,
            registro_id=registro_id,
            registro_non_risolvibile=registro_non_risolvibile,
            search=search,
        )
        where_clause = "WHERE " + " AND ".join(conditions)

        # ⚠️ Tiebreak su (gruppo_key, stadio) e non sulla sola chiave: la vista
        # raggruppa per (competenza, gruppo_key, …, stadio), quindi SENZA il
        # filtro stadio — che e' opzionale — lo STESSO gruppo compare su piu'
        # righe (parte da emettere, parte gia' fatturata). Con il solo
        # gruppo_key l'ordine fra quelle righe sarebbe indefinito e la
        # paginazione non deterministica (frontend-standards §Paginazione
        # deterministica): righe ripetute o saltate cambiando pagina.
        sort_col = colonna_ordinamento(order_by, self.DASH_COMPETENZA_GRUPPI_SORT_COLUMNS)
        # sql_order_direction ritorna gia' 'ASC NULLS FIRST'/'DESC NULLS LAST'.
        # Direzione prima del ramo: vale anche per il default DESC.
        direction = sql_order_direction_lista(
            order_by, order_dir, colonne=self.DASH_COMPETENZA_GRUPPI_SORT_COLUMNS, default_desc=True,
        )
        tiebreak_dir = sql_tiebreak_direction(direction)
        tiebreak = f"gruppo_key ASC, stadio {tiebreak_dir}"
        if sort_col is not None:
            order_clause = f"ORDER BY {sort_col} {direction}, {tiebreak}"
        else:
            # Default: i gruppi che pesano di piu' in cima (stessa logica del
            # drill-down per commessa).
            order_clause = f"ORDER BY valore DESC NULLS LAST, {tiebreak}"

        # Clamp dell'offset all'ultima pagina reale in UNA valutazione, come le
        # altre liste dei cruscotti: il service dichiara poi la pagina effettiva
        # nell'envelope e `usePagedDashFetch` la adotta. Senza, una pagina
        # stantia tornerebbe VUOTA con count > 0 e il FE ripiegherebbe sulla
        # PRIMA pagina — un secondo giro, e per giunta nel posto sbagliato.
        # 🟢 `documento_id` e `commessa_stato_descrizione` arrivano ora dalla
        # VISTA (changeSet DB `20260815-24`/`-25`, brief emittibilita' §9.3).
        # Qui c'erano due risoluzioni scritte a mano — una LATERAL su
        # `vw_dash_fatturazione_documenti` per l'id del documento e un
        # `LEFT JOIN vendite.stati_commessa` per la descrizione dello stato —
        # ed erano **due copie** di regole che la vista gia' applicava: il
        # commento di allora dichiarava il drift come «noto e accettato».
        # Toglierle non e' cosmetica: l'id del documento nasce ora dalla
        # STESSA riga da cui viene il `riferimento`, quindi codice e id non
        # possono piu' descrivere documenti diversi.
        # Gruppi SOURCELESS (oneri di commessa): `documento_id` resta NULL —
        # quei gruppi un documento non ce l'hanno, e il FE offre la sola
        # commessa.
        rows, total_count = self._query_paged_view(
            select_sql=f"""
            SELECT
                g.gruppo_key,
                g.tipo_gruppo,
                g.documento_apribile,
                g.riferimento,
                g.commessa_id,
                g.commessa_codice,
                g.cliente_display,
                g.stadio,
                g.n_attivita,
                g.valore,
                g.ha_oneri,
                g.data_attivita_min,
                g.data_attivita_max,
                g.documento_id,
                g.commessa_emittibile,
                g.commessa_stato_codice_interno,
                g.commessa_stato_descrizione,
                g.ba_codice_fatturazione,
                g.id_fiscale,
                g.emittente_ragione_sociale,
                g.registri_n,
                g.registro_codice,
                g.data_documento_prevista,
                g.ultimo_esito,
                g.ultimo_errore_codice,
                g.ultimo_errore_messaggio,
                g.ultimo_errore_quando,
                g.ultimo_lotto_codice,
                -- ⭐ IL VERDETTO «questo documento e' trattenuto da un lotto
                --    VIVO» (`20260909-24`), non la materia per dedurlo.
                -- ⛔ E il perche' e' una misura: `ultimo_esito` sembrava
                --    bastare e rispondeva GIUSTO PER CASO. Su tre documenti in
                --    `DA_EMETTERE` due avevano `COMPLETED` con il lotto
                --    ANNULLATO — cioe' liberi — e sbarrare la riga da li'
                --    avrebbe bloccato per sempre il contenuto di ogni lotto
                --    annullato.
                -- ⚠️ Colonne che nominano IL VERBO (§12.5.4): `emissione_*`, e
                --    non un `blocco_` generico che domani risponde a due
                --    domande diverse.
                g.emissione_blocco_reason,
                g.emissione_blocco_reason_key,
                -- ⭐ Il lotto viaggia come BERSAGLIO e non come frase: chi
                --    legge non deve ricopiare un codice per poi cercarlo.
                g.emissione_blocco_lotto_id,
                g.emissione_blocco_lotto_codice,
                -- ⭐ V-1 (`20260909-66`): il lotto del TENTATIVO esce con il
                --    suo STATO. Prima usciva il solo codice, e a video un
                --    tentativo in un lotto ANNULLATO si leggeva come uno
                --    ancora in corso — rilievo di Tid sul collaudo.
                -- ⛔ Il dato non si toglie: e' l'unica traccia che spieghi
                --    perche' il documento e' tornato disponibile. Si dice SE
                --    conta ancora, e il frontend spegne il GESTO — testo si',
                --    pulsante no.
                g.ultimo_lotto_id,
                g.ultimo_lotto_stato,
                g.ultimo_lotto_pre_fiscale
            FROM vendite.vw_dash_competenza_gruppi g
            {where_clause}
            """,  # noqa: S608 — WHERE da _where_gruppi (clausole letterali + BB add_ricerca_full_condition), valori come parametri
            order_by=order_clause,
            params=params,
            limit=limit,
            offset=offset,
        )

        result: list[DashCompetenzaGruppoRow] = []
        for row in rows:
            result.append(
                {
                    "gruppo_key": str(row[0]),
                    "tipo_gruppo": str(row[1]),
                    "documento_apribile": None if row[2] is None else bool(row[2]),
                    # Nessun ramo NULL, come `gruppo_key` e `tipo_gruppo` qui
                    # sopra: `riferimento` e' NOT NULL per contratto della vista
                    # (`COALESCE(documento_numero, commessa_codice, gruppo_key)`,
                    # e l'ultimo ramo e' la chiave del gruppo). Il ramo c'era, e
                    # descriveva un caso che la vista non puo' produrre: e' la
                    # stessa catena di ripiego duplicata tolta dal frontend il
                    # 2026-09-01 (brief-db-riferimento-gruppi-lateral-costosa §9).
                    "riferimento": str(row[3]),
                    "commessa_id": None if row[4] is None else int(row[4]),
                    "commessa_codice": None if row[5] is None else str(row[5]),
                    "cliente_display": None if row[6] is None else str(row[6]),
                    "stadio": None if row[7] is None else str(row[7]),
                    "n_attivita": int(row[8]),
                    "valore": str(row[9]) if row[9] is not None else None,
                    "ha_oneri": bool(row[10]),
                    "data_attivita_min": row[11].isoformat() if row[11] is not None else None,
                    "data_attivita_max": row[12].isoformat() if row[12] is not None else None,
                    "documento_id": None if row[13] is None else int(row[13]),
                    "commessa_emittibile": None if row[14] is None else bool(row[14]),
                    "commessa_stato_codice_interno": None if row[15] is None else str(row[15]),
                    "commessa_stato_descrizione": None if row[16] is None else str(row[16]),
                    # Cliente di FATTURAZIONE (padre se c'e', altrimenti se
                    # stesso): e' l'elemento che `fn_build_fattura_key` mette in
                    # chiave, non il BA della riga. NULL quando il padre e'
                    # fuori scope RLS — il gruppo resta comunque in lista (D-5),
                    # perche' una riga che non si riesce ad attribuire e'
                    # precisamente la riga dimenticata da cui nasce il cantiere.
                    "ba_codice_fatturazione": None if row[17] is None else str(row[17]),
                    "id_fiscale": None if row[18] is None else str(row[18]),
                    # Emittente della riga (P-4, lista PILOTA del giro — brief
                    # perimetro-emittente passo 6). La vista lo espone dal
                    # 2026-08-18 (`20260818-15`); la riga di catalogo esiste
                    # (`ui.lista_colonna`, codice `emittente_fiscale`) e la
                    # colonna si puo' spuntare.
                    # ⛔ La chiave DEVE restare `emittente_ragione_sociale`: e'
                    # il `campo_sorgente` dichiarato a catalogo, e la lista ha
                    # `vista_sql = NULL` — quindi il catalogo non puo' pescare
                    # il campo da se', lo deve portare questo SELECT. Se le due
                    # divergono la colonna si spunta e resta VUOTA.
                    "emittente_ragione_sociale": None if row[19] is None else str(row[19]),
                    # ═══ Sezionale previsto e data prevista (BE-1) ═══════════
                    # ⛔ Le due CHIAVI devono restare identiche al
                    # `campo_sorgente` a catalogo (`registro_codice`,
                    # `data_documento_prevista`, righe 553/554): la lista ha
                    # `vista_sql = NULL`, quindi il catalogo il campo non lo
                    # pesca da se' — lo porta questo SELECT. Se divergono, la
                    # colonna si spunta e resta VUOTA su tutte le righe, senza
                    # nessun errore.
                    # ⛔ `registri_ids` NON entra nel payload, ed e' una scelta.
                    # Serve al WHERE del filtro e alla facet — che stanno
                    # entrambi qui — ma esporlo obbligherebbe a decidere se
                    # tenere i NULL che `array_agg(DISTINCT)` conserva: con i
                    # NULL e' una lista scomoda, senza diverge da `registri_n`
                    # che li conta. Due numeri che dicono «quanti sezionali» e
                    # non coincidono sono una domanda senza risposta. Al FE
                    # bastano il conteggio e il codice.
                    "registri_n": 0 if row[20] is None else int(row[20]),
                    "registro_codice": None if row[21] is None else str(row[21]),
                    "data_documento_prevista": (
                        row[22].isoformat() if row[22] is not None else None
                    ),
                    # ═══ L'ESITO DELL'ULTIMO TENTATIVO DI FATTURAZIONE ═══════
                    # (changeSet DB `20260906-12`, brief-db-esito-gruppo-lotto
                    # R-3). ⭐ Nasce dal lotto LTF-0009578: tre ordini presi in
                    # carico, due fatturati, e il terzo — caduto PRIMA di
                    # diventare fattura — restava qui senza nessun segno,
                    # quindi sembrava fatturabile.
                    # ⛔ NON sono una LATERAL scritta qui: le calcola la VISTA,
                    #    che lega l'esito al gruppo sul mese di competenza. Il
                    #    mese e' parte del legame e non un di piu' — senza, il
                    #    documento di settembre erediterebbe l'errore di agosto.
                    # ⚠️ `ultimo_esito` NON spegne `stadio` ne'
                    #    `commessa_emittibile` (decisione di Tid, 2026-09-06):
                    #    dice «ci ho provato e non ci sono riuscito», non
                    #    «questo documento non si puo' fatturare». Un gruppo in
                    #    errore resta DA EMETTERE ed e' ancora selezionabile.
                    # ⚠️ Tutte `None` finche' il giro non passa da
                    #    `vendite.fn_segna_esito_gruppo_lotto`: `NULL` vuol dire
                    #    «nessuno l'ha detto», che e' diverso da «e' andata
                    #    bene». Le due cose il frontend deve tenerle distinte.
                    "ultimo_esito": None if row[23] is None else str(row[23]),
                    "ultimo_errore_codice": None if row[24] is None else str(row[24]),
                    "ultimo_errore_messaggio": None if row[25] is None else str(row[25]),
                    "ultimo_errore_quando": (
                        row[26].isoformat() if row[26] is not None else None
                    ),
                    "ultimo_lotto_codice": None if row[27] is None else str(row[27]),
                    # ═══ TRATTENUTO DA UN LOTTO VIVO (2026-09-09) ═══════════
                    # ⚠️ `None` = la riga si puo' prendere. Il motivo e la
                    # chiave i18n viaggiano insieme al BERSAGLIO del lotto: la
                    # frase dice cosa fare, il bersaglio ci porta.
                    "emissione_blocco_reason": (
                        None if row[28] is None else str(row[28])
                    ),
                    "emissione_blocco_reason_key": (
                        None if row[29] is None else str(row[29])
                    ),
                    "emissione_blocco_lotto_id": (
                        None if row[30] is None else int(row[30])
                    ),
                    "emissione_blocco_lotto_codice": (
                        None if row[31] is None else str(row[31])
                    ),
                    # ═══ V-1 · il lotto del TENTATIVO, col suo stato ═════════
                    # ⚠️ `ultimo_lotto_pre_fiscale` e' il flag su cui il
                    # frontend decide se offrire il gesto: un bersaglio verso
                    # un lotto che non conta piu' e' un pulsante in un vicolo
                    # cieco. `None` quando non c'e' nessun tentativo.
                    "ultimo_lotto_id": None if row[32] is None else int(row[32]),
                    "ultimo_lotto_stato": (
                        None if row[33] is None else str(row[33])
                    ),
                    "ultimo_lotto_pre_fiscale": (
                        None if row[34] is None else bool(row[34])
                    ),
                    # ═══ D3 · la bandiera della commessa respinta ════════════
                    # Nascono vuote e le riempie `_applica_bandiera_respinta`
                    # sulla SOLA pagina: vedi il commento del metodo per il
                    # motivo per cui non sono una colonna di questo SELECT.
                    "respinta_il": None,
                    "respinta_motivo": None,
                }
            )
        self._applica_bandiera_respinta(result, competenza_mese=competenza_mese)
        return result, total_count

    # Scopo: D3 · accende sulle righe della PAGINA la bandiera «questa commessa
    #        e' stata respinta», con il motivo che il pull ha scritto sul log.
    #        Fino al 2026-09-04 la riga non lo diceva: mostrava lavoro «da
    #        emettere» del tutto ordinario mentre un giro l'aveva rifiutata, e
    #        il motivo viveva solo nel log del lotto — a due click da chi deve
    #        agire.
    #
    # ⛔ PERCHE' NON E' UNA LATERAL NEL SELECT, che sarebbe stata la forma
    #    ovvia. `query_paged_view` materializza la CTE `righe` per contare il
    #    totale, quindi una LATERAL nella proiezione si valuta su TUTTO il
    #    perimetro del mese e non sulla pagina. Il costo non e' teorico:
    #    misurato il 2026-09-04 su `2026-06` (48 gruppi), **27 ms senza e
    #    1073 ms con** — quarantuno volte tanto, e cresce con lo storico
    #    perche' la chiave del join esce da un jsonb
    #    (`meta->'context'->>'commessa_id'`) e nessun indice la copre.
    #    Qui la stessa risposta costa **2,8 ms**: una lettura sola, con gli id
    #    della sola pagina.
    #
    # ⚠️ `DISTINCT ON` e non un `GROUP BY`: vale l'ULTIMO rifiuto — quello su
    #    cui si agisce — e senza il collasso una commessa respinta due volte
    #    porterebbe due righe, che nel dizionario diventerebbero una
    #    sovrascrittura silenziosa dell'ordine di arrivo.
    #
    # ⚠️ Il filtro sul MESE non e' ridondante: senza, un rifiuto di agosto
    #    accenderebbe la bandiera su una riga di settembre — un allarme vero
    #    su un lavoro che non c'entra.
    def _applica_bandiera_respinta(
        self,
        righe: list[DashCompetenzaGruppoRow],
        *,
        competenza_mese: date,
    ) -> None:
        commesse_ids = sorted({
            r["commessa_id"] for r in righe if r["commessa_id"] is not None
        })
        if not commesse_ids:
            return

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT ON (commessa_id)
                       commessa_id, respinta_il, dettaglio
                  FROM vendite.vw_dash_commesse_respinte
                 WHERE competenza_mese = %s
                   AND commessa_id = ANY(%s::bigint[])
                 ORDER BY commessa_id, respinta_il DESC
                """,
                [competenza_mese, commesse_ids],
            )
            respinte = {
                int(riga[0]): (riga[1], riga[2]) for riga in cursor.fetchall()
            }

        if not respinte:
            return
        for r in righe:
            if r["commessa_id"] is None:
                continue
            trovata = respinte.get(r["commessa_id"])
            if trovata is None:
                continue
            quando, motivo = trovata
            r["respinta_il"] = quando.isoformat() if quando is not None else None
            r["respinta_motivo"] = None if motivo is None else str(motivo)

    # ═══════════════════════════════════════════════════════════════════════
    # IL CONTORNO DELLA LISTA GRUPPI, IN UNA SOLA LETTURA
    # ═══════════════════════════════════════════════════════════════════════
    # Scopo: tutto cio' che sta INTORNO alla lista — il riepilogo di perimetro,
    #        le tre facet dei filtri e il totale del perimetro base — in UNA
    #        query sola.
    #
    # ⭐ PERCHE' ESISTE. Erano cinque metodi e cinque query, e ognuna rileggeva
    #    `vw_dash_competenza_gruppi` da capo: la vista e' un innesto di una
    #    dozzina di join, quindi la sola cornice della lista pagava ~1,46 s sui
    #    ~2,47 s dell'endpoint (misurato il 2026-08-26 con
    #    `CaptureQueriesContext`). Qui la vista si legge UNA volta e i cinque
    #    conteggi girano su quel materiale: ~0,31 s per tutti e cinque.
    #
    # ⛔ DUE PERIMETRI DENTRO LA STESSA QUERY, ED E' IL PUNTO DA NON SBAGLIARE.
    #    · `base`     = competenza + stadio. Ci girano le TRE FACET e il totale
    #                   di perimetro: le tendine devono mostrare tutte le voci
    #                   anche quando una e' gia' scelta, altrimenti scegliendo
    #                   «Preventivi» le altre sparirebbero e non si potrebbe piu'
    #                   cambiare idea senza azzerare il filtro alla cieca;
    #    · `filtrato` = base PIU' i filtri dell'operatore. Ci gira il RIEPILOGO,
    #                   che deve riconciliare le righe che l'utente ha davanti.
    #    Unificare i due sarebbe la scorciatoia ovvia e romperebbe le tendine in
    #    silenzio: una query sola che risponde a una domanda sola. Presidiato da
    #    `test_due_perimetri_dentro_la_query`.
    #
    # ⚠️ `AS MATERIALIZED` NON e' una vista materializzata: e' un'istruzione al
    #    pianificatore valida per QUESTA query — «questo pezzo calcolalo una
    #    volta e riusalo» — e sparisce con la query. Nessun oggetto nel
    #    database, nessun dato da rinfrescare. Una CTE citata piu' volte sarebbe
    #    materializzata comunque: e' scritto per non dipendere da quella regola,
    #    e perche' dichiara l'intenzione a chi legge.
    #
    # ⛔ `SUM(g.valore)::text` e NON un numero JSON: il valore e' denaro, e un
    #    `numeric` che passa da JSON diventa un float in Python. Un totale
    #    fiscale non passa da un binario a virgola mobile — e' la stessa regola
    #    per cui `valore` esce come stringa da tutte le liste.
    #
    # ⚠️ `jsonb_agg(... ORDER BY ...)` e non un `ORDER BY` sulla CTE: l'ordine
    #    di una CTE non sopravvive all'aggregazione. Le tre clausole sono le
    #    STESSE dei cinque metodi che questo sostituisce, e l'equivalenza delle
    #    uscite e' stata provata sul DB vero su sette perimetri (perimetro vuoto
    #    compreso) prima di rimuoverli.
    # ⚠️ `COALESCE(..., '[]')`: su perimetro vuoto `jsonb_agg` torna NULL, e al
    #    FE arriverebbe `null` dove aspetta una lista.
    def get_dash_competenza_gruppi_accessori(
        self,
        *,
        competenza_mese: date,
        stadio: str | None,
        tipo_gruppo: str | None = None,
        ba_fatturazione_id: int | None = None,
        ba_non_determinabile: bool = False,
        registro_id: int | None = None,
        registro_non_risolvibile: bool = False,
        search: str | None = None,
    ) -> dict[str, Any]:
        cond_base, par_base = self._where_gruppi_base(
            competenza_mese=competenza_mese, stadio=stadio,
        )
        cond_filtri, par_filtri, colonne_filtri = self._where_gruppi_filtri(
            tipo_gruppo=tipo_gruppo,
            ba_fatturazione_id=ba_fatturazione_id,
            ba_non_determinabile=ba_non_determinabile,
            registro_id=registro_id,
            registro_non_risolvibile=registro_non_risolvibile,
            search=search,
        )
        where_base = "WHERE " + " AND ".join(cond_base)
        where_filtri = ("WHERE " + " AND ".join(cond_filtri)) if cond_filtri else ""
        # ⛔ SOLO le colonne che servono, e non `g.*`: su questa vista il costo
        #    dipende da COSA le si chiede — 348 ms per le dodici che servono,
        #    **1052 ms** per `g.*` (misurato). `g.*` era il primo rimedio alla
        #    fragilita' dell'elenco, e costava 0,7 s a ogni caricamento.
        # ⭐ L'elenco non si scrive a mano: e' quello degli AGGREGATI piu' quello
        #    che i filtri attivi DICHIARANO di leggere. Un filtro che non c'e'
        #    non porta le sue colonne — la ricerca libera ne chiede cinque, e
        #    solo quando l'operatore ha davvero digitato qualcosa.
        colonne = list(dict.fromkeys([*_ACCESSORI_COLONNE_AGGREGATI, *colonne_filtri]))
        select_base = ",\n                           ".join(colonne)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                WITH base AS MATERIALIZED (
                    SELECT {select_base}
                      FROM vendite.vw_dash_competenza_gruppi g
                      {where_base}
                ),
                filtrato AS (
                    SELECT g.* FROM base g
                    {where_filtri}
                ),
                riepilogo AS (
                    -- ⭐ 2026-09-09: i tre totali ESCLUDONO i gruppi trattenuti
                    --    da un lotto ancora in gioco — sono lavoro che
                    --    l'operatore non puo' prendere, e un totale che li
                    --    comprende e' la stessa promessa non mantenuta della
                    --    card («4» sopra un elenco che ne mostrava 3).
                    -- ⛔ `FILTER` e mai una `WHERE` sulla CTE: filtrando le
                    --    righe fuori sparirebbero anche dalla LISTA, e la
                    --    decisione D-1 del brief precedente e' che la riga
                    --    RESTA visibile e spenta — sparire non spiega niente.
                    -- ⭐ E `n_gruppi_trattenuti` non e' un di piu': senza, il
                    --    numero cala e nessuno sa di quanto.
                    SELECT COUNT(*) FILTER (WHERE g.emissione_blocco_reason IS NULL)::int
                                                                  AS n_gruppi,
                           COALESCE(SUM(g.n_attivita) FILTER (WHERE g.emissione_blocco_reason IS NULL), 0)::bigint
                                                                  AS n_attivita,
                           COALESCE(SUM(g.valore) FILTER (WHERE g.emissione_blocco_reason IS NULL), 0)::text
                                                                  AS valore,
                           COUNT(*) FILTER (WHERE g.tipo_gruppo = %s
                                              AND g.emissione_blocco_reason IS NULL)::int
                                                                  AS n_gruppi_oneri,
                           COUNT(*) FILTER (WHERE g.emissione_blocco_reason IS NOT NULL)::int
                                                                  AS n_gruppi_trattenuti
                      FROM filtrato g
                ),
                tipi AS (
                    SELECT g.tipo_gruppo,
                           -- valori identici per tipo (la sorgente e' una):
                           -- `bool_and` e non `MIN`, che sui boolean non c'e'.
                           bool_and(g.documento_apribile)         AS documento_apribile,
                           COUNT(*)::int                          AS n_gruppi,
                           COALESCE(SUM(g.n_attivita), 0)::bigint AS n_attivita
                      FROM base g
                     GROUP BY g.tipo_gruppo
                ),
                clienti AS (
                    SELECT g.ba_fatturazione_id,
                           MIN(g.cliente_fatturazione_display)    AS cliente_display,
                           MIN(g.ba_codice_fatturazione)          AS ba_codice_fatturazione,
                           MIN(g.id_fiscale)                      AS id_fiscale,
                           COUNT(*)::int                          AS n_gruppi,
                           COALESCE(SUM(g.n_attivita), 0)::bigint AS n_attivita
                      FROM base g
                     GROUP BY g.ba_fatturazione_id
                ),
                registri AS (
                    SELECT r.id                                   AS registro_id,
                           MIN(rf.codice)                         AS codice,
                           MIN(rf.descrizione)                    AS descrizione,
                           COUNT(*)::int                          AS n_gruppi,
                           COALESCE(SUM(g.n_attivita), 0)::bigint AS n_attivita
                      FROM base g
                      LEFT JOIN LATERAL unnest(g.registri_ids) AS r(id) ON TRUE
                      LEFT JOIN vendite.registri_fatturazione rf ON rf.id = r.id
                     GROUP BY r.id
                )
                SELECT
                    (SELECT to_jsonb(x) FROM riepilogo x),
                    (SELECT COALESCE(jsonb_agg(to_jsonb(x)
                                ORDER BY x.n_gruppi DESC, x.tipo_gruppo ASC),
                             '[]'::jsonb) FROM tipi x),
                    (SELECT COALESCE(jsonb_agg(to_jsonb(x)
                                ORDER BY x.n_gruppi DESC,
                                         x.cliente_display ASC NULLS LAST,
                                         x.ba_fatturazione_id ASC NULLS LAST),
                             '[]'::jsonb) FROM clienti x),
                    (SELECT COALESCE(jsonb_agg(to_jsonb(x)
                                ORDER BY x.n_gruppi DESC,
                                         x.codice ASC NULLS LAST,
                                         x.registro_id ASC NULLS LAST),
                             '[]'::jsonb) FROM registri x),
                    (SELECT COUNT(*)::int FROM base)
                """,  # noqa: S608 — colonne da costante _ACCESSORI_COLONNE_AGGREGATI + _where_gruppi_filtri, WHERE letterali, valori come parametri
                # ⛔ L'ordine segue i SEGNAPOSTO NEL TESTO, non la logica: la
                # CTE `filtrato` sta prima di `riepilogo`, quindi i parametri
                # dei filtri precedono la costante degli oneri. Invertirli non
                # da' errore — confronta il tipo gruppo col valore sbagliato e
                # torna numeri plausibili.
                [*par_base, *par_filtri, TIPO_GRUPPO_ONERI],
            )
            row = cursor.fetchone()
        assert row is not None
        # ⚠️ DECODIFICA ESPLICITA: psycopg 3 in questa configurazione consegna
        #    il `jsonb` come STRINGA, non come oggetto Python (riverificato con
        #    uno smoke sul DB vero il 2026-09-04). Non e' un dettaglio del
        #    driver da dare per scontato — senza, viaggia una stringa dove il FE
        #    aspetta una lista, e non lo segnala nessuno.
        # ⛔ E qui si vede perche' `valore` doveva uscire come TESTO dalla
        #    query: dentro il JSON un `numeric` e' un numero, e `json.loads` lo
        #    trasformerebbe in un **float**. Il denaro sarebbe passato da un
        #    binario a virgola mobile senza che nessuno se ne accorgesse.
        # ⭐ `jsonb_out` e non una funzioncina locale: era una TERZA copia della
        #    stessa decodifica (il BB sta in `apps/core/db/_helpers`, ed e' gia'
        #    importato qui sopra). Stesso comportamento — stringa -> oggetto,
        #    tutto il resto invariato — e una sede sola se il driver cambia idea.
        return {
            "riepilogo": jsonb_out(row[0]),
            "tipi": jsonb_out(row[1]),
            "clienti": jsonb_out(row[2]),
            "registri": jsonb_out(row[3]),
            "n_gruppi_perimetro": int(row[4]),
        }

    # Colonne ordinabili della lista errori vivi (8° lotto liste, 2026-08-03).
    # Alias di output della union: la vista non ha una PK e le colonne di
    # documento sono NULLABLE per costruzione (un errore di task non ha fattura,
    # una fattura critical non ha task) — NULLS LAST e' applicato nel metodo.
    DASH_COMPETENZA_ERRORI_SORT_COLUMNS = {
        "tipo_evento": "tipo_evento",
        "lotto_codice": "lotto_codice",
        "fattura_numero": "fattura_numero",
        "error_code": "error_code",
        "data_evento": "data_evento",
        # Emittente (P-4, Fase E del brief perimetro-emittente): la riga di
        # catalogo e' `ordinabile = t`, e il presidio
        # `test_liste_configurabili_seed` lega catalogo e whitelist nei DUE
        # versi — la chiave e' il CAMPO FISICO, non il `codice` della colonna.
        "emittente_ragione_sociale": "emittente_ragione_sociale",
    }

    # Scopo: Restituisce la lista paginata degli errori vivi (blocco 4 Lente 1:
    #        task run in ERRORE non superati + fatture critical), con filtro
    #        opzionale per mese di competenza.
    # Perimetro: sola lettura su vw_dash_competenza_errori (scope GUC in vista).
    # Risultato: tuple (lista DashCompetenzaErroreRow, conteggio totale).
    def list_dash_competenza_errori(
        self,
        *,
        competenza_mese: date | None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[DashCompetenzaErroreRow], int]:
        conditions: list[str] = []
        params: list[Any] = []
        if competenza_mese is not None:
            # date_trunc simmetrico al conteggio mensile: la competenza dei
            # lotti non e' vincolata al 1° del mese (nessun CHECK sul DB).
            conditions.append("date_trunc('month', e.competenza_mese)::date = %s")
            params.append(competenza_mese)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # La union (anti-join task_runs + LATERAL fatture_log) e' la query piu'
        # costosa della pagina: una sola valutazione + clamp offset via
        # _query_paged_view. La union non ha una PK: tiebreaker deterministico
        # su tutte le chiavi naturali (evento, lotto, fattura, task).
        select_sql = f"""
            SELECT
                e.tipo_evento,
                e.competenza_mese,
                e.lotto_id,
                e.lotto_codice,
                e.stato_lotto,
                e.fattura_id,
                e.fattura_anno,
                e.fattura_serie,
                e.fattura_numero,
                -- Sede unica del numero documento (20260829-15): questa lista
                -- componeva `serie numero/anno` nel .vue, cioe' una delle sei
                -- forme in giro.
                vendite.fn_numero_documento_fattura(e.fattura_numero, e.fattura_serie)
                                             AS fattura_numero_documento,
                e.task_code,
                e.error_code,
                e.messaggio,
                e.data_evento,
                -- Emittente (P-4, Fase E). ⛔ L'alias deve restare
                -- `emittente_ragione_sociale`: e' il `campo_sorgente`
                -- del catalogo, e la lista ha `vista_sql = NULL` —
                -- il campo lo porta questo SELECT o non arriva.
                e.emittente_ragione_sociale,
                -- ⭐ D3 (changeSet 20260904-47): QUALI commesse ha respinto il
                -- giro, non solo quante volte c'e' stato un errore. Un array
                -- jsonb con, per voce, commessa_id, commessa_codice,
                -- error_code, messaggio e dettaglio; vuoto su FATTURA_CRITICA.
                -- ⚠️ Niente parentesi graffe in questo commento: la stringa e'
                --    una f-string, e verrebbero interpolate.
                -- ⛔ La sorgente NON e' `task_run.meta->'commesse_fallite'`,
                --    che il backend tronca a cinque: e' il log di lotto, che ha
                --    una riga per commessa. Con sei respinte, la sesta c'e'.
                -- ⚠️ IN CODA, e non e' estetica: la mappatura qui sotto e' per
                --    INDICE, e infilarle in mezzo sposterebbe di una casella
                --    tutto quello che segue — in silenzio.
                e.commesse_fallite,
                e.n_commesse_fallite
            FROM vendite.vw_dash_competenza_errori e
            {where_clause}
        """  # noqa: S608 — WHERE da clausole letterali con %s, valori come parametri

        # ORDER BY server-side (stessa convenzione delle altre liste dash):
        # colonna dalla whitelist + direzione, NULLS LAST esplicito (le colonne
        # di documento sono NULL su meta' della union — in DESC finirebbero in
        # testa), tiebreak = la catena deterministica storica sulle chiavi
        # naturali. order_by assente -> ordine storico (eventi recenti prima).
        _tiebreak = """tipo_evento ASC,
                     lotto_id ASC NULLS LAST, fattura_id ASC NULLS LAST,
                     task_code ASC NULLS LAST"""
        sort_col = colonna_ordinamento(order_by, self.DASH_COMPETENZA_ERRORI_SORT_COLUMNS)
        if sort_col is not None:
            direction = sql_order_direction_lista(order_by, order_dir, colonne=self.DASH_COMPETENZA_ERRORI_SORT_COLUMNS)
            # Il tiebreak qui e' una catena di chiavi NATURALI (la union non ha
            # una PK): resta fissa, non e' uno spareggio tecnico da allineare.
            #
            # 🔴 Qui c'era un ` NULLS LAST` incollato dopo `{direction}`, e
            #    rendeva questa lista NON ORDINABILE PER NIENTE: `direction`
            #    porta gia' la clausola (`ASC NULLS FIRST` / `DESC NULLS LAST`),
            #    quindi l'SQL usciva `... ASC NULLS FIRST NULLS LAST` e
            #    PostgreSQL rifiutava con un errore di sintassi — 500 su ogni
            #    click di intestazione, su tutte e cinque le colonne.
            #    E' un residuo dell'unificazione dei 29 call-site in
            #    `sql_order_direction` (2026-07-19), che la sua docstring
            #    dichiara: *«3 avevano un NULLS LAST fisso incollato al
            #    template — semantica diversa che qui viene uniformata»*. Su
            #    questo call-site il pezzo vecchio non e' stato tolto.
            #    ⚠️ Nessun presidio poteva vederlo: quello del seed confronta
            #    catalogo e whitelist (statico) e i test mockano
            #    `_query_paged_view`, quindi l'SQL non arriva mai al database.
            #    Trovato provando un ORDER BY vero contro il DB.
            order_clause = f"ORDER BY {sort_col} {direction}, {_tiebreak}"
        else:
            order_clause = f"ORDER BY data_evento DESC NULLS LAST, {_tiebreak}"

        rows, total_count = self._query_paged_view(
            select_sql=select_sql,
            order_by=order_clause,
            params=params,
            limit=limit,
            offset=offset,
        )

        # ⚠️ QUI SI MAPPA ANCORA PER INDICE, ed e' dichiarato invece che
        #    scoperto: `_query_paged_view` (otto chiamanti in questo file, piu'
        #    quelli del core) restituisce tuple, non dict. Il gemello
        #    `list_lotto_fatture` e' passato all'accesso per nome il 2026-08-29
        #    perche' li' il `fetchall` e' locale; qui servirebbe cambiare un
        #    helper condiviso, che e' una decisione di infrastruttura e non di
        #    questo cantiere.
        # ⛔ Finche' resta cosi': aggiungere o togliere una colonna nella SELECT
        #    qui sopra SPOSTA di una casella tutto quello che segue, **senza
        #    nessun errore** — la data finisce nel campo del task, il messaggio
        #    in quello della data. E' successo il 2026-08-29 inserendo
        #    `fattura_numero_documento`. Chi tocca la SELECT ricontrolla gli
        #    indici QUI SOTTO, uno per uno.
        result: list[DashCompetenzaErroreRow] = []
        for row in rows:
            result.append(
                {
                    "tipo_evento": str(row[0]),
                    "competenza_mese": row[1].isoformat() if row[1] is not None else None,
                    "lotto_id": None if row[2] is None else int(row[2]),
                    "lotto_codice": None if row[3] is None else str(row[3]),
                    "stato_lotto": None if row[4] is None else str(row[4]),
                    "fattura_id": None if row[5] is None else int(row[5]),
                    "fattura_anno": None if row[6] is None else int(row[6]),
                    "fattura_serie": None if row[7] is None else str(row[7]),
                    "fattura_numero": None if row[8] is None else int(row[8]),
                    # Numero documento dalla sede unica DB (20260829-15).
                    "fattura_numero_documento": row[9],
                    "task_code": None if row[10] is None else str(row[10]),
                    "error_code": None if row[11] is None else str(row[11]),
                    "messaggio": None if row[12] is None else str(row[12]),
                    "data_evento": row[13].isoformat() if row[13] is not None else None,
                    # Emittente (P-4, Fase E): chiave = `campo_sorgente`
                    # del catalogo, o la colonna resta vuota a video.
                    "emittente_ragione_sociale": row[14],
                    # D3: l'elenco delle commesse respinte dal giro, ognuna
                    # col proprio motivo.
                    # 🔴 `jsonb_out` E NON `row[15]` NUDO. Django/psycopg 3 in
                    #    questa configurazione consegna il `jsonb` come
                    #    STRINGA: senza decodifica il campo arriva al frontend
                    #    come `"[{...}]"` invece che come array — nessun
                    #    errore, una lista che non si puo' ciclare. Misurato
                    #    con uno smoke sul DB vero il 2026-09-04, dopo che i
                    #    test (che consegnano gia' una lista) erano verdi.
                    # ⚠️ Il `or []` resta DOPO la decodifica: il COALESCE della
                    #    vista garantisce `'[]'`, ma un NULL da una riga storica
                    #    non deve far esplodere chi cicla.
                    "commesse_fallite": jsonb_out(row[15]) or [],
                    "n_commesse_fallite": 0 if row[16] is None else int(row[16]),
                }
            )
        return result, total_count

    # Scopo: il `codice` di un registro di fatturazione, per l'etichetta della
    #        riga «Filtri applicati» dell'export. `None` se l'id non esiste.
    # ⚠️ Sta QUI e non nella view: leggere una tabella con SQL grezzo dentro un
    #    layer di presentazione e' il punto da cui nascono le seconde
    #    risoluzioni della stessa regola. `registri_fatturazione` non ha RLS —
    #    e' un catalogo di configurazione — quindi «non trovato» significa
    #    davvero «non esiste».
    def get_registro_codice(self, registro_id: int) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT codice FROM vendite.registri_fatturazione WHERE id = %s",
                [registro_id],
            )
            row = cursor.fetchone()
        return None if row is None else str(row[0])

    # Scopo: Restituisce i contatori del backlog (Lente 2) a grana
    #        classe × area — il pivot per classe (3 classi sempre presenti)
    #        e' a carico del service.
    # Perimetro: sola lettura su vw_dash_backlog_riepilogo (RLS invoker sulle
    #        6 aree documento + rami resi + scope GUC nel resolver commesse).
    # Risultato: lista DashBacklogRiepilogoRow delle sole coppie non vuote.
    def list_dash_backlog_riepilogo(self) -> list[DashBacklogRiepilogoRow]:
        # GREATEST: data_riferimento futura (es. mese esploso contratti o
        # documento post-datato) produrrebbe anzianita' negativa — un "fermo
        # da -N giorni" non ha senso operativo, si legge come 0.
        sql = """
            SELECT
                classe,
                area,
                n_documenti,
                valore_fermo_tot,
                unita_ferme_tot,
                GREATEST(anzianita_max_giorni, 0) AS anzianita_max_giorni
            FROM vendite.vw_dash_backlog_riepilogo
            ORDER BY classe, area
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

        result: list[DashBacklogRiepilogoRow] = []
        for row in rows:
            result.append(
                {
                    "classe": str(row[0]),
                    "area": str(row[1]),
                    "n_documenti": int(row[2]),
                    "valore_fermo_tot": str(row[3]) if row[3] is not None else None,
                    "unita_ferme_tot": int(row[4]) if row[4] is not None else 0,
                    "anzianita_max_giorni": None if row[5] is None else int(row[5]),
                }
            )
        return result

    # Scopo: Restituisce la lista paginata del backlog (Lente 2): documenti
    #        non-collegati non-verdi ordinati per anzianita' (i piu' vecchi
    #        prima — l'ordinamento e' BE-side per contratto, le viste non
    #        garantiscono ORDER; si ordina su data_riferimento ASC, colonna
    #        base equivalente ad anzianita' DESC ma piu' amichevole per il
    #        planner), con filtri opzionali per classe e area. Il filtro
    #        classe NON e' whitellistato: coerenza fail-visible col riepilogo
    #        (una classe futura del CHECK resta drillabile; sconosciuta =>
    #        lista vuota, mai 400).
    # Perimetro: sola lettura su vw_dash_backlog_documenti (union resolver:
    #        RLS invoker + scope GUC commesse). Una sola valutazione della
    #        union + clamp offset via _query_paged_view.
    # Risultato: tuple (lista DashBacklogDocumentoRow, conteggio totale).
    # Colonne ordinabili del backlog fatturazione: chiave FE (field della colonna
    # DataTable) -> colonna della CTE `righe`. Whitelist: nell'ORDER BY entrano
    # solo chiavi note + direzione ASC/DESC (no SQL injection). Convenzione
    # order_by/order_dir come le liste standard, gemella di DASH_APERTO_SORT_COLUMNS.
    DASH_BACKLOG_SORT_COLUMNS = {
        "anzianita_giorni": "anzianita_giorni",
        "area": "area",
        "codice": "codice",
        "cliente_display": "cliente_display",
        "valore_fermo": "valore_fermo",
        "stato_codice": "stato_codice",
        # Estesa 2026-08-03 (passata BE dashboard, 8° lotto liste): la classe di
        # azionabilita' e' colonna a video (Tag) e vocabolario chiuso a 3 valori —
        # ordinarla raggruppa il lavoro per tipo di intervento.
        "classe": "classe",
        # Emittente (P-4, Fase E del brief perimetro-emittente): la riga di
        # catalogo e' `ordinabile = t`, e il presidio
        # `test_liste_configurabili_seed` lega catalogo e whitelist nei DUE
        # versi — la chiave e' il CAMPO FISICO, non il `codice` della colonna.
        "emittente_ragione_sociale": "emittente_ragione_sociale",
    }

    def list_dash_backlog_documenti(
        self,
        *,
        classe: str | None,
        area: str | None,
        ritardo_giorni: int | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[DashBacklogDocumentoRow], int]:
        conditions: list[str] = []
        params: list[Any] = []
        if classe is not None:
            conditions.append("d.classe = %s")
            params.append(classe)
        if area is not None:
            conditions.append("d.area = %s")
            params.append(area)
        # Filtro "fermo da oltre N giorni" su data documento — stessa semantica e
        # stesso SQL della Situazione aperta (DL-17). Solo sulla lista: le card
        # per classe restano la fotografia completa. Le righe con data ignota
        # (data_riferimento NULL, anzianita_giorni NULL) sono escluse dal
        # confronto — coerente: "fermo da N giorni" richiede un'età nota.
        if ritardo_giorni is not None:
            conditions.append(
                "d.data_riferimento <= (SELECT script.fn_data_operativa()) - make_interval(days => %s)"
            )
            params.append(ritardo_giorni)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        select_sql = f"""
            SELECT
                d.area,
                d.competenza_mese,
                d.documento_id,
                d.documento_uid,
                d.codice,
                d.cliente_display,
                d.valore_fermo,
                d.unita_ferme,
                d.motivo_fermo,
                d.classe,
                d.azione,
                d.data_riferimento,
                GREATEST(d.anzianita_giorni, 0) AS anzianita_giorni,
                d.stato_codice_interno,
                d.stato_codice,
                d.fase,
                -- Emittente (P-4, Fase E). ⛔ L'alias deve restare
                -- `emittente_ragione_sociale`: e' il `campo_sorgente`
                -- del catalogo, e la lista ha `vista_sql = NULL` —
                -- il campo lo porta questo SELECT o non arriva.
                d.emittente_ragione_sociale
            FROM vendite.vw_dash_backlog_documenti d
            {where_clause}
        """  # noqa: S608 — WHERE da clausole letterali con %s, valori come parametri

        # ORDER BY server-side (corretto su TUTTE le pagine): colonna dalla
        # whitelist DASH_BACKLOG_SORT_COLUMNS + direzione ASC/DESC, tiebreak
        # stabile (area, documento_id). order_by assente/non ammesso -> ordine
        # storico "fermo da" (i piu' vecchi prima).
        sort_col = colonna_ordinamento(order_by, self.DASH_BACKLOG_SORT_COLUMNS)
        if sort_col is not None:
            direction = sql_order_direction_lista(order_by, order_dir, colonne=self.DASH_BACKLOG_SORT_COLUMNS)
            tiebreak_dir = sql_tiebreak_direction(direction)
            order_clause = (
                f"ORDER BY {sort_col} {direction}, "
                f"area ASC, documento_id {tiebreak_dir}"
            )
        else:
            order_clause = """
            ORDER BY data_riferimento ASC NULLS LAST,
                     valore_fermo DESC NULLS LAST,
                     area ASC, documento_id ASC
            """

        rows, total_count = self._query_paged_view(
            select_sql=select_sql,
            order_by=order_clause,
            params=params,
            limit=limit,
            offset=offset,
        )

        result: list[DashBacklogDocumentoRow] = []
        for row in rows:
            result.append(
                {
                    "area": str(row[0]),
                    "competenza_mese": row[1].isoformat() if row[1] is not None else None,
                    "documento_id": int(row[2]),
                    "documento_uid": None if row[3] is None else str(row[3]),
                    "codice": None if row[4] is None else str(row[4]),
                    "cliente_display": None if row[5] is None else str(row[5]),
                    "valore_fermo": str(row[6]) if row[6] is not None else None,
                    "unita_ferme": None if row[7] is None else int(row[7]),
                    "motivo_fermo": str(row[8]),
                    "classe": str(row[9]),
                    "azione": None if row[10] is None else str(row[10]),
                    "data_riferimento": row[11].isoformat() if row[11] is not None else None,
                    "anzianita_giorni": None if row[12] is None else int(row[12]),
                    "stato_codice_interno": None if row[13] is None else str(row[13]),
                    "stato_codice": None if row[14] is None else str(row[14]),
                    "fase": None if row[15] is None else str(row[15]),
                    # Emittente (P-4, Fase E): chiave = `campo_sorgente`
                    # del catalogo, o la colonna resta vuota a video.
                    "emittente_ragione_sociale": row[16],
                }
            )
        return result, total_count

    # Colonne ordinabili dell'elenco «fondi da decidere»: chiave FE (field della
    # colonna a video) -> colonna di output della vista. Whitelist: nell'ORDER BY
    # entrano solo chiavi note + direzione ASC/DESC.
    # ⚠️ `importo_proposto` e' NULL fuori dal ramo che lo produce
    # (PROPOSTA_SENZA_ATTO): ordinarlo e' lecito e i vuoti finiscono dove
    # `sql_order_direction` mette i NULL — in fondo ordinando DESC, che e'
    # quello che serve a chi cerca gli importi. `capienza_attuale` invece e'
    # calcolata su TUTTI i rami (fn_saldo_sorgente_fondo fa COALESCE): mai NULL.
    # ⚠️ `stato_atto` vale `'DISPONIBILE'` sul solo ramo NON_PIU_CAPIENTE (dove
    # la vista filtra `s.stato = 'DISPONIBILE'`) ed e' `NULL::varchar` per
    # COSTRUZIONE sugli altri: la colonna ha DUE valori, non uno, e ordinarla
    # separa le righe con un atto vivo da quelle senza — che e' informazione
    # vera, non un flag alzato per far tacere il presidio dei seed.
    # 📌 Sui NULL non serve nessun `NULLS LAST` scritto a mano: la direzione la
    # produce `sql_order_direction`, che ritorna gia' `ASC NULLS FIRST` /
    # `DESC NULLS LAST` (il vuoto sta dove starebbe lo zero) proprio perche' i
    # default di PostgreSQL sono l'opposto.
    FONDI_DA_DECIDERE_SORT_COLUMNS: dict[str, str] = {
        "data": "data",
        "motivo": "motivo",
        "anno": "anno",
        "numero": "numero",
        "totale_a_pagare": "totale_a_pagare",
        "importo_proposto": "importo_proposto",
        "capienza_attuale": "capienza_attuale",
        "stato_atto": "stato_atto",
    }

    # Colonne dell'elenco, NELL'ORDINE: un'unica tupla costruisce sia il SELECT
    # sia il dict di riga (zip), cosi' aggiungere/spostare una colonna non puo'
    # disallineare indice e nome — con 22 colonne quasi tutte nullable e coercite
    # (str/int), uno shift servirebbe dati SBAGLIATI senza nessuna eccezione.
    _FONDI_DA_DECIDERE_COLONNE: tuple[str, ...] = (
        "motivo",
        "fattura_sorgente_id",
        "anno",
        "serie",
        "numero",
        "data",
        "totale_a_pagare",
        "billing_account_id",
        "utility_id",
        "tipo_doc_fiscale_id",
        "emittente_soggetto_ruolo_id",
        "valuta_id",
        "tipo_fondo_fattura_id",
        "tipo_fondo_codice_interno",
        "fondo_source_id",
        "origine",
        "stato_atto",
        "importo_atto",
        "atto_motivo",
        "atto_data",
        "importo_proposto",
        "capienza_attuale",
    )

    # Coercizioni per colonna (chi manca resta com'e'): interi per gli id,
    # ISO per le date, str per i numeric (envelope JSON senza float).
    _FONDI_DA_DECIDERE_COERCE: dict[str, Any] = {
        "motivo": str,
        "fattura_sorgente_id": int,
        "anno": lambda v: None if v is None else int(v),
        "serie": lambda v: None if v is None else str(v),
        "numero": lambda v: None if v is None else str(v),
        "data": iso_or_none,
        "totale_a_pagare": lambda v: None if v is None else str(v),
        "billing_account_id": lambda v: None if v is None else int(v),
        "utility_id": lambda v: None if v is None else int(v),
        "tipo_doc_fiscale_id": lambda v: None if v is None else int(v),
        "emittente_soggetto_ruolo_id": lambda v: None if v is None else int(v),
        "valuta_id": lambda v: None if v is None else int(v),
        "tipo_fondo_fattura_id": lambda v: None if v is None else int(v),
        "tipo_fondo_codice_interno": lambda v: None if v is None else str(v),
        "fondo_source_id": lambda v: None if v is None else int(v),
        "origine": lambda v: None if v is None else str(v),
        "stato_atto": lambda v: None if v is None else str(v),
        "importo_atto": lambda v: None if v is None else str(v),
        "atto_motivo": lambda v: None if v is None else str(v),
        "atto_data": iso_or_none,
        "importo_proposto": lambda v: None if v is None else str(v),
        "capienza_attuale": lambda v: None if v is None else str(v),
    }

    # Scopo: 🔴 Il cancello del CANALE, sede unica (regola del 2, 2026-08-31:
    #        seconda occorrenza scrivendo `cancella_fondo_fattura`).
    # Obiettivo: rifiutare la chiamata quando la connessione ha un ruolo
    #        BYPASSRLS. Vale per ogni percorso che si appoggia alla row
    #        security invece di filtrare da se': viste `security_invoker`,
    #        funzioni `SECURITY INVOKER`, letture dirette di tabelle con
    #        policy. Su un canale di sistema quel perimetro non c'e', e il
    #        filtro applicativo no-opa con `auth_user_id = None` — che e' anche
    #        il valore legittimo del superuser, quindi non discrimina.
    # ⚠️ PERCHE' IN UNA SEDE SOLA: il difetto che previene non fallisce, RIESCE.
    #        Su una lettura mostra i dati di tutti gli emittenti, su una
    #        scrittura li tocca. Un guard riscritto a mano ogni volta e' un
    #        guard che alla terza volta qualcuno non scrive — e nessun test se
    #        ne accorge, perche' il caso non solleva niente.
    # ⭐ Il messaggio resta PARAMETRICO e non generico: «non disponibile dal
    #        canale di sistema» senza dire QUALE gesto e su quale oggetto non
    #        aiuta chi legge il log. Si unifica la meccanica, non la ragione.
    def _require_canale_utente(self, *, gesto: str, oggetto: str, metodo: str) -> None:
        ErrorManager.require(
            not connection_role_bypasses_rls(),
            code="E_VENDITE_VALIDATION",
            message=f"{gesto} non disponibile dal canale di sistema.",
            detail=(
                f"{oggetto} si appoggia alla row security per il perimetro "
                "emittente: da un ruolo BYPASSRLS quel perimetro non si "
                "applica. Usare la connessione dell'utente della richiesta."
            ),
            function_name=f"vendite.vendite_repository.{metodo}",
        )

    # Scopo: Restituisce l'elenco paginato dei casi di fondo fattura che
    #        chiedono una persona (`vendite.vw_fondi_fattura_da_decidere`),
    #        filtrabile per motivo.
    # Obiettivo: sola lettura. L'elenco PRESENTA e non sana: nessuna riga qui ha
    #        un gemello automatico che la corregge — sanarle vorrebbe dire
    #        muovere denaro senza che nessuno l'abbia deciso.
    # Perimetro: nessun side-effect, nessun ricalcolo in Python. La proposta la
    #        da' `fn_fondo_fattura_proponibile` e la capienza
    #        `fn_check_fondo_fattura_capiente` — le STESSE che usano il giro
    #        notturno — quindi l'elenco non puo' raccontare una cosa diversa da
    #        quello che la pipeline fa davvero.
    # Risultato: tuple (lista FondoFatturaDaDecidereRow, conteggio totale).
    #
    # ⚠️ SCOPE. La vista e' `security_invoker=on`: il perimetro emittente lo
    # applica la RLS di `vendite.fatture` con l'identita' dell'utente della
    # richiesta. Il filtro applicativo qui sotto e' DEFENSE-IN-DEPTH e si somma,
    # com'e' la convenzione del progetto. 🔴 Ne discende che questo metodo NON
    # va chiamato su una connessione con ruolo `BYPASSRLS`: li' la vista
    # perderebbe il suo unico cancello e l'elenco mostrerebbe i fondi di tutti
    # gli emittenti. ⚠️ Il gateway applicativo che apriva un canale simile e'
    # stato ritirato il 2026-09-05, ma il guard resta: difende dalla
    # CONFIGURAZIONE (un `DB_USER` puntato al ruolo sbagliato), non solo da un
    # chiamante distratto.
    def list_fondi_fattura_da_decidere(
        self,
        *,
        motivo: str | None = None,
        auth_user_id: int | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[FondoFatturaDaDecidereRow], int]:
        # 🔴 Guard strutturale, non un commento: su un ruolo BYPASSRLS il
        # `security_invoker` della vista non filtra niente e il filtro
        # applicativo sotto no-opa con auth_user_id=None (che e' anche il
        # valore legittimo del superuser: non discrimina). Un consumer headless
        # su un ruolo `BYPASSRLS` leggerebbe i fondi di TUTTI gli emittenti
        # senza che nulla fallisca.
        self._require_canale_utente(
            gesto="Elenco fondi da decidere",
            oggetto="La vista vw_fondi_fattura_da_decidere e' security_invoker e",
            metodo="list_fondi_fattura_da_decidere",
        )
        conditions: list[str] = []
        params: list[Any] = []
        if motivo is not None:
            conditions.append("v.motivo = %s")
            params.append(motivo)
        # Convenzione SR: la vista espone `emittente_soggetto_ruolo_id`.
        add_emittente_scope_condition(
            conditions,
            params,
            auth_user_id=auth_user_id,
            column="v.emittente_soggetto_ruolo_id",
            convention="sr",
        )
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # SELECT costruito dalla STESSA tupla che fa da chiave al mapping di
        # riga: colonne e nomi non possono disallinearsi.
        select_cols = ",\n                ".join(
            f"v.{col}" for col in self._FONDI_DA_DECIDERE_COLONNE
        )
        select_sql = f"""
            SELECT
                {select_cols}
            FROM vendite.vw_fondi_fattura_da_decidere v
            {where_clause}
        """  # noqa: S608 — colonne da costante _FONDI_DA_DECIDERE_COLONNE, WHERE letterale + BB scope emittente, valori come parametri

        # ORDER BY server-side (corretto su TUTTE le pagine). Default: le fatture
        # piu' recenti prima — l'elenco non e' una coda per anzianita', e' la
        # lista di cio' che il giro ha lasciato a una persona.
        # ⚠️ Tiebreak DETERMINISTICO su (fattura_sorgente_id, fondo_source_id):
        # la sola fattura non basta, perche' sul ramo NON_PIU_CAPIENTE una
        # sorgente puo' portare piu' di un atto vivo (l'indice parziale
        # `uq_fondi_source_atto_vivo_automatico` presidia i soli AUTOMATICI).
        # `COALESCE(..., 0)` perche' negli altri tre rami l'atto non esiste.
        sort_col = colonna_ordinamento(order_by, self.FONDI_DA_DECIDERE_SORT_COLUMNS)
        direction = sql_order_direction(order_dir, default_desc=True)
        tiebreak_dir = sql_tiebreak_direction(direction)
        order_clause = (
            f"ORDER BY {sort_col or 'data'} {direction}, "
            f"fattura_sorgente_id {tiebreak_dir}, "
            f"COALESCE(fondo_source_id, 0) {tiebreak_dir}"
        )

        rows, total_count = self._query_paged_view(
            select_sql=select_sql,
            order_by=order_clause,
            params=params,
            limit=limit,
            offset=offset,
        )

        # Mapping per NOME via zip sulla tupla condivisa col SELECT (niente
        # indici posizionali) + coercizioni dichiarate per colonna.
        # `strict=False` e' voluto: `query_paged_view` appende una colonna in
        # coda (`total_count`, gia' estratta nel totale) che qui si scarta.
        result: list[FondoFatturaDaDecidereRow] = []
        for row in rows:
            record = dict(zip(self._FONDI_DA_DECIDERE_COLONNE, row, strict=False))
            for campo, coerce in self._FONDI_DA_DECIDERE_COERCE.items():
                record[campo] = coerce(record[campo])
            result.append(record)  # type: ignore[arg-type]
        return result, total_count

    # Scopo: Cancella un atto di fondo fattura via la madre DB
    #        `vendite.fn_cancella_fondo_fattura` (D-21 di
    #        brief-db-fondo-fattura-ricalcolo-e-governo §9.3).
    # Obiettivo: UNA sola `SELECT`. Il criterio («il denaro non si e' ancora
    #        mosso, e la fattura che ha ricevuto il fondo e' ancora
    #        modificabile») sta nel predicato `fn_check_fondo_cancellabile`, che
    #        la madre legge una volta sola: riscriverlo qui sarebbe una seconda
    #        implementazione, e la divergenza sarebbe silenziosa.
    # Perimetro: i tre `DELETE` nell'ordine che la FK `NO ACTION` impone li fa
    #        il database, in transazione sua. ⛔ Niente `transaction.atomic()`
    #        con piu' chiamate: sarebbe una seconda implementazione di
    #        un'atomicita' che il database gia' garantisce.
    # Risultato: dict con i tre contatori di cio' che e' stato cancellato.
    #
    # 🔴 GUARD DI CANALE, ed e' lo stesso di `list_fondi_fattura_da_decidere`
    # ma pesa di piu': la madre e' `SECURITY INVOKER` e si appoggia alla row
    # security di `fatture_fondi_fattura_source` (accesa il 2026-08-31, D-20).
    # E' quella policy a rendere vera la frase «non esiste **o** non e' tuo»:
    # su un ruolo BYPASSRLS il perimetro sparisce, e qui non si leggerebbe
    # l'atto di un altro emittente — lo si **cancellerebbe**.
    def cancella_fondo_fattura(self, source_id: int) -> dict[str, int]:
        self._require_canale_utente(
            gesto="Cancellazione del fondo",
            oggetto="La funzione fn_cancella_fondo_fattura e' SECURITY INVOKER e",
            metodo="cancella_fondo_fattura",
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT deleted_righe, deleted_fondi, deleted_source
                FROM vendite.fn_cancella_fondo_fattura(%s::bigint)
                """,
                [source_id],
            )
            row = cursor.fetchone()
            assert row is not None
        return {
            "deleted_righe": int(row[0]),
            "deleted_fondi": int(row[1]),
            "deleted_source": int(row[2]),
        }

    # Scopo: Restituisce elenco fatture di un lotto con decodifiche e filtri opzionali.
    # Obiettivo: lista paginata per lotto_id con JOIN anagrafiche, SDI, stato doc fiscale.
    # Perimetro: sola lettura; nessun side-effect.
    # Risultato: tuple (lista LottoFattureRow, conteggio totale).
    def list_lotto_fatture(
        self,
        *,
        lotto_id: int,
        stato_esecuzione: str | None,
        auth_user_id: int | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
        max_rows: int | None = None,
    ) -> tuple[list[LottoFattureRow], int]:
        # ⚠️ DUE TETTI, e la differenza e' voluta: la PAGINA si ferma a
        # `MAX_LIMIT`, l'EXPORT salta la paginazione e arriva al tetto
        # dell'esportazione. Senza `max_rows` un file di 3.000 righe uscirebbe
        # troncato a 200 senza dirlo — e un export troncato in silenzio somiglia
        # in tutto a un export completo.
        tetto = _LOTTO_EXPORT_MAX_ROWS if max_rows else MAX_LIMIT
        safe_limit, safe_offset = limiti_pagina(max_rows or limit, offset, tetto=tetto)

        # Ordinamento: solo valori dalla whitelist entrano nella query — BB
        # `sql_order_clause` (NULL come valore minimo; tiebreak `fattura_id`
        # allineato alla direzione, e omesso quando e' gia' la colonna scelta).
        order_clause = sql_order_clause(
            order_by, order_dir,
            colonne=LOTTO_FATTURE_SORT_COLUMNS, default="fllf.fattura_id",
            colonne_desc=LOTTO_FATTURE_SORT_COLONNE_DATA, tiebreak="fllf.fattura_id",
        )

        # WHERE obbligatorio su lotto_id; filtri opzionali aggiunti dinamicamente.
        conditions: list[str] = ["fllf.lotto_id = %s"]
        params: list[Any] = [lotto_id]

        if stato_esecuzione is not None:
            conditions.append("fllf.stato_esecuzione = %s")
            params.append(stato_esecuzione)

        self._add_scope_emittente(
            auth_user_id, "f.emittente_soggetto_ruolo_id", conditions, params
        )

        where_clause = "WHERE " + " AND ".join(conditions)

        joins = """
            INNER JOIN vendite.fatture f
                ON f.id = fllf.fattura_id
            INNER JOIN anagrafiche.billing_account ba
                ON ba.id = f.billing_account_id
            INNER JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srd
                ON srd.soggetto_ruolo_id = ba.soggetto_ruolo_id
            LEFT JOIN config.stati_sdi ssdi
                ON ssdi.id = fllf.stato_sdi_id
            LEFT JOIN config.stati_doc_fiscale sdf
                ON sdf.id = fllf.stato_doc_fiscale_id
            LEFT JOIN config.nature_doc_fiscale ndf
                ON ndf.id = f.natura_doc_id
        """

        # ⭐ IL MOTIVO DELL'AZIONE SPENTA, dalla sede che rifiuta (F5,
        # 2026-08-31). `fn_check_fattura_eliminabile_da_lotto` e' `STABLE` e
        # PURA — nessun raise di dominio, ritorna `[]` oppure l'array ORDINATO
        # dei motivi — ed e' nata dichiarando due consumatori: la madre che
        # solleva, «e il BE, per spiegare invece di far fallire». Il secondo
        # non esisteva.
        #
        # ⚠️ Si prende il PRIMO motivo e non tutti: e' lo stesso che la madre
        # solleva, quindi il tooltip dice esattamente la frase che l'operatore
        # leggerebbe tentando. L'ordine dell'array e' contratto della funzione.
        #
        # ⛔ La funzione non puo' sollevare da qui: sui suoi due guard di
        # parametro gli id arrivano da una FK, e i suoi due «non trovato» sono
        # irraggiungibili perche' la lista fa `INNER JOIN vendite.fatture` —
        # una fattura fuori scope RLS non produce nemmeno la riga.
        # Il frammento e' il BB `sql_lateral_primo_motivo` (core/db): qui si
        # proiettano solo `reason` e `reason_key`, il `dettaglio` resta nel
        # blocco e non viaggia.
        reset_lateral = sql_lateral_primo_motivo(
            "script.fn_check_fattura_eliminabile_da_lotto(fllf.lotto_id, fllf.fattura_id)",
            "reset_cap",
        )

        # ⭐ LA SEGNALAZIONE ATTACCATA ALLA RIGA (D-6 del brief liste drawer
        # lotto, 2026-08-22). La colonna `stato_esecuzione` dice CHE la fattura
        # e' fallita; da sola non dice perche', e il motivo viveva solo nel
        # toast del momento — cioe' in nessun posto, un minuto dopo.
        #
        # ⭐ LA REGOLA E' «L'ULTIMA VIVA, DALLE PIU' GRAVI», e le due meta'
        # contano entrambe: si guardano TUTTI i livelli, non solo i critici, e
        # a parita' vince la GRAVITA' prima della data. Un documento con un
        # avviso di ieri e nessun critico ha qualcosa da dire, e prima non lo
        # diceva; uno con un critico di ieri e un avviso di oggi deve mostrare
        # il critico, non l'avviso.
        #
        # ⚠️ LATERAL e non un JOIN semplice: di segnalazioni una fattura ne ha
        # 0..n e ne serve UNA. Con un JOIN normale una fattura con tre
        # segnalazioni comparirebbe tre volte nell'elenco del lotto.
        # ⚠️ Sta FUORI da `joins` di proposito: `count_sql` conta le righe del
        # lotto e non ha bisogno del messaggio — un LATERAL nel COUNT sarebbe
        # lavoro per niente su ogni pagina.
        # 📌 `disabilitato IS NOT TRUE`: «chi alza la bandiera la abbassa» — una
        # segnalazione ritirata da chi l'ha scritta non deve piu' comparire.
        errore_lateral = """
            LEFT JOIN LATERAL (
                SELECT fl.status, fl.messaggio, fl.data_ora, fl.meta
                  FROM vendite.fatture_log fl
                 WHERE fl.fattura_id = fllf.fattura_id
                   AND fl.disabilitato IS NOT TRUE
                 ORDER BY CASE fl.status
                              WHEN 'C' THEN 3
                              WHEN 'W' THEN 2
                              WHEN 'I' THEN 1
                              ELSE 0
                          END DESC,
                          fl.data_ora DESC,
                          fl.id DESC
                 LIMIT 1
            ) err ON TRUE
        """

        count_sql = f"""
            SELECT COUNT(*)
            FROM vendite.fatturazione_lotti_fatture fllf
            {joins}
            {where_clause}
        """  # noqa: S608 — JOIN letterali, WHERE letterale + BB scope emittente, valori come parametri

        data_sql = f"""
            SELECT
                fllf.id,
                fllf.lotto_id,
                fllf.fattura_id,
                fllf.stato_sdi_id,
                ssdi.descrizione        AS stato_sdi_descrizione,
                fllf.stato_doc_fiscale_id,
                sdf.descrizione         AS stato_doc_fiscale_descrizione,
                fllf.stato_esecuzione,
                f.numero,
                f.serie,
                -- Sede unica del numero documento (20260829-15).
                vendite.fn_numero_documento_fattura(f.numero, f.serie)
                                        AS numero_documento,
                f.data,
                f.billing_account_id,
                f.totale_doc,
                f.totale_a_pagare,
                srd.soggetto_id,
                srd.ragione_sociale_completa,
                srd.id_fiscale_univoco_cf_piva,
                sdf.codice_interno      AS stato_doc_fiscale_codice,
                -- ⚠️ Un lotto puo' contenere documenti di NATURA DIVERSA: la
                -- nota di credito nasce nello stesso giro della fattura e il
                -- verbo «numera» le numera entrambe, sui rispettivi registri
                -- (§12.4-bis.8). Senza questa decodifica il drawer del lotto
                -- non «assume» che siano tutte fatture: non ha il dato.
                -- ⭐ Nome fedele dal 2026-08-29, e le due meta' sono andate
                -- INSIEME: il `campo_sorgente` del seed `ui.lista_colonna`
                -- id 494 e questo alias. ⛔ Una sola delle due svuota la
                -- colonna «Natura» del drawer lotto — il catalogo chiede un
                -- nome che il payload non porta, e non lo dice nessuno.
                ndf.codice_interno      AS natura_doc_codice_interno,
                ndf.descrizione         AS natura_doc_descrizione,
                err.messaggio           AS errore_messaggio,
                err.data_ora            AS errore_quando,
                err.meta                AS errore_meta,
                -- ⚠️ Il LIVELLO non e' una colonna del seed ma serve al FE per
                -- scegliere la severita': senza, l'icona di riga sarebbe rossa
                -- anche su un avviso, cioe' direbbe «errore» dove errore non
                -- c'e'. Stesso ruolo di `natura_doc_codice`, colonna di
                -- supporto invisibile del seed.
                err.status              AS errore_livello,
                -- ⭐ LA CAPABILITY DELLA RIGA (F5, 2026-08-31): «questa fattura
                -- si puo' riportare in lavorazione?» e, se no, PERCHE'.
                -- ⛔ Il backend TRASPORTA, non deduce: il motivo lo produce
                -- `script.fn_check_fattura_eliminabile_da_lotto`, cioe' la
                -- STESSA funzione che `fn_elimina_fattura_da_lotto` usa per
                -- rifiutare (ne solleva il codice del primo motivo). Cosi'
                -- tooltip e rifiuto non «coincidono oggi»: non possono
                -- divergere. Ricalcolare la condizione qui sarebbe la forma in
                -- cui i due si sfilano in silenzio.
                -- ⭐ E toglie la NONA copia della soglia di congelamento: il
                -- frontend aveva la sua `PRE_FISCALI = ['DRAFT','EMESSA']`
                -- scritta a mano in un template Vue, dove il database non la
                -- vede. La funzione legge `congela_fiscale` (D33), quindi la
                -- sede torna a essere una sola.
                -- ⚠️ Il flag si DERIVA dal motivo (`reason IS NULL`), non si
                -- calcola a parte: due sorgenti per la stessa risposta sono
                -- due risposte che prima o poi differiscono.
                (reset_cap.reason IS NULL) AS can_reset_fattura,
                reset_cap.reason           AS can_reset_fattura_reason,
                reset_cap.reason_key       AS can_reset_fattura_reason_key
            FROM vendite.fatturazione_lotti_fatture fllf
            {joins}
            {errore_lateral}
            {reset_lateral}
            {where_clause}
            ORDER BY {order_clause}
            LIMIT %s OFFSET %s
        """  # noqa: S608 — JOIN/LATERAL letterali, ORDER BY da whitelist LOTTO_FATTURE_SORT_COLUMNS, valori come parametri

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, params + [safe_limit, safe_offset])
            # ⛔ PER NOME, non per indice, ed e' una correzione del 2026-08-29.
            #    Questo dict era costruito con `row[0]`, `row[1]`…: inserire una
            #    colonna in mezzo alla SELECT sposta di una casella TUTTO quello
            #    che segue, e non da' nessun errore — mette la data nel campo del
            #    billing account e il totale in quello del soggetto. E' successo
            #    davvero aggiungendo `numero_documento`, e una riga FUORI dal
            #    blocco (`errore_meta`) era sfuggita anche alla correzione.
            #    ⭐ L'accesso per nome e' gia' l'idioma di questo file
            #    (`row_to_dict` due metodi piu' su): qui era l'eccezione.
            rows = rows_to_list(cursor)

        result: list[LottoFattureRow] = []
        for row in rows:
            # `errore_meta` arriva decodificato dal lettore comune; NULL = nessun
            # errore.
            errore_meta = row["errore_meta"] or {}
            result.append(
                {
                    "id": int(row["id"]),
                    "lotto_id": int(row["lotto_id"]),
                    "fattura_id": int(row["fattura_id"]),
                    "stato_sdi_id": None if row["stato_sdi_id"] is None else int(row["stato_sdi_id"]),
                    "stato_sdi_descrizione": row["stato_sdi_descrizione"],
                    "stato_doc_fiscale_id": None if row["stato_doc_fiscale_id"] is None else int(row["stato_doc_fiscale_id"]),
                    "stato_doc_fiscale_descrizione": row["stato_doc_fiscale_descrizione"],
                    "stato_esecuzione": str(row["stato_esecuzione"]),
                    "numero": None if row["numero"] is None else int(row["numero"]),
                    "serie": row["serie"],
                    # Numero documento dalla sede unica DB (20260829-15).
                    "numero_documento": row["numero_documento"],
                    "data": row["data"].isoformat() if row["data"] is not None else None,
                    "billing_account_id": int(row["billing_account_id"]),
                    "totale_doc": str(row["totale_doc"]) if row["totale_doc"] is not None else None,
                    "totale_a_pagare": str(row["totale_a_pagare"]) if row["totale_a_pagare"] is not None else None,
                    "soggetto_id": int(row["soggetto_id"]),
                    "ragione_sociale_completa": row["ragione_sociale_completa"],
                    "id_fiscale_univoco_cf_piva": row["id_fiscale_univoco_cf_piva"],
                    "stato_doc_fiscale_codice": row["stato_doc_fiscale_codice"],
                    "natura_doc_codice_interno": row["natura_doc_codice_interno"],
                    "natura_doc_descrizione": row["natura_doc_descrizione"],
                    "errore_messaggio": row["errore_messaggio"],
                    "errore_quando": row["errore_quando"].isoformat() if row["errore_quando"] is not None else None,
                    # Il codice sta nel `meta` di chi ha scritto la riga: dice
                    # DI CHE errore si tratta, non solo che c'e'. `jsonb_out`
                    # perche' dal cursore RAW il jsonb arriva come stringa.
                    "errore_codice": errore_meta.get("error_code"),
                    # ⭐ IL BERSAGLIO dell'errore persistito (2026-08-24): su
                    # QUALE cosa, cosi' che l'icona di riga possa offrire un
                    # gesto e non solo una lettura. Stessa borsa `meta` del
                    # codice qui sopra — il canale c'era gia', mancava cosa
                    # metterci. Forma: `[{"type": "FATTURA", "id": "820"}]`.
                    # Brief: `brief-db-bersaglio-errore.md` §7-bis (B7).
                    "errore_bersagli": errore_meta.get("bersagli"),
                    "errore_livello": row["errore_livello"],
                    # ⭐ Capability di riga (F5): permesso => nascondi, stato =>
                    # disabilita COL MOTIVO. Qui e' sempre il secondo caso, ed
                    # e' la ragione per cui il motivo viaggia: un pulsante
                    # grigio che non spiega niente e' indistinguibile da un bug.
                    # ⛔ Viaggia la CHIAVE i18n, mai il testo: il messaggio e'
                    # multilingua e vive nei `locales`.
                    "can_reset_fattura": bool(row["can_reset_fattura"]),
                    "can_reset_fattura_reason": row["can_reset_fattura_reason"],
                    "can_reset_fattura_reason_key": row["can_reset_fattura_reason_key"],
                }
            )
        return result, total_count

    # Scopo: I DOCUMENTI CHE UN LOTTO HA PRESO IN CARICO, con l'esito di
    #        ciascuno — compresi quelli che una fattura non sono mai diventati.
    #
    # ⭐ PERCHE' NON BASTA LA SCHEDA «DOCUMENTI» (brief-db-esito-gruppo-lotto).
    #    Quella elenca `fatturazione_lotti_fatture`, che si aggancia a
    #    `fattura_id`: un documento caduto PRIMA che una fattura esista non ha
    #    niente a cui appendersi e sparisce dal racconto. Sul lotto LTF-0009578
    #    si vedevano due documenti su tre, e il terzo era nominato solo da una
    #    segnalazione — per giunta con l'identificativo della COMMESSA.
    #    Il piano giusto e' un gradino piu' su, ed e' il GRUPPO.
    #
    # ⛔ IL CANCELLO E' LA TESTATA, e va tenuto: `fatturazione_lotti_gruppi` NON
    #    ha RLS, `fatturazione_lotti` si'. Leggere la figlia da sola sarebbe
    #    fail-open. Il `JOIN` sulla CTE `lotto` e' quel cancello, e vale anche
    #    per il conteggio — un totale senza cancello direbbe «3 documenti»
    #    mostrandone zero.
    #
    # ⭐ L'IDENTITA' DEL GRUPPO NON SI RICOSTRUISCE QUI. Una `gruppo_key` e'
    #    `<sorgente>:<uid>` (oppure `MAN:<commessa>`): per scriverla a video ci
    #    vuole la derivazione che `vendite.fn_build_gruppo_fatturabile_key` e
    #    `vw_dash_competenza_gruppi` gia' fanno. Si legge da LI' invece di
    #    spezzare la chiave in Python — che sarebbe la seconda sede della
    #    regola, e il giorno in cui la chiave cambia forma le due dissentono in
    #    silenzio. Il legame e' (gruppo, MESE del lotto), lo stesso della vista.
    #
    # ⚠️ L'ESITO si legge da `vendite.fatturazione_lotti_esiti`, non dalle
    #    colonne `ultimo_*` della vista: quelle dicono com'e' andato l'ULTIMO
    #    tentativo su quel documento, che puo' essere di un ALTRO lotto. Qui la
    #    domanda e' «come e' andata in QUESTO lotto», e la risposta e' la riga
    #    di questo lotto.
    #
    # ⚠️ `commessa_id` esce solo quando ce n'e' UNA. Il gruppo di un documento
    #    non porta la commessa in chiave, quindi due commesse sullo stesso
    #    documento sono ammesse per costruzione: offrirne una sarebbe una
    #    scommessa travestita da regola — la stessa forma con cui questa lista
    #    tratta gia' il sezionale (`registri_n`). `commesse_n` dice quante sono.
    #
    # Risultato: (righe, totale). ⭐ Zero righe ha UN significato solo, dal
    #        2026-09-07: di questo lotto non risulta nessun documento — perche'
    #        non ha ancora lavorato, o perche' e' anteriore al tracciamento.
    #        ⛔ Prima ne aveva due, e serviva un flag (`perimetro_dichiarato`)
    #        per distinguerli: era la conseguenza di leggere il solo perimetro,
    #        che i giri di massa non scrivono. Con l'unione la distinzione non
    #        esiste piu', e il flag e' stato tolto invece che tenuto «per
    #        sicurezza» — un campo che non discrimina piu' niente e' un campo
    #        che qualcuno leggera' credendo che discrimini.
    def list_lotto_gruppi(
        self,
        *,
        lotto_id: int,
        auth_user_id: int | None = None,
        stato_esecuzione: str | None = None,
        sort_by: str | None = None,
        sort_dir: str | None = None,
        limit: int,
        offset: int,
        max_rows: int | None = None,
    ) -> tuple[list[LottoGruppoRow], int]:
        # Due tetti, come sulle fatture del lotto: la PAGINA si ferma a
        # `MAX_LIMIT`, l'EXPORT salta la paginazione e arriva al suo.
        tetto = _LOTTO_EXPORT_MAX_ROWS if max_rows else MAX_LIMIT
        safe_limit, safe_offset = limiti_pagina(max_rows or limit, offset, tetto=tetto)

        lotto_conditions: list[str] = ["l.id = %s"]
        params: list[Any] = [lotto_id]
        # Scope emittente esplicito OLTRE alla RLS, come su `list_lotto_fatture`:
        # il canale applicativo non e' l'unico che passa di qui.
        self._add_scope_emittente(
            auth_user_id, "l.emittente_soggetto_ruolo_id", lotto_conditions, params
        )
        lotto_where = " AND ".join(lotto_conditions)

        gruppi_where = ""
        if stato_esecuzione is not None:
            # ⚠️ `IS NOT DISTINCT FROM` no: `NULL` non e' un valore del
            #    vocabolario, e chiederlo come filtro vorrebbe dire un secondo
            #    parametro. Chi vuole «mai tentati» non filtra.
            gruppi_where = "AND esito.stato_esecuzione = %s"
            params.append(stato_esecuzione)

        # Ordinamento: solo valori dalla whitelist entrano nella query.
        sort_col = colonna_ordinamento(sort_by, LOTTO_GRUPPI_SORT_COLUMNS)
        order_params: list[Any] = []
        if sort_col is not None:
            # Direzione dal BB `sql_order_direction` (NULL come valore minimo).
            # ⚠️ `gruppo_key ASC` resta fisso: e' il criterio di raggruppamento
            #    della tabella «Regola d'uso» del catalogo BB, non uno spareggio
            #    tecnico da allineare.
            order_clause = (
                f"ORDER BY {sort_col} {sql_order_direction_lista(sort_by, sort_dir, colonne=LOTTO_GRUPPI_SORT_COLUMNS)}, gruppo_key ASC"
            )
        else:
            # ⭐ DEFAULT: i falliti in cima. Non e' l'ordine alfabetico dello
            #    stato — che metterebbe `ERRORE` dopo `COMPLETED` — ma la
            #    domanda con cui si apre questa scheda: «quale documento non e'
            #    passato?». Il resto in ordine di riferimento, e `gruppo_key`
            #    come tiebreak perche' `riferimento` puo' non risolversi.
            # ⛔ Il valore viaggia come PARAMETRO e non come letterale nell'SQL:
            #    e' la lezione gia' pagata sullo stadio della lista gruppi
            #    (AGENTS.md §vocabolari). Una stringa scritta a mano dentro la
            #    query e' una SECONDA sede del vocabolario, e il giorno in cui
            #    il CHECK rinomina il valore l'ordinamento smette di funzionare
            #    senza fallire: le righe rosse tornano in fondo, e nessuno se ne
            #    accorge finche' non le cerca.
            # 🔴 `NULLS LAST` NON E' UN DI PIU', ed e' un difetto misurato il
            #    2026-09-07. In PostgreSQL `DESC` implica `NULLS FIRST`, e il
            #    confronto `NULL = 'ERRORE'` vale NULL — cioe' i documenti MAI
            #    TENTATI finivano SOPRA quelli falliti. L'ordinamento prometteva
            #    «i falliti in cima» e metteva in cima i mai guardati: su un
            #    lotto con quaranta documenti dichiarati, quello caduto
            #    scompariva in fondo. ⛔ Nessun errore, solo la riga sbagliata
            #    per prima — e con l'unione il caso e' la NORMA, perche' ogni
            #    documento del perimetro non ancora tentato ha esito NULL.
            order_clause = (
                "ORDER BY (stato_esecuzione = %s) DESC NULLS LAST, "
                "riferimento ASC NULLS LAST, gruppo_key ASC"
            )
            order_params.append(STATO_ESECUZIONE_ERRORE)

        # ⭐ IL PERIMETRO DELLA LISTA VIVE IN UN POSTO SOLO, e le due query lo
        #    CONDIVIDONO invece di riscriverlo.
        # ⛔ Prima era copiato: la definizione dei documenti del lotto stava sia
        #    nella query di pagina sia in quella di riserva del conteggio. Due
        #    copie della stessa regola divergono al primo che ne tocca una, e
        #    qui la divergenza sarebbe MUTA — il paginatore direbbe un totale
        #    che non descrive le righe che consegna. E' la regola di api.md
        #    §count: «si condivide il frammento FROM+WHERE, non lo si riscrive».
        # ⚠️ `documenti` porta anche `lotto_id`: serve alla LEFT JOIN, e averlo
        #    nella riga evita un `CROSS JOIN` sulla CTE del lotto — che
        #    funzionava solo perche' quella CTE ha al massimo una riga, cioe'
        #    era corretto per coincidenza e non per costruzione.
        perimetro_sql = f"""
            WITH lotto AS (
                SELECT l.id, l.competenza_mese
                FROM vendite.fatturazione_lotti l
                WHERE {lotto_where}
            ),
            documenti AS (
                -- ⭐ L'UNIONE DI DUE FATTI INDIPENDENTI, dal 2026-09-07.
                --    Il PERIMETRO dice che cosa il lotto doveva lavorare, e lo
                --    dichiarano i soli giri mirati; gli ESITI dicono che cosa
                --    ha lavorato davvero, e ci sono su entrambi i tipi di giro.
                --    Nessuno dei due da solo risponde alla domanda della
                --    scheda: «quali documenti, e com'e' andata».
                -- ⛔ Il solo perimetro lascerebbe muto ogni giro di massa — il
                --    difetto appena chiuso dal database. I soli esiti
                --    perderebbero i documenti di un lotto mirato che non e'
                --    ancora arrivato al passo del pull: dichiarati, e non
                --    ancora tentati.
                SELECT lg.lotto_id, lg.gruppo_key
                  FROM vendite.fatturazione_lotti_gruppi lg
                  JOIN lotto ON lotto.id = lg.lotto_id
                UNION
                SELECT le.lotto_id, le.gruppo_key
                  FROM vendite.fatturazione_lotti_esiti le
                  JOIN lotto ON lotto.id = le.lotto_id
            ),
            gruppi AS (
                SELECT d.gruppo_key,
                       -- ⚠️ Serve al join della pagina con la vista delle azioni di riga: averlo qui
                       --    evita un secondo segnaposto, e i parametri di
                       --    questa query hanno gia' un ordine delicato
                       --    (perimetro + ordinamento + paginazione).
                       d.lotto_id,
                       -- ⚠️ NULL = il documento e' nel perimetro ma nessuno ha
                       --    ancora detto com'e' andata. Sulla tabella degli
                       --    esiti `stato_esecuzione` e' NOT NULL apposta — la
                       --    riga NASCE quando c'e' qualcosa da dire — quindi
                       --    qui il non-detto e' l'ASSENZA della riga, non uno
                       --    stato di mezzo.
                       esito.stato_esecuzione,
                       esito.errore_codice,
                       esito.errore_messaggio,
                       esito.errore_quando,
                       -- ⭐ L'USCITA DAL GIRO (brief-db-uscita-documento-dal-giro):
                       --    motivo scritto dall'operatore piu' il timbro, che
                       --    lo mette il trigger dalla GUC.
                       -- ⚠️ `uscita_quando`, non `uscita_il`: il nome vero e'
                       --    quello, letto dalla doc auto-gen della tabella.
                       esito.uscita_motivo,
                       esito.uscita_quando,
                       esito.uscita_da
                -- ⚠️ Alias `esito` e non `le`: `le` e' gia' il ramo dell'UNION
                --    qui sopra, e lo stesso nome per due cose nella stessa
                --    istruzione si legge male anche quando compila.
                FROM documenti d
                LEFT JOIN vendite.fatturazione_lotti_esiti esito
                       ON esito.lotto_id = d.lotto_id
                      AND esito.gruppo_key = d.gruppo_key
                WHERE TRUE {gruppi_where}
            )
        """  # noqa: S608

        sql = f"""
            {perimetro_sql},
            ref AS (
                -- Una riga per gruppo. ⚠️ La vista ha grana
                -- (competenza, gruppo_key, …, stadio): senza il collasso lo
                -- STESSO documento comparirebbe due volte quando parte del suo
                -- lavoro e' gia' fatturato e parte no.
                -- ⚠️ `min()` sulle colonne di IDENTITA' e' un collasso di valori
                -- identici, non una scelta fra alternative: riferimento, tipo e
                -- documento discendono dalla CHIAVE, che qui e' fissa. Resta
                -- deterministico anche se un giorno smettessero di esserlo.
                SELECT g.gruppo_key,
                       min(g.riferimento)                  AS riferimento,
                       min(g.tipo_gruppo)                  AS tipo_gruppo,
                       bool_and(g.documento_apribile)      AS documento_apribile,
                       min(g.documento_id)                 AS documento_id,
                       count(DISTINCT g.commessa_id)       AS commesse_n,
                       CASE WHEN count(DISTINCT g.commessa_id) = 1
                            THEN min(g.commessa_id) END    AS commessa_id,
                       CASE WHEN count(DISTINCT g.commessa_id) = 1
                            THEN min(g.commessa_codice) END AS commessa_codice
                FROM vendite.vw_dash_competenza_gruppi g
                JOIN lotto ON lotto.competenza_mese = g.competenza_mese
                WHERE g.gruppo_key IN (SELECT gruppo_key FROM gruppi)
                GROUP BY g.gruppo_key
            )
            SELECT gr.gruppo_key,
                   gr.stato_esecuzione,
                   gr.errore_codice,
                   gr.errore_messaggio,
                   gr.errore_quando,
                   gr.uscita_motivo,
                   gr.uscita_quando,
                   gr.uscita_da,
                   -- ⭐ IL MOTIVO DEL PULSANTE SPENTO e QUANTI DOCUMENTI
                   --    VENGONO VIA INSIEME, letti dalla superficie del DB
                   --    (`vendite.vw_lotti_gruppi_azioni`, la superficie che il
                   --    registro `config.azioni_riga` nomina per
                   --    ESCLUDI_DOCUMENTO_DA_GIRO: brief-modello-documento-
                   --    vendita §15.11.1, BE-2). La vista chiama la STESSA
                   --    `fn_check_documento_escludibile_da_giro` della madre,
                   --    e lo verifica il presidio del registro: tooltip ed
                   --    errore non possono dire due cose diverse.
                   -- ⛔ Prima queste colonne le componeva questa query, e il
                   --    presidio del DB non poteva vederle.
                   az.uscita_blocco_reason,
                   az.uscita_blocco_reason_key,
                   az.n_trascinati,
                   ref.riferimento,
                   ref.tipo_gruppo,
                   ref.documento_apribile,
                   ref.documento_id,
                   ref.commessa_id,
                   ref.commessa_codice,
                   COALESCE(ref.commesse_n, 0) AS commesse_n,
                   COUNT(*) OVER () AS total_count
            FROM gruppi gr
            LEFT JOIN ref ON ref.gruppo_key = gr.gruppo_key
            -- 🔴 Il filtro sul lotto e' COSTANTE (`(SELECT id FROM lotto)`), non
            --    il join su `gr.lotto_id`, e non e' un dettaglio. La vista ha una
            --    UNION (perimetro ∪ esiti): un filtro di JOIN non ci entra, e la
            --    vista calcolava la check per ogni gruppo di OGNI lotto visibile
            --    (EXPLAIN su dbdev, 2026-10-27: 155 righe per servirne 12). Un
            --    filtro costante invece scende nei due rami della UNION.
            LEFT JOIN vendite.vw_lotti_gruppi_azioni az
                   ON az.lotto_id = (SELECT id FROM lotto)
                  AND az.gruppo_key = gr.gruppo_key
            {order_clause}
            LIMIT %s OFFSET %s
        """  # noqa: S608

        # ⚠️ IL FALLBACK NON E' DECORATIVO. `COUNT(*) OVER ()` non puo' dire il
        #    totale quando la pagina richiesta non ha righe: su una pagina
        #    STANTIA — l'elenco si e' accorciato sotto le mani di chi guarda —
        #    il totale uscirebbe `0`, e la scheda direbbe «nessun documento
        #    preso in carico» su un lotto che ne ha tre. ⛔ Qui non c'e' il
        #    clamp dei cruscotti: `useListaDrawerPaginata` serve la pagina
        #    CHIESTA e non adotta nessuna pagina effettiva, quindi il conteggio
        #    e' l'unica cosa che puo' raccontare la verita'.
        # ⭐ E conta le righe della STESSA CTE che la lista consegna: non e' un
        #    perimetro «uguale», e' lo stesso.
        count_sql = f"{perimetro_sql} SELECT COUNT(*) FROM gruppi"  # noqa: S608

        rows, total_count = fetch_paged_with_total(
            sql, params + order_params + [safe_limit, safe_offset],
            fallback_count_sql=count_sql,
            fallback_params=list(params),
            offset=safe_offset,
        )

        result: list[LottoGruppoRow] = []
        for row in rows:
            result.append(
                {
                    # ⛔ Niente `id`: la riga non è più UNA riga di tabella, è
                    #    l'unione di due fatti. L'identità di questa lista è il
                    #    DOCUMENTO, e la sua chiave è `gruppo_key` — che è unica
                    #    dentro il lotto per costruzione (lo dicono entrambi i
                    #    vincoli `uq_*_lotto_key` e `uq_*_documento`).
                    "gruppo_key": str(row["gruppo_key"]),
                    # ⚠️ `None` = mai tentato in questo lotto, e non e' «andato
                    # bene»: e' la verita' di ogni gruppo lavorato prima che il
                    # backend chiamasse `fn_segna_esito_gruppo_lotto`.
                    "stato_esecuzione": row["stato_esecuzione"],
                    "errore_codice": row["errore_codice"],
                    "errore_messaggio": row["errore_messaggio"],
                    "errore_quando": (
                        row["errore_quando"].isoformat()
                        if row["errore_quando"] is not None else None
                    ),
                    # ⚠️ Tutte `None` quando il gruppo non si risolve piu': il
                    # lavoro puo' essere stato preso da un altro giro o essere
                    # uscito dal mese. Il gruppo resta in elenco col suo esito —
                    # nasconderlo cancellerebbe proprio la riga per cui questa
                    # scheda esiste. Il frontend ripiega sulla chiave.
                    "riferimento": row["riferimento"],
                    "tipo_gruppo": row["tipo_gruppo"],
                    "documento_apribile": row["documento_apribile"],
                    "documento_id": (
                        None if row["documento_id"] is None else int(row["documento_id"])
                    ),
                    "commessa_id": (
                        None if row["commessa_id"] is None else int(row["commessa_id"])
                    ),
                    "commessa_codice": row["commessa_codice"],
                    # ⭐ L'uscita dal giro: `None` su tutte e tre finche' il
                    #    documento e' dentro. Il motivo e' obbligatorio (D-5),
                    #    quindi su una riga ESCLUSO c'e' sempre.
                    "uscita_motivo": row["uscita_motivo"],
                    "uscita_quando": (
                        row["uscita_quando"].isoformat()
                        if row["uscita_quando"] is not None else None
                    ),
                    "uscita_da": row["uscita_da"],
                    # ⚠️ `None` = l'azione e' AMMESSA su questa riga. Il
                    #    frontend spegne il pulsante quando c'e' un valore, e
                    #    rende il testo dalla `reason_key`.
                    "uscita_blocco_reason": row["uscita_blocco_reason"],
                    "uscita_blocco_reason_key": row["uscita_blocco_reason_key"],
                    # ⚠️ `None` quando l'azione e' bloccata: li' non e' «zero
                    #    trascinati», e' «non e' stato chiesto». Zero e un vuoto
                    #    dicono cose diverse e il frontend deve poterli
                    #    distinguere.
                    "n_trascinati": (
                        None if row["n_trascinati"] is None else int(row["n_trascinati"])
                    ),
                    "commesse_n": int(row["commesse_n"] or 0),
                }
            )
        return result, total_count

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Fattura (generazione documento / stampa, C-2)
    #  Read-side per il motore documentale (sorgente FATTURA). La fattura
    #  non ha un repository dedicato: i read vivono qui, accanto a
    #  list_lotto_fatture (convenzione AGENTS.md — `<schema>_repository`
    #  per le operazioni generiche vendite che non sono un sottodominio
    #  con orchestrazione propria).
    # ══════════════════════════════════════════════════════════

    # Scopo: Contesto minimo per la generazione documento (stampa PDF) della
    #        fattura. Mirror di OrdiniRepository.get_for_documento_generation,
    #        con la differenza-chiave FATTURA: la testata espone
    #        `emittente_soggetto_ruolo_id` (SR), mentre il motore documentale
    #        vuole `emittente_fiscale_id` (PK). Si risolve la PK con JOIN a
    #        anagrafiche.emittenti_fiscali (1:1 garantito da
    #        uq_emittenti_fiscali_ruolo) — memoria
    #        feedback_emittente_pk_vs_soggetto_ruolo. LEFT JOIN, non INNER: se
    #        il record EF manca (dato sporco), la fattura ESISTE con
    #        emittente_fiscale_id NULL → il BB `resolve_contesto_documentale`
    #        distingue "non trovata" (404) da "emittente non risolto"
    #        (validation parlante); un INNER collasserebbe i due casi. Ritorna
    #        {id, uid, emittente_fiscale_id}; None se id inesistente o fuori
    #        scope RLS (indistinguibile per design → 404 unificato nel caller).
    def get_fattura_for_documento_generation(
        self, fattura_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT
                f.id,
                f.uid::text AS uid,
                ef.id       AS emittente_fiscale_id
              FROM vendite.fatture f
              LEFT JOIN anagrafiche.emittenti_fiscali ef
                ON ef.soggetto_ruolo_id = f.emittente_soggetto_ruolo_id
             WHERE f.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            return row_to_dict(cursor)

    # Scopo: Testata fattura completa di decodifiche (cliente, emittente,
    #        pagamento, totali) per il context builder del PDF **e** per
    #        l'endpoint di dettaglio del drawer fattura.
    #
    #        ⚠️ RISTAMPA CONFORME (Fase 2 piano BE/FE satelliti, 2026-07-31):
    #        l'intestazione delle due parti NON si legge piu' dall'anagrafica
    #        viva ma dagli SNAPSHOT congelati allo step DRAFT dalla pipeline
    #        (`fn_snapshot_fattura_lotto`):
    #          - identita' fiscale emittente/cliente → `f.emittente_snapshot` /
    #            `f.cliente_snapshot` (testata, guard di congelamento);
    #          - indirizzo di fatturazione cliente → riga `FATT` di
    #            `vendite.fatture_indirizzi`.
    #        Le chiavi piatte esposte restano IDENTICHE (contratto del drawer
    #        FE e del template PDF): cambia solo la sorgente. NESSUN fallback
    #        alla vista live (§9 del piano): una fattura senza snapshot mostra
    #        i campi vuoti, ed e' giusto che si veda.
    #        La rimozione delle vecchie subquery su vw_indirizzi_resolved_ruolo
    #        chiude anche i DUE difetti del §10.3 del brief intestazione (il
    #        filtro confrontava codice_interno con la colonna `codice`, e la
    #        vista contiene il solo layer RUOLO — la sede legale dell'emittente
    #        non era MAI stata stampata).
    #
    #        Lettura pura: nessun calcolo fiscale in Python. None se la fattura
    #        non esiste (o è fuori scope RLS).
    #        `auth_user_id` opzionale = difesa in profondita' applicativa che si
    #        SOMMA alla RLS di `vendite.fatture` (policy `rls_fatture_ef_whitelist`,
    #        attiva sul ruolo dell'app: `zeroerp_app` non e' owner della tabella).
    #        Default `None` = nessun filtro applicativo: e' il percorso del motore
    #        documentale, che applica lo scope a monte e non va toccato.
    def get_fattura_testata(
        self,
        fattura_id: int,
        *,
        auth_user_id: int | None = None,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT
                f.id,
                f.uid::text                  AS uid,
                f.anno,
                f.serie,
                f.numero,
                -- ⭐ IL NUMERO DEL DOCUMENTO, dalla SEDE UNICA. L'identita' di
                -- una fattura sono TRE colonne (anno, serie, numero) e nessuna
                -- di loro e' il «codice parlante»: per gli altri sei documenti
                -- `numero` e' gia' un testo (DDT0000031), qui e' un contatore.
                -- La forma — `numero - serie`, senza anno perche' la data sta
                -- sempre accanto — e' una decisione di Tid del 2026-08-29 e vive
                -- in `vendite.fn_numero_documento_fattura` (20260829-15).
                -- ⛔ NON si ricompone qui e NON si ricompone nel frontend: erano
                -- gia' sei forme diverse in giro per il progetto, e la settima
                -- sarebbe stata questa.
                -- ⚠️ NULL quando il documento non e' ancora numerato: il
                -- consumatore ha gia' la sua fallback, e un placeholder scritto
                -- qui gliene toglierebbe la scelta.
                vendite.fn_numero_documento_fattura(f.numero, f.serie)
                                             AS numero_documento,
                f.data,
                f.tipo_doc_fiscale_id,
                tdf.codice_interno           AS tipo_doc_fiscale_codice,
                tdf.descrizione              AS tipo_doc_fiscale_descrizione,
                -- Natura del documento (FATTURA | NOTA_CREDITO | NOTA_DEBITO):
                -- e' un asse DIVERSO dal tipo documento (front/back office) e
                -- dal registro. Sta accanto a `serie` perche' le tre cose
                -- insieme dicono su quale sezionale il documento e' numerato.
                f.natura_doc_id,
                ndf.codice_interno           AS natura_doc_codice_interno,
                ndf.descrizione              AS natura_doc_descrizione,
                f.stato_doc_fiscale_id,
                sdf.codice_interno           AS stato_codice_interno,
                sdf.descrizione              AS stato_descrizione,
                f.emittente_soggetto_ruolo_id,
                -- ⭐ La PK dell'emittente VIVA, dalla colonna di testata (NOT
                -- NULL) e non dallo snapshot: la chiede il cancello di
                -- perimetro delle liste nel drawer (i documenti generati), e
                -- in BOZZA lo snapshot puo' mancare — lo pretende solo
                -- l'uscita dalla bozza. Dallo snapshot, su una bozza il dialog
                -- dei documenti restava in attesa per sempre. Nessun effetto
                -- sulle righe: `soggetto_ruolo_id` e' UNIQUE su
                -- `emittenti_fiscali` (`uq_emittenti_fiscali_ruolo`).
                ef_pk.id                     AS emittente_fiscale_pk,
                -- ===== Intestazione EMITTENTE: dallo snapshot congelato =====
                -- Chiavi piatte derivate dal jsonb per compatibilita' col
                -- contratto esistente (drawer FE + template PDF v1). NULL se
                -- lo snapshot manca (fattura pre-Fase 1): niente fallback.
                (f.emittente_snapshot->>'emittente_fiscale_id')::bigint
                                             AS emittente_fiscale_id,
                f.emittente_snapshot->>'emittente_codice'
                                             AS emittente_fiscale_codice,
                f.emittente_snapshot->>'denominazione'
                                             AS emittente_denominazione,
                f.emittente_snapshot->>'id_fiscale'
                                             AS emittente_piva,
                f.emittente_snapshot->>'codice_fiscale'
                                             AS emittente_cf,
                -- Sede legale: display dello snapshot indirizzo annidato
                -- (composto a DB da fn_resolve_indirizzo_documento, due layer).
                f.emittente_snapshot->'sede'->>'display'
                                             AS emittente_sede,
                -- Utility del documento: dalla COLONNA di testata (D-S,
                -- 2026-08-01), non dedotta dal billing account. Sono due
                -- derivazioni diverse e possono divergere: la chiave di
                -- aggregazione prende l'utility dal BA dell'**attivita'** (il
                -- figlio), mentre `f.billing_account_id` e' il BA della
                -- fattura (il **padre**, D-P). Finche' non esistono BA con
                -- `parent_account_id` le due coincidono, ma dedurla da `ba`
                -- rimetterebbe qui lo stesso difetto latente che D-S ha
                -- appena tolto dal ricalcolo totali.
                f.utility_id,
                util.codice                  AS utility_codice,
                util.descrizione             AS utility_descrizione,
                mpag.codice                  AS pagamento_modalita_codice,
                tpag.codice_interno          AS pagamento_termine_codice,
                f.billing_account_id,
                -- ===== Intestazione CLIENTE: dallo snapshot congelato =====
                f.cliente_snapshot->>'ba_codice'          AS ba_codice,
                (f.cliente_snapshot->>'soggetto_ruolo_id')::bigint
                                             AS cliente_soggetto_ruolo_id,
                (f.cliente_snapshot->>'soggetto_id')::uuid AS soggetto_id,
                f.cliente_snapshot->>'denominazione'
                                             AS ragione_sociale_completa,
                f.cliente_snapshot->>'id_fiscale'
                                             AS id_fiscale_univoco_cf_piva,
                -- Indirizzo di fatturazione cliente: riga FATT del satellite
                -- congelato (unica per la UNIQUE (fattura_id, tipo)). E' QUESTA
                -- la lettura che rende la ristampa conforme: modificare
                -- l'anagrafica non cambia piu' il documento.
                (SELECT fi.snapshot->>'display'
                   FROM vendite.fatture_indirizzi fi
                   JOIN config.tipi_indirizzi ti ON ti.id = fi.tipo_indirizzo_id
                  WHERE fi.fattura_id = f.id
                    AND ti.codice_interno = %s)
                                             AS cliente_indirizzo,
                -- Snapshot integrali: per i consumer che vorranno i campi
                -- ricchi (REA, forma giuridica, codice SDI) senza riaprire
                -- questa SELECT. Shape interno non contrattuale (brief §10.2).
                f.emittente_snapshot,
                f.cliente_snapshot,
                f.valuta_id,
                val.iso_code                 AS valuta_codice,
                f.tasso_cambio,
                f.imponibile_tot,
                f.imposta_tot,
                f.bollo_applicato,
                f.bollo_importo,
                f.arrotondamento_attuale,
                f.totale_doc,
                f.totale_a_pagare,
                f.data_contabilizzazione,
                f.meta
              FROM vendite.fatture f
              JOIN anagrafiche.billing_account ba
                ON ba.id = f.billing_account_id
              LEFT JOIN config.utilities util
                ON util.id = f.utility_id
              LEFT JOIN config.modalita_pagamento mpag
                ON mpag.id = f.modalita_pagamento_id
              LEFT JOIN config.termini_pagamento tpag
                ON tpag.id = f.termine_pagamento_id
              LEFT JOIN config.tipi_doc_fiscale tdf
                ON tdf.id = f.tipo_doc_fiscale_id
              LEFT JOIN config.nature_doc_fiscale ndf
                ON ndf.id = f.natura_doc_id
              LEFT JOIN config.stati_doc_fiscale sdf
                ON sdf.id = f.stato_doc_fiscale_id
              LEFT JOIN config.valute val
                ON val.id = f.valuta_id
              LEFT JOIN anagrafiche.emittenti_fiscali ef_pk
                ON ef_pk.soggetto_ruolo_id = f.emittente_soggetto_ruolo_id
             WHERE f.id = %s
        """
        # Parametri nell'ordine dei %s: subquery indirizzo fatturazione
        # cliente (riga FATT del satellite), id fattura.
        params: list[Any] = [
            TIPO_INDIRIZZO_FATTURAZIONE,
            int(fattura_id),
        ]
        # Scope emittente applicativo (convenzione SR) appeso alla WHERE solo
        # quando il chiamante lo chiede: l'helper non aggiunge nulla per
        # auth_user_id None o per un utente che vede tutto (admin globale).
        conditions: list[str] = []
        self._add_scope_emittente(
            auth_user_id, "f.emittente_soggetto_ruolo_id", conditions, params,
        )
        if conditions:
            sql += " AND " + " AND ".join(conditions)
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = row_to_dict(cursor)
        return row

    # Scopo: Il legame DOCUMENTO-a-documento della nota di credito
    #        (`vendite.fatture_rettifiche`), letto nei DUE versi: da una nota di
    #        credito i documenti che rettifica, da una fattura le note di
    #        credito che la rettificano. Numero, data e id per il link.
    # ⚠️ SI CHIAMA DOPO IL CANCELLO DI TESTATA, MAI PRIMA. `vendite.fatture` ha
    #    la RLS, `fatture_rettifiche` NO: chiamarla su un id qualunque
    #    esporrebbe il numero di un documento fuori perimetro. Il service lo
    #    rispetta (§B7 del brief nota di credito) — chi aggiunge un chiamante
    #    nuovo deve rispettarlo pure.
    # ⭐ La tabella e' una PROIEZIONE di cio' che le righe gia' dicono
    #    (`fatture_righe.riga_rettificata_id`), scritta dal task di pipeline
    #    `popola_fatture_rettifiche` dopo la numerazione: su un documento non
    #    ancora numerato e' legittimamente vuota.
    def get_fattura_rettifiche(self, fattura_id: int) -> dict[str, list[dict[str, Any]]]:
        return {
            verso: self._legame_rettifiche(fattura_id, verso=verso)
            for verso in _RETTIFICHE_VERSI
        }

    # Scopo: un verso solo del legame documentale. Le due colonne del ponte si
    #        scambiano di ruolo fra i due versi, e vengono da una **whitelist**:
    #        sono nomi di colonna, non valori, quindi non possono arrivare da
    #        fuori.
    # ⚠️ Prima erano due `CASE WHEN %(verso)s = 'rettifica'`, uno nella JOIN e
    #    uno nella WHERE: due copie della stessa condizione che DEVONO
    #    concordare, e un refuso in una delle due avrebbe agganciato il
    #    documento sbagliato **in silenzio** — nessun errore, solo il numero di
    #    un'altra fattura a video. Qui la coppia si legge da una riga sola.
    def _legame_rettifiche(self, fattura_id: int, *, verso: str) -> list[dict[str, Any]]:
        col_filtro, col_target = _RETTIFICHE_VERSI[verso]
        sql = f"""
            SELECT %s::text AS verso,
                   f.id, f.numero, f.serie, f.anno, f.data,
                   -- Stessa sede unica della testata: un legame di rettifica
                   -- mostra un documento, e lo scrive come tutto il resto.
                   vendite.fn_numero_documento_fattura(f.numero, f.serie)
                        AS numero_documento,
                   ndf.codice_interno AS natura_doc_codice_interno
              FROM vendite.fatture_rettifiche fr
              JOIN vendite.fatture f ON f.id = fr.{col_target}
              LEFT JOIN config.nature_doc_fiscale ndf ON ndf.id = f.natura_doc_id
             WHERE fr.{col_filtro} = %s
             ORDER BY f.anno, f.numero
        """  # noqa: S608 — colonne da dict costante _RETTIFICHE_VERSI, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [verso, int(fattura_id)])
            return rows_to_list(cursor)

    # Scopo: Riepilogo IVA della fattura, letto dalla tabella REALE
    #        `vendite.fatture_riepiloghi_iva` (a differenza degli ordini, che
    #        derivano il riepilogo on-the-fly da una vista): una riga per
    #        gruppo (iva/natura/esigibilità/split). Decodifica iva + natura via
    #        JOIN (display field). Lettura pura: gli importi sono già
    #        aggregati/arrotondati dalla pipeline di fatturazione.
    def list_fattura_riepilogo_iva(self, fattura_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT
                ri.id,
                ri.fattura_id,
                ri.iva_id,
                iva.codice          AS iva_codice,
                iva.descrizione     AS iva_descrizione,
                iva.aliquota_iva    AS iva_aliquota,
                ri.natura_id,
                nat.codice          AS natura_codice,
                ri.esigibilita,
                ri.split_payment,
                ri.imponibile,
                ri.imposta,
                ri.arrotondamento
              FROM vendite.fatture_riepiloghi_iva ri
              LEFT JOIN config.iva iva        ON iva.id  = ri.iva_id
              LEFT JOIN config.iva_natura nat ON nat.id  = ri.natura_id
             WHERE ri.fattura_id = %s
             ORDER BY iva.aliquota_iva NULLS LAST, ri.iva_id NULLS LAST
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            return rows_to_list(cursor)

    # Scopo: Scadenze (rate) della fattura per il context builder (piano
    #        pagamenti stampato in fattura). Lettura pura, ordine stabile per
    #        numero rata → data. `modalita_codice` (opz.) dal jsonb `meta` se il
    #        DB lo mantiene; la tabella non ha colonna dedicata.
    def list_fattura_scadenze(self, fattura_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT
                sc.id,
                sc.numero_rata,
                sc.data_scadenza,
                sc.importo,
                sc.meta
              FROM vendite.fatture_scadenze sc
             WHERE sc.fattura_id = %s
             ORDER BY sc.numero_rata NULLS LAST, sc.data_scadenza NULLS LAST, sc.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            # `meta` decodificato dal lettore comune: il `_shape_scadenza` del
            # context builder ci fa `.get("modalita_codice")`.
            return rows_to_list(cursor)

    # Scopo: Annotazioni di legge della fattura per il context builder (forma 4,
    #        R-3 di brief-db-esigibilita-iva-per-cassa-emittente §11). QUALI
    #        annotazioni e con quale testo lo decide il database
    #        (`vendite.fn_annotazioni_fattura`, con la stessa regola del regime
    #        che calcola l'esigibilita' delle righe): qui solo l'ordine dato.
    #        Nessuna voce = lista vuota; mai un `testo` NULL (contratto DB).
    def list_fattura_annotazioni(self, fattura_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT a.codice, a.testo
              FROM vendite.fn_annotazioni_fattura(%s) a
             ORDER BY a.ordine
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            return rows_to_list(cursor)

    # Scopo: Le ORIGINI della fattura, i documenti a monte che cita (DDT,
    #        ordine, contratto…; per la nota di credito la fattura rettificata e
    #        il reso): una lista `{livello, tipo_id, tipo_codice_interno,
    #        etichetta, uid, codice}`. QUALI documenti e in che ordine lo decide
    #        il database (`vendite.fn_fattura_origini`, D-G1 = c, Q-F6 = b,
    #        Q-F7; brief-modello-documento-vendita §15.11.1, BE-1). Nessuna
    #        origine = lista vuota.
    # ⭐ L'ordine e' quello in cui la funzione le consegna, e qui lo si FISSA
    #    con `WITH ORDINALITY` invece di riscriverlo: un `ORDER BY livello, …`
    #    in questa query sarebbe una seconda sede della regola.
    # ⚠️ La funzione e' INVOKER: i documenti che chi legge non vede non escono.
    #    Si chiama DOPO il cancello della testata (`_testata_fattura_o_404`).
    def list_fattura_origini(self, fattura_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT o.livello, o.tipo_id, o.tipo_codice_interno,
                   o.etichetta, o.uid, o.codice
              FROM vendite.fn_fattura_origini(%s)
                   WITH ORDINALITY AS o(livello, tipo_id, tipo_codice_interno,
                                        etichetta, uid, codice, ordine)
             ORDER BY o.ordine
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            return rows_to_list(cursor)

    # ------------------------------------------------------------------
    # Lineage documenti (genealogia/transiti — brief-be-fe-lineage)
    # Letture generiche su vw_documento_lineage_nodi, fn_documento_lineage e
    # fn_documento_lineage_sintesi. Tutte security_invoker/SECURITY INVOKER: la
    # RLS emittente del chiamante si applica da sola (niente auth_user_id).
    # ------------------------------------------------------------------

    # Scopo: Traduce il doc_id di dominio nella chiave nodo lineage secondo
    #        la convenzione key_selector (config manual sorgenti): 'id' ->
    #        id::text senza round-trip; 'uid' -> SELECT uid dalla tabella
    #        target. Ritorna None se il documento non esiste (o e' fuori
    #        scope RLS: indistinguibile per design).
    def resolve_lineage_node_uid(
        self, *, target_table: str | None, key_selector: str, doc_id: int
    ) -> str | None:
        if key_selector == "id":
            return str(doc_id)
        # ⚠️ `config.sorgenti.target_table` e' nullable: una sorgente con chiave
        #    `uid` e senza tabella e' un seed incoerente, e lo si dice.
        if target_table is None:
            raise ValueError("target_table assente per una sorgente con key_selector 'uid'")
        # Guardia identifier: target_table viene da config.sorgenti
        # (regclass seedata), mai da input utente — la regex intercetta
        # solo dati sporchi da refactor (stesso pattern del repo note).
        if not re.fullmatch(r"[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)?", target_table):
            raise ValueError(f"target_table non valida: {target_table!r}")
        sql = f"SELECT uid::text FROM {target_table} WHERE id = %s"  # noqa: S608 — tabella da config.sorgenti (regclass seedata) validata da regex identificatore, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, [doc_id])
            row = cursor.fetchone()
        return None if not row else str(row[0])

    # Scopo: Riga summary lineage di un documento (nodo + pratica +
    #        frontiera + contatori) da fn_documento_lineage_sintesi, seminata
    #        sul solo documento (brief-db-lineage-seminata-per-chiave B1: la
    #        vista vw_documento_lineage, che calcolava il grafo intero, e'
    #        ritirata col 20261011-98). I tipi arrivano gia' come
    #        codice_interno (mai id numerici verso il FE). None se il nodo non
    #        esiste o e' fuori perimetro RLS.
    def get_lineage_nodo(self, *, tipo_id: int, node_uid: str) -> LineageNodoRow | None:
        sql = """
            SELECT
                l.tipo_id,
                -- ⭐ Il CODICE del tipo lo porta il grafo (20260829-02): fino a
                -- ieri il grafo esponeva solo l'id e ogni consumatore lo
                -- traduceva da se' con lo stesso join a config.sorgenti —
                -- UNDICI volte nel backend, e una di quelle undici era stata
                -- gia' dimenticata (lista resi, 25/08: colonna a catalogo, dato
                -- a database, niente a video e nessun errore).
                -- ⚠️ E qui c'era una `JOIN` (INNER) a config.sorgenti: la
                -- garanzia che il tipo esista non e' sparita insieme al join,
                -- si e' SPOSTATA — la sintesi esce solo per i nodi di
                -- `vendite.fn_documento_lineage_nodi`, che costruisce ogni
                -- suo ramo con una `JOIN config.sorgenti` interna. Un nodo senza
                -- sorgente attiva non esiste proprio, quindi la colonna non e'
                -- mai NULL ed e' lecito il `str()` sul lato Python. E' una
                -- garanzia STRUTTURALE (una join interna in una definizione di
                -- vista), non un'osservazione sui dati di oggi.
                l.tipo_codice_interno,
                l.uid,
                l.codice,
                l.stato_codice_interno,
                l.stato_codice,
                l.stato_descrizione,
                l.fase,
                l.is_abortito,
                l.pratica_id,
                l.pratica_numero,
                l.n_pratiche,
                l.frontiera_tipo_id,
                l.frontiera_tipo_codice_interno,
                l.frontiera_uid,
                l.frontiera_codice,
                l.frontiera_stato_codice_interno,
                l.frontiera_fase,
                l.n_discendenti_diretti,
                l.n_discendenti_attivi,
                l.is_transitato,
                l.n_sorgenti,
                l.root_codice,
                l.natura_doc_codice_interno,
                -- ⭐ La natura della FRONTIERA la porta LA SINTESI (prima la
                -- vista, dal changeSet 20260828-22). Fino ad allora la summary non ce
                -- l'aveva e questo repository se la ricavava da solo, con un
                -- LEFT JOIN a vw_documento_lineage_nodi sulla chiave del nodo
                -- di frontiera. Erano DUE SEDI per la stessa regola, e la
                -- seconda ricalcolava dall'esterno una frontiera che la CTE
                -- della vista risolve col tie-break su pipeline_rank: finche'
                -- coincidevano non lo diceva nessuno, ma il giorno in cui la
                -- regola della frontiera cambia in un posto solo il pannello e
                -- le liste direbbero due cose diverse sullo STESSO documento,
                -- e nessuna delle due darebbe errore. Tolta la copia, non
                -- scelta la migliore.
                -- ⚠️ Serve davvero, e non e' un caso limite: la frontiera PUO'
                -- essere una nota di credito (arco G dalla commessa, che non
                -- e' un ramo di ritorno) — misurato il 2026-08-21, e' gia' la
                -- frontiera dell'ordine 240 e della commessa 322. Senza, il
                -- pannello la etichetta «Fattura».
                -- ⛔ NULL non vuol dire «non lo so» ma «la frontiera non e' un
                -- documento fiscale»: la natura e' un asse diverso dal tipo ed
                -- esiste solo per le fatture.
                l.frontiera_natura_doc_codice_interno
            FROM vendite.fn_documento_lineage_sintesi(
                     ARRAY[%s]::bigint[], ARRAY[%s]::text[]) l
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo_id, node_uid])
            row = cursor.fetchone()
        if not row:
            return None
        return {
            "tipo_id": int(row[0]),
            "tipo_codice_interno": str(row[1]),
            "uid": str(row[2]),
            "codice": row[3],
            "stato_codice_interno": row[4],
            "stato_codice": row[5],
            "stato_descrizione": row[6],
            "fase": row[7],
            "is_abortito": bool(row[8]),
            "pratica_id": None if row[9] is None else int(row[9]),
            "pratica_numero": row[10],
            "n_pratiche": int(row[11]),
            "frontiera_tipo_id": None if row[12] is None else int(row[12]),
            "frontiera_tipo_codice_interno": row[13],
            "frontiera_uid": row[14],
            "frontiera_codice": row[15],
            "frontiera_stato_codice_interno": row[16],
            "frontiera_fase": row[17],
            "n_discendenti_diretti": int(row[18]),
            "n_discendenti_attivi": int(row[19]),
            "is_transitato": bool(row[20]),
            "n_sorgenti": int(row[21]),
            "root_codice": row[22],
            "natura_doc_codice_interno": row[23],
            "frontiera_natura_doc_codice_interno": row[24],
        }

    # Scopo: I legami di un documento che si annulla
    #        (`vendite.fn_documento_legami`, lettore unico di avviso, conferma e
    #        finestra; brief-db-annullo-documento-con-legami D-4): una riga per
    #        legame — riga_id, riga_nr (NULL per testata e commessa), origine
    #        (ORDINE, RESO, PREVENTIVO, OFFERTA, COMMESSA), natura (CONSUMO o
    #        PROVENIENZA), origine_id (la testata dall'altra parte),
    #        origine_riga_id, qta.
    #        ⚠️ La funzione e' SECURITY DEFINER: non applica il perimetro. Il
    #        chiamante deve aver gia' letto la testata del documento.
    def list_documento_legami(self, documento: str, documento_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT l.riga_id, l.riga_nr, l.origine, l.natura, l.origine_id,
                   l.origine_riga_id, l.qta
              FROM vendite.fn_documento_legami(%s, %s) AS l
             ORDER BY l.riga_nr NULLS LAST, l.origine, l.origine_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [documento, int(documento_id)])
            return rows_to_list(cursor)

    # Scopo: Catena dei passaggi di un documento via
    #        fn_documento_lineage(tipo, uid, direzione), decodificando i
    #        tipi degli estremi in codice_interno (JOIN config.sorgenti).
    #        Ordine stabile per il rendering timeline (colonna `ordine`).
    def list_lineage_passaggi(
        self, *, tipo_id: int, node_uid: str, direzione: str
    ) -> list[LineagePassaggioRow]:
        sql = """
            SELECT
                p.livello,
                p.ordine,
                p.arco,
                p.ruolo,
                p.from_tipo_id,
                sf.codice_interno           AS from_tipo_codice_interno,
                p.from_uid,
                p.from_codice,
                nf.stato_codice_interno     AS from_stato_codice_interno,
                nf.fase                     AS from_fase,
                -- Id numerico apribile nel drawer di dettaglio: uid::bigint
                -- per i tipi id-keyed; traduzione uuid->id per preventivo/
                -- offerta (unici key_selector='uid'). NULL = fuori scope RLS
                -- -> tappa consultiva, il FE non apre. (Fattura e commessa un
                -- drawer ce l'hanno: dal 2026-07-29 il grafo non ha piu' nodi
                -- senza superficie.)
                COALESCE(pfrom.id, ofrom.id,
                    CASE WHEN sf.key_selector = 'id'
                         THEN NULLIF(p.from_uid, '')::bigint END) AS from_doc_id,
                p.to_tipo_id,
                st.codice_interno           AS to_tipo_codice_interno,
                p.to_uid,
                p.to_codice,
                p.to_stato_codice_interno,
                p.to_fase,
                p.to_is_abortito,
                COALESCE(pto.id, oto.id,
                    CASE WHEN st.key_selector = 'id'
                         THEN NULLIF(p.to_uid, '')::bigint END) AS to_doc_id,
                p.is_ramo_inverso,
                -- La natura dei due estremi: distingue una nota di credito da
                -- una fattura quando la tappa e' la seconda di fila sotto lo
                -- stesso tipo documento (arco N).
                p.from_natura_doc_codice_interno,
                p.to_natura_doc_codice_interno,
                -- Il LEGAME, non il nodo (brief-db-annullo-a-valle-riapre-a-monte
                -- §11, 2026-10-13): la commessa puo' essere viva e il contributo
                -- di QUESTO documento ritirato (preventivo annullato). A tre
                -- stati: NULL = arco non censito dal DB.
                p.is_legame_ritirato
            FROM vendite.fn_documento_lineage(%s, %s, %s) p
            LEFT JOIN config.sorgenti sf ON sf.id = p.from_tipo_id
            LEFT JOIN config.sorgenti st ON st.id = p.to_tipo_id
            LEFT JOIN vendite.vw_documento_lineage_nodi nf
                   ON nf.tipo_id = p.from_tipo_id AND nf.uid = p.from_uid
            LEFT JOIN vendite.preventivi pfrom
                   ON sf.codice_interno = %s AND pfrom.uid::text = p.from_uid
            LEFT JOIN vendite.offerte_commerciali ofrom
                   ON sf.codice_interno = %s AND ofrom.uid::text = p.from_uid
            LEFT JOIN vendite.preventivi pto
                   ON st.codice_interno = %s AND pto.uid::text = p.to_uid
            LEFT JOIN vendite.offerte_commerciali oto
                   ON st.codice_interno = %s AND oto.uid::text = p.to_uid
            ORDER BY p.ordine
        """
        with connection.cursor() as cursor:
            # ⚠️ Ordine dei parametri = ordine nel testo: i tre della funzione,
            #    poi i codici delle quattro LEFT JOIN (from, from, to, to).
            cursor.execute(sql, [
                tipo_id, node_uid, direzione,
                SORGENTE_PREVENTIVO, SORGENTE_OFFERTA_COMMERCIALE,
                SORGENTE_PREVENTIVO, SORGENTE_OFFERTA_COMMERCIALE,
            ])
            rows = cursor.fetchall()

        result: list[LineagePassaggioRow] = []
        for row in rows:
            result.append(
                {
                    "livello": int(row[0]),
                    "ordine": int(row[1]),
                    "arco": str(row[2]),
                    "ruolo": row[3],
                    "from_tipo_id": int(row[4]),
                    "from_tipo_codice_interno": row[5],
                    "from_uid": str(row[6]),
                    "from_codice": row[7],
                    "from_stato_codice_interno": row[8],
                    "from_fase": row[9],
                    "from_doc_id": None if row[10] is None else int(row[10]),
                    "to_tipo_id": int(row[11]),
                    "to_tipo_codice_interno": row[12],
                    "to_uid": str(row[13]),
                    "to_codice": row[14],
                    "to_stato_codice_interno": row[15],
                    "to_fase": row[16],
                    "to_is_abortito": bool(row[17]),
                    "to_doc_id": None if row[18] is None else int(row[18]),
                    "is_ramo_inverso": bool(row[19]),
                    "from_natura_doc_codice_interno": row[20],
                    "to_natura_doc_codice_interno": row[21],
                    # ⛔ Niente `bool()`: NULL e' «non censito», e diventerebbe
                    #    «legame vivo» — un'affermazione che il DB non ha fatto.
                    "is_legame_ritirato": row[22],
                }
            )
        return result

    # ------------------------------------------------------------------
    # Situazione merce (pannello ordine/DDT — brief-design-situazione-merce-ordine)
    # Letture sulle viste della partita generalizzata. Tutte
    # `security_invoker=on`: la RLS del chiamante si applica da sola, quindi
    # NIENTE `auth_user_id` e niente filtro applicativo di scope.
    # ⚠️ E vale il §8.6 del brief partita: su una vista con RLS uno zero non e'
    # un dato, e' fail-closed. Il cancello di perimetro sono le due `exists_*`
    # qui sotto, che interrogano la TESTATA (l'unica tabella con la policy).
    # ------------------------------------------------------------------

    # Scopo: Esistenza (e visibilita' nello scope) di un ordine. `vendite.ordini`
    #        ha la RLS, `ordini_righe` NO: e' la testata a fare da cancello, ed
    #        e' lo stesso ordine di lettura del dettaglio fattura (api.md).
    #        False = inesistente OPPURE fuori scope, indistinguibili di proposito.
    def exists_ordine(self, ordine_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM vendite.ordini WHERE id = %s", [int(ordine_id)]
            )
            return cursor.fetchone() is not None

    # Scopo: Gemella della precedente per il DDT (`vendite.ddt` ha la RLS,
    #        `ddt_righe` no).
    def exists_ddt(self, ddt_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM vendite.ddt WHERE id = %s", [int(ddt_id)]
            )
            return cursor.fetchone() is not None

    # Scopo: Il riassunto PER RIGA D'ORDINE (livello 1 del pannello), da
    #        `vw_situazione_merce_ordine`. E' l'aggregato PARLANTE: `differenza`
    #        NULL dove il conto non si applica e `stato` gia' tradotto.
    # Risultato: una riga per riga d'ordine ATTIVA, comprese quelle mai spedite
    #        (`NON_SPEDITA`) — che nel contatore non ci sono affatto — e quelle
    #        di ordini non ancora impegnati (`NON_IMPEGNATA`).
    # ⚠️ Due colonne sono NULLABLE e il NULL NON e' uno zero: `differenza` dove
    #        il conto non si applica, e `da_spedire` sotto la soglia di impegno
    #        dell'ordine (< CONFERMATO o abortito, `20260818-06`). Un
    #        `COALESCE(..., 0)` qui direbbe «N da spedire» su ogni bozza — 60
    #        righe su 107 in sviluppo.
    # ⚠️ NON e' `vw_contatore_merce`: quello e' il contatore GREZZO che dosa la
    #        fatturazione, non ha `stato` e appiattisce i NULL a un numero.
    # ⭐ DUE FILTRI, UNA LETTURA (come `list_partite_merce`, rev 2026-08-19):
    #        per ordine = tutte le sue righe; per DDT = le righe d'ordine che
    #        QUELLA spedizione ha toccato. Il secondo serve al pannello
    #        uniformato — dal DDT si vede sia lo stato della riga d'ordine sia
    #        quello della spedizione (rilievo in-app di Tid del 2026-08-19).
    # ⭐ DAL 2026-09-21 LA CHIUSURA STA NELLA FUNZIONE (giro 2 di
    #        brief-db-partita-merce-per-documento, D3): si legge
    #        `fn_situazione_merce_ordine(p_ddt_ids, p_ordine_ids)` col solo
    #        array del documento riempito, e il `WHERE` sul documento non c'e'
    #        piu' — per DDT la funzione incorpora l'`EXISTS` sul fulfillment che
    #        prima stava qui (stessa semantica: la situazione INTERA delle righe
    #        d'ordine che quel DDT ha toccato, pgTAP test 5-6). Il legame
    #        DDT->riga d'ordine resta `ordini_righe_fulfillment`, la stessa
    #        fonte dell'`origine` della partita. «NON si passa dalla partita»
    #        resta vero nel senso che conta: la funzione la chiede per ORDINE
    #        (la chiusura), non ri-valuta la vista intera per un filtro.
    #        La scelta dell'array e' il BB `sorgente_per_documento`.
    def list_situazione_merce_ordine(
        self,
        *,
        ordine_id: int | None = None,
        ddt_id: int | None = None,
    ) -> list[dict[str, Any]]:
        sorgente, params = sorgente_per_documento(
            "vendite.fn_situazione_merce_ordine", ddt_id=ddt_id, ordine_id=ordine_id
        )
        sql = f"""
            SELECT
                s.ordine_riga_id,
                s.ordine_id,
                s.riga_nr,
                s.articolo_id,
                a.codice            AS articolo_codice,
                orr.descrizione,
                s.ordinato,
                s.consegnato,
                s.reso,
                s.in_riconsegna,
                s.tenuti,
                s.fatturato_merce,
                s.fatturato_da_ordine,
                s.fatturato,
                s.fatturato_anticipato,
                s.da_spedire,
                s.partite_merce,
                s.misurabile,
                s.differenza,
                s.stato,
                orr.uom_operativa_id,
                um.codice           AS uom_codice,
                -- Le date di consegna e il ritardo (brief-db-modifiche-certe-
                -- ciclo-vendita-e-articolo, P-6). `giorni_ritardo` sta nella
                -- vista e non altrove perche' legge `da_spedire` con la soglia
                -- dell'impegno: NULL = «non si applica» (niente da spedire, o
                -- nessuna data), 0 = c'e' da spedire e non e' tardi, N > 0 =
                -- giorni di ritardo rispetto alla PROMESSA (o, senza promessa,
                -- alla richiesta del cliente). Un COALESCE(..., 0) qui direbbe
                -- «in tempo» su una riga che non ha niente da spedire.
                s.data_consegna_richiesta_cliente,
                s.data_consegna_confermata,
                s.giorni_ritardo
              FROM {sorgente} s
              JOIN vendite.ordini_righe orr      ON orr.id = s.ordine_riga_id
              LEFT JOIN catalogo.articoli a      ON a.id   = s.articolo_id
              LEFT JOIN catalogo.unita_misura um ON um.id  = orr.uom_operativa_id
             ORDER BY s.ordine_id, s.riga_nr, s.ordine_riga_id
        """  # noqa: S608 — `sorgente` e' il BB, con i parametri a parte
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return rows_to_list(cursor)

    # Scopo: Le PARTITE DI MERCE (livello 2 del pannello), da
    #        `fn_partite_merce`. Grana = riga di DDT. Due filtri, una lettura
    #        (richiesta BE-1): per DDT = «la situazione di QUESTA spedizione»,
    #        per ordine = tutte le spedizioni di quell'ordine.
    # ⭐ DAL 2026-09-21 LA CHIUSURA STA NELLA FUNZIONE (giro 1 di
    #        brief-db-partita-merce-per-documento): la vista `vw_partite_merce`
    #        e' la sola proiezione `fn(NULL, NULL)` — «tutte» — e qui si legge la
    #        funzione col solo array del documento riempito, senza `WHERE` sul
    #        documento: la funzione filtra gia' l'uscita sulla stessa colonna
    #        proiettata (`ddt_id`, o `ordine_id` = riga minima). Per documento
    #        non e' piu' «la vista piu' costosa del sistema»: la chiusura e'
    #        O(righe del documento) sotto RLS, non O(tutte).
    # ⚠️ Esattamente uno dei due parametri va valorizzato (guard nel BB
    #        `sorgente_per_documento`): il chiamante e' il service, e un filtro
    #        assente restituirebbe TUTTE le partite del database — errore di
    #        programmazione, non input utente.
    def list_partite_merce(
        self,
        *,
        ddt_id: int | None = None,
        ordine_id: int | None = None,
    ) -> list[dict[str, Any]]:
        sorgente, params = sorgente_per_documento(
            "vendite.fn_partite_merce", ddt_id=ddt_id, ordine_id=ordine_id
        )
        sql = f"""
            SELECT
                p.ddt_riga_id,
                p.ddt_id,
                d.numero            AS ddt_numero,
                d.data              AS ddt_data,
                p.articolo_id,
                a.codice            AS articolo_codice,
                dr.descrizione,
                dr.riga_nr,
                dr.uom_operativa_id,
                um.codice           AS uom_codice,
                p.is_composito,
                p.ordine_riga_id,
                p.ordine_id,
                o.numero            AS ordine_numero,
                p.origine,
                p.fatturabile,
                p.consegnato,
                p.reso,
                p.in_riconsegna,
                p.tenuti,
                p.fatturato_merce,
                p.fatturato_da_ordine,
                p.fatturato,
                p.misurabile,
                p.differenza,
                p.stato,
                p.e_riconsegna,
                p.sospetto_duplicato_ordine
              FROM {sorgente} p
              JOIN vendite.ddt d                 ON d.id   = p.ddt_id
              JOIN vendite.ddt_righe dr          ON dr.id  = p.ddt_riga_id
              LEFT JOIN vendite.ordini o         ON o.id   = p.ordine_id
              LEFT JOIN catalogo.articoli a      ON a.id   = p.articolo_id
              LEFT JOIN catalogo.unita_misura um ON um.id  = dr.uom_operativa_id
             ORDER BY d.data, p.ddt_id, dr.riga_nr, p.ddt_riga_id
        """  # noqa: S608 — `sorgente` e' il BB, con i parametri a parte
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return rows_to_list(cursor)

    # Scopo: Le due code di lavoro del documento (D-4: un round-trip solo, cosi'
    #        il pannello NON PUO' contraddire le code — e' l'ultima voce della
    #        definizione di fatto del cantiere 2).
    # ⭐ L'aggancio e' `ddt_riga_id`, MAI `ordine_riga_id`: quest'ultimo e'
    #        nullable e sulla merce senza origine ordine e' vuoto — usarlo come
    #        chiave farebbe uscire quelle righe dal conto SENZA ERRORE, che e'
    #        il difetto §8.5 che questo cantiere ha chiuso.
    # ⚠️ Il filtro NON passa da `vw_partite_merce` (revisione 2026-08-18: la
    #        prima versione faceva EXISTS sulla partita, cioe' ri-valutava la
    #        vista piu' costosa del sistema dentro una query che gia' valuta la
    #        vista-coda — due volte lo stesso prezzo per rispondere a un filtro):
    #        - lato DDT basta `v.ddt_id`, che la coda espone gia' — e' il DDT
    #          della riga resa, lo stesso della partita per costruzione;
    #        - lato ordine il legame e' il FULFILLMENT della riga di DDT resa,
    #          che e' la STESSA fonte da cui la partita deriva la sua origine
    #          (CTE `orig`): un criterio solo, non un terzo criterio.
    # ⭐ DUE FORME, UNA PER CODA, E A SCEGLIERE NON E' QUESTO REPOSITORY (dal
    #        2026-09-21, giro 2 del brief partita; sede unica dal 22-09, regola
    #        del 2, ok Tid): la coda ACCREDITI ha la chiusura dentro
    #        `fn_resi_da_accreditare` e si legge dal `FROM` senza predicato —
    #        la funzione segue per ordine lo stesso `EXISTS` sul fulfillment
    #        (§9.3.2: stesse righe, pgTAP test 7); la coda RI-CONSEGNE non
    #        legge la partita, resta sulla vista e sul predicato. Quale coda ha
    #        quale forma lo dice `FUNZIONE_PER_CODA` in `_coda_documento_filtro`,
    #        e il BB `lettura_coda_per_documento` la applica — lo stesso che usa
    #        `ResiRepository._list_coda`: le due schermate contano le STESSE
    #        righe perche' leggono con la stessa forma, non perche' due wrapper
    #        sono stati tenuti allineati a mano.
    def _list_coda_su_partite(
        self,
        vista: str,
        colonne: str,
        *,
        ddt_id: int | None,
        ordine_id: int | None,
    ) -> list[dict[str, Any]]:
        # `vista` e `colonne` arrivano SOLO dai due wrapper qui sotto (letterali
        # statici, nessun input utente).
        # Guard di programmazione: i wrapper passano sempre uno dei due id.
        # Senza documento questa lettura non ha significato — non e' «tutte le
        # code», e' un chiamante rotto (il BB, senza documento, risponderebbe
        # la vista intera: qui quella risposta non e' una domanda).
        if ddt_id is None and ordine_id is None:
            raise ValueError(
                "_list_coda_su_partite: serve un documento (ddt_id o ordine_id)"
            )
        lettura = lettura_coda_per_documento(vista, ddt_id=ddt_id, ordine_id=ordine_id)
        where = f"WHERE {lettura.condizione}" if lettura.condizione is not None else ""
        sql = f"""
            SELECT {colonne}
              FROM {lettura.sorgente} v
             {where}
             ORDER BY v.reso_id, v.resi_riga_id
        """  # noqa: S608 — sorgente/predicato dal BB, parametri a parte
        with connection.cursor() as cursor:
            cursor.execute(sql, [*lettura.params_sorgente, *lettura.params_condizione])
            return rows_to_list(cursor)

    # Scopo: Coda «da accreditare» del documento. `etichetta` DOVUTA|FACOLTATIVA
    #        arriva dalla coda (la funzione con la chiusura, per `FUNZIONE_PER_CODA`):
    #        il pannello mostra la STESSA parola della coda di lavoro.
    def list_situazione_merce_accrediti(
        self, *, ddt_id: int | None = None, ordine_id: int | None = None
    ) -> list[dict[str, Any]]:
        return self._list_coda_su_partite(
            "vendite.vw_resi_da_accreditare",
            "v.resi_riga_id, v.reso_id, v.reso_numero, v.data, v.articolo_id, "
            "v.descrizione, v.quantita, v.qta_operativa, v.ddt_riga_id, "
            "v.ddt_id, v.ddt_numero, v.ordine_riga_id, v.tenuti, v.fatturati, "
            "v.accredito_dovuto, v.etichetta, v.motivo",
            ddt_id=ddt_id,
            ordine_id=ordine_id,
        )

    # Scopo: Coda «da ri-consegnare» del documento (residuo aperto).
    def list_situazione_merce_riconsegne(
        self, *, ddt_id: int | None = None, ordine_id: int | None = None
    ) -> list[dict[str, Any]]:
        return self._list_coda_su_partite(
            "vendite.vw_resi_da_riconsegnare",
            "v.resi_riga_id, v.reso_id, v.reso_numero, v.data, v.articolo_id, "
            "v.descrizione, v.ddt_riga_id, v.ddt_id, v.ddt_numero, "
            "v.ordine_riga_id, v.qta_resa, v.qta_riconsegnata, "
            "v.qta_rinunciata, v.qta_residua, v.stato_riconsegna",
            ddt_id=ddt_id,
            ordine_id=ordine_id,
        )

    # Scopo: IL GIORNALE DI UN'ENTITA' — «cosa e' successo a questa cosa, in
    #        ordine di tempo», letto dalla vista che cuce i registri.
    #
    # ⭐ LA SORGENTE E' `script.vw_giornale_entita` (lotto L3 del brief
    #    event_log), che unisce quattro registri in una forma normalizzata. Vive
    #    in `script` e non in `vendite` perche' i registri di eventi del progetto
    #    sono sei: quando arrivera' «cosa e' successo a questa pratica», il ramo
    #    entra con un UNION ALL e questo lettore non cambia.
    # 📌 Sta in `vendite` perche' il primo consumatore e' la fattura. Al SECONDO
    #    dominio va spostato in `core` — non prima (regola del 2).
    #
    # ⚠️ La vista e' `security_invoker`: il perimetro lo applica la connessione
    #    di chi legge, non questa query. ⛔ Ma NON e' il cancello di questo
    #    endpoint: `fatture` ha la RLS, e una fattura fuori scope darebbe zero
    #    righe — cioe' «non e' successo niente» invece di «non la vedi». Il
    #    cancello e' la TESTATA, e lo tiene il service.
    #
    # ⛔ L'ORDINE NON PUO' APPOGGIARSI AL SOLO TEMPO, ed e' il rilievo R-1 della
    #    ricognizione: `event_time` e `data_ora` hanno default `now()`, che in
    #    PostgreSQL e' il timestamp di TRANSAZIONE. Misurato: 38 righe di un
    #    lotto su 3 istanti distinti, uno per corsa. A ordinare davvero dentro
    #    l'istante e' il tiebreak `riga_id`, che e' l'ordine di scrittura — ed e'
    #    la sequenza vera finche' il registro e' UNO SOLO (oggi, per la fattura,
    #    e' `fatture_log`). ⚠️ Il giorno che una fattura avra' righe da due
    #    registri, dentro lo stesso istante l'ordine tornera' arbitrario: allora
    #    servira' una sequenza vera, non un ripiego qui.
    # ⭐ `disabilitato` — la segnalazione RITIRATA — arriva dal changeSet
    #    `20260824-14`. Il nome e' quello della sorgente ed e' lo stesso che
    #    espone `fn_list_lotto_segnalazioni`: lo stesso fatto non ha due nomi,
    #    quindi il pannello della fattura e la scheda del lotto lo mappano su
    #    «Ritirata» allo stesso modo.
    # ⚠️ Sulla vista la colonna e' IN CODA (un `CREATE OR REPLACE VIEW` non puo'
    #    inserirla in mezzo). Qui non morde: le colonne si nominano nella
    #    `SELECT`, quindi la posizione la decidiamo noi — ma chi legge per
    #    posizione da un `SELECT *` deve saperlo.
    # ⛔ `NULL` NON vuol dire «non ritirata», e i due NULL non sono uguali: su
    #    `event_log` il concetto non esiste (append-only, un evento e' un fatto
    #    accaduto), sui `task_runs` il ritiro esiste ma su un altro asse
    #    (`attivo` spegne il TENTATIVO, `disabilitato` ritira un SEGNALE). Da
    #    qui il `COALESCE(..., false)`: dove il concetto non si applica, la riga
    #    e' viva — che e' l'unica lettura che non inventa niente.
    def list_giornale_entita(
        self,
        *,
        entity_type: str,
        entity_id: int,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        escludi_ritirate: bool = True,
        sort_by: str | None = None,
        sort_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int, int, int]:
        return self._list_giornale(
            perimetro_sql="entity_type = %s AND entity_id = %s",
            perimetro_params=[entity_type, int(entity_id)],
            limit=limit,
            offset=offset,
            escludi_ritirate=escludi_ritirate,
            escludi_info=False,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

    # Scopo: il giornale di un LOTTO — il lotto PIU' le sue fatture.
    #
    # ⭐ «Che cos'e' un caso» e' una DECISIONE (Tid, 2026-08-24), non una scelta
    #    di schermata: cambia il filtro, il contratto e su cosa si pagina. Un
    #    pannello limitato all'entita' LOTTO sarebbe onesto e **non conterrebbe
    #    la risposta** — misurato sul 6260: 113 righe non-INFO sul lotto che
    #    dicono «Esito fatture lotto · WARN», e il motivo sta sulla FATTURA,
    #    perche' la sua entita' e' la fattura (rilievo R-3).
    #
    # ⛔ Il perimetro e' una SOTTO-QUERY, non una lista di id passata da Python:
    #    un lotto di fatturazione puo' contenere migliaia di documenti, e
    #    tradurli in un `IN (...)` sarebbe un limite nascosto che si scopre il
    #    giorno del lotto grosso.
    # Perimetro: sola lettura. ⚠️ Nessuno scope emittente QUI — il cancello e'
    #    `get_lotto`, che il service chiama PRIMA (stessa forma del giornale
    #    fattura, dove il cancello e' `get_fattura_testata`).
    def list_giornale_lotto(
        self,
        *,
        lotto_id: int,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        escludi_ritirate: bool = True,
        escludi_info: bool = True,
        sort_by: str | None = None,
        sort_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int, int, int]:
        return self._list_giornale(
            perimetro_sql="""
                (entity_type = 'LOTTO' AND entity_id = %s)
                OR (entity_type = 'FATTURA' AND entity_id IN (
                        SELECT lf.fattura_id
                          FROM vendite.fatturazione_lotti_fatture lf
                         WHERE lf.lotto_id = %s))
            """,
            perimetro_params=[int(lotto_id), int(lotto_id)],
            limit=limit,
            offset=offset,
            escludi_ritirate=escludi_ritirate,
            escludi_info=escludi_info,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

    # Scopo: L'ERRORE VIVO di un'entita' — la riga ERROR piu' recente e non
    #        ritirata, o `None`. E' la fonte del banner in testa al drawer della
    #        fattura («chi apre una fattura in errore la apre per quello»).
    #
    # ⭐ UNA FONTE SUA, e non la prima riga della pagina della Storia (2026-09-27,
    #    brief-db-liste-datatable-grezze §3.1): da quando la Storia e' la lista a
    #    catalogo `vendite.giornale`, l'ordine della pagina lo decide il preset
    #    (`quando desc`) o l'operatore — e un banner che legge «il primo ERROR
    #    della pagina» dice «nessun errore» appena l'errore scivola a pagina 2,
    #    o appena qualcuno ordina per `quando` crescente. Nessun errore, un
    #    documento in errore che a video sembra sano.
    # ⭐ Lo STESSO corpo dei tre lettori (`_list_giornale`, una pagina da una
    #    riga), non una quarta query: la riga esce con la stessa decodifica
    #    (`etichetta_key`) e la stessa regola sulle ritirate della Storia — il
    #    banner e la scheda parlano dello stesso fatto con lo stesso nome.
    # ⚠️ `gravita = 'ERROR'` esatto, e la gravita' NULL resta FUORI: e' il
    #    segnale di un vincolo allargato (la vista lo dichiara), non un errore
    #    del documento — la Storia la mostra col trattino, il banner rosso
    #    direbbe una cosa che non e'. Stessa regola del banner di prima.
    # Perimetro: sola lettura. ⚠️ Nessun cancello qui: la vista e'
    #    `security_invoker`, e il chiamante (`get_fattura_dettaglio`) la chiede
    #    solo DOPO la testata, che e' il cancello.
    def get_giornale_errore_vivo(
        self, *, entity_type: str, entity_id: int,
    ) -> dict[str, Any] | None:
        righe, _vive, _ritirate, _info = self._list_giornale(
            perimetro_sql="entity_type = %s AND entity_id = %s AND gravita = 'ERROR'",
            perimetro_params=[entity_type, int(entity_id)],
            limit=1,
            offset=0,
            escludi_ritirate=True,
            escludi_info=False,
            sort_by="quando",
            sort_dir="desc",
            con_conteggi=False,
            # Il banner non mostra di chi e' la riga: e' la fattura aperta.
            con_entita_display=False,
        )
        return righe[0] if righe else None

    # Scopo: i registri che il filtro `registro` del giornale trasversale puo'
    #        nominare — i `codice_interno` di `config.registri_giornale`, TUTTI,
    #        ritirati compresi (brief-db-registri-giornale-catalogo §8.4): le
    #        righe vecchie del diario si leggono anche a registro ritirato, e un
    #        deep-link scritto ieri non deve diventare un 400 domani.
    # ⭐ Letto dal catalogo a ogni richiesta che porta il filtro, e non pinnato
    #    in una costante con un presidio: una costante e' una sede in piu' (con
    #    un test che la tiene allineata), il catalogo e' LA sede. Costo: una
    #    `SELECT` da quattro righe, solo quando `registro` e' presente.
    # ⚠️ Nessun cast a `attivo`: la tabella non ce l'ha (D3 del brief).
    def registri_giornale_ammessi(self) -> frozenset[str]:
        with connection.cursor() as cursor:
            cursor.execute("SELECT codice_interno FROM config.registri_giornale")
            return frozenset(row[0] for row in cursor.fetchall())

    # Scopo: il GIORNALE TRASVERSALE — «cosa e' andato storto, su tutto,
    #        nell'ultimo periodo»: la Storia di tutte le entita' insieme,
    #        filtrata per gravita' (pezzo G del piano BE/FE dell'osservabilita',
    #        2026-09-19 — la meta' «vista errori» del Passo B).
    #
    # ⭐ TERZO LETTORE della stessa vista e dello STESSO corpo (`_list_giornale`):
    #    non un aggregato nuovo. Il perimetro qui non e' un'entita' ma un
    #    insieme di filtri — ed e' la ragione per cui `_list_giornale` riceve il
    #    perimetro come SQL + parametri: serve «una riga», «un lotto e le sue
    #    fatture» e «tutto cio' che passa questi filtri» con lo stesso corpo.
    #    Regole di gravita', conteggi e ordinamento restano in una sede sola.
    # ⭐ Al TERZO consumatore il lettore del giornale dovrebbe uscire da
    #    `vendite_repository` — «al SECONDO dominio va spostato in `core`». Il
    #    dominio e' ancora `vendite` (tre lettori, un dominio), quindi non
    #    ancora: si dichiara qui perche' il prossimo (pratiche) lo sposta.
    #
    # I filtri, tutti in whitelist e tutti nei `params`:
    #   `gravita`    sottoinsieme di `GIORNALE_GRAVITA`. ⚠️ Con `ERROR` si
    #                INCLUDE il `NULL` — la riga che dichiara un difetto (stessa
    #                regola del pannello lotto e del `rango_gravita`).
    #   `registri`   `codice_interno` di `config.registri_giornale`, `None` =
    #                tutti. ⛔ Li valida il SERVICE contro il catalogo
    #                (`registri_giornale_ammessi`): qui viaggiano nei
    #                params e basta, e un valore ignoto darebbe zero righe
    #                — e' la ragione per cui il cancello sta a monte.
    #   `entity_type` codice di `config.tipi_entita`, esatto.
    #   `data_da`/`data_a` su `quando`, `[da, a + 1 giorno)`: il floor lo mette
    #                il frontend (e' consultazione, non coda di lavoro).
    #                ⭐ E' il predicato che gli indici per tempo di P-3
    #                (`20260919-05`) servono, spinto dentro i quattro rami.
    #   `filo`       uuid: `tx_id` OPPURE `correlation_id` (R-2: filtrare per
    #                filo tiene `EVENT_LOG` + `TASK_RUN` e butta le righe
    #                scritte per una persona — il default NON filtra per filo).
    #   `solo_vive`  esclude le segnalazioni ritirate (`ritirate` dice quante).
    # ⛔ Niente `context`/`payload`: espone le stesse colonne della Storia. Gli
    #    appunti forensi restano nella Storia dell'entita' (vincolo del Passo A).
    # ⚠️ La vista e' `security_invoker`: il perimetro emittente lo applica la
    #    connessione di chi legge, riga per riga e nei CONTEGGI (la CTE conta
    #    sulla vista gia' filtrata). Fuori scope la riga non c'e', e il totale
    #    dice il numero VISTO — presidiato sul DB vero con due emittenti
    #    costruiti (`test_giornale_trasversale_perimetro`).
    def list_giornale_trasversale(
        self,
        *,
        gravita: Sequence[str],
        registri: Sequence[str] | None = None,
        entity_type: str | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
        filo: str | None = None,
        solo_vive: bool = True,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        sort_by: str | None = None,
        sort_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int, int, int]:
        gravita_valide = [g for g in gravita if g in GIORNALE_GRAVITA]
        registri_validi = list(registri) if registri is not None else None
        # Il giorno e' quello dell'AZIENDA (BB): fino al 2026-10-09 era
        # `quando >= %s::date`, la mezzanotte della sessione (UTC), e un evento
        # fra mezzanotte e le 2 di Roma finiva sotto il giorno prima.
        giorno_sql, giorno_params = predicato_giorno_operativo("quando", data_da, data_a)
        return self._list_giornale(
            perimetro_sql=f"""
                (gravita = ANY(%s::text[]) OR (gravita IS NULL AND 'ERROR' = ANY(%s::text[])))
                AND (%s::text[] IS NULL OR registro = ANY(%s::text[]))
                AND (%s::text IS NULL OR entity_type = %s)
                AND {giorno_sql}
                AND (%s::uuid IS NULL OR tx_id = %s::uuid OR correlation_id = %s::uuid)
            """,
            perimetro_params=[
                gravita_valide, gravita_valide,
                registri_validi, registri_validi,
                entity_type, entity_type,
                *giorno_params,
                filo, filo, filo,
            ],
            limit=limit,
            offset=offset,
            escludi_ritirate=solo_vive,
            escludi_info=False,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

    # Scopo: `entita_display` sulle righe di UNA pagina — il codice del lotto,
    #        «serie/numero» del documento — risolto qui nel backend (memoria:
    #        liste API → display via JOIN, mai lookup client-side).
    # ⭐ UNA query sulla pagina e NON un JOIN dentro la query di `_list_giornale`:
    #    la' il JOIN starebbe PRIMA di `LIMIT`, cioe' su tutto il perimetro (che
    #    con un intervallo largo sono migliaia di righe per una pagina di 25).
    #    Qui costa una lettura per chiave sulla pagina.
    # ⭐ La chiama `_list_giornale`, cioe' TUTTI E TRE i lettori (2026-09-27):
    #    la Storia della fattura e del lotto sono la stessa lista a catalogo
    #    del trasversale (`vendite.giornale`), e la colonna «Riferimento» legge
    #    questo campo. Fino a quel giorno la chiamava il solo trasversale, e
    #    sulle due Storie la colonna sarebbe uscita VUOTA senza nessun errore —
    #    un campo dichiarato dal catalogo e trasportato da un lettore su tre.
    # ⚠️ I due JOIN attraversano tabelle in RLS: fuori scope darebbero `NULL` —
    #    ma fuori scope la riga del giornale NON c'e' (la vista e'
    #    `security_invoker`), quindi un `NULL` qui e' un'entita' cancellata, non
    #    una nascosta. Coerente, e nel test di perimetro.
    # ⚠️ `TASK_RUN` e gli altri tipi restano `None`: il display e' un'offerta.
    def _aggiungi_entita_display(self, righe: list[dict[str, Any]]) -> None:
        lotti = sorted({int(r["entity_id"]) for r in righe
                        if r["entity_type"] == "LOTTO" and r["entity_id"] is not None})
        fatture = sorted({int(r["entity_id"]) for r in righe
                          if r["entity_type"] == "FATTURA" and r["entity_id"] is not None})
        display: dict[tuple[str, int], str] = {}
        if lotti or fatture:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 'LOTTO', l.id, l.codice::text
                      FROM vendite.fatturazione_lotti l
                     WHERE l.id = ANY(%s::bigint[])
                    UNION ALL
                    SELECT 'FATTURA', f.id,
                           -- ⭐ Il numero parlante dalla SEDE UNICA a DB
                           --    (`fn_numero_documento_fattura`, NULL sulla non
                           --    numerata, mai la stringa vuota), come gli altri
                           --    quattro lettori di questo file: composto qui a
                           --    mano era una forma diversa («serie/numero») e
                           --    con `concat_ws` la bozza usciva '' invece di
                           --    cadere sul ripiego. L'id fra parentesi finche'
                           --    la bozza non ha un numero.
                           COALESCE(
                               vendite.fn_numero_documento_fattura(f.numero, f.serie),
                               '(' || f.id::text || ')'
                           )
                      FROM vendite.fatture f
                     WHERE f.id = ANY(%s::bigint[])
                    """,
                    [lotti, fatture],
                )
                for tipo, entity_id, testo in cursor.fetchall():
                    display[(str(tipo), int(entity_id))] = str(testo)
        for r in righe:
            chiave = (r["entity_type"], r["entity_id"])
            r["entita_display"] = display.get(chiave) if r["entity_id"] is not None else None

    # Scopo: il corpo unico del giornale — CTE dei conteggi, rango di gravita',
    #        filtri, ordinamento e mappatura delle righe. Cambia SOLO il
    #        perimetro: una riga (la fattura) oppure un lotto e le sue fatture.
    #
    # ⭐ ESTRATTO alla 2a occorrenza (regola del 2). Le due letture devono dare
    #    le stesse regole di gravita', gli stessi conteggi e lo stesso
    #    ordinamento: due copie sarebbero identiche il primo giorno e divergenti
    #    al primo ritocco — e qui divergere vuol dire che lo stesso evento si
    #    legge in due modi a seconda della scheda da cui lo guardi.
    # ⚠️ Il perimetro arriva come SQL e parametri, non come valori: e' l'unico
    #    modo di servire «una riga» e «un insieme calcolato dal database» con lo
    #    stesso corpo. Le due stringhe sono LETTERALI scritte qui sopra — nessun
    #    input dell'utente le raggiunge.
    def _list_giornale(
        self,
        *,
        perimetro_sql: str,
        perimetro_params: list[Any],
        limit: int,
        offset: int,
        escludi_ritirate: bool,
        escludi_info: bool,
        sort_by: str | None,
        sort_dir: str | None,
        con_conteggi: bool = True,
        con_entita_display: bool = True,
    ) -> tuple[list[dict[str, Any]], int, int, int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        # ⭐ L'ORDINE DI DEFAULT E' IL TEMPO, dal piu' recente
        #    (`GIORNALE_ORDINE_DEFAULT`, dal 2026-09-27: e' il preset della lista
        #    a catalogo, la stessa per i tre lettori). La gravita' resta a un
        #    clic, sulla sua colonna.
        # ⛔ E l'ordinamento sta QUI e non nel client: la lista e' PAGINATA lato
        #    server, quindi ordinare a valle ordinerebbe la sola pagina
        #    visibile — «il piu' grave» diventerebbe «il piu' grave fra i primi
        #    50 in ordine di tempo», che e' un difetto silenzioso: a video
        #    somiglia in tutto a un elenco ordinato bene.
        order_clause = _giornale_order_clause(sort_by, sort_dir)
        with connection.cursor() as cursor:
            # ⚠️ I TRE conteggi si calcolano PRIMA dei filtri, in una CTE: una
            # finestra sulla query filtrata non vedrebbe le righe nascoste, e
            # dire quante se ne nascondono e' meta' del mestiere di nasconderle.
            cursor.execute(
                """
                WITH tutte AS (
                    SELECT riga_key, registro, riga_id, quando, gravita, cosa,
                           tx_id, correlation_id, auth_user_id, user_insert,
                           entity_type, entity_id,
                           COALESCE(disabilitato, false) AS ritirata,
                           -- ⭐ IL RANGO DELLA GRAVITA', qui e non nel client:
                           --    il vocabolario normalizzato della vista e'
                           --    INFO | WARN | ERROR, e ordinarlo per TESTO
                           --    darebbe ERROR < INFO < WARN — cioe' un ordine
                           --    alfabetico spacciato per una scala.
                           -- ⚠️ NULL (e ogni parola non prevista) pesa come un
                           --    ERROR, non come un INFO. La vista dichiara che
                           --    una gravita' nulla significa «un vincolo si e'
                           --    allargato e la mappa e' rimasta indietro»:
                           --    mandarla in fondo la renderebbe invisibile
                           --    dalla seconda pagina in giu', che e' il modo
                           --    piu' efficace di nascondere un difetto. A video
                           --    resta distinguibile — trattino e colore neutro
                           --    (`gravitaGiornaleSeverity`), quindi nessuno la
                           --    scambia per un errore vero.
                           CASE gravita
                               WHEN 'INFO' THEN 1
                               WHEN 'WARN' THEN 2
                               ELSE 3
                           END AS rango_gravita
                      FROM script.vw_giornale_entita
                     WHERE {perimetro_sql}
                ), conteggi AS (
                    SELECT COUNT(*) FILTER (WHERE NOT ritirata) AS vive,
                           COUNT(*) FILTER (WHERE ritirata)     AS ritirate,
                           -- ⚠️ Le INFO si contano fra le righe che il filtro
                           -- sulle ritirate LASCIA PASSARE (solo le vive, o anche
                           -- le ritirate quando le si chiede): sono quelle che il
                           -- filtro «info» toglie davvero. Contate sulle sole vive
                           -- con le ritirate a video, il totale mostrato
                           -- supererebbe le righe di tante INFO ritirate — e il
                           -- paginatore avrebbe pagine finali vuote.
                           COUNT(*) FILTER (
                               WHERE rango_gravita = 1 AND (NOT %s OR NOT ritirata)
                           ) AS info_vive
                      FROM tutte
                )
                SELECT t.riga_key, t.registro, t.quando, t.gravita, t.cosa,
                       t.tx_id, t.correlation_id, t.auth_user_id, t.user_insert,
                       t.ritirata, t.entity_type, t.entity_id,
                       c.vive, c.ritirate, c.info_vive,
                       ed.etichetta_key
                  FROM tutte t
                  CROSS JOIN conteggi c
                  -- ⭐ L'INDIRIZZO i18n DEL FATTO, per le sole righe del diario.
                  -- `cosa` e' il CODICE dell'evento solo su `EVENT_LOG`: sugli
                  -- altri tre registri e' un messaggio o «task · stato · codice»,
                  -- e agganciare il catalogo li' significherebbe cercare una
                  -- frase in una tabella di codici. Il ramo sta nella ON, non in
                  -- un filtro a valle.
                  -- ⚠️ Il JOIN sta QUI e non dentro `tutte`: quella CTE alimenta
                  -- anche i conteggi, e una riga in piu' li falserebbe. Oggi non
                  -- puo' moltiplicare (`codice` e' la PK di `config.eventi_dominio`),
                  -- ma la posizione la rende vera per costruzione e non per
                  -- coincidenza con un indice.
                  -- ⛔ Nessun filtro su `obsoleto_dal`: il diario e' append-only e
                  -- le sue righe vecchie devono restare LEGGIBILI. Un evento
                  -- ritirato oggi ha scritto ieri, ed e' la stessa regola dei
                  -- codici errore ritirati, che restano e risolvono.
                  LEFT JOIN config.eventi_dominio ed
                         ON t.registro = 'EVENT_LOG'
                        AND ed.codice = t.cosa
                 WHERE (NOT %s OR NOT t.ritirata)
                   -- ⚠️ «Non-INFO» e' TUTTO CIO' CHE NON E' INFO, NULL COMPRESO,
                   -- e per questo si filtra sul RANGO e non con un
                   -- `gravita IN ('WARN','ERROR')`: una gravita' nulla e'
                   -- esattamente la riga da non perdere, e un filtro scritto
                   -- per elencazione la butterebbe via in silenzio.
                   AND (NOT %s OR t.rango_gravita > 1)
                 ORDER BY {order_clause}
                 LIMIT %s OFFSET %s
                """.format(perimetro_sql=perimetro_sql, order_clause=order_clause),  # noqa: S608
                [
                    *perimetro_params,
                    bool(escludi_ritirate),  # conteggio delle INFO (CTE)
                    bool(escludi_ritirate), bool(escludi_info),
                    safe_limit, safe_offset,
                ],
            )
            rows = cursor.fetchall()

        # ⚠️ Su zero righe non c'e' nessuna riga da cui leggere i conteggi. E' il
        # caso «tutte ritirate» — o, sul lotto, «tutte INFO»: la CTE li avrebbe,
        # ma i filtri non lasciano passare nulla da cui prenderli. Si ripiega su
        # una domanda secca, con lo STESSO perimetro.
        # ⚠️ `con_conteggi=False` salta il ripiego: e' il lettore che vuole UNA
        #    riga e non un elenco (`get_giornale_errore_vivo`), dove i numeri non
        #    li legge nessuno — e il caso senza righe e' quello di gran lunga piu'
        #    frequente, cioe' una seconda query a ogni apertura per niente.
        if rows:
            vive, ritirate, info_vive = int(rows[0][12]), int(rows[0][13]), int(rows[0][14])
        elif not con_conteggi:
            vive, ritirate, info_vive = 0, 0, 0
        else:
            vive, ritirate, info_vive = self._conta_giornale(
                perimetro_sql, perimetro_params, escludi_ritirate=escludi_ritirate,
            )
        risultato: list[dict[str, Any]] = [
            {
                "riga_key": str(row[0]),
                "registro": str(row[1]),
                "quando": None if row[2] is None else row[2].isoformat(),
                # ⚠️ `gravita` puo' essere NULL, e non e' un caso da ignorare: la
                # vista lo dichiara come il segnale che «un vincolo si e'
                # allargato e la mappa e' rimasta indietro». Passa cosi' com'e'.
                "gravita": row[3],
                "cosa": row[4],
                "tx_id": None if row[5] is None else str(row[5]),
                # ⚠️ NULL su due registri su quattro PER COSTRUZIONE della vista
                # (rilievo R-2): `LOTTO_LOG` e `FATTURA_LOG` non hanno un filo.
                # Non e' un dato mancante, e' un dato che li' non esiste.
                "correlation_id": None if row[6] is None else str(row[6]),
                "auth_user_id": None if row[7] is None else int(row[7]),
                "user_insert": row[8],
                "ritirata": bool(row[9]),
                # ⭐ DI CHI e' la riga. Sul giornale della fattura e' sempre la
                # stessa e sembra ridondante; sul lotto e' l'informazione che
                # rende utile il pannello — «il lotto dice che e' andata male,
                # la fattura 19205 dice perche'».
                "entity_type": row[10],
                "entity_id": None if row[11] is None else int(row[11]),
                # ⭐ LA CHIAVE i18n DEL FATTO (`config.eventi_dominio.etichetta_key`),
                # per le sole righe `EVENT_LOG`. `None` ovunque altrove, e anche
                # su un codice evento che il catalogo non dichiara — `event_log`
                # non ha una FK verso quel catalogo, ed e' deliberato (il diario
                # non deve smettere di scrivere per un problema di
                # configurazione).
                # ⚠️ Chi rende usa `labelOrCode(t, te, etichetta_key, cosa)`: il
                # ripiego e' il CODICE grezzo, mai il path della chiave. Fino al
                # 2026-08-31 il catalogo dichiarava questo indirizzo e non lo
                # leggeva nessuno — un contratto emesso, trasportato e non
                # consumato, la stessa forma di `ui_action`.
                "etichetta_key": row[15],
            }
            for row in rows
        ]
        # ⚠️ Una query in piu' (le etichette «di chi e' la riga»): la salta chi
        #    non la mostra (`get_giornale_errore_vivo`, a ogni dettaglio fattura).
        if con_entita_display:
            self._aggiungi_entita_display(risultato)
        return risultato, vive, ritirate, info_vive

    # Scopo: i conteggi del giornale quando la pagina non ha righe da cui
    #        leggerli — vedi il ripiego qui sopra. Stesso perimetro, per
    #        costruzione: riceve la stessa coppia SQL/parametri.
    def _conta_giornale(
        self, perimetro_sql: str, perimetro_params: list[Any], *, escludi_ritirate: bool,
    ) -> tuple[int, int, int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) FILTER (WHERE NOT COALESCE(disabilitato, false)),
                       COUNT(*) FILTER (WHERE COALESCE(disabilitato, false)),
                       -- Le INFO come nella CTE di `_list_giornale`: fra le
                       -- righe che il filtro sulle ritirate lascia passare.
                       COUNT(*) FILTER (
                           WHERE gravita = 'INFO'
                             AND (NOT %s OR NOT COALESCE(disabilitato, false))
                       )
                  FROM script.vw_giornale_entita
                 WHERE {perimetro_sql}
                """.format(perimetro_sql=perimetro_sql),  # noqa: S608
                [bool(escludi_ritirate), *perimetro_params],
            )
            row = cursor.fetchone()
        if not row:
            return 0, 0, 0
        return int(row[0]), int(row[1]), int(row[2])

    # Scopo: I motivi che impediscono di riportare «da emettere» un elenco di
    #        attivita' fatturabili. Lettura pura: nessuna scrittura, nessun
    #        raise di dominio — serve a SPIEGARE invece di far fallire.
    # Perimetro: `script.fn_check_attivita_riportabile_da_emettere`, che porta
    #        con se' il proprio cancello di scope (il JOIN su
    #        `vendite.commesse_attivita`, che ha la RLS).
    # Risultato: lista di motivi; `[]` se il verbo e' ammesso su tutte.
    def check_attivita_riportabili_da_emettere(
        self, attivita_fatturabili_ids: list[int],
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_check_attivita_riportabile_da_emettere(%s::bigint[])",
                [attivita_fatturabili_ids],
            )
            row = cursor.fetchone()
            assert row is not None
        # ⛔ Lettura per posizione: il `jsonb` arriva come STRINGA, e senza
        #    `jsonb_out` `list(payload)` itera i CARATTERI — `"[]"` diventa
        #    `['[', ']']`, cioe' **due motivi** dove non ce n'era nessuno, e il
        #    verbo risulterebbe bloccato su righe perfettamente riportabili.
        return list(jsonb_out(row[0]) or [])

    # Scopo: Rimette in coda di fatturazione un elenco di attivita' RESIDUE —
    #        la madre DB del verbo «Riporta da emettere».
    # Perimetro e risultato atteso: UNA sola `SELECT` sulla funzione madre, che
    #        e' atomica per costruzione: libera le attivita', riporta a
    #        NON_EMESSA le righe di commessa passate a EMESSA per causa loro e
    #        scrive l'evento di registro, tutto nella stessa transazione.
    #        ⛔ Niente `transaction.atomic()` con due chiamate: sarebbe una
    #        seconda implementazione di un'atomicita' che il database gia'
    #        garantisce.
    # Risultato: dict con `riportate` e `riemesse_attivita`.
    def riporta_attivita_da_emettere(
        self, attivita_fatturabili_ids: list[int],
    ) -> dict[str, int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT riportate, riemesse_attivita
                FROM vendite.fn_riporta_attivita_da_emettere(%s::bigint[])
                """,
                [attivita_fatturabili_ids],
            )
            row = cursor.fetchone()
            assert row is not None
        return {"riportate": int(row[0]), "riemesse_attivita": int(row[1])}

