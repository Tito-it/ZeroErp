## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_pratiche_giornale_ins`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la tabella su cui è montata
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — dove scrive

---

### 🎯 Scopo Principale

`pratiche.trgfn_pratiche_giornale_ins` registra nel giornale l'azione `PRATICA_CREATA` alla nascita di
una pratica.

---

### Che cosa scrive

È montata `AFTER INSERT`, riga per riga, su `pratiche.pratiche`, nella fase `_z90_`.

* La riga di giornale è a livello di pratica: nessun flusso.
* L'origine è `SISTEMA`; il dettaglio fotografa la pratica alla nascita: tipo di prestazione, stato,
  priorità, soggetto e canale di origine.
* La transazione è quella della pratica, o quella di sessione se la pratica non la porta.

---

### Test

* `pratiche/test-trigger-giornale-pratiche` — i trigger di giornale della pratica.

---

{% include-markdown "signature-core.md" %}
