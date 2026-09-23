# Brief BE — La ricerca libera delle liste legge il catalogo

> **Destinatari:** backend (`dev/backend-tid`). Il prerequisito al team DB
> (§2.2) è chiuso.
>
> **Tipo:** brief di cantiere. Nasce il 2026-09-23 dal difetto della ricerca
> di Preventivi e Offerte (codice BA e id fiscale non trovati) e
> dall'estrazione del BB `add_ricerca_full_condition`, che ha già ritirato le
> copie scritte a mano di **dieci** liste di vendite.
>
> **Stato 2026-09-23:** 🟡 in corso — passi 0-2 di §9 chiusi, 3-5 aperti.
>
> | Passo | Stato | Dove |
> | --- | --- | --- |
> | 0 — lettura DB delle colonne ricercabili, filtrata dai permessi | ✅ `ui.fn_lista_colonne_ricerca_full(lista_codice)`, applicata sul DB di sviluppo, pgTAP del team DB | [brief-db-ricerca-full-colonne-permessi](../work-done/brief-db-ricerca-full-colonne-permessi.md), PR #1656 |
> | 0-bis — `ddt_origine_numero` di `vendite.resi` acceso a catalogo | ✅ seed `lista_colonna.csv` id 156 | PR #1658 |
> | 1 — BB a runtime (`RicercaFull` + `add_ricerca_full_condition`) e presidi | ✅ `test_ricerca_full_seed` (senza DB) e `tests/db/test_ricerca_full_db` (DB vero) verdi, suite backend verde | §3, §4 |
> | 2 — le **dieci** liste di vendite | ✅ convertite, provate sul DB vero colonna per colonna (tutte trovate, compreso il DDT di origine di Resi) | §5.0 |
> | 3 — le 12 a tupla | ⏳ da aprire | §5.1 |
> | 4 — le 11 a mappa | ⏳ | §5.2 |
> | 5 — le 9 senza ricerca | ⏳ dopo aver guardato il frontend | §5.3 |
>
> ⚠️ Passi 1-2 **non ancora committati** su `dev/backend-tid` (al 23-09 sera).
> Restano aperte le decisioni di §6 (soglia) e §7 (colonne da accendere):
> non bloccano i passi 3-5, tranne dove scritto.
>
> **Decisione di Tid (2026-09-23):** la lettura del catalogo a runtime si fa
> **per prima**, così ogni lista si modifica una volta sola.
>
> **Da leggere per primo: §2 — chi decide cosa.**

---

## 1. Da dove viene

Ogni lista configurabile dichiara nel catalogo (`ui.lista_colonna`, flag
`ricercabile_full`) su quali colonne cade la ricerca libera. Il backend quel
flag non lo leggeva: ogni repository riscriveva a mano l'elenco delle
colonne, e le copie si erano separate. Preventivi, Offerte e Contratti
cercavano su due colonne invece che su quattro, e nessun test lo vedeva.

Lo stesso giorno è nato il BB, in [`apps/core/db/_helpers.py`](../../../../backend/apps/core/db/_helpers.py),
in **due tempi**:

1. **prima versione** — un elenco fisso di colonne per lista, confrontato col
   **seed** da [`test_ricerca_full_seed.py`](../../../../backend/apps/core/tests/test_ricerca_full_seed.py).
   Ha corretto Preventivi, Offerte e Contratti e ritirato le otto copie;
2. **versione attuale** — la lettura del catalogo **a runtime** (§2, §3),
   dopo il prerequisito DB.

⚠️ **Il limite che la seconda versione ha chiuso.** Nella prima l'elenco era
una costante del codice, confrontata col seed. Ma `ricercabile_full` si
cambia anche dal pannello admin (`lista_colonna_admin_service`), e quel
cambio la ricerca non lo vedeva: il catalogo diceva una cosa, la lista ne
faceva un'altra, senza errore — lo stesso difetto da cui si era partiti,
spostato dal seed al pannello. Oggi vale per le dieci liste convertite; le
32 del registro di debito `_DEBITO_RICERCA_A_MANO` lo hanno ancora.

## 2. Chi decide cosa

### 2.1 Il modello

Due domande diverse, due sedi diverse:

| Domanda | Sede | Perché lì |
| --- | --- | --- |
| **Cosa si PUÒ cercare** in questa lista | il **codice**: una mappa `campo_sorgente → espressione SQL` nel repository | è SQL: solo il codice sa che `ba_codice` si scrive `ba.codice` in quella query, e solo il codice può garantire che l'espressione esista |
| **Cosa si CERCA** adesso, per questo utente | il **catalogo**, letto a ogni ricerca, già filtrato dai permessi di colonna | è configurazione: la cambia l'admin, e un permesso può nascondere una colonna a un utente |

La ricerca cade sull'**intersezione**: le colonne accese a catalogo **e**
conosciute dalla mappa.

- l'admin spegne una colonna → sparisce subito dalla ricerca;
- l'admin accende una colonna che la mappa conosce → entra subito;
- l'admin accende una colonna che la mappa **non** conosce → ignorata, con un
  `warning` nel log che la nomina. Mai SQL costruito da un nome di catalogo.

⛔ **Perché non si interpola direttamente il `campo_sorgente`.** Il trigger
`trgfn_ui_lista_colonna_a10_valida_campo_sorgente` verifica che la colonna
esista nella vista **solo se la lista dichiara `vista_sql`** (molte non lo
fanno), cerca la vista **per nome senza schema**, e controlla solo quando la
riga di catalogo viene scritta — non se la vista cambia dopo. E in metà delle
liste (§5.2) il `campo_sorgente` è un nome di uscita (`ba.codice AS ba_codice`)
che nel `WHERE` non esiste. La mappa nel codice è la sola garanzia.

### 2.2 Prerequisito DB — la richiesta al team

Una lettura che restituisca, **per una lista e per l'utente corrente**, le
colonne ricercabili **dopo** il filtro dei permessi di colonna:

- **output**: `codice`, `campo_sorgente`;
- **condizioni**: `attivo = t`, `ricercabile_full = t`,
  `campo_sorgente IS NOT NULL AND <> ''`, livello effettivo `<> 'BLOCCATO'`;
- **contesto**: lo stesso di `ui.fn_resolve_lista_config` (utente, emittente,
  veste dalla GUC `app.ruolo_applicativo`). ⭐ Preferenza del BE: utente ed
  emittente letti dal **contesto di sessione** (le GUC che il middleware già
  imposta per la RLS), così che la firma sia il solo `lista_codice`: i
  repository non ricevono tutti `auth_user_id`, e aggiungerlo a ogni firma è
  proprio il giro doppio che questa decisione evita. Se non è praticabile, la
  firma di `fn_resolve_lista_config` va bene e il BE si adegua;
- **volatilità** `STABLE`, grant a `zeroerp_app`.

⚠️ **Il calcolo del livello effettivo non si ricopia.** Cascata dei grant
(ruolo, emittente, fallback `sensibile → BLOCCATO`): oggi vive solo in
`fn_resolve_lista_config`, passo 5. Regola del 2 lato DB: si estrae in un
pezzo condiviso usato da entrambe, oppure — se per il team è più pulito —
si aggiungono `ricercabile_full` e `campo_sorgente` agli elementi di
`colonne` di `fn_resolve_lista_config` e il BE legge quella. Scelta del
team DB.

**pgTAP richiesti**, col caso **costruito** nel test (nel seed di oggi non
esiste nessuna colonna ricercabile e sensibile, quindi un test sul seed
passerebbe a vuoto):

1. colonna `sensibile = t` senza grant → esclusa;
2. la stessa con grant `TUTTO` o `LETTURA` → inclusa;
3. colonna non sensibile con grant `BLOCCATO` → esclusa;
4. `ricercabile_full = f`, `attivo = f`, `campo_sorgente` NULL → escluse;
5. lista inesistente → errore catalogato (come `E_UI_LISTA_NON_TROVATA`).

## 3. Il BB

```python
_RICERCA_PREVENTIVI = RicercaFull(
    "vendite.preventivi",
    ("numero", "ragione_sociale_completa", "ba_codice", "id_fiscale_univoco_cf_piva"),
)                                        # o una mappa campo_sorgente -> SQL
...
add_ricerca_full_condition(conditions, params, search, _RICERCA_PREVENTIVI)
#                                     alias="v" (forma a tupla), min_caratteri=3
```

⭐ **Scritto il 2026-09-23 in una forma diversa da quella prevista qui**:
`lista_codice` non è un argomento della chiamata ma sta nella
**dichiarazione** `RicercaFull`, insieme alle colonne. Una chiamata non può
così passare le colonne di una lista col codice di un'altra, e la
dichiarazione valida i nomi alla costruzione: un errore esce all'import del
modulo, non al primo operatore che cerca.

- **la lettura del catalogo avviene solo se il termine supera la soglia**:
  aprire una lista senza cercare non costa niente in più;
- `colonne` accetta la **mappa** `campo_sorgente → espressione SQL` (stessa
  forma delle whitelist di ordinamento: chiavi = nomi fisici del catalogo) e,
  per il caso semplice, la **tupla** di nomi, che vale la mappa identità
  `{c: f"{alias}.{c}"}`;
- il `::text` resta su ogni espressione;
- colonne accese a catalogo ma assenti dalla mappa → `logger.warning` con
  lista e colonne, e si procede con le altre;
- **nessuna colonna attiva e un termine valido → condizione `FALSE`**: una
  ricerca che non ha dove cercare non trova niente. Tornare tutta la lista
  direbbe all'operatore che tutto corrisponde al termine. ✅ Deciso da Tid il
  2026-09-23;
- errore della lettura (lista inesistente) → si propaga col suo codice: è un
  errore di dichiarazione nel repository, non un caso da ripiegare.

## 4. Il presidio

| Test | Cosa verifica | Dove |
| --- | --- | --- |
| 1 — **la mappa copre il seed** | ogni `campo_sorgente` `ricercabile_full = t` del seed è una chiave della mappa (⊇, non più =). Una colonna in più nella mappa è una capacità, non un errore | `test_ricerca_full_seed` (senza DB) |
| 2 — registro e debito | invariati: ogni lista con colonne ricercabili è registrata o in debito; il debito può solo calare | idem |
| 3 — **il codice lista giusto** | la `RicercaFull` registrata per la lista X porta `lista_codice = X`. Con codice e colonne nella stessa dichiarazione (§3) non serve leggere il sito di chiamata | idem |
| 4 — **comportamento del BB** | con la lettura del catalogo mockata: intersezione, colonna accesa non dichiarata (`warning`), nessuna colonna (`FALSE`), soglia senza lettura, mappa | idem |
| 5 — **sul DB vero** | per ogni lista registrata la condizione parte sulla sua vista (`EXPLAIN`); il catalogo non accende colonne sconosciute; spegnere `ricercabile_full` su una colonna la toglie subito (transazione annullata). ⚠️ Il caso «sensibile senza grant» sta nel pgTAP del team DB (`test-fn-lista-colonne-ricerca-full-v1`), che lo costruisce: qui non si ricopia | `tests/db/test_ricerca_full_db` (opt-in `ZEROERP_TEST_DB_E2E=1`) |

`_DIVERGENZE_NOTE` **sparisce**: una colonna che il codice sa cercare e il
catalogo non accende non è più una divergenza, è una colonna spenta. Le
domande di §7 restano, ma diventano «si accende a catalogo o no?».

## 5. Le liste

### 5.0 Le dieci già convertite il 23-09

`vendite.preventivi`, `offerte`, `ordini`, `ddt`, `fatture`, `contratti`,
`resi`, `resi_da_accreditare`, `resi_da_riconsegnare`, `famiglie_documento`.
✅ **Convertite il 2026-09-23** alla lettura a runtime, con prova sul DB vero
colonna per colonna. ✅ `vendite.resi` cerca anche `ddt_origine_numero`: la ricerca per DDT di
origine è voluta (Tid, 2026-09-23), il repository la dichiara e il seed
`lista_colonna.csv` la accende (`ricercabile_full = t`, id 156, PR del team DB
del 23-09).

### 5.1 Colonne semplici — forma a tupla (12)

| Lista | Repository · metodo | Alias | Oggi rispetto al catalogo |
| --- | --- | --- | --- |
| `anagrafiche.categorie_clienti` | `categorie_clienti_repository.list_categorie` | `cc` | allineata |
| `anagrafiche.fornitori` | `fornitori_repository.list_fornitori` | `v` | ⚠️ diversa (§7) |
| `anagrafiche.indirizzi` | `indirizzi_repository.list_indirizzi_dettaglio` | `vid` | allineata |
| `anagrafiche.soggetti` | `soggetti_repository.list_soggetti` | `s` | ⚠️ diversa (§7) |
| `catalogo.uom_tipi` | `catalogo_repository.list_uom_tipi` | `ut` | allineata |
| `catalogo.unita_misura` | `catalogo_repository.list_unita_misura` | `u` | allineata |
| `magazzino.magazzini` | `anagrafiche_magazzino_repository.list_magazzini` | `m` | allineata |
| `magazzino.ubicazioni` | `anagrafiche_magazzino_repository.list_ubicazioni` | `u` | allineata |
| `magazzino.lotti` | `anagrafiche_magazzino_repository.list_lotti` | `l` | allineata |
| `pagamenti.rate` | `pagamenti_repository.list_rate_paginata` | `v` / `p` | ⚠️ diversa (§7) |
| `amm.processi` | `core/db/processi_repository.list_processi` | `p` | allineata |
| `vendite.registri_numerazione` | `registri_repository.list_registri` | `r` | allineata |

⚠️ `pagamenti.rate`: `_condizioni(alias)` è chiamata **due volte** (pagina `v`,
perimetro `solo_aperte` `p`). Il BB va chiamato dentro `_condizioni` con
l'alias che riceve: i due insiemi non devono poter divergere.

### 5.2 Alias di uscita o colonne su più join — forma a mappa (11)

Il `campo_sorgente` è il **nome di uscita** di un'espressione, o le colonne
stanno su tabelle diverse del join.

| Lista | Repository · metodo | Nota |
| --- | --- | --- |
| `anagrafiche.clienti` | `clienti_repository.list_clienti` | join; il `vista_sql = vw_clienti_lista` a catalogo **non** è ciò che il repository legge. ⚠️ diversa (§7) |
| `anagrafiche.emittenti_fiscali` | `emittenti_fiscali_repository.list_emittenti_fiscali` | colonne su `ef` e `s`. ⚠️ diversa (§7) |
| `anagrafiche.emittente_billing_account` | `EmittentiFiscaliBillingAccountRepository.list_by_emittente` | tre alias di uscita |
| `catalogo.conversioni_uom` | `catalogo_repository.list_conversioni` | alias di uscita (`uom_from_codice` = `uf.codice`, …) |
| `config.tipi_ruolo_tipi_indirizzo` | `tipi_ruolo_tipi_indirizzo_repository.list_matrice` | ⚠️ l'uscita è `COALESCE(x.codice_interno, x.codice)`, la ricerca oggi usa `x.codice`: la mappa usa **la stessa espressione dell'uscita** |
| `config.utilities_tipi_ruolo` | `utilities_tipi_ruolo_repository.list_matrice` | alias di uscita |
| `pratiche.pratiche` | `pratiche_repository.list_pratiche` | `soggetto_display` = `s.ragione_sociale_completa`. ⚠️ La stessa query serve `vendite.approvazioni_prezzo`: il `lista_codice` va passato dal chiamante |
| `magazzino.inventari` · `magazzino.rettifiche` | `magazzino_repository.list_documenti` | un metodo, due liste: `lista_codice` dal chiamante |
| `magazzino.disponibilita` | `magazzino_repository.list_disponibilita` | ⚠️ diversa (§7) |
| `magazzino.disponibilita_articoli` | `magazzino_repository.list_disponibilita_articoli` | alias di uscita |

⭐ Regola della mappa: il valore è **la stessa espressione che la `SELECT`
proietta** con quel nome. Si cerca su ciò che si mostra.

### 5.3 Nessuna ricerca, ma il catalogo la dichiara (9)

| Lista | Repository · metodo | Colonne dichiarate |
| --- | --- | --- |
| `magazzino.inventario_righe` | `magazzino_repository.list_righe` | articolo_codice, articolo_descrizione |
| `magazzino.rettifica_righe` | `magazzino_repository.list_righe` | articolo_codice, articolo_descrizione, motivo |
| `magazzino.inventario_piano` | `magazzino_repository.list_piano` (legge `fn_inventario_piano`) | articolo_codice, articolo_descrizione |
| `magazzino.movimenti` | `magazzino_repository.list_movimenti` | articolo_codice, articolo_descrizione |
| `pagamenti.distinte` | `pagamenti_repository.list_distinte` | codice |
| `pagamenti.righe` | `pagamenti_repository.list_righe_coda` | riferimento_ente, billing_account_descrizione, fattura_numero, contabile_codice |
| `pagamenti.distinta_righe` | `pagamenti_repository.list_righe_distinta` | riferimento_ente, billing_account_descrizione, fattura_numero_documento, billing_account_codice |
| `pagamenti.rate_fuori_capienza` | `pagamenti_repository.list_rate_fuori_capienza` (`FROM pagamenti.vw_rate_fuori_capienza v`) | fattura_numero, numero_documento |
| `pagamenti.eccedenze` | `pagamenti_repository.list_eccedenze` | cliente_ragione_sociale, fattura_numero |

Qui si **aggiunge** la ricerca (view: parametro `search`; repository: BB),
non si spegne il flag: il catalogo è il contratto. Prima di scrivere,
verificare cosa mostra il frontend: casella presente che non filtra è un
difetto visibile; casella assente è un montaggio da completare.

### 5.4 Cosa si fa per ogni lista

1. si dichiara la `RicercaFull` (mappa o tupla) `_RICERCA_…` nel repository e si
   chiama il BB con il suo `lista_codice`;
2. la lista si **toglie** da `_DEBITO_RICERCA_A_MANO` e si **aggiunge** a
   `_RICERCHE`, nello stesso giro;
3. si prova sul **DB vero**, non coi mock: per ogni colonna accesa si cerca il
   valore di una riga e la riga deve uscire (la prova fatta il 23-09 sulle
   dieci liste di vendite: i test di servizio mockano il repository e non
   vedono la SQL).

⛔ Le copie locali dell'helper si ritirano **nello stesso giro** dei loro
consumatori (§8), non «dopo».

## 6. La soglia minima del termine

| Comportamento | Dove |
| --- | --- |
| **400** `E_SEARCH_VALIDATION` sotto 3 caratteri (`require_min_search_length`) | view di magazzino e di `catalogo.uom_tipi`/`unita_misura`; `ErrorManager.require` in `saldi_service` per `pagamenti.rate` |
| **ignorato** sotto 3 caratteri | il BB (default), e le dieci liste di vendite — offerte comprese: il suo 400 in `offerte_service` e' ritirato il 2026-09-23 (Tid) |
| **nessuna soglia** | quasi tutte le altre |

⚠️ **Decisione aperta per Tid:** una regola sola (400 o ignorato)? Il frontend
manda il termine a ogni tasto (`useSearchTable`): il 400 durante la
digitazione va guardato a video prima di sceglierlo. Fino alla decisione i
400 esistenti **restano** nelle view. `min_caratteri=1` resta la via
dichiarata per le liste di configurazione a codici corti (la usa
`vendite.famiglie_documento`).

## 7. Colonne diverse fra codice e catalogo — si decide se accenderle

Con la lettura a runtime la mappa può legittimamente conoscere più colonne di
quelle accese. La domanda per ciascuna diventa: **si accende a catalogo o
no?** Ogni «sì» è una riga del seed `lista_colonna.csv` per il team DB.

| Lista | Il codice cerca in più | Il catalogo accende in più | Domanda |
| --- | --- | --- | --- |
| `anagrafiche.clienti` | `codice_fiscale`, `partita_iva`, `soggetto_codice` | — | ricerca per CF/P.IVA e codice soggetto voluta? |
| `anagrafiche.fornitori` | `codice_fiscale`, `partita_iva` | `id_fiscale_univoco_cf_piva` | CF+P.IVA separati o l'id fiscale univoco, come le liste di vendite? |
| `anagrafiche.soggetti` | `codice_fiscale`, `partita_iva` | — | come clienti |
| `anagrafiche.emittenti_fiscali` | `codice_fiscale` | — | come clienti |
| `pagamenti.rate` | `id_fiscale_univoco_cf_piva` | `numero_documento` | ⛔ **contraddizione di progetto**: il commento in `list_rate_paginata` dice «`search` cerca il CLIENTE, mai il numero» (brief D19-c §8), il seed accende il numero. Uno dei due è sbagliato |
| `magazzino.disponibilita` | — | `magazzino_codice` | colonna mancante nel codice: entra nella mappa |
| `vendite.resi` | `ddt_origine_numero` | — | ✅ voluta (Tid, 2026-09-23): dichiarata nel repository e accesa nel seed `lista_colonna.csv` (id 156) |

## 8. Helper locali da ritirare nello stesso giro

| Helper | Consumatori | Nota |
| --- | --- | --- |
| `catalogo_repository._append_ilike_search` | articoli, lookup, `unita_misura` | due colonne, niente escape né strip |
| `listini_repository._append_ilike_search` | tre liste di listini | **copia identica** della precedente. Le liste di listini non hanno colonne `ricercabile_full`: l'helper si ritira, ma la loro ricerca non ha un catalogo da leggere — da decidere se seminarle |
| `anagrafiche_magazzino_repository._ricerca` | magazzini, ubicazioni, lotti | già con escape: è il BB in piccolo |
| forma inline `search_pattern = …` + `(%s::text IS NULL OR (… ILIKE %s …))` | clienti, emittenti (×2), fornitori, indirizzi, soggetti, registri | la stessa riga ripetuta sette volte |

## 9. Ordine

0. ✅ **Team DB** — la lettura di §2.2, coi pgTAP.
1. ✅ **BB e presidio** — §3, §4: `test_ricerca_full_seed` e
   `tests/db/test_ricerca_full_db`.
2. ✅ **Le dieci di vendite** (§5.0).
3. **Le 12 a tupla** (§5.1), per app, ritirando i loro helper (§8).
4. **Le 11 a mappa** (§5.2).
5. **Le 9 senza ricerca** (§5.3), dopo aver guardato il frontend.

Le domande di §6 e §7 si chiudono man mano: non bloccano il resto, tranne
dove è scritto.

Fine cantiere: `_DEBITO_RICERCA_A_MANO` **vuoto**, e il docstring del BB senza
più il paragrafo «Limite noto».

## 10. Fuori perimetro

- **L'ordinamento ha lo stesso limite**: `ordinabile` si cambia dal pannello,
  la whitelist sta nel codice e `test_liste_configurabili_seed` la confronta
  col seed. La stessa soluzione (whitelist = cosa si può ordinare, catalogo =
  cosa si ordina) vale anche lì, ma è un cantiere a parte.
- I numeri di questo brief (32 liste, 12 + 11 + 9, più le 10 già convertite)
  sono una **fotografia del 2026-09-23**: la fonte è il registro nel test, non
  questo documento.
