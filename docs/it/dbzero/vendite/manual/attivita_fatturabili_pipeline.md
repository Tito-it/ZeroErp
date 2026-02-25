## 📘 Documentazione Concettuale – Tabella `vendite.attivita_fatturabili_pipeline`

> 👀 **Vedi anche**
>
> **Approfondimento funzioni:**
>
> • [`vendite.fn_resolve_attivita_pipeline_step`](/dbzero/vendite/funzioni/fn_resolve_attivita_pipeline_step)  
> • [`vendite.fn_list_attivita_pipeline_steps`](/dbzero/vendite/funzioni/fn_list_attivita_pipeline_steps)  
>
> **Guide:**
>
> • [Fatturazione](/guide/fatturazione)  

---

### 🎯 Scopo Principale

**DEPRECATA DA COMMESSE** — pipeline attivita` legacy sostituita dal flusso commessa-only.
Tutte le righe disabilitate (`attivo=false`) dal changeset `20260224-41`.
Candidata a DROP dopo go-live. Rif: `gestione-commesse-v2.md` §25.4, §27.

(latest review 16-02-2026)
La tabella **`vendite.attivita_fatturabili_pipeline`** configura gli step della pipeline
del dominio **attivita_fatturabili**, separata dalla pipeline fatturazione documenti.

Ogni riga rappresenta uno step con:

* codice step (`codice_step`)
* ordine di esecuzione (`ordine`)
* task JSON (`processi`)
* task JSON di rollback (`rollback`)
* filtri opzionali (`utility_id`, `sorgente_tipo_id`) con fallback su `NULL`

---

### ✅ Regole principali

* Pipeline dominio-specifica: non mescola stati/documenti della fatturazione.
* Risoluzione configurazione con fallback:
  1. `utility_id + sorgente_tipo_id`
  2. `utility_id`
  3. `sorgente_tipo_id`
  4. fallback globale (`NULL/NULL`)
* `processi` e `rollback` sono JSONB, consumati dal runner applicativo.
* `attivo=true` abilita lo step.

---

### 🧪 Esempio record

```json
{
  "codice_step": "RACCOLTA_INPUT",
  "ordine": 10,
  "processi": [
    {
      "task": "noop",
      "fase": "Placeholder raccolta input",
      "params": {"implementation_key": "default"}
    }
  ],
  "rollback": []
}
```

---

{% include-markdown "signature-core.md" %}
