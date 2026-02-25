## 📘 Documentazione Concettuale – Funzione `vendite.fn_list_consumi_da_pushare(...)`

> 👀 **Vedi anche**
>
> * [vendite.attivita_consumi](/dbzero/vendite/tabelle/attivita_consumi)
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> * [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa)
> * [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)
> * [WIP: Modello fatturazione utilities](../../../dev/work-in-progress/modello-fatturazione-utilities-gas-ee-idrico.md)

---

### 🎯 Scopo Principale

`vendite.fn_list_consumi_da_pushare(...)` seleziona i consumi utility
pronti per il push verso `commesse_attivita`, restituendo un payload di base
per l'handler di calcolo componenti.

A differenza delle sorgenti commerciali (preventivi, ordini) dove il mapping
e 1 riga → 1 `commesse_attivita`, un consumo genera **N componenti fatturabili**
(consumo per fascia, canoni fissi, oneri, accise, ecc.).
Il fan-out 1→N e responsabilita dell'handler, non di questa funzione.

---

### ✅ Regole principali

* considera consumi con `stato_calcolo = 'OK'` (esclusi WARNING/ERRORE);
* esclude consumi gia fatturati sul percorso legacy (`fattura_id IS NULL`);
* esclude consumi con segment_key gia EMESSA in `commesse_attivita` (idempotenza batch);
* costruisce `segment_key` base (`CONS:{uid}`); l'handler espande in
  `CONS:{uid}:COMP:{componente}` per ogni componente;
* restituisce `articolo_id = NULL` e `valuta_id = NULL`:
  l'handler deve risolverli da configurazione;
* `prezzo_bloccato = FALSE`: i consumi sono sempre ricalcolabili da listino;
* sorgente tipo: `ATTIVITA_CONSUMI` da `config.sorgenti` (id=12);
* supporta filtri opzionali:
  * `p_competenza_mese`
  * `p_billing_account_id`
  * `p_limit`

---

### 📦 Output (alto livello)

Restituisce per ogni consumo candidato:
* contesto consumo (`consumo_id`, `consumo_uid`),
* dati commessa/competenza (`billing_account_id`, `utility_id`, `emittente`, `competenza_dal/al`),
* dati economici (`prezzo_snapshot = NULL`, `prezzo_bloccato = FALSE`, `pricing_mode = FIXED`),
* sorgente (`sorgente_tipo_id`, `sorgente_uid`, `segment_key`),
* quantita grezza (`consumo_totale` come `quantita` e `qta_operativa`),
* `meta` tecnico con periodo, stato_calcolo, tipo_commessa/policy.

---

### 🔄 Flusso nel contesto pipeline

```
attivita_consumi (stato_calcolo = OK)
    |
    v
fn_list_consumi_da_pushare (questa funzione — 1 riga per consumo)
    |
    v
Handler utility-specific (gas_v1, energia_v1, idrico_v1):
    fan-out 1 consumo → N componenti fatturabili
    |
    v
fn_get_or_create_commessa (AUTO) + fn_upsert_commessa_attivita x N
    |
    v
fn_emit_attivita_fatturabili_da_commessa → attivita_fatturabili x N
```

---

### 🧪 Esempio d'uso

```sql
SELECT *
FROM vendite.fn_list_consumi_da_pushare(
  p_competenza_mese => DATE '2026-02-01',
  p_billing_account_id => NULL,
  p_limit => 500
);
```

---

{% include-markdown "signature-core.md" %}
