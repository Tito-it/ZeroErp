# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le tre ANAGRAFICHE di magazzino sul DATABASE PROVVISTO — l'unico
#        livello che vede la giuntura Python↔SQL: crea/aggiorna/dettaglio di
#        magazzino, ubicazione e lotto sul mondo costruito; il 404 no-leak
#        dell'altro emittente; i rifiuti del DB tradotti col campo (duplicato,
#        padre di altro magazzino, scadenza prima dell'arrivo); il lock del
#        codice; ogni colonna di whitelist che produce SQL che parte
#        (`feedback_contratto_dichiarato_provalo_intero`). Dal 2026-11-22 le
#        scritture passano dai VERBI del DB (R-1 di
#        brief-db-magazzino-tutte-le-scritture-dal-verbo): il contratto dei
#        lettori del backend e' quello del DB, e senza livello il verbo
#        rifiuta; il lotto e' dell'AZIENDA (brief-db-magazzino-lotto-dell-azienda).
# Note: ⚠️ Il mondo si COSTRUISCE, non si cerca (guida pgtap §79): azienda e
#       operatore col livello TUTTO su magazzino (`apri_operatore_con_aree`:
#       i verbi chiedono il livello sull'oggetto), poi due magazzini e un
#       articolo per lotti dai BB `dbops.fn_pgtap_crea_*`.
#       Tutto in transazione ANNULLATA; ogni rifiuto atteso in un SAVEPOINT.
#       ⚠️ Il lock su `ubicazioni.magazzino_id` (D1 del brief) lo genera il job
#       delle automazioni: qui NON si prova (il PATCH non lo manda nemmeno).
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) AnagraficheMagazzinoDbTests.test_magazzino_crea_legge_aggiorna_per_delta
2) AnagraficheMagazzinoDbTests.test_il_codice_del_magazzino_e_lockato_e_il_duplicato_dice_il_campo
3) AnagraficheMagazzinoDbTests.test_ubicazioni_del_magazzino_padre_e_guard
4) AnagraficheMagazzinoDbTests.test_lotti_dell_articolo_e_la_scadenza
5) AnagraficheMagazzinoDbTests.test_un_altro_emittente_non_vede_il_magazzino_ne_le_ubicazioni
6) AnagraficheMagazzinoDbTests.test_ogni_ordinamento_della_whitelist_esegue
7) AnagraficheMagazzinoDbTests.test_la_ricerca_trova_ogni_colonna_accesa
8) AnagraficheMagazzinoDbTests.test_i_lettori_del_backend_sono_il_contratto_del_db
9) AnagraficheMagazzinoDbTests.test_senza_livello_sull_oggetto_il_verbo_rifiuta
10) AnagraficheMagazzinoDbTests.test_il_lotto_e_dell_azienda
11) AnagraficheMagazzinoDbTests.test_le_lunghezze_dei_testi_sono_quelle_delle_colonne
"""
from __future__ import annotations

import unittest
from datetime import timedelta

from django.db import DatabaseError, connection, transaction

from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import (
    apri_contesto_su,
    apri_operatore_con_aree,
    esegui_fixture,
    richiedi_db_provvisto,
    richiedi_ruolo_soggetto_a_rls,
    verifica_ricerca_colonna_per_colonna,
)
from apps.magazzino.db.anagrafiche_magazzino_repository import (
    LOTTI_SORT_COLUMNS,
    MAGAZZINI_SORT_COLUMNS,
    UBICAZIONI_SORT_COLUMNS,
    AnagraficheMagazzinoRepository,
)
from apps.magazzino.services import anagrafiche_magazzino_service as svc


_FIXTURE: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _mag AS
    SELECT dbops.fn_pgtap_crea_magazzino('BE-ANA-A', false) AS mag_a,
           dbops.fn_pgtap_crea_magazzino('BE-ANA-U', true)  AS mag_u
    """,
    """
    CREATE TEMP TABLE _art AS
    SELECT dbops.fn_pgtap_crea_articolo('BE-ANA-L', true, true) AS art_l
    """,
)


class _Mondo:
    """Gli id del mondo costruito."""

    def __init__(self, cur) -> None:
        self.uid = apri_operatore_con_aree(cur, aree=("magazzino",))
        esegui_fixture(cur, _FIXTURE)
        cur.execute("SELECT mag_a, mag_u FROM _mag")
        self.mag_a, self.mag_u = (int(x) for x in cur.fetchone())
        cur.execute("SELECT art_l FROM _art")
        self.art_l = str(cur.fetchone()[0])
        # L'indirizzo dell'azienda: quello che il BB ha dato al magazzino A.
        cur.execute("SELECT indirizzo_dettaglio_id FROM magazzino.magazzini WHERE id = %s", [self.mag_a])
        self.indirizzo_id = int(cur.fetchone()[0])
        cur.execute("SELECT id FROM config.tipi_ubicazione WHERE codice_interno = 'TIPO_UBI_STORAGE'")
        self.tipo_ubi = int(cur.fetchone()[0])


class AnagraficheMagazzinoDbTests(unittest.TestCase):
    """Magazzini, ubicazioni e lotti sul mondo costruito."""

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()
        # Il 404 no-leak (5) si prova solo con un ruolo che la RLS vede.
        richiedi_ruolo_soggetto_a_rls("magazzino.magazzini")

    # Scopo: esegue `azione(cur, mondo)` in una transazione SEMPRE annullata.
    def _nel_mondo(self, azione):
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    return azione(cur, _Mondo(cur))
            finally:
                transaction.set_rollback(True)

    # Scopo: un'azione che DEVE essere rifiutata, in un savepoint.
    @staticmethod
    def _rifiuto(fn) -> ServiceError:
        try:
            with transaction.atomic():
                fn()
        except ServiceError as e:
            return e
        raise AssertionError("atteso un rifiuto, e' passato")

    # 1.
    def test_magazzino_crea_legge_aggiorna_per_delta(self):
        def _prova(cur, m):
            creato = svc.crea_magazzino({
                "codice": "be-ana-n", "descrizione": "Nuovo deposito",
                "indirizzo_dettaglio_id": m.indirizzo_id, "usa_ubicazioni": True,
            })
            # `trgfn_magazzini_normalize` alza il codice; l'emittente lo mette
            # il DB dalla GUC; i display field arrivano decodificati.
            self.assertEqual(creato["codice"], "BE-ANA-N")
            self.assertTrue(creato["usa_ubicazioni"])
            self.assertIsNotNone(creato["emittente_fiscale_id"])
            self.assertIsNotNone(creato["emittente_codice"])
            self.assertIsNotNone(creato["emittente_soggetto_id"])
            self.assertIsNotNone(creato["indirizzo_normalizzato"])
            self.assertEqual(creato["ubicazioni_count"], 0)
            lista = svc.list_magazzini(auth_user_id=m.uid, search="BE-ANA", limit=10)
            self.assertEqual(lista["count"], 3)
            # Solo le attive: spento, il nuovo esce dalla lista di default.
            aggiornato = svc.aggiorna_magazzino(creato["id"], {"descrizione": "Deposito nord", "attivo": False})
            self.assertEqual((aggiornato["descrizione"], aggiornato["attivo"]), ("Deposito nord", False))
            self.assertEqual(svc.list_magazzini(auth_user_id=m.uid, search="BE-ANA", attivo=True, limit=10)["count"], 2)
            self.assertEqual(svc.list_magazzini(auth_user_id=m.uid, search="BE-ANA-N", limit=10)["count"], 1)
            # Il dettaglio di uno spento si legge (e si riattiva).
            self.assertFalse(svc.get_magazzino(creato["id"])["attivo"])
            self.assertTrue(svc.aggiorna_magazzino(creato["id"], {"attivo": True})["attivo"])
        self._nel_mondo(_prova)

    # 2. Il lock del codice e' del DB e arriva col SUO codice; il duplicato
    #    arriva come E_ANAG_DUPLICATO col campo `codice`.
    def test_il_codice_del_magazzino_e_lockato_e_il_duplicato_dice_il_campo(self):
        def _prova(cur, m):
            e = self._rifiuto(lambda: svc.aggiorna_magazzino(m.mag_a, {"codice": "ALTRO"}))
            # ⚠️ `E_CODICE_NON_MODIFICABILE` dal 2026-09-23: il vecchio
            #    `CODICE_NON_MODIFICABILE` e' obsoleto dal 2026-08-05 e il
            #    changeSet `90_end/20260923-02` ha rigenerato i lock coi codici
            #    vivi (brief-db-codici-ritirati-negli-argomenti-dei-trigger).
            self.assertEqual(e.code, "E_CODICE_NON_MODIFICABILE")
            # Lo stesso codice riscritto NON e' un cambio: il delta non lo manda,
            # e se lo manda il lock non scatta (OLD = NEW).
            self.assertEqual(svc.aggiorna_magazzino(m.mag_a, {"codice": "BE-ANA-A"})["codice"], "BE-ANA-A")
            e = self._rifiuto(lambda: svc.crea_magazzino({
                "codice": "BE-ANA-A", "descrizione": "doppione", "indirizzo_dettaglio_id": m.indirizzo_id,
            }))
            self.assertEqual((e.code, e.context.get("field")), ("E_ANAG_DUPLICATO", "codice"))
            # Il guard su `usa_ubicazioni` a registro vuoto: senza movimenti passa.
            self.assertTrue(svc.aggiorna_magazzino(m.mag_a, {"usa_ubicazioni": True})["usa_ubicazioni"])
        self._nel_mondo(_prova)

    # 3. Le ubicazioni: creazione nel magazzino del path, padre dello stesso
    #    magazzino, il guard del DB su un padre di un ALTRO magazzino (campo
    #    `parent_id`), il 404 sulla coppia, il duplicato per magazzino.
    def test_ubicazioni_del_magazzino_padre_e_guard(self):
        def _prova(cur, m):
            area = svc.crea_ubicazione(m.mag_u, {"codice": "A", "tipo_id": m.tipo_ubi, "descrizione": "Area A"})
            corsia = svc.crea_ubicazione(m.mag_u, {"codice": "A-01", "tipo_id": m.tipo_ubi, "parent_id": area["id"], "corsia": "01"})
            self.assertEqual((corsia["parent_id"], corsia["parent_codice"], corsia["tipo_codice"] is not None), (area["id"], "A", True))
            self.assertEqual(svc.get_magazzino(m.mag_u)["ubicazioni_count"], 2)
            lista = svc.list_ubicazioni(m.mag_u, limit=10)
            self.assertEqual([u["codice"] for u in lista["results"]], ["A", "A-01"])
            self.assertEqual(svc.list_ubicazioni(m.mag_u, parent_id=area["id"], limit=10)["count"], 1)
            self.assertEqual(svc.list_ubicazioni(m.mag_a, limit=10)["count"], 0)
            # Il padre di un altro magazzino: lo rifiuta il trigger, col campo.
            e = self._rifiuto(lambda: svc.crea_ubicazione(m.mag_a, {"codice": "X", "tipo_id": m.tipo_ubi, "parent_id": area["id"]}))
            self.assertEqual(e.code, "E_MAG_UBICAZIONE_PADRE_DI_ALTRO_MAGAZZINO")
            self.assertEqual(e.fields, ("parent_id",))
            # Un ciclo (l'area sotto la sua corsia): codice separato.
            e = self._rifiuto(lambda: svc.aggiorna_ubicazione(m.mag_u, area["id"], {"parent_id": corsia["id"]}))
            self.assertEqual(e.code, "E_MAG_UBICAZIONE_PADRE_CICLICO")
            # La coppia e' la risorsa: l'ubicazione di U letta sotto A non c'e'.
            e = self._rifiuto(lambda: svc.get_ubicazione(m.mag_a, area["id"]))
            self.assertEqual(e.code, "E_MAG_UBICAZIONE_NON_TROVATA")
            # Il duplicato vale PER magazzino: stesso codice in A passa.
            svc.crea_ubicazione(m.mag_a, {"codice": "A", "tipo_id": m.tipo_ubi})
            e = self._rifiuto(lambda: svc.crea_ubicazione(m.mag_u, {"codice": "A", "tipo_id": m.tipo_ubi}))
            self.assertEqual((e.code, e.context.get("field")), ("E_ANAG_DUPLICATO", "codice"))
            # Il delta: `parent_id: null` rende radice, la posizione si azzera.
            radice = svc.aggiorna_ubicazione(m.mag_u, corsia["id"], {"parent_id": None, "corsia": ""})
            self.assertEqual((radice["parent_id"], radice["corsia"]), (None, None))
        self._nel_mondo(_prova)

    # 4. I lotti: per articolo (obbligatorio), la scadenza prima dell'arrivo
    #    la rifiuta il CHECK col campo, il duplicato vale per articolo
    #    nell'azienda (il vincolo `uq_mag_lotti_emittente_articolo_codice`), il
    #    delta con `data_scadenza: null` la toglie; nasce con l'azienda della
    #    sessione.
    def test_lotti_dell_articolo_e_la_scadenza(self):
        def _prova(cur, m):
            oggi = oggi_aziendale()
            lotto = svc.crea_lotto({"articolo_id": m.art_l, "codice": "L-01", "data_arrivo": oggi.isoformat(),
                                    "data_scadenza": (oggi + timedelta(days=30)).isoformat()})
            self.assertEqual((lotto["codice"], lotto["data_arrivo"], lotto["data_scadenza"]), ("L-01", oggi, oggi + timedelta(days=30)))
            cur.execute("SELECT emittente_fiscale_id FROM magazzino.magazzini WHERE id = %s", [m.mag_a])
            self.assertEqual(lotto["emittente_fiscale_id"], cur.fetchone()[0])
            e = self._rifiuto(lambda: svc.crea_lotto({"articolo_id": m.art_l, "codice": "L-02", "data_arrivo": oggi.isoformat(),
                                                      "data_scadenza": (oggi - timedelta(days=1)).isoformat()}))
            self.assertEqual((e.code, e.context.get("field")), ("E_MAGAZZINO_VALIDATION", "data_scadenza"))
            e = self._rifiuto(lambda: svc.crea_lotto({"articolo_id": m.art_l, "codice": "L-01", "data_arrivo": oggi.isoformat()}))
            self.assertEqual((e.code, e.context.get("field")), ("E_ANAG_DUPLICATO", "codice"))
            # La lista pretende l'articolo (uuid): senza e' un 400 col campo.
            e = self._rifiuto(lambda: svc.list_lotti(auth_user_id=m.uid, articolo_id=None, limit=10))
            self.assertEqual((e.code, e.context.get("field")), ("E_MAGAZZINO_VALIDATION", "articolo_id"))
            e = self._rifiuto(lambda: svc.list_lotti(auth_user_id=m.uid, articolo_id="abc", limit=10))
            self.assertEqual(e.code, "E_MAGAZZINO_VALIDATION")
            self.assertEqual(svc.list_lotti(auth_user_id=m.uid, articolo_id=m.art_l, limit=10)["count"], 1)
            self.assertEqual(svc.list_lotti(auth_user_id=m.uid, articolo_id=m.art_l, search="ZZZ", limit=10)["count"], 0)
            senza = svc.aggiorna_lotto(lotto["id"], {"data_scadenza": None})
            self.assertIsNone(senza["data_scadenza"])
            e = self._rifiuto(lambda: svc.get_lotto(999_999_999))
            self.assertEqual(e.code, "E_MAG_LOTTO_NON_TROVATO")
        self._nel_mondo(_prova)

    # 5. Il 404 no-leak: l'altro emittente non vede il magazzino (dettaglio e
    #    lista), ne' le sue ubicazioni, e non puo' scrivergli dentro.
    def test_un_altro_emittente_non_vede_il_magazzino_ne_le_ubicazioni(self):
        def _prova(cur, m):
            svc.crea_ubicazione(m.mag_u, {"codice": "A", "tipo_id": m.tipo_ubi})
            cur.execute("CREATE TEMP TABLE _mondo2 AS SELECT x.* FROM dbops.fn_pgtap_crea_emittente_operatore('B2') x")
            cur.execute("SELECT auth_user_id FROM _mondo2")
            uid2 = apri_contesto_su(cur, int(cur.fetchone()[0]))
            self.assertEqual(self._rifiuto(lambda: svc.get_magazzino(m.mag_u)).code, "E_MAG_MAGAZZINO_NON_TROVATO")
            self.assertEqual(svc.list_magazzini(auth_user_id=uid2, search="BE-ANA", limit=10)["count"], 0)
            self.assertEqual(self._rifiuto(lambda: svc.list_ubicazioni(m.mag_u, limit=10)).code, "E_MAG_MAGAZZINO_NON_TROVATO")
            self.assertEqual(
                self._rifiuto(lambda: svc.crea_ubicazione(m.mag_u, {"codice": "B", "tipo_id": m.tipo_ubi})).code,
                "E_MAG_MAGAZZINO_NON_TROVATO",
            )
            self.assertEqual(self._rifiuto(lambda: svc.aggiorna_magazzino(m.mag_u, {"descrizione": "x"})).code, "E_MAG_MAGAZZINO_NON_TROVATO")
        self._nel_mondo(_prova)

    # 6. Ogni colonna delle tre whitelist, in ENTRAMBI i versi, produce SQL che
    #    parte — il verso che un mock non sa rifiutare (500, non 400).
    def test_ogni_ordinamento_della_whitelist_esegue(self):
        def _prova(cur, m):
            for col in MAGAZZINI_SORT_COLUMNS:
                for verso in ("asc", "desc"):
                    with self.subTest(lista="magazzini", col=col, verso=verso):
                        svc.list_magazzini(auth_user_id=m.uid, order_by=col, order_dir=verso, limit=5)
            for col in UBICAZIONI_SORT_COLUMNS:
                for verso in ("asc", "desc"):
                    with self.subTest(lista="ubicazioni", col=col, verso=verso):
                        svc.list_ubicazioni(m.mag_u, order_by=col, order_dir=verso, limit=5)
            for col in LOTTI_SORT_COLUMNS:
                for verso in ("asc", "desc"):
                    with self.subTest(lista="lotti", col=col, verso=verso):
                        svc.list_lotti(auth_user_id=m.uid, articolo_id=m.art_l, order_by=col, order_dir=verso, limit=5)
        self._nel_mondo(_prova)

    # 7. La ricerca libera (BB `add_ricerca_full_condition`): per ogni colonna
    #    che il CATALOGO accende si cerca un valore che sta SOLO in quella
    #    colonna, e la riga deve uscire (`verifica_ricerca_colonna_per_colonna`).
    #    Le tre liste non hanno `vista_sql`: questo e' il loro esercizio sul DB
    #    vero (`test_ricerca_full_db` lo nomina).
    def test_la_ricerca_trova_ogni_colonna_accesa(self):
        def _prova(cur, m):
            oggi = oggi_aziendale().isoformat()
            svc.aggiorna_magazzino(m.mag_a, {"descrizione": "Deposito ricdescmag"})
            ubi = svc.crea_ubicazione(m.mag_u, {"codice": "RICCODUBI", "descrizione": "Scaffale ricdescubi", "tipo_id": m.tipo_ubi})
            lotto = svc.crea_lotto({"articolo_id": m.art_l, "codice": "RICCODLOT", "data_arrivo": oggi})
            verifica_ricerca_colonna_per_colonna(
                self, cur, "magazzino.magazzini", m.mag_a,
                {"codice": "BE-ANA-A", "descrizione": "ricdescmag"},
                lambda t: svc.list_magazzini(auth_user_id=m.uid, search=t, limit=10)["results"],
            )
            verifica_ricerca_colonna_per_colonna(
                self, cur, "magazzino.ubicazioni", ubi["id"],
                {"codice": "riccodubi", "descrizione": "ricdescubi"},
                lambda t: svc.list_ubicazioni(m.mag_u, search=t, limit=10)["results"],
            )
            verifica_ricerca_colonna_per_colonna(
                self, cur, "magazzino.lotti", lotto["id"],
                {"codice": "riccodlot"},
                lambda t: svc.list_lotti(auth_user_id=m.uid, articolo_id=m.art_l, search=t, limit=10)["results"],
            )
        self._nel_mondo(_prova)

    # 8. Le chiavi che il backend sa LEGGERE sono quelle che il DB AMMETTE
    #    (`fn_<tabella>_colonne_ammesse`): una divergenza qui sarebbe un 500 su
    #    ogni scrittura (`campi_per_presenza`). L'articolo del lotto e'
    #    un'identita' del gesto, argomento del verbo e non colonna.
    def test_i_lettori_del_backend_sono_il_contratto_del_db(self):
        def _prova(cur, m):
            repo = AnagraficheMagazzinoRepository()
            attese = {
                ("magazzini", "crea"): svc.CREATE_KEYS_MAGAZZINO,
                ("magazzini", "modifica"): svc.UPDATE_KEYS_MAGAZZINO,
                ("ubicazioni", "crea"): svc.CREATE_KEYS_UBICAZIONE,
                ("ubicazioni", "modifica"): svc.UPDATE_KEYS_UBICAZIONE,
                ("lotti", "crea"): svc.CREATE_KEYS_LOTTO - {"articolo_id"},
                ("lotti", "modifica"): svc.UPDATE_KEYS_LOTTO,
            }
            for (tabella, gesto), chiavi in attese.items():
                with self.subTest(tabella=tabella, gesto=gesto):
                    self.assertEqual(repo.colonne_ammesse(tabella, gesto), chiavi)
        self._nel_mondo(_prova)

    # 9. Il permesso lo dice il VERBO (non solo l'endpoint): con LETTURA su
    #    magazzino il service, chiamato senza view, riceve il rifiuto del DB.
    def test_senza_livello_sull_oggetto_il_verbo_rifiuta(self):
        def _prova(cur, m):
            # Il livello si abbassa dal builder del DB: le eccezioni utente sono
            # in sola lettura per l'app (giro 10-quater, 2026-11-27).
            cur.execute(
                "SELECT dbops.fn_pgtap_concedi_livello_area(%s, 'magazzino', 'LETTURA'::config.livello_accesso)",
                [m.uid],
            )
            self.assertIsNotNone(cur.fetchone()[0])
            e = self._rifiuto(lambda: svc.crea_magazzino({
                "codice": "BE-ANA-P", "descrizione": "x", "indirizzo_dettaglio_id": m.indirizzo_id,
            }))
            self.assertEqual(e.code, "E_PERMESSO_NEGATO")
            e = self._rifiuto(lambda: svc.aggiorna_magazzino(m.mag_a, {"descrizione": "x"}))
            self.assertEqual(e.code, "E_PERMESSO_NEGATO")
            e = self._rifiuto(lambda: svc.crea_ubicazione(m.mag_u, {"codice": "P", "tipo_id": m.tipo_ubi}))
            self.assertEqual(e.code, "E_PERMESSO_NEGATO")
            oggi = oggi_aziendale().isoformat()
            e = self._rifiuto(lambda: svc.crea_lotto({"articolo_id": m.art_l, "codice": "L-P", "data_arrivo": oggi}))
            self.assertEqual(e.code, "E_PERMESSO_NEGATO")
        self._nel_mondo(_prova)

    # 10. Il lotto e' dell'AZIENDA: due aziende hanno ciascuna il proprio
    #     «L-01» dello stesso articolo; ognuna vede e modifica solo il suo, e
    #     quello dell'altra risponde «non trovato» (no-leak) in lettura e in
    #     scrittura.
    def test_il_lotto_e_dell_azienda(self):
        def _prova(cur, m):
            oggi = oggi_aziendale().isoformat()
            lotto_a = svc.crea_lotto({"articolo_id": m.art_l, "codice": "L-01", "data_arrivo": oggi})
            uid_b = apri_operatore_con_aree(cur, aree=("magazzino",))
            lotto_b = svc.crea_lotto({"articolo_id": m.art_l, "codice": "L-01", "data_arrivo": oggi})
            self.assertNotEqual(lotto_a["emittente_fiscale_id"], lotto_b["emittente_fiscale_id"])
            lista_b = svc.list_lotti(auth_user_id=uid_b, articolo_id=m.art_l, limit=10)
            self.assertEqual([x["id"] for x in lista_b["results"]], [lotto_b["id"]])
            self.assertEqual(self._rifiuto(lambda: svc.get_lotto(lotto_a["id"])).code, "E_MAG_LOTTO_NON_TROVATO")
            self.assertEqual(
                self._rifiuto(lambda: svc.aggiorna_lotto(lotto_a["id"], {"data_scadenza": None})).code,
                "E_MAG_LOTTO_NON_TROVATO",
            )
            # Il verbo da solo dice lo stesso (il 404 non e' solo la lettura del service).
            with self.assertRaises(DatabaseError) as rifiuto, transaction.atomic():
                AnagraficheMagazzinoRepository().update_lotto(lotto_a["id"], {"attivo": False})
            self.assertEqual(structured_db_error_code(rifiuto.exception), "E_MAG_LOTTO_NON_TROVATO")
            # Torna l'azienda A: vede il suo e non quello di B.
            apri_contesto_su(cur, m.uid)
            lista_a = svc.list_lotti(auth_user_id=m.uid, articolo_id=m.art_l, limit=10)
            self.assertEqual([x["id"] for x in lista_a["results"]], [lotto_a["id"]])
        self._nel_mondo(_prova)

    # 11. Ogni testo che il backend legge ha la lunghezza della SUA colonna:
    #     piu' lunga, il DB risponde 22001 (un 500); piu' corta, il backend
    #     rifiuta un valore che il modello ammette. Fino al 2026-11-23 c'era un
    #     tetto unico (codice 50, descrizione 500), sbagliato in tutti e due i
    #     versi. Si confronta col catalogo, non con una copia dei numeri.
    def test_le_lunghezze_dei_testi_sono_quelle_delle_colonne(self):
        letture = {
            "magazzini": (svc._NASCITA_MAGAZZINO, svc._MODIFICA_MAGAZZINO),
            "ubicazioni": (svc._NASCITA_UBICAZIONE, svc._MODIFICA_UBICAZIONE),
            "lotti": (svc._NASCITA_LOTTO, svc._MODIFICA_LOTTO),
        }
        with connection.cursor() as cur:
            for tabella, gesti in letture.items():
                for lettura in gesti:
                    for colonna, (_nullable, max_len) in lettura.get("testi", {}).items():
                        cur.execute(
                            "SELECT character_maximum_length FROM information_schema.columns"
                            " WHERE table_schema = 'magazzino' AND table_name = %s AND column_name = %s",
                            [tabella, colonna],
                        )
                        riga = cur.fetchone()
                        with self.subTest(tabella=tabella, colonna=colonna):
                            self.assertIsNotNone(riga, "colonna assente")
                            self.assertEqual(max_len, riga[0])
