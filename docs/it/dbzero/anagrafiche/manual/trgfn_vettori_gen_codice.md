## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_vettori_gen_codice()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.vettori](/dbzero/anagrafiche/tabelle/vettori)
> • [config.sistema_codici](/dbzero/config/tabelle/sistema_codici)
>
Approfondimento funzioni:
> • [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)
> • [script.trgfn_config_sistema_codici_sync_gen_codice](/dbzero/script/funzioni/trgfn_config_sistema_codici_sync_gen_codice)
> • [anagrafiche.trgfn_vettori_normalize](/dbzero/anagrafiche/funzioni/trgfn_vettori_normalize)

---
### 🎯 Scopo Principale

(rev 2026-08-21 — **funzione nata il 2026-08-21**)

Assegna il **codice del vettore** quando non viene fornito, delegando a
`script.fn_generate_codice('vettori')`. È la settima della famiglia `gen_codice`, identica
alle altre sei perché — come loro — non è scritta a mano: la genera l'automazione dei codici.

Configurazione in `config.sistema_codici`, riga `codice_interno = 'vettori'`:
prefisso `VET`, separatore `-`, numero a 7 cifre (`VET-0000001`).

---

### Aggancio

Trigger `trg_vettori_a10_gen_codice_ins_upd` — fase `_a10_`,
`BEFORE INSERT OR UPDATE OF codice` su `anagrafiche.vettori`.

---

### Regole applicate

1. Se `NEW.codice` è `NULL` o vuoto dopo `btrim`, viene valorizzato con
   `script.fn_generate_codice('vettori')`.
2. Un codice già valorizzato non viene mai sovrascritto.

---

### ⚠️ Questa funzione è **generata**, non scritta a mano

Funzione, sequenza (`anagrafiche.vettori_codice_seq`) e trigger sono creati con DDL dinamico
da `script.trgfn_config_sistema_codici_sync_gen_codice`, il trigger `AFTER` di
`config.sistema_codici`, a partire dalla sola riga di configurazione.

Modificarla a mano non serve a niente: il loader del CSV è `runOnChange` e la riscrive col
template a ogni migrate. Si spegne portando `usa_sequenza` a `false`, non con un `DROP`.

---

### Perché è arrivata così tardi

Fino al 2026-08-21 `anagrafiche.vettori.codice` era `NOT NULL` e `UNIQUE` ma **non lo
generava nessuno**: niente riga in `config.sistema_codici`, niente trigger sulla tabella. Il
codice doveva arrivare dal chiamante, e un `INSERT` che lo ometteva moriva su una violazione
di vincolo (SQLSTATE `23502`), senza nessun codice `E_*` a spiegarne il motivo.

Nel frattempo `anagrafiche.trgfn_vettori_normalize` — un no-op — dichiarava nel proprio
`COMMENT` «generazione codice demandata al sistema_codici»: un rinvio a un meccanismo che per
i vettori non era mai stato attivato. La lacuna è emersa scrivendo la doc manuale delle
trigger function, ed è stata chiusa aggiungendo la riga 19 al CSV.

⚠️ Alla nascita la sequenza è stata allineata da `20260821-06` oltre il massimo dei codici già
presenti in forma `VET-<numero>`: senza, il primo `nextval` avrebbe potuto produrre un codice
già occupato e violare `uq_vettori_codice`.

---

### Il codice resta immutabile

Su `anagrafiche.vettori` agisce anche `trg_vettori_a10_lock_columns_upd`
(`CODICE_NON_MODIFICABILE`), configurato in `dbops.automation_lock_columns` fin da gennaio —
fino a oggi presidiava una colonna che nessuno generava.

I `BEFORE ROW` scattano in ordine alfabetico, quindi `gen_codice` gira prima di
`lock_columns`: chi azzera `codice` in un `UPDATE` ne ottiene uno nuovo, che il lock rifiuta
subito dopo come modifica.

---

### Codici errore

| Codice | Sollevato da | Quando |
|--------|--------------|--------|
| `E_SEQUENZA_NON_CONFIGURATA` | `script.fn_generate_codice` | Riga `codice_interno = 'vettori'` assente in `config.sistema_codici`, o sequenza non provisionata |
| `CODICE_NON_MODIFICABILE` | `script.trgfn_lock_columns` | Tentativo di cambiare `codice` in `UPDATE` |

La funzione non solleva errori propri.

Presidio: `db/pgtap/anagrafiche/test-vettori-gen-codice.sql`.

---

{% include-markdown "signature-core.md" %}
