## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_magazzino`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_articolo](/dbzero/dbops/funzioni/fn_pgtap_crea_articolo), [dbops.fn_pgtap_crea_indirizzo_dettaglio](/dbzero/dbops/funzioni/fn_pgtap_crea_indirizzo_dettaglio)
> • [script.fn_pgtap_emittente_operatore](/dbzero/script/funzioni/fn_pgtap_emittente_operatore) — l'emittente che usa
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-magazzino-lotto-2-motore` (§5)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

**Fixture pgTAP: un magazzino dell'emittente dell'operatore in sessione**, con un indirizzo
fabbricato e `usa_ubicazioni` scelto dal test. Da chiamare **dopo**
`fn_pgtap_set_contesto_operatore`: il guard di scope dei magazzini pretende l'emittente
dell'operatore. Solo per i test.

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-26`).

---

{% include-markdown "signature-core.md" %}
