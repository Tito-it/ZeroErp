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
#       ⭐ Default: il documento NON ha uno stato di emissione (lettore -> None,
#       «Emetti» risponde E_CONFIG_MANCANTE). Il test di «Emetti» dichiara lo
#       stato con `self.emissione_del_documento("EMESSO")`: il codice lo
#       sceglie il test, come il vocabolario lo sceglie per il documento.
#       ⭐ Default per l'annullo: e' lo stato d'annullo un codice di
#       `ANNULLI_DI_PROVA` (i nomi dei vocabolari, maschile e femminile): la
#       domanda resta al BB (`e_stato_di_annullo`), il nome lo sceglie il test.
# ------------------------------------------------------------

from __future__ import annotations

from unittest.mock import patch

from apps.core.db.documento_modello_repository import StatoDocumento

# I codici d'annullo che il repository finto riconosce, come i vocabolari.
ANNULLI_DI_PROVA: frozenset[str] = frozenset({"ANNULLATO", "ANNULLATA"})


class ModelloDocumentoMockatoMixin:
    # Scopo: per la durata del test il BB legge un repository finto.
    def setUp(self) -> None:
        super().setUp()  # type: ignore[misc]
        patcher = patch("apps.core.services.documento_modello.DocumentoModelloRepository")
        self.modello_documento = patcher.start().return_value
        self.addCleanup(patcher.stop)  # type: ignore[attr-defined]
        self.modello_documento.e_stato_di_emissione.return_value = False
        self.modello_documento.stato_di_emissione.return_value = None
        self.modello_documento.e_stato_di_annullo.side_effect = (
            lambda _testata, codice: codice in ANNULLI_DI_PROVA
        )

    # Scopo: lo stato chiesto e' lo stato di emissione del documento.
    def stato_chiesto_di_emissione(self) -> None:
        self.modello_documento.e_stato_di_emissione.return_value = True

    # Scopo: il documento si emette, e il suo stato di emissione e' questo.
    def emissione_del_documento(self, codice: str, *, stato_id: int = 2) -> None:
        self.modello_documento.stato_di_emissione.return_value = StatoDocumento(
            id=stato_id, codice=codice,
        )
