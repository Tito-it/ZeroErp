## 📘 Documentazione Funzione – `pratiche.fn_fork_definizione`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.fn_copia_definizione](fn_copia_definizione.md)
> [pratiche.fn_nuova_versione_definizione](fn_nuova_versione_definizione.md)
> [pratiche.fn_pubblica_definizione](fn_pubblica_definizione.md)
> [pratiche.vw_definizioni_drift](vw_definizioni_drift.md)
> [pratiche.workflow_definizioni](workflow_definizioni.md)

---
### 🎯 Scopo Principale

Crea l'**edizione di un emittente** (fork) a partire da una definizione — tipicamente il
**preset** — copiandone header, template e figli in una nuova **BOZZA**, con
**provenance** valorizzata (`preset_origine_id`/`versione_origine`) per il rilevamento
[drift](vw_definizioni_drift.md). È il gesto con cui una singola società ottiene il **suo**
workflow, divergente dal preset condiviso.

---

### Firma

```sql
CREATE FUNCTION pratiche.fn_fork_definizione(
    p_definizione_id       pratiche.workflow_definizioni.id%TYPE,
    p_emittente_fiscale_id pratiche.workflow_definizioni.emittente_fiscale_id%TYPE
)
RETURNS pratiche.workflow_definizioni.id%TYPE
LANGUAGE plpgsql VOLATILE
```

| Parametro | Descrizione |
|---|---|
| `p_definizione_id` | Definizione sorgente da forkare (di solito il preset del tipo) |
| `p_emittente_fiscale_id` | Emittente destinatario del fork (**obbligatorio**, NOT NULL) |

**Ritorna**: l'id della nuova edizione BOZZA.

---

### Note operative

- Wrapper sottile di [fn_copia_definizione](fn_copia_definizione.md)`(..., true)`.
- **Guard**: `p_emittente_fiscale_id` NOT NULL e > 0 → altrimenti `E_PARAMETRO_INVALIDO`.
  Il fork ha per definizione uno scope emittente; per una **nuova versione dello stesso
  scope** (preset incluso) usare [fn_nuova_versione_definizione](fn_nuova_versione_definizione.md).
- La BOZZA prodotta va poi validata e attivata con
  [fn_pubblica_definizione](fn_pubblica_definizione.md); da quel momento le pratiche di
  quell'emittente pinnano il fork (risoluzione emittente > preset in
  [fn_risolvi_definizione](fn_risolvi_definizione.md)).
- Introdotta con `20260703-07` (Parte 2 / Fase 2, D2-11).
- Test: `db/pgtap/pratiche/test-workflow-definizioni-fase2.sql` (fork + copia + provenance).

---
{% include-markdown "signature-core.md" %}
