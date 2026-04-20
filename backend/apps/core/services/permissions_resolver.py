# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Risolutore centrale permessi ZeroErp.
# Delega la catena di risoluzione alle funzioni SQL script.fn_*
# e mantiene cache per-request (dict) per evitare roundtrip duplicati.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any, Callable, TypeVar

from django.db import connection

T = TypeVar("T")

# Mapping livello -> set di azioni CRUD consentite.
LIVELLO_MAP: dict[str, frozenset[str]] = {
    "TUTTO": frozenset({"view", "add", "change", "delete"}),
    "LETTURA": frozenset({"view"}),
    "BLOCCATO": frozenset(),
}


def _cached(
    cache: dict[str, Any] | None, key: str, compute_fn: Callable[[], T]
) -> T:
    """Scopo: Helper cache read/write — evita boilerplate ripetuto."""
    if cache is not None and key in cache:
        return cache[key]
    result = compute_fn()
    if cache is not None:
        cache[key] = result
    return result


class PermissionResolver:
    """Risolve il livello di accesso effettivo per un utente ZeroErp."""

    # ── Metodi pubblici ────────────────────────────────────

    @classmethod
    def is_super_admin(
        cls, user: Any, cache: dict[str, Any] | None = None
    ) -> bool:
        """Scopo: Verifica se l'utente ha il binding SUPER_ADMIN attivo.

        Delega a `script.fn_is_super_admin` (PR1 §4.6.B.1). Ritorna
        False per utenti senza binding, con identita inattiva o
        finestra temporale scaduta (fail-closed). Sostituisce il check
        legacy `get_ruolo_sistema(user) == "ADMIN"` nei caller.

        §8.3.7 multi-face: la fn DB filtra esplicitamente per
        `ruolo_applicativo = 'OPERATORE'` (post migration 20260420-*).
        Un utente con identita CLIENTE_PORTALE / FORNITORE_PORTALE /
        SHOP_CUSTOMER + binding SUPER_ADMIN sulla stessa auth_user
        NON attiva il bypass: il privilegio e' legato alla "veste"
        OPERATORE, non all'auth_user. Enforcement centralizzato lato
        DB — il wrapper Python non duplica la logica. Il contratto
        cross-veste e' verificato da pgTAP su
        `db/pgtap/script/fn_is_super_admin*.sql` (single source of
        truth): un mock Python non puo' darne prova, ritorna solo
        quello che gli si passa.
        """
        def _query() -> bool:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT script.fn_is_super_admin(%s)", [user.id]
                )
                row = cursor.fetchone()
            return bool(row[0]) if row else False

        return _cached(cache, "is_super_admin", _query)

    @classmethod
    def get_ruolo_applicativo(
        cls, user: Any, cache: dict[str, Any] | None = None
    ) -> str | None:
        """Scopo: Restituisce il ruolo_applicativo dell'identita attiva.

        Strategia GUC-first (Q1): se `app.ruolo_applicativo` e'
        popolato (JwtAuditAuthentication lo ha gia' propagato per la
        request corrente), ritorna quel valore senza query DB. In
        assenza di GUC (scenari di test che non passano dalla auth
        class, management command, chiamate non-HTTP), fallback a
        query su `anagrafiche.identita_digitali` filtrata sull'identita
        attiva.

        Ritorna None se l'utente non ha alcuna identita attiva.
        """
        def _query() -> str | None:
            with connection.cursor() as cursor:
                # Scopo: tenta GUC prima — zero round-trip DB se popolato.
                cursor.execute(
                    "SELECT NULLIF(current_setting('app.ruolo_applicativo', true), '')"
                )
                row = cursor.fetchone()
                if row and row[0]:
                    return str(row[0])
                # Scopo: fallback query diretta su identita_digitali.
                cursor.execute(
                    """
                    SELECT ruolo_applicativo
                      FROM anagrafiche.identita_digitali
                     WHERE auth_user_id = %s
                       AND attivo = true
                     LIMIT 1
                    """,
                    [user.id],
                )
                row = cursor.fetchone()
            return str(row[0]) if row and row[0] else None

        return _cached(cache, "ruolo_applicativo", _query)

    @classmethod
    def get_livello_area(
        cls,
        user: Any,
        area_schema_db: str,
        *,
        cache: dict[str, Any] | None = None,
    ) -> str:
        """Scopo: Restituisce il livello effettivo per un'area funzionale.
        Delega l'intera catena alla funzione SQL script.fn_resolve_livello_area."""
        def _query() -> str:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT script.fn_resolve_livello_area(%s, %s)",
                    [user.id, area_schema_db],
                )
                row = cursor.fetchone()
            return row[0] if row else "BLOCCATO"

        return _cached(cache, f"area:{area_schema_db}", _query)

    @classmethod
    def get_livello_oggetto(
        cls,
        user: Any,
        app_label: str,
        model_name: str,
        area_schema_db: str,
        *,
        cache: dict[str, Any] | None = None,
    ) -> str:
        """Scopo: Restituisce il livello effettivo per un singolo model.
        Delega alla funzione SQL script.fn_resolve_livello_oggetto."""
        def _query() -> str:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT script.fn_resolve_livello_oggetto(%s, %s, %s, %s)",
                    [user.id, app_label, model_name, area_schema_db],
                )
                row = cursor.fetchone()
            return row[0] if row else "BLOCCATO"

        return _cached(cache, f"oggetto:{app_label}.{model_name}", _query)

    @classmethod
    def check_azione(
        cls,
        user: Any,
        permission_codename: str,
        *,
        cache: dict[str, Any] | None = None,
    ) -> bool:
        """Scopo: Verifica se un'azione di processo e' abilitata.
        Delega alla funzione SQL script.fn_check_azione_processo."""
        def _query() -> bool:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT script.fn_check_azione_processo(%s, %s)",
                    [user.id, permission_codename],
                )
                row = cursor.fetchone()
            return bool(row[0]) if row else False

        return _cached(cache, f"azione:{permission_codename}", _query)

    @classmethod
    def get_emittenti_ids(
        cls, user: Any, *, cache: dict[str, Any] | None = None
    ) -> list[int] | None:
        """Scopo: Restituisce gli ID emittenti fiscali autorizzati per l'utente.
        Restituisce None se l'utente non ha restrizioni (whitelist vuota = tutto)."""
        def _query() -> list[int] | None:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT script.fn_get_emittenti_scope(%s)", [user.id]
                )
                row = cursor.fetchone()
            # fn_get_emittenti_scope ritorna bigint[] o NULL
            if row and row[0]:
                return list(row[0])
            return None

        return _cached(cache, "emittenti_ids", _query)

    @classmethod
    def get_emittenti_sr_ids(
        cls, user: Any, *, cache: dict[str, Any] | None = None
    ) -> list[int] | None:
        """Scopo: Restituisce i soggetto_ruolo_id degli emittenti fiscali
        autorizzati per l'utente. Wrapper su fn_get_emittenti_scope_sr_ids.

        Le tabelle anagrafiche e vendite usano emittente_soggetto_ruolo_id
        (FK a soggetti_ruoli), non emittenti_fiscali.id, quindi serve
        questa mappatura. Usare questo metodo (NON get_emittenti_ids) per
        filtrare su emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id.

        Semantica: None = nessuna restrizione, [] = nessun accesso."""
        def _query() -> list[int] | None:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT script.fn_get_emittenti_scope_sr_ids(%s)",
                    [user.id],
                )
                row = cursor.fetchone()
            # fn_get_emittenti_scope_sr_ids ritorna bigint[] o NULL
            if row and row[0] is not None:
                return list(row[0])
            return None

        return _cached(cache, "emittenti_sr_ids", _query)

    @classmethod
    def get_emittente_for_user(
        cls, user: Any, *, cache: dict[str, Any] | None = None
    ) -> int | None:
        """Scopo: Risolve l'emittente fiscale 1-a-1 dell'utente (refactor
        operatore-emittenti). Wrapper Python su `script.fn_resolve_emittente_for_user`.

        Ritorna `emittenti_fiscali.id` (PK reale) se l'utente ha esattamente
        una riga in `config.user_emittenti_fiscali` (operatore o admin di
        emittente), altrimenti `None`:
          - admin globale (0 righe in `user_emittenti_fiscali`) → None
          - istanza "0 emittenti" (gestore = emittente) → None

        I chiamanti devono trattare il `None` in base al loro contesto.
        Per la creazione BA, il check di legittimità "admin globale +
        emittenti presenti" è demandato alla funzione SQL
        `script.fn_check_user_can_create_ba` e al trigger
        `anagrafiche.trgfn_billing_account_guard_admin_globale`.

        Vedi memoria progetto `feedback_emittente_pk_vs_soggetto_ruolo`:
        questa funzione ritorna **la PK reale `emittenti_fiscali.id`**,
        NON `soggetto_ruolo_id`.
        """
        def _query() -> int | None:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT script.fn_resolve_emittente_for_user(%s)",
                    [user.id],
                )
                row = cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else None

        return _cached(cache, "emittente_for_user", _query)

    @classmethod
    def get_area_schema_db(cls, app_label: str, model_name: str) -> str:
        """Scopo: Determina lo schema_db dell'area per un model.
        1. Controlla override in area_model_overrides
        2. Altrimenti usa app_label (che corrisponde allo schema)."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT af.schema_db
                  FROM config.area_model_overrides amo
                  JOIN config.aree_funzionali af ON af.id = amo.area_id
                 WHERE amo.app_label = %s AND amo.model_name = %s
                """,
                [app_label, model_name],
            )
            row = cursor.fetchone()
        return row[0] if row else app_label

    @classmethod
    def get_unita_organizzativa_id(
        cls, user: Any, cache: dict[str, Any] | None = None
    ) -> int | None:
        """Scopo: Risale alla unita' organizzativa dell'utente.

        Delega a `script.fn_get_uo_id_for_user` (PR1 §13.3.7). La
        catena `identita_digitali (OPERATORE) -> soggetti_ruoli ->
        risorse_umane` e' incapsulata nella funzione SQL, determinismo
        garantito via `ORDER BY ru.valido_dal DESC LIMIT 1`. Ritorna
        None per utenti non-operatore, senza RU attiva o inesistenti.
        """
        def _query() -> int | None:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT script.fn_get_uo_id_for_user(%s)",
                    [user.id],
                )
                row = cursor.fetchone()
            return row[0] if row and row[0] is not None else None

        return _cached(cache, "uo_id", _query)

    @classmethod
    def has_profilo_applicabile_per_area(
        cls,
        user: Any,
        area_schema_db: str,
        *,
        cache: dict[str, Any] | None = None,
    ) -> bool:
        """Scopo: Verifica se l'utente ha almeno un profilo applicabile
        con una configurazione esplicita per l'area (qualsiasi livello,
        incluso BLOCCATO).

        Usato per distinguere due casi di diniego nei messaggi di
        errore:
          * True  -> "BLOCCATO intenzionale" (profilo configurato ma
            nega la richiesta)
          * False -> "nessun profilo configurato" (manca anche solo
            una riga del profilo per quell'area — configurazione
            incompleta)

        Delega a `script.fn_get_profili_accesso_applicabili` che
        incapsula la catena multi-face (AD_HOC prio 1, PORTALE /
        REPARTO prio 2). La join con `profili_accesso_aree` verifica
        che almeno uno dei profili applicabili copra l'area
        richiesta. Sostituisce la vecchia
        `has_profilo_reparto_area` (SQL su `profili_reparto_aree` +
        `risorse_umane_auth_user`).
        """
        def _query() -> bool:
            with connection.cursor() as cursor:
                # Workaround ambiguita' overload §8.3 (debito DB):
                # la migration 20260420-11 crea sia la fn a 1 param sia
                # quella a 2 param con `DEFAULT NULL` per ruolo_applicativo.
                # Postgres con 1 arg matcha entrambe -> `function is not unique`.
                # Passiamo esplicitamente 2 arg con NULL::config.ruolo_applicativo
                # per agganciare univocamente la signature multi-veste
                # (comportamento identico al legacy: NULL = no filtro veste).
                # TODO(DB dev/db-tid): droppare la fn a 1 param e rimuovere
                # questo workaround.
                cursor.execute(
                    """
                    SELECT EXISTS(
                        SELECT 1
                          FROM script.fn_get_profili_accesso_applicabili(
                                   %s, NULL::config.ruolo_applicativo
                               ) prof
                          JOIN config.profili_accesso_aree paa
                            ON paa.profilo_accesso_id = prof.profilo_accesso_id
                          JOIN config.aree_funzionali af
                            ON af.id = paa.area_id
                         WHERE af.schema_db = %s
                    )
                    """,
                    [user.id, area_schema_db],
                )
                row = cursor.fetchone()
            return bool(row[0]) if row else False

        return _cached(cache, f"has_profilo:{area_schema_db}", _query)
