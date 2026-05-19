# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per PartitionedNoteService e per la costruzione
#        di PartitionedNoteRepository (validazione parametri __init__).
#        Repo e ParameterService mockati: nessun accesso DB reale.
#
# Indice test (0..N):
#   0. RepoInit         - validazione target_tipo + child_table coerenti
#   1. ListNote         - 404 parent / pass-through ok / clamp page_size
#   2. GetNota          - 404 anti-tampering id<->target
#   3. CreaNota         - default anchor/posizione/seq, testo obbligatorio,
#                         id_stile fallback parametro, target_riga_id check,
#                         payload whitelist, supports_riga
#   4. AggiornaNota     - rifiuta target_riga_id, 404, patch vuoto idempotente
#   5. EliminaNota      - 404 / ok
#   6. CountPerTarget   - delega al repo
# ------------------------------------------------------------

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from apps.core.db.partitioned_note_repository import PartitionedNoteRepository
from apps.core.services.partitioned_note_service import (
    PARAM_DEFAULT_STILE,
    PartitionedNoteService,
)
from apps.core.services.service_errors import ServiceError


def _make_repo_mock(
    *,
    target_tipo: str = "PREVENTIVO",
    supports_riga: bool = True,
) -> MagicMock:
    # `spec=PartitionedNoteRepository` consente set/get sulle @property
    # del target: `supports_riga` e' settabile come attributo dell'istanza
    # senza inquinare la classe MagicMock globale (regressione test paralleli).
    repo = MagicMock(spec=PartitionedNoteRepository)
    repo.target_tipo = target_tipo
    repo.supports_riga = supports_riga
    repo.exists_parent.return_value = True
    repo.riga_belongs_to_parent.return_value = True
    repo.list.return_value = ([], 0)
    repo.get.return_value = None
    repo.create.return_value = 1
    repo.update.return_value = True
    repo.delete.return_value = True
    repo.count_for_parent.return_value = 0
    return repo


def _make_params_mock(*, default_codice: str | None = "DEFAULT") -> MagicMock:
    # Post-correzione brief 2026-05-19: il parametro NOTE_DEFAULT_STILE
    # contiene la chiave naturale (codice_interno), non l'id intero.
    # Il service fa: get_parameter -> codice -> lookup id.
    params = MagicMock()
    if default_codice is None:
        params.get_parameter.side_effect = ServiceError(
            code="E_PARAMETER_NOT_FOUND",
            message="parametro non trovato",
        )
    else:
        params.get_parameter.return_value = default_codice
    return params


# Scopo: Costruisce un service con stile_lookup_fn iniettato.
#        Default: lookup ritorna 99 per qualunque codice (sufficiente per i
#        test che esercitano il fallback parametro). Override via
#        `stile_id_by_codice` per casi specifici.
def _make_service(
    repo,
    params,
    *,
    stile_id_by_codice: dict[str, int] | None = None,
) -> PartitionedNoteService:
    lookup = stile_id_by_codice if stile_id_by_codice is not None else {"DEFAULT": 99}
    stile_lookup = MagicMock(side_effect=lambda c: lookup.get(c))
    svc = PartitionedNoteService(
        repo=repo,
        parameter_service=params,
        stile_lookup_fn=stile_lookup,
    )
    # Espone il mock sul service per inspection nei test (assert_not_called, ecc.)
    svc._test_stile_lookup = stile_lookup  # type: ignore[attr-defined]
    return svc


class RepoInitTests(unittest.TestCase):
    def test_target_tipo_invalido_solleva(self) -> None:
        with self.assertRaises(ValueError):
            PartitionedNoteRepository(
                partition_table="vendite.note_xxx",
                target_tipo="INESISTENTE",
                parent_table="vendite.preventivi",
            )

    def test_child_table_senza_fk_solleva(self) -> None:
        with self.assertRaises(ValueError):
            PartitionedNoteRepository(
                partition_table="vendite.note_preventivo",
                target_tipo="PREVENTIVO",
                parent_table="vendite.preventivi",
                child_table="vendite.preventivi_righe",
                # manca child_parent_fk
            )

    def test_init_valido(self) -> None:
        repo = PartitionedNoteRepository(
            partition_table="vendite.note_preventivo",
            target_tipo="PREVENTIVO",
            parent_table="vendite.preventivi",
            child_table="vendite.preventivi_righe",
            child_parent_fk="preventivo_id",
        )
        self.assertEqual(repo.target_tipo, "PREVENTIVO")
        self.assertTrue(repo.supports_riga)

    def test_init_senza_riga(self) -> None:
        repo = PartitionedNoteRepository(
            partition_table="vendite.note_preventivo",
            target_tipo="PREVENTIVO",
            parent_table="vendite.preventivi",
        )
        self.assertFalse(repo.supports_riga)


class ListNoteTests(unittest.TestCase):
    def test_parent_inesistente_404(self) -> None:
        repo = _make_repo_mock()
        repo.exists_parent.return_value = False
        svc = _make_service(repo, _make_params_mock())
        with self.assertRaises(ServiceError) as ctx:
            svc.list_note(target_id=1)
        self.assertEqual(ctx.exception.code, "E_NOTA_PARENT_NOT_FOUND")

    def test_pass_through_filtri(self) -> None:
        repo = _make_repo_mock()
        repo.list.return_value = ([{"id": 7}], 1)
        svc = _make_service(repo, _make_params_mock())
        rows, total = svc.list_note(
            target_id=42, target_riga_id=5, include_invisible=False,
            page=2, page_size=10,
        )
        self.assertEqual(total, 1)
        self.assertEqual(rows, [{"id": 7}])
        repo.list.assert_called_once_with(
            42, target_riga_id=5, include_invisible=False, page=2, page_size=10,
        )

    def test_page_size_clamp(self) -> None:
        repo = _make_repo_mock()
        svc = _make_service(repo, _make_params_mock())
        svc.list_note(target_id=1, page=0, page_size=1000)
        _args, kwargs = repo.list.call_args
        self.assertEqual(kwargs["page"], 1)         # clamp min
        self.assertEqual(kwargs["page_size"], 200)  # clamp max


class GetNotaTests(unittest.TestCase):
    def test_404_su_inesistente(self) -> None:
        repo = _make_repo_mock()
        repo.get.return_value = None
        svc = _make_service(repo, _make_params_mock())
        with self.assertRaises(ServiceError) as ctx:
            svc.get_nota(note_id=10, target_id=1)
        self.assertEqual(ctx.exception.code, "E_NOTA_NOT_FOUND")

    def test_ritorna_nota(self) -> None:
        repo = _make_repo_mock()
        repo.get.return_value = {"id": 10, "testo_md": "ciao"}
        svc = _make_service(repo, _make_params_mock())
        result = svc.get_nota(note_id=10, target_id=1)
        self.assertEqual(result["id"], 10)


class CreaNotaTests(unittest.TestCase):
    def test_testo_obbligatorio(self) -> None:
        repo = _make_repo_mock()
        svc = _make_service(repo, _make_params_mock())
        with self.assertRaises(ServiceError) as ctx:
            svc.crea_nota(target_id=1, payload={})
        self.assertEqual(ctx.exception.code, "E_NOTA_VALIDATION")

    def test_payload_chiavi_non_riconosciute(self) -> None:
        repo = _make_repo_mock()
        svc = _make_service(repo, _make_params_mock())
        with self.assertRaises(ServiceError) as ctx:
            svc.crea_nota(target_id=1, payload={"testo_md": "x", "campo_ignoto": 1})
        self.assertEqual(ctx.exception.code, "E_NOTA_VALIDATION")

    def test_default_anchor_documento(self) -> None:
        repo = _make_repo_mock()
        # Restituisce un dict dopo create (get) per il return finale.
        repo.get.return_value = {"id": 1, "anchor_tipo": "DOCUMENTO"}
        svc = _make_service(repo, _make_params_mock())
        svc.crea_nota(target_id=1, payload={"testo_md": "ciao"})
        normalized = repo.create.call_args[0][1]
        self.assertEqual(normalized["anchor_tipo"], "DOCUMENTO")
        self.assertEqual(normalized["posizione"], "HEADER")
        self.assertEqual(normalized["seq"], 10)
        self.assertTrue(normalized["visibile"])
        self.assertFalse(normalized["solo_stampa"])
        self.assertEqual(normalized["id_stile"], 99)  # fallback parametro

    def test_default_anchor_riga(self) -> None:
        repo = _make_repo_mock()
        repo.get.return_value = {"id": 1, "anchor_tipo": "RIGA"}
        svc = _make_service(repo, _make_params_mock())
        svc.crea_nota(
            target_id=1, payload={"testo_md": "ciao", "target_riga_id": 7},
        )
        normalized = repo.create.call_args[0][1]
        self.assertEqual(normalized["anchor_tipo"], "RIGA")
        self.assertEqual(normalized["posizione"], "AFTER")
        self.assertEqual(normalized["target_riga_id"], 7)

    def test_anchor_riga_senza_target_riga_id_errore(self) -> None:
        repo = _make_repo_mock()
        svc = _make_service(repo, _make_params_mock())
        with self.assertRaises(ServiceError) as ctx:
            svc.crea_nota(
                target_id=1,
                payload={"testo_md": "x", "anchor_tipo": "RIGA"},
            )
        self.assertEqual(ctx.exception.code, "E_NOTA_VALIDATION")

    def test_riga_non_appartiene_a_parent(self) -> None:
        repo = _make_repo_mock()
        repo.riga_belongs_to_parent.return_value = False
        svc = _make_service(repo, _make_params_mock())
        with self.assertRaises(ServiceError) as ctx:
            svc.crea_nota(
                target_id=1, payload={"testo_md": "x", "target_riga_id": 7},
            )
        self.assertEqual(ctx.exception.code, "E_NOTA_RIGA_INCOERENTE")

    def test_repo_non_supporta_riga(self) -> None:
        repo = _make_repo_mock(supports_riga=False)
        svc = _make_service(repo, _make_params_mock())
        with self.assertRaises(ServiceError) as ctx:
            svc.crea_nota(
                target_id=1, payload={"testo_md": "x", "target_riga_id": 7},
            )
        self.assertEqual(ctx.exception.code, "E_NOTA_VALIDATION")

    def test_id_stile_esplicito_no_lookup_parametro(self) -> None:
        repo = _make_repo_mock()
        repo.get.return_value = {"id": 1}
        params = _make_params_mock()
        svc = _make_service(repo, params)
        svc.crea_nota(target_id=1, payload={"testo_md": "x", "id_stile": 5})
        normalized = repo.create.call_args[0][1]
        self.assertEqual(normalized["id_stile"], 5)
        params.get_parameter.assert_not_called()
        svc._test_stile_lookup.assert_not_called()  # type: ignore[attr-defined]

    def test_id_stile_fallback_parametro_assente(self) -> None:
        # Parametro NOTE_DEFAULT_STILE non configurato: errore parlante,
        # NON 500 sul NOT NULL della colonna id_stile.
        repo = _make_repo_mock()
        svc = _make_service(repo, _make_params_mock(default_codice=None))
        with self.assertRaises(ServiceError) as ctx:
            svc.crea_nota(target_id=1, payload={"testo_md": "x"})
        self.assertEqual(ctx.exception.code, "E_NOTA_VALIDATION")
        self.assertIn(PARAM_DEFAULT_STILE, str(ctx.exception.hint or ""))

    def test_id_stile_fallback_codice_non_risolvibile(self) -> None:
        # Parametro presente ma punta a un codice_interno inesistente o
        # disattivato: errore parlante con il codice incriminato nel hint.
        repo = _make_repo_mock()
        svc = _make_service(
            repo, _make_params_mock(default_codice="DEFAULT"),
            stile_id_by_codice={},  # nessun match
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.crea_nota(target_id=1, payload={"testo_md": "x"})
        self.assertEqual(ctx.exception.code, "E_NOTA_VALIDATION")
        self.assertIn("DEFAULT", str(ctx.exception.hint or ""))

    def test_id_stile_fallback_codice_naturale_risolto(self) -> None:
        # Flusso end-to-end del fallback: parametro -> codice -> lookup id.
        repo = _make_repo_mock()
        repo.get.return_value = {"id": 1}
        svc = _make_service(
            repo, _make_params_mock(default_codice="DEFAULT"),
            stile_id_by_codice={"DEFAULT": 77},
        )
        svc.crea_nota(target_id=1, payload={"testo_md": "x"})
        normalized = repo.create.call_args[0][1]
        self.assertEqual(normalized["id_stile"], 77)

    def test_parent_inesistente_404(self) -> None:
        repo = _make_repo_mock()
        repo.exists_parent.return_value = False
        svc = _make_service(repo, _make_params_mock())
        with self.assertRaises(ServiceError) as ctx:
            svc.crea_nota(target_id=999, payload={"testo_md": "x"})
        self.assertEqual(ctx.exception.code, "E_NOTA_PARENT_NOT_FOUND")


class AggiornaNotaTests(unittest.TestCase):
    def test_rifiuta_target_riga_id(self) -> None:
        repo = _make_repo_mock()
        repo.get.return_value = {"id": 10, "target_id": 1}
        svc = _make_service(repo, _make_params_mock())
        with self.assertRaises(ServiceError) as ctx:
            svc.aggiorna_nota(
                note_id=10, target_id=1, patch={"target_riga_id": 5},
            )
        self.assertEqual(ctx.exception.code, "E_NOTA_VALIDATION")

    def test_404_nota_inesistente(self) -> None:
        repo = _make_repo_mock()
        repo.get.return_value = None
        svc = _make_service(repo, _make_params_mock())
        with self.assertRaises(ServiceError) as ctx:
            svc.aggiorna_nota(note_id=10, target_id=1, patch={"testo_md": "x"})
        self.assertEqual(ctx.exception.code, "E_NOTA_NOT_FOUND")

    def test_patch_vuoto_idempotente(self) -> None:
        repo = _make_repo_mock()
        existing = {"id": 10, "target_id": 1, "testo_md": "originale"}
        repo.get.return_value = existing
        svc = _make_service(repo, _make_params_mock())
        result = svc.aggiorna_nota(note_id=10, target_id=1, patch={})
        self.assertEqual(result, existing)
        repo.update.assert_not_called()

    def test_patch_normale(self) -> None:
        repo = _make_repo_mock()
        # Prima call: verifica esistenza; seconda: dettaglio dopo update.
        repo.get.side_effect = [
            {"id": 10, "testo_md": "originale"},
            {"id": 10, "testo_md": "nuovo"},
        ]
        svc = _make_service(repo, _make_params_mock())
        result = svc.aggiorna_nota(
            note_id=10, target_id=1, patch={"testo_md": "nuovo"},
        )
        self.assertEqual(result["testo_md"], "nuovo")
        repo.update.assert_called_once()


class EliminaNotaTests(unittest.TestCase):
    def test_ok(self) -> None:
        repo = _make_repo_mock()
        svc = _make_service(repo, _make_params_mock())
        svc.elimina_nota(note_id=10, target_id=1)
        repo.delete.assert_called_once_with(10, 1)

    def test_404(self) -> None:
        repo = _make_repo_mock()
        repo.delete.return_value = False
        svc = _make_service(repo, _make_params_mock())
        with self.assertRaises(ServiceError) as ctx:
            svc.elimina_nota(note_id=10, target_id=1)
        self.assertEqual(ctx.exception.code, "E_NOTA_NOT_FOUND")


class CountPerTargetTests(unittest.TestCase):
    def test_delega_al_repo(self) -> None:
        repo = _make_repo_mock()
        repo.count_for_parent.return_value = 7
        svc = _make_service(repo, _make_params_mock())
        self.assertEqual(svc.count_per_target(target_id=1), 7)
