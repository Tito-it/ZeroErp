# Modalita sola lettura — Pattern "Protect"

**Data**: Marzo 2026
**Stato**: PIANO
**Prerequisito**: Sistema permessi completato (sez. 1-8 di `permessi-e-autorizzazioni.md`)
**Riferimento**: `frontend-standards.md` sezione "Modalita' sola lettura (pattern protect)"

---

## Contesto

Le autorizzazioni utente prevedono tre livelli: `TUTTO`, `LETTURA`, `BLOCCATO`.
Il backend enforce gia' il livello `LETTURA` bloccando le API write (POST/PUT/DELETE).
Il frontend non ha ancora il concetto di sola lettura: un utente con livello `LETTURA`
vede i pulsanti Salva/Nuovo ma riceve 403 al click. L'esperienza deve essere coerente:
se non puoi scrivere, il form e' in modalita' protect (ispirato ai formati protect AS/400).

**Scelta di percorso**: non esiste produzione, quindi malfunzionamenti temporanei
durante lo sviluppo non creano problemi. Si puo' procedere per fasi senza
retrocompatibilita' forzata — riscrivere liberamente.

---

## Dipendenze tra livelli (modello concentrico)

```
DB (Centro)
  config.livello_accesso ENUM: TUTTO | LETTURA | BLOCCATO
  script.fn_resolve_livello_area(user_id, schema_db) -> livello
  Gia' pronto, zero modifiche necessarie
    |
Backend (Anello 1)
  PermissionResolver.get_livello_area() -> chiama fn SQL
  ZeroERPPermission -> blocca API write per LETTURA
  Gia' pronto. Serve solo arricchire /me/ con la mappa livelli
    |
Frontend (Anello 2)
  Auth store -> carica mappa livelli da /me/
  useReadonlyMode() -> computed isReadonly per area
  CSS .app-readonly -> overlay visivo
  Tutto da fare
```

---

## Fase 0 — DB: nessuna modifica

Il DB ha gia' tutto:

- ENUM `config.livello_accesso` (`TUTTO`, `LETTURA`, `BLOCCATO`)
- `script.fn_resolve_livello_area(p_auth_user_id, p_area_schema_db)` -> `livello_accesso`
- `config.aree_funzionali` con 10 aree funzionali + `schema_db`
- Catena di risoluzione: `ruolo_sistema -> override utente -> profilo reparto -> BLOCCATO`

**Nessun intervento DB necessario.**

---

## Fase 1 — Backend: arricchire `/me/` con mappa livelli area

### 1.1 Nuova funzione DB `script.fn_get_user_permissions_map`

Anche se il DB non richiede modifiche strutturali, serve una funzione che
restituisca la mappa completa dei livelli per tutte le aree in un solo roundtrip.

| Elemento | Valore |
|----------|--------|
| Schema | `script` |
| Nome | `fn_get_user_permissions_map` |
| Parametri | `p_auth_user_id integer` |
| Ritorno | `jsonb` — `{ "anagrafiche": "TUTTO", "vendite": "LETTURA", ... }` |
| Volatilita' | STABLE |

**Logica**:

```sql
-- Scopo: Restituisce la mappa livello accesso per tutte le aree funzionali.
-- Usa fn_resolve_livello_area per ogni area attiva.
CREATE OR REPLACE FUNCTION script.fn_get_user_permissions_map(p_auth_user_id integer)
RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY INVOKER
AS $$
DECLARE
  v_result jsonb := '{}'::jsonb;
  v_area   RECORD;
BEGIN
  FOR v_area IN
    SELECT schema_db FROM config.aree_funzionali WHERE attiva = true ORDER BY schema_db
  LOOP
    v_result := v_result || jsonb_build_object(
      v_area.schema_db,
      script.fn_resolve_livello_area(p_auth_user_id, v_area.schema_db)::text
    );
  END LOOP;
  RETURN v_result;
END;
$$;
```

**Perche' una funzione dedicata e non N chiamate da Python**:
- 1 roundtrip DB vs 10 (una per area)
- La funzione e' cacheable lato Redis (L2 `permissions_cache.py`)
- Se le aree cambiano, la funzione si adatta senza toccare Python

### 1.2 Arricchire `script.fn_get_user_profile` (o alternativa: campo separato)

Due opzioni:

**Opzione A** (preferita) — aggiungere `permessi_area` al JSONB di `fn_get_user_profile`:

```sql
-- Nel body di fn_get_user_profile, aggiungere:
v_result := v_result || jsonb_build_object(
  'permessi_area', script.fn_get_user_permissions_map(p_auth_user_id)
);
```

Il `/me/` restituisce gia' un JSONB. Aggiungere una chiave non rompe nulla.

**Opzione B** — endpoint separato `/api/v1/core/me/permessi/`.
Scartata: richiederebbe una chiamata aggiuntiva dopo login e gestione cache separata.

### 1.3 Aggiornare `UserProfileView` (se opzione A)

Nessuna modifica Python — il JSONB arricchito arriva dal DB automaticamente.
Solo aggiornare lo schema `@extend_schema` per documentare il nuovo campo.

**File coinvolti**:

| File | Modifica |
|------|----------|
| `db/changelog/migrations_v2/20_code/script/` | Nuova migration: `fn_get_user_permissions_map` |
| `db/changelog/migrations_v2/20_code/script/` | Modifica migration: `fn_get_user_profile` (add `permessi_area`) |
| `backend/apps/core/api/me_view.py` | Aggiornare `@extend_schema` (campo `permessi_area`) |

---

## Fase 2 — Frontend: infrastruttura — COMPLETATO

### Strategia provide/inject

L'implementazione usa **provide/inject** per massima ottimizzazione:

- La **View** (provider) chiama `useReadonlyMode('area')` che fa `provide(READONLY_KEY, isReadonly)`
- I **componenti figli** (consumer) chiamano `useInjectReadonly()` che fa `inject(READONLY_KEY, ref(false))`
- **NewButton** e **DrawerFooter** iniettano il valore e si auto-nascondono

Vantaggi rispetto all'approccio prop-based:
- **Zero modifiche alle 10 SearchTable** (NewButton si auto-nasconde via inject)
- **Zero v-if manuali su DrawerFooter** in ogni drawer (si auto-nasconde via inject)
- Il provider e' nella View, tutti i figli (drawer, sub-drawer, toolbar) ereditano

### 2.1 CSS `.app-readonly` in `main.css` — COMPLETATO

```css
.app-readonly {
  pointer-events: none;
  user-select: text;
  opacity: 0.85;
}

.app-readonly :deep(.p-drawer-close),
.app-readonly :deep(.p-dialog-close),
.app-readonly :deep(.app-escape) {
  pointer-events: auto;
  cursor: pointer;
}
```

### 2.2 Auth store — COMPLETATO

`frontend/src/stores/auth.js` espone:
- `permessiArea` — computed dalla chiave `permessi_area` del profilo `/me/`
- `getLivelloArea(schemaDb)` — ritorna `TUTTO | LETTURA | BLOCCATO`
- `isAreaReadonly(schemaDb)` — ritorna `true` se livello = `LETTURA`

### 2.3 Composable `useReadonlyMode` — COMPLETATO

`frontend/src/core/composables/useReadonlyMode.js` (~30 righe):
- `useReadonlyMode(areaSchemaDb)` — provider, chiamato dalla View
- `useInjectReadonly()` — consumer, chiamato da drawer/NewButton/DrawerFooter
- Symbol key `READONLY_KEY` per evitare collisioni

---

## Fase 3 — Frontend: componenti core — COMPLETATO

### 3.1 `DrawerFooter` — auto-hide via inject

```vue
const isReadonly = useInjectReadonly()
<!-- template -->
<div v-if="!isReadonly" class="app-drawer-footer">
```

Il DrawerFooter inietta il readonly e si nasconde da solo.
**Zero modifiche necessarie nei drawer** per nascondere il footer.

### 3.2 `NewButton` — auto-hide via inject

```vue
const isReadonly = useInjectReadonly()
<!-- template -->
<Button v-if="!isReadonly" ... />
```

Il NewButton inietta il readonly e si nasconde da solo.
**Zero modifiche necessarie nelle 10 SearchTable.**

### 3.3 `useDrawerState` — nessuna modifica

Il readonly non e' uno stato del drawer. E' uno stato dell'utente.
Responsabilita' separate.

---

## Fase 4 — Frontend: integrazione drawer e view — COMPLETATO

### Pattern implementato

**View (provider):**
```vue
import { useReadonlyMode } from '@/core/composables/useReadonlyMode'
const { isReadonly } = useReadonlyMode('anagrafiche')
```

**Drawer (consumer):**
```vue
import { useInjectReadonly } from '@/core/composables/useReadonlyMode'
const isReadonly = useInjectReadonly()
<!-- template -->
<div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
```

### View integrate (3 provider)

| View | Area | Stato |
|------|------|-------|
| `SoggettiView.vue` | `anagrafiche` | COMPLETATO |
| `IndirizziView.vue` | `anagrafiche` | COMPLETATO |
| `ConfigTablePanel.vue` | `config` | COMPLETATO |

### Drawer integrati (11 consumer)

| Drawer | `:class` | Note |
|--------|----------|------|
| `SoggettoDrawer.vue` | COMPLETATO | + `app-escape` su pulsanti "Gestisci" |
| `IndirizzoDrawer.vue` | COMPLETATO | |
| `IndirizziSoggettoDrawer.vue` | COMPLETATO | |
| `ContattiSoggettoDrawer.vue` | COMPLETATO | |
| `GenericConfigDrawer.vue` | COMPLETATO | |
| `ToponomasticaDrawer.vue` | COMPLETATO | |
| `ComuneDrawer.vue` | COMPLETATO | |
| `CodiciPostaliDrawer.vue` | COMPLETATO | |
| `ProvinceDrawer.vue` | COMPLETATO | |
| `RegioniDrawer.vue` | COMPLETATO | |
| `StatiDrawer.vue` | COMPLETATO | |

### Pulsanti "Gestisci" con `app-escape`

In `SoggettoDrawer.vue` (edit mode), i pulsanti "Gestisci Contatti" e
"Gestisci Indirizzi" hanno la classe `app-escape`. In readonly mode restano
cliccabili perche' sono azioni di consultazione (aprono sub-drawer in readonly).
I sub-drawer ereditano il readonly dalla stessa catena provide/inject.

### Comportamento DataTable row-click in sola lettura

Il click su riga apre il drawer ugualmente (mode `edit`, dati caricati), ma:
- `.app-readonly` blocca ogni interazione nel contenuto
- DrawerFooter non viene renderizzato (auto-hide via inject)
- L'utente puo' solo consultare e chiudere (X del drawer)

Non serve un `mode: 'view'` separato.

---

## Fase 5 — Ottimizzazione: cache e invalidazione

### 5.1 Cache frontend permessi

La mappa `permessi_area` arriva con il `/me/` al login e resta in memoria
per tutta la sessione. Non serve ricaricarla ad ogni navigazione.

**Invalidazione**: quando l'admin modifica i permessi di un utente (futuro pannello
gestione permessi), il backend invalida la cache Redis (L2) tramite
`permissions_cache.invalidate_user(user_id)`. Al prossimo refresh token
il frontend ricarica `/me/` con i nuovi permessi.

### 5.2 Nessun endpoint aggiuntivo

La mappa viaggia con `/me/` — zero chiamate extra. Il costo e':
- DB: 1 chiamata `fn_get_user_permissions_map` (10 query `fn_resolve_livello_area` nel loop)
- Con cache Redis L2: 0 query DB dopo la prima richiesta della sessione
- Frontend: 0 chiamate extra — i dati sono gia' nello store auth

### 5.3 Riusabilita' composable

`useReadonlyMode(areaSchemaDb)` e' generico. Funziona per qualsiasi dominio
presente/futuro senza modifiche. Aggiungere un nuovo dominio al frontend:
basta passare lo `schema_db` corretto.

Casi d'uso futuri gia' supportati:
- **Split view** (tab affiancate): pannello secondario sempre readonly
- **Audit mode**: consultazione storica → stesso pattern CSS
- **Utente guest**: readonly globale → logica aggiuntiva nel composable

---

## Riepilogo file coinvolti

### DB (2 funzioni, gia' deploiate)

| Funzione | Stato |
|----------|-------|
| `script.fn_get_user_permissions_map(p_auth_user_id)` | COMPLETATO |
| `script.fn_get_user_profile` — aggiunta chiave `permessi_area` | COMPLETATO |

### Backend (1 file)

| File | Modifica | Stato |
|------|----------|-------|
| `backend/apps/core/api/me_view.py` | `@extend_schema` aggiornato con `permessi_area` | COMPLETATO |

### Frontend (17 file)

| File | Modifica | Stato |
|------|----------|-------|
| `frontend/src/assets/main.css` | `.app-readonly` + regole escape | COMPLETATO |
| `frontend/src/stores/auth.js` | `permessiArea`, `getLivelloArea`, `isAreaReadonly` | COMPLETATO |
| `frontend/src/core/composables/useReadonlyMode.js` | Nuovo: provider + consumer (~30 righe) | COMPLETATO |
| `frontend/src/core/components/NewButton.vue` | `useInjectReadonly` + `v-if` | COMPLETATO |
| `frontend/src/core/components/DrawerFooter.vue` | `useInjectReadonly` + `v-if` | COMPLETATO |
| `frontend/src/anagrafiche/views/SoggettiView.vue` | `useReadonlyMode('anagrafiche')` | COMPLETATO |
| `frontend/src/anagrafiche/views/IndirizziView.vue` | `useReadonlyMode('anagrafiche')` | COMPLETATO |
| `frontend/src/core/components/ConfigTablePanel.vue` | `useReadonlyMode('config')` | COMPLETATO |
| `frontend/src/anagrafiche/components/SoggettoDrawer.vue` | inject + `:class` + `app-escape` | COMPLETATO |
| `frontend/src/anagrafiche/components/IndirizzoDrawer.vue` | inject + `:class` | COMPLETATO |
| 7 drawer geo + ContattiSoggettoDrawer + GenericConfigDrawer | inject + `:class` | COMPLETATO |

**Build**: OK (525ms, 0 errori)

---

## Impatto su componenti esistenti

| Componente | Modifica | Note |
|------------|----------|------|
| **DrawerFooter** | inject + v-if | Si auto-nasconde, zero modifiche nei consumer |
| **NewButton** | inject + v-if | Si auto-nasconde, zero modifiche nelle SearchTable |
| **useDrawerState** | Nessuna | Il readonly non e' stato del drawer |
| **useSearchTable** | Nessuna | Le liste sono gia' di sola lettura |
| **useApiHandler** | Nessuna | L'overlay CSS blocca prima dell'API call |
| **DataTable** | Nessuna | Il row-click apre il drawer, il CSS fa il resto |
| **SoggettoForm** | Nessuna | Il wrap `.app-readonly` sul container basta |
| **IndirizzoSoggettoForm** | Nessuna | Idem |
| **ContattoForm** | Nessuna | Idem |
| **10 SearchTable** | Nessuna | NewButton si auto-nasconde via inject |

**Zero componenti da duplicare. Zero varianti ReadOnly da creare.**

---

## Metriche effettive

| Metrica | Valore |
|---------|--------|
| Componenti core con auto-hide | 2 (NewButton, DrawerFooter) |
| SearchTable modificate | 0 (grazie a inject) |
| File nuovi | 1 (composable) |
| File modificati | 16 |
| Righe CSS aggiunte | 15 |
| Righe JS composable | 30 |
| Righe modifica per drawer | 3 ciascuno |
| Endpoint nuovi | 0 |
| Query DB aggiuntive per sessione | 0 (viaggia con /me/) |

---

## Stato

**COMPLETATO** (18/03/2026)

- DB: funzioni deploiate
- Backend: schema aggiornato
- Frontend: infrastruttura + 11 drawer + 3 view + 2 componenti core
- Build: OK

**Da verificare**: test end-to-end da UI con utente livello `LETTURA` su area `anagrafiche`.

Controllare che:
- DrawerFooter si nasconda su tutti i drawer (soggetti, indirizzi, config)
- NewButton non sia visibile nelle SearchTable
- I form siano in overlay readonly (pointer-events bloccati)
- I pulsanti "Gestisci" (app-escape) restino cliccabili in SoggettoDrawer
- Il click su riga apra il drawer in consultazione (senza footer salva)
- Un tentativo di POST/PATCH diretto riceva 403 dal backend

---

## Principio guida

> Il DB **definisce** i livelli (TUTTO, LETTURA, BLOCCATO).
> Il backend **enforce** (ZeroERPPermission blocca le API write).
> Il frontend **riflette** (CSS protect + nasconde i controlli di scrittura).
>
> Nessun livello fa il lavoro di un altro. Il CSS non "protegge" —
> e' solo feedback visivo. La protezione reale e' nel backend.
> Se qualcuno bypassa il CSS, il 403 lo ferma comunque.
