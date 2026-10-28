# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository dell'area «Accessi» di Amm. Software: le due liste che
#        insieme alla lista operatori censiscono TUTTE le credenziali
#        («Altri accessi», «Di sistema») e lo stato di una credenziale (il
#        blocco dell'amministratore) per il pannello delle sue azioni.
# Note: file proprio e non `amm_software_repository.py` perche' e' un
#       sottodominio con le sue liste, i suoi verbi e le sue viste DB
#       (brief-db-be-fe-area-accessi), non tre metodi in piu' sugli operatori.
#       ⛔ La partizione fra i tre tab NON si scrive qui: la decide
#       `script.fn_categoria_accesso`, e le due viste la leggono gia'.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
    fetch_paged_with_total,
    limiti_pagina,
    row_to_dict,
    sql_lateral_primo_motivo,
    sql_order_clause,
)

# ⭐ Il vocabolario dello STATO di una veste e' del DB (`script.fn_stato_veste`,
#    A-7) piu' NESSUNO, che `vw_accessi_altri.stato_accesso` dichiara per la
#    credenziale senza vesti. Qui serve solo a rifiutare un filtro estraneo
#    con un 400 invece di rispondere una lista vuota: un valore sbagliato che
#    non trova niente e' un difetto che non da' errore. Presidio sul DB vero:
#    `test_accessi_db` legge i valori dal corpo della funzione.
STATI_ACCESSO: tuple[str, ...] = ("ATTIVO", "PENDING", "NON_SPEDITO", "DISATTIVO", "NESSUNO")

# Il TIPO di una credenziale di sistema (`vw_accessi_sistema.tipo`): l'utente
# tecnico di un processo automatico o un sistema esterno.
TIPI_SISTEMA: tuple[str, ...] = ("PROCESSO", "API_CLIENT")

# Whitelist ORDER BY di «Altri accessi»: chiave = `campo_sorgente` del catalogo
# (lista 104), valore = colonna della vista. Le colonne che il seed dichiara
# ordinabili, tutte e sole.
ACCESSI_ALTRI_ORDER_COLUMNS: dict[str, str] = {
    "nome_visualizzato": "v.nome_visualizzato",
    "username": "v.username",
    "stato_accesso": "v.stato_accesso",
    "nessun_accesso": "v.nessun_accesso",
    "secondo_fattore_stato": "v.secondo_fattore_stato",
    "bloccata": "v.bloccata",
    "ultimo_accesso": "v.ultimo_accesso",
}

# Whitelist ORDER BY di «Di sistema» (lista 105), stessa forma.
ACCESSI_SISTEMA_ORDER_COLUMNS: dict[str, str] = {
    "username": "v.username",
    "tipo": "v.tipo",
    "processo_codice": "v.processo_codice",
    "emittente_codice": "v.emittente_codice",
    "emittente_ragione_sociale": "v.emittente_ragione_sociale",
    "identita_attiva": "v.identita_attiva",
    "bloccata": "v.bloccata",
    "ultimo_accesso": "v.ultimo_accesso",
}

# Il primo motivo per cui la credenziale non si blocca (`[]` = si blocca).
_LATERAL_BLOCCO = sql_lateral_primo_motivo("script.fn_check_credenziale_bloccabile(au.id)", "blocco")

# Il primo motivo per cui la credenziale non si elimina (`[]` = si elimina),
# per il dettaglio (`au`) e per le righe di «Altri accessi» (`v`): la stessa
# check che il verbo `fn_elimina_credenziale` solleva (brief-db-elimina-
# credenziale-senza-veste §7.3). ⚠️ Sulla lista gira per riga filtrata (sotto
# la `COUNT(*) OVER ()`): con una veste la check esce subito, e la ricerca
# della storia (una lettura per FK) tocca le sole credenziali senza vesti.
_LATERAL_ELIMINA_DETTAGLIO = sql_lateral_primo_motivo(
    "script.fn_check_credenziale_eliminabile(au.id)", "elimina",
)
_LATERAL_ELIMINA_RIGA = sql_lateral_primo_motivo(
    "script.fn_check_credenziale_eliminabile(v.auth_user_id)", "elimina",
)

# La terna dell'eliminazione, stessa famiglia del blocco (`can_block`,
# `block_reason`, `block_reason_key`) piu' il dettaglio: per `CON_STORIA`
# porta `dove`, le tabelle che la chiave i18n nomina.
_COLONNE_ELIMINA = """
       (elimina.reason IS NULL) AS can_delete,
       elimina.reason AS delete_reason,
       elimina.reason_key AS delete_reason_key,
       elimina.dettaglio AS delete_dettaglio"""

# Le colonne DATA delle due liste: senza `order_dir` si leggono dalla piu'
# recente (regola di Tid, 2026-09-02). Costante di modulo: il presidio
# `test_liste_configurabili_seed` la confronta con le date ordinabili del seed.
_COLONNE_DESC: frozenset[str] = frozenset({"ultimo_accesso"})

# Cosa si PUO' cercare; cosa si cerca lo dice il catalogo (`ricercabile_full`).
# Colonne semplici della vista: la tupla, con l'alias `v`.
_RICERCA_ACCESSI_ALTRI = RicercaFull(
    "anagrafiche.accessi_altri",
    ("nome_visualizzato", "username", "email", "vesti_elenco", "soggetti_elenco"),
)
_RICERCA_ACCESSI_SISTEMA = RicercaFull(
    "anagrafiche.accessi_sistema",
    ("username", "processo_codice", "processo_descrizione",
     "emittente_codice", "emittente_ragione_sociale"),
)


class AccessiRepository:
    """Le liste «Altri accessi» e «Di sistema» e lo stato di una credenziale."""

    # Scopo: Le credenziali di categoria ALTRO (`anagrafiche.vw_accessi_altri`),
    #        paginate col totale in una valutazione. Filtri: la veste
    #        (`ruolo_applicativo` dentro `vesti`), lo stato riassunto, nessun
    #        accesso, secondo fattore (stato e obbligo), blocco. Ogni riga
    #        porta la capability dell'eliminazione (`can_delete` e la terna
    #        del motivo), per il kebab e il drawer.
    # ⚠️ `v.*`: la vista e' il contratto (§7.4 del brief), e una colonna
    #    elencata a mano sarebbe una colonna che il giorno dopo manca.
    # ⚠️ La vista attraversa `anagrafiche.clienti` (RLS): letta senza contesto,
    #    `cliente_ids` esce vuoto. Qui la legge la richiesta, con le sue GUC.
    def list_accessi_altri(
        self,
        *,
        search: str | None = None,
        ruolo_applicativo: str | None = None,
        stato_accesso: str | None = None,
        nessun_accesso: bool | None = None,
        secondo_fattore_stato: str | None = None,
        secondo_fattore_obbligatorio: bool | None = None,
        bloccata: bool | None = None,
        limit: int,
        offset: int,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[str] = ["TRUE"]
        params: list[Any] = []
        if ruolo_applicativo is not None:
            # Una veste di quel tipo fra le vesti della credenziale, accesa o no.
            conditions.append(
                "v.vesti @> jsonb_build_array(jsonb_build_object('ruolo_applicativo', %s::text))"
            )
            params.append(ruolo_applicativo)
        if stato_accesso is not None:
            conditions.append("v.stato_accesso = %s")
            params.append(stato_accesso)
        if nessun_accesso is not None:
            conditions.append("v.nessun_accesso = %s")
            params.append(nessun_accesso)
        if secondo_fattore_stato is not None:
            conditions.append("v.secondo_fattore_stato = %s")
            params.append(secondo_fattore_stato)
        if secondo_fattore_obbligatorio is not None:
            conditions.append("v.secondo_fattore_obbligatorio = %s")
            params.append(secondo_fattore_obbligatorio)
        if bloccata is not None:
            conditions.append("v.bloccata = %s")
            params.append(bloccata)
        add_ricerca_full_condition(conditions, params, search, _RICERCA_ACCESSI_ALTRI, alias="v")

        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=ACCESSI_ALTRI_ORDER_COLUMNS,
            default="v.nome_visualizzato",
            colonne_desc=_COLONNE_DESC,
            tiebreak="v.auth_user_id",
        )
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        sql = f"""
            SELECT v.*,{_COLONNE_ELIMINA},
                   COUNT(*) OVER () AS total_count
              FROM anagrafiche.vw_accessi_altri v
              {_LATERAL_ELIMINA_RIGA}
             WHERE {" AND ".join(conditions)}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """  # noqa: S608 — WHERE da frammenti letterali + colonne _RICERCA_ACCESSI_ALTRI, ORDER BY da whitelist, LATERAL e colonne da costanti di modulo, valori come parametri
        # `vesti` e il dettaglio del motivo arrivano decodificati dal lettore
        # comune (`fetch_paged_with_total`).
        return fetch_paged_with_total(sql, [*params, safe_limit, safe_offset], offset=safe_offset)

    # Scopo: Le credenziali di categoria SISTEMA (`anagrafiche.vw_accessi_sistema`):
    #        utenti tecnici dei processi automatici e API_CLIENT. Filtri: tipo,
    #        emittente, veste accesa, blocco. Sola lettura (A-6).
    def list_accessi_sistema(
        self,
        *,
        search: str | None = None,
        tipo: str | None = None,
        emittente_fiscale_id: int | None = None,
        identita_attiva: bool | None = None,
        bloccata: bool | None = None,
        limit: int,
        offset: int,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[str] = ["TRUE"]
        params: list[Any] = []
        if tipo is not None:
            conditions.append("v.tipo = %s")
            params.append(tipo)
        if emittente_fiscale_id is not None:
            conditions.append("v.emittente_fiscale_id = %s")
            params.append(emittente_fiscale_id)
        if identita_attiva is not None:
            conditions.append("v.identita_attiva = %s")
            params.append(identita_attiva)
        if bloccata is not None:
            conditions.append("v.bloccata = %s")
            params.append(bloccata)
        add_ricerca_full_condition(conditions, params, search, _RICERCA_ACCESSI_SISTEMA, alias="v")

        ordinamento = sql_order_clause(
            order_by, order_dir,
            colonne=ACCESSI_SISTEMA_ORDER_COLUMNS,
            default="v.username",
            colonne_desc=_COLONNE_DESC,
            tiebreak="v.auth_user_id",
        )
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        sql = f"""
            SELECT v.*, COUNT(*) OVER () AS total_count
              FROM anagrafiche.vw_accessi_sistema v
             WHERE {" AND ".join(conditions)}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """  # noqa: S608 — WHERE da frammenti letterali + colonne _RICERCA_ACCESSI_SISTEMA, ORDER BY da whitelist, valori come parametri
        return fetch_paged_with_total(sql, [*params, safe_limit, safe_offset], offset=safe_offset)

    # Scopo: Lo stato di UNA credenziale per il pannello delle sue azioni:
    #        categoria (il tab), blocco dell'amministratore (chi, quando,
    #        perche'), la capability del blocco (`can_block`, `block_reason`,
    #        `block_reason_key`) e quella dell'eliminazione (`can_delete` e la
    #        sua terna). `None` se la credenziale non esiste.
    # ⭐ La capability e' il PRIMO motivo di `script.fn_check_credenziale_bloccabile`,
    #    la stessa check che il verbo `fn_blocca_credenziale` chiama prima di
    #    scrivere e di cui solleva il primo motivo: pulsante spento e rifiuto
    #    non possono dire due cose diverse. Motivi e chiavi sono del DB.
    # ⚠️ Il blocco si legge dalla tabella: `config.credenziali` e' leggibile
    #    dall'app (le SCRITTURE passano dai verbi `script.fn_*_credenziale`).
    def get_credenziale(self, auth_user_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT au.id AS auth_user_id,
                       au.username,
                       NULLIF(au.email, '') AS email,
                       script.fn_categoria_accesso(au.id) AS categoria,
                       (cr.bloccata_at IS NOT NULL) AS bloccata,
                       cr.bloccata_at AS bloccata_dal,
                       chi.username AS bloccata_da,
                       cr.motivo_blocco,
                       (blocco.reason IS NULL) AS can_block,
                       blocco.reason AS block_reason,
                       blocco.reason_key AS block_reason_key,{_COLONNE_ELIMINA}
                  FROM auth_user au
                  LEFT JOIN config.credenziali cr ON cr.auth_user_id = au.id
                  LEFT JOIN auth_user chi ON chi.id = cr.bloccata_da
                  {_LATERAL_BLOCCO}
                  {_LATERAL_ELIMINA_DETTAGLIO}
                 WHERE au.id = %s
                """,  # noqa: S608 — frammenti da costanti di modulo, valori come parametri
                [auth_user_id],
            )
            return row_to_dict(cursor)

    # Scopo: Il verbo del blocco (`script.fn_blocca_credenziale`): SUPER_ADMIN
    #        (prima riga del verbo), motivo obbligatorio, anti-lockout nel guard.
    def blocca_credenziale(self, auth_user_id: int, motivo: str | None) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT script.fn_blocca_credenziale(%s, %s)", [auth_user_id, motivo])

    # Scopo: Il verbo dello sblocco (`script.fn_sblocca_credenziale`):
    #        idempotente, non tocca i tentativi.
    def sblocca_credenziale(self, auth_user_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT script.fn_sblocca_credenziale(%s)", [auth_user_id])

    # Scopo: Il verbo dell'eliminazione (`script.fn_elimina_credenziale`):
    #        SUPER_ADMIN (prima riga del verbo), lock sulla riga di
    #        `auth_user`, primo motivo della check, traccia in
    #        `config.credenziali_eliminate`, poi il DELETE (le righe che le
    #        appartengono seguono in CASCADE). ⛔ L'app non ha il DELETE su
    #        `django.auth_user`: questa e' l'unica porta.
    def elimina_credenziale(self, auth_user_id: int) -> None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT script.fn_elimina_credenziale(%s)", [auth_user_id])
