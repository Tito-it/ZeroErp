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
    def get_ruolo_sistema(
        cls, user: Any, cache: dict[str, Any] | None = None
    ) -> str | None:
        """Scopo: Restituisce il ruolo_sistema dell'utente dalla tabella ponte.
        Ritorna None se l'utente non ha un record in risorse_umane_auth_user."""
        def _query() -> str | None:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT script.fn_get_ruolo_sistema(%s)", [user.id]
                )
                row = cursor.fetchone()
            return row[0] if row else None

        return _cached(cache, "ruolo_sistema", _query)

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
        """Scopo: Risale alla unita' organizzativa dell'utente
        via bridge risorse_umane_auth_user -> risorse_umane."""
        def _query() -> int | None:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ru.unita_organizzativa_id
                      FROM anagrafiche.risorse_umane_auth_user rau
                      JOIN anagrafiche.risorse_umane ru
                        ON ru.id = rau.risorsa_umana_id
                     WHERE rau.auth_user_id = %s
                    """,
                    [user.id],
                )
                row = cursor.fetchone()
            return row[0] if row else None

        return _cached(cache, "uo_id", _query)

    @classmethod
    def has_profilo_reparto_area(
        cls,
        user: Any,
        area_schema_db: str,
        *,
        cache: dict[str, Any] | None = None,
    ) -> bool:
        """Scopo: Verifica se il reparto dell'utente ha un profilo per l'area.
        Usato per distinguere 'BLOCCATO da profilo' da 'nessun profilo configurato'."""
        def _query() -> bool:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT EXISTS(
                        SELECT 1
                          FROM config.profili_reparto_aree pra
                          JOIN config.aree_funzionali af ON af.id = pra.area_id
                          JOIN anagrafiche.risorse_umane_auth_user rau
                            ON rau.auth_user_id = %s
                          JOIN anagrafiche.risorse_umane ru
                            ON ru.id = rau.risorsa_umana_id
                         WHERE ru.unita_organizzativa_id = pra.unita_organizzativa_id
                           AND af.schema_db = %s
                    )
                    """,
                    [user.id, area_schema_db],
                )
                row = cursor.fetchone()
            return bool(row[0]) if row else False

        return _cached(cache, f"has_profilo:{area_schema_db}", _query)
