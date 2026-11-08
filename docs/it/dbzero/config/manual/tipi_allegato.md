## 📘 Documentazione Concettuale – Tabella `config.tipi_allegato`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.allegati_pratiche](/dbzero/pratiche/tabelle/allegati_pratiche)
> [pratiche.allegati_flussi](/dbzero/pratiche/tabelle/allegati_flussi)

---
### 🎯 Scopo Principale
La tabella `config.tipi_allegato` definisce la **tipologia** degli allegati associabili a pratiche e flussi. Consente di classificare i file allegati per natura (documento, immagine, contratto, ecc.).

---

### Ruolo nel processo

* Ogni allegato (su pratica o flusso) ha un `tipo_allegato_id` obbligatorio che lo classifica.
* La classificazione abilita **filtri**, **validazioni** (es. formati ammessi per tipo) e **policy di retention** differenziate.

---

### Valori previsti (seed DB-6)

| codice_interno | Descrizione |
|----------------|-------------|
| `DOCUMENTO` | Documento generico |
| `IMMAGINE` | File immagine |
| `MODULO` | Modulo/form compilato |
| `CONTRATTO` | Documento contrattuale |
| `FATTURA` | Documento fiscale |
| `VERBALE` | Verbale di intervento |
| `CERTIFICATO` | Certificazione |
| `ALTRO` | Altro tipo |

---

### Convenzioni

* Pattern config standard: `codice`, `codice_interno` locked, `attivo`, `meta`, audit.
* Trigger standard applicati automaticamente dai runner del framework di automazione (`dbops.fn_run_automations_<tipo>`).

---

{% include-markdown "signature-core.md" %}
