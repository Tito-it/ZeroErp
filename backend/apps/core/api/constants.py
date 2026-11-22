# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Costanti condivise per API (paginazione, limiti).
# ------------------------------------------------------------

# ⭐ FONTE UNICA della paginazione delle liste (2026-09-28, decisione di Tid).
#    Le leggono view, service e repository — anche il layer db: questo modulo
#    non importa niente, quindi non crea cicli. Prima c'erano tre costanti per
#    il tetto (`MAX_LIMIT` in `core/db/_helpers`, `MAX_LIMIT` qui e in
#    `amm_software/constants`), ~45 `200` scritti a mano e due default
#    diversi (50 qui, 25 in `parse_list_params`). Presidio:
#    `apps/core/tests/test_paginazione_fonte_unica.py`.

# Righe per pagina quando il client non le chiede: e' la REGOLA DELL'API per
# gli endpoint FUORI dal catalogo delle liste configurabili.
# ⛔ Non ricopia la misura di una lista configurabile (Q11-bis, BE10 del giro 3
#    di brief-db-revisione-ui): quella la dice il DB, dalla configurazione
#    risolta (`pagina_dimensione`, lo standard dal catalogo `ui.misure_pagina`
#    secondo l'uso che la lista dichiara), e il frontend la manda come `limit`.
#    Chiamata SENZA `limit`, una lista configurabile pagina con la misura
#    della sua configurazione (`ui.fn_misura_lista`), registrata dalla base
#    view nella stessa sede dell'ordinamento di partenza
#    (`apps.core.services.ordinamento_di_partenza`) e letta da
#    `pagina_da_query`: BE10, giro 6 dello stesso brief (2026-11-22).
DEFAULT_LIMIT = 25

# Righe per pagina di una lista di EVENTI fuori catalogo (il giornale di una
# pratica, il registro di una commessa; i task run di un lotto, lista
# configurabile, prendono la misura della loro configurazione): si legge a
# blocchi piu' lunghi di una lista anagrafica. Una costante e non un `100`
# scritto nella view e ripetuto nelle firme di service e repository (§9.6
# punto 3 del brief-db-liste-righe-documento, Tid 2026-10-04: «riportare le
# liste non standard allo standard»). Il tetto resta `MAX_LIMIT`.
DEFAULT_LIMIT_EVENTI = 100

# Tetto di righe per PAGINA di lista. L'export non e' una pagina: ha il suo
# (`EXPORT_MAX_ROWS`) e lo passa esplicitamente.
MAX_LIMIT = 200
