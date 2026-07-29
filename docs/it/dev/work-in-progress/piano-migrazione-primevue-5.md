# Piano operativo — Migrazione a PrimeVue 5 (+ @primeuix/themes 3, primeicons 8)

> **Tipo**: piano operativo FE (`dev/backend-tid`) · **Data**: 2026-07-29 ·
> **Owner**: Tid · **Stato**: ⬜ **DA ESEGUIRE** — pianificato, non iniziato ·
> **Raccomandazione**: **non ora**, vedi §1. Il piano è pronto per quando si decide di partire.
>
> **Contesto**: non siamo in produzione
> ([[project_no_produzione_solo_sviluppo]]) → breaking secchi ammessi.

---

## 0. Come usare questo documento

È scritto per essere eseguito **in una sessione separata**, senza il contesto
della conversazione che l'ha prodotto. Tutto ciò che serve è qui dentro.

Tre regole per chi esegue:

1. **Una major per volta, un commit per volta.** Se qualcosa si muove a video,
   devi poter dire *quale* pacchetto l'ha mossa. Saltare questa regola è il modo
   più veloce per passare una giornata a bisezionare.
2. **I numeri di §2 sono del 2026-07-29** e il branch è vivo: **ri-misurali**
   (i comandi ci sono) prima di fidarti.
3. **Niente `npm install` senza ok esplicito di Tid** — regola di casa
   (AGENTS.md §Frontend, [[feedback_autorizzazioni_esplicite]]). Questo piano
   *descrive* i comandi, non autorizza a lanciarli.

---

## 1. La raccomandazione: non ora

| Pacchetto | Da | A | Uscita | Patch sulla major |
| --- | --- | --- | --- | --- |
| `primevue` | 4.5.5 | 5.0.0 | **2026-07-15** | 1 |
| `@primeuix/themes` | 2.0.3 | 3.0.0 | 2026-07-15 | 1 |
| `primeicons` | 7.0.0 | 8.0.0 | 2026-07-15 | 1 |
| `pinia` | 3.0.4 | 4.0.2 | 2026-07-14 | 3 |

Sono uscite **tutte due settimane fa** e tre su quattro sono ancora al `.0.0`.
PrimeVue 4.0.0 è del luglio 2024 e oggi è alla 4.5.5: cinque minor di
correzioni in due anni. Con **260 file su 335** che importano PrimeVue,
aggiornare oggi significa candidarsi a trovare i bug per conto della community.

**Non è un problema di documentazione**: la guida di migrazione v5 esiste ed è
chiara, le release notes di Pinia 4 pure. Manca il *collaudo altrui*.

**Quando riprenderlo**, con segnali oggettivi invece di un «più avanti»:

- PrimeVue arrivata a ~5.2, o comunque due mesi di patch alle spalle;
- changelog di primeicons 8.0.0 pubblicato (al 2026-07-29 il `CHANGELOG.md` su
  `master` si ferma alla 7.0.0).

**Costo di aspettare: zero.** Nessun blocco, nessuna EOL, nessun avviso di
sicurezza; la 4.5.5 è supportata.

---

## 2. Superficie misurata (2026-07-29 — da ri-verificare)

```bash
cd frontend
# quanti file toccano PrimeVue
grep -rl "from 'primevue/" src --include=*.vue --include=*.js | wc -l
grep -rh "from 'primevue/" src --include=*.vue --include=*.js | wc -l
# quali componenti
grep -rho "from 'primevue/[a-z]*'" src --include=*.vue --include=*.js \
  | sed "s/.*primevue\///;s/'//" | sort | uniq -c | sort -rn
```

| Pacchetto | Superficie |
| --- | --- |
| `primevue` | **937 import in 260 file** (su 335 `.vue`) |
| `pinia` | 43 store, 39 `userScoped`, **1 plugin che usa `pinia._s`** |
| `@primeuix/themes` | **1 file** — `src/main.js`, preset `Aura` |
| `primeicons` | 122 classi `pi-*` distinte + **28 codepoint cablati** in `main.css` |

I dieci componenti più usati: `tag` (96), `button` (93), `inputtext` (90),
`column` (86), `datatable` (76), `select` (75), `drawer` (67), `message` (58),
`toggleswitch` (43), `inputnumber` (43).

---

## 3. Cosa NON è un problema (verificato)

PrimeVue 5 dichiara **nessun breaking change sulle API pubbliche dei
componenti**. E i componenti rimossi o deprecati **non sono usati da noi**:

| Componente | v5 | Nel repo |
| --- | --- | --- |
| `Calendar`, `Dropdown`, `Chips` | rimossi | ❌ non usati |
| `InputMask` | ora è una **direttiva** | ❌ non usato |
| `Carousel` | riscritto (compound API) | ❌ non usato |
| `MultiSelect` → `Select` | deprecato | ❌ non usato |
| `Galleria` → `Gallery` | deprecato | ❌ non usato |
| `ColorPicker` → `InputColor` | deprecato | ❌ non usato |

Comando di controllo (deve dare 0 per ciascuno):

```bash
cd frontend
for c in inputmask carousel multiselect galleria colorpicker calendar dropdown chips; do
  printf "%-12s %s\n" "$c" "$(grep -rl "primevue/$c'" src --include=*.vue --include=*.js 2>/dev/null | wc -l)"
done
```

> Questo lo dobbiamo alla migrazione `TabView`→`Tabs` e `Dropdown`/`Calendar`
> completata il 2026-07-22: ci ha già portati fuori dal campo minato.

---

## 4. I tre rischi specifici di questo repo

### R1 — La baseline del font passa da 14px a 16px 🔴

PrimeVue dimensiona i componenti in `rem`. La v4 assumeva un root di **14px**,
la v5 assume **16px**. L'app **non fissa** il root font-size (nessuna regola
`html { font-size }` in `theme.css`), quindi eredita i 16px del browser.

Col preset standard di v5 **tutte le proporzioni si ricalibrano** — e questa è
una UI deliberatamente densa: tabelle compatte, paginator ridotto,
`--app-font-size-base: 0.875rem`.

**Mitigazione ufficiale**: ogni preset ha una variante **`compat`** tarata a
14px. Si parte da lì → upgrade a **delta visivo zero**. Il passaggio allo
standard 16px è una decisione separata, da prendere dopo e con calma (§6.5).

### R2 — primeicons 8 e i 28 codepoint cablati 🟠

Le icone composite di dominio (`.app-nav-icon-*`, frontend-standards
§"Iconografia di dominio") **non** usano le classi `pi-*`: incollano il glifo
con `content: "\eXXX"`. Se v8 rinumera i codepoint, quelle icone diventano
**glifi sbagliati in silenzio** — nessun errore, nessun test rosso, solo un
camion al posto di una matita.

Il changelog di 8.0.0 non è pubblicato, quindi è un ignoto — ma **meccanicamente
verificabile**. C'è uno script pronto e collaudato: §6.3.

### R3 — `pinia._s` nel plugin auto-reset 🔴

`src/core/pinia-plugins/auto-reset.js:91` itera `pinia._s` — **API privata**
(la mappa interna degli store). Pinia 4 non promette nulla al riguardo.

Se cambia, il reset degli store `userScoped` al logout smette di funzionare, e
il sintomo è **silenzioso**: l'utente B vede filtri e cache dell'utente A sullo
stesso browser. Per gravità è il peggiore dei tre — nessun test lo copre, e non
si manifesta con un errore ma con dati sbagliati a video.

---

## 5. Step 0 (raccomandato) — la rete di sicurezza

**Il progetto non ha alcun test frontend**: niente vitest, niente playwright.
La verifica di una migrazione che tocca ogni schermata è oggi «build verde +
occhio umano», e l'occhio umano è quello di Tid.

Prima di toccare PrimeVue conviene investire mezza giornata in **3 smoke
Playwright** con baseline screenshot **presa su PrimeVue 4.5**:

1. login;
2. una lista configurabile (righe presenti, paginator presente, n. colonne);
3. il kebab di riga (`RowActionsMenu`) — si apre e mostra le voci.

Il valore non è l'assert: è lo **screenshot diff**. Trasforma «riguardati tutta
l'app e spera di accorgerti che le tabelle sono cresciute» in «guarda questi tre
screenshot che sono cambiati» — ed è esattamente il tipo di regressione che R1
produce.

⚠️ Costo: `@playwright/test` come devDependency **+ download browser**
(~150-300 MB in `~/.cache/ms-playwright`; su questa macchina non c'è alcun
browser headless). È una decisione sulle dipendenze → **ok esplicito di Tid**.

⚠️ Gli E2E scritti male sono fragili e diventano rumore che si impara a
ignorare. Regole per tenerli sani: pochi, sul **telaio** e non sul dominio
(quello è già coperto dai 38 smoke BE), niente asserzioni su testi di dominio,
niente dipendenze dall'ordinamento, **niente `sleep` fissi**. E niente
asserzioni sul *contenuto* dei dati: il DB di dev è magro e variabile
(«la tabella ha righe» sì, «la tabella ha 5 righe» no).

**Se si salta lo Step 0**, il piano resta valido ma la verifica di §6.4 diventa
interamente manuale e va messa in conto.

---

## 6. Gli step

**Prerequisito comune**: working tree pulito (`git status`) e branch dedicato.

```bash
git switch -c chore/upgrade-primevue-5
cd frontend
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use --lts
```

### 6.1 — Pinia 4 (il più isolato, si può fare anche da solo)

```bash
npm i pinia@^4 @vue/devtools-api
./node_modules/.bin/vite build
npm run lint
```

`@vue/devtools-api` va installato **esplicitamente**: in Pinia 4 non è più una
dipendenza transitiva. L'altra novità è che il pacchetto è **ESM-only** (per noi
irrilevante: Vite lo è già).

**Verifica — l'unica che conta, ed è manuale** (R3):

1. login utente A;
2. applica filtri su una lista (es. clienti: ricerca + filtro data);
3. **logout**;
4. login utente B;
5. **i filtri devono essere spariti.**

Se sono ancora lì, `pinia._s` è cambiato e il reset user-scoped è morto: **non
proseguire**, va riscritto `auto-reset.js` su API pubbliche
(`pinia.use(...)` + registro proprio degli store invece di leggere `_s`).

Commit: `chore(fe): pinia 4 + @vue/devtools-api`.

### 6.2 — primeicons 8: baseline PRIMA

⚠️ **Da fare prima di aggiornare**, altrimenti il confronto non esiste più.
La baseline su primeicons 7 è già in repo
(`frontend/scripts/primeicons-codepoints.baseline.json`), ma verificala:

```bash
node scripts/check-primeicons-codepoints.mjs           # deve uscire [ok], exit 0
```

Se il file non c'è o è disallineato:

```bash
node scripts/check-primeicons-codepoints.mjs --baseline
```

### 6.3 — primeicons 8: upgrade e diff

```bash
npm i primeicons@^8
node scripts/check-primeicons-codepoints.mjs           # ← il controllo vero
```

Lo script confronta i 28 codepoint cablati in `main.css` con la mappa
`.pi-*:before` del `primeicons.css` **installato**, e segnala:

- `[X]` codepoint che **non esiste più** nel font;
- `[!]` codepoint che ora risolve a un'icona **diversa** da quella dichiarata
  nel commento inline (`/* pi-file — base documento */`);
- **drift** rispetto alla baseline.

Se segnala qualcosa: aprire `src/assets/main.css` alle righe indicate e
sostituire il codepoint con quello nuovo della stessa icona *per nome* (il nome
è la verità, il numero è un dettaglio d'implementazione del font).

**Verifica a video**: la sidebar dei documenti vendite — preventivi, offerte,
ordini, DDT, resi, contratti, fatture devono avere ognuno il **proprio**
overlay, e non tutti lo stesso.

Commit: `chore(fe): primeicons 8 + allineamento codepoint icone di dominio`.

### 6.4 — PrimeVue 5 + @primeuix/themes 3 (insieme, mai separati)

Sono accoppiati: `@primeuix/themes` 3 è la controparte di PrimeVue 5.

```bash
npm i primevue@^5 @primeuix/themes@^3
```

**Poi, PRIMA di buildare**, passare alla variante `compat` del preset in
`src/main.js` (R1). Oggi la riga è:

```js
import Aura from '@primeuix/themes/aura'
// ...
app.use(PrimeVue, { theme: { preset: Aura, /* ... */ } })
```

Va usata la variante calibrata a 14px. **Verificare il nome esatto dell'export
nella v3 installata** — non indovinarlo:

```bash
ls node_modules/@primeuix/themes/           # sottocartelle disponibili
grep -rl "compat" node_modules/@primeuix/themes/ | head
cat node_modules/@primeuix/themes/package.json | python3 -m json.tool | grep -A2 exports | head -40
```

Poi:

```bash
./node_modules/.bin/vite build
npm run lint
```

**Verifica a video** — le schermate a più alta densità di componenti, in
quest'ordine (dalla più probabile alla meno):

| # | Cosa | Perché proprio questa |
| --- | --- | --- |
| 1 | **Kebab di riga**, inline (desktop) e compact (<1024px) | `Menu` in v5 ha il multi-livello nuovo, e noi lo usiamo in `RowActionsMenu`, `PageActionsBar` e `DrawerActionsBar`: è in **ogni riga di ogni lista** |
| 2 | Una lista configurabile (clienti, contratti) | `DataTable` + paginator + ritiro colonne responsive |
| 3 | Un drawer con tab (`LottoDrawer`) | `Tabs`/`TabPanel` + `DataTable` annidata |
| 4 | Un `AppDialog` con footer | `Dialog` + `FormFooter` |
| 5 | Un toast di successo e uno di errore | Toast ha animazioni nuove |
| 6 | Il login | l'unica schermata senza sidebar/topbar |

Se lo Step 0 è stato fatto: `npx playwright test --update-snapshots=none` e
guardare i diff.

Commit: `chore(fe): primevue 5 + themes 3 (preset compat 14px)`.

### 6.5 — (separato, non ora) dal `compat` allo standard 16px

Decisione a sé, da prendere quando il resto è stabile. Significa accettare che
tutta la UI cresca di ~14% e ricalibrare le variabili `--app-*` di `theme.css`.
**Non mescolarla con l'upgrade**: sono due cose diverse che si romperebbero a
vicenda nella diagnosi.

---

## 7. Rollback

Ogni step è un commit isolato, quindi:

```bash
git revert <sha>          # oppure git switch main && git branch -D chore/upgrade-primevue-5
npm ci                    # ripristina node_modules dal lock
```

⚠️ `npm ci` e non `npm install`: rimette **esattamente** il lock committato.

---

## 8. Trappole (lette a caro prezzo altrove)

- **Non aggiornare `vue` nello stesso giro.** È a 3.5.40 e non è nell'elenco:
  lasciarlo fuori tiene una variabile in meno.
- **Non fidarsi del build verde.** Vite compila anche una UI completamente
  sballata: il build dice che gli import risolvono, non che l'app si vede.
- **Non toccare `theme.css` durante l'upgrade.** Se qualcosa non torna, la
  tentazione è ritoccare una variabile: così però si mescola la migrazione con
  una ricalibrazione, e non si sa più cosa ha causato cosa. Prima si arriva a
  delta zero col `compat`, poi eventualmente §6.5.
- **`i18n`**: nessun impatto atteso, ma `python3 scripts/check_i18n_keys.py`
  costa due secondi e va tenuto verde comunque.
- **Backend**: nessun impatto. Non serve rilanciare la suite Django, ma se si
  tocca `main.js` conviene un `kill -HUP` al master gunicorn solo se si sta
  servendo il FE buildato ([[project_backend_gunicorn_reload]]).

---

## 9. Registro

### 2026-07-29 · Analisi e piano

Nato dalla domanda di Tid dopo un `npm outdated` che segnalava quattro major.
Superficie misurata sul repo, guide ufficiali lette (non a memoria), date di
rilascio verificate sul registry npm.

**Tre conclusioni che hanno formato il piano:**

1. **Il codice non è il problema**: nessuno dei componenti rimossi o deprecati
   in v5 è usato: il grosso del lavoro era già stato fatto a luglio con
   `TabView`→`Tabs`.
2. **Il problema è la freschezza + l'assenza di rete**: tutto pubblicato due
   settimane fa, e zero test FE. Da qui la raccomandazione di aspettare e la
   proposta dello Step 0.
3. **L'unico ignoto (i codepoint delle icone) non richiede documentazione**:
   è verificabile meccanicamente. Da qui lo script
   `frontend/scripts/check-primeicons-codepoints.mjs`, scritto e **collaudato**
   contro primeicons 7 (exit 0, 28 codepoint risolti, baseline salvata).
