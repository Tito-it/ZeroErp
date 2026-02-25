## 📘 Documentazione Concettuale – Funzione `vendite.fn_list_attivita_sorgenti_abilitate`

### 🎯 Scopo Principale

**DEPRECATA DA COMMESSE** — nessun chiamante attivo dopo il passaggio a commessa-only (24-02-2026).
Candidata a DROP dopo go-live. Rif: `gestione-commesse-v2.md` §27.

Restituisce l'elenco delle sorgenti abilitate per la pipeline
`ATTIVITA_FATTURABILI`, con ordinamento centralizzato lato DB.

---

### ✅ Regole principali

* filtra solo record policy con:
  * `attivo = true`
  * `abilitata = true`
* ordinamento stabile: `priorita`, `id`.
* parametro `p_utility_id` supportato per compatibilita` interfaccia;
  al momento non applica filtri specifici.

---

### ✅ Output

Ritorna una tabella con:
* `sorgente_tipo_id`
* `branch_code`
* `abilitata`
* `acquisizione_mode`
* `block_scope`
* `priorita`
* `meta`

---

### 🧪 Esempio d'uso

```sql
SELECT *
FROM vendite.fn_list_attivita_sorgenti_abilitate(NULL)
ORDER BY priorita;
```

---

### 🧩 Utilizzo previsto

* repository/backend per ottenere l'elenco sorgenti processabili;
* eliminazione query inline hardcoded nel codice applicativo;
* configurabilita` policy tramite seed DB senza deploy backend.

---

{% include-markdown "signature-core.md" %}

