# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB per ordini di vendita (CRUD testata, righe, componenti BoM).
# ------------------------------------------------------------

# Repository ordini di vendita: letture sulla vista canonica
# `vendite.vw_ordini_lista` (lista DEF-8) e su `vendite.ordini` (dettaglio),
# scritture dirette su tabelle, chiamate a funzioni DB per i componenti BoM.
# Il ricalcolo totali e' gestito da trigger DB su ordini_righe; il backend
# non lo orchestra. Clone strutturale di `preventivi_repository` adattato alle
# colonne reali della testata/riga ordine (riga_nr, sconto_percentuale, iva_id) e
# senza revisioni (gli ordini non hanno `rev`).

import json
from datetime import date
from typing import Any

from django.db import connection

from apps.config.sorgenti import SORGENTE_ORDINE_VENDITA
from apps.core.api.constants import MAX_LIMIT
from apps.core.db._helpers import (
    limiti_pagina,
    RicercaFull,
    add_ricerca_full_condition,
    sql_order_clause,
    call_jsonb_fn,
    row_to_dict,
    rows_to_list,
)
from apps.core.db.emittente_scope_helpers import add_emittente_scope_condition
from apps.core.db.sql_write_helpers import execute_dynamic_insert, execute_dynamic_update
from apps.vendite.db._componenti_repo_mixin import ComponentiRepositoryMixin
from apps.vendite.db._indirizzi_repo_mixin import IndirizziDocumentoRepositoryMixin
from apps.vendite.db._lineage_sintesi import unisci_sintesi_lineage
from apps.vendite.db._riepilogo_iva_repo_mixin import RiepilogoIvaRepositoryMixin
from apps.vendite.db._righe_repo_mixin import (
    COLONNE_RIGHE_COMMERCIALI,
    RICERCA_RIGHE_COMMERCIALI,
    RigheDocumentoRepositoryMixin,
)


# Scopo: Whitelist colonne ORDER BY per la lista ordini (SQL injection safe).
#        La lista legge dalla vista canonica `vendite.vw_ordini_lista`
#        (alias `v`); le chiavi sono i `campo_sorgente` del catalogo liste
#        ('vendite.ordini') che il FE invia come sortField della DataTable.
#        Nomi canonici del soggetto (lezione DEF-8). `serie`/`anno` non
#        ordinabili (fuori dalla whitelist): la chiave logica e' `numero`.
# Colonne che la ricerca libera SA cercare nella lista `vendite.ordini`. Quali cerca
# davvero lo decide il catalogo a ogni ricerca (`add_ricerca_full_condition`);
# `test_ricerca_full_seed` verifica che coprano le `ricercabile_full` del seed.
_RICERCA_ORDINI = RicercaFull(
    "vendite.ordini",
    (
        "numero", "ragione_sociale_completa", "ba_codice", "id_fiscale_univoco_cf_piva",
    ),
)

_ORDER_COLS_ORDINI: dict[str, str] = {
    "numero": "v.numero",
    "anno": "v.anno",
    "serie": "v.serie",
    "data": "v.data",
    "ragione_sociale_completa": "v.ragione_sociale_completa",
    "ba_codice": "v.ba_codice",
    "id_fiscale_univoco_cf_piva": "v.id_fiscale_univoco_cf_piva",
    "utility_codice": "v.utility_codice",
    "utility_descrizione": "v.utility_descrizione",
    "totale_doc": "v.totale_doc",
    "imponibile_tot": "v.imponibile_tot",
    "iva_tot": "v.iva_tot",
    "fatturazione_trigger": "v.fatturazione_trigger",
    "stato_descrizione": "v.stato_descrizione",
    "data_insert": "v.data_insert",
    # Colonne lineage (Fase B): pratica + fase ordinabili (frontiera no).
    "pratica_numero": "v.pratica_numero",
    "fase": "v.fase",
}


# Le righe del documento come lista configurabile `vendite.ordine_righe` (BB
# `RigheDocumentoRepositoryMixin`, brief-db-liste-righe-documento lotto A).
# Le colonne gemelle sono dichiarate una volta nel BB; qui solo cio' che e'
# di questo documento. `test_ricerca_full_seed` legge `_RICERCA_RIGHE`.
_RICERCA_RIGHE = RicercaFull("vendite.ordine_righe", RICERCA_RIGHE_COMMERCIALI)
_ORDER_COLS_RIGHE: dict[str, str] = {
    **COLONNE_RIGHE_COMMERCIALI,
    "data_consegna_confermata": "data_consegna_confermata",
    "data_consegna_richiesta_cliente": "data_consegna_richiesta_cliente",
}


# La testata nella mappa del modello del documento (`script.fn_doc_stato_modello`):
# la leggono il repository, il service e la catena dei permessi.
TESTATA_ORDINI = "vendite.ordini"


class OrdiniRepository(
    RigheDocumentoRepositoryMixin,
    ComponentiRepositoryMixin,
    RiepilogoIvaRepositoryMixin,
    IndirizziDocumentoRepositoryMixin,
):
    """Repository ordini di vendita.

    Eredita da `ComponentiRepositoryMixin` per il CRUD componenti BoM
    modello unificato (`ordini_righe_componenti`). I metodi specifici
    `init_componenti_riga` (chiama `fn_ordine_riga_componenti_init`) e
    `preview_componenti_riga` (chiama `fn_ordine_riga_componenti_preview`)
    sono definiti localmente. Eredita da `RiepilogoIvaRepositoryMixin` la
    lettura del riepilogo IVA (vista derivata on-the-fly dalle righe attive,
    nessun trigger: a differenza dei preventivi non espone `id` tecnico).
    """

    # Righe (BB `RigheDocumentoRepositoryMixin`): vista, chiave, ordine del
    # documento, whitelist e ricerca della lista `vendite.ordine_righe`.
    _righe_vista = "vendite.vw_ordini_righe_dettaglio"
    _righe_tabella = "vendite.ordini_righe"
    _righe_fk_documento = "ordine_id"
    # Gli oneri dopo gli articoli: la sezione (1 articoli, 2 oneri) e' del DB
    # (20261103-51), poi la posizione della riga.
    _righe_ordine_documento = "sezione_documento"
    _righe_ordine_documento_extra = ("riga_nr",)
    _righe_ordinamento = _ORDER_COLS_RIGHE
    _righe_ricerca = _RICERCA_RIGHE
    _righe_colonne_desc = ("data_consegna_confermata", "data_consegna_richiesta_cliente")
    # Le date di consegna in blocco (BB `scrivi_data_consegna`): la confermata
    # salta le righe gia' spedite, motivo della check di riga (D-7, BF-1).
    _righe_date_consegna = {
        "data_consegna_richiesta_cliente": None,
        "data_consegna_confermata": (
            "script.fn_check_ordine_riga_data_consegna_confermata", "RIGA_SPEDITA",
        ),
    }

    # Configurazione mixin componenti (tabella + FK riga padre).
    _componenti_table_name = "vendite.ordini_righe_componenti"
    _componenti_fk_riga = "riga_ordine_id"

    # Configurazione mixin riepilogo IVA.
    _riepilogo_iva_vista = "vendite.vw_ordini_riepilogo_iva_dettaglio"
    _riepilogo_iva_fk_documento = "ordine_id"

    # Configurazione mixin indirizzi documento.
    _indirizzi_table = "vendite.ordini_indirizzi"
    _indirizzi_fk_documento = "ordine_id"
    _indirizzi_documento = SORGENTE_ORDINE_VENDITA

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Testata (via vista canonica vw_ordini_lista)
    # ══════════════════════════════════════════════════════════

    # Scopo: Elenco ordini paginato dalla vista canonica
    #        `vendite.vw_ordini_lista` (DEF-8). Espone i nomi CANONICI
    #        (ragione_sociale_completa, id_fiscale_univoco_cf_piva, ba_codice),
    #        `stato_codice_interno` per la severity del Tag FE, e
    #        `emittente_fiscale_id` per lo scope operatore.
    # Risultato: tuple (lista righe, conteggio totale).
    def list_ordini(
        self,
        *,
        stato_codice: str | None = None,
        billing_account_id: int | None = None,
        utility_id: int | None = None,
        data_da: date | None = None,
        data_al: date | None = None,
        search: str | None = None,
        auth_user_id: int | None = None,
        limit: int,
        offset: int,
        order_by: str = "data",
        order_dir: str = "desc",
        max_limit: int = MAX_LIMIT,
    ) -> tuple[list[dict[str, Any]], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS_ORDINI,
            default=_ORDER_COLS_ORDINI["data"],
            tiebreak="v.id",
            # ⭐ `default_desc=True`: senza indicazioni si legge dalla piu'
            #    recente. ⛔ Non e' cosmesi — il frontend apre questa lista a
            #    `data desc`, e con `removable-sort` esiste uno stato in cui
            #    l'ordinamento viene TOLTO e il backend applica il proprio: se
            #    i due default non coincidono, quello stato ribalta l'elenco in
            #    crescente senza che nessuna freccia lo dica (visto da Tid sui
            #    DDT il 2026-09-02).
            default_desc=True,
        )
        # `max_limit`: lista cap `MAX_LIMIT` (gia' via parse_list_params), export fino a
        # EXPORT_MAX_ROWS+1 per non troncare in silenzio (guard su COUNT reale).
        safe_limit, safe_offset = limiti_pagina(limit, offset, tetto=max_limit)

        conditions: list[str] = []
        params: list[Any] = []

        # `stato_codice` arriva dal FE come `codice_interno` (LookupSelect
        # value-field): nella vista canonica la colonna e' `stato_codice_interno`.
        if stato_codice is not None:
            conditions.append("v.stato_codice_interno = %s")
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
        add_ricerca_full_condition(conditions, params, search, _RICERCA_ORDINI)

        # Scope emittente (defense-in-depth applicativa). La vista
        # `vw_ordini_lista` e' `security_invoker=on`: la RLS della tabella base
        # filtra gia' per emittente in scope; questo filtro si somma (api.md
        # §"Scope emittente"). Array risolto UNA volta in Python dal BB condiviso; convenzione PK su
        # `emittenti_fiscali.id` (memoria feedback_emittente_pk_vs_soggetto_ruolo).
        add_emittente_scope_condition(
            conditions, params,
            auth_user_id=auth_user_id,
            column="v.emittente_fiscale_id",
            convention="pk",
        )

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        count_sql = f"SELECT COUNT(*) FROM vendite.vw_ordini_lista v {where}"  # noqa: S608
        # Tiebreaker v.id obbligatorio per paginazione deterministica
        # (frontend-standards "Paginazione deterministica").
        data_sql = f"""
            SELECT v.*
            FROM vendite.vw_ordini_lista v
            {where}
            ORDER BY {ordinamento}
            LIMIT %s OFFSET %s
        """  # noqa: S608

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            total_count = row[0] if row else 0

            cursor.execute(data_sql, [*params, safe_limit, safe_offset])
            results = rows_to_list(cursor)

        # Le colonne del grafo dalla sintesi, per le chiavi della pagina
        # (brief-db-lineage-seminata-per-chiave B1): la vista non le porta piu'.
        unisci_sintesi_lineage(results, tipo_codice_interno=SORGENTE_ORDINE_VENDITA)
        return results, total_count

    # Scopo: Dettaglio singolo ordine. Riusa la vista canonica (che ha gia'
    #        tutte le decodifiche + agente + documento di origine) e aggiunge
    #        i campi non esposti in lista: `meta`, `storicizza`,
    #        `istanza_utility_id` del BA (serve al FE per la cascata indirizzi
    #        a 3 livelli nel drawer indirizzi documento).
    #        `emittente_ragione_sociale` (ragione sociale del SOGGETTO
    #        emittente, consumata da EmittenteFiscaleField nel drawer EDIT)
    #        arriva dalla vista (esposta dal DB team il 2026-07-13).
    #        Ritorna None se id inesistente.
    def get_ordine(self, ordine_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT
                v.*,
                o.meta,
                o.storicizza,
                -- Corsia di instradamento: colonna aggiunta dalla Fase B del
                -- brief emissione mirata. Letta dalla tabella e non dalla vista
                -- di lista, che non la espone (la vista e' del team DB).
                o.fatturazione_immediata,
                ba.istanza_utility_id,
                -- Il nome del tipo d'origine come lo legge una persona: la
                -- stampa lo mette sulla carta al posto del codice
                -- (brief-db-grammatica-unica-documenti §12.9). LEFT: NULL
                -- quando l'ordine non ha origine.
                so.etichetta AS documento_origine_etichetta
              FROM vendite.vw_ordini_lista v
              JOIN vendite.ordini o ON o.id = v.id
              LEFT JOIN anagrafiche.billing_account ba
                ON ba.id = v.billing_account_id
              LEFT JOIN config.sorgenti so
                ON so.codice_interno = v.documento_origine_tipo
             WHERE v.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [ordine_id])
            return row_to_dict(cursor)

    # Scopo: Contesto minimo per la generazione documento (stampa PDF). Mirror
    #        di `PreventiviRepository.get_for_documento_generation`: ritorna
    #        id + uid + emittente_fiscale_id, i campi che
    #        `resolve_contesto_documentale` usa per il guard NOT_FOUND/emittente
    #        e l'orchestrator per scope/snapshot. None se id inesistente.
    def get_for_documento_generation(
        self, ordine_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT
                id,
                uid::text AS uid,
                emittente_fiscale_id
              FROM vendite.ordini
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(ordine_id)])
            return row_to_dict(cursor)

    # Scopo: Capability data-driven dell'ordine per il detail API. Wrapper su
    #        `script.fn_available_actions_ordine` (matrice transizioni
    #        `config.transizioni_stati_ordini`): ritorna jsonb con
    #        available_actions, can_change_state, can_edit_testata/righe,
    #        can_push_commessa(+reason/_reason_key), non_editable_fields,
    #        stato_codice. Blob opaco lato Python (passato intatto al FE).
    #        Pattern gemello di preventivi/offerte/contratti. {} se la fn
    #        ritorna NULL (ordine inesistente — il caller verifica a monte).
    def get_capabilities(self, ordine_id: int) -> dict[str, Any]:
        return call_jsonb_fn("script.fn_available_actions_ordine", ordine_id)

    # Scopo: Stato corrente (codice_interno) dell'ordine. Usato dal service
    #        come guard pre-operazione (es. modifica ammessa solo in DRAFT).
    def get_stato_codice(self, ordine_id: int) -> str | None:
        sql = """
            SELECT sd.codice_interno
              FROM vendite.ordini o
              JOIN config.stati_doc_ordini sd ON sd.id = o.stato_doc_ordine_id
             WHERE o.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [ordine_id])
            row = cursor.fetchone()
            return row[0] if row else None

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Righe
    # ══════════════════════════════════════════════════════════

    # Scopo: Load atomico di un componente con scope completo (componente →
    #        riga → ordine) in un'unica query JOIN, per i guard del service.
    def load_componente_with_scope(
        self, componente_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT c.id          AS componente_id,
                   c.riga_ordine_id,
                   r.ordine_id,
                   sd.codice_interno AS stato_codice_interno,
                   -- L'etichetta del rifiuto di stato («Ordine 2026/00012», o
                   -- «Ordine #131» se NULL): senza, il guard delle righe in
                   -- bozza ripiega sull'id anche su un ordine confermato.
                   o.numero
              FROM vendite.ordini_righe_componenti c
              JOIN vendite.ordini_righe r ON r.id = c.riga_ordine_id
              JOIN vendite.ordini o       ON o.id = r.ordine_id
              JOIN config.stati_doc_ordini sd ON sd.id = o.stato_doc_ordine_id
             WHERE c.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [componente_id])
            return row_to_dict(cursor)

    # ══════════════════════════════════════════════════════════
    #  SCRITTURE — Testata
    # ══════════════════════════════════════════════════════════

    # Scopo: Inserisce un nuovo ordine e restituisce id, uid, numero.
    #        `numero` e' generato dal trigger BEFORE INSERT
    #        (trgfn_ordini_gen_codice) → non si passa. `emittente_fiscale_id`
    #        opzionale: se None il trigger lo valorizza da GUC.
    #        Lo stato non si scrive: lo mette il DB, lo stato iniziale del
    #        vocabolario (`script.trgfn_doc_stato_iniziale`).
    def create_ordine(
        self,
        *,
        billing_account_id: int,
        emittente_fiscale_id: int | None = None,
        valuta_id: int | None = None,
        modalita_pagamento_id: int | None = None,
        termine_pagamento_id: int | None = None,
        fatturazione_trigger: str | None = None,
        agente_soggetto_ruolo_id: int | None = None,
        data: date | None = None,
        meta: dict[str, Any] | None = None,
        fatturazione_immediata: bool | None = None,
    ) -> dict[str, Any]:
        # BB `execute_dynamic_insert`: i None si omettono (`skip_none`) così i
        # DEFAULT del DB (es. fatturazione_trigger ereditato da BA via
        # trgfn_ordini_normalize, canale_origine='ADMIN') restano attivi; le
        # chiavi sono letterali del metodo (`allowed=None`).
        # ⭐ Ruolo del cliente e utility NON si scrivono: sono copie del BA, e
        #    le mette `trgfn_ordini_normalize` (BB `fn_cliente_dal_billing_account`,
        #    brief-db-esecutivi-ba-coppia §10.2 domanda 2).
        valori: dict[str, Any] = {
            "billing_account_id": billing_account_id,
            "emittente_fiscale_id": emittente_fiscale_id,
            "valuta_id": valuta_id,
            "modalita_pagamento_id": modalita_pagamento_id,
            "termine_pagamento_id": termine_pagamento_id,
            "fatturazione_trigger": fatturazione_trigger,
            "agente_soggetto_ruolo_id": agente_soggetto_ruolo_id,
            "data": data,
            # Corsia di instradamento (simmetria del flag): None = si lascia il
            # DEFAULT false del DB, cioe' corsia differita.
            "fatturazione_immediata": fatturazione_immediata,
            "meta": meta or {},
        }
        return execute_dynamic_insert(
            "vendite.ordini", valori, allowed=None, skip_none=True,
            returning="id, uid::text AS uid, numero",
        )

    # Scopo: Il primo ordine VIVO nato da (tipo, origine_id), o None. Lo
    #        leggono lo smistamento del preventivo (esito MERCE_PRESENTE) e
    #        l'handler che aggancia l'ordine alla pratica.
    #        ⛔ Solo i vivi (`NOT is_abortito_snapshot`, 2026-10-11): dal D-2 di
    #        brief-db-annullo-documento-con-legami un ordine annullato rilascia
    #        le righe del preventivo, che puo' generarne un altro. Leggere anche
    #        gli annullati darebbe MERCE_PRESENTE per un ordine morto e
    #        aggancerebbe alla pratica quello sbagliato.
    #        L'offerta non passa piu' da qui: «l'offerta e' gia' trasformata?»
    #        lo dice `vendite.fn_offerta_documenti_vivi`, dentro il verbo DB.
    def get_ordine_by_documento_origine(
        self, tipo: str, origine_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT id, numero
              FROM vendite.ordini
             WHERE documento_origine_tipo = %s
               AND documento_origine_id   = %s
               AND NOT is_abortito_snapshot
             ORDER BY id
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [tipo, int(origine_id)])
            return row_to_dict(cursor)

    # Scopo: Risolve l'ordine COLLEGATO a una PRATICA (pratiche_sorgenti, sorgente
    #        ORDINE_VENDITA, ruolo COLLEGATO; aggancio fatto da
    #        PostSmistamentoHandler). Alimenta gli step pratica a valle
    #        (CONFERMA_ORDINE / INVIO_COMMESSA) che aprono l'OrdiniDrawer su
    #        quell'ordine. None se non agganciato. Cross-schema read vendite→pratiche
    #        (direzione anelli consentita). sorgente_uid = id ordine (text).
    def get_ordine_id_by_pratica(self, pratica_id: int) -> int | None:
        sql = """
            SELECT ps.sorgente_uid::bigint
              FROM pratiche.pratiche_sorgenti ps
              JOIN config.sorgenti s ON s.id = ps.sorgente_tipo_id
             WHERE s.codice_interno = %s
               AND ps.ruolo_link    = 'COLLEGATO'
               AND ps.pratica_id    = %s
             ORDER BY ps.id DESC
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [SORGENTE_ORDINE_VENDITA, pratica_id])
            row = cursor.fetchone()
        return int(row[0]) if row else None

    # ⛔ Whitelist RIGIDA del BB `execute_dynamic_update` (2026-09-26): una
    #    chiave fuori lista e' `ValueError`, non uno scarto. E' l'elenco delle
    #    colonne che QUESTO metodo scrive, non il contratto dell'operatore (che
    #    sta nel service, `ordini_service.UPDATE_KEYS_ORDINE / UPDATE_KEYS_RIGA`): se il service ne aggiunge una, va aggiunta
    #    qui — e dimenticarlo e' un errore che si vede, non un campo perso.
    TESTATA_UPDATE_COLUMNS: frozenset[str] = frozenset({
        "billing_account_id", "valuta_id", "modalita_pagamento_id",
        "termine_pagamento_id", "fatturazione_trigger", "agente_soggetto_ruolo_id",
        "data", "meta", "fatturazione_immediata",
    })
    RIGA_UPDATE_COLUMNS: frozenset[str] = frozenset({
        "descrizione", "quantita", "qta_operativa", "uom_operativa_id",
        "factor_to_base", "prezzo_unitario", "sconto_percentuale", "meta",
        "data_consegna_richiesta_cliente", "data_consegna_confermata",
    })

    # Scopo: Aggiorna campi modificabili della testata ordine. Accetta None per
    #        azzerare campi nullable. Campi jsonb (meta) serializzati ::jsonb.
    def update_ordine(self, ordine_id: int, **kwargs: Any) -> bool:
        return execute_dynamic_update(
            "vendite.ordini", ordine_id, kwargs, allowed=self.TESTATA_UPDATE_COLUMNS,
        )

    # Scopo: Hard-delete ordine (flusso abbandono bozza). Guard di dominio
    #        (stato DRAFT, no DDT/fatture collegate) applicati nel service +
    #        trigger DB (trgfn_dlt_block_ordrig_ddtrig sulle righe). Le righe e
    #        i componenti hanno ON DELETE CASCADE.
    def delete_ordine(self, ordine_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM vendite.ordini WHERE id = %s",
                [ordine_id],
            )
            return cursor.rowcount > 0

    # Scopo: Annulla l'ordine via il verbo DB `vendite.fn_annulla_ordine`
    #        (brief-db-annullo-documento-con-legami): con legami (righe di
    #        preventivo, offerta d'origine, righe di commessa da emettere)
    #        `legami_confermati` dichiara quanti l'operatore ne ha visti; se non
    #        corrisponde, E_DOC_ANNULLO_CON_LEGAMI. Ritira i consumi e porta lo
    #        stato ad ANNULLATO (matrice e freni dai guard della tabella).
    # Ritorna: i legami confermati (0 se non ce n'erano).
    def annulla(self, ordine_id: int, legami_confermati: int | None) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_annulla_ordine(%s, %s)",
                [int(ordine_id), legami_confermati],
            )
            row = cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else 0

    # Scopo: Cambia lo stato dell'ordine dal suo verbo
    #        `vendite.fn_cambia_stato_ordine` (brief-modello-documento-vendita
    #        §9.6 C-1), gemello di `PreventiviRepository.cambia_stato`: permesso
    #        dalla riga del passaggio, perimetro, porta, e il guard di
    #        transizione per matrice, righe attive, aliquote, prezzi e
    #        annullabilita'. Lo stato chiesto e' il `codice_interno`.
    #        ⛔ Fino al 2026-10-25 un UPDATE diretto della colonna: ora la porta
    #        lo rifiuta (E_DOC_STATO_SOLO_DAL_VERBO).
    # Ritorna: {ordine_id, stato_precedente, stato_nuovo} (codici).
    def cambia_stato(self, ordine_id: int, stato_codice: str) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM vendite.fn_cambia_stato_ordine(%s, %s)",
                [int(ordine_id), stato_codice],
            )
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # ══════════════════════════════════════════════════════════
    #  SCRITTURE — Righe (ricalcolo totali automatico via trigger DB)
    # ══════════════════════════════════════════════════════════

    # Scopo: Prossimo riga_nr disponibile per l'ordine (riga_nr e' NOT NULL +
    #        UNIQUE per ordine, senza autoassegnazione DB).
    def next_riga_nr(self, ordine_id: int) -> int:
        sql = (
            "SELECT COALESCE(MAX(riga_nr), 0) + 1 "
            "FROM vendite.ordini_righe WHERE ordine_id = %s"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [ordine_id])
            row = cursor.fetchone()
            return int(row[0]) if row else 1

    # Scopo: Lookup lean del flag `is_composito` dell'articolo (default prezzo
    #        padre composito = 0 / NULL; il prezzo padre e' SUM(figli) calcolata
    #        dal trigger DB post init componenti).
    def is_articolo_composito(self, articolo_id: str) -> bool:
        from apps.catalogo.db.catalogo_repository import CatalogoRepository
        return CatalogoRepository().is_articolo_composito(articolo_id)

    # Scopo: Inserisce una nuova riga ordine. `riga_nr` assegnato dal service
    #        via next_riga_nr. Ritorna id.
    def create_riga(
        self,
        *,
        ordine_id: int,
        riga_nr: int,
        articolo_id: str,
        descrizione: str | None = None,
        quantita: str | None = None,
        qta_operativa: str | None = None,
        uom_operativa_id: int | None = None,
        factor_to_base: str | None = None,
        prezzo_unitario: str | None = None,
        sconto_percentuale: str | None = None,
        iva_id: int | None = None,
        meta: dict[str, Any] | None = None,
        data_consegna_richiesta_cliente: date | None = None,
        data_consegna_confermata: date | None = None,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO vendite.ordini_righe (
                ordine_id, riga_nr, articolo_id, descrizione,
                quantita, qta_operativa, uom_operativa_id, factor_to_base,
                prezzo_unitario, sconto_percentuale, iva_id, meta,
                data_consegna_richiesta_cliente, data_consegna_confermata
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb,
                %s, %s
            )
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                ordine_id, riga_nr, articolo_id, descrizione,
                quantita, qta_operativa, uom_operativa_id, factor_to_base,
                prezzo_unitario, sconto_percentuale, iva_id,
                json.dumps(meta or {}),
                data_consegna_richiesta_cliente, data_consegna_confermata,
            ])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna una riga ordine esistente. Campi jsonb (meta) ::jsonb.
    def update_riga(self, riga_id: int, **kwargs: Any) -> bool:
        return execute_dynamic_update(
            "vendite.ordini_righe", riga_id, kwargs, allowed=self.RIGA_UPDATE_COLUMNS,
        )

    # Scopo: Elimina una riga ordine (HARD DELETE). La FK
    #        ordini_righe_componenti.riga_ordine_id ha ON DELETE CASCADE.
    #        Il trigger DB trgfn_dlt_block_ordrig_ddtrig blocca la delete se la
    #        riga e' gia' collegata a un DDT.
    def delete_riga(self, riga_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM vendite.ordini_righe WHERE id = %s",
                [riga_id],
            )
            return cursor.rowcount > 0

    # ══════════════════════════════════════════════════════════
    #  Componenti riga (BoM CASO A) — init/preview
    #  CRUD list/get/update/delete/purge da ComponentiRepositoryMixin.
    # ══════════════════════════════════════════════════════════

    # Scopo: Converte emittente_fiscale_id (PK) nel suo soggetto_ruolo_id, per
    #        le fn componenti che attendono sr_id (memoria
    #        feedback_emittente_pk_vs_soggetto_ruolo).
    def get_emittente_sr_id_by_fiscale_id(self, fiscale_id: int) -> int | None:
        from apps.anagrafiche.db.emittenti_fiscali_repository import (
            EmittentiFiscaliRepository,
        )
        return EmittentiFiscaliRepository().get_sr_id_by_fiscale_id(fiscale_id)

    # Scopo: Popola i componenti BoM per una riga padre composita invocando
    #        `vendite.fn_ordine_riga_componenti_init` (modello unificato).
    #        Idempotente: ritorna 0 se gia' presenti o articolo non composito.
    def init_componenti_riga(
        self,
        *,
        riga_id: int,
        emittente_soggetto_ruolo_id: int,
        data_riferimento: date,
        componenti_overrides: dict[str, Any] | None = None,
    ) -> int:
        overrides_json: str | None
        if componenti_overrides is None:
            overrides_json = None
        else:
            overrides_json = json.dumps(
                {str(k): str(v) for k, v in componenti_overrides.items()},
            )
        sql = (
            "SELECT vendite.fn_ordine_riga_componenti_init("
            "%s, %s, %s, %s::jsonb)"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                riga_id, emittente_soggetto_ruolo_id, data_riferimento,
                overrides_json,
            ])
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    # Scopo: Preview read-only componenti BoM per il drawer riga (modello
    #        unificato). Per ogni componente attivo/valido alla data ritorna
    #        prezzo_suggerito (NULL se resolver fail) + resolver_error_reason.
    def preview_componenti_riga(
        self,
        *,
        articolo_id: str,
        uom_id: int | None,
        quantita_padre,
        data_riferimento: date,
        ba_id: int | None,
        utility_id: int | None,
        emittente_soggetto_ruolo_id: int,
        classe_utenza_id: int | None = None,
    ) -> list[dict[str, Any]]:
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
                   esposizione_in_fattura
              FROM vendite.fn_ordine_riga_componenti_preview(
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

    # ══════════════════════════════════════════════════════════
    #  INTEGRAZIONE — Push commessa
    # ══════════════════════════════════════════════════════════

    # Scopo: Conteggio righe ordine eleggibili per il push singolo in commessa
    #        (via fn DB con parametro p_ordine_id). Usato dal service per il
    #        gating del pulsante push.
    def count_righe_pushable(self, ordine_id: int) -> int:
        sql = """
            SELECT COUNT(*) AS cnt
              FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [ordine_id])
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    # ══════════════════════════════════════════════════════════
    #  LOOKUP — Risoluzione config per creazione/transizioni
    # ══════════════════════════════════════════════════════════

    # ⛔ `get_soggetto_ruolo_id_by_ba` RITIRATA (2026-10-10): ruolo e utility
    #    del cliente li scrive `trgfn_ordini_normalize` col BB
    #    `script.fn_cliente_dal_billing_account` (brief-db-esecutivi-ba-coppia
    #    §10.2 domanda 2). Derivarli qui era una copia della regola.

