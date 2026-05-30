# Brief FE — Bundle splitting chunk principale

> **Stato**: CHIUSO · 2026-05-29 — interventi sicuri applicati (locale
> lazy + vendor-core split). Warning residuo sul main = **cosmetico,
> accettato consapevolmente**: il visualizer ha provato che sono byte di
> PrimeVue realmente usato, non grasso. Lo split PrimeVue è stato testato
> e SCARTATO (peggiora il boot, vedi sotto). Unico lever rimasto =
> app-level (meno componenti / tema più leggero), fuori scope.
> **Tipo**: debito tecnico FE (non-blocking)
> **Owner**: TBD

## Problema

Vite emette in build:

```text
(!) Some chunks are larger than 500 kB after minification.
dist/assets/index-D0NF_Otl.js   1,303.82 kB  │  gzip: 337.30 kB
```

Il chunk principale `index-*.js` pesa **1.30 MB raw / 337 KB gzip** dopo
minificazione, superando il soft-limit Vite di 500 KB.

Non è un bug funzionale: l'app si carica correttamente. È un debito
tecnico che impatta:

- TTFP (Time To First Paint) su nuovo download / cache fredda (~1.5s su
  3G veloce per 337 KB gzip + parse)
- Esperienza primo accesso operatore (login + redirect)
- Comportamento PWA in futuro (cache invalidation per ogni rebuild)

Per un'app B2B desktop con utenza interna e cache calda l'impatto è
mitigato, ma con il modello di sviluppo concentrico
(`feedback_concentrico_no_yagni`) il bundle continuerà a crescere se non
si fissa una soglia operativa adesso.

## Stato attuale (misure)

Output `vite build` rilevante (2026-05-29, dopo fix
INEFFECTIVE_DYNAMIC_IMPORT su `stores/ai.js`):

| Chunk | Raw | gzip | Note |
| --- | --- | --- | --- |
| `index-D0NF_Otl.js` | 1,304 KB | 337 KB | **Main bundle** — sopra il limit |
| `datepicker-*.js` | 97 KB | 20 KB | PrimeVue Calendar isolato (code split OK) |
| `SoggettoDrawer-*.js` | 74 KB | 17 KB | Lazy per route |
| `PreventiviView-*.js` | 64 KB | 17 KB | Lazy per route |
| `ConfigurazioneDocumentiView-*.js` | 70 KB | 18 KB | Lazy per route |
| `ListiniView-*.js` | 60 KB | 15 KB | Lazy per route |

Tutte le route sono già lazy (`component: () => import(...)`) — code
splitting per route funziona. Il problema è la **base** che entra
nel main chunk.

## Sospetti documentati

Da ispezione `frontend/src/main.js` (eager imports) +
`package.json`:

1. **Vue core + Vue Router + Pinia** — inevitabili nel main (~120 KB
   raw stimati). Niente da fare.
2. **PrimeVue config + base components in AppLayout/HomeView** —
   ~~`app.use(PrimeVue, {...})` ... componenti in catena eager~~.
   **VERIFICATO 2026-05-29: falso allarme.** In `main.js` NON c'è
   alcuna `app.component(...)` globale; i componenti PrimeVue sono
   importati per-componente (`from 'primevue/...'`, ~201 file) e quindi
   seguono il code-splitting per route. Solo la catena eager
   App → AppLayout → HomeView finisce nel main, ed è poca roba. PrimeVue 4
   con import per-componente è già tree-shaken: NON intervenire qui salvo
   evidenza contraria dal visualizer (sarebbe ottimizzazione speculativa,
   vietata da Decisioni aperte #2).
3. **vue-i18n + locale inline** — `core/i18n.js` importa `it.json` ed
   `en.json` inline ed eager (`messages: { it, en }`). **MISURATO
   2026-05-29: la stima precedente (~50-80 KB raw) era sbagliata di
   3-5×.** Dati reali:
   - `it.json` = 134 KB raw / 33 KB gzip
   - `en.json` = 128 KB raw / 32 KB gzip
   - **Totale inline nel main = 262 KB raw / 65 KB gzip**, cioè ~20% del
     main chunk sia raw sia gzip.

   È di gran lunga il singolo contributor più grosso e il più facile da
   togliere. Fix noto: caricare solo la locale attiva al boot e fare
   import lazy dell'altra allo switch (`loadLocaleMessages(locale)`).
   Guadagno atteso: ~33 KB gzip / ~130 KB raw via dal main, basso rischio.
4. **axios + interceptors** — `core/api.js` eager. ~40 KB raw. Difficile
   ridurre (è il client HTTP centrale).
5. **`@primeuix/themes/aura`** — tema importato eager.
6. **CSS bundle** — `theme.css`, `main.css`, `auth-pages.css` +
   `primeicons.css` — sono CSS, non JS, ma vanno verificati per
   font asset embedded.

## Target

Obiettivo operativo (rivedibile dopo prima misurazione visualizer):

| Metrica | Attuale | Target | Note |
| --- | --- | --- | --- |
| Main chunk raw | 1,304 KB | ≤ 700 KB | Sotto warning Vite default |
| Main chunk gzip | 337 KB | ≤ 180 KB | Soglia ragionevole TTFP |
| Numero chunk lazy | ~85 | — | Metrica accessoria, NON un obiettivo: contano gzip main + n. richieste critiche al boot, non il conteggio chunk |

## Strumenti

- `rollup-plugin-visualizer` — produce treemap `dist/stats.html` per
  identificare top contributor del main chunk. **Da installare con OK
  esplicito di Tid** (regola `feedback_autorizzazioni_esplicite`).
  Alternativa zero-deps: `npx vite-bundle-visualizer` (runtime, no
  package.json change). Da preferire come prima passata.
- `manualChunks` in `vite.config.js` per vendor split. **✅ FATTO
  2026-05-29 (split core sicuro). CAVEAT TECNICO: il progetto usa
  `rolldown-vite`, dove `manualChunks` DEVE essere una funzione** (la
  forma oggetto fallisce con `TypeError: manualChunks is not a
  function`). Implementato come `manualChunks(id)` che matcha i path
  `node_modules/...`. Chunk creati:
  - `vendor-core` (vue + vue-router + pinia + @vue) — 135 KB / 51 KB gzip
  - `vendor-i18n` (vue-i18n + @intlify) — 54 KB / 17 KB gzip
  - `vendor-http` (axios) — 40 KB / 15 KB gzip
  - `vendor-primevue` — **NON fatto di proposito**: primevue è splittato
    per route; raggrupparlo tutto lo renderebbe eager al boot (regresso).
    Da affrontare solo dopo il visualizer.

  Migrato poi a `build.rollupOptions.output.advancedChunks` (API nativa
  rolldown, suggerita dal build output stesso) — equivalente, più
  idiomatica della forma funzione `manualChunks`.

  ATTENZIONE: il vendor split sposta byte in chunk separati cacheabili →
  beneficio cache su rebuild (PWA). NON spegne il warning: vedi sotto
  "Analisi visualizer" — lo split PrimeVue che lo spegnerebbe è stato
  testato e scartato perché regredisce il boot.

## Decisioni aperte

1. **Quando affrontarlo**: dopo chiusura Sprint corrente (offerta
   commerciale + componenti BoM). Non priorità immediata.
2. **Approccio**: prima visualizer, poi decisione case-by-case. NO
   ottimizzazioni speculative. NO alzare `chunkSizeWarningLimit` per
   silenziare il warning (= nascondere il sintomo, vietato da
   `feedback_no_quick_fix_soluzione_assoluta`).
3. **Misura post-fix**: confronto raw+gzip prima/dopo per ogni
   manualChunk introdotto, salvato in fondo a questo brief.

## Analisi visualizer (2026-05-29) — composizione del main 725 KB

`npx vite-bundle-visualizer -t raw-data` sul main *dopo* locale lazy +
vendor-core split. Composizione del chunk `index` (gzip, sum-of-parts):

| Modulo | gzip | raw | Note |
| --- | --- | --- | --- |
| `primevue` (componenti) | 126 KB | 603 KB | superficie condivisa ≥2 route |
| `@primeuix/themes` (Aura) | 42 KB | 135 KB | tema + token |
| `@primevue/icons` | 42 KB | 84 KB | set icone |
| **src/core** (app eager) | 40 KB | 114 KB | tuo codice |
| `@primeuix/styles` | 14 KB | 81 KB | |
| `@primevue/core` | 9 KB | 32 KB | |
| src/stores + router | 11 KB | — | |

**~80% del main è l'ecosistema PrimeVue**; l'app code eager è solo
~50 KB gzip. I 725 KB NON sono grasso: sono la libreria UI usata
ovunque.

Ripartizione PrimeVue eager vs lazy (misurata):

- già eager nel main (condiviso ≥2 route): **234 KB gzip / 935 KB raw**
- correttamente lazy nelle route (datepicker, password, tabview…):
  **144 KB gzip / 601 KB raw**

### Esperimento split PrimeVue — TESTATO e SCARTATO

`advancedChunks` con `vendor-primevue` + `minShareCount: 2`:

| Chunk | raw | gzip |
| --- | --- | --- |
| `index` | 275 KB | 62 KB |
| `vendor-primevue` | **804 KB** | **169 KB** |

Due esiti negativi:

1. **Warning NON spento, solo spostato**: `vendor-primevue` è 804 KB raw
   (> 500 KB). La superficie condivisa è intrinsecamente ~800 KB raw e
   deve stare in un chunk unico (spezzarla in `-1/-2` arbitrari = cosmesi
   pura, vietata).
2. **Boot regredito di +72 KB gzip** (273 → 345): separare PrimeVue
   dall'app code perde compressione gzip di vicinanza.

→ Config tornata a vendor-core-only. Decisione chiusa: il warning resta,
è cosmetico. L'unico lever reale per ridurre i byte è app-level (meno
componenti PrimeVue importati / tema unstyled più leggero) — fuori scope
di questo brief, eventuale brief dedicato futuro se il boot diventasse un
problema misurato.

## Piano del fix (locale lazy) — ✅ COMPLETATO 2026-05-29

Obiettivo: togliere le due locale (`it`+`en`, 262 KB raw / 65 KB gzip)
dal main chunk caricando solo la locale attiva al boot e l'altra
on-demand allo switch lingua. Per l'utenza default IT, `en.json` non
viene mai scaricato finché non si passa a EN.

Passi:

1. **`core/i18n.js`** — rimuovere gli `import it`/`import en` statici e
   il `messages: { it, en }`. Creare l'istanza con `messages: {}`.
   Aggiungere `loadLocaleMessages(locale)` async che fa
   `await import('../locales/<locale>.json')` (dynamic import → Vite
   genera un chunk per locale) + `i18n.global.setLocaleMessage(...)`, con
   `Set` di locale già caricate per idempotenza.
2. `setAppLanguage(code)` → `async`: `await loadLocaleMessages(code)`
   prima di assegnare `i18n.global.locale.value`.
3. `syncUserLanguage(userId)` → `async`: carica la locale risolta prima
   di applicarla (fire-and-forget al call-site auth; per utente IT è
   no-op perché già caricata al boot).
4. **`main.js`** — bootstrap async: `await loadLocaleMessages(locale
   attiva)` (+ fallback se diverso da quella attiva, per correttezza dei
   fallback key) PRIMA di `app.mount('#app')`, così il primo paint ha le
   traduzioni.
5. Call-site: `AppTopbar.toggleLanguage` e `auth.fetchProfile` non
   richiedono modifiche oltre l'`await`/fire-and-forget (le funzioni
   chiamate diventano async ma il contratto resta).

Rischio basso: `t()` nel router è invocato solo dentro le guard
(post-mount), nessun uso a livello modulo che precederebbe il load.

File toccati: `core/i18n.js` (rimossi import statici, aggiunta
`loadLocaleMessages`, `setAppLanguage`/`syncUserLanguage` ora async),
`main.js` (bootstrap async con load locale attiva + fallback prima del
mount), `core/components/AppTopbar.vue` (`toggleLanguage` await).

### Risultato (misura post-fix `vite build` 2026-05-29)

| Metrica | Prima | Dopo | Δ |
| --- | --- | --- | --- |
| Main chunk raw | 1.304 KB | **1.059 KB** | −245 KB |
| Main chunk gzip | 337 KB | **265 KB** | −72 KB |
| `it` locale | inline nel main | chunk lazy `it-*.js` 111 KB raw / 31 KB gzip | scaricato al boot (default IT) |
| `en` locale | inline nel main | chunk lazy `en-*.js` 105 KB raw / 31 KB gzip | scaricato SOLO allo switch EN |

Esito: la diagnosi è confermata: le locale erano ~72 KB gzip del main.
Per l'utente default IT il boot ora scarica `index` + solo `it` (31 KB
gzip) invece di `index` con entrambe inline.

**Residuo aperto (follow-up, NON in questo fix):** il main resta a
1.059 KB raw, ancora sopra il soft-limit Vite di 500 KB → il warning di
build persiste (NON silenziato, come da Decisioni aperte #2). I prossimi
~200 KB gzip di app code richiedono il visualizer (Prossima azione punto
2) e sono debito separato a bassa priorità.

## Riferimenti

- Vite chunk size warning:
  <https://vite.dev/guide/build.html#chunking-strategy>
- Build pre-fix #1: stessi numeri (il dynamic import in
  `stores/ai.js` era cosmetico per il bundling, vedi log build
  2026-05-29).

## Storico

| Data | Misura | Note |
| --- | --- | --- |
| 2026-05-29 | 1,304 KB raw / 337 KB gzip | Baseline. Post fix `ai.js` INEFFECTIVE_DYNAMIC_IMPORT |
| 2026-05-29 | — | Correzione diagnosi: locale i18n = 262 KB raw / 65 KB gzip inline eager (non ~50-80 KB), ~20% del main. PrimeVue base = falso allarme (import per-componente, no registrazione globale). `vite.config.js` senza sezione build. Riordinata prossima azione: locale lazy PRIMA del visualizer |
| 2026-05-29 | 1.059 KB raw / 265 KB gzip | ✅ Fix locale lazy applicato (i18n.js + main.js + AppTopbar). −245 KB raw / −72 KB gzip dal main. `it`/`en` ora chunk separati 31 KB gzip cad.; default IT scarica solo `it` al boot. Warning Vite ancora presente (residuo app code, follow-up) |
| 2026-05-29 | 725 KB raw / 159 KB gzip | ✅ Vendor split core (vite.config.js, poi migrato ad `advancedChunks` nativa rolldown). −334 KB raw / −106 KB gzip dal main verso vendor-core/i18n/http. **Target gzip ≤180 KB RAGGIUNTO (159)**; target raw ≤700 KB mancato per 25 KB → warning ANCORA presente (non silenziato) |
| 2026-05-29 | 725 KB raw / 159 KB gzip | 🔬 Visualizer: main = ~80% PrimeVue (componenti 126 + tema 42 + icone 42 + styles 14 + core 9 = ~233 KB gzip), app code solo ~50 KB gzip. Split PrimeVue TESTATO e SCARTATO: `vendor-primevue` risulta 804 KB raw (warning si sposta, non sparisce) + boot +72 KB gzip (273→345). **Brief CHIUSO**: warning cosmetico accettato, lever residuo solo app-level (fuori scope) |
