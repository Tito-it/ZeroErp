# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Smoke — CONTATORE NOTE del dettaglio fattura (badge del drawer) sul percorso
#         REALE: `get_fattura_dettaglio` -> `PartitionedNoteService.count_per_target`.
# Uso:    ./manage-env.sh shell < scripts/tests/smoke-fattura-contatore-note.py
# ------------------------------------------------------------
#
# PERCHE' ESISTE. I test del service sono mockati (girano senza DB, come da
# regole CI): la query `COUNT(*) FROM vendite.note_fatture WHERE target_tipo=%s
# AND target_id=%s` non e' esercitata da nessuno di essi. Un nome di partizione
# sbagliato scoppierebbe solo a runtime, all'apertura del drawer.
#
# COSA PRESIDIA (oltre al fatto che la query giri):
#   - il **perimetro** del contatore == quello della lista note esposta dall'API
#     (caso 5). Se qualcuno cambiasse il default di `include_invisible`, il badge
#     mostrerebbe un numero e il sub-drawer un altro: il badge "salterebbe" al
#     primo salvataggio. Nessun test unitario puo' vederlo (sono due percorsi
#     mockati separatamente);
#   - il **cancello di scope davanti al conteggio** (caso 6): `note_fatture` NON
#     ha policy RLS, quindi il COUNT su una fattura fuori scope risponderebbe
#     («esiste e ha N note»). L'unica difesa e' l'ordine delle letture nel
#     service.
#
# IDEMPOTENZA. Tutto dentro una transazione con `set_rollback(True)` finale: la
# nota creata per il caso 4 non persiste. Rieseguibile all'infinito.
#
# Indice test (1..6):
#   1  count_per_target esegue sulla partizione reale
#   2  `contatori` presente nel payload del dettaglio
#   3  contatori.note coincide con la lettura diretta
#   4  il contatore e' vivo: una nota reale lo fa salire di 1
#   5  perimetro allineato: nota invisibile contata come nella lista API
#   6  senza contesto operatore -> 404 (il cancello precede il conteggio)
# ------------------------------------------------------------

from django.db import connection, transaction

from apps.core.services.partitioned_note_service import PartitionedNoteService
from apps.core.services.service_errors import ServiceError
from apps.vendite.db.note_repositories import NOTE_REPO_FATTURA
from apps.vendite.services.vendite_service import get_fattura_dettaglio
from scripts.tests._smoke_contesto import apri_contesto_smoke

note_svc = PartitionedNoteService(repo=NOTE_REPO_FATTURA)

FAIL: list[str] = []


# Scopo: Registra ed emette l'esito di una singola asserzione dello smoke.
def check(label, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + label + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(label)


print("\n=== SMOKE contatore note dettaglio fattura (badge drawer) ===\n")

with transaction.atomic():
    with connection.cursor() as cur:
        # Contesto operatore: `vendite.fatture` e' RLS. Senza GUC la testata
        # non si legge e lo smoke misurerebbe il nulla.
        auth_user_id = apri_contesto_smoke(cur)
        cur.execute("SELECT id FROM vendite.fatture ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            raise SystemExit("Nessuna fattura: smoke impossibile.")
        fattura_id = row[0]

    print(f"fattura {fattura_id}, operatore auth_user_id={auth_user_id}\n")

    # 1) il COUNT gira davvero sulla partizione (nome tabella/colonne reali)
    base = note_svc.count_per_target(target_id=fattura_id)
    check("1) count_per_target esegue sulla partizione reale",
          isinstance(base, int), f"note attuali = {base}")

    # 2-3) il contatore arriva nel payload del service, con scope applicativo
    det = get_fattura_dettaglio(fattura_id=fattura_id, auth_user_id=auth_user_id)
    check("2) `contatori` nel payload", "contatori" in det, str(det.get("contatori")))
    check("3) contatori.note == count_per_target",
          det["contatori"]["note"] == base,
          f"payload={det['contatori']['note']} diretto={base}")

    # 4) il conteggio e' VIVO: creando una nota il badge sale di 1. Passa dal
    #    service note (stesso percorso dell'API), non da un INSERT diretto.
    nota = note_svc.crea_nota(
        target_id=fattura_id,
        payload={"testo": "smoke contatore badge"},
    )
    nota_id = nota["id"]
    det2 = get_fattura_dettaglio(fattura_id=fattura_id, auth_user_id=auth_user_id)
    check("4) il contatore sale dopo una nota reale",
          det2["contatori"]["note"] == base + 1,
          f"{base} -> {det2['contatori']['note']} (nota {nota_id})")

    # 5) ⚠️ L'ASSERZIONE CHE CONTA. Perimetro allineato alla lista API: una nota
    #    NON visibile deve essere contata comunque, perche' la lista note usa
    #    `include_invisible=True` di default. Se i due perimetri divergessero il
    #    badge (dal BE) e il totale che il sub-drawer ripropaga dopo un
    #    salvataggio direbbero numeri diversi — e il badge salterebbe.
    note_svc.aggiorna_nota(
        note_id=nota_id, target_id=fattura_id, patch={"visibile": False},
    )
    det3 = get_fattura_dettaglio(fattura_id=fattura_id, auth_user_id=auth_user_id)
    _, totale_lista = NOTE_REPO_FATTURA.list(fattura_id, limit=200)
    check("5) nota invisibile: contatore == totale della lista API",
          det3["contatori"]["note"] == totale_lista == base + 1,
          f"contatore={det3['contatori']['note']} lista={totale_lista}")

    # 6) il cancello di scope resta davanti al conteggio: senza contesto
    #    operatore la RLS chiude la testata e l'endpoint risponde 404 — NON un
    #    documento a meta' con il contatore delle note (che non ha RLS).
    with connection.cursor() as cur:
        cur.execute(
            "SELECT set_config('app.ruolo_applicativo','',false),"
            "       set_config('app.current_user_id','',false)"
        )
    try:
        get_fattura_dettaglio(fattura_id=fattura_id)
        check("6) senza GUC -> 404", False, "ha restituito un documento!")
    except ServiceError as exc:
        check("6) senza GUC -> 404 (RLS)", exc.code == "E_FATTURA_NON_TROVATA",
              f"code={exc.code}")

    transaction.set_rollback(True)

print("\n=== ROLLBACK eseguito: nessun dato persistito ===")
print(f"=== ESITO: {'FALLITO — ' + ', '.join(FAIL) if FAIL else 'TUTTO VERDE'} ===\n")
