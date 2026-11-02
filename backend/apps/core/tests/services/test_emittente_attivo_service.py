# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit di `EmittenteAttivoService` — le regole di «dentro quale
#        emittente sto lavorando» (impersonazione di scope). Repository
#        mockato: qui si prova la POLITICA (chi vince fra permesso e
#        preferenza, cosa succede a una scelta decaduta, cosa vede il FE),
#        non l'SQL.
#
#        La regola di sicurezza vera — «solo restringente, mai allargante» —
#        NON è sotto test qui perché non vive qui: sta nelle funzioni di scope
#        del DB ed è coperta dai loro pgTAP (caso 3). Questo modulo può al più
#        proporre l'emittente sbagliato, e il DB restringerebbe comunque.
#
# Indice test (0..N):
#   0. operatore_usa_il_suo_emittente_di_permesso
#   1. operatore_ignora_la_preferenza (il permesso vince, sempre)
#   2. super_admin_usa_la_preferenza_valida
#   3. super_admin_senza_preferenza_entra_in_globale
#   4. preferenza_decaduta_viene_cancellata
#   5. imposta_valida_e_persiste
#   6. imposta_rifiuta_emittente_non_valido
#   7. imposta_globale_non_cancella_la_preferenza
#   8. descrivi_super_admin_senza_scelta_deve_scegliere
#   9. descrivi_operatore_non_puo_scegliere
#  10. descrivi_modalita_globale_esplicita
#  11. descrivi_senza_user_non_dichiara_il_perimetro
#  12. descrivi_con_scope_multiplo_dichiara_il_perimetro
#  13. descrivi_con_scope_singolo_dichiara_perimetro_falso
#  14. super_admin_puo_scegliere
#  15. operatore_non_configurato_non_puo_scegliere
#  16. senza_user_resta_il_calcolo_storico
#  17. emittente attivo: nome e ruolo nel blocco
#  18. modalita' globale: nome e ruolo assenti
#  19. emittente attivo fuori scope: nome e ruolo assenti
# ------------------------------------------------------------

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.emittente_attivo_service import (
    E_EMITTENTE_ATTIVO_NON_VALIDO,
    EmittenteAttivoService,
)
from apps.core.services.service_errors import ServiceError

_UTENTE = 42


# Scopo: repository mockato con la configurazione del caso in esame.
def _repo(*, permesso=None, preferenza=None, valida=True, voci=None) -> MagicMock:
    repo = MagicMock()
    repo.get_emittente_di_permesso.return_value = permesso
    repo.get_preferenza.return_value = preferenza
    repo.is_scelta_valida.return_value = valida
    repo.list_selezionabili.return_value = voci or []
    return repo


class RisolviPerLoginTests(SimpleTestCase):

    # 0. L'operatore entra dentro il suo emittente, senza scelte da fare.
    def test_operatore_usa_il_suo_emittente_di_permesso(self) -> None:
        repo = _repo(permesso=32)
        self.assertEqual(
            EmittenteAttivoService(repo).risolvi_per_login(_UTENTE), 32,
        )
        # La preferenza non viene nemmeno letta: per lui non esiste.
        repo.get_preferenza.assert_not_called()

    # 1. Se un operatore avesse anche una preferenza (residuo di quando era
    #    super admin), il PERMESSO vince: la preferenza non è un permesso.
    def test_operatore_ignora_la_preferenza(self) -> None:
        service = EmittenteAttivoService(_repo(permesso=32, preferenza=44))
        self.assertEqual(service.risolvi_per_login(_UTENTE), 32)

    # 2. Super admin: la preferenza salvata, se ancora valida.
    def test_super_admin_usa_la_preferenza_valida(self) -> None:
        service = EmittenteAttivoService(_repo(preferenza=44, valida=True))
        self.assertEqual(service.risolvi_per_login(_UTENTE), 44)

    # 3. Nessuna preferenza → modalità globale, e il FE chiederà di scegliere.
    def test_super_admin_senza_preferenza_entra_in_globale(self) -> None:
        service = EmittenteAttivoService(_repo(preferenza=None))
        self.assertIsNone(service.risolvi_per_login(_UTENTE))

    # 4. Preferenza decaduta (emittente disattivato o uscito dallo scope): si
    #    CANCELLA e si riparte dalla scelta. Trascinarla in silenzio farebbe
    #    lavorare l'utente dentro un emittente spento.
    def test_preferenza_decaduta_viene_cancellata(self) -> None:
        repo = _repo(preferenza=44, valida=False)
        service = EmittenteAttivoService(repo)
        self.assertIsNone(service.risolvi_per_login(_UTENTE))
        repo.delete_preferenza.assert_called_once_with(_UTENTE)


class ImpostaTests(SimpleTestCase):

    # 5. Scelta valida: persistita e restituita per il nuovo claim.
    def test_imposta_valida_e_persiste(self) -> None:
        repo = _repo(valida=True)
        self.assertEqual(EmittenteAttivoService(repo).imposta(_UTENTE, 44), 44)
        repo.set_preferenza.assert_called_once_with(_UTENTE, 44)

    # 6. Scelta non valida: errore di dominio, e NIENTE persistenza — una
    #    preferenza scritta e poi rifiutata riapparirebbe al login successivo.
    def test_imposta_rifiuta_emittente_non_valido(self) -> None:
        repo = _repo(valida=False)
        with self.assertRaises(ServiceError) as ctx:
            EmittenteAttivoService(repo).imposta(_UTENTE, 999)
        self.assertEqual(ctx.exception.code, E_EMITTENTE_ATTIVO_NON_VALIDO)
        repo.set_preferenza.assert_not_called()

    # 7. «Tutti gli emittenti» è uno stato di SESSIONE: non tocca la
    #    preferenza, così al prossimo login si rientra dove si lavorava.
    def test_imposta_globale_non_cancella_la_preferenza(self) -> None:
        repo = _repo(preferenza=44)
        self.assertIsNone(EmittenteAttivoService(repo).imposta(_UTENTE, None))
        repo.set_preferenza.assert_not_called()
        repo.delete_preferenza.assert_not_called()


class DescriviTests(SimpleTestCase):

    # 8. Super admin che non ha MAI scelto (nessuna preferenza) → dialog
    #    iniziale bloccante.
    def test_descrivi_super_admin_senza_scelta_deve_scegliere(self) -> None:
        d = EmittenteAttivoService(_repo(preferenza=None)).descrivi(_UTENTE, None)
        self.assertTrue(d["puo_scegliere"])
        self.assertTrue(d["deve_scegliere"])
        self.assertTrue(d["modalita_globale"])

    # 9. L'operatore non sceglie: niente combo, niente dialog.
    def test_descrivi_operatore_non_puo_scegliere(self) -> None:
        d = EmittenteAttivoService(_repo(permesso=32)).descrivi(_UTENTE, 32)
        self.assertFalse(d["puo_scegliere"])
        self.assertFalse(d["deve_scegliere"])
        self.assertFalse(d["modalita_globale"])
        self.assertEqual(d["emittente_fiscale_id"], 32)

    # 10. Super admin che ha SCELTO «Tutti»: è in globale e può scegliere, ma
    #     non «deve» — ha già deciso, e lo si vede dalla preferenza salvata.
    #     Dal solo claim i due stati sono indistinguibili (assente in
    #     entrambi): senza la preferenza il dialog bloccante ricomparirebbe a
    #     ogni caricamento proprio a chi ha appena scelto di vedere tutto.
    def test_descrivi_modalita_globale_esplicita(self) -> None:
        d = EmittenteAttivoService(_repo(preferenza=44)).descrivi(_UTENTE, None)
        self.assertTrue(d["modalita_globale"])
        self.assertTrue(d["puo_scegliere"])
        self.assertFalse(d["deve_scegliere"])


class DescriviPerimetroTests(SimpleTestCase):
    """La chiave `perimetro_multi_emittente` (P-2c, etichette di perimetro)."""

    _SCOPE = (
        "apps.core.services.perimetro_emittente.PermissionResolver"
        ".get_emittenti_pk_ids"
    )
    # ⚠️ Da mockare in ogni test che passa `user`: dal 2026-08-18
    # `puo_scegliere` interroga il bypass SUPER_ADMIN, che va al database.
    _SUPER_ADMIN = (
        "apps.core.services.emittente_attivo_service.PermissionResolver"
        ".is_super_admin"
    )

    # 11. Senza l'oggetto utente la chiave NON compare.
    #     ⚠️ Non vale `False`: senza utente lo scope non si risolve, e scrivere
    #     «un solo emittente» a chi magari li ha tutti sarebbe peggio del
    #     silenzio. E' il caso del POST di cambio emittente, dove per giunta la
    #     GUC porta ancora la sessione precedente.
    def test_descrivi_senza_user_non_dichiara_il_perimetro(self) -> None:
        d = EmittenteAttivoService(_repo(permesso=32)).descrivi(_UTENTE, 32)
        self.assertNotIn("perimetro_multi_emittente", d)

    # 12. Super admin in «Tutti gli emittenti»: perimetro multiplo -> etichetta.
    def test_descrivi_con_scope_multiplo_dichiara_il_perimetro(self) -> None:
        with patch(self._SCOPE, return_value=None), \
                patch(self._SUPER_ADMIN, return_value=True):
            d = EmittenteAttivoService(_repo(preferenza=None)).descrivi(
                _UTENTE, None, user=MagicMock(id=_UTENTE),
            )
        self.assertTrue(d["perimetro_multi_emittente"])

    # 13. Operatore, o super admin che ha scelto: un perimetro solo, niente
    #     etichetta. ⚠️ E' il caso che dimostra perche' si usa lo scope
    #     EFFETTIVO (gia' intersecato con l'emittente attivo) e non quello di
    #     diritto: il super admin che ha scelto sta guardando UN emittente.
    def test_descrivi_con_scope_singolo_dichiara_perimetro_falso(self) -> None:
        with patch(self._SCOPE, return_value=[32]), \
                patch(self._SUPER_ADMIN, return_value=False):
            d = EmittenteAttivoService(_repo(permesso=32)).descrivi(
                _UTENTE, 32, user=MagicMock(id=_UTENTE),
            )
        self.assertFalse(d["perimetro_multi_emittente"])


class PuoScegliereTests(SimpleTestCase):
    """Chi vede la combo dell'emittente di lavoro.

    🔴 Il difetto che questi test chiudono: `puo_scegliere` guardava solo
    l'assenza di un emittente proprio, e dopo P-2a quella condizione descrive
    **anche l'operatore non configurato** — uno che il database non fa piu'
    vedere niente, e a cui l'interfaccia offriva una combo con dentro zero
    opzioni.
    """

    _SUPER_ADMIN = (
        "apps.core.services.emittente_attivo_service.PermissionResolver"
        ".is_super_admin"
    )

    # 14. Super admin senza emittente proprio: sceglie (invariato).
    def test_super_admin_puo_scegliere(self) -> None:
        with patch(self._SUPER_ADMIN, return_value=True):
            d = EmittenteAttivoService(_repo(preferenza=None)).descrivi(
                _UTENTE, None, user=MagicMock(id=_UTENTE), con_perimetro=False,
            )
        self.assertTrue(d["puo_scegliere"])

    # 15. ⭐ Operatore NON configurato: nessun emittente proprio, ma nemmeno
    #     super admin. Prima vedeva la combo, ora no.
    def test_operatore_non_configurato_non_puo_scegliere(self) -> None:
        with patch(self._SUPER_ADMIN, return_value=False):
            d = EmittenteAttivoService(_repo(preferenza=None)).descrivi(
                _UTENTE, None, user=MagicMock(id=_UTENTE), con_perimetro=False,
            )
        self.assertFalse(d["puo_scegliere"])
        # E non gli si impone nemmeno il dialog: non c'e' niente da scegliere.
        self.assertFalse(d["deve_scegliere"])

    # 16. ⚠️ Senza `user` resta il calcolo storico: restringere al buio
    #     toglierebbe la combo a un super admin per mancanza di informazioni.
    def test_senza_user_resta_il_calcolo_storico(self) -> None:
        d = EmittenteAttivoService(_repo(preferenza=None)).descrivi(_UTENTE, None)
        self.assertTrue(d["puo_scegliere"])


class DatiEmittenteAttivoTests(SimpleTestCase):
    """Nome e ruolo dell'emittente ATTIVO (2026-09-26): servono al FE per
    scrivere dentro l'emittente scelto dal super admin (listini)."""

    # 17. Con un emittente attivo il blocco porta il suo nome e il suo RUOLO,
    #     letti con lo stesso criterio di scope delle opzioni della combo.
    def test_emittente_attivo_porta_nome_e_ruolo(self) -> None:
        repo = _repo(voci=[{
            "emittente_fiscale_id": 44, "codice": "E44",
            "ragione_sociale": "Rossi Srl", "soggetto_ruolo_id": 910,
        }])
        d = EmittenteAttivoService(repo).descrivi(_UTENTE, 44)
        self.assertEqual(d["ragione_sociale"], "Rossi Srl")
        self.assertEqual(d["soggetto_ruolo_id"], 910)
        repo.list_selezionabili.assert_called_once_with(_UTENTE, solo_id=44)

    # 18. In modalita' globale non c'e' un emittente su cui scrivere: le
    #     chiavi mancano, e il repository non viene nemmeno interrogato.
    def test_modalita_globale_senza_nome_e_ruolo(self) -> None:
        repo = _repo(preferenza=44)
        d = EmittenteAttivoService(repo).descrivi(_UTENTE, None)
        self.assertNotIn("soggetto_ruolo_id", d)
        self.assertNotIn("ragione_sociale", d)
        repo.list_selezionabili.assert_not_called()

    # 19. Un claim che non e' (piu') nello scope non inventa dati: chiavi
    #     assenti, e il FE tratta la sessione come senza emittente di scrittura.
    def test_emittente_attivo_fuori_scope_senza_dati(self) -> None:
        d = EmittenteAttivoService(_repo(voci=[])).descrivi(_UTENTE, 44)
        self.assertNotIn("soggetto_ruolo_id", d)
