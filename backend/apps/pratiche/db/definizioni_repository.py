# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso in LETTURA alle edizioni di workflow versionate
#        (pratiche.workflow_definizioni) + drift (vw_definizioni_drift),
#        per la UI admin (Fase 2 Slice 1a). Letture gia' sbloccate a DB
#        (GRANT SELECT). Le azioni write (fork/nuova-versione/pubblica)
#        arrivano in lockstep con la conversione SECURITY DEFINER delle fn
#        DB — vedi brief-db-accesso-be-definizioni-workflow.md §P1.
# ------------------------------------------------------------
from __future__ import annotations

from typing import Any, NamedTuple

from django.db import connection

# Campi "core" di uno step editabili in Slice 2 anello 3 — UNICA fonte di verità
# condivisa da repository (build SQL) e service (clean payload), così i due layer
# non possono divergere. Gli enum/default vivono nei CHECK/DEFAULT DB, non qui.
STEP_CORE_FIELDS: tuple[str, ...] = (
    "codice", "descrizione", "sequenza", "obbligatorio",
    "direzione", "modalita_esito", "esito_default",
)


class ChildSpec(NamedTuple):
    """Descrittore di un tipo di figlio per-nodo di uno step (Slice 2 anello 4).
    `table` = tabella; `writable` = colonne scrivibili dal client (oltre a
    template_flusso_id, imposto dal BE); `required` = sottoinsieme obbligatorio
    (per un 400 parlante prima del NOT NULL DB)."""
    table: str
    writable: tuple[str, ...]
    required: tuple[str, ...]


# Registro dei figli per-nodo editabili — UNICA fonte condivisa repo↔service. La
# chiave (child_kind) arriva SEMPRE dalla urlconf (allowlist fissa), mai da input
# utente → i nomi tabella/colonna nella SQL dinamica sono sicuri. Enum/FK/NOT NULL
# restano validati dai constraint DB, non duplicati qui.
CHILD_SPECS: dict[str, ChildSpec] = {
    "canali": ChildSpec(
        "pratiche.template_flussi_canali",
        ("canale_id", "attivo"),
        ("canale_id",),
    ),
    "handler_eventi": ChildSpec(
        "pratiche.template_flussi_handler_eventi",
        ("evento", "esito_richiesto", "handler_id", "sequenza", "attivo"),
        ("evento", "handler_id"),
    ),
    "competenze": ChildSpec(
        "pratiche.competenze_flussi",
        ("unita_organizzativa_id", "risorsa_umana_id", "attivo"),
        ("unita_organizzativa_id", "risorsa_umana_id"),
    ),
}


class EdgeSpec(NamedTuple):
    """Descrittore di un arco del grafo (Slice 2 anello 5). Gli archi collegano
    due step. `anchor_col` = FK allo step "proprietario", usata per lo scoping
    ownership alla definizione (join a template_flussi). `in_def_cols` = FK che
    DEVONO puntare a step della stessa definizione (validate in create).
    `tipo_col` = colonna NOT NULL impostata dal BE = tipo della definizione."""
    table: str
    writable: tuple[str, ...]
    required: tuple[str, ...]
    anchor_col: str
    in_def_cols: tuple[str, ...]
    tipo_col: str | None


# Registro archi editabili — UNICA fonte condivisa repo↔service. `edge_kind` dalla
# urlconf (allowlist fissa) → SQL dinamica sicura. `regole_generazione` ha il dest
# potenzialmente cross-edizione: solo l'origine è validata in-definizione.
EDGE_SPECS: dict[str, EdgeSpec] = {
    "prerequisiti": EdgeSpec(
        "pratiche.template_flussi_prerequisiti",
        ("template_flusso_id", "prerequisito_id", "esito_richiesto"),
        ("template_flusso_id", "prerequisito_id"),
        "template_flusso_id",
        ("template_flusso_id", "prerequisito_id"),
        None,
    ),
    "formule_tempo": EdgeSpec(
        "pratiche.formule_tempo",
        ("template_flusso_da_id", "template_flusso_a_id", "giorni_esecuzione",
         "giorni_warning", "giorni_critico", "attivo", "descrizione"),
        ("template_flusso_da_id", "template_flusso_a_id",
         "giorni_esecuzione", "giorni_warning", "giorni_critico"),
        "template_flusso_da_id",
        ("template_flusso_da_id", "template_flusso_a_id"),
        "tipo_prestazione_id",
    ),
    "regole_generazione": EdgeSpec(
        "pratiche.regole_generazione",
        ("template_flusso_origine_id", "template_flusso_dest_id",
         "tipo_prestazione_dest_id", "esito_richiesto", "auto", "attivo", "descrizione"),
        ("template_flusso_origine_id", "tipo_prestazione_dest_id"),
        "template_flusso_origine_id",
        ("template_flusso_origine_id",),
        None,
    ),
}


class DefinizioniRepository:
    """Accesso alle edizioni di workflow versionate: lettura (lista/dettaglio +
    figli/archi), editing strutturale della BOZZA (step) e azioni ciclo di vita
    (wrapper sulle fn DB). L'immutabilità delle edizioni emesse è enforce dai guard
    DB, non qui."""

    # SELECT condiviso lista↔dettaglio (header edizione + drift): una sola fonte,
    # così le due letture non possono divergere sulle colonne. Le clausole
    # WHERE/ORDER BY le aggiunge il metodo chiamante.
    _DEFINIZIONE_SELECT = """
        SELECT
            wd.id,
            wd.tipo_prestazione_id,
            tp.descrizione                       AS tipo_prestazione_descrizione,
            wd.emittente_fiscale_id,
            ef.descrizione                       AS emittente_display,
            wd.versione,
            wd.stato,
            wd.descrizione,
            wd.preset_origine_id,
            wd.versione_origine,
            drift.versioni_indietro,
            drift.preset_corrente_id,
            drift.versione_preset_corrente
        FROM pratiche.workflow_definizioni wd
        JOIN pratiche.tipi_prestazione tp ON tp.id = wd.tipo_prestazione_id
        LEFT JOIN anagrafiche.emittenti_fiscali ef ON ef.id = wd.emittente_fiscale_id
        LEFT JOIN pratiche.vw_definizioni_drift drift ON drift.definizione_id = wd.id
    """

    # Scopo: helper interno — esegue una SELECT e ritorna list[dict].
    def _rows(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Scopo: elenco edizioni per (tipo [, emittente]) con drift. Preset =
    # emittente_fiscale_id NULL; il drift e' valorizzato solo per le edizioni
    # forkate (vista vuota finche' non esistono fork → LEFT JOIN → NULL).
    def list_definizioni(
        self,
        *,
        tipo_prestazione_id: int | None = None,
        emittente_fiscale_id: int | None = None,
    ) -> list[dict[str, Any]]:
        return self._rows(
            self._DEFINIZIONE_SELECT + """
            WHERE (%(tipo)s IS NULL OR wd.tipo_prestazione_id = %(tipo)s)
              AND (%(emittente)s IS NULL OR wd.emittente_fiscale_id = %(emittente)s)
            ORDER BY wd.tipo_prestazione_id,
                     wd.emittente_fiscale_id NULLS FIRST,
                     wd.versione DESC,
                     wd.id
            """,
            {"tipo": tipo_prestazione_id, "emittente": emittente_fiscale_id},
        )

    # Scopo: header singolo di un'edizione per id (stessi campi della lista, drift
    # incluso) per il dettaglio editing (Slice 2). None se l'id non esiste.
    def get_definizione(self, definizione_id: int) -> dict[str, Any] | None:
        rows = self._rows(
            self._DEFINIZIONE_SELECT + " WHERE wd.id = %(id)s",
            {"id": definizione_id},
        )
        return rows[0] if rows else None

    # Scopo: step (template_flussi) di un'edizione, in ordine di sequenza, con i
    # display fields via JOIN (azione UI + handler key). Base del dettaglio editing
    # (Slice 2 anello 1). I figli per-nodo (canali/handler_eventi/competenze) e gli
    # archi (prerequisiti/formule/regole) arrivano negli anelli successivi.
    def list_steps_definizione(self, definizione_id: int) -> list[dict[str, Any]]:
        return self._rows(
            """
            SELECT
                tf.id, tf.codice, tf.descrizione, tf.sequenza, tf.obbligatorio,
                tf.direzione, tf.attivo, tf.modalita_esito, tf.esito_default,
                tf.chiude_pratica, tf.ripetibilita, tf.azione_ui_id,
                au.azione_ui_key, tf.handler_id, hf.handler_key,
                (tf.handler_id IS NOT NULL)          AS has_handler
            FROM pratiche.template_flussi tf
            LEFT JOIN pratiche.azioni_ui au      ON au.id = tf.azione_ui_id
            LEFT JOIN pratiche.handler_flussi hf ON hf.id = tf.handler_id
            WHERE tf.definizione_id = %(id)s
            ORDER BY tf.sequenza, tf.id
            """,
            {"id": definizione_id},
        )

    # --- Figli per-nodo di un'edizione (Slice 2 anello 2) ---------------------
    # Tutti i figli/archi di una definizione in una query per tipo (no N+1); il
    # service li annida per step. Scoping via JOIN a template_flussi sul lato "nodo".

    # Scopo: canali per step (display via config.canali_pratiche).
    def list_canali_definizione(self, definizione_id: int) -> list[dict[str, Any]]:
        return self._rows(
            """
            SELECT tfc.id, tfc.template_flusso_id, tfc.canale_id, tfc.attivo,
                   cp.codice AS canale_codice, cp.descrizione AS canale_descrizione,
                   cp.codice_interno AS canale_codice_interno
            FROM pratiche.template_flussi_canali tfc
            JOIN pratiche.template_flussi tf ON tf.id = tfc.template_flusso_id
            LEFT JOIN config.canali_pratiche cp ON cp.id = tfc.canale_id
            WHERE tf.definizione_id = %(id)s
            ORDER BY tfc.template_flusso_id, cp.codice
            """,
            {"id": definizione_id},
        )

    # Scopo: handler-eventi per step (display via handler_flussi). handler_params
    # (jsonb) escluso qui: config di dettaglio, arriva con l'anello di editing dedicato.
    def list_handler_eventi_definizione(self, definizione_id: int) -> list[dict[str, Any]]:
        return self._rows(
            """
            SELECT tfhe.id, tfhe.template_flusso_id, tfhe.evento, tfhe.esito_richiesto,
                   tfhe.handler_id, hf.handler_key, tfhe.sequenza, tfhe.attivo
            FROM pratiche.template_flussi_handler_eventi tfhe
            JOIN pratiche.template_flussi tf ON tf.id = tfhe.template_flusso_id
            LEFT JOIN pratiche.handler_flussi hf ON hf.id = tfhe.handler_id
            WHERE tf.definizione_id = %(id)s
            ORDER BY tfhe.template_flusso_id, tfhe.sequenza, tfhe.id
            """,
            {"id": definizione_id},
        )

    # Scopo: competenze per step (display unità + risorsa umana).
    def list_competenze_definizione(self, definizione_id: int) -> list[dict[str, Any]]:
        return self._rows(
            """
            SELECT cf.id, cf.template_flusso_id, cf.unita_organizzativa_id,
                   cf.risorsa_umana_id, cf.attivo,
                   uo.descrizione AS unita_organizzativa_descrizione,
                   sog.ragione_sociale_completa AS risorsa_umana_display
            FROM pratiche.competenze_flussi cf
            JOIN pratiche.template_flussi tf ON tf.id = cf.template_flusso_id
            LEFT JOIN config.unita_organizzative uo ON uo.id = cf.unita_organizzativa_id
            LEFT JOIN anagrafiche.risorse_umane ru ON ru.id = cf.risorsa_umana_id
            LEFT JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ru.soggetto_ruolo_id
            LEFT JOIN anagrafiche.soggetti sog ON sog.id = sr.soggetto_id
            WHERE tf.definizione_id = %(id)s
            ORDER BY cf.template_flusso_id, uo.descrizione
            """,
            {"id": definizione_id},
        )

    # --- Archi (grafo) di un'edizione (Slice 2 anello 2) ----------------------
    # Riferiscono step per id; il FE mappa a codice via l'array steps dello stesso
    # payload (nessun self-join per il display, endpoint intra-definizione).

    # Scopo: prerequisiti (arco step→prerequisito, esito richiesto), scope via il nodo.
    def list_prerequisiti_definizione(self, definizione_id: int) -> list[dict[str, Any]]:
        return self._rows(
            """
            SELECT tfp.id, tfp.template_flusso_id, tfp.prerequisito_id, tfp.esito_richiesto
            FROM pratiche.template_flussi_prerequisiti tfp
            JOIN pratiche.template_flussi tf ON tf.id = tfp.template_flusso_id
            WHERE tf.definizione_id = %(id)s
            ORDER BY tfp.template_flusso_id, tfp.prerequisito_id
            """,
            {"id": definizione_id},
        )

    # Scopo: formule tempo (arco da→a con soglie giorni), scope via il nodo "da".
    def list_formule_tempo_definizione(self, definizione_id: int) -> list[dict[str, Any]]:
        return self._rows(
            """
            SELECT ft.id, ft.template_flusso_da_id, ft.template_flusso_a_id,
                   ft.giorni_esecuzione, ft.giorni_warning, ft.giorni_critico,
                   ft.attivo, ft.descrizione
            FROM pratiche.formule_tempo ft
            JOIN pratiche.template_flussi tf ON tf.id = ft.template_flusso_da_id
            WHERE tf.definizione_id = %(id)s
            ORDER BY ft.template_flusso_da_id, ft.template_flusso_a_id
            """,
            {"id": definizione_id},
        )

    # Scopo: regole generazione (arco origine→dest cross-pratica), scope via il
    # nodo "origine". Il dest puo' appartenere a un'altra edizione/tipo (id grezzi).
    def list_regole_generazione_definizione(self, definizione_id: int) -> list[dict[str, Any]]:
        return self._rows(
            """
            SELECT rg.id, rg.template_flusso_origine_id, rg.template_flusso_dest_id,
                   rg.tipo_prestazione_dest_id, rg.esito_richiesto, rg.auto,
                   rg.attivo, rg.descrizione
            FROM pratiche.regole_generazione rg
            JOIN pratiche.template_flussi tf ON tf.id = rg.template_flusso_origine_id
            WHERE tf.definizione_id = %(id)s
            ORDER BY rg.template_flusso_origine_id, rg.template_flusso_dest_id
            """,
            {"id": definizione_id},
        )

    # --- Write step su BOZZA (Slice 2 anello 3) -------------------------------
    # DML diretta su template_flussi; l'immutabilita' (edizione per-emittente gia'
    # emessa) e' garantita dai guard DB (514), non da logica Python. Solo i campi
    # STEP_CORE_FIELDS per questo giro; handler/azione_ui/chiude_pratica in un anello
    # dopo. I nomi colonna nell'SQL vengono SEMPRE da STEP_CORE_FIELDS (allowlist
    # fissa) — mai da input utente — quindi la costruzione dinamica è sicura.

    # Scopo: crea uno step nella BOZZA. definizione_id + tipo_prestazione_id
    # SEMPRE espliciti (il trigger di default non deve re-parentare al preset).
    def create_step(
        self, definizione_id: int, tipo_prestazione_id: int, data: dict[str, Any],
    ) -> int:
        cols = ["definizione_id", "tipo_prestazione_id"]
        vals: dict[str, Any] = {
            "definizione_id": definizione_id,
            "tipo_prestazione_id": tipo_prestazione_id,
        }
        for k in STEP_CORE_FIELDS:
            if k in data:
                cols.append(k)
                vals[k] = data[k]
        placeholders = ", ".join(f"%({c})s" for c in cols)
        sql = (
            f"INSERT INTO pratiche.template_flussi ({', '.join(cols)}) "
            f"VALUES ({placeholders}) RETURNING id"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return int(cursor.fetchone()[0])

    # Scopo: aggiorna i campi core di uno step, scoping su (id, definizione_id)
    # per ownership atomica. Ritorna il numero di righe toccate (0 = non nello scope
    # → 404 lato service). Precondizione (garantita dal service): `data` contiene
    # almeno un campo core; violarla è un errore di programmazione, non un no-op.
    def update_step(
        self, definizione_id: int, step_id: int, data: dict[str, Any],
    ) -> int:
        sets = [f"{k} = %({k})s" for k in STEP_CORE_FIELDS if k in data]
        if not sets:
            raise ValueError("update_step richiede almeno un campo core in `data`")
        vals: dict[str, Any] = {k: data[k] for k in STEP_CORE_FIELDS if k in data}
        vals["id"] = step_id
        vals["definizione_id"] = definizione_id
        sql = (
            f"UPDATE pratiche.template_flussi SET {', '.join(sets)} "
            f"WHERE id = %(id)s AND definizione_id = %(definizione_id)s"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return cursor.rowcount

    # Scopo: hard DELETE di uno step (BOZZA senza pratiche pinnate). Scoping su
    # (id, definizione_id). Ritorna il numero di righe cancellate.
    def delete_step(self, definizione_id: int, step_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM pratiche.template_flussi "
                "WHERE id = %(id)s AND definizione_id = %(definizione_id)s",
                {"id": step_id, "definizione_id": definizione_id},
            )
            return cursor.rowcount

    # --- Write figli per-nodo su BOZZA (Slice 2 anello 4) ---------------------
    # CRUD generico dei figli (canali/handler_eventi/competenze) parametrizzato da
    # CHILD_SPECS. Ownership doppia riga→step→definizione via JOIN a template_flussi;
    # l'immutabilità (edizione emessa) è enforce dal guard figli DB (514).

    # Scopo: True se lo step appartiene alla definizione (ownership pre-insert).
    def step_in_definizione(self, definizione_id: int, step_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pratiche.template_flussi "
                "WHERE id = %s AND definizione_id = %s",
                [step_id, definizione_id],
            )
            return cursor.fetchone() is not None

    # Scopo: crea un figlio sotto lo step. template_flusso_id imposto dal BE.
    def create_child(self, child_kind: str, step_id: int, data: dict[str, Any]) -> int:
        spec = CHILD_SPECS[child_kind]
        cols = ["template_flusso_id"] + [c for c in spec.writable if c in data]
        vals: dict[str, Any] = {"template_flusso_id": step_id}
        vals.update({c: data[c] for c in spec.writable if c in data})
        placeholders = ", ".join(f"%({c})s" for c in cols)
        sql = (
            f"INSERT INTO {spec.table} ({', '.join(cols)}) "
            f"VALUES ({placeholders}) RETURNING id"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return int(cursor.fetchone()[0])

    # Scopo: aggiorna un figlio, scoping (row, step, definizione) via JOIN. Ritorna
    # le righe toccate (0 = fuori scope → 404 lato service).
    def update_child(
        self, child_kind: str, definizione_id: int, step_id: int, row_id: int,
        data: dict[str, Any],
    ) -> int:
        spec = CHILD_SPECS[child_kind]
        sets = [f"{c} = %({c})s" for c in spec.writable if c in data]
        if not sets:
            raise ValueError("update_child richiede almeno un campo scrivibile in `data`")
        vals: dict[str, Any] = {c: data[c] for c in spec.writable if c in data}
        vals.update({"row_id": row_id, "step_id": step_id, "definizione_id": definizione_id})
        sql = f"""
            UPDATE {spec.table} AS c SET {', '.join(sets)}
            FROM pratiche.template_flussi tf
            WHERE c.id = %(row_id)s
              AND c.template_flusso_id = %(step_id)s
              AND tf.id = c.template_flusso_id
              AND tf.definizione_id = %(definizione_id)s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return cursor.rowcount

    # Scopo: hard DELETE di un figlio, scoping (row, step, definizione) via JOIN.
    def delete_child(
        self, child_kind: str, definizione_id: int, step_id: int, row_id: int,
    ) -> int:
        spec = CHILD_SPECS[child_kind]
        sql = f"""
            DELETE FROM {spec.table} AS c
            USING pratiche.template_flussi tf
            WHERE c.id = %(row_id)s
              AND c.template_flusso_id = %(step_id)s
              AND tf.id = c.template_flusso_id
              AND tf.definizione_id = %(definizione_id)s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, {
                "row_id": row_id, "step_id": step_id, "definizione_id": definizione_id,
            })
            return cursor.rowcount

    # --- Write archi del grafo su BOZZA (Slice 2 anello 5) --------------------
    # CRUD generico degli archi (prerequisiti/formule_tempo/regole_generazione)
    # parametrizzato da EDGE_SPECS. Ownership via anchor_col→definizione (JOIN);
    # immutabilità enforce dal guard figli DB (514). Le colonne inserite/aggiornate
    # provengono SEMPRE dall'allowlist dello spec (mai da input utente).

    # Scopo: crea un arco. `data` è già curato dal service (writable + tipo auto-set).
    def create_edge(self, edge_kind: str, data: dict[str, Any]) -> int:
        spec = EDGE_SPECS[edge_kind]
        allowed = spec.writable + ((spec.tipo_col,) if spec.tipo_col else ())
        cols = [c for c in allowed if c in data]
        vals = {c: data[c] for c in cols}
        placeholders = ", ".join(f"%({c})s" for c in cols)
        sql = (
            f"INSERT INTO {spec.table} ({', '.join(cols)}) "
            f"VALUES ({placeholders}) RETURNING id"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return int(cursor.fetchone()[0])

    # Scopo: aggiorna un arco (solo colonne writable), scoping anchor→definizione.
    def update_edge(
        self, edge_kind: str, definizione_id: int, row_id: int, data: dict[str, Any],
    ) -> int:
        spec = EDGE_SPECS[edge_kind]
        sets = [f"{c} = %({c})s" for c in spec.writable if c in data]
        if not sets:
            raise ValueError("update_edge richiede almeno un campo writable in `data`")
        vals: dict[str, Any] = {c: data[c] for c in spec.writable if c in data}
        vals.update({"row_id": row_id, "definizione_id": definizione_id})
        sql = f"""
            UPDATE {spec.table} AS e SET {', '.join(sets)}
            FROM pratiche.template_flussi tf
            WHERE e.id = %(row_id)s
              AND tf.id = e.{spec.anchor_col}
              AND tf.definizione_id = %(definizione_id)s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            return cursor.rowcount

    # Scopo: hard DELETE di un arco, scoping anchor→definizione.
    def delete_edge(self, edge_kind: str, definizione_id: int, row_id: int) -> int:
        spec = EDGE_SPECS[edge_kind]
        sql = f"""
            DELETE FROM {spec.table} AS e
            USING pratiche.template_flussi tf
            WHERE e.id = %(row_id)s
              AND tf.id = e.{spec.anchor_col}
              AND tf.definizione_id = %(definizione_id)s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, {"row_id": row_id, "definizione_id": definizione_id})
            return cursor.rowcount

    # --- Azioni ciclo di vita (Slice 1b) --------------------------------------
    # Wrapper 1:1 sulle fn DB (che restano l'unica sede di logica/validazione).
    # Nota lockstep: finché le fn sono SECURITY INVOKER la DML interna su
    # workflow_definizioni fallisce col ruolo web (permesso negato) → il DB deve
    # convertirle a SECURITY DEFINER (brief-db-accesso-be-definizioni-workflow §P1).

    def _call_scalar(self, sql: str, params: list) -> int:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return int(cursor.fetchone()[0])

    # Scopo: crea l'edizione BOZZA di un emittente da una definizione (di solito il
    # preset), con provenance per il drift. Ritorna l'id della nuova BOZZA.
    def fork_definizione(self, definizione_id: int, emittente_fiscale_id: int) -> int:
        return self._call_scalar(
            "SELECT pratiche.fn_fork_definizione(%s, %s)",
            [definizione_id, emittente_fiscale_id],
        )

    # Scopo: crea una nuova versione BOZZA dello stesso scope di una definizione.
    def nuova_versione_definizione(self, definizione_id: int) -> int:
        return self._call_scalar(
            "SELECT pratiche.fn_nuova_versione_definizione(%s)",
            [definizione_id],
        )

    # Scopo: pubblica una BOZZA (→ PUBBLICATA; la precedente dello scope → RITIRATA).
    def pubblica_definizione(self, definizione_id: int) -> int:
        return self._call_scalar(
            "SELECT pratiche.fn_pubblica_definizione(%s)",
            [definizione_id],
        )
