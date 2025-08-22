## 📘 Documentazione Concettuale – Tabella `dbops.automation_scope`

> 👀 **Vedi anche**
>
> * Orchestratori: `dbops.fn_run_automations`, `dbops.run_automations_tx_id`, `dbops.run_automations_audit_update`, `dbops.run_automations_storico`, `dbops.fn_run_automations_attivo`
> * Tabelle correlate: `dbops.automation_rules_tbl`, `dbops.automation_overrides_cols`, `dbops.automation_fk_exclusions`

### 🎯 Scopo Principale

Definire **l’elenco degli schemi** su cui gli orchestratori di automazione devono operare. Funziona come una **allow‑list**: se presente e popolata, limita l’esecuzione alle sole voci elencate.

> Se `automation_scope` è **vuota** o **assente**, gli orchestratori applicano la logica di fallback: tutti gli schemi **user** (non `pg_%`, non `information_schema`) **escludendo** `storico`.

---

### 🔎 Precedenza dello *scope*

1. **Parametro** `p_schemas` passato alla funzione → *ha priorità massima* (ignora la tabella).
2. **Tabella** `dbops.automation_scope` (se esiste e contiene righe).
3. **Fallback**: introspezione catalogo → tutti gli schemi user escluso `storico`.

> Questa scelta evita sorprese in ambienti dove vuoi forzare un sottoinsieme stabile di schemi.

---

### 🧩 Casi d’uso

* **Ambienti multi‑schema**: limita l’automazione a 3‑4 schemi principali.
* **Testing controllato**: in test popola con uno schema “lab” e verifica i risultati.
* **Rollout progressivo**: abilita via via nuovi schemi aggiungendo righe.

---

### ✍️ Esempi

**Impostare lo scope a 4 schemi core**

```sql
INSERT INTO dbops.automation_scope(schema_name, note)
VALUES ('anagrafiche','core anagrafiche'),
       ('vendite','modulo vendite'),
       ('catalogo','catalogo prodotti'),
       ('config','configurazioni di sistema');
```

**Usare uno scope “temporaneo” senza toccare la tabella**

```sql
SELECT dbops.fn_run_automations('CI', ARRAY['lab'], true, ARRAY['TX_ID']);
```

---

### 🔍 Troubleshooting

* Nessun effetto? Controlla se `automation_scope` è popolata e i nomi schema sono corretti (minuscoli se non quotati).
* Ricorda che `p_schemas` **sovrascrive** lo scope tabellare.
* Se lo scope è vuoto, la funzione può ricadere sul fallback (tutti gli schemi user, escluso `storico`).

---


### 🔒 Vincoli (logici)

* Unicità consigliata: `PRIMARY KEY (schema_name)`.
* Se esiste `enabled`, gli orchestratori possono considerare **solo** le righe `enabled=true`.

### 🚀 Interazione con gli orchestratori

* In assenza del parametro `p_schemas`, gli orchestratori leggono `SELECT array_agg(DISTINCT schema_name) FROM dbops.automation_scope` (eventualmente filtrando `enabled=true`).
* Se la tabella non esiste o non ha righe, si usa il fallback su catalogo (`pg_namespace`).

---

### 🧠 Best practice

* Mantieni la lista **minima** necessaria all’ambiente.
* Evita di inserire `storico` nello scope a meno di motivazioni specifiche.
* Versiona le modifiche allo scope con changeSet dedicati per tracciabilità.

---

{% include-markdown "signature-core.md" %}