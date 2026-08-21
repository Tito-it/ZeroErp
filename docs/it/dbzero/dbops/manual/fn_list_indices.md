## 📘 Documentazione Concettuale – Funzione `dbops.fn_list_indices`

> 👀 **Vedi anche**
>
> • [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Elenca gli **indici** di uno schema — o di una singola tabella — con nome, unicità, chiave
primaria e definizione completa (`pg_get_indexdef`).

È utilità di ispezione per il DBA: leggibile a colpo d'occhio, senza scrivere la join su
`pg_index`/`pg_class` ogni volta.

⚠️ Non è un cancello: non confronta con una policy e non segnala nulla. Per i duplicati esiste
`dbops.vw_duplicate_indexes`; per gli indici di FK, `dbops.fk_index_policy`.

---

{% include-markdown "signature-core.md" %}
