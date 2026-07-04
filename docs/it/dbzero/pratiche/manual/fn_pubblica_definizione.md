## 📘 Documentazione Funzione – `pratiche.fn_pubblica_definizione`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.fn_copia_definizione](fn_copia_definizione.md)
> [pratiche.fn_fork_definizione](fn_fork_definizione.md)
> [pratiche.fn_nuova_versione_definizione](fn_nuova_versione_definizione.md)
> [pratiche.trgfn_workflow_definizioni_guard](trgfn_workflow_definizioni_guard.md)
> [pratiche.workflow_definizioni](workflow_definizioni.md)

---
### 🎯 Scopo Principale

Valida una **BOZZA** e la promuove a **PUBBLICATA**, **ritirando in transazione** la
precedente PUBBLICATA dello stesso scope (una sola PUBBLICATA per scope,
`uq_workflow_definizioni_pubblicata`). Ordine: RITIRA la vecchia **prima** di pubblicare
la nuova, per non collidere sull'indice parziale.

---

### Firma

```sql
CREATE FUNCTION pratiche.fn_pubblica_definizione(
    p_definizione_id pratiche.workflow_definizioni.id%TYPE
)
RETURNS pratiche.workflow_definizioni.id%TYPE
LANGUAGE plpgsql VOLATILE
```

**Ritorna**: l'id della definizione pubblicata.

---

### Validazioni (fail-fast `DEFINIZIONE_NON_PUBBLICABILE`, 511)

1. la definizione deve essere in **BOZZA**;
2. almeno uno **step (template) attivo**;
3. nessun **ciclo** nel grafo dei prerequisiti — chiusura transitiva: uno step che
   richiede sé stesso (il no-self è già garantito da `chk_template_flussi_prereq_no_self`;
   qui si coprono i cicli multi-nodo, via CTE ricorsiva).

Il vincolo "max un `chiude_pratica` per definizione" è già garantito dall'indice
`uq_template_flussi_chiusura_definizione`.

---

### Note operative

- Le transizioni `BOZZA → PUBBLICATA` (sulla nuova) e `PUBBLICATA → RITIRATA` (sulla
  precedente) passano per il guard
  [trgfn_workflow_definizioni_guard](trgfn_workflow_definizioni_guard.md), che le ammette.
- Idempotenza/scope: opera solo sullo scope `(tipo_prestazione_id, emittente_fiscale_id)`
  della definizione; il preset (emittente NULL) e i fork (emittente valorizzato) sono
  scope distinti e non si interferiscono.
- Errori parlanti: `E_PARAMETRO_INVALIDO` (id NULL/≤0), `E_VALORE_MANCANTE` (id inesistente),
  `DEFINIZIONE_NON_PUBBLICABILE` (511) con il motivo (non-BOZZA / nessuno step attivo / ciclo).
- **Accesso** (`20260703-17`, P1 strada B): `SECURITY DEFINER` + `search_path` fisso — gli
  `UPDATE` di ritiro/pubblicazione girano come owner, il ruolo app li esegue senza grant DML
  diretto su `workflow_definizioni`; `EXECUTE` ristretto al solo ruolo app (`20260703-18`),
  gate applicativo AdminAPIView super-admin. `search_path` sulle schema fidate coinvolte dai
  trigger (il guard header/transizioni gira sotto lo stesso path).
- Introdotta con `20260703-08` (Parte 2 / Fase 2, D2-13); resa SECURITY DEFINER con `20260703-17`.
- Test: `db/pgtap/pratiche/test-workflow-definizioni-fase2.sql` (pubblica atomica con
  ritiro; ciclo → 511; non-BOZZA → 511).

---
{% include-markdown "signature-core.md" %}
