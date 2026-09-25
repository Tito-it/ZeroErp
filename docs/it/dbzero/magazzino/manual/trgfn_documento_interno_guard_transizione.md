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

(rev 2026-09-22 — R-1 del Lotto 2-bis: la matrice **esce dal corpo**)

⭐ **Dal 22-09-2026 il guard non CONTIENE più la matrice: la LEGGE** da
[magazzino.fn_documento_interno_transizioni](/dbzero/magazzino/funzioni/fn_documento_interno_transizioni),
la stessa sede da cui la capability del drawer disegna i pulsanti. Cambia dove
sta la regola, non chi la fa rispettare — e cambia perché adesso i lettori sono
**due**: un `CASE` nel corpo avrebbe costretto il frontend a scriverne una
seconda copia (linee-guida-sql §12.2 punto 1). Comportamento, codici e frasi
sono invariati. Il DELETE solo in bozza e la porta `POSTED` restano qui: sono
regole di questo guard, non della matrice.

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

**La porta `POSTED`.** Un documento «registrato» senza movimenti dietro direbbe il falso.
`POSTED` è ammesso solo se valgono **due condizioni insieme**:

1. la GUC transazionale `zeroerp.magazzino_posting_<famiglia>` porta l'id del documento. La
   impostano `fn_posta_inventario` / `fn_posta_rettifica` e la azzerano in coda. Dice **quale
   operazione e quale documento**;
2. chi esegue è il proprietario della tabella
   ([script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella)).
   Dice **che la scrittura passa da un verbo**: i due verbi girano con i privilegi del
   proprietario, l'app no.

La seconda condizione c'è dal 25-09-2026 (D-V1 di brief-db-magazzino-verbi-con-permesso).
Prima bastava la GUC, ma l'app può accenderla da sola: poteva segnare un documento come
registrato senza movimenti e senza il permesso. Da sola, ora, la GUC non apre più niente.

Un `UPDATE` diretto è `E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE` (tecnico: nessuna
interfaccia lo produce). Nel contesto dell'errore `dentro_verbo` e `db_user` dicono quale
delle due condizioni è mancata. Ogni altra transizione fuori matrice è
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
