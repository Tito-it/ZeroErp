## 📘 Documentazione Concettuale – Tabella `vendite.registri_fatturazione`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.registri_fatturazione_progressivi](/dbzero/vendite/tabelle/registri_fatturazione_progressivi)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)  
> • [vendite.tipi_doc_fiscale_registri](/dbzero/vendite/manual/tipi_doc_fiscale_registri)  
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)  
>
---

### 🎯 Scopo Principale

(latest review 26-01-2026)
`vendite.registri_fatturazione` definisce i **registri fiscali di emissione**:
serie, regole di reset e collegamento all’emittente fiscale. Ogni fattura
si aggancia a un registro, che governa numerazione e perimetro fiscale.

---

### 🧱 Campi chiave (semantica)

* **Identita`**: `id`, `uid`, `codice`.
* **Emittente**: `emittente_soggetto_ruolo_id` (ruolo fiscale che emette).
* **Numerazione**: `serie_default`, `reset_policy` (es. ANNUALE).
* **Stato**: `attivo`.
* **Governance**: `meta`, `storicizza`, `tx_id`, audit.

---

### 🔗 Relazioni principali

* `vendite.fatture.registro_id` → determina la numerazione.
* `vendite.registri_fatturazione_progressivi` mantiene i contatori per anno/mese/serie.
* `vendite.tipi_doc_fiscale_registri` associa il registro al tipo documento fiscale.

---

### ✅ Nota sulla FK emittente

La FK su `emittente_soggetto_ruolo_id` e` **coerente** con un modello multi‑emittente:
ogni registro appartiene a un emittente fiscale specifico. In presenza di piu`
aziende abilitate, la separazione dei registri evita collisioni di numerazione.

---

{% include-markdown "signature-core.md" %}
