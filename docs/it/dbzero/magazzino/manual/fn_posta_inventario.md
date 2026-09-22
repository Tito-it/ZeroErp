## 📘 Documentazione Concettuale – Funzione `magazzino.fn_posta_inventario`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.inventari](/dbzero/magazzino/tabelle/inventari), [magazzino.inventari_righe](/dbzero/magazzino/tabelle/inventari_righe)
>
Approfondimento funzioni:
> • [magazzino.fn_inventario_piano](/dbzero/magazzino/funzioni/fn_inventario_piano) — da dove legge
> • [magazzino.fn_scrivi_movimento](/dbzero/magazzino/funzioni/fn_scrivi_movimento) — la primitiva che chiama per riga
> • [magazzino.trgfn_documento_interno_guard_transizione](/dbzero/magazzino/funzioni/trgfn_documento_interno_guard_transizione) — la porta `POSTED`
>
Guide: [Linee guida SQL — 5b la funzione madre](/linee-guida-sql) · brief `brief-db-magazzino-lotto-2-motore` (§4.5, D-L2-f, D-L2-n)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

⭐ **Rev 2026-09-22 (R-1 del Lotto 2-bis): le condizioni per registrare non sono
più scritte qui.** Le dice
[script.fn_check_documento_interno_registrabile](/dbzero/script/funzioni/fn_check_documento_interno_registrabile)
— stato `CONFIRM`, almeno una riga, nessuna riga che la primitiva rifiuterebbe —
e questa funzione ne solleva il **primo motivo**. È la stessa funzione da cui la
capability del drawer accende o spegne il pulsante «Registra»: il rifiuto e il
tooltip non possono divergere, perché sono la stessa riga di codice
(linee-guida-sql §12.5.2). Codici, valori e frasi restano quelli di prima. Il
`SELECT … FOR UPDATE` sulla testata resta **primo**: è il lock che serializza due
registrazioni dello stesso documento, e la check — che è `STABLE` — non può
prenderlo.


**Registra un inventario confermato.** Legge il [piano](/dbzero/magazzino/funzioni/fn_inventario_piano),
scrive su ogni riga la quantità che il registro diceva (`qta_sistema`: la fotografia contro cui
il conteggio è stato posto, e resta), posta con la primitiva ogni riga con differenza, porta la
testata a `POSTED`. Ritorna, riga per riga, il movimento scritto.

È **una transazione sola** per costruzione: si chiama con una `SELECT`. Se una riga è rifiutata
(la merce non c'è, l'articolo non è gestito), non resta niente e il documento resta `CONFIRM`.

---

### Che cosa posta

* la **differenza** `qta_contata − qta_sistema`, alla grana della riga (articolo, ubicazione,
  lotto, seriale); differenza zero = nessun movimento;
* la **causale** la decide il registro: `INV_INIZIALE` se quell'articolo non ha nessun
  movimento nel magazzino (è il primo carico in assoluto), altrimenti `RETT_POS` / `RETT_NEG`;
* la **sorgente** è la riga (`INVENTARIO_RIGA`), il **costo** è quello della riga solo su
  un'entrata (un'uscita va alla media), la **data** del movimento è quella dell'inventario;
* le posizioni `NON_CONTATA` del piano restano com'erano — informazione, non blocco;
* una riga `NON_POSTABILE` fa rifiutare tutto, col primo motivo della stessa check che il piano
  aveva mostrato.

---

### La porta

Un inventario va a `POSTED` **solo** da qui: la funzione si firma con una GUC transazionale
(`zeroerp.magazzino_posting_inventario` = id del documento), che il
[guard di famiglia](/dbzero/magazzino/funzioni/trgfn_documento_interno_guard_transizione)
pretende per ammettere lo stato, e che le righe in `CONFIRM` accettano per lasciar scrivere
`qta_sistema`. Un `UPDATE` diretto a `POSTED` è rifiutato.

La testata si legge `FOR UPDATE` sotto la row level security dell'operatore: fuori perimetro
**non c'è** (`E_MAG_DOCUMENTO_NON_TROVATO`, lo stesso 404 di un id inesistente); non in
`CONFIRM` → `E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA`; senza righe →
`E_MAG_DOCUMENTO_SENZA_RIGHE`. Due posting dello stesso documento si serializzano sulla riga
della testata: il secondo trova `POSTED`.

Presidio: `db/pgtap/magazzino/test-fn-posta-inventario-v1.sql`.

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-23`).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
