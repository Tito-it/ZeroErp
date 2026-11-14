## 📘 Documentazione Concettuale – Tabella `documenti.formati_pagina`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — la colonna `page_format` di ogni versione è un valore di qui
> * [config.tabelle_gestibili](/dbzero/config/tabelle/tabelle_gestibili) — il vocabolario è nel lookup generico, non nel pannello
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §5, come è fatto un modello

---

### 🎯 Scopo Principale

Il vocabolario dei formati di pagina del PDF: A4, A3 e Letter. Ogni versione di modello sceglie il suo, e il render ne fa la dimensione della pagina.

---

### I valori ammessi

* `A4` — 210 × 297 mm;
* `A3` — 297 × 420 mm;
* `LETTER` — 8,5 × 11 pollici.

Il codice è già la parola che il foglio di stile della pagina capisce: il render lo usa così com'è,
insieme all'orientamento e ai margini della versione, e vince sull'impaginazione scritta nel modello.

---

### ⭐ Si legge, non si configura

Il vocabolario dice ciò che il motore di stampa sa onorare, non una scelta dell'azienda: per questo non
ha `attivo`, e un valore nuovo nasce dal seed insieme al codice che lo sa trattare. Il drawer della
versione lo rende come tendina, con l'etichetta tradotta da `etichetta_key` e l'ordine di `ordine`,
che non ha altra semantica.

La versione punta al vocabolario per chiave esterna sul `codice_interno`, che è bloccato dopo
l'inserimento; la chiave esterna rifiuta sia un valore fuori vocabolario sia la cancellazione o il
cambio di un valore in uso. È la sede unica dei valori ammessi: prima stavano in un `CHECK` sulla
versione, e una copia nel frontend offriva valori che il database rifiutava.


---

### Test

* `db/pgtap/documenti/test-documenti-vocabolari-versione-v1.sql` — i valori del seed, nessun
  `attivo`, la chiave esterna su `codice_interno`, un valore fuori vocabolario rifiutato, il blocco
  della chiave, la presenza nel lookup e non nel pannello.

---

### Note di migrazione

* 2026-10-04 — nasce, e prende il posto del `CHECK` su `template_documenti_versioni.page_format`.

---

{% include-markdown "signature-core.md" %}
