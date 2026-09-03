# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository dello schema `pagamenti` — letture di lista e dettaglio,
#        scritture semplici, e chiamate alle funzioni madri del database.
# Note: ⛔ Un repository PER SCHEMA e non uno per entita': distinte e righe
#       stanno insieme finche' non nasce un sottodominio con orchestrazione
#       propria (convenzione di naming, AGENTS.md).
#
#       🔴 TUTTE le tabelle di `pagamenti` hanno la row security accesa (lotto
#       DB 6) e le policy pretendono `app.ruolo_applicativo = 'OPERATORE'` per
#       LEGGERE e per SCRIVERE. Un percorso che le tocchi senza quella GUC non
#       vede niente e non scrive niente: la impostano il middleware JWT (ciclo
#       web) e il contesto della coda lavori (worker).
#
#       ⛔ E per la stessa ragione questi metodi NON vanno chiamati da un canale
#       di sistema (ruolo BYPASSRLS): li' il perimetro non filtra e le liste
#       mostrerebbero il denaro di tutti gli emittenti. Il guard e' esplicito
#       nelle letture di lista, non affidato al ricordo.
# ------------------------------------------------------------

from datetime import date
from decimal import Decimal
from typing import Any

from django.db import connection

from apps.core.db._helpers import (
    fetch_paged_with_total,
    sql_order_clause,
    jsonb_out,
    rows_to_list,
    sql_order_direction,
    sql_tiebreak_direction,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.system_context import connection_role_bypasses_rls
from apps.pagamenti.types import (
    DistintaRow,
    RicevutaPosting,
    RigaCodaRow,
    RigaContabileRow,
    StatoCatalogoRow,
    StatoRigaCatalogoRow,
)

_FN = "pagamenti.pagamenti_repository"

# Codice usato dai soli guard strutturali di questo modulo (canale di sistema):
# non e' un errore che un operatore possa causare compilando qualcosa.
_E_CHIAMATA = "E_PAGAMENTI_CHIAMATA_NON_VALIDA"

# ✅ Il «fuori perimetro», gia' a catalogo (classe `NON_PERMESSO` -> **403**) e
# gia' col suo ripiego: non se ne inventa uno nuovo, che cadrebbe su
# `E_GENERICO` e quindi su un **500**.
_E_SCOPE_EMITTENTE = "E_SCOPE_EMITTENTE"


# ══════════════════════════════════════════════════════════════════
#  Frammenti SQL condivisi
# ══════════════════════════════════════════════════════════════════

# I totali derivati della distinta. ⚠️ Contano le righe ATTIVE, SCARTATA
# compresa: e' la stessa somma che il guard di validazione confronta con
# `importo_dichiarato` — se una riga scartata uscisse dal conto, il primo
# scarto romperebbe la quadratura di una distinta sana.
_TOTALI_LATERAL = """
    LEFT JOIN LATERAL (
        SELECT
            count(*)::int                                          AS righe_totali,
            count(*) FILTER (WHERE rs.is_postabile)::int           AS righe_registrabili,
            COALESCE(sum(r.importo), 0)                            AS totale_righe,
            COALESCE(sum(r.importo) FILTER (WHERE rs.is_postabile), 0) AS totale_registrabile
          FROM pagamenti.vendite_contabili_righe r
          JOIN pagamenti.vendite_contabili_righe_stati rs ON rs.id = r.stato_id
         WHERE r.contabile_id = c.id
           AND r.attivo IS TRUE
    ) tot ON TRUE
"""

_DISTINTA_SELECT = """
    SELECT
        c.id,
        c.codice,
        c.centro_riscossione_id,
        cr.codice          AS centro_codice,
        cr.descrizione     AS centro_descrizione,
        c.ente_incasso_id,
        ei.codice          AS ente_codice,
        ei.descrizione     AS ente_descrizione,
        c.data_contabile,
        c.data_registrazione,
        c.stato_id,
        st.codice_interno  AS stato_codice,
        st.descrizione     AS stato_descrizione,
        st.is_final        AS stato_is_final,
        c.origine,
        c.importo_dichiarato,
        c.data_conferma,
        c.user_conferma,
        -- ⭐ IL LEGAME DELLA CORREZIONE, letto nei DUE versi (Q-7, C-3): una
        --    distinta puo' essere la correzione di un'altra, oppure essere
        --    quella che e' stata corretta. ⛔ Sono due domande diverse e a
        --    video dicono due cose opposte: «questo documento rovescia quello»
        --    e «questo documento e' gia' stato rovesciato». Portarne una sola
        --    lascerebbe l'altra meta' invisibile.
        c.contabile_corretta_id,
        orig.codice        AS contabile_corretta_codice,
        corr.id            AS correzione_id,
        corr.codice        AS correzione_codice,
        lot.lotti_ids,
        c.meta,
        tot.righe_totali,
        tot.righe_registrabili,
        tot.totale_righe,
        tot.totale_registrabile,
        -- Lo scarto esiste solo se qualcuno ha dichiarato un totale: NULL non
        -- e' zero, e mostrare «scarto 0» dove nessuno ha dichiarato niente
        -- direbbe che la distinta quadra quando non c'e' niente da quadrare.
        CASE WHEN c.importo_dichiarato IS NULL THEN NULL
             ELSE tot.totale_righe - c.importo_dichiarato
        END AS scarto_dichiarato
      FROM pagamenti.vendite_contabili c
      JOIN pagamenti.centri_riscossione cr        ON cr.id = c.centro_riscossione_id
      LEFT JOIN pagamenti.enti_incasso ei         ON ei.id = c.ente_incasso_id
      LEFT JOIN pagamenti.vendite_contabili_stati st ON st.id = c.stato_id
      -- Il documento da cui questa correzione nasce.
      LEFT JOIN pagamenti.vendite_contabili orig     ON orig.id = c.contabile_corretta_id
      -- ⚠️ E la correzione di QUESTO documento, se c'e'. E' un LEFT JOIN
      --    diretto e non una LATERAL perche' non puo' duplicare la riga:
      --    `uq_vendite_contabili_correzione` e' un unico parziale su
      --    `contabile_corretta_id`, quindi la corrispondenza e' al piu' una.
      LEFT JOIN pagamenti.vendite_contabili corr     ON corr.contabile_corretta_id = c.id
      -- 🔴 I lotti si AGGREGANO, non si joinano. L'unico e' su
      -- `(lotto_id, contabile_id)` e NON sul solo `contabile_id`: una distinta
      -- puo' legittimamente appartenere a piu' lotti, e un LEFT JOIN diretto
      -- avrebbe DUPLICATO la riga nell'elenco — con il conteggio totale
      -- sbagliato di conseguenza, che e' il modo silenzioso di rompersi.
      LEFT JOIN LATERAL (
          SELECT array_agg(l.lotto_id ORDER BY l.lotto_id) AS lotti_ids
            FROM pagamenti.vendite_contabili_lotti l
           WHERE l.contabile_id = c.id
      ) lot ON TRUE
"""

_RIGA_COLONNE = """
        r.id,
        r.contabile_id,
        r.importo,
        r.riferimento_ente,
        r.data_pagamento,
        r.data_valuta,
        r.data_operazione,
        r.fattura_id,
        f.numero           AS fattura_numero,
        f.anno             AS fattura_anno,
        f.serie            AS fattura_serie,
        r.billing_account_id,
        ba.codice          AS billing_account_codice,
        srd.ragione_sociale_completa AS billing_account_descrizione,
        r.scadenza_id,
        sc.numero_rata     AS scadenza_numero_rata,
        sc.data_scadenza   AS scadenza_data,
        r.forzata,
        r.motivo_forzatura,
        r.stato_id,
        rs.codice_interno  AS stato_codice,
        rs.descrizione     AS stato_descrizione,
        rs.is_postabile    AS stato_is_postabile,
        rs.richiede_abbinamento AS stato_richiede_abbinamento,
        r.motivo_sospeso,
        r.fondo_source_id,
        r.attivo,
        r.meta
"""

_RIGA_FROM = """
      FROM pagamenti.vendite_contabili_righe r
      LEFT JOIN pagamenti.vendite_contabili_righe_stati rs ON rs.id = r.stato_id
      LEFT JOIN vendite.fatture f            ON f.id = r.fattura_id
      LEFT JOIN anagrafiche.billing_account ba ON ba.id = r.billing_account_id
      -- Il nome del cliente non sta sul billing account: la vista di dettaglio
      -- e' la sede unica della ragione sociale (persone fisiche e giuridiche
      -- si compongono in modo diverso, e ricomporla qui sarebbe una copia).
      LEFT JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srd
             ON srd.soggetto_ruolo_id = ba.soggetto_ruolo_id
      LEFT JOIN vendite.fatture_scadenze sc  ON sc.id = r.scadenza_id
"""

# La riga «nuda», per il dettaglio e per le righe di UNA distinta.
_RIGA_SELECT = f"SELECT {_RIGA_COLONNE} {_RIGA_FROM}"

# 🔴 La riga della CODA porta anche la sua distinta, e non e' un di piu': una
# riga cross-distinta senza il documento da cui viene non si lavora — chi la
# guarda deve poterci tornare. ⚠️ Ed e' anche la colonna su cui il contratto
# dichiara di saper ordinare: senza, `order_by=distinta` sarebbe un 500.
_RIGA_CODA_SELECT = f"""
    SELECT {_RIGA_COLONNE},
        c.codice          AS contabile_codice,
        c.data_contabile  AS contabile_data,
        c.origine         AS contabile_origine
    {_RIGA_FROM}
      JOIN pagamenti.vendite_contabili c ON c.id = r.contabile_id
"""

# 🔴 LE CHIAVI SONO IL `campo_sorgente` DEL SEED, NON IL `codice` LOGICO — e la
# differenza non e' di stile. `<ListaConfigurabile>` monta le Column con
# `:field="col.campo_sorgente"`, quindi al click sull'intestazione PrimeVue
# manda **il nome fisico**: una whitelist chiavata sul codice logico risponde
# **400 su una colonna che il catalogo dichiara ordinabile**. E' il difetto gia'
# pagato su `vendite.lotti` il 2026-07-31, presidiato da
# `apps/core/tests/test_liste_configurabili_seed.py`
# (`test_whitelist_chiavata_sul_campo_sorgente`).
# ⚠️ Dove il codice logico e il campo fisico divergono, anche il VALORE segue il
# campo mostrato (`stato_descrizione`, non `stato_codice`): una colonna che
# mostra una cosa e ordina per un'altra sembra semplicemente non ordinata —
# codice e descrizione non hanno lo stesso ordine alfabetico.
# ⛔ Mai input utente dentro l'ORDER BY: la whitelist e' chiusa.

# Colonne ordinabili della lista distinte.
DISTINTE_SORT_COLUMNS: dict[str, str] = {
    "data_contabile": "data_contabile",
    "codice": "codice",
    "stato_descrizione": "stato_descrizione",
    "origine": "origine",
    "centro_descrizione": "centro_descrizione",
    "totale_righe": "totale_righe",
}

# Colonne ordinabili della coda del riconciliatore (righe cross-distinta).
RIGHE_SORT_COLUMNS: dict[str, str] = {
    "data_pagamento": "data_pagamento",
    "importo": "importo",
    "stato_descrizione": "stato_descrizione",
    "contabile_codice": "contabile_codice",
}

# Colonne ordinabili dell'elenco delle rate fuori capienza.
RATE_FUORI_CAPIENZA_SORT_COLUMNS: dict[str, str] = {
    "data_scadenza": "data_scadenza",
    "motivo": "motivo",
    "residuo": "residuo",
    "importo_rata": "importo_rata",
    "fattura_numero": "fattura_numero",
}

# Colonne ordinabili dell'elenco delle eccedenze da sistemare.
# ⭐ Il default e' per CLIENTE, non per documento: la decisione si prende
#    guardando il cliente (D15-b) — compensare significa mettere insieme due
#    documenti suoi.
ECCEDENZE_SORT_COLUMNS: dict[str, str] = {
    "cliente_ragione_sociale": "cliente_ragione_sociale",
    "eccedenza_cliente": "eccedenza_cliente",
    "eccedenza": "eccedenza",
    "fattura_data": "fattura_data",
    "fattura_numero": "fattura_numero",
}

# ⭐ La utility di un conto: si legge nei DUE punti in cui si sceglie un conto —
# l'elenco dei conti agganciabili e il canale che ne ha gia' uno — perche' un
# elenco che non la dice fa scegliere il conto del gas al posto di quello
# dell'energia, e chi sbaglia se ne accorge dopo (BE-11).
# ⛔ NON e' una colonna di `enti_incasso`: la utility e' un fatto del CONTO, e
#    dichiararla anche sul canale sarebbe una seconda sede.
# ⚠️ Non si passa da `anagrafiche.vw_istanze_utilities_dettaglio` benche' la
#    porti: quella vista descrive l'istanza col suo INDIRIZZO — sei join, due
#    dei quali su viste di indirizzo che PostgreSQL non pota. Misurato con
#    EXPLAIN il 2026-08-27 sull'elenco dei conti: **928.86 contro 6.10**, per
#    decodificare una parola. La catena diretta e' anche la forma gia' in uso
#    in `BillingAccountRepository.search_lookup`.
# ⚠️ La descrizione e' NULL in DUE casi legittimi, e sono diversi: il conto non
#    ha istanza (`istanza_utility_id` e' nullable: e' il conto generico del
#    ruolo, cfr. `uq_src_bancari_..._no_istanza`), oppure l'istanza non ha PDP.
#    ⛔ A video NULL non e' un buco: e' «nessuna utility», e va reso come tale.
# ⚠️ Chi lo innesta usa una f-string: una graffa LETTERALE nell'SQL (un
#    `'{}'::jsonb`) andrebbe raddoppiata. Il difetto sarebbe rumoroso — errore
#    all'import, l'applicazione non parte — non silenzioso.
_UTILITY_DEL_CONTO_JOIN = """
      LEFT JOIN anagrafiche.istanze_utilities iu ON iu.id = src.istanza_utility_id
      LEFT JOIN anagrafiche.pdp p ON p.id = iu.pdp_id
      LEFT JOIN config.utilities u ON u.id = p.utility_id
"""

_ENTE_INCASSO_SELECT = f"""
    SELECT
        e.id, e.codice, e.codice_interno, e.descrizione, e.tipo, e.attivo,
        e.centro_riscossione_id,
        cr.codice          AS centro_codice,
        cr.descrizione     AS centro_descrizione,
        e.soggetto_ruolo_id,
        srp.ragione_sociale_completa AS soggetto_ragione_sociale,
        e.bank_branch_id,
        bb.name       AS bank_branch_nome,
        bb.bank_code  AS bank_branch_bank_code,
        e.soggetto_ruolo_conto_bancario_id,
        cb.iban            AS conto_iban,
        src.uso            AS conto_uso,
        src.soggetto_ruolo_id AS conto_soggetto_ruolo_id,
        src.istanza_utility_id AS conto_istanza_utility_id,
        u.descrizione      AS conto_utility_descrizione,
        e.formato_flusso, e.regole_match, e.meta
      FROM pagamenti.enti_incasso e
      LEFT JOIN pagamenti.centri_riscossione cr ON cr.id = e.centro_riscossione_id
      LEFT JOIN anagrafiche.soggetti_ruoli_conti_bancari src
             ON src.id = e.soggetto_ruolo_conto_bancario_id
      LEFT JOIN anagrafiche.conti_bancari cb ON cb.id = src.conto_bancario_id
      -- ⭐ Filiale e soggetto PSP IN CHIARO, e non e' cosmesi: il drawer li
      --    mostra su un canale gia' configurato, e senza il nome resterebbe un
      --    campo vuoto accanto a un id valorizzato — cioe' direbbe «non c'e'
      --    filiale» di un canale BANCA, dove la filiale e' obbligatoria.
      LEFT JOIN anagrafiche.bank_branches bb ON bb.id = e.bank_branch_id
      LEFT JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srp
             ON srp.soggetto_ruolo_id = e.soggetto_ruolo_id
      {_UTILITY_DEL_CONTO_JOIN}
"""

# Le colonne aggiornabili di un canale. ⛔ `codice_interno` NON c'e': e' la
# chiave stabile con cui il resto del sistema lo nomina, e cambiarla romperebbe
# i riferimenti senza che niente lo dica.
_COLONNE_ENTE_INCASSO_AGGIORNABILI = frozenset(
    {"codice", "descrizione", "tipo", "attivo", "centro_riscossione_id",
     "soggetto_ruolo_id", "bank_branch_id", "soggetto_ruolo_conto_bancario_id",
     "formato_flusso", "regole_match", "meta"}
)

# Colonne ordinabili degli ATTI DI SISTEMAZIONE di una fattura (lista 61).
# ⛔ Chiavata sui `campo_sorgente` FISICI, non sui codici logici: il frontend
#    monta le Column con `:field="col.campo_sorgente"` e manda QUELLO in
#    `order_by`. Chiavarla sui codici logici e' il difetto di `vendite.lotti`
#    (2026-07-31), e qui sarebbe stato peggio: prima di questa modifica il
#    metodo aveva `ORDER BY s.id` inchiodato e **ignorava** `order_by` in
#    silenzio — la freccia si girava sopra righe immobili, senza nemmeno un 400
#    a dirlo.
# `FROM` + `WHERE` degli ATTI DI SISTEMAZIONE di una fattura, in una sede sola.
# ⛔ Lo condividono la query di PAGINA e il conteggio di RIPIEGO: sono due
#    domande sullo stesso insieme, e scritte due volte diventano due insiemi al
#    primo filtro che se ne aggiunge a una sola delle due.
_SISTEMAZIONI_FROM_WHERE = """
              FROM pagamenti.sistemazioni s
             WHERE s.fattura_origine_id = %s"""

SISTEMAZIONI_SORT_COLUMNS: dict[str, str] = {
    "destinazione": "s.destinazione",
    "importo": "s.importo",
    "stato": "s.stato",
    "motivo": "s.motivo",
    "data_esecuzione": "s.data_esecuzione",
}

# ⭐ Le colonne DATA della lista 61. Il BB `sql_order_clause` le ordina DESC
#    quando il chiamante non indica un verso: «gli ordinamenti per data hanno
#    sempre default DESC» (Tid, 2026-09-02). Una data si legge dalla piu'
#    recente, e chiedere «ordina per data» ricevendo il caso piu' vecchio in
#    cima e' il contrario di cio' che si e' chiesto.
# ⚠️ Vive ACCANTO alla whitelist e non altrove: e' un sottoinsieme delle sue
#    chiavi, e a distanza le due si separerebbero senza che niente lo dica.
SISTEMAZIONI_SORT_COLONNE_DATA: frozenset[str] = frozenset({"data_esecuzione"})

# Colonne ordinabili dell'elenco dei canali di incasso.
# ⭐ CHIAVATA SUI `campo_sorgente` FISICI dal 2026-09-02, ed e' il giorno che il
#    commento precedente aveva previsto: *«il giorno in cui la schermata dei
#    canali si monta sul BB, `centro` va riscritta come `centro_descrizione` — o
#    l'intestazione rispondera' 400 al click»*. La lista e' seedata
#    (`pagamenti.canali_incasso`, id 60) con `campo_sorgente = centro_descrizione`,
#    quindi quel giorno e' arrivato.
# ⭐ E SI ORDINA PER LA DESCRIZIONE, non per il codice (decisione di Tid,
#    2026-09-02). Il valore era `centro_codice`: l'intestazione mostra
#    `centro_descrizione` e ordinava per un campo che a video non c'e'. Se
#    codice e descrizione non sono correlati l'ordine sembra arbitrario — e un
#    ordinamento che non corrisponde a cio' che si legge e' un difetto che
#    l'operatore vede e nessun test prende.
#    ⇒ **Si ordina la colonna che si vede.**
ENTI_INCASSO_SORT_COLUMNS: dict[str, str] = {
    "codice": "codice",
    "descrizione": "descrizione",
    "tipo": "tipo",
    "centro_descrizione": "centro_descrizione",
}

# Colonne jsonb che il driver restituisce come stringa fuori dall'ORM.
_JSONB_COLS = ("meta",)

# 🔴 Le colonne che questo repository accetta di aggiornare, e non e' una
# ripetizione della whitelist del service: quella dice che cosa il CONTRATTO
# API espone, questa e' l'ultimo cancello prima che un nome finisca dentro una
# stringa SQL. Il giorno in cui qualcuno chiamasse questi metodi con delle
# chiavi che arrivano da un payload, la differenza fra le due sarebbe una
# SQL injection.
_COLONNE_DISTINTA_AGGIORNABILI = frozenset(
    {"data_contabile", "data_registrazione", "ente_incasso_id",
     "importo_dichiarato", "meta"}
)
_COLONNE_RIGA_AGGIORNABILI = frozenset(
    {"importo", "riferimento_ente", "data_pagamento", "data_valuta",
     "data_operazione", "fattura_id", "billing_account_id", "scadenza_id",
     "forzata", "motivo_forzatura", "motivo_sospeso", "meta"}
)


class PagamentiRepository:
    """Accesso dati dello schema `pagamenti`."""

    # ══════════════════════════════════════════════════════════════
    #  Guard strutturale
    # ══════════════════════════════════════════════════════════════

    # Scopo: Impedisce che una lettura di perimetro giri su un ruolo BYPASSRLS.
    # Contesto: le policy di `pagamenti` sono l'unico cancello di queste liste.
    #        Su un ruolo che le scavalca la lista non fallirebbe: mostrerebbe
    #        il denaro di TUTTI gli emittenti, che e' molto peggio di un errore.
    @staticmethod
    def _guard_canale_sistema(metodo: str) -> None:
        ErrorManager.require(
            not connection_role_bypasses_rls(),
            code=_E_CHIAMATA,
            message="Operazione non disponibile dal canale di sistema.",
            detail=(
                "Le tabelle di pagamenti sono protette da RLS: lette da un "
                "ruolo BYPASSRLS perderebbero il perimetro emittente. Usare "
                "la connessione dell'utente della richiesta."
            ),
            function_name=f"{_FN}.{metodo}",
        )

    # Scopo: Esegue una lista paginata: pagina + totale in una valutazione, e
    #        il conteggio di ripiego per la pagina stantia.
    # Nota: era scritto tre volte (distinte, coda, rate fuori capienza) — e tre
    #       copie della stessa paginazione divergono alla prima correzione.
    # ⚠️ `order_clause` si compone dalla WHITELIST del chiamante e MAI da input
    #    utente: qui dentro finisce in una stringa SQL.
    @staticmethod
    def _lista_paginata(
        *,
        select_sql: str,
        params: list[Any],
        order_clause: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        data_sql = f"""
            SELECT *, COUNT(*) OVER () AS total_count FROM (
                {select_sql}
            ) q
            {order_clause}
            LIMIT %s OFFSET %s
        """
        # ⚠️ Il conteggio di ripiego serve SOLO a pagina oltre l'ultima: li' la
        # window function non ha righe su cui calcolare il totale e
        # risponderebbe zero. Senza, a chi e' rimasto su una pagina stantia di
        # una lista che si e' accorciata sotto di lui diremmo «nessun
        # risultato» — una cosa falsa, con l'aria di un dato.
        count_sql = f"SELECT COUNT(*) FROM ({select_sql}) q"
        return fetch_paged_with_total(
            data_sql,
            [*params, limit, offset],
            fallback_count_sql=count_sql,
            fallback_params=list(params),
            offset=offset,
        )

    # ══════════════════════════════════════════════════════════════
    #  Cataloghi di stato
    # ══════════════════════════════════════════════════════════════

    # Scopo: Il vocabolario degli stati della distinta, coi suoi flag.
    # Nota: `obsoleto_dal` filtra i valori RITIRATI — che restano leggibili
    #       sui documenti vecchi ma non si propongono piu' a nessuno.
    def list_stati_distinta(self) -> list[StatoCatalogoRow]:
        sql = """
            SELECT id, codice, codice_interno, descrizione, is_final, ordine
              FROM pagamenti.vendite_contabili_stati
             WHERE attivo IS TRUE
               AND (obsoleto_dal IS NULL OR obsoleto_dal > CURRENT_DATE)
             ORDER BY ordine NULLS LAST, id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return rows_to_list(cursor)  # type: ignore[return-value]

    # Scopo: Il vocabolario degli stati della riga, coi due flag che governano
    #        l'interfaccia — `is_postabile` (occupa spazio, si puo' registrare)
    #        e `richiede_abbinamento` (pretende fattura e cliente).
    def list_stati_riga(self) -> list[StatoRigaCatalogoRow]:
        sql = """
            SELECT id, codice, codice_interno, descrizione, is_final, ordine,
                   is_postabile, richiede_abbinamento
              FROM pagamenti.vendite_contabili_righe_stati
             WHERE attivo IS TRUE
               AND (obsoleto_dal IS NULL OR obsoleto_dal > CURRENT_DATE)
             ORDER BY ordine NULLS LAST, id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return rows_to_list(cursor)  # type: ignore[return-value]

    # ══════════════════════════════════════════════════════════════
    #  Distinte — lettura
    # ══════════════════════════════════════════════════════════════

    # Scopo: Elenco paginato delle distinte contabili con i display field in
    #        JOIN e i totali derivati.
    # Perimetro: la RLS della testata; nessun filtro applicativo aggiuntivo
    #        (le policy passano dal canale e dalla fattura, non da una colonna
    #        emittente su questa tabella).
    def list_distinte(
        self,
        *,
        stato_codice: str | None = None,
        origine: str | None = None,
        centro_riscossione_id: int | None = None,
        ente_incasso_id: int | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[DistintaRow], int]:
        self._guard_canale_sistema("list_distinte")

        conditions: list[str] = []
        params: list[Any] = []
        if stato_codice is not None:
            conditions.append("st.codice_interno = %s")
            params.append(stato_codice)
        if origine is not None:
            conditions.append("c.origine = %s")
            params.append(origine)
        if centro_riscossione_id is not None:
            conditions.append("c.centro_riscossione_id = %s")
            params.append(centro_riscossione_id)
        if ente_incasso_id is not None:
            conditions.append("c.ente_incasso_id = %s")
            params.append(ente_incasso_id)
        if data_da is not None:
            conditions.append("c.data_contabile >= %s")
            params.append(data_da)
        if data_a is not None:
            conditions.append("c.data_contabile <= %s")
            params.append(data_a)
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # ⚠️ La direzione la compone l'helper condiviso, e porta con se' la
        # posizione dei NULL: i vuoti vanno dove starebbe lo zero (in coda
        # scendendo, in testa salendo). ⛔ Non si incolla un `NULLS LAST` fisso:
        # sarebbe sintatticamente doppio, e su una lista che si ordina dal piu'
        # recente porterebbe i campi vuoti in cima.
        # Tiebreak nella STESSA direzione della colonna primaria: due distinte
        # dello stesso giorno non devono cambiare posto fra una pagina e l'altra.
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=DISTINTE_SORT_COLUMNS,
            default="data_contabile",
            tiebreak="id",
            default_desc=True,
        )

        rows, total = self._lista_paginata(
            select_sql=f"{_DISTINTA_SELECT}{_TOTALI_LATERAL}{where_clause}",
            params=params,
            order_clause=f"ORDER BY {ordinamento}",
            limit=limit,
            offset=offset,
        )
        return [self._shape(row) for row in rows], total

    # Scopo: Dettaglio di una distinta (testata + display + totali derivati).
    # Risultato: None se non esiste — o se il perimetro non la lascia vedere,
    #        e i due casi sono volutamente indistinguibili al chiamante.
    def get_distinta(self, contabile_id: int) -> DistintaRow | None:
        self._guard_canale_sistema("get_distinta")
        sql = f"""
            {_DISTINTA_SELECT}
            {_TOTALI_LATERAL}
            WHERE c.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(contabile_id)])
            rows = rows_to_list(cursor)
        return self._shape(rows[0]) if rows else None

    # ══════════════════════════════════════════════════════════════
    #  Distinte — scrittura
    # ══════════════════════════════════════════════════════════════

    # Scopo: Apre (o ritrova) la distinta manuale dell'operatore.
    # ⭐ E' un GET **or** CREATE, e la chiave di riuso comprende CHI STA
    #    LAVORANDO oltre alla giornata e al canale: due operatori non si
    #    contendono la stessa distinta, e il lock che sarebbe servito a
    #    governarla non si costruisce.
    # ⛔ L'operatore NON si passa: lo mette la funzione dall'identita' della
    #    connessione. Passarlo dal backend sarebbe una seconda verita'.
    # ⚠️ Il valore di ritorno e' il solo `id`: «creata» e «riaperta» non si
    #    distinguono dalla chiamata — si leggono dal dettaglio (ha righe o no).
    def get_or_create_distinta(
        self,
        *,
        centro_riscossione_id: int,
        data_contabile: date,
        data_registrazione: date | None = None,
        ente_incasso_id: int | None = None,
        codice_stato_interno: str = "BOZZA",
        origine: str = "MANUALE",
        meta: str = "{}",
    ) -> int:
        sql = """
            SELECT pagamenti.fn_get_or_create_vendite_contabile(
                p_centro_riscossione_id := %s,
                p_data_contabile        := %s,
                p_data_registrazione    := COALESCE(%s, CURRENT_DATE),
                p_ente_incasso_id       := %s,
                p_codice_stato_interno  := %s,
                p_meta                  := %s::jsonb,
                p_origine               := %s
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [
                    int(centro_riscossione_id),
                    data_contabile,
                    data_registrazione,
                    ente_incasso_id,
                    codice_stato_interno,
                    meta,
                    origine,
                ],
            )
            row = cursor.fetchone()
        return int(row[0])

    # Scopo: Compone la clausola SET di un UPDATE parziale, verificando che
    #        OGNI nome di colonna sia nella whitelist del suo oggetto.
    # ⛔ Nessun nome arriva mai in SQL senza passare di qui.
    @staticmethod
    def _set_clause(
        campi: dict[str, Any], consentite: frozenset[str], metodo: str
    ) -> tuple[str, list[Any]]:
        fuori = sorted(c for c in campi if c not in consentite)
        ErrorManager.require(
            not fuori,
            code=_E_CHIAMATA,
            message="Aggiornamento non ammesso su queste colonne.",
            detail=f"Colonne non aggiornabili: {', '.join(fuori)}",
            function_name=f"{_FN}.{metodo}",
        )
        assegnazioni: list[str] = []
        params: list[Any] = []
        for colonna, valore in campi.items():
            assegnazioni.append(
                f"{colonna} = %s::jsonb" if colonna in _JSONB_COLS else f"{colonna} = %s"
            )
            params.append(valore)
        return ", ".join(assegnazioni), params

    # Scopo: Aggiorna i campi che una persona compila sulla testata.
    # ⛔ Lo stato NON passa di qui: cambiarlo e' un'azione, e la matrice delle
    #    transizioni ha un guard suo che va fatto parlare.
    # Risultato: numero di righe toccate (0 = distinta inesistente o fuori
    #        perimetro, e il service lo traduce in 404).
    def update_distinta(self, contabile_id: int, campi: dict[str, Any]) -> int:
        if not campi:
            return 0
        set_clause, params = self._set_clause(
            campi, _COLONNE_DISTINTA_AGGIORNABILI, "update_distinta"
        )
        params.append(int(contabile_id))
        sql = f"""
            UPDATE pagamenti.vendite_contabili
               SET {set_clause}
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount

    # Scopo: Cambia lo stato della distinta risolvendo il codice a catalogo.
    # ⚠️ Un UPDATE solo: la transizione la giudicano i guard del database
    #    (matrice, quadratura col dichiarato, riapertura solo se MANUALE,
    #    chiusura con righe ancora pronte). Il backend non li replica.
    def set_stato_distinta(self, contabile_id: int, codice_stato_interno: str) -> int:
        sql = """
            UPDATE pagamenti.vendite_contabili c
               SET stato_id = st.id
              FROM pagamenti.vendite_contabili_stati st
             WHERE c.id = %s
               AND st.codice_interno = %s
               AND st.attivo IS TRUE
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(contabile_id), codice_stato_interno])
            return cursor.rowcount

    # ══════════════════════════════════════════════════════════════
    #  Righe
    # ══════════════════════════════════════════════════════════════

    # Scopo: Le righe di una distinta, ordine stabile.
    # Nota: nessuna paginazione — le righe sono il dettaglio di UN documento e
    #       si leggono insieme alla sua testata; la lista cross-distinta (la
    #       coda del riconciliatore) e' un'altra cosa e ha il suo metodo.
    def list_righe(self, contabile_id: int) -> list[RigaContabileRow]:
        self._guard_canale_sistema("list_righe")
        # ⚠️ Solo le righe ATTIVE, e senza un interruttore per vederle tutte:
        # una riga disattivata non e' un dato da mostrare con un filtro, e un
        # parametro che nessuno passa e' superficie che invecchia. Quando
        # servira' davvero, si aggiunge con il suo consumatore.
        sql = f"""
            {_RIGA_SELECT}
            WHERE r.contabile_id = %s
              AND r.attivo IS TRUE
            ORDER BY r.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(contabile_id)])
            rows = rows_to_list(cursor)
        return [self._shape(row) for row in rows]

    # Scopo: Dettaglio di una singola riga contabile.
    def get_riga(self, riga_id: int) -> RigaContabileRow | None:
        self._guard_canale_sistema("get_riga")
        sql = f"""
            {_RIGA_SELECT}
            WHERE r.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(riga_id)])
            rows = rows_to_list(cursor)
        return self._shape(rows[0]) if rows else None

    # Scopo: Crea una riga sotto una distinta.
    # ⚠️ Lo stato si risolve dal catalogo per codice: gli id sono smallint
    #    seminati e non si scrivono a mano da nessuna parte (mai id cablati).
    def create_riga(
        self,
        *,
        contabile_id: int,
        importo: Decimal,
        codice_stato_interno: str,
        riferimento_ente: str | None = None,
        data_pagamento: date | None = None,
        data_valuta: date | None = None,
        data_operazione: date | None = None,
        motivo_sospeso: str | None = None,
        meta: str = "{}",
    ) -> int:
        # ⛔ Niente `fattura_id`, `billing_account_id`, `scadenza_id` qui: una
        # riga NASCE senza destinazione (`DA_ABBINARE`), e l'abbinamento e' un
        # verbo con le sue regole — la coerenza rata/fattura e la capienza. Dei
        # parametri accettati qui e mai passati sarebbero una seconda porta per
        # scriverli, che aggirerebbe quel verbo senza dirlo.
        sql = """
            INSERT INTO pagamenti.vendite_contabili_righe (
                contabile_id, importo, stato_id, riferimento_ente,
                data_pagamento, data_valuta, data_operazione,
                motivo_sospeso, meta
            )
            SELECT
                %s, %s, st.id, %s,
                %s, %s, %s,
                %s, %s::jsonb
              FROM pagamenti.vendite_contabili_righe_stati st
             WHERE st.codice_interno = %s
               AND st.attivo IS TRUE
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [
                    int(contabile_id), importo, riferimento_ente,
                    data_pagamento, data_valuta, data_operazione,
                    motivo_sospeso, meta,
                    codice_stato_interno,
                ],
            )
            row = cursor.fetchone()
        # Nessuna riga di ritorno = il codice di stato non esiste a catalogo:
        # non e' un dato dell'operatore, e il service lo traduce come tale.
        ErrorManager.require(
            row is not None,
            code="E_CONTABILE_STATO_NON_CONFIGURATO",
            message="Stato riga contabile non configurato.",
            detail=f"codice_interno={codice_stato_interno} assente o non attivo.",
            function_name=f"{_FN}.create_riga",
        )
        assert row is not None
        return int(row[0])

    # Scopo: Aggiorna i FATTI di una riga (importo, date, riferimento) e le
    #        decisioni che non sono un'azione di dominio.
    def update_riga(self, riga_id: int, campi: dict[str, Any]) -> int:
        if not campi:
            return 0
        set_clause, params = self._set_clause(
            campi, _COLONNE_RIGA_AGGIORNABILI, "update_riga"
        )
        params.append(int(riga_id))
        sql = f"""
            UPDATE pagamenti.vendite_contabili_righe
               SET {set_clause}
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount

    # Scopo: Cambia lo stato di una riga risolvendo il codice a catalogo.
    # ⚠️ Come per la testata: un UPDATE solo, e i guard del database dicono se
    #    la transizione e' ammessa e se i dati che quello stato pretende ci
    #    sono (fattura e cliente su ABBINATA, per esempio).
    def set_stato_riga(self, riga_id: int, codice_stato_interno: str) -> int:
        sql = """
            UPDATE pagamenti.vendite_contabili_righe r
               SET stato_id = st.id
              FROM pagamenti.vendite_contabili_righe_stati st
             WHERE r.id = %s
               AND st.codice_interno = %s
               AND st.attivo IS TRUE
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(riga_id), codice_stato_interno])
            return cursor.rowcount

    # Scopo: Imputa una riga a una fattura (e, quando c'e', a una rata).
    # ⭐ UN SOLO `UPDATE`: i dati dell'abbinamento e lo stato viaggiano insieme,
    #    perche' sono lo stesso gesto — «questa riga e' di questo documento».
    #    Separarli lascerebbe per un istante una riga abbinata a meta', che i
    #    guard rifiuterebbero comunque, ma con un messaggio sull'ordine delle
    #    scritture invece che sul merito.
    # ⚠️ `forzata` e' il SECONDO TEMPO della capienza (D14-d): il primo
    #    tentativo arriva senza, il guard rifiuta con la ragione e i numeri, e
    #    la conferma dell'operatore torna qui come `forzata = true` — che resta
    #    SCRITTA sulla riga, ed e' cio' che l'elenco a valle legge.
    def abbina_riga(
        self,
        *,
        riga_id: int,
        fattura_id: int,
        billing_account_id: int,
        scadenza_id: int | None,
        forzata: bool,
        motivo_forzatura: str | None,
        codice_stato_interno: str,
    ) -> int:
        sql = """
            UPDATE pagamenti.vendite_contabili_righe r
               SET fattura_id         = %s,
                   billing_account_id = %s,
                   scadenza_id        = %s,
                   forzata            = %s,
                   motivo_forzatura   = %s,
                   stato_id           = st.id
              FROM pagamenti.vendite_contabili_righe_stati st
             WHERE r.id = %s
               AND st.codice_interno = %s
               AND st.attivo IS TRUE
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [
                    int(fattura_id), int(billing_account_id), scadenza_id,
                    bool(forzata), motivo_forzatura,
                    int(riga_id), codice_stato_interno,
                ],
            )
            return cursor.rowcount

    # ══════════════════════════════════════════════════════════════
    #  I saldi — le tre letture, e nient'altro le chiama
    # ══════════════════════════════════════════════════════════════

    # Scopo: Il saldo di una RATA: residuo, in lavorazione, incassato.
    # ⭐ Tre numeri e non uno: «quanto manca», «quanto e' gia' digitato ma non
    #    registrato» e «quanto e' entrato davvero in banca» sono tre domande
    #    diverse, e la terza esclude i centri interni (fondi, compensazioni).
    # ⚠️ `escludi_riga_id` serve a chiedere lo spazio PRIMA DI SE': e' cosi' che
    #    si verifica se una riga ci sta, senza contarsi addosso.
    def get_saldo_rata(
        self, scadenza_id: int, *, escludi_riga_id: int | None = None
    ) -> dict[str, Any] | None:
        # Le tre funzioni di saldo sono SECURITY INVOKER: la row security del
        # chiamante si applica da sola, e su un ruolo che la scavalca
        # risponderebbero i numeri di TUTTI gli emittenti.
        self._guard_canale_sistema("get_saldo_rata")
        sql = """
            SELECT saldo, in_lavorazione, incassato, has_movimenti
              FROM pagamenti.fn_get_saldo_rata(%s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(scadenza_id), escludi_riga_id])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None

    # Scopo: Il saldo di un DOCUMENTO: residuo e denaro in lavorazione.
    # ⭐ UNA query per due funzioni, e non e' solo un round-trip risparmiato su
    #    un pannello che si apre a ogni fattura: due `SELECT` separate leggono
    #    DUE ISTANTI diversi. Se una registrazione atterra fra l'una e l'altra,
    #    il pannello mostra un residuo di prima accanto a un «in lavorazione»
    #    di dopo — due numeri veri che insieme raccontano una cosa falsa.
    # ⭐ TRE numeri, dal 2026-08-29: la richiesta DB-10 e' atterrata il 25/08 e
    #    `fn_get_saldo_fattura` risponde `saldo, in_lavorazione, incassato,
    #    has_movimenti` — la stessa forma e lo stesso ordine della sorella della
    #    rata. Fino a ieri qui se ne leggevano DUE e l'`incassato` si buttava
    #    via: la richiesta che questo cantiere aveva fatto era stata esaudita e
    #    nessuno era passato a raccoglierla.
    # ⛔ E `in_lavorazione` si prende da `f`, non da `fn_get_saldo_fattura_contabili`:
    #    il numero e' lo stesso — la funzione delega proprio a quella — ma
    #    leggerlo dalla seconda gli darebbe DUE sorgenti con lo stesso nome, che
    #    e' cio' che il vincolo «una sede sola per i saldi» vieta.
    # ⭐ UNA funzione sola, e non e' un'ottimizzazione. Fino al 2026-08-29 qui
    #    c'era un `CROSS JOIN` con `fn_get_saldo_fattura_contabili` per prendere
    #    `has_righe_postabili`: quella colonna **non la legge nessuno** — ne'
    #    service, ne' view, ne' frontend — quindi il join faceva girare una
    #    seconda volta, a ogni apertura del drawer fattura, una funzione che
    #    `fn_get_saldo_fattura` chiama gia' al suo interno.
    #    ⚠️ E non era gratis: `fn_get_saldo_fattura` NON e' dichiarata STABLE (il
    #    suo ramo d'errore scrive nel registro), quindi due valutazioni sono due
    #    letture indipendenti — la trappola gia' pagata sul guard del fondo, dove
    #    una funzione VOLATILE letta due volte poteva accettare meta' condizione
    #    e rifiutare l'altra.
    #    📮 Se un giorno servira' `has_righe_postabili`, la sede giusta e'
    #    aggiungerlo a `fn_get_saldo_fattura` — che quella funzione la interroga
    #    gia' — non rimettere il join qui.
    def get_saldo_documento(self, fattura_id: int) -> dict[str, Any] | None:
        self._guard_canale_sistema("get_saldo_documento")
        sql = """
            SELECT f.saldo, f.in_lavorazione, f.incassato, f.has_movimenti
              FROM pagamenti.fn_get_saldo_fattura(%s) f
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None

    # Scopo: Le rate di un documento, con il loro saldo accanto.
    # ⭐ Sta in `pagamenti` e non in `vendite` benche' le rate siano di vendite:
    #    la domanda e' «quanto resta su questa rata», e a saperla rispondere e'
    #    questo schema. ⚠️ E `vendite` non potrebbe chiederglielo: le chiamate
    #    laterali fra moduli di pari livello non sono ammesse (api.md).
    def list_rate_con_saldo(self, fattura_id: int) -> list[dict[str, Any]]:
        self._guard_canale_sistema("list_rate_con_saldo")
        sql = """
            SELECT
                sc.id                AS scadenza_id,
                sc.numero_rata,
                sc.data_scadenza,
                sc.importo,
                s.saldo              AS residuo,
                s.in_lavorazione,
                s.incassato,
                s.has_movimenti
              FROM vendite.fatture_scadenze sc
              CROSS JOIN LATERAL pagamenti.fn_get_saldo_rata(sc.id) s
             WHERE sc.fattura_id = %s
             ORDER BY sc.numero_rata NULLS LAST, sc.data_scadenza NULLS LAST, sc.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            return rows_to_list(cursor)

    # ══════════════════════════════════════════════════════════════
    #  Le due code di lavoro
    # ══════════════════════════════════════════════════════════════

    # Scopo: Le righe di TUTTE le distinte in uno degli stati chiesti — la coda
    #        del riconciliatore.
    # ⭐ Un endpoint solo per due code: «da abbinare» e «sospese» sono due
    #    mestieri diversi (D12-f) e due voci di menu, ma la stessa lista con un
    #    filtro diverso gia' impostato. Due definizioni a catalogo per due
    #    schermate identiche sarebbero due cose da tenere allineate.
    def list_righe_coda(
        self,
        *,
        stati: tuple[str, ...],
        billing_account_id: int | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[RigaCodaRow], int]:
        self._guard_canale_sistema("list_righe_coda")

        conditions = ["r.attivo IS TRUE", "rs.codice_interno = ANY(%s)"]
        params: list[Any] = [list(stati)]
        if billing_account_id is not None:
            conditions.append("r.billing_account_id = %s")
            params.append(billing_account_id)
        if data_da is not None:
            conditions.append("c.data_contabile >= %s")
            params.append(data_da)
        if data_a is not None:
            conditions.append("c.data_contabile <= %s")
            params.append(data_a)

        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=RIGHE_SORT_COLUMNS,
            default="data_pagamento",
            tiebreak="id",
            default_desc=True,
        )

        rows, total = self._lista_paginata(
            select_sql=f'{_RIGA_CODA_SELECT} WHERE {" AND ".join(conditions)}',
            params=params,
            order_clause=f"ORDER BY {ordinamento}",
            limit=limit,
            offset=offset,
        )
        return [self._shape(row) for row in rows], total

    # Scopo: L'elenco delle rate uscite dalla banda di capienza.
    # ⭐ Senza questo elenco la forzatura sarebbe «un modo per nascondere, non
    #    per registrare»: e' la ragione per cui la vista sta nello stesso lotto
    #    del guard che permette di forzare.
    # ⚠️ `motivo` ha due valori e vanno mostrati entrambi: `SOVRA_INCASSATA` e
    #    `MOVIMENTO_CONTRARIO` — un rimborso dove non era entrato niente e' il
    #    caso che ha fatto cadere l'asimmetria di D1-bis.
    def list_rate_fuori_capienza(
        self,
        *,
        motivo: str | None = None,
        billing_account_id: int | None = None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        self._guard_canale_sistema("list_rate_fuori_capienza")

        conditions: list[str] = []
        params: list[Any] = []
        if motivo is not None:
            conditions.append("v.motivo = %s")
            params.append(motivo)
        if billing_account_id is not None:
            conditions.append("v.billing_account_id = %s")
            params.append(billing_account_id)
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=RATE_FUORI_CAPIENZA_SORT_COLUMNS,
            default="data_scadenza",
            tiebreak="scadenza_id",
            default_desc=True,
        )

        return self._lista_paginata(
            select_sql=(
                f"SELECT v.* FROM pagamenti.vw_rate_fuori_capienza v {where_clause}"
            ),
            params=params,
            order_clause=(
                f"ORDER BY {ordinamento}"
            ),
            limit=limit,
            offset=offset,
        )

    # ══════════════════════════════════════════════════════════════
    #  I canali di incasso — da dove arrivano i soldi
    # ══════════════════════════════════════════════════════════════

    # Scopo: L'elenco dei canali, coi display field di chi li guarda.
    # ⭐ Il **conto** e' in JOIN e non e' un dettaglio: e' da li' che il
    #    database ricava di chi sono i soldi arrivati prima della fattura, ed e'
    #    la colonna che rende leggibile una riga di configurazione altrimenti
    #    fatta di id.
    def list_enti_incasso(
        self,
        *,
        tipo: str | None = None,
        centro_riscossione_id: int | None = None,
        attivo: bool | None = None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        self._guard_canale_sistema("list_enti_incasso")

        conditions: list[str] = []
        params: list[Any] = []
        if tipo is not None:
            conditions.append("e.tipo = %s")
            params.append(tipo)
        if centro_riscossione_id is not None:
            conditions.append("e.centro_riscossione_id = %s")
            params.append(centro_riscossione_id)
        if attivo is not None:
            conditions.append("e.attivo = %s")
            params.append(attivo)
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=ENTI_INCASSO_SORT_COLUMNS,
            default="codice",
            tiebreak="id",
        )

        select_sql = f"""
            {_ENTE_INCASSO_SELECT}
            {where_clause}
        """
        return self._lista_paginata(
            select_sql=select_sql,
            params=params,
            order_clause=f"ORDER BY {ordinamento}",
            limit=limit,
            offset=offset,
        )

    # Scopo: Il dettaglio di un canale.
    def get_ente_incasso(self, ente_id: int) -> dict[str, Any] | None:
        self._guard_canale_sistema("get_ente_incasso")
        sql = f"{_ENTE_INCASSO_SELECT} WHERE e.id = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(ente_id)])
            rows = rows_to_list(cursor)
        return self._shape(rows[0]) if rows else None

    # Scopo: L'emittente indicato e' dentro il perimetro di chi sta chiedendo?
    # 🔴 Serve perche' `anagrafiche.soggetti_ruoli_conti_bancari` ha la row
    #    security SPENTA di proposito: la' il perimetro non lo mette il
    #    database, quindi se non lo mette il backend non lo mette nessuno.
    #    ⛔ Misurato il 2026-08-28 (E-4): senza questa domanda un operatore
    #    dell'emittente A leggeva l'IBAN di incasso dell'emittente B passando il
    #    suo `soggetto_ruolo_id` — e senza nessun errore.
    # ⛔ SENZA UTENTE NON SI PASSA, e non e' pignoleria: la canonica
    #    `fn_check_user_emittente_scope` risponde **true** quando
    #    `p_auth_user_id` e' NULL (regola 1, «job batch»). Delegarle la domanda
    #    su un percorso senza GUC aprirebbe il perimetro invece di chiuderlo:
    #    qui «non so chi sei» vale **no**.
    def emittente_nel_perimetro(self, emittente_soggetto_ruolo_id: int) -> bool:
        self._guard_canale_sistema("emittente_nel_perimetro")
        with connection.cursor() as cursor:
            # ⚠️ La GUC si chiama `app.current_user_id`, NON `app.auth_user_id`:
            #    e' il nome che usano le policy RLS di questo schema, ed e' da
            #    li' che si legge — mai dal nome che sembra giusto. Con il nome
            #    sbagliato il `current_setting` risponde NULL e questa funzione
            #    rifiuta TUTTO, compreso chi ha diritto: un difetto che i mock
            #    non vedono, perche' i mock non hanno GUC.
            cursor.execute(
                "SELECT NULLIF(current_setting('app.current_user_id', true), '')::int"
            )
            row = cursor.fetchone()
            auth_user_id = row[0] if row else None
            if auth_user_id is None:
                return False
            cursor.execute(
                "SELECT COALESCE(script.fn_scope_ef_whitelist_via_sr(%s, %s), false)",
                [int(auth_user_id), int(emittente_soggetto_ruolo_id)],
            )
            return bool(cursor.fetchone()[0])

    # Scopo: I conti che un emittente puo' agganciare a un canale.
    # 🔴 **Solo quelli con `uso = 'INCASSO'`**, ed e' la richiesta BE-8: il
    #    database rifiuta gli altri con un errore parlante, ma un elenco che li
    #    propone fa sbagliare — e chi sbaglia se ne accorge dopo aver compilato
    #    tutto il resto.
    # ⚠️ Il livello e' quello del RUOLO (`soggetti_ruoli_conti_bancari`) e non
    #    del soggetto: e' li' che vive l'unicita' «un conto INCASSO -> un solo
    #    soggetto», che e' la garanzia da cui il perimetro degli incassi dipende.
    #    Un conto censito solo a livello soggetto NON e' agganciabile, e non e'
    #    una svista del modello: e' quella garanzia.
    def list_conti_incasso(self, soggetto_ruolo_id: int) -> list[dict[str, Any]]:
        self._guard_canale_sistema("list_conti_incasso")
        # 🔴 IL PERIMETRO, e sta QUI e non nel service: e' lo stesso posto e la
        #    stessa ragione di `_guard_canale_sistema` — il repository e'
        #    l'ultimo cancello prima della stringa SQL, e un controllo un piano
        #    piu' su lo salta il secondo chiamante che nascera'.
        # ⚠️ Si RIFIUTA, non si risponde vuoto: un elenco vuoto direbbe «questo
        #    emittente non ha conti di incasso», che e' un'altra frase — e
        #    falsa. E' la trappola del conteggio fail-closed.
        ErrorManager.require(
            self.emittente_nel_perimetro(soggetto_ruolo_id),
            code=_E_SCOPE_EMITTENTE,
            message="Questo emittente non e' nel tuo perimetro.",
            detail=f"soggetto_ruolo_id={soggetto_ruolo_id}",
            context={"field": "soggetto_ruolo_id"},
            function_name=f"{_FN}.list_conti_incasso",
        )
        sql = f"""
            SELECT src.id            AS soggetto_ruolo_conto_bancario_id,
                   src.soggetto_ruolo_id,
                   src.predefinito,
                   src.intestazione_dichiarata,
                   cb.id             AS conto_bancario_id,
                   cb.iban,
                   cb.bic_swift,
                   cb.intestatario_predefinito,
                   -- ⭐ La utility del conto: qui e' la tendina in cui si SCEGLIE,
                   --    quindi e' il punto in cui non dirla fa sbagliare (BE-11).
                   src.istanza_utility_id AS conto_istanza_utility_id,
                   u.descrizione     AS conto_utility_descrizione
              FROM anagrafiche.soggetti_ruoli_conti_bancari src
              JOIN anagrafiche.conti_bancari cb ON cb.id = src.conto_bancario_id
              {_UTILITY_DEL_CONTO_JOIN}
             WHERE src.soggetto_ruolo_id = %s
               AND src.uso = 'INCASSO'
               AND src.bloccato IS NOT TRUE
               -- Le date di validita' ordinano e filtrano sempre: un conto
               -- scaduto non si propone. `COALESCE(valido_al, 'infinity')`
               -- perche' scadenza vuota = validita' infinita.
               AND (src.valido_dal IS NULL OR src.valido_dal <= CURRENT_DATE)
               AND COALESCE(src.valido_al, 'infinity'::date) >= CURRENT_DATE
             ORDER BY src.predefinito DESC, cb.iban
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(soggetto_ruolo_id)])
            return rows_to_list(cursor)

    # Scopo: Crea un canale di incasso.
    # ⚠️ Nessuna funzione madre: e' un `INSERT` su una tabella di
    #    configurazione, e i quattro guard (tipo/filiale, conto di incasso,
    #    coerenza PSP, scope emittente) parlano da soli.
    def create_ente_incasso(self, campi: dict[str, Any]) -> int:
        colonne = list(campi)
        segnaposti = ", ".join(
            "%s::jsonb" if c in _JSONB_COLS or c == "regole_match" else "%s"
            for c in colonne
        )
        sql = f"""
            INSERT INTO pagamenti.enti_incasso ({", ".join(colonne)})
            VALUES ({segnaposti})
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [campi[c] for c in colonne])
            row = cursor.fetchone()
        return int(row[0])

    # Scopo: Aggiorna un canale di incasso.
    def update_ente_incasso(self, ente_id: int, campi: dict[str, Any]) -> int:
        if not campi:
            return 0
        set_clause, params = self._set_clause(
            campi, _COLONNE_ENTE_INCASSO_AGGIORNABILI, "update_ente_incasso"
        )
        params.append(int(ente_id))
        sql = f"""
            UPDATE pagamenti.enti_incasso
               SET {set_clause}
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount

    # ══════════════════════════════════════════════════════════════
    #  Le sistemazioni — il denaro di troppo
    # ══════════════════════════════════════════════════════════════

    # Scopo: L'elenco dei documenti su cui e' entrato piu' del dovuto.
    # ⭐ La vista porta GIA' il raggruppamento per cliente in finestra
    #    (`eccedenza_cliente`, `documenti_cliente`): qui non si somma niente —
    #    rifarlo in Python sarebbe una seconda aritmetica da tenere allineata.
    # ⚠️ Il nome del cliente NON e' nella vista: si aggiunge in JOIN, perche' un
    #    elenco che si guarda per cliente e mostra un id non si guarda.
    def list_eccedenze(
        self,
        *,
        chi_e_in_credito: str | None = None,
        billing_account_id: int | None = None,
        order_by: str,
        order_dir: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        self._guard_canale_sistema("list_eccedenze")

        conditions: list[str] = []
        params: list[Any] = []
        if chi_e_in_credito is not None:
            conditions.append("v.chi_e_in_credito = %s")
            params.append(chi_e_in_credito)
        if billing_account_id is not None:
            conditions.append("v.billing_account_id = %s")
            params.append(billing_account_id)
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        sort_col = ECCEDENZE_SORT_COLUMNS.get(order_by, "eccedenza_cliente")
        direction = sql_order_direction(order_dir, default_desc=True)
        tiebreak = sql_tiebreak_direction(direction)

        select_sql = f"""
            SELECT v.*,
                   srd.ragione_sociale_completa AS cliente_ragione_sociale
              FROM pagamenti.vw_eccedenze_da_sistemare v
              LEFT JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srd
                     ON srd.soggetto_ruolo_id = v.cliente_soggetto_ruolo_id
              {where_clause}
        """
        return self._lista_paginata(
            select_sql=select_sql,
            params=params,
            # ⚠️ Tiebreak sul CLIENTE prima che sul documento: ordinando per
            # eccedenza di cliente, i documenti dello stesso cliente devono
            # restare insieme — altrimenti l'elenco «per cliente» li sparpaglia.
            order_clause=(
                f"ORDER BY {sort_col} {direction}, "
                f"cliente_soggetto_ruolo_id {tiebreak}, fattura_id {tiebreak}"
            ),
            limit=limit,
            offset=offset,
        )

    # Scopo: Cliente ed emittente di una fattura, DERIVATI e non dichiarati.
    # 🔴 Il guard sui dati li verifica con un codice TECNICO apposta: «l'emittente
    #    e il cliente non li sceglie una persona in un modulo, li DERIVA chi
    #    costruisce l'atto». Prenderli dal payload significherebbe far arrivare
    #    al database una dichiarazione che il database sa gia' — e che, se
    #    sbagliata, il suo autore non puo' correggere.
    # ⚠️ Lettura sotto RLS: una fattura fuori perimetro non risponde, e il
    #    chiamante lo traduce in «non trovata».
    def get_riferimenti_fattura(self, fattura_id: int) -> dict[str, Any] | None:
        self._guard_canale_sistema("get_riferimenti_fattura")
        sql = """
            SELECT f.id                       AS fattura_id,
                   f.emittente_soggetto_ruolo_id,
                   f.billing_account_id,
                   ba.soggetto_ruolo_id       AS cliente_soggetto_ruolo_id
              FROM vendite.fatture f
              JOIN anagrafiche.billing_account ba ON ba.id = f.billing_account_id
             WHERE f.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(fattura_id)])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None

    # Scopo: Registra l'atto di sistemazione.
    # ⭐ Un `INSERT`, non una funzione madre: una scrittura sola non ha bisogno
    #    di una madre, e inventarne una avrebbe aggiunto un oggetto che non
    #    garantisce niente in piu'.
    # ⚠️ Nasce in `BOZZA` (default di colonna): registrare una decisione non e'
    #    ancora eseguirla — il denaro si muove alla conferma.
    def create_sistemazione(
        self,
        *,
        destinazione: str,
        importo: Decimal,
        fattura_origine_id: int,
        cliente_soggetto_ruolo_id: int,
        emittente_soggetto_ruolo_id: int,
        fattura_destinazione_id: int | None = None,
        motivo: str | None = None,
        meta: str = "{}",
    ) -> int:
        sql = """
            INSERT INTO pagamenti.sistemazioni (
                destinazione, importo, fattura_origine_id, fattura_destinazione_id,
                cliente_soggetto_ruolo_id, emittente_soggetto_ruolo_id, motivo, meta
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [
                    destinazione, importo, int(fattura_origine_id),
                    fattura_destinazione_id, int(cliente_soggetto_ruolo_id),
                    int(emittente_soggetto_ruolo_id), motivo, meta,
                ],
            )
            row = cursor.fetchone()
        return int(row[0])

    # Scopo: Un atto di sistemazione, con i display field di chi lo legge.
    def get_sistemazione(self, sistemazione_id: int) -> dict[str, Any] | None:
        self._guard_canale_sistema("get_sistemazione")
        sql = """
            SELECT s.id, s.destinazione, s.stato, s.importo, s.motivo,
                   s.fattura_origine_id, fo.numero AS fattura_origine_numero,
                   fo.anno AS fattura_origine_anno, fo.serie AS fattura_origine_serie,
                   s.fattura_destinazione_id, fd.numero AS fattura_destinazione_numero,
                   fd.anno AS fattura_destinazione_anno,
                   fd.serie AS fattura_destinazione_serie,
                   s.cliente_soggetto_ruolo_id,
                   srd.ragione_sociale_completa AS cliente_ragione_sociale,
                   s.emittente_soggetto_ruolo_id,
                   s.contabile_id, s.fondo_source_id,
                   s.data_esecuzione, s.user_esecuzione,
                   s.data_insert, s.user_insert, s.meta
              FROM pagamenti.sistemazioni s
              LEFT JOIN vendite.fatture fo ON fo.id = s.fattura_origine_id
              LEFT JOIN vendite.fatture fd ON fd.id = s.fattura_destinazione_id
              LEFT JOIN anagrafiche.vw_soggetti_ruoli_dettaglio srd
                     ON srd.soggetto_ruolo_id = s.cliente_soggetto_ruolo_id
             WHERE s.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(sistemazione_id)])
            rows = rows_to_list(cursor)
        return self._shape(rows[0]) if rows else None

    # Scopo: Gli atti registrati su un documento.
    # ⭐ Sono PIU' DI UNO per natura: si puo' rimborsare una parte e riportare il
    #    resto, e l'elenco delle eccedenze conta apposta le bozze e le confermate
    #    separatamente.
    # ⭐ PAGINATA dal 2026-09-02 (decisione di Tid). Prima consegnava TUTTI gli
    #    atti in un colpo e il totale veniva da una query separata
    #    (`count_sistemazioni_fattura`, ora sparita): due valutazioni dello
    #    stesso predicato possono non concordare, una sola non puo'.
    # ⚠️ `limit=None` NON e' un ripiego per pigrizia: e' il modo in cui un
    #    chiamante dichiara di volere il dataset intero (l'export). Il totale
    #    resta quello vero perche' lo dice `COUNT(*) OVER ()`, che non guarda
    #    la finestra.
    def list_sistemazioni_fattura(
        self,
        fattura_id: int,
        *,
        limit: int | None = None,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        self._guard_canale_sistema("list_sistemazioni_fattura")
        # ⭐ `default_desc=True` — decisione di Tid del 2026-09-02: **l'ultimo
        #    atto deciso sta in cima**. Prima era `s.id ASC`, e finche' la lista
        #    non impaginava non si vedeva; da quando impagina, un atto appena
        #    registrato finiva nell'ULTIMA pagina e chi l'aveva appena creato non
        #    lo vedeva. ⚠️ E' anche il verso del registro gemello qui accanto
        #    (`list_movimenti`, «il piu' recente per primo, che e' come si legge
        #    un registro»): due elenchi della stessa cosa non devono leggersi al
        #    contrario l'uno dell'altro.
        # ⛔ Il tiebreak `s.id` NON e' estetica da quando la lista impagina:
        #    senza, a offset diversi PostgreSQL puo' consegnare due volte la
        #    stessa riga e mai un'altra. Lo scrive il BB, allineato alla
        #    direzione primaria — e lo OMETTE quando la colonna e' gia' `s.id`.
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=SISTEMAZIONI_SORT_COLUMNS,
            default="s.id",
            tiebreak="s.id",
            default_desc=True,
            colonne_desc=SISTEMAZIONI_SORT_COLONNE_DATA,
        )
        # ⛔ LIMIT/OFFSET solo se il chiamante impagina: una `LIMIT NULL` sarebbe
        #    legale in PostgreSQL ma legherebbe la query a un parametro in piu'
        #    senza che serva a nessuno.
        paginazione = "" if limit is None else "\n             LIMIT %s OFFSET %s"
        params: list[Any] = [int(fattura_id)]
        if limit is not None:
            params += [limit, offset]
        data_sql = f"""
            SELECT s.id, s.destinazione, s.stato, s.importo, s.motivo,
                   s.fattura_destinazione_id, s.contabile_id, s.fondo_source_id,
                   s.data_esecuzione, s.user_esecuzione, s.data_insert,
                   COUNT(*) OVER () AS total_count
             {_SISTEMAZIONI_FROM_WHERE}
             ORDER BY {ordinamento}{paginazione}
        """  # noqa: S608
        return fetch_paged_with_total(
            data_sql,
            params,
            # ⛔ Il conteggio di ripiego riusa lo STESSO `FROM`/`WHERE` della
            #    pagina, e non e' cerimonia: due predicati scritti a mano
            #    divergono, e il giorno in cui divergono il totale parla di un
            #    insieme diverso da quello che si sta guardando.
            fallback_count_sql=(
                f"SELECT count(*) {_SISTEMAZIONI_FROM_WHERE}"  # noqa: S608
            ),
            fallback_params=[int(fattura_id)],
            offset=offset,
        )

    # Scopo: Esegue l'atto — la decisione diventa un fatto.
    # ⭐ UNA SOLA `SELECT` sulla funzione madre: sceglie la strada (fondo,
    #    distinta negativa, distinta di compensazione) e ci mette sopra il
    #    denaro. ⛔ Nessuna delle tre macchine e' nuova, e nessuna la orchestra
    #    il backend.
    # ⚠️ `ente_incasso_id` si chiede QUI e non alla registrazione: «da quale
    #    conto esce il bonifico» e' una decisione del momento in cui si paga.
    def conferma_sistemazione(
        self, sistemazione_id: int, *, ente_incasso_id: int | None = None
    ) -> dict[str, Any] | None:
        sql = """
            SELECT contabile_id, fondo_source_id, esito
              FROM pagamenti.fn_conferma_sistemazione(%s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(sistemazione_id), ente_incasso_id])
            rows = rows_to_list(cursor)
        return rows[0] if rows else None

    # Scopo: Scarta l'atto, lasciandolo a registro con la sua ragione.
    # ⚠️ Il motivo si FONDE con quello gia' scritto: se l'atto ne aveva uno e la
    #    chiamata arriva vuota, resta quello che c'era.
    def annulla_sistemazione(
        self, sistemazione_id: int, *, motivo: str | None = None
    ) -> str | None:
        sql = "SELECT pagamenti.fn_annulla_sistemazione(%s, %s)"
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(sistemazione_id), motivo])
            row = cursor.fetchone()
        return row[0] if row else None

    # ══════════════════════════════════════════════════════════════
    #  La madre del posting
    # ══════════════════════════════════════════════════════════════

    # Scopo: Registra la distinta — trasforma in movimenti contabili le righe
    #        pronte a diventarlo, e chiude la distinta.
    # ⭐ UNA SOLA `SELECT`, quindi atomica per costruzione: l'atomicita' e'
    #    DENTRO la funzione. ⛔ Nessun `transaction.atomic()` attorno a piu'
    #    statement, nessun ciclo che posta le righe una a una.
    # ⚠️ `righe_attese` e `totale_atteso` sono la DICHIARAZIONE di chi conferma
    #    (quante righe pronte aveva davanti e per che totale): sono facoltativi
    #    ma LEGATI — o tutti e due o nessuno. Mezza dichiarazione non si puo'
    #    verificare, e accettarla significherebbe registrare senza controllo
    #    credendo di averlo fatto.
    # ⭐ Non solleva su «niente da registrare»: risponde `NULLA_DA_POSTARE` ed
    #    e' un esito, non un errore. Il backend lo passa senza interpretarlo.
    def posta_contabile(
        self,
        *,
        contabile_id: int,
        righe_attese: int | None = None,
        totale_atteso: Decimal | None = None,
    ) -> RicevutaPosting:
        sql = """
            SELECT movimenti_creati, righe_postate, righe_saltate,
                   totale_postato, esito
              FROM pagamenti.fn_posta_contabile(
                   p_contabile_id  := %s,
                   p_righe_attese  := %s,
                   p_totale_atteso := %s
              )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(contabile_id), righe_attese, totale_atteso])
            rows = rows_to_list(cursor)
        # La funzione ritorna sempre una riga: se non ci fosse, il contratto
        # sarebbe cambiato sotto e tacere sarebbe la cosa peggiore.
        ErrorManager.require(
            bool(rows),
            code=_E_CHIAMATA,
            message="La registrazione non ha prodotto nessuna ricevuta.",
            detail="pagamenti.fn_posta_contabile non ha restituito righe.",
            function_name=f"{_FN}.posta_contabile",
        )
        return rows[0]  # type: ignore[return-value]

    # Scopo: La CORREZIONE GUIDATA (Q-7) — apre una distinta nuova con le righe
    #        di segno opposto gia' dentro.
    # ⭐ UNA SOLA `SELECT` sulla madre, come le altre tre: la distinta e le sue N
    #    righe nascono atomiche per costruzione. ⛔ Nessun ciclo nel service —
    #    produrrebbe una distinta a meta' se qualcosa si rompe a meta' elenco,
    #    cioe' esattamente il documento che nessuno sa piu' leggere.
    # ⛔ E non e' uno «storno»: `STORNATA` e' stata ritirata dal catalogo il
    #    21/08, e rimetterne la parola riaprirebbe una porta che il lotto 2 ha
    #    chiuso. Si chiama correzione.
    # ⭐ Non solleva su «niente da correggere»: risponde `NULLA_DA_CORREGGERE`
    #    con `contabile_id` a NULL, ed e' un ESITO — il backend lo passa senza
    #    interpretarlo, come gia' fa con `NULLA_DA_POSTARE`.
    def crea_distinta_correzione(
        self,
        *,
        contabile_id: int,
        data_contabile: date | None = None,
        motivo: str | None = None,
    ) -> dict[str, Any]:
        self._guard_canale_sistema("crea_distinta_correzione")
        sql = """
            SELECT contabile_id, righe_create, righe_saltate, esito
              FROM pagamenti.fn_crea_distinta_correzione(
                       %s, COALESCE(%s::date, CURRENT_DATE), %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(contabile_id), data_contabile, motivo])
            rows = rows_to_list(cursor)
        # La funzione risponde SEMPRE una riga, anche sul nulla da correggere.
        # Se non lo facesse, il contratto sarebbe cambiato sotto — e tacere su
        # un gesto che ha creato un documento e' la cosa peggiore.
        ErrorManager.require(
            bool(rows),
            code=_E_CHIAMATA,
            message="La correzione non ha prodotto nessun esito.",
            detail="pagamenti.fn_crea_distinta_correzione non ha restituito righe.",
            function_name=f"{_FN}.crea_distinta_correzione",
        )
        return rows[0]

    # ══════════════════════════════════════════════════════════════
    #  Mapping di riga
    # ══════════════════════════════════════════════════════════════

    # Scopo: Normalizza le colonne jsonb lette da cursor RAW (il driver le
    #        restituisce come stringa fuori dall'ORM: senza questo, il primo
    #        `.get()` del consumatore esplode su una `str`).
    # Nota: una funzione sola per testata e riga — erano due copie identiche, e
    #       due copie della stessa normalizzazione divergono alla prima colonna
    #       jsonb che se ne aggiunge.
    @staticmethod
    def _shape(row: dict[str, Any]) -> dict[str, Any]:
        for col in _JSONB_COLS:
            if col in row:
                row[col] = jsonb_out(row[col])
        return row
