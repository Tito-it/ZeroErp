# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il CABLAGGIO dei filtri di lista coi loro vocabolari (2026-10-20):
#        ogni lista con un filtro a vocabolario chiuso lo verifica PRIMA della
#        query — con `richiedi_codice_a_vocabolario` se il vocabolario e' una
#        tabella, con lo specchio del CHECK se e' un vincolo. Prima i valori
#        andavano nel WHERE senza controllo e la lista rispondeva vuota.
#        Qui si prova che ogni service CHIAMA il controllo giusto; che le
#        tabelle esistano lo prova `test_vocabolari_dei_filtri_db`, che gli
#        specchi coincidano coi CHECK `test_specchi_dei_check_db`.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_liste_a_tabella_chiamano_il_vocabolario — sei documenti + natura fattura
   + giornale + distinte: tabella, colonna e valore giusti, prima del repository
2) test_liste_a_check_rifiutano_fuori_specchio — stato lotto, esito fattura del
   lotto, stati della riga di commessa, origine distinta: 400, query non partita
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError


# Il controllo sostituito: un filtro assente (None) passa come nel BB vero, il
# primo valore presente ferma la chiamata prima del repository.
def _ferma(_tabella, _colonna, valore, **_k):
    if valore is None:
        return None
    raise RuntimeError("stop")


class FiltriVocabolarioCablaggioTests(TestCase):

    def test_liste_a_tabella_chiamano_il_vocabolario(self) -> None:
        from apps.pagamenti.services import pagamenti_service
        from apps.vendite.services import (
            ddt_service, offerte_service, ordini_service, preventivi_service,
            resi_service, vendite_service,
        )

        comuni = {"limit": 10, "offset": 0}
        casi = (
            (ddt_service, lambda: ddt_service.list_ddt_rows(stato_codice="X", **comuni), "config.stati_doc_ddt"),
            (resi_service, lambda: resi_service.list_resi_rows(stato_codice="X", **comuni), "config.stati_doc_reso"),
            (preventivi_service, lambda: preventivi_service.list_preventivi_rows(stato_codice="X", **comuni),
             "config.stati_doc_preventivi"),
            (ordini_service, lambda: ordini_service.list_ordini_rows(stato_codice="X", **comuni), "config.stati_doc_ordini"),
            (offerte_service, lambda: offerte_service.OfferteService().list_offerte(stato_codice_interno="X"),
             "config.stati_doc_offerte"),
            (vendite_service, lambda: vendite_service.list_fatture_rows(stato_codice="X", **comuni),
             "config.stati_doc_fiscale"),
            (vendite_service, lambda: vendite_service.list_fatture_rows(natura_doc_codice="X", **comuni),
             "config.nature_doc_fiscale"),
            (vendite_service, lambda: vendite_service.get_giornale_trasversale(entity_type="x"), "config.tipi_entita"),
            (pagamenti_service, lambda: pagamenti_service.list_distinte(stato="X"), "pagamenti.vendite_contabili_stati"),
        )
        for modulo, chiamata, tabella in casi:
            with self.subTest(tabella=tabella), \
                    patch.object(modulo, "richiedi_codice_a_vocabolario", side_effect=_ferma) as vocab, \
                    patch("apps.vendite.services.offerte_service.OfferteRepository", MagicMock()), \
                    patch("apps.vendite.services.vendite_service.VenditeRepository", MagicMock()):
                with self.assertRaises(RuntimeError):
                    chiamata()
                tabelle_chieste = [c.args[0] for c in vocab.call_args_list]
                self.assertIn(tabella, tabelle_chieste)
                valori = [c.args[2] for c in vocab.call_args_list if c.args[0] == tabella]
                self.assertIn(valori[0], ("X", "X".upper()))

    def test_liste_a_check_rifiutano_fuori_specchio(self) -> None:
        from apps.pagamenti.services import pagamenti_service
        from apps.vendite.services import commesse_service, vendite_service

        casi = (
            ("stato_lotto", lambda: vendite_service.fn_list_lotti(stato_lotto="DRAFT")),
            ("stato_esecuzione", lambda: vendite_service.fn_list_lotto_fatture(
                lotto_id=1, stato_esecuzione="OK")),
            ("stato_emissione", lambda: commesse_service.fn_list_commessa_attivita(
                commessa_id=1, stato_emissione="BOH")),
            ("stato_approvazione", lambda: commesse_service.fn_list_commessa_attivita(
                commessa_id=1, stato_approvazione="BOH")),
            ("origine", lambda: pagamenti_service.list_distinte(origine="BOH")),
        )
        for campo, chiamata in casi:
            with self.subTest(campo=campo), \
                    patch("apps.vendite.services.vendite_service.VenditeRepository") as v_repo, \
                    patch("apps.vendite.services.commesse_service.CommesseRepository") as c_repo, \
                    patch("apps.pagamenti.services.pagamenti_service.richiedi_codice_a_vocabolario"), \
                    patch("apps.pagamenti.services.pagamenti_service.PagamentiRepository") as p_repo:
                with self.assertRaises(ServiceError) as ctx:
                    chiamata()
                # Il parametro nominato nel context, senza `field` (filtro di query).
                self.assertEqual(ctx.exception.context.get("parametro"), campo)
                self.assertNotIn("field", ctx.exception.context)
                self.assertFalse(v_repo.return_value.list_lotti.called)
                self.assertFalse(v_repo.return_value.list_lotto_fatture.called)
                self.assertFalse(c_repo.return_value.list_commessa_attivita.called)
                self.assertFalse(p_repo.return_value.list_distinte.called)
