# Architettura Building Block — DB, Backend, Frontend

> Documento master per la scomposizione in building block riutilizzabili su tutti i livelli.
> Data: 2026-03-12 | Aggiornato: 2026-03-14
> Stato: **Backend COMPLETATO — Frontend PARZIALMENTE COMPLETATO (FE-1..FE-9, FE-11)**
>
> Documenti correlati:
>
> * [Building Block Repository (backend)](../backend/building-block-repository.md) — piano backend **completato**
> * [Amministrazione Utenti](amministrazione-utenti.md) — Sprint 2 originale **completato**
>
> Guide di riferimento:
>
> * [Guida Soggetti e Ruoli Anagrafici](/guide/soggetti-e-ruoli-anagrafici)
> * [Guida Gestione dei Contatti](/guide/gestione-dei-contatti)
> * [Guida Generazione di un Cliente](/guide/generazione-cliente)
> * [Guida Sviluppo Frontend](guida-sviluppo-frontend.md)

---

## Motivazione

Il modulo Amministrazione (Sprint 2) ha prodotto componenti monolitici come `UtenteDrawer.vue`
che contengono form per persona, accesso, contatto e collocazione in un unico blocco.
Lo stesso form "persona fisica" servira' per creare un cliente PF, un fornitore PF, un referente.
Lo stesso form "contatto" servira' ovunque si crei un soggetto (vincolo DEFERRED `E_SOGGETTO_NO_CONTATTI`).

Senza scomposizione, ogni dominio riduplica gli stessi form con varianti minime.

### Principio guida

> **Il frontend rispecchia l'architettura DB**: cosi' come il database ha building block SQL
> riutilizzabili (`fn_crea_soggetto_pf`, `fn_crea_auth_user`, `fn_get_or_create_soggetto_ruolo`),
> il frontend ha componenti Vue atomici che si compongono nelle view di dominio.

---

## Stato attuale per livello

L'architettura building block si sviluppa su 3 livelli. Ogni livello ha il proprio
documento di dettaglio; questa sezione riassume lo stato complessivo.

### DB — Building block SQL (completato)

Il DB ha scomposto la funzione monolitica `fn_crea_operatore` in building block atomici:

| Funzione                               | Scopo                                       | Riusabile da                        |
| -------------------------------------- | ------------------------------------------- | ----------------------------------- |
| `fn_crea_auth_user(...)`               | Crea solo `auth_user`                       | operatore, admin, qualsiasi utente  |
| `fn_crea_soggetto_pf(...)`             | Crea soggetto PF + contatto default         | operatore, cliente PF, fornitore PF |
| `fn_get_or_create_soggetto_ruolo(...)` | Crea/recupera ruolo soggetto                | tutti                               |
| `fn_crea_risorsa_umana(...)`           | Crea risorsa_umana + bridge auth_user       | operatore, admin, dipendenti        |
| `fn_crea_operatore(...)`               | **Orchestratore** — chiama i building block | solo operatore                      |

Gestito sul server DB. Dettagli nelle guide di schema.

### Backend — Repository core (completato)

I repository Python mappano 1:1 i building block SQL.
Dettaglio completo: [Building Block Repository](../backend/building-block-repository.md)

| Repository                   | Metodo                 | In `apps/core/db/`                 |
| ---------------------------- | ---------------------- | ---------------------------------- |
| `AuthRepository`             | `crea_auth_user()`     | `auth_repository.py`               |
| `AnagraficheCoreRepository`  | `crea_soggetto_pf()`   | `anagrafiche_core_repository.py`   |
| `RisorseUmaneCoreRepository` | `crea_risorsa_umana()` | `risorse_umane_core_repository.py` |

L'orchestratore resta in `apps/amm_software/db/amm_software_repository.py` → `crea_operatore()`.

52 test backend OK + smoke test.

### Frontend — Componenti atomici (parzialmente completato)

I componenti Vue mappano i building block come descritto nelle sezioni seguenti.
Primo consumer: refactor di `UtenteDrawer.vue` — **completato** (Sprint 3, 2026-03-14).

**Implementati:**

* `SoggettoForm.vue` — form universale PF/PG/ENTE (unificato, non separato PF+PG)
* `AuthUserForm.vue` — form credenziali di accesso
* `ComuneAutocomplete.vue` — autocomplete comuni con ricerca server-side
* `StradarioAutocomplete.vue` — autocomplete stradario per comune
* `useSoggettoForm.js` — composable universale con matrice tipi soggetto
* `useAuthUser.js` — composable credenziali con password match
* `useLookup.js` — cache generica per lookup API
* `useServerAutocomplete.js` — composable ricerca server-side con debounce

**Da implementare (domini futuri: clienti, fornitori):**

* `ContattoForm.vue` — form contatto (obbligatorio per guard DEFERRED)
* `IndirizzoForm.vue` — form indirizzo normalizzato/libero
* `DatiSocietariForm.vue` — form dati camerali SC/ENC
* `UOSelect.vue` — select unita' organizzativa con gerarchia

---

## Vincoli dal modello dati

Prima di definire i componenti, e' fondamentale capire cosa il DB richiede
al COMMIT di una transazione che crea un soggetto.

### Vincoli DEFERRED (scattano al COMMIT)

| Trigger                                        | Tabella    | Errore                      | Cosa richiede                                                            |
| ---------------------------------------------- | ---------- | --------------------------- | ------------------------------------------------------------------------ |
| `trgfn_soggetti_guard_soggetto_contatti`       | `soggetti` | `E_SOGGETTO_NO_CONTATTI`    | Almeno un contatto default per ogni soggetto                             |
| `trgfn_soggetti_guard_indirizzi_required`      | `soggetti` | `E_SOGGETTO_NO_INDIRIZZI`   | Indirizzi obbligatori in base a `tipi_soggetto_dettaglio_tipi_indirizzo` |
| `trgfn_soggetti_guard_dati_societari_required` | `soggetti` | `E_DATI_SOCIETARI_REQUIRED` | Dati societari per SC/ENC (non per PF)                                   |

### Implicazioni per i form

* **Creare un soggetto senza contatto** = errore garantito al COMMIT
* **Creare un soggetto PG senza dati societari** = errore per SC/ENC
* **Indirizzi** = dipendono dalla matrice config; per PR (Privato) potrebbe non essere obbligatorio

Questo significa che i form "Soggetto" e "Contatto" sono **inseparabili**:
ogni view che crea un soggetto DEVE includere anche il form contatto.

---

## Catena completa — dal DB al frontend

```
DB (building block SQL)        Backend (repository core)          Frontend (componenti Vue)
──────────────────────         ────────────────────────           ─────────────────────────
fn_crea_auth_user         →    AuthRepository                →    AuthUserForm.vue
fn_crea_soggetto_pf       →    AnagraficheCoreRepository     →    SoggettoPFForm.vue + ContattoForm.vue
fn_get_or_create_soggetto_ruolo  (auto — chiamato dai building block, nessun form)
fn_crea_risorsa_umana     →    RisorseUmaneCoreRepository    →    CollocazioneForm.vue (UO + qualifica)

fn_crea_operatore         →    AmmSoftwareRepository         →    UtenteDrawer.vue (compone i form)
(futuro) fn_crea_cliente  →    (futuro) ClienteRepository    →    ClienteDrawer.vue (compone diversi)
```

**Flusso dati**: il frontend manda un payload unificato → il backend (service/view)
scompone e chiama i building block SQL nella sequenza corretta → tutto in una transazione.

**I repository core** (`apps/core/db/`) sono gia' implementati e testati.
I domini futuri (clienti, fornitori) li riuseranno senza modificarli.

---

## Componenti atomici — Catalogo

### Collocazione: `src/core/components/`

Tutti i componenti riutilizzabili cross-dominio stanno in `core/components/`.
I componenti specifici di un dominio (es. `ClienteDatiForm.vue`) stanno in `src/<dominio>/components/`.

### 1. SoggettoForm.vue — Form universale PF/PG/ENTE (COMPLETATO)

> **Nota**: il catalogo originale prevedeva componenti separati `SoggettoPFForm.vue` e `SoggettoPGForm.vue`.
> L'implementazione reale (Sprint 3) li ha unificati in un unico `SoggettoForm.vue` guidato dalla matrice
> `tipi_soggetto_dettaglio`, come da piano FE-4/FE-5.

**Scopo**: raccogliere i dati identificativi di qualsiasi soggetto (PF, PG, ENTE).
Il form si adatta automaticamente al tipo selezionato mostrando/nascondendo i campi appropriati.

**Campi sezione PF** (PR, DI):

| Campo             | Tipo               | Obbligatorio | Note                                    |
| ----------------- | ------------------ | ------------ | --------------------------------------- |
| cognome           | InputText          | si           | Trim + uppercase dal trigger DB         |
| nome              | InputText          | si           | Trim + uppercase dal trigger DB         |
| sesso             | Select             | si           | Default 'M', valori: M/F                |
| data_nascita      | DatePicker         | no           |                                         |
| comune_nascita_id | ComuneAutocomplete | no           | Autocomplete server-side (8098 comuni)  |

**Campi sezione PG** (SC, SP, ENC):

| Campo                      | Tipo      | Obbligatorio | Note                       |
| -------------------------- | --------- | ------------ | -------------------------- |
| ragione_sociale            | InputText | si           |                            |

**Campi sempre visibili:**

| Campo                      | Tipo      | Obbligatorio         | Note                                 |
| -------------------------- | --------- | -------------------- | ------------------------------------ |
| tipo_soggetto_dettaglio_id | Select    | si                   | Nascosto se `tipoForzato` attivo     |
| codice_fiscale             | InputText | dipende dalla natura | 16 char alfanum                      |
| partita_iva                | InputText | se PG/DI             | Visibile tramite `showPartitaIva`    |

**Props** (implementazione reale):

```js
defineProps({
  form: { type: Object, required: true },
  tipiSoggetto: { type: Object, required: true },
  isPF: { type: Boolean, default: true },
  showPartitaIva: { type: Boolean, default: false },
  tipoForzato: { type: Number, default: null },
  disabled: { type: Boolean, default: false }
})
```

**Composable associato**: `useSoggettoForm(options)` — gestisce state, computed guidati dalla matrice DB, reset.

**Riusato da**: Crea operatore (tipoForzato=1), Crea cliente PF/PG (futuro), Crea fornitore (futuro).

**File**: `src/core/components/SoggettoForm.vue`, `src/core/composables/useSoggettoForm.js`

---

### 3. ContattoForm.vue — Form contatto (DA IMPLEMENTARE)

**Scopo**: raccogliere i dati di un contatto associabile a soggetto, ruolo o utility.

**Campi**:

| Campo                  | Tipo              | Obbligatorio | Note                         |
| ---------------------- | ----------------- | ------------ | ---------------------------- |
| nominativo             | InputText         | si           | Nome del referente           |
| email                  | InputText         | no*          | Almeno un canale consigliato |
| telefono               | InputText         | no           |                              |
| cellulare              | InputText         | no           |                              |
| pec                    | InputText         | no           |                              |
| unita_organizzativa_id | Select (UOSelect) | no           | Reparto/ufficio              |
| tipo_contatto_id       | Select            | no           | Categoria                    |
| note                   | Textarea          | no           |                              |

**Props**:

```js
defineProps({
  modelValue: { type: Object, required: true },
  // { nominativo, email, telefono, cellulare, pec, unita_organizzativa_id, tipo_contatto_id, note }
  readonly: { type: Boolean, default: false },
  requireEmail: { type: Boolean, default: false },
  // true per operatori (email = username accesso)
  showUO: { type: Boolean, default: true },
  showTipoContatto: { type: Boolean, default: false }
})
```

**Riusato da**: Crea operatore, Crea cliente, Crea fornitore, Gestione contatti da scheda soggetto.

**Note sul contesto**: il form non si occupa dei campi `soggetto_id`, `soggetto_ruolo_id`, `utility_id`.
Quelli sono responsabilita' della view/drawer che compone il form e li passa al backend nel payload.

---

### 4. IndirizzoForm.vue — Form indirizzo (DA IMPLEMENTARE)

**Scopo**: raccogliere un indirizzo in modalita' normalizzata o libera.

**Campi modalita' normalizzata**:

| Campo                  | Tipo         | Obbligatorio | Note                                         |
| ---------------------- | ------------ | ------------ | -------------------------------------------- |
| tipo_indirizzo_id      | Select       | si           | Filtrato dalla matrice config                |
| indirizzo_dettaglio_id | Autocomplete | si           | Ricerca su `anagrafiche.indirizzi_dettaglio` |

**Campi modalita' libera** (fallback per esteri/non normalizzabili):

| Campo                          | Tipo      | Obbligatorio | Note |
| ------------------------------ | --------- | ------------ | ---- |
| indirizzo_libero               | InputText | si           |      |
| stato_id                       | Select    | si           |      |
| comune_id / locality           | InputText | si           |      |
| codice_postale_id / postal_box | InputText | si           |      |

**Props**:

```js
defineProps({
  modelValue: { type: Object, required: true },
  readonly: { type: Boolean, default: false },
  tipoSoggettoDettaglioId: { type: Number, default: null }
  // Se fornito, filtra i tipi indirizzo ammessi dalla matrice config
})
```

**Riusato da**: Soggetto (indirizzi_soggetti), Istanza (indirizzo fornitura), Scheda qualsiasi.

---

### 5. AuthUserForm.vue — Form credenziali di accesso (COMPLETATO)

**Scopo**: raccogliere username, email e password per un utente Django.

**Campi**:

| Campo            | Tipo      | Obbligatorio      | Note                              |
| ---------------- | --------- | ----------------- | --------------------------------- |
| username         | InputText | si                |                                   |
| email            | InputText | si                | Formato email                     |
| password         | Password  | si (in creazione) | Con toggle visibilita' e conferma |
| password_confirm | Password  | si (in creazione) | Match con password                |

**Props** (implementazione reale):

```js
defineProps({
  form: { type: Object, required: true },
  // { username, email, password, password_confirm }
  passwordMatch: { type: Boolean, default: true }
})
```

**Composable associato**: `useAuthUser()` — gestisce state, `passwordMatch` computed, reset.

**Riusato da**: Crea operatore, Crea admin, Reset password (solo campo password).

**File**: `src/core/components/AuthUserForm.vue`, `src/core/composables/useAuthUser.js`

---

### 6. DatiSocietariForm.vue — Form dati camerali (DA IMPLEMENTARE)

**Scopo**: raccogliere forma giuridica, REA, capitale sociale per PG/ENC.

**Campi**:

| Campo              | Tipo        | Obbligatorio  | Note                                                          |
| ------------------ | ----------- | ------------- | ------------------------------------------------------------- |
| forma_giuridica_id | Select      | si per SC/ENC | Filtrato da `config.forme_giuridiche_tipi_soggetto_dettaglio` |
| rea                | InputText   | no            |                                                               |
| capitale_sociale   | InputNumber | no            |                                                               |

**Riusato da**: Crea cliente PG, Crea fornitore PG, Scheda emittente fiscale, Scheda gestore.

---

### 7. UOSelect.vue — Select unita' organizzativa (DA IMPLEMENTARE)

**Scopo**: Select filtrato sulle UO attive, con supporto gerarchia.

**Props**:

```js
defineProps({
  modelValue: { type: Number, default: null },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  filter: { type: Boolean, default: true }
})
```

**Riusato da**: CollocazioneForm, ContattoForm, filtri lista operatori, filtri lista reparti.

---

## Composable condivisi — Catalogo

### Collocazione: `src/core/composables/`

### 1. useSoggettoForm(options) — COMPLETATO

> **Nota**: il catalogo originale prevedeva composable separati `useSoggettoPF` e `useSoggettoPG`.
> L'implementazione reale li ha unificati in `useSoggettoForm` guidato dalla matrice DB.

```js
// State universale PF/PG/ENTE guidato dalla matrice tipi_soggetto_dettaglio
export function useSoggettoForm(options = {}) {
  const { tipoForzato = null } = options

  const form = reactive({
    tipo_soggetto_dettaglio_id: tipoForzato || null,
    cognome: '', nome: '', sesso: 'M', data_nascita: null, comune_nascita_id: null,
    ragione_sociale: '',
    codice_fiscale: '', partita_iva: ''
  })

  // Computed guidati dalla matrice DB
  const tipiSoggetto = useLookup(lookupTipiSoggettoDettaglio)
  const isPF = computed(...)           // natura_soggetto === 'PF'
  const showPartitaIva = computed(...) // piva_obbligatoria dal tipo corrente
  // ... matriceIndirizzi, indirizziObbligatori (watch su tipo)

  return { form, tipiSoggetto, tipoCorrente, isPF, showPartitaIva,
           showDatiSocietari, requireDatiSocietari, matriceIndirizzi,
           indirizziObbligatori, validate, reset }
}
```

**File**: `src/core/composables/useSoggettoForm.js`
**Riusato da**: ogni view che usa `SoggettoForm.vue`.

### 2. useContatto() — DA IMPLEMENTARE

```js
// State + validazione per contatto
export function useContatto(options = {}) {
  const { requireEmail = false } = options

  const form = reactive({
    nominativo: '',
    email: '',
    telefono: '',
    cellulare: '',
    pec: '',
    unita_organizzativa_id: null,
    tipo_contatto_id: null,
    note: ''
  })

  function validate() { /* nominativo non vuoto; email se requireEmail */ }
  function reset() { /* ripristina */ }

  return { form, errors, validate, reset }
}
```

### 3. useAuthUser() — COMPLETATO

```js
// State + validazione per credenziali
export function useAuthUser() {
  const form = reactive({
    username: '',
    email: '',
    password: '',
    password_confirm: ''
  })

  const passwordMatch = computed(() => form.password === form.password_confirm)
  function reset() { /* ripristina */ }

  return { form, passwordMatch, reset }
}
```

**File**: `src/core/composables/useAuthUser.js`

### 4. useLookup(fetchFn, options) — COMPLETATO

```js
// Cache generica per lookup (UO, qualifiche, tipi contatto, ecc.)
export function useLookup(fetchFn, options = {}) {
  const { immediate = false } = options
  const items = ref([])
  const loading = ref(false)

  async function load() {
    if (items.value.length > 0) return // gia' caricato
    loading.value = true
    items.value = await fetchFn()
    loading.value = false
  }

  if (immediate) load()

  return { items, loading, load, reload: () => { items.value = []; load() } }
}
```

**File**: `src/core/composables/useLookup.js`

### 5. useServerAutocomplete(searchFn, options) — COMPLETATO

```js
// Composable per autocomplete con ricerca server-side e debounce
export function useServerAutocomplete(searchFn, options = {}) {
  const { minLength = 2, debounceMs = 300 } = options
  const suggestions = ref([])
  const loading = ref(false)

  async function search(event) { /* debounce + chiamata API */ }

  return { suggestions, loading, search }
}
```

**File**: `src/core/composables/useServerAutocomplete.js`
**Riusato da**: `ComuneAutocomplete.vue`, `StradarioAutocomplete.vue`

**Riusato da**: `UOSelect`, `SoggettoPFForm` (tipi soggetto), `ContattoForm` (tipi contatto),
qualsiasi select che carica opzioni da API.

---

## Composizione nelle view di dominio

### Esempio 1 — UtenteDrawer.vue (refactored)

```vue
<template>
  <Drawer position="right" :style="{ width: DRAWER_WIDTH.COMPLEX }">
    <template v-if="isCreate">
      <h3>{{ $t('amm.nuovoOperatore') }}</h3>

      <!-- Building block riutilizzabili -->
      <SoggettoPFForm v-model="soggettoPF.form" />
      <ContattoForm v-model="contatto.form" :require-email="true" />
      <AuthUserForm v-model="authUser.form" />

      <!-- Specifico operatore -->
      <div class="field">
        <label>{{ $t('amm.unitaOrganizzativa') }}</label>
        <UOSelect v-model="unitaOrganizzativa" />
      </div>

      <Button :label="$t('amm.crea')" @click="handleCreate" />
    </template>
  </Drawer>
</template>

<script setup>
import SoggettoPFForm from '@/core/components/SoggettoPFForm.vue'
import ContattoForm from '@/core/components/ContattoForm.vue'
import AuthUserForm from '@/core/components/AuthUserForm.vue'
import UOSelect from '@/core/components/UOSelect.vue'
import { useSoggettoPF } from '@/core/composables/useSoggettoPF'
import { useContatto } from '@/core/composables/useContatto'
import { useAuthUser } from '@/core/composables/useAuthUser'

const soggettoPF = useSoggettoPF()
const contatto = useContatto({ requireEmail: true })
const authUser = useAuthUser()

async function handleCreate() {
  if (!soggettoPF.validate() || !contatto.validate() || !authUser.validate()) return
  // Payload unificato → API → backend chiama l'orchestratore
}
</script>
```

### Esempio 2 — ClienteDrawer.vue (futuro)

```vue
<template>
  <Drawer>
    <!-- Stessi building block, composizione diversa -->
    <SoggettoPFForm v-model="soggettoPF.form" v-if="isPF" />
    <SoggettoPGForm v-model="soggettoPG.form" v-if="isPG" />
    <DatiSocietariForm v-model="datiSocietari.form" v-if="requireDatiSocietari" />
    <ContattoForm v-model="contatto.form" />
    <IndirizzoForm v-model="indirizzo.form" :tipo-soggetto-dettaglio-id="tipoDettaglioId" />

    <!-- Specifico cliente -->
    <ClienteDatiForm v-model="datiCliente" />
  </Drawer>
</template>
```

### Esempio 3 — ProfiloUtente (readonly)

```vue
<template>
  <div>
    <!-- Stessi componenti in modalita' readonly -->
    <SoggettoPFForm :model-value="profilo.soggetto" :readonly="true" />
    <ContattoForm :model-value="profilo.contatto" :readonly="true" />
  </div>
</template>
```

---

## Matrice riutilizzo

Mappa di quali componenti servono per ogni caso d'uso:

| Caso d'uso                | SoggettoPF | SoggettoPG | Contatto | Indirizzo | AuthUser | DatiSocietari | UOSelect |
| ------------------------- | :--------: | :--------: | :------: | :-------: | :------: | :-----------: | :------: |
| Crea operatore            |     x      |            |    x     |           |    x     |               |    x     |
| Crea admin                |     x      |            |    x     |           |    x     |               |    x     |
| Crea cliente PF           |     x      |            |    x     |     x     |          |               |          |
| Crea cliente PG           |            |     x      |    x     |     x     |          |       x       |          |
| Crea fornitore PF         |     x      |            |    x     |     x     |          |               |          |
| Crea fornitore PG         |            |     x      |    x     |     x     |          |       x       |          |
| Profilo utente (readonly) |     x      |            |    x     |           |          |               |          |
| Scheda soggetto (edit)    |    x/PG    |    x/PG    |    x     |     x     |          |      x?       |          |
| Gestione contatti         |            |            |    x     |           |          |               |          |

---

## Struttura cartelle risultante

```
frontend/src/
├── core/
│   ├── components/
│   │   ├── (esistenti: AppLayout, Sidebar, ecc.)
│   │   ├── SoggettoForm.vue            # COMPLETATO — form universale PF/PG/ENTE
│   │   ├── AuthUserForm.vue            # COMPLETATO — form credenziali
│   │   ├── ComuneAutocomplete.vue      # COMPLETATO — autocomplete comuni
│   │   ├── StradarioAutocomplete.vue   # COMPLETATO — autocomplete stradario
│   │   ├── ContattoForm.vue            # FUTURO — form contatto
│   │   ├── IndirizzoForm.vue           # FUTURO — form indirizzo
│   │   ├── DatiSocietariForm.vue       # FUTURO — form dati camerali
│   │   └── UOSelect.vue               # FUTURO — select unita' organizzativa
│   ├── composables/
│   │   ├── (esistenti: useNotify, useApiHandler, ecc.)
│   │   ├── useSoggettoForm.js          # COMPLETATO — state universale PF/PG/ENTE
│   │   ├── useAuthUser.js              # COMPLETATO — state credenziali
│   │   ├── useLookup.js                # COMPLETATO — cache generica per select
│   │   ├── useServerAutocomplete.js    # COMPLETATO — ricerca server-side con debounce
│   │   └── useContatto.js              # FUTURO — state contatto
│   ├── apiCore.js                      # COMPLETATO — API lookup/search core
│   └── api/
│       └── anagrafiche.js              # FUTURO — API soggetti, contatti, indirizzi
├── amministrazione/
│   ├── components/
│   │   ├── UtenteDrawer.vue            # COMPLETATO — refactored con building block
│   │   ├── UtentePermessiTab.vue       # COMPLETATO — usa useLookup locale
│   │   └── RepartoProfiloEditor.vue    # Invariato
│   └── views/
│       └── ...
├── assets/
│   └── main.css                        # COMPLETATO — CSS utility classes globali
```

---

## Regole di implementazione

### R1 — Nessuna logica di business nei componenti form

I componenti atomici fanno solo:

* Rendere i campi con binding v-model
* Validazione UX locale (campo vuoto, formato email, lunghezza CF)
* Emettere eventi

Non chiamano API, non gestiscono transazioni, non conoscono il contesto d'uso.

### R2 — Il composable gestisce lo state, il componente lo rende

Il composable (`useSoggettoPF`) possiede il `reactive()` e la funzione `validate()`.
Il componente (`SoggettoPFForm`) riceve il form via `v-model` e mostra i campi.
La view (`UtenteDrawer`) li compone e gestisce il submit.

### R3 — Il backend assembla, il frontend compone

Il frontend manda un **payload unico** al backend (es. `POST /api/v1/amm-software/operatori/`).
Il backend (service layer) scompone il payload e chiama i building block SQL nella sequenza corretta.
Il frontend non chiama mai i building block singolarmente — l'orchestrazione e' responsabilita' del backend.

### R4 — Lookup via useLookup, mai duplicati

Ogni select che carica opzioni da API usa `useLookup(fetchFn)`.
Le opzioni vengono caricate una volta e cachate nel composable.
Non duplicare le stesse chiamate API in componenti diversi della stessa view.

### R5 — i18n sempre, stringhe hardcoded mai

Tutti i label dei form usano `$t('chiave')`.
Le chiavi per i componenti core vanno nel namespace `common` dei file locale:

```json
{
  "common": {
    "cognome": "Cognome",
    "nome": "Nome",
    "codiceFiscale": "Codice Fiscale",
    "email": "Email",
    "telefono": "Telefono"
  }
}
```

---

## Priorita' di implementazione

| Fase | Cosa                                                   | Perche'                                                   |
| ---- | ------------------------------------------------------ | --------------------------------------------------------- |
| 1    | `useLookup`, `UOSelect`                                | Base per tutti i select, dipendenza trasversale           |
| 2    | `useSoggettoPF` + `SoggettoPFForm`                     | Nucleo identita' PF, riusato ovunque                      |
| 3    | `useContatto` + `ContattoForm`                         | Obbligatorio per ogni creazione soggetto (guard DEFERRED) |
| 4    | `useAuthUser` + `AuthUserForm`                         | Necessario per operatori e admin                          |
| 5    | Refactor `UtenteDrawer.vue`                            | Primo consumer reale dei building block                   |
| 6    | `SoggettoPGForm`, `DatiSocietariForm`, `IndirizzoForm` | Per i domini successivi (clienti, fornitori)              |

---

## Note

* I componenti atomici NON hanno dipendenze tra loro: `SoggettoForm` non importa `ContattoForm`.
  La composizione avviene solo nella view/drawer di dominio.
* Il composable gestisce lo state (`reactive`), il componente lo rende via props.
  La view compone i building block e gestisce il submit.
* I componenti esistenti in `amministrazione/components/` verranno refactored gradualmente:
  prima si creano i building block core, poi si sostituiscono le sezioni monolitiche.

---

## CSS utility classes — Standard globale (COMPLETATO)

> Aggiunto Sprint 3 (2026-03-14).
> File: `src/assets/main.css`

Classi CSS globali usate da tutte le pagine e drawer per garantire uniformita'.
Singola source of truth — non duplicare stili in scoped dei componenti.

| Classe                | Scopo                                                          |
| --------------------- | -------------------------------------------------------------- |
| `.app-page`           | Wrapper root di ogni view (flex column, overflow hidden)       |
| `.app-page-toolbar`   | Barra filtri + azioni sopra la DataTable                       |
| `.app-page-filters`   | Gruppo filtri con flex-wrap dentro la toolbar                  |
| `.app-page-action`    | Pulsanti azione (su mobile nasconde label, mostra solo icona)  |
| `.app-datatable`      | DataTable compatta con font-size/padding da variabili CSS      |
| `.form-grid`          | Layout verticale per form (flex column, gap 0.75rem)           |
| `.form-field`         | Singolo campo form (flex column label+input, gap 0.25rem)      |
| `.app-drawer-content` | Layout standard contenuto drawer (flex column, gap, font-size) |

**Responsive**: `@media (max-width: 1023px)` nasconde `.app-page-action .p-button-label`
e riduce padding — il pulsante diventa solo icona + tooltip via `v-tooltip`.

---

## Sprint 3 — Piano di implementazione dettagliato

> Data: 2026-03-13 | Aggiornato: 2026-03-14
> Stato: **PARZIALMENTE COMPLETATO** (FE-1..FE-9, FE-11 completati; FE-10 da verificare)
> Prerequisiti globali: Sprint 2 completato (52 test OK, building block backend/DB)
> Guida di riferimento: [Gestione degli indirizzi](/guide/gestione-degli-indirizzi)

### Obiettivi Sprint 3

1. **SoggettoForm universale** — un unico componente Vue che si adatta a PF/PG/ENTE guidato dalla matrice `tipi_soggetto_dettaglio`
2. **Refactoring lookup** — eliminare i lookup duplicati da `amm-software`, usare `core/lookup-codici` per tabelle config standard
3. **Gestione indirizzi completa** — risolvere il trigger DEFERRED `E_INDIRIZZO_OBBLIGATORIO_MANCANTE` con supporto a tutta la catena indirizzi normalizzati
4. **Autocomplete comuni e stradario** — ricerca server-side su comuni (8098 record) e stradario

---

### Matrice dati dal DB (riferimento per lo sviluppo)

**Tipi soggetto dettaglio:**

| id  | codice | natura | CF obbl. | PIVA obbl. | Dati societari | Campi visibili                                                    |
| --- | ------ | ------ | :------: | :--------: | -------------- | ----------------------------------------------------------------- |
| 1   | PR     | PF     |    si    |     no     | NONE           | cognome, nome, sesso, data_nascita, comune_nascita, CF            |
| 2   | DI     | PF     |    si    |     si     | OPTIONAL       | cognome, nome, sesso, data_nascita, comune_nascita, CF, **P.IVA** |
| 3   | SC     | PG     |    si    |     si     | REQUIRED       | ragione_sociale, CF, P.IVA, **dati societari obbl.**              |
| 4   | SP     | PG     |    si    |     si     | OPTIONAL       | ragione_sociale, CF, P.IVA, dati societari opz.                   |
| 5   | ENC    | ENTE   |    si    |     si     | OPTIONAL       | ragione_sociale, CF, P.IVA, dati societari opz.                   |

**Indirizzi obbligatori per tipo:**

| Tipo               | Obbligatori                               | Opzionali ammessi                                                                                                                        |
| ------------------ | ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| PR (Privato)       | RESID, DOM-FISC, FATT (fallback→DOM-FISC) | CONS (fallback→RESID), POSTALE (fallback→RESID), SPED                                                                                    |
| DI (Ditta Ind.)    | DOM-FISC                                  | RESID, SEDE-LEG (fallback→DOM-FISC), SEDE-OP, CONS, FATT (fallback→DOM-FISC), POSTALE (fallback→SEDE-LEG), FORN (fallback→SEDE-OP), SPED |
| SC (Soc. Capitali) | SEDE-LEG                                  | DOM-FISC (fallback→SEDE-LEG), SEDE-OP, CONS, FATT (fallback→SEDE-LEG), POSTALE (fallback→SEDE-LEG), FORN (fallback→SEDE-OP), SPED        |
| SP (Soc. Persone)  | SEDE-LEG                                  | DOM-FISC (fallback→SEDE-LEG), SEDE-OP, CONS, FATT (fallback→SEDE-LEG), POSTALE (fallback→SEDE-LEG), FORN (fallback→SEDE-OP), SPED        |
| ENC (Ente)         | SEDE-LEG                                  | DOM-FISC (fallback→SEDE-LEG), SEDE-OP, CONS, FATT (fallback→SEDE-LEG), POSTALE (fallback→SEDE-LEG), FORN (fallback→SEDE-OP), SPED        |

**Tabella comuni**: `config.comuni` — 8098 record (id, descrizione, provincia_id).

**Tabella indirizzi**: `anagrafiche.indirizzi_soggetti` — soggetto_id, tipo_indirizzo_id, indirizzo_dettaglio_id (normalizzato) o indirizzo_libero (eccezione), stato_id, ecc.

---

### Architettura indirizzi — catena completa

> Riferimento: [Guida Gestione degli Indirizzi](/guide/gestione-degli-indirizzi)

L'indirizzo in ZeroERP **non e' un campo di testo**: e' un dato strutturato normalizzato.
La modalita' **normalizzata** (via `indirizzo_dettaglio_id`) e' **sempre preferita**.
L'`indirizzo_libero` e' riservato a eccezioni (migrazioni, indirizzi esteri non normalizzabili).

**Catena di normalizzazione (dal basso verso l'alto):**

```
config.toponomastica          (Via, Piazza, Corso, Largo...)
       ↓
config.stradario_generale     (toponimo + denominazione via)
       ↓
config.stradario              (via locale = stradario_generale + comune + CAP)
       ↓
anagrafiche.indirizzi_dettaglio  (civico normalizzato: stradario + civico + estensione + palazzina + scala + piano + interno)
       ↓
anagrafiche.indirizzi_soggetti   (soggetto_id + tipo_indirizzo_id + indirizzo_dettaglio_id)
```

**Gerarchia geografica:**
```
config.stati → config.regioni → config.province → config.comuni → config.codici_postali
                                                        ↓
                                                  config.stradario
```

**Regole chiave (dalla guida):**
- **R1 — XOR**: o normalizzato (`indirizzo_dettaglio_id`) o libero (`indirizzo_libero`), mai entrambi
- **R2 — Unicita'**: un solo indirizzo per tipo per soggetto (`UNIQUE soggetto_id, tipo_indirizzo_id`)
- **R3 — Completezza libero**: se libero, obbligatori `indirizzo_libero` + `stato_id` + (`comune_id` + `codice_postale_id`) oppure (`locality` + `postal_box`)
- **R6 — Guard tipo**: trigger verifica tipo_indirizzo contro matrice `config.tipi_soggetto_dettaglio_tipi_indirizzo`
- **R7 — Unicita' civico**: vincolo `uq_indirizzi_dettaglio_norm` su (stradario_id, civico, estensione, palazzina, scala, piano, interno)

**Funzioni di ricerca gia' esistenti:**
- `anagrafiche.fn_search_indirizzi_dettaglio(...)` — ricerca per stradario+civico o fuzzy su indirizzo_normalizzato
- `script.fn_get_indirizzo(p_soggetto_ruolo_id, p_tipo_codice)` — risoluzione master/fallback
- `script.fn_get_indirizzo_by_soggetto(p_soggetto_id, p_tipo_codice)` — layer soggetto con fallback

---

### TRACK DB (competenza server DB)

> **Nota**: DB-1 e' stato riscritto completamente rispetto alla versione iniziale.
> La gestione indirizzi richiede building block dedicati per tutta la catena di normalizzazione,
> non un semplice parametro JSONB con `indirizzo_libero`.

#### DB-1 — Building block `fn_get_or_create_indirizzo_dettaglio`

**Prerequisiti**: nessuno
**Schema**: `anagrafiche`
**Tipo**: building block riusabile

Funzione upsert: cerca un civico esistente per chiave naturale, se non esiste lo crea.
Il vincolo `uq_indirizzi_dettaglio_norm` garantisce la deduplicazione.

**Firma proposta:**
```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_get_or_create_indirizzo_dettaglio(
    p_stradario_id        config.stradario.id%TYPE,
    p_civico              anagrafiche.indirizzi_dettaglio.civico%TYPE         DEFAULT NULL,
    p_estensione_civico   anagrafiche.indirizzi_dettaglio.estensione_civico%TYPE DEFAULT NULL,
    p_palazzina           anagrafiche.indirizzi_dettaglio.palazzina%TYPE      DEFAULT NULL,
    p_scala               anagrafiche.indirizzi_dettaglio.scala%TYPE          DEFAULT NULL,
    p_piano               anagrafiche.indirizzi_dettaglio.piano%TYPE          DEFAULT NULL,
    p_interno             anagrafiche.indirizzi_dettaglio.interno%TYPE        DEFAULT NULL
)
RETURNS anagrafiche.indirizzi_dettaglio.id%TYPE
```

**Logica:**
1. Guard: `p_stradario_id` obbligatorio, verificare che esista e sia attivo in `config.stradario`
2. Cercare per chiave naturale (stradario_id, civico, estensione, palazzina, scala, piano, interno) con COALESCE su nullable
3. Se trovato → RETURN id esistente
4. Se non trovato → INSERT + RETURNING id (il trigger `trgfn_indirizzi_dettaglio_normalize` calcola `indirizzo_normalizzato`, `via_norm`, `civico_norm`)
5. Gestire `unique_violation` (race condition) con retry

**Nota**: questa funzione NON gestisce la creazione dello stradario. Se lo stradario non esiste, il chiamante (o il frontend) deve prima crearlo o selezionarlo. Vedi DB-1b.

#### DB-1b — `fn_get_or_create_stradario`: NON SERVE (stradario chiuso)

**Stato**: CHIUSO — nessun changeset necessario.

Lo stradario e' **chiuso**: la gestione di `config.toponomastica`, `config.stradario_generale`
e `config.stradario` e' riservata all'admin. L'utente operativo seleziona da stradari esistenti
tramite autocomplete (vedi DB-7). Non serve nessuna funzione di creazione on-the-fly.

#### DB-2 — Building block `fn_crea_indirizzo_soggetto`

**Prerequisiti**: DB-1 (se normalizzato) oppure nessuno (se libero)
**Schema**: `anagrafiche`
**Tipo**: building block riusabile

Crea un record in `anagrafiche.indirizzi_soggetti`. Supporta entrambe le modalita':
- **Normalizzata** (standard): riceve `p_indirizzo_dettaglio_id`
- **Libera** (eccezione): riceve `p_indirizzo_libero` + campi geografici

**Firma proposta:**
```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_crea_indirizzo_soggetto(
    -- Obbligatori
    p_soggetto_id             anagrafiche.soggetti.id%TYPE,
    p_tipo_indirizzo_codice   config.tipi_indirizzi.codice_interno%TYPE,
    -- Modalita' normalizzata (preferita)
    p_indirizzo_dettaglio_id  anagrafiche.indirizzi_dettaglio.id%TYPE   DEFAULT NULL,
    -- Modalita' libera (eccezione)
    p_indirizzo_libero        text                                     DEFAULT NULL,
    p_stato_id                config.stati.id%TYPE                     DEFAULT NULL,
    p_comune_id               config.comuni.id%TYPE                    DEFAULT NULL,
    p_codice_postale_id       config.codici_postali.id%TYPE            DEFAULT NULL
)
RETURNS anagrafiche.indirizzi_soggetti.id%TYPE
```

**Logica:**
1. Guard XOR: o `p_indirizzo_dettaglio_id` o `p_indirizzo_libero`, mai entrambi (R1)
2. Lookup `tipo_indirizzo_id` da `p_tipo_indirizzo_codice` in `config.tipi_indirizzi`
3. Se modalita' libera: guard completezza (R3) — `stato_id` + (`comune_id` + `codice_postale_id`)
4. INSERT in `anagrafiche.indirizzi_soggetti`
5. I trigger si occupano di: guard tipo (R6), normalizzazione (R8), sync geoloc, audit, tx_id

**Nota**: il trigger `trgfn_indirizzi_soggetti_guard_tipo_indirizzo` verifica automaticamente
che il tipo indirizzo sia ammesso per il tipo_soggetto_dettaglio del soggetto (matrice config).

#### DB-3 — Aggiornare `fn_crea_soggetto_pf`: aggiungere `p_comune_nascita_id`

**Prerequisiti**: nessuno
**File**: nuovo changeset per `anagrafiche.fn_crea_soggetto_pf` (runOnChange)

* Nuovo parametro `p_comune_nascita_id anagrafiche.soggetti.comune_id%TYPE DEFAULT NULL`
* Aggiungere `comune_id` nell'INSERT di `anagrafiche.soggetti` (colonna gia' esistente, FK `fk_comuni_config`)
* La FK verifica automaticamente l'esistenza del comune — nessun guard aggiuntivo necessario
* Propagare il parametro anche in `fn_crea_operatore`

#### DB-4 — `risorse_umane.valido_dal`: nessun intervento (opzione B)

**Stato**: CHIUSO — nessun changeset necessario.

La funzione `fn_crea_risorsa_umana` gestisce gia' `p_valido_dal DEFAULT CURRENT_DATE` nel parametro.
Non si aggiunge DEFAULT sulla colonna: tutti gli INSERT passano dalla funzione building block.

#### DB-5 — Aggiornare `fn_crea_operatore`: indirizzi tramite building block

**Prerequisiti**: DB-1, DB-2, DB-3
**File**: nuovo changeset per `anagrafiche.fn_crea_operatore` (runOnChange)

Aggiungere alla firma dell'orchestratore i parametri per gli indirizzi obbligatori PR:

**Nuovi parametri (modalita' normalizzata):**
```sql
-- Indirizzo residenza (RESID) — normalizzato
p_indirizzo_resid_dettaglio_id   anagrafiche.indirizzi_dettaglio.id%TYPE DEFAULT NULL,
-- Indirizzo domicilio fiscale (DOM-FISC) — se NULL, usa stesso di RESID
p_indirizzo_domfisc_dettaglio_id anagrafiche.indirizzi_dettaglio.id%TYPE DEFAULT NULL,
-- Comune nascita
p_comune_nascita_id              anagrafiche.soggetti.comune_id%TYPE     DEFAULT NULL
```

**Logica aggiuntiva nel body:**
1. Dopo `fn_crea_soggetto_pf` (che ora accetta `p_comune_nascita_id`)
2. Se `p_indirizzo_resid_dettaglio_id` IS NOT NULL:
   - `PERFORM anagrafiche.fn_crea_indirizzo_soggetto(v_soggetto_id, 'RESID', p_indirizzo_resid_dettaglio_id)`
   - Se `p_indirizzo_domfisc_dettaglio_id` IS NULL → usa lo stesso di RESID per DOM-FISC
   - `PERFORM anagrafiche.fn_crea_indirizzo_soggetto(v_soggetto_id, 'DOMFISC', COALESCE(p_indirizzo_domfisc_dettaglio_id, p_indirizzo_resid_dettaglio_id))`
3. Se `p_indirizzo_resid_dettaglio_id` IS NULL → nessun indirizzo creato (il trigger DEFERRED potrebbe
   bloccare al COMMIT se la matrice richiede RESID per PR — questo e' voluto: il chiamante deve fornire
   gli indirizzi obbligatori)

**Nota sul trigger DEFERRED**: `trgfn_soggetti_guard_indirizzi_required` scatta al COMMIT.
Se gli indirizzi obbligatori non sono presenti, il COMMIT fallisce con errore chiaro.
L'orchestratore non deve duplicare questo check — il trigger fa da rete di sicurezza.

#### DB-6 — Aggiornare test pgTAP

**Prerequisiti**: DB-1..DB-5
**File**: aggiornare `db/pgtap/anagrafiche/test-fn-crea-operatore.sql`

Nuovi test:
* Creazione operatore con indirizzo normalizzato (RESID + DOM-FISC) — successo
* Creazione operatore con solo RESID (DOM-FISC copiato da RESID) — successo
* Creazione operatore senza indirizzo — errore trigger DEFERRED (se matrice lo richiede)
* Verifica che `indirizzi_soggetti` contenga i record corretti dopo creazione
* Verifica `comune_nascita_id` passato correttamente a `soggetti.comune_id`
* Test building block `fn_get_or_create_indirizzo_dettaglio`: get esistente, create nuovo, race condition
* Test building block `fn_crea_indirizzo_soggetto`: normalizzato OK, libero OK, XOR violation

#### DB-7 — Funzione `fn_search_stradario` (ricerca vie per autocomplete)

**Prerequisiti**: nessuno
**Schema**: `script` (funzione di lettura cross-dominio, come le altre `fn_search_*`)
**Tipo**: funzione STABLE di lettura ottimizzata

Il frontend cerca VIE (stradario) per comune, non civici. L'utente:
1. Seleziona un comune (autocomplete comuni, BE-3)
2. Cerca una via nel comune selezionato (autocomplete stradario, questa funzione)
3. Inserisce il civico manualmente (campo numerico + dettagli)
4. Il backend chiama `fn_get_or_create_indirizzo_dettaglio` (DB-1) per ottenere/creare il civico

**Firma proposta:**
```sql
CREATE OR REPLACE FUNCTION script.fn_search_stradario(
    p_comune_id    config.comuni.id%TYPE        DEFAULT NULL,
    p_search       text                         DEFAULT NULL,
    p_limit        integer                      DEFAULT 30
)
RETURNS TABLE (
    stradario_id           config.stradario.id%TYPE,
    toponimo               config.toponomastica.descrizione%TYPE,
    denominazione          config.stradario_generale.denominazione_norm%TYPE,
    via_completa           text,    -- es. "Via Roma"
    comune_id              config.comuni.id%TYPE,
    comune_descrizione     config.comuni.denominazione%TYPE,
    provincia_sigla        config.province.sigla%TYPE,
    codice_postale_id      config.codici_postali.id%TYPE,
    cap                    config.codici_postali.cap%TYPE
)
LANGUAGE plpgsql
STABLE
PARALLEL SAFE
```

**Logica:**
1. Guard: almeno `p_comune_id` o `p_search` deve essere valorizzato
2. Se `p_comune_id` fornito: filtra per comune (caso principale — autocomplete dopo selezione comune)
3. Se `p_search` fornito: ricerca ILIKE su `toponimo || ' ' || denominazione_norm`
4. JOIN: `stradario` → `stradario_generale` → `toponomastica` + `comuni` → `province` + `codici_postali`
5. Filtro `stradario.attivo = true` (se presente), ORDER BY `via_completa`, LIMIT `p_limit`
6. Campo calcolato `via_completa` = `toponimo || ' ' || denominazione_norm` (es. "Via Roma", "Piazza Garibaldi")

**Nota sulle performance**: con `p_comune_id` + `p_search` il numero di righe e' contenuto
(un comune ha mediamente poche centinaia di vie). Se necessario, aggiungere indice trigram
su `stradario_generale.denominazione_norm`.

**Pattern coerente con il progetto**: stessa struttura di `fn_search_soggetti_universale`
e `fn_search_indirizzi_dettaglio` — funzione STABLE in `script`, usata dal backend come entry point.

---

### TRACK BACKEND

#### BE-1 — Refactoring lookup: eliminare duplicati da `amm-software`

**Stato**: PARZIALMENTE COMPLETATO (2026-03-13)

**Risultato verifica compatibilita'**:

| Tabella | Whitelist | Struttura compatibile | Migrata | Note |
|---------|:---------:|:--------------------:|:-------:|------|
| `config.qualifiche` | si | si (id/codice/descrizione) | **SI** | Rimossa LookupQualificheView + list_qualifiche() |
| `config.unita_organizzative` | si | **NO** — `nome` ≠ `descrizione`, serve `parent_id` | NO | Serve per gerarchia UI permessi |
| `config.aree_funzionali` | no | **NO** — serve `ordinamento` | NO | Usata da override aree/profili reparto |
| `config.azioni_processo` | no | **NO** — JOIN complessa, serve `pericolosa/area_id/area_codice` | NO | Usata da override azioni |
| `anagrafiche.emittenti_fiscali` | no | **NO** — `denominazione` ≠ `descrizione`, serve `partita_iva` | NO | Usata da scope emittenti |

Le 4 lookup non migrate restano in `amm-software` perche' servono campi extra per la UI permessi.
Saranno rivisitate quando i permessi avranno una propria app.

#### BE-2 — Endpoint matrice indirizzi per tipo soggetto

**Stato**: COMPLETATO (2026-03-13)
**File**: `apps/core/api/views_lookup.py` → `LookupMatriceIndirizziView`
**File**: `apps/core/db/lookup_repository.py` → `list_matrice_indirizzi()`

```
GET /api/v1/core/lookup/tipi-soggetto-dettaglio/<id>/indirizzi/
→ { "data": { "results": [{ "tipo_indirizzo_id": 1, "codice": "RESID", "descrizione": "Residenza",
     "obbligatorio": true, "fallback_tipo_indirizzo_id": null, "fallback_codice": null }, ...] } }
```

#### BE-3 — Endpoint autocomplete comuni

**Stato**: COMPLETATO (2026-03-13)
**File**: `apps/core/api/views_lookup.py` → `LookupComuniView`
**File**: `apps/core/db/lookup_repository.py` → `search_comuni()`

```
GET /api/v1/core/lookup/comuni/?search=ROM&limit=20
→ { "data": { "count": 5, "results": [{ "id": 4517, "descrizione": "ROMA", "provincia_sigla": "RM" }, ...] } }
```

* `is_search_endpoint = True` per throttling DRF
* Permission: `ZeroERPPermission` (qualsiasi utente autenticato)

#### BE-4 — Endpoint lookup tipi soggetto dettaglio

**Stato**: COMPLETATO (2026-03-13)
**File**: `apps/core/api/views_lookup.py` → `LookupTipiSoggettoDettaglioView`
**File**: `apps/core/db/lookup_repository.py` → `list_tipi_soggetto_dettaglio()`

```
GET /api/v1/core/lookup/tipi-soggetto-dettaglio/
→ { "data": { "results": [{ "id": 1, "codice_interno": "PR", "descrizione": "...", "natura_soggetto": "PF",
     "cf_obbligatorio": true, "piva_obbligatoria": false, "dati_societari_policy": "NONE" }, ...] } }
```

#### BE-5 — Aggiornare POST creazione operatore

**Stato**: COMPLETATO (2026-03-13)
**File**: `apps/amm_software/api/views.py`, `apps/amm_software/db/amm_software_repository.py`

Nuovi parametri nel payload POST (tutti opzionali, retrocompatibili):
* `comune_nascita_id` (int) — FK verso `config.comuni`
* `indirizzo_resid_dettaglio_id` (int) — FK verso `anagrafiche.indirizzi_dettaglio` (residenza)
* `indirizzo_domfisc_dettaglio_id` (int) — FK verso `anagrafiche.indirizzi_dettaglio` (domicilio fiscale)

Passati a `fn_crea_operatore` come `p_comune_nascita_id`, `p_indirizzo_resid_dettaglio_id`, `p_indirizzo_domfisc_dettaglio_id`.
Test aggiornati: 9 test OK (2 nuovi per Sprint 3 params + retrocompatibilita').

#### BE-6 — Test

**Stato**: COMPLETATO per BE-2/BE-3/BE-4/BE-5/BE-7 (2026-03-13)
**File**: `apps/core/tests/db/test_lookup_repository.py` — 11 test OK (mock cursor, +3 stradario)
**File**: `apps/amm_software/tests/api/test_crea_utente.py` — 9 test OK (+2 Sprint 3)
**Risultato**: 275 test OK (core + amm_software), 0 failures
**Smoke test**: aggiornato con 4 nuovi endpoint (test 13/14/15/16 — incluso stradario)

#### BE-7 — Endpoint search stradario

**Stato**: COMPLETATO (2026-03-13)
**File**: `apps/core/api/views_lookup.py` → `SearchStradarioView`
**File**: `apps/core/db/lookup_repository.py` → `search_stradario()`

```
GET /api/v1/core/search/stradario/?comune_id=4517&search=via&limit=30
→ { "data": { "results": [{ "stradario_id": 101, "toponimo": "Via", "denominazione": "Roma",
     "via_completa": "Via Roma", "comune_id": 4517, "comune_descrizione": "ROMA",
     "provincia_sigla": "RM", "codice_postale_id": 50, "cap": "00100" }, ...] } }
```

* `is_search_endpoint = True` per throttling DRF
* Chiama `script.fn_search_stradario(p_comune_id, p_search, p_limit)`
* Test: 3 test unitari in `test_lookup_repository.py` (with_results, empty, params)

---

### TRACK FRONTEND

#### FE-1 — API client core per lookup

**Stato**: COMPLETATO (2026-03-14)
**File**: `src/core/apiCore.js`

Funzioni implementate:
* `lookupCodici(rel, params)` → chiama `GET /api/v1/core/lookup-codici/?rel=...`
* `lookupTipiSoggettoDettaglio()` → chiama BE-4
* `lookupMatriceIndirizzi(tipoSoggettoDettaglioId)` → chiama BE-2
* `searchComuni(search, limit)` → chiama BE-3
* `searchStradario(comuneId, search, limit)` → chiama BE-7

#### FE-2 — Composable `useLookup`

**Stato**: COMPLETATO (2026-03-14)
**File**: `src/core/composables/useLookup.js`

Cache generica per lookup API con `items`, `loading`, `load()`, `reload()`.
Opzione `immediate: true` per caricare al mount.

#### FE-3 — Refactoring store `utenti.js` e API `amministrazione.js`

**Stato**: PARZIALMENTE COMPLETATO (2026-03-14)
**File**: `src/amministrazione/stores/utenti.js`, `src/amministrazione/api/amministrazione.js`

Completato:

* Rimossa `listQualifiche()` da `amministrazione.js` (migrata a `lookupCodici('config.qualifiche')`)
* Rimossi 5 lookup ref e fetch methods da `utenti.js` (qualifiche, UO, aree, azioni, emittenti)
* Componenti usano `useLookup` direttamente

Non migrato (restano in `amm-software`):

* `listUnitaOrganizzative` — serve campo `nome` (non `descrizione`) + `parent_id` per gerarchia
* `listAreeFunzionali` — serve campo `ordinamento`
* `listAzioniProcesso` — JOIN complessa con `pericolosa`, `area_id`, `area_codice`
* `listEmittentiFiscali` — serve `denominazione` + `partita_iva`

#### FE-4 — Composable `useSoggettoForm`

**Stato**: COMPLETATO (2026-03-14)
**File**: `src/core/composables/useSoggettoForm.js`

Composable universale PF/PG/ENTE guidato dalla matrice DB `tipi_soggetto_dettaglio`.

Differenze dall'implementazione rispetto al piano originale:

* `email` **rimossa** dal form — vive in `useAuthUser` (separazione building block)
* `indirizzo` **non incluso** nel form — sara' gestito da `IndirizzoForm` futuro
* Props passate al componente (non v-model bidirezionale): `form`, `tipiSoggetto`, `isPF`, `showPartitaIva`

#### FE-5 — Componente `SoggettoForm.vue`

**Stato**: COMPLETATO (2026-03-14)
**File**: `src/core/components/SoggettoForm.vue`

Form universale che si adatta al tipo selezionato. Usa classi CSS globali `form-grid` e `form-field`
da `main.css`. Include `ComuneAutocomplete` per comune di nascita.

#### FE-6 — Componente `ComuneAutocomplete.vue`

**Stato**: COMPLETATO (2026-03-14)
**File**: `src/core/components/ComuneAutocomplete.vue`

* PrimeVue `AutoComplete` con `useServerAutocomplete` + `searchComuni(query)`
* Mostra `descrizione` + provincia sigla
* Emette `id` via v-model

#### FE-6b — Componente `StradarioAutocomplete.vue`

**Stato**: COMPLETATO (2026-03-14)
**File**: `src/core/components/StradarioAutocomplete.vue`

* PrimeVue `AutoComplete` con `useServerAutocomplete` + `searchStradario(comuneId, query)`
* Mostra `via_completa` + CAP
* Richiede `comuneId` prop per filtrare per comune

#### FE-7 — Composable `useAuthUser` + componente `AuthUserForm.vue`

**Stato**: COMPLETATO (2026-03-14)
**File**: `src/core/composables/useAuthUser.js`, `src/core/components/AuthUserForm.vue`

Composable con `form` reactive (username, email, password, password_confirm),
`passwordMatch` computed, `reset()`. Componente con props `form` e `passwordMatch`.

#### FE-8 — Refactor `UtenteDrawer.vue`

**Stato**: COMPLETATO (2026-03-14)
**File**: `src/amministrazione/components/UtenteDrawer.vue`

Refactored con building block:

* Crea mode: `SoggettoForm` (tipoForzato=1) + `AuthUserForm` + sezione collocazione (inline)
* Edit mode: `TabView` con tab Dati (form-grid/form-field) + tab Permessi
* Lookup via `useLookup`: qualifiche da `lookupCodici('config.qualifiche')`, UO da `listUnitaOrganizzative`
* Wrapper `app-drawer-content` per stile uniforme

#### FE-9 — Aggiornare `UtentiListView.vue` e `UtentePermessiTab.vue`

**Stato**: COMPLETATO (2026-03-14)
**File**: `src/amministrazione/views/UtentiListView.vue`, `src/amministrazione/components/UtentePermessiTab.vue`

* `UtentiListView`: usa `useLookup(listUnitaOrganizzative)` per filtro UO, classi CSS `app-page`,
  `app-datatable`, `app-page-action` con `v-tooltip` per responsive
* `UtentePermessiTab`: 3 lookup locali con `useLookup` (aree, azioni, emittenti)
* Rimossi tutti i riferimenti a `store.unitaOrganizzative` e altri lookup centralizzati

#### FE-10 — i18n

**Stato**: DA VERIFICARE
**File**: `src/locales/it.json`, `src/locales/en.json`

Chiavi nel namespace `common` per i campi dei building block:
* `common.cognome`, `common.nome`, `common.codice_fiscale`, `common.partita_iva`
* `common.ragione_sociale`, `common.sesso`, `common.data_nascita`, `common.comune_nascita`
* `common.indirizzo`, `common.comune`, `common.cap`, `common.provincia`
* `common.email`, `common.telefono`, `common.pec`
* `common.username`, `common.password`, `common.password_confirm`
* `common.tipo_soggetto`, `common.select_tipo_soggetto`

#### FE-11 — Build e verifica

**Stato**: COMPLETATO (2026-03-14)

* `vite build` — zero errori
* 275 test backend OK (44 amm_software + 231 core)
* Test manuale pendente: creare operatore con tutti i campi da UI

---

### Diagramma dipendenze

```text
DB TRACK                              BACKEND TRACK                    FRONTEND TRACK
────────                              ─────────────                    ──────────────

DB-4 (valido_dal) ─ CHIUSO            BE-1 (refactor lookup)  ─────→  FE-3 (refactor store)
                                           │                               │
DB-3 (comune_nascita fn_crea_soggetto_pf)  BE-2 (matrice indirizzi)     FE-1 (API client)
     │                                     BE-3 (autocomplete comuni)      │
DB-1 (fn_get_or_create_indirizzo_dettaglio)BE-4 (tipi soggetto dett.)  FE-2 (useLookup)
     │                                          │                          │
DB-2 (fn_crea_indirizzo_soggetto) ←── DB-1 BE-7 (search stradario)    FE-4 (useSoggettoForm)
     │                                          │                          │
DB-7 (search stradario) — parallelo        BE-5 (POST operatore)      FE-5 (SoggettoForm.vue)
     │                                       ←── DB-5                  FE-6 (ComuneAutocomplete)
DB-5 (fn_crea_operatore + indirizzi)            │                      FE-6b (StradarioAutocomplete)
   ←── DB-1, DB-2, DB-3                   BE-6 (test)                  FE-7 (AuthUserForm)
     │                                                                      │
DB-6 (test pgTAP) ←── DB-1..DB-5                                      FE-8 (refactor drawer)
                                                                       FE-9 (aggiorna views)
                                                                       FE-10 (i18n) — parallelo
                                                                       FE-11 (build + verifica)
```

### Decisioni prese

1. **DB-1b — Stradario chiuso**: toponomastica / stradario_generale / stradario sono gestiti solo da admin.
   L'utente operativo seleziona da vie esistenti via autocomplete. Nessuna funzione di creazione on-the-fly.

2. **DB-7 — Funzione DB**: `script.fn_search_stradario(p_comune_id, p_search, p_limit)` — coerente
   col pattern del progetto (lettura ottimizzata in DB, Django orchestra e espone API).

3. **DB-4 — `valido_dal` opzione B**: nessun ALTER TABLE, il COALESCE nella funzione basta.

### Ordine di esecuzione consigliato

**Parallelo 1** (indipendenti, nessuna dipendenza):

* DB-1 (`fn_get_or_create_indirizzo_dettaglio`)
* DB-3 (`fn_crea_soggetto_pf` + `p_comune_nascita_id`)
* DB-7 (search stradario — dopo decisione aperta #2)
* BE-1 (refactoring lookup — nessuna dipendenza DB)
* FE-10 (i18n — nessuna dipendenza)

**Parallelo 2** (dopo Parallelo 1):

* DB-2 (`fn_crea_indirizzo_soggetto` — dipende da DB-1)
* BE-2, BE-3, BE-4, BE-7 (endpoint lookup/search — nessuna dipendenza DB)
* FE-1, FE-2, FE-3 (API client, useLookup, refactoring store — dipende da BE-1..BE-4)

**Sequenziale 3** (dopo Parallelo 2):

* DB-5 (aggiornare `fn_crea_operatore` — dipende da DB-1, DB-2, DB-3)
* BE-5 (POST operatore — dipende da DB-5)
* FE-4, FE-5, FE-6, FE-6b, FE-7 (composable + componenti — dipende da FE-1..FE-3)

**Sequenziale 4** (dopo tutto):

* DB-6 (test pgTAP — dipende da DB-1..DB-5)
* FE-8 (refactor drawer — dipende da FE-5, FE-7, BE-5)
* FE-9 (aggiorna views)
* BE-6 (test completi)
* FE-11 (build + verifica finale)
