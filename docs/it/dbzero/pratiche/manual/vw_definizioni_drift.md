## 📘 Documentazione Vista – `pratiche.vw_definizioni_drift`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.fn_fork_definizione](fn_fork_definizione.md)
> [pratiche.fn_pubblica_definizione](fn_pubblica_definizione.md)
> [pratiche.workflow_definizioni](workflow_definizioni.md)

---
### 🎯 Scopo Principale

Espone le **edizioni forkate in drift**: i fork il cui **preset d'origine è avanzato**
(esiste una PUBBLICATA del preset con `versione` superiore alla `versione_origine` con cui
il fork è nato). Alimenta il **banner "preset aggiornato"** (pattern DEF-2) con un diff
informativo. L'allineamento del fork al preset resta **una scelta manuale**, mai
automatico.

---

### Colonne

| Colonna | Significato |
|---|---|
| `definizione_id` | id dell'edizione forkata (viva: BOZZA o PUBBLICATA) |
| `tipo_prestazione_id` | tipo condiviso |
| `emittente_fiscale_id` | emittente del fork |
| `versione_edizione` | versione del fork |
| `stato_edizione` | stato del fork |
| `versione_origine` | versione del preset al momento del fork |
| `preset_corrente_id` | id della PUBBLICATA corrente del preset (emittente NULL) |
| `versione_preset_corrente` | versione della PUBBLICATA corrente del preset |
| `versioni_indietro` | `versione_preset_corrente − versione_origine` (di quante versioni il fork è rimasto indietro) |

---

### Regole

- Considera solo fork **emittente-scoped** (`emittente_fiscale_id NOT NULL`) con provenance
  (`preset_origine_id`/`versione_origine` valorizzati) e in stato vivo (BOZZA/PUBBLICATA).
- Join al **preset corrente** per tipo (`emittente_fiscale_id IS NULL AND stato =
  'PUBBLICATA'`): il drift è `preset_corrente.versione > fork.versione_origine`.
- `WITH (security_invoker = true)`: la vista gira coi permessi del chiamante (convenzione
  viste RLS-aware; `workflow_definizioni` non è sotto RLS).

---

### Note operative

- Introdotta con `20260703-09` (brief-db-step-dominio-e-definizioni-versionate, Parte 2 /
  Fase 2, D2-14).
- Test: `db/pgtap/pratiche/test-workflow-definizioni-fase2.sql` (il fork compare dopo che il
  preset avanza a v2).

---
{% include-markdown "signature-core.md" %}
