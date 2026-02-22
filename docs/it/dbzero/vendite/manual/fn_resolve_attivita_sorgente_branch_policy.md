## 📘 Documentazione Concettuale – Funzione `vendite.fn_resolve_attivita_sorgente_branch_policy`

### 🎯 Scopo Principale

Restituisce la policy runtime sorgente -> branch per la pipeline
`ATTIVITA_FATTURABILI`, con filtro opzionale sulle sole sorgenti abilitate.

---

### ✅ Regole principali

* `p_sorgente_tipo_id` obbligatorio (`> 0`).
* considera solo record `attivo=true`.
* se `p_require_abilitata=true` (default) ritorna solo policy con `abilitata=true`.
* risoluzione ordinata per `priorita`, poi `id`.
* in assenza policy valida genera errore applicativo `scope=ATTIVITA_FATTURABILI`.

---

### ✅ Output

Una riga con:
* `sorgente_tipo_id`
* `branch_code`
* `abilitata`
* `acquisizione_mode`
* `block_scope`
* `priorita`
* `meta`

---

### 🧩 Utilizzo previsto

* chiamata dal runner/repository backend prima del dispatch task,
* elimina branch mapping hardcoded,
* riduce regressioni quando cambia lo scope sorgenti attive.

---

{% include-markdown "signature-core.md" %}
