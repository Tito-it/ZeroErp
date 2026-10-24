# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del service delle FAMIGLIE DI DOCUMENTO — validazione, la
#        creazione che passa dalla madre, la traduzione dei due vincoli e la
#        NON-traduzione dei codici che arrivano dai trigger.
# Note: Il repository e' mockato: qui si prova il CONTRATTO del service, non
#       l'SQL. L'SQL vero e' provato dal giro sul database (§11.10 BE-F1/F4).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) create_senza_campi_obbligatori_e_400_col_campo
 2) create_normalizza_la_colonna_serie_vuota_a_null
 2-bis) create_senza_billing_account_passa_e_arriva_null (P-9, 2026-09-14)
 3) create_passa_dalla_madre_e_riporta_i_registri_creati
 4) sorgente_inesistente_accende_codice_interno (FK verso le sorgenti, 2026-10-20)
 5) (ritirato il 2026-10-20: la tabella gia' numerata e' del guard, vedi il 7)
 6) duplicato_codice_interno_passa_dalla_mappa_generica
 7) i_codici_dei_guard_non_si_traducono_qui
 8) get_famiglia_inesistente_e_404
 9) set_attivo_legge_una_volta_sola
10) update_su_famiglia_inesistente_e_404
11) update_codice_arriva_al_repository
12) update_codice_vuoto_e_400_col_campo
13) duplicato_codice_in_modifica_accende_codice
14) duplicato_codice_in_creazione_accende_codice_interno
15) codice_in_creazione_rifiutato
15-bis) attivo_in_modifica_rifiutato
15-ter) schema_e_tabella_in_creazione_rifiutati (2026-10-20)
"""

from unittest import TestCase
from unittest.mock import patch

from django.db import IntegrityError, ProgrammingError

from apps.core.services.service_errors import ServiceError
from apps.vendite.db.famiglie_repository import FamiglieDocumentoRepository
from apps.vendite.services.famiglie_service import FamiglieDocumentoService

_REPO = FamiglieDocumentoRepository


# Scopo: un IntegrityError che *nomina* un vincolo, come lo consegna psycopg.
# ⚠️ `vincolo_violato` legge il TESTO dell'eccezione: senza il nome dentro,
#    nessuna voce della mappa fa match.
def _integrity(nome_vincolo: str) -> IntegrityError:
    return IntegrityError(
        f'duplicate key value violates unique constraint "{nome_vincolo}"\n'
        f"DETAIL:  Key (codice_interno)=(PARCELLA) already exists.",
    )


# Scopo: una famiglia finta come la restituisce la vista, per le riletture.
def _famiglia(**over):
    base = {
        "id": 3, "codice_interno": "FATTURA", "descrizione": "Fatture",
        "schema_tabella": "vendite", "nome_tabella": "fatture",
        "tabella_documento": "vendite.fatture",
        "colonna_numero": "numero", "colonna_serie": "serie",
        "colonna_billing_account": "billing_account_id",
        "gestisce_serie": True, "presidia_data_documento": True,
        "prefisso_default": None, "lunghezza_default": 7,
        "n_registri": 2, "n_registri_attivi": 2, "attivo": True,
        "can_disattivare": False, "can_modificare_struttura": False,
    }
    base.update(over)
    return base


# ⭐ Dal 2026-10-20 (brief-db-grammatica-unica-documenti 2c, G-5) la famiglia e'
#    quella di una SORGENTE: `codice_interno` e' il suo codice, e schema e
#    tabella non si passano piu' (la tabella e' la `target_table`).
_CREATE_MINIMO = {
    "codice_interno": "PARCELLA",
    "descrizione": "Parcelle",
    "colonna_numero": "numero",
}


class FamiglieValidazioneTests(TestCase):
    # 1. Il campo mancante si NOMINA: senza, l'operatore legge «obbligatorio» e
    #    deve indovinare quale dei tre (erano sei fino al 2026-09-14, quando il
    #    billing account e' uscito con la P-9; cinque fino al 2026-10-20, quando
    #    schema e tabella sono passati alla sorgente).
    def test_create_senza_campi_obbligatori_e_400_col_campo(self):
        for campo in _CREATE_MINIMO:
            payload = {k: v for k, v in _CREATE_MINIMO.items() if k != campo}
            with self.subTest(campo=campo), self.assertRaises(ServiceError) as ctx:
                FamiglieDocumentoService().crea_famiglia(payload)
            self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
            self.assertEqual(ctx.exception.context.get("field"), campo)

    # 2. ⛔ La stringa vuota NON e' una colonna serie. `NULL` significa «questa
    #    famiglia non gestisce le serie» ed e' cio' che legge
    #    `fn_check_registro_serie_ammessa`; un `''` la farebbe risultare
    #    dichiarata, e il guard dei riferimenti la cercherebbe sul documento.
    @patch.object(_REPO, "get_famiglia", return_value=_famiglia())
    @patch.object(_REPO, "crea_famiglia")
    def test_create_normalizza_la_colonna_serie_vuota_a_null(self, mock_crea, _get):
        mock_crea.return_value = {
            "famiglia_id": 3, "codice_interno": "PARCELLA", "registri_creati": 0,
        }
        FamiglieDocumentoService().crea_famiglia(
            {**_CREATE_MINIMO, "colonna_serie": "   "},
        )
        self.assertIsNone(mock_crea.call_args.args[0]["colonna_serie"])

    # 2-bis. ⭐ IL BILLING ACCOUNT NON E' PIU' OBBLIGATORIO (P-9, 2026-09-14):
    #    `NULL` = «questa famiglia non ha un billing account», ed e' la forma
    #    dell'ordine di acquisto (controparte = soggetto_ruolo). Vuoto o
    #    assente, alla madre arriva NULL — la stessa disciplina di
    #    `colonna_serie`, e per la stessa ragione: un `''` la farebbe risultare
    #    una colonna DICHIARATA, e il guard dei riferimenti la cercherebbe.
    @patch.object(_REPO, "get_famiglia", return_value=_famiglia(colonna_billing_account=None))
    @patch.object(_REPO, "crea_famiglia")
    def test_create_senza_billing_account_passa_e_arriva_null(self, mock_crea, _get):
        mock_crea.return_value = {
            "famiglia_id": 3, "codice_interno": "PARCELLA", "registri_creati": 0,
        }
        for payload in (
            dict(_CREATE_MINIMO),
            {**_CREATE_MINIMO, "colonna_billing_account": ""},
            {**_CREATE_MINIMO, "colonna_billing_account": "   "},
        ):
            with self.subTest(payload=payload):
                FamiglieDocumentoService().crea_famiglia(payload)
                self.assertIsNone(
                    mock_crea.call_args.args[0].get("colonna_billing_account"),
                )

    # 3. ⭐ `registri_creati` e' meta' del lavoro che la creazione ha fatto: la
    #    madre scrive la famiglia E le provvede i registri, e la maschera deve
    #    poterlo dire.
    @patch.object(_REPO, "get_famiglia", return_value=_famiglia())
    @patch.object(_REPO, "crea_famiglia")
    def test_create_passa_dalla_madre_e_riporta_i_registri_creati(self, mock_crea, _g):
        mock_crea.return_value = {
            "famiglia_id": 3, "codice_interno": "PARCELLA", "registri_creati": 4,
        }
        esito = FamiglieDocumentoService().crea_famiglia(dict(_CREATE_MINIMO))
        self.assertEqual(esito["registri_creati"], 4)
        self.assertEqual(mock_crea.call_count, 1)


class FamiglieVincoliTests(TestCase):
    # 4. ⭐ La famiglia e' quella di una SORGENTE: un codice che in
    #    `config.sorgenti` non c'e' viola `fk_famiglie_documento_sorgenti`, e si
    #    dice che cosa manca accendendo `codice_interno`. Il ramo e' vivo sulle
    #    famiglie create spente, dove il guard dei riferimenti non guarda
    #    (provato su dbdev il 2026-10-20).
    @patch.object(_REPO, "crea_famiglia", side_effect=IntegrityError(
        'insert or update on table "famiglie_documento" violates foreign key '
        'constraint "fk_famiglie_documento_sorgenti"',
    ))
    def test_sorgente_inesistente_accende_codice_interno(self, _crea):
        with self.assertRaises(ServiceError) as ctx:
            FamiglieDocumentoService().crea_famiglia(
                {**_CREATE_MINIMO, "attivo": False},
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(ctx.exception.context.get("field"), "codice_interno")
        self.assertIn("sorgente", ctx.exception.message)

    # 6. L'altro UNIQUE passa dalla mappa generica e accende `codice_interno`.
    @patch.object(_REPO, "crea_famiglia",
                  side_effect=_integrity("uq_famiglie_documento_codice_interno"))
    def test_duplicato_codice_interno_passa_dalla_mappa_generica(self, _crea):
        with self.assertRaises(ServiceError) as ctx:
            FamiglieDocumentoService().crea_famiglia(dict(_CREATE_MINIMO))
        self.assertEqual(ctx.exception.code, "E_VENDITE_DUPLICATO")
        self.assertEqual(ctx.exception.context.get("field"), "codice_interno")

    # 7. ⛔ I QUATTRO CODICI DEI GUARD NON SI TRADUCONO QUI, ed e' la voce BE-F3
    #    (il quarto, `..._TABELLA_GIA_NUMERATA`, dal 2026-10-20: era l'indice
    #    `uq_famiglie_documento_tabella_attiva`, tradotto qui).
    #    Arrivano come **P0001** — li solleva `fn_log_and_raise_error` dentro un
    #    trigger — quindi non sono `IntegrityError` e devono risalire intatti al
    #    middleware, che legge il codice strutturato dall'eccezione. Tradurli qui
    #    vorrebbe dire riscrivere il messaggio del database accanto al suo.
    def test_i_codici_dei_guard_non_si_traducono_qui(self):
        for testo in (
            "La famiglia di documento PARCELLA dichiara un riferimento che non "
            "esiste: vendite.parcelle. E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE",
            "La famiglia PARCELLA numererebbe la tabella vendite.fatture, che e' "
            "gia' numerata dalla famiglia attiva FATTURA. "
            "E_FAMIGLIA_DOCUMENTO_TABELLA_GIA_NUMERATA",
        ):
            with self.subTest(testo=testo[-45:]), patch.object(
                _REPO, "crea_famiglia", side_effect=ProgrammingError(testo),
            ), self.assertRaises(ProgrammingError):
                FamiglieDocumentoService().crea_famiglia(dict(_CREATE_MINIMO))


class FamiglieLetturaEVerbiTests(TestCase):
    # 8.
    @patch.object(_REPO, "get_famiglia", return_value=None)
    def test_get_famiglia_inesistente_e_404(self, _get):
        with self.assertRaises(ServiceError) as ctx:
            FamiglieDocumentoService().get_famiglia(99)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    # 9. Si scrive prima e si rilegge una volta sola: «zero righe» ha due cause
    #    (non esiste / gia' in quello stato) e la rilettura le separa da sola.
    @patch.object(_REPO, "get_famiglia", return_value=_famiglia(attivo=False))
    @patch.object(_REPO, "set_attivo", return_value=1)
    def test_set_attivo_legge_una_volta_sola(self, mock_set, mock_get):
        FamiglieDocumentoService().set_attivo(3, False)
        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(mock_set.call_count, 1)

    # 10. `toccate == 0` non e' un errore da solo: a distinguere «non esiste» da
    #     «payload senza colonne scrivibili» e' la rilettura.
    @patch.object(_REPO, "get_famiglia", return_value=None)
    @patch.object(_REPO, "update_famiglia", return_value=0)
    def test_update_su_famiglia_inesistente_e_404(self, _upd, _get):
        with self.assertRaises(ServiceError) as ctx:
            FamiglieDocumentoService().update_famiglia(99, {"descrizione": "x"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")


class FamiglieCodiceTests(TestCase):
    """Il `codice` dell'operatore (2026-09-24): mutabile dal CRUD, unico."""

    # 11.
    @patch.object(_REPO, "get_famiglia", return_value=_famiglia(codice="FT"))
    @patch.object(_REPO, "update_famiglia", return_value=1)
    def test_update_codice_arriva_al_repository(self, mock_upd, _get):
        FamiglieDocumentoService().update_famiglia(3, {"codice": "FT"})
        self.assertEqual(mock_upd.call_args.args[1], {"codice": "FT"})

    # 12. Si cambia, non si svuota: col campo acceso, non un vincolo generico.
    @patch.object(_REPO, "update_famiglia")
    def test_update_codice_vuoto_e_400_col_campo(self, mock_upd):
        with self.assertRaises(ServiceError) as ctx:
            FamiglieDocumentoService().update_famiglia(3, {"codice": "  "})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(ctx.exception.context.get("field"), "codice")
        mock_upd.assert_not_called()

    # 13.
    @patch.object(_REPO, "update_famiglia",
                  side_effect=_integrity("uq_famiglie_documento_codice"))
    def test_duplicato_codice_in_modifica_accende_codice(self, _upd):
        with self.assertRaises(ServiceError) as ctx:
            FamiglieDocumentoService().update_famiglia(3, {"codice": "FT"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_DUPLICATO")
        self.assertEqual(ctx.exception.context.get("field"), "codice")

    # 14. ⚠️ In creazione il codice nasce dal `codice_interno` (trigger): il
    #     campo da correggere e' quello, e non va confuso col vincolo del
    #     `codice_interno` (il nome del primo e' prefisso del secondo).
    @patch.object(_REPO, "crea_famiglia",
                  side_effect=_integrity("uq_famiglie_documento_codice"))
    def test_duplicato_codice_in_creazione_accende_codice_interno(self, _crea):
        with self.assertRaises(ServiceError) as ctx:
            FamiglieDocumentoService().crea_famiglia(dict(_CREATE_MINIMO))
        self.assertEqual(ctx.exception.code, "E_VENDITE_DUPLICATO")
        self.assertEqual(ctx.exception.context.get("field"), "codice_interno")
        self.assertIn("codice di un'altra", ctx.exception.message)

    # 15. ⛔ Un client che in creazione manda anche `codice` (non e' in
    #     `_CAMPI_CREATE`: alla nascita lo copia il trigger) e' RIFIUTATO con
    #     400, prima del database (2026-09-26). Fino a quel giorno il repository
    #     lo scartava in silenzio, e questo test verificava solo che l'errore di
    #     duplicato non finisse sul campo ignorato.
    @patch.object(_REPO, "crea_famiglia")
    def test_codice_in_creazione_rifiutato(self, crea):
        with self.assertRaises(ServiceError) as ctx:
            FamiglieDocumentoService().crea_famiglia({**_CREATE_MINIMO, "codice": "FT"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(ctx.exception.context.get("unknown_keys"), ["codice"])
        crea.assert_not_called()

    # 15-bis. ⛔ Stessa regola in modifica: `attivo` ha il suo verbo, e spedito
    #     nel PATCH e' un 400 — non un «salvato» senza aver scritto niente.
    @patch.object(_REPO, "update_famiglia")
    def test_attivo_in_modifica_rifiutato(self, update):
        with self.assertRaises(ServiceError) as ctx:
            FamiglieDocumentoService().update_famiglia(3, {"descrizione": "X", "attivo": False})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(ctx.exception.context.get("unknown_keys"), ["attivo"])
        update.assert_not_called()

    # 15-ter. ⛔ Il contratto di prima (schema e tabella) e' un 400 parlante, non
    #     una madre chiamata con parametri che non ha piu': dal 2026-10-20 la
    #     tabella la dice la sorgente (brief-db-grammatica-unica-documenti 2c).
    @patch.object(_REPO, "crea_famiglia")
    def test_schema_e_tabella_in_creazione_rifiutati(self, crea):
        with self.assertRaises(ServiceError) as ctx:
            FamiglieDocumentoService().crea_famiglia(
                {**_CREATE_MINIMO, "schema_tabella": "vendite", "nome_tabella": "parcelle"},
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(
            sorted(ctx.exception.context.get("unknown_keys")),
            ["nome_tabella", "schema_tabella"],
        )
        crea.assert_not_called()
