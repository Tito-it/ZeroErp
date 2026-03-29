## 📘 Documentazione Concettuale – Tabella `config.stati_doc_preventivi`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)    
> • [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)    
>
### 🎯 Scopo Principale
(latest review 29-03-2026)
`config.stati_doc_preventivi` definisce gli **stati documento** del ciclo dei
preventivi commerciali. Serve a governare il passaggio dalla proposta iniziale
alla sua accettazione, revisione o chiusura operativa.

---

### Campi chiave (semantica)

* **Identita` stato**: `id`, `codice`, `codice_interno`.
* **Ordine**: `ordine` per descrivere la progressione del preventivo nel processo commerciale.
* **Governance**: `attivo`, `meta`.
* **Audit**: `data_insert`, `user_insert`, `data_update`, `user_update`.

---

### Regole operative

* Lo stato e` usato da `vendite.preventivi.stato_doc_preventivo_id` come riferimento funzionale del documento.
* `codice` e `codice_interno` devono restare **stabili** per workflow, query e integrazioni.
* La disattivazione di uno stato gia` in uso su preventivi esistenti e` bloccata a livello DB.
* `ordine` va mantenuto coerente con la sequenza attesa del flusso commerciale, in particolare per stati come bozza, emesso, accettato, annullato.

---

### Uso tipico nel processo

* **Preparazione**: stati di lavoro per preventivi in costruzione o revisione.
* **Proposta/accettazione**: stati che qualificano il preventivo come presentato o accettato dal cliente.
* **Chiusura**: stati finali per annullo, superamento o completamento del ciclo.

---

{% include-markdown "signature-core.md" %}
