# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository core per lookup anagrafiche e config.
#        Endpoint: tipi di indirizzo proponibili (natura, tipo di ruolo), autocomplete comuni,
#        tipi soggetto dettaglio con natura e policy,
#        search stradario per autocomplete vie.
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.db._helpers import fetch_paged_with_total, pattern_contiene, row_to_dict, rows_to_list

from typing import Any, ClassVar

from django.db import connection


# Scopo: La riga di `config.tipi_soggetto_dettaglio` come la legge il form del
#        soggetto: la natura e le regole che ne discendono (CF/P.IVA, dati
#        societari, sesso, regime fiscale). Il chiamante aggiunge WHERE e ORDER BY.
# ⭐ BB (regola del 2, ok Tid 2026-10-11): la leggono il lookup generico
#    (`list_tipi_soggetto_dettaglio`) e il risolutore per ruolo
#    (`SoggettiRepository.get_config_resolver`), e alimentano lo STESSO form.
#    Erano due elenchi di colonne, e divergevano: per l'ente il lookup diceva
#    `natura_soggetto = 'ENC'` (era `ts.id`), il risolutore `'ENTE'` (l'enum).
# ⛔ `natura_soggetto` e' l'ENUM `config.natura_soggetto_enum`, come la colonna
#    di cui porta il nome; il codice della macro-tipologia (`PF`, `PG`, `ENC`)
#    e' `tipo_soggetto_id`. Una colonna nuova che il form deve leggere si
#    aggiunge QUI, e arriva a tutti e due.
SQL_TIPI_SOGGETTO_DETTAGLIO = """
    SELECT tsd.id, tsd.codice_interno, tsd.descrizione,
           ts.id AS tipo_soggetto_id,
           ts.natura_soggetto,
           tsd.cf_obbligatorio, tsd.piva_obbligatoria,
           tsd.formato_cf, tsd.formato_piva,
           tsd.dati_societari_policy, tsd.sesso_policy,
           -- Regime fiscale: il form mostra i due flag solo dove la natura
           -- li ammette; la regola la presidia `trgfn_soggetti_guard_regime_pa`
           -- (brief-db-dati-fiscali-e-societari-del-soggetto, parte A).
           tsd.cliente_pa_ammesso, tsd.split_payment_ammesso
      FROM config.tipi_soggetto_dettaglio tsd
      JOIN config.tipi_soggetto ts ON ts.id = tsd.tipo_soggetto_id
"""


class LookupRepository:
    """Lookup lettura per tabelle config/anagrafiche cross-dominio."""

    # Scopo: Restituisce i tipi soggetto dettaglio, con la natura e le regole
    #        che il form del soggetto legge (BB `SQL_TIPI_SOGGETTO_DETTAGLIO`).
    def list_tipi_soggetto_dettaglio(self) -> list[dict[str, Any]]:
        sql = f"{SQL_TIPI_SOGGETTO_DETTAGLIO} ORDER BY tsd.id"
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return rows_to_list(cursor)

    # Scopo: Restituisce i tipi ruolo ammessi per una data natura soggetto.
    # Se natura_soggetto e' fornita, filtra via matrice tipi_ruoli_nature_ammesse.
    # ⚠️ `natura_soggetto` e' l'enum (PF/PG/ENTE), come in ogni altra risposta
    #    (BB `SQL_TIPI_SOGGETTO_DETTAGLIO`): la matrice e' per `tipo_soggetto_id`,
    #    e si passa dalla macro-tipologia. Fino al 2026-10-11 confrontava il codice.
    # Se non fornita, restituisce tutti i ruoli attivi.
    def list_tipi_ruoli_per_natura(
        self, natura_soggetto: str | None = None
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT tr.id, tr.codice_interno, tr.descrizione
              FROM config.tipi_ruoli tr
             WHERE (%s::varchar IS NULL OR NOT EXISTS (
                       SELECT 1 FROM config.tipi_ruoli_nature_ammesse m
                        WHERE m.tipo_ruolo_id = tr.id
                   ) OR EXISTS (
                       SELECT 1 FROM config.tipi_ruoli_nature_ammesse m
                         JOIN config.tipi_soggetto ts ON ts.id = m.tipo_soggetto_id
                        WHERE m.tipo_ruolo_id = tr.id
                          AND ts.natura_soggetto::text = %s
                          AND m.attivo = true
                          AND (m.validita IS NULL OR m.validita @> (SELECT script.fn_data_operativa()))
                   ))
             ORDER BY tr.descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [natura_soggetto, natura_soggetto])
            return rows_to_list(cursor)

    # Scopo: Restituisce le forme giuridiche con policy REA e capitale sociale.
    # Opzionalmente filtrate per tipo_soggetto_dettaglio_id (via matrice).
    # ⭐ Il filtro per natura e' il PREDICATO DEL GUARD,
    #    `anagrafiche.fn_forma_giuridica_ammessa`, con lo stesso «oggi»
    #    (`script.fn_giorno_operativo(now())`): riga di matrice attiva E valida
    #    oggi. Fino al 2026-10-10 qui c'era una EXISTS scritta a mano che
    #    guardava solo `attivo`: il form avrebbe offerto una forma con la riga
    #    di matrice scaduta, che il DB rifiuta (brief-db-dati-fiscali-e-
    #    societari-del-soggetto §8.3). Un predicato, due lettori.
    # ⛔ `fg.codice`, e basta: fino al 2026-10-10 qui c'era
    #    `COALESCE(fg.codice_interno, fg.codice)`, ma `config.forme_giuridiche`
    #    una colonna `codice_interno` non l'ha mai avuta. La query falliva SEMPRE
    #    (dal 2026-03-28), il drawer ingoiava l'errore e la tendina restava vuota:
    #    era il «la forma giuridica e' vuota» del collaudo R-2. I test, col
    #    cursore mockato, non lo vedevano; lo ha visto il primo sul DB vero
    #    (`tests/db/test_dati_fiscali_societari_db`, test 10).
    def list_forme_giuridiche(
        self, tipo_soggetto_dettaglio_id: int | None = None
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT fg.id, fg.codice, fg.descrizione,
                   fg.rea_policy, fg.capitale_sociale_policy, fg.attivo
              FROM config.forme_giuridiche fg
             WHERE fg.attivo = true
               AND (%s::bigint IS NULL
                    OR anagrafiche.fn_forma_giuridica_ammessa(
                           fg.id, %s::bigint, script.fn_giorno_operativo(now())))
             ORDER BY fg.descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo_soggetto_dettaglio_id, tipo_soggetto_dettaglio_id])
            return rows_to_list(cursor)

    # Scopo: I PICKER DEI TIPI DI INDIRIZZO, in una lettura sola (regola del 2,
    #        R-2 di brief-db-copia-indirizzo-soggetto, 2026-11-15). Quattro
    #        funzioni del DB, una per contesto, con lo stesso ritorno: una riga
    #        per tipo di `config.tipi_indirizzi`, con `obbligatorio`, `ammesso`,
    #        il primo motivo (`motivo_codice`, `reason`, `reason_key`,
    #        `reason_valori`) e tutti i `motivi`. Codice e descrizione del tipo
    #        dal catalogo. L'ordine e' quello della funzione (prima gli
    #        ammessi), tenuto con `WITH ORDINALITY`.
    #          - `soggetto` (soggetto salvato, uuid): Aggiungi e la copia;
    #          - `natura` (soggetto da creare, tipo_soggetto_dettaglio_id);
    #          - `ruolo` (ruolo salvato, e l'istanza: NULL = il ruolo);
    #          - `tipo_ruolo` (ruolo da assegnare, tipo_ruolo_id).
    # ⭐ Un tipo NON ammesso resta nell'elenco col suo motivo: chi propone i
    #    tipi lo spegne, non lo nasconde (R-4). Il motivo e' quello della check
    #    che la madre di creazione solleva, quindi il picker non puo' proporre
    #    un tipo che la creazione rifiuta.
    # ⛔ Fino al 2026-11-15 qui c'erano due letture della MATRICE
    #    (`list_matrice_indirizzi`, `list_matrice_indirizzi_ruolo`): una copia
    #    della regola gia' divergente (ignorava validita' e tipi presenti, §3.1
    #    del brief). Ritirate nello stesso giro.
    _PICKER_TIPI_INDIRIZZO: ClassVar[dict[str, str]] = {
        "soggetto": "anagrafiche.fn_tipi_indirizzo_proponibili_soggetto(%s::uuid)",
        "natura": "anagrafiche.fn_tipi_indirizzo_proponibili_natura(%s::bigint)",
        "ruolo": "anagrafiche.fn_tipi_indirizzo_proponibili_ruolo(%s::bigint, %s::bigint)",
        "tipo_ruolo": "anagrafiche.fn_tipi_indirizzo_proponibili_tipo_ruolo(%s::integer, %s::uuid)",
    }

    def list_tipi_indirizzo_proponibili(
        self, contesto: str, *args: Any,
    ) -> list[dict[str, Any]]:
        chiamata = self._PICKER_TIPI_INDIRIZZO[contesto]
        sql = f"""
            SELECT p.tipo_indirizzo_id,
                   ti.codice,
                   ti.codice_interno,
                   ti.descrizione,
                   p.obbligatorio,
                   p.ammesso,
                   p.motivo_codice,
                   p.reason,
                   p.reason_key,
                   p.reason_valori,
                   p.motivi
              FROM {chiamata} WITH ORDINALITY
                   AS p(tipo_indirizzo_id, obbligatorio, ammesso, motivo_codice,
                        reason, reason_key, reason_valori, motivi, ordine)
              JOIN config.tipi_indirizzi ti ON ti.id = p.tipo_indirizzo_id
             ORDER BY p.ordine
        """  # noqa: S608 — `chiamata` da whitelist di classe, valori come parametri
        with connection.cursor() as cursor:
            cursor.execute(sql, list(args))
            return rows_to_list(cursor)

    # Scopo: Il picker dei tipi di indirizzo per un ruolo da assegnare, dal
    #        CODICE del tipo di ruolo (la rotta lo porta per codice). Un codice
    #        sconosciuto e' un elenco vuoto, come prima: passare NULL alla
    #        funzione vorrebbe dire «nessuna matrice, tutti ammessi».
    #        `soggetto_id` e' il soggetto a cui il ruolo si assegna: `None`
    #        finche' non e' scelto (la natura non conta); con il soggetto,
    #        la natura toglie i tipi che non ammette. Un soggetto che non
    #        esiste e' un elenco vuoto (la funzione non da' righe).
    def list_tipi_indirizzo_proponibili_tipo_ruolo(
        self, tipo_ruolo_codice: str, soggetto_id: str | None = None,
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM config.tipi_ruoli WHERE codice_interno = %s",
                [tipo_ruolo_codice],
            )
            row = cursor.fetchone()
        if row is None:
            return []
        return self.list_tipi_indirizzo_proponibili("tipo_ruolo", row[0], soggetto_id)

    # Scopo: Matrice utility ammesse per un tipo ruolo + override specifici di
    #        un'entita' figlia (es. emittente fiscale, fornitore, cliente). LEFT JOIN
    #        tra config.utilities_tipi_ruolo (matrice base) e una tabella di override
    #        del dominio chiamante. Ritorna SEMPRE tutte le utility ammesse per il
    #        ruolo: per quelle non personalizzate dall'entita', i campi override sono
    #        NULL.
    #
    #        Pattern slot/override generico cross-dominio. Whitelist statica delle
    #        coppie (table, fk_col) ammesse per impedire SQL injection sui due
    #        identificatori interpolati con f-string.
    #
    #        Esempio uso:
    #          repo.list_entity_utility_matrix(
    #              entity_soggetto_ruolo_id=50,
    #              tipo_ruolo_codice='EF',
    #              overrides_table='anagrafiche.emittenti_fiscali_utilities',
    #              overrides_fk_column='emittente_soggetto_ruolo_id',
    #          )
    _ALLOWED_UTILITY_OVERRIDES: ClassVar[set[tuple[str, str]]] = {
        ("anagrafiche.emittenti_fiscali_utilities", "emittente_soggetto_ruolo_id"),
    }

    def list_entity_utility_matrix(
        self,
        *,
        entity_soggetto_ruolo_id: int,
        tipo_ruolo_codice: str,
        overrides_table: str,
        overrides_fk_column: str,
    ) -> list[dict[str, Any]]:
        # Whitelist statica: protegge dall'iniezione SQL sui due identificatori
        # (table + colonna FK) che vengono interpolati con f-string. Solo le coppie
        # registrate qui sono ammesse.
        if (overrides_table, overrides_fk_column) not in self._ALLOWED_UTILITY_OVERRIDES:
            raise ValueError(
                f"Coppia (table={overrides_table}, fk_col={overrides_fk_column}) "
                "non ammessa per list_entity_utility_matrix."
            )

        # NB: `config.utilities` NON ha colonna `attivo` (catalogo
        # statico, codice_interno immutabile via lock_columns). Esponiamo
        # `utility_attiva = TRUE` literal per mantenere il contratto col
        # service che usa il campo per calcolare `can_configure` (Fase 4
        # capability data-driven). Se in futuro la tabella aggiunge un
        # campo `attivo`, sostituire con `u.attivo`.
        sql = f"""
            SELECT u.id                              AS utility_id,
                   u.codice                          AS utility_codice,
                   u.descrizione                     AS utility_descrizione,
                   TRUE                              AS utility_attiva,
                   o.id                              AS record_id,
                   o.minimo_soglia_min,
                   o.minimo_soglia_max,
                   o.arrotondamento_importi_dec,
                   o.metodo_arrotondamento_importi,
                   o.attivo                          AS record_attivo,
                   o.data_insert                     AS record_data_insert,
                   o.data_update                     AS record_data_update
              FROM config.utilities u
              JOIN config.utilities_tipi_ruolo utr ON utr.utility_id = u.id
              JOIN config.tipi_ruoli tr            ON tr.id = utr.tipo_ruolo_id
              LEFT JOIN {overrides_table} o
                     ON o.utility_id = u.id
                    AND o.{overrides_fk_column} = %s
             WHERE tr.codice_interno = %s
               AND utr.attivo = true
               AND (utr.validita IS NULL OR utr.validita @> (SELECT script.fn_data_operativa()))
             ORDER BY u.descrizione
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [entity_soggetto_ruolo_id, tipo_ruolo_codice])
            return rows_to_list(cursor)

    # Scopo: Lista utility per un billing account "guidata da emittente"
    #        (refactor operatore-emittenti, sez. 3 del WIP).
    #        Wrapper Python su anagrafiche.fn_lookup_utilities_per_ba.
    #        Politica ibrida (C):
    #          - utility ammesse per il ruolo del soggetto del BA
    #          - filtrate per intersezione con utility ammesse per ruolo EF
    #            dell'emittente associato al BA (specifico → default globale)
    #          - decorate con i parametri override di
    #            emittenti_fiscali_utilities quando esistono per la coppia
    #            (emittente, utility); is_personalizzata_per_ef=true
    #          - le utility "ammesse ma non personalizzate" restano visibili
    #            con i parametri default di sistema
    #
    #        Param p_ruolo_codice_soggetto: 'CL' / 'FO' / 'GE' (codice del
    #        ruolo del soggetto del BA, lato cliente).
    def list_utilities_per_billing_account(
        self, *, billing_account_id: int, ruolo_codice_soggetto: str
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT utility_id,
                   codice,
                   descrizione,
                   is_personalizzata_per_ef,
                   minimo_soglia_min,
                   minimo_soglia_max,
                   arrotondamento_importi_dec,
                   metodo_arrotondamento_importi
              FROM anagrafiche.fn_lookup_utilities_per_ba(%s, %s)
             ORDER BY descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [billing_account_id, ruolo_codice_soggetto])
            return rows_to_list(cursor)

    # Scopo: Lista utility ammesse per un tipo ruolo (es. EF, FO, CL).
    #        Strict mode: ritorna SOLO utility con riga ATTIVA in
    #        config.utilities_tipi_ruolo per tipo_ruolo_codice e periodo
    #        di validita' corrente. Le utility senza alcuna riga in matrice
    #        sono escluse, coerentemente con il trigger DB
    #        script.fn_guard_utility_tipo_ruolo.
    def list_utilities_per_ruolo(
        self, tipo_ruolo_codice: str
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT u.id, u.codice, u.descrizione
              FROM config.utilities u
              JOIN config.utilities_tipi_ruolo utr ON utr.utility_id = u.id
              JOIN config.tipi_ruoli tr            ON tr.id = utr.tipo_ruolo_id
             WHERE tr.codice_interno = %s
               AND utr.attivo = true
               AND (utr.validita IS NULL OR utr.validita @> (SELECT script.fn_data_operativa()))
             ORDER BY u.descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo_ruolo_codice])
            return rows_to_list(cursor)

    # Scopo: Lista utility per popolare la combo "Utility" nei drawer e
    #        nei filtri lista: le utility AMMESSE per il ruolo emittente
    #        fiscale (`EF`) in `config.utilities_tipi_ruolo` (riga attiva e
    #        valida alla data operativa), intersecate — se
    #        `ruolo_codice_soggetto` e' dato (es. 'CL'/'FO') — con quelle
    #        ammesse anche per il ruolo del soggetto.
    # ⛔ NON legge `anagrafiche.emittenti_fiscali_utilities`. Quella tabella e'
    #    OPZIONALE e porta i PARAMETRI di fatturazione di una coppia
    #    (emittente, utility) — soglie della fattura minima, arrotondamento del
    #    totale — non l'elenco delle utility dell'emittente: la sola
    #    ammissibilita' del modello e' `utilities_tipi_ruolo` (changeSet
    #    `20260408-01`, che tolse la guard «almeno una riga per emittente»), e la
    #    funzione DB gemella `fn_lookup_utilities_per_ba` la legge in LEFT JOIN,
    #    come override. Fino al 2026-10-14 questo lookup la usava come filtro:
    #    un emittente con i parametri della sola luce si vedeva sparire il gas
    #    dalla combo (analisi-be-difetti-emersi-verifica-doc-api-core §6).
    #
    #        Ritorna id/codice/codice_interno/descrizione (per combo filtro,
    #        non editing). codice_interno serve al FE per risolvere
    #        DEFAULT_UTILITY (che stocca codice_interno stabile, non id) -> id.
    def list_utilities_per_emittente(
        self,
        ruolo_codice_soggetto: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT u.id, u.codice, u.codice_interno, u.descrizione
              FROM config.utilities u
              -- ammessa per il ruolo EF (emittente fiscale)
              JOIN config.utilities_tipi_ruolo utr_ef
                ON utr_ef.utility_id = u.id
               AND utr_ef.attivo = true
               AND (utr_ef.validita IS NULL OR utr_ef.validita @> (SELECT script.fn_data_operativa()))
              JOIN config.tipi_ruoli tr_ef
                ON tr_ef.id = utr_ef.tipo_ruolo_id
               AND tr_ef.codice_interno = 'EF'
        """
        params: list = []

        # Intersezione opzionale con ruolo soggetto (es. CL, FO).
        if ruolo_codice_soggetto:
            sql += """
              -- ammessa anche per il ruolo del soggetto (es. CL)
              JOIN config.utilities_tipi_ruolo utr_sogg
                ON utr_sogg.utility_id = u.id
               AND utr_sogg.attivo = true
               AND (utr_sogg.validita IS NULL OR utr_sogg.validita @> (SELECT script.fn_data_operativa()))
              JOIN config.tipi_ruoli tr_sogg
                ON tr_sogg.id = utr_sogg.tipo_ruolo_id
               AND tr_sogg.codice_interno = %s
            """
            params.append(ruolo_codice_soggetto)

        sql += " ORDER BY u.descrizione"

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return rows_to_list(cursor)

    # Scopo: Verifica se esiste una configurazione sistema codici per schema/tabella/colonna.
    #        Restituisce la configurazione (prefisso, separatore, usa_sequenza, etc.)
    #        oppure None se non configurato (codice deve essere editabile manualmente).
    def get_sistema_codici(
        self, schema_tabella: str, nome_tabella: str, nome_colonna: str = "codice",
    ) -> dict[str, Any] | None:
        sql = """
            SELECT id, codice_interno, prefisso, separatore,
                   lunghezza_numero, usa_sequenza,
                   schema_tabella, nome_tabella, nome_colonna
              FROM config.sistema_codici
             WHERE schema_tabella = %s
               AND nome_tabella = %s
               AND nome_colonna = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [schema_tabella, nome_tabella, nome_colonna])
            return row_to_dict(cursor)

    # Scopo: Ricerca comuni per autocomplete (ILIKE su descrizione).
    # Restituisce id, descrizione, provincia sigla.
    # Risultato: (lista record, conteggio totale).
    def search_comuni(
        self,
        *,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        search_pattern = pattern_contiene(search)

        sql = """
            SELECT c.id,
                   c.descrizione,
                   p.sigla AS provincia_sigla,
                   COUNT(*) OVER () AS total_count
              FROM config.comuni c
              LEFT JOIN config.province p ON p.id = c.provincia_id
             WHERE (%s::text IS NULL OR c.descrizione ILIKE %s)
             ORDER BY c.descrizione, c.id
             LIMIT %s OFFSET %s
        """
        rows, total_count = fetch_paged_with_total(
            sql, [search_pattern, search_pattern, limit, offset], offset=offset,
        )
        results = [
            {"id": r["id"], "descrizione": r["descrizione"], "provincia_sigla": r["provincia_sigla"]}
            for r in rows
        ]
        return results, total_count

    # Scopo: Ricerca vie (stradario) per autocomplete, filtrate per comune.
    # Chiama script.fn_search_stradario(p_comune_id, p_search, p_limit).
    # Restituisce stradario_id, indirizzo_normalizzato, comune, provincia, CAP.
    # Risultato: lista record (la funzione DB gestisce gia' il limit).
    def search_stradario(
        self,
        *,
        comune_id: int | None = None,
        search: str | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT *
              FROM script.fn_search_stradario(
                       p_comune_id := %s,
                       p_search    := %s,
                       p_limit     := %s
                   )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [comune_id, search, limit])
            return rows_to_list(cursor)

    # Scopo: Lista conti contabili filtrati per tipo (A=Acquisto, V=Vendita).
    # Lookup dedicato: espone tipo_conto che il lookup generico non ritorna.
    # Ordinamento per codice (codice contabile e' numerico-parlante).
    # Whitelist del tipo per evitare SQL injection sul parametro.
    def list_conti_contabili(self, *, tipo: str | None = None) -> list[dict[str, Any]]:
        if tipo is not None and tipo not in {"A", "V"}:
            raise ValueError(
                f"tipo_conto '{tipo}' non valido. Ammessi: 'A' (acquisto), 'V' (vendita)."
            )
        sql = """
            SELECT id, codice, descrizione, tipo_conto
              FROM config.conti_contabili
             WHERE (%s::char IS NULL OR tipo_conto = %s::char)
             ORDER BY codice
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo, tipo])
            return rows_to_list(cursor)

    # Scopo: IL VOCABOLARIO DEI TIPI DI ENTITA' (`config.tipi_entita`), per i
    #        filtri e i picker che nominano «su quale cosa» e' successo qualcosa
    #        (il giornale trasversale; domani il resolver dei bersagli).
    # ⛔ Lookup dedicato e non generico: la tabella ha PK `codice` (testo) e
    #    nessun `id`/`descrizione` — `fn_get_lookup_codici` pretende un id
    #    intero. Cio' che serve al client e' l'INDIRIZZO i18n che il DB dichiara
    #    (`etichetta_key`) e la chiave con cui si raggiunge l'entita'
    #    (`key_selector`), non una descrizione.
    # ⚠️ Solo i tipi VIVI (`obsoleto_dal IS NULL`): un tipo ritirato resta a
    #    catalogo per leggere il diario, non per essere scelto in un filtro.
    def list_tipi_entita(self) -> list[dict[str, Any]]:
        sql = """
            SELECT codice, etichetta_key, key_selector
              FROM config.tipi_entita
             WHERE obsoleto_dal IS NULL
             ORDER BY codice
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return rows_to_list(cursor)

    # Scopo: IL REGISTRO DELLE AZIONI DI RIGA (`config.azioni_riga`), in sola
    #        lettura: per ogni azione, le due colonne della sua superficie che
    #        dicono perche' il pulsante e' spento (`colonna_motivo`, il codice;
    #        `colonna_motivo_chiave`, la chiave i18n). Il frontend costruisce
    #        il pulsante di riga leggendo da qui QUALI colonne guardare, invece
    #        di scriverle in ogni componente (brief-modello-documento-vendita
    #        §15.11.1, BE-3; F-5, Q-F5).
    # ⛔ Lookup dedicato e non generico: la tabella non ha `codice` (solo
    #    `codice_interno`), e servono due colonne oltre a quelle del contratto
    #    generico, mentre la variante specializzata ne porta una.
    # ⚠️ Solo le azioni ATTIVE: un'azione spenta non ha piu' un pulsante.
    #    Superficie, `fn_check` e verbo restano al DB (il presidio pgTAP del
    #    registro li verifica): al client servono solo i nomi delle colonne.
    def list_azioni_riga(self) -> list[dict[str, Any]]:
        sql = """
            SELECT codice_interno, colonna_motivo, colonna_motivo_chiave
              FROM config.azioni_riga
             WHERE attivo IS TRUE
             ORDER BY codice_interno
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return rows_to_list(cursor)

    # Scopo: Ricerca vie su stradario_generale (senza comune/CAP) per autocomplete via nuova.
    # Chiama script.fn_search_stradario_generale(p_search, p_toponomastica_id, p_limit).
    # Restituisce stradario_generale_id, toponomastica_id, toponimo, denominazione, indirizzo_normalizzato.
    def search_stradario_generale(
        self,
        *,
        search: str | None = None,
        toponomastica_id: int | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT *
              FROM script.fn_search_stradario_generale(
                       p_search           := %s,
                       p_toponomastica_id := %s,
                       p_limit            := %s
                   )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [search, toponomastica_id, limit])
            return rows_to_list(cursor)
