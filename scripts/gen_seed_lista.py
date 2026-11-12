# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Generatore delle righe di seed per una lista configurabile
#        (`ui.lista_definizione`, `lista_colonna`, `lista_preset`,
#        `lista_preset_colonna`), a partire dal componente .vue che oggi la
#        disegna con una DataTable grezza e, quando esiste, dalla vista DB che
#        la alimenta.
#
#        Nasce dalla migrazione delle 34 liste del Gruppo A
#        (docs/it/dev/work-in-progress/piano-migrazione-primevue-5.md §8-bis):
#        269 colonne da configurare a mano sono un lavoro meccanico, e il
#        meccanico si genera.
#
#        Il lavoro si fa a piu' mani e su piu' giorni, quindi lo script parte
#        SEMPRE da cosa esiste gia' — nei CSV di seed e nel DB — e si rifiuta
#        di rigenerare una lista gia' fatta:
#          --stato            fotografia di tutte le liste (CSV vs DB)
#          --esporta CODICE   recupera in CSV il lavoro fatto in-app dai
#                             pannelli di amministrazione, che altrimenti vive
#                             solo nel DB di chi l'ha fatto
#        Gli id nuovi si allocano oltre il massimo fra CSV e DB, cosi' due
#        persone che lavorano in parallelo non si scavalcano.
#
# Note: NON scrive sul DB e NON applica migrazioni. Emette righe CSV da
#       rivedere e da far confluire nei CSV di seed dal team DB
#       (regola: le azioni DB non partono dall'agente).
#       Quello che genera e' una BOZZA: i campi curati (priorita, gruppo,
#       larghezza, sensibile) escono con i default e vanno decisi a mano —
#       lo script li elenca nel report finale invece di far finta di saperli.
# ------------------------------------------------------------
"""Genera le righe di seed per una lista configurabile.

Uso tipico (dalla root del repo):

    backend/.venv/bin/python scripts/gen_seed_lista.py \\
        --codice vendite.fatture \\
        --descrizione "Elenco Fatture" \\
        --vista vendite.vw_fatture_lista \\
        --vue frontend/src/vendite/views/FattureListView.vue

Cosa e' gia' stato fatto, da chiunque e ovunque:

    backend/.venv/bin/python scripts/gen_seed_lista.py --stato

Recupero del lavoro fatto in-app (lista configurata dai pannelli di
amministrazione: vive nel DB ma non nei CSV, e su un'installazione pulita
sparirebbe):

    backend/.venv/bin/python scripts/gen_seed_lista.py --esporta catalogo.uom_tipi

Autoverifica (confronta una lista gia' configurata con la sua vista):

    backend/.venv/bin/python scripts/gen_seed_lista.py --verifica vendite.ddt

Controllo di consegna, da lanciare PRIMA di passare un lotto al team BE:
confronta il flag `ordinabile` del seed con la whitelist di ordinamento del
repository che serve la lista. Una colonna `ordinabile=t` fuori whitelist non
da' errore da nessuna parte — a video resta una freccia che non ordina.
Non usa il DB, quindi gira ovunque ci sia il repo:

    python scripts/gen_seed_lista.py --verifica-ordinamento
    python scripts/gen_seed_lista.py --verifica-ordinamento vendite.ordini
"""

from __future__ import annotations

import argparse
import ast
import csv
import io
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

# Import pigro: `--verifica-ordinamento` legge solo CSV e sorgenti Python, e
# deve poter girare dove psycopg non c'e' (server DB, CI). Chi ha bisogno del
# DB se lo sente dire da connetti(), non all'avvio.
try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = ROOT / "db/changelog/migrations_v2/80_data/sql/ui"
LOCALES = ROOT / "frontend/src/locales/it.json"

# Mappa tipo PostgreSQL -> ui.tipo_dato (enum: string|numeric|date|datetime|boolean|enum).
# Le voci non mappate finiscono a 'string' e vengono segnalate nel report: e'
# preferibile un default onesto e visibile a un'inferenza silenziosa.
TIPO_DATO = {
    "character varying": "string", "text": "string", "character": "string",
    "uuid": "string", "jsonb": "string", "json": "string",
    "integer": "numeric", "bigint": "numeric", "smallint": "numeric",
    "numeric": "numeric", "double precision": "numeric", "real": "numeric",
    "date": "date",
    "timestamp without time zone": "datetime",
    "timestamp with time zone": "datetime",
    "boolean": "boolean",
}

# Formatter FE riconosciuti nei template di cella -> ui.lista_colonna.formato.
# I valori a destra devono esistere in CellaConfigurabile.formatValue: uno
# sconosciuto non da' errore, cade nel `default` e mostra il valore grezzo.
FORMATO_DA_TEMPLATE = {
    "displayDate": "date_short",
    "displayDateTime": "datetime_short",
    "displayTimestamp": "datetime_short",
    "formatCurrency": "currency_eur",
    "formatNumber": "number",
}

# Ripiego per le colonne che nel DB non esistono (calcolate dal FE o dal BE):
# il formatter usato nel .vue dice di che dato si tratta meglio di `string`.
TIPO_DA_FORMATO = {
    "date_short": "date", "datetime_short": "datetime",
    "currency_eur": "numeric", "number": "numeric",
}

# ── Contratto seed <-> backend: dove vive la whitelist di ordinamento ──────
#
# `<ListaConfigurabile>` monta le Column con `:field="campo_sorgente"`, quindi
# l'`order_by` che arriva al backend porta il nome FISICO della colonna. Una
# colonna `ordinabile=t` il cui `campo_sorgente` non e' nella whitelist del
# repository non da' errore: il repository ripiega in silenzio sull'ordinamento
# di default. A video resta una freccia che non ordina — il difetto piu' caro
# che questo seed possa produrre, perche' nessuno se ne accorge.
#
# Questa mappa dice, per ogni lista, DOVE leggere quella whitelist. Va tenuta
# completa: `--verifica-ordinamento` si ferma sulle liste che non trova qui,
# invece di dichiararle a posto (una lista saltata in silenzio e' esattamente
# come non aver fatto il controllo).
#
# Forme supportate, tutte incontrate davvero:
#   (file, costante)              costante di modulo, dict oppure set
#   (file, costante, "class X")   costante dentro una classe
#   (file, "_CODA_META", chiave)  mappa annidata: <chiave>["order_cols"]
#   (file, costante)              anche `NOME = colonne_identita("a", ...)`
WHITELIST_BE: dict[str, tuple] = {
    # Le sei geografiche (2026-09-27, brief-db-liste-datatable-grezze riga 9):
    # whitelist `colonne_identita` di `geo_repository`.
    "config.stati": ("apps/anagrafiche/db/geo_repository.py", "_STATI_ORDER_COLS"),
    "config.regioni": ("apps/anagrafiche/db/geo_repository.py", "_REGIONI_ORDER_COLS"),
    "config.province": ("apps/anagrafiche/db/geo_repository.py", "_PROVINCE_ORDER_COLS"),
    "config.comuni": ("apps/anagrafiche/db/geo_repository.py", "_COMUNI_ORDER_COLS"),
    "config.codici_postali": ("apps/anagrafiche/db/geo_repository.py", "_CODICI_POSTALI_ORDER_COLS"),
    "config.toponomastica": ("apps/anagrafiche/db/geo_repository.py", "_TOPONOMASTICA_ORDER_COLS"),
    "anagrafiche.clienti": ("apps/anagrafiche/db/clienti_repository.py", "_CLIENTI_ORDER_COLS"),
    "anagrafiche.soggetti": ("apps/anagrafiche/db/soggetti_repository.py", "_SOGGETTI_ORDER_COLS"),
    "anagrafiche.fornitori": ("apps/anagrafiche/db/fornitori_repository.py", "_FORNITORI_ORDER_COLS"),
    "anagrafiche.categorie_clienti": ("apps/anagrafiche/db/categorie_clienti_repository.py", "_ORDER_COLS"),
    "anagrafiche.indirizzi": ("apps/anagrafiche/db/indirizzi_repository.py", "_ORDER_COLS"),
    "anagrafiche.emittenti_fiscali": ("apps/anagrafiche/db/emittenti_fiscali_repository.py",
                                      "_EMITTENTI_ORDER_COLS"),
    # Annidata nella classe: nel modulo esiste anche `_EMITTENTI_ORDER_COLS`,
    # che contiene `_ORDER_COLS` come sottostringa. Senza l'ancora di classe si
    # leggerebbe la costante sbagliata.
    "anagrafiche.emittente_billing_account": ("apps/anagrafiche/db/emittenti_fiscali_repository.py",
                                              "_ORDER_COLS",
                                              "class EmittentiFiscaliBillingAccountRepository"),
    # Registri di numerazione (2026-09-01, brief-be-fe-crud-registri-di-
    # numerazione F1/F3). Costante di MODULO, come vuole la convenzione del
    # 7° lotto: una whitelist annidata nella classe si svuota quando un test
    # mocka il repository.
    "vendite.registri_numerazione": ("apps/vendite/db/registri_repository.py", "_ORDER_COLS"),
    # Magazzino, Lotto 2 (2026-09-18): otto liste, sei whitelist — le due
    # famiglie del documento interno condividono la proiezione di TESTATA;
    # le righe hanno la loro (la quantita' ha un nome fisico diverso).
    "magazzino.inventari": ("apps/magazzino/db/magazzino_repository.py", "DOCUMENTI_SORT_COLUMNS"),
    "magazzino.rettifiche": ("apps/magazzino/db/magazzino_repository.py", "DOCUMENTI_SORT_COLUMNS"),
    # Righe dei documenti di vendita (2026-09-28, brief-db-liste-righe-
    # documento lotto A): whitelist di modulo del repository, con le colonne
    # gemelle importate dal mixin (`**COLONNE_RIGHE_COMMERCIALI`).
    "vendite.preventivo_righe": ("apps/vendite/db/preventivi_repository.py", "_ORDER_COLS_RIGHE"),
    "vendite.ordine_righe": ("apps/vendite/db/ordini_repository.py", "_ORDER_COLS_RIGHE"),
    "vendite.ddt_righe": ("apps/vendite/db/ddt_repository.py", "_ORDER_COLS_RIGHE"),
    "vendite.reso_righe": ("apps/vendite/db/resi_repository.py", "_ORDER_COLS_RIGHE"),
    # La distinta base (2026-09-28, lotto C).
    "catalogo.articolo_componenti": ("apps/catalogo/db/catalogo_bom_repository.py",
                                     "COMPONENTI_SORT_COLUMNS"),
    # Le righe di una fattura (2026-09-28, lotto C).
    "vendite.fattura_righe": ("apps/vendite/db/fatture_repository.py", "_ORDER_COLS_RIGHE_FATTURA"),
    # Le righe di un contratto (2026-09-30, lotto D).
    "vendite.contratto_righe": ("apps/vendite/db/contratti_repository.py", "_ORDER_COLS_RIGHE_CONTRATTO"),
    # Le righe di un'offerta (2026-10-05, gemella della 103).
    "vendite.offerta_righe": ("apps/vendite/db/offerte_repository.py", "_ORDER_COLS_RIGHE_OFFERTA"),
    "magazzino.inventario_righe": ("apps/magazzino/db/magazzino_repository.py",
                                   "INVENTARIO_RIGHE_SORT_COLUMNS"),
    "magazzino.rettifica_righe": ("apps/magazzino/db/magazzino_repository.py",
                                  "RETTIFICA_RIGHE_SORT_COLUMNS"),
    "magazzino.inventario_piano": ("apps/magazzino/db/magazzino_repository.py", "PIANO_SORT_COLUMNS"),
    "magazzino.disponibilita": ("apps/magazzino/db/magazzino_repository.py", "DISPONIBILITA_SORT_COLUMNS"),
    "magazzino.disponibilita_articoli": ("apps/magazzino/db/magazzino_repository.py",
                                         "DISPONIBILITA_ARTICOLI_SORT_COLUMNS"),
    "magazzino.movimenti": ("apps/magazzino/db/magazzino_repository.py", "MOVIMENTI_SORT_COLUMNS"),
    "magazzino.magazzini": ("apps/magazzino/db/anagrafiche_magazzino_repository.py", "MAGAZZINI_SORT_COLUMNS"),
    "magazzino.ubicazioni": ("apps/magazzino/db/anagrafiche_magazzino_repository.py", "UBICAZIONI_SORT_COLUMNS"),
    "magazzino.lotti": ("apps/magazzino/db/anagrafiche_magazzino_repository.py", "LOTTI_SORT_COLUMNS"),
    "config.utilities_tipi_ruolo": ("apps/config/db/utilities_tipi_ruolo_repository.py", "_ORDER_COLS"),
    "config.tipi_ruolo_tipi_indirizzo": ("apps/config/db/tipi_ruolo_tipi_indirizzo_repository.py",
                                         "_ORDER_COLS"),
    # ⚠️ Era `_PRATICHE_ORDER_COLS`. Rinominata dal BE il 2026-08-02 nella
    # passata del 7° lotto: le whitelist passano da privata/`ClassVar` a
    # costante di MODULO pubblica, perche' un gate che le derivava dalla classe
    # si svuotava quando un test mockava il repository — il controllo dipendeva
    # dal mock invece che dal codice. La regola che ne hanno tratto («una
    # whitelist e' un dato, non un comportamento») e' giusta, ma e' la SECONDA
    # volta in un giorno che questo registro resta indietro su una rinomina,
    # dopo `AUDIT_ORDER_COLUMNS`. Il presidio se ne accorge e si ferma, che e'
    # il comportamento voluto; ma quando il BE rinomina una whitelist,
    # aggiornare qui e' parte della stessa passata.
    "pratiche.pratiche": ("apps/pratiche/db/pratiche_repository.py", "PRATICHE_ORDER_COLS"),
    "vendite.lotti": ("apps/vendite/db/vendite_repository.py", "LOTTI_SORT_COLUMNS"),
    "vendite.contratti": ("apps/vendite/db/contratti_repository.py", "_ORDER_COLS_CONTRATTI"),
    "vendite.preventivi": ("apps/vendite/db/preventivi_repository.py", "_ORDER_COLS_PREVENTIVI"),
    "vendite.offerte": ("apps/vendite/db/offerte_repository.py", "_ORDER_COLS_OFFERTE"),
    "vendite.preventivo_revisioni": ("apps/vendite/db/preventivi_repository.py",
                                     "PREVENTIVO_REVISIONI_ORDER_COLUMNS"),
    "vendite.offerta_revisioni": ("apps/vendite/db/offerte_repository.py",
                                  "OFFERTA_REVISIONI_ORDER_COLUMNS"),
    "vendite.ordini": ("apps/vendite/db/ordini_repository.py", "_ORDER_COLS_ORDINI"),
    "vendite.ddt": ("apps/vendite/db/ddt_repository.py", "_ORDER_COLS_DDT"),
    "vendite.resi": ("apps/vendite/db/resi_repository.py", "_ORDER_COLS_RESI"),
    # Le due code NON usano `_ORDER_COLS_RESI`: hanno mappe proprie, con colonne
    # completamente diverse. Averle lette dalla costante sbagliata ci ha fatto
    # contare 18 colonne rotte che erano zero.
    "vendite.resi_da_accreditare": ("apps/vendite/db/resi_repository.py", "_CODA_META",
                                    "vendite.vw_resi_da_accreditare"),
    "vendite.resi_da_riconsegnare": ("apps/vendite/db/resi_repository.py", "_CODA_META",
                                     "vendite.vw_resi_da_riconsegnare"),
    "catalogo.uom_tipi": ("apps/catalogo/db/catalogo_repository.py", "UOM_TIPI_ORDER_COLUMNS"),
    "catalogo.unita_misura": ("apps/catalogo/db/catalogo_repository.py", "UOM_ORDER_COLUMNS"),
    "catalogo.conversioni_uom": ("apps/catalogo/db/catalogo_repository.py",
                                 "UOM_CONVERSIONI_ORDER_COLUMNS"),
    # Quarto lotto (2026-08-01). Mappate PRIMA di generare il seed: il
    # controllo di consegna salta le liste che non trova qui, e una lista
    # saltata in silenzio e' come non aver fatto il controllo. Le tre whitelist
    # esistono gia' — e' il criterio con cui il lotto e' stato scelto.
    "documenti.template_documenti": ("apps/documenti/db/documenti_repository.py",
                                     "TEMPLATES_ORDER_COLUMNS"),
    "documenti.template_asset": ("apps/documenti/db/documenti_repository.py",
                                 "ASSET_ORDER_COLUMNS"),
    # brief-db-liste-datatable-grezze righe 2 e 6 (2026-09-27).
    "documenti.documenti_sorgente": ("apps/documenti/db/documenti_repository.py",
                                     "DOCUMENTI_SORGENTE_ORDER_COLUMNS"),
    "documenti.template_versioni": ("apps/documenti/db/documenti_repository.py",
                                    "TEMPLATE_VERSIONI_ORDER_COLUMNS"),
    "vendite.promo_articoli": ("apps/vendite/db/promo_articoli_repository.py", "_ORDER_COLS"),
    # Quinto lotto (2026-08-01). Stesso criterio del quarto: mappate prima di
    # generare. `ALLOWED_ORDER_COLUMNS` e' un `frozenset({...})` — forma che il
    # lettore ha imparato a leggere proprio per questa lista.
    "catalogo.articoli": ("apps/catalogo/db/catalogo_repository.py", "ARTICOLI_ORDER_COLUMNS"),
    "vendite.listini": ("apps/vendite/db/listini_repository.py", "LISTINI_ORDER_COLUMNS"),
    # Le note di vendita e di catalogo, e le UoM di un articolo (2026-10-31,
    # secondo giro righe 3 e 4): le note su UNA whitelist (le liste gemelle).
    "vendite.note": ("apps/core/db/partitioned_note_repository.py", "NOTE_ORDER_COLUMNS"),
    "catalogo.note": ("apps/core/db/partitioned_note_repository.py", "NOTE_ORDER_COLUMNS"),
    "catalogo.articolo_uom": ("apps/catalogo/db/catalogo_uom_repository.py", "ARTICOLO_UOM_ORDER_COLUMNS"),
    # La ricerca universale dei soggetti (2026-10-31, secondo giro riga 6):
    # l'ordinamento lo fa la funzione DB, questa e' la colonna che accetta.
    "anagrafiche.ricerca_soggetti": ("apps/core/api/search_validators.py", "ALLOWED_ORDER_COLUMNS"),
    # Le impostazioni (2026-10-31, secondo giro riga 2).
    "config.parametri_impostazioni": ("apps/core/db/parameter_repository.py", "IMPOSTAZIONI_ORDER_COLUMNS"),
    # Le edizioni di workflow (2026-10-31, secondo giro riga 1).
    "pratiche.definizioni_workflow": ("apps/pratiche/db/definizioni_repository.py", "DEFINIZIONI_ORDER_COLUMNS"),
    # Il tab «Versioni» del drawer listino (2026-10-31, brief-db-liste-
    # datatable-grezze-secondo-giro riga 5): fino a quel giorno una `DataTable`
    # nella riga espansa della lista listini.
    "vendite.listini_versioni": ("apps/vendite/db/listini_repository.py", "VERSIONI_ORDER_COLUMNS"),
    "anagrafiche.operatori": ("apps/amm_software/db/amm_software_repository.py",
                              "ALLOWED_ORDER_COLUMNS"),
    # L'area «Accessi» (2026-10-02, brief-db-be-fe-area-accessi R-BE-d): gli
    # altri due tab accanto agli operatori, whitelist di modulo.
    "anagrafiche.accessi_altri": ("apps/amm_software/db/accessi_repository.py",
                                  "ACCESSI_ALTRI_ORDER_COLUMNS"),
    "anagrafiche.accessi_sistema": ("apps/amm_software/db/accessi_repository.py",
                                    "ACCESSI_SISTEMA_ORDER_COLUMNS"),
    # Sesto lotto (2026-08-01). Le tre email nascono dalla passata unica del BE
    # su `email_repository` (whitelist + query param + envelope paginato: la
    # forma di ApiConversioniUomList), chiesta PRIMA di scegliere il lotto
    # invece che in consegna.
    "config.email_account": ("apps/core/db/email_repository.py",
                             "EMAIL_ACCOUNT_ORDER_COLUMNS"),
    "config.email_template": ("apps/core/db/email_repository.py",
                              "EMAIL_TEMPLATE_ORDER_COLUMNS"),
    "config.email_log": ("apps/core/db/email_repository.py", "EMAIL_LOG_ORDER_COLUMNS"),
    # ⚠️ Aggiornato il 2026-08-02: era `_AUDIT_ORDER_COLUMNS` DENTRO la classe,
    # con l'ancora `class AmmSoftwareRepository` per non confonderla con
    # `ALLOWED_ORDER_COLUMNS` (operatori) che vive nello stesso modulo. Il BE
    # l'ha promossa a costante di modulo `AUDIT_ORDER_COLUMNS` convertendo
    # AuditLogView — forma giusta, coerente con le altre otto whitelist, e ora
    # l'ancora di classe non serve piu': i due nomi non collidono.
    # Il presidio ha segnalato «whitelist illeggibile» e si e' rifiutato di
    # dichiarare il seed a posto, che e' il comportamento voluto: meglio dire
    # «non lo so» che dare per verificata una lista che non si e' guardata.
    # ⚠️ Lista POLIMORFA: non legge una tabella, legge `storico.{code}` scelta a
    # runtime da `script.vw_audit_sources`, e proietta alias sintetizzati
    # (`tabella` <- `code`, `user_modifica` <- `user_insert`). Quindi
    # `vista_sql` resta NULL e i tipi si mettono a mano: non c'e'
    # `information_schema` da interrogare, perche' non c'e' UN oggetto.
    "storico.audit_log": ("apps/amm_software/db/amm_software_repository.py",
                          "AUDIT_ORDER_COLUMNS"),
    "anagrafiche.categorie_clienti_listini": (
        "apps/anagrafiche/db/categorie_clienti_listini_repository.py", "_ORDER_COLS"),
    # Settimo lotto (2026-08-02), dalla passata unica del BE. Tutte e tre le
    # whitelist sono costanti di MODULO: il BE le ha portate fuori dalla classe
    # dopo aver scoperto che un gate derivato dal `ClassVar` si svuotava quando
    # un test mockava il repository — il controllo dipendeva dal mock invece che
    # dal codice. «Una whitelist e' un dato, non un comportamento.»
    "dbops.coda_lavori": ("apps/core/services/coda_lavori/repository.py",
                          "ELENCA_SORT_SQL"),
    "vendite.fatture_stampa_coda": ("apps/vendite/db/pipeline_repository.py",
                                    "CODA_STAMPA_SORT_SQL"),
    # ⚠️ La coda approvazioni non ha una whitelist propria: passa da
    # `cerca_pratiche`, quindi la sua e' quella delle pratiche. E' il motivo per
    # cui la mappa di prontezza l'aveva data per «senza ordinamento» — cercata
    # nel repository che porta il nome della lista, dove non c'e'.
    "vendite.approvazioni_prezzo": ("apps/pratiche/db/pratiche_repository.py",
                                    "PRATICHE_ORDER_COLS"),
    # Righe di versione listino (2026-08-03). La lista e' una UNION di righe
    # standalone e compositi bundle: dopo la UNION l'ORDER BY vede solo i nomi
    # PROIETTATI, per questo la whitelist mappa nome -> se stesso e non ad
    # alias di tabella.
    "vendite.listini_righe": ("apps/vendite/db/listini_repository.py",
                              "RIGHE_ORDER_COLUMNS"),
    # Ottavo lotto (2026-08-03): le 3 dashboard vendite + il drawer commessa.
    #
    # ⚠️ `vendite.commesse_attivita` e' la PRIMA lista la cui whitelist non vive
    # in Python: sta nel `CASE` di `vendite.fn_list_commessa_attivita`, perche'
    # ordine e paginazione stanno nella stessa funzione e ordinare a valle
    # ordinerebbe la pagina gia' estratta. Si registra col percorso della doc
    # AUTO-GEN (che parte da `docs/`), non con un sorgente backend: cosi' il
    # controllo resta senza DB e continua a leggere il repository.
    "vendite.commesse_attivita": (
        "docs/it/dbzero/vendite/funzioni/fn_list_commessa_attivita.md", ""),
    # ══════════════════════════════════════════════════════════════════
    # Le tre liste del drawer lotto di fatturazione (L3, 2026-08-22)
    # ══════════════════════════════════════════════════════════════════
    # ⚠️ Registrate PRIMA che il seed esista: qui una voce in piu' e' inerte
    # (il giro parte dalle liste seedate e cerca la loro whitelist), mentre una
    # voce MANCANTE il giorno del seed fa saltare la lista — e una lista saltata
    # viene dichiarata a posto senza essere stata guardata. Meglio in anticipo.
    "vendite.lotto_fatture": ("apps/vendite/db/vendite_repository.py",
                              "LOTTO_FATTURE_SORT_COLUMNS"),
    # ⭐ Come `vendite.commesse_attivita`: la whitelist NON vive in Python, sta
    # nel `CASE` di `vendite.fn_list_lotto_task_runs` — ordine e paginazione
    # nella stessa funzione, e ordinare a valle ordinerebbe la pagina gia'
    # estratta. Il backend non ne tiene uno specchio di proposito: sarebbe una
    # terza verita' da mantenere allineata a mano.
    "vendite.lotto_task_runs": (
        "docs/it/dbzero/vendite/funzioni/fn_list_lotto_task_runs.md", ""),
    "vendite.lotto_segnalazioni": (
        "docs/it/dbzero/vendite/funzioni/fn_list_lotto_segnalazioni.md", ""),
    # Le 5 dashboard tengono la whitelist come attributo di CLASSE, quindi
    # serve l'ancora: nello stesso modulo ne convivono cinque e senza ancora si
    # leggerebbe la prima che capita.
    # ⚠️ Era l'UNICA lista seedata a restare fuori dal registro (trovata dal
    # presidio stesso il 2026-08-22, mentre si registravano le tre del drawer
    # lotto). Attributo di CLASSE come le dashboard, quindi serve l'ancora.
    "vendite.fondi_fattura_da_decidere": ("apps/vendite/db/vendite_repository.py",
                                          "FONDI_DA_DECIDERE_SORT_COLUMNS",
                                          "class VenditeRepository"),
    "vendite.dash_aperto_documenti": ("apps/vendite/db/vendite_repository.py",
                                      "DASH_APERTO_SORT_COLUMNS", "class VenditeRepository"),
    "vendite.dash_backlog_documenti": ("apps/vendite/db/vendite_repository.py",
                                       "DASH_BACKLOG_SORT_COLUMNS", "class VenditeRepository"),
    "vendite.dash_competenza_errori": ("apps/vendite/db/vendite_repository.py",
                                       "DASH_COMPETENZA_ERRORI_SORT_COLUMNS", "class VenditeRepository"),
    "vendite.dash_competenza_gruppi": ("apps/vendite/db/vendite_repository.py",
                                       "DASH_COMPETENZA_GRUPPI_SORT_COLUMNS", "class VenditeRepository"),
    # ⭐ Le sette liste di `pagamenti` (2026-09-17). Fino a quel giorno NESSUNA
    #    era mappata: `--verifica-ordinamento` le saltava come «NON MAPPATA», cioe'
    #    il controllo su di loro non era mai stato fatto — e questo registro dice
    #    di se' che «una lista saltata in silenzio e' come non aver fatto il
    #    controllo». Trovate registrando `pagamenti.rate` (lista 68, D19-c),
    #    l'unica delle sette nata col presidio acceso. Tutte costanti di MODULO
    #    nello stesso repository.
    "pagamenti.distinte": ("apps/pagamenti/db/pagamenti_repository.py", "DISTINTE_SORT_COLUMNS"),
    "pagamenti.righe": ("apps/pagamenti/db/pagamenti_repository.py", "RIGHE_SORT_COLUMNS"),
    # Le righe di UNA distinta (lista 69, 2026-09-18): nata col presidio acceso.
    "pagamenti.distinta_righe": ("apps/pagamenti/db/pagamenti_repository.py",
                                 "DISTINTA_RIGHE_SORT_COLUMNS"),
    "pagamenti.rate_fuori_capienza": ("apps/pagamenti/db/pagamenti_repository.py",
                                      "RATE_FUORI_CAPIENZA_SORT_COLUMNS"),
    "pagamenti.rate": ("apps/pagamenti/db/pagamenti_repository.py", "RATE_SORT_COLUMNS"),
    "pagamenti.eccedenze": ("apps/pagamenti/db/pagamenti_repository.py", "ECCEDENZE_SORT_COLUMNS"),
    "pagamenti.sistemazioni_fattura": ("apps/pagamenti/db/pagamenti_repository.py",
                                       "SISTEMAZIONI_SORT_COLUMNS"),
    "pagamenti.canali_incasso": ("apps/pagamenti/db/pagamenti_repository.py",
                                 "ENTI_INCASSO_SORT_COLUMNS"),
    "vendite.dash_competenza_commesse": ("apps/vendite/db/vendite_repository.py",
                                         "DASH_COMPETENZA_COMMESSE_SORT_COLUMNS", "class VenditeRepository"),
    # Sessioni attive e reparti (2026-09-27, brief-db-liste-datatable-grezze
    # righe 1 e 5): costanti di MODULO nei due repository.
    "core.sessioni_attive": ("apps/core/db/session_audit_repository.py",
                             "SESSIONI_ATTIVE_ORDER_COLUMNS"),
    "amm.reparti": ("apps/amm_software/db/amm_software_repository.py", "REPARTI_ORDER_COLUMNS"),
    # Flussi di una pratica e utilizzo della matrice utility/ruoli (2026-09-27,
    # brief-db-liste-datatable-grezze righe 3 e 4): costanti di MODULO.
    "pratiche.flussi": ("apps/pratiche/db/pratiche_repository.py", "FLUSSI_ORDER_COLS"),
    "config.utilities_tipi_ruolo_usage": ("apps/config/db/utilities_tipi_ruolo_repository.py",
                                          "USAGE_ORDER_COLS"),
}

# Colonne che devono ordinare SEMPRE, quando la lista ce l'ha (regola di
# dominio, Tid 2026-07-31): la data che individua il contesto ha priorita' su
# tutto, poi il numero/codice del contesto, la ragione sociale, il billing
# account, l'id fiscale, la utility, il totale e lo stato.
# Riconosciute per sottostringa sul `codice` della colonna; basta che UNA delle
# candidate ordini perche' il concetto sia coperto.
NUCLEO_ORDINABILE: dict[str, tuple[str, ...]] = {
    "data": ("data_", "data"),
    "numero/codice": ("numero", "codice"),
    "ragione sociale": ("ragione_sociale", "denominazione", "soggetto", "destinatario"),
    "billing account": ("billing_account", "ba_codice"),
    "id fiscale": ("id_fiscale", "partita_iva"),
    "utility": ("utility",),
    "totale": ("totale",),
    # `is_active`/`is_attivo`: stessa colonna di dominio con nome inglese
    # (amm_software). Senza questi alias il controllo segnalerebbe «nucleo
    # rotto: stato» su una lista che lo stato lo ordina eccome — un falso
    # allarme che, ripetuto, insegna a ignorare il controllo.
    "stato": ("stato", "attivo", "is_active"),
}

# Le eccezioni al nucleo, una per (lista, concetto), ciascuna col suo motivo e
# la decisione che la prende. ⛔ Non e' un modo per far tacere il controllo:
# una voce qui e' una decisione di Tid sul modello, scritta con la data. Il
# controllo la mostra a ogni verifica, e segnala come STANTIA un'eccezione che
# non serve piu' (il concetto ordina, o la lista non ha piu' quella colonna):
# un'eccezione che sopravvive al suo motivo diventa un buco.
NUCLEO_ECCEZIONI: dict[tuple[str, str], str] = {
    # `utility_list` e' un aggregato della pagina (le forniture concatenate del
    # soggetto), e `fn_search_soggetti_universale` la rifiuta in `p_order_by`.
    ("anagrafiche.ricerca_soggetti", "utility"): (
        "D-2 (a) di brief-db-ricerca-universale-tetto-10000 (2026-10-10), confermata "
        "da D-3 di brief-db-liste-datatable-grezze-secondo-giro (Tid, 2026-10-31): "
        "l'ordine di una lista di forniture concatenate dice poco, la fornitura si "
        "filtra nel dettaglio"
    ),
}

CAMPI_DEF = ["id", "codice", "descrizione", "schema_dati", "vista_sql", "attivo",
             "data_insert", "user_insert",
              # P-2b: senza questa voce il generatore riscriverebbe il CSV
              # SENZA la colonna, spegnendo il flag su tutte le liste in silenzio.
              "multi_emittente"]
CAMPI_COL = ["id", "lista_id", "codice", "etichetta", "etichetta_estesa", "campo_sorgente",
             "tipo_colonna", "tipo_dato", "formato", "larghezza_default", "ordine_default",
             "allineamento", "gruppo", "gruppo_ordine", "filtrabile", "ordinabile",
             "esportabile", "ricercabile_full", "sensibile", "attivo", "data_insert",
             "user_insert", "etichetta_i18n_key", "priorita"]
CAMPI_PRESET = ["id", "lista_id", "codice", "descrizione", "ambito", "profilo_accesso_id",
                "emittente_fiscale_id", "is_default", "pagina_dimensione",
                "ordinamento_default", "attivo", "data_insert", "user_insert"]
CAMPI_PC = ["preset_id", "colonna_id", "ordine", "visibile", "fissata"]

# Descrittore dei quattro CSV di seed. `nullo` e' il token che il rispettivo
# loader Liquibase interpreta come NULL, e NON e' lo stesso per tutti:
# 20260507-06 (lista_definizione) e 20260806-15 (lista_colonna, dal 2026-11-12) dichiarano
# `nullValue: "NULL"`, gli altri due `nullValue: ""`.
# Sbagliarlo non e' un dettaglio di forma: una cella vuota su lista_definizione
# diventa `vista_sql = ''` (non NULL), il guard
# ui.trgfn_ui_lista_definizione_a10_valida_vista_sql non salta piu' e l'apply
# fallisce con E_UI_VISTA_SQL_NON_TROVATA.
CSV_SEED = {
    "lista_definizione.csv": {
        "campi": CAMPI_DEF, "nullo": "NULL", "pk": ("id",),
        "tabella": "ui.lista_definizione",
    },
    "lista_colonna.csv": {
        "campi": CAMPI_COL, "nullo": "NULL", "pk": ("id",),
        "tabella": "ui.lista_colonna",
    },
    "lista_preset.csv": {
        "campi": CAMPI_PRESET, "nullo": "", "pk": ("id",),
        "tabella": "ui.lista_preset",
    },
    "lista_preset_colonna.csv": {
        "campi": CAMPI_PC, "nullo": "", "pk": ("preset_id", "colonna_id"),
        "tabella": "ui.lista_preset_colonna",
    },
}
# La cella «nessun valore» delle colonne nullable di lista_colonna: il token del
# suo loader. Una cella vuota arriverebbe come stringa vuota, che i CHECK
# chk_lista_colonna_*_non_vuoto/a rifiutano (90_end/20261112-30).
NULLO_COL = CSV_SEED["lista_colonna.csv"]["nullo"]

# Suffissi fisici che le liste configurate tolgono per ottenere il nome logico
# della colonna (`stato_descrizione` -> `stato`, `valuta_codice` -> `valuta`).
# Ricavati dalle 61 colonne su 204 che hanno `codice != campo_sorgente`.
SUFFISSI_FISICI = ("_descrizione", "_codice", "_numero", "_denominazione", "_completa")

# Token del sorgente .vue che delimitano l'ambito di una tabella.
RE_TOKEN = re.compile(r"<DataTable\b|</DataTable>|<Column\b")
RE_COLONNA = re.compile(r"<Column\b(.*?)(?:/>|>(.*?)</Column>)", re.S)


# Scopo: apre la connessione al DB leggendo backend/.env (stesse variabili del BE).
def connetti():
    if psycopg is None:
        sys.exit("psycopg non disponibile: usa backend/.venv/bin/python "
                 "(serve solo ai comandi che leggono il DB)")
    env = {}
    percorso = ROOT / "backend/.env"
    if percorso.exists():
        for riga in percorso.read_text().splitlines():
            m = re.match(r"\s*(?:export\s+)?([A-Z_]+)=(.*)", riga)
            if m:
                env[m.group(1)] = m.group(2).strip().strip("'\"")
    g = lambda k, d=None: os.environ.get(k) or env.get(k) or d
    return psycopg.connect(
        host=g("DB_HOST", "localhost"), port=g("DB_PORT", "5432"),
        dbname=g("DB_NAME"), user=g("DB_USER"), password=g("DB_PASSWORD"),
    )


# Scopo: colonne della vista che alimenta la lista, in ordine di definizione.
#        Serve a due cose oneste: dare i tipi certi e proporre i campi che il
#        .vue non mostra come candidati per le colonne invisibili.
def colonne_vista(conn, schema: str, vista: str) -> list[tuple[str, str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, vista),
        )
        return [(r[0], r[1]) for r in cur.fetchall()]


# Scopo: tipo_dato inferito dal NOME della colonna, cercandolo fra tutte le
#        tabelle e viste del DB. Serve quando la lista non ha una sorgente
#        dichiarata (il caso normale per il Gruppo A: una `vw_*` dedicata in
#        genere non esiste), perche' l'alternativa era far uscire tutto `string`.
#
#        Regola di sicurezza: si accetta l'inferenza **solo se non ambigua**.
#        Misurato sul DB il 2026-07-30: dopo la mappatura a `ui.tipo_dato`,
#        1567 nomi su 1588 (98.7%) risolvono a un tipo solo — l'ambiguita' dei
#        tipi PG (`descrizione` e' varchar, text e char) sparisce perche' tutti
#        e tre mappano su `string`. I 21 casi residui (`id`, `numero`,
#        `data_evento`, `split_payment`...) restano `string` e vengono segnalati:
#        un tipo sbagliato non da' errore, da' una colonna che non ordina.
#
#        Lo schema della lista ha la precedenza: `codice` dentro `catalogo` vale
#        piu' di `codice` trovato altrove.
def tipi_per_nome(conn, nomi: list[str], schema_pref: str) -> tuple[dict, dict]:
    nomi = sorted({n for n in nomi if n})
    if not nomi:
        return {}, {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, table_schema, data_type
            FROM information_schema.columns
            WHERE column_name = ANY(%s)
              AND table_schema NOT IN ('pg_catalog', 'information_schema')
            """,
            (list(nomi),),
        )
        righe = cur.fetchall()

    per_nome: dict[str, dict[str, set]] = {}
    for nome, schema, tipo_pg in righe:
        td = TIPO_DATO.get(tipo_pg)
        if td is None:
            continue  # tipo esotico (PostGIS, enum applicativi): non inferisce
        per_nome.setdefault(nome, {"pref": set(), "tutti": set()})
        per_nome[nome]["tutti"].add(td)
        if schema == schema_pref:
            per_nome[nome]["pref"].add(td)

    risolti, ambigui = {}, {}
    for nome, dati in per_nome.items():
        candidati = dati["pref"] or dati["tutti"]
        if len(candidati) == 1:
            risolti[nome] = (next(iter(candidati)),
                             "schema della lista" if dati["pref"] else "altro schema")
        else:
            ambigui[nome] = sorted(candidati)
    return risolti, ambigui


# Scopo: colonne oggi disegnate dal .vue, nell'ordine in cui l'operatore le vede.
#        E' cio' che rende il preset di default gia' "quello di prima" invece di
#        un elenco alfabetico da risistemare a mano.
#
#        Tre cose che una semplice ricerca di `<Column>` sbaglierebbe, e che qui
#        sono gestite perche' sbagliarle e' silenzioso:
#        1. un file puo' contenere PIU' DataTable (tabella principale + tabella
#           di espansione, o piu' schede): si legge solo quella scelta con
#           --tabella, le altre finiscono nel conteggio degli scarti. Fondere le
#           colonne di due tabelle produce una lista sbagliata e `codice`
#           duplicati;
#        2. le colonne SENZA `field=` ma con un header sono colonne vere
#           calcolate lato FE (il DB le prevede: `campo_sorgente` NULL, come
#           `sosp_riatt` in clienti). Scartarle perde colonne visibili;
#        3. le colonne senza field e senza header sono l'expander o la
#           selezione: quelle si scartano davvero.
#
#        Ritorna (elenco di descrittori, contatori di cio' che e' stato scartato).
def colonne_vue(percorso: Path, tabella: int = 1) -> tuple[list[dict], dict]:
    info = {"tabelle": 0, "annidate": 0, "altre_tabelle": 0, "mute": 0}
    if not percorso.exists():
        return [], info
    testo = percorso.read_text(encoding="utf-8")
    colonne: list[dict] = []
    profondita = 0
    indice = 0

    for tok in RE_TOKEN.finditer(testo):
        segno = tok.group(0)
        if segno == "</DataTable>":
            profondita = max(0, profondita - 1)
            continue
        if segno.startswith("<DataTable"):
            profondita += 1
            if profondita == 1:
                indice += 1
            continue

        m = RE_COLONNA.match(testo, tok.start())
        if not m:
            continue
        if profondita > 1:
            info["annidate"] += 1      # DataTable dentro DataTable: altra lista
            continue
        if profondita == 0:
            continue                   # <Column> fuori da qualunque tabella
        if indice != tabella:
            info["altre_tabelle"] += 1
            continue

        attr, corpo = m.group(1), m.group(2) or ""
        campo = re.search(r'\bfield="([^"]+)"', attr)
        chiave = re.search(r""":header="t\(['"]([^'"]+)['"]\)""", attr)
        statica = re.search(r'\sheader="([^"]+)"', attr)
        azione = "RowActionsMenu" in corpo
        if not campo and not chiave and not statica and not azione:
            info["mute"] += 1          # expander / selezione: niente da configurare
            continue

        colonne.append({
            "campo": campo.group(1) if campo else None,
            "chiave": chiave.group(1) if chiave else None,
            "etichetta_statica": statica.group(1) if statica else None,
            "formato": next(
                (v for k, v in FORMATO_DA_TEMPLATE.items() if k + "(" in corpo), None
            ),
            "destra": "text-align: right" in attr or "text-align:right" in attr,
            "azione": azione,
        })

    info["tabelle"] = indice
    return colonne, info


# Scopo: rileva se il .vue ha una colonna di azioni di riga (kebab
#        `RowActionsMenu`), gia' classificata da colonne_vue().
def ha_colonna_azioni(colonne: list[dict]) -> bool:
    return any(c["azione"] for c in colonne)


# Scopo: etichetta leggibile a partire dalla chiave i18n, cercata in it.json.
#        Se non si risolve si ripiega sull'header statico o sul codice colonna
#        umanizzato, e la riga viene segnalata: un'etichetta sbagliata a video
#        e' peggio di una da rivedere.
def etichetta_da_i18n(chiave: str | None, ripiego: str, dizionario: dict) -> tuple[str, bool]:
    if chiave:
        nodo = dizionario
        for pezzo in chiave.split("."):
            if isinstance(nodo, dict) and pezzo in nodo:
                nodo = nodo[pezzo]
            else:
                nodo = None
                break
        if isinstance(nodo, str):
            return nodo, True
    return ripiego.replace("_", " ").capitalize(), False


# Scopo: nome logico proposto per una colonna, a partire dal campo fisico.
#        E' una PROPOSTA: viene sempre segnalata nel report, perche' il nome di
#        una colonna e' una scelta di presentazione, non una regola.
def nome_logico(campo: str) -> str:
    for s in SUFFISSI_FISICI:
        if campo.endswith(s) and len(campo) > len(s) + 1:
            return campo[: -len(s)]
    return campo


# Scopo: codice proposto per una colonna calcolata FE (senza `field=`), a
#        partire dalla chiave i18n del suo header: `...col_uom` -> `uom`.
def codice_da_etichetta(chiave: str | None, statica: str | None, pos: int) -> str:
    if chiave:
        ultimo = chiave.split(".")[-1]
        for prefisso in ("col_", "field_", "campo_"):
            if ultimo.startswith(prefisso):
                return ultimo[len(prefisso):]
        return ultimo
    if statica:
        pulito = re.sub(r"[^a-z0-9]+", "_", statica.lower()).strip("_")
        if pulito:
            return pulito
    return f"colonna_{pos}"


# Scopo: converte un valore letto dal DB nella cella CSV equivalente, col token
#        NULL richiesto dal loader di quel file.
def cella(valore, nullo: str) -> str:
    if valore is None:
        return nullo
    if isinstance(valore, bool):
        return "t" if valore else "f"
    if isinstance(valore, (dict, list)):
        return json.dumps(valore, separators=(",", ":"), ensure_ascii=False)
    if isinstance(valore, datetime):
        return valore.strftime("%Y-%m-%d %H:%M:%S")
    return str(valore)


# Scopo: righe gia' presenti in un CSV di seed, indicizzate per chiave primaria.
def righe_csv(nome_csv: str) -> dict[tuple, dict]:
    percorso = SEED_DIR / nome_csv
    if not percorso.exists():
        return {}
    pk = CSV_SEED[nome_csv]["pk"]
    with percorso.open(newline="", encoding="utf-8") as fh:
        return {tuple(r[c] for c in pk): r for r in csv.DictReader(fh)}


# Scopo: prossimo id libero considerando SIA il CSV SIA il DB. Il CSV da solo
#        non basta: una lista configurata dai pannelli di amministrazione vive
#        solo nel DB, e riusarne gli id farebbe collidere due lavori paralleli.
def prossimo_id(conn, nome_csv: str, campo: str = "id") -> int:
    da_csv = max((int(k[0]) for k in righe_csv(nome_csv) if k[0]), default=0)
    with conn.cursor() as cur:
        cur.execute(f"SELECT COALESCE(MAX({campo}), 0) FROM {CSV_SEED[nome_csv]['tabella']}")  # noqa: S608 — tabella dalla costante CSV_SEED, colonna dal default letterale 'id'; script CLI, nessun valore nel testo
        da_db = cur.fetchone()[0] or 0
    return max(da_csv, int(da_db)) + 1


# Scopo: legge dal DB le righe di seed di una lista, gia' in forma di celle CSV.
#        E' la base sia del confronto CSV/DB sia del recupero (--esporta).
def righe_db(conn, id_lista: int) -> dict[str, dict[tuple, dict]]:
    fuori: dict[str, dict[tuple, dict]] = {}
    interrogazioni = {
        "lista_definizione.csv": (
            f"SELECT {', '.join(CAMPI_DEF)} FROM ui.lista_definizione WHERE id = %s",  # noqa: S608 — colonne dalla costante CAMPI_DEF, id_lista come parametro
            CAMPI_DEF),
        "lista_colonna.csv": (
            f"SELECT {', '.join(CAMPI_COL)} FROM ui.lista_colonna WHERE lista_id = %s "  # noqa: S608 — colonne dalla costante CAMPI_COL, id_lista come parametro
            "ORDER BY ordine_default, id", CAMPI_COL),
        "lista_preset.csv": (
            f"SELECT {', '.join(CAMPI_PRESET)} FROM ui.lista_preset WHERE lista_id = %s "  # noqa: S608 — colonne dalla costante CAMPI_PRESET, id_lista come parametro
            "ORDER BY id", CAMPI_PRESET),
        "lista_preset_colonna.csv": (
            f"SELECT {', '.join(f'pc.{c}' for c in CAMPI_PC)} "  # noqa: S608 — colonne dalla costante CAMPI_PC, id_lista come parametro
            "FROM ui.lista_preset_colonna pc JOIN ui.lista_preset p ON p.id = pc.preset_id "
            "WHERE p.lista_id = %s ORDER BY pc.preset_id, pc.ordine", CAMPI_PC),
    }
    for nome_csv, (sql, campi) in interrogazioni.items():
        nullo = CSV_SEED[nome_csv]["nullo"]
        pk = CSV_SEED[nome_csv]["pk"]
        with conn.cursor() as cur:
            cur.execute(sql, (id_lista,))
            righe = [dict(zip(campi, [cella(v, nullo) for v in r], strict=True)) for r in cur.fetchall()]
        fuori[nome_csv] = {tuple(r[c] for c in pk): r for r in righe}
    return fuori


# Scopo: dove sta una lista — nei CSV di seed, nel DB, in entrambi o da nessuna
#        parte. E' il controllo che impedisce di rifare un lavoro gia' fatto.
def stato_lista(conn, codice: str) -> dict:
    da_csv = {r["codice"]: r for r in righe_csv("lista_definizione.csv").values()}
    riga_csv = da_csv.get(codice)
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM ui.lista_definizione WHERE codice = %s", (codice,))
        riga_db = cur.fetchone()
    return {
        "codice": codice,
        "id_csv": int(riga_csv["id"]) if riga_csv else None,
        "id_db": int(riga_db[0]) if riga_db else None,
    }


# Scopo: confronta le righe di seed di una lista fra CSV e DB e ritorna, per
#        ciascun file, le righe mancanti nel CSV e quelle divergenti.
def confronta(conn, id_lista: int) -> dict[str, dict]:
    dal_db = righe_db(conn, id_lista)
    esito = {}
    for nome_csv, righe_del_db in dal_db.items():
        campi = CSV_SEED[nome_csv]["campi"]
        nel_csv = righe_csv(nome_csv)
        mancanti = [r for k, r in righe_del_db.items() if k not in nel_csv]
        divergenti = [
            (nel_csv[k], r) for k, r in righe_del_db.items()
            if k in nel_csv and any(nel_csv[k].get(c, "") != r[c] for c in campi)
        ]
        esito[nome_csv] = {"mancanti": mancanti, "divergenti": divergenti,
                           "totale_db": len(righe_del_db)}
    return esito


# Scopo: serializza righe come CSV senza intestazione, pronte da appendere.
def csv_righe(righe: list[dict], campi: list[str]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=campi, lineterminator="\n")
    for r in righe:
        w.writerow(r)
    return buf.getvalue()


# Scopo: costruisce le quattro liste di righe CSV per una lista configurabile.
#        Ritorna anche l'elenco dei punti che richiedono una decisione umana.
def genera(codice, descrizione, schema, vista, cols_vista, cols_vue, dizionario, utente,
           data_insert, id_lista, id_col_base, id_preset,
           tipi_nome=None, tipi_ambigui=None, info_vue=None):
    avvisi: list[str] = []
    tipi_vista = dict(cols_vista)
    tipi_nome = tipi_nome or {}
    tipi_ambigui = tipi_ambigui or {}
    info_vue = info_vue or {}

    # FONTE = il .vue, non la vista. Verificato sulle 11 liste gia' configurate:
    # `ui.lista_colonna.codice` e' un nome LOGICO curato e `campo_sorgente` la
    # colonna fisica (`stato` -> `stato_descrizione`), e 61 colonne su 204
    # differiscono. In piu' esistono colonne senza sorgente (`azioni`,
    # tipo_colonna='azione'; e le calcolate FE come `sosp_riatt`). Una
    # generazione 1:1 dalla vista produrrebbe per `vendite.ddt` 63 colonne coi
    # nomi sbagliati invece di 24 coi nomi giusti.
    # Senza .vue si genera dalla vista: e' una bozza piu' grezza, ma e' l'unica
    # fonte disponibile per una lista che il frontend non disegna ancora.
    if cols_vue:
        voci = list(cols_vue)
    else:
        voci = [{"campo": n, "chiave": None, "etichetta_statica": None,
                 "formato": None, "destra": False, "azione": False}
                for n, _ in cols_vista]
        avvisi.append(
            "nessun .vue: le colonne vengono dalla vista, TUTTE visibili e nell'ordine "
            "di definizione della vista. Ordine, visibilita' e nomi logici vanno curati")

    if info_vue.get("tabelle", 0) > 1:
        avvisi.append(
            f"il .vue contiene {info_vue['tabelle']} <DataTable>: letta solo la n. "
            f"{info_vue.get('scelta', 1)} ({info_vue.get('altre_tabelle', 0)} colonne "
            "delle altre ignorate). Se la lista giusta e' un'altra, usare --tabella")
    if info_vue.get("annidate"):
        avvisi.append(
            f"{info_vue['annidate']} colonne appartengono a una DataTable annidata "
            "(riga di espansione): sono un'altra lista, non entrano in questa")

    dati = [v for v in voci if not v["azione"]]
    azioni = [v for v in voci if v["azione"]]
    if len(azioni) > 1:
        avvisi.append(f"{len(azioni)} colonne azione nel .vue: ne viene generata una sola")

    # Nome logico: si propone togliendo il suffisso fisico, ma solo se il nome
    # risultante resta unico nella lista. `uom_from_codice` e
    # `uom_from_descrizione` collasserebbero entrambi su `uom_from`, e
    # uq_ui_lista_colonna_lista_codice farebbe fallire l'apply.
    proposte = [nome_logico(v["campo"]) if v["campo"]
                else codice_da_etichetta(v["chiave"], v["etichetta_statica"], i + 1)
                for i, v in enumerate(dati)]
    conteggio: dict[str, int] = {}
    for p in proposte:
        conteggio[p] = conteggio.get(p, 0) + 1

    righe_col, righe_pc = [], []
    id_col = id_col_base - 1
    usati: set[str] = set()

    for pos, (voce, proposto) in enumerate(zip(dati, proposte, strict=True), start=1):
        id_col += 1
        campo = voce["campo"]
        calcolata = campo is None

        if calcolata:
            logico = proposto
        elif conteggio[proposto] > 1 or (proposto != campo and proposto in usati):
            logico = campo          # la proposta collide: si tiene il nome fisico
            avvisi.append(
                f"`{campo}`: il nome logico `{proposto}` collide con un'altra colonna "
                "-> tenuto il nome fisico. Se ne serve uno piu' corto, sceglierlo a mano")
        else:
            logico = proposto
            if logico != campo:
                avvisi.append(f"`{campo}` -> codice logico proposto `{logico}` "
                              "(campo_sorgente conservato): confermare il nome")
        usati.add(logico)

        # tipo_dato: prima la vista (certo), poi il nome cercato nel DB (dedotto
        # e accettato solo se non ambiguo), infine `string` dichiarato tale.
        chiave_tipo = campo or logico
        if campo and campo in tipi_vista:
            tipo_dato = TIPO_DATO.get(tipi_vista[campo])
            if tipo_dato is None:
                tipo_dato = "string"
                avvisi.append(f"tipo PG `{tipi_vista[campo]}` (colonna `{campo}`) "
                              "non mappato -> string, da verificare")
        elif chiave_tipo in tipi_nome:
            tipo_dato = tipi_nome[chiave_tipo][0]
        elif voce["formato"] in TIPO_DA_FORMATO:
            # Ultima risorsa, ma non un'invenzione: se il .vue passa il valore a
            # formatCurrency il dato e' un numero, e lasciarlo `string` vorrebbe
            # dire una colonna che non ordina.
            tipo_dato = TIPO_DA_FORMATO[voce["formato"]]
            avvisi.append(
                f"`{chiave_tipo}` non esiste nel DB -> tipo `{tipo_dato}` dedotto dal "
                f"formatter `{voce['formato']}` usato nel .vue: verificarlo")
        else:
            tipo_dato = "string"
            if chiave_tipo not in tipi_ambigui:
                avvisi.append(
                    f"`{chiave_tipo}` non trovata in nessuna tabella o vista -> `string`: "
                    "campo calcolato dal BE? va tipizzato a mano")

        etichetta, risolta = etichetta_da_i18n(
            voce["chiave"], voce["etichetta_statica"] or logico, dizionario)
        if voce["chiave"] and not risolta:
            avvisi.append(f"etichetta di `{logico}`: chiave i18n `{voce['chiave']}` "
                          "non risolta da it.json, e' un segnaposto")

        allineamento = "right" if (voce["destra"] or tipo_dato == "numeric") else (
            "center" if tipo_dato == "boolean" else "left"
        )
        # La prima colonna e' l'identificatore: e' la convenzione di tutte e 11
        # le liste configurate, e non e' cosmetica —
        # ui.fn_resolve_lista_config ne deriva `fissata` e la forza visibile,
        # cioe' e' la colonna che l'utente non puo' nascondere.
        tipo_colonna = "identificatore" if pos == 1 else "informazione"

        if calcolata:
            avvisi.append(
                f"`{logico}`: colonna calcolata dal FE (nel .vue non ha `field=`) -> "
                "campo_sorgente vuoto, filtrabile/ordinabile/esportabile a `f` come "
                "`sosp_riatt` in clienti. Se invece un campo sorgente esiste, indicarlo")

        righe_col.append({
            "id": id_col, "lista_id": id_lista, "codice": logico, "etichetta": etichetta,
            "etichetta_estesa": "Colonna calcolata FE" if calcolata else NULLO_COL,
            "campo_sorgente": campo or NULLO_COL,
            "tipo_colonna": tipo_colonna, "tipo_dato": tipo_dato,
            "formato": voce["formato"] or NULLO_COL, "larghezza_default": NULLO_COL,
            "ordine_default": pos * 10, "allineamento": allineamento,
            "gruppo": NULLO_COL, "gruppo_ordine": NULLO_COL,
            "filtrabile": "f" if calcolata else "t",
            "ordinabile": "f" if calcolata else "t",
            "esportabile": "f" if calcolata else "t",
            "ricercabile_full": "f", "sensibile": "f", "attivo": "t",
            "data_insert": data_insert, "user_insert": utente,
            "etichetta_i18n_key": voce["chiave"] or NULLO_COL, "priorita": 50,
        })
        righe_pc.append({
            "preset_id": id_preset, "colonna_id": id_col, "ordine": pos * 10,
            "visibile": "t", "fissata": "t" if tipo_colonna == "identificatore" else "f",
        })

    # Colonna azioni: senza campo_sorgente, sempre visibile e in coda, con i
    # valori di convenzione delle 11 liste esistenti (ordine 999, gruppo 99).
    if azioni:
        id_col += 1
        righe_col.append({
            "id": id_col, "lista_id": id_lista, "codice": "azioni", "etichetta": "Azioni",
            "etichetta_estesa": NULLO_COL, "campo_sorgente": NULLO_COL,
            "tipo_colonna": "azione", "tipo_dato": "string", "formato": NULLO_COL,
            "larghezza_default": 70, "ordine_default": 999, "allineamento": "center",
            "gruppo": NULLO_COL, "gruppo_ordine": 99,
            "filtrabile": "f", "ordinabile": "f", "esportabile": "f",
            "ricercabile_full": "f", "sensibile": "f", "attivo": "t",
            "data_insert": data_insert, "user_insert": utente,
            "etichetta_i18n_key": "common.col_azioni", "priorita": 50,
        })
        righe_pc.append({"preset_id": id_preset, "colonna_id": id_col,
                         "ordine": 999, "visibile": "t", "fissata": "f"})

    for nome_ambiguo, candidati in tipi_ambigui.items():
        avvisi.append(
            f"tipo di `{nome_ambiguo}` AMBIGUO nel DB ({', '.join(candidati)}) -> lasciato "
            "`string`: va deciso a mano, altrimenti la colonna non ordina come dovrebbe")

    if not tipi_vista and tipi_nome:
        avvisi.append(
            f"nessuna sorgente dichiarata: {len(tipi_nome)} tipi dedotti dal NOME della "
            "colonna cercandolo nel DB (accettati solo se non ambigui). Restano una "
            "deduzione: verificarli")

    if tipi_vista:
        candidati = sorted(set(tipi_vista) - {v["campo"] for v in voci if v["campo"]})
        if candidati:
            avvisi.append(
                f"la vista espone altri {len(candidati)} campi non usati dal .vue: NON sono "
                "stati aggiunti automaticamente (sarebbero rumore). Vanno scelti a mano "
                "quelli che meritano una colonna configurabile invisibile: "
                + ", ".join(candidati[:12]) + ("..." if len(candidati) > 12 else ""))
        assenti = [v["campo"] for v in voci if v["campo"] and v["campo"] not in tipi_vista]
        for c in assenti:
            avvisi.append(f"campo `{c}` del .vue non esiste nella vista: verificare il nome")

    riga_def = {
        "id": id_lista, "codice": codice, "descrizione": descrizione,
        "schema_dati": schema,
        # Cella vuota = stringa vuota per questo loader (nullValue: "NULL"):
        # deve uscire il token letterale, altrimenti il guard vista_sql blocca.
        "vista_sql": vista or CSV_SEED["lista_definizione.csv"]["nullo"],
        "attivo": "t", "data_insert": data_insert, "user_insert": utente,
    }
    breve = codice.split(".")[-1]
    riga_preset = {
        "id": id_preset, "lista_id": id_lista, "codice": f"{breve}_default",
        "descrizione": f"Vista standard {breve}", "ambito": "sistema",
        "profilo_accesso_id": "", "emittente_fiscale_id": "", "is_default": "t",
        "pagina_dimensione": 25, "ordinamento_default": "", "attivo": "t",
        "data_insert": data_insert, "user_insert": utente,
    }

    avvisi.append("`priorita` (ritiro responsive), `gruppo`/`gruppo_ordine`, "
                  "`larghezza_default`, `sensibile` e `ricercabile_full` escono coi "
                  "default: sono decisioni curate, vanno riviste a mano")
    avvisi.append("`tipo_colonna='identificatore'` e' stato messo sulla prima colonna "
                  "(convenzione delle 11 liste esistenti): e' quella che l'utente non "
                  "potra' nascondere — confermare che sia la scelta giusta")
    return riga_def, righe_col, riga_preset, righe_pc, avvisi


# Scopo: estrae le chiavi di una costante-whitelist dal sorgente di un
#        repository backend. Lettura statica: non importa Django, quindi gira
#        anche dove il backend non e' installato (es. il server DB).
#
#        Due accortezze pagate a caro prezzo:
#        1. i **commenti vanno tolti prima**: dentro ai commenti di quelle
#           costanti compaiono parole come `campo_sorgente`, che finivano per
#           errore fra le chiavi e mascheravano colonne rotte;
#        2. il nome va ancorato a **inizio riga**, altrimenti `_ORDER_COLS`
#           aggancia `_EMITTENTI_ORDER_COLS` che lo contiene.
#
#        Solleva ValueError se non trova la costante: meglio fermarsi che
#        rispondere "nessun problema" perche' non si e' guardato niente.
# Scopo: estrae le chiavi di una whitelist che vive DENTRO una funzione DB,
#        leggendole dalla documentazione auto-generata di quella funzione.
#
#        ⚠️ Perche' esiste questo secondo lettore. Per tutte le liste la
#        whitelist sta in una costante Python. Per `vendite.commesse_attivita`
#        no: ordine e paginazione vivono entrambi dentro
#        `vendite.fn_list_commessa_attivita`, e ordinare a valle ordinerebbe la
#        pagina gia' estratta. La whitelist e' quindi il `CASE` in PL/pgSQL.
#
#        Si legge dalla **doc auto-gen** e non dal DB di proposito: cosi'
#        `--verifica-ordinamento` resta senza connessione — gira in CI e dove
#        psycopg non c'e' — e continua a verificare lo stato del REPOSITORY,
#        non quello di un database particolare che potrebbe essere disallineato.
#
#        Se la doc non c'e' o non ha il CASE si solleva: una lista non
#        verificabile va detta, non saltata in silenzio.
def whitelist_funzione_db(percorso_doc: str) -> set[str]:
    file = ROOT / percorso_doc
    if not file.exists():
        raise ValueError(f"doc auto-gen non trovata: {percorso_doc} "
                         "(va rigenerata dopo l'apply della funzione)")
    testo = file.read_text(encoding="utf-8")
    # `WHEN 'nome' THEN 'espressione'` — il ramo `WHEN ''` e' il default
    # (nessun ordinamento chiesto) e non e' una colonna: la regex non lo prende.
    chiavi = set(re.findall(r"WHEN\s+'([a-z_0-9]+)'\s+THEN", testo))
    if not chiavi:
        raise ValueError(f"nessun `WHEN '<nome>' THEN` in {percorso_doc}: "
                         "la funzione non espone una whitelist leggibile")
    return chiavi


def whitelist_backend(percorso: str, costante: str, dentro: str | None = None) -> set[str]:
    # Le liste il cui ordinamento vive in una funzione DB si registrano col
    # percorso della doc auto-gen (che parte da `docs/`), non con un sorgente
    # Python: si dirotta qui.
    if percorso.startswith("docs/"):
        return whitelist_funzione_db(percorso)
    file = ROOT / "backend" / percorso
    if not file.exists():
        raise ValueError(f"sorgente backend non trovato: {percorso}")
    testo = file.read_text(encoding="utf-8")

    if costante == "_CODA_META":
        # Mappa annidata: <vista>: { "order_cols": { ... } }
        try:
            inizio = testo.index(f'"{dentro}"')
            inizio = testo.index('"order_cols"', inizio)
        except ValueError:
            raise ValueError(f"`{dentro}` senza `order_cols` in {percorso}") from None
    else:
        base = testo.index(dentro) if dentro else 0
        if dentro and dentro not in testo:
            raise ValueError(f"ancora `{dentro}` non trovata in {percorso}")
        # ⭐ `NOME = colonne_identita("a", "b", ...)` (2026-09-27): la whitelist
        #    in cui il nome E' la colonna (BB di `_helpers`), anche su piu'
        #    righe. Fino a quel giorno il lettore cercava solo `{`: la forma non
        #    lo aveva, e `anagrafiche.indirizzi` usciva «whitelist illeggibile»
        #    — con le sei geografiche (riga 9 di brief-db-liste-datatable-
        #    grezze) sarebbero state sette liste mai verificate.
        #    Gli argomenti sono stringhe letterali: sono loro le chiavi.
        m_id = re.compile(rf"^[ \t]*{re.escape(costante)}\s*(?::[^=\n]*)?=\s*"
                          r"colonne_identita\(", re.M).search(testo, base)
        if m_id:
            aperta = m_id.end() - 1
            profondita = 0
            for chiusa in range(aperta, len(testo)):
                profondita += (testo[chiusa] == "(") - (testo[chiusa] == ")")
                if profondita == 0:
                    break
            # ⚠️ Gli argomenti li legge il parser di Python, non una regex: una
            #    regex sulle sole virgolette doppie perdeva le chiavi fra apici
            #    (falso «KO») e prendeva quelle scritte in un commento in coda
            #    (falso verde, il peggiore per uno strumento di consegna).
            chiamata = ast.parse("f" + testo[aperta:chiusa + 1], mode="eval").body
            chiavi = {a.value for a in chiamata.args
                      if isinstance(a, ast.Constant) and isinstance(a.value, str)}
            if not chiavi:
                raise ValueError(f"`{costante} = colonne_identita()` senza colonne in {percorso}")
            return chiavi
        # `NOME = {...}`, `NOME: tipo = {...}`, ma anche `NOME = frozenset({...})`
        # / `set({...})`: la forma con wrapper e' usata dove la whitelist e' un
        # insieme immutabile (amm_software). Senza questo ramo il lettore non
        # trova la costante e la lista viene SALTATA dal controllo di consegna —
        # cioe' dichiarata a posto senza essere stata guardata, che e' il modo
        # peggiore di fallire per uno strumento che esiste per guardare.
        m = re.compile(rf"^[ \t]*{re.escape(costante)}\s*(?::[^=\n]*)?=\s*"
                       rf"(?:frozenset|set)?\s*\(?\s*\{{",
                       re.M).search(testo, base)
        if not m:
            raise ValueError(f"costante `{costante}` non trovata in {percorso}"
                             + (f" dopo `{dentro}`" if dentro else ""))
        inizio = m.start()

    apertura = testo.index("{", inizio)
    profondita = 0
    for fine in range(apertura, len(testo)):
        profondita += (testo[fine] == "{") - (testo[fine] == "}")
        if profondita == 0:
            break
    corpo = "\n".join(r for r in testo[apertura:fine + 1].splitlines()
                      if not r.strip().startswith("#"))
    # Forma dict (`"chiave": "v.colonna"`) oppure set (`"chiave", ...`).
    chiavi = set(re.findall(r'"([a-z_0-9]+)"\s*:', corpo))
    # ⭐ `{**ALTRA, "chiave": ...}` (2026-09-28, righe dei documenti di vendita):
    #    le colonne GEMELLE di tre liste sono dichiarate una volta
    #    (`COLONNE_RIGHE_COMMERCIALI`) e ogni repository aggiunge le sue.
    #    ⛔ Senza questo ramo il lettore vedrebbe solo le chiavi scritte a mano
    #    e darebbe le gemelle per mancanti: un falso «KO» che insegna a
    #    ignorare lo strumento.
    for nome in re.findall(r"\*\*([A-Za-z_][A-Za-z0-9_]*)", corpo):
        chiavi |= _whitelist_importata(percorso, testo, nome)
    return chiavi or set(re.findall(r'"([a-z_0-9]+)"', corpo))


# Scopo: le chiavi di una costante nominata in un `**NOME`: nello stesso file,
#        oppure nel modulo `apps.…` da cui il file la importa.
def _whitelist_importata(percorso: str, testo: str, nome: str) -> set[str]:
    if re.search(rf"^[ \t]*{re.escape(nome)}\s*(?::[^=\n]*)?=", testo, re.M):
        return whitelist_backend(percorso, nome)
    # Le due forme dell'import: fra parentesi (anche su piu' righe) o in linea.
    for m in re.finditer(r"^from (apps(?:\.\w+)+) import (?:\(([^)]*)\)|([^\n(]+))$", testo, re.M):
        elenco = m.group(2) if m.group(2) is not None else m.group(3)
        importati = {n.split("#")[0].strip() for n in elenco.split(",")}
        if nome in importati:
            return whitelist_backend(m.group(1).replace(".", "/") + ".py", nome)
    raise ValueError(f"`**{nome}` in {percorso}: costante non trovata ne' importata")


# Scopo: confronta il seed con la whitelist di ordinamento del backend, lista
#        per lista, e riporta i tre modi in cui possono divergere.
#        Gira PRIMA della consegna al team BE (il loro presidio,
#        apps/core/tests/test_liste_configurabili_seed.py, gira dopo che il
#        seed e' atterrato: sono complementari, non doppioni).
#        Non tocca il DB e non scrive niente.
def verifica_ordinamento(solo: str | None = None) -> int:
    liste = [r for r in righe_csv("lista_definizione.csv").values()
             if r["attivo"] == "t" and (solo is None or r["codice"] == solo)]
    if solo and not liste:
        print(f"[X] lista `{solo}` non presente nel seed", file=sys.stderr)
        return 1
    colonne = list(csv.DictReader((SEED_DIR / "lista_colonna.csv").open(encoding="utf-8")))
    preset = list(csv.DictReader((SEED_DIR / "lista_preset.csv").open(encoding="utf-8")))

    problemi = saltate = 0
    for riga in sorted(liste, key=lambda r: r["codice"]):
        codice = riga["codice"]
        if codice not in WHITELIST_BE:
            saltate += 1
            print(f"  {codice:<40}[X] NON MAPPATA — aggiungerla a WHITELIST_BE "
                  "(non posso dire se e' a posto)")
            continue
        try:
            wl = whitelist_backend(*WHITELIST_BE[codice])
        except ValueError as errore:
            saltate += 1
            print(f"  {codice:<40}[X] whitelist illeggibile: {errore}")
            continue

        attive = [c for c in colonne
                  if c["lista_id"] == riga["id"] and c["attivo"] == "t"
                  and c["tipo_colonna"] != "azione" and c["campo_sorgente"]]
        ordinabili = {c["campo_sorgente"] for c in attive if c["ordinabile"] == "t"}
        a_catalogo = {c["campo_sorgente"] for c in attive}

        # 1. promette e non mantiene: freccia a video, ripiego silenzioso a valle.
        bugiarde = sorted(ordinabili - wl)
        # 2. il backend sa ordinare una colonna che il seed non offre. Solo per
        #    le colonne A CATALOGO: una whitelist puo' legittimamente conoscere
        #    campi che la lista non mostra (stessa regola del test del BE).
        irraggiungibili = sorted((wl & a_catalogo) - ordinabili)
        # 3. regola di dominio: il nucleo ordina sempre.
        rotti_grezzi = [nome for nome, chiavi in NUCLEO_ORDINABILE.items()
                        if (cand := [c for c in attive if any(k in c["codice"] for k in chiavi)])
                        and not any(c["campo_sorgente"] in wl for c in cand)]
        #    Le eccezioni dichiarate escono dal KO; quelle che non servono piu'
        #    ci entrano, come stantie.
        eccezioni = {conc for (lista, conc) in NUCLEO_ECCEZIONI if lista == codice}
        rotte = [nome for nome in rotti_grezzi if nome not in eccezioni]
        eccezioni_stantie = sorted(eccezioni - set(rotti_grezzi))
        for nome in sorted(eccezioni & set(rotti_grezzi)):
            print(f"  {codice:<40}    eccezione al nucleo «{nome}»: "
                  f"{NUCLEO_ECCEZIONI[(codice, nome)]}")

        # 4. l'ordinamento di APERTURA della lista. `ordinamento_default` del
        #    preset deve puntare a una colonna che il backend sa ordinare E che
        #    il seed offre come ordinabile. E' una quarta direzione, non un
        #    doppione delle prime tre: quelle guardano le COLONNE, questa
        #    guarda il primo ORDER BY che la lista manda da sola, prima che
        #    l'utente tocchi niente. Un default rotto non si manifesta come
        #    freccia che non ordina — si manifesta come lista che apre
        #    nell'ordine sbagliato, e nessuno lo collega al seed.
        #    Trovato cosi' il difetto di `anagrafiche.clienti` (2026-08-01):
        #    default scritto col `codice` logico (`ragione_sociale`) invece che
        #    col `campo_sorgente` (`ragione_sociale_completa`), quindi fuori
        #    whitelist E fuori seed. Era li' da maggio.
        default_rotti = []
        for pre in preset:
            grezzo = (pre["ordinamento_default"] or "").strip()
            if pre["lista_id"] != riga["id"] or not grezzo:
                continue
            try:
                col = json.loads(grezzo)[0]["col"]
            except (ValueError, KeyError, IndexError, TypeError):
                default_rotti.append(f"{pre['codice']}: `ordinamento_default` illeggibile")
                continue
            if col not in wl:
                default_rotti.append(f"{pre['codice']}: `{col}` non e' nella whitelist del BE")
            elif col not in ordinabili:
                default_rotti.append(f"{pre['codice']}: `{col}` non e' offerta come ordinabile")

        if (not bugiarde and not irraggiungibili and not rotte and not default_rotti
                and not eccezioni_stantie):
            print(f"  {codice:<40}ok  ({len(attive)} colonne, whitelist {len(wl)})")
            continue
        problemi += 1
        print(f"  {codice:<40}KO")
        if bugiarde:
            print(f"      promettono l'ordinamento ma il BE non ce l'ha: {', '.join(bugiarde)}")
        if irraggiungibili:
            print(f"      il BE sa ordinarle ma il seed non le offre : {', '.join(irraggiungibili)}")
        if rotte:
            print(f"      NUCLEO rotto (deve ordinare sempre)        : {', '.join(rotte)}")
        if eccezioni_stantie:
            print(f"      eccezione al nucleo STANTIA (togliere da NUCLEO_ECCEZIONI): "
                  f"{', '.join(eccezioni_stantie)}")
        if default_rotti:
            print(f"      ordinamento di APERTURA del preset        : {'; '.join(default_rotti)}")

    plurale = lambda n, s, p: f"{n} {s if n == 1 else p}"
    print()
    if saltate:
        print(f"[X] {plurale(saltate, 'lista non verificata', 'liste non verificate')}: "
              "finche' restano, questo comando NON dice che il seed e' a posto")
    if problemi:
        print(f"[X] {plurale(problemi, 'lista', 'liste')} con divergenze seed <-> backend")
    if not problemi and not saltate:
        print(f"[ok] {plurale(len(liste), 'lista allineata', 'liste allineate')} "
              "col backend in tutte e tre le direzioni")
    return 1 if (problemi or saltate) else 0


# Scopo: autoverifica — confronta le colonne di una lista GIA' configurata con
#        quelle esposte dalla sua vista. Serve a sapere se l'introspezione e'
#        credibile PRIMA di usarla su liste nuove.
def verifica(conn, codice: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, schema_dati, vista_sql FROM ui.lista_definizione WHERE codice = %s",
            (codice,),
        )
        riga = cur.fetchone()
        if not riga:
            print(f"[X] lista `{codice}` non registrata")
            return 1
        id_lista, schema, vista = riga
        if not vista:
            print(f"[i] lista `{codice}` non ha vista_sql: non verificabile per introspezione")
            return 0
        cur.execute(
            "SELECT codice FROM ui.lista_colonna WHERE lista_id = %s ORDER BY codice",
            (id_lista,),
        )
        reali = {r[0] for r in cur.fetchall()}

    dalla_vista = {c for c, _ in colonne_vista(conn, schema, vista)}
    solo_db = sorted(reali - dalla_vista)
    solo_vista = sorted(dalla_vista - reali)

    print(f"lista `{codice}`  vista {schema}.{vista}")
    print(f"  colonne configurate nel DB : {len(reali)}")
    print(f"  colonne esposte dalla vista: {len(dalla_vista)}")
    print(f"  in comune                  : {len(reali & dalla_vista)}")
    if solo_db:
        print(f"  [!] configurate ma NON nella vista ({len(solo_db)}): {', '.join(solo_db)}")
    if solo_vista:
        print(f"  [i] nella vista ma non configurate ({len(solo_vista)}): {', '.join(solo_vista)}")
    # Le colonne configurate senza corrispondenza nella vista sono il segnale
    # che conta: vorrebbero dire che l'introspezione non basta come fonte.
    return 1 if solo_db else 0


# Scopo: fotografia di tutte le liste — nei CSV di seed, nel DB o in entrambi.
#        E' la mappa del lavoro di allineamento: dice cosa e' gia' fatto, cosa
#        e' stato fatto in-app da qualcun altro e va recuperato, e cosa manca.
def stato(conn) -> int:
    nel_csv = {r["codice"]: int(r["id"]) for r in righe_csv("lista_definizione.csv").values()}
    with conn.cursor() as cur:
        cur.execute("SELECT id, codice FROM ui.lista_definizione ORDER BY id")
        nel_db = {r[1]: int(r[0]) for r in cur.fetchall()}

    print(f"{'lista':<34} {'id':>4} {'CSV':>5} {'DB':>4}  esito")
    print("-" * 88)
    da_recuperare = []
    for codice in sorted(set(nel_csv) | set(nel_db)):
        id_csv, id_db = nel_csv.get(codice), nel_db.get(codice)
        if id_db is None:
            print(f"{codice:<34} {id_csv:>4} {'si':>5} {'-':>4}  seedata ma non applicata al DB")
            continue
        diff = confronta(conn, id_db)
        n_col = diff["lista_colonna.csv"]["totale_db"]
        mancanti = sum(len(d["mancanti"]) for d in diff.values())
        divergenti = sum(len(d["divergenti"]) for d in diff.values())
        if id_csv is None:
            esito = "SOLO DB — fatta in-app, da recuperare: --esporta"
            da_recuperare.append(codice)
        elif mancanti or divergenti:
            esito = f"DA RIALLINEARE — {mancanti} righe mancanti, {divergenti} divergenti: --esporta"
            da_recuperare.append(codice)
        else:
            esito = "allineata"
        print(f"{codice:<34} {id_db:>4} {('si' if id_csv else '-'):>5} {n_col:>4}  {esito}")

    if da_recuperare:
        print(f"\n[!] {len(da_recuperare)} liste hanno lavoro nel DB non ancora nei CSV:")
        for c in da_recuperare:
            print(f"      scripts/gen_seed_lista.py --esporta {c}")
    else:
        print("\n[ok] CSV e DB allineati: niente da recuperare")
    return 0


# Scopo: recupera in righe CSV il lavoro gia' fatto su una lista — tipicamente
#        configurata dai pannelli di amministrazione, quindi viva solo nel DB e
#        destinata a sparire su un'installazione pulita. Emette solo cio' che
#        manca ai CSV, cosi' rilanciarlo non duplica niente.
def esporta(conn, codice: str) -> int:
    info = stato_lista(conn, codice)
    if info["id_db"] is None:
        print(f"[X] lista `{codice}` non esiste nel DB: niente da recuperare "
              "(per crearla da zero usa --codice)")
        return 1

    diff = confronta(conn, info["id_db"])
    mancanti = sum(len(d["mancanti"]) for d in diff.values())
    divergenti = sum(len(d["divergenti"]) for d in diff.values())
    if not mancanti and not divergenti:
        print(f"[ok] lista `{codice}` (id {info['id_db']}) gia' allineata nei CSV: "
              "niente da fare")
        return 0

    print(f"# lista `{codice}` (id {info['id_db']}) — {mancanti} righe da appendere, "
          f"{divergenti} da sostituire\n")
    for nome_csv, d in diff.items():
        if d["mancanti"]:
            print(f"# ---- da appendere a {nome_csv} ----")
            print(csv_righe(d["mancanti"], CSV_SEED[nome_csv]["campi"]), end="")
            print()
    for nome_csv, d in diff.items():
        if not d["divergenti"]:
            continue
        # Righe gia' nel CSV ma con valori diversi nel DB: vanno SOSTITUITE in
        # place, non appese — due righe con la stessa chiave nello stesso CSV
        # sono ambigue per loadUpdateData.
        print(f"# ---- da SOSTITUIRE in {nome_csv} (stessa chiave, valori diversi) ----")
        for vecchia, nuova in d["divergenti"]:
            campi = CSV_SEED[nome_csv]["campi"]
            cambiati = [c for c in campi if vecchia.get(c, "") != nuova[c]]
            print(f"#  chiave {'/'.join(str(nuova[c]) for c in CSV_SEED[nome_csv]['pk'])}"
                  f" — cambia: {', '.join(cambiati)}")
            print(csv_righe([nuova], campi), end="")
        print()

    print("# ---- da decidere a mano ----")
    print("#  - queste righe sono lo STATO DEL DB, non una bozza: rispecchiano scelte "
          "gia' fatte in-app")
    if divergenti:
        print("#  - le righe divergenti vanno sostituite, non appese: chi ha ragione fra "
              "CSV e DB e' una decisione, non un automatismo")
    return 0


# Scopo: punto d'ingresso CLI.
def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--codice", help="codice stabile della lista, es. vendite.fatture")
    p.add_argument("--descrizione", default=None, help="descrizione leggibile")
    p.add_argument("--vista", "--sorgente", dest="vista", default=None,
                   help="schema.oggetto che alimenta la lista: vista OPPURE tabella "
                        "(information_schema copre entrambe); fornisce i tipi reali")
    p.add_argument("--vue", default=None, help="componente .vue con le <Column> attuali")
    p.add_argument("--tabella", type=int, default=1,
                   help="quale <DataTable> del .vue leggere, se ce n'e' piu' d'una "
                        "(default: la prima)")
    p.add_argument("--utente", default="mctit", help="user_insert nei CSV (default: mctit)")
    p.add_argument("--data", default=None,
                   help="data_insert nei CSV (default: oggi). Le colonne sono NOT NULL: "
                        "un valore vuoto farebbe fallire l'apply")
    p.add_argument("--stato", action="store_true",
                   help="fotografia di tutte le liste: cosa e' gia' seedato, cosa e' "
                        "stato fatto in-app e va recuperato")
    p.add_argument("--esporta", metavar="CODICE",
                   help="recupera in CSV il lavoro gia' fatto su una lista esistente")
    p.add_argument("--verifica", metavar="CODICE",
                   help="autoverifica su una lista gia' configurata")
    p.add_argument("--verifica-ordinamento", metavar="CODICE", nargs="?", const="__tutte__",
                   dest="verifica_ordinamento",
                   help="confronta `ordinabile` nel seed con la whitelist di ordinamento "
                        "del backend (tutte le liste, o solo quella indicata). Non usa il "
                        "DB: gira ovunque ci sia il repo")
    p.add_argument("--forza", action="store_true",
                   help="genera comunque una bozza anche se la lista esiste gia' "
                        "(gli id restano nuovi: serve solo per ripartire da capo)")
    args = p.parse_args()
    if not args.data:
        args.data = f"{date.today().isoformat()} 00:00:00"  # noqa: DTZ011 — strumento fuori da Django e senza DB: la data del seed e' quella di chi lo genera

    # Prima di aprire la connessione: questo controllo legge solo CSV e sorgenti
    # e deve poter girare anche dove il DB non e' raggiungibile (CI, server BE).
    if args.verifica_ordinamento:
        return verifica_ordinamento(
            None if args.verifica_ordinamento == "__tutte__" else args.verifica_ordinamento)

    with connetti() as conn:
        if args.stato:
            return stato(conn)
        if args.esporta:
            return esporta(conn, args.esporta)
        if args.verifica:
            return verifica(conn, args.verifica)

        if not args.codice:
            p.error("serve --codice (oppure --stato, --esporta, --verifica)")
        if not args.vue and not args.vista:
            p.error("serve almeno --vue (fonte preferita) o --vista: senza nessuna delle "
                    "due non ci sono colonne da generare")

        # Idempotenza: una lista gia' fatta non si rifa'. Il lavoro procede a
        # piu' mani e qualcuno puo' averla configurata in-app nel frattempo.
        info = stato_lista(conn, args.codice)
        if (info["id_csv"] or info["id_db"]) and not args.forza:
            print(f"[i] lista `{args.codice}` esiste gia'"
                  + (f" nei CSV (id {info['id_csv']})" if info["id_csv"] else "")
                  + (" e" if info["id_csv"] and info["id_db"] else "")
                  + (f" nel DB (id {info['id_db']})" if info["id_db"] else "")
                  + ": non la rigenero.", file=sys.stderr)
            if info["id_db"]:
                print(f"    per allineare i CSV al lavoro gia' fatto: "
                      f"--esporta {args.codice}", file=sys.stderr)
            else:
                print("    e' seedata ma non ancora applicata a questo DB: "
                      "niente da generare.", file=sys.stderr)
            print("    per ripartire da capo comunque: --forza", file=sys.stderr)
            return 0

        schema, vista = ("", "")
        cols_vista: list[tuple[str, str]] = []
        if args.vista:
            if "." not in args.vista:
                p.error("--vista va nella forma schema.vista")
            schema, vista = args.vista.split(".", 1)
            cols_vista = colonne_vista(conn, schema, vista)
            if not cols_vista:
                print(f"[X] vista {schema}.{vista} inesistente o senza colonne", file=sys.stderr)
                return 1
        else:
            schema = args.codice.split(".")[0]

        cols_vue, info_vue = ([], {})
        if args.vue:
            cols_vue, info_vue = colonne_vue(ROOT / args.vue, args.tabella)
            info_vue["scelta"] = args.tabella
            if not cols_vue:
                print(f"[X] nessuna <Column> letta da {args.vue} "
                      f"(tabella n. {args.tabella} di {info_vue.get('tabelle', 0)})",
                      file=sys.stderr)
                return 1

        dizionario = {}
        if LOCALES.exists():
            dizionario = json.loads(LOCALES.read_text(encoding="utf-8"))

        # I tipi si cercano per nome solo per i campi che la vista non copre:
        # per le colonne calcolate FE si prova col codice proposto.
        noti = dict(cols_vista)
        da_cercare = []
        for i, v in enumerate(cols_vue):
            if v["azione"]:
                continue
            nome = v["campo"] or codice_da_etichetta(
                v["chiave"], v["etichetta_statica"], i + 1)
            if nome not in noti:
                da_cercare.append(nome)
        tipi_nome, tipi_ambigui = tipi_per_nome(conn, da_cercare, schema)

        riga_def, righe_col, riga_preset, righe_pc, avvisi = genera(
            args.codice, args.descrizione or args.codice, schema, vista,
            cols_vista, cols_vue, dizionario, args.utente, args.data,
            id_lista=prossimo_id(conn, "lista_definizione.csv"),
            id_col_base=prossimo_id(conn, "lista_colonna.csv"),
            id_preset=prossimo_id(conn, "lista_preset.csv"),
            tipi_nome=tipi_nome, tipi_ambigui=tipi_ambigui, info_vue=info_vue,
        )

    print(f"# lista `{args.codice}` — {len(righe_col)} colonne "
          f"(id {righe_col[0]['id']}..{righe_col[-1]['id']})\n")
    for nome, righe in (
        ("lista_definizione.csv", [riga_def]),
        ("lista_colonna.csv", righe_col),
        ("lista_preset.csv", [riga_preset]),
        ("lista_preset_colonna.csv", righe_pc),
    ):
        print(f"# ---- da appendere a {nome} ----")
        print(csv_righe(righe, CSV_SEED[nome]["campi"]), end="")
        print()

    print("# ---- da decidere a mano ----")
    for a in dict.fromkeys(avvisi):
        print(f"#  - {a}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
