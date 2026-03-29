## 📘 Documentazione Concettuale – Tabella `config.stati_doc_contratti`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [vendite.contratti](/dbzero/vendite/tabelle/contratti)    
> • [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe)    
>
### 🎯 Scopo Principale
(latest review 29-03-2026)
`config.stati_doc_contratti` definisce gli **stati documento** del ciclo di vita
dei contratti commerciali. Fornisce un catalogo centralizzato per rappresentare
le fasi operative del contratto, dalla bozza fino alla chiusura.

---

### Campi chiave (semantica)

* **Identita` stato**: `id`, `codice`, `codice_interno`.
* **Ordine**: `ordine` per esprimere una progressione logica degli stati.
* **Governance**: `attivo`, `meta`.
* **Audit**: `data_insert`, `user_insert`, `data_update`, `user_update`.

---

### Regole operative

* Lo stato e` usato da `vendite.contratti.stato_doc_contratto_id` come riferimento funzionale univoco.
* `codice` e `codice_interno` devono restare **stabili** per non rompere query, mapping applicativi e integrazioni.
* La disattivazione di uno stato gia` usato da contratti esistenti e` bloccata da trigger DB.
* `ordine` va mantenuto coerente con la sequenza attesa del processo contrattuale.

---

### Uso tipico nel processo

* **Apertura**: stati iniziali per bozze o contratti in preparazione.
* **Attivazione**: stati che rendono il contratto operativo e fatturabile.
* **Chiusura**: stati finali per cessazione, annullo o completamento del rapporto.

---

{% include-markdown "signature-core.md" %}
