# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit ListaExportService (DEF-1).
#        Renderer puro (no DB): verifica filtri colonne, hard cap,
#        formati, BOM, foglio filtri, format invalido.
#
# Indice test (0..N):
#   0. format_invalido_raises_400
#   1. cap_righe_supera_max_raises_422
#   2. csv_filtra_colonne_azione_e_non_esportabili
#   3. csv_ordina_per_ordine_default
#   4. csv_include_header_filtri_serializzato
#   5. csv_include_bom_utf8
#   6. csv_format_bool_si_no_italiano
#   7. csv_none_diventa_stringa_vuota
#   8. xlsx_due_fogli_dati_e_filtri
#   9. xlsx_foglio_filtri_vuoto_quando_no_filtri
#  10. xlsx_filename_safe_replace_punto_due_punti
#  11. xlsx_zero_righe_genera_file_valido
# ------------------------------------------------------------

from __future__ import annotations

import csv
import io

from django.test import SimpleTestCase
from openpyxl import load_workbook

from apps.core.services.service_errors import ServiceError
from apps.ui.services.lista_export_service import (
    EXPORT_MAX_ROWS,
    ListaExportService,
)


def _colonne_clienti() -> list[dict]:
    return [
        {
            "codice": "ragione_sociale", "etichetta": "Ragione sociale",
            "campo_sorgente": "ragione_sociale_completa",
            "tipo_colonna": "identificatore", "tipo_dato": "string",
            "esportabile": True, "ordine_default": 10,
        },
        {
            "codice": "partita_iva", "etichetta": "Partita IVA",
            "campo_sorgente": "partita_iva",
            "tipo_colonna": "informazione", "tipo_dato": "string",
            "esportabile": True, "ordine_default": 20,
        },
        {
            "codice": "stato", "etichetta": "Stato",
            "campo_sorgente": "stato_descrizione",
            "tipo_colonna": "informazione", "tipo_dato": "string",
            "esportabile": True, "ordine_default": 30,
        },
        {
            "codice": "azioni", "etichetta": "Azioni",
            "campo_sorgente": None,
            "tipo_colonna": "azione", "tipo_dato": "string",
            "esportabile": False, "ordine_default": 99,
        },
        {
            "codice": "secret", "etichetta": "Riservato",
            "campo_sorgente": "campo_segreto",
            "tipo_colonna": "informazione", "tipo_dato": "string",
            "esportabile": False, "ordine_default": 50,
        },
    ]


def _righe_clienti() -> list[dict]:
    return [
        {
            "ragione_sociale_completa": "Acme S.p.A.",
            "partita_iva": "12345678901",
            "stato_descrizione": "ATTIVO",
            "campo_segreto": "non-esportabile",
        },
        {
            "ragione_sociale_completa": "Beta Srl",
            "partita_iva": None,
            "stato_descrizione": "SOSPESO",
            "campo_segreto": "x",
        },
    ]


# ============================================================
# Validazione + cap
# ============================================================

class ExportValidationTests(SimpleTestCase):
    def test_format_invalido_raises_400(self) -> None:
        svc = ListaExportService()
        with self.assertRaises(ServiceError) as ctx:
            svc.render(
                lista_codice="anagrafiche.clienti",
                colonne=_colonne_clienti(),
                righe=[],
                filtri_applicati={},
                formato="pdf",
            )
        self.assertEqual(ctx.exception.code, "E_UI_EXPORT_FORMAT_INVALID")

    def test_cap_righe_supera_max_raises_422(self) -> None:
        svc = ListaExportService()
        # genera EXPORT_MAX_ROWS + 1 righe minime per bypassare il cap
        too_many = [{"ragione_sociale_completa": f"r{i}"} for i in range(EXPORT_MAX_ROWS + 1)]
        with self.assertRaises(ServiceError) as ctx:
            svc.render(
                lista_codice="anagrafiche.clienti",
                colonne=_colonne_clienti(),
                righe=too_many,
                filtri_applicati={},
                formato="csv",
            )
        self.assertEqual(ctx.exception.code, "E_UI_EXPORT_LIMIT_EXCEEDED")


# ============================================================
# CSV
# ============================================================

class ExportCsvTests(SimpleTestCase):
    def _render_and_parse(self, righe, filtri=None):
        body, ct, fn = ListaExportService().render(
            lista_codice="anagrafiche.clienti",
            colonne=_colonne_clienti(),
            righe=righe,
            filtri_applicati=filtri or {},
            formato="csv",
        )
        # Verifica BOM e content-type prima del parse
        self.assertTrue(body.startswith(b"\xef\xbb\xbf"))
        self.assertIn("text/csv", ct)
        self.assertTrue(fn.startswith("anagrafiche_clienti_"))
        self.assertTrue(fn.endswith(".csv"))
        text = body[3:].decode("utf-8")  # strip BOM
        return text, csv.reader(io.StringIO(text))

    def test_csv_filtra_colonne_azione_e_non_esportabili(self) -> None:
        text, _reader = self._render_and_parse(_righe_clienti())
        # `Azioni` (tipo_colonna=azione) e `Riservato` (esportabile=false)
        # NON devono apparire come header.
        self.assertNotIn("Azioni", text)
        self.assertNotIn("Riservato", text)
        # Le 3 colonne legittime sono presenti.
        self.assertIn("Ragione sociale", text)
        self.assertIn("Partita IVA", text)
        self.assertIn("Stato", text)

    def test_csv_ordina_per_ordine_default(self) -> None:
        # Inverto l'ordine di input per assicurarmi che il sort funzioni.
        cols = list(reversed(_colonne_clienti()))
        body, _, _ = ListaExportService().render(
            lista_codice="anagrafiche.clienti",
            colonne=cols,
            righe=_righe_clienti(),
            filtri_applicati={},
            formato="csv",
        )
        text = body[3:].decode("utf-8")
        header_line = text.split("\n")[1]
        # Header deve essere Ragione sociale, Partita IVA, Stato (ordine 10,20,30)
        self.assertEqual(header_line.strip(), "Ragione sociale,Partita IVA,Stato")

    def test_csv_include_header_filtri_serializzato(self) -> None:
        text, _ = self._render_and_parse(
            [], filtri={"utility_id": 3, "stato": "ATTIVO"},
        )
        first_line = text.split("\n")[0]
        self.assertTrue(first_line.startswith("# Filtri applicati:"))
        # JSON sortato per determinismo.
        self.assertIn('"stato": "ATTIVO"', first_line)
        self.assertIn('"utility_id": 3', first_line)

    def test_csv_include_bom_utf8(self) -> None:
        body, _, _ = ListaExportService().render(
            lista_codice="anagrafiche.clienti",
            colonne=_colonne_clienti(),
            righe=[{"ragione_sociale_completa": "Caffè à la Sicilienne"}],
            filtri_applicati={},
            formato="csv",
        )
        # BOM presente per Excel-friendly
        self.assertTrue(body.startswith(b"\xef\xbb\xbf"))
        # Accenti UTF-8 preservati
        self.assertIn("Caffè à la Sicilienne".encode("utf-8"), body)

    def test_csv_format_bool_si_no_italiano(self) -> None:
        cols = [{
            "codice": "flag", "etichetta": "Attivo",
            "campo_sorgente": "is_active",
            "tipo_colonna": "informazione", "tipo_dato": "boolean",
            "esportabile": True, "ordine_default": 1,
        }]
        body, _, _ = ListaExportService().render(
            lista_codice="x.y", colonne=cols,
            righe=[{"is_active": True}, {"is_active": False}],
            filtri_applicati={}, formato="csv",
        )
        text = body[3:].decode("utf-8")
        self.assertIn("Si", text)
        self.assertIn("No", text)

    def test_csv_none_diventa_stringa_vuota(self) -> None:
        text, _ = self._render_and_parse([
            {"ragione_sociale_completa": "Beta", "partita_iva": None, "stato_descrizione": "X"},
        ])
        # La cella partita_iva e' vuota tra due virgole.
        self.assertIn("Beta,,X", text)

    def test_csv_date_formato_italiano_dd_mm_yyyy(self) -> None:
        # DEF-1: le date devono uscire in formato DD-MM-YYYY (italiano)
        # via il dispatcher centralizzato `locale_formatters`. Il caller
        # passa il `tipo_dato='date'` nel catalogo colonne.
        from datetime import date
        cols = [{
            "codice": "data_attivazione",
            "etichetta": "Data attivazione",
            "campo_sorgente": "data_att",
            "tipo_colonna": "informazione",
            "tipo_dato": "date",
            "esportabile": True,
            "ordine_default": 1,
        }]
        body, _, _ = ListaExportService().render(
            lista_codice="x.y", colonne=cols,
            righe=[{"data_att": date(2026, 5, 10)}, {"data_att": None}],
            filtri_applicati={}, formato="csv",
        )
        text = body[3:].decode("utf-8")
        self.assertIn("10-05-2026", text)
        # NON deve apparire il formato ISO predefinito di str(date).
        self.assertNotIn("2026-05-10", text)


# ============================================================
# XLSX
# ============================================================

class ExportXlsxTests(SimpleTestCase):
    def _render_and_load(self, righe, filtri=None):
        body, ct, fn = ListaExportService().render(
            lista_codice="anagrafiche.clienti",
            colonne=_colonne_clienti(),
            righe=righe,
            filtri_applicati=filtri or {},
            formato="xlsx",
        )
        self.assertIn("spreadsheetml", ct)
        self.assertTrue(fn.endswith(".xlsx"))
        wb = load_workbook(io.BytesIO(body))
        return wb, fn

    def test_xlsx_due_fogli_dati_e_filtri(self) -> None:
        wb, _ = self._render_and_load(
            _righe_clienti(),
            filtri={"utility_id": 3},
        )
        self.assertEqual(wb.sheetnames, ["Dati", "Filtri applicati"])
        ws_dati = wb["Dati"]
        # 1 header + 2 righe dati = 3
        self.assertEqual(ws_dati.max_row, 3)
        # Header bold
        self.assertTrue(ws_dati.cell(row=1, column=1).font.bold)
        # Foglio filtri ha header + 1 riga filtro
        ws_filtri = wb["Filtri applicati"]
        self.assertEqual(ws_filtri.cell(row=2, column=1).value, "utility_id")
        self.assertEqual(ws_filtri.cell(row=2, column=2).value, 3)

    def test_xlsx_foglio_filtri_vuoto_quando_no_filtri(self) -> None:
        wb, _ = self._render_and_load([], filtri={})
        ws_filtri = wb["Filtri applicati"]
        # Header + riga "(nessun filtro applicato)"
        self.assertEqual(ws_filtri.max_row, 2)
        self.assertIn("nessun filtro", str(ws_filtri.cell(row=2, column=1).value))

    def test_xlsx_filename_safe_replace_punto_due_punti(self) -> None:
        # Lista con suffisso variante (`:picker`) -> filename safe.
        body, ct, fn = ListaExportService().render(
            lista_codice="catalogo.articoli:picker",
            colonne=_colonne_clienti(),
            righe=[],
            filtri_applicati={},
            formato="xlsx",
        )
        self.assertTrue(fn.startswith("catalogo_articoli_picker_"))
        # Niente punti/due punti nel filename (oltre l'estensione).
        stem = fn.rsplit(".", 1)[0]
        self.assertNotIn(".", stem)
        self.assertNotIn(":", stem)

    def test_xlsx_zero_righe_genera_file_valido(self) -> None:
        wb, _ = self._render_and_load([])
        ws = wb["Dati"]
        # Solo header.
        self.assertEqual(ws.max_row, 1)
        self.assertEqual(ws.cell(row=1, column=1).value, "Ragione sociale")


# ============================================================
# Helper select_colonne_visibili_da_config
# ============================================================

class SelectColonneVisibiliTests(SimpleTestCase):
    """Verifica che l'export rispetti la preferenza utente: ordine,
    visibilita', filtro permessi (gia' applicato dalla fn DB)."""

    def _metadata_full(self) -> list[dict]:
        return _colonne_clienti()  # 5 colonne con tipo_colonna/etichetta/...

    def test_ordine_utente_prevale_su_ordine_default(self) -> None:
        # Utente ha invertito l'ordine: stato prima, partita_iva dopo.
        config = {
            "colonne": [
                {"codice": "stato", "visibile": True, "ordine": 1},
                {"codice": "ragione_sociale", "visibile": True, "ordine": 2},
                {"codice": "partita_iva", "visibile": True, "ordine": 3},
            ],
        }
        result = ListaExportService.select_colonne_visibili_da_config(
            config, self._metadata_full(),
        )
        self.assertEqual([c["codice"] for c in result], ["stato", "ragione_sociale", "partita_iva"])
        # `ordine_default` sovrascritto con posizione progressiva 0,1,2.
        self.assertEqual([c["ordine_default"] for c in result], [0, 1, 2])

    def test_colonne_nascoste_dall_utente_sono_escluse(self) -> None:
        # Utente ha nascosto partita_iva e stato (visibile=false).
        config = {
            "colonne": [
                {"codice": "ragione_sociale", "visibile": True},
                {"codice": "partita_iva", "visibile": False},
                {"codice": "stato", "visibile": False},
            ],
        }
        result = ListaExportService.select_colonne_visibili_da_config(
            config, self._metadata_full(),
        )
        self.assertEqual([c["codice"] for c in result], ["ragione_sociale"])

    def test_colonne_assenti_dal_catalogo_skip_silenzioso(self) -> None:
        # Edge case: config ha una colonna obsoleta che non e' piu' nel
        # catalogo (es. cancellata via admin). Skip senza errore.
        config = {
            "colonne": [
                {"codice": "ragione_sociale", "visibile": True},
                {"codice": "colonna_fantasma", "visibile": True},
            ],
        }
        result = ListaExportService.select_colonne_visibili_da_config(
            config, self._metadata_full(),
        )
        self.assertEqual([c["codice"] for c in result], ["ragione_sociale"])

    def test_colonne_bloccate_gia_filtrate_dal_BE(self) -> None:
        # I permessi BLOCCATO sono filtrati upstream da `fn_resolve_lista_config`.
        # Qui simuliamo il caso: la colonna BLOCCATA non e' in config.colonne
        # nemmeno se e' nel catalogo. L'export non la include.
        config = {
            "colonne": [
                {"codice": "ragione_sociale", "visibile": True},
                # `partita_iva` non c'e': filtrata dal BE per profilo Tecnico.
            ],
        }
        result = ListaExportService.select_colonne_visibili_da_config(
            config, self._metadata_full(),
        )
        self.assertEqual([c["codice"] for c in result], ["ragione_sociale"])
        # Nemmeno se la passiamo a render: solo ragione_sociale nell'output.

    def test_visibile_default_true_quando_flag_assente(self) -> None:
        # Alcuni preset di sistema non dichiarano esplicitamente `visibile`:
        # interpretiamo come True (mostra/esporta). Solo `visibile: false`
        # esplicito esclude.
        config = {
            "colonne": [
                {"codice": "ragione_sociale"},  # no flag visibile
                {"codice": "partita_iva", "visibile": True},
                {"codice": "stato", "visibile": False},
            ],
        }
        result = ListaExportService.select_colonne_visibili_da_config(
            config, self._metadata_full(),
        )
        self.assertEqual([c["codice"] for c in result], ["ragione_sociale", "partita_iva"])
