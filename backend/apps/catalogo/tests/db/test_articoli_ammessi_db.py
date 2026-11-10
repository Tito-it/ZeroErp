# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL PICKER DELLE RIGHE DI DOCUMENTO e la correzione di struttura
#        dell'articolo, provati contro il database vero: il binding con
#        `catalogo.fn_articoli_ammessi` e `catalogo.fn_articolo_correggi_struttura`
#        (brief-db-articoli-ammessi-per-documento §9.6, Lotti 3u e 4).
#
# 🔴 PERCHE' NON BASTANO I TEST UNITARI. Tutto cio' che puo' andare storto qui
#    sta sotto il service, dove i test di `tests/services/` mettono un mock:
#    l'ordine dei parametri della funzione, i due cast (`tipo_eccezione_contratto`,
#    `uuid`), e soprattutto `motivo`, che fuori dall'ORM psycopg 3 consegna come
#    STRINGA. Un `motivo` stringa non fallisce niente: il FE legge
#    `motivo.reason` su una stringa, trova `undefined`, e ogni articolo sembra
#    ammesso. Il caso si e' visto davvero mentre il repository nasceva.
#
# ⭐ NIENTE VERDE PER SOTTRAZIONE. I casi che servono si costruiscono (un
#    articolo cercato come componente di se' stesso: il motivo 1 della distinta,
#    `COMPONENTE_PADRE`, vale su qualunque articolo) o non dipendono dai dati;
#    dove serve almeno un articolo attivo e non c'e', il test si dichiara
#    saltato col motivo.
#
# Indice test:
#   1) un articolo escluso porta `motivo` come OGGETTO, con reason e reason_key
#   2) l'ammesso porta `motivo` None, e gli ammessi vengono prima (costruito:
#      l'escluso ha il codice alfabeticamente primo)
#   3) `tipo_eccezione_valido`: l'enum letto dal DB, dentro e fuori
#   4) la sede unica col tipo d'eccezione: il cast regge (contratto inesistente,
#      nessun 500)
#   5) documento sconosciuto: lo rifiuta la funzione, col suo codice
#   6) la correzione di struttura senza SUPER_ADMIN: la rifiuta il verbo
#   7) la correzione di struttura con `campi` assente, vuoto o non oggetto: la
#      rifiuta il verbo (il service non ripete la regola)
#   8) R-BE-1: correzione e PATCH in UNA transazione — un UPDATE rifiutato
#      annulla anche la correzione; riuscito, le scrive tutte e due
#   9) `struttura_correggibile` del dettaglio e' la sede del DB
# ------------------------------------------------------------

from __future__ import annotations

import unittest
import uuid

from django.db import DatabaseError, connection, transaction

from apps.catalogo.db.catalogo_repository import CatalogoRepository
from apps.catalogo.services.catalogo_service import fn_get_articolo, fn_update_articolo
from apps.core.services.db_error_fields import db_error_code
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto


class ArticoliAmmessiDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def setUp(self) -> None:
        self.repo = CatalogoRepository()

    # 1. Il motivo arriva DECODIFICATO: un articolo cercato come componente di
    #    se' stesso e' escluso dalla distinta per costruzione.
    # ⚠️ Il padre si COSTRUISCE, composito (2026-11-09): dal giro 1 di
    #    brief-db-revisione-catalogo (BE12) il picker della distinta su un padre
    #    non composito rifiuta (`E_ARTICOLO_NON_COMPOSITO`). Fino a quel giorno
    #    il test prendeva «un articolo attivo qualunque»: una popolazione, che
    #    su un DB vuoto lo saltava.
    def test_un_escluso_porta_il_motivo_come_oggetto(self):
        codice = f"PYAMM-{uuid.uuid4().hex[:10].upper()}-P"
        try:
            with transaction.atomic(), connection.cursor() as cur:
                cur.execute(
                    "SELECT dbops.fn_pgtap_crea_articolo(%s, p_is_composito => true)::text", [codice],
                )
                articolo_id = cur.fetchone()[0]

                righe, _troncato = self.repo.lookup_articoli_ammessi(
                    documento="ARTICOLO", documento_id=None, search=codice,
                    tipo_eccezione=None, articolo_padre_id=articolo_id, limit=50,
                )

                se_stesso = [r for r in righe if str(r["id"]) == articolo_id]
                self.assertEqual(len(se_stesso), 1, "il padre cercato per codice non e' fra i trovati")
                motivo = se_stesso[0]["motivo"]
                self.assertIsInstance(motivo, dict, "motivo arriva come stringa: il FE lo leggerebbe come ammesso")
                self.assertEqual(motivo["reason"], "COMPONENTE_PADRE")
                self.assertTrue(motivo["reason_key"])
                raise Annulla
        except Annulla:
            pass

    # 2. L'ammesso porta None, e l'ordine della funzione arriva intatto: prima
    #    gli ammessi (A-7). Il caso si COSTRUISCE: due articoli con un segno
    #    proprio, cosi' la ricerca trova loro due e nessun altro. Il padre
    #    (escluso, COMPONENTE_PADRE) ha il codice che in ordine ALFABETICO viene
    #    PRIMA (`…-A`), l'altro (ammesso) dopo (`…-Z`): se l'elenco seguisse il
    #    codice e non il motivo, l'escluso starebbe in testa e il test cadrebbe.
    def test_gli_ammessi_vengono_prima(self):
        segno = uuid.uuid4().hex[:10].upper()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                # Il padre e' composito: e' il solo che ha una distinta (BE12).
                cur.execute(
                    "SELECT dbops.fn_pgtap_crea_articolo(%s, p_is_composito => true)",
                    [f"PYAMM-{segno}-A"],
                )
                padre = cur.fetchone()[0]
                cur.execute("SELECT dbops.fn_pgtap_crea_articolo(%s)", [f"PYAMM-{segno}-Z"])
                cur.fetchone()

                righe, troncato = self.repo.lookup_articoli_ammessi(
                    documento="ARTICOLO", documento_id=None, search=segno,
                    tipo_eccezione=None, articolo_padre_id=padre, limit=50,
                )

                self.assertFalse(troncato)
                self.assertEqual(
                    [(r["codice"], r["motivo"]["reason"] if r["motivo"] else None) for r in righe],
                    [(f"PYAMM-{segno}-Z", None), (f"PYAMM-{segno}-A", "COMPONENTE_PADRE")],
                    "prima l'ammesso, poi l'escluso col suo motivo",
                )
                raise Annulla
        except Annulla:
            pass

    # 3. Il vocabolario del tipo d'eccezione si legge dal DB.
    def test_tipo_eccezione_valido(self):
        self.assertTrue(self.repo.tipo_eccezione_valido("AGGIUNTA"))
        self.assertTrue(self.repo.tipo_eccezione_valido("ESCLUSIONE"))
        self.assertFalse(self.repo.tipo_eccezione_valido("BANANA"))

    # 4. La sede unica col tipo d'eccezione: parametri nell'ordine giusto e
    #    cast che regge. Un contratto che non esiste e' un documento senza
    #    listino, non un errore di binding.
    def test_il_binding_con_tipo_eccezione_regge(self):
        righe, troncato = self.repo.lookup_articoli_ammessi(
            documento="CONTRATTO", documento_id=-1, search="zz-nessun-articolo-zz",
            tipo_eccezione="AGGIUNTA", articolo_padre_id=None, limit=5,
        )
        self.assertEqual(righe, [])
        self.assertFalse(troncato)

    # 5. Un documento che il DB non conosce lo rifiuta la funzione.
    def test_documento_sconosciuto(self):
        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
            self.repo.lookup_articoli_ammessi(
                documento="NON_ESISTE", documento_id=1, search=None,
                tipo_eccezione=None, articolo_padre_id=None, limit=5,
            )
        self.assertEqual(db_error_code(ctx.exception), "E_DOC_TIPO_NON_GESTITO")

    # 6. Senza utente SUPER_ADMIN il verbo rifiuta, prima di guardare l'articolo.
    def test_correggi_struttura_senza_amministratore(self):
        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
            self.repo.correggi_struttura_articolo(
                "00000000-0000-0000-0000-000000000001", {"requires_lotto": True},
            )
        self.assertEqual(db_error_code(ctx.exception), "E_PERMESSO_NEGATO")

    # 7. La FORMA di `campi` la giudica il verbo, e il service non la ripete:
    #    assente (jsonb `null`), vuoto o lista -> E_PARAMETRO_INVALIDO, che e'
    #    DATO_ERRATO (400). Il SUPER_ADMIN si COSTRUISCE: il permesso viene
    #    prima della forma, e un utente preso dal DB non e' garantito.
    def test_correggi_struttura_forma_dei_campi(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                cur.execute(
                    "SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('struttura admin', true)"
                )
                admin = cur.fetchone()[0]
                cur.execute("SET LOCAL app.ruolo_applicativo = 'OPERATORE'")
                cur.execute("SET LOCAL app.current_user_id = %s", [str(admin)])
                for campi in (None, {}, ["requires_lotto"]):
                    with self.subTest(campi=campi):
                        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
                            self.repo.correggi_struttura_articolo(
                                "00000000-0000-0000-0000-000000000001", campi,
                            )
                        self.assertEqual(db_error_code(ctx.exception), "E_PARAMETRO_INVALIDO")
                raise Annulla
        except Annulla:
            pass

    # Scopo: il SUPER_ADMIN costruito e un articolo nuovo gestito a magazzino,
    #        senza lotto. Ritorna l'id dell'articolo.
    @staticmethod
    def _admin_e_articolo(cur) -> str:
        cur.execute(
            "SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano('struttura admin', true)"
        )
        admin = cur.fetchone()[0]
        cur.execute(
            "SELECT dbops.fn_pgtap_crea_articolo(%s, true, false)",
            [f"PYSTR-{uuid.uuid4().hex[:8]}"],
        )
        articolo_id = str(cur.fetchone()[0])
        cur.execute("SET LOCAL app.ruolo_applicativo = 'OPERATORE'")
        cur.execute("SET LOCAL app.current_user_id = %s", [str(admin)])
        return articolo_id

    @staticmethod
    def _lotto_e_descrizione(cur, articolo_id: str) -> tuple[bool, str]:
        cur.execute(
            "SELECT requires_lotto, descrizione FROM catalogo.articoli WHERE id = %s", [articolo_id]
        )
        return cur.fetchone()

    # 8. R-BE-1: la correzione viaggia nel PATCH, e le due scritture sono UNA
    #    transazione. Un UPDATE che il DB rifiuta (un'aliquota che non esiste:
    #    la FK, DOPO il verbo) annulla anche la correzione; un PATCH buono le
    #    scrive tutte e due. Fino al 2026-10-18 erano due chiamate, e la prima
    #    restava scritta.
    def test_correzione_e_patch_in_una_transazione(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                articolo_id = self._admin_e_articolo(cur)
                prima = self._lotto_e_descrizione(cur, articolo_id)
                self.assertFalse(prima[0])

                with self.assertRaises(ServiceError):
                    fn_update_articolo(articolo_id, {
                        "iva_id": 2_000_000_000,
                        "correzione_struttura": {"requires_lotto": True},
                    })
                self.assertEqual(self._lotto_e_descrizione(cur, articolo_id), prima)

                dettaglio = fn_update_articolo(articolo_id, {
                    "descrizione": "Corretto in un colpo",
                    "correzione_struttura": {"requires_lotto": True},
                })
                self.assertTrue(dettaglio["requires_lotto"])
                self.assertEqual(self._lotto_e_descrizione(cur, articolo_id), (True, "Corretto in un colpo"))
                raise Annulla
        except Annulla:
            pass

    # 9. Le colonne che la scheda riapre in correzione arrivano col dettaglio,
    #    dalla sede del DB (R-DB-3): le stesse, nello stesso ordine.
    def test_struttura_correggibile_dalla_sede(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                articolo_id = self._admin_e_articolo(cur)
                cur.execute("SELECT catalogo.fn_articolo_colonne_struttura()")
                sede = list(cur.fetchone()[0])
                self.assertIn("requires_lotto", sede)
                self.assertEqual(fn_get_articolo(articolo_id)["struttura_correggibile"], sede)
                raise Annulla
        except Annulla:
            pass
