# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio della PROIEZIONE della riga di lotto
#        (`VenditeRepository._map_lotto_row`): che ogni chiave legga la colonna
#        che le compete, e non quella accanto.
#
# ⛔ PERCHE' ESISTE, ed e' un difetto vero trovato il 2026-08-25.
#    `riaperto` leggeva `row[20]`, cioe' `totale_documenti`. Nessun errore:
#    prendeva un NUMERIC e lo passava a `bool()`, quindi il flag valeva
#    «questo lotto ha un totale diverso da zero». Sui dati veri era INVERTITO
#    proprio sul caso che conta — un lotto riaperto a saldo zero diceva
#    `false`, un lotto non riaperto con degli importi diceva `true` — e a
#    video quel flag decide se il prossimo giro si chiama «Avanza step»
#    (falso) o «Rigenera la bozza».
#
# ⚠️ Un mapper posizionale non fallisce mai quando l'indice e' sbagliato: legge
#    un'altra colonna e va avanti. L'unico presidio possibile e' una riga finta
#    in cui OGNI posizione porta un valore riconoscibile, cosi' uno scambio si
#    vede. E' anche la rete per la prossima colonna aggiunta in coda alla
#    SELECT: chi la aggiunge senza toccare il mapper trova qui il rosso.
#
# Indice test:
#   0. ogni_chiave_legge_la_sua_colonna
#   1. riaperto_non_dipende_dal_totale   (il difetto storico, in negativo)
#   2. data_documento_assente_resta_none
#   3. stato_congela_fiscale_senza_stato_resta_none
# ------------------------------------------------------------

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from django.test import SimpleTestCase

from apps.vendite.db.vendite_repository import VenditeRepository


# Riga finta nell'ORDINE ESATTO di `_LOTTO_SELECT_COLS`. Ogni valore e'
# riconoscibile: se un indice slitta, l'asserzione lo dice per nome.
def _riga(override: dict[int, object] | None = None):
    riga = [
        7,                              # 0  id
        "LTF-0000001",                  # 1  codice
        date(2026, 7, 1),               # 2  competenza_mese
        "MASSIVO",                      # 3  tipo_lotto
        11,                             # 4  utility_id
        "Utility X",                    # 5  utility_descrizione
        "COMPLETATO",                   # 6  stato_lotto
        "CHIUSO",                       # 7  stato_operativo
        2,                              # 8  stato_doc_fiscale_id
        "Emessa",                       # 9  stato_doc_fiscale_descrizione
        "EMESSA",                       # 10 stato_doc_fiscale_codice
        3,                              # 11 tipo_doc_fiscale_id
        "Front-office",                 # 12 tipo_doc_fiscale_descrizione
        4,                              # 13 area_geografica_id
        "Nord",                         # 14 area_geografica_descrizione
        72,                             # 15 emittente_soggetto_ruolo_id
        datetime(2026, 7, 2, 10, 30, tzinfo=UTC),   # 16 data_insert
        "mctit",                        # 17 user_insert
        "Emittente S.p.A.",             # 18 emittente_ragione_sociale
        5,                              # 19 n_fatture
        Decimal("1234.56"),             # 20 totale_documenti
        True,                           # 21 ha_errori_gravi
        False,                          # 22 riaperto
        date(2026, 7, 31),              # 23 data_documento
        False,                          # 24 stato_congela_fiscale
        # ⚠️ Due numeri DIVERSI fra loro e da `n_fatture` (5): uno scambio fra
        #    i tre conteggi non si vedrebbe con valori uguali.
        4,                              # 25 n_presi_in_carico
        3,                              # 26 n_esiti_completati
        # ⚠️ Diverso da `emittente_soggetto_ruolo_id` (72): sono due id del
        #    progetto che NON coincidono, e uno scambio si deve vedere.
        9,                              # 27 emittente_fiscale_id
        ["numera", "riporta_a_draft"],  # 28 azioni_permesse
        True,                           # 29 ristampabile
    ]
    for i, v in (override or {}).items():
        riga[i] = v
    return tuple(riga)


class MapLottoRowTests(SimpleTestCase):

    # 0. Ogni chiave prende il valore della SUA posizione.
    def test_ogni_chiave_legge_la_sua_colonna(self) -> None:
        r = VenditeRepository._map_lotto_row(_riga())

        self.assertEqual(r["id"], 7)
        self.assertEqual(r["codice"], "LTF-0000001")
        self.assertEqual(r["competenza_mese"], "2026-07-01")
        self.assertEqual(r["tipo_lotto"], "MASSIVO")
        self.assertEqual(r["utility_id"], 11)
        self.assertEqual(r["utility_descrizione"], "Utility X")
        self.assertEqual(r["stato_lotto"], "COMPLETATO")
        self.assertEqual(r["stato_operativo"], "CHIUSO")
        self.assertEqual(r["stato_doc_fiscale_id"], 2)
        self.assertEqual(r["stato_doc_fiscale_codice"], "EMESSA")
        self.assertEqual(r["tipo_doc_fiscale_id"], 3)
        self.assertEqual(r["area_geografica_id"], 4)
        self.assertEqual(r["emittente_soggetto_ruolo_id"], 72)
        self.assertEqual(r["user_insert"], "mctit")
        self.assertEqual(r["emittente_ragione_sociale"], "Emittente S.p.A.")
        self.assertEqual(r["n_fatture"], 5)
        # ⚠️ Stringa, non float: un totale fiscale non passa dal binario.
        self.assertEqual(r["totale_documenti"], "1234.56")
        self.assertIs(r["ha_errori_gravi"], True)
        self.assertIs(r["riaperto"], False)
        self.assertEqual(r["data_documento"], "2026-07-31")
        self.assertIs(r["stato_congela_fiscale"], False)
        # I due conteggi degli esiti (2026-09-12): presi in carico e completati.
        self.assertEqual(r["n_presi_in_carico"], 4)
        self.assertEqual(r["n_esiti_completati"], 3)
        # La PK dell'emittente (2026-09-27), accanto al soggetto-ruolo.
        self.assertEqual(r["emittente_fiscale_id"], 9)
        # I passaggi permessi dallo stato (§15.14, 2026-10-27): una lista, non
        # l'array del driver.
        self.assertEqual(r["azioni_permesse"], ["numera", "riporta_a_draft"])
        self.assertIs(r["ristampabile"], True)
        # Lotto senza stato (LEFT JOIN vuoto): NULL non e' «si ristampa».
        self.assertIs(VenditeRepository._map_lotto_row(_riga({29: None}))["ristampabile"], False)

    # 1. ⛔ IL DIFETTO STORICO, scritto in negativo: `riaperto` deve dipendere
    #    SOLO dalla sua colonna. Le due righe qui sotto sono i due casi veri
    #    misurati sul database il 2026-08-25, ed erano entrambi sbagliati.
    def test_riaperto_non_dipende_dal_totale(self) -> None:
        # Lotto riaperto a saldo ZERO (era il lotto 6034): diceva `false`.
        riaperto_a_zero = VenditeRepository._map_lotto_row(
            _riga({20: Decimal("0"), 22: True}),
        )
        self.assertIs(riaperto_a_zero["riaperto"], True)

        # Lotto NON riaperto con degli importi (erano 7132/7133/7515/4213):
        # diceva `true`.
        non_riaperto_con_importi = VenditeRepository._map_lotto_row(
            _riga({20: Decimal("400.00"), 22: False}),
        )
        self.assertIs(non_riaperto_con_importi["riaperto"], False)

    # 2. `data_documento` assente = nessuna DICHIARAZIONE, e resta None: non si
    #    ripiega su una data qualunque, che a video sembrerebbe una scelta.
    def test_data_documento_assente_resta_none(self) -> None:
        r = VenditeRepository._map_lotto_row(_riga({23: None}))
        self.assertIsNone(r["data_documento"])

    # 3. Il JOIN sullo stato e' LEFT: un lotto senza stato fiscale resta una
    #    riga, e la soglia di congelamento resta `None` — «non lo so», non
    #    «non congela». Appiattirlo a `False` qui accenderebbe i verbi di
    #    pipeline sul caso in cui si sa meno di tutti.
    def test_stato_congela_fiscale_senza_stato_resta_none(self) -> None:
        r = VenditeRepository._map_lotto_row(_riga({24: None}))
        self.assertIsNone(r["stato_congela_fiscale"])
