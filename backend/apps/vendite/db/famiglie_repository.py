# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository delle FAMIGLIE DI DOCUMENTO (`vendite.famiglie_documento`)
#        — la lista del CRUD, il dettaglio, la creazione che passa dalla madre
#        `fn_crea_famiglia_documento`, l'update delle colonne ammesse e il verbo
#        `attivo`. Brief: brief-be-fe-crud-registri-di-numerazione §11.10.
# ------------------------------------------------------------
#
# ⛔ SOTTODOMINIO SUO, come `registri_repository`. La famiglia e' la REGOLA che
#    il registro applica: sono due entita' con due cicli di vita e due elenchi
#    di guard, e tenerle nello stesso file confonderebbe la piu' piccola con la
#    piu' grande.
#
# ⭐ SI LEGGE UNA VISTA, E LA VISTA E' IL CONTRATTO.
#    `vendite.vw_famiglie_documento_lista` porta le colonne di catalogo, i due
#    conteggi dei registri e i due blocchi capability presi dalle `fn_check_*`.
#    ⛔ Il lookup generico NON basta e non e' un suo difetto: `fn_get_lookup_
#    codici` da' id/codice/descrizione/attivo e non puo' portare i default della
#    forma ne' le colonne di natura, che sono proprio cio' che serve al drawer
#    dei registri (§11.10 BE-F1, decisione di Tid 2026-09-01).
#
# ⭐ `SELECT v.*`, E NON UNA PROIEZIONE SCRITTA A MANO. La lista dichiara
#    `vista_sql = vw_famiglie_documento_lista` a catalogo, quindi il trigger
#    `ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente` valida OGNI
#    `campo_sorgente` contro le colonne di questa vista. Elencarle di nuovo qui
#    creerebbe una TERZA copia dello stesso elenco — catalogo, vista, SELECT —
#    e quella terza non la guarderebbe nessun presidio: una colonna dimenticata
#    uscirebbe come cella VUOTA, che e' esattamente il difetto contro cui il
#    catalogo dichiara la vista. Con la stella la SELECT non puo' divergere.
#
# ⛔ NESSUNO SCOPE EMITTENTE, e non e' una dimenticanza: una famiglia di
#    documento e' GLOBALE — non ha una colonna emittente e vale per tutti.
#    Il perimetro qui non e' un filtro di righe, e' un cancello di accesso:
#    il CRUD sta sotto `AdminAPIView` (D6, Tid 2026-09-01).

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.config.sorgenti import CATEGORIA_SORGENTE_DOCUMENTO
from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
    sql_order_clause,
    fetch_paged_with_total,
    row_to_dict,
    rows_to_list,
)
from apps.core.db.sql_write_helpers import execute_dynamic_update

_VISTA = "vendite.vw_famiglie_documento_lista"

# Whitelist colonne ammesse per ORDER BY: chiave = `campo_sorgente` del catalogo
# `vendite.famiglie_documento` (e' quello che <ListaConfigurabile> invia come
# sortField), valore = espressione SQL.
# ⛔ Whitelist e non passaggio diretto: il valore arriva dal client e finisce in
#    un ORDER BY, che non e' parametrizzabile.
# ⚠️ DEVE COINCIDERE con le colonne `ordinabile = t` del catalogo, nei due versi
#    (§11.10 BE-F6): una freccia che il catalogo mostra e la whitelist non
#    riconosce fa ripiegare l'ordinamento sul default IN SILENZIO. A tenerli
#    allineati e' `test_liste_configurabili_seed`, che confronta questo
#    dizionario col seed — non la buona volonta'.
_ORDER_COLS: dict[str, str] = {
    "codice_interno": "v.codice_interno",
    "descrizione": "v.descrizione",
    "tabella_documento": "v.tabella_documento",
    "colonna_numero": "v.colonna_numero",
    "colonna_serie": "v.colonna_serie",
    "colonna_billing_account": "v.colonna_billing_account",
    "gestisce_serie": "v.gestisce_serie",
    "presidia_data_documento": "v.presidia_data_documento",
    "prefisso_default": "v.prefisso_default",
    "lunghezza_default": "v.lunghezza_default",
    "n_registri": "v.n_registri",
    "n_registri_attivi": "v.n_registri_attivi",
    "attivo": "v.attivo",
    "data_insert": "v.data_insert",
}
_ORDER_DEFAULT = "codice_interno"

# Colonne che la ricerca libera SA cercare nella lista `vendite.famiglie_documento`. Quali cerca
# davvero lo decide il catalogo a ogni ricerca (`add_ricerca_full_condition`);
# `test_ricerca_full_seed` verifica che coprano le `ricercabile_full` del seed.
# ⭐ `codice` e non `codice_interno` (Tid, 2026-09-23; changeSet DB
#    `20260924-03…-07`, brief-db-ricerca-full-colonne-da-accendere §3.5): il
#    `codice_interno` e' la chiave immutabile del sistema — quella su cui si
#    agganciano i registri — e non il codice dell'operatore. Il catalogo accende
#    `codice` (riga 938) e spegne `codice_interno` (riga 630).
# ⭐ La proiezione non si tocca: `SELECT v.*` porta gia' `codice`, che la vista
#    espone in coda.
_RICERCA = RicercaFull(
    "vendite.famiglie_documento",
    ("codice", "descrizione", "prefisso_default"),
)

# I parametri della madre, NELL'ORDINE della sua firma.
# ⛔ La creazione non fa un INSERT: passa da `vendite.fn_crea_famiglia_documento`
#    (§11.10 BE-F4), che scrive la famiglia E provvede i registri mancanti nella
#    stessa transazione. Un INSERT diretto farebbe nascere una famiglia che non
#    produce nessun documento finche' qualcuno non se ne accorge.
# ⭐ Dal 2026-10-20 (brief-db-grammatica-unica-documenti 2c, G-5) la famiglia e'
#    quella di una SORGENTE: `codice_interno` e' il `codice_interno` di
#    `config.sorgenti` (FK `fk_famiglie_documento_sorgenti`) e la tabella dei
#    documenti e' la sua `target_table`. `schema_tabella` e `nome_tabella` non
#    sono piu' parametri della madre ne' colonne della famiglia: la vista le
#    calcola ancora, in sola lettura.
_CAMPI_CREATE: tuple[str, ...] = (
    "codice_interno",
    "descrizione",
    "colonna_numero",
    "colonna_billing_account",
    "colonna_serie",
    "prefisso_default",
    "lunghezza_default",
    "attivo",
    "meta",
)

# Colonne scrivibili in UPDATE.
#
# ⛔ FUORI: `codice_interno` (lo presidia il lock automatico `trgfn_lock_columns`
#    — D3), `attivo` (ha il suo verbo) e `presidia_data_documento`.
#
# ⭐ QUEST'ULTIMA E' LA VOCE CHE VA CAPITA: una famiglia creata dal CRUD nasce
#    NON FISCALE, e non per prudenza. Il `CHECK chk_registri_fatturazione_
#    famiglia_regole_fattura` cabla `'FATTURA'` e un `CHECK` non puo' leggere
#    un'altra tabella; accanto, `fn_get_pavimento_data_documento` e
#    `fn_get_registro_documento` cablano la stessa stringa. Accendere il
#    presidio su una famiglia nuova le prometterebbe un comportamento fiscale
#    che il resto del modello non le da'. ✅ D5 (Tid, 2026-09-01): il `CHECK`
#    non si tocca, e il limite si dichiara nella maschera (§11.11).
#
# ⭐ LE TRE COLONNE STRUTTURALI CI SONO INVECE, ed e' la stessa logica dei
#    tre campi di forma dei registri: esiste il guard che le rifiuta quando la
#    famiglia ha gia' dei registri (`trgfn_famiglie_documento_guard_struttura`,
#    E_FAMIGLIA_DOCUMENTO_CHIAVE_IMMUTABILE). Tenerle fuori sarebbe un divieto
#    APPLICATIVO accanto a uno di DATABASE — il secondo elenco parallelo che
#    tutto il cantiere esiste per non avere.
# ⛔ E `meta` NON e' in UPDATE: e' una colonna tecnica NOT NULL che nessuna
#    maschera scrive e nessun serializer dichiara. Tenerla scrivibile sarebbe
#    superficie morta con un difetto dentro — un `meta: ""` normalizzato a NULL
#    verrebbe respinto dal NOT NULL con un messaggio generico, su un campo che
#    l'operatore non ha mai visto. In CREATE resta, perche' e' un parametro
#    della madre e ha il suo default.
# ⭐ `codice` c'e' dal 2026-09-24 (Tid): e' il codice dell'OPERATORE — mutabile,
#    `UNIQUE`, `NOT NULL` — accanto al `codice_interno` immutabile su cui si
#    agganciano i registri (changeSet `20260924-03…-07`). ⚠️ In CREATE non c'e':
#    la madre non ha il parametro, e alla nascita il trigger
#    `trg_famiglie_documento_a10_default_codice_ins` lo copia dal `codice_interno`.
_CAMPI_UPDATE: tuple[str, ...] = (
    "codice",
    "descrizione",
    "colonna_numero",
    "colonna_billing_account",
    "colonna_serie",
    "prefisso_default",
    "lunghezza_default",
)


class FamiglieDocumentoRepository:
    """Accesso DB al catalogo delle famiglie di documento."""

    # =================================================================
    # Lettura
    # =================================================================

    # Scopo: lista paginata delle famiglie, con i conteggi dei registri e i due
    #        blocchi capability che la maschera usa per spegnere i pulsanti.
    def list_famiglie(
        self,
        *,
        search: str | None = None,
        attivo: bool | None = None,
        gestisce_serie: bool | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str = _ORDER_DEFAULT,
        order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS,
            default=_ORDER_COLS[_ORDER_DEFAULT],
            tiebreak="v.id",
        )
        conditions = [
            "(%s::boolean IS NULL OR v.attivo = %s)",
            "(%s::boolean IS NULL OR v.gestisce_serie = %s)",
        ]
        params: list[Any] = [attivo, attivo, gestisce_serie, gestisce_serie]
        # ⭐ Una lista di configurazione, dove prefissi e codici di uno o due
        #    caratteri sono normali e vanno trovati: la soglia la dichiara il
        #    catalogo della lista (`ricerca_min_caratteri`), non questo modulo.
        add_ricerca_full_condition(conditions, params, search, _RICERCA)
        sql = f"""
            SELECT v.*,
                   COUNT(*) OVER () AS total_count
              FROM {_VISTA} v
             WHERE {" AND ".join(conditions)}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params.extend([limit, offset])
        righe, totale = fetch_paged_with_total(sql, params, offset=offset)
        return righe, totale

    # Scopo: il dettaglio di una famiglia. `None` se non esiste.
    def get_famiglia(self, famiglia_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT v.* FROM {_VISTA} v WHERE v.id = %s", [famiglia_id])  # noqa: S608
            riga = row_to_dict(cursor)
        if riga is None:
            return None
        return riga

    # Scopo: la famiglia per codice interno — serve a chi ha in mano il codice e
    #        non l'id (i registri si agganciano per `codice_interno`).
    def get_famiglia_per_codice(self, codice_interno: str) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT v.* FROM {_VISTA} v WHERE v.codice_interno = %s",  # noqa: S608
                [codice_interno],
            )
            riga = row_to_dict(cursor)
        if riga is None:
            return None
        return riga

    # Scopo: «questa famiglia ammette le regole fiscali?» — cioe' i limiti di
    #        emissione e una politica data non neutra sul suo registro.
    #
    # ⛔ NON e' `presidia_data_documento`, che oggi ha la stessa risposta su
    #    tutte e cinque. Quella dice se la famiglia ha un PAVIMENTO sulla data
    #    del documento (il cancello di monotonia di `fn_get_next_progressivo`);
    #    questa dice cosa ammette il `CHECK` dei registri. Due domande diverse
    #    con la stessa risposta di oggi restano due domande — e la prima
    #    famiglia creata dal CRUD le separa, perche' nasce presidiata e NON
    #    fiscale (§12.2, colonna aggiunta dal team DB il 2026-09-02).
    #
    # ⭐ E la colonna non e' libera: un `CHECK` la lega allo stesso letterale del
    #    `CHECK` sui registri, quindi il posto in cui si decide cosa e' fiscale
    #    resta UNO e la colonna lo dichiara invece di duplicarlo.
    #
    # ⛔ Legge la TABELLA e non la vista: serve un booleano, e passare dalla
    #    vista farebbe girare due `fn_check_*` in LATERAL per leggerlo.
    # ⚠️ `None` quando la famiglia non esiste, e NON `False`: sono due risposte
    #    diverse — «non ammette» e «non c'e'» — e a rifiutare la seconda deve
    #    essere la FK, con il suo messaggio, non un default silenzioso qui.
    def ammette_regole_fiscali(self, codice_interno: str) -> bool | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT ammette_regole_fiscali
                  FROM vendite.famiglie_documento
                 WHERE codice_interno = %s
                """,
                [codice_interno],
            )
            riga = cursor.fetchone()
        return None if riga is None else bool(riga[0])

    # Scopo: le famiglie da offrire in un Select — le sole ATTIVE, con i default
    #        della forma e le due colonne di natura che il drawer dei registri
    #        usa per precompilare e per decidere quali campi mostrare.
    # ⛔ `ammette_regole_fiscali` e non `presidia_data_documento`: e' la prima a
    #    rispondere alla domanda «questo registro puo' avere i limiti di
    #    emissione?». La seconda risponde al pavimento di sequenza, e la
    #    maschera dei registri non la usa.
    # ⛔ Non e' un doppione della lista: quella e' paginata, ordinabile e piena
    #    di capability; questo e' l'elenco che riempie una tendina.
    def list_lookup(self) -> list[dict[str, Any]]:
        sql = f"""
            SELECT v.codice_interno,
                   v.descrizione,
                   v.prefisso_default,
                   v.lunghezza_default,
                   v.gestisce_serie,
                   v.ammette_regole_fiscali
              FROM {_VISTA} v
             WHERE v.attivo
             ORDER BY v.descrizione
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return rows_to_list(cursor)

    # Scopo: le sorgenti fra cui il drawer sceglie la famiglia da creare —
    #        i tipi di documento di `config.sorgenti` che dichiarano una
    #        tabella, con la tabella e chi la numera gia'.
    # ⭐ La famiglia E' una sorgente (G-5, 2026-10-20): la creazione riceve il
    #    `codice_interno` della sorgente, e la tabella la dice `target_table`
    #    (`config.fn_sorgente_tabella`, il BB del DB, mai `target_table::text`).
    # ⛔ `famiglia_esistente` e `tabella_numerata_da` sono INFORMAZIONI per
    #    spegnere la voce e dire perche', non il rifiuto: a rifiutare restano
    #    l'indice unico su `codice_interno` e il guard dei riferimenti
    #    (`E_FAMIGLIA_DOCUMENTO_TABELLA_GIA_NUMERATA`). Una sorgente puo' avere
    #    una famiglia SPENTA: allora non se ne crea un'altra, si riaccende.
    # ⚠️ `tabella_numerata_da` e' la famiglia ATTIVA di un'ALTRA sorgente sulla
    #    stessa tabella: la propria famiglia non conta (e' `famiglia_esistente`),
    #    altrimenti una famiglia spenta da riaccendere e una tabella gia' presa
    #    da un'altra non si distinguerebbero — e la seconda la riaccensione la
    #    rifiuta.
    # ⚠️ `codice_interno` e non `codice`: il nome del tipo e' quello immutabile.
    def list_sorgenti_numerabili(self) -> list[dict[str, Any]]:
        sql = """
            SELECT s.codice_interno,
                   s.etichetta,
                   s.descrizione,
                   (t.schema_tabella::text || '.' || t.nome_tabella::text)
                                                  AS tabella_documento,
                   (f.id IS NOT NULL)             AS famiglia_esistente,
                   occ.descrizione                AS tabella_numerata_da
              FROM config.sorgenti s
              JOIN LATERAL config.fn_sorgente_tabella(s.codice_interno) t ON TRUE
              LEFT JOIN vendite.famiglie_documento f
                     ON f.codice_interno = s.codice_interno
              LEFT JOIN LATERAL (
                    SELECT fo.descrizione
                      FROM vendite.famiglie_documento fo
                      JOIN LATERAL config.fn_sorgente_tabella(fo.codice_interno) tf
                           ON TRUE
                     WHERE fo.attivo
                       AND fo.codice_interno <> s.codice_interno
                       AND tf.relid = t.relid
                     ORDER BY fo.id
                     LIMIT 1
              ) occ ON TRUE
             WHERE s.attivo
               AND s.categoria = %s
             ORDER BY s.etichetta, s.codice_interno
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [CATEGORIA_SORGENTE_DOCUMENTO])
            return rows_to_list(cursor)

    # =================================================================
    # Scrittura
    # =================================================================

    # Scopo: crea la famiglia PASSANDO DALLA MADRE, e ritorna cio' che la madre
    #        dichiara: l'id, il codice e quanti registri ha provveduto.
    # ⭐ `registri_creati` non e' un dettaglio da buttare: e' la meta' del lavoro
    #    che la creazione ha fatto, e la maschera deve poterlo dire.
    def crea_famiglia(self, dati: dict[str, Any]) -> dict[str, Any]:
        # ⛔ ARGOMENTI PER NOME, NON PER POSIZIONE, ed è la differenza fra un
        #    errore rumoroso e un difetto muto. Con undici `%s` posizionali la
        #    corrispondenza sta in `_CAMPI_CREATE`: il giorno che la madre
        #    cambia l'ordine dei parametri — o ne aggiunge uno in mezzo —
        #    `colonna_serie` riceverebbe il valore di `colonna_billing_account`
        #    e la famiglia nascerebbe SBAGLIATA senza che niente fallisca (sono
        #    tutti `text`). Con la notazione nominale un parametro rinominato è
        #    un errore SQL, e uno spostato non è niente.
        argomenti = ", ".join(f"p_{c} => %s" for c in _CAMPI_CREATE)
        sql = f"""
            SELECT famiglia_id, codice_interno, registri_creati
              FROM vendite.fn_crea_famiglia_documento({argomenti})
        """  # noqa: S608
        params = [dati.get(c) for c in _CAMPI_CREATE]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            riga = row_to_dict(cursor)
        assert riga is not None, "fn_crea_famiglia_documento non ha ritornato righe"
        return riga

    # Scopo: aggiorna le colonne ammesse. Ritorna le righe toccate, cosi' il
    #        service distingue «non esiste» da «fatto».
    # ⭐ BB core `execute_dynamic_update` (2026-09-26). Whitelist RIGIDA: una
    #    chiave fuori `_CAMPI_UPDATE` e' `RuntimeError`, non piu' uno scarto
    #    silenzioso — il 400 lo da' il service (`_verifica_chiavi`).
    # ⛔ `prefisso_default` NON si strippa (`letterali`): e' il prefisso che i
    #    registri della famiglia ereditano, cioe' un pezzo del numero stampato,
    #    e uno spazio ai bordi li' e' contenuto. Le altre stringhe si strippano.
    # ⚠️ Il BB ritorna un bool (`rowcount > 0`): per id l'UPDATE tocca al piu'
    #    una riga, quindi 1/0 e' la stessa informazione di prima.
    def update_famiglia(self, famiglia_id: int, dati: dict[str, Any]) -> int:
        toccata = execute_dynamic_update(
            "vendite.famiglie_documento",
            famiglia_id,
            dati,
            allowed=_CAMPI_UPDATE,
            letterali=("prefisso_default",),
        )
        return int(toccata)

    # Scopo: accende o spegne la famiglia — un verbo suo, non un PATCH generico.
    # ⛔ Qui non si ricontrolla se e' spegnibile: a rifiutare e'
    #    `trgfn_famiglie_documento_guard_disattivazione`, e la
    #    `fn_check_famiglia_documento_disattivabile` che la vista legge serve a
    #    SPEGNERE IL PULSANTE, non a decidere al posto del database.
    # ⚠️ `IS DISTINCT FROM` rende il verbo idempotente: ri-spegnere una famiglia
    #    gia' spenta tocca zero righe e non sveglia il guard.
    def set_attivo(self, famiglia_id: int, attivo: bool) -> int:
        sql = """
            UPDATE vendite.famiglie_documento
               SET attivo = %s
             WHERE id = %s
               AND attivo IS DISTINCT FROM %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [attivo, famiglia_id, attivo])
            return cursor.rowcount
