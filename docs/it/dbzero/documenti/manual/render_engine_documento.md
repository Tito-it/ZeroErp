## 📘 Documentazione Concettuale – Tabella `documenti.render_engine_documento`

> **Ultimo aggiornamento**: 16 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — ogni versione dice con quale motore si rende
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §5, come è fatto un modello

---

### 🎯 Scopo Principale

Il vocabolario dei motori che trasformano una versione di modello in un PDF. Oggi c'è un motore solo,
WeasyPrint. Ogni versione di modello nomina il suo, così la scelta non è una stringa libera sparsa fra
schema e backend.

---

### ⭐ Il motore lo sa usare il backend, non il vocabolario

La riga dice che un motore esiste; renderlo è compito del backend, che ha una lista sua dei motori che
sa usare e confronta sul `codice_interno`. È voluto: un motore è codice, e una riga non installa un
programma. Un motore nuovo nasce quindi in due posti insieme, dallo stesso aggiornamento del sistema:
la riga del seed e il codice che lo sa chiamare.

La tabella non conserva parametri del motore né segreti.

---

### Un vocabolario si legge, non si configura

Un motore nasce o si ritira con il changeSet che accompagna il suo codice. Non ha `attivo`: c'è o non c'è. L'applicazione lo legge soltanto.

* `codice_interno` è la chiave su cui confronta la logica, bloccata dopo l'inserimento;
* `codice` e `descrizione` sono per chi legge il catalogo; a video l'etichetta viene da
  `etichetta_key` (`documenti.render_engine_documento.<codice_interno minuscolo>`);
* `ordine` dà l'ordine della tendina.

È la forma dei sette vocabolari dello schema.

---

### Test

* `db/pgtap/documenti/test-documenti-vocabolari-forma-v1.sql` — la forma e la sola lettura.
* `db/pgtap/documenti/test-documenti-lookup.sql` — la riga del seed, l'unicità di `codice_interno`, il
  blocco della chiave.

---

### Note di migrazione

* 2026-04-29 — nasce con `WEASYPRINT`.
* 2026-11-16 — prende la forma dei vocabolari della versione: entrano `etichetta_key` e `ordine`,
  escono `attivo`, `meta` e lo storico. L'applicazione lo legge soltanto: non può più aggiungere un
  motore che il backend non sa usare.

---

{% include-markdown "signature-core.md" %}
