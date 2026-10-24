# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del service "situazione merce" (mock repository).
#        Presidiano le tre cose che il brief della partita generalizzata
#        chiede espressamente al backend (§19.1 BE-2/BE-3) e il cancello di
#        perimetro sulla testata.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) SituazioneMerceServiceTests.test_ordine_quattro_sezioni_e_filtro_per_ordine
2) SituazioneMerceServiceTests.test_ddt_livello_uno_filtrato_sulla_spedizione
3) SituazioneMerceServiceTests.test_differenza_null_non_diventa_zero
4) SituazioneMerceServiceTests.test_stato_non_viene_ri_tradotto
5) SituazioneMerceServiceTests.test_ordine_fuori_scope_o_inesistente_not_found
6) SituazioneMerceServiceTests.test_ddt_fuori_scope_o_inesistente_not_found
7) SituazioneMerceServiceTests.test_nessun_id_indicato_validazione
8) SituazioneMerceServiceTests.test_entrambi_gli_id_indicati_validazione
9) SituazioneMerceServiceTests.test_perimetro_verificato_prima_delle_letture
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.vendite_service import get_situazione_merce

# Riga d'ordine MAI SPEDITA: e' il caso che il contatore non contiene affatto
# (89 su 107 in sviluppo) e ha `differenza` NULL con `fatturato_anticipato`
# valorizzato — cioe' merce fatturata e non ancora uscita, che NON e' un
# accredito. Se una di queste due cose si perde, il pannello mente.
_RIGA_MAI_SPEDITA = {
    "ordine_riga_id": 101,
    "riga_nr": 1,
    "ordinato": "2.000000",
    "consegnato": "0",
    "fatturato": "0",
    "fatturato_anticipato": "2.000000",
    "da_spedire": "2.000000",
    "partite_merce": 0,
    "misurabile": True,
    "differenza": None,
    "stato": "NON_SPEDITA",
}

# Partita su causale non fatturabile: `differenza` NULL significa «il conto non
# si applica», non «zero».
_PARTITA_NON_FATTURABILE = {
    "ddt_riga_id": 47,
    "ddt_id": 9,
    "ordine_riga_id": None,
    "origine": "NESSUNA",
    "fatturabile": False,
    "consegnato": "1.000000",
    "differenza": None,
    "stato": "NON_FATTURABILE",
    "sospetto_duplicato_ordine": False,
}


# Scopo: Costruisce un repository finto con le quattro letture del pannello.
def _repo_finto(**override: object) -> MagicMock:
    repo = MagicMock()
    repo.exists_ordine.return_value = True
    repo.exists_ddt.return_value = True
    repo.list_situazione_merce_ordine.return_value = [dict(_RIGA_MAI_SPEDITA)]
    repo.list_partite_merce.return_value = [dict(_PARTITA_NON_FATTURABILE)]
    repo.list_situazione_merce_accrediti.return_value = []
    repo.list_situazione_merce_riconsegne.return_value = []
    for nome, valore in override.items():
        getattr(repo, nome).return_value = valore
    return repo


class SituazioneMerceServiceTests(TestCase):
    # Scopo: Sul lato ordine escono tutte e quattro le sezioni e OGNI lettura
    #        e' filtrata per ordine (mai per DDT).
    def test_ordine_quattro_sezioni_e_filtro_per_ordine(self):
        repo = _repo_finto()
        with patch(
            "apps.vendite.services.vendite_service.VenditeRepository",
            return_value=repo,
        ):
            out = get_situazione_merce(ordine_id=42)

        self.assertEqual(
            sorted(out.keys()),
            ["accrediti", "contesto", "partite", "riconsegne", "righe_ordine"],
        )
        self.assertEqual(out["contesto"], "ORDINE_VENDITA")
        repo.list_situazione_merce_ordine.assert_called_once_with(
            ordine_id=42, ddt_id=None
        )
        repo.list_partite_merce.assert_called_once_with(ordine_id=42, ddt_id=None)
        repo.list_situazione_merce_accrediti.assert_called_once_with(
            ordine_id=42, ddt_id=None
        )
        repo.list_situazione_merce_riconsegne.assert_called_once_with(
            ordine_id=42, ddt_id=None
        )

    # Scopo: Sul DDT il livello 1 C'E' (rev 2026-08-19), ma filtrato sulla
    #        SPEDIZIONE: sono le righe d'ordine che quel DDT ha toccato, non
    #        quelle dell'ordine intero. Serve a leggere i due livelli insieme
    #        senza saltare da una schermata all'altra.
    # ⚠️ La cosa che questo test presidia e' il FILTRO, non la presenza: se
    #        `list_situazione_merce_ordine` venisse chiamata con `ordine_id`
    #        dedotto dalla partita, la sezione mostrerebbe TUTTE le righe di
    #        quell'ordine — comprese quelle che questa spedizione non ha mai
    #        toccato — e il pannello del DDT parlerebbe di merce altrui.
    def test_ddt_livello_uno_filtrato_sulla_spedizione(self):
        repo = _repo_finto()
        with patch(
            "apps.vendite.services.vendite_service.VenditeRepository",
            return_value=repo,
        ):
            out = get_situazione_merce(ddt_id=7)

        self.assertEqual(out["contesto"], "DDT_VENDITA")
        repo.list_situazione_merce_ordine.assert_called_once_with(
            ordine_id=None, ddt_id=7
        )
        repo.list_partite_merce.assert_called_once_with(ordine_id=None, ddt_id=7)
        repo.list_situazione_merce_accrediti.assert_called_once_with(
            ordine_id=None, ddt_id=7
        )

    # Scopo: BE-3. `differenza = None` arriva al client come null. Un
    #        `COALESCE(..., 0)` qui rimetterebbe dentro i falsi allarmi che il
    #        cantiere della partita ha appena tolto: «da fatturare» su un conto
    #        visione e «da accreditare» su merce mai spedita.
    def test_differenza_null_non_diventa_zero(self):
        repo = _repo_finto()
        with patch(
            "apps.vendite.services.vendite_service.VenditeRepository",
            return_value=repo,
        ):
            out = get_situazione_merce(ordine_id=42)

        self.assertIsNone(out["righe_ordine"][0]["differenza"])
        self.assertIsNone(out["partite"][0]["differenza"])
        # E l'anticipo resta distinto dal saldo: non e' un accredito (FE-3).
        self.assertEqual(out["righe_ordine"][0]["fatturato_anticipato"], "2.000000")

    # Scopo: BE-2. Il verso del saldo e' gia' tradotto dalle viste: il service
    #        passa `stato` cosi' com'e'. Due traduzioni diventano due frasi
    #        diverse per lo stesso numero.
    def test_stato_non_viene_ri_tradotto(self):
        repo = _repo_finto()
        with patch(
            "apps.vendite.services.vendite_service.VenditeRepository",
            return_value=repo,
        ):
            out = get_situazione_merce(ordine_id=42)

        self.assertEqual(out["righe_ordine"][0]["stato"], "NON_SPEDITA")
        self.assertEqual(out["partite"][0]["stato"], "NON_FATTURABILE")

    # Scopo: Il cancello di perimetro. `vendite.ordini` ha la RLS, le righe no:
    #        senza questo passo un ordine fuori scope tornerebbe un pannello
    #        VUOTO — «non ho il permesso di saperlo» presentato come «non c'e'
    #        nulla da fare». Inesistente e fuori scope sono indistinguibili di
    #        proposito (no-leak).
    def test_ordine_fuori_scope_o_inesistente_not_found(self):
        repo = _repo_finto(exists_ordine=False)
        with patch(
            "apps.vendite.services.vendite_service.VenditeRepository",
            return_value=repo,
        ):
            with self.assertRaises(ServiceError) as ctx:
                get_situazione_merce(ordine_id=999)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    # Scopo: Gemello sul DDT.
    def test_ddt_fuori_scope_o_inesistente_not_found(self):
        repo = _repo_finto(exists_ddt=False)
        with patch(
            "apps.vendite.services.vendite_service.VenditeRepository",
            return_value=repo,
        ):
            with self.assertRaises(ServiceError) as ctx:
                get_situazione_merce(ddt_id=999)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    # Scopo: Nessun id → errore di programmazione, non una lista vuota. Senza
    #        filtro le letture restituirebbero TUTTE le partite del database.
    def test_nessun_id_indicato_validazione(self):
        with self.assertRaises(ServiceError) as ctx:
            get_situazione_merce()
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Due id insieme → idem. Il filtro sarebbe ambiguo.
    def test_entrambi_gli_id_indicati_validazione(self):
        with self.assertRaises(ServiceError) as ctx:
            get_situazione_merce(ordine_id=1, ddt_id=2)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: ⚠️ L'ORDINE conta, non solo la presenza del check. Se il perimetro
    #        si verificasse DOPO le letture, i dati sarebbero gia' stati letti
    #        (e con `security_invoker` non e' garantito che tornino vuoti su
    #        ogni percorso). Il 404 deve precedere qualunque lettura.
    def test_perimetro_verificato_prima_delle_letture(self):
        repo = _repo_finto(exists_ordine=False)
        with patch(
            "apps.vendite.services.vendite_service.VenditeRepository",
            return_value=repo,
        ):
            with self.assertRaises(ServiceError):
                get_situazione_merce(ordine_id=999)

        repo.list_situazione_merce_ordine.assert_not_called()
        repo.list_partite_merce.assert_not_called()
        repo.list_situazione_merce_accrediti.assert_not_called()
        repo.list_situazione_merce_riconsegne.assert_not_called()
