## 📘 Documentazione Concettuale – Tabella `pratiche.note_flussi`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.flussi](/dbzero/pratiche/tabelle/flussi)
> [pratiche.note_pratiche](/dbzero/pratiche/tabelle/note_pratiche)
> [config.tipi_nota](/dbzero/config/tabelle/tipi_nota)

---
### 🎯 Scopo Principale
La tabella `pratiche.note_flussi` contiene le **note testuali** associate a un flusso specifico. Struttura identica a `note_pratiche` ma collegata al singolo step di workflow anziche' alla pratica.

---

### Ruolo nel processo

* Consente annotazioni granulari a livello di singolo step del workflow.
* Il `tipo_nota_id` determina la visibilita' della nota.
* L'aggiunta viene registrata nel giornale con azione `NOTA_AGGIUNTA` (trigger DB-5).
* Le note sono **modificabili** e **storicizzabili**.

---

### Convenzioni

* PK BIGINT IDENTITY.
* `storicizza = true`, `tx_id` per correlazione.
* Trigger standard applicati automaticamente, trigger giornale in DB-5.

---

{% include-markdown "signature-core.md" %}
