# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command per il riallineamento batch di
#        `auth_user.is_active` alle vesti utilizzabili oggi (spegne chi non ne
#        ha piu' una, accende chi ne ha una diventata valida). Wrapper Django per
#        anagrafiche.fn_sync_auth_user_expired() con invalidazione
#        cache permessi per gli utenti coinvolti.
# Note: ⛔ ATTREZZO A MANO, non un processo programmato — e dal 2026-09-07 non
#       si registra piu' sul giornale dei run.
#       Il lavoro schedulato lo fa il job pgAgent `sync_auth_user_expired_daily`
#       (`dbops.processi` id 11). La riga gemella id 23 (`sync_auth_user_active`,
#       canale COMMAND) e' RITIRATA — `obsoleto_dal = 2026-09-07` — e con lei
#       sono spariti l'unit systemd, la voce in `deploy/sveglie.json` e la
#       costante `PROCESSO_*`: fino a quel giorno il modello ammetteva che
#       girassero **entrambi**, cioe' la disattivazione due volte per notte.
#       ⛔ E NON si registra sotto il codice superstite, che pure la FK
#       accetterebbe: la LATERAL di `dbops.vw_processi_programmazione` legge il
#       giornale con `processo_codice = codice OR jobname = codice` **senza
#       filtrare `origine`**, quindi una corsa a mano sposterebbe avanti
#       `giornale_ultima_corsa` e spegnerebbe il confronto GIRA_E_NON_REGISTRA
#       su quel job — cioe' il rilevatore di R-12. Un attrezzo a mano non deve
#       poter accecare il presidio del lavoro che imita.
#       ⚠️ Ne discende che un lancio di qui NON lascia traccia: e' il prezzo
#       dichiarato della scelta (Tid, 2026-09-07), non una dimenticanza.
#       Brief: work-in-progress/brief-db-sveglia-dei-processi.md §8.5/§9.5.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.core.management.base import CommandError
from apps.core.management.comando_aziendale import ComandoAziendale

from apps.anagrafiche.db.anagrafiche_repository import AnagraficheRepository
from apps.core.services.permissions_cache import invalidate_user

logger = logging.getLogger(__name__)


class Command(ComandoAziendale):
    help = (
        "Riallinea auth_user.is_active alle vesti utilizzabili oggi (spegne e accende). "
        "Wrapper per anagrafiche.fn_sync_auth_user_expired() con invalidazione "
        "cache permessi."
    )

    # Scopo: Registra argomenti CLI del command.
    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo report: mostra gli utenti che sarebbero riallineati senza applicare modifiche.",
        )

    # Scopo: Esegue la sync. ⛔ NESSUNA registrazione sul giornale dei run, e la
    #        ragione sta nell'header: il processo di catalogo che questo command
    #        nominava e' ritirato, e registrarsi sotto il gemello pgAgent
    #        accecherebbe il presidio che sorveglia proprio quel job.
    # ⚠️ Classe AMMINISTRAZIONE: tocca dati che non appartengono a un emittente
    #    (`auth_user`, `risorse_umane`), quindi non ha un utente tecnico e non
    #    itera per azienda.
    # ⚠️ Il riepilogo di `_esegui` NON viene piu' consumato: era il `set_meta`
    #    del run, e chi lo leggeva era il giornale. Resta un valore di ritorno
    #    perche' e' l'esito della funzione — quello che l'operatore vede lo
    #    scrive `_esegui` su stdout — ma qui non ha piu' un destinatario, ed e'
    #    scritto per non farlo sembrare una dimenticanza.
    def handle(self, *args: Any, **options: Any) -> None:
        self._esegui(options)

    # Scopo: Esegue il riallineamento batch e ritorna il riepilogo.
    # Flusso: UNA chiamata al repository, che esegue la funzione SQL e ritorna
    #         gli auth_user_id che ha DAVVERO modificato; poi invalida la cache
    #         permessi per ciascuno. In dry-run la corsa e' la stessa, ritirata.
    # ⛔ Fino al 2026-09-12 c'era una «fase 1» che elencava i candidati con una
    #    `WHERE` ricopiata in Python (e a meta': solo il ramo legacy, via la
    #    vista `risorse_umane_auth_user` che il DB ritira). La regola «chi vale
    #    oggi» ora vive in una sede sola, a DB, e il command legge
    #    l'effetto (analisi-software-per-dati-morti §2.1, passo 1).
    def _esegui(self, options: Any) -> dict:
        dry_run: bool = options["dry_run"]
        repository = AnagraficheRepository()

        try:
            count, affected_ids = repository.sync_auth_user_expired(dry_run=dry_run)

            if not affected_ids:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Nessun utente da riallineare."
                    )
                )
                return {"riallineati": 0, "cache_invalidata": 0}

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f"[DRY-RUN] {len(affected_ids)} utenti sarebbero riallineati: "
                        f"auth_user_id = {affected_ids}"
                    )
                )
                return {"dry_run": True, "candidati": len(affected_ids)}

            # Invalidazione cache permessi: solo chi ha cambiato stato.
            invalidated = 0
            for user_id in affected_ids:
                invalidate_user(user_id)
                invalidated += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Sync completata: {count} utenti riallineati, "
                    f"cache invalidata per {invalidated} utenti."
                )
            )

            logger.info(
                "sync_auth_user_active: riallineati=%d, cache_invalidata=%d, "
                "auth_user_ids=%s",
                count,
                invalidated,
                affected_ids,
            )
            return {"riallineati": count, "cache_invalidata": invalidated}

        except Exception as exc:
            logger.exception("Errore in sync_auth_user_active")
            raise CommandError(
                f"Errore durante la sync: {exc}"
            ) from exc
