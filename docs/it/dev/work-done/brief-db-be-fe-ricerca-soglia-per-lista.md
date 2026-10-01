# Brief DB · BE · FE — La soglia della ricerca è un fatto della lista

> **Destinatari:** team DB (`dev/db-tid`) per §1 e §4; backend e frontend
> (`dev/backend-tid`) per §5, **dopo** il DB.
>
> **Tipo:** brief di cantiere. Nasce il 2026-09-24 sera dalla chiusura di due
> brief che hanno portato la ricerca libera delle liste sul catalogo:
> [brief-be-ricerca-full-liste-residue](../work-done/brief-be-ricerca-full-liste-residue.md)
> e [brief-db-ricerca-full-colonne-da-accendere](../work-done/brief-db-ricerca-full-colonne-da-accendere.md).
> Quello che restava aperto in coda a entrambi era un argomento solo — **quanti
> caratteri servono per cercare, e chi lo decide** — più una richiesta di seed
> ancora da applicare (§1). Qui sono raccolti; il resto dei residui è in
> PROJECT_CONTEXT § «Aperto — Media priorità».
>
> **Stato 2026-09-24 sera:** §1 ✅ **scritta** dal team DB (seed, tre righe),
> da applicare. ⏳ Resta al **team DB** §4 (colonna, seed, lettura, pgTAP). BE
> e FE aspettano §4. La decisione di §6 a resta aperta per Tid e non blocca
> niente.
>
> **Stato 2026-09-25 notte:** §4 ✅ **scritta** dal team DB (`20260925-75` →
> `-78`, seed nel CSV principale, pgTAP nuovo 16/16 sull'SQL estratto) —
> **da leggere per primo: §4-bis**, che dice le scelte e cosa il BE legge.
> ⏳ Da applicare (`db-migrate`) e da far girare i pgTAP (Tid). Poi §5, BE e
> FE nello stesso giro.
>
> **Stato 2026-09-26:** ✅ **§1 e §4 applicate** su dbdev (`20260925-75` →
> `-78` alle 00:12, letto dal `databasechangelog`; righe 932-934 a
> `ordinabile = t`), **pgTAP verdi** (corsa di Tid). ✅ **Decise da Tid** le
> due scelte di §4-bis: `NOT NULL DEFAULT 3` e il BB `ui.fn_lista_da_codice`.
> **Il lato DB è chiuso.** ⏳ Tocca a **BE e FE**: §5, nello stesso giro.
>
> **Stato 2026-09-26 (pomeriggio):** ✅ **§5 scritta**, BE e FE nello stesso
> giro — esito in **§5-bis**. Suite BE 5400/5400 con E2E (2 skip), suite FE
> 354/354. ⏳ Resta a **Tid**: la prova a video («KG» su unità di misura) e le
> decisioni di §6, che non bloccano. Poi il brief va in `work-done/`.
>
> **Stato 2026-09-26 (sera):** ✅ **§6 a decisa da Tid: strada 2**, nessun 400
> sotto soglia sulle liste a catalogo — applicata nello stesso giorno
> (§6 a-bis). ✅ **§6 b decisa da Tid: strada 1** — il resolver soggetti usa
> la soglia a catalogo della lista che interroga; applicata lo stesso giorno
> (§6 b-bis), insieme a un difetto trovato strada facendo: la configurazione
> del resolver non era mai passata sul DB vero (cast `bigint[]` su un codice).
> **Nessuna decisione aperta.** ~~Resta la prova a video di Tid.~~ ✅ fatta, vedi sotto.
>
> **Stato 2026-09-26 (chiusura):** ✅ revisione critica del diff prima del
> commit, esito in **§8**: sei difetti corretti (fra cui la ricerca universale,
> che misurava la soglia sul testo non trimmato), l'elenco delle nature del
> resolver letto dall'enum, i mock del catalogo in una sede sola. **Brief
> chiuso e spostato in `work-done/`.** Suite BE 5022/5022 sulle app toccate con
> E2E (2 skip), FE 354/354.
>
> **Stato 2026-09-26 (collaudo):** ✅ **prova a video di Tid superata** — «KG»
> su unità di misura filtra, il resolver soggetti cerca dalla soglia della
> lista, i preventivi non ricaricano al 1° e 2° carattere (§8-bis). FE
> 360/360. **Cantiere chiuso.**

---

## 1. Richiesta al team DB — tre frecce di ordinamento ✅ scritta

> Ex brief DB `ricerca-full-colonne-da-accendere` §8 (2026-09-24 sera). ⚠️ Da
> applicare per prima: finché manca, la suite BE ha **due rossi**, ed è il
> segnale voluto, non un difetto del BE.
>
> ✅ **Fatto 2026-09-24 (team DB)**: `ordinabile = t` sulle righe 932, 933 e
> 934 di `80_data/sql/ui/lista_colonna.csv`. Nessun changeSet nuovo: il CSV lo
> ricaricano i due `loadUpdateData` con `runOnChange: true` già esistenti (il
> loader `20260507-07` e il mirror `20260806-15`). Controllato prima di
> scrivere: nessun UPDATE nei changelog riscrive `ordinabile`, nessun pgTAP
> fissa il valore di queste righe, e i tre `campo_sorgente` sono chiavi delle
> due `_ORDER_COLS`. ⏳ **Da applicare** (`db-migrate`), poi la suite BE deve
> tornare verde su
> `test_seed_offre_tutto_cio_che_il_backend_sa_ordinare`.

Convertite le liste al catalogo, la suite BE ha un rosso che viene dal seed:
`test_liste_configurabili_seed.test_seed_offre_tutto_cio_che_il_backend_sa_ordinare`
(sottocasi `vendite.promo_articoli` e `anagrafiche.categorie_clienti_listini`).

Il seed del 2026-09-24 aveva scelto `ordinabile = f` su tutte le righe nuove,
perché «`ordinabile = t` pretende la colonna nella whitelist di ordinamento del
repository». Per tre righe la whitelist **c'era già**, da prima di quel
cantiere:

| Riga | Lista · `campo_sorgente` | Whitelist BE che la ordina |
| --- | --- | --- |
| 932 | `vendite.promo_articoli` · `articolo_descrizione` | `promo_articoli_repository._ORDER_COLS` → `a.descrizione` |
| 933 | `anagrafiche.categorie_clienti_listini` · `categoria_descrizione` | `categorie_clienti_listini_repository._ORDER_COLS` → `cc.descrizione` |
| 934 | `anagrafiche.categorie_clienti_listini` · `listino_descrizione` | idem → `l.descrizione` |

**Richiesta**: `ordinabile = t` sulle tre righe di
`80_data/sql/ui/lista_colonna.csv` (dal CSV, linee guida SQL §11.2). Togliere
le colonne dalla whitelist vorrebbe dire spegnere una capacità che il BE ha
già: il test chiede proprio di non farlo. Le altre righe nuove (930, 931,
935-938) restano `ordinabile = f`, perché le loro whitelist non le conoscono.

## 2. Il difetto — la soglia «da un carattere» non arriva a video

Le liste di configurazione cercano da **un** carattere (decisione di Tid del
2026-09-23), ma solo **nel backend**. La soglia oggi vive in tre sedi che non
si conoscono:

| Sede | Forma |
| --- | --- |
| repository | `add_ricerca_full_condition(…, min_caratteri=1)`, quattordici chiamate |
| schema OpenAPI della view | `param_ricerca_full(min_caratteri=1)`, ripetuto per view |
| frontend | nessuna: manda il termine da `RICERCA.MIN_CARATTERI` (3) per ogni lista |

Quindi «KG» su unità di misura o «FT» sulle famiglie: la casella lo accetta, la
richiesta parte **senza** `search`, e la lista resta intera — senza nessun
errore. È un contratto dichiarato che nessun client esercita.

⭐ Il lato frontend della soglia ha già una sede sola dal 2026-09-24 (regola
del 2, ok Tid): `paramsRicerca(f, {minCaratteri})` e
`termineCorto(termine, {minCaratteri})` in `core/utils/listParams.js`, sulla
costante `RICERCA.MIN_CARATTERI`. Manca solo **da dove prendere
`minCaratteri` per ogni lista**.

## 3. Il modello — decisione di Tid del 2026-09-24

Quanti caratteri servono per cercare dipende da **cosa è la lista** (una tabella
di configurazione a codici corti, o un archivio che cresce), non da chi la
chiama. È una proprietà della lista, e le proprietà della lista stanno in
`ui.lista_definizione`: il catalogo diventa la sede unica della soglia, come lo
è già delle colonne.

Le strade valutate (ex brief BE §13.6):

1. ✅ **la soglia nella configurazione della lista**, da una colonna di
   `ui.lista_definizione`, letta anche dal BB al posto di `min_caratteri`;
2. ⛔ un'opzione dello store FE (`ricercaMinCaratteri: 1`) sulle liste di
   configurazione: rapida, ma è la quarta copia dello stesso fatto.

## 4. Richiesta al team DB

> Ex brief DB §9. La forma la sceglie il team DB, come per
> `fn_lista_colonne_ricerca_full`.

1. **colonna** in `ui.lista_definizione`, per esempio `ricerca_min_caratteri`
   `smallint NOT NULL`, `CHECK (ricerca_min_caratteri >= 1)`. Il default è la
   soglia di progetto, 3 (`RICERCA_MIN_CARATTERI` nel BE,
   `RICERCA.MIN_CARATTERI` nel FE). ⚠️ Scritto anche qui diventa la terza copia
   del numero: se il team preferisce `NULL` = «default di progetto» e il
   numero solo nel codice, al BE va bene lo stesso. Basta che la scelta sia una;
2. **seed** `80_data/sql/ui/lista_definizione.csv` (dal CSV, §11.2): **1**
   sulle liste di configurazione che oggi il BE chiama con `min_caratteri=1`:
   `catalogo.uom_tipi`, `catalogo.unita_misura`, `catalogo.conversioni_uom`,
   `config.tipi_ruolo_tipi_indirizzo`, `config.utilities_tipi_ruolo`,
   `config.email_account`, `config.email_template`,
   `anagrafiche.categorie_clienti`, `anagrafiche.categorie_clienti_listini`,
   `documenti.template_documenti`, `documenti.template_asset`,
   `vendite.registri_numerazione`, `vendite.famiglie_documento`,
   `amm.processi`. Tutte le altre al default;
3. **lettura**: il valore deve arrivare a **due** lettori, dalla stessa fonte:
   - la **configurazione della schermata**: nel jsonb di
     `ui.fn_resolve_lista_config`, accanto a `pagina_dimensione` (il FE la
     legge da lì, come `ricerca_full`);
   - il **BB di ricerca** del BE, che oggi legge solo
     `ui.fn_lista_colonne_ricerca_full(lista_codice)`: una colonna in più nel
     suo risultato, o una funzione piccola (`STABLE`, grant `zeroerp_app`).
     Scelta del team. ⚠️ Lista inesistente → lo stesso
     `E_UI_LISTA_NON_TROVATA` delle altre letture;
4. **pgTAP** col caso **costruito**: il `CHECK` rifiuta 0; una lista a 1 e una
   al default rispondono ciascuna col suo valore, in **entrambe** le letture.

## 4-bis. Esito del team DB — 2026-09-25 ✅ scritto, ✅ applicato il 2026-09-26

| Pezzo | Dove |
| --- | --- |
| colonna `ricerca_min_caratteri smallint NOT NULL DEFAULT 3`, `CHECK (>= 1)` | `00_schema/ui/20260925-75-alter-ui-lista-definizione-add-ricerca-min-caratteri` |
| BB `ui.fn_lista_da_codice(codice) RETURNS ui.lista_definizione` | `20_code/ui/20260925-76-create-fn-lista-da-codice` |
| il risolutore porta `ricerca_min_caratteri` nel jsonb, accanto a `pagina_dimensione`, e legge la lista dal BB | `20_code/ui/20260925-77-update-fn-resolve-lista-config-soglia-ricerca` |
| la ricerca libera legge la lista dal BB (contratto invariato) | `20_code/ui/20260925-78-update-fn-lista-colonne-ricerca-full-lista-dal-bb` |
| seed: colonna in coda a `80_data/sql/ui/lista_definizione.csv` (**1** sulle quattordici di §4.2, **3** sulle altre 68) + `- column:` nel mirror `20260507-06` | nessun changeSet nuovo: il mirror è `runOnChange` + `ANY` (linee guida SQL §11.2, «una tabella, un CSV») |
| note di `E_UI_LISTA_NON_TROVATA` in `codici_errore.csv` e `messaggi_errore.csv`: ora nominano il BB | mirror `20260614-08` |
| pgTAP `db/pgtap/ui/test-lista-ricerca-min-caratteri-v1.sql` (16 test) | — |
| doc manuale: `lista_definizione.md`, `fn_resolve_lista_config.md`, `fn_lista_colonne_ricerca_full.md`, **nuova** `fn_lista_da_codice.md` | `docs/it/dbzero/ui/manual/` |

**Le scelte, e perché** — ✅ entrambe confermate da Tid il 2026-09-26.

1. **`NOT NULL DEFAULT 3`, non `NULL` = «default di progetto».** Con il NULL
   ciascuno dei due lettori (schermata e BB di ricerca) avrebbe dovuto
   completarlo con la propria costante: due sedi che decidono lo stesso fatto.
   Con `NOT NULL` la risposta è una, già risolta, e **nessun lettore fa
   `COALESCE`**. Le costanti `RICERCA_MIN_CARATTERI` (BE) e
   `RICERCA.MIN_CARATTERI` (FE) restano solo per le ricerche che **non** sono
   una lista a catalogo (per esempio il resolver dei soggetti, §6 b). Il 3 nel
   CSV è una dichiarazione per lista, come `perimetro_emittente = t`.
2. **La lettura per il BE è un building block, non una colonna in più di
   `fn_lista_colonne_ricerca_full`.** La soglia è della lista, non delle
   colonne: ripeterla su ogni riga la farebbe sparire proprio quando le
   colonne ricercabili sono zero, e cambiare un `RETURNS TABLE` vuol dire
   `DROP`. ⭐ E «lista dal codice, o `E_UI_LISTA_NON_TROVATA`» era **già
   scritta due volte** (risolutore e ricerca libera): la soglia chiedeva un
   terzo lettore, quindi è nata la sede `ui.fn_lista_da_codice` e le due copie
   sono state ritirate nello stesso giro (regola del 2). Nel log l'errore ora lo
   firma il BB; codice, classe e frase sono gli stessi.
3. **`%TYPE` ri-ancorati.** `pg_get_functiondef` scioglie i `%TYPE` di firma e
   `RETURNS TABLE`: nei `-77`/`-78` sono stati rimessi (codice lista,
   `auth_user_id`, `emittente_fiscale_id`, le due colonne della ricerca, e
   `v_ordinamento`/`v_filtri`/`v_auth_user_id` nel `DECLARE`). Stessi tipi,
   stessa firma: `CREATE OR REPLACE` resta valido (verificato).

**Cosa legge il BE** (§5):

- la soglia: `SELECT ricerca_min_caratteri FROM ui.fn_lista_da_codice(%s)`
  — ⚠️ con `SELECT … FROM`: `SELECT ui.fn_lista_da_codice(%s)` dà la riga
  intera come una tupla in un campo solo;
- la configurazione della schermata: chiave `ricerca_min_caratteri` del jsonb
  di `ui.fn_resolve_lista_config` (un numero, non una stringa).

**Prove fatte (2026-09-25, su `zeroerp_ci` come owner, transazione ritirata,
SQL estratto dagli YAML):**

- pgTAP nuovo: 16/16, anche dopo il mirror **reso offline** (`updateSQL`) ed
  eseguito: 82 righe accettate, nessun'altra colonna cambiata, distribuzione
  `1=14`, `3=68`. Il mirror degli errori (reso offline anch'esso) passa per
  intero;
- pgTAP esistenti con e senza l'SQL estratto in testa, **esiti identici**:
  `test-fn-lista-colonne-ricerca-full-v1` 20/20, `test-fn-resolve-lista-config`
  13/13, `…-contatore-colonne-nuove-v1` 5/5, `…-preset-aggiornato-v1` 6/6,
  `test-lista-contratti-seed` 14/14, `dbops/test-riferimenti-morti-v1` 9/9,
  `config/test-fn-pannello-scrivi-v1` 14/14.
  `test-lista-definizione-multi-emittente-v1` (3/9) e
  `…-perimetro-emittente-v1` (7/8) sono rossi **già senza** le modifiche: da
  owner il guard del flag lascia scrivere, sono rossi per costruzione e verdi
  come app;
- `plpgsql_check` sulle tre funzioni: zero errori (il solo avviso «STABLE ma
  `PERFORM` volatile» è quello di `fn_log_and_raise_error`, già presente sulle
  due funzioni che lo chiamavano).
- ✅ La misura **come app**: corsa pgTAP di Tid dopo l'apply del 2026-09-26, verde.

⚠️ **Una cosa per il BE, da decidere, non bloccante.** `ui.lista_definizione`
si scrive anche dal CRUD di amministrazione (`lista_definizione_admin_service`,
e il pannello di configurazione, solo SUPER_ADMIN). La colonna **non** è
protetta come `multi_emittente`: un admin può cambiarla — ma il mirror la
riscrive dal CSV al migrate successivo, come già `descrizione` (è lo stesso
debito delle famiglie di documento in PROJECT_CONTEXT). Se si vuole esporla
dal CRUD, va prima deciso chi vince.

## 5. Dopo il DB — BE e FE, nello stesso giro

**Backend**

- `add_ricerca_full_condition` legge la soglia dal catalogo; l'argomento
  `min_caratteri` sparisce dalle quattordici chiamate. ⚠️ Oggi il BB legge il
  catalogo solo **sopra** soglia (aprire una lista senza cercare non costa
  niente): con la soglia nel catalogo la lettura parte a termine non vuoto.
  Una query leggera, e il frontend non manderà più termini corti;
- `param_ricerca_full` smette di dichiarare la soglia per view: dice «soglia
  dal catalogo della lista» (lo schema OpenAPI non può leggere il DB
  all'import);
- `get_lista_config_per_video` porta la soglia al FE (dal jsonb di §4.3);
- presidi: `test_ricerca_full_seed` (nessuna chiamata passa `min_caratteri`),
  `test_ricerca_full_db` (una lista a 1 filtra con un carattere, una al
  default no).

**Frontend**

- `useListaConfigurabilePage.onConfigLoaded` scrive la soglia nello store
  accanto a `ricercaFull` (dichiarata dallo stesso BB di stato,
  `useListaEmptyStateFetch`);
- `paramsRicerca` e `termineCorto` la ricevono come `minCaratteri`: nessun
  numero nuovo nel codice.

⛔ Fino ad allora i quattordici `min_caratteri=1` e i
`param_ricerca_full(min_caratteri=1)` restano dove sono: niente passo a metà.

## 5-bis. Esito BE e FE — 2026-09-26 ✅ scritto

**Backend**

| Pezzo | Dove |
| --- | --- |
| `soglia_ricerca(lista_codice)`: `SELECT ricerca_min_caratteri FROM ui.fn_lista_da_codice(%s)`, nessun ripiego (colonna `NOT NULL`) | `apps/core/db/_helpers.py` |
| `add_ricerca_full_condition` senza `min_caratteri`: termine vuoto o di soli spazi → **nessuna** lettura; sotto soglia → si legge la soglia, **non** le colonne | idem |
| i quattordici `min_caratteri=1` tolti dai repository | catalogo ×3, config ×2, anagrafiche ×2, documenti ×2, email ×2, famiglie, registri, processi |
| `param_ricerca_full(*, rifiuta_sotto_soglia=False)`: la frase dice «sotto la soglia della lista (`ricerca_min_caratteri` nella configurazione) non filtra»; i quattordici `param_ricerca_full(min_caratteri=1)` diventano `param_ricerca_full()` | `apps/core/api/openapi_params.py` + le view |
| la configurazione della schermata: **nessun codice nuovo** — `ricerca_min_caratteri` arriva già nel jsonb del risolutore, e `get_lista_config_per_video` lo porta così com'è | `apps/ui/services/ui_service.py` (solo il commento) |
| `RICERCA_MIN_CARATTERI` resta, **solo** per le ricerche che non sono una lista a catalogo (il 400 di `require_min_search_length`, i tool dell'assistente) | `_helpers.py`, commento riscritto |

Presidi: `test_ricerca_full_seed` — `test_nessuna_chiamata_dichiara_la_soglia`
(firma dei due BB **e** scansione AST di `apps/`: una chiamata col vecchio
argomento sarebbe un `TypeError` solo al primo operatore che cerca),
`test_bb_termine_vuoto_non_legge_niente`, `test_bb_la_soglia_e_quella_della_lista`;
`test_ricerca_full_db` — `test_la_soglia_e_della_lista_e_la_leggono_i_due_lettori`:
la **stessa** lista messa a 1 e poi a 3 nel test (caso costruito, non il seed)
filtra «K» solo nel primo caso, la configurazione per video porta ogni volta lo
stesso numero (intero), e una lista inesistente è `E_UI_LISTA_NON_TROVATA`. I
quattro test unitari che mockavano la sola lettura delle colonne mockano anche
la soglia. `test_seed_offre_tutto_cio_che_il_backend_sa_ordinare` è verde (§1).

**Frontend**

| Pezzo | Dove |
| --- | --- |
| `ricercaMinCaratteri = ref(null)` dichiarata accanto a `ricercaFull`; `fetchList` la usa per `termineCorto` e la passa a `buildParams` come **terzo argomento** (`{ minCaratteri }`) | `core/composables/useListaEmptyStateFetch.js` |
| `termineCorto`/`paramsRicerca`: `minCaratteri ?? RICERCA.MIN_CARATTERI` — ⚠️ `??` e non un default di parametro: lo store tiene `null`, e `length < null` manderebbe ogni lettera | `core/utils/listParams.js` |
| `paramsFiltro` legge lo stesso ref: fetch **ed export** con la stessa soglia | `core/composables/useListaStoreCore.js` |
| i cinque store scritti a mano (`distinte`, `codaRighe`, `rateFuoriCapienza`, `eccedenze`, `resiCoda`): `buildParams(f, _termine, ricerca)` → `paramsRicerca(f, ricerca)`, ed espongono `ricercaMinCaratteri` | `pagamenti/stores/`, `vendite/resi/stores/` |
| `onConfigLoaded` scrive la soglia (intero ≥ 1, altrimenti `null`) e **ricarica** se la soglia vera cambia il `search` che si manda — il deep-link `?search=KG` parte con la soglia di ripiego, prima della configurazione. Una fetch sola se cambiano insieme pagina e soglia | `core/composables/useListaConfigurabilePage.js` |

Presidi: `listParams.spec` (soglia `null`), `useListaStoreCore.spec` (15-17),
`pagamenti/stores/ricercaFull.spec` (la soglia arriva al `buildParams` scritto a
mano), e il **nuovo** `useListaConfigurabilePage.spec` (5 test: soglia dalla
configurazione, deep-link corto ricaricato, nessuna ricarica senza termine o a
soglia invariata, una fetch sola).

Doc: cataloghi BB (backend `add_ricerca_full_condition` e `param_ricerca_full`,
frontend `useListaEmptyStateFetch` e `listParams`), `frontend-standards`
§ricerca, `api.md` §Ricerca, `Policy-ricerca-e-paginazione` §2.1.

⚠️ **Cosa NON è cambiato, e perché** — da leggere con §6:

- ~~i **400** sotto soglia restano sulla soglia di progetto~~ → ✅ chiuso da
  §6 a (sera del 2026-09-26): tolti, vedi §6 a-bis;
- i **tool dell'assistente** rifiutano sotto `RICERCA_MIN_CARATTERI` prima di
  chiamare il service, anche su liste a catalogo: stessa natura del punto
  sopra, oggi tutte le liste che interrogano sono a 3;
- l'export della **coda resi** (`ResiCodaTable.buildExportParams`) manda il
  termine della casella senza soglia, da prima di questo cantiere: il backend lo
  ignora sotto la soglia della lista, quindi il file coincide con la videata;
- il **CRUD admin** della colonna (§4-bis, «chi vince» fra admin e mirror CSV):
  non esposto.

## 6. Decisioni aperte per Tid — non bloccano §4

**a. Sotto soglia, sulle liste NON di configurazione: 400 o termine ignorato?**
(ex brief BE §6). Oggi convivono due comportamenti:

| Comportamento | Dove |
| --- | --- |
| **400** `E_SEARCH_VALIDATION` (`require_min_search_length`) | testate e disponibilità di magazzino, anagrafiche di magazzino, `catalogo.articoli`, `vendite.listini`, `pagamenti.rate` (`saldi_service`) |
| **ignorato** (il BB non filtra) | le dieci liste di vendite e tutte le altre sul BB senza 400 nella view |

Il frontend manda il termine a ogni tasto (`useSearchTable`): il 400 durante la
digitazione va guardato a video prima di sceglierlo. ⭐ Con la soglia nel
catalogo la domanda cambia forma: il frontend non manda più un termine sotto
la soglia **della lista**, quindi il 400 diventa una difesa contro un client che
non legge la configurazione, non un evento della digitazione. Fino alla
decisione i 400 esistenti **restano** nelle view.

**✅ Decisa da Tid il 2026-09-26: strada 2 — il termine sotto soglia si
ignora, nessun 400 sulle liste a catalogo.** Il perché: la domanda «il
termine è troppo corto?» ha già una sede, la soglia del catalogo applicata dal
BB; un controllo nella view ne è una seconda, e il frontend non manda più
termini corti, quindi il 400 non protegge l'operatore. Una regola sola per
tutte le liste.

**§6 a-bis. Esito — 2026-09-26 ✅ scritto**

| Lista | Dove era il 400 |
| --- | --- |
| `catalogo.articoli` | `ApiArticoliList.get` |
| `vendite.listini` | `ApiListiniList.get` |
| `pagamenti.rate` | `saldi_service.list_rate` |
| testate `magazzino.inventari` / `magazzino.rettifiche` | `magazzino/api/views._filtri_documenti` |
| `magazzino.disponibilita` / `…_articoli` | `magazzino/api/views._filtri_disponibilita` |
| `magazzino.magazzini` / `ubicazioni` / `lotti` | `magazzino/api/views_anagrafiche._filtri_anagrafica` |

- `param_ricerca_full` perde l'opzione `rifiuta_sotto_soglia` (nessun
  consumatore): lo schema OpenAPI di ogni lista dice la stessa frase;
- tre test rovesciati: il termine corto arriva al service/repository con un
  200 (`test_list_articoli_search_corta_non_e_un_errore`,
  `test_ricerca_corta_non_e_un_errore` in rate e magazzino);
- ⛔ **restano** col 400, perché non sono liste a catalogo: la ricerca
  universale (`search_view`), il lookup articoli per autocomplete e il lookup
  delle risorse umane. Per questi `RICERCA_MIN_CARATTERI` resta la soglia;
- i **tool dell'assistente** rifiutano ancora il termine corto prima di
  chiamare il service: non è un 400 HTTP ma un errore azionabile per il
  modello (`ai_assistant/tools/base.py`), fuori dal perimetro di questa
  decisione. ➡️ Annotato in
  [integrazione-ai-sviluppo-v2](../work-in-progress/integrazione-ai-sviluppo-v2.md)
  § «Debiti dei tool esistenti»: il guard resta, la soglia va letta dalla lista.

**b. `MIN_SEARCH_LENGTH_SOGGETTI = 3`** (ex brief BE §13.3 f) in
`anagrafiche/db/soggetti_repository.py`: la soglia della ricerca soggetti del
`SoggettoResolver`, esposta al FE dal resolver (`min_search_length`,
`SoggettoResolver.vue`). Stesso valore di `RICERCA_MIN_CARATTERI`, seconda
sede. ⚠️ Il resolver **non** è una lista a catalogo, quindi §4 non la copre. Da
decidere se legge `RICERCA_MIN_CARATTERI` (e il FE `RICERCA.MIN_CARATTERI`) o se
è una soglia sua, e allora con un nome che lo dica.

## 7. Ordine

1. ✅ **Team DB**: §4 scritta il 2026-09-25 (§4-bis), coi pgTAP; §1 scritta il
   2026-09-24. ✅ Applicate entrambe il 2026-09-26, pgTAP verdi.
2. ✅ **BE + FE**: §5, nello stesso giro — scritto il 2026-09-26 (§5-bis).
   ✅ Prova a video di Tid superata il 2026-09-26 (§9). Era: **sbloccato**. Il BE legge la soglia
   con `SELECT ricerca_min_caratteri FROM ui.fn_lista_da_codice(%s)` e la
   passa al FE dalla chiave `ricerca_min_caratteri` del jsonb del risolutore
   (§4-bis). Con §1 applicata, `test_seed_offre_tutto_cio_che_il_backend_sa_ordinare`
   deve tornare verde.
3. ✅ **Tid**: §6 a (strada 2) e §6 b (strada 1) decise e applicate il
   2026-09-26. ✅ Prova a video superata lo stesso giorno (§9).

Fine cantiere: nessuna chiamata al BB passa `min_caratteri`, nessuna view
dichiara la soglia a mano, e «KG» su unità di misura filtra a video.

## 6 b-bis. Esito — 2026-09-26 ✅ scritto

**Decisione di Tid: strada 1.** Il brief diceva «il resolver non è una lista a
catalogo, quindi §4 non lo copre». Il codice dice altro: il `SoggettoResolver`
cerca con `listSoggetti`, cioè con la lista `anagrafiche.soggetti`, e quindi
col BB che applica la soglia a catalogo di quella lista. Due soglie decidevano
la stessa ricerca, e con quella del resolver più bassa la lista inline avrebbe
proposto i primi soggetti **non filtrati** come suggerimenti.

| Pezzo | Dove |
| --- | --- |
| `min_search_length` della configurazione del resolver = `soglia_ricerca(_RICERCA_SOGGETTI.lista_codice)`; `MIN_SEARCH_LENGTH_SOGGETTI` ritirata | `anagrafiche/db/soggetti_repository.py` |
| il componente: ripiego `RICERCA.MIN_CARATTERI` invece di `?? 3`; la soglia si misura sul termine **trimmato** con `termineCorto` (« ab» erano tre caratteri nella casella e due per il BB) e si manda il termine trimmato | `core/components/SoggettoResolver.vue` |
| il placeholder dice la soglia vera: «Digita almeno {n} caratteri...» | `locales/it.json`, `en.json` |

⚠️ **Difetto trovato strada facendo, e corretto**: `get_config_resolver`
filtrava i tipi di dettaglio con `%s::bigint[]`, ma `config.tipi_soggetto.id`
è un `varchar(10)` (`PF`, `PG`, `ENC`). Su ogni ruolo con la matrice delle
nature valorizzata — tutti quelli del seed — la query falliva; i test unitari,
con la connessione mockata, non potevano vederlo. Ora `varchar[]`. A video il
resolver ripiegava in silenzio: nessuna natura, nessun tipo di dettaglio,
soglia 3.

Presidi: `test_config_resolver` (la soglia arriva dalla lettura del catalogo,
chiamata col codice della lista soggetti), e `test_ricerca_full_db` test 8, sul
DB vero: la lista soggetti messa a 5 nel test, la configurazione del resolver
risponde 5 **e** porta i tipi di dettaglio (presidio del cast).

## 8. Revisione critica prima del commit — 2026-09-26 ✅ scritta

Una lettura del diff completo (BE, FE, test) cercando difetti, copie e numeri
scritti a mano. Il trasporto della soglia è risultato completo: ogni
`paramsRicerca`/`termineCorto` la riceve, ogni `buildParams` scritto a mano la
inoltra, e i cinque store costruiti su `useListaEmptyStateFetch` che non la
ricevono (`canaliIncasso`, `codeJobs`, `fondiFatturaDaDecidere`, `lotti`,
`approvazioniPrezzo`) non hanno ricerca testuale.

**Difetti corretti**

| # | Difetto | Dove | Correzione |
| --- | --- | --- | --- |
| 1 | Con la soglia a catalogo `{n}` può valere 1: «Digita almeno 1 caratteri» | `SoggettoResolver.vue`, `locales/*.json` | plurale `1 carattere \| {n} caratteri`, `t(key, n, { n })` come nel resto del progetto |
| 2 | Ricerca universale: `3` scritto due volte, e soglia misurata sul testo **non** trimmato mentre il backend fa `strip` — « ab» passava il frontend e prendeva un 400. Lo stesso difetto di §6 b-bis, nel componente accanto | `core/components/SearchDrawer.vue` | `termineCorto` sul termine trimmato (soglia di progetto: non è una lista a catalogo), `q` trimmato; `search.min_chars` dice `{n}` da `RICERCA.MIN_CARATTERI` |
| 3 | `min_length=3` scritto accanto a un default che è già `RICERCA_MIN_CARATTERI` | `core/api/search_view.py`, `core/api/examples/domain_search_example.py` (un esempio si ricopia) | tolto: vale il default |
| 4 | Commento falso: «la view risponde ancora 400, decisione aperta» | `catalogo_repository.list_articoli` | riscritto: nessun 400 (§6 a) |
| 5 | Il `min_caratteri=1` sparito dal codice restava in una decina di commenti al presente («cerca da un carattere»): la seconda sede che il brief ritira, falsa al primo cambio di catalogo | repository e view di configurazione | «la soglia la dichiara il catalogo della lista»; le decisioni restano, datate |
| 6 | Righe di commento oltre 100 caratteri, tre righe vuote dopo un import tolto | view di magazzino, rate, listini, articoli; `openapi_params.py` | riavvolte |

**Da decidere, deciso e fatto (ok Tid, stesso giorno)**

- **Le nature del resolver senza matrice.** `get_config_resolver` rispondeva
  `["PF", "PG", "ENTE"]` scritto nel codice quando il ruolo non ha righe in
  `tipi_ruoli_nature_ammesse` («tutte le nature»): una seconda sede dell'enum
  `config.natura_soggetto_enum`, che una natura nuova avrebbe lasciato indietro
  senza errore. Ora si legge il dominio:
  `SELECT unnest(enum_range(NULL::config.natura_soggetto_enum))::text`, nell'ordine
  di dichiarazione. Presidi: `test_config_resolver` 3 (una natura che il codice
  non conosce arriva) e `test_ricerca_full_db` 8 (lo stesso ruolo con la matrice
  spenta nel test risponde col dominio, letto come app).
  ⚠️ **Resta fuori perimetro** una seconda copia dello stesso elenco nello schema
  JSON di un tool dell'assistente (`ai_assistant/tools/anagrafiche_tools.py`,
  `"enum": ["PF", "PG", "ENTE"]`): lo schema si costruisce all'import e non può
  leggere il DB. ➡️ Annotato, insieme alla soglia dei tool (§6 a-bis), in
  [integrazione-ai-sviluppo-v2](../work-in-progress/integrazione-ai-sviluppo-v2.md)
  § «Debiti dei tool esistenti».
- **I mock del catalogo in una sede.** Dopo §5 ogni test unitario che passa dal
  BB di ricerca doveva fingere **due** letture (colonne e soglia), e la coppia
  era scritta a mano in cinque file con tre nomi diversi per lo stesso percorso.
  Ora c'è `catalogo_ricerca_finto(accese, *, soglia=RICERCA_MIN_CARATTERI)` in
  `apps/core/tests/ricerca_catalogo_fakes.py` (regola del 2), e le cinque copie
  sono ritirate nello stesso giro. Presidio:
  `test_ricerca_full_seed.test_i_test_fingono_il_catalogo_da_una_sede` — nessun
  altro file di test scrive i percorsi delle due letture. Il mock di
  `test_config_resolver` resta a parte: sostituisce un altro nome
  (`soggetti_repository.soglia_ricerca`).


**§8-bis. Segnalazione di Tid a video, 2026-09-26** — «i preventivi partono a
cercare al primo carattere». Non era la soglia (a catalogo `vendite.preventivi`
è 3, e «a» non partiva come `search`): la lista ha il filtro data di default,
che conta come filtro attivo, e a ogni tasto sotto soglia la guardia lasciava
ripartire la **stessa** richiesta senza `search`. Corretto nel BB
`useListaEmptyStateFetch` con `ricercaCambiaLaRichiesta(termine)`, chiesta dal
watcher di `useSearchTable`: se il `search` che partirebbe è quello dell'ultima
richiesta partita, nessuna fetch e nessun ritorno a pagina 1. Presidi:
`useListaStoreCore.spec` 18-22 e `useListaConfigurabilePage.spec` 6 (rosso con
la correzione tolta). Doc: catalogo BB frontend, `frontend-standards` §ricerca.

## 9. Collaudo a video — 2026-09-26 ✅ superato (Tid)

| Prova | Esito |
| --- | --- |
| «KG» su unità di misura (lista a soglia 1): la lista filtra | ✅ |
| Ricerca del soggetto (`SoggettoResolver`): cerca dalla soglia della lista `anagrafiche.soggetti`, il placeholder dice il numero vero | ✅ |
| Preventivi (lista a soglia 3 col filtro data di default): «a» e «ab» non ricaricano, «abc» cerca (§8-bis) | ✅ |

Fine cantiere raggiunta: nessuna chiamata al BB passa `min_caratteri`, nessuna
view dichiara la soglia a mano, e «KG» su unità di misura filtra a video.

