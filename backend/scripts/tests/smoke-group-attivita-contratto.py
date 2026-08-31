# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke F3-a — l'ATTO entra nella chiave di aggregazione delle righe di
#        fattura, provato sul database vero.
# Eseguito via `./manage-env.sh shell < scripts/tests/smoke-group-attivita-contratto.py`
#
# ⭐ PERCHE' UNO SMOKE E NON I SOLI TEST DJANGO. I test di
# `test_fatture_righe_service` mockano il repository: provano che la chiave
# spezza, e NON che `a.contratto_id` esista nella proiezione ne' che il mapper
# lo legga dalla colonna giusta. La proiezione e' una tupla letta per INDICE:
# una colonna aggiunta in mezzo invece che in fondo sposterebbe tutte quelle
# dopo, e il difetto sarebbe MUTO — `rett_iva_id` finirebbe in `contratto_id` e
# viceversa, entrambi interi, entrambi plausibili.
#
# ⭐ IL CASO SI COSTRUISCE, NON SI CERCA. Al 2026-08-31 `attivita_fatturabili`
# ha 52 righe e **zero** con un contratto: uno smoke che cercasse l'attivita'
# con l'atto passerebbe a vuoto — verde per sottrazione. Qui il contratto si
# posa su un'attivita' viva e alla fine si annulla tutto.
#
# ⚠️ SERVE IL CONTESTO OPERATORE: `attivita_fatturabili` ha la RLS. Senza i
# cinque GUC la proiezione torna zero righe e non si distingue «non c'e' niente
# di sbagliato» da «non vedo niente».
#
# ⚠️ L'attivita' dev'essere NON ancora fatturata: `trgfn_attivita_fatturabili_
# guard_fatturato` rifiuta ogni UPDATE su una riga con `fattura_riga_id`.
#
# Rollback-safe: `transaction.atomic()` + `set_rollback(True)`.
#
# Indice test (1..7):
#   1. Fixture: contesto operatore + un'attivita' non fatturata e un contratto
#   2. La proiezione LEGA: `a.contratto_id` esiste e la SELECT gira
#   3. Senza contratto il campo e' None (e non un altro valore per caso)
#   4. Posato il contratto, il repository lo legge — dalla colonna GIUSTA
#   5. ⛔ Nessun altro campo si e' spostato: il presidio dell'off-by-one
#   6. La chiave di gruppo porta l'atto, e cambia SOLO per quello
#   7. La lettura BATCH dice la stessa cosa della singola
# ------------------------------------------------------------
from dataclasses import asdict

from django.db import connection, transaction

from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.services.fatture_righe_service import FattureRigheService

FAIL: list[str] = []


# Scopo: registra l'esito di un caso, leggibile a colpo d'occhio.
def check(nome: str, ok: bool, dettaglio: str = "") -> None:
    print(f"  [{'OK ' if ok else 'KO '}] {nome}{(' — ' + dettaglio) if dettaglio else ''}")
    if not ok:
        FAIL.append(nome)


with transaction.atomic():
    repo = VenditePipelineRepository()

    # ── 1. Fixture ────────────────────────────────────────────────────────
    print("\n=== 1. Fixture: il caso si costruisce ===")
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT i.id, i.auth_user_id, i.soggetto_ruolo_id, u.username
              FROM anagrafiche.identita_digitali i
              JOIN auth_user u ON u.id = i.auth_user_id
             WHERE i.ruolo_applicativo = 'OPERATORE' AND i.attivo
             LIMIT 1
            """
        )
        ident = cur.fetchone()
        if not ident:
            raise SystemExit("SENZA_MATERIA: nessuna identita OPERATORE attiva.")
        for chiave, valore in (
            ("app.current_user_id", str(ident[1])),
            ("app.current_identita_id", str(ident[0])),
            ("app.ruolo_applicativo", "OPERATORE"),
            ("app.soggetto_ruolo_id", str(ident[2])),
            ("app.jwt_user", ident[3]),
        ):
            cur.execute("SELECT set_config(%s, %s, true)", [chiave, valore])

        # ⚠️ `fattura_riga_id IS NULL`: su una gia' fatturata il guard rifiuta
        #    l'UPDATE, e lo smoke morirebbe nella fixture invece che sul merito.
        cur.execute(
            """
            SELECT id FROM vendite.attivita_fatturabili
             WHERE fattura_riga_id IS NULL AND contratto_id IS NULL
             ORDER BY id LIMIT 1
            """
        )
        r = cur.fetchone()
        attivita_id = r[0] if r else None
        cur.execute("SELECT id FROM vendite.contratti ORDER BY id LIMIT 1")
        r = cur.fetchone()
        contratto_id = r[0] if r else None

    if attivita_id is None or contratto_id is None:
        raise SystemExit(
            "SENZA_MATERIA: servono un'attivita non fatturata e un contratto, "
            f"trovati attivita={attivita_id} contratto={contratto_id}."
        )
    check("attivita non fatturata e contratto", True,
          f"attivita={attivita_id} contratto={contratto_id}")

    # ── 2-3. La proiezione, prima ─────────────────────────────────────────
    print("\n=== 2-3. La proiezione lega, e senza atto il campo e' None ===")
    prima = repo.get_group_attivita_input(attivita_id)
    check("la SELECT gira e ritorna la riga", prima is not None)
    if prima is None:
        raise SystemExit("SENZA_MATERIA: la proiezione non vede l'attivita (RLS?).")
    check("il campo `contratto_id` esiste sulla dataclass",
          "contratto_id" in asdict(prima))
    check("senza atto vale None", prima.contratto_id is None,
          str(prima.contratto_id))

    # ── 4-5. Posato l'atto ────────────────────────────────────────────────
    print("\n=== 4-5. Posato l'atto: arriva, e non sposta nient'altro ===")
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE vendite.attivita_fatturabili SET contratto_id = %s WHERE id = %s",
            [contratto_id, attivita_id],
        )
    dopo = repo.get_group_attivita_input(attivita_id)
    assert dopo is not None
    # ⭐ Il valore arriva, e arriva UGUALE a quello scritto: con la colonna
    #    letta a un indice sbagliato qui comparirebbe un altro intero.
    check("il repository legge l'atto posato",
          dopo.contratto_id == contratto_id,
          f"letto={dopo.contratto_id} atteso={contratto_id}")

    # ⛔ IL PRESIDIO DELL'OFF-BY-ONE: la proiezione e' una tupla letta per
    #    indice. Se la colonna nuova fosse finita in mezzo, TUTTI i campi dopo
    #    di lei scivolerebbero di uno — e nessuno solleverebbe. Qui si confronta
    #    campo per campo il PRIMA e il DOPO: l'unica differenza ammessa e'
    #    l'atto, che e' l'unica cosa che l'UPDATE ha toccato.
    d_prima, d_dopo = asdict(prima), asdict(dopo)
    spostati = [
        k for k in d_prima
        if k != "contratto_id" and d_prima[k] != d_dopo[k]
    ]
    check("nessun altro campo si e' spostato", not spostati, str(spostati))

    # ── 6. La chiave ──────────────────────────────────────────────────────
    print("\n=== 6. La chiave di gruppo porta l'atto ===")
    k_prima = FattureRigheService._build_group_key(prima)
    k_dopo = FattureRigheService._build_group_key(dopo)
    check("l'atto e' nella chiave", k_dopo.get("contratto_id") == contratto_id,
          str(k_dopo.get("contratto_id")))
    # ⭐ La spezzatura si vede QUI: due chiavi diverse sono due righe di
    #    fattura. E cambia SOLO per l'atto — se cambiasse altro, il
    #    raggruppamento di righe che con i contratti non c'entrano si
    #    sposterebbe, cioe' il contrario di cio' che questa voce promette.
    diff = [k for k in k_prima if k_prima[k] != k_dopo[k]]
    check("le due chiavi differiscono SOLO per l'atto",
          diff == ["contratto_id"], str(diff))

    # ── 7. La lettura batch ───────────────────────────────────────────────
    print("\n=== 7. La batch dice la stessa cosa della singola ===")
    # ⚠️ Le due letture condividono la proiezione e il mapper, ma condividerli
    #    e' precisamente cio' che va PROVATO: sono state due copie divergenti,
    #    e il commento che le ha unificate lo racconta.
    batch = repo.batch_get_group_attivita_inputs([attivita_id])
    check("la batch vede l'attivita", attivita_id in batch)
    if attivita_id in batch:
        check("e legge lo stesso atto",
              batch[attivita_id].contratto_id == contratto_id,
              str(batch[attivita_id].contratto_id))
        check("e la stessa riga, campo per campo",
              asdict(batch[attivita_id]) == d_dopo)

    transaction.set_rollback(True)

print(f"\n=== ESITO: {'FALLITO — ' + ', '.join(FAIL) if FAIL else 'TUTTO VERDE'} ===\n")
