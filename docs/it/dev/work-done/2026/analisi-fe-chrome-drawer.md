# Analisi — Il chrome dei drawer, e la sede che ancora non c'è

> **Tipo**: analisi · **Data**: 2026-10-03 · **Owner**: Tid ·
> **Stato**: ✅ **CHIUSA il 2026-10-03** — collaudo a video verde (Tid,
> 2026-10-03), compreso il dialog dei componenti BoM. Sede `AppDrawer` scritta,
> 80 drawer laterali migrati (gli 82 file grezzi meno le due sedi E), divieto
> nel lint; D-1…D-14 chiusi. Le regole vivono in `frontend-standards`
> (§«Drawer (nuovo e modifica)», §«Import PrimeVue riservati», §AppDialog) e
> nel catalogo BB; questo documento resta come storia e motivazione.
> ⏳ **Unico residuo**, registrato in `.codex/PROJECT_CONTEXT.md` § «Aperto»
> perché sopravviva alla chiusura: l'editor dei workflow (`DefinizioneEditorView`,
> `useEditableCollection`) non ha la fotografia dei form di riga (§9, D-13).
>
> 📍 **Dove siamo (2026-10-03)**
>
> - ✅ **Decisioni** (§7): accolte tutte le proposte (Tid, 2026-10-03).
> - ✅ **D-1, uscite che perdevano il lavoro**: corrette in **tre** drawer, non
>   uno — `ContrattoRigheDrawer`, `FamigliaDocumentoDrawer`, `DistintaDrawer`
>   (col suo `DistintaRigaForm`). Dettaglio in §4 D-1.
> - ✅ **D-3, la sede**: `AppDrawer` riscritto (§5), con `AppDrawer.spec.js`
>   (10 test) e il guard delle larghezze esteso. `CanaleIncassoDrawer`, l'unico
>   consumatore, era già compatibile.
> - ✅ **Collaudo a video** di D-1 sui tre drawer (§8): verde.
> - ✅ **Lotto `core`** (§9): tutti e 7 i drawer laterali su `AppDrawer`,
>   compresi i due «modal» con la testata a conteggio (D-10, ok Tid).
>   Drawer laterali grezzi: **73** (erano 80), tutti nei domini.
> - ✅ **Lotto `amministrazione`** (§9): tutti e 18 su `AppDrawer`.
> - ✅ **Lotto `vendite`** (§9): tutti e 18 su `AppDrawer`, documenti compresi.
>   Drawer laterali grezzi: **37**.
> - ✅ **D-11**: il footer dei documenti è il BB `useFooterDocumento`, usato da
>   tutti e 6 (ok Tid).
> - ✅ **Ultimi lotti** (§9): `anagrafiche` 10, `catalogo` 7, `magazzino` 6,
>   `ui` 5, `config` 3, `pagamenti` 2, `pratiche` 2, `portale` 1, `strumenti` 1.
>   Drawer laterali grezzi: **0**.
> - ✅ **Divieto nel lint** (§6): `primevue/drawer` è fra gli import riservati,
>   sedi `AppDrawer`, `AppLayout`, `FiltriLista`. **Nessun registro**: non c'è
>   debito da far calare.
> - ⚠️ **D-4 rivista** (§9, «La sola lettura sul corpo»): `app-readonly` sul
>   corpo spegneva il kebab di riga e i pulsanti di consultazione. Nasce
>   `proteggiCorpo`, spento dove la classe prima non c'era.
> - ✅ **D-8** (Tid: «mettere la conferma»): cambiare riga col form inline
>   modificato chiede, dal BB `useFormInline` (`confermaCambio`), in 9 drawer.
> - ✅ **D-12** (Tid: «uniformali, nessuna eccezione»): i drawer di `ui` si
>   chiudono col clic fuori come tutti, la nota è tolta.
> - ✅ **D-14** (rilievo di Tid sul dialog dei componenti, ok «procedi»): i 44
>   `AppDialog` con campi chiedono prima di uscire con dati inseriti
>   (`confermaUscita` di AppDialog + `useFotografiaDialog`), presidiati dalla
>   regola 6 del guard. Dettaglio in §9, D-14.
> - ✅ **D-13** (ok Tid): i form di riga di DDT, ordini, preventivi, resi e
>   documenti interni hanno la fotografia; cambio riga e uscita dal drawer
>   chiedono. ⏳ Residuo dichiarato: l'editor dei workflow (§9, D-13).
> - ✅ **Collaudo a video** verde (Tid, 2026-10-03).
>
> 📍 **Perché esiste.** Il 2026-10-03 il lint ha preso a fermare gli import
> PrimeVue che hanno un wrapper nostro (frontend-standards §«Import PrimeVue
> riservati»). Il passo naturale era `primevue/drawer`, con sede `AppDrawer`.
> Ma `AppDrawer` **non è un'alternativa**: è un guscio crea/modifica minimo,
> usato da **un** file (`CanaleIncassoDrawer`). Un divieto senza un posto dove
> andare non si può rispettare: congela il debito, e ogni drawer nuovo nasce
> come eccezione.
>
> ⇒ Questo documento censisce che cosa fanno i drawer, separa ciò che è
> **comune** (e deve avere una sede) da ciò che è **contenuto** (e resta del
> chiamante), e raccoglie le **divergenze** trovate. La forma della sede è
> decisa in §7 ed è scritta (§5).

---

## 1. Il perimetro, in numeri datati

Fatti al 2026-10-03, dal codice. Servono a trovare errori, non a decidere la
forma (regola zero).

- **83 file** importano `primevue/drawer`, un `<Drawer>` per file:
  `AppDrawer` + **9** in `core/` + **73** nei domini (vendite 18,
  amministrazione 18, anagrafiche 10, catalogo 7, magazzino 6, ui 5, config 3,
  pagamenti 2, pratiche 2, portale 1, strumenti 1).
- ⚠️ Correzione rispetto a quanto scritto in chat lo stesso giorno: i drawer
  grezzi sono **82** (83 meno `AppDrawer`), di cui 73 fuori da `core/`.
- Il censimento è stato fatto con uno script usa-e-getta, che legge ogni tag
  `<Drawer>`: attributi, slot `#header`/`#footer`, posizione di `FormFooter`,
  composable chiamati (con la parentesi, non il solo nome nell'import). Se si
  vuole riproducibile, va messo in `frontend/scripts/` (§7, D-7).

## 2. Che cos'è un drawer in questo software

Dal modello, non dai conteggi: un drawer è **il pannello laterale destro in cui
si lavora su una cosa** senza perdere la lista sotto (frontend-standards
§«Drawer (nuovo e modifica)»). Le cose su cui si lavora sono di cinque forme:

| Forma | Che cosa fa | Esempi |
| --- | --- | --- |
| **A. Form** | crea o modifica UNA entità: campi, Annulla/Salva | `CanaleIncassoDrawer`, `EmailAccountDrawer`, i geografici via `EntityFormDrawer` |
| **B. Entità/documento** | A più testata informativa, barra azioni di processo, schede, sotto-drawer | `PreventiviDrawer`, `DdtDrawer`, `ContrattoDrawer`, `PraticaDrawer` |
| **C. Sotto-entità di un padre** | lista delle sotto-entità con il form inline sotto (master-detail), «Chiudi» quando il form è chiuso | `ContattiSoggettoDrawer`, `ArticoloUomDrawer`, `NoteDrawer`, `ContrattoRigheDrawer` |
| **D. Consultazione** | si guarda, non si scrive: «Chiudi» e basta | `ErrorLogDettaglioDrawer`, `JobDettaglioDrawer`, `CodeLavoroDrawer` |
| **E. Non è un drawer laterale** | usa il componente `Drawer` per un'altra cosa | `AppLayout` (menu mobile, a sinistra), `FiltriLista` (filtri dal basso), `ListaColonneModal` e `DashboardWidgetModal` (si chiamano modal) |

⭐ **A, B, C e D sono lo stesso oggetto**: cambia il contenuto e cambia il
footer, non il chrome. **E non lo è**: posizione, testata e uscita sono
diverse per natura, e una sede di drawer laterale non le deve servire. Le E
sono **sedi a sé**, già in `core/` o da portarci.

Ci sono anche **BB-drawer** che sono già una sede per i propri consumatori:
`EntityFormDrawer` (6 usi), `GenericConfigDrawer`, `NoteDrawer` (3),
`SearchDrawer`. Montano `<Drawer>` direttamente perché la sede comune non c'è.
Il giorno in cui c'è, ci passano sopra come tutti.

## 3. Il chrome comune: cosa ripetono quasi tutti

Ogni drawer di forma A-D riscrive a mano gli stessi pezzi:

| Pezzo | Come si scrive oggi | Quanti (su 82) |
| --- | --- | --- |
| Testata | `<template #header><DrawerTitle :title :icon :action :modificato /></template>` | 77 |
| Larghezza | `:style="{ width: DRAWER_WIDTH.X }"` | 76 (gli altri §4 D-4) |
| Uscita | `@update:visible="suVisibile"`, con `suVisibile = gestoreVisibile(emit, chiudi)` | 62 |
| Conferma d'uscita | `useDrawerFormPreserve` → `modificato` + `chiudiConConferma` | 55 |
| Montaggio dopo l'animazione | `@after-show="onAfterShow"` + `v-if="contentReady"` (`useDrawerContentReady`) | 73 / 72 |
| Corpo | `<div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">` | 78 / 63 |
| Footer | `<FormFooter>` (Annulla/Salva, o `close-only`) | 72 |

⭐ Questa è la definizione operativa della sede: **tutto ciò che sta in questa
tabella è chrome**. Il resto (`DrawerEntityHeader`, `DrawerActionsBar`, le
schede, le liste) è **contenuto**, ed è già fatto di BB propri.

⚠️ `AppDrawer` oggi copre testata (senza icona), larghezza in px libera, uscita
e conferma, footer Annulla/Salva fisso. **Non copre**: l'icona, la scala
`DRAWER_WIDTH`, `contentReady`, `app-drawer-content`/`app-readonly`, il footer
«Chiudi», il footer assente. È per questo che nessuno lo usa.

## 4. Le divergenze trovate

Sono il motivo per cui le misure servono. Ognuna è una domanda, non una
correzione già decisa.

⚠️ Due numerazioni: i **D-n di questa sezione** sono le divergenze, quelli di
§7 le decisioni. Nel riquadro «Dove siamo» «D-1» e «D-3» sono quelli di §7.

⭐ **Dal 2026-10-03 D-2, D-3, D-4, D-5, D-6 e D-7 sono risolti NELLA SEDE**:
footer fisso, montaggio a fine animazione, larghezza dalla scala, readonly
applicato dal guscio, testata unica, default di PrimeVue non ripetuti. Restano
negli 80 drawer laterali finché non migrano, e si chiudono drawer per drawer con la
migrazione: non si correggono a parte.

### ✅ D-1. Uscite che saltano la conferma — corretto il 2026-10-03

18 drawer passano la X, l'ESC e il clic fuori con un `emit` scritto a mano
invece di `gestoreVisibile`. Per la maggior parte sono di forma D o non hanno
campi (`ErrorLogDettaglio`, `JobDettaglio`, `CodeLavoro`, `AccessoAltro`, i tre
`EmittenteFiscale*`, `WebAccessi`), e lì non si perde niente. Tre vanno
guardati:

- **`ContrattoRigheDrawer`** — 🔴 **candidato difetto**. Ha il form inline di
  una riga (`formMode` crea/modifica, 7 campi), e la X chiude con
  `emit('update:visible', val)` diretto: una riga compilata e non salvata si
  perde **senza conferma**. In più il form ha **Annulla/Salva scritti a mano**
  (righe ~1376-1377) invece di `FormFooter`, che la regola vieta («mai
  duplicare i pulsanti inline»). È il drawer che `useFormInline` lascia fuori
  «col suo lotto (L4)».
- **`FamigliaDocumentoDrawer`** — 10 campi, nessun `FormFooter`, nessun
  `gestoreVisibile`. Da verificare come salva e se una modifica può andare
  persa.
- **`DistintaDrawer`** — usa `useFormInline` ma non `gestoreVisibile`. Da
  verificare se il form inline aperto è protetto.

**Esito della verifica e della correzione (2026-10-03).** Tutti e tre i
sospetti erano lo stesso difetto:

| Drawer | Che cosa si perdeva | Correzione |
| --- | --- | --- |
| `ContrattoRigheDrawer` | la riga in compilazione (form inline) e i componenti BoM confermati nel dialog | fotografia di form + `componentiPayload`; X/ESC/clic fuori/Chiudi/Annulla da `chiudiConConferma`; Annulla/Salva scritti a mano → `FormFooter` |
| `FamigliaDocumentoDrawer` | una famiglia compilata o modificata (10 campi) | fotografia del form, anche in creazione; uscite da `chiudiConConferma`; pulsanti a mano → `FormFooter` (Salva nascosto in readonly come prima, più Ctrl+S) |
| `DistintaDrawer` | la riga contabile in compilazione nel form figlio `DistintaRigaForm` | il figlio tiene la fotografia (form **più** destinazione, confrontata per id: `RataSelect` riemette la rata come oggetto nuovo coi numeri uguali) e la espone; il drawer la legge con `unisciFotografie` |

In tutti e tre `DrawerTitle` riceve `modificato`. ⚠️ Non c'è un test di
componente per questi tre drawer: la macchina è quella di
`useDrawerFormPreserve`, già provata dalla sua spec, e qui si è cambiato il
cablaggio. Va visto a video (§8).

`DdtDrawer`, `OrdiniDrawer` e `PreventiviDrawer` hanno un gestore proprio
(`onVisibleChange`) che passa da `chiudiConConferma`: protetti, ma è una quarta
forma dello stesso gesto.

### 🟡 D-2. Il footer sta in due posti, con due comportamenti

- **65** drawer mettono `FormFooter` **nel corpo**: scorre col contenuto
  (`margin-top: auto` lo spinge in fondo solo se il contenuto è corto).
- **7** lo mettono nello **slot `#footer`** di PrimeVue: resta **fisso** in
  basso (`EmailAccountDrawer`, `EmailTemplateDrawer`, `TemplateAssetDrawer`,
  `TemplateDocumentoDrawer`, `AppDrawer`, e le due E).

Su un form lungo l'operatore trova il Salva in fondo alla pagina nel primo
caso, sempre a vista nel secondo. **La regola non è scritta da nessuna parte**:
la sede deve sceglierne uno, ed è una decisione di UX (§7, D-2).

### 🟡 D-3. Il montaggio dopo l'animazione manca in 8 drawer di forma A-D

`ContattiSoggettoDrawer`, `ContiBancariDrawer`, `TitoliIvaSoggettoDrawer`,
`ImpostazioniOverrideDrawer`, `WebAccessiDrawer`, `CommessaDrawer`, e i due
gusci `AppDrawer` ed `EntityFormDrawer` non usano `useDrawerContentReady`: il
rimbalzo all'apertura che il BB evita (regola in memoria
«feedback_content_ready_after_show»). Nella sede diventa automatico, e il
difetto sparisce per costruzione.

### 🟡 D-4. Larghezze fuori dalla scala

- `VersioneDrawer`: `const DRAWER_WIDTH_RIGHE_LISTINO = '1000px'`, un valore
  fuori da `DRAWER_WIDTH`. Il guard `check-drawer-width.mjs` non lo vede,
  perché controlla solo le chiavi `DRAWER_WIDTH.X` scritte.
- `OperatoreDrawer`: larghezza che cambia con la scheda (`XLARGE` sui permessi,
  `COMPLEX` altrove). È dentro la scala: la sede deve permetterlo.
- `AppDrawer` (`'640px'` di default) ed `EntityFormDrawer` (prop): px liberi.

⇒ Nella sede la larghezza è una **chiave** di `DRAWER_WIDTH`, non una
stringa CSS: un valore fuori scala smette di essere scrivibile.

### 🟡 D-5. Il readonly si applica in due modi

63 drawer mettono `app-readonly` sul corpo. 6 che dichiarano `readonly`
(`AccessoAltro`, `Distinta`, `Sistemazione`, `WebAccessi`, `CommessaGestione`,
`Lotto`) non lo fanno e **nascondono le azioni** invece. Per drawer fatti
soprattutto di azioni può essere giusto. La sede dovrebbe applicare
`app-readonly` da sola, leggendo il readonly iniettato; resta da decidere se
anche questi 6 lo prendono.

### 🟢 D-6. Testata senza `DrawerTitle`

`ErrorLogDettaglio`, `JobDettaglio` e `CodeLavoro` usano la prop `:header`
(testo semplice) invece di `DrawerTitle`: niente icona, niente badge readonly.
Nella sede la testata è una sola.

### 🟢 D-7. Attributi che ripetono i default

`:modal="true"` (9) e `:dismissable="true"` (33) sono già i default di
PrimeVue. `dismissable` come **espressione** ha invece un senso: `!loading` in
`ListaColonneModal`, `!hasChildOpen` in `VersioneDrawer` (non si chiude col
clic fuori mentre un figlio è aperto). La sede lo deve accettare.

### ✅ D-8. Cambiare riga con il form inline modificato non chiede conferma — fatto il 2026-10-03

Emerso il 2026-10-03 correggendo D-1. Nelle forme master-detail il clic su
un'altra riga riapre il form sulla riga nuova e sostituisce quello aperto:
le modifiche alla riga precedente si perdono senza domanda. Vale anche per i
drawer di riferimento (`ArticoloUomDrawer`: `apriRiga(row)` senza conferma),
quindi è una domanda del pattern, non di un drawer: la sede naturale è
`useFormInline` (`apriRiga`), che oggi non conosce la fotografia. Da decidere.

### 🟢 D-9. Il footer della forzatura in `DistintaRigaForm` è scritto a mano

Il form ha due tempi (Salva, poi «Forza» col motivo quando il server chiede
conferma), con `Tag` + tre pulsanti nel secondo tempo. Non è passato a
`FormFooter` con D-1 perché è un caso a due stati che `FormFooter` da solo non
rende; si guarda con la migrazione di `DistintaDrawer`.

## 5. La forma della sede (decisa e scritta il 2026-10-03)

`AppDrawer` riscritto, che copre la tabella di §3 e nient'altro
(`core/components/AppDrawer.vue`, contratto in `AppDrawer.spec.js`):

| Cosa | Proposta |
| --- | --- |
| Testata | `title`, `icon`, `action`, `modificato` → `DrawerTitle` (badge readonly incluso) |
| Larghezza | `width`: un **valore** di `DRAWER_WIDTH` (`:width="DRAWER_WIDTH.STANDARD"`), reattivo (caso `OperatoreDrawer`). ⚠️ Cambiato rispetto alla proposta («chiave in stringa»): il valore è la forma che 76 drawer scrivono già e che `check-drawer-width.mjs` controlla per chiave; il fuori-scala lo fermano il validatore della prop e il guard, esteso al valore scritto a mano sul tag |
| Uscita | `confermaUscita` (il `chiudiConConferma` di `useDrawerFormPreserve` o di `unisciFotografie`), default «esci e basta»; ogni uscita passa di lì (`gestoreVisibile` interno) |
| Chiudibile col clic fuori | `dismissable`, default `true` |
| Montaggio | `useDrawerContentReady` **interno**: il corpo si monta dopo l'animazione, sempre |
| Corpo | `app-drawer-content` + `app-readonly` dal readonly iniettato, interni |
| Footer | **fisso** (slot `#footer` di PrimeVue, D-2). `footer`: `'form'` (Annulla/Salva, emette `save`/`cancel`), `'chiudi'` (close-only), `'nessuno'`; più lo slot `#footer` per i casi veri (wizard, terzo bottone), che riceve `chiudi` |
| Readonly | dalla catena `READONLY_KEY`; la prop `readonly` la può solo stringere, e il guscio la ri-provide in OR (`FormFooter` e figli la vedono) |
| Contenuto | slot di default; `DrawerEntityHeader`, `DrawerActionsBar`, schede e liste restano del chiamante |

⛔ **Non entra**: niente schede, niente barra azioni, niente caricamento del
dettaglio. Sono BB di contenuto che esistono già, e una sede che li assorbisse
diventerebbe un drawer-di-tutto.

⚠️ Le forme C hanno **due footer** (il «Chiudi» del drawer, nascosto a form
aperto, e Annulla/Salva del form inline: 18 drawer ne hanno 2 o 3). La sede
gestisce il primo (`footer="chiudi"` con una condizione); il secondo è del
form inline, cioè di `useFormInline`.

## 6. Dopo la sede: lint e registro — ✅ fatto il 2026-10-03, senza registro

1. `primevue/drawer` entra in `IMPORT_PRIMEVUE_RISERVATI` con sede
   `AppDrawer.vue`. ⚠️ Le forme E sono **più sedi** (`AppLayout`,
   `FiltriLista`, …): la configurazione del lint oggi accetta una sede per
   import, e va estesa a un elenco.
2. Registro dei drawer grezzi, che può solo calare. ⚠️ È il **secondo**
   registro dello stesso tipo dopo `datatable.baseline.json`: si estrae il
   meccanismo in uno script con più registri, non si copia (regola del 2).
3. Migrazione a lotti per dominio, con il registro che scende a ogni giro.

## 7. Decisioni per Tid

✅ **Accolte tutte le proposte** (Tid, 2026-10-03): «direi di iniziare da D-1
poi procedi D-3».

| # | Domanda | Proposta (deciso così) |
| --- | --- | --- |
| **D-1** | `ContrattoRigheDrawer`: la X che perde la riga in modifica è un difetto da correggere subito, o entra nel lotto della migrazione? | Subito, è un difetto che non dà errore; e i pulsanti a mano diventano `FormFooter` |
| **D-2** | Footer fisso (slot `#footer`) o che scorre col contenuto? | **Fisso**: il Salva sempre a vista su un form lungo; il «Chiudi» delle forme C pure |
| **D-3** | La sede è `AppDrawer` riscritto, o un componente nuovo con `AppDrawer` ritirato? | `AppDrawer` riscritto: ha un solo consumatore, il nome è già quello giusto e fa da specchio ad `AppDialog` |
| **D-4** | I 6 drawer «ad azioni» (D-5) prendono anche `app-readonly`? | Sì, la sede lo mette sempre; nascondere le azioni resta in più |
| **D-5** | Le forme E (menu mobile, filtri, i due «modal») restano sedi a sé? | Sì; i due «modal» vanno guardati: se sono drawer laterali, passano alla sede |
| **D-6** | `EntityFormDrawer`, `GenericConfigDrawer`, `NoteDrawer`, `SearchDrawer` passano sopra la sede? | Sì, sono i primi del lotto: spostano molti consumatori in un colpo |
| **D-7** | Lo script del censimento entra in `frontend/scripts/`? | Sì, se diventa la base del registro (§6); altrimenti no |

## 8. Collaudo a video (D-1)

Per ognuno dei tre drawer: aprire, modificare un campo, poi uscire da **X**,
**ESC**, **clic fuori** e **Annulla** → deve comparire «Modifiche non
salvate»; senza modifiche si esce senza domanda; dopo il Salva si esce senza
domanda. La scritta dell'azione in testata diventa arancio mentre c'è una
modifica.

- `ContrattoRigheDrawer`: dal contratto, «Righe» → «Aggiungi articolo» o clic
  su una riga; anche un articolo composito con i componenti confermati e poi
  la X.
- `FamigliaDocumentoDrawer`: Amministrazione → famiglie di documento, sia
  «Nuova» sia una esistente.
- `DistintaDrawer`: una distinta manuale in bozza → «Nuova riga»; provare anche
  scegliendo solo la fattura (la destinazione conta come modifica).
- **Righe del listino**: con una riga semplice aperta e modificata, cliccare
  una riga di articolo **composito** → deve chiedere; dopo il sì si apre il
  dialog del kit e il form si chiude.
- **D-8 e D-13** (stessa prova, due gesti): su un DDT, un ordine, un preventivo,
  un reso e un documento interno in bozza, aprire una riga, cambiare un campo,
  poi (a) cliccare un'ALTRA riga e (b) uscire dal drawer con X/ESC: in entrambi
  i casi deve comparire «Modifiche non salvate»; senza modifiche, nessuna
  domanda. Stessa prova del cambio riga su UoM e distinta base di un articolo,
  note, eccezioni d'offerta, righe del listino, indirizzi, contatti, conti
  bancari e righe del contratto.

## 9. Migrazione — stato per lotto

### Lotto `core` (2026-10-03)

| File | Forma | Esito |
| --- | --- | --- |
| `EntityFormDrawer` | A, guscio dei 6 geografici | ✅ su `AppDrawer`: la sede si porta dietro anche i 6 consumatori |
| `GenericConfigDrawer` | A, metadata-driven | ✅ su `AppDrawer` |
| `NoteDrawer` | C, guscio dei drawer note di dominio | ✅ su `AppDrawer`, `:footer="formMode ? 'nessuno' : 'chiudi'"`; il «Chiudi» ora è fisso |
| `SearchDrawer` | D, ricerca universale | ✅ su `AppDrawer`. ⚠️ **Guadagna il footer «Chiudi»**: prima non ne aveva e si usciva solo dalla X (regola: ogni drawer che mostra una lista ha il «Chiudi») |
| `CodeLavoroDrawer` | D, code di lavoro | ✅ su `AppDrawer`. ⚠️ **La testata diventa `DrawerTitle`** con l'icona delle code: prima era la prop `header` di testo semplice (§4 D-6) |
| `ListaColonneModal` | A, con terzo pulsante | ✅ su `AppDrawer` (D-10): testata standard col conteggio delle colonne nuove e il suo tooltip, footer dallo slot (Ripristina + Annulla/Salva, l'Annulla con `chiudi` dello slot), `:dismissable="!loading"`. Guadagna l'indicatore «modificato» |
| `DashboardWidgetModal` | A, con terzo pulsante | ✅ su `AppDrawer` (D-10), come sopra col conteggio dei widget nuovi |
| `AppLayout`, `FiltriLista` | E | restano sedi a sé (§2) |

Cosa i cinque **non scrivono più**: `useDrawerContentReady`, `gestoreVisibile`,
`DrawerTitle`, la classe di corpo e il readonly sul corpo, il `FormFooter` del
drawer.

⚠️ **Un difetto del guard trovato strada facendo.** Togliendo `import Drawer`
da `NoteDrawer`, la finestra di 4 righe con cui `check-datatable-baseline.mjs`
cerca il motivo di una `DataTable` è arrivata al commento d'**intestazione** del
file, e il guard ha dato `NoteDrawer` per «motivato»: il registro calava per
caso. Ora la finestra si ferma alla prima riga vuota. Verificato prima di
cambiarlo: sui 31 file del registro il nuovo criterio dà esattamente gli
stessi 11 «senza motivazione» (un criterio più stretto, «il commento subito
sopra», ne avrebbe cambiati altri 11).

### ✅ D-10. La testata con un conteggio — fatto il 2026-10-03 (ok Tid)

`ListaColonneModal` e `DashboardWidgetModal` hanno la stessa testata scritta a
mano: un titolo e un `Badge` col numero di colonne o widget **nuovi** (con
tooltip nelle colonne). `DrawerTitle` non sa renderla, quindi `AppDrawer`
nemmeno. Sono due occorrenze dello stesso bisogno (regola del 2).

**Proposta**: `DrawerTitle` riceve `conteggio` (numero; nascosto a 0) e
`conteggioTooltip`, reso accanto al titolo; `AppDrawer` li passa. Il footer di
entrambi (Ripristina + Annulla/Salva) entra già dallo slot `#footer`, e
`dismissable="!loading"` è già una prop. Con la testata standard guadagnano
anche l'indicatore «modificato».

**Fatto**: `DrawerTitle` ha `conteggio` + `conteggioTooltip` (un `Badge` info
accanto al titolo, nascosto a 0), `AppDrawer` li passa, `AppDrawer.spec.js`
test 11. Le due testate scritte a mano e il loro CSS sono ritirati.

### Lotto `amministrazione` (2026-10-03)

Tutti e 18 su `AppDrawer`; in `amministrazione/` non resta nessun
`primevue/drawer`.

| Forma | Drawer |
| --- | --- |
| A, Annulla/Salva | `CategoriaCliente`, `CategoriaClienteListino`, `TipoRuoloTipoIndirizzo`, `UtilityTipoRuolo`, `EmittenteFiscale` (col sotto-drawer `SoggettoResolver` in fondo allo slot), `FamigliaDocumento`, `RegistroNumerazione`, `RepartoProfiloEditor`, `EmailAccount`, `EmailTemplate` |
| D, sola consultazione | `AccessoAltro`, `ErrorLogDettaglio`, `Processo` |
| lista o scheda dentro | `EmittenteFiscaleBillingAccount`, `EmittenteFiscaleRegistri`, `EmittenteFiscaleUtilities`, `OperatorePermessi` |
| con schede | `Operatore`: footer **secondo la scheda** (`'form'` sui Dati, `'chiudi'` sui Permessi, dove ogni sezione ha il suo Salva) e larghezza pure |

Gli eventi verso il padre restano quelli di prima: chi emetteva `cancelled`
all'uscita lo emette da `@cancel` di `AppDrawer`.

**Che cosa cambia a video** (da collaudare):

- **Footer fisso** dappertutto (D-2): in 14 drawer il pulsante stava nel corpo
  e scorreva col contenuto.
- **«Chiudi» standard al posto di un `Button` scritto a mano** nelle tre schede
  dell'emittente (billing account, registri, utilities); ⚠️ e ora anche la **X**
  emette `close` verso il padre, come il pulsante: un gesto solo.
- **«Chiudi» nuovo** in `OperatorePermessiDrawer`: prima si usciva solo dalla X.
- **Testata standard** in `ErrorLogDettaglioDrawer` (icona del log errori),
  prima la prop `header` di testo semplice (§4 D-6).
- ~~`app-readonly` applicato dal guscio anche in `AccessoAltro`, `Processo`,
  `ErrorLogDettaglio`~~ — superato lo stesso giorno: in quei tre il corpo resta
  cliccabile (`proteggiCorpo: false`, §9 «D-4 rivista»), come prima.

### Lotto `vendite` (2026-10-03)

Tutti e 18 su `AppDrawer`; in `vendite/` non resta nessun `primevue/drawer`.

| Forma | Drawer |
| --- | --- |
| A, Annulla/Salva | `CloneVersione`, `VersioneForm`, `Listino`, `PromoArticolo` |
| C, form inline | `ContrattoRighe`, `OffertaEccezioni`, `Versione` — `:footer="formMode ? 'nessuno' : 'chiudi'"` |
| D, consultazione / lista | `ContrattiBillingAccount`, `Commessa` (lineage), `CommessaGestione`, `Fattura`, `Lotto` |
| documento, footer secondo lo stato | `Contratto`, `Offerta`, `Reso`, `Ddt`, `Ordini`, `Preventivi` |

**Che cosa ha chiesto alla sede.** `AppDrawer` emette ora `after-show`
(test 12): `useDrawerAutosaveBozza` di DDT, ordini e preventivi non deve creare
la bozza mentre il drawer scorre, e per saperlo ascolta questo. In quei tre
l'uscita la possiede il BB della bozza (abbandono di una bozza vuota, poi le
modifiche), che emette da sé verso il padre: `:conferma-uscita="() => close()"`.

**Che cosa cambia a video** (da collaudare):

- **Footer fisso** dappertutto (D-2), compresi i documenti.
- **`VersioneDrawer` (righe del listino) passa da 1000px a `WIDE_PLUS`, 1100px**
  (§4 D-4): dal modello è il suo caso, master-detail con la sotto-tabella dei
  componenti BoM.
- **«Chiudi» nuovo** nel drawer della commessa del lineage (prima solo la X).
- **`FatturaDrawer` bloccato**: ora ha il «Chiudi» anche col pannello
  «accesso bloccato» (prima si usciva solo dalla X).
- **`Listino`**: niente più spinner durante l'animazione d'apertura; il corpo
  compare a fine animazione, come in tutti gli altri.
- **`CommessaGestioneDrawer`**: il dialog del registro di riga è montato in
  fondo al contenuto invece che nello slot della testata; si apre come prima,
  dal menu di una riga.

### ✅ D-11. Il footer dei documenti: quattro copie della stessa regola — fatto il 2026-10-03

Migrando i documenti è nata la stessa `computed` in **quattro** drawer
(`Reso`, `Ddt`, `Ordini`, `Preventivi`), identica salvo il nome di un flag:

```js
const footerDrawer = computed(() => {
  if (formRigaAperto.value) return 'nessuno'
  if (canEditTestataEffective.value && !isReadonly.value) return 'form'
  return hasDetail.value ? 'chiudi' : 'nessuno'
})
```

È una regola del modello dei documenti, non di un drawer: «Annulla/Salva
finché la testata si modifica, "Chiudi" quando il documento c'è ma non si
tocca, niente col form di una riga aperto». `Contratto` e `Offerta` ne hanno
una variante (lì il «si modifica» ha una regola di dominio propria).

**Proposta** (regola del 2): un BB `footerDocumento({ formRigaAperto,
modificabile, presente })` → `computed` col valore per `footer`, in
`core/composables/`, con una spec; i quattro ci passano sopra, e i due con la
variante gli passano il loro `modificabile`.

**Fatto** (ok Tid: «tutti e 6 stesso BB»): `core/composables/useFooterDocumento.js`
con `useFooterDocumento.spec.js` (6 test). Reso, DDT, ordine e preventivo gli
passano `formRigaAperto`; contratto e offerta, che le righe le gestiscono in
un drawer a parte, no. La regola di dominio del contratto in ATTIVO è rimasta
scritta accanto alla chiamata.

### Ultimi lotti (2026-10-03)

`anagrafiche` (10), `catalogo` (7), `magazzino` (6), `ui` (5), `config` (3),
`pagamenti` (2), `pratiche` (2), `portale` (1), `strumenti` (1): tutti su
`AppDrawer`. Fuori dalle tre sedi non resta nessun `primevue/drawer`.

Casi da notare:

- `ClienteDrawer` aspetta anche i suoi dati (`ready`): lo spinner sta ora
  dentro il corpo, il guscio aspetta l'animazione.
- `ContiBancariDrawer` e `FatturaDrawer` tengono il pannello «accesso bloccato»
  come primo elemento del corpo, il resto in `v-else`.
- `UomConversioniDrawer`: l'Annulla/Salva del form di **aggiunta** resta nel
  corpo (annulla l'aggiunta, non chiude il drawer); il «Chiudi» del drawer si
  nasconde mentre si aggiunge.
- `PraticaDrawer` usa `useFooterDocumento`: Annulla/Salva in creazione e sulla
  scheda Dati (prima stava dentro quei pannelli); **«Chiudi» nuovo** sulle altre
  cinque schede, che un footer non l'avevano.
- `FlussoDrawer`: i tre footer alternativi (esito, completamento di dominio,
  Chiudi) sono uno solo, con etichetta, abilitazione e Salva che seguono lo
  stato.
- `DocumentoInternoDrawer`: il Salva della testata è il footer del drawer,
  nascosto col form di una riga aperto.
- **«Chiudi» nuovo** anche in `SoggettoResolver` (emette `annullato`, che il
  padre già ascoltava) e `SistemazioneDrawer`; **testata standard** in
  `JobDettaglioDrawer` (prima la prop `header` di testo).
- ⚠️ Tre drawer di `ui` (`ListaColonnaPermesso`, `ListaPreset`,
  `ListaPresetColonne`) in sola lettura non avevano footer: ora mostrano
  «Chiudi».

### ⚠️ La sola lettura sul corpo: D-4 rivista (2026-10-03)

D-4 (§7) diceva «la sede mette sempre `app-readonly`». Migrando è emerso che
**non si può**: `app-readonly` è `pointer-events: none` su tutto salvo filtri,
paginazione, schede e `.app-escape`, e **`RowActionsMenu` non è
`.app-escape`**. Sul corpo intero, in sola lettura si spegnevano il kebab di
riga (il registro di `CommessaGestione`, «anche a commessa in readonly»), i
pulsanti di consultazione («Esegui ora» dei processi, «vai alla scheda» degli
accessi) e la personalizzazione di colonne e home, che un utente in sola
lettura deve poter fare.

I drawer che la classe non la mettevano **lo facevano apposta**: proteggono la
sola lettura nascondendo le azioni, non spegnendo il corpo. Da qui
`proteggiCorpo` (default `true`, test 13): spento — dal confronto con `HEAD`,
non a occhio — in `Processo`, `ErrorLogDettaglio`, `AccessoAltro`,
`SoggettoResolver`, `CodeLavoro`, `SearchDrawer`, `ListaColonneModal`,
`DashboardWidgetModal`, `Commessa` (lineage), `CommessaGestione`, `Lotto` (vendite),
`DocumentoInterno` (protegge il solo pannello della testata), `Distinta`,
`Sistemazione`, `WebAccessi`, `JobDettaglio`. Restano protetti i **form**, anche
dove la classe prima mancava (`CanaleIncasso`, `ListaColonna`,
`ListaDefinizione`): per un form è la protezione voluta.

### ✅ D-12. Il `dismissable-mask` che non ha mai funzionato — chiuso il 2026-10-03

I cinque drawer di `ui` avevano `:dismissable-mask="false"`. È una prop di
`Dialog`, non di `Drawer` (verificato su `primevue/drawer/index.d.ts`): non ha
mai avuto effetto, e il clic fuori **chiudeva** (con la conferma sulle
modifiche). La migrazione conserva il comportamento reale e lo annota sul tag.
**Deciso da Tid**: «uniformali agli altri, nessuna eccezione al momento». I
cinque si chiudono col clic fuori (con la conferma sulle modifiche) come tutti
i drawer; la nota sul tag è tolta.

### ✅ D-8 fatto (2026-10-03)

`useFormInline` ha l'opzione `confermaCambio(procedi)` — di solito il
`chiudiConConferma` della fotografia del form inline — e `apriRiga(riga, poi)`:
con un form già aperto prima si chiede, e il nuovo si apre (e `poi` lo
riempie) solo dopo il sì. ⛔ Il riempimento sta in `poi` e non dopo la
chiamata: scritto dopo, riempirebbe il form prima della risposta e butterebbe
le modifiche comunque. Test 7 e 8 di `useFormInline.spec.js`.

Agganciato in `ArticoloUom`, `ArticoloBom` (dove la conferma era scritta a mano:
ora è del BB), `OffertaEccezioni`, `Versione`, `IndirizziSoggetto`, `Note`,
`Distinta`, e `useSoggettoRuoloCollection` (contatti, conti bancari). In
`ContrattoRighe`, che il BB non lo usa ancora (L4), la stessa conferma sul clic
di riga e su «Aggiungi articolo».

⚠️ **Rilievo di Tid in collaudo (2026-10-03, listino `sadasdfa`).** Nelle
righe del listino il clic su un articolo **composito** non chiedeva: il
composito non passa da `apriRiga` (non ha un form inline, i suoi prezzi si
danno nel dialog del kit), e il dialog si apriva lasciando sotto il form della
riga precedente con le modifiche in sospeso. Corretto in `VersioneDrawer`: con
un form aperto prima si chiede, e dopo il sì il form si chiude e si apre il
dialog. Verificati gli altri: DDT, ordini, preventivi e resi aprono ogni riga
(composite comprese) con `apriRiga`, e il dialog dei componenti lì sta DENTRO
il form della stessa riga; negli altri drawer di D-8 nessun clic scavalca
`apriRiga`.

### ✅ D-13. I form di riga dei documenti non hanno una fotografia — fatto il 2026-10-03

Emerso facendo D-8. `DdtRigaForm`, `OrdiniRigaForm`, `PreventiviRigaForm`,
`ResoRigaForm` e `DocumentoInternoRigaForm` **non tengono la fotografia** del
form: la fotografia del drawer copre la sola testata. Una riga in
compilazione si perde **senza domanda** cambiando riga, e anche uscendo dal
drawer (X, ESC, clic fuori). È la famiglia di D-1, su cinque documenti.
Senza fotografia non si sa se il form è modificato, quindi D-8 lì non si può
agganciare. Stessa mancanza in `DefinizioneEditorView` e `useEditableCollection`.

Come sono montati: i quattro di vendita stanno nello slot `#form` di
`RigheMasterDetailTable`, dentro la tabella-righe del documento
(`DdtRigheTable`, `OrdiniRigheTable`, …), dentro il drawer; quello di magazzino
è montato dal drawer stesso. Ordini e preventivi condividono già il cuore della
riga (`useRigaArticoloComposito`, B11).

**Proposta** (la forma è una scelta, quindi prima dell'estrazione):

1. ogni form di riga tiene la sua fotografia ed espone `modificato` e
   `chiudiConConferma`, come già fa `DistintaRigaForm`; dove c'è il cuore
   comune (B11) la fotografia sta lì, una volta;
2. `RigheMasterDetailTable` riceve `confermaCambio` e lo passa a
   `useFormInline` (D-8), ed espone la fotografia del form aperto;
3. il drawer unisce testata e righe con `unisciFotografie`, così anche X/ESC
   chiedono.

**Fatto** (Tid: «procedi»):

- `useRigaArticoloComposito` tiene la fotografia per DDT, ordini e preventivi
  (form più componenti BoM confermati); `ResoRigaForm` e
  `DocumentoInternoRigaForm` la tengono da sé. Tutti e cinque la fissano a riga
  caricata (`nextTick`, dopo il giro di watch), la espongono, e il loro Annulla
  chiede. `ResoRigaForm` passa anche a `FormFooter` (i due pulsanti erano scritti
  a mano).
- `RigheMasterDetailTable`: `registra` nello scope dello slot, `confermaCambio`
  a `useFormInline`, `modificato`/`chiudiConConferma` esposti.
- Le quattro tabelle-righe inoltrano la fotografia; i drawer di DDT, ordini,
  preventivi, resi e documenti interni la uniscono alla testata: indicatore
  «modificato», X, ESC, clic fuori, «Chiudi», e la domanda sulla bozza di DDT,
  ordini e preventivi (`confermaUscita` del BB della bozza).
- ⚠️ Nessun test di componente copre il cablaggio (slot → tabella → drawer):
  le macchine sono `useDrawerFormPreserve`, `unisciFotografie` e
  `useFormInline`, già provate. Va visto a video (§8).

⏳ **Residuo dichiarato**: l'editor dei workflow (`DefinizioneEditorView`, e
`useEditableCollection` sotto i pannelli di passi e archi) ha la stessa
mancanza. Non è un drawer documento e i suoi form sono componenti propri: un
giro a sé, da decidere.

### ✅ D-14. I dialog con campi si chiudevano senza chiedere — fatto il 2026-10-03

Rilievo di Tid in collaudo: nel dialog dei componenti BoM, modificati i prezzi
e uscendo, nessuna domanda. Il difetto era nella sede: `AppDialog`, a
differenza di `AppDrawer`, non aveva conferma d'uscita. Censimento: 54
`AppDialog`, 11 di solo messaggio o conferma, **44 con campi** (43 con
componenti di input e `DocumentoEmissioneDialog` con il campo file degli
allegati) — nessuno chiedeva.

- `AppDialog`: `confermaUscita(chiudi)` su X, ESC, maschera, Annulla e sul
  `chiudi` dello slot `#footer` (`AppDialog.spec.js`, 5 test, per mutazione).
- `useFotografiaDialog` (BB nuovo, 4 test): lo stato come getter, la
  fotografia all'apertura; `fissaAllApertura: false` + `fissa()` per chi carica
  dati aprendosi (`ChiudiVersione`, `NumerazioneData`, `EmittenteAttivo`,
  `ApriDistinta`, `ComponentiDialog`, i tre dialog su `useRigheSelezioneQta`,
  lo smistamento).
- **42 dialog** con la fotografia; **2 dichiarati senza dati** con il motivo
  (`InventarioPianoDialog`: una ricerca; `TestResolverDialog`: parametri di
  prova); `RatePickerDialog` aveva già la sua conferma (rate in area), ora è la
  sua `conferma-uscita` invece di un aggancio a `update:visible`.
- **Footer personalizzati**: `ChiudiVersione`, `ApplicaVariazione` e
  `ResoRiconsegna` uscivano con un `emit` diretto, saltando la conferma; ora con
  il `chiudi` dello slot.
- **Guard** `check-dialog-chrome.mjs`, regola 6: un `AppDialog` con campi
  passa `conferma-uscita`, o dichiara `<!-- conferma-uscita: nessuna — motivo -->`.
  ⚠️ Corretto anche un difetto del guard: lo spoglio dei commenti `//` usava
  `^\s*`, che con il flag `m` mangiava le righe vuote — i numeri di riga dei
  messaggi erano sbagliati.

⚠️ Interruzione del 2026-10-03: uno stash fatto da un'altra sessione per un
rebase ha portato via il lavoro tracciato a metà di D-14; ripristinato con
`git stash apply` (147 file su 148 identici allo stash, il 148° —
`PROJECT_CONTEXT` — fuso col commit DB), poi D-14 ripreso.

**Collaudo D-14**: per ognuno, aprire, cambiare un campo, uscire con X / ESC /
Annulla → «Modifiche non salvate»; senza toccare niente → nessuna domanda.
Da provare almeno: componenti BoM (riga composita di un preventivo/ordine in
creazione), apertura distinta, abbina riga, reso da DDT (selezione e
quantità), evasione ordine, smistamento preventivo, chiusura/attivazione
versione di listino, cessazione contratto, sospensione pratica, emissione
documento con un allegato scelto e non ancora inviato, indirizzo libero del
documento.

