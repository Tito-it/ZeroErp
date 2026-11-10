# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le mappe dei vincoli del service catalogo (`_ARTICOLO_CHECK`,
#        `_COMPONENTE_UNIQUE`, `_UOM_OPERATIVA_UNIQUE`, `_UOM_OPERATIVA_CHECK`,
#        `_CONVERSIONE_EXCLUDE`) provate contro il database vero: ogni nome di
#        vincolo che il service traduce esiste e scatta davvero, con la frase
#        del dominio e non col ripiego generico. Dal giro 2 di
#        brief-db-revisione-catalogo (2026-11-09) anche le unita': la
#        mappatura versionata, la riga base fissa, la coppia di conversione.
#
# 🔴 PERCHE' SUL DB VERO. La mappa riconosce il vincolo dal NOME: se il DB lo
#    rinomina, il service cade sul ripiego («Violazione vincoli …») senza
#    nessun rosso, e i test con l'IntegrityError finto restano verdi. Il caso
#    composito + solo componente ha anche una copia nel form
#    (`ArticoloDrawer.vue`, `ESCLUSI`): questo test e' il presidio che il CHECK
#    che quella copia ripete c'e' ancora, col nome che il service conosce.
#
# ⭐ I CASI SI COSTRUISCONO (`dbops.fn_pgtap_crea_articolo`), in una
#    transazione annullata: niente dipende dai dati presenti.
#
# Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`):
#   1) composito e solo componente insieme -> la frase del CHECK
#      `chk_articoli_composito_non_solo_componente`, senza campo
#   2) un legame che si sovrappone a uno in vigore -> la frase di
#      `uq_articoli_componenti_no_overlap`, senza campo
#   3) la UoM base aggiunta di nuovo come operativa -> la frase di
#      `uq_articoli_uom_operativa_no_overlap`, senza campo
#   4) la mappatura si versiona: chiudi e inserisci passa, un periodo che si
#      sovrappone no (stessa frase del 3)
#   5) la riga base con un fattore diverso da 1 -> la frase di
#      `chk_articoli_uom_operativa_base_fissa`
#   6) la riga base non si toglie -> `E_UOM_RIGA_BASE_IMMUTABILE` dal DB,
#      intatto fino al middleware
#   7) la conversione nel verso opposto, nello stesso periodo -> la frase di
#      `ex_unita_misura_conversioni_coppia_no_overlap`
#   8) la conversione fra tipologie diverse -> `E_UOM_CONVERSIONE_TIPO_DIVERSO`
#      dal DB, intatto
# ------------------------------------------------------------

from __future__ import annotations

import unittest
from typing import Any
from uuid import uuid4

from django.db import DatabaseError, connection, transaction

from apps.catalogo.services import catalogo_service
from apps.core.services.db_error_fields import db_error_code
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto


class VincoliCatalogoDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto("dbops.fn_pgtap_crea_articolo(varchar, boolean, boolean, boolean,"
                              " bigint, smallint, boolean, boolean, bigint, bigint)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.sfx = uuid4().hex[:8].upper()

    def _articolo(self, sigla: str, *, composito: bool = False) -> str:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT dbops.fn_pgtap_crea_articolo(%s, p_is_composito => %s)::text",
                [f"VINC-{sigla}-{self.sfx}", composito],
            )
            return cur.fetchone()[0]

    def _uom_base(self, articolo: str) -> int:
        with connection.cursor() as cur:
            cur.execute("SELECT uom_id FROM catalogo.articoli WHERE id = %s", [articolo])
            return cur.fetchone()[0]

    # Un'unita' nuova della tipologia indicata (per codice interno), dalla porta
    # dell'applicazione: niente dipende dalle unita' presenti.
    def _unita(self, sigla: str, tipologia: str = "MASSA") -> int:
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM catalogo.uom_tipi WHERE codice_interno = %s", [tipologia])
            tipo = cur.fetchone()
        assert tipo is not None, f"tipologia {tipologia} assente dal seed"
        riga = catalogo_service.fn_create_unita_misura(
            {"codice": f"{sigla}{self.sfx[:6]}", "descrizione": f"Prova {sigla}", "tipo_uom_id": tipo[0]},
        )
        return int(riga["id"])

    def _riga_base(self, articolo: str) -> int:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id FROM catalogo.articoli_uom_operativa WHERE articolo_id = %s AND is_base",
                [articolo],
            )
            riga = cur.fetchone()
        assert riga is not None, "il trigger seed della UoM base non ha seminato"
        return int(riga[0])

    # Il rifiuto del DB col suo codice, che il service lascia passare intatto.
    def _rifiuto_db(self, chiamata: Any) -> str | None:
        with self.assertRaises(DatabaseError) as cm, transaction.atomic():
            chiamata()
        return db_error_code(cm.exception)

    # Il rifiuto in un savepoint: la transazione del test resta usabile.
    def _rifiuto(self, chiamata: Any) -> ServiceError:
        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            chiamata()
        return cm.exception

    # 1. Composito e solo componente insieme.
    def test_composito_e_solo_componente(self) -> None:
        semplice = self._articolo("S")
        err = self._rifiuto(lambda: catalogo_service.fn_update_articolo(
            semplice, {"is_composito": True, "is_solo_componente": True},
        ))
        self.assertEqual(err.code, "E_CATALOGO_VALIDATION")
        self.assertIn("solo componente", err.message)
        self.assertNotIn("field", err.context)

    # 2. Un secondo legame dello stesso componente in un periodo che si
    #    sovrappone al primo.
    def test_legame_sovrapposto(self) -> None:
        kit = self._articolo("K", composito=True)
        figlio = self._articolo("F")
        catalogo_service.fn_create_componente(
            kit, {"componente_id": figlio, "coeff_qta": "1", "valido_dal": "2020-01-01"},
        )
        err = self._rifiuto(lambda: catalogo_service.fn_create_componente(
            kit, {"componente_id": figlio, "coeff_qta": "2", "valido_dal": "2021-01-01"},
        ))
        self.assertEqual(err.code, "E_CATALOGO_VALIDATION")
        self.assertIn("periodo che si sovrappone", err.message)
        self.assertNotIn("field", err.context)

    # 3. La UoM base ha gia' la sua operativa (seed del trigger), senza fine:
    #    aggiungerla di nuovo e' un periodo che si sovrappone.
    def test_uom_operativa_doppia(self) -> None:
        articolo = self._articolo("U")
        uom_base = self._uom_base(articolo)
        err = self._rifiuto(lambda: catalogo_service.fn_create_uom_operativa(
            articolo, {"uom_id": uom_base, "factor_to_base": "1"},
        ))
        self.assertEqual(err.code, "E_CATALOGO_VALIDATION")
        self.assertIn("periodo che si sovrappone", err.message)
        self.assertNotIn("field", err.context)

    # 4. Chiudi e inserisci: la stessa unita' su due periodi consecutivi passa,
    #    un terzo che si sovrappone no. Proiezione della vista letta dal vero
    #    (la rilettura dopo la create passa da `get_uom_operativa`).
    def test_uom_operativa_versionata(self) -> None:
        articolo = self._articolo("V")
        cartone = self._unita("CT")
        prima = catalogo_service.fn_create_uom_operativa(articolo, {
            "uom_id": cartone, "factor_to_base": "10",
            "valido_dal": "2020-01-01", "valido_al": "2020-12-31",
        })
        seconda = catalogo_service.fn_create_uom_operativa(articolo, {
            "uom_id": cartone, "factor_to_base": "12", "valido_dal": "2021-01-01",
        })
        self.assertNotEqual(prima["id"], seconda["id"])
        self.assertNotIn("rounding_mode", seconda)
        err = self._rifiuto(lambda: catalogo_service.fn_create_uom_operativa(articolo, {
            "uom_id": cartone, "factor_to_base": "11", "valido_dal": "2020-06-01",
        }))
        self.assertIn("periodo che si sovrappone", err.message)

    # 5. La riga base ha fattore 1: un altro lo rifiuta il CHECK.
    def test_riga_base_fissa(self) -> None:
        articolo = self._articolo("B")
        base = self._riga_base(articolo)
        err = self._rifiuto(lambda: catalogo_service.fn_update_uom_operativa(
            articolo, base, {"factor_to_base": "2"},
        ))
        self.assertEqual(err.code, "E_CATALOGO_VALIDATION")
        self.assertIn("unita' base", err.message)

    # 6. La riga base non si toglie: lo dice il guard, col suo codice.
    def test_riga_base_non_si_toglie(self) -> None:
        articolo = self._articolo("D")
        base = self._riga_base(articolo)
        codice = self._rifiuto_db(lambda: catalogo_service.fn_delete_uom_operativa(articolo, base))
        self.assertEqual(codice, "E_UOM_RIGA_BASE_IMMUTABILE")

    # 7. Una conversione per coppia non orientata e periodo: il verso opposto
    #    nello stesso periodo e' la stessa conversione.
    def test_conversione_verso_opposto_sovrapposta(self) -> None:
        da, a = self._unita("KA"), self._unita("KB")
        catalogo_service.fn_create_conversione(
            {"uom_from_id": da, "uom_to_id": a, "fattore": "1000", "valido_dal": "2020-01-01"},
        )
        err = self._rifiuto(lambda: catalogo_service.fn_create_conversione(
            {"uom_from_id": a, "uom_to_id": da, "fattore": "0.001", "valido_dal": "2021-01-01"},
        ))
        self.assertEqual(err.code, "E_CATALOGO_VALIDATION")
        self.assertIn("in uno dei due versi", err.message)

    # 8. Tipologie diverse: il guard parla col suo codice, e arriva intatto.
    def test_conversione_tipologie_diverse(self) -> None:
        massa = self._unita("TM")
        with connection.cursor() as cur:
            cur.execute(
                "SELECT codice_interno FROM catalogo.uom_tipi WHERE codice_interno <> 'MASSA' "
                "AND codice_interno IS NOT NULL ORDER BY codice_interno LIMIT 1",
            )
            altra = cur.fetchone()
        assert altra is not None, "serve una seconda tipologia nel seed"
        altro = self._unita("TX", altra[0])
        codice = self._rifiuto_db(lambda: catalogo_service.fn_create_conversione(
            {"uom_from_id": massa, "uom_to_id": altro, "fattore": "2"},
        ))
        self.assertEqual(codice, "E_UOM_CONVERSIONE_TIPO_DIVERSO")
