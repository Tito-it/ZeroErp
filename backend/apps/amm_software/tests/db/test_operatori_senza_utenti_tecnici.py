# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio — le due liste di Amm. Software che partono `FROM auth_user`
#        parlano di PERSONE, e non devono mai mostrare un utente TECNICO di
#        processo automatico.
#
# ⛔ PERCHE' ESISTE, e non e' teoria. Dal 2026-09-04 il database crea un utente
#    per ogni coppia (processo automatico, emittente) — `run_fatturazione_batch@ACME`
#    e compagni. Hanno un `auth_user`, un'identita' `OPERATORE` e un perimetro,
#    ma nessun rapporto di lavoro e nessuno a cui telefonare. Le due query
#    partono dalla tabella degli utenti Django, quindi li mostravano come
#    persone senza cognome: **nessun errore, righe vere di una specie
#    sbagliata**. Misurato il 2026-09-05 sul database di sviluppo: 12 utenti
#    tecnici in mezzo a 10 persone.
#
# ⛔ IL SOGGETTO NON SI PUO' FABBRICARE, ED E' STATO PROVATO. La strada giusta
#    sarebbe chiamare `script.fn_crea_utente_tecnico`, cioe' la fabbrica vera.
#    Non funziona, per DUE guard che si sommano — e nessuno dei due va rilassato:
#      1. il flag non si accende a mano su una persona: dal changeSet
#         20260904-28 `trgfn_identita_digitali_guard_coerenza` pretende un
#         `soggetto_ruolo` `PROC_AUTO` quando `tecnica = true` e `RIS_UMANA`
#         quando e' false — i due mondi sono disgiunti in ENTRAMBI i versi
#         (stessa scoperta del brief DB §12.7);
#      2. ✅ RISOLTA IL 2026-09-05 (DB-6), e si scrive perche' resti la storia:
#         la fabbrica non poteva rifare una coppia gia' servita — il guard 4
#         guardava `processi_identita.attivo`, ma lo USERNAME e' deterministico
#         (`processo@emittente`) e UNIQUE senza condizioni, quindi disattivare
#         il legame liberava il guard e lasciava il muro
#         (`auth_user_username_key`), con un 23505 nudo. Adesso il rifiuto
#         parla (`E_UTENTE_TECNICO_DA_RIATTIVARE`) e c'e' il verbo che mancava
#         (`script.fn_riattiva_utente_tecnico`).
#         ⚠️ Non basta a fabbricare qui: resta il guard 1, che e' giusto e non
#         si tocca, e resta il fatto che su un database ricostruito da zero
#         mancano gli EMITTENTI (seed `dati_macchina`) — cioe' l'argomento
#         obbligatorio della fabbrica.
#
# ⚠️ Quindi il test USA i soggetti che ci sono, e QUANDO NON CI SONO LO DICE
#    (`skip` motivato) invece di passare a vuoto. E' la seconda delle due
#    strade che AGENTS.md ammette, non una scorciatoia: su un database
#    ricostruito da zero gli utenti tecnici non esistono (il loro seed e'
#    `context: dati_macchina`, che la CI non esegue), e un verde li' non
#    proverebbe niente.
#
# ⭐ La vacuita' e' comunque chiusa da DUE lati: la controprova nella stessa
#    corsa (una PERSONA deve comparire in entrambe le liste, altrimenti il
#    «non c'e'» varrebbe anche per una lista vuota) e il test 2, che fissa il
#    guard del database — il presidio piu' forte dei due.
#
# Rollback-safe: tutto in `transaction.atomic()` + `set_rollback(True)`.
#
# Indice test (1..2):
#   1. nessun utente tecnico compare in `list_operatori` ne' in
#      `get_permessi_riepilogo` — e nella stessa corsa una PERSONA compare in
#      entrambe (controprova: le liste non sono vuote)
#   2. ⛔ il flag non si puo' spostare a mano fra i due mondi: il presidio piu'
#      forte e' del database, e questo test lo fissa perche' non venga rilassato
# ------------------------------------------------------------

from __future__ import annotations

import unittest

from django.db import DatabaseError, connection, transaction

from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository
from apps.core.tests.db_e2e import richiedi_db_provvisto


# Scopo: gli `auth_user_id` che hanno un'identita' TECNICA. Sono i soggetti
#        della prova: se l'insieme e' vuoto il test si dichiara senza materia
#        invece di passare a vuoto (vedi intestazione).
def _utenti_tecnici() -> set[int]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT idg.auth_user_id
              FROM anagrafiche.identita_digitali idg
             WHERE idg.tecnica
            """
        )
        return {row[0] for row in cursor.fetchall()}


# Scopo: una PERSONA che le liste devono continuare a consegnare — serve come
#        controprova nella stessa corsa dei test.
def _una_persona() -> int | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT au.id
              FROM auth_user au
              JOIN anagrafiche.identita_digitali idg
                ON idg.auth_user_id = au.id
               AND idg.ruolo_applicativo = 'OPERATORE'
             WHERE au.is_active = true
               AND NOT COALESCE(idg.tecnica, false)
             ORDER BY au.id
             LIMIT 1
            """
        )
        row = cursor.fetchone()
    return row[0] if row else None


class OperatoriSenzaUtentiTecniciTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()
        cls.tecnici = _utenti_tecnici()
        cls.persona = _una_persona()
        # ⚠️ Skip DICHIARATO, non silenzio: senza utenti tecnici questo test non
        #    ha soggetti e la sua copertura vale ZERO, non «parziale».
        if not cls.tecnici:
            raise unittest.SkipTest(
                "Nessuna identita' con flag `tecnica`: i soggetti della prova non "
                "esistono su questo database (il loro seed e' `dati_macchina`)."
            )
        if cls.persona is None:
            raise unittest.SkipTest(
                "Nessun operatore persona: manca la controprova, e senza il test "
                "sarebbe verde anche su liste vuote."
            )

    def setUp(self) -> None:
        self.repo = AmmSoftwareRepository()

    # Scopo: gli id consegnati dalle due liste di Amm. Software.
    # ⚠️ Dal 2026-10-06 il riepilogo non sceglie piu' i suoi operatori: riceve
    #    gli id della pagina della lista. Gli si chiedono APPOSTA i tecnici
    #    (piu' la persona): deve scartarli lui, non contare sul chiamante.
    def _id_dalle_due_liste(self) -> tuple[set[int], set[int]]:
        righe, _ = self.repo.list_operatori(limit=200)
        riepilogo = self.repo.get_permessi_riepilogo(sorted(self.tecnici | {self.persona}))
        return (
            {r["auth_user_id"] for r in righe},
            {r["auth_user_id"] for r in riepilogo},
        )

    def test_utenti_tecnici_fuori_dalle_liste_delle_persone(self):
        ids_lista, ids_riepilogo = self._id_dalle_due_liste()

        self.assertEqual(
            self.tecnici & ids_lista, set(),
            "Uno o piu' utenti tecnici compaiono nella lista Operatori: quella "
            "lista parla di persone.",
        )
        self.assertEqual(
            self.tecnici & ids_riepilogo, set(),
            "Uno o piu' utenti tecnici compaiono nel riepilogo permessi: "
            "sarebbero letti come «operatori senza permessi» invece che come "
            "«non sono operatori».",
        )
        # ⭐ La controprova, nella STESSA corsa: senza, i due `assertEqual`
        #    sarebbero verdi anche se le liste tornassero vuote per un motivo
        #    qualsiasi — e non proverebbero niente.
        self.assertIn(self.persona, ids_lista)
        self.assertIn(self.persona, ids_riepilogo)

    # ⛔ Il presidio vero e' del DATABASE, e questo test lo FISSA: se un giorno
    #    qualcuno rilassasse il guard, il difetto tornerebbe possibile a monte —
    #    e l'esclusione applicativa non basterebbe piu' a descrivere il modello.
    def test_il_flag_non_si_sposta_a_mano_fra_i_due_mondi(self):
        with transaction.atomic():
            try:
                with connection.cursor() as cursor, self.assertRaises(DatabaseError):
                    cursor.execute(
                        "UPDATE anagrafiche.identita_digitali SET tecnica = true"
                        " WHERE auth_user_id = %s AND ruolo_applicativo = 'OPERATORE'",
                        [self.persona],
                    )
            finally:
                transaction.set_rollback(True)
