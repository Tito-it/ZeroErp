# Brief BE — La ricerca libera delle liste legge il catalogo

> **Destinatari:** backend (`dev/backend-tid`). Il prerequisito al team DB
> (§2.2) è chiuso.
>
> **Tipo:** brief di cantiere. Nasce il 2026-09-23 dal difetto della ricerca
> di Preventivi e Offerte (codice BA e id fiscale non trovati) e
> dall'estrazione del BB `add_ricerca_full_condition`, che ha già ritirato le
> copie scritte a mano di **dieci** liste di vendite.
>
> **Stato 2026-09-24:** 🟡 in corso — passi 0-5 lato BE chiusi, tranne
> tre liste che **aspettano il seed del team DB**; passo 6 (FE) da aprire.
> Il 24-09: revisione del diff non committato (§11), regola del 2 sul
> parametro OpenAPI `search`, soglia negli strumenti AI, `ricerca_full` solo
> sulla schermata (§7-bis), e **una richiesta nuova al team DB**: il codice
> della guardia di contesto utente (§12), che il BE aspetta.
> `_DEBITO_RICERCA_A_MANO` è sceso da 32 a **3**: `anagrafiche.clienti`,
> `anagrafiche.soggetti`, `pagamenti.rate`. Richiesta al team DB:
> [brief-db-ricerca-full-colonne-da-accendere](brief-db-ricerca-full-colonne-da-accendere.md).
>
> ✅ **Aggiornamento DB del 2026-09-24 sera:** le **due** richieste al team DB
> sono **applicate** su dbdev: il seed del brief DB (§3.1-§3.5, compreso il
> `codice` di `vendite.famiglie_documento`, changeSet `20260924-03…-07`) e il
> codice `E_UI_CHIAMATA_NON_VALIDA` (§12). **I passi 7 e 8 sono sbloccati.**
> Cosa diventa rosso lato BE fino alla conversione, e perché, è in §6.6 del
> brief DB (è il segnale voluto).
>
> | Passo | Stato | Dove |
> | --- | --- | --- |
> | 0 — lettura DB delle colonne ricercabili, filtrata dai permessi | ✅ `ui.fn_lista_colonne_ricerca_full(lista_codice)`, applicata sul DB di sviluppo, pgTAP del team DB | [brief-db-ricerca-full-colonne-permessi](../work-done/brief-db-ricerca-full-colonne-permessi.md), PR #1656 |
> | 0-bis — `ddt_origine_numero` di `vendite.resi` acceso a catalogo | ✅ seed `lista_colonna.csv` id 156 | PR #1658 |
> | 1 — BB a runtime (`RicercaFull` + `add_ricerca_full_condition`) e presidi | ✅ `test_ricerca_full_seed` (senza DB) e `tests/db/test_ricerca_full_db` (DB vero) verdi, suite backend verde | §3, §4 |
> | 2 — le **dieci** liste di vendite | ✅ convertite, provate sul DB vero colonna per colonna (tutte trovate, compreso il DDT di origine di Resi) | §5.0 |
> | 3 — le 12 a tupla | 🟡 10 di 12 ✅, provate sul DB vero colonna per colonna da test permanenti (`verifica_ricerca_colonna_per_colonna`). Restano soggetti e pagamenti.rate: §7 deciso, aspettano il seed DB | §5.1 |
> | 4 — le 11 a mappa | 🟡 10 di 11 ✅, provate sul DB vero colonna per colonna da test permanenti. Resta `anagrafiche.clienti`: aspetta il seed DB (id fiscale e codice soggetto, brief DB §3.1) | §5.2 |
> | 5 — le 9 senza ricerca | ✅ BE / ⏳ FE — **BE fatto il 23-09**: `search` nelle view (anche negli export), BB nei repository, prova colonna per colonna sul DB vero (magazzino: `test_documento_interno_db` test 13; pagamenti: `test_rate_lista_db.RicercaListeDbTests`). Nessuna delle 9 mostrava la casella: ⏳ **FE da fare** (la casella legge `ricerca_full`) | §5.3 |
> | 5-bis — la configurazione dice se la lista cerca | ✅ `ricerca_full` nella configurazione della schermata (`GET /ui/liste/<codice>/config`, `UiService.get_lista_config_per_video` dal 24-09) | §7-bis |
> | 5-ter — revisione del 24-09 | ✅ correzioni di fragilità e duplicazioni, BB `param_ricerca_full`, soglia negli strumenti AI | §11 |
> | 6 — FE: casella solo se `ricerca_full` | ⏳ da aprire — pezzo condiviso, poi le 9 liste di §5.3 | §9 |
> | 7 — dopo il seed DB | ⏳ convertire clienti, soggetti, rate, le 12 liste di §7-bis; togliere `codice_interno` da `uom_tipi` e `partita_iva` dagli emittenti. ✅ Seed DB **applicato il 24-09** (brief DB §6): **sbloccato** | §9 |
> | 8 — guardia di contesto utente su `ricerca_full` | ⏳ BE — codice DB `E_UI_CHIAMATA_NON_VALIDA` **applicato il 24-09** (brief DB §6.4): **sbloccato** | §12 |
>
> Passi 1-2 mergiati (PR #1660); passi 3-5, 5-bis e 5-ter **non ancora
> committati** su `dev/backend-tid` (al 24-09). Resta aperta **una** decisione: §6, la
> soglia delle liste non di configurazione (400 o ignorato). Le domande di §7 e
> §7-bis sono tutte chiuse da Tid il 23-09.
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
spostato dal seed al pannello. Al 23-09 sera resta solo sulle 3 liste del
registro di debito `_DEBITO_RICERCA_A_MANO` (partito da 32).

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
| 5-bis — **le liste senza vista** | una lista registrata senza `vista_sql` nomina in `_ESERCITATE_DAL_REPOSITORY` il test che la cerca dal suo repository; il nome si **risolve** (test rinominato o cancellato → rosso) | `test_ricerca_full_db` test 1 |
| 6 — **ogni colonna accesa trova la sua riga** | su una riga **costruita**, per ogni colonna che il catalogo accende il valore la trova; un termine inesistente non trova niente. Le colonne vengono dal catalogo, non dal test: una accesa domani senza valore fa rosso. BB di test `verifica_ricerca_colonna_per_colonna` (`apps/core/tests/db_e2e.py`, regola del 2, ok di Tid) | `test_ricerca_full_db` test 4 (anagrafiche, config, catalogo, pratiche, emittenti, registri, processi); `test_anagrafiche_magazzino_db` test 7; `test_documento_interno_db` test 13; `test_rate_lista_db.RicercaListeDbTests` |
| 7 — **la configurazione dice se la lista cerca** | `ricerca_full` vero per una lista con colonne accese, falso per una senza, falso subito se l'admin le spegne tutte | `test_ricerca_full_db` test 5 |

⭐ Provate con mutazione il 23-09: tolta una colonna da una dichiarazione (o
spostata su un'altra espressione), il rosso arriva sia dal seed sia dal DB
vero.

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
| `anagrafiche.categorie_clienti` | `categorie_clienti_repository.list_categorie` | `cc` | ✅ convertita, `min_caratteri=1` |
| `anagrafiche.fornitori` | `fornitori_repository.list_fornitori` | `v` | ✅ convertita (id fiscale univoco, §7) |
| `anagrafiche.indirizzi` | `indirizzi_repository.list_indirizzi_dettaglio` | `vid` | ✅ convertita |
| `anagrafiche.soggetti` | `soggetti_repository.list_soggetti` | `s` | ⏳ aspetta il seed DB (§7) |
| `catalogo.uom_tipi` | `catalogo_repository.list_uom_tipi` | `ut` | ✅ convertita, `min_caratteri=1`. ⏳ Toglie `codice_interno` dopo il seed (brief DB §3.4) |
| `catalogo.unita_misura` | `catalogo_repository.list_unita_misura` | `u` | ✅ convertita, `min_caratteri=1`, 400 della view tolto |
| `magazzino.magazzini` | `anagrafiche_magazzino_repository.list_magazzini` | `m` | ✅ convertita |
| `magazzino.ubicazioni` | `anagrafiche_magazzino_repository.list_ubicazioni` | `u` | ✅ convertita |
| `magazzino.lotti` | `anagrafiche_magazzino_repository.list_lotti` | `l` | ✅ convertita |
| `pagamenti.rate` | `pagamenti_repository.list_rate_paginata` | `v` / `p` | ⏳ aspetta il seed DB (§7) |
| `amm.processi` | `core/db/processi_repository.list_processi` | `p` | ✅ convertita, `min_caratteri=1` |
| `vendite.registri_numerazione` | `registri_repository.list_registri` | `r` | ✅ convertita, `min_caratteri=1` |

⭐ **Liste senza `vista_sql`** (quasi tutte quelle convertite dopo le dieci di
vendite): il test 1 di `tests/db/test_ricerca_full_db` non ha una vista su cui
provare la condizione. La lista nomina allora in `_ESERCITATE_DAL_REPOSITORY`
il test che la cerca **dal suo repository** su una riga costruita (§4, riga 6).

⭐ **Soglia:** le tabelle di configurazione cercano da un carattere (decisione
di Tid, §6); le altre col default del BB.

⚠️ `pagamenti.rate` (dopo il seed): `_condizioni(alias)` è chiamata **due
volte** (pagina `v`, perimetro `solo_aperte` `p`). Il BB va chiamato dentro
`_condizioni` con l'alias che riceve: i due insiemi non devono poter divergere.
Nello stesso giro si rovesciano il commento «mai il numero» di
`list_rate_paginata` e il test `test_la_ricerca_libera_trova_il_cliente_non_il_numero`
(decisione di Tid: si cerca anche per documento).

### 5.2 Alias di uscita o colonne su più join — forma a mappa (11)

Il `campo_sorgente` è il **nome di uscita** di un'espressione, o le colonne
stanno su tabelle diverse del join.

| Lista | Repository · metodo | Nota |
| --- | --- | --- |
| `anagrafiche.clienti` | `clienti_repository.list_clienti` | join; il `vista_sql = vw_clienti_lista` a catalogo **non** è ciò che il repository legge. ⚠️ diversa (§7) — ⏳ aspetta il seed DB: il catalogo non accende id fiscale e codice soggetto, che il codice cerca oggi. |
| `anagrafiche.emittenti_fiscali` | `emittenti_fiscali_repository.list_emittenti_fiscali` | ✅ convertita il 23-09 (codice, ragione sociale, P.IVA oggi accesa). La dichiarazione conosce già l'id fiscale univoco, ora proiettato; ⏳ `partita_iva` si toglie dopo il seed (brief DB §3.2) |
| `anagrafiche.emittente_billing_account` | `EmittentiFiscaliBillingAccountRepository.list_by_emittente` | tre alias di uscita — ✅ convertita il 23-09. |
| `catalogo.conversioni_uom` | `catalogo_repository.list_conversioni` | alias di uscita (`uom_from_codice` = `uf.codice`, …) — ✅ convertita il 23-09, configurazione: da un carattere. |
| `config.tipi_ruolo_tipi_indirizzo` | `tipi_ruolo_tipi_indirizzo_repository.list_matrice` | ✅ convertita il 23-09 su `tr.codice`/`ti.codice`, da un carattere. ✅ **Proiezione corretta** lo stesso giorno: `tipo_ruolo_codice`, `tipo_indirizzo_codice`, `fallback_codice` (e le opzioni di fallback del drawer) erano `COALESCE(x.codice_interno, x.codice)` — un codice interno sotto un nome `*_codice` (linee-guida-sql §6c). Ora sono il `codice`: si cerca su ciò che si mostra, e il `codice_interno` non si cerca |
| `config.utilities_tipi_ruolo` | `utilities_tipi_ruolo_repository.list_matrice` | alias di uscita — ✅ convertita il 23-09, da un carattere. |
| `pratiche.pratiche` | `pratiche_repository.list_pratiche` | `soggetto_display` = `s.ragione_sociale_completa`. ⚠️ La stessa query serve `vendite.approvazioni_prezzo`: il `lista_codice` va passato dal chiamante — ✅ convertita il 23-09 (dichiarazione fissa: `approvazioni_prezzo` non passa mai `search`). |
| `magazzino.inventari` · `magazzino.rettifiche` | `magazzino_repository.list_documenti` | ✅ convertite il 23-09: un metodo, due liste, una dichiarazione per famiglia (`_RICERCA_DOCUMENTI[f.lista_codice]`) |
| `magazzino.disponibilita` | `magazzino_repository.list_disponibilita` | ⚠️ diversa (§7) — ✅ convertita il 23-09, con `magazzino_codice` che mancava. |
| `magazzino.disponibilita_articoli` | `magazzino_repository.list_disponibilita_articoli` | alias di uscita — ✅ convertita il 23-09. |

⭐ Regola della mappa: il valore è **la stessa espressione che la `SELECT`
proietta** con quel nome. Si cerca su ciò che si mostra.

### 5.3 Nessuna ricerca, ma il catalogo la dichiara (9)

| Lista | Repository · metodo | Colonne dichiarate | BE | FE |
| --- | --- | --- | --- | --- |
| `magazzino.inventario_righe` | `magazzino_repository.list_righe` | articolo_codice, articolo_descrizione | ✅ | ⏳ |
| `magazzino.rettifica_righe` | `magazzino_repository.list_righe` | articolo_codice, articolo_descrizione, motivo | ✅ | ⏳ |
| `magazzino.inventario_piano` | `magazzino_repository.list_piano` (legge `fn_inventario_piano`) | articolo_codice, articolo_descrizione | ✅ | ⏳ |
| `magazzino.movimenti` | `magazzino_repository.list_movimenti` | articolo_codice, articolo_descrizione | ✅ | ⏳ |
| `pagamenti.distinte` | `pagamenti_repository.list_distinte` | codice | ✅ | ⏳ |
| `pagamenti.righe` | `pagamenti_repository.list_righe_coda` | riferimento_ente, billing_account_descrizione, fattura_numero, contabile_codice | ✅ | ⏳ |
| `pagamenti.distinta_righe` | `pagamenti_repository.list_righe_distinta` | riferimento_ente, billing_account_descrizione, fattura_numero_documento, billing_account_codice | ✅ (anche l'export) | ⏳ |
| `pagamenti.rate_fuori_capienza` | `pagamenti_repository.list_rate_fuori_capienza` (`FROM pagamenti.vw_rate_fuori_capienza v`) | fattura_numero, numero_documento | ✅ | ⏳ |
| `pagamenti.eccedenze` | `pagamenti_repository.list_eccedenze` | cliente_ragione_sociale, fattura_numero | ✅ | ⏳ |

Qui si **aggiunge** la ricerca (view: parametro `search`; repository: BB),
non si spegne il flag: il catalogo è il contratto. ✅ **BE aggiunto il
2026-09-23** su tutte e nove; nessuna mostrava la casella (verificato nei
componenti FE), quindi il montaggio resta da completare lato FE. Le view nuove
**non** rispondono 400 sotto 3 caratteri: il BB ignora il termine corto, e la
soglia delle liste non di configurazione è la decisione aperta di §6. Righe di
magazzino, piano e righe di distinta sono diventate `is_search_endpoint`
(limite di frequenza delle ricerche), come le altre liste che cercano.

### 5.4 Cosa si fa per ogni lista

1. si dichiara la `RicercaFull` (mappa o tupla) `_RICERCA_…` nel repository e si
   chiama il BB con il suo `lista_codice`;
2. la lista si **toglie** da `_DEBITO_RICERCA_A_MANO` e si **aggiunge** a
   `_RICERCHE`, nello stesso giro;
3. si prova sul **DB vero**, non coi mock: per ogni colonna accesa si cerca il
   valore di una riga e la riga deve uscire (la prova fatta il 23-09 sulle
   dieci liste di vendite: i test di servizio mockano il repository e non
   vedono la SQL). ⭐ Dal 23-09 la prova è **permanente**:
   `verifica_ricerca_colonna_per_colonna` di `apps/core/tests/db_e2e.py`
   (regola del 2, ok di Tid), su una riga **costruita** nel test. Chi la usa:
   §4, riga 6. Le dieci di vendite restano provate una tantum.

⛔ Le copie locali dell'helper si ritirano **nello stesso giro** dei loro
consumatori (§8), non «dopo».

## 6. La soglia minima del termine

| Comportamento | Dove |
| --- | --- |
| **400** `E_SEARCH_VALIDATION` sotto 3 caratteri (`require_min_search_length`) | view delle testate e della disponibilità di magazzino e delle anagrafiche di magazzino; `ErrorManager.require` in `saldi_service` per `pagamenti.rate`; `catalogo.articoli` |
| **ignorato** sotto 3 caratteri | il BB (default): le dieci liste di vendite (il 400 di `offerte_service` è ritirato, Tid), e tutte le liste convertite il 23-09 che non hanno un 400 nella view — comprese le nove di §5.3 |
| **da un carattere** | le tabelle di configurazione (sotto) |

✅ **Decisione di Tid (2026-09-23): le tabelle di configurazione cercano da un
carattere, senza 400.** Applicata il 23-09 con `min_caratteri=1` a
`catalogo.uom_tipi`, `catalogo.unita_misura` (tolto anche il 400 delle due
view: «KG» ora si cerca), `amm.processi`, `anagrafiche.categorie_clienti`,
`vendite.registri_numerazione`; `vendite.famiglie_documento` lo aveva già.
Le anagrafiche di magazzino (magazzini, ubicazioni, lotti) **non** sono
configurazione: restano al default.

⚠️ **Resta aperta per Tid, sulle liste NON di configurazione:** una regola sola (400 o ignorato)? Il frontend
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
| `anagrafiche.clienti` | `codice_fiscale`, `partita_iva`, `soggetto_codice` | — | ✅ **id fiscale univoco** (uniformità, Tid 23-09) e codice soggetto, che il codice cerca oggi. ⏳ Richieste le righe 3 e 4 al team DB (brief DB §3.1); la conversione aspetta il seed |
| `anagrafiche.fornitori` | `codice_fiscale`, `partita_iva` | `id_fiscale_univoco_cf_piva` | ✅ **id fiscale univoco** (Tid, 23-09). Convertita il 23-09: codice, ragione sociale, id fiscale |
| `anagrafiche.soggetti` | `codice_fiscale`, `partita_iva` | — | ✅ **id fiscale univoco** (Tid, 23-09). ⏳ Il catalogo non lo accende (id 17, `ricercabile_full = f`): richiesta al team DB, e la conversione **aspetta il seed** — prima perderebbe la ricerca per CF/P.IVA |
| `anagrafiche.emittenti_fiscali` | `codice_fiscale` | `partita_iva` | ✅ **id fiscale univoco** anche qui (uniformità, Tid 23-09). Convertita il 23-09; ⏳ riga nuova `id_fiscale_univoco_cf_piva` e `partita_iva` spenta, richieste al team DB (brief DB §3.2) |
| `pagamenti.rate` | `id_fiscale_univoco_cf_piva` | `numero_documento` | ✅ **anche il documento** (Tid, 23-09): il seed ha ragione, il commento «mai il numero» e il test che lo fissa vanno rovesciati. ⏳ L'id fiscale che il codice cerca oggi **non ha una colonna** nel catalogo della lista: richiesta al team DB, e la conversione **aspetta il seed** |
| `magazzino.disponibilita` | — | `magazzino_codice` | colonna mancante nel codice: entra nella mappa — ✅ convertita il 23-09, con `magazzino_codice` che mancava. |
| `vendite.resi` | `ddt_origine_numero` | — | ✅ voluta (Tid, 2026-09-23): dichiarata nel repository e accesa nel seed `lista_colonna.csv` (id 156) |

## 7-bis. Liste a catalogo che cercano senza dichiararlo — ⛔ lacuna del modello

Trovata il 2026-09-23 convertendo il catalogo. La ricognizione delle 40 liste
attive senza colonne ricercabili (pagina FE → view → repository) ne ha trovate
**12 che cercano nel codice e mostrano la casella**: `catalogo.articoli`,
`vendite.listini`, `vendite.listini_righe`,
`anagrafiche.categorie_clienti_listini`, `vendite.promo_articoli`,
`documenti.template_documenti`, `documenti.template_asset`,
`anagrafiche.operatori`, `config.email_account`, `config.email_template`,
`config.email_log`, `vendite.dash_competenza_gruppi`. Le altre 27 non cercano
e non hanno casella. Dettaglio per riga: brief DB §3.

Il contratto dice «qui non si cerca», il codice cerca lo stesso: è la stessa
divergenza da cui è nato il cantiere, rovesciata. **Col BB la ricerca di
queste liste non troverebbe niente** (nessuna colonna accesa → `FALSE`, §3):
non si convertono finché il catalogo non le accende.

⚠️ **Il presidio non la vede.** `test_ogni_lista_ricercabile_e_registrata_o_in_debito`
parte dalle liste con colonne ricercabili: una lista che cerca senza
dichiararlo gli è invisibile per costruzione.

✅ **Decisione di Tid (2026-09-23): si accendono.** Richiesta al team DB in
[brief-db-ricerca-full-colonne-da-accendere](brief-db-ricerca-full-colonne-da-accendere.md);
le liste si convertono **dopo** il seed.

✅ **Decisioni di Tid (2026-09-23):**
- descrizione articolo nelle promo e descrizioni della matrice categorie-listini:
  **si accendono**, con colonne nuove a catalogo (brief DB §3.2-bis);
- ⛔ **il `codice_interno` non si usa per cercare**: si cerca il `codice`. I
  template non lo dichiareranno; `catalogo.uom_tipi` lo toglie **dopo** il
  seed (brief DB §3.4);
- la casella di ricerca si mostra **solo se il catalogo accende almeno una
  colonna**. ✅ **Pezzo BE fatto il 23-09, spostato il 24-09**: la configurazione della
  lista (`GET /ui/liste/<codice>/config`) porta `ricerca_full`, vero se per
  l'utente corrente c'è almeno una colonna accesa. Letta con
  `colonne_ricerca_accese` (`core/db/_helpers.py`, resa pubblica: la stessa
  lettura del BB) via `UiRepository.ha_ricerca_full`; doc in
  `backend/ui/manual/api_ui_liste.md`; test 5 di `test_ricerca_full_db`.
  ⭐ **Dal 24-09 la calcola solo `UiService.get_lista_config_per_video`**, che
  serve la schermata (Tid): `get_lista_config` la leggono anche l'export
  (`export_helpers`) e la modale di personalizzazione (`get_catalogo`), che la
  casella non la mostrano e pagavano una query per niente. Presidio:
  `test_ui_service` (la configurazione «nuda» non porta la chiave e non legge
  il catalogo della ricerca);
  È anche la chiusura del punto cieco del presidio: casella e catalogo non
  possono più divergere. ⏳ **Pezzo FE da fare** (passo 6): la casella legge
  `ricerca_full`. Il BE del passo 5 è fatto, quindi le liste che la
  configurazione dichiara ricercabili cercano davvero;
- operatori (email, nome, ragione sociale): **si aggiungono** a catalogo (brief DB §3.2-bis);
- **tutte le anagrafiche cercano per id fiscale univoco**, per uniformità: anche
  `anagrafiche.emittenti_fiscali` (brief DB §3.2; la dichiarazione lo conosce
  già dal 23-09, `partita_iva` si toglie dopo il seed);
- la matrice `config.tipi_ruolo_tipi_indirizzo` proiettava come `*_codice` il
  `codice_interno`: **corretta** il 23-09 (`tipo_ruolo_codice`,
  `tipo_indirizzo_codice`, `fallback_codice` e le opzioni di fallback sono il
  `codice`);
- `vendite.famiglie_documento`: la colonna `codice` si **aggiunge** (brief DB §3.5);
- il pannello generico dei codici (`dbops_repository`) che cerca anche sul
  `codice_interno`: **resta così** (Tid).

La **lookup** articoli (`lookup_articoli`, autocomplete cross-dominio) non è
una lista: non ha un catalogo da leggere e non passerà dal BB. Il suo
`_append_ilike_search` non escapa `%`/`_` né toglie gli spazi: va sul
`escape_ilike` come le altre lookup (`billing_account`, `istanze_utility`)
quando l'helper si ritira.

## 8. Helper locali da ritirare nello stesso giro

| Helper | Consumatori | Nota |
| --- | --- | --- |
| `catalogo_repository._append_ilike_search` | articoli, lookup — ~~`unita_misura`~~ ✅ 2026-09-23 | due colonne, niente escape né strip. ⚠️ **Non si ritira ancora**: articoli è bloccata da §7-bis, e la lookup non è una lista (non ha un catalogo da leggere) |
| `listini_repository._append_ilike_search` | tre liste di listini | **copia identica** della precedente. Le liste di listini non hanno colonne `ricercabile_full`: l'helper si ritira, ma la loro ricerca non ha un catalogo da leggere — da decidere se seminarle |
| ~~`anagrafiche_magazzino_repository._ricerca`~~ | magazzini, ubicazioni, lotti | ✅ ritirato il 2026-09-23 |
| forma inline `search_pattern = …` + `(%s::text IS NULL OR (… ILIKE %s …))` | clienti, emittenti (×2), fornitori, soggetti — ~~indirizzi, registri~~ ✅ ritirati il 2026-09-23 | la stessa riga ripetuta sette volte |

## 9. Ordine

0. ✅ **Team DB** — la lettura di §2.2, coi pgTAP.
1. ✅ **BB e presidio** — §3, §4: `test_ricerca_full_seed` e
   `tests/db/test_ricerca_full_db`.
2. ✅ **Le dieci di vendite** (§5.0).
3. ✅ **Le 12 a tupla** (§5.1): 10 convertite, `_ricerca` di magazzino
   ritirato; soggetti e rate al passo 7.
4. ✅ **Le 11 a mappa** (§5.2): 10 convertite; clienti al passo 7.
5. ✅ BE / ⏳ FE — **Le 9 senza ricerca** (§5.3).
   - 5-bis ✅ `ricerca_full` nella configurazione risolta (§7-bis).
6. ⏳ **FE** — un pezzo condiviso che mostra la casella di ricerca solo se la
   configurazione dice `ricerca_full`, montato sulle 9 liste di §5.3 (anche in
   drawer e dialog: righe di distinta, piano) e sulle liste che oggi mostrano
   la casella. Prima: `frontend-standards.md` e il catalogo BB frontend.
7. ⏳ **Dopo il seed del team DB** (brief DB): convertire `anagrafiche.clienti`,
   `anagrafiche.soggetti`, `pagamenti.rate` e le 12 liste di §7-bis, ritirando
   `catalogo_repository._append_ilike_search` (articoli), il gemello dei
   listini e la forma inline di clienti/soggetti; togliere `codice_interno`
   da `uom_tipi` e `partita_iva` dagli emittenti; `famiglie_documento` cerca
   sul `codice` quando la colonna esiste (brief DB §3.5).

8. ⏳ **Dopo il codice DB di §12**: la guardia di contesto utente in
   `get_lista_config_per_video`, col BB `utente_di_sessione` estratto nello
   stesso giro.

Resta aperta la decisione di §6 (soglia delle liste non di configurazione):
non blocca niente.

Fine cantiere: `_DEBITO_RICERCA_A_MANO` **vuoto**, e il docstring del BB senza
più il paragrafo «Limite noto».

## 10. Fuori perimetro

- **L'ordinamento ha lo stesso limite**: `ordinabile` si cambia dal pannello,
  la whitelist sta nel codice e `test_liste_configurabili_seed` la confronta
  col seed. La stessa soluzione (whitelist = cosa si può ordinare, catalogo =
  cosa si ordina) vale anche lì, ma è un cantiere a parte.
- `vendite.famiglie_documento` senza colonna `codice`: modifica di modello,
  richiesta nel brief DB §3.5.
- Il pannello generico dei codici (`dbops_repository`, `has_codice_interno`)
  cerca anche sul `codice_interno`: **resta così** (Tid, 2026-09-23).
- ⚠️ **Trovato il 24-09, fuori da questo cantiere**: il giornale trasversale
  (`vendite_repository.list_giornale_trasversale`) filtra `quando >= %s::date`
  nel fuso della connessione (UTC). Un evento registrato fra mezzanotte e le
  2 ora italiana finisce sotto il giorno prima; `test_il_giornale_mostra_solo_l_emittente_di_chi_legge`
  va rosso se gira in quella fascia. Da decidere se e dove aprirlo.
- I numeri di questo brief (32 liste, 12 + 11 + 9, più le 10 già convertite)
  sono una **fotografia del 2026-09-23**: la fonte è il registro nel test, non
  questo documento.

## 11. Revisione del 2026-09-24

Rilettura critica del diff non committato dei passi 3-5 (Tid, 24-09). Niente
di rotto a runtime: fragilità, copie, commenti fuori posto. Tutto corretto e
provato (suite senza DB e test sul DB vero verdi).

| Cosa | Dove | Correzione |
| --- | --- | --- |
| Dichiarazioni di testate e righe **cablate per famiglia** (`INVENTARI`, `RETTIFICHE`): una terza famiglia avrebbe dato `KeyError` a ogni apertura di lista, anche senza cercare — contro il contratto di `famiglie.py` («una famiglia è una riga qui, non un `if` altrove») | `magazzino_repository` | derivate da `FAMIGLIE` coi flag `ha_descrizione` / `con_motivo`, gli stessi che decidono la `SELECT`; `_RICERCA_ARTICOLO` al posto di sei copie |
| `"".join(f"AND {c}" …)`: senza separatore, con due condizioni avrebbe scritto `AND xAND y` (oggi regge solo perché il BB ne aggiunge una) | emittenti ×2, fornitori, registri, righe di distinta | la forma di `famiglie_documento`: lista `conditions` e `" AND ".join` |
| Due mappe di pagamenti con le stesse espressioni, su liste che proiettano la stessa `_RIGA_COLONNE` | `pagamenti_repository` | una base `_RICERCA_RIGA`; la coda aggiunge `contabile_codice` |
| Commenti finiti sopra il codice sbagliato | `tipi_ruolo_tipi_indirizzo_repository`, `test_ricerca_full_seed` | rimessi al loro posto |

**Regola del 2 fra domini (ok Tid, 24-09) — `param_ricerca_full`** in
`core/api/openapi_params.py`, a catalogo BB. Il parametro `search` delle liste
sul BB era dichiarato una trentina di volte, con testi già separati dal
codice: «min 2», «>=3 char» dove il 400 era ritirato, «P.IVA, C.F.» dove si
cerca l'id fiscale univoco, il codice interno che non si cerca. La frase non
elenca più le colonne (le decide il catalogo) e dice la soglia vera della
view. ⚠️ Una lista che passa al BB (passo 7) passa anche a questo parametro,
nello stesso giro.

**Strumenti AI — la soglia è un errore (Tid, 24-09).** Le liste sul BB
ignorano un termine sotto `RICERCA_MIN_CARATTERI`: a video va bene, ma un
modello riceverebbe tutte le righe credendole filtrate. `AITool.termine_ricerca`
solleva un `ValueError` che nomina termine e soglia (l'executor lo gira al
modello, che si corregge al giro dopo), usato dalle sette `Cerca*` che passano
`search` a una lista. Fuori: `cerca_articoli`, che è una lookup. Presidio:
`ai_assistant/tests/tools/test_base_termine_ricerca.py`.

**Frontend — commenti.** `magazzino/api/magazzino.js` (soglie, colonne dal
catalogo, `search` su righe e movimenti) e cinque file di pagamenti che
dicevano «questa lista non ha ricerca testuale»: ora dicono che il BE cerca
dal 23-09 e che la casella arriva al passo 6. Il codice FE non è cambiato.

## 12. La guardia di contesto utente — ✅ codice DB applicato, ⏳ BE

> ✅ **2026-09-24, team DB**: `E_UI_CHIAMATA_NON_VALIDA` è a catalogo su dbdev
> (`codici_errore.csv`, classe `TECNICO`; `messaggi_errore.csv`, id **1121**),
> frase chiusa senza `%s`: *«Chiamata non valida alla configurazione della
> lista: il contesto della richiesta non corrisponde all'utente.»* Restano i tre
> passi BE qui sotto (rigenerare le policy: il DB è allineato). Dettaglio:
> brief DB §6.4.

**Il problema.** `get_lista_config_per_video` mette insieme due letture con
due fonti diverse per l'utente:

| Lettura | Utente da |
| --- | --- |
| la configurazione (`ui.fn_resolve_lista_config`) | `user.id`, passato esplicito |
| `ricerca_full` e la ricerca vera (`ui.fn_lista_colonne_ricerca_full`, il BB) | la GUC `app.current_user_id`, impostata da `JwtAuditMiddleware` |

⭐ **L'emittente non c'entra**, verificato sulla doc auto-generata: il livello
di colonna (`ui.fn_lista_colonne_livello`) dipende da lista, utente e veste;
l'emittente entra solo nella scelta del preset. Su questo le due letture non
possono separarsi.

In una richiesta HTTP le due fonti dell'utente coincidono. Il modello però
ammette il caso in cui non coincidono: la GUC vuota fuori da una richiesta, o
un contesto aperto per un utente diverso. Allora la ricerca toglie le colonne
sensibili (senza utente nessun grant) mentre la configurazione le mostra, e la
casella dice una cosa diversa da quella che la ricerca fa — senza nessun
errore.

**La decisione.** Il BB deve leggere la GUC: i repository non ricevono
l'utente, ed è la scelta di §2.2. La casella deve dire la stessa cosa della
ricerca. Quindi non si sceglie una delle due fonti: **una differenza deve
fare rumore**. In `get_lista_config_per_video`, prima di leggere
`ricerca_full`: se `app.current_user_id` è vuota o diversa da `user.id` →
errore tecnico.

**Richiesta al team DB** — un codice nuovo a catalogo:

- **codice**: `E_UI_CHIAMATA_NON_VALIDA`, classe **`TECNICO`**. Gemello di
  `E_MAG_`, `E_PAGAMENTI_` ed `E_VENDITE_CHIAMATA_NON_VALIDA`: un valore che
  nessuna interfaccia produce, qui un contesto di sessione incoerente con
  l'utente della chiamata;
- sollevato dal **backend** (`ui_service`), non da una funzione DB;
- messaggio senza `%s`; nel contesto `lista_codice`, `auth_user_id` e
  l'utente della GUC.

⛔ `E_UI_GENERIC_FAILED` non va bene: è `DATO_ERRATO`, e su un guasto di
contesto l'operatore non ha niente da correggere. Nemmeno
`E_SCOPE_SENZA_UTENTE`: dice «scrittura su tabella con perimetro senza
utente», e copre solo il caso della GUC vuota.

**Dopo il codice, lato BE:**

1. rigenerare le policy (col DB **allineato** a git) e aggiungere il ripiego
   in `error_messages_fallback.py`;
2. **regola del 2**: la lettura della GUC `app.current_user_id` esiste già in
   `pagamenti_repository.emittente_nel_perimetro`. Alla seconda occorrenza si
   estrae `utente_di_sessione()` in `core/db` e la copia di pagamenti si
   ritira nello stesso giro;
3. la guardia in `get_lista_config_per_video`, con i test: GUC vuota → errore;
   GUC di un altro utente → errore; GUC uguale → `ricerca_full` letta.

