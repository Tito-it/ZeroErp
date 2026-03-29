## 📘 Documentazione Concettuale – Tabella `config.stati_doc_ddt`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [vendite.ddt](/dbzero/vendite/tabelle/ddt)    
> • [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)    
>
### 🎯 Scopo Principale
(latest review 29-03-2026)
`config.stati_doc_ddt` definisce gli **stati documento** dei Documenti di
Trasporto. Centralizza il vocabolario di stato usato nel ciclo logistico, dalla
emissione alla consegna o agli eventuali esiti finali.

---

### Campi chiave (semantica)

* **Identita` stato**: `id`, `codice`, `codice_interno`.
* **Ordine**: `ordine` per descrivere la sequenza attesa del flusso logistico.
* **Governance**: `attivo`, `meta`.
* **Audit**: `data_insert`, `user_insert`, `data_update`, `user_update`.

---

### Regole operative

* Lo stato e` referenziato da `vendite.ddt.stato_doc_ddt_id` come stato ufficiale della testata DDT.
* `codice` e `codice_interno` devono restare **immutabili** dal punto di vista funzionale.
* La disattivazione di stati gia` usati da DDT esistenti e` bloccata a livello DB.
* `ordine` deve rispecchiare la progressione operativa del documento, utile per workflow, filtri e push verso processi successivi.

---

### Uso tipico nel processo

* **Emissione**: creazione del DDT e avvio del flusso di spedizione.
* **Transito/consegna**: avanzamento dello stato in base agli eventi logistici.
* **Esiti finali**: gestione di consegna completata, reso o annullo secondo le regole del dominio.

---

{% include-markdown "signature-core.md" %}
