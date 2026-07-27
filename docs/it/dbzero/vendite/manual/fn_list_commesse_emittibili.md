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
### 🎯 Scopo Principale
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

---

### Emissione mirata: `p_gruppi` (rev 2026-07-27)

Parametro `text[]`, default `NULL`. Restringe alle commesse che contengono
almeno una riga di un gruppo richiesto.

**Perché.** Questa è la discovery dello step di *pull*: il task cicla commessa
per commessa con un savepoint ciascuna. Senza filtro, un'emissione mirata su un
preventivo farebbe comunque il giro di tutte le commesse emittibili del
perimetro — savepoint, chiamata all'emit (già filtrato), zero righe. Nessun
danno ai dati, ma un log che dice «ho lavorato 40 commesse» per un'operazione
che ne riguardava una sola è fuorviante quando poi si va a leggere cos'è
successo.

⚠️ **Non sostituisce il filtro per riga dentro l'emit.** Qui si sceglie *quali
commesse* visitare, lì *quali righe* emettere. Una commessa multi-sorgente che
contiene sia il preventivo richiesto sia il contratto non richiesto passa
comunque il filtro: sarà l'emit a prendere solo le righe giuste.

Con `p_gruppi` valorizzato anche `total_non_emesse` segue il filtro: è il numero
di righe che l'emit lavorerà davvero su quella commessa.

> **Prerequisito di entrambe le discovery**: la commessa deve essere in uno
> stato **emittibile** (`stati_commessa.emittibile = true`). È il criterio 1,
> valutato prima di ogni filtro di perimetro.

{% include-markdown "signature-core.md" %}
