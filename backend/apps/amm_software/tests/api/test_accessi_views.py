# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'area «Accessi» sul percorso client -> middleware -> DRF -> view ->
#        servizio (brief-db-be-fe-area-accessi): forma della risposta delle
#        due liste, vocabolari dei filtri rifiutati con un 400, capability del
#        blocco, `Idempotency-Key` sui due verbi, sessioni chiuse col blocco.
#        Finti: il repository, la revoca dei token, la transazione.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_altri_envelope_paginato_e_filtri_al_repository
 2) test_altri_vocabolario_estraneo_e_un_400 — mai una lista vuota che sembra un dato
 3) test_altri_disabilitato_non_e_una_veste — la voce storica non e' un filtro
 4) test_sistema_envelope_e_tipo_validato
 5) test_credenziale_capability_del_blocco — ultimo SUPER_ADMIN: spento col motivo
 6) test_credenziale_inesistente_404
 7) test_blocca_vuole_l_idempotency_key
 8) test_blocca_chiude_le_sessioni_e_rilegge
 9) test_sblocca_non_tocca_le_sessioni
10) test_vecchia_rotta_del_secondo_fattore_ritirata
"""

from unittest.mock import MagicMock, patch

from django.test import Client, override_settings

from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_SERVIZIO = "apps.amm_software.services.accessi_service"
_CRED = {
    "auth_user_id": 7, "username": "cliente7", "email": None, "categoria": "ALTRO",
    "bloccata": False, "bloccata_dal": None, "bloccata_da": None, "motivo_blocco": None,
    "ultimo_super_admin": False,
}


# Idempotenza forte OFF deterministica: blocca e sblocca vogliono la chiave, e
# con DJANGO_API_STRONG_IDEMPOTENCY_ENABLED=1 nell'ambiente il claim colpirebbe
# il DB (vietato in SimpleTestCase) → 500 finti.
@override_settings(API_STRONG_IDEMPOTENCY_ENABLED=False)
class _Base(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        self.user = MagicMock(id=42, is_authenticated=True, is_superuser=False)
        for target, valore in (
            ("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", (self.user, None)),
            ("apps.core.api.permissions.IsAdminZeroERP.has_permission", True),
        ):
            p = patch(target, return_value=valore)
            p.start()
            self.addCleanup(p.stop)
        repo = patch(f"{_SERVIZIO}.AccessiRepository")
        self.repo = repo.start().return_value
        self.addCleanup(repo.stop)
        self.repo.get_credenziale.side_effect = lambda _uid: dict(_CRED)
        for nome, attr in (("blocca_token_sessioni", "revoca"), ("invalidate_user", "invalida"),
                           ("transaction", "tx")):
            p = patch(f"{_SERVIZIO}.{nome}")
            setattr(self, attr, p.start())
            self.addCleanup(p.stop)

    def _post(self, url: str, corpo: dict | None = None, *, chiave: str | None = "k-1"):
        headers = {"HTTP_IDEMPOTENCY_KEY": chiave} if chiave else {}
        return self.client.post(url, corpo or {}, content_type="application/json", **headers)


class AccessiListeTests(_Base):
    def test_altri_envelope_paginato_e_filtri_al_repository(self):
        self.repo.list_accessi_altri.return_value = ([{"auth_user_id": 7, "vesti": []}], 31)
        resp = self.client.get(
            "/api/v1/amm-software/accessi/altri/",
            {"ruolo_applicativo": "shop_customer", "stato_accesso": "pending",
             "nessun_accesso": "false", "bloccata": "true", "limit": "10", "offset": "20",
             "order_by": "ultimo_accesso", "order_dir": "desc"},
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()["data"]
        self.assertEqual((data["count"], len(data["results"])), (31, 1))
        kw = self.repo.list_accessi_altri.call_args.kwargs
        self.assertEqual(kw["ruolo_applicativo"], "SHOP_CUSTOMER")
        self.assertEqual(kw["stato_accesso"], "PENDING")
        self.assertIs(kw["nessun_accesso"], False)
        self.assertIs(kw["bloccata"], True)
        self.assertEqual((kw["limit"], kw["offset"]), (10, 20))
        self.assertEqual((kw["order_by"], kw["order_dir"]), ("ultimo_accesso", "desc"))

    def test_altri_vocabolario_estraneo_e_un_400(self):
        for param, valore in (("stato_accesso", "ATTIVA"), ("secondo_fattore_stato", "SI"),
                              ("nessun_accesso", "forse")):
            with self.subTest(param=param):
                resp = self.client.get("/api/v1/amm-software/accessi/altri/", {param: valore})
                self.assertEqual(resp.status_code, 400, resp.content)
        self.repo.list_accessi_altri.assert_not_called()

    def test_altri_disabilitato_non_e_una_veste(self):
        resp = self.client.get("/api/v1/amm-software/accessi/altri/", {"ruolo_applicativo": "DISABILITATO"})
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_sistema_envelope_e_tipo_validato(self):
        self.repo.list_accessi_sistema.return_value = ([], 0)
        ok = self.client.get("/api/v1/amm-software/accessi/sistema/", {"tipo": "processo", "emittente_fiscale_id": "3"})
        self.assertEqual(ok.status_code, 200, ok.content)
        kw = self.repo.list_accessi_sistema.call_args.kwargs
        self.assertEqual((kw["tipo"], kw["emittente_fiscale_id"]), ("PROCESSO", 3))
        ko = self.client.get("/api/v1/amm-software/accessi/sistema/", {"tipo": "OPERATORE"})
        self.assertEqual(ko.status_code, 400, ko.content)


class CredenzialeTests(_Base):
    def test_credenziale_capability_del_blocco(self):
        self.repo.get_credenziale.side_effect = lambda _uid: {**_CRED, "ultimo_super_admin": True}
        data = self.client.get("/api/v1/amm-software/credenziali/7/").json()["data"]
        self.assertIs(data["can_block"], False)
        self.assertEqual(data["block_reason"], "ULTIMO_SUPER_ADMIN")
        self.assertEqual(data["block_reason_key"], "amministrazione.accessi.blocca_reason.ultimo_super_admin")
        self.assertNotIn("ultimo_super_admin", data)

    def test_credenziale_inesistente_404(self):
        self.repo.get_credenziale.side_effect = lambda _uid: None
        resp = self.client.get("/api/v1/amm-software/credenziali/7/")
        self.assertEqual(resp.status_code, 404, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "E_CREDENZIALE_NON_TROVATA")

    def test_blocca_vuole_l_idempotency_key(self):
        resp = self._post("/api/v1/amm-software/credenziali/7/blocca/", {"motivo": "x"}, chiave=None)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.repo.blocca_credenziale.assert_not_called()

    def test_blocca_chiude_le_sessioni_e_rilegge(self):
        letture = iter([dict(_CRED), {**_CRED, "bloccata": True, "motivo_blocco": "abuso"}])
        self.repo.get_credenziale.side_effect = lambda _uid: next(letture)
        resp = self._post("/api/v1/amm-software/credenziali/7/blocca/", {"motivo": "  abuso  "})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.repo.blocca_credenziale.assert_called_once_with(7, "abuso")
        self.revoca.assert_called_once_with(7)
        self.assertIs(resp.json()["data"]["bloccata"], True)

    def test_sblocca_non_tocca_le_sessioni(self):
        resp = self._post("/api/v1/amm-software/credenziali/7/sblocca/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.repo.sblocca_credenziale.assert_called_once_with(7)
        self.revoca.assert_not_called()

    # Scopo: Il secondo fattore sta sotto la credenziale; la rotta vecchia
    #        sotto `/operatori/` non risponde piu' (nessuna rotta doppia).
    def test_vecchia_rotta_del_secondo_fattore_ritirata(self):
        resp = self.client.get("/api/v1/amm-software/operatori/7/secondo-fattore/")
        self.assertEqual(resp.status_code, 404)
