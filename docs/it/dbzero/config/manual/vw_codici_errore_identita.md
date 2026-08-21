## 📘 Documentazione Concettuale – Vista `config.vw_codici_errore_identita`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [config.codici_errore](/dbzero/config/tabelle/codici_errore)
>
Approfondimento viste:
> • [config.vw_codici_errore](/dbzero/config/views/vw_codici_errore)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**L'identità dei codici errore: una riga per codice, nessun join con le traduzioni.**

È la sorgente del generatore lato backend. La sua unica promessa — quella che la rende
diversa dalla gemella `vw_codici_errore` — è la **cardinalità**: un codice, una riga. Sempre.

Espone `codice`, `classe`, `obsoleto_dal`, `note`.

---

### ⚠️ Perché esiste, se c'è già la tabella

Perché la promessa sia **dichiarata** e non solo di fatto. Un consumatore che generi codice a
partire dal catalogo (una enum, una mappa) va in pezzi se lo stesso codice arriva due volte:
la gemella `vw_codici_errore` fa esattamente questo, perché unisce le traduzioni e un codice
tradotto in due lingue compare due volte.

Le due viste sembrano una il superset dell'altra. **Non lo sono**: hanno due contratti
diversi, e questo è il contratto «uno a uno». Chi genera codice usa questa; chi rivede i testi
usa quella.

---

### `ORDER BY` nel corpo

C'è un `ORDER BY codice` dentro la vista: rende stabile l'output del generatore, così un
rigenerato non produce diff spurî per il solo riordino.

⚠️ Un `ORDER BY` dentro una vista **non sopravvive** a una query esterna che ne imponga uno
proprio, e non va dato per garantito a valle. Chi ha bisogno di quell'ordine lo ripete.

---

### Scope

`WITH (security_invoker = true)`. Qui è formale — `config.codici_errore` non ha RLS — ma è
la forma corretta e va **ri-specificata a ogni `CREATE OR REPLACE VIEW`**: PostgreSQL azzera
le reloptions quando si riscrive una vista senza `WITH (...)`. È un incidente già capitato nel
progetto su un'altra famiglia di viste.

---

{% include-markdown "signature-core.md" %}
