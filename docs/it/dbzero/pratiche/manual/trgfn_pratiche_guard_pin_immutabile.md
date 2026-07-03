## 📘 Documentazione Trigger Function – `pratiche.trgfn_pratiche_guard_pin_immutabile`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.trgfn_pratiche_default_definizione](trgfn_pratiche_default_definizione.md)
> [pratiche.trgfn_flussi_guard_definizione](trgfn_flussi_guard_definizione.md)
>
Tabelle:
>
[pratiche.pratiche](pratiche.md)
> [pratiche.workflow_definizioni](workflow_definizioni.md)

---
### 🎯 Scopo Principale

**Immutabilità del pin** (cuore di V6): l'edizione di workflow che una pratica ha
pinnato alla nascita (`pratiche.definizione_id`) è **definitiva**. Una volta valorizzata
non cambia più → le pratiche in volo restano sull'edizione con cui sono nate, qualunque
cosa accada alle definizioni dopo.

> `definizione_id` già valorizzato e cambiato → `PRATICHE_PIN_IMMUTABILE` (513)

---

### Trigger associato

| Trigger | Timing | Evento | Tabella |
|---|---|---|---|
| `trg_pratiche_a10_guard_pin_immutabile_upd` | BEFORE | UPDATE OF `definizione_id` | `pratiche.pratiche` |

Complementare al [default/auto-pin](trgfn_pratiche_default_definizione.md) (BEFORE INSERT,
descrizione `default` → gira sull'INSERT): l'uno **assegna** il pin, l'altro ne impedisce
la modifica.

---

### Regole

* Ammette **solo** la prima valorizzazione `NULL → valore`: è il caso del **backfill
  Fase 0** (`20260702-25`), che in replay CI gira in `80_data` **dopo** questo guard
  (creato in `20_code`). Condizione: `OLD.definizione_id IS NOT NULL AND OLD IS DISTINCT
  FROM NEW`.
* Una pratica non ancora pinnata (`OLD` NULL) può ricevere il pin; una già pinnata non
  può cambiarlo (né verso un'altra definizione, né verso NULL).
* La coerenza col tipo è garantita a monte dalla FK composita
  `(definizione_id, tipo_prestazione_id)`; questo guard aggiunge l'**immutabilità**.

---

### Note operative

* Errore: `PRATICHE_PIN_IMMUTABILE` (513). Per usare un'altra edizione la pratica va
  ricreata (nasce sul pin risolto alla creazione).
* Introdotto con `20260703-04` (brief-db-step-dominio-e-definizioni-versionate, Parte 2 /
  Fase 1, D2-9b).
* Test: `db/pgtap/pratiche/test-workflow-definizioni-fase1.sql` (caso 4).
