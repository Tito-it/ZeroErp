## 📘 Documentazione Concettuale – Tabella `vendite.listini_righe`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)  
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)  
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)  
>
---

### 🎯 Scopo Principale

La tabella `vendite.listini_righe` contiene i prezzi elementari per articolo/UOM,
eventualmente specializzati per contesto (BA, utility, emittente fiscale).

Rappresenta il livello usato dal resolver prezzi per selezionare il match piu`
specifico rispetto al contesto operativo.

---

### ✅ Regole principali

* FK obbligatorie su `listino_versione_id`, `articolo_id`, `uom_id`;
* dimensioni opzionali:
  * `billing_account_id`
  * `utility_id`
  * `emittente_soggetto_ruolo_id`
* `prezzo >= 0`;
* precisione prezzo operativa v1: `numeric(22,10)` nel percorso listino -> commessa -> attivita_fatturabili;
* una sola riga attiva per la stessa combinazione dimensionale
  (`uq_listini_righe_key_attiva` con coalesce delle dimensioni opzionali).

---

### 🧩 Utilizzo previsto

* pricing puntuale per contesto utility/commercio;
* supporto fallback da combinazioni specifiche a combinazioni generiche;
* mantenimento precisione alta a monte; riduzione a 6 decimali demandata al layer `fatture_righe`;
* base tecnica per policy anti-ambiguita` del resolver.

---

{% include-markdown "signature-core.md" %}
