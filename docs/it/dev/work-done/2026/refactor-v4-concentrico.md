# Refactor v4 — Completamento Modello Concentrico

**Data**: Marzo 2026
**Stato**: COMPLETATO (18/03/2026)
**Prerequisito**: Refactor v3 completato (18/03/2026)

---

## Contesto

Post refactor v3 il codebase è all'85% di aderenza concentrica.
Le aree migliorate (check duplicato nel DB, scomposizione composable, eliminazione
duplicazione payload) sono solide. Restano 4 violazioni concrete.

| Violazione | Dove | Tipo |
|------------|------|------|
| Auto-clone indirizzi obbligatori | `useIndirizzoSoggettoForm.js` | Business logic nel frontend |
| Manipolazione payload replace | `IndirizziSoggettoDrawer.vue` | Business logic nel componente |
| `addressNotFound` duplicato | 2 drawer | Duplicazione codice |
| Loop creazione indirizzi | `IndirizziSoggettoDrawer.vue` | Orchestrazione frammentata |

**Non sono problemi**: CAP auto-set (è UX), validate form (è UX),
check duplicato real-time (è UX con debounce).

---

## Fase 1 — Backend: auto-clone e replace intelligente

### 1.1 Spostare auto-clone nel backend

**Stato attuale** — frontend clona il primo indirizzo per i tipi obbligatori mancanti:

```javascript
// useIndirizzoSoggettoForm.js — LOGICA DOMINIO NEL FRONTEND
if (multiTipo.autoClone.value && result.length > 0) {
  const primoSalvato = Object.values(salvati)[0]
  for (const m of multiTipo.tipiMatrice.value) {
    if (m.obbligatorio && !salvati[m.codice]) {
      result.push(_buildPayload(primoSalvato, m.codice))
    }
  }
}
```

**Refactor** — il frontend manda solo gli indirizzi compilati dall'utente +
un flag `auto_clone`. Il backend gestisce la clonazione:

```python
# soggetti_service.py — LOGICA DOMINIO NEL BACKEND
def _apply_auto_clone(self, soggetto_id, indirizzi, tipo_id):
    """Auto-clona il primo indirizzo per i tipi obbligatori mancanti."""
    if not indirizzi:
        return
    matrice = self._repo.list_matrice_indirizzi(tipo_id)
    tipi_presenti = {ind["tipo_indirizzo_codice"] for ind in indirizzi}
    primo = indirizzi[0]
    for m in matrice:
        if m["obbligatorio"] and m["codice"] not in tipi_presenti:
            clone = {**primo, "tipo_indirizzo_codice": m["codice"]}
            indirizzi.append(clone)
```

**Impatto su create_soggetto**:

```python
def create_soggetto(self, payload):
    with transaction.atomic():
        soggetto_id = self._create_pf_or_pg(payload, natura, tipo_id)
        indirizzi = payload.get("indirizzi") or []
        if payload.get("auto_clone", True):
            self._apply_auto_clone(soggetto_id, indirizzi, tipo_id)
        self._create_indirizzi_batch(soggetto_id, indirizzi)
    return {"id": soggetto_id}
```

**File coinvolti**:
- `soggetti_service.py` — aggiungere `_apply_auto_clone`, estrarre `_create_indirizzi_batch`
- `useIndirizzoSoggettoForm.js` — rimuovere logica auto-clone da `toPayloadArray`
- Nessun endpoint nuovo — il payload passa da `indirizzi[]` con N elementi a
  `indirizzi[]` con solo quelli compilati + `auto_clone: true`

### 1.2 Replace intelligente nel backend

**Stato attuale** — il drawer manipola il payload cancellando campi:

```javascript
// IndirizziSoggettoDrawer.vue — BUSINESS LOGIC NEL COMPONENTE
if (!payload.indirizzo_libero && indirizzo.existingDettaglioId.value) {
  payload.indirizzo_dettaglio_id = indirizzo.existingDettaglioId.value
  delete payload.stradario_id
  delete payload.civico
  // ... delete 5 campi
}
```

**Refactor** — il frontend manda il payload completo. Il backend decide:

```python
# soggetti_service.py
def replace_indirizzo_soggetto(self, soggetto_id, old_id, payload):
    with transaction.atomic():
        self._repo.delete_indirizzo_soggetto(old_id, soggetto_id)
        # Il backend risolve: se indirizzo_dettaglio_id passato → usa quello,
        # altrimenti _resolve_indirizzo_dettaglio crea/cerca
        sog_id, _ = self._create_indirizzo(soggetto_id, payload)
    return {"id": sog_id}
```

Il backend già gestisce `indirizzo_dettaglio_id` in `_resolve_indirizzo_dettaglio`.
Il frontend non ha più bisogno di manipolare il payload.

**Impatto frontend** — `onSaveForm` in replace mode diventa:

```javascript
if (formMode.value === 'replace') {
  const payload = payloads[0]
  // Passa existingDettaglioId se esatto → backend lo usa direttamente
  if (indirizzo.existingDettaglioId.value) {
    payload.indirizzo_dettaglio_id = indirizzo.existingDettaglioId.value
  }
  await execute(() => replaceSoggettoIndirizzo(..., payload))
}
```

Niente più `delete` di campi — il backend ignora stradario_id/civico se
`indirizzo_dettaglio_id` è presente (già implementato in `_resolve_indirizzo_dettaglio`).

**File coinvolti**:
- `IndirizziSoggettoDrawer.vue` — semplificare `onSaveForm` replace path

### 1.3 Estrarre `_create_indirizzi_batch` da `create_soggetto`

**Stato attuale** — `create_soggetto` ha 40+ righe con loop indirizzi + riuso dettaglio:

```python
resolved_det_id: int | None = None
for ind in indirizzi:
    if resolved_det_id and not ind.get("indirizzo_libero") and not ind.get("indirizzo_dettaglio_id"):
        ind = dict(ind, indirizzo_dettaglio_id=resolved_det_id)
    _, det_id = self._create_indirizzo(soggetto_id, ind)
    if resolved_det_id is None and det_id is not None:
        resolved_det_id = det_id
```

**Refactor** — estrarre in metodo dedicato:

```python
def _create_indirizzi_batch(self, soggetto_id, indirizzi):
    """Crea indirizzi in batch con riuso dettaglio per auto-clone."""
    resolved_det_id = None
    for ind in indirizzi:
        if not isinstance(ind, dict):
            continue
        if resolved_det_id and not ind.get("indirizzo_libero") and not ind.get("indirizzo_dettaglio_id"):
            ind = dict(ind, indirizzo_dettaglio_id=resolved_det_id)
        _, det_id = self._create_indirizzo(soggetto_id, ind)
        if resolved_det_id is None and det_id is not None:
            resolved_det_id = det_id
```

`create_soggetto` diventa:

```python
def create_soggetto(self, payload):
    with transaction.atomic():
        soggetto_id = ...
        indirizzi = payload.get("indirizzi") or []
        if payload.get("auto_clone", True):
            self._apply_auto_clone(soggetto_id, indirizzi, tipo_id)
        self._create_indirizzi_batch(soggetto_id, indirizzi)
    return {"id": soggetto_id}
```

Metodo orchestratore da 40+ righe → ~15 righe. Chiaro, testabile.

---

## Fase 2 — Frontend: centralizzare e semplificare

### 2.1 Centralizzare `addressNotFound` in useIndirizzoBase

**Stato attuale** — stessa computed duplicata in 2 componenti:

```javascript
// IndirizziSoggettoDrawer.vue (riga 99) — DUPLICATO
const addressNotFound = computed(() =>
  !indirizzo.isLibera.value && !indirizzo.form.via_nuova
  && indirizzo.form.via_obj?.stradario_id && indirizzo.form.civico
  && !indirizzo.existingDettaglioId.value
)

// IndirizzoDrawer.vue (riga 51) — DUPLICATO
const addressNotFound = computed(() =>
  isCreate.value && !addr.form.via_nuova
  && addr.form.via_obj?.stradario_id && addr.form.civico
  && !addr.existingDettaglioId.value
)
```

**Refactor** — spostare in `useIndirizzoBase` come computed esportato:

```javascript
// useIndirizzoBase.js
const addressNotFound = computed(() =>
  !form.via_nuova
  && form.via_obj?.stradario_id
  && form.civico
  && !existingDettaglioId.value
)
```

I drawer aggiungono solo le condizioni locali:

```javascript
// IndirizziSoggettoDrawer.vue
const blocked = computed(() => !indirizzo.isLibera.value && indirizzo.addressNotFound.value)

// IndirizzoDrawer.vue
const blocked = computed(() => isCreate.value && addr.addressNotFound.value)
```

**File coinvolti**:
- `useIndirizzoBase.js` — aggiungere `addressNotFound` al return
- `IndirizziSoggettoDrawer.vue` — usare `indirizzo.addressNotFound`
- `IndirizzoDrawer.vue` — usare `addr.addressNotFound`

### 2.2 Semplificare `toPayloadArray` (dopo fase 1.1)

**Dopo** lo spostamento dell'auto-clone al backend, `toPayloadArray` diventa:

```javascript
function toPayloadArray() {
  multiTipo.salvaSnapshot()
  const salvati = { ...multiTipo.indirizziSalvati.value }
  return Object.entries(salvati).map(([codice, data]) => _buildPayload(data, codice))
}
```

Zero logica di clonazione. Solo conversione snapshot → payload.

### 2.3 Semplificare `onSaveForm` nel drawer (dopo fase 1.2)

**Dopo** il replace intelligente, `onSaveForm` diventa:

```javascript
async function onSaveForm() {
  const payloads = indirizzo.toPayloadArray()
  if (!payloads.length) return

  let success = true

  if (formMode.value === 'replace') {
    const payload = payloads[0]
    if (indirizzo.existingDettaglioId.value) {
      payload.indirizzo_dettaglio_id = indirizzo.existingDettaglioId.value
    }
    const result = await execute(
      () => replaceSoggettoIndirizzo(props.soggettoId, replaceId.value, payload),
      { successMessage: t('indirizzi.indirizzo_salvato') }
    )
    if (result === null) success = false
  } else {
    for (const p of payloads) {
      const result = await execute(
        () => createSoggettoIndirizzo(props.soggettoId, p),
        { successMessage: t('indirizzi.indirizzo_creato') }
      )
      if (result === null) { success = false; break }
    }
  }

  if (success) {
    formMode.value = null
    replaceId.value = null
    indirizzo.reset()
    await loadIndirizzi()
    emit('saved')
  }
}
```

Niente più `delete` di campi dal payload. Il backend gestisce.

---

## Fase 3 — Test

### 3.1 Test backend auto-clone

```python
# test_soggetti_service.py
def test_auto_clone_indirizzi_obbligatori(self):
    """Verifica che i tipi obbligatori mancanti vengano clonati dal primo."""
    ...

def test_auto_clone_skip_libero(self):
    """Se il primo indirizzo e' libero, non clonare per normalizzati."""
    ...

def test_no_auto_clone_if_flag_false(self):
    """Se auto_clone=False, nessuna clonazione."""
    ...
```

### 3.2 Test backend replace intelligente

```python
def test_replace_con_dettaglio_esistente(self):
    """Replace con indirizzo_dettaglio_id passa diretto, ignora campi civico."""
    ...

def test_replace_senza_dettaglio(self):
    """Replace senza indirizzo_dettaglio_id crea nuovo dettaglio."""
    ...
```

---

## Ordine di esecuzione

Nessun vincolo di retrocompatibilità — si può riscrivere liberamente.

| Step | Cosa | File | Effort |
|------|------|------|--------|
| 1 | `_create_indirizzi_batch` + `_apply_auto_clone` | `soggetti_service.py` | Basso |
| 2 | Semplificare `create_soggetto` | `soggetti_service.py` | Basso |
| 3 | Rimuovere auto-clone da `toPayloadArray` | `useIndirizzoSoggettoForm.js` | Basso |
| 4 | Centralizzare `addressNotFound` | `useIndirizzoBase.js` + 2 drawer | Basso |
| 5 | Semplificare replace payload | `IndirizziSoggettoDrawer.vue` | Basso |
| 6 | Test backend | `test_soggetti_service.py` | Medio |
| 7 | Build + test completo | — | Basso |

**Effort totale**: ~2h di lavoro, tutto basso rischio.

---

## Metriche attese post-v4

| Principio | v3 (attuale) | v4 (atteso) |
|-----------|-------------|-------------|
| DB-first (logica in PostgreSQL) | 70% | 80% |
| Django orchestrazione | 85% | 95% |
| Vue solo presentazione | 60% | 85% |
| No logica duplicata | 80% | 95% |
| **Score globale** | **85%** | **~92%** |

Il 100% non è l'obiettivo — il restante 8% è validazione UX (form),
CAP auto-set, check duplicato real-time. Sono nel frontend per necessità
di UX e non violano il concentrico perché il DB resta la source of truth.

---

## Principio guida

> Il frontend **determina** (l'utente sceglie cosa compilare).
> Il backend **orchestra** (applica policy, clona, risolve, valida).
> Il DB **garantisce** (trigger, constraint, funzioni).
>
> Quando il frontend fa `if (obbligatorio && !salvato)` sta orchestrando.
> Quando il backend fa lo stesso, sta applicando una policy.
> La differenza è dove vive la regola.
