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
from typing import Any, cast

from django.db import connection

from apps.config.sorgenti import SORGENTE_PREVENTIVO
from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT
from apps.core.db._helpers import (
    limiti_pagina,
    RicercaFull,
    add_ricerca_full_condition,
    fetch_paged_with_total,
    sql_order_clause,
    call_jsonb_fn,
    row_to_dict,
    rows_to_list,
)
from apps.core.db.emittente_scope_helpers import add_emittente_scope_condition
from apps.core.db.sql_write_helpers import execute_dynamic_update
from apps.vendite.db._componenti_repo_mixin import ComponentiRepositoryMixin
from apps.vendite.db._indirizzi_repo_mixin import IndirizziDocumentoRepositoryMixin
from apps.vendite.db._lineage_sintesi import unisci_sintesi_lineage
from apps.vendite.db._riepilogo_iva_repo_mixin import RiepilogoIvaRepositoryMixin
from apps.vendite.db._righe_repo_mixin import (
    COLONNE_RIGHE_COMMERCIALI,
    RICERCA_RIGHE_COMMERCIALI,
    RigheDocumentoRepositoryMixin,
)
from apps.vendite.types import (
    PreventivoDetailRow,
    PreventivoListRow,
    PreventivoPraticaRow,
    PreventivoSmistamentoRow,
)


# Scopo: Whitelist colonne ORDER BY per la lista preventivi (SQL injection safe).
#        La lista legge dalla vista canonica `vendite.vw_preventivi_lista`
#        (alias `v`); le chiavi sono i `campo_sorgente` del catalogo liste
#        ('vendite.preventivi') che il FE invia come sortField della DataTable
#        (`<ListaConfigurabile>` usa `:field="col.campo_sorgente"`). Nomi
#        canonici del soggetto (no alias `ba_*` su cliente/id.fiscale, lezione
#        DEF-8). `rev` volutamente ASSENTE: non ordinabile (decisione §7.3).
# Colonne che la ricerca libera SA cercare nella lista `vendite.preventivi`. Quali cerca
# davvero lo decide il catalogo a ogni ricerca (`add_ricerca_full_condition`);
# `test_ricerca_full_seed` verifica che coprano le `ricercabile_full` del seed.
_RICERCA_PREVENTIVI = RicercaFull(
    "vendite.preventivi",
    (
        "numero", "ragione_sociale_completa", "ba_codice", "id_fiscale_univoco_cf_piva",
    ),
)

_ORDER_COLS_PREVENTIVI: dict[str, str] = {
    "numero": "v.numero",
    "data": "v.data",
    "ragione_sociale_completa": "v.ragione_sociale_completa",
    "ba_codice": "v.ba_codice",
    "id_fiscale_univoco_cf_piva": "v.id_fiscale_univoco_cf_piva",
    "utility_codice": "v.utility_codice",
    "utility_descrizione": "v.utility_descrizione",
    "istanza_utility_codice": "v.istanza_utility_codice",
    "totale_documento": "v.totale_documento",
    "totale_imponibile": "v.totale_imponibile",
    "totale_iva": "v.totale_iva",
    "validita_al": "COALESCE(v.validita_al, 'infinity'::date)",
    "validita_dal": "COALESCE(v.validita_dal, '-infinity'::date)",
    "stato_descrizione": "v.stato_descrizione",
    # `stato_codice_interno` (tecnica, severity del Tag) ed
    # `emittente_fiscale_codice` (la colonna Emittente legge
    # `emittente_ragione_sociale`) sono uscite il 2026-07-31: nessuna
    # colonna del catalogo le invia come sortField.
    "valuta_codice": "v.valuta_codice",
    "competenza_mese": "v.competenza_mese",
    "data_insert": "v.data_insert",
    # Colonne lineage (Fase B brief-be-fe-lineage): pratica + fase ordinabili
    # (frontiera NON ordinabile, seed ui.lista_colonna transito.ordinabile=false).
    "pratica_numero": "v.pratica_numero",
    "fase": "v.fase",
}

# Scopo: whitelist ORDER BY del tab «Revisioni» del drawer preventivo (lista
#        `vendite.preventivo_revisioni`, alias `v` su `vw_preventivi_lista`).
# ⛔ COSTANTE NUOVA E SEPARATA da `_ORDER_COLS_PREVENTIVI`, di proposito: la
#    lista principale NON ordina per `rev` (decisione §7.3 qui sopra) e questa
#    invece parte proprio da li'. Allargare quella per servire questa avrebbe
#    offerto alla lista principale una freccia che il suo catalogo non ha — e
#    `test_liste_configurabili_seed` (test 2) l'avrebbe detta irraggiungibile.
# ⚠️ Le chiavi sono i `campo_sorgente` del catalogo (lista 89): le colonne
#    gemelle della lista offerte hanno gli STESSI codici ma campo_sorgente
#    diversi (`rev`/`revisione_numero`, `data`/`data_emissione`), ed e' questo
#    che il FE manda come `order_by`.
# ⚠️ `numero` e `stato_descrizione` dal 2026-09-28 (brief-db-liste-datatable-
#    grezze §9.1): colonne del nucleo rese ordinabili dal seed, GEMELLE di
#    quelle della lista 90 — si cambiano insieme.
PREVENTIVO_REVISIONI_ORDER_COLUMNS: dict[str, str] = {
    "rev": "v.rev",
    "numero": "v.numero",
    "data": "v.data",
    "stato_descrizione": "v.stato_descrizione",
    "totale_documento": "v.totale_documento",
}

# Colonne DATA della whitelist qui sopra: senza `order_dir` ordinano DESC
# (`sql_order_clause(colonne_desc=…)`, regola di Tid del 2026-09-02),
# confrontate col seed da `test_liste_configurabili_seed` (test 10).
PREVENTIVO_REVISIONI_SORT_COLONNE_DATA: frozenset[str] = frozenset({"data"})

# Risoluzione "rev attiva" del legame ROOT preventivo↔pratica/flusso
# (pratiche_sorgenti, sorgente PREVENTIVO, ruolo ROOT). Il link memorizza l'uid
# della rev AGGANCIATA (`p_link`); da essa deriviamo numero+emittente e
# ritorniamo la rev ATTIVA (`vw_preventivi.is_attiva`): la pratica segue sempre la
# revisione viva (revisione → nuova rev; annullamento revisione → predecessore,
# gratis da is_attiva). Nessun UPDATE del link, nessun trigger: risoluzione a
# read-time (Fase 4 uniformità pratica preventivi). Interpolato come costante
# (nessun input utente) → S608 ok.
# ⚠️ Il frammento porta UN parametro, il codice della sorgente
# (`SORGENTE_PREVENTIVO`): va PRIMO nella lista, prima di quelli del chiamante.
_ROOT_PREVENTIVO_ATTIVO_FROM = """
    FROM pratiche.pratiche_sorgenti ps
    JOIN config.sorgenti s ON s.id = ps.sorgente_tipo_id
    JOIN vendite.preventivi p_link ON p_link.uid::text = ps.sorgente_uid
    JOIN vendite.vw_preventivi p_attivo
      ON p_attivo.numero = p_link.numero
     AND p_attivo.emittente_fiscale_id = p_link.emittente_fiscale_id
     AND p_attivo.is_attiva
    WHERE s.codice_interno = %s
      AND ps.ruolo_link = 'ROOT'
"""


# Le righe del documento come lista configurabile `vendite.preventivo_righe` (BB
# `RigheDocumentoRepositoryMixin`, brief-db-liste-righe-documento lotto A).
# Le colonne gemelle sono dichiarate una volta nel BB; qui solo cio' che e'
# di questo documento. `test_ricerca_full_seed` legge `_RICERCA_RIGHE`.
_RICERCA_RIGHE = RicercaFull("vendite.preventivo_righe", RICERCA_RIGHE_COMMERCIALI)
_ORDER_COLS_RIGHE: dict[str, str] = {
    **COLONNE_RIGHE_COMMERCIALI,
    "data_consegna_richiesta_cliente": "data_consegna_richiesta_cliente",
}


class PreventiviRepository(
    RigheDocumentoRepositoryMixin,
    ComponentiRepositoryMixin,
    RiepilogoIvaRepositoryMixin,
    IndirizziDocumentoRepositoryMixin,
):
    """Repository preventivi.

    Eredita da `ComponentiRepositoryMixin` per il CRUD componenti BoM
    modello unificato (`preventivi_righe_componenti`). I metodi specifici
    `init_componenti_riga` (chiama `fn_preventivo_riga_componenti_init`)
    e `preview_componenti_riga` (chiama `fn_preventivo_riga_componenti_preview`)
    sono definiti localmente. Eredita da `RiepilogoIvaRepositoryMixin` la
    lettura del riepilogo IVA (vista mantenuta dal trigger AFTER su
    preventivi_righe via fn_ricalcola_riepilogo_iva_preventivo).
    """

    # Righe (BB `RigheDocumentoRepositoryMixin`): vista, chiave, ordine del
    # documento, whitelist e ricerca della lista `vendite.preventivo_righe`.
    _righe_vista = "vendite.vw_preventivi_righe_dettaglio"
    _righe_tabella = "vendite.preventivi_righe"
    # ⛔ `count_righe` (BB) non conta per stato di approvazione del prezzo:
    #    quella domanda ha una sede sola, script.fn_check_prezzi_autorizzati, e
    #    arriva nel blob delle capability (brief-db-preventivi-congelamento-
    #    pricing §6.1).
    _righe_fk_documento = "preventivo_id"
    _righe_ordine_documento = "ordine"
    _righe_ordinamento = _ORDER_COLS_RIGHE
    _righe_ricerca = _RICERCA_RIGHE
    _righe_colonne_desc = ("data_consegna_richiesta_cliente",)
    # Le date di consegna in blocco (BB `scrivi_data_consegna`): la sola
    # richiesta, che segue il lock delle righe (solo bozza).
    _righe_date_consegna = {"data_consegna_richiesta_cliente": None}

    # Configurazione mixin componenti.
    _componenti_table_name = "vendite.preventivi_righe_componenti"
    _componenti_fk_riga = "riga_preventivo_id"

    # Configurazione mixin riepilogo IVA (unica vista con `id` tecnico:
    # righe fisiche di preventivi_riepiloghi_iva, non derivate on-the-fly).
    _riepilogo_iva_vista = "vendite.vw_preventivi_riepilogo_iva_dettaglio"
    _riepilogo_iva_fk_documento = "preventivo_id"
    _riepilogo_iva_con_id = True

    # Configurazione mixin indirizzi documento.
    _indirizzi_table = "vendite.preventivi_indirizzi"
    _indirizzi_fk_documento = "preventivo_id"
    _indirizzi_ambito = "PREVENTIVI"
    _indirizzi_documento = SORGENTE_PREVENTIVO

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Testata (via vista canonica vw_preventivi_lista)
    # ══════════════════════════════════════════════════════════

    # Scopo: Restituisce elenco preventivi paginato dalla vista canonica
    #        `vendite.vw_preventivi_lista` (DEF-8, lista configurabile). La
    #        vista espone i nomi CANONICI senza alias (ragione_sociale_completa,
    #        id_fiscale_univoco_cf_piva, ba_codice) richiesti dal catalogo
    #        `ui.lista_colonna` di 'vendite.preventivi', `stato_codice_interno`
    #        per la severity del Tag FE, e `emittente_fiscale_id` per lo scope.
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
        solo_ultima_revisione: bool = True,
        auth_user_id: int | None = None,
        limit: int,
        offset: int,
        order_by: str = "data",
        order_dir: str = "desc",
        max_limit: int = MAX_LIMIT,
    ) -> tuple[list[PreventivoListRow], int]:
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=_ORDER_COLS_PREVENTIVI,
            default=_ORDER_COLS_PREVENTIVI["data"],
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

        # Filtri dinamici parametrizzati. `stato_codice` arriva dal FE come
        # `codice_interno` dello stato (LookupSelect value-field): nella vista
        # canonica la colonna e' `stato_codice_interno`.
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
        add_ricerca_full_condition(
            conditions, params, search, _RICERCA_PREVENTIVI,
        )
        # Filtro revisione attiva: di default mostra solo l'ultima revisione
        # "viva" per numero: `is_superata IS FALSE` — "non esiste una revisione
        # successiva che l'abbia rimpiazzata". Quando l'operatore vuole lo
        # storico completo (toggle "Mostra storico revisioni") il FE passa
        # solo_ultima_revisione=false.
        #
        # ⛔ ERA `is_attiva IS TRUE`, ed era il difetto (brief-db-revisione-attiva-due-domande,
        #    2026-08-28). `is_attiva` rispondeva a DUE domande in un flag solo —
        #    «e' l'ultima revisione?» E «non e' annullato?» — in AND, quindi non
        #    piu' separabili da chi legge. Effetto misurato: 18 preventivi
        #    ANNULLATO su 18 avevano `is_attiva = false`, e il filtro di stato
        #    «Annullato» non poteva restituire NIENTE, mai, per costruzione.
        #    Un'opzione di filtro che esiste nel menu e da' sempre zero.
        # ⚠️ `is_attiva` NON e' stata ritirata e resta giusta dov'e' la domanda
        #    giusta: nei cruscotti (`vw_dash_fatturazione_preventivi`) si chiede
        #    davvero «il documento e' vivo e corrente». La distinzione fra le due
        #    domande e' il punto del cantiere, non un dettaglio di nomi.
        if solo_ultima_revisione:
            conditions.append("v.is_superata IS FALSE")

        # Scope emittente (defense-in-depth applicativa). La vista
        # `vw_preventivi_lista` e' `security_invoker=on`: la RLS della tabella
        # base filtra gia' per emittente in scope. Questo filtro si somma
        # (api.md §"Scope emittente"). `fn_get_emittenti_scope_pk_ids` mappa su
        # PK reale `emittenti_fiscali.id` (NON `_sr_ids` = soggetto_ruolo_id);
        # `v.emittente_fiscale_id` e' la PK (memoria
        # feedback_emittente_pk_vs_soggetto_ruolo).
        add_emittente_scope_condition(
            conditions, params,
            auth_user_id=auth_user_id,
            column="v.emittente_fiscale_id",
            convention="pk",
        )

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        count_sql = f"SELECT COUNT(*) FROM vendite.vw_preventivi_lista v {where}"  # noqa: S608
        # Tiebreaker v.id obbligatorio per paginazione deterministica
        # (frontend-standards "REGOLA CRITICA: Paginazione deterministica").
        # Senza id, righe con stessa data/numero (es. revisioni) possono
        # comparire duplicate o sparire fra pagine consecutive.
        # ⭐ Il chip transito legge `frontiera_tipo_codice_interno` dalla
        # sintesi lineage (unita dopo la paginazione, sotto): mai id numerici
        # verso il FE, e mai una decodifica ricopiata per lista (memoria
        # feedback_no_hardcoded_ids).
        data_sql = f"""
            SELECT v.*
            FROM vendite.vw_preventivi_lista v
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
        unisci_sintesi_lineage(results, tipo_codice_interno=SORGENTE_PREVENTIVO)
        return cast("list[PreventivoListRow]", results), total_count

    # Scopo: Restituisce dettaglio singolo preventivo con tutte le decodifiche.
    # Usa query diretta (non vista lista) per includere campi extra (meta, storicizza, audit).
    def get_preventivo(self, preventivo_id: int) -> PreventivoDetailRow | None:
        sql = """
            SELECT
                p.id,
                p.uid::text AS uid,
                p.numero,
                p.rev,
                p.is_attiva,
                -- ⭐ LE TRE DOMANDE, e sono tre perche' hanno risposte diverse
                --    sulla stessa riga (brief-db-revisione-attiva-due-domande):
                --      `is_superata`        — esiste una revisione successiva
                --                             che l'ha RIMPIAZZATA (non abortita)
                --      `has_next_revisione` — esiste una revisione successiva
                --                             QUALUNQUE, anche annullata
                --      `is_attiva`          — non superata E non annullata
                --    Esempio: rev 0 EMESSO + rev 1 ANNULLATO
                --      -> has_next = TRUE, is_superata = FALSE, is_attiva = TRUE
                --    Il consumatore sceglie la domanda, invece di dedurla.
                -- ⛔ `has_next_revisione` NON si ricalcola qui: fino al 2026-08-28
                --    c'era un `EXISTS` inline che duplicava il predicato della
                --    vista. Due copie della stessa regola divergono senza che
                --    niente fallisca — e il nome esposto all'API resta inglese
                --    per non rompere il contratto col frontend.
                p.has_next_revisione AS has_next_revision,
                p.is_superata,
                p.data::text AS data,
                p.stato_doc_preventivo_id,
                sdp.codice_interno AS stato_codice_interno,
                sdp.codice AS stato_codice,
                sdp.descrizione AS stato_descrizione,
                p.billing_account_id,
                -- soggetto_ruolo del cliente (BA): serve al FE per la
                -- gestione indirizzi documento (elenco anagrafico cascata).
                ba.soggetto_ruolo_id,
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
                s_ef.ragione_sociale_completa
                    AS emittente_ragione_sociale,
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
            FROM vendite.vw_preventivi p
            JOIN config.stati_doc_preventivi sdp ON sdp.id = p.stato_doc_preventivo_id
            LEFT JOIN anagrafiche.billing_account ba ON ba.id = p.billing_account_id
            LEFT JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
            LEFT JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
            LEFT JOIN config.utilities u ON u.id = p.utility_id
            LEFT JOIN config.valute v ON v.id = p.valuta_id
            LEFT JOIN config.termini_pagamento tp ON tp.id = p.termine_pagamento_id
            -- Decode emittente fiscale: codice + ragione sociale del soggetto
            -- (nessun fallback a `emittenti_fiscali.descrizione`, rimosso col
            -- brief emittente-ragione-sociale-dal-soggetto). Pattern allineato a
            -- documenti repo per UX uniforme nei drawer (EmittenteFiscaleField
            -- in edit legge questi campi denormalizzati senza round-trip).
            LEFT JOIN anagrafiche.emittenti_fiscali ef ON ef.id = p.emittente_fiscale_id
            LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON sr_ef.id = ef.soggetto_ruolo_id
            LEFT JOIN anagrafiche.soggetti s_ef ON s_ef.id = sr_ef.soggetto_id
            WHERE p.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return cast("PreventivoDetailRow | None", row_to_dict(cursor))

    # ══════════════════════════════════════════════════════════
    #  LETTURE — Righe (via vista vw_preventivi_righe_dettaglio)
    # ══════════════════════════════════════════════════════════

    # Scopo: Stato corrente (codice_interno) del preventivo. Guard leggero
    #        pre-operazione (mirror ddt/ordini): mai il detail completo per
    #        leggere un solo campo.
    def get_stato_codice(self, preventivo_id: int) -> str | None:
        sql = """
            SELECT sdp.codice_interno
              FROM vendite.preventivi p
              JOIN config.stati_doc_preventivi sdp
                ON sdp.id = p.stato_doc_preventivo_id
             WHERE p.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            row = cursor.fetchone()
            return row[0] if row else None

    # CRUD indirizzi documento (list/upsert/delete + tipi ammessi) ereditato
    # da `IndirizziDocumentoRepositoryMixin`. Vedi `_indirizzi_repo_mixin.py`.

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
    #        (script.trgfn_default_emittente_fiscale, BB unico dal 2026-09-15,
    #        montato in fase _a10_default)
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

    # ⛔ Whitelist RIGIDA del BB `execute_dynamic_update` (2026-09-26): una
    #    chiave fuori lista e' `ValueError`, non uno scarto. E' l'elenco delle
    #    colonne che QUESTI metodi scrivono, non il contratto dell'operatore:
    #    la testata la scrivono `preventivi_service.aggiorna_preventivo` (tupla
    #    inline) e `cambia_stato` (fatturazione_immediata/competenza_mese
    #    all'accettazione); la riga anche il workflow L3
    #    (`approvazioni_prezzo_service`: stato_approvazione_prezzo,
    #    pratica_approvazione_prezzo_id, meta). Chi aggiunge un campo a monte
    #    lo aggiunge qui: dimenticarlo e' un errore che si vede.
    TESTATA_UPDATE_COLUMNS: frozenset[str] = frozenset({
        "billing_account_id", "istanza_utility_id",
        "valuta_id", "termine_pagamento_id",
        "validita_dal", "validita_al", "competenza_mese",
        "fatturazione_immediata", "meta",
    })
    RIGA_UPDATE_COLUMNS: frozenset[str] = frozenset({
        "descrizione", "qta_operativa", "uom_operativa_id",
        "factor_to_base", "prezzo_unitario", "sconto_percentuale",
        "ordine", "meta", "data_consegna_richiesta_cliente",
        "stato_approvazione_prezzo", "pratica_approvazione_prezzo_id",
    })

    # Scopo: Aggiorna campi modificabili della testata preventivo.
    # Accetta anche None per azzerare campi nullable.
    # Campi jsonb (meta) vengono serializzati con json.dumps e cast ::jsonb.
    def update_preventivo(
        self,
        preventivo_id: int,
        **kwargs: Any,
    ) -> bool:
        return execute_dynamic_update(
            "vendite.preventivi", preventivo_id, kwargs,
            allowed=self.TESTATA_UPDATE_COLUMNS,
        )

    # Scopo: Risolve l'id del preventivo agganciato come ROOT a una pratica
    #        (pratiche_sorgenti, sorgente PREVENTIVO). Unica fonte di verita' del
    #        legame preventivo↔pratica sul percorso pratica-first (creato a
    #        PREVENTIVAZIONE). Ritorna la rev ATTIVA del numero agganciato (segue
    #        la revisione viva), None se nessun ROOT preventivo.
    def get_preventivo_id_by_pratica_root(self, pratica_id: int) -> int | None:
        sql = f"SELECT p_attivo.id {_ROOT_PREVENTIVO_ATTIVO_FROM} AND ps.pratica_id = %s LIMIT 1"
        with connection.cursor() as cursor:
            cursor.execute(sql, [SORGENTE_PREVENTIVO, pratica_id])
            row = cursor.fetchone()
        return int(row[0]) if row else None

    # Scopo: Risolve l'id del preventivo agganciato come ROOT a un FLUSSO
    #        (pratiche_sorgenti.flusso_id, aggancio per-flusso). Fonte di verita'
    #        della RIAPERTURA dal percorso: l'attivita' UI ha il flusso_id e
    #        riapre il preventivo di quel flusso. None se nessun ROOT su quel
    #        flusso. L'indice unico parziale garantisce al piu' 1 riga. Ritorna la
    #        rev ATTIVA del numero agganciato (segue la revisione viva).
    def get_preventivo_id_by_flusso_root(self, flusso_id: int) -> int | None:
        sql = f"SELECT p_attivo.id {_ROOT_PREVENTIVO_ATTIVO_FROM} AND ps.flusso_id = %s LIMIT 1"
        with connection.cursor() as cursor:
            cursor.execute(sql, [SORGENTE_PREVENTIVO, flusso_id])
            row = cursor.fetchone()
        return int(row[0]) if row else None

    # Scopo: Reverse del legame ROOT per-flusso — dato un preventivo, ritorna il
    #        flusso d'origine (pratiche_sorgenti.flusso_id) o None. Alimenta
    #        l'auto-completamento all'emissione: il preventivo conosce IL SUO
    #        flusso, lo si completa direttamente senza cercarlo per azione_ui.
    #        Match per numero+emittente (non per uid): QUALSIASI revisione del
    #        numero agganciato trova il flusso (emissione di una rev successiva
    #        completa comunque PREVENTIVAZIONE).
    def get_flusso_id_by_preventivo_root(self, preventivo_id: int) -> int | None:
        sql = """
            SELECT ps.flusso_id
              FROM pratiche.pratiche_sorgenti ps
              JOIN config.sorgenti s ON s.id = ps.sorgente_tipo_id
              JOIN vendite.preventivi p_link ON p_link.uid::text = ps.sorgente_uid
              JOIN vendite.preventivi p_in
                ON p_in.numero = p_link.numero
               AND p_in.emittente_fiscale_id = p_link.emittente_fiscale_id
             WHERE s.codice_interno = %s
               AND ps.ruolo_link = 'ROOT'
               AND ps.flusso_id IS NOT NULL
               AND p_in.id = %s
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [SORGENTE_PREVENTIVO, preventivo_id])
            row = cursor.fetchone()
        return int(row[0]) if row else None

    # Scopo: Reverse del legame ROOT — dato un preventivo, ritorna la PRATICA cui
    #        e' agganciato come ROOT (pratiche_sorgenti.pratica_id) o None. A
    #        differenza di get_flusso_id_by_preventivo_root NON richiede
    #        `flusso_id IS NOT NULL`: la pratica e' sul link a prescindere
    #        dall'aggancio per-flusso (collega-pratica puo' essere chiamato senza
    #        flusso_id). Match per numero+emittente (revision-aware). Alimenta gli
    #        step del percorso pratica risolti dal preventivo (es.
    #        completa_smistamento).
    def get_pratica_id_by_preventivo_root(self, preventivo_id: int) -> int | None:
        sql = """
            SELECT ps.pratica_id
              FROM pratiche.pratiche_sorgenti ps
              JOIN config.sorgenti s ON s.id = ps.sorgente_tipo_id
              JOIN vendite.preventivi p_link ON p_link.uid::text = ps.sorgente_uid
              JOIN vendite.preventivi p_in
                ON p_in.numero = p_link.numero
               AND p_in.emittente_fiscale_id = p_link.emittente_fiscale_id
             WHERE s.codice_interno = %s
               AND ps.ruolo_link = 'ROOT'
               AND p_in.id = %s
             ORDER BY ps.id DESC
             LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [SORGENTE_PREVENTIVO, preventivo_id])
            row = cursor.fetchone()
        return int(row[0]) if row else None

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

    # Scopo: Annulla il preventivo via il verbo DB `vendite.fn_annulla_preventivo`
    #        (brief-db-annullo-documento-con-legami): con legami (righe di
    #        commessa da emettere) `legami_confermati` dichiara quanti
    #        l'operatore ne ha visti; se non corrisponde, E_DOC_ANNULLO_CON_LEGAMI.
    #        Lo stato passa ad ANNULLATO coi guard della tabella (matrice e
    #        `script.fn_check_preventivo_annullabile`).
    # Ritorna: i legami confermati (0 se non ce n'erano).
    def annulla(self, preventivo_id: int, legami_confermati: int | None) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT vendite.fn_annulla_preventivo(%s, %s)",
                [int(preventivo_id), legami_confermati],
            )
            row = cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else 0

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

    # Scopo: Lista PAGINATA della catena revisioni che condividono lo stesso
    #        `numero` del preventivo passato (lista `vendite.preventivo_revisioni`).
    #        Diverso dal modello offerte (catenate via `revisione_padre_id`, con
    #        la radice scritta sulla riga): qui le revisioni hanno tutte stesso
    #        `numero` (UNIQUE (numero, rev)) e si distinguono per `rev` (0 =
    #        prima). Legge la vista canonica `vw_preventivi_lista`: `is_attiva`,
    #        `stato_descrizione`, `totale_documento` gia' pronti.
    # ⛔ Fino al 2026-09-27 restituiva la catena INTERA senza LIMIT, e il tab la
    #    mostrava in una DataTable grezza: nessun paginatore, nessun ordinamento,
    #    nessuna scelta colonne (brief-db-liste-datatable-grezze §4 riga 7).
    # ⚠️ Nessun filtro emittente, ed e' voluto: l'`emittente_fiscale_id` che il
    #    tab manda lo legge SOLO il cancello di perimetro (la view lo dichiara
    #    `lista_emittente_param`). Le righe sono di UN documento, quindi di un
    #    emittente solo per costruzione; filtrarle ancora trasformerebbe un id
    #    sbagliato in una lista VUOTA, cioe' in un «nessuna revisione» falso e
    #    senza errore. La visibilita' resta alla RLS (vista `security_invoker`).
    def list_revisioni(
        self, preventivo_id: int, *,
        limit: int = DEFAULT_LIMIT, offset: int = 0,
        order_by: str | None = "rev", order_dir: str | None = "asc",
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=PREVENTIVO_REVISIONI_ORDER_COLUMNS, default="v.rev", tiebreak="v.id",
            colonne_desc=PREVENTIVO_REVISIONI_SORT_COLONNE_DATA,
        )
        params: list[Any] = [preventivo_id]
        from_where = (
            "FROM vendite.vw_preventivi_lista v "
            "WHERE v.numero = (SELECT numero FROM vendite.preventivi WHERE id = %s)"
        )
        return fetch_paged_with_total(
            f"""
            SELECT v.*, COUNT(*) OVER () AS total_count
            {from_where}
            ORDER BY {ordinamento}
            LIMIT %s OFFSET %s
            """,  # ORDER BY da sql_order_clause su whitelist, WHERE da condizioni letterali, valori come parametri
            params + [safe_limit, safe_offset],
            fallback_count_sql=f"SELECT COUNT(*) {from_where}",  # stesso FROM/WHERE della pagina
            fallback_params=params,
            offset=safe_offset,
        )

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

    # Scopo: Load atomico di un componente con guard scope completo
    # (componente → riga → preventivo) in UN'unica query JOIN. Sostituisce
    # la sequenza 3-query (`get_componente` + `get_riga` + `get_preventivo`)
    # del service `_load_componente_for_modification` (Fix #2 perf,
    # refactor-componenti.md §13). Ritorna `None` se il componente non
    # esiste; altrimenti dict con `{componente_id, riga_preventivo_id,
    # preventivo_id, stato_codice_interno, numero}` strettamente necessari ai
    # check del service (`numero` per l'etichetta di `richiedi_righe_in_bozza`).
    def load_componente_with_scope(
        self, componente_id: int,
    ) -> dict[str, Any] | None:
        sql = """
            SELECT c.id          AS componente_id,
                   c.riga_preventivo_id,
                   r.preventivo_id,
                   sdp.codice_interno AS stato_codice_interno,
                   -- L'etichetta del rifiuto di stato («Preventivo 2026/00012
                   -- rev. 1», o «Preventivo #131 rev. 0» se NULL): senza, il
                   -- guard delle righe in bozza ripiega sull'id anche su un
                   -- preventivo emesso, e senza `rev` non dice quale revisione.
                   p.numero,
                   p.rev
              FROM vendite.preventivi_righe_componenti c
              JOIN vendite.preventivi_righe r ON r.id = c.riga_preventivo_id
              JOIN vendite.preventivi p       ON p.id = r.preventivo_id
              JOIN config.stati_doc_preventivi sdp
                                              ON sdp.id = p.stato_doc_preventivo_id
             WHERE c.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [componente_id])
            return row_to_dict(cursor)

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
        data_consegna_richiesta_cliente: date | None = None,
    ) -> dict[str, Any]:
        sql = """
            INSERT INTO vendite.preventivi_righe (
                preventivo_id, articolo_id, descrizione,
                quantita, qta_operativa, uom_operativa_id, factor_to_base,
                prezzo_unitario, sconto_percentuale, iva_id, ordine, meta,
                stato_approvazione_prezzo, pratica_approvazione_prezzo_id,
                data_consegna_richiesta_cliente
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s,
                %s
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
                data_consegna_richiesta_cliente,
            ])
            result = row_to_dict(cursor)
            assert result is not None
            return result

    # Scopo: Aggiorna una riga preventivo esistente.
    # Campi jsonb (meta) vengono serializzati con json.dumps e cast ::jsonb.
    def update_riga(self, riga_id: int, **kwargs: Any) -> bool:
        return execute_dynamic_update(
            "vendite.preventivi_righe", riga_id, kwargs,
            allowed=self.RIGA_UPDATE_COLUMNS,
        )

    # Scopo: Elimina una riga preventivo (HARD DELETE).
    # Pattern simmetrico a `contratti_repository.delete_riga`: l'eliminazione
    # avviene solo in DRAFT (guard nel service: BB `richiedi_righe_in_bozza`),
    # in cui la riga e' una bozza non ancora pushed in commessa. La FK
    # `preventivi_righe_componenti.riga_preventivo_id` ha ON DELETE CASCADE
    # (migration 20260511-06): il DB pulisce automaticamente i componenti
    # BoM, niente UPDATE attivo=FALSE sui figli, niente trigger
    # `componenti_guard_obbligatorio` da bypassare.
    def delete_riga(self, riga_id: int) -> bool:
        sql = "DELETE FROM vendite.preventivi_righe WHERE id = %s"
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
    # restituiti (no filtro sull'esposizione), proiezione include
    # `obbligatorio` (gate prezzo zero) e `esposizione_in_fattura` (modo
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
                   esposizione_in_fattura
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

    # Scopo: Ramo MERCE dello split preventivo (brief-preventivi-ordini.md D8):
    #        delega a vendite.fn_push_preventivo_a_ordine. Copia le righe con
    #        natura destinazione_tipo='ORDINE_VENDITA' ancora residue verso un nuovo
    #        ordine DRAFT (snapshot prezzi + BoM), con idempotenza A LIVELLO RIGA
    #        (ordini_righe.preventivo_riga_id). Se `pratica_id` e' valorizzato la
    #        fn DB aggancia anche pratiche_sorgenti (preventivo ROOT + ordine
    #        COLLEGATO). Ritorna l'id dell'ordine creato.
    #        Solleva E_VENDITA_PREVENTIVO_NESSUNA_RIGA_ORDINE se non resta merce
    #        da smistare: il caller deve invocarla solo quando
    #        `preventivo_ha_residuo_ordine()` e' True.
    def push_a_ordine(
        self,
        preventivo_id: int,
        *,
        righe_ids: list[int] | None = None,
        pratica_id: int | None = None,
        fatturazione_trigger: str | None = None,
    ) -> int:
        # p_righe_ids NULL → tutte le righe merce residue; una lista → solo quel
        # sottoinsieme (smistamento selettivo). Cast espliciti per evitare
        # ambiguita' di tipo sui NULL non tipizzati.
        sql = """
            SELECT vendite.fn_push_preventivo_a_ordine(
                %s, %s::bigint[], %s::bigint, %s::varchar
            ) AS ordine_id
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [preventivo_id, righe_ids, pratica_id, fatturazione_trigger],
            )
            row = cursor.fetchone()
            assert row is not None and row[0] is not None
            return int(row[0])

    # Scopo: Righe MERCE smistabili a ordine — il sottoinsieme che alimenta il
    #        dialog di smistamento riga-per-riga (preventivo→ordine). Legge dalla
    #        **vista** `vendite.vw_preventivi_righe_smistabili_ordine`, FONTE
    #        UNICA del predicato (natura destinazione ORDINE, riga attiva, NON
    #        allocata), consumata anche da `fn_preventivo_ha_residuo_ordine` e
    #        `fn_push_preventivo_a_ordine` (consolidamento DB 2026-06-10): le
    #        righe restituite sono **esattamente** quelle che `push_a_ordine`
    #        copierebbe, senza ri-scrivere il predicato qui. La vista non espone i
    #        campi display → JOIN articolo/uom solo per codice/descrizione.
    def list_righe_smistabili_ordine(self, preventivo_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT
                s.id,
                s.ordine,
                s.articolo_id,
                a.codice            AS articolo_codice,
                a.descrizione       AS articolo_descrizione,
                s.descrizione,
                s.qta_operativa,
                s.uom_operativa_id,
                um.codice           AS uom_codice,
                s.prezzo_unitario,
                s.sconto_percentuale
              FROM vendite.vw_preventivi_righe_smistabili_ordine s
              LEFT JOIN catalogo.articoli a    ON a.id  = s.articolo_id
              LEFT JOIN catalogo.unita_misura um ON um.id = s.uom_operativa_id
             WHERE s.preventivo_id = %s
             ORDER BY s.ordine NULLS LAST, s.id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return rows_to_list(cursor)

    # Scopo: Predicato residuo MERCE (D6) — TRUE se restano righe natura
    #        destinazione_tipo='ORDINE_VENDITA' non ancora allocate a un ordine.
    #        Condiviso tra il dispatch del ramo ordine (decide se invocare
    #        push_a_ordine) e il gate EVASO (evadi solo a residuo nullo).
    def preventivo_ha_residuo_ordine(self, preventivo_id: int) -> bool:
        sql = "SELECT vendite.fn_preventivo_ha_residuo_ordine(%s) AS residuo"
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            row = cursor.fetchone()
            return bool(row[0]) if row else False

    # Scopo: TRUE se esiste gia' almeno un ordine generato da questo preventivo
    #        (riga ordine collegata via preventivo_riga_id). Usato dal guard di
    #        idempotenza natura-completo dell'handler per distinguere "gia'
    #        smistato" (artefatti presenti) da "preventivo vuoto" quando non
    #        resta nulla da smistare.
    def exists_ordine_da_preventivo(self, preventivo_id: int) -> bool:
        sql = """
            SELECT EXISTS (
                SELECT 1
                  FROM vendite.ordini_righe orr
                  JOIN vendite.preventivi_righe pr ON pr.id = orr.preventivo_riga_id
                 WHERE pr.preventivo_id = %s
            ) AS esiste
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            row = cursor.fetchone()
            return bool(row[0]) if row else False

    # Scopo: Predicato residuo COMMESSA (simmetrico a preventivo_ha_residuo_ordine,
    #        brief-db-smistamento-preventivi.md A) — TRUE se restano righe natura
    #        destinazione COMMESSA eleggibili al push non ancora EMESSE in
    #        commessa E la testata e' completa (billing_account + utility: la fn
    #        DB verifica anche i requisiti di testata del push). Condiviso tra
    #        capability can_push_commessa e gate EVASO bi-ramo.
    def preventivo_ha_residuo_commessa(self, preventivo_id: int) -> bool:
        sql = "SELECT vendite.fn_preventivo_ha_residuo_commessa(%s) AS residuo"
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            row = cursor.fetchone()
            return bool(row[0]) if row else False

    # Scopo: Aggregato smistamento per ramo (badge + progress X/Y del pannello).
    # Legge vw_preventivi_smistamento (rename DB 2026-06-12 della vecchia
    # vw_preventivi_stato_fatturazione, droppata): contatori natura-aware.
    def stato_smistamento(self, preventivo_id: int) -> PreventivoSmistamentoRow | None:
        sql = """
            SELECT *
            FROM vendite.vw_preventivi_smistamento
            WHERE preventivo_id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return cast("PreventivoSmistamentoRow | None", row_to_dict(cursor))

    # Scopo: Righe del Pannello Smistamento — una per riga attiva del preventivo,
    #        con natura, destinazione effettiva e `stato_smistamento` autorevole
    #        (RESIDUA/A_ORDINE/IN_COMMESSA/EMESSA_AF/FATTURATA). La vista espone
    #        gia' descrizione/qta/prezzo di riga e i riferimenti ordine
    #        (id+numero); JOIN solo per i display articolo/uom (regola display
    #        fields via JOIN, no lookup client-side).
    def list_righe_smistamento(self, preventivo_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT
                s.riga_id,
                s.riga_ordine,
                s.riga_descrizione,
                s.articolo_id,
                a.codice            AS articolo_codice,
                s.quantita,
                s.qta_operativa,
                s.uom_operativa_id,
                um.codice           AS uom_codice,
                s.prezzo_unitario,
                s.natura_vendita_id,
                s.natura_vendita_codice,
                s.destinazione_tipo,
                s.stato_smistamento,
                s.ordine_id,
                s.ordine_numero
              FROM vendite.vw_preventivi_smistamento_righe s
              LEFT JOIN catalogo.articoli a      ON a.id  = s.articolo_id
              LEFT JOIN catalogo.unita_misura um ON um.id = s.uom_operativa_id
             WHERE s.preventivo_id = %s
             ORDER BY s.riga_ordine NULLS LAST, s.riga_id
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return rows_to_list(cursor)

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
                ba.soggetto_ruolo_id,
                -- Il cliente a grana fine della pratica (D-9 di
                -- brief-db-istanza-nasce-col-ba): il BA del documento.
                ba.id AS billing_account_id
            FROM vendite.preventivi p
            JOIN anagrafiche.billing_account ba ON ba.id = p.billing_account_id
            JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
            WHERE p.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [preventivo_id])
            return row_to_dict(cursor)

    # Scopo: Generazione atomica della pratica da preventivo via funzione madre DB.
    #        Obiettivo: fondere in UNA sola statement (vendite.fn_genera_pratica_da_preventivo)
    #        la creazione della pratica (figlia condivisa pratiche.fn_crea_pratica) e
    #        l'INSERT del link ROOT su pratiche_sorgenti.
    #        Perimetro: o entrambe o rollback totale — niente piu' pratica orfana
    #        senza link se l'INSERT sorgente fallisce (fix analisi-fix-transazioni
    #        Classe A, finding #3; prima crea_pratica (@atomic a se') + link_pratica
    #        erano due unita' autocommit separate).
    #        La fn risolve internamente il contesto anagrafico (emittente PK +
    #        soggetto/ruolo + istanza dal BA del preventivo) e il tipo sorgente
    #        PREVENTIVO; e' SECURITY INVOKER (RLS/scope emittente invariati, §2-bis).
    #        Ritorna l'id della pratica creata.
    def genera_pratica_da_preventivo(
        self,
        *,
        preventivo_id: int,
        tipo_prestazione_id: int,
        priorita_id: int | None = None,
        descrizione: str | None = None,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT pratica_id
                  FROM vendite.fn_genera_pratica_da_preventivo(%s, %s, %s, %s)
                """,
                [preventivo_id, tipo_prestazione_id, priorita_id, descrizione],
            )
            row = cursor.fetchone()
            assert row is not None
            return int(row[0])

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
            return cast("list[PreventivoPraticaRow]", rows_to_list(cursor))

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

