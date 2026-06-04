# Brief BE/FE — LANDED `classify_contatto_payload` regola unificata contatti inline (Fase 5 refactor anagrafiche, bug logico modello C1)

> **Stato**: LANDED 2026-04-28
> **Branch BE/FE**: `dev/backend-tid`
> **DB**: nessuna modifica (lo schema ha gia' `NOT NULL` su `nominativo` e `tipo_contatto_id` come safety net)
> **Origine**: analisi C1 in `analisi-refactor.frontend-anagrafiche.md`
> **Pattern**: A2 defense-in-depth (regola scritta backend = verita' unica, mirror nel composable frontend per UX immediata)

## 1. Bug logico individuato (recap)

Tre drawer fratelli (Cliente, Fornitore, Soggetto) con tre regole divergenti su "quando un contatto inline e' considerato compilato":

| Drawer pre-fix | Comportamento backend | Comportamento frontend | Bug |
|---|---|---|---|
| Cliente | `if contatto and nominativo: crea` (silent skip) | "qualunque campo" → valida | OK end-to-end (per accident: FE blocca prima) |
| Fornitore | `if contatto and nominativo: crea` (silent skip) | "solo nominativo conta" → ignora altri campi | **Bug**: utente compila solo email → email persa silenziosamente |
| Soggetto | `require_str(nominativo)` (errore) | manda sempre payload contatto | OK ma con auto-fill nominativo da cognome+nome che maschera la regola |

Nessuno aveva definito a livello modello dominio cosa significa "contatto compilato". Tre implementazioni divergenti.

## 2. Decisione canonica

Regola **A** (versione Cliente): se almeno UN campo tra `nominativo`,
`email`, `telefono`, `cellulare`, `pec`, `tipo_contatto_id` e' valorizzato
→ il contatto e' "in compilazione" e richiede gli obbligatori
(`nominativo` + `tipo_contatto_id`).

Stati canonici:

- `EMPTY` = nessun campo valorizzato → caller decide (cliente/fornitore: skip; soggetto: errore perche' contatto obbligatorio)
- `PARTIAL` = almeno un campo MA mancano obbligatori → errore esplicito `E_CONTATTO_INCOMPLETO`
- `VALID` = nominativo + tipo_contatto_id presenti → crea

## 3. Implementazione backend

### 3.1 Nuovo modulo `apps/anagrafiche/services/contatti_service.py`

```python
def classify_contatto_payload(data: dict | None) -> str:
    """Ritorna 'EMPTY' | 'PARTIAL' | 'VALID'."""

def missing_required_fields(data: dict | None) -> list[str]:
    """Per error context UI: lista campi obbligatori mancanti."""
```

Helper `_is_filled()` interno per coerenza: stringhe vuote / spaziature / `0` / `None` / `False` = non valorizzato. `tipo_contatto_id` deve essere `> 0` (FK).

### 3.2 Refactor 3 service

- [`clienti_service.py:307`](../../../../backend/apps/anagrafiche/services/clienti_service.py#L307): EMPTY → skip; PARTIAL → raise; VALID → crea.
- [`fornitori_service.py:100`](../../../../backend/apps/anagrafiche/services/fornitori_service.py#L100): stesso pattern. **Fix bug originale**: prima ignorava email/telefono se senza nominativo.
- [`soggetti_service.py`](../../../../backend/apps/anagrafiche/services/soggetti_service.py): nuovo helper privato `_require_contatto_valid(contatto)` che richiede sempre VALID (contatto obbligatorio per soggetto). Usato in `_create_pf` e `_create_pg` al posto del vecchio `require_str(contatto, "nominativo")`.

### 3.3 Error code mapping

[`apps/core/services/error_policies.py`](../../../../backend/apps/core/services/error_policies.py): nuova policy `E_CONTATTO_INCOMPLETO` (HTTP 400 + `highlight_form_fields`) con messaggio user-friendly. [`apps/anagrafiche/error_codes.py`](../../../../backend/apps/anagrafiche/error_codes.py): costante esportata.

### 3.4 Test

[`apps/anagrafiche/tests/services/test_contatti_service.py`](../../../../backend/apps/anagrafiche/tests/services/test_contatti_service.py): 14 test unit per `classify_contatto_payload` + `missing_required_fields`. Coprono:

- None / `{}` / tutti vuoti → EMPTY
- email/telefono/nominativo/tipo singoli → PARTIAL (regressione esplicita per bug fornitore)
- whitespace su nominativo → PARTIAL
- `tipo_contatto_id = 0` → PARTIAL (FK non valida)
- nominativo+tipo presenti → VALID

Test esistenti soggetti aggiornati per fornire `tipo_contatto_id` nelle fixture (allineati al NOT NULL DB).

**Test totale**: 829/829 verdi (15 nuovi rispetto a Fase 3).

## 4. Implementazione frontend

### 4.1 Estensione `useContattoForm`

[`frontend/src/core/composables/useContattoForm.js`](../../../../frontend/src/core/composables/useContattoForm.js): aggiunti tre metodi mirror del backend:

```js
function classify()  // 'EMPTY' | 'PARTIAL' | 'VALID'
function isEmpty()
function isFilled()  // !isEmpty
```

Stessa regola del backend (defense-in-depth UX). Helper `_isFilled` interno coerente con la versione Python.

### 4.2 Aggiornamento drawer

- [`ClienteDrawer.vue:309-329`](../../../../frontend/src/anagrafiche/components/ClienteDrawer.vue#L309): rimosso check `hasAnyContatto` inline (7 righe → uso di `contatto.isFilled()`).
- [`FornitoreDrawer.vue:161-168`](../../../../frontend/src/anagrafiche/components/FornitoreDrawer.vue#L161): rimosso check "solo nominativo" (bug fix end-to-end).
- `SoggettoDrawer.vue`: nessun cambio FE necessario — il `canSave` esistente gia' richiede `contatto.validate().length === 0` (cioe' VALID), pattern allineato. Il backend ora protegge anche il caso edge (cancellazione manuale post auto-fill).

### 4.3 Pulsante "pulisci contatto" (rinviato)

Citato nel piano originale come bonus UX. Rinviato a quando si fara' un refactor mirato dei drawer (richiede ridisegno mini-UI nel ContattoForm). Non bloccante.

## 5. Cambio comportamento osservabile

### Per chi usa l'UI

- **Cliente**: invariato (FE gia' bloccava prima del save).
- **Fornitore**: bug fixato — se l'utente scrive email senza nominativo, ora vede errore esplicito con campi mancanti, prima l'email veniva persa silenziosamente.
- **Soggetto**: invariato (auto-fill nominativo da cognome+nome continua a garantire VALID).

### Per chi usa l'API direttamente

- POST `/api/v1/anagrafiche/clienti/` con `{contatto: {email: "x@y.it"}}` (no nominativo) → prima `200 OK` (email scartata), ora `400 E_CONTATTO_INCOMPLETO` con `context.missing = ["nominativo", "tipo_contatto_id"]`.
- Stesso per fornitori e soggetti.
- POST soggetto senza `tipo_contatto_id` → ora `400 E_CONTATTO_INCOMPLETO` (prima `400 E_ANAG_VALIDAZIONE` se mancava nominativo, ma `tipo_contatto_id` non era validato applicativamente).

**Defense-in-depth DB**: schema `anagrafiche.contatti` ha `NOT NULL` su `nominativo` e `tipo_contatto_id` → qualunque bypass del backend solleva IntegrityError comunque.

## 6. Pattern emerso

Pattern **A2 defense-in-depth** (regola unica scritta backend, mirror frontend) qui applicato per la prima volta a una regola di "validazione semantica del payload" (vs. precedenti applicazioni a normalize+guard data-driven). Se in futuro arriveranno altre regole sui payload contatto inline (es. validazione email esterna, lookup unita organizzativa), il punto di estensione e' chiaro: `classify_contatto_payload` o nuovo helper accanto.

## 7. Riferimenti

- [analisi-refactor.frontend-anagrafiche.md](analisi-refactor.frontend-anagrafiche.md) — sezione C1 (LANDED 28-04)
- Pattern simmetrici: [brief-be-clienti-fornitori-normalize-payload.md](brief-be-clienti-fornitori-normalize-payload.md) (Fase 2)
- Modulo: [`contatti_service.py`](../../../../backend/apps/anagrafiche/services/contatti_service.py)
