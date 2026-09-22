# Brief FE — I filtri di una lista su schermo compatto: un gesto, non un ingombro

> **Destinatari:** frontend (`dev/backend-tid`, cartella `frontend/`).
> ⛔ **Nessun prerequisito DB e nessun prerequisito BE**: nessun changeSet,
> nessun endpoint, nessuna chiave di catalogo. È un cantiere interamente FE.
>
> **Tipo:** brief di cantiere, nato da una **richiesta di Tid del 2026-09-22**
> e dalle **nove decisioni** prese lo stesso giorno (§2).
>
> **Da leggere per primo: §1 — la regola. Il §4 è il perimetro misurato, cioè
> il costo: non è la ragione di niente.**
>
> **Stato (2026-09-22, fine giornata):** 🟡 **consegnati L1, L4, il building
> block del periodo (A5) e le decisioni D7/D8**, più **una view pilota**
> (`OrdiniSearchTable`) passata anche per L2 e L3. Restano **L2+L3** sulle
> altre liste, **L5** (riga nel catalogo BB) e **L6** (collaudo su dispositivi
> veri). Inventario completo, numeri del registro e registro dei collaudi in
> **§9**.
>
> **In una riga:** sotto i 1024px (o su un touch senza hover) i filtri di una
> lista escono dalla toolbar ed entrano in un **drawer dal basso**, aperto da
> un'icona che **dice se ci sono filtri attivi** — pallino quando sono i soli
> default, numero quando l'operatore ne ha cambiato uno.

---

## 1. La regola

> **Un filtro è stato della LISTA, non decorazione della view.**
> Ne discende che *dove* i filtri si rendono, e il segno che sono attivi,
> appartengono al building block della lista — come il paginator, il ritiro
> delle colonne e le azioni di testata.

Due conseguenze, entrambe sul modello:

1. **Su una superficie che non li contiene, i filtri diventano un gesto.**
   Una toolbar che va a capo tre volte non è una toolbar: è la tabella spinta
   fuori schermo. Il progetto ha già questa risposta scritta altrove — le
   azioni di riga diventano un kebab, le azioni di pagina diventano un menu,
   le colonne si ritirano nella riga di espansione. I filtri erano l'ultima
   cosa rimasta a occupare spazio in proporzione al loro numero.
2. **Un filtro attivo che non si vede è una lista che mente per omissione.**
   Nel momento in cui i filtri smettono di essere sempre a video, il segno
   della loro presenza diventa **obbligatorio**: senza, una lista ristretta e
   una lista vuota si assomigliano, e l'operatore attribuisce il buco al
   sistema («il documento non c'è») invece che al filtro.
   ⭐ **E vale anche per i default**: `data_da` a «oggi-60gg al primo del mese»
   (`feedback_filtro_data_liste`) restringe esattamente come un filtro scelto a
   mano. Che nessuno l'abbia digitato non lo rende meno vero.

⛔ **Non è una regola sul telefono.** Regge identica su un desktop: il segno dei
filtri attivi è informazione utile comunque, e il building block che lo calcola
è lo stesso. La soglia decide solo *dove si rendono i widget*, non *se la lista
deve dire che è filtrata*.

---

## 2. Le decisioni di Tid — 2026-09-22

| # | Domanda | Decisione |
| --- | --- | --- |
| **D1** | Soglia della modalità compatta | **`< 1024px`**, **e** ogni dispositivo **touch senza hover** a qualunque larghezza |
| **D2** | La casella di ricerca | **Resta fuori dal drawer**, sempre visibile accanto all'icona filtro |
| **D3** | Applicazione dei filtri | **Immediata** a ogni cambio, come oggi. Nessun pulsante «Applica» |
| **D4** | Il segno dei filtri attivi | **Tre stati**: niente / **pallino** (solo default) / **numero** (almeno uno diverso dal default) |
| **D5** | «Pulisci filtri» nel drawer | **Sì**, in fondo, e **scompare quando non c'è niente da pulire** |
| **D6** | Le larghezze scritte dentro i tag | **Si tolgono**: diventano classi di utility. Non un override `!important` nel drawer |
| **D7** | Quanti filtri per riga nel drawer | **Al massimo due, sempre.** Il periodo (`data_da`/`data_a`) è una coppia inscindibile; una combo prende la riga intera finché due non ci stanno leggibili (2026-09-22, terzo giro di collaudo) |
| **D8** | L'intervallo invertito (era A6) | **`da > a` non può esistere.** Meccanismo: *l'estremo che si tocca vince, l'altro si apre* (si svuota), simmetrico e in una sola fetch. ⛔ Rifiutati: il blocco con `min-date`/`max-date` incrociati (impedisce di spostare la finestra in avanti), lo scambio automatico (inventa un periodo in silenzio) |
| **D9** | Un default che si risolve **dopo** il mount (`apply-default`) conta come default o come scelta? | **Si conta e basta: la regola è UNA — si contano sempre i filtri, default compresi.** Un default risolto a runtime cade quindi nel *numero*, non nel pallino, e va bene così: qualunque eccezione aprirebbe il caso gemello — *«e se l'operatore TOGLIE un filtro di default?»* — e il conteggio andrebbe rifatto su una seconda regola (2026-09-22) |

### 2.1 Perché D2 — la ricerca non è un filtro

È **il gesto principale** di una lista; gli altri filtri la restringono.
Nasconderla dietro due tocchi proprio sul dispositivo dove digitare costa di
più è il contrario di ciò che serve. E non guadagna nulla dallo stare con gli
altri: ha già il suo debounce in `useSearchTable` e non ha bisogno di essere
«applicata».

### 2.2 Perché D3 — l'immediata non è la scelta comoda, è l'unica con una sola verità

I binder di `useStoreFilterBindings` scrivono **diretti sullo store**, che è la
sede del filtro. Un «Applica» vorrebbe una **copia temporanea** dei filtri
accanto a quella vera, viva solo mentre il drawer è aperto — e che diverge alla
prima cosa che la tocca da fuori: un deep-link `?search=` (che azzera i default
data), un `reset()`, un cambio di emittente.
⚠️ Effetto collaterale dichiarato: col drawer aperto ogni cambio fa una fetch
dietro le quinte. Non è spreco — alla chiusura la lista è **già** pronta.

### 2.3 Perché D4 — il numero conta *tutti* i filtri attivi

| Stato dei filtri | Segno |
| --- | --- |
| Nessun filtro con valore | niente |
| Filtri con valore, **tutti** al loro default | **pallino discreto** |
| Almeno un filtro diverso dal default | **numero** = quanti filtri stanno limitando la lista, **default compresi** |

⭐ Il numero risponde alla domanda che l'operatore si fa davvero — *«quante cose
stanno restringendo questo elenco?»* — non a *«quante ne ho toccate io»*. Con
`data_da` al default più uno stato scelto si legge **2**, ed è giusto: sono due.

⚠️ **Il caso che il pallino sistema**: con i default dentro il conteggio, quasi
ogni lista mostrerebbe un numero **sempre**, e un segno sempre acceso smette di
essere un segno. Il pallino distingue «ristretta come nasce» da «ristretta da
te».

#### ⛔ Il pallino NON copre i default risolti a runtime — ed è deciso (D9)

`filterDefaults` è un **letterale dello store**, quindi `filtriDefault` è la
fotografia scattata alla nascita della lista. Un default che arriva **dopo** —
`UtilityPerRuoloSelect apply-default`, che risolve la catena
utente→gruppo→emittente e scrive `utility_id` a mount avvenuto — in quella
fotografia non c'è: il segno lo legge come «diverso dal default» e mostra il
**numero**. Sulla view pilota significa **2** appena la lista si apre, non il
pallino.

**Deciso il 2026-09-22 (D9): resta così, e la regola diventa una sola —
*si contano sempre i filtri, default compresi*.** La ragione non è il costo
della correzione: è che l'eccezione non starebbe in piedi da sola. Se un
default risolto tardi dovesse «tornare» nel pallino, allora il caso gemello —
l'operatore che **svuota** un filtro di default — vorrebbe la regola opposta, e
il conteggio finirebbe per rispondere a due domande diverse a seconda di come
il valore ci è arrivato.
⭐ Il numero resta **vero** in ogni caso: dice quante cose stanno restringendo
l'elenco, che è la domanda di §2.3. È il pallino a essere più raro del previsto,
non il conteggio a essere sbagliato.
⛔ **Quindi non è un difetto da correggere**: chi lo ritrova in collaudo si
fermi qui invece di «sistemarlo» in `segnoFiltri`.

### 2.4 Perché D6 — una larghezza scritta nel tag vince su qualunque foglio di stile

```vue
<DatePicker … style="width: 150px;" />
```

Nel drawer vogliamo ogni filtro a tutta riga, uno sotto l'altro: quel `150px`
resta `150px`. **Non dà nessun errore** — si vede solo guardando il telefono, ed
è la famiglia di difetti che questo repo paga più cara. Un `!important` nel
drawer lo tapperebbe, ma sarebbe una regola che combatte il markup: il primo
filtro nuovo scritto con la larghezza nel tag continuerebbe a funzionare **per
fortuna**, non per costruzione.

---

## 3. La forma

### 3.1 Il building block — `FiltriLista.vue`

Un componente in `frontend/src/core/components/`, che **avvolge il markup che
le view già scrivono**:

```vue
<FiltriLista :store="store" :inert="perimetroBloccato">
  <template #sempre>
    <InputText v-model="searchText" … />
  </template>
  <!-- gli altri filtri: inline su desktop, nel drawer in modalità compatta -->
  <LookupSelect … />
  <FiltroPeriodo :periodo="periodo" />
</FiltriLista>
```

| Modalità | Cosa rende |
| --- | --- |
| Desktop | `#sempre` + lo slot di default in linea, dentro `app-page-filters` — **identico a oggi** |
| Compatta | `#sempre` in linea + **icona filtro col segno**; al click, lo **stesso slot** dentro un `Drawer position="bottom"`, su una griglia di **al massimo due per riga** (D7), «Pulisci filtri» in fondo |

⛔ **Il BB unifica il CONTENITORE, non i filtri** (`feedback_bb_legge_non_trasporta`):
i widget restano quelli che sono, con i loro `@change`. I punti che oggi
divergono si guardano **uno per uno** (§6).

### 3.2 Il conteggio nasce nel core, non nelle view

`useListaStoreCore` conosce **già** entrambe le cose che servono, e oggi le
tiene private:

* `filterDefaults` → l'elenco dei filtri **di quella lista**;
* `filtriDiPartenza()` → i loro valori di default.

Si espongono (`chiaviFiltro`, `filtriDefault`) e il segno si calcola in **una**
funzione pura — `segnoFiltri(filters, chiavi, defaults) → {stato, conteggio}` —
con il suo `.spec.js`.
⛔ Mai nelle view: una lista che «dimentica» di contare direbbe **«nessun
filtro» mentre filtra**, senza nessun errore (stampo di
`feedback_rls_conteggio_zero_non_e_un_dato`: uno zero senza contesto sembra un
dato).
⚠️ Il confronto è `!= null`, non un truthy-check: `false` e `0` sono filtri
legittimi — è la stessa regola già scritta in `paramsFiltro`.

✅ **Copertura**: i 49 store che dichiarano `filterDefaults` passano **tutti** da
`useListaStoreCore` (23 diretti, 36 via `createCrudStore`, 27 via
`createListaStore`). Le poche superfici senza store-lista (cruscotti,
`GiornaleEventi`) usano il ripiego esplicito `:conteggio`.

### 3.3 «Modalità compatta» va scritta in UNA sede

D1 mette insieme larghezza **e** assenza di hover. Oggi quella soglia è scritta
**due volte**, e concordano per caso:

| Dove | Cosa dice |
| --- | --- |
| `assets/main.css` | `@media (hover: none), (max-width: 1024px)` — `RowActionsMenu`, `PageActionsBar` |
| `stores/ui.js` | `isMobile`/`isTablet` da `BREAKPOINTS` — **solo larghezza**, cieco al touch |

⇒ Senza un punto solo, su un iPad Pro in orizzontale le **azioni** si
comprimono e i **filtri** no. Nasce `isCompatto` nello store `ui` (larghezza
**o** `matchMedia('(hover: none)')`), lo legge `FiltriLista`, e il `@media`
resta dov'è citando la stessa soglia.
⭐ È la regola di casa sulle asimmetrie: si chiude **subito**, non in una «fase
due» (`feedback_simmetria_modello_no_meta_scope`).

### 3.4 Le larghezze — da numero nel tag a classe

Poche classi in `main.css` (`app-filter-w-xs|sm|md|lg|xl`), applicate ai widget
di filtro. Nel drawer **una** regola le porta a tutta riga.
⭐ Beneficio che non riguarda il telefono: oggi filtri dello stesso tipo hanno
larghezze diverse da una schermata all'altra (§4) — le classi le rendono
uniformi **anche su desktop**, che è il principio di omogeneità dichiarato
negli standard.
⚠️ La mappatura valore → classe si decide **famiglia per famiglia** guardando la
schermata, non con un sostituisci-tutto sul numero più vicino.

### 3.5 i18n

Chiavi nuove sotto `common.*` (nessuna esiste oggi): `filtri`,
`filtri_attivi` (tooltip/aria con il conteggio), `filtri_default_attivi`
(tooltip del pallino), `pulisci_filtri`. In `it.json` **e** `en.json`.

---

## 4. Il perimetro, misurato il 2026-09-22

⚠️ *Fatti datati. Servono a dire il **costo**, non a giustificare la forma: se i
file fossero venti invece di settanta, il building block unico resterebbe
la risposta giusta.*

> ⚠️ **I numeri di questa sezione sono stati CORRETTI il 2026-09-22**, quando il
> cancello del §5/L4 ha misurato la stessa cosa con un criterio scritto. La
> prima passata contava con l'indentazione e chiudeva il blocco al primo
> `</div>` allineato: sui gruppi filtri **auto-chiusi** (`<div
> class="app-page-filters" />`, sette nel repo — spaziatori su liste senza
> filtri) proseguiva fino in fondo al template e tirava dentro larghezze che
> non c'entravano. Diceva **136** larghezze e **86** blocchi; sono **118** e
> **76**. ⭐ È la ragione per cui il conteggio vive in uno script committato e
> non in una riga di `grep`: *una misura senza criterio scritto non la può
> riprodurre nessuno, nemmeno chi l'ha fatta.*

| Cosa | Quanto |
| --- | --- |
| Blocchi con filtri (alcune view ne hanno più d'uno) | **76**, in **70** file |
| Gruppi filtri **vuoti** (`<div … />` usati da spaziatore) | **7** — ⭐ non sono debito: col BB non servono, la spaziatura è del foglio |
| Righe di markup dentro i blocchi | **~1.457** (media 19, massimo **214** in `LottoDrawer.vue`) |
| Blocchi che contengono **anche** la casella di ricerca → da spostare in `#sempre` (D2) | **38** |
| Larghezze inline dentro i blocchi filtri | **118** in **43** file, con **16 valori distinti** (150px ×40, 160px ×14, 120px ×10, 200px ×8, 220px ×8, 260px ×8, 170px ×7, 240px ×5, …) |
| Coppie di date `data_da`/`data_a` scritte a mano | **18** file |
| File in cui i filtri stanno **dentro un drawer** (drawer-dentro-drawer) | **12** |
| View che usano `useListaConfigurabilePage` | 55 |
| Drawer `position="bottom"` esistenti nel repo | **0** — il pattern è nuovo |

⭐ I 16 valori distinti non sono un progetto: sono una sedimentazione. Nessuno
ha mai deciso che lo stesso filtro fosse 150px qui e 160px là.

⚠️ **Questa tabella è la fotografia di PARTENZA e come tale invecchia**: il
numero vivo di ciascuna riga sta nel registro del cancello
(`scripts/filtri-lista.baseline.json`, §9.2), che è l'unico posto che si
aggiorna — e solo per decisione, con `--baseline`. A fine giornata la view
pilota ne aveva già spostati due (larghezze 118 → **114**, coppie di date
18 → **17**).

---

## 5. Lotti, costo e ordine

| # | Lavoro | Costo |
| --- | --- | --- |
| **L1** | ✅ `FiltriLista.vue` (due slot, tre stati del segno, drawer dal basso, «Pulisci filtri») + `chiaviFiltro`/`filtriDefault` esposti dal core + `segnoFiltri` + `isCompatto` in sede unica + CSS + i18n it/en — **consegnato il 2026-09-22** | **fatto** |
| **L2** | Adozione sui **75 blocchi** rimasti (69 file): wrapper, `inert` come prop, ricerca in `#sempre` sui 38, le **17 coppie di date** su `<FiltroPeriodo>`, i 12 casi dentro drawer **guardati uno per uno** | **1,5–2 g** |
| **L3** | Le **114** larghezze inline rimaste → classi di utility (D6). ⭐ Si attraversa **insieme a L2, per view** (§9.4) | **0,5 g** |
| **L4** | ✅ Presidio: `scripts/check-filtri-lista.mjs` + `npm run guard:filtri` — **consegnato il 2026-09-22**, vedi §9 | **fatto** |
| **L5** | Doc: `frontend-standards.md` (§Pattern lista, §Responsive) + catalogo BB FE | **0,5 g** |
| **L6** | Collaudo in-app su smartphone e tablet **veri**, compresi i 12 casi annidati | **0,5 g** |
| | **Totale** | **5–5,5 giornate**, di cui **~2 fatte** |

**L'ordine conta**: **L1 e L4 prima dell'adozione**. Il building block e il suo
cancello consegnati per primi sono l'unica cosa che impedisce alla prossima
lista di nascere già fuori standard — è la lezione della «regola zero della
lista», dove il numero delle `DataTable` grezze era **risalito** proprio mentre
la regola non stava scritta dove si legge.
⚠️ **L2+L3 in un giro solo e corto**: toccano quasi ogni dominio e si accavallano
col cantiere magazzino Lotto 2 se si spalmano su settimane.

---

## 6. I difetti che non darebbero errore

1. **Le larghezze inline vincono sul CSS del drawer** (§2.4). Filtri stretti in
   un drawer largo: nessun errore, si vede solo guardando. È la ragione per cui
   L3 non è cosmetica.
2. **Un conteggio a zero non è un dato.** Una superficie che non passa lo store
   (o uno store senza `filterDefaults`) direbbe «nessun filtro» mentre filtra.
   Il presidio di L4 guarda **questo**, non la resa.
3. **Drawer dentro drawer** — i 12 file del §4. Pila dei drawer
   (`useDrawerChiusuraGlobale`), `app-escape` sui pannelli-azione, z-index,
   Escape che deve chiudere **il drawer dei filtri** e non quello ospite. Si
   collauda a mano: non c'è test che lo veda.
4. **Il rimonto dei widget** al passaggio inline ⇄ drawer (rotazione dello
   schermo, resize). ✅ Qui il progetto è già coperto: i filtri vivono nello
   store, e `bindLookup` ricorda l'oggetto scelto in `<chiave>_obj` — che
   esiste **esattamente** per il widget che rinasce
   (`feedback_autocomplete_restore`). Da verificare in collaudo, non da
   riscrivere.
5. **La soglia in due sedi** (§3.3): se il drawer filtri legge `ui.js` e le
   azioni leggono il `@media`, l'asimmetria nasce il primo giorno.
6. **Il blocco da 214 righe** (`LottoDrawer.vue`) e i suoi simili: non sono
   «un blocco più lungo», sono una forma diversa. Vanno letti, non convertiti.

✅ **Due cancelli esistenti coprono già una parte di L3 e L1**, e vanno tenuti
verdi nello **stesso** commit (non nel successivo — l'hook gira sul solo
*staged*, `feedback_commit_hook_stage_all`):

| Hook | Cosa pretende |
| --- | --- |
| `check-classi-morte` | le classi `app-filter-w-*` **definite nel foglio** nello stesso giro in cui i template le citano. È globale: vede anche il verso opposto |
| `check-i18n-keys` | le chiavi nuove in **`it.json` e `en.json`**, non in uno solo |

---

## 7. Cosa NON è in perimetro

* **DB e backend**: niente. Nessun changeSet, nessun endpoint, nessuna
  preferenza da persistere lato server — il drawer non ha stato da ricordare.
* **Il desktop non cambia**: sopra la soglia la resa è quella di oggi, filtri in
  linea. L'unica aggiunta visibile è il segno dei filtri attivi.
* **L'«Applica» differito**: rifiutato con D3, e non è un «forse più avanti» —
  è una seconda sede dello stato dei filtri.
* **Le 39 larghezze inline fuori dai blocchi filtri**: non si toccano in questo
  cantiere.
* **La matrice slot/override** (`DataTable` grezza con debito già dichiarato nel
  piano PrimeVue 5): non ha filtri di lista, resta fuori.

---

## 8. Decisioni ancora aperte

| # | Cosa | Chi decide |
| --- | --- | --- |
| **A1** | La mappatura larghezza → classe. ⭐ **Le tre taglie esistono** (`sm` 10rem / `md` 13rem / `lg` 16rem, `theme.css`) e sul pilota sono già assegnate: resta aperto **quale filtro prende quale taglia** nelle altre liste, che si decide guardando la schermata durante L2+L3 | Tid, in corso d'opera |
| **A2** | Se il segno dei filtri attivi debba comparire **anche su desktop** accanto alla toolbar (oggi il BB lo calcola comunque: sarebbe una riga di template). L'argomento del §1.2 regge anche lì | Tid |
| **A3** | Se «Pulisci filtri» debba comparire anche nella toolbar desktop, o restare un gesto del solo drawer | Tid |
| **A4** | Se il valore selezionato di una combo stretta debba portare il testo intero nel `title` (come `.app-lista-cella` per le celle di lista). PrimeVue non lo fa; `LookupSelect` è nostro e potrebbe. ⚠️ Su touch non c'è hover: servirebbe solo al desktop | Tid |

---

## 9. Stato dei lavori — 2026-09-22

> **In una riga:** il building block esiste, ha il suo cancello, il periodo ha
> il suo BB e l'invariante `da ≤ a`; **una** view è convertita per intero e fa
> da pilota. Il resto è adozione.

| Lotto | Stato |
| --- | --- |
| **L1** building block e fondamenta | ✅ consegnato |
| **L4** cancello + registro | ✅ consegnato (5 controlli) |
| **A5** BB del periodo | ✅ consegnato (ok Tid in giornata) |
| **D7** due filtri per riga · **D8** intervallo non invertito | ✅ decise e implementate |
| **L2** adozione · **L3** larghezze | 🔵 fatte su **1 view su 70** |
| **L5** riga nel catalogo BB · **L6** collaudo su dispositivi veri | 🔵 da fare |

### 9.1 Che cosa esiste adesso

**File nuovi**

| File | Che cosa |
| --- | --- |
| `core/components/FiltriLista.vue` | il BB dei filtri: due slot (`#sempre` per la ricerca, default per i filtri), icona col segno, `Drawer position="bottom"`, «Pulisci filtri», `console.error` fail-visible se lo store non dichiara le chiavi |
| `core/components/FiltroPeriodo.vue` | il BB del periodo: i due estremi resi insieme, **una** cella nella griglia |
| `core/utils/segnoFiltri.js` | il segno in una **funzione pura**: `segnoFiltri(filtri, chiavi, defaults) → {stato, conteggio}` |
| `core/utils/segnoFiltri.spec.js` | **8 test**, uno per ramo più i limiti (`false`/`0` sono filtri veri, la stringa vuota no, un default svuotato a mano, un filtro ad array) |
| `scripts/check-filtri-lista.mjs` + `filtri-lista.baseline.json` | il cancello e il suo registro (§9.2) |

**File modificati**

| File | Che cosa |
| --- | --- |
| `core/composables/useListaStoreCore.js` | espone `chiaviFiltro` e `filtriDefault` (copia **congelata**) e il verbo **`azzeraFiltri()`** — ⛔ non `reset()`, che scollegherebbe la lista dal padre |
| `core/composables/useStoreFilterBindings.js` | **`bindPeriodo()`** con i setter `setDa`/`setA` e l'invariante D8 (l'estremo toccato vince, l'altro si apre) |
| `core/composables/useStoreFilterBindings.spec.js` | **+8 test** sul periodo; spegnendo la correzione **4 vanno rossi** |
| `stores/ui.js` | **`isCompatto`** — la soglia in una sede: `< BREAKPOINTS.TABLET` **oppure** `matchMedia('(hover: none)')`, con cleanup HMR |
| `core/constants.js` | `MANAGE_ICONS.FILTRI` (`pi-filter`) e `FILTRI_PULISCI` (`pi-filter-slash`) |
| `assets/theme.css` | `--app-filtro-unita` (8rem), `--app-filtro-min-combo` (13rem) e le tre taglie `--app-filter-w-sm|md|lg` |
| `assets/main.css` | barra compatta, pulsante + segno, drawer dal basso (altezza dal contenuto fino a `80vh`, animazione a `0.3s`), **griglia a due colonne**, periodo, taglie in linea |
| `locales/it.json` · `en.json` | `common.filtri`, `filtri_attivi`, `filtri_default_attivi`, `pulisci_filtri` — in **entrambi** |
| `package.json` | `guard:filtri` (entra da sé in `npm run guards`, cioè in CI) |
| `.github/workflows/ci-frontend.yaml` | il commento elencava «i quattro presidi» mentre erano otto: sostituito col rimando alla sede unica |
| `vendite/ordini/components/OrdiniSearchTable.vue` | la view **pilota** |

⭐ **La view pilota, e perché una sola**: esercita **tutto** in un file —
ricerca in `#sempre`, `:inert` del perimetro emittente, due lookup, il periodo,
e (avendo `data_da` col default standard) il passaggio **pallino → numero**. Un
building block che nessuno ha mai montato non è verificato, e non è una cosa da
far scoprire alle altre 69 conversioni. Su di lei sono già passati anche **L2 e
L3**: quattro larghezze inline via, due `bindDate` + due `DatePicker` + due
handler diventati `bindPeriodo()` + `<FiltroPeriodo>`, due import in meno.

**Verifiche a fine giornata**: `eslint` + `oxlint` puliti, **17 `[ok]`** su
`npm run guards`, `check_classi_morte.py` e `check_i18n_keys.py` puliti,
**vitest 209 test su 23 file** (erano 201), `vite build` verde.

### 9.2 Il cancello: cinque controlli, due nature

`npm run guard:filtri` — registro in `scripts/filtri-lista.baseline.json`.
⭐ **Gira già in CI senza toccare il workflow**: `npm run guards` è `run-s guard:*`.

| # | Controllo | Natura | Oggi |
| --- | --- | --- | --- |
| 1 | file che scrivono `app-page-filters` a mano | **cricchetto** | **69** file |
| 2 | ogni `<FiltriLista>` dichiara `:store` o `:segno` | **cancello a zero** | 0 |
| 3 | la ricerca sta nello slot `#sempre` | **cancello a zero** | 0 |
| 4 | larghezze inline nei blocchi filtri | **cricchetto** (la misura di L3) | **114** in 42 file |
| 5 | coppie di date scritte a mano | **cricchetto** (la misura di A5 sul pregresso) | **17** file |

*(informativo, non un cricchetto: **7** gruppi filtri **vuoti** — `<div … />`
usati da spaziatore. Non sono debito: col BB non servono, la spaziatura è del
foglio.)*

⭐ **Perché 2 e 3 nascono a zero**: non sono pregresso, sono modi di usare male
un BB che esiste da oggi. Il 2 spegne il segno su una lista che filtra; il 3
nasconde la ricerca nel drawer — e **da desktop nessuno dei due si vede**,
perché là i due slot si rendono uno accanto all'altro. Sono i difetti che un
collaudo fatto al monitor non può trovare.

⚠️ **I cricchetti sono rossi anche quando CALANO**: una baseline che resta alta
dopo un miglioramento riapre in silenzio lo spazio appena chiuso (lezione di
`check-datatable-baseline.mjs`, dove le `DataTable` grezze erano scese a 48 e
risalite a 57 senza che nessuno lo notasse). Si riscrive con `--baseline`, e la
ragione va nel commit. ⭐ **Successo reale in giornata**: convertendo il pilota
il controllo 4 è andato rosso con «registro da abbassare» (118 → 114), e il 5 è
sceso da 18 a 17.

**Provato contro violazioni vere**, non solo sul verde: `:store` tolto dal
pilota → rosso sul 2; ricerca fuori da `#sempre` → rosso sul 3; un blocco
grezzo in un file nuovo → rosso sul 1 col nome del file; una larghezza in più →
rosso sul 4 (`4 → 5`); una coppia di date aggiunta → rosso sul 5. Ripristinato
tutto dopo ogni prova.

⚠️ **Il buco dichiarato**: un blocco grezzo il cui `<div` ha la `class` su una
riga diversa non verrebbe visto (criterio scritto in testa allo script). Nel
repo non ce n'è; i controlli 2, 3 e 5 non ne soffrono, perché guardano il BB.

### 9.3 Il registro dei collaudi — quattro giri, dodici rilievi

Tutti sulla view pilota, tutti **muti**: build, lint, guard e test verdi mentre
a video la cosa era sbagliata. È il motivo per cui il pilota esiste.

| Giro | Rilievo di Tid | Causa | Rimedio |
| --- | --- | --- | --- |
| 1º | «l'icona filtri non si vede» + «il numero è parzialmente visibile» | ⛔ in PrimeVue **lo slot di default del `Button` SOSTITUISCE il rendering interno**: il `<Badge>` che ci avevo messo ha cancellato l'icona | il segno esce dal Button e lo mette `OverlayBadge` (posizione dal tema, zero coordinate a mano) |
| 1º | «il drawer non si apre completamente» | il tema dichiara `.p-drawer-bottom .p-drawer { height: 10rem }` con la **stessa specificità** del mio override | selettore a tre classi, altezza dal contenuto fino a `80vh`. ⛔ Non un `!important` |
| 1º | «il movimento è meccanico, non fluido» | **errore mio di progetto**: `useDrawerContentReady` montava i filtri a fine slide → il pannello saliva vuoto e il contenuto compariva di scatto | deroga motivata al pattern + durata `0.3s`, curva del tema invariata |
| 2º | «le date sempre affiancate» · «ridurre la combo utility» | i filtri erano impilati uno per riga | griglia di unità, poi **due colonne fisse** (D7) |
| 2º | «quale può essere la riduzione minima di una combo con descrizioni?» | — | ha una risposta precisa, §9.4 |
| 3º | «la combo servizi è troppo piccola» | una combo a mezza riga su un telefono | riga intera finché due non ci stanno leggibili (soglia `@container`) |
| 3º | «il numero è troppo grande e viene tagliato **ancora**» | la **stessa** trappola di specificità del drawer: `.p-overlaybadge .p-badge` del tema batteva il mio override a parità | tre classi + misure derivate dall'icona; il pallino resta quello del tema |
| 3º | «al massimo 2 elementi per riga» | — | ✅ **D7** |
| 3º | «non può essere da > a» | — | ✅ **D8** |
| 4º | «se tolgo i filtri rimane un pallino vuoto che copre l'icona» | ⛔ **il `size="small"` sul badge**: nel tema `.p-badge-dot` (0.5rem) e `.p-badge-sm` (1.25rem) hanno la stessa specificità e `sm` è dichiarata **dopo**, quindi vinceva lei su `min-width`/`height`. Il pallino era un cerchio da 1.25rem nell'angolo di un pulsante da 2.5rem, cioè sopra il glifo | tolto `size`: il numero ha già le sue misure in `main.css`, il pallino torna al token del tema. ⛔ Non un override più forte — il `:not(.p-badge-dot)` proteggeva il pallino dalle **mie** misure, non da quelle che il tema si applica da solo |

#### ⛔ Le tre lezioni che valgono oltre questo cantiere

1. **A parità di specificità vince PrimeVue.** Gli stili del tema sono
   **iniettati a runtime**, quindi arrivano dopo il foglio del progetto: per
   sostituire una regola del tema serve **una classe in più**, non un
   `!important`. L'ho pagata **tre volte** in un giorno (altezza del drawer,
   badge, larghezza nella griglia) — ora sta scritta in `main.css` accanto a
   ognuno dei tre punti, non in un posto solo che si legge per caso.
   ⭐ **E c'è una quarta faccia, pagata al 4º giro**: la regola vera è *«a
   parità vince l'**ultima dichiarata**»*, e **dentro** il tema quale sia non
   lo decido io. `.p-badge-dot` e `.p-badge-sm` sono entrambe a una classe, e
   `sm` viene dopo. ⇒ Un `:not()` che protegge un elemento dalle **mie** misure
   non lo protegge da quelle che il tema si applica **da solo** quando gli
   chiedo una variante: lì non si rilancia con un override più forte, **si
   smette di chiedere la variante**.
2. **Un pattern buono applicato dove la premessa non vale è un difetto**, e non
   lo segnala nessuno: `feedback_content_ready_after_show` nasce per i drawer
   **laterali**, dove la geometria è fissa. In un foglio che sale dal basso **la
   geometria la decide il contenuto**, quindi rimandarlo produce il difetto che
   il pattern dovrebbe evitare.
3. **Un BB unifica la lettura, e i punti che traducevano si cercano uno per
   uno** (`feedback_bb_legge_non_trasporta`). Il censimento delle 18 coppie di
   date ha trovato un **cablaggio divergente**: `@date-select` + `@clear-click`
   quasi ovunque, `@update:modelValue` nei contratti. Non sono equivalenti — col
   primo una data **digitata** non applica il filtro: l'operatore vede la data
   che ha scritto e una lista che non l'ha ricevuta. Nessun errore, da nessuna
   parte.

### 9.4 Le due domande difficili, e le risposte che hanno avuto

**«Quanto si può stringere una combo con le descrizioni?»** — Il minimo riguarda
la **lettura di ciò che è già scelto**, non la scelta: `Select.alignOverlay`
impone al pannello `min-width` = larghezza del trigger e le opzioni hanno
`white-space: nowrap`, quindi **il pannello cresce col contenuto** — un trigger
stretto non taglia nessuna descrizione — e il valore selezionato degrada in
**ellissi**. ⇒ Il pavimento è una soglia di **riconoscibilità**, dichiarata una
volta: `--app-filtro-unita: 8rem` ≈ 13 caratteri (`31/12/2026` intero più
l'icona; per una combo il punto in cui «Energia el…» si legge e «Ene…» no).

**«Le date da/a su una riga può essere una regola?»** — Sì, ma non quella che
sembra: non «le date sono strette», bensì **`data_da`/`data_a` non sono due
filtri, sono un filtro con due estremi**. Detta così vale anche su desktop e non
dipende da quanto è larga la casella. Da lì discendono il BB del periodo e
l'invariante D8.

**Ne discende una cosa sull'ordine dei lotti**: per far governare la griglia, le
larghezze scritte nei tag della view pilota sono dovute uscire. ⇒ **L2 e L3 si
attraversano per view**, non uno dopo l'altro sul repo: convertire il wrapper
lasciando il numero nel tag produce uno stato intermedio in cui il drawer esiste
e i filtri dentro sono stretti.

### 9.5 Quel che resta

* **L2 + L3 insieme, per view**: 75 blocchi in 69 file, 114 larghezze inline,
  17 coppie di date. ⭐ Cominciare dai **12 casi dentro drawer**: sono i più
  rischiosi (pila dei drawer, `app-escape`, Escape che deve chiudere quello dei
  filtri) e conviene scoprire lì cosa non va, non alla sessantesima view facile.
* **L5** la riga nel [catalogo BB frontend](../frontend/catalogo-building-block-frontend.md)
  per **entrambi** i building block — ⚠️ non scritta prima di proposito: quel
  documento è l'inventario di ciò che **c'è e si usa**, e con un consumatore
  solo direbbe più di quanto è vero.
* **L6** collaudo su smartphone e tablet veri.
* ⚠️ **Il guard D8 vive in `bindPeriodo`**: le 17 liste che scrivono ancora la
  coppia a mano **non ce l'hanno**, e lì `da > a` resta possibile. È lo stesso
  debito del controllo 5, con una ragione in più per chiuderlo presto.

⚠️ **Il componente non ha una sua spec, e non è una dimenticanza**: il progetto
non ha `@vue/test-utils` né `jsdom` (`vite.config.js` lo dichiara: *«environment
resta quello di node»*), quindi oggi **nessun** componente è montabile in test.
Aggiungerli è una **dipendenza nuova** e vuole l'ok di Tid. Finché non c'è, dei
due BB sono provate le parti pure (`segnoFiltri`, `bindPeriodo`: 16 test) e il
resto risponde al collaudo in-app — dichiarato, non sottinteso.
