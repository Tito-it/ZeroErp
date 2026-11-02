# Piano operativo — Migrazione a PrimeVue 5 (+ @primeuix/themes 3, primeicons 8)

> **Tipo**: piano operativo FE (`dev/backend-tid`) · **Data**: 2026-07-29 ·
> **Owner**: Tid · **Stato**: 🔴 **UPGRADE FERMO** / ✅ **DISACCOPPIAMENTO
> CHIUSO**. §6.1 (Pinia 4) è **chiuso e resta valido**. §6.2/6.3 (primeicons 8)
> è stato eseguito e poi **annullato**. §6.4 (PrimeVue 5 + themes 3) **non è
> più una questione tecnica**.
>
> ✅ **Il binario §8-bis è arrivato in fondo: Gruppo A 30/34 il 2026-08-03**, e
> i **4 file rimasti sono fermi per decisione** (i cassetti senza endpoint
> paginato, §8-bis decisione 4), non per debito.
> ⭐ **Dal 2026-08-22 il Gruppo A è 31/35**: `LottoDrawer.vue` è stato
> riclassificato dal Gruppo B (i suoi tre tab sono tre liste, non tre
> dettagli di un master) e **convertito**. Il lavoro DB che lo precedeva sta in
> [brief-db-liste-drawer-lotto.md](../work-done/brief-db-liste-drawer-lotto.md).
> Cronologia: `vendite.lotti` e
> il 1° lotto il 31-07; dal 2° al 5° l'01-08; il 6° fra l'1 e il 2 agosto
> (`storico.audit_log` compresa); il **7°** (2 code + approvazioni prezzo +
> `VersioneDrawer`) e l'**8°** (drawer commessa + le 5 liste delle 3 dashboard)
> il **03-08**; il **9°** (`LottoDrawer`, 3 liste su 3 tab) il **22-08**.
> Registro del presidio a **47/47** — cioè le liste *montate dal frontend*.
> ⭐ Il 47° è `vendite.fondi_fattura_da_decidere` (definizione 44), che il
> 2026-08-22 ha smesso di essere l'eccezione: era seedata dal 15-08 da un altro
> cantiere e **non la montava nessuno**, cioè esisteva e nessun operatore poteva
> aprirla. Ora ha la sua pagina — *Vendite → Tool fatturazione*, primo tab —
> e il registro non ha più righe scoperte.
> ⚠️ **Qui si contano FILE, il presidio conta CODICI lista**: sono due unità
> di misura diverse e divergono già oggi (le 3 dashboard valgono 5 codici).
> `LottoDrawer` è 1 file = 3 codici, quindi con la sua conversione il piano
> è passato a **31/35**. La pagina «Tool fatturazione» **non muove il
> rapporto**: non è una conversione, è un file NUOVO che nasce standard — il
> denominatore 35 è il censimento delle liste *già scritte a mano*, e gonfiarlo
> con le nuove farebbe sembrare il debito più grande di quello che è.
>
> Il rapporto che il piano voleva invertire — 14 liste sullo standard contro 71
> con `DataTable` grezza (§8-bis, «il numero scomodo») — **è invertito**: 40
> file montano il building block. Cosa resta e di chi: §9, «Cosa resta aperto».
> È utile con QUALUNQUE esito della questione licenza.
>
> 🚨 **PrimeVue ha cambiato licenza al confine della major.** `primevue`,
> `@primeuix/themes` e `primeicons` erano **MIT** fino alla versione
> precedente e passano tutti e tre alla **licenza PrimeUI**
> (community/commerciale, con chiave di licenza) dalla nuova. ZeroErp è
> **AGPL v3 pubblica, con doppia licenza commerciale**. Questo non è un rischio di migrazione: è una decisione
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
> ⭐ **2026-10-03 — il disaccoppiamento passa anche dai drawer.** Gli 80 drawer
> laterali che montavano `<Drawer>` di PrimeVue a mano passano tutti dalla sede `AppDrawer`
> (`work-done/analisi-fe-chrome-drawer.md`), e il lint ferma gli import
> diretti di `dialog`, `confirmdialog`, `useconfirm`, `datatable` e `drawer`
> fuori dalle loro sedi (frontend-standards §«Import PrimeVue riservati»).
> Per questo piano vuol dire due cose: `drawer` passa da 73 import a **3**
> (le sedi), e una regressione non può più ricrescere in silenzio. Numeri in §2
> e §8-bis, colonna del 2026-10-03.
> Lo stesso giorno i due gusci hanno preso anche il **comportamento** comune:
> `AppDrawer` e `AppDialog` fanno passare ogni uscita (X, ESC, maschera,
> Annulla) da una conferma sulle modifiche non salvate, che i 44 dialog con
> campi e i form dei drawer alimentano con la loro fotografia
> (`useFotografiaDialog`, `useDrawerFormPreserve`). Per una migrazione vuol
> dire che il comportamento d'uscita di `Drawer` e `Dialog` in v5 si verifica
> **in due file** e vale per tutti (§6.4, prove 3 e 4). Analisi chiusa il
> 2026-10-03, collaudo verde.
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

ZeroErp è **AGPL v3** e pubblica su GitHub (fino al 2026-11-02 era GPL v3: il
punto non cambia, l'AGPL v3 ha lo stesso divieto al §10). L'AGPL v3 non ammette che si
aggiungano restrizioni oltre le proprie a chi riceve il codice, e la Community
License ne aggiunge parecchie: tetti di fatturato, di sviluppatori, di
dipendenti, e un rinnovo annuale. Il punto **non è** se ZeroErp sia idonea —
quasi certamente lo è — ma che **non può trasmettere a valle** una libertà che
lei stessa riceve con condizioni.

⚠️ **Con la doppia licenza il punto pesa su due fronti.** Oltre alla versione
AGPL, ZeroErp si vende anche con **licenza commerciale**: chi la compra
riceverebbe un prodotto che dipende da una libreria con tetti di fatturato,
sviluppatori e rinnovo annuale che ZeroErp non controlla e non può
sublicenziare. Una dipendenza permissiva (MIT, BSD, Apache-2.0) è l'unica che
va bene per **entrambe** le licenze — è anche la regola di
[CONTRIBUTING.md](https://github.com/Tito-it/ZeroErp/blob/main/CONTRIBUTING.md) per il codice di terzi.

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

## 2. Superficie misurata (2026-07-29 · **ri-verificata il 2026-09-02**)

```bash
cd frontend
# quanti file toccano PrimeVue
grep -rl "from 'primevue/" src --include=*.vue --include=*.js | wc -l
grep -rh "from 'primevue/" src --include=*.vue --include=*.js | wc -l
# quali componenti
grep -rho "from 'primevue/[a-z]*'" src --include=*.vue --include=*.js \
  | sed "s/.*primevue\///;s/'//" | sort | uniq -c | sort -rn
```

| Pacchetto | Superficie 2026-07-29 | **Superficie 2026-09-02** | **Superficie 2026-10-03** |
| --- | --- | --- | --- |
| `primevue` | 937 import in 260 file (su 335 `.vue`) — 47 moduli distinti | **1039 import in 300 file** (su **383** `.vue`) — **47** moduli distinti | **1027 import in 336 file** (su **441** `.vue`) — **47** moduli distinti |
| `pinia` | 43 store, 39 `userScoped` — plugin ora su sola API pubblica (§6.1 fatto) | non ri-misurato | non ri-misurato |
| `@primeuix/themes` | 1 file — `src/main.js`, preset `Aura` | **1 file** (invariato) | non ri-misurato |
| `primeicons` | 122 classi `pi-*` distinte + 28 codepoint cablati in `main.css` | non ri-misurato | non ri-misurato |

I dieci componenti più usati, **al 2026-10-03**: `tag` 141, `inputtext` 128,
`button` 113, `select` 104, `message` 94, `inputnumber` 50, `toggleswitch` 46,
`datepicker` 40, `column` 39, `datatable` 33. `drawer` esce dalla classifica:
**3** import, cioè le tre sedi (`AppDrawer`, `AppLayout`, `FiltriLista`).

⚠️ **2026-10-03: per la prima volta il totale cala** (1039 → 1027) mentre il
repo cresce (383 → 441 `.vue`). Le voci in calo sono di nuovo e solo quelle con
una sede: `drawer` (73 → 3), `datatable` (57 → 33), `column` (67 → 39). I
primitivi senza casa continuano a salire.

I dieci componenti più usati, **al 2026-09-02** (fra parentesi il 2026-07-29):
`tag` 117 (96), `button` 111 (93), `inputtext` 97 (90), `select` 93 (75),
`message` 77 (58), `drawer` 73 (67), `column` 67 (86), `datatable` **57** (76),
`inputnumber` 48 (43), `datepicker` 45 (—).

⚠️ **Il rapporto fra le due colonne conta più dei valori.** In 35 giorni il
repo è cresciuto di 48 `.vue` e la superficie PrimeVue di 102 import: `datatable`
e `column` sono le **uniche due voci in calo** (−19 e −19), tutto il resto sale.
Sono i due componenti su cui esiste un building block; gli altri non ne hanno
uno, e crescono col repo.

🔗 **Sulle icone c'è una regola, e NON sta qui.** Dove viva il *nome* di
un'icona (costante o letterale sul posto) è deciso dal 2026-09-02 in
[frontend-standards §«Dove vive il NOME di un'icona»](../frontend/frontend-standards.md):
regola del 2 applicata al **significato**, non campagna. ⛔ La regola generale
«ogni icona da `MANAGE_ICONS`» è stata valutata e **rifiutata**.
⚠️ Il rimando esiste perché la centralizzazione abbassa il costo di R2
(primeicons e i codepoint cablati) — ma **la regola non appartiene a questo
piano**: un piano è destinato a chiudersi in `work-done/`, e uno standard
archiviato insieme a lui smette di essere trovabile.

> ℹ️ **Come leggere questi numeri.** Sono una **fotografia datata**, non un
> argomento: dicono dov'era la superficie in quel giorno, non cosa vada fatto.
> La ragione per cui una lista passa da `<ListaConfigurabile>` sta nella regola
> zero di `frontend-standards`, e resterebbe identica se questa tabella dicesse
> altri numeri ([AGENTS.md §Regola zero](../../../../.codex/AGENTS.md)).

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

| Aggancio | Superficie 2026-07-29 | **Superficie 2026-09-02** | Se cede |
| --- | --- | --- | --- |
| Variabili `--p-*` | 364 usi, 63 distinte, 51 file | **374 usi, 65 distinte, 54 file** | Il colore ripiega sul nulla: testo invisibile, sfondi trasparenti |
| Classi interne `.p-*` | 187 usi, 48 distinte, 9 file | **194 usi, 49 distinte, 11 file** | Lo stile si stacca e il componente torna nudo |

Le più agganciate **al 2026-09-02** sono `--p-primary-color` (63),
`--p-text-muted-color` (61) e `--p-text-color` (24); sul fronte classi
`.p-button` (19) e `.p-menu-item-link` + `.p-tieredmenu-item-link` (26 fra le
due) — cioè **il kebab**, che sta in ogni riga di ogni lista.

⚠️ Entrambi gli agganci **salgono**, e sono quelli che nessun build segnala. La
deriva è lenta (+10 usi e +7 usi in 35 giorni) ma il verso è quello: il debito
di [[feedback_css_centralizzazione]] non si sta riassorbendo da sé.

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

✅ **Ri-eseguito il 2026-09-02: tutti e otto a zero**, più i due controlli di
non-regressione di `frontend-standards` §«Residui PrimeVue 3» (`tabview`,
`inputswitch`) — anch'essi **zero**. In 35 giorni di sviluppo nessun componente
rimosso o deprecato è rientrato: il campo resta sgombro.

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
| 3 | Un drawer con tab (`LottoDrawer`) | `Tabs`/`TabPanel` + `DataTable` annidata (agganciamo `.p-tabs`, `.p-tabpanels`, `.p-tablist`). ⭐ Dal 2026-10-03 tutti i drawer laterali passano da `AppDrawer`: il chrome (testata, footer fisso nello slot `#footer`, larghezza) si verifica **una volta**, e vale per tutti. Il nostro CSS aggancia `.p-drawer`, `.p-drawer-content`, `.p-drawer-footer`, `.p-drawer-title` (§R5) |
| 4 | Un `AppDialog` con footer | `Dialog` + `FormFooter`. ⭐ Dal 2026-10-03 anche la **conferma d'uscita**: con un campo cambiato, X / ESC / maschera / Annulla devono chiedere «Modifiche non salvate» (prop `confermaUscita`; agganciata a `update:visible` e al keydown di ESC in `pt.root`, che in v5 va riverificato). Un dialog che la provi: i componenti BoM |
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

| Gruppo | Import 2026-07-29 | **Import 2026-09-02** | Difficoltà di sostituzione |
| --- | --- | --- | --- |
| Primitivi (`tag`, `button`, `inputtext`, `select`, `toggleswitch`, `inputnumber`, `message`) | ~449 | **586** | **Bassa** — ce li ha qualunque libreria: rinomina + mappatura prop |
| `datatable` + `column` | 164 in 77 file | **116 in 53 file** | **Alta** — è il componente che nessuno replica bene |
| Coda lunga (componenti usati in ≤2 posti) | 22 componenti, poche decine | **21 componenti**, poche decine | Trascurabile |

**Il costo di lasciare PrimeVue è quasi tutto in DataTable.**

⭐ **Ri-misurato il 2026-09-02 (valori di fine giornata), e le due righe si
muovono in verso opposto.** `datatable`+`column` è calato di 48 import e 24 file
— è il lavoro del Gruppo A, e si vede: 8 import e 4 file sono caduti nel
pomeriggio, con le quattro liste `ui`. I primitivi sono saliti di **137**, cioè più di quanto DataTable sia
sceso: la superficie complessiva **cresce** mentre la parte cara si assottiglia.

⚠️ Non cambia la conclusione della riga in grassetto — la difficoltà dei
primitivi resta bassa e quella di DataTable resta alta, e sono proprietà dei
componenti, non dei conteggi. Cambia **dove sta il numero che cresce**, ed è la
metà del §8-bis che il piano non ha mai sviluppato: vedi la sezione nuova qui
sotto.

### I primitivi — la riga che questo piano non ha mai sviluppato

Il paragrafo «La mossa» (qui sotto) dice, in una riga sola: *«stessa logica per i
primitivi, con un sottile strato nostro davanti dove capita di passarci»*.
**Quella riga non ha mai avuto un inventario, un criterio, né una spunta**, e nel
frattempo i primitivi sono passati da ~449 a 586 import.

Cosa c'è già davanti ai primitivi, **misurato il 2026-09-02** (file che li usano):

⚠️ I conteggi del 2026-10-03 escludono il file del wrapper stesso (un `<AppDrawer>`
nel suo commento d'esempio non è un uso); quelli del 2026-09-02 no.

| Strato di casa | Primitivo che copre | File 2026-09-02 | **File 2026-10-03** |
| --- | --- | --- | --- |
| `FormFooter` | `button` (coppia Annulla/Salva) | 81 | **17** diretti + gli 81 `AppDrawer`, che lo rendono loro |
| `LookupSelect` | `select` | 72 | **71** |
| `PageActionsBar` | `button` (azioni di pagina) | 70 | **67** |
| `RowActionsMenu` | `button` + `menu` (azioni di riga) | 49 | **60** |
| `AppDialog` | `dialog` | 43 | **48** — e dal 2026-10-03 anche la conferma d'uscita (comportamento, non solo presentazione) |
| `AttivoTag` | `tag` (il caso attivo/non attivo) | 28 | **34** |
| `DrawerActionsBar` | `button` (azioni di drawer) | 18 | **14** |
| `NewButton` | `button` | 3 | **0** |
| `AppDrawer` | `drawer` | 2 | **81** — tutti i drawer laterali |
| `EntityFormField` | `inputtext` & c. | 1 | **1** |
| — | `inputtext` (97), `datepicker` (45), `toggleswitch` (43), `inputnumber` (48), `message` (77), `textarea` (21), `checkbox` (19) | **nessuno** | `inputtext` 128, `datepicker` 40, `toggleswitch` 46, `inputnumber` 50, `message` 94, `textarea` 24, `checkbox` 20 — **nessuno** |

⭐ **Lo strato non è assente: è a due velocità.** Dove c'è un building block di
*comportamento* — una barra di azioni, un footer, un lookup — la copertura è
larga (70-81 file) e nessuno importa più il primitivo a mano. Dove servirebbe un
wrapper di *presentazione pura* (`AttivoTag`, `NewButton`, `AppDrawer`,
`EntityFormField`) la copertura è 1, 2, 3, 28 file: **quei quattro sono estratti
e non adottati**, che è la forma peggiore — una seconda implementazione della
stessa cosa accanto alla prima ([[feedback_duplicazione_nasconde_il_bug]]).

⛔ **Non è una lista di lavoro, ed è deliberato.** I sette primitivi senza casa
sono ~350 import: incapsularli è un progetto di migrazione, cioè esattamente
quello che «La mossa» dice di **non** aprire. La cosa che questa sezione
stabilisce è più piccola e più utile: **prima di scrivere un wrapper nuovo, si
guarda perché i quattro esistenti non sono stati adottati** — un quinto wrapper
inadottato non abbassa nessun costo, lo raddoppia.

⭐ **`AppDrawer` ha risposto alla domanda (2026-10-03).** «Perché il wrapper
esistente non è stato adottato?» — per `AppDrawer` la risposta era misurabile:
**non copriva quello che i drawer fanno davvero** (icona in testata, scala
`DRAWER_WIDTH`, montaggio a fine animazione, footer «Chiudi», readonly sul
corpo, conferma su ogni uscita), quindi ogni drawer ricostruiva a mano il
chrome intero. Censito il chrome comune, riscritto il guscio per coprirlo, gli 80
drawer laterali ci sono passati sopra in un giorno, e solo DOPO il lint ha vietato
l'import. La lezione per gli altri tre inadottati (`NewButton`, ormai a zero,
`EntityFormField`, `AttivoTag`) è la stessa: un wrapper si adotta se copre il
caso reale, non se esiste.

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

> 📉 **Ri-misurato: i file con `DataTable` grezza sono scesi a 56 il 2026-08-02,
> a 48 a fine 03-08, risaliti a 57 il 30-08 e ancora 57 al 2026-09-02.** I 77
> sono la fotografia del 2026-07-29 e restano qui perché sono il metro con cui è
> stato dimensionato il lavoro; il numero vivo è quello sopra. Il calo di agosto
> è più grande del numero di conversioni perché alcune pagine montavano più
> `DataTable` nello stesso file (`DashboardCompetenzaView` ne aveva tre).
>
> ⚠️ **Fermo a 57 non vuol dire fermo**: fra il 30-08 e il 02-09 sono state
> convertite `EmittenteFiscaleBillingAccountTab` (§Gruppo B, 01-09) e ne sono
> nate altrettante altrove. Il totale sta piatto perché entrate e uscite si
> compensano — è il motivo per cui questa riga da sola non dice se il lavoro
> avanza, e vanno guardati i due denominatori separati.
>
> Contro cosa verificarlo, visto che i denominatori in questo documento sono
> **tre e diversi**, e confonderli è il modo più facile di litigare sui numeri:
>
> | Misura | 02-08 | 03-08 | 02-09 mattina | 02-09 sera | 02-09 notte | 02-09 chiusura | 02-09 · 61 paginata | **02-09 · lotto 3** | Cos'è |
> | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
> | codici seedati (`ui.lista_definizione`) | 33 | 43 | 55 | 59 | 63 | 63 | 63 | **65** | le liste configurate a DB — +4 col lotto 2, +2 col lotto 3 (`titolo_iva_ambiti`, `titolo_iva_movimenti`) |
> | righe nel registro del presidio (`_LISTE`) | 33 | 43 | 54 ⏳ | 59 ✅ | 59 ⏳ | 63 ✅ | 63 ✅ | **65** ✅ | ⭐ divergenza rientrata e RIMASTA tale anche col lotto 3: `comm -23 seed presidio` è vuoto |
> | file consumer che montano `<ListaConfigurabile>` | 32 | 40 | 55 | 60 | 60 | 62 | 61 | **61** | ⭐ **scende, e non è una regressione**: `SistemazioneDrawer` è passato a `<DrawerTabLista>`, che il BB lo monta per lui. Il `grep` su `<ListaConfigurabile` non lo vede più — è il conteggio a essere parziale, non la conversione a essere tornata indietro |
> | file del Gruppo A convertiti | 22 / 34 | 30 / 34 | 31 / 35 | 35 / 39 | 35 / 39 | 35 / 39 | 35 / 39 | **35 / 37** | ⭐ cala il DENOMINATORE, non sale il numeratore: BoM e righe contratto passano al Gruppo B (decisione di Tid, 02-09). Le conversioni restano 35 — quei due file non sono stati toccati |
> | **liste montate `:paginata="false"`** | — | — | — | 4 | 4 | 5 | 4 | **5** | i quattro pannelli `ui.*` più gli **ambiti** del titolo (lista 64, limitata per modello). Il `grep` ne trova sempre uno in più (6), ed è il BB che si cita nel proprio commento |
> | file con `DataTable` grezza | 56 | 48 | 57 | 53 | 53 | 49 | 49 | **48** | il contatore della regola zero — `TitoloIvaDrawer` convertito (lotto 3) |
>
> ⭐ **SECONDA CODA — il lotto 3 (liste 64 e 65).** Il team DB ha seminato le due
> liste dentro `TitoloIvaDrawer` (`brief-db-seed-liste-titolo-iva.md`, in
> `work-done/`), e il drawer **è stato convertito lo stesso giorno**: le sue due
> `DataTable` grezze sono sparite, `DataTable grezza` scende a **48**.
>
> ⛔ **E le due liste sono passate da Gruppo B a Gruppo A**, con la stessa
> disciplina con cui BoM e righe-contratto hanno fatto il viaggio opposto: la
> classificazione del 02-09 mattina le aveva lette come *dettaglio del master*
> perché le righe **arrivavano dal payload del dettaglio** (`detail.ambiti`,
> `detail.movimenti`). Ma la PRIMA domanda del criterio — *«l'entità ha vita
> propria: un endpoint suo, una popolazione arbitraria?»* — per entrambe
> risponde sì, e i due endpoint esistevano già. Il registro dei movimenti, in
> più, **cresce a ogni fattura**: leggerlo dentro un dettaglio significava una
> query senza LIMIT che un giorno cade proprio sul titolo più usato.
>
> ⚠️ **Le due hanno contratti diversi, e di proposito**: gli ambiti sono
> limitati per modello (montati `:paginata="false"`, `ordinabile = f` su tutte
> le colonne, `pagina_dimensione` vuota), il registro è paginato a 25. Un
> contratto solo per due nature diverse sarebbe stato comodo e sbagliato.
>
> ⛔ **Ma il registro sì, e stavolta i presidi che si sono accesi sono TRE**, non
> due. Vale la pena elencarli perché è la prova che il meccanismo funziona senza
> che nessuno se ne ricordi:
>
> | Presidio | Cosa ha preteso |
> | --- | --- |
> | `test_lista_proiezione_campo_sorgente` §2 | una riga in `_ESERCIZI` per ciascuna delle due |
> | idem §4 | una whitelist per ogni lista esercitata ⇒ `_ORDER_COLS_MOVIMENTI` + `list_movimenti(order_by, order_dir)`. Gli **ambiti** no: a catalogo nessuna colonna è `ordinabile = t`, quindi `ORDINAMENTO_LOCALE` |
> | `test_perimetro_emittente_copertura` | un `lista_codice` su una view ⇒ dichiarato sulle due view dei titoli |
>
> ⭐ **Nessuno dei tre è stato «ricordato»: si sono accesi da soli quando le
> righe sono arrivate.** È il verso giusto — il lavoro BE serve nel momento in
> cui il catalogo lo rende raggiungibile, non prima.

> ⭐ **CODA DELLA GIORNATA — la 61 è passata da «non paginata» a paginata**
> (decisione di Tid, 2026-09-02, dopo la chiusura qui sopra). `SistemazioneDrawer`
> era stato convertito **con `:paginata="false"`**, e la ragione scritta era «gli
> atti di UNA fattura sono pochi per modello».
>
> ⛔ **Quella ragione è una previsione sui DATI, e una previsione sui dati non
> decide la forma di una lista** (regola zero). Il prezzo era concreto e non si
> vedeva: niente pagine, niente «Personalizza colonne», niente export — cioè un
> drawer fuori dallo standard delle altre quaranta liste, senza che niente lo
> dicesse. Ora ha lo stesso pacchetto della 62: store Pinia + `useDrawerTabLista`
> + `<DrawerTabLista>`, e un endpoint di export suo.
>
> ⭐ **E la whitelist di BE-1 ha smesso di essere «pronta per domani»**: la 61 è
> uscita dalla sentinella `ORDINAMENTO_LOCALE` ed è ora esigibile dai test 1-3
> come ogni altra lista. ⇒ **`test_liste_lotto2_whitelist_ponte.py` è stato
> cancellato**: esisteva solo per coprire ciò che quei test non raggiungevano, e
> a zero righe nel suo registro non copriva più niente. Due presidi sullo stesso
> invariante divergono al primo che qualcuno aggiorna.
>
> ⚠️ **Cosa è cambiato anche a BE**: `list_sistemazioni_fattura` restituisce
> `(righe, totale)` in **una** valutazione (`COUNT(*) OVER ()`) e
> `count_sistemazioni_fattura` è sparita — era una seconda query sullo stesso
> predicato, e due valutazioni possono non concordare. Stessa mossa già fatta su
> `count_titoli_soggetto` con la 62.

> ✅ **E RICHIUSA a fine giornata: 63 = 63** (`comm -23 seed presidio` vuoto). Le
> quattro liste del lotto 2 sono montate — `CanaliIncassoSearchTable`,
> `SistemazioneDrawer`, `TitoliIvaSoggettoDrawer`, `TitoliIvaSfondatiView` — e
> con loro sono rientrate BE-1 e BE-2. ⭐ **Il debito auto-esigente ha funzionato
> nel verso previsto**: i due rossi annunciati qui sotto si sono presentati alla
> conversione, non prima, e sono stati pagati in quel momento. Il blocco che
> segue resta come racconto, non come stato.
>
> ⏳ *Era: riaperta la sera stessa, di proposito — 63 seedati contro 59 nel registro*
> (2026-09-02, lotto 2 — `work-done/brief-db-seed-liste-lotto-2.md`). Le quattro sono
> `pagamenti.canali_incasso`, `pagamenti.sistemazioni_fattura`,
> `anagrafiche.soggetto_titoli_iva`, `anagrafiche.titoli_iva_sfondati`: **seed
> arrivato prima del suo consumer**, esattamente la forma già descritta qui sotto
> per `vendite.famiglie_documento`.
>
> ⭐ **Il presidio NON tace per distrazione, e questo è il punto**: `_LISTE` si
> misura sul **frontend** (test 6, `test_registro_copre_tutte_le_liste_montate_dal_frontend`),
> e nessuna delle quattro è ancora montata. Quindi oggi la suite è verde a
> ragione, non per sottrazione.
>
> ⛔ **Ma il giorno in cui si converte una di quelle view, il registro la
> pretende — e con lei arrivano DUE rossi già previsti**, che sono la ragione per
> cui `work-done/brief-db-seed-liste-lotto-2.md` §7 esiste:
>
> | Test che diventerà rosso | Su quale lista | Cosa chiede |
> | --- | --- | --- |
> | `test_whitelist_copre_le_colonne_ordinabili` | 61 e 62 | I due endpoint non accettano `order_by` affatto: 9 colonne seminate `ordinabile = t` non hanno nessuna whitelist dietro (richiesta **BE-1**) |
> | `test_whitelist_chiavata_sul_campo_sorgente` | 60 | `ENTI_INCASSO_SORT_COLUMNS` è chiavata su `centro`, il `campo_sorgente` è `centro_descrizione` (richiesta **BE-2**) |
>
> ⇒ **Il debito è auto-esigente**: chi converte non può dimenticarlo, perché il
> presidio glielo mette davanti. È il verso giusto — la conversione è il momento
> in cui quel lavoro serve davvero, non prima.

> ✅ **RIENTRATA in giornata (2026-09-02, sera): 59 = 59.**
> `vendite.famiglie_documento` ha preso la sua riga nel registro quando il
> cantiere dei registri di numerazione l'ha chiusa. Il blocco qui sotto resta
> come **racconto di come si legge una divergenza attesa**, non come stato.
>
> ⏳ *Era: le prime due righe divergono di uno, ed è cantiere aperto (confermato
> da Tid il 2026-09-02).* Lo scarto è `vendite.famiglie_documento` (id 55, seedata il
> 2026-09-01, `vista_sql = vw_famiglie_documento_lista`): è a catalogo, non è
> ancora nel registro `_LISTE` di
> `apps/core/tests/test_liste_configurabili_seed.py`, e non ha ancora un consumer
> `<ListaConfigurabile codice="…">` — oggi il codice è usato come **vocabolario**
> da `EmittenteFiscaleBillingAccountTab` e `RegistroNumerazioneDrawer`. Fa parte
> del cantiere dei **registri di numerazione**, ed è un seed arrivato prima del
> suo consumer.
> ⚠️ Le altre due seedate senza consumer statico — `vendite.resi_da_accreditare`,
> `vendite.resi_da_riconsegnare` — sono i due `:codice` dinamici di
> `ResiCodaTable`, e sono a posto.
> ⇒ **La riga di destra resta l'invariante**, ma si verifica a cantiere chiuso:
> il momento in cui deve tornare a coincidere è quando la lista prende il suo
> consumer. Fino ad allora la divergenza è **attesa e datata**, non un difetto —
> e questa nota esiste perché fra un mese non lo sembri.
>
> Comandi per rifare le misure, **tutte** (aggiornati il 2026-09-02: la nota sui
> «+3 falsi positivi in commento» non vale più — oggi il conteggio è netto):
>
> ```bash
> # i tre denominatori
> awk 'NR>1 && NF' db/changelog/migrations_v2/80_data/sql/ui/lista_definizione.csv | wc -l
> grep -rl "<ListaConfigurabile" frontend/src --include=*.vue | wc -l
> grep -rl "from 'primevue/datatable'" frontend/src --include=*.vue | wc -l
>
> # l'invariante seed ↔ presidio, che il 02-09 è rotta di 1
> awk -F',' 'NR>1 && NF {print $2}' \
>   db/changelog/migrations_v2/80_data/sql/ui/lista_definizione.csv | sort > /tmp/seed.txt
> grep -oE '"[a-z_]+\.[a-z_0-9]+"' backend/apps/core/tests/test_liste_configurabili_seed.py \
>   | tr -d '"' | sort -u > /tmp/presidio.txt
> comm -23 /tmp/seed.txt /tmp/presidio.txt      # seedate e NON presidiate
> ```

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

**I prerequisiti tecnici**, da verificare riga per riga. ⚠️ Erano **cinque**
fino al 2026-09-02: il primo è caduto quel giorno, e resta scritto **barrato**
invece che cancellato — un prerequisito che sparisce senza lasciare traccia fa
sembrare che non ci sia mai stato, e questo aveva dimensionato per un mese il
costo di ogni conversione.

| # | Prerequisito | Perché |
| --- | --- | --- |
| 1 | ~~**Endpoint paginato server-side**~~ → **CADUTO il 2026-09-02** | Diceva: «il BB ha `lazy` **fisso**, non parametrico: senza paginazione server-side non si monta». **Non è più vero**: `lazy` e `paginator` sono governati dalla prop `paginata` (default `true`). Una lista la cui popolazione è limitata **per modello** si monta con `:paginata="false"` — vedi §«La modalità non paginata» |
| 2 | **Codici colonna == campi dell'API** | il BB rende `data[codice]`: il nome è un contratto, non un'etichetta |
| 3 | **Display field risolti dal BE** (JOIN) | niente lookup client-side, altrimenti la colonna mostra un id ([[feedback_display_fields_backend]]) |
| 4 | **Il caller resta padrone dei dati** | fornisce `rows`/`total`/`loading` e gestisce `@page`/`@sort`; il BB **non fa fetch** |
| 5 | **Rendering custom via slot** | `cell-{codice}` per la cella, `actions` + `RowActionsMenu` per le azioni di riga |

🔴 **Quattro liste del Gruppo A non soddisfacevano il prerequisito 1** (colonna
`Lazy` = «—»): richiedevano **prima** un endpoint paginato lato BE —
`ArticoloBomDrawer`, `ContrattiBillingAccountDrawer`, `ContrattoRigheDrawer`,
`OffertaEccezioniDrawer`.

⭐ **Due delle quattro sono uscite dal Gruppo A il 2026-09-02** (decisione di
Tid): `ArticoloBomDrawer` e `ContrattoRigheDrawer` sono **righe di un master**,
non liste — vedi la nota qui sotto. Ferme per decisione 4 restano le altre due.

⭐ **Dal 2026-09-02 quel blocco non è più automatico**: se la loro popolazione è
limitata per modello possono montarsi `:paginata="false"` senza toccare il
backend. ⚠️ Ma non è un liberi tutti e non le sblocca d'ufficio: le righe di un
contratto o i componenti di una distinta base **non** sono limitati per modello,
e per due di esse la domanda vera era un'altra (sono righe di documento →
Gruppo B: spostate il 2026-09-02, vedi la nota qui sotto).

> ✅ **DECISO DA TID IL 2026-09-02: la coppia passa al Gruppo B.**
> `ArticoloBomDrawer` **sono** i componenti BoM e `ContrattoRigheDrawer` **sono**
> le righe del contratto: la seconda domanda del criterio li nomina per esteso
> (*«righe ordine, **componenti BoM**, righe reso»*), e per loro la risposta è
> quella — non una lista con un paginator mancante, un **dettaglio del master**.
> Vanno su `RigheMasterDetailTable` / `SearchDetailTable`, non su
> `<ListaConfigurabile>`.
>
> ⭐ **Ha vinto il criterio, non la tabella**, ed è il verso giusto: la
> contraddizione stava fra una regola scritta il 01-09 e un inventario più
> vecchio, e a muoversi è l'inventario. Il denominatore del Gruppo A scende da
> **39 a 37**, e i convertiti restano 35 — nessuno di quei due file è stato
> toccato: cambia dove sono attesi, non cosa è stato fatto.
>
> ⚠️ **Il denominatore non cala perché il lavoro è finito**: cala perché due
> file erano contati nel posto sbagliato. Chi legge il numero fra un mese deve
> vedere questa riga, altrimenti legge un avanzamento che non c'è stato.
>
> ℹ️ Le altre due (`ContrattiBillingAccountDrawer`, `OffertaEccezioniDrawer`)
> restano **Gruppo A**, e non per inerzia: la prima è un tab-lista su entità con
> vita propria (prima domanda ⇒ Gruppo A, oggi la casa è `useDrawerTabLista`), la
> seconda è un'eccezione di prezzo con endpoint suo. Sono le uniche due ancora
> ferme per decisione 4 — cioè in attesa di un endpoint paginato o della scelta
> di montarle non paginate.

#### ⭐ La modalità non paginata — il cancello che è caduto (2026-09-02)

Fino al 2026-09-02 `<ListaConfigurabile>` aveva `lazy` e `paginator` **cablati
nel template**. Non era una scelta dichiarata da nessuna parte: era una costante
rimasta lì. La conseguenza è che il BB **rifiutava** ogni lista senza
paginazione server-side — cioè, per costruzione, tutto il residuo.

⭐ Il punto che rende la modifica piccola e il guadagno grande: **cinque dei sei
benefici del BB non c'entrano niente con la paginazione.**

| Cosa dà il BB | Dipende dalla paginazione? |
| --- | --- |
| Colonne dal catalogo, etichette, formati | **No** |
| Personalizzazione colonne dell'operatore + preset | **No** |
| Ritiro responsive (`useResponsiveColumns`) | **No** |
| Colonna azioni, slot `cell-*`, colonna selezione | **No** |
| Export dal catalogo | Quasi |
| `lazy` + paginator server-side | Sì — ed è l'unica |

⇒ Un cancello che presidiava **una** cosa stava davanti a cinque che non
riguardava. Ora la prop `paginata` (default `true`) le separa.

##### ⛔ «Non paginata» non vuol dire «senza `total`»

Vuol dire **`rows.length === total`**, e il BB lo **verifica**: se divergono non
disegna la tabella e mostra un errore al posto suo (`troncamentoSospetto`).

⚠️ È il presidio su **l'unico difetto muto** che la modalità introduce. Con
`lazy` spento PrimeVue tratta `rows` come il dataset **completo**: un caller che
continuasse a mandare una pagina mostrerebbe 25 righe su 500 senza paginator e
**senza errore**, e l'operatore non avrebbe modo di saperlo.

🔴 **E il `total` deve essere INDIPENDENTE dalle righe, o il guard è un'eco.**
È la trappola dentro la trappola, emersa implementando: gli endpoint di queste
liste restituivano una lista nuda e lo store faceva
`totalRecords = items.length` — cioè `rows.length === rows.length`, sempre vero.
⇒ Regola: **una lista `paginata: false` pretende un endpoint che dichiari il
conteggio con una query sua**. Forma `{results, count}`, che è la variante
offset-based già documentata in `api.md` §Paginazione.
⛔ E `count` **non** si calcola con `len(results)` nel service: sposterebbe la
tautologia dal frontend al backend senza toglierla.

##### Le altre quattro modalità di guasto, e come sono chiuse

| | Come sta |
| --- | --- |
| Doppio ordinamento (PrimeVue ordina in locale **e** emette `@sort`) | `@page`/`@sort` **non** vengono emessi: non c'è niente da rifetchare |
| `pagina_dimensione` del preset diventa lettera morta | `paginator: false` forzato in coda al merge; nel seed la colonna si lascia **vuota** |
| Ordine locale ≠ ordine del database (NULL, accenti, numeri-come-testo) | **Non presidiabile: dichiarata.** `nullSortOrder` esplicito, e `ordinamento_default` del preset vuoto. Una lista in cui l'ordine dei NULL è informazione resta `paginata: true` |
| Il presidio `_LISTE` pretende una whitelist che queste liste non hanno | Sentinella **`ORDINAMENTO_LOCALE`**. ⛔ NON `_DEBITO_WHITELIST_LOGICA`: quello è un registro di debito e deve calare, questa è una proprietà della lista e resta |

⭐ E la sentinella ha il suo cancello (test **8-bis**): una lista dichiarata a
ordinamento locale **deve** essere montata con `:paginata="false"`. Il difetto
che previene è una **rimozione** — togliere la prop sembra innocuo e la pagina
continua a funzionare, ma riaccende l'ordinamento server-side su una lista senza
whitelist, e la freccia risponde 400 al primo click.

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
- `anagrafiche/components/GeoSearchTable.vue` (in `core/components/` fino al 2026-09-26)
- `core/components/ListaConfigurabile.vue`
- `core/components/RigheMasterDetailTable.vue`
- `core/components/SearchDrawer.vue`

#### ⚠️ L'inventario qui sotto è più vecchio del repo — riconciliato il 2026-09-02

Le due tabelle che seguono coprono **46** dei **57** file misurati oggi (35
Gruppo A + 36 Gruppo B − `LottoDrawer` contato due volte, + 6 dello strato = 76
righe che valgono 46 file vivi). **Undici file non stanno in nessuna delle due**,
e la conciliazione va fatta prima di usare l'inventario come lista di spunta:

| File fuori inventario | Da dove arriva |
| --- | --- |
| `pagamenti/components/CanaliIncassoSearchTable.vue` | cantiere incassi — porta già in testa il proprio debito dichiarato: *«NON ha un seed in `ui.lista_definizione`»* |
| `pagamenti/components/DistintaDrawer.vue` | cantiere incassi |
| `pagamenti/components/RegistraDistintaDialog.vue` | cantiere incassi |
| `pagamenti/components/SistemazioneDrawer.vue` | cantiere incassi |
| `anagrafiche/components/TitoliIvaSoggettoDrawer.vue` | titoli IVA (I7/D10) |
| `anagrafiche/components/TitoloIvaDrawer.vue` | titoli IVA (I7/D10) |
| `anagrafiche/views/TitoliIvaSfondatiView.vue` | titoli IVA (Q4) |
| `vendite/resi/components/AccreditoEsitoDialog.vue` | resi — esito giro di accredito (F2) |
| `vendite/_shared/situazioneMerce/SituazioneMerceContenuto.vue` | situazione merce — **quattro** `DataTable` nello stesso file |
| `vendite/components/ListiniSearchTable.vue` | ✅ già convertita 01-08: **residuo** nella riga di espansione (versioni) |
| `vendite/components/LottoDrawer.vue` | ✅ già convertito 22-08: **residuo**, motivo dichiarato in commento a riga 17 |

⚠️ **Le ultime due righe non sono un errore di spunta.** Un file può montare
`<ListaConfigurabile>` **e** una `DataTable` grezza: il `grep` degli import conta
i file, non le tabelle. ⇒ Il contatore di `frontend-standards` §Regola zero
resta valido come **campanello** (se sale, hai aggiunto una lista fuori
standard), ma **non** è il conteggio delle liste da convertire, e non lo è mai
stato. Confonderli è il quarto denominatore.

#### ✅ Classificazione fatta — 2026-09-02

Applicato il criterio in tre domande a tutti e undici, guardando **da dove
arrivano le righe** e non dove sta la tabella. ⚠️ Nessuno tocca la terza domanda:
il timore che `SituazioneMerceContenuto` e `AccreditoEsitoDialog` fossero
matrici era infondato — sono entrambi dettaglio, non slot/override.

| File | Righe da | Esito |
| --- | --- | --- |
| `pagamenti/components/CanaliIncassoSearchTable.vue` | `store.items`, endpoint suo, ha il paginator | **Gruppo A** |
| `pagamenti/components/SistemazioneDrawer.vue` | `listSistemazioniFattura(fatturaId)` → envelope `results` | **Gruppo A** |
| `anagrafiche/components/TitoliIvaSoggettoDrawer.vue` | endpoint suo (`results`), e il singolo titolo ha un **drawer autonomo** | **Gruppo A** |
| `anagrafiche/views/TitoliIvaSfondatiView.vue` | endpoint suo (`results`), è una view di presidio | **Gruppo A** |
| `pagamenti/components/DistintaDrawer.vue` | `dettaglio.righe` — sono le **righe della distinta** | ~~Gruppo B~~ → **Gruppo A** (18-09, rilievo in-app di Tid: «mancano tutte le caratteristiche di una lista standard»): le righe arrivavano dal dettaglio, ma le righe contabili hanno endpoint propri (`righe/<id>/…`), una macchina a stati propria e una coda propria (`pagamenti.righe`) — la **prima** domanda risponde sì, come per `TitoloIvaDrawer`. **Convertita il 18-09**: lista `pagamenti.distinta_righe` (69), `GET distinte/<id>/righe/` paginato + `export/`, `useDrawerTabLista` + `<DrawerTabLista>`. Resta il debito dichiarato del master-detail (form sotto la lista, non `RigheMasterDetailTable`) |
| `anagrafiche/components/TitoloIvaDrawer.vue` | `ambiti` + `movimenti` **del titolo** che il drawer mostra | ~~Gruppo B~~ → **Gruppo A** (02-09 sera): le righe arrivavano dal dettaglio, ma i due endpoint esistevano già e il registro **cresce**. Convertito col lotto 3 |
| `vendite/_shared/situazioneMerce/SituazioneMerceContenuto.vue` | 4 tabelle di **dettaglio** della stessa situazione | Gruppo B |
| `pagamenti/components/RegistraDistintaDialog.vue` | `anteprima.righe_non_registrabili` | Gruppo B — **anteprima in dialog** (eccezione dichiarata) |
| `vendite/resi/components/AccreditoEsitoDialog.vue` | `props.esito.falliti` — il referto di un giro | Gruppo B — **anteprima in dialog** (eccezione dichiarata) |
| `vendite/components/ListiniSearchTable.vue` | riga di espansione (versioni) di una lista **già convertita** | non è un bersaglio |
| `vendite/components/LottoDrawer.vue` | residuo dichiarato in commento, lista **già convertita** | non è un bersaglio |

⇒ **4 al Gruppo A, 5 al Gruppo B (di cui 2 sono l'eccezione anteprima), 2 non
sono bersagli.** ⚠️ Dal 18-09 `DistintaDrawer` è passato al Gruppo A ed è
convertito (riga sopra): il Gruppo B di questa conciliazione conta **4**.

⭐ **Il segnale che decide è UNO, ed è ripetibile**: `grep -oE ':value="[^"]+"'`
sul `.vue`, poi si risale alla variabile. Se viene da un `dettaglio.righe` o da
una prop del padre è dettaglio; se viene da un endpoint suo con envelope
`results` è una lista. ⚠️ **Non** decide il contenitore: due dei quattro Gruppo A
stanno dentro un drawer, ed è esattamente l'errore che il criterio del 01-09 è
nato per correggere.

⚠️ **`CanaliIncassoSearchTable` è il caso più netto**: porta già in testa il
proprio debito scritto — *«NON ha un seed in `ui.lista_definizione`»*. Non era
una svista, era una dichiarazione in attesa di questo momento.

#### ✅ CHIUSA — il legame catalogo ↔ payload ha il suo presidio

> ⚠️ **Questa sezione era sbagliata quando l'ho scritta** (2026-09-02 mattina):
> la registrai come «consegna aperta al team BE/FE» senza cercare se il presidio
> esistesse gia'. Esisteva — `apps/core/tests/db/test_lista_proiezione_campo_sorgente.py`
> — e copre **43 liste**, si **arma da solo** dal seed (una lista nuova senza
> vista rende rosso `test_il_registro_copre_ogni_lista_senza_vista` il giorno in
> cui viene seminata) e include gia' le 4 liste `ui`.
> ⭐ Eseguito contro il database vero il 2026-09-02 (`ZEROERP_TEST_DB_E2E=1`):
> **4 test verdi**, incluse le 4 liste nuove.
> ⛔ E' skippato nella corsa normale (vuole un DB), quindi **non si vede** nella
> suite veloce: chi tocca un seed deve lanciarlo a mano o fidarsi della CI.
>
> Il testo originale resta sotto perche' descrive bene il difetto che quel
> presidio previene — ma **non e' piu' una consegna**.

#### 🕳️ Il difetto che quel presidio previene (era: consegna aperta)

> Rilievo del **team DB**, 2026-09-02, alla chiusura di
> [brief-db-seed-liste-ui-admin](../work-done/brief-db-seed-liste-ui-admin.md).
> Non appartiene a quel lotto: vale per tutte le liste senza vista.

Il guard DB sui `campo_sorgente`
(`trgfn_ui_lista_colonna_a10_valida_campo_sorgente`) **si ferma subito quando la
lista non dichiara una `vista_sql`**. Su quelle liste nessuno verifica che i
`campo_sorgente` a catalogo esistano davvero nel payload dell'endpoint.

⚠️ **Se un endpoint rinomina un campo non fallisce niente**: cella vuota a video
e colonna vuota nell'export, in silenzio. È la classe di difetto più cara di
questo repo — quella che non dà errore. E non è teorica: le quattro liste `ui`
appena seedate hanno **sei** campi in questa condizione (`colonne_count`,
`preset_riferimento`, `colonna_etichetta`, `colonna_codice`,
`profilo_accesso_codice`, `livello_accesso`), tutti prodotti da JOIN o calcolati
dal service.

⭐ **Perimetro: 43 liste su 59** non dichiarano una vista — solo 16 ce l'hanno
(misurato il 2026-09-02 su `origin/Tito-dev`, seed `ui` compreso: `vista_sql`
NULL o vuota in `lista_definizione.csv`). Il presidio possibile è **uno solo ed è
lato BE**: un test che confronti i `campo_sorgente` a catalogo con le chiavi
della proiezione del repository che serve quella lista.

```bash
git show origin/Tito-dev:db/changelog/migrations_v2/80_data/sql/ui/lista_definizione.csv \
  | awk -F',' 'NR>1 && NF {tot++; if ($5=="NULL" || $5=="") senza++} \
               END {print senza" senza vista su "tot}'
```

⇒ **Vale per tutte in una volta.** Farlo lista per lista, mentre si converte,
significa scriverne 43 versioni e dimenticarne alcune — che è il modo in cui i
presidi di questo repo diventano verdi per sottrazione. Cantiere suo, non un
pezzo della conversione.

⚠️ Il rapporto è **il contrario di come suona**: la lista con la vista è
l'eccezione (16), quella senza è la norma (43). Un presidio che coprisse le sole
liste «con vista» presidierebbe poco più di un quarto del catalogo.

#### Gruppo A — liste vere (39 file)

Sono il bersaglio naturale di `<ListaConfigurabile>`: ordinate dalla più
semplice alla più complessa, così le prime servono da rodaggio.

| ✓ | File | Col. | Lazy |
| --- | --- | --- | --- |
| ✅ 01-08 | `catalogo/components/UomTipiSearchTable.vue` | 4 | sì |
| ✅ 31-07 | `amministrazione/components/CategorieClientiSearchTable.vue` | 5 | sì |
| ✅ 01-08 | `amministrazione/components/EmittenteFiscaleBillingAccountTab.vue` | 5 | sì |
| ✅ 31-07 | `amministrazione/components/UtilitiesTipiRuoloSearchTable.vue` | 5 | sì |
| ✅ 02-08 | `amministrazione/views/AuditLogView.vue` | 5 | sì |
| ✅ 31-07 | `anagrafiche/components/IndirizziSearchTable.vue` | 5 | sì |
| ✅ 03-08 | `vendite/views/ApprovazioniPrezzoListView.vue` | 5 | sì |
| ✅ 01-08 | `amministrazione/views/EmailAccountsListView.vue` | 6 | sì |
| ✅ 01-08 | `amministrazione/views/EmailTemplatesListView.vue` | 6 | sì |
| ✅ 01-08 | `amministrazione/views/EmittentiFiscaliListView.vue` | 6 | sì |
| ✅ 01-08 | `catalogo/components/ConversioniUomSearchTable.vue` | 6 | sì |
| ✅ 01-08 | `catalogo/components/UnitaMisuraSearchTable.vue` | 6 | sì |
| ✅ 03-08 | `vendite/components/VersioneDrawer.vue` | 6 | sì |
| ✅ 01-08 | `amministrazione/views/EmailLogsListView.vue` | 7 | sì |
| ✅ 01-08 | `config/components/TemplateDocumentiSearchTable.vue` | 7 | sì |
| ✅ 01-08 | `config/components/TemplateAssetSearchTable.vue` | 8 | sì |
| ✅ 01-08 | `pratiche/components/PraticheSearchTable.vue` | 8 | sì |
| ✅ 03-08 | `strumenti/components/CodaLavoriTab.vue` | 8 | sì |
| ✅ 26-09 | `vendite/components/ContrattiBillingAccountDrawer.vue` | 8 | sì — `vendite.contratti` filtrata sul cliente, `useDrawerTabLista` + store `contrattiCliente`; la «decisione 4» non serviva: l'endpoint era gia' paginato e filtrava per cliente. Chiuso anche il troncamento a 50 righe e il filtro di stato fatto sul client |
| ✅ 01-08 | `vendite/components/PromoArticoliSearchTable.vue` | 8 | sì |
| ⏸ dec.4 | `vendite/offerte/components/OffertaEccezioniDrawer.vue` | 8 | — |
| ✅ 01-08 | `amministrazione/components/CategorieClientiListiniSearchTable.vue` | 9 | sì |
| ✅ 31-07 | `amministrazione/components/TipiRuoloTipiIndirizzoSearchTable.vue` | 9 | sì |
| ✅ 01-08 | `amministrazione/views/OperatoriListView.vue` | 9 | sì |
| ✅ 01-08 | `catalogo/components/ArticoliSearchTable.vue` | 9 | sì |
| ✅ 03-08 | `strumenti/components/CodaStampaTab.vue` | 9 | sì |
| ✅ 03-08 | `vendite/components/CommessaGestioneDrawer.vue` | 9 | sì |
| ✅ 2026-07-31 | `vendite/views/LottiListView.vue` | 9 | sì |
| ✅ 03-08 | `vendite/views/SituazioneApertaView.vue` | 10 | sì |
| ✅ 03-08 | `vendite/views/DashboardBacklogView.vue` | 11 | sì |
| ✅ 01-08 | `vendite/components/ListiniSearchTable.vue` | 13 | sì |
| ✅ 03-08 | `vendite/views/DashboardCompetenzaView.vue` | 23 | sì |
| ✅ 22-08 | `vendite/components/LottoDrawer.vue` — **3 liste su 3 tab**, dal Gruppo B | 11 | no |
| ✅ 02-09 | `ui/components/ListaColonnaPermessoPanel.vue` — dal Gruppo B, **non paginata** | 5 | no |
| ✅ 02-09 | `ui/components/ListaDefinizionePanel.vue` — dal Gruppo B, **non paginata** | 6 | no |
| ✅ 02-09 | `ui/components/ListaPresetPanel.vue` — dal Gruppo B, **non paginata** | 8 | no |
| ✅ 02-09 | `ui/components/ListaColonnaPanel.vue` — dal Gruppo B, **non paginata** | 9 | no |

> ➡️ **Due file sono USCITI da questa tabella il 2026-09-02** (decisione di
> Tid): `catalogo/components/ArticoloBomDrawer.vue` (componenti BoM) e
> `vendite/components/ContrattoRigheDrawer.vue` (righe del contratto). Sono
> **righe di un master**, quindi Gruppo B: la loro casa è
> `RigheMasterDetailTable` / `SearchDetailTable`, non `<ListaConfigurabile>`.
> ⚠️ Il denominatore passa da **39 a 37** per RICLASSIFICAZIONE, non per lavoro
> fatto: quei due file non sono stati toccati.
>
> ✅ **`LottoDrawer` — CONVERTITO il 2026-08-22.** È il **35°** file del
> gruppo: i tre tab sono ora tre liste configurabili
> (`vendite.lotto_fatture` 45, `vendite.lotto_task_runs` 46,
> `vendite.lotto_segnalazioni` 47), con paginazione, ordinamento server-side e
> colonne personalizzabili. Il totale passa da 34 a 35 file e il registro del
> presidio da 43 a **46 codici**.
>
> ⛔ **Le tre ragioni per cui non era convertibile sono state tolte una per
> una**, ed è il motivo per cui questo file è rimasto fermo un giorno invece di
> essere convertito male:
> * il tab **documenti** aveva l'endpoint paginato ma una whitelist di **3
>   voci** su 11 — cinque colonne di nucleo non ordinavano. Ora sono 11, e la
>   chiave `nominativo` è diventata `ragione_sociale_completa` perché la
>   freccia ordina solo se la chiave coincide col campo del payload;
> * il tab **task** non era paginato e aveva **due sorgenti divergenti** (una
>   funzione DB mai chiamata che ordinava al contrario del backend). Ora la
>   sorgente è la funzione, e la `SELECT` scritta a mano non c'è più;
> * il tab **segnalazioni** non aveva righe — solo sei contatori. Ora ha
>   `vendite.fn_list_lotto_segnalazioni`, che unisce le due origini.
>
> ⭐ **Lo stato paginato è un composable, non tre copie**:
> [`useListaDrawerPaginata`](../../../../frontend/src/core/composables/useListaDrawerPaginata.js)
> — tre liste nello stesso file volevano dire tre `onPage`/`onSort`
> identici, cioè tre occasioni di dimenticare l'azzeramento della pagina al
> cambio ordinamento. Quarto consumatore naturale: `CommessaGestioneDrawer`,
> che ha la stessa forma scritta a mano.
>
> ✅ **Export CSV/XLSX su tutte e tre** (2026-08-22): tre endpoint
> `/lotti/<id>/{fatture,task-runs,segnalazioni}/export/` sul BB condiviso
> (`parse_export_format` + `build_export_response`), colonne dal catalogo.
> ⛔ **Nessun lavoro DB**: il seed marca già `esportabile=t` su tutte le
> colonne dati (solo `azioni` è `f`, ed è giusto).
> ⚠️ **`max_rows` e non `page_size`**: l'export SALTA la paginazione invece di
> violarne il tetto — due limiti per due usi diversi, e confonderli significa o
> una pagina enorme o un file troncato in silenzio. Il tetto vero
> (`EXPORT_MAX_ROWS`) lo presidia il BB, che confronta il `count` esatto.
>
> Piano DB, passata BE e ordine dei lotti:
> [brief-db-liste-drawer-lotto.md](../work-done/brief-db-liste-drawer-lotto.md).

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

##### Primo lotto dopo lotti — ✅ 4 liste CONVERTITE e validate in-app (2026-07-31)

> Il blocco sotto è la consegna del team DB, lasciata com'era. Esito della
> conversione FE: **tutte e quattro fatte e validate in-app da Tid**, e la
> previsione si è avverata — costo una frazione di `vendite.lotti`, perché
> avevano già store, `useSearchTable` e ordinamento BE. Zero lavoro backend.

**Cosa è servito davvero, per lista:** sostituire `useSearchTable` con
`useListaConfigurabilePage`, `<DataTable>`+`<Column>` con
`<ListaConfigurabile codice="…">`, spostare le celle custom negli slot
`cell-{codice}`, e cancellare il blocco `pageActions` scritto a mano. Le
specificità sono state preservate: `v-show` dell'empty-state e
`data-key="indirizzo_dettaglio_id"` su indirizzi, editing inline (ToggleSwitch
e Select con `@click.stop`) sulla matrice tipi_ruolo × tipi_indirizzo.

**Due lezioni nuove, che valgono per le prossime 29:**

6. 🔵 **Le azioni «Nuovo» ed «Esporta» sono ora CONDIZIONALI nel building
   block.** Queste quattro liste non hanno endpoint di export, e lo scaffolding
   includeva l'azione sempre: sarebbero nate con un pulsante che apre un dialog
   inerte. Ora `export` compare solo con `exportFn` e `new` solo con `onNew`.
   Effetto collaterale utile: il `filter(a => a.key !== 'new')` che era
   duplicato in 3 file (`ResiSearchTable`, `ResiCodaTable`, `LottiListView`) è
   stato **rimosso** — non serve più. Non reintrodurlo.
7. ⚠️ **`@row-click` cambia firma**: `<ListaConfigurabile>` emette `data`
   direttamente, `<DataTable>` emetteva l'evento PrimeVue. Ogni
   `onRowClick(event) { emit('row-click', event.data) }` va diventare
   `onRowClick(data)`. Silenzioso: non rompe il build, rompe il click.

**Igiene da non saltare**: tolti gli import diventati orfani (`computed`,
`MANAGE_ICONS`, `displayDate`) — il lint li prende, ma solo se lo si lancia.
Le chiavi i18n `col_*` **non** diventano orfane: le referenzia il seed via
`etichetta_i18n_key` (44 colonne sulle 5 liste convertite).

**Presidio esteso, non duplicato**: il test di allineamento seed↔whitelist è
stato generalizzato in `apps/core/tests/test_liste_configurabili_seed.py` —
tabella `_LISTE`, una riga per lista convertita, `subTest` per lista. Copre
tutte e 5. In `test_lotti_lista_configurabile.py` è rimasto solo ciò che è
specifico dei lotti (cap export, whitelist condivisa lista/export). **Per la
prossima conversione: aggiungere una riga a `_LISTE`, non un file di test.**

##### La consegna del team DB (2026-07-31)

> **Convenzione dell'inventario**: `☐` da fare · `☐ 🔵` **seed DB già pronto**,
> la lista è convertibile senza aspettare nessuno e senza rigenerare niente ·
> `✅ gg-mm` convertita e validata. Queste quattro sono passate da 🔵 a ✅ in
> giornata, quindi al momento nessuna riga porta 🔵 — il marcatore serve al
> prossimo lotto seedato.

Scelte perché **l'ordinamento server-side esiste già** in tutte e quattro
(`_ORDER_COLS` nei rispettivi repository) e le chiavi di quelle whitelist sono
già i nomi **fisici** — cioè proprio ciò che il seed mette in `campo_sorgente`.
La lezione n.1 lì costa zero, ed è il motivo per cui questo lotto viene prima
delle 5 cockpit, dove ordinamento **ed** export sono da scrivere per ciascuna.

| Lista | `lista_id` | Colonne | Visibili | `vista_sql` |
| --- | --- | --- | --- | --- |
| `anagrafiche.categorie_clienti` | 13 | 7 | 5 | `categorie_clienti` (tabella) |
| `config.utilities_tipi_ruolo` | 14 | 7 | 5 | NULL — campi joinati |
| `anagrafiche.indirizzi` | 15 | 7 | 5 | `vw_indirizzi_dettaglio` |
| `config.tipi_ruolo_tipi_indirizzo` | 16 | 12 | 9 | NULL — campi joinati |

Righe `217..249` nei quattro CSV, **nessun changeset**. Applicate in transazione
di prova e rollbackate; l'ordine delle colonne visibili è **identico a quello di
oggi** in tutte e quattro.

Cosa sapere prima di convertire i `.vue`:

- ✅ **Invariante della lezione n.1 già verificata**: ogni colonna `ordinabile=t`
  ha il `campo_sorgente` dentro la whitelist del suo repository. Nessuna
  whitelist BE da scrivere — resta da replicare il **test** di allineamento.
- ⚠️ **Due colonne sono `ordinabile=f` apposta**: `fallback_codice` e
  `fallback_descrizione` (lista 16) non sono in `_ORDER_COLS`. Se le si vuole
  ordinabili va estesa la whitelist **e poi** il seed, in quest'ordine.
- **Zero nuove chiavi i18n**: le extra invisibili riusano `common.data_insert` /
  `common.data_update`. L'unica senza chiave è `fallback_descrizione`, che cade
  sull'etichetta italiana del catalogo.
- **Nessuna colonna `azioni`**: nessuna delle quattro ha un kebab di riga, quindi
  la lezione n.5 non si applica — non crearla per simmetria.
- **`vista_sql` valorizzato su due liste**: lì il guard
  `trgfn_ui_lista_colonna_a10_valida_campo_sorgente` valida davvero i campi. Sulle
  due matrici resta NULL perché `tipo_ruolo_descrizione` & c. nascono da JOIN e
  non esistono in nessuna singola relazione.
- **`ordinamento_default` del preset** replica il default che il BE già applica
  (`ordinamento`, `utility_descrizione`, `indirizzo_normalizzato`,
  `tipo_ruolo_descrizione`): al primo caricamento la lista non si riordina sotto
  gli occhi dell'operatore.

#### ✅ CHIUSA — commessa BE: whitelist di ordinamento (2026-07-31)

> **Stato al 2026-07-31, verificato sul pushato** (`origin/Tito-dev`,
> «Aggiornamento come da test-fn-get-evento-stato-corrente-cliente-v1.sql e
> piano-migrazione-primevue-5.md»): il BE ha eseguito **tutta** la tabella qui
> sotto. Ricontrollato meccanicamente leggendo le whitelist dal sorgente
> pushato e incrociandole col seed: **11 liste su 12 a residuo zero** nelle due
> direzioni.
>
> - `_DEBITO_WHITELIST_LOGICA` è ora **`frozenset()`** — il registro di debito
>   non si è ridotto, si è **svuotato**;
> - `_LISTE` legge le due code resi da `_CODA_META` invece che da
>   `_ORDER_COLS_RESI`: la correzione che avevamo segnalato è applicata;
> - `date_insert` su soggetti è stato **scritto giusto** (`data_insert`,
>   qualificato `s.data_insert` perché la query joina tre tabelle che hanno
>   tutte i campi audit) invece che tolto — la strada che avevamo indicato come
>   alternativa. Non è un residuo: il test intersecta la whitelist con le
>   colonne del catalogo, quindi una capacità tenuta pronta per una colonna che
>   ancora non c'è è legittima.
>
> ⚠️ **Resta aperta una sola voce**, ed è **posteriore** a questo lavoro:
> `partita_iva` su `_EMITTENTI_ORDER_COLS`, che nasce col secondo lotto di seed
> (vedi il blocco «Secondo lotto» più sotto). È una rottura del nucleo, una riga.
>
> Nota di metodo: la nostra misura contava anche `data_insert` su soggetti come
> residuo. Sbagliato — la definizione del test è più precisa della nostra:
> `(whitelist ∩ catalogo) − ordinabili`. Una whitelist **può** legittimamente
> conoscere campi che la lista non mostra.

##### La commessa, per riferimento — tutte le righe sono state eseguite

> Consegna del team DB del 2026-07-31. **Nessuna modifica al seed era richiesta
> al BE**: le celle di competenza DB erano già cambiate. Il ragionamento
> completo è in §9 («Debito "freccia che non ordina"»); questa era la lista
> operativa.

##### Prima di leggere la tabella: l'id fiscale è UNA colonna sola, per disegno

Le liste **non** mostrano il codice fiscale e la partita IVA separati. Mostrano
`id_fiscale_univoco_cf_piva`, la colonna **unificata** (`GENERATED ALWAYS`:
vale il CF oppure la P.IVA), ed è una scelta deliberata — una colonna sola
invece di due mezze vuote.

I nomi in gioco sono due e non vanno scambiati:

| | Nome | Dove si usa |
| --- | --- | --- |
| Nome della colonna (`codice`) | `id_fiscale` | slot FE `cell-id_fiscale`, preferenze utente |
| Campo letto (`campo_sorgente`) | `id_fiscale_univoco_cf_piva` | **è questo che va in whitelist** |

Scambiarli è precisamente ciò che ha prodotto il difetto.

> **Correzione applicata al seed il 2026-07-31.** Su clienti e soggetti quella
> colonna si chiamava `codice_fiscale` pur mostrando l'id fiscale unificato —
> unico caso su 9 liste, ovunque altrove era già `id_fiscale`. Il nome bugiardo
> è **la radice del difetto**: chi ha scritto `_CLIENTI_ORDER_COLS` e
> `_SOGGETTI_ORDER_COLS` ha messo in whitelist `codice_fiscale` leggendo il
> nome della colonna, non il campo che legge. Ora il `codice` è `id_fiscale` su
> tutte e 9, e l'`etichetta_estesa` dice cosa contiene davvero.
>
> **Ricaduta FE, minima**: `ClientiSearchTable.vue:191` e
> `SoggettiSearchTable.vue:152` hanno uno slot `#cell-codice_fiscale` che ora
> non aggancia più. Non è una regressione: senza slot la cella cade sul
> formatter di serie, che legge `data[campo_sorgente]` — **lo stesso identico
> valore**. I due slot si possono **cancellare** invece che rinominare (quello
> di clienti ha anche un fallback `|| codice_fiscale || partita_iva` che è
> codice morto: se la colonna generata è NULL lo sono anche le due sorgenti).
> Restano 2 preferenze utente salvate che citano il vecchio codice: siamo in
> sviluppo, si ripuliscono a mano ([[project_no_produzione_solo_sviluppo]]).

⚠️ **Ci sono voci da TOGLIERE, non solo da aggiungere** — è la parte che si
salta leggendo in fretta, ed è quella che fa fallire il presidio. Il test
`test_seed_offre_tutto_cio_che_il_backend_sa_ordinare` controlla anche il verso
opposto: una voce in whitelist che **nessuna colonna del catalogo usa** è una
capacità irraggiungibile, e va rimossa. Nessuna delle rimozioni sotto perde un
ordinamento realmente offerto all'operatore.

| Repository | ➕ Aggiungere | ➖ Togliere |
| --- | --- | --- |
| `_CLIENTI_ORDER_COLS` | `id_fiscale_univoco_cf_piva`, `data_sospensione`, `data_riattivazione` | `codice_fiscale` |
| `_SOGGETTI_ORDER_COLS` | `id_fiscale_univoco_cf_piva` | `codice_fiscale`, `partita_iva`, `date_insert` |
| `_FORNITORI_ORDER_COLS` | `id_fiscale_univoco_cf_piva`, `data_update` | `attivo`, `codice_fiscale`, `partita_iva` |
| `_ORDER_COLS_ORDINI` | `imponibile_tot`, `iva_tot`, `anno`, `serie`, `utility_descrizione` | `stato_codice_interno` |
| `_ORDER_COLS_DDT` | `anno`, `serie` | `stato_codice_interno` |
| `_ORDER_COLS_OFFERTE` | `data_accettazione`, `data_rifiuto`, `data_annullamento` | `stato_codice_interno`, `data_update` |
| `_ORDER_COLS_CONTRATTI` | — | `emittente_fiscale_codice`, `stato_codice`, `stato_codice_interno` |
| `_ORDER_COLS_PREVENTIVI` | — | `emittente_fiscale_codice`, `stato_codice_interno` |
| `_ORDER_COLS_RESI` | — | `stato_codice_interno` |
| `_EMITTENTI_ORDER_COLS` | `partita_iva` | — |

**Perché queste aggiunte e non altre.** Sono tutte applicazioni della stessa
regola di dominio (nucleo sempre ordinabile) o del criterio di simmetria che ne
discende: `id_fiscale_univoco_cf_piva` è **nucleo** su clienti, soggetti e
fornitori; `anno`/`serie` sono l'identità del documento accanto al `numero`;
`imponibile_tot`/`iva_tot` stanno accanto a `totale`; le date di ciclo vita
(`data_accettazione`/`rifiuto`/`annullamento` su offerte, `data_sospensione`/
`data_riattivazione` su clienti, `data_update` su fornitori) hanno le sorelle
dello stesso gruppo già ordinabili. **Tutto il resto è già stato portato a
`ordinabile=f` nel seed**: 30 colonne, lavoro DB, già fatto.

Due note sulle rimozioni, oltre a quelle già dette:

- **`stato_codice_interno` compare in 6 whitelist su 9** ed è sempre lo stesso
  caso: colonna tecnica che dà la severity al Tag di stato, nel seed
  `ordinabile=f` e invisibile. Verificato che **nessun repository la usa come
  ordinamento di default** (i default sono `data`, `data_insert`,
  `tipo_ruolo_descrizione`…), quindi toglierla non cambia comportamento.
- **`codice_fiscale` e `partita_iva` su `_FORNITORI_ORDER_COLS`** sono diventate
  orfane il 2026-07-31, **su richiesta del BE**: le due colonne omonime del
  catalogo (id 28 e 29) sono state disattivate (`attivo=f`). `fornitori` era
  l'unica lista del sistema a esporre tre colonne fiscali insieme; ovunque
  altrove ce n'è una sola, `id_fiscale`, che punta al campo `GENERATED`.
  Nessuna informazione va persa: l'espressione generata **concatena** CF e
  P.IVA quando ci sono entrambe e differiscono, non ne sceglie una.
- **`data_update` su `_ORDER_COLS_OFFERTE`** è un caso a parte: è mappata di
  proposito su `v.data_insert` come compatibilità all'indietro, con tanto di
  commento. Nessuna colonna la richiede. Toglierla è coerente col presidio, ma
  è l'unica rimozione che cancella una scelta deliberata: decidete voi.

🔵 **Correzione al registro `_LISTE` del presidio.** `vendite.resi_da_accreditare`
e `vendite.resi_da_riconsegnare` sono registrate con `_ORDER_COLS_RESI`, ma **non
è la loro whitelist**: le due code usano `_CODA_META[<vista>]["order_cols"]`
(`resi_repository.py`), che sono due mappe distinte e — verificato — **già
perfette**, chiavate sui `campo_sorgente`, zero residuo in entrambe le direzioni.
Finché restano nel registro di debito i test 1-3 le saltano e l'errore non si
vede; togliendole di lì senza correggere la costante andrebbero rosse per un
motivo falso. È lo stesso equivoco che ha ingannato anche la nostra prima
misura, che le contava fra le peggiori.

Perché ciascuna rimozione è sicura:

- **`stato_codice_interno`** (ordini) — è la colonna tecnica che dà il colore al
  Tag di stato: nel seed è `ordinabile=f` e invisibile, nessuno la ordina.
- **`codice_fiscale`** e **`partita_iva`** (clienti, soggetti) — sono i due
  campi **separati**, e nessuna colonna di queste due liste li mostra: mostrano
  l'unificato (vedi sopra). Toglierli **non** toglie niente all'operatore.
  Nota: su `anagrafiche.fornitori` invece esistono davvero come colonne
  distinte, accanto a `id_fiscale` — lì restano al loro posto.
- **`date_insert`** (soggetti) — **è un refuso**: la colonna si chiama
  `data_insert`. **Rettifica del 2026-07-31**: una stesura precedente qui
  parlava di «errore 500», ed era allarmista. Dall'interfaccia non può
  succedere: il frontend manda solo `campo_sorgente` di colonne esistenti, e
  `date_insert` non è il campo di nessuna colonna. Il danno reale è più
  banale e più probabile: se domani si aggiunge ai soggetti una colonna
  *Creazione* / *Data movimento* (`campo_sorgente = data_insert`, come già su
  12 liste su 16), **non ordinerà**, perché `data_insert` ≠ `date_insert`. Due
  strade, entrambe accettabili: toglierla, oppure **scriverla giusta**.

> ℹ️ **Se si vuole la colonna «Data movimento» sui soggetti** servono tre cose,
> in quest'ordine: (1) l'API deve restituirla — oggi il `SELECT` della lista
> soggetti **non** include `data_insert`, quindi è lavoro BE; (2) la riga nel
> seed, che facciamo noi (il modello c'è già identico su 12 liste: `datetime` +
> `datetime_short`, invisibile di default); (3) `data_insert` scritto bene in
> whitelist. Senza il punto 1 gli altri due non servono a niente.

**Esito, verificato sul pushato**: tutte e 11 le liste a residuo zero nelle due
direzioni, `_DEBITO_WHITELIST_LOGICA` svuotato. La previsione era «applicata
questa tabella il registro non si riduce, si svuota»: è andata così.

##### Secondo lotto — ✅ 3 liste CONVERTITE (seed 2026-07-31, conversione 2026-08-01)

> **Esito, verificato sul pushato**: tutte e tre montano `<ListaConfigurabile>`
> (`PraticheSearchTable`, `EmittentiFiscaliListView`,
> `EmittenteFiscaleBillingAccountTab`), le **tre chiavi i18n** che il seed
> dichiarava sono state aggiunte a `it.json`/`en.json`, le tre liste sono state
> registrate in `_LISTE` (con una funzione dedicata per la whitelist annidata
> del tab BA), e **`partita_iva` è entrata in `_EMITTENTI_ORDER_COLS`**: l'unica
> voce che il lotto chiedeva. Ricontrollato incrociando whitelist e seed:
> **residuo zero nelle due direzioni** su tutte e tre.

| Lista | `lista_id` | Colonne | Visibili | Lavoro BE |
| --- | --- | --- | --- | --- |
| `pratiche.pratiche` | 17 | 10 | 8 | nessuno |
| `anagrafiche.emittenti_fiscali` | 18 | 9 | 6 | 1 voce di whitelist ✅ fatta |
| `anagrafiche.emittente_billing_account` | 19 | 6 | 5 | nessuno |

Righe `250..274` nei quattro CSV, `vista_sql` NULL su tutte e tre (i campi
nascono da JOIN). Applicate in transazione di prova e rollbackate; l'ordine
delle colonne visibili è quello di oggi.

**Due liste su tre non chiedono niente al backend**: `pratiche` e il tab
billing account hanno whitelist complete e già chiavate sui `campo_sorgente` —
zero bugiarde e zero capacità irraggiungibili, in entrambe le direzioni. Sono
le prime liste seedate che nascono già in regola.

✅ L'unica voce che il lotto chiedeva — **`partita_iva` su
`anagrafiche.emittenti_fiscali`**, rottura del nucleo perché per un emittente la
P.IVA *è* l'identificativo fiscale — è stata aggiunta a
`_EMITTENTI_ORDER_COLS` il 2026-08-01.

Da sapere prima di convertire i `.vue`:

- **La colonna «Default» del tab billing account non è una colonna calcolata.**
  Nel `.vue` è una `<Column>` senza `field` che disegna un Badge, ma il dato
  esiste (`is_default`) ed è pure ordinabile: nel seed è una colonna vera con
  `campo_sorgente = is_default`, tipo `boolean`. Serve solo lo slot
  `cell-is_default` per tenere il Badge.
- **L'identificatore non è la prima colonna** su quella lista: è `Codice BA`,
  che sta in seconda posizione. La colonna non-nascondibile dev'essere quella
  che identifica la riga, non quella che capita per prima.
- **Tre chiavi i18n da aggiungere**: `pratiche.col_descrizione`,
  `amministrazione.emittenti_fiscali.col_valuta` e `…col_regime_fiscale`. Sono
  già dichiarate nel seed e servono a tre colonne **invisibili di default**;
  finché non ci sono, il `te()` di `<ListaConfigurabile>` fa fallback
  sull'etichetta italiana del catalogo. Tutte le altre esistono già.
- **Colonne extra invisibili**: `descrizione` e `data_insert` su pratiche
  (entrambe ordinabili: la lista mostra il codice ma non la descrizione, che il
  BE sa già cercare e ordinare), `valuta`/`regime fiscale`/`data_insert` su
  emittenti, `data_insert` sul tab BA.

##### Terzo lotto — le 3 liste UoM di `catalogo` — ✅ 3 liste CONVERTITE (seed 2026-07-31, conversione 2026-08-01)

> **Esito, verificato sul pushato** (`9afa5d277`): tutte e tre montano
> `<ListaConfigurabile>` (`UomTipiSearchTable`, `UnitaMisuraSearchTable`,
> `ConversioniUomSearchTable`), sono registrate in `_LISTE` del presidio seed, e
> **le tre voci `attivo` sono state aggiunte** alle rispettive whitelist — cioè
> l'unica cosa che il lotto chiedeva. Alla chiusura di questo lotto il residuo
> di allineamento del sistema era **zero**: nessun seed in attesa di conversione
> — condizione poi riaperta, per scelta, dal **quarto lotto** seedato lo stesso
> giorno.
>
> Due cose fatte **oltre** la richiesta, entrambe da registrare perché generano
> lavoro:
>
> 1. **`ApiConversioniUomList` è diventata un endpoint lista vero**
>    (`is_search_endpoint`, `parse_list_params`, `paginated_envelope`, i cinque
>    query param): prima le tre sorelle UoM non parlavano la stessa lingua, ora
>    sì. È il prerequisito che rendeva la terza lista convertibile davvero e non
>    solo a video.
> 2. 🔵 **`valido_dal`/`valido_al` sono già in `UOM_CONVERSIONI_ORDER_COLUMNS`**,
>    con la motivazione scritta accanto: «le date di validità, quando una lista
>    le mostra, ordinano SEMPRE — e `valido_al` è il default d'elezione». Il BE
>    le ha messe **prima** del seed apposta per non aprire la finestra di frecce
>    bugiarde alla consegna, e la nota dice esplicitamente «il seed delle due
>    colonne è in arrivo dal team DB». **È una richiesta a noi**: il piano le
>    dava come opzionali («dirlo e diventano due righe»), il pre-cablaggio della
>    whitelist è il modo in cui il BE ha detto sì. Servono le due righe di seed
>    **più due chiavi i18n**, che qui non esistono ancora — vedi il registro §9.

| Lista | `lista_id` | Colonne | Visibili | `vista_sql` |
| --- | --- | --- | --- | --- |
| `catalogo.uom_tipi` | 20 | 6 | 4 | `uom_tipi` (tabella) |
| `catalogo.unita_misura` | 21 | 9 | 6 | NULL — campi joinati |
| `catalogo.conversioni_uom` | 22 | 6 | 6 | NULL — campi joinati |

Righe `275..295`. **L'ordinamento server-side per queste tre non c'era, e nel
frattempo il BE l'ha aggiunto** (`UOM_TIPI_ORDER_COLUMNS`, `UOM_ORDER_COLUMNS`,
`UOM_CONVERSIONI_ORDER_COLUMNS` in `catalogo_repository.py`), quindi il lotto è
partito da una base che non esisteva quando l'avevamo scartato. Applicate in
transazione di prova e rollbackate.

✅ **L'unica cosa che il lotto chiedeva — `attivo`, ripetuta tre volte — è stata
fatta il 2026-08-01.** Non era in nessuna delle tre whitelist mentre la colonna
*Attivo* era visibile su tutte e tre: una **rottura del nucleo** (lo stato
ordina sempre), con lo stesso precedente delle quattro liste del primo lotto.

| Whitelist | ➕ Aggiunta | Stato |
| --- | --- | --- |
| `UOM_TIPI_ORDER_COLUMNS` | `attivo` → `ut.attivo` | ✅ |
| `UOM_ORDER_COLUMNS` | `attivo` → `u.attivo` | ✅ |
| `UOM_CONVERSIONI_ORDER_COLUMNS` | `attivo` → `c.attivo` | ✅ |

⚠️ Nel farlo il BE ha lasciato scritto sopra le mappe l'avvertenza che vale la
pena non perdere: **gli alias non sono intercambiabili fra le tre query** —
`ut` è `uom_tipi` in due di esse ma è l'unità di misura di *destinazione* nella
terza. Una mappa copiata dalla sorella sbagliata ordinerebbe sulla colonna di
un'altra tabella senza che nulla protesti.

A parte quello: **zero bugiarde e zero capacità irraggiungibili** su tutte e
tre, e **zero nuove chiavi i18n** — le colonne extra invisibili riusano
`common.data_insert` / `common.data_update`.

Da sapere prima di convertire i `.vue`:

- **`catalogo.uom_tipi` ha `vista_sql` valorizzato** sulla tabella base: tutti i
  suoi campi vengono da lì, quindi il guard `campo_sorgente` fa un lavoro vero.
  Le altre due joinano e restano NULL.
- **Colonne non ordinabili per scelta**, perché il BE non le espone e non sono
  nucleo: `tipo_uom_codice`, `tipo_uom_descrizione` e `descrizione_fattura` su
  `unita_misura`; `uom_from_descrizione` e `uom_to_descrizione` su
  `conversioni_uom` (le rispettive colonne *codice* ordinano). Se servono, sono
  altre voci di whitelist — ma nessuno le ha chieste.
- ✅ **`valido_dal` / `valido_al` di `conversioni_uom`: chiuse in entrambe le
  direzioni.** Erano state lasciate opzionali («dirlo e diventano due righe»);
  il seed le ha scritte (`lista_colonna` **296-297**) e il BE aveva
  **pre-cablato** le voci in `UOM_CONVERSIONI_ORDER_COLUMNS` e le chiavi i18n
  *prima* della consegna, apposta: la finestra di frecce bugiarde non si è
  aperta nemmeno per un commit. È il verso giusto della sequenza, ed è la prima
  volta che ci riesce.
  > ⚠️ **Rettifica 2026-08-01.** Una revisione precedente di questo paragrafo
  > dichiarava «il seed no» — era **falso**, e lo era già quando è stato
  > scritto: le due righe erano in `lista_colonna.csv`. La frase era stata
  > riportata da una stesura più vecchia senza ri-guardare il CSV. Segnalato dal
  > BE. Vale la regola di §0: i numeri e gli stati di questo documento vanno
  > **ri-misurati**, non ricopiati.
- **`conversioni_uom` non ha colonna azioni**: nel `.vue` non c'è kebab di riga.

##### Quarto lotto — ✅ CHIUSO: seed + 3 liste CONVERTITE (2026-08-01)

> **Chiuso in giornata, su entrambe le sponde.** Righe di seed nei quattro CSV
> (liste **23-25**, colonne **298-320**, preset 23-25); il BE ha evaso **tutte e
> 12** le voci di whitelist — non solo le due che bloccavano — e il controllo di
> consegna è passato da «1 su 3» a **25 liste allineate in tutte e tre le
> direzioni**. ✅ **I tre `.vue` sono stati convertiti** lo stesso giorno
> (`fb59cc5a4` e il commit precedente per `promo_articoli`).
>
> La selezione è stata fatta **misurando**, non leggendo l'inventario, e la
> misura ha ribaltato l'ordine del piano.

| Lista | `lista_id` | `.vue` | Mostra | Ordina | Consegna |
| --- | --- | --- | --- | --- | --- |
| `vendite.promo_articoli` | 23 | `vendite/components/PromoArticoliSearchTable.vue` | 8 | **8** | ✅ ok |
| `documenti.template_documenti` | 24 | `config/components/TemplateDocumentiSearchTable.vue` | 7 | **7** | ✅ ok |
| `documenti.template_asset` | 25 | `config/components/TemplateAssetSearchTable.vue` | 8 | **8** | ✅ ok |

**Come sono nate le colonne che il backend non sapeva ordinare, e come si sono
chiuse.** Sono nate `ordinabile = f`, non `t`: una colonna che promette
l'ordinamento e poi lo vede ripiegare in silenzio sul default è il difetto più
caro che questo seed possa produrre, perché a video sembra funzionare. Il BE ha
poi aggiunto **tutte e 12** le voci, e le 12 righe sono state **ribaltate a `t`**
— una lettera per riga, e a dire quali è stato il controllo di consegna, non la
memoria di qualcuno. È il ciclo completo per cui `ordinabile = f` esiste: non un
ripiego, ma lo stato onesto di una colonna finché il backend non la regge.

Tre decisioni prese seguendo il precedente delle liste già seedate, non il
suggerimento del generatore: **`codice` coincide con `campo_sorgente`** (niente
rinomina logica: `<ListaConfigurabile>` monta le Column su `campo_sorgente`, e
due nomi diversi per la stessa cosa sono due cose da tenere allineate);
**`vista_sql = NULL` su tutte e tre**, perché tutte espongono campi che vengono
da JOIN e non dalla tabella base; **ordinamento di default allineato a quello
del repository** (`valido_dal` desc per le promo, `codice` asc per i due
template), così la prima schermata non chiede al backend un ordinamento che non
sa fare.

**Perché non le prossime dell'inventario.** L'elenco del Gruppo A è ordinato per
numero di colonne, «dalla più semplice alla più complessa». Ma la difficoltà
vera non è quella: è **se il backend sa già ordinare**. `AuditLogView` e
`ApprovazioniPrezzoListView` sono le prossime per colonne e sono fra le meno
pronte — nessuna whitelist. Le tre liste email stanno peggio:
`email_repository.py` non ha **nessuna** mappa di ordinamento, quindi quel lotto
comincerebbe dal backend e non dal seed. Seedarle adesso vorrebbe dire
consegnare liste con le frecce che non ordinano: il difetto che
`--verifica-ordinamento` esiste per intercettare, ricreato di proposito.

⚠️ **E «ha una whitelist» non basta**, lezione di questa selezione: le whitelist
di `documenti` esistono ma hanno 5-6 voci che coprono soprattutto colonne di
audit **che la lista non mostra**. Il criterio giusto è l'incrocio fra colonne a
video e whitelist, non la presenza della costante. Di liste davvero pronte ne
esiste **una sola**, `promo_articoli`.

###### ✅ La richiesta al BE — chiesta come passata unica, evasa come passata unica

`attivo` **mancava dalla whitelist di ogni lista non ancora convertita** — le tre
del lotto e anche `catalogo.articoli` e `vendite.listini` che verranno dopo. Non
era un difetto per lista: era sistemico, e chiederlo un lotto per volta avrebbe
significato mandare cinque volte la stessa richiesta. È stata proposta come
**una passata sola**, ed è così che il BE l'ha fatta il 2026-08-01: la loro nota
nel codice cita «la stessa voce mancava su **nove** whitelist e sarebbe arrivata
un lotto per volta». `catalogo.articoli` e `vendite.listini` hanno ora `attivo`
**in anticipo sul proprio seed**: quando arriverà il loro lotto, la voce c'è già.

Evase **tutte e 12** le voci, non solo le due che bloccavano:

| Lista | ➕ Aggiunte alla whitelist | Stato |
| --- | --- | --- |
| `vendite.promo_articoli` (`_ORDER_COLS`) | `tipo_variazione` | ✅ |
| `documenti.template_documenti` (`TEMPLATES_ORDER_COLUMNS`) | `attivo`, `emittente_fiscale_descrizione`, `is_default`, `sorgente_tipo_descrizione`, `tipo_documento_output_descrizione` | ✅ |
| `documenti.template_asset` (`ASSET_ORDER_COLUMNS`) | `attivo`, `asset_tipo_descrizione`, `emittente_fiscale_descrizione`, `file_name`, `file_size_bytes`, `mime_type`, `valido_al` | ✅ |

⚠️ **La distinzione che ha retto lo scambio, e vale per i lotti futuri.** Delle
12 voci una sola classe bloccava: **`attivo`**, perché lo stato appartiene al
nucleo. Le altre erano colonne che *potevano* restare non ordinabili senza che
nulla fosse rotto — e infatti erano già nate `ordinabile = f`. Separare «cosa
blocca la consegna» da «cosa la migliora» ha permesso al BE di decidere invece
di eseguire, e conviene continuare a scrivere le richieste così.

💡 **Un dettaglio tecnico che il BE ha lasciato scritto e vale la pena tenere**:
le descrizioni joinate (`emittente_fiscale_descrizione`, `asset_tipo_descrizione`,
`sorgente_tipo_descrizione`, `tipo_documento_output_descrizione`) sono mappate
**sull'alias di output nudo** e non su `tabella.colonna`, perché sono alias della
`SELECT` — e `emittente_fiscale_descrizione` in particolare è un `COALESCE`, che
`ORDER BY` risolve **solo** per alias. Una whitelist scritta col riflesso
`prefisso.colonna` avrebbe prodotto SQL non valido su quelle quattro.

✅ **Fatto da parte nostra**: le tre liste sono mappate in `WHITELIST_BE` dentro
`scripts/gen_seed_lista.py` — senza, il controllo di consegna le **salterebbe**
dichiarandole a posto, e una lista saltata in silenzio è come non aver fatto il
controllo. Poi le **12 righe ribaltate** a `ordinabile = t`. Esito finale:
**25 liste allineate col backend in tutte e tre le direzioni** (erano 22).

⚙️ **Nota operativa sul generatore — risolta il 2026-08-01.**
`gen_seed_lista.py` interroga `information_schema` per i tipi reali delle
colonne e importa `psycopg` v3, che stava solo in `backend/.venv`: sul server DB
la `.venv` degli strumenti aveva `psycopg2` v2, e la generazione non partiva.
`psycopg[binary]==3.3.4` è stato installato negli strumenti dev **con ok
esplicito di Tid** e messo in `requirements.txt` (stessa versione del backend,
`pip check` pulito). Da ora il seed si genera anche dal server DB. Il
**controllo** di consegna non ha mai avuto questo vincolo: non usa il DB e gira
ovunque ci sia il repo.

##### Quinto lotto — ✅ CHIUSO: seed + 3 liste CONVERTITE, senza attese (2026-08-01)

> **Il primo lotto che nasce senza rompere il nucleo su nessuna delle tre**, ed è
> il dividendo della passata `attivo`: due di queste liste l'avevano già in
> whitelist *prima* di essere scelte. Liste **26-28**, colonne **321-345**,
> preset 26-28. Controllo di consegna **ok su tutte e tre al primo passaggio**;
> **zero chiavi i18n nuove**.
>
> ✅ **Convertito lo stesso giorno** (`fb59cc5a4`), senza che nessuna delle due
> sponde abbia dovuto aspettare l'altra: seed e `.vue` sono atterrati nella
> stessa giornata in cui il lotto è stato scelto. È il primo a riuscirci.

| Lista | `lista_id` | `.vue` | Col. | Ordina | `vista_sql` |
| --- | --- | --- | --- | --- | --- |
| `catalogo.articoli` | 26 | `catalogo/components/ArticoliSearchTable.vue` | 9 | 4 | `vw_articoli_dettaglio` |
| `vendite.listini` | 27 | `vendite/components/ListiniSearchTable.vue` | 7 | 5 | NULL — subquery aggregate |
| `anagrafiche.operatori` | 28 | `amministrazione/views/OperatoriListView.vue` | 9 | 6 | NULL — `auth_user` + 6 JOIN |

`catalogo.articoli` è la **prima lista del binario con una vista vera**
(`catalogo.vw_articoli_dettaglio`): `vista_sql` è valorizzato e il guard
`campo_sorgente` fa un lavoro reale, come su `catalogo.uom_tipi`.

⚠️ **Un errore di misura evitato dal generatore, che vale più del lotto.** Una
misura fatta a mano su `ListiniSearchTable.vue` aveva contato **8** colonne e
dichiarato `codice_versione` come rottura del nucleo che avrebbe **bloccato** il
lotto. Falso: quel `.vue` ha **due** `<DataTable>`, e `codice_versione` /
`righe_count` appartengono alla **seconda** — la tabella annidata delle versioni,
che è Gruppo B e non va su `<ListaConfigurabile>`. Il generatore legge la prima
`<DataTable>` (e ha `--tabella` per scegliere), quindi aveva ragione lui. La
lezione è secca: **un grep sul file non è una misura della lista**, perché un
`.vue` può contenere più tabelle. Dove il generatore e una misura a mano
divergono, ha ragione il generatore.

###### Le 6 voci di whitelist da chiedere al BE — nessuna blocca

| Lista | ➕ Da aggiungere | Blocca? |
| --- | --- | --- |
| `catalogo.articoli` (`ARTICOLI_ORDER_COLUMNS`) | `tipologia_descrizione`, `gruppo_descrizione`, `iva_ref_id`, `is_solo_componente` | no |
| `vendite.listini` (`LISTINI_ORDER_COLUMNS`) | `versioni_count` | no |
| `anagrafiche.operatori` (`ALLOWED_ORDER_COLUMNS`) | `emittenti_descrizione` | no |

Tutte nate `ordinabile = f`, come da prassi. `attivo`/`is_active` sono già in
whitelist su tutte e tre — è **il dividendo della passata**: il nucleo è coperto
in partenza, e per la prima volta la consegna non aspetta nessuno.

⚙️ **Due buchi dello strumento chiusi per poter misurare questo lotto**, entrambi
sulla lista più pronta: il lettore di whitelist non riconosceva la forma
`NOME = frozenset({...})` (usata da `amm_software`), quindi `operatori` sarebbe
stata **saltata** dal controllo — cioè dichiarata a posto senza essere guardata;
e la regola del nucleo cercava `stato`/`attivo` e non `is_active`, quindi avrebbe
segnalato «nucleo rotto» su una lista che lo stato lo ordina eccome. Un falso
allarme ripetuto insegna a ignorare il controllo, ed è il modo in cui un presidio
muore.

##### Sesto lotto — ✅ CHIUSO: 5 liste CONVERTITE, `storico.audit_log` compresa (2026-08-01/02)

> **Aggiornamento 2026-08-02, verificato sul pushato.** Il BE ha convertito
> **quattro** delle cinque (`8983528ac`): le tre email e
> `CategorieClientiListiniSearchTable`, con la riga in `_LISTE`. La quinta,
> `AuditLogView`, l'hanno **sospesa** con una motivazione scritta nel test:
> «il seed non ha la colonna calcolata *Dettaglio*, che la pagina mostra».
> **Avevano ragione**: il `.vue` ha 5 `<Column>` e il seed ne portava 4 —
> l'ultima è quella senza `field=`, che rende `rowSummary(data)`. Colonna
> **378** aggiunta a `lista_colonna.csv` (`campo_sorgente` vuoto, tutti i flag
> `f`, `attivo=t`) + riga `32,378,50,t,f` in `lista_preset_colonna.csv`, sul
> precedente di `anagrafiche.operatori` (341 `ruolo`) e `anagrafiche.clienti`
> (14 `sosp_riatt`). Nessun changeset: i loader `runOnChange` la ripescano.
> Chiave i18n `amministrazione.audit_col_dettaglio` **già esistente**.
>
> 🔴 **È il terzo errore sulla stessa lista, e sempre nella parte scritta a
> mano.** Prima quattro chiavi i18n inventate, poi una colonna intera saltata.
> `storico.audit_log` è l'unica lista che il generatore non può produrre
> (polimorfa) ed è l'unica su cui abbiamo sbagliato due volte: la correlazione
> non è casuale. **Dove lo strumento non arriva, contare le `<Column>` del
> `.vue` prima di dichiarare il seed completo** — qui bastava `4 ≠ 5`.
>
> Liste **29-33**, colonne **346-378**, preset 29-33. **Zero chiavi i18n nuove.**
> Nato dalla mappa di prontezza qui sotto: la famiglia email era il blocco più
> grosso rimasto, è stata chiesta al BE **prima** di scegliere il lotto, e loro
> l'hanno preparata — quindi il lotto è arrivato con tre liste già pronte invece
> che con tre richieste da fare.

| Lista | `lista_id` | `.vue` | Col. | Ordina | Consegna |
| --- | --- | --- | --- | --- | --- |
| `config.email_account` | 29 | `amministrazione/views/EmailAccountsListView.vue` | 6 | **6** | ✅ ok |
| `config.email_template` | 30 | `amministrazione/views/EmailTemplatesListView.vue` | 6 | 5 | ✅ ok |
| `config.email_log` | 31 | `amministrazione/views/EmailLogsListView.vue` | 7 | 6 | ✅ ok |
| `storico.audit_log` | 32 | `amministrazione/views/AuditLogView.vue` | 4 → **5** | **4** | ✅ convertita 02-08 |
| `anagrafiche.categorie_clienti_listini` | 33 | `amministrazione/components/CategorieClientiListiniSearchTable.vue` | 9 | 6 | ⛔ nucleo |

🔴 **L'unica voce da chiedere**: `emittente_ragione_sociale` in `_ORDER_COLS` di
`categorie_clienti_listini_repository`. **È nucleo** — la ragione sociale ordina
sempre — quindi blocca quella lista e solo quella. Le altre tre non ordinabili
(`classe_utenza_codice`, `tipo_variazione`, e l'emittente stesso) sono nate
`ordinabile = f`.

**La passata email ha reso due liste su tre complete al 100%**, e nessuna delle
cinque rompe il nucleo per colpa nostra. È la seconda conferma dello schema:
chiedere il lavoro BE **prima** di scegliere il lotto, non in consegna.

⚠️ **`storico.audit_log` è una lista POLIMORFA**, l'unica finora. Non legge una
tabella: legge `storico.{code}` scelta a runtime da `script.vw_audit_sources`, e
proietta alias sintetizzati (`tabella` ← `code`, `user_modifica` ← `user_insert`).
Quindi `vista_sql` resta NULL e i tipi si mettono a mano — non c'è un
`information_schema` da interrogare, perché non c'è **un** oggetto. Il
generatore non la può produrre da solo, e va scritta a mano sapendo perché.

> ⚠️ **E scrivendola a mano ho inventato quattro chiavi i18n** invece di
> leggerle dal `.vue` (`amministrazione.audit_timestamp` e sorelle, mentre le
> vere sono `audit_col_data`, `audit_col_tipo`, `audit_col_operazione`,
> `audit_col_chi`). Corrette. Il generatore le deduce dalle etichette e non
> sbaglia: **il pezzo scritto a mano è quello in cui si sbaglia**, ed è
> esattamente il pezzo che il generatore non poteva coprire.

##### Mappa di prontezza delle liste rimaste (misurata 2026-08-01)

> **A cosa serve.** L'inventario del Gruppo A è ordinato per numero di colonne,
> ma tre lotti hanno dimostrato che la difficoltà vera è un'altra: **se il
> backend sa già ordinare e paginare**. Questa mappa dice quali liste sono
> pescabili subito e quali richiedono lavoro BE *prima* della conversione — che
> è la domanda che il BE ha chiesto esplicitamente di anticipare in consegna.

| Lista / `.vue` | Whitelist di ordinamento | Pescabile? |
| --- | --- | --- |
| `AuditLogView` | `_AUDIT_ORDER_COLUMNS` (attributo di classe, `frozenset`) | ✅ **seedata**, lotto 6 |
| `CategorieClientiListiniSearchTable` | `_ORDER_COLS` | ✅ **seedata**, lotto 6 |
| `EmailAccountsListView` · `EmailTemplatesListView` · `EmailLogsListView` | ~~nessuna~~ → ✅ tre whitelist + endpoint paginati (BE, `fb59cc5a4`) | ✅ **seedate**, lotto 6 |
| `ApprovazioniPrezzoListView` | ✅ `_PRATICHE_ORDER_COLS` (10 voci) — passa da `cerca_pratiche`; il service **inchioda** `order_by="data_insert"` | 🔵 far passare il parametro |
| `CodaLavoriTab` | ✅ `_ELENCA_SORT_SQL` (4 voci) + endpoint con `sort_by`/`sort_dir` | 🔵 estendere la whitelist |
| `CodaStampaTab` | ✅ `_CODA_STAMPA_SORT_SQL` (3 voci) + endpoint con `sort_by`/`sort_dir` | 🔵 estendere la whitelist |
| `SituazioneApertaView` · `DashboardBacklogView` · `DashboardCompetenzaView` | `query_paged_view` (`order_by` è un suo parametro) — **e i `.vue` ordinano già**: 4 · 6 · 12 colonne `sortable` con `@sort` | 🔵 rinviate per scelta |
| `VersioneDrawer` (righe di versione listino) | ✅ `RIGHE_ORDER_COLUMNS` (`listini_repository`), 8 voci | ⛔ **non per la whitelist**: vedi sotto |
| `CommessaGestioneDrawer` (righe commessa) | ❌ nessuna — `ORDER BY id` fisso, e il `.vue` non emette nemmeno `@sort` | 🔵 lavoro BE |

🔴 **Ri-misurata il 2026-08-02: la mappa sbagliava su cinque righe su sei, e
sempre nello stesso verso — dava per assente un ordinamento che c'era.**

| Diceva | È |
| --- | --- |
| `ApprovazioniPrezzo`: «nessuna whitelist» | la whitelist esiste ed è quella delle pratiche: il service ci passa attraverso e **inchioda** il valore in [`approvazioni_prezzo_service.py:624`](../../../../backend/apps/vendite/services/approvazioni_prezzo_service.py#L624) |
| le due code: «nessuna, ordinano per `id DESC`» | **entrambe** hanno una whitelist e un endpoint che accetta `sort_by`/`sort_dir`; il default di `CodaStampa` è `data_update DESC`, non `id` |
| le dashboard: «da verificare caso per caso» | ordinano **già oggi**, sia lato `.vue` sia lato BE |

Il motivo dell'errore è sempre lo stesso, ed è il terzo caso in due giorni dopo
`AuditLogView` e `CategorieClientiListini`: **la whitelist è stata cercata nel
repository che porta il nome della lista**. Queste la tengono altrove — in un
service condiviso (`cerca_pratiche`), in un `ClassVar` dentro la classe, o
dietro un helper generico. ➡️ **La domanda giusta non è «esiste un
`_ORDER_COLS` in quel file», è «questo endpoint, oggi, accetta un
ordinamento».** Si risponde leggendo la catena view→service→repository, che è
poi lo stesso limite già scritto per il presidio: confronta una costante, non
l'endpoint che la attraversa.

⚠️ **Le ultime due righe mancavano alla misura del 2026-08-01** — la mappa ne
copriva 11 sulle 13 lazy rimaste, e queste due erano state saltate, non
valutate. Aggiunte il 2026-08-02. È lo stesso modo in cui `AuditLogView` e
`CategorieClientiListini` erano finite fuori misura: **una lista che nessuno
guarda non è una lista senza problemi.**

🔴 **`VersioneDrawer` ha l'ordinamento e non basta.** La sua `<DataTable>` non
monta le righe dello store paginato ma un computed `righeUnificate`, che fonde
`store.items` con i **compositi** caricati a parte (`loadBundleCompositi`,
fuori dalla paginazione). `<ListaConfigurabile>` ha `lazy` **fisso** e prende
`total` dal caller: con righe aggiunte dopo la paginazione, conteggio e pagine
mentirebbero. Non è un allineamento di whitelist, è la domanda «i compositi
sono righe della lista o un'altra cosa» — cioè una decisione, come le altre sei.

✅ **La leva più grande era la famiglia email — ed è stata tirata.** Tre liste
ferme sulla stessa mancanza, in un solo repository: chiesta come **passata
unica prima di scegliere il lotto**, il BE ha aggiunto le tre whitelist
(`EMAIL_ACCOUNT_/TEMPLATE_/LOG_ORDER_COLUMNS`) e portato le tre view alla forma
di `ApiConversioniUomList` — `parse_list_params`, `order_by`/`order_dir`,
`paginated_envelope`. Risultato: le tre liste sono entrate nel sesto lotto già
verdi, due delle quali complete al 100%.

> **Il metodo che ha funzionato due volte** (`attivo`, poi email): guardare il
> residuo **prima** di comporre il lotto, isolare il blocco che vale più liste,
> e chiederlo come passata unica. La stessa richiesta spezzata in tre consegne
> sarebbe costata tre giri e avrebbe prodotto tre lotti con le frecce morte.

⚠️ **Due correzioni a una lettura precedente**, entrambe da misura sul file
sbagliato: `AuditLogView` era stata data come «nessuna whitelist» guardando
`session_audit_repository.py`, mentre la sua vive in `amm_software_repository.py`;
e `CategorieClientiListiniSearchTable` non era stata guardata affatto. La
conclusione che ne era seguita — «aspettare la famiglia email e farne uno da
cinque» — si è rivelata giusta: è esattamente il sesto lotto.

**Cosa resta dopo il sesto** (aggiornato 2026-08-02 a conversione avvenuta,
**12 liste**): `ApprovazioniPrezzoListView` (decidere *se* debba essere
ordinabile, prima di seedarla: oggi l'`order_by` è cablato), le due code
(l'ordine `id DESC` è il loro contenuto informativo, renderle ordinabili è una
scelta di dominio), le tre dashboard da guardare una per una, `VersioneDrawer`
(i compositi fuori paginazione), `CommessaGestioneDrawer` (nessun ordinamento,
né BE né FE) e i quattro drawer senza endpoint paginato.

`AuditLogView` era la **tredicesima e l'unica meccanica**: sbloccata dalla
colonna 378 e convertita il 2026-08-02. Da qui in avanti **nessuna delle dodici
è un allineamento meccanico: sono tutte decisioni** — e conviene affrontarle in
blocco, non una lista per volta, perché tre di esse (le due code e
`ApprovazioniPrezzoListView`) sono la stessa domanda posta a oggetti diversi:
*un ordine implicito è un dato o un default?*

##### ✅ Le quattro decisioni — prese da Tid il 2026-08-02

Le dodici non erano dodici problemi ma **quattro domande**, ognuna posta a più
liste. Le risposte, e cosa ne consegue:

| # | Domanda | Decisione | Effetto |
| --- | --- | --- | --- |
| 1 | L'ordine delle code è un dato o un default? | **Default → ordinabili** | 3 liste entrano nel 7° lotto |
| 2 | Le dashboard vanno personalizzate? | **Sì, come le altre — ma per ultime** | 3 liste rinviate, non escluse |
| 3 | I due drawer si uniformano? | **Sì, entrambi** | 2 liste, di cui 1 con una domanda aperta |
| 4 | Vale la paginazione per i 4 cassetti? | **Per ora no** | 4 liste ferme |

**1 — Le code sono un default, quindi ordinabili.** `CodaLavoriTab`,
`CodaStampaTab`, `ApprovazioniPrezzoListView`. La misura qui sopra dice che
costano molto meno di quanto il piano dichiarava: **nessuna delle tre parte da
zero.** Per le due code la whitelist esiste e l'endpoint accetta già
`sort_by`/`sort_dir` — va solo estesa alle colonne del nucleo e il `.vue` deve
emettere `@sort`. Per le approvazioni la whitelist è addirittura completa (10
voci): basta smettere di inchiodare il valore nel service e lasciar passare il
parametro dalla view.

**2 — Le dashboard sono cruscotti, ma si trattano come le altre.** Motivo di
Tid: **ordinano già oggi** (e la misura lo conferma: 4, 6 e 12 colonne
`sortable`), quindi il salto è corto; e l'export CSV — che il building block dà
gratis — su un cruscotto è più utile che altrove. **Restano per ultime** per
scelta, non per difficoltà: sono le tre più grosse e nessuno le sta aspettando.

**3 — I due drawer si uniformano a tutte le altre liste.**
`CommessaGestioneDrawer` ordina per **`data_attivita` (default)** e
**`segment_key`** — entrambe colonne che il `.vue` già mostra, quindi nessun
campo nuovo da esporre. ⚠️ Su `VersioneDrawer` «uniformare» **implica una
risposta alla domanda dei compositi**, che resta l'unica aperta delle dodici: se
la lista è una sola, i compositi devono arrivare **dal server insieme alle altre
righe** e non essere attaccati dopo, altrimenti totale e pagine mentono. È
lavoro BE sull'endpoint, non un allineamento di whitelist.

**4 — I quattro cassetti restano come sono.** `ArticoloBomDrawer`,
`ContrattiBillingAccountDrawer`, `ContrattoRigheDrawer`,
`OffertaEccezioniDrawer`: caricano tutto in una volta e il building block ha
`lazy` fisso, quindi servirebbero quattro endpoint paginati nuovi prima di
toccare la parte visibile. Su cassetti da poche righe è tutto costo e nessun
beneficio.

➡️ **Il 7° lotto sono le 5 liste dei punti 1 e 3** — e per il metodo che ha già
funzionato due volte (`attivo`, poi la famiglia email), il lavoro BE va chiesto
come **passata unica prima di comporre il lotto**, non in consegna. Cosa
**blocca** (nucleo, quindi la consegna aspetta) e cosa **migliora** vanno
separati nella richiesta, così il BE decide invece di eseguire.

##### ✅ Settimo lotto — SEEDATO il 2026-08-02, 3 liste convertibili subito

| Lista | `lista_id` | `.vue` da convertire | Col. | Ordina | Apertura |
| --- | --- | --- | --- | --- | --- |
| `dbops.coda_lavori` | 34 | `strumenti/components/CodaLavoriTab.vue` | 8 | 6 | `started_at desc` |
| `vendite.fatture_stampa_coda` | 35 | `strumenti/components/CodaStampaTab.vue` | 9 | 7 | `data_update desc` |
| `vendite.approvazioni_prezzo` | 36 | `vendite/views/ApprovazioniPrezzoListView.vue` | 5 | 3 | `data_insert desc` |

**Nessuna delle tre aspetta nessuno**: il presidio le dà allineate in tutte e
tre le direzioni, e i preset replicano i default che il BE già applica — quindi
al primo caricamento la lista non si riordina sotto gli occhi dell'operatore.

⚠️ **Una sola coda lato FE**: su `vendite.approvazioni_prezzo` il `.vue` monta
ancora `field="priorita_codice"` mentre il seed ordina per
`priorita_descrizione` (decisione Tid su proposta BE). Vanno allineati insieme
alla conversione, e l'API deve esporre la descrizione nella riga.

🔵 `CommessaGestioneDrawer` **non è in questo lotto**: il DB ha fatto la sua
parte (`20260802-26`), ma prima del seed serve che BE e FE facciano passare
`order_by`/`order_dir` fino alla funzione. Vedi «Cosa resta aperto» in §9.

##### 📋 Commessa BE per il 7° lotto — misurata il 2026-08-02

Colonne dei cinque `.vue` incrociate con la whitelist di ciascuno. Tutti e
cinque hanno **una sola** `<DataTable>`, quindi il conteggio è affidabile (la
trappola di `ListiniSearchTable` non si applica).

🔴 **Blocca la consegna** — è nucleo, e senza queste la lista nasce con una
freccia che non ordina:

| Lista | Voce da aggiungere | Famiglia di nucleo | Esito |
| --- | --- | --- | --- |
| `CodaLavoriTab` | `stato` | stato | ✅ BE |
| `CodaStampaTab` | `stato` · `emittente_codice` | stato · numero/codice | ✅ BE |
| `ApprovazioniPrezzoListView` | ~~`priorita_codice`~~ | ~~numero/codice~~ | ⛔ **RITIRATA** |
| `CommessaGestioneDrawer` | `data_attivita` · **uno fra** `stato_approvazione` / `stato_emissione` | data · stato | ✅ DB, ma **non in whitelist** |
| `VersioneDrawer` | *(nessuna: il nucleo è già coperto)* | — | — |

> ⚠️ **Due voci di questa tabella erano indirizzate male, e il BE l'ha detto.
> Corrette il 2026-08-02.**
>
> - **`priorita_codice` è RITIRATA.** Non era aggiungibile alla whitelist, e
>   soprattutto non era il problema: quello vero era una **colonna vuota**, già
>   risolto lato FE. Il seed della lista 36 usa `campo_sorgente =
>   priorita_descrizione` (decisione Tid su proposta BE), e con il `codice`
>   logico `priorita` la famiglia *numero/codice* non si attiva nemmeno.
>   Chiedere quella voce sarebbe stato far lavorare il BE su un sintomo.
> - **Le due voci di `CommessaGestioneDrawer` non erano voci di whitelist.**
>   Ordine e paginazione vivono **dentro `fn_list_commessa_attivita`**: il BE
>   non aveva un punto in cui metterle. Si risolvono lato DB, ed è ciò che fa
>   `20260802-26` — la whitelist chiusa della funzione include `data_attivita`,
>   `stato_approvazione` e `stato_emissione`, quindi il nucleo *stato* che
>   avevamo segnalato scoperto è coperto lì.
>
> ➡️ Regola che ne esce: **prima di scrivere una voce di commessa, verificare
> che il destinatario abbia un posto dove metterla.** Una richiesta indirizzata
> allo strato sbagliato costa un giro a entrambi, e la seconda l'avevamo
> generata proprio noi segnalando un nucleo scoperto senza dire *dove* andasse
> chiuso.

🔵 **Migliora, non blocca** — se non arrivano, la colonna nasce
`ordinabile = f` e si ribalta quando la voce c'è (è già successo con `attivo`):

| Lista | Voci |
| --- | --- |
| `CodaStampaTab` | `id` · `operatore` |
| `ApprovazioniPrezzoListView` | `id` |
| `VersioneDrawer` | `iva_aliquota` |
| `CommessaGestioneDrawer` | `competenza_mese` · `segment_key` · `quantita` · `prezzo_snapshot` |

⚙️ **Due lavori che non sono voci di whitelist**, e sono i più grossi dei cinque:

1. **`ApprovazioniPrezzoListView` — far passare il parametro.** La whitelist è
   già completa (`_PRATICHE_ORDER_COLS`, 10 voci): il service chiama
   `cerca_pratiche(..., order_by="data_insert", order_dir="desc")` con i valori
   **inchiodati** ([`approvazioni_prezzo_service.py:624`](../../../../backend/apps/vendite/services/approvazioni_prezzo_service.py#L624)).
   Serve che view e service li accettino e li inoltrino. È l'unica delle cinque
   dove il lavoro è di **cablaggio**, non di dominio.
2. **`VersioneDrawer` — i compositi.** La `<DataTable>` monta un computed che
   fonde le righe paginate dal server con i compositi caricati a parte. Il BB ha
   `lazy` fisso e prende `total` dal caller: con righe aggiunte dopo la
   paginazione, conteggio e pagine mentono. **Decisione presa: la lista è una
   sola**, quindi i compositi devono arrivare **dall'endpoint insieme alle
   altre righe**. Finché non lo fanno, questa lista non è seedabile: è l'unica
   delle cinque che ha un prerequisito, non una richiesta.

⚠️ **Una conseguenza da segnalare a Tid, perché la decisione presa non basta.**
Su `CommessaGestioneDrawer` la richiesta era «ordine per data (default) e
segmento». `data_attivita` copre la famiglia *data*, ma `segment_key` **non è
nucleo**, e il nucleo *stato* resta scoperto: la lista ha `stato_approvazione` e
`stato_emissione`, nessuna delle due ordinabile. O se ne rende ordinabile
almeno una, o la lista nasce con il presidio rosso. Non è una svista della
decisione: è che la regola del nucleo chiede una cosa in più di quella che si
vede guardando la pagina.
> ➡️ **Aggiornamento 2026-08-02 (BE): la passata BE del 7° lotto è FATTA** per
> le due code e le approvazioni — whitelist estese al nucleo e inchiodatura
> rimossa. `CommessaGestioneDrawer` è risultata **bloccata lato DB** (ordine e
> paginazione vivono dentro `fn_list_commessa_attivita`), non priva di
> whitelist come diceva questa riga. Dettaglio, verifica e **le 4 consegne al
> team DB** nella voce di registro §9 «Settimo lotto — la passata BE».

#### Gruppo B — righe di documento e anteprime (32 file)

Dentro drawer, dialog e pannelli. **Non** vanno su `ListaConfigurabile`:
il loro equivalente è `RigheMasterDetailTable` / `SearchDetailTable`, o
un wrapper sottile da estrarre alla seconda occorrenza
([[feedback_regola_del_2_estrai_bb]]).

> ⚠️ **«Annidata» non è una categoria sola** (2026-08-21). Il criterio con cui
> questo gruppo è stato formato — *tabella dentro un contenitore, senza
> paginator* — mette insieme due cose diverse: la tabella di **righe** di un
> documento (che è davvero un dettaglio del master, e resta qui) e la
> **lista su tab** di un'entità che ha vita propria, popolazione arbitraria e
> un endpoint suo. La seconda è una lista a tutti gli effetti: le manca il
> paginator, non la natura.
>
> ⭐ **`LottoDrawer.vue` è il primo caso riclassificato**: i suoi tre tab
> (documenti, tentativi dei task, segnalazioni) **passano al Gruppo A**.
> Il seed e il lavoro DB che li precede — due dei tre tab oggi non hanno un
> endpoint paginato, e uno non ha nemmeno una sorgente di righe — stanno in
> [brief-db-liste-drawer-lotto.md](../work-done/brief-db-liste-drawer-lotto.md).
> ⚠️ Se ne emergesse un secondo, la regola del 2 dice di **riscrivere il
> criterio del gruppo**, non di spostare un'altra riga a mano.

> ## ✅ Il secondo è emerso — criterio RISCRITTO (2026-09-01)
>
> Il caso è `EmittenteFiscaleRegistriTab`, il tab dei registri di numerazione
> del drawer emittente
> ([brief-be-fe-crud-registri-di-numerazione](../work-done/brief-be-fe-crud-registri-di-numerazione.md)
> §10). ⇒ Come questa nota prescriveva, non si sposta una riga: si riscrive il
> criterio, e il gruppo si legge da qui in avanti così.
>
> ### Il criterio, in tre domande — la prima decide
>
> | Domanda | Se sì |
> | --- | --- |
> | ⭐ **L'entità ha vita propria** — un endpoint suo, una popolazione arbitraria, un ciclo di vita indipendente dal padre? | **Gruppo A**: `<ListaConfigurabile>` + `useDrawerTabLista` + `DrawerTabLista`. Le manca il paginator, non la natura |
> | ~~Sono le **righe** del documento che la contiene (righe ordine, componenti BoM, righe reso)?~~ | ⛔ **Domanda ritirata il 2026-09-28** (decisione di Tid, [brief-db-liste-righe-documento](brief-db-liste-righe-documento.md) §1): un documento ha un numero **arbitrario** di righe con molti attributi, quindi le righe **sono** una lista e rispondono sì alla prima domanda — **Gruppo A**. `RigheMasterDetailTable` monta ora `<DrawerTabLista>`. Resta Gruppo B solo il dettaglio espanso della ricerca (`SearchDetailTable`) |
> | È una **matrice slot/override** — la popolazione la decide il catalogo (LEFT JOIN su tutte le voci ammesse), l'operatore compila le celle? | 🔴 **Nessuna delle due**, vedi il buco qui sotto |
>
> ⛔ **«È dentro un drawer» e «non ha il paginator» NON sono più il criterio.**
> Erano un fatto di forma, e la forma è la conseguenza: un tab-lista non ha il
> paginator perché nessuno gliel'ha ancora messo, non perché non gli serva.
>
> ### ⭐ Il wrapper sottile che questa sezione chiedeva ESISTE
>
> Il testo del gruppo diceva *«un wrapper sottile da estrarre alla seconda
> occorrenza»*. La seconda occorrenza è arrivata, e il wrapper è stato estratto
> il **2026-09-01** (ok di Tid), in **tre** pezzi separati per mestiere:
>
> | Pezzo | Cosa |
> | --- | --- |
> | [`core/composables/useDrawerTabLista.js`](../../../../frontend/src/core/composables/useDrawerTabLista.js) | il legame col padre: `watch` immediate, reset filtri, doppia fetch |
> | [`core/components/DrawerTabLista.vue`](../../../../frontend/src/core/components/DrawerTabLista.vue) | lo scheletro: help + `testata` + toolbar + `<ListaConfigurabile>`, slot inoltrati per nome |
> | [`core/utils/bloccoMotivo.js`](../../../../frontend/src/core/utils/bloccoMotivo.js) | la frase di un'azione spenta, dalla terna `reason`/`reason_key`/`dettaglio` |
>
> ⛔ **`EmittenteFiscaleBillingAccountTab` ci è stato convertito lo stesso
> giorno**, e non per cortesia: un BB estratto e lasciato accanto alla sua
> copia sono due implementazioni della stessa regola, e la copia diverge in
> silenzio ([[feedback_duplicazione_nasconde_il_bug]]).
>
> ### 🔴 E resta un buco, che questa riclassificazione fa vedere
>
> **La matrice slot/override non ha una casa.** Le due eccezioni della regola
> zero (`frontend-standards` §Regola zero della lista) sono *righe di un
> documento* e *anteprima in un dialog*: una matrice non è né l'una né
> l'altra, eppure `EmittenteFiscaleUtilitiesTab` e `OperatorePermessiTab` sono
> esattamente questo — popolazione dal catalogo, editing inline multi-riga,
> nessun paginator.
>
> ⇒ Oggi restano `DataTable` grezza **senza una motivazione che la regola
> ammetta**, ed è un debito da nominare, non da coprire con un'eccezione
> inventata sul momento. Le due strade, e sono una decisione di Tid:
>
> 1. dare a `<ListaConfigurabile>` l'**editing inline di riga** — è la strada
>    che la regola zero indica quando il BB non basta (*«estendere il BB, non
>    tornare alla DataTable grezza»*), e sblocca **tutte** le matrici insieme;
> 2. riconoscere la **matrice** come terza eccezione e darle il suo wrapper,
>    sul modello di `RigheMasterDetailTable`.
>
> ⚠️ Finché non si sceglie, quei file restano dove sono **con il debito
> scritto**: non è un'omissione, è un rifiuto di chiamare «eccezione» una cosa
> che non lo è.

> ⭐ **Quattro righe sono uscite di qui il 2026-09-02** — i pannelli `ui/`.
> Erano in Gruppo B per il criterio VECCHIO («tabella dentro un contenitore,
> senza paginator»), ma per il criterio in tre domande sono liste a tutti gli
> effetti: entità con endpoint proprio, popolazione arbitraria, ciclo di vita
> indipendente. ⚠️ Il paginator non l'avevano perché **il BB non lo permetteva**
> a chi non paginava lato server — cioè la forma era la conseguenza del cancello,
> non della natura. Caduto il cancello, la classificazione si è raddrizzata da sé.

| ✓ | File | Col. |
| --- | --- | --- |
| ☐ | `amministrazione/components/CollectionEditorPanel.vue` | 2 |
| ☐ | `amministrazione/components/UtilityTipoRuoloDrawer.vue` | 3 |
| ☐ | `amministrazione/views/RepartiProfiloView.vue` | 3 |
| ☐ | `core/components/ScadenzeSintesi.vue` | 3 |
| ➡️ | ~~`amministrazione/views/PermessiRiepilogoView.vue`~~ — **pagina ritirata** il 2026-10-06: il riepilogo è un interruttore *Mostra permessi* della lista `anagrafiche.operatori` (`OperatoriListView.vue`), file cancellato e uscito da `datatable.baseline.json` ([brief-db-riepilogo-permessi-lista-operatori](../work-done/brief-db-riepilogo-permessi-lista-operatori.md) §7) | 4 |
| ✅ 26-09 → **Gruppo A** | `catalogo/components/UomConversioniDrawer.vue` | 4 | criterio in tre domande: le conversioni hanno endpoint e lista loro (`catalogo.conversioni_uom`). Convertito con `useDrawerTabLista` + store `uomConversioni`, fattore modificabile nello slot `cell-fattore`; chiuso il troncamento a 200 righe |
| ☐ | `core/components/SessioniAttivePanel.vue` | 4 |
| ☐ | `vendite/components/AlertScadenzeWidget.vue` | 4 |
| ☐ | `vendite/components/ApplicaVariazioneDialog.vue` | 4 |
| ☐ | `vendite/components/AttivaVersioneDialog.vue` | 4 |
| ☐ | `vendite/offerte/components/OffertaDrawer.vue` | 4 |
| ☐ | `vendite/preventivi/components/PreventiviDrawer.vue` | 4 |
| ☐ | `amministrazione/components/RepartoProfiloEditor.vue` | 5 |
| ☐ | `core/components/RiepilogoIvaTable.vue` | 5 |
| ➡️ | ~~`ui/components/ListaColonnaPermessoPanel.vue`~~ — **al Gruppo A** il 2026-09-02 (`ui.lista_colonna_permesso`, non paginata) | 5 |
| ☐ | `vendite/preventivi/components/dialogs/PreventiviSmistamentoDialog.vue` | 5 |
| ➡️ | ~~`ui/components/ListaDefinizionePanel.vue`~~ — **al Gruppo A** il 2026-09-02 (`ui.lista_definizione`, non paginata) | 6 |
| ☐ | `vendite/ordini/components/dialogs/OrdineEvasioneDialog.vue` | 6 |
| ☐ | `amministrazione/views/DefinizioniWorkflowListView.vue` | 7 |
| ☐ | `catalogo/components/ArticoloUomDrawer.vue` | 7 |
| ☐ | `config/components/TemplateVersioniSection.vue` | 7 |
| ☐ | `core/components/NoteDrawer.vue` | 7 |
| ☐ | `documenti/components/DocumentiGeneratiSorgenteList.vue` | 7 |
| ☐ | `ui/components/ListaPresetColonneDrawer.vue` | 7 |
| ☐ | `amministrazione/views/DefinizioneEditorView.vue` | 8 |
| ☐ | `pratiche/components/PraticaFlussiTab.vue` — due tabelle di **sola lettura**: resta Gruppo B col criterio nuovo | 8 |
| ➡️ | ~~`ui/components/ListaPresetPanel.vue`~~ — **al Gruppo A** il 2026-09-02 (`ui.lista_preset`, non paginata) | 8 |
| ☐ | `vendite/_shared/componenti/ComponentiDialog.vue` | 8 |
| ☐ | `vendite/_shared/componenti/ComponentiPanel.vue` | 8 |
| ☐ | `vendite/components/FatturaDrawer.vue` | 8 |
| ☐ | `vendite/ddt/components/DdtResoDialog.vue` | 8 |
| ☐ | `vendite/resi/components/dialogs/ResoRiconsegnaDialog.vue` | 8 |
| 🔴 | `amministrazione/components/EmittenteFiscaleUtilitiesTab.vue` — **matrice slot/override**: nessuna delle due eccezioni la copre (buco dichiarato sopra) | 9 |
| 🔴 | `amministrazione/components/OperatorePermessiTab.vue` — **matrice slot/override** (tre tabelle di spunte): stesso buco | 9 |
| ☐ | `config/components/ImpostazioniSearchTable.vue` | 9 |
| ➡️ | ~~`ui/components/ListaColonnaPanel.vue`~~ — **al Gruppo A** il 2026-09-02 (`ui.lista_colonna`, non paginata) | 9 |
| ➡️ | ~~`vendite/components/LottoDrawer.vue`~~ — **spostato al Gruppo A** il 2026-08-21 (3 liste su 3 tab) | 11 |

### Le opzioni, per quando sarà il momento

Elencate perché siano note, non per sceglierne una ora:

1. **Restare sulla 4.5.5** congelata (MIT, nessuna scadenza fino a Vue 4).
2. **Accettare la Community License** — ZeroErp con ogni probabilità è idonea;
   ma va allora affrontata l'AGPL (il passaggio GPL → AGPL del 2026-11-02
   non la risolve: ha lo stesso divieto di restrizioni aggiuntive), e restano
   esposti i clienti della licenza commerciale.
3. **Licenza commerciale** — toglie il problema dell'idoneità, non quello
   dell'AGPL verso valle.
4. **Migrare a un'altra libreria** — costo dominato da DataTable, vedi sopra.
5. **Fork comunitario della 4.x** — MIT lo consente a chiunque.

**Il segnale esterno da tenere d'occhio è il punto 5**: con una relicensing di
questa portata un fork è lo sbocco più probabile, e non dipende da noi. Da
notare che rende obsoleto il segnale di §1 («aspetta la prima 5.0.x»): quello
misurava l'adozione, e l'adozione ora è governata dalla licenza, non dalla
maturità.

---

## 9. Registro

### 2026-09-02 · Il drawer dei titoli IVA del soggetto torna sullo standard

Rilievo di Tid in collaudo: *«la lista titoli iva soggetti drawer non è per
niente standard, non ha neanche la possibilità di fare il download o
parametrizzare le colonne e neanche la paginazione»*. Ed era vero: la lista era
una `<ListaConfigurabile>` montata **a mano**, con le righe in due `ref` locali.

⛔ **Il difetto non stava nel componente, stava nel montaggio.** Le tre cose
mancanti — pagine, «Personalizza colonne», export — non sono tre lavori: sono
quello che lo **scaffolding** porta con sé, e che chi monta il BB da solo si
perde tutte insieme. È il motivo per cui una schermata resta indietro **senza
che niente lo dica**: funziona, mostra dati veri, e nessun test è rosso.

Cosa è cambiato, in ordine di dipendenza:

| Dove | Cosa |
| --- | --- |
| `titoli_iva_repository` | `list_titoli_soggetto` accetta `limit`/`offset` e ritorna `(righe, totale)` da **una** valutazione (`fetch_paged_with_total`). ⛔ `count_titoli_soggetto` **cancellata**: era una seconda query sullo stesso predicato, e due valutazioni possono non concordare |
| `titoli_iva_service` | envelope `{results, count}` come ogni altra lista |
| `views_titoli_iva` | GET paginata + **nuovo** `GET .../titoli-iva/export/` (DEF-1, `build_export_response`) |
| `soggettoTitoliIva.js` (nuovo) | store col contratto `useSearchTable` |
| `TitoliIvaSoggettoDrawer.vue` | `useDrawerTabLista` + `<DrawerTabLista>` |
| `DrawerTabLista.vue` | ⭐ inoltra `@row-click`: un contenitore che si tiene un evento del componente che avvolge è un buco silenzioso |

⭐ **`limit` assente = nessuna paginazione**, e non è una comodità: quel metodo
ha un **secondo consumatore** (`SoggettiService`, che incorpora i titoli nel
dettaglio del soggetto). Un `LIMIT` di default avrebbe troncato quella sezione
senza dirlo — lo stesso difetto appena corretto sui sfondati, in un altro posto.

⇒ Conseguenza sul registro: `anagrafiche.soggetto_titoli_iva` **esce** dalla
sentinella `ORDINAMENTO_LOCALE` (ora ordina lato server, quindi i test 1-3 la
coprono) e la sua riga **esce dal ponte** del lotto 2, che resta con la sola 61.

### 2026-09-02 · Cade il cancello del `lazy`, e le 4 liste `ui` entrano dal Gruppo B

Il cambio strutturale della giornata, e in un certo senso l'unico:
`<ListaConfigurabile>` aveva `lazy` e `paginator` **cablati nel template**. Non
era una decisione: era una costante rimasta lì. E finché c'era, il residuo del
Gruppo A era per costruzione irraggiungibile — **13 delle 15 liste rimaste non
hanno paginazione server-side**, quindi ciascuna sarebbe stata una fetta backend
intera (endpoint paginato + whitelist + `count`) per liste che non hanno niente
da paginare.

⭐ Ora la prop `paginata` (default `true`) le separa. Le 55 liste esistenti sono
**invariate** — verificato: nessun consumer passava la prop.

**Il pilota e il suo lotto.** Scelte le 4 liste della pagina tecnica `ui`, e il
pilota è `ui.lista_definizione` per una ragione operativa: è **la lista delle
liste**, quindi si sa quante righe devono uscire (59, lo dice il CSV stesso) e un
troncamento si vede a occhio invece che per deduzione. Seed consegnato al team DB
come richiesta unica per quattro liste e applicato in giornata:
[brief-db-seed-liste-ui-admin](../work-done/brief-db-seed-liste-ui-admin.md).
⭐ **64 righe su 64 atterrate identiche alla specifica**, verificato
meccanicamente contro `origin/Tito-dev` invece che dato per buono.

#### 🔴 La trappola dentro la trappola: un `total` che è un'eco

Il guard anti-troncamento confronta `rows.length` con `total`. Sul pilota
**sarebbe stato una tautologia**: l'endpoint restituiva una lista nuda e lo store
faceva `totalRecords = items.length`, cioè `rows.length === rows.length`.

⚠️ E la correzione ovvia è sbagliata: `success_response({"results": rows,
"count": len(rows)})` **sposta** la tautologia sul server invece di toglierla.
⇒ Il conteggio è una query **sua** (`SELECT count(*)` con lo stesso perimetro
della lista), su tutti e quattro gli endpoint. Quattro test lo fissano: il repo
dichiara 40/12/5/57 e consegna 1 riga, e il service deve **riportare** la
divergenza, non appianarla — sono i test che sarebbero passati lo stesso con
`len(results)`, ed è per questo che servono.

⭐ **Su `count_permessi_by_lista` il `FROM` è ripetuto per intero, JOIN
compresi**: quelli della lista sono INNER e possono togliere righe. Un
`count(*)` sulla sola tabella avrebbe contato di più e acceso il guard su un
troncamento inesistente. *Il conteggio dev'essere indipendente dalle RIGHE, non
dal PERIMETRO.*

#### La riclassificazione, che si è raddrizzata da sé

I 4 pannelli erano in **Gruppo B**. Non ci appartenevano: hanno endpoint proprio,
popolazione arbitraria e ciclo di vita indipendente — prima domanda del criterio
⇒ Gruppo A. ⚠️ Il paginator non ce l'avevano **perché il BB non lo permetteva a
chi non paginava lato server**: la forma era la conseguenza del cancello, non
della natura. Caduto il cancello, la classificazione si è sistemata da sola —
ed è la prova che il criterio del 01-09 era giusto e il gruppo era sbagliato.

#### Revisione critica del proprio codice: sei difetti, cinque corretti

Passata ostile sul lavoro appena scritto. In ordine di gravità:

1. 🔴 **`onSort` chiudeva le righe espanse anche in ordinamento locale.** L'uscita
   anticipata stava *dopo* `resetExpansionSePropria()`. Ma in modalità non
   paginata le righe sono le stesse, solo riordinate: PrimeVue indicizza
   l'espansione per `dataKey`, quindi restava valida — e il reset la buttava via,
   chiudendo sotto gli occhi dell'operatore le righe aperte per leggere le
   colonne ritirate.
2. 🔴 **Il presidio del perimetro emittente era rosso e non me n'ero accorto**:
   non avevo rilanciato quella suite dopo le conversioni. Le 4 liste vogliono un
   cancello o un'esenzione **dichiarata**. ⛔ Scritta per quello che ciascuna è,
   non copiando la motivazione delle vicine: tre tabelle **non hanno**
   `emittente_fiscale_id` (nessun perimetro da sciogliere), mentre
   `ui.lista_preset` ce l'ha — e lì la ragione è che l'ambiguità è già sciolta a
   video dalla colonna «Riferimento», che è la seconda via ammessa da P-2c.
3. ⚠️ **Finestra a 800 caratteri nel test 8-bis**: cercava `:paginata="false"` in
   una finestra fissa. Se fosse caduta oltre, il test sarebbe passato lo stesso —
   **verde per sottrazione**, su un guard nato contro i difetti silenziosi.
   Sostituita con un'estrazione esatta del tag che rispetta le virgolette.
4. **Riscritto quattro volte un BB che esiste**: `fetchone_scalar` in
   `apps/core/db/_helpers.py`, adottato da 7 repository core. Ora lo importano.
5. `:null-sort-order="1"` numero magico → costante con nome, **dopo** aver
   verificato nel sorgente di `@primeuix/utils` che `1` significhi davvero
   «nulls at bottom» (il commento era accurato, ma l'avevo scritto senza
   controllarlo).
6. `eslint-disable no-console` per una regola non attiva — lo diceva ESLint
   stesso: «Unused eslint-disable directive».

⛔ **Non corretto, e dichiarato**: il cablaggio dei 4 pannelli è identico
(`listaRef` + `useListaAzioni` + spread + `ListaConfigStatusTag`), 4 volte su 4.
È la regola del 2 alla quarta occorrenza, ma l'estrazione giusta non è un
wrapper di 3 righe — tre dei quattro condividono anche filtro sul padre,
empty-state e readonly, quindi è uno scaffolding tipo `useDrawerTabLista` per
tab di pagina. Va dichiarato e deciso, non fatto di straforo mentre si correggono
bug.

#### Verifiche

Suite backend **completa: 4345 test OK**. Build frontend verde, ESLint e oxlint
puliti, `check-liste-configurabili.mjs` e `check-pinia-user-scoped-reset.mjs`
verdi. Il guard 8-bis **provato in entrambi i versi**: tolta la prop da un
pannello diventa rosso sulla lista giusta, rimessa torna verde.

⚠️ **Quello che NON è stato visto**: le quattro liste **a video**. I pannelli
trovano la configurazione solo dopo il prossimo `migrate`. Il pilota è quello da
guardare per primo — `ui.lista_definizione` deve mostrare **59 righe**, e un
numero diverso deve dare un errore rosso al posto della tabella, non una lista
corta e silenziosa.

### 2026-09-02 · Ri-misura di tutta la superficie, e tre cose che i numeri fanno vedere

Passata di sole **misure**, senza toccare una riga di frontend: §2, §2-bis, §3,
§8-bis e i denominatori dell'inventario sono stati ri-eseguiti sul repo di oggi.
I valori stanno nelle rispettive sezioni; qui c'è solo ciò che il confronto con
il 2026-07-29 mette in evidenza.

**1. La superficie cresce, ma non dove costa.** `datatable`+`column` è passato da
164 import in 77 file a **124 in 57 file**; i sette primitivi da ~449 a **586**.
In 35 giorni il repo è cresciuto di 48 `.vue` (335 → 383) e sono le uniche due
voci in calo di tutta la tabella. ⇒ Il lavoro del Gruppo A si vede nel numero
caro; la crescita si è spostata sui primitivi, che è il gruppo a difficoltà
bassa — ma è anche **la riga del piano che non è mai stata sviluppata**, e ora
ha una sezione sua in §8-bis.

**2. Seed ↔ presidio divergono di 1, ed è cantiere aperto.** 55 codici in
`ui.lista_definizione`, **54** righe nel registro `_LISTE`: lo scarto è
`vendite.famiglie_documento`, seedata il 2026-09-01, ancora senza consumer
`<ListaConfigurabile>` — oggi il codice è vocabolario per il cantiere dei
registri di numerazione. ⚠️ Confermato da Tid il 02-09: **in costruzione, non una
regressione**. La riga «devono coincidere» resta l'invariante, ma il momento in
cui si verifica è la chiusura del cantiere, non oggi.

**3. Il contatore della regola zero non è il conteggio delle liste da
convertire**, e per tre giorni è sembrato che lo fosse. 57 il 30-08, 57 il 02-09:
piatto, mentre nel mezzo `EmittenteFiscaleBillingAccountTab` veniva convertita
(01-09) e altrettante liste nascevano altrove. ⚠️ E **due file già convertiti
compaiono ancora nel `grep`** — `ListiniSearchTable` (riga di espansione) e
`LottoDrawer` (residuo dichiarato in commento) — perché un file può montare
`<ListaConfigurabile>` **e** una `DataTable`: il `grep` conta i file, non le
tabelle. ⇒ Resta un ottimo **campanello** (se sale, è nata una lista fuori
standard) e un pessimo denominatore.

⛔ **Nessuna riclassificazione fatta in questa passata**, e non per prudenza: le
due cose emerse — gli **11 file fuori inventario** e la coppia
`ArticoloBomDrawer`/`ContrattoRigheDrawer` che il criterio del 01-09 manda in
Gruppo B mentre la tabella li tiene in Gruppo A — sono **decisioni**, non
aggiornamenti di conteggio. Stanno scritte dove servono (§Inventario e §Gruppo A)
come domande aperte.

⚠️ **E vale la regola zero su tutto quanto sopra**: questi numeri sono fatti
datati. Nessuno di essi è la ragione per convertire una lista — quella sta nella
regola zero di `frontend-standards`, e reggerebbe identica con altri numeri.

### 2026-08-24 · La settima sorella — `vendite.vw_fatture_lista` e la lista a catalogo

Scrive il team DB, su richiesta BE. La fattura era **l'unico documento del ciclo
attivo senza vista canonica e senza lista**: esistono `vw_contratti_lista`,
`vw_ddt_lista`, `vw_offerte_commerciali_lista`, `vw_ordini_lista`,
`vw_preventivi_lista`, `vw_resi_lista` — tutte `security_invoker=on` — e le sei
`ui.lista_definizione` corrispondenti. Per le fatture, niente: oggi un documento
fiscale si raggiunge **solo di rimbalzo**, da un lotto, da un cruscotto o da un
collegamento.

**Consegnato** (changeSet `20260824-15`, applicato alle 17:33):

| Cosa | Dove |
| --- | --- |
| `vendite.vw_fatture_lista` | `20_code/vendite` — 51 colonne, `security_invoker=on` |
| `ui.lista_definizione` **48** `vendite.fatture` | `80_data`, CSV — ⛔ **`attivo = f`**, vedi sotto |
| 22 `ui.lista_colonna` (527-548) + preset `fatture_default` | `80_data`, CSV |
| 8 asserzioni pgTAP | `db/pgtap/vendite/test-vw-fatture-lista.sql` — **8/8 verdi come applicazione** |

⭐ **Due cose che la vista fa diversamente dalle sorelle, e sono misure, non
gusto.**

**1. `emittente_fiscale_id` non è una colonna della fattura.** Le sei sorelle ce
l'hanno in tabella; `vendite.fatture` porta `emittente_soggetto_ruolo_id`. Si
deriva da `anagrafiche.emittenti_fiscali.soggetto_ruolo_id`, ed è una
derivazione **sicura** perché quella colonna ha un vincolo di unicità
(`uq_emittenti_fiscali_ruolo`): il join non moltiplica le righe. ⚠️ Verificato
sul catalogo, non dedotto — un join 1:N qui avrebbe raddoppiato le fatture in
lista, che è il modo più silenzioso in cui una lista mente.

**2. ⛔ Un solo JOIN interno, e tutti gli altri LEFT — per la RLS, non per
prudenza.** `anagrafiche.billing_account` **ha quattro policy**, e
`billing_account_id` è NOT NULL sulla fattura: verrebbe naturale un inner join.
Ma le due tabelle risolvono il perimetro con **funzioni diverse**:

```text
vendite.fatture             -> fn_scope_ef_whitelist_via_sr(emittente_soggetto_ruolo_id)
anagrafiche.billing_account -> fn_scope_ef_whitelist_via_efba(id)
```

Una dall'emittente del **documento**, l'altra dalla relazione
emittente↔account. Possono legittimamente divergere — e con un inner join la
fattura, che la **sua** policy lascia passare, sparirebbe perché il cliente non
è visibile. ⚠️ Sarebbe una lista che mostra **meno del dovuto senza nessun
segnale**: un vuoto non si distingue da un «non c'è niente». Col LEFT JOIN la
riga resta e il nome del cliente è vuoto, che è il degrado onesto.
L'unico interno è `config.nature_doc_fiscale`, e solo perché `natura_doc_id` è
NOT NULL con FK — l'unico caso *dimostrabile*, e per questo l'unico.
⭐ **Il test 5 del pgTAP conta i `JOIN` non-LEFT nel corpo e pretende che siano
uno**: se qualcuno ne aggiunge un altro, la prossima corsa lo dice.

⚠️ **Anche le colonne nullable sono LEFT** (`stato_doc_fiscale_id`,
`tipo_doc_fiscale_id`, `utility_id`, `valuta_id`): oggi sono valorizzate su 18
fatture su 18, ma la domanda è «può succedere?», non «è successo?». Una fattura
senza stato deve comparire **senza stato**, non sparire. Il test 6 crea proprio
quella riga.

⭐ **Sul filtro per data il rischio è chiuso dalla forma.** La richiesta
insisteva — *«la data che filtra è quella del DOCUMENTO, non la competenza: una
commessa di competenza giugno fatturata ad agosto produce un documento con data
agosto»* — e la vista non espone **nessuna** competenza, perché
`vendite.fatture` non ne ha una: la competenza vive sul lotto. Sbagliare
colonna, partendo da questa vista, non è possibile.

**⛔ `attivo = f` sulla `lista_definizione`, e non è cautela generica.** La
lista è inerte per costruzione finché non esistono l'endpoint e la rotta, che
sono BE/FE. Con `attivo = f`:

- `fn_resolve_lista_config('vendite.fatture', …)` **fallisce fail-fast*- con
  `E_UI_LISTA_NON_TROVATA` invece di rispondere una configurazione che nessuno
  può usare (verificato in transazione);
- il presidio `gen_seed_lista.py --verifica-ordinamento` **salta le liste
  spente**, quindi non annuncia un debito che non è ancora tale. Il giorno
  dell'accensione, se la whitelist del BE non c'è, diventa rosso — cioè
  l'accensione è **cancellata dal controllo**, non affidata alla memoria.

⭐ **E qui il guard sul `campo_sorgente` C'È**, al contrario della lista
`vendite.lotti`: `trgfn_ui_lista_colonna_a10_valida_campo_sorgente` valida
contro `pg_attribute` solo quando la lista ha una `vista_sql`, e questa ce l'ha.
Provato al contrario, in transazione: una colonna con `campo_sorgente`
inventato viene **rifiutata**. È la differenza pratica fra una lista che nasce
da una vista e una che nasce da SQL nel backend.

**Cosa serve al BE/FE** — la lista non si accende senza tutti e cinque:

1. **endpoint paginato** `GET /api/v1/vendite/fatture/` sulla vista, con la
   policy di ricerca e paginazione, più l'export gemello;
2. **i filtri chiesti da Tid**: `data_da`/`data_a` su `data` (⚠️ la data del
   **documento**), `billing_account_id`, `id_fiscale_univoco_cf_piva`,
   `stato_codice_interno`, e la ricerca testuale sulle quattro colonne marcate
   `ricercabile_full` (`numero`, `ragione_sociale_completa`,
   `id_fiscale_univoco_cf_piva`, `ba_codice`).
   ⭐ **Per l'aggancio dalla scheda soggetto conviene `soggetto_id`**, che la
   vista espone: un identificativo fiscale può cambiare, l'id del soggetto no;
3. **whitelist di ordinamento** chiavata sul `campo_sorgente` (non sul `codice`
   logico), più la voce in `WHITELIST_BE` di `gen_seed_lista.py`. Il preset
   apre su `data desc`, quindi `data` deve esserci;
4. **la rotta e la vista Vue**, che oggi non esistono: è il pezzo che rende
   raggiungibile il documento fiscale senza passare da un lotto;
5. **le chiavi i18n** `vendite.fatture.col_*` (le due di genealogia riusano le
   `vendite.lineage.col_*` già a catalogo).

Poi **una cella**: `attivo` da `f` a `t` sulla riga 48 di
`lista_definizione.csv`.

⚠️ **Due nomi divergono da `vendite.lotto_fatture`**, e non è un errore: quella
lista chiama gli stessi concetti `stato_doc_fiscale_descrizione` /
`stato_doc_fiscale_codice` perché non nasce da una vista — la costruisce il
backend con SQL diretto. Qui si segue il canone delle **viste**
(`stato_codice_interno` / `stato_descrizione`), che è ciò che la richiesta
chiedeva.

📌 **Due candidati lasciati fuori, dichiarati invece che dimenticati**: il
**lotto di appartenenza** sulla riga (questa lista nasce per raggiungere la
fattura *senza* passare dal lotto, quindi il legame inverso è una comodità, non
un requisito) e `multi_emittente = t`, che le sei sorelle hanno tutte a `f`: è
una **capacità che si guadagna** collaudando la schermata, non un valore di
seed. La colonna emittente c'è, quindi il giorno che serve il presidio
`dbops.vw_liste_multi_emittente_non_certificate` non si oppone — resta a zero
righe, verificato.

🔴 **Un rilievo trovato di passaggio, e non è di questo lotto**: le due colonne
`n_fatture` / `totale_documenti` della lista `vendite.lotti` (registro qui
sotto) sono state **accese** — `attivo = t` nel CSV e nel database — mentre il
payload del backend **continua a non produrle** (verificato sul tip di
`origin/dev/backend-tid`, `6a1e23ca5`). Il presidio è di conseguenza **rosso**:

```text
vendite.lotti     KO
    promettono l'ordinamento ma il BE non ce l'ha: n_fatture, totale_documenti
    NUCLEO rotto (deve ordinare sempre)          : totale
```

⭐ **È il cancello che funziona**, non un guasto: era esattamente ciò che
`attivo = f` doveva far succedere all'accensione. Ma finché resta acceso, la
colonna è spuntabile e la cella è vuota — e il presidio resta rosso per tutte
le altre liste, che è il modo in cui un controllo smette di essere letto. Le
due strade sono: rimettere `attivo = f` in attesa del BE, oppure consegnare i
quattro punti elencati sotto. **Non è una decisione del team DB.**

#### 🔧 E una regressione pgTAP sanata di passaggio — `test-riporta-lotto-a-draft-v1.sql`

Non c'entra con le liste, ma è emersa dalla baseline `vendite` di questo lotto
ed è la **stessa classe di difetto** che il file aveva già corretto il
2026-08-22 sul proprio soggetto principale. Vale la pena registrarla dove è
stata trovata.

Il test 11 verifica che il ritorno in bozza rifiuti un lotto le cui righe sono
già state accreditate. La sua fixture prendeva *«l'ultimo lotto con righe
accreditate»* — con l'`ORDER BY`, quindi non era il caso del `LIMIT 1` cieco —
ma **senza la condizione che rende il caso significativo**. E
`fn_riporta_lotto_a_draft` solleva il codice del **primo** motivo
(`v_motivi -> 0 ->> 'codice'`), con i motivi ordinati: lo **stato** viene prima
delle rettifiche. Il 2026-08-24 il lotto più recente con righe accreditate è
diventato il **4212**, in `DEFINITIVA`: la funzione ha risposto — correttamente
— *«il ritorno in bozza è ammesso solo su un lotto in bozza o emesso»*, e il
test è diventato rosso **accusando il codice invece della propria selezione**.
Il **603** (`EMESSA`, unico motivo `RIGHE_RETTIFICATE`) era il soggetto giusto e
c'era.

⛔ **E c'era un secondo difetto, non ancora manifestato**: la fixture
ri-elencava a mano **una** delle quattro sorgenti che
`script.fn_check_fatture_con_rettifiche` guarda (`commesse_attivita`),
ignorando `attivita_fatturabili`, `resi_righe_accrediti` e l'auto-riferimento
fra righe di fattura. Cercava meno soggetti di quanti ne esistano, e su un
database dove l'accredito fosse arrivato per una delle altre tre strade avrebbe
saltato il test dichiarando «caso non riproducibile».

➡️ **Sanato chiedendolo alla funzione**, che è ciò che la fixture principale fa
già dal 22/08: si seleziona il lotto il cui **primo motivo** è
`RIGHE_RETTIFICATE`. Un motivo nuovo che passasse davanti non rompe più il test
— al massimo lo fa saltare, dichiarandolo.

⭐ **E l'asserzione è passata dalla frase al CODICE.** C'era un `throws_like` sul
testo del messaggio, ed è il canale sbagliato su cui legarsi: **la prova è dello
stesso giorno**, perché il passo T-3b ha riscritto il messaggio 937 per togliere
gli id dalla prosa. Un messaggio si riscrive quando serve; un codice registrato
a catalogo no. Ora si legge `E_FATTURE_RIGHE_RETTIFICATE` dal canale
`CONSTRAINT`, che risponde alla stessa domanda per cui il `throws_like` era
stato preferito a `throws_ok('P0001')` — non *«è un errore di dominio»* ma
**quale** — e ci risponde in un modo che una riscrittura del testo non tocca.

✅ **11/11 verdi**, e la baseline `vendite` torna senza regressioni.

### 2026-08-24 · Due colonne per `vendite.lotti` — e il payload non le produce

Scrive il team DB, su richiesta BE. La richiesta: *«la riga del lotto dice com'è
andato ma non quanto pesa»* — servono `n_fatture` e `totale_documenti`, e
*«il backend li produce già nel payload della lista: mancano solo le due voci di
`ui.lista_colonna`»*.

🔴 **Misurato prima di seedare, e la premessa non regge.** Sul **tip del ramo
backend** (`6a1e23ca5`, 13:33 del 2026-08-24) e su `origin/Tito-dev`:

| Cosa | Misura |
| --- | --- |
| `totale_documenti` in `backend/` | **non esiste**, in nessun file, in nessun ramo, in tutta la storia |
| `n_fatture` in `vendite_repository.py` | esiste **solo** per la dashboard competenza, non per la lista lotti |
| `_LOTTO_SELECT_COLS` | 21 colonne, nessuna delle due |

Le due voci sono state seedate lo stesso — è il lavoro chiesto — ma **`attivo = f`**.

⛔ **Perché `attivo = f` e non `t`.** Un `campo_sorgente` che non esiste nel
payload non dà errore da nessuna parte: la colonna compare nel pannello di
personalizzazione, l'operatore la spunta e la cella resta **vuota**. È
letteralmente il difetto contro cui `vendite_repository.py` ha già un commento in
maiuscolo su `emittente_ragione_sociale` — *«se diverge, la colonna si spunta e
resta vuota, cioè SEMBRA la garanzia senza esserlo»*.
⭐ E `attivo = f` è **auto-annunciante**, che è la ragione vera: il BE spedisce il
payload, apre la lista, non vede le colonne e torna. Con `attivo = t` il buco
resta muto finché non se ne accorge un operatore.
Verificato in transazione: con `attivo = f` `fn_resolve_lista_config` ne espone
**zero**; accese, ne espone due, entrambe `visibile: false` (merge del passo 3),
quindi nemmeno l'accensione cambia da sola l'aspetto della lista.

🔴 **Il cancello che tutti danno per scontato qui non c'è**, ed è la misura che
vale oltre questa richiesta. `trgfn_ui_lista_colonna_a10_valida_campo_sorgente`
valida `campo_sorgente` contro `pg_attribute` **solo se la lista ha una
`vista_sql`**; altrimenti fa `RETURN NEW`. Misurato sul database:

| | |
| --- | ---: |
| liste con `vista_sql IS NULL` | **33 su 47** |
| colonne attive con `campo_sorgente` **senza alcun cancello** | **275 su 487 (56%)** |

`vendite.lotti` è fra queste: la lista nasce da SQL diretto sulla tabella, non da
una vista. ⚠️ Quindi su più della metà del catalogo *«il trigger lo prende»* è
falso, e nessuno lo aveva scritto.

🔵 **Proposta — la quinta direzione del presidio** (non fatta, serve una
decisione). `gen_seed_lista.py --verifica-ordinamento` già legge il repository
del BE per estrarne la whitelist di ordinamento. Per le liste senza `vista_sql`
può fare la stessa cosa col **TypedDict della riga** (`LottoListRow` e gemelli):
sono chiavi dichiarate una per riga, ed è il contratto vero del payload.
Coprirebbe le 275 colonne che oggi non hanno niente.

**Le decisioni del seed, con la ragione:**

| Campo | Valore | Perché |
| --- | --- | --- |
| `ordinabile` | **`t` su entrambe** | `totale_documenti` è **nucleo** (`NUCLEO_ORDINABILE`, voce «totale»): la regola di dominio dice che ordina sempre. Non è la solita cautela «`f` finché la whitelist non arriva» — qui `f` sarebbe *già* un KO al presidio |
| `filtrabile` | `f` | nessun parametro di filtro nel BE, e sulla lista lotti i due flag si corrispondono uno a uno |
| `formato` | vuoto / `currency_eur` | ⚠️ **non `number` sul conteggio**: `formatNumber` ha `minimumFractionDigits: 2` e renderebbe «3,00». Vuoto → `String(value)` → «3», che è la convenzione delle altre 49 colonne numeriche |
| `sensibile` | `f` | un totale in euro invita a metterlo `t`. ⛔ Non si fa: `sensibile` è un **cancello**, e senza un grant in `lista_colonna_permesso` la colonna sparisce per tutti |
| `gruppo` | `Contenuto` (4) | gruppo nuovo fra `Stato` (3) e `Audit`. ⚠️ Le due righe `Audit` passano da `gruppo_ordine` 4 a **5**: senza, l'ordine dei due gruppi lo deciderebbe il tiebreak alfabetico del modale, cioè per caso |
| `lista_preset_colonna` | **nessuna riga** | è il precedente di `emittente_fiscale` (2026-08-18): una colonna aggiunta dopo entra dal merge del passo 3 — nascosta, annunciata da `colonne_nuove`. Metterla nel preset la accenderebbe d'ufficio a tutti |

⭐ **Il cancello sull'accensione, provato e non dedotto.** Il presidio ignora le
righe `attivo = f`, quindi oggi è **verde (47/47)**. Flippando `attivo` a `t`
senza la whitelist del BE diventa:

```text
vendite.lotti                           KO
    promettono l'ordinamento ma il BE non ce l'ha: n_fatture, totale_documenti
    NUCLEO rotto (deve ordinare sempre)          : totale
```

Cioè l'accensione **non passa** finché il BE non ha consegnato. È il metodo della
passata unica applicato al contrario: invece di chiedere e sperare, il controllo
si rifiuta di lasciar accendere.

⚠️ **Lo zero non è il nulla, e la catena si rompe in SQL.** Il BE ha chiesto che
`totale_documenti` sia *«zero, non nullo, su un lotto senza documenti»*, ed è la
richiesta giusta — ma il punto in cui si perde non è il frontend:

```text
SUM(...) su zero righe  ->  NULL      ← qui
psycopg -> JSON         ->  null
CellaConfigurabile      ->  if (value == null) return ''   ← cella vuota
```

`formatCurrency(0)` dà «0,00 €» e `0 == null` è falso in JS: **il frontend fa già
la cosa giusta**. Serve `COALESCE(SUM(...), 0)` nella query, e nessun
`None if row[x] is None` nel mapping. `COUNT(*)` non ha il problema.

**Cosa deve fare il BE** — quattro punti, tutti in `apps/vendite`:

1. `_LOTTO_SELECT_COLS`: le due aggregazioni, con `COALESCE(SUM(...), 0)` sul
   totale. ⚠️ Misurarle: l'`EXISTS` di `ha_errori_gravi` è stato verificato con
   `EXPLAIN ANALYZE` e il pianificatore lo esegue **una volta**; due aggregati
   correlati non ereditano quella proprietà — se non si appiattiscono, meglio un
   `LEFT JOIN LATERAL` unico;
2. `_map_lotto_row` e `LottoListRow`: le due chiavi, **con questi nomi esatti**;
3. `LOTTI_SORT_COLUMNS`: entrambe, o l'accensione resta bloccata dal presidio;
4. `frontend/src/locales/*.json`: `vendite.lotti.col_n_documenti` e
   `col_totale_documenti`. ⚠️ Non è un errore se mancano — `etichettaColonna` ha
   il guard `te` e ripiega sull'etichetta italiana — ma in `en` si vedrebbe
   l'italiano.

Poi **una sola cella**: `attivo` da `f` a `t` sulle righe 525 e 526 del CSV.

📌 **Un rilievo di nomenclatura, che decide il BE**: `n_fatture` conta *documenti*
(un lotto produce anche note di credito), e la colonna gemella si chiama
`totale_**documenti**`. Se il nome va cambiato è ora che costa zero — dopo è una
chiave nel JSONB delle preferenze utente.

### 2026-08-21 · `LottoDrawer` esce dal Gruppo B — il bersaglio passa a 35

Scrive il team DB, su richiesta BE/FE. La nota chiedeva tre
`ui.lista_definizione` per i tab del drawer lotto «sullo stampo di
`vendite.commesse_attivita`». Prima di seedare si è misurato il terreno, e la
misura ha cambiato la forma del lavoro.

**La riclassificazione.** `LottoDrawer.vue` stava nel **Gruppo B** — «tabelle
annidate, non vanno su `ListaConfigurabile`». La decisione di Tid è di
spostarlo: *«annidate anche nel senso di liste su diverse tab»*. Il criterio del
Gruppo B mescolava due cose — le **righe di un documento** (dettaglio del
master) e le **liste su tab** di entità con vita propria — e solo la prima
appartiene davvero lì. Inventario e §8-bis aggiornati: **35 file, 30 convertiti**.

⚠️ **Una riclassificazione non è una conversione**, e qui la distanza è grossa:
delle tre liste **una sola** è un seed.

| tab | stato reale |
| --- | --- |
| documenti | endpoint paginato ✅, whitelist di **3 voci** → **5 nuclei rotti** al presidio, e la chiave `nominativo` non coincide col `campo_sorgente` (stesso difetto di `anagrafiche.clienti`, maggio) |
| tentativi task | **non paginato** (`LIMIT 100` fisso, `ORDER BY` inchiodato) e **due sorgenti divergenti**: `vendite.fn_list_lotto_task_runs` esiste, ordina al contrario, ignora `attivo`, e non la chiama nessuno |
| segnalazioni | **non è una tabella**: sei contatori e tre `Tag`. Le righe non esistono — vanno costruite unendo `fatture_log` e `fatturazione_lotti_log` |

⭐ **Un difetto trovato misurando, che vale a prescindere dalle liste**: il
**codice errore non è scritto da nessuno**. I writer dei due log catturano
`MESSAGE_TEXT` e `RETURNED_SQLSTATE`, mai `CONSTRAINT_NAME` — e per un errore di
dominio lo sqlstate è sempre `P0001`. La colonna «codice» chiesta su due delle
tre liste non ha una sorgente, e non è recuperabile sullo storico.

Piano DB, le sei consegne BE/FE (di cui **tre bloccanti**) e l'ordine dei lotti:
[brief-db-liste-drawer-lotto.md](../work-done/brief-db-liste-drawer-lotto.md).
Vale ancora il metodo delle volte precedenti: **la passata BE si chiede prima di
comporre il lotto, non in consegna.**

### 2026-08-03 · Settimo e ottavo lotto: il Gruppo A arriva in fondo (30/34)

Scrive il BE/FE. Due lotti nella stessa giornata, resi possibili dal fatto che
il DB ha consegnato i seed **due volte in giornata** — 7° lotto al mattino,
8° nel pomeriggio, entrambi verdi al primo passaggio.

**7° lotto — 4 conversioni.** `ApprovazioniPrezzoListView` (36) con nuovo store
`approvazioniPrezzo`; `CodaLavoriTab` (34) e `CodaStampaTab` (35) con la
factory `codeJobs`, e `useCodaFiltri` snellito ai soli helper UI (lo stato dei
filtri è passato allo store); `VersioneDrawer` (37), possibile da quando righe
standalone e compositi arrivano dallo stesso endpoint paginato.

⚠️ Una coda del brief si è rivelata **già chiusa**: su approvazioni il `.vue`
montava già `priorita_descrizione` e l'API la espone. Vale la pena dirlo perché
è il secondo caso in due giorni in cui una voce di commessa descriveva un
sintomo già risolto — **rimisurare prima di lavorare** costa dieci minuti e ne
salva di più.

**Passata BE dashboard** (prima dell'8° lotto, stesso metodo di `attivo` e
della famiglia email): 4 liste su 5 ordinavano già server-side. I tre buchi
veri: `dash_competenza_errori` non ordinava affatto (catena view→service→repo
aggiunta, con `NULLS LAST` perché metà della union ha i campi documento NULL
per costruzione), `stato_codice`/`area`/`fase` su aperto e `classe` su backlog.

**8° lotto — 6 conversioni**: `CommessaGestioneDrawer` (38) + le 5 liste delle
3 dashboard (39-43). Le due liste con checkbox — righe approvabili e gruppi
fatturabili — usano lo **slot `selection` del BB**, estratto il giorno prima
alla 2ª occorrenza: la colonna di selezione è chrome della lista, non catalogo.

Sugli errori vivi è servito un pezzo in più: la union **non ha una PK** (il
tiebreak lato BE è una catena di chiavi naturali), quindi la chiave di riga del
DataTable si compone dalle stesse colonne — senza un `data-key` stabile Vue non
ha su cosa riconciliare.

#### 🔴 Il presidio era CIECO su quattro liste su sei

Registrando le liste, il presidio ne segnalava mancanti solo **2 su 6**. Causa:
la regex cercava `codice="..."` con `[^>]*` fra il nome del tag e l'attributo,
ma un `>` può vivere **dentro** un attributo — e ci vive davvero, in
`v-if="documentiCount > 0 || documentiLoading"` sulle dashboard. La classe
negata si fermava lì.

Il difetto è peggiore di come suona: il presidio **taceva proprio sulle liste
appena convertite**, cioè il caso per cui esiste. Corretto con una finestra di
caratteri al posto della classe negata, senza pretendere di sapere dove finisce
il tag. ➡️ Regola che ne esce, gemella di quelle già pagate: **un controllo che
non ha mai visto rosso non è ancora un controllo** — va provato su un caso che
DEVE fallire.

Registrato anche il primo caso di **whitelist che non vive in Python**:
`vendite.commesse_attivita` la tiene dentro `fn_list_commessa_attivita` (ordine
e paginazione stanno lì), e il presidio confronta lo specchio che il BE usa per
validare prima del round-trip.

**Verifiche**: 3503 test Django verdi, build + lint + i18n puliti, presidio
43/43, nessuna `DataTable` grezza rimasta nei file toccati.

---

### 2026-08-03 · Rename `emittente_fiscale_descrizione` → `emittente_ragione_sociale`: BE/FE allineati, una cosa TENUTA apposta

Scrive il BE/FE. Rename eseguito su **20 file**: i 10 repository/types che
proiettavano l'alias, i 4 test che lo asserivano, i 4 file FE e i 2 manuali API
correnti (`api_ui_admin_personalizzazioni`, `api_documenti_templates`). I brief
storici in `work-done/` **non** sono stati riscritti: registrano cosa era vero
allora.

Con il seed arrivato nello stesso push, **la suite torna verde: 3452 OK**. Le due
chiavi di whitelist di `documenti_repository` che tenevano rosso il presidio ora
combaciano col `campo_sorgente` rinominato.

Verificato contro il DB reale: le 9 liste che attraversano l'alias rispondono e
proiettano il nome nuovo, nessuna porta più il vecchio. Le 6 viste `vw_*_lista`
risolvono la colonna (tornano 0 righe perché interrogate senza GUC operatore —
è la RLS, non l'assenza di dati).

#### ✅ La chiave JSON dell'offerta — tenuta ferma, poi chiusa in giornata

⛔→✅ **`emittente_fiscale.descrizione` → `ragione_sociale`: rinominata**, ma
**dopo** il template e non prima. Il paragrafo che segue resta perché la ragione
dell'attesa è la parte che vale.

La sorgente era già il nome nuovo, la chiave no.

Il motivo è che il template da aggiornare **non è quello indicato**: il
`.md` in `docs/it/backend/vendite/manual/` documenta il template, ma il corpo
vivo è **dato a DB** — `documenti.template_documenti_versioni`, versione
**id 44** (`OffertaComm`, stato **PUBBLICATA**), il cui `html_template` contiene
`offerta.emittente_fiscale.descrizione`.

Con `StrictUndefined` rinominare la chiave da sola non svuota il campo: **fa
fallire il render** dell'offerta. È la stessa famiglia del difetto
builder↔template che lo smoke C-9 aveva scoperto sulla stampa FATTURA.

➡️ **Andata così, e la sequenza ha funzionato.** Il team DB ha pubblicato nuove
versioni dei quattro template scritte **tolleranti al fallback**
(`.get("ragione_sociale") or .get("descrizione") or …`): con entrambe le forme
accettate non esiste una finestra di render rotto, e il BE ha potuto rinominare
la chiave subito dopo. È il modello da riusare quando il contro-pezzo di un
rename è dato a DB — costa una riga di template e toglie il vincolo di
simultaneità.

#### 🔴 E cercandolo è saltato fuori altro: tre stampe mostrano l'impalcatura

Partiti da una segnalazione di Tid — l'ordine stampava
«Emittente fiscale PGTAP-EF-20260126172242554» — si è visto che **non era il
rename**: era un testo di scaffolding rimasto dentro template **PUBBLICATI**.
Cercata la famiglia invece del caso singolo, sono tre:

| Template (versione PUBBLICATA) | Cosa stampa oggi |
|---|---|
| `Ordini vendita` (id 74) | `Emittente fiscale {{ ordine.emittente.codice or "demo" }}` |
| `DDT vendita` (id 47) | `Emittente fiscale {{ ddt.emittente.codice or "demo" }}` |
| `Preventivo` (id 7) | `Emittente fiscale demo` — **stringa cablata**, uguale su ogni preventivo |

Tutti e tre hanno anche la riga
«Dati emittente/asset da collegare nelle prossime iterazioni», che è una nota di
lavoro finita su documenti che vanno al cliente.

**Metà del difetto era del BE, ed è chiusa**: il contesto non offriva un nome da
stampare. `ordine` e `ddt` avevano solo `id` e `codice`; il `preventivo` non
aveva affatto il blocco emittente. Ora tutti e tre espongono
`emittente.denominazione` — stessa chiave della fattura, che stampa bene, così
chi scrive un template usa un nome solo. Verificato: i tre contesti portano
«Gestore Test pgTAP».

**L'altra metà era dato a DB, ed è stata fatta in giornata**: nuove versioni
PUBBLICATE (ordini 139, DDT 140, offerta 141, preventivo 8) che leggono
`emittente.denominazione` con fallback, senza più la riga di promemoria. Il team
DB ha anche corretto un quarto caso che il BE non aveva contato: **anche
l'offerta** aveva la nota di lavoro e il «Emittente fiscale demo» cablato.

✅ Verificato a valle: i quattro contesti espongono esattamente la chiave che il
rispettivo template pubblicato legge — `ordine`/`ddt`/`preventivo`
`.emittente.denominazione`, offerta `.emittente_fiscale.ragione_sociale` — e
tutti e quattro valorizzano «Gestore Test pgTAP» invece del codice.

---

### 2026-08-02 · Settimo lotto — le 4 consegne del BE evase lato DB

Risposta del team DB alle quattro consegne della voce qui sotto. **Tutte e
quattro chiuse**; le prime tre scritte e verificate, la quarta è una decisione.

**Prima di eseguire, le affermazioni del BE sono state verificate sul codice, non
sul documento**: whitelist categorie-listini estesa ✅, colonna corretta a
`ragione_sociale_completa` ✅ (hanno preso anche il difetto che *il presidio non
può vedere*, perché confronta nomi e non l'SQL sotto), `ELENCA_SORT_SQL` a 6
voci ✅, `CODA_STAMPA_SORT_SQL` a 8 con `NULLS LAST` dove serve ✅,
inchiodatura di `order_by` rimossa ✅.

**1 — Riga 371 ribaltata** a `ordinabile=t`, **dopo** che la whitelist esiste e
mai prima. Il presidio è passato da «nucleo rotto» a «il BE sa ordinarle ma il
seed non le offre» e infine a verde: è la stretta di mano che avevano descritto,
funzionata esattamente come previsto.

**2 — `fn_list_commessa_attivita` accetta l'ordinamento** (`20260802-26`).
⚠️ `DROP FUNCTION` obbligatoria: con 6 parametri già tutti a DEFAULT, un
`CREATE OR REPLACE` avrebbe creato un **overload** e reso ambigua ogni chiamata
a 6 argomenti. Whitelist chiusa di 7 colonne + tiebreak `ca.id`; un nome fuori
whitelist **solleva** invece di ripiegare. Verificato in transazione: 14
combinazioni colonna×direzione girano, ASC e DESC danno estremi opposti, due
pagine consecutive non hanno duplicati né buchi, l'iniezione è respinta, e
**senza parametri l'ordine resta `ca.id`** — nessuna chiamata esistente cambia
risultato. La validazione dell'ordinamento è stata messa **prima** della query
di esistenza della commessa, come il BE ha fatto sulle approvazioni.

**3 — Seed delle 3 liste** (34 `dbops.coda_lavori`, 35
`vendite.fatture_stampa_coda`, 36 `vendite.approvazioni_prezzo`), colonne
379-400. **36 liste allineate in tutte e tre le direzioni, al primo passaggio**:
nessun giro di ritorno col BE, che è il dividendo della passata unica.

> ⚠️ **Tre curature che il generatore non poteva fare, e sono le uniche che
> contano:**
>
> - **I preset replicano il default del BE**, non ne inventano uno:
>   `started_at desc` per i lavori e `data_update desc` per la stampa sono
>   default **espliciti chiesti da Tid il 2026-07-23**, non casuali. Un preset
>   diverso avrebbe riordinato la lista sotto gli occhi dell'operatore al primo
>   caricamento.
> - **`fattura` ordina per `fattura_numero`, non per `fattura_id`.** Il BE ha
>   aggiunto quella voce apposta (`f.numero`, `NULLS LAST` perché è NULL finché
>   la fattura è in bozza). Seedare l'id avrebbe ordinato per un numero che a
>   video non c'è.
> - **`id` delle approvazioni nasce `ordinabile = f`**: non è in
>   `PRATICHE_ORDER_COLS`. È la regola già pagata — mai `t` con la speranza.

**4 — Priorità: `priorita_descrizione`**, come proposto dal BE e approvato da
Tid. Il codice logico della colonna resta `priorita`, il `campo_sorgente` è la
descrizione, il codice serve solo al colore del Tag. ➡️ **Ricade sul FE**: il
`.vue` monta ancora `field="priorita_codice"`, e l'API deve esporre
`priorita_descrizione` nella riga.

**Applicazione**: ✅ **fatta.** `20260802-26` EXECUTED, liste 34/35/36 e colonne
379-400 atterrate, riga 371 a `ordinabile = true`, firma della funzione a 8
parametri. Baseline `vendite`: 36 rossi, 36 noti, **nessuna regressione**.

> 🔴 **Un test si è rotto per colpa nostra, e la causa merita di essere scritta.**
> `test-lista-commessa-attivita-fatturata-v1.sql` inchiodava la firma dentro un
> cast:
>
> ```sql
> 'vendite.fn_list_commessa_attivita(bigint,character varying,…,integer,integer)'::regprocedure
> ```
>
> Con due parametri in più quella firma non esiste: il cast non trova nulla e il
> file **muore alla prima riga**, quindi le altre 3 asserzioni — il vero
> contenuto — non vengono nemmeno eseguite. È la forma peggiore di rosso:
> sembra un test che fallisce, è un test che *non gira*.
> Riscritto per risolvere **per nome** (`pg_proc` + `proname`): quel che si
> vuole sapere è che la funzione dichiari la colonna `fatturata`, non con quali
> parametri. Ora è immune alla prossima aggiunta, e se nascesse un overload la
> subquery scalare troverebbe due righe e fallirebbe rumorosamente.
>
> ⚠️ **Come ci è sfuggito**: i chiamanti *erano* stati censiti prima della DROP,
> ma l'output del `grep` era stato **troncato con `head`** e i due file pgTAP
> stavano sotto la decima riga. Un censimento troncato non è un censimento. È la
> terza volta in due giorni che un controllo dà una risposta parziale e viene
> trattato come completa — dopo i commenti dentro `prosrc` e l'alias nudo `e`.
> ➡️ Regola: **quando si conta per decidere, non si tronca l'output.**
>
> ℹ️ `test-fn-list-commessa-attivita-v1.sql` è rosso ma **non per questo**: era
> già in `baseline-rossi.tsv` come `ERRORE_FIXTURE` (guard `tipo_doc_fiscale`),
> e muore nel fixture da prima.

#### 📌 Cosa resta aperto sul binario delle liste — ✅ NIENTE (2026-08-03)

**31/35 convertite · 47 codici seedati · presidio 47/47 · ✅ zero KO.**

✅ L'ultimo KO era `vendite.fondi_fattura_da_decidere`, ed era **preesistente**:
era l'unica lista seedata a non essere registrata nella whitelist del
generatore, quindi veniva *saltata* — cioè dichiarata a posto senza essere
guardata. Mappata il 2026-08-22 registrando le tre del drawer lotto, e appena
mappata ha detto la verità: il nucleo «stato» non ordinava (`stato_atto` a
catalogo con `ordinabile=f`). **Chiuso in giornata con i due passi insieme** —
riga di seed dal team DB (`ordinabile` `f` → `t`) e voce `stato_atto` in
`FONDI_DA_DECIDERE_SORT_COLUMNS` — perché separati si peggiorava: il solo flag
avrebbe prodotto una freccia che ordina per stato e ottiene `data`, senza
nessun errore a dirlo. `--verifica-ordinamento`: **47 liste allineate in tutte
e tre le direzioni**. Dettaglio in
[brief-db-liste-drawer-lotto.md](../work-done/brief-db-liste-drawer-lotto.md)
§4-bis B.
✅ **E il 2026-08-22 i due numeri hanno smesso di divergere**: erano 47 codici
seedati contro 46 nel presidio, e la differenza era una sola — la 44
(`vendite.fondi_fattura_da_decidere`), l'unica lista **senza consumatore
frontend**. Ora è montata (*Vendite → Tool fatturazione*, primo tab) e il
registro `_LISTE` — che conta le liste *montate* — arriva a **47**.
📌 La pagina è nuova, non convertita: il rapporto 31/35 resta quello che è.
Vale la pena tenerlo a mente come metro — un catalogo con più righe di quante
il frontend ne mostri non è un catalogo pronto, è una lista che nessuno guarda.

I 4 file non convertiti sono i cassetti fermi per **decisione 4**, non debito:
caricano tutto in una volta e servirebbero quattro endpoint paginati nuovi
prima di toccare la parte visibile.

| # | Cosa | Esito |
| --- | --- | --- |
| 1 | I 3 `.vue` del 7° lotto (le due code + approvazioni) | ✅ convertiti il 03-08 |
| 2 | Su approvazioni, `priorita_descrizione` nel `.vue` e in API | ✅ **era già a posto**: il `.vue` montava già la descrizione e `cerca_pratiche` la espone. La voce era una coda che si era già chiusa da sé |
| 3 | `CommessaGestioneDrawer`: `order_by`/`order_dir` fino a `fn_list_commessa_attivita` + `@sort` | ✅ cablato il 03-08 → ha sbloccato il seed (lista 38), poi convertito |
| 4 | ~~`VersioneDrawer`: i compositi~~ | ✅ chiuso il 03-08 (UNION lato BE) + seed lista 37 + conversione |
| 5 | Le 3 dashboard (5 liste) | ✅ **fatte il 03-08**, ultime come da decisione 2: passata BE (3 buchi chiusi), seed 39-43, conversione |
| 6 | I 4 drawer senza endpoint paginato | ⏸ fermi per **decisione 4**, invariata |

➡️ **Il binario è chiuso.** Da qui in avanti la regola resta quella di §8-bis:
quando si tocca una lista per altri motivi, la si fa passare dal building
block. Non c'è più un arretrato da consumare.

📎 **Cosa questo binario NON copre.** Il roll-out è il *contenitore*; le
funzionalità di personalizzazione ancora aperte stanno altrove e nessuna passa
di qui: viste nominate per utente (DEF-3) e loro condivisione (DEF-4), più la
domanda se le **dashboard configurabili** debbano seguire la stessa roadmap.
Vivono in
[sviluppo-personalizzazioni-liste_def.md](sviluppo-personalizzazioni-liste_def.md),
che dal 2026-08-22 contiene **solo** quelle (DEF-8 e DEF-10 li ha assorbiti
questo piano, DEF-7 è chiusa come non necessaria proprio in forza della regola
sulle calcolate FE scritta qui sopra).

---

### 2026-08-02 · Settimo lotto — la passata BE: 3 liste pronte, 1 bloccata dove non ce l'aspettavamo

Scrive il BE/FE. Eseguita la **passata unica prima di comporre il lotto**, nella
forma chiesta dal team DB: cosa **blocca** (nucleo) separato da cosa **migliora**,
e la misura rifatta leggendo la catena view→service→repository invece dei nomi
dei file.

**Prima di tutto: la ri-misura del DB è confermata**, su tutti e quattro i punti.
Le due code hanno whitelist e la view accetta già `sort_by`/`sort_dir`; le
approvazioni passano da `PRATICHE_ORDER_COLS` e il valore è inchiodato nel
service; `CommessaGestioneDrawer` non ha ordinamento da nessuna parte. La
diagnosi del perché la mappa sbagliava — «la whitelist è stata cercata nel
repository che porta il nome della lista» — regge, ed è la stessa famiglia del
`_CODA_META` di ieri.

#### Cosa è stato fatto

| Lista | 🔴 Blocca (fatto) | 🟡 Migliora (fatto) |
|---|---|---|
| `CodaLavoriTab` | `stato` | `proprietario` |
| `CodaStampaTab` | `stato`, `fattura_numero` | `id`, `emittente_codice`, `operatore` |
| `ApprovazioniPrezzo` | tolta l'inchiodatura di `order_by` in `lista_coda`; la view legge `order_by`/`order_dir` | — |

Il numero fattura a video è composto da `fatturaLabel`, ma ciò che si ordina è
`f.numero`, con `NULLS LAST`: è NULL finché la fattura è in bozza, e in DESC
sarebbe finito in testa. Stessa cura su `emittente_codice`.

Nelle approvazioni la validazione dell'ordinamento sta **prima** della
risoluzione utente/emittente: un parametro sbagliato non deve costare due
round-trip per essere respinto.

#### Due difetti strutturali corretti strada facendo, e il secondo l'ho creato io

🟠 **Il gate del service era una copia a mano delle whitelist** — tre nomi
ricopiati per la coda stampa, quattro per i lavori. La convenzione lo vieta
proprio perché diverge alla prima estensione, che è appunto oggi. Reso derivato.

🔴 **Ma derivandolo dalla CLASSE ho rotto un test, e il difetto era peggiore
della copia.** Le whitelist erano `ClassVar`: quando un test mocka il
repository, `tuple(Repo.WHITELIST)` diventa vuoto e il gate rifiuta tutto —
cioè **il gate dipendeva dal mock invece che dal codice**. Portate a livello
**modulo**, come `ALLOWED_ORDER_COLUMNS`, `PRATICHE_ORDER_COLS` e
`AUDIT_ORDER_COLUMNS`. La regola che ne esce vale oltre il caso: *una whitelist
è un dato, non un comportamento — non deve passare per l'oggetto che la usa.*

#### 🔴 `CommessaGestioneDrawer` è bloccata, e non per il motivo previsto

Il piano diceva «nessuna whitelist, va creata». **Non è quello.** In
`vendite.fn_list_commessa_attivita` l'`ORDER BY ca.id` e il `LIMIT/OFFSET`
stanno **dentro la funzione DB**:

```sql
ORDER BY ca.id LIMIT p_limit OFFSET p_offset;
```

Ordinare fuori ordinerebbe **la pagina già estratta**, non la lista: un
ordinamento che sembra funzionare e mente — peggio della freccia morta, perché
non ripiega, risponde sbagliato. Il BE non ha un punto in cui intervenire senza
riscrivere in Python una query che il DB possiede (e la filosofia DB-first dice
di non farlo). Serve il parametro nella funzione: vedi la consegna qui sotto.

#### 📤 Da consegnare al team DB

| # | Cosa | Perché ora |
|---|---|---|
| 1 | **Riga 371** — `anagrafiche.categorie_clienti_listini.emittente_ragione_sociale` da `ordinabile=f` a `t` | Il BE è pronto (whitelist estesa, colonna corretta a `ragione_sociale_completa`). **Il presidio è rosso apposta** e nomina la lista: è la stretta di mano concordata, non un guasto |
| 2 | **`fn_list_commessa_attivita` deve accettare l'ordinamento** (`p_order_by`/`p_order_dir`, whitelist lato DB) | Senza, `CommessaGestioneDrawer` non è convertibile: ordine e paginazione sono nella stessa funzione |
| 3 | **Seed delle 3 liste pronte** (coda lavori, coda stampa, approvazioni prezzo) con `ordinabile` allineato alle whitelist estese sopra | È il contenuto del 7° lotto; le colonne ordinabili sono ora esattamente quelle delle tabelle in «Cosa è stato fatto» |
| 4 | ⚠️ **Decisione prima di seedare le approvazioni**: il `.vue` mostra `priorita_codice`, la whitelist offre `priorita_descrizione` | Il BB invia al BE il `campo_sorgente` del seed: se i due nomi non combaciano, la freccia nasce morta. **Proposta BE: `priorita_descrizione` a video e nel seed**, tenendo il codice solo per la severity del Tag (regola di casa sui display field) |

⚠️ Sul punto 1, per non ripetere l'errore di ieri con la DROP: **il seed va
ribaltato ORA che la whitelist esiste, mai prima**. L'ordine inverso produce la
freccia bugiarda.

#### Verifica

Suite **3452 con un solo fallimento**, che è il rosso di consegna del punto 1.
E siccome il presidio confronta costanti — limite che il team DB ha giustamente
rimarcato — l'SQL è stato esercitato davvero: **24 combinazioni** (6 voci coda
lavori + 8 coda stampa + 10 pratiche, per due direzioni) contro il DB reale,
tutte ordinano; il gate delle approvazioni respinge una colonna fuori whitelist
con `E_VENDITE_VALIDATION`.

Resta fuori `VersioneDrawer`, in attesa della decisione sui compositi: è l'unica
delle dodici che chiede una risposta di modello, non di ordinamento.

---

### 2026-08-02 · `storico.audit_log` convertita: il Gruppo A non ha più nulla di meccanico

Scrive il BE/FE, su richiesta di Tid (di norma questo documento lo tiene il team
DB: se la regola resta, questa voce va riletta da loro).

Consegnata la colonna **378** (*Dettaglio*), l'ultima conversione senza domande
aperte è stata fatta: `AuditLogView.vue` monta ora
`<ListaConfigurabile codice="storico.audit_log">`. Con lei il conteggio passa a
**22/34** e **le dodici rimaste sono tutte decisioni**.

| | |
|---|---|
| liste convertite | 21/34 → **22/34** |
| codici seedati ↔ registro `_LISTE` | **33 ↔ 33** |
| file con `DataTable` grezza | **56** (erano 77 il 29-07) |

**Cosa è stato scritto.** Uno store nuovo (`stores/auditLog.js`): lo
scaffolding `useListaConfigurabilePage` vuole uno store che possieda
`items`/`totalRecords`/`loading`/`filters`/`fetchList`, e qui filtri e
paginazione vivevano dentro il `.vue`. Ne è uscito anche un allineamento: il
floor temporale passa da un «ultimo mese» calcolato a mano a
`defaultFiltroDataDaString()`, che è la fonte unica del filtro data delle liste.

**Tre slot soli, e uno mancante di proposito.** `tabella` e `tipo_operazione`
per i Tag, `dettaglio` per il riepilogo (nel seed ha `campo_sorgente` vuoto: il
valore può arrivare solo da lì). Su `timestamp` **non** c'è slot, perché il seed
dichiara `datetime_short` e mettercelo salterebbe il formatter del catalogo —
una delle trappole già pagate su questo binario.

**Nessuna casella di ricerca**, ed è coerenza col modello, non una dimenticanza:
`AuditLogView` (BE) non legge `search` e nel seed tutte le colonne hanno
`ricercabile_full=f`. Lo store tiene comunque la chiave `search` perché
`useSearchTable` ci scrive dentro, ma non la invia.

🟠 **Una asimmetria raddrizzata mentre passavo, e vale oltre questa lista.** In
`amm_software_repository` convivevano `ALLOWED_ORDER_COLUMNS` a livello **modulo**
e `_AUDIT_ORDER_COLUMNS` come attributo **di classe**: due whitelist con lo
stesso ruolo, nello stesso file, in due forme diverse. È esattamente il terreno
su cui un presidio finisce per leggere il simbolo sbagliato — e su questa mappa
**era già successo** (il `frozenset` confrontato dopo la traduzione
`tabella`→`code`, che faceva ripiegare l'ordinamento per *Tabella* in silenzio).
Promossa a modulo come `AUDIT_ORDER_COLUMNS`.

**Verifica.** Presidio **7/7** con la lista registrata e la nota di sospensione
rimossa; suite BE verde; lint e build FE puliti. Poi, siccome **il presidio è
statico**, l'ordinamento è stato esercitato contro il DB reale su **574 righe**:
tutte e quattro le voci della whitelist ordinano in entrambi i versi, e
`dettaglio` — `ordinabile=f` nel seed — ripiega sul default senza sollevare.

---

### 2026-08-02 · Il sesto lotto è stato convertito mentre non guardavamo, e la lista sospesa aveva ragione di esserlo

Ripresa del binario dopo la consegna BE/FE `8983528ac`. **Prima di tutto, tre
misure rifatte sul codice invece che rilette da qui** — e due delle tre
smentivano questo documento.

| Misura | Il documento diceva | Il codice dice |
| --- | --- | --- |
| liste convertite | 17/34 | **21/34** (email ×3 + categorie_clienti_listini) |
| `storico.audit_log` | seed «✅ ok» | seed **incompleto**, conversione sospesa dal BE |
| KO aperti | 1 (`emittente_ragione_sociale`) | **1**, invariato |

**La conversione del sesto lotto era già fatta e l'inventario non lo sapeva.**
Le quattro liste sono state convertite e registrate in `_LISTE`, ma nessuno ha
barrato le righe qui: il documento è restato a 17 mentre il codice stava a 21.
È il difetto opposto a quello di ieri — ieri una misura a mano contro uno
strumento che aveva ragione, oggi un documento che non è stato aggiornato dalla
sponda che ha fatto il lavoro. **Il registro va scritto da chi consegna, o
diventa una fonte che mente in silenzio.**

🔴 **La quinta lista era sospesa, e la motivazione era corretta.** Il BE l'ha
scritta dove serviva — nel commento di `_LISTE` in
`test_liste_configurabili_seed.py` — invece che in una richiesta: «`storico.audit_log`
NON e' qui: il seed non ha la colonna calcolata *Dettaglio*, che la pagina
mostra». Verificato: `AuditLogView.vue` ha **cinque** `<Column>`, il seed ne
portava **quattro**. La mancante è quella senza `field=`, che rende
`rowSummary(data)` — cioè esattamente la categoria che il generatore sa
produrre («colonne calcolate FE, `campo_sorgente` vuoto») e che qui è stata
scritta a mano perché la lista è polimorfa.

**Sbloccata**: colonna `378` in `lista_colonna.csv` + `32,378,50,t,f` in
`lista_preset_colonna.csv`, sul precedente delle altre due calcolate FE già
seedate (`operatori.ruolo` 341, `clienti.sosp_riatt` 14). Nessun changeset —
i loader `runOnChange` la ripescano. Chiave i18n già esistente. Il presidio
resta a **un solo KO**, quello di ieri.

> **La regolarità, ormai con tre punti sulla stessa retta**: su
> `storico.audit_log` abbiamo sbagliato le chiavi i18n *e* saltato una colonna,
> ed è l'unica lista che il generatore non può produrre. Il pezzo scritto a mano
> non è solo quello in cui si sbaglia: è quello in cui si sbaglia **più volte**,
> perché manca anche il controllo che il generatore fa di suo. Contromisura
> minima e a costo zero: **contare le `<Column>` del `.vue` e confrontarle col
> numero di righe seedate** prima di dichiarare una lista pronta.

**Un buco della mappa di prontezza, da colmare al prossimo giro**: `VersioneDrawer`
e `CommessaGestioneDrawer` sono Gruppo A con paginator, non convertite, e **non
compaiono nella mappa** misurata il 2026-08-01 — che copre 11 delle 13 liste
lazy rimaste. Non sono state valutate né dichiarate difficili: sono state
saltate. Vanno misurate prima di comporre il settimo lotto, o si ripete
l'errore già fatto con `AuditLogView` e `CategorieClientiListini`, date per
«nessuna whitelist» senza guardare il repository giusto.

---

### 2026-08-01 · Sesto lotto, e metà del Gruppo A è fatta

Giornata chiusa a **17/34 convertite** — metà esatta del Gruppo A — con il sesto
lotto seedato e quattro liste su cinque verdi.

| | |
|---|---|
| convertite in giornata | **12** (secondo, terzo, quarto, quinto lotto) |
| seed scritti in giornata | **11** liste (quarto, quinto, sesto) |
| KO aperti a fine giornata | **1** (`emittente_ragione_sociale`, nucleo) |
| chiavi i18n nuove chieste dal 5° e 6° lotto | **zero** |

**Il metodo ha retto due volte di fila, e la seconda era una previsione.** Con
`attivo` avevamo chiesto una passata unica e il BE l'aveva estesa a nove
whitelist: il quinto lotto ne ha raccolto il dividendo senza attese. Con la
famiglia email abbiamo fatto la stessa cosa **deliberatamente** — mappa di
prontezza del residuo, isolato il blocco che valeva tre liste, chiesto **prima**
di comporre il lotto. Il BE ha aggiunto le tre whitelist e portato le view alla
forma di `ApiConversioniUomList`, e le tre liste sono entrate nel sesto lotto
già verdi, due complete al 100%. Spezzata in tre consegne, la stessa richiesta
sarebbe costata tre giri e avrebbe prodotto tre lotti con le frecce morte.

**La prima lista polimorfa del binario.** `storico.audit_log` non legge una
tabella ma `storico.{code}`, scelta a runtime da `script.vw_audit_sources`, con
alias sintetizzati. Il generatore non la può produrre: non c'è un
`information_schema` da interrogare perché non c'è **un** oggetto. Scritta a
mano — ed è lì che ho inventato quattro chiavi i18n invece di leggerle dal
`.vue`. Corrette. La regolarità è netta e vale per i prossimi casi simili: **il
pezzo scritto a mano è quello in cui si sbaglia**, e capita di doverlo scrivere
proprio dove lo strumento non arriva. Quando succede, la verifica va fatta con
più cura, non con meno.

**Il presidio ha preso anche l'altro mio errore**: `emittente_ragione_sociale` è
nucleo, e non l'avevo visto nella misura preliminare perché cercavo
`ragione_sociale` fra i pattern mentre la colonna ha un prefisso. Il controllo
la riconosce per sottostringa. Due errori miei intercettati in un lotto solo,
entrambi da uno strumento che a inizio giornata non aveva né il quarto controllo
né la lettura dei `frozenset`.

---

### 2026-08-01 · Quinto lotto: il primo che non aspetta nessuno, e il generatore che smentisce una misura a mano

Tre liste (`catalogo.articoli`, `vendite.listini`, `anagrafiche.operatori`),
**verdi al primo passaggio del controllo di consegna**, **zero chiavi i18n
nuove**, **zero rotture del nucleo**. È il primo lotto consegnabile senza che
nessuna delle due sponde debba muoversi prima dell'altra.

**È il dividendo della passata `attivo`.** Due di queste liste avevano già la
voce in whitelist *prima* di essere scelte, perché il BE aveva esteso la passata
a nove whitelist invece delle tre chieste. Un debito chiuso in anticipo si è
tradotto, un lotto dopo, in una consegna che non ha avuto attese: è
l'argomento migliore a favore delle passate uniche, e non era prevedibile
scrivendola.

⚠️ **Il generatore ha smentito una mia misura, e aveva ragione lui.** Misurando
`ListiniSearchTable.vue` con un grep sui `field=` avevo contato **8** colonne e
dichiarato `codice_versione` come rottura del nucleo che avrebbe **bloccato** il
lotto — l'avevo anche comunicato come voce da anticipare al BE. Falso: quel
`.vue` ha **due** `<DataTable>`, e `codice_versione`/`righe_count` stanno nella
**seconda**, la tabella annidata delle versioni, che è Gruppo B e non va su
`<ListaConfigurabile>`. Il generatore legge la prima e offre `--tabella` per
scegliere: era attrezzato per una cosa che il grep non sapeva nemmeno esistere.

> **La regola che ne esce**: un grep sul file **non è** una misura della lista,
> perché un `.vue` può contenere più tabelle. Dove lo strumento e una misura a
> mano divergono, si guarda **perché** — e qui la ragione era tutta dalla parte
> dello strumento. Vale anche al contrario: le due volte in cui lo strumento è
> stato cieco (`frozenset` e `is_active`, qui sopra) l'ha detto con un
> «illeggibile» o un falso allarme, non con un silenzio.

🔴 **E la cosa peggiore è che l'avvertenza era già scritta qui dentro.** Questo
documento dice da giorni «⚠️ **Un file `.vue` può contenere più `<DataTable>`**
(tabella principale + riga di espansione…). Fonderle produrrebbe una lista
sbagliata» — e più sotto elenca i file colpiti **nominando `ListiniSearchTable`**
come uno dei due. La misura a mano è stata fatta senza rileggere il documento che
descriveva esattamente quella trappola, sul file che citava per nome. Il §0 dice
che i numeri vanno **ri-misurati e non ricopiati**; questa è la faccia opposta e
altrettanto costosa: le **avvertenze** vanno rilette prima di misurare, non dopo
aver sbagliato. È la seconda volta in due giorni che una frase già presente nel
documento avrebbe evitato un errore (la prima: «il seed no» sulle colonne di
validità).

**Due buchi dello strumento chiusi**, entrambi scoperti perché mordevano sulla
lista **più pronta** delle tre: il lettore non riconosceva
`NOME = frozenset({...})` (quindi `operatori` sarebbe stata *saltata* dal
controllo, cioè dichiarata a posto senza essere guardata) e la regola del nucleo
non riconosceva `is_active` come stato (falso allarme su una lista sana). Un
presidio che salta in silenzio e uno che grida al lupo si guastano nello stesso
modo: smettono di essere creduti.

Restano **6 voci** di whitelist da chiedere al BE, **nessuna bloccante** — e per
la prima volta la consegna non le aspetta.

---

### 2026-08-01 · Quattro rifiniture di cella, e la regola sull'ordinamento delle date che era girata al contrario

Giro di correzioni chieste dal BE dopo la consegna del quarto lotto. Tre sono
celle, la prima è una **regola di dominio che era stata scritta al rovescio** —
da loro, e riconosciuta da loro.

**1. `valido_al` ordina DESC, non ASC.** La regola diceva «quando una lista
mostra le date di validità, `valido_al` è il default»; la direzione era `asc`, ed
era sbagliata. In PostgreSQL `DESC` mette i **NULL in testa**: salgono le righe
**senza scadenza**, poi quelle con validità più lunga, e in fondo le scadute.
Con `asc` succedeva l'opposto — in cima finivano proprio le scadute, cioè le
meno interessanti. Corretti **entrambi** i preset: `catalogo.conversioni_uom`
(22) e `vendite.promo_articoli` (23). ⚠️ Da ricordare per ogni lista futura con
date di validità: la colonna giusta era già stata scelta, era il **verso** a
tradire — e un verso sbagliato non rompe niente, mostra solo le righe peggiori
per prime.

**2. Le 11 celle ribaltate a `ordinabile = t`** (template documenti 308-312,
template asset 315-320), `attivo` incluso su entrambe: le due liste `documenti`
sono passate a **ok** nel controllo di consegna.

**3. `date_short` sulle due date di `promo_articoli`** (303, 304): erano le
**uniche due** colonne data attive di tutto il seed senza `formato`, e a video
uscivano come ISO grezzo. Verificato incrociando l'intero `lista_colonna.csv` —
tutte le altre ce l'avevano.

**4. `tipo_variazione` (302) resta `ordinabile = f`.** A video è una cella
composita «TIPO: valore»: ordinarla per il solo tipo direbbe poco. La decisione
del seed era giusta e non si è toccata.

> ⚠️ **Da questo nasce l'unico KO aperto**, ed è nella direzione senza sintomi.
> Il BE aveva aggiunto `tipo_variazione` alla whitelist prima di concordare il
> punto 4, e la rimozione non è ancora pushata: il controllo segnala «il BE sa
> ordinarla ma il seed non la offre». Non produce nulla di visibile — nessuna
> freccia mente — ma resta una divergenza fra le due dichiarazioni, e accorgersi
> **anche di questa direzione** è metà del mestiere di quel controllo. Si chiude
> col loro push, non dal lato seed.

🔴 **La segnalazione più importante del giro, e non riguarda il seed.** Su
`template_documenti` il `.vue` marcava `sortable` tre colonne che non erano in
whitelist, e `documenti_repository` **non ripiega in silenzio**: solleva
`E_DOCUMENTI_VALIDATION` (verificato, riga 401). Quindi in app cliccare quelle
intestazioni **dava errore**. Non era una freccia che non ordina: era una
**freccia che rompe**. Il ribaltamento del punto 2 la chiude.
>
> Vale la pena tenerlo come distinzione: fin qui il rischio raccontato era il
> ripiego silenzioso sul default, fastidioso ma innocuo. Questo caso dice che
> non tutti i repository si comportano così — dove l'`order_by` è validato con
> `raise`, la stessa disallineatura diventa un errore a video. Il presidio
> seed↔whitelist copre entrambi i casi, ma la **gravità** di ciò che intercetta
> dipende dal repository, e non è la stessa ovunque.

---

### 2026-08-01 · Quarto lotto: seed consegnabile in giornata, e la passata `attivo` che vale per i lotti futuri

Il giro si è chiuso nella stessa giornata in cui è cominciato, ed è il primo in
cui **le due sponde si sono incrociate senza attese**: seed scritto → richiesta
al BE → whitelist evase → `ordinabile` ribaltato → controllo verde.

| | |
|---|---|
| seed | liste **23-25**, colonne **298-320**, preset 23-25 |
| voci di whitelist chieste | 12 · **evase 12** (non solo le 2 che bloccavano) |
| righe ribaltate a `ordinabile = t` | 12 |
| controllo di consegna | da «1 lista su 3» a **25 liste allineate** (erano 22) |
| chiavi i18n nuove necessarie | **zero** |

**La passata `attivo` è stata accolta come passata.** Era stata proposta così
apposta — la stessa voce mancava ovunque, e chiederla un lotto per volta voleva
dire mandare cinque volte la stessa richiesta. Il BE l'ha estesa a **nove**
whitelist, quindi `catalogo.articoli` e `vendite.listini` hanno `attivo`
**in anticipo sul proprio seed**: i due lotti futuri partono già senza
quell'ostacolo. È il primo debito di questo binario che viene chiuso *prima* di
incontrarlo.

**Cosa ha fatto funzionare lo scambio**, e conviene ripeterlo: la richiesta
separava «cosa **blocca** la consegna» (solo `attivo`, perché lo stato è nucleo)
da «cosa la **migliora**» (le altre 10, colonne che potevano restare non
ordinabili senza che nulla fosse rotto). Il BE ha potuto **decidere** invece di
eseguire — e ha deciso di farle tutte.

💡 **Il dettaglio che ci saremmo giocati scrivendo noi quelle voci.** Le quattro
descrizioni joinate sono mappate **sull'alias di output nudo**, non su
`tabella.colonna`: sono alias della `SELECT`, e `emittente_fiscale_descrizione`
è un `COALESCE`, che `ORDER BY` risolve **solo** per alias. Il riflesso
`prefisso.colonna` avrebbe prodotto SQL non valido su quattro colonne su dodici.

---

### 2026-08-01 · Passata sugli `ordinamento_default`, e un difetto vecchio trovato applicando la regola a tutti

Il BE ha chiesto due righe di `lista_preset.csv`: **pratiche** da `data_insert`
a `data_apertura` (un dato tecnico e invisibile di default lasciava il posto a
uno di business e visibile — ordinare per una colonna che non si vede rende
l'ordine incomprensibile) e **conversioni UoM** da `uom_from_codice` a
`valido_al` (regola di dominio: quando una lista mostra le date di validità,
`valido_al` è il default). Entrambe applicate. La stessa regola vale per il
quarto lotto, quindi **`vendite.promo_articoli` è nato con `valido_al`** invece
del `valido_dal` che avevo messo copiando il default del repository: la regola di
dominio batte il default tecnico.

> ⚠️ **La direzione scritta quel giorno era `asc`, ed era sbagliata** — insieme
> alla motivazione che l'accompagnava. Corretta a `desc` poche ore dopo su
> entrambi i preset: vedi la voce «Quattro rifiniture di cella» qui sopra. La
> colonna era giusta fin dall'inizio; a tradire è stato il **verso**.

**Applicare la regola a tutti i preset invece che alle due righe chieste ha
trovato un difetto di maggio.** `anagrafiche.clienti` — la **prima** lista del
sistema — aveva `ordinamento_default = ragione_sociale`, che non è nella
whitelist del backend **e non è nemmeno una colonna seedata**. La causa è
istruttiva: il valore era stato scritto col **`codice` logico** della colonna
invece che col suo **`campo_sorgente`** (`ragione_sociale_completa`). Backend e
`<ListaConfigurabile>` lavorano entrambi sul `campo_sorgente`, e `clienti` è una
delle pochissime liste dove i due nomi divergono — per questo è passata
inosservata per mesi. È esattamente la **regressione fantasma** che il BE teme:
oggi invisibile perché il FE non consuma ancora `ordinamento_default`, e visibile
il giorno in cui comincerà. Corretta.

> ✅ **Il controllo è ora sistematico**: per ogni preset si verifica che la
> colonna dell'`ordinamento_default` sia **nella whitelist del backend** e
> **presente e attiva nel seed**. Esito dopo le correzioni: **nessun preset
> rotto** su 21. È un controllo che `--verifica-ordinamento` non fa — lui guarda
> le colonne della lista, non l'ordinamento iniziale — e vale la pena
> incorporarlo.

**Il limite dello strumento, detto dal BE e vero.** `--verifica-ordinamento`
confronta il seed con una **costante** del repository, non con l'**endpoint**
che la attraversa. Su `conversioni_uom` la costante c'era ed era giusta, ma i
due strati sopra la schiacciavano (`order_by` inchiodato, `limit=9999`): il
controllo diceva verde e le frecce sarebbero state morte lo stesso. È la stessa
lezione di `_CODA_META`. Regola pratica per le consegne future: **se l'endpoint
di una lista non è mai stato paginato, è lavoro BE prima della conversione, non
dopo.**

✅ **Verificato per il quarto lotto, prima di consegnarlo**: tutti e tre gli
endpoint (`promo_articoli`, `template_documenti`, `template_asset`) passano
`order_by`/`order_dir`/`limit`/`offset` lungo l'intera catena
view → service → repository e restituiscono un envelope paginato. Nessuno strato
che schiaccia, nessun `limit` cablato. Il lotto non ha il problema di
`conversioni_uom`.

#### La passata sulle chiavi i18n — 80 su 80, in due tempi

Il BE ha chiesto la sostituzione di prefisso sulle chiavi `etichetta_i18n_key`
delle righe **1-78** e **185-199** di `lista_colonna.csv`. La tabella di
sostituzione non era nel messaggio arrivato, quindi invece di chiederla è stata
**derivata e verificata meccanicamente**: per ogni chiave rotta si cerca in
`it.json` una chiave che finisca con lo stesso suffisso e che esista **anche in
`en.json`**.

| | |
|---|---|
| chiavi rotte nel perimetro | **80** (in entrambe le lingue) |
| risolte in modo **univoco** | **58** — prefisso `vendite.` (38) o `anagrafiche.` (20) |
| **ambigue** (più di una destinazione) | **0** |
| senza destinazione | 22 righe = **10 chiavi distinte** |

Zero ambiguità è ciò che ha reso la derivazione applicabile senza indovinare: se
anche una sola chiave avesse avuto due candidate, la passata si sarebbe fermata.
Le 58 sono state riscritte.

✅ **Le ultime 22 righe applicate** dopo la risposta del BE (2026-08-01): tutte
sotto `anagrafiche.` / `vendite.`, **mai a radice**. La ragione data è quella
giusta e va tenuta: mettere `fornitori.col_pec_email` a radice avrebbe creato
una **seconda radice `fornitori`** accanto a `anagrafiche.fornitori`, cioè le
due convenzioni parallele che questa passata esiste per eliminare.

Sette seguono la stessa regola meccanica delle altre 58. Le **15 `lineage` sono
l'unica eccezione, e va capita**: il prefisso `lista.` non diventa un dominio ma
**`vendite.lineage`**, perché quelle tre colonne (`col_pratica`, `col_fase`,
`col_transito`) sono condivise fra **cinque liste diverse** — non appartengono a
nessuna di esse, appartengono alla *funzionalità* lineage, che nel locale ha già
la sua sezione (verificato: `vendite.lineage` esiste ed è popolata). È il caso
in cui la regola del prefisso-per-dominio non si applica, e applicarla
meccanicamente avrebbe attribuito una colonna condivisa a una lista a caso.

> ⚙️ La riscrittura è stata fatta con una **cintura**: ogni riga si tocca solo
> se il valore attuale coincide con quello censito dal BE. Se una riga fosse
> stata diversa dall'atteso, la sostituzione non sarebbe partita invece di
> colpire alla cieca. Esito: **22/22, nessuna saltata**.

✅ **Stato finale della passata, chiusa il 2026-08-01**: **80/80 riscritte**,
**307 chiavi dichiarate** in `lista_colonna.csv`, **zero** rimaste su una radice
di dominio, **zero** divergenze fra italiano e inglese, e — dopo il push del BE
(`f31b792c4`, che porta i 10 tasselli) — **residuo zero: nessuna chiave senza
destinazione, in entrambe le lingue**. Il seed non è stato toccato di nuovo:
erano già scritte col nome definitivo, che era il punto di concordare il prefisso
*prima* invece di riscrivere due volte.

---

### 2026-08-01 · Terzo lotto convertito: le 3 UoM di `catalogo`, e il residuo di sistema va a zero

Tre conversioni (`catalogo.uom_tipi`, `catalogo.unita_misura`,
`catalogo.conversioni_uom`) dal seed del 2026-07-31, tutte e tre registrate in
`_LISTE` del presidio. Con questo lotto **non resta nessun seed in attesa di
conversione**: per la prima volta da quando il binario è partito, catalogo delle
liste e `.vue` dicono la stessa cosa. **11/34.**

**L'unica richiesta del lotto è stata evasa**: le tre voci `attivo`, che erano
una rottura del nucleo (colonna visibile su tutte e tre, ordinamento assente su
tutte e tre). Nessuna nuova chiave i18n, come previsto.

**Il lavoro non richiesto, che è la parte interessante.** La terza lista non era
convertibile davvero: `ApiConversioniUomList` non era un endpoint lista come le
sue due sorelle — niente `is_search_endpoint`, niente `parse_list_params`,
niente envelope paginato, niente `order_by`/`order_dir`. Convertirla soltanto a
video avrebbe prodotto una `<ListaConfigurabile>` con le frecce che non ordinano
e la paginazione che non pagina: esattamente il debito «freccia che non ordina»
che questo piano insegue da due giorni, ricreato da capo su una lista nuova. È
stata portata alla stessa forma delle sorelle **prima** di convertirla.

**Una trappola scritta accanto al codice, che vale la pena non perdere.** Le tre
mappe di ordinamento usano gli stessi alias per tabelle diverse: `ut` è
`uom_tipi` in due query ma è l'unità di misura di **destinazione** nella terza.
Una mappa copiata dalla sorella sbagliata ordinerebbe sulla colonna di un'altra
tabella, e nessun test lo direbbe: la query è valida, il risultato è solo
sbagliato. L'avvertenza è ora sopra le mappe in `catalogo_repository.py`.

🔵 **Una richiesta che torna a noi.** `valido_dal` e `valido_al` di
`conversioni_uom` erano opzionali nel seed («dirlo e diventano due righe»). Il
BE le ha **pre-cablate** nella whitelist, con la regola di dominio scritta
accanto — *le date di validità, quando una lista le mostra, ordinano sempre, e
`valido_al` è il default d'elezione* — proprio per non aprire la finestra di
frecce bugiarde fra la consegna del seed e l'allineamento del backend. È il
verso giusto della sequenza, ed è il sì alla domanda che il lotto aveva lasciato
aperta. Ci restano **due righe di seed** su `lista_colonna` (lista 22) e **due
chiavi i18n nuove**: qui, a differenza delle altre colonne extra del lotto,
`common.data_insert`/`common.data_update` non coprono — sono date di validità,
non di audit.

---

### 2026-08-01 · Secondo lotto convertito: 3 liste, e le prime che nascono già in regola

> ℹ️ **Voce scritta a posteriori il 2026-08-01**, ricostruita dal pushato
> (`db2bbed3a`) e **verificata contro il codice**, non contro il documento. Il
> lotto era stato marcato fatto in §8-bis ma non aveva lasciato traccia qui: §0
> chiede che questo documento si regga senza la conversazione che l'ha prodotto,
> e un lotto senza voce di registro è esattamente ciò che quella regola esiste
> per impedire.

Tre conversioni (`pratiche.pratiche`, `anagrafiche.emittenti_fiscali`,
`anagrafiche.emittente_billing_account`) dal seed del 2026-07-31.
`PraticheSearchTable`, `EmittentiFiscaliListView` e
`EmittenteFiscaleBillingAccountTab` montano `<ListaConfigurabile>`, e tutte e
tre sono registrate nel presidio `_LISTE`.

**Due liste su tre non hanno chiesto niente al backend.** `pratiche` e il tab
billing account avevano whitelist complete e già chiavate sui `campo_sorgente`:
zero bugiarde e zero capacità irraggiungibili in entrambe le direzioni. Sono le
**prime liste seedate che nascono già in regola** — il che dice che il criterio
di scelta del team DB sta migliorando, non che siano state fortunate.

**L'unica voce richiesta era una rottura del nucleo**, ed è stata evasa:
`partita_iva` in `_EMITTENTI_ORDER_COLS`. Per un emittente la P.IVA *è*
l'identificativo fiscale, quindi per la regola di dominio deve ordinare; era
sfuggita perché posteriore alla commessa che il BE aveva già chiuso.

**Tre chiavi i18n nuove**, aggiunte in `it.json` **e** `en.json`:
`pratiche.col_descrizione`, `amministrazione.emittenti_fiscali.col_valuta` e
`…col_regime_fiscale`. Servono a tre colonne invisibili di default: senza, il
`te()` di `<ListaConfigurabile>` sarebbe caduto in fallback sull'etichetta
italiana del catalogo — funzionante, e per questo difficile da notare.

**La whitelist annidata ha richiesto una funzione dedicata nel presidio.** Quella
del tab BA non è una costante di modulo ma un attributo di classe
(`EmittentiFiscaliBillingAccountRepository._ORDER_COLS`), quindi `_LISTE` la
legge con `_whitelist_emittente_billing_account()` invece che con
`_da_costante`. È lo stesso principio annotato in quel file a caro prezzo: **una
whitelist va letta dal simbolo che il repository USA, non da quello che sembra
suo per nome** — inganno che nel registro delle due code resi era costato
un'attribuzione sbagliata fino al 2026-07-31.

Due cose emerse convertendo, che valgono per le prossime: la colonna «Default»
del tab BA **non** è calcolata (il dato è `is_default`, ordinabile: serve solo
lo slot `cell-is_default` per tenere il Badge), e su quella lista
**l'identificatore non è la prima colonna** ma `Codice BA`, che sta in seconda
posizione — la colonna non-nascondibile dev'essere quella che identifica la
riga, non quella che capita per prima.

---

### 2026-07-31 · Primo lotto convertito: 4 liste in un giro, e un building block sistemato

Quattro conversioni (`anagrafiche.categorie_clienti`, `config.utilities_tipi_ruolo`,
`anagrafiche.indirizzi`, `config.tipi_ruolo_tipi_indirizzo`) a partire dal seed
consegnato dal team DB. **Zero lavoro backend**: ordinamento e whitelist
c'erano già, ed erano già chiavate sui nomi fisici — la scelta del team DB di
partire da queste si è rivelata giusta sul merito, non solo sulla carta.

**La verifica sugli standard (richiesta di Tid) ha prodotto il risultato più
utile del giro.** Le quattro liste non hanno endpoint di export, ma
`useListaConfigurabilePage` includeva l'azione «Esporta» in modo
incondizionato: sarebbero nate con quattro pulsanti che aprono un dialog
inerte. Stessa forma per «Nuovo», che chi non ce l'ha filtrava a mano — e quel
filtro era già duplicato **tre volte**, oltre la regola del 2. Le due azioni
sono ora condizionate al proprio handler dentro il BB (verificati tutti e 12 i
chiamanti: comportamento invariato), i tre filtri manuali sono spariti, e il
catalogo BB è stato corretto: descriveva quattro azioni «standard» senza dire
che due sono condizionali.

**Presidio esteso invece che duplicato**: il test di allineamento
seed↔whitelist nato per i lotti è stato generalizzato in
`apps/core/tests/test_liste_configurabili_seed.py` (tabella `_LISTE` +
`subTest`), e copre tutte e 5 le liste convertite. Sta in `core` perché il
contratto è del building block, non di un dominio. Aggiungere una lista =
aggiungere una riga.

**Validate in-app da Tid** il 2026-07-31, tutte e quattro.

**Verifiche**: 1250 test su `core`/`ui`/`anagrafiche`/`config` verdi, build,
lint e `check_i18n_keys` puliti. La suite `vendite` ha 23 rossi in
`pipeline_runner`, **estranei a questo lavoro**: isolati con uno stash mirato —
senza i file di un'altra attività in corso la suite passa, e nessuno dei rossi
tocca liste o catalogo.

### 2026-07-31 · Debito «freccia che non ordina»: il nucleo di Tid, e `vendite.ordini` come pilota

Estendendo il presidio a tutte le liste è emerso che il registro
`_DEBITO_WHITELIST_LOGICA` copre un caso solo (whitelist chiavata sui codici
logici) ma **non** il suo gemello: colonne dichiarate `ordinabile=t` nel seed
per cui il backend non ha proprio quell'ordinamento. Stesso sintomo — il
repository ripiega in silenzio sul default — e nessun test lo vede, perché i
test 1-3 saltano proprio le 11 liste del registro.

**La regola di dominio (Tid).** Esiste un nucleo di colonne **sempre**
ordinabili: la **data** del contesto (data ordine, data fattura, data pratica)
che ha priorità su tutto, il **numero** del contesto, **ragione sociale**,
**billing account**, **id fiscale**, **utility**, **totale**, **stato**. Il
resto si valuta caso per caso.

Verificato su tutte e 11 le liste preesistenti: il nucleo è **già rispettato
quasi ovunque**, 4 caselle rotte in tutto —

| Lista | Rotte |
| --- | --- |
| `anagrafiche.clienti` | id fiscale |
| `anagrafiche.soggetti` | id fiscale |
| `vendite.resi_da_riconsegnare` | numero, stato |

Le prime due sono lo stesso difetto: la whitelist dice `codice_fiscale`, la
colonna legge `id_fiscale_univoco_cf_piva`. Il nucleo non è quindi una regola
da imporre: è la **fotografia di com'è già fatto il sistema**, e vale come
invariante da presidiare anche sulle liste future.

**Pilota `vendite.ordini`** (la peggiore: 12 colonne bugiarde su 24 dichiarate
ordinabili). Nota che spiega perché nessuno se n'era accorto: **tutte e 12 sono
fuori dal preset di default** — le incontra solo chi si personalizza le colonne.

- **Lato DB, fatto**: 7 colonne portate a `ordinabile=f` — `Canale`,
  `Mod. pagamento`, `Termine pag.`, `Valuta`, `Emittente`, `Origine`, `Agente`.
  La freccia sparisce dall'intestazione e nessuno ci prova più.
- **Lato BE, da fare** (decisione Tid: eccezioni accettate): aggiungere a
  `_ORDER_COLS_ORDINI` le 5 voci `imponibile_tot`, `iva_tot`, `anno`, `serie`,
  `utility_descrizione` — *Imponibile*/*IVA* perché sono fratelli di *Totale*
  che è nel nucleo, *Anno*/*Serie* perché sono l'identità del documento insieme
  al *Numero*, *Descr. Utility* per ordinare per esteso e non per codice.
  **E togliere `stato_codice_interno`**: è la colonna tecnica che dà il colore
  al Tag di stato, non è offerta all'operatore e farebbe fallire il controllo
  inverso.

Fatte queste due cose i conti tornano esatti — 17 colonne ordinabili nel seed,
17 voci in whitelist, **zero residuo in entrambe le direzioni** — e
`vendite.ordini` può **uscire da `_DEBITO_WHITELIST_LOGICA`**, prima delle 11.
Finché il BE non aggiunge le 5 voci quelle colonne restano bugiarde: è
l'unica finestra aperta, ed è voluta.

**Poi tutte le altre, con lo stesso metodo** (2026-07-31, secondo giro). Il
lavoro sul seed è chiuso su **tutte e 11 le liste**: 30 colonne fuori dal nucleo
portate a `ordinabile=f`, e la colonna *Emittente* rinominata da
`emittente_fiscale_codice` a `emittente_fiscale` su 6 liste — stessa bugia di
nome dell'*Id. Fiscale* (il `codice` diceva «codice», il `campo_sorgente` legge
`emittente_fiscale_descrizione`), e stavolta **nessuno slot FE la usa**, quindi
la rinomina non tocca il frontend. Quel che resta è tutto nella tabella della
commessa qui sotto.

⚠️ **Due misure sbagliate, corrette.** La prima stesura contava 48 colonne
rotte su 8 liste. Erano due errori di misura, entrambi miei:

1. l'estrattore delle whitelist leggeva anche **dentro i commenti** del
   sorgente, e parole come `campo_sorgente` finivano per errore fra le chiavi;
2. soprattutto: `resi_da_accreditare` e `resi_da_riconsegnare` **non usano**
   `_ORDER_COLS_RESI` — hanno whitelist proprie in `_CODA_META`, già perfette.
   Le contavo fra le peggiori (10 e 8 colonne rotte) e sono a **zero**.

Il debito vero era **39 colonne su 9 liste**, non 48 su 8. La lezione è che una
whitelist va letta **dal simbolo che il repository usa davvero**, non da quello
che sembra suo per nome — ed è lo stesso inganno in cui è caduto il registro
`_LISTE` del presidio (vedi in fondo alla commessa).

**Poi `anagrafiche.clienti` e `anagrafiche.soggetti` — l'*Id. Fiscale*.** È
l'unica rottura del nucleo che si vede **nella vista di default**: la colonna
c'è, sembra ordinabile e non lo è. Causa identica sulle due liste — la colonna
mostra `id_fiscale_univoco_cf_piva` (il campo unificato CF-o-P.IVA) mentre la
whitelist conosce solo `codice_fiscale` e `partita_iva`, che sono i due campi
separati. **Qui il seed non ha nulla da correggere: `campo_sorgente` è giusto,
è la whitelist che guarda altrove.** Lavoro tutto lato BE:

| Repository | Aggiungere | Togliere |
| --- | --- | --- |
| `_CLIENTI_ORDER_COLS` | `id_fiscale_univoco_cf_piva`, `data_sospensione`, `data_riattivazione` | `codice_fiscale` |
| `_SOGGETTI_ORDER_COLS` | `id_fiscale_univoco_cf_piva` | `codice_fiscale`, `partita_iva`, `date_insert` |

- Le due **date di ciclo vita** su clienti (*Sospeso il*, *Riattivato il*) sono
  proposte in aggiunta per lo stesso motivo di *Imponibile*/*IVA* sugli ordini:
  le sorelle dello stesso gruppo (*Attivazione*, *Chiusura*) ordinano già, e la
  regola di dominio dà priorità alle date. Se si preferisce non toccare il BE,
  l'alternativa è **due celle** nel seed (`ordinabile=f`): dimmelo e cambia lì.
- Le voci da togliere non sono ordinamenti persi: **nessuna colonna del catalogo
  le usa**, e restando dentro farebbero fallire il controllo inverso.
- ⚠️ **`date_insert` è un refuso**: la colonna in `anagrafiche.soggetti` si
  chiama `data_insert`. Dettaglio e rettifica nella commessa; in breve: non è
  un errore 500 come diceva una prima stesura, è una colonna *Creazione* che
  domani non ordinerebbe. Va tolta, o scritta giusta.

Verificato: dopo queste modifiche **entrambe le liste hanno zero residuo nelle
due direzioni** (clienti 10 = 10, soggetti 4 = 4) e possono uscire dal registro
di debito insieme a `vendite.ordini`.

> **La radice del refuso non era del BE.** `docs/it/linee-guida-sql.md` §7 e
> `.codex/AGENTS.md` documentavano i campi di audit come `date_insert` /
> `date_update`, mentre nel DB sono **806 colonne e si chiamano tutte
> `data_*`**, zero con `date_`. Il blocco della linea guida era perfino
> incoerente con sé stesso (`date_insert` sulla prima riga, `data_update` sulla
> terza). Corretti entrambi, più il tutorial `framework-automazione-db.md` (5
> occorrenze: è il posto peggiore, insegna) e altri 2 documenti. Restano solo
> le occorrenze nei changelog storici, che non si riscrivono, e in
> `docs/it/dev/work-done/`, che è archivio.

**Richiesta del BE sulle colonne fiscali di `anagrafiche.fornitori`** (arrivata
e applicata il 2026-07-31). Le righe **28** (`codice_fiscale`) e **29**
(`partita_iva`) sono state disattivate: `fornitori` era l'unica lista del
sistema a esporre tre colonne fiscali insieme, mentre ovunque altrove ce n'è
una sola — `id_fiscale`, che punta al campo `GENERATED`. Oltre ad `attivo=f` ho
messo anche `ordinabile=f` (una colonna spenta non deve restare dichiarata
ordinabile) e riscritto l'`etichetta_estesa`, così chi le ritrova nel catalogo
capisce perché sono lì e perché sono spente.

Tre cose emerse controllando, che vale la pena avere agli atti:

- **Nessun dato si perde, ed è più forte dell'argomento di coerenza.** Il dubbio
  legittimo era «un fornitore con CF *e* P.IVA diversi perde un'informazione».
  Non la perde: l'espressione generata **concatena** invece di scegliere.

  ```sql
  CASE WHEN codice_fiscale IS NOT NULL AND partita_iva IS NOT NULL
            AND codice_fiscale <> partita_iva
       THEN codice_fiscale || ' ' || partita_iva
       ELSE COALESCE(codice_fiscale, partita_iva) END
  ```

  La colonna unificata è un **sovrainsieme** delle due. È l'obiezione che
  qualcuno rifarà: la risposta sta qui.
- **Ricaduta sulla commessa**: spegnere le due colonne rende orfane altrettante
  voci di `_FORNITORI_ORDER_COLS`. La riga della tabella ora chiede di togliere
  `attivo`, `codice_fiscale` **e** `partita_iva`.
- La richiesta indicava `lista_id 4`, ma `anagrafiche.fornitori` è **3** (4 è
  `vendite.contratti`). Gli id di riga erano giusti, quindi l'istruzione era
  comunque univoca.

### 2026-07-30/31 · Il filone DB: generatore riparato, `vendite.lotti` e il primo lotto seedati

Filone parallelo alla conversione, su `dev/db-tid`: la configurazione delle
liste è **dato sotto `db/`**, quindi nasce di qua e arriva al FE già pronta.
Tre passaggi, in ordine.

**1. Il generatore è stato verificato eseguendolo, e riparato.** Non una
rilettura: `gen_seed_lista.py` è stato lanciato contro il DB e passato su tutti
e 34 i file del Gruppo A. Sei difetti, due dei quali avrebbero prodotto seed
sbagliati **in silenzio**:

- `vista_sql` usciva come cella vuota, ma `20260507-06` dichiara
  `nullValue: "NULL"` (gli altri tre loader `""`): diventava `vista_sql = ''`,
  il guard non saltava più e l'apply falliva con `E_UI_VISTA_SQL_NON_TROVATA` —
  cioè per **ogni lista senza vista**, che è il caso normale del Gruppo A.
  Dimostrato in transazione: `''` → errore, `NULL` → passa;
- **14 colonne visibili scartate senza dirlo**: le `<Column>` senza `field=` ma
  con header sono colonne calcolate FE, che il DB prevede
  (`campo_sorgente` NULL, come `sosp_riatt` in clienti). Su
  `ContrattoRigheDrawer` ne leggeva 5 su 11;
- `codice` duplicati in **8 file su 34** (`uom_from_codice` e
  `uom_from_descrizione` collassavano entrambi su `uom_from`), che
  `uq_ui_lista_colonna_lista_codice` avrebbe rifiutato;
- i file con **più `<DataTable>`** (`ListiniSearchTable`, `DashboardCompetenzaView`)
  fondevano in una sola lista le colonne di tabelle diverse;
- `formato=number_2` **non esiste** in `CellaConfigurabile`: cadeva nel default
  e mostrava il numero grezzo. Ora `number`;
- `tipo_colonna` era sempre `informazione`: nessuna colonna `identificatore`,
  cioè nessuna colonna non-nascondibile, contro la convenzione di 11 liste su 11.

Dopo la riparazione i conti tornano al pezzo: 269 `<Column>` = 243 lette + 19
azioni + annidate + expander, **zero collisioni**.

**2. Idempotenza, perché il lavoro procede a più mani** (richiesta Tid). Una
lista si può configurare anche dai pannelli di amministrazione, e in quel caso
vive solo nel DB di chi l'ha fatta. Aggiunti `--stato` (fotografia CSV vs DB) e
`--esporta` (recupera in CSV il lavoro già fatto, solo le righe mancanti);
generare una lista che esiste già **non parte**, e gli id si allocano oltre il
massimo fra CSV **e** DB. Controprova: rimossa `vendite.resi` dai CSV e
rigenerata da `--esporta` → 26 righe **identiche byte per byte** all'originale.

**3. I seed.** `vendite.lotti` (id 12) il 30/07 — poi convertita dal BE, vedi
l'altra voce di oggi; il primo lotto di quattro (id 13-16, 33 colonne) il 31/07.
Scelte per un motivo misurabile: hanno **già** `_ORDER_COLS` nel repository, con
le chiavi sui nomi fisici, quindi la lezione n.1 lì costa zero. L'allineamento
`ordinabile=t` ↔ whitelist BE è stato **verificato meccanicamente** leggendo le
whitelist dal sorgente: nessuna colonna fuori. Tutti i seed applicati in
transazione e rollbackati prima della consegna.

Nota di metodo, visto che si ripeterà: il generatore fa le righe, **non le
decisioni**. `ordinabile`, `priorita`, le colonne extra invisibili e
l'identificatore restano scelte, e sbagliarle non dà errore — dà una lista che
sembra giusta.

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
