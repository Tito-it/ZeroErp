## 📘 Documentazione Concettuale – Tabella `magazzino.note`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.note](/dbzero/vendite/tabelle/note) — il meccanismo delle note, documentato per intero

---

### 🎯 Scopo Principale

La tabella madre delle note di magazzino, divisa in partizioni per `target_tipo`: non annota un bersaglio proprio, le note stanno nelle partizioni `note_<bersaglio>`, una per ciascuna tabella annotata.

---

{% include-markdown "it/dbzero/magazzino/_note-partizioni.md" %}

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
