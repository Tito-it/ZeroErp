# Brief DB — Seed delle liste ancora montate con `DataTable` grezza

> **Destinatari:** team DB (`dev/db-tid`). Il lavoro BE e FE che segue (§4) è
> di `dev/backend-tid` e **parte solo a seed applicati**: la conversione FE
> monta `<ListaConfigurabile codice="…">`, e senza le righe di catalogo la
> lista non ha colonne.
>
> **Tipo:** seed (`ui.lista_definizione` + `ui.lista_colonna`, e
> `ui.lista_preset`/`lista_preset_colonna` dove serve). Nessun DDL, salvo
> l'eventuale vista di §3.2.
>
> **Decisione:** di Tid, 2026-09-26 — *«correggere le DataTable grezze»*,
> partendo da quelle che sono liste vere per il criterio in tre domande
> ([piano PrimeVue 5](piano-migrazione-primevue-5.md), §«Gruppo B», «Il
> criterio, in tre domande»).
>
> **Stato:** ⏳ aperto.

---

## 1. Perché

`frontend-standards` §«Regola zero della lista»: una lista si monta con
`<ListaConfigurabile>`. La `DataTable` grezza è ammessa solo per le righe di un
documento, il dettaglio espanso della ricerca, la matrice slot/override e
l'anteprima in un dialog.

Il 2026-09-26 i 44 file con `DataTable` grezza sono stati riclassificati uno
per uno (da dove arrivano le righe, non dove sta la tabella). Esito:

- 10 sono eccezioni vere: commento di motivazione messo lo stesso giorno;
- 2 erano liste vere con seed ed endpoint già pronti: convertite lo stesso
  giorno (`ContrattiBillingAccountDrawer`, `UomConversioniDrawer`);
- **le liste qui sotto sono liste vere a cui manca il seed**. È questo brief.

⚠️ Tre di queste, oggi, **troncano in silenzio**: chiedono un numero fisso di
righe e non hanno paginatore (§2, colonna «Oggi»). La conversione chiude anche
quel difetto.

## 2. Richiesta al team DB — i seed

Per ciascuna riga: una `ui.lista_definizione` e le sue `ui.lista_colonna`. Le
bozze si generano con il generatore di progetto, che parte dal `.vue` di oggi
e non scrive sul DB:

```bash
backend/.venv/bin/python scripts/gen_seed_lista.py \
    --codice <codice> --descrizione "<descrizione>" \
    --vue <file .vue> [--vista <vista>]
```

Le colonne della bozza sono quelle che la `DataTable` mostra oggi. I campi
curati (priorità, gruppo, larghezza, sensibile) escono coi default e vanno
decisi: il generatore li elenca nel suo report.

| # | Codice proposto | `.vue` di partenza (sotto `frontend/src/`) | Righe da | Oggi |
|---|---|---|---|---|
| 1 | `core.sessioni_attive` | `core/components/SessioniAttivePanel.vue` | `GET /core/me/sessioni/` (`session_audit_repository.list_sessioni_attive`) | — |
| 2 | `documenti.documenti_sorgente` | `documenti/components/DocumentiGeneratiSorgenteList.vue` | `GET …/documenti/` (`sorgente_documenti_views`) | ⛔ tronca a 50 (`page_size` non passato) |
| 3 | `pratiche.flussi` | `pratiche/components/PraticaFlussiTab.vue` (la prima tabella, i flussi) | `GET /pratiche/{id}/flussi/` (`repo.list_flussi`) | — |
| 4 | `config.utilities_tipi_ruolo_usage` | `amministrazione/components/UtilityTipoRuoloDrawer.vue` (tab «Utilizzo») | `GET config/utilities-tipi-ruolo/<id>/usage/` | ⛔ tronca a 100 |
| 5 | `amm.reparti` | `amministrazione/views/RepartiProfiloView.vue` | `GET amm-software/reparti/` (`list_reparti`) | — |
| 6 | `documenti.template_versioni` | `config/components/TemplateVersioniSection.vue` | `GET …/templates/<id>/versioni/` (`documenti_repository.list_versioni`) | — |
| 7 | `vendite.preventivo_revisioni` | `vendite/preventivi/components/PreventiviDrawer.vue` (tab «Revisioni») | `GET preventivi/<id>/revisioni/` (legge `vw_preventivi_lista`) | — |
| 8 | `vendite.offerta_revisioni` | `vendite/offerte/components/OffertaDrawer.vue` (tab «Revisioni») | `GET offerte/<id>/revisioni/` | — vedi §3.2 |
| 9 | le 6 liste geografiche (`anagrafiche.regioni`, `.province`, `.stati`, `.comuni`, `.codici_postali`, `.toponomastica`) | i sei `*SearchTable.vue` di `anagrafiche/components/` che montano `GeoSearchTable` | i loro endpoint di lista | — |

⚠️ **Il codice è una proposta**: se il catalogo ha già una convenzione diversa
per quel dominio, vince il catalogo. Il codice scelto va riportato qui, perché
è quello che il FE scriverà nel `.vue`.

⚠️ Per 7 e 8 le colonne delle due revisioni vanno tenute **uguali**: sono lo
stesso tab su due documenti gemelli, e oggi le monta lo stesso BB
(`useRevisioniTab`).

## 3. Da decidere prima di seminare

### 3.1 Il giornale di un'entità (Storia di fattura e lotto)

`FatturaDrawer` (tab «Storia») e `LottoDrawer` (scheda Storia) mostrano la
**stessa** tabella grezza sulla stessa vista (`vw_giornale_entita`,
`GET …/giornale/`, già paginato). È una lista vera (Gruppo A) e sono due copie:
per la regola del 2 diventa **una** lista, per esempio `vendite.giornale_entita`,
montata da tutti e due i drawer. Serve l'ok di Tid sull'estrazione; poi il seed
entra in questo brief come riga 10.

### 3.2 Le revisioni dell'offerta

Il repository calcola la catena delle revisioni con una CTE ricorsiva scritta
nel backend (`offerte_repository.py`). Per paginarla in modo pulito conviene
una vista o una funzione DB che esponga la radice della catena, come per i
preventivi (che leggono già `vw_preventivi_lista WHERE numero = …`). Se il team
DB la ritiene giusta, la vista entra in questo brief insieme al seed della
riga 8.

## 4. Ricaduta BE e FE (`dev/backend-tid`, dopo i seed)

Non è del team DB: sta qui perché chi applica i seed sappia cosa aspetta.

| # | BE | FE |
|---|---|---|
| 1 | envelope `results` + `page`/`page_size` + whitelist di ordinamento; l'esclusione della sessione corrente si sposta dalla lista Python alla SQL, o la paginazione conta male | `<ListaConfigurabile>` nel pannello |
| 2 | whitelist di ordinamento; allineare `total_count` a quello che legge `useListaConfigurabilePage` | lo store serve 8 chiamanti: va adattato a `useDrawerTabLista` o affiancato |
| 3 | paginare `ApiPraticaFlussiList` + whitelist | `useDrawerTabLista` |
| 4 | whitelist `order_by`; lista e conteggio in **una** query (`fetch_paged_with_total`), oggi sono due | `useDrawerTabLista` |
| 5 | `list_reparti` paginata + whitelist + ricerca | `useListaConfigurabilePage` |
| 6 | `list_versioni` paginata + whitelist | `useDrawerTabLista`; il form sotto resta debito master-detail |
| 7 | paginare l'endpoint (LIMIT, conteggio, whitelist) | `useDrawerTabLista`; `useRevisioniTab` si ritira o si riduce |
| 8 | come 7, sulla vista di §3.2 | come 7 |
| 9 | whitelist sugli endpoint che non l'hanno | i sei wrapper passano a `<ListaConfigurabile>`; `GeoSearchTable` si ritira |

Prima di consegnare un lotto al BE: `python scripts/gen_seed_lista.py
--verifica-ordinamento <codice>` (una colonna `ordinabile=t` fuori whitelist è
una freccia che non ordina, senza errore).

## 5. Fuori da questo brief — decisioni di Tid aperte

Non sono seed, ma bloccano la chiusura del registro delle `DataTable` grezze:

- **`MatriceOverride` da estendere** per `EmittenteFiscaleUtilitiesTab`,
  `RepartoProfiloEditor`, `ImpostazioniSearchTable`: più colonne di override e
  un livello «ereditato» facoltativo;
- **`PermessiRiepilogoView`**: colonne dinamiche (una per area) in
  `ListaConfigurabile`, o vista ridisegnata;
- **`NoteDrawer`** e **`ArticoloUomDrawer`**: righe del documento o liste vere?
  (ArticoloUom, se resta righe, va comunque su `RigheMasterDetailTable`, di cui
  copia la macchina a stati);
- **`OffertaEccezioniDrawer`**: il piano la tiene in Gruppo A, ma è lo
  specchio di `ContrattoRigheDrawer`, che è in Gruppo B;
- **riga espansa di `ListiniSearchTable`** (versioni del listino): eccezione
  scritta o debito;
- **`AlertScadenzeWidget`**: lista propria, o anteprima di `vendite.listini`
  con un filtro «in scadenza»;
- **`SearchDrawer`** (ricerca universale): lista vera, oggi fuori catalogo;
- **tabella comune dei dialog di selezione** (evasione ordine, riconsegna
  reso, reso da DDT): stessa impalcatura sullo stesso BB
  `useRigheSelezioneQta`, candidata alla regola del 2.
