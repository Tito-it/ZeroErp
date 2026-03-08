# ZeroERP — Standard Frontend

> Questo documento definisce le regole di progettazione e sviluppo dell'interfaccia utente di ZeroERP.  
> È vincolante per qualsiasi contributo al frontend. Le deroghe devono essere documentate e motivate.

---

## Stack tecnologico

| Componente | Versione | Ruolo                   |
| ---------- | -------- | ----------------------- |
| Vue.js     | 3.5.x    | Framework UI            |
| Vite       | 7.x      | Build tool e dev server |
| PrimeVue   | 4.5.x    | Libreria componenti     |
| PrimeIcons | latest   | Iconografia             |
| Pinia      | 3.x      | Gestione stato          |
| Vue Router | 5.x      | Navigazione             |
| Node.js    | 24 LTS   | Runtime di sviluppo     |

---

## Struttura del progetto

La struttura delle cartelle rispecchia i domini del database. Chi conosce il backend riconosce immediatamente il frontend.

```
src/
  core/               ← client API, error handling, composables base, utilities
  config/             ← dominio config
  anagrafiche/        ← dominio anagrafiche
  catalogo/           ← dominio catalogo
  pratiche/           ← dominio pratiche
  vendite/            ← dominio vendite
  acquisti/           ← dominio acquisti
  magazzino/          ← dominio magazzino
  pagamenti/          ← dominio pagamenti
  contabilita/        ← dominio contabilità
  router/             ← definizione rotte
  stores/             ← store Pinia globali
  assets/             ← immagini, font, stili globali
```

Ogni cartella di dominio contiene:

```
anagrafiche/
  views/              ← pagine intere (lista, dettaglio)
  components/         ← componenti specifici del dominio
```

`core/` è l'equivalente frontend di `dbops` e `scripts`: nessun dominio lo chiama esplicitamente, ma tutti dipendono da lui.

---

## Layout generale

L'interfaccia è suddivisa in tre aree fisse:

```
┌─────────────────────────────────────────────────┐
│                   TOPBAR                         │
├──────────┬──────────────────────────────────────┤
│          │                                      │
│ SIDEBAR  │           AREA CONTENUTO             │
│          │                                      │
│          │                                      │
└──────────┴──────────────────────────────────────┘
```

### Sidebar sinistra (fissa, collassabile)
- Sempre visibile, collassabile tramite pulsante dedicato in fondo
- Quando collassata mostra solo le icone con tooltip al passaggio del mouse
- La preferenza di stato (aperta/chiusa) è persistita in localStorage
- Contiene la navigazione tra i domini (le "stanze")
- Ogni voce ha un'icona PrimeIcons e un'etichetta
- La voce attiva è evidenziata visivamente
- Logo e nome applicazione in cima
- Logout e pulsante comprimi/espandi in fondo

### Topbar
- Sempre visibile
- Mostra il percorso corrente (breadcrumb): `Dominio > Sezione`
- Contiene il pulsante **Nuovo** quando applicabile
- Contiene eventuali filtri rapidi globali della schermata

### Area contenuto
- Occupa tutto lo spazio rimanente
- Contiene la schermata attiva (lista o altra vista)

---

## Login

La schermata di login è l'unica pagina senza sidebar e topbar.

- Centrata verticalmente e orizzontalmente
- Logo ZeroERP in cima
- Form con campi: **Username** e **Password**
- Pulsante **Accedi** (larghezza piena del form)
- Messaggio di errore inline in caso di credenziali errate (non toast)
- Nessun link "Registrati" — accesso solo su invito

---

## Schermata di benvenuto (default dopo login)

La prima schermata dopo l'autenticazione mostra:

- Saluto personalizzato con nome utente
- Accessi rapidi ai domini autorizzati (card cliccabili con icona e nome)
- Pannello calendario attivita' (colonna destra)
- Nessun KPI o dato aggregato in questa fase — evolvera' in una dashboard completa in seguito

### Accessi rapidi personalizzabili

La home mostra di default tutti i domini autorizzati per l'utente. L'utente puo' selezionare i propri **preferiti**, che vengono mostrati in evidenza rispetto agli altri.

- Le preferenze sono salvate nel backend come campo JSON sul profilo utente
- Al login vengono caricate insieme ai dati di sessione
- I preferiti sono sempre un sottoinsieme dei domini autorizzati — se un'autorizzazione viene revocata, il preferito viene ignorato silenziosamente senza errore
- I domini non preferiti restano visibili ma con stile secondario (non spariscono)

### Pannello calendario attivita'

Il pannello e' visibile **solo nella home**, nella colonna destra. Scompare navigando nelle stanze.

```text
┌──────────────────────────────────┬──────────────────┐
│                                  │                  │
│   Accessi rapidi (card griglia)  │   Calendario     │
│                                  │   attivita'      │
│                                  │                  │
└──────────────────────────────────┴──────────────────┘
```

**Contenuto**: mostra le attivita' in scadenza relative all'unita' organizzativa dell'utente connesso, non solo le proprie. Per ogni attivita' e' indicato il responsabile di competenza.

**Organizzazione temporale**:

| Sezione | Visualizzazione |
| --- | --- |
| **Oggi** | In evidenza, con indicatore visivo di urgenza |
| **Prossimi 5 giorni** | Raggruppate per giorno |

**Comportamento**:

- Il click su un'attivita' porta alla **lista pratiche filtrata** per quella specifica pratica — non apre il drawer direttamente. L'utente mantiene il contesto della lista e puo' navigare liberamente
- Il pannello si aggiorna automaticamente al primo caricamento della home
- Non si aggiorna in tempo reale — un refresh manuale e' sufficiente per questa fase

### Evoluzione prevista: home personalizzabile (idea progettuale)

> Questa sezione descrive un'evoluzione futura — non e' ancora implementata ne' vincolante.

Le dashboard non saranno un dominio a se', ma viste specializzate all'interno dei domini esistenti (es. `vendite/views/FatturazioneDashboard.vue`, `pagamenti/views/FlussiDashboard.vue`).

Il meccanismo dei preferiti si estendera' oltre i domini: l'utente potra' aggiungere ai propri preferiti anche dashboard specifiche, rotte di dominio, o viste frequenti. Il campo JSON sul profilo e' gia' progettato per ospitare sia domini che viste, sotto forma di riferimenti a rotte.

La home diventera' cosi' un punto di ingresso completamente personalizzabile per ogni utente, con i propri accessi rapidi scelti tra tutto cio' che e' autorizzato: domini, dashboard, liste filtrate.

---

## Pattern lista

Ogni schermata di elenco segue questo schema fisso:

```
┌─ TOPBAR: [Breadcrumb]                  [Nuovo] ─┐
├─────────────────────────────────────────────────┤
│ [Filtro 1] [Filtro 2] [Cerca...]                │
├─────────────────────────────────────────────────┤
│ Colonna A │ Colonna B │ Colonna C │   Azioni    │
│───────────┼───────────┼───────────┼─────────────│
│ dato      │ dato      │ dato      │ 🖊 👁 🗑    │
│ dato      │ dato      │ dato      │ 🖊 👁 🗑    │
├─────────────────────────────────────────────────┤
│                  [Paginazione]                   │
└─────────────────────────────────────────────────┘
```

### Tabella
- Componente `DataTable` di PrimeVue
- Paginazione server-side (mai caricare tutti i record)
- Ordinamento per colonna abilitato di default sulle colonne principali
- Righe con altezza confortevole, padding verticale sufficiente
- Nessuna riga espandibile — i dettagli si aprono nel drawer

### Filtri
- Posizionati sopra la tabella, sotto la topbar
- Campo di ricerca testuale sempre presente
- Filtri specifici del dominio accanto al campo di ricerca
- I filtri agiscono in tempo reale o con pulsante Cerca (deciso dominio per dominio)

### Colonna Azioni
- Sempre l'ultima colonna della tabella
- Larghezza fissa, non ridimensionabile
- Contiene icone cliccabili, una per azione disponibile
- Ogni icona ha un **tooltip** con la descrizione dell'azione (appare al passaggio del mouse)
- Le azioni tipiche sono: **Modifica** (`pi-pencil`), **Visualizza** (`pi-eye`), **Elimina** (`pi-trash`)
- Le azioni variano per dominio — non tutte le righe hanno le stesse azioni
- Icone con colori semantici: modifica neutro, elimina rosso

---

## Drawer (nuovo e modifica)

**Regola unica: qualsiasi form di inserimento o modifica si apre sempre in un drawer laterale destro.**  
Non esistono dialog di compilazione né pagine intere per i form. Il drawer è l'unico pattern.

### Comportamento
- Si apre da destra con animazione slide
- La lista rimane visibile e invariata sullo sfondo
- Si chiude con: tasto `ESC`, clic fuori dal drawer, pulsante Annulla, o salvataggio riuscito
- Non è possibile aprire due drawer contemporaneamente

### Larghezze standard
| Tipo di form                              | Larghezza |
| ----------------------------------------- | --------- |
| Form semplice (tabelle di lookup, config) | 480px     |
| Form standard (anagrafiche, catalogo)     | 640px     |
| Form complesso (pratiche, contratti)      | 800px     |

La larghezza è definita a livello di dominio, non lasciata alla discrezione del developer.

### Struttura interna del drawer
```
┌─────────────────────────────────┐
│ Titolo ("Nuovo soggetto" /      │
│ "Modifica soggetto")            │
├─────────────────────────────────┤
│                                 │
│   Contenuto del form            │
│   (scrollabile se necessario)   │
│                                 │
├─────────────────────────────────┤
│ [Annulla]          [Salva]      │  ← fissi in fondo, non scrollano
└─────────────────────────────────┘
```

- Il titolo indica sempre l'operazione e l'entità: "Nuovo soggetto" / "Modifica soggetto"
- I pulsanti **Annulla** e **Salva** sono sempre in fondo, fissi, non scrollano con il contenuto
- **Salva** è il pulsante primario (colorato), **Annulla** è secondario (outline o testo)
- La validazione è inline sui campi — gli errori appaiono sotto il campo interessato
- Il pulsante Salva rimane disabilitato finché il form non è valido

---

## Conferma azioni distruttive

Qualsiasi azione irreversibile (eliminazione, annullamento, reset) richiede una conferma esplicita.

- Si apre un **dialog di conferma** centrato nella pagina (non un drawer)
- Il dialog mostra: titolo dell'azione + nome dell'elemento coinvolto
- Esempio: *"Sei sicuro di voler eliminare il soggetto **Mario Rossi**? L'operazione non può essere annullata."*
- Due pulsanti: **Annulla** (secondario) e **Conferma** (primario, colore rosso per azioni distruttive)
- Il dialog si chiude solo tramite uno dei due pulsanti — non con ESC o clic fuori

---

## Notifiche

| Tipo                  | Componente       | Posizione      | Durata                           |
| --------------------- | ---------------- | -------------- | -------------------------------- |
| Successo              | Toast            | Alto a destra  | 3 secondi                        |
| Errore operativo      | Toast            | Alto a destra  | 5 secondi (con chiusura manuale) |
| Errore di validazione | Inline sul campo | Sotto il campo | Fino a correzione                |
| Errore di sistema     | Toast            | Alto a destra  | Persistente con chiusura manuale |

I toast di successo hanno icona e colore verde. I toast di errore hanno icona e colore rosso.  
Il testo è sempre in italiano, chiaro e specifico — mai messaggi generici come "Errore" o "OK".

---

## Regole di stile generali

- **Tema**: Aura (PrimeVue) — dark mode seguendo le preferenze di sistema
- **Lingua interfaccia**: italiano
- **Iconografia**: esclusivamente PrimeIcons — nessuna libreria aggiuntiva
- **Font**: default del tema Aura — non personalizzare senza motivazione documentata
- **Densità**: interfaccia densa, adatta all'uso intensivo da desktop — no spaziature consumer/marketing
- **Responsive**: ottimizzato per desktop (≥ 1280px) — il mobile non è un obiettivo in questa fase

---

## Multilingua

ZeroERP è progettato per supportare più lingue fin dall'inizio. La libreria utilizzata è **vue-i18n v10**.

### Regola fondamentale
**Nessun testo visibile all'utente viene scritto direttamente nei componenti.** Ogni stringa usa la funzione di traduzione `$t()`:

```html
<!-- ❌ SBAGLIATO -->
<Button label="Salva" />

<!-- ✅ CORRETTO -->
<Button :label="$t('common.save')" />
```

### Struttura dei file di traduzione
```
src/
  locales/
    it.json    ← italiano (lingua di default)
    en.json    ← inglese (lingua di fallback)
```

Le chiavi sono organizzate per area funzionale: `common`, `nav`, `auth`, `notifications`, `confirm`, e una sezione per ogni dominio.

### Regole operative
- La lingua di default è **italiano** (`locale: 'it'`)
- La lingua di fallback è **inglese** (`fallbackLocale: 'en'`) — se una chiave manca in italiano, viene usata quella inglese
- Quando si aggiunge una nuova stringa, va aggiunta **in entrambi i file** contemporaneamente
- I nomi delle chiavi sono in inglese, il contenuto nella lingua del file
- Le chiavi specifiche di dominio vanno nella sezione del dominio corrispondente (es. `anagrafiche.new_subject`)

---

## Principi architetturali

### Modularita' e riuso

Ogni configurazione, costante o lista condivisa deve avere **una sola fonte di verita'**. Se un dato viene usato in piu' componenti, deve essere estratto in un modulo `core/` e importato — mai duplicato.

**Regola pratica**: se modifichi un valore e devi toccare piu' di un file, quel valore va centralizzato.

Esempi concreti gia' implementati:

| Dato                  | Fonte unica               | Usato da                          |
| --------------------- | ------------------------- | --------------------------------- |
| Lista domini/voci nav | `core/navigation.js`      | `AppSidebar`, `HomeView`          |
| Larghezze drawer      | `core/constants.js`       | Tutti i drawer di dominio         |
| Durata toast          | `core/constants.js`       | `core/useNotify.js`               |
| Opzioni paginazione   | `core/constants.js`       | Tutte le `DataTable`              |
| Client API            | `core/api.js`             | Tutti i componenti e store        |
| Notifiche             | `core/useNotify.js`       | Tutti i componenti                |

### Parametrizzazione via route meta

La `Topbar` e il layout si adattano automaticamente in base ai metadati della rotta corrente. Per aggiungere comportamenti a una schermata, basta configurare `meta` nella definizione della rotta:

```js
{
  path: 'soggetti',
  component: SoggettiListView,
  meta: {
    domain: 'anagrafiche',      // breadcrumb: primo livello
    section: 'Soggetti',        // breadcrumb: secondo livello
    allowNew: true              // mostra pulsante "Nuovo" nella topbar
  }
}
```

Non creare logica condizionale nei componenti layout per gestire casi specifici di dominio. Usare `meta` per dichiarare il comportamento, i componenti `core/` lo interpretano.

### Isolamento dei domini

- I componenti di un dominio (es. `vendite/`) non importano mai da un altro dominio (es. `anagrafiche/`)
- Se serve logica condivisa tra domini, va in `core/`
- I domini comunicano solo tramite il router (navigazione) e lo store (stato globale)

---

## Sicurezza

### Autenticazione JWT

L'autenticazione e' basata su JWT (access + refresh token) gestiti dallo store `stores/auth.js`. Le regole di sicurezza sono implementate a livello infrastrutturale — i componenti di dominio non devono occuparsene.

| Meccanismo | Dove | Descrizione |
| --- | --- | --- |
| **Route guard** | `router/index.js` | Tutte le rotte sono protette di default. Solo `meta: { public: true }` le rende accessibili |
| **Token refresh automatico** | `core/api.js` | Su risposta 401, l'interceptor tenta il refresh prima di redirigere al login |
| **Accodamento richieste** | `core/api.js` | Richieste parallele durante un refresh in corso vengono accodate, non scartate |
| **Protezione loop** | `core/api.js` | Le chiamate a `/token/` non innescano il meccanismo di refresh (previene loop infiniti) |
| **Redirect post-login** | `core/api.js`, `LoginView` | La rotta originale viene salvata come query param `?redirect=` e ripristinata dopo il login |
| **Logout centralizzato** | `stores/auth.js` | Un unico metodo `clearTokens()` pulisce tutti i dati di sessione |
| **Redirect utente autenticato** | `router/index.js` | Un utente gia' autenticato che naviga a `/login` viene rediretto alla home |

### Regole di sicurezza per il developer

- **Mai accedere a `localStorage` direttamente** per leggere/scrivere token — usare sempre `useAuthStore()`
- **Mai usare `window.location`** per redirect di autenticazione — usare il router per evitare page reload
- **Mai esporre dati sensibili** (token, password) in `console.log`, template o attributi HTML
- **Validare sempre l'input utente** prima di inviarlo all'API — la validazione frontend e' UX, non sicurezza, ma previene chiamate inutili
- **Mai costruire URL con interpolazione di stringhe** dall'input utente — usare i parametri Axios

---

## File core implementati

I seguenti file sono gia' presenti in `src/core/` e devono essere utilizzati da tutti i componenti senza duplicazioni:

### Moduli infrastrutturali

| File | Ruolo |
| --- | --- |
| `core/api.js` | Client Axios centralizzato con interceptor JWT, token refresh automatico e gestione 401 |
| `core/constants.js` | Costanti globali: larghezze drawer, durata toast, opzioni paginazione |
| `core/navigation.js` | Configurazione centralizzata domini e voci sidebar |

### Composables

| File | Ruolo |
| --- | --- |
| `core/useNotify.js` | Notifiche toast uniformi (`success`, `error`, `systemError`) |
| `core/useApiHandler.js` | Wrapper chiamate API con gestione automatica errori/toast e stato `loading` |
| `core/usePagination.js` | Stato paginazione server-side, integrato con PrimeVue DataTable |
| `core/useConfirmAction.js` | Dialog conferma azioni distruttive (`confirmDelete`, `confirmAction`) |

### Componenti layout e riutilizzabili

| File | Ruolo |
| --- | --- |
| `core/components/AppLayout.vue` | Layout principale: sidebar + topbar + area contenuto |
| `core/components/AppSidebar.vue` | Sidebar fissa con navigazione domini da `navigation.js` |
| `core/components/AppTopbar.vue` | Topbar con breadcrumb e azioni parametrizzate via `route.meta` |
| `core/components/AppDrawer.vue` | Drawer laterale standard con titolo, slot contenuto, pulsanti fissi |
| `core/components/PaginationInfo.vue` | Barra info paginazione con pagina corrente, totale, e vai-a-pagina |

### Viste core

| File | Ruolo |
| --- | --- |
| `core/views/HomeView.vue` | Schermata di benvenuto con griglia domini da `navigation.js` |
| `core/views/LoginView.vue` | Schermata di login senza layout (rotta pubblica) |

### Stili globali

| File | Ruolo |
| --- | --- |
| `assets/theme.css` | Variabili CSS custom `--app-*` — unico punto di personalizzazione visiva |
| `assets/main.css` | Reset CSS e stili base del documento |

Lo store di autenticazione e' in `src/stores/auth.js` — gestisce login, logout, token refresh e stato `isAuthenticated`.

---

## Gestione errori API

I componenti di dominio **non devono** gestire gli errori delle chiamate API manualmente. Il composable `useApiHandler` intercetta le risposte, estrae il messaggio dall'envelope backend e mostra il toast appropriato.

### Envelope errore backend

Il backend restituisce sempre la struttura: `{ error: { code, message, detail, hint, retryable, ui_action }, meta: { request_id } }`.
Il frontend legge `error.message` per il toast utente. I campi `detail`, `hint` e `retryable` sono disponibili per logica avanzata.

### Flusso errori

```text
Componente → useApiHandler.execute() → api.js (interceptor)
                                           ↓
                                    401 → token refresh → retry
                                    4xx → estrai message → toast error
                                    5xx → estrai message → toast systemError (persistente)
                                    rete/timeout → toast systemError
```

### Esempio d'uso nei componenti

```js
const { execute, loading } = useApiHandler()
const { t } = useI18n()

// Caricamento dati (nessun toast su successo, toast automatico su errore)
const data = await execute(() => api.get('/vendite/fatture/', { params }))

// Salvataggio (toast su successo e su errore)
const result = await execute(
  () => api.post('/vendite/fatture/', payload),
  { successMessage: t('notifications.save_success') }
)

// Polling silenzioso (nessun toast)
const status = await execute(() => api.get('/status/'), { silent: true })
```

---

## Paginazione server-side

Tutte le liste usano paginazione server-side. Il composable `usePagination` gestisce lo stato e si integra con PrimeVue `DataTable`.

### Esempio d'uso

```js
const pagination = usePagination()
const items = ref([])

async function loadData() {
  const data = await execute(() => api.get('/endpoint/', {
    params: { ...pagination.queryParams.value, search: searchText.value }
  }))
  if (data) {
    items.value = data.results
    pagination.updateFromResponse(data)
  }
}
```

```html
<DataTable :value="items" lazy
  :totalRecords="pagination.totalRecords.value"
  :rows="pagination.rows.value"
  :first="pagination.first.value"
  :rowsPerPageOptions="pagination.rowsOptions"
  @page="pagination.onPage($event); loadData()"
  paginator>
  <!-- colonne -->
</DataTable>
<PaginationInfo
  :page="pagination.page.value"
  :totalPages="pagination.totalPages.value"
  :totalRecords="pagination.totalRecords.value"
  @go-to-page="pagination.goToPage($event); loadData()"
/>
```

### Reset filtri

Quando l'utente cambia i filtri di ricerca, chiamare `pagination.reset()` prima di ricaricare i dati per tornare alla prima pagina.

---

## Sistema di theming CSS

L'aspetto visivo dell'applicazione e' interamente controllato da variabili CSS custom definite in un unico file: `src/assets/theme.css`. Per personalizzare colori, dimensioni o transizioni, e' sufficiente modificare **solo questo file** — tutti i componenti lo referenziano.

### Architettura a due livelli

| Livello | Prefisso | Fonte | Ruolo |
| --- | --- | --- | --- |
| **PrimeVue** | `--p-*` | Tema Aura | Colori base, tipografia, superfici |
| **ZeroERP** | `--app-*` | `theme.css` | Variabili applicative che referenziano `--p-*` |

I componenti usano **solo** variabili `--app-*`. Se serve un colore PrimeVue, lo si mappa prima in `theme.css` con un nome semantico `--app-*`, poi lo si usa nel componente. Questo garantisce che un cambio di tema o palette si faccia in un solo punto.

### Sezioni di theme.css

| Sezione | Variabili | Esempio |
| --- | --- | --- |
| Sidebar | `--app-sidebar-*` | `--app-sidebar-bg`, `--app-sidebar-item-active-bg` |
| Topbar | `--app-topbar-*` | `--app-topbar-bg`, `--app-topbar-breadcrumb-color` |
| Area contenuto | `--app-content-*` | `--app-content-bg`, `--app-content-padding` |
| Card dominio | `--app-card-*` | `--app-card-bg`, `--app-card-hover-border` |
| Logo | `--app-logo-*` | `--app-logo-bg`, `--app-logo-size` |
| Login | `--app-login-*` | `--app-login-card-bg`, `--app-login-error-color` |
| Drawer | `--app-drawer-*` | `--app-drawer-footer-border` |
| Transizioni | `--app-transition-*` | `--app-transition-fast` (0.15s), `--app-transition-normal` (0.2s) |
| Tipografia | `--app-font-size-*` | `--app-font-size-sm`, `--app-font-size-base`, `--app-font-size-lg` |

### Ordine di importazione in main.js

```js
import './assets/theme.css'   // 1. Variabili --app-* (sopra tutto)
import './assets/main.css'    // 2. Reset e stili base
```

`theme.css` deve essere importato **prima** di `main.css` affinche' le variabili siano disponibili per gli stili base.

### Regole di stile per i componenti

- **Mai usare `var(--p-*)` direttamente** nei componenti — creare prima una variabile `--app-*` in `theme.css`
- **Mai hardcodare colori** (`#fff`, `rgb(...)`, `hsl(...)`) nei componenti — usare sempre variabili
- Quando si aggiunge un nuovo componente con stili propri, aggiungere le variabili necessarie in `theme.css` con un commento di sezione
- I valori di default delle variabili `--app-*` referenziano `--p-*` — cambiando il tema PrimeVue (es. da Aura a Lara), l'app si adatta automaticamente

---

## Regole per il developer

- Ogni componente e' autonomo — nessuna logica di business fuori dai composables di `core/`
- Le chiamate API nei componenti passano attraverso `core/useApiHandler.js` — gestione errori e toast automatici
- L'accesso diretto a `core/api.js` e' riservato ai composables e agli store — mai nei componenti `.vue`
- Le notifiche toast passano sempre attraverso `core/useNotify.js` — mai `useToast()` direttamente
- I dialog di conferma passano attraverso `core/useConfirmAction.js` — mai `useConfirm()` direttamente
- I drawer usano `core/components/AppDrawer.vue` — mai creare drawer custom nei domini
- I testi visibili all'utente sono sempre tramite `$t()` — mai stringhe hardcoded
- Nessun `console.log` in produzione
- I componenti di dominio non importano da altri domini — solo da `core/`
- Le larghezze dei drawer sono le costanti definite in `core/constants.js`
- La lista dei domini e delle voci di navigazione e' in `core/navigation.js` — mai duplicarla nei componenti
- Aggiungere un nuovo dominio = aggiornare `core/navigation.js` + creare la cartella + aggiungere la rotta

---

*ZeroERP Frontend Standards — rev. 4*
*Sviluppo Concentrico — anello esterno, radici nell'infrastruttura*