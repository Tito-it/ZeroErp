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

from apps.core.db._helpers import row_to_dict, rows_to_list
from apps.core.services.error_manager import ErrorManager


# Scopo: Coercion difensiva jsonb -> dict. psycopg puo' restituire un jsonb
# come str (nessun adapter automatico): senza coerce, un isinstance(dict)
# scarterebbe SILENZIOSAMENTE la configurazione (bug handler_params={} sul
# dispatch CONFERMA, trovato dallo smoke pratica 2026-06-11).
def coerce_jsonb_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return {}
    return value if isinstance(value, dict) else {}


_PRATICHE_ORDER_COLS = {
    "codice", "descrizione", "data_apertura", "data_scadenza", "data_insert",
    "tipo_prestazione_descrizione", "stato_descrizione",
    "priorita_descrizione", "soggetto_display", "risorsa_umana_display",
}


class PraticheRepository:

    # -- SQL comuni pratiche (JOIN display fields) --

    _PRATICA_SELECT = """
        p.id, p.emittente_fiscale_id, p.tipo_prestazione_id,
        p.soggetto_id, p.soggetto_ruolo_id, p.istanza_utility_id,
        -- Cliente (BA) derivato dall'istanza: presente se cliente attivo, NULL se
        -- prospect. Single source of truth a DB (script.fn_get_billing_account_by_istanza),
        -- nessuna derivazione lato FE. Alimenta pre-fill+lock e gating documenti
        -- (offerta/contratto richiedono BA) aprendo un documento dal flusso.
        script.fn_get_billing_account_by_istanza(p.istanza_utility_id) AS billing_account_id,
        p.stato_id, p.priorita_id,
        p.risorsa_umana_id, p.unita_organizzativa_id,
        p.pratica_padre_id, p.flusso_origine_id, p.canale_origine_id,
        p.codice, p.descrizione, p.data_apertura, p.data_scadenza,
        p.meta, p.data_insert, p.user_insert,
        tp.codice AS tipo_prestazione_codice,
        tp.descrizione AS tipo_prestazione_descrizione,
        sp.codice_interno AS stato_codice_interno,
        sp.descrizione AS stato_descrizione,
        pp.codice_interno AS priorita_codice_interno,
        pp.descrizione AS priorita_descrizione,
        s.ragione_sociale_completa AS soggetto_display,
        s.id_fiscale_univoco_cf_piva AS soggetto_id_fiscale,
        sru.ragione_sociale_completa AS risorsa_umana_display,
        uo.descrizione AS unita_organizzativa_descrizione
    """

    _PRATICA_JOINS = """
        JOIN pratiche.tipi_prestazione tp ON tp.id = p.tipo_prestazione_id
        JOIN config.stati_pratiche sp ON sp.id = p.stato_id
        JOIN config.priorita_pratiche pp ON pp.id = p.priorita_id
        LEFT JOIN anagrafiche.soggetti s ON s.id = p.soggetto_id
        LEFT JOIN anagrafiche.risorse_umane ru ON ru.id = p.risorsa_umana_id
        LEFT JOIN anagrafiche.soggetti_ruoli srr ON srr.id = ru.soggetto_ruolo_id
        LEFT JOIN anagrafiche.soggetti sru ON sru.id = srr.soggetto_id
        LEFT JOIN config.unita_organizzative uo ON uo.id = p.unita_organizzativa_id
    """

    # -- Metodi pubblici per SQL comuni (usati anche da GenerazioneRepository) --

    @classmethod
    def pratica_select_sql(cls) -> str:
        """Restituisce il frammento SELECT per pratiche con display fields."""
        return cls._PRATICA_SELECT

    @classmethod
    def pratica_joins_sql(cls) -> str:
        """Restituisce il frammento JOIN per pratiche con display fields."""
        return cls._PRATICA_JOINS

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
        soggetto_ruolo_id: int | None = None,
        istanza_utility_id: int | None = None,
        solo_interne: bool = False,
        priorita_id: int | None = None,
        risorsa_umana_id: int | None = None,
        search: str | None = None,
        data_da: str | None = None,
        data_a: str | None = None,
        limit: int,
        offset: int,
        order_by: str = "data_insert",
        order_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        order_col = order_by if order_by in _PRATICHE_ORDER_COLS else "data_insert"
        direction = "DESC" if order_dir and order_dir.upper() == "DESC" else "ASC"

        conditions: list[str] = ["p.emittente_fiscale_id = %s"]
        params: list[Any] = [emittente_fiscale_id]

        # Lente di contesto canonica (D1): la verita' del filtro vive nella fn
        # DB fn_lista_pratiche_per_contesto (bucket ruolo/istanza/interne);
        # qui si compone come semi-join per mantenere proiezione display,
        # filtri e paginazione della lista standard.
        if soggetto_ruolo_id is not None or istanza_utility_id is not None or solo_interne:
            conditions.append("""p.id IN (
                SELECT c.pratica_id
                FROM pratiche.fn_lista_pratiche_per_contesto(%s, %s, %s, %s) c
            )""")
            params.extend([
                emittente_fiscale_id, soggetto_ruolo_id,
                istanza_utility_id, solo_interne,
            ])

        if stato_codice_interno is not None:
            conditions.append("sp.codice_interno = %s")
            params.append(stato_codice_interno)
        if tipo_prestazione_id is not None:
            conditions.append("p.tipo_prestazione_id = %s")
            params.append(tipo_prestazione_id)
        if soggetto_id is not None:
            conditions.append("p.soggetto_id = %s")
            params.append(soggetto_id)
        if priorita_id is not None:
            conditions.append("p.priorita_id = %s")
            params.append(priorita_id)
        if risorsa_umana_id is not None:
            conditions.append("p.risorsa_umana_id = %s")
            params.append(risorsa_umana_id)
        if data_da:
            conditions.append("p.data_insert >= %s::date")
            params.append(data_da)
        if data_a:
            conditions.append("p.data_insert < (%s::date + INTERVAL '1 day')")
            params.append(data_a)
        if search:
            conditions.append("""(
                p.codice ILIKE %s
                OR p.descrizione ILIKE %s
                OR s.ragione_sociale_completa ILIKE %s
            )""")
            pattern = f"%{search.strip()}%"
            params.extend([pattern, pattern, pattern])

        where_clause = "WHERE " + " AND ".join(conditions)

        count_sql = f"""
            SELECT COUNT(*)
            FROM pratiche.pratiche p
            {self._PRATICA_JOINS}
            {where_clause}
        """

        data_sql = f"""
            SELECT {self._PRATICA_SELECT}
            FROM pratiche.pratiche p
            {self._PRATICA_JOINS}
            {where_clause}
            ORDER BY {order_col} {direction}, p.id
            LIMIT %s OFFSET %s
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_PRATICA_QUERY",
                message="Errore conteggio pratiche",
            )
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, params + [safe_limit, safe_offset])
            result = rows_to_list(cursor)

        return result, total_count

    # Scopo: Restituisce il dettaglio di una singola pratica per ID con display fields.
    def get_pratica(self, pratica_id: int) -> dict[str, Any] | None:
        sql = f"""
            SELECT {self._PRATICA_SELECT}
            FROM pratiche.pratiche p
            {self._PRATICA_JOINS}
            WHERE p.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            return row_to_dict(cursor)

    # Scopo: Inserisce una nuova pratica e ritorna l'ID generato.
    def create_pratica(self, data: dict[str, Any]) -> int:
        sql = """
            INSERT INTO pratiche.pratiche (
                emittente_fiscale_id, tipo_prestazione_id, soggetto_id,
                soggetto_ruolo_id, istanza_utility_id,
                stato_id, priorita_id, risorsa_umana_id,
                unita_organizzativa_id, canale_origine_id,
                descrizione, data_scadenza, meta
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
            )
            RETURNING id
        """
        params = [
            data["emittente_fiscale_id"],
            data["tipo_prestazione_id"],
            data.get("soggetto_id"),
            data.get("soggetto_ruolo_id"),
            data.get("istanza_utility_id"),
            data["stato_id"],
            data["priorita_id"],
            data.get("risorsa_umana_id"),
            data.get("unita_organizzativa_id"),
            data.get("canale_origine_id"),
            data.get("descrizione"),
            data.get("data_scadenza"),
            json.dumps(data.get("meta", {})),
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_PRATICA_INSERT",
                message="Errore inserimento pratica (RETURNING id nullo)",
            )
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

    _FLUSSO_SELECT = """
        f.id, f.pratica_id, f.template_flusso_id, f.stato_id,
        f.flusso_padre_id, f.risorsa_umana_id,
        f.unita_organizzativa_id, f.sequenza,
        f.esito, f.note_esito, f.data_scadenza,
        f.meta, f.data_insert, f.user_insert,
        sf.codice_interno AS stato_codice_interno,
        sf.descrizione AS stato_descrizione,
        tf.codice AS template_flusso_codice,
        tf.descrizione AS template_flusso_descrizione,
        -- Attività UI data-driven (catalogo pratiche.azioni_ui): chiave risolta
        -- dal registry FE → drawer di dominio da aprire dal flusso. NULL = nessuna.
        au.azione_ui_key AS template_azione_ui_key,
        p.codice AS pratica_codice,
        p.data_apertura AS pratica_data_apertura,
        p.istanza_utility_id AS pratica_istanza_utility_id,
        script.fn_get_billing_account_by_istanza(p.istanza_utility_id) AS pratica_billing_account_id,
        s.ragione_sociale_completa AS pratica_soggetto_display,
        s.id_fiscale_univoco_cf_piva AS pratica_soggetto_id_fiscale
    """

    _FLUSSO_JOINS = """
        JOIN config.stati_flussi_pratiche sf ON sf.id = f.stato_id
        LEFT JOIN pratiche.template_flussi tf ON tf.id = f.template_flusso_id
        LEFT JOIN pratiche.azioni_ui au ON au.id = tf.azione_ui_id
        JOIN pratiche.pratiche p ON p.id = f.pratica_id
        LEFT JOIN anagrafiche.soggetti s ON s.id = p.soggetto_id
    """

    # Scopo: Restituisce i flussi di una pratica ordinati per sequenza, con display fields.
    def list_flussi(self, pratica_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT {self._FLUSSO_SELECT}
            FROM pratiche.flussi f
            {self._FLUSSO_JOINS}
            WHERE f.pratica_id = %s
            ORDER BY f.sequenza, f.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            return rows_to_list(cursor)

    # Scopo: Restituisce il dettaglio di un singolo flusso con display fields.
    def get_flusso(self, flusso_id: int) -> dict[str, Any] | None:
        sql = f"""
            SELECT {self._FLUSSO_SELECT}
            FROM pratiche.flussi f
            {self._FLUSSO_JOINS}
            WHERE f.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [flusso_id])
            return row_to_dict(cursor)

    # Scopo: Percorso suggerito della pratica = template_flussi del suo
    #        tipo_prestazione (in ordine), LEFT JOIN i flussi gia' istanziati.
    #        Ogni riga: lo step (codice/sequenza/obbligatorio/has_handler) +,
    #        se istanziato, flusso_id/stato/esito. Alimenta la roadmap FE (i
    #        flussi NON sono materializzati alla creazione: si creano
    #        progressivamente, §6 brief FE).
    def get_percorso_pratica(self, pratica_id: int) -> list[dict[str, Any]]:
        # Arricchimento workflow v2 (D3/D4): per ogni step la fn DB dice se e'
        # ripetibile ADESSO (regola template + ultima istanza) e lo stato del
        # ramo da fn_check_chiusura_pratica (completato / percorribile /
        # bloccante). `ramo` e' la sintesi per la resa FE:
        #   COMPLETATO   → almeno un'istanza chiusa;
        #   PERCORRIBILE → prerequisiti soddisfatti, eseguibile ora;
        #   RAMO_CHIUSO  → un prerequisito e' stato DECISO (istanza COMPLETATO)
        #                  ma mai con l'esito richiesto: il bivio ha preso
        #                  l'altra strada (allo stato attuale: un retry del
        #                  predecessore puo' riaprirlo);
        #   FUTURO       → prerequisiti non ancora decisi (step a valle).
        sql = """
            SELECT
                tf.id AS template_flusso_id,
                tf.codice AS template_flusso_codice,
                tf.descrizione AS template_flusso_descrizione,
                tf.sequenza,
                tf.obbligatorio,
                tf.direzione,
                (tf.handler_id IS NOT NULL) AS has_handler,
                au.azione_ui_key AS template_azione_ui_key,
                f.id AS flusso_id,
                sf.codice_interno AS stato_codice_interno,
                f.esito,
                pratiche.fn_check_ripetibilita_flusso(p.id, tf.id) AS ripetibile_adesso,
                COALESCE(cc.completato, false) AS completato,
                COALESCE(cc.percorribile, false) AS percorribile,
                COALESCE(cc.bloccante, false) AS bloccante,
                CASE
                    WHEN COALESCE(cc.completato, false) THEN 'COMPLETATO'
                    WHEN COALESCE(cc.percorribile, false) THEN 'PERCORRIBILE'
                    -- RAMO_CHIUSO: un prerequisito NON soddisfatto (verita'
                    -- esito-aware delegata alla fn DB, niente regole
                    -- duplicate qui) il cui template e' pero' gia' stato
                    -- DECISO (almeno un'istanza COMPLETATO) → il bivio ha
                    -- preso l'altra strada. Senza prerequisiti decisi e'
                    -- solo uno step FUTURO.
                    WHEN EXISTS (
                        SELECT 1
                        FROM pratiche.fn_check_prerequisiti_flusso(p.id, tf.id) pr
                        WHERE NOT pr.soddisfatto
                          AND EXISTS (
                              SELECT 1
                              FROM pratiche.flussi pf
                              JOIN config.stati_flussi_pratiche psf
                                ON psf.id = pf.stato_id
                              WHERE pf.pratica_id = p.id
                                AND pf.template_flusso_id = pr.prerequisito_id
                                AND psf.codice_interno = 'COMPLETATO'
                          )
                    ) THEN 'RAMO_CHIUSO'
                    ELSE 'FUTURO'
                END AS ramo
            FROM pratiche.pratiche p
            JOIN pratiche.template_flussi tf
              ON tf.tipo_prestazione_id = p.tipo_prestazione_id AND tf.attivo
            LEFT JOIN pratiche.azioni_ui au ON au.id = tf.azione_ui_id
            LEFT JOIN pratiche.fn_check_chiusura_pratica(%s) cc
              ON cc.template_flusso_id = tf.id
            LEFT JOIN LATERAL (
                SELECT ff.id, ff.stato_id, ff.esito
                FROM pratiche.flussi ff
                WHERE ff.pratica_id = p.id AND ff.template_flusso_id = tf.id
                ORDER BY ff.id DESC
                LIMIT 1
            ) f ON true
            LEFT JOIN config.stati_flussi_pratiche sf ON sf.id = f.stato_id
            WHERE p.id = %s
            ORDER BY tf.sequenza, tf.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id, pratica_id])
            return rows_to_list(cursor)

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
            ErrorManager.require(
                row is not None,
                code="E_FLUSSO_INSERT",
                message="Errore inserimento flusso (RETURNING id nullo)",
            )
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
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT prerequisito_id, codice, descrizione, soddisfatto
            FROM pratiche.fn_check_prerequisiti_flusso(%s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id, template_flusso_id])
            return rows_to_list(cursor)

    # -- GIORNALE --------------------------------------------------------

    # Scopo: Restituisce il giornale di bordo di una pratica (audit trail).
    # Ordinato cronologicamente (piu' recente in cima), include tx_id per tracciabilita'.
    def get_giornale_pratica(
        self, pratica_id: int, *, limit: int = 100, offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
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
            ErrorManager.require(
                row is not None,
                code="E_GIORNALE_QUERY",
                message="Errore conteggio giornale",
            )
            assert row is not None
            total_count = int(row[0])

            cursor.execute(data_sql, [pratica_id, safe_limit, safe_offset])
            result = rows_to_list(cursor)

        return result, total_count

    # Scopo: Scrive un evento di dominio DOMINIO_* sul giornale via la fn DB
    # dedicata (append-only, origine='HANDLER', forma DOMINIO_* garantita dal
    # CHECK chk_giornale_azione). Unico canale applicativo di scrittura.
    def log_evento_dominio(
        self, *, pratica_id: int, flusso_id: int | None,
        tipo_evento: str, meta: dict[str, Any] | None = None,
    ) -> int:
        sql = """
            SELECT pratiche.fn_log_evento_dominio(
                p_pratica_id => %s,
                p_flusso_id => %s,
                p_tipo_evento => %s,
                p_meta => %s::jsonb
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id, flusso_id, tipo_evento, json.dumps(meta or {})])
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    # -- SORGENTI --------------------------------------------------------

    # Scopo: Aggancia (idempotente) una sorgente alla pratica. Risolve il
    # sorgente_tipo_id da config.sorgenti per codice_interno (no id hardcoded).
    # ON CONFLICT sulla UNIQUE (pratica_id, sorgente_tipo_id, sorgente_uid,
    # ruolo_link): la seconda chiamata e' un no-op.
    def upsert_pratica_sorgente(
        self, *, pratica_id: int, sorgente_codice: str, sorgente_uid: str,
        ruolo_link: str = "ROOT", sorgente_riga: int | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        sql = """
            INSERT INTO pratiche.pratiche_sorgenti (
                pratica_id, sorgente_tipo_id, sorgente_uid,
                sorgente_riga, ruolo_link, meta
            )
            SELECT %s, s.id, %s, %s, %s, %s::jsonb
            FROM config.sorgenti s
            WHERE s.codice_interno = %s
            ON CONFLICT (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
            DO NOTHING
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                pratica_id, sorgente_uid, sorgente_riga, ruolo_link,
                json.dumps(meta or {}), sorgente_codice,
            ])
            ErrorManager.require(
                cursor.rowcount > 0 or self._sorgente_link_exists(
                    pratica_id, sorgente_codice, sorgente_uid, ruolo_link,
                ),
                code="E_PRATICA_SORGENTE_TIPO_INVALIDO",
                message=f"Codice sorgente '{sorgente_codice}' non in config.sorgenti",
            )

    def _sorgente_link_exists(
        self, pratica_id: int, sorgente_codice: str, sorgente_uid: str, ruolo_link: str,
    ) -> bool:
        sql = """
            SELECT 1
            FROM pratiche.pratiche_sorgenti ps
            JOIN config.sorgenti s ON s.id = ps.sorgente_tipo_id
            WHERE ps.pratica_id = %s AND s.codice_interno = %s
              AND ps.sorgente_uid = %s AND ps.ruolo_link = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id, sorgente_codice, sorgente_uid, ruolo_link])
            return cursor.fetchone() is not None

    # -- CANALI ----------------------------------------------------------

    # Scopo: Restituisce i canali abilitati per un template flusso.
    def get_canali_flusso(self, template_flusso_id: int) -> list[dict[str, Any]]:
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
            return rows_to_list(cursor)

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
            ErrorManager.require(
                row is not None,
                code="E_SOSPENSIONE_INSERT",
                message="Errore inserimento sospensione (RETURNING id nullo)",
            )
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
    def get_sospensione_attiva_pratica(self, pratica_id: int) -> dict[str, Any] | None:
        sql = f"""
            SELECT {self._SOSPENSIONE_COLS}
            FROM pratiche.sospensioni
            WHERE pratica_id = %s AND flusso_id IS NULL AND data_fine IS NULL
            LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            return row_to_dict(cursor)

    # Scopo: Trova la sospensione attiva per un flusso specifico.
    def get_sospensione_attiva_flusso(self, pratica_id: int, flusso_id: int) -> dict[str, Any] | None:
        sql = f"""
            SELECT {self._SOSPENSIONE_COLS}
            FROM pratiche.sospensioni
            WHERE pratica_id = %s AND flusso_id = %s AND data_fine IS NULL
            LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id, flusso_id])
            return row_to_dict(cursor)

    # Scopo: Restituisce le sospensioni di una pratica (tutte, ordinate per data).
    def list_sospensioni(self, pratica_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT {self._SOSPENSIONE_COLS}
            FROM pratiche.sospensioni
            WHERE pratica_id = %s
            ORDER BY data_inizio DESC, id DESC
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            return rows_to_list(cursor)

    # -- NOTE PRATICHE ---------------------------------------------------

    _NOTA_SELECT = """
        n.id, n.pratica_id, n.tipo_nota_id,
        tn.codice_interno AS tipo_nota_codice,
        tn.descrizione AS tipo_nota_descrizione,
        n.contenuto, n.data_insert, n.user_insert,
        n.data_update, n.user_update
    """

    _NOTA_JOINS = """
        JOIN config.tipi_nota tn ON tn.id = n.tipo_nota_id
    """

    # Scopo: Restituisce le note di una pratica con tipo nota display.
    def list_note_pratica(self, pratica_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT {self._NOTA_SELECT}
            FROM pratiche.note_pratiche n
            {self._NOTA_JOINS}
            WHERE n.pratica_id = %s
            ORDER BY n.data_insert DESC, n.id DESC
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            return rows_to_list(cursor)

    # Scopo: Crea una nota per la pratica. Risolve tipo_nota da codice_interno.
    def create_nota_pratica(
        self, pratica_id: int, tipo_nota_codice: str, contenuto: str,
    ) -> int:
        with connection.cursor() as cursor:
            # Risolve tipo_nota_id prima dell'INSERT per errore chiaro
            cursor.execute(
                "SELECT id FROM config.tipi_nota WHERE codice_interno = %s AND attivo = true",
                [tipo_nota_codice],
            )
            tipo_row = cursor.fetchone()
            ErrorManager.require(
                tipo_row is not None,
                code="E_CONFIG_MANCANTE",
                message=f"Tipo nota '{tipo_nota_codice}' non trovato o non attivo",
            )
            assert tipo_row is not None

            cursor.execute(
                """INSERT INTO pratiche.note_pratiche (pratica_id, tipo_nota_id, contenuto)
                   VALUES (%s, %s, %s) RETURNING id""",
                [pratica_id, tipo_row[0], contenuto],
            )
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_NOTA_INSERT",
                message="Errore inserimento nota (RETURNING id nullo)",
            )
            assert row is not None
        return int(row[0])

    # Scopo: Aggiorna il contenuto di una nota (ownership check su pratica_id).
    def update_nota_pratica(
        self, nota_id: int, pratica_id: int, contenuto: str,
    ) -> bool:
        sql = """
            UPDATE pratiche.note_pratiche
            SET contenuto = %s
            WHERE id = %s AND pratica_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [contenuto, nota_id, pratica_id])
            return cursor.rowcount > 0

    # Scopo: Elimina una nota (ownership check su pratica_id).
    def delete_nota_pratica(self, nota_id: int, pratica_id: int) -> bool:
        sql = """
            DELETE FROM pratiche.note_pratiche
            WHERE id = %s AND pratica_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [nota_id, pratica_id])
            return cursor.rowcount > 0

    # -- ALLEGATI PRATICHE -----------------------------------------------

    _ALLEGATO_SELECT = """
        a.id, a.pratica_id, a.tipo_allegato_id,
        ta.codice_interno AS tipo_allegato_codice,
        ta.descrizione AS tipo_allegato_descrizione,
        a.nome_file, a.percorso, a.mime_type, a.dimensione,
        a.allegato_padre_id, a.data_insert, a.user_insert
    """

    _ALLEGATO_JOINS = """
        JOIN config.tipi_allegato ta ON ta.id = a.tipo_allegato_id
    """

    # Scopo: Restituisce gli allegati di una pratica con tipo allegato display.
    def list_allegati_pratica(self, pratica_id: int) -> list[dict[str, Any]]:
        sql = f"""
            SELECT {self._ALLEGATO_SELECT}
            FROM pratiche.allegati_pratiche a
            {self._ALLEGATO_JOINS}
            WHERE a.pratica_id = %s
            ORDER BY a.data_insert DESC, a.id DESC
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id])
            return rows_to_list(cursor)

    # Scopo: Crea un record allegato (senza upload file — solo metadati).
    # Il file verra' caricato in una fase successiva.
    def create_allegato_pratica(
        self, pratica_id: int, tipo_allegato_codice: str,
        nome_file: str, *, percorso: str | None = None,
        mime_type: str | None = None, dimensione: int | None = None,
        allegato_padre_id: int | None = None,
    ) -> int:
        with connection.cursor() as cursor:
            # Risolve tipo_allegato_id prima dell'INSERT per errore chiaro
            cursor.execute(
                "SELECT id FROM config.tipi_allegato WHERE codice_interno = %s AND attivo = true",
                [tipo_allegato_codice],
            )
            tipo_row = cursor.fetchone()
            ErrorManager.require(
                tipo_row is not None,
                code="E_CONFIG_MANCANTE",
                message=f"Tipo allegato '{tipo_allegato_codice}' non trovato o non attivo",
            )
            assert tipo_row is not None

            cursor.execute(
                """INSERT INTO pratiche.allegati_pratiche (
                       pratica_id, tipo_allegato_id, nome_file,
                       percorso, mime_type, dimensione, allegato_padre_id
                   ) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                [pratica_id, tipo_row[0], nome_file,
                 percorso, mime_type, dimensione, allegato_padre_id],
            )
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_ALLEGATO_INSERT",
                message="Errore inserimento allegato (RETURNING id nullo)",
            )
            assert row is not None
        return int(row[0])

    # Scopo: Elimina un allegato (ownership check su pratica_id).
    # Gli allegati sono immutabili (no update), solo delete per rimozione.
    def delete_allegato_pratica(self, allegato_id: int, pratica_id: int) -> bool:
        sql = """
            DELETE FROM pratiche.allegati_pratiche
            WHERE id = %s AND pratica_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [allegato_id, pratica_id])
            return cursor.rowcount > 0

    # -- CALCOLI TEMPO ---------------------------------------------------

    # Scopo: Restituisce i calcoli tempo di una pratica arricchiti con stato_tempo live.
    # Usa LEFT JOIN LATERAL su fn_valuta_tempo_esecuzione_da_a per calcolare
    # giorni_rimanenti e stato_tempo (OK/WARNING/CRITICO/SFORATO) in tempo reale.
    def list_calcoli_tempo(self, pratica_id: int) -> list[dict[str, Any]]:
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
            return rows_to_list(cursor)

    # -- FORMULE TEMPO -----------------------------------------------------

    # Scopo: Restituisce le formule tempo attive per un tipo prestazione.
    def list_formule_tempo(self, tipo_prestazione_id: int) -> list[dict[str, Any]]:
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
            return rows_to_list(cursor)

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

    # Scopo: Risolve l'ID di una priorita' pratica da codice_interno
    #        (default NORMALE in crea_pratica — mai id hardcodato).
    def resolve_priorita_pratica(self, codice_interno: str) -> int:
        return self._resolve_stato("config.priorita_pratiche", codice_interno, "priorita")

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
        return str(row[0]), coerce_jsonb_dict(row[1])

    # Scopo: Binding handler legati a un EVENTO di flusso (template_flussi_handler_eventi).
    # Generalizza il dispatch oltre l'avvio: per (template, evento) restituisce gli
    # handler attivi il cui esito_richiesto combacia con l'esito effettivo (NULL =
    # qualsiasi esito), ordinati per sequenza. Lista di (handler_key, handler_params).
    def get_handler_eventi(
        self, template_flusso_id: int, evento: str, esito: str | None,
    ) -> list[tuple[str, dict[str, Any]]]:
        sql = """
            SELECT hf.handler_key, tfhe.handler_params
            FROM pratiche.template_flussi_handler_eventi tfhe
            JOIN pratiche.handler_flussi hf ON hf.id = tfhe.handler_id
            WHERE tfhe.template_flusso_id = %s
              AND tfhe.evento = %s
              AND tfhe.attivo = true
              AND hf.attivo = true
              AND (tfhe.esito_richiesto IS NULL OR tfhe.esito_richiesto = %s)
            ORDER BY tfhe.sequenza, tfhe.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [template_flusso_id, evento, esito])
            rows = cursor.fetchall()
        return [(str(r[0]), coerce_jsonb_dict(r[1])) for r in rows]

    # -- TIPO PRESTAZIONE ------------------------------------------------

    # Scopo: Legge pre_attivazione e post_attivazione dal tipo prestazione.
    # Usato dal service per il guard di ammissibilita' pratica.
    def get_tipo_prestazione_attivazione(self, tipo_prestazione_id: int) -> dict[str, bool]:
        sql = """
            SELECT pre_attivazione, post_attivazione
            FROM pratiche.tipi_prestazione
            WHERE id = %s AND attivo = true
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo_prestazione_id])
            row = cursor.fetchone()
        ErrorManager.require(
            row is not None,
            code="E_CONFIG_MANCANTE",
            message=f"Tipo prestazione {tipo_prestazione_id} non trovato o non attivo",
        )
        assert row is not None
        return {"pre_attivazione": bool(row[0]), "post_attivazione": bool(row[1])}

    # -- CODA LAVORO OPERATORE ------------------------------------------

    # Scopo: Restituisce la coda di lavoro di un operatore su tre livelli
    #        (ASSEGNATO, COMPETENZA, REPARTO) chiamando la funzione DB.
    def list_coda_lavoro(
        self,
        risorsa_umana_id: int,
        emittente_fiscale_id: int,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT *
            FROM pratiche.fn_coda_lavoro_operatore(%s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [risorsa_umana_id, emittente_fiscale_id])
            return rows_to_list(cursor)

    # -- PRENDI IN CARICO FLUSSO -----------------------------------------

    # Scopo: Assegna un flusso DA_ESEGUIRE all'operatore, verificando competenza.
    # Delega alla funzione DB che gestisce lock (FOR UPDATE) e validazione.
    # Ritorna True se assegnato, False se gia' assegnato allo stesso operatore.
    def prendi_in_carico_flusso(
        self,
        flusso_id: int,
        risorsa_umana_id: int,
    ) -> bool:
        sql = """
            SELECT pratiche.fn_prendi_in_carico_flusso(%s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [flusso_id, risorsa_umana_id])
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_FLUSSO_PRESA_IN_CARICO",
                message="Errore presa in carico flusso",
            )
            assert row is not None
        return bool(row[0])

    # -- COMPETENZE FLUSSI -----------------------------------------------

    # Scopo: Restituisce le competenze flussi con display fields da JOIN.
    def list_competenze_flussi(self) -> list[dict[str, Any]]:
        sql = """
            SELECT cf.id, cf.template_flusso_id, cf.unita_organizzativa_id,
                   cf.risorsa_umana_id, cf.attivo,
                   tf.codice AS template_flusso_codice,
                   tf.descrizione AS template_flusso_descrizione,
                   uo.descrizione AS unita_organizzativa_descrizione,
                   sog.ragione_sociale_completa AS risorsa_umana_display
            FROM pratiche.competenze_flussi cf
            JOIN pratiche.template_flussi tf ON tf.id = cf.template_flusso_id
            JOIN config.unita_organizzative uo ON uo.id = cf.unita_organizzativa_id
            JOIN anagrafiche.risorse_umane ru ON ru.id = cf.risorsa_umana_id
            LEFT JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ru.soggetto_ruolo_id
            LEFT JOIN anagrafiche.soggetti sog ON sog.id = sr.soggetto_id
            ORDER BY tf.codice, uo.descrizione, sog.ragione_sociale_completa
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return rows_to_list(cursor)

    # Scopo: Crea una competenza flusso e ritorna l'ID.
    def create_competenza_flusso(self, data: dict[str, Any]) -> int:
        sql = """
            INSERT INTO pratiche.competenze_flussi (
                template_flusso_id, unita_organizzativa_id, risorsa_umana_id, attivo
            ) VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        params = [
            data["template_flusso_id"],
            data["unita_organizzativa_id"],
            data["risorsa_umana_id"],
            data.get("attivo", True),
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            ErrorManager.require(
                row is not None,
                code="E_COMPETENZA_INSERT",
                message="Errore inserimento competenza flusso (RETURNING id nullo)",
            )
            assert row is not None
        return int(row[0])

    # Scopo: Elimina una competenza flusso per ID.
    def delete_competenza_flusso(self, competenza_id: int) -> bool:
        sql = """
            DELETE FROM pratiche.competenze_flussi
            WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [competenza_id])
            return cursor.rowcount > 0

    # -- VERIFICA STATO BA SOGGETTO (cross-schema) ----------------------

    # Scopo: Verifica se il soggetto ha un billing_account attivo per l'emittente.
    # Ritorna True se esiste un BA con data_attivazione NOT NULL e data_chiusura IS NULL.
    # Usato dal guard pre/post-attivazione in crea_pratica.
    # La query attraversa: clienti → billing_account → istanze_utilities.
    def ha_ba_attivo(self, soggetto_id: str, emittente_fiscale_id: int) -> bool:
        # Scope emittente via fn ufficiale sul BA: l'istanza NON ha un
        # emittente (la relazione vive su billing_account -> efba, fallback
        # gestore default incapsulato nella fn, che ritorna la PK reale
        # dell'EF — feedback_emittente_pk_vs_soggetto_ruolo).
        sql = """
            SELECT EXISTS (
                SELECT 1
                FROM anagrafiche.clienti cl
                JOIN anagrafiche.billing_account ba ON ba.id = cl.billing_account_id
                JOIN anagrafiche.istanze_utilities iu ON iu.id = cl.istanza_utility_id
                WHERE iu.soggetto_id = %s::uuid
                  AND anagrafiche.fn_get_emittente_fiscale_pk(ba.id) = %s
                  AND cl.data_attivazione IS NOT NULL
                  AND cl.data_chiusura IS NULL
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id, emittente_fiscale_id])
            row = cursor.fetchone()
        return bool(row[0]) if row else False
