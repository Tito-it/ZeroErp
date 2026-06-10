## 📘 Documentazione Concettuale – Funzione `vendite.fn_list_preventivi_da_pushare(...)`

> 👀 **Vedi anche**
>
• [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)  
> • [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)  
> • [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa)  
> • [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)  

---
### 🎯 Scopo Principale
`vendite.fn_list_preventivi_da_pushare(...)` seleziona le righe preventivo
pronte per il push verso `commesse_attivita`, restituendo un payload completo
per l’handler di acquisizione.

---

### Regole principali

* considera preventivi in stato documento `ACCETTATO`;
* considera solo preventivi con `stato_commessa = LIBERO`;
* include solo righe attive con quantità e prezzo validi;
* esclude segmenti già emessi in `commesse_attivita` (idempotenza batch);
* costruisce `segment_key` deterministica (`PREV:{uid}:R:{riga_id}`);
* supporta filtri opzionali:
  * `p_competenza_mese`
  * `p_billing_account_id`
  * `p_limit`
  * `p_preventivo_id` *(2026-05)* — vedi sezione dedicata

---

### Push singolo preventivo (UI-driven)

> **Aggiunto:** 2026-05 — migration `20260510-01/06`

Il parametro `p_preventivo_id` (tipo `vendite.preventivi.id%TYPE`, default `NULL`) consente
di restringere il risultato al singolo preventivo selezionato dall'utente nel drawer preventivo
(pulsante "Push commessa" di `PreventiviIntegrazione.vue`).

| Valore  | Comportamento                                                          |
|---------|------------------------------------------------------------------------|
| `NULL`  | Lista globale — comportamento batch invariato                          |
| `> 0`   | Filtra al preventivo specificato; tutti gli altri filtri in AND        |
| `<= 0`  | Guard: solleva `E_PUSH_SORGENTE_ID_INVALIDO` (id 433)                  |

**Semantica AND dei filtri:** `p_preventivo_id` si aggiunge in AND agli altri filtri. Se si
passa anche `p_billing_account_id` di un BA diverso da quello del preventivo, si ottengono
0 righe (comportamento atteso: i filtri sono tutti coerenti o il push non avviene).

**Idempotenza:** se il preventivo ha righe già in `commesse_attivita` con `stato_emissione = 'EMESSA'`,
la funzione restituisce 0 righe — coerente con il NOT EXISTS del batch.

---

### Competenza e periodo

> **Aggiornato:** 2026-06-10 — migration `20260610-06`

I campi di competenza alimentano `commesse_attivita` (colonne **NOT NULL**) e
sono derivati così:

| Campo | Derivazione | Note |
| --- | --- | --- |
| `competenza_dal` | `COALESCE(validita_dal, competenza_mese, data)` | mai NULL |
| `competenza_al` | `GREATEST(competenza_dal, COALESCE(validita_al, validita_dal, competenza_mese, data))` | garantisce `dal ≤ al` |
| `competenza_mese` | `COALESCE(competenza_mese, date_trunc('month', COALESCE(validita_dal, data)))` | la **policy** `preventivi.competenza_mese` vince sul derivato |

* **`competenza_dal/al`** = periodo attività (validità del preventivo o, in sua
  mancanza, data documento). Un preventivo ACCETTATO **senza validità** è
  legittimo: i fallback evitano il crash NOT NULL sul push.
* **`competenza_mese`** = mese di fatturazione. Se la colonna di policy
  `preventivi.competenza_mese` è valorizzata (accettazione DIFFERITA, o handler
  pratica `vendita.push_preventivo`), è **autorevole**; altrimenti fallback al
  mese derivato da validità/data (pregresso).
* Periodo e mese di fatturazione sono **indipendenti**: una riga DIFFERITA può
  avere periodo a giugno e mese di fatturazione a settembre.
* Il filtro `p_competenza_mese` usa la **stessa espressione** di `competenza_mese`,
  così lista e filtro restano coerenti.

---

### 📦 Output (alto livello)

Restituisce per ogni riga candidata:
* contesto documento (`preventivo_id`, `preventivo_uid`, `riga_id`),
* dati commessa/competenza,
* dati economici (`prezzo_snapshot`, `prezzo_bloccato`, `pricing_mode`),
* sorgente (`sorgente_tipo_id`, `sorgente_uid`, `segment_key`),
* `meta` tecnico per il push.

---

### Esempi d’uso

**Batch globale (orchestrator):**

```sql
SELECT *
FROM vendite.fn_list_preventivi_da_pushare(
  p_competenza_mese => DATE ‘2026-02-01’,
  p_billing_account_id => NULL,
  p_limit => 500
);
```

**Push singolo preventivo (UI):**

```sql
SELECT *
FROM vendite.fn_list_preventivi_da_pushare(
  p_preventivo_id => 12345
);
```

---

{% include-markdown "signature-core.md" %}
