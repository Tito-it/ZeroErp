## 📘 Documentazione Concettuale – Funzione `vendite.fn_list_commesse_emittibili`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse](/dbzero/vendite/tabelle/commesse)  
> • [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa)  
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_commessa_stato](/dbzero/vendite/funzioni/fn_get_commessa_stato)  
> • [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa)  
>
🎯 Scopo Principale

(latest review 26-02-2026)  
Elenca le commesse candidate all'emissione verso `attivita_fatturabili`, applicando i criteri minimi di prontezza operativa.

---

### Regole principali

* Funzione read-only (`STABLE`).
* Restituisce solo commesse con:
  * stato `emittibile = true` in `vendite.stati_commessa`
  * almeno una riga `commesse_attivita` con `stato_emissione = NON_EMESSA`.
* `p_competenza_mese` e` opzionale:
  * se presente, viene normalizzato al primo giorno del mese
  * filtra le righe attivita` sulla stessa competenza.
* Filtri opzionali di perimetro:
  * `p_billing_account_id`
  * `p_utility_id`
* `p_limit` normalizzato:
  * default `1000`
  * massimo `10000`.

---

### Output

Per ogni commessa idonea restituisce:

* identificativi principali (`commessa_id`, `codice`, `stato_commessa_id`, `stato_commessa`)
* perimetro billing (`billing_account_id`, `utility_id`, `emittente_soggetto_ruolo_id`)
* competenza testata (`competenza_dal`, `competenza_al`)
* `total_non_emesse` (numero righe ancora da emettere)

---

### Esempio d'uso

```sql
SELECT *
FROM vendite.fn_list_commesse_emittibili(
  p_competenza_mese => DATE '2026-02-01',
  p_billing_account_id => NULL,
  p_utility_id => NULL,
  p_limit => 500
);
```

---

{% include-markdown "signature-core.md" %}
