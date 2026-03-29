## 📘 Documentazione Concettuale – Tabella `config.tipi_documenti`

> 👀 **Vedi anche**
>
**Approfondimento backend:**    
>
• [API Lookup Codici Generica](/backend/core/manual/api_lookup_codici)    
>
### 🎯 Scopo Principale
(latest review 29-03-2026)
`config.tipi_documenti` definisce un catalogo generale dei **tipi documento**
utilizzati dal sistema come classificazione configurabile. Serve a distinguere
famiglie documentali omogenee tramite codici stabili, riusabili in lookup,
configurazioni e integrazioni.

---

### Campi chiave (semantica)

* **Identita` voce**: `id`, `codice`, `codice_interno`.
* **Descrizione funzionale**: `descrizione`.
* **Audit**: `data_insert`, `user_insert`, `data_update`, `user_update`.

---

### Regole operative

* `codice` e `codice_interno` devono restare **stabili** per non rompere mapping applicativi e integrazioni.
* La tabella e` adatta al lookup generico delle tabelle config con struttura `id / codice / descrizione`.
* I tipi vanno definiti con naming chiaro, evitando sovrapposizioni semantiche con cataloghi piu` specifici del dominio.

---

### Uso tipico nel processo

* classificazione trasversale di documenti in moduli diversi;
* alimentazione di select e filtri tramite endpoint lookup;
* supporto a regole applicative o reportistiche basate su tipologie documentali codificate.

---

{% include-markdown "signature-core.md" %}
