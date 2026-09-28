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
> - ✅ **L1 chiuso il 2026-09-28** (`dev/backend-tid`, non committato, via
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
>   «seed prima, BE dopo» (arma quattro presidi in CI); sette decisioni per Tid
>   in §8.9.

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
| `prezzo_unitario` | informazione | 70 |
| `uom_codice` | informazione | 60 |
| `tipo_erogazione` | informazione | 45 |
| `prezzo_listino` | informazione | 35 |
| `origine` | informazione | 30 |
| `azioni` | azione | — |

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

### 8.2 🟠 BoM globale: coerente col modello, incoerente col catalogo

`catalogo.articoli_componenti` non ha emittente, quindi `perimetro_emittente = f`
è la lettura giusta del modello. Ma la lista madre `catalogo.articoli` (26) e
le tre liste UoM (20-22) sono a `t`, e nemmeno quelle tabelle hanno un
emittente. Una delle due letture è sbagliata:

- o `f` è giusto, e le quattro liste di catalogo sono un debito dello stesso
  tipo delle sei geografiche corrette il 2026-09-27;
- o `t` ha una ragione che il seed non dice, e la BoM la eredita.

Se `f`: la BoM va aggiunta all'elenco di
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

### 8.6 🟡 Preventivo (1): una vista che nessuno legge

`vendite.vw_preventivi_righe_dettaglio` è la proiezione che il repository
**dice** di leggere («via vista», riga ~404), ma la query legge la tabella e
aggiunge `data_consegna_richiesta_cliente`, `stato_approvazione_prezzo`,
`pratica_approvazione_prezzo_id`, `is_composito_caso_a`, che la vista non ha.
La vista ha anche un `ORDER BY` nel corpo. Lettori: il solo
`db/pgtap/rls/test-rls-preventivi-satelliti.sql`.
Stessa scelta della BoM (D-8.6): o la vista diventa la sorgente, o si ritira
insieme al commento che la cita.

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

### 8.9 Decisioni per Tid

| # | Domanda | Raccomandazione |
| --- | --- | --- |
| D-8.1 | Seed e BE: giro unico (A) o seed spento (B)? | B |
| D-8.2 | BoM `perimetro_emittente`: `f` (e le 4 liste catalogo sono un debito) o `t`? | `f`, con il debito catalogo registrato |
| D-8.3 | Fattura: ordine fisso e nessuna colonna ordinabile? | sì |
| D-8.4 | Contratto: grana = `fn_contratto_righe_preview` per le due forme, con chiave e capability di riga dal DB? | sì |
| D-8.5 | BoM: vista al pari e `vista_sql` valorizzata? | sì |
| D-8.6 | `vw_preventivi_righe_dettaglio`: sorgente o ritiro? | sorgente, come D-8.5 |
| D-8.8 | `importo_riga` in una funzione: in questo cantiere o a parte? | a parte, registrato |
