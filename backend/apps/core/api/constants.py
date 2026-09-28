# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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

# Righe per pagina quando il client non le chiede: le stesse che l'operatore
# vede a video (`ui.lista_preset.pagina_dimensione` e `PAGINATION.DEFAULT_ROWS`
# del frontend), cosi' una chiamata API senza `limit` risponde come la lista.
DEFAULT_LIMIT = 25

# Tetto di righe per PAGINA di lista. L'export non e' una pagina: ha il suo
# (`EXPORT_MAX_ROWS`) e lo passa esplicitamente.
MAX_LIMIT = 200
