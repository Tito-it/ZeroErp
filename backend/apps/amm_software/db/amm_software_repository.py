# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Repository per accesso DB del modulo amministrazione.
# Gestisce query utenti, override permessi e profili reparto.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import connection

from apps.core.services.error_manager import ErrorManager
from apps.amm_software.types import UtenteDetailRow, UtenteRow

# Colonne ammesse per ordinamento lista utenti
ALLOWED_ORDER_COLUMNS = frozenset({
    "last_name", "username", "ruolo_sistema", "is_active",
    "unita_organizzativa_nome", "data_insert",
})


class AmmSoftwareRepository:
    """Accesso DB per amministrazione utenti e reparti."""

    # Scopo: Restituisce la lista paginata degli utenti con filtri opzionali.
    # JOIN: auth_user + risorse_umane_auth_user + risorse_umane + unita_organizzative.
    # Risultato: (lista righe, conteggio totale).
    def list_utenti(
        self,
        *,
        search: str | None = None,
        ruolo_sistema: str | None = None,
        unita_organizzativa_id: int | None = None,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> tuple[list[UtenteRow], int]:
        # Validazione ordinamento
        if order_by and order_by not in ALLOWED_ORDER_COLUMNS:
            order_by = None
        if order_dir and order_dir.upper() not in ("ASC", "DESC"):
            order_dir = None

        conditions: list[str] = []
        params: list[Any] = []

        if search:
            conditions.append(
                "(au.username ILIKE %s OR au.first_name ILIKE %s "
                "OR au.last_name ILIKE %s OR au.email ILIKE %s)"
            )
            like_term = f"%{search}%"
            params.extend([like_term, like_term, like_term, like_term])

        if ruolo_sistema:
            conditions.append("rua.ruolo_sistema = %s::config.ruolo_sistema")
            params.append(ruolo_sistema)

        if unita_organizzativa_id is not None:
            conditions.append("ru.unita_organizzativa_id = %s")
            params.append(unita_organizzativa_id)

        if is_active is not None:
            conditions.append("au.is_active = %s")
            params.append(is_active)

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        # Ordinamento sicuro (whitelist)
        if order_by and order_by in ALLOWED_ORDER_COLUMNS:
            direction = "DESC" if order_dir and order_dir.upper() == "DESC" else "ASC"
            order_clause = f"ORDER BY {order_by} {direction}, au.id"
        else:
            order_clause = "ORDER BY au.last_name ASC, au.username ASC, au.id"

        sql = f"""
            SELECT au.id AS auth_user_id,
                   au.username,
                   au.email,
                   au.first_name,
                   au.last_name,
                   rua.ruolo_sistema::text,
                   au.is_active,
                   ru.unita_organizzativa_id,
                   uo.descrizione AS unita_organizzativa_nome,
                   ru.id AS risorsa_umana_id,
                   ru.attivo,
                   ru.valido_al::text,
                   au.date_joined::text AS data_insert,
                   COUNT(*) OVER() AS total_count
              FROM auth_user au
              LEFT JOIN anagrafiche.risorse_umane_auth_user rua
                ON rua.auth_user_id = au.id
              LEFT JOIN anagrafiche.risorse_umane ru
                ON ru.id = rua.risorsa_umana_id
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
        results: list[UtenteRow] = []
        for row in rows:
            d = dict(zip(cols, row))
            d.pop("total_count", None)
            results.append(d)  # type: ignore[arg-type]

        return results, total_count

    # Scopo: Restituisce il dettaglio completo di un utente con conteggi override.
    def get_utente_detail(self, auth_user_id: int) -> UtenteDetailRow | None:
        sql = """
            SELECT au.id AS auth_user_id,
                   au.username,
                   au.email,
                   au.first_name,
                   au.last_name,
                   rua.ruolo_sistema::text,
                   au.is_active,
                   ru.unita_organizzativa_id,
                   uo.descrizione AS unita_organizzativa_nome,
                   ru.id AS risorsa_umana_id,
                   ru.attivo,
                   ru.valido_al::text,
                   au.date_joined::text AS data_insert,
                   COALESCE((SELECT COUNT(*) FROM config.user_override_aree uoa
                             WHERE uoa.auth_user_id = au.id), 0) AS override_aree_count,
                   COALESCE((SELECT COUNT(*) FROM config.user_override_azioni uoz
                             WHERE uoz.auth_user_id = au.id), 0) AS override_azioni_count,
                   COALESCE((SELECT COUNT(*) FROM config.user_emittenti_fiscali uef
                             WHERE uef.auth_user_id = au.id), 0) AS emittenti_count
              FROM auth_user au
              LEFT JOIN anagrafiche.risorse_umane_auth_user rua
                ON rua.auth_user_id = au.id
              LEFT JOIN anagrafiche.risorse_umane ru
                ON ru.id = rua.risorsa_umana_id
              LEFT JOIN config.unita_organizzative uo
                ON uo.id = ru.unita_organizzativa_id
             WHERE au.id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id])
            if not cursor.description:
                return None
            cols = [c.name for c in cursor.description]
            row = cursor.fetchone()

        if not row:
            return None

        return dict(zip(cols, row))  # type: ignore[return-value]

    # Scopo: Aggiorna i campi modificabili di un utente (auth_user + risorse_umane).
    # Dopo la modifica, il chiamante deve invalidare la cache permessi.
    def update_utente(
        self,
        auth_user_id: int,
        *,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        ruolo_sistema: str | None = None,
        unita_organizzativa_id: int | None = None,
        attivo: bool | None = None,
        valido_al: str | None = None,
    ) -> None:
        # Aggiorna auth_user
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

        # Aggiorna ruolo_sistema nel bridge
        if ruolo_sistema is not None:
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE anagrafiche.risorse_umane_auth_user
                          SET ruolo_sistema = %s::config.ruolo_sistema
                        WHERE auth_user_id = %s""",
                    [ruolo_sistema, auth_user_id],
                )

        # Aggiorna risorse_umane
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
                          FROM anagrafiche.risorse_umane_auth_user rua
                         WHERE rua.risorsa_umana_id = ru.id
                           AND rua.auth_user_id = %s""",
                    ru_params + [auth_user_id],
                )

        # Se ruolo_sistema o attivo cambiati, sync is_active via funzione DB
        if ruolo_sistema is not None or attivo is not None:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT anagrafiche.fn_sync_auth_user_is_active(%s)",
                    [auth_user_id],
                )

    # Scopo: Disabilita un utente impostando ruolo_sistema=DISABILITATO e attivo=false.
    # Chiama fn_sync_auth_user_is_active per sincronizzare auth_user.is_active.
    def disabilita_utente(self, auth_user_id: int) -> None:
        with connection.cursor() as cursor:
            # Imposta ruolo_sistema = DISABILITATO
            cursor.execute(
                """UPDATE anagrafiche.risorse_umane_auth_user
                      SET ruolo_sistema = 'DISABILITATO'::config.ruolo_sistema
                    WHERE auth_user_id = %s""",
                [auth_user_id],
            )
            # Imposta attivo = false su risorse_umane
            cursor.execute(
                """UPDATE anagrafiche.risorse_umane ru
                      SET attivo = false
                     FROM anagrafiche.risorse_umane_auth_user rua
                    WHERE rua.risorsa_umana_id = ru.id
                      AND rua.auth_user_id = %s""",
                [auth_user_id],
            )
            # Sync auth_user.is_active
            cursor.execute(
                "SELECT anagrafiche.fn_sync_auth_user_is_active(%s)",
                [auth_user_id],
            )

    # Scopo: Crea un operatore completo invocando l'orchestratore DB fn_crea_operatore.
    # Chiama i building block: fn_crea_auth_user, fn_crea_soggetto_pf, fn_crea_risorsa_umana.
    # Parametri Sprint 3: comune_nascita_id, indirizzo_resid_dettaglio_id,
    # indirizzo_domfisc_dettaglio_id (normalizzati via stradario).
    # Ritorna l'auth_user_id del nuovo operatore.
    def crea_operatore(
        self,
        *,
        cognome: str,
        nome: str,
        codice_fiscale: str,
        username: str,
        email: str,
        password_hash: str,
        qualifica_id: int,
        unita_organizzativa_id: int | None = None,
        data_nascita: str | None = None,
        sesso: str = "M",
        ruolo_sistema: str = "OPERATIVO",
        valido_dal: str | None = None,
        valido_al: str | None = None,
        comune_nascita_id: int | None = None,
        indirizzo_resid_dettaglio_id: int | None = None,
        indirizzo_domfisc_dettaglio_id: int | None = None,
    ) -> int:
        sql = """
            SELECT anagrafiche.fn_crea_operatore(
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
                p_ruolo_sistema                  := %s::config.ruolo_sistema,
                p_valido_dal                     := COALESCE(%s::date, CURRENT_DATE),
                p_valido_al                      := %s::date,
                p_comune_nascita_id              := %s,
                p_indirizzo_resid_dettaglio_id   := %s,
                p_indirizzo_domfisc_dettaglio_id := %s
            )
        """
        params = [
            cognome, nome, codice_fiscale,
            username, email, password_hash,
            qualifica_id, unita_organizzativa_id,
            data_nascita, sesso, ruolo_sistema,
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
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # ================================================================== #
    # Override aree per utente                                             #
    # ================================================================== #

    # Scopo: Restituisce gli override aree per un utente con nome area.
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
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Scopo: Sostituisce gli override aree di un utente (replace semantics).
    # Cancella tutti gli override esistenti e inserisce i nuovi.
    def put_override_aree(self, auth_user_id: int, items: list[dict[str, Any]]) -> None:
        with connection.cursor() as cursor:
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
    # Override azioni per utente                                           #
    # ================================================================== #

    # Scopo: Restituisce gli override azioni per un utente con descrizione azione.
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
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Scopo: Sostituisce gli override azioni di un utente (replace semantics).
    def put_override_azioni(self, auth_user_id: int, items: list[dict[str, Any]]) -> None:
        with connection.cursor() as cursor:
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
    # Emittenti scope per utente                                           #
    # ================================================================== #

    # Scopo: Restituisce gli emittenti fiscali associati a un utente.
    def get_emittenti_scope(self, auth_user_id: int) -> list[dict[str, Any]]:
        sql = """
            SELECT uef.id, uef.emittente_fiscale_id,
                   ef.codice AS emittente_codice,
                   ef.descrizione AS emittente_descrizione
              FROM config.user_emittenti_fiscali uef
              JOIN anagrafiche.emittenti_fiscali ef ON ef.id = uef.emittente_fiscale_id
             WHERE uef.auth_user_id = %s
             ORDER BY ef.descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [auth_user_id])
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Scopo: Sostituisce gli emittenti scope di un utente (replace semantics).
    def put_emittenti_scope(self, auth_user_id: int, emittente_ids: list[int]) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM config.user_emittenti_fiscali WHERE auth_user_id = %s",
                [auth_user_id],
            )
            for eid in emittente_ids:
                cursor.execute(
                    """INSERT INTO config.user_emittenti_fiscali
                       (auth_user_id, emittente_fiscale_id)
                       VALUES (%s, %s)""",
                    [auth_user_id, eid],
                )

    # ================================================================== #
    # Reparti e profili                                                    #
    # ================================================================== #

    # Scopo: Lista reparti con flag profilo configurato e conteggio operatori.
    def list_reparti(self) -> list[dict[str, Any]]:
        sql = """
            SELECT uo.id, uo.codice, uo.descrizione, uo.attivo,
                   (SELECT COUNT(*) FROM config.profili_reparto_aree pra
                     WHERE pra.unita_organizzativa_id = uo.id) AS profilo_aree_count,
                   (SELECT COUNT(*) FROM config.profili_reparto_azioni prz
                     WHERE prz.unita_organizzativa_id = uo.id) AS profilo_azioni_count,
                   (SELECT COUNT(*) FROM anagrafiche.risorse_umane ru
                     WHERE ru.unita_organizzativa_id = uo.id
                       AND ru.attivo = true) AS operatori_count
              FROM config.unita_organizzative uo
             WHERE uo.attivo = true
             ORDER BY uo.descrizione
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Scopo: Restituisce il profilo completo di un reparto (aree + azioni).
    def get_profilo_reparto(self, uo_id: int) -> dict[str, Any]:
        # Aree
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT pra.id, pra.area_id, af.codice AS area_codice,
                          af.descrizione AS area_descrizione,
                          pra.livello::text
                     FROM config.profili_reparto_aree pra
                     JOIN config.aree_funzionali af ON af.id = pra.area_id
                    WHERE pra.unita_organizzativa_id = %s
                    ORDER BY af.ordinamento, af.codice""",
                [uo_id],
            )
            cols_a = [c.name for c in cursor.description]
            aree = [dict(zip(cols_a, row)) for row in cursor.fetchall()]

        # Azioni
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT prz.id, prz.azione_id, ap.permission_codename,
                          ap.descrizione AS azione_descrizione,
                          af.codice AS area_codice,
                          prz.abilitata
                     FROM config.profili_reparto_azioni prz
                     JOIN config.azioni_processo ap ON ap.id = prz.azione_id
                     JOIN config.aree_funzionali af ON af.id = ap.area_id
                    WHERE prz.unita_organizzativa_id = %s
                    ORDER BY af.ordinamento, ap.permission_codename""",
                [uo_id],
            )
            cols_z = [c.name for c in cursor.description]
            azioni = [dict(zip(cols_z, row)) for row in cursor.fetchall()]

        return {"aree": aree, "azioni": azioni}

    # Scopo: Sostituisce il profilo completo di un reparto (aree + azioni).
    # Impatto: tutti gli operatori del reparto ereditano le modifiche.
    def put_profilo_reparto(
        self, uo_id: int, aree: list[dict[str, Any]], azioni: list[dict[str, Any]]
    ) -> None:
        with connection.cursor() as cursor:
            # Aree: replace
            cursor.execute(
                "DELETE FROM config.profili_reparto_aree WHERE unita_organizzativa_id = %s",
                [uo_id],
            )
            for item in aree:
                cursor.execute(
                    """INSERT INTO config.profili_reparto_aree
                       (unita_organizzativa_id, area_id, livello)
                       VALUES (%s, %s, %s::config.livello_accesso)""",
                    [uo_id, item["area_id"], item["livello"]],
                )
            # Azioni: replace
            cursor.execute(
                "DELETE FROM config.profili_reparto_azioni WHERE unita_organizzativa_id = %s",
                [uo_id],
            )
            for item in azioni:
                cursor.execute(
                    """INSERT INTO config.profili_reparto_azioni
                       (unita_organizzativa_id, azione_id, abilitata)
                       VALUES (%s, %s, %s)""",
                    [uo_id, item["azione_id"], item["abilitata"]],
                )

    # ================================================================== #
    # Lookup: aree funzionali e azioni processo                            #
    # ================================================================== #

    # Scopo: Lista aree funzionali attive per dropdown/selezione.
    def list_aree_funzionali(self) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, codice, descrizione, ordinamento
                     FROM config.aree_funzionali
                    WHERE attivo = true
                    ORDER BY ordinamento, codice"""
            )
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

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
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Scopo: Lista emittenti fiscali per dropdown scope utente.
    def list_emittenti_fiscali(self) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, codice, descrizione
                     FROM anagrafiche.emittenti_fiscali
                    WHERE attivo = true
                    ORDER BY descrizione"""
            )
            cols = [c.name for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
