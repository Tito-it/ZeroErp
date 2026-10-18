# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per gestione soggetti (PF/PG/ENTE).
#        CRUD soggetti, contatti, indirizzi soggetto, ruoli.
#        Accesso DB-first via cursor e funzioni PostgreSQL.
# ------------------------------------------------------------

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
    coerce_jsonb_dict,
    pattern_contiene,
    RicercaFull,
    add_ricerca_full_condition,
    sql_order_clause,
    fetch_paged_with_total,
    row_to_dict,
    rows_to_list,
    soglia_ricerca,
)
from apps.core.db.lookup_repository import SQL_TIPI_SOGGETTO_DETTAGLIO
from apps.core.db.parameter_repository import ParameterRepository
from apps.core.db.sql_write_helpers import execute_dynamic_update, sql_set_clause

from django.db import connection


# Whitelist colonne ammesse per ORDER BY: chiave = campo_sorgente inviato dal
# client, valore = espressione SQL qualificata. Qualificata perche' la lista
# joina tre tabelle che hanno tutte i campi audit: un `data_insert` nudo in
# ORDER BY sarebbe ambiguo (soggetti / tipi_soggetto_dettaglio / tipi_soggetto).
# `tipo_descrizione` resta nudo: e' un alias di output della SELECT.
#
# L'identificativo fiscale a video e' SEMPRE `id_fiscale_univoco_cf_piva` (la
# colonna GENERATED che sceglie fra CF e P.IVA): il catalogo la espone con
# `codice = 'codice_fiscale'` ma `campo_sorgente = id_fiscale_univoco_cf_piva`,
# ed e' il secondo che il frontend invia come sortField. `codice_fiscale` e
# `partita_iva` NON stanno qui: nudi non arrivano mai dalla lista, e tenerli
# reintrodurrebbe la chiave logica che il presidio vieta.
_SOGGETTI_ORDER_COLS: dict[str, str] = {
    "codice": "s.codice",
    "ragione_sociale_completa": "s.ragione_sociale_completa",
    "id_fiscale_univoco_cf_piva": "s.id_fiscale_univoco_cf_piva",
    "tipo_descrizione": "tipo_descrizione",
    "data_insert": "s.data_insert",
}

# Cosa si PUO' cercare; cosa si cerca lo dice il catalogo (`add_ricerca_full_condition`).
# ⭐ L'id fiscale univoco e non CF e P.IVA separati (Tid, 2026-09-23): come
#    fornitori, clienti ed emittenti. Fino al 2026-09-24 la ricerca era scritta
#    a mano qui e cercava `codice_fiscale` e `partita_iva` nudi.
#    Nessun termine si perde: la colonna GENERATED porta `cf || ' ' || piva`
#    quando i due differiscono, altrimenti quello che c'e'.
_RICERCA_SOGGETTI = RicercaFull(
    "anagrafiche.soggetti", ("ragione_sociale_completa", "id_fiscale_univoco_cf_piva"),
)

# Scopo: clausola scope emittente sul ruolo CL (regola del 2: usata da
#        list_soggetti, get_soggetto_ruoli e search_ruoli_lookup). Un ruolo CL
#        e' visibile a un operatore scoped solo se il soggetto ha un cliente il
#        cui BA e' visibile per i suoi emittenti. Richiede alias `sr`
#        (soggetti_ruoli) e `tr` (tipi_ruoli) nel contesto chiamante.
#        2 parametri posizionali: emittente_ids, emittente_ids (NULL = bypass).
# ⛔ «BA visibile» lo decide `script.fn_check_ba_visible_for_emittenti`, come
#    gia' `billing_account_repository` e `istanze_utility_repository`. Fino
#    al 2026-09-13 la regola stava qui INLINE — «mapping specifico, altrimenti
#    default se il BA non ha mapping» — in TRE copie (questa e una ricopiata
#    dentro la jsonb_agg di list_soggetti): dal changeSet `20260913-01` (D13)
#    la regola del DB ha tre livelli (in sessione un BA senza legame e'
#    dell'operatore che sta agendo) e le copie sarebbero rimaste alla vecchia,
#    in silenzio. Una regola, un posto: brief-db-ba-riserva-emittente-operatore-d13 §6.2.
# ⚠️ Il `JOIN billing_account` RESTA anche se la fn riceve l'id: `clienti` e
#    `billing_account` hanno entrambe la RLS e i filtri si sommano (api.md
#    §Enforcement RLS) — togliere il JOIN toglierebbe un cancello in silenzio.
_RUOLO_CL_SCOPE_SQL = """(
                 %s::bigint[] IS NULL
                 OR COALESCE(tr.codice_interno, tr.codice) != 'CL'
                 OR EXISTS (
                     SELECT 1
                       FROM anagrafiche.clienti cl
                       JOIN anagrafiche.billing_account ba
                         ON ba.id = cl.billing_account_id
                      WHERE cl.soggetto_ruolo_id = sr.id
                        AND script.fn_check_ba_visible_for_emittenti(ba.id, %s::bigint[])
                 )
               )"""

# Scopo: le forniture del ruolo per le righe lookup contesto pratica (search +
#        restore by-id ne condividono la proiezione): conteggio dei billing
#        account del ruolo + il BA «unico» derivabile (id/codice valorizzati
#        SOLO se il conteggio e' 1 — il form non chiede niente). Il BA e' il
#        cliente a grana fine di cui la pratica parla (D-9 di
#        brief-db-istanza-nasce-col-ba): un ruolo CLIENTE ne ha uno per ogni
#        coppia (istanza, utility).
#        Perimetro per riga:
#        - riga con ruolo: i BA di quel ruolo (`ba.soggetto_ruolo_id`), con o
#          senza la riga cliente — coerente col filtro `soggetto_ruolo_id` del
#          lookup istanze. Per i ruoli non-CL il conteggio e' 0;
#        - riga "senza ruolo" ({sr_ref} NULL): 0. Un BA e' sempre di un ruolo e
#          la pratica lo accetta solo dal suo ruolo (regola 5,
#          E_PRATICHE_BA_NON_COERENTE); e un soggetto senza ruoli non ha
#          istanze (D-3: il ruolo CLIENTE nasce con la prima).
#        ⚠️ Fino al 2026-10-08 si contavano le ISTANZE legate al ruolo via
#        `clienti`: un ruolo col BA e senza la riga cliente (la fase del
#        preventivo) risultava senza forniture, e un'istanza con due utility
#        contava uno.
#        `{sr_ref}` = espressione del contesto chiamante ("sr.id",
#        "m.soggetto_ruolo_id", "NULL::bigint"). Da usare come
#        `LEFT JOIN LATERAL {tpl} forn ON true` + `_FORNITURE_SELECT`.
_FORNITURE_LATERAL_TPL = """(
                   SELECT COUNT(*)::int AS n_billing_account,
                          MAX(ba.id) AS _unico_id,
                          MAX(ba.codice) AS _unico_codice
                     FROM anagrafiche.billing_account ba
                    WHERE ba.soggetto_ruolo_id = {sr_ref}
               )"""

_FORNITURE_SELECT = """forn.n_billing_account,
       CASE WHEN forn.n_billing_account = 1 THEN forn._unico_id END AS billing_account_unico_id,
       CASE WHEN forn.n_billing_account = 1 THEN forn._unico_codice END AS billing_account_unico_codice"""

# ⛔ `MIN_SEARCH_LENGTH_SOGGETTI` non c'e' piu' (2026-09-26, brief-db-be-fe-
#    ricerca-soglia-per-lista §6 b, decisione di Tid): la soglia del resolver
#    soggetti e' quella del catalogo della lista che interroga — vedi
#    `get_config_resolver`.


# Whitelist delle colonne SCRIVIBILI dagli update (BB `sql_write_helpers`,
# politica RIGIDA dal 2026-09-26: una colonna fuori lista e' `RuntimeError`).
# ⚠️ Sono il perimetro del REPOSITORY, non il contratto dell'operatore: le
#    chiavi del payload le valida prima `SoggettiService` (400), che parte da
#    qui e puo' restringere.
SOGGETTO_UPDATE_COLS: frozenset[str] = frozenset({
    "cognome", "nome", "ragione_sociale", "codice_fiscale",
    "partita_iva", "sesso", "data_nascita", "comune_id",
    # I0/D8 (2026-08-29): regime fiscale della controparte.
    "split_payment", "cliente_pa",
    # La natura di dettaglio (2026-10-10, brief-db-dati-fiscali-e-societari-del-
    # soggetto §8.3): il drawer la offriva in modifica (fra i
    # `tipi_modificabili_ids`), ma fino a quel giorno la chiave non era nel
    # contratto e il cambio non arrivava mai al DB. Cosa la natura nuova
    # ammette (flag PA/split, forma giuridica, titoli IVA) lo giudicano i guard.
    "tipo_soggetto_dettaglio_id",
})
# Alias frontend → colonna DB accettati da `update_soggetto`.
SOGGETTO_UPDATE_ALIAS: dict[str, str] = {"comune_nascita_id": "comune_id"}
CONTATTO_UPDATE_COLS: frozenset[str] = frozenset({
    "nominativo", "email", "telefono", "cellulare", "pec",
    "tipo_contatto_id", "unita_organizzativa_id", "note",
})
INDIRIZZO_RUOLO_UPDATE_COLS: frozenset[str] = frozenset({
    "tipo_indirizzo_id", "istanza_utility_id", "indirizzo_dettaglio_id",
    "indirizzo_libero", "stato_id", "comune_id", "codice_postale_id",
    "administrative_area", "locality", "sublocality", "postal_code",
})


# Le colonne del contatto appena creato che il repository restituisce: le
# stesse della RETURNING che c'era prima della madre (2026-10-18).
_CONTATTO_CREATO_COLS: tuple[str, ...] = (
    "id", "nominativo", "email", "telefono", "cellulare", "pec",
    "tipo_contatto_id", "unita_organizzativa_id", "note",
    "soggetto_ruolo_id", "istanza_utility_id",
)


class SoggettiRepository:
    """Accesso DB per soggetti, contatti, indirizzi soggetto, ruoli."""

    # =================================================================
    # Lista e dettaglio soggetti
    # =================================================================

    # Scopo: Lista paginata soggetti con la ricerca libera del catalogo
    #        (`_RICERCA_SOGGETTI`) e filtro per tipo_soggetto_dettaglio_id.
    def list_soggetti(
        self, *, search: str | None = None,
        tipo_soggetto_dettaglio_id: int | None = None,
        emittente_ids: list[int] | None = None,
        limit: int = DEFAULT_LIMIT, offset: int = 0,
        order_by: str = "ragione_sociale_completa", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_SOGGETTI_ORDER_COLS,
            default=_SOGGETTI_ORDER_COLS["ragione_sociale_completa"],
            tiebreak="s.id",
        )
        # ⚠️ I due parametri dello scope dei ruoli stanno nella SELECT (la
        #    subquery dei badge), quindi PRIMA di quelli del WHERE.
        params: list[Any] = [emittente_ids, emittente_ids]
        conditions: list[str] = ["(%s::bigint IS NULL OR s.tipo_soggetto_dettaglio_id = %s)"]
        params.extend([tipo_soggetto_dettaglio_id, tipo_soggetto_dettaglio_id])
        # ⚠️ Sotto la soglia della lista (catalogo) il termine non filtra: fino al
        #    2026-09-24 la ricerca scritta a mano filtrava da un carattere.
        add_ricerca_full_condition(conditions, params, search, _RICERCA_SOGGETTI, alias="s")
        sql = f"""
            SELECT s.id, s.codice, s.ragione_sociale_completa, s.codice_fiscale,
                   s.partita_iva, s.id_fiscale_univoco_cf_piva,
                   s.cognome, s.nome, s.ragione_sociale,
                   tsd.descrizione AS tipo_descrizione,
                   tsd.id AS tipo_soggetto_dettaglio_id,
                   ts.natura_soggetto,
                   (SELECT COALESCE(jsonb_agg(jsonb_build_object(
                       'soggetto_ruolo_id', sr.id,
                       'codice', COALESCE(tr.codice_interno, tr.codice),
                       'descrizione', tr.descrizione
                   ) ORDER BY tr.descrizione), '[]'::jsonb)
                    FROM anagrafiche.soggetti_ruoli sr
                    JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
                   WHERE sr.soggetto_id = s.id
                     AND {_RUOLO_CL_SCOPE_SQL}
                   ) AS ruoli,
                   COUNT(*) OVER () AS total_count
              FROM anagrafiche.soggetti s
              JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id
              JOIN config.tipi_soggetto ts ON ts.id = tsd.tipo_soggetto_id
             WHERE {" AND ".join(conditions)}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params.extend([limit, offset])
        # ⚠️ Nessun conteggio di ripiego scritto a parte: i parametri dello scope
        #    stanno nella SELECT (prima di quelli del WHERE), e un conteggio
        #    senza SELECT dovrebbe sapere quanti sono — un `params[2:]` che si
        #    disallinea in silenzio al primo parametro in piu' dello scope. Il
        #    BB rilegge la stessa query con `LIMIT 1 OFFSET 0`.
        results, total_count = fetch_paged_with_total(sql, params, offset=offset)
        # Normalizza ruoli (jsonb_agg): psycopg in alcune configurazioni
        # ritorna jsonb come stringa anziche' lista. Garantiamo sempre list.
        for r in results:
            ruoli = r.get("ruoli")
            if isinstance(ruoli, str):
                try:
                    r["ruoli"] = json.loads(ruoli)
                except (ValueError, TypeError):
                    r["ruoli"] = []
            elif ruoli is None:
                r["ruoli"] = []
        return results, total_count

    # Scopo: Recupera il codice catastale (Belfiore) di un comune da extra_country.
    def get_codice_catastale(self, comune_id: int) -> str | None:
        sql = """
            SELECT extra_country->>'codice_catastale'
              FROM config.comuni
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [comune_id])
            row = cursor.fetchone()
            return str(row[0]) if row and row[0] else None

    # Scopo: Verifica esistenza soggetto (query leggera, SELECT 1).
    def exists_soggetto(self, soggetto_id: str) -> bool:
        sql = "SELECT 1 FROM anagrafiche.soggetti WHERE id = %s::uuid"
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            return cursor.fetchone() is not None

    # Scopo: Risolve la descrizione di un tipo_soggetto_dettaglio per id
    #        (DEF-1, header filtri leggibili nell'export). Lookup
    #        opportunistico senza cache: 1-2 chiamate per richiesta export.
    def get_tipo_soggetto_dettaglio_descrizione(self, tipo_id: int) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT descrizione FROM config.tipi_soggetto_dettaglio WHERE id = %s",
                [tipo_id],
            )
            row = cursor.fetchone()
            return row[0] if row else None

    # Scopo: Risolve la natura (l'enum `config.natura_soggetto_enum`: PF/PG/ENTE)
    #        dal tipo_soggetto_dettaglio_id. Stesso significato di
    #        `natura_soggetto` in lista, dettaglio e lookup (BB
    #        `SQL_TIPI_SOGGETTO_DETTAGLIO`).
    def get_natura_by_tipo_id(self, tipo_id: int) -> str | None:
        sql = """
            SELECT ts.natura_soggetto::text
              FROM config.tipi_soggetto_dettaglio tsd
              JOIN config.tipi_soggetto ts ON ts.id = tsd.tipo_soggetto_id
             WHERE tsd.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo_id])
            row = cursor.fetchone()
            return str(row[0]) if row and row[0] else None

    # Scopo: Dettaglio completo soggetto con tipo, natura, comune nascita,
    # e tipi_modificabili_ids = id dei dettagli ammessi in edit (Fase 6 B3:
    # stessa natura del soggetto corrente). Il frontend filtra con quello
    # invece di ricostruire la regola natura_soggetto.
    def get_soggetto(self, soggetto_id: str) -> dict[str, Any] | None:
        sql = """
            SELECT s.id, s.ragione_sociale_completa, s.codice_fiscale,
                   s.partita_iva, s.cognome, s.nome, s.ragione_sociale,
                   -- Regime fiscale della controparte (I0/D8, 2026-08-29): saliti
                   -- da `anagrafiche.clienti`, che e' una riga PER FORNITURA e
                   -- ammetteva tre valori diversi per la stessa partita IVA. Un
                   -- ente E' o NON E' una PA: non lo e' per il gas e non per
                   -- l'acqua. ⚠️ NON sono un codice IVA e non entrano nel
                   -- risolutore (D4): non cambiano l'aliquota, cambiano CHI VERSA
                   -- l'imposta — in fattura elettronica sono l'EsigibilitaIVA.
                   s.split_payment, s.cliente_pa,
                   s.sesso, s.data_nascita::text, s.comune_id AS comune_nascita_id,
                   c.descrizione AS comune_nascita_descrizione,
                   p.sigla AS comune_nascita_provincia_sigla,
                   tsd.id AS tipo_soggetto_dettaglio_id,
                   tsd.descrizione AS tipo_descrizione,
                   ts.natura_soggetto,
                   -- Tipi dettaglio ammessi in edit per questo soggetto:
                   -- stessa natura del corrente. Sostituisce il filtro
                   -- frontend (SoggettoForm.tipiSoggettoFiltrati).
                   (SELECT COALESCE(array_agg(tsd2.id ORDER BY tsd2.codice_interno), '{}')
                      FROM config.tipi_soggetto_dettaglio tsd2
                     WHERE tsd2.tipo_soggetto_id = tsd.tipo_soggetto_id
                   ) AS tipi_modificabili_ids
              FROM anagrafiche.soggetti s
              JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id
              JOIN config.tipi_soggetto ts ON ts.id = tsd.tipo_soggetto_id
              LEFT JOIN config.comuni c ON c.id = s.comune_id
              LEFT JOIN config.province p ON p.id = c.provincia_id
             WHERE s.id = %s::uuid
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            return row_to_dict(cursor)

    # =================================================================
    # Creazione soggetti
    # =================================================================

    # Scopo: Crea soggetto PF chiamando la funzione DB building block.
    #        Obiettivo: INSERT soggetto + contatto default, tutto in funzione PG.
    # ⛔ `sesso` e `tipo_soggetto_dettaglio_id` senza default, come a DB: la
    #    natura e il sesso non si inventano (brief-db-sesso-senza-default D4).
    #    `sesso=None` e' un valore legittimo (DI, OPTIONAL): se la natura lo
    #    pretende, rifiuta il guard `trgfn_soggetti_guard_sesso_policy`.
    def crea_soggetto_pf(
        self, *, cognome: str, nome: str, codice_fiscale: str, email: str,
        sesso: str | None, tipo_soggetto_dettaglio_id: int,
        data_nascita: str | None = None,
        # None = il default di `config.parameters`, risolto dalla funzione DB.
        stato_iso2: str | None = None,
        comune_nascita_id: int | None = None,
        tipo_contatto_id: int | None = None,
        partita_iva: str | None = None,
    ) -> str:
        sql = """
            SELECT anagrafiche.fn_crea_soggetto_pf(
                p_cognome           := %s,
                p_nome              := %s,
                p_codice_fiscale    := %s,
                p_email             := %s,
                p_data_nascita      := %s::date,
                p_sesso             := %s,
                p_stato_iso2        := %s,
                p_comune_nascita_id := %s,
                p_tipo_contatto_id  := %s,
                p_tipo_soggetto_dettaglio_id := %s,
                p_partita_iva       := %s
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                cognome, nome, codice_fiscale, email,
                data_nascita, sesso, stato_iso2, comune_nascita_id, tipo_contatto_id,
                tipo_soggetto_dettaglio_id, partita_iva,
            ])
            row = cursor.fetchone()
            assert row is not None
            return str(row[0])

    # Scopo: Crea soggetto PG chiamando la funzione DB building block.
    #        Obiettivo: INSERT soggetto + contatto default + dati societari
    #        (se policy REQUIRED o dati forniti). Non crea indirizzi ne' ruoli.
    def crea_soggetto_pg(
        self, *, ragione_sociale: str, tipo_soggetto_dettaglio_id: int,
        email: str, codice_fiscale: str | None = None,
        partita_iva: str | None = None, stato_iso2: str | None = None,
        forma_giuridica_id: int | None = None,
        id_prov_iscri_rea: int | None = None,
        iscrizione_rea: str | None = None,
        capitale_sociale: float | None = None,
        # None = i default di `config.parameters` (fn_crea_soggetto_pg): fino al
        # 2026-10-09 qui c'erano "IT"/"SU"/"LN" cablati, una copia del dato.
        socio_unico: str | None = None, liquidazione: str | None = None,
        destinatario_fe: str | None = None,
        pec_fatturazione: str | None = None,
        codice_sdi: str | None = None,
        tipo_contatto_id: int | None = None,
    ) -> str:
        sql = """
            SELECT anagrafiche.fn_crea_soggetto_pg(
                p_ragione_sociale            := %s,
                p_tipo_soggetto_dettaglio_id := %s,
                p_email                      := %s,
                p_codice_fiscale             := %s,
                p_partita_iva                := %s,
                p_stato_iso2                 := %s,
                p_forma_giuridica_id         := %s,
                p_id_prov_iscri_rea          := %s,
                p_iscrizione_rea             := %s,
                p_capitale_sociale           := %s,
                p_socio_unico                := %s::anagrafiche.socio_unico_enum,
                p_liquidazione               := %s::anagrafiche.liquidazione_enum,
                p_destinatario_fe            := %s,
                p_pec_fatturazione           := %s,
                p_codice_sdi                 := %s,
                p_tipo_contatto_id           := %s
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                ragione_sociale, tipo_soggetto_dettaglio_id, email,
                codice_fiscale, partita_iva, stato_iso2,
                forma_giuridica_id, id_prov_iscri_rea, iscrizione_rea,
                capitale_sociale, socio_unico, liquidazione,
                destinatario_fe, pec_fatturazione, codice_sdi,
                tipo_contatto_id,
            ])
            row = cursor.fetchone()
            assert row is not None
            return str(row[0])

    # =================================================================
    # Aggiornamento soggetti
    # =================================================================

    # Scopo: Aggiorna campi modificabili di un soggetto.
    # Normalizza stringhe vuote a NULL per evitare conflitti con trigger
    # che controllano IS NOT NULL (es. partita_iva, codice_fiscale).
    # ⛔ Dal 2026-09-26 la scrittura passa dal BB `execute_dynamic_update`, con
    #    whitelist RIGIDA: una chiave fuori `SOGGETTO_UPDATE_COLS` (dopo l'alias)
    #    e' `RuntimeError`, non piu' uno scarto silenzioso. Il contratto
    #    dell'operatore lo valida PRIMA il service (400 `E_ANAG_VALIDAZIONE`).
    def update_soggetto(self, soggetto_id: str, data: dict[str, Any]) -> bool:
        # Campi dove stringa vuota deve diventare NULL.
        # ⚠️ `split_payment`/`cliente_pa` restano FUORI: sono `character(1)`
        #    NOT NULL con CHECK ('S','N'), quindi normalizzare a NULL
        #    trasformerebbe un valore sbagliato in una violazione di NOT NULL —
        #    un errore piu' oscuro di quello che gia' c'e'. Il valore lo valida
        #    il service prima di arrivare qui.
        # `sesso` (2026-10-09): il vuoto e' «non indicato», cioe' NULL — per la
        #    DI e' ammesso; `''` lo rifiuterebbe il CHECK `chk_soggetti_sesso`.
        _NULLABLE = {"codice_fiscale", "partita_iva", "sesso", "data_nascita", "comune_id"}
        # Copia con l'alias frontend → colonna DB applicato: `data` e' spesso
        # `request.data`, e non si muta l'input del chiamante.
        mapped = {SOGGETTO_UPDATE_ALIAS.get(k, k): v for k, v in data.items()}
        # Normalizza stringhe vuote a None per campi nullable
        for k in _NULLABLE:
            val = mapped.get(k)
            if isinstance(val, str) and not val.strip():
                mapped[k] = None
        if not mapped:
            return False
        # `id` e' uuid: il cast lo fa PostgreSQL sul literal del parametro.
        return execute_dynamic_update(
            "anagrafiche.soggetti", soggetto_id, mapped,  # type: ignore[arg-type]
            allowed=SOGGETTO_UPDATE_COLS,
        )

    # Scopo: Crea o aggiorna i dati societari del soggetto col verbo DB
    #        `anagrafiche.fn_scrivi_dati_societari` (STATO INTERO: un NULL scrive
    #        NULL dove la colonna lo ammette; socio unico e liquidazione NULL
    #        valgono il default di `config.parameters`).
    # Risultato: l'id della riga di `anagrafiche.dati_societari`.
    # ⛔ Mai un UPDATE diretto della tabella: dal `20261011-04` l'applicazione
    #    non ha piu' i privilegi di scrittura, e il verbo e' la porta
    #    (brief-db-dati-fiscali-e-societari-del-soggetto, B-5). Le regole
    #    (forma per natura, REA e capitale per forma, canale FE) stanno nei
    #    trigger della tabella e arrivano come errori di dominio col campo.
    def scrivi_dati_societari(
        self, soggetto_id: str, *,
        forma_giuridica_id: int | None,
        id_prov_iscri_rea: int | None,
        iscrizione_rea: str | None,
        capitale_sociale: Decimal | None,
        socio_unico: str | None,
        liquidazione: str | None,
        destinatario_fe: str | None,
        pec_fatturazione: str | None,
        codice_sdi: str | None,
        data_costituzione: date | None,
    ) -> int:
        sql = """
            SELECT anagrafiche.fn_scrivi_dati_societari(
                p_soggetto_id        := %s::uuid,
                p_forma_giuridica_id := %s,
                p_id_prov_iscri_rea  := %s,
                p_iscrizione_rea     := %s,
                p_capitale_sociale   := %s,
                p_socio_unico        := %s::anagrafiche.socio_unico_enum,
                p_liquidazione       := %s::anagrafiche.liquidazione_enum,
                p_destinatario_fe    := %s,
                p_pec_fatturazione   := %s,
                p_codice_sdi         := %s,
                p_data_costituzione  := %s::date
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                soggetto_id, forma_giuridica_id, id_prov_iscri_rea, iscrizione_rea,
                capitale_sociale, socio_unico, liquidazione,
                destinatario_fe, pec_fatturazione, codice_sdi, data_costituzione,
            ])
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # =================================================================
    # Contatti
    # =================================================================

    # Scopo: Lista contatti di un soggetto.
    def get_soggetto_contatti(self, soggetto_id: str) -> list[dict[str, Any]]:
        sql = """
            SELECT c.id, c.nominativo, c.email, c.telefono, c.cellulare,
                   c.pec, c.note, c.tipo_contatto_id,
                   tc.descrizione AS tipo_contatto_descrizione,
                   c.unita_organizzativa_id
              FROM anagrafiche.contatti c
              LEFT JOIN config.tipi_contatti tc ON tc.id = c.tipo_contatto_id
             WHERE c.soggetto_id = %s::uuid
             ORDER BY c.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            return rows_to_list(cursor)

    # Scopo: Crea contatto per un soggetto. Se soggetto_ruolo_id fornito, il contatto
    #        e' specifico del ruolo; altrimenti e' a livello soggetto (fallback).
    # ⭐ Dal 2026-10-18 (2b-2, lotto 3) scrive la madre del DB
    #    `anagrafiche.fn_crea_contatto`: nominativo e tipo obbligatori
    #    (`E_CONTATTO_INCOMPLETO`, col campo), le chiavi assenti al DEFAULT.
    #    Le unicita' escono dai vincoli, tradotti per nome dal chiamante.
    #    Ritorna le stesse colonne di prima, non la riga intera.
    def crea_contatto(
        self, soggetto_id: str, *, nominativo: str, email: str | None = None,
        telefono: str | None = None, cellulare: str | None = None,
        pec: str | None = None, tipo_contatto_id: int | None = None,
        unita_organizzativa_id: int | None = None, note: str | None = None,
        soggetto_ruolo_id: int | None = None, istanza_utility_id: int | None = None,
    ) -> dict[str, Any]:
        campi = {
            k: v for k, v in {
                "nominativo": nominativo, "email": email, "telefono": telefono,
                "cellulare": cellulare, "pec": pec, "tipo_contatto_id": tipo_contatto_id,
                "unita_organizzativa_id": unita_organizzativa_id, "note": note,
                "istanza_utility_id": istanza_utility_id,
            }.items() if v is not None
        }
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT anagrafiche.fn_crea_contatto(%s::uuid, %s::bigint, %s::jsonb)",
                [soggetto_id, soggetto_ruolo_id, json.dumps(campi)],
            )
            row = cursor.fetchone()
        assert row is not None
        riga = coerce_jsonb_dict(row[0])
        return {k: riga.get(k) for k in _CONTATTO_CREATO_COLS}

    # Scopo: Aggiorna un contatto esistente con verifica ownership soggetto o ruolo.
    #        SET composto dal BB `sql_set_clause` (whitelist RIGIDA
    #        `CONTATTO_UPDATE_COLS`, dal 2026-09-26): il WHERE di ownership lo
    #        scrive il metodo, per questo non e' `execute_dynamic_update`.
    def update_contatto(self, contatto_id: int, data: dict[str, Any],
                        soggetto_id: str | None = None,
                        soggetto_ruolo_id: int | None = None) -> bool:
        if not data:
            return False
        set_clause, values = sql_set_clause(data, allowed=CONTATTO_UPDATE_COLS)
        values.append(contatto_id)
        where = "WHERE id = %s"
        if soggetto_id is not None:
            where += " AND soggetto_id = %s::uuid"
            values.append(soggetto_id)
        if soggetto_ruolo_id is not None:
            where += " AND soggetto_ruolo_id = %s"
            values.append(soggetto_ruolo_id)
        sql = f"UPDATE anagrafiche.contatti SET {set_clause} {where}"  # noqa: S608 — SET da sql_set_clause (colonne in whitelist), WHERE letterale del metodo, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0

    # Scopo: Elimina contatto con ownership check.
    def delete_contatto(self, contatto_id: int, soggetto_id: str) -> bool:
        sql = """
            DELETE FROM anagrafiche.contatti
             WHERE id = %s AND soggetto_id = %s::uuid
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [contatto_id, soggetto_id])
            return cursor.rowcount > 0

    # =================================================================
    # Indirizzi soggetto
    # =================================================================

    # Scopo: Lista indirizzi layer soggetto con dettaglio geografico per UI.
    def get_soggetto_indirizzi(self, soggetto_id: str) -> list[dict[str, Any]]:
        sql = """
            SELECT isog.id, isog.tipo_indirizzo_id,
                   ti.descrizione AS tipo_indirizzo_descrizione,
                   ti.codice_interno AS tipo_indirizzo_codice,
                   isog.indirizzo_dettaglio_id,
                   isog.indirizzo_libero,
                   isog.stato_id, isog.comune_id,
                   COALESCE(isog.indirizzo_libero,
                            idet.indirizzo_normalizzato) AS indirizzo_display,
                   idet.stradario_id,
                   idet.civico,
                   idet.estensione_civico,
                   idet.palazzina,
                   idet.scala,
                   idet.piano,
                   idet.interno,
                   idet.via_norm AS stradario_display,
                   s.comune_id AS det_comune_id,
                   c.descrizione AS descrizione_comune
              FROM anagrafiche.indirizzi_soggetti isog
              JOIN config.tipi_indirizzi ti ON ti.id = isog.tipo_indirizzo_id
              LEFT JOIN anagrafiche.indirizzi_dettaglio idet
                ON idet.id = isog.indirizzo_dettaglio_id
              LEFT JOIN config.stradario s
                ON s.id = idet.stradario_id
              LEFT JOIN config.comuni c
                ON c.id = s.comune_id
             WHERE isog.soggetto_id = %s::uuid
             ORDER BY ti.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            return rows_to_list(cursor)

    # Scopo: Crea un indirizzo del soggetto con la madre del DB
    #        `anagrafiche.fn_crea_indirizzo_soggetto(soggetto, indirizzo jsonb)`
    #        (firma dal 2026-10-18: la posizionale non c'e' piu'). Ritorna l'id
    #        della riga di `indirizzi_soggetti`.
    def crea_indirizzo_soggetto(self, soggetto_id: str, indirizzo: dict[str, Any]) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT anagrafiche.fn_crea_indirizzo_soggetto(%s::uuid, %s::jsonb)",
                [soggetto_id, json.dumps(indirizzo, default=str)],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # Scopo: Elimina un'associazione indirizzo-soggetto per id.
    def delete_indirizzo_soggetto(self, indirizzo_soggetto_id: int, soggetto_id: str) -> bool:
        sql = """
            DELETE FROM anagrafiche.indirizzi_soggetti
             WHERE id = %s AND soggetto_id = %s::uuid
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [indirizzo_soggetto_id, soggetto_id])
            return cursor.rowcount > 0

    # =================================================================
    # Indirizzi ruolo (anagrafiche.indirizzi — con istanza_utility_id)
    # =================================================================

    # Scopo: Gli indirizzi di un ruolo dalla madre del DB
    #        `anagrafiche.fn_crea_indirizzi_ruolo` (auto-clone dei tipi
    #        obbligatori, salto dei tipi presenti, via risolta da
    #        `fn_create_indirizzo`). Ritorna quanti ne ha scritti.
    def crea_indirizzi_ruolo(self, soggetto_ruolo_id: int, indirizzi: list[dict[str, Any]]) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT anagrafiche.fn_crea_indirizzi_ruolo(%s::bigint, %s::jsonb)",
                [soggetto_ruolo_id, json.dumps(indirizzi, default=str)],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # Campi nullable dell'update indirizzi ruolo: stringa vuota -> NULL.
    _IND_RUOLO_NULLABLE = {
        "istanza_utility_id", "indirizzo_dettaglio_id", "indirizzo_libero",
        "stato_id", "comune_id", "codice_postale_id",
        "administrative_area", "locality", "sublocality", "postal_code",
    }

    # Scopo: Crea indirizzo a livello ruolo.
    #        Supporta modalita' normalizzata (indirizzo_dettaglio_id)
    #        e libera (indirizzo_libero + stato_id).
    #        Il trigger guard valida tipo_indirizzo_id vs matrice ammessi.
    def crea_indirizzo_ruolo(
        self, soggetto_ruolo_id: int, *,
        tipo_indirizzo_id: int,
        istanza_utility_id: int | None = None,
        indirizzo_dettaglio_id: int | None = None,
        indirizzo_libero: str | None = None,
        stato_id: int | None = None,
        comune_id: int | None = None,
        codice_postale_id: int | None = None,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO anagrafiche.indirizzi
                (soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id,
                 indirizzo_dettaglio_id, indirizzo_libero,
                 stato_id, comune_id, codice_postale_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id,
                      indirizzo_dettaglio_id, indirizzo_libero,
                      stato_id, comune_id, codice_postale_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id,
                indirizzo_dettaglio_id, indirizzo_libero,
                stato_id, comune_id, codice_postale_id,
            ])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna indirizzo ruolo con ownership check su soggetto_ruolo_id.
    #        SET dal BB `sql_set_clause` (whitelist RIGIDA
    #        `INDIRIZZO_RUOLO_UPDATE_COLS`, dal 2026-09-26); il WHERE di
    #        ownership lo scrive il metodo.
    def update_indirizzo_ruolo(
        self, indirizzo_id: int, soggetto_ruolo_id: int,
        data: dict[str, Any],
    ) -> bool:
        # Copia: `data` e' spesso `request.data`, non si muta l'input.
        valori = dict(data)
        # Normalizza stringhe vuote a None per campi nullable
        for k in self._IND_RUOLO_NULLABLE:
            val = valori.get(k)
            if isinstance(val, str) and not val.strip():
                valori[k] = None
        if not valori:
            return False
        set_clause, values = sql_set_clause(valori, allowed=INDIRIZZO_RUOLO_UPDATE_COLS)
        values.extend([indirizzo_id, soggetto_ruolo_id])
        sql = (
            f"UPDATE anagrafiche.indirizzi SET {set_clause} "  # noqa: S608 — SET da sql_set_clause (colonne in whitelist), WHERE letterale, valori come parametri
            "WHERE id = %s AND soggetto_ruolo_id = %s"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            return cursor.rowcount > 0

    # Scopo: Elimina indirizzo ruolo con ownership check su soggetto_ruolo_id.
    def delete_indirizzo_ruolo(
        self, indirizzo_id: int, soggetto_ruolo_id: int,
    ) -> bool:
        sql = """
            DELETE FROM anagrafiche.indirizzi
             WHERE id = %s AND soggetto_ruolo_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [indirizzo_id, soggetto_ruolo_id])
            return cursor.rowcount > 0

    # Scopo: Risolve tipo_indirizzo codice → id. Usa COALESCE(codice_interno, codice) per match.
    def resolve_tipo_indirizzo_id(self, codice: str) -> int | None:
        sql = "SELECT id FROM config.tipi_indirizzi WHERE COALESCE(codice_interno, codice) = %s LIMIT 1"
        with connection.cursor() as cursor:
            cursor.execute(sql, [codice])
            row = cursor.fetchone()
            return row[0] if row else None

    # =================================================================
    # Ruoli
    # =================================================================

    # Scopo: Lista ruoli assegnati a un soggetto, con filtro scope emittente
    #        sul ruolo CL (stessa logica a 3 livelli di list_soggetti).
    def get_soggetto_ruoli(
        self, soggetto_id: str, emittente_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        sql = f"""
            SELECT sr.id, sr.tipo_ruolo_id,
                   COALESCE(tr.codice_interno, tr.codice) AS ruolo_codice,
                   tr.descrizione AS ruolo_descrizione
              FROM anagrafiche.soggetti_ruoli sr
              JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
             WHERE sr.soggetto_id = %s::uuid
               AND {_RUOLO_CL_SCOPE_SQL}
             ORDER BY tr.descrizione
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id, emittente_ids, emittente_ids])
            return rows_to_list(cursor)

    # Scopo: Lookup ricco per la selezione contesto pratica — una riga per
    #        soggetto_ruolo + una riga "senza ruolo" per i soggetti privi di
    #        qualunque ruolo (per esempio appena censiti: non hanno istanze,
    #        il ruolo CLIENTE nasce con la prima — D-3 di
    #        brief-db-istanza-nasce-col-ba). `n_billing_account` permette al FE
    #        di decidere se proporre la scelta della fornitura.
    def search_ruoli_lookup(
        self,
        *,
        q: str,
        tipo_ruolo: str | None,
        emittente_ids: list[int] | None,
        limit: int,
        con_ruolo: bool = False,
    ) -> tuple[list[dict[str, Any]], int]:
        search_pattern = pattern_contiene(q)
        # Filtro tipo_ruolo: esclude per definizione le righe "senza ruolo"
        # (secondo ramo della UNION gated su tipo_ruolo IS NULL).
        # `con_ruolo`: le esclude senza restringere il tipo, per i campi che
        # salvano un soggetto_ruolo_id (es. destinatario del DDT): li' una riga
        # "senza ruolo" non ha niente da salvare.
        cte = f"""
            WITH matches AS (
                SELECT s.id AS soggetto_id,
                       sr.id AS soggetto_ruolo_id,
                       COALESCE(tr.codice_interno, tr.codice) AS ruolo_codice,
                       tr.descrizione AS ruolo_descrizione,
                       s.ragione_sociale_completa,
                       s.id_fiscale_univoco_cf_piva AS id_fiscale,
                       s.codice AS soggetto_codice
                  FROM anagrafiche.soggetti s
                  JOIN anagrafiche.soggetti_ruoli sr ON sr.soggetto_id = s.id
                  JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
                 WHERE (s.ragione_sociale_completa ILIKE %s
                        OR s.codice_fiscale ILIKE %s
                        OR s.partita_iva ILIKE %s)
                   AND (%s::text IS NULL
                        OR COALESCE(tr.codice_interno, tr.codice) = %s::text)
                   AND {_RUOLO_CL_SCOPE_SQL}
                UNION ALL
                SELECT s.id, NULL::bigint, NULL::varchar, NULL::varchar,
                       s.ragione_sociale_completa,
                       s.id_fiscale_univoco_cf_piva,
                       s.codice
                  FROM anagrafiche.soggetti s
                 WHERE (s.ragione_sociale_completa ILIKE %s
                        OR s.codice_fiscale ILIKE %s
                        OR s.partita_iva ILIKE %s)
                   AND %s::text IS NULL
                   AND NOT %s::boolean
                   AND NOT EXISTS (
                       SELECT 1
                         FROM anagrafiche.soggetti_ruoli sr2
                        WHERE sr2.soggetto_id = s.id
                   )
            )
        """  # noqa: S608
        where_params = [
            search_pattern, search_pattern, search_pattern,
            tipo_ruolo, tipo_ruolo,
            emittente_ids, emittente_ids,
            search_pattern, search_pattern, search_pattern,
            tipo_ruolo,
            con_ruolo,
        ]

        count_sql = cte + "SELECT COUNT(*) FROM matches"  # noqa: S608
        data_sql = cte + f"""
            SELECT m.*,
                   {_FORNITURE_SELECT}
              FROM matches m
              LEFT JOIN LATERAL {_FORNITURE_LATERAL_TPL.format(sr_ref="m.soggetto_ruolo_id")} forn ON true
             ORDER BY m.ragione_sociale_completa ASC NULLS LAST,
                      m.ruolo_codice ASC NULLS FIRST,
                      m.soggetto_ruolo_id ASC NULLS FIRST
             LIMIT %s
        """  # noqa: S608

        with connection.cursor() as cursor:
            cursor.execute(count_sql, where_params)
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, where_params + [limit])
            rows = rows_to_list(cursor)

        return rows, total_count

    # Scopo: Restore by-id per l'AutoComplete (feedback_autocomplete_restore):
    #        ricostruisce la riga lookup gia' selezionata quando un form riapre
    #        in edit. Due chiavi alternative: soggetto_ruolo_id per le righe
    #        ruolo, soggetto_id per le righe "senza ruolo" (riga a ruolo NULL,
    #        indipendentemente dai ruoli che il soggetto possiede).
    # Perimetro: la STESSA regola di scope della ricerca, non lo stesso
    #        insieme di righe.
    #        - Riga ruolo: `_RUOLO_CL_SCOPE_SQL`, identica alla ricerca.
    #        - Riga «senza ruolo»: il soggetto e' visibile se NESSUNO dei suoi
    #          ruoli e' fuori scope (lo scope tocca solo il ruolo CL: gli altri
    #          ruoli non nascondono niente). ⚠️ E' PIU' LARGO della ricerca, di
    #          proposito: la ricerca propone la riga «senza ruolo» solo ai
    #          soggetti privi di qualunque ruolo, mentre il restore ricostruisce
    #          una selezione GIA' FATTA, e il soggetto puo' aver preso ruoli
    #          dopo. Un soggetto scelto quando non aveva ruoli resta quindi
    #          ricostruibile dopo che e' diventato cliente, ma solo per chi quel
    #          cliente lo vede; con soli ruoli non-CL, per chiunque.
    #        `emittente_ids` obbligatorio: None e' il bypass, e va detto.
    # ⛔ Fino al 2026-10-08 nessuno dei due rami lo applicava e la view, con
    #    `skip_area_check`, non lo chiedeva: con un id si leggevano nome e CF
    #    di soggetti di qualunque emittente (D10-bis).
    # Risultato: riga lookup, o None se non trovata O fuori scope.
    def get_ruolo_lookup_by_id(
        self,
        *,
        soggetto_ruolo_id: int | None = None,
        soggetto_id: str | None = None,
        emittente_ids: list[int] | None,
    ) -> dict[str, Any] | None:
        if soggetto_ruolo_id is not None:
            sql = f"""
                SELECT s.id AS soggetto_id,
                       sr.id AS soggetto_ruolo_id,
                       COALESCE(tr.codice_interno, tr.codice) AS ruolo_codice,
                       tr.descrizione AS ruolo_descrizione,
                       s.ragione_sociale_completa,
                       s.id_fiscale_univoco_cf_piva AS id_fiscale,
                       s.codice AS soggetto_codice,
                       {_FORNITURE_SELECT}
                  FROM anagrafiche.soggetti_ruoli sr
                  JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
                  JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
                  LEFT JOIN LATERAL {_FORNITURE_LATERAL_TPL.format(sr_ref="sr.id")} forn ON true
                 WHERE sr.id = %s
                   AND {_RUOLO_CL_SCOPE_SQL}
            """  # noqa: S608
            params: list[Any] = [soggetto_ruolo_id, emittente_ids, emittente_ids]
        else:
            sql = f"""
                SELECT s.id AS soggetto_id,
                       NULL::bigint AS soggetto_ruolo_id,
                       NULL::varchar AS ruolo_codice,
                       NULL::varchar AS ruolo_descrizione,
                       s.ragione_sociale_completa,
                       s.id_fiscale_univoco_cf_piva AS id_fiscale,
                       s.codice AS soggetto_codice,
                       {_FORNITURE_SELECT}
                  FROM anagrafiche.soggetti s
                  LEFT JOIN LATERAL {_FORNITURE_LATERAL_TPL.format(sr_ref="NULL::bigint")} forn ON true
                 WHERE s.id = %s::uuid
                   AND NOT EXISTS (
                       SELECT 1
                         FROM anagrafiche.soggetti_ruoli sr
                         JOIN config.tipi_ruoli tr ON tr.id = sr.tipo_ruolo_id
                        WHERE sr.soggetto_id = s.id
                          AND NOT {_RUOLO_CL_SCOPE_SQL}
                   )
            """  # noqa: S608
            params = [soggetto_id, emittente_ids, emittente_ids]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return row_to_dict(cursor)

    # Scopo: Verifica se un CF esiste gia' in anagrafica. Ritorna soggetto trovato o None.
    def find_by_codice_fiscale(self, codice_fiscale: str) -> dict[str, Any] | None:
        sql = """
            SELECT s.id, s.codice, s.ragione_sociale_completa, s.codice_fiscale
              FROM anagrafiche.soggetti s
             WHERE UPPER(TRIM(s.codice_fiscale)) = UPPER(TRIM(%s))
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [codice_fiscale])
            return row_to_dict(cursor)

    # Scopo: Verifica se una P.IVA esiste gia' in anagrafica. Ritorna soggetto trovato o None.
    def find_by_partita_iva(self, partita_iva: str) -> dict[str, Any] | None:
        sql = """
            SELECT s.id, s.codice, s.ragione_sociale_completa, s.partita_iva
              FROM anagrafiche.soggetti s
             WHERE UPPER(TRIM(s.partita_iva)) = UPPER(TRIM(%s))
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [partita_iva])
            return row_to_dict(cursor)

    # Scopo: Assegna ruolo a soggetto (get or create, idempotente).
    #        `codice_interno` e' gia' risolto dal chiamante
    #        (`resolve_tipo_ruolo`, sede unica della risoluzione); un
    #        codice sconosciuto passa com'e' e lo rifiuta la funzione DB col suo codice.
    def assign_ruolo(self, soggetto_id: str, codice_interno: str) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_get_or_create_soggetto_ruolo(%s::uuid, %s)",
                [soggetto_id, codice_interno],
            )
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Il TIPO RUOLO dal codice del payload, che puo' essere il codice
    #        (`CLIENTE`) o gia' il codice interno (`CL`): `{codice_interno,
    #        codice, descrizione}`, o None se sconosciuto. Il codice interno e'
    #        la chiave che il codice usa; codice e descrizione sono cio' che si
    #        mostra all'utente.
    # ⚠️ `codice` e `codice_interno` sono UNIQUE ciascuno, non fra loro: il
    #    codice di una riga puo' essere il codice interno di un'altra. Vince il
    #    `codice` (e' il campo del payload), e l'ORDER BY rende la scelta
    #    deterministica invece di lasciarla al `LIMIT 1`.
    def resolve_tipo_ruolo(self, codice_ruolo: str) -> dict[str, Any] | None:
        sql = """
            SELECT codice_interno, codice, descrizione
              FROM config.tipi_ruoli
             WHERE codice = %s OR codice_interno = %s
             ORDER BY (codice = %s) DESC
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [codice_ruolo, codice_ruolo, codice_ruolo])
            return row_to_dict(cursor)

    # =================================================================
    # Dati societari
    # =================================================================

    # =================================================================
    # Config resolver per tipo ruolo
    # =================================================================

    # Scopo: Dato un codice tipo_ruolo, restituisce le nature ammesse,
    # i tipi_soggetto_dettaglio con i requisiti CF/PIVA, il default
    # tipo_soggetto_dettaglio (da config.parameters) e min_search_length.
    # Usato dal SoggettoResolver frontend per adattare form e ricerca.
    # emittente_fiscale_id: se valorizzato, usato per risolvere override
    # del default sul livello emittente (catena fn_get_parameter_full).
    def get_config_resolver(
        self, tipo_ruolo_codice: str,
        emittente_fiscale_id: int | None = None,
    ) -> dict[str, Any] | None:
        # 1. Recupera tipo_ruolo
        sql_ruolo = """
            SELECT tr.id, COALESCE(tr.codice_interno, tr.codice) AS codice, tr.descrizione
              FROM config.tipi_ruoli tr
             WHERE COALESCE(tr.codice_interno, tr.codice) = %s
        """
        # 2. Nature ammesse per il ruolo (dalla matrice config)
        sql_nature = """
            SELECT ts.id AS tipo_soggetto_id,
                   ts.descrizione AS tipo_soggetto_descrizione,
                   ts.natura_soggetto
              FROM config.tipi_ruoli_nature_ammesse trna
              JOIN config.tipi_soggetto ts ON ts.id = trna.tipo_soggetto_id
             WHERE trna.tipo_ruolo_id = %s
               AND trna.attivo = true
               AND (trna.valido_dal IS NULL OR trna.valido_dal <= (SELECT script.fn_data_operativa()))
               AND (trna.valido_al IS NULL OR trna.valido_al >= (SELECT script.fn_data_operativa()))
        """
        # 3. Tipi soggetto dettaglio filtrati per nature ammesse
        # ⛔ `varchar[]`, non `bigint[]`: `config.tipi_soggetto.id` e' un codice
        #    (`PF`, `PG`, `ENC`). Col cast a `bigint[]` la query falliva su OGNI
        #    ruolo con la matrice delle nature valorizzata — cioe' tutti quelli
        #    del seed — e i test unitari, con la connessione mockata, non lo
        #    vedevano. Trovato il 2026-09-26 dal primo test sul DB vero
        #    (`test_ricerca_full_db`, brief-db-be-fe-ricerca-soglia-per-lista §6 b).
        sql_dettaglio = f"""
            {SQL_TIPI_SOGGETTO_DETTAGLIO}
             WHERE (%s::varchar[] IS NULL OR ts.id = ANY(%s::varchar[]))
             ORDER BY tsd.codice_interno
        """
        with connection.cursor() as cursor:
            cursor.execute(sql_ruolo, [tipo_ruolo_codice])
            ruolo = row_to_dict(cursor)
            if not ruolo:
                return None

            cursor.execute(sql_nature, [ruolo["id"]])
            nature = rows_to_list(cursor)

            # Se nessuna natura configurata, il ruolo accetta tutte le nature (NULL = nessun filtro)
            nature_ids = [n["tipo_soggetto_id"] for n in nature] if nature else None

            cursor.execute(sql_dettaglio, [nature_ids, nature_ids])
            dettagli = rows_to_list(cursor)

            # «Tutte le nature» si leggono dal dominio, l'enum di
            # `tipi_soggetto.natura_soggetto`, nell'ordine in cui e' dichiarato.
            # ⛔ Mai un elenco scritto qui: fino al 2026-09-26 era
            #    `["PF", "PG", "ENTE"]`, una seconda sede dell'enum che una
            #    natura nuova avrebbe lasciato indietro senza errore.
            if nature:
                nature_ammesse = [n["natura_soggetto"] for n in nature]
            else:
                cursor.execute(
                    "SELECT unnest(enum_range(NULL::config.natura_soggetto_enum))::text"
                )
                nature_ammesse = [r[0] for r in cursor.fetchall()]

        # 4. Default tipo_soggetto_dettaglio per ruolo (codice_interno via
        # config.parameters, override gratuito per emittente). Usiamo
        # ruolo["codice"] (validato dal DB) per costruire la chiave: evita
        # di propagare l'input utente raw nella stringa parametro.
        # Delega a ParameterRepository per coerenza con la firma di
        # script.fn_get_parameter_full.
        param_code = f"DEFAULT_TIPO_SOGGETTO_DETTAGLIO_{ruolo['codice']}"
        # ⚠️ FACOLTATIVO (2026-10-11): il default e' una preferenza, non un
        #    obbligo — il seed lo dichiara per CL e FO, e il FE ripiega sul primo
        #    tipo ammesso. Con `get_parameter` un ruolo senza parametro
        #    (RIS_UMANA, EF) mandava in errore tutto il risolutore.
        default_codice = ParameterRepository().get_parameter_se_dichiarato(
            param_code, emittente_fiscale_id=emittente_fiscale_id,
        )

        # Risolvi id dal codice_interno matchando i dettagli gia' caricati
        # (no extra query). Se il codice non e' tra i dettagli ammessi per
        # questo ruolo (config errata o cambio nature), default a None.
        default_id = next(
            (d["id"] for d in dettagli if d.get("codice_interno") == default_codice),
            None,
        ) if default_codice else None

        return {
            "tipo_ruolo": ruolo["codice"],
            "tipo_ruolo_descrizione": ruolo["descrizione"],
            "nature_ammesse": nature_ammesse,
            "tipi_soggetto_dettaglio": dettagli,
            "default_tipo_soggetto_dettaglio_id": default_id,
            # ⭐ La soglia del catalogo della lista soggetti, non una costante:
            #    il resolver cerca con `listSoggetti`, cioe' con QUESTA lista, e
            #    il BB di ricerca filtra solo da `ricerca_min_caratteri` in su.
            #    Una soglia sua sarebbe una seconda sede dello stesso fatto — e
            #    se fosse piu' bassa di quella del catalogo, il resolver
            #    manderebbe termini che il BB ignora, e proporrebbe come
            #    suggerimenti i primi soggetti NON filtrati, senza errore.
            #    Il codice lista viene dalla dichiarazione che la ricerca usa.
            "min_search_length": soglia_ricerca(_RICERCA_SOGGETTI.lista_codice),
        }

    # Scopo: Recupera dati societari del soggetto (se esistono).
    # ⚠️ `data_costituzione` (2026-10-10): il verbo di scrittura riceve lo STATO
    #    INTERO, quindi il form deve poter rimandare tutto cio' che la riga ha.
    #    Un campo letto qui e non rimandato verrebbe azzerato al primo salvataggio.
    def get_dati_societari(self, soggetto_id: str) -> dict[str, Any] | None:
        sql = """
            SELECT ds.id, ds.forma_giuridica_id,
                   fg.descrizione AS forma_giuridica_descrizione,
                   fg.codice AS forma_giuridica_codice,
                   fg.rea_policy, fg.capitale_sociale_policy,
                   ds.id_prov_iscri_rea, ds.iscrizione_rea,
                   ds.capitale_sociale,
                   ds.socio_unico, ds.liquidazione,
                   ds.destinatario_fe, ds.pec_fatturazione, ds.codice_sdi,
                   ds.data_costituzione::text
              FROM anagrafiche.dati_societari ds
              LEFT JOIN config.forme_giuridiche fg ON fg.id = ds.forma_giuridica_id
             WHERE ds.soggetto_id = %s::uuid
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id])
            return row_to_dict(cursor)
