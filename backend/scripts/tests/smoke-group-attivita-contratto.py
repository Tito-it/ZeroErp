# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
#  5b. ⛔ Gli indici dopo l'uscita di `art.iva_id` (`I4`)
#   6. La chiave di gruppo porta l'atto, e cambia SOLO per quello
#   7. La lettura BATCH dice la stessa cosa della singola
#   8. F3-c: la lista da fatturare porta il CODICE dell'articolo
#   9. ⛔ ed e' il codice vero, non un altro campo scivolato di posto
#  10. ⭐ l'ordine che ne esce e' quello dei codici, non degli UUID
#  11. ⛔ Il contesto IVA di testata porta la PK dell'emittente, non il
#      soggetto-ruolo: con quello sbagliato l'IVA e' piena e nessuno lo dice
# ------------------------------------------------------------
import uuid
from dataclasses import asdict
from decimal import Decimal

from django.db import connection, transaction

from apps.vendite.db.pipeline_repository import VenditePipelineRepository
from apps.vendite.services.fatture_righe_service import FattureRigheService
from scripts.tests._smoke_contesto import apri_contesto_smoke
from scripts.tests._smoke_fatturazione import (
    chiave_di_commessa,
    costruisci_base_fatturazione,
    crea_articolo_di_prova,
    crea_attivita_di_commessa,
    crea_lotto_di_prova,
)

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
    # ⭐ Tutto si COSTRUISCE (brief-be-utenti-di-sviluppo §9.9.1, T-7b):
    #    prima il contesto era «un operatore attivo qualunque» e attivita',
    #    contratto e fattura erano «il primo che c'e'». Ora il contesto e'
    #    l'utente degli smoke sull'emittente di prova, la base e le attivita'
    #    vengono dal BB, il contratto dal builder del DB.
    # ⛔ Il contratto e' del BA della commessa dell'attivita': un contratto di
    #    un altro cliente e' `E_ATTIVITA_CONTRATTO_INCOERENTE`
    #    (`vendite.trgfn_attivita_guard_contratto`, 2026-10-21).
    # ⚠️ Tre attivita' su tre articoli, lockate sullo stesso lotto: servono ai
    #    test 8-10, che confrontano l'ordine per codice con quello per UUID.
    #    La prima e' quella dei test 2-7: non fatturata, senza contratto.
    with connection.cursor() as cur:
        apri_contesto_smoke(cur)
        marker = uuid.uuid4().hex[:8]
        t = costruisci_base_fatturazione(cur, marker=marker)
        lock_batch_id = str(uuid.uuid4())
        lotto_id = crea_lotto_di_prova(cur, t, codice=f"SMOKE-GRP-{marker}", lock_batch_id=lock_batch_id)
        articoli = [t["articolo_id"]] + [
            crea_articolo_di_prova(cur, prefisso="SMOKE-GRP", uom_id=t["uom_id"])[0]
            for _ in range(2)
        ]
        attivita_ids = [
            crea_attivita_di_commessa(
                cur, t,
                segment_key=chiave_di_commessa(cur, t, t["commessa_id"], f"SMOKE:{marker}:G{n}"), lock_batch_id=lock_batch_id,
                prezzo=Decimal("10.00"), articolo_id=art,
            )[1]
            for n, art in enumerate(articoli)
        ]
        attivita_id = attivita_ids[0]
        cur.execute(
            "SELECT contratto_id FROM dbops.fn_pgtap_crea_contratto(%s, 'ATTIVO', %s)",
            [f"smoke group {marker}", t["billing_account_id"]],
        )
        contratto_id = cur.fetchone()[0]

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

    # ── 5-bis. Gli indici, dopo che `art.iva_id` e' USCITA ────────────────
    print("\n=== 5-bis. La proiezione ha perso una colonna: gli indici tengono? ===")
    # ⛔ Il 2026-08-31 `art.iva_id` e' uscita dalla SELECT (`I4`): tutti gli
    #    indici DOPO di lei sono scalati di uno. Il confronto prima/dopo del
    #    test 5 NON basta a prendere uno scivolamento COSTANTE — vede solo cio'
    #    che cambia fra due letture. Qui i valori si confrontano con la riga
    #    vera, campo per campo, sui tipi che uno scivolamento renderebbe
    #    assurdi.
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT a.prezzo_unitario, a.competenza_dal, a.data_attivita,
                   a.tipo_movimento, COALESCE(a.uom_id, art.uom_id)
              FROM vendite.attivita_fatturabili a
              JOIN catalogo.articoli art ON art.id = a.articolo_id
             WHERE a.id = %s
            """,
            [attivita_id],
        )
        v = cur.fetchone()
    for nome, letto, atteso in (
        ("prezzo_unitario", dopo.prezzo_unitario, v[0]),
        ("competenza_dal", dopo.competenza_dal, v[1]),
        ("data_attivita", dopo.data_attivita, v[2]),
        ("tipo_movimento", dopo.tipo_movimento, v[3]),
        ("uom_id", dopo.uom_id, None if v[4] is None else int(v[4])),
    ):
        check(f"«{nome}» e' al posto giusto", letto == atteso, f"{letto!r} vs {atteso!r}")
    # ⭐ E la prova che la colonna e' davvero sparita: la dataclass non ha piu'
    #    il campo. Se qualcuno la rimettesse, l'IVA tornerebbe ad avere due
    #    risposte — quella dell'articolo e quella del risolutore.
    check("`iva_id` NON e' piu' sul group input", "iva_id" not in d_dopo,
          str([k for k in d_dopo if "iva" in k]))

    # ── 6. La chiave ──────────────────────────────────────────────────────
    print("\n=== 6. La chiave di gruppo porta l'atto ===")
    # ⚠️ `iva_id` e' un PARAMETRO della chiave dal 2026-08-31: qui si passa un
    #    valore fisso perche' cio' che si prova e' l'ATTO, non la risoluzione.
    k_prima = FattureRigheService._build_group_key(prima, iva_id=22)
    k_dopo = FattureRigheService._build_group_key(dopo, iva_id=22)
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

    # ── 8-10. F3-c: l'ordinamento leggibile ───────────────────────────────
    print("\n=== 8-10. Il CODICE dell'articolo nella lista da fatturare ===")
    # ⚠️ E' una SECONDA proiezione (`list_attivita_da_fatturare`), non quella dei
    #    test 2-7: condivide la tabella ma non la SELECT, quindi va provata a
    #    parte o `art.codice` resterebbe non verificato.
    att = repo.list_attivita_da_fatturare(lotto_id)
    check("la lista risponde", bool(att), f"lotto={lotto_id} righe={len(att)}")
    check("il campo `articolo_codice` e' valorizzato",
          all(a.articolo_codice for a in att),
          str([a.articolo_codice for a in att][:5]))
    # ⛔ Il presidio dell'off-by-one, di nuovo: `art.codice` e' stato
    #    APPESO in fondo alla SELECT. Se fosse finito in mezzo, `meta` e
    #    `tipo_movimento` scivolerebbero — e `tipo_movimento` finirebbe a
    #    valere il codice di un articolo, senza che niente sollevi.
    with connection.cursor() as cur:
        cur.execute(
            "SELECT codice FROM catalogo.articoli WHERE id = %s",
            [att[0].articolo_id],
        )
        atteso = cur.fetchone()
    check("ed e' il codice VERO dell'articolo",
          bool(atteso) and att[0].articolo_codice == atteso[0],
          f"letto={att[0].articolo_codice} db={atteso[0] if atteso else None}")
    check("e `tipo_movimento` non e' scivolato",
          all(a.tipo_movimento in ("NORMALE", "ONERE", "RETTIFICA") for a in att),
          str(sorted({a.tipo_movimento for a in att})))
    # ⭐ E la cosa che la decisione compra davvero: l'ordine per codice non
    #    coincide con l'ordine per UUID. Se coincidesse su QUESTI dati il
    #    controllo non discriminerebbe, e va detto invece di far finta.
    codici = [a.articolo_codice for a in att]
    per_uuid = [a.articolo_codice for a in sorted(att, key=lambda x: x.articolo_id)]
    if sorted(codici) == per_uuid:
        print("  [--] i due ordini coincidono su questi dati: "
              "il confronto non discrimina (lo dicono i test unitari)")
    else:
        check("l'ordine per codice DIFFERISCE da quello per UUID", True,
              f"codice={sorted(codici)[:3]} uuid={per_uuid[:3]}")

    # ── 11. Il contesto IVA di testata ────────────────────────────────────
    print("\n=== 11. Il contesto della testata: la PK, non il soggetto-ruolo ===")
    with connection.cursor() as cur:
        cur.execute(
            "SELECT fattura_id FROM dbops.fn_pgtap_crea_fattura(%s, 'DRAFT', %s)",
            [f"smoke group {marker}", t["billing_account_id"]],
        )
        fattura_id = cur.fetchone()[0]
    ctx = repo.batch_get_fattura_iva_context([fattura_id]).get(fattura_id) or {}
    check("il contesto risponde", bool(ctx), str(sorted(ctx)))
    check("porta cliente, emittente e data",
          {"billing_account_id", "emittente_fiscale_id", "data_riferimento"}
          <= set(ctx), str(sorted(ctx)))
    emittente = ctx.get("emittente_fiscale_id")
    with connection.cursor() as cur:
        # ⛔ LA PROVA CHE CONTA: l'id tornato deve essere una PK di
        #    `emittenti_fiscali`, e la testata porta invece il
        #    SOGGETTO-RUOLO. Con quello sbagliato il risolutore non trova
        #    l'emittente, quindi non trova i suoi titoli, e risponde con
        #    l'aliquota ordinaria SENZA sollevare.
        cur.execute(
            """
            SELECT ef.id, f.emittente_soggetto_ruolo_id
              FROM vendite.fatture f
              LEFT JOIN anagrafiche.emittenti_fiscali ef
                ON ef.soggetto_ruolo_id = f.emittente_soggetto_ruolo_id
             WHERE f.id = %s
            """,
            [fattura_id],
        )
        atteso = cur.fetchone()
    check("e' la PK dell'emittente", emittente == atteso[0],
          f"letto={emittente} pk={atteso[0]} soggetto_ruolo={atteso[1]}")
    # ⚠️ E i due numeri devono essere DIVERSI, o il controllo sopra
    #    passerebbe anche con l'id sbagliato: si dice invece di far finta.
    if atteso[0] == atteso[1]:
        print("  [--] su questa fattura PK e soggetto-ruolo COINCIDONO: "
              "il controllo non discrimina")
    else:
        check("PK e soggetto-ruolo sono numeri DIVERSI", True,
              f"pk={atteso[0]} sr={atteso[1]}")

    transaction.set_rollback(True)

print(f"\n=== ESITO: {'FALLITO — ' + ', '.join(FAIL) if FAIL else 'TUTTO VERDE'} ===\n")
