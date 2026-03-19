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
Trigger function per la **generazione automatica cross-pratica**. Si attiva **AFTER UPDATE OF stato_id** su `pratiche.flussi`. Quando un flusso passa allo stato COMPLETATO, cerca le regole di generazione automatica e invoca `fn_genera_pratica_da_flusso` per ciascuna regola matching.

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

1. Recupera `codice_interno` del nuovo stato da `config.stati_flussi_pratiche`.
2. Se non e' `'COMPLETATO'` → RETURN NEW (nessuna azione).
3. Se `template_flusso_id IS NULL` (flusso manuale) → RETURN NEW.
4. Cerca regole matching in `pratiche.regole_generazione`:
   - `template_flusso_origine_id = NEW.template_flusso_id`
   - `auto = true` e `attivo = true`
   - `esito_richiesto IS NULL` (qualsiasi esito) oppure `esito_richiesto = NEW.esito`
5. Per ogni regola trovata, invoca `pratiche.fn_genera_pratica_da_flusso(NEW.id, regola.id)`.

---

### Trigger associato

| Nome | Fase | Evento | WHEN |
|------|------|--------|------|
| `trg_flussi_z90_generazione_upd` | AFTER | UPDATE OF stato_id | `OLD.stato_id IS DISTINCT FROM NEW.stato_id` |

---

### Note operative

* Il trigger scatta per qualsiasi cambio di `stato_id`, ma la function esce immediatamente se il nuovo stato non e' COMPLETATO — costo minimo per gli altri cambi stato.
* Le regole con `auto = false` non vengono elaborate dal trigger: richiedono invocazione esplicita dal backend Django.
* Il filtro `esito_richiesto` permette di generare pratiche solo per specifici esiti del flusso (es. solo su esito positivo).
