## 📘 Documentazione Concettuale – Tabella `documenti.orientamenti_pagina`

> **Ultimo aggiornamento**: 16 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — la colonna `page_orientation` di ogni versione è un valore di qui
> * [config.tabelle_gestibili](/dbzero/config/tabelle/tabelle_gestibili) — il vocabolario è nel lookup generico, non nel pannello
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §5, come è fatto un modello

---

### 🎯 Scopo Principale

Il vocabolario degli orientamenti di pagina del PDF: verticale e orizzontale. Ogni versione di modello sceglie il suo, e il render lo applica alla pagina.

---

### I valori ammessi

* `PORTRAIT` — verticale;
* `LANDSCAPE` — orizzontale.

Il codice è già la parola che il foglio di stile della pagina capisce: il render lo usa così com'è,
insieme al formato e ai margini della versione, e vince sull'impaginazione scritta nel modello.

---

### ⭐ Si legge, non si configura

Il vocabolario dice ciò che il motore di stampa sa onorare, non una scelta dell'azienda: per questo non
ha `attivo`, e un valore nuovo nasce dal seed insieme al codice che lo sa trattare. Il drawer della
versione lo rende come tendina, con l'etichetta tradotta da `etichetta_key` e l'ordine di `ordine`,
che non ha altra semantica. `descrizione` è obbligatoria, per chi legge il catalogo. L'applicazione
lo legge soltanto. È la forma dei sette vocabolari dello schema.

La versione punta al vocabolario per chiave esterna sul `codice_interno`, che è bloccato dopo
l'inserimento; la chiave esterna rifiuta sia un valore fuori vocabolario sia la cancellazione o il
cambio di un valore in uso. È la sede unica dei valori ammessi: prima stavano in un `CHECK` sulla
versione, e una copia nel frontend offriva valori che il database rifiutava.


---

### Test

* `db/pgtap/documenti/test-documenti-vocabolari-forma-v1.sql` — la forma e la sola lettura.
* `db/pgtap/documenti/test-documenti-vocabolari-versione-v1.sql` — i valori del seed, nessun
  `attivo`, la chiave esterna su `codice_interno`, un valore fuori vocabolario rifiutato, il blocco
  della chiave, la presenza nel lookup e non nel pannello.

---

### Note di migrazione

* 2026-10-04 — nasce, e prende il posto del `CHECK` su `template_documenti_versioni.page_orientation`.
* 2026-11-16 — `descrizione` obbligatoria e non vuota, `codice` non vuoto; l'applicazione lo legge
  soltanto.

---

{% include-markdown "signature-core.md" %}
