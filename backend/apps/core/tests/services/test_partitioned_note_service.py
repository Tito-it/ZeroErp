# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per PartitionedNoteService e per la costruzione
#        di PartitionedNoteRepository (validazione parametri __init__).
#        Repo e ParameterService mockati: nessun accesso DB reale.
#
# Indice test (0..N):
#   0. RepoInit         - target_tipo senza whitelist + child_table coerenti
#   1. ListNote         - 404 parent / pass-through ok / clamp page_size
#   2. GetNota          - 404 anti-tampering id<->target
#   3. CreaNota         - default anchor/posizione/seq, testo obbligatorio,
#                         id_stile fallback parametro, target_riga_id check,
#                         payload whitelist, supports_riga
#   4. AggiornaNota     - rifiuta target_riga_id, 404, patch vuoto idempotente
#   5. EliminaNota      - 404 / ok
#   6. CountPerTarget   - delega al repo
#   7. ContatoriDocumento - la forma `{"note": n}` del dettaglio, zero compreso
#   8. SedeSenzaRighe   - (catalogo, 2026-11-11) chiave UUID normalizzata, chiave
#                         non UUID 400, ancora RIGA rifiutata in create e update
# ------------------------------------------------------------

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from apps.core.db.partitioned_note_repository import PartitionedNoteRepository
from apps.core.services.partitioned_note_service import (
    PARAM_DEFAULT_STILE,
    PartitionedNoteService,
    contatori_documento,
)
from apps.core.services.service_errors import ServiceError


def _make_repo_mock(
    *,
    target_tipo: str = "PREVENTIVO",
    supports_riga: bool = True,
    target_id_uuid: bool = False,
) -> MagicMock:
    # `spec=PartitionedNoteRepository` consente set/get sulle @property
    # del target: `supports_riga` e' settabile come attributo dell'istanza
    # senza inquinare la classe MagicMock globale (regressione test paralleli).
    repo = MagicMock(spec=PartitionedNoteRepository)
    repo.target_tipo = target_tipo
    repo.supports_riga = supports_riga
    # ⚠️ Esplicito: su un MagicMock la property sarebbe un mock VERO, e il
    #    service tratterebbe la chiave intera come un UUID.
    repo.target_id_uuid = target_id_uuid
    repo.exists_parent.return_value = True
    repo.riga_belongs_to_parent.return_value = True
    repo.list.return_value = ([], 0)
    repo.get.return_value = None
    repo.create.return_value = 1
    repo.update.return_value = True
    repo.delete.return_value = True
    repo.count_for_parent.return_value = 0
    return repo


def _make_params_mock(
    *,
    default_codice: str | None = "DEFAULT",
    default_lingua_codice: str | None = "it",
) -> MagicMock:
    # Post-correzione brief 2026-05-19/20: i parametri NOTE_DEFAULT_STILE e
    # NOTE_DEFAULT_LINGUA contengono chiavi naturali (codice_interno per
    # stile, codice_iso per lingua), non id interi. Il service fa:
    # get_parameter -> codice -> lookup id.
    params = MagicMock()

    def side_effect(code, **_kwargs):
        if code == "NOTE_DEFAULT_STILE":
            if default_codice is None:
                raise ServiceError(
                    code="E_PARAMETER_NOT_FOUND",
                    message="parametro non trovato",
                )
            return default_codice
        if code == "NOTE_DEFAULT_LINGUA":
            if default_lingua_codice is None:
                raise ServiceError(
                    code="E_PARAMETER_NOT_FOUND",
                    message="parametro non trovato",
                )
            return default_lingua_codice
        return None

    params.get_parameter.side_effect = side_effect
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
    lingua_id_by_codice_iso: dict[str, int] | None = None,
) -> PartitionedNoteService:
    lookup = stile_id_by_codice if stile_id_by_codice is not None else {"DEFAULT": 99}
    stile_lookup = MagicMock(side_effect=lambda c: lookup.get(c))
    lingua_lookup_map = (
        lingua_id_by_codice_iso if lingua_id_by_codice_iso is not None else {"it": 88}
    )
    lingua_lookup = MagicMock(side_effect=lambda c: lingua_lookup_map.get(c))
    svc = PartitionedNoteService(
        repo=repo,
        parameter_service=params,
        stile_lookup_fn=stile_lookup,
        lingua_lookup_fn=lingua_lookup,
    )
    # Espone i mock sul service per inspection nei test (assert_not_called, ecc.)
    svc._test_stile_lookup = stile_lookup  # type: ignore[attr-defined]
    svc._test_lingua_lookup = lingua_lookup  # type: ignore[attr-defined]
    return svc


class RepoInitTests(unittest.TestCase):
    # ⛔ Il `target_tipo` non ha una whitelist nel backend dal 2026-10-25: e' un
    #    codice di `config.tipi_entita` e il confine di una partizione, e decide
    #    il DB (presidio: `core/tests/db/test_note_confini_partizione_db.py`).
    #    Un codice con `_` si costruisce come gli altri.
    def test_target_tipo_senza_whitelist(self) -> None:
        repo = PartitionedNoteRepository(
            partition_table="vendite.note_ddt",
            target_tipo="DDT_VENDITA",
            parent_table="vendite.ddt",
        )
        self.assertEqual(repo.target_tipo, "DDT_VENDITA")
        self.assertEqual(repo.partition_table, "vendite.note_ddt")

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
            limit=10, offset=10,
        )
        self.assertEqual(total, 1)
        self.assertEqual(rows, [{"id": 7}])
        repo.list.assert_called_once_with(
            42, target_riga_id=5, include_invisible=False,
            search=None, order_by=None, order_dir=None, limit=10, offset=10,
        )

    def test_page_size_clamp(self) -> None:
        repo = _make_repo_mock()
        svc = _make_service(repo, _make_params_mock())
        svc.list_note(target_id=1, limit=1000, offset=-5)
        _args, kwargs = repo.list.call_args
        self.assertEqual(kwargs["offset"], 0)     # clamp min
        self.assertEqual(kwargs["limit"], 200)    # clamp max


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

    # D-seq (Tid, 2026-11-11): il range di `seq` e' quello del DB,
    # `integer` con `CHECK (seq >= 0)`. Lo 0 passa, oltre lo smallint passa,
    # il negativo e oltre l'integer sono un 400 col campo.
    def test_seq_range_del_db(self) -> None:
        repo = _make_repo_mock()
        repo.get.return_value = {"id": 1, "anchor_tipo": "DOCUMENTO"}
        svc = _make_service(repo, _make_params_mock())
        for valore in (0, 40000, 2_147_483_647):
            svc.crea_nota(target_id=1, payload={"testo_md": "ciao", "seq": valore})
            self.assertEqual(repo.create.call_args[0][1]["seq"], valore)
        for valore in (-1, 2_147_483_648):
            with self.assertRaises(ServiceError) as cm:
                svc.crea_nota(target_id=1, payload={"testo_md": "ciao", "seq": valore})
            self.assertEqual(cm.exception.code, "E_NOTA_VALIDATION")
            self.assertEqual(cm.exception.context.get("field"), "seq")

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
        # Quando id_stile e' esplicito nel payload, il parameter NOTE_DEFAULT_STILE
        # non viene consultato (verifica per-codice — il parameter NOTE_DEFAULT_LINGUA
        # puo' invece essere chiamato perche' la lingua non e' nel payload).
        repo = _make_repo_mock()
        repo.get.return_value = {"id": 1}
        params = _make_params_mock()
        svc = _make_service(repo, params)
        svc.crea_nota(target_id=1, payload={"testo_md": "x", "id_stile": 5})
        normalized = repo.create.call_args[0][1]
        self.assertEqual(normalized["id_stile"], 5)
        codici_chiamati = [c.args[0] for c in params.get_parameter.call_args_list]
        self.assertNotIn("NOTE_DEFAULT_STILE", codici_chiamati)
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

    # --- id_lingua fallback (refactor 2026-05-20) ------------------------

    def test_id_lingua_fallback_codice_iso_risolto(self) -> None:
        # Parameter NOTE_DEFAULT_LINGUA='it' + lookup attivo -> id_lingua
        # auto-popolato in create senza che l'utente lo specifichi.
        repo = _make_repo_mock()
        repo.get.return_value = {"id": 1}
        svc = _make_service(
            repo, _make_params_mock(default_lingua_codice="it"),
            lingua_id_by_codice_iso={"it": 88},
        )
        svc.crea_nota(target_id=1, payload={"testo_md": "x"})
        normalized = repo.create.call_args[0][1]
        self.assertEqual(normalized["id_lingua"], 88)

    def test_id_lingua_fallback_parametro_assente_resta_null(self) -> None:
        # id_lingua e' NULLABLE in DB: se NOTE_DEFAULT_LINGUA non configurato,
        # la nota viene creata SENZA id_lingua nel payload normalizzato
        # (default_value NULL passato al DB). NO raise (differenza con stile).
        repo = _make_repo_mock()
        repo.get.return_value = {"id": 1}
        svc = _make_service(
            repo, _make_params_mock(default_lingua_codice=None),
        )
        svc.crea_nota(target_id=1, payload={"testo_md": "x"})
        normalized = repo.create.call_args[0][1]
        self.assertNotIn("id_lingua", normalized)

    def test_id_lingua_fallback_codice_iso_non_risolvibile(self) -> None:
        # Parametro presente ma codice_iso non in config.lingue (o disattivato):
        # errore parlante con il codice incriminato nel hint.
        repo = _make_repo_mock()
        svc = _make_service(
            repo, _make_params_mock(default_lingua_codice="xx"),
            lingua_id_by_codice_iso={},  # nessun match
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.crea_nota(target_id=1, payload={"testo_md": "x"})
        self.assertEqual(ctx.exception.code, "E_NOTA_VALIDATION")
        self.assertIn("xx", str(ctx.exception.hint or ""))

    def test_id_lingua_esplicito_no_lookup_parametro(self) -> None:
        # Se l'utente passa id_lingua esplicito, il parameter NOTE_DEFAULT_LINGUA
        # non viene consultato.
        repo = _make_repo_mock()
        repo.get.return_value = {"id": 1}
        params = _make_params_mock()
        svc = _make_service(repo, params)
        svc.crea_nota(
            target_id=1,
            payload={"testo_md": "x", "id_stile": 5, "id_lingua": 7},
        )
        normalized = repo.create.call_args[0][1]
        self.assertEqual(normalized["id_lingua"], 7)
        codici_chiamati = [c.args[0] for c in params.get_parameter.call_args_list]
        self.assertNotIn("NOTE_DEFAULT_LINGUA", codici_chiamati)
        svc._test_lingua_lookup.assert_not_called()  # type: ignore[attr-defined]

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

    # ⛔ Un PATCH senza campi e' un 400, non la nota restituita com'e' (Tid,
    #    2026-10-20, brief-be-verifica-documentazione-api §A2).
    def test_patch_vuoto_e_rifiutato(self) -> None:
        repo = _make_repo_mock()
        repo.get.return_value = {"id": 10, "target_id": 1, "testo_md": "originale"}
        svc = _make_service(repo, _make_params_mock())
        with self.assertRaises(ServiceError) as ctx:
            svc.aggiorna_nota(note_id=10, target_id=1, patch={})
        self.assertEqual(ctx.exception.code, "E_NOTA_VALIDATION")
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


class SedeSenzaRigheTests(unittest.TestCase):
    """Una sede come `catalogo.note`: padre con chiave UUID, nessuna riga."""

    _UUID = "019bbee2-5f6a-704f-bbd0-34ed84db252d"

    def _svc(self) -> tuple[MagicMock, PartitionedNoteService]:
        repo = _make_repo_mock(target_tipo="ARTICOLO", supports_riga=False, target_id_uuid=True)
        repo.get.return_value = {"id": 1}
        return repo, _make_service(repo, _make_params_mock())

    def test_chiave_uuid_arriva_al_repo_come_stringa(self) -> None:
        from uuid import UUID

        repo, svc = self._svc()
        svc.crea_nota(target_id=UUID(self._UUID), payload={"testo": "x"})
        self.assertEqual(repo.create.call_args.args[0], self._UUID)
        self.assertEqual(repo.create.call_args.args[1]["anchor_tipo"], "DOCUMENTO")

    def test_chiave_non_uuid_e_un_400(self) -> None:
        repo, svc = self._svc()
        with self.assertRaises(ServiceError) as ctx:
            svc.list_note(target_id=1)
        self.assertEqual(ctx.exception.code, "E_NOTA_VALIDATION")
        repo.list.assert_not_called()

    def test_ancora_riga_rifiutata_in_creazione_e_in_modifica(self) -> None:
        repo, svc = self._svc()
        for nome, chiama in (
            ("crea", lambda: svc.crea_nota(target_id=self._UUID, payload={"testo": "x", "anchor_tipo": "RIGA"})),
            ("aggiorna", lambda: svc.aggiorna_nota(note_id=1, target_id=self._UUID, patch={"anchor_tipo": "riga"})),
        ):
            with self.subTest(nome), self.assertRaises(ServiceError) as ctx:
                chiama()
            self.assertEqual(ctx.exception.code, "E_NOTA_VALIDATION")
            self.assertEqual(ctx.exception.context.get("field"), "anchor_tipo")
        repo.create.assert_not_called()
        repo.update.assert_not_called()

    # ⛔ Il filtro di riga in lettura: senza il cancello l'intero arrivava al
    #    DB contro `target_riga_id uuid` (`uuid = integer`, un 500).
    def test_filtro_di_riga_rifiutato_in_lettura(self) -> None:
        repo, svc = self._svc()
        with self.assertRaises(ServiceError) as ctx:
            svc.list_note(target_id=self._UUID, target_riga_id=5)
        self.assertEqual(ctx.exception.code, "E_NOTA_VALIDATION")
        self.assertEqual(ctx.exception.context.get("field"), "target_riga_id")
        repo.list.assert_not_called()


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


# ⭐ La chiave `note` e' il contratto col pulsante standard «Gestisci note» del
#    frontend (`useContatoreNote` legge `contatori.note`): un rename qui spegne
#    il badge di ogni documento senza errori.
class ContatoriDocumentoTests(unittest.TestCase):
    def test_forma_del_dettaglio(self) -> None:
        repo = _make_repo_mock()
        repo.count_for_parent.return_value = 3
        self.assertEqual(contatori_documento(repo, 42), {"note": 3})
        repo.count_for_parent.assert_called_once_with(42)

    # Lo zero e' un numero, non un'assenza: decide il frontend di non
    # mostrarlo, il backend lo dice comunque.
    def test_zero_e_un_numero(self) -> None:
        repo = _make_repo_mock()
        repo.count_for_parent.return_value = 0
        self.assertEqual(contatori_documento(repo, 42), {"note": 0})
