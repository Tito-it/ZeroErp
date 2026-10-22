# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB specializzato per il sottodominio vendite/listini.
# ------------------------------------------------------------

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any
from uuid import UUID

from django.db import connection, transaction

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.db._helpers import (
    limiti_pagina,
    RicercaFull,
    add_ricerca_full_condition,
    fetch_paged_with_total,
    row_to_dict,
    rows_to_list,
    sql_order_clause,
)
from apps.core.db.sql_write_helpers import execute_dynamic_insert, sql_set_clause

logger = logging.getLogger(__name__)

# Sentinel SQL per il bound "open-ended" sui daterange. Allineato alla canonical
# form usata dalle STORED column `validita` su `listini_versioni` e
# `listini_righe_componenti` (`daterange(coalesce(d,'-infinity'),
# coalesce(a,'infinity'), '[]')`). Se la convenzione DB evolvera' (es. switch a
# `9999-12-31`), aggiornare qui — punto unico di drift.
_SQL_DATE_INFINITY = "'infinity'::date"


# `attivo` e' NUCLEO: lo stato ordina sempre. Aggiunta in anticipo sul seed
# della lista listini (passata unica 2026-08-01, richiesta del team DB).
LISTINI_ORDER_COLUMNS: dict[str, str] = {
    "codice": "l.codice",
    "descrizione": "l.descrizione",
    "utility_descrizione": "u.descrizione",
    "tipologia_descrizione": "lt.descrizione",
    "attivo": "l.attivo",
    "data_insert": "l.data_insert",
    "data_update": "l.data_update",
}

LISTINO_CREATE_COLUMNS: dict[str, str] = {
    "codice": "text",
    "descrizione": "text",
    "utility_id": "int",
    "tipologia_id": "int",
    "emittente_soggetto_ruolo_id": "int",
    "meta": "jsonb",
    "attivo": "bool",
}

LISTINO_UPDATE_COLUMNS: dict[str, str] = {
    key: value for key, value in LISTINO_CREATE_COLUMNS.items() if key != "codice"
}

VERSIONE_CREATE_COLUMNS: dict[str, str] = {
    "codice_versione": "text",
    "valido_dal": "date",
    "valido_al": "date",
    "meta": "jsonb",
    "attivo": "bool",
}

VERSIONE_UPDATE_COLUMNS: dict[str, str] = dict(VERSIONE_CREATE_COLUMNS)

RIGA_CREATE_COLUMNS: dict[str, str] = {
    "articolo_id": "uuid",
    "uom_id": "int",
    "prezzo": "numeric",
    "meta": "jsonb",
    "attivo": "bool",
}

RIGA_UPDATE_COLUMNS: dict[str, str] = {
    key: value for key, value in RIGA_CREATE_COLUMNS.items() if key not in {"articolo_id", "uom_id"}
}

# Whitelist ORDER BY delle righe di versione listino: chiave = `campo_sorgente`
# inviato dal frontend, valore = **alias di output** della SELECT.
#
# ⚠️ Alias di output e non colonne qualificate, perche' `list_righe` e' una
# `UNION ALL` (righe standalone + compositi bundle): dopo una UNION l'ORDER BY
# vede solo i nomi proiettati, non le tabelle delle due gambe.
#
# 🔴 Rimosse il 2026-08-03: `billing_account_codice`, `billing_account_descrizione`
# e `utility_descrizione`. Puntavano agli alias `ba`, `srd_ba` e `cu`, che non
# esistono nel FROM da quando il cleanup v5 (F1-DB-25) ha tolto quelle
# dimensioni da `listini_righe`. Non erano frecce morte che ripiegano in
# silenzio: erano **500** (`elemento FROM per la tabella "ba" mancante`) per
# chiunque le inviasse. Il commento del metodo diceva gia' che i parametri
# erano ignorati; la whitelist non era stata ripulita.
RIGHE_ORDER_COLUMNS: dict[str, str] = {
    "articolo_codice": "articolo_codice",
    "articolo_descrizione": "articolo_descrizione",
    "uom_codice": "uom_codice",
    "prezzo": "prezzo",
    "iva_aliquota": "iva_aliquota",
    "attivo": "attivo",
}


# Cosa si PUO' cercare; cosa si cerca lo dice il catalogo (`add_ricerca_full_condition`).
# ⭐ 2026-09-24 (brief-be-ricerca-full-liste-residue §7-bis, passo 7): le due
#    liste cercavano senza che il catalogo lo dichiarasse; il seed del team DB
#    ha acceso le colonne e la ricerca passa dal BB. ⛔ Ritirato nello stesso
#    giro `_append_ilike_search`, copia identica di quello di catalogo: niente
#    escape di `%`/`_`, niente strip, e un elenco di colonne cablato che il
#    pannello admin non poteva spegnere.
_RICERCA_LISTINI = RicercaFull("vendite.listini", ("codice", "descrizione"))

# ⭐ Forma a tupla sull'alias `unione`, e NON due mappe per le due gambe della
#    `UNION ALL` (`ad.*` e `adc.*`): la condizione si applica ai nomi che la
#    lista MOSTRA (`articolo_codice`, `articolo_descrizione`), sulla CTE, UNA
#    volta. Due dichiarazioni per gamba sarebbero due copie che possono
#    divergere — una riga standalone trovata e il composito con lo stesso
#    articolo no — e due letture del catalogo per ricerca.
_RICERCA_LISTINI_RIGHE = RicercaFull(
    "vendite.listini_righe", ("articolo_codice", "articolo_descrizione"),
)


class ListiniRepository:
    """Repository SQL per listini, versioni, righe (F2-BE-13: rimosso CRUD associazioni)."""

    # Scopo: Restituisce l'elenco listini con filtri opzionali, count e ordinamento whitelist.
    def list_listini(
        self,
        *,
        utility_id: int | None,
        tipologia_id: int | None,
        attivo: bool | None,
        search: str | None,
        order_by: str,
        order_dir: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        # BB `sql_order_clause` (NULL come valore minimo, tiebreak `l.id`
        # allineato). Rigido: il service ha gia' validato `order_by`/`order_dir`
        # contro la stessa whitelist, un valore estraneo qui e' un errore.
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=LISTINI_ORDER_COLUMNS, default="l.codice", tiebreak="l.id",
        )

        conditions: list[str] = []
        params: list[Any] = []

        if utility_id is not None:
            conditions.append("l.utility_id = %s")
            params.append(utility_id)
        if tipologia_id is not None:
            conditions.append("l.tipologia_id = %s")
            params.append(tipologia_id)
        if attivo is not None:
            conditions.append("l.attivo = %s")
            params.append(attivo)
        # ⚠️ Una condizione sola per le DUE query (conteggio e pagina): stessi
        #    `conditions`/`params`, quindi il totale non puo' descrivere un
        #    perimetro diverso dalle righe. Il 400 sotto soglia resta nella view
        #    (brief §6, decisione aperta): qui il BB non vede mai un termine corto.
        add_ricerca_full_condition(conditions, params, search, _RICERCA_LISTINI, alias="l")
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        count_sql = f"""
            SELECT COUNT(*)
              FROM vendite.listini l
              LEFT JOIN config.utilities u ON u.id = l.utility_id
              LEFT JOIN config.listini_tipologie lt ON lt.id = l.tipologia_id
            {where_clause}
        """  # noqa: S608 — WHERE da clausole letterali/BB add_ricerca_full_condition, ORDER BY da whitelist LISTINI_ORDER_COLUMNS, valori come parametri
        data_sql = f"""
            SELECT
                l.id,
                l.codice,
                l.descrizione,
                l.utility_id,
                u.codice AS utility_codice,
                u.descrizione AS utility_descrizione,
                l.tipologia_id,
                lt.codice AS tipologia_codice,
                lt.descrizione AS tipologia_descrizione,
                l.meta,
                l.attivo,
                l.data_insert,
                l.user_insert,
                l.data_update,
                l.user_update,
                (
                    SELECT COUNT(*)
                      FROM vendite.listini_versioni v
                     WHERE v.listino_id = l.id
                ) AS versioni_count
              FROM vendite.listini l
              LEFT JOIN config.utilities u ON u.id = l.utility_id
              LEFT JOIN config.listini_tipologie lt ON lt.id = l.tipologia_id
            {where_clause}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """  # noqa: S608 — WHERE da clausole letterali/BB add_ricerca_full_condition, ORDER BY da whitelist LISTINI_ORDER_COLUMNS, valori come parametri

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, params + [safe_limit, safe_offset])
            results = rows_to_list(cursor)

        return results, total_count

    # Scopo: Restituisce il dettaglio singolo del listino con metadati aggregati minimi.
    def get_listino(self, listino_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    l.id,
                    l.codice,
                    l.descrizione,
                    l.utility_id,
                    u.codice AS utility_codice,
                    u.descrizione AS utility_descrizione,
                    l.tipologia_id,
                    lt.codice AS tipologia_codice,
                    lt.descrizione AS tipologia_descrizione,
                    l.meta,
                    l.attivo,
                    l.data_insert,
                    l.user_insert,
                    l.data_update,
                    l.user_update,
                    (
                        SELECT COUNT(*)
                          FROM vendite.listini_versioni v
                         WHERE v.listino_id = l.id
                    ) AS versioni_count,
                    -- ⭐ Un listino con storia (una versione ATTIVA o CHIUSA)
                    --    non si spegne col flag: si spegne con la fine validita'
                    --    della versione (decisione di Tid, 2026-10-21; il DB
                    --    rifiuta con E_LISTINO_CON_STORIA_NON_SPEGNIBILE). La
                    --    regola e' del DB e si LEGGE da li', non si ricopia qui:
                    --    il drawer mostra il toggle solo se e' falso.
                    vendite.fn_listino_ha_storia(l.id) AS ha_storia
                  FROM vendite.listini l
                  LEFT JOIN config.utilities u ON u.id = l.utility_id
                  LEFT JOIN config.listini_tipologie lt ON lt.id = l.tipologia_id
                 WHERE l.id = %s
                """,
                [listino_id],
            )
            return row_to_dict(cursor)

    # Scopo: I listini che un contratto o un'offerta di questa utility e di
    #        questo emittente (`emittente_fiscale_id`, PK) puo' scegliere, per la
    #        tendina del form: `vendite.fn_listini_selezionabili`, il predicato
    #        del guard del documento (`script.fn_check_listino_documento`),
    #        quindi la tendina non propone cio' che il DB rifiuta (F-2 di
    #        brief-db-offerta-emissione-ed-erogazione). Sui VALORI del form: in
    #        creazione il documento non esiste. Non filtra sulla versione (in
    #        bozza un listino senza versione in vigore si sceglie: lo rifiutano
    #        attivazione ed emissione). Utility o emittente `None`: nessun
    #        listino. Forma `{id, codice, descrizione}`, ordinata dal DB.
    def list_lookup_selezionabili(
        self, utility_id: int | None, emittente_fiscale_id: int | None,
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, codice, descrizione
                  FROM vendite.fn_listini_selezionabili(%s, %s)
                """,
                [utility_id, emittente_fiscale_id],
            )
            return [
                {"id": int(row[0]), "codice": row[1], "descrizione": row[2]}
                for row in cursor.fetchall()
            ]

    # Scopo: Inserisce il listino usando solo colonne write ammesse.
    def create_listino(self, data: dict[str, Any]) -> int:
        # BB `execute_dynamic_insert`: whitelist RIGIDA sulle chiavi di
        # LISTINO_CREATE_COLUMNS (payload vuoto o chiave estranea -> ValueError).
        riga = execute_dynamic_insert(
            "vendite.listini", data, allowed=LISTINO_CREATE_COLUMNS,
        )
        return int(riga["id"])

    # Scopo: Aggiorna il listino sui soli campi forniti nel payload.
    def update_listino(self, listino_id: int, data: dict[str, Any]) -> bool:
        if not data:
            return False
        set_clause, params = sql_set_clause(data, allowed=LISTINO_UPDATE_COLUMNS)
        params.append(listino_id)

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE vendite.listini
                   SET {set_clause}
                 WHERE id = %s
                """,  # noqa: S608 — SET dal BB sql_set_clause su whitelist *_UPDATE_COLUMNS, valori come parametri
                params,
            )
            return cursor.rowcount > 0

    # Scopo: Elimina un listino. Usato solo quando il listino non ha figli
    #        (zero versioni): il guard di counts e' nel service.
    def delete_listino(self, listino_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM vendite.listini WHERE id = %s",
                [listino_id],
            )
            return cursor.rowcount > 0

    # Scopo: Restituisce le versioni del listino con conteggio righe e
    # ordinamento stabile. `righe_count` = N standalone + M compositi
    # distinti (modello unificato BoM 2026-05-13): un articolo composito
    # vive in `listini_righe_componenti` come N righe figlio, ma in UX
    # conta come UNA riga "articolo" della versione.
    def list_versioni(self, listino_id: int) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    v.id,
                    v.listino_id,
                    v.codice_versione,
                    v.valido_dal,
                    v.valido_al,
                    v.stato,
                    v.meta,
                    v.attivo,
                    v.data_insert,
                    v.user_insert,
                    v.data_update,
                    v.user_update,
                    (
                        SELECT COUNT(*)
                          FROM vendite.listini_righe r
                         WHERE r.listino_versione_id = v.id
                    ) + (
                        SELECT COUNT(DISTINCT lrc.articolo_padre_id)
                          FROM vendite.listini_righe_componenti lrc
                         WHERE lrc.listino_versione_id = v.id
                    ) AS righe_count
                  FROM vendite.listini_versioni v
                 WHERE v.listino_id = %s
                 ORDER BY v.valido_dal DESC, v.id DESC
                """,
                [listino_id],
            )
            return rows_to_list(cursor)

    # Scopo: Restituisce il dettaglio singolo della versione verificando
    # l'appartenenza al listino. Stessa semantica `righe_count` di
    # `list_versioni`: standalone + compositi distinti.
    def get_versione(self, listino_id: int, versione_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    v.id,
                    v.listino_id,
                    v.codice_versione,
                    v.valido_dal,
                    v.valido_al,
                    v.stato,
                    v.meta,
                    v.attivo,
                    v.data_insert,
                    v.user_insert,
                    v.data_update,
                    v.user_update,
                    (
                        SELECT COUNT(*)
                          FROM vendite.listini_righe r
                         WHERE r.listino_versione_id = v.id
                    ) + (
                        SELECT COUNT(DISTINCT lrc.articolo_padre_id)
                          FROM vendite.listini_righe_componenti lrc
                         WHERE lrc.listino_versione_id = v.id
                    ) AS righe_count
                  FROM vendite.listini_versioni v
                 WHERE v.listino_id = %s
                   AND v.id = %s
                """,
                [listino_id, versione_id],
            )
            return row_to_dict(cursor)

    # Scopo: Inserisce una nuova versione nel listino target.
    def create_versione(self, listino_id: int, data: dict[str, Any]) -> int:
        # `listino_id` e' la chiave del padre, fuori dal payload: la whitelist
        # la nomina esplicitamente accanto alle colonne del payload.
        riga = execute_dynamic_insert(
            "vendite.listini_versioni",
            {"listino_id": listino_id, **data},
            allowed={"listino_id", *VERSIONE_CREATE_COLUMNS},
        )
        return int(riga["id"])

    # Scopo: Aggiorna la versione mantenendo il perimetro del listino.
    def update_versione(self, listino_id: int, versione_id: int, data: dict[str, Any]) -> bool:
        if not data:
            return False
        set_clause, params = sql_set_clause(data, allowed=VERSIONE_UPDATE_COLUMNS)
        params.extend([listino_id, versione_id])

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE vendite.listini_versioni
                   SET {set_clause}
                 WHERE listino_id = %s
                   AND id = %s
                """,  # noqa: S608 — SET dal BB sql_set_clause su whitelist *_UPDATE_COLUMNS, valori come parametri
                params,
            )
            return cursor.rowcount > 0

    # Scopo: Clona una versione esistente in una nuova versione BOZZA dello stesso
    #        listino, copiando tutte le righe attive della sorgente. La nuova versione
    #        prende i dati di testata dal payload (codice_versione, valido_dal,
    #        valido_al); meta e attivo derivano dai default DB. Restituisce
    #        l'id della nuova versione. Esegue tutto in transazione gestita dal caller.
    def clone_versione(
        self,
        listino_id: int,
        src_versione_id: int,
        target_data: dict[str, Any],
    ) -> int:
        # Guardrail atomicità (review 2026-07-08): INSERT testata + INSERT righe clonate
        # resi self-atomici (o versione+righe complete o rollback). Nested=savepoint.
        with transaction.atomic(), connection.cursor() as cursor:
            # 1) INSERT testata nuova versione, stato BOZZA forzato.
            #    ⛔ Whitelist RIGIDA (BB `execute_dynamic_insert`): attivo/meta
            #    NON si clonano, e il payload li ha gia' tolti il service
            #    (`fn_clone_versione`, `clonable_fields`). Qui non si scartano
            #    in silenzio: se arrivassero sarebbe un errore del chiamante.
            target_versione_id = int(
                execute_dynamic_insert(
                    "vendite.listini_versioni",
                    {"listino_id": listino_id, **target_data, "stato": "BOZZA"},
                    allowed={
                        "listino_id", "codice_versione", "valido_dal", "valido_al", "stato",
                    },
                )["id"]
            )

            # 2) Copy delle righe ATTIVE della sorgente nella nuova versione.
            #    Pricing v5: le dimensioni contesto (BA/utility/emittente)
            #    sono state droppate da listini_righe (F1-DB-25). La riga
            #    e' (articolo, uom, prezzo, meta). Forziamo attivo=TRUE sulla
            #    copia. user_insert/data_insert sono gestiti dai default audit.
            cursor.execute(
                """
                INSERT INTO vendite.listini_righe (
                    listino_versione_id,
                    articolo_id,
                    uom_id,
                    prezzo,
                    meta,
                    attivo
                )
                SELECT
                    %s,
                    articolo_id,
                    uom_id,
                    prezzo,
                    meta,
                    TRUE
                  FROM vendite.listini_righe
                 WHERE listino_versione_id = %s
                   AND attivo IS TRUE
                """,
                [target_versione_id, src_versione_id],
            )

            # 3) Copy delle righe bundle compositi ATTIVE
            #    (`listini_righe_componenti`) della sorgente nella nuova
            #    versione (modello unificato BoM 2026-05-13). Ricalcolo
            #    `valido_dal`/`valido_al` come intersezione fra validita'
            #    della BoM (`articoli_componenti`) e validita' della versione
            #    target (NON della sorgente: l'admin si aspetta prezzi validi
            #    per il nuovo range).
            #
            #    `GREATEST`/`LEAST` sono NULL-safe in PG: NULL viene ignorato
            #    nel calcolo. Quindi `LEAST(NULL, date)=date`, `LEAST(NULL,NULL)=NULL`.
            #    NULL su `valido_al` significa "open-ended" e la formula lo
            #    propaga correttamente (post-fix DB 2026-05-15 il trigger
            #    `trgfn_listini_righe_comp_guard_coerenza_bom` coalesce
            #    simmetricamente vs STORED su listini_versioni.validita).
            #
            #    Skip riga se intersezione vuota (es. BoM scaduta o non
            #    coperta dalla versione target): il WHERE finale lo intercetta
            #    via COALESCE→'infinity'. Senza lo skip la riga arriverebbe al
            #    guard comune delle date (`script.trgfn_guard_date_validita`,
            #    dal 2026-09-23) con `E_DATA_AL_MINORE_DAL`, e l'intera copia
            #    fallirebbe per una sola riga fuori periodo.
            cursor.execute(
                f"""
                INSERT INTO vendite.listini_righe_componenti (
                    listino_versione_id,
                    articolo_componente_id,
                    articolo_padre_id,
                    articolo_figlio_id,
                    prezzo,
                    iva_id,
                    valido_dal,
                    valido_al,
                    attivo
                )
                SELECT
                    %s,
                    lrc.articolo_componente_id,
                    lrc.articolo_padre_id,
                    lrc.articolo_figlio_id,
                    lrc.prezzo,
                    lrc.iva_id,
                    GREATEST(ac.valido_dal, target_v.valido_dal) AS v_dal,
                    LEAST(ac.valido_al, target_v.valido_al) AS v_al,
                    TRUE
                  FROM vendite.listini_righe_componenti lrc
                  JOIN catalogo.articoli_componenti ac
                       ON ac.id = lrc.articolo_componente_id
                  JOIN vendite.listini_versioni target_v
                       ON target_v.id = %s
                 WHERE lrc.listino_versione_id = %s
                   AND lrc.attivo IS TRUE
                   AND GREATEST(ac.valido_dal, target_v.valido_dal) <=
                       LEAST(
                           COALESCE(ac.valido_al, {_SQL_DATE_INFINITY}),
                           COALESCE(target_v.valido_al, {_SQL_DATE_INFINITY})
                       )
                """,  # noqa: S608 — costante di modulo _SQL_DATE_INFINITY, valori come parametri
                [target_versione_id, target_versione_id, src_versione_id],
            )

        return target_versione_id

    # Scopo: Elimina una versione e le sue righe in cascata. Usato solo per
    #        versioni in stato BOZZA: il guard di stato e' nel service. La cascade
    #        sulle righe e` esplicita perche' la FK puo' non avere ON DELETE CASCADE
    #        (le righe ATTIVE non vanno mai cancellate, qui si parla solo di BOZZA).
    #        Cascade su 2 tabelle figlie:
    #          - `listini_righe` (standalone)
    #          - `listini_righe_componenti` (compositi, modello unificato 2026-05-13)
    def delete_versione(self, listino_id: int, versione_id: int) -> bool:
        # Guardrail atomicità (review 2026-07-08): 3 DELETE a cascata (componenti +
        # righe + versione) resi self-atomici. Nested=savepoint se caller ha atomic.
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM vendite.listini_righe_componenti "
                "WHERE listino_versione_id = %s",
                [versione_id],
            )
            cursor.execute(
                "DELETE FROM vendite.listini_righe WHERE listino_versione_id = %s",
                [versione_id],
            )
            cursor.execute(
                """
                DELETE FROM vendite.listini_versioni
                 WHERE listino_id = %s
                   AND id = %s
                """,
                [listino_id, versione_id],
            )
            return cursor.rowcount > 0

    # Scopo: Restituisce le versioni candidate all'auto-close quando si attiva
    #        una nuova versione (decisione D3). Sono le versioni dello stesso
    #        listino con `attivo = TRUE`, `valido_dal < nuova.valido_dal`, e la
    #        cui `validita` (daterange) si sovrappone al nuovo intervallo. La
    #        versione che si sta per attivare viene esclusa per id. Il filtro
    #        si basa sulla validita` E sullo stato 'ATTIVA' (regola §6 brief
    #        2026-05-16): l'autoclose tocca solo versioni operative. Le BOZZA
    #        in cantiere si cancellano manualmente, non si chiudono per
    #        scadenza (sono preparazione, non versione operativa).
    def find_versioni_per_autoclose(
        self,
        listino_id: int,
        exclude_versione_id: int,
        nuova_valido_dal: date,
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    codice_versione,
                    valido_dal,
                    valido_al
                  FROM vendite.listini_versioni
                 WHERE listino_id = %s
                   AND id <> %s
                   AND attivo IS TRUE
                   AND stato = 'ATTIVA'
                   AND valido_dal < %s
                   AND validita && daterange(%s, NULL, '[)')
                 ORDER BY valido_dal
                """,
                [listino_id, exclude_versione_id, nuova_valido_dal, nuova_valido_dal],
            )
            return rows_to_list(cursor)

    # Scopo: Aggiorna solo il valido_al di una versione (usato dall'auto-close
    #        all'attivazione: chiude la precedente al giorno prima della nuova
    #        decorrenza). Operazione atomica usata dentro una transazione caller.
    #        Filtra anche per listino_id come safety guard contro chiamate errate.
    def set_versione_valido_al(self, *, listino_id: int, versione_id: int, valido_al: date) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.listini_versioni
                   SET valido_al = %s
                 WHERE listino_id = %s
                   AND id = %s
                """,
                [valido_al, listino_id, versione_id],
            )
            return cursor.rowcount > 0

    # Scopo: Aggiorna lo stato della versione con check di appartenenza al listino.
    def change_versione_state(self, listino_id: int, versione_id: int, stato: str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.listini_versioni
                   SET stato = %s
                 WHERE listino_id = %s
                   AND id = %s
                """,
                [stato, listino_id, versione_id],
            )
            return cursor.rowcount > 0

    # Scopo: Conta le righe prezzo ATTIVE della versione per guard di
    # pubblicazione (BOZZA → ATTIVA richiede >= 1 riga). Somma standalone
    # + compositi distinti (modello unificato BoM 2026-05-13). Senza
    # contare i compositi un listino di soli compositi non si potrebbe mai
    # attivare.
    def count_active_righe_versione(self, versione_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    (
                        SELECT COUNT(*)
                          FROM vendite.listini_righe
                         WHERE listino_versione_id = %s
                           AND attivo IS TRUE
                    ) + (
                        SELECT COUNT(DISTINCT articolo_padre_id)
                          FROM vendite.listini_righe_componenti
                         WHERE listino_versione_id = %s
                           AND attivo IS TRUE
                    )
                """,
                [versione_id, versione_id],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # Scopo: Restituisce le righe della versione listino con display fields
    #        articolo/UoM, paginazione server-side e search sull'articolo.
    #
    #        ⚠️ UNA lista sola (decisione Tid 2026-08-02): la SELECT e' una
    #        `UNION ALL` fra le righe standalone di `listini_righe` e i
    #        **compositi con prezzo bundle** aggregati da
    #        `listini_righe_componenti`. Prima i compositi arrivavano da un
    #        endpoint separato e il FE li concatenava DOPO la paginazione: con
    #        righe aggiunte a valle, `total` e numero di pagine mentivano.
    #        Ogni riga porta `is_composito` (discriminatore per il FE) e
    #        `row_key` (chiave stabile della DataTable: l'id per le standalone,
    #        `composito:<uuid>` per i padri, che non hanno un id di testata).
    def list_righe(
        self,
        listino_id: int,
        versione_id: int,
        *,
        search: str | None = None,
        attivo: bool | None = True,
        order_by: str = "articolo_descrizione",
        order_dir: str | None = "asc",
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        # BB `sql_order_clause`, rigido come `list_listini`. Il default e'
        # l'ALIAS di uscita `articolo_descrizione`: dopo la UNION l'ORDER BY
        # vede solo i nomi proiettati — il vecchio ripiego `ad.descrizione`
        # avrebbe fatto fallire la query. Tiebreak `row_key` (chiave univoca
        # della riga, standalone o composito) allineato alla direzione.
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=RIGHE_ORDER_COLUMNS, default="articolo_descrizione",
            tiebreak="row_key",
        )

        conditions: list[str] = ["r.listino_versione_id = %s"]
        params: list[Any] = [versione_id]

        # Join guard: la versione deve appartenere al listino richiesto.
        join_guard_params: list[Any] = [listino_id]

        # ⛔ Niente filtro per billing_account/utility: le colonne sono state
        #    tolte da listini_righe (F1-DB-25), il contesto vive sul listino o
        #    sul contratto. Fino al 2026-10-20 i parametri restavano nella firma
        #    e venivano IGNORATI: un filtro accettato che non filtrava.
        if attivo is not None:
            conditions.append("r.attivo = %s")
            params.append(attivo)

        where_clause = "WHERE " + " AND ".join(conditions)

        from_clause = """
              FROM vendite.listini_righe r
              JOIN vendite.listini_versioni v
                ON v.id = r.listino_versione_id
               AND v.listino_id = %s
              LEFT JOIN catalogo.vw_articoli_dettaglio ad
                ON ad.id = r.articolo_id
              LEFT JOIN catalogo.unita_misura u
                ON u.id = r.uom_id
        """

        # ── Gamba 2: i compositi con prezzo bundle ────────────────────────
        # Stessi filtri della gamba standalone (guard listino↔versione; la
        # ricerca sta FUORI dalle gambe, sulla CTE `unione` — vedi
        # `_RICERCA_LISTINI_RIGHE`); `attivo` non e' una colonna di
        # `listini_righe_componenti` a livello di padre: il composito ESISTE
        # nella lista se ha almeno un componente attivo, quindi il filtro
        # `attivo=False` non ha compositi da mostrare.
        cond_comp: list[str] = ["lrc.listino_versione_id = %s", "lrc.attivo = TRUE"]
        params_comp: list[Any] = [versione_id]
        where_comp = "WHERE " + " AND ".join(cond_comp)
        # `attivo=False` chiede esplicitamente le righe disattivate: i compositi
        # non ne hanno, quindi la gamba si annulla invece di sporcare l'elenco.
        if attivo is False:
            cond_comp.append("FALSE")
            where_comp = "WHERE " + " AND ".join(cond_comp)

        # ── La ricerca libera: sulla UNIONE, cioe' su cio' che la lista mostra ─
        # ⭐ Il `WHERE` sta prima di `COUNT(*) OVER()`, quindi il totale conta
        #    le righe trovate e non l'intera versione. PostgreSQL spinge la
        #    condizione dentro le due gambe della `UNION ALL` (colonne del
        #    `GROUP BY` nella seconda): non si paga una scansione in piu'.
        cond_unione: list[str] = []
        params_unione: list[Any] = []
        add_ricerca_full_condition(
            cond_unione, params_unione, search, _RICERCA_LISTINI_RIGHE, alias="unione",
        )
        where_unione = ("WHERE " + " AND ".join(cond_unione)) if cond_unione else ""

        data_sql = f"""
            WITH unione AS (
                SELECT
                    r.id::text                          AS row_key,
                    FALSE                               AS is_composito,
                    r.id,
                    r.listino_versione_id,
                    r.articolo_id,
                    ad.codice                           AS articolo_codice,
                    ad.descrizione                      AS articolo_descrizione,
                    r.uom_id,
                    u.codice                            AS uom_codice,
                    u.descrizione                       AS uom_descrizione,
                    r.prezzo,
                    -- IVA dell'articolo (denormalizzata dal `vw_articoli_dettaglio`):
                    -- il FE mostra la colonna IVA per ogni riga (audit visivo +
                    -- coerenza padre-figlio nei bundle).
                    ad.iva_id,
                    ad.iva_codice,
                    ad.iva_aliquota_iva                 AS iva_aliquota,
                    NULL::bigint                        AS n_componenti_bundle,
                    r.meta,
                    r.attivo,
                    r.data_insert,
                    r.user_insert,
                    r.data_update,
                    r.user_update
                {from_clause}
                {where_clause}

                UNION ALL

                SELECT
                    'composito:' || lrc.articolo_padre_id::text AS row_key,
                    TRUE                                AS is_composito,
                    NULL::bigint                        AS id,
                    lrc.listino_versione_id,
                    lrc.articolo_padre_id               AS articolo_id,
                    adc.codice                          AS articolo_codice,
                    adc.descrizione                     AS articolo_descrizione,
                    NULL::bigint                        AS uom_id,
                    NULL::varchar                       AS uom_codice,
                    NULL::varchar                       AS uom_descrizione,
                    -- Il composito non ha un prezzo proprio: il suo valore e' la
                    -- somma dei componenti, mostrata come badge «N componenti».
                    NULL::numeric                       AS prezzo,
                    adc.iva_id,
                    adc.iva_codice,
                    adc.iva_aliquota_iva                AS iva_aliquota,
                    COUNT(*)                            AS n_componenti_bundle,
                    NULL::jsonb                         AS meta,
                    TRUE                                AS attivo,
                    MIN(lrc.data_insert)                AS data_insert,
                    MIN(lrc.user_insert)                AS user_insert,
                    MAX(lrc.data_update)                AS data_update,
                    NULL::text                          AS user_update
                  FROM vendite.listini_righe_componenti lrc
                  JOIN vendite.listini_versioni vc
                    ON vc.id = lrc.listino_versione_id
                   AND vc.listino_id = %s
                  LEFT JOIN catalogo.vw_articoli_dettaglio adc
                    ON adc.id = lrc.articolo_padre_id
                {where_comp}
                 GROUP BY lrc.articolo_padre_id, lrc.listino_versione_id,
                          adc.codice, adc.descrizione, adc.iva_id,
                          adc.iva_codice, adc.iva_aliquota_iva
            )
            SELECT *, COUNT(*) OVER() AS total_count
              FROM unione
            {where_unione}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """  # noqa: S608 — ordinamento dal BB sql_order_clause su whitelist RIGHE_ORDER_COLUMNS

        # L'ordine dei parametri segue il testo SQL: gamba 1 (join_guard +
        # where), gamba 2 (join_guard + where), la ricerca sulla unione, poi
        # la paginazione.
        data_params = (
            join_guard_params + params
            + join_guard_params + params_comp
            + params_unione
            + [safe_limit, safe_offset]
        )

        # Righe e totale da `COUNT(*) OVER()`: una sola valutazione della union
        # invece di count + data separati; oltre l'ultima pagina il BB rilegge
        # la prima riga per il totale vero.
        return fetch_paged_with_total(data_sql, data_params, offset=safe_offset)

    # Scopo: Restituisce il dettaglio singolo della riga prezzo in perimetro listino/versione.
    def get_riga(self, listino_id: int, versione_id: int, riga_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    r.id,
                    r.listino_versione_id,
                    r.articolo_id,
                    r.uom_id,
                    r.prezzo,
                    r.meta,
                    r.attivo,
                    r.data_insert,
                    r.user_insert,
                    r.data_update,
                    r.user_update
                  FROM vendite.listini_righe r
                  JOIN vendite.listini_versioni v
                    ON v.id = r.listino_versione_id
                   AND v.listino_id = %s
                 WHERE r.listino_versione_id = %s
                   AND r.id = %s
                """,
                [listino_id, versione_id, riga_id],
            )
            return row_to_dict(cursor)

    # Scopo: Inserisce una riga prezzo nella versione target.
    def create_riga(self, versione_id: int, data: dict[str, Any]) -> int:
        riga = execute_dynamic_insert(
            "vendite.listini_righe",
            {"listino_versione_id": versione_id, **data},
            allowed={"listino_versione_id", *RIGA_CREATE_COLUMNS},
        )
        return int(riga["id"])

    # Scopo: Aggiorna una riga prezzo nel perimetro listino/versione.
    def update_riga(self, listino_id: int, versione_id: int, riga_id: int, data: dict[str, Any]) -> bool:
        if not data:
            return False
        set_clause, params = sql_set_clause(data, allowed=RIGA_UPDATE_COLUMNS)
        params.extend([listino_id, versione_id, riga_id])

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE vendite.listini_righe r
                   SET {set_clause}
                  FROM vendite.listini_versioni v
                 WHERE r.listino_versione_id = v.id
                   AND v.listino_id = %s
                   AND r.listino_versione_id = %s
                   AND r.id = %s
                """,  # noqa: S608 — SET dal BB sql_set_clause su whitelist *_UPDATE_COLUMNS, valori come parametri
                params,
            )
            return cursor.rowcount > 0

    # Scopo: Elimina una riga prezzo mantenendo il check di appartenenza gerarchica.
    def delete_riga(self, listino_id: int, versione_id: int, riga_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM vendite.listini_righe r
                 USING vendite.listini_versioni v
                 WHERE r.listino_versione_id = v.id
                   AND v.listino_id = %s
                   AND r.listino_versione_id = %s
                   AND r.id = %s
                """,
                [listino_id, versione_id, riga_id],
            )
            return cursor.rowcount > 0

    # Scopo: Verifica in un solo round-trip articolo attivo, UoM attiva e coerenza articolo/UoM.
    def get_articolo_uom_validation(self, articolo_id: UUID | str, uom_id: int) -> dict[str, bool]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    EXISTS(
                        SELECT 1
                          FROM catalogo.articoli a
                         WHERE a.id = %s
                           AND a.attivo IS TRUE
                    ) AS articolo_attivo,
                    EXISTS(
                        SELECT 1
                          FROM catalogo.unita_misura u
                         WHERE u.id = %s
                           AND u.attivo IS TRUE
                    ) AS uom_attiva,
                    EXISTS(
                        SELECT 1
                          FROM catalogo.articoli a
                         WHERE a.id = %s
                           AND a.attivo IS TRUE
                           AND a.uom_id = %s
                        UNION ALL
                        SELECT 1
                          FROM catalogo.articoli_uom_operativa uo
                         WHERE uo.articolo_id = %s
                           AND uo.uom_id = %s
                           AND uo.attivo IS TRUE
                    ) AS uom_compatibile
                """,
                [articolo_id, uom_id, articolo_id, uom_id, articolo_id, uom_id],
            )
            row = cursor.fetchone()

        assert row is not None
        return {
            "articolo_attivo": bool(row[0]),
            "uom_attiva": bool(row[1]),
            "uom_compatibile": bool(row[2]),
        }

    # Scopo: Blocca la riga con FOR UPDATE per prevenire race condition durante
    #        la rettifica controllata N6. Restituisce True se la riga esiste.
    def lock_riga_for_update(self, versione_id: int, riga_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM vendite.listini_righe
                 WHERE id = %s AND listino_versione_id = %s
                   FOR UPDATE
                """,
                [riga_id, versione_id],
            )
            return cursor.fetchone() is not None

    # Scopo: Aggiorna il prezzo di una riga per rettifica controllata N6.
    #        Aggiorna anche meta con audit trail. Caller gestisce transazione.
    def update_riga_prezzo_rettifica(
        self,
        riga_id: int,
        nuovo_prezzo: str,
        meta_aggiornata: dict[str, Any] | None,
    ) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE vendite.listini_righe
                   SET prezzo = %(prezzo)s::numeric,
                       meta = %(meta)s::jsonb,
                       data_update = now()
                 WHERE id = %(riga_id)s
                """,
                {
                    "riga_id": riga_id,
                    "prezzo": nuovo_prezzo,
                    "meta": json.dumps(meta_aggiornata) if meta_aggiornata else None,
                },
            )
            return cursor.rowcount > 0

    # Scopo: Restituisce versioni ATTIVE in scadenza entro N giorni senza successore.
    #        Filtro temporale isolato per facilitare futura migrazione daterange (N1).
    # ⛔ La scadenza e' `valido_al` (incluso), NON `upper(validita)`:
    #    `validita` e' `daterange(valido_dal, valido_al, '[]')`, che PostgreSQL
    #    normalizza in `[)`, quindi `upper()` vale `valido_al + 1`. Fino al
    #    2026-10-21 la query leggeva `upper()` e sbagliava di un giorno la
    #    scadenza, i giorni rimanenti e il successore contiguo
    #    (brief-be-verifica-documentazione-api §C1).
    def _filter_versioni_in_scadenza(self) -> str:
        return (
            "v.valido_al IS NOT NULL "
            "AND v.valido_al <= (SELECT script.fn_data_operativa()) + %(giorni)s * INTERVAL '1 day'"
        )

    # Scopo: Lista versioni operativamente ATTIVE oggi che scadono entro `giorni`
    #        e non hanno una versione successiva (BOZZA o operativa) che subentra.
    #        Filtro operativo: stato='ATTIVA' + `validita @> fn_data_operativa()` (regola
    #        §6 brief 2026-05-16: la BOZZA e' preparazione, non versione operativa,
    #        quindi non genera alert di scadenza). Per il "successore che
    #        subentrera`" sono ammesse sia BOZZA sia operative future.
    def listini_in_scadenza(self, giorni: int) -> list[dict[str, Any]]:
        filtro_scadenza = self._filter_versioni_in_scadenza()
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    l.id AS listino_id,
                    l.codice AS listino_codice,
                    l.descrizione AS listino_descrizione,
                    l.utility_id,
                    u.descrizione AS utility_descrizione,
                    v.id AS versione_id,
                    v.codice_versione,
                    v.valido_dal,
                    v.valido_al,
                    v.valido_al - (SELECT script.fn_data_operativa()) AS giorni_rimanenti
                  FROM vendite.listini_versioni v
                  JOIN vendite.listini l ON l.id = v.listino_id
                  LEFT JOIN config.utilities u ON u.id = l.utility_id
                 WHERE v.validita @> (SELECT script.fn_data_operativa())
                   AND v.attivo IS TRUE
                   AND v.stato = 'ATTIVA'
                   AND l.attivo IS TRUE
                   AND {filtro_scadenza}
                   AND NOT EXISTS (
                       SELECT 1
                         FROM vendite.listini_versioni succ
                        WHERE succ.listino_id = v.listino_id
                          AND succ.id != v.id
                          AND succ.attivo IS TRUE
                          -- Il successore CONTIGUO nasce il giorno dopo la
                          -- scadenza: `valido_dal = valido_al + 1`, cioe' `>`.
                          AND succ.valido_dal > v.valido_al
                          AND (
                              succ.stato = 'BOZZA'
                              OR succ.validita && daterange(v.valido_al + 1, NULL, '[)')
                          )
                   )
                 ORDER BY v.valido_al ASC, l.codice
                """,  # noqa: S608 — filtro letterale da _filter_versioni_in_scadenza, valori come parametri
                {"giorni": giorni},
            )
            return rows_to_list(cursor)

    # Scopo: Applica variazione percentuale massa ai prezzi delle righe attive
    #        di una versione. Se dry_run=True restituisce la preview senza modificare.
    #        Restituisce (righe_aggiornate, preview_rows).
    def applica_variazione_percentuale(
        self,
        versione_id: int,
        variazione_pct: str,
        arrotondamento_decimali: int,
        filtro_articoli: list[str] | None = None,
        *,
        dry_run: bool = False,
    ) -> tuple[int, list[dict[str, Any]]]:
        with connection.cursor() as cursor:
            if dry_run:
                # Scopo: calcola i prezzi senza modificare, per preview frontend.
                cursor.execute(
                    """
                    SELECT
                        r.id AS riga_id,
                        a.codice AS articolo_codice,
                        a.descrizione AS articolo_descrizione,
                        r.prezzo AS prezzo_attuale,
                        ROUND(r.prezzo * (1 + %(pct)s::numeric / 100.0), %(dec)s) AS prezzo_calcolato
                      FROM vendite.listini_righe r
                      JOIN catalogo.articoli a ON a.id = r.articolo_id
                     WHERE r.listino_versione_id = %(ver_id)s
                       AND r.attivo IS TRUE
                       AND (%(filtro)s::uuid[] IS NULL
                            OR r.articolo_id = ANY(%(filtro)s::uuid[]))
                     ORDER BY a.codice, r.id
                    """,
                    {
                        "ver_id": versione_id,
                        "pct": variazione_pct,
                        "dec": arrotondamento_decimali,
                        "filtro": filtro_articoli,
                    },
                )
                preview = rows_to_list(cursor)
                return len(preview), preview

            # Scopo: applica UPDATE reale sulle righe.
            cursor.execute(
                """
                UPDATE vendite.listini_righe
                   SET prezzo = ROUND(prezzo * (1 + %(pct)s::numeric / 100.0), %(dec)s),
                       data_update = now()
                 WHERE listino_versione_id = %(ver_id)s
                   AND attivo IS TRUE
                   AND (%(filtro)s::uuid[] IS NULL
                        OR articolo_id = ANY(%(filtro)s::uuid[]))
                """,
                {
                    "ver_id": versione_id,
                    "pct": variazione_pct,
                    "dec": arrotondamento_decimali,
                    "filtro": filtro_articoli,
                },
            )
            return cursor.rowcount, []

    # Scopo: Restituisce le tipologie listino ammesse per una utility, leggendo
    #        la matrice config.listini_tipologie_utilities (solo righe attive).
    def list_tipologie_per_utility(self, utility_id: int) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    lt.id,
                    lt.codice,
                    lt.descrizione,
                    lt.e_consumo,
                    lt.e_quota_fissa,
                    lt.e_imposta,
                    lt.e_onere,
                    lt.e_prodotto,
                    lt.e_servizio,
                    lt.ordinamento
                  FROM config.listini_tipologie lt
                  JOIN config.listini_tipologie_utilities m
                    ON m.tipologia_id = lt.id
                 WHERE m.utility_id = %s
                   AND m.attivo = true
                   AND lt.attivo = true
                 ORDER BY lt.ordinamento, lt.descrizione
                """,
                [utility_id],
            )
            return rows_to_list(cursor)

    # ══════════════════════════════════════════════════════════
    #  BUNDLE componenti (modello unificato BoM 2026-05-13)
    # ══════════════════════════════════════════════════════════
    #
    # Tabella `vendite.listini_righe_componenti`: una riga = "in questa
    # versione listino, il componente X del padre composito Y ha prezzo Z".
    # Il prezzo padre composito NON e' un dato di listino (e' SUM dei
    # componenti via resolver bundle-aware); listini_righe diretti su
    # padre composito sono vietati (trigger 20260513-04).
    #
    # API repo: 2 metodi
    #   (l'elenco dei padri compositi con prezzo bundle NON e' piu' un metodo
    #    a se': dal 2026-08-03 e' la seconda gamba della UNION in `list_righe`,
    #    perche' righe standalone e compositi sono UNA lista sola e devono
    #    essere paginati e contati insieme)
    #   - list_bundle_preview(versione_id, padre_id, data_riferimento):
    #     BoM corrente del padre LEFT JOIN prezzi gia' definiti, per
    #     popolare il Dialog di editing
    #   - upsert_bundle(versione_id, padre_id, rows, validita_versione):
    #     batch INSERT/UPDATE/soft-delete delle righe bundle per quel
    #     padre, in transazione atomica.

    # Scopo: Lista articoli compositi che hanno almeno 1 riga in
    # `listini_righe_componenti` attiva per la versione data. Usata dal
    # FE per popolare la sezione "Prezzi bundle compositi" del drawer
    # versione listino. Una riga per padre, con conteggio componenti
    # definiti + codice/descrizione articolo padre.
    #
    # Nota: NON proiettiamo un totale bundle qui. Il totale corretto e'
    # SUM(prezzo_componente * coeff_qta) dai dati BoM (articoli_componenti)
    # — un SUM(lrc.prezzo) puro sarebbe fuorviante perche' ignora i
    # coefficienti. Il totale per padre vive nel preview del Dialog detail
    # (`list_bundle_preview`) dove abbiamo accesso a `ac.coeff_qta`.

    # Scopo: Preview BoM corrente di un padre composito + LEFT JOIN sui
    # prezzi gia' definiti in `listini_righe_componenti` per la versione
    # listino target. Restituisce 1 riga per ogni `articoli_componenti`
    # valida alla data; `prezzo_listino_bundle` NULL se non ancora
    # definito (l'admin lo valorizza nel Dialog).
    # `data_riferimento`: data per filtrare BoM corrente (validita @>).
    # Tipicamente = oggi o = validita versione listino (lower bound).
    def list_bundle_preview(
        self,
        *,
        versione_id: int,
        articolo_padre_id: str,
        data_riferimento: date,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                ac.id                              AS articolo_componente_id,
                ac.componente_id,
                a.codice                           AS componente_codice,
                a.descrizione                      AS componente_descrizione,
                ac.coeff_qta,
                -- Alias `quantita_componente` per uniformita' col
                -- `ComponentiDialog` FE (template colonna Q.ta + calcolo
                -- summaryTotale). Nel contesto bundle qty_padre=1 quindi
                -- coeff_qta e quantita_componente coincidono; nei
                -- preventivi/contratti la fn DB ritorna `quantita_componente`
                -- gia' scalato per la quantita padre del documento.
                ac.coeff_qta                       AS quantita_componente,
                ac.obbligatorio,
                ac.esposizione_in_fattura,
                a.iva_id,
                iva.codice                         AS iva_codice,
                iva.aliquota_iva                   AS iva_aliquota,
                a.uom_id,
                um.codice                          AS uom_codice,
                lrc.id                             AS listini_righe_componenti_id,
                -- Alias `prezzo_suggerito` per uniformita' col `ComponentiDialog`
                -- FE che si attende quel campo come valore di pre-populating;
                -- semantica listino: e' il prezzo bundle gia' definito.
                -- Nota: NON proiettare lrc.validita (daterange) perche'
                -- psycopg fallisce su `infinity` ("date too large after year
                -- 10K"). Se servira' al FE, castarla a testo con
                -- `to_char(...)` o estrarre lower/upper come date guardate.
                lrc.prezzo                         AS prezzo_suggerito
              FROM catalogo.articoli_componenti ac
              JOIN catalogo.articoli a            ON a.id = ac.componente_id
              LEFT JOIN catalogo.unita_misura um   ON um.id = a.uom_id
              LEFT JOIN config.iva iva             ON iva.id = a.iva_id
              LEFT JOIN vendite.listini_righe_componenti lrc
                ON lrc.listino_versione_id = %s
               AND lrc.articolo_componente_id = ac.id
               AND lrc.attivo = TRUE
             WHERE ac.prodotto_id = %s
               AND COALESCE(ac.attivo, TRUE) = TRUE
               AND ac.validita @> %s
             ORDER BY a.codice NULLS LAST, ac.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [versione_id, str(articolo_padre_id), data_riferimento])
            return rows_to_list(cursor)

    # Scopo: Batch upsert dei prezzi bundle di un padre composito su
    # `listini_righe_componenti`. Strategia "tabula rasa idempotente":
    #   1. SOFT-DELETE (attivo=FALSE) le righe bundle attive correnti per
    #      (versione, padre) — l'EXCLUDE GIST WHERE attivo=TRUE non si
    #      scontra con quelle disattivate, semplifica la riapplicazione
    #   2. INSERT le nuove righe attive
    # In una transazione atomica per evitare stato intermedio inconsistente.
    #
    # `rows`: lista di dict con chiavi:
    #   - `articolo_componente_id` (UUID, BoM riga)
    #   - `articolo_figlio_id`     (UUID, denorm)
    #   - `prezzo`                 (Decimal)
    #   - `iva_id`                 (int, default = IVA del figlio dal catalogo)
    # `validita`: tuple (date_dal, date_al) o (date_dal, None) per `infinity`
    # Le righe con `prezzo IS NULL` sono ignorate (= "non gestito a bundle").
    def upsert_bundle_componenti(
        self,
        *,
        versione_id: int,
        articolo_padre_id: str,
        rows: list[dict[str, Any]],
        valido_dal: date,
        valido_al: date | None = None,
    ) -> dict[str, int]:
        # Validita' della riga listino_righe_componenti = intersezione fra
        # la validita' della versione listino e la validita' della riga BoM
        # `catalogo.articoli_componenti` referenziata da articolo_componente_id.
        # Calcolata su `valido_dal`/`valido_al`: la colonna `validita` daterange
        # e' STORED generated (PG 18, migration 20260514-04). La temporal FK
        # `fk_listrighe_comp_articoli_comp_temporal` (migration 20260514-12)
        # garantisce il contenimento riga listino ⊆ BoM al posto del guard
        # trigger rimosso con migration 20260514-13.
        #
        # Esempio: versione listino valida `[2026-04-07, infinity]`, BoM del
        # componente valida `[2026-05-13, infinity]` → riga bundle salvata
        # con valido_dal = `2026-05-13`, valido_al = NULL (la BoM e' il limite).
        # Igiene analisi-fix-transazioni: `transaction.atomic()` ESPLICITO qui —
        # prima il commento dichiarava "in una transazione atomica" ma il metodo
        # (soft-delete + N insert su due statement) NON ne apriva alcuna, era
        # protetto solo dal caller. Ora e' self-atomico: o tabula rasa + reinsert
        # completi o rollback (nested = savepoint se il caller avvolge gia').
        with transaction.atomic(), connection.cursor() as cursor:
            # Soft-delete riga attive correnti per la coppia (versione, padre).
            cursor.execute(
                """
                UPDATE vendite.listini_righe_componenti
                   SET attivo = FALSE
                 WHERE listino_versione_id = %s
                   AND articolo_padre_id = %s
                   AND attivo = TRUE
                """,
                [versione_id, str(articolo_padre_id)],
            )
            n_disattivati = cursor.rowcount

            # INSERT nuove righe attive (skip prezzo NULL).
            # Intersezione valido_dal/valido_al con la BoM via CTE:
            #  - valido_dal = GREATEST(ac.valido_dal, requested)
            #  - valido_al  = LEAST(ac.valido_al, requested)
            # `GREATEST`/`LEAST` sono NULL-safe in PG (ignorano i NULL),
            # quindi NULL su uno dei due lati propaga correttamente la
            # semantica "open-ended" (post-fix DB 2026-05-15 il trigger
            # `trgfn_listini_righe_comp_guard_coerenza_bom` coalesce
            # simmetricamente vs STORED su listini_versioni.validita).
            # Guard intersezione vuota: il WHERE finale skippa l'INSERT se
            # `v_dal > v_al` (es. versione [2026-04, 2026-04] vs BoM [2026-05,..]).
            # Senza lo skip la riga arriverebbe al guard comune delle date
            # (`script.trgfn_guard_date_validita`, dal 2026-09-23) con
            # `E_DATA_AL_MINORE_DAL`, e l'intera propagazione fallirebbe per
            # una sola riga fuori periodo. rowcount=0 → log warning + conteggio skippati.
            n_inseriti = 0
            n_skipped_no_overlap = 0
            for r in rows:
                if r.get("prezzo") is None:
                    continue
                cursor.execute(
                    f"""
                    WITH bom AS (
                        SELECT
                            ac.id AS componente_id,
                            ac.valido_dal AS bom_valido_dal,
                            ac.valido_al AS bom_valido_al
                          FROM catalogo.articoli_componenti ac
                         WHERE ac.id = %s::uuid
                    )
                    INSERT INTO vendite.listini_righe_componenti (
                        listino_versione_id,
                        articolo_componente_id,
                        articolo_padre_id,
                        articolo_figlio_id,
                        prezzo,
                        iva_id,
                        valido_dal,
                        valido_al,
                        attivo
                    )
                    SELECT
                        %s,
                        bom.componente_id,
                        %s,
                        %s,
                        %s,
                        %s,
                        GREATEST(bom.bom_valido_dal, %s::date) AS v_dal,
                        LEAST(bom.bom_valido_al, %s::date) AS v_al,
                        TRUE
                      FROM bom
                     WHERE GREATEST(bom.bom_valido_dal, %s::date) <=
                           LEAST(
                               COALESCE(bom.bom_valido_al, {_SQL_DATE_INFINITY}),
                               COALESCE(%s::date, {_SQL_DATE_INFINITY})
                           )
                    """,  # noqa: S608 — costante di modulo _SQL_DATE_INFINITY, valori come parametri
                    [
                        r["articolo_componente_id"],
                        versione_id,
                        str(articolo_padre_id),
                        r["articolo_figlio_id"],
                        r["prezzo"],
                        r.get("iva_id"),
                        valido_dal,
                        valido_al,
                        valido_dal,
                        valido_al,
                    ],
                )
                if cursor.rowcount == 0:
                    n_skipped_no_overlap += 1
                    logger.warning(
                        "listini_righe_componenti.upsert_bundle.skip_no_overlap "
                        "versione_id=%s articolo_padre_id=%s articolo_componente_id=%s "
                        "valido_dal=%s valido_al=%s — intersezione vuota fra "
                        "validita' versione e BoM, riga ignorata.",
                        versione_id, articolo_padre_id, r["articolo_componente_id"],
                        valido_dal, valido_al,
                    )
                else:
                    n_inseriti += cursor.rowcount

            return {
                "disattivati": n_disattivati,
                "inseriti": n_inseriti,
                "skipped_no_overlap": n_skipped_no_overlap,
            }
