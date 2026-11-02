# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Renderer generico per export liste configurabili (DEF-1).
#        Riceve righe + config colonne + filtri applicati e produce
#        bytes CSV o XLSX. Non esegue query: il dominio (clienti,
#        contratti, ecc.) usa il proprio repository per ottenere le
#        righe e poi delega a questo renderer per la serializzazione.
#
#        Vantaggi del design "renderer no-fetch":
#          - zero SQL dinamico (no rischio injection sulla `vista_sql`)
#          - riuso massimo: ogni dominio adotta il pattern in DEF-8
#            estendendo solo il proprio endpoint con `?formato=csv|xlsx`
#          - sicurezza: le whitelist colonne/filtri sono garantite dai
#            repository di dominio gia' esistenti
#
#        Filtri colonne applicati dal renderer:
#          - escluse `tipo_colonna='azione'` (pulsanti UI, non dato)
#          - escluse `esportabile=false` (decisione admin)
#          - identificatore + informazione esportate
#          - rispetto ordine `ordine_default` o ordine fornito dal caller
#
#        Hard cap righe (decisione 3 _def.md): 10.000.
#        Sopra il cap, il caller solleva E_UI_EXPORT_LIMIT_EXCEEDED.
#
#        Filtri leggibili (decisione 4 _def.md): in v1 il dict filtri
#        viene serializzato come JSON nell'header CSV (riga commentata
#        prefissata `#`) o nel foglio "Filtri applicati" del XLSX.
#        Il dispatcher per tipo (es. stato_id=3 -> "ATTIVO") e' rinviato.
# ------------------------------------------------------------

from __future__ import annotations

import csv
import io
import json
from django.utils import timezone
from collections.abc import Mapping, Sequence
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font

from apps.core.services.locale_formatters import in_ora_locale
from apps.core.services.error_manager import ErrorManager
from apps.core.services.locale_formatters import format_for_export

E_EXPORT_LIMIT_EXCEEDED = "E_UI_EXPORT_LIMIT_EXCEEDED"
E_EXPORT_FORMAT_INVALID = "E_UI_EXPORT_FORMAT_INVALID"

# Hard cap righe export sincrono (decisione 3 _def.md). Sopra questo
# limite il service rifiuta con messaggio "raffinare i filtri". L'export
# asincrono via job e' rinviato a DEF separato se emerge esigenza.
EXPORT_MAX_ROWS = 10_000

_FORMATS_AMMESSI: frozenset[str] = frozenset({"csv", "xlsx"})


class ListaExportService:
    """Renderer per generare CSV/XLSX da righe + config colonne."""

    # Scopo: Genera il file di export.
    #        Argomenti:
    #          - lista_codice: codice della lista (es. 'anagrafiche.clienti'),
    #            usato solo per il filename
    #          - colonne: lista dict colonne (output di
    #            UiRepository.list_colonne_by_codice). Devono includere
    #            `codice`, `etichetta`, `campo_sorgente`, `tipo_colonna`,
    #            `esportabile`, `ordine_default`. Eventuali campi extra
    #            sono ignorati.
    #          - righe: lista dict (output del repository del dominio).
    #            Le chiavi devono coincidere con `colonne[i].campo_sorgente`.
    #          - filtri_applicati: dict generico filtri usati dal caller.
    #            Verra' incluso nel file come metadato. Pass {} se nessuno.
    #          - formato: 'csv' | 'xlsx'.
    #
    #        Ritorna: tuple (bytes, content_type, filename).
    def render(
        self,
        *,
        lista_codice: str,
        colonne: list[dict[str, Any]],
        righe: Sequence[Mapping[str, Any]],
        filtri_applicati: dict[str, Any] | None,
        formato: str,
    ) -> tuple[bytes, str, str]:
        # Validazione formato lato service (defense-in-depth oltre alla
        # view che gia' filtra il query param).
        ErrorManager.require(
            formato in _FORMATS_AMMESSI,
            code=E_EXPORT_FORMAT_INVALID,
            message="Formato export non supportato.",
            detail=f"formato='{formato}', ammessi={sorted(_FORMATS_AMMESSI)!r}",
        )

        # Hard cap righe applicato qui (single source of truth): se il
        # caller ha gia' applicato un cap diverso, prevale il piu'
        # restrittivo.
        ErrorManager.require(
            len(righe) <= EXPORT_MAX_ROWS,
            code=E_EXPORT_LIMIT_EXCEEDED,
            message="Export oltre il limite consentito.",
            detail=(
                f"righe={len(righe)}, max={EXPORT_MAX_ROWS}. "
                "Raffinare i filtri."
            ),
            context={"rows": len(righe), "limit": EXPORT_MAX_ROWS},
        )

        colonne_export = self._filter_colonne_esportabili(colonne)
        filtri = filtri_applicati or {}
        # ⚠️ Ora DELL'AZIENDA, non dell'host ne' del processo: il nome del file
        #    deve dire la stessa ora delle celle che contiene (2026-09-14), e
        #    la stessa sede la converte (`in_ora_locale`).
        timestamp = in_ora_locale(timezone.now()).strftime("%Y%m%d-%H%M%S")
        # Filename safe: caratteri speciali del codice rimpiazzati con `_`.
        # Pattern es. `anagrafiche.clienti` -> `anagrafiche_clienti`.
        safe_codice = lista_codice.replace(".", "_").replace(":", "_")
        filename_base = f"{safe_codice}_{timestamp}"

        if formato == "csv":
            body = self._render_csv(colonne_export, righe, filtri)
            return (
                body,
                "text/csv; charset=utf-8",
                f"{filename_base}.csv",
            )

        # formato == "xlsx" (validato sopra)
        body = self._render_xlsx(colonne_export, righe, filtri)
        return (
            body,
            (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            f"{filename_base}.xlsx",
        )

    # =================================================================
    # Helper pubblico — combinare config runtime utente con catalogo
    # =================================================================

    # Scopo: Costruisce la lista colonne export rispettando la
    #        configurazione runtime dell'utente (preferenza personale,
    #        preset di base, permessi colonna) anziche' usare il
    #        catalogo grezzo. L'export riflette ESATTAMENTE quello che
    #        l'utente vede nella DataTable: colonne nascoste -> escluse,
    #        ordine personalizzato -> rispettato.
    #
    #        Argomenti:
    #          - config: output di `UiService.get_lista_config(user, codice)`.
    #            Contiene `colonne` (lista in ordine FE con flag
    #            `visibile`, post-filtri permessi e BLOCCATE rimosse
    #            dalla fn DB).
    #          - metadata: output di `UiRepository.list_colonne_by_codice(codice)`.
    #            Contiene i metadati ricchi del catalogo (etichetta,
    #            tipo_dato, formato, esportabile, tipo_colonna).
    #
    #        Combinazione:
    #          1. Itera `config.colonne` nell'ordine fornito (ordine utente).
    #          2. Skip se `visibile=false` (colonna nascosta a video).
    #          3. Merge con `metadata` per recuperare etichetta + tipo_*.
    #          4. Sovrascrive `ordine_default` con la posizione progressiva
    #             cosi' il renderer (che sorta per quel campo) preserva
    #             l'ordine utente.
    #
    #        I filtri export `tipo_colonna='azione'` e
    #        `esportabile=false` sono applicati DOPO da `render()` —
    #        rimangono regole di sistema indipendenti dalla preferenza
    #        utente (un admin puo' aver marcato esportabile=false su
    #        una colonna che l'utente vede comunque a video).
    @staticmethod
    def select_colonne_visibili_da_config(
        config: dict[str, Any],
        metadata: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        config_colonne = config.get("colonne") or []
        meta_by_code = {m["codice"]: m for m in metadata}
        out: list[dict[str, Any]] = []
        for idx, c in enumerate(config_colonne):
            codice = c.get("codice")
            if not codice:
                continue
            # Colonna nascosta dall'utente nella DataTable -> skip export.
            # Default `True` se il flag manca (alcuni preset di sistema
            # non lo dichiarano esplicitamente).
            if c.get("visibile") is False:
                continue
            m = meta_by_code.get(codice)
            if not m:
                # Colonna in config ma non nel catalogo: edge case raro
                # (drift catalogo/preferenza dopo cancellazione colonna).
                # Skip silenzioso per coerenza con render FE.
                continue
            merged = dict(m)
            merged["ordine_default"] = idx
            out.append(merged)
        return out

    # =================================================================
    # Helpers privati
    # =================================================================

    # Scopo: Filtra le colonne ammissibili all'export. Esclude
    #        `tipo_colonna='azione'` (pulsanti UI) e `esportabile=false`
    #        (decisione admin). Ordina per `ordine_default` per coerenza
    #        col display lista. Tiene anche colonne con
    #        `campo_sorgente=None`: il rendering produrra' celle vuote
    #        (sono colonne FE-only composite, non rappresentabili senza
    #        funzione FE).
    def _filter_colonne_esportabili(
        self, colonne: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        result = [
            c for c in colonne
            if c.get("tipo_colonna") != "azione"
            and c.get("esportabile", True) is not False
        ]
        result.sort(key=lambda c: int(c.get("ordine_default") or 0))
        return result

    # Scopo: Rendering CSV. Pattern:
    #          - prima riga: header commentato '# Filtri applicati: {...}'
    #            (vuoto se nessun filtro)
    #          - seconda riga: header colonne (etichetta letterale)
    #          - righe: valori serializzati con cast minimal (str/repr)
    #        Encoding UTF-8, separatore virgola, quoting MINIMAL, BOM
    #        per Excel-friendly opening (otherwise accenti/UTF-8 si
    #        rompono nei file aperti con doppio click su Windows).
    def _render_csv(
        self,
        colonne: list[dict[str, Any]],
        righe: Sequence[Mapping[str, Any]],
        filtri: dict[str, Any],
    ) -> bytes:
        buffer = io.StringIO()
        # Header filtri come riga commentata (compatibile con import
        # standard CSV: il `#` viene letto come dato testo se non
        # filtrato dal parser, quindi il consumer puo' skippare la
        # prima riga "# Filtri applicati:..." manualmente).
        filtri_serial = json.dumps(filtri, ensure_ascii=False, sort_keys=True)
        buffer.write(f"# Filtri applicati: {filtri_serial}\n")

        writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL)
        writer.writerow([c["etichetta"] for c in colonne])
        for riga in righe:
            writer.writerow([
                self._format_cell(riga, c) for c in colonne
            ])

        # BOM UTF-8 per Excel: senza, gli accenti compaiono mojibake al
        # doppio click su Windows. Costo: 3 byte. Tradeoff accettato.
        return b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")

    # Scopo: Rendering XLSX con openpyxl. Due fogli:
    #          - "Dati": header bold + righe valori
    #          - "Filtri applicati": tabella key/value dei filtri attivi
    #        In v1 niente styling fine (formati cella per data/numero):
    #        i valori sono stringhe semplici, Excel li interpreta bene
    #        per i casi tipici.
    def _render_xlsx(
        self,
        colonne: list[dict[str, Any]],
        righe: Sequence[Mapping[str, Any]],
        filtri: dict[str, Any],
    ) -> bytes:
        wb = Workbook()
        ws_dati = wb.active
        assert ws_dati is not None
        ws_dati.title = "Dati"

        # Header bold per leggibilita'.
        ws_dati.append([c["etichetta"] for c in colonne])
        bold_font = Font(bold=True)
        for cell in ws_dati[1]:
            cell.font = bold_font

        for riga in righe:
            ws_dati.append([
                self._format_cell(riga, c) for c in colonne
            ])

        # Foglio filtri sempre presente. Se vuoto, riga "(nessun filtro)"
        # per non lasciare il foglio bianco.
        ws_filtri = wb.create_sheet("Filtri applicati")
        ws_filtri.append(["Campo", "Valore"])
        for cell in ws_filtri[1]:
            cell.font = bold_font
        if not filtri:
            ws_filtri.append(["(nessun filtro applicato)", ""])
        else:
            for key in sorted(filtri.keys()):
                value = filtri[key]
                ws_filtri.append([
                    key,
                    json.dumps(value, ensure_ascii=False)
                    if not isinstance(value, (str, int, float, bool))
                    or isinstance(value, bool)
                    else value,
                ])

        # Save su BytesIO -> bytes restituibili dalla view.
        out = io.BytesIO()
        wb.save(out)
        return out.getvalue()

    # Scopo: Formatta una cella per CSV/XLSX delegando al dispatcher
    #        centralizzato `apps.core.services.locale_formatters.
    #        format_for_export`. Passiamo `tipo_dato` e `formato` della
    #        colonna cosi' il formatter applica la regola corretta:
    #        date -> DD-MM-YYYY (italiano), datetime -> DD-MM-YYYY HH:MM,
    #        boolean -> Si/No, numeric -> separatori italiani con
    #        eventuali formati `currency_eur`/`percent_2`/`thousand`.
    #
    #        Le costanti del formatter sono italiane di default in v1.
    #        v2 (rinviato): override per emittente/utente via
    #        `config.parameters` LOCALE_*.
    @staticmethod
    def _format_cell(riga: Mapping[str, Any], colonna: dict[str, Any]) -> Any:
        # `campo_sorgente` e' nullable (ui.lista_colonna): senza campo la
        # cella e' vuota, come la lettura di una chiave assente.
        campo = colonna.get("campo_sorgente")
        value = riga.get(campo, "") if campo is not None else ""
        return format_for_export(
            value,
            tipo_dato=colonna.get("tipo_dato"),
            formato=colonna.get("formato"),
        )
