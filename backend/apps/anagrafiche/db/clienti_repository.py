# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per gestione clienti.
#        CRUD clienti, creazione istanza/BA, lista paginata.
#        Accesso DB-first via cursor e funzioni PostgreSQL.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import connection

from apps.anagrafiche.db._helpers import get_or_create_soggetto_ruolo
from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
    sql_order_clause,
    extract_paginated,
    row_to_dict,
    rows_to_list,
)


# Whitelist colonne ammesse per ORDER BY: chiave = `campo_sorgente` del catalogo
# 'anagrafiche.clienti' (e' quello che `<ListaConfigurabile>` invia come
# sortField), valore = la colonna della vista `anagrafiche.vw_clienti_lista`,
# qualificata con il suo alias `v`.
#
# L'identificativo fiscale a video e' SEMPRE `id_fiscale_univoco_cf_piva` (la
# colonna GENERATED che unifica CF e P.IVA). `codice_fiscale` e `partita_iva`
# nudi non sono esposti da nessuna colonna della lista: fuori dalla whitelist.
_CLIENTI_ORDER_COLS: dict[str, str] = {
    c: f"v.{c}"
    for c in (
        "ragione_sociale_completa", "id_fiscale_univoco_cf_piva",
        "soggetto_codice", "ba_codice", "utility_descrizione", "stato_descrizione",
        "data_attivazione", "data_sospensione", "data_riattivazione", "data_chiusura",
    )
}

# Cosa si PUO' cercare; cosa si cerca lo dice il catalogo (`add_ricerca_full_condition`).
# ⭐ Tupla con alias `v`: la lista legge la vista che il catalogo le dichiara
#    (`vista_sql = vw_clienti_lista`), quindi il `campo_sorgente` e' un nome di
#    colonna vero anche nel `WHERE`.
# ⭐ L'id fiscale univoco e non CF e P.IVA separati (Tid, 2026-09-23): come
#    fornitori, soggetti ed emittenti. Fino al 2026-09-24 la ricerca era scritta
#    a mano qui e cercava `codice_fiscale` e `partita_iva` nudi, che nessuna
#    colonna della lista mostra. Nessun termine si perde: la colonna GENERATED
#    porta `cf || ' ' || piva` quando i due differiscono, altrimenti quello che c'e'.
_RICERCA_CLIENTI = RicercaFull(
    "anagrafiche.clienti",
    ("ragione_sociale_completa", "ba_codice", "soggetto_codice", "id_fiscale_univoco_cf_piva"),
)


class ClientiRepository:
    """Accesso DB per clienti, istanze utilities e billing account."""

    # =================================================================
    # Helpers condivisi (riusabili da service per singoli step)
    # =================================================================

    # ⛔ `get_default_iva_id` RIMOSSA (2026-08-29, I0/D7-bis del brief
    #    brief-be-fe-iva-risolutore-e-regime-cliente): `anagrafiche.clienti.iva_id`
    #    non esiste piu'. Leggeva il parametro DEFAULT_IVA_ID per riempire una
    #    colonna NOT NULL senza default DB — cioe' faceva nascere ogni cliente con
    #    un codice IVA CHE NESSUNO AVEVA SCELTO, indistinguibile da uno scelto
    #    apposta. Il parametro di sistema resta a seed: qui muore il lettore.
    #    L'influenza del soggetto sull'IVA passa da un titolo documentato (D10),
    #    mai da un default appeso all'anagrafica.

    # Scopo: Verifica se l'utility ammette creazione manuale (richiede_pdp = false).
    def get_utility(self, utility_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT id, descrizione, codice, richiede_pdp
              FROM config.utilities
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [utility_id])
            return row_to_dict(cursor)

    # Scopo: Ottiene o crea il ruolo CLIENTE per un soggetto.
    #        Delega alla funzione DB script.fn_get_or_create_soggetto_ruolo.
    def get_or_create_ruolo_cliente(self, soggetto_id: str) -> int:
        return get_or_create_soggetto_ruolo(soggetto_id, 'CL')

    # Scopo: Crea istanza utility fittizia (senza PDP).
    #        Nota: istanze_utilities non ha utility_id; l'utility viene propagata
    #        dal billing_account al cliente tramite trigger trgfn_clienti_sync_utility_from_ba.
    def create_istanza_fittizia(
        self, *, soggetto_id: str,
        indirizzo_dettaglio_id: int | None = None,
    ) -> int:
        sql = """
            INSERT INTO anagrafiche.istanze_utilities
                   (soggetto_id, fittizia, indirizzo_dettaglio_id)
            VALUES (%s, true, %s)
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [soggetto_id, indirizzo_dettaglio_id])
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    # Scopo: Wrapper script.fn_check_user_can_create_ba. Vedi WIP refactor
    #        operatore-emittenti Q6 (la motivazione di dominio sta nel service).
    def check_user_can_create_ba(self, auth_user_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_check_user_can_create_ba(%s)",
                [auth_user_id],
            )
            row = cursor.fetchone()
        return bool(row[0]) if row else False

    # Scopo: Crea billing account per un'istanza e un ruolo soggetto.
    #        Il codice viene generato dal trigger trgfn_billing_account_gen_codice.
    #        Il default di fatturazione_ordini e' gestito dal DB (CONFERMATO).
    #        L'auto-link BA -> emittente fiscale viene gestito dal trigger
    #        z90 trgfn_billing_account_link_ef leggendo la GUC
    #        app.current_user_id (settata da JwtAuditMiddleware).
    def create_billing_account(
        self, *, istanza_utility_id: int, soggetto_ruolo_id: int,
        utility_id: int, fatturazione_ordini: str | None = None,
        parent_account_id: int | None = None,
        categoria_cliente_id: int,
    ) -> int:
        # categoria_cliente_id e' obbligatorio: il service deve averlo gia'
        # risolto (dal payload `ba_categoria_cliente_id`). La colonna DB e'
        # NOT NULL post-backfill F1-DB-03; la FK e' validata dal trigger
        # `fk_billing_account_categoria_cliente`.
        cols = [
            "istanza_utility_id", "soggetto_ruolo_id", "utility_id",
            "parent_account_id", "categoria_cliente_id",
        ]
        vals: list[Any] = [
            istanza_utility_id, soggetto_ruolo_id, utility_id,
            parent_account_id, categoria_cliente_id,
        ]
        if fatturazione_ordini is not None:
            cols.append("fatturazione_ordini")
            vals.append(fatturazione_ordini)
        placeholders = ", ".join(["%s"] * len(cols))
        sql = f"""
            INSERT INTO anagrafiche.billing_account ({", ".join(cols)})
            VALUES ({placeholders})
            RETURNING id
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    # Scopo: Crea record cliente con stato ATTIVO.
    #        I trigger DB gestiscono: sync_utility, set_periodo, sync_pdp, guard.
    #        Le colonne opzionali sono incluse solo se valorizzate; il DB ha un
    #        default o un trigger per i campi NOT NULL rimanenti.
    def create_cliente(self, **kwargs) -> int:
        # Colonne fisse (sempre presenti)
        cols = ["istanza_utility_id", "billing_account_id", "soggetto_ruolo_id",
                "stato_cliente_id", "data_attivazione"]
        vals: list = [kwargs["istanza_utility_id"], kwargs["billing_account_id"],
                      kwargs["soggetto_ruolo_id"]]
        # Espressioni speciali (non parametrizzate)
        special = {
            "stato_cliente_id": "(SELECT id FROM config.stati_cliente WHERE codice_interno = 'AT')",
            "data_attivazione": "CURRENT_DATE",
        }
        # Colonne opzionali: incluse solo se valorizzate (non None)
        # ⛔ Sei chiavi tolte il 2026-08-29 (I0/I8 del brief
        #    brief-be-fe-iva-risolutore-e-regime-cliente): `iva_id`,
        #    `cliente_pa`, `split_payment`, `codice_cig`, `codice_cup`,
        #    `codice_commessa` non sono piu' colonne di `anagrafiche.clienti`.
        #    Le loro sedi: i due flag su `anagrafiche.soggetti` (D8 — la PA e' una
        #    proprieta' dell'ENTE, non della fornitura), i tre codici su
        #    `vendite.contratti` (D9 — nominano un contratto, non un cliente),
        #    l'IVA in nessuna colonna di default (D7-bis).
        _OPTIONAL = [
            "termine_pagamento_id", "modalita_pagamento_id",
            "servizio_da_fatturare",
            "garanzia_tipo", "garanzia_importo",
        ]
        for col in _OPTIONAL:
            val = kwargs.get(col)
            if val is not None:
                cols.append(col)
                vals.append(val)
        placeholders = [special.get(c, "%s") for c in cols]
        sql = f"""
            INSERT INTO anagrafiche.clienti ({", ".join(cols)})
            VALUES ({", ".join(placeholders)})
            RETURNING id
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, vals)
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    # =================================================================
    # Validazione entita' esistenti
    # =================================================================

    # Scopo: Valida che un'istanza esista e appartenga al soggetto.
    def get_istanza(self, istanza_utility_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT id, soggetto_id, utility_id, fittizia, indirizzo_dettaglio_id
              FROM anagrafiche.istanze_utilities
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [istanza_utility_id])
            return row_to_dict(cursor)

    # Scopo: Valida che un billing account esista e appartenga all'istanza.
    def get_billing_account(self, billing_account_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT id, istanza_utility_id, soggetto_ruolo_id, utility_id, codice
              FROM anagrafiche.billing_account
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [billing_account_id])
            return row_to_dict(cursor)

    # =================================================================
    # Lista e dettaglio
    # =================================================================

    # Scopo: Lista paginata clienti con search e filtri.
    #        Join: clienti + istanza + BA + soggetto + utility + stato.
    #        Scope emittente fiscale: filtra i clienti i cui BA appartengono
    #        agli emittenti autorizzati per l'utente chiamante (refactor
    #        operatore-emittenti, follow-up BE-3.5). `emittente_ids=None`
    #        bypassa il filtro (superuser, admin globale, "0 emittenti");
    #        lista vuota ⇒ nessun risultato.
    # ⛔ Lo scope DELEGA a `script.fn_check_ba_visible_for_emittenti`, come
    #    gia' `billing_account_repository` e `istanze_utility_repository`.
    #    Fino al 2026-09-13 la regola stava qui INLINE («mapping specifico,
    #    altrimenti default se il BA non ha mapping», per lasciare al planner
    #    il semi-join) e il commento la dichiarava «identica alla fn canonica»:
    #    dal changeSet `20260913-01` (D13) la regola del DB ha TRE livelli — in
    #    sessione un BA senza legame e' dell'operatore che sta agendo, non del
    #    default — e la copia inline sarebbe rimasta alla vecchia, in silenzio.
    #    Una regola, un posto: brief-db-ba-riserva-emittente-operatore-d13 §6.2.
    def list_clienti(
        self, *, search: str | None = None,
        utility_id: int | None = None,
        stato_cliente_id: int | None = None,
        emittente_ids: list[int] | None = None,
        limit: int = 25, offset: int = 0,
        order_by: str = "ragione_sociale_completa", order_dir: str = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_CLIENTI_ORDER_COLS,
            default=_CLIENTI_ORDER_COLS["ragione_sociale_completa"],
            tiebreak="v.id",
        )
        conditions: list[str] = [
            "(%s::integer IS NULL OR v.utility_id = %s)",
            "(%s::integer IS NULL OR v.stato_cliente_id = %s)",
            "(%s::bigint[] IS NULL"
            " OR script.fn_check_ba_visible_for_emittenti(v.billing_account_id, %s::bigint[]))",
        ]
        params: list[Any] = [
            utility_id, utility_id,
            stato_cliente_id, stato_cliente_id,
            emittente_ids, emittente_ids,
        ]
        # ⚠️ Sotto `RICERCA_MIN_CARATTERI` (3) il termine non filtra: fino al
        #    2026-09-24 la ricerca scritta a mano filtrava da un carattere (e
        #    senza `escape_ilike`: un `%` o un `_` facevano da jolly).
        add_ricerca_full_condition(conditions, params, search, _RICERCA_CLIENTI, alias="v")
        # ⭐ Dal 2026-09-24 la lista legge la VISTA che il catalogo le dichiara
        #    (`vista_sql = vw_clienti_lista`, `security_invoker`): fino a quel
        #    giorno questa query ne era una copia — stessi cinque join, stesse
        #    colonne — e il catalogo nominava una vista che la lista non leggeva
        #    (brief-be-ricerca-full-liste-residue §5.2). Una sola sede della
        #    forma della riga: una colonna nuova della lista si aggiunge alla vista.
        sql = f"""
            SELECT v.id,
                   v.billing_account_id,
                   v.istanza_utility_id,
                   v.soggetto_ruolo_id,
                   v.soggetto_id,
                   v.soggetto_codice,
                   v.ba_codice,
                   v.ragione_sociale_completa,
                   v.codice_fiscale,
                   v.partita_iva,
                   v.id_fiscale_univoco_cf_piva,
                   v.utility_descrizione,
                   v.utility_id,
                   v.stato_descrizione,
                   v.stato_codice_interno,
                   v.stato_codice,
                   v.data_attivazione,
                   v.data_chiusura,
                   v.data_sospensione,
                   v.data_riattivazione,
                   COUNT(*) OVER () AS total_count
              FROM anagrafiche.vw_clienti_lista v
             WHERE {" AND ".join(conditions)}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """  # noqa: S608
        params.extend([limit, offset])
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return extract_paginated(cursor)

    # Scopo: Lista utility ammesse per creazione manuale (richiede_pdp = false, attivo).
    def list_utilities_manuali(self) -> list[dict[str, Any]]:
        sql = """
            SELECT id, codice, descrizione
              FROM config.utilities
             WHERE richiede_pdp = false
             ORDER BY descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return rows_to_list(cursor)

    # Scopo: Risolve la descrizione di un'utility per id (DEF-1, header
    #        filtri leggibili nell'export). Niente cache: lookup
    #        opportunistico (1-2 chiamate per richiesta export).
    def get_utility_descrizione(self, utility_id: int) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT descrizione FROM config.utilities WHERE id = %s",
                [utility_id],
            )
            row = cursor.fetchone()
            return row[0] if row else None

    # Scopo: Risolve la descrizione di uno stato cliente per id (DEF-1).
    def get_stato_cliente_descrizione(self, stato_id: int) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT descrizione_breve "
                "  FROM config.stati_cliente WHERE id = %s",
                [stato_id],
            )
            row = cursor.fetchone()
            return row[0] if row else None

    # Scopo: Dettaglio completo di un cliente con dati istanza, BA, soggetto e FK descrizioni.
    def get_cliente(self, cliente_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT cl.id,
                   cl.istanza_utility_id,
                   cl.billing_account_id,
                   cl.soggetto_ruolo_id,
                   cl.stato_cliente_id,
                   cl.utility_id,
                   cl.pdp_id,
                   cl.data_attivazione,
                   cl.data_sospensione,
                   cl.data_riattivazione,
                   cl.data_chiusura,
                   -- Stato evento corrente data-driven (Fase 4 refactor):
                   -- la fn DB risolve sosp vs riatt confrontando le date.
                   -- Pareggio = RIATTIVAZIONE. Niente logica nel frontend.
                   evt.data_evento_stato,
                   evt.tipo_evento_stato,
                   -- Pagamento — unico meccanismo: termine di catalogo +
                   -- modalita' (D-I). La coppia legacy tipo_gg_scadenza_ft /
                   -- nr_giorni_scadenza non si legge piu': le colonne cadono
                   -- con la 3a.5 del piano DB satelliti.
                   cl.termine_pagamento_id,
                   cl.modalita_pagamento_id,
                   -- ⛔ iva_id / cliente_pa / split_payment / codice_cig /
                   --    codice_cup / codice_commessa: colonne rimosse dal DB il
                   --    2026-08-29 (I0/I8). I due flag si leggono ora da
                   --    `anagrafiche.soggetti`, i tre codici da
                   --    `vendite.contratti`. Il dettaglio cliente NON ne tiene
                   --    una copia in sola lettura (Q2): un campo che ripete un
                   --    dato che vive altrove e' la premessa dell'errore che
                   --    questo cantiere sta chiudendo.
                   cl.servizio_da_fatturare,
                   -- Garanzia
                   cl.garanzia_tipo,
                   cl.garanzia_importo,
                   -- Soggetto
                   s.id AS soggetto_id,
                   s.ragione_sociale_completa,
                   s.codice_fiscale,
                   s.partita_iva,
                   s.tipo_soggetto_dettaglio_id,
                   -- Billing account
                   ba.codice AS ba_codice,
                   ba.fatturazione_ordini AS ba_fatturazione_ordini,
                   ba.parent_account_id AS ba_parent_account_id,
                   ba.valido_dal AS ba_valido_dal,
                   ba.valido_al AS ba_valido_al,
                   -- Categoria cliente (pricing v5 STADIO 2)
                   ba.categoria_cliente_id AS ba_categoria_cliente_id,
                   cc.codice AS ba_categoria_codice,
                   cc.descrizione AS ba_categoria_descrizione,
                   -- Istanza
                   iu.fittizia AS istanza_fittizia,
                   iu.indirizzo_dettaglio_id AS istanza_indirizzo_dettaglio_id,
                   iu.codice AS istanza_codice,
                   -- FK descrizioni
                   u.descrizione AS utility_descrizione,
                   sc.codice_interno AS stato_codice_interno,
                   sc.codice AS stato_codice,
                   sc.descrizione_breve AS stato_descrizione,
                   mp.descrizione AS modalita_pagamento_descrizione,
                   tp.descrizione AS termine_pagamento_descrizione
              FROM anagrafiche.clienti cl
              JOIN anagrafiche.istanze_utilities iu ON iu.id = cl.istanza_utility_id
              JOIN anagrafiche.soggetti s ON s.id = iu.soggetto_id
              JOIN anagrafiche.billing_account ba ON ba.id = cl.billing_account_id
              JOIN config.utilities u ON u.id = cl.utility_id
              JOIN config.stati_cliente sc ON sc.id = cl.stato_cliente_id
              LEFT JOIN config.modalita_pagamento mp ON mp.id = cl.modalita_pagamento_id
              LEFT JOIN config.termini_pagamento tp ON tp.id = cl.termine_pagamento_id
              LEFT JOIN anagrafiche.categorie_clienti cc ON cc.id = ba.categoria_cliente_id
              -- LATERAL: chiama fn_get_evento_stato_corrente_cliente per la riga corrente
              LEFT JOIN LATERAL anagrafiche.fn_get_evento_stato_corrente_cliente(cl.id)
                       AS evt(data_evento_stato, tipo_evento_stato) ON TRUE
             WHERE cl.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [cliente_id])
            return row_to_dict(cursor)

    # Campi editabili sul cliente (pagamento, garanzia, servizio).
    # ATTENZIONE: questo set DEVE restare allineato alla whitelist interna della
    # funzione madre anagrafiche.fn_update_cliente (autorita' finale: ignora le
    # chiavi non whitelisted). Qui e' difesa-in-profondita' + igiene payload (non
    # spedire chiavi ignote nel jsonb), coerente coi repo fratelli
    # (fornitori/emittenti). Aggiungere un campo editabile => aggiornare ENTRAMBI.
    # ⛔ Le sei chiavi di I0/I8 sono uscite il 2026-08-29 QUI e nella fn madre
    #    (changeSet 20260829-20). L'allineamento e' il punto: se restassero solo
    #    qui, la PATCH le accetterebbe e la fn le butterebbe via — l'operatore
    #    salverebbe senza vedere errori e il valore non andrebbe da nessuna parte.
    _UPDATE_ALLOWED = {
        "modalita_pagamento_id", "termine_pagamento_id",
        "servizio_da_fatturare",
        "garanzia_tipo", "garanzia_importo",
    }

    # Scopo: Aggiornamento atomico del cliente via funzione madre DB.
    #        Obiettivo: fondere in UNA sola statement SQL
    #        (anagrafiche.fn_update_cliente) la scrittura della categoria
    #        cliente sul billing_account e i campi editabili del cliente.
    #        Perimetro: o vanno a buon fine entrambe o rollback totale — niente
    #        piu' stato parziale con la categoria BA committata e l'UPDATE
    #        cliente fallito (fix analisi-fix-transazioni Classe A, finding #1;
    #        prima erano due UPDATE separati in autocommit).
    #        Risultato: dict {categoria_aggiornata, campi_aggiornati}; il service
    #        decide se sollevare "nessun campo modificato" quando entrambi False.
    #        La fn e' SECURITY INVOKER: RLS e scope emittente su billing_account
    #        restano valutati come dal Python (vincolo invariante §2-bis).
    #
    #        Input:
    #          - ba_categoria_cliente_id: categoria da scrivere sul BA del
    #            cliente; None = categoria non toccata (colonna NOT NULL, mai a NULL).
    #          - cliente_fields: delta dei campi editabili. Solo le chiavi
    #            whitelisted (_UPDATE_ALLOWED) sono passate alla fn; le stringhe
    #            vuote/whitespace sono normalizzate a NULL (la fn DB non
    #            normalizza: la disciplina null-vs-empty resta lato BE).
    def update_cliente_atomico(
        self, cliente_id: int, *,
        ba_categoria_cliente_id: int | None,
        cliente_fields: dict[str, Any],
    ) -> dict[str, bool]:
        # Whitelist + normalizzazione stringa-vuota -> None prima di serializzare
        # il delta in jsonb per la fn madre.
        # Empty -> NULL applicata a TUTTI i campi editabili: nessuno memorizza
        # legittimamente '' (interi, numerici, enum-char, codici opzionali), quindi
        # svuotare = azzerare. Evita una lista di colonne nullable da tenere in
        # sync col DB e protegge i cast tipati della fn (::integer/::numeric) dal
        # crash su '': i campi nullable si azzerano, i NOT NULL restano rifiutati
        # dal vincolo (input FE invalido, mai inviato dalle select).
        clean: dict[str, Any] = {}
        for k, v in cliente_fields.items():
            if k not in self._UPDATE_ALLOWED:
                continue
            if isinstance(v, str) and not v.strip():
                v = None
            clean[k] = v
        with connection.cursor() as cursor:
            # Cast espliciti ai tipi dichiarati dalla fn: fn_update_cliente(
            # bigint, smallint, jsonb). psycopg invia gli int Python come int4;
            # int4->bigint e' implicito, ma int4->smallint (categoria_cliente_id)
            # e' un restringimento NON implicito -> senza ::smallint la
            # risoluzione dell'overload fallisce ("funzione non esiste") quando
            # la categoria e' un intero concreto (con NULL il tipo unknown si adatta).
            cursor.execute(
                """
                SELECT categoria_aggiornata, campi_aggiornati
                  FROM anagrafiche.fn_update_cliente(%s::bigint, %s::smallint, %s::jsonb)
                """,
                [cliente_id, ba_categoria_cliente_id, json.dumps(clean, default=str)],
            )
            row = cursor.fetchone()
            assert row is not None
        return {"categoria_aggiornata": bool(row[0]), "campi_aggiornati": bool(row[1])}
