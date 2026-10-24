# ------------------------------------------------------------
# Smoke C-9 «parte alta» — approva -> fattura (giro) -> numera -> stampa (G2)
# Eseguito via `python manage.py shell < smoke_c9_parte_alta.py`.
# Percorso REALE: enqueue identico alle view, drain dai worker systemd
# (zeroerp-coda-lavori / zeroerp-coda-stampa, ogni minuto).
# Verifica di verita' con una seconda connessione (ruolo normale,
# autocommit) che ITERA IL ROSTER degli utenti tecnici: un'azienda alla
# volta, come il lavoro vero. Niente BYPASSRLS — ritirato il 2026-09-05.
#
# ⚠️⚠️ QUESTO SMOKE **NON FA ROLLBACK**, ed e' l'unico della famiglia. Approva
# attivita', emette fatture, consuma progressivi fiscali e accoda stampe: tutto
# persiste. Non e' una svista da sanare — passa dalla coda e dai worker, che
# girano in transazioni proprie in un altro processo, quindi un rollback non e'
# rappresentabile. Lanciarlo equivale a emettere le fatture a mano dalla UI: la
# differenza e' che qui ogni passaggio viene verificato mentre accade.
# Gli smoke rollback-safe sono gli altri (scadenze, indirizzi, aggregazione).
#
# COMPETENZA — parametrica dal 2026-08-03. Default invariato **2026-06**
# (15 attivita' BOZZA da approvare, 37 APPROVATE da emettere), override con:
#
#     SMOKE_C9_COMPETENZA=2026-08-01 ./manage-env.sh shell < scripts/tests/smoke-c9-fatturazione-parte-alta.py
#
# Serviva perche' un mese gia' interamente lavorato fa passare lo smoke a
# VUOTO: il 2026-08-02 e' girato verde con `numerati=0` e `lotti=0` — nessun
# lotto nuovo, guard di numerazione mai invocato. Un verde che non ha
# esercitato niente e' peggio di un rosso, e con la costante cablata l'unico
# modo di accorgersene era leggere i contatori a mano.
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
from apps.core.services.processi import PROCESSO_RUN_FATTURAZIONE_BATCH
from apps.vendite.services.commesse_service import approva_attivita_competenza

# Scopo: Competenza su cui gira lo smoke. Da `SMOKE_C9_COMPETENZA` (ISO
#        `YYYY-MM-DD`), altrimenti il default storico. Il valore viene
#        normalizzato al PRIMO del mese: la competenza e' mensile e passare
#        una data a meta' mese produrrebbe un giro che non trova nulla senza
#        dire perche' — fallire sul formato e' meglio che girare a vuoto.
def _competenza_da_env() -> date:
    raw = (os.environ.get("SMOKE_C9_COMPETENZA") or "").strip()
    if not raw:
        return date(2026, 6, 1)
    try:
        d = date.fromisoformat(raw)
    except ValueError as exc:
        raise SystemExit(
            f"SMOKE_C9_COMPETENZA='{raw}' non e' una data ISO YYYY-MM-DD: {exc}"
        ) from exc
    return d.replace(day=1)


COMPETENZA = _competenza_da_env()
FAIL = []
WARN = []


def check(label, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + label + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(label)


# Scopo: anomalia NON imputabile a questa esecuzione (dato storico incoerente).
#        Visibile e contata, ma non fa fallire lo smoke: il verde deve dipendere
#        dal codice, non dalla bonifica dei dati pregressi.
def warn(label, detail=""):
    print("  WARN " + label + (f" — {detail}" if detail else ""))
    WARN.append(label)


# --- connessione di VERITÀ per gli snapshot -----------------------------
# ⭐ RISCRITTA IL 2026-09-05, col ritiro del ruolo `BYPASSRLS` (R-2).
#
#    Prima apriva una seconda connessione come `zeroerp_batch_fatturazione`, e
#    le ragioni erano DUE — vale la pena tenerle separate, perche' una sola
#    delle due e' sparita:
#      1. ⛔ vedere TUTTI gli emittenti da una sessione sola. Questa NON si fa
#         piu', e non e' una perdita: era il privilegio che il cantiere
#         «nessun processo senza operatore» esiste per togliere;
#      2. ✅ leggere da FUORI la transazione del fixture (`autocommit = True`),
#         cioe' i dati COMMITTATI e non il proprio lavoro in corso. Questa
#         resta necessaria, e non si sostituisce con la connessione Django —
#         quella vedrebbe anche cio' che il fixture ha appena scritto, e lo
#         snapshot «prima» conterebbe cose che non c'erano ancora.
#
# ⇒ La seconda connessione resta, ma sul ruolo NORMALE (`zeroerp_app`, niente
#   bypass) e il conteggio cross-azienda si ottiene ITERANDO IL ROSTER: per ogni
#   utente tecnico di `run_fatturazione_batch` si impostano le sue GUC e si
#   contano le righe che QUELL'AZIENDA vede. La somma e' il totale.
#
# ⭐ E il giro non e' solo un modo diverso di ottenere lo stesso numero: e' la
#   stessa strada che percorre il lavoro vero. Se un badge manca, il conteggio
#   cala — e cala anche la fatturazione di quell'azienda. Prima il bypass
#   nascondeva l'assenza mostrando comunque tutte le righe.
#
# ⚠️ La somma non fa doppioni perche' `config.user_emittenti_fiscali` e' 1-a-1
#    sull'utente (UNIQUE): ogni badge vede un'azienda sola, e gli insiemi sono
#    disgiunti. Non e' un'assunzione di comodo — e' il vincolo su cui poggia
#    tutto il perimetro.
# ⚠️ E la somma copre TUTTO solo finche' `dbops.vw_emittenti_non_serviti` e'
#    vuota. Se un'azienda attiva non ha badge, il suo lavoro non entra in questi
#    conteggi — ma non entra nemmeno in fatturazione, quindi lo smoke misura la
#    stessa cosa che il mondo fa. ⭐ Con il bypass, invece, il conteggio restava
#    completo mentre la fatturazione no: e' la differenza fra osservare da dentro
#    il perimetro e osservare da sopra.
#
# 🔵 NON ANCORA ESEGUITO dopo la riscrittura (2026-09-05): la meta' OSSERVATIVA
#    e' stata provata isolata (roster iterato, somma corretta su `2026-06`), ma
#    il giro completo emette fatture vere — si lancia a mano, quando serve. La
#    riga in `baseline-smoke.tsv` resta finche' qualcuno non lo vede verde:
#    toglierla adesso vorrebbe dire dichiarare un verde mai visto.
_ROSTER_SQL = """
    SELECT auth_user_id, username, identita_id,
           emittente_fiscale_id, emittente_codice
      FROM dbops.vw_processi_roster
     WHERE processo_codice = %s
     ORDER BY emittente_codice
"""
_PROCESSO_OSSERVATO = PROCESSO_RUN_FATTURAZIONE_BATCH

dsn = (
    f"host={os.environ['DB_HOST']} port={os.environ.get('DB_PORT', '5432')} "
    f"dbname={os.environ['DB_NAME']} user={os.environ['DB_USER']} "
    f"password={os.environ['DB_PASSWORD']}"
)
truth = psycopg.connect(dsn)
truth.autocommit = True

with truth.cursor() as _cur:
    _cur.execute(_ROSTER_SQL, [_PROCESSO_OSSERVATO])
    BADGE = _cur.fetchall()

# ⛔ Roster vuoto = nessuna finestra da cui guardare. Si DICHIARA, non si conta
#    zero: uno smoke che osserva da nessuna parte e' verde per sottrazione, che
#    e' peggio di un rosso.
if not BADGE:
    raise SystemExit(
        "SENZA_MATERIA: nessun utente tecnico per "
        f"`{_PROCESSO_OSSERVATO}` in dbops.vw_processi_roster. Senza badge non "
        "c'e' nessuna azienda da cui osservare, e i conteggi sarebbero zero "
        "per assenza di perimetro, non per assenza di dati."
    )

print(
    f"--- osservatori: {len(BADGE)} badge di {_PROCESSO_OSSERVATO} "
    f"({', '.join(b[4] for b in BADGE)})"
)


# Scopo: impone alla connessione di verita' l'identita' di UN badge. Le sei GUC
#        sono le stesse che il middleware JWT scrive nel web
#        (`set_jwt_gucs`): la RLS operatore risolve identica.
# ⚠️ `app.ruolo_applicativo` non e' facoltativo — senza, le policy operatore
#    rispondono ZERO righe a chiunque, e uno zero fail-closed non si distingue
#    da un dato.
def _indossa(badge):
    auth_user_id, username, identita_id, emittente_id, _codice = badge
    with truth.cursor() as cur:
        cur.execute(
            """
            SELECT set_config('app.jwt_user',             %s, false),
                   set_config('app.current_user_id',      %s, false),
                   set_config('app.current_identita_id',  %s, false),
                   set_config('app.ruolo_applicativo',    'OPERATORE', false),
                   set_config('app.soggetto_ruolo_id',
                              COALESCE((SELECT soggetto_ruolo_id::text
                                          FROM anagrafiche.identita_digitali
                                         WHERE id = %s), ''), false),
                   set_config('app.current_emittente_id', %s, false)
            """,
            [str(username), str(auth_user_id), str(identita_id),
             str(identita_id), str(emittente_id)],
        )


def q(sql, params=None):
    with truth.cursor() as cur:
        cur.execute(sql, params or [])
        return cur.fetchall()


# Scopo: somma righe `(chiave..., n...)` provenienti da badge diversi. La chiave
#        e' tutto cio' che precede le colonne numeriche.
# ⚠️ Le chiavi che un'azienda non ha semplicemente non compaiono: si accumulano
#    in un dizionario e si riordina, invece di pretendere che i badge tornino le
#    stesse righe — un'azienda senza fatture non deve far sparire la riga di
#    un'altra.
def _somma(acc, righe, n_chiavi):
    for riga in righe:
        chiave = tuple(riga[:n_chiavi])
        valori = tuple(riga[n_chiavi:])
        precedenti = acc.get(chiave)
        acc[chiave] = (
            valori if precedenti is None
            else tuple(a + b for a, b in zip(precedenti, valori, strict=True))
        )
    return acc


def _righe(acc):
    return [tuple(k) + tuple(v) for k, v in sorted(acc.items(), key=lambda kv: kv[0])]


# Scopo: la fotografia del mese, vista dall'insieme delle aziende servite.
# ⭐ Ogni conteggio e' la somma di cio' che ciascun badge vede nel proprio
#    perimetro: e' la stessa aritmetica che fa il giro di fatturazione.
def snapshot(label):
    att_acc, lotti_acc, fatture_acc, stampa_acc = {}, {}, {}, {}
    for badge in BADGE:
        _indossa(badge)
        _somma(att_acc, q(
            """SELECT stato_approvazione, stato_emissione, count(*)
                 FROM vendite.commesse_attivita WHERE competenza_mese=%s
                 GROUP BY 1,2""",
            [COMPETENZA],
        ), 2)
        _somma(lotti_acc, q(
            """SELECT s.codice, count(*) FROM vendite.fatturazione_lotti l
                 JOIN config.stati_doc_fiscale s ON s.id=l.stato_doc_fiscale_id
                WHERE l.competenza_mese=%s GROUP BY 1""",
            [COMPETENZA],
        ), 1)
        _somma(fatture_acc, q(
            """SELECT s.codice, count(*), count(f.numero) FROM vendite.fatture f
                 JOIN vendite.fatturazione_lotti_fatture lf ON lf.fattura_id=f.id
                 JOIN vendite.fatturazione_lotti l ON l.id=lf.lotto_id
                 LEFT JOIN config.stati_doc_fiscale s ON s.id=f.stato_doc_fiscale_id
                WHERE l.competenza_mese=%s GROUP BY 1""",
            [COMPETENZA],
        ), 1)
        _somma(stampa_acc, q(
            "SELECT stato, count(*) FROM vendite.fatture_stampa_coda GROUP BY 1"
        ), 1)

    att, lotti = _righe(att_acc), _righe(lotti_acc)
    fatture, stampa = _righe(fatture_acc), _righe(stampa_acc)
    print(f"--- snapshot {label} (somma di {len(BADGE)} aziende)")
    print("    attivita (appr, emiss, n):", att)
    print("    lotti giu:", lotti, "| fatture giu (stato, n, con_numero):", fatture)
    print("    coda stampa:", stampa)
    return {"att": att, "lotti": dict(r[:2] for r in lotti), "fatture": fatture,
            "stampa": dict(stampa)}


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


# --- identità operatore (l'utente degli smoke, admin globale) ------------
# Lo stesso utente degli smoke bash: SMOKE_USER (run-book §11), mai scritto a
# mano e senza ripiego, come `_smoke_auth.sh`.
User = get_user_model()
smoke_user = os.environ.get("SMOKE_USER", "").strip()
assert smoke_user, "utente degli smoke non impostato (SMOKE_USER, run-book §11)"
operatore = User.objects.get(username=smoke_user)
rows = q(
    "SELECT id FROM anagrafiche.identita_digitali WHERE auth_user_id=%s AND attivo AND ruolo_applicativo='OPERATORE' ORDER BY id LIMIT 1",
    [operatore.id],
)
assert rows, f"nessuna identita' OPERATORE attiva per {operatore.username}"
identita_id = rows[0][0]
emittente_ids = PermissionResolver.get_emittenti_pk_ids(operatore)
scope_key = scope_key_da_emittenti(emittente_ids)
print(f"identita': auth_user={operatore.id} identita={identita_id} emittenti={emittente_ids} scope_key={scope_key}")

pre = snapshot("PRE")
lotti_pre_ids = {r[0] for r in q("SELECT id FROM vendite.fatturazione_lotti WHERE competenza_mese=%s", [COMPETENZA])}
stampa_pre_ids = {r[0] for r in q("SELECT id FROM vendite.fatture_stampa_coda")}

# --- 1) APPROVA competenza (stesso service della view A-2) --------------
print("== 1) APPROVA competenza", COMPETENZA)
with operator_identity_context(operatore.id, username=operatore.username, identita_id=identita_id):
    esito = approva_attivita_competenza(competenza_mese=COMPETENZA, commessa_ids=None, user=operatore.username)
print("    esito approva:", esito)
bozze_dopo = q(
    "SELECT count(*) FROM vendite.commesse_attivita WHERE competenza_mese=%s AND stato_approvazione='BOZZA'",
    [COMPETENZA],
)[0][0]
check("approva: nessuna attivita' BOZZA residua nel mese", bozze_dopo == 0, f"residue={bozze_dopo}")

# --- 2) GIRO di fatturazione (enqueue identico alla view C-3) -----------
print("== 2) GIRO FATTURAZIONE (enqueue + drain worker systemd)")
scope = {
    "auth_user_id": int(operatore.id),
    "username": str(operatore.username),
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
# La PRESENZA di lotti EMESSA non è un invariante del codice: dipende da quanto
# lavoro resta nel mese. A mese interamente lavorato (tutto già DEFINITIVA) il
# valore corretto è 0 — trattarlo come FAIL renderebbe lo smoke verde solo alla
# PRIMA esecuzione. Fallisce invece il GIRO in sé (già verificato sopra) o la
# presenza di attività emittibili rimaste indietro, che qui viene solo esposta.
if n_emesse > 0:
    check("giro: esistono lotti EMESSA da numerare", True, f"n={n_emesse}")
else:
    residue = q(
        """SELECT count(*) FROM vendite.commesse_attivita
            WHERE competenza_mese=%s AND stato_approvazione='APPROVATA'
              AND stato_emissione <> 'EMESSA'""",
        [COMPETENZA],
    )[0][0]
    bloccati = q(
        """SELECT count(*) FROM vendite.fatturazione_lotti l
             JOIN config.stati_doc_fiscale s ON s.id=l.stato_doc_fiscale_id
            WHERE l.competenza_mese=%s AND s.codice='DRAFT' AND l.stato_lotto='ERRORE'""",
        [COMPETENZA],
    )[0][0]
    if residue or bloccati:
        warn(
            "giro: nessun lotto EMESSA, ma restano attività non emesse",
            f"attivita_approvate_non_emesse={residue}, lotti_DRAFT_in_ERRORE={bloccati} "
            "(dato pregresso da bonificare: le attività sono ferme in quei lotti)",
        )
    else:
        print("    (mese interamente lavorato: nessun lotto da numerare)")

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
    """SELECT f.id, s.codice, f.anno, f.serie, f.numero, lf.lotto_id
         FROM vendite.fatture f
         JOIN vendite.fatturazione_lotti_fatture lf ON lf.fattura_id=f.id
         JOIN vendite.fatturazione_lotti l ON l.id=lf.lotto_id
         LEFT JOIN config.stati_doc_fiscale s ON s.id=f.stato_doc_fiscale_id
        WHERE l.competenza_mese=%s ORDER BY f.id""",
    [COMPETENZA],
)
print("    fatture mese:", rows)

# Esito del job: distingue i lotti NUMERATI in questa passata da quelli
# SALTATI. Un lotto saltato = dato preesistente incoerente (es. lotto EMESSA
# con fatture rimaste DRAFT: la transizione DRAFT→DEFINITIVA non esiste per la
# fattura). NON e' una regressione di questa esecuzione: va segnalato forte
# (WARN + causa) ma non fa fallire lo smoke, altrimenti il verde dipende dalla
# bonifica dei dati storici invece che dal codice.
result_numera = (st or {}).get("result") or {}
saltati_dett = result_numera.get("saltati_dett") or []
lotti_saltati = {int(s["lotto_id"]) for s in saltati_dett if s.get("lotto_id")}
n_numerati = int(result_numera.get("numerati") or 0)
for s in saltati_dett:
    errore = s.get("errore") or {}
    warn(
        f"lotto {s.get('codice')} (id={s.get('lotto_id')}) NON numerato",
        f"motivo_stop={s.get('motivo_stop')} code={errore.get('code')} "
        f"detail={(errore.get('detail') or '').splitlines()[0] if errore.get('detail') else None}",
    )

# Fatture ATTESE numerate = quelle dei lotti non saltati.
attese = [r for r in rows if int(r[5]) not in lotti_saltati]
non_def = [r for r in attese if r[1] != "DEFINITIVA" or r[4] is None]
check(
    "numera: le fatture dei lotti lavorati sono DEFINITIVE e numerate",
    not non_def,
    f"anomale={non_def}",
)
if not attese:
    print("    (nessuna fattura attesa in questa passata: niente da numerare)")
dup = q(
    """SELECT f.anno, f.serie, f.numero, count(*) FROM vendite.fatture f
        WHERE f.numero IS NOT NULL GROUP BY 1,2,3 HAVING count(*) > 1"""
)
check("numera: nessun numero duplicato (anno,serie)", not dup, str(dup))

# --- 4) G2: la DEFINITIVA ha ACCODATO le stampe; il worker le drena -----
print("== 4) STAMPA (G2: accodo automatico in pipeline + drain worker)")
# Attese SOLO per le fatture effettivamente numerate ORA: la DEFINITIVA e' la
# sola che accoda (G2). Se questa passata non ha numerato nulla (mese gia'
# lavorato), non c'e' nulla da attendere — sezione neutra, non un fallimento.
fattura_ids = [r[0] for r in attese]
stampe = []
if n_numerati == 0 or not fattura_ids:
    print(f"    SKIP: nessun lotto numerato in questa passata (numerati={n_numerati}) "
          "→ G2 non deve accodare nulla.")
else:
    t0 = time.monotonic()
    while time.monotonic() - t0 < 300:
        stampe = q(
            """SELECT id, sorgente_id, lotto_id, stato, tentativi, documento_id
                 FROM vendite.fatture_stampa_coda
                WHERE id != ALL(%s) AND sorgente_id = ANY(%s) ORDER BY id""",
            [list(stampa_pre_ids) or [0], fattura_ids],
        )
        if stampe and all(r[3] in ("FATTO", "ERRORE") for r in stampe):
            break
        time.sleep(10)
    print("    righe stampa nuove:", stampe)
    check(
        "G2: stampe accodate dalla pipeline DEFINITIVA",
        len(stampe) > 0,
        f"n={len(stampe)} (attese ~{len(fattura_ids)})",
    )
    err = [r for r in stampe if r[3] != "FATTO"]
    check("stampa: nessuna stampa nuova in errore", not err, f"non FATTO={err}")

# --- 5) PDF su disco, agganciato alla fattura NUMERATA ------------------
print("== 5) VERIFICA PDF")
for _sid, fid, _lotto, _stato, _tent, doc_id in [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in stampe]:
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
if WARN:
    print(f"WARN (dati storici incoerenti, non regressioni): {len(WARN)} -> {WARN}")
if FAIL:
    print(f"SMOKE C-9 PARTE ALTA: {len(FAIL)} FAIL -> {FAIL}")
else:
    print("SMOKE C-9 PARTE ALTA: TUTTO VERDE"
          + (f" ({len(WARN)} warn su dati preesistenti)" if WARN else ""))
truth.close()
