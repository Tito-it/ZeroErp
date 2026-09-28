# Brief DB — Le righe di un documento diventano liste standard

> **Destinatari:** team DB (`dev/db-tid`) per il §3; il lavoro BE e FE (§4-§6)
> è di `dev/backend-tid`. Il lotto **L1** parte subito (usa liste già a
> catalogo); **L2-L4 partono solo a seed applicati**.
>
> **Tipo:** seed (`ui.lista_definizione` + `ui.lista_colonna` +
> `ui.lista_preset`/`lista_preset_colonna`). Nessun DDL.
> ⚠️ **Smentito dalla verifica del 2026-09-28 (§8.3-§8.5)**: fattura, contratto
> e BoM chiedono DDL (chiave di riga, grana, vista stantìa).
>
> **Decisione:** di Tid, 2026-09-27. Rilievo in-app su tablet e smartphone: la
> tabella delle righe del preventivo, come quelle di ordini e DDT, mostra
> uno **scroll orizzontale** che su touch non funziona. Tid ha scelto la
> proposta completa: le righe di un documento diventano `<ListaConfigurabile>`,
> con colonne dal catalogo, ritiro nella riga espandibile e personalizzazione.
> **Distinta base (BoM) compresa**, sullo stesso building block se può
> usarlo, e comunque su `ListaConfigurabile`.
>
> **Stato (2026-09-27):** brief scritto e rivisto con Tid lo stesso giorno:
>
> - ✅ **priorità delle colonne §3.2 approvate** da Tid così come sono;
> - ✅ **contratto nello STESSO brief** (Tid): riga 7, lotto L4, §7; il
>   2026-09-28 decise anche le colonne calcolate (dall'endpoint righe) e le
>   priorità della lista 7;
> - ✅ **L1 chiuso il 2026-09-28** (`dev/backend-tid`, commit `a5bed4f2a`, PR #1723 in `Tito-dev`; via
>   di Tid): la macchina del master-detail è il BB `useRigheMasterDetail`
>   (dal giorno stesso **`useFormInline`**, vedi sotto),
>   usato da `RigheMasterDetailTable`, `DistintaDrawer` e
>   `DocumentoInternoDrawer`. ⚠️ **In forma diversa da quella scritta qui
>   sotto**: vedi §5 L1, «Com'è andato». Seed e L2-L4 restano fermi sulle
>   decisioni del §8.9;
> - ✅ **verifica critica di L1 (2026-09-28)**: la stessa macchina esisteva già
>   in due BB di dominio e in sette drawer. **Unificata lo stesso giorno** (ok
>   Tid, nome scelto dall'agente): il BB si chiama ora **`useFormInline`**, ed
>   è la sede unica. Fuori, col loro lotto, `ContrattoRigheDrawer` (L4) e la
>   BoM (L3). §5 L1, «Verifica critica»;
> - 🔍 **verifica critica della parte DB il 2026-09-28: §8, da leggere per
>   primo.** Smentisce «Nessun DDL» (fattura, contratto, BoM) e l'ordine
>   «seed prima, BE dopo» (arma quattro presidi in CI);
> - ✅ **le sette decisioni di §8.9 sono PRESE da Tid lo stesso giorno**; il
>   lavoro DB che ne esce, in ordine, è in **§8.10**;
> - ✅ **Blocco 1 DB MIGRATO il 2026-09-28, pgTAP verdi** (esito di Tid):
>   dodici changeSet `20260928-16 → -27`, il seed delle liste 1-4 e 6, due
>   pgTAP. Resoconto, prove e richieste al BE in **§8.11**;
> - ✅ **Blocco 2 (fattura) MIGRATO il 2026-09-28, pgTAP verdi, nessuna
>   regressione** (esito di Tid): changeSet `20260928-28`, seed della lista
>   102, un pgTAP. Resoconto in **§8.12**;
> - ✅ **Blocco 3 (contratto) MIGRATO il 2026-09-28, pgTAP verdi** (esito di
>   Tid): changeSet `20260928-29`, `-31`, `-32`, seed della lista 103, un pgTAP
>   nuovo e il rubinetto aggiornato. Resoconto in **§8.13**;
> - 📋 **Cosa resta, in un posto solo: §8.14.** Due decisioni di Tid del
>   2026-09-28: la **versione del listino in vigore** si sistema **prima di
>   chiudere** il brief; le **chiavi i18n** si fanno **alla fine**;
> - ✅ **versione del listino in vigore, 15 righe nei drawer, data richiesta
>   sull'ordine: MIGRATI il 2026-09-28 sera, pgTAP verdi** (§8.15);
> - ✅ **costo della vista righe fattura MIGRATO, nessuna regressione** (§8.16);
>   **documentazione manuale scritta** (§8.17); **chiavi i18n fatte**,
>   `check_i18n_keys` tutto pulito (§8.14.2);
> - 🏁 **PARTE DB CHIUSA il 2026-09-28 sera.** Restano due passi di Tid —
>   migrare la riga di seed delle etichette UoM (liste 97-99) e **rigenerare la
>   doc auto-gen** (le 7 pagine nuove agganciano la loro scheda `manual/`) — e
>   il lavoro **BE/FE** dei lotti L2-L4 (§8.14.3-4). Il brief resta in
>   `work-in-progress/` finché BE e FE non chiudono.

---

## 1. Perché

`frontend-standards` §«Regola zero della lista» ammette la `DataTable` grezza
per le **righe di un documento** (`RigheMasterDetailTable`). Quella tabella
però non ha il ritiro dinamico delle colonne: rende 9-11 colonne a larghezza
`max-content` dentro un drawer, e sotto una certa larghezza l'unica via è lo
scroll orizzontale, che su touch non si usa.

⭐ **Il motivo sta nel modello, non nel dispositivo.** Un documento ha un
numero **arbitrario** di righe, ognuna con molti attributi. È la stessa natura
di qualsiasi lista: ha bisogno di colonne dal catalogo, di priorità di ritiro,
di paginazione lato server e di export. Il tablet ha solo reso visibile la
mancanza.

⭐ **Due precedenti hanno già fatto questo passo**, e ognuno dichiara lo
stesso debito:

| Drawer | Lista | Debito dichiarato nel file |
| --- | --- | --- |
| `DistintaDrawer` | `pagamenti.distinta_righe` (69) | la macchina «form sotto la lista» (`formMode`) è riscritta qui invece di passare da `RigheMasterDetailTable` |
| `DocumentoInternoDrawer` | `magazzino.inventario_righe` (71), `magazzino.rettifica_righe` (74) | idem |

⇒ Oggi quella macchina esiste in **tre copie**. La regola del 2 chiede
l'estrazione in ogni caso; questo brief la fa coincidere con la conversione.

⛔ **L'eccezione «righe di un documento» esce dalla regola zero**
(`frontend-standards`, catalogo BB, piano PrimeVue 5 §Gruppo B). Restano
ammessi solo il dettaglio espanso della ricerca, la matrice slot/override e
l'anteprima o la selezione dentro un dialog.

## 2. Perimetro

| # | Codice proposto | Tabella di oggi (sotto `frontend/src/`) | Righe da, oggi |
| --- | --- | --- | --- |
| 1 | `vendite.preventivo_righe` | `vendite/preventivi/components/PreventiviRigheTable.vue` | `GET preventivi/<id>/righe/`, lista intera |
| 2 | `vendite.ordine_righe` | `vendite/ordini/components/OrdiniRigheTable.vue` | `GET ordini/<id>/righe/`, lista intera |
| 3 | `vendite.ddt_righe` | `vendite/ddt/components/DdtRigheTable.vue` | `GET ddt/<id>/righe/`, lista intera |
| 4 | `vendite.reso_righe` | `vendite/resi/components/ResoRigheTable.vue` | `GET resi/<id>/righe/` (`vw_resi_righe_dettaglio`), lista intera |
| 5 | `vendite.fattura_righe` | `vendite/components/FatturaDrawer.vue` (sezione righe) | `dettaglio.righe`: **nessun endpoint proprio** |
| 6 | `catalogo.articolo_componenti` | `catalogo/components/ArticoloBomDrawer.vue` | `listArticoloComponenti`, filtri locali (validità, testo) |
| 7 | `vendite.contratto_righe` | `vendite/components/ContrattoRigheDrawer.vue` | `righeIniziali` dal dettaglio del padre + anteprima `/righe-preview/`: vedi §7 |

⚠️ **Il codice è una proposta**, sulla convenzione delle liste righe già a
catalogo (`<schema>.<documento al singolare>_righe`, come
`magazzino.inventario_righe`). Se il catalogo ha una convenzione più precisa,
vince il catalogo; il codice scelto va riportato qui, perché è quello che il FE
scrive.

**Fuori perimetro, e perché:** `DdtResoDialog`, `OrdineEvasioneDialog` e
`ResoRiconsegnaDialog` sono **selezioni con quantità dentro un dialog**
(l'operatore sceglie cosa evadere o rendere), non elenchi. Restano l'eccezione
«dialog», col motivo già scritto sopra l'import.

## 3. Richiesta al team DB — i seed

### 3.1 Le definizioni

Come le liste righe già a catalogo (37, 69, 71, 74):

- `vista_sql` NULL: le righe le legge il repository;
- `perimetro_emittente = t`, `multi_emittente = f` per 1-5 e 7: il documento
  appartiene a un emittente, e il drawer lo passa alla lista
  (`emittenteEsplicito`). Sulla 6 (BoM, catalogo) `perimetro_emittente = f`;
  ⚠️ **superato da D-8.2 (Tid, 2026-09-28): anche la 6 è `t`**, come
  `catalogo.articoli`;
- preset di sistema con `pagina_dimensione = 10` (`PAGINATION.COMPACT_ROWS`: è
  una lista dentro un drawer, com'è oggi).

Bozze col generatore, che parte dal `.vue` di oggi:

```bash
.venv/bin/python scripts/gen_seed_lista.py \
    --codice <codice> --descrizione "<descrizione>" --vue <file .vue>
```

⚠️ Per le righe 1-3 il generatore legge le `<Column>` scritte nel
`<template #columns>` di `RigheMasterDetailTable`: è lì che stanno oggi.

### 3.2 Le priorità di ritiro — sono il cuore di questo brief

Le priorità decidono **quali colonne restano a video su un tablet** e quali
finiscono nella riga espandibile. Scala del catalogo: 0-100, si ritira per
prima la più bassa; `identificatore` e `azione` non si ritirano mai.
✅ **Approvate da Tid il 2026-09-27** (righe 1-6; la 7, approvata il 2026-09-28, sta in §7):

**Righe commerciali 1-3 (colonne GEMELLE: stessi codici, etichette e
priorità, cambia solo la data di consegna).** Così i tre documenti si
comportano allo stesso modo sullo stesso schermo.

| Codice colonna | Tipo | Priorità | Nota |
| --- | --- | --- | --- |
| `articolo_codice` | identificatore | — | |
| `descrizione` | informazione | 95 | |
| `qta_operativa` | informazione | 90 | |
| `importo_riga` | informazione | 85 | |
| `prezzo_unitario` | informazione | 70 | slot: tag di approvazione prezzo (preventivo) |
| `uom_codice` | informazione | 60 | |
| `sconto_percentuale` | informazione | 40 | |
| `data_consegna` | informazione | 35 | `campo_sorgente`: `data_consegna_richiesta_cliente` (preventivo), `data_consegna_confermata` (ordine); assente sul DDT |
| `iva` | informazione | 30 | `campo_sorgente` `iva_descrizione` |
| `azioni` | azione | — | |

**Reso (4):** `articolo_codice` identificatore · `descrizione` 95 ·
`qta_operativa` 90 · `stato_riconsegna` 80 · `tipo_reso` 70 ·
`uom_codice` 60 · `gia_accreditato` 50 · `motivo` 40 · `azioni`.

**Fattura (5), sola lettura:** `riga_nr` identificatore · `descrizione` 95 ·
`quantita` 90 · `importo_riga` 85 · `prezzo_unitario` 70 · `uom_codice` 60 ·
`sconto_percentuale` 40 · `iva` 30.

**BoM (6):** `componente_codice` identificatore · `componente_descrizione`
95 · `coeff_qta` 90 · `valido_al` 60 · `esposto_in_fattura` 40 · `azioni`.
⚠️ **Integrata dalla D-8.5 (Tid, 2026-09-28): `valido_dal` 65.** Il codice del
componente non identifica la riga (dopo «Duplica versione» compare due volte);
la data di inizio sì. Ordine di partenza: `valido_dal` DESC, come oggi.
⚠️ Le colonne di validità (`valido_dal`/`valido_al`) si ordinano con
`COALESCE(col, 'infinity')` e partono DESC (regola delle date di validità).

### 3.3 Ordinabilità

`ordinabile = t` solo sulle colonne che il repository mette nella whitelist
(§4). Prima della consegna al BE si lancia il controllo del generatore
(seed contro whitelist): una freccia fuori whitelist non dà errore, a video
semplicemente non ordina.

⚠️ **L'ordine qui sopra non è eseguibile (§8.7):** al momento del seed la
whitelist non esiste ancora e `gen_seed_lista.py` non ha la voce della lista.

## 4. Lavoro BE (`dev/backend-tid`, dopo i seed)

Per ciascuna lista 1-6:

- **endpoint di lista paginato**: `search`, `order_by`/`order_dir`,
  `limit`/`offset`, `lista_codice` sulla view, `is_search_endpoint`; risposta
  `{results, count}`. Stampo: `magazzino/api/views.py` `_Righe`;
- **endpoint di export** (`…/righe/export/`), stampo `_RigheExport`;
- whitelist di ordinamento; ordine di partenza = quello del documento
  (`riga_nr`, o `ordine` sul preventivo), non una colonna scelta nel FE;
- ⛔ **il `count` non si deriva dalle righe** (`api.md` §«Il `count` non si
  deriva MAI dalle righe che stai consegnando»).

⛔ **La lettura COMPLETA resta, con il suo nome.** Oggi `repo.list_righe` è
letto intero da: i generatori di contesto documento (`*_document_context_builder`),
i conteggi `righe_count` di preventivi, ordini e DDT, `ordini_service`
(evasione) e `contratti_service`. Nel FE, `OrdineEvasioneDialog` e
`ResoRiconsegnaDialog` chiamano `store.loadRighe` e hanno bisogno di **tutte**
le righe. ⇒ La lista paginata nasce **accanto** (`list_righe_pagina`, o nome
equivalente), non al posto della lettura intera. I due dialog passano a una
lettura esplicita «tutte le righe», come `righe-per-reso` esiste già per il
DDT: si decide nel lotto quale forma, ma ⛔ non si ottiene «tutte» chiedendo
alla lista una pagina molto grande.

**Fattura (5):** nasce `GET fatture/<id>/righe/` (oggi le righe arrivano solo
dentro il dettaglio).

**BoM (6):** i due filtri oggi locali (validità «tutto/vigenti», testo)
diventano parametri dell'endpoint.

⚠️ Il cambio di forma della risposta (lista → `{results, count}`) è un breaking
change: ammesso (non in produzione), ma i lettori elencati sopra vanno
allineati **nello stesso giro**.

## 5. Lavoro FE

### L1 — il building block (parte subito, nessun prerequisito DB)

`RigheMasterDetailTable` smette di disegnare una `DataTable` e diventa
**`useDrawerTabLista` + `<DrawerTabLista>` + la macchina del form**:

- props nuove: `codice`, `store` (lo store-lista delle righe, uno per istanza
  con `storePerIstanza`), `emittenteEsplicito`;
- `deleteAction` diventa **facoltativa**: senza, «elimina» non compare. Serve
  alla BoM, dove una riga non si elimina ma si chiude a data («Chiudi riga» e
  «Duplica versione» entrano come `extraRowActions`);
- lo slot `#columns` sparisce: il caller passa gli slot `cell-{codice}` (e
  `#filtri`/`#filtri-sempre`), inoltrati per nome come fa `DrawerTabLista`;
- restano identici `#form`, gli eventi `changed`/`form-aperto`, `loadRighe`
  esposta (i drawer padre la chiamano), `app-escape` sulla cella azioni.

Nello stesso lotto passano sul BB **`DistintaDrawer` e
`DocumentoInternoDrawer`**, le cui liste esistono già: così il BB nasce con due
consumatori veri e le due copie della macchina si ritirano insieme (regola del
2: le copie si ritirano nello STESSO giro).

#### ✅ Com'è andato (2026-09-28) — e perché la forma è cambiata

⚠️ **Il BB è un composable, `core/composables/useRigheMasterDetail.js`, non
il componente descritto sopra.** Il piano metteva `useDrawerTabLista` dentro
`RigheMasterDetailTable`; leggendo i due drawer da migrare non regge:

- lo **stato del form serve al drawer**, in punti che il componente-lista non
  raggiunge: le azioni della barra si spengono a form aperto («Nuova riga»,
  «Righe da rate» della distinta), il `FormFooter` della testata sparisce in
  form mode (regola 12 del pattern), la ricarica dopo un gesto chiude il form;
- la **lista la monta il drawer**: gli slot dei filtri scritti dal drawer usano
  `searchText` e `applyFilters` (il «Mostra scartate» della distinta), che
  `useDrawerTabLista` restituisce a chi lo chiama. Chiamato dentro il
  componente, andrebbero ritrasportati fuori.

⇒ La parte davvero comune alle tre copie era la **macchina**, e quella è il BB:
`useRigheMasterDetail({ padre, puoModificare })` → `formMode`,
`rigaInModifica`, `formAperto`, `nuovaRiga`, `apriRiga`, `chiudiForm`,
`risincronizza`, `azioneNuovaRiga`. I drawer continuano a montare
`useDrawerTabLista` + `<DrawerTabLista>` come prima.

| File | Cosa |
| --- | --- |
| `core/composables/useRigheMasterDetail.js` + `.spec.js` | il BB (6 test; il cambio di padre provato per mutazione: tolto il `watch`, rosso il test 6) |
| `core/components/RigheMasterDetailTable.vue` | la macchina dal BB; la `DataTable` **resta** fino a L2 (le vendite non hanno ancora il seed) |
| `pagamenti/components/DistintaDrawer.vue`, `magazzino/components/DocumentoInternoDrawer.vue` | la macchina dal BB; debito del 28/08 chiuso nei commenti di testa |
| catalogo BB FE, `frontend-standards` §«Pattern Master-Detail inline» regola 11 | la voce nuova; `formMode` non si scrive più a mano |

⭐ **Un difetto chiuso strada facendo.** `RigheMasterDetailTable` non chiudeva
il form al cambio di documento: il drawer non si smonta, cambia la prop, e il
form restava aperto sulla riga del documento precedente, pronto a salvare sul
padre nuovo. I due drawer lo facevano a mano; ora è una regola del BB (il
`padre`), per tutti e tre.

⭐ **Un comportamento reso uniforme.** «Nuovo» di `RigheMasterDetailTable`
restava a video col form aperto (un secondo clic buttava via la riga in
scrittura); i due drawer lo spegnevano. Ora si spegne ovunque
(`azioneNuovaRiga`).

Prove: vitest 58 file / 467 test, `npm run lint`, `npm run guards`,
`vite build` verdi.

#### 🔴 Verifica critica di L1 (2026-09-28) — il BB non è la sede unica

⚠️ **Errore mio, da dichiarare.** Prima di estrarre ho cercato nel catalogo e
nelle tre copie delle righe di documento, non in tutto il codice. La stessa
macchina (`formMode` null/crea/modifica + la riga + apri/chiudi) era **già** un
building block, due volte:

| Sede | Tipo | Consumatori | Differenze dal BB nuovo |
| --- | --- | --- | --- |
| `amministrazione/composables/useEditableCollection.js` | BB, **non a catalogo** | `useStepFigliCollection`, `useArchiCollection` (6 tab dell'editor definizioni) | aggiunge salva/elimina/attivo; nomi inglesi (`startCreate`, `rowInForm`) |
| `anagrafiche/composables/useSoggettoRuoloCollection.js` | BB a catalogo | contatti, conti bancari, titoli IVA | aggiunge caricamento soggetto/ruolo e salvataggio; ⚠️ vocabolario diverso: `'new'` invece di `'create'`, `editId` invece della riga |
| `core/composables/useRigheMasterDetail.js` | BB (L1) | le righe di documento | solo la macchina, più chiusura al cambio di padre e «Nuova riga» |

E a mano, sette volte: `core/components/NoteDrawer.vue`,
`vendite/components/ContrattoRigheDrawer.vue`, `vendite/components/VersioneDrawer.vue`,
`vendite/offerte/components/OffertaEccezioniDrawer.vue`,
`anagrafiche/components/IndirizziSoggettoDrawer.vue`,
`catalogo/components/ArticoloUomDrawer.vue`,
`amministrazione/views/DefinizioneEditorView.vue`. Più `ArticoloBomDrawer`, che
dice la stessa cosa con altri nomi (`adding`, `isFormOpen`): il criterio è il
significato, non il testo.

📌 *Fatto datato (2026-09-28), non motivo*: il conto dice **dove** mettere le
mani. La ragione per unificare è la regola del 2: il difetto chiuso qui (form
aperto al cambio di documento) vive ancora, o non vive, in ciascuna copia a
seconda di chi l'ha scritta.

⭐ **La causa**: `frontend-standards` §«Come applicare a una nuova
sub-entita'» diceva «copiare la struttura di `ContrattoRigheDrawer.vue`». Lo
standard prescriveva la duplicazione. Corretto nello stesso giro.

**Proposta (tocca amministrazione, anagrafiche, vendite, catalogo e core) —
✅ approvata da Tid il 2026-09-28 e FATTA lo stesso giorno (sotto):**

1. `useRigheMasterDetail` resta la **sola macchina** (è in `core`, gli altri
   due sono in un dominio). Il nome forse è da allargare, perché non serve
   solo alle righe di documento (per esempio `useFormInline`): lo decide Tid;
2. `useEditableCollection` e `useSoggettoRuoloCollection` la **usano** invece
   di riscriverla, e tengono solo ciò che aggiungono (salvataggio,
   eliminazione, caricamento). `useSoggettoRuoloCollection` si allinea al
   vocabolario `'create'`, con i suoi tre drawer;
3. i sette drawer a mano (e la BoM) passano alla macchina. Quelli di vendita
   insieme a L2-L4, gli altri in un giro loro;
4. `useEditableCollection`, se resta, entra nel catalogo.

#### ✅ L'unificazione (2026-09-28)

**Nome: `useFormInline`** (scelto dall'agente su mandato di Tid): riprende il
nome del pattern («master-detail inline») e non lega il BB alle righe di un
documento, che sono uno solo dei suoi usi.

| Dove | Cosa |
| --- | --- |
| `core/composables/useFormInline.js` + `.spec.js` | il BB rinominato; `azioneNuovaRiga` accetta `command` (il verbo del contenitore che all'apertura fa anche altro) |
| `amministrazione/composables/useEditableCollection.js` | la macchina dal BB, restituita per intero. I sei tab e `CollectionEditorPanel` passano ai nomi del BB (`rigaInModifica`, `nuovaRiga`, `chiudiForm`): due nomi per la stessa cosa sarebbero la copia che si voleva togliere |
| `anagrafiche/composables/useSoggettoRuoloCollection.js` | la macchina dal BB; `startNew`/`startEdit`/`cancelForm` restano, perché sono verbi della collezione (errori, popolamento, fotografia) che la chiamano; `'new'` → `'create'` (e `ContiBancariDrawer`, che lo leggeva); `editId` ritirato; padre = il proprietario a drawer aperto |
| `NoteDrawer`, `ArticoloUomDrawer`, `VersioneDrawer`, `OffertaEccezioniDrawer`, `DefinizioneEditorView` | la macchina dal BB; `'new'` → `'create'` dove c'era; la selezione evidenziata è la riga in modifica |
| `IndirizziSoggettoDrawer` | `'new'`/`'replace'` → `'create'`/`'edit'`: «cambia» è la modifica di un indirizzo esistente, la **sostituzione** è il verbo di salvataggio del dominio e resta suo |

⭐ **Due comportamenti resi uniformi dal BB**, e sono correzioni:

- **«Nuovo» sparisce a form aperto** ovunque. `VersioneDrawer` e
  `OffertaEccezioniDrawer` lo tenevano attivo durante la **modifica** di una
  riga (lo spegnevano solo in creazione): un clic buttava via la modifica in
  corso. `ArticoloUomDrawer` lo teneva a video disabilitato;
- **il cambio di padre chiude il form** anche in `DefinizioneEditorView`
  (un'altra definizione) e in `useSoggettoRuoloCollection` (un altro
  proprietario sotto lo stesso drawer).

⛔ **Un difetto introdotto e chiuso nello stesso giro**, da sapere per i
prossimi: `hideWhenReadonly` legge il readonly **iniettato**.
`OffertaEccezioniDrawer` ha un readonly **locale** più stretto («offerta non in
BOZZA») e non lo fornisce ai figli: col solo `hideWhenReadonly`, «Nuovo»
sarebbe ricomparso su un'offerta emessa. Si passa anche in `visible`; la regola
è scritta nella voce di catalogo.

**Fuori, con il loro lotto:** `ContrattoRigheDrawer` (L4) e `ArticoloBomDrawer`
(L3), dove cambia comunque tutta la lista.

Prove: vitest 58 file / 467 test, `npm run lint`, `npm run guards`,
`vite build` verdi.

**Cosa cambia per L2.** Il componente `RigheMasterDetailTable` passa a
`<DrawerTabLista>` quando i documenti di vendita hanno il seed; le props
`codice`/`store` e gli slot `cell-{codice}` del piano restano validi, ma il
componente riceve i valori di `useDrawerTabLista` dal chiamante (come fa
`DrawerTabLista` stesso) invece di chiamarlo da sé. Si decide lì, con i
quattro consumatori davanti.

### L2 — vendite 1-4 (dopo seed e BE)

Store-lista per documento (`createListaStore`, stampo
`magazzino/stores/documentoRighe.js`), consumer sul BB, slot per le celle
speciali (prezzo con tag di approvazione, IVA, date, `gia_accreditato`). I due
dialog di evasione e riconsegna passano alla lettura completa del §4.

### L3 — fattura e BoM

- Fattura: sola lettura, niente form ⇒ `<DrawerTabLista>` diretto, senza il
  BB master-detail.
- BoM: sul BB se il flusso «Duplica versione» (chiudi + form precompilato) ci
  sta come `extraRowActions` + `#form`; è il test di generalità del BB. Se non
  ci sta, `<DrawerTabLista>` diretto, e ⛔ comunque niente `DataTable`.

### L4 — contratto (§7)

Ultimo lotto, dopo che L1-L3 hanno collaudato il BB. Prima il BE: endpoint
righe proprio (lista paginata + export) e la sede delle tre colonne calcolate
(§7); poi il seed della lista 7; poi il FE, sul BB con `#form` e la riga di
espansione dell'anteprima.

## 6. Documentazione, nello stesso giro

- `frontend-standards` §«Regola zero della lista»: la riga «righe di un
  documento» esce dalle eccezioni; §«Pattern Master-Detail inline» punta al BB
  nuovo;
- catalogo BB FE: voce `RigheMasterDetailTable` riscritta;
- piano PrimeVue 5 §Gruppo B: il criterio in tre domande perde la seconda
  domanda («sono le righe del documento? → Gruppo B»);
- `docs/it/backend/vendite/manual/api_*.md`: contratto nuovo degli endpoint
  righe.

## 7. Contratto — resta in questo brief (Tid, 2026-09-27)

✅ **Deciso da Tid: il contratto resta qui**, come lotto L4 (§5), non in un
brief a parte.

**Perché è l'ultimo.** Le righe del contratto non hanno una lettura propria:
arrivano dal dettaglio del padre (`righeIniziali`) e passano da un'anteprima
prezzi (`/righe-preview/`) con colonne **calcolate** (prezzo listino, prezzo
finale, origine) e una riga di espansione propria. Convertirle chiede prima un
endpoint righe e una decisione su dove stanno quelle tre colonne.

✅ **Le tre colonne calcolate — deciso da Tid il 2026-09-28**: prezzo listino,
prezzo finale e origine arrivano dall'**endpoint righe**, come colonne di
catalogo uguali alle altre (ordinabili, esportabili, personalizzabili). Una
colonna che esiste solo nel FE non si esporta e non si personalizza.
L'anteprima prezzi resta per il momento dell'inserimento, ma non è più la
sorgente della lista.

✅ **Priorità della lista 7 — approvate da Tid il 2026-09-28**, con la stessa
logica delle righe commerciali (cosa si compra, quanto, a che prezzo resta a
video; il resto si ritira per primo):

| Codice colonna | Tipo | Priorità |
| --- | --- | --- |
| `articolo_codice` | identificatore | — |
| `descrizione` | informazione | 95 |
| `qta_operativa` | informazione | 90 |
| `prezzo_finale` | informazione | 85 |
| `prezzo_forzato` | informazione | 70 |
| `uom_codice` | informazione | 60 |
| `tipo_erogazione` | informazione | 45 |
| `prezzo_listino` | informazione | 35 |
| `origine` | informazione | 30 |
| `azioni` | azione | — |

⚠️ **Riga 70 corretta dalla D-8.4 (Tid, 2026-09-28):** era `prezzo_unitario`,
che nella sorgente della lista non esiste. Diventa `prezzo_forzato`, etichetta
«Prezzo forzato», `campo_sorgente` = `override_prezzo` della funzione: il
prezzo scritto a mano sull'eccezione, vuoto sulle righe che lo prendono dal
listino. Stessa priorità.

## 8. Verifica critica della parte DB (2026-09-28)

> Letta sul **contratto**: CSV di seed, doc auto-gen delle viste e funzioni,
> nullabilità, presidi pgTAP e Django. Nessuna misura sui dati: dove sotto
> compare un comportamento, è quello che il modello **ammette**.

### 8.1 🔴 «Seed prima, BE dopo» manda in rosso la CI

Le liste 1-7 hanno `vista_sql` NULL. Un seed che arriva **da solo** su
`Tito-dev` arma quattro presidi che leggono il CSV, e che nessun lavoro DB può
far tornare verdi:

| Presidio | Cosa pretende | Chi lo scatena |
| --- | --- | --- |
| `core/tests/db/test_lista_proiezione_campo_sorgente` test 2 | ogni lista **attiva** con `vista_sql` NULL ha il suo `_ESERCIZI` | le sette definizioni |
| stesso file, test 1 | ogni `campo_sorgente` **attivo** è una chiave che il repository proietta | ogni colonna con sorgente |
| `core/tests/test_perimetro_emittente_copertura` `…il_registro_e_il_seed…` | ogni `perimetro_emittente = f` del seed ha la sua ragione in `_ESENZIONI` | la BoM (6); legge il CSV **senza** filtrare `attivo` |
| `core/tests/test_ricerca_full_seed` `…ricercabile_e_registrata_o_in_debito` | ogni lista con colonne `ricercabile_full` è in `_RICERCHE` o nel debito | le colonne ricercabili |

⇒ Due forme, da scegliere (decisione **D-8.1** in §8.9):

- **A — seed e BE nello stesso giro verso `Tito-dev`**, lista per lista (L2:
  1-4, L3: 5-6, L4: 7). Il seed si scrive prima, ma si mergia insieme al BE;
- **B — seed «spento»**: definizioni e colonne con sorgente nascono
  `attivo = f` (regola di casa per le liste senza vista), le accende il BE
  nello stesso commit in cui le proietta e le registra. ⚠️ Non basta per la
  BoM se resta `perimetro_emittente = f`: quel test legge anche le righe spente.

Raccomandazione: **B**, che è la regola già scritta; più l'esenzione BoM
chiesta al BE nello stesso merge (o D-8.2 risolta in `t`).

✅ **Deciso da Tid il 2026-09-28: né A né B.** Il seed si scrive **acceso**
(`attivo = t`) e va per la sua strada; il rosso momentaneo dei presidi Django
fino all'arrivo del BE è **accettato** («non fa niente se momentaneamente va in
errore»). ⇒ Nel brief va scritto, nella richiesta al BE, quali quattro test
tornano verdi col suo lavoro (tabella sopra), perché chi vede il rosso sappia
che è atteso e da dove si chiude.

### 8.2 🟠 BoM globale: coerente col modello, incoerente col catalogo

`catalogo.articoli_componenti` non ha emittente, quindi `perimetro_emittente = f`
è la lettura giusta del modello. Ma la lista madre `catalogo.articoli` (26) e
le tre liste UoM (20-22) sono a `t`, e nemmeno quelle tabelle hanno un
emittente. Una delle due letture è sbagliata:

- o `f` è giusto, e le quattro liste di catalogo sono un debito dello stesso
  tipo delle sei geografiche corrette il 2026-09-27;
- o `t` ha una ragione che il seed non dice, e la BoM la eredita.

✅ **Deciso da Tid il 2026-09-28: la distinta è PER AZIENDA**
(`perimetro_emittente = t`, `multi_emittente = f`), come la sua lista madre
`catalogo.articoli`. ⇒ Nessun elenco pgTAP da toccare, nessuna esenzione da
chiedere al BE, e l'eccezione BoM di §8.1 cade. Le quattro liste di catalogo
restano come sono.

~~Se `f`~~ (non più applicabile): la BoM andava aggiunta all'elenco di
`db/pgtap/ui/test-lista-definizione-perimetro-emittente-v1.sql` test 6 (ordine
alfabetico, con la riga di motivo), e al BE si chiede la ragione «catalogo
globale» in `_ESENZIONI`. Gli altri due elenchi (`multi_emittente`, soglia 1)
non sono toccati.

### 8.3 🔴 Fattura (5): la vista non ha una chiave di riga

La sorgente è `vendite.vw_fattura_righe_esposte`, e la sua forma rende la
tabella del §3.2 non costruibile così com'è:

- **`riga_nr` non è unico, per progetto**: le due parti `PARTE_PLAFOND` lo
  condividono («`riga_nr` NON cambia», dal `COMMENT` della vista), e il
  `KIT_PADRE` prende `min(riga_nr)` dei componenti, cioè lo stesso numero del
  suo primo `KIT_COMPONENTE`. Come `identificatore` è ambiguo;
  ⚠️ **corretto il 2026-09-28 scrivendo il Blocco 2 (§8.12):** metà di questo
  punto era sbagliata. L'indice unico `uq_fatture_righe_riga_nr (fattura_id,
  riga_nr)` impedisce alle due parti del plafond di avere lo stesso numero: la
  parte ha il suo `riga_nr`, e condivide con la capofila solo `ordinamento`.
  ⚠️ **E il `COMMENT` della vista madre NON sbagliava (riletto il 2026-09-28
  sera):** «`riga_nr` NON cambia» vuol dire che ogni riga **conserva il suo**
  numero di linea, non che le due parti ne condividano uno. L'errore era mio,
  nella lettura. Resta vero che il padre del kit ripete il numero del suo primo
  componente, e che non ha una PK: la chiave calcolata serve comunque;
- **il `KIT_PADRE` ha `fatture_righe_id` NULL**, e il repository lo alias-a
  `id`: la lista non ha una chiave stabile. Il drawer di oggi lo sa e rinuncia
  alla `data-key`; paginazione, espansione ed export non possono.
  ⇒ **DDL**: la vista espone una chiave di riga calcolata (per il padre: la
  stessa tupla del raggruppamento, fattura + `kit_key` + IVA + BA destinatario),
  in coda alle colonne, con `security_invoker` ri-specificato;
- **l'ordine è una struttura, non una preferenza**: `ordinamento, livello`
  mettono i componenti sotto il loro padre. Un ordinamento per importo stacca i
  componenti (importo NULL, per progetto) dal padre, e una pagina da 10 può
  tagliare un kit. ⇒ Proposta: sulla 5 **nessuna colonna ordinabile**, ordine
  fisso `ordinamento, livello, riga_nr, <chiave>` (D-8.3);
- **mancano colonne che il drawer mostra oggi**: la riga rettificata della nota
  di credito (`riga_rettificata_*`, «si legge accanto alla fattura riga per
  riga»), e il rientro dei componenti (`livello`). L'IVA oggi non è
  `iva_descrizione` ma `formatIvaLabel` su `iva_codice`/aliquota, con ripiego
  su `iva_natura`: il `campo_sorgente` della colonna `iva` va scelto.

✅ **Deciso da Tid il 2026-09-28 (D-8.3), al posto del «non ordinabile»:
i componenti del kit diventano il DETTAGLIO della riga padre.**

- **La lista = le sole righe di livello 0** (`NORMALE`, `PARTE_PLAFOND`,
  `KIT_PADRE`). I `KIT_COMPONENTE` escono dalla lista ed entrano nella riga
  padre come `componenti jsonb` (stessa forma di
  `fn_contratto_righe_preview`), che il FE apre nella riga di espansione — come
  le righe composite del preventivo;
- ⇒ ordinamento e paginazione lavorano sul padre: il kit **si muove intero** e
  non si spezza fra due pagine; il `count` conta le righe di livello 0;
- **DDL**: una vista nuova **sopra** `vw_fattura_righe_esposte` (nessun calcolo
  rifatto: quella resta la sede unica della rappresentazione), con
  `security_invoker`, che espone la chiave di riga stabile (anche per il
  `KIT_PADRE`) e aggrega i componenti. Nome da fissare nel changeSet;
- **ordinabile**: sì, sulle colonne della lista. Ordine di partenza
  `ordinamento, riga_nr, <chiave>`;
- ⚠️ **limite dichiarato**: le due `PARTE_PLAFOND` sono righe vere (due
  `DettaglioLinee`) e restano due righe; ordinando per importo possono
  separarsi, per `riga_nr` restano vicine (stesso numero). Accettato;
- **ricerca**: `ricercabile_full` su codice e descrizione articolo (vale anche
  per BoM e contratto, oggi filtrati in locale).

### 8.4 🔴 Contratto (7): due grane, e tre colonne che vivono solo in una

Il drawer di oggi ha **due forme**, e la lista 7 le mescola:

| Forma | Righe da | Chiave |
| --- | --- | --- |
| con listino | `vendite.fn_contratto_righe_preview` — una riga per articolo × UoM: righe `DA_LISTINO` **non persistite** + overlay OVERRIDE/ESCLUSIONE + AGGIUNTA | nessuna: il FE sintetizza `_row_key` = `articolo_id__uom_id` |
| senza listino | `vendite.contratti_righe` (le sole eccezioni) | `id` |

- `prezzo_listino`, `prezzo_finale`, `origine` esistono **solo** nella funzione;
  `prezzo_unitario` (priorità 70) esiste **solo** in `contratti_righe` — nella
  funzione ci sono `override_prezzo` e, per le AGGIUNTA, `cr.prezzo_unitario`
  dentro lo stesso slot;
- la decisione del 2026-09-28 («dall'endpoint righe») dice **dove** arrivano,
  non **da quale grana**. La sede del calcolo è già a DB: l'endpoint deve
  leggere la funzione, non ricalcolare il prezzo (niente logica duplicata fra
  livelli);
- la Parte 2 della funzione gira anche senza listino, quindi la grana della
  funzione **copre le due forme** — è la candidata naturale (D-8.4);
- le azioni cambiano per `origine` (DA_LISTINO → sovrascrivi/escludi;
  AGGIUNTA → modifica/elimina): oggi le decide il FE. Per §12.5 delle linee
  guida SQL è una **capability di riga**, e va emessa dalla funzione.

✅ **Deciso da Tid il 2026-09-28 (D-8.4): la lista 7 legge SEMPRE
`fn_contratto_righe_preview`, per le due forme.** La funzione cambia forma e
aggiunge:

1. una **chiave di riga stabile** (il FE smette di sintetizzare `_row_key`);
2. la **capability di riga** (§12.5 linee guida SQL): DA_LISTINO →
   sovrascrivi prezzo / escludi; OVERRIDE e ESCLUSIONE → modifica / ripristina;
   AGGIUNTA → modifica / elimina. Elenco esatto dei verbi da fissare leggendo
   il drawer di oggi, nel changeSet;
3. la colonna prezzo di lista = `override_prezzo`, etichetta «Prezzo forzato»
   (§7).

⇒ **DDL per L4**: chiave di riga stabile emessa dal DB, capability di riga,
e la colonna prezzo da decidere (`override_prezzo` o via). Cambia un
`RETURNS TABLE`: DROP + CREATE, e censimento dei pgTAP che la chiamano.

### 8.5 🟠 BoM (6): la vista è stantìa e la regola vive in due posti

`catalogo.vw_articoli_componenti_dettaglio` **non ha `esposto_in_fattura`**
(colonna della lista, priorità 40) né `determina_qta_padre`. Il repository non
la legge: rifà la stessa proiezione in `COMPONENTE_DETAIL_COLUMNS`, capability
di chiusura compresa, con il commento «aggiornare ENTRAMBI». È la divergenza
che la regola del 2 previene, ed è già avvenuta (le due colonne).

⇒ Proposta (D-8.5): **DDL** che porta la vista al pari (colonne in coda), il BE
la legge al posto della proiezione, e la definizione 6 ha
`vista_sql = catalogo.vw_articoli_componenti_dettaglio`. Effetti: il trigger
`ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente` valida il seed **al
migrate** (presidio DB gratuito) e il cancello Django di §8.1 non si applica.

Due punti di seed:

- **`componente_codice` non identifica la riga**: l'unicità è
  `(prodotto, componente, valido_dal)`, e dopo «Duplica versione» lo stesso
  componente compare su due righe. `valido_dal` è citato nella nota di §3.2 ma
  **manca dalla tabella**: va in lista, con priorità almeno pari a `valido_al`;
- l'ordine di oggi è `valido_dal DESC, id`: va scritto
  nell'`ordinamento_default` del preset, o il controllo `default_rotti` del
  generatore non ha nulla da confrontare.

✅ **Deciso da Tid il 2026-09-28 (D-8.5): una sede sola, la vista.**

- **DDL**: `CREATE OR REPLACE VIEW` di `vw_articoli_componenti_dettaglio` con
  `esposto_in_fattura` e `determina_qta_padre` **in coda** (dalla doc auto-gen,
  non dagli YAML);
- **seed**: definizione 6 con `vista_sql = catalogo.vw_articoli_componenti_dettaglio`
  → il trigger `a10_valida_campo_sorgente` controlla le colonne al migrate;
  `valido_dal` 65 in lista (§3.2); preset con
  `ordinamento_default = [{"col":"valido_dal","dir":"desc"}]`;
- **richiesta al BE**: `catalogo_bom_repository` legge la vista e ritira
  `COMPONENTE_DETAIL_COLUMNS` (la capability di chiusura resta solo a DB),
  nello stesso giro.

### 8.6 🟡 Preventivo (1): una vista che nessuno legge

`vendite.vw_preventivi_righe_dettaglio` è la proiezione che il repository
**dice** di leggere («via vista», riga ~404), ma la query legge la tabella e
aggiunge `data_consegna_richiesta_cliente`, `stato_approvazione_prezzo`,
`pratica_approvazione_prezzo_id`, `is_composito_caso_a`, che la vista non ha.
La vista ha anche un `ORDER BY` nel corpo. Lettori: il solo
`db/pgtap/rls/test-rls-preventivi-satelliti.sql`.
Stessa scelta della BoM (D-8.6): o la vista diventa la sorgente, o si ritira
insieme al commento che la cita.

✅ **Deciso da Tid il 2026-09-28 (D-8.6), ESTESO a ordini e DDT: per le
righe di un documento la sede è una vista DB, e il repository la legge.**

| Lista | Vista | Lavoro DB |
| --- | --- | --- |
| 1 preventivo | `vendite.vw_preventivi_righe_dettaglio` (esiste, stantìa) | `CREATE OR REPLACE` con le quattro colonne in coda, **senza** l'`ORDER BY` nel corpo, `security_invoker` ri-specificato |
| 2 ordine | nuova, `vendite.vw_ordini_righe_dettaglio` | dalla query di `ordini_repository.list_righe`: evaso/residuo da `ordini_righe_fulfillment`, flag componenti, le due date di consegna |
| 3 DDT | nuova, `vendite.vw_ddt_righe_dettaglio` | dalla query di `ddt_repository.list_righe`, con `importo_riga` NULL se manca il prezzo (V-2/DEC-6 del DDT) |
| 4 reso | `vendite.vw_resi_righe_dettaglio` (esiste, letta con `SELECT *`) | nessun DDL: solo `vista_sql` nel seed, per coerenza |

- le quattro definizioni hanno `vista_sql` valorizzata → il trigger
  `a10_valida_campo_sorgente` controlla il seed al migrate, e il cancello
  Django di §8.1 non le riguarda più (resta sulle liste 5 e 7);
- le viste nuove nascono con `security_invoker`, e il perimetro RLS delle
  tabelle righe resta quello delle tabelle (pgTAP RLS da estendere alle due
  viste nuove, come `test-rls-preventivi-satelliti` fa per la prima);
- ⛔ **nessun `ORDER BY` nelle viste**: l'ordine lo dà la whitelist del BE;
- **richiesta al BE**, stesso giro: `list_righe`/`get_riga` dei tre repository
  leggono la vista e le proiezioni Python si ritirano (regola del 2: le copie
  si ritirano insieme all'estrazione). ⚠️ `ordini_repository.get_riga` oggi ha
  una proiezione più corta di `list_righe` (niente evaso): leggendo la vista
  diventano la stessa.

### 8.7 🟡 Il seed, voce per voce

- **§3.3 non è eseguibile nell'ordine scritto**: `--verifica-ordinamento`
  cerca la lista nella mappa di `gen_seed_lista.py` e la whitelist nel
  repository, che nascono col BE. ⇒ `ordinabile` è il contratto che il DB
  dichiara; il controllo gira nel giro BE (o nel giro unico di §8.1-A);
- **priorità di `identificatore` e `azione`**: la tabella dice «—», i seed di
  casa scrivono `100` (37, 69, 71, 74);
- **`pagina_dimensione = 10`** «come le liste righe già a catalogo»: vale per
  la 37; 69, 71 e 74 hanno `25`. Da scegliere e scrivere il motivo;
- **`campo_sorgente` non dichiarati**: reso `tipo_reso` →
  `tipo_reso_descrizione` (la vista ha anche `tipo_reso_codice_interno`);
  fattura `iva` (§8.3); contratto `descrizione` → `articolo_descrizione`;
- **ricerca**: nessuna colonna è dichiarata `ricercabile_full`. Oggi BoM e
  contratto filtrano in locale su codice e descrizione: quelle sono le
  candidate, e la scelta arma `test_ricerca_full_seed` (§8.1);
- **etichette gemelle 1-3**: «stesse etichette» ma oggi tre namespace
  (`vendite.preventivi.riga_*`, `vendite.ordini.riga_*`, `vendite.ddt.riga_*`).
  `check_i18n_keys.py` legge `etichetta_i18n_key` di `lista_colonna.csv`: una
  chiave nuova condivisa è lavoro FE nello stesso giro;
- **`data_consegna` sull'ordine = `data_consegna_confermata`**: il modello la
  ammette NULL (si decide alla conferma), mentre la richiesta del cliente esiste
  già. In bozza la colonna è vuota su ogni riga. Seconda colonna
  `data_consegna_richiesta` a priorità bassa, o scelta dichiarata;
- **preset per intero**: ogni colonna del catalogo in `lista_preset_colonna`,
  le spente con `visibile = f` (convenzione di `test-liste-preset-default-v1`).

### 8.8 🟡 `importo_riga` scritto sei volte

Stessa formula in `preventivi_repository`, `ordini_repository`,
`ddt_repository`, `vw_preventivi_righe_dettaglio` e nelle due `vw_*_righe_iva_base`.
Oggi danno lo stesso risultato (il `COALESCE(prezzo, 0)` dell'ordine è morto:
`ordini_righe.prezzo_unitario` è NOT NULL), ma la colonna «gemella» promette lo
stesso significato su tre documenti, e il DDT ha già **deciso** un ramo diverso
(NULL, non zero). Candidata a una funzione `IMMUTABLE` unica (D-8.8); se si
estrae, le copie si ritirano nello stesso giro.

✅ **Deciso da Tid il 2026-09-28 (D-8.8): in QUESTO cantiere.** Le viste
righe della D-8.6 si scrivono adesso: farle nascere con la formula copiata per
poi toglierla sarebbe lavoro doppio.

- **una funzione** `IMMUTABLE`, `PARALLEL SAFE`, sui **valori**
  (quantità, prezzo, sconto) e non su un id di riga: nessuna lettura, quindi
  nessuna RLS da attraversare. Restituisce l'imponibile **a precisione piena**;
  `importo_riga` = `round(…, 2)` nella vista, `imponibile_riga_full` = il
  valore pieno, come oggi;
- **semantica** = quella già scritta nelle viste IVA: prezzo NULL o quantità
  NULL → NULL, **mai zero** (V-2/DEC-6 del DDT); sconto NULL → zero;
- **sede**: `script`, non `vendite` — le righe di `acquisti` avranno la stessa
  formula (PROJECT_CONTEXT: ogni decisione su `vendite` è presa anche per
  `acquisti`). Nome da fissare nel changeSet, cercando prima nel catalogo BB e
  negli schemi `script`/`dbops` che non esista già;
- **le cinque copie si ritirano nello stesso giro**: le tre viste righe
  (D-8.6) nascono chiamandola, e le due `vw_ordini_righe_iva_base` /
  `vw_ddt_righe_iva_base` passano a chiamarla con `CREATE OR REPLACE`
  (colonne e ordine invariati, `security_invoker` ri-specificato);
- **pgTAP**: la funzione si prova sui valori, un caso per ramo (prezzo NULL,
  quantità NULL, sconto NULL, sconto 100); il riepilogo IVA si ricontrolla coi
  pgTAP che già leggono le due viste IVA (censimento dei chiamanti prima del
  changeSet).

### 8.9 Decisioni per Tid

| # | Domanda | Raccomandazione |
| --- | --- | --- |
| D-8.1 | Seed e BE: giro unico (A) o seed spento (B)? | ✅ **Tid, 28-09: seed acceso, rosso temporaneo accettato** |
| D-8.2 | BoM `perimetro_emittente`: `f` (e le 4 liste catalogo sono un debito) o `t`? | ✅ **Tid, 28-09: `t`, per azienda** |
| D-8.3 | Fattura: ordine fisso e nessuna colonna ordinabile? | ✅ **Tid, 28-09: no — componenti nel dettaglio del padre, lista ordinabile sul livello 0** |
| D-8.4 | Contratto: grana = `fn_contratto_righe_preview` per le due forme, con chiave e capability di riga dal DB? | ✅ **Tid, 28-09: sì, colonna «Prezzo forzato»** |
| D-8.5 | BoM: vista al pari e `vista_sql` valorizzata? | ✅ **Tid, 28-09: sì, più `valido_dal` 65** |
| D-8.6 | `vw_preventivi_righe_dettaglio`: sorgente o ritiro? | ✅ **Tid, 28-09: sorgente, esteso a ordini e DDT (e `vista_sql` sul reso)** |
| D-8.8 | `importo_riga` in una funzione: in questo cantiere o a parte? | ✅ **Tid, 28-09: in questo cantiere** |

### 8.10 Il lavoro DB che ne esce, in ordine (Blocco 1 scritto: §8.11)

> Riepilogo delle decisioni D-8.1 → D-8.8. ⏸ **Nessun changeSet scritto**: lo
> sviluppo parte al via di Tid. Ogni passo con la regola di casa: DDL e corpi
> dalla doc auto-gen, un changeSet per file, prova su SQL estratto in
> `BEGIN/ROLLBACK`, pgTAP lanciati da Tid.

**Blocco 1 — per L2 (liste 1-4) e la BoM (6)**

1. `20_code`: la funzione dell'importo di riga in `script` (D-8.8) + pgTAP sui
   valori;
2. `20_code`: `vw_preventivi_righe_dettaglio` al pari, `vw_ordini_righe_dettaglio`
   e `vw_ddt_righe_dettaglio` nuove, tutte sulla funzione (D-8.6);
3. `20_code`: le due `vw_*_righe_iva_base` sulla funzione (D-8.8);
4. `20_code`: `vw_articoli_componenti_dettaglio` al pari (D-8.5);
5. pgTAP: RLS delle due viste nuove; forma delle viste (colonne che il seed
   nomina);
6. `80_data`: seed delle liste 1-4 e 6 nei quattro CSV di `ui` (una tabella,
   un CSV), `vista_sql` valorizzata, **acceso** (D-8.1), BoM per azienda
   (D-8.2), `valido_dal` 65 e `ordinamento_default` sulla BoM. Prima
   dell'append: upsert dell'intero CSV in `ROLLBACK` con timeout (le due specie
   di mina, §11.2 linee guida SQL), e resync delle sequenze di
   `90_end/20260602-17` incluso nella prova.

**Blocco 2 — per L3 (fattura, 5)**

7. `20_code`: vista di lista sopra `vw_fattura_righe_esposte` — livello 0,
   chiave stabile, `componenti jsonb` (D-8.3) + pgTAP (un kit con due IVA, una
   riga spezzata dal plafond, costruiti, non trovati);
8. `80_data`: seed della lista 5 sulla vista nuova.

**Blocco 3 — per L4 (contratto, 7)**

9. `20_code`: `fn_contratto_righe_preview` con chiave di riga e capability di
   riga (D-8.4) — cambia il `RETURNS TABLE`: DROP + CREATE, censimento dei
   pgTAP e dei chiamanti prima;
10. `80_data`: seed della lista 7 con `prezzo_forzato`.

**Richieste al BE che nascono qui** (vanno nel §4 quando si scrive il blocco):
repository righe di preventivo, ordine, DDT e BoM sulle viste, con ritiro delle
proiezioni Python nello stesso giro; registri dei presidi Django (§8.1) per le
liste 5 e 7, che restano senza `vista_sql`; lettura della capability di riga
del contratto al posto della logica nel drawer.

### 8.11 Blocco 1 — consegna DB (2026-09-28)

> ✅ **Migrato da Tid il 2026-09-28, pgTAP verdi.** (Scritto e provato prima
> sullo scratch, §8.11.2.)

#### 8.11.1 Cosa c'è

| changeSet | Oggetto | Cosa |
| --- | --- | --- |
| `20_code/script/20260928-16` | `script.fn_imponibile_riga` | la sede unica dell'imponibile (D-8.8): pura, `IMMUTABLE`, `PARALLEL SAFE`, non `STRICT`, precisione piena, NULL se manca prezzo o quantità |
| `20_code/vendite/20260928-17` | `vw_preventivi_righe_dettaglio` | sorgente delle righe (D-8.6): quattro colonne in coda, niente `ORDER BY`, importo dalla funzione |
| `20_code/vendite/20260928-18` | `vw_ordini_righe_dettaglio` | **nuova**: le colonne di `list_righe`, evaso e residuo portati a DB |
| `20_code/vendite/20260928-19` | `vw_ddt_righe_dettaglio` | **nuova**: le colonne di `list_righe` |
| `20_code/vendite/20260928-20 / -21` | `vw_ordini_righe_iva_base`, `vw_ddt_righe_iva_base` | imponibile dalla funzione |
| `20_code/vendite/20260928-22 / -23 / -24` | le tre `vw_dash_fatturazione_*` | valore di riga (e residuo, sull'ordine) dalla funzione |
| `20_code/vendite/20260928-25` | `fn_ricalcola_riepilogo_iva_preventivo` | imponibile dalla funzione; firma col `%TYPE`, `SECURITY INVOKER` esplicito |
| `20_code/vendite/20260928-26` | `trgfn_fatture_righe_importo` | imponibile pieno dalla funzione, arrotondamento configurato invariato |
| `20_code/catalogo/20260928-27` | `vw_articoli_componenti_dettaglio` | sorgente della BoM (D-8.5): `determina_qta_padre`, `esposto_in_fattura` in coda |
| `80_data/sql/ui/*.csv` (quattro file, append) | liste 97-101 | `vendite.preventivo_righe`, `vendite.ordine_righe`, `vendite.ddt_righe`, `vendite.reso_righe`, `catalogo.articolo_componenti`: colonne 1011-1055, preset 97-101 |
| `db/pgtap/script/test-fn-imponibile-riga-v1.sql` | 15 test | formula, forma, consumatori, nessuna copia residua |
| `db/pgtap/vendite/test-vw-righe-dettaglio-sorgente-lista-v1.sql` | 9 test | `security_invoker`, niente `ORDER BY`, colonne dei consumatori |

⚠️ **Il perimetro di D-8.8 si è allargato, e va detto.** Il §8.8 contava sei
copie della formula; il censimento sulla doc auto-gen fatto prima di scrivere
ne ha trovate **otto a DB**: in più le tre `vw_dash_fatturazione_*`, il
ricalcolo IVA del preventivo e il trigger dell'imponibile di fattura. Per la
regola del 2 le copie si ritirano nello stesso giro: sono tutte in questo
blocco (`-20 → -26`). Oggi coincidevano tutte.

**Il seed, le scelte che non erano scritte nel §3:**

- `vista_sql` valorizzata su tutte e cinque (D-8.5/D-8.6; il reso sulla vista
  che c'era): il trigger `a10_valida_campo_sorgente` controlla il seed al
  migrate, e il cancello Django delle liste senza vista non le riguarda;
- priorità di identificatore e azioni = `100`, come i seed di casa;
- `ordinabile = t` su tutte le colonne con sorgente, `ricercabile_full = t` su
  codice articolo e descrizione (e motivo sul reso; codice e descrizione del
  componente sulla BoM), `filtrabile = f`, `sensibile = f`, `fissata = f`
  (come 71 e 74);
- `pagina_dimensione = 10` come dice il §3.1 approvato (⚠️ 69/71/74 hanno 25:
  resta il punto aperto del §8.7);
- `ordinamento_default` NULL sulle liste 1-4 (l'ordine del documento lo dà il
  BE), `valido_dal` DESC sulla BoM (D-8.5);
- chiavi i18n: quelle che le tabelle di oggi già usano, per documento. ⚠️ Le
  etichette «gemelle» **non** coincidono nel testo: «Qta'» e «UdM» sul
  preventivo, «Quantità» e «Unità di misura» su ordine e DDT. È il punto
  aperto del §8.7, lavoro FE;
- sull'ordine `data_consegna` = `data_consegna_confermata`, come approvato:
  la richiesta del cliente è nella vista ma non in lista (§8.7, aperto).

#### 8.11.2 Le prove, e cosa NON coprono

Tutte su `zeroerp_ci` come owner, in `BEGIN … ROLLBACK`, con l'SQL **estratto**
dagli YAML e il render offline dei cinque mirror (`20260507-06/-07/-08/-09`,
`20260806-15`) più il resync `90_end/20260602-17`:

| Prova | Esito |
| --- | --- |
| SQL dei dodici changeSet | passa; una sola funzione per nome; firme byte-identiche al vivo |
| equivalenza: formula vecchia e funzione su una griglia costruita di 252 casi (quantità, prezzi, sconti con scale diverse, NULL) | identiche nel valore **e nel testo**, anche la variante `/ 100.0` dei cruscotti |
| inlining | nel piano di `vw_ddt_righe_dettaglio` la chiamata non compare: c'è l'espressione |
| `plpgsql_check` sulle due plpgsql riscritte | zero errori |
| `security_invoker` | acceso sulle otto viste di vendite toccate |
| copie residue della formula in `vendite`/`script` | zero |
| mirror dei quattro CSV, upsert di **tutte** le righe | nessun rifiuto; i `campo_sorgente` esistono nelle viste; preset completi; `fn_resolve_lista_config` risponde per le cinque liste |
| i due pgTAP nuovi | 15/15 e 9/9 con l'SQL estratto; rossi senza; **mutazioni**: formula ricopiata a mano → rosso il 15; `ORDER BY` rimesso → rosso il 4 |
| 34 pgTAP esistenti che toccano gli oggetti, e i 16 di `ui` | **nessuna differenza** con e senza il blocco |

⚠️ **Cosa non dicono.** Lo scratch non ha i dati di base (emittenti, registri,
utility): 25 dei 34 file muoiono in fixture **in entrambe le corse**, quindi
per quei file il confronto è vuoto — fra questi quelli dell'imponibile di
fattura, del ricalcolo IVA del preventivo e dei cruscotti. La prova vera è la
corsa di Tid dopo l'apply. La RLS delle due viste nuove è coperta per criterio
(`security_invoker`), non esercitata con un operatore. Tre rossi di `ui` sullo
scratch (`multi-emittente` 6, `perimetro-emittente` 1,
`competenza-gruppi` 1) c'erano già **prima** di questo blocco.

⚠️ **Rosso atteso in CI, accettato da D-8.1:** `core/tests/test_ricerca_full_seed`
(`test_ogni_lista_ricercabile_e_registrata_o_in_debito`), finché il BE non
dichiara le `RicercaFull` delle cinque liste.

#### 8.11.3 Richieste al BE nate dal Blocco 1

1. **Repository sulle viste, proiezioni Python ritirate nello stesso giro:**
   `preventivi_repository.list_righe/get_riga` →
   `vw_preventivi_righe_dettaglio`; `ordini_repository.list_righe/get_riga` →
   `vw_ordini_righe_dettaglio` (⚠️ `get_riga` oggi non ha evaso e residuo:
   leggendo la vista li riceve); `ddt_repository.list_righe/get_riga` →
   `vw_ddt_righe_dettaglio`; `catalogo_bom_repository.list_componenti/get_componente`
   → `vw_articoli_componenti_dettaglio`, con il ritiro di
   `COMPONENTE_DETAIL_COLUMNS` e del commento «aggiornare ENTRAMBI». Il filtro
   `attivo IS TRUE` e l'ordinamento li mette il repository: le viste non filtrano
   e non ordinano.
2. **Endpoint di lista paginato + export** per le cinque liste (§4), con
   `lista_codice` sulla view Django; whitelist di ordinamento = le colonne con
   `ordinabile = t`; poi `scripts/gen_seed_lista.py --verifica-ordinamento`
   (va aggiunta la voce di ogni lista nella mappa del generatore).
3. **`RicercaFull`** per le cinque liste sulle colonne `ricercabile_full`
   (chiude il rosso atteso di `test_ricerca_full_seed`).
4. **Chiavi i18n gemelle** delle liste 1-3 (§8.7): scelta FE, poi il seed si
   riallinea.

#### 8.11.4 File che nel working tree NON sono di questo blocco

Al momento della consegna `git status` mostrava modificati, e non da questo
lavoro: `90_end/ci_apply/20260205-41-apply-runtime-grants-ci`, i pgTAP
`config/test-pannello-porta-v1` e `config/test-permessi-strutture-base`,
`dbzero/config/manual/aree_funzionali.md`, `scripts/sql/provision_db_roles.sql`,
il changeSet nuovo `90_end/20260928-30-revoke-app-scrittura-aree-funzionali` e
i brief del pannello config e del permesso nel verbo. Sono di un'altra sessione: non toccati, e da non
includere per errore nello stesso commit.

### 8.12 Blocco 2 — consegna DB (2026-09-28)

> ✅ **Migrato da Tid il 2026-09-28, pgTAP verdi, nessuna regressione.**

#### 8.12.1 Cosa c'è

| File | Cosa |
| --- | --- |
| `20_code/vendite/20260928-28-create-vw-fattura-righe-lista` | **nuova** `vendite.vw_fattura_righe_lista` (D-8.3): solo il livello 0 di `vw_fattura_righe_esposte`; `riga_key` (`R:<id>` per le righe vere, `K:<fattura>:<md5>` per il padre di un kit); `componenti` jsonb e `componenti_numero` sul padre; legame riga-riga della nota di credito con il numero **parlante** della fattura rettificata (`fn_numero_documento_fattura`); `security_invoker`; niente `ORDER BY` |
| `80_data/sql/ui/*.csv` (append) | lista 102 `vendite.fattura_righe` su `vw_fattura_righe_lista`, colonne 1056-1065, preset 102 |
| `db/pgtap/vendite/test-vw-fattura-righe-lista-v1.sql` | 13 test su una fattura **costruita** (`dbops.fn_pgtap_crea_fattura`): vale anche in CI |

⚠️ Numero `-28`: il primo buco libero del giorno (`-28/-29`), non un numero
oltre il massimo (`-30` è di un'altra sessione).

**Il seed della 102, e cosa non era nel §3.2:**

- le colonne del §3.2 con le loro priorità: `riga_nr` identificatore,
  `descrizione` 95, `quantita` 90, `importo_riga` 85 (etichetta
  «Imponibile», come il drawer), `prezzo_unitario` 70, `uom_codice` 60,
  `sconto_percentuale` 40, `iva` 30 (`campo_sorgente` `iva_descrizione`,
  gemella delle righe commerciali; la vista espone anche codice, aliquota e
  natura per il `formatIvaLabel` del FE);
- ➕ **`articolo_codice` a 50**: non era nel §3.2, ma la D-8.3 chiede la
  ricerca su codice e descrizione articolo, e una colonna è ricercabile solo se
  sta a catalogo. Il drawer di oggi lo mostra già, dentro la cella della
  descrizione. Chiave i18n `catalogo.articolo`;
- ➕ **`riga_rettificata` a 20** (`campo_sorgente` `riga_rettificata_documento`,
  chiave `vendite.fatture.col_rettifica_riga`, non ordinabile): è la colonna
  che il §8.3 dava per mancante. Il FE la compone con `riga_rettificata_nr`;
- nessuna colonna `azioni` (sola lettura, §3.2); `ordinabile = t` sulle altre,
  `ricercabile_full` su descrizione e codice articolo; `pagina_dimensione` 10;
  `ordinamento_default` NULL (l'ordine del documento lo dà il BE:
  `ordinamento, riga_nr, riga_key`). ⚠️ Le altre D-8.3 da ricordare: le
  PARTE_PLAFOND sono righe vere, e ordinando per importo possono separarsi.

#### 8.12.2 Le prove

| Prova | Esito |
| --- | --- |
| pgTAP nuovo, su `zeroerp_ci` col changeSet estratto | **13/13**; rosso senza la vista; **mutazione** (finestra senza l'IVA) → rossi 9 e 10 |
| piano con filtro per fattura | il filtro scende sotto la finestra fino alle righe della vista madre |
| confronto coi dati di dev, come app con contesto operatore e vista temporanea, in `ROLLBACK` | fatto datato (2026-09-28): 34 righe esposte, 29 di livello 0 (5 padri di kit), 5 componenti, 1 legame di nota di credito. La lista dà **29 righe, 29 chiavi diverse**; livello 0 del repository **meno** lista = 0; componenti del repository **meno** componenti nei padri = 0 |
| mirror dei quattro CSV (render offline) + resync | nessun rifiuto; `campo_sorgente` nella vista; preset completo; `fn_resolve_lista_config('vendite.fattura_righe')` → 10 colonne |
| 16 pgTAP di `ui` | nessuna differenza con e senza |

⚠️ **Rosso atteso in CI**, come per il Blocco 1 (D-8.1):
`test_ricerca_full_seed` anche per la 102, finché il BE non dichiara la sua
`RicercaFull`.

#### 8.12.3 Richieste al BE nate dal Blocco 2

1. **Nasce `GET fatture/<id>/righe/`** (lista paginata + export,
   `lista_codice = vendite.fattura_righe`) su `vw_fattura_righe_lista`, con
   `riga_key` come chiave di riga; ordine di partenza `ordinamento, riga_nr,
   riga_key`; whitelist = le colonne `ordinabile = t`; `RicercaFull` su
   `descrizione` e `articolo_codice`.
2. **`componenti`** (jsonb) nella riga di espansione dei `KIT_PADRE`: il FE
   non li chiede più con un'altra lettura.
3. **`vendite_repository.list_fattura_righe`**: ripete le join che la vista ora
   fa. Quando il drawer legge l'endpoint nuovo, `dettaglio.righe` va ritirato
   dal dettaglio (o letto dalla vista), nello stesso giro: due proiezioni delle
   stesse righe divergono. ⚠️ Il repository espone
   `riga_rettificata_fattura_numero` = il **contatore** della fattura (ambiguo:
   fattura 1 e nota 1 nello stesso anno); la vista dà
   `riga_rettificata_documento`, il numero parlante.

#### 8.12.4 Debiti registrati, non toccati

- **Costo della vista madre.** In `vw_fattura_righe_esposte` il CTE `kit` è
  usato due volte, quindi materializzato: il filtro per fattura non ci entra, e
  ogni lettura aggrega i kit di **tutte** le fatture. Succede già oggi al
  repository; la lista lo eredita. Da rivedere con la vista madre (un
  `LATERAL` per fattura, o il CTE inlineato), cantiere a sé.
- ~~**Il `COMMENT` della vista madre** dice che le due parti del plafond hanno
  lo stesso `riga_nr`~~ ⚠️ **ritirato il 2026-09-28 sera**: il `COMMENT` è
  giusto (ogni riga conserva il suo numero), l'avevo letto male. Nessun
  changeSet.

### 8.13 Blocco 3 — contratto: analisi prima di scrivere (2026-09-28)

> Letto sul contratto: corpo vivo di `vendite.fn_contratto_righe_preview`, i
> due guard di `contratti_righe`, il drawer `ContrattoRigheDrawer`. La
> D-8.13a si è sciolta sul modello (sotto): nessuna decisione pendente.

#### 8.13.1 La forma che ne esce (scelte tecniche, dentro la D-8.4)

- **Chiave di riga** dalla funzione: `L:<articolo>:<uom>` per le righe del
  listino (unicità di `uq_listini_righe_key_attiva`: versione, articolo, UoM),
  `A:<id>` per le AGGIUNTA (la loro riga di `contratti_righe`).
- **Azioni per riga**, oggi decise dal drawer in base all'origine:

  | origine | azioni |
  | --- | --- |
  | `DA_LISTINO` | sovrascrivi prezzo (click di riga), escludi |
  | `OVERRIDE` | modifica, ripristina il prezzo di listino |
  | `ESCLUSIONE` | modifica, ripristina l'articolo |
  | `AGGIUNTA` | modifica, rimuovi dal contratto |

  La funzione le restituisce (`azioni`, elenco dei verbi applicabili). ⭐ E c'è
  un caso di riga **spenta con un motivo**, che oggi il drawer non conosce:
  **«escludi» su un componente di un bundle** è rifiutato dal guard
  `trgfn_contratti_righe_guard_esclusione_figlio_bundle`
  (`E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA`) solo **dopo** il click. Per
  la §12.5 delle linee guida: una `fn_check_*` che nomina il motivo, letta dalla
  funzione **e chiamata dal guard** (il predicato in un posto solo).
- ⚠️ **Il blocco «fuori bozza» resta di documento**: lo applica il trigger
  condiviso `trgfn_doc_righe_lock_fuori_bozza`, e il drawer lo riceve già come
  sola lettura dalla capability del contratto. Ripeterlo su ogni riga sarebbe
  una seconda sede.

#### 8.13.2 Cose trovate

- **a) Un'AGGIUNTA su un articolo disattivato sparisce dalla lista.** Le parti
  2a/2b della funzione filtrano `catalogo.articoli.attivo = TRUE`; la riga
  resta in `contratti_righe`, ma nell'anteprima non c'è. Oggi il contratto
  **senza** listino la mostra (legge la tabella), quello **con** listino no.
  Con la lista che legge solo la funzione, sparirebbe in tutti e due i casi.
  ✅ **Smentito prima di chiederlo, sul modello:** `catalogo.articoli` ha
  `trg_articoli_a10_contratti_righe_block_deact_upd`
  (`dbops.trgfn_prevent_deactivate_if_children` su `contratti_righe`): un
  articolo usato da una riga di contratto attiva **non si può disattivare**. Il
  filtro della funzione è difesa, non un ramo raggiungibile. Nessuna decisione.
- **b) Un prezzo forzato vale per TUTTE le unità di misura dell'articolo.**
  Le righe del listino sono per articolo **e** UoM, le eccezioni solo per
  articolo (`uq_contrighe_one_eccezione_per_articolo`): la parte 1 unisce per
  articolo, quindi un OVERRIDE finisce sulle due righe di un articolo venduto
  in due UoM, con lo stesso prezzo. Domanda di dominio, **registrata, non
  bloccante** per questa lista.
- **c) La «versione operativa del listino» è scritta in sei funzioni**
  (anteprima contratto, righe espanse dell'offerta, risolutore prezzo, freeze,
  i due guard) e non dice sempre la stessa cosa: l'anteprima ne sceglie **una**
  (`ORDER BY stato = 'ATTIVA' DESC LIMIT 1`), i guard guardano **tutte** quelle
  valide oggi (`EXISTS`). Candidato a un building block a sé, con una
  decisione sulla semantica: **registrato**, fuori da questo cantiere.

#### 8.13.3 Consegna (2026-09-28)

> ✅ **Migrato da Tid il 2026-09-28, pgTAP verdi.**

| File | Cosa |
| --- | --- |
| `20_code/script/20260928-29-create-fn-check-esclusione-articolo-contratto` | **nuova** `script.fn_check_esclusione_articolo_contratto(contratto, articolo)`: `[]` o il motivo `FIGLIO_DI_BUNDLE` (codice a catalogo, `reason_key` `vendite.contratti.escludi_blocco.figlio_di_bundle`). Il predicato è quello del guard, **spostato** |
| `20_code/vendite/20260928-31-update-trgfn-contratti-righe-guard-esclusione-da-check` | il guard chiama la check e solleva il primo motivo (`fn_raise_primo_motivo_se_presente`); stesso codice e messaggio, trigger non toccato |
| `20_code/vendite/20260928-32-update-fn-contratto-righe-preview-chiave-e-azioni` | DROP + CREATE: in coda `riga_key`, `azioni text[]`, `escludi_blocco_codice`; firma e `RETURNS TABLE` ancorati da `20260604-03`; `GRANT` ridichiarato |
| `80_data/sql/ui/*.csv` (append) | lista 103 `vendite.contratto_righe` (colonne 1066-1075, preset 103), priorità del §7, `prezzo_forzato` su `override_prezzo`, `vista_sql` NULL (la sorgente è una funzione) |
| `db/pgtap/vendite/test-contratto-righe-lista-v1.sql` | 12 test, fixture **tutta costruita** (mondo, listino con versione BOZZA→ATTIVA, bundle in distinta e in listino, contratto, eccezioni) |
| `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql` | conteggio esatto da 25 a 26, con la nota datata |

⚠️ Numeri `-29`, `-31`, `-32`: il `-30` è di un'altra sessione.

#### 8.13.4 Le prove

| Prova | Esito |
| --- | --- |
| SQL dei tre changeSet su `zeroerp_ci`, in `ROLLBACK` | passa; una funzione per nome; le 19 colonne di prima **identiche** nei tipi risolti, più le 3 in coda |
| `plpgsql_check` su check, guard e anteprima | zero errori |
| rollback dei tre changeSet | ricompila la forma a 19 colonne, `plpgsql_check` pulito |
| pgTAP nuovo | **12/12**; mutazioni: anteprima che non chiama la check → rosso il 7; guard col predicato scritto dentro → rosso il 12 |
| pgTAP esistenti (tre sull'anteprima, quello del guard, il presidio dei riferimenti morti) e i 16 di `ui` | **nessuna differenza** con e senza; il rubinetto passa da rosso (senza: 25 ≠ 26) a verde (con) |
| seed (render offline dei mirror + resync) | nessun rifiuto; preset completo; `fn_resolve_lista_config('vendite.contratto_righe')` → 10 colonne; ogni `campo_sorgente` è una colonna della funzione |

⚠️ Sullo scratch due dei tre pgTAP vecchi dell'anteprima hanno rossi di fixture
(leggono BA e listini dal DB, stile vecchio) **in entrambe le corse**: per loro
fa fede la corsa di Tid.

#### 8.13.5 Richieste al BE / FE nate dal Blocco 3

1. ⛔ **Due chiavi i18n** nei locales (FE): `vendite.contratti.col_prezzo_forzato`
   («Prezzo forzato», intestazione della lista 103) e
   `vendite.contratti.escludi_blocco.figlio_di_bundle` (tooltip di «Escludi»
   spento). Fatto datato: **`check_i18n_keys` segnala già la prima** sul CSV, e
   gira come **pre-commit** sui CSV di `80_data`: senza la chiave il commit è
   bloccato. La seconda comparirà alla rigenerazione della doc auto-gen.
2. **Nasce `GET contratti/<id>/righe/`** (lista paginata + export,
   `lista_codice = vendite.contratto_righe`) su `fn_contratto_righe_preview`,
   con `riga_key` come chiave; ordine di partenza da decidere nel lotto (le
   righe dal listino non hanno un numero di riga: `articolo_codice` è il
   candidato); `RicercaFull` su codice e descrizione articolo. La lista 103 non
   ha vista: entra in `_ESERCIZI` di `test_lista_proiezione_campo_sorgente`
   (rosso atteso fino ad allora, D-8.1).
3. **Il drawer smette di decidere**: le azioni di riga dalla colonna `azioni`,
   «Escludi» spento con il tooltip da `escludi_blocco_codice`
   (`vendite.contratti.escludi_blocco.<reason in minuscolo>`); si ritirano
   `buildRigaActions`, la chiave sintetica `_row_key` e la doppia sorgente
   `righeIniziali`/anteprima.
4. Le domande registrate in §8.13.2 (prezzo forzato su più UoM, «versione
   operativa» in sei funzioni) **non** bloccano la lista: restano aperte.

### 8.14 Cosa resta (2026-09-28, dopo i tre blocchi DB)

I tre blocchi DB sono **migrati e verdi**. Resta questo, per sede.

#### 8.14.1 DB — da fare prima di chiudere il brief

> ✅ **Tutto fatto il 2026-09-28** (dettaglio nelle voci sotto e in §8.15-8.17).

1. ⭐ **La versione del listino in vigore in una sede sola** (§8.13.2 c).
   ✅ **Decisione di Tid, 2026-09-28: si sistema PRIMA di chiudere.**
   ✅ **Semantica decisa da Tid la sera stessa: «quelle valide oggi»**, e
   ✅ **si CHIUDE il buco che la renderebbe ambigua**: «non si può modificare
   una sequenza di date di listino, sarebbe un disastro».
   ⭐ **Perché le due semantiche oggi quasi coincidono, sul modello:** una
   versione passa ad ATTIVA → CHIUSA **solo** con `valido_al` già scaduto
   (`trgfn_listini_versioni_guard_transizione_stato`), e fra versioni ATTIVE non
   c'è sovrapposizione (`ex_listini_versioni_no_overlap`). Quindi oggi vale al
   più **una** versione. Il buco: **nessun guard blocca le date di una versione
   CHIUSA** (`trgfn_guard_date_validita` controlla solo la coerenza), quindi
   allungarne la fine dopo la chiusura la farebbe tornare «valida oggi» accanto
   all'ATTIVA — ed è l'unico caso in cui «una» e «tutte le valide» divergono.
   ⇒ Da fare: date di una versione CHIUSA **immutabili** (e l'esclusione delle
   sovrapposizioni estesa a CHIUSA, da valutare), poi il building block unico
   «versione in vigore» e il ritiro delle sei copie.
   ✅ **FATTO: migrato da Tid il 2026-09-28, pgTAP verdi** (§8.15). La regola
   «quale versione del listino vale oggi per questo contratto/documento» è
   scritta in sei funzioni (`fn_contratto_righe_preview`,
   `fn_offerta_righe_espanse`, `fn_resolve_prezzo_listino_v2_esito`,
   `trgfn_contratti_freeze_listino_versione` e la check/guard dell'esclusione e
   dell'aggiunta fuori listino), e non dice sempre la stessa cosa: l'anteprima
   ne sceglie **una** (ATTIVA prima di CHIUSA), i guard guardano **tutte** quelle
   valide oggi. Prima del codice serve la **decisione sulla semantica** (una
   sola versione o tutte le valide?), poi un building block unico e il ritiro
   delle sei copie nello stesso giro.
2. **Debiti registrati nel giro** (da decidere se entrano qui o in un cantiere
   a sé):
   - il prezzo forzato vale per tutte le UoM dell'articolo (§8.13.2 b),
     domanda di dominio. ✅ **Decisa da Tid il 2026-09-28 sera: va bene così**
     (riguarda solo il contratto; un prezzo forzato per articolo). Chiusa;
   - `vw_fattura_righe_esposte`: il CTE `kit` si calcola su tutte le fatture a
     ogni lettura (§8.12.4). ✅ **Tid: «dovremo sistemare» → SCRITTO il
     2026-09-28 (`20260928-43`, CTE `NOT MATERIALIZED`): §8.16.** ✅ Migrato, nessuna regressione;
   - ~~`vw_fattura_righe_esposte`: il `COMMENT` sul `riga_nr`~~ — ritirato:
     il `COMMENT` era giusto, lettura mia sbagliata (§8.12.4).
3. **Punti del §8.7:**
   - ✅ **data di consegna richiesta sull'ordine — decisa da Tid e FATTA il
     2026-09-28 sera**: colonna `data_consegna_richiesta_cliente` nella lista 98
     (id 1076, priorità 33, chiave `vendite.ordini.riga_data_consegna_richiesta_cliente`,
     già nei locales), e la colonna `data_consegna` passa a «Consegna
     confermata» (`vendite.ordini.riga_data_consegna_confermata`, già nei
     locales). Nessuna chiave nuova; provata col render dei mirror (11 colonne
     risolte). ✅ Migrata il 2026-09-28;
   - ✅ **`pagina_dimensione` — REGOLA NUOVA di Tid, 2026-09-28 sera: «15
     righe nei drawer», per TUTTE le liste dentro un drawer.** Era: 25 su
     desktop, 10 sotto `BREAKPOINTS.TABLET`, 10 fisse nei dialog
     (`frontend-standards` §«Righe per pagina default»); le liste righe nei
     drawer erano a 25 (69, 71, 74) e le sette nuove a 10. ⇒ DB: il preset di
     sistema di ogni lista montata in un drawer passa a 15 (censimento dal
     frontend, §8.15). ⇒ FE: la regola scritta in `frontend-standards` e,
     se serve, una costante (oggi `PAGINATION.COMPACT_ROWS` = 10) — richiesta.
     ✅ **Fatto e migrato il 2026-09-28 sera (seed), §8.15.4**; restano le
     richieste FE.
4. **Documentazione manuale** degli oggetti nuovi (`dbzero/<schema>/manual/`):
   ✅ **SCRITTA il 2026-09-28 sera** (§8.17): 7 schede nuove, 18 esistenti con
   una sezione «rev 2026-09-28» che rimanda alle sedi uniche. ⏳ Serve una
   **rigenerazione della doc auto-gen** perché le 7 pagine nuove includano la
   loro scheda (il generatore la aggancia solo se esiste quando gira).

#### 8.14.2 i18n — alla fine (decisione di Tid, 2026-09-28; «con le necessarie correzioni»)

✅ **FATTO il 2026-09-28 sera** (Tid: «ok procedi», dopo che la sessione DB
aveva chiesto il via per toccare `frontend/src/locales/`, fuori dal suo
perimetro):

- `vendite.contratti.col_prezzo_forzato` — «Prezzo forzato» / «Forced price»;
- `vendite.contratti.escludi_blocco.figlio_di_bundle` — «È un componente di un
  bundle del listino: si esclude il bundle intero, non il singolo componente.»
  (e l'inglese);
- **etichette gemelle**: l'unica a divergere era il preventivo, in due voci e
  nelle due lingue — `vendite.preventivi.riga_quantita` «Qta'» → «Quantità»
  («Qty» → «Quantity») e `riga_uom` «UdM» → «Unità di misura» («UoM» → «Unit
  of measure»), allineate a ordine e DDT. Nel seed l'etichetta di riserva della
  colonna `uom_codice` delle liste 97-99 passa a «Unita' di misura» (⏳ da
  migrare, mirror di `lista_colonna`).

`check_i18n_keys`: **tutto pulito**. I due JSON sono stati riscritti con un
giro lettura/scrittura verificato identico prima della modifica: il diff tocca
solo le righe cambiate.

- `vendite.contratti.col_prezzo_forzato` (intestazione della lista 103):
  ⚠️ `check_i18n_keys` gira come pre-commit sui CSV e la segnala già;
- `vendite.contratti.escludi_blocco.figlio_di_bundle` (tooltip di «Escludi»):
  comparirà alla rigenerazione della doc auto-gen;
- le etichette gemelle delle righe 1-3 (§8.7): oggi tre namespace con testi
  diversi («Qta'» / «Quantità», «UdM» / «Unità di misura»).

#### 8.14.3 BE (`dev/backend-tid`) — le richieste raccolte

Dettaglio in §8.11.3 (blocco 1), §8.12.3 (fattura), §8.13.5 (contratto), in
sintesi:

- repository delle righe di preventivo, ordine, DDT e BoM **sulle viste**, con
  il ritiro delle proiezioni Python nello stesso giro;
- endpoint di lista paginata + export per le sette liste (97-103), whitelist
  = colonne `ordinabile`, `RicercaFull` dichiarate; nascono
  `GET fatture/<id>/righe/` e `GET contratti/<id>/righe/`;
- registri dei presidi Django: `_RICERCHE` (oggi rosso atteso
  `test_ricerca_full_seed`) e `_ESERCIZI` per la lista 103, che non ha vista;
- `dettaglio.righe` della fattura da ritirare (o leggere dalla vista) quando
  il drawer passa all'endpoint;
- la lettura COMPLETA delle righe per i dialog di evasione e riconsegna (§4).

#### 8.14.4 FE — i lotti

- **L2** vendite 1-4 sul BB, **L3** fattura e BoM, **L4** contratto (§5): con
  le azioni di riga del contratto lette da `azioni` / `escludi_blocco_codice`
  e i componenti del kit dalla colonna `componenti`.
- **Documentazione del §6** (`frontend-standards`, catalogo BB, piano PrimeVue
  5, pagine API).

### 8.15 La versione del listino in vigore — lavoro (avviato il 2026-09-28)

**Decisioni di Tid (2026-09-28 sera):** semantica «le versioni valide oggi»;
il buco che la rende ambigua **si chiude** («non si può modificare una sequenza
di date di listino, sarebbe un disastro»).

**Censimento delle copie** (doc auto-gen, 2026-09-28): la regola «la versione
ATTIVA o CHIUSA, non BOZZA, attiva, la cui validità contiene la data» è
scritta **sette** volte in sei funzioni:

| Funzione | Data | Forma |
| --- | --- | --- |
| `vendite.fn_contratto_righe_preview` | oggi | una (`ORDER BY stato='ATTIVA' DESC LIMIT 1`) |
| `vendite.fn_offerta_righe_espanse` | oggi | una |
| `vendite.fn_resolve_prezzo_listino_v2_esito` (due punti) | `p_data_riferimento` | una |
| `vendite.trgfn_contratti_freeze_listino_versione` | oggi | una |
| `vendite.trgfn_contratti_righe_guard_aggiunta_fuori_listino` | oggi | tutte (`EXISTS`) |
| `script.fn_check_esclusione_articolo_contratto` | oggi | tutte (`EXISTS`) |

Altre tre funzioni leggono `listini_versioni` ma chiedono un'altra cosa (lo
stato della versione **scelta** per un'offerta, il perimetro): non sono copie.

**Il modello, e perché «una» e «tutte» oggi coincidono quasi sempre:**
ATTIVA → CHIUSA solo a `valido_al` scaduto; nessuna sovrapposizione fra
ATTIVE. Due buchi, entrambi ammessi dallo schema:

1. le **date di una versione CHIUSA** si possono cambiare dopo la chiusura
   (nessun guard): allungarne la fine la rende valida accanto all'ATTIVA;
2. una versione nuova può diventare ATTIVA con un `valido_dal` **nel passato**
   che copre il periodo di una CHIUSA: l'esclusione vale solo fra ATTIVE, e per
   una data passata (il risolutore del prezzo lavora su
   `p_data_riferimento`) le versioni valide diventano due.

⇒ **Il piano:**

- **a)** `ex_listini_versioni_no_overlap` esteso a `stato IN ('ATTIVA',
  'CHIUSA')` (stesso nome: il BE lo traduce per nome in
  `E_VENDITE_LISTINO_VERSIONE_OVERLAP`). Fatto datato: su dev, come operatore,
  **zero** coppie ATTIVA/CHIUSA sovrapposte su 31 versioni; il changeSet ha la
  sua `preCondition` sul conto, che al migrate gira come owner;
- **b)** date di una versione CHIUSA **immutabili**: guard `BEFORE UPDATE OF
  valido_dal, valido_al` con un codice nuovo (catalogo + messaggi; ⚠️ la
  policy BE in `error_policies.py` è una richiesta al BE, o
  `test_error_codes_db_policy_guardrail` è rosso);
- **c)** il building block `vendite.fn_listino_versione_in_vigore(listino,
  data)`: con a) e b) la risposta è **al più una** versione, quindi «una» e
  «tutte le valide» sono la stessa cosa per costruzione;
- **d)** le sei funzioni chiamano il building block; le sette copie si
  ritirano nello stesso giro.

#### 8.15.1 Consegna (2026-09-28)

> ✅ **Migrato da Tid il 2026-09-28, pgTAP verdi.**

| File | Cosa |
| --- | --- |
| `00_schema/vendite/20260928-33-alter-listini-versioni-no-overlap-attiva-chiusa` | `ex_listini_versioni_no_overlap` su `stato IN ('ATTIVA','CHIUSA')`, stesso nome; `preCondition` HALT sulle coppie già sovrapposte |
| `20_code/vendite/20260928-34-create-trgfn-listini-versioni-guard-date-chiusa` | guard + trigger `BEFORE UPDATE OF valido_dal, valido_al WHEN (OLD.stato = 'CHIUSA')`: rifiuta solo un cambio vero |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` (append) | `E_LISTINO_VERSIONE_CHIUSA_DATE_IMMUTABILI`, `CONFLITTO_STATO`, it/en (id 1142-1143) |
| `20_code/vendite/20260928-35-create-fn-listino-versione-in-vigore` | **la sede unica**: `vendite.fn_listino_versione_in_vigore(listino, data)`, al più una versione per costruzione, non ordina né limita |
| `20_code/script/20260928-36` … `20_code/vendite/20260928-41` | le sei funzioni la chiamano: check dell'esclusione, guard dell'aggiunta, congelamento all'attivazione, anteprima contratto, righe dell'offerta, risolutore del prezzo (due punti). Firme ancorate dagli ultimi YAML che le hanno (per il risolutore **`20260819-07`**: `20260829-45` l'aveva sciolta), `SECURITY INVOKER` esplicito |
| `80_data/changelog/20260928-42-update-automazione-overlap-listini-versioni-attiva-chiusa` | il registro `dbops.automazione_overlap` col predicato esteso, nella forma scritta nel DDL |
| `db/pgtap/vendite/test-listino-versione-in-vigore-v1.sql` | 13 test su un listino **costruito** (V1 attiva→chiusa, V2, una VX che prova a sovrapporsi) |

#### 8.15.2 Le prove

| Prova | Esito |
| --- | --- |
| SQL dei dieci changeSet su `zeroerp_ci`, in `ROLLBACK` | passa; firme **identiche** al vivo per le sei funzioni; una funzione per nome; `plpgsql_check` pulito |
| pgTAP nuovo (col blocco e i mirror dei codici resi offline) | **13/13**; mutazioni: vincolo solo-ATTIVA → rossi 2, 3, 8, 9, 10; trigger tolto → rosso 6; registro disallineato → rosso 3 |
| 56 pgTAP esistenti che toccano versioni, anteprime, risolutore, guard | **nessuna differenza** con e senza. ⚠️ Sullo scratch 29 girano verdi, 8 hanno rossi preesistenti, 19 si fermano in fixture in entrambe le corse — fra questi quasi tutti i test del risolutore (fixture vecchio stile) |
| ⭐ **equivalenza sui dati di dev**, come app col contesto, copie `pg_temp` delle funzioni nuove, in `ROLLBACK` | risolutore: **262 casi** (righe di preventivi e ordini, alla data del documento e a oggi), **0 differenze**, esiti vari (37 prezzi risolti); anteprima contratto: 24 contratti / 31 righe, **0**; righe dell'offerta: 10 offerte / 40 righe, **0**. Fatti datati |

#### 8.15.3 Richieste nate dal punto 1

- **BE**: la policy HTTP di `E_LISTINO_VERSIONE_CHIUSA_DATE_IMMUTABILI` in
  `error_policies.py` (409, come gli altri `CONFLITTO_STATO`), o
  `test_error_codes_db_policy_guardrail` è rosso quando la doc auto-gen
  rigenerata porta il codice nel corpo del guard;
- **FE**: il form della versione di listino non offre più le date su una
  versione CHIUSA (oggi il guard le rifiuterebbe dopo il click).

#### 8.15.4 La regola delle 15 righe nei drawer (Tid, 2026-09-28 sera)

Censimento dal frontend (`DrawerTabLista` / `useDrawerTabLista`, 2026-09-28):
**25 liste** montate **solo** dentro un drawer → preset di sistema a **15**
(`lista_preset.csv`, 18 righe esistenti + le 7 nuove): 19, 37, 54, 61, 62, 64,
65, 69, 71, 74, 81, 82, 84, 85, 86, 88, 89, 90, 97-103. Provato col render del
mirror: 25 liste si risolvono a 15; i 16 pgTAP di `ui` senza differenze (quelli
che fissano 25 riguardano liste di pagina, non toccate).

⚠️ **Fuori, e perché:**
- **nei dialog restano 10** (la regola scritta dei dialog non cambia):
  `magazzino.inventario_piano` (72), `pagamenti.rate` nel picker;
- **tre liste vivono sia in un drawer sia come pagina principale**, con **un**
  preset: `vendite.contratti` (drawer del BA), `vendite.giornale` (tab del
  giornale di un'entità), `catalogo.conversioni_uom` (drawer della UoM). Il
  preset resta a 25 per la pagina ⇒ **richiesta FE**: dove sono montate in un
  drawer, forzare 15 con l'opzione `limit` di `useDrawerTabLista`;
- **richiesta FE**: scrivere la regola in `frontend-standards` §«Righe per
  pagina default» (15 nei drawer, 10 nei dialog, 25/10 nelle pagine) ed
  eventualmente una costante `PAGINATION`.

### 8.16 Il costo della vista righe fattura (2026-09-28)

> ✅ **Migrato da Tid il 2026-09-28, nessuna regressione.**

`20_code/vendite/20260928-43-update-vw-fattura-righe-esposte-kit-not-materialized`:
il CTE `kit` di `vw_fattura_righe_esposte` diventa `NOT MATERIALIZED`. Letto da
due rami, era materializzato: calcolato su **tutte** le righe kit di **tutte**
le fatture a ogni lettura, e il filtro per fattura dei lettori non ci entrava.

- **I lettori filtrano tutti per fattura** (censimento del 2026-09-28):
  `vendite_repository.list_fattura_righe` e `vendite.vw_fattura_righe_lista`.
  Nessun altro lettore, né Python né DB;
- ⚠️ **il prezzo, dichiarato**: nel ramo dei componenti l'aggregato del kit si
  rivaluta per componente (in memoria, sulle sole righe di quella fattura);
  una lettura senza filtro lo calcolerebbe due volte — oggi non ce n'è.

| Prova | Esito |
| --- | --- |
| dev, come app col contesto, vista temporanea | righe 34 e 34, **0 differenze**; fattura 835: prima `CTE kit` = `Seq Scan` su 15 righe kit di tutte le fatture, 4,8 ms; dopo `Bitmap Index Scan` sulla fattura (9 righe), 1,75 ms (fatti datati) |
| `zeroerp_ci`, changeSet estratto | `security_invoker` resta; il rollback ripristina la forma materializzata |
| `test-vw-fattura-righe-lista-v1` (fattura con due kit **costruita**) | **14/14** col changeSet (test 14 nuovo: la forma); senza, rosso il 14 e le altre 13 identiche |

### 8.17 Documentazione manuale (2026-09-28 sera)

**Schede nuove** (`dbzero/<schema>/manual/`):
`script/fn_imponibile_riga`, `script/fn_check_esclusione_articolo_contratto`,
`vendite/fn_listino_versione_in_vigore`,
`vendite/trgfn_listini_versioni_guard_date_chiusa`,
`vendite/vw_ordini_righe_dettaglio`, `vendite/vw_ddt_righe_dettaglio`,
`vendite/vw_fattura_righe_lista`.

**Schede esistenti con la sezione «rev 2026-09-28»** (marcatore
`<!-- rev-2026-09-28-liste-righe -->`, che rende lo script idempotente): le
viste righe di preventivo e reso, le due viste IVA, i tre cruscotti, il
ricalcolo IVA del preventivo, il trigger dell'imponibile di fattura, la vista
della distinta, la vista righe esposte della fattura (con la nota di lettura
sul `riga_nr`), l'anteprima del contratto, i due guard e il congelamento del
contratto, le righe dell'offerta, il risolutore del prezzo, `listini_versioni`.
Ogni sezione **rimanda** alla sede unica (`fn_imponibile_riga`,
`fn_listino_versione_in_vigore`, la check dell'esclusione) invece di ripeterne
la regola.

⚠️ **Da sapere per il commit** (fatto datato: dopo la rigenerazione della doc di
Tid del 2026-09-28): `check_i18n_keys`, che gira come **pre-commit** su CSV e
doc auto-gen, segnala **due** chiavi, `vendite.contratti.escludi_blocco.figlio_di_bundle`
e `vendite.contratti.col_prezzo_forzato`. «Le chiavi i18n alla fine» (Tid)
vuol dire quindi: **prima del commit** di CSV e doc.
