# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I formati di file che un tipo ammette, letti dal DB in una sede sola
#        (regola del 2, ok Tid 2026-11-16, BE5/BE12 di
#        brief-db-revisione-documenti §12.6).
#        `config.formati_file` e' il vocabolario dei formati (un tipo MIME
#        con la sua estensione); ogni vocabolario di tipi che ammette dei
#        formati ha la sua tabella di abbinamento tipo × formato. Prima del
#        2026-11-16 le liste erano mappe Python ricopiate nei service
#        (`_MIME_WHITELIST_PER_TIPO`, `_MIME_WHITELIST_ALLEGATO` e le due
#        `_MIME_EXT_FALLBACK*`): la regola ora e' del DB
#        (`documenti.trgfn_guard_formato_ammesso`), qui si LEGGE soltanto.
#
#        - `sql_formati_ammessi(vocabolario, alias)`: la sottoquery che,
#          dentro una SELECT sul vocabolario dei tipi, porta i formati del
#          tipo come lista jsonb `[{mime_type, estensione, etichetta_key}]`
#          nell'ordine del vocabolario dei formati (`[]` se nessuno). La usano
#          le letture puntuali del tipo e la lookup specializzata della
#          tendina: la join c'e' una volta.
#        - `estensione_del_formato(formati, mime)`: l'estensione di un MIME
#          nella lista letta, o `None` se il MIME non c'e'.
# Note: gli identificatori interpolati vengono SOLO da `_ABBINAMENTI`
#       (costante): un vocabolario sconosciuto e' un errore di programma.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

# Vocabolario dei tipi → (tabella di abbinamento, colonna che punta al tipo).
# Un vocabolario nuovo che ammette formati (gli allegati email, quando un giro
# delle email lo apre) aggiunge una riga qui.
_ABBINAMENTI: dict[str, tuple[str, str]] = {
    "documenti.tipi_asset_documento": (
        "documenti.tipi_asset_documento_formati", "asset_tipo_id",
    ),
    "documenti.tipi_file_documento": (
        "documenti.tipi_file_documento_formati", "file_tipo_id",
    ),
}


# Scopo: La sottoquery dei formati ammessi da un tipo, da proiettare in una
#        SELECT su `vocabolario` con alias `alias`.
# Risultato: espressione SQL jsonb (lista, mai NULL).
def sql_formati_ammessi(vocabolario: str, alias: str = "t") -> str:
    if vocabolario not in _ABBINAMENTI:
        raise ValueError(f"vocabolario senza formati: {vocabolario!r}")
    if not alias.isidentifier():
        raise ValueError(f"alias non valido: {alias!r}")
    abbinamento, colonna_tipo = _ABBINAMENTI[vocabolario]
    return f"""(
        SELECT COALESCE(
                   jsonb_agg(
                       jsonb_build_object(
                           'mime_type', ff.mime_type,
                           'estensione', ff.estensione,
                           'etichetta_key', ff.etichetta_key
                       ) ORDER BY ff.ordine, ff.id
                   ),
                   '[]'::jsonb
               )
          FROM {abbinamento} ab
          JOIN config.formati_file ff ON ff.id = ab.formato_file_id
         WHERE ab.{colonna_tipo} = {alias}.id
    )"""  # noqa: S608 — tabella e colonna da _ABBINAMENTI (costante), alias verificato identificatore


# Scopo: L'estensione di un MIME fra i formati letti con `sql_formati_ammessi`.
# Risultato: l'estensione, o None se il MIME non e' fra i formati.
def estensione_del_formato(formati: list[dict[str, Any]], mime: str) -> str | None:
    for formato in formati:
        if formato.get("mime_type") == mime:
            return formato.get("estensione")
    return None
