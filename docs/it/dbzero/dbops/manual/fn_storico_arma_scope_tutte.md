## 📘 Documentazione Concettuale – Funzione `dbops.fn_storico_arma_scope_tutte`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — dove finisce il riepilogo della corsa
>
> Approfondimento funzioni:
>
> * [dbops.fn_storico_arma_scope](/dbzero/dbops/funzioni/fn_storico_arma_scope) — la primitiva, applicata qui a ogni madre
> * [dbops.fn_storico_backfill_scope_tutte](/dbzero/dbops/funzioni/fn_storico_backfill_scope_tutte) — la gemella per le versioni già scritte
> * [dbops.fn_grant_storico_shadows](/dbzero/dbops/funzioni/fn_grant_storico_shadows) — la stessa forma per i privilegi delle shadow
>
> Guide:
>
> * [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle) — la sezione «Di chi è una versione»

---

### 🎯 Scopo Principale

Applica `dbops.fn_storico_arma_scope` alla shadow di ogni madre che porta il trigger di storico, e
registra un riepilogo della corsa nell'audit. È la convergenza dello scope congelato: porta alla
forma decisa le shadow che esistono già, quelle che il generatore non ha visto nascere.

---

### ⭐ Il marcatore è il trigger, non un elenco

Le madri si trovano dal catalogo: ogni tabella con un trigger su `script.trgfn_storico_generic`.
Una madre che entra nella storicizzazione entra qui da sola, una che ne esce esce da sola, e
nessun elenco va tenuto allineato. Due madri omonime contano come due madri, anche se scrivono
nella stessa shadow.

---

### Il riepilogo

La funzione restituisce, e scrive nell'audit, quante madri ha visto, quante shadow ha allineato,
quante sono armate, quante ha saltato perché di un altro proprietario e quante madri non hanno
ancora una shadow. Lo status del riepilogo è `WARN` se almeno una shadow è stata saltata per il
proprietario, `DRYRUN` in simulazione, `OK` altrimenti. Il riepilogo si scrive a ogni corsa, anche
quando non c'era niente da fare.

---

### Chi la chiama

* un changeSet di `90_end` che gira a **ogni** migrate: fa convergere ciò che nasce fra due migrate
  (shadow create dal job, righe di mappa che passano da `NESSUNO` a un modo);
* un changeSet in coda alla passata `ci_apply`, anche lui a ogni passata: su un database ricostruito
  da zero i trigger di storico li monta proprio quella passata, e la convergenza di `90_end` gira
  prima di loro;
* `scripts/sql/provision_storico_scope.sql`, da superuser, per le shadow che il migratore non possiede.

---

### Test

* `db/pgtap/storico/test-storico-scope-congelato-v1.sql` — l'invariante che la convergenza tiene: ogni
  shadow di una madre col trigger ha le colonne dello scope, ogni shadow di una madre protetta è
  armata, nessuna è armata se tutte le sue madri sono `NESSUNO`.

---

### Note di migrazione

* 2026-09-11 — nasce con lo scope congelato (`brief-db-rls-storico-scope-congelato`, §4b), insieme
  alla primitiva.
* 2026-09-12 — la convergenza si ripete in coda a `ci_apply`: in CI le shadow create in `00_schema`
  restavano senza colonne, perché la passata principale le cercava prima che esistessero i trigger.

---

{% include-markdown "signature-core.md" %}
