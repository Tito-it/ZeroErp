## 📘 Documentazione Concettuale – Tabella `config.tipi_attivita`

> 👀 **Vedi anche**
>
**Approfondimento backend:**    
>
• [API Lookup Codici Generica](/backend/core/manual/api_lookup_codici)    
>
### 🎯 Scopo Principale
(latest review 29-03-2026)
`config.tipi_attivita` definisce il catalogo dei **tipi di attivita`**
utilizzati dal sistema come classificazione configurabile. La tabella fornisce
un vocabolario stabile per distinguere categorie operative omogenee nei moduli
che richiedono una tipizzazione leggera basata su codice.

---

### Campi chiave (semantica)

* **Identita` voce**: `id`, `codice`, `codice_interno`.
* **Descrizione funzionale**: `descrizione`.
* **Audit**: `data_insert`, `user_insert`, `data_update`, `user_update`.

---

### Regole operative

* `codice` e `codice_interno` devono restare **stabili** per lookup, integrazioni e configurazioni applicative.
* La tabella e` compatibile con il lookup generico delle tabelle config basato su `id / codice / descrizione`.
* Le nuove tipologie vanno aggiunte mantenendo una nomenclatura coerente e non ambigua rispetto al dominio che le usa.

---

### Uso tipico nel processo

* classificazione di attivita` o causali operative in moduli applicativi;
* popolamento di combo/select tramite endpoint lookup;
* supporto a regole applicative che discriminano comportamenti in base al tipo codificato.

---

{% include-markdown "signature-core.md" %}
