## 📘 Documentazione Funzione – `pratiche.fn_nuova_versione_definizione`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.fn_copia_definizione](fn_copia_definizione.md)
> [pratiche.fn_fork_definizione](fn_fork_definizione.md)
> [pratiche.fn_pubblica_definizione](fn_pubblica_definizione.md)
> [pratiche.workflow_definizioni](workflow_definizioni.md)

---
### 🎯 Scopo Principale

Crea una **nuova versione BOZZA** nello **stesso scope** (tipo + emittente) di una
definizione sorgente — preset incluso. È il modo di **modificare in sicurezza**
un'edizione già PUBBLICATA (che è strutturalmente immutabile): si crea una bozza, la si
modifica, la si pubblica — e la [fn_pubblica_definizione](fn_pubblica_definizione.md)
ritira automaticamente la precedente PUBBLICATA. Le pratiche in volo restano sul loro pin
(V6).

---

### Firma

```sql
CREATE FUNCTION pratiche.fn_nuova_versione_definizione(
    p_definizione_id pratiche.workflow_definizioni.id%TYPE
)
RETURNS pratiche.workflow_definizioni.id%TYPE
LANGUAGE plpgsql VOLATILE
```

| Parametro | Descrizione |
|---|---|
| `p_definizione_id` | Definizione sorgente di cui creare una nuova versione (lo scope emittente viene ereditato) |

**Ritorna**: l'id della nuova edizione BOZZA.

---

### Note operative

- Wrapper sottile di [fn_copia_definizione](fn_copia_definizione.md)`(..., false)`:
  legge l'emittente della sorgente e copia nello stesso scope, **senza provenance** (non è
  un fork).
- Errore parlante `E_VALORE_MANCANTE` se la sorgente non esiste.
- **Guard ciclo di vita** (`20260704-06`): (1) la sorgente **deve** essere in stato
  **`PUBBLICATA`** — la nuova versione si deriva dall'edizione pubblicata dello scope, non
  da una bozza arbitraria; da BOZZA/RITIRATA → `DEFINIZIONE_NO_PUBBLICATA` (516). (2) lo
  scope non deve avere **già una BOZZA** aperta → `DEFINIZIONE_BOZZA_ESISTENTE` (515),
  invariante **≤1 BOZZA per scope** (indice `uq_workflow_definizioni_bozza`).
- Differenza da [fn_fork_definizione](fn_fork_definizione.md): il fork cambia scope
  (verso un nuovo emittente, con provenance); la nuova versione resta nello **stesso**
  scope (versione successiva) e parte dalla **PUBBLICATA** corrente.
- **Accesso** (`20260703-16`, P1 strada B): `SECURITY DEFINER` + `search_path` fisso (come
  [fn_fork_definizione](fn_fork_definizione.md)) — la DML interna gira come owner, il ruolo
  app la esegue senza grant DML diretto; `EXECUTE` ristretto al solo ruolo app (`20260703-18`),
  gate applicativo AdminAPIView super-admin.
- Introdotta con `20260703-07` (Parte 2 / Fase 2, D2-12); SECURITY DEFINER con `20260703-16`;
  guard PUBBLICATA + ≤1 BOZZA con `20260704-06`.
- Test: `db/pgtap/pratiche/test-workflow-definizioni-fase2.sql` (nuova versione + pubblica
  con ritiro) e `test-definizione-bozza-unica.sql` (guard 515/516 + flusso pulito).

---
{% include-markdown "signature-core.md" %}
