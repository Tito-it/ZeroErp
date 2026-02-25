## Documentazione Concettuale – Funzione `vendite.fn_list_ddt_da_pushare(...)`

> **Vedi anche**
>
> * [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> * [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)
> * [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)
> * [vendite.fn_list_ordini_da_pushare](/dbzero/vendite/funzioni/fn_list_ordini_da_pushare)
> * [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa)
> * [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)

---

### Scopo Principale

`vendite.fn_list_ddt_da_pushare(...)` seleziona le righe DDT pronte per
il push verso `commesse_attivita`, restituendo un payload completo per
l'handler di acquisizione.

Supporta **due modalita`**:
- **DDT da ordine**: fatturazione delegata dall'ordine via `fatturazione_trigger`
- **DDT autonomo**: DDT con billing_account proprio, senza ordine sorgente

---

### Regole principali

**Caso A — DDT da ordine (fulfillment esiste):**

* l'ordine sorgente ha `fatturazione_trigger IN ('SPEDITO','CONSEGNATO')`;
* lo stato DDT deve corrispondere al trigger dell'ordine;
* prezzo: `COALESCE(ddt_righe.prezzo_unitario, ordini_righe.prezzo_unitario)`;
* billing_account: `COALESCE(ddt.billing_account_id, ordini.billing_account_id)`.

**Caso B — DDT autonomo (nessun fulfillment):**

* `ddt.billing_account_id IS NOT NULL` (obbligatorio);
* stato DDT IN (`SPEDITO`, `CONSEGNATO`);
* prezzo da `ddt_righe.prezzo_unitario` (puo` essere NULL; handler risolve).

**Regole comuni:**

* riga attiva (`attivo = TRUE`);
* esclude segmenti gia` emessi in `commesse_attivita` (idempotenza batch);
* costruisce `segment_key` deterministica (`DDT:{uid}:R:{riga_id}`);
* `prezzo_bloccato = TRUE` se prezzo_snapshot presente;
* sorgente tipo: `DDT_VENDITA` da `config.sorgenti` (id=8);
* supporta filtri opzionali:
  * `p_competenza_mese`
  * `p_billing_account_id`
  * `p_limit`

---

### Relazione con fn_list_ordini_da_pushare

Le due funzioni sono **mutuamente esclusive** per design:

| fatturazione_trigger | Chi pusha | Funzione |
|---------------------|-----------|----------|
| `CONFERMATO` | Ordine | `fn_list_ordini_da_pushare` |
| `SPEDITO` | DDT alla spedizione | `fn_list_ddt_da_pushare` |
| `CONSEGNATO` | DDT alla consegna | `fn_list_ddt_da_pushare` |

Il campo `fatturazione_trigger` su `vendite.ordini` (default da
`anagrafiche.billing_account.fatturazione_ordini`) determina quale
funzione gestisce il push a commessa.

---

### Output (alto livello)

Restituisce per ogni riga candidata:
* contesto documento (`ddt_id`, `ddt_uid`, `riga_id`),
* dati commessa/competenza (risolti da DDT o ordine sorgente),
* dati economici (`prezzo_snapshot`, `prezzo_bloccato`, `pricing_mode`),
* sorgente (`sorgente_tipo_id`, `sorgente_uid`, `segment_key`),
* `meta` tecnico con riferimento ordine sorgente (se presente).

---

### Esempio d'uso

```sql
SELECT *
FROM vendite.fn_list_ddt_da_pushare(
  p_competenza_mese => DATE '2026-03-01',
  p_billing_account_id => NULL,
  p_limit => 500
);
```

---

{% include-markdown "signature-core.md" %}
