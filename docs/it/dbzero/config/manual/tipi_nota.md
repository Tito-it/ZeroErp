## 📘 Documentazione Concettuale – Tabella `config.tipi_nota`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.note_pratiche](/dbzero/pratiche/tabelle/note_pratiche)
> [pratiche.note_flussi](/dbzero/pratiche/tabelle/note_flussi)

---
### 🎯 Scopo Principale
La tabella `config.tipi_nota` definisce la **tipologia** delle note associabili a pratiche e flussi. Consente di classificare le note per finalita' (interna, per il cliente, tecnica, ecc.).

---

### Ruolo nel processo

* Ogni nota (su pratica o flusso) ha un `tipo_nota_id` obbligatorio che la classifica.
* La classificazione consente il **filtraggio** nelle interfacce e la **visibilita' differenziata** (es. note interne non visibili al cliente).

---

### Valori previsti (seed DB-6)

| codice_interno | Descrizione |
|----------------|-------------|
| `GENERALE` | Nota generica |
| `INTERNA` | Nota visibile solo internamente |
| `CLIENTE` | Nota visibile al cliente |
| `TECNICA` | Nota tecnica operativa |
| `LEGALE` | Nota con rilevanza legale |

---

### Convenzioni

* Pattern config standard: `codice`, `codice_interno` locked, `attivo`, `meta`, audit.
* Trigger standard applicati automaticamente dai runner del framework di automazione (`dbops.fn_run_automations_<tipo>`).

---

{% include-markdown "signature-core.md" %}
