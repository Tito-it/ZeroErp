## 📘 Documentazione Concettuale – Tabella `vendite.attivita_fatturabili_sorgenti_branch_policy`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti)  
> • [vendite.attivita_fatturabili_pipeline_task_policy](/dbzero/vendite/tabelle/attivita_fatturabili_pipeline_task_policy)  
>
---

### 🎯 Scopo Principale

**DEPRECATA DA COMMESSE** — sostituita da `config.sorgenti.scope` + handler commessa-v2.
Tutte le righe disabilitate (`abilitata=false`) dal changeset `20260224-41`.
Candidata a DROP dopo go-live. Rif: `gestione-commesse-v2.md` §27.

La tabella `vendite.attivita_fatturabili_sorgenti_branch_policy` centralizza la
mappatura tra sorgente (`config.sorgenti`) e policy runtime del dominio
`ATTIVITA_FATTURABILI`.

Evita mapping hardcoded lato backend e consente di governare in DB:

* branch target (`branch_code`),
* abilitazione sorgente (`abilitata`),
* modalita` ingest (`acquisizione_mode`),
* scope blocco default (`block_scope`),
* priorita` risoluzione (`priorita`).

---

### ✅ Regole principali

* Unicita` per sorgente: `sorgente_tipo_id`.
* `acquisizione_mode` ammessi:
  * `PUSH`
  * `PULL`
* `block_scope` ammessi:
  * `BRANCH`
  * `GLOBAL`
* `priorita` deve essere `> 0`.
* Solo righe `attivo=true` sono considerate in runtime.

---

### 🧩 Utilizzo previsto

* risoluzione policy sorgente in apertura pipeline attività;
* switch rapido attivo/disattivo per sorgenti posticipate;
* gestione progressiva di canali futuri (`DDT*`, `FATTURA*`, `*_RIGA`) senza refactor backend.

---

{% include-markdown "signature-core.md" %}
