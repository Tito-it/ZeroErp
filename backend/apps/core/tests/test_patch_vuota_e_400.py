# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio TRASVERSALE della regola «una PATCH senza campi e' un 400»
#        (decisione Tid 2026-10-20, brief-be-verifica-documentazione-api §A2).
#        Fino a quel giorno lo stesso caso rispondeva in tre modi: 400 in
#        alcuni domini, 404 su un record che esiste in anagrafiche (l'UPDATE
#        vuoto tocca zero righe), 200 senza scrivere niente altrove — un
#        «salvato» che non ha salvato.
#        Un caso per ogni service corretto quel giorno: repository finto (ogni
#        lettura trova il record), corpo `{}`, e si guarda che l'errore sia di
#        classe 400 e che nessun UPDATE parta. Senza DB.
#        Le PATCH che gia' passavano dal BB `require_campi_da_aggiornare` hanno
#        i loro test nei domini; geo ha il suo presidio (`test_geo_patch`).
# ------------------------------------------------------------
"""Indice test:
1. test_ogni_patch_vuota_e_400_e_non_scrive (un subTest per service)
2. test_la_colonna_azione_non_inventa_un_campo
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.services.service_errors import ServiceError


# Scopo: un caso = (nome, bersaglio del repository da fingere, metodo di
#        scrittura che NON deve partire, chiamata, preparazione del finto).
def _casi() -> list[tuple[str, str, str, Callable[[], Any], Callable[[MagicMock], None]]]:
    from apps.amm_software.services.amm_software_service import AmmSoftwareService
    from apps.anagrafiche.services.soggetti_service import SoggettiService
    from apps.catalogo.services import catalogo_service
    from apps.core.services.email_outbox_service import EmailOutboxService
    from apps.magazzino.services import anagrafiche_magazzino_service as mag
    from apps.pagamenti.services import enti_incasso_service, pagamenti_service
    from apps.pratiche.services import pratiche_service
    from apps.vendite.services import preventivi_service
    from apps.vendite.services.famiglie_service import FamiglieDocumentoService
    from apps.vendite.services.registri_service import RegistriService

    def niente(_repo: MagicMock) -> None:
        return None

    def bozza(repo: MagicMock) -> None:
        repo.get_outbox.return_value = {"id": 1, "stato": "DRAFT"}

    def operatore(repo: MagicMock) -> None:
        from apps.amm_software.services import amm_software_service as amm

        repo.get_categoria_accesso.return_value = amm.CATEGORIA_ACCESSO_OPERATORE
        repo.get_operatore_detail.return_value = {"auth_user_id": 1, "veste_attiva": True}

    pag = "apps.pagamenti.services.pagamenti_service.PagamentiRepository"
    return [
        ("distinta", pag, "update_distinta",
         lambda: pagamenti_service.aggiorna_distinta(1, {}), niente),
        ("riga di distinta", pag, "update_riga",
         lambda: pagamenti_service.aggiorna_riga(1, {}), niente),
        ("ente d'incasso", "apps.pagamenti.services.enti_incasso_service.PagamentiRepository",
         "update_ente_incasso", lambda: enti_incasso_service.aggiorna_ente_incasso(1, {}), niente),
        ("magazzino", "apps.magazzino.services.anagrafiche_magazzino_service.AnagraficheMagazzinoRepository",
         "update_magazzino", lambda: mag.aggiorna_magazzino(1, {}), niente),
        ("ubicazione", "apps.magazzino.services.anagrafiche_magazzino_service.AnagraficheMagazzinoRepository",
         "update_ubicazione", lambda: mag.aggiorna_ubicazione(1, 2, {}), niente),
        ("lotto di magazzino", "apps.magazzino.services.anagrafiche_magazzino_service.AnagraficheMagazzinoRepository",
         "update_lotto", lambda: mag.aggiorna_lotto(1, {}), niente),
        ("tipologia UoM", "apps.catalogo.services.catalogo_service.CatalogoRepository",
         "update_uom_tipo", lambda: catalogo_service.fn_update_uom_tipo(1, {}), niente),
        ("unita' di misura", "apps.catalogo.services.catalogo_service.CatalogoRepository",
         "update_unita_misura", lambda: catalogo_service.fn_update_unita_misura(1, {}), niente),
        ("conversione UoM", "apps.catalogo.services.catalogo_service.CatalogoRepository",
         "update_conversione", lambda: catalogo_service.fn_update_conversione(1, {}), niente),
        ("preventivo", "apps.vendite.services.preventivi_service.PreventiviRepository",
         "update_preventivo", lambda: preventivi_service.aggiorna_preventivo(1, {}), niente),
        ("registro", "apps.vendite.services.registri_service.RegistriRepository",
         "update_registro", lambda: RegistriService().update_registro(1, None, {}), niente),
        ("famiglia", "apps.vendite.services.famiglie_service.FamiglieDocumentoRepository",
         "update_famiglia", lambda: FamiglieDocumentoService().update_famiglia(1, {}), niente),
        ("bozza email", "apps.core.services.email_outbox_service.EmailRepository",
         "update_outbox", lambda: EmailOutboxService().update_draft(1), bozza),
        ("pratica", "apps.pratiche.services.pratiche_service.PraticheRepository",
         "update_pratica", lambda: pratiche_service.aggiorna_pratica(1, {}), niente),
        ("operatore", "apps.amm_software.services.amm_software_service.AmmSoftwareRepository",
         "update_operatore", lambda: AmmSoftwareService().update_operatore(1, {}), operatore),
        ("contatto del soggetto", "apps.anagrafiche.services.soggetti_service.SoggettiRepository",
         "update_contatto", lambda: SoggettiService().update_contatto(1, {}, soggetto_id="x"), niente),
        ("contatto del ruolo", "apps.anagrafiche.services.soggetti_service.SoggettiRepository",
         "update_contatto", lambda: SoggettiService().update_contatto_ruolo(1, 2, {}), niente),
        ("indirizzo del ruolo", "apps.anagrafiche.services.soggetti_service.SoggettiRepository",
         "update_indirizzo_ruolo", lambda: SoggettiService().update_indirizzo_ruolo(1, 2, {}), niente),
        ("soggetto", "apps.anagrafiche.services.soggetti_service.SoggettiRepository",
         "update_soggetto", lambda: SoggettiService().update_soggetto("x", {}), niente),
        # ⛔ La sezione vuota non e' un campo: il verbo e' a stato intero, e
        #    `{}` azzerava i dati societari rispondendo 200.
        ("dati societari vuoti", "apps.anagrafiche.services.soggetti_service.SoggettiRepository",
         "scrivi_dati_societari",
         lambda: SoggettiService().update_soggetto("x", {"dati_societari": {}}), niente),
    ]


class PatchVuotaTests(TestCase):
    def test_ogni_patch_vuota_e_400_e_non_scrive(self) -> None:
        for nome, bersaglio, scrittura, chiamata, prepara in _casi():
            with self.subTest(patch=nome), patch(bersaglio) as classe:
                repo = classe.return_value
                prepara(repo)
                with self.assertRaises(ServiceError) as ctx:
                    chiamata()
                self.assertEqual(
                    ErrorPolicyRegistry.resolve(ctx.exception.code).http_status, 400,
                    f"{nome}: {ctx.exception.code}",
                )
                getattr(repo, scrittura).assert_not_called()

    # ⚠️ Sulle colonne «azione» `esportabile = false` e' DERIVATO: non e' un
    #    campo chiesto, e con `{}` faceva passare il controllo e scriveva.
    def test_la_colonna_azione_non_inventa_un_campo(self) -> None:
        from apps.ui.services.lista_colonna_admin_service import ListaColonnaAdminService

        svc = ListaColonnaAdminService()
        corrente = {"tipo_colonna": "azione"}
        self.assertEqual(svc._build_update_data({}, current=corrente), {})
        self.assertEqual(
            svc._build_update_data({"esportabile": True}, current=corrente),
            {"esportabile": False},
        )
