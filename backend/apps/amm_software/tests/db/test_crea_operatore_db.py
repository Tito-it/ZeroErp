# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `AmmSoftwareRepository.crea_operatore` sul DB vero: il binding per
#        nome della madre `anagrafiche.fn_crea_operatore` e il suo permesso
#        (giro 10-bis di brief-db-porte-aperte-dalla-sola-guc §14, 2026-11-26:
#        il verbo e' SECURITY DEFINER e chiede il SUPER_ADMIN della sessione).
#        I test di service e di API mockano il repository e non vedono ne' i
#        nomi dei parametri ne' il guard.
#
# ⚠️ CASI COSTRUITI in una transazione SEMPRE annullata: chi crea e' un
#    utente costruito, mai il primo operatore del DB.
#
# Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`):
#   1. un SUPER_ADMIN costruito crea un operatore SUPER_ADMIN: credenziale
#      nuova, veste OPERATORE spenta, legame SUPER_ADMIN sulla veste
#   2. un operatore con livello TUTTO sulle anagrafiche riceve
#      E_PERMESSO_NEGATO: il verbo chiede il SUPER_ADMIN, non un livello
# ------------------------------------------------------------

from __future__ import annotations

from unittest import TestCase

from django.db import DatabaseError, connection, transaction

from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository
from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.tests.db_e2e import (
    Annulla,
    apri_operatore_con_aree,
    apri_super_admin_costruito,
    richiedi_db_provvisto,
)


class CreaOperatoreDbTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: Gli argomenti di un operatore nuovo, flusso A (il soggetto lo crea
    #        la madre): codice fiscale libero adesso, username ed email da lui,
    #        la qualifica DIPENDENTE per codice (mai un id cablato), la
    #        residenza da un dettaglio costruito.
    @staticmethod
    def _argomenti(cur) -> dict:
        cur.execute("SELECT dbops.fn_pgtap_cf_libero()")
        cf = cur.fetchone()[0]
        cur.execute("SELECT id FROM config.qualifiche WHERE codice_interno = 'DIPENDENTE'")
        riga = cur.fetchone()
        assert riga is not None, "la qualifica DIPENDENTE non e' a catalogo (config.qualifiche)"
        # Un privato vuole la residenza: la madre la scrive al passo degli
        # indirizzi, come nel modulo vero.
        cur.execute("SELECT dbops.fn_pgtap_crea_indirizzo_dettaglio('crea operatore BE')")
        residenza = cur.fetchone()[0]
        return {
            "indirizzo_resid_dettaglio_id": int(residenza),
            "cognome": "Creato dal BE",
            "nome": "Test",
            "codice_fiscale": cf,
            "sesso": "M",
            "username": f"be_crea_{cf.lower()}",
            "email": f"be_crea_{cf.lower()}@example.com",
            "password_hash": "be-test-nessun-login",
            "qualifica_id": int(riga[0]),
        }

    def test_il_super_admin_crea_un_operatore(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_super_admin_costruito(cur, etichetta="crea operatore admin")
                # Dopo i builder: il codice fiscale e' libero ADESSO, e il
                # builder ne prende uno anche lui.
                argomenti = self._argomenti(cur)
                # ⚠️ La finestra differita: i builder la richiudono, e la madre
                #    scrive il soggetto prima dei suoi indirizzi. Si riapre per
                #    la saga e si richiude dopo, cosi' i guard differiti
                #    giudicano l'operatore finito, come al COMMIT.
                cur.execute("SET CONSTRAINTS ALL DEFERRED")
                creato = AmmSoftwareRepository().crea_operatore(
                    **argomenti, is_super_admin=True,
                )
                cur.execute("SET CONSTRAINTS ALL IMMEDIATE")
                self.assertFalse(creato["credenziale_riusata"])

                # ⛔ In un'istruzione separata dalla creazione: una lettura
                #    nella stessa vedrebbe la fotografia di prima.
                cur.execute(
                    "SELECT idd.attivo,"
                    "       EXISTS (SELECT 1"
                    "                 FROM config.profili_accesso_bindings pab"
                    "                 JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id"
                    "                WHERE pab.identita_digitale_id = idd.id AND pa.tipo = 'SUPER_ADMIN')"
                    "  FROM anagrafiche.identita_digitali idd"
                    " WHERE idd.auth_user_id = %s AND idd.ruolo_applicativo = 'OPERATORE'",
                    [creato["auth_user_id"]],
                )
                # La veste nasce spenta (la accende l'invito), col legame.
                self.assertEqual(cur.fetchall(), [(False, True)])
                raise Annulla
        except Annulla:
            pass

    def test_un_operatore_che_non_e_super_admin_e_rifiutato(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_operatore_con_aree(
                    cur, aree=("anagrafiche",), motivo="crea operatore senza SUPER_ADMIN",
                )
                argomenti = self._argomenti(cur)
                with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
                    AmmSoftwareRepository().crea_operatore(**argomenti)
                self.assertEqual(structured_db_error_code(ctx.exception), "E_PERMESSO_NEGATO")
                raise Annulla
        except Annulla:
            pass
