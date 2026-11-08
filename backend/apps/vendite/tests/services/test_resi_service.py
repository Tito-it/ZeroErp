# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Unit test resi_service (mock repository, no DB). Clone strutturale di
#        test_ddt_service: valida i guard di creazione (DDT sorgente esistente e
#        CONSEGNATO, sorgente per codice), lo snapshot riga dalla riga DDT
#        (appartenenza al DDT sorgente, tipo/qta obbligatori, ordine_riga_id dal
#        fulfillment), i guard di stato DRAFT su update/righe/delete, le azioni
#        di dominio (conferma/annullo/ri-consegna: delega alle fn madri DB,
#        niente atomic extra, ritorno light) e la traduzione errori DB di
#        _db_errors (IntegrityError -> codice vincolo; DatabaseError trigger ->
#        estrazione codice E_RESO_*).
# ------------------------------------------------------------

"""
Indice test eseguiti (classe :: metodo):

ResiServiceGuardsTests
 1) test_get_reso_not_found              — E_RESO_NOT_FOUND se testata None
 2) test_aggiorna_reso_stato_non_draft   — E_RESO_STATO_TRANSIZIONE se != DRAFT
 3) test_gestisci_riga_stato_non_draft   — E_RIGA_DOC_NON_BOZZA se != DRAFT (il codice del DB, BB richiedi_righe_in_bozza)
 4) test_elimina_riga_stato_non_draft    — E_RIGA_DOC_NON_BOZZA se != DRAFT

ResiCreaTests
 5) test_crea_reso_ok                    — sorgente per codice + uid DDT + DRAFT
 6) test_crea_reso_ddt_mancante          — E_RESO_VALIDAZIONE senza ddt_id
 7) test_crea_reso_ddt_id_non_numerico   — E_RESO_VALIDAZIONE (no 500)
 8) test_crea_reso_ddt_not_found         — E_DDT_NOT_FOUND
 9) test_crea_reso_ddt_non_consegnato    — E_RESO_DDT_NON_CONSEGNATO (stesso codice del trigger)
10) test_crea_reso_con_righe_atomic      — testata + N righe, righe_ids, riga_nr batch senza next_riga_nr
10b) test_crea_reso_data_non_iso         — E_RESO_VALIDAZIONE (data non ISO)

ResiRigheTests
11) test_crea_riga_snapshot_da_riga_ddt  — snapshot articolo/uom/ordine_riga_id
12) test_crea_riga_ddt_riga_estranea     — E_RESO_VALIDAZIONE (riga di altro DDT)
13) test_crea_riga_senza_tipo            — E_RESO_VALIDAZIONE
14) test_crea_riga_senza_qta_operativa   — E_RESO_VALIDAZIONE (quantita base sola NON basta)
14b) test_crea_riga_fulfillment_multipli — E_RESO_VALIDAZIONE (modello 1:1)
15) test_aggiorna_riga_ok                — whitelist campi update (quantita esclusa)
16) test_aggiorna_riga_estranea          — E_RESO_NOT_FOUND

ResiCodaAccreditareTests
16b) test_etichetta_valida_passthrough    — DOVUTA/FACOLTATIVA al repo
16c) test_etichetta_invalida_400          — whitelist fail-fast E_RESO_VALIDAZIONE
16d) test_etichetta_none_default          — assente = tutte le righe

ResiEliminaTests
17) test_elimina_reso_con_righe_rifiutato — E_RESO_STATO_TRANSIZIONE
18) test_elimina_reso_bozza_orfana_ok     — hard-delete ammesso (0 righe)

ResiAzioniTests
19) test_conferma_delega_fn_madre_light   — fn_conferma_reso + stato RILETTO dal DB
20) test_conferma_not_found_da_fn         — E_RESO_NOT_FOUND estratto dal RAISE della fn
21) test_conferma_no_atomic_extra         — atomicita' nella fn madre DB
22) test_annulla_delega_fn_madre_light    — fn_annulla_reso + stato riletto
23) test_riconsegna_delega_e_ritorna      — fn_genera_ddt_riconsegna + ddt_id + slot di default
24) test_riconsegna_errore_del_default_sale — verbo e default in una transazione
24b) test_riconsegna_righe_vuote          — E_RESO_VALIDAZIONE (no degrado a "tutto")
24c) test_riconsegna_righe_non_lista      — E_RESO_VALIDAZIONE (no degrado a "tutto")
24d) test_riconsegna_riga_senza_qta       — E_RESO_VALIDAZIONE

ResiChiusuraRiconsegnaTests (chiudi/riapri ri-consegna — l'altra uscita)
24e) test_chiudi_delega_e_ritorna         — fn_chiudi_riconsegna_reso + righe_chiuse
24f) test_chiudi_note_vuote_a_null        — note whitespace -> NULL
24g) test_chiudi_note_trimmate            — note trimmate
24g-bis) test_chiudi_note_tipo_non_stringa_rifiutata — E_RESO_VALIDAZIONE
24h) test_chiudi_righe_none_e_tutta_la_copertura — None = tutta la copertura
24i) test_chiudi_righe_degeneri_rifiutate — E_RESO_VALIDAZIONE (no degrado)
24j) test_riapri_delega_e_ritorna         — fn_riapri_riconsegna_reso
24k) test_riapri_righe_degeneri_rifiutate — E_RESO_VALIDAZIONE
24l) test_nessun_atomic_extra             — nessun transaction.atomic extra

ResiDbErrorsTests
25) test_integrity_error_fk_mappato       — E_VENDITE_FK
26) test_integrity_error_fallback         — E_VENDITE_VALIDATION
27) test_database_error_trigger_code      — E_RESO_QTA_SUPERA_CONSEGNATO
28) test_filtro_ddt_passthrough            — ddt_id arriva al repository
28b) test_filtro_documento_id_non_positivo — ddt_id=0 -> 400, non coda vuota
29) test_filtro_ordine_passthrough         — ordine_id arriva al repository
30) test_filtro_documento_mutuamente_esclusivo — ddt_id + ordine_id -> 400
31) test_filtro_documento_assente_default  — None su entrambe le code
32) test_filtro_documento_su_riconsegne    — la simmetria fra le due code
33) test_etichette_export_dichiarano_il_documento — il file non mente sul perimetro

ResiAccreditoTests (il verbo della nota di credito — madre fn_accredita_riga_reso)
34) test_accredito_ritorna_tutte_le_rettifiche   — RETURNS TABLE: N righe, non la prima
35) test_accredito_nessun_precheck_applicativo   — i guard sono nella madre
36) test_accredito_no_atomic_extra               — una sola SELECT fn_()
37) test_accredito_codice_dominio_dalla_madre    — E_ACCREDITO_GIA_ESEGUITO

ResiAccreditoMassivoTests (il fan-out del verbo — B2 / D-NC-7)
38) test_massivo_esito_parziale_non_solleva      — 200 con esito PARZIALE
39) test_massivo_tutte_fallite_non_solleva       — anche ERRORE e' un report
40) test_massivo_accrediti_portano_la_riga       — flatten con resi_riga_id
41) test_massivo_dedup_preserva_ordine           — id ripetuto lavorato UNA volta
42) test_massivo_lista_vuota_rifiutata           — no «tutte» per omissione
43) test_massivo_lista_degenere_rifiutata        — non-lista, id 0/negativi/bool/testo
44) test_massivo_cap_rispettato                  — max MAX_ACCREDITI_MASSIVI

ResiAnnulloAccreditoTests (B2-bis / D-NC-11)
45) test_annullo_delega_alla_madre               — una sola fn, ritorno light
46) test_annullo_riga_di_altro_reso_rifiutata    — E_RESO_NOT_FOUND, madre non chiamata
47) test_annullo_motivo_vuoto_a_null             — normalizza, il rifiuto e' della madre
48) test_annullo_codice_dominio_dalla_madre      — E_ACCREDITO_ANNULLO_NON_AMMESSO
49) test_annullo_no_atomic_extra                 — atomicita' nella fn madre
50) test_annullo_motivo_non_stringa_rifiutato    — nessun tipo strano al driver

ResiSatellitiTestataTests (2026-09-21, «leggi prima la testata»)
51) test_list_righe_reso_non_trovato_e_404       — E_RESO_NOT_FOUND, repo righe non chiamato
52) test_list_righe_con_testata_delega_al_repo    — caso felice: delega invariata
53) test_get_rientri_raggruppa_per_voce            — origini e rientri sotto riga o componente giusti (B2)
54) test_crea_rientro_vuole_il_prelievo            — E_RESO_VALIDAZIONE senza prelievo, niente scrittura
55) test_rientro_di_altra_riga_e_404               — E_RESO_NOT_FOUND, niente scrittura
"""

from contextlib import nullcontext
from unittest.mock import patch

from django.db import DatabaseError, IntegrityError
from django.test import SimpleTestCase

from apps.core.services.error_manager import ServiceError
from apps.core.tests._helpers.modello_documento_mockato import ModelloDocumentoMockatoMixin
from apps.core.services.fan_out import run_fan_out as _run_fan_out_vero
from apps.vendite.services import resi_service
from apps.vendite.services.resi_service import _db_errors

_REPO = "apps.vendite.services.resi_service.ResiRepository"
_SVC = "apps.vendite.services.resi_service"
_ATOMIC = "apps.vendite.services.resi_service.transaction.atomic"
_DDT_REPO = "apps.vendite.services.resi_service.DdtRepository"


# Scopo: il BB `run_fan_out` VERO, con l'isolamento per elemento spento. Il
#        savepoint richiede un database e questi test girano su SimpleTestCase;
#        spegnere l'isolamento lascia intatto cio' che i test misurano —
#        aggregazione a tre stati, ordine, cattura dei codici — e non simula il
#        BB con un finto ciclo, che sarebbe il modo migliore per verificare una
#        cosa e consegnarne un'altra.
def _fan_out_reale(items, process, **kwargs):
    kwargs["isola_in_transazione"] = False
    return _run_fan_out_vero(items, process, **kwargs)

# Lettura leggera di comodo per i guard righe (get_stato_e_ddt_origine).
_RESO_DRAFT = {"stato_codice_interno": "DRAFT", "ddt_origine_id": 30}
# Snapshot riga DDT di comodo (get_ddt_riga_snapshot).
_SNAPSHOT_RIGA = {
    "id": 11, "ddt_id": 30, "articolo_id": "a-uuid", "descrizione": "Art. X",
    "quantita": "10", "qta_operativa": "10", "uom_operativa_id": 4,
    "factor_to_base": "1", "ordine_riga_id": 90, "fulfillment_count": 1,
}


class ResiServiceGuardsTests(SimpleTestCase):
    """Guard di stato (E_RESO_STATO_TRANSIZIONE sulla testata, E_RIGA_DOC_NON_BOZZA
    sulle righe — il codice del BB a DB, anche se su resi_righe non e' ancora
    montato) e not-found (E_RESO_NOT_FOUND)."""

    @patch(_REPO, autospec=True)
    def test_get_reso_not_found(self, repo_cls) -> None:
        repo_cls.return_value.get_reso.return_value = None
        with self.assertRaises(ServiceError) as cm:
            resi_service.get_reso(99)
        self.assertEqual(cm.exception.code, "E_RESO_NOT_FOUND")

    # Scopo: il blob di fn_available_actions_reso viaggia intatto SOTTO
    #        `capabilities`, e nessuna sua chiave sale nella testata (api.md
    #        §«Il blob sta SOTTO `capabilities`», 2026-09-23). Fino a quel
    #        giorno nessun test del reso guardava la forma del dettaglio.
    @patch(_REPO, autospec=True)
    def test_get_reso_capabilities_annidate(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_reso.return_value = {"id": 7, "stato_codice_interno": "DRAFT"}
        repo.get_capabilities.return_value = {
            "available_actions": [{"key": "conferma", "target_state": "CONFERMATO"}],
            "can_edit_testata": True,
            "can_edit_righe": True,
            "non_editable_fields": ["ddt_id"],
            "stato_codice": "DRAFT",
        }
        repo.count_righe.return_value = 2
        out = resi_service.get_reso(7)
        self.assertEqual(out["capabilities"], repo.get_capabilities.return_value)
        for chiave in repo.get_capabilities.return_value:
            self.assertNotIn(chiave, out)
        self.assertEqual(out["righe_count"], 2)

    @patch(_REPO, autospec=True)
    def test_aggiorna_reso_fuori_bozza_decide_il_db(self, repo_cls) -> None:
        # Reso CONFERMATO: le note si cambiano ancora, la data no, e lo dice il
        # lock di testata del DB (brief-db-testata-dopo-emissione, D-2): il
        # service non ha piu' un «solo in DRAFT» e passa la scrittura.
        repo = repo_cls.return_value
        # L'esistenza si legge col lettore leggero; lo stato non ferma niente.
        repo.get_stato_codice.return_value = "CONFERMATO"
        resi_service.aggiorna_reso(7, {"meta": {"nota": "x"}})
        repo.get_reso.assert_not_called()
        self.assertEqual(repo.update_reso.call_args.kwargs, {"meta": {"nota": "x"}})

    @patch(_REPO, autospec=True)
    def test_gestisci_riga_stato_non_draft(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_e_ddt_origine.return_value = {
            **_RESO_DRAFT, "stato_codice_interno": "CONFERMATO", "numero": "2026/00005",
        }
        with self.assertRaises(ServiceError) as cm:
            resi_service.gestisci_riga(7, {"ddt_riga_id": 11})
        self.assertEqual(cm.exception.code, "E_RIGA_DOC_NON_BOZZA")
        self.assertEqual(
            cm.exception.message,
            "Reso 2026/00005 non e' piu' in bozza (stato CONFERMATO): le sue righe "
            "si possono aggiungere solo finche' e' in bozza.",
        )
        repo.create_riga.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_elimina_riga_stato_non_draft(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_e_ddt_origine.return_value = {
            **_RESO_DRAFT, "stato_codice_interno": "ANNULLATO",
        }
        with self.assertRaises(ServiceError) as cm:
            resi_service.elimina_riga(7, 3)
        self.assertEqual(cm.exception.code, "E_RIGA_DOC_NON_BOZZA")
        # Senza `numero` l'etichetta ripiega su `#id`.
        self.assertTrue(cm.exception.message.startswith("Reso #7 non e' piu' in bozza (stato ANNULLATO)"))
        repo.delete_riga.assert_not_called()


class ResiCreaTests(SimpleTestCase):
    """crea_reso: sorgente data-driven + guard DDT CONSEGNATO (applicativo)."""

    def setUp(self) -> None:
        # transaction.atomic() a no-op (SimpleTestCase senza DB); nullcontext
        # stateless riusabile su piu' `with`.
        patcher = patch(_ATOMIC, return_value=nullcontext())
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch(_REPO, autospec=True)
    def test_crea_reso_ok(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ddt_sorgente.return_value = {
            "id": 30, "uid": "u-ddt-30", "numero": "DDT01",
            "stato_codice_interno": "CONSEGNATO",
        }
        repo.create_reso.return_value = {"id": 7, "uid": "u-reso", "numero": None}

        out = resi_service.crea_reso({"ddt_id": 30})

        self.assertEqual(out["id"], 7)
        self.assertEqual(out["righe_ids"], [])
        # Il service passa la bolla: tipo e chiave della provenienza li
        # sceglie il repository dal BB del DB (`script.fn_sorgente_provenienza`).
        kwargs = repo.create_reso.call_args.kwargs
        self.assertEqual(kwargs["ddt_id"], 30)
        self.assertNotIn("sorgente_tipo_id", kwargs)
        self.assertNotIn("sorgente_uid", kwargs)
        # Lo stato non si passa: lo mette il DB, lo stato iniziale del
        # vocabolario (brief-modello-documento-vendita P-2).
        self.assertNotIn("stato_doc_reso_id", kwargs)

    @patch(_REPO, autospec=True)
    def test_crea_reso_ddt_mancante(self, repo_cls) -> None:
        repo = repo_cls.return_value
        with self.assertRaises(ServiceError) as cm:
            resi_service.crea_reso({})
        self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo.create_reso.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_crea_reso_ddt_id_non_numerico(self, repo_cls) -> None:
        # ddt_id non numerico -> 4xx parlante, non 500 da int().
        repo = repo_cls.return_value
        with self.assertRaises(ServiceError) as cm:
            resi_service.crea_reso({"ddt_id": "abc"})
        self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo.create_reso.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_crea_reso_ddt_not_found(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_ddt_sorgente.return_value = None
        with self.assertRaises(ServiceError) as cm:
            resi_service.crea_reso({"ddt_id": 30})
        self.assertEqual(cm.exception.code, "E_DDT_NOT_FOUND")
        repo.create_reso.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_crea_reso_ddt_non_consegnato(self, repo_cls) -> None:
        # Guard applicativo parlante col medesimo codice del trigger DB
        # (trgfn_resi_guard_ddt_consegnato): un solo errore per lo stesso
        # caso a prescindere dal percorso.
        repo = repo_cls.return_value
        repo.get_ddt_sorgente.return_value = {
            "id": 30, "uid": "u", "stato_codice_interno": "SPEDITO",
        }
        with self.assertRaises(ServiceError) as cm:
            resi_service.crea_reso({"ddt_id": 30})
        self.assertEqual(cm.exception.code, "E_RESO_DDT_NON_CONSEGNATO")
        repo.create_reso.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_crea_reso_con_righe_atomic(self, repo_cls) -> None:
        # Pannello FE: testata + N righe in un'unica chiamata; le righe
        # ricevono lo snapshot dalla riga DDT e finiscono in righe_ids.
        # riga_nr assegnato in batch (testata nuova): NIENTE next_riga_nr.
        repo = repo_cls.return_value
        repo.get_ddt_sorgente.return_value = {
            "id": 30, "uid": "u-ddt-30", "stato_codice_interno": "CONSEGNATO",
        }
        repo.create_reso.return_value = {"id": 7, "uid": "u", "numero": None}
        repo.get_ddt_riga_snapshot.return_value = dict(_SNAPSHOT_RIGA)
        repo.create_riga.return_value = {"id": 71}

        out = resi_service.crea_reso({
            "ddt_id": 30,
            "righe": [{"ddt_riga_id": 11, "tipo_reso_id": 2,
                       "qta_operativa": "3", "motivo": "danneggiato"}],
        })

        self.assertEqual(out["righe_ids"], [71])
        repo.next_riga_nr.assert_not_called()
        kwargs = repo.create_riga.call_args.kwargs
        self.assertEqual(kwargs["reso_id"], 7)
        self.assertEqual(kwargs["riga_nr"], 1)
        self.assertEqual(kwargs["ddt_riga_id"], 11)
        self.assertEqual(kwargs["tipo_reso_id"], 2)
        self.assertEqual(kwargs["qta_operativa"], "3")
        self.assertEqual(kwargs["motivo"], "danneggiato")

    @patch(_REPO, autospec=True)
    def test_crea_reso_data_non_iso(self, repo_cls) -> None:
        # `data` non ISO -> 4xx parlante, non errore DB grezzo (o peggio
        # interpretazione DateStyle-dipendente).
        repo = repo_cls.return_value
        repo.get_ddt_sorgente.return_value = {
            "id": 30, "uid": "u-ddt-30", "stato_codice_interno": "CONSEGNATO",
        }
        with self.assertRaises(ServiceError) as cm:
            resi_service.crea_reso({"ddt_id": 30, "data": "13/07/2026"})
        self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo.create_reso.assert_not_called()


class ResiRigheTests(SimpleTestCase):
    """gestisci_riga/aggiorna_riga: snapshot dalla riga DDT + guard."""

    @patch(_REPO, autospec=True)
    def test_crea_riga_snapshot_da_riga_ddt(self, repo_cls) -> None:
        # Articolo/descrizione/UoM/factor/ordine_riga_id copiati dallo
        # snapshot (il reso non inventa articoli); il payload porta solo
        # ddt_riga_id + tipo + quantita'.
        repo = repo_cls.return_value
        repo.get_stato_e_ddt_origine.return_value = dict(_RESO_DRAFT)
        repo.get_ddt_riga_snapshot.return_value = dict(_SNAPSHOT_RIGA)
        repo.next_riga_nr.return_value = 2
        repo.create_riga.return_value = {"id": 72}

        out = resi_service.gestisci_riga(
            7, {"ddt_riga_id": 11, "tipo_reso_id": 1, "qta_operativa": "5"},
        )

        self.assertEqual(out, {"reso_id": 7, "riga_id": 72})
        kwargs = repo.create_riga.call_args.kwargs
        self.assertEqual(kwargs["articolo_id"], "a-uuid")
        self.assertEqual(kwargs["descrizione"], "Art. X")
        self.assertEqual(kwargs["uom_operativa_id"], 4)
        self.assertEqual(kwargs["factor_to_base"], "1")
        # ordine_riga_id dal fulfillment (alimenta il residuo reso-aware).
        self.assertEqual(kwargs["ordine_riga_id"], 90)
        self.assertEqual(kwargs["riga_nr"], 2)

    @patch(_REPO, autospec=True)
    def test_crea_riga_ddt_riga_estranea(self, repo_cls) -> None:
        # La riga DDT appartiene a un ALTRO DDT: rifiuto parlante.
        repo = repo_cls.return_value
        repo.get_stato_e_ddt_origine.return_value = dict(_RESO_DRAFT)
        repo.get_ddt_riga_snapshot.return_value = {
            **_SNAPSHOT_RIGA, "ddt_id": 999,
        }
        with self.assertRaises(ServiceError) as cm:
            resi_service.gestisci_riga(
                7, {"ddt_riga_id": 11, "tipo_reso_id": 1, "qta_operativa": "5"},
            )
        self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo.create_riga.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_crea_riga_senza_tipo(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_e_ddt_origine.return_value = dict(_RESO_DRAFT)
        repo.get_ddt_riga_snapshot.return_value = dict(_SNAPSHOT_RIGA)
        with self.assertRaises(ServiceError) as cm:
            resi_service.gestisci_riga(
                7, {"ddt_riga_id": 11, "qta_operativa": "5"},
            )
        self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo.create_riga.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_crea_riga_senza_qta_operativa(self, repo_cls) -> None:
        # `quantita` base sola NON basta: il trigger DB qta_from_operativa
        # su INSERT calcola sempre la base da qta_operativa (E_QTA_MISSING
        # se assente) -> il contratto BE richiede l'operativa.
        repo = repo_cls.return_value
        repo.get_stato_e_ddt_origine.return_value = dict(_RESO_DRAFT)
        repo.get_ddt_riga_snapshot.return_value = dict(_SNAPSHOT_RIGA)
        with self.assertRaises(ServiceError) as cm:
            resi_service.gestisci_riga(
                7, {"ddt_riga_id": 11, "tipo_reso_id": 1, "quantita": "5"},
            )
        self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo.create_riga.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_crea_riga_fulfillment_multipli(self, repo_cls) -> None:
        # Riga DDT con 2+ fulfillment (caso teorico del modello 1..n):
        # attribuire il reso a UNA sola riga ordine riaprirebbe il residuo
        # solo in parte, silenziosamente -> errore parlante.
        repo = repo_cls.return_value
        repo.get_stato_e_ddt_origine.return_value = dict(_RESO_DRAFT)
        repo.get_ddt_riga_snapshot.return_value = {
            **_SNAPSHOT_RIGA, "fulfillment_count": 2,
        }
        with self.assertRaises(ServiceError) as cm:
            resi_service.gestisci_riga(
                7, {"ddt_riga_id": 11, "tipo_reso_id": 1, "qta_operativa": "5"},
            )
        self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo.create_riga.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_aggiorna_riga_ok(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_e_ddt_origine.return_value = dict(_RESO_DRAFT)
        repo.get_riga.return_value = {"id": 3, "reso_id": 7}
        out = resi_service.aggiorna_riga(
            7, 3, {"qta_operativa": "2"},
        )
        self.assertTrue(out["updated"])
        kwargs = repo.update_riga.call_args.kwargs
        self.assertEqual(kwargs["qta_operativa"], "2")
        self.assertNotIn("articolo_id", kwargs)
        # ⛔ Lo snapshot articolo e' immutabile: fuori whitelist, e dal
        #    2026-10-20 e' un 400 invece di uno scarto silenzioso.
        repo.update_riga.reset_mock()
        with self.assertRaises(ServiceError) as ctx:
            resi_service.aggiorna_riga(7, 3, {"qta_operativa": "2", "articolo_id": "hack"})
        self.assertEqual(ctx.exception.code, "E_RESO_VALIDAZIONE")
        repo.update_riga.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_aggiorna_riga_estranea(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_e_ddt_origine.return_value = dict(_RESO_DRAFT)
        repo.get_riga.return_value = {"id": 3, "reso_id": 999}
        with self.assertRaises(ServiceError) as cm:
            resi_service.aggiorna_riga(7, 3, {"qta_operativa": "2"})
        self.assertEqual(cm.exception.code, "E_RESO_NOT_FOUND")
        repo.update_riga.assert_not_called()


class ResiCodaAccreditareTests(SimpleTestCase):
    """Filtro etichetta della coda accrediti (forma contatore, DL-26)."""

    # Scopo: etichetta valida (DOVUTA | FACOLTATIVA) passa al repository.
    @patch(_REPO, autospec=True)
    def test_etichetta_valida_passthrough(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.list_da_accreditare.return_value = ([], 0)
        for et in ("DOVUTA", "FACOLTATIVA"):
            with self.subTest(etichetta=et):
                resi_service.list_da_accreditare(etichetta=et, limit=25, offset=0)
                self.assertEqual(
                    repo.list_da_accreditare.call_args.kwargs["etichetta"], et
                )

    # Scopo: etichetta fuori whitelist -> E_RESO_VALIDAZIONE fail-fast (un
    #        valore ignoto e' un errore del chiamante, non una lista vuota).
    @patch(_REPO, autospec=True)
    def test_etichetta_invalida_400(self, repo_cls) -> None:
        with self.assertRaises(ServiceError) as ctx:
            resi_service.list_da_accreditare(
                etichetta="OBBLIGATORIA", limit=25, offset=0
            )
        self.assertEqual(ctx.exception.code, "E_RESO_VALIDAZIONE")
        repo_cls.return_value.list_da_accreditare.assert_not_called()

    # Scopo: etichetta assente -> None al repository (tutte le righe).
    @patch(_REPO, autospec=True)
    def test_etichetta_none_default(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.list_da_accreditare.return_value = ([], 0)
        resi_service.list_da_accreditare(limit=25, offset=0)
        self.assertIsNone(repo.list_da_accreditare.call_args.kwargs["etichetta"])


class ResiCodaFiltroDocumentoTests(SimpleTestCase):
    """Restrizione delle code a un documento (slice B3, richiesta FE-2)."""

    # Scopo: il filtro DDT arriva al repository. E' il caso del collegamento dal
    #        pannello situazione merce del DDT.
    @patch(_REPO, autospec=True)
    def test_filtro_ddt_passthrough(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.list_da_accreditare.return_value = ([], 0)
        resi_service.list_da_accreditare(ddt_id=140, limit=25, offset=0)
        kwargs = repo.list_da_accreditare.call_args.kwargs
        self.assertEqual(kwargs["ddt_id"], 140)
        self.assertIsNone(kwargs["ordine_id"])

    # Scopo: idem dal pannello dell'ordine, dove il legame passa dal
    #        fulfillment della riga di DDT resa e non da una colonna.
    @patch(_REPO, autospec=True)
    def test_filtro_ordine_passthrough(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.list_da_accreditare.return_value = ([], 0)
        resi_service.list_da_accreditare(ordine_id=240, limit=25, offset=0)
        kwargs = repo.list_da_accreditare.call_args.kwargs
        self.assertEqual(kwargs["ordine_id"], 240)
        self.assertIsNone(kwargs["ddt_id"])

    # Scopo: i due id sono ALTERNATIVI. Accettarli insieme vorrebbe dire due
    #        domande in una, con la seconda che restringe la prima in silenzio:
    #        l'operatore vedrebbe un elenco corto senza sapere perche'.
    #        ⚠️ E il repository non deve essere chiamato affatto.
    @patch(_REPO, autospec=True)
    def test_filtro_documento_mutuamente_esclusivo(self, repo_cls) -> None:
        for chiamata in (
            lambda: resi_service.list_da_accreditare(
                ddt_id=1, ordine_id=2, limit=25, offset=0
            ),
            lambda: resi_service.list_da_riconsegnare(
                ddt_id=1, ordine_id=2, limit=25, offset=0
            ),
        ):
            with self.subTest(chiamata=chiamata):
                with self.assertRaises(ServiceError) as ctx:
                    chiamata()
                self.assertEqual(ctx.exception.code, "E_RESO_VALIDAZIONE")
        repo_cls.return_value.list_da_accreditare.assert_not_called()
        repo_cls.return_value.list_da_riconsegnare.assert_not_called()

    # Scopo: 🔴 `?ddt_id=0` passa il parsing strict (0 e' un intero valido) e
    #        produrrebbe `WHERE v.ddt_id = 0`, cioe' una coda VUOTA. E una coda
    #        vuota si legge «non c'e' niente da fare» — il messaggio piu'
    #        sbagliato possibile su un elenco di accrediti dovuti. Deve essere
    #        un errore parlante, non una normalizzazione silenziosa.
    @patch(_REPO, autospec=True)
    def test_filtro_documento_id_non_positivo(self, repo_cls) -> None:
        for kwargs in ({"ddt_id": 0}, {"ddt_id": -1}, {"ordine_id": 0}):
            with self.subTest(**kwargs):
                with self.assertRaises(ServiceError) as ctx:
                    resi_service.list_da_accreditare(limit=25, offset=0, **kwargs)
                self.assertEqual(ctx.exception.code, "E_RESO_VALIDAZIONE")
        repo_cls.return_value.list_da_accreditare.assert_not_called()

    # Scopo: NON-regressione. La coda aperta a mano non ha nessun documento, e
    #        i due filtri devono arrivare `None` — non 0, che sarebbe un id.
    @patch(_REPO, autospec=True)
    def test_filtro_documento_assente_default(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.list_da_accreditare.return_value = ([], 0)
        repo.list_da_riconsegnare.return_value = ([], 0)
        resi_service.list_da_accreditare(limit=25, offset=0)
        resi_service.list_da_riconsegnare(limit=25, offset=0)
        for chiamata in (repo.list_da_accreditare, repo.list_da_riconsegnare):
            self.assertIsNone(chiamata.call_args.kwargs["ddt_id"])
            self.assertIsNone(chiamata.call_args.kwargs["ordine_id"])

    # Scopo: la simmetria fra le due code. Il pannello situazione merce mostra
    #        «da accreditare» e «da ri-consegnare» una sopra l'altra: dare il
    #        collegamento filtrato a una sola sarebbe un'asimmetria visibile.
    @patch(_REPO, autospec=True)
    def test_filtro_documento_su_riconsegne(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.list_da_riconsegnare.return_value = ([], 0)
        resi_service.list_da_riconsegnare(ddt_id=15848, limit=25, offset=0)
        self.assertEqual(
            repo.list_da_riconsegnare.call_args.kwargs["ddt_id"], 15848
        )

    # Scopo: un export lanciato dalla coda filtrata contiene le sole righe di
    #        quel documento. Senza la dichiarazione nel foglio «Filtri
    #        applicati» il file si leggerebbe come la coda intera — ed e' lo
    #        stesso motivo per cui l'etichetta era stata dichiarata.
    def test_etichette_export_dichiarano_il_documento(self) -> None:
        etichette = resi_service.resolve_filtri_coda_export_label(ddt_id=140)
        self.assertEqual(etichette, {"DDT (id)": 140})
        etichette = resi_service.resolve_filtri_coda_export_label(ordine_id=240)
        self.assertEqual(etichette, {"Ordine (id)": 240})
        # Nessun documento: nessuna riga in piu' nel foglio dei filtri.
        self.assertEqual(resi_service.resolve_filtri_coda_export_label(), {})


class ResiEliminaTests(ModelloDocumentoMockatoMixin, SimpleTestCase):
    """elimina_reso: hard-delete solo per bozza orfana (0 righe)."""

    @patch(_REPO, autospec=True)
    def test_elimina_reso_con_righe_rifiutato(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.count_righe.return_value = 2
        with self.assertRaises(ServiceError) as cm:
            resi_service.elimina_reso(7)
        self.assertEqual(cm.exception.code, "E_RESO_STATO_TRANSIZIONE")
        repo.delete_reso.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_elimina_reso_bozza_orfana_ok(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.count_righe.return_value = 0
        repo.delete_reso.return_value = True
        out = resi_service.elimina_reso(7)
        self.assertTrue(out["deleted"])
        repo.delete_reso.assert_called_once_with(7)


class ResiAzioniTests(SimpleTestCase):
    """conferma/annulla/genera_ddt_riconsegna: delega alle fn madri DB."""

    @patch(_REPO, autospec=True)
    def test_conferma_delega_fn_madre_light(self, repo_cls) -> None:
        # Ritorno LIGHT (parita' ddt_service.emetti): niente reload del detail
        # pesante. Lo stato di ritorno e' RILETTO dal DB dopo la fn madre
        # (la transizione target vive nella matrice, non si asserisce
        # hardcoded); nessun pre-check di esistenza (la fn alza
        # E_RESO_NOT_FOUND da sola).
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "CONFERMATO"
        out = resi_service.conferma_reso(7)
        repo.conferma.assert_called_once_with(7)
        repo.get_stato_codice.assert_called_once_with(7)
        repo.get_reso.assert_not_called()
        repo.get_capabilities.assert_not_called()
        self.assertEqual(out, {"reso_id": 7, "stato": "CONFERMATO"})

    @patch(_REPO, autospec=True)
    def test_conferma_not_found_da_fn(self, repo_cls) -> None:
        # Il NOT_FOUND arriva dalla fn madre (RAISE con E_RESO_NOT_FOUND nel
        # testo/context) tradotto da _db_errors: nessun pre-check duplicato.
        repo = repo_cls.return_value
        repo.conferma.side_effect = DatabaseError(
            "Reso non trovato.\nCONTEXT: ... 'E_RESO_NOT_FOUND' ...",
        )
        with self.assertRaises(ServiceError) as cm:
            resi_service.conferma_reso(99)
        self.assertEqual(cm.exception.code, "E_RESO_NOT_FOUND")

    @patch(f"{_SVC}.transaction")
    @patch(_REPO, autospec=True)
    def test_conferma_no_atomic_extra(self, repo_cls, mock_tx) -> None:
        # L'atomicita' vive DENTRO fn_conferma_reso: il service NON apre un
        # transaction.atomic() extra (una sola SELECT fn_madre).
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "CONFERMATO"
        resi_service.conferma_reso(7)
        mock_tx.atomic.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_annulla_delega_fn_madre_light(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "ANNULLATO"
        out = resi_service.annulla_reso(7)
        repo.annulla.assert_called_once_with(7)
        self.assertEqual(out, {"reso_id": 7, "stato": "ANNULLATO"})

    @patch(_DDT_REPO, autospec=True)
    @patch(_ATOMIC, return_value=nullcontext())
    @patch(_REPO, autospec=True)
    def test_riconsegna_delega_e_ritorna(self, repo_cls, _atomic, ddt_cls) -> None:
        repo = repo_cls.return_value
        repo.genera_ddt_riconsegna.return_value = 42

        out = resi_service.genera_ddt_riconsegna(
            7, [{"resi_riga_id": 71, "qta": "3"}],
        )

        repo.genera_ddt_riconsegna.assert_called_once_with(
            7, [{"resi_riga_id": 71, "qta": "3"}], None,
        )
        # Il DDT di ri-spedizione nasce in DRAFT: numero deterministicamente
        # None (nessun re-read).
        self.assertEqual(out, {"reso_id": 7, "ddt_id": 42, "numero": None})
        # Dopo la cascata dal DDT d'origine, lo slot di default sul DDT nato
        # (il DB lo riempie solo se e' rimasto vuoto): come il DDT da ordine.
        ddt_cls.return_value.riempi_indirizzo_default.assert_called_once_with(42)

    @patch(_DDT_REPO, autospec=True)
    @patch(_ATOMIC, return_value=nullcontext())
    @patch(_REPO, autospec=True)
    def test_riconsegna_errore_del_default_sale(self, repo_cls, atomic, ddt_cls) -> None:
        # Verbo e default nella stessa transazione: non e' best-effort, un
        # errore sale e annulla anche il DDT di ri-spedizione.
        repo_cls.return_value.genera_ddt_riconsegna.return_value = 42
        ddt_cls.return_value.riempi_indirizzo_default.side_effect = RuntimeError("DB")
        with self.assertRaises(RuntimeError):
            resi_service.genera_ddt_riconsegna(7)
        atomic.assert_called_once_with()

    @patch(_REPO, autospec=True)
    def test_riconsegna_righe_vuote(self, repo_cls) -> None:
        # Lista vuota NON degrada a None = "ri-spedisci tutto": errore
        # parlante (mirror _parse_righe_evasione di views_ordini).
        repo = repo_cls.return_value
        with self.assertRaises(ServiceError) as cm:
            resi_service.genera_ddt_riconsegna(7, [])
        self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo.genera_ddt_riconsegna.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_riconsegna_righe_non_lista(self, repo_cls) -> None:
        # Body malformato (righe non-lista) -> 400, non ri-spedizione totale.
        repo = repo_cls.return_value
        with self.assertRaises(ServiceError) as cm:
            resi_service.genera_ddt_riconsegna(7, {"resi_riga_id": 71})
        self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo.genera_ddt_riconsegna.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_riconsegna_riga_senza_qta(self, repo_cls) -> None:
        repo = repo_cls.return_value
        with self.assertRaises(ServiceError) as cm:
            resi_service.genera_ddt_riconsegna(7, [{"resi_riga_id": 71}])
        self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo.genera_ddt_riconsegna.assert_not_called()


class ResiChiusuraRiconsegnaTests(SimpleTestCase):
    """L'ALTRA uscita della copertura: chiudi/riapri la ri-consegna (rinuncia).

    Delega alle fn madri DB `fn_chiudi_riconsegna_reso` /
    `fn_riapri_riconsegna_reso`; la validazione righe e' la stessa della
    ri-spedizione (le due uscite condividono contratto e copertura).
    """

    @patch(_REPO, autospec=True)
    def test_chiudi_delega_e_ritorna(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.chiudi_riconsegna.return_value = 2

        out = resi_service.chiudi_riconsegna(
            7, [{"resi_riga_id": 71, "qta": "3"}], "cliente non lo rivuole",
        )

        repo.chiudi_riconsegna.assert_called_once_with(
            7, [{"resi_riga_id": 71, "qta": "3"}], "cliente non lo rivuole",
        )
        self.assertEqual(out, {"reso_id": 7, "righe_chiuse": 2})

    @patch(_REPO, autospec=True)
    def test_chiudi_note_vuote_a_null(self, repo_cls) -> None:
        # Testo libero facoltativo: whitespace -> NULL, mai stringa vuota a DB
        # ([[feedback_null_vs_empty]]).
        repo = repo_cls.return_value
        repo.chiudi_riconsegna.return_value = 1
        resi_service.chiudi_riconsegna(7, None, "   ")
        self.assertIsNone(repo.chiudi_riconsegna.call_args[0][2])

    @patch(_REPO, autospec=True)
    def test_chiudi_note_trimmate(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.chiudi_riconsegna.return_value = 1
        resi_service.chiudi_riconsegna(7, None, "  merce non ripristinabile  ")
        self.assertEqual(
            repo.chiudi_riconsegna.call_args[0][2], "merce non ripristinabile",
        )

    @patch(_REPO, autospec=True)
    def test_chiudi_note_tipo_non_stringa_rifiutata(self, repo_cls) -> None:
        # Un `note` non testuale e' un body malformato: 400 parlante qui, non
        # un parametro varchar imprevedibile passato a psycopg.
        repo = repo_cls.return_value
        for note in (123, {"x": 1}, ["a"]):
            with self.subTest(note=note):
                with self.assertRaises(ServiceError) as cm:
                    resi_service.chiudi_riconsegna(7, None, note)
                self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo.chiudi_riconsegna.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_chiudi_righe_none_e_tutta_la_copertura(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.chiudi_riconsegna.return_value = 3
        resi_service.chiudi_riconsegna(7)
        repo.chiudi_riconsegna.assert_called_once_with(7, None, None)

    @patch(_REPO, autospec=True)
    def test_chiudi_righe_degeneri_rifiutate(self, repo_cls) -> None:
        # Il degrado silenzioso a "rendi definitiva TUTTA la copertura" e' qui
        # piu' grave che sulla gemella: rinuncerebbe a merce che l'operatore
        # voleva ri-spedire.
        repo = repo_cls.return_value
        for righe in ([], {"resi_riga_id": 71}, [{"resi_riga_id": 71}]):
            with self.subTest(righe=righe):
                with self.assertRaises(ServiceError) as cm:
                    resi_service.chiudi_riconsegna(7, righe)
                self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo.chiudi_riconsegna.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_riapri_delega_e_ritorna(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.riapri_riconsegna.return_value = 1

        out = resi_service.riapri_riconsegna(7, [{"resi_riga_id": 71, "qta": "3"}])

        repo.riapri_riconsegna.assert_called_once_with(
            7, [{"resi_riga_id": 71, "qta": "3"}],
        )
        self.assertEqual(out, {"reso_id": 7, "righe_riaperte": 1})

    @patch(_REPO, autospec=True)
    def test_riapri_righe_degeneri_rifiutate(self, repo_cls) -> None:
        repo = repo_cls.return_value
        with self.assertRaises(ServiceError) as cm:
            resi_service.riapri_riconsegna(7, [])
        self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo.riapri_riconsegna.assert_not_called()

    @patch(f"{_SVC}.transaction")
    @patch(_REPO, autospec=True)
    def test_nessun_atomic_extra(self, repo_cls, mock_tx) -> None:
        # Le madri DB sono gia' atomiche: un atomic applicativo sopra sarebbe
        # solo un lock in piu' (stessa regola della ri-spedizione).
        repo = repo_cls.return_value
        repo.chiudi_riconsegna.return_value = 1
        repo.riapri_riconsegna.return_value = 1
        resi_service.chiudi_riconsegna(7)
        resi_service.riapri_riconsegna(7)
        mock_tx.atomic.assert_not_called()


class ResiAccreditoTests(SimpleTestCase):
    """Il verbo dell'accredito: delega alla madre `fn_accredita_riga_reso`."""

    # Scopo: 🔴 la madre e' `RETURNS TABLE` e ritorna UNA riga per rettifica
    # creata (kit: una per componente; consumo su piu' righe di fattura a
    # prezzi diversi: altrettante). Il service le rilancia TUTTE: prenderne una
    # sarebbe verde su ogni caso semplice e muto sui kit, cioe' esattamente i
    # casi per cui il cantiere esiste.
    @patch(_REPO, autospec=True)
    def test_accredito_ritorna_tutte_le_rettifiche(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.accredita_riga_reso.return_value = [
            {"accredito_id": 901, "commessa_attivita_id": 5501,
             "fattura_riga_rettificata_id": 7101,
             "qta": "-3.000000", "qta_partita": "-3.000000"},
            {"accredito_id": 902, "commessa_attivita_id": 5502,
             "fattura_riga_rettificata_id": 7102,
             "qta": "-1.000000", "qta_partita": "-1.000000"},
        ]

        out = resi_service.accredita_riga_reso(5797)

        repo.accredita_riga_reso.assert_called_once_with(5797)
        self.assertEqual(out["resi_riga_id"], 5797)
        self.assertEqual(len(out["accrediti"]), 2)
        self.assertEqual(
            [a["accredito_id"] for a in out["accrediti"]], [901, 902],
        )

    # Scopo: nessun guard applicativo che ripeta la madre. «E' in coda»,
    # «l'attivita' e' finita in fattura», «non e' gia' accreditata» stanno nel
    # DB: il service non deve leggere la coda ne' lo stato del reso prima di
    # chiamare (due copie della stessa regola divergono, e la piu' vecchia non
    # fa rumore).
    @patch(_REPO, autospec=True)
    def test_accredito_nessun_precheck_applicativo(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.accredita_riga_reso.return_value = []

        resi_service.accredita_riga_reso(5797)

        repo.list_da_accreditare.assert_not_called()
        repo.get_stato_codice.assert_not_called()
        repo.get_riga.assert_not_called()
        repo.get_capabilities.assert_not_called()

    @patch(f"{_SVC}.transaction")
    @patch(_REPO, autospec=True)
    def test_accredito_no_atomic_extra(self, repo_cls, mock_tx) -> None:
        # L'atomicita' vive DENTRO fn_accredita_riga_reso: una sola
        # SELECT fn_(), nessun transaction.atomic() nel service.
        repo = repo_cls.return_value
        repo.accredita_riga_reso.return_value = []
        resi_service.accredita_riga_reso(5797)
        mock_tx.atomic.assert_not_called()

    # Scopo: i codici di dominio dell'accredito arrivano dalla madre e passano
    # da _db_errors (routing UI del FE). Il doppio click e' il caso vivo:
    # E_ACCREDITO_GIA_ESEGUITO, non un 500.
    @patch(_REPO, autospec=True)
    def test_accredito_codice_dominio_dalla_madre(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.accredita_riga_reso.side_effect = DatabaseError(
            "E_ACCREDITO_GIA_ESEGUITO: Riga di reso 5797: accredito gia' "
            "eseguito.",
        )
        with self.assertRaises(ServiceError) as cm:
            resi_service.accredita_riga_reso(5797)
        self.assertEqual(cm.exception.code, "E_ACCREDITO_GIA_ESEGUITO")


class ResiAccreditoMassivoTests(SimpleTestCase):
    """Il fan-out del verbo: un endpoint solo, e la riga singola e' una lista di uno."""

    # Scopo: 🔴 il test che fissa la scelta di fondo — un esito parziale NON
    # solleva. Il verbo non e' l'atto fiscale (il documento nasce dopo, nel
    # giro di fatturazione), quindi sollevare butterebbe via anche le righe
    # riuscite; e le righe rifiutate restano semplicemente in coda.
    @patch(f"{_SVC}.run_fan_out")
    @patch(_REPO, autospec=True)
    def test_massivo_esito_parziale_non_solleva(self, repo_cls, _fan_out) -> None:
        repo = repo_cls.return_value
        repo.accredita_riga_reso.side_effect = [
            [{"accredito_id": 901}],
            DatabaseError("E_ACCREDITO_GIA_ESEGUITO: gia' eseguito."),
            [{"accredito_id": 903}],
        ]
        _fan_out.side_effect = _fan_out_reale

        out = resi_service.accredita_righe_reso([1, 2, 3])

        self.assertEqual(out["esito"], "PARZIALE")
        self.assertEqual((out["totale"], out["ok"]), (3, 2))
        self.assertEqual(len(out["falliti"]), 1)
        self.assertEqual(out["falliti"][0]["resi_riga_id"], 2)
        self.assertEqual(out["falliti"][0]["codice"], "E_ACCREDITO_GIA_ESEGUITO")

    # Scopo: anche «tutte fallite» e' un report a 200. Sollevare qui darebbe al
    # frontend DUE forme da leggere per la stessa domanda (una lista di esiti
    # oppure un errore): e' lo stesso argomento per cui l'endpoint e' uno solo.
    @patch(f"{_SVC}.run_fan_out")
    @patch(_REPO, autospec=True)
    def test_massivo_tutte_fallite_non_solleva(self, repo_cls, _fan_out) -> None:
        repo = repo_cls.return_value
        repo.accredita_riga_reso.side_effect = DatabaseError(
            "E_ACCREDITO_NON_IN_CODA: niente da accreditare.",
        )
        _fan_out.side_effect = _fan_out_reale

        out = resi_service.accredita_righe_reso([1, 2])

        self.assertEqual(out["esito"], "ERRORE")
        self.assertEqual(out["ok"], 0)
        self.assertEqual(
            [f["codice"] for f in out["falliti"]],
            ["E_ACCREDITO_NON_IN_CODA"] * 2,
        )

    # Scopo: le rettifiche di righe diverse finiscono in una lista sola, e ogni
    # riga porta il proprio `resi_riga_id`: senza, il chiamante non saprebbe di
    # chi e' la rettifica che sta guardando (su un kit ne arrivano N per riga).
    @patch(f"{_SVC}.run_fan_out")
    @patch(_REPO, autospec=True)
    def test_massivo_accrediti_portano_la_riga(self, repo_cls, _fan_out) -> None:
        repo = repo_cls.return_value
        repo.accredita_riga_reso.side_effect = [
            [{"accredito_id": 901}, {"accredito_id": 902}],
            [{"accredito_id": 903}],
        ]
        _fan_out.side_effect = _fan_out_reale

        out = resi_service.accredita_righe_reso([7, 9])

        self.assertEqual(
            [(a["resi_riga_id"], a["accredito_id"]) for a in out["accrediti"]],
            [(7, 901), (7, 902), (9, 903)],
        )

    # Scopo: lo stesso id due volte nel body produrrebbe un
    # E_ACCREDITO_GIA_ESEGUITO AUTOINFLITTO, che a video sembra un difetto del
    # sistema e invece e' il body. L'ordine si preserva: e' quello in cui
    # l'operatore ha spuntato le righe.
    @patch(f"{_SVC}.run_fan_out")
    @patch(_REPO, autospec=True)
    def test_massivo_dedup_preserva_ordine(self, repo_cls, _fan_out) -> None:
        repo = repo_cls.return_value
        repo.accredita_riga_reso.return_value = []
        _fan_out.side_effect = _fan_out_reale

        resi_service.accredita_righe_reso([9, 7, 9, "7", 5])

        self.assertEqual(
            [c.args[0] for c in repo.accredita_riga_reso.call_args_list],
            [9, 7, 5],
        )

    @patch(_REPO, autospec=True)
    def test_massivo_lista_vuota_rifiutata(self, repo_cls) -> None:
        # Lista vuota NON e' «tutte»: indovinare male qui significa lavorare un
        # perimetro che nessuno ha chiesto, su un documento fiscale.
        with self.assertRaises(ServiceError) as cm:
            resi_service.accredita_righe_reso([])
        self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo_cls.return_value.accredita_riga_reso.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_massivo_lista_degenere_rifiutata(self, repo_cls) -> None:
        # ⚠️ `True` e' incluso apposta: in Python `bool` e' un `int`, quindi
        # senza il controllo di tipo esplicito passerebbe come riga 1.
        for degenere in (None, "5797", 5797, [0], [-1], ["banana"], [True], [None]):
            with self.subTest(degenere=degenere):
                with self.assertRaises(ServiceError) as cm:
                    resi_service.accredita_righe_reso(degenere)
                self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo_cls.return_value.accredita_riga_reso.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_massivo_cap_rispettato(self, repo_cls) -> None:
        troppi = list(range(1, resi_service.MAX_ACCREDITI_MASSIVI + 2))
        with self.assertRaises(ServiceError) as cm:
            resi_service.accredita_righe_reso(troppi)
        self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo_cls.return_value.accredita_riga_reso.assert_not_called()


class ResiAnnulloAccreditoTests(SimpleTestCase):
    """L'annullo dell'accredito (D-NC-11): a monte del documento, non il reset."""

    @patch(_REPO, autospec=True)
    def test_annullo_delega_alla_madre(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_riga.return_value = {"id": 24, "reso_id": 7}
        repo.annulla_accredito_riga_reso.return_value = [
            {"accredito_id": 901}, {"accredito_id": 902},
        ]

        out = resi_service.annulla_accredito_riga_reso(7, 24, "riga sbagliata")

        repo.annulla_accredito_riga_reso.assert_called_once_with(24, "riga sbagliata")
        self.assertEqual(out["resi_riga_id"], 24)
        self.assertEqual(len(out["rimosse"]), 2)

    # Scopo: la madre non conosce il reso, quindi l'appartenenza della riga al
    # percorso e' l'unico guard legittimo qui — senza,
    # `/resi/999/righe/24/annulla-accredito/` annullerebbe l'accredito della
    # riga 24 di un ALTRO reso.
    @patch(_REPO, autospec=True)
    def test_annullo_riga_di_altro_reso_rifiutata(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_riga.return_value = {"id": 24, "reso_id": 8}
        with self.assertRaises(ServiceError) as cm:
            resi_service.annulla_accredito_riga_reso(7, 24, "motivo")
        self.assertEqual(cm.exception.code, "E_RESO_NOT_FOUND")
        repo.annulla_accredito_riga_reso.assert_not_called()

    # Scopo: whitespace -> NULL e' normalizzazione, non un guard: il rifiuto lo
    # fa la madre (E_ACCREDITO_MOTIVO_OBBLIGATORIO), che e' anche l'unica a
    # sapere perche' il motivo serve — l'annullo cancella le righe di ponte,
    # quindi la traccia del PERCHE' resta solo nel log.
    @patch(_REPO, autospec=True)
    def test_annullo_motivo_vuoto_a_null(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_riga.return_value = {"id": 24, "reso_id": 7}
        repo.annulla_accredito_riga_reso.return_value = []
        resi_service.annulla_accredito_riga_reso(7, 24, "   ")
        repo.annulla_accredito_riga_reso.assert_called_once_with(24, None)

    @patch(_REPO, autospec=True)
    def test_annullo_codice_dominio_dalla_madre(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_riga.return_value = {"id": 24, "reso_id": 7}
        repo.annulla_accredito_riga_reso.side_effect = DatabaseError(
            "E_ACCREDITO_ANNULLO_NON_AMMESSO: rettifiche gia' emesse.",
        )
        with self.assertRaises(ServiceError) as cm:
            resi_service.annulla_accredito_riga_reso(7, 24, "motivo")
        self.assertEqual(cm.exception.code, "E_ACCREDITO_ANNULLO_NON_AMMESSO")

    # Scopo: il motivo passa dallo STESSO parser della nota di rinuncia, che
    # rifiuta i tipi non stringa invece di consegnarli al driver. E' la meta'
    # che una normalizzazione scritta al volo (`empty_to_none` se e' str, else
    # passa) dimentica sempre: un dict sarebbe arrivato a psycopg.
    @patch(_REPO, autospec=True)
    def test_annullo_motivo_non_stringa_rifiutato(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_riga.return_value = {"id": 24, "reso_id": 7}
        for degenere in ({"motivo": "x"}, ["x"], 42):
            with self.subTest(degenere=degenere):
                with self.assertRaises(ServiceError) as cm:
                    resi_service.annulla_accredito_riga_reso(7, 24, degenere)
                self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo.annulla_accredito_riga_reso.assert_not_called()

    @patch(f"{_SVC}.transaction")
    @patch(_REPO, autospec=True)
    def test_annullo_no_atomic_extra(self, repo_cls, mock_tx) -> None:
        repo = repo_cls.return_value
        repo.get_riga.return_value = {"id": 24, "reso_id": 7}
        repo.annulla_accredito_riga_reso.return_value = []
        resi_service.annulla_accredito_riga_reso(7, 24, "motivo")
        mock_tx.atomic.assert_not_called()


class ResiDbErrorsTests(SimpleTestCase):
    """Traduzione errori DB di _db_errors (gemello DdtDbErrorsTests)."""

    def test_integrity_error_fk_mappato(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            with _db_errors("test"):
                raise IntegrityError(
                    'insert or update on table "resi_righe" violates foreign '
                    'key constraint "fk_resi_righe_tipo_reso"',
                )
        self.assertEqual(cm.exception.code, "E_VENDITE_FK")

    def test_integrity_error_fallback(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            with _db_errors("test"):
                raise IntegrityError("vincolo sconosciuto xyz")
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")

    def test_database_error_trigger_code(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            with _db_errors("test"):
                raise DatabaseError(
                    "E_RESO_QTA_SUPERA_CONSEGNATO: quantita' resa superiore "
                    "alla quantita' consegnata residua",
                )
        self.assertEqual(cm.exception.code, "E_RESO_QTA_SUPERA_CONSEGNATO")


# Scopo: Le righe «leggono prima la testata» (2026-09-21, allineamento a
#        api.md §Scope emittente): un reso fuori perimetro RLS — `None` dal
#        repository, come un id inesistente — e' un 404, non un 200 vuoto.
#
# Indice:
# 51) test_list_righe_reso_non_trovato_e_404
# 52) test_list_righe_con_testata_delega_al_repo
class ResiSatellitiTestataTests(SimpleTestCase):
    @patch(_REPO, autospec=True)
    def test_list_righe_reso_non_trovato_e_404(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_reso.return_value = None
        with self.assertRaises(ServiceError) as cm:
            resi_service.list_righe(99)
        self.assertEqual(cm.exception.code, "E_RESO_NOT_FOUND")
        repo.list_righe.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_list_righe_con_testata_delega_al_repo(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_reso.return_value = {"id": 7, "stato_codice_interno": "DRAFT"}
        repo.list_righe.return_value = [{"id": 31}]
        self.assertEqual(resi_service.list_righe(7), [{"id": 31}])
        repo.list_righe.assert_called_once_with(7)


# B2 (3-bis R-1b, piano-be-fe-magazzino-lotto-3): il trasporto dei rientri.
# ⚠️ Le regole (bozza, prelievo della riga di bolla, quadratura alla conferma)
# sono del DB: lo prova `tests/db/test_ddt_cambia_stato_db` (test 7).
class ResiRientriTests(SimpleTestCase):
    @patch(_REPO, autospec=True)
    def test_get_rientri_raggruppa_per_voce(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_testata_rientri.return_value = {"reso_id": 4, "muove_merce": True}
        repo.list_merce_da_rientrare.return_value = [
            {"resi_riga_id": 1, "ddt_riga_componente_id": 10},
            {"resi_riga_id": 1, "ddt_riga_componente_id": 11},
        ]
        repo.list_prelievi_origine.return_value = [
            {"resi_riga_id": 1, "id": 500, "ddt_riga_componente_id": 11},
            {"resi_riga_id": 1, "id": 501, "ddt_riga_componente_id": 10},
        ]
        repo.list_rientri.return_value = [
            {"resi_riga_id": 1, "id": 900, "ddt_riga_componente_id": 11},
        ]
        out = resi_service.get_rientri(4)
        self.assertEqual(
            [([p["id"] for p in v["prelievi_origine"]], [r["id"] for r in v["rientri"]]) for v in out["voci"]],
            [([501], []), ([500], [900])],
        )

    @patch(_REPO, autospec=True)
    def test_crea_rientro_vuole_il_prelievo(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_riga.return_value = {"id": 7, "reso_id": 4}
        with self.assertRaises(ServiceError) as cm:
            resi_service.crea_rientro(4, 7, {"qta": "1"})
        self.assertEqual(cm.exception.code, "E_RESO_VALIDAZIONE")
        repo.create_rientro.assert_not_called()

    @patch(_REPO, autospec=True)
    def test_rientro_di_altra_riga_e_404(self, repo_cls) -> None:
        repo = repo_cls.return_value
        repo.get_stato_codice.return_value = "DRAFT"
        repo.get_riga.return_value = {"id": 7, "reso_id": 4}
        repo.get_rientro.return_value = {"id": 9, "resi_riga_id": 8}
        with self.assertRaises(ServiceError) as cm:
            resi_service.elimina_rientro(4, 7, 9)
        self.assertEqual(cm.exception.code, "E_RESO_NOT_FOUND")
        repo.delete_rientro.assert_not_called()
