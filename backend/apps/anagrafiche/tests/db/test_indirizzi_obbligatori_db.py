# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Gli indirizzi OBBLIGATORI lato BE, sul DB vero
#        (brief-db-fornitore-privato-indirizzi, R-6 §12.4 e R-7 §13.4):
#        - R-6: cancellare o cambiare di tipo l'unico indirizzo obbligatorio
#          di un ruolo o di un soggetto e' rifiutato, col codice del suo layer
#          (`E_INDIRIZZO_OBBLIGATORIO_MANCANTE` il ruolo,
#          `E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO` il soggetto); il
#          ripiego lo evita; sostituirlo nella stessa transazione passa;
#        - R-7: il cambio di natura porta gli indirizzi che la natura nuova
#          chiede, letti da `motivi_cambio_natura` e scritti dal PATCH.
# ⚠️ I guard sono constraint trigger DIFFERITI: giudicano al COMMIT, e la
#    transazione del test si annulla. Il commit lo simula
#    `SET CONSTRAINTS ALL IMMEDIATE`; i builder escono coi vincoli IMMEDIATE,
#    e il setUp torna a quelli di una transazione nuova (DEFERRED).
# ⭐ I casi si COSTRUISCONO: le righe di matrice che il test legge le scrive
#    il test (`_matrice`), nella transazione annullata. Il seed decide solo cio'
#    che il test non nomina.
#    Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) IndirizziObbligatoriRuoloDbTests.test_cancellare_l_unico_obbligatorio_rifiutato
2) IndirizziObbligatoriRuoloDbTests.test_cambiare_tipo_all_unico_obbligatorio_rifiutato
3) IndirizziObbligatoriRuoloDbTests.test_col_ripiego_l_obbligatorio_si_cancella
3b) IndirizziObbligatoriRuoloDbTests.test_sostituire_l_unico_obbligatorio_passa
4) IndirizziObbligatoriSoggettoDbTests.test_cancellare_la_sede_legale_rifiutato_col_codice_del_soggetto
5) IndirizziObbligatoriSoggettoDbTests.test_sostituire_la_sede_legale_passa
6) CambioNaturaIndirizziDbTests.test_motivi_elencano_l_indirizzo_che_la_natura_nuova_chiede
7) CambioNaturaIndirizziDbTests.test_patch_senza_l_indirizzo_rifiutato_al_commit
8) CambioNaturaIndirizziDbTests.test_patch_con_l_indirizzo_del_ruolo_passa
9) CambioNaturaIndirizziDbTests.test_indirizzi_senza_la_natura_rifiutati
9b) CambioNaturaIndirizziDbTests.test_indirizzi_con_la_natura_di_oggi_rifiutati
10) CambioNaturaIndirizziDbTests.test_ruolo_di_un_altro_soggetto_rifiutato
"""
from __future__ import annotations

import unittest
from collections.abc import Callable
from typing import Any

from django.db import connection, transaction

from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_contesto_operatore, apri_transazione_annullata, richiedi_db_provvisto

_CODICE_RUOLO = "E_INDIRIZZO_OBBLIGATORIO_MANCANTE"
_CODICE_SOGGETTO = "E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO"

# Le due matrici degli indirizzi: la colonna che porta il titolare della riga
# (tipo di ruolo, natura) e la sua tabella di codici.
_MATRICI: dict[str, tuple[str, str, str]] = {
    "ruolo": ("config.tipi_ruolo_tipi_indirizzo", "tipo_ruolo_id", "config.tipi_ruoli"),
    "natura": ("config.tipi_soggetto_dettaglio_tipi_indirizzo", "tipo_soggetto_dettaglio_id",
               "config.tipi_soggetto_dettaglio"),
}


# Scopo: La base comune: transazione annullata, contesto operatore, e gli
#        strumenti per costruire i casi e simulare il commit.
class _IndirizziObbligatoriBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)
            cur.execute("SELECT codice_interno, id FROM config.tipi_indirizzi")
            self.tipo = dict(cur.fetchall())
            cur.execute("SELECT codice_interno, id FROM config.tipi_soggetto_dettaglio")
            self.natura = dict(cur.fetchall())

    @staticmethod
    def _service():
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        return SoggettiService()

    # Scopo: Una riga di matrice nello stato voluto: cancellata (`obbligatorio`
    #        None) o riscritta, col ripiego. L'id non ha default.
    def _matrice(
        self, matrice: str, titolare: str, tipo: str,
        obbligatorio: bool | None, ripiego: str | None = None,
    ) -> None:
        tabella, colonna, codici = _MATRICI[matrice]
        with connection.cursor() as cur:
            cur.execute(f"SELECT id FROM {codici} WHERE codice_interno = %s", [titolare])
            titolare_id = cur.fetchone()[0]
            cur.execute(
                f"DELETE FROM {tabella} WHERE {colonna} = %s AND tipo_indirizzo_id = %s",
                [titolare_id, self.tipo[tipo]],
            )
            if obbligatorio is None:
                return
            cur.execute(
                f"INSERT INTO {tabella} (id, {colonna}, tipo_indirizzo_id, obbligatorio,"
                "                        fallback_tipo_indirizzo_id, attivo)"
                f" SELECT COALESCE(max(id), 0) + 1, %s, %s, %s, %s, true FROM {tabella}",
                [titolare_id, self.tipo[tipo], obbligatorio, self.tipo[ripiego] if ripiego else None],
            )

    # Scopo: Il primo argomento dei builder sulle madri del DB; ognuno esce coi
    #        vincoli IMMEDIATE, e qui si torna a quelli di una transazione nuova.
    @staticmethod
    def _builder(sql: str, params: list[Any] | None = None) -> Any:
        with connection.cursor() as cur:
            cur.execute(sql, params or [])
            valore = cur.fetchone()[0]
            cur.execute("SET CONSTRAINTS ALL DEFERRED")
        return valore

    # Scopo: Un indirizzo della forma delle madri, sul dettaglio di un builder.
    def _indirizzo(self, tipo: str) -> dict[str, Any]:
        dettaglio = self._builder("SELECT dbops.fn_pgtap_crea_indirizzo_dettaglio(%s)", [f"obbligatori {tipo}"])
        return {"tipo_indirizzo_codice_interno": tipo, "indirizzo_dettaglio_id": dettaglio}

    # Scopo: I vincoli differiti, controllati adesso (al posto del COMMIT).
    @staticmethod
    def _commit_simulato() -> None:
        with connection.cursor() as cur:
            cur.execute("SET CONSTRAINTS ALL IMMEDIATE")

    # Scopo: La scrittura, poi il commit simulato, in un blocco proprio: il
    #        rifiuto e' quello che arriverebbe all'uscita della transazione.
    def _rifiuto(self, fn: Callable[[], Any], codice: str) -> None:
        try:
            with transaction.atomic():
                fn()
                self._commit_simulato()
        except Exception as exc:  # la strada e' cio' che si prova
            api = ErrorTranslator.to_api_error(exc)
            self.assertEqual(api.code, codice, f"{api.message} — {exc!r}")
            self.assertEqual(ErrorTranslator.get_http_status(api), 400)
            return
        self.fail(f"atteso {codice}, accettato")

    def _passa(self, fn: Callable[[], Any]) -> None:
        with transaction.atomic():
            fn()
            self._commit_simulato()

    @staticmethod
    def _tipi_del_ruolo(soggetto_ruolo_id: int) -> list[str]:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT ti.codice_interno FROM anagrafiche.indirizzi i"
                "  JOIN config.tipi_indirizzi ti ON ti.id = i.tipo_indirizzo_id"
                " WHERE i.soggetto_ruolo_id = %s ORDER BY 1",
                [soggetto_ruolo_id],
            )
            return [r[0] for r in cur.fetchall()]

    def _indirizzo_del_ruolo(self, soggetto_ruolo_id: int, tipo: str) -> int:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id FROM anagrafiche.indirizzi WHERE soggetto_ruolo_id = %s AND tipo_indirizzo_id = %s",
                [soggetto_ruolo_id, self.tipo[tipo]],
            )
            return cur.fetchone()[0]


# Scopo: R-6 punti 1 e 4, layer RUOLO: il cliente di una societa', con la sola
#        fatturazione obbligatoria (ripiego il domicilio fiscale, facoltativo).
class IndirizziObbligatoriRuoloDbTests(_IndirizziObbligatoriBase):
    def setUp(self) -> None:
        super().setUp()
        self._matrice("ruolo", "CL", "FATT", True, "DOMFISC")
        self._matrice("ruolo", "CL", "DOMFISC", False)
        self._matrice("ruolo", "CL", "SPED", False)
        # La natura della societa' ammette i tre tipi: si scrive anche lei.
        for tipo in ("FATT", "DOMFISC", "SPED"):
            self._matrice("natura", "SC", tipo, False)
        societa = self._builder("SELECT dbops.fn_pgtap_crea_soggetto_pg('Obbligatori ruolo BE')")
        self.ruolo = self._builder("SELECT dbops.fn_pgtap_crea_soggetto_ruolo(%s, 'CL')", [societa])
        # La fixture scrive il primo obbligatorio del requisito, e solo quello.
        self.assertEqual(self._tipi_del_ruolo(self.ruolo), ["FATT"])
        self.fatt = self._indirizzo_del_ruolo(self.ruolo, "FATT")

    @staticmethod
    def _repo():
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        return SoggettiRepository()

    # 1. `DELETE /ruoli/{id}/indirizzi/{id}/` (la view chiama il repository).
    def test_cancellare_l_unico_obbligatorio_rifiutato(self):
        self._rifiuto(lambda: self._repo().delete_indirizzo_ruolo(self.fatt, self.ruolo), _CODICE_RUOLO)

    # 2. `PATCH` che cambia il tipo: anche lui toglie l'obbligatorio.
    def test_cambiare_tipo_all_unico_obbligatorio_rifiutato(self):
        self._rifiuto(
            lambda: self._service().update_indirizzo_ruolo(
                self.ruolo, self.fatt, {"tipo_indirizzo_id": self.tipo["SPED"]},
            ),
            _CODICE_RUOLO,
        )

    # 3. Col domicilio fiscale sul ruolo vale il ripiego: la fatturazione si
    #    cancella.
    def test_col_ripiego_l_obbligatorio_si_cancella(self):
        self._service().create_indirizzo_ruolo(self.ruolo, self._indirizzo("DOMFISC"))
        self._passa(lambda: self._repo().delete_indirizzo_ruolo(self.fatt, self.ruolo))
        self.assertEqual(self._tipi_del_ruolo(self.ruolo), ["DOMFISC"])

    # 3b. `PUT /ruoli/{id}/indirizzi/{id}/` (la «modifica» del form): cancella
    #     e riscrive nel suo `transaction.atomic()`; al commit la fatturazione
    #     c'e'. Gemello del caso 5 del soggetto. Fino al 2026-11-18 il FE la
    #     faceva in due richieste, e la prima (il caso 1) era rifiutata.
    def test_sostituire_l_unico_obbligatorio_passa(self):
        self._passa(lambda: self._service().replace_indirizzo_ruolo(
            self.ruolo, self.fatt, self._indirizzo("FATT"),
        ))
        self.assertEqual(self._tipi_del_ruolo(self.ruolo), ["FATT"])
        self.assertNotEqual(self._indirizzo_del_ruolo(self.ruolo, "FATT"), self.fatt)


# Scopo: R-6 punti 2 e 3, layer SOGGETTO: la sede legale della societa'.
class IndirizziObbligatoriSoggettoDbTests(_IndirizziObbligatoriBase):
    def setUp(self) -> None:
        super().setUp()
        self._matrice("natura", "SC", "SEDELEG", True)
        self.societa = str(self._builder("SELECT dbops.fn_pgtap_crea_soggetto_pg('Obbligatori soggetto BE')"))
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id FROM anagrafiche.indirizzi_soggetti WHERE soggetto_id = %s AND tipo_indirizzo_id = %s",
                [self.societa, self.tipo["SEDELEG"]],
            )
            self.sedeleg = cur.fetchone()[0]

    # 4. `DELETE /soggetti/{id}/indirizzi/{id}/`: il codice e' del soggetto.
    def test_cancellare_la_sede_legale_rifiutato_col_codice_del_soggetto(self):
        self._rifiuto(
            lambda: self._service().delete_indirizzo_soggetto(self.societa, self.sedeleg),
            _CODICE_SOGGETTO,
        )

    # 5. `PUT` (replace): cancella e riscrive nel suo `transaction.atomic()`;
    #    al commit la sede legale c'e'.
    def test_sostituire_la_sede_legale_passa(self):
        self._passa(lambda: self._service().replace_indirizzo_soggetto(
            self.societa, self.sedeleg, self._indirizzo("SEDELEG"),
        ))


# Scopo: R-7 (e R-6 punto 3 per il PATCH): il cambio di natura porta con se'
#        gli indirizzi. Il caso del §13.2 del brief: per il fornitore la
#        consegna (SPED) e' obbligatoria, la natura PRIVATO la vieta, la DITTA
#        la ammette. Il privato fornitore che diventa ditta deve dare la
#        consegna sul ruolo, e prima del cambio non la poteva scrivere.
class CambioNaturaIndirizziDbTests(_IndirizziObbligatoriBase):
    def setUp(self) -> None:
        super().setUp()
        self._matrice("ruolo", "FO", "SPED", True)
        self._matrice("natura", "PR", "SPED", None)
        self._matrice("natura", "DI", "SPED", False)
        self.privato = str(self._builder(
            "SELECT dbops.fn_pgtap_crea_soggetto_pf('Natura', 'Fornitore', %s)", [self.natura["PR"]],
        ))
        self.fornitore = self._builder("SELECT dbops.fn_pgtap_crea_soggetto_ruolo(%s, 'FO')", [self.privato])

    def _mancanti(self, natura: str) -> list[tuple[Any, ...]]:
        esito = self._service().motivi_cambio_natura(
            self.privato, {"tipo_soggetto_dettaglio_id": self.natura[natura]},
        )
        return [
            (m["soggetto_ruolo_id"], m["tipo_indirizzo_codice_interno"], m["ripiego_tipo_indirizzo_codice_interno"])
            for m in esito["indirizzi_mancanti"]
        ]

    # La ditta vuole la partita IVA (guard immediato, prima degli indirizzi).
    def _verso_ditta(self, **chiavi: Any) -> dict[str, Any]:
        with connection.cursor() as cur:
            cur.execute("SELECT dbops.fn_pgtap_piva_libera()")
            piva = cur.fetchone()[0]
        return self._service().update_soggetto(self.privato, {
            "tipo_soggetto_dettaglio_id": self.natura["DI"], "partita_iva": piva, **chiavi,
        })

    def _rifiuto_campo(self, fn: Callable[[], Any], campo: str) -> None:
        try:
            with transaction.atomic():
                fn()
        except Exception as exc:  # la strada e' cio' che si prova
            api = ErrorTranslator.to_api_error(exc)
            self.assertEqual(api.code, "E_ANAG_VALIDAZIONE", f"{api.message} — {exc!r}")
            self.assertIn(campo, api.fields or ())
            return
        self.fail("accettato")

    # 6. La lettura del form: la consegna del fornitore, senza ripiego; sul
    #    soggetto niente (la ditta chiede il domicilio fiscale, che c'e').
    def test_motivi_elencano_l_indirizzo_che_la_natura_nuova_chiede(self):
        self.assertEqual(self._mancanti("DI"), [(self.fornitore, "SPED", None)])

    # 7. Il PATCH senza l'indirizzo: il guard lo rifiuta al COMMIT, col codice
    #    del ruolo (R-6 punto 3: non come errore tecnico).
    def test_patch_senza_l_indirizzo_rifiutato_al_commit(self):
        self._rifiuto(lambda: self._verso_ditta(), _CODICE_RUOLO)

    # 8. Con la consegna sul ruolo passa, e sulla natura nuova non manca piu'
    #    niente.
    def test_patch_con_l_indirizzo_del_ruolo_passa(self):
        self._passa(lambda: self._verso_ditta(indirizzi_ruoli=[
            {"soggetto_ruolo_id": self.fornitore, "indirizzi": [self._indirizzo("SPED")]},
        ]))
        self.assertIn("SPED", self._tipi_del_ruolo(self.fornitore))
        self.assertEqual(self._mancanti("DI"), [])

    # 9. Gli indirizzi accompagnano il cambio di natura: da soli, 400.
    def test_indirizzi_senza_la_natura_rifiutati(self):
        self._rifiuto_campo(
            lambda: self._service().update_soggetto(self.privato, {
                "cognome": "Natura", "indirizzi": [self._indirizzo("RES")],
            }),
            "indirizzi",
        )

    # 9b. La natura che il soggetto ha gia', rimandata, non e' un cambio: gli
    #     indirizzi si scrivono dal loro endpoint (che copia gli obbligatori).
    #     Fino al 2026-11-18 bastava la chiave, e il PATCH li scriveva.
    def test_indirizzi_con_la_natura_di_oggi_rifiutati(self):
        self._rifiuto_campo(
            lambda: self._service().update_soggetto(self.privato, {
                "tipo_soggetto_dettaglio_id": self.natura["PR"],
                "indirizzi_ruoli": [
                    {"soggetto_ruolo_id": self.fornitore, "indirizzi": [self._indirizzo("FATT")]},
                ],
            }),
            "indirizzi_ruoli",
        )

    # 10. Il ruolo dev'essere del soggetto: uno di un altro soggetto e' un 400.
    def test_ruolo_di_un_altro_soggetto_rifiutato(self):
        altro = self._builder(
            "SELECT dbops.fn_pgtap_crea_soggetto_pf('Natura', 'Altro', %s)", [self.natura["PR"]],
        )
        ruolo_altrui = self._builder("SELECT dbops.fn_pgtap_crea_soggetto_ruolo(%s, 'FO')", [altro])
        self._rifiuto_campo(
            lambda: self._verso_ditta(indirizzi_ruoli=[
                {"soggetto_ruolo_id": ruolo_altrui, "indirizzi": [self._indirizzo("SPED")]},
            ]),
            "indirizzi_ruoli",
        )
