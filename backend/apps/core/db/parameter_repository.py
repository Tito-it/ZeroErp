# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository core per parametri di sistema (config.parameters)
#        con risoluzione override via script.fn_get_parameter_full.
#        Supporta: risoluzione singola/multipla, lista parametri per
#        utente con livelli override, CRUD override utente.
# ------------------------------------------------------------

from __future__ import annotations

from django.db import connection
from typing import Any

from apps.core.db._helpers import (
    RicercaFull,
    add_ricerca_full_condition,
    fetch_paged_with_total,
    limiti_pagina,
    sql_order_clause,
)

# Whitelist ORDER BY della lista `config.parametri_impostazioni` (108): le
# colonne di uscita di `script.fn_list_parameters_for_user` (alias `p`). I
# valori dei livelli non si ordinano: sono testo di tipi diversi (seed §7.1).
IMPOSTAZIONI_ORDER_COLUMNS: dict[str, str] = {
    "code": "p.code",
    "description": "p.description",
}

# Cosa si PUO' cercare (cosa si cerca lo dice il catalogo).
_RICERCA_IMPOSTAZIONI = RicercaFull("config.parametri_impostazioni", ("code", "description"))

# Firma fn_get_parameter_full estesa (2026-05-15): aggiunto in coda
# p_categoria_cliente_id (smallint) per gating soglie commerciali per
# categoria cliente del BA destinatario.
# Catena priorita':
#   user -> categoria_cliente -> group -> emittente -> session -> function -> default
#
# Cast espliciti obbligatori sui placeholder (fix 2026-05-20): psycopg
# passa i Python int come `integer`, mentre la signature DB ha
# `bigint` (emittente_fiscale_id) e `smallint` (categoria_cliente_id).
# PG non fa upcast/downcast implicito → "function does not exist".
# Bug latente finora: i path che passavano `categoria_cliente_id=NULL`
# non lo manifestavano (NULL accetta qualunque tipo); emerso con il
# pricing gate L2 contratto MANUALE che passa il valore reale per
# la prima volta. Il cast sui placeholder `text`/`integer`/`integer[]`
# non sarebbe strettamente necessario ma e' incluso per simmetria
# e robustezza (zero ambiguita' sui tipi).
_SQL_RESOLVE = """
    SELECT script.fn_get_parameter_full(
        %s::text,
        %s::bigint,
        %s::integer,
        %s::integer[],
        %s::text,
        %s::text,
        %s::smallint
    )
"""

# ⭐ La stessa cascata, ma SOLO se il parametro e' dichiarato: la chiamata parte
#    dalla riga di `config.parameters`, e senza riga non c'e' chiamata (nessuna
#    riga in risposta). `fn_get_parameter_full` su un codice non dichiarato
#    SOLLEVA `E_ERRORE_PARAMETRI_TABELLA`, ed e' giusto: chi chiede un parametro
#    obbligatorio deve saperlo. Questa e' la lettura per chi lo dichiara
#    facoltativo (2026-10-11).
_SQL_RESOLVE_SE_DICHIARATO = """
    SELECT script.fn_get_parameter_full(
        p.code::text,
        %s::bigint,
        %s::integer,
        %s::integer[],
        %s::text,
        %s::text,
        %s::smallint
    )
      FROM config.parameters p
     WHERE p.code = %s::text
"""

# Limite massimo codici per singola richiesta (difesa contro abuse).
MAX_CODES = 20

# Le dimensioni di scope di `config.parameter_overrides`, in UN posto solo.
# ⭐ Un override vale per UN ambito: la sua dimensione valorizzata, tutte le
#    altre NULL. Dal 2026-10-07 lo dice il DB (`chk_parameter_overrides_un_ambito`,
#    `num_nonnulls(...) = 1`, decisione di Tid: le righe miste non esistono), e
#    l'unicita' sull'ambito e' vera (`uq_overrides_full_scope_v5`, NULLS NOT
#    DISTINCT). Qui la tupla resta solo come elenco delle colonne ammesse come
#    scope: i filtri «le altre dimensioni IS NULL» sarebbero una copia del CHECK
#    (la stessa pulizia del 20261007-73 sulla lista).
# ⛔ Fino al 2026-09-28 ogni metodo aveva il suo elenco, e divergevano (F-5
#    dell'analisi difetti doc API core); fino al 2026-10-07 il perimetro «puro»
#    lo teneva questo modulo, perche' il modello ammetteva le righe miste.
_DIMENSIONI_OVERRIDE: tuple[str, ...] = (
    "django_user_id",
    "django_group_id",
    "emittente_fiscale_id",
    "categoria_cliente_id",
    "session_key",
    "function_name",
)


# Scopo: La colonna di scope, verificata. `scope_col` viene dai chiamanti di
#        questo modulo (mai input utente) e finisce nella SQL per nome: una
#        colonna fuori tupla e' un errore di programmazione.
def _colonna_di_scope(scope_col: str) -> str:
    if scope_col not in _DIMENSIONI_OVERRIDE:
        raise ValueError(f"Dimensione di override sconosciuta: {scope_col!r}")
    return scope_col


class ParameterRepository:
    """Accesso DB ai parametri di sistema con risoluzione override."""

    # Scopo: Risolve il valore di un singolo parametro applicando la catena di
    #        override:
    #          user -> categoria_cliente -> group -> emittente -> session -> function -> default
    def get_parameter(
        self,
        code: str,
        django_user_id: int | None = None,
        group_ids: list[int] | None = None,
        emittente_fiscale_id: int | None = None,
        session_key: str | None = None,
        function_name: str | None = None,
        categoria_cliente_id: int | None = None,
    ) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(_SQL_RESOLVE, [
                code, emittente_fiscale_id, django_user_id,
                group_ids, session_key, function_name,
                categoria_cliente_id,
            ])
            row = cursor.fetchone()
        if not row:
            return None
        return row[0]

    # Scopo: Il valore di DEFAULT di un parametro (`config.parameters.default_value`),
    #        senza la cascata di override. None se il parametro non esiste o
    #        il default e' NULL.
    # ⭐ Per i limiti uguali per tutti (decisione del team DB, es. D-1 di
    #    brief-db-parametro-data-minima-ritardo-dashboard): la cascata farebbe
    #    valere un override che il modello non prevede. Stessa scelta di
    #    `script.fn_data_operativa` su SYSTEM_FUSO_ORARIO.
    def get_default_value(self, code: str) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT default_value FROM config.parameters WHERE code = %s",
                [code],
            )
            row = cursor.fetchone()
        return row[0] if row else None

    # Scopo: Come `get_parameter`, per un parametro FACOLTATIVO: None se il
    #        codice non e' dichiarato in `config.parameters` (o se il valore
    #        risolto e' NULL), invece di `E_ERRORE_PARAMETRI_TABELLA`.
    # ⭐ BB (regola del 2, ok Tid 2026-10-11): `get_parameters` e il default di
    #    natura del risolutore per ruolo (`SoggettiRepository.get_config_resolver`).
    #    Tutti e due dichiaravano «non trovato = escluso / None» e leggevano con la
    #    funzione che SOLLEVA: un ruolo senza `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_<ruolo>`
    #    (il seed lo da' a CL e FO) mandava in errore il risolutore.
    # ⛔ Non per un parametro che il modello pretende: li' l'errore e' il
    #    contratto, e si usa `get_parameter`.
    def get_parameter_se_dichiarato(
        self,
        code: str,
        django_user_id: int | None = None,
        group_ids: list[int] | None = None,
        emittente_fiscale_id: int | None = None,
        session_key: str | None = None,
        function_name: str | None = None,
        categoria_cliente_id: int | None = None,
    ) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute(_SQL_RESOLVE_SE_DICHIARATO, [
                emittente_fiscale_id, django_user_id,
                group_ids, session_key, function_name,
                categoria_cliente_id, code,
            ])
            row = cursor.fetchone()
        return row[0] if row else None

    # Scopo: Risolve N parametri in un'unica sessione DB.
    #        Restituisce un dizionario {code: valore_risolto}.
    #        I codici non dichiarati (e quelli che risolvono a NULL) vengono
    #        esclusi dal risultato: lettura FACOLTATIVA, BB
    #        `get_parameter_se_dichiarato`. Fino al 2026-10-11 un codice non
    #        dichiarato faceva fallire l'intera richiesta.
    def get_parameters(
        self,
        codes: list[str],
        django_user_id: int | None = None,
        group_ids: list[int] | None = None,
        emittente_fiscale_id: int | None = None,
        categoria_cliente_id: int | None = None,
    ) -> dict[str, str]:
        if not codes:
            return {}
        results: dict[str, str] = {}
        for code in codes[:MAX_CODES]:
            valore = self.get_parameter_se_dichiarato(
                code, django_user_id=django_user_id, group_ids=group_ids,
                emittente_fiscale_id=emittente_fiscale_id,
                categoria_cliente_id=categoria_cliente_id,
            )
            if valore is not None:
                results[code] = valore
        return results

    # Scopo: La pagina della lista `config.parametri_impostazioni` (108): i
    #        parametri con i valori risolti a ogni livello di scope (emittente,
    #        gruppo, utente, categoria_cliente) e il valore finale, con ricerca
    #        e ordinamento sulle colonne di uscita della funzione. Fino al
    #        2026-10-31 era la lista intera, filtrata nel browser.
    #        Delega a script.fn_list_parameters_for_user (migration 20260519-01,
    #        firma 4-arg).
    #        Output include `categoria_cliente_value` (text) e
    #        `categoria_cliente_override_id` (bigint, deriva da
    #        config.parameter_overrides.id%TYPE).
    def list_for_user(
        self,
        django_user_id: int,
        group_ids: list[int] | None = None,
        emittente_fiscale_id: int | None = None,
        categoria_cliente_id: int | None = None,
        *,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_limit, safe_offset = limiti_pagina(limit, offset)
        conditions: list[str] = []
        params: list[Any] = [django_user_id, group_ids, emittente_fiscale_id, categoria_cliente_id]
        add_ricerca_full_condition(conditions, params, search, _RICERCA_IMPOSTAZIONI, alias="p")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        ordinamento = sql_order_clause(
            order_by, order_dir, colonne=IMPOSTAZIONI_ORDER_COLUMNS, default="p.code", tiebreak="p.code",
        )
        # Cast espliciti (fix 2026-05-20): la signature DB e' (integer,
        # integer[], bigint, smallint). Senza cast, psycopg manda Python int
        # come `integer`, e PG non risolve la signature quando esistono
        # overload competing. Vedi `_SQL_RESOLVE` sopra per il pattern.
        sql = f"""
            SELECT p.*, COUNT(*) OVER () AS total_count
              FROM script.fn_list_parameters_for_user(
                %s::integer,
                %s::integer[],
                %s::bigint,
                %s::smallint
              ) p
            {where}
             ORDER BY {ordinamento}
             LIMIT %s OFFSET %s
        """  # noqa: S608 — WHERE dal BB add_ricerca_full_condition, ORDER BY da whitelist IMPOSTAZIONI_ORDER_COLUMNS, valori come parametri
        return fetch_paged_with_total(sql, [*params, safe_limit, safe_offset])

    # Scopo: Upsert generico di un override su config.parameter_overrides, sul
    #        vincolo che identifica l'ambito (`uq_overrides_full_scope_v5`, NULLS
    #        NOT DISTINCT: le dimensioni non scritte valgono NULL e collidono fra
    #        loro). Ritorna l'id dell'override, o None se il parametro NON ESISTE.
    # ⭐ Atomico: due upsert concorrenti sullo stesso ambito si serializzano sul
    #    vincolo e il secondo aggiorna. Fino al 2026-10-07 era una CTE
    #    SELECT-poi-INSERT col match IS NULL a mano, perche' il v4 (NULLS
    #    DISTINCT) non scattava su nessuna riga reale: due richieste concorrenti
    #    creavano un doppione, e la cascata ne sceglieva uno a caso. Col v5 la
    #    CTE avrebbe risposto `23505`; `ON CONFLICT` non risponde affatto.
    # ⭐ Il parametro si risolve nella SELECT dell'INSERT: se manca non nasce
    #    nessuna riga e il chiamante lo dice col suo codice. Fino al 2026-09-28
    #    la sottoquery dava `parameter_id` NULL e l'INSERT violava il NOT NULL,
    #    cioe' un `E_DATABASE` al posto di «parametro non trovato» (E-9).
    # ⭐ L'UPDATE riattiva la riga (`attivo = true`, ok Tid 2026-09-28).
    #    L'unicita' non comprende `attivo`: una riga spenta occupa il suo
    #    ambito, e risoluzione e lista leggono solo `attivo = true`. Prima un
    #    upsert su una riga spenta (o NULL) rispondeva con l'id e non aveva
    #    effetto: override invisibile e inerte. Impostare un override vuol
    #    dire volerlo in vigore.
    def _upsert_override(
        self,
        parameter_code: str,
        scope_col: str,
        scope_value: int,
        value: str,
    ) -> int | None:
        colonna = _colonna_di_scope(scope_col)
        sql = f"""
            INSERT INTO config.parameter_overrides
                   (parameter_id, {colonna}, overridden_value)
            SELECT p.id, %s, %s
              FROM config.parameters p
             WHERE p.code = %s
            ON CONFLICT ON CONSTRAINT uq_overrides_full_scope_v5 DO UPDATE
               SET overridden_value = EXCLUDED.overridden_value,
                   attivo = true,
                   data_update = now()
            RETURNING id
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [scope_value, value, parameter_code])
            row = cursor.fetchone()
        return row[0] if row else None

    # Scopo: DELETE di un override del suo ambito: l'id e il suo scope. Che le
    #        altre dimensioni siano NULL lo garantisce il CHECK del DB.
    def _delete_override(
        self, override_id: int, scope_col: str, scope_value: int,
    ) -> bool:
        colonna = _colonna_di_scope(scope_col)
        sql = f"""
            DELETE FROM config.parameter_overrides
             WHERE id = %s
               AND {colonna} = %s
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [override_id, scope_value])
            return cursor.rowcount > 0

    # Scopo: Crea o aggiorna un override personale dell'utente per un parametro.
    #        Cascata user > categoria_cliente > group > emittente > default.
    #        None se il parametro non esiste.
    def upsert_user_override(
        self,
        parameter_code: str,
        django_user_id: int,
        value: str,
    ) -> int | None:
        return self._upsert_override(
            parameter_code, "django_user_id", django_user_id, value,
        )

    # Scopo: Rimuove un override personale dell'utente (l'override deve
    #        essere dell'utente).
    def delete_user_override(
        self,
        override_id: int,
        django_user_id: int,
    ) -> bool:
        return self._delete_override(override_id, "django_user_id", django_user_id)

    # Scopo: Crea o aggiorna un override a livello emittente per un parametro.
    #        Vale per tutti gli utenti dell'emittente, salvo override di
    #        gruppo o personali. None se il parametro non esiste.
    def upsert_emittente_override(
        self,
        parameter_code: str,
        emittente_fiscale_id: int,
        value: str,
    ) -> int | None:
        return self._upsert_override(
            parameter_code, "emittente_fiscale_id", emittente_fiscale_id, value,
        )

    # Scopo: Rimuove un override a livello emittente.
    def delete_emittente_override(
        self,
        override_id: int,
        emittente_fiscale_id: int,
    ) -> bool:
        return self._delete_override(
            override_id, "emittente_fiscale_id", emittente_fiscale_id,
        )

    # Scopo: Crea o aggiorna un override a livello categoria_cliente per un
    #        parametro (colonna aggiunta in 20260515-06, cascata visualizzata
    #        in 20260519-01). Vale per TUTTI gli utenti che operano su BA di
    #        quella categoria, salvo override di gruppo o personali (cascata
    #        user > categoria_cliente > group > emittente > default).
    #        None se il parametro non esiste.
    def upsert_categoria_cliente_override(
        self,
        parameter_code: str,
        categoria_cliente_id: int,
        value: str,
    ) -> int | None:
        return self._upsert_override(
            parameter_code, "categoria_cliente_id", categoria_cliente_id, value,
        )

    # Scopo: Rimuove un override a livello categoria_cliente.
    def delete_categoria_cliente_override(
        self,
        override_id: int,
        categoria_cliente_id: int,
    ) -> bool:
        return self._delete_override(
            override_id, "categoria_cliente_id", categoria_cliente_id,
        )

    # Scopo: Risolve l'emittente_fiscale_id "corrente" per l'utente.
    #        Catena di fallback:
    #        1) whitelist personale (config.user_emittenti_fiscali) -> il
    #           proprio emittente;
    #        2) gestore globale dal mapping anagrafiche.emittenti_fiscali_billing_account
    #           (riga con billing_account_id IS NULL AND is_default = true), risolvendo
    #           poi l'emittenti_fiscali.id via JOIN su soggetto_ruolo_id.
    #        Restituisce None solo se nessuno dei due e' disponibile (sistema
    #        non configurato).
    #
    #        NB: la whitelist si legge DIRETTAMENTE, non via le funzioni di
    #        scope (fn_get_emittenti_scope*). Questa e' una SCELTA di
    #        "emittente corrente per risoluzione parametri", NON uno scope
    #        di visibilita': non deve applicare i guard (super_admin ->
    #        nessuna restrizione). Cosi' un SUPER_ADMIN con whitelist
    #        risolve sul PROPRIO emittente, non sul gestore globale —
    #        comportamento storico preservato. La tabella e' 1:1 per
    #        auth_user (UNIQUE su auth_user_id), quindi al piu' una riga.
    def get_emittente_fiscale_id_for_user(self, auth_user_id: int) -> int | None:
        with connection.cursor() as cursor:
            # 1) Whitelist personale (lettura diretta)
            cursor.execute(
                """
                SELECT emittente_fiscale_id
                  FROM config.user_emittenti_fiscali
                 WHERE auth_user_id = %s
                 LIMIT 1
                """,
                [auth_user_id],
            )
            row = cursor.fetchone()
            if row and row[0]:
                return row[0]

            # 2) Fallback: gestore globale dal mapping emittenti_fiscali_billing_account.
            #    La riga "gestore" ha billing_account_id IS NULL AND is_default = true.
            #    JOIN su emittenti_fiscali per ottenere la PK numerica usata da
            #    config.parameter_overrides.emittente_fiscale_id (FK -> emittenti_fiscali.id).
            cursor.execute(
                """
                SELECT ef.id
                  FROM anagrafiche.emittenti_fiscali_billing_account efba
                  JOIN anagrafiche.emittenti_fiscali ef
                    ON ef.soggetto_ruolo_id = efba.emittente_soggetto_ruolo_id
                 WHERE efba.billing_account_id IS NULL
                   AND efba.is_default = true
                   AND ef.attivo = true
                 LIMIT 1
                """
            )
            row = cursor.fetchone()
            return row[0] if row else None
