# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB per preventivi vendita (CRUD testata, righe, indirizzi, integrazione).
# ------------------------------------------------------------

# Repository preventivi vendita: letture su viste DB denormalizzate,
# scritture dirette su tabelle, chiamate a funzioni DB per operazioni complesse.
# Il ricalcolo totali e' gestito da trigger AFTER su preventivi_righe.

import json
from datetime import date
from typing import Any

from django.db import connection

from apps.core.db._helpers import call_jsonb_fn, row_to_dict, rows_to_list
from apps.vendite.db._componenti_repo_mixin import ComponentiRepositoryMixin
from apps.vendite.types import (
    PreventivoDetailRow,
    PreventivoIndirizzoRow,
    PreventivoListRow,
    PreventivoPraticaRow,
    PreventivoRigaRow,
    PreventivoStatoFatturazioneRow,
)


class PreventiviRepository(ComponentiRepositoryMixin):
    """Repository preventivi.

    Eredita da `ComponentiRepositoryMixin` per il CRUD componenti BoM
    modello unificato (`preventivi_righe_componenti`). I metodi specifici
    `init_componenti_riga` (chiama `fn_preventivo_riga_componenti_init`)
    e `preview_componenti_riga` (chiama `fn_preventivo_riga_componenti_preview`)
    sono definiti localmente.
    """

    # Configurazione mixin componenti.
    _componenti_table_name = "vendite.preventivi_righe_componenti"
    _componenti_fk_riga = "riga_preventivo_id"

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Testata (via vista vw_preventivi_list)
    # ══════════════════════════════════════════════════════════

    # Scopo: Restituisce elenco preventivi paginato dalla vista denormalizzata.
    # La vista include emittente_fiscale_id per scope permessi.
    # Perimetro: sola lettura; nessun side-effect.
    # Risultato: tuple (lista PreventivoListRow, conteggio totale).
    def list_preventivi(
        self,
        *,
        stato_codice: str | None = None,
        billing_account_id: int | None = None,
        utility_id: int | None = None,
        data_da: date | None = None,
        data_al: date | None = None,
        search: str | None = None,
        solo_revisione_attiva: bool = True,
        auth_user_id: int | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[PreventivoListRow], int]:
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))

        conditions: list[str] = []
        params: list[Any] = []

        # Filtri dinamici parametrizzati
        if stato_codice is not None:
            conditions.append("v.stato_codice = %s")
            params.append(stato_codice)
        if billing_account_id is not None:
            conditions.append("v.billing_account_id = %s")
            params.append(billing_account_id)
        if utility_id is not None:
            conditions.append("v.utility_id = %s")
            params.append(utility_id)
        if data_da is not None:
            conditions.append("v.data >= %s")
            params.append(data_da)
        if data_al is not None:
            conditions.append("v.data <= %s")
            params.append(data_al)
        if search and len(search) >= 3:
            conditions.append("(v.numero ILIKE %s OR v.cliente_denominazione ILIKE %s)")
            # cliente_denominazione nella vista e' ragione_sociale_completa
            like = f"%{search}%"
            params.extend([like, like])
        # Filtro revisione attiva: di default mostra solo l'ultima revisione
        # per numero. La condizione corretta e' "non esiste una revisione
        # successiva per lo stesso numero": copre sia i preventivi mai
        # revisionati (single-rev, is_revision_attiva=false di default DDL)
        # sia le revisioni effettive (rev N+1 dopo fn_crea_revisione_preventivo).
        # NB: NON usiamo `is_revision_attiva IS TRUE` perche' il flag e' false
        # di default su crea_preventivo: filtrarlo escluderebbe quasi tutti i
        # preventivi single-revision. Subquery NOT EXISTS supportata da indice
        # implicito su (numero, rev). Quando l'operatore vuole vedere lo
        # storico, il FE passa solo_revisione_attiva=false.
        if solo_revisione_attiva:
            conditions.append(
                "NOT EXISTS ("
                " SELECT 1 FROM vendite.preventivi p2"
                "  WHERE p2.numero = v.numero AND p2.rev > v.rev"
                ")"
            )

        # Scope emittente: la vista espone emittente_fiscale_id (PK reale di
        # anagrafiche.emittenti_fiscali.id, post brief preventivi rev2). Usa
        # quindi fn_get_emittenti_scope_pk_ids (NON _sr_ids che mappa a
        # soggetto_ruolo_id). Vedi guida soggetti-e-ruoli §5b + memoria
        # feedback_emittente_pk_vs_soggetto_ruolo per il pattern duale SR vs PK.
        if auth_user_id is not None:
            conditions.append(
                "(script.fn_get_emittenti_scope_pk_ids(%s) IS NULL "
                "OR v.emittente_fiscale_id = ANY("
                "script.fn_get_emittenti_scope_pk_ids(%s)))"
            )
            params.extend([auth_user_id, auth_user_id])

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        count_sql = f"SELECT COUNT(*) FROM vendite.vw_preventivi_list v {where}"
        # Tiebreaker v.id obbligatorio per paginazione deterministica
        # (frontend-standards "REGOLA CRITICA: Paginazione deterministica").
        # Senza id, righe con stessa data/numero (es. revisioni) possono
        # comparire duplicate o sparire fra pagine consecutive.
        data_sql = f"""
            SELECT * FROM vendite.vw_preventivi_list v
            {where}
            ORDER BY v.data DESC, v.numero DESC, v.id
            LIMIT %s OFFSET %s
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            total_count = row[0] if row else 0

            cursor.execute(data_sql, [*params, safe_limit, safe_offset])
            results = rows_to_list(cursor)

        return results, total_count

    # Scopo: Restituisce dettaglio singolo preventivo con tutte le decodifiche.
    # Usa query diretta (non vista lista) per includere campi extra (meta, storicizza, audit).
    def get_preventivo(self, preventivo_id: int) -> PreventivoDetailRow | None:
        sql = """
            SELECT
                p.id,
                p.uid::text AS uid,
                p.numero,
                p.rev,
                p.is_revision_attiva,
                -- has_next_revision: true se esiste un'altra riga con stesso
                -- numero e rev maggiore (= questo preventivo e' superseded).
                -- Affidabile indipendentemente dal flag is_revision_attiva
                -- (default DDL false: non e' single source of truth — vedi
                -- nota in repo.list_preventivi).
                EXISTS (
                  SELECT 1 FROM vendite.preventivi p2
                   WHERE p2.numero = p.numero AND p2.rev > p.rev
                ) AS has_next_revision,
                p.data::text AS data,
                p.stato_doc_preventivo_id,
                sdp.codice_interno AS stato_codice_interno,
                sdp.codice AS stato_codice,
                sdp.descrizione AS stato_descrizione,
                p.billing_account_id,
                s.ragione_sociale_completa AS cliente_denominazione,
                p.utility_id,
                u.descrizione AS utility_descrizione,
                p.istanza_utility_id,
                p.valuta_id,
                v.codice AS valuta_codice,
                p.termine_pagamento_id,
                tp.descrizione AS termine_pagamento_descrizione,
                p.validita_dal::text AS validita_dal,
                p.validita_al::text AS validita_al,
                p.competenza_mese::text AS competenza_mese,
                COALESCE(p.fatturazione_immediata, false) AS fatturazione_immediata,
                p.totale_imponibile::text AS totale_imponibile,
                p.totale_iva::text AS totale_iva,
                p.totale_documento::text AS totale_documento,
                p.emittente_fiscale_id,
                ef.codice AS emittente_fiscale_codice,
                COALESCE(s_ef.ragione_sociale_completa, ef.descrizione)
                    AS emittente_fiscale_descrizione,
                -- Flag informativo (UX): il BA ha un contratto ATTIVO per
                -- la coppia (utility, data preventivo)? Se false il pricing
                -- delle righe passera' dallo STADIO 2 (matrice categoria→
                -- listino) e l'operatore puo' anticipare l'eventuale errore
                -- E_CATEGORIA_LISTINO_NON_MAPPATA. Non bloccante.
                -- Filtro su c.utility_id nativo (colonna NOT NULL di
                -- vendite.contratti): coerente con fn_resolve_prezzo_listino_v2.
                -- Non usare vendite.contratti_utilities qui: e' snapshot
                -- precontrattuale OPZIONALE — se assente il contratto risulta
                -- erroneamente "non attivo" pur essendo presente.
                EXISTS (
                    SELECT 1
                      FROM vendite.contratti c
                      JOIN config.stati_doc_contratti sdc
                        ON sdc.id = c.stato_doc_contratto_id
                     WHERE c.billing_account_id = p.billing_account_id
                       AND c.utility_id = p.utility_id
                       AND sdc.codice_interno = 'ATTIVO'
                       AND c.validita @> p.data
                ) AS ba_ha_contratto_attivo,
                p.storicizza,
                p.meta,
                p.data_insert::text AS data_insert,
                p.user_insert,
                p.data_update::text AS data_update,
                p.user_update
            FROM vendite.preventivi p
            JOIN config.stati_doc_preventivi sdp ON sdp.id = p.stato_doc_preventivo_id
            LEFT JOIN anagrafiche.billing_account ba ON ba.id = p.billing_account_id
            LEFT JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
            LEFT JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
            LEFT JOIN config.utilities u ON u.id = p.utility_id
            LEFT JOIN config.valute v ON v.id = p.valuta_id
            LEFT JOIN config.termini_pagamento tp ON tp.id = p.termine_pagamento_id
            -- Decode emittente fiscale: codice + ragione sociale (con fallback
            -- a descrizione plain dell'EF). Pattern allineato a documenti repo
            -- per UX uniforme nei drawer (EmittenteFiscaleField in modalita' edit
            -- legge questi campi denormalizzati senza round-trip aggiuntivo).
            LEFT JOIN anagrafiche.emittenti_fiscali ef ON ef.id = p.emittente_fiscale_id
            LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON sr_ef.id = ef.soggetto_ruolo_id
            LEFT JOIN anagrafiche.soggetti s_ef ON s_ef.id = sr_ef.soggetto_id
            WHERE p.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return row_to_dict(cursor)

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Righe (via vista vw_preventivi_righe_dettaglio)
    # ══════════════════════════════════════════════════════════

    # Scopo: Restituisce righe preventivo. Replica la proiezione di
    # `vw_preventivi_righe_dettaglio` aggiungendo `stato_approvazione_prezzo`
    # e `pratica_approvazione_prezzo_id` (Sprint E L3) che la vista NON
    # espone — la vista DB e' di Sprint <E e va estesa col team DB. Finche'
    # la patch DB non landa, leggiamo dalla tabella nativa con i medesimi
    # LEFT JOIN per non perdere il tag UI "In approvazione" sulle righe PENDING.
    # NB: importo_iva_riga e' rimosso (l'IVA per riga e' concettualmente
    # errata, art. 21 DPR 633/72: IVA si calcola sull'aggregato per aliquota,
    # vedi vendite.preventivi_riepiloghi_iva).
    def list_righe(self, preventivo_id: int) -> list[PreventivoRigaRow]:
        sql = """
            SELECT
                pr.id,
                pr.preventivo_id,
                pr.ordine,
                pr.attivo,
                pr.articolo_id,
                a.codice                AS articolo_codice,
                a.descrizione           AS articolo_descrizione,
                pr.descrizione,
                pr.quantita,
                pr.qta_operativa,
                pr.factor_to_base,
                pr.uom_operativa_id,
                um.codice               AS uom_codice,
                pr.prezzo_unitario,
                pr.sconto_percentuale,
                pr.iva_id,
                iva.codice              AS iva_codice,
                iva.descrizione         AS iva_descrizione,
                iva.aliquota_iva        AS iva_aliquota,
                ROUND(
                    (pr.quantita * pr.prezzo_unitario) *
                    (1::numeric - COALESCE(pr.sconto_percentuale, 0::numeric) / 100::numeric),
                    2
                ) AS importo_riga,
                (pr.quantita * pr.prezzo_unitario) *
                    (1::numeric - COALESCE(pr.sconto_percentuale, 0::numeric) / 100::numeric)
                    AS imponibile_riga_full,
                pr.meta,
                pr.data_insert,
                pr.data_update,
                -- Sprint E (autorizzazioni prezzi L3): flag + FK pratica
                -- per il tag UI "In approvazione" su righe PENDING.
                pr.stato_approvazione_prezzo,
                pr.pratica_approvazione_prezzo_id,
                -- Refactor componenti BoM CASO A 2026-05-11:
                -- flag derivato per il FE (DataTable expander). Vero quando
                -- la riga padre ha almeno un componente CASO A attivo nella
                -- tabella parallela `preventivi_righe_componenti`. Permette
                -- al FE di mostrare il chevron solo dove serve, senza N+1
                -- fetch lato client.
                EXISTS (
                    SELECT 1
                      FROM vendite.preventivi_righe_componenti prc
                     WHERE prc.riga_preventivo_id = pr.id
                       AND prc.attivo IS TRUE
                ) AS is_composito_caso_a
              FROM vendite.preventivi_righe pr
              LEFT JOIN catalogo.articoli a   ON a.id   = pr.articolo_id
              LEFT JOIN catalogo.unita_misura um ON um.id = pr.uom_operativa_id
              LEFT JOIN config.iva iva        ON iva.id = pr.iva_id
             WHERE pr.preventivo_id = %s
               AND pr.attivo IS TRUE
             ORDER BY pr.ordine, pr.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return rows_to_list(cursor)

    # Scopo: Conta righe attive per stato_approvazione_prezzo. Single SELECT
    #        ottimizzata: serve a `get_preventivo` per derivare il flag
    #        "frozen_for_pending/rejected_pricing" senza caricare l'intero
    #        elenco righe (ognuna con N JOIN). Ritorna sempre tutte le chiavi
    #        rilevanti — chiavi mancanti = 0.
    def count_righe_per_stato_approvazione(
        self, preventivo_id: int,
    ) -> dict[str, int]:
        sql = """
            SELECT stato_approvazione_prezzo, COUNT(*) AS n
              FROM vendite.preventivi_righe
             WHERE preventivo_id = %s
               AND attivo IS TRUE
             GROUP BY stato_approvazione_prezzo
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            rows = cursor.fetchall()
        out = {"PENDING": 0, "APPROVED": 0, "REJECTED": 0, "TOTAL": 0}
        for stato, n in rows:
            n = int(n)
            out["TOTAL"] += n
            if stato in out:
                out[stato] = n
        return out

    # Scopo: Carica una singola riga preventivo via lookup mirato per id.
    #        Replica la stessa proiezione di list_righe (denormalizzazioni
    #        articolo/uom/iva + flag approvazione_prezzo) ma senza caricare
    #        tutto l'elenco quando serve solo una riga (es. aggiorna_riga).
    def get_riga(self, riga_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT
                pr.id,
                pr.preventivo_id,
                pr.ordine,
                pr.attivo,
                pr.articolo_id,
                a.codice                AS articolo_codice,
                a.descrizione           AS articolo_descrizione,
                pr.descrizione,
                pr.quantita,
                pr.qta_operativa,
                pr.factor_to_base,
                pr.uom_operativa_id,
                um.codice               AS uom_codice,
                pr.prezzo_unitario,
                pr.sconto_percentuale,
                pr.iva_id,
                iva.codice              AS iva_codice,
                iva.descrizione         AS iva_descrizione,
                iva.aliquota_iva        AS iva_aliquota,
                pr.meta,
                pr.stato_approvazione_prezzo,
                pr.pratica_approvazione_prezzo_id,
                EXISTS (
                    SELECT 1
                      FROM vendite.preventivi_righe_componenti prc
                     WHERE prc.riga_preventivo_id = pr.id
                       AND prc.attivo IS TRUE
                ) AS is_composito_caso_a
              FROM vendite.preventivi_righe pr
              LEFT JOIN catalogo.articoli a   ON a.id   = pr.articolo_id
              LEFT JOIN catalogo.unita_misura um ON um.id = pr.uom_operativa_id
              LEFT JOIN config.iva iva        ON iva.id = pr.iva_id
             WHERE pr.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [riga_id])
            return row_to_dict(cursor)

    # Scopo: Restituisce il riepilogo IVA aggregato del preventivo dalla view
    #        denormalizzata. Una riga per gruppo (iva_id, natura, esigibilita,
    #        split_payment) — sui preventivi natura/esigibilita/split sono
    #        sempre NULL (struttura allineata a fatture_riepiloghi_iva per
    #        coerenza). Imponibile e imposta sono ROUND 2 sull'aggregato per
    #        aliquota (regola fiscale: DPR 633/72 art. 21 + DM 24/12/93).
    #        Popolata dal trigger AFTER su preventivi_righe via
    #        fn_ricalcola_riepilogo_iva_preventivo: il chiamante non orchestra
    #        il ricalcolo, legge solo lo stato corrente.
    def list_riepilogo_iva(self, preventivo_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT id, preventivo_id, iva_id, iva_codice, iva_descrizione,
                   iva_aliquota, natura_id, natura_codice,
                   esigibilita, split_payment,
                   imponibile, imposta, arrotondamento, totale_riga
              FROM vendite.vw_preventivi_riepilogo_iva_dettaglio
             WHERE preventivo_id = %s
             ORDER BY iva_aliquota NULLS LAST, iva_id NULLS LAST
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return rows_to_list(cursor)

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Indirizzi
    # ══════════════════════════════════════════════════════════

    # Scopo: Restituisce indirizzi preventivo con tipo.
    def list_indirizzi(self, preventivo_id: int) -> list[PreventivoIndirizzoRow]:
        sql = """
            SELECT
                pi.id,
                pi.preventivo_id,
                pi.tipo_indirizzo_id,
                ti.descrizione AS tipo_indirizzo_descrizione,
                pi.snapshot,
                pi.origine_indirizzo_id,
                pi.origine_soggetto_ruolo_id
            FROM vendite.preventivi_indirizzi pi
            LEFT JOIN config.tipi_indirizzi ti ON ti.id = pi.tipo_indirizzo_id
            WHERE pi.preventivo_id = %s
            ORDER BY pi.tipo_indirizzo_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return rows_to_list(cursor)

    # Scopo: Capability del preventivo per il detail API (Fase 1 refactor
    #        frontend vendite). Wrapper su `script.fn_available_actions_preventivo`
    #        che ritorna jsonb con available_actions, can_edit_*,
    #        can_push_commessa(+ reason), can_create_revisione, non_editable_fields,
    #        stato_codice. Il blob e' opaco lato Python: viene passato al FE
    #        intatto perche' la logica di rendering dipende solo dai metadata.
    #        Ritorna {} se la fn ritorna NULL (preventivo inesistente — caller
    #        deve aver gia' verificato l'esistenza).
    def get_capabilities(self, preventivo_id: int) -> dict[str, Any]:
        return call_jsonb_fn("script.fn_available_actions_preventivo", preventivo_id)

    # ══════════════════════════════════════════════════════════
    #  SCRITTURE — Testata
    # ══════════════════════════════════════════════════════════

    # Scopo: Inserisce un nuovo preventivo e restituisce id e uid.
    #        emittente_fiscale_id e' opzionale: se None il trigger DB
    #        (vendite.trgfn_preventivi_default_emittente, fase _a10_default)
    #        lo valorizza da GUC app.current_user_id via
    #        script.fn_resolve_emittente_for_user. Va passato esplicito solo
    #        per il caso admin globale (utente senza emittente assegnato che
    #        sceglie l'emittente del documento).
    def create_preventivo(
        self,
        *,
        billing_account_id: int | None,
        utility_id: int,
        istanza_utility_id: int | None = None,
        emittente_fiscale_id: int | None = None,
        valuta_id: int | None = None,
        termine_pagamento_id: int | None = None,
        validita_dal: date | None = None,
        validita_al: date | None = None,
        competenza_mese: date | None = None,
        fatturazione_immediata: bool = False,
        stato_doc_preventivo_id: int,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO vendite.preventivi (
                billing_account_id, utility_id, istanza_utility_id,
                emittente_fiscale_id,
                valuta_id, termine_pagamento_id,
                validita_dal, validita_al, competenza_mese,
                fatturazione_immediata, stato_doc_preventivo_id, meta
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
            )
            RETURNING id, uid::text AS uid, numero
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                billing_account_id, utility_id, istanza_utility_id,
                emittente_fiscale_id,
                valuta_id, termine_pagamento_id,
                validita_dal, validita_al, competenza_mese,
                fatturazione_immediata, stato_doc_preventivo_id,
                json.dumps(meta or {}),
            ])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna campi modificabili della testata preventivo.
    # Accetta anche None per azzerare campi nullable.
    # Campi jsonb (meta) vengono serializzati con json.dumps e cast ::jsonb.
    def update_preventivo(
        self,
        preventivo_id: int,
        **kwargs: Any,
    ) -> bool:
        fields: list[str] = []
        params: list[Any] = []
        for col, val in kwargs.items():
            if isinstance(val, dict):
                fields.append(f"{col} = %s::jsonb")
                params.append(json.dumps(val))
            else:
                if isinstance(val, str):
                    val = val.strip()
                fields.append(f"{col} = %s")
                params.append(val)
        if not fields:
            return False
        params.append(preventivo_id)
        sql = f"UPDATE vendite.preventivi SET {', '.join(fields)} WHERE id = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount > 0

    # Scopo: Hard-delete preventivo. Usato dal flusso "abbandono bozza"
    #        (preventivi BOZZA orfani senza righe). I guard di dominio
    #        (stato BOZZA, zero righe, no pratiche/commesse collegate) sono
    #        applicati lato service prima di chiamare questo metodo. Cascade
    #        FK gestita a livello DB (preventivi_righe e preventivi_indirizzi
    #        hanno ON DELETE CASCADE su preventivo_id).
    # Risultato: rowcount > 0 se preventivo eliminato, False se id inesistente.
    def delete_preventivo(self, preventivo_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM vendite.preventivi WHERE id = %s",
                [preventivo_id],
            )
            return cursor.rowcount > 0

    # Scopo: Cambia stato preventivo invocando la funzione DB.
    # La funzione valida transizione via config.transizioni_stati_preventivi,
    # guard su righe/totale per EMESSO, blocco annullamento con commessa attiva.
    def cambia_stato(
        self, preventivo_id: int, nuovo_stato_codice: str, user: str
    ) -> dict[str, Any]:
        sql = """
            SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, %s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id, nuovo_stato_codice, user])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Crea nuova revisione invocando la funzione DB.
    # Copia testata + righe attive + indirizzi, disattiva revisione precedente.
    def crea_revisione(self, preventivo_id: int, user: str) -> dict[str, Any]:
        sql = """
            SELECT * FROM vendite.fn_crea_revisione_preventivo(%s, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id, user])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # ══════════════════════════════════════════════════════════
    #  SCRITTURE — Righe
    #  Nota: il ricalcolo totali e' automatico via trigger AFTER
    #  trg_preventivi_righe_z90_ricalcola_totali_ins_upd_dlt
    # ══════════════════════════════════════════════════════════

    # Scopo: Lookup lean del flag `is_composito` di un articolo. Usato dal
    #        service `gestisci_riga` per default `prezzo_unitario=0` su
    #        padre composito quando il payload non lo passa (FE lo
    #        omette per articoli compositi: il prezzo padre e' SUM(figli)
    #        calcolato dal trigger DB `_z90_ricalcola_padre` post init
    #        componenti). Senza default, l'INSERT viola il NOT NULL della
    #        colonna `prezzo_unitario` con E_DATABASE generico.
    #        Ritorna False se articolo non trovato (defensive).
    # Thin delegate cross-dominio (Fase H residue 2026-05-14): l'implementazione
    # vive in `apps.catalogo.db.catalogo_repository.CatalogoRepository.is_articolo_composito`.
    # I caller `preventivi_service` continuano a usare `self._repo.is_articolo_composito`
    # (no churn lato caller + mock test backward-compat).
    def is_articolo_composito(self, articolo_id: str) -> bool:
        from apps.catalogo.db.catalogo_repository import CatalogoRepository
        return CatalogoRepository().is_articolo_composito(articolo_id)

    # Scopo: Restituisce il factor_to_base della UoM operativa di un articolo.
    #        Usato dal service per derivare qta_operativa = quantita * factor
    #        quando il payload FE non passa esplicitamente i due campi
    #        (UX riga preventivo: l'operatore inserisce solo `quantita`).
    #        None se l'accoppiata articolo+UoM non e' presente o non attiva.
    def get_articolo_uom_factor(self, articolo_id: str, uom_id: int) -> Any:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT auo.factor_to_base
                  FROM catalogo.articoli_uom_operativa auo
                 WHERE auo.articolo_id = %s
                   AND auo.uom_id = %s
                   AND auo.attivo IS TRUE
                """,
                [articolo_id, uom_id],
            )
            row = cursor.fetchone()
            return row[0] if row else None

    # Scopo: Inserisce una nuova riga preventivo. I campi
    #        `stato_approvazione_prezzo` + `pratica_approvazione_prezzo_id`
    #        servono al workflow L3 (Sprint E listini v5 §14.6): default NULL
    #        per righe normali, valorizzati se la creazione contestualmente
    #        attiva una richiesta di approvazione out-of-policy.
    def create_riga(
        self,
        *,
        preventivo_id: int,
        articolo_id: str,
        descrizione: str | None = None,
        quantita: str | None = None,
        qta_operativa: str | None = None,
        uom_operativa_id: int | None = None,
        factor_to_base: str | None = None,
        prezzo_unitario: str | None = None,
        sconto_percentuale: str | None = None,
        iva_id: int | None = None,
        ordine: int | None = None,
        meta: dict[str, Any] | None = None,
        stato_approvazione_prezzo: str | None = None,
        pratica_approvazione_prezzo_id: int | None = None,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO vendite.preventivi_righe (
                preventivo_id, articolo_id, descrizione,
                quantita, qta_operativa, uom_operativa_id, factor_to_base,
                prezzo_unitario, sconto_percentuale, iva_id, ordine, meta,
                stato_approvazione_prezzo, pratica_approvazione_prezzo_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s
            )
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                preventivo_id, articolo_id, descrizione,
                quantita, qta_operativa, uom_operativa_id, factor_to_base,
                prezzo_unitario, sconto_percentuale, iva_id, ordine,
                json.dumps(meta or {}),
                stato_approvazione_prezzo, pratica_approvazione_prezzo_id,
            ])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna una riga preventivo esistente.
    # Campi jsonb (meta) vengono serializzati con json.dumps e cast ::jsonb.
    def update_riga(self, riga_id: int, **kwargs: Any) -> bool:
        fields: list[str] = []
        params: list[Any] = []
        for col, val in kwargs.items():
            if isinstance(val, dict):
                fields.append(f"{col} = %s::jsonb")
                params.append(json.dumps(val))
            else:
                if isinstance(val, str):
                    val = val.strip()
                fields.append(f"{col} = %s")
                params.append(val)
        if not fields:
            return False
        params.append(riga_id)
        sql = f"UPDATE vendite.preventivi_righe SET {', '.join(fields)} WHERE id = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount > 0

    # Scopo: Disattiva una riga preventivo (soft delete).
    def delete_riga(self, riga_id: int) -> bool:
        sql = "UPDATE vendite.preventivi_righe SET attivo = false WHERE id = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql, [riga_id])
            return cursor.rowcount > 0

    # ══════════════════════════════════════════════════════════
    #  SCRITTURE / LETTURE — Componenti riga (BoM CASO A)
    # ══════════════════════════════════════════════════════════
    #
    # Modello `vendite.preventivi_righe_componenti`: una riga per ogni
    # componente esposto in fattura (CASO A) della BoM di un articolo
    # composito padre. Vedi `refactor-componenti.md` + brief DB
    # `brief-db-preventivi-righe-componenti-override.md`.
    #
    # Trigger DB ricalcolano `prezzo_unitario` del padre come SUM dei
    # componenti × coeff_qta_snapshot — il backend NON deve toccarlo
    # esplicitamente.

    # Scopo: Converte emittente_fiscale_id (PK `anagrafiche.emittenti_fiscali.id`)
    # nel suo `soggetto_ruolo_id` corrispondente. Helper usato dal flusso
    # init componenti CASO A quando il preventivo dichiara un emittente
    # esplicito che NON coincide con quello dell'operatore (caso admin
    # globale o override). Restituisce None se l'id non esiste.
    # Vedi memoria `feedback_emittente_pk_vs_soggetto_ruolo`: la tabella
    # `emittenti_fiscali` ha sia `id` (PK) che `soggetto_ruolo_id` (FK),
    # serve la conversione PK -> sr_id per le fn pricing che attendono sr_id.
    # Thin delegate cross-dominio (Fase H residue 2026-05-14): implementazione
    # in `apps.anagrafiche.db.emittenti_fiscali_repository.EmittentiFiscaliRepository.get_sr_id_by_fiscale_id`.
    def get_emittente_sr_id_by_fiscale_id(self, fiscale_id: int) -> int | None:
        from apps.anagrafiche.db.emittenti_fiscali_repository import (
            EmittentiFiscaliRepository,
        )
        return EmittentiFiscaliRepository().get_sr_id_by_fiscale_id(fiscale_id)

    # Scopo: Popola i componenti BoM per una riga padre composita invocando
    # la fn DB `vendite.fn_preventivo_riga_componenti_init` (modello
    # unificato 2026-05-13). Idempotente: ritorna 0 se gia' presenti
    # componenti su quella riga o se l'articolo non e' composito.
    # Se il padre e' composito ma BoM scaduta/non configurata alla data:
    # la fn DB solleva `E_DOC_COMPOSITO_BOM_VUOTA`.
    #
    # `componenti_overrides`: mappa opzionale {componente_id: prezzo} per
    # i componenti su cui l'operatore ha inserito un prezzo manuale.
    # Per ogni componente la fn DB:
    #   - applica l'override se presente (origine_prezzo='MANUALE')
    #   - altrimenti delega al pricing resolver bundle-aware (STADIO 0
    #     listino bundle del padre, fallback STADIO 1 standalone); se
    #     manca listino solleva `E_DOC_COMPONENTE_LISTINO_MANCANTE`
    # Guard prezzo=0 solo per componenti `obbligatorio=TRUE` (modello
    # unificato: opzionali ammettono prezzo 0/negativo).
    # Il caller (service) deve gating L1: passare overrides non vuoti
    # solo se l'utente ha l'azione `prezzo_override_manuale`.
    #
    # `componenti_attivazioni`: mappa opzionale {componente_id: bool} per
    # sovrascrivere il default DB di `attivo` su componenti opzionali.
    # Default DB (modello unificato): obbligatori = TRUE, opzionali =
    # FALSE. L'operatore puo' attivare opzionali via questa mappa.
    # Implementato come UPDATE post-init (la fn DB non accetta il
    # parametro): il trigger guard DB
    # `script.trgfn_componenti_guard_obbligatorio` impedisce di
    # disattivare obbligatori (raise `E_DOC_COMPONENTE_OBBLIGATORIO`).
    #
    # ATTENZIONE re-init implicito: se la fn DB fa no-op (componenti gia'
    # presenti, ritorna 0) la mappa attivazioni viene comunque applicata
    # come UPDATE sui figli esistenti. In Fase B il caller reale e'
    # `gestisci_riga` (CREATE riga, mai no-op): comportamento ininfluente.
    # In Fase D (EDIT panel) servira' un metodo dedicato
    # `apply_attivazioni(riga_id, attivazioni)` per separare init e
    # modifica successive. Per ora non splittiamo perche' YAGNI.
    def init_componenti_riga(
        self,
        *,
        riga_id: int,
        emittente_soggetto_ruolo_id: int,
        data_riferimento: date,
        componenti_overrides: dict[str, Any] | None = None,
        componenti_attivazioni: dict[str, bool] | None = None,
    ) -> int:
        # Cast esplicito a jsonb per disambiguare l'overload della fn DB:
        # None -> NULL, dict -> json.dumps. Il caller (service) e' tenuto
        # a validare la forma dei valori (numero non vuoto) prima di passarli
        # qui — vedi `_normalize_componenti_overrides` in preventivi_service.
        overrides_json: str | None
        if componenti_overrides is None:
            overrides_json = None
        else:
            overrides_json = json.dumps(
                {str(k): str(v) for k, v in componenti_overrides.items()},
            )
        sql = (
            "SELECT vendite.fn_preventivo_riga_componenti_init("
            "%s, %s, %s, %s::jsonb)"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                riga_id, emittente_soggetto_ruolo_id, data_riferimento,
                overrides_json,
            ])
            row = cursor.fetchone()
            inserted = int(row[0]) if row else 0

            # Applica attivazioni esplicite post-init. UPDATE selettivo per
            # componente: il trigger DB guard scatta se il payload tenta di
            # disattivare un obbligatorio. Niente UPDATE se il valore
            # richiesto coincide con il default gia' applicato dalla fn
            # `_init` (obbligatorio -> attivo=TRUE, opzionale -> attivo=FALSE):
            # WHERE clause con `attivo IS DISTINCT FROM` impedisce UPDATE
            # spurio e relativi trigger.
            if componenti_attivazioni:
                update_sql = (
                    "UPDATE vendite.preventivi_righe_componenti "
                    "SET attivo = %s "
                    "WHERE riga_preventivo_id = %s "
                    "  AND componente_id = %s "
                    "  AND attivo IS DISTINCT FROM %s"
                )
                for componente_id, attivo in componenti_attivazioni.items():
                    cursor.execute(update_sql, [
                        bool(attivo), riga_id, str(componente_id),
                        bool(attivo),
                    ])

            return inserted

    # Scopo: Preview componenti BoM per drawer riga (modello unificato).
    # Read-only, no side-effect. Per ogni componente attivo e valido alla
    # data ritorna prezzo_suggerito (NULL se resolver fail per quel
    # componente) + resolver_error_reason. Consumato dal FE per
    # pre-popolare la tabella componenti del drawer riga PRIMA del save.
    # Modello unificato 2026-05-13: tutti i componenti attivi sono
    # restituiti (no filtro esposto_in_fattura), proiezione include
    # `obbligatorio` (gate prezzo zero) e `esposto_in_fattura` (flag
    # presentazione fattura).
    def preview_componenti_riga(
        self,
        *,
        articolo_id: str,
        uom_id: int | None,
        quantita_padre,
        data_riferimento: date,
        ba_id: int | None,
        utility_id: int,
        emittente_soggetto_ruolo_id: int,
        classe_utenza_id: int | None = None,
    ) -> list[dict[str, Any]]:
        # Proiezione allineata alla fn DB modello unificato (14 colonne):
        # `iva_codice` NON e' esposto dalla fn (solo `iva_id`); l'aliquota
        # del componente coincide con quella del padre (vincolo IVA BoM).
        sql = """
            SELECT articolo_componente_id,
                   componente_id,
                   componente_codice,
                   componente_descrizione,
                   coeff_qta_snapshot,
                   quantita_componente,
                   uom_id,
                   uom_codice,
                   iva_id,
                   prezzo_suggerito,
                   origine_prezzo,
                   resolver_error_reason,
                   obbligatorio,
                   esposto_in_fattura
              FROM vendite.fn_preventivo_riga_componenti_preview(
                  %s, %s, %s, %s, %s, %s, %s, %s
              )
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                articolo_id, uom_id, quantita_padre, data_riferimento,
                ba_id, utility_id, emittente_soggetto_ruolo_id,
                classe_utenza_id,
            ])
            return rows_to_list(cursor)

    # CRUD componenti (list/get/update/delete/purge) ereditato da
    # `ComponentiRepositoryMixin`. Vedi `_componenti_repo_mixin.py`.

    # ══════════════════════════════════════════════════════════
    #  SCRITTURE — Indirizzi
    # ══════════════════════════════════════════════════════════

    # Scopo: Upsert indirizzo preventivo (uno per tipo).
    def upsert_indirizzo(
        self,
        *,
        preventivo_id: int,
        tipo_indirizzo_id: int,
        snapshot: dict[str, Any],
        origine_indirizzo_id: int | None = None,
        origine_soggetto_ruolo_id: int | None = None,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO vendite.preventivi_indirizzi (
                preventivo_id, tipo_indirizzo_id, snapshot,
                origine_indirizzo_id, origine_soggetto_ruolo_id
            ) VALUES (%s, %s, %s::jsonb, %s, %s)
            ON CONFLICT ON CONSTRAINT uq_preventivi_indirizzi_uno_per_tipo_
            DO UPDATE SET
                snapshot = EXCLUDED.snapshot,
                origine_indirizzo_id = EXCLUDED.origine_indirizzo_id,
                origine_soggetto_ruolo_id = EXCLUDED.origine_soggetto_ruolo_id
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                preventivo_id, tipo_indirizzo_id, json.dumps(snapshot),
                origine_indirizzo_id, origine_soggetto_ruolo_id,
            ])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # ══════════════════════════════════════════════════════════
    #  INTEGRAZIONE — Commesse / Fatturazione
    # ══════════════════════════════════════════════════════════

    # Scopo: Discovery righe preventivo eleggibili per push in commessa.
    # TODO: l'orchestrazione completa (get_or_create_commessa + upsert righe)
    # sara' aggiunta quando il CommessePushOrchestrator verra' esteso per
    # supportare il push singolo preventivo (oggi gestisce solo push batch).
    def count_righe_pushable(self, preventivo_id: int) -> int:
        sql = """
            SELECT count(*) AS cnt
            FROM vendite.fn_list_preventivi_da_pushare()
            WHERE preventivo_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            row = cursor.fetchone()
            return row[0] if row else 0

    # Scopo: Stato fatturazione aggregato del preventivo (per badge UI).
    # Usa la vista DB che fa il join via segment_key e filtra per sorgente PREVENTIVO.
    def stato_fatturazione(self, preventivo_id: int) -> PreventivoStatoFatturazioneRow | None:
        sql = """
            SELECT *
            FROM vendite.vw_preventivi_stato_fatturazione
            WHERE preventivo_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return row_to_dict(cursor)

    # ══════════════════════════════════════════════════════════
    #  INTEGRAZIONE — Pratiche
    # ══════════════════════════════════════════════════════════

    # Scopo: Restituisce il contesto minimo richiesto dal motore documentale
    #        (Tranche K) per generare un documento da preventivo: `id`,
    #        `uid` (UUID stringa che finisce su `documenti_generati.sorgente_uid`),
    #        `emittente_fiscale_id` (colonna nativa NOT NULL del DDL preventivi).
    #        Niente JOIN su anagrafiche/billing_account: l'emittente_fiscale_id
    #        e' gia' su `vendite.preventivi.emittente_fiscale_id` (multi-face
    #        auth, Tranche A). Ritorna None se id inesistente.
    def get_for_documento_generation(
        self, preventivo_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT
                id,
                uid::text AS uid,
                emittente_fiscale_id
              FROM vendite.preventivi
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(preventivo_id)])
            return row_to_dict(cursor)

    # Scopo: Risolve contesto anagrafico dal preventivo per creazione pratica.
    # Restituisce emittente_fiscale_id (PK numerica anagrafiche.emittenti_fiscali.id),
    # soggetto_id e soggetto_ruolo_id ricavati dal billing_account del preventivo.
    # L'emittente fiscale viene risolto via anagrafiche.fn_get_emittente_fiscale_pk
    # (mapping specifico BA -> fallback gestore globale, errore esplicito se manca).
    # Scopo: Risolve il contesto pricing applicato al preventivo: contratto
    # attivo (se presente) o listino categoria fallback. Mostrato in header
    # del drawer preventivo per audit visivo del path resolver. Non chiama
    # il resolver effettivo (lettura informativa); l'effettivo prezzo riga
    # passa per `fn_resolve_prezzo_listino_v2` con la stessa logica.
    #
    # Ritorna dict con campi:
    #   - fonte: 'CONTRATTO' | 'CATEGORIA' | 'NONE'
    #   - contratto_id, contratto_numero (NULL se fonte != CONTRATTO)
    #   - listino_id, listino_codice, listino_descrizione (NULL se fonte == NONE)
    #   - categoria_cliente_id, categoria_cliente_codice, categoria_cliente_descrizione
    #     (solo se fonte == CATEGORIA)
    def resolve_contesto_pricing(self, preventivo_id: int) -> dict[str, Any] | None:
        sql = """
            WITH preventivo AS (
                SELECT
                    p.id,
                    p.billing_account_id,
                    p.utility_id,
                    p.data::date AS data_riferimento,
                    ba.categoria_cliente_id
                  FROM vendite.preventivi p
                  JOIN anagrafiche.billing_account ba ON ba.id = p.billing_account_id
                 WHERE p.id = %s
            ),
            -- Contratto attivo applicabile al preventivo (stessa logica resolver:
            -- billing_account + utility + data, stato ATTIVO, piu' recente).
            contratto_attivo AS (
                SELECT c.id, c.numero, c.listino_id
                  FROM vendite.contratti c
                  JOIN config.stati_doc_contratti s
                    ON s.id = c.stato_doc_contratto_id
                  JOIN preventivo prev ON TRUE
                 WHERE c.billing_account_id = prev.billing_account_id
                   AND c.utility_id         = prev.utility_id
                   AND c.validita          @> prev.data_riferimento
                   AND s.codice_interno     = 'ATTIVO'
                 ORDER BY c.id DESC
                 LIMIT 1
            ),
            -- Listino categoria fallback (solo se non c'e' contratto).
            -- Match su classe NULL: la versione UI non passa classe utenza,
            -- privilegiamo il default `classe_utenza_id IS NULL`.
            listino_categoria AS (
                SELECT ccl.id AS categoria_cliente_listino_id,
                       ccl.listino_id,
                       prev.categoria_cliente_id
                  FROM anagrafiche.categorie_clienti_listini ccl
                  JOIN preventivo prev ON TRUE
                 WHERE NOT EXISTS (SELECT 1 FROM contratto_attivo)
                   AND ccl.categoria_cliente_id = prev.categoria_cliente_id
                   AND ccl.utility_id           = prev.utility_id
                   AND ccl.classe_utenza_id IS NULL
                   AND ccl.validita            @> prev.data_riferimento
                   AND ccl.attivo               = TRUE
                 LIMIT 1
            )
            SELECT
                prev.id AS preventivo_id,
                prev.data_riferimento,
                CASE
                    WHEN ca.id IS NOT NULL THEN 'CONTRATTO'
                    WHEN lc.listino_id IS NOT NULL THEN 'CATEGORIA'
                    ELSE 'NONE'
                END AS fonte,
                ca.id     AS contratto_id,
                ca.numero AS contratto_numero,
                COALESCE(ca.listino_id, lc.listino_id) AS listino_id,
                l.codice      AS listino_codice,
                l.descrizione AS listino_descrizione,
                cc.id         AS categoria_cliente_id,
                cc.codice     AS categoria_cliente_codice,
                cc.descrizione AS categoria_cliente_descrizione
              FROM preventivo prev
              LEFT JOIN contratto_attivo ca ON TRUE
              LEFT JOIN listino_categoria lc ON TRUE
              LEFT JOIN vendite.listini l
                ON l.id = COALESCE(ca.listino_id, lc.listino_id)
              LEFT JOIN anagrafiche.categorie_clienti cc
                ON cc.id = lc.categoria_cliente_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return row_to_dict(cursor)

    def resolve_contesto_pratica(self, preventivo_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT
                anagrafiche.fn_get_emittente_fiscale_pk(p.billing_account_id)
                    AS emittente_fiscale_id,
                sr.soggetto_id::text AS soggetto_id,
                ba.soggetto_ruolo_id
            FROM vendite.preventivi p
            JOIN anagrafiche.billing_account ba ON ba.id = p.billing_account_id
            JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
            WHERE p.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return row_to_dict(cursor)

    # Scopo: Inserisce link preventivo → pratica in pratiche_sorgenti.
    def link_pratica(
        self,
        *,
        pratica_id: int,
        sorgente_tipo_id: int,
        sorgente_uid: str,
        ruolo_link: str = "ROOT",
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO pratiche.pratiche_sorgenti (
                pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link
            ) VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Restituisce pratiche collegate al preventivo via vista DB.
    # La vista filtra gia' per sorgente_tipo codice = 'PREVENTIVO'.
    def list_pratiche(self, preventivo_id: int) -> list[PreventivoPraticaRow]:
        sql = """
            SELECT *
            FROM vendite.vw_preventivi_pratiche
            WHERE preventivo_id = %s
            ORDER BY data_apertura DESC NULLS LAST
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return rows_to_list(cursor)

    # ══════════════════════════════════════════════════════════
    #  LOOKUP — Risoluzione config per creazione
    # ══════════════════════════════════════════════════════════

    # Scopo: Restituisce l'id dello stato DRAFT (bozza) da config.stati_doc_preventivi.
    # Usa codice_interno (immutabile) per lookup applicativi.
    def get_stato_bozza_id(self) -> int | None:
        sql = """
            SELECT id FROM config.stati_doc_preventivi
            WHERE codice_interno = 'DRAFT' AND attivo = true
            LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            row = cursor.fetchone()
            return row[0] if row else None

    # Scopo: Restituisce l'id del tipo sorgente PREVENTIVO da config.sorgenti.
    def get_sorgente_tipo_preventivo_id(self) -> int | None:
        sql = """
            SELECT id FROM config.sorgenti
            WHERE codice_interno = 'PREVENTIVO' AND attivo = true
            LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            row = cursor.fetchone()
            return row[0] if row else None
