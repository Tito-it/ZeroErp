## 📘 Documentazione Concettuale – Funzione `vendite.fn_documento_lineage_nodi(p_tipo_ids, p_uids)`

> 👀 **Vedi anche**
>
> [vendite.vw_documento_lineage_nodi](/dbzero/vendite/views/vw_documento_lineage_nodi) — la stessa cosa per tutti i documenti
> [vendite.fn_documento_lineage_archi](/dbzero/vendite/funzioni/fn_documento_lineage_archi) — gli archi, con lo stesso seme
> Brief: `docs/it/dev/work-done/brief-db-lineage-seminata-per-chiave.md` §8.2-§8.3

---
### 🎯 Scopo Principale
(rev 2026-10-11)

I **documenti** del grafo della lineage — una riga per documento, con codice,
stato, fase, natura fiscale — **per i soli documenti che si chiedono**. La vista
[`vw_documento_lineage_nodi`](vw_documento_lineage_nodi.md) ne è la proiezione
«senza seme», cioè tutti i documenti.

Il seme è lo stesso di
[`fn_documento_lineage_archi`](fn_documento_lineage_archi.md): la chiave del nodo
(tipo e chiave del documento resa a testo) in due array paralleli. Entrambi `NULL`
= tutti; array vuoti = nessuno; tipo ignoto o chiave inesistente = nessuno.

Serve a chi ha già trovato gli archi di una catena e vuole **decorare solo i
documenti visitati**, invece di leggerli tutti.

{% include-markdown "signature-core.md" %}
