# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository core per parametri di sistema (config.parameters)
#        con risoluzione override via script.fn_get_parameter_full.
#        Supporta: risoluzione singola/multipla, lista parametri per
#        utente con livelli override, CRUD override utente.
# ------------------------------------------------------------

from __future__ import annotations

from django.db import connection

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

# Limite massimo codici per singola richiesta (difesa contro abuse).
MAX_CODES = 20

# Le dimensioni di scope di `config.parameter_overrides`, in UN posto solo.
# ⭐ Un override gestito da qui e' «di livello puro»: la sua dimensione
#    valorizzata, TUTTE le altre NULL — in scrittura e in cancellazione. Il
#    NULL di ogni dimensione si DERIVA da questa tupla, non si elenca a mano.
# ⛔ Fino al 2026-09-28 ogni metodo aveva il suo elenco, e divergevano: gli
#    upsert utente ed emittente non azzeravano `categoria_cliente_id`, e la
#    delete emittente guardava solo utente e gruppo (F-5 dell'analisi difetti
#    doc API core). Il modello non vieta le righe miste (l'unicita' e' su
#    tutte le dimensioni insieme): il perimetro lo tiene questo modulo.
_DIMENSIONI_OVERRIDE: tuple[str, ...] = (
    "django_user_id",
    "django_group_id",
    "emittente_fiscale_id",
    "categoria_cliente_id",
    "session_key",
    "function_name",
)


# Scopo: Il frammento «tutte le altre dimensioni sono NULL» per uno scope.
#        `scope_col` viene dai chiamanti di questo modulo (mai input utente):
#        una colonna fuori tupla e' un errore di programmazione.
def _altre_dimensioni_nulle(scope_col: str, alias: str = "") -> str:
    if scope_col not in _DIMENSIONI_OVERRIDE:
        raise ValueError(f"Dimensione di override sconosciuta: {scope_col!r}")
    return "".join(
        f"   AND {alias}{c} IS NULL\n" for c in _DIMENSIONI_OVERRIDE if c != scope_col
    )


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

    # Scopo: Risolve N parametri in un'unica sessione DB.
    #        Restituisce un dizionario {code: valore_risolto}.
    #        I codici non trovati vengono esclusi dal risultato.
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
        safe_codes = codes[:MAX_CODES]
        results: dict[str, str] = {}
        with connection.cursor() as cursor:
            for code in safe_codes:
                cursor.execute(_SQL_RESOLVE, [
                    code, emittente_fiscale_id, django_user_id,
                    group_ids, None, None,
                    categoria_cliente_id,
                ])
                row = cursor.fetchone()
                if row and row[0] is not None:
                    results[code] = row[0]
        return results

    # Scopo: Restituisce la lista completa dei parametri con i valori risolti
    #        a ogni livello di scope (emittente, gruppo, utente, categoria_cliente)
    #        e il valore finale.
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
    ) -> list[dict]:
        # Cast espliciti (fix 2026-05-20): la signature DB e' (integer,
        # integer[], bigint, smallint). Senza cast, psycopg manda Python int
        # come `integer`, e PG non risolve la signature quando esistono
        # overload competing. Vedi `_SQL_RESOLVE` sopra per il pattern.
        sql = """
            SELECT * FROM script.fn_list_parameters_for_user(
                %s::integer,
                %s::integer[],
                %s::bigint,
                %s::smallint
            )
        """
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                [django_user_id, group_ids, emittente_fiscale_id, categoria_cliente_id],
            )
            columns = [col.name for col in cursor.description]
            rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    # Scopo: CTE-based upsert generico per config.parameter_overrides. Il classico
    #        ON CONFLICT ON CONSTRAINT non funziona: PostgreSQL tratta NULL != NULL
    #        nei UNIQUE constraint con colonne scope nullable, quindi serve il match
    #        esplicito IS NULL sulle dimensioni non usate (derivate da
    #        `_DIMENSIONI_OVERRIDE`). `scope_col` e' un nome colonna HARDCODED
    #        dai chiamanti (nessun input utente).
    #        Ritorna l'id dell'override, o None se il parametro NON ESISTE.
    # ⭐ Il parametro si risolve UNA volta (`param`), e se manca la query non
    #    produce righe: il chiamante lo dice col suo codice. Fino al 2026-09-28
    #    la sottoquery dava `parameter_id` NULL e l'INSERT violava il NOT NULL,
    #    cioe' un `E_DATABASE` al posto di «parametro non trovato» (E-9).
    # ⭐ L'UPDATE riattiva la riga (`attivo = true`, ok Tid 2026-09-28).
    #    `target` non guarda `attivo` e non puo' (l'unicita' non lo comprende:
    #    una seconda riga attiva accanto a quella spenta non si inserisce),
    #    mentre risoluzione e lista leggono solo `attivo = true`. Prima un
    #    upsert su una riga spenta (o NULL) rispondeva con l'id e non aveva
    #    effetto: override invisibile e inerte. Impostare un override vuol
    #    dire volerlo in vigore.
    def _upsert_override_cte(
        self,
        parameter_code: str,
        scope_col: str,
        scope_value: int,
        value: str,
    ) -> int | None:
        null_clause = _altre_dimensioni_nulle(scope_col, alias="po.")
        sql = f"""
            WITH param AS (
                SELECT id FROM config.parameters WHERE code = %s
            ),
            target AS (
                SELECT po.id FROM config.parameter_overrides po
                  JOIN param p ON p.id = po.parameter_id
                 WHERE po.{scope_col} = %s
{null_clause}            ),
            updated AS (
                UPDATE config.parameter_overrides po
                   SET overridden_value = %s, attivo = true, data_update = now()
                  FROM target t
                 WHERE po.id = t.id
                RETURNING po.id
            ),
            inserted AS (
                INSERT INTO config.parameter_overrides
                       (parameter_id, {scope_col}, overridden_value)
                SELECT p.id, %s, %s
                  FROM param p
                 WHERE NOT EXISTS (SELECT 1 FROM target)
                RETURNING id
            )
            SELECT id FROM updated
            UNION ALL
            SELECT id FROM inserted
        """  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [
                parameter_code, scope_value, value, scope_value, value,
            ])
            row = cursor.fetchone()
        return row[0] if row else None

    # Scopo: DELETE di un override di livello puro: l'id, il suo scope, e
    #        tutte le altre dimensioni NULL. Stesso perimetro dell'upsert.
    def _delete_override_puro(
        self, override_id: int, scope_col: str, scope_value: int,
    ) -> bool:
        null_clause = _altre_dimensioni_nulle(scope_col)
        sql = f"""
            DELETE FROM config.parameter_overrides
             WHERE id = %s
               AND {scope_col} = %s
{null_clause}        """  # noqa: S608
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
        return self._upsert_override_cte(
            parameter_code, "django_user_id", django_user_id, value,
        )

    # Scopo: Rimuove un override personale dell'utente (di livello puro:
    #        l'override deve essere dell'utente e di nessun'altra dimensione).
    def delete_user_override(
        self,
        override_id: int,
        django_user_id: int,
    ) -> bool:
        return self._delete_override_puro(override_id, "django_user_id", django_user_id)

    # Scopo: Crea o aggiorna un override a livello emittente per un parametro.
    #        Vale per tutti gli utenti dell'emittente, salvo override di
    #        gruppo o personali. None se il parametro non esiste.
    def upsert_emittente_override(
        self,
        parameter_code: str,
        emittente_fiscale_id: int,
        value: str,
    ) -> int | None:
        return self._upsert_override_cte(
            parameter_code, "emittente_fiscale_id", emittente_fiscale_id, value,
        )

    # Scopo: Rimuove un override a livello emittente (di livello puro).
    def delete_emittente_override(
        self,
        override_id: int,
        emittente_fiscale_id: int,
    ) -> bool:
        return self._delete_override_puro(
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
        return self._upsert_override_cte(
            parameter_code, "categoria_cliente_id", categoria_cliente_id, value,
        )

    # Scopo: Rimuove un override a livello categoria_cliente (di livello puro).
    def delete_categoria_cliente_override(
        self,
        override_id: int,
        categoria_cliente_id: int,
    ) -> bool:
        return self._delete_override_puro(
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
