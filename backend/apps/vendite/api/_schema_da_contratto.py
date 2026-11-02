# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il dizionario dei TIPI delle chiavi dei contratti di vendite (una
#        chiave, un tipo, in tutti e sei i documenti) e l'adattatore che lega
#        il building block di core `schema_da_contratto` a questo dizionario.
# Note: ⭐ Il meccanismo e' in `core/api/schema_da_contratto.py` (traslocato il
#       2026-09-26, regola del 2, ok Tid): qui resta cio' che e' di vendite. Le
#       view chiamano `schema_da_contratto(nome, chiavi, ...)` senza `tipi`.
#       ⭐ I tipi vengono dalle colonne (docs/it/dbzero/vendite/tabelle), e
#       `allow_null` dove la colonna e' nullable o dove il null ha un
#       significato in PATCH (azzera `meta`).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from collections.abc import Iterable, Mapping

from rest_framework import serializers

from apps.core.api import schema_da_contratto as _bb
from apps.core.api.schema_da_contratto import (
    Tipi,
    booleano as _booleano,
    data as _data,
    decimale as _decimale,
    intero as _intero,
    json as _json,
    testo as _testo,
    uuid as _uuid,
)


# Scopo: le due mappe dei componenti BoM di una riga composita (chiavi del
#        contratto che non sono colonne): prezzi manuali e attivazioni.
def _mappa_prezzi(**kw: Any) -> serializers.Field:
    return serializers.DictField(
        help_text=(
            "Mappa {componente_id: prezzo} per prezzi manuali sui componenti "
            "BoM del padre composito. Richiede l'azione `prezzo_override_manuale`."
        ),
        **kw,
    )


def _mappa_attivazioni(**kw: Any) -> serializers.Field:
    return serializers.DictField(
        child=serializers.BooleanField(),
        help_text=(
            "Mappa {componente_id: bool} per attivare i componenti opzionali "
            "del padre composito."
        ),
        **kw,
    )


# Il tipo di ogni chiave che un contratto di vendite puo' nominare, e se la
# colonna ammette NULL. Una chiave nuova in un contratto entra QUI, o l'import
# fallisce.
TIPI: Tipi = {
    # ── testate: parti e anagrafiche ─────────────────────────
    "billing_account_id": (_intero, True),
    "soggetto_ruolo_id": (_intero, False),
    "destinatario_soggetto_ruolo_id": (_intero, False),
    "mittente_soggetto_ruolo_id": (_intero, True),
    "vettore_soggetto_ruolo_id": (_intero, True),
    "agente_soggetto_ruolo_id": (_intero, True),
    "emittente_fiscale_id": (_intero, False),
    "utility_id": (_intero, True),
    "valuta_id": (_intero, True),
    "modalita_pagamento_id": (_intero, True),
    "termine_pagamento_id": (_intero, True),
    "causale_trasporto_id": (_intero, True),
    "aspetto_bene_id": (_intero, True),
    "modalita_addebito_trasporto_id": (_intero, True),
    # Il magazzino di bolla e reso (Lotto 3 D-L3-a, 3-bis D-3b-a): nullable in
    # bozza, obbligatorio all'emissione/conferma se il documento muove merce.
    "magazzino_id": (_intero, True),
    "magazzino_arrivo_id": (_intero, True),
    "ddt_id": (_intero, False),
    "istanza_utility_id": (_intero, True),
    "contratto_id": (_intero, False),
    "parent_contratto_id": (_intero, True),
    "listino_id": (_intero, True),
    "listino_versione_id": (_intero, True),
    "categoria_cliente_id_snapshot": (_intero, True),
    # ── testate: dati del documento ──────────────────────────
    "data": (_data, False),
    "meta": (_json, True),
    "fatturazione_immediata": (_booleano, False),
    # Dominio chiuso (CHECK a DB): i valori li dice il messaggio d'errore del
    # service, non si ricopiano qui.
    "fatturazione_trigger": (_testo, False),
    "num_colli": (_intero, True),
    "peso_lordo": (_decimale, True),
    "peso_netto": (_decimale, True),
    "volume": (_decimale, True),
    "targa": (_testo, True),
    "autista": (_testo, True),
    "tracking_code": (_testo, True),
    "validita_dal": (_data, True),
    "validita_al": (_data, True),
    "valido_dal": (_data, False),
    "valido_al": (_data, True),
    "competenza_mese": (_data, True),
    # Domini chiusi a DB (CHECK o enum): i valori li dice il DB, non questo file.
    "ambito": (_testo, True),
    "tipo_variazione_globale": (_testo, True),
    "valore_variazione_globale": (_decimale, True),
    "codice_cig": (_testo, True),
    "codice_cup": (_testo, True),
    "codice_commessa": (_testo, True),
    # I canoni della testata (F-2, F-7): anticipati/normali e il mese da cui si
    # contano i periodi. NOT NULL a DB col default: `null` non si manda.
    "mese_partenza_canone": (_intero, False),
    # ── righe ────────────────────────────────────────────────
    "articolo_id": (_uuid, False),
    "descrizione": (_testo, False),
    "quantita": (_decimale, False),
    "qta_operativa": (_decimale, True),
    # I prelievi della bolla (Lotto 3 D-L3-b): quantita' in UoM base, la voce
    # (componente del kit) e la posizione fisica.
    "qta": (_decimale, False),
    "ddt_riga_componente_id": (_intero, True),
    "lotto_id": (_intero, True),
    "asset_id": (_intero, True),
    "ubicazione_id": (_intero, True),
    "ubicazione_arrivo_id": (_intero, True),
    # Il rientro del reso (3-bis D-3b-b): il prelievo d'origine della bolla.
    "ddt_riga_prelievo_id": (_intero, False),
    "uom_operativa_id": (_intero, True),
    "factor_to_base": (_decimale, False),
    "prezzo_unitario": (_decimale, True),
    "sconto_percentuale": (_decimale, True),
    "data_consegna_richiesta_cliente": (_data, True),
    "data_consegna_confermata": (_data, True),
    "ddt_riga_id": (_intero, False),
    "tipo_reso_id": (_intero, False),
    "motivo": (_testo, True),
    "ordine": (_intero, True),
    "tipo_eccezione": (_testo, False),
    "tipo_erogazione": (_testo, True),
    "fonte_quantita_attesa": (_testo, False),
    "periodicita": (_testo, True),
    "generazione_canone": (_testo, True),
    # Non colonne: il service le legge per il gate prezzi (L3) e i componenti.
    "richiesta_approvazione": (_booleano, False),
    "componenti_overrides": (_mappa_prezzi, True),
    "componenti_attivazioni": (_mappa_attivazioni, True),
    # ── utility 1:1 (oggetto `utility` annidato nelle testate) ──
    "istanza_dati_precontrattuali_id": (_intero, True),
    "tipo_utenza_id": (_intero, True),
    "classe_utenza_id": (_intero, True),
    "param_1_num": (_decimale, True),
    "param_2_txt": (_testo, True),
    # ── componenti BoM ───────────────────────────────────────
    "attivo": (_booleano, False),
    # ── azioni ───────────────────────────────────────────────
    "stato_codice": (_testo, False),
    # La conferma dell'annullo di un documento con legami
    # (brief-db-annullo-documento-con-legami): quanti legami l'operatore ha
    # visto. Assente al primo tentativo.
    "legami_confermati": (_intero, True),
}


# Scopo: l'adattatore: il building block di core col dizionario di vendite.
def schema_da_contratto(
    nome: str,
    chiavi: Iterable[str],
    *,
    obbligatorie: Iterable[str] = (),
    speciali: Mapping[str, serializers.Field] | None = None,
) -> serializers.Serializer:
    return _bb.schema_da_contratto(
        nome, chiavi, tipi=TIPI, obbligatorie=obbligatorie, speciali=speciali,
    )


# Il cambio stato di ordini e ddt: il gestore legge la sola `stato_codice`.
# ⚠️ UNA costante per i due documenti: due `inline_serializer` con lo stesso
#    nome sono due classi, e drf-spectacular avverte che lo schema e' sbagliato.
CAMBIA_STATO_REQUEST = schema_da_contratto(
    "VenditeCambiaStatoReq", ("stato_codice",), obbligatorie=("stato_codice",),
)
# Il cambio di stato di un documento che si annulla con conferma (bolla,
# ordine): verso ANNULLATO porta la dichiarazione `legami_confermati`.
CAMBIA_STATO_CON_CONFERMA_REQUEST = schema_da_contratto(
    "VenditeCambiaStatoConConfermaReq", ("stato_codice", "legami_confermati"),
    obbligatorie=("stato_codice",),
)
