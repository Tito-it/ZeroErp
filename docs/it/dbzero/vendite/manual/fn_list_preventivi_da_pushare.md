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

---

### 📦 Output (alto livello)

Restituisce per ogni riga candidata:
* contesto documento (`preventivo_id`, `preventivo_uid`, `riga_id`),
* dati commessa/competenza,
* dati economici (`prezzo_snapshot`, `prezzo_bloccato`, `pricing_mode`),
* sorgente (`sorgente_tipo_id`, `sorgente_uid`, `segment_key`),
* `meta` tecnico per il push.

---

### Esempio d’uso

```sql
SELECT *
FROM vendite.fn_list_preventivi_da_pushare(
  p_competenza_mese => DATE '2026-02-01',
  p_billing_account_id => NULL,
  p_limit => 500
);
```

---

{% include-markdown "signature-core.md" %}
