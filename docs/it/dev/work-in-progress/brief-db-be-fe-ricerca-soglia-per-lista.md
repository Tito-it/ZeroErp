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
2. ⏳ **BE + FE**: §5, nello stesso giro — **sbloccato**. Il BE legge la soglia
   con `SELECT ricerca_min_caratteri FROM ui.fn_lista_da_codice(%s)` e la
   passa al FE dalla chiave `ricerca_min_caratteri` del jsonb del risolutore
   (§4-bis). Con §1 applicata, `test_seed_offre_tutto_cio_che_il_backend_sa_ordinare`
   deve tornare verde.
3. ⏳ **Tid**: §6 a e b, quando vuole: non bloccano.

Fine cantiere: nessuna chiamata al BB passa `min_caratteri`, nessuna view
dichiara la soglia a mano, e «KG» su unità di misura filtra a video.
