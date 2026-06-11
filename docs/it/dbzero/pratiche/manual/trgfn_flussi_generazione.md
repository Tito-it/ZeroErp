## 📘 Documentazione Funzione – `pratiche.trgfn_flussi_generazione`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.fn_genera_pratica_da_flusso](fn_genera_pratica_da_flusso.md)
>
Tabelle:
>
[pratiche.regole_generazione](regole_generazione.md)
> [pratiche.flussi](flussi.md)
> [config.stati_flussi_pratiche](/dbzero/config/tabelle/stati_flussi_pratiche)
>
Overview:
>
[Trigger business overview](trigger_business_overview.md)

---
### 🎯 Scopo Principale
Trigger function per la **generazione automatica cross-pratica**. Si attiva **AFTER UPDATE OF stato_id** su `pratiche.flussi`. Quando un flusso **transita** allo stato COMPLETATO, cerca le regole di generazione automatica e invoca `fn_genera_pratica_da_flusso` per ciascuna regola matching.

**Idempotente** (rev 2026-06-11): genera solo alla **transizione di stato** (`OLD.stato_id IS DISTINCT FROM NEW.stato_id`) — un UPDATE su un flusso gia' COMPLETATO (es. correzione `note_esito`) non rigenera nulla. Terza difesa: dedup in `fn_genera_pratica_da_flusso` + indice `uq_pratiche_flusso_origine_tipo`.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_generazione()
RETURNS trigger
LANGUAGE plpgsql
```

---

### DECLARE

| Variabile | Tipo | Descrizione |
|-----------|------|-------------|
| `v_codice_interno` | `config.stati_flussi_pratiche.codice_interno%TYPE` | Codice interno del nuovo stato |
| `v_regola` | `RECORD` | Cursore per le regole matching |

---

### Logica

1. **Guard transizione (idempotenza)**: se `OLD.stato_id IS NOT DISTINCT FROM NEW.stato_id` → RETURN NEW (un UPDATE che non cambia stato non genera).
2. Recupera `codice_interno` del nuovo stato da `config.stati_flussi_pratiche`.
3. Se non e' `'COMPLETATO'` → RETURN NEW (nessuna azione).
4. Se `template_flusso_id IS NULL` (flusso manuale) → RETURN NEW.
5. Cerca regole matching in `pratiche.regole_generazione`:
   - `template_flusso_origine_id = NEW.template_flusso_id`
   - `auto = true` e `attivo = true`
   - `esito_richiesto IS NULL` (qualsiasi esito) oppure `esito_richiesto = NEW.esito`
6. Per ogni regola trovata, invoca `pratiche.fn_genera_pratica_da_flusso(NEW.id, regola.id)` (dedup interno alla fn).

---

### Trigger associato

| Nome | Fase | Evento |
|------|------|--------|
| `trg_flussi_z90_generazione_upd` | AFTER | UPDATE OF `stato_id` |

Il check di transizione (`OLD IS DISTINCT FROM NEW`) e' **interno alla funzione**, non una clausola WHEN del trigger: copre anche gli UPDATE che riscrivono lo stesso `stato_id`.

---

### Note operative

* Prima della rev 2026-06-11 il trigger era `AFTER UPDATE` senza `OF` e senza check di transizione: ogni UPDATE su un flusso gia' COMPLETATO rigenerava una pratica figlia (bug di idempotenza, analisi-pratiche-workflow-v2 §7.B).
* Le regole con `auto = false` non vengono elaborate dal trigger: richiedono invocazione esplicita dal backend Django.
* Il filtro `esito_richiesto` permette di generare pratiche solo per specifici esiti del flusso (es. solo su esito positivo).
* Test: `db/pgtap/pratiche/test-generazione-cross-pratica.sql`.
