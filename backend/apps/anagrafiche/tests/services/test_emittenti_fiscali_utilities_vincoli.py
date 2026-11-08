# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari della traduzione dei vincoli DB di
#        anagrafiche.emittenti_fiscali_utilities (R-2 del brief fondo fattura).
#        Mock repo, no DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) CreaRecordVincoliTests.test_soglie_coppia_incompleta_da_codice_dedicato
2) CreaRecordVincoliTests.test_soglie_fuori_ordine_da_validazione
3) CreaRecordVincoliTests.test_duplicato_resta_duplicato
4) CreaRecordVincoliTests.test_vincolo_ignoto_non_diventa_un_duplicato
4b) CreaRecordVincoliTests.test_decimali_fuori_intervallo_nominano_il_campo
4c) CreaRecordVincoliTests.test_metodo_non_ammesso_nomina_il_campo
5) AggiornaRecordVincoliTests.test_update_traduce_le_soglie_incomplete
6) AggiornaRecordVincoliTests.test_update_ok_non_tocca_la_traduzione
"""

from unittest import TestCase
from unittest.mock import patch

from django.db import IntegrityError

from apps.core.services.service_errors import ServiceError

SVC_MOD = "apps.anagrafiche.services.emittenti_fiscali_service"

_PAYLOAD_OK = {
    "utility_id": 5,
    "arrotondamento_importi_dec": 2,
    "metodo_arrotondamento_importi": "HALF_UP",
    "minimo_soglia_min": -500,
    "minimo_soglia_max": None,
}


# Scopo: fabbrica un IntegrityError che nomina il vincolo violato come lo
#        nomina psycopg (il nome compare nel testo dell'eccezione).
def _integrity(constraint: str) -> IntegrityError:
    return IntegrityError(
        f'new row for relation "emittenti_fiscali_utilities" violates '
        f'check constraint "{constraint}"'
    )


class CreaRecordVincoliTests(TestCase):
    # Scopo: la coppia di soglie incompleta esce col SUO codice, non mascherata.
    #        ⚠️ E' il difetto che R-2 chiude: prima ogni IntegrityError della
    #        tabella passava da `create_with_dedup` e usciva come «esiste gia' un
    #        record per questa coppia» — un messaggio non povero ma FALSO.
    @patch(f"{SVC_MOD}.EmittentiFiscaliRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
    def test_soglie_coppia_incompleta_da_codice_dedicato(self, mock_repo_cls, _parent):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )

        svc = EmittentiFiscaliUtilitiesService()
        svc._parent._resolve_soggetto_ruolo_id = lambda _id: 11  # type: ignore[method-assign]
        mock_repo_cls.return_value.create_record.side_effect = _integrity(
            "chk_emittenti_fiscali_utilities_soglie_coppia"
        )

        with self.assertRaises(ServiceError) as ctx:
            svc.crea_record(7, dict(_PAYLOAD_OK))
        self.assertEqual(ctx.exception.code, "E_FONDO_SOGLIE_INCOMPLETE")

    # Scopo: il vincolo gemello (ordine min <= max) ha un messaggio suo e non si
    #        confonde con quello della coppia incompleta.
    @patch(f"{SVC_MOD}.EmittentiFiscaliRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
    def test_soglie_fuori_ordine_da_validazione(self, mock_repo_cls, _parent):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )

        svc = EmittentiFiscaliUtilitiesService()
        svc._parent._resolve_soggetto_ruolo_id = lambda _id: 11  # type: ignore[method-assign]
        mock_repo_cls.return_value.create_record.side_effect = _integrity(
            "chk_emittenti_fiscali_utilities_soglie"
        )

        with self.assertRaises(ServiceError) as ctx:
            svc.crea_record(7, dict(_PAYLOAD_OK))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn("minima", ctx.exception.message)

    # Scopo: il duplicato vero continua a uscire come duplicato (non-regressione
    #        del comportamento che `create_with_dedup` garantiva).
    @patch(f"{SVC_MOD}.EmittentiFiscaliRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
    def test_duplicato_resta_duplicato(self, mock_repo_cls, _parent):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )

        svc = EmittentiFiscaliUtilitiesService()
        svc._parent._resolve_soggetto_ruolo_id = lambda _id: 11  # type: ignore[method-assign]
        mock_repo_cls.return_value.create_record.side_effect = IntegrityError(
            'duplicate key value violates unique constraint '
            '"uq_emittenti_fiscali_utilities_emittente_utility"'
        )

        with self.assertRaises(ServiceError) as ctx:
            svc.crea_record(7, dict(_PAYLOAD_OK))
        self.assertEqual(ctx.exception.code, "E_ANAG_DUPLICATO")

    # Scopo: un vincolo non mappato cade sul fallback di VALIDAZIONE. Non e' un
    #        dettaglio: il ripiego precedente era «duplicato», cioe' diceva una
    #        cosa falsa su ogni violazione che non fosse la UNIQUE.
    #        ⚠️ Fino al 2026-10-31 l'esempio era il CHECK dei decimali, che da
    #        quel giorno e' mappato: qui serve un vincolo che la mappa NON
    #        conosce, e un nome inventato lo resta per costruzione.
    @patch(f"{SVC_MOD}.EmittentiFiscaliRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
    def test_vincolo_ignoto_non_diventa_un_duplicato(self, mock_repo_cls, _parent):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )

        svc = EmittentiFiscaliUtilitiesService()
        svc._parent._resolve_soggetto_ruolo_id = lambda _id: 11  # type: ignore[method-assign]
        mock_repo_cls.return_value.create_record.side_effect = _integrity(
            "chk_emittenti_fiscali_utilities_vincolo_che_non_esiste"
        )

        with self.assertRaises(ServiceError) as ctx:
            svc.crea_record(7, dict(_PAYLOAD_OK))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertNotEqual(ctx.exception.code, "E_ANAG_DUPLICATO")

    # Scopo: i decimali fuori dal CHECK escono col loro messaggio e nominano il
    #        CAMPO (2026-10-31: prima era il ripiego generico, che non diceva
    #        cosa correggere).
    @patch(f"{SVC_MOD}.EmittentiFiscaliRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
    def test_decimali_fuori_intervallo_nominano_il_campo(self, mock_repo_cls, _parent):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )

        svc = EmittentiFiscaliUtilitiesService()
        svc._parent._resolve_soggetto_ruolo_id = lambda _id: 11  # type: ignore[method-assign]
        mock_repo_cls.return_value.create_record.side_effect = _integrity(
            "chk_emittenti_fiscali_utilities_arrotondamento_dec"
        )

        with self.assertRaises(ServiceError) as ctx:
            svc.crea_record(7, dict(_PAYLOAD_OK))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn("Decimali", ctx.exception.message)
        self.assertEqual(ctx.exception.context.get("field"), "arrotondamento_importi_dec")

    # Scopo: stesso trattamento per il metodo di arrotondamento.
    @patch(f"{SVC_MOD}.EmittentiFiscaliRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
    def test_metodo_non_ammesso_nomina_il_campo(self, mock_repo_cls, _parent):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )

        svc = EmittentiFiscaliUtilitiesService()
        svc._parent._resolve_soggetto_ruolo_id = lambda _id: 11  # type: ignore[method-assign]
        mock_repo_cls.return_value.create_record.side_effect = _integrity(
            "chk_emittenti_fiscali_utilities_metodo_arrotondamento"
        )

        with self.assertRaises(ServiceError) as ctx:
            svc.crea_record(7, dict(_PAYLOAD_OK))
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertEqual(ctx.exception.context.get("field"), "metodo_arrotondamento_importi")


class AggiornaRecordVincoliTests(TestCase):
    # Scopo: la traduzione vale anche in UPDATE, che prima non catturava NIENTE
    #        (la stessa violazione diventava un 500).
    #        ⚠️ Ed e' il percorso in cui il CHECK e' l'unica autorita' possibile:
    #        l'update e' un delta, quindi la coppia di soglie effettiva nasce
    #        dall'unione del payload con la riga gia' a database — nessuna guard
    #        Python sul solo payload potrebbe deciderlo.
    @patch(f"{SVC_MOD}._verify_record_ownership")
    @patch(f"{SVC_MOD}.EmittentiFiscaliRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
    def test_update_traduce_le_soglie_incomplete(self, mock_repo_cls, _parent, _own):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )

        svc = EmittentiFiscaliUtilitiesService()
        mock_repo_cls.return_value.update_record.side_effect = _integrity(
            "chk_emittenti_fiscali_utilities_soglie_coppia"
        )

        with self.assertRaises(ServiceError) as ctx:
            svc.aggiorna_record(7, 3, {"minimo_soglia_max": None})
        self.assertEqual(ctx.exception.code, "E_FONDO_SOGLIE_INCOMPLETE")

    # Scopo: percorso felice invariato — il context manager non cambia l'esito.
    @patch(f"{SVC_MOD}._verify_record_ownership")
    @patch(f"{SVC_MOD}.EmittentiFiscaliRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
    def test_update_ok_non_tocca_la_traduzione(self, mock_repo_cls, _parent, _own):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )

        svc = EmittentiFiscaliUtilitiesService()
        mock_repo_cls.return_value.update_record.return_value = True

        result = svc.aggiorna_record(7, 3, {"minimo_soglia_min": -500})
        self.assertEqual(result, {"updated": True})
