## 📘 Documentazione Concettuale – Funzione `vendite.fn_list_commessa_attivita`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.commesse](/dbzero/vendite/tabelle/commesse)  
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti)  
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_get_commessa_stato](/dbzero/vendite/funzioni/fn_get_commessa_stato)  
> • [vendite.fn_list_commesse_emittibili](/dbzero/vendite/funzioni/fn_list_commesse_emittibili)  
>
---

### 🎯 Scopo Principale

(latest review 26-02-2026)  
Restituisce il dettaglio righe di una commessa (`commesse_attivita`) con filtri opzionali e paginazione, per uso backend in consultazione e pre-validazione dei flussi di emissione.

---

### ✅ Regole principali

* Funzione read-only (`STABLE`).
* `p_commessa_id` obbligatorio (`> 0`).
* Errore esplicito se la commessa non esiste.
* Filtri opzionali:
  * `p_stato_emissione`
  * `p_stato_approvazione`
  * `p_competenza_mese` (normalizzato al primo giorno del mese)
* Paginazione:
  * `p_limit` default `1000`, massimo `10000`
  * `p_offset` minimo `0`
* Include `sorgente_codice` tramite join su `config.sorgenti`, evitando risoluzioni N+1 lato backend.

---

### ✅ Output

Elenco righe `commesse_attivita` della commessa con i principali campi operativi:

* identificativi (`id`, `commessa_id`, `segment_key`)
* dati di competenza/quantita`/prezzo
* stati (`stato_approvazione`, `stato_emissione`)
* classificazione sorgente (`sorgente_tipo_id`, `sorgente_codice`)
* `meta` e `data_update`

---

### 🧪 Esempio d'uso

```sql
SELECT *
FROM vendite.fn_list_commessa_attivita(
  p_commessa_id => 12345,
  p_stato_emissione => 'NON_EMESSA',
  p_stato_approvazione => NULL,
  p_competenza_mese => DATE '2026-02-01',
  p_limit => 200,
  p_offset => 0
);
```

---

{% include-markdown "signature-core.md" %}
