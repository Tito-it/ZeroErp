# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Risolutore centrale permessi ZeroErp.
# Delega la catena di risoluzione alle funzioni SQL script.fn_*
# e mantiene cache per-request (dict) per evitare roundtrip duplicati.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any, Callable, TypeVar

from django.db import connection

from apps.core.services.auth_constants import RUOLO_APPLICATIVO_OPERATORE

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
        finestra temporale scaduta (fail-closed). Source of truth
        unica per il privilegio admin (post Fase 7 amm-software).

        §8.3.7 multi-face: la fn DB filtra esplicitamente per
        `ruolo_applicativo = 'OPERATORE'` (post migration 20260420-*).
        Un utente con identita CLIENTE_PORTALE / FORNITORE_PORTALE /
        SHOP_CUSTOMER + binding SUPER_ADMIN sulla stessa auth_user
        NON attiva il bypass: il privilegio e' legato alla "veste"
        OPERATORE, non all'auth_user. Enforcement centralizzato lato
        DB — il wrapper Python non duplica la logica. Il contratto
        cross-veste e' verificato da pgTAP su
        `db/pgtap/script/test-fn-is-super-admin*.sql` (single source of
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
        """Scopo: Restituisce il ruolo_applicativo della SESSIONE corrente.

        ⛔ Risponde per chi fa la richiesta, NON per `user` (S-6,
        2026-09-27): la GUC e' della sessione, e una credenziale puo' avere
        piu' vesti, quindi «il» ruolo applicativo di un altro utente non
        esiste. `user` deve essere l'utente della richiesta. Per chiedere
        qualcosa di un ALTRO utente si usa la domanda precisa
        (`has_veste_operatore_attiva`), come fa permessi-effettivi.

        Strategia GUC-first (Q1): se `app.ruolo_applicativo` e'
        popolato (JwtAuditAuthentication lo ha gia' propagato per la
        request corrente), ritorna quel valore senza query DB. In
        assenza di GUC (scenari di test che non passano dalla auth
        class, management command, chiamate non-HTTP), fallback a
        query su `anagrafiche.identita_digitali` filtrata sulle vesti
        UTILIZZABILI oggi: la stessa regola con cui `set_jwt_gucs` popola
        la GUC, letta dal building block DB `script.fn_veste_utilizzabile`
        (brief-db-veste-utilizzabile). ⛔ Non `attivo = true`: con la GUC
        una veste scaduta non ha ruolo, e il fallback non deve dargliene
        uno. `ORDER BY id`: fra piu' vesti utilizzabili la piu' vecchia,
        come al login (`find_veste_utilizzabile_per_ruoli`).

        Ritorna None se l'utente non ha alcuna veste utilizzabile.
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
                       AND script.fn_veste_utilizzabile(id)
                     ORDER BY id
                     LIMIT 1
                    """,
                    [user.id],
                )
                row = cursor.fetchone()
            return str(row[0]) if row and row[0] else None

        return _cached(cache, "ruolo_applicativo", _query)

    @classmethod
    def has_veste_operatore_attiva(
        cls, user: Any, cache: dict[str, Any] | None = None
    ) -> bool:
        """Scopo: L'utente ha una veste OPERATORE attiva (e nella finestra)?

        E' il passo 1 della catena di `fn_resolve_livello_area` e
        `fn_resolve_livello_oggetto`: senza, ogni area e' BLOCCATO. Livelli
        d'area, livelli oggetto e super admin esistono SOLO per la veste
        OPERATORE; le altre vesti passano dalla porta, non dalle aree.
        Delega a `script.fn_has_identita_attiva` (stessa lettura della
        catena): risponde per `user`, qualunque sia la sessione.
        """
        def _query() -> bool:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT script.fn_has_identita_attiva(%s, %s::config.ruolo_applicativo)",
                    [user.id, RUOLO_APPLICATIVO_OPERATORE],
                )
                row = cursor.fetchone()
            return bool(row[0]) if row else False

        return _cached(cache, "veste_operatore_attiva", _query)

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
    def get_emittenti_sr_ids(
        cls, user: Any, *, cache: dict[str, Any] | None = None
    ) -> list[int] | None:
        """Scopo: Restituisce i soggetto_ruolo_id degli emittenti fiscali
        autorizzati per l'utente. Wrapper su fn_get_emittenti_scope_sr_ids.

        **Quando usare**: query che filtrano su colonne <ruolo>_soggetto_ruolo_id
        (BA scope via emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id,
        search universale, lista clienti, fatture/ordini/lotti/listini con
        emittente_soggetto_ruolo_id). Per filtri su PK reale (emittenti_fiscali.id,
        vw_preventivi_list.emittente_fiscale_id, ecc.) usare `get_emittenti_pk_ids`.

        Vedi guida `soggetti-e-ruoli-anagrafici §5b` per il pattern duale SR vs PK
        e memoria `feedback_emittente_pk_vs_soggetto_ruolo`.

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
    def get_emittenti_pk_ids(
        cls, user: Any, *, cache: dict[str, Any] | None = None
    ) -> list[int] | None:
        """Scopo: Restituisce le PK reali (emittenti_fiscali.id) autorizzate
        per l'utente. Wrapper su fn_get_emittenti_scope_pk_ids (canonica nuova,
        2026-05-02).

        **Quando usare**: query che filtrano su colonne PK
        (vw_preventivi_list.emittente_fiscale_id, vendite.preventivi.emittente_fiscale_id
        post brief rev2, parameter_overrides.emittente_fiscale_id,
        user_emittenti_fiscali.emittente_fiscale_id, ecc.). Per filtri su SR id
        (<ruolo>_soggetto_ruolo_id) usare `get_emittenti_sr_ids`.

        Guard completi, come `_sr_ids`: nessuna identita OPERATORE attiva →
        `'{}'` (nessun accesso); super admin → NULL (nessuna restrizione).
        ⛔ Fino al 2026-09-12 esisteva l'alias `get_emittenti_ids`, dichiarato
        DEPRECATO dal 2026-05-02 e con NOVE chiamanti vivi — piu' dell'
        originale: un nome deprecato che non cala e' un nome in servizio
        (analisi-software-per-dati-morti §2.7). Rinominati i chiamanti, alias
        tolto: il presidio e' il grep a zero. *(La legacy
        `script.fn_get_emittenti_scope`, senza guard, e' stata droppata dal DB
        il 2026-08-18, `20260818-66`.)*

        Vedi guida `soggetti-e-ruoli-anagrafici §5b` per il pattern duale SR vs PK
        e memoria `feedback_emittente_pk_vs_soggetto_ruolo`.

        Semantica: None = nessuna restrizione, [] = nessun accesso."""
        def _query() -> list[int] | None:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT script.fn_get_emittenti_scope_pk_ids(%s)",
                    [user.id],
                )
                row = cursor.fetchone()
            if row and row[0] is not None:
                return list(row[0])
            return None

        return _cached(cache, "emittenti_pk_ids", _query)

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
    def list_model_overrides_grouped(cls) -> dict[str, list[dict[str, str]]]:
        """Scopo: Restituisce tutti i model configurabili raggruppati per schema_db.
        Usato da permessi-effettivi per mostrare il livello oggetto per area.

        ⚠️ Solo i NON riservati (`area_model_overrides.riservato`, dal
        2026-09-28): i dieci oggetti del kernel stanno a catalogo per essere
        dichiarati, non per essere personalizzati — senza il filtro la pagina
        li mostrerebbe come oggetti della loro area."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT af.schema_db, amo.app_label, amo.model_name
                  FROM config.area_model_overrides amo
                  JOIN config.aree_funzionali af ON af.id = amo.area_id
                 WHERE NOT amo.riservato
                 ORDER BY af.schema_db, amo.model_name
                """
            )
            rows = cursor.fetchall()
        result: dict[str, list[dict[str, str]]] = {}
        for schema_db, app_label, model_name in rows:
            result.setdefault(schema_db, []).append(
                {"app_label": app_label, "model_name": model_name}
            )
        return result

    @classmethod
    def get_area_schema_db(cls, app_label: str, model_name: str) -> str:
        """Scopo: Determina lo schema_db dell'area per un model: l'eccezione
        di `area_model_overrides`, altrimenti `app_label` (area = schema).

        ⛔ La regola e' di `script.fn_area_di_oggetto`, la stessa che usa il
        guard dei verbi (`fn_guard_livello`): fino al 2026-09-25 qui c'era la
        stessa query riscritta, cioe' una seconda sede della regola
        (brief-db-pannello-config-verbo-generico §6)."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT script.fn_area_di_oggetto(%s, %s)",
                [app_label, model_name],
            )
            row = cursor.fetchone()
        return row[0] if row and row[0] else app_label

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

        Delega a `script.fn_get_permessi_ereditati_aree`, la stessa
        funzione che fa il passo 4 di `fn_resolve_livello_area`: un'area
        e' «configurata» esattamente quando il resolver la trova nel
        profilo. Include le righe a `BLOCCATO`, che sono una scelta del
        profilo e non una sua assenza.

        ⛔ Conta i soli profili della veste OPERATORE (D-1,
        brief-db-pgtap-permessi-ereditati): un operatore che ha anche una
        veste cliente non si porta il profilo PORTALE di quella veste.
        La veste e' fissata nella funzione, non letta dalla GUC di chi
        chiama: i due caller sono di contesto operatore
          - permissions.py: gia' gated da ruolo_app == OPERATORE
          - views.py: ispeziona target_user; filtrare sulla GUC
            dell'admin corrente sarebbe semanticamente errato.
        """
        def _query() -> bool:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT EXISTS(
                        SELECT 1
                          FROM script.fn_get_permessi_ereditati_aree(%s) e
                          JOIN config.aree_funzionali af
                            ON af.id = e.area_id
                         WHERE af.schema_db = %s
                    )
                    """,
                    [user.id, area_schema_db],
                )
                row = cursor.fetchone()
            return bool(row[0]) if row else False

        return _cached(cache, f"has_profilo:{area_schema_db}", _query)
