# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Accesso DB per DDT di vendita — oggi limitato al CRUD componenti BoM
#        (modello unificato `ddt_righe_componenti`) usato dal push a commessa.
# ------------------------------------------------------------

# Repository DDT vendita. Nasce minimale: espone solo i componenti BoM
# (via ComponentiRepositoryMixin) per consentire al push commessa il fan-out
# degli articoli compositi, simmetrico a preventivi/ordini/contratti. Il resto
# del ciclo DDT (testata/righe) non e' ancora gestito lato BE.

from apps.vendite.db._componenti_repo_mixin import ComponentiRepositoryMixin


class DdtRepository(ComponentiRepositoryMixin):
    """Repository DDT vendita (componenti BoM modello unificato).

    Eredita da `ComponentiRepositoryMixin` per `list_componenti_riga` su
    `vendite.ddt_righe_componenti`. Usato dal push commessa (HandlerDdt) per
    leggere i componenti negoziati della riga sorgente ed espandere i compositi.
    """

    # Configurazione mixin componenti (tabella + FK riga padre).
    _componenti_table_name = "vendite.ddt_righe_componenti"
    _componenti_fk_riga = "riga_ddt_id"
