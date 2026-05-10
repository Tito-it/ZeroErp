## Documentazione Concettuale – Funzione `vendite.fn_list_ordini_da_pushare(...)`

> **Vedi anche**
>
[vendite.ordini](/dbzero/vendite/tabelle/ordini)
> [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
> [vendite.fn_list_ddt_da_pushare](/dbzero/vendite/funzioni/fn_list_ddt_da_pushare) — funzione complementare per DDT
> [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa)
> [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)

---
### 🎯 Scopo Principale
`vendite.fn_list_ordini_da_pushare(...)` seleziona le righe ordine
pronte per il push verso `commesse_attivita`, restituendo un payload completo
per l’handler di acquisizione.

**Solo ordini con `fatturazione_trigger = ‘CONFERMATO’`** sono gestiti
da questa funzione. Ordini con trigger `SPEDITO` o `CONSEGNATO` sono
delegati a `fn_list_ddt_da_pushare`.

---

### Regole principali

* considera ordini in stato documento `CONFERMATO`;
* **`fatturazione_trigger = ‘CONFERMATO’`** (esclusione reciproca con DDT);
* include solo righe attive con quantita` e prezzo validi;
* esclude segmenti gia` emessi in `commesse_attivita` (idempotenza batch);
* costruisce `segment_key` deterministica (`ORD:{uid}:R:{riga_id}`);
* forza `prezzo_bloccato = TRUE` (ordine confermato);
* supporta filtri opzionali:
  * `p_competenza_mese`
  * `p_billing_account_id`
  * `p_limit`
  * `p_ordine_id` *(2026-05)* — vedi sezione dedicata

---

### Push singolo ordine (estensione coordinata)

> **Aggiunto:** 2026-05 — migration `20260510-02`

Il parametro `p_ordine_id` (tipo `vendite.ordini.id%TYPE`, default `NULL`) consente
di restringere il risultato a un singolo ordine.

| Valore  | Comportamento                                                |
|---------|--------------------------------------------------------------|
| `NULL`  | Lista globale — comportamento batch invariato                |
| `> 0`   | Filtra all'ordine specificato; tutti gli altri filtri in AND |
| `<= 0`  | Guard: solleva `E_PUSH_SORGENTE_ID_INVALIDO` (id 433)        |

Estensione coordinata con le altre 4 `fn_list_*_da_pushare` per uniformare
la signature al client Python `CommesseRepository.fetch_pushable_rows` (4 args posizionali).

---

### Esclusione reciproca con DDT

| `fatturazione_trigger` | Chi pusha | Funzione |
|------------------------|-----------|----------|
| `CONFERMATO` | Ordine alla conferma | `fn_list_ordini_da_pushare` |
| `SPEDITO` | DDT alla spedizione | `fn_list_ddt_da_pushare` |
| `CONSEGNATO` | DDT alla consegna | `fn_list_ddt_da_pushare` |

Il valore di `fatturazione_trigger` e` ereditato da
`billing_account.fatturazione_ordini` al momento dell’inserimento ordine
(via `trgfn_ordini_normalize`).

---

### 📦 Output (alto livello)

Restituisce per ogni riga candidata:
* contesto documento (`ordine_id`, `ordine_uid`, `riga_id`),
* dati commessa/competenza,
* dati economici (`prezzo_snapshot`, `prezzo_bloccato`, `pricing_mode`),
* sorgente (`sorgente_tipo_id`, `sorgente_uid`, `segment_key`),
* `meta` tecnico per il push.

---

### Esempi d’uso

**Batch globale (orchestrator):**

```sql
SELECT *
FROM vendite.fn_list_ordini_da_pushare(
  p_competenza_mese => DATE ‘2026-02-01’,
  p_billing_account_id => NULL,
  p_limit => 500
);
```

**Push singolo ordine:**

```sql
SELECT *
FROM vendite.fn_list_ordini_da_pushare(
  p_ordine_id => 12345
);
```

---

{% include-markdown "signature-core.md" %}
