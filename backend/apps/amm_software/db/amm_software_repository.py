# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per accesso DB del modulo amministrazione.
# Gestisce query operatori, override permessi e profili reparto.
# ------------------------------------------------------------

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any, ClassVar

from django.db import DatabaseError, connection, transaction

from apps.core.db._helpers import row_to_dict, rows_to_list, sql_order_direction

from apps.core.services.auth_constants import TIPO_PROFILO_SUPER_ADMIN
from apps.core.services.error_manager import ErrorManager
from apps.amm_software.constants import DEFAULT_LIMIT
from apps.amm_software.types import OperatoreDetailRow, OperatoreRow

# Colonne ammesse per ordinamento lista operatori. Niente piu' "ruolo_sistema":
# il campo legacy non e' esposto. Per ordinare per stato amministrativo si usa
# `is_super_admin` o `ruolo_applicativo`.
ALLOWED_ORDER_COLUMNS = frozenset({
    "last_name", "soggetto_cognome", "username", "is_super_admin",
    "ruolo_applicativo", "is_active", "unita_organizzativa_nome",
    "valido_dal", "valido_al",
})


# Fase 8 — Model riservati: non possono essere target di override granulari.
# Sono il kernel del sistema permessi: ammettere override a livello model
# qui aprirebbe scenari di lockout ricorsivo (es. negare a un admin
# l'accesso a `profili_accesso_bindings` => non puo' piu' rimuovere il
# proprio binding => bypass automatico).
#
# Convenzione tuple: `(schema_db, model_logical_name)` — stessa del seed
# `config.area_model_overrides` (es. `('anagrafiche', 'soggetto')`).
# NOTA: alla data del 2026-04-29 NESSUN model di kernel e' presente in
# `area_model_overrides` (verifica: il seed `20260410-11` registra solo
# 12 model business). Questa blacklist e' quindi PREVENTIVA — defense
# in depth contro futuri seed che includessero per errore tabelle di
# kernel. Se la convenzione di registrazione cambia (es. uso di
# Django app_label invece dello schema), aggiornare le tuple di
# conseguenza.
_MODEL_OVERRIDE_RISERVATI: frozenset[tuple[str, str]] = frozenset({
    # Identita digitali (anagrafiche) — modificarla via override-oggetti
    # lascerebbe l'utente bypassare i guard sul ruolo applicativo.
    ("anagrafiche", "identita_digitali"),
    # Catalogo profili accesso e binding SUPER_ADMIN.
    ("config", "profili_accesso"),
    ("config", "profili_accesso_bindings"),
    # Catalogo del lookup stesso: override-abile solo via DDL.
    ("config", "area_model_overrides"),
    # Tabelle override granulari: ricorsione semantica.
    ("config", "user_override_aree"),
    ("config", "user_override_azioni"),
    ("config", "user_override_oggetti"),
    # Scope emittenti utente: cambiarlo cambia i dati visibili.
    ("config", "user_emittenti_fiscali"),
    # Profili accesso: livello sopra ai singoli operatori (modello generalizzato
    # post-cutover PR-B; le legacy profili_reparto_* sono state rimosse).
    ("config", "profili_accesso_aree"),
    ("config", "profili_accesso_azioni"),
})


class AmmSoftwareRepository:
    """Accesso DB per amministrazione operatori e reparti."""

    # Scopo: Restituisce la lista paginata degli operatori con filtri opzionali.
    # JOIN: auth_user + identita_digitali (OPERATORE) + soggetti_ruoli +
    # risorse_umane + unita_organizzative. Il modello identitario e' multi-face:
    # `is_super_admin` da `script.fn_is_super_admin`, `ruolo_applicativo` da
    # `identita_digitali`, `is_active` da `auth_user`. Niente piu' enum
    # legacy `config.ruolo_sistema` esposto in output (Fase 7).
    # Risultato: (lista righe, conteggio totale).
    def list_operatori(
        self,
        *,
        search: str | None = None,
        is_super_admin: bool | None = None,
        unita_organizzativa_id: int | None = None,
        is_active: bool | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> tuple[list[OperatoreRow], int]:
        # Validazione ordinamento
        if order_by and order_by not in ALLOWED_ORDER_COLUMNS:
            order_by = None
        if order_dir and order_dir.upper() not in ("ASC", "DESC"):
            order_dir = None

        conditions: list[str] = []
        params: list[Any] = []

        if search:
            conditions.append(
                "(au.username ILIKE %s OR au.email ILIKE %s "
                "OR s.cognome ILIKE %s OR s.nome ILIKE %s "
                "OR s.ragione_sociale_completa ILIKE %s)"
            )
            like_term = f"%{search}%"
            params.extend([like_term] * 5)

        if is_super_admin is not None:
            # Multi-face auth: filtro binario sul binding SUPER_ADMIN.
            # Ortogonale a is_active. Delega a script.fn_is_super_admin.
            conditions.append("script.fn_is_super_admin(au.id) = %s")
            params.append(is_super_admin)

        if unita_organizzativa_id is not None:
            conditions.append("ru.unita_organizzativa_id = %s")
            params.append(unita_organizzativa_id)

        if is_active is not None:
            conditions.append("au.is_active = %s")
            params.append(is_active)

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        # Ordinamento sicuro (whitelist)
        if order_by and order_by in ALLOWED_ORDER_COLUMNS:
            direction = sql_order_direction(order_dir)
            order_clause = f"ORDER BY {order_by} {direction}, au.id"
        else:
            order_clause = "ORDER BY soggetto_cognome ASC, au.username ASC, au.id"

        sql = f"""
            SELECT au.id AS auth_user_id,
                   au.username,
                   au.email,
                   au.first_name,
                   au.last_name,
                   COALESCE(s.cognome, au.last_name) AS soggetto_cognome,
                   COALESCE(s.nome, au.first_name) AS soggetto_nome,
                   script.fn_is_super_admin(au.id) AS is_super_admin,
                   id.ruolo_applicativo::text AS ruolo_applicativo,
                   au.is_active,
                   ru.unita_organizzativa_id,
                   uo.descrizione AS unita_organizzativa_nome,
                   ru.id AS risorsa_umana_id,
                   ru.attivo,
                   ru.valido_dal::text,
                   ru.valido_al::text,
                   (SELECT string_agg(COALESCE(s_ef.ragione_sociale_completa, ef.descrizione), ', '
                                      ORDER BY COALESCE(s_ef.ragione_sociale_completa, ef.descrizione))
                      FROM config.user_emittenti_fiscali uef
                      JOIN anagrafiche.emittenti_fiscali ef ON ef.id = uef.emittente_fiscale_id
                      LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON sr_ef.id = ef.soggetto_ruolo_id
                      LEFT JOIN anagrafiche.soggetti s_ef ON s_ef.id = sr_ef.soggetto_id
                     WHERE uef.auth_user_id = au.id
                   ) AS emittenti_descrizione,
                   COUNT(*) OVER() AS total_count
              FROM auth_user au
              LEFT JOIN anagrafiche.identita_digitali id
                ON id.auth_user_id = au.id
               AND id.ruolo_applicativo = 'OPERATORE'
              LEFT JOIN anagrafiche.soggetti_ruoli sr
                ON sr.id = id.soggetto_ruolo_id
              LEFT JOIN anagrafiche.risorse_umane ru
                ON ru.soggetto_ruolo_id = sr.id
              LEFT JOIN anagrafiche.soggetti s
                ON s.id = sr.soggetto_id
              LEFT JOIN config.unita_organizzative uo
                ON uo.id = ru.unita_organizzativa_id
             WHERE {where_clause}
             {order_clause}
             LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            if not cursor.description:
                return [], 0
            cols = [c.name for c in cursor.description]
            rows = cursor.fetchall()

        if not rows:
            return [], 0

        total_count = rows[0][cols.index("total_count")]
        results: list[OperatoreRow] = []
        for row in rows:
            d = dict(zip(cols, row))
            d.pop("total_count", None)
            results.append(d)  # type: ignore[arg-type]

        return results, total_count

    # Scopo: Restituisce il dettaglio completo di un operatore con conteggi
    # override e i 6 campi capability (can_invite/disable/demote + reason).
    #
    # Delega interamente a `script.fn_get_operatore_detail(p_auth_user_id)`
    # (Fase 1 multi-face): la fn DB e' single source of truth per la
    # composizione del dettaglio. Lo SQL inline precedente e' eliminato per
    # evitare drift tra Python e regole DB.
    #
    # Semantica lookup-by-id: la fn ritorna 0 righe per id NULL/<=0/inesistenti
    # (idioma standard per i lookup; diverge dalla regola AGENTS "guard
    # NULL/<=0" volutamente — i chiamanti gestiscono `None` come "non
    # trovato"). I 3 service consumer (`get_operatore`, `update_operatore`,
    # `disabilita_operatore`, `riattiva_operatore`) trasformano None in
    # E_AMM_OPERATORE_NOT_FOUND quando rilevante.
    #
    # GUC awareness: la fn DB usa `script.fn_is_super_admin` che e' gated
    # su `app.ruolo_applicativo` (post 2026-04-21) e ritorna false per
    # contesti non-OPERATORE (portale/shop). Questo repo e' richiamato solo
    # da `AdminAPIView` (drawer admin-only), quindi il contesto e' sempre
    # OPERATORE. Se in futuro la fn fosse esposta altrove, la GUC va
    # garantita prima della chiamata.
    def get_operatore_detail(self, auth_user_id: int) -> OperatoreDetailRow | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM script.fn_get_operatore_detail(%s)",
                [auth_user_id],
            )
            if not cursor.description:
                return None
            cols = [c.name for c in cursor.description]
            row = cursor.fetchone()

        if not row:
            return None

        return dict(zip(cols, row))  # type: ignore[return-value]

    # Scopo: Aggiorna stato identita_digitali (attivo, ruolo_applicativo) per
    # l'utente. Helper privato per orchestrare le 3 write path dei writer
    # (update/disabilita/riattiva). La UNIQUE su auth_user_id garantisce
    # una sola identita per utente.
    def _set_identita_state(
        self,
        auth_user_id: int,
        *,
        attivo: bool | None = None,
        ruolo_applicativo: str | None = None,
    ) -> None:
        fields: list[str] = []
        params: list[Any] = []
        if attivo is not None:
            fields.append("attivo = %s")
            params.append(attivo)
        if ruolo_applicativo is not None:
            fields.append("ruolo_applicativo = %s::config.ruolo_applicativo")
            params.append(ruolo_applicativo)
        if not fields:
            return
        params.append(auth_user_id)
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE anagrafiche.identita_digitali "
                f"SET {', '.join(fields)} "
                f"WHERE auth_user_id = %s",
                params,
            )

    # Scopo: Aggiunge o rimuove il binding SUPER_ADMIN sull'identita
    # digitale dell'utente. Singola query atomica (no race SELECT+WRITE,
    # no-op se l'utente non ha identita). Il guard DB
    # `trgfn_profili_accesso_bindings_guard_ultimo_super_admin` blocca
    # la rimozione dell'ultimo binding attivo (lockout prevention).
    def _set_super_admin_binding(
        self, auth_user_id: int, *, enabled: bool
    ) -> None:
        with connection.cursor() as cursor:
            if enabled:
                cursor.execute(
                    """INSERT INTO config.profili_accesso_bindings
                          (profilo_accesso_id, identita_digitale_id)
                       SELECT pa.id, id.id
                         FROM config.profili_accesso pa
                        CROSS JOIN anagrafiche.identita_digitali id
                        WHERE pa.tipo = %s::config.tipo_profilo_accesso
                          AND id.auth_user_id = %s
                       ON CONFLICT DO NOTHING""",
                    [TIPO_PROFILO_SUPER_ADMIN, auth_user_id],
                )
            else:
                cursor.execute(
                    """DELETE FROM config.profili_accesso_bindings pab
                        USING anagrafiche.identita_digitali id,
                              config.profili_accesso pa
                        WHERE pab.identita_digitale_id = id.id
                          AND pab.profilo_accesso_id  = pa.id
                          AND pa.tipo = %s::config.tipo_profilo_accesso
                          AND id.auth_user_id = %s""",
                    [TIPO_PROFILO_SUPER_ADMIN, auth_user_id],
                )

    # Scopo: Aggiorna i campi modificabili di un operatore (auth_user +
    # identita_digitali + bindings SUPER_ADMIN + risorse_umane).
    # Dopo la modifica, il chiamante deve invalidare la cache permessi.
    # Transazione atomica: i 4-5 step devono succedere insieme o
    # nessuno (nessuno stato parziale inconsistente).
    #
    # Contract Fase 7 multi-face — solo campi nuovi:
    #   - `is_super_admin=True`  -> binding SUPER_ADMIN UPSERT (identita
    #                               OPERATORE attiva)
    #   - `is_super_admin=False` -> binding SUPER_ADMIN DELETE (identita
    #                               OPERATORE attiva)
    #   - `attivo=False`         -> identita_digitali.attivo=False +
    #                               ruolo_applicativo=DISABILITATO
    #   - `attivo=True`          -> identita_digitali.attivo=True +
    #                               ruolo_applicativo=OPERATORE
    # `is_super_admin` e `attivo` sono ortogonali e indipendenti.
    def update_operatore(
        self,
        auth_user_id: int,
        *,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        is_super_admin: bool | None = None,
        unita_organizzativa_id: int | None = None,
        attivo: bool | None = None,
        valido_al: str | None = None,
    ) -> None:
        with transaction.atomic():
            # 1) Aggiorna auth_user (name/email)
            auth_fields: list[str] = []
            auth_params: list[Any] = []
            if email is not None:
                auth_fields.append("email = %s")
                auth_params.append(email)
            if first_name is not None:
                auth_fields.append("first_name = %s")
                auth_params.append(first_name)
            if last_name is not None:
                auth_fields.append("last_name = %s")
                auth_params.append(last_name)

            if auth_fields:
                auth_params.append(auth_user_id)
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"UPDATE auth_user SET {', '.join(auth_fields)} WHERE id = %s",
                        auth_params,
                    )

            # 2) Stato identita_digitali pilotato da `attivo` (cambio
            #    simmetrico a disabilita/riattiva):
            #    attivo=True  -> ruolo_applicativo=OPERATORE attivo
            #    attivo=False -> ruolo_applicativo=DISABILITATO + attivo=false
            if attivo is True:
                self._set_identita_state(
                    auth_user_id, attivo=True, ruolo_applicativo="OPERATORE"
                )
            elif attivo is False:
                self._set_identita_state(
                    auth_user_id, attivo=False, ruolo_applicativo="DISABILITATO"
                )

            # 3) Binding SUPER_ADMIN (ortogonale ad `attivo`).
            if is_super_admin is True:
                self._set_super_admin_binding(auth_user_id, enabled=True)
            elif is_super_admin is False:
                self._set_super_admin_binding(auth_user_id, enabled=False)

            # 4) Aggiorna risorse_umane via catena identita -> soggetto_ruolo
            ru_fields: list[str] = []
            ru_params: list[Any] = []
            if attivo is not None:
                ru_fields.append("attivo = %s")
                ru_params.append(attivo)
            if unita_organizzativa_id is not None:
                ru_fields.append("unita_organizzativa_id = %s")
                ru_params.append(unita_organizzativa_id)
            if valido_al is not None:
                ru_fields.append("valido_al = %s::date")
                ru_params.append(valido_al)

            if ru_fields:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""UPDATE anagrafiche.risorse_umane ru
                               SET {', '.join(ru_fields)}
                              FROM anagrafiche.identita_digitali id
                             WHERE id.auth_user_id = %s
                               AND id.soggetto_ruolo_id = ru.soggetto_ruolo_id""",
                        ru_params + [auth_user_id],
                    )

            # 5) Sync auth_user.is_active se stato cambiato
            if attivo is not None or is_super_admin is not None:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT anagrafiche.fn_sync_auth_user_is_active(%s)",
                        [auth_user_id],
                    )

    # Scopo: Conta operatori con binding SUPER_ADMIN attivo.
    # Usato dal service per impedire la disabilitazione dell'ultimo admin
    # (guard a livello servizio; il guard DB equivalente e' il trigger
    # `trgfn_profili_accesso_bindings_guard_ultimo_super_admin`).
    def count_admin_attivi(self) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT COUNT(*)
                     FROM config.profili_accesso_bindings pab
                     JOIN config.profili_accesso pa
                       ON pa.id = pab.profilo_accesso_id
                     JOIN anagrafiche.identita_digitali id
                       ON id.id = pab.identita_digitale_id
                    WHERE pa.tipo = %s::config.tipo_profilo_accesso
                      AND pa.attivo = true
                      AND id.attivo = true
                      AND id.ruolo_applicativo <> 'DISABILITATO'""",
                [TIPO_PROFILO_SUPER_ADMIN],
            )
            return cursor.fetchone()[0]

    # Scopo: Disabilita un operatore. Post-cutover (§13.3.2) il framework
    # ATTIVO su risorse_umane valuta RUA.attivo come vista derivata da
    # identita_digitali.attivo, quindi l'ordine figlio→padre funziona
    # scrivendo su identita prima di RU. Transazione atomica per evitare
    # stato inconsistente se uno dei 3 step fallisce.
    def disabilita_operatore(self, auth_user_id: int) -> None:
        with transaction.atomic(), connection.cursor() as cursor:
            # 1. Disattiva identita_digitali + marca ruolo_applicativo
            #    DISABILITATO (signal esplicito, simmetrico a riattiva).
            cursor.execute(
                """UPDATE anagrafiche.identita_digitali
                      SET attivo = false,
                          ruolo_applicativo = 'DISABILITATO'::config.ruolo_applicativo
                    WHERE auth_user_id = %s""",
                [auth_user_id],
            )
            # 2. Disattiva risorse_umane (padre) + imposta valido_al = oggi
            cursor.execute(
                """UPDATE anagrafiche.risorse_umane ru
                      SET attivo = false,
                          valido_al = CURRENT_DATE
                     FROM anagrafiche.identita_digitali id
                    WHERE id.auth_user_id = %s
                      AND id.soggetto_ruolo_id = ru.soggetto_ruolo_id""",
                [auth_user_id],
            )
            # 3. Sync auth_user.is_active
            cursor.execute(
                "SELECT anagrafiche.fn_sync_auth_user_is_active(%s)",
                [auth_user_id],
            )

    # Scopo: Riattiva un operatore precedentemente disabilitato. Ordine
    # inverso: padre→figlio per rispettare il framework ATTIVO
    # (un figlio attivo richiede padre attivo). Transazione atomica.
    def riattiva_operatore(self, auth_user_id: int) -> None:
        with transaction.atomic(), connection.cursor() as cursor:
            # 1. Riattiva risorse_umane (padre) + valido_dal=oggi, valido_al=NULL
            cursor.execute(
                """UPDATE anagrafiche.risorse_umane ru
                      SET attivo = true,
                          valido_dal = CURRENT_DATE,
                          valido_al = NULL
                     FROM anagrafiche.identita_digitali id
                    WHERE id.auth_user_id = %s
                      AND id.soggetto_ruolo_id = ru.soggetto_ruolo_id""",
                [auth_user_id],
            )
            # 2. Riattiva identita_digitali + ripristina ruolo_applicativo=OPERATORE
            #    (utente era DISABILITATO o inattivo)
            cursor.execute(
                """UPDATE anagrafiche.identita_digitali
                      SET attivo = true,
                          ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
                    WHERE auth_user_id = %s""",
                [auth_user_id],
            )
            # 3. Sync auth_user.is_active
            cursor.execute(
                "SELECT anagrafiche.fn_sync_auth_user_is_active(%s)",
                [auth_user_id],
            )

    # Scopo: Crea un operatore completo invocando l'orchestratore DB
    # `anagrafiche.fn_crea_operatore_v2`. Chiama i building block: fn_crea_auth_user,
    # fn_crea_soggetto_pf, fn_crea_risorsa_umana.
    # Parametri Sprint 3: comune_nascita_id, indirizzo_resid_dettaglio_id,
    # indirizzo_domfisc_dettaglio_id (normalizzati via stradario).
    # Due flussi: soggetto_id NULL (crea soggetto nuovo) o valorizzato (usa esistente).
    #
    # Contract multi-face puro (Fase 7-DB step 6): la fn DB v2 accetta
    # `p_is_super_admin bool` + `p_attivo bool` al posto del legacy
    # `p_ruolo_sistema config.ruolo_sistema`. Il translator interno e'
    # stato rimosso. Compat layer DB legacy chiuso.
    # Ritorna l'auth_user_id del nuovo operatore.
    def crea_operatore(
        self,
        *,
        username: str,
        email: str,
        password_hash: str,
        qualifica_id: int,
        soggetto_id: str | None = None,
        cognome: str | None = None,
        nome: str | None = None,
        codice_fiscale: str | None = None,
        unita_organizzativa_id: int | None = None,
        data_nascita: str | None = None,
        sesso: str = "M",
        is_super_admin: bool = False,
        attivo: bool = True,
        valido_dal: str | None = None,
        valido_al: str | None = None,
        comune_nascita_id: int | None = None,
        indirizzo_resid_dettaglio_id: int | None = None,
        indirizzo_domfisc_dettaglio_id: int | None = None,
    ) -> int:
        sql = """
            SELECT anagrafiche.fn_crea_operatore_v2(
                p_soggetto_id                    := %s::uuid,
                p_cognome                        := %s,
                p_nome                           := %s,
                p_codice_fiscale                 := %s,
                p_username                       := %s,
                p_email                          := %s,
                p_password_hash                  := %s,
                p_qualifica_id                   := %s,
                p_unita_organizzativa_id         := %s,
                p_data_nascita                   := %s::date,
                p_sesso                          := %s,
                p_is_super_admin                 := %s,
                p_attivo                         := %s,
                p_valido_dal                     := COALESCE(%s::date, CURRENT_DATE),
                p_valido_al                      := %s::date,
                p_comune_nascita_id              := %s,
                p_indirizzo_resid_dettaglio_id   := %s,
                p_indirizzo_domfisc_dettaglio_id := %s
            )
        """
        params = [
            soggetto_id,
            cognome, nome, codice_fiscale,
            username, email, password_hash,
            qualifica_id, unita_organizzativa_id,
            data_nascita, sesso, is_super_admin, attivo,
            valido_dal, valido_al,
            comune_nascita_id,
            indirizzo_resid_dettaglio_id,
            indirizzo_domfisc_dettaglio_id,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
            assert row is not None
            return row[0]

    # Scopo: Lista unita' organizzative per dropdown filtro.
    def list_unita_organizzative(self) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, descrizione, parent_id
                     FROM config.unita_organizzative
                    ORDER BY descrizione"""
            )
            return rows_to_list(cursor)

    # ================================================================== #
    # Override aree per operatore                                           #
    # ================================================================== #

    # Scopo: Restituisce gli override aree per un operatore con nome area.
    def get_override_aree(self, auth_user_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT uoa.id, uoa.area_id, af.codice AS area_codice,
                   af.descrizione AS area_descrizione,
                   uoa.livello::text, uoa.motivo,
                   uoa.valido_dal::text, uoa.valido_al::text
              FROM config.user_override_aree uoa
              JOIN config.aree_funzionali af ON af.id = uoa.area_id
             WHERE uoa.auth_user_id = %s
             ORDER BY af.ordinamento, af.codice
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id])
            return rows_to_list(cursor)

    # Scopo: Sostituisce gli override aree di un operatore (replace semantics).
    # Cancella tutti gli override esistenti e inserisce i nuovi.
    def put_override_aree(self, auth_user_id: int, items: list[dict[str, Any]]) -> None:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM config.user_override_aree WHERE auth_user_id = %s",
                [auth_user_id],
            )
            for item in items:
                cursor.execute(
                    """INSERT INTO config.user_override_aree
                       (auth_user_id, area_id, livello, motivo, valido_dal, valido_al)
                       VALUES (%s, %s, %s::config.livello_accesso, %s, %s::date, %s::date)""",
                    [
                        auth_user_id,
                        item["area_id"],
                        item["livello"],
                        item.get("motivo"),
                        item.get("valido_dal"),
                        item.get("valido_al"),
                    ],
                )

    # ================================================================== #
    # Override azioni per operatore                                         #
    # ================================================================== #

    # Scopo: Restituisce gli override azioni per un operatore con descrizione azione.
    def get_override_azioni(self, auth_user_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT uoz.id, uoz.azione_id, ap.permission_codename,
                   ap.descrizione AS azione_descrizione,
                   af.codice AS area_codice,
                   uoz.abilitata, uoz.motivo,
                   uoz.valido_dal::text, uoz.valido_al::text
              FROM config.user_override_azioni uoz
              JOIN config.azioni_processo ap ON ap.id = uoz.azione_id
              JOIN config.aree_funzionali af ON af.id = ap.area_id
             WHERE uoz.auth_user_id = %s
             ORDER BY af.ordinamento, ap.permission_codename
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id])
            return rows_to_list(cursor)

    # Scopo: Sostituisce gli override azioni di un operatore (replace semantics).
    def put_override_azioni(self, auth_user_id: int, items: list[dict[str, Any]]) -> None:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM config.user_override_azioni WHERE auth_user_id = %s",
                [auth_user_id],
            )
            for item in items:
                cursor.execute(
                    """INSERT INTO config.user_override_azioni
                       (auth_user_id, azione_id, abilitata, motivo, valido_dal, valido_al)
                       VALUES (%s, %s, %s, %s, %s::date, %s::date)""",
                    [
                        auth_user_id,
                        item["azione_id"],
                        item["abilitata"],
                        item.get("motivo"),
                        item.get("valido_dal"),
                        item.get("valido_al"),
                    ],
                )

    # ================================================================== #
    # Override oggetti per operatore (v2 permessi)                         #
    # ================================================================== #

    # Scopo: Restituisce gli override oggetto di un operatore con info model e area.
    def get_override_oggetti(self, auth_user_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT uoo.id, uoo.app_label, uoo.model_name,
                   uoo.livello::text,
                   uoo.motivo,
                   uoo.valido_dal::text, uoo.valido_al::text,
                   amo.area_id,
                   af.descrizione AS area_descrizione
              FROM config.user_override_oggetti uoo
              LEFT JOIN config.area_model_overrides amo
                ON amo.app_label = uoo.app_label AND amo.model_name = uoo.model_name
              LEFT JOIN config.aree_funzionali af ON af.id = amo.area_id
             WHERE uoo.auth_user_id = %s
             ORDER BY af.descrizione, uoo.app_label, uoo.model_name
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id])
            return rows_to_list(cursor)

    # Scopo: Sostituisce gli override oggetto di un operatore (replace semantics).
    def put_override_oggetti(self, auth_user_id: int, items: list[dict[str, Any]]) -> None:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM config.user_override_oggetti WHERE auth_user_id = %s",
                [auth_user_id],
            )
            for item in items:
                cursor.execute(
                    """INSERT INTO config.user_override_oggetti
                       (auth_user_id, app_label, model_name, livello, motivo, valido_dal, valido_al)
                       VALUES (%s, %s, %s, %s::config.livello_accesso, %s, %s::date, %s::date)""",
                    [
                        auth_user_id,
                        item["app_label"],
                        item["model_name"],
                        item["livello"],
                        item.get("motivo"),
                        item.get("valido_dal"),
                        item.get("valido_al"),
                    ],
                )

    # Scopo: Lista model registrati in area_model_overrides (lookup per dropdown admin).
    #        Ogni riga e' arricchita con capability `can_override` (bool) +
    #        `reason` (chiave i18n|None) — Fase 8: i model che afferiscono al
    #        kernel del sistema permessi (auth_user, identita, bindings, override
    #        stessi) NON possono essere target di override per evitare lockout
    #        ricorsivi. Pattern simmetrico a `can_change_scope`/`change_scope_reason`
    #        di Fase 2.
    def list_model_overrides(self) -> list[dict[str, Any]]:
        sql = """
            SELECT amo.id, amo.app_label, amo.model_name,
                   af.schema_db AS area_schema, af.descrizione AS area_descrizione
              FROM config.area_model_overrides amo
              JOIN config.aree_funzionali af ON af.id = amo.area_id
             ORDER BY af.descrizione, amo.app_label, amo.model_name
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = rows_to_list(cursor)

        for row in rows:
            riservato = (row["app_label"], row["model_name"]) in _MODEL_OVERRIDE_RISERVATI
            row["can_override"] = not riservato
            row["reason"] = "amm.model_override_reason_riservato" if riservato else None
        return rows

    # ================================================================== #
    # Emittenti scope per operatore (Fase 2 multi-face)                     #
    # ================================================================== #

    # Scopo: Restituisce lo scope emittenti dichiarativo dell'operatore via
    # `script.fn_get_user_emittenti_scope`. La fn DB e' single source of truth
    # per:
    #   - scope_mode ('GLOBAL'|'SINGLE') derivato dal numero di righe in
    #     config.user_emittenti_fiscali (post Q2: max 1 riga per UNIQUE)
    #   - emittente_id + emittente_descrizione (NULL se GLOBAL)
    #   - allowed_scope_modes (sempre ['GLOBAL','SINGLE'] post Q2; MULTI
    #     architetturalmente chiuso)
    #   - can_change_scope: false sse l'operatore e' SA e l'unico attivo
    #     (delega a fn_check_ultimo_super_admin_attivo di Fase 1)
    #   - change_scope_reason: testo it-IT free-form, NULL se can=true
    #
    # Idioma lookup-by-id: 0 righe per p_auth_user_id non valido (None lato
    # Python), coerente con fn_get_operatore_detail. Il chiamante service
    # gestisce None come E_AMM_OPERATORE_NOT_FOUND quando rilevante.
    def get_user_emittenti_scope(self, auth_user_id: int) -> dict[str, Any] | None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM script.fn_get_user_emittenti_scope(%s)",
                [auth_user_id],
            )
            if not cursor.description:
                return None
            cols = [c.name for c in cursor.description]
            row = cursor.fetchone()
        if not row:
            return None
        return dict(zip(cols, row))

    # Scopo: Cambio scope emittenti atomico via
    # `script.fn_change_user_emittenti_scope(p_auth_user_id, p_emittente_ids)`.
    # La fn DB esegue in transazione:
    #   1. Validazione array_length IN (NULL|0|1) — altrimenti RAISE con
    #      marker E_AMM_VALIDAZIONE / E_AMM_SCOPE_NON_AMMESSO (no MULTI).
    #   2. Guard `fn_check_ultimo_super_admin_attivo` se SA -> RAISE
    #      E_PROFILO_ULTIMO_SUPER_ADMIN (riuso Fase 1).
    #   3. DELETE + INSERT condizionale.
    # Ritorna jsonb con lo stato post-change. Per il consumer Python ci
    # interessa solo l'esito (errori sollevati come DatabaseError gestiti
    # dal service); il return jsonb non viene proiettato perche' il service
    # rilegge tramite get_user_emittenti_scope per consistenza con il GET.
    def change_user_emittenti_scope(
        self, auth_user_id: int, emittente_ids: list[int]
    ) -> None:
        with connection.cursor() as cursor:
            # GLOBAL = array vuoto []; SINGLE = [id]. La fn DB Q2 valida
            # array_length <= 1 e solleva E_AMM_SCOPE_NON_AMMESSO altrimenti.
            cursor.execute(
                "SELECT script.fn_change_user_emittenti_scope(%s, %s::bigint[])",
                [auth_user_id, list(emittente_ids)],
            )

    # ================================================================== #
    # Reparti e profili                                                    #
    # ================================================================== #

    # Scopo: Lista reparti con flag profilo configurato e conteggio operatori.
    #        Conteggi su modello generalizzato profili_accesso_* via binding
    #        REPARTO (post-cutover PR-B): JOIN profili_accesso_bindings ->
    #        profili_accesso_aree/_azioni filtrato per unita_organizzativa_id.
    def list_reparti(self) -> list[dict[str, Any]]:
        sql = """
            SELECT uo.id, uo.codice, uo.descrizione, uo.attivo,
                   (SELECT COUNT(*)
                      FROM config.profili_accesso_bindings pab
                      JOIN config.profili_accesso_aree paa
                        ON paa.profilo_accesso_id = pab.profilo_accesso_id
                     WHERE pab.unita_organizzativa_id = uo.id) AS profilo_aree_count,
                   (SELECT COUNT(*)
                      FROM config.profili_accesso_bindings pab
                      JOIN config.profili_accesso_azioni paz
                        ON paz.profilo_accesso_id = pab.profilo_accesso_id
                     WHERE pab.unita_organizzativa_id = uo.id) AS profilo_azioni_count,
                   (SELECT COUNT(*) FROM anagrafiche.risorse_umane ru
                     WHERE ru.unita_organizzativa_id = uo.id
                       AND ru.attivo = true) AS operatori_count
              FROM config.unita_organizzative uo
             WHERE uo.attivo = true
             ORDER BY uo.descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return rows_to_list(cursor)

    # Scopo: Restituisce il profilo completo di un reparto (aree + azioni).
    #        Legge dal modello generalizzato profili_accesso_* via binding
    #        REPARTO. Contratto API invariato: {"aree": [...], "azioni": [...]}
    def get_profilo_reparto(self, uo_id: int) -> dict[str, Any]:
        # Aree
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT paa.id, paa.area_id, af.codice AS area_codice,
                          af.descrizione AS area_descrizione,
                          paa.livello::text
                     FROM config.profili_accesso_bindings pab
                     JOIN config.profili_accesso_aree paa
                       ON paa.profilo_accesso_id = pab.profilo_accesso_id
                     JOIN config.aree_funzionali af ON af.id = paa.area_id
                    WHERE pab.unita_organizzativa_id = %s
                    ORDER BY af.ordinamento, af.codice""",
                [uo_id],
            )
            cols_a = [c.name for c in cursor.description]
            aree = [dict(zip(cols_a, row)) for row in cursor.fetchall()]

        # Azioni
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT paz.id, paz.azione_id, ap.permission_codename,
                          ap.descrizione AS azione_descrizione,
                          af.codice AS area_codice,
                          paz.abilitata
                     FROM config.profili_accesso_bindings pab
                     JOIN config.profili_accesso_azioni paz
                       ON paz.profilo_accesso_id = pab.profilo_accesso_id
                     JOIN config.azioni_processo ap ON ap.id = paz.azione_id
                     JOIN config.aree_funzionali af ON af.id = ap.area_id
                    WHERE pab.unita_organizzativa_id = %s
                    ORDER BY af.ordinamento, ap.permission_codename""",
                [uo_id],
            )
            cols_z = [c.name for c in cursor.description]
            azioni = [dict(zip(cols_z, row)) for row in cursor.fetchall()]

        return {"aree": aree, "azioni": azioni}

    # Scopo: Sostituisce il profilo completo di un reparto (aree + azioni)
    #        scrivendo direttamente sul modello generalizzato profili_accesso_*
    #        (post-cutover PR-B). Operazione atomica:
    #          1. UPSERT profilo REPARTO (codice = 'REPARTO_' || codice_interno).
    #          2. UPSERT binding REPARTO -> profilo per uo_id (1:1, partial UQ).
    #          3. DELETE + INSERT su profili_accesso_aree per profilo_accesso_id.
    #          4. DELETE + INSERT su profili_accesso_azioni per profilo_accesso_id.
    #        Il fail-fast su uo_id inesistente solleva E_AMM_VALIDAZIONE prima
    #        di toccare qualunque tabella. Tutti gli operatori bindati al
    #        reparto ereditano le modifiche; la cache permessi e' invalidata
    #        dal service caller (`invalidate_department`).
    def put_profilo_reparto(
        self, uo_id: int, aree: list[dict[str, Any]], azioni: list[dict[str, Any]]
    ) -> None:
        with transaction.atomic(), connection.cursor() as cursor:
            # 1. Recupera codice/descrizione UO per derivare codice profilo.
            cursor.execute(
                "SELECT codice_interno, descrizione, attivo "
                "FROM config.unita_organizzative WHERE id = %s",
                [uo_id],
            )
            row = cursor.fetchone()
            if not row:
                ErrorManager.raise_error(
                    code="E_AMM_VALIDAZIONE",
                    message="Reparto inesistente.",
                    detail=f"unita_organizzativa_id={uo_id}",
                )
                raise  # unreachable, per type checker
            codice_interno, descrizione_uo, attivo_uo = row
            codice_profilo = f"REPARTO_{codice_interno}"

            # 2. UPSERT profilo accesso (tipo REPARTO). Idempotente sul codice.
            cursor.execute(
                """INSERT INTO config.profili_accesso (
                       tipo, codice, descrizione, attivo
                   )
                   VALUES ('REPARTO', %s, %s, %s)
                   ON CONFLICT ON CONSTRAINT uq_profili_accesso_codice
                   DO UPDATE SET descrizione = EXCLUDED.descrizione,
                                 attivo      = EXCLUDED.attivo
                   RETURNING id""",
                [codice_profilo, f"Profilo reparto {descrizione_uo}", attivo_uo],
            )
            profilo_id = cursor.fetchone()[0]

            # 3. UPSERT binding REPARTO -> profilo. UNIQUE parziale su
            #    unita_organizzativa_id IS NOT NULL: ON CONFLICT esplicita
            #    indice + predicato per consentire l'inferenza Postgres.
            cursor.execute(
                """INSERT INTO config.profili_accesso_bindings (
                       profilo_accesso_id, unita_organizzativa_id,
                       identita_digitale_id, ruolo_applicativo
                   )
                   VALUES (%s, %s, NULL, NULL)
                   ON CONFLICT (unita_organizzativa_id)
                       WHERE unita_organizzativa_id IS NOT NULL
                       DO UPDATE SET profilo_accesso_id = EXCLUDED.profilo_accesso_id""",
                [profilo_id, uo_id],
            )

            # 4. Aree: replace (filtrato per profilo_accesso_id).
            cursor.execute(
                "DELETE FROM config.profili_accesso_aree "
                "WHERE profilo_accesso_id = %s",
                [profilo_id],
            )
            for item in aree:
                cursor.execute(
                    """INSERT INTO config.profili_accesso_aree
                       (profilo_accesso_id, area_id, livello)
                       VALUES (%s, %s, %s::config.livello_accesso)""",
                    [profilo_id, item["area_id"], item["livello"]],
                )

            # 5. Azioni: replace.
            cursor.execute(
                "DELETE FROM config.profili_accesso_azioni "
                "WHERE profilo_accesso_id = %s",
                [profilo_id],
            )
            for item in azioni:
                cursor.execute(
                    """INSERT INTO config.profili_accesso_azioni
                       (profilo_accesso_id, azione_id, abilitata)
                       VALUES (%s, %s, %s)""",
                    [profilo_id, item["azione_id"], item["abilitata"]],
                )

    # ================================================================== #
    # Audit log globale permessi                                           #
    # ================================================================== #

    _OP_LABELS: dict[int, str] = {1: "INIZIALE", 2: "MODIFICA", 3: "ELIMINAZIONE"}

    # Colonne ammesse per ordinamento audit log (whitelist).
    _AUDIT_ORDER_COLUMNS: frozenset[str] = frozenset({
        "timestamp", "valid_from", "user_modifica", "user_insert",
        "tabella", "tipo_operazione",
    })

    # Scopo: Restituisce le sorgenti audit ammesse (Fase 5).
    #        Single source of truth lato DB: `script.vw_audit_sources` gia'
    #        filtrata `attivo=true` e ordinata per `code`. Sostituisce l'ex
    #        `_AUDIT_TABLES` hardcoded. La vista include 8 sorgenti (incluse
    #        `user_override_oggetti` permessi v2 e `identita_digitali`
    #        multi-face). Cardinalita' bassa, no paginazione.
    #
    #        Cache modulo-level via `lru_cache`: la vista cambia solo con
    #        migration (no mutazioni runtime), 8 righe immutabili durante
    #        il processo. Evita 2 round-trip DB per ogni `get_audit_summary`
    #        (validazione code + fn call). Test/hot-reload: `cache_clear()`.
    @staticmethod
    @lru_cache(maxsize=1)
    def _list_audit_sources_cached() -> tuple[tuple[str, str, str], ...]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT code, label_key, area_funzionale
                  FROM script.vw_audit_sources
                """
            )
            return tuple((r[0], r[1], r[2]) for r in cursor.fetchall())

    def list_audit_sources(self) -> list[dict[str, Any]]:
        return [
            {"code": code, "label_key": label_key, "area_funzionale": area}
            for code, label_key, area in self._list_audit_sources_cached()
        ]

    # Scopo: Calcola summary + diff per uno snapshot audit (Fase 5).
    #        Wrapper su `script.fn_audit_summary(p_audit_source_code, p_storico_id)`.
    #        Ritorna dict {"summary": "<N> modifiche", "diff": [{field, old, new}]}.
    #        Convenzione "snapshot mancante -> None": il fn DB solleva
    #        `E_AUDIT_SNAPSHOT_NON_TROVATO` come marker stabile; il repo lo
    #        traduce in None per coerenza con il pattern lookup-by-id (idiom
    #        `feedback_db_doc_first`). Il service mappa None ->
    #        ServiceError(E_AUDIT_SNAPSHOT_NON_TROVATO) preservando il code.
    #        Altri DatabaseError sono ri-sollevati (gestiti dal middleware).
    def get_audit_summary(self, code: str, storico_id: int) -> dict[str, Any] | None:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT script.fn_audit_summary(%s, %s) AS audit",
                    [code, storico_id],
                )
                row = cursor.fetchone()
        except DatabaseError as exc:
            if "E_AUDIT_SNAPSHOT_NON_TROVATO" in str(exc):
                return None
            raise
        if not row or row[0] is None:
            return None
        # Il driver Postgres ritorna jsonb come dict Python.
        return row[0]

    # Defensive: i `code` e `area_funzionale` arrivano da `script.vw_audit_sources`
    # (whitelist DB) ma vengono interpolati in f-string nella query
    # (`storico.{code}`, `fn_audit_summary('{code}', ...)`,
    # `'{area}' AS area_funzionale`). Se in futuro la vista esponesse valori
    # con caratteri inattesi (improbabile, ma mitigation lowcost), l'iniezione
    # SQL diventerebbe possibile. Le regex riflettono la convenzione naming:
    #   - code: nomi tabella PG snake_case lowercase
    #   - area: enum chiuso UPPERCASE (PERMESSI/AUTH/ANAGRAFICHE/...)
    _AUDIT_CODE_RE: ClassVar = re.compile(r"^[a-z_][a-z0-9_]*$")
    _AUDIT_AREA_RE: ClassVar = re.compile(r"^[A-Z][A-Z_]*$")

    # Scopo: Restituisce la timeline globale degli eventi audit permessi (Fase 5).
    # Paginata, filtri opzionali: data_da, data_a, tabella.
    #
    # Build dinamico delle UNION ALL dalla vista `script.vw_audit_sources`:
    # niente piu' lista hardcoded `_AUDIT_TABLES`. Quando il team DB aggiunge
    # una sorgente alla vista, l'audit log la vede automaticamente.
    #
    # Ogni branch UNION espone:
    #   - `code` (= label_key sorgente, era `tabella`),
    #   - `storico_id` = `s.id` (PK riga in storico.<tabella>, NECESSARIO per
    #     `fn_audit_summary` — l'id della riga sorgente non basta),
    #   - `area_funzionale` (5 valori: PERMESSI/AUTH/ANAGRAFICHE/EMITTENTI/FATTURAZIONE),
    #   - `summary` + `diff` calcolati inline via LATERAL `fn_audit_summary`
    #     (1 query, no N+1 sulle pagine).
    #
    # Whitelist `vw_audit_sources` controllata dal DB + regex paranoia
    # `_AUDIT_CODE_RE` per defense-in-depth.
    def list_audit_log(
        self,
        *,
        data_da: str | None = None,
        data_a: str | None = None,
        tabella: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        sources = self.list_audit_sources()
        if not sources:
            return [], 0

        unions: list[str] = []
        for src in sources:
            code = src["code"]
            area = src["area_funzionale"]
            if tabella and tabella != code:
                continue
            # Defensive: code/area arrivano da vw_audit_sources (whitelist DB)
            # ma sono interpolati in f-string. Regex check come safety net se
            # la vista esponesse mai un nome anomalo. Salta la sorgente: log
            # la dropperebbe silenziosamente, ma la vista e' under DB control.
            if not self._AUDIT_CODE_RE.match(code):
                continue
            if not self._AUDIT_AREA_RE.match(area):
                continue
            unions.append(
                f"SELECT '{code}' AS code, "
                f"'{area}' AS area_funzionale, "
                f"s.id AS storico_id, "
                f"s.valid_from, s.tipo_operazione, s.user_insert, "
                f"s.snapshot, "
                f"script.fn_audit_summary('{code}', s.id) AS audit "
                f"FROM storico.{code} s"  # noqa: S608
            )

        if not unions:
            return [], 0

        params: list[Any] = []
        sql = f"WITH events AS ({' UNION ALL '.join(unions)}) "  # noqa: S608
        sql += (
            "SELECT code, area_funzionale, storico_id, valid_from, "
            "tipo_operazione, user_insert, snapshot, audit, "
            "COUNT(*) OVER() AS total_count "
            "FROM events WHERE true "
        )

        if data_da:
            sql += "AND valid_from >= %s::timestamptz "
            params.append(data_da)
        if data_a:
            sql += "AND valid_from < (%s::date + INTERVAL '1 day') "
            params.append(data_a)

        # Ordinamento sicuro (whitelist). Il FE manda il nome campo come
        # appare nel risultato; mappiamo al nome colonna SQL.
        _col_map = {
            "timestamp": "valid_from",
            "user_modifica": "user_insert",
            "tabella": "code",
        }
        safe_col = _col_map.get(order_by, order_by) if order_by else None
        if safe_col and safe_col in self._AUDIT_ORDER_COLUMNS:
            direction = sql_order_direction(order_dir, default_desc=True)
            sql += f"ORDER BY {safe_col} {direction}, valid_from DESC "  # noqa: S608
        else:
            sql += "ORDER BY valid_from DESC "
        sql += "LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        if not rows:
            return [], 0

        total_count = rows[0][8]
        events = [
            {
                "code": row[0],
                # Manteniamo `tabella` come alias di `code` per retrocompat
                # con consumer FE legacy. Nuovi consumer usano `code`.
                "tabella": row[0],
                "area_funzionale": row[1],
                "storico_id": row[2],
                "timestamp": row[3].isoformat() if row[3] else None,
                "tipo_operazione": self._OP_LABELS.get(row[4], str(row[4])),
                "user_modifica": row[5],
                "snapshot": row[6],
                "audit": row[7],  # {"summary": "...", "diff": [...]}
            }
            for row in rows
        ]
        return events, total_count

    # ================================================================== #
    # Riepilogo permessi (matrice operatori × aree)                        #
    # ================================================================== #

    # Scopo: Restituisce la matrice permessi effettivi per tutti gli operatori attivi.
    # Ogni riga contiene dati operatore + una colonna per ogni area funzionale
    # con il livello effettivo (TUTTO/LETTURA/BLOCCATO) calcolato dalla funzione SQL.
    # Filtri opzionali: reparto, is_super_admin, emittente. Niente piu' enum
    # legacy `ruolo_sistema` (Fase 7).
    def get_permessi_riepilogo(
        self,
        *,
        unita_organizzativa_id: int | None = None,
        is_super_admin: bool | None = None,
        emittente_fiscale_id: int | None = None,
    ) -> dict[str, Any]:
        # 1. Recupera aree funzionali attive (per le colonne)
        aree = self.list_aree_funzionali()

        # 2. Query operatori attivi con livello effettivo per ogni area
        conditions: list[str] = ["au.is_active = true"]
        params: list[Any] = []

        if unita_organizzativa_id is not None:
            conditions.append("ru.unita_organizzativa_id = %s")
            params.append(unita_organizzativa_id)

        if is_super_admin is not None:
            conditions.append("script.fn_is_super_admin(au.id) = %s")
            params.append(is_super_admin)

        if emittente_fiscale_id is not None:
            conditions.append(
                "EXISTS (SELECT 1 FROM config.user_emittenti_fiscali uef"
                " WHERE uef.auth_user_id = au.id AND uef.emittente_fiscale_id = %s)"
            )
            params.append(emittente_fiscale_id)

        where_clause = " AND ".join(conditions)

        # Genera una subquery per ogni area funzionale.
        # `fn_resolve_livello_area` matcha sulla colonna IMMUTABILE
        # `aree_funzionali.schema_db` (chiave tecnica), NON sul `codice`
        # (etichetta mutabile rinominabile dall'utente): l'arg deve essere
        # `schema_db`. L'alias colonna resta su `codice` perche' il FE mappa le
        # colonne `area_<codice>` con la lista `aree` ricevuta in parallelo.
        # Entrambi validati come identificatori sicuri (solo alfanumerici +
        # underscore) per prevenire injection.
        _SAFE_IDENT = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
        area_columns = ", ".join(
            f"script.fn_resolve_livello_area(au.id, '{a['schema_db']}')::text AS area_{a['codice']}"
            for a in aree
            if _SAFE_IDENT.match(a['codice']) and _SAFE_IDENT.match(a['schema_db'])
        )

        sql = f"""
            SELECT au.id AS auth_user_id,
                   au.username,
                   COALESCE(s.cognome, au.last_name) AS cognome,
                   COALESCE(s.nome, au.first_name) AS nome,
                   script.fn_is_super_admin(au.id) AS is_super_admin,
                   id.ruolo_applicativo::text AS ruolo_applicativo,
                   au.is_active,
                   uo.descrizione AS reparto,
                   {area_columns}
              FROM auth_user au
              LEFT JOIN anagrafiche.identita_digitali id
                ON id.auth_user_id = au.id
               AND id.ruolo_applicativo = 'OPERATORE'
              LEFT JOIN anagrafiche.soggetti_ruoli sr
                ON sr.id = id.soggetto_ruolo_id
              LEFT JOIN anagrafiche.risorse_umane ru
                ON ru.soggetto_ruolo_id = sr.id
              LEFT JOIN anagrafiche.soggetti s
                ON s.id = sr.soggetto_id
              LEFT JOIN config.unita_organizzative uo
                ON uo.id = ru.unita_organizzativa_id
             WHERE {where_clause}
             ORDER BY COALESCE(s.cognome, au.last_name), au.username
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = rows_to_list(cursor)

        return {"aree": aree, "operatori": rows}

    # ================================================================== #
    # Lookup: aree funzionali e azioni processo                            #
    # ================================================================== #

    # Scopo: Lista aree funzionali attive per dropdown/selezione.
    def list_aree_funzionali(self) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, codice, codice_interno, schema_db, descrizione,
                          ordinamento
                     FROM config.aree_funzionali
                    WHERE attivo = true
                    ORDER BY ordinamento, codice"""
            )
            return rows_to_list(cursor)

    # Scopo: Lista azioni processo attive per dropdown/selezione.
    def list_azioni_processo(self) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT ap.id, ap.permission_codename, ap.descrizione,
                          ap.pericolosa, ap.area_id,
                          af.codice AS area_codice
                     FROM config.azioni_processo ap
                     JOIN config.aree_funzionali af ON af.id = ap.area_id
                    WHERE ap.attivo = true
                    ORDER BY af.ordinamento, ap.permission_codename"""
            )
            return rows_to_list(cursor)

    # Scopo: Lista emittenti fiscali per dropdown scope operatore.
    #        Espone ragione_sociale del soggetto associato via soggetto_ruolo_id.
    def list_emittenti_fiscali(self) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT ef.id, ef.codice, ef.descrizione,
                          ef.soggetto_ruolo_id,
                          s.ragione_sociale_completa AS ragione_sociale
                     FROM anagrafiche.emittenti_fiscali ef
                     LEFT JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id
                     LEFT JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
                    WHERE ef.attivo = true
                    ORDER BY s.ragione_sociale_completa, ef.descrizione"""
            )
            return rows_to_list(cursor)

    # Scopo: Wrapper script.fn_get_setup_status. Refactor operatore-emittenti
    # (decisione D1): conta emittenti attivi, operatori totali/assegnati/
    # admin globali/non assegnati per il banner UI "operatori non assegnati".
    def get_setup_status(self) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute("SELECT script.fn_get_setup_status()")
            row = cursor.fetchone()
        return row[0] if row else {}
