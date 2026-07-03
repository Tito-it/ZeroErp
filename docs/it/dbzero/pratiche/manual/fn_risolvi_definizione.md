## 📘 Documentazione Funzione – `pratiche.fn_risolvi_definizione`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.workflow_definizioni](workflow_definizioni.md)
> [pratiche.trgfn_pratiche_default_definizione](trgfn_pratiche_default_definizione.md)
> [pratiche.trgfn_template_flussi_default_definizione](trgfn_template_flussi_default_definizione.md)
> [pratiche.trgfn_tipi_prestazione_bootstrap_definizione](trgfn_tipi_prestazione_bootstrap_definizione.md)

---
### 🎯 Scopo Principale

**Punto unico di risoluzione** dell'edizione di workflow per (tipo prestazione, scope
emittente). Catena (design brief §3.4):

1. edizione **PUBBLICATA dell'emittente**, se esiste (fork — da Fase 2);
2. altrimenti il **preset** PUBBLICATA (`emittente_fiscale_id IS NULL`);
3. altrimenti errore parlante `DEFINIZIONE_NON_TROVATA` (507).

---

### Firma

```sql
CREATE FUNCTION pratiche.fn_risolvi_definizione(
    p_tipo_prestazione_id  pratiche.tipi_prestazione.id%TYPE,
    p_emittente_fiscale_id anagrafiche.emittenti_fiscali.id%TYPE DEFAULT NULL
)
RETURNS pratiche.workflow_definizioni.id%TYPE
LANGUAGE plpgsql VOLATILE
```

| Parametro | Obbligatorio | Descrizione |
|-----------|:---:|-------------|
| `p_tipo_prestazione_id` | SI (guard: errore se NULL o ≤ 0) | Tipo prestazione di cui risolvere l'edizione |
| `p_emittente_fiscale_id` | NO (NULL = solo preset) | Scope emittente: la sua edizione pubblicata vince sul preset |

---

### Note operative

* **VOLATILE** (non STABLE): il ramo di errore scrive il log via
  `script.fn_log_and_raise_error` (INSERT vietato nelle funzioni non-volatile).
* Consumatori: [auto-pin delle pratiche](trgfn_pratiche_default_definizione.md)
  (con l'emittente della pratica) e [auto-default dei
  template](trgfn_template_flussi_default_definizione.md) (con emittente NULL →
  preset). In Fase 1 la userà anche `fn_genera_pratica_da_flusso` (risoluzione con
  l'emittente della pratica sorgente).
* Errore sollevato: `DEFINIZIONE_NON_TROVATA` (507) — sia per parametro tipo invalido
  sia per assenza di edizioni pubblicate (il `context` jsonb distingue il motivo).
  In pratica non dovrebbe mai scattare per un tipo reale: il preset v1 è garantito dal
  [bootstrap](trgfn_tipi_prestazione_bootstrap_definizione.md) e dal backfill Fase 0.
* Test: `db/pgtap/pratiche/test-workflow-definizioni-fase0.sql` (casi 4–5).

---
{% include-markdown "signature-core.md" %}
