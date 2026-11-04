## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_sorgente`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento in cui la fixture scrive
> * [vendite.famiglie_documento](/dbzero/vendite/tabelle/famiglie_documento) — la famiglia di numerazione, che è una sorgente
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — dove si sceglie una fixture

---

### 🎯 Scopo Principale

Fixture pgTAP: **una sorgente di prova**, cioè un tipo di documento che il catalogo non ha,
costruita e non pescata. Restituisce l'id della sorgente.

Serve a chi costruisce una famiglia di numerazione di prova (una famiglia è una sorgente: la
chiave esterna la lega a `config.sorgenti`) o un ambito di prova, e ha bisogno di un codice che
nessun documento vero usa.

---

### ⚠️ L'id è il primo libero

`config.sorgenti` non ha un default per l'id: gli id del catalogo li dà il seed. La fixture prende
il massimo più uno, dentro la transazione del test. Il codice interno e il codice sono quello
dato dal test, e devono essere liberi: un codice già a catalogo collide con l'unicità.

---

### Com'è fatta la sorgente

* **Categoria documento, attiva**, con la tabella dei documenti che il test indica; senza tabella
  è il caso del riferimento che manca. La chiave del documento è l'id.
* **Spenta come documento**: non apribile, scope `CATALOGO`, etichetta uguale al codice. Il test
  la vede, nessuna lista dell'applicazione la propone.
* Nel `meta` porta il marchio `pgtap`, che la distingue dalle sorgenti del seed.

---

### Test

Non ha un test suo: la usano i test delle famiglie di documento
(`db/pgtap/vendite/test-famiglie-documento-crud-v1.sql`,
`db/pgtap/vendite/test-famiglie-documento-codice-v1.sql`,
`db/pgtap/vendite/test-famiglie-documento-guard-riferimenti.sql`) e
`db/pgtap/vendite/test-fn-list-commessa-attivita-sorgente-codice-interno-v1.sql`.

---

### Note di migrazione

* 2026-10-20 — nasce quando la famiglia di numerazione diventa una sorgente
  (`brief-db-grammatica-unica-documenti`, §13).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
