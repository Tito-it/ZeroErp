# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio della MISURA di copertura della doc API
#        (`copertura_doc_api`), sulle trappole che l'hanno gia' fatta sbagliare.
#
#        ⭐ PERCHE' UN TEST SU UNA MISURA. Il 2026-09-12, rimisurando la
#        copertura a 24 giorni dal brief, il conto era sbagliato NEI DUE VERSI
#        insieme: sei rotte con la pagina gia' scritta risultavano scoperte
#        (la pagina le citava senza lo slash iniziale — trappola 7) e nove
#        rotte che NESSUNA pagina nominava risultavano documentate (una
#        citazione di soli segnaposto, `/api/v1/vendite/<dominio>/{id}/`,
#        col jolly copriva tutto — trappola 8). ⛔ Il secondo verso e' quello
#        che non si vede mai: una rotta nuova nasceva gia' «documentata».
#
#        ⚠️ I casi sono COSTRUITI, non letti dalla doc di oggi: una prova che
#        confronta la misura con la documentazione corrente passerebbe a vuoto
#        il giorno in cui qualcuno riscrive la pagina che la faceva sbagliare.
#
# ⚠️ NON SERVE IL DATABASE ne' il resolver: si provano le funzioni pure del
#    command e la lettura delle citazioni su un `docs/` temporaneo.
# ------------------------------------------------------------
"""Indice test (0..N):

0. test_il_segnaposto_di_risorsa_si_distingue_dall_identificativo
   `<dominio>` vale `{*}`, `<pratica_id>`/`<int:id>`/`{pk}` valgono `{}`.
   E' la differenza su cui poggia la trappola 8.

1. test_norma_toglie_prefisso_e_punto_di_prosa
   `/api/v1/core/...` e' un prefisso e `…/utility/.` ha un punto di prosa in
   coda: nessuno dei due e' un segmento, e prima erano due falsi fantasmi.

2. test_una_citazione_senza_nomi_non_documenta_niente
   Trappola 8, nei tre casi che la decidono: la `{*}` condanna, la sintesi
   base+coda condanna, il dettaglio radice citato per intero si salva.

3. test_la_citazione_generica_non_copre_la_rotta
   Il matcher, sul caso reale: `/api/v1/vendite/{*}/{}` non copre
   `famiglie/{}`, mentre `/api/v1/vendite/{*}/{}/documenti` copre
   `ordini/{}/documenti` — il jolly della trappola 2 resta.

4. test_il_path_nel_blocco_di_codice_senza_slash_conta
   Trappola 7: la tabella con la base nell'intestazione e i path nudi
   (`soggetti/{soggetto_id}/titoli-iva/`, `GET processi/`) documenta.

5. test_la_coda_di_soli_segnaposto_non_si_attacca_alla_base
   `400/409/404` in un blocco di codice diventa `/{}/{}/{}` e NON deve
   coprire ogni rotta a tre segmenti sotto la base. Il singolo `/{id}/` si'.

6. test_la_forma_troncata_vale_sul_path_della_stessa_riga
   ``GET /api/v1/vendite/lotti/<id>/gruppi/ (+ `/export/`)`` documenta
   anche `…/gruppi/export/`, che una base corta del file non raggiunge.

7. test_l_alternanza_nelle_graffe_e_un_segnaposto
   `{approva,rifiuta}-prezzo` copre entrambe le rotte e non e' un fantasma
   troncato alla virgola.

8. test_la_lapide_in_prosa_non_e_una_citazione
   «il vecchio path `/api/v1/auth/token/`» non conta come citazione
   assoluta: e' una lapide, come la riga marcata `⛔`.

9. test_i_puntini_valgono_un_prefisso_qualunque_della_stessa_area
   La quinta forma, `.../{titolo_id}/ambiti/`: copre la rotta della SUA
   area qualunque sia il prefisso, e non una rotta di un'altra area che
   finisce allo stesso modo.

10. test_un_codice_al_posto_del_segnaposto_non_e_un_fantasma (2026-10-21)
   `ruoli/cl/config-resolver` e' un'istanza di `ruoli/{}/config-resolver`:
   servita, ma NON copre la rotta (un esempio non la documenta).

11. test_la_riga_che_dichiara_di_non_documentare_non_copre (2026-10-21)
   «queste rotte non sono documentate» nomina i path apposta: contarla
   come copertura era il verso permissivo.

12. test_le_lapidi_scritte_bene_si_riconoscono (2026-10-21)
   Titolo barrato, «ritirato», «esistevano»: lapidi, non fantasmi.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.management.commands import copertura_doc_api as cmd


# Scopo: scrive `nome.md` con `testo` in una cartella temporanea e legge le
#        citazioni da li', al posto di `docs/it/backend`.
def _citazioni_da(testo: str, nome: str = "api_x.md"):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / nome).write_text(testo, encoding="utf-8")
        with patch.object(cmd, "DOCS", Path(d)):
            return cmd.leggi_citazioni()


class CoperturaDocApiTests(SimpleTestCase):
    # Scopo: test 0 — i due segnaposto.
    def test_il_segnaposto_di_risorsa_si_distingue_dall_identificativo(self):
        self.assertEqual(cmd.norma("/api/v1/vendite/<dominio>/{id}/"), "/api/v1/vendite/{*}/{}")
        self.assertEqual(cmd.norma("/api/v1/pratiche/<pratica_id>/"), "/api/v1/pratiche/{}")
        self.assertEqual(cmd.norma("/api/v1/x/<int:pk>/<uuid:uid>/{codice}/"), "/api/v1/x/{}/{}/{}")

    # Scopo: test 1 — prefisso e punto di prosa.
    def test_norma_toglie_prefisso_e_punto_di_prosa(self):
        self.assertEqual(cmd.norma("/api/v1/core/..."), "/api/v1/core")
        self.assertEqual(
            cmd.norma("/api/v1/vendite/listini/tipologie/."), "/api/v1/vendite/listini/tipologie"
        )
        self.assertEqual(cmd.norma("/api/v1/vendite/<dominio>/..."), "/api/v1/vendite/{*}")

    # Scopo: test 2 — la regola della trappola 8, caso per caso.
    def test_una_citazione_senza_nomi_non_documenta_niente(self):
        self.assertTrue(cmd.generica("/api/v1/vendite/{*}", assoluta=True))
        self.assertTrue(cmd.generica("/api/v1/vendite/{*}/{}", assoluta=True))
        # Sintetizzata da base + `/{id}/`: non l'ha scritta la doc.
        self.assertTrue(cmd.generica("/api/v1/vendite/{}", assoluta=False))
        # Il dettaglio radice di un'area, citato per intero con un identificativo.
        self.assertFalse(cmd.generica("/api/v1/pratiche/{}", assoluta=True))
        # Nomina un segmento: il jolly della trappola 2 e' legittimo.
        self.assertFalse(cmd.generica("/api/v1/vendite/{*}/{}/documenti", assoluta=True))
        # Fuori da `/api/` la regola non si applica.
        self.assertFalse(cmd.generica("/{}/{}", assoluta=False))

    # Scopo: test 3 — il matcher sul caso reale del 2026-09-12.
    def test_la_citazione_generica_non_copre_la_rotta(self):
        tutte = {
            "/api/v1/vendite/{*}/{}": {"api_documenti_per_sorgente.md"},
            "/api/v1/vendite/{*}/{}/documenti": {"api_documenti_per_sorgente.md"},
            "/api/v1/pratiche/{}": {"api_pratica_detail.md"},
        }
        coperta = cmd.matcher_copertura(tutte, dict(tutte))
        self.assertFalse(coperta("/api/v1/vendite/famiglie/{}"))
        self.assertFalse(coperta("/api/v1/vendite/famiglie/lookup"))
        self.assertTrue(coperta("/api/v1/vendite/ordini/{}/documenti"))
        self.assertTrue(coperta("/api/v1/pratiche/{}"))

    # Scopo: test 4 — la quarta forma di citazione.
    def test_il_path_nel_blocco_di_codice_senza_slash_conta(self):
        tutte, _ = _citazioni_da(
            "| Metodo | Path (sotto `/api/v1/anagrafiche/`) |\n"
            "| `GET`/`POST` | `soggetti/{soggetto_id}/titoli-iva/` |\n"
            "| `GET` | `titoli-iva/sfondati/` |\n"
            "Le rotte (`GET processi/`, `GET processi/{codice}/`) stanno sotto "
            "`/api/v1/amm-software/processi/presidi/`.\n"
        )
        coperta = cmd.matcher_copertura(tutte, {})
        self.assertTrue(coperta("/api/v1/anagrafiche/soggetti/{}/titoli-iva"))
        self.assertTrue(coperta("/api/v1/anagrafiche/titoli-iva/sfondati"))
        self.assertTrue(coperta("/api/v1/amm-software/processi"))
        self.assertTrue(coperta("/api/v1/amm-software/processi/{}"))

    # Scopo: test 5 — la spazzatura che la trappola 7 rischiava di far entrare.
    def test_la_coda_di_soli_segnaposto_non_si_attacca_alla_base(self):
        tutte, _ = _citazioni_da(
            "Vedi `/api/v1/vendite/lotti/{id}/`.\n"
            "Risponde `400/409/404` a seconda del caso.\n"
            "Il dettaglio e' `GET /<id>/`.\n"
        )
        coperta = cmd.matcher_copertura(tutte, {"/api/v1/vendite/lotti/{}": set()})
        self.assertFalse(coperta("/api/v1/vendite/lotti/{}/task-runs/export"))
        self.assertFalse(coperta("/api/v1/vendite/lotti/{}/segnalazioni/rows"))
        # Il singolo `/{id}/` resta: e' il dettaglio della base.
        self.assertTrue(coperta("/api/v1/vendite/lotti/{}"))

    # Scopo: test 6 — la base di riga per la forma troncata.
    def test_la_forma_troncata_vale_sul_path_della_stessa_riga(self):
        tutte, _ = _citazioni_da(
            "`GET /api/v1/vendite/lotti/<id>/gruppi/` (+ `/export/?formato=csv|xlsx`).\n"
        )
        coperta = cmd.matcher_copertura(tutte, {})
        self.assertTrue(coperta("/api/v1/vendite/lotti/{}/gruppi"))
        self.assertTrue(coperta("/api/v1/vendite/lotti/{}/gruppi/export"))

    # Scopo: test 7 — l'alternanza fra graffe.
    def test_l_alternanza_nelle_graffe_e_un_segnaposto(self):
        tutte, assolute = _citazioni_da(
            "| `/api/v1/vendite/eccezioni-offerta/{riga_id}/{approva,rifiuta}-prezzo/` |\n"
        )
        self.assertIn("/api/v1/vendite/eccezioni-offerta/{}/{}-prezzo", assolute)
        coperta = cmd.matcher_copertura(tutte, assolute)
        self.assertTrue(coperta("/api/v1/vendite/eccezioni-offerta/{}/approva-prezzo"))
        self.assertTrue(coperta("/api/v1/vendite/eccezioni-offerta/{}/rifiuta-prezzo"))
        # Non deve esistere il troncone alla virgola.
        self.assertNotIn("/api/v1/vendite/eccezioni-offerta/{}/{approva", assolute)

    # Scopo: test 8 — la lapide in prosa.
    def test_la_lapide_in_prosa_non_e_una_citazione(self):
        _, assolute = _citazioni_da(
            "Il vecchio path `/api/v1/auth/token/` e' stato tolto.\n"
            "⛔ `/api/v1/vendite/listini/test-prezzo/` non esiste piu'.\n"
            "Resta `/api/v1/admin/token/`.\n"
        )
        self.assertNotIn("/api/v1/auth/token", assolute)
        self.assertNotIn("/api/v1/vendite/listini/test-prezzo", assolute)
        self.assertIn("/api/v1/admin/token", assolute)

    # Scopo: test 9 — la quinta forma, coi puntini ASCII.
    def test_i_puntini_valgono_un_prefisso_qualunque_della_stessa_area(self):
        tutte, _ = _citazioni_da(
            "| Path (sotto `/api/v1/anagrafiche/`) |\n"
            "| `GET`/`POST` | `.../{titolo_id}/ambiti/` |\n"
            "| `POST` | `…/{titolo_id}/movimenti/{movimento_id}/annulla/` |\n"
        )
        coperta = cmd.matcher_copertura(tutte, {})
        self.assertTrue(coperta("/api/v1/anagrafiche/soggetti/{}/titoli-iva/{}/ambiti"))
        self.assertTrue(
            coperta("/api/v1/anagrafiche/soggetti/{}/titoli-iva/{}/movimenti/{}/annulla")
        )
        # Stessa coda, altra area: i puntini non escono dall'area del file.
        self.assertFalse(coperta("/api/v1/vendite/contratti/{}/ambiti"))
        # E un troncone di soli segnaposto resta niente.
        tutte, _ = _citazioni_da("Base `/api/v1/vendite/`, poi `.../{id}/`.\n")
        self.assertFalse(cmd.matcher_copertura(tutte, {})("/api/v1/vendite/ordini/{}"))
        # Un segmento solo (`…/export/`) e' una frase, non una citazione: vale
        # sulla base della RIGA, non su tutta l'area.
        tutte, _ = _citazioni_da(
            "Il path e' `…/export/` in coda alla lista (`/api/v1/vendite/`).\n"
            "`GET /api/v1/vendite/resi/da-accreditare/` (+ `…/export/`).\n"
        )
        coperta = cmd.matcher_copertura(tutte, {})
        self.assertTrue(coperta("/api/v1/vendite/resi/da-accreditare/export"))
        self.assertFalse(coperta("/api/v1/vendite/lotti/{}/fatture/export"))

    # Scopo: test 10 — l'esempio con un codice concreto.
    def test_un_codice_al_posto_del_segnaposto_non_e_un_fantasma(self):
        rotte = {"/api/v1/anagrafiche/ruoli/{}/config-resolver": ("", ["GET"])}
        servita = cmd.matcher_servita(rotte)
        self.assertTrue(servita("/api/v1/anagrafiche/ruoli/cl/config-resolver"))
        self.assertFalse(servita("/api/v1/anagrafiche/ruoli/cl/altro"))
        # ⛔ Ma solo col valore del CONVERTER: un nome letterale al posto di un
        #    `<int:pk>` resta un fantasma (un endpoint ritirato col suo nome).
        rotte = {"/api/v1/vendite/ordini/{}": ("/api/v1/vendite/ordini/<int:pk>/", ["GET"])}
        servita = cmd.matcher_servita(rotte)
        self.assertTrue(servita("/api/v1/vendite/ordini/42"))
        self.assertFalse(servita("/api/v1/vendite/ordini/esporta"))
        tutte, assolute = _citazioni_da("Esempio: `/api/v1/anagrafiche/ruoli/CL/config-resolver/`.\n")
        self.assertFalse(
            cmd.matcher_copertura(tutte, assolute)("/api/v1/anagrafiche/ruoli/{}/config-resolver"),
        )

    # Scopo: test 11 — la nota che dichiara di non documentare.
    def test_la_riga_che_dichiara_di_non_documentare_non_copre(self):
        tutte, assolute = _citazioni_da(
            "Queste rotte non sono documentate: `/api/v1/amm-software/processi/{codice}/run/`.\n"
            "Documentata: `/api/v1/amm-software/processi/{codice}/accensione/`.\n"
        )
        coperta = cmd.matcher_copertura(tutte, assolute)
        self.assertFalse(coperta("/api/v1/amm-software/processi/{}/run"))
        self.assertTrue(coperta("/api/v1/amm-software/processi/{}/accensione"))
        # Non e' nemmeno un fantasma: la citazione resta fra le assolute, e la
        # rotta esiste.
        self.assertIn("/api/v1/amm-software/processi/{}/run", assolute)

    # Scopo: test 12 — le lapidi come la doc le scrive davvero.
    def test_le_lapidi_scritte_bene_si_riconoscono(self):
        _, assolute = _citazioni_da(
            "### 1.6 ~~POST /api/v1/amm-software/operatori/{id}/riattiva/~~ -- Ritirato\n"
            "Il lookup `/api/v1/amm-software/lookup/email-log-stati/` e' ritirato.\n"
            "Pre-§8.3: esistevano solo `POST /api/v1/auth/token/` e `/refresh/`.\n"
            "Vivo: `/api/v1/admin/token/`.\n"
        )
        self.assertEqual(sorted(assolute), ["/api/v1/admin/token"])

