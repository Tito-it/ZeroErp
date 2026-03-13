# Componenti Riutilizzabili — Architettura Building Block Frontend

> Documento di lavoro per la scomposizione in componenti atomici riusabili.
> Data: 2026-03-12
> Stato: **PIANIFICAZIONE**
>
> Dipende da:
>
> * [Guida Soggetti e Ruoli Anagrafici](/guide/soggetti-e-ruoli-anagrafici)
> * [Guida Gestione dei Contatti](/guide/gestione-dei-contatti)
> * [Guida Generazione di un Cliente](/guide/generazione-cliente)
> * [Guida Sviluppo Frontend](guida-sviluppo-frontend.md)
> * [Amministrazione Utenti](amministrazione-utenti.md)

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

## Vincoli dal modello dati

Prima di definire i componenti, e' fondamentale capire cosa il DB richiede
al COMMIT di una transazione che crea un soggetto.

### Vincoli DEFERRED (scattano al COMMIT)

| Trigger | Tabella | Errore | Cosa richiede |
|---|---|---|---|
| `trgfn_soggetti_guard_soggetto_contatti` | `soggetti` | `E_SOGGETTO_NO_CONTATTI` | Almeno un contatto default per ogni soggetto |
| `trgfn_soggetti_guard_indirizzi_required` | `soggetti` | `E_SOGGETTO_NO_INDIRIZZI` | Indirizzi obbligatori in base a `tipi_soggetto_dettaglio_tipi_indirizzo` |
| `trgfn_soggetti_guard_dati_societari_required` | `soggetti` | `E_DATI_SOCIETARI_REQUIRED` | Dati societari per SC/ENC (non per PF) |

### Implicazioni per i form

* **Creare un soggetto senza contatto** = errore garantito al COMMIT
* **Creare un soggetto PG senza dati societari** = errore per SC/ENC
* **Indirizzi** = dipendono dalla matrice config; per PR (Privato) potrebbe non essere obbligatorio

Questo significa che i form "Soggetto" e "Contatto" sono **inseparabili**:
ogni view che crea un soggetto DEVE includere anche il form contatto.

---

## Catena completa — dal DB al frontend

```
DB (building block SQL)                    Frontend (componenti Vue)
──────────────────────                     ─────────────────────────
fn_crea_auth_user          ←────────────→  AuthUserForm.vue
fn_crea_soggetto_pf        ←────────────→  SoggettoPFForm.vue + ContattoForm.vue
fn_get_or_create_soggetto_ruolo  (auto)    (nessun form — gestito dal backend)
fn_crea_risorsa_umana      ←────────────→  CollocazioneForm.vue (UO + qualifica)

fn_crea_operatore          ←────────────→  UtenteDrawer.vue (compone i form sopra)
(futuro) fn_crea_cliente   ←────────────→  ClienteDrawer.vue (compone form diversi)
```

Il backend (repository + service) fa da ponte: il frontend manda un payload unificato,
il service Python chiama i building block SQL nella giusta sequenza.

---

## Componenti atomici — Catalogo

### Collocazione: `src/core/components/`

Tutti i componenti riutilizzabili cross-dominio stanno in `core/components/`.
I componenti specifici di un dominio (es. `ClienteDatiForm.vue`) stanno in `src/<dominio>/components/`.

### 1. SoggettoPFForm.vue — Form persona fisica

**Scopo**: raccogliere i dati identificativi di una persona fisica.

**Campi**:

| Campo | Tipo | Obbligatorio | Note |
|---|---|---|---|
| cognome | InputText | si | Trim + uppercase dal trigger DB |
| nome | InputText | si | Trim + uppercase dal trigger DB |
| codice_fiscale | InputText | dipende dalla natura | 16 char alfanum, validazione formato |
| data_nascita | DatePicker | no | |
| sesso | Select | si | Default 'M', valori: M/F/S/X |
| tipo_soggetto_dettaglio_id | Select | si | Default: PR (Privato) |

**Props**:

```js
defineProps({
  modelValue: { type: Object, required: true },
  // { cognome, nome, codice_fiscale, data_nascita, sesso, tipo_soggetto_dettaglio_id }
  readonly: { type: Boolean, default: false },
  showTipoSoggetto: { type: Boolean, default: false }
  // PR e' il default per PF; mostrare il select solo se servono anche DI (Ditta Ind.)
})
defineEmits(['update:modelValue'])
```

**Riusato da**: Crea operatore, Crea cliente PF, Crea fornitore PF, Profilo utente (readonly).

**Validazione locale (UX)**:

* cognome e nome non vuoti
* codice_fiscale: formato 16 char se compilato
* Nessuna validazione di unicita' lato frontend (il DB la gestisce)

---

### 2. SoggettoPGForm.vue — Form persona giuridica

**Scopo**: raccogliere i dati identificativi di un'azienda o ente.

**Campi**:

| Campo | Tipo | Obbligatorio | Note |
|---|---|---|---|
| ragione_sociale | InputText | si | |
| codice_fiscale | InputText | si | Per PG sempre obbligatorio |
| partita_iva | InputText | si | 11 cifre numeriche |
| tipo_soggetto_dettaglio_id | Select | si | SP/SC/ENC |

**Riusato da**: Crea cliente PG, Crea fornitore PG, Crea gestore, Scheda emittente fiscale.

**Nota**: per SC e ENC il form deve attivare anche `DatiSocietariForm.vue` (vincolo DEFERRED).

---

### 3. ContattoForm.vue — Form contatto

**Scopo**: raccogliere i dati di un contatto associabile a soggetto, ruolo o utility.

**Campi**:

| Campo | Tipo | Obbligatorio | Note |
|---|---|---|---|
| nominativo | InputText | si | Nome del referente |
| email | InputText | no* | Almeno un canale consigliato |
| telefono | InputText | no | |
| cellulare | InputText | no | |
| pec | InputText | no | |
| unita_organizzativa_id | Select (UOSelect) | no | Reparto/ufficio |
| tipo_contatto_id | Select | no | Categoria |
| note | Textarea | no | |

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

### 4. IndirizzoForm.vue — Form indirizzo

**Scopo**: raccogliere un indirizzo in modalita' normalizzata o libera.

**Campi modalita' normalizzata**:

| Campo | Tipo | Obbligatorio | Note |
|---|---|---|---|
| tipo_indirizzo_id | Select | si | Filtrato dalla matrice config |
| indirizzo_dettaglio_id | Autocomplete | si | Ricerca su `anagrafiche.indirizzi_dettaglio` |

**Campi modalita' libera** (fallback per esteri/non normalizzabili):

| Campo | Tipo | Obbligatorio | Note |
|---|---|---|---|
| indirizzo_libero | InputText | si | |
| stato_id | Select | si | |
| comune_id / locality | InputText | si | |
| codice_postale_id / postal_box | InputText | si | |

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

### 5. AuthUserForm.vue — Form credenziali di accesso

**Scopo**: raccogliere username, email e password per un utente Django.

**Campi**:

| Campo | Tipo | Obbligatorio | Note |
|---|---|---|---|
| username | InputText | si | |
| email | InputText | si | Formato email |
| password | Password | si (in creazione) | Con toggle visibilita' e conferma |
| password_confirm | Password | si (in creazione) | Match con password |

**Props**:

```js
defineProps({
  modelValue: { type: Object, required: true },
  // { username, email, password, password_confirm }
  readonly: { type: Boolean, default: false },
  isEdit: { type: Boolean, default: false }
  // In edit mode: password opzionale (cambia solo se compilata)
})
```

**Riusato da**: Crea operatore, Crea admin, Reset password (solo campo password).

---

### 6. DatiSocietariForm.vue — Form dati camerali

**Scopo**: raccogliere forma giuridica, REA, capitale sociale per PG/ENC.

**Campi**:

| Campo | Tipo | Obbligatorio | Note |
|---|---|---|---|
| forma_giuridica_id | Select | si per SC/ENC | Filtrato da `config.forme_giuridiche_tipi_soggetto_dettaglio` |
| rea | InputText | no | |
| capitale_sociale | InputNumber | no | |

**Riusato da**: Crea cliente PG, Crea fornitore PG, Scheda emittente fiscale, Scheda gestore.

---

### 7. UOSelect.vue — Select unita' organizzativa

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

### 1. useSoggettoPF()

```js
// State + validazione per dati persona fisica
export function useSoggettoPF(initialData = {}) {
  const form = reactive({
    cognome: '',
    nome: '',
    codice_fiscale: '',
    data_nascita: null,
    sesso: 'M',
    tipo_soggetto_dettaglio_id: 1, // PR
    ...initialData
  })

  const errors = reactive({})

  function validate() { /* cognome, nome non vuoti; CF formato */ }
  function reset() { /* ripristina valori iniziali */ }

  return { form, errors, validate, reset }
}
```

**Riusato da**: ogni view che usa `SoggettoPFForm.vue`.

### 2. useContatto()

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

### 3. useAuthUser()

```js
// State + validazione per credenziali
export function useAuthUser(options = {}) {
  const { isEdit = false } = options

  const form = reactive({
    username: '',
    email: '',
    password: '',
    password_confirm: ''
  })

  function validate() {
    // username, email non vuoti
    // password match con confirm
    // in edit: password opzionale
  }

  return { form, errors, validate, reset }
}
```

### 4. useLookup(fetchFn, options)

```js
// Cache generica per lookup (UO, qualifiche, tipi contatto, ecc.)
export function useLookup(fetchFn, options = {}) {
  const { immediate = true, cacheKey = null } = options
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

| Caso d'uso | SoggettoPF | SoggettoPG | Contatto | Indirizzo | AuthUser | DatiSocietari | UOSelect |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Crea operatore | x | | x | | x | | x |
| Crea admin | x | | x | | x | | x |
| Crea cliente PF | x | | x | x | | | |
| Crea cliente PG | | x | x | x | | x | |
| Crea fornitore PF | x | | x | x | | | |
| Crea fornitore PG | | x | x | x | | x | |
| Profilo utente (readonly) | x | | x | | | | |
| Scheda soggetto (edit) | x/PG | x/PG | x | x | | x? | |
| Gestione contatti | | | x | | | | |

---

## Struttura cartelle risultante

```
frontend/src/
├── core/
│   ├── components/
│   │   ├── (esistenti: AppLayout, Sidebar, ecc.)
│   │   ├── SoggettoPFForm.vue          # NUOVO — form persona fisica
│   │   ├── SoggettoPGForm.vue          # NUOVO — form persona giuridica
│   │   ├── ContattoForm.vue            # NUOVO — form contatto
│   │   ├── IndirizzoForm.vue           # NUOVO — form indirizzo
│   │   ├── AuthUserForm.vue            # NUOVO — form credenziali
│   │   ├── DatiSocietariForm.vue       # NUOVO — form dati camerali
│   │   └── UOSelect.vue               # NUOVO — select unita' organizzativa
│   ├── composables/
│   │   ├── (esistenti: useNotify, useApiHandler, ecc.)
│   │   ├── useSoggettoPF.js            # NUOVO — state + validazione PF
│   │   ├── useSoggettoPG.js            # NUOVO — state + validazione PG
│   │   ├── useContatto.js              # NUOVO — state + validazione contatto
│   │   ├── useAuthUser.js              # NUOVO — state + validazione credenziali
│   │   └── useLookup.js               # NUOVO — cache generica per select
│   └── api/
│       └── anagrafiche.js              # NUOVO — API soggetti, contatti, indirizzi
├── amministrazione/
│   ├── components/
│   │   ├── UtenteDrawer.vue            # REFACTOR — compone building block core
│   │   ├── UtentePermessiTab.vue       # Invariato (specifico dominio)
│   │   └── RepartoProfiloEditor.vue    # Invariato
│   └── views/
│       └── ...
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

Il frontend manda un **payload unico** al backend (es. `POST /api/v1/amm-software/utenti/`).
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

| Fase | Cosa | Perche' |
|---|---|---|
| 1 | `useLookup`, `UOSelect` | Base per tutti i select, dipendenza trasversale |
| 2 | `useSoggettoPF` + `SoggettoPFForm` | Nucleo identita' PF, riusato ovunque |
| 3 | `useContatto` + `ContattoForm` | Obbligatorio per ogni creazione soggetto (guard DEFERRED) |
| 4 | `useAuthUser` + `AuthUserForm` | Necessario per operatori e admin |
| 5 | Refactor `UtenteDrawer.vue` | Primo consumer reale dei building block |
| 6 | `SoggettoPGForm`, `DatiSocietariForm`, `IndirizzoForm` | Per i domini successivi (clienti, fornitori) |

---

## Note

* I componenti atomici NON hanno dipendenze tra loro: `SoggettoPFForm` non importa `ContattoForm`.
  La composizione avviene solo nella view/drawer di dominio.
* Il pattern v-model bidirezionale permette alla view di leggere lo state del form
  e assemblare il payload per il backend.
* I componenti esistenti in `amministrazione/components/` verranno refactored gradualmente:
  prima si creano i building block core, poi si sostituiscono le sezioni monolitiche.
