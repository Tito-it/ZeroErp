# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository admin per CRUD diretti sulle tabelle dello
#        schema `ui` (Blocco F Fase 1):
#          - ui.lista_definizione   -> read-only (lista per Select header)
#          - ui.lista_preset        -> list / create / update / delete
#          - ui.lista_preset_colonna -> replace atomico composizione preset
#          - ui.lista_colonna       -> read-only (helper composizione preset)
#          - ui.lista_colonna_permesso -> list / upsert / delete
#
#        Logica di dominio nei trigger DB (CHECK ambito_refs, partial
#        UNIQUE is_default). Il repository si limita a marshalling
#        cursor + propagazione IntegrityError al service.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import connection, transaction


# SELECT comune per ui.lista_preset con display fields (profilo accesso +
# emittente fiscale via LEFT JOIN). Riusato da `list_preset_by_lista` e
# `get_preset` per garantire stessa proiezione e ridurre il drift.
# Il `{filter_clause}` viene risolto con uno snippet sicuro (`p.lista_id = %s`
# o `p.id = %s`) — non e' un punto di iniezione perche' viene scelto fra
# stringhe statiche.
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
           ef.descrizione                 AS emittente_fiscale_descrizione,
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
    # ui.lista_definizione - read-only
    # =================================================================

    # Scopo: Lista delle definizioni di lista attive. Usato dall'header
    #        "Lista corrente" della pagina admin per popolare il Select.
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
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

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
            row = cursor.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cursor.description]
            return dict(zip(cols, row))

    # =================================================================
    # ui.lista_colonna - read-only (composizione preset)
    # =================================================================

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
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

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
            cols = [c[0] for c in cursor.description]
            return [
                self._normalize_preset_jsonb(dict(zip(cols, row)))
                for row in cursor.fetchall()
            ]

    # Scopo: Restituisce il preset per id (con display fields), None se
    #        inesistente. Usato dal service per get post-mutazione.
    def get_preset(self, preset_id: int) -> dict[str, Any] | None:
        sql = _PRESET_SELECT_SQL.format(
            extra_select="",
            filter_clause="p.id = %s",
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [preset_id])
            row = cursor.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cursor.description]
            return self._normalize_preset_jsonb(dict(zip(cols, row)))

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

    # Scopo: Aggiorna preset sui soli campi presenti in `data`. Costruisce
    #        SET dinamico per evitare di sovrascrivere campi non passati.
    #        Gli immutabili (lista_id/ambito/profilo/emittente) NON sono
    #        in whitelist update lato service, quindi non arrivano qui.
    def update_preset(
        self,
        preset_id: int,
        data: dict[str, Any],
        user_update: str,
    ) -> bool:
        if not data:
            return False
        sets: list[str] = []
        params: list[Any] = []
        for field in ("codice", "descrizione", "is_default",
                      "pagina_dimensione", "attivo"):
            if field in data:
                sets.append(f"{field} = %s")
                params.append(data[field])
        if "ordinamento_default" in data:
            sets.append("ordinamento_default = %s::jsonb")
            value = data["ordinamento_default"]
            params.append(json.dumps(value) if value is not None else None)
        if "filtri_default" in data:
            sets.append("filtri_default = %s::jsonb")
            value = data["filtri_default"]
            params.append(json.dumps(value) if value is not None else None)
        sets.append("data_update = now()")
        sets.append("user_update = %s")
        params.append(user_update)
        params.append(preset_id)
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE ui.lista_preset SET {', '.join(sets)} WHERE id = %s",
                params,
            )
            return cursor.rowcount > 0

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
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

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
                    """,
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
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

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

    # =================================================================
    # Helpers privati
    # =================================================================

    # Scopo: Normalizza i campi JSONB (`ordinamento_default`,
    #        `filtri_default`) garantendo dict/list anche quando
    #        l'adapter ritorna stringa serializzata.
    @staticmethod
    def _normalize_preset_jsonb(row: dict[str, Any]) -> dict[str, Any]:
        for key in ("ordinamento_default", "filtri_default"):
            value = row.get(key)
            if isinstance(value, str):
                row[key] = json.loads(value)
        return row
