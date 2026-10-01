# Analisi — Le regole di frontend-standards che il codice non rispetta

> **Tipo**: analisi · **Data**: 2026-09-26 · **Owner**: Tid ·
> **Stato**: ✅ **CHIUSA** il 2026-09-26 — tutte le voci decise da Tid e applicate. Il
> solo residuo (R-3, circa 60 `var(--p-*)` senza un significato ancora nominato)
> è passato in `.codex/PROJECT_CONTEXT.md` § «Aperto — Media priorità»
>
> **Origine**: riallineamento delle guide sviluppatori del 2026-09-26
> ([frontend-standards](../frontend/frontend-standards.md),
> [catalogo BB frontend](../frontend/catalogo-building-block-frontend.md)). Le
> guide sono state corrette dove descrivevano male il codice. Qui restano i
> casi **opposti**: la regola è scritta chiara, e il codice non la segue.

---

## Perché è un documento a parte

Una regola violata in modo esteso si può chiudere in due modi, e la guida non
può scegliere da sola:

* **è sbagliato il codice** → si porta a norma (o si decide un presidio che
  impedisca di peggiorare);
* **è sbagliata la regola** → si riscrive la regola, dichiarando le eccezioni
  vere.

⛔ Il criterio non è il numero di violazioni. Molte violazioni non fanno una
regola sbagliata, e una sola non ne fa una giusta: si decide sul **modello**
(isolamento dei domini, tema unico, un solo client HTTP…). I conteggi sotto sono
**fatti datati**, misurati col `grep` il 2026-09-26 sul branch allineato a
`Tito-dev` (`6989d35df`), e servono solo a trovare i casi.

## Le voci

| # | Regola (sezione di frontend-standards) | Stato al 2026-09-26 | Esempi | Da decidere |
| --- | --- | --- | --- | --- |
| R-1 | I componenti di dominio **non importano da altri domini** | ✅ **Chiusa 2026-09-26 — regola riscritta** (decisione Tid). La regola nuova è il verso delle FK: un dominio importa un'entità che le sue tabelle referenziano; il verso opposto passa da un **punto di estensione**; i motori (`pratiche`, `documenti`) non nominano i domini. Il codice è a norma: `catalogo`→`magazzino`, `anagrafiche`→`vendite`/`portale`, `vendite`→`pagamenti` e `pratiche`→`vendite` sono diventati iscrizioni. Presidio: `check-confini-domini.mjs` | frontend-standards §«Confini fra domini» | — |
| R-2 | `core/` **non importa da un dominio** | ✅ **Chiusa 2026-09-26 — codice**, e l'eccezione dei geografici non serve più. 35 BB di soggetto, indirizzi e geografia sono tornati in `anagrafiche`; `ArticoloLookup`/`useArticoloUomOptions` in `catalogo`, `FatturaLookup` in `vendite`, `SaldoPanel`/`useSaldi` in `pagamenti`. Il registro «tipo → drawer» è passato in `core/drawerEntita.js` e i domini si iscrivono; la lookup degli emittenti e la testata dei presidi stanno in `core/api`. Oggi `core` non importa nessun dominio | — | — |
| R-3 | Mai `var(--p-*)` nei componenti: si passa dai token `--app-*` | 🟡 **In gran parte chiusa 2026-09-26.** Sostituzione meccanica dove il token esisteva; l'arancio «attenzione» va su `--app-warning-color` (decisione Tid: attenzione = arancio). Tre token nuovi per significato: `--app-accent-color`, `--app-fonte-soggetto-color`, `--app-split-color`. Da 191 a circa 60 occorrenze. **Restano** quelle senza un significato ancora nominato (`primary-700/500/50`, `yellow-*`, `blue-*`, `surface-200/400`, `border-radius-sm`…) | — | Dare un nome ai residui, poi un guard |
| R-4 | Divieto esplicito di `--p-surface-700` | ✅ **Chiusa 2026-09-26 — codice.** Le occorrenze erano 4, non 3: c'era anche `PraticaAllegatiTab.vue`. Erano quattro copie della stessa regola, e una stava già nel BB `GiornaleEventi`. Estratta la classe `app-voce-registro` in `main.css`, con il token `--app-voce-registro-bg` che ha un valore per ciascun tema; le quattro copie sono ritirate | `PraticaSospensioniTab.vue`, `PraticaNoteTab.vue`, `PraticaAllegatiTab.vue`, `GiornaleEventi.vue` | — |
| R-5 | Nessun `@media` nei componenti scoped | ✅ **Chiusa 2026-09-26 — regola riscritta, strada B** (decisione Tid). `@media` ammessa anche nel componente, ma solo con le soglie di `BREAKPOINTS` in forma canonica (presidio `check-media-soglie.mjs`). Le soglie che dipendono dal riquadro (479/560/900px) sono diventate `@container` sul contenuto di drawer e `AppDialog` (`app-riquadro`). Corrette le soglie `1024px`/`768px` che divergevano sul confine | — | — |
| R-6 | `useReadonlyMode` con il dominio dalle costanti, mai con una stringa | ✅ **Chiusa 2026-09-26 — codice.** Aggiunto `READONLY_DOMAINS.PAGAMENTI`; le 5 view lo usano | le 5 view di `pagamenti/views/` | — |
| R-7 | Mai `api.get/post` nei componenti | ✅ **Chiusa 2026-09-26 — codice**, e corretta la contraddizione della guida. Nuovi moduli `core/api/` (password, sessioni, configTables, ricerca) e azione `auth.cambiaPassword`; la revoca delle sessioni ora mostra il messaggio del backend invece di un errore generico. Presidio: `check-api-componenti.mjs` | — | — |
| R-8 | Le classi PrimeFlex non esistono nel progetto | ✅ **Chiusa 2026-09-26 — falso positivo.** Le due righe trovate sono commenti che dicono *«Niente `class="w-full"`»*: il codice rispetta la regola | `ApriDistintaDialog.vue`, `ApriDocumentoInternoDialog.vue` | — |
| R-9 | Mai `window.location`: si naviga col router | ✅ **Chiusa 2026-09-26 — regola.** Non è un redirect, è un ripartire dal boot. L'eccezione è scritta in frontend-standards §Regole di sicurezza, con una sola sede ammessa: `cambiaEmittenteAttivo` | `stores/auth.js` | — |
| R-10 | Il glifo dell'euro resta solo su «Fattura» | ✅ **Chiusa 2026-09-26 — codice, e regola precisata** (decisione Tid, strada A). La regola vale dentro la famiglia documento: l'euro su listini e approvazioni prezzo significa «prezzo» su basi proprie, ed è corretto. Il difetto vero era la base della Fattura, la ricevuta `\ea06` condivisa con Clienti: ora è il foglio `\e958` come gli altri documenti. Corretto anche il commento stantio su `app-nav-icon-approvazioni-prezzo` | `main.css` | — |

| R-11 | Il producer di un evento cross-tab sta **sempre nello store**, mai nel componente | ✅ **Chiusa 2026-09-26 — codice, e regola completata.** Nascono i verbi `generaDdt` (store ordini) e `generaOrdine` (store preventivi), che avvisano **le due** entità; dialog e drawer non emettono più. La guida ora dice chi avvisa l'entità che nasce da un verbo. Test: `ordini.spec.js` e `preventivi.spec.js`, provati per mutazione | `OrdineEvasioneDialog.vue`, `PreventiviDrawer.vue` | — |

## Cosa non è in questa lista

* i difetti delle guide (esempi sbagliati, nomi ritirati, contraddizioni):
  corretti direttamente nelle guide il 2026-09-26;
* ✅ **file senza consumatori — ritirati il 2026-09-26** (decisione Tid). Censiti
  risolvendo ogni import di `src/`, anche dinamico, fino a punto fisso: i sei BB
  `ReloadButton`, `PaginationInfo`, `AppToolbar`, `useLoading`,
  `useDirtyState`, `useTabLabel`; la copia `usePreventivoRigaComponenti`,
  sopravvissuta all'estrazione di `useRigaComponenti`; `portaleAuth.js` e
  `shopAuth.js`, superati da `core/api/attivazioneVeste.js`; `GeneraPdfButton`
  e, a cascata, `SceltaTemplateDocumentoDialog` e `templateDocumentiLookup.js`;
  `MieAttivitaPanel`; `ContrattoUtilityDrawer`. Con loro sono uscite le 17
  chiavi i18n che leggevano solo loro, la classe morta `app-edit-btn` con i
  token `--app-btn-edit-*`, e `--app-toolbar-tab-active-*`;
* il commento di `main.css` sulle voci `app-menu-item-action` dice ancora
  «verde»: il colore è blu dal 2026-08-27 (la guida è già corretta).
* i commenti di `AppDialog.vue` ed `EmittenteAttivoDialog.vue` dicono «l'unico
  override» del chrome: ce n'è un secondo, `AttivaVersioneDialog.vue` (il
  catalogo è già corretto).

## Registro

| Data | Cosa |
| --- | --- |
| 2026-09-26 | Censimento iniziale, undici voci, nessuna decisione presa |
| 2026-09-26 | Ritirati i 14 file senza consumatori e i loro residui (i18n, CSS). `npm run verify` verde |
| 2026-09-26 | Chiuse le voci meccaniche R-4, R-6, R-8, R-9, R-11 (decisione Tid). `npm run verify` verde: 39 file di test, 364 test. Restano da decidere R-1/R-2, R-3, R-5, R-7, R-10 |
| 2026-09-26 | Decisioni di Tid su R-1/R-2 (verso delle FK, iscrizioni in `core`, BB nel dominio dell'entità), R-3, R-5 (strada B), R-7: applicate. `npm run verify` verde: 41 file di test, 370 test, tre guard nuovi. Resta aperta R-10 (base dell'icona Fattura) e il residuo di R-3 |
| 2026-09-26 | R-10 chiusa (strada A): la Fattura prende la base documento. Resta il residuo di R-3 |
| 2026-09-26 | Analisi chiusa e spostata in `work-done/`; il residuo di R-3 è in PROJECT_CONTEXT § «Aperto». Guide riallineate: frontend-standards (confini fra domini, responsive, API nei componenti, producer cross-tab, sola lettura, enum), catalogo BB frontend (BB spostati nei domini, registri ed estensioni, moduli `core/api`, token e classi nuove) |
