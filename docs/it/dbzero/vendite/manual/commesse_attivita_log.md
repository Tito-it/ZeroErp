## 📘 Documentazione Concettuale – Tabella `vendite.commesse_attivita_log`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
>

### 🎯 Scopo Principale
La tabella `vendite.commesse_attivita_log` registra eventi di dominio sulle righe
`commesse_attivita`, come audit persistente indipendente dal layer applicativo.

---

### Regole principali

* ogni log punta a una riga `commesse_attivita` esistente (`commessa_attivita_id`);
* `evento` obbligatorio (codice dell'evento di dominio);
* payload `dettaglio` in `jsonb` per traccia strutturata;
* audit (`data_/user_insert`, `tx_id`) gestito dai trigger della tabella.

---

### Writer e eventi

> ⚠️ **Storia (2026-07-21)**: fino alla porta oneri questa tabella **non aveva
> alcun writer** — il manuale precedente citava eventi «push/pull» e riallineamenti
> prezzo che nessuno scriveva (in particolare il «pull» che toglie righe dalla
> commessa **non esiste**: la commessa è un libro giornale, si corregge aggiungendo).
> Il testo è stato riscritto sul comportamento reale.

Writer attuali:

* **`ONERE_AGGIUNTO`** — scritto da `vendite.fn_aggiungi_onere_commessa` (porta oneri).
  Prima e unica scrittura reale: registra una voce di valore manuale caricata sulla
  commessa. `dettaglio` contiene causale, importo, motivo, istanza utility, tipo doc,
  segment. Vedi `brief-db-immutabilita-quantita-e-porta-oneri` §4c.

Nuovi writer (riallineamenti prezzo, altri eventi di dominio) si aggiungono a
questa tabella al bisogno, sempre con `evento` parlante e `dettaglio` strutturato.

---

{% include-markdown "signature-core.md" %}
