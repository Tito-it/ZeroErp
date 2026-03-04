## 📘 Documentazione Concettuale – Tabella `pratiche.note_pratiche`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
> * [pratiche.note_flussi](/dbzero/pratiche/tabelle/note_flussi)
> * [config.tipi_nota](/dbzero/config/tabelle/tipi_nota)

---

### 🎯 Scopo Principale

La tabella `pratiche.note_pratiche` contiene le **note testuali** associate a una pratica. Ogni nota e' classificata per tipo (GENERALE, INTERNA, CLIENTE, TECNICA, LEGALE) e puo' essere modificata.

---

### 🧱 Ruolo nel processo

* Consente di aggiungere annotazioni libere a una pratica durante il suo ciclo di vita.
* Il `tipo_nota_id` determina la **visibilita'** della nota (es. note INTERNA non visibili al cliente).
* L'aggiunta di una nota viene registrata nel **giornale** con azione `NOTA_AGGIUNTA` (trigger DB-5).
* Le note sono **modificabili** (4 audit fields completi) e **storicizzabili**.

---

### ✅ Convenzioni

* PK BIGINT IDENTITY.
* `storicizza = true`, `tx_id` per correlazione.
* Trigger standard (audit, storico) applicati automaticamente.
* Trigger giornale (business) in DB-5.

---

{% include-markdown "signature-core.md" %}
