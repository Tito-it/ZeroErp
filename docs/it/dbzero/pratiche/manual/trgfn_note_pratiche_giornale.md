## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_note_pratiche_giornale`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.note_pratiche](/dbzero/pratiche/tabelle/note_pratiche) — la nota che si registra
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — il giornale in cui finisce la riga

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_note_pratiche_giornale` registra nel giornale l'azione
`NOTA_AGGIUNTA` quando a una pratica si aggiunge una nota.

---

### La riga di giornale

* Scatta dopo l'inserimento di una riga in `pratiche.note_pratiche`.
* La riga è a livello di pratica: il flusso resta vuoto.
* L'origine è `SISTEMA`: la scrive il database, non l'operatore.
* Il dettaglio porta l'id della nota e il suo tipo, così dal giornale si risale alla nota.
* La transazione è quella della nota; se la nota non la porta, quella della sessione.

---

{% include-markdown "signature-core.md" %}
