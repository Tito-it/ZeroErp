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

### ⭐ La struttura si sceglie alla nascita

Un articolo **usato** non cambia più struttura: il guard
[catalogo.trgfn_articoli_guard_struttura_se_usato](/dbzero/catalogo/funzioni/trgfn_articoli_guard_struttura_se_usato)
congela otto colonne — composito, solo componente, natura di vendita, causale onere,
tipologia di listino, gestito a magazzino, a lotti, a matricola. Il builder le accetta tutte, e le
scrive nell'`INSERT`: chi le sceglie le passa qui, per nome (`p_is_composito => true`).

⛔ **Non si corregge l'articolo dopo con un `UPDATE`.** Una correzione di fixture regge solo se arriva
prima che l'articolo venga usato: sbagliato l'ordine, il test diventa rosso con un
`E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE` che non nomina la fixture. Restano legittimi gli `UPDATE`
che sono **l'oggetto** del test (il guard stesso, un cambio di struttura su un articolo non usato).

* La UoM base (`p_uom_id`) segue la stessa regola per un altro motivo: la colonna è loccata.
* La natura di vendita non passata resta quella di default della tabella.
* Le combinazioni (un onere su una natura di merce, una tipologia spenta) le giudica la tabella:
  il builder non le ripete.

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-26`).
* 2026-09-23 — la UoM base si sceglie (`20260923-01`).
* 2026-10-17 — tutta la struttura si sceglie alla nascita (`20261017-01`).

---

{% include-markdown "signature-core.md" %}
