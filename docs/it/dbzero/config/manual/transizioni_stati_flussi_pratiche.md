## 📘 Documentazione Concettuale – Tabella `config.transizioni_stati_flussi_pratiche`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[config.stati_flussi_pratiche](/dbzero/config/tabelle/stati_flussi_pratiche)
> [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)
>
**Funzioni collegate:**
>
[pratiche.trgfn_flussi_guard_transizione](/dbzero/pratiche/manual/trgfn_flussi_guard_transizione)

---
### 🎯 Scopo Principale
`config.transizioni_stati_flussi_pratiche` definisce la **matrice delle transizioni ammesse** tra stati dei flussi pratica. Il trigger guard `trgfn_flussi_guard_transizione` consulta questa tabella per bloccare qualsiasi transizione non configurata.

---

### Campi chiave (semantica)

| Colonna | Note |
|---------|------|
| `stato_da_id` | FK a `config.stati_flussi_pratiche` — stato di origine. |
| `stato_a_id` | FK a `config.stati_flussi_pratiche` — stato di destinazione. |
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
| DA_ESEGUIRE | IN_CORSO |
| DA_ESEGUIRE | ANNULLATO |
| IN_CORSO | COMPLETATO |
| IN_CORSO | SOSPESO |
| IN_CORSO | ERRORE |
| SOSPESO | IN_CORSO |
| SOSPESO | DA_ESEGUIRE |

Gli stati COMPLETATO, ANNULLATO e ERRORE sono **terminali**: nessuna transizione in uscita.

**SOSPESO → DA_ESEGUIRE**: previsto per la riattivazione automatica (job pgAgent).
**SOSPESO → IN_CORSO**: previsto per la ripresa manuale da parte dell'operatore.

---

### Note operative

* **Configurabile senza deploy**: aggiungere/disattivare transizioni e' un UPDATE/INSERT su config.
* **Impossibile bypassare**: il trigger guard vale per API, service, query dirette, migration.
* Pattern coerente con `config.stati_doc_fiscale_transizioni` (vendite).

---

{% include-markdown "signature-core.md" %}
