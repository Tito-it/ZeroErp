## 📘 Documentazione Concettuale – Tabella `config.tipi_evento_assets`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [magazzino.eventi_assets](/dbzero/magazzino/tabelle/eventi_assets)    
>
### 🎯 Scopo Principale
(latest review 29-03-2026)
`config.tipi_evento_assets` definisce il catalogo dei **tipi evento** usati per
registrare il ciclo di vita operativo degli asset. Centralizza il vocabolario
con cui gli eventi vengono classificati in `magazzino.eventi_assets`.

---

### Campi chiave (semantica)

* **Identita` tipo evento**: `id`, `codice`, `codice_interno`.
* **Descrizione**: `descrizione`.
* **Ordine**: `ordine` per eventuali ordinamenti logici o presentazione in UI.
* **Governance**: `attivo`, `meta`.
* **Audit**: `data_insert`, `user_insert`, `data_update`, `user_update`.

---

### Regole operative

* Il tipo evento e` referenziato da `magazzino.eventi_assets.tipo_evento_id`.
* `codice` e `codice_interno` devono restare **immutabili** dal punto di vista funzionale.
* La disattivazione di tipi gia` usati in eventi asset esistenti e` bloccata da trigger DB.
* `meta` puo` ospitare configurazioni accessorie legate alla natura dell'evento, senza duplicare campi core.

---

### Uso tipico nel processo

* classificazione di movimenti, cambi stato, assegnazioni o altri eventi rilevanti sugli asset;
* filtraggio e reporting degli eventi per categoria;
* supporto a workflow applicativi che reagiscono in modo diverso al tipo evento registrato.

---

{% include-markdown "signature-core.md" %}
