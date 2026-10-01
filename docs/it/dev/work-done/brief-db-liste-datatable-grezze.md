# Brief DB — Seed delle liste ancora montate con `DataTable` grezza

> **Destinatari:** team DB (`dev/db-tid`). Il lavoro BE e FE che segue (§4) è
> di `dev/backend-tid` e **parte solo a seed applicati**: la conversione FE
> monta `<ListaConfigurabile codice="…">`, e senza le righe di catalogo la
> lista non ha colonne.
>
> **Tipo:** seed (`ui.lista_definizione` + `ui.lista_colonna`, e
> `ui.lista_preset`/`lista_preset_colonna` dove serve). DDL solo per il §3.2
> (la catena delle revisioni dell'offerta).
>
> **Decisione:** di Tid, 2026-09-26 — *«correggere le DataTable grezze»*,
> partendo da quelle che sono liste vere per il criterio in tre domande
> ([piano PrimeVue 5](../work-in-progress/piano-migrazione-primevue-5.md), §«Gruppo B», «Il
> criterio, in tre domande»). §3.1 e §3.2 decisi da Tid il 2026-09-27.
>
> **Stato (2026-09-27):** lato DB scritto (§6). §3.1 risolto senza seed (si
> riusa `vendite.giornale`).
>
> - ✅ **§3.2 applicato** da Tid alle 00:34-00:36 (`20260927-03…-08`, nel
>   `databasechangelog`); verificati a DB: i due codici con la frase, il lock
>   rigenerato con le due colonne, l'indice sulla FK, la colonna nella vista con
>   `security_invoker=on`;
> - ✅ **seed delle righe 1-9 applicato** da Tid alle 01:00 (liste 83-96 e le
>   loro 69 colonne a DB), nella versione con `vista_sql` NULL su quattro
>   geografiche;
> - ✅ **§6.3 applicato** da Tid alle 01:08 (`20260927-30`, `-31`); verificati
>   a DB il 2026-09-27 (sessione BE): i due trigger cercano la vista in
>   `schema_dati` (e la definizione scatta anche su `UPDATE OF schema_dati`),
>   le quattro `config.vw_*_lista` con `security_invoker=on`, `vista_sql` su
>   tutte e sei le geografiche con ogni `campo_sorgente` presente nella vista,
>   lista 14 globale e 24 `multi_emittente`, messaggi 428/429 aggiornati; il
>   lock generato copre `revisione_padre_id` e `revisione_radice_id`, nessuna
>   radice NULL;
> - ✅ corsa pgTAP di Tid (§7) — dichiarata nel commit `55bbc1e10`;
> - ✅ giro BE/FE (§4) scritto il 2026-09-27, righe 1-10, non committato:
>   suite BE e FE verdi, registro delle `DataTable` grezze abbassato (8 in
>   meno, `GeoSearchTable` ritirato). Decisioni di Tid dello stesso giorno:
>   padre «documento + emittente» estratto in BB (regola del 2), PK
>   emittente esposta sul lotto, `useRevisioniTab.js` cancellato, NULLS come
>   da BB, reparti solo attivi;
> - ✅ **§9 lato DB applicato** da Tid alle 23:50 del 2026-09-27 (§9.4;
>   `20260927-42` EXECUTED, mirror dei CSV RERAN); verificati a DB la vista
>   con `provincia_id`/`provincia_sigla`, i cinque `ordinabile = t`, la 1010
>   visibile nel preset 95. Scritto così:
>   `20_code/config/20260927-42` (vista CAP con la provincia) e le righe dei
>   CSV `lista_colonna` / `lista_preset_colonna`. Al migrate `20_code` precede
>   `80_data`: la vista ha già `provincia_sigla` quando il CSV carica la
>   colonna 1010, che il trigger valida contro la vista;
> - ✅ corsa pgTAP di Tid dopo l'apply del §9: verde (2026-09-28);
> - ✅ **§9.3 lato BE chiuso il 2026-09-28** (`dev/backend-tid`, sopra il
>   merge del giro DB `a5538fb04`): `sigla_stato` in `_STATI_ORDER_COLS`;
>   `numero`/`stato_descrizione` e `codice`/`stato_descrizione` nelle due
>   costanti delle revisioni (gemelle, insieme); la lista CAP legge
>   `provincia_id`/`provincia_sigla` dalla vista e ordina per la sigla, e il
>   dettaglio `get_codice_postale` legge **la stessa vista** (non più un JOIN
>   suo). `gen_seed_lista.py --verifica-ordinamento` **ok** sulle quattro liste
>   (`config.stati`, `config.codici_postali`, `vendite.preventivo_revisioni`,
>   `vendite.offerta_revisioni`), presidi Django verdi (§9.5).
>
> ✅ **BRIEF CHIUSO il 2026-09-28** su DB, BE e FE. Le decisioni del §5 non
> sono di questo brief: vivono nel registro delle `DataTable` grezze del
> [piano PrimeVue 5](../work-in-progress/piano-migrazione-primevue-5.md).

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
# sul server DB il venv e' quello della radice (.venv): backend/.venv c'e' solo
# sul server backend. Le credenziali: DB_NAME/DB_USER nell'ambiente, o backend/.env
.venv/bin/python scripts/gen_seed_lista.py \
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

⭐ **Codici seminati (2026-09-27)** — sono questi che il FE scrive nel `.vue`:

| # | Codice | id lista/preset | colonne |
|---|---|---|---|
| 1 | `core.sessioni_attive` | 83 | 941-945 |
| 2 | `documenti.documenti_sorgente` | 84 | 946-952 |
| 3 | `pratiche.flussi` | 85 | 953-961 |
| 4 | `config.utilities_tipi_ruolo_usage` | 86 | 962-965 |
| 5 | `amm.reparti` | 87 | 966-969 |
| 6 | `documenti.template_versioni` | 88 | 970-977 |
| 7 | `vendite.preventivo_revisioni` | 89 | 978-984 |
| 8 | `vendite.offerta_revisioni` | 90 | 985-990 |
| 9 | ⚠️ **`config.regioni`**, **`config.province`**, **`config.stati`**, **`config.comuni`**, **`config.codici_postali`**, **`config.toponomastica`** | 91-96 | 991-1009 |

⚠️ Riga 9: il codice **non** è `anagrafiche.*` come proposto. Le sei tabelle
stanno in `config`, e nel catalogo il prefisso del codice è lo schema dei dati
in 80 liste su 81 (l'eccezione è `amm.processi`); le cinque `config.*` già a
catalogo sono montate anche loro dall'area FE amministrazione. Vince il
catalogo.

⚠️ Riga 1: `core.` resta (area FE) ma `schema_dati` è `dbops`: la tabella è
`dbops.sessioni_utente`, lo schema `core` non esiste. Stessa forma di
`amm.processi`.

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

✅ **Deciso da Tid il 2026-09-27: si riusa `vendite.giornale` (id 79). Nessun
seed nuovo.** La premessa di una lista a parte era «nella storia di un'entità
le colonne Entità/Riferimento sono ridondanti», ed era **falsa**: la storia del
lotto è per costruzione *il lotto più le sue fatture* (decisione di Tid del
2026-08-24), quindi mescola due entità e quelle colonne servono. Tolte quelle,
la lista nuova sarebbe uscita con le **stesse nove colonne** di
`vendite.giornale` — stessi codici, etichette, chiavi i18n, sulla stessa vista:
due definizioni dello stesso significato, cioè la copia che la regola del 2
vieta.

Cosa ne discende per BE e FE (sta nel §4, riga 10):

- i due endpoint per entità (`GET …/giornale/` di fattura e lotto) prendono il
  contratto di lista standard con `lista_codice = vendite.giornale`: oggi
  leggono `sort_by`/`sort_dir` e `page`/`page_size`, la lista manda
  `order_by`/`order_dir` e `limit`/`offset`. La whitelist
  (`GIORNALE_SORT_COLUMNS` = gravita, quando) copre già le due colonne
  ordinabili;
- `_aggiungi_entita_display` va chiamato anche dai due lettori per entità
  (oggi solo dal trasversale): senza, la colonna Riferimento esce vuota;
- ⚠️ **l'ordine di default cambia**: il preset di `vendite.giornale` ordina per
  `quando desc`, le due Storie di oggi per gravità. L'operatore può riordinare,
  ma il banner `erroreVivo` della fattura (`FatturaDrawer`), che oggi prende il
  primo ERROR della pagina ordinata per gravità, **non può più dipendere
  dall'ordine della pagina**: gli serve una fonte sua (per esempio un
  `exists` di un ERROR vivo, dal BE);
- FE: un componente unico con `<ListaConfigurabile codice="vendite.giornale">`
  montato dai due drawer; il filtro «solo problemi» (`info`) vale solo per il
  lotto; gli slot di cella si riusano da `GiornaleListView`. Diventano orfane
  e si ritirano `vendite.fatture.col_giornale_*`, `vendite.lotti.col_giornale_*`
  e `vendite.lotti.giornale_entita_*`; nel `LottoDrawer` va tolto il commento
  che dice che la storia non deve avere una definizione a catalogo.

### 3.2 Le revisioni dell'offerta

Il repository calcola la catena delle revisioni con una CTE ricorsiva scritta
nel backend (`offerte_repository.py`). Per paginarla in modo pulito conviene
una vista o una funzione DB che esponga la radice della catena, come per i
preventivi (che leggono già `vw_preventivi_lista WHERE numero = …`). Se il team
DB la ritiene giusta, la vista entra in questo brief insieme al seed della
riga 8.

✅ **Deciso da Tid il 2026-09-27: una colonna, non una vista ricorsiva.** La
catena delle revisioni è un fatto della riga, fissato alla nascita: si scrive
una volta e si legge per uguaglianza, come `numero` sui preventivi (UNIQUE
(numero, rev)). Una vista che la ricalcolasse a ogni lettura farebbe la stessa
ricorsione che oggi fa il backend, solo in un altro posto.

`vendite.offerte_commerciali.revisione_radice_id` — l'id della rev.1: su sé
stessa per la rev.1, ereditato dal padre per ogni revisione successiva.

- la **deriva** un trigger `BEFORE INSERT`
  (`trg_offerte_commerciali_a10_default_revisione_radice_ins`), non la madre
  `fn_crea_revisione_offerta`: un'offerta nasce anche da un INSERT diretto, e
  la radice deve valere per tutte. Un valore passato dal chiamante non conta;
- padre che sotto RLS non si vede (o non esiste): errore dichiarato
  `E_OFFERTA_REVISIONE_PADRE_NON_TROVATO`, non un 23502 sul NOT NULL;
- **immutabile** dopo la nascita, e con lei `revisione_padre_id`: due righe nel
  registro dei lock, codice `E_OFFERTA_REVISIONE_CATENA_IMMUTABILE`. Spostare
  il padre lascerebbe la radice a dire un'altra catena. Nessuno scrive
  `revisione_padre_id` in UPDATE oggi (censiti backend, changeSet, pgTAP);
- NOT NULL + FK sulla tabella stessa + indice via policy;
- esce da `vw_offerte_commerciali_lista` (ultima colonna).

Per il BE: il tab legge `vw_offerte_commerciali_lista v WHERE
v.revisione_radice_id = (SELECT revisione_radice_id FROM
vendite.offerte_commerciali WHERE id = %s)` — la stessa forma dei preventivi —
e la CTE ricorsiva di `offerte_repository.list_revisioni` si **ritira**.

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
| 10 | i due endpoint giornale per entità col contratto di lista (§3.1) | un componente unico su `vendite.giornale`, montato da `FatturaDrawer` e `LottoDrawer` |

Prima di consegnare un lotto al BE: `python scripts/gen_seed_lista.py
--verifica-ordinamento <codice>` (una colonna `ordinabile=t` fuori whitelist è
una freccia che non ordina, senza errore).

⚠️ **Fatto del 2026-09-27**: sulle 14 liste nuove il comando risponde «NON
MAPPATA» — le whitelist non esistono ancora, e la mappa `WHITELIST_BE` dello
script va estesa dal BE insieme alle costanti. In più lo script **non sa
leggere** le whitelist scritte con `colonne_identita(...)` (già oggi
`anagrafiche.indirizzi` esce «whitelist illeggibile»): le sei geografiche ci
cadrebbero. Va insegnata quella forma prima di consegnare. Le quattro
divergenze che il comando riporta oggi (`pagamenti.*`, «NUCLEO rotto») sono
preesistenti e non di questo brief.

### 4.1 Dettaglio per lista — whitelist, ricerca, cose da sapere

Chiave della whitelist = il `campo_sorgente` della colonna (è ciò che il FE
manda come `order_by`); ogni costante ha un tiebreaker fisso.

| # | Whitelist (colonna → espressione) | Ricerca (`RicercaFull`) | Da sapere |
|---|---|---|---|
| 1 | `ip_address`→`r.ip_address`, `data_ultimo_evento`→`r.data_insert`, `data_inizio`→`pl.data_inizio` (NULL = minimo, come da BB: in fondo in DESC, in testa in ASC); tie `r.jti` | `user_agent`, `ip_address::text` | l'esclusione della sessione corrente va nella SQL (`r.jti <> %s`), o il conteggio conta una riga in più. «Dispositivo» legge `user_agent`: il FE ne ricava browser/OS in una cella |
| 2 | `progressivo_sorgente`, `generato_at`, `titolo`, `nome_file`, `stato` su `d.*`; tie `d.id DESC` | `titolo`, `nome_file` | «Originale» legge `has_file_principale` (boolean). La view nasce da una factory che serve 8 sorgenti: il presidio `test_perimetro_emittente_copertura` non vede un `lista_codice` messo dalla factory — sottoclassi col codice scritto, o eccezione dichiarata al presidio |
| 3 | `sequenza`→`f.sequenza`, `template_flusso_descrizione`→`tf.descrizione`, `stato_descrizione`→`sf.descrizione`, `esito_descrizione`, `data_scadenza`, `risorsa_umana_display`, `unita_organizzativa_descrizione` (NULLS LAST), `data_insert`; tie `f.id` | `tf.descrizione` | ⛔ il `JOIN pratiche.pratiche` resta anche nel `COUNT`: `pratiche.flussi` non ha RLS, il perimetro lo decide la pratica. L'esito esce come descrizione, non più come codice grezzo |
| 4 | `emittente_codice`→`ef.codice`, `emittente_descrizione`→`s_ef.ragione_sociale_completa`, `emittente_attivo`→`ef.attivo`, `override_attivo`→`efu.attivo`; tie `ef.id` | `ef.codice`, ragione sociale | oggi la view «non accetta order_by»; lista e conteggio in una query (`fetch_paged_with_total`). Lista `multi_emittente` (§6) |
| 5 | `descrizione`→`uo.descrizione`, `codice`→`uo.codice`, `profilo_aree_count`, `operatori_count` (alias: SQL avvolta in una CTE); tie `uo.id` | `uo.descrizione`, `uo.codice` (soglia 1) | lista globale (`config.unita_organizzative`) |
| 6 | `versione`, `titolo`, `stato`, `valido_dal`, `valido_al`, `attivo`, `data_update` su `v.*`; tie `v.id` | `v.titolo` | il form sotto resta debito master-detail |
| 7 | `rev`→`v.rev` (default ASC), `data`→`v.data`, `totale_documento`; tie `v.id` | — | costante **nuova e separata** dalla lista principale |
| 8 | `revisione_numero`→`v.revisione_numero` (default ASC), `data_emissione` NULLS LAST; tie `v.id` | — | legge `vw_offerte_commerciali_lista` per radice (§3.2): lì ci sono anche `is_attiva` e `stato_descrizione`. ⛔ Non aggiungere `revisione_numero` a `_ORDER_COLS_OFFERTE`: lì è «volutamente ASSENTE» (§7.3 della lista principale) |
| 9 | le sei `colonne_identita(...)` di `geo_repository.py` coprono già tutto, **salvo `codice_iso3` sugli stati** (oggi la freccia ISO3 non ordina) | le ricerche scritte a mano passano a `add_ricerca_full_condition` | ⭐ `list_regioni`, `list_province_paginated`, `list_comuni`, `list_codici_postali` **leggono le viste `config.vw_*_lista`** al posto dei loro JOIN (§6.3); registrare le sei liste in `test_ricerca_full_seed` e `test_liste_configurabili_seed` |
| 10 | `GIORNALE_SORT_COLUMNS` copre già | — | vedi §3.1 |

**7 e 8, colonne gemelle.** Stessi codici, etichette, chiavi e ordine (`rev`,
`numero`, `data`, `stato`, `attiva`, più `stato_codice_interno` nascosta);
cambia solo il `campo_sorgente` (`rev`/`revisione_numero`, `numero`/`codice`,
`data`/`data_emissione`). Così il FE aggancia gli slot per codice
(`cell-${col.codice}`) con un template solo. `totale` c'è solo sulla 7:
l'offerta nel modello non ha un totale. ⚠️ `rev` dei preventivi parte da 0,
`revisione_numero` delle offerte da 1: a video lo si vede.

**Liste nei drawer e super admin (2, 7, 8).** Con `perimetro_emittente = t` e
`multi_emittente = f`, chi vede più emittenti riceve
`E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` dentro un drawer già aperto: la view deve
dichiarare `lista_emittente_param` e il FE passare l'emittente del documento.

**Due liste già a catalogo cambiano natura (§8 punto 7).**
`config.utilities_tipi_ruolo` (14) diventa **globale**: la sua view non chiede
più l'emittente, e il presidio BE `test_perimetro_emittente_copertura` va
allineato (`_ESENZIONI`). `documenti.template_documenti` (24) diventa
**`multi_emittente`**: il super admin la apre su «Tutti» e la colonna
`emittente_ragione_sociale` dice di chi è ogni riga — la view deve accettarlo.

**Chiavi i18n da aggiungere (FE, `it.json` + `en.json`).** Il seed le dichiara
già, quindi **`check_i18n_keys` in `ci-frontend` resta rosso finché non ci
sono** (controllo «intestazioni di colonna senza traduzione», 10 voci):
`vendite.revisioni.col_*` (`rev`, `numero`, `data`, `stato`, `attiva`, `totale`)
(namespace condiviso dalle due liste 7/8, come `vendite.lineage.*`),
`sessions.col_data_inizio`, `amministrazione.col_codice_reparto`,
`amministrazione.matrice_utilities_ruoli.usage_col_override_attivo`,
`indirizzi.col_provincia_nome`.

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

## 6. Lato DB — cosa è stato scritto (2026-09-27; tutto applicato)

### 6.1 Seed delle righe 1-9

Righe in coda ai quattro CSV di `80_data/sql/ui/` (i mirror `runOnChange` +
`validCheckSums: ANY` li caricano al prossimo migrate): 14 `lista_definizione`
(id 83-96), 69 `lista_colonna` (941-1009), 14 `lista_preset` di sistema di
default (stessi id delle liste), 69 `lista_preset_colonna`. `vista_sql` NULL
sulle righe 1-8; ⭐ **tutte e sei le geografiche dichiarano una vista** (§6.3):
`stati` e `toponomastica` la tabella stessa, le altre quattro una vista di
lista nuova — così il database valida ogni loro `campo_sorgente`.

Le bozze sono uscite dal generatore e sono state curate a mano lista per
lista: `campo_sorgente` = la chiave che il BE restituisce, colonne calcolate
dal FE ricondotte al campo BE vero, flag decisi sul contratto dell'endpoint.

| Flag | Liste | Perché (sul modello) |
|---|---|---|
| `perimetro_emittente = f` | 1, 5, le sei geografiche; ⭐ e la **14** (`config.utilities_tipi_ruolo`, già a catalogo) | una sessione è di un utente; reparti e geografia sono cataloghi senza emittente né RLS; la matrice utility / tipi ruolo è un vocabolario uguale per tutte le aziende (Tid, 2026-09-27) |
| `multi_emittente = t` | 4; ⭐ e la **24** (`documenti.template_documenti`, già a catalogo) | ogni riga è di UN emittente e la lista le mostra di aziende diverse; il biglietto è una colonna `emittente_*` attiva (`emittente_codice` sulla 4, `emittente_ragione_sociale` id 310 sulla 24, che c'era già) — Tid, 2026-09-27 |
| `ricerca_min_caratteri = 1` | 5, province, stati | si cerca su codici corti (sigla, ISO2) |

I due elenchi pgTAP che nominano le liste globali e le `multi_emittente`
(`db/pgtap/ui/test-lista-definizione-perimetro-emittente-v1.sql` test 6,
`…-multi-emittente-v1.sql` test 5) sono aggiornati con il motivo di ogni riga.

### 6.2 La catena delle revisioni dell'offerta (§3.2)

| changeSet | Cosa |
|---|---|
| `00_schema/vendite/20260927-03` | `offerte_commerciali.revisione_radice_id` bigint, nuda, col suo COMMENT |
| `20_code/vendite/20260927-04` | `vendite.trgfn_offerte_commerciali_default_revisione_radice()` + trigger `BEFORE INSERT` `trg_offerte_commerciali_a10_default_revisione_radice_ins` |
| `00_schema/vendite/20260927-05` | bonifica del pregresso (risalita ricorsiva), a trigger utente **sospesi e riaccesi** — solo quelli accesi: la radice non è una modifica del documento e non deve toccare audit né passare dai guard; si ferma se trova una catena senza rev.1 (ciclo) |
| `00_schema/vendite/20260927-06` | NOT NULL + `fk_offerte_commerciali_revisione_radice` |
| `20_code/vendite/20260927-07` | `vw_offerte_commerciali_lista` espone `revisione_radice_id` (ultima colonna, `security_invoker=on` ri-specificata; corpo dalla doc auto-gen, verificato identico alla vista viva) |
| `80_data/changelog/20260927-08` + `sql/vendite/fk_index_policy_revisione_radice.csv` | indice sulla FK a `consentito = true` (lo crea `apply_fk_index_policy()` in `90_end`) |
| `sql/dbops/automation_lock_columns.csv` | lock su `revisione_padre_id` e `revisione_radice_id` → `E_OFFERTA_REVISIONE_CATENA_IMMUTABILE` |
| `sql/config/codici_errore.csv`, `messaggi_errore.csv` (id 1140-1141) | `E_OFFERTA_REVISIONE_CATENA_IMMUTABILE` (CONFLITTO_STATO), `E_OFFERTA_REVISIONE_PADRE_NON_TROVATO` (NON_TROVATO, frase chiusa, senza bersaglio) |
| `db/pgtap/vendite/offerte_commerciali/test-offerte-revisione-radice.sql` | 13 test: struttura; la radice su rev.1, su una rev.1 con valore passato, su rev.2 e rev.3 dalla madre (⭐ il 7: la rev.3 prende la radice, non il padre); la vista; padre inesistente; il lock dichiarato e — se già generato, altrimenti `skip()` dichiarato — che rifiuta. ⛔ Fixture **costruita** (cliente/BA e listino dagli helper `dbops.fn_pgtap_crea_*`, emittente del contesto operatore): la prima versione li prendeva dal DB esistente e su `zeroerp_ci`, costruito da zero, moriva in ERRORE_FIXTURE (BA NULL) — corsa di Tid del 2026-09-27 |

⚠️ **Su dev dopo l'apply**: il trigger di lock lo genera il job
`automations_lock_columns` (o `CALL
maintenance.proc_automations_lock_columns_job()`); finché non gira, i test 11 e
12 del pgTAP nuovo fanno `skip()`.

⚠️ **Per il BE**: due codici errore nuovi nel catalogo, da riconoscere nella
tassonomia (`E_OFFERTA_REVISIONE_CATENA_IMMUTABILE` → 409,
`E_OFFERTA_REVISIONE_PADRE_NON_TROVATO` → 404).

### 6.3 La validazione del catalogo liste (§8 punti 6 e 7, Tid 2026-09-27)

| changeSet | Cosa |
|---|---|
| `20_code/ui/20260927-30` | i due trigger che validano il catalogo (`ui.trgfn_ui_lista_definizione_a10_valida_vista_sql`, `ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente`) cercano la vista **in `schema_dati`** e non più per solo nome; il trigger della definizione scatta anche su `UPDATE OF schema_dati`; il messaggio porta il nome qualificato `schema.vista`. Verificato prima di scriverlo: tutte le 18 liste con vista a catalogo l'hanno nel proprio schema, e ogni loro `campo_sorgente` (anche delle colonne spente) regge |
| `20_code/config/20260927-31` | quattro viste di lista: `config.vw_regioni_lista`, `vw_province_lista`, `vw_comuni_lista`, `vw_codici_postali_lista` — la proiezione di oggi di `geo_repository.py` più gli id dei filtri, `security_invoker=on`, GRANT all'app. `province.descrizione`/`sigla` sono `character(n)`: escono con TRIM (la lista comuni oggi dava la sigla con gli spazi in coda) |
| `sql/config/messaggi_errore.csv` (id 428, 429) | frase, causa e soluzione dicono che la vista si cerca nello schema della lista |
| `db/pgtap/ui/test-lista-colonna-campo-sorgente-in-vista-v1.sql` | 6 test: tutto il catalogo contro le viste nel loro schema; le sei geografiche con la vista; una vista che esiste solo in un altro schema rifiutata; un campo che esiste solo nella gemella `storico.comuni` rifiutato (skip dichiarato se la gemella non c'è) |

⛔ **Non** si è messa nel trigger della definizione la ri-validazione delle
colonne quando la lista cambia vista: il CSV delle definizioni si carica prima
di quello delle colonne, e un cambio di vista fatto insieme alle colonne
farebbe morire il migrate a metà. Quel buco (e quello di una vista che cambia
colonne) lo presidia il test 2 del pgTAP nuovo, sull'intero catalogo.

⛔ **Le quattro viste non sono viste «di validazione» accanto alla query**: il
repository le deve LEGGERE (§4.1 riga 9), altrimenti la vista e la query
possono divergere e il controllo passa su un oggetto che la lista non usa —
l'avvertenza di `backend/apps/core/tests/db/test_lista_proiezione_campo_sorgente.py`.

## 7. Prova e presidi

**Prova fatta (2026-09-27), su cluster PG18 usa-e-getta**, con l'SQL
**estratto** dai quattro changeSet `-03…-06` su una tabella minima con le
stesse colonne (le credenziali da owner di dbdev non erano disponibili). Esito:
pregresso con due catene e una singola bonificato giusto; `data_update` non
toccata; il trigger già spento resta spento, gli altri tornano accesi; rev.1
nuova → sé stessa; valore passato dal chiamante ignorato; figlia di una rev.3 →
radice della rev.1; padre inesistente → `E_OFFERTA_REVISIONE_PADRE_NON_TROVATO`;
NOT NULL in piedi; un ciclo nel pregresso ferma la bonifica con il suo
messaggio, e la transazione rimette i trigger com'erano.

**Cosa la prova NON copre** — resta alla corsa di Tid dopo l'apply: i trigger
veri della tabella (guard, lock generato), la RLS, la vista, `plpgsql_check`.

| Presidio | Cosa guardare |
|---|---|
| `db/pgtap/dbops/test-riferimenti-morti-v1.sql` test 2 | compila ogni funzione plpgsql: c'è una trigger function nuova |
| `db/pgtap/ui/test-lista-definizione-perimetro-emittente-v1.sql` test 6, `…-multi-emittente-v1.sql` test 5 | elenchi aggiornati (§6.1) |
| `db/pgtap/ui/test-liste-preset-default-v1.sql` | un preset di sistema di default per ogni lista: c'è |
| pgTAP della famiglia offerte (`db/pgtap/vendite/offerte_commerciali/`) | 107 INSERT sulla tabella in tutto il repo: nessuno passa la radice, la deriva il trigger |
| `scripts/check_i18n_keys.py` (ci-frontend) | ⛔ rosso con le 10 chiavi del §4.1 finché il FE non le aggiunge |
| `db/pgtap/ui/test-lista-colonna-campo-sorgente-in-vista-v1.sql` | nuovo (§6.3) |
| `db/pgtap/ui/test-lista-ricerca-min-caratteri-v1.sql` test 16 | elenco delle liste a soglia 1: aggiunte `amm.reparti`, `config.province`, `config.stati` (era rosso alla corsa di Tid del 2026-09-27, prima della correzione) |
| pgTAP che toccano i trigger di validazione (`test-lista-contratti-seed`, `test-fn-resolve-lista-config-contatore-colonne-nuove-v1`, `test-famiglie-documento-crud-v1`) | le loro liste di prova hanno la vista nel proprio schema: nessun cambio atteso |

## 8. Scelte fatte curando i seed — da confermare

Non bloccano l'apply; ognuna si cambia dal CSV. ✅ = decisa da Tid il
2026-09-27.

1. **IP delle sessioni non `sensibile`**: con `t` l'utente non vedrebbe più
   l'IP delle proprie sessioni senza permessi di colonna.
2. **Colonne nascoste aggiunte** dove il BE le restituisce già: `data_inizio`
   (sessioni), quattro sui flussi (note esito, operatore, reparto, data
   inserimento), `override_attivo` (4), `codice` (reparti), `data_update`
   (versioni), `sigla_stato`/`codice_telefonico` (stati),
   `provincia_descrizione` (comuni). Se si vuole un seed identico al `.vue` di
   oggi, si tolgono.
3. ✅ **Flussi: l'esito esce come descrizione** (`esito_descrizione`), come le
   altre liste, non più come codice grezzo — è già così nel seed.
4. **Revisioni: colonna `attiva` visibile di default** (nei preventivi lo stato
   non dice quale revisione è viva); `totale` solo sulla 7.
5. **Reparti**: la lista mostra solo gli attivi (il BE filtra `attivo = true`):
   decidere se servono anche i disattivati.
6. ✅ **`vista_sql` su tutte e sei le geografiche**: le quattro che leggevano
   con dei JOIN hanno ora una vista di lista vera, che il repository legge
   (§6.3).
7. Osservazioni emerse curando:
   - ✅ la lista 14 (`config.utilities_tipi_ruolo`) è **globale**
     (`perimetro_emittente = f`);
   - ✅ la 24 (`documenti.template_documenti`) è **certificata
     `multi_emittente`**;
   - ✅ i trigger che validano `vista_sql`/`campo_sorgente` cercano la vista
     **nel suo schema** (§6.3);
   - ✅ la lista CAP non restituisce la provincia, quindi due comuni omonimi
     non si distinguono: **deve mostrarla** (Tid, 2026-09-27) → §9.2.

## 9. Seguito — richiesta al team DB (Tid, 2026-09-27)

Emerso dal giro BE/FE del §4. Solo seed e una vista; il BE segue a seed
applicati (§9.3).

### 9.1 Colonne del nucleo rese ordinabili

`gen_seed_lista.py --verifica-ordinamento` dava «NUCLEO rotto» su tre liste:
una colonna identificativa o di stato con `ordinabile = f`. Decisione di Tid:
**si rendono ordinabili**. In `lista_colonna.csv`, `ordinabile` da `f` a `t`:

| id | Lista | Colonna | `campo_sorgente` |
| --- | --- | --- | --- |
| 1000 | 93 `config.stati` | `sigla_stato` | `sigla_stato` |
| 979 | 89 `vendite.preventivo_revisioni` | `numero` | `numero` |
| 981 | 89 `vendite.preventivo_revisioni` | `stato` | `stato_descrizione` |
| 986 | 90 `vendite.offerta_revisioni` | `numero` | `codice` |
| 988 | 90 `vendite.offerta_revisioni` | `stato` | `stato_descrizione` |

⚠️ 979/986 e 981/988 restano **gemelle** (§4.1 «7 e 8, colonne gemelle»): si
cambiano insieme.

### 9.2 La provincia nella lista CAP (`config.codici_postali`, 95)

Due comuni omonimi in province diverse oggi escono identici. Si chiede:

- `config.vw_codici_postali_lista` (corpo dalla doc auto-gen): in coda
  `c.provincia_id` e `TRIM(p.sigla) AS provincia_sigla`, con `LEFT JOIN
  config.province p ON p.id = c.provincia_id` (il comune può non avere la
  provincia: la riga del CAP non deve sparire). `security_invoker=on`
  ri-specificata. Stessa forma e stesso TRIM di `vw_comuni_lista`
  (`province.sigla` è `character(n)`);
- una `lista_colonna` per la 95: `provincia_sigla`, etichetta «Provincia»,
  chiave i18n `indirizzi.col_provincia` (già usata dalla colonna 1003 della
  lista comuni), `ordinabile = t`, `ricercabile_full = f`, gruppo
  «Territorio», dopo `comune`; e la sua `lista_preset_colonna` visibile nel
  preset di sistema 95.

### 9.3 Ricaduta BE (dev/backend-tid, dopo il seed)

- whitelist: `sigla_stato` in `_STATI_ORDER_COLS`; `numero` e
  `stato_descrizione` nelle due costanti delle revisioni
  (`PREVENTIVO_REVISIONI_ORDER_COLUMNS` su `v.numero`,
  `OFFERTA_REVISIONI_ORDER_COLUMNS` su `v.codice`, entrambe
  `stato_descrizione` su `v.stato_descrizione`);
- `geo_repository.list_codici_postali`: `provincia_sigla` nella proiezione e
  in `_CODICI_POSTALI_ORDER_COLS`; lo stesso nel dettaglio
  `get_codice_postale`;
- poi `--verifica-ordinamento` sulle quattro liste e i presidi
  `test_liste_configurabili_seed` / `test_lista_proiezione_campo_sorgente`.

### 9.4 Lato DB — cosa è stato scritto (2026-09-27, applicato alle 23:50)

| Dove | Cosa |
| --- | --- |
| `20_code/config/20260927-42` | `config.vw_codici_postali_lista`: in coda `c.provincia_id` e `TRIM(p.sigla) AS provincia_sigla`, `LEFT JOIN config.province` (`comuni.provincia_id` è nullable). Corpo dalla doc auto-gen, `security_invoker=on` ri-specificata, GRANT all'app ripetuto |
| `80_data/sql/ui/lista_colonna.csv` | `ordinabile` da `f` a `t` su 979, 981, 986, 988 (le gemelle insieme) e 1000; riga nuova **1010** sulla 95: `provincia_sigla`, «Provincia», `indirizzi.col_provincia`, gruppo «Territorio», `ordine_default` 30 (dopo `comune`), `ordinabile = t`, `ricercabile_full = f`, `filtrabile = f` come la gemella 1003 dei comuni |
| `80_data/sql/ui/lista_preset_colonna.csv` | `95,1010,30,t,f`: visibile nel preset di sistema 95 |

**Prova fatta (2026-09-27) su `zeroerp_ci`, da owner, SQL estratto dallo YAML
in transazione annullata:** la vista si ricrea con `security_invoker=on` e il
GRANT all'app; la riga 1010 passa il trigger `valida_campo_sorgente`, e un
`campo_sorgente` che la vista non ha è rifiutato con
`E_UI_CAMPO_SORGENTE_NON_TROVATO`; l'`UPDATE` dei cinque `ordinabile` passa;
un comune **costruito** senza provincia tiene la riga del suo CAP con
`provincia_sigla` NULL.

**Presidi:**

- `db/pgtap/ui/test-lista-colonna-campo-sorgente-in-vista-v1.sql` test 2
  (tutto il catalogo contro le viste) copre la 1010: nessun cambio al file;
- `gen_seed_lista.py --verifica-ordinamento` oggi è **KO sulle quattro liste
  per costruzione**: il seed promette ordinamenti che la whitelist BE non ha
  ancora. Si chiude con il §9.3. ⚠️ Il «NUCLEO rotto: stato» su
  `config.stati` è un match per sottostringa (`sigla_stato` contiene «stato»):
  si spegne con `sigla_stato` in whitelist, non indica una colonna di stato
  mancante;
- ⛔ `backend/apps/core/tests/test_liste_configurabili_seed.py`
  (`test_whitelist_copre_le_colonne_ordinabili`) legge **il CSV**, non il DB:
  diventa rosso sulle quattro liste **appena il CSV entra nel ramo**, non
  all'apply. ⇒ il §9.3 del BE va in `Tito-dev` **insieme** a questo giro DB
  (stessa PR o subito dopo, prima che giri la CI), non «a seed applicati».
  `test_lista_proiezione_campo_sorgente.py` invece non è toccato: esercita le
  liste **senza** vista, e la 95 ne ha una.

### 9.5 Lato BE — cosa è stato scritto (2026-09-28)

| Dove | Cosa |
| --- | --- |
| `anagrafiche/db/geo_repository.py` | `sigla_stato` in `_STATI_ORDER_COLS`; `provincia_sigla` in `_CODICI_POSTALI_ORDER_COLS`; `list_codici_postali` proietta `provincia_id`, `provincia_sigla`; `get_codice_postale` legge `config.vw_codici_postali_lista` — una sede della forma della riga CAP, non due |
| `vendite/db/preventivi_repository.py` | `PREVENTIVO_REVISIONI_ORDER_COLUMNS`: `numero` → `v.numero`, `stato_descrizione` → `v.stato_descrizione` |
| `vendite/db/offerte_repository.py` | `OFFERTA_REVISIONI_ORDER_COLUMNS`: `codice` → `v.codice`, `stato_descrizione` → `v.stato_descrizione`. ⛔ `_ORDER_COLS_OFFERTE` della lista principale non è toccata (§4.1 riga 8) |

Nessun cambio FE: la colonna 1010 la rende `ListaConfigurabile` dal seed, con
la chiave `indirizzi.col_provincia` già tradotta.
