# ------------------------------------------------------------
# Smoke C-9 «parte alta» — approva -> fattura (giro) -> numera -> stampa (G2)
# Eseguito via `python manage.py shell < smoke_c9_parte_alta.py`.
# Percorso REALE: enqueue identico alle view, drain dai worker systemd
# (zeroerp-coda-lavori / zeroerp-coda-stampa, ogni minuto).
# Verifica di verità con connessione BYPASSRLS (ruolo batch) separata.
# Competenza: 2026-06 (15 attivita' BOZZA da approvare, 37 APPROVATE da emettere).
# ------------------------------------------------------------
import os
import time
from datetime import date

import psycopg
from django.contrib.auth import get_user_model

from apps.core.services.coda_lavori.context import operator_identity_context
from apps.core.services.coda_lavori.repository import (
    ORIGINE_API,
    RUN_AS_OPERATORE,
    CodaLavoriRepository,
)
from apps.core.services.coda_lavori.scope import scope_key_da_emittenti
from apps.core.services.permissions_resolver import PermissionResolver
from apps.vendite.services.commesse_service import approva_attivita_competenza

COMPETENZA = date(2026, 6, 1)
FAIL = []


def check(label, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + label + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(label)


# --- connessione di VERITÀ (BYPASSRLS) per gli snapshot -----------------
dsn = (
    f"host={os.environ['DB_HOST']} port={os.environ.get('DB_PORT', '5432')} "
    f"dbname={os.environ['DB_NAME']} user=zeroerp_batch_fatturazione "
    f"password={os.environ['DB_SYSTEM_FATTURAZIONE_PASSWORD']}"
)
truth = psycopg.connect(dsn)
truth.autocommit = True


def q(sql, params=None):
    with truth.cursor() as cur:
        cur.execute(sql, params or [])
        return cur.fetchall()


def snapshot(label):
    att = q(
        """SELECT stato_approvazione, stato_emissione, count(*)
             FROM vendite.commesse_attivita WHERE competenza_mese=%s
             GROUP BY 1,2 ORDER BY 1,2""",
        [COMPETENZA],
    )
    lotti = q(
        """SELECT s.codice, count(*) FROM vendite.fatturazione_lotti l
             JOIN config.stati_doc_fiscale s ON s.id=l.stato_doc_fiscale_id
            WHERE l.competenza_mese=%s GROUP BY 1 ORDER BY 1""",
        [COMPETENZA],
    )
    fatture = q(
        """SELECT s.codice, count(*), count(f.numero) FROM vendite.fatture f
             JOIN vendite.fatturazione_lotti_fatture lf ON lf.fattura_id=f.id
             JOIN vendite.fatturazione_lotti l ON l.id=lf.lotto_id
             LEFT JOIN config.stati_doc_fiscale s ON s.id=f.stato_doc_fiscale_id
            WHERE l.competenza_mese=%s GROUP BY 1 ORDER BY 1""",
        [COMPETENZA],
    )
    stampa = q("SELECT stato, count(*) FROM vendite.fatture_stampa_coda GROUP BY 1 ORDER BY 1")
    print(f"--- snapshot {label}")
    print("    attivita (appr, emiss, n):", att)
    print("    lotti giu:", lotti, "| fatture giu (stato, n, con_numero):", fatture)
    print("    coda stampa:", stampa)
    return {"att": att, "lotti": dict(r[:2] for r in lotti), "fatture": fatture, "stampa": dict(stampa)}


def poll_job(job_id, label, timeout_s=240):
    repo = CodaLavoriRepository()
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        st = repo.get_stato(int(job_id), owner_scope_key=None)
        stato = st["stato"] if st else None
        if stato in ("FATTO", "ERRORE", "ANNULLATO"):
            print(f"    job {job_id} [{label}] -> {stato} result={st.get('result')} err={st.get('ultimo_errore')}")
            return st
        time.sleep(5)
    print(f"    job {job_id} [{label}] TIMEOUT dopo {timeout_s}s")
    return None


# --- identità operatore (tid, admin globale) ----------------------------
User = get_user_model()
tid = User.objects.get(username="tid")
rows = q(
    "SELECT id FROM anagrafiche.identita_digitali WHERE auth_user_id=%s AND attivo AND ruolo_applicativo='OPERATORE' ORDER BY id LIMIT 1",
    [tid.id],
)
assert rows, "nessuna identita' OPERATORE attiva per tid"
identita_id = rows[0][0]
emittente_ids = PermissionResolver.get_emittenti_ids(tid)
scope_key = scope_key_da_emittenti(emittente_ids)
print(f"identita': auth_user={tid.id} identita={identita_id} emittenti={emittente_ids} scope_key={scope_key}")

pre = snapshot("PRE")
lotti_pre_ids = {r[0] for r in q("SELECT id FROM vendite.fatturazione_lotti WHERE competenza_mese=%s", [COMPETENZA])}
stampa_pre_ids = {r[0] for r in q("SELECT id FROM vendite.fatture_stampa_coda")}

# --- 1) APPROVA competenza (stesso service della view A-2) --------------
print("== 1) APPROVA competenza", COMPETENZA)
with operator_identity_context(tid.id, username=tid.username, identita_id=identita_id):
    esito = approva_attivita_competenza(competenza_mese=COMPETENZA, commessa_ids=None, user=tid.username)
print("    esito approva:", esito)
bozze_dopo = q(
    "SELECT count(*) FROM vendite.commesse_attivita WHERE competenza_mese=%s AND stato_approvazione='BOZZA'",
    [COMPETENZA],
)[0][0]
check("approva: nessuna attivita' BOZZA residua nel mese", bozze_dopo == 0, f"residue={bozze_dopo}")

# --- 2) GIRO di fatturazione (enqueue identico alla view C-3) -----------
print("== 2) GIRO FATTURAZIONE (enqueue + drain worker systemd)")
scope = {
    "auth_user_id": int(tid.id),
    "username": str(tid.username),
    "identita_id": identita_id,
    "emittente_ids": emittente_ids,
    "scope_key": scope_key,
}
job_giro = CodaLavoriRepository().accoda(
    job_type="FATTURAZIONE_GIRO",
    payload={"competenza_mese": COMPETENZA.isoformat()},
    run_as=RUN_AS_OPERATORE,
    scope=scope,
    idempotency_key=f"FATTURAZIONE_GIRO:{COMPETENZA.isoformat()}:{scope_key}",
    origine=ORIGINE_API,
)
print("    accodato job giro:", job_giro)
st = poll_job(job_giro, "GIRO")
check("giro: job FATTO", bool(st) and st["stato"] == "FATTO", str(st and st.get("ultimo_errore")))

mid = snapshot("POST-GIRO")
lotti_nuovi = {r[0] for r in q("SELECT id FROM vendite.fatturazione_lotti WHERE competenza_mese=%s", [COMPETENZA])} - lotti_pre_ids
print("    lotti nuovi:", sorted(lotti_nuovi))
n_emesse = q(
    """SELECT count(*) FROM vendite.fatturazione_lotti l JOIN config.stati_doc_fiscale s ON s.id=l.stato_doc_fiscale_id
        WHERE l.competenza_mese=%s AND s.codice='EMESSA'""",
    [COMPETENZA],
)[0][0]
check("giro: esistono lotti EMESSA nel mese", n_emesse > 0, f"n={n_emesse}")

# --- 3) NUMERA di perimetro (enqueue identico alla view C-4) ------------
print("== 3) NUMERA (Rendi definitive) perimetro", COMPETENZA)
job_num = CodaLavoriRepository().accoda(
    job_type="FATTURAZIONE_NUMERA",
    payload={"competenza_mese": COMPETENZA.isoformat()},
    run_as=RUN_AS_OPERATORE,
    scope=scope,
    idempotency_key=f"FATTURAZIONE_NUMERA:{COMPETENZA.isoformat()}:{scope_key}",
    origine=ORIGINE_API,
)
print("    accodato job numera:", job_num)
st = poll_job(job_num, "NUMERA")
check("numera: job FATTO", bool(st) and st["stato"] == "FATTO", str(st and st.get("ultimo_errore")))

# fatture del mese: tutte DEFINITIVE e NUMERATE
rows = q(
    """SELECT f.id, s.codice, f.anno, f.serie, f.numero FROM vendite.fatture f
         JOIN vendite.fatturazione_lotti_fatture lf ON lf.fattura_id=f.id
         JOIN vendite.fatturazione_lotti l ON l.id=lf.lotto_id
         LEFT JOIN config.stati_doc_fiscale s ON s.id=f.stato_doc_fiscale_id
        WHERE l.competenza_mese=%s ORDER BY f.id""",
    [COMPETENZA],
)
print("    fatture mese:", rows)
non_def = [r for r in rows if r[1] != "DEFINITIVA" or r[4] is None]
check("numera: tutte le fatture del mese DEFINITIVE e numerate", len(rows) > 0 and not non_def, f"anomale={non_def}")
dup = q(
    """SELECT f.anno, f.serie, f.numero, count(*) FROM vendite.fatture f
        WHERE f.numero IS NOT NULL GROUP BY 1,2,3 HAVING count(*) > 1"""
)
check("numera: nessun numero duplicato (anno,serie)", not dup, str(dup))

# --- 4) G2: la DEFINITIVA ha ACCODATO le stampe; il worker le drena -----
print("== 4) STAMPA (G2: accodo automatico in pipeline + drain worker)")
fattura_ids = [r[0] for r in rows]
t0 = time.monotonic()
stampe = []
while time.monotonic() - t0 < 300:
    stampe = q(
        """SELECT id, sorgente_id, lotto_id, stato, tentativi, documento_id
             FROM vendite.fatture_stampa_coda
            WHERE id != ALL(%s) AND sorgente_id = ANY(%s) ORDER BY id""",
        [list(stampa_pre_ids) or [0], fattura_ids or [0]],
    )
    if stampe and all(r[3] in ("FATTO", "ERRORE") for r in stampe):
        break
    time.sleep(10)
print("    righe stampa nuove:", stampe)
check("G2: stampe accodate dalla pipeline DEFINITIVA", len(stampe) > 0, f"n={len(stampe)} (attese ~{len(fattura_ids)})")
err = [r for r in stampe if r[3] != "FATTO"]
check("stampa: tutte le stampe nuove FATTO", bool(stampe) and not err, f"non FATTO={err}")

# --- 5) PDF su disco, agganciato alla fattura NUMERATA ------------------
print("== 5) VERIFICA PDF")
for sid, fid, lotto, stato, tent, doc_id in [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in stampe]:
    if doc_id is None:
        check(f"doc fattura {fid}", False, "documento_id NULL")
        continue
    frow = q(
        """SELECT dgf.storage_key, dgf.file_name FROM documenti.documenti_generati_file dgf
            WHERE dgf.documento_id=%s ORDER BY dgf.id DESC LIMIT 1""",
        [doc_id],
    )
    if not frow:
        check(f"doc {doc_id} fattura {fid}: riga file presente", False, "nessuna riga documenti_generati_file")
        continue
    storage_key, fname = frow[0]
    from django.conf import settings

    path = os.path.join(settings.DOCUMENTI_STORAGE_ROOT, storage_key)
    ok = os.path.isfile(path) and os.path.getsize(path) > 1000
    check(
        f"doc {doc_id} fattura {fid}: PDF su disco",
        ok,
        f"{path} ({os.path.getsize(path) if os.path.isfile(path) else 'assente'} byte)",
    )

post = snapshot("POST")
print()
print("=" * 60)
if FAIL:
    print(f"SMOKE C-9 PARTE ALTA: {len(FAIL)} FAIL -> {FAIL}")
else:
    print("SMOKE C-9 PARTE ALTA: TUTTO VERDE")
truth.close()
