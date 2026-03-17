## 📘 Documentazione Concettuale – Tabella `config.transizioni_stati_pratiche`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[config.stati_pratiche](/dbzero/config/tabelle/stati_pratiche)
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
>
**Funzioni collegate:**
>
[pratiche.trgfn_pratiche_guard_transizione](/dbzero/pratiche/manual/trgfn_pratiche_guard_transizione)

---

### 🎯 Scopo Principale

`config.transizioni_stati_pratiche` definisce la **matrice delle transizioni ammesse** tra stati delle pratiche. Il trigger guard `trgfn_pratiche_guard_transizione` consulta questa tabella per bloccare qualsiasi transizione non configurata.

---

### Campi chiave (semantica)

| Colonna | Note |
|---------|------|
| `stato_da_id` | FK a `config.stati_pratiche` — stato di origine. |
| `stato_a_id` | FK a `config.stati_pratiche` — stato di destinazione. |
| `attivo` | Se true, la transizione e' ammessa. Permette di disattivare senza eliminare. |
| `meta` | JSONB per metadati/estensioni future. |

---

### Vincoli

* **UNIQUE** su `(stato_da_id, stato_a_id)` — una sola riga per coppia.
* **CHECK** `stato_da_id <> stato_a_id` — transizione identitaria non ammessa.

---

### Transizioni configurate (seed)

| Da | A |
|----|---|
| BOZZA | APERTA |
| BOZZA | ANNULLATA |
| APERTA | SOSPESA |
| APERTA | CHIUSA |
| APERTA | ANNULLATA |
| SOSPESA | APERTA |

Gli stati CHIUSA e ANNULLATA sono **terminali**: nessuna transizione in uscita.

---

### Note operative

* **Configurabile senza deploy**: aggiungere/disattivare transizioni e' un UPDATE/INSERT su config.
* **Impossibile bypassare**: il trigger guard vale per API, service, query dirette, migration.
* Pattern coerente con `config.stati_doc_fiscale_transizioni` (vendite).

---

{% include-markdown "signature-core.md" %}
