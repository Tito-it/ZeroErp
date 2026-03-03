## 📘 Documentazione Concettuale – Tabella `pratiche.allegati_flussi`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)
> * [pratiche.allegati_pratiche](/dbzero/pratiche/tabelle/allegati_pratiche)
> * [config.tipi_allegato](/dbzero/config/tabelle/tipi_allegato)

---

### 🎯 Scopo Principale

La tabella `pratiche.allegati_flussi` gestisce i **file allegati** a un flusso specifico. Struttura identica a `allegati_pratiche` ma collegata al singolo step di workflow anziche' alla pratica.

---

### 🧱 Ruolo nel processo

* Consente di allegare documenti a livello di singolo step (es. foto sopralluogo, verbale intervento).
* **Immutabile**: versionamento tramite `allegato_padre_id`.
* L'aggiunta viene registrata nel giornale con azione `ALLEGATO_AGGIUNTO` (trigger DB-5).

---

### ⚙️ Caratteristiche

| Aspetto | Dettaglio |
|---------|-----------|
| **Immutabilita'** | Solo `data_insert/user_insert`. |
| **Versionamento** | Via `allegato_padre_id` (FK self-reference, ON DELETE SET NULL). |
| **Colonne file** | `nome_file`, `percorso`, `mime_type`, `dimensione` — identiche a `allegati_pratiche`. |

---

{% include-markdown "signature-core.md" %}
