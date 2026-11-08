## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_note_flussi_giornale`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.note_flussi](/dbzero/pratiche/tabelle/note_flussi) — la tabella su cui è montata
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — dove scrive
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — da cui risale alla pratica

---

### 🎯 Scopo Principale

`pratiche.trgfn_note_flussi_giornale` registra nel giornale della pratica l'azione `NOTA_AGGIUNTA`
quando a un flusso si aggiunge una nota.

---

### Che cosa scrive

È montata `AFTER INSERT`, riga per riga, su `pratiche.note_flussi`, nella fase `_z90_`.

* La riga di giornale è a livello di flusso: porta il flusso della nota e la pratica a cui il flusso
  appartiene, che la funzione risale dal flusso.
* L'origine è `SISTEMA`; il dettaglio porta l'id della nota e il suo tipo.
* La transazione è quella della nota, o quella di sessione se la nota non la porta: la riga di giornale
  si lega sempre alla transazione che l'ha prodotta.

---

{% include-markdown "signature-core.md" %}
