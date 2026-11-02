# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari permissions_cache — cache Redis L2 permessi.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_save_and_load_nello_stesso_contesto
 2) test_load_cache_miss_returns_none
 3) test_contesti_diversi_non_si_vedono  (M-1: veste o emittente diversi)
 4) test_invalidate_user_scade_tutti_i_contesti
 5) test_invalidate_user_non_tocca_altri_utenti
 6) test_invalidazione_a_meta_richiesta_scade_la_voce_salvata
 7) test_invalidate_department
 8) test_invalidate_all  (S-3: prima non cancellava niente)
 9) test_generazione_sfrattata_non_resuscita_voci_vecchie
10) test_contesto_sessione_emittente_assente
11) test_load_resiliente_a_errore_redis
12) test_save_resiliente_a_errore_redis
13) test_cache_che_non_conserva_la_generazione_non_salva
"""

from unittest import TestCase
from unittest.mock import patch

from django.core.cache.backends.dummy import DummyCache
from django.core.cache.backends.locmem import LocMemCache

from apps.core.services import permissions_cache
from apps.core.services.permissions_cache import contesto_sessione

_CACHE = "apps.core.services.permissions_cache.cache"
# Il legame reparto → utente passa dalla MADRE `identita_digitali` (per
# `soggetto_ruolo_id` verso `risorse_umane`). Fino al 2026-09-12 qui si
# mockava `RisorseUmaneAuthUser`, il model della vista col nome vecchio —
# ritirato (analisi-software-per-dati-morti §2.1).
_IDENTITA = "apps.anagrafiche.models.IdentitaDigitale"
_RISORSE_UMANE = "apps.anagrafiche.models.RisorseUmane"

_OPERATORE_EF1 = contesto_sessione(10, 1)
_OPERATORE_EF2 = contesto_sessione(10, 2)
_PORTALE = contesto_sessione(11, None)


class PermissionsCacheTests(TestCase):
    """Test per permissions_cache, su una cache vera (LocMem) e non un mock:
    il contratto e' fatto di chiavi e generazioni, e un mock direbbe solo
    quali metodi sono stati chiamati."""

    def setUp(self) -> None:
        self.backend = LocMemCache(f"perms-{id(self)}", {})
        patcher = patch(_CACHE, self.backend)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.backend.clear)

    def _salva(self, user_id: int, contesto: str, valori: dict) -> None:
        _, gen = permissions_cache.load_user_cache(user_id, contesto)
        assert gen is not None
        permissions_cache.save_user_cache(user_id, contesto, valori, gen)

    # Scopo: Salvare e ricaricare la cache per un utente nello stesso contesto.
    def test_save_and_load_nello_stesso_contesto(self):
        self._salva(1, _OPERATORE_EF1, {"area:vendite": "TUTTO"})
        valori, _ = permissions_cache.load_user_cache(1, _OPERATORE_EF1)
        self.assertEqual(valori, {"area:vendite": "TUTTO"})

    # Scopo: Cache miss restituisce None (ma le generazioni ci sono).
    def test_load_cache_miss_returns_none(self):
        valori, gen = permissions_cache.load_user_cache(1, _OPERATORE_EF1)
        self.assertIsNone(valori)
        self.assertIsNotNone(gen)

    # Scopo: M-1 — lo stesso utente in un altro emittente o in un'altra veste
    # non riceve i valori calcolati nel primo contesto.
    def test_contesti_diversi_non_si_vedono(self):
        self._salva(1, _OPERATORE_EF1, {"emittenti_pk_ids": [1]})
        self.assertIsNone(permissions_cache.load_user_cache(1, _OPERATORE_EF2)[0])
        self.assertIsNone(permissions_cache.load_user_cache(1, _PORTALE)[0])

    # Scopo: invalidate_user scade le voci di TUTTI i contesti dell'utente.
    def test_invalidate_user_scade_tutti_i_contesti(self):
        self._salva(1, _OPERATORE_EF1, {"a": 1})
        self._salva(1, _PORTALE, {"b": 2})
        permissions_cache.invalidate_user(1)
        self.assertIsNone(permissions_cache.load_user_cache(1, _OPERATORE_EF1)[0])
        self.assertIsNone(permissions_cache.load_user_cache(1, _PORTALE)[0])

    # Scopo: invalidare un utente non scade la cache di un altro.
    def test_invalidate_user_non_tocca_altri_utenti(self):
        self._salva(2, _OPERATORE_EF1, {"a": 1})
        permissions_cache.invalidate_user(1)
        self.assertEqual(permissions_cache.load_user_cache(2, _OPERATORE_EF1)[0], {"a": 1})

    # Scopo: un'invalidazione arrivata fra il caricamento e il salvataggio
    # rende la voce salvata gia' scaduta (si salva con le generazioni lette
    # PRIMA di calcolare).
    def test_invalidazione_a_meta_richiesta_scade_la_voce_salvata(self):
        _, gen = permissions_cache.load_user_cache(1, _OPERATORE_EF1)
        assert gen is not None
        permissions_cache.invalidate_user(1)
        permissions_cache.save_user_cache(1, _OPERATORE_EF1, {"a": "stantio"}, gen)
        self.assertIsNone(permissions_cache.load_user_cache(1, _OPERATORE_EF1)[0])

    # Scopo: Invalidazione reparto scade la cache di tutti gli utenti del reparto.
    @patch(_RISORSE_UMANE)
    @patch(_IDENTITA)
    def test_invalidate_department(self, mock_identita, mock_ru):
        mock_identita.objects.filter.return_value.values_list.return_value = [1, 2]
        for uid in (1, 2, 3):
            self._salva(uid, _OPERATORE_EF1, {"a": uid})

        permissions_cache.invalidate_department(10)

        # Il reparto si cerca su `risorse_umane`, l'utente su `identita_digitali`.
        mock_ru.objects.filter.assert_called_once_with(unita_organizzativa_id=10)
        mock_identita.objects.filter.assert_called_once_with(
            soggetto_ruolo_id__in=mock_ru.objects.filter.return_value.values.return_value
        )
        self.assertIsNone(permissions_cache.load_user_cache(1, _OPERATORE_EF1)[0])
        self.assertIsNone(permissions_cache.load_user_cache(2, _OPERATORE_EF1)[0])
        self.assertEqual(permissions_cache.load_user_cache(3, _OPERATORE_EF1)[0], {"a": 3})

    # Scopo: S-3 — l'invalidazione globale scade davvero tutte le voci
    # (prima costruiva a mano un pattern col prefisso, che django-redis
    # aggiunge da se': non cancellava niente).
    def test_invalidate_all(self):
        self._salva(1, _OPERATORE_EF1, {"a": 1})
        self._salva(2, _PORTALE, {"b": 2})
        permissions_cache.invalidate_all()
        self.assertIsNone(permissions_cache.load_user_cache(1, _OPERATORE_EF1)[0])
        self.assertIsNone(permissions_cache.load_user_cache(2, _PORTALE)[0])

    # Scopo: una generazione sfrattata non fa tornare valide le voci scritte
    # prima: alla rilettura nasce una generazione NUOVA, non «nessuna».
    def test_generazione_sfrattata_non_resuscita_voci_vecchie(self):
        self._salva(1, _OPERATORE_EF1, {"a": 1})
        self.backend.delete(f"perms:gen:user:{1}")
        self.assertIsNone(permissions_cache.load_user_cache(1, _OPERATORE_EF1)[0])

    # Scopo: emittente assente o vuoto (GUC vuota) = un contesto solo, «tutti».
    def test_contesto_sessione_emittente_assente(self):
        self.assertEqual(contesto_sessione(7, None), contesto_sessione(7, ""))
        self.assertNotEqual(contesto_sessione(7, None), contesto_sessione(7, 1))

    # Scopo: Errore Redis su load non propaga eccezione e disattiva il salvataggio.
    @patch(_CACHE)
    def test_load_resiliente_a_errore_redis(self, mock_cache):
        mock_cache.get_many.side_effect = ConnectionError("Redis down")
        self.assertEqual(permissions_cache.load_user_cache(1, _OPERATORE_EF1), (None, None))

    # Scopo: Errore Redis su save non propaga eccezione.
    @patch(_CACHE)
    def test_save_resiliente_a_errore_redis(self, mock_cache):
        mock_cache.set.side_effect = ConnectionError("Redis down")
        # Non deve sollevare eccezione
        permissions_cache.save_user_cache(1, _OPERATORE_EF1, {"a": 1}, ("g", "g"))

    # Scopo: una cache che non conserva la generazione (sfratto immediato,
    # backend che non memorizza) non da' generazioni: senza, la voce salvata
    # porterebbe la generazione "None" e non si potrebbe invalidare.
    def test_cache_che_non_conserva_la_generazione_non_salva(self):
        with patch(_CACHE, DummyCache("perms-dummy", {})):
            self.assertEqual(
                permissions_cache.load_user_cache(1, _OPERATORE_EF1), (None, None)
            )
