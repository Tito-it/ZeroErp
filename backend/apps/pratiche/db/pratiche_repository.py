# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB generico per lo schema pratiche (CRUD pratiche,
#        flussi, giornale, prerequisiti, canali).
# ------------------------------------------------------------

import json
from typing import Any

from django.db import connection

from apps.core.services.error_manager import ErrorManager
from apps.pratiche.types import (
    CalcoloTempoRow,
    CanalePraticaRow,
    FlussoRow,
    FormulaTempoRow,
    GiornaleRow,
    PraticaRow,
    PrerequisitoCheckRow,
    SospensioneRow,
)


class PraticheRepository:

    # -- PRATICHE --------------------------------------------------------

    # Scopo: Restituisce elenco pratiche paginato con filtri opzionali.
    # Perimetro: sola lettura, nessun side-effect.
    # Risultato: tuple (lista PraticaRow, conteggio totale).
    def list_pratiche(
        self,
        *,
        emittente_fiscale_id: int,
        stato_codice_interno: str | None = None,
        tipo_prestazione_id: int | None = None,
        soggetto_id: str | None = None,
        solo_interna: bool | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[PraticaRow], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        conditions: list[str] = ["p.emittente_fiscale_id = %s"]
        params: list[Any] = [emittente_fiscale_id]

        if stato_codice_interno is not None:
            conditions.append("sp.codice_interno = %s")
            params.append(stato_codice_interno)
        if tipo_prestazione_id is not None:
            conditions.append("p.tipo_prestazione_id = %s")
            params.append(tipo_prestazione_id)
        if soggetto_id is not None:
            conditions.append("p.soggetto_id = %s")
            params.append(soggetto_id)
        if solo_interna is not None:
            conditions.append("p.solo_interna = %s")
            params.append(solo_interna)

        where_clause = "WHERE " + " AND ".join(conditions)

        joins = """
            JOIN config.stati_pratiche sp ON sp.id = p.stato_id
        """

        count_sql = f"""
            SELECT COUNT(*)
            FROM pratiche.pratiche p
            {joins}
            {where_clause}
        """

        data_sql = f"""
            SELECT
                p.id, p.emittente_fiscale_id, p.tipo_prestazione_id,
                p.soggetto_id, p.stato_id, p.priorita_id,
                p.risorsa_umana_id, p.unita_organizzativa_id,
                p.pratica_padre_id, p.flusso_origine_id,
                p.canale_origine_id, p.solo_interna,
                p.codice, p.descrizione, p.data_scadenza,
                p.meta, p.data_insert, p.user_insert
            FROM pratiche.pratiche p
            {joins}
            {where_clause}
            ORDER BY p.data_insert DESC, p.id DESC
            LIMIT %s OFFSET %s
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, params + [safe_limit, safe_offset])
            rows = cursor.fetchall()

        return [self._map_pratica_row(r) for r in rows], total_count

    # Scopo: Restituisce il dettaglio di una singola pratica per ID.
    def get_pratica(self, pratica_id: int) -> PraticaRow | None:
        sql = """
            SELECT
                p.id, p.emittente_fiscale_id, p.tipo_prestazione_id,
                p.soggetto_id, p.stato_id, p.priorita_id,
                p.risorsa_umana_id, p.unita_organizzativa_id,
                p.pratica_padre_id, p.flusso_origine_id,
                p.canale_origine_id, p.solo_interna,
                p.codice, p.descrizione, p.data_scadenza,
                p.meta, p.data_insert, p.user_insert
            FROM pratiche.pratiche p
            WHERE p.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            row = cursor.fetchone()

        if not row:
            return None
        return self._map_pratica_row(row)

    # Scopo: Inserisce una nuova pratica e ritorna l'ID generato.
    def create_pratica(self, data: dict[str, Any]) -> int:
        sql = """
            INSERT INTO pratiche.pratiche (
                emittente_fiscale_id, tipo_prestazione_id, soggetto_id,
                stato_id, priorita_id, risorsa_umana_id,
                unita_organizzativa_id, canale_origine_id,
                solo_interna, descrizione, data_scadenza, meta
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
            )
            RETURNING id
        """
        params = [
            data["emittente_fiscale_id"],
            data["tipo_prestazione_id"],
            data.get("soggetto_id"),
            data["stato_id"],
            data["priorita_id"],
            data.get("risorsa_umana_id"),
            data.get("unita_organizzativa_id"),
            data.get("canale_origine_id"),
            data.get("solo_interna", False),
            data.get("descrizione"),
            data.get("data_scadenza"),
            json.dumps(data.get("meta", {})),
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            assert row is not None
        return int(row[0])

    # Scopo: Aggiorna i campi modificabili di una pratica esistente.
    def update_pratica(self, pratica_id: int, data: dict[str, Any]) -> None:
        # Costruzione SET dinamica con whitelist campi aggiornabili.
        allowed_fields: dict[str, str] = {
            "descrizione": "descrizione = %s",
            "data_scadenza": "data_scadenza = %s",
            "soggetto_id": "soggetto_id = %s",
            "risorsa_umana_id": "risorsa_umana_id = %s",
            "unita_organizzativa_id": "unita_organizzativa_id = %s",
            "meta": "meta = %s::jsonb",
        }

        set_parts: list[str] = []
        params: list[Any] = []
        for field_name, sql_fragment in allowed_fields.items():
            if field_name in data:
                set_parts.append(sql_fragment)
                if field_name == "meta":
                    params.append(json.dumps(data[field_name]))
                else:
                    params.append(data[field_name])

        if not set_parts:
            return

        params.append(pratica_id)
        sql = f"""
            UPDATE pratiche.pratiche
            SET {', '.join(set_parts)}
            WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, params)

    # Scopo: Aggiorna lo stato di una pratica tramite codice_interno dello stato.
    # Risolve lo stato prima dell'UPDATE per evitare SET NULL su colonna NOT NULL.
    def update_stato_pratica(self, pratica_id: int, stato_codice_interno: str) -> None:
        stato_id = self.resolve_stato_pratica(stato_codice_interno)
        sql = """
            UPDATE pratiche.pratiche
            SET stato_id = %s
            WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [stato_id, pratica_id])
            ErrorManager.require(
                cursor.rowcount > 0,
                code="E_PRATICA_NOT_FOUND",
                message=f"Pratica {pratica_id} non trovata",
            )

    # -- FLUSSI ----------------------------------------------------------

    # Scopo: Restituisce i flussi di una pratica ordinati per sequenza.
    def list_flussi(self, pratica_id: int) -> list[FlussoRow]:
        sql = """
            SELECT
                f.id, f.pratica_id, f.template_flusso_id, f.stato_id,
                f.flusso_padre_id, f.risorsa_umana_id,
                f.unita_organizzativa_id, f.sequenza,
                f.esito, f.note_esito, f.data_scadenza,
                f.meta, f.data_insert, f.user_insert
            FROM pratiche.flussi f
            WHERE f.pratica_id = %s
            ORDER BY f.sequenza, f.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            rows = cursor.fetchall()

        return [self._map_flusso_row(r) for r in rows]

    # Scopo: Restituisce il dettaglio di un singolo flusso.
    def get_flusso(self, flusso_id: int) -> FlussoRow | None:
        sql = """
            SELECT
                f.id, f.pratica_id, f.template_flusso_id, f.stato_id,
                f.flusso_padre_id, f.risorsa_umana_id,
                f.unita_organizzativa_id, f.sequenza,
                f.esito, f.note_esito, f.data_scadenza,
                f.meta, f.data_insert, f.user_insert
            FROM pratiche.flussi f
            WHERE f.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [flusso_id])
            row = cursor.fetchone()

        if not row:
            return None
        return self._map_flusso_row(row)

    # Scopo: Inserisce un nuovo flusso. Il trigger DB valida i prerequisiti.
    def create_flusso(self, data: dict[str, Any]) -> int:
        sql = """
            INSERT INTO pratiche.flussi (
                pratica_id, template_flusso_id, stato_id,
                flusso_padre_id, risorsa_umana_id,
                unita_organizzativa_id, sequenza, data_scadenza, meta
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
            )
            RETURNING id
        """
        params = [
            data["pratica_id"],
            data.get("template_flusso_id"),
            data["stato_id"],
            data.get("flusso_padre_id"),
            data.get("risorsa_umana_id"),
            data.get("unita_organizzativa_id"),
            data.get("sequenza", 0),
            data.get("data_scadenza"),
            json.dumps(data.get("meta", {})),
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            assert row is not None
        return int(row[0])

    # Scopo: Aggiorna lo stato di un flusso tramite codice_interno.
    # Risolve lo stato prima dell'UPDATE per evitare SET NULL su colonna NOT NULL.
    def update_stato_flusso(
        self, flusso_id: int, stato_codice_interno: str,
        esito: str | None = None, note_esito: str | None = None,
    ) -> None:
        stato_id = self.resolve_stato_flusso(stato_codice_interno)
        sql = """
            UPDATE pratiche.flussi
            SET stato_id = %s,
                esito = COALESCE(%s, esito),
                note_esito = COALESCE(%s, note_esito)
            WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [stato_id, esito, note_esito, flusso_id])
            ErrorManager.require(
                cursor.rowcount > 0,
                code="E_FLUSSO_NOT_FOUND",
                message=f"Flusso {flusso_id} non trovato",
            )

    # -- PREREQUISITI ----------------------------------------------------

    # Scopo: Chiama fn_check_prerequisiti_flusso per verifica prerequisiti.
    # Ritorna una riga per ogni prerequisito con flag soddisfatto.
    def check_prerequisiti(
        self, pratica_id: int, template_flusso_id: int,
    ) -> list[PrerequisitoCheckRow]:
        sql = """
            SELECT prerequisito_id, codice, descrizione, soddisfatto
            FROM pratiche.fn_check_prerequisiti_flusso(%s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id, template_flusso_id])
            rows = cursor.fetchall()

        return [
            {
                "prerequisito_id": int(r[0]),
                "codice": str(r[1]),
                "descrizione": str(r[2]),
                "soddisfatto": bool(r[3]),
            }
            for r in rows
        ]

    # -- GIORNALE --------------------------------------------------------

    # Scopo: Restituisce il giornale di bordo di una pratica (audit trail).
    # Ordinato cronologicamente (piu' recente in cima), include tx_id per tracciabilita'.
    def get_giornale_pratica(
        self, pratica_id: int, *, limit: int = 100, offset: int = 0,
    ) -> tuple[list[GiornaleRow], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        count_sql = """
            SELECT COUNT(*)
            FROM pratiche.giornale
            WHERE pratica_id = %s
        """
        data_sql = """
            SELECT
                g.id, g.pratica_id, g.flusso_id, g.azione,
                g.origine, g.dettaglio, g.tx_id,
                g.data_insert, g.user_insert
            FROM pratiche.giornale g
            WHERE g.pratica_id = %s
            ORDER BY g.data_insert DESC, g.id DESC
            LIMIT %s OFFSET %s
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, [pratica_id])
            row = cursor.fetchone()
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, [pratica_id, safe_limit, safe_offset])
            rows = cursor.fetchall()

        result: list[GiornaleRow] = [
            {
                "id": int(r[0]),
                "pratica_id": int(r[1]),
                "flusso_id": None if r[2] is None else int(r[2]),
                "azione": str(r[3]),
                "origine": str(r[4]),
                "dettaglio": r[5] if isinstance(r[5], dict) else {},
                "tx_id": str(r[6]) if r[6] is not None else None,
                "data_insert": r[7].isoformat() if r[7] is not None else "",
                "user_insert": str(r[8]),
            }
            for r in rows
        ]
        return result, total_count

    # -- CANALI ----------------------------------------------------------

    # Scopo: Restituisce i canali abilitati per un template flusso.
    def get_canali_flusso(self, template_flusso_id: int) -> list[CanalePraticaRow]:
        sql = """
            SELECT cp.id, cp.codice, cp.descrizione, cp.codice_interno
            FROM pratiche.template_flussi_canali tfc
            JOIN config.canali_pratiche cp ON cp.id = tfc.canale_id
            WHERE tfc.template_flusso_id = %s
              AND tfc.attivo = true
              AND cp.attivo = true
            ORDER BY cp.codice
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [template_flusso_id])
            rows = cursor.fetchall()

        return [
            {
                "id": int(r[0]),
                "codice": str(r[1]),
                "descrizione": r[2],
                "codice_interno": str(r[3]),
            }
            for r in rows
        ]

    # -- SOSPENSIONI -----------------------------------------------------

    _SOSPENSIONE_COLS = """
        id, pratica_id, flusso_id, data_inizio, data_fine,
        data_riattivazione_prevista, motivo,
        data_insert, user_insert, data_update, user_update
    """

    # Scopo: Inserisce una nuova sospensione per pratica (o flusso) e ritorna l'ID.
    def create_sospensione(
        self,
        pratica_id: int,
        motivo: str,
        *,
        flusso_id: int | None = None,
        data_riattivazione_prevista: str | None = None,
    ) -> int:
        sql = """
            INSERT INTO pratiche.sospensioni (
                pratica_id, flusso_id, data_inizio, motivo,
                data_riattivazione_prevista
            ) VALUES (
                %s, %s, NOW(), %s, %s
            )
            RETURNING id
        """
        params = [pratica_id, flusso_id, motivo, data_riattivazione_prevista]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            assert row is not None
        return int(row[0])

    # Scopo: Chiude la sospensione attiva impostando data_fine = NOW().
    # Il trigger DB gestisce la riattivazione (ripristino stati flussi).
    def chiudi_sospensione(self, sospensione_id: int) -> None:
        sql = """
            UPDATE pratiche.sospensioni
            SET data_fine = NOW()
            WHERE id = %s AND data_fine IS NULL
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [sospensione_id])
            ErrorManager.require(
                cursor.rowcount > 0,
                code="E_SOSPENSIONE_NOT_FOUND",
                message=f"Sospensione {sospensione_id} non trovata o gia' chiusa",
            )

    # Scopo: Trova la sospensione attiva (data_fine IS NULL) per una pratica intera.
    def get_sospensione_attiva_pratica(self, pratica_id: int) -> SospensioneRow | None:
        sql = f"""
            SELECT {self._SOSPENSIONE_COLS}
            FROM pratiche.sospensioni
            WHERE pratica_id = %s AND flusso_id IS NULL AND data_fine IS NULL
            LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            row = cursor.fetchone()
        if not row:
            return None
        return self._map_sospensione_row(row)

    # Scopo: Trova la sospensione attiva per un flusso specifico.
    def get_sospensione_attiva_flusso(self, pratica_id: int, flusso_id: int) -> SospensioneRow | None:
        sql = f"""
            SELECT {self._SOSPENSIONE_COLS}
            FROM pratiche.sospensioni
            WHERE pratica_id = %s AND flusso_id = %s AND data_fine IS NULL
            LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id, flusso_id])
            row = cursor.fetchone()
        if not row:
            return None
        return self._map_sospensione_row(row)

    # Scopo: Restituisce le sospensioni di una pratica (tutte, ordinate per data).
    def list_sospensioni(self, pratica_id: int) -> list[SospensioneRow]:
        sql = f"""
            SELECT {self._SOSPENSIONE_COLS}
            FROM pratiche.sospensioni
            WHERE pratica_id = %s
            ORDER BY data_inizio DESC, id DESC
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            rows = cursor.fetchall()
        return [self._map_sospensione_row(r) for r in rows]

    # -- CALCOLI TEMPO ---------------------------------------------------

    # Scopo: Restituisce i calcoli tempo di una pratica arricchiti con stato_tempo live.
    # Usa LEFT JOIN LATERAL su fn_valuta_tempo_esecuzione_da_a per calcolare
    # giorni_rimanenti e stato_tempo (OK/WARNING/CRITICO/SFORATO) in tempo reale.
    def list_calcoli_tempo(self, pratica_id: int) -> list[CalcoloTempoRow]:
        sql = """
            SELECT ct.id, ct.pratica_id, ct.flusso_da_id, ct.flusso_a_id,
                   ct.formula_tempo_id, ct.data_inizio_calcolo, ct.data_fine_calcolo,
                   ct.giorni_lordi, ct.giorni_sospensione, ct.giorni_netti,
                   ct.giorni_formula, ct.sforato,
                   v.giorni_rimanenti, v.stato_tempo
            FROM pratiche.calcoli_tempo ct
            LEFT JOIN LATERAL pratiche.fn_valuta_tempo_esecuzione_da_a(
                ct.pratica_id, ct.flusso_da_id, ct.flusso_a_id
            ) v ON true
            WHERE ct.pratica_id = %s
            ORDER BY ct.data_inizio_calcolo, ct.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            rows = cursor.fetchall()
        return [self._map_calcolo_tempo_row(r) for r in rows]

    # -- FORMULE TEMPO -----------------------------------------------------

    # Scopo: Restituisce le formule tempo attive per un tipo prestazione.
    def list_formule_tempo(self, tipo_prestazione_id: int) -> list[FormulaTempoRow]:
        sql = """
            SELECT ft.id, ft.tipo_prestazione_id,
                   ft.template_flusso_da_id, ft.template_flusso_a_id,
                   ft.giorni_esecuzione, ft.giorni_warning, ft.giorni_critico,
                   ft.attivo, ft.descrizione, ft.meta
            FROM pratiche.formule_tempo ft
            WHERE ft.tipo_prestazione_id = %s AND ft.attivo = true
            ORDER BY ft.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo_prestazione_id])
            rows = cursor.fetchall()
        return [self._map_formula_tempo_row(r) for r in rows]

    # -- RISOLUZIONE STATO -----------------------------------------------

    # Scopo: Risolve l'ID di uno stato da codice_interno su una tabella config.
    # Metodo generico usato dai wrapper resolve_stato_pratica / resolve_stato_flusso.
    def _resolve_stato(self, tabella: str, codice_interno: str, etichetta: str) -> int:
        sql = f"""
            SELECT id FROM {tabella}
            WHERE codice_interno = %s AND attivo = true
            LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [codice_interno])
            row = cursor.fetchone()
        ErrorManager.require(
            row is not None,
            code="E_CONFIG_MANCANTE",
            message=f"Stato {etichetta} '{codice_interno}' non trovato in {tabella}",
        )
        assert row is not None
        return int(row[0])

    # Scopo: Risolve l'ID di uno stato pratica da codice_interno.
    def resolve_stato_pratica(self, codice_interno: str) -> int:
        return self._resolve_stato("config.stati_pratiche", codice_interno, "pratica")

    # Scopo: Risolve l'ID di uno stato flusso da codice_interno.
    def resolve_stato_flusso(self, codice_interno: str) -> int:
        return self._resolve_stato("config.stati_flussi_pratiche", codice_interno, "flusso")

    # -- HANDLER KEY -----------------------------------------------------

    # Scopo: Recupera l'handler_key dal template flusso (via handler_flussi).
    def get_handler_key(self, template_flusso_id: int) -> str | None:
        sql = """
            SELECT hf.handler_key
            FROM pratiche.template_flussi tf
            JOIN pratiche.handler_flussi hf ON hf.id = tf.handler_id
            WHERE tf.id = %s AND hf.attivo = true
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [template_flusso_id])
            row = cursor.fetchone()
        if not row:
            return None
        return str(row[0])

    # Scopo: Recupera handler_key e handler_params dal template flusso.
    # Restituisce entrambi per il dispatch: la key per il lookup nel registry,
    # i params per la configurazione statica passata all'handler.
    def get_handler_info(self, template_flusso_id: int) -> tuple[str, dict[str, Any]] | None:
        sql = """
            SELECT hf.handler_key, tf.handler_params
            FROM pratiche.template_flussi tf
            JOIN pratiche.handler_flussi hf ON hf.id = tf.handler_id
            WHERE tf.id = %s AND hf.attivo = true
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [template_flusso_id])
            row = cursor.fetchone()
        if not row:
            return None
        handler_params = row[1] if isinstance(row[1], dict) else {}
        return str(row[0]), handler_params

    # -- MAPPING HELPERS -------------------------------------------------

    @staticmethod
    def _map_pratica_row(r: tuple) -> PraticaRow:
        return {
            "id": int(r[0]),
            "emittente_fiscale_id": int(r[1]),
            "tipo_prestazione_id": int(r[2]),
            "soggetto_id": str(r[3]) if r[3] is not None else None,
            "stato_id": int(r[4]),
            "priorita_id": int(r[5]),
            "risorsa_umana_id": None if r[6] is None else int(r[6]),
            "unita_organizzativa_id": None if r[7] is None else int(r[7]),
            "pratica_padre_id": None if r[8] is None else int(r[8]),
            "flusso_origine_id": None if r[9] is None else int(r[9]),
            "canale_origine_id": None if r[10] is None else int(r[10]),
            "solo_interna": bool(r[11]),
            "codice": r[12],
            "descrizione": r[13],
            "data_scadenza": r[14].isoformat() if r[14] is not None else None,
            "meta": r[15] if isinstance(r[15], dict) else {},
            "data_insert": r[16].isoformat() if r[16] is not None else "",
            "user_insert": str(r[17]),
        }

    @staticmethod
    def _map_sospensione_row(r: tuple) -> SospensioneRow:
        return {
            "id": int(r[0]),
            "pratica_id": int(r[1]),
            "flusso_id": None if r[2] is None else int(r[2]),
            "data_inizio": r[3].isoformat() if r[3] is not None else "",
            "data_fine": r[4].isoformat() if r[4] is not None else None,
            "data_riattivazione_prevista": r[5].isoformat() if r[5] is not None else None,
            "motivo": str(r[6]),
            "data_insert": r[7].isoformat() if r[7] is not None else "",
            "user_insert": str(r[8]),
            "data_update": r[9].isoformat() if r[9] is not None else None,
            "user_update": str(r[10]) if r[10] is not None else None,
        }

    @staticmethod
    def _map_calcolo_tempo_row(r: tuple) -> CalcoloTempoRow:
        return {
            "id": int(r[0]),
            "pratica_id": int(r[1]),
            "flusso_da_id": int(r[2]),
            "flusso_a_id": int(r[3]),
            "formula_tempo_id": int(r[4]),
            "data_inizio_calcolo": r[5].isoformat() if r[5] is not None else "",
            "data_fine_calcolo": r[6].isoformat() if r[6] is not None else None,
            "giorni_lordi": None if r[7] is None else int(r[7]),
            "giorni_sospensione": None if r[8] is None else int(r[8]),
            "giorni_netti": None if r[9] is None else int(r[9]),
            "giorni_formula": int(r[10]),
            "sforato": None if r[11] is None else bool(r[11]),
            "giorni_rimanenti": None if r[12] is None else int(r[12]),
            "stato_tempo": None if r[13] is None else str(r[13]),
        }

    @staticmethod
    def _map_formula_tempo_row(r: tuple) -> FormulaTempoRow:
        return {
            "id": int(r[0]),
            "tipo_prestazione_id": int(r[1]),
            "template_flusso_da_id": int(r[2]),
            "template_flusso_a_id": int(r[3]),
            "giorni_esecuzione": int(r[4]),
            "giorni_warning": int(r[5]),
            "giorni_critico": int(r[6]),
            "attivo": bool(r[7]),
            "descrizione": str(r[8]) if r[8] is not None else None,
            "meta": r[9] if isinstance(r[9], dict) else {},
        }

    @staticmethod
    def _map_flusso_row(r: tuple) -> FlussoRow:
        return {
            "id": int(r[0]),
            "pratica_id": int(r[1]),
            "template_flusso_id": None if r[2] is None else int(r[2]),
            "stato_id": int(r[3]),
            "flusso_padre_id": None if r[4] is None else int(r[4]),
            "risorsa_umana_id": None if r[5] is None else int(r[5]),
            "unita_organizzativa_id": None if r[6] is None else int(r[6]),
            "sequenza": int(r[7]),
            "esito": r[8],
            "note_esito": r[9],
            "data_scadenza": r[10].isoformat() if r[10] is not None else None,
            "meta": r[11] if isinstance(r[11], dict) else {},
            "data_insert": r[12].isoformat() if r[12] is not None else "",
            "user_insert": str(r[13]),
        }
