## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_articolo`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_magazzino](/dbzero/dbops/funzioni/fn_pgtap_crea_magazzino), [dbops.fn_pgtap_crea_indirizzo_dettaglio](/dbzero/dbops/funzioni/fn_pgtap_crea_indirizzo_dettaglio) — le altre fixture
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-magazzino-lotto-2-motore` (§5)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

**Fixture pgTAP: un articolo costruito con i flag che il test sceglie** — gestito a
magazzino, per lotti, per seriale — e la prima unità di misura attiva del seed. Solo per i
test: pescare un articolo dal catalogo darebbe uno *non* gestito, cioè un
`E_MAG_ARTICOLO_NON_GESTITO` che sembra un test rosso. Estratta alla seconda occorrenza (dodici
file avrebbero avuto la stessa copia).

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-26`).

---

{% include-markdown "signature-core.md" %}
