## Documentazione Concettuale – Funzione `vendite.fn_list_contratti_da_pushare(...)`

> **Vedi anche**
>
[vendite.contratti](/dbzero/vendite/tabelle/contratti)
> [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe)
> [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa)
> [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)

---
### 🎯 Scopo Principale
`vendite.fn_list_contratti_da_pushare(...)` seleziona le righe contratto
pronte per il push verso `commesse_attivita`, restituendo un payload completo
per l'handler di acquisizione.

A differenza di preventivi e ordini (una tantum), un contratto puo` avere
righe ricorrenti (canoni, quote fisse mensili). Per garantire idempotenza
su piu` periodi il `segment_key` include il mese di competenza.

---

### Regole principali

* considera contratti in stato documento `ATTIVO`;
* contratto in validita` (`valido_al IS NULL` o `>= competenza_mese/oggi`);
* include solo righe attive con articolo valido;
* esclude segmenti gia` emessi in `commesse_attivita` (idempotenza batch);
* costruisce `segment_key` deterministica (`CONTR:{uid}:R:{riga_id}:M:{YYYY-MM}`);
* `prezzo_bloccato = TRUE` se `prezzo_unitario` presente nel contratto;
* sorgente tipo: `CONTRATTO` da `config.sorgenti` (id=4);
* supporta filtri opzionali:
  * `p_competenza_mese`
  * `p_billing_account_id`
  * `p_limit`
  * `p_contratto_id` *(2026-05)* — vedi sezione dedicata

---

### Push singolo contratto (estensione coordinata)

> **Aggiunto:** 2026-05 — migration `20260510-03`

Il parametro `p_contratto_id` (tipo `vendite.contratti.id%TYPE`, default `NULL`) consente
di restringere il risultato a un singolo contratto.

| Valore  | Comportamento                                                  |
|---------|----------------------------------------------------------------|
| `NULL`  | Lista globale — comportamento batch invariato                  |
| `> 0`   | Filtra al contratto specificato; tutti gli altri filtri in AND |
| `<= 0`  | Guard: solleva `E_PUSH_SORGENTE_ID_INVALIDO` (id 433)          |

Estensione coordinata con le altre 4 `fn_list_*_da_pushare` per uniformare
la signature al client Python `CommesseRepository.fetch_pushable_rows` (4 args posizionali).

---

### Output (alto livello)

Restituisce per ogni riga candidata:
* contesto documento (`contratto_id`, `contratto_uid`, `riga_id`),
* dati commessa/competenza (`billing_account_id`, `utility_id`, `emittente`, `competenza_dal/al`),
* dati economici (`prezzo_snapshot`, `prezzo_bloccato`, `pricing_mode`),
* sorgente (`sorgente_tipo_id`, `sorgente_uid`, `segment_key`),
* `meta` tecnico per il push (include `periodicita`, `generazione_canone`, `tipo_erogazione`).

---

### Differenze rispetto a preventivi/ordini

| Aspetto | Preventivi/Ordini | Contratti |
|---------|------------------|-----------|
| **segment_key** | `PREV/ORD:<uid>:R:<id>` | `CONTR:<uid>:R:<id>:M:<YYYY-MM>` |
| **Ricorrenza** | Una tantum | Potenzialmente ricorrente |
| **quantita** | Dalla riga sorgente | `quantita_fissa` (puo` essere NULL) |
| **prezzo** | Dalla riga sorgente | `prezzo_unitario` (puo` essere NULL) |
| **valuta_id** | Dalla testata | NULL (handler deve risolvere) |
| **uom_id** | NULL (handler risolve) | NULL (handler risolve) |

---

### Esempi d'uso

**Batch globale (orchestrator):**

```sql
SELECT *
FROM vendite.fn_list_contratti_da_pushare(
  p_competenza_mese => DATE '2026-03-01',
  p_billing_account_id => NULL,
  p_limit => 500
);
```

**Push singolo contratto:**

```sql
SELECT *
FROM vendite.fn_list_contratti_da_pushare(
  p_contratto_id => 12345
);
```

---

{% include-markdown "signature-core.md" %}
