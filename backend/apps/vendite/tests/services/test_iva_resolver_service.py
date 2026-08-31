# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidi del building block risolutore IVA (F2-a). Repository
#        mockato: qui si prova la CATENA PYTHON — il guard di chiamata, il
#        contratto della ripartizione e la normalizzazione — non che la
#        funzione DB calcoli bene, che e' coperto dai 15 casi pgTAP di
#        `db/pgtap/vendite/test-fn-resolve-iva-riga.sql`.
#
# Indice test:
#   1. risolvi: senza emittente si FERMA (P3), e non ripiega
#   2. risolvi: emittente <= 0 e booleano si fermano allo stesso guard
#   3. risolvi: l'anteprima passa imponibile=None al repository
#   4. risolvi: con imponibile la ripartizione a due parti passa
#   5. risolvi: zero righe = invariante rotta, non «nessuna IVA»
#   6. risolvi: ripartizione SENZA imponibile = difetto muto intercettato
#   7. risolvi_anteprima: non e' risolvi()[0] — l'imponibile non si passa
#   8. risolvi_anteprima: ritorna la parte, non la lista
#   9. meta_riga: due chiavi, e non copia cio' che si deriva
#  10. articolo_id e data_riferimento mancanti si fermano
#  11. il soggetto si DERIVA dal billing account (stadio B non si salta)
#  12. un soggetto esplicito non viene sovrascritto dalla derivazione
#  13. applica_riga: payload vuoto -> risolve, ed e' AUTORITATIVA (errori passano)
#  14. applica_riga: payload valorizzato -> il payload VINCE
#  15. applica_riga: payload che DIVERGE -> meta dice MANUALE
#  16. applica_riga: payload che COINCIDE -> resta l'origine del risolutore
#  17. applica_riga: audit che esplode -> il salvataggio NON si blocca
# ------------------------------------------------------------

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.iva_resolver_service import IvaResolverService

_ARTICOLO = "11111111-1111-1111-1111-111111111111"
_DATA = date(2026, 8, 31)
_EMITTENTE = 7


# Scopo: una parte del composito, con i valori che il DB produce davvero.
def _parte(**over):
    base = {
        "quota": None,
        "iva_id": 3,
        "aliquota": Decimal("22.00"),
        "natura_codice": None,
        "is_reverse_charge": False,
        "esigibilita": "I",
        "split_payment": False,
        "riferimento_normativo": "Aliquota I.V.A. al 22%",
        "origine": "ARTICOLO",
        "titolo_iva_id": None,
    }
    base.update(over)
    return base


class IvaResolverServiceTests(unittest.TestCase):
    def setUp(self):
        self.repo = MagicMock()
        # ⚠️ Anche il repository BA e' mockato, e non e' pignoleria: dal
        #    momento in cui il service DERIVA il soggetto dal billing account,
        #    un test che passa un `billing_account_id` senza mock aprirebbe
        #    una connessione vera — e in CI, dove il DB non c'e', fallirebbe
        #    per una ragione che non c'entra con cio' che verifica.
        self.ba_repo = MagicMock()
        self.ba_repo.get_soggetto_id.return_value = None
        self.service = IvaResolverService(repo=self.repo, ba_repo=self.ba_repo)

    # ── 1-2. Il guard che vale tutti gli altri ────────────────────────────
    # Scopo: ⛔ IL PRESIDIO PIU' IMPORTANTE DEL BB, e prova una cosa che il
    #        DB non puo' provare. Senza emittente la funzione NON sbaglia:
    #        legge zero titoli sotto RLS e risponde con l'aliquota ordinaria,
    #        cioe' risponde bene a una domanda diversa. Il difetto non ha
    #        nessun sintomo — una fattura semplicemente sbagliata — ed e' per
    #        questo che deve fermarsi PRIMA del round-trip.
    def test_senza_emittente_si_ferma_e_non_chiama_il_db(self):
        for valore in (None, 0, -1, True):
            with self.subTest(emittente=valore):
                with self.assertRaises(ServiceError) as ctx:
                    self.service.risolvi(
                        articolo_id=_ARTICOLO,
                        data_riferimento=_DATA,
                        emittente_fiscale_id=valore,  # type: ignore[arg-type]
                    )
                self.assertEqual(ctx.exception.code, "E_VENDITE_CHIAMATA_NON_VALIDA")
        # ⚠️ Il guard non serve a niente se il round-trip parte lo stesso.
        self.repo.resolve.assert_not_called()

    # Scopo: `True` e' un `int` in Python e passerebbe un `> 0` ingenuo.
    #        L'emittente 1 e l'emittente "vero" non sono la stessa cosa.
    def test_emittente_booleano_non_passa_per_un_intero(self):
        with self.assertRaises(ServiceError):
            self.service.risolvi(
                articolo_id=_ARTICOLO,
                data_riferimento=_DATA,
                emittente_fiscale_id=True,  # type: ignore[arg-type]
            )

    # ── 3-4. Il contratto della ripartizione ──────────────────────────────
    # Scopo: sui DOCUMENTI l'imponibile non si passa (P1), ed e' cosi' che la
    #        riga non si spezza. Si verifica che arrivi `None` al repository,
    #        non che il risultato abbia un elemento: la seconda cosa sarebbe
    #        vera anche passando l'imponibile su un plafond capiente.
    def test_anteprima_passa_imponibile_none_al_repository(self):
        self.repo.resolve.return_value = [_parte()]
        self.service.risolvi(
            articolo_id=_ARTICOLO,
            data_riferimento=_DATA,
            emittente_fiscale_id=_EMITTENTE,
        )
        self.assertIsNone(self.repo.resolve.call_args.kwargs["imponibile"])

    # Scopo: con l'imponibile le due parti sono legittime e passano intatte,
    #        nell'ordine del DB — prima la quota coperta dal titolo.
    def test_con_imponibile_la_ripartizione_a_due_parti_passa(self):
        self.repo.resolve.return_value = [
            _parte(quota=Decimal("100"), origine="TITOLO", titolo_iva_id=5, aliquota=Decimal("0")),
            _parte(quota=Decimal("40")),
        ]
        parti = self.service.risolvi(
            articolo_id=_ARTICOLO,
            data_riferimento=_DATA,
            emittente_fiscale_id=_EMITTENTE,
            imponibile=Decimal("140"),
        )
        self.assertEqual(len(parti), 2)
        self.assertEqual(parti[0]["origine"], "TITOLO")
        self.assertEqual(parti[1]["quota"], Decimal("40"))

    # ── 5-6. I due difetti muti ───────────────────────────────────────────
    # Scopo: zero righe non e' «nessuna IVA»: il contratto della funzione e'
    #        «una riga esce sempre», e quando non trova nulla lo dice con
    #        origine=ASSENTE. Una lista vuota e' un'invariante rotta, e senza
    #        guard il chiamante scriverebbe una riga senza IVA credendo di
    #        aver letto una risposta.
    def test_zero_righe_e_invariante_rotta(self):
        self.repo.resolve.return_value = []
        with self.assertRaises(ServiceError) as ctx:
            self.service.risolvi(
                articolo_id=_ARTICOLO,
                data_riferimento=_DATA,
                emittente_fiscale_id=_EMITTENTE,
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_CHIAMATA_NON_VALIDA")

    # Scopo: ⭐ il caso che nessuno penserebbe di scrivere. Senza imponibile
    #        il DB NON puo' spezzare: se due parti arrivano lo stesso, il ramo
    #        di anteprima si e' rotto. E il difetto sarebbe MUTO — il
    #        chiamante prende `parti[0]` e non sa di aver perso l'altra meta'.
    def test_ripartizione_senza_imponibile_e_un_difetto_intercettato(self):
        self.repo.resolve.return_value = [_parte(), _parte()]
        with self.assertRaises(ServiceError):
            self.service.risolvi(
                articolo_id=_ARTICOLO,
                data_riferimento=_DATA,
                emittente_fiscale_id=_EMITTENTE,
            )

    # ── 7-8. L'anteprima ──────────────────────────────────────────────────
    # Scopo: ⚠️ `risolvi_anteprima` NON e' `risolvi()[0]`. Chiamare col totale
    #        e prendere la prima parte darebbe il trattamento della sola quota
    #        coperta applicandolo a TUTTA la riga — il difetto opposto a
    #        quello che P1 evita. Si prova che l'imponibile non viene passato.
    def test_anteprima_non_passa_mai_un_imponibile(self):
        self.repo.resolve.return_value = [_parte()]
        self.service.risolvi_anteprima(
            articolo_id=_ARTICOLO,
            data_riferimento=_DATA,
            emittente_fiscale_id=_EMITTENTE,
            billing_account_id=42,
        )
        kwargs = self.repo.resolve.call_args.kwargs
        self.assertIsNone(kwargs["imponibile"])
        self.assertEqual(kwargs["billing_account_id"], 42)

    def test_anteprima_ritorna_la_parte_non_la_lista(self):
        self.repo.resolve.return_value = [_parte(origine="TITOLO", titolo_iva_id=9)]
        parte = self.service.risolvi_anteprima(
            articolo_id=_ARTICOLO,
            data_riferimento=_DATA,
            emittente_fiscale_id=_EMITTENTE,
        )
        self.assertIsInstance(parte, dict)
        self.assertEqual(parte["titolo_iva_id"], 9)

    # ── 9. Cosa sopravvive sulla riga ─────────────────────────────────────
    # Scopo: ⭐ due chiavi, e il test presidia soprattutto cio' che NON c'e'.
    #        Aliquota, natura e riferimento normativo si derivano dal JOIN su
    #        `config.iva` che i repository di riga fanno gia': copiarli nel
    #        meta creerebbe una frase che invecchia — e `descrizione` e'
    #        l'unica colonna che il lock D27 lascia modificabile apposta.
    def test_meta_riga_porta_i_fatti_e_non_i_derivabili(self):
        meta = IvaResolverService.meta_riga(
            _parte(origine="TITOLO", titolo_iva_id=5)
        )
        self.assertEqual(meta, {"iva_origine": "TITOLO", "iva_titolo_id": 5})
        for derivabile in ("aliquota", "natura_codice", "riferimento_normativo"):
            self.assertNotIn(derivabile, meta)

    # ── 10. Gli altri guard ───────────────────────────────────────────────
    def test_articolo_e_data_obbligatori(self):
        with self.assertRaises(ServiceError):
            self.service.risolvi(
                articolo_id="",
                data_riferimento=_DATA,
                emittente_fiscale_id=_EMITTENTE,
            )
        with self.assertRaises(ServiceError):
            self.service.risolvi(
                articolo_id=_ARTICOLO,
                data_riferimento="2026-08-31",  # type: ignore[arg-type]
                emittente_fiscale_id=_EMITTENTE,
            )
        self.repo.resolve.assert_not_called()

    # ── 11-12. La derivazione del soggetto ────────────────────────────────
    # Scopo: ⛔ IL DIFETTO MUTO CHE QUESTO COMPORTAMENTO EVITA. Il risolutore
    #        applica lo stadio B — i titoli documentati del soggetto, cioe' le
    #        dichiarazioni d'intento — solo se riceve INSIEME soggetto ed
    #        emittente, e il soggetto dal BA non lo deriva. Un chiamante che ha
    #        in mano il solo billing account otterrebbe l'aliquota ordinaria
    #        senza che niente segnali che i titoli non sono stati guardati:
    #        IVA piena a un esportatore abituale, e nessun errore.
    def test_il_soggetto_si_deriva_dal_billing_account(self):
        self.repo.resolve.return_value = [_parte()]
        self.ba_repo.get_soggetto_id.return_value = "22222222-2222-2222-2222-222222222222"
        self.service.risolvi(
            articolo_id=_ARTICOLO,
            data_riferimento=_DATA,
            emittente_fiscale_id=_EMITTENTE,
            billing_account_id=99,
        )
        self.ba_repo.get_soggetto_id.assert_called_once_with(99)
        self.assertEqual(
            self.repo.resolve.call_args.kwargs["soggetto_id"],
            "22222222-2222-2222-2222-222222222222",
        )

    # Scopo: ⚠️ la derivazione RIEMPIE un vuoto, non sovrascrive una scelta.
    #        Un chiamante che il soggetto ce l'ha (la riga di fattura, che lo
    #        conosce dalla testata) deve vedersi passare il suo — e il BA non
    #        deve nemmeno essere interrogato.
    def test_un_soggetto_esplicito_vince_sulla_derivazione(self):
        self.repo.resolve.return_value = [_parte()]
        self.service.risolvi(
            articolo_id=_ARTICOLO,
            data_riferimento=_DATA,
            emittente_fiscale_id=_EMITTENTE,
            billing_account_id=99,
            soggetto_id="33333333-3333-3333-3333-333333333333",
        )
        self.ba_repo.get_soggetto_id.assert_not_called()
        self.assertEqual(
            self.repo.resolve.call_args.kwargs["soggetto_id"],
            "33333333-3333-3333-3333-333333333333",
        )

    # ── 13-17. La regola «il payload vince, ma si registra» (opzione B) ───
    # Scopo: senza `iva_id` nel payload la risoluzione e' AUTORITATIVA: decide
    #        lei, e il `meta` porta l'origine vera.
    def test_applica_riga_senza_payload_risolve(self):
        self.repo.resolve.return_value = [_parte(iva_id=9, origine="TITOLO", titolo_iva_id=4)]
        iva, meta = self.service.applica_riga_documento(
            payload_iva_id=None,
            articolo_id=_ARTICOLO,
            data_riferimento=_DATA,
            emittente_fiscale_id=_EMITTENTE,
        )
        self.assertEqual(iva, 9)
        self.assertEqual(meta, {"iva_origine": "TITOLO", "iva_titolo_id": 4})

    # Scopo: ⛔ E gli errori PASSANO. Se il risolutore non sa rispondere, la
    #        riga non si scrive con un'IVA inventata: si ferma. E' l'unico ramo
    #        in cui un fallimento deve fermare il salvataggio.
    def test_applica_riga_senza_payload_non_ingoia_gli_errori(self):
        self.repo.resolve.return_value = []
        with self.assertRaises(ServiceError):
            self.service.applica_riga_documento(
                payload_iva_id=None,
                articolo_id=_ARTICOLO,
                data_riferimento=_DATA,
                emittente_fiscale_id=_EMITTENTE,
            )

    # Scopo: con `iva_id` nel payload vince il payload — finche' `I6` non
    #        chiude la casella, la scelta dell'operatore e' legittima e
    #        ignorarla la farebbe sparire senza dirlo.
    def test_applica_riga_il_payload_vince(self):
        self.repo.resolve.return_value = [_parte(iva_id=3)]
        iva, _ = self.service.applica_riga_documento(
            payload_iva_id=77,
            articolo_id=_ARTICOLO,
            data_riferimento=_DATA,
            emittente_fiscale_id=_EMITTENTE,
        )
        self.assertEqual(iva, 77)

    # Scopo: ⭐ e il `meta` lo DICE. Senza, una riga con l'aliquota scelta a
    #        mano sarebbe indistinguibile da una risolta — e la ricostruzione
    #        storica risponderebbe la cosa sbagliata a «perche' e' cosi'».
    def test_applica_riga_payload_divergente_e_manuale(self):
        self.repo.resolve.return_value = [_parte(iva_id=3, origine="ARTICOLO")]
        _, meta = self.service.applica_riga_documento(
            payload_iva_id=77,
            articolo_id=_ARTICOLO,
            data_riferimento=_DATA,
            emittente_fiscale_id=_EMITTENTE,
        )
        self.assertEqual(meta["iva_origine"], "MANUALE")
        self.assertIsNone(meta["iva_titolo_id"])

    # Scopo: ⚠️ il gemello che impedisce l'errore opposto. Se l'operatore
    #        CONFERMA il valore proposto non ha sovrascritto niente: marcarlo
    #        manuale renderebbe manuale tutto il traffico del form, cioe'
    #        toglierebbe al campo ogni capacita' di dire qualcosa.
    def test_applica_riga_payload_coincidente_resta_del_risolutore(self):
        self.repo.resolve.return_value = [_parte(iva_id=3, origine="ARTICOLO")]
        _, meta = self.service.applica_riga_documento(
            payload_iva_id=3,
            articolo_id=_ARTICOLO,
            data_riferimento=_DATA,
            emittente_fiscale_id=_EMITTENTE,
        )
        self.assertEqual(meta["iva_origine"], "ARTICOLO")

    # Scopo: ⭐ l'audit e' BEST-EFFORT. Un titolo ambiguo o un paese non
    #        implementato non devono bloccare un salvataggio che l'operatore ha
    #        gia' determinato: si perde l'audit, non il lavoro.
    def test_applica_riga_audit_che_esplode_non_blocca(self):
        self.repo.resolve.side_effect = RuntimeError("titoli ambigui")
        iva, meta = self.service.applica_riga_documento(
            payload_iva_id=77,
            articolo_id=_ARTICOLO,
            data_riferimento=_DATA,
            emittente_fiscale_id=_EMITTENTE,
        )
        self.assertEqual(iva, 77)
        self.assertEqual(meta, {})

