# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Unit test del service del documento interno (repository mockato):
#        la validazione del payload, il vocabolario degli stati, il 404 PRIMA
#        del satellite, l'envelope delle liste, la configurazione delle due
#        famiglie — cio' che sta in Python e non nel database.
# Note: `SimpleTestCase`: il database e' VIETATO. Cio' che passa dal database
#       (guard, posting, piano) sta in `tests/db/`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
 1) FamiglieTests.test_le_due_famiglie_dichiarano_le_tre_differenze
 2) FamiglieTests.test_gli_identificatori_passano_dalla_regex
 3) ListaTests.test_envelope_offset_based
 4) ListaTests.test_ordinamento_fuori_whitelist_rifiutato
 5) ListaTests.test_stato_fuori_vocabolario_rifiutato
 6) ListaTests.test_senza_ordinamento_decide_il_repository
 7) DettaglioTests.test_404_prima_del_piano
 8) DettaglioTests.test_il_riepilogo_del_piano_solo_sull_inventario
 9) DettaglioTests.test_capabilities_non_si_fingono
10) ScritturaTests.test_crea_richiede_il_magazzino
11) ScritturaTests.test_crea_rifiuta_la_descrizione_sulla_rettifica
12) ScritturaTests.test_crea_magazzino_non_visibile_400_col_campo
13) ScritturaTests.test_patch_esclude_il_magazzino
14) ScritturaTests.test_stato_richiedibile_solo_dal_vocabolario
15) ScritturaTests.test_registra_legge_prima_la_testata
16) RigheTests.test_la_quantita_e_obbligatoria_e_col_nome_della_famiglia
17) RigheTests.test_la_quantita_rifiuta_bool_nan_e_testo
18) RigheTests.test_null_azzera_un_nullable_nel_patch
19) RigheTests.test_il_motivo_solo_sulla_rettifica
20) RigheTests.test_riga_di_un_altro_documento_404
21) RigheTests.test_il_piano_solo_sull_inventario
22) ArticoloUuidTests.test_un_articolo_che_non_e_un_uuid_e_un_400_col_campo — 2026-09-18: i lookup e i motivi, non un DataError
23) ArticoloUuidTests.test_un_filtro_articolo_malformato_e_un_400_col_campo — idem sulle tre liste di consultazione
24) ArticoloUuidTests.test_l_uuid_arriva_canonico_al_repository
25) ContrattoDalDbTests.test_meta_non_e_piu_nel_contratto — R-2: le colonne dei verbi non lo portano
26) ContrattoDalDbTests.test_la_provenienza_non_e_un_dato_dell_operatore — D-M11: ammessa dal DB, tolta per nome
27) ContrattoDalDbTests.test_una_chiave_del_db_che_nessuno_legge_e_un_500 — mai uno scarto silenzioso
28) ContrattoDalDbTests.test_la_descrizione_ha_la_lunghezza_della_colonna — varchar(255), non un 22001
29) FamiglieTests.test_il_codice_della_famiglia_del_db_passa_dalla_regex
30) ContrattoDalDbTests.test_il_motivo_ha_la_lunghezza_della_colonna — varchar(64)
"""

from decimal import Decimal
from unittest.mock import create_autospec, patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.magazzino.db.famiglie import FAMIGLIE, FamigliaDocumentoInterno
from apps.magazzino.db.magazzino_repository import MagazzinoRepository
from apps.magazzino.services import consultazione_service as cons
from apps.magazzino.services import magazzino_service as svc

_ART = "019bbee2-5f6a-704f-bbd0-34ed84db252d"

_DOC = {
    "id": 7, "uid": "u", "data": "2026-09-18", "stato": "DRAFT", "magazzino_id": 3,
    "magazzino_codice": "MAG-A", "magazzino_descrizione": "Centrale",
    "magazzino_usa_ubicazioni": False, "descrizione": None, "righe_count": 0,
    "sorgente_tipo_id": None, "sorgente_id": None, "sorgente_riga": None, "sorgente_uid": None, "meta": {},
    "data_insert": "x", "user_insert": "u", "data_update": "x", "user_update": None,
}
_RIGA = {"id": 11, "inventario_id": 7, "articolo_id": _ART, "qta_contata": Decimal("10")}
# Le liste del DB (`fn_documento_interno_colonne_ammesse`), lette il
# 2026-11-23: qui sono un FINTO del repository. Che coincidano con il DB vero
# lo prova `tests/db/test_documento_interno_db.py`.
_AMMESSE = {
    ("INVENTARIO", "testata", "crea"): {"data", "descrizione", "sorgente_tipo_id", "sorgente_id", "sorgente_uid", "sorgente_riga"},
    ("INVENTARIO", "testata", "modifica"): {"data", "descrizione"},
    ("INVENTARIO", "riga", "crea"): {"articolo_id", "qta_contata", "ubicazione_id", "lotto_id", "asset_id", "costo_unitario"},
    ("INVENTARIO", "riga", "modifica"): {"articolo_id", "qta_contata", "ubicazione_id", "lotto_id", "asset_id", "costo_unitario"},
    ("RETTIFICA", "testata", "crea"): {"data", "sorgente_tipo_id", "sorgente_id", "sorgente_uid", "sorgente_riga"},
    ("RETTIFICA", "testata", "modifica"): {"data"},
    ("RETTIFICA", "riga", "crea"): {"articolo_id", "qta_delta", "motivo", "ubicazione_id", "lotto_id", "asset_id", "costo_unitario"},
    ("RETTIFICA", "riga", "modifica"): {"articolo_id", "qta_delta", "motivo", "ubicazione_id", "lotto_id", "asset_id", "costo_unitario"},
}


def _ammesse(f: FamigliaDocumentoInterno, parte: str, gesto: str) -> frozenset[str]:
    return frozenset(_AMMESSE[(f.famiglia_db, parte, gesto)])


_RIEPILOGO = {"n_righe": 1, "n_con_delta": 1, "n_invariate": 0, "n_non_contate": 0, "n_non_postabili": 0}


class _ConRepo(SimpleTestCase):
    def setUp(self) -> None:
        # Il finto dal repository vero: un metodo che non c'e' e' un errore.
        self.repo = create_autospec(MagazzinoRepository, instance=True)
        self.repo.get_documento.return_value = dict(_DOC)
        self.repo.get_magazzino.return_value = {"id": 3, "codice": "MAG-A", "usa_ubicazioni": False}
        self.repo.piano_riepilogo.return_value = dict(_RIEPILOGO)
        self.repo.get_riga.return_value = dict(_RIGA)
        self.repo.list_documenti.return_value = ([dict(_DOC)], 1)
        self.repo.list_righe.return_value = ([dict(_RIGA)], 1)
        self.repo.list_piano.return_value = ([], 0)
        self.repo.create_documento.return_value = 7
        self.repo.create_riga.return_value = 11
        self.repo.colonne_ammesse.side_effect = _ammesse
        self.repo.update_documento.return_value = {"id": 7}
        self.repo.set_stato_documento.return_value = "CONFIRM"
        self.repo.update_riga.return_value = {"id": 11}
        self.repo.posta_documento.return_value = [{"movimento_id": 1, "riga_id": 11, "qta": Decimal("10")}]
        patcher = patch.object(svc, "MagazzinoRepository", autospec=True, return_value=self.repo)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _rifiuto(self, fn) -> ServiceError:
        with self.assertRaises(ServiceError) as ctx:
            fn()
        return ctx.exception


class FamiglieTests(SimpleTestCase):
    # Scopo: Q-1 — le due configurazioni differiscono SOLO per le tre cose
    #        di dato (quantita', piano, sorgente) e per cio' che ne discende.
    def test_le_due_famiglie_dichiarano_le_tre_differenze(self):
        inv, rett = FAMIGLIE["inventari"], FAMIGLIE["rettifiche"]
        self.assertEqual((inv.col_qta, rett.col_qta), ("qta_contata", "qta_delta"))
        self.assertEqual((inv.ha_piano, rett.ha_piano), (True, False))
        self.assertEqual((inv.sorgente_codice_interno, rett.sorgente_codice_interno),
                         ("INVENTARIO", "RETTIFICA"))
        self.assertEqual((inv.con_motivo, rett.con_motivo), (False, True))
        self.assertEqual((inv.ha_descrizione, rett.ha_descrizione), (True, False))
        self.assertEqual(inv.guard_riga_uniq, "uq_mag_inventari_righe_posizione")
        self.assertIsNone(rett.guard_riga_uniq)
        # ⭐ R-1: l'INVOLUCRO della famiglia, non il corpo parametrico — la
        # famiglia la sa gia' lui, e un valore in meno da passare e' un valore
        # in meno da sbagliare.
        self.assertEqual(
            (inv.fn_capability, rett.fn_capability),
            ("script.fn_available_actions_inventario", "script.fn_available_actions_rettifica"),
        )

    # Scopo: un refuso in un identificatore si ferma all'import, non in una query.
    def test_gli_identificatori_passano_dalla_regex(self):
        with self.assertRaises(ValueError):
            FamigliaDocumentoInterno(
                codice="x", singolare="x", tabella="magazzino.inventari; DROP",
                tabella_righe="magazzino.inventari_righe", fk_riga="inventario_id",
                col_stato="stato_mag_inventario", fn_posta="magazzino.fn_posta_inventario",
                famiglia_db="INVENTARIO", fn_aggiungi="magazzino.fn_aggiungi_inventario",
                fn_aggiungi_riga="magazzino.fn_aggiungi_riga_inventario",
                fn_capability="script.fn_available_actions_inventario",
                sorgente_codice_interno="X", lista_codice="x", lista_righe_codice="x",
                col_qta="qta_contata", ha_piano=True, ha_descrizione=True, con_motivo=False,
                guard_riga_uniq=None,
            )

    # Scopo: R-2 — il codice della famiglia nel registro del DB viaggia come
    #        valore; un refuso darebbe `E_PERMESSO_NEGATO` a ogni scrittura
    #        (il registro e' fail-closed), e si ferma all'import.
    def test_il_codice_della_famiglia_del_db_passa_dalla_regex(self):
        self.assertEqual(
            (FAMIGLIE["inventari"].famiglia_db, FAMIGLIE["rettifiche"].famiglia_db),
            ("INVENTARIO", "RETTIFICA"),
        )
        with self.assertRaises(ValueError):
            FamigliaDocumentoInterno(
                codice="x", singolare="x", tabella="magazzino.inventari",
                tabella_righe="magazzino.inventari_righe", fk_riga="inventario_id",
                col_stato="stato_mag_inventario", fn_posta="magazzino.fn_posta_inventario",
                famiglia_db="inventario", fn_aggiungi="magazzino.fn_aggiungi_inventario",
                fn_aggiungi_riga="magazzino.fn_aggiungi_riga_inventario",
                fn_capability="script.fn_available_actions_inventario",
                sorgente_codice_interno="X", lista_codice="x", lista_righe_codice="x",
                col_qta="qta_contata", ha_piano=True, ha_descrizione=True, con_motivo=False,
                guard_riga_uniq=None,
            )


class ListaTests(_ConRepo):
    def test_envelope_offset_based(self):
        esito = svc.list_documenti("inventari", auth_user_id=5, limit=25, offset=50)
        self.assertEqual(set(esito), {"count", "results"})
        self.assertEqual(esito["count"], 1)
        kwargs = self.repo.list_documenti.call_args.kwargs
        self.assertEqual((kwargs["limit"], kwargs["offset"], kwargs["auth_user_id"]), (25, 50, 5))

    def test_ordinamento_fuori_whitelist_rifiutato(self):
        e = self._rifiuto(lambda: svc.list_documenti("inventari", auth_user_id=None, limit=25, order_by="colonna_x"))
        self.assertEqual(e.code, svc.E_VALIDAZIONE)
        self.repo.list_documenti.assert_not_called()

    def test_stato_fuori_vocabolario_rifiutato(self):
        e = self._rifiuto(lambda: svc.list_documenti("inventari", auth_user_id=None, limit=25, stato="BOZZA"))
        self.assertEqual(e.code, svc.E_VALIDAZIONE)

    def test_senza_ordinamento_decide_il_repository(self):
        svc.list_documenti("rettifiche", auth_user_id=None, limit=25)
        kwargs = self.repo.list_documenti.call_args.kwargs
        self.assertIsNone(kwargs["order_by"])
        self.assertIsNone(kwargs["order_dir"])
        self.assertEqual(self.repo.list_documenti.call_args.args[0], FAMIGLIE["rettifiche"])


class DettaglioTests(_ConRepo):
    # Scopo: fuori scope e' un 404, e il piano non si legge nemmeno.
    def test_404_prima_del_piano(self):
        self.repo.get_documento.return_value = None
        e = self._rifiuto(lambda: svc.get_documento("inventari", 99))
        self.assertEqual(e.code, "E_MAG_DOCUMENTO_NON_TROVATO")
        self.repo.piano_riepilogo.assert_not_called()

    def test_il_riepilogo_del_piano_solo_sull_inventario(self):
        inv = svc.get_documento("inventari", 7)
        self.assertEqual(inv["piano_riepilogo"]["n_con_delta"], 1)
        self.assertEqual(inv["famiglia"], "inventari")
        rett = svc.get_documento("rettifiche", 7)
        self.assertNotIn("piano_riepilogo", rett)

    # Scopo: R-1 — il blob della capability viaggia INTATTO, e `stato_info_key`
    #        viene da li'. ⛔ Il backend trasporta, non deduce (api.md
    #        §Capability): se una chiave del blob venisse ricalcolata qui,
    #        sarebbe la seconda sede della matrice del guard.
    def test_capabilities_trasportate_intatte(self):
        blob = {
            "stato_codice": "CONFIRM",
            "available_actions": [{"key": "annulla", "target_state": "CANCEL"}],
            "can_change_state": True,
            "can_edit_testata": False,
            "can_edit_righe": False,
            "can_delete": False,
            "can_registra": False,
            "can_registra_reason": "DOCUMENTO_SENZA_RIGHE",
            "can_registra_reason_key": "magazzino.documenti_interni.registra_reason.senza_righe",
            "stato_info_key": None,
        }
        self.repo.get_capabilities.return_value = blob
        d = svc.get_documento("inventari", 7)
        self.assertEqual(d["capabilities"], blob)
        self.assertEqual(self.repo.get_capabilities.call_args.args[0], FAMIGLIE["inventari"])

    # Scopo: `stato_info_key` sta SOLO nel blob — fino al 2026-09-23 era
    #        copiata anche in cima al documento, una lettura piatta con due
    #        sedi (api.md §«Il blob sta SOTTO `capabilities`»). Il drawer la
    #        legge da `capabilities`, e nessuna chiave del blob sale di livello.
    def test_stato_info_key_solo_nel_blob(self):
        self.repo.get_capabilities.return_value = {
            "stato_codice": "POSTED",
            "stato_info_key": "magazzino.documenti_interni.stato_info.posted",
        }
        d = svc.get_documento("inventari", 7)
        self.assertEqual(
            d["capabilities"]["stato_info_key"], "magazzino.documenti_interni.stato_info.posted",
        )
        self.assertNotIn("stato_info_key", d)

    # Scopo: un documento fuori perimetro e' un 404 sulla TESTATA, e la
    #        capability non si chiama nemmeno (una capability non solleva).
    def test_404_prima_della_capability(self):
        self.repo.get_documento.return_value = None
        self._rifiuto(lambda: svc.get_documento("inventari", 99))
        self.repo.get_capabilities.assert_not_called()


class ScritturaTests(_ConRepo):
    def test_crea_richiede_il_magazzino(self):
        e = self._rifiuto(lambda: svc.crea_documento("inventari", {"descrizione": "x"}))
        self.assertEqual(e.code, svc.E_VALIDAZIONE)
        self.assertEqual(e.context.get("field"), "magazzino_id")

    def test_crea_rifiuta_la_descrizione_sulla_rettifica(self):
        e = self._rifiuto(lambda: svc.crea_documento("rettifiche", {"magazzino_id": 3, "descrizione": "x"}))
        self.assertEqual(e.code, svc.E_VALIDAZIONE)
        self.repo.create_documento.assert_not_called()

    def test_crea_magazzino_non_visibile_400_col_campo(self):
        self.repo.get_magazzino.return_value = None
        e = self._rifiuto(lambda: svc.crea_documento("inventari", {"magazzino_id": 3}))
        self.assertEqual((e.code, e.context.get("field")), (svc.E_VALIDAZIONE, "magazzino_id"))
        self.repo.create_documento.assert_not_called()

    # Scopo: il magazzino si sceglie alla nascita e basta.
    def test_patch_esclude_il_magazzino(self):
        e = self._rifiuto(lambda: svc.aggiorna_documento("inventari", 7, {"magazzino_id": 4}))
        self.assertEqual(e.code, svc.E_VALIDAZIONE)
        self.repo.update_documento.assert_not_called()
        svc.aggiorna_documento("inventari", 7, {"descrizione": None, "data": "2026-09-01"})
        campi = self.repo.update_documento.call_args.args[2]
        self.assertEqual(set(campi), {"descrizione", "data"})
        self.assertIsNone(campi["descrizione"])

    def test_stato_richiedibile_solo_dal_vocabolario(self):
        for stato in ("POSTED", "BOZZA", ""):
            e = self._rifiuto(lambda s=stato: svc.cambia_stato_documento("inventari", 7, {"stato": s}))
            self.assertEqual(e.code, svc.E_VALIDAZIONE)
        self.repo.set_stato_documento.assert_not_called()
        svc.cambia_stato_documento("inventari", 7, {"stato": "confirm"})
        self.repo.set_stato_documento.assert_called_once_with(FAMIGLIE["inventari"], 7, "CONFIRM")

    def test_registra_legge_prima_la_testata(self):
        esito = svc.registra_documento("inventari", 7)
        self.assertEqual(esito["n_movimenti"], 1)
        self.assertEqual(esito["documento"]["id"], 7)
        self.repo.posta_documento.assert_called_once_with(FAMIGLIE["inventari"], 7)
        self.repo.get_documento.return_value = None
        e = self._rifiuto(lambda: svc.registra_documento("inventari", 99))
        self.assertEqual(e.code, "E_MAG_DOCUMENTO_NON_TROVATO")
        self.repo.posta_documento.assert_called_once()


class RigheTests(_ConRepo):
    def test_la_quantita_e_obbligatoria_e_col_nome_della_famiglia(self):
        e = self._rifiuto(lambda: svc.crea_riga("inventari", 7, {"articolo_id": _ART}))
        self.assertEqual(e.context.get("field"), "qta_contata")
        # Il nome dell'altra famiglia non e' una chiave ammessa.
        e = self._rifiuto(lambda: svc.crea_riga("inventari", 7, {"articolo_id": _ART, "qta_delta": 1}))
        self.assertEqual(e.code, svc.E_VALIDAZIONE)
        svc.crea_riga("rettifiche", 7, {"articolo_id": _ART, "qta_delta": "-2.5"})
        # Articolo e quantita' sono ARGOMENTI del verbo, non campi.
        kwargs = self.repo.create_riga.call_args.kwargs
        self.assertEqual(kwargs["qta"], Decimal("-2.5"))
        self.assertEqual(kwargs["articolo_id"], _ART)
        self.assertEqual(kwargs["campi"], {})

    def test_la_quantita_rifiuta_bool_nan_e_testo(self):
        for raw in (True, "NaN", "dieci"):
            e = self._rifiuto(lambda r=raw: svc.crea_riga("inventari", 7, {"articolo_id": _ART, "qta_contata": r}))
            self.assertEqual((e.code, e.context.get("field")), (svc.E_VALIDAZIONE, "qta_contata"))

    # Scopo: `null` esplicito AZZERA (togliere il lotto); chiave assente non tocca.
    def test_null_azzera_un_nullable_nel_patch(self):
        svc.aggiorna_riga("inventari", 7, 11, {"lotto_id": None, "costo_unitario": None})
        campi = self.repo.update_riga.call_args.args[3]
        self.assertEqual(campi, {"lotto_id": None, "costo_unitario": None})
        e = self._rifiuto(lambda: svc.aggiorna_riga("inventari", 7, 11, {}))
        self.assertEqual(e.code, svc.E_VALIDAZIONE)

    def test_il_motivo_solo_sulla_rettifica(self):
        e = self._rifiuto(lambda: svc.crea_riga("inventari", 7, {"articolo_id": _ART, "qta_contata": 1, "motivo": "x"}))
        self.assertEqual(e.code, svc.E_VALIDAZIONE)
        svc.crea_riga("rettifiche", 7, {"articolo_id": _ART, "qta_delta": 1, "motivo": "ROTTURA"})
        self.assertEqual(self.repo.create_riga.call_args.kwargs["campi"], {"motivo": "ROTTURA"})

    # ⭐ R-7: codice SUO dal 2026-09-23 — la risposta resta un 404 identico,
    #    ma dice QUALE delle due cose manca (il documento o la riga).
    def test_riga_di_un_altro_documento_404(self):
        self.repo.get_riga.return_value = None
        e = self._rifiuto(lambda: svc.aggiorna_riga("inventari", 7, 11, {"qta_contata": 1}))
        self.assertEqual(e.code, "E_MAG_DOCUMENTO_RIGA_NON_TROVATA")
        self.repo.update_riga.assert_not_called()
        self.repo.get_riga.assert_called_with(FAMIGLIE["inventari"], 7, 11)

    def test_il_piano_solo_sull_inventario(self):
        svc.list_piano("inventari", 7, limit=10)
        self.repo.list_piano.assert_called_once()
        e = self._rifiuto(lambda: svc.list_piano("rettifiche", 7, limit=10))
        self.assertEqual(e.code, svc.E_VALIDAZIONE)


class ArticoloUuidTests(_ConRepo):
    """`articolo_id` finisce in `%s::uuid` nelle SQL: un valore che non e' un
    UUID deve fermarsi QUI con un 400 col campo, non arrivare a PostgreSQL come
    `DataError` (un 500 su un parametro che il contratto dichiara ammesso)."""

    def setUp(self) -> None:
        super().setUp()
        self.repo.lookup_lotti.return_value = []
        self.repo.lookup_assets.return_value = []
        self.repo.check_riga.return_value = []
        self.repo.list_blocchi.return_value = []
        self.repo.list_disponibilita.return_value = ([], 0)
        self.repo.list_disponibilita_articoli.return_value = ([], 0)
        self.repo.list_movimenti.return_value = ([], 0)
        patcher = patch.object(cons, "MagazzinoRepository", autospec=True, return_value=self.repo)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_un_articolo_che_non_e_un_uuid_e_un_400_col_campo(self):
        chiamate = (
            lambda: svc.lookup_lotti(articolo_id="abc", magazzino_id=3, search=None),
            lambda: svc.lookup_assets(articolo_id="abc", magazzino_id=3),
            lambda: svc.motivi_riga(
                magazzino_id=3, articolo_id="", lotto_id=None, asset_id=None, ubicazione_id=None,
            ),
            lambda: cons.list_blocchi(articolo_id="abc", magazzino_id=3),
        )
        for chiama in chiamate:
            e = self._rifiuto(chiama)
            self.assertEqual(e.code, svc.E_VALIDAZIONE)
            self.assertEqual(e.context["field"], "articolo_id")
        self.repo.lookup_lotti.assert_not_called()
        self.repo.lookup_assets.assert_not_called()
        self.repo.check_riga.assert_not_called()
        self.repo.list_blocchi.assert_not_called()

    def test_un_filtro_articolo_malformato_e_un_400_col_campo(self):
        chiamate = (
            lambda: cons.list_disponibilita(auth_user_id=None, articolo_id="abc", limit=10),
            lambda: cons.list_disponibilita_articoli(articolo_id="abc", limit=10),
            lambda: cons.list_movimenti(auth_user_id=None, articolo_id="abc", limit=10),
        )
        for chiama in chiamate:
            e = self._rifiuto(chiama)
            self.assertEqual(e.code, svc.E_VALIDAZIONE)
            self.assertEqual(e.context["field"], "articolo_id")
        # Assente resta assente: nessun filtro, nessun rifiuto.
        cons.list_movimenti(auth_user_id=None, articolo_id=None, limit=10)
        self.assertIsNone(self.repo.list_movimenti.call_args.kwargs["articolo_id"])

    def test_l_uuid_arriva_canonico_al_repository(self):
        svc.lookup_lotti(articolo_id=_ART.upper(), magazzino_id=3, search="L-")
        self.repo.lookup_lotti.assert_called_once_with(_ART, 3, "L-")


# ⭐ R-2 di brief-db-magazzino-tutte-le-scritture-dal-verbo: le chiavi del
#    payload le dice il DB (`fn_documento_interno_colonne_ammesse`), il
#    trasporto di ognuna lo dice il service.
class ContrattoDalDbTests(_ConRepo):
    # Scopo: `meta` non e' fra le colonne dei verbi: un 400, non un campo
    #        scartato o un `E_CAMPO_NON_AMMESSO` del DB.
    def test_meta_non_e_piu_nel_contratto(self):
        for fn in (
            lambda: svc.crea_documento("inventari", {"magazzino_id": 3, "meta": {}}),
            lambda: svc.aggiorna_documento("inventari", 7, {"meta": {}}),
            lambda: svc.crea_riga("inventari", 7, {"articolo_id": _ART, "qta_contata": 1, "meta": {}}),
            lambda: svc.aggiorna_riga("inventari", 7, 11, {"meta": {}}),
        ):
            e = self._rifiuto(fn)
            self.assertEqual(e.code, svc.E_VALIDAZIONE)
        self.repo.create_documento.assert_not_called()
        self.repo.update_documento.assert_not_called()
        self.repo.create_riga.assert_not_called()
        self.repo.update_riga.assert_not_called()

    # Scopo: D-M11 — il DB ammette la provenienza alla nascita, ma la scrive chi
    #        fa nascere il documento da un altro, non l'operatore dal form.
    def test_la_provenienza_non_e_un_dato_dell_operatore(self):
        e = self._rifiuto(lambda: svc.crea_documento("inventari", {"magazzino_id": 3, "sorgente_id": 5}))
        self.assertEqual(e.code, svc.E_VALIDAZIONE)
        self.repo.create_documento.assert_not_called()
        svc.crea_documento("inventari", {"magazzino_id": 3, "data": "2026-09-01", "descrizione": "Conta"})
        kwargs = self.repo.create_documento.call_args.kwargs
        self.assertEqual(kwargs["magazzino_id"], 3)
        self.assertEqual(set(kwargs["campi"]), {"data", "descrizione"})

    # Scopo: una colonna che il DB ammette e che qui nessuno sa leggere e' un
    #        difetto del backend (500), non una chiave scartata in silenzio.
    def test_una_chiave_del_db_che_nessuno_legge_e_un_500(self):
        self.repo.colonne_ammesse.side_effect = lambda f, parte, gesto: _ammesse(f, parte, gesto) | {"nuova"}
        with self.assertRaises(RuntimeError):
            svc.aggiorna_documento("inventari", 7, {"data": "2026-09-01"})
        self.repo.update_documento.assert_not_called()

    def test_la_descrizione_ha_la_lunghezza_della_colonna(self):
        e = self._rifiuto(lambda: svc.aggiorna_documento("inventari", 7, {"descrizione": "x" * 256}))
        self.assertEqual((e.code, e.context.get("field")), (svc.E_VALIDAZIONE, "descrizione"))
        svc.aggiorna_documento("inventari", 7, {"descrizione": "x" * 255})
        self.repo.update_documento.assert_called_once()

    # Scopo: `rettifiche_righe.motivo` e' varchar(64): oltre, un 400 col campo.
    def test_il_motivo_ha_la_lunghezza_della_colonna(self):
        e = self._rifiuto(lambda: svc.aggiorna_riga("rettifiche", 7, 11, {"motivo": "x" * 65}))
        self.assertEqual((e.code, e.context.get("field")), (svc.E_VALIDAZIONE, "motivo"))
        svc.aggiorna_riga("rettifiche", 7, 11, {"motivo": "x" * 64})
        self.repo.update_riga.assert_called_once()
