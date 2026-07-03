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
- Differenza da [fn_fork_definizione](fn_fork_definizione.md): il fork cambia scope
  (verso un nuovo emittente, con provenance); la nuova versione resta nello **stesso**
  scope (versione successiva).
- Introdotta con `20260703-07` (Parte 2 / Fase 2, D2-12).
- Test: `db/pgtap/pratiche/test-workflow-definizioni-fase2.sql` (nuova versione + pubblica
  con ritiro della precedente).

---
{% include-markdown "signature-core.md" %}
