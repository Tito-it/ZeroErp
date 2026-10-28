# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository admin per CRUD diretti sulle tabelle dello
#        schema `ui`:
#        Blocco F Fase 1:
#          - ui.lista_preset        -> list / create / update / delete
#          - ui.lista_preset_colonna -> replace atomico composizione preset
#          - ui.lista_colonna_permesso -> list / upsert / delete
#        Blocco F Fase 2 (DEF-5b):
#          - ui.lista_definizione   -> list / get / create / update / delete
#          - ui.lista_colonna       -> list (esistente) / create / update /
#                                      delete (T2 BE)
#
#        Logica di dominio nei trigger DB (CHECK ambito_refs, partial
#        UNIQUE is_default, valida_vista_sql, valida_campo_sorgente). Il
#        repository si limita a marshalling cursor + propagazione
#        IntegrityError al service.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import connection, transaction

from apps.core.db._helpers import fetchone_scalar, row_to_dict, rows_to_list
from apps.core.db.sql_write_helpers import execute_dynamic_update


# SELECT comune per ui.lista_preset con display fields (profilo accesso +
# emittente fiscale via LEFT JOIN). Riusato da `list_preset_by_lista` e
# `get_preset` per garantire stessa proiezione e ridurre il drift.
# Il `{filter_clause}` viene risolto con uno snippet sicuro (`p.lista_id = %s`
# o `p.id = %s`) — non e' un punto di iniezione perche' viene scelto fra
# stringhe statiche.
# `emittente_ragione_sociale` porta la ragione sociale del SOGGETTO
# dell'emittente, non `emittenti_fiscali.descrizione` (etichetta interna
# divergente, in via di eliminazione — brief
# `brief-emittente-ragione-sociale-dal-soggetto.md`). Alias rinominato il
# 2026-08-03 (era `emittente_fiscale_descrizione`), in pari con viste e seed.
_PRESET_SELECT_SQL = """
    SELECT p.id,
           p.lista_id,
           p.codice,
           p.descrizione,
           p.ambito::text                 AS ambito,
           p.profilo_accesso_id,
           pa.codice                      AS profilo_accesso_codice,
           pa.descrizione                 AS profilo_accesso_descrizione,
           p.emittente_fiscale_id,
           ef.codice                      AS emittente_fiscale_codice,
           s_ef.ragione_sociale_completa  AS emittente_ragione_sociale,
           p.is_default,
           p.pagina_dimensione,
           p.ordinamento_default,
           p.filtri_default,
           p.attivo,
           {extra_select}
           p.data_insert,
           p.user_insert,
           p.data_update,
           p.user_update
      FROM ui.lista_preset                          p
      LEFT JOIN config.profili_accesso              pa
           ON pa.id = p.profilo_accesso_id
      LEFT JOIN anagrafiche.emittenti_fiscali       ef
           ON ef.id = p.emittente_fiscale_id
      LEFT JOIN anagrafiche.soggetti_ruoli          sr_ef
           ON sr_ef.id = ef.soggetto_ruolo_id
      LEFT JOIN anagrafiche.soggetti                s_ef
           ON s_ef.id = sr_ef.soggetto_id
     WHERE {filter_clause}
"""

# Frammento SELECT extra per la lista (conteggio righe composizione).
_PRESET_LIST_EXTRA_SELECT = """
           (SELECT COUNT(*)
              FROM ui.lista_preset_colonna lpc
             WHERE lpc.preset_id = p.id) AS colonne_count,
"""


class UiAdminRepository:
    """Accesso DB per CRUD admin tabelle `ui.*` (Blocco F Fase 1)."""

    # =================================================================
    # ui.lista_definizione - CRUD (Fase 2 DEF-5b)
    # =================================================================

    # SELECT esteso usato dalla pagina tecnica Fase 2: include vista_sql,
    # note, audit. La proiezione "Fase 1" (id/codice/descrizione/schema_dati/
    # attivo) resta esposta da `list_definizioni` come header del select.
    _DEFINIZIONE_SELECT_FULL = """
        SELECT id,
               codice,
               descrizione,
               schema_dati,
               vista_sql,
               note,
               attivo,
               data_insert,
               user_insert,
               data_update,
               user_update
          FROM ui.lista_definizione
    """

    # Scopo: Lista delle definizioni di lista attive. Usato dall'header
    #        "Lista corrente" della pagina admin per popolare il Select
    #        (Fase 1, proiezione minima).
    def list_definizioni(self) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, codice, descrizione, schema_dati, attivo
                  FROM ui.lista_definizione
                 WHERE attivo = TRUE
                 ORDER BY descrizione, id
                """
            )
            return rows_to_list(cursor)

    # Scopo: Lista TUTTE le definizioni (incluse disattivate) con campi
    #        completi per la pagina tecnica Fase 2. Ordinate per
    #        attive-prima poi codice per UX coerente.
    def list_definizioni_admin(self) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                self._DEFINIZIONE_SELECT_FULL
                + " ORDER BY attivo DESC, codice, id"
            )
            return rows_to_list(cursor)

    # Scopo: Conta TUTTE le definizioni (incluse disattivate), con lo stesso
    #        perimetro di `list_definizioni_admin` ma senza passare dalle righe.
    # ⛔ E' una query SEPARATA di proposito, e non un `len()` sul risultato
    #    della lista: il conteggio serve al frontend come ASSERZIONE che le
    #    righe consegnate siano tutte (guard `troncamentoSospetto` di
    #    `<ListaConfigurabile>` in modalita' `paginata: false`). Derivarlo dalle
    #    righe lo renderebbe una tautologia — direbbe sempre di si', anche il
    #    giorno in cui qualcuno mettesse un LIMIT nella SELECT sopra. E'
    #    l'INDIPENDENZA dalle righe a fare il presidio, non il numero.
    # ⚠️ Il perimetro deve restare quello della lista: se un giorno
    #    `list_definizioni_admin` prendesse un filtro, va preso anche qui, o le
    #    due grandezze divergono per un motivo che non e' un troncamento.
    def count_definizioni_admin(self) -> int:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM ui.lista_definizione")
            return int(fetchone_scalar(cursor))

    # Scopo: Restituisce la riga di lista_definizione per id, oppure None
    #        se inesistente o non attivo. Usato per validare l'id passato
    #        dai service admin prima di toccare preset/permessi.
    def get_definizione(self, lista_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, codice, descrizione, schema_dati, attivo
                  FROM ui.lista_definizione
                 WHERE id = %s
                   AND attivo = TRUE
                """,
                [lista_id],
            )
            return row_to_dict(cursor)

    # Scopo: Restituisce la definizione per id (anche disattivate, campi
    #        completi inclusi vista_sql/note/audit). Usato dal service
    #        admin Fase 2 per get post-mutazione e validazione id update/
    #        delete: la pagina tecnica deve poter editare anche record
    #        soft-disabled.
    def get_definizione_admin(
        self, lista_id: int
    ) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                self._DEFINIZIONE_SELECT_FULL + " WHERE id = %s",
                [lista_id],
            )
            return row_to_dict(cursor)

    # Scopo: INSERT lista_definizione. Il trigger
    #        trgfn_ui_lista_definizione_a10_valida_vista_sql verifica
    #        l'esistenza della view in pg_catalog ma skippa se attivo=
    #        FALSE o vista_sql=NULL: il workflow draft "registra prima,
    #        attiva dopo aver creato la view" e' supportato nativamente.
    # 🚫 `multi_emittente` non compare in questo INSERT ne' nella whitelist
    #    `_DEFINIZIONE_UPDATE_COLS` di `update_definizione`, ed e' deliberato: il flag si accende SOLO dal
    #    seed. Il presidio forte e' il trigger DB — la scrittura verrebbe
    #    rifiutata comunque con `E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE` — ma la
    #    colonna non va nominata nemmeno qui, o l'applicazione chiederebbe al
    #    database una cosa che il database le vieta.
    #    Perche' e come: `lista_definizione_admin_service.CREATE_KEYS`.
    def create_definizione(
        self,
        data: dict[str, Any],
        user_insert: str,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ui.lista_definizione (
                    codice,
                    descrizione,
                    schema_dati,
                    vista_sql,
                    note,
                    attivo,
                    user_insert
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                [
                    data["codice"],
                    data["descrizione"],
                    data["schema_dati"],
                    data.get("vista_sql"),
                    data.get("note"),
                    data.get("attivo", True),
                    user_insert,
                ],
            )
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Colonne scrivibili da `update_definizione` (whitelist del BB
    # `execute_dynamic_update`) + `user_update`, l'audit che il repository
    # aggiunge lui stesso. 🚫 `multi_emittente` resta fuori: vedi il
    # commento su `create_definizione`.
    _DEFINIZIONE_UPDATE_COLS: frozenset[str] = frozenset({
        "codice", "descrizione", "schema_dati", "vista_sql", "note", "attivo",
        "user_update",
    })

    # Scopo: UPDATE lista_definizione sui soli campi presenti in `data`.
    #        Il trigger guard verifica vista_sql come per l'INSERT.
    #        SET dinamico via BB `execute_dynamic_update`; `user_update`
    #        viaggia fra i valori (parametro), `data_update = now()` come
    #        `extra_set`. Payload vuoto -> False senza query.
    def update_definizione(
        self,
        lista_id: int,
        data: dict[str, Any],
        user_update: str,
    ) -> bool:
        if not data:
            return False
        return execute_dynamic_update(
            "ui.lista_definizione", lista_id,
            {**data, "user_update": user_update},
            allowed=self._DEFINIZIONE_UPDATE_COLS,
            extra_set="data_update = now()",
        )

    # Scopo: DELETE lista_definizione. Le FK su lista_colonna,
    #        lista_preset e lista_preferenza_utente sono RESTRICT (NO
    #        ACTION default): se la definizione e' in uso il DB solleva
    #        IntegrityError, il service la traduce in E_UI_DEFINIZIONE_
    #        IN_USO. Soft-disable disponibile via update attivo=false.
    def delete_definizione(self, lista_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM ui.lista_definizione WHERE id = %s",
                [lista_id],
            )
            return cursor.rowcount > 0

    # =================================================================
    # ui.lista_colonna - read (Fase 1) + CRUD (Fase 2 DEF-5b)
    # =================================================================

    # SELECT esteso usato dalla pagina tecnica Fase 2: include tutti i
    # campi della tabella (etichetta_i18n_key, formato, allineamento,
    # gruppo, flag comportamento, audit). La proiezione "Fase 1" per la
    # composizione preset resta in `list_colonne_by_lista` (helper FE).
    _COLONNA_SELECT_FULL = """
        SELECT id,
               lista_id,
               codice,
               etichetta,
               etichetta_estesa,
               etichetta_i18n_key,
               campo_sorgente,
               tipo_colonna::text       AS tipo_colonna,
               tipo_dato::text          AS tipo_dato,
               formato,
               larghezza_default,
               ordine_default,
               allineamento::text       AS allineamento,
               gruppo,
               gruppo_ordine,
               filtrabile,
               ordinabile,
               esportabile,
               ricercabile_full,
               sensibile,
               attivo,
               data_insert,
               user_insert,
               data_update,
               user_update
          FROM ui.lista_colonna
    """

    # Scopo: Lista colonne attive di una lista, ordinate per gruppo +
    #        ordine_default. Usato dal sub-drawer composizione preset
    #        per offrire al super-admin il catalogo grezzo (no filtro
    #        permessi: amministrazione tecnica).
    def list_colonne_by_lista(
        self, lista_id: int
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id,
                       codice,
                       etichetta,
                       etichetta_estesa,
                       tipo_colonna::text AS tipo_colonna,
                       tipo_dato::text    AS tipo_dato,
                       gruppo,
                       gruppo_ordine,
                       ordine_default,
                       larghezza_default,
                       attivo
                  FROM ui.lista_colonna
                 WHERE lista_id = %s
                   AND attivo  = TRUE
                 ORDER BY COALESCE(gruppo_ordine, 9999),
                          gruppo NULLS FIRST,
                          ordine_default,
                          id
                """,
                [lista_id],
            )
            return rows_to_list(cursor)

    # Scopo: Lista TUTTE le colonne di una lista (incluse disattivate)
    #        con campi completi per la pagina tecnica Fase 2. Stesso
    #        ordering della Fase 1 ma include disattive in coda.
    def list_colonne_by_lista_admin(
        self, lista_id: int
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                self._COLONNA_SELECT_FULL
                + " WHERE lista_id = %s "
                  " ORDER BY attivo DESC, "
                  "          COALESCE(gruppo_ordine, 9999), "
                  "          gruppo NULLS FIRST, "
                  "          ordine_default, id",
                [lista_id],
            )
            return rows_to_list(cursor)

    # Scopo: Conta le colonne di una lista con lo STESSO perimetro di
    #        `list_colonne_by_lista_admin` (stessa tabella, stesso WHERE),
    #        senza passare dalle righe.
    # ⛔ Query separata, non `len()` sul risultato della lista: vedi la nota
    #    estesa su `count_definizioni_admin`. E' l'indipendenza dalle righe a
    #    fare il presidio, non il numero.
    # ⚠️ Il `WHERE lista_id = %s` deve restare gemello di quello della lista:
    #    se uno dei due prendesse un filtro in piu', le due grandezze
    #    divergerebbero per un motivo che non e' un troncamento.
    def count_colonne_by_lista_admin(self, lista_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM ui.lista_colonna WHERE lista_id = %s",
                [lista_id],
            )
            return int(fetchone_scalar(cursor))

    # Scopo: Restituisce la colonna per id (campi completi, anche
    #        disattivate). Usato dal service admin Fase 2 per get
    #        post-mutazione e validazione id update/delete.
    def get_colonna_admin(
        self, colonna_id: int
    ) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                self._COLONNA_SELECT_FULL + " WHERE id = %s",
                [colonna_id],
            )
            return row_to_dict(cursor)

    # Scopo: INSERT lista_colonna. Il trigger valida_campo_sorgente
    #        verifica esistenza dell'attributo nella vista_sql della
    #        lista padre, ma skippa per tipo_colonna='azione' o
    #        campo_sorgente NULL. Defaults applicativi su filtrabile/
    #        ordinabile/esportabile vengono passati esplicitamente per
    #        chiarezza (anche se la tabella ha default DDL).
    def create_colonna(
        self,
        data: dict[str, Any],
        user_insert: str,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ui.lista_colonna (
                    lista_id,
                    codice,
                    etichetta,
                    etichetta_estesa,
                    etichetta_i18n_key,
                    campo_sorgente,
                    tipo_colonna,
                    tipo_dato,
                    formato,
                    larghezza_default,
                    ordine_default,
                    allineamento,
                    gruppo,
                    gruppo_ordine,
                    filtrabile,
                    ordinabile,
                    esportabile,
                    ricercabile_full,
                    sensibile,
                    attivo,
                    user_insert
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s::ui.tipo_colonna,
                    %s::ui.tipo_dato,
                    %s, %s, %s,
                    %s::ui.allineamento_colonna,
                    %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s
                )
                RETURNING id
                """,
                [
                    data["lista_id"],
                    data["codice"],
                    data["etichetta"],
                    data.get("etichetta_estesa"),
                    data.get("etichetta_i18n_key"),
                    data.get("campo_sorgente"),
                    data["tipo_colonna"],
                    data["tipo_dato"],
                    data.get("formato"),
                    data.get("larghezza_default"),
                    data["ordine_default"],
                    data.get("allineamento", "left"),
                    data.get("gruppo"),
                    data.get("gruppo_ordine"),
                    data.get("filtrabile", True),
                    data.get("ordinabile", True),
                    data.get("esportabile", True),
                    data.get("ricercabile_full", False),
                    data.get("sensibile", False),
                    data.get("attivo", True),
                    user_insert,
                ],
            )
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Colonne scrivibili da `update_colonna` (whitelist RIGIDA del BB
    # `execute_dynamic_update`) + `user_update`, l'audit che il repository
    # aggiunge lui stesso. `lista_id` resta fuori: e' immutabile.
    _COLONNA_UPDATE_COLS: frozenset[str] = frozenset({
        "codice", "etichetta", "etichetta_estesa", "etichetta_i18n_key",
        "campo_sorgente", "tipo_colonna", "tipo_dato", "formato",
        "larghezza_default", "ordine_default", "allineamento", "gruppo",
        "gruppo_ordine", "filtrabile", "ordinabile", "esportabile",
        "ricercabile_full", "sensibile", "attivo", "user_update",
    })
    # I tre enum della tabella: il valore arriva come testo e va castato.
    _COLONNA_CASTS: dict[str, str] = {
        "tipo_colonna": "ui.tipo_colonna",
        "tipo_dato": "ui.tipo_dato",
        "allineamento": "ui.allineamento_colonna",
    }

    # Scopo: UPDATE lista_colonna sui soli campi presenti in `data`.
    #        Il trigger guard ricontrolla campo_sorgente come per
    #        l'INSERT. lista_id NON e' aggiornabile (nel service e'
    #        immutabile), per spostare una colonna serve cancellarla e
    #        ricrearla. SET dinamico via BB `execute_dynamic_update` (con
    #        `casts` per gli enum, 2026-09-26: prima era un SET scritto a mano
    #        che scartava in silenzio le chiavi fuori elenco); `user_update`
    #        fra i valori, `data_update = now()` come `extra_set`.
    #        Payload vuoto -> False senza query.
    def update_colonna(
        self,
        colonna_id: int,
        data: dict[str, Any],
        user_update: str,
    ) -> bool:
        if not data:
            return False
        return execute_dynamic_update(
            "ui.lista_colonna", colonna_id,
            {**data, "user_update": user_update},
            allowed=self._COLONNA_UPDATE_COLS,
            casts=self._COLONNA_CASTS,
            extra_set="data_update = now()",
        )

    # Scopo: DELETE lista_colonna. Le FK su lista_preset_colonna e
    #        lista_colonna_permesso hanno ON DELETE CASCADE: vengono
    #        ripulite automaticamente. Le preferenze utente referenziano
    #        per CODICE colonna nel JSONB `configurazione->colonne` e
    #        non hanno FK: il service esegue prima un soft-block via
    #        `count_preferenze_referenced_by_colonna` per evitare
    #        configurazioni stale silenziose.
    def delete_colonna(self, colonna_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM ui.lista_colonna WHERE id = %s",
                [colonna_id],
            )
            return cursor.rowcount > 0

    # Scopo: Conta le preferenze utente che referenziano la colonna nel
    #        JSONB `configurazione->colonne`. Il match e' per `codice`
    #        (le preferenze non memorizzano l'id colonna, ma il codice
    #        stabile cross-environment) e per `lista_id` (la struttura
    #        e' per lista). Usato dal soft-block DELETE.
    def count_preferenze_referenced_by_colonna(
        self,
        lista_id: int,
        codice: str,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                  FROM ui.lista_preferenza_utente lpu
                 WHERE lpu.lista_id = %s
                   AND EXISTS (
                       SELECT 1
                         FROM jsonb_array_elements(
                              COALESCE(lpu.configurazione->'colonne',
                                       '[]'::jsonb)
                         ) AS elem
                        WHERE elem->>'codice' = %s
                   )
                """,
                [lista_id, codice],
            )
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # =================================================================
    # ui.lista_preset - CRUD
    # =================================================================

    # Scopo: Lista preset di una lista, ordinati per ambito poi codice.
    #        Include join con profili_accesso e emittenti_fiscali per
    #        display fields (codice/descrizione) — pattern display-fields
    #        backend. Conteggio righe composizione per UX (badge
    #        "n colonne" nella DataTable).
    def list_preset_by_lista(
        self, lista_id: int
    ) -> list[dict[str, Any]]:
        sql = _PRESET_SELECT_SQL.format(
            extra_select=_PRESET_LIST_EXTRA_SELECT,
            filter_clause="p.lista_id = %s",
        ) + " ORDER BY p.ambito, p.codice, p.id"
        with connection.cursor() as cursor:
            cursor.execute(sql, [lista_id])
            return rows_to_list(cursor)

    # Scopo: Conta i preset di una lista con lo STESSO perimetro di
    #        `list_preset_by_lista` (`p.lista_id = %s`), senza passare dalle
    #        righe. ⛔ Query separata, non `len()`: vedi `count_definizioni_admin`.
    # ⚠️ La lista passa da `_PRESET_SELECT_SQL`, che ha dei LEFT JOIN per i
    #    display field: sono LEFT apposta, quindi non tolgono righe e il
    #    `count` sulla sola tabella e' l'equivalente esatto. Se uno di quei
    #    JOIN diventasse INNER, questo conteggio andrebbe rifatto con lo
    #    stesso FROM — o direbbe piu' righe di quante la lista ne consegna.
    def count_preset_by_lista(self, lista_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM ui.lista_preset p WHERE p.lista_id = %s",
                [lista_id],
            )
            return int(fetchone_scalar(cursor))

    # Scopo: Restituisce il preset per id (con display fields), None se
    #        inesistente. Usato dal service per get post-mutazione.
    def get_preset(self, preset_id: int) -> dict[str, Any] | None:
        sql = _PRESET_SELECT_SQL.format(
            extra_select="",
            filter_clause="p.id = %s",
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [preset_id])
            return row_to_dict(cursor)

    # Scopo: Crea preset (testata). I campi `lista_id`/`ambito`/refs sono
    #        obbligatori e validati dal service; FK + CHECK ambito_refs
    #        sono enforced lato DB (IntegrityError -> mapping service).
    #        `user_insert` derivato dall'utente autenticato.
    def create_preset(
        self,
        data: dict[str, Any],
        user_insert: str,
    ) -> int:
        ordinamento_default = data.get("ordinamento_default")
        filtri_default = data.get("filtri_default")
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ui.lista_preset (
                    lista_id,
                    codice,
                    descrizione,
                    ambito,
                    profilo_accesso_id,
                    emittente_fiscale_id,
                    is_default,
                    pagina_dimensione,
                    ordinamento_default,
                    filtri_default,
                    attivo,
                    user_insert
                )
                VALUES (
                    %s, %s, %s, %s::ui.ambito_preset,
                    %s, %s,
                    %s, %s,
                    %s::jsonb, %s::jsonb,
                    %s, %s
                )
                RETURNING id
                """,
                [
                    data["lista_id"],
                    data["codice"],
                    data["descrizione"],
                    data["ambito"],
                    data.get("profilo_accesso_id"),
                    data.get("emittente_fiscale_id"),
                    data.get("is_default", False),
                    data.get("pagina_dimensione"),
                    json.dumps(ordinamento_default) if ordinamento_default is not None else None,
                    json.dumps(filtri_default) if filtri_default is not None else None,
                    data.get("attivo", True),
                    user_insert,
                ],
            )
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Colonne scrivibili da `update_preset` (whitelist del BB) +
    # `user_update` aggiunto dal repository. Gli immutabili (lista_id/
    # ambito/profilo/emittente) restano fuori anche qui.
    _PRESET_UPDATE_COLS: frozenset[str] = frozenset({
        "codice", "descrizione", "is_default", "pagina_dimensione",
        "ordinamento_default", "filtri_default", "attivo", "user_update",
    })

    # Scopo: Aggiorna preset sui soli campi presenti in `data`. SET
    #        dinamico via BB `execute_dynamic_update`: i JSONB
    #        `ordinamento_default` (lista) / `filtri_default` (oggetto) vanno
    #        a `::jsonb` dal BB, None azzera. Gli immutabili (lista_id/
    #        ambito/profilo/emittente) NON sono in whitelist update lato
    #        service, quindi non arrivano qui.
    def update_preset(
        self,
        preset_id: int,
        data: dict[str, Any],
        user_update: str,
    ) -> bool:
        if not data:
            return False
        return execute_dynamic_update(
            "ui.lista_preset", preset_id,
            {**data, "user_update": user_update},
            allowed=self._PRESET_UPDATE_COLS,
            extra_set="data_update = now()",
        )

    # Scopo: Cancella preset per id. Le FK su lista_preferenza_utente
    #        hanno ON DELETE SET NULL (DB-2 landed): la preferenza
    #        utente sopravvive con preset_base_id NULL. La FK su
    #        lista_preset_colonna ha CASCADE.
    def delete_preset(self, preset_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM ui.lista_preset WHERE id = %s",
                [preset_id],
            )
            return cursor.rowcount > 0

    # =================================================================
    # ui.lista_preset_colonna - composizione (replace atomico)
    # =================================================================

    # Scopo: Restituisce la composizione del preset (lista colonne con
    #        flag visibilita'/larghezza/ordine). Include codice +
    #        etichetta per display: il FE non deve fare lookup separato.
    def list_preset_colonne(self, preset_id: int) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT lpc.preset_id,
                       lpc.colonna_id,
                       lc.codice,
                       lc.etichetta,
                       lc.tipo_colonna::text AS tipo_colonna,
                       lpc.ordine,
                       lpc.larghezza,
                       lpc.visibile,
                       lpc.fissata
                  FROM ui.lista_preset_colonna lpc
                  JOIN ui.lista_colonna       lc ON lc.id = lpc.colonna_id
                 WHERE lpc.preset_id = %s
                 ORDER BY lpc.ordine, lc.id
                """,
                [preset_id],
            )
            return rows_to_list(cursor)

    # Scopo: REPLACE atomico della composizione di un preset. Cancella
    #        tutte le righe esistenti e re-inserisce quelle del payload
    #        in transazione. Pattern coerente con altri PUT-replace
    #        (es. ruoli_anagrafici). Le FK e PK garantiscono l'integrita'.
    def replace_preset_colonne(
        self,
        preset_id: int,
        rows: list[dict[str, Any]],
    ) -> int:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM ui.lista_preset_colonna "
                    "WHERE preset_id = %s",
                    [preset_id],
                )
                if not rows:
                    return 0
                # Costruzione VALUES dinamico per single-shot.
                args: list[Any] = []
                placeholders: list[str] = []
                for r in rows:
                    placeholders.append("(%s, %s, %s, %s, %s, %s)")
                    args.extend([
                        preset_id,
                        r["colonna_id"],
                        r["ordine"],
                        r.get("larghezza"),
                        r.get("visibile", True),
                        r.get("fissata", False),
                    ])
                cursor.execute(
                    f"""
                    INSERT INTO ui.lista_preset_colonna (
                        preset_id, colonna_id, ordine, larghezza,
                        visibile, fissata
                    ) VALUES {", ".join(placeholders)}
                    """,  # noqa: S608 — VALUES solo segnaposto %s generati, valori come parametri
                    args,
                )
                return len(rows)

    # =================================================================
    # ui.lista_colonna_permesso - permessi colonna (UPSERT/DELETE)
    # =================================================================

    # Scopo: Lista permessi colonna di una lista. Join con lista_colonna
    #        per filtrare per lista e con profili_accesso per display.
    def list_permessi_by_lista(
        self, lista_id: int
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT lcp.id,
                       lcp.colonna_id,
                       lc.codice                      AS colonna_codice,
                       lc.etichetta                   AS colonna_etichetta,
                       lc.gruppo                      AS colonna_gruppo,
                       lcp.profilo_accesso_id,
                       pa.codice                      AS profilo_accesso_codice,
                       pa.descrizione                 AS profilo_accesso_descrizione,
                       lcp.livello_accesso::text      AS livello_accesso,
                       lcp.data_insert,
                       lcp.user_insert,
                       lcp.data_update,
                       lcp.user_update
                  FROM ui.lista_colonna_permesso lcp
                  JOIN ui.lista_colonna          lc ON lc.id = lcp.colonna_id
                  JOIN config.profili_accesso    pa ON pa.id = lcp.profilo_accesso_id
                 WHERE lc.lista_id = %s
                 ORDER BY lc.ordine_default, lc.codice, pa.codice, lcp.id
                """,
                [lista_id],
            )
            return rows_to_list(cursor)

    # Scopo: Conta i permessi di una lista con lo STESSO perimetro di
    #        `list_permessi_by_lista`, senza passare dalle righe.
    # ⛔ Query separata, non `len()`: vedi `count_definizioni_admin`.
    # ⭐ Qui il FROM e' RIPETUTO per intero, JOIN compresi, e non e' pigrizia:
    #    quelli di `list_permessi_by_lista` sono INNER, quindi POSSONO togliere
    #    righe. Un `count(*)` sulla sola `lista_colonna_permesso` conterebbe
    #    anche i permessi che i JOIN scartano, direbbe un numero piu' grande di
    #    quello che la lista consegna, e farebbe scattare il guard
    #    anti-troncamento su un troncamento che non c'e'. Il conteggio dev'essere
    #    indipendente dalle RIGHE, non dal PERIMETRO.
    def count_permessi_by_lista(self, lista_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT count(*)
                  FROM ui.lista_colonna_permesso lcp
                  JOIN ui.lista_colonna          lc ON lc.id = lcp.colonna_id
                  JOIN config.profili_accesso    pa ON pa.id = lcp.profilo_accesso_id
                 WHERE lc.lista_id = %s
                """,
                [lista_id],
            )
            return int(fetchone_scalar(cursor))

    # Scopo: UPSERT permesso colonna su (colonna_id, profilo_accesso_id).
    #        Vincolo UNIQUE garantisce 1 sola riga per coppia. Ritorna
    #        l'id (nuovo o aggiornato).
    def upsert_permesso(
        self,
        colonna_id: int,
        profilo_accesso_id: int,
        livello_accesso: str,
        user_insert: str,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ui.lista_colonna_permesso (
                    colonna_id,
                    profilo_accesso_id,
                    livello_accesso,
                    user_insert
                )
                VALUES (%s, %s, %s::config.livello_accesso, %s)
                ON CONFLICT ON CONSTRAINT uq_ui_lista_colonna_permesso_col_profilo
                DO UPDATE
                   SET livello_accesso = EXCLUDED.livello_accesso,
                       data_update     = now(),
                       user_update     = EXCLUDED.user_insert
                RETURNING id
                """,
                [
                    colonna_id,
                    profilo_accesso_id,
                    livello_accesso,
                    user_insert,
                ],
            )
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Cancella permesso per id. Ritorna True se ha eliminato la
    #        riga, False se non esisteva. Idempotente.
    def delete_permesso(self, permesso_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM ui.lista_colonna_permesso WHERE id = %s",
                [permesso_id],
            )
            return cursor.rowcount > 0
