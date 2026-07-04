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

from typing import Any

from django.db import connection

# Campi "core" di uno step editabili in Slice 2 anello 3 — UNICA fonte di verità
# condivisa da repository (build SQL) e service (clean payload), così i due layer
# non possono divergere. Gli enum/default vivono nei CHECK/DEFAULT DB, non qui.
STEP_CORE_FIELDS: tuple[str, ...] = (
    "codice", "descrizione", "sequenza", "obbligatorio",
    "direzione", "modalita_esito", "esito_default",
)


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
