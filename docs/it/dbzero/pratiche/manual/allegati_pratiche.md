## 📘 Documentazione Concettuale – Tabella `pratiche.allegati_pratiche`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
> * [pratiche.allegati_flussi](/dbzero/pratiche/tabelle/allegati_flussi)
> * [config.tipi_allegato](/dbzero/config/tabelle/tipi_allegato)

---

### 🎯 Scopo Principale

La tabella `pratiche.allegati_pratiche` gestisce i **file allegati** a una pratica. Gli allegati sono **immutabili**: non vengono modificati ma versionati tramite `allegato_padre_id`.

---

### 🧱 Ruolo nel processo

* Ogni allegato e' classificato per tipo (DOCUMENTO, IMMAGINE, CONTRATTO, ecc.).
* Il **versionamento** funziona tramite `allegato_padre_id`: una nuova versione punta alla precedente.
* L'aggiunta viene registrata nel giornale con azione `ALLEGATO_AGGIUNTO` (trigger DB-5).
* Il file fisico e' referenziato da `percorso` (chiave di storage); il DB non contiene il contenuto binario.

---

### ⚙️ Colonne specifiche

| Colonna | Note |
|---------|------|
| `nome_file` | TEXT NOT NULL. Nome originale del file caricato. |
| `percorso` | TEXT NOT NULL. Percorso o chiave di storage (es. S3 key, path filesystem). |
| `mime_type` | VARCHAR(255) nullable. Content-type (es. `application/pdf`). |
| `dimensione` | BIGINT nullable. Dimensione in byte. |
| `allegato_padre_id` | BIGINT nullable. FK self-reference per versionamento. ON DELETE SET NULL. |

---

### ⚙️ Caratteristiche

| Aspetto | Dettaglio |
|---------|-----------|
| **Immutabilita'** | Solo `data_insert/user_insert` — nessun UPDATE. |
| **Versionamento** | Nuova versione → nuovo record con `allegato_padre_id` che punta al precedente. |
| **No storicizza** | Non necessario: i record sono immutabili. |
| **No tx_id** | Non necessario per record immutabili. |

---

{% include-markdown "signature-core.md" %}
