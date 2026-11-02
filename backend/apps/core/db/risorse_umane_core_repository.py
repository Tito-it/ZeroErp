# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block repository per risorse umane.
# Chiama anagrafiche.fn_crea_risorsa_umana per creare una
# risorsa umana con bridge auth_user opzionale.
# Riusabile da qualsiasi dominio che crei risorse umane
# (operatori, admin, dipendenti senza accesso).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.db import connection

from apps.core.db._helpers import fetchone_scalar


class RisorseUmaneCoreRepository:
    """Building block: operazioni atomiche su risorse umane."""

    # Scopo: Crea una risorsa umana invocando fn_crea_risorsa_umana.
    # Se auth_user_id fornito, crea anche il bridge risorse_umane_auth_user.
    # Contract multi-face puro (Fase 7-DB step 6): la fn DB v2 accetta
    # `p_is_super_admin bool` + `p_attivo bool` al posto del legacy
    # `p_ruolo_sistema config.ruolo_sistema`. Il translator interno e'
    # stato rimosso.
    # Ritorna risorse_umane.id.
    def crea_risorsa_umana(
        self,
        *,
        soggetto_id: str,
        qualifica_id: int,
        unita_organizzativa_id: int | None = None,
        valido_dal: str | None = None,
        valido_al: str | None = None,
        auth_user_id: int | None = None,
        is_super_admin: bool = False,
        attivo: bool = True,
    ) -> int:
        sql = """
            SELECT anagrafiche.fn_crea_risorsa_umana(
                p_soggetto_id            := %s::uuid,
                p_qualifica_id           := %s,
                p_unita_organizzativa_id := %s,
                p_valido_dal             := %s::date,
                p_valido_al              := %s::date,
                p_auth_user_id           := %s,
                p_is_super_admin         := %s,
                p_attivo                 := %s
            )
        """
        params: list[Any] = [
            soggetto_id, qualifica_id, unita_organizzativa_id,
            valido_dal, valido_al, auth_user_id,
            is_super_admin, attivo,
        ]
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return fetchone_scalar(cursor)

    # Scopo: Riapre la risorsa umana di una VESTE (catena veste ->
    #        soggetto_ruolo), se e' chiusa: `attivo = true`, e `valido_al`
    #        azzerata solo se e' gia' arrivata (oggi o prima).
    #        Ritorna le righe riaperte (0 se era gia' aperta, o se la veste non
    #        ha una risorsa umana).
    # ⭐ D-3 (Tid, 2026-09-24/2026-10-04): un operatore spento si riattiva col
    #    reinvio dell'invito, e il gesto dell'amministratore riapre il RAPPORTO,
    #    non la porta — la veste resta spenta finche' la persona non attiva.
    #    Riaprire il padre prima del figlio e' anche l'ordine che il DB chiede
    #    (api.md §«Disattivazione record»).
    # ⛔ Prende l'id della veste, non la credenziale: il rapporto da riaprire
    #    e' quello della veste che il chiamante sta invitando. Ricavarla qui
    #    con un secondo selettore (`fn_veste_di_riferimento`) era una seconda
    #    regola su «quale veste», d'accordo con la prima solo finche' il check
    #    d'invitabilita' ne lascia passare una sola.
    # ⛔ `valido_dal` non si tocca: e' l'inizio del rapporto. La riattivazione
    #    diretta, ritirata con D-3, lo riscriveva a oggi.
    # ⛔ Una `valido_al` FUTURA resta (Tid, 2026-10-04): e' una fine rapporto
    #    prevista, scritta dall'amministratore, e riaprire non la decide.
    #    Si azzera solo quella che chiude il rapporto oggi o l'ha gia' chiuso
    #    (`Disabilita` scrive oggi), o il rapporto riaperto resterebbe scaduto.
    def riapri_risorsa_umana_della_veste(self, identita_id: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """UPDATE anagrafiche.risorse_umane ru
                      SET attivo = true,
                          valido_al = CASE WHEN ru.valido_al <= (SELECT script.fn_data_operativa())
                                           THEN NULL ELSE ru.valido_al END
                     FROM anagrafiche.identita_digitali id
                    WHERE id.id = %s
                      AND id.soggetto_ruolo_id = ru.soggetto_ruolo_id
                      AND ru.attivo = false""",
                [identita_id],
            )
            return cursor.rowcount
