## 📘 Documentazione Funzione – `pratiche.fn_copia_definizione`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.fn_fork_definizione](fn_fork_definizione.md)
> [pratiche.fn_nuova_versione_definizione](fn_nuova_versione_definizione.md)
> [pratiche.fn_pubblica_definizione](fn_pubblica_definizione.md)
> [pratiche.workflow_definizioni](workflow_definizioni.md)
> [pratiche.template_flussi](template_flussi.md)

---
### 🎯 Scopo Principale

**Motore di copia** di un'edizione di workflow: replica header + template + **tutti
i figli di configurazione** di una definizione in una nuova edizione **BOZZA**,
rimappando gli id dei template **per codice** (il codice è unico per definizione, quindi
è la chiave naturale del remap).

È l'**unico punto** che elenca il set di copia (contratto C6): aggiungere un figlio al
modello = aggiungere un blocco `INSERT ... SELECT` qui, e nient'altro. Usata dai wrapper
[fn_fork_definizione](fn_fork_definizione.md) e
[fn_nuova_versione_definizione](fn_nuova_versione_definizione.md).

---

### Firma

```sql
CREATE FUNCTION pratiche.fn_copia_definizione(
    p_sorgente_id    pratiche.workflow_definizioni.id%TYPE,
    p_emittente_dest pratiche.workflow_definizioni.emittente_fiscale_id%TYPE,
    p_provenance     boolean
)
RETURNS pratiche.workflow_definizioni.id%TYPE
LANGUAGE plpgsql VOLATILE
```

| Parametro | Descrizione |
|---|---|
| `p_sorgente_id` | Definizione da copiare (di solito il preset) |
| `p_emittente_dest` | Scope emittente della copia (NULL = preset; valorizzato = edizione società) |
| `p_provenance` | `true` → valorizza `preset_origine_id`/`versione_origine` (fork, per il drift); `false` → nessuna provenance (nuova versione stesso scope) |

**Ritorna**: l'id della nuova edizione BOZZA.

---

### Set di copia (figli posseduti dalla definizione via i suoi template)

| Tabella | Remap |
|---|---|
| `template_flussi` | header dei template (codice preservato, id nuovo, `definizione_id` = nuova) |
| `template_flussi_canali` | singolo (`template_flusso_id`) |
| `template_flussi_handler_eventi` | singolo (`handler_id` globale invariato) |
| `competenze_flussi` | singolo |
| `template_flussi_prerequisiti` | **doppio** (`template_flusso_id` + `prerequisito_id`) |
| `formule_tempo` | **doppio** (`template_flusso_da_id` + `_a_id`; `tipo_prestazione_id` invariato) |
| `regole_generazione` | **origine** rimappata per codice; **dest** lasciata invariata — [fn_genera_pratica_da_flusso](fn_genera_pratica_da_flusso.md) la rimappa per codice a runtime (D2-8) |

**NON copiati**: istanze runtime (`flussi`, `calcoli_tempo`) e i valori
generati/audit (`id`, `tx_id`, `storicizza`, `data_/user_`).

---

### Note operative

- La nuova edizione nasce sempre **BOZZA** (non collide con l'indice
  `uq_workflow_definizioni_pubblicata`), con `versione = max(scope) + 1`
  (`uq_workflow_definizioni_scope_versione`).
- Il remap per codice funziona perché il codice è unico per definizione
  (`uq_template_flussi_definizione_codice`): ogni figlio risolve il nuovo template via
  join `(nuova_definizione, codice_del_vecchio_template)`.
- **VOLATILE**: scrive (INSERT). Errori parlanti: `E_PARAMETRO_INVALIDO` (sorgente NULL/≤0),
  `E_VALORE_MANCANTE` (sorgente inesistente).
- Introdotta con `20260703-06` (brief-db-step-dominio-e-definizioni-versionate, Parte 2 / Fase 2, D2-10).
- Test: `db/pgtap/pratiche/test-workflow-definizioni-fase2.sql` (fork + doppio remap prereq/formula).

---
{% include-markdown "signature-core.md" %}
