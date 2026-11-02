# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Factory condivisa del fixture "lane" (terna emittibile) con la STESSA
#        forma di CommesseRepository.list_emittibili_lane. Prima viveva in tre
#        copie identiche (test_emissione_mirata, test_fatturazione_driver_service,
#        test_run_fatturazione_batch_command): l'aggiunta di `gruppi_coperti`
#        (rev DB 2026-08-15) ha richiesto lo stesso edit tre volte — regola
#        del 2, estratta qui. Un fixture che resta indietro rispetto alla
#        forma vera "conferma un comportamento inesistente" (memoria
#        whitelist-dal-percorso-reale): una sede sola tiene il rischio in un
#        posto solo.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from typing import Any


# Scopo: costruisce una lane come la ritorna CommesseRepository.list_emittibili_lane.
#        `em=None` = terna senza emittente (non fatturabile); `coperti` = gruppi
#        fatturabili coperti dalla terna (rev DB 2026-08-15).
def lane(em: int | None = 1, *, tipo_doc: int = 1, utility: int = 9,
         comp: date = date(2026, 6, 1), tot: int = 1,
         coperti: tuple[str, ...] | list[str] = ()) -> dict[str, Any]:
    return {
        "emittente_soggetto_ruolo_id": em,
        "tipo_doc_fiscale_id": tipo_doc,
        "utility_id": utility,
        "competenza_mese": comp,
        "total_candidate": tot,
        "gruppi_coperti": list(coperti),
    }
