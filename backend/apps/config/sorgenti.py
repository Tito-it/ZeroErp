# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I codici di `config.sorgenti` (`codice_interno`, la chiave immutabile)
#        che il backend nomina, in un posto solo.
# ------------------------------------------------------------

# PERCHE' ESISTE (2026-10-11, ok Tid). Gli stessi codici erano ricopiati come
# letterali o costanti locali in una trentina di moduli (`_SORGENTE_DDT` due
# volte, `_CODICE_SORGENTE_*` nelle view documenti, le mappe del push a
# commessa, il lineage). Un codice scritto male non da' errore: la lettura per
# codice non trova la riga, e il risultato e' una lista vuota o una colonna NULL.
#
# ⛔ SOLO il vocabolario di `config.sorgenti`. Molti altri vocabolari usano le
#    stesse parole e NON sono questo: le partizioni delle note (`target_tipo`,
#    dove l'ordine e' "ORDINE"), i tipi di `config.tipi_entita`
#    (`fn_offerta_documenti_vivi`), la fonte del prezzo, l'entita' dei log.
#    Che oggi alcuni coincidano e' un caso: legarli a queste costanti li
#    farebbe cambiare insieme il giorno in cui divergono.
# ⭐ La grammatica delle TESTATE (il `p_documento` dei lettori di testata, dei
#    building block degli indirizzi e di `fn_documento_legami`) e' invece
#    QUESTO vocabolario dal 2026-10-19 (brief-db-grammatica-unica-documenti,
#    lotto 2a): a DB `p_documento` e' `config.sorgenti.codice_interno%TYPE`.
#    Dal lotto 2b (stesso giorno) lo sono anche l'ORIGINE e la DESTINAZIONE:
#    `vendite.ordini.documento_origine_tipo` e
#    `config.nature_vendita.destinazione_tipo` (FK verso `config.sorgenti`),
#    l'`origine` di `fn_documento_legami` (tranne `ONERE`, che non e' una
#    sorgente). Dal 2026-10-20 (§12.8) anche l'`origine` delle partite di
#    `vendite.fn_partite_merce` (`ORDINE_VENDITA`; `NESSUNA` e `MULTIPLA`
#    dicono l'assenza e l'ambiguita' dell'origine, non sono sorgenti).
# ⭐ Il NOME e' `SORGENTE_<codice_interno>`, sempre: lo presidia
#    `config/tests/test_sorgenti_seed.py`, insieme all'esistenza e all'attivita'
#    del codice nel seed. Un codice nuovo si aggiunge qui quando un modulo lo
#    nomina, non prima.

from typing import Final

# ⭐ `Final`: mypy legge il valore come letterale, quindi una costante si passa
#    dove la firma dichiara i codici ammessi (`Literal[...]`, per esempio
#    `DocumentoEccezioni`) e una divergenza fra i due e' un errore di tipo.

# Documenti (categoria DOCUMENTO).
SORGENTE_PREVENTIVO: Final = "PREVENTIVO"
SORGENTE_OFFERTA_COMMERCIALE: Final = "OFFERTA_COMMERCIALE"
SORGENTE_ORDINE_VENDITA: Final = "ORDINE_VENDITA"
SORGENTE_CONTRATTO: Final = "CONTRATTO"
SORGENTE_DDT_VENDITA: Final = "DDT_VENDITA"
SORGENTE_RESO_VENDITA: Final = "RESO_VENDITA"
SORGENTE_FATTURA: Final = "FATTURA"
SORGENTE_COMMESSA: Final = "COMMESSA"
SORGENTE_ATTIVITA_CONSUMI: Final = "ATTIVITA_CONSUMI"

# Righe di magazzino (categoria RIGA).
SORGENTE_INVENTARIO_RIGA: Final = "INVENTARIO_RIGA"
SORGENTE_RETTIFICA_RIGA: Final = "RETTIFICA_RIGA"
