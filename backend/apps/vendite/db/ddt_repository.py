# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB per DDT di vendita (CRUD testata, righe, componenti BoM,
#        evasione da ordine, push a commessa).
# ------------------------------------------------------------

# Repository DDT di vendita: letture sulla vista canonica
# `vendite.vw_ddt_lista` (lista) e su `vendite.ddt` (dettaglio), scritture
# dirette su tabelle, chiamate a funzioni DB per l'evasione da ordine
# (`fn_genera_ddt_da_ordine`) e i componenti BoM. Clone strutturale di
# `ordini_repository` adattato alle colonne reali del DDT (testata trasporto,
# destinatario/mittente/vettore, sorgente ordine). Numerazione a EMESSO gestita
# dal trigger DB `trgfn_ddt_gen_numero_emesso`; il ricalcolo prezzi del padre
# composito e la derivazione `quantita` da `qta_operativa` sono trigger DB.

import json
from datetime import date
from typing import Any

from django.db import connection

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
from apps.vendite.db._riepilogo_iva_repo_mixin import RiepilogoIvaRepositoryMixin
from apps.vendite.db._righe_repo_mixin import (
    COLONNE_RIGHE_COMMERCIALI,
    RICERCA_RIGHE_COMMERCIALI,
    RigheDocumentoRepositoryMixin,
)


# Scopo: Whitelist colonne ORDER BY per la lista DDT (SQL injection safe). Le
#        chiavi sono i `campo_sorgente` del catalogo liste ('vendite.ddt') che il
#        FE invia come sortField; i valori sono le colonne reali di
#        `vendite.vw_ddt_lista` (alias `v`).
# Colonne che la ricerca libera SA cercare nella lista `vendite.ddt`. Quali cerca
# davvero lo decide il catalogo a ogni ricerca (`add_ricerca_full_condition`);
# `test_ricerca_full_seed` verifica che coprano le `ricercabile_full` del seed.
_RICERCA_DDT = RicercaFull(
    "vendite.ddt",
    (
        "numero", "destinatario_denominazione", "ba_codice", "id_fiscale_univoco_cf_piva",
    ),
)

_ORDER_COLS_DDT: dict[str, str] = {
    "numero": "v.numero",
    "anno": "v.anno",
    "serie": "v.serie",
    "data": "v.data",
    "destinatario_denominazione": "v.destinatario_denominazione",
    "ba_codice": "v.ba_codice",
    "id_fiscale_univoco_cf_piva": "v.id_fiscale_univoco_cf_piva",
    "stato_descrizione": "v.stato_descrizione",
    "causale_trasporto_descrizione": "v.causale_trasporto_descrizione",
    "ordine_origine_numero": "v.ordine_origine_numero",
    "data_insert": "v.data_insert",
    # Colonne lineage (Fase B): pratica + fase ordinabili (frontiera no).
    "pratica_numero": "v.pratica_numero",
    "fase": "v.fase",
}


# Le righe del documento come lista configurabile `vendite.ddt_righe` (BB
# `RigheDocumentoRepositoryMixin`, brief-db-liste-righe-documento lotto A).
# Le colonne gemelle sono dichiarate una volta nel BB; qui solo cio' che e'
# di questo documento. `test_ricerca_full_seed` legge `_RICERCA_RIGHE`.
_RICERCA_RIGHE = RicercaFull("vendite.ddt_righe", RICERCA_RIGHE_COMMERCIALI)
_ORDER_COLS_RIGHE: dict[str, str] = {
    **COLONNE_RIGHE_COMMERCIALI,
}


class DdtRepository(
    RigheDocumentoRepositoryMixin,
    ComponentiRepositoryMixin,
    RiepilogoIvaRepositoryMixin,
    IndirizziDocumentoRepositoryMixin,
):
    """Repository DDT di vendita.

    Eredita da `ComponentiRepositoryMixin` per il CRUD componenti BoM modello
    unificato (`ddt_righe_componenti`, FK `riga_ddt_id`). I metodi specifici
    `init_componenti_riga` (chiama `fn_ddt_riga_componenti_init`) e
    `preview_componenti_riga` (chiama `fn_ddt_riga_componenti_preview`) sono
    definiti localmente. Usato anche dal push commessa (HandlerDdt) che legge i
    componenti negoziati della riga sorgente. Eredita da
    `RiepilogoIvaRepositoryMixin` la lettura del riepilogo IVA (vista derivata
    on-the-fly dalle righe attive valorizzate: le righe con prezzo NULL — DDT
    solo di trasporto — restano fuori dal riepilogo per filtro in vista).
    """

    # Righe (BB `RigheDocumentoRepositoryMixin`): vista, chiave, ordine del
    # documento, whitelist e ricerca della lista `vendite.ddt_righe`.
    _righe_vista = "vendite.vw_ddt_righe_dettaglio"
    _righe_tabella = "vendite.ddt_righe"
    _righe_fk_documento = "ddt_id"
    _righe_ordine_documento = "riga_nr"
    _righe_ordinamento = _ORDER_COLS_RIGHE
    _righe_ricerca = _RICERCA_RIGHE
    _righe_colonne_desc = ()

    # Configurazione mixin componenti (tabella + FK riga padre).
    _componenti_table_name = "vendite.ddt_righe_componenti"
    _componenti_fk_riga = "riga_ddt_id"

    # Configurazione mixin riepilogo IVA.
    _riepilogo_iva_vista = "vendite.vw_ddt_riepilogo_iva_dettaglio"
    _riepilogo_iva_fk_documento = "ddt_id"

    # Configurazione mixin indirizzi documento (whitelist ambito DDT: CON
    # obbligatorio all'emissione, guard trigger a DB).
    _indirizzi_table = "vendite.ddt_indirizzi"
    _indirizzi_fk_documento = "ddt_id"
    _indirizzi_ambito = "DDT"
    _indirizzi_documento_table = "vendite.ddt"
    # Ancora ownership/auto-default = DESTINATARIO (chi riceve la merce),
    # NOT NULL in testata: coerente col picker FE. Col BA e' il ruolo del BA
    # (`fk_ddt_ba_cliente`); senza — causale che non manda merce a un
    # cliente — e' il terzista o il deposito, e resta l'unica ancora.
    _indirizzi_doc_sr_column = "destinatario_soggetto_ruolo_id"

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Testata (via vista canonica vw_ddt_lista)
    # ══════════════════════════════════════════════════════════

    # Scopo: Elenco DDT paginato dalla vista canonica `vendite.vw_ddt_lista`.
    #        Espone i nomi CANONICI (destinatario_denominazione,
    #        id_fiscale_univoco_cf_piva, ba_codice), `stato_codice_interno` per
    #        la severity del Tag FE e `emittente_fiscale_id` per lo scope
    #        operatore (addendum §15 applicato 2026-07-10).
    # Risultato: tuple (lista righe, conteggio totale).
    def list_ddt(
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
        # NULL = valore MINIMO (lo mette `sql_order_clause`): il `numero` e' NULL
        # su tutte le bozze (lo assegna il trigger a EMESSO) e i default
        # PostgreSQL le mandavano IN CIMA ordinando dal piu' recente.
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS_DDT,
            default=_ORDER_COLS_DDT["data"],
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
        # `max_limit`: la lista pagina (cap `MAX_LIMIT`, gia' imposto da
        # parse_list_params), l'export chiede fino a EXPORT_MAX_ROWS+1 per
        # intercettare l'overflow SENZA troncare in silenzio (il guard di
        # build_export_response usa la COUNT reale).
        safe_limit, safe_offset = limiti_pagina(limit, offset, tetto=max_limit)

        conditions: list[str] = []
        params: list[Any] = []

        # `stato_codice` arriva dal FE come `codice_interno` (LookupSelect
        # value-field): nella vista la colonna e' `stato_codice_interno`.
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
        add_ricerca_full_condition(conditions, params, search, _RICERCA_DDT)

        # Scope emittente (defense-in-depth applicativa, mirror ordini). La
        # vista `vw_ddt_lista` e' `security_invoker=on` e `vendite.ddt` ha la
        # policy RLS `rls_ddt_ef_whitelist` (addendum §15): la RLS filtra gia'
        # per emittente in scope; questo filtro si somma (api.md §"Scope
        # emittente"). Array risolto UNA volta in Python dal BB condiviso
        # (memoria feedback_emittente_pk_vs_soggetto_ruolo per la convenzione PK).
        add_emittente_scope_condition(
            conditions, params,
            auth_user_id=auth_user_id,
            column="v.emittente_fiscale_id",
            convention="pk",
        )

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        count_sql = f"SELECT COUNT(*) FROM vendite.vw_ddt_lista v {where}"  # noqa: S608
        # Tiebreaker v.id per paginazione deterministica.
        data_sql = f"""
            SELECT v.*
            FROM vendite.vw_ddt_lista v
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

        return results, total_count

    # Scopo: Dettaglio singolo DDT. Riusa la vista canonica (decodifiche +
    #        provenienza ordine) e aggiunge i campi non esposti in lista:
    #        `meta`, `storicizza`, `istanza_utility_id` del BA (serve al FE
    #        per la cascata indirizzi a 3 livelli: senza istanza il livello
    #        'istanza' resta invisibile nel drawer indirizzi documento).
    #        `emittente_ragione_sociale` (ragione sociale del SOGGETTO
    #        emittente, consumata da EmittenteFiscaleField) arriva dalla
    #        vista (esposta dal DB team il 2026-07-13, brief
    #        emittente-user-e-etichetta-soggetto). None se id inesistente.
    def get_ddt(self, ddt_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT
                v.*,
                d.meta,
                d.storicizza,
                -- Corsia di instradamento: colonna aggiunta dalla Fase B del
                -- brief emissione mirata, non esposta dalla vista di lista.
                d.fatturazione_immediata,
                ba.istanza_utility_id,
                -- DEC-5: «questo documento vende?» ha UNA sede lato
                -- applicativo, ed e' la causale di trasporto. Grezzo, senza
                -- COALESCE: al FE serve distinguere «non vende» (false) da
                -- «causale non ancora scelta» (NULL), e un default a false
                -- cancellerebbe proprio quella differenza.
                ct.fatturabile AS causale_trasporto_fatturabile
              FROM vendite.vw_ddt_lista v
              JOIN vendite.ddt d ON d.id = v.id
              LEFT JOIN anagrafiche.billing_account ba
                ON ba.id = v.billing_account_id
              LEFT JOIN config.causali_trasporto ct
                ON ct.id = d.causale_trasporto_id
             WHERE v.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [ddt_id])
            return row_to_dict(cursor)

    # Scopo: Capability data-driven del DDT per il detail API. Wrapper su
    #        `script.fn_available_actions_ddt` (matrice transizioni
    #        `config.transizioni_stati_ddt`): ritorna jsonb con available_actions,
    #        can_change_state, can_edit_testata/righe,
    #        can_push_commessa(+reason/_reason_key), non_editable_fields,
    #        stato_codice. Blob opaco lato Python (passato intatto al FE).
    #        {} se la fn ritorna NULL (DDT inesistente — caller verifica a monte).
    def get_capabilities(self, ddt_id: int) -> dict[str, Any]:
        return call_jsonb_fn("script.fn_available_actions_ddt", ddt_id)

    # Scopo: Contesto minimo per la generazione documento (stampa PDF). Mirror
    #        di `OrdiniRepository.get_for_documento_generation`: ritorna
    #        id + uid + emittente_fiscale_id, i campi che
    #        `resolve_contesto_documentale` usa per il guard NOT_FOUND/emittente
    #        e l'orchestrator per scope/snapshot. None se id inesistente.
    #        `emittente_fiscale_id` e' NOT NULL a modello (addendum §15): il
    #        guard emittente dell'helper resta come defense-in-depth.
    def get_for_documento_generation(
        self, ddt_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT
                id,
                uid::text AS uid,
                emittente_fiscale_id
              FROM vendite.ddt
             WHERE id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(ddt_id)])
            return row_to_dict(cursor)

    # Scopo: Stato corrente (codice_interno) del DDT. Guard pre-operazione del
    #        service (es. modifica ammessa solo in DRAFT).
    def get_stato_codice(self, ddt_id: int) -> str | None:
        sql = """
            SELECT sd.codice_interno
              FROM vendite.ddt d
              JOIN config.stati_doc_ddt sd ON sd.id = d.stato_doc_ddt_id
             WHERE d.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [ddt_id])
            row = cursor.fetchone()
            return row[0] if row else None

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Righe
    # ══════════════════════════════════════════════════════════

    # Scopo: Load atomico di un componente con scope completo (componente →
    #        riga → ddt) in un'unica query JOIN, per i guard del service.
    def load_componente_with_scope(
        self, componente_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT c.id          AS componente_id,
                   c.riga_ddt_id,
                   r.ddt_id,
                   sd.codice_interno AS stato_codice_interno,
                   -- L'etichetta del rifiuto di stato («DDT 2026/00012», o
                   -- «DDT #131» se NULL): senza, il guard delle righe in
                   -- bozza ripiega sull'id anche su un DDT emesso.
                   d.numero
              FROM vendite.ddt_righe_componenti c
              JOIN vendite.ddt_righe r ON r.id = c.riga_ddt_id
              JOIN vendite.ddt d       ON d.id = r.ddt_id
              JOIN config.stati_doc_ddt sd ON sd.id = d.stato_doc_ddt_id
             WHERE c.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [componente_id])
            return row_to_dict(cursor)

    # ══════════════════════════════════════════════════════════
    #  SCRITTURE — Testata
    # ══════════════════════════════════════════════════════════

    # Scopo: Inserisce un nuovo DDT (standalone) e restituisce id, uid, numero.
    #        `numero` NON si passa: e' NULL in DRAFT e valorizzato dal trigger
    #        `trgfn_ddt_gen_numero_emesso` alla transizione a EMESSO.
    #        `emittente_fiscale_id` (NOT NULL, scope RLS) arriva dallo user
    #        (prefill FE dal profilo, mirror ordini — uniformazione 2026-07-13);
    #        se None lo risolve `trgfn_ddt_normalize` dal billing_account (o
    #        dall'ordine sorgente per i DDT da evasione).
    #        `stato_doc_ddt_id` (DRAFT) obbligatorio. Destinatario e utility,
    #        col BA, li scrive `trgfn_ddt_normalize` (la utility non si passa
    #        mai: e' copia del BA); senza BA il destinatario e' del chiamante.
    def create_ddt(
        self,
        *,
        destinatario_soggetto_ruolo_id: int | None,
        stato_doc_ddt_id: int,
        billing_account_id: int | None = None,
        emittente_fiscale_id: int | None = None,
        valuta_id: int | None = None,
        mittente_soggetto_ruolo_id: int | None = None,
        vettore_soggetto_ruolo_id: int | None = None,
        causale_trasporto_id: int | None = None,
        aspetto_bene_id: int | None = None,
        modalita_addebito_trasporto_id: int | None = None,
        num_colli: int | None = None,
        peso_lordo: str | None = None,
        peso_netto: str | None = None,
        volume: str | None = None,
        targa: str | None = None,
        autista: str | None = None,
        tracking_code: str | None = None,
        data: date | None = None,
        meta: dict[str, Any] | None = None,
        fatturazione_immediata: bool | None = None,
    ) -> dict[str, Any]:
        # BB `execute_dynamic_insert`: i None si omettono (`skip_none`) così i
        # DEFAULT del DB restano attivi; le chiavi sono letterali del metodo
        # (`allowed=None`). `meta` e' un dict -> `::jsonb` dal BB.
        valori: dict[str, Any] = {
            "destinatario_soggetto_ruolo_id": destinatario_soggetto_ruolo_id,
            "stato_doc_ddt_id": stato_doc_ddt_id,
            "billing_account_id": billing_account_id,
            "emittente_fiscale_id": emittente_fiscale_id,
            "valuta_id": valuta_id,
            "mittente_soggetto_ruolo_id": mittente_soggetto_ruolo_id,
            "vettore_soggetto_ruolo_id": vettore_soggetto_ruolo_id,
            "causale_trasporto_id": causale_trasporto_id,
            "aspetto_bene_id": aspetto_bene_id,
            "modalita_addebito_trasporto_id": modalita_addebito_trasporto_id,
            "num_colli": num_colli,
            "peso_lordo": peso_lordo,
            "peso_netto": peso_netto,
            "volume": volume,
            "targa": targa,
            "autista": autista,
            "tracking_code": tracking_code,
            "data": data,
            # Corsia di instradamento: None = DEFAULT false del DB (differita).
            "fatturazione_immediata": fatturazione_immediata,
            "meta": meta or {},
        }
        return execute_dynamic_insert(
            "vendite.ddt", valori, allowed=None, skip_none=True,
            returning="id, uid::text AS uid, numero",
        )

    # ⛔ Whitelist RIGIDA del BB `execute_dynamic_update` (2026-09-26): una
    #    chiave fuori lista e' `ValueError`, non uno scarto. E' l'elenco delle
    #    colonne che QUESTO metodo scrive, non il contratto dell'operatore (che
    #    sta nel service, `ddt_service.UPDATE_KEYS_DDT / UPDATE_KEYS_RIGA`): se il service ne aggiunge una, va aggiunta
    #    qui — e dimenticarlo e' un errore che si vede, non un campo perso.
    TESTATA_UPDATE_COLUMNS: frozenset[str] = frozenset({
        "billing_account_id", "destinatario_soggetto_ruolo_id",
        "valuta_id", "mittente_soggetto_ruolo_id",
        "vettore_soggetto_ruolo_id", "causale_trasporto_id", "aspetto_bene_id",
        "modalita_addebito_trasporto_id", "num_colli", "peso_lordo", "peso_netto",
        "volume", "targa", "autista", "tracking_code", "data", "meta",
        "fatturazione_immediata",
    })
    RIGA_UPDATE_COLUMNS: frozenset[str] = frozenset({
        "descrizione", "quantita", "qta_operativa", "uom_operativa_id",
        "factor_to_base", "prezzo_unitario", "sconto_percentuale", "meta",
    })

    # Scopo: Aggiorna campi modificabili della testata DDT. Accetta None per
    #        azzerare campi nullable. Campi jsonb (meta) serializzati ::jsonb.
    def update_ddt(self, ddt_id: int, **kwargs: Any) -> bool:
        return execute_dynamic_update(
            "vendite.ddt", ddt_id, kwargs, allowed=self.TESTATA_UPDATE_COLUMNS,
        )

    # Scopo: Hard-delete DDT (flusso abbandono bozza). Guard di dominio (stato
    #        DRAFT, no righe/fulfillment collegati) applicati nel service +
    #        trigger DB. Righe e componenti hanno ON DELETE CASCADE.
    def delete_ddt(self, ddt_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM vendite.ddt WHERE id = %s", [ddt_id])
            return cursor.rowcount > 0

    # Scopo: Cambia stato DDT via UPDATE diretto di stato_doc_ddt_id. La
    #        transizione e' validata dal trigger DB `trgfn_ddt_guard_transizione`
    #        (matrice `config.transizioni_stati_ddt`); l'emissione (→EMESSO)
    #        assegna il numero via `trgfn_ddt_gen_numero_emesso`; il guard
    #        approvazione blocca EMESSO con componenti PENDING.
    def update_stato(self, ddt_id: int, stato_doc_ddt_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE vendite.ddt SET stato_doc_ddt_id = %s WHERE id = %s",
                [stato_doc_ddt_id, ddt_id],
            )
            return cursor.rowcount > 0

    # ══════════════════════════════════════════════════════════
    #  SCRITTURE — Righe (quantita base derivata da qta_operativa via trigger DB)
    # ══════════════════════════════════════════════════════════

    # Scopo: Prossimo riga_nr disponibile per il DDT (NOT NULL + UNIQUE per DDT).
    def next_riga_nr(self, ddt_id: int) -> int:
        sql = (
            "SELECT COALESCE(MAX(riga_nr), 0) + 1 "
            "FROM vendite.ddt_righe WHERE ddt_id = %s"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [ddt_id])
            row = cursor.fetchone()
            return int(row[0]) if row else 1

    # Scopo: Lookup lean del flag `is_composito` dell'articolo (default prezzo
    #        padre composito = 0 / NULL; il prezzo padre e' SUM(figli) calcolata
    #        dal trigger DB post init componenti).
    def is_articolo_composito(self, articolo_id: str) -> bool:
        from apps.catalogo.db.catalogo_repository import CatalogoRepository
        return CatalogoRepository().is_articolo_composito(articolo_id)

    # Scopo: Inserisce una nuova riga DDT. `riga_nr` assegnato dal service via
    #        next_riga_nr. Ritorna id.
    def create_riga(
        self,
        *,
        ddt_id: int,
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
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO vendite.ddt_righe (
                ddt_id, riga_nr, articolo_id, descrizione,
                quantita, qta_operativa, uom_operativa_id, factor_to_base,
                prezzo_unitario, sconto_percentuale, iva_id, meta
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
            )
            RETURNING id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                ddt_id, riga_nr, articolo_id, descrizione,
                quantita, qta_operativa, uom_operativa_id, factor_to_base,
                prezzo_unitario, sconto_percentuale, iva_id,
                json.dumps(meta or {}),
            ])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna una riga DDT esistente. Campi jsonb (meta) ::jsonb.
    def update_riga(self, riga_id: int, **kwargs: Any) -> bool:
        return execute_dynamic_update(
            "vendite.ddt_righe", riga_id, kwargs, allowed=self.RIGA_UPDATE_COLUMNS,
        )

    # Scopo: Elimina una riga DDT (HARD DELETE). La FK
    #        ddt_righe_componenti.riga_ddt_id ha ON DELETE CASCADE. Il trigger DB
    #        `trgfn_dlt_block_ordrig_ddtrig`: in bozza la riga evasa si cancella
    #        e i suoi legami (fulfillment, ponte di ri-consegna) si ritirano con
    #        lei, riproiettando l'ordine (brief-db-ddt-righe-evase-dall-ordine
    #        D-3, D-7); blocca solo se la riga e' l'origine di un reso
    #        (E_DELETE_RIGA_DOC_REFERENZIATA).
    def delete_riga(self, riga_id: int) -> bool:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM vendite.ddt_righe WHERE id = %s", [riga_id])
            return cursor.rowcount > 0

    # Scopo: Corregge la quantita' evasa di una riga in bozza via il verbo DB
    #        `vendite.fn_ddt_riga_correggi_qta_evasa` (D-2): riga, componenti,
    #        legami e stato dell'ordine nella stessa operazione. Perimetro,
    #        stato, residuo e copertura del reso li giudica il DB.
    # Ritorna: la nuova quantita' evasa, in unita' base.
    def correggi_qta_evasa(self, riga_id: int, qta_operativa: Any) -> Any:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_ddt_riga_correggi_qta_evasa(%s, %s)",
                [int(riga_id), qta_operativa],
            )
            row = cursor.fetchone()
            return row[0] if row else None

    # Scopo: I legami della bolla, riga per riga (`vendite.fn_ddt_legami`,
    #        sede unica dell'avviso, della conferma e del ritiro dell'annullo):
    #        ddt_riga_id, riga_nr, origine (ORDINE/RESO), origine_riga_id, qta
    #        (unita' base).
    def list_legami(self, ddt_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT l.ddt_riga_id, l.riga_nr, l.origine, l.origine_riga_id, l.qta
              FROM vendite.fn_ddt_legami(%s) AS l
             ORDER BY l.riga_nr, l.origine
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(ddt_id)])
            return rows_to_list(cursor)

    # Scopo: Annulla la bolla via il verbo DB `vendite.fn_annulla_ddt` (D-8):
    #        con legami, `righe_legate_confermate` dichiara quante righe
    #        legate l'operatore ha visto (se non corrisponde:
    #        E_DDT_ANNULLO_CON_LEGAMI); poi ritiro dei legami e
    #        `fn_cambia_stato_ddt(…, 'ANNULLATO')` (matrice, permesso, storno).
    # Ritorna: i movimenti di storno (movimento_id, prelievo_id, qta).
    def annulla(
        self, ddt_id: int, righe_legate_confermate: int | None,
    ) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM vendite.fn_annulla_ddt(%s, %s)",
                [int(ddt_id), righe_legate_confermate],
            )
            return rows_to_list(cursor)

    # ══════════════════════════════════════════════════════════
    #  Componenti riga (BoM CASO A) — init/preview
    #  CRUD list/get/update/delete/purge da ComponentiRepositoryMixin.
    # ══════════════════════════════════════════════════════════

    # Scopo: Converte emittente_fiscale_id (PK) nel suo soggetto_ruolo_id, per le
    #        fn componenti che attendono sr_id (memoria
    #        feedback_emittente_pk_vs_soggetto_ruolo).
    def get_emittente_sr_id_by_fiscale_id(self, fiscale_id: int) -> int | None:
        from apps.anagrafiche.db.emittenti_fiscali_repository import (
            EmittentiFiscaliRepository,
        )
        return EmittentiFiscaliRepository().get_sr_id_by_fiscale_id(fiscale_id)

    # Scopo: Popola i componenti BoM per una riga padre composita invocando
    #        `vendite.fn_ddt_riga_componenti_init` (modello unificato, firma
    #        identica a fn_ordine_riga_componenti_init). Idempotente: 0 se gia'
    #        presenti o articolo non composito.
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
            "SELECT vendite.fn_ddt_riga_componenti_init("
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
    #        unificato, firma identica a fn_ordine_riga_componenti_preview). Per
    #        ogni componente attivo/valido alla data ritorna prezzo_suggerito
    #        (NULL se resolver fail) + resolver_error_reason.
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
              FROM vendite.fn_ddt_riga_componenti_preview(
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
    #  INTEGRAZIONE — Evasione da ordine + push commessa
    # ══════════════════════════════════════════════════════════

    # Scopo: Genera un DDT da un ordine (evasione) invocando la funzione madre
    #        `vendite.fn_genera_ddt_da_ordine` (atomica, DB-first): crea testata
    #        DRAFT + righe (snapshot A-2) + componenti + fulfillment riga↔riga e
    #        proietta lo stato ordine (CONFERMATO/PARZIALMENTE_EVASO/EVASO).
    #        `righe` = [{ordine_riga_id, qta_da_evadere}] in UNITA' OPERATIVA;
    #        None = tutto il residuo. Ritorna l'id del DDT creato.
    def push_da_ordine(
        self,
        ordine_id: int,
        righe: list[dict[str, Any]] | None = None,
        data: date | None = None,
    ) -> int:
        righe_json = json.dumps(righe) if righe is not None else None
        sql = (
            "SELECT vendite.fn_genera_ddt_da_ordine("
            "%s, %s::jsonb, COALESCE(%s, (SELECT script.fn_data_operativa())))"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [int(ordine_id), righe_json, data])
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

    # Scopo: Conteggio righe DDT eleggibili per il push singolo in commessa (via
    #        fn DB con parametro p_ddt_id). Usato dal service per il gating del
    #        pulsante push (eleggibilita' tipica SPEDITO/CONSEGNATO).
    def count_righe_pushable(self, ddt_id: int) -> int:
        sql = """
            SELECT COUNT(*) AS cnt
              FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL, %s)
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [ddt_id])
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    # ══════════════════════════════════════════════════════════
    #  LOOKUP — Risoluzione config per creazione/transizioni
    # ══════════════════════════════════════════════════════════

    # ⛔ `get_soggetto_ruolo_id_by_ba` RITIRATA (2026-10-10): il destinatario
    #    col BA lo scrive `trgfn_ddt_normalize` col BB
    #    `script.fn_cliente_dal_billing_account` (brief-db-esecutivi-ba-coppia
    #    §9.6, §10.2 domanda 2). Derivarlo qui era la quarta copia della regola.

    # Scopo: id di uno stato DDT via codice_interno (immutabile).
    def get_stato_id_by_codice(self, codice_interno: str) -> int | None:
        sql = """
            SELECT id FROM config.stati_doc_ddt
             WHERE codice_interno = %s AND attivo = true
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [codice_interno])
            row = cursor.fetchone()
            return row[0] if row else None
