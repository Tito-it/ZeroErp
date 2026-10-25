# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Mixin per i test unitari dei service che applicano le regole del
#        modello del documento (`apps.core.services.documento_modello`): il
#        mixin mette il mock sul repository di QUEL modulo, cosi' il rifiuto
#        dello stato di emissione non interroga il DB.
# Note: ⛔ Senza mock i test erano verdi per il motivo sbagliato o rossi per
#       quello sbagliato (2026-10-25, giro BE 6): sotto `SimpleTestCase` il DB
#       e' vietato, sotto `unittest.TestCase` la domanda arrivava al DB di
#       sviluppo.
#       ⭐ Default: lo stato chiesto NON e' l'emissione. Il test del rifiuto lo
#       dichiara con `self.stato_chiesto_di_emissione()`.
# ------------------------------------------------------------

from __future__ import annotations

from unittest.mock import patch


class ModelloDocumentoMockatoMixin:
    # Scopo: per la durata del test il BB legge un repository finto.
    def setUp(self) -> None:
        super().setUp()  # type: ignore[misc]
        patcher = patch("apps.core.services.documento_modello.DocumentoModelloRepository")
        self.modello_documento = patcher.start().return_value
        self.addCleanup(patcher.stop)  # type: ignore[attr-defined]
        self.modello_documento.e_stato_di_emissione.return_value = False

    # Scopo: lo stato chiesto e' lo stato di emissione del documento.
    def stato_chiesto_di_emissione(self) -> None:
        self.modello_documento.e_stato_di_emissione.return_value = True
