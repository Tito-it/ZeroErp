## 📘 Documentazione Concettuale – Tabella `vendite.listini_righe`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)  
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)  
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)  
>
### 🎯 Scopo Principale
La tabella `vendite.listini_righe` contiene i prezzi elementari per articolo/UOM,
eventualmente specializzati per contesto (BA, utility, emittente fiscale).

Rappresenta il livello usato dal resolver prezzi per selezionare il match piu`
specifico rispetto al contesto operativo.

---

### Regole principali

* FK obbligatorie su `listino_versione_id`, `articolo_id`, `uom_id`;
* dimensioni opzionali:
  * `billing_account_id`
  * `utility_id`
  * `emittente_soggetto_ruolo_id`
* `prezzo >= 0`;
* precisione prezzo operativa v1: `numeric(22,10)` nel percorso listino -> commessa -> attivita_fatturabili;
* una sola riga attiva per la stessa combinazione dimensionale
  (`uq_listini_righe_key_attiva` con coalesce delle dimensioni opzionali);
* ⭐ **articolo, unità di misura e versione sono l'identità della riga** (rev 2026-10-15,
  decisione di Tid): dopo l'inserimento non cambiano. Lo tiene il blocco di colonna
  (`dbops.automation_lock_columns`, codice `E_LISTINO_RIGA_IDENTITA_IMMUTABILE`); per cambiarli
  si elimina la riga e se ne crea una nuova. Il backend lo faceva già (non li accetta in
  modifica), il database no. È l'altro lato della regola che
  [vendite.trgfn_attivita_guard_listino_riga](/dbzero/vendite/manual/trgfn_attivita_guard_listino_riga)
  tiene sulle righe di commessa e sulle attività fatturabili che citano la riga: se la riga di
  listino cambiasse articolo, chi la cita resterebbe incoerente.

---

### Utilizzo previsto

* pricing puntuale per contesto utility/commercio;
* supporto fallback da combinazioni specifiche a combinazioni generiche;
* mantenimento precisione alta a monte; riduzione a 6 decimali demandata al layer `fatture_righe`;
* base tecnica per policy anti-ambiguita` del resolver.

---

{% include-markdown "signature-core.md" %}
