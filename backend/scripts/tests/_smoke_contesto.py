# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block degli smoke Python: il CONTESTO OPERATORE con cui uno
#        smoke in-process legge e scrive sotto RLS, sull'utente degli smoke del
#        provisioning di sviluppo (`dev.smoke`).
# Note: ⭐ Regola del 2 (ok Tid, 2026-10-18): la stessa apertura del contesto
#       stava in dieci smoke, e prendeva l'operatore con
#       `SELECT auth_user_id FROM config.user_emittenti_fiscali LIMIT 1`, senza
#       ordine. Da quando ci sono gli utenti `dev.*` quella riga poteva essere
#       `dev.lettura`, che vede solo l'emittente di prova (vuoto): la RLS dava
#       zero righe e lo smoke diceva «nessuna attivita' fatturabile» su un
#       database che ne aveva 63.
#       ⭐ PERCHE' `dev.smoke`: e' l'utente degli smoke (brief-be-utenti-di-
#       sviluppo T-2), lo stesso di quelli via HTTP, e il provisioning lo crea
#       su ogni installazione di sviluppo. E' SUPER_ADMIN e non ha whitelist:
#       il perimetro e' largo e non dipende da come e' configurata la
#       macchina. Mai l'utente personale di qualcuno.
#       Il nome viene dalla sede che crea l'utente (`UTENTE_SMOKE` del command
#       `provision_utenti_sviluppo`), non si ricopia qui.
#       ⚠️ Le GUC sono di SESSIONE (`set_config(..., false)`), come nelle copie
#       che sostituisce: valgono anche per lo smoke che lavora fuori da una
#       transazione. La shell finisce con lo smoke.
#       Uso: `from scripts.tests._smoke_contesto import apri_contesto_smoke`.
#       Il trattino basso lo tiene fuori dalla scoperta di `smoke-baseline.sh`.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.anagrafiche.management.commands.provision_utenti_sviluppo import UTENTE_SMOKE


# Scopo: apre il contesto OPERATORE sull'utente degli smoke e ne restituisce
#        l'`auth_user.id`. Si ferma (SystemExit, col perche') se l'utente non
#        c'e', non e' una credenziale di prova, non e' super admin o non ha una
#        veste OPERATORE attiva: lo smoke non misura il vuoto.
def apri_contesto_smoke(cur: Any) -> int:
    cur.execute(
        """
        SELECT au.id,
               EXISTS (SELECT 1 FROM dbops.credenziali_di_prova cp
                        WHERE cp.auth_user_id = au.id),
               script.fn_is_super_admin(au.id),
               EXISTS (SELECT 1 FROM anagrafiche.identita_digitali i
                        WHERE i.auth_user_id = au.id
                          AND i.ruolo_applicativo = 'OPERATORE'
                          AND i.attivo)
          FROM auth_user au
         WHERE au.username = %s
        """,
        [UTENTE_SMOKE],
    )
    riga = cur.fetchone()
    if riga is None:
        raise SystemExit(
            f"SENZA_CONTESTO: l'utente degli smoke {UTENTE_SMOKE} non c'e'. "
            "Lancia `./manage-env.sh provision_utenti_sviluppo` (run-book §11)."
        )
    auth_user_id, di_prova, super_admin, operatore = riga
    if not (di_prova and super_admin and operatore):
        raise SystemExit(
            f"SENZA_CONTESTO: {UTENTE_SMOKE} non e' come lo crea il provisioning "
            f"(di prova={di_prova}, super admin={super_admin}, veste OPERATORE attiva={operatore}). "
            "Rilancia `./manage-env.sh provision_utenti_sviluppo`."
        )
    cur.execute(
        "SELECT set_config('app.ruolo_applicativo', 'OPERATORE', false),"
        "       set_config('app.current_user_id', %s, false)",
        [str(auth_user_id)],
    )
    return int(auth_user_id)


# Scopo: SCEGLIE l'emittente di prova, come l'operatore lo sceglie in alto
#        (`app.current_emittente_id`, GUC di sessione), per uno smoke che
#        COSTRUISCE le sue fixture (un cliente, un BA): il primo per codice fra
#        quelli del provisioning di sviluppo, riconosciuti dall'etichetta
#        (`dbops.soggetti_di_prova`), non da una sigla scritta qui. Da li' in
#        poi il perimetro della sessione e' quell'emittente. Ritorna
#        `(emittente_fiscale_id, soggetto_ruolo_id)`.
# ⚠️ Serve perche' `dev.smoke` e' SUPER_ADMIN in «Tutti gli emittenti»: un
#    BA nuovo vuole un emittente scelto (`trgfn_billing_account_guard_admin_globale`),
#    e scriverlo su un emittente vero sporcherebbe dati veri.
def seleziona_emittente_di_prova(cur: Any) -> tuple[int, int]:
    cur.execute(
        """
        SELECT ef.id, ef.soggetto_ruolo_id
          FROM anagrafiche.emittenti_fiscali ef
          JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id
          JOIN dbops.soggetti_di_prova sp ON sp.soggetto_id = sr.soggetto_id
         WHERE ef.attivo
         ORDER BY ef.codice
         LIMIT 1
        """
    )
    riga = cur.fetchone()
    if riga is None:
        raise SystemExit(
            "SENZA_CONTESTO: nessun emittente di prova. "
            "Lancia `./manage-env.sh provision_utenti_sviluppo` (run-book §11)."
        )
    cur.execute("SELECT set_config('app.current_emittente_id', %s, false)", [str(riga[0])])
    return int(riga[0]), int(riga[1])
