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
> - ⏸ **lavoro non ancora avviato**, per indicazione di Tid: né il seed né L1
>   partono finché Tid non dà il via;
> - 🔍 **verifica critica della parte DB il 2026-09-28: §8, da leggere per
>   primo.** Smentisce «Nessun DDL» (fattura, contratto, BoM) e l'ordine
>   «seed prima, BE dopo» (arma quattro presidi in CI);
> - ✅ **le sette decisioni di §8.9 sono PRESE da Tid lo stesso giorno**; il
>   lavoro DB che ne esce, in ordine, è in **§8.10**. ⏸ Sviluppo **non avviato**
>   («aggiorna il brief ma non iniziare lo sviluppo», Tid, 2026-09-28).

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

### 8.10 Il lavoro DB che ne esce, in ordine (non avviato)

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
