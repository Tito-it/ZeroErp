# Analisi — Le regole di frontend-standards che il codice non rispetta

> **Tipo**: analisi · **Data**: 2026-09-26 · **Owner**: Tid ·
> **Stato**: 🔴 **DA DECIDERE**, voce per voce
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
| R-1 | I componenti di dominio **non importano da altri domini** | 26 file; quasi tutti in `vendite/` (verso `documenti/`, `anagrafiche/`, `catalogo/`…) | `vendite/preventivi/components/PreventiviDrawer.vue`, `anagrafiche/views/ClientiView.vue`, `catalogo/components/ArticoloDrawer.vue` | Regola o codice? Se `vendite` → `documenti` è una dipendenza voluta (la stampa è un servizio), va dichiarata come eccezione con la direzione ammessa |
| R-2 | `core/` **non importa da un dominio** (unica eccezione dichiarata: i componenti geografici) | 30 file, di cui 23 fuori dai geografici | `core/bersagli.js`, `core/components/SoggettoForm.vue`, `core/components/ContoBancarioForm.vue`, `core/composables/usePresidiPolling.js` | Sono BB finiti in `core/` senza esserlo, o `core/` ha bisogno di un meccanismo di registrazione (il dominio si iscrive, `core/` non lo nomina)? |
| R-3 | Mai `var(--p-*)` nei componenti: si passa dai token `--app-*` | 162 occorrenze dirette in 48 `.vue` (esclusi i fallback dentro un `var(--app-*, …)`) | `PresidioChip.vue`, `PraticaPercorso.vue`, `IndirizziSoggettoDrawer.vue` | Codice da portare a norma, o token `--app-*` che mancano? Un `--p-*` usato ovunque per la stessa cosa è un token non ancora nato |
| R-4 | Divieto esplicito di `--p-surface-700` | 4 occorrenze | `PraticaSospensioniTab.vue`, `PraticaNoteTab.vue`, `GiornaleEventi.vue` | Probabilmente codice: la regola ha un motivo scritto |
| R-5 | Nessun `@media` nei componenti scoped: il responsive sta in `main.css` | 13 `.vue` | `AppLayout.vue`, `DrawerActionsBar.vue`, `PraticheHome.vue` | Alcuni sono `core/` strutturali (layout, topbar): eccezione da dichiarare, o spostamento in `main.css`? |
| R-6 | `useReadonlyMode` con il dominio dalle costanti, mai con una stringa | 5 chiamate `useReadonlyMode('pagamenti')`; `READONLY_DOMAINS` non ha una voce `PAGAMENTI` | `pagamenti/views/EccedenzeView.vue`, `DistinteListView.vue`, `CanaliIncassoView.vue`, `CodaRigheView.vue`, `RateFuoriCapienzaView.vue` | Codice: manca la costante. Correzione piccola e meccanica |
| R-7 | Mai `api.get/post` nei componenti: si passa da uno store o da un modulo `api` | 15 chiamate in 7 `.vue`, tutti in `core/` | `ChangePasswordView.vue`, `ConfigTablePanel.vue`, `GenericConfigDrawer.vue`, `SearchDrawer.vue` | Codice, probabilmente: sono componenti nati prima della regola |
| R-8 | Le classi PrimeFlex non esistono nel progetto | 2 `class="w-full"` | `ApriDistintaDialog.vue`, `ApriDocumentoInternoDialog.vue` | Codice: la classe non fa niente, è un residuo |
| R-9 | Mai `window.location`: si naviga col router | 1: `stores/auth.js`, `cambiaEmittenteAttivo` | — | **Regola**, probabilmente: il commento in `auth.js` spiega perché il ricaricamento completo è voluto (cambiare emittente deve svuotare cache, KeepAlive e store). Va scritta come eccezione dichiarata |
| R-10 | Il glifo dell'euro resta solo su «Fattura» | `main.css`: `\e9bd` anche in `.app-nav-icon-listini::after`, sovrapposto all'icona base | — | La regola parla dell'icona intera o del glifo? Un'icona composta «listino + euro» può essere voluta |

| R-11 | Il producer di un evento cross-tab sta **sempre nello store**, mai nel componente | 2 componenti emettono da sé con `useTabEvents().emitDataChanged` | `vendite/preventivi/components/PreventiviDrawer.vue`, `OrdineEvasioneDialog.vue` | Codice, probabilmente: l'emissione nel componente si perde se la stessa scrittura parte da un'altra superficie |

## Cosa non è in questa lista

* i difetti delle guide (esempi sbagliati, nomi ritirati, contraddizioni):
  corretti direttamente nelle guide il 2026-09-26;
* **building block senza consumatori** — `ReloadButton`, `PaginationInfo`,
  `AppToolbar`, `useLoading`, `useDirtyState`, `useTabLabel`: non violano una
  regola, ma nessun file li importa. Candidati al ritiro, da decidere a parte;
  frontend-standards li segna «senza consumatori»;
* il commento di `main.css` sulle voci `app-menu-item-action` dice ancora
  «verde»: il colore è blu dal 2026-08-27 (la guida è già corretta).
* i commenti di `AppDialog.vue` ed `EmittenteAttivoDialog.vue` dicono «l'unico
  override» del chrome: ce n'è un secondo, `AttivaVersioneDialog.vue` (il
  catalogo è già corretto).

## Registro

| Data | Cosa |
| --- | --- |
| 2026-09-26 | Censimento iniziale, undici voci, nessuna decisione presa |
