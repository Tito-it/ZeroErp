# ------------------------------------------------------------
# Collaudo del presidio dei job, fase BE: le corse le scrive il backend vero
# Brief: work-done/brief-db-presidio-job-run-a-chi-tocca §5 («Fasi»), §12
#
# La fase 1 (collaudo-presidio-job-run-prepara.sql) mette nel giornale righe
# scritte a mano: prova la vista, non chi scrive. Qui le tre corse passano da
# `registered_job` sul DB vero, e il controllo legge causa e destinatario dalla
# vista, come fa il digest:
#
#   COLLAUDO-CAUSA-BE-AMBIENTE  §4.2: errore del DB dentro un command, SQLSTATE
#                               57014 (statement_timeout)  → AMBIENTE → SISTEMISTA
#   COLLAUDO-CAUSA-BE-CODICE    §4.2: P0001 col suo codice E_ (quello di
#                               collaudo, che dichiara CONFIGURAZIONE) → AMMINISTRATORE
#   COLLAUDO-CAUSA-BE-D9        D9: elementi non completati, codice senza causa,
#                               decide il processo (PROGRAMMA) → SVILUPPO
#
# Come si lancia (dalla radice, su dbdev):
#   1. psql -X -f docs/it/dev/work-done/allegati/collaudo-presidio-job-run-prepara.sql
#      (crea il processo e il codice di collaudo; serve anche qui)
#   2. backend/manage-env.sh shell < docs/it/dev/work-done/allegati/collaudo-presidio-job-run-be.py
#   3. backend/manage-env.sh digest_presidi --cadenza giornaliera --secco
#      gruppi attesi: sistemista (APPESA, DISCO, BE-AMBIENTE), sviluppo
#      (PROGRAMMA, BE-D9), amministratore (CONFIGURAZIONE, BE-CODICE)
#   4. psql -X -f docs/it/dev/work-done/allegati/collaudo-presidio-job-run-pulisci.sql
#      (toglie anche queste: jobname LIKE 'COLLAUDO-CAUSA-%'). ⚠️ Lo stesso giorno.
#
# ⚠️ Le corse restano nel giornale anche se il controllo non torna: la pulizia
#    si lancia comunque.
# ------------------------------------------------------------
from django.db import connection, transaction

from apps.core.services.job_run import (
    chiudi_se_elementi_non_completati,
    registered_job,
)

PROCESSO = "COLLAUDO-CAUSA"
ATTESE = {
    "COLLAUDO-CAUSA-BE-AMBIENTE": ("57014", "AMBIENTE", "SISTEMISTA"),
    "COLLAUDO-CAUSA-BE-CODICE": ("E_COLLAUDO_CAUSA_CONFIGURAZIONE", "CONFIGURAZIONE", "AMMINISTRATORE"),
    "COLLAUDO-CAUSA-BE-D9": ("E_JOB_ELEMENTI_NON_COMPLETATI", "PROGRAMMA", "SVILUPPO"),
}

with connection.cursor() as c:
    c.execute("SELECT count(*) FROM dbops.processi WHERE codice = %s", [PROCESSO])
    if c.fetchone()[0] != 1:
        raise SystemExit("Manca il processo di collaudo: lanciare prima collaudo-presidio-job-run-prepara.sql")
    c.execute("SELECT count(*) FROM maintenance.job_run_log WHERE jobname LIKE 'COLLAUDO-CAUSA-BE-%%'")
    if c.fetchone()[0]:
        raise SystemExit("Ci sono gia' corse BE di collaudo: lanciare prima la pulizia, poi di nuovo la preparazione")


def corsa(jobname, corpo):
    try:
        with registered_job(jobname, processo_codice=PROCESSO) as job:
            corpo(job)
    except Exception as exc:  # il rosso e' quello che si vuole: lo ha gia' scritto registered_job
        print(f"{jobname}: uscita con {type(exc).__name__}")
    else:
        print(f"{jobname}: ⚠️ uscita VERDE, attesa rossa")


def ambiente(job):
    # SET LOCAL dentro l'atomic: al rollback il tetto sparisce, e fn_job_run_end
    # (stessa connessione) non lo eredita.
    with transaction.atomic(), connection.cursor() as c:
        c.execute("SET LOCAL statement_timeout = '50ms'")
        c.execute("SELECT pg_sleep(1)")


def codice(job):
    with connection.cursor() as c:
        c.execute(
            "DO $$ BEGIN RAISE EXCEPTION 'collaudo: impostazione mancante' "
            "USING ERRCODE = 'P0001', CONSTRAINT = 'E_COLLAUDO_CAUSA_CONFIGURAZIONE'; END $$"
        )


def d9(job):
    job.set_meta({"falliti": ["COLLAUDO-AZ-1", "COLLAUDO-AZ-2"]})
    chiudi_se_elementi_non_completati(job, ["COLLAUDO-AZ-1", "COLLAUDO-AZ-2"], cosa="aziende non accodate")


corsa("COLLAUDO-CAUSA-BE-AMBIENTE", ambiente)
corsa("COLLAUDO-CAUSA-BE-CODICE", codice)
corsa("COLLAUDO-CAUSA-BE-D9", d9)

with connection.cursor() as c:
    c.execute(
        """
        SELECT l.jobname, l.ok, l.error_code, l.sqlstate, v.motivo, v.causa, pc.chi_agisce
          FROM maintenance.job_run_log l
          LEFT JOIN maintenance.vw_job_run_da_guardare v ON v.job_run_id = l.id
          LEFT JOIN dbops.presidi_cause pc
                 ON pc.vista = 'maintenance.vw_job_run_da_guardare' AND pc.causa = v.causa
         WHERE l.jobname LIKE 'COLLAUDO-CAUSA-BE-%%'
         ORDER BY l.jobname
        """
    )
    righe = {r[0]: r for r in c.fetchall()}

sbagliate = 0
for jobname, (atteso, causa, chi) in ATTESE.items():
    r = righe.get(jobname)
    if r is None:
        print(f"❌ {jobname}: nessuna corsa nel giornale")
        sbagliate += 1
        continue
    _, ok, error_code, sqlstate, motivo, v_causa, v_chi = r
    trovato = sqlstate if atteso == "57014" else error_code
    esito = ok is False and trovato == atteso and v_causa == causa and v_chi == chi
    sbagliate += not esito
    print(f"{'✅' if esito else '❌'} {jobname}: ok={ok} error_code={error_code} sqlstate={sqlstate} "
          f"motivo={motivo!r} causa={v_causa} → {v_chi} (atteso {atteso}, {causa} → {chi})")

print("Collaudo BE SUPERATO" if not sbagliate else f"Collaudo BE NON superato: {sbagliate} su {len(ATTESE)}")
