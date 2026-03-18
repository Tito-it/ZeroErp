## 📘 Documentazione – Funzione trigger `anagrafiche.trgfn_pdp_a10_guard`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [`anagrafiche.pdp`](/dbzero/anagrafiche/tabelle/anagrafiche_pdp)  
>
**Approfondimento funzioni:**
>
• [`script.fn_log_and_raise_error`](/dbzero/script/funzioni/fn_log_and_raise_error)  

---
### 🎯 Scopo Principale
(latest review 28-01-2026)
Impedire la **modifica** dei campi **identitari** del PDP:

* `pdp` (codice univoco globale)
* `indirizzo_dettaglio_id` (ancoraggio fisico)

La regola è **immutabilità dopo prima valorizzazione**: è consentito impostare il valore da `NULL → valore`, ma **qualunque modifica successiva** viene bloccata con eccezione applicativa tracciata via `script.fn_log_and_raise_error`.

**Nota naming**: in versioni precedenti la funzione era `anagrafiche.trgfn_pdp_protect_cols` con trigger `trg_pdp_protect_cols_upd`.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_pdp_a10_guard()
RETURNS trigger
LANGUAGE plpgsql
VOLATILE
```

**Perché `VOLATILE`**: la funzione può lanciare eccezioni e scrivere log; inoltre dipende da variabili di contesto del trigger (`TG_OP`, `TG_NAME`).

---


**Effetti pratici**

* Consentito: `pdp: NULL → 'IT001...'` (prima valorizzazione).
* Vietato: `pdp: 'IT001...' → 'IT002...'` (cambio codice).
* Consentito: `indirizzo_dettaglio_id: NULL → 123` (prima valorizzazione).
* Vietato: `indirizzo_dettaglio_id: 123 → 456` (spostamento di luogo).

> **Variante più restrittiva**: per **vietare anche** `NULL → valore`, rimuovi le condizioni `OLD.<col> IS NOT NULL`.

---

### Dipendenze

* `script.fn_log_and_raise_error` – registra l’evento e genera l’eccezione applicativa con **codice** `E_COLONNA_NON_MODIFICABILE` e payload JSON (colonna/id).

---

### Esempi d’uso

**DDL trigger su tabella `anagrafiche.pdp`**

```sql
-- Ricrea il trigger di protezione
DROP TRIGGER IF EXISTS trg_pdp_a10_guard_upd ON anagrafiche.pdp;
CREATE TRIGGER trg_pdp_a10_guard_upd
BEFORE UPDATE OF pdp, indirizzo_dettaglio_id
ON anagrafiche.pdp
FOR EACH ROW
EXECUTE FUNCTION anagrafiche.trgfn_pdp_a10_guard();
```

**Test rapido**

```sql
-- 1) Prima valorizzazione: OK
UPDATE anagrafiche.pdp SET pdp = 'IT001ABCDEF' WHERE id = 100 AND pdp IS NULL;

-- 2) Tentativo di cambio codice: ERRORE atteso
UPDATE anagrafiche.pdp SET pdp = 'IT002XYZ' WHERE id = 100; -- raise E_COLONNA_NON_MODIFICABILE

-- 3) Tentativo di spostare indirizzo: ERRORE atteso
UPDATE anagrafiche.pdp SET indirizzo_dettaglio_id = 999 WHERE id = 100; -- raise E_COLONNA_NON_MODIFICABILE
```

---

### Motivazioni progettuali

1. **Stabilità dei riferimenti**: `pdp` è chiave esterna per sistemi esterni (POD/PDR). Cambiarlo romperebbe l’allineamento.
2. **Coerenza fisica**: un PDP rappresenta un **punto reale**; spostarlo di indirizzo equivale a creare **un nuovo PDP**, non a modificare quello esistente.
3. **Audit e governance**: in caso di tentativi di modifica, l’errore viene **loggato** con contesto (`TG_NAME`) e payload strutturato.
4. **Sicurezza by‑design**: la protezione è a livello DB, non delegata al solo applicativo.

---

### ⚠️ Note operative

* Il trigger deve essere **`BEFORE UPDATE OF pdp, indirizzo_dettaglio_id`** per intercettare solo gli update rilevanti, riducendo overhead.
* In **migrazione dati** (bulk load): applicare le valorizzazioni iniziali **prima** di attivare il trigger, o disabilitarlo temporaneamente, se serve caricare codici/indirizzi già definitivi.
* In caso di refactor del dominio: se una riga necessita cambio di indirizzo, procedere con **nuova riga PDP** e, se necessario, storicizzare la precedente.

---

{% include-markdown "signature-core.md" %}
