# Piano operativo — Migrazione a PrimeVue 5 (+ @primeuix/themes 3, primeicons 8)

> **Tipo**: piano operativo FE (`dev/backend-tid`) · **Data**: 2026-07-29 ·
> **Owner**: Tid · **Stato**: 🔴 **FERMO — la premessa del piano è caduta**.
> §6.1 (Pinia 4) è **chiuso e resta valido**. §6.2/6.3 (primeicons 8) è stato
> eseguito e poi **annullato**. §6.4 (PrimeVue 5 + themes 3) **non è più una
> questione tecnica**.
>
> 🚨 **PrimeVue ha cambiato licenza al confine della major.** `primevue`,
> `@primeuix/themes` e `primeicons` erano **MIT** fino alla versione
> precedente e passano tutti e tre alla **licenza PrimeUI**
> (community/commerciale, con chiave di licenza) dalla nuova. ZeroErp è
> **GPL v3 pubblica**. Questo non è un rischio di migrazione: è una decisione
> di licenza, e non la prende un piano operativo. **Vedi §1-bis.**
>
> Tutto il lavoro tecnico di §4 resta corretto e utile — semplicemente non è
> più quello che decide.
>
> ⚠️ **Revisione del 2026-07-29 (seconda passata).** I rischi tecnici del
> piano sono stati **misurati**, non stimati: i tarball dei tre pacchetti sono
> stati scaricati con `npm pack` e interrogati senza installarli. Esito: R2
> annullato, R1 **rovesciato di verso** (lo standard v5 rimpicciolisce la UI,
> non la ingrandisce), due rischi che il piano non aveva visto trovati e
> verificati innocui. Quello che resta in piedi non è più una questione di
> codice nostro: è che il pacchetto è nuovo e non l'ha ancora collaudato
> nessuno. Dettaglio in §4 e §9.
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

## 1-bis. Il cambio di licenza — leggere prima di tutto il resto

> Scoperto il 2026-07-29, **dopo** aver installato primeicons 8 e **per caso**:
> un `npm i --dry-run` su `@primeuix/themes@3` mostrava l'arrivo di tre
> pacchetti inattesi — `@primeui/license-manager`, `@noble/ed25519`,
> `@noble/hashes`. Cioè un verificatore di **chiavi di licenza** con
> crittografia a firma.

### I fatti

| Pacchetto | Versione attuale | Licenza | Versione nuova | Licenza |
| --- | --- | --- | --- | --- |
| `primevue` | 4.5.5 | **MIT** | 5.0.0 | **PrimeUI** |
| `@primeuix/themes` | 2.0.3 | **MIT** | 3.0.0 | **PrimeUI** |
| `primeicons` | 7.0.0 | **MIT** | 8.0.0 | **PrimeUI** |
| `pinia` | 4.0.2 | **MIT** | — | — (non coinvolta) |

Verifica in due secondi: `npm view primevue@5.0.0 license` → `SEE LICENSE IN
LICENSE.md`; `npm view primevue@4.5.5 license` → `MIT`.

Il `LICENSE.md` è **identico** nei tre pacchetti e dice, in sintesi:

- **Community License (gratuita)** per chi sta sotto tutte queste soglie:
  < 1.000.000 USD di fatturato annuo, < 5 sviluppatori, < 10 dipendenti,
  < 3.000.000 USD di finanziamenti. Individui, studenti, non-profit e progetti
  open source non commerciali rientrano. **Rinnovo annuale** con conferma di
  idoneità.
- **Commercial License (a pagamento)** per tutti gli altri, per sviluppatore.
- **Chiave di licenza richiesta.** Verifica **offline**, nessuna telemetria,
  nessuna connessione remota — questo va detto, perché è la preoccupazione che
  viene per prima ed è infondata. Ma: *«A missing, invalid, or expired key may
  cause the software to display a license notice.»*
- **Restrizioni**: *«You may not reverse-engineer, decompile, or extract its
  source code, redistribute it as a component library or development tool, or
  remove its license mechanisms. Redistributing the software so that third
  parties can develop with it requires a separate OEM License.»*

### Perché riguarda ZeroErp

ZeroErp è **GPL v3** e pubblica su GitHub. La GPL v3 non ammette che si
aggiungano restrizioni oltre le proprie a chi riceve il codice, e la Community
License ne aggiunge parecchie: tetti di fatturato, di sviluppatori, di
dipendenti, e un rinnovo annuale. Il punto **non è** se ZeroErp sia idonea —
quasi certamente lo è — ma che **non può trasmettere a valle** una libertà che
lei stessa riceve con condizioni.

⚠️ Questa non è consulenza legale, e chi scrive non è un legale. È un
segnale: la decisione appartiene a Tid come titolare del copyright, e va presa
apposta, non per inerzia da un `npm i`.

### Attenuanti concrete (per non allarmarsi più del dovuto)

- `primeicons` 8 **non contiene codice**: zero dipendenze, spedisce solo
  `fonts/`, `raw-svg/` e `primeicons.css`. Nessuna chiave, nessun avviso a
  video. Il meccanismo di licenza è di **PrimeVue 5**, non suo.
- **ZeroErp oggi non distribuisce il frontend buildato**: il `Dockerfile`
  costruisce solo il backend Django e la CI non esegue `vite build`. I font
  finiscono in `frontend/dist/` solo in locale. Il giorno in cui si aggiungesse
  uno stage frontend, cambierebbe.
- **MIT non si revoca.** 4.5.5, 2.0.3 e 7.0.0 sono state pubblicate sotto MIT e
  restano MIT per sempre. «Congelati» non è «scaduti».

### Cosa è stato fatto

`primeicons` è stato **riportato a 7.0.0** con la procedura di §7
(`git checkout` del `package.json`/lock committati + `npm ci`, che ripristina
esattamente il lock invece di risolvere di nuovo). Motivo: la 8 non porta
**nulla** — 124 classi `pi-*` usate, tutte già nella 7; 28 codepoint identici;
le 45 icone in più non le usiamo. A beneficio zero, qualunque ambiguità è un
cattivo scambio. Tornare indietro tiene aperte tutte le opzioni; restare ne
chiudeva una senza aver comprato niente.

### E lo zero-patch di §1 si spiega da sé

L'analisi di §1 leggeva «zero patch a due settimane» come **poca adozione**. La
direzione era giusta, la causa no: non è che la 5.0.0 sia acerba — è che
l'ecosistema si è **ri-licenziato**, e la community sta reagendo a quello. È
anche il motivo per cui il segnale «aspetta la prima 5.0.x» non vale più: non
misura più quello per cui era stato scelto.

---

## 1. La raccomandazione: non ora — ma resta una ragione sola

| Pacchetto | Da | A | Uscita | Patch dopo la major (al 2026-07-29) |
| --- | --- | --- | --- | --- |
| `primevue` | 4.5.5 | 5.0.0 | **2026-07-15** | **0** |
| `@primeuix/themes` | 2.0.3 | 3.0.0 | 2026-07-15 | **0** |
| ~~`primeicons`~~ | ~~7.0.0~~ | **8.0.0 ✅ fatto** | 2026-07-15 | 0 |
| ~~`pinia`~~ | ~~3.0.4~~ | **4.0.2 ✅ fatto** | 2026-07-14 | 2 |

> **primeicons è stato staccato dal gruppo** e fatto il 2026-07-29, pur essendo
> anch'esso a zero patch. La ragione: è un font più un foglio di stile, **non
> entra nei componenti** — quindi il rischio «bug interno alla libreria che non
> puoi riparare», che è ciò che tiene fermo §6.4, lì non esiste. E il suo unico
> rischio proprio (i codepoint) era misurato al 100%. Vedi §9.
>
> Correzione rispetto alla prima stesura, che riportava «1 patch» per i tre
> pacchetti PrimeVue: **le patch sono zero**. `5.0.0`, `3.0.0` e `8.0.0` sono
> tuttora le ultime pubblicate. Verifica: `npm view primevue versions --json`.

**Il dato è più severo di come lo raccontava la prima stesura.** Quattordici
giorni dopo una major di un pacchetto grande come PrimeVue, zero patch non è un
segnale di perfezione: è un segnale di **poca adozione**. Pinia, nello stesso
periodo, di patch ne ha fatte due. Un ecosistema che sta davvero usando la 5.0.0
produce issue, e le issue producono `.0.1`.

Questa, dopo la seconda passata, è **l'unica ragione rimasta** per aspettare.
La prima stesura ne elencava tre — freschezza, R1 e R2 — ma R1 e R2 sono stati
misurati e sono caduti (§4). Il rischio non è più «il nostro codice è esposto e
non lo vediamo»: quello lo abbiamo guardato e sta bene. Il rischio è quello
generico di essere fra i primi a usare una major.

**Quando riprenderlo**, con segnali oggettivi invece di un «più avanti»:

- PrimeVue arrivata a ~5.2, **o anche solo alla prima `5.0.x`**: la prima patch
  è il segnale che qualcun altro la sta esercitando;
- changelog di primeicons 8.0.0 pubblicato (al 2026-07-29 il `CHANGELOG.md` su
  `master` si ferma alla 7.0.0) — ormai poco rilevante, vedi R2 in §4.

**Costo di aspettare: zero.** Nessun blocco, nessuna EOL, nessun avviso di
sicurezza; la 4.5.5 è supportata.

**Costo di NON aspettare, oggi**: molto più basso di quanto il piano credesse.
Se decidi di partire comunque, §6.4 è pronto, la mitigazione di R1 è confermata
esistente e il rollback è un `git revert` + `npm ci`. È una scelta difendibile,
non un azzardo — semplicemente non è quella che consiglio a parità di tutto.

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
| `primevue` | **937 import in 260 file** (su 335 `.vue`) — **47 moduli distinti** |
| `pinia` | 43 store, 39 `userScoped` — plugin ora su sola API pubblica (§6.1 fatto) |
| `@primeuix/themes` | **1 file** — `src/main.js`, preset `Aura` |
| `primeicons` | 122 classi `pi-*` distinte + **28 codepoint cablati** in `main.css` |

I dieci componenti più usati: `tag` (96), `button` (93), `inputtext` (90),
`column` (86), `datatable` (76), `select` (75), `drawer` (67), `message` (58),
`toggleswitch` (43), `inputnumber` (43).

### 2-bis. La superficie che la prima stesura non aveva contato

Gli `import` sono la parte **visibile** dell'accoppiamento a PrimeVue, e sono
anche la più innocua: se un modulo sparisce, il build lo dice. Gli altri due
agganci non li dice nessuno — cedono in silenzio.

```bash
cd frontend
# variabili CSS del tema usate direttamente
grep -rhoE '\-\-p-[a-z0-9-]+' src --include=*.css --include=*.vue --include=*.js | sort | uniq -c | sort -rn
# classi INTERNE dei componenti agganciate dal nostro CSS
grep -rhoE '\.p-[a-z0-9-]+' src --include=*.css --include=*.vue | sort | uniq -c | sort -rn
```

| Aggancio | Superficie | Se cede |
| --- | --- | --- |
| Variabili `--p-*` | **364 usi, 63 distinte, 51 file** | Il colore ripiega sul nulla: testo invisibile, sfondi trasparenti |
| Classi interne `.p-*` | **187 usi, 48 distinte, 9 file** | Lo stile si stacca e il componente torna nudo |

Le più agganciate sono `--p-primary-color` (65), `--p-text-muted-color` (58) e,
sul fronte classi, `.p-menu-item-link` + `.p-tieredmenu-item-link` (26 fra le
due) — cioè **il kebab**, che sta in ogni riga di ogni lista.

⚠️ Nota di merito, non di migrazione: le 364 variabili dirette contraddicono la
regola di casa «mai `--p-*` diretto, sempre `--app-*` da `theme.css`»
([[feedback_css_centralizzazione]]). Non è un problema **per** l'upgrade — le
variabili sopravvivono tutte (§4-R4) — ma è debito che rende ogni futura major
di PrimeVue più cara di quanto dovrebbe.

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

## 4. I rischi, dopo averli misurati

> **Come sono state fatte le misure** (2026-07-29, seconda passata). I tre
> pacchetti sono stati scaricati **senza installarli**, così le risposte
> arrivano prima di prendere qualunque impegno:
>
> ```bash
> cd "$(mktemp -d)"
> npm pack primeicons@8 @primeuix/themes@3 primevue@5
> for f in *.tgz; do mkdir -p "${f%.tgz}" && tar xzf "$f" -C "${f%.tgz}"; done
> ```
>
> `package.json`, `package-lock.json` e `node_modules` restano intatti. È il
> modo più economico che abbiamo per trasformare un «vedremo dopo l'upgrade»
> in un fatto — ed è la lezione di R3: **il controllo meccanico prima**.

### R1 — La baseline del font 🟢 MISURATO — e il verso era sbagliato

**Cosa diceva la prima stesura**: «col preset standard di v5 la UI cresce di
~14%». **È il contrario.**

PrimeVue dimensiona in `rem`. La v4 dava per scontato un root di **14px**, la v5
di **16px**. L'app non fissa il root, quindi eredita i **16px** del browser: già
oggi, quindi, rendiamo i valori della v4 più grandi di come erano pensati. La v3
dei temi **riscala i token verso il basso** proprio per ottenere a 16px l'aspetto
che la v4 otteneva a 14px:

| Token | v2 `aura` (oggi) | v3 `aura-compat` | v3 `aura` standard |
| --- | --- | --- | --- |
| `semantic.formField.paddingY` | `0.5rem` | `0.5rem` | `0.375rem` |
| `semantic.typography.fontSize` | *(non esiste)* | `1rem` | `0.875rem` |
| `semantic.iconSize` | — | `1rem` | `0.875rem` |
| `semantic.list.option.padding` | — | `0.5rem 0.75rem` | `0.25rem 0.625rem` |

Quindi passare allo standard **rimpicciolirebbe** la UI di circa il 12%, non la
ingrandirebbe. Su una UI già volutamente densa è una proposta molto meno
allettante di come §6.5 la descriveva: vedi §6.5 riscritta.

**La mitigazione esiste e il nome esatto ora è noto** (non più da indovinare):
`@primeuix/themes/aura-compat` — la cartella `dist/aura-compat/` c'è, e
l'`exports` map espone `./*`. Confronto dei token, albero completo appiattito:

| Confronto | Token in comune | Valore cambiato |
| --- | --- | --- |
| v2 `aura` → v3 `aura-compat` | 2122 | **2** |
| v3 `aura-compat` → v3 `aura` | 3008 | 345 |

**Due token su 2122**, ed entrambi sono
`components.datatable.headerCell.selected{Background,Color}`
(da `{highlight.*}` a `{content.*}`: lo sfondo dell'intestazione di colonna
quando la colonna è selezionata). Tutto il resto è identico al bit.

L'insidia che restava — la v3 **introduce** `semantic.typography.fontSize`, un
token che nella v2 non esiste, quindi potrebbe imporre una dimensione dove prima
si ereditava — è stata controllata: `body` in `main.css` **non ha** una
`font-size` propria ed eredita i 16px del browser, e `aura-compat` mette
esattamente `1rem`. Delta zero regge anche lì.

> I 978 token «rimossi» e 886 «aggiunti» fra v2 e v3 **non sono perdite**: è una
> ristrutturazione: `semantic.colorScheme.light.surface.*` → `semantic.surface.*`.
> Il livello `colorScheme` è stato appiattito, i valori sono gli stessi.

### R2 — primeicons 8 e i 28 codepoint cablati ✅ ANNULLATO

Le icone composite di dominio (`.app-nav-icon-*`, frontend-standards
§"Iconografia di dominio") **non** usano le classi `pi-*`: incollano il glifo
con `content: "\eXXX"`. Se v8 avesse rinumerato i codepoint, quelle icone
sarebbero diventate **glifi sbagliati in silenzio**.

**Non li ha rinumerati.** Lo script di §6.3 è stato puntato sul
`primeicons.css` della **8.0.0 estratta dal tarball**, senza installarla:

- **28 codepoint su 28** risolvono a un'icona esistente;
- **zero drift** rispetto alla baseline presa su primeicons 7;
- la v8 è **additiva**: da 314 a **359** icone `.pi-*`.

Il changelog mancante non serve più: la domanda a cui doveva rispondere ha già
una risposta misurata. Il rischio è **nullo**, non «basso».

### R3 — `pinia._s` nel plugin auto-reset ✅ RISOLTO (2026-07-29)

**Testo originale**: `src/core/pinia-plugins/auto-reset.js:91` itera `pinia._s`
— **API privata** (la mappa interna degli store). Pinia 4 non promette nulla al
riguardo. Se cambia, il reset degli store `userScoped` al logout smette di
funzionare, e il sintomo è **silenzioso**: l'utente B vede filtri e cache
dell'utente A sullo stesso browser.

**Come è andata**: il rischio non si è materializzato — su Pinia 4 `_s` esiste
ancora ed è ancora iterabile. Il plugin è stato comunque riscritto su sola API
pubblica (registro proprio degli store) e il caso è ora coperto da
`frontend/scripts/check-pinia-user-scoped-reset.mjs`. Dettaglio in §9.

⚠️ **La lezione che ha guidato la seconda passata** è nata qui: la gravità di R3
non stava nella probabilità della rottura, ma nel fatto che **il sintomo era
silenzioso e non c'era modo di accorgersene**. La mitigazione giusta non è
sperare, è costruire il controllo meccanico *prima* di aggiornare — che è
esattamente ciò che è stato poi fatto per R1, R2, R4 e R5.

### R4 — Le 364 variabili `--p-*` 🟢 MISURATO, nessuna sparisce

Rischio che la prima stesura non aveva visto (§2-bis). La ristrutturazione dei
token poteva rinominare le variabili CSS generate, e 51 file le usano dirette.

Verificato ricostruendo i nomi variabile dai path dei token, **con validazione
dell'algoritmo sul preset in uso oggi** (88.9% di copertura sulle 63 usate; le 7
non ricostruite sono state escluse dal confronto invece di essere date per
buone). Sulle **56 verificabili: nessuna sparisce**, né in `aura-compat` né
nello standard.

> Le 7 escluse meritano un'occhiata a sé, ma **non** come parte della
> migrazione: `--p-info-color` (9 usi), `--p-warn-color`, `--p-font-family`
> (usata da `body`) e `--p-content-color-muted` non risultano fra i token del
> preset Aura **nemmeno oggi**. Se davvero non esistono, sono riferimenti già
> morti che ripiegano in silenzio sul default — un difetto attuale, non una
> conseguenza della v5.

### R5 — Le 48 classi interne `.p-*` 🟠 il residuo vero

L'altro aggancio invisibile (§2-bis): il nostro CSS aggancia 48 classi generate
da PrimeVue, e le due più usate sono quelle del **kebab**, che la v5 ha
riscritto (nuovo multi-livello).

Verificato che i nomi esistano ancora nel sorgente della 5.0.0 — **con
controprova**, che è ciò che rende il risultato utilizzabile:

- 43 su 48 compaiono nel sorgente v5;
- le 5 che non compaiono (`.p-dark`, `.p-row-toggler`, `.p-datatable-row-odd`,
  `.p-paginator-element`, `.p-confirmdialog-mask`) **non compaiono nemmeno nella
  4.5 installata** → non sono una regressione della v5, sono classi composte a
  runtime o selettori già morti.

**Delta v4 → v5 sui nostri agganci di classe: zero.**

Ma qui la misura arriva al suo limite, e va detto: *«la classe esiste nel
sorgente»* non è *«la classe sta sullo stesso elemento, allo stesso livello di
annidamento»*. Un `.p-menu-item-link` che in v5 finisce dentro un wrapper in più
esiste ancora, e il nostro selettore discendente continua a prenderlo — ma un
combinatore figlio diretto (`>`) o una regola su `:first-child` no.

**Questo è l'unico rischio del piano che nessuna analisi statica può chiudere.**
Si chiude guardando il kebab aperto a video: §6.4, verifica n. 1.

---

## 5. Step 0 — gli smoke Playwright: ritirato

> **La prima stesura consigliava mezza giornata di Playwright come rete di
> sicurezza prima di toccare PrimeVue. Non lo consiglio più.** Non perché sia
> una cattiva idea in sé, ma perché la ragione per cui la proponevo è caduta.

**La motivazione era questa** (testo originale): *«Il valore non è l'assert: è
lo screenshot diff. Trasforma "riguardati tutta l'app e spera di accorgerti che
le tabelle sono cresciute" in "guarda questi tre screenshot che sono cambiati" —
ed è esattamente il tipo di regressione che R1 produce.»*

Quella frase descrive **R1**. Ma R1 oggi è un delta di **2 token su 2122**,
misurato in Node in un secondo senza browser (§4). Spendere 150-300 MB di
browser e mezza giornata per intercettare una cosa che si intercetta gratis è
cattivo affare — e il piano si sarebbe portato dietro un'infrastruttura per una
regressione che non può avvenire.

**E per il residuo che resta davvero — R5, gli agganci di classe — lo screenshot
è comunque lo strumento sbagliato**, per un motivo che il piano scriveva già da
sé: il DB di dev è «magro e variabile». Uno screenshot asserisce **ogni pixel,
dati compresi**. Righe che cambiano fra due esecuzioni = diff a ogni
esecuzione = rumore che si impara a ignorare — cioè esattamente il fallimento
contro cui la prima stesura metteva in guardia, tre righe più in basso. La
domanda di R5 è *«i nostri selettori agganciano ancora?»*, e la risposta si dà
con un'**asserzione sul DOM**, non con un confronto di immagini.

**Cosa fare invece**: §6.4 con `aura-compat` e le 6 schermate a occhio. Contro
un residuo ristretto a un componente, mezz'ora di occhi è proporzionata;
un'infrastruttura no.

### Playwright resta una discussione aperta — ma separata

Il fatto sotto è vero e non cambia: **il progetto non ha alcun test frontend**,
niente vitest, niente playwright. La verifica di qualunque modifica FE è oggi
«build verde + occhio di Tid». È una lacuna che esiste **a prescindere da questa
migrazione** e che questa migrazione non è il momento giusto per colmare:

- comprare Playwright **per coprire un upgrade** è cattivo rapporto
  costo/beneficio, e lo si giudica su un rischio che ormai è misurato;
- comprarlo **come banco di prova del frontend** è una decisione a sé, che si
  giudica sui suoi meriti e con calma.

Da non confondere: sono due spese diverse con due giustificazioni diverse.

Se e quando si farà, valgono le regole che la prima stesura aveva già scritto
bene, e che restano: pochi test, sul **telaio** e non sul dominio (quello è già
coperto dai 38 smoke BE), niente asserzioni su testi di dominio, niente
dipendenze dall'ordinamento, **niente `sleep` fissi**, e niente asserzioni sul
*contenuto* dei dati («la tabella ha righe» sì, «la tabella ha 5 righe» no).
Costo: `@playwright/test` come devDependency + download browser (~150-300 MB in
`~/.cache/ms-playwright`; su questa macchina non c'è alcun browser headless) →
decisione sulle dipendenze, **ok esplicito di Tid**.

---

## 6. Gli step

**Prerequisito comune**: working tree pulito (`git status`) e branch dedicato.

```bash
git switch -c chore/upgrade-primevue-5
cd frontend
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use --lts
```

### 6.1 — Pinia 4 ✅ ESEGUITO il 2026-07-29 (dettaglio in §9)

```bash
npm i pinia@^4 @vue/devtools-api
./node_modules/.bin/vite build
npm run lint
```

`@vue/devtools-api` va installato **esplicitamente**: in Pinia 4 non è più una
dipendenza transitiva. L'altra novità è che il pacchetto è **ESM-only** (per noi
irrilevante: Vite lo è già).

**Verifica del reset user-scoped** — ora è meccanica e va tenuta verde:

```bash
node scripts/check-pinia-user-scoped-reset.mjs     # 9/9, exit 0
```

Se va rosso, al logout i dati dell'utente precedente restano in memoria:
**non proseguire**.

Controprova in-app — **fatta il 2026-07-29, superata**. Va rifatta solo se si
tocca `auto-reset.js` o il flusso di logout, perché lo script non copre né il
logout vero né i 39 store reali con i loro `clearUserState`:

1. login utente A;
2. applica filtri su una lista (es. clienti: ricerca + filtro data);
3. **logout**;
4. login utente B;
5. **i filtri devono essere spariti.**

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

### 6.3 — primeicons 8 ⛔ ESEGUITO E ANNULLATO il 2026-07-29 (vedi §1-bis)

> **Tecnicamente era andato tutto bene**: 28/28 codepoint risolti, zero drift,
> exit 0, build e lint verdi, i cinque file di font emessi nel bundle —
> esattamente come la verifica sul tarball aveva previsto (§4-R2).
>
> **È stato annullato per la licenza, non per un difetto**: primeicons 8 non è
> più MIT (§1-bis). Ripristinata la 7.0.0 con la procedura di §7. Lo step resta
> scritto qui perché la parte tecnica è valida e riutilizzabile se un giorno la
> questione di licenza si risolve.
>
> ⚠️ **Lezione**: erano state verificate tre cose — codepoint, nomi di classe,
> font nel bundle — e **non** il campo `license`. Per un progetto open source
> è la domanda più basilare delle quattro, ed è l'unica che sarebbe bastata da
> sola a fermare lo step. Vedi la trappola aggiunta in §8.

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

> ⚠️ Limite dello script, da conoscere: il controllo `[!]` (glifo cambiato)
> funziona solo dove il commento inline `/* pi-nome */` dichiara l'intenzione, e
> in `main.css` ce l'hanno **10 codepoint su 28**. Per gli altri 18 la rete è il
> confronto con la baseline — che li copre, ma solo finché la baseline resta
> allineata. Annotare i 18 mancanti è lavoro da mezz'ora che renderebbe il
> controllo pieno.

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

**Il nome dell'export è `aura-compat`** — verificato sul tarball della 3.0.0
(cartella `dist/aura-compat/`, esposta dall'`exports` map via `./*`), non più
da indovinare:

```js
import Aura from '@primeuix/themes/aura-compat'
```

Nient'altro cambia: `preset: Aura`, `darkModeSelector` e `locale` restano
identici. Conferma di sanità dopo l'installazione, se vuoi:

```bash
ls node_modules/@primeuix/themes/dist/ | grep compat    # deve elencare aura-compat
```

Poi:

```bash
./node_modules/.bin/vite build
npm run lint
```

**Verifica a video** — le schermate a più alta densità di componenti, in
quest'ordine. **Non è più un rastrellamento a tappeto**: dopo §4 l'ordine
riflette il rischio residuo misurato, e la n. 1 è quella che conta davvero,
perché è l'unica che chiude R5.

| # | Cosa | Perché proprio questa |
| --- | --- | --- |
| 1 | **Kebab di riga**, inline (desktop) e compact (<1024px) | ⬅ **la verifica che chiude R5**. `Menu` in v5 ha il multi-livello nuovo, e il nostro CSS aggancia `.p-menu-item-link` / `.p-tieredmenu-item-link` (26 usi). I nomi esistono ancora in v5, ma nessuna analisi statica dice se stanno sullo stesso elemento. Usato da `RowActionsMenu`, `PageActionsBar`, `DrawerActionsBar`: è in **ogni riga di ogni lista** |
| 2 | Una lista configurabile (clienti, contratti) | `DataTable` + paginator + ritiro colonne responsive; il nostro CSS aggancia `.p-datatable-tbody/thead/table` e `.p-paginator` |
| 3 | Un drawer con tab (`LottoDrawer`) | `Tabs`/`TabPanel` + `DataTable` annidata (agganciamo `.p-tabs`, `.p-tabpanels`, `.p-tablist`) |
| 4 | Un `AppDialog` con footer | `Dialog` + `FormFooter` |
| 5 | Un toast di successo e uno di errore | Toast ha animazioni nuove |
| 6 | Il login | l'unica schermata senza sidebar/topbar; aggancia `.p-password-input` (10 usi) |

**Cosa NON serve più cercare**, perché è già misurato (§4): che le proporzioni
siano cambiate (2 token su 2122), che i colori siano saltati (nessuna `--p-*`
sparisce), che un componente non esista più (47 moduli su 47 presenti).
Cercarlo comunque non fa danno, ma sapere dove *non* guardare è ciò che rende
mezz'ora sufficiente.

Commit: `chore(fe): primevue 5 + themes 3 (preset aura-compat)`.

### 6.5 — (separato, non ora) dal `compat` allo standard

⚠️ **Correzione**: la prima stesura diceva «significa accettare che tutta la UI
cresca di ~14%». **È il verso opposto** — vedi §4-R1. Passare allo standard
**rimpicciolisce** la UI di circa il 12%: la v5 riscala i token verso il basso
(`formField.paddingY` `0.5rem` → `0.375rem`, `typography.fontSize` `1rem` →
`0.875rem`) perché a un root di 16px riproducano l'aspetto che la v4 dava a
14px.

Questo cambia la natura della decisione, non solo un numero. Su una UI
**deliberatamente densa** — tabelle compatte, paginator ridotto,
`--app-font-size-base: 0.875rem` — «tutto più piccolo del 12%» è una proposta
molto meno attraente di «tutto più grande del 14%»: si andrebbe verso il limite
di leggibilità, non lontano da esso.

Il che rende questo step non tanto «da rimandare» quanto **da valutare se farlo
affatto**. `aura-compat` non è un ripiego temporaneo da smaltire: è il preset
che conserva le dimensioni che abbiamo scelto. Se un giorno lo si vuole
abbandonare, va fatto come **decisione di design** («vogliamo la UI più
compatta?») e non come debito di migrazione da chiudere.

**Non mescolarlo con l'upgrade** in nessun caso: sono due cose diverse che si
romperebbero a vicenda nella diagnosi.

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
- **Non fidarsi nemmeno dell'analisi statica, oltre il suo limite.** Le misure
  di §4 dicono che un nome (token, variabile, classe) **esiste ancora**. Non
  dicono **dove sta**: una classe spostata di un livello di annidamento supera
  il controllo e rompe lo stile lo stesso. È esattamente il residuo R5, ed è il
  motivo per cui la verifica n. 1 di §6.4 non è saltabile.
- **Misura prima di installare.** `npm pack` + `tar` costano dieci secondi e
  rispondono a domande che il piano rimandava al «dopo l'upgrade», quando
  costano un rollback (ricetta in §4). Vale per qualunque major, non solo
  questa.
- 🔴 **Guarda la licenza PRIMA di tutto il resto.** È l'errore commesso il
  2026-07-29 con primeicons 8: verificati esaustivamente 28 codepoint, 124 nomi
  di classe e i font nel bundle — e mai il campo `license`. Su un progetto
  open source è la domanda **più basilare**, ed è l'unica che da sola avrebbe
  fermato lo step. Costa un comando, e va **prima** di ogni analisi tecnica,
  perché se fallisce rende inutile tutto quello che viene dopo:

  ```bash
  for p in primevue@5 @primeuix/themes@3 primeicons@8; do
    printf "%-26s %s\n" "$p" "$(npm view "$p" license)"
  done
  ```

  Se esce qualcosa di diverso da una licenza OSI nota (`MIT`, `Apache-2.0`,
  `BSD-*`) — e in particolare `SEE LICENSE IN LICENSE.md` — **fermati e leggi
  il `LICENSE.md`** prima di scrivere una riga.
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

## 8-bis. «Non possiamo restare sulla 4.x per sempre» — quanto è vero

Obiezione di Tid, giusta. Risposta con numeri invece che con rassicurazioni.

### Il muro è reale ma lontano

- **MIT non si revoca**: `primevue` 4.5.5 resta MIT per sempre. Si perdono le
  correzioni future, non il diritto d'uso.
- **Il vincolo tecnico vero è Vue**: `@primevue/core` 4.5.5 chiede
  `vue: ^3.5.0` e siamo su 3.5.40. Finché Vue 3.5 è la linea corrente, la 4.5.5
  non ha scadenza tecnica. Il muro è **Vue 4**, non il mese prossimo.
- **È presentazione, non sicurezza**: congelare un layer di componenti
  client-side ha un profilo di rischio molto diverso dal congelare un framework
  server o una libreria di auth. Non è zero, ma non è quello che tiene svegli.

### Il costo di uscita è sbilanciato, e questo è il dato utile

941 import su 47 componenti distinti, ma **11 coprono l'80%**:

| Gruppo | Import | Difficoltà di sostituzione |
| --- | --- | --- |
| Primitivi (`tag`, `button`, `inputtext`, `select`, `toggleswitch`, `inputnumber`, `message`) | ~449 | **Bassa** — ce li ha qualunque libreria: rinomina + mappatura prop |
| `datatable` + `column` | **164 in 77 file** | **Alta** — è il componente che nessuno replica bene |
| Coda lunga (22 componenti usati in ≤2 posti) | poche decine | Trascurabile |

**Il costo di lasciare PrimeVue è quasi tutto in DataTable.**

### Il numero scomodo, ed è anche la leva

| | File |
| --- | --- |
| Usano `DataTable` **grezza** | **77** |
| — di cui sono i **wrapper stessi** (giusto che la usino) | 6 |
| **Bersaglio reale** | **71** |
| Passano dal nostro `<ListaConfigurabile>` | **14** |

Lo standard di casa ([[feedback_lista_pattern_standard]]) esiste ma copre meno
di un quinto delle liste. E i 71 non sono omogenei: **34 sono liste vere** (col
paginator, bersaglio naturale del BB) e **37 sono tabelle annidate** dentro
drawer e dialog, che vogliono un trattamento diverso. Elenco completo e
spuntabile più sotto.

### La mossa: non decidere, comprare opzioni

Quel 14 contro 71 è insieme il problema e la risposta. **Ogni lista spostata su
`ListaConfigurabile` riduce il costo di qualunque futuro cambio di libreria**,
senza impegnare a nulla — ed è una cosa già voluta per conto suo (coerenza,
niente duplicazione).

Non serve un progetto di migrazione: serve che, ogni volta che si tocca una
lista per altri motivi, la si faccia passare di lì. Stessa logica per i
primitivi, con un sottile strato nostro davanti dove capita di passarci.
Invertito quel rapporto, «lasciamo PrimeVue?» diventa una decisione normale
invece di un salto nel vuoto — **ed è utile anche se PrimeVue non si lascia
mai**.

### Inventario — le liste da migrare, una alla volta

> Elenco generato il 2026-07-29, da ri-generare quando serve:
>
> ```bash
> cd frontend
> grep -rl "from 'primevue/datatable'" src --include=*.vue | sort
> ```
>
> **Come usarlo**: non è un progetto da aprire. È una lista di spunta da
> consumare **quando tocchi quel file per altri motivi**. Ogni riga barrata
> abbassa il costo di un eventuale addio a PrimeVue e, indipendentemente da
> quello, riporta la lista sullo standard di casa
> ([[feedback_lista_pattern_standard]]).
>
> ⚠️ Prima di migrarne una, leggere il contratto di `<ListaConfigurabile>` nel
> catalogo BB FE: se la lista ha bisogno di qualcosa che il BB non copre, la
> risposta giusta è **estendere il BB**, non tornare alla `DataTable` grezza.
> Altrimenti fra un anno questo elenco è di nuovo lungo 71.

Totale file con `DataTable` grezza: **77**, di cui **6** sono i
wrapper stessi (giusto che la usino) → **bersaglio reale: 71**.

#### Cosa serve davvero per convertire una lista (leggere prima di iniziare)

⚠️ **`<ListaConfigurabile>` non è uno scambio di componente.** Il BB è
parametrizzato dalla configurazione risolta dal BE
(`ui.fn_resolve_lista_config`), quindi ogni lista ha bisogno del proprio
**`codice`** registrato: una riga in `ui.lista_definizione` + N righe in
`ui.lista_colonna` (facoltative: `lista_colonna_permesso` per le colonne
riservate a profilo, `lista_preset` per i preset di colonne).

**La configurazione la crei tu, senza aspettare nessuno.** Esiste
l'amministrazione in-app: `ListaDefinizionePanel`, `ListaColonnaPanel`,
`ListaColonnaPermessoPanel`, `ListaPresetPanel`, con gli endpoint
`ApiAdminListaDefinizione*`. È **dato, non DDL** — nessun brief, nessun blocco.

🔵 **Va comunque seedato in Liquibase, altrimenti vive solo nel tuo DB.** Le 11
liste già configurate sono anche nei CSV di seed: una lista creata soltanto
dall'app **sparisce su un'installazione pulita**. Ma il seed è più leggero di
quanto sembri.

> ⚠️ **Rettifica 2026-07-30.** Una stesura precedente di questa sezione diceva
> che «ogni lista migrata prima o poi vuole il suo changeset di seed». **È
> sbagliato**: non serve alcun changeset nuovo. Tutti e quattro i loader sono
> `runOnChange: true` + `validCheckSums: ANY` + `loadUpdateData`, cioè **mirror
> vivi dei CSV**, progettati per rigirare a ogni modifica del file (lo dice il
> commento di `20260507-07`). **Appendere le righe basta**: il loader le
> ripesca, i checksum non si rompono.
>
> | CSV in `80_data/sql/ui/` | Loader | Chiave |
> | --- | --- | --- |
> | `lista_definizione.csv` | `20260507-06` | `id` |
> | `lista_colonna.csv` | `20260507-07` | `id` |
> | `lista_preset.csv` | `20260507-08` | `id` |
> | `lista_preset_colonna.csv` | `20260507-09` | `preset_id,colonna_id` |
>
> Resta lavoro da concordare col team DB perché sono file sotto `db/`
> ([[feedback_db_actions_passaggio_team]]) — ma è una **revisione di righe CSV**,
> non una migrazione da scrivere. E si consegna a lotti per dominio, non una
> lista per volta.

⚠️ **Non fidarsi dei changeset `priorita` come modello.** Esistono
`20260603-15` (ordini), `20260709-17` (DDT) e gemelli che impostano `priorita`
con un `UPDATE` dedicato, e il loro commento diceva che la colonna «non vive nel
CSV». **Era vero quando sono stati scritti, non più**: il loader `20260507-07`
espone tutte e 24 le colonne, `priorita` compresa, e il CSV ne porta i valori
(verificato: per `vendite.ddt` il CSV ha 100/95/90… allineati al DB). Quei
changeset sono oggi **ridondanti ma idempotenti**. Il commento fuorviante è
stato rettificato in entrambi i file il 2026-07-30. **Per una lista nuova non
replicarli**: `priorita` si valorizza direttamente nel CSV.

**Dimensione dell'impegno, misurata**: il Gruppo A è **34 liste / 269 colonne**,
contro le 204 colonne delle 11 liste attuali (media 18,5). Il seed finale **più
che raddoppia** la configurazione esistente — ed è la ragione per cui esiste il
generatore (più sotto), non per cui va temuto.

**I cinque prerequisiti tecnici**, da verificare riga per riga:

| # | Prerequisito | Perché |
| --- | --- | --- |
| 1 | **Endpoint paginato server-side** | il BB ha `lazy` **fisso**, non parametrico: senza paginazione server-side non si monta |
| 2 | **Codici colonna == campi dell'API** | il BB rende `data[codice]`: il nome è un contratto, non un'etichetta |
| 3 | **Display field risolti dal BE** (JOIN) | niente lookup client-side, altrimenti la colonna mostra un id ([[feedback_display_fields_backend]]) |
| 4 | **Il caller resta padrone dei dati** | fornisce `rows`/`total`/`loading` e gestisce `@page`/`@sort`; il BB **non fa fetch** |
| 5 | **Rendering custom via slot** | `cell-{codice}` per la cella, `actions` + `RowActionsMenu` per le azioni di riga |

🔴 **Quattro liste del Gruppo A non soddisfano il prerequisito 1** (colonna
`Lazy` = «—»): richiedono **prima** un endpoint paginato lato BE, quindi non
sono spuntabili «di passaggio» come le altre —
`ArticoloBomDrawer`, `ContrattiBillingAccountDrawer`, `ContrattoRigheDrawer`,
`OffertaEccezioniDrawer`.

#### Il generatore: `scripts/gen_seed_lista.py`

Compilare 269 colonne a mano è lavoro meccanico, e il meccanico si genera. Lo
script legge il `.vue` con le `<Column>` attuali e produce le righe pronte per i
quattro CSV di seed.

```bash
backend/.venv/bin/python scripts/gen_seed_lista.py \
    --codice catalogo.uom_tipi --descrizione "Tipi unità di misura" \
    --vue frontend/src/catalogo/components/UomTipiSearchTable.vue
```

**Non scrive sul DB e non applica nulla**: stampa righe da rivedere
([[feedback_db_actions_passaggio_team]]).

⚠️ **Quello che esce è strutturalmente corretto e semanticamente una bozza.**
La distinzione è la cosa da tenere a mente:

| Lo fa lo script | Resta da curare a mano |
| --- | --- |
| Le 4 tabelle e i loro collegamenti | `codice` logico vs `campo_sorgente`: lo script *propone* togliendo i suffissi, ma il nome è una scelta di presentazione |
| Gli `id`, oltre il massimo fra CSV **e DB** | `priorita` (ritiro responsive), `gruppo`/`gruppo_ordine`, `larghezza_default` |
| L'ordine delle colonne visibili, preso dal `.vue` | `sensibile`, `ricercabile_full` |
| Chiavi i18n ed etichette risolte da `it.json` | `formato`, se il `.vue` usa un formatter non riconosciuto |
| `tipo_dato` e allineamento — **dedotti dal DB**, vedi sotto | I `tipo_dato` **ambigui**, che lo script rifiuta di indovinare e segnala |
| Quali colonne sono visibili nel preset di default | **Le colonne extra invisibili**: lo script *non* le aggiunge — sceglierle è progettazione |
| La colonna `azioni` (`tipo_colonna='azione'`) e le colonne **calcolate FE** (senza `field=`, `campo_sorgente` vuoto) | Se una calcolata ha in realtà un campo sorgente, indicarlo |
| `tipo_colonna='identificatore'` sulla prima colonna | Confermare che sia davvero quella da non poter nascondere |

Il risparmio è sulle righe da compilare, **non sulle decisioni**. Ogni
esecuzione stampa in coda l'elenco di ciò che è uscito coi default, invece di
far finta di saperlo.

##### Non rifare due volte lo stesso lavoro

L'allineamento si fa a più mani e su più giorni, e la configurazione di una
lista si può creare anche **dai pannelli di amministrazione in-app** — dove
però vive solo nel DB di chi l'ha fatta. Lo script parte quindi sempre da cosa
esiste già, nei CSV e nel DB:

```bash
# fotografia di tutte le liste: seedate, fatte in-app, divergenti
backend/.venv/bin/python scripts/gen_seed_lista.py --stato

# recupera in CSV il lavoro già fatto (non lo rigenera: lo esporta dal DB)
backend/.venv/bin/python scripts/gen_seed_lista.py --esporta catalogo.uom_tipi
```

- **Generare una lista che esiste già non parte**: lo script dice dov'è e
  rimanda a `--esporta` (`--forza` solo per ripartire davvero da capo).
- `--esporta` emette **solo ciò che manca ai CSV**, quindi rilanciarlo non
  duplica niente; le righe con la stessa chiave ma valori diversi le elenca a
  parte, da **sostituire** in place — appenderne una seconda con lo stesso `id`
  renderebbe ambiguo `loadUpdateData`.
- Gli `id` nuovi si allocano oltre il massimo fra CSV **e** DB: due persone che
  lavorano in parallelo non si scavalcano.

⚠️ **Un file `.vue` può contenere più `<DataTable>`** (tabella principale +
riga di espansione, o più schede). Lo script legge solo quella scelta da
`--tabella` (default: la prima) e dichiara in coda quante colonne ha lasciato
fuori. Fonderle produrrebbe una lista sbagliata e `codice` duplicati.

> **`tipo_dato` viene dal DB, non da un default.** Una prima versione lo lasciava
> `string` quando la lista non dichiarava una sorgente — cioè quasi sempre, dato
> che per il Gruppo A una `vw_*` dedicata in genere non esiste. Era il difetto
> peggiore di tutti perché **silenzioso**: una colonna con `tipo_dato` sbagliato
> non dà errore, semplicemente non ordina e non filtra come dovrebbe, e te ne
> accorgi settimane dopo.
>
> Ora lo script cerca ogni campo **per nome** fra tutte le tabelle e viste del DB
> e ne prende il tipo, con una regola di sicurezza: **lo accetta solo se non
> ambiguo**. Misurato il 2026-07-30, dopo la mappatura a `ui.tipo_dato`,
> **1567 nomi su 1588 (98,7%)** risolvono a un tipo solo — l'ambiguità dei tipi
> PG sparisce perché `varchar`, `text` e `char` mappano tutti su `string`. Lo
> schema della lista ha la precedenza sugli altri. I ~21 residui (`id`, `numero`,
> `data_evento`, `split_payment`…) restano `string` e vengono **elencati come
> decisione aperta**, non indovinati.
>
> Effetto su una lista vera (`LottiListView`): `competenza_mese` → `date` con
> `formato=date_short`, `data_insert` → `datetime`, `attivo` → `boolean` con
> allineamento `center`.
>
> Passare `--sorgente schema.oggetto` (**tabella oppure vista**: per
> `information_schema` sono la stessa cosa) resta preferibile quando la sorgente
> è nota — dà i tipi certi invece che dedotti, e propone i campi non usati come
> candidati per le colonne invisibili.
>
> **Perché la fonte è il `.vue` e non la vista DB.** La prima versione dello
> script generava le colonne introspezionando `vista_sql`. L'autoverifica su
> liste già configurate l'ha bocciata: `vendite.ddt` ha **24 colonne
> configurate contro 63 esposte dalla vista**, e 8 di quelle configurate —
> `stato`, `valuta`, `pratica`, `azioni` — nella vista **non esistono**. Il
> motivo è che `ui.lista_colonna.codice` è un nome **logico** e
> `campo_sorgente` la colonna fisica (`stato` → `stato_descrizione`): **61
> colonne su 204** differiscono. Generare dalla vista avrebbe prodotto 63
> colonne coi nomi sbagliati e perso comunque `azioni`.
>
> Resta utile passare `--vista` quando esiste: dà i tipi veri (niente
> `string` ovunque) e propone i campi non usati come candidati. Ma per il
> Gruppo A una vista dedicata in genere **non c'è**.
>
> L'autoverifica è riutilizzabile e va rilanciata se si tocca il generatore:
>
> ```bash
> backend/.venv/bin/python scripts/gen_seed_lista.py --verifica vendite.ddt
> ```

#### Non toccare — sono lo strato, non i clienti

- `core/components/ConfigTablePanel.vue`
- `core/components/details/SearchDetailTable.vue`
- `core/components/GeoSearchTable.vue`
- `core/components/ListaConfigurabile.vue`
- `core/components/RigheMasterDetailTable.vue`
- `core/components/SearchDrawer.vue`

#### Gruppo A — liste vere (34 file, hanno il paginator)

Sono il bersaglio naturale di `<ListaConfigurabile>`: ordinate dalla più
semplice alla più complessa, così le prime servono da rodaggio.

| ✓ | File | Col. | Lazy |
| --- | --- | --- | --- |
| ☐ | `catalogo/components/UomTipiSearchTable.vue` | 4 | sì |
| ☐ | `amministrazione/components/CategorieClientiSearchTable.vue` | 5 | sì |
| ☐ | `amministrazione/components/EmittenteFiscaleBillingAccountTab.vue` | 5 | sì |
| ☐ | `amministrazione/components/UtilitiesTipiRuoloSearchTable.vue` | 5 | sì |
| ☐ | `amministrazione/views/AuditLogView.vue` | 5 | sì |
| ☐ | `anagrafiche/components/IndirizziSearchTable.vue` | 5 | sì |
| ☐ | `vendite/views/ApprovazioniPrezzoListView.vue` | 5 | sì |
| ☐ | `amministrazione/views/EmailAccountsListView.vue` | 6 | sì |
| ☐ | `amministrazione/views/EmailTemplatesListView.vue` | 6 | sì |
| ☐ | `amministrazione/views/EmittentiFiscaliListView.vue` | 6 | sì |
| ☐ | `catalogo/components/ArticoloBomDrawer.vue` | 6 | — |
| ☐ | `catalogo/components/ConversioniUomSearchTable.vue` | 6 | sì |
| ☐ | `catalogo/components/UnitaMisuraSearchTable.vue` | 6 | sì |
| ☐ | `vendite/components/VersioneDrawer.vue` | 6 | sì |
| ☐ | `amministrazione/views/EmailLogsListView.vue` | 7 | sì |
| ☐ | `config/components/TemplateDocumentiSearchTable.vue` | 7 | sì |
| ☐ | `config/components/TemplateAssetSearchTable.vue` | 8 | sì |
| ☐ | `pratiche/components/PraticheSearchTable.vue` | 8 | sì |
| ☐ | `strumenti/components/CodaLavoriTab.vue` | 8 | sì |
| ☐ | `vendite/components/ContrattiBillingAccountDrawer.vue` | 8 | — |
| ☐ | `vendite/components/PromoArticoliSearchTable.vue` | 8 | sì |
| ☐ | `vendite/offerte/components/OffertaEccezioniDrawer.vue` | 8 | — |
| ☐ | `amministrazione/components/CategorieClientiListiniSearchTable.vue` | 9 | sì |
| ☐ | `amministrazione/components/TipiRuoloTipiIndirizzoSearchTable.vue` | 9 | sì |
| ☐ | `amministrazione/views/OperatoriListView.vue` | 9 | sì |
| ☐ | `catalogo/components/ArticoliSearchTable.vue` | 9 | sì |
| ☐ | `strumenti/components/CodaStampaTab.vue` | 9 | sì |
| ☐ | `vendite/components/CommessaGestioneDrawer.vue` | 9 | sì |
| ✅ 2026-07-31 | `vendite/views/LottiListView.vue` | 9 | sì |
| ☐ | `vendite/views/SituazioneApertaView.vue` | 10 | sì |
| ☐ | `vendite/components/ContrattoRigheDrawer.vue` | 11 | — |
| ☐ | `vendite/views/DashboardBacklogView.vue` | 11 | sì |
| ☐ | `vendite/components/ListiniSearchTable.vue` | 13 | sì |
| ☐ | `vendite/views/DashboardCompetenzaView.vue` | 23 | sì |

##### `vendite.lotti` — ✅ CONVERTITA il 2026-07-31, validata in-app da Tid

Prima conversione dell'inventario, fatta a perimetro pieno: ordinamento
server-side, export CSV/XLSX, personalizzazione colonne. **Le lezioni sotto
valgono per le prossime 33 e correggono tre affermazioni della stesura
precedente di questo stesso blocco.**

**Cosa è stato fatto** (2026-07-30/31, non committato):

- BE: `order_by`/`order_dir` su `ApiLottiList` (whitelist `LOTTI_SORT_COLUMNS`
  nel repository, tiebreak `fl.id`, fallback all'ordine storico) + endpoint
  `GET /vendite/lotti/export/` via `build_export_response`; parsing filtri
  **condiviso** fra lista ed export (`_parse_lotti_query`) — il contratto
  «l'export rispecchia la lista» vive in un parser solo;
- FE: store `vendite-lotti` (`userScoped`, converte `limit/offset` →
  `page/page_size` in `buildParams`) + view su `<ListaConfigurabile>` con
  `useListaConfigurabilePage`; 5 slot di cella, il resto lo rende il catalogo;
- seed: 11 colonne `ordinabile=t`; colonna `azioni` **disattivata**
  (`attivo=f` + preset `visibile=f`): l'unica azione era «apri», cioè il
  row-click — decisione Tid, si riattiva dal catalogo quando le azioni
  diventeranno più d'una;
- i18n: le 3 chiavi mancanti aggiunte a `it.json`/`en.json`;
- test: `test_lotti_lista_configurabile.py`, 5 test CI-safe che presidiano
  l'allineamento seed↔whitelist **in entrambi i versi**.

**Lezioni per le prossime conversioni:**

1. 🔴 **La whitelist di ordinamento si chiava sul `campo_sorgente`, MAI sul
   `codice` logico.** `<ListaConfigurabile>` monta le Column con
   `:field="col.campo_sorgente"`, quindi `event.sortField` → `order_by` porta
   il nome **fisico**. Chiavata sui codici, 4 colonne su 11 rispondevano 400 al
   primo click — trovato prima di arrivare a video solo per confronto con
   `_ORDER_COLS_CONTRATTI`. Replicare anche il **test di allineamento**
   seed↔whitelist: è l'invariante che nessun build rompe.
2. **«useListaConfigurabilePage non si applica alle liste cockpit» era
   sbagliato.** Bastava creare lo store col contratto atteso (`filters` con
   `limit/offset/order_by/order_dir/search`, `hasSearched`, `fetchList`):
   nessun wiring a mano. Vale per le altre 5 liste cockpit.
3. ⚠️ **Doppio `onActivated`**: `useSearchTable` ne registra uno proprio
   (refresh idempotente sulle riattivazioni) che parte PRIMA di quello della
   view. Senza guard su `store.loading` si fanno due fetch concorrenti; e il
   sync dei filtri della view deve azzerare `offset` **solo se un filtro è
   cambiato**, o l'operatore perde la pagina a ogni rientro nel tab.
4. **Export**: serve una porta di servizio dedicata (qui `fn_export_lotti`) —
   la funzione di lista passa da `validate_pagination`, che impone il tetto di
   200 righe e impedirebbe perfino di *rilevare* il superamento di
   `EXPORT_MAX_ROWS`.
5. **Colonna `azioni` senza azioni**: se il kebab non serve, disattivarla nel
   catalogo (`attivo=f`), non solo omettere lo slot — altrimenti resta
   riesumabile dalla personalizzazione come colonna vuota.

**Resta vero** dalla stesura precedente: le 3 colonne extra invisibili
(`area_geografica`, `stato_operativo`, `user_insert`) sono ciò che rende la
personalizzazione utile — l'endpoint le restituiva già.

#### Gruppo B — tabelle annidate (37 file, senza paginator)

Dentro drawer, dialog e pannelli. **Non** vanno su `ListaConfigurabile`:
il loro equivalente è `RigheMasterDetailTable` / `SearchDetailTable`, o
un wrapper sottile da estrarre alla seconda occorrenza
([[feedback_regola_del_2_estrai_bb]]).

| ✓ | File | Col. |
| --- | --- | --- |
| ☐ | `amministrazione/components/CollectionEditorPanel.vue` | 2 |
| ☐ | `amministrazione/components/UtilityTipoRuoloDrawer.vue` | 3 |
| ☐ | `amministrazione/views/RepartiProfiloView.vue` | 3 |
| ☐ | `core/components/ScadenzeSintesi.vue` | 3 |
| ☐ | `amministrazione/views/PermessiRiepilogoView.vue` | 4 |
| ☐ | `catalogo/components/UomConversioniDrawer.vue` | 4 |
| ☐ | `core/components/SessioniAttivePanel.vue` | 4 |
| ☐ | `vendite/components/AlertScadenzeWidget.vue` | 4 |
| ☐ | `vendite/components/ApplicaVariazioneDialog.vue` | 4 |
| ☐ | `vendite/components/AttivaVersioneDialog.vue` | 4 |
| ☐ | `vendite/offerte/components/OffertaDrawer.vue` | 4 |
| ☐ | `vendite/preventivi/components/PreventiviDrawer.vue` | 4 |
| ☐ | `amministrazione/components/RepartoProfiloEditor.vue` | 5 |
| ☐ | `core/components/RiepilogoIvaTable.vue` | 5 |
| ☐ | `ui/components/ListaColonnaPermessoPanel.vue` | 5 |
| ☐ | `vendite/preventivi/components/dialogs/PreventiviSmistamentoDialog.vue` | 5 |
| ☐ | `ui/components/ListaDefinizionePanel.vue` | 6 |
| ☐ | `vendite/ordini/components/dialogs/OrdineEvasioneDialog.vue` | 6 |
| ☐ | `amministrazione/views/DefinizioniWorkflowListView.vue` | 7 |
| ☐ | `catalogo/components/ArticoloUomDrawer.vue` | 7 |
| ☐ | `config/components/TemplateVersioniSection.vue` | 7 |
| ☐ | `core/components/NoteDrawer.vue` | 7 |
| ☐ | `documenti/components/DocumentiGeneratiSorgenteList.vue` | 7 |
| ☐ | `ui/components/ListaPresetColonneDrawer.vue` | 7 |
| ☐ | `amministrazione/views/DefinizioneEditorView.vue` | 8 |
| ☐ | `pratiche/components/PraticaFlussiTab.vue` | 8 |
| ☐ | `ui/components/ListaPresetPanel.vue` | 8 |
| ☐ | `vendite/_shared/componenti/ComponentiDialog.vue` | 8 |
| ☐ | `vendite/_shared/componenti/ComponentiPanel.vue` | 8 |
| ☐ | `vendite/components/FatturaDrawer.vue` | 8 |
| ☐ | `vendite/ddt/components/DdtResoDialog.vue` | 8 |
| ☐ | `vendite/resi/components/dialogs/ResoRiconsegnaDialog.vue` | 8 |
| ☐ | `amministrazione/components/EmittenteFiscaleUtilitiesTab.vue` | 9 |
| ☐ | `amministrazione/components/OperatorePermessiTab.vue` | 9 |
| ☐ | `config/components/ImpostazioniSearchTable.vue` | 9 |
| ☐ | `ui/components/ListaColonnaPanel.vue` | 9 |
| ☐ | `vendite/components/LottoDrawer.vue` | 11 |

### Le opzioni, per quando sarà il momento

Elencate perché siano note, non per sceglierne una ora:

1. **Restare sulla 4.5.5** congelata (MIT, nessuna scadenza fino a Vue 4).
2. **Accettare la Community License** — ZeroErp con ogni probabilità è idonea;
   ma va allora affrontata la GPL, e come titolare del copyright Tid può anche
   ri-licenziare il progetto.
3. **Licenza commerciale** — toglie il problema dell'idoneità, non quello
   della GPL verso valle.
4. **Migrare a un'altra libreria** — costo dominato da DataTable, vedi sopra.
5. **Fork comunitario della 4.x** — MIT lo consente a chiunque.

**Il segnale esterno da tenere d'occhio è il punto 5**: con una relicensing di
questa portata un fork è lo sbocco più probabile, e non dipende da noi. Da
notare che rende obsoleto il segnale di §1 («aspetta la prima 5.0.x»): quello
misurava l'adozione, e l'adozione ora è governata dalla licenza, non dalla
maturità.

---

## 9. Registro

### 2026-07-31 · Prima conversione dell'inventario: `vendite.lotti` — FATTA e validata

Prima lista del Gruppo A convertita a `<ListaConfigurabile>`, **a perimetro
pieno** (decisione Tid: ordinamento + export insieme alla conversione, non
rinviati). Validata in-app da Tid. Dettaglio e lezioni nel blocco
«`vendite.lotti` — CONVERTITA» sopra l'inventario; qui i fatti di processo:

- **Sequenza che ha funzionato**: prima il BE (ordinamento con whitelist +
  export), poi lo store, poi la view, poi seed/i18n — ogni strato collaudato
  prima di appoggiarci il successivo. 2200 test Django, build, lint, i18n
  verdi a ogni passo.
- **Un bug intercettato prima del video**: whitelist di ordinamento chiavata
  sul `codice` logico invece che sul `campo_sorgente` (lezione 1 del blocco).
  È nato un test CI-safe che rende l'errore impossibile da rifare in silenzio
  su questa lista, e il pattern va replicato sulle prossime.
- **Revisione critica a valle** (richiesta Tid): trovati e corretti il reset
  pagina a ogni rientro nel tab + doppio fetch concorrente (doppio
  `onActivated`), la duplicazione del parsing lista/export, e un commento che
  documentava la convenzione sbagliata. Nota lasciata agli atti: `onPage`/
  `onSort` di `useSearchTable` chiamano `fetchList` senza catch — pattern
  pre-esistente comune a TUTTE le liste standard, da valutare a parte.
- **Kebab rimosso** (decisione Tid): il row-click apre il drawer, l'unica
  azione era ridondante. Colonna `azioni` disattivata nel catalogo, chiave
  i18n orfana rimossa.
- Restano nel Gruppo A: **33 liste**. Le 4 senza endpoint paginato sono
  invariate (lotti era già lazy).

### 2026-07-29 · Il cambio di licenza — e il rollback di primeicons

**La scoperta è arrivata per caso, ed è la cosa più importante di tutta la
sessione.** Tid ha chiesto se anche `@primeuix/themes` 2→3 andasse rimandato.
Per rispondere con un fatto invece che con un'opinione è stato lanciato un
`npm i @primeuix/themes@^3 --dry-run` (che non modifica nulla), e l'output
mostrava l'arrivo di tre pacchetti che non c'entravano niente con un tema:
`@primeui/license-manager`, `@noble/ed25519`, `@noble/hashes`. Un verificatore
di **chiavi di licenza** con crittografia a firma.

Da lì: `primevue`, `@primeuix/themes` e `primeicons` sono **MIT** fino alla
versione precedente e passano tutti e tre alla **licenza PrimeUI** dalla nuova.
Dettaglio completo in **§1-bis**.

**Conseguenze immediate:**

1. **`primeicons` riportato da 8.0.0 a 7.0.0** con la procedura di §7 —
   `git checkout` di `package.json`/lock committati + `npm ci`, che ripristina
   *esattamente* il lock invece di risolvere di nuovo le versioni. Verificato
   dopo: le quattro dipendenze in gioco tornano tutte **MIT**,
   `@primeui/license-manager` assente, 28/28 codepoint verdi, reset user-scoped
   9/9 (Pinia 4 intatta), build e lint verdi.
2. **§6.4 non è più una questione tecnica.** Tutto il lavoro di misura di §4
   resta corretto e utile, ma non è più ciò che decide.
3. **Aggiunta §8-bis** per l'obiezione di Tid («non possiamo restare sulla 4.x
   per sempre»), con il costo di uscita misurato e la mossa che compra opzioni
   senza impegnare a nulla.

**L'errore, per iscritto perché non si ripeta.** Su primeicons 8 erano state
verificate esaustivamente tre cose — 28 codepoint, 124 nomi di classe, i font
emessi nel bundle — e **mai** il campo `license`. Su un progetto GPL pubblica
è la domanda più basilare delle quattro, l'unica che da sola avrebbe fermato lo
step, e costa un comando. Il pacchetto è stato installato prima che qualcuno la
facesse. Da qui la trappola aggiunta in §8: **la licenza si guarda per prima**,
perché se fallisce rende inutile tutta l'analisi tecnica che viene dopo.

Nota di merito: la scoperta **spiega retroattivamente** lo zero-patch su cui era
costruita §1. «Poca adozione» era la lettura giusta, ma la causa non era
l'acerbità della 5.0.0 — era la relicensing.

### 2026-07-29 · Step 6.2 + 6.3 eseguiti — primeicons 8 (poi annullati)

Decisione di Tid dopo la seconda passata: **staccare primeicons dal gruppo** e
farlo subito, tenendo fermo §6.4. La logica è che i due pacchetti hanno rischi
di natura diversa — quello che tiene fermo PrimeVue 5 è il rischio di un bug
*interno* alla libreria, che non puoi riparare e per cui non c'è evidenza di un
ciclo di fix reattivo (zero patch). Su primeicons quel rischio non esiste: è un
font più un foglio di stile, non ha logica, non entra nei componenti.

Sequenza eseguita, `primeicons` 7.0.0 → **8.0.0**:

1. **§6.2** — baseline riverificata su primeicons 7 **prima** di toccare
   qualunque cosa: verde, exit 0. Senza questo passo il confronto dopo non
   sarebbe esistito.
2. **§6.3** — `npm i primeicons@^8`, poi il controllo vero: **28/28 codepoint
   risolti, zero drift**, exit 0.
3. `vite build` verde, i 5 file di font emessi nel bundle; `npm run lint` verde.

**La previsione dal tarball ha retto al 100%**: stesso esito, stessi 28
codepoint, stessa assenza di drift. È la conferma che il metodo `npm pack` di
§4 non è un giochino — quella verifica *prima* di installare valeva esattamente
quanto la verifica *dopo*, ma senza impegno da sciogliere in caso di rosso.

**Nota di igiene**: `main.css` era stato modificato da Tid in parallelo (+58
righe, lavoro su altro). Verificato prima di procedere che il diff **non
toccasse** righe di codepoint o `.app-nav-icon-*` — altrimenti un rosso dello
script sarebbe stato ambiguo fra le due cause. I numeri di riga nel report sono
di conseguenza traslati rispetto alle passate precedenti.

**Residuo**: la verifica a video della sidebar documenti vendite (ogni voce col
proprio overlay) resta a Tid — è l'unica parte che nessuno script copre.

### 2026-07-29 (seconda passata) · I rischi misurati invece che stimati

Nata da una domanda di Tid: *«per PrimeVue 5 il consiglio era di fare degli
smoke Playwright, che dici?»*. Per rispondere serviva sapere quanto vale
davvero il rischio che quegli smoke dovrebbero coprire — e si è scoperto che si
poteva **misurare**, non stimare.

**Metodo**: i tre pacchetti scaricati con `npm pack` in una cartella temporanea
e interrogati **senza installarli** (`package.json`, lock e `node_modules`
intatti). Ricetta in §4.

**Cosa ne è uscito:**

| | Prima (stima) | Dopo (misura) |
| --- | --- | --- |
| R1 baseline font | 🔴 «la UI cresce del 14%» | 🟢 **verso sbagliato**: lo standard la *rimpicciolisce* del 12%; `aura-compat` = 2 token diversi su 2122 |
| R2 codepoint icone | 🟠 ignoto, changelog assente | ✅ **28/28 invariati, zero drift**; v8 additiva (314 → 359) |
| `--p-*` (R4) | non visto | 🟢 364 usi in 51 file, **nessuna variabile sparisce** |
| `.p-*` (R5) | non visto | 🟠 187 usi in 9 file, **zero regressioni di nome** — ma resta il residuo |
| import `primevue/*` | «260 file, campo minato» | 🟢 **47 moduli su 47** presenti in v5 |
| patch dopo la major | «1 per pacchetto» | **0** per tutti e tre |

**Tre conclusioni che hanno riscritto il piano:**

1. **Lo Step 0 Playwright è ritirato** (§5). La sua motivazione era R1, e R1 ora
   si misura in un secondo senza browser. In più, per il residuo che resta
   davvero (R5) lo screenshot è lo strumento *sbagliato*: asserisce ogni pixel
   dati compresi, e il DB di dev è magro e variabile — cioè produce proprio il
   rumore contro cui il piano stesso metteva in guardia. Playwright resta una
   discussione legittima, ma come **banco di prova del frontend**, decisione a
   sé e non spesa di migrazione.
2. **La raccomandazione «non ora» regge su una gamba sola** (§1). Non più
   freschezza + R1 + R2, ma solo freschezza — e il dato è pure peggiorato:
   **zero patch** su tutti e tre a due settimane dall'uscita. Per un pacchetto
   grande come PrimeVue quello non è un segnale di qualità, è un segnale di
   scarsa adozione: chi usa una major genera issue, e le issue generano `.0.1`.
   Corollario onesto: partire oggi è **difendibile**, non azzardato.
3. **Il valore stava nella controprova, non nel controllo.** Ogni misura è stata
   validata prima di crederle: l'algoritmo che ricostruisce i nomi delle
   variabili è stato tarato sul preset in uso oggi (88.9%, e le 7 non
   ricostruite **escluse** invece che date per buone); le 5 classi «assenti in
   v5» sono state ricontrollate contro la 4.5 e risultano assenti pure lì,
   quindi non sono regressioni. Senza quelle controprove i numeri avrebbero
   avuto la stessa forma e nessun valore.

**Sottoprodotti** — difetti attuali emersi di sponda, **non** causati dalla
migrazione e da trattare a parte: 364 usi diretti di `--p-*` contro la regola
di casa ([[feedback_css_centralizzazione]]); `--p-info-color` (9 usi),
`--p-warn-color`, `--p-font-family` e `--p-content-color-muted` che non
risultano fra i token del preset Aura nemmeno oggi; 18 dei 28 codepoint di
`main.css` senza commento `/* pi-nome */`, il che dimezza la capacità
diagnostica dello script icone (§6.3).

### 2026-07-29 · Step 6.1 eseguito — Pinia 4

Fatto su `dev/backend-tid` (non su un branch dedicato: scelta di Tid).
`pinia` 3.0.4 → **4.0.2**, `@vue/devtools-api` **8.2.1** aggiunto esplicito.
`npm i` ha rimosso 17 pacchetti transitivi. Build verde, `npm run lint` verde.

**R3 non si e' materializzato, e la premessa era sbagliata.** Sondato
direttamente su Pinia 4: `pinia._s` **esiste ancora ed e' ancora iterabile**.
Il codice precedente avrebbe continuato a funzionare. Era un rischio *latente*
— dipendere da un interno senza garanzie — non una rottura in arrivo.

Prima dell'upgrade `auto-reset.js` e' stato comunque riscritto su sola API
pubblica: il plugin costruisce un **registro proprio** degli store user-scoped
(li vede gia' tutti alla creazione, `_s` non serviva), in una `WeakMap` sull'
istanza di Pinia — cosi' HMR e test non si trascinano store di istanze morte —
con rimozione dal registro su `$dispose()`.

Aggiunta la rete che mancava: **`frontend/scripts/check-pinia-user-scoped-reset.mjs`**,
9 verifiche che girano in Node in un secondo, senza browser. Copre store con
snapshot, store con `clearUserState`, store *non* user-scoped che deve
sopravvivere, resetter module-scope, secondo logout consecutivo, e un controllo
che il plugin non torni a leggere `pinia._*`. Verde su 3.0.4 **e** su 4.0.2.

Tre cose emerse strada facendo:

1. **La prima stesura del test passava per il motivo sbagliato.** `pinia.use()`
   chiamato prima di `app.use(pinia)` mette il plugin in coda, e la coda la
   scarica `install(app)`: senza una app Vue il plugin non gira e il test
   verifica il nulla. Ora replica la sequenza di `src/main.js`.
2. **`npm run lint` era gia' rosso prima di questo lavoro**: `scripts/*.mjs` non
   aveva i globals Node in `eslint.config.js` — 5 errori `'process' is not
   defined` su `check-primeicons-codepoints.mjs` (committato in `6d255b200`).
   Aggiunto il blocco `app/node-scripts`. Senza, il gate «lint verde» non era
   utilizzabile da **nessuno** dei quattro step.
3. **La superficie Pinia dell'app e' minuscola**, ed e' questo il vero motivo
   del rischio basso — non il build verde: solo `createPinia`, `defineStore`,
   `getActivePinia`, `storeToRefs` (tutte presenti in v4); `$patch`, `$state` e
   `$dispose` compaiono **solo** dentro `auto-reset.js`. I 43 store non toccano
   altro.

Note: `npm audit` segnala 1 high (`eslint → minimatch → brace-expansion`),
**preesistente e non correlato**. In dev la console mostra al logout
`[PINIA_R1004] Pinia instance not found in context`: e' `getActivePinia()`
chiamato fuori da un contesto d'iniezione, Pinia 3 emetteva lo stesso avviso in
forma discorsiva — non e' una regressione.

**Controprova in-app: fatta da Tid il 2026-07-29, superata.** Login A → filtri
su una lista → logout → login B: i filtri risultano azzerati. Serviva perche'
lo script esercita il plugin con reattivita' Vue reale ma non il flusso di
logout vero (`stores/auth.js`) ne' i 39 store reali con i loro
`clearUserState`. **Step 6.1 chiuso, nessun residuo.**

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
