## 📘 Documentazione Concettuale – Tabella `documenti.formati_template`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — la colonna `formato_template` di ogni versione è un valore di qui
> * [config.tabelle_gestibili](/dbzero/config/tabelle/tabelle_gestibili) — il vocabolario è nel lookup generico, non nel pannello
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §5, come è fatto un modello

---

### 🎯 Scopo Principale

Il vocabolario dei formati in cui è scritto il sorgente di una versione di modello: HTML con il suo foglio di stile, oppure HTML con blocchi Markdown controllati.

---

### I valori ammessi

* `HTML` — il sorgente è HTML, con il suo CSS;
* `HTML_MARKDOWN_BLOCKS` — il sorgente è HTML, con blocchi di testo scritti in Markdown.

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

### ⚠️ Che cosa oggi non copre

* **`HTML_MARKDOWN_BLOCKS` si sceglie ma non cambia la stampa.** Il valore è ammesso e si salva, ma
  il render tratta ogni versione come HTML: i blocchi Markdown non vengono convertiti.

---

### Test

* `db/pgtap/documenti/test-documenti-vocabolari-versione-v1.sql` — i valori del seed, nessun
  `attivo`, la chiave esterna su `codice_interno`, un valore fuori vocabolario rifiutato, il blocco
  della chiave, la presenza nel lookup e non nel pannello.

---

### Note di migrazione

* 2026-10-04 — nasce, e prende il posto del `CHECK` su `template_documenti_versioni.formato_template`.

---

{% include-markdown "signature-core.md" %}
