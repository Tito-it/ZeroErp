## 📘 Documentazione Concettuale – Funzione `pratiche.fn_pratica_del_documento(p_sorgente_tipo_id, p_sorgente_uid)`

> 👀 **Vedi anche**
>
> [vendite.fn_documento_lineage_sintesi](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi) — la sintesi della lineage, che la legge
> Le sette viste di lista di `vendite` (`vw_*_lista`) — colonne `pratica_id`, `pratica_numero`, `n_pratiche`
> Brief: `docs/it/dev/work-done/brief-db-lineage-seminata-per-chiave.md` §8.6-§8.7

---
### 🎯 Scopo Principale
(rev 2026-10-11)

**La pratica di un documento**: quante pratiche lo hanno fra le sorgenti, la
prima (per id) e il suo codice. Una riga sempre: senza pratiche, il conteggio è 0
e le altre colonne sono vuote.

È la sede unica di questa regola. Prima stava dentro la sintesi della lineage,
calcolata per tutti i documenti; ora la leggono per chiave sia le liste (dove la
pratica è filtrabile e ordinabile) sia la sintesi.

Il documento si indica con la sua chiave del grafo: il tipo
(`config.sorgenti.id`) e la chiave resa a testo — `uid` per preventivi e offerte,
`id` per gli altri.

{% include-markdown "signature-core.md" %}
