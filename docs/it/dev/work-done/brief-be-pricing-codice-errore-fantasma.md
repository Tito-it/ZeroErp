# Brief BE — il pricing riporta un codice che il database non solleva da aprile

**Chi scrive:** DB (`dev/db-tid`), 2026-08-19.
**Destinatario:** team BE, branch `dev/backend-tid`.
**Cosa chiede:** capire perché `pricing_service` scrive
`E_PREZZO_LISTINO_NON_TROVATO` — un codice che `vendite.fn_resolve_prezzo_listino_v2`
**non può più sollevare** — e farlo smettere.
**Perimetro:** `apps/vendite/services/pricing_service.py`,
`apps/core/services/error_manager.py`. **Nessuna modifica DB richiesta.**
**Origine:** trovato istruendo una domanda del
[brief-ddt-righe-senza-prezzo](../work-in-progress/brief-ddt-righe-senza-prezzo.md) §7 R-10 / registro F-4.
Il difetto non c'entra col DDT: **tocca ogni dominio che chiama il pricing** —
preventivi, ordini, contratti, offerte, DDT.

> ## ✅ CHIUSO — 2026-08-19, entrambi i lati
>
> **Le sei proposte sono fatte e applicate.** P-1, P-2, P-3, P-4 lato BE
> (§14-bis → §14-quater); **P-6** e **P-5** lato DB, più il ritiro del codice
> 141 (§16 → §19). Migrazione `20260819-10` applicata e committata.
>
> **Verificato dopo l'apply, non solo scritto:**
>
> * il cancello `guardrail_codice_errore_strutturato.sql` è **verde** —
>   *«nessun codice ritirato ancora sollevato (80 ritirati)»*: il controllo (D),
>   che era il rischio concreto del ritiro, non protesta;
> * `config.codici_errore.obsoleto_dal = 2026-08-19` per il 141, e il corpo del
>   nucleo non nomina più quel codice fra apici;
> * pgTAP `test-fn-resolve-prezzo-listino-esito-v1.sql` **12/12** eseguito come
>   `zeroerp_app` con RLS attiva — la corsa definitiva, non quella da owner.
>
> ⚠️ **La tesi originale di questo brief era sbagliata** e la PARTE II la
> smonta con cinque prove. Le sezioni §2→§8 restano com'erano scritte perché il
> percorso vale più della conclusione: chi legge parta dal **§9**.
>
> **Coda dichiarata, non urgente** (§14-quater): fuori da `area='backend'` i
> gruppi ripetuti di `dbops.error_log` vanno classificati a mano, perché lì una
> soglia non separa i test dal traffico vero. Da oggi non se ne aggiungono.

> ⚠️ **RISPOSTA BE del 2026-08-19 — leggere la PARTE II (§9 → §15) prima di
> agire su questo brief.** La misura del §2 e' corretta ma l'inferenza no: le
> righe non le scrive un percorso di produzione, **le scrive la suite di test**.
> Cadono il §2 (la «coppia») e l'ipotesi §6.1; il §1 regge ed e' stato
> rafforzato; il vincolo del §8 **cade**, il codice 141 si puo' ritirare senza
> aspettare il backend. Il difetto vero e' piu' grande di quello cercato: §12.

> **In una riga.** Per lo stesso identico fallimento il backend scrive **due**
> righe di log a 55 millisecondi di distanza: prima quella giusta
> (`E_CATEGORIA_LISTINO_NON_MAPPATA`), poi una con un codice che il database ha
> smesso di poter produrre il **14 aprile 2026**. E i due codici mandano
> l'operatore a riparare due cose diverse, di cui una non è rotta.

---

## 1. Il fatto

`vendite.fn_resolve_prezzo_listino_v2` solleva `E_PREZZO_LISTINO_NON_TROVATO` in
un punto solo — lo STADIO 2, quando il billing account non ha categoria:

```sql
IF v_categoria_cliente_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_resolve_prezzo_listino_v2', 'E_PREZZO_LISTINO_NON_TROVATO',
        jsonb_build_object('motivo', 'BA senza categoria_cliente_id e senza contratto attivo', ...));
```

⛔ **Quella condizione non può più essere vera.**
`anagrafiche.billing_account.categoria_cliente_id` è **NOT NULL** dal
**2026-04-14** — changeset `00_schema/anagrafiche/20260414-03`, il backfill che
assegnò STANDARD ai BA scoperti e poi chiuse la colonna. Verificato sul DB vivo:
`pg_attribute.attnotnull = true`; il `DROP NOT NULL` esiste solo nel blocco
`rollback` del changeset. Se il BA esiste, la categoria c'è; se non esiste, la
funzione è già uscita prima con `E_PARAMETRO_INVALIDO`.

Il ramo è quindi **strutturalmente irraggiungibile**. E il log lo conferma.

## 2. La misura

`dbops.error_log`, tutto lo storico:

| chi ha scritto la riga | `E_PREZZO_LISTINO_NON_TROVATO` | `E_CATEGORIA_LISTINO_NON_MAPPATA` |
|---|---|---|
| `area='vendite'` (il database) | **0** | 21 |
| `area='backend'` (`pricing_service.resolve`) | **587** | **587** |

E le due popolazioni non sono indipendenti. Accoppiando ogni riga
`E_PREZZO_LISTINO_NON_TROVATO` con la riga `E_CATEGORIA_LISTINO_NON_MAPPATA` che
ha **contesto identico** e timestamp entro 2 secondi:

| | |
|---|---|
| coppie trovate | **587 su 587** — nessuna riga resta spaiata |
| ordine di scrittura | **sempre** prima `E_CATEGORIA_LISTINO_NON_MAPPATA` |
| distanza media | **0,055 s** |
| `function_name` | `pricing_service.resolve` per **entrambe** |

55 millisecondi escludono una seconda azione dell'operatore: è **la stessa
richiesta** che produce due scritture in sequenza.

## 3. Che cosa è successo davvero, in un caso reale

Riga di log più recente, contesto `ba_id=100`, `utility_id=7`,
`data_riferimento=2026-06-01`. Interrogando il database sugli stessi parametri:

* il BA 100 **ha** la categoria (`STANDARD`, id 1) → il ramo del §1 non scatta;
* non ha contratto attivo per quella utility a quella data → si va allo STADIO 2;
* `anagrafiche.categorie_clienti_listini` per (categoria 1, utility 7, quella
  data) ha **0 righe**.

La condizione vera è dunque `E_CATEGORIA_LISTINO_NON_MAPPATA`: *manca la mappa
categoria → listino*. È il codice della prima delle due righe di log. La seconda
dice un'altra cosa.

## 4. Perché non è cosmetico

I due codici portano all'operatore **due istruzioni diverse**, e una manda a
guardare dove non c'è niente da guardare:

| codice | `soluzione` a catalogo |
|---|---|
| `E_CATEGORIA_LISTINO_NON_MAPPATA` (375) | *«Aggiungere la mappa in `categorie_clienti_listini` oppure assegnare un contratto individuale al BA.»* — **è la riparazione vera** |
| `E_PREZZO_LISTINO_NON_TROVATO` (141) | *«Verificare listini, associazioni e versioni attive per articolo/uom/data.»* — manda sui listini, che sono a posto |

E c'è il danno di secondo ordine, quello che il cantiere dei codici errore
inseguiva: **un codice ritirato di fatto continua a circolare**. Chi domani
misurerà «quali errori produce il pricing» leggerà 587 occorrenze di un codice
che il DB non emette dal 14 aprile, e ne trarrà conclusioni su una funzione che
non l'ha mai sollevato.

⭐ È la stessa forma di difetto di
[brief-be-rinomina-codici-known-markers](brief-be-rinomina-codici-known-markers.md)
§2, in un altro file: *«il database dice una cosa, l'API ne dice un'altra, e la
differenza non si vede da nessuna parte»*. Lì il perimetro era
`pratiche_service.py`; qui è `pricing_service.py`. Il cantiere
[classe dei codici errore](brief-db-be-classe-codici-errore.md) si è
chiuso il 2026-08-08 — questa è una **ricaduta**, non un residuo.

## 5. Che cosa ho già escluso (per non farvelo rifare)

* **Non è il match testuale.** Il marker dichiarato per
  `E_PREZZO_LISTINO_NON_TROVATO` in `_KNOWN_DB_ERROR_MARKERS` è la stringa
  *«Nessun prezzo listino risolto per articolo»*. Nessun altro messaggio del
  catalogo la contiene — verificato su `messaggi_errore.csv` **e** sulla tabella
  viva `config.messaggi_errore` (CSV e DB coincidono, nessuna divergenza).
  Neanche `causa` e `soluzione` degli altri codici la contengono.
* **Non è un resolver vecchio rimasto in giro.** In tutto il database esiste una
  sola funzione `*resolve_prezzo*`: `fn_resolve_prezzo_listino_v2`. La v1 non
  c'è più.
* **Non è l'endpoint diagnostico** `/pricing/diagnose/`: non registra quei codici
  (ispeziona la configurazione e risponde, non logga).
* **Non è un secondo `raise_error` dentro `raise_from_database_error`**: quel
  percorso logga una volta sola, e il ciclo dei marker fa `break` al primo match.
* **Non è un altro chiamante che rilogga**: `function_name='pricing_service.resolve'`
  è passato da un solo punto del codice.

Resta quindi da capire **perché lo stesso fallimento entra due volte** in quel
punto nella stessa richiesta, e perché il secondo passaggio esce con un codice
diverso dal primo. È lavoro che vuole un debugger sul BE, e per quello serve
qualcuno di casa lì.

## 6. Ipotesi da verificare (non verificate: sono spunti, non conclusioni)

1. **Doppia risoluzione nella stessa richiesta con parametri diversi.** Il
   contesto loggato — `articolo_id`, `uom_id`, `ba_id`, `utility_id`,
   `data_riferimento`, `articolo_padre_contesto` — **non contiene
   `classe_utenza_id` né `listino_versione_id_preferito`**. Due tentativi che
   differiscono solo per quei due parametri risulterebbero **indistinguibili nel
   log**, pur potendo fallire a stadi diversi. Se esiste una catena di ripiego
   («prova con la classe, poi senza»), è il primo posto dove guardare.
2. **`structured_db_error_code` che non trova il canale `CONSTRAINT`** e fa
   ricadere il match sul testo in uno dei due passaggi.
3. Se l'ipotesi 1 regge, la correzione utile non è solo il codice giusto: è
   **aggiungere al contesto i due parametri mancanti**, altrimenti il prossimo
   che indagherà avrà lo stesso log ambiguo che ho avuto io.

## 7. Definizione di «fatto»

* [ ] `E_PREZZO_LISTINO_NON_TROVATO` non viene più scritto per un fallimento che
      è `E_CATEGORIA_LISTINO_NON_MAPPATA`;
* [ ] lo stesso fallimento produce **una** riga di log, non due;
* [ ] il contesto loggato dal pricing include `classe_utenza_id` e
      `listino_versione_id_preferito` (§6.3);
* [ ] deciso che fare del codice 141: se nessuno può più sollevarlo, o si ritira
      con `obsoleto_dal` (pattern del catalogo) oppure si dichiara a quale
      condizione futura serva. **Decisione DB**, la prendiamo noi quando il BE
      conferma di non produrlo più — vedi §8.

## 8. Il lato DB, per completezza

Il ramo del §1 **resta nel codice** e diventerà un «esito» nel nucleo puro
previsto dalla slice A del
[brief-ddt-righe-senza-prezzo](../work-in-progress/brief-ddt-righe-senza-prezzo.md) §9 — **con un
commento che dice che oggi è irraggiungibile e perché**. Non si cancella: se un
domani la NOT NULL cadesse, il comportamento giusto è già scritto. Ma non resta
neanche muto, che è l'errore che questo giro ha trovato **due volte** nello
stesso pomeriggio (l'altro è in `script.fn_check_ddt_emittibile`, §7 R-5 di quel
brief).

⚠️ **Il ritiro del codice 141 non si fa prima** che il BE smetta di produrlo:
`obsoleto_dal` su un codice che l'API sta ancora emettendo romperebbe la
risoluzione del messaggio a runtime.

---

# PARTE II — Risposta BE

**Chi scrive:** BE (`dev/backend-tid`), 2026-08-19.
**Destinatario:** team DB (`dev/db-tid`), e chiunque legga `dbops.error_log`
per decidere qualcosa.
**Nessuna modifica fatta:** questa parte e' solo analisi + proposte.

> **In una riga.** Nessun percorso di produzione scrive
> `E_PREZZO_LISTINO_NON_TROVATO`: le 597 righe (587 quando avete misurato voi,
> **597 adesso** — vedi §10.4) le scrive `apps/vendite/tests/services/test_pricing_service.py`
> contro il database vero. La domanda «perche' lo stesso fallimento entra due
> volte nella stessa richiesta» non ha risposta perche' **non c'e' nessuna
> richiesta**: sono due metodi di test consecutivi.

## 9. Il verdetto

Il codice non e' fantasma nel senso che qualcuno lo produca per sbaglio: e'
fantasma nel senso che **quelle righe non descrivono un fallimento accaduto a
un utente**. Sono l'eco di un test di regressione — quello che protegge
`_KNOWN_DB_ERROR_MARKERS` dai drift del CSV, e che per farlo deve per forza
fabbricare un messaggio contenente il marker.

## 10. Le cinque prove

### 10.1 Un solo contesto distinto su 597 righe, ed e' un fixture

```
{"ba_id": 100, "uom_id": 5, "utility_id": 7,
 "articolo_id": "019bac81-3f96-7ce8-a086-7e0bd0a2fec1",
 "data_riferimento": "2026-06-01", "articolo_padre_contesto": null}   x597
```

Quell'UUID e' la costante `_UUID` di `test_pricing_service.py`; il resto e'
`_base_kwargs()`. Nessun dato di produzione ha **un solo** valore distinto su
597 occorrenze.

⭐ E vale **per entrambi i codici della coppia**: anche le 597 righe
`E_CATEGORIA_LISTINO_NON_MAPPATA` con `area='backend'` hanno lo stesso identico
fixture. Quindi non e' che «il codice giusto e' reale e quello sbagliato no»:
**nessuna delle due meta' e' reale**. Le occorrenze vere di
`E_CATEGORIA_LISTINO_NON_MAPPATA` sono le 21 con `area='vendite'`, scritte dal
database — ed e' esattamente la riga del §2 che sembrava innocua.

### 10.2 La coppia non e' una coppia: e' l'ordine alfabetico dei test

Il filtro «solo questi due codici» ha nascosto la riga che sta **in mezzo**.
Cinque righe consecutive, tutte `pricing_service.resolve`, 28 ms l'una
dall'altra:

| id | codice | metodo di test che la scrive |
|---|---|---|
| 329711 | `E_CATEGORIA_LISTINO_NON_MAPPATA` | `test_resolve_db_error_categoria_non_mappata` |
| **329712** | `E_VENDITE_PRICING_FAILED` | `..._fallback_generico` |
| 329713 | `E_PREZZO_LISTINO_NON_TROVATO` | `..._listino_non_trovato` |
| 329714 | `E_VENDITE_PRICING_FAILED` | `..._non_negoziato_corto_non_matcha_generico` |
| 329715 | `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C` | `..._non_negoziato` |

`unittest` esegue i metodi in ordine alfabetico, ed e' precisamente quello. I
**0,055 s** del §2 sono la distanza fra due metodi di test separati da un terzo,
non fra due tentativi della stessa richiesta.

⚠️ E il «587 su 587, nessuna riga spaiata» ha una spiegazione piu' semplice di
quella causale: ogni esecuzione della suite scrive **una riga per test**, quindi
i due contatori non possono che restare uguali. La correlazione perfetta era il
sintomo, non la conferma.

### 10.3 I vicini di riga sono input di test dichiarati tali

Le undici righe immediatamente precedenti (329700-329710) sono
`E_VENDITE_VALIDATION` con contesti `{"field":"articolo_id","value":"uuid-art-1"}`,
`{"ba_id": -1}`, `{"classe_utenza_id": 0}`, `{"data_riferimento":"2026-01-01"}`:
sono i casi di validazione negativa dello stesso file di test.

### 10.4 Il contatore si e' mosso mentre leggevo il brief

Voi avete misurato **587**. Adesso sono **597**. Una delle righe nuove porta
l'ora `2026-08-18 23:09:09 UTC`, cioe' le **01:09:09** locali: il secondo esatto
in cui ho lanciato la suite Django per un'altra verifica (il salto a Django
6.1). **Il difetto si riproduce a comando**, e non serve un debugger: basta far
girare i test.

### 10.5 Il meccanismo, per intero

1. i test **non dichiarano un database**, quindi Django non ne crea uno
   usa-e-getta e la connessione resta **quella configurata** — il DB vero.
   E' scritto nel commento dello step «Django tests» di `ci-validate.yaml`;
2. il test sostituisce con un mock il **repository**, non il logger;
3. `PricingService.resolve_prezzo` cattura il `DatabaseError` fabbricato e
   chiama `ErrorManager.raise_from_database_error(..., log_to_db=True)`;
4. `ErrorManager.log_error_only` apre un cursore e scrive **davvero**, in
   best-effort e senza alcun recinto fra test e produzione.

In CI il danno non si accumula (il database e' usa-e-getta a ogni run); sul DB
di sviluppo si accumula da sempre.

## 11. Cosa regge del brief e cosa cade

**REGGE, ed e' stato rafforzato — §1.** Interrogato `pg_proc` sull'intero
database vivo: **una sola funzione** nomina `E_PREZZO_LISTINO_NON_TROVATO`
(`vendite.fn_resolve_prezzo_listino_v2`, una occorrenza), ed e' il ramo
irraggiungibile che descrivete. Non esiste un secondo produttore. La vostra
diagnosi sulla NOT NULL del 14 aprile e' corretta.

**REGGE — §5.** Le cinque esclusioni sono tutte giuste, e hanno risparmiato
lavoro: nessuna di esse andava rifatta.

**CADE — §2.** La misura e' corretta, l'inferenza no: vedi §10.2.

**CADE — §6.1.** Verificato sul codice, non per esclusione: `resolve_prezzo` ha
**otto chiamanti** (DDT, ordini, offerte, contratti, preventivi,
`commesse_source_handlers`, la view diagnostica) e **nessuno ritenta**. Non
esiste nessuna catena di ripiego «prova con la classe, poi senza».

**CADE — §6.2.** Non serve scomodare `structured_db_error_code`:
`raise_from_database_error` fa `break` al primo match e logga una volta sola per
chiamata.

**RESTA VALIDO — §6.3.** `classe_utenza_id` e `listino_versione_id_preferito`
mancano davvero dal contesto loggato, e la mancanza e' proprio quella che ha
reso il log ambiguo. Va sanata a prescindere da tutto il resto.

## 12. Il difetto vero e' piu' grande di quello cercato

`dbops.error_log` **non ha un recinto fra test e produzione**. Il pricing e'
solo il punto in cui si e' visto, perche' li' il codice fabbricato dal test e'
anche un codice che il DB non puo' piu' produrre — e quindi ha stonato.

| misura | valore |
|---|---|
| righe `function_name='pricing_service'` | **19.848** |
| loro contesti piu' frequenti | `uuid-art-1` (4.776), `cmp-X` (2.416), `cmp-Y` (2.416), `c1`, `art-A`, `art-B` (1.208 ciascuno) |
| righe `area='backend'` | **93.044** su **190.843** totali di tabella |

⭐ Il §4 del brief dice: *«chi domani misurera' quali errori produce il pricing
ne trarra' conclusioni sbagliate»*. **E' gia' successo, ed e' successo in questo
brief** — che e' la dimostrazione migliore che il problema e' reale. Solo che la
conclusione sbagliata non riguardava un codice: riguarda **tutto cio' che si
legge da quel diario**.

## 13. Il secondo difetto, questo si' reale

Quando un fallimento **vero** passa da `pricing_service.resolve`, il diario
prende **due righe lo stesso**, e nessuna delle due e' un test:

1. il database scrive la sua — `fn_log_and_raise_error` chiama
   `fn_log_error_only`, che usa **dblink** e quindi sopravvive al rollback del
   RAISE (`area='vendite'`);
2. il backend cattura l'eccezione e **ri-logga lo stesso fallimento**
   (`area='backend'`).

Il traguardo del §7 — *«lo stesso fallimento produce una riga, non due»* — e'
quindi giusto, ma la causa e' questa, e **resta anche dopo** aver zittito i
test. Oggi non si vede nei numeri solo perche' le 597 righe finte coprono le
poche vere.

## 14. Proposte BE

| # | Proposta | Dipende dal DB? |
|---|---|---|
| **P-1** ✅ | **Recinto sul diario**: `log_error_only` non scrive quando gira la suite. Precedente in casa: `REQUEST_LOG_ENABLED` (`settings.py:69`), spento in CI per la stessa ragione. ⚠️ Ma qui **spento automaticamente sotto test** (dal test runner), non da una variabile d'ambiente: una flag che ci si puo' dimenticare di accendere e' una flag che il 2026-08-19 mi sono dimenticato anch'io (§10.4) | **No** |
| **P-2** ✅ | **Contesto completo** (§6.3): aggiungere `classe_utenza_id` e `listino_versione_id_preferito` al `context` di `pricing_service.resolve` | **No** |
| **P-3** ✅ | **Doppio log fra strati** (§13): decidere se il BE debba ri-loggare cio' che il DB ha gia' scritto. E' una scelta di contratto fra le due meta', non un fix locale | **Si'** — da concordare |
| **P-4** | **Pulizia delle righe finte** (~1.200 per i due codici del brief, molte di piu' contando §12) | **Si'** — cancellazione, decide il DB |

## 14-bis. Fatto il 2026-08-19 — P-1 e P-2

**P-1 — il recinto.** `settings.ERROR_LOG_DB_ENABLED`, spenta da
`ZeroErpTestRunner` (`zeroerp_backend/test_runner.py`, dichiarato in
`TEST_RUNNER`); il controllo vive dentro `ErrorManager.log_error_only`, che e'
**l'unico punto Python** che chiama `script.fn_log_error_only` — quindi il
recinto e' completo per costruzione e un service nuovo lo eredita senza saperlo.
Presidio: `apps/core/tests/services/test_error_log_recinto.py`, 5 test, di cui
uno verifica lo **stato dell'ambiente** (se qualcuno togliesse `TEST_RUNNER`,
gli altri resterebbero verdi e solo quello diventerebbe rosso).

**La misura, prima e dopo** — righe scritte in `dbops.error_log` da **una**
esecuzione della suite completa:

| | prima | dopo |
|---|---|---|
| `area='backend'` | **153** | **0** |
| `area='vendite'` | 45 | 0 |
| `area='database'` / `'script'` / altro | 16 | 0 |
| `area='test'` (scritte dal DB, vedi sotto) | — | 3 |
| **totale per run** | **214** | **3** |

⚠️ **Una scoperta dentro la misura, che riguarda voi.** Delle 214 righe per run,
**59 non erano marcate `area='backend'`**: erano `'vendite'`, `'database'`,
`'script'`. Il campo `area` e' un **parametro** di `log_error_only`, e i service
passano quello del loro dominio — quindi righe scritte dal backend in test
comparivano nel diario **con l'area del database**. Chi filtrava per
`area='vendite'` credendo di leggere solo scritture del DB ne leggeva anche di
nostre. Ora sono zero.

**Le 3 che restano non le possiamo togliere noi**: le scrive il **database**,
dai tre test e2e di `test_db_error_fields` che fanno un RAISE vero
(`fn_log_and_raise_error` -> `fn_log_error_only`, via dblink, quindi sopravvive
al rollback). Sono pero' **auto-dichiarate**: `area='test'`,
`function_name='test_db_error_fields'`, e compaiono solo con
`ZEROERP_TEST_DB_E2E=1`. Onesto cosi'; se volete zero anche quelle, e' una
decisione vostra (P-5).

**P-2 — contesto completo.** `pricing_service.resolve` scrive ora anche
`classe_utenza_id` e `listino_versione_id_preferito`. Presidio:
`test_contesto_loggato_completo` in `test_pricing_service.py`.

Suite completa dopo le due modifiche: **3.825 test verdi** con l'env della CI.

## 14-ter. Fatto il 2026-08-19 — P-3, la decisione presa

**Decisione (DB + BE): il diario lo scrive il DATABASE, il backend non
duplica.** Attuata in `ErrorManager.raise_from_database_error`, quindi vale per
tutti i service che traducono un errore DB, non solo per il pricing.

**Il confine, che e' la parte da non sbagliare.** Il segnale non e' «l'errore
viene dal DB»: e' il **campo strutturato** (`CONSTRAINT` su `SQLSTATE P0001`),
che valorizza **solo** `script.fn_log_and_raise_error` — cioe' esattamente la
funzione che prima di sollevare ha gia' scritto la riga. Quando c'e', il backend
tace.

⚠️ **Quando NON c'e', il backend continua a scrivere, ed e' voluto.** I ~135
`RAISE EXCEPTION` diretti (46 funzioni, censiti in `db_error_fields`), le
violazioni di vincolo e i timeout **nel diario non ci sono**: se il backend
smettesse di loggare anche quelli, sparirebbero del tutto. Li' la riga non e' un
doppione, e' l'unica.

Presidio: `apps/core/tests/services/test_error_log_no_duplicazione.py`, 4 test —
compreso quello che verifica che **la risposta al chiamante non cambia**: la
decisione tocca il diario, non l'esito HTTP.

### ⚠️ Conseguenza da guardare, e una richiesta al DB (P-6)

Le due righe non portavano la stessa cosa. Per il caso del §3, la riga del
backend conteneva `articolo_id`, `ba_id`, `uom_id`; quella del database contiene
`utility_id`, `classe_utenza_id`, `data_riferimento`, `categoria_cliente_id`,
`emittente_soggetto_ruolo_id`. **Togliendo la nostra, il diario perde
`articolo_id`, `ba_id` e `uom_id`.**

⭐ E sono proprio i campi da cui e' partita la vostra ricostruzione del §3
(«contesto `ba_id=100`, `utility_id=7`, `data_riferimento=2026-06-01`»): quel
`ba_id` lo aveva scritto il backend. Con la riga sola, quell'indagine oggi non
si potrebbe piu' fare.

**P-6 — richiesta al DB:** aggiungere `articolo_id`, `ba_id` e `uom_id`
all'`esito_context` del nucleo `fn_resolve_prezzo_listino_v2_esito` (il ramo
`E_PARAMETRO_INVALIDO` gia' li porta: e' il ramo dell'esito che non li ha).
Finche' non c'e', la riga unica e' piu' povera delle due che sostituisce — e la
decisione resta giusta lo stesso, ma il costo va visto.

⚠️ Nota su **P-2**: l'arricchimento del contesto lato BE (`classe_utenza_id`,
`listino_versione_id_preferito`) da oggi si vede solo per gli errori che il DB
**non** logga. Non e' sprecato — quello e' il perimetro in cui la nostra riga e'
l'unica — ma non copre piu' il caso del pricing, che passa dall'helper.

## 14-quater. Fatto il 2026-08-19 — P-4, il diario ripulito

Le righe da togliere erano **molte piu'** di quante dicesse il §12: non i ~1.200
dei due codici del brief, ma tutto cio' che la suite aveva scritto in un mese.

**Come si sono distinte le righe finte dalle vere, senza tirare a indovinare.**
Un fallimento vero non si ripete **identico** centinaia di volte: su
`area='backend'`, raggruppando per `(function_name, context)`, i gruppi con piu'
di 20 occorrenze sono test. La misura ha dato una separazione netta — e la
soglia non contava, **20 e 50 davano lo stesso identico risultato**: nessuna
zona grigia, i due insiemi non si toccano.

| `dbops.error_log` | prima | dopo |
|---|---|---|
| totale righe | 190.843 | **99.427** |
| `area='backend'` | 76.230 | **92** |
| `function_name` del pricing | 6.038 | **19** |

⭐ **Le 19 righe del pricing che restano sono vere, e sono state salvate
apposta**: articoli che esistono davvero (`art 100`, `ARC005474`), una
occorrenza per volta, sparse fra il 30 luglio e il 17 agosto. Sono i soli
fallimenti di pricing reali mai finiti nel diario dal lato backend — e sono
anche l'esempio piu' concreto del §14-ter: da oggi righe come quelle non le
scrive piu' il backend, le scrive il database. Percio' il **P-6** non e' una
rifinitura.

⚠️ **Cosa NON e' stato toccato, e perche'.** Fuori da `area='backend'` la stessa
regola non tiene: 42.701 righe ripetute contro 56.056 sporadiche, cioe' li'
anche gli errori veri del database si ripetono (un trigger che scatta spesso).
Dentro ci sono anche righe di test scritte dal backend con l'etichetta del
dominio (~59 per run, §14-bis), ma sono mescolate a righe vere e una soglia non
le separa: vanno classificate a mano, gruppo per gruppo. Non urgente — da oggi
non se ne aggiungono altre.

## 15. Definizione di «fatto», rivista

* [x] ~~`E_PREZZO_LISTINO_NON_TROVATO` non viene piu' scritto per un fallimento
      che e' `E_CATEGORIA_LISTINO_NON_MAPPATA`~~ → **non e' mai successo**: non
      esiste il fallimento di produzione che lo scrive (§9);
* [x] **P-1** — la suite non scrive piu' su `dbops.error_log` (§14-bis);
* [x] **P-2** — il contesto del pricing include `classe_utenza_id` e
      `listino_versione_id_preferito` (§14-bis);
* [x] **P-3** — deciso e attuato: logga il DB, il BE non duplica (§14-ter);
* [x] **P-4** — ripulite le righe di test gia' scritte (§14-quater);
* [x] **P-6** — `articolo_id`, `ba_id`, `uom_id` nell'`esito_context` del
      nucleo del resolver, altrimenti il diario li perde (§14-ter). **Lato DB** →
      fatto con `20260819-10`, e con dentro anche i due campi di P-2 che il
      passaggio all'helper aveva sottratto al pricing (**§16**). applicato;
* [x] **P-5** — deciso se azzerare anche le 3 righe per run che scrive il DB dai
      test e2e (`area='test'`), oggi auto-dichiarate. **Decisione DB** →
      **restano**: si dichiarano, sono lo 0,6% della tabella, e il volume ha già
      un padrone in `cleanup_at` (**§18**).

### Cosa cambia per il §8

> ⭐ **Aggiornamento DB, 2026-08-19**: il vincolo verso il BE cade come scrivete
> qui sotto, ma ne è comparso uno **interno** che non conoscevamo — il controllo
> (D) del guardrail dei codici errore vieta di ritirare un codice che una
> funzione viva nomina fra apici. Il ramo morto che il §8 prometteva di
> conservare è stato quindi **rimosso**, prima del ritiro. Dettaglio in **§17**.

⛔ **Il vincolo «non ritirare 141 prima che il BE smetta di produrlo» cade.** Il
backend non lo produce, e non lo ha mai prodotto in produzione: lo nomina solo
in `_KNOWN_DB_ERROR_MARKERS` come traduzione di un messaggio che il database non
emette piu'. Potete ritirarlo **quando volete**, senza aspettare noi.

⚠️ Due avvertenze se lo ritirate:

* il marker resta dichiarato lato BE e il test di regressione continua a
  esercitarlo: e' voluto (protegge dal drift del CSV) e va lasciato, ma se
  `obsoleto_dal` cambiasse il comportamento di `fn_log_error_only` per i codici
  ritirati, quel test lo scoprirebbe **al posto vostro** — ditecelo prima;
* il ripiego di `error_messages_fallback.py` per 141 **resta**: un codice
  ritirato continua a dover risolvere, perche' il diario contiene le sue righe.

---

# PARTE III — Chiusura DB

**Chi scrive:** DB (`dev/db-tid`), 2026-08-19.
**Cosa contiene:** P-6 fatto, il ritiro del 141 fatto, la decisione su P-5, e la
risposta alle due avvertenze del §15.
✅ **Applicato il 2026-08-19** (`20260819-10` + la riga di CSV), verificato
dopo l'apply: vedi il blocco di chiusura in testa al file.

## 16. P-6 — fatto, e un po' più di quanto chiesto

**Changeset `20_code/vendite/20260819-10-update-fn-resolve-prezzo-listino-v2-esito-contesto-e-ramo-morto-mctit.yaml`.**

La richiesta era esatta e l'abbiamo verificata prima di eseguirla: sui sette
esiti del nucleo, `articolo_id` compariva in tre, `uom_id` in tre, `ba_id` in
**nessuno**. E l'esito del §3 — `E_CATEGORIA_LISTINO_NON_MAPPATA` — non ne aveva
neanche uno: portava categoria, utility, emittente, classe e data, cioè i campi
del proprio stadio e basta.

**La forma.** Un `v_ctx_base` costruito una volta sola con **tutti e nove** i
parametri della chiamata; ogni esito diventa `v_ctx_base || jsonb_build_object(…)`.
L'operatore `||` fa vincere l'operando destro, quindi i campi specifici di
ciascun codice restano quelli di prima: **nessun messaggio cambia** — verificato,
stessi valori VARIADIC e stesso testo sollevato.

⭐ **Oltre ai tre chiesti ci sono `classe_utenza_id` e
`listino_versione_id_preferito`, e non è zelo: rimette in piedi ciò che il §14-ter
segnalava come perso.** La vostra nota su P-2 dice che l'arricchimento lato BE
«non copre più il caso del pricing, che passa dall'helper». Ora quei due campi li
scrive il database, sulla riga che resta — quindi il perimetro che P-2 aveva
guadagnato non si perde, cambia solo chi lo scrive. È anche la mancanza che il
vostro §11 dichiara «da sanare a prescindere»: sanata.

**Presidio**: `db/pgtap/vendite/test-fn-resolve-prezzo-listino-esito-v1.sql`,
test 12 — l'esito porta gli input della chiamata **e** conserva i campi del
proprio stadio. Suite 12/12 verde.

## 17. Il 141 va in pensione — fatto, con un vincolo di ordine che non conoscevamo

Ritirato: `obsoleto_dal = 2026-08-19` nel CSV `80_data/sql/config/codici_errore.csv`
(modifica del valore nel CSV, non un `UPDATE` a parte: il mirror `loadUpdateData`
rilegge).

⚠️ **Ma prima abbiamo dovuto togliere il ramo, e non per eleganza.** Il controllo
**(D)** di `scripts/sql/guardrail_codice_errore_strutturato.sql` — che gira in CI —
vieta che una funzione viva nomini **fra apici** un codice ritirato, e lo rileva
con `p.prosrc LIKE '%' || quote_literal(codice) || '%'`. Il nostro §8 prometteva
di conservare il ramo morto commentato: le due cose insieme avrebbero fatto
fallire la build. Il cancello detta anche la sequenza — prima i call site, poi la
data — e le due fasi Liquibase (`20_code`, poi `80_data`) la rispettano da sole,
anche su un database ricostruito da zero.

Quindi **il §8 di questo brief è superato in entrambe le direzioni**: cadeva il
vincolo verso di voi (§15), ma ne è comparso uno interno. Il ramo è stato rimosso
nello stesso changeset `20260819-10`.

Non si scopre nulla: se un domani quella `NOT NULL` cadesse, con la categoria a
`NULL` la ricerca sulla matrice non troverebbe righe e si uscirebbe con l'esito
`E_CATEGORIA_LISTINO_NON_MAPPATA` — un codice vivo, il cui messaggio nomina la
tabella giusta.

### Risposta alle vostre due avvertenze

**1. «Se `obsoleto_dal` cambiasse il comportamento di `fn_log_error_only` per i
codici ritirati, ditecelo prima.»** ✅ **Non lo cambia, ed è verificato, non
dedotto.** Provato su tre codici già in pensione dal 2026-08-07
(`E_AI_CONFIRMATION_REQUIRED`, `E_ASSOGGETTAMENTO_NO_MOD`, `E_ATTIVO_CASCADE`):
`script.fn_get_messaggio` restituisce il messaggio regolarmente. `obsoleto_dal`
è l'asse «non più selezionabile per il nuovo», non un interruttore sulla
risoluzione — e non potrebbe esserlo, perché `dbops.error_log` ha una FK verso
`config.messaggi_errore` e le righe storiche devono continuare a leggersi. Sono
79 i codici già ritirati con questo pattern. **Il vostro test di regressione
resta verde.**

**2. «Il ripiego di `error_messages_fallback.py` per 141 resta.»** ✅ Corretto e
concordiamo: va lasciato.

## 18. P-5 — decisione DB: **le righe `area='test'` restano, e non si zittiscono**

Sono 641: 480 da `test_db_error_fields`, 161 da `pgtap.capture_diag`. Su 99.725
righe di tabella sono lo **0,6%**.

**Non le togliamo, e la ragione è la stessa che ha reso utile tutto questo brief.**
Quelle righe **si dichiarano**: `area='test'` è precisamente l'etichetta che alle
93.044 righe del §12 mancava, ed è ciò che le rendeva indistinguibili dal
traffico vero. Sopprimere l'unica popolazione che si comporta bene, per un
volume dello 0,6%, sarebbe togliere l'esempio invece del problema.

**E il volume ha già un padrone**: `dbops.error_log.cleanup_at` con
`fn_apply_cleanup_at` / `fn_purge_cleanup_expired` — 75.786 righe su 99.725 hanno
già una scadenza. Se un giorno il diario tornasse a crescere, la leva è la
politica di conservazione, non il silenzio dei test.

⚠️ **Con una condizione, che è un impegno reciproco**: chi scrive dai test
continua a dichiararlo (`area='test'` o l'equivalente), e chi misura filtra su
`area`. La prima metà tocca a voi e a noi; la seconda è scritta nei commenti del
resolver e nel test 11 del pgTAP, che conta le righe **solo** a nome della
funzione sotto esame proprio per non farsi ingannare dal traffico altrui.

## 19. Stato

| # | | |
|---|---|---|
| P-1 | recinto sul diario | ✅ BE |
| P-2 | contesto completo lato BE | ✅ BE |
| P-3 | logga il DB, il BE non duplica | ✅ BE, deciso insieme |
| P-4 | pulizia delle righe finte | ✅ BE |
| **P-6** | input della chiamata nell'`esito_context` | ✅ **DB — `20260819-10`, applicato** |
| **P-5** | righe `area='test'` | ✅ **DB — deciso: restano (§18)** |
| §8 | ritiro del 141 | ✅ **DB — CSV + rimozione del ramo, applicato** |

✅ **Applicato e committato il 2026-08-19.** Il cancello dei codici errore è
verde e il pgTAP gira 12/12 come `zeroerp_app`. Per il DB il brief è **chiuso**.

Fuori perimetro e non urgente, come dite voi al §14-quater: la classificazione a
mano dei gruppi ripetuti fuori da `area='backend'`. Da oggi non se ne aggiungono.
