## 📘 Documentazione Concettuale – Tabella `documenti.render_engine_documento`

> **Ultimo aggiornamento**: 14 novembre 2026
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

* `codice_interno` è la chiave, bloccata dopo l'inserimento;
* `codice` e `descrizione` sono le etichette;
* `meta` non ha lettori. La tabella non conserva parametri del motore né segreti.

---

### Spegnere un motore

Un motore non si spegne finché una versione attiva di un modello lo usa. Le modifiche sono storicizzate
in `storico.render_engine_documento`. La tabella è nel lookup generico, per la tendina del drawer della
versione, e non nel pannello di configurazione.

---

### ⚠️ Che cosa oggi non copre

* **L'applicazione può aggiungere un motore.** Ha la scrittura sul vocabolario: una riga attiva che il
  backend non sa usare si sceglie nel drawer della versione e si salva, e la stampa si ferma solo al
  render.

---

### Test

* `db/pgtap/documenti/test-documenti-lookup.sql` — la riga del seed, l'unicità di `codice_interno`, il
  blocco della chiave.

---

### Note di migrazione

* 2026-04-29 — nasce con `WEASYPRINT`.

---

{% include-markdown "signature-core.md" %}
