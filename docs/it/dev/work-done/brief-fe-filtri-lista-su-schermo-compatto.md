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
> **Stato (2026-09-23, fine giornata): 🟢 TUTTO CONSEGNATO E MERGIATO TRANNE IL
> COLLAUDO.** L1, L2, L3, L4, L5, il building block del periodo (A5), le
> decisioni D7/D8/D9, i nove difetti della rilettura critica (§11), il primo
> collaudo in-app (§11.9) e la sua riverifica (§11.10). **I tre registri del
> cancello sono a ZERO**: nessuna view scrive più i filtri a mano, nessuna
> coppia di date è scritta a mano, nessuna larghezza di filtro sta in un tag.
> ⇒ **Resta solo L6**, il collaudo su dispositivi veri, che è di Tid. Delle
> decisioni aperte, A3 è stata presa (**sì**) e A2 respinta (**no**) il 23-09;
> resta la sola A4 (§8). Tre commit mergiati — `06b6a8742`, `d0ca2d850`,
> `1d49b0aa2` (PR #1651) — più A3, ancora da committare.
> Inventario, numeri datati e registro dei collaudi in **§9**; ciò che
> l'adozione ha *trovato* — e che il §4 non poteva sapere — in **§10**.
>
> 🔴 **E una RILETTURA CRITICA del 2026-09-23 (§11) ha trovato nove difetti che
> il cantiere aveva introdotto o lasciato aperti**, il più grosso dei quali è
> che «Pulisci filtri» — il verbo nuovo — non arrivava a **49 filtri in 23
> file**. Tutti chiusi lo stesso giorno. ⭐ La lezione sta in §11.0: *un verbo
> nuovo montato su cinquanta superfici vecchie non è una funzione aggiunta, è un
> contratto nuovo che quelle superfici non hanno mai firmato.*
>
> 🔴 **Poi il primo collaudo in-app (§11.9) ha cambiato la resa del segno e ha
> introdotto i valori neutri; una RIVERIFICA di quel lavoro (§11.10) ha trovato
> che il censimento dei neutri era incompleto — quattro filtri della stessa
> famiglia, uno dei quali nello store che quel giro aveva in mano — e che
> «Pulisci filtri» spariva proprio negli stati che i neutri avevano appena reso
> raggiungibili.** ⭐ La regola che li trova tutti è in §11.10: *un interruttore
> «mostra anche X» ha sempre un valore neutro, ed è quello acceso.*
>
> **In una riga:** sotto i 1024px (o su un touch senza hover) i filtri di una
> lista escono dalla toolbar ed entrano in un **drawer dal basso**, aperto da
> un'icona che **dice se ci sono filtri attivi** — numero in grigio quando sono
> i soli default, in blu quando l'operatore ne ha cambiato uno.

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
| **D4** | Il segno dei filtri attivi | **Tre stati**: niente / solo default / almeno uno diverso dal default. ⚠️ **La RESA è cambiata il 23-09** dopo il primo collaudo in-app: non più *pallino / numero* ma **numero grigio / numero blu** — la regola del conteggio è intatta, §11.9 |
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
| Niente sta restringendo la lista | niente |
| Qualcosa restringe, **tutto** al suo default | **numero in grigio** |
| Almeno un filtro diverso dal default | **numero in blu** |

> 🔴 **La resa è cambiata il 2026-09-23** (rilievo in-app di Tid, §11.9). Fino a
> quel giorno lo stato «tutto al default» era un **pallino senza numero**: a
> video si leggeva *«0 → 2»* toccando **una** cosa sola, perché il filtro già
> attivo valeva zero un istante e uno quello dopo. Il conteggio non è mai
> cambiato — era 1 anche col pallino — ma la forma lo **nascondeva**, e un segno
> che nasconde ciò che conta fa sembrare sbagliato un conto giusto.
> ⭐ **La regola di D4 resta intera**: si contano sempre i filtri, default
> compresi. Cambia solo *come* si distingue «ristretta come nasce» da «ristretta
> da te» — prima due **forme**, adesso due **colori** a parità di forma. Così
> l'obiezione qui sotto continua a valere: a essere sempre acceso è il *numero*,
> non l'allarme.

⭐ Il numero risponde alla domanda che l'operatore si fa davvero — *«quante cose
stanno restringendo questo elenco?»* — non a *«quante ne ho toccate io»*. Con
`data_da` al default più uno stato scelto si legge **2**, ed è giusto: sono due.

⛔ **E «restringere» va preso alla lettera** (2026-09-23, §11.9): il conteggio
sapeva riconoscere un solo «tutto» — l'assenza (`null`/`''`). Per la maggior
parte dei filtri basta; non per quelli il cui «tutto» è un valore **vero** che
deve viaggiare sul filo. Effetto: accendere «mostra storico» su offerte e
preventivi — cioè **allargare** la lista — faceva **salire** il numero. Il valore
che non restringe adesso si **dichiara** accanto ai `filterDefaults`
(`filtriNeutri`), come `paramNames` e `gateKeys`: è conoscenza del filtro, non
della funzione che lo conta.

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

🔴 **~~Copertura~~ — questa frase era una TAUTOLOGIA, corretta il 2026-09-23.**
Diceva: *«i 49 store che dichiarano `filterDefaults` passano tutti da
`useListaStoreCore`»*. È **vera** e non dimostra niente: `filterDefaults` è
un'opzione di quel composable, quindi chi la dichiara ci passa per costruzione.
La domanda giusta non era «quanti store dichiarano `filterDefaults`» ma **quante
liste hanno filtri** — e le due popolazioni non coincidevano: **quattordici**
liste i filtri li tenevano senza dichiararli, su store scritti a mano.
⇒ La risposta è `useContrattoFiltriLista`, il contratto in **tre membri**
estratto da `useListaStoreCore` (che lo consuma): dettaglio e elenco in
**§10.2**. Il ripiego `:segno` resta, e resta per ciò per cui è nato — le
superfici che uno store-lista non ce l'hanno **affatto**: i due cruscotti, i
filtri client-side di due drawer, la pagina permessi.

### 3.3 «Modalità compatta» va scritta in UNA sede

D1 mette insieme larghezza **e** assenza di hover. Oggi quella soglia è scritta
**due volte**, e concordano per caso:

| Dove | Cosa dice |
| --- | --- |
| `assets/main.css` | `@media (hover: none), (max-width: 1023.98px)` — `RowActionsMenu`, `PageActionsBar`. ⚠️ Fino al 23-09 questa riga diceva `1024px`, che il foglio non ha mai avuto: `max-width: 1024px` INCLUDE 1024, cioe' un pixel dalla parte sbagliata della sola soglia che il progetto dichiara |
| `stores/ui.js` | `isMobile`/`isTablet` da `BREAKPOINTS` — **solo larghezza**, cieco al touch |

⇒ Senza un punto solo, su un iPad Pro in orizzontale le **azioni** si
comprimono e i **filtri** no. Nasce `isCompatto` nello store `ui` (larghezza
**o** `matchMedia('(hover: none)')`), lo legge `FiltriLista`, e il `@media`
resta dov'è citando la stessa soglia.
⭐ È la regola di casa sulle asimmetrie: si chiude **subito**, non in una «fase
due» (`feedback_simmetria_modello_no_meta_scope`).

### 3.4 Le larghezze — da numero nel tag a classe

Poche classi in `main.css`, applicate ai widget di filtro. Nel drawer **una**
regola le porta a tutta riga.
✅ **Le taglie consegnate sono TRE, non cinque** (`sm` 10rem / `md` 13rem /
`lg` 16rem): `xs` e `xl` non sono mai servite in settanta liste, e una taglia
senza consumatori è un invito a sceglierla a caso.
⭐ Beneficio che non riguarda il telefono: oggi filtri dello stesso tipo hanno
larghezze diverse da una schermata all'altra (§4) — le classi le rendono
uniformi **anche su desktop**, che è il principio di omogeneità dichiarato
negli standard.
⚠️ La mappatura valore → classe si decide **famiglia per famiglia** guardando la
schermata, non con un sostituisci-tutto sul numero più vicino.
✅ **E il criterio che ne è uscito** (A1, chiusa il 2026-09-23) non guarda il
numero di ieri ma **da dove vengono le opzioni**, perché è questo che dice
quanto sono lunghe le etichette: `lg` = ricerca e lookup ricchi; `md` = combo
con descrizioni che vengono da un **catalogo** (`LookupSelect` su un `rel`,
`UtilityPerRuoloSelect`); `sm` = date, stati e liste di opzioni **scritte in
pagina** (`attivo`, `sì/no`). Sta negli standard, non solo qui.

### 3.5 i18n

Chiavi nuove sotto `common.*` (nessuna esiste oggi): `filtri`,
`filtri_attivi` (tooltip/aria con il conteggio), `filtri_default_attivi`
(tooltip del pallino), `pulisci_filtri`. In `it.json` **e** `en.json`.

---

## 4. Il perimetro, misurato il 2026-09-22

⚠️ *Fatti datati. Servono a dire il **costo**, non a giustificare la forma: se i
file fossero venti invece di settanta, il building block unico resterebbe
la risposta giusta.*

> 🔴 **E la correzione stessa era PARZIALE**: il 22-09 sono state ricalcolate le
> righe dei blocchi e delle larghezze, **non** quella delle righe di markup, che
> ha continuato a portare i numeri della passata sbagliata fino al 2026-09-23 —
> e sopra quel «massimo 214» ci stava un corollario del §6 (punto 6), cioè una
> **conclusione costruita su un numero mai riverificato**. ⭐ È la regola zero
> vista da vicino: una misura invecchia *in silenzio*, e un argomento appoggiato
> a un conteggio scade con lui.
>
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
| Righe di markup dentro i blocchi | **1.474** (media 19, massimo **61** in `CodaFiltriToolbar.vue`) — ⚠️ **corretta il 2026-09-23**: diceva «~1.457, massimo **214** in `LottoDrawer.vue`», e il massimo era un residuo della prima passata. I tre blocchi di `LottoDrawer` sono di **14, 9 e 11** righe |
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
aggiorna — e solo per decisione, con `--baseline`.
✅ **Al 2026-09-23 sono tutti a zero.** ⛔ E tre righe di questa tabella erano
**sbagliate nella categoria, non nel numero**: dei 76 blocchi, nove non erano
filtri affatto (§10.1) — una misura può contare ciò che vede, non sapere che
cos'è.

---

## 5. Lotti, costo e ordine

| # | Lavoro | Costo |
| --- | --- | --- |
| **L1** | ✅ `FiltriLista.vue` (due slot, tre stati del segno, drawer dal basso, «Pulisci filtri») + `chiaviFiltro`/`filtriDefault` esposti dal core + `segnoFiltri` + `isCompatto` in sede unica + CSS + i18n it/en — **consegnato il 2026-09-22** | **fatto** |
| **L2** | ✅ Adozione sui **75 blocchi** rimasti (69 file) — **consegnato il 2026-09-23**. Tre cose che il perimetro non prevedeva: nove blocchi non erano filtri affatto (§10.1), quattordici store non dichiaravano i propri filtri (§10.2), e il cancello aveva due punti ciechi (§10.3) | **fatto** |
| **L3** | ✅ Le **114** larghezze inline → classi di utility (D6) — **consegnato il 2026-09-23**, attraversato insieme a L2, per view | **fatto** |
| **L4** | ✅ Presidio: `scripts/check-filtri-lista.mjs` + `npm run guard:filtri` — **consegnato il 2026-09-22**, vedi §9 | **fatto** |
| **L5** | ✅ Doc: `frontend-standards.md` + catalogo BB FE — **consegnato il 2026-09-23** | **fatto** |
| **L6** | Collaudo in-app su smartphone e tablet **veri**, compresi i 12 casi annidati | **0,5 g** |
| | **Totale** | **5–5,5 giornate**, di cui **tutte fatte tranne L6** |

**L'ordine conta**: **L1 e L4 prima dell'adozione**. Il building block e il suo
cancello consegnati per primi sono l'unica cosa che impedisce alla prossima
lista di nascere già fuori standard — è la lezione della «regola zero della
lista», dove il numero delle `DataTable` grezze era **risalito** proprio mentre
la regola non stava scritta dove si legge.
⚠️ **L2+L3 in un giro solo e corto**: toccano quasi ogni dominio e si accavallano
col cantiere magazzino Lotto 2 se si spalmano su settimane.
✅ **Fatti così il 2026-09-23, in un giro solo**, e la previsione ha retto: il
costo vero non è stato il numero di file ma le **tre sorprese** del §10 — nove
blocchi che filtri non erano, quattordici store che non li dichiaravano, due
punti ciechi del cancello. ⭐ Nessuna delle tre stava nel §4, e non poteva
starci: un conteggio dice quanti sono, non che cosa sono.

---

## 6. I difetti che non darebbero errore

1. **Le larghezze inline vincono sul CSS del drawer** (§2.4). Filtri stretti in
   un drawer largo: nessun errore, si vede solo guardando. È la ragione per cui
   L3 non è cosmetica. ✅ **Chiuso il 23-09** (registro a zero), e il criterio
   del cancello ora guarda anche `rem`/`%`/`input-style`: l'unità non cambia il
   difetto, e guardarne una sola sarebbe stato cieco sull'altra.
2. **Un conteggio a zero non è un dato.** Una superficie che non passa lo store
   (o uno store senza `filterDefaults`) direbbe «nessun filtro» mentre filtra.
   Il presidio di L4 guarda **questo**, non la resa.
   🔴 **E il caso non era teorico: erano quattordici liste** — §10.2. La
   risposta è il contratto in tre membri, non il conteggio nelle view.
3. **Drawer dentro drawer** — i 12 file del §4. Pila dei drawer
   (`useDrawerChiusuraGlobale`), `app-escape` sui pannelli-azione, z-index,
   Escape che deve chiudere **il drawer dei filtri** e non quello ospite. Si
   collauda a mano: non c'è test che lo veda. ⏳ **Convertiti tutti il 23-09**,
   e uno ha già dato un rilievo di costruzione: `app-escape` non poteva restare
   sul contenitore, perché `FiltriLista` ha **più nodi radice** e Vue non
   inoltra gli attrs quando le radici sono più d'una — la classe è scesa sul
   widget, dove la regola (`.app-readonly .app-escape`, discendente) vale
   identica. ⇒ **Resta la cosa da guardare in L6.**
4. **Il rimonto dei widget** al passaggio inline ⇄ drawer (rotazione dello
   schermo, resize). ✅ Qui il progetto è già coperto: i filtri vivono nello
   store, e `bindLookup` ricorda l'oggetto scelto in `<chiave>_obj` — che
   esiste **esattamente** per il widget che rinasce
   (`feedback_autocomplete_restore`). Da verificare in collaudo, non da
   riscrivere.
5. **La soglia in due sedi** (§3.3): se il drawer filtri legge `ui.js` e le
   azioni leggono il `@media`, l'asimmetria nasce il primo giorno. ✅ Chiuso il
   22-09 con `ui.isCompatto`.
6. 🔴 **~~Il blocco da 214 righe~~ — questo punto NON ESISTEVA, ed è stato
   ritirato il 2026-09-23.** Era un corollario del «massimo 214 in
   `LottoDrawer.vue`» del §4, che è un numero della prima passata mai
   riverificato: quel file porta **tre** blocchi da 14, 9 e 11 righe, e il
   blocco più lungo del repo ne ha **61** (`CodaFiltriToolbar.vue`). ⭐ La
   lezione vale oltre il refuso: *un argomento appoggiato a un conteggio non è
   più forte del conteggio* — e qui il conteggio era già stato dichiarato
   sbagliato due paragrafi più su, senza che questo punto se ne accorgesse.
   ⚠️ **La cosa vera che il punto voleva dire resta**, e l'ha confermata
   l'adozione: i blocchi **fuori forma** si leggono, non si convertono. Solo
   che non erano i lunghi — erano quelli che **filtri non contenevano affatto**
   (§10.1) e quelli il cui store non dichiarava i filtri (§10.2).

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
| ~~**A1**~~ | ✅ **CHIUSA il 2026-09-23** attraversando le settanta liste. La taglia si decide dal **ruolo del filtro**, non dal numero che c'era prima: `lg` = ricerca e lookup ricchi (articolo, billing account, comune); `md` = combo con descrizioni che vengono da un **catalogo** (`LookupSelect` su un `rel`, `UtilityPerRuoloSelect`); `sm` = date, stati e liste di opzioni **scritte in pagina** (`attivo`, `sì/no`), che portano etichette corte. ⭐ Il criterio è riproducibile e sta negli standard: *da dove vengono le opzioni* dice quanto sono lunghe le etichette, il numero di ieri non diceva niente | ✅ decisa |
| ~~**A2**~~ | ⛔ **CHIUSA il 2026-09-23: NON si fa.** Il segno su desktop non si aggiunge, e la ragione è la stessa che ha chiuso A3 al contrario: là i filtri **si vedono tutti**, quindi non manca l'informazione — mancava il **verbo**, ed è arrivato. ⚠️ E ci sarebbe un danno: quasi ogni lista nasce con un `data_da` al floor, quindi il numero sarebbe **permanente** su quasi tutte — *un segno sempre acceso smette di essere un segno* (§2.3), e dopo due giorni non lo guarderebbe più nessuno, nemmeno nei casi per cui è nato. ⭐ Il BB il conteggio lo calcola comunque: se un giorno servisse è una riga di template, e la si scriverà con un motivo | ⛔ decisa: no |
| ~~**A3**~~ | ✅ **CHIUSA il 2026-09-23: sì.** «Pulisci filtri» compare anche nella toolbar desktop, **icona sola col tooltip** come ogni altro comando di quella riga (`ReloadButton`); l'etichetta per esteso resta nel drawer. ⭐ Il criterio che l'ha decisa, e che vale anche per A2: su desktop i filtri **si vedono tutti**, quindi ciò che manca non è l'informazione — è il **verbo**. Riportarli al default a mano costa un gesto per filtro, e su una lista con sei filtri l'operatore non ricorda nemmeno quali ha toccato. ⚠️ Stessa condizione del ramo compatto (`puoPulire` + `$slots.default`), non una seconda regola | ✅ decisa |
| **A4** | Se il valore selezionato di una combo stretta debba portare il testo intero nel `title` (come `.app-lista-cella` per le celle di lista). PrimeVue non lo fa; `LookupSelect` è nostro e potrebbe. ⚠️ Su touch non c'è hover: servirebbe solo al desktop | Tid |

---

## 9. Stato dei lavori — 2026-09-23 (aggiornato a fine giornata)

> **In una riga:** il cantiere è **finito e mergiato tranne il collaudo**. I due
> building block esistono e sono montati su **tutte e settanta** le liste, il
> periodo ha l'invariante `da ≤ a` ovunque, il contratto dei filtri ha una sede
> sola, il cancello ha sette controlli e i suoi tre registri sono a **zero**.
> Resta **L6**, che è l'unica cosa che nessun presidio sa fare: guardare un
> telefono. Delle decisioni aperte ne restano **una** (A4): A3 è stata presa e
> A2 respinta il 23-09 (§8).

| Lotto | Stato |
| --- | --- |
| **L1** building block e fondamenta | ✅ consegnato (22-09) |
| **L4** cancello + registro | ✅ consegnato (22-09), portato a **7 controlli** il 23-09 (§11.6) |
| **A5** BB del periodo | ✅ consegnato (ok Tid in giornata) |
| **D7** due filtri per riga · **D8** intervallo non invertito · **D9** il conteggio | ✅ decise e implementate |
| **L2** adozione · **L3** larghezze | ✅ **consegnati il 23-09 — 70 view su 70**, tre registri a zero |
| **L5** riga nel catalogo BB e negli standard | ✅ consegnato (23-09) |
| §11 **rilettura critica** — nove difetti | ✅ tutti chiusi il 23-09 |
| §11.9 **primo collaudo in-app** — segno a colori, valori neutri | ✅ chiuso il 23-09 |
| §11.10 **riverifica** — quattro neutri mancanti, «Pulisci» che spariva | ✅ chiusa il 23-09 |
| **regola del 2** — la terna `Tutti / Attivo / Non attivo` | ✅ estratta il 23-09 (ok Tid), cinque sedi → una |
| **`rate.solo_numerate`** — filtro senza gesto | ✅ chiuso il 23-09 (ok Tid): **non era un filtro, era un perimetro** → sceso nel backend |
| **L6** collaudo su dispositivi veri | 🔵 **l'unica cosa aperta** — è di Tid |

> **Dove sta il lavoro**: tre commit sul ramo `dev/backend-tid`, tutti mergiati —
> `06b6a8742` (L1+L4, 22-09), `d0ca2d850` (L2+L3+L5, adozione, §10 e §11) e
> `1d49b0aa2` (§11.9, §11.10, regola del 2, perimetro delle rate), quest'ultimo
> in PR #1651.
>
> ⚠️ **I numeri della suite sono datati, e vanno letti così** (regola di casa: un
> numero misurato invecchia in silenzio). **Al commit `1d49b0aa2`**: `eslint` +
> `oxlint` puliti, **17 `[ok]`** su `npm run guards`, **251 test su 26 file**,
> `vite build` verde, `check_i18n_keys.py` e `check_classi_morte.py` puliti.
> Da quel commit in poi il numero globale si muove con gli **altri** cantieri:
> ciò che resta vero di questo sono i suoi presidi, che sono cinque —
> `segnoFiltri` (12), `clonaFiltri` (8), `useContrattoFiltriLista` (12),
> `useContrattoFiltriLocali` (15) e `useStoreFilterBindings` (25, che porta il
> periodo) — più `npm run guard:filtri`, che tiene i tre registri a zero.

### 9.1 Che cosa esiste adesso

**File nuovi**

| File | Che cosa |
| --- | --- |
| `core/components/FiltriLista.vue` | il BB dei filtri: due slot (`#sempre` per la ricerca, default per i filtri), icona col segno, `Drawer position="bottom"`, «Pulisci filtri», `console.error` fail-visible se lo store non dichiara le chiavi |
| `core/components/FiltroPeriodo.vue` | il BB del periodo: i due estremi resi insieme, **una** cella nella griglia |
| `core/utils/segnoFiltri.js` | il segno in una **funzione pura**: `segnoFiltri(filtri, chiavi, defaults) → {stato, conteggio}` |
| `core/components/FiltriLista.spec.js` | **(23-09, ok Tid) 12 test** — il primo test di componente di questo cantiere, reso possibile da `@vue/test-utils` + `jsdom` entrati lo stesso giorno. Prova ciò che si vede **solo montando**: l'imbuto che non nasce con la sola ricerca, i tre stati del segno, il valore neutro che spegne il conteggio, «Pulisci filtri» che c'è anche senza segno, il fail-visible sullo store senza chiavi, la ricerca che resta fuori dal drawer. Provata contro **quattro mutazioni**, una per difetto vero. ⛔ Non vede il CSS: il badge sul glifo e l'altezza del drawer restano a L6 |
| `core/utils/segnoFiltri.spec.js` | **8 test**, uno per ramo più i limiti (`false`/`0` sono filtri veri, la stringa vuota no, un default svuotato a mano, un filtro ad array) |
| `scripts/check-filtri-lista.mjs` + `filtri-lista.baseline.json` | il cancello e il suo registro (§9.2) |
| `core/composables/useContrattoFiltriLista.js` | **(23-09)** il contratto che una lista offre ai suoi filtri — `chiaviFiltro`, `filtriDefault` congelati, `azzeraFiltri()` — estratto da `useListaStoreCore`, **che lo consuma**. È ciò che ha permesso ai quattordici store scritti a mano di adottarlo in tre righe senza cedere il proprio `buildParams` (§10.2) |
| `core/composables/useContrattoFiltriLista.spec.js` | **(23-09) 8 test**: le chiavi sono i soli filtri di dominio, i default sono congelati e sono una copia, «Pulisci» non tocca la ricerca (D2), un default valorizzato torna al suo valore, `offset` non si inventa su una lista non paginata. ⭐ Provati contro **due mutazioni**: spegnendo il guard di `offset` e scongelando i default, vanno rossi |

**File modificati**

| File | Che cosa |
| --- | --- |
| `core/composables/useListaStoreCore.js` | espone `chiaviFiltro`, `filtriDefault` (copia **congelata**) e il verbo **`azzeraFiltri()`** — ⛔ non `reset()`, che scollegherebbe la lista dal padre. **(23-09)** le tre righe non stanno più qui: le prende da `useContrattoFiltriLista`, così la sede è una sola per tutti |
| `core/composables/useStoreFilterBindings.js` | **`bindPeriodo()`** con i setter `setDa`/`setA` e l'invariante D8 (l'estremo toccato vince, l'altro si apre) |
| `core/composables/useStoreFilterBindings.spec.js` | **+8 test** sul periodo; spegnendo la correzione **4 vanno rossi** |
| `stores/ui.js` | **`isCompatto`** — la soglia in una sede: `< BREAKPOINTS.TABLET` **oppure** `matchMedia('(hover: none)')`, con cleanup HMR |
| `core/constants.js` | `MANAGE_ICONS.FILTRI` (`pi-filter`) e `FILTRI_PULISCI` (`pi-filter-slash`) |
| `assets/theme.css` | `--app-filtro-unita` (8rem), `--app-filtro-min-combo` (13rem) e le tre taglie `--app-filter-w-sm|md|lg` |
| `assets/main.css` | barra compatta, pulsante + segno, drawer dal basso (altezza dal contenuto fino a `80vh`, animazione a `0.3s`), **griglia a due colonne**, periodo, taglie in linea. **(23-09)** `app-page-toolbar-start` (la zona sinistra che filtri non porta, §10.1), `app-msg-riga`, `.app-page-toolbar > .app-page-actions:first-child` (le azioni restano a destra senza lo spaziatore nel markup), la taglia di un `InputNumber` che arriva al suo `<input>` |
| `core/components/DrawerTabLista.vue` | **(23-09)** monta `<FiltriLista>` per conto del caller: prop `store` e **due** slot riservati in più — `#filtri-sempre` (la ricerca) e `#filtri`. Converte in un colpo le **tredici** liste dentro un drawer, ed è il motivo per cui il cancello ha imparato a leggere anche quel contenitore |
| `strumenti/stores/codeJobs.js` | **(23-09)** i filtri data da `dataDa`/`dataA` (oggetti `Date`) a **`data_da`/`data_a` in ISO**, come ogni altra lista: era l'unica coppia fuori standard, quindi l'unica che non poteva passare da `bindPeriodo` — cioè l'unica senza l'invariante D8 |
| **70 view** in tutti i domini | **(23-09)** L2+L3: wrapper `<FiltriLista>`, ricerca in `#sempre`, `<FiltroPeriodo>`, taglie al posto delle larghezze. Elenco vivo: `git diff` — qui non si ricopia, invecchierebbe al primo file toccato |
| `locales/it.json` · `en.json` | `common.filtri`, `filtri_attivi`, `filtri_default_attivi`, `pulisci_filtri` — in **entrambi** |
| `package.json` | `guard:filtri` (entra da sé in `npm run guards`, cioè in CI) |
| `.github/workflows/ci-frontend.yaml` | il commento elencava «i quattro presidi» mentre erano otto: sostituito col rimando alla sede unica |
| `vendite/ordini/components/OrdiniSearchTable.vue` | la view **pilota** |

⭐ **La view pilota, e perché è servita**: esercitava **tutto** in un file —
ricerca in `#sempre`, `:inert` del perimetro emittente, due lookup, il periodo,
e il passaggio **pallino → numero**. Un building block che nessuno ha mai
montato non è verificato, e i dodici rilievi del §9.3 sono usciti tutti da lì:
senza il pilota li avrebbero incontrati le altre sessantanove conversioni, una
alla volta. ⚠️ **Ma il pilota non poteva trovare ciò che sta in §10**: quei
difetti non erano nel building block, erano nella *popolazione* — nove blocchi
che filtri non erano, quattordici store che i filtri non li dichiaravano. Si
vedono solo aprendo tutte le settanta liste.

**Verifiche (2026-09-23)**: `eslint` + `oxlint` puliti, **17 `[ok]`** su
`npm run guards`, `check_classi_morte.py` e `check_i18n_keys.py` puliti,
**vitest 220 test su 24 file** (erano 209 su 23), `vite build` verde.
⛔ **E nessuna di queste è un collaudo**: il §9.3 conta dodici rilievi trovati a
video **mentre tutto era verde**. È la ragione per cui L6 è un lotto e non una
formalità.

### 9.2 Il cancello: sette controlli, due nature

`npm run guard:filtri` — registro in `scripts/filtri-lista.baseline.json`.
⭐ **Gira già in CI senza toccare il workflow**: `npm run guards` è `run-s guard:*`.

| # | Controllo | Natura | Al 22-09 | Al 23-09 |
| --- | --- | --- | --- | --- |
| 1 | file che scrivono `app-page-filters` a mano | **cricchetto** | **69** file | ✅ **0** |
| 2 | ogni `<FiltriLista>` (e ogni `<DrawerTabLista>` con filtri) dichiara `:store` o `:segno` | **cancello a zero** | 0 | 0 |
| 3 | la ricerca sta nello slot `#sempre` / `#filtri-sempre` | **cancello a zero** | 0 | 0 |
| 2-bis | dietro quel `:store` c'è **davvero** il contratto dei filtri | **cancello a zero** | — | 0 (dal 23-09, §11.6) |
| 3-bis | `app-page-toolbar-start` non contiene filtri | **cancello a zero** | — | 0 |
| 4 | larghezze inline nei blocchi filtri (`px`, `rem`, `%`, `input-style`) | **cricchetto** (la misura di L3) | **114** in 42 file | ✅ **0** |
| 5 | coppie di date scritte a mano | **cricchetto** (la misura di A5 sul pregresso) | **17** file | ✅ **0** |

⭐ **Un registro a zero non è un registro inutile**: cambia solo ciò che dice.
Fino a ieri diceva *«quanto manca»*; da oggi dice *«una lista nuova fuori
standard lo fa risalire»* — che è la ragione per cui la «regola zero della
lista» esiste, dove le `DataTable` grezze erano **risalite** da 48 a 57 proprio
mentre nessuno guardava.

*(informativo, non un cricchetto: al 22-09 erano **7** gruppi filtri **vuoti**
— `<div … />` usati da spaziatore. ✅ **Oggi sono zero**: erano tredici in
tutto, perché tre li scriveva `></div>` — stessa cosa, spelling diverso — e tre
usavano `<span>`, che il criterio non guardava affatto. Sono spariti col
`margin-left: auto` sulla barra azioni: la spaziatura è del foglio, non del
markup.)*

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

**Provato contro violazioni vere**, non solo sul verde. Il 22-09: `:store`
tolto dal pilota → rosso sul 2; ricerca fuori da `#sempre` → rosso sul 3; un
blocco grezzo in un file nuovo → rosso sul 1 col nome del file; una larghezza in
più → rosso sul 4; una coppia di date aggiunta → rosso sul 5.
✅ **E di nuovo il 23-09, sui controlli nuovi**: un `<Select>` dentro
`app-page-toolbar-start` → rosso sul 3-bis; `:store` tolto da un
`<DrawerTabLista>` con filtri → rosso sul 2; la ricerca spostata da
`#filtri-sempre` a `#filtri` → rosso sul 3; una larghezza in **rem** → rosso sul
4. Ripristinato tutto dopo ogni prova.

⚠️ **I buchi dichiarati**, aggiornati il 23-09:
* un blocco grezzo il cui `<div` ha la `class` su una riga diversa non verrebbe
  visto (criterio in testa allo script). Nel repo non ce n'è;
* ⭐ **due ne sono stati CHIUSI, e solo perché il cancello è stato allargato**
  (§10.3): leggeva il file intero invece della sola sezione `<template>` — e
  le intestazioni *nominano* i tag di cui parlano — e `senzaSlotSempre`
  lasciava dentro il `</template>` di chiusura. Nessuno dei due si vedeva sul
  verde.

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
   🔴 **E l'adozione ha alzato il conto** (§10.4): oltre alle diciotto coppie
   c'erano **tre** liste che la conversione Date↔ISO se la scrivevano a mano
   fuori da ogni binder, e **due** in cui `data_a` nasceva `ref(null)` invece
   di leggere lo store — filtro attivo con la casella vuota. I punti che
   traducono non stavano solo dove il censimento li cercava.

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

### 9.5 Quel che resta — **L6, e tre decisioni**

* 🔵 **L6** collaudo su smartphone e tablet veri, compresi i casi annidati. È di
  Tid, e resta **l'unica cosa aperta del cantiere**, perché è l'unica che
  nessun presidio sa fare: ✅ i sette controlli del cancello, ✅ `eslint`/
  `oxlint`, ✅ le spec e ✅ il `vite build` sono tutti verdi, e **nessuno di loro
  guarda un telefono**. Il registro del §9.3 dice perché: dodici rilievi su
  quattro giri, tutti **muti** — e il §11.9 ne ha aggiunti due, trovati da Tid
  al primo giro vero a video.
  ⭐ **Cosa guardare per primo**, perché è dove i difetti si sono nascosti finora:
  il **segno** (numero grigio all'apertura, blu al primo cambio, assente quando
  non resta niente che restringa), il **«Pulisci filtri»** dopo aver spostato un
  interruttore che *allarga* (§11.10), i **tab-lista dentro un drawer** — tredici
  liste, le più difficili da vedere — e il **drawer che sale**, che è l'unica
  cosa animata.
* ✅ **Il buco di D8 è chiuso**: l'invariante «`da > a` non può esistere» vive in
  `bindPeriodo`, e non c'è più nessuna lista che scrive la coppia a mano —
  l'ultima era la toolbar delle code di lavoro (§10.4).
* ✅ **Due delle tre decisioni sono chiuse il 23-09** (§8): **A3 sì** — «Pulisci
  filtri» è anche nella toolbar desktop, icona sola col tooltip — e **A2 no**,
  il segno su desktop non si aggiunge. ⭐ Le due si sono decise insieme e con lo
  stesso criterio: *su desktop i filtri si vedono tutti, quindi non manca
  l'informazione — mancava il verbo*.
* 🟡 **Resta aperta la sola A4** (il testo intero nel `title` di una combo
  stretta): serve solo al desktop, dove c'è l'hover, ed è una domanda che il
  collaudo chiude meglio di un ragionamento.

✅ **Il componente ORA È MONTABILE, e la decisione è presa** (Tid, 2026-09-23):
`@vue/test-utils` + `jsdom` sono entrati nel progetto — non per questo cantiere
ma **per tre insieme**, perché rate (17-09), filtri di lista (23-09) e barra del
drawer di magazzino (23-09) avevano lasciato scoperto lo stesso difetto. I
filtri ne hanno pagati due in un giorno solo, e sono citati nella motivazione.
⇒ L'impalcatura è `frontend/test/montaggio.js` (fuori da `src/`, così non finisce
in nessun bundle), il DOM si accende **per file** con `// @vitest-environment
jsdom`, e il primo componente provato è `DrawerActionsBar` (12 test).
✅ **E la spec di `FiltriLista` è stata scritta lo stesso giorno** (ok Tid):
`FiltriLista.spec.js`, **12 test**, che coprono i difetti strutturali che finora
aveva trovato solo l'occhio. ⭐ **Provata contro quattro mutazioni**, una per
difetto vero — togliendo il guard `$slots.default` dal badge (§10.4), rimettendo
«Pulisci» appeso al segno (§11.10), togliendo i valori neutri al conteggio
(§11.9) e spegnendo la ricerca del listener nel vnode (§11): **ogni mutazione
manda rosso un test, e uno solo**.
⚠️ Il montaggio ha chiesto **una riga** all'impalcatura condivisa: `monta()` non
inoltrava gli `slots`, che in `@vue/test-utils` stanno nella radice delle opzioni
e non dentro `global` — scritti nel posto sbagliato vengono ignorati **in
silenzio**, e il test proverebbe il contenitore senza il suo contenuto. Per un BB
che decide *cosa rendere guardando `$slots`* non è un dettaglio.

> ⭐ **Resta però vero l'ordine delle leve, e va tenuto**: *la spec si scrive
> prima sul building block GENERICO, poi sul componente*. Se un difetto si vede
> solo montando, la prima domanda è se la parte che **decide** possa uscire in
> una funzione pura — costa zero dipendenze e copre tutti i consumatori insieme.
> Questo cantiere è il precedente: cinque presidi puri (`segnoFiltri`,
> `clonaFiltri`, i due contratti dei filtri, `useStoreFilterBindings`) e un
> componente rimasto sottile.
> ⛔ **E c'è un confine che nemmeno il montaggio supera**: jsdom **non calcola il
> CSS**. Un badge che copre un glifo, un drawer che si apre alto 10rem, una media
> query sotto i 1024px — cioè *metà* dei dodici rilievi del §9.3 — lì non si
> vedono. Quella metà la presidia **solo L6**. Finché non c'è, dei
BB sono provate le parti pure — `segnoFiltri` (12), `clonaFiltri` (8),
`useContrattoFiltriLista` (12), `useContrattoFiltriLocali` (15) e
`useStoreFilterBindings` (25, che porta `bindPeriodo`) — e il resto risponde al
collaudo in-app, dichiarato e non sottinteso.
🔴 **E il 23-09 quel confine ha presentato il conto**: i due difetti trovati
convertendo — l'imbuto su una lista con la sola ricerca, e lo `<slot>` senza
`v-if` che è un default slot anche quando il caller non passa niente — sono
**esattamente** ciò che una spec di componente avrebbe visto, e che nessuna
funzione pura può vedere. Sono usciti leggendo il codice, non da un presidio.
⇒ La decisione su `@vue/test-utils` + `jsdom` resta di Tid, ma ora ha un costo
misurato: **due difetti in un giorno**, entrambi invisibili da desktop.

---

## 10. Quel che l'adozione ha trovato — 2026-09-23

> ⚠️ **Questa sezione non è un consuntivo, è un elenco di difetti.** Il §4 aveva
> misurato il **costo** (settantasei blocchi, centoquattordici larghezze); non
> poteva sapere *che cosa fossero* quei blocchi, perché per saperlo bisogna
> aprirli. ⭐ È l'uso legittimo di una misura: portare un **controesempio**.

### 10.1 Nove «blocchi filtri» non contenevano nessun filtro

`app-page-filters` era usata come **zona sinistra della toolbar**: il titolo
`<h2>` di una pagina (approvazioni prezzo, cruscotto competenza, tool
fatturazione, code di lavoro, lotti), il `<h4>` delle righe di un documento, il
pulsante «torna alla lista» dell'editor di definizioni. Più **tredici**
spaziatori **vuoti** (`<div class="app-page-filters" />`), messi lì solo per
spingere le azioni a destra.

⛔ **Avvolgerli in `<FiltriLista>` sarebbe stato meccanicamente coerente e
sbagliato**: sotto i 1024px il titolo della pagina sarebbe finito dentro il
drawer dal basso, dietro un'icona a forma di imbuto.

**Deciso da Tid il 2026-09-23**: nasce `app-page-toolbar-start` — stesse regole
flex, nome che dice la verità — e gli spaziatori **spariscono**, perché la
spaziatura è del foglio e non del markup (`.app-page-toolbar > .app-page-actions:first-child`).
⚠️ **E la classe nuova è subito un cancello** (controllo 3-bis): altrimenti
sarebbe la porta di servizio del cricchetto 1 — si rinomina la classe e il
registro non se ne accorge. Il controllo guarda il **contenuto**, non il nome.

⭐ La lezione, e vale oltre questo cantiere: *una classe di layout riusata per
il suo effetto CSS diventa una categoria sbagliata nel primo censimento che
qualcuno ne fa.* `app-page-filters` non descriveva più un gruppo filtri: faceva
un flex.

### 10.2 Quattordici liste non dichiaravano i propri filtri — e il §3.2 diceva che erano coperte

Il §3.2 affermava: *«✅ Copertura: i 49 store che dichiarano `filterDefaults`
passano tutti da `useListaStoreCore`»*. La frase è **vera** e la conclusione era
**falsa**, perché è una tautologia: `filterDefaults` è un'opzione di quel
composable, quindi chi la dichiara ci passa per costruzione. Restavano fuori gli
store che i filtri li tengono **senza dichiararli** — scritti a mano su
`useListaEmptyStateFetch`, con il proprio `buildParams`:

distinte, eccedenze, rate fuori capienza, coda righe e canali d'incasso dei
pagamenti; le due code resi; i lotti; i fondi fattura da decidere; le
definizioni di workflow; le **due code di lavoro**.

🔴 **E questo elenco, riletto il 23-09, ne conteneva due che non c'entravano**
(§11.7): «le impostazioni» non hanno filtri affatto — solo la casella di
ricerca, che per D2 non è un filtro — e «i due cruscotti» non hanno uno store
**lista**, quindi la loro risposta non è questo building block ma quello del
§11.2. Gli store che adottano `useContrattoFiltriLista` sono **dieci**, per
dodici liste. ⭐ È lo stesso difetto che il §10.2 descrive, un piano più su: una
popolazione contata col metro sbagliato — e stavolta dentro la frase che quel
difetto lo denunciava.

⛔ Su di loro `:store` accendeva il `console.error` fail-visible, e il ripiego
`:segno` scritto **nella view** sarebbe stato esattamente la seconda sede che il
§3.2 vieta — *«mai nelle view»* — moltiplicata per quattordici.

**Deciso da Tid il 2026-09-23 (regola del 2)**: le tre righe escono da
`useListaStoreCore` in un building block, **`useContrattoFiltriLista`**, e il
core **lo consuma**. Non è una copia: è la loro unica sede. Uno store a mano lo
adotta in tre righe, senza cedere il proprio `buildParams` — che per quelle
liste diverge davvero (code di lavoro senza pavimento temporale, nomi propri sul
filo). Presidio: `useContrattoFiltriLista.spec.js`, 8 test, verificati contro
due mutazioni.

⭐ **La forma del difetto**, che è quella che conta: una copertura misurata
**sul metro sbagliato**. La domanda non era «quanti store dichiarano
`filterDefaults`» ma «quante liste hanno filtri» — e le due popolazioni non
coincidevano.

### 10.3 Il cancello aveva due punti ciechi, e li ha trovati allargandolo

Estendendo i controlli 2 e 3 ai tab-lista di drawer, il guard è diventato rosso
su **sette** file che erano a posto. Due difetti suoi:

1. **Leggeva il file intero invece della sola sezione `<template>`.** Le
   intestazioni di questi componenti *nominano* i tag di cui parlano («si monta
   con `<DrawerTabLista>`»): quel testo veniva preso per markup, il tag «aperto»
   diventava `<DrawerTabLista>` senza attributi — quindi «senza `:store`» — e la
   ricerca della chiusura inghiottiva mezzo file, tirando dentro `DatePicker`
   che coi filtri non c'entravano. ⇒ **Le regole di markup si leggono nel
   template**, non nel file.
2. **`senzaSlotSempre` lasciava dentro il `</template>` di chiusura**, perché
   `fineBlocco` ne restituisce l'*indice*. Innocuo finché serviva solo a
   cercare la ricerca; appena è servito a dire *«questo blocco ha filtri?»* ha
   fatto sembrare «pieno» un blocco che aveva la sola casella di ricerca.

⚠️ **Nessuno dei due si vedeva sul verde**: sono emersi perché il cancello è
stato **allargato**, non perché qualcosa fosse rotto. È il caso di
`feedback_contratto_dichiarato_provalo_intero` visto dal lato del presidio.

### 10.4 Le cose che il building block ha scoperto essere difetti

Convertendo, il BB ha trovato quattro cose che non davano nessun errore:

| Dove | Che cosa | Perché nessuno se ne accorgeva |
| --- | --- | --- |
| `EmailLogsListView`, `PraticheSearchTable` | `data_a` nasceva `ref(null)` invece di leggere lo store | Un valore rimasto nel filtro restava **attivo con la casella vuota**: la lista era ristretta e il widget diceva di no |
| `AuditLogView`, `EmailLogsListView`, `PraticheSearchTable` | conversione Date↔ISO scritta a mano, con `@date-select` + `@clear-click` | Una data **digitata** non applicava il filtro (§9.3, terza lezione) |
| `strumenti/stores/codeJobs.js` | i filtri data si chiamavano `dataDa`/`dataA` e tenevano **oggetti `Date`** | Era l'unica coppia del prodotto fuori standard, quindi **l'unica che non poteva passare da `bindPeriodo`** — cioè l'unica senza l'invariante D8. Rinominati `data_da`/`data_a` in ISO, come ogni altra lista |
| `FiltriLista` (il BB stesso) | su una lista con la **sola** ricerca rendeva l'icona a imbuto e un drawer **vuoto** | Da desktop il ramo compatto non si rende affatto: il difetto esisteva solo sotto i 1024px, dove nessuno guarda mentre scrive il codice |

⭐ E il quarto ha un gemello nei contenitori: uno `<slot name="filtri" />`
scritto **senza `v-if`** è un default slot per `FiltriLista` anche quando il
caller non passa niente — la funzione dello slot esiste e rende il vuoto. ⇒ Nei
BB che inoltrano slot, la **condizione sta sul `<template>`**, non sul widget
dentro.

### 10.5 Una decisione locale presa convertendo

* **`RatePickerDialog`**: il lookup del **cliente** è andato in `#filtri-sempre`
  come se fosse una ricerca. Non è una forzatura di D2: lì il cliente è il gesto
  principale — finché non lo si sceglie (o non si digita un numero) la lista
  **non chiede niente al backend** (`startsEmpty` + `gateKeys`). Nel drawer,
  l'operatore avrebbe visto un elenco vuoto e un imbuto, cioè un dialog che non
  dice come si usa.
* **`ArticoloBomDrawer`**: il `Checkbox` + `<label>` del filtro «tutte le
  versioni» è diventato `FiltroToggle` — era l'ultima copia a mano di un
  interruttore di filtro, e nella griglia del drawer il BB prende la riga intera
  da sé.
* **`DistintaDrawer`**: «Mostra scartate (N)» stava in una barra **sopra** la
  lista; è un filtro di quelle righe, quindi è sceso nello slot `#filtri` del
  tab-lista — e da oggi conta nel segno.

---

## 11. La rilettura critica — 2026-09-23

> ⚠️ **Questa sezione non è un consuntivo né un elenco di migliorie: sono
> difetti**, trovati rileggendo il cantiere a lavoro finito e a tutto verde —
> `eslint`/`oxlint` puliti, 220 test verdi, sei controlli del cancello a zero,
> `vite build` verde. **Nessuno dei nove accendeva niente.**
> Tutti chiusi in giornata (ok di Tid: «direi di risolvere tutto»).

### 11.0 La lezione, che viene prima dei nove

> **Un verbo nuovo montato su cinquanta superfici vecchie non è una funzione
> aggiunta: è un contratto nuovo che quelle superfici non hanno mai firmato.**

Il cantiere ha introdotto `azzeraFiltri()` — «Pulisci filtri» — e l'ha reso
raggiungibile da ogni lista. Ma quel verbo scrive **nello store**, e dà per
scontato che i widget lo rileggano. Cinquanta liste su settanta lo facevano
(passano dai binder di `useStoreFilterBindings`, che hanno il `watch`
store → widget); **ventitré no**: tenevano i filtri in `ref` che spingevano
nello store e non tornavano mai indietro.

⭐ Il §10 aveva già scritto la regola giusta — *«un BB unifica la lettura, e i
punti che traducevano si cercano uno per uno»* — e l'aveva applicata alle
**date**. Non a ciò che il BB stesso stava aggiungendo. ⇒ *Quando un building
block porta un verbo che scrive, il censimento non è «chi rende questa cosa» ma
**«chi la rilegge»**.*

### 11.1 🔴 «Pulisci filtri» non arrivava a 49 filtri in 23 file

**Il difetto.** `azzeraFiltri()` riporta `store.filters` ai default e rilegge.
Un filtro montato così —

```js
const attivoFilter = ref(true)
function onAttivoChange() { store.filters.attivo = attivoFilter.value; applyFilters() }
```

— non ha il verso di ritorno: dopo «Pulisci», la lista mostra tutti gli attivi e
la combo continua a dire «solo disattivati». **È la lista che mente del §1.2,
rovesciata**: stavolta è il *widget* a mentire sulla lista.

⚠️ E si vede **solo sotto i 1024px**, perché il pulsante vive nel drawer: nessun
collaudo al monitor poteva trovarlo.

🔴 **Il caso peggiore era `RatePickerDialog`**: la sua lista parte vuota
(`startsEmpty` + `gateKeys`), quindi «Pulisci» la **svuotava** mentre il lookup
continuava a mostrare il cliente scelto — un dialog che dice «nessuna rata per
questo cliente» con il cliente non più fra i criteri.

⭐ **Che non fosse una politica lo diceva un file solo**: `PraticheSearchTable`
aveva il `watch` scritto a mano per **uno** dei quattro filtri e non per gli
altri tre. Non una scelta: una dimenticanza, copiata ventitré volte.

**La correzione.** I 49 filtri passano ai binder (`bindSelect`, `bindLookup`,
`bindToggle`), che il `watch` ce l'hanno per costruzione. Dove un binder non
arriva perché il punto **traduce**, il filtro diventa un `computed` sullo store
— che è meglio, perché lo stato non si copia affatto:

| Dove | Forma | Perché non un binder |
| --- | --- | --- |
| `ContrattiSearchTable` · `scadenza_mese` | `computed` get/set | lo store tiene `YYYY-MM`, il widget una `Date`. Unica occorrenza: la regola del 2 dice di estrarre alla **seconda** |
| `RatePickerDialog` · numero, serie | `computed` get/set | la serie normalizza `''` → `null` |
| `LottiListView` · `stato_lotto` | `ref` + `watch` esplicito | `syncFiltri()` decide il reset a pagina 1 **confrontando** ref e store: con un binder i due sarebbero sempre uguali e l'offset non si azzererebbe mai |

⛔ **Ciò che non va bene resta la terza forma**: un `ref` che scrive nello store
e non lo rilegge. Sta scritto negli standard, §«Un filtro si lega con un
binder».

### 11.2 🟠 Cinque superfici scrivevano l'elenco dei filtri quattro volte

Il ripiego `:segno` — legittimo, e deciso — costringeva ogni superficie senza
store-lista a ripetere le chiavi **tre volte nella stessa chiamata** (valori,
array delle chiavi, oggetto dei default), più un `pulisciFiltri()` a mano che
ripeteva i default una **quarta**.

⛔ **E la terza sede si era già dimenticata**: in `ArticoloBomDrawer` una chiave
stava nei valori e **non** nell'array delle chiavi. Lì era innocuo (era la
ricerca, che per D2 non è un filtro), ma è esattamente la forma in cui il
difetto nasce.

**La correzione (regola del 2, cinque occorrenze):** nasce
`useContrattoFiltriLocali`, dove chiave, `ref` e default stanno sulla **stessa
riga** e `segno`/`azzeraFiltri()` si derivano.

🔴 **Due difetti trovati mentre lo si scriveva**, e nessuno dei due era nel
piano:

1. **Il default non si può fotografare dal `ref`.** La prima stesura lo faceva
   («il default è il valore alla nascita», come per uno store). Per un `ref` del
   componente è vero; per i **due cruscotti** no — i loro filtri vivono in uno
   store `userScoped` che **sopravvive al componente**, quindi al secondo
   montaggio la «nascita» avrebbe fotografato il filtro lasciato dall'operatore:
   pallino invece del numero, e «Pulisci» che riporta al filtro di prima invece
   che al default. ⇒ Il default si **dichiara**, come `filterDefaults`.
2. **Una `computed` senza dipendenze reattive è di nuovo una fotografia.** Per
   il default «oggi» serve una funzione che si **ri-risolva**; tenendola in una
   `computed` si sarebbe calcolata una volta e cachizzata per sempre — con in
   più l'aria di non esserlo. ⭐ **L'ha trovata la spec**, non il collaudo.

### 11.3 🟠 Il default «oggi» del drawer BoM era scritto in quattro posti, e due divergevano

`ArticoloBomDrawer` teneva il metro del segno in `OGGI_ALLA_NASCITA`
(`new Date()` al setup) e, **riaprendo il drawer**, rimetteva il filtro a
`new Date()`. Due istanti diversi di qualche millisecondo: per `segnoFiltri` due
filtri diversi. ⇒ **Bastava riaprire il drawer per vedere il numero al posto del
pallino**, senza aver toccato niente.

**La correzione:** il default è `addDaysToToday(0)` — mezzanotte di **oggi**,
stabile dentro la giornata e che si sposta quando la giornata si sposta — ed è
dichiarato **una volta sola** nel contratto; la riapertura chiama
`pulisciFiltriBom()` invece di riscrivere i valori.

### 11.4 🟠 Il segno del giornale lotto si leggeva al contrario

«Mostra tutto» **allarga** la storia. Contando la variabile del widget
(`giornaleInfoVisibili`) usciva **«1 filtro attivo»** proprio quando non ne
filtrava nessuno, e il pallino compariva quando la lista *era* ristretta.
⇒ Il filtro vero è il suo opposto — «solo problemi» — e si dichiara con un
`computed` scrivibile. ⭐ Il contratto nuovo lo ammette apposta.

### 11.5 🟠 Un `:store` puntava alla lista sbagliata

`ContrattiBillingAccountDrawer` passava `:store="store"` (lo store della **lista
contratti**) mentre le sue righe sono locali e il filtro di stato è
**client-side**. Due cose sbagliate insieme, e nessuna dava errore: il segno
contava i filtri di **un'altra schermata**, e «Pulisci filtri» azzerava *quei*
filtri rilanciando *quella* fetch, lasciando intatta la tendina che l'operatore
stava guardando. ⇒ Passa a `:segno` + `useContrattoFiltriLocali`.

### 11.6 🟠 Il cancello: rosso dove non doveva, cieco dove doveva

**(a) Falsi positivi.** I blocchi `<DrawerTabLista>` venivano letti **per
intero**, quindi le regole dei filtri cadevano su cose che filtri non sono —
provato e riprodotto: una `<Column style="width: 120px">` faceva scattare il
controllo 4 («larghezza inline nei filtri»), e due `<DatePicker>` nello slot
`#testata` — che quel componente documenta come *«il posto della form di
inserimento»* — facevano scattare il 5 («coppia di date scritta a mano»).
⛔ È la forma peggiore: *un cancello che boccia a caso viene spento, e allora non
presidia più nemmeno i casi per cui era nato.* ⇒ Per i tab-lista si guardano
**solo** i due slot dei filtri.

**(b) Tre buchi non dichiarati**, chiusi:

* `WIDGET_FILTRO` non vedeva `<AutoComplete>` di PrimeVue (C maiuscola) mentre
  vedeva `<ComuneAutocomplete>`: un lookup grezzo nella zona sinistra passava il
  3-bis. Stampo di `feedback_whitelist_dal_percorso_reale`;
* `senzaSlotSempre` con la chiusura non trovata restituiva la **stringa vuota**,
  cioè un blocco che sembra senza filtri e due controlli spenti in silenzio;
* il controllo 2 guardava che `:store` fosse **scritto**, non che dietro ci fosse
  qualcosa. ⇒ Nasce il **2-bis**: risolve lo store e verifica che passi da
  `useListaStoreCore`/`createListaStore`/`createCrudStore`/`useContrattoFiltriLista`.
  ⚠️ Il buco che resta è **dichiarato e stampato**: quando lo store arriva come
  *prop* (`DrawerTabLista`, `GeoSearchTable`, `CodaFiltriToolbar`) il file finisce
  fra i «non verificabili». *Un cancello che tace su ciò che non sa guardare fa
  credere di averlo guardato.*

✅ Tutti e sette i controlli **riprovati contro violazioni vere** e contro i due
falsi positivi, ripristinando dopo ogni prova.

### 11.7 🟡 Cose che il codice non diceva più

* **La copia dei default era SUPERFICIALE.** `Object.freeze({ ...filterDefaults })`
  congela un livello: con un default ad **array** il metro resta *lo stesso*
  array del letterale, e il primo `push` del widget lo sposta insieme alla cosa
  misurata — da lì il segno direbbe «sempre al default» per sempre. ⛔ Il caso è
  **dichiarato ammesso** dal contratto (`segnoFiltri` tratta apposta gli array, e
  la sua spec ha quel caso), quindi si presidia anche senza occorrenze: *zero
  occorrenze è l'assenza di un controesempio, non l'assenza del caso*. Nasce
  `core/utils/clonaFiltri.js`, con tre consumatori e una sede.
* **Una regola CSS dichiarata transitoria non era scaduta: era diventata un
  difetto.** `.app-filtri-drawer__corpo > .p-datepicker` diceva di sé *«a zero,
  questa regola si toglie»*, il registro era a zero e la regola c'era ancora — e
  stringeva a mezza riga i due DatePicker **soli e legittimi** rimasti.
* **Le regole della griglia dipendevano dalla forma del markup.** Erano scritte
  come figli **diretti** (`>`): un filtro dentro un `<div class="form-field">`
  con la sua etichetta le perdeva in silenzio (la taglia non si annullava,
  l'interruttore restava a mezza riga). Tre siti nel repo. ⇒ descendant + `:has()`,
  perché la regola parla del **filtro**, non dell'involucro.
* **Due condotti per lo stesso stato** in `CodaFiltriToolbar`: un `defineModel`
  *e* la prop `store`, con un commento che *asseriva* che fossero lo stesso
  oggetto. Lo erano per abitudine dell'unico chiamante. ⇒ Uno solo.
* **La soglia compatta aveva tre grafie** nei fogli (`1023.98px`, `1023px` ×2)
  per un numero che §3.3 dichiara «in UNA sede» — e la tabella del §3.3 ne citava
  una quarta (`1024px`) che il foglio non ha mai avuto. Allineate, e ogni sito
  cita `BREAKPOINTS.TABLET`.
* **`:inert` stava sul corpo del drawer e non sul footer**, cioè su tutto tranne
  l'unico comando che **scrive**. Irraggiungibile oggi; non più di una rotazione
  dall'esserlo.
* **Il §10.2 contava la propria popolazione col metro sbagliato** — lo stesso
  difetto che quella sezione denuncia: fra i «quattordici store che non
  dichiaravano i filtri» c'erano «le impostazioni» (che filtri non hanno) e «i
  due cruscotti» (che uno store-*lista* non ce l'hanno). Sono **dieci** store,
  per dodici liste.

### 11.8 Che cosa esiste in più, adesso

| File | Che cosa |
| --- | --- |
| `core/utils/clonaFiltri.js` + `.spec.js` | staccare un valore di filtro dal letterale che lo dichiara — **8 test** |
| `core/composables/useContrattoFiltriLocali.js` + `.spec.js` | il contratto dei filtri per le superfici senza store-lista — **13 test** |
| `scripts/check-filtri-lista.mjs` | **sette** controlli (nasce il 2-bis), i blocchi tab letti solo negli slot dei filtri, tre buchi chiusi e uno dichiarato |

**Verifiche (2026-09-23, dopo la rilettura)**: `eslint` + `oxlint` puliti,
**17 `[ok]`** su `npm run guards`, `check_classi_morte.py` e `check_i18n_keys.py`
puliti, **vitest 243 test su 26 file** (erano 220 su 24), `vite build` verde.
⛔ **E nessuna di queste è un collaudo**: L6 resta, e resta l'unica cosa che
nessun presidio di questo cantiere sa fare — guardare un telefono.

### 11.9 🔴 Il primo collaudo in-app, e i due difetti che ha tirato fuori

> Tid, 2026-09-23, su `/catalogo/articoli`: *«ho attivato il solo filtro
> composito SI e vengono conteggiati 2 filtri»*, poi *«quando apro la schermata
> compare 0, se attivo composito compare 2, se tolgo composito 0»*.

⭐ **La diagnosi che sembrava ovvia era sbagliata, e va detto perché la lezione
è lì.** La prima lettura — la mia e quella del rilievo — era *«conta anche la
ricerca»*. Riprodotto lo stato esatto, non era vero:

```
chiaviFiltro = [ attivo, is_composito, tipo_voce_id, gruppo_voce_id ]   ← `search` NON c'è

1. lista appena aperta   -> { stato: 'default',    conteggio: 1 }   ← pallino
2. digito «art»          -> { stato: 'default',    conteggio: 1 }   ← invariato
3. composito = SI        -> { stato: 'modificato', conteggio: 2 }
```

Il **2** era `attivo = SI` (default dello store) + `composito = SI`. ⇒ *Un
rilievo in-app dice sempre una verità; la causa che gli si attribuisce quasi
mai. Si riproduce prima di correggere.*

**Difetto A — la forma nascondeva il conteggio.** Lo stato «tutto al default»
era un pallino senza numero, quindi lo stesso filtro (`attivo`) valeva **zero**
un istante e **uno** quello dopo: toccando una cosa sola si leggeva «0 → 2».
⇒ Il numero adesso c'è sempre, e la differenza la fa il **colore** (D4, tabella
aggiornata). La regola del conteggio non è stata toccata.

**Difetto B — un filtro che non si poteva togliere.** Su articoli il filtro
«attivo» offriva solo `Attivo`/`Non attivo`: niente «Tutti», niente
`show-clear`. Contava un'unità su cui l'operatore **non aveva nessun gesto**.
⛔ Era l'**unico filtro del prodotto** in quella forma — le altre dodici liste
con «attivo» offrono tutte «Tutti», e tre (magazzini, lotti, ubicazioni) usano
la forma migliore, `bindToggle('attivo', { on: null, off: true })`, dove
accendere «mostra non attivi» porta il filtro a `null` e **lo fa smettere di
contare**.

#### La verifica che ne è seguita — «ci sono altre liste così?» (Tid)

Sì, e in **due** famiglie distinte.
🔴 **⚠️ Questo elenco è INCOMPLETO sulla seconda famiglia, e lo si è scoperto
riverificandolo la sera stessa: mancavano quattro filtri, uno nello store che
questo stesso giro stava modificando. Il censimento corretto e la regola che li
trova tutti sono in §11.10 — quanto segue resta com'era scritto, perché il modo
in cui è stato contato è parte del difetto.**

**① Filtri che non si possono togliere** — oltre ad articoli, uno solo, e
peggiore: `/catalogo/unita-misura?tab=conversioni` filtrava `attivo: true` con
**nessun widget**. La lista mostrava le sole conversioni attive, l'operatore non
poteva cambiarlo, e siccome quel blocco aveva la sola ricerca `FiltriLista` non
rendeva nemmeno l'icona: **nessun segno lo diceva**. ⇒ Aggiunto l'interruttore
«Mostra non attive», nella stessa forma delle tre liste di magazzino.
🟡 Restano **per scelta** i floor data con `clearTo` (contratti, code di
lavoro): svuotando `data_da` torna il floor, quindi non si tolgono — ma
restringono davvero, e il conteggio è vero.

**② Filtri che contano senza restringere niente** — la famiglia del «mostra
tutto» del giornale lotto (§11.4), che isolata non era:

| Filtro | Valore neutro | Perché non poteva essere `null` |
| --- | --- | --- |
| `offerte` · `solo_ultima_revisione` | `false` («mostra storico») | il BE è `qp_bool(..., default=True)`: **assente significa `true`**, quindi il `false` va mandato per forza |
| `preventivi` · idem | idem | idem |
| code di lavoro · `ambito` | `'tutti'` | `buildCodaParams` manda il parametro **solo** quando vale «tutti»: sul filo il silenzio è «miei», nel dominio è il contrario |
| drawer Lotto · `ampiezzaTask` | `'TUTTI'` | `AMPIEZZE_TASK.TUTTI === null`: una `ref`, non va sul filo |
| `pratiche` · `solo_interne` | era `false` | ⭐ qui il BE fa `... or False`, quindi il rimedio migliore non è dichiarare il neutro: è **smettere di mandarlo**. Default `null` e `bindToggle` senza `off` — è la forma che quel binder già dichiara di default, *«un `false` sul filo è un parametro che il backend legge senza che filtri niente»* |

⇒ Nasce **`filtriNeutri`**, dichiarato accanto ai `filterDefaults` (e `neutro`
riga per riga in `useContrattoFiltriLocali`). ⛔ Non si indovina e non si
deriva: è conoscenza del **filtro**, come `paramNames` e `gateKeys` — e le due
righe qui sopra lo dimostrano, perché `archiviate: false` (code di lavoro) è
l'esatto contrario, **nasconde** le righe archiviate e quindi conta a ragione.

⚠️ **Niente cancello per questa famiglia, ed è una scelta dichiarata.** Un
controllo statico non può sapere se un valore restringe: boccerebbe
`archiviate: false`, che è legittimo. Vale il criterio di casa — *un cancello
che capisce un caso su cinque boccia a caso, e dopo due blocchi sbagliati
qualcuno lo spegne*. Il presidio praticabile è la **spec**: `segnoFiltri` ha
quattro test sui neutri (spegnendo la riga ne vanno rossi tre) e
`useContrattoFiltriLocali` il suo gemello.

**Verifiche (2026-09-23, dopo il collaudo)**: `eslint` + `oxlint` puliti,
**17 `[ok]`** su `npm run guards`, **vitest 248 test su 26 file**, `vite build`
verde, `check_i18n_keys.py` con la sola differenza delle due chiavi nuove
(parità it/en integra).

---

### 11.10 🔴 La riverifica del §11.9 — quattro filtri della stessa famiglia, e un verbo che spariva

> ⚠️ **Il §11.9 dichiara un censimento chiuso** — *«ci sono altre liste così?
> Sì, e in **due** famiglie distinte»* — e la riverifica lo ha smentito sulla
> seconda. Non è un dettaglio: è **la terza volta in due giorni** che una
> popolazione contata una volta sola si rivela incompleta (§10.2 con i
> «quattordici store», §11.7 con lo stesso elenco riletto, adesso qui).

#### La regola che il §11.9 non aveva scritto, e che li avrebbe trovati tutti

> **Un interruttore «mostra anche X» ha SEMPRE un valore neutro: è quello
> acceso.** Spento nasconde qualcosa — restringe, e conta a ragione; acceso
> apre l'elenco al massimo che quella lista sappia mostrare.

Il §11.9 aveva guardato i filtri **uno per uno** e aveva trovato i tre che
avevano dato fastidio a video. Il prodotto ne aveva **sette** della stessa
forma, e il discriminante non è il valore: è il **mestiere** del filtro — e il
dominio lo dichiara già altrove, perché un interruttore che allarga porta il
conteggio di ciò che nasconde (`archiviate_count`, `scartate_count`,
`annullati_count`) e uno che restringe no (catalogo BB, `FiltroToggle`).

| Dove | Filtro | Neutro | Perché nessuno se ne accorgeva |
| --- | --- | --- | --- |
| `strumenti/stores/codeJobs` | `archiviate` | `true` | ⛔ **È lo store che il §11.9 aveva in mano**: gli ha aggiunto `filtriNeutri: { ambito: 'tutti' }` e ha lasciato fuori il filtro accanto. Il §11.9 cita `archiviate: false` come esempio di «conta a ragione» — vero, e la domanda «e da acceso?» non se l'è posta |
| `vendite/stores/lotti` | `annullati` | `true` | `annullati: 1` sul filo chiede i lotti annullati **in più** |
| `pagamenti/stores/distintaRighe` | `scartate` | `true` | idem: acceso, l'elenco è tutta la distinta |
| `ArticoloBomDrawer` | `tutto` | — | vedi sotto: lì il rimedio non è un neutro |

#### ⛔ Il drawer BoM non voleva un neutro: voleva **una chiave in meno**

`valido_al` e «tutte le versioni» erano **due** chiavi del contratto. Ma
l'interruttore non è un filtro: è ciò che **spegne** `valido_al` — e il
`computed` scrivibile che lo dice esisteva già. Contarlo a parte faceva due
cose sbagliate insieme, nessuna delle quali dava errore:

* a interruttore **spento** l'elenco era ristretto da **una** cosa sola (la
  data) e il segno diceva **2**;
* a interruttore **acceso** non restringeva più niente e il segno diceva **1** —
  il numero che sale mentre la lista si allarga, cioè esattamente il difetto
  del §11.9, dentro la correzione del §11.9.

⇒ `tutto` esce dalle chiavi; il legame fra i due vive **solo** nel `set` del
`computed`, che adesso spegne l'interruttore quando una data viene scritta —
senza, «Pulisci filtri» rimetteva la data di oggi e lasciava acceso ciò che
quella data la annulla. ⭐ È la stessa forma di `FiltroPeriodo`: *due estremi
sono un filtro solo*; qui, *un filtro e il suo interruttore sono un filtro
solo*.

#### 🔴 E il difetto peggiore era nel building block: «Pulisci filtri» spariva

`puoPulire` chiedeva `haSegno`. Le due domande — *«c'è un segno da mostrare?»* e
*«c'è qualcosa da riportare al default?»* — coincidevano finché «non restringe»
voleva dire «non c'è»; **i valori neutri le hanno separate**. Da allora:

* un filtro portato al valore neutro («mostra non attive» sulle conversioni,
  «tutte le versioni» nel BoM) o **un default svuotato a mano** («Tutti» su
  articoli, dove la voce l'ha appena aggiunta il §11.9) lascia la lista intera:
  nessun segno — e quindi **nessun pulsante**;
* ⛔ ma è lo stato in cui «Pulisci» è l'**unico** gesto che riporta indietro:
  l'operatore doveva ricordarsi *quale* interruttore aveva spostato.

⇒ `segnoFiltri` restituisce anche **`modificato`** — la risposta alla seconda
domanda, che prima veniva calcolata e **buttata via** nel ramo `vuoto` — e
`puoPulire` la legge. ⚠️ Il pulsante si **aggiunge** dove mancava: non si toglie
dallo stato «tutto al default», dove oggi c'è e ricarica la pagina 1.

#### Le altre tre cose, più piccole

* **I neutri del contratto locale erano congelati in superficie**
  (`Object.freeze` + nessuna copia) mentre il gemello sugli store passa da
  `clonaFiltri`: con un neutro ad **array** il metro sarebbe rimasto *lo stesso*
  array del letterale. È la §11.7, un piano più giù — il caso è **dichiarato
  ammesso** dal contratto (`uguale()` tratta apposta gli array), quindi si
  presidia anche senza occorrenze.
* **Un neutro su una chiave che non è un filtro non diceva niente**: refuso →
  no-op silenzioso, e il segno continua a contare il filtro vero. Adesso è
  `console.error`, stesso stampo del guard di `FiltriLista` e di
  `useContrattoFiltriLocali`. ⚠️ Nel contratto **locale** non serve: lì `neutro`
  sta sulla riga del filtro, e una chiave sbagliata non esiste.
* **La regola CSS `:not(.p-badge-dot)` era scaduta il giorno stesso**: col
  numero sempre presente `Badge` non entra più nello stato «dot», quindi
  proteggeva uno stato che non esiste. Tolta (la *lezione* sulla specificità
  resta scritta accanto). Stessa forma del rilievo §11.7 sulla regola
  transitoria mai scaduta.

#### 🟡 Due cose viste e NON toccate, perché sono decisioni

* ✅ **`rate.solo_numerate` — risolto il 2026-09-23, decisione di Tid: non era
  un filtro, era un PERIMETRO.** Era la terza occorrenza della famiglia ① del
  §11.9 («un filtro che l'operatore non può togliere»), e le prime due si
  curavano con un gesto — «Tutti» nell'elenco, un interruttore. Questa no: il
  gesto non doveva esistere. *La rata di un documento non numerato non è un
  credito su cui registrare un incasso* è una regola del **dominio**, quindi
  vale per ogni client — e stava scritta nel frontend, cioè era vera solo per
  il client che si ricordava di mandarla.
  ⇒ La regola è scesa nel backend (`list_rate` e `list_rate_paginata`, default
  `True`; l'assenza del parametro significa «applica la regola», non «falso»), e
  `solo_numerate` è uscito da `filterDefaults`: il picker non lo manda più e il
  suo segno non conta più un filtro che a video non esiste. La via d'uscita
  resta, dalla parte giusta (`?solo_numerate=false`).
  ⭐ **La lezione, ed è la ragione per cui sta scritta in api.md e negli standard
  FE**: `filterDefaults` risponde a **due** domande — «cosa mando al backend» e
  «cosa conto come filtro» — e per un perimetro le due risposte divergono. Il
  sintomo che l'ha fatto emergere è piccolo (un «1» nell'imbuto), la causa no.
  ⚠️ Provato sul **database vero**, non su un mock: `test_rate_lista_db` ora
  costruisce la bozza e verifica che senza dire niente resti fuori, e che
  chiedendo `solo_numerate=False` rientri — il perimetro è una scelta, non un
  dato che manca. ⏳ Invariato il resto: il predicato più stretto di Tid («solo
  le definitive, inviate a SDI») arriva col cantiere SDI, in una sede a DB.
* ✅ **La terna `Tutti / Attivo / Non attivo` — estratta il 2026-09-23, ok di
  Tid.** ⚠️ E il censimento fatto per estrarla ha alzato il conto: non erano due
  sedi ma **cinque**, e la quinta era già una **factory** in un altro dominio
  (`amministrazione/constants.js::buildFilterStatoOptions`), cioè la prova che
  l'estrazione era stata fatta una volta e poi ricopiata lo stesso.
  ⇒ `core/utils/options.js` → **`buildAttivoOptions(t)`**, accanto a
  `buildBoolOptions`; la factory di dominio è **ritirata**, non lasciata come
  alias. ⛔ **E le copie erano già divergenti**, che è il motivo per cui una
  duplicazione non è mai solo estetica: `ListiniSearchTable` e
  `FamiglieDocumentoListView` scrivevano **«Inattivo»** nella tendina e **«Non
  attivo»** nella colonna — due parole per lo stesso stato, nella stessa
  schermata — e la copia di `ListiniSearchTable`, che sta in `vendite`, leggeva
  le chiavi i18n di `amministrazione`. Allineato anche
  `amministrazione.stato_inattivo` (IT) a «Non attivo», così le colonne che
  usano ancora quelle chiavi dicono la stessa parola delle tendine.
  ⚠️ **Restano fuori di proposito** due terne che *sembrano* la stessa:
  `buildFilterSuperAdminOptions` e il filtro dei registri di numerazione («Solo
  attivi / Solo disattivati»). Hanno etichette diverse perché fanno una domanda
  diversa: unificarle cambierebbe ciò che l'operatore legge, e sarebbe una
  decisione, non un'estrazione.

**Verifiche (2026-09-23, dopo la riverifica)**: `eslint` + `oxlint` puliti,
**17 `[ok]`** su `npm run guards` (i tre registri restano a zero), **vitest 251
test su 26 file**, `vite build` verde. I due presidi nuovi provati **contro le
mutazioni**: spegnendo il congelamento profondo e il `console.error` vanno rossi
uno per fix.
