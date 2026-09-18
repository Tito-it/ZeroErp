## 📘 Documentazione Concettuale – Funzione `magazzino.trgfn_documento_interno_guard_transizione`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.inventari](/dbzero/magazzino/tabelle/inventari), [magazzino.rettifiche](/dbzero/magazzino/tabelle/rettifiche) — dove è montato
>
Approfondimento funzioni:
> • [magazzino.trgfn_documento_interno_righe_guard_testata](/dbzero/magazzino/funzioni/trgfn_documento_interno_righe_guard_testata) — il gemello sulle righe
> • [magazzino.fn_posta_inventario](/dbzero/magazzino/funzioni/fn_posta_inventario), [fn_posta_rettifica](/dbzero/magazzino/funzioni/fn_posta_rettifica) — chi apre la porta
>
Guide: brief `brief-db-magazzino-lotto-2-motore` (§3 D-L2-h, §6-ter C3, C13)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

**La matrice degli stati** dei documenti interni — una funzione per le due famiglie
(`TG_ARGV`: la colonna di stato, il nome della GUC), montata `BEFORE UPDATE OF <stato> OR
DELETE` su `inventari` e `rettifiche`:

```
DRAFT   → CONFIRM · CANCEL
CONFIRM → POSTED (solo dall'operazione) · CANCEL · DRAFT (riapri)
POSTED, CANCEL → terminali
```

Il ritorno in bozza (`CONFIRM → DRAFT`) esiste perché il piano dell'inventario si legge in
`CONFIRM` e le righe si correggono in `DRAFT`: senza, l'unica uscita da una riga sbagliata
sarebbe annullare e rifare.

**La porta `POSTED`.** Un documento «registrato» senza movimenti dietro direbbe il falso:
`POSTED` è ammesso solo se la GUC transazionale `zeroerp.magazzino_posting_<famiglia>` porta
l'id del documento — la impostano `fn_posta_inventario` / `fn_posta_rettifica` e la azzerano in
coda. Un `UPDATE` diretto è `E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE` (tecnico: nessuna
interfaccia lo produce). Ogni altra transizione fuori matrice è
`E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA`, con i due stati nella frase.

**Il cestino.** Le righe cascano con la testata; cancellare un documento registrato lascerebbe i
movimenti con una sorgente sparita. Si elimina **solo una bozza**
(`E_MAG_DOCUMENTO_NON_ELIMINABILE` altrimenti): da `CONFIRM` in poi l'uscita è `CANCEL`.

Matrice nel guard e non in una tabella: gli stati sono un `CHECK` a valori chiusi senza
attributi. Se un giorno serviranno stati configurabili, cambierà dove sta, non chi la fa
rispettare.

Presidio: `db/pgtap/magazzino/test-documenti-interni-guard-v1.sql`.

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-21`).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
