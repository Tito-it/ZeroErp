# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'ora di ogni riga di log in UTC, ISO 8601 con `Z`
#        (`2026-10-09T22:54:03.120Z`). Decisione T-3 di
#        brief-be-db-fe-un-solo-fuso-aziendale (B-8).
#
#        ⛔ Fino al 2026-10-09 `%(asctime)s` scriveva l'ora del PROCESSO senza
#        offset: prima `TIME_ZONE` (Roma), poi UTC — e una riga senza offset
#        non dice in che fuso e' scritta. Nell'ora del cambio legale due righe
#        diverse avevano la stessa ora. Un log si confronta con altri log (PG,
#        nginx, systemd): l'istante con `Z` non dipende ne' dal processo ne'
#        dal parametro dell'azienda, ed e' l'unica forma che non si fraintende.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from datetime import UTC, datetime


class FormatterUtcIso(logging.Formatter):
    """`logging.Formatter` con `asctime` in UTC, ISO 8601, millisecondi e `Z`."""

    # Scopo: sostituisce la resa dell'ora del record (`%(asctime)s`); ignora
    #        `datefmt`, perche' il formato e' la decisione e non un'opzione.
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        istante = datetime.fromtimestamp(record.created, tz=UTC)
        return istante.isoformat(timespec="milliseconds").replace("+00:00", "Z")
