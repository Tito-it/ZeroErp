# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit del PERCORSO 3 — `DocumentGenerationService.ristampa_fedele`
#        (brief-ristampa-fedele-documenti, 2026-08-03). Mock-only, nessun DB.
#
#        Cosa presidiano davvero questi test: che la ristampa **legga** gli
#        ingredienti congelati invece di ricostruirli. E' l'unica cosa che
#        distingue una ristampa fedele da un documento nuovo travestito da
#        vecchio, e non si vede guardando il PDF prodotto — si vede solo
#        guardando CHI viene chiamato e CON COSA (test 0, 1 e 2).
#
#        Indice test (0..N):
#         0. ristampa_usa_versione_pinnata_e_contesto_congelato
#         1. ristampa_non_ricostruisce_il_contesto (nessun context_builder)
#         2. ristampa_non_persiste_documento_ne_file
#         3. ristampa_pdf_hash_coincide_esito_ok
#         4. ristampa_pdf_hash_diverso_non_solleva_ed_e_dichiarato
#         5. ristampa_template_hash_diverso_dichiarato
#         6. ristampa_documento_inesistente_o_fuori_scope_not_found
#         7. ristampa_senza_versione_pinnata_raises_validation
#         8. ristampa_versione_pinnata_sparita_raises_not_found
#         9. ristampa_contesto_vuoto_raises_validation
#        10. ristampa_evento_audit_emesso_con_dettaglio_fedelta
#        11. ristampa_evento_fallito_ritorna_comunque_il_pdf
#        12. ristampa_anon_user_raises_validation
#        13. ristampa_input_guard_id_non_positivo
#        14. ristampa_versione_obsoleta_e_ammessa
#        15. [presidio dichiarato, expectedFailure] ristampa_pagina_cambiata_
#            dichiarata: il template_hash non vede le colonne della pagina
# ------------------------------------------------------------

from __future__ import annotations

import hashlib
from typing import Any
from unittest import expectedFailure
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)
from apps.documenti.tests.services.generazione_fakes import (
    make_user,
    patch_render,
    patch_scope,
    service_with_mocks,
)

_PDF = b"%PDF-1.4 ristampa"
_PDF_HASH = hashlib.sha256(_PDF).hexdigest()

# Contesto CONGELATO: porta la chiave `descrizione` dell'emittente, che e'
# quella della v1 del template. Dopo il cantiere emittente (2026-08-03) il
# nome corrente e' `ragione_sociale`: se la ristampa ricostruisse il contesto
# di oggi, questa chiave non ci sarebbe. E' il caso di prova del brief §6.4.
_CONTEXT_CONGELATO: dict[str, Any] = {
    "numero": 12,
    "emittente_fiscale": {"id": 11, "codice": "EF-01", "descrizione": "Vecchio Nome SRL"},
}


# Scopo: versione PINNATA del documento (v1), quella con cui nacque.
def _versione_pinnata(stato: str = "OBSOLETA") -> dict[str, Any]:
    return {
        "id": 12,
        "versione": 1,
        "stato": stato,
        "html_template": "<p>{{ emittente_fiscale.descrizione }}</p>",
        "css_template": None,
        "markdown_template": None,
        "render_engine_codice_interno": "WEASYPRINT",
    }


# Scopo: template_hash coerente con la versione pinnata (stessa formula del
#        service: html \x00 css \x00 markdown).
def _template_hash_di(versione: dict[str, Any]) -> str:
    composite = (
        f"{versione.get('html_template') or ''}\x00"
        f"{versione.get('css_template') or ''}\x00"
        f"{versione.get('markdown_template') or ''}"
    )
    return hashlib.sha256(composite.encode("utf-8")).hexdigest()


# Scopo: snapshot congelato del documento generato.
def _snapshot(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": 99,
        "uid": "uid-doc-99",
        "template_documento_id": 7,
        "template_versione_id": 12,
        "sorgente_tipo_id": 10,
        "sorgente_uid": "uid-prev",
        "nome_file": "offerta-12.pdf",
        "context_json": dict(_CONTEXT_CONGELATO),
        "context_hash": "a" * 64,
        "template_hash": _template_hash_di(_versione_pinnata()),
        "pdf_hash": _PDF_HASH,
        "emittente_fiscale_id": 11,
    }
    base.update(overrides)
    return base


def _patch_atomic():
    return patch(
        "apps.documenti.services.document_generation_service.transaction.atomic",
    )


class RistampaFedeleTests(SimpleTestCase):
    """Percorso 3: ri-renderizza l'originale, non ne emette uno nuovo."""

    # 0. Il cuore: versione PINNATA (non la pubblicata) + contesto CONGELATO
    #    (non ricostruito) arrivano al render esattamente come sono a DB.
    def test_ristampa_usa_versione_pinnata_e_contesto_congelato(self) -> None:
        versione = _versione_pinnata()
        svc, repo, _, _ = service_with_mocks(repo_methods={
            "get_documento_generato_snapshot": _snapshot(),
            "get_versione_by_id": versione,
        })
        with patch_scope(), _patch_atomic(), patch_render(_PDF) as mock_render, \
                patch.object(DocumentGenerationService, "_risolutore_asset") as mock_ris:
            result = svc.ristampa_fedele(make_user(), 99)

        # Gli asset: quelli dell'emittente del DOCUMENTO, anche se oggi scaduti
        # o disattivati (sono immutabili: il codice_interno indica il file di
        # allora, decisione Tid 2026-10-01).
        mock_ris.assert_called_once_with(11, solo_validi=False)
        self.assertIs(mock_render.call_args.kwargs["risolvi_asset"], mock_ris.return_value)

        # La versione caricata e' quella pinnata sul documento.
        repo.get_versione_by_id.assert_called_once_with(12)
        # NON e' stata chiesta la versione che stampa oggi (la porta della
        # stampa nuova): sarebbe l'errore che rende la "ristampa" un documento
        # nuovo.
        repo.risolvi_template_applicabile.assert_not_called()
        repo.get_versione.assert_not_called()

        kwargs = mock_render.call_args.kwargs
        self.assertIs(kwargs["template_versione"], versione)
        # Il contesto e' quello congelato, chiave vecchia inclusa (§6.4).
        self.assertEqual(
            kwargs["context"]["emittente_fiscale"]["descrizione"], "Vecchio Nome SRL",
        )
        self.assertEqual(result["pdf_bytes"], _PDF)
        self.assertEqual(result["nome_file"], "offerta-12.pdf")
        self.assertEqual(result["template_versione_id"], 12)

    # 1. Nessun context_builder invocato: il contesto si legge, non si costruisce.
    def test_ristampa_non_ricostruisce_il_contesto(self) -> None:
        svc, _, _, _ = service_with_mocks(repo_methods={
            "get_documento_generato_snapshot": _snapshot(),
            "get_versione_by_id": _versione_pinnata(),
        })
        with patch_scope(), _patch_atomic(), patch_render(_PDF):
            with patch(
                "apps.documenti.services.document_generation_service.get_builder_del_template",
            ) as mock_builder:
                svc.ristampa_fedele(make_user(), 99)
        mock_builder.assert_not_called()

    # 2. Non e' un'emissione: nessuna riga nuova, nessun file, nessun
    #    progressivo consumato (§5.1.4 del brief).
    def test_ristampa_non_persiste_documento_ne_file(self) -> None:
        svc, repo, _, _ = service_with_mocks(repo_methods={
            "get_documento_generato_snapshot": _snapshot(),
            "get_versione_by_id": _versione_pinnata(),
        })
        with patch_scope(), _patch_atomic(), patch_render(_PDF):
            svc.ristampa_fedele(make_user(), 99)
        repo.create_documento_generato.assert_not_called()
        repo.create_documento_generato_file.assert_not_called()
        repo.next_progressivo_sorgente.assert_not_called()

    # 3. Byte identici -> match dichiarato, evento OK.
    def test_ristampa_pdf_hash_coincide_esito_ok(self) -> None:
        svc, repo, _, _ = service_with_mocks(repo_methods={
            "get_documento_generato_snapshot": _snapshot(),
            "get_versione_by_id": _versione_pinnata(),
        })
        with patch_scope(), _patch_atomic(), patch_render(_PDF):
            result = svc.ristampa_fedele(make_user(), 99)
        self.assertTrue(result["pdf_hash_match"])
        self.assertEqual(result["pdf_hash_ristampa"], _PDF_HASH)
        evento = repo.emit_evento_documento.call_args.args[0]
        self.assertEqual(evento["esito"], "OK")

    # 4. Byte diversi (renderer non deterministico) -> NON solleva: la
    #    decisione §8.2 e' "fedele nel contenuto, non nei byte", e il fatto
    #    va DETTO invece che nascosto.
    def test_ristampa_pdf_hash_diverso_non_solleva_ed_e_dichiarato(self) -> None:
        svc, repo, _, _ = service_with_mocks(repo_methods={
            "get_documento_generato_snapshot": _snapshot(pdf_hash="f" * 64),
            "get_versione_by_id": _versione_pinnata(),
        })
        with patch_scope(), _patch_atomic(), patch_render(_PDF):
            result = svc.ristampa_fedele(make_user(), 99)
        self.assertFalse(result["pdf_hash_match"])
        self.assertEqual(result["pdf_hash_atteso"], "f" * 64)
        self.assertEqual(result["pdf_hash_ristampa"], _PDF_HASH)
        # Il PDF esce comunque.
        self.assertEqual(result["pdf_bytes"], _PDF)
        # L'evento lo registra come WARN (valore ammesso dal CHECK esito).
        evento = repo.emit_evento_documento.call_args.args[0]
        self.assertEqual(evento["esito"], "WARN")
        self.assertFalse(evento["detail"]["pdf_hash_match"])

    # 5. Il template_hash congelato non combacia con la versione caricata:
    #    la versione e' cambiata dopo la generazione (possibile solo su BOZZA).
    #    Dichiarato, non bloccante.
    def test_ristampa_template_hash_diverso_dichiarato(self) -> None:
        svc, _, _, _ = service_with_mocks(repo_methods={
            "get_documento_generato_snapshot": _snapshot(template_hash="9" * 64),
            "get_versione_by_id": _versione_pinnata(),
        })
        with patch_scope(), _patch_atomic(), patch_render(_PDF):
            result = svc.ristampa_fedele(make_user(), 99)
        self.assertFalse(result["template_hash_match"])
        self.assertTrue(result["pdf_hash_match"])

    # 6. Documento inesistente o fuori scope emittente -> 404 unificato,
    #    nessun render sprecato.
    def test_ristampa_documento_inesistente_o_fuori_scope_not_found(self) -> None:
        svc, repo, _, _ = service_with_mocks(repo_methods={
            "get_documento_generato_snapshot": None,
        })
        with patch_scope([11]), patch_render(_PDF) as mock_render:
            with self.assertRaises(ServiceError) as ctx:
                svc.ristampa_fedele(make_user(), 999)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        mock_render.assert_not_called()
        repo.emit_evento_documento.assert_not_called()

    # 7. Documento senza versione pinnata: non e' ristampabile fedelmente, e
    #    va detto con un messaggio di dominio (non un crash a valle).
    def test_ristampa_senza_versione_pinnata_raises_validation(self) -> None:
        svc, repo, _, _ = service_with_mocks(repo_methods={
            "get_documento_generato_snapshot": _snapshot(template_versione_id=None),
        })
        with patch_scope(), patch_render(_PDF) as mock_render:
            with self.assertRaises(ServiceError) as ctx:
                svc.ristampa_fedele(make_user(), 99)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        mock_render.assert_not_called()
        repo.get_versione_by_id.assert_not_called()

    # 8. Versione pinnata sparita dal DB (non dovrebbe: il DB la protegge
    #    dalla cancellazione finche' e' referenziata) -> 404 parlante.
    def test_ristampa_versione_pinnata_sparita_raises_not_found(self) -> None:
        svc, _, _, _ = service_with_mocks(repo_methods={
            "get_documento_generato_snapshot": _snapshot(),
            "get_versione_by_id": None,
        })
        with patch_scope(), patch_render(_PDF) as mock_render:
            with self.assertRaises(ServiceError) as ctx:
                svc.ristampa_fedele(make_user(), 99)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        mock_render.assert_not_called()

    # 9. Contesto congelato vuoto: il render StrictUndefined fallirebbe
    #    comunque, ma con un errore che parla di Jinja invece che del
    #    documento. Meglio dirlo prima e nel linguaggio del dominio.
    def test_ristampa_contesto_vuoto_raises_validation(self) -> None:
        svc, _, _, _ = service_with_mocks(repo_methods={
            "get_documento_generato_snapshot": _snapshot(context_json={}),
            "get_versione_by_id": _versione_pinnata(),
        })
        with patch_scope(), patch_render(_PDF) as mock_render:
            with self.assertRaises(ServiceError) as ctx:
                svc.ristampa_fedele(make_user(), 99)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        mock_render.assert_not_called()

    # 10. Evento di audit (decisione Tid §8.3): unica scrittura del percorso,
    #     sul documento ESISTENTE, col dettaglio di fedelta'.
    def test_ristampa_evento_audit_emesso_con_dettaglio_fedelta(self) -> None:
        svc, repo, _, _ = service_with_mocks(repo_methods={
            "get_documento_generato_snapshot": _snapshot(),
            "get_versione_by_id": _versione_pinnata(),
        })
        with patch_scope(), _patch_atomic(), patch_render(_PDF):
            svc.ristampa_fedele(make_user(user_id=42), 99)
        repo.emit_evento_documento.assert_called_once()
        evento = repo.emit_evento_documento.call_args.args[0]
        self.assertEqual(evento["evento_tipo"], "RISTAMPA_FEDELE")
        self.assertEqual(evento["documento_generato_id"], 99)
        self.assertEqual(evento["user_id"], 42)
        self.assertEqual(evento["detail"]["template_versione_id"], 12)
        self.assertTrue(evento["detail"]["pdf_hash_match"])
        # Decisione 76: niente tx_id esplicito.
        self.assertNotIn("tx_id", evento)

    # 11. L'audit e' best-effort come il `SCARICATO`: se l'INSERT fallisce
    #     (es. il CHECK evento_tipo non ammette ancora RISTAMPA_FEDELE) il
    #     PDF esce comunque — negarlo sarebbe peggio del log mancante.
    def test_ristampa_evento_fallito_ritorna_comunque_il_pdf(self) -> None:
        svc, repo, _, _ = service_with_mocks(repo_methods={
            "get_documento_generato_snapshot": _snapshot(),
            "get_versione_by_id": _versione_pinnata(),
        })
        repo.emit_evento_documento.side_effect = RuntimeError("check violation")
        with patch_scope(), _patch_atomic(), patch_render(_PDF):
            result = svc.ristampa_fedele(make_user(), 99)
        self.assertEqual(result["pdf_bytes"], _PDF)

    # 12. Utente non autenticato -> validazione, niente lettura.
    def test_ristampa_anon_user_raises_validation(self) -> None:
        svc, repo, _, _ = service_with_mocks()
        with self.assertRaises(ServiceError):
            svc.ristampa_fedele(make_user(is_authenticated=False), 99)
        repo.get_documento_generato_snapshot.assert_not_called()

    # 13. Guard input: id non positivo -> errore prima di qualunque round-trip.
    def test_ristampa_input_guard_id_non_positivo(self) -> None:
        svc, repo, _, _ = service_with_mocks()
        with self.assertRaises(ServiceError):
            svc.ristampa_fedele(make_user(), 0)
        repo.get_documento_generato_snapshot.assert_not_called()

    # 14. Una versione OBSOLETA e' AMMESSA: e' il caso normale della ristampa
    #     fedele (il modello del 2025 oggi e' obsoleto — ed e' proprio quello
    #     che si vuole). Se un filtro di stato si insinuasse nel percorso,
    #     questo test diventerebbe rosso.
    def test_ristampa_versione_obsoleta_e_ammessa(self) -> None:
        versione = _versione_pinnata(stato="OBSOLETA")
        svc, _, _, _ = service_with_mocks(repo_methods={
            "get_documento_generato_snapshot": _snapshot(
                template_hash=_template_hash_di(versione),
            ),
            "get_versione_by_id": versione,
        })
        with patch_scope(), _patch_atomic(), patch_render(_PDF):
            result = svc.ristampa_fedele(make_user(), 99)
        self.assertEqual(result["versione_stato"], "OBSOLETA")
        self.assertTrue(result["template_hash_match"])

    # 15. ⚠️ PRESIDIO DICHIARATO, NON UNA PROVA (2026-10-04, decisione Tid:
    #     «per ora solo il test»). Dal render con la pagina dalle colonne
    #     (R-BE-V2a) formato, orientamento e margini decidono il PDF quanto
    #     html e css; ma `_compute_template_hash` legge solo html|css|markdown.
    #     Una versione la cui pagina cambia dopo la generazione (possibile
    #     solo in BOZZA, come il test 5) si dichiara fedele: `template_hash_
    #     match` vale True su un PDF che esce in un altro formato.
    #     `expectedFailure` finche' la formula non include la pagina: quando la
    #     includera', il test passera' e unittest lo segnalera' come «unexpected
    #     success» — si toglie allora il decoratore.
    @expectedFailure
    def test_ristampa_pagina_cambiata_dichiarata(self) -> None:
        allora = {
            **_versione_pinnata(),
            "page_format": "A4", "page_orientation": "PORTRAIT",
            "margin_top_mm": 10, "margin_right_mm": 10,
            "margin_bottom_mm": 10, "margin_left_mm": 10,
        }
        oggi = {**allora, "page_format": "A3", "page_orientation": "LANDSCAPE"}
        svc, _, _, _ = service_with_mocks(repo_methods={
            "get_documento_generato_snapshot": _snapshot(
                template_hash=_hash_del_service(allora),
            ),
            "get_versione_by_id": oggi,
        })
        with patch_scope(), _patch_atomic(), patch_render(_PDF):
            result = svc.ristampa_fedele(make_user(), 99)
        self.assertFalse(result["template_hash_match"])


# Scopo: l'hash che il SERVICE calcola su una versione (non la copia della
#        formula di `_template_hash_di`): il test 15 deve seguire la formula
#        vera, o il giorno che la si corregge resterebbe rosso per la copia.
def _hash_del_service(versione: dict[str, Any]) -> str:
    svc, _, _, _ = service_with_mocks()
    return svc._compute_template_hash(versione)
