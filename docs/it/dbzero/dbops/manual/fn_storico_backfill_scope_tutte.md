## 📘 Documentazione Concettuale – Funzione `dbops.fn_storico_backfill_scope_tutte`

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
> * [dbops.fn_storico_backfill_scope](/dbzero/dbops/funzioni/fn_storico_backfill_scope) — la primitiva, applicata qui a ogni madre
> * [dbops.fn_storico_arma_scope_tutte](/dbzero/dbops/funzioni/fn_storico_arma_scope_tutte) — la gemella che mette le colonne
>
> Guide:
>
> * [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle) — la sezione «Di chi è una versione»

---

### 🎯 Scopo Principale

Applica `dbops.fn_storico_backfill_scope` a ogni madre che porta il trigger di storico e registra un
riepilogo nell'audit: quante madri, quante versioni attribuite, quante versioni restano senza
origine in tutto lo schema `storico`, quante madri sono state saltate.

---

### ⭐ Le versioni senza origine si contano a fine giro

Il conteggio delle versioni ancora senza origine non è la somma dei conteggi delle singole
chiamate: in una shadow condivisa la prima madre vede ancora le versioni che la seconda sta per
attribuire, e la somma le conterebbe due volte. Si contano alla fine, una volta per shadow, su ogni
tabella di `storico` che ha la colonna di origine.

Una madre si conta come saltata quando la primitiva risponde `SENZA_COLONNE`, `NON_ATTRIBUIBILE` o
`NO_SHADOW`; con almeno una madre saltata il riepilogo ha status `WARN`, altrimenti `OK`. Il
riepilogo si scrive a ogni corsa.

Le madri si trovano dal catalogo, dal trigger su `script.trgfn_storico_generic`: nessun elenco.

---

### Chi la chiama

Un changeSet di `90_end`, **una volta sola**: è una migrazione del pregresso, e le versioni nuove le
scrive il trigger già complete. E `scripts/sql/provision_storico_scope.sql`, da superuser, dopo aver
riassegnato e armato le shadow di un altro proprietario.

---

### Note di migrazione

* 2026-09-11 — nasce con lo scope congelato (`brief-db-rls-storico-scope-congelato`, §4b e §5), per
  attribuire le versioni scritte prima di quel giorno.

---

{% include-markdown "signature-core.md" %}
