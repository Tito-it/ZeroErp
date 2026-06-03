# Sviluppo — Preferiti utente (HOME + sidebar)

> **Stato**: ✅ IMPLEMENTATO (2026-05-25) — feature atterrata nel codice:
> store `navigation.js` multi-preferito (`favorites` mappa di array +
> `addFavorite`/`removeFavorite`/`toggleFavorite`/`reorderFavorites`, cap 4),
> `FavoriteItem.vue`, composable `useNavigationFavorites.js`, kebab topbar
> `TieredMenu` in `AppTopbar.vue`, `HomeView.vue`. Restano da spuntare solo
> le caselle smoke/accettazione manuali (step 10), non implementazione.
> **Branch di lavoro**: `dev/backend-tid` (interamente frontend, nessun
> intervento DB o BE).
> **Autore**: backend agent (sessione 2026-05-25).
> **Origine**: richiesta Tid 2026-05-25 — il sistema preferiti minimale
> esistente (1 preferita per dominio, usata solo come pagina di atterraggio)
> è poco scopribile e poco utile. Si vuole una vera lista preferiti.

## Stato attuale (sintesi)

Il codice oggi gestisce un solo "preferito" per dominio, salvato in
localStorage e usato unicamente come pagina di atterraggio quando l'utente
clicca l'icona del dominio in sidebar HOME.

- Store: [`stores/navigation.js`](../../../frontend/src/stores/navigation.js)
  — `favorites: { [domainKey]: routePath }`, funzioni `setFavorite`,
  `clearFavorite`, `isFavorite`, `getDefaultRoute`.
- Persistenza: localStorage con chiave `domainFavoriteKey(<domain>)`,
  scope per-utente (store ha `userScoped: true` → reset al logout).
- UI:
  [`SidebarDomain.vue`](../../../frontend/src/core/components/SidebarDomain.vue)
  espone una stella accanto a ogni voce L2 (`pi-star` / `pi-star-fill`);
  [`SidebarHome.vue`](../../../frontend/src/core/components/SidebarHome.vue)
  consuma `getDefaultRoute` per l'atterraggio dominio.
- Doc: una riga in
  [`frontend-standards.md`](frontend/frontend-standards.md) ("voci L2 +
  preferiti"), nessuna sezione dedicata.

**Gap funzionali**:

- Una sola preferita per dominio (toggle = overwrite, non aggiunta).
- Nessuna lista preferiti visibile in HOME — l'unico effetto della stella è
  cambiare la rotta di atterraggio, comportamento poco intuitivo.
- Nessuna scorciatoia diretta a una pagina senza prima entrare nel dominio.
- Nessun feedback nella HomeView (l'area centrale è oggi vuota per i
  preferiti).

## Obiettivi

1. **Lista preferiti per dominio**: fino a 4 voci L2 per dominio, ordinabili.
2. **Accesso rapido globale via topbar**: kebab dedicato in topbar (subito
   prima del pulsante Logout) che raggruppa preferenze utente (dark mode,
   lingua) + voce "Preferiti" che apre un **submenu** con tutte le voci
   preferite cross-dominio. Implementazione PrimeVue 4 `TieredMenu`.
3. **Pannello in HomeView**: i preferiti compaiono anche come tile cliccabili
   nell'area centrale della HomeView, con drag-and-drop per il riordino.
4. **Atterraggio coerente**: cliccare un dominio dalla sidebar HOME atterra
   sul *primo* preferito del dominio se esiste, altrimenti sulla prima voce
   L2 (fallback attuale).
5. **Riordino libero**: drag-and-drop in HomeView. (Nel topbar kebab non
   serve — l'utente apre il submenu e clicca; per riordinare va in HomeView.)
6. **Persistenza per-utente**: i preferiti sopravvivono al logout/login
   dello stesso utente. La chiave localStorage è user-aware
   (`<userId>:domain.favorite.<domain>`), niente più wipe forzato al logout.
   Altri utenti sulla stessa macchina vedono solo le loro chiavi.
7. **Migrazione trasparente**: i preferiti già salvati nel formato vecchio
   (chiave globale `domain.favorite.<domain>`) vengono migrati al primo
   login post-deploy verso la chiave user-aware come array di 1 elemento;
   la chiave vecchia viene rimossa. Senza azione utente.
8. **Cross-dominio non serve dato**: l'aggregazione globale nel topbar
   kebab copre il caso d'uso "voglio vedere tutti i miei shortcut insieme".

## Modello dati

### Struttura store

```js
// stores/navigation.js
const favorites = ref({
  vendite: ['/vendite/contratti', '/vendite/listini'],
  catalogo: ['/catalogo/articoli'],
  // ...
})
```

Da `{ [domain]: routePath }` (string) a `{ [domain]: routePath[] }` (array
ordinato). L'ordine dell'array E' l'ordine di visualizzazione (riordino
drag-and-drop = `splice` sull'array).

### API store

```js
// Tutte le funzioni accettano (domainKey, routePath) e mantengono l'array.
nav.addFavorite(domainKey, routePath)       // append se assente e cap non raggiunto
nav.removeFavorite(domainKey, routePath)    // splice se presente
nav.toggleFavorite(domainKey, routePath)    // add se assente, remove se presente
nav.isFavorite(routePath)                   // true se in qualche array
nav.isFavoriteOfDomain(domainKey, routePath) // true se nell'array di quel dominio
nav.reorderFavorites(domainKey, newOrder)   // sostituisce array (drag-and-drop)
nav.getDomainFavorites(domainKey)           // array, eventualmente vuoto
nav.getAllFavorites()                       // [{ domain, path }, ...] in ordine [dom1.preferiti, dom2.preferiti, ...]
nav.getDefaultRoute(domainKey)              // primo preferito || prima voce L2 || base dominio
```

### Cap

**4 preferiti per dominio** (nessun limite globale, si autoregola). Il
tentativo di aggiungere il 5° preferito mostra un toast con chiave i18n
`nav.preferiti_limite_raggiunto` (es. "Massimo 4 preferiti per dominio.
Rimuovine uno per aggiungerne un altro.") e la stella non si accende.

### Persistenza

LocalStorage con chiave esistente `domainFavoriteKey(<domain>)`, **valore
JSON-encoded array di string**. Migrazione automatica al primo load:

```js
function loadFavorites() {
  const result = {}
  for (const domain of DOMAINS) {
    const raw = local.get(domainFavoriteKey(domain.key))
    if (!raw) continue
    if (Array.isArray(raw)) result[domain.key] = raw
    else if (typeof raw === 'string') result[domain.key] = [raw]   // legacy → array 1 elem
  }
  return result
}
```

Nessun bump di versione storage, nessun prompt utente: i preferiti vecchi
restano e funzionano.

### Persistenza per utente e reset al logout

I preferiti devono restare disponibili al login successivo dello stesso
utente. Per evitare leak cross-user sullo stesso browser, lo store salva le
chiavi in forma user-scoped (`domain_default_<domain>_user_<id>`) dopo il
login, tramite `syncUserFavorites(userId)` chiamato da `auth.fetchProfile()`.

Al logout `clearUserState` azzera solo lo stato in memoria (`currentDomain`,
`favorites`, `currentUserId`), **non** cancella il localStorage personale.
Al login successivo dello stesso utente, `syncUserFavorites(userId)` ricarica
i preferiti personali. `clearAll` resta l'azione esplicita distruttiva per
rimuovere i preferiti dell'utente corrente.

Migrazione: se esiste ancora una vecchia chiave non user-scoped
`domain_default_<domain>`, al primo login viene copiata nella chiave personale
dell'utente corrente e poi rimossa dalla chiave legacy.

## UI

### Sidebar DOMINIO — stella su voce L2

Comportamento attuale ([`SidebarDomain.vue:155-162`](../../../frontend/src/core/components/SidebarDomain.vue)):
toggle = overwrite della preferita unica.

Nuovo comportamento:

- Toggle = `nav.toggleFavorite(currentDomain, item.to)` su lista.
- `pi-star-fill` (gialla) se la voce è in lista; `pi-star` (outline) altrimenti.
- Hover-only opacity (come oggi); stella piena sempre visibile.
- Se cap 4 raggiunto e l'utente prova ad aggiungere un 5° → toast `nav.preferiti_limite_raggiunto`,
  stella non cambia stato.
- Tooltip dinamico: `nav.add_favorite` / `nav.remove_favorite` (chiavi già esistenti).

### Topbar — kebab "preferenze utente" (con submenu Preferiti)

**Iter design**: in una prima iterazione i preferiti sono stati renderizzati
come sezione dedicata sopra l'elenco domini in `SidebarHome.vue`. La scelta
è stata poi rivista (2026-05-25): la sidebar HOME resta minimale (Home +
elenco domini), e i preferiti finiscono in un kebab dedicato in topbar
insieme alle altre preferenze utente. Motivazioni: la sidebar deve restare
una pura navigazione cross-dominio, le preferenze utente (lingua, tema,
shortcut) sono concettualmente "personali" e stanno meglio raggruppate in
topbar — coerente con dove l'utente già trova il proprio badge identità e
il logout.

Nuovo kebab in [`AppTopbar.vue`](../../../frontend/src/core/components/AppTopbar.vue),
posizionato **subito prima del pulsante logout**, sempre visibile (non solo
mobile). Implementazione PrimeVue 4 `TieredMenu` (variante di `Menu` che
supporta submenu nested). Stile coerente col kebab standard di lista via
`menuItemClass(undefined, 'app-menu-item-action')` (verde, come gli inline
`topbar-icon-btn`).

Voci del kebab:

```text
⋮  (icona MANAGE_ICONS.KEBAB, subito prima del logout)
   ├── ⭐ Preferiti                              ►  (submenu)
   │     ├── <icona voce> <label voce>           (1° preferito)
   │     ├── <icona voce> <label voce>           (2° preferito)
   │     └── ...                                  (visibili filtrati permessi)
   │     se vuoto → voce disabled "Nessun preferito"
   ├── 🌐 Lingua · IT/EN                          (click → toggle)
   └── 🌙 Modalità scura / ☀️ Modalità chiara     (click → toggle)
```

Dettagli:

- **Submenu Preferiti**: items risolti via `useNavigationFavorites().visibleFavorites`
  (già filtrati per permessi). Ogni voce ha l'icona della voce L2 originale
  e la label tradotta. Click → `navigateToFavorite(fav)` apre tab + naviga.
- **Empty state**: se non ci sono preferiti, il submenu mostra una sola voce
  `disabled` con `t('nav.preferiti_empty_short')` ("Nessun preferito") —
  l'utente capisce come aggiungerli usando la stella in `SidebarDomain.vue`.
- **No drag-and-drop nel topbar**: il riordino vive nella HomeView (vedi
  sotto). Il topbar è scorciatoia "apro al volo", non gestionale.
- **Stile colori**: `app-menu-item-action` (verde) — stesso fallback default
  del kebab `PageActionsBar`. Severity `danger`/`warn` non si applicano
  (sono tutte azioni neutre/positive).

### Sidebar HOME — invariata

`SidebarHome.vue` torna alla forma originale: Home + elenco domini. Nessuna
sezione preferiti, nessun composable di filtro consumato da qui. Il
`useNavigationFavorites` resta usato solo da `AppTopbar.vue` (submenu kebab)
e `HomeView.vue` (pannello tile).

### HomeView — pannello "I tuoi preferiti"

Sezione principale della HomeView (oggi probabilmente placeholder). Tile
grid responsive:

```text
┌───────────────────────────────────────────────┐
│ ⭐ I tuoi preferiti              [+ Aggiungi] │
├───────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│ │  icona   │ │  icona   │ │  icona   │        │
│ │ Articoli │ │ Listini  │ │ Approva… │        │
│ │ Catalogo │ │ Vendite  │ │ Vendite  │        │
│ └──────────┘ └──────────┘ └──────────┘        │
└───────────────────────────────────────────────┘
```

- **Tile**: icona voce grande + nome voce + sotto-label con nome dominio.
- **Drag-and-drop**: riordino libero, persiste subito su localStorage.
- **Click tile**: stesso `handleLeafClick` (apre tab + naviga).
- **Hover rimozione**: piccola × o stella piena in alto a destra del tile
  → rimuove dal dominio.
- **Empty state**: pannello con testo i18n `nav.preferiti_empty_hint` ("Apri
  un dominio dalla sidebar e clicca la stella sulle voci che vuoi
  ritrovare velocemente qui").
- **Pulsante "+ Aggiungi"**: opzionale fase 2, apre un picker (modal o
  dropdown) di tutte le voci L2 accessibili filtrabili → utile come
  scorciatoia rispetto a "entra in ogni dominio e clicca stella". Non
  bloccante per MVP.

### Atterraggio dominio

`getDefaultRoute(domainKey)` aggiornato:

```js
function getDefaultRoute(domainKey) {
  const favs = favorites.value[domainKey]
  if (favs && favs.length > 0) return favs[0]      // primo preferito
  const menu = DOMAIN_MENUS[domainKey] || []
  if (menu.length > 0) return menu[0].to
  const domain = DOMAINS.find(d => d.key === domainKey)
  return domain?.to || null
}
```

Quindi:

- Se l'utente ha definito 1+ preferiti per "Vendite" e clicca l'icona
  "Vendite" in sidebar HOME → atterra sul *primo* preferito (top dell'array,
  cioè quello aggiunto per primo o promosso col drag).
- Se non ha preferiti per quel dominio → prima voce L2 (comportamento
  attuale).
- Riordinare i preferiti col drag-and-drop cambia anche l'atterraggio
  dominio — semantica: "il primo della lista è quello che apro per primo".

## Filtri permessi / accessi bloccati

I preferiti puntano a route concrete; se il livello accesso utente cambia e
la voce non è più accessibile, il preferito va *filtrato a runtime* ma
**mantenuto in storage** (se l'accesso torna, il preferito ricompare).

Implementazione:

- `nav.getDomainFavorites(domainKey)` non filtra (restituisce raw).
- I componenti che renderizzano (SidebarHome, HomeView) applicano lo stesso
  filter di `visibleMenu` in
  [`SidebarDomain.vue:35-45`](../../../frontend/src/core/components/SidebarDomain.vue#L35-L45):
  per ogni preferito risolvere la voce in `DOMAIN_MENUS`, scartare se
  `requireArea` BLOCCATA o `requireAnyAction` non soddisfatto.
- Voce ammessa in lista solo se trovata in `DOMAIN_MENUS` (un preferito
  "morto" — route rimossa dal codice — viene silenziosamente ignorato).

## Edge case

- **Preferito a route con `children`**: oggi nessuna voce in `DOMAIN_MENUS`
  ha `children`, ma quando arriveranno il preferito punterà al `to` del
  leaf, non al gruppo padre. Coerente con `handleLeafClick`.
- **Doppio click rapido sulla stella**: `toggleFavorite` deve essere
  idempotente — un secondo toggle riporta allo stato iniziale. Già garantito
  dalla logica add/remove.
- **Cambio lingua**: i preferiti memorizzano `routePath`, la label è
  risolta via i18n a runtime. Nessuna azione richiesta.
- **Stessa voce L2 in due domini** (oggi non esiste, ma tecnicamente
  possibile in futuro): supportato — la chiave dello store è `[domain]` non
  `[routePath]`, quindi la stessa route può essere preferita in due domini
  distinti se mai capitasse.
- **Cap 4 — quale messaggio se l'utente riordina e poi prova ad aggiungere
  un 5°**: il toast del cap si attiva su `addFavorite`, non su `reorder`. Il
  riordino non aumenta il count.
- **Atterraggio dominio — re-click sullo stesso dominio già attivo**:
  `getDefaultRoute(domain)` è consultato SOLO quando il dominio attivo
  *cambia* (da HOME a DOMINIO, o da DOMINIO_A a DOMINIO_B). Se l'utente è
  già su `/vendite/contratti` (preferito #2) e ri-clicca l'icona "Vendite"
  in sidebar HOME, la navigazione NON deve forzare il salto a `/vendite/listini`
  (preferito #1) — sarebbe disorientante. Implementazione: in
  `SidebarHome.handleDomainClick`, prima di `router.push(getDefaultRoute())`
  verificare `if (nav.currentDomain === domain.key) return` (skip se già
  dentro). Riordinare i preferiti cambia il #1 e quindi il *prossimo* atterraggio,
  non quello corrente.
- **Sidebar collassata**: non più rilevante dopo lo spostamento dei
  preferiti in topbar. Il kebab topbar è indipendente dallo stato collapsed
  della sidebar — funziona sempre identico.
- **Submenu vuoto in topbar**: se l'utente non ha alcun preferito, la voce
  "Preferiti" nel kebab topbar resta visibile ma il submenu mostra una sola
  riga `disabled` con `t('nav.preferiti_empty_short')` ("Nessun preferito").
  L'utente capisce così come/dove aggiungerne (stella in SidebarDomain).

## i18n — chiavi nuove

```json
{
  "nav": {
    "preferiti": "Preferiti",
    "preferiti_sezione_sidebar": "Preferiti",
    "preferiti_empty_hint": "Apri un dominio dalla sidebar e clicca la stella sulle voci che vuoi ritrovare velocemente qui.",
    "preferiti_empty_short": "Nessun preferito",
    "preferiti_limite_raggiunto": "Massimo 4 preferiti per dominio. Rimuovine uno per aggiungerne un altro.",
    "preferiti_rimuovi": "Rimuovi dai preferiti",
    "preferiti_tooltip_dominio_voce": "{dominio} · {voce}"
  }
}
```

Le chiavi `nav.set_favorite` / `nav.remove_favorite` già usate dalla stella
restano invariate.

## Piano di esecuzione

> Sequenza autoritativa per l'implementazione. **Interamente frontend**:
> nessuna API, nessun BE, nessun DB. Persistenza su `localStorage` via store
> `navigation`, con chiavi per-utente.
>
> Le caselle (`- [ ]` → `- [x]`) si spuntano man mano che gli step vengono
> completati. Ogni step include sotto-task verificabili.

### 1. Rilettura vincoli frontend

- [x] Leggere [`frontend-standards.md`](../frontend/frontend-standards.md) (sezioni building block, sidebar, i18n)
- [x] Leggere [`catalogo-building-block-frontend.md`](../frontend/catalogo-building-block-frontend.md) (composable + componenti esistenti)
- [x] Verificare cosa esiste già in `src/core/composables/`, `src/core/components/`, `src/core/utils/` prima di creare nuovi building block

### 2. Mappatura codice corrente

- [x] Ispezionare [`stores/navigation.js`](../../../frontend/src/stores/navigation.js)
- [x] Ispezionare [`core/storage.js`](../../../frontend/src/core/storage.js) (funzione `domainFavoriteKey`, helper `local.get/set`)
- [x] Ispezionare [`core/navigation.js`](../../../frontend/src/core/navigation.js) (`DOMAINS`, `DOMAIN_MENUS`, `resolveNavigationLabel`)
- [x] Ispezionare [`SidebarDomain.vue`](../../../frontend/src/core/components/SidebarDomain.vue) (logica `visibleMenu`, `handleLeafClick`, `handleToggleFavorite`)
- [x] Ispezionare [`SidebarHome.vue`](../../../frontend/src/core/components/SidebarHome.vue) (`handleDomainClick`, `getDefaultRoute`)
- [x] Identificare la HomeView reale (cercare la route `/` o `/home`) e verificare contenuti esistenti
- [x] Verificare se `vuedraggable` è già in `package.json` (deps)
- [x] Verificare pattern test FE esistenti (se nessuno → MVP solo smoke manuale, lo dichiariamo allo step 9)

### 3. Building block minimi (no over-engineering)

- [x] Composable `useNavigationFavorites` in `src/core/composables/useNavigationFavorites.js`
  - risoluzione `(domain, path)` → `{ item, label, icon, tooltip }` via `DOMAIN_MENUS` + `resolveNavigationLabel`
  - filtro permessi runtime (estratto dalla logica oggi inline in [`SidebarDomain.vue:35-45`](../../../frontend/src/core/components/SidebarDomain.vue))
  - helper `navigateToFavorite({ domain, path })` → `tabs.openTab` + `nav.setDomain` + `router.push`
  - getter reattivo `visibleFavorites` (computed che applica il filtro permessi su `nav.getAllFavorites()`)
- [x] Componente atomico `FavoriteItem.vue` in `src/core/components/`
  - props: `domain`, `path`, `variant: 'sidebar' | 'tile'`, `collapsed?: boolean`, `draggable?: boolean`
  - rendering condizionato dal `variant`: lista compatta (sidebar) o tile (grid)
  - tooltip "Dominio · Voce" sempre, stella di rimozione hover, click → navigate
- [x] **NIENTE** wrapper `FavoriteList` / `FavoriteTiles`: il layout (lista verticale vs grid) vive nei consumer (`SidebarHome.vue`, HomeView), un wrapper qui aggiungerebbe indirezione senza riuso
- [x] Aggiornamento [`catalogo-building-block-frontend.md`](../frontend/catalogo-building-block-frontend.md) con le due nuove voci (dopo creazione)

### 4. Refactor store

- [x] Convertire `favorites` da `{ [domain]: string }` a `{ [domain]: string[] }`
- [x] Migrazione legacy in `loadFavorites()`: se `raw` è stringa → wrappare in `[raw]`; se array → usa diretto
- [x] Implementare API:
  - [x] `addFavorite(domain, path)` — append se assente e `length < 4`, ritorna `true|false` (per il caller toast)
  - [x] `removeFavorite(domain, path)` — splice se presente
  - [x] `toggleFavorite(domain, path)` — add se assente, remove se presente, rispetta cap (ritorna `false` se cap raggiunto)
  - [x] `reorderFavorites(domain, newOrder)` — sostituisce array
  - [x] `getDomainFavorites(domain)` — array raw (no filtro permessi qui)
  - [x] `getAllFavorites()` — `[{ domain, path }, ...]` in ordine dominio→ordine interno
  - [x] `isFavorite(path)` — true se in qualsiasi dominio (per la stella SidebarDomain)
  - [x] `isFavoriteOfDomain(domain, path)` — granulare
- [x] Aggiornare `getDefaultRoute(domain)`: primo preferito || prima voce L2 || base dominio
- [x] Separare `clearAll` distruttivo da `clearUserState` non distruttivo: logout pulisce solo memoria, i preferiti personali restano per il login successivo
- [x] Aggiungere `syncUserFavorites(userId)` e chiamarla da `auth.fetchProfile()` dopo il login/restore profilo
- [x] Test unitari dello store (solo se pattern test FE già esistente — verificato a step 2; nessun pattern test FE presente, copertura MVP via build + smoke manuale)

### 5. SidebarDomain

- [x] Sostituire `handleToggleFavorite` con chiamata a `nav.toggleFavorite(currentDomain, item.to)`
- [x] Se ritorno `false` (cap raggiunto): `useNotify().warn(t('nav.preferiti_limite_raggiunto'))` — severity **warn**, non error
- [x] Tooltip dinamici `nav.add_favorite`/`nav.remove_favorite` invariati (chiavi i18n già esistenti)
- [x] Stella si accende/spegne basata su `nav.isFavoriteOfDomain(currentDomain, item.to)`

### 6. Cablaggio rendering preferiti (topbar kebab + HomeView)

> **Iter design 2026-05-25**: la sezione preferiti in `SidebarHome.vue` è
> stata rimossa. I preferiti vivono ora nel kebab "preferenze utente" in
> topbar (`AppTopbar.vue`) come submenu `TieredMenu`, e nella HomeView
> come pannello tile con drag-and-drop.

- [x] Importare `useNavigationFavorites` nei due consumer (filtro + navigate condivisi)
- [x] `AppTopbar.vue` (kebab utente, pre-logout):
  - [x] import `TieredMenu` da PrimeVue 4
  - [x] computed `userKebabItems` con 3 voci: "Preferiti" (submenu via `items`), "Lingua", "Dark/Light mode"
  - [x] submenu Preferiti popolato da `visibleFavorites` (filtrato permessi)
  - [x] empty state: voce singola `disabled` con `t('nav.preferiti_empty_short')`
  - [x] click su voce preferito → `navigateToFavorite(fav)` (apre tab + naviga)
  - [x] classe `app-menu-item-action` su tutte le voci (verde, standard kebab)
- [x] `SidebarHome.vue`: pulizia — sezione preferiti rimossa, torna a forma minimale (Home + domini)
- [x] HomeView:
  - [x] pannello "I tuoi preferiti" con grid responsive di `FavoriteItem variant="tile"`
  - [x] empty state con testo `t('nav.preferiti_empty_hint')`
  - [x] drag-and-drop libero (riordino per dominio), persistenza su `drop end` via `nav.reorderFavorites`

### 7. Atterraggio dominio (regola "solo a cambio dominio")

- [x] `getDefaultRoute(domain)` usa primo preferito del dominio se esiste
- [x] In `SidebarHome.handleDomainClick`: aggiungere guard `if (nav.currentDomain === domain.key) return` PRIMA del `router.push`
  - rationale: se l'utente è già dentro il dominio, ri-cliccare l'icona NON deve forzare la navigazione al preferito #1 (sarebbe disorientante; vedi edge case)
- [ ] Verifica manuale al smoke: riordinare i preferiti cambia il prossimo atterraggio, non quello corrente

### 8. i18n e documentazione

- [x] `locales/it.json`: aggiungere le 6 chiavi `nav.preferiti*` documentate nella sezione "i18n — chiavi nuove"
- [x] `locales/en.json`: stesse chiavi tradotte (Favorites, Maximum 4 favorites per area, etc.)
- [x] `frontend-standards.md`: nuova sezione "Preferiti utente" con modello dati, API store, cap 4, regola atterraggio "solo a cambio dominio", pattern UI sidebar+home, comportamento collapsed
- [x] `catalogo-building-block-frontend.md`: entry per `useNavigationFavorites` (composable) e `FavoriteItem` (componente)

### 9. Build e smoke

- [x] `vite build` verde (nessun errore di compilazione, nessuna i18n key mancante)
- [ ] Smoke manuale (eseguire in ordine):
  - [ ] aggiungo 4 preferiti su "Vendite" → 5° tentativo: toast warn, stella non si accende
  - [ ] drag-and-drop in HomeView riordina, refresh persiste lo stato
  - [ ] topbar kebab: voce "Preferiti" mostra il submenu con tutte le voci visibili
  - [ ] topbar kebab — submenu vuoto: voce disabilitata "Nessun preferito" se zero preferiti
  - [ ] topbar kebab — click su preferito apre tab + naviga (no doppio click)
  - [ ] click "Vendite" da sidebar HOME (da stato HOME) → atterro sul primo preferito
  - [ ] sono su `/vendite/contratti`, ri-clicco "Vendite" → resto su `/vendite/contratti` (no salto al #1)
  - [ ] rimuovo tutti i preferiti di "Vendite" → atterraggio dominio torna alla prima voce L2
  - [ ] sidebar collapsed: nessun impatto sui preferiti (vivono in topbar)
  - [ ] cambio lingua IT → EN → label preferiti aggiornate sia in topbar sia in HomeView
  - [ ] filtro permessi: simulo un'area BLOCCATA per l'utente → i preferiti su quella area scompaiono da sidebar+HomeView ma restano in localStorage
  - [ ] logout/login stesso utente → preferiti ancora visibili
  - [ ] logout/login con altro utente → nessun leak (preferiti dell'altro non visibili)
  - [ ] legacy: chiudere browser, modificare manualmente in localStorage la chiave `domainFavoriteKey(vendite)` a valore stringa singolo `"/vendite/listini"`, riaprire app → letto come array di 1, funziona

### Definition of Done

L'MVP si considera **completato** quando:

- [ ] tutte le caselle degli step 1-9 sopra spuntate
- [x] build frontend verde (`vite build`)
- [ ] cap 4 per dominio attivo (testato manualmente a step 9)
- [ ] drag-and-drop funzionante in HomeView (riordino per dominio)
- [ ] kebab topbar mostra submenu Preferiti + lingua + dark/light, e naviga su click
- [ ] regola atterraggio "solo a cambio dominio" rispettata (testata a step 9)
- [ ] migrazione legacy stringa → array testata manualmente
- [x] `frontend-standards.md` e `catalogo-building-block-frontend.md` aggiornati
- [ ] preferiti persistenti dopo logout/login stesso utente
- [ ] nessun leak cross-user dopo logout/login con altro utente (`clearUserState` pulisce memoria e `syncUserFavorites` ricarica le chiavi personali)
- [x] nessuna duplicazione di logica tra topbar kebab e HomeView (entrambi consumano `useNavigationFavorites`)

## Cosa NON fa questo brief

- Nessuna preferita cross-dominio singolare (es. "questa è la mia home
  iniziale" indipendente dal dominio). La HOME aggregata copre il caso.
- Nessun pulsante "+ Aggiungi preferito" da HomeView in MVP (fase 2).
- Nessuna sincronizzazione cloud / per-device-share. localStorage per
  utente, basta.
- Nessuna analitica / contatore di "preferiti più cliccati".

## Riferimenti

- Store esistente: [`stores/navigation.js`](../../../frontend/src/stores/navigation.js)
- Storage helper: [`core/storage.js`](../../../frontend/src/core/storage.js)
  (funzione `domainFavoriteKey`)
- Sidebar dominio: [`SidebarDomain.vue`](../../../frontend/src/core/components/SidebarDomain.vue)
- Sidebar home: [`SidebarHome.vue`](../../../frontend/src/core/components/SidebarHome.vue)
- Navigation config: [`core/navigation.js`](../../../frontend/src/core/navigation.js)
  (`DOMAINS`, `DOMAIN_MENUS`, `resolveNavigationLabel`, `HOME_ITEM`)
- Doc standard esistente:
  [`frontend-standards.md`](frontend/frontend-standards.md) §"Catalogo
  componenti" (`SidebarDomain` cita "voci L2 + preferiti" — da espandere).

---

*Brief Preferiti utente — ZeroErp, 2026-05-25. Estende il sistema preferiti
minimale esistente. Pronto per implementazione su `dev/backend-tid`.*
