# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL CANCELLO DEL TERZO LATO — ogni codice `E_*` che una funzione
#        PL/pgSQL viva puo' nominare deve avere una voce in `error_policies.py`.
#        Risposta al brief `brief-db-be-terzo-lato-presidio-codici.md` §4 punto 2.
#
#        PERCHE' ESISTE. Sui codici errore devono andare d'accordo tre elenchi:
#        il catalogo `config.messaggi_errore`, i codici usati dal codice Python,
#        e la tabella che dice per ogni codice CHE TIPO di risposta dare
#        (404/403/409/400). Due accordi erano gia' presidiati — i codici usati
#        dal Python (`test_error_codes_declared_guardrail`, il gemello qui
#        accanto) e i codici sollevati dal DB contro il catalogo (guardrail SQL
#        lato DB). Il terzo — **i codici sollevati dal DB contro
#        `error_policies.py`** — non lo guardava nessuno, ed e' da li' che sono
#        passati 141 codici e, prima di loro, i nove delle guard di cambio stato.
#
#        Effetto del difetto: l'operatore legge comunque la frase giusta (viene
#        dal catalogo), ma il TIPO di risposta resta appiattito su 400 anche
#        quando la verita' e' 404 o 403 — e chi deve REAGIRE (la pagina che
#        decide se riportarti indietro, un allarme, un ritentativo) non puo'.
#
#        PERCHE' LATO BE E NON LATO DB (brief §5). Il confronto e' contro un
#        dizionario Python: da SQL si potrebbe fare solo leggendo il *testo* di
#        `error_policies.py`, legando un guardrail SQL alla forma di un sorgente
#        Python. Qui invece il dizionario si interroga per quello che e'
#        (`ErrorPolicyRegistry.has`), e un rinominio si vede subito.
#
#        LA MISURA E' UNA SOLA, E STA NEL DB. `dbops.vw_codici_errore_da_dichiarare`.
#        Non si riscrive qui il regex su `pg_proc`: tre misure diverse dello
#        stesso fatto (133 / 141 / 137) sono gia' costate una giornata di
#        riconciliazione, e la piu' «raffinata» era la sbagliata.
#
#        ⚠️ RICHIEDE IL DB VERO, come i tre e2e di
#        `services/test_db_error_fields.py`: stessa opt-in `ZEROERP_TEST_DB_E2E=1`
#        (accesa in CI da `ci-validate.yaml`, dove il database e' appena stato
#        provvisto da Liquibase) e stesso guard sullo schema in `setUpClass`.
#        Vedi la nota in `.codex/AGENTS.md` §Regole test Django.
#
#        ⚠️ NON SCRIVE NULLA. La connessione e' quella configurata — cioe' il
#        database di sviluppo: qui si legge soltanto.
# ------------------------------------------------------------

"""Indice test previsti (tutti opt-in `ZEROERP_TEST_DB_E2E=1`).

 1) test_nessun_codice_nuovo_senza_policy
       verso 1 — un codice che il DB puo' nominare, senza policy e non nel
       registro: e' il 142esimo, quello nuovo. Rosso.
 2) test_registro_non_contiene_codici_gia_risolti
       verso 2 — una voce del registro che ha OTTENUTO la sua policy: la riga
       va tolta dal CSV. Senza questo verso il registro puo' solo allungarsi.
 3) test_registro_non_contiene_codici_che_il_db_non_nomina_piu
       verso 3 — una voce del registro che nessuna funzione viva nomina piu'
       (codice ritirato o rinominato): riga orfana, va tolta dal CSV.
 4) test_la_misura_non_e_degradata
       sanity — vista e registro non vuoti, dizionario policy non vuoto: senza,
       una misura che si rompe rende il cancello silenziosamente verde.
"""

from __future__ import annotations

from unittest import TestCase

from apps.core.services.error_policies import ErrorPolicyRegistry

# Prerequisito condiviso con i tre e2e di `services/test_db_error_fields.py`: e'
# lo stesso (un database con lo schema Liquibase completo), quindi sta in un
# posto solo — flag inclusa, che altrimenti sarebbe un secondo interruttore da
# ricordarsi di accendere in CI.
from apps.core.tests.db_e2e import richiedi_db_provvisto

# La misura canonica e il registro del debito, entrambi lato DB.
_VISTA = "dbops.vw_codici_errore_da_dichiarare"
_REGISTRO = "dbops.codici_errore_senza_policy"


class ErrorCodesDbPolicyGuardrail(TestCase):
    """Il terzo lato: i codici che il database dice, contro le policy del backend.

    ⚠️ **Salta se lo schema non c'e', fallisce se c'e' ma manca il presidio.**
    La distinzione e' il punto delicato di questo file, e va tenuta:

    * database usa-e-getta creato dal runner (lo schema Liquibase non c'e'
      affatto) -> **skip**. E' la stessa situazione descritta in
      `brief-be-e2e-db-error-fields-skip-schema.md`: senza questo ramo il
      cancello fallirebbe addosso a chi ha scritto il primo test che dichiara un
      database, in una PR che non c'entra niente;
    * schema Liquibase presente ma vista o registro assenti -> **errore**, non
      skip. Li' il presidio c'e' e non e' stato applicato: un cancello che in
      quel caso tacesse sarebbe l'etichetta rassicurante di cui parla la guida
      dei presidi — la cosa peggiore che si possa mettere in un registro.
    """

    vista: dict[str, dict]
    registro: dict[str, bool]

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # Flag spenta, DB irraggiungibile o schema Liquibase assente -> skip.
        # E' la meta' "ambientale" del guard, condivisa con gli e2e.
        richiedi_db_provvisto()

        from django.db import connection

        with connection.cursor() as cur:
            # Schema presente: da qui in poi l'assenza degli oggetti del presidio
            # e' un difetto, non una condizione ambientale — quindi si fallisce.
            cur.execute(
                "SELECT to_regclass(%s) IS NOT NULL, to_regclass(%s) IS NOT NULL",
                [_VISTA, _REGISTRO],
            )
            row = cur.fetchone()
            assert row is not None
            if not (row[0] and row[1]):
                raise AssertionError(
                    f"schema Liquibase presente ma il presidio del terzo lato no: "
                    f"vista={_VISTA} {'ok' if row[0] else 'MANCANTE'}, "
                    f"registro={_REGISTRO} {'ok' if row[1] else 'MANCANTE'}. "
                    "Applicare i changeSet 20260805-35/36/37."
                )

            cur.execute(
                f"SELECT codice, da_trigger, n_funzioni, funzioni FROM {_VISTA}"
            )
            cls.vista = {
                r[0]: {"da_trigger": r[1], "n_funzioni": r[2], "funzioni": r[3]}
                for r in cur.fetchall()
            }

            cur.execute(f"SELECT codice, da_trigger FROM {_REGISTRO}")
            cls.registro = {r[0]: r[1] for r in cur.fetchall()}

    # Scopo: verso 1 — il 142esimo codice. Un codice che una funzione PL/pgSQL
    #        viva puo' nominare, senza policy e non nel registro del debito, e'
    #        un codice NUOVO che si sta sfilando: da qui in avanti il debito puo'
    #        solo calare.
    def test_nessun_codice_nuovo_senza_policy(self):
        mancanti = {
            codice: dati
            for codice, dati in self.vista.items()
            if not ErrorPolicyRegistry.has(codice) and codice not in self.registro
        }
        if mancanti:
            # I da_trigger per primi: stanno sul percorso di una richiesta vera,
            # quindi il loro tipo di risposta lo legge davvero qualcuno.
            righe = "\n".join(
                f"  - {codice}{'  [da trigger]' if dati['da_trigger'] else ''}"
                f"  ({dati['funzioni']})"
                for codice, dati in sorted(
                    mancanti.items(), key=lambda kv: (not kv[1]["da_trigger"], kv[0])
                )
            )
            self.fail(
                f"{len(mancanti)} codici errore che il database puo' nominare non "
                f"hanno una policy in error_policies.py e non sono nel registro "
                f"del debito {_REGISTRO}:\n{righe}\n\n"
                "Dichiarali in error_policies.py decidendo il TIPO di risposta "
                "(404 non esiste / 403 non permesso / 409 conflitto di stato / "
                "400 richiesta malformata). Il registro NON va allungato: "
                "fotografa il debito del 2026-08-05 e deve calare."
            )

    # Scopo: verso 2 — la riga da togliere. Una voce del registro che nel
    #        frattempo ha ottenuto la sua policy deve uscire dal CSV, altrimenti
    #        il registro puo' solo allungarsi e torna a essere un elenco di
    #        eccezioni.
    def test_registro_non_contiene_codici_gia_risolti(self):
        risolti = sorted(c for c in self.registro if ErrorPolicyRegistry.has(c))
        if risolti:
            righe = "\n".join(f"  - {c}" for c in risolti)
            self.fail(
                f"{len(risolti)} voci del registro {_REGISTRO} hanno ottenuto la "
                f"loro policy: vanno TOLTE dal registro.\n{righe}\n\n"
                "Togliere le righe da "
                "db/changelog/migrations_v2/80_data/sql/dbops/"
                "codici_errore_senza_policy.csv (mirror DELETE + loadData: basta "
                "togliere la riga) e chiedere al team DB di riapplicare il "
                "changeSet 20260805-37."
            )

    # Scopo: verso 3 — la riga orfana. Un codice del registro che nessuna
    #        funzione viva nomina piu' (ritirato, rinominato, o la funzione non
    #        c'e' piu') e' debito gia' pagato che nessuno ha registrato: se
    #        restasse, il registro conterebbe piu' di quanto deve davvero.
    def test_registro_non_contiene_codici_che_il_db_non_nomina_piu(self):
        orfani = sorted(c for c in self.registro if c not in self.vista)
        if orfani:
            righe = "\n".join(f"  - {c}" for c in orfani)
            self.fail(
                f"{len(orfani)} voci del registro {_REGISTRO} non sono piu' "
                f"nominate da nessuna funzione PL/pgSQL viva (codice ritirato o "
                f"rinominato): il debito e' gia' pagato, la riga va TOLTA dal "
                f"CSV.\n{righe}"
            )

    # Scopo: sanity della misura. Una vista che tornasse vuota, o un dizionario
    #        policy che non si legge, renderebbero i tre versi sopra
    #        silenziosamente verdi — cioe' il modo in cui un presidio muore
    #        senza che nessuno se ne accorga.
    def test_la_misura_non_e_degradata(self):
        self.assertGreater(
            len(self.vista), 300, f"{_VISTA} sospetta: la misura sembra degradata"
        )
        self.assertGreater(
            len(ErrorPolicyRegistry.codici_registrati()),
            400,
            "registro policy sospetto: estrazione o import falliti",
        )
        # Il registro puo' arrivare a zero — e' l'obiettivo — ma ogni sua voce
        # deve essere un codice conforme, altrimenti si sta sovrapponendo al
        # registro dei codici fuori convenzione (dbops.messaggi_errore_codici_legacy).
        non_conformi = sorted(c for c in self.registro if not c.startswith("E_"))
        self.assertEqual(
            non_conformi, [], f"codici fuori convenzione nel registro {_REGISTRO}"
        )
