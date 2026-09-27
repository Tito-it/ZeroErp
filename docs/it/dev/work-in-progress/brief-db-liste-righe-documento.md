# Brief DB — Le righe di un documento diventano liste standard

> **Destinatari:** team DB (`dev/db-tid`) per il §3; il lavoro BE e FE (§4-§6)
> è di `dev/backend-tid`. Il lotto **L1** parte subito (usa liste già a
> catalogo); **L2-L4 partono solo a seed applicati**.
>
> **Tipo:** seed (`ui.lista_definizione` + `ui.lista_colonna` +
> `ui.lista_preset`/`lista_preset_colonna`). Nessun DDL.
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
> - ⏸ **lavoro non ancora avviato**, per indicazione di Tid: né il seed né L1
>   partono finché Tid non dà il via.

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
