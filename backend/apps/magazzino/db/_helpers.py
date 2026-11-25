# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I pezzi che i repository dello schema `magazzino` condividono — il
#        guard contro il canale di sistema (le tabelle sono sotto RLS: lette da
#        un ruolo BYPASSRLS perderebbero il perimetro).
# Note: Stampo `magazzino/services/_helpers.py`: materiale INTERNO del dominio,
#       non un building block di progetto. Nato il 2026-09-21 alla seconda
#       occorrenza — `anagrafiche_magazzino_repository` (magazzini, ubicazioni,
#       lotti: piano-be-fe-magazzino-anagrafiche-fuori-dal-pannello-config)
#       avrebbe ricopiato i due staticmethod di `MagazzinoRepository`.
#
#       ⭐ 2026-09-26 → 2026-11-23: `meta_mai_null`, poi `campi_jsonb` ed
#       `esegui_verbo` (il trasporto verso i VERBI del DB) sono stati qui;
#       alla seconda occorrenza sono passati al core, BB di
#       `apps/core/db/sql_write_helpers.py` (ok Tid 2026-11-23,
#       brief-db-magazzino-tutte-le-scritture-dal-verbo).
#       ⭐ 2026-11-24: `lista_paginata` e' passata al core, BB di
#       `apps/core/db/_helpers.py` (E-2 di brief-be-fe-BB-audit, ok Tid): la
#       stessa pagina era scritta in `PagamentiRepository._lista_paginata`.
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.services.error_manager import ErrorManager
from apps.core.services.system_context import connection_role_bypasses_rls

# Il guard di parametro del dominio, gia' a catalogo (TECNICO): e' il codice
# dei soli guard strutturali dei repository, che un operatore non puo'
# causare compilando qualcosa.
E_CHIAMATA = "E_MAG_CHIAMATA_NON_VALIDA"


# Scopo: Impedisce che una lettura di perimetro giri su un ruolo BYPASSRLS.
# Contesto: le policy di `magazzino` sono il cancello delle liste (piu' lo
#        scope applicativo che si somma). Su un ruolo che le scavalca la lista
#        non fallirebbe: mostrerebbe la merce di TUTTI gli emittenti.
def guard_canale_sistema(function_name: str) -> None:
    ErrorManager.require(
        not connection_role_bypasses_rls(),
        code=E_CHIAMATA,
        message="Operazione non disponibile dal canale di sistema.",
        detail=(
            "Le tabelle di magazzino sono protette da RLS: lette da un "
            "ruolo BYPASSRLS perderebbero il perimetro emittente. Usare "
            "la connessione dell'utente della richiesta."
        ),
        function_name=function_name,
    )
