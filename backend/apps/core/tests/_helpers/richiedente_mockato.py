# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Mixin per i test delle view che consultano i dati di UN utente
#        (permessi effettivi, audit permessi). La decisione «se stesso o
#        amministratore» la prende il BB `richiedi_se_stesso_o_amministratore`
#        in `apps.core.api.permissions`: il mixin mette il mock sul resolver
#        di QUEL modulo, e ogni test dichiara chi e' il richiedente con
#        `self.richiedente_amministratore()`.
# Note: ⛔ Il mock della view NON decide piu' chi chiede: il resolver della
#       view risponde sull'utente CONSULTATO (`is_super_admin(target_user)` in
#       permessi effettivi). Due domande su due utenti, due mock: con uno solo
#       un test non sa distinguere «chi guarda e' admin» da «chi e' guardato e'
#       admin».
#       ⛔ Senza mock i test erano verdi per il motivo sbagliato (2026-10-08,
#       estrazione del BB): sono `unittest.TestCase`, il DB non e' vietato, e
#       `is_super_admin` interrogava il DB di sviluppo con un id finto.
#       ⭐ Default fail-closed: il richiedente NON e' amministratore finche' il
#       test non lo dice.
# ------------------------------------------------------------

from __future__ import annotations

from unittest.mock import patch


class RichiedenteMockatoMixin:
    # Scopo: per la durata del test il BB legge un resolver finto, che di
    #        default nega.
    def setUp(self) -> None:
        super().setUp()  # type: ignore[misc]
        patcher = patch("apps.core.api.permissions.PermissionResolver")
        self.resolver_richiedente = patcher.start()
        self.addCleanup(patcher.stop)  # type: ignore[attr-defined]
        self.resolver_richiedente.is_super_admin.return_value = False

    # Scopo: il richiedente e' SUPER_ADMIN (non superuser Django: si prova
    #        il ramo che passa dal resolver).
    def richiedente_amministratore(self) -> None:
        self.resolver_richiedente.is_super_admin.return_value = True
