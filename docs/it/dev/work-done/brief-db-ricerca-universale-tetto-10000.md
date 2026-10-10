# Brief DB — Ricerca universale: oltre 10.000 risultati il totale e le pagine non dicono il vero

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-10. **A chi:** Tid per le decisioni; poi il
> team DB per il codice e BE/FE per la ricaduta (§5).
> **Origine:** trovato scrivendo R-6 di
> [brief-db-codici-non-trovato-email-e-permessi](brief-db-codici-non-trovato-email-e-permessi.md)
> (§14.5). Non nato in quel giro: c'era già.
> **Nel registro dei difetti DB:** voce **D23** di
> [migliorie-generali-da-test-valutazione.md](migliorie-generali-da-test-valutazione.md), che rimanda qui.
> **Stato:** 🔧 **decisioni chiuse** (Tid, 2026-10-10: strada B, via l'ordinamento per utility, quindi nessun tetto); **giro DB applicato da Tid il 2026-10-10, pgTAP verdi** (Tid: «migrazione applicata e test verdi»; §7). ✅ **Ricaduta BE/FE fatta il 2026-10-10** (§7.4). ✅ **Chiuso e archiviato il 2026-10-10** su richiesta di Tid; il collaudo a video segue il `kill -HUP` del backend.

## 1. Il difetto, in breve

La lista della ricerca universale (`script.fn_search_soggetti_universale`) lavora in tre passi:

1. **raccoglie** i soggetti che corrispondono al testo cercato, **al massimo 10.000**;
2. **conta** quelli raccolti: è il totale che la pagina mostra;
3. **ordina** e **taglia la pagina** (50 alla volta).

Il taglio del passo 1 non ha un ordine: quando le corrispondenze sono più di 10.000, il database
ne tiene 10.000 **qualunque**. Quindi, con 25.000 corrispondenze:

* **il totale è falso**: si legge «10.000 risultati», e niente dice che la lista è tagliata;
* **l'ordine è falso**: la prima pagina in ordine alfabetico è la prima **fra i 10.000 pescati**,
  non la prima vera. «AAA Srl» può mancare;
* **le pagine possono non tornare**: la scelta dei 10.000 non è garantita uguale da una chiamata
  all'altra, quindi fra la pagina 1 e la 2 un soggetto può ripetersi o sparire.

Sotto le 10.000 corrispondenze tutto è corretto. Il caso è ammesso dal modello: la ricerca parte
da tre caratteri, e tre lettere comuni («SRL», «ROS») su un'anagrafica grande lo producono.

## 2. Dove sta, nel corpo

Nella prima CTE della query dinamica (`filtered`): `WHERE … LIMIT 10000`, **senza `ORDER BY`**.
Poi `with_utility` raggruppa e aggrega (`utility_list`, `emittente_ragione_sociale`: una join su
`anagrafiche.clienti` e una chiamata a `fn_get_ba_emittente_sr_id` per cliente), e solo `paged`
fa `COUNT(*) OVER()`, `ORDER BY` e `LIMIT/OFFSET`.

Il tetto serve a proteggere il passo costoso: **gli aggregati si calcolano su tutto ciò che è stato
raccolto**, non sulla sola pagina. È questo il punto da cui partire.

Il backend (`core/db/search_repository.py`) legge `total_count` dalla prima riga e lo passa
all'envelope paginato (`paginated_envelope`): il totale falso arriva così com'è al frontend, che
ne ricava anche il numero di pagine.

## 3. Due strade

### A — Tenere il tetto, ma renderlo onesto

* **Ordinare prima di tagliare**: la prima CTE prende le 10.000 secondo lo stesso ordinamento
  della pagina (con il tie-breaker su `soggetto_ruolo_id`). Le pagine diventano stabili e la prima
  pagina è davvero la prima.
* **Dichiarare il taglio**: una colonna nuova in coda al `RETURNS TABLE` (per esempio
  `oltre_tetto boolean`), vera quando le corrispondenze superano il tetto. Il frontend scrive
  «troppi risultati, affina la ricerca» invece di un totale falso.
* ⚠️ L'ordinamento per `utility_list` è un aggregato: si calcola **dopo** il raggruppamento, quindi
  non si può usare per scegliere le 10.000 prima del taglio. Va deciso come trattarlo (D-2).

### B — Togliere la ragione del tetto

* **Contare, ordinare e paginare sulle righe semplici** (soggetto, ruolo, codice, ragione sociale,
  identificativo fiscale), che non chiedono join pesanti: il totale è quello **vero**, e la pagina
  è quella giusta qualunque sia il numero di corrispondenze.
* **Calcolare gli aggregati solo per le righe della pagina** (50, non 10.000): la parte costosa
  non cresce più con il numero di corrispondenze, e il tetto non ha più niente da proteggere.
* ⚠️ Stesso nodo di A: l'ordinamento per `utility_list` vorrebbe l'aggregato su tutte le
  corrispondenze, prima della pagina (D-2).
* Ricaduta sul backend minima: firma e colonne restano uguali; `total_count` diventa vero.

**La proposta del team DB è B.** Corregge il difetto alla radice: il tetto esisteva perché gli
aggregati si calcolavano su tutto, e B li calcola solo dove servono. A invece lascia un limite che
l'operatore deve conoscere, e chiede una colonna nuova a backend e frontend. Che B regga anche come
tempi lo dirà un `EXPLAIN` dopo, sul DB vero: è una verifica, non il motivo della scelta.

## 4. Decisioni attese (Tid)

| # | Domanda | Proposta |
| --- | --- | --- |
| D-1 | Strada A (tetto onesto) o B (pagina prima, aggregati dopo)? | ✅ Tid, 2026-10-10: **B** |
| D-2 | L'ordinamento per «utility» (`utility_list`, un aggregato): (a) si toglie dalla whitelist, e il frontend non lo offre più; (b) si tiene, calcolando l'aggregato su tutte le corrispondenze solo quando l'operatore sceglie quell'ordinamento, con un tetto dichiarato per quel caso | ✅ Tid, 2026-10-10: **(a)**. La colonna resta visibile, non è più ordinabile. Motivo: l'ordine di una lista di forniture concatenate («ENERGIA» < «ENERGIA, GAS» < «GAS») dice poco, e la fornitura si filtra già nel dettaglio (`p_utility_id`). Con (a) non resta nessun tetto |
| D-3 | Se resta un tetto (A, o B con D-2 b): il frontend mostra un avviso «affina la ricerca» | ✅ **cade** con D-1 = B e D-2 = (a): non resta nessun tetto da segnalare |

## 5. Ricaduta su backend e frontend (dopo le decisioni)

Con le decisioni prese (B, D-2 = a):

* **firma e colonne invariate**; il totale e il numero di pagine diventano veri;
* `utility_list` esce dalla whitelist di `p_order_by` del DB: un ordinamento chiesto su quella
  colonna risponde `E_PARAMETRO_INVALIDO`, come ogni colonna non ammessa;
* **frontend**: in `core/components/SearchDrawer.vue` la colonna «Utility» perde `sortable`;
* **backend**: se tiene un elenco suo delle colonne ordinabili della ricerca, ci toglie
  `utility_list`; documentazione dell'endpoint (`api_search_universale.md`).

## 6. pgTAP previsti

Con soggetti **costruiti** nel test (nessun confronto con i dati presenti):

* il totale è quello vero anche quando le corrispondenze sono più di quelle di una pagina (e la
  funzione non ha più un tetto da cui dipendere);
* la prima pagina ordinata per ragione sociale contiene la prima in assoluto;
* pagina 1 e pagina 2 non si sovrappongono e non saltano nessuno;
* gli aggregati (`utility_list`, `emittente_ragione_sociale`) delle righe della pagina sono uguali
  a quelli di oggi;
* `p_order_by = 'utility_list'` → `E_PARAMETRO_INVALIDO`.

## 7. Consegne

*(team DB, 2026-10-10)* — scritto e provato pre-apply; **applicato da Tid il 2026-10-10, pgTAP verdi**
(Tid: «migrazione applicata e test verdi»).

### 7.1 Cosa c'è

| Cosa | Dove | Note |
| --- | --- | --- |
| La lista | `20_code/script/20261010-16-update-fn-search-soggetti-universale-pagina-prima-degli-aggregati` | `CREATE OR REPLACE` dal corpo di `20261010-12` (applicato): firma e `RETURNS TABLE` invariati. Conteggio (`COUNT(*) OVER()` prima del `LIMIT`), ordine e pagina sulle colonne semplici di tutte le corrispondenze; `utility_list` ed `emittente_ragione_sociale` in una `LEFT JOIN LATERAL` solo per le righe della pagina; via `c_hard_cap`; `utility_list` fuori dalla whitelist di `p_order_by` (D-2) |
| pgTAP | `script/test-search-universale-pagina-v1` (**nuovo**, 9 test) | totale sull'insieme, prima pagina vera in ASC e DESC, tre pagine contigue senza ripetizioni, oltre l'ultima pagina zero righe, aggregati della pagina (utility ed emittente del cliente, `NULL` per un ruolo senza clienti), `utility_list` non ordinabile |
| Doc `manual/` | `script/fn_search_soggetti_universale.md` | strategia della query, colonne ordinabili |

⚠️ **Dichiarato nel pgTAP**: sotto le 10.000 corrispondenze anche il corpo vecchio passava i
test 1-8; il caso oltre il vecchio tetto vorrebbe 10.000 soggetti costruiti. I test pinnano le
proprietà della forma nuova, che non dipendono dal numero di corrispondenze; il 9 distingue il
corpo nuovo dal vecchio.

### 7.2 Prove fatte (pre-apply, scratch `zeroerp_ci` allineato a `20261010-15`, SQL estratto in transazione annullata)

| Prova | Esito |
| --- | --- |
| SQL estratto di `-16` + `sqlCheck` della preCondition | ✅ passa; preCondition 1 come attesa |
| Firma | ✅ `pg_get_function_identity_arguments` + `pg_get_function_result` + `prosecdef` identici al vivo; una funzione con quel nome; nel corpo non c'è più nessun `LIMIT` sul raccolto |
| `plpgsql_check` | ✅ zero `error` |
| `script/test-search-universale-pagina-v1` | ✅ 9/9 col corpo nuovo; col corpo di `-12` rosso solo il 9, come atteso |
| `script/test-search-regola-unica-visibile-v1`, `script/test-search-scope-interno-v1`, `script/test-ba-emittente-risoluzione-v1` | ✅ 17/17, 10/10, 14/14 |
| `dbops/test-riferimenti-morti-v1` | ✅ 9/9 |
| `script/test-search-soggetti-universale` | il rosso noto dello scratch al test 7 (`ERRORE_FIXTURE`, pesca dai dati); su dbdev, dopo l'apply, verde nella corsa di Tid |
| Guardrail statici (letterali, `runOnChange`, preCondition/seed, preambolo pgTAP) | ✅ |

### 7.3 Per backend e frontend (DB applicato il 2026-10-10)

1. **Backend**: `utility_list` esce dalla whitelist di `core/api/search_validators.py` (riga
   «`utility_list`» delle colonne ordinabili) e dalla descrizione OpenAPI di `p_order_by` in
   `core/api/search_view.py`. Senza, il backend lascia passare un ordinamento che il DB rifiuta
   con `E_PARAMETRO_INVALIDO`.
2. **Frontend**: in `core/components/SearchDrawer.vue` la colonna «Utility» (`field="utility_list"`)
   perde `sortable`. Resta visibile.
3. **Doc**: `api_search_universale.md` — totale vero senza tetto, colonne ordinabili.

### 7.4 Giro BE/FE (sessione backend, 2026-10-10)

| §7.3 | Dove | Che cosa |
| --- | --- | --- |
| 1 | `core/api/search_validators.py` | `utility_list` esce da `ALLOWED_ORDER_COLUMNS`. Il commento la dichiara **mirror** della whitelist di `p_order_by`: resta perché dà il 400 `E_SEARCH_VALIDATION` col campo, mentre il rifiuto del DB è `E_PARAMETRO_INVALIDO`, un codice di debito (D11) che non si espone |
| 1 | `core/api/search_view.py` | descrizione OpenAPI di `order_by`: tre colonne, e perché `utility_list` non c'è |
| 2 | `core/components/SearchDrawer.vue` | la colonna «Utility» perde `sortable` e resta visibile |
| 3 | `api_search_universale.md`, `api_search_validation.md` | nessun tetto, `total_count` vero, colonne ordinabili e aggregati della sola pagina |

⭐ **Il presidio del mirror**, ed è il pezzo che mancava: questo difetto è nato perché due
copie della stessa whitelist si sono separate senza che niente fallisse.
`core/tests/db/test_search_ordinamento_db` (e2e, sul DB vero) prova i due versi: ogni
colonna del mirror la accetta la funzione; `utility_list` ed `emittente_ragione_sociale` la
funzione le rifiuta **e** il mirror non le ammette. Mutazione con `utility_list` rimessa nel
mirror: rossi tutti e due. In `test_search_view` il test 12 prova anche il 400 su
`utility_list`.

Verde: `test_search_view` (22), `test_search_ordinamento_db` (2, e2e), ruff, eslint.

