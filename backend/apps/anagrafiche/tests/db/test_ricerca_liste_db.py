# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La ricerca libera delle liste di anagrafiche convertite al BB
#        `add_ricerca_full_condition` il 2026-09-24 (brief-be-ricerca-full-liste-
#        residue §5.4, passo 7), provata sul DATABASE VERO: per ogni colonna che
#        il CATALOGO accende, il valore di una riga COSTRUITA la trova dal suo
#        repository (`verifica_ricerca_colonna_per_colonna`).
#        Liste: `anagrafiche.clienti`, `anagrafiche.soggetti`,
#        `anagrafiche.categorie_clienti_listini`, `anagrafiche.operatori`.
# Note: ⚠️ Il mondo si COSTRUISCE, non si cerca (guida pgtap, regola zero in
#       .codex/AGENTS.md): su un database ricostruito dai changelog le
#       anagrafiche sono a zero, e una prova che «cerca» una riga esistente
#       uscirebbe vuota. Le righe nascono dai builder `dbops.fn_pgtap_crea_*`,
#       in transazione ANNULLATA (`Annulla`) e col contesto operatore.
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
#       ⚠️ Le tre liste senza `vista_sql` (soggetti, matrice, operatori) sono
#       esercitate SOLO qui: `test_ricerca_full_db` nomina questi test in
#       `_ESERCITATE_DAL_REPOSITORY`, e un rename li fa rossi la'.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) RicercaListeAnagraficheDbTests.test_clienti_trova_ogni_colonna_accesa
2) RicercaListeAnagraficheDbTests.test_soggetti_trova_ogni_colonna_accesa
3) RicercaListeAnagraficheDbTests.test_categorie_clienti_listini_trova_ogni_colonna_accesa
4) RicercaListeAnagraficheDbTests.test_operatori_trova_ogni_colonna_accesa
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.tests.db_e2e import (
    Annulla,
    apri_contesto_operatore,
    richiedi_db_provvisto,
    verifica_ricerca_colonna_per_colonna,
)


# Scopo: il mondo minimo di un cliente — azienda con operatore, contesto, e un
#        cliente fatturabile legato a QUELL'azienda, fino alla riga di
#        `anagrafiche.clienti` (builder `dbops.fn_pgtap_crea_cliente`, R-9 di
#        brief-db-codici-non-trovato-email-e-permessi: fino al 2026-10-10 la
#        riga era una INSERT a mano, copia divergente di quella del test del
#        dettaglio ricerca). Torna `(mondo, cliente_id)`.
# ⚠️ Il mondo PRIMA del contesto dell'operatore di prova: il builder vuole
#    scegliersi l'azienda (ramo «nessun contesto»), come in `test_ricerca_full_db`.
#    E anche il cliente: il builder apre il contesto sul SUO operatore, e il BA
#    lo crea solo un operatore d'azienda (`E_BA_ADMIN_GLOBALE_VIETATO` per
#    l'amministratore globale su cui si apre poi la prova).
# ⚠️ Utility SENZA PDP (`richiede_pdp = false`): un cliente su un'utility a PDP
#    ne pretenderebbe uno, e il PDP non e' il soggetto di questa prova.
def _mondo_cliente(cur) -> tuple[dict, int]:
    cur.execute("SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('ricerca anagrafiche BE')")
    mondo = dict(zip([c.name for c in cur.description], cur.fetchone(), strict=True))
    # Stato PR (pre-contratto), come la riga scritta a mano che il builder
    # sostituisce: lo stato non e' il soggetto di questa prova.
    cur.execute(
        "SELECT * FROM dbops.fn_pgtap_crea_cliente("
        "  'ricerca anagrafiche',"
        "  (SELECT u.id FROM config.utilities u WHERE NOT u.richiede_pdp ORDER BY u.id LIMIT 1),"
        "  %s, 'PR')",
        [mondo["emittente_soggetto_ruolo_id"]],
    )
    cli = dict(zip([c.name for c in cur.description], cur.fetchone(), strict=True))
    cliente_id = cli["cliente_id"]
    apri_contesto_operatore(cur)
    return {**mondo, "cliente": cli}, cliente_id


# Scopo: codice, ragione sociale e id fiscale di un soggetto, per cercarli.
# ⭐ La ragione sociale si RISCRIVE con un termine che sta solo li': il builder la
#    compone col codice del BA (`Cliente <etichetta> PGTAPBA00001`), e cercare
#    il codice BA la troverebbe anche per la ragione sociale — la colonna
#    `ba_codice` resterebbe non provata, verde per sottrazione.
def _soggetto(cur, soggetto_id, ragione_sociale: str) -> tuple[str, str]:
    cur.execute(
        "UPDATE anagrafiche.soggetti SET ragione_sociale = %s WHERE id = %s",
        [ragione_sociale, soggetto_id],
    )
    cur.execute(
        "SELECT codice, id_fiscale_univoco_cf_piva FROM anagrafiche.soggetti WHERE id = %s",
        [soggetto_id],
    )
    return cur.fetchone()


class RicercaListeAnagraficheDbTests(unittest.TestCase):
    """Ogni colonna che il catalogo accende trova la riga costruita, dal
    repository della lista (brief-be-ricerca-full-liste-residue §4, riga 6)."""

    def setUp(self):
        richiedi_db_provvisto("ui.fn_lista_colonne_ricerca_full(character varying)")

    def test_clienti_trova_ogni_colonna_accesa(self):
        from apps.anagrafiche.db.clienti_repository import ClientiRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                mondo, cliente_id = _mondo_cliente(cur)
                soggetto_codice, id_fiscale = _soggetto(
                    cur, mondo["cliente"]["soggetto_id"], "Cliente ricragcli",
                )
                cur.execute(
                    "SELECT codice FROM anagrafiche.billing_account WHERE id = %s",
                    [mondo["cliente"]["billing_account_id"]],
                )
                ba_codice = cur.fetchone()[0]
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "anagrafiche.clienti", cliente_id,
                    {"ragione_sociale_completa": "ricragcli", "ba_codice": ba_codice,
                     "soggetto_codice": soggetto_codice, "id_fiscale_univoco_cf_piva": id_fiscale},
                    # `emittente_ids=None`: nessun filtro di perimetro, qui si
                    # prova la ricerca e non lo scope.
                    lambda t: ClientiRepository().list_clienti(search=t, emittente_ids=None, limit=500)[0],
                )
                raise Annulla
        except Annulla:
            pass

    def test_soggetti_trova_ogni_colonna_accesa(self):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Soggetto ricragsog')")
                soggetto_id = cur.fetchone()[0]
                cur.execute(
                    "SELECT id_fiscale_univoco_cf_piva FROM anagrafiche.soggetti WHERE id = %s",
                    [soggetto_id],
                )
                id_fiscale = cur.fetchone()[0]
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "anagrafiche.soggetti", soggetto_id,
                    {"ragione_sociale_completa": "ricragsog", "id_fiscale_univoco_cf_piva": id_fiscale},
                    lambda t: SoggettiRepository().list_soggetti(search=t, limit=500)[0],
                )
                raise Annulla
        except Annulla:
            pass

    def test_categorie_clienti_listini_trova_ogni_colonna_accesa(self):
        from apps.anagrafiche.db.categorie_clienti_listini_repository import (
            CategorieClientiListiniRepository,
        )

        try:
            with transaction.atomic(), connection.cursor() as cur:
                # Il mondo apre il contesto sul SUO operatore: il listino e' per
                # costruzione dell'azienda di chi agisce (guard emittente_scope
                # di vendite.listini), quindi nasce PRIMA del contesto di prova.
                cur.execute("SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('ricerca matrice BE')")
                mondo = dict(zip([c.name for c in cur.description], cur.fetchone(), strict=True))
                cur.execute(
                    "SELECT listino_id FROM dbops.fn_pgtap_crea_listino(%s, 'ricdesclst')",
                    [mondo["utility_id"]],
                )
                listino = cur.fetchone()[0]
                cur.execute("SELECT codice FROM vendite.listini WHERE id = %s", [listino])
                listino_codice = cur.fetchone()[0]
                apri_contesto_operatore(cur)
                cur.execute(
                    "INSERT INTO anagrafiche.categorie_clienti (codice, descrizione, codice_interno) "
                    "VALUES ('RICCATLST', 'Categoria ricdesccatl', 'RICCATLST') RETURNING id"
                )
                categoria = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO anagrafiche.categorie_clienti_listini "
                    "       (categoria_cliente_id, utility_id, emittente_soggetto_ruolo_id, listino_id, valido_dal) "
                    "VALUES (%s, %s, %s, %s, script.fn_data_operativa()) RETURNING id",
                    [categoria, mondo["utility_id"], mondo["emittente_soggetto_ruolo_id"], listino],
                )
                riga = cur.fetchone()[0]
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "anagrafiche.categorie_clienti_listini", riga,
                    {"categoria_codice": "riccatlst", "categoria_descrizione": "ricdesccatl",
                     "listino_codice": listino_codice, "listino_descrizione": "ricdesclst"},
                    lambda t: CategorieClientiListiniRepository().list_matrice(search=t, limit=200)[0],
                )
                # ⭐ Da un carattere (matrice di configurazione, Tid 2026-09-24):
                #    con la soglia di default il termine sarebbe ignorato.
                self.assertEqual(CategorieClientiListiniRepository().list_matrice(search="§", limit=200)[0], [])
                raise Annulla
        except Annulla:
            pass

    def test_operatori_trova_ogni_colonna_accesa(self):
        from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute(
                    "SELECT auth_user_id, soggetto_id FROM dbops.fn_pgtap_crea_operatore_umano('ricopcogn')"
                )
                auth_user_id, soggetto_id = cur.fetchone()
                # ⭐ Username ed email con un termine che sta solo li': il builder
                #    li deriva entrambi dal codice fiscale (`pgtap_<cf>`), e
                #    cercare l'uno troverebbe la riga anche per l'altro.
                cur.execute(
                    "UPDATE auth_user SET username = 'ricopuser_' || id, email = 'ricopmail_' || id || '@example.com' "
                    " WHERE id = %s",
                    [auth_user_id],
                )
                cur.execute("SELECT cognome, nome FROM anagrafiche.soggetti WHERE id = %s", [soggetto_id])
                cognome, nome = cur.fetchone()
                # ⚠️ Cognome e nome stanno ANCHE nella ragione sociale completa di
                #    una persona fisica (`cognome || ' ' || nome`, GENERATED): per
                #    una persona le tre colonne non si possono separare.
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "anagrafiche.operatori", auth_user_id,
                    {"soggetto_cognome": cognome, "soggetto_nome": nome,
                     "username": f"ricopuser_{auth_user_id}",
                     "email": f"ricopmail_{auth_user_id}@",
                     "soggetto_ragione_sociale": f"{cognome} {nome}"},
                    lambda t: AmmSoftwareRepository().list_operatori(search=t, limit=500)[0],
                    chiave="auth_user_id",
                )
                raise Annulla
        except Annulla:
            pass
