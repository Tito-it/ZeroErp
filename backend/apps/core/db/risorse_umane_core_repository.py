# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block repository per risorse umane.
# ⚠️ `crea_risorsa_umana` (wrapper di anagrafiche.fn_crea_risorsa_umana)
#    ritirato il 2026-11-26 (ok Tid, brief-db-porte-aperte-dalla-sola-guc
#    §14.9): non aveva chiamanti, e dal giro 10-bis la funzione e' una
#    primitiva chiusa all'app. Una risorsa umana con accesso nasce da
#    `anagrafiche.fn_crea_operatore`.
# ------------------------------------------------------------

from __future__ import annotations

from django.db import connection


class RisorseUmaneCoreRepository:
    """Building block: operazioni atomiche su risorse umane."""

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
