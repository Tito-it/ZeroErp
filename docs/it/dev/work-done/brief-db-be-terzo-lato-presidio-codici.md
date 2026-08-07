# Brief DB+BE — il terzo lato: i codici che il database dice e nessuno ha classificato

**Chi scrive:** DB (`dev/db-tid`), 2026-08-05.
**Origine:** rilievo del team BE, §12.5 di
[brief-db-codice-errore-strutturato](brief-db-codice-errore-strutturato.md) (chiuso).
**Stato:** ✅ **CHIUSO — 2026-08-07 (§28).** Cancello 4/4 · suite 3580/3580 · **registro 141 → 0** · `da_trigger` senza policy **90 → 0** · **659 policy** · 150 decisioni in tre giorni · 3 lati su 3 presidiati, più una lente sul quarto.
L'ultima richiesta al DB (§26.2) è **fatta e verificata** (§27): registro svuotato, misura canonica a **0 codici da dichiarare**. ⚠️ Resta il solo `make db-migrate` per portarlo sul DB di sviluppo, e la tabella **non si droppa**.
**Perimetro:** misura e cancello lato DB · assegnazione dei significati lato BE.

> **Non è una regressione.** Questo difetto c'era anche prima; la slice del codice
> errore strutturato l'ha soltanto reso **visibile**, perché ora il codice arriva
> davvero al backend invece di perdersi per strada.

---

## 1. Il problema, in parole semplici

Quando il database rifiuta un'operazione dice una **parola** — il codice errore.
Su quelle parole devono andare d'accordo **tre elenchi**:

1. il **catalogo** delle parole che il database può dire, con la frase che
   l'operatore legge (`config.messaggi_errore`);
2. le parole che usa il **codice applicativo**;
3. la tabella che dice, per ogni parola, **che tipo di risposta** dare a chi ha
   fatto la richiesta: «non esiste», «non ti è permesso», «è in conflitto con lo
   stato attuale», «hai sbagliato a compilare» (`error_policies.py`).

Oggi due accordi sono controllati automaticamente, il terzo no:

| Direzione | Presidiata da |
|---|---|
| le parole usate nel codice applicativo sono dichiarate | test lato backend ✅ |
| le parole che dice il database sono nel catalogo | guardrail DB ✅ |
| **le parole che dice il database hanno un tipo di risposta** | 🔴 **nessuno** |

**Conseguenza.** L'operatore legge comunque la frase giusta — quella viene dal
catalogo. Ma il *tipo* di risposta viene appiattito su «hai sbagliato a
compilare» anche quando la verità è «non esiste» o «non ti è permesso».

È come un commesso che, qualunque sia il problema, risponde sempre «c'è un errore
nella sua richiesta» invece di «quel prodotto non ce l'abbiamo» oppure «questo non
glielo posso vendere». Chi ascolta capisce lo stesso; chi deve **reagire** — la
pagina che decide se mostrare un avviso o riportarti indietro, un allarme, un
tentativo automatico — no.

⚠️ Ed è la stessa direzione da cui erano passati inosservati i nove codici delle
guard di cambio stato del cantiere precedente. Non è un caso: è **l'unico lato
che nessuno guarda**, quindi è lì che le cose si accumulano.

---

## 2. Quanto è grande

Misurato sul DB vivo il 2026-08-05, dopo la chiusura del cantiere precedente:

| | |
|---:|---|
| **341** | codici `E_*` **sollevati** da funzioni PL/pgSQL vive, via `script.fn_log_and_raise_error` |
| **141** | di questi, **senza una voce** in `error_policies.py` |
| **90** | dei 141, sollevati da funzioni **agganciate a un trigger**: sono sul percorso di una richiesta vera |

### ⚠️ Le misure riconciliate — e la terza era sbagliata

Tre numeri sono circolati per lo stesso fatto: **133** (BE), **141** (DB) e poi un
**137** «raffinato». Vale la pena dire com'è andata, perché è la trappola che
questo progetto continua a incontrare.

Il 137 nasceva dal restringere la misura ai soli letterali **dentro la chiamata
che solleva** — più preciso, in apparenza. In realtà **perdeva i codici del
gruppo C**: quelli che arrivano da un'espressione (`v_motivi -> 0 ->> 'codice'`),
dove il letterale vive dentro la funzione pura `fn_check_*` e non dentro la
`PERFORM`. Sono 19 codici, **4 dei quali senza policy**.

`137 + 4 = 141`. **Il numero grezzo di partenza era quello giusto**, e la
raffinazione l'aveva peggiorato dichiarando conformi quattro codici che non lo
sono. *Anche la misura di un difetto è un programma, e può avere il suo difetto.*

Da qui la scelta della vista canonica (§7): **volutamente larga**. Fra i due
errori possibili si sceglie quello che si corregge guardando i falsi positivi —
una policy di troppo costa una riga — non quello che non si vede.

L'insieme è fissato: **141 decisioni**, di cui **90 prioritarie**.

---

## 3. Perché non è ancora stato fatto

Non per dimenticanza. Il BE l'ha **trovato e segnalato** mentre chiudeva la
propria parte, e ha anche già scritto la misura. Si è fermato lì per una ragione
giusta:

> assegnare il tipo di risposta a 141 codici **non è una traduzione, è una
> decisione di dominio**, una per codice.

Centoquarantuno decisioni improvvisate in un pomeriggio sarebbero
centoquarantuno scelte da rifare. E non essendo una regressione, non c'era nessuna urgenza che giustificasse
la fretta.

---

## 4. Come lo chiuderei

La forma che ha già funzionato due volte in questo progetto — **misura, registro
del debito, cancello** — e nell'ordine che permette di accendere il cancello
**subito**, senza aspettare le 141 decisioni:

| # | Cosa | Chi |
|---|---|---|
| 1 | ~~Riconciliare le misure e fissare l'insieme~~ | ✅ **fatto** (§2) — DB |
| 2 | ~~**Cancello** in CI: un codice `E_*` che il DB può nominare deve avere una voce in `error_policies.py`~~ | ✅ **fatto** (§8) — BE |
| 3 | ~~**Registro del debito** con i codici già esistenti~~ | ✅ **fatto** (§7) — DB |
| 4 | Assegnare il tipo di risposta, **a lotti e per dominio** — non in ordine alfabetico: i codici di uno stesso dominio si decidono meglio insieme | BE + Tid |

Senza il punto 3 il cancello sarebbe rosso dal primo giorno e finirebbe
disattivato — che è il modo in cui i presidi muoiono.

⚠️ **Priorità dentro il punto 4:** i **90 da trigger agganciati** vengono prima.
Gli altri stanno in funzioni che potrebbero non essere sul percorso di una
richiesta, quindi il loro tipo di risposta non lo legge nessuno.

---

## 5. Una cosa da decidere prima di cominciare

Il cancello **non può leggere `error_policies.py` da SQL**: è un file Python. Due
strade, e vanno pesate insieme:

* **il controllo vive lato BE** — un test che legge le funzioni del database
  (serve una connessione) e le confronta col dizionario. È dove sta già il
  presidio gemello `test_error_codes_declared_guardrail`;
* **il controllo vive lato DB** — lo script SQL legge il *testo* di
  `error_policies.py`. È quello che fa oggi la misura scritta dal BE, funziona,
  ma lega un guardrail SQL alla forma di un sorgente Python.

Propendo per il **lato BE**: il dizionario è loro, e un test che gli sta accanto
si accorge di un rinominio molto prima di uno script che ne legge il testo.

✅ **Ed è tecnicamente possibile**, cosa che fino a ieri non era ovvia. Un test
Django che interroga `pg_proc` ha bisogno di un database **col nostro schema**, e
in CI ce l'ha: il runner non crea il database di test usa-e-getta finché nessun
test ne dichiara uno, quindi la connessione resta quella provvista da Liquibase.
È lo stesso meccanismo che fa funzionare i tre end-to-end di
`test_db_error_fields` (§14 del brief chiuso) — **con la stessa fragilità**: il
giorno in cui un test dichiarerà un database, questo controllo va adeguato
insieme a quelli. Sta scritto in `.codex/AGENTS.md` §Regole test Django.

Ma è una decisione da prendere insieme, non da imporre.

---

## 6. Riferimenti

* [brief-db-codice-errore-strutturato](brief-db-codice-errore-strutturato.md)
  §12.5 (il rilievo originale) e §10 (la forma dei due presidi già in servizio)
* [Presidi e registri del debito](../../guide/presidi-e-registri-del-debito.md) §3.3
* `scripts/sql/guardrail_codice_errore_strutturato.sql` — i cinque controlli esistenti

---

## 7. ✅ Pronto lato DB — la misura e il registro

Preparati il 2026-08-05, **da applicare**. Il cancello (punto 2) resta al BE.

| ChangeSet | Cosa |
|---|---|
| `20260805-35` | **la misura canonica**: vista `dbops.vw_codici_errore_da_dichiarare` |
| `20260805-36` | **il registro**: `dbops.codici_errore_senza_policy` |
| `20260805-37` + CSV | le **141 voci**, mirror `DELETE` + `loadData` |

### Perché una vista e non una query per ciascuno

È il pezzo che conta più della tabella. Tre numeri diversi per lo stesso fatto
sono nati perché ognuno si è scritto la propria query: la vista toglie quel
problema alla radice, e il cancello lato BE diventa poche righe.

```sql
SELECT codice, da_trigger, n_funzioni, funzioni
  FROM dbops.vw_codici_errore_da_dichiarare
 WHERE codice NOT IN (SELECT codice FROM dbops.codici_errore_senza_policy);
```

Il confronto col dizionario Python resta al test: `error_policies.py` da SQL non
si legge, ed è la ragione del §5.

**Verificato**: la vista dà esattamente gli stessi numeri della misura scritta a
mano — 360 codici totali, i 141 del registro tutti presenti, `da_trigger`
concorde su ognuno.

### Quello che il cancello deve fare, nei due versi

1. un codice della vista **senza** policy e **non** nel registro → **rosso**
   (è il 142esimo, quello nuovo);
2. una voce del registro che **ha ottenuto** la sua policy → **rosso**, la riga
   va tolta dal CSV.

⚠️ Senza il secondo verso il registro può solo allungarsi, e torna a essere un
elenco di eccezioni. È la regola che ha fatto passare il registro gemello da 57
voci a 1 in una giornata.

---

## 8. ✅ Lato BE — il cancello è acceso (2026-08-06)

**Chi scrive:** BE (`dev/backend-tid`).
**Stato:** punto 2 del §4 **chiuso**. Il punto 4 — le 141 decisioni — resta
aperto ed è l'unica cosa che manca.

### 8.1 La decisione del §5: **lato BE**, come proposto

Accolta la proposta del DB, e per la ragione che dava lui: il dizionario è del
backend, e un test che gli sta accanto si accorge di un rinominio molto prima di
uno script SQL che ne legge il testo.

Con una cosa in più rispetto a entrambe le strade descritte nel §5: il cancello
**non legge il testo** di `error_policies.py` — interroga il dizionario per
quello che è, `ErrorPolicyRegistry.has(codice)`. La lettura testuale serve al
gemello `test_error_codes_declared_guardrail`, che deve poter girare senza Django
configurato; questo cancello Django ce l'ha per forza (gli serve la connessione),
quindi la fragilità della regex non se la porta dietro. Un rinominio di
`_POLICIES` qui rompe l'import, non falsa il conteggio.

### 8.2 Prerequisiti verificati sul DB vivo, non dedotti

I tre changeSet risultano **applicati** su `dbdev`, e i numeri del §2 e del §7
tornano tutti:

| Misura | Atteso dal brief | Trovato |
|---|---|---|
| codici nella vista | 360 | **360** |
| senza voce in `error_policies.py` | 141 | **141** |
| voci del registro | 141 | **141** |
| di cui `da_trigger` | 90 | **90** |
| voci del registro fuori dalla vista | — | **0** |
| voci del registro che hanno già una policy | — | **0** |

Nessuna deriva: il cancello si accende **verde il primo giorno**, che era
esattamente lo scopo del registro. Il dizionario ha 458 codici `E_*` dichiarati,
nessuno duplicato.

### 8.3 Il cancello — e un terzo verso che il §7 non chiedeva

`backend/apps/core/tests/test_error_codes_db_policy_guardrail.py`, quattro test:

| # | Verso | Rosso quando |
|---|---|---|
| 1 | il 142esimo | un codice della vista **senza** policy e **non** nel registro |
| 2 | la riga da togliere | una voce del registro che **ha ottenuto** la sua policy |
| 3 | ⭐ **la riga orfana** | una voce del registro che **nessuna funzione viva nomina più** |
| 4 | sanity | vista vuota, dizionario non letto, codice fuori convenzione nel registro |

Il **terzo** è un'aggiunta, e vale la pena dire perché. Il §7 chiede due versi
per impedire che il registro si allunghi. Ma c'è un modo in cui una voce diventa
falsa senza passare da nessuno dei due: il codice viene **ritirato o rinominato**
e la funzione che lo nominava non c'è più. La riga resterebbe lì per sempre — mai
rossa, mai tolta — e il registro conterebbe un debito già pagato. In un cantiere
che ha appena rinominato codici a lotti non è un'ipotesi di scuola. Oggi sono 0,
ed è il momento giusto per accendere il controllo: quando saranno 1, si vedrà.

Il quarto verso è la difesa del presidio da se stesso: se la vista tornasse
vuota, i primi tre sarebbero **silenziosamente verdi**. È il modo in cui i presidi
muoiono senza che nessuno se ne accorga — l'«etichetta rassicurante» del §4-bis
della guida.

⚠️ **Il messaggio di fallimento del verso 1 mette i `da_trigger` in cima** e
stampa le funzioni che nominano il codice. Un elenco di codici senza posizione
non è azionabile, ed è la lezione già pagata sul gemello.

### 8.4 Salta se lo schema non c'è, **fallisce** se c'è ma manca il presidio

Il cancello ha bisogno di un database provvisto da Liquibase: stessa opt-in dei
tre e2e (`ZEROERP_TEST_DB_E2E=1`, accesa in `ci-validate.yaml` su ogni PR), stesso
guard sullo schema in `setUpClass`, nessun contatto col DB a import time.

La distinzione che conta, e che il §14 del brief chiuso non poteva ancora avere:

* **schema Liquibase assente** (database usa-e-getta creato dal runner) →
  **skip**. Senza questo ramo il cancello fallirebbe addosso a chi scriverà il
  primo test che dichiara un database, in una PR che non c'entra niente;
* **schema presente ma vista o registro assenti** → **errore**, non skip. Lì il
  presidio esiste e non è stato applicato: un cancello che in quel caso tacesse
  starebbe mentendo.

⚠️ Resta la fragilità dichiarata nel §5: il giorno in cui un test dichiarerà un
database, questo controllo **salterà** invece di fallire — e un cancello che
salta non presidia niente. Va adeguato insieme ai tre e2e, non lasciato skippato.
Annotato in `.codex/AGENTS.md` §Regole test Django.

### 8.5 Le prove

* **4/4 verdi** sul DB vivo con `ZEROERP_TEST_DB_E2E=1`;
* **3580/3580** l'intera suite Django, sempre con il flag acceso: nessun test di
  altre app disturbato (era il rischio pagato al primo tentativo dei tre e2e —
  469 rossi da un probe a import time);
* **il cancello morde in tutti e quattro i versi.** Provato alterando lo stato
  letto dal DB — una voce tolta dal registro, una voce a cui si concede una
  policy, un codice tolto dalla vista, la misura azzerata — e verificando che
  ogni verso diventi rosso con il proprio messaggio. Un presidio che non si è mai
  visto rosso non è un presidio.

### 8.6 Cosa resta, ed è solo il punto 4

Le **141 decisioni**, a lotti e per dominio, **90 da trigger per prime**. Il
registro adesso è protetto nei tre versi: può solo calare, e ogni riga che cala
va tolta dal CSV (`db/changelog/migrations_v2/80_data/sql/dbops/codici_errore_senza_policy.csv`,
mirror `DELETE` + `loadData`) chiedendo al DB di riapplicare il `20260805-37`.

⚠️ Il lotto va deciso con Tid: assegnare 404/403/409/400 a un codice è una
decisione di dominio, non una traduzione — è la ragione per cui il BE si era
fermato la prima volta, e resta valida.

### 8.7 I file toccati

| File | Cosa |
|---|---|
| `backend/apps/core/tests/test_error_codes_db_policy_guardrail.py` | **nuovo** — il cancello, 4 test |
| `backend/apps/core/tests/db_e2e.py` | **nuovo** — `richiedi_db_provvisto()`, il prerequisito «DB vero» in un posto solo |
| `backend/apps/core/tests/services/test_db_error_fields.py` | i 3 e2e passano al guard condiviso |
| `.codex/AGENTS.md` | §Regole test Django: il quarto test che dipende dal DB provvisto, e cosa lo rompe |
| `docs/it/guide/presidi-e-registri-del-debito.md` | **§3.4 nuovo** — il terzo lato entra nella guida dei presidi |

⚠️ **Il guard «serve il DB vero» sta in un posto solo** (`db_e2e.py`), ed è la
regola del 2 applicata a una duplicazione che sarebbe stata pericolosa: quel
guard è il punto in cui il progetto paga una **dipendenza implicita** — il
runner non crea un database usa-e-getta finché nessun test ne dichiara uno. Il
giorno in cui cadrà, va sanata una volta, non cercandone le copie.

### 8.8 Cosa cambia davvero assegnando una policy

Non il messaggio: quello viene dal catalogo e arriva già oggi
(`ErrorTranslator` usa `policy.user_message` solo come ripiego). Cambiano
**`http_status`** e **`ui_action`**. Oggi un codice non dichiarato prende il
ripiego `400 · show_error_banner`, quindi **assegnare 400 a un codice non cambia
niente per nessuno**: il lavoro utile è tutto sui codici la cui verità è
404 / 403 / 409. Serve a dimensionare il punto 4 — vedi §9.

---

## 9. Il punto 4, dimensionato — le 141 non pesano uguale

> ℹ️ **Fotografia di partenza.** I numeri di questo paragrafo sono quelli del
> 2026-08-06 *prima* del lotto 1: servono a dimensionare il lavoro, non a dire
> lo stato corrente. Per quello vale il §12.1 (registro a 114, 112 quando il DB
> avrà tolto le ultime due righe).

Misurato sui 141 codici del registro (2026-08-06). La classificazione qui sotto è
**dal nome del codice**, quindi indicativa: serve a dare un ordine di grandezza,
non a decidere al posto di nessuno.

| Verità probabile | Codici | di cui `da_trigger` |
|---|---|---|
| 400 — è già così, dichiararlo non cambia niente | 104 | 71 |
| **409 conflitto di stato** | 19 | 13 |
| **404 non esiste** | 14 | 4 |
| **403 non permesso** | 4 | 2 |

⚠️ **Il numero che conta non è 141, è ~37** — i codici la cui verità è diversa
dal 400 che prendono oggi. E fra quelli, **19 stanno su funzioni agganciate a un
trigger**, cioè arrivano davvero a un utente. Gli altri 104 sono lavoro di
registrazione, non decisioni: vanno fatti — il cancello li vuole — ma non
costano scelte e non cambiano il comportamento di nulla.

⚠️ La classificazione dal nome **non è la decisione**: `E_..._NON_AMMESSO` può
essere un 409 (lo stato non lo consente) o un 403 (non hai il diritto), e il nome
non lo dice. La lettura va fatta sulla funzione che solleva. Ma dice quali codici
vale la pena leggere per primi.

Distribuzione per dominio dei **90 `da_trigger`**: `script` 31 · `anagrafiche` 22
· `vendite` 21 · `config` 6 · `dbops` 5 · `catalogo` 4 · `shop` 1.

⚠️ Quella distribuzione conta ogni codice **una volta sola**, sul primo nome di
funzione in ordine alfabetico. I codici che toccano *almeno una* funzione
`vendite.` sono **29**, non 21: otto sono sollevati anche da `script.`,
`config.` o `catalogo.`. Per decidere serve il secondo numero — un codice
condiviso va deciso per tutti i suoi punti insieme (§10).

---

## 10. Primo lotto — `vendite`, i 29 codici da trigger

Proposta BE del 2026-08-06, **da confermare con Tid**. Ogni riga è stata letta
dal **punto che solleva**, non dal nome del codice: il nome dice `..._NON_AMMESSO`
sia quando è lo stato a non consentirlo (409) sia quando è un diritto che manca
(403), e la differenza si vede solo nella funzione.

⚠️ **Cosa cambia davvero.** Il messaggio a video arriva già oggi dal catalogo e
non cambia. Cambiano `http_status` e `ui_action` — cioè come **reagisce** la
pagina. I 13 codici a 400 prendono già 400 dal ripiego: dichiararli non cambia
niente per nessuno, serve solo a togliere la riga dal registro.

### 10.1 `404` — la cosa indicata non esiste (2)

| Codice | Perché |
|---|---|
| `E_FULFILL_NOT_FOUND` | `trgfn_ordini_ful_guard_consistenza`: la `ordine_riga_id` o la `ddt_riga_id` indicate non danno nessuna riga |
| `E_PARAMETRI_TABELLA` | `trgfn_attivita_fatturabili_guard_ba_coerenza`: `IF NOT FOUND` sul billing account indicato ⚠️ vedi §10.5 |

### 10.2 `403` — non è permesso, e non dipende dallo stato (1)

| Codice | Perché |
|---|---|
| `E_DELETE_NOT_ALLOWED` | tre punti, stessa sostanza: la cancellazione è **sempre** bloccata (righe ordine/DDT senza fulfillment, log) e si sblocca solo con una GUC di sistema. Non è una questione di stato: quell'azione non è dell'operatore |

### 10.3 `409` — in conflitto con lo stato attuale (13)

| Codice | Il conflitto |
|---|---|
| `E_ARTICOLO_MISMATCH` | riga ordine e riga DDT esistono ma hanno articoli diversi ⚠️ §10.5 |
| `E_UOM_MISMATCH` | stesse due righe, unità di misura diverse ⚠️ §10.5 |
| `E_COMMESSA_CHIAVE_IMMUTABILE` | la commessa ha già attività collegate |
| `E_COMMESSA_STATO_TRANSIZIONE_INVALIDA` | transizione non ammessa da quello stato |
| `E_CONTRATTO_CATEGORIA_SNAPSHOT_IMMUTABILE` | lo snapshot è congelato alla creazione |
| `E_DDT_EMISSIONE_SENZA_RIGHE` | il DDT non ha righe attive |
| `E_DELETE_BLOCKED_FUL` | esistono riferimenti fulfillment |
| `E_FATTURA_NON_ANNULLABILE` | la fattura è già numerata |
| `E_FATTURA_RIGA_CONGELATA` | lo stato fattura non consente più di toccare le righe |
| `E_FATTURA_SATELLITE_CONGELATO` | idem, sui satelliti |
| `E_ORDINE_CONFERMA_SENZA_RIGHE` | l'ordine non ha righe |
| `E_ORDINE_TRANSIZIONE_NON_AMMESSA` | transizione non ammessa da quello stato |
| `E_RIGA_LISTINO_PROPAGATA` | la riga è già stata propagata a valle |

Sono i 13 che **cambiano comportamento**: oggi la pagina evidenzia un campo
(400) dove dovrebbe ricaricare e mostrare lo stato vero.

### 10.4 `400` — resta com'è (12)

> ⚠️ Erano 13 nella prima stesura: `E_STATO_SCONOSCIUTO` è uscito da questo
> gruppo con la decisione del §10.5 punto 1 → §11.2 → §12.

Nessun cambio di comportamento: si dichiarano solo per svuotare il registro.
`highlight_form_fields` dove c'è davvero un campo da correggere,
`show_error_banner` dove il problema non è un campo del form.

| Codice | `ui_action` |
|---|---|
| `E_QTA_NON_POSITIVA` · `E_COERENZA_ID` · `E_SORG_FORMATO` · `E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE` · `E_LISTINO_TIPOLOGIA_UTILITY` | `highlight_form_fields` |
| `E_ARTICOLO_TIPOLOGIA_MANCANTE` · `E_CONTRATTO_EMITTENTE_NON_RISOLTO` · `E_ORDINE_EMITTENTE_NON_RISOLTO` · `E_LISTINO_RIGA_COMPOSITO_VIETATO` · `E_SORG_CONF` · `E_SORG_KEYSEL` · `E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA` | `show_error_banner` |

### 10.5 ⚠️ Le tre righe su cui decide Tid, non il BE

**1. `E_STATO_SCONOSCIUTO` — un nome, due domini.** Lo sollevano
`fn_cambia_stato_commessa`/`_preventivo` (lo stato di workflow indicato non
esiste o non è attivo) **e** `config.trgfn_toponomastica_normalize` (il codice
*nazione* di un indirizzo non si risolve). Sul primo «404 non esiste» sarebbe
giusto; sul secondo farebbe **svuotare la pagina di un indirizzo** mentre
l'operatore sta digitando. Proposta: **400**, il denominatore comune sicuro. La
risposta precisa costa **spezzare il codice in due**, ed è lavoro DB.

> ✅ **Deciso da Tid (2026-08-06): si spezza**, non si sceglie il denominatore
> comune. Fatto dal DB lo stesso giorno (§11.2 → §12): i due codici esistono e
> hanno preso 404 e 400. È la scelta più cara delle due ed è quella giusta —
> il denominatore comune avrebbe reso *permanente* un difetto di modellazione.

**2. `E_PARAMETRI_TABELLA` — il nome dice due cose.** «Parametro non valido *o*
inesistente». Oggi l'unico punto che lo solleva è un `NOT FOUND` su un billing
account, quindi **404** è la verità. Ma il nome invita a riusarlo per un
parametro *malformato*, che è un 400: al prossimo riuso la policy diventerebbe
falsa senza che nessuno se ne accorga. È un difetto di modellazione, non di
mapping: o si accetta il 404 sapendolo, o si rinomina (DB).

**3. `E_ARTICOLO_MISMATCH` / `E_UOM_MISMATCH` — 409 o 400?** Le due righe
esistono entrambe e non vanno d'accordo. Ho proposto **409** perché l'operatore
non ha un campo da correggere: deve rileggere lo stato e scegliere un altro
abbinamento. Chi la vede come «hai passato la coppia sbagliata» direbbe 400. È
una scelta di dominio, non tecnica.

### 10.6 ⚠️ Le due metà devono atterrare insieme

Appena i 29 codici entrano in `error_policies.py`, il **verso 2** del cancello
(§8.3) diventa rosso: sono voci del registro che hanno ottenuto la loro policy.
Le righe vanno tolte dal CSV
(`db/changelog/migrations_v2/80_data/sql/dbops/codici_errore_senza_policy.csv`)
e il `20260805-37` riapplicato — ed è **lavoro del team DB**, non del BE.

Il cancello sta facendo esattamente il suo mestiere: costringe le due sponde a
muoversi insieme. Va concordato **prima**, non scoperto in CI.

---

## 11. ⚠️ Richieste al team DB — il lotto 1 è scritto, il cancello è rosso

**Chi scrive:** BE (`dev/backend-tid`), 2026-08-06.
**Stato:** le 28 policy sono in `error_policies.py`, **non committate**. Il
cancello è rosso nel verso 2 finché il DB non toglie le righe dal registro.

Le decisioni del §10.5 sono state prese da Tid il 2026-08-06:

| Domanda | Decisione |
|---|---|
| `E_STATO_SCONOSCIUTO` | **404, ma spezzando il codice** → §11.2, resta nel registro |
| `E_PARAMETRI_TABELLA` | **404**, sapendo il rischio del nome generico (annotato nella policy) |
| `E_ARTICOLO_MISMATCH` / `E_UOM_MISMATCH` | **409** conflitto |
| Sequenza | policy + richiesta al DB **insieme**, nessun commit prima |

### 11.1 Togliere 28 righe dal registro (`20260805-37`)

Tutte e 28 hanno ottenuto la loro policy: sono debito **pagato**, e finché
restano nel CSV il cancello resta rosso. Sono tutte `da_trigger = true`.

```
E_ARTICOLO_MISMATCH · E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE · E_ARTICOLO_TIPOLOGIA_MANCANTE
E_COERENZA_ID · E_COMMESSA_CHIAVE_IMMUTABILE · E_COMMESSA_STATO_TRANSIZIONE_INVALIDA
E_CONTRATTO_CATEGORIA_SNAPSHOT_IMMUTABILE · E_CONTRATTO_EMITTENTE_NON_RISOLTO
E_DDT_EMISSIONE_SENZA_RIGHE · E_DELETE_BLOCKED_FUL · E_DELETE_NOT_ALLOWED
E_FATTURA_NON_ANNULLABILE · E_FATTURA_RIGA_CONGELATA · E_FATTURA_SATELLITE_CONGELATO
E_FULFILL_NOT_FOUND · E_LISTINO_RIGA_COMPOSITO_VIETATO · E_LISTINO_TIPOLOGIA_UTILITY
E_ORDINE_CONFERMA_SENZA_RIGHE · E_ORDINE_EMITTENTE_NON_RISOLTO · E_ORDINE_TRANSIZIONE_NON_AMMESSA
E_PARAMETRI_TABELLA · E_QTA_NON_POSITIVA · E_RIGA_LISTINO_PROPAGATA
E_SORG_CONF · E_SORG_FORMATO · E_SORG_KEYSEL · E_UOM_MISMATCH
E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA
```

Togliere le righe da
`db/changelog/migrations_v2/80_data/sql/dbops/codici_errore_senza_policy.csv` e
riapplicare il `20260805-37` (è già `runOnChange: true` + `validCheckSums: ANY`,
e il mirror `DELETE` + `loadData` fa il resto: **è esattamente il caso per cui
era stato scelto il mirror invece di un upsert**).

Il registro passa da **141 a 113**, i `da_trigger` da **90 a 62**. Primo calo:
il debito comincia a pagarsi.

⚠️ **Non serve toccare `config.messaggi_errore`**: i messaggi ci sono già e sono
quelli che l'operatore legge. Qui cambia solo *come reagisce la pagina*.

**Come si verifica che è fatto** — non dal CSV, dal cancello:

```bash
ZEROERP_TEST_DB_E2E=1 ./manage-test.sh apps.core.tests.test_error_codes_db_policy_guardrail
```

Deve tornare **4/4 verdi**. È l'unico controllo che guarda le due sponde
insieme: il CSV da solo direbbe di sì anche se il changeSet non fosse stato
riapplicato.

### 11.2 Spezzare `E_STATO_SCONOSCIUTO` — un codice, due domini

**Decisione di Tid: si spezza.** Oggi lo sollevano tre funzioni che parlano di
due cose diverse:

| Funzione | Cosa manca davvero | Verità |
|---|---|---|
| `vendite.fn_cambia_stato_commessa` | lo **stato di workflow** indicato non esiste o non è attivo | 404 |
| `vendite.fn_cambia_stato_preventivo` | idem | 404 |
| `config.trgfn_toponomastica_normalize` | il **codice nazione** dell'indirizzo non si risolve | 400, campo da correggere |

Un codice solo non può dire due cose: con 404 la form indirizzi si svuoterebbe
mentre l'operatore digita; con 400 il cambio stato mente. **Non è un problema di
mapping, è un codice che ne contiene due** — la stessa famiglia di difetti del
§15 del brief chiuso.

Serve, lato DB:

1. due codici nuovi a catalogo (proposta di nome, da confermare):
   `E_STATO_WORKFLOW_NON_TROVATO` e `E_NAZIONE_NON_TROVATA`;
2. le tre funzioni aggiornate a sollevare il proprio;
3. `E_STATO_SCONOSCIUTO` **ritirato** con `obsoleto_dal`, non cancellato — la
   riga del catalogo regge il diario degli errori già accaduti (§15.3 del brief
   chiuso).

Finché non è fatto, `E_STATO_SCONOSCIUTO` **resta nel registro del debito**, e
non è una dimenticanza: è la riga che documenta questo lavoro. Appena i due
codici esistono, il BE assegna 404 e 400 e la riga esce.

> ✅ **Fatto dal DB il 2026-08-06** (`9c3f88856`, changeSet `20260806-09/10/11`),
> e il BE ha assegnato i due status. Verifica e residuo nel §12.

⚠️ **La verifica va fatta dal percorso, non dal nome.** Che le tre funzioni
sollevino il codice giusto si vede solo leggendo il punto che solleva: è così che
questo doppio significato è saltato fuori, e il nome del codice non lo diceva.

---

## 12. ✅ Il giro DB è arrivato — verificato, e restano due righe

**Chi scrive:** BE, 2026-08-06 (commit DB `9c3f88856`).

### 12.1 Cosa risulta fatto, misurato sul DB vivo

| | prima | dopo |
|---|---|---|
| voci del registro | 141 | **114** |
| di cui `da_trigger` | 90 | **62** |
| codici nella vista | 360 | **361** |
| `E_STATO_SCONOSCIUTO` ancora sollevato | sì, da 3 funzioni | **0** |

Il conto torna esattamente: −28 (§11.1) −1 (`E_STATO_SCONOSCIUTO`, che nessuna
funzione viva nomina più, quindi esce anche dalla vista) **+2** (i due codici
nuovi, messi nel registro perché ancora senza policy). `141 − 28 − 1 + 2 = 114`.

**Le tre funzioni lette dal punto che solleva**, non dal nome del changeSet:
`fn_cambia_stato_commessa` e `_preventivo` sollevano `E_STATO_WORKFLOW_NON_TROVATO`
sul ramo `v_nuovo_stato_id IS NULL`, e `trgfn_toponomastica_normalize` solleva
`E_NAZIONE_NON_TROVATA` quando né il chiamante né il default per parametro
risolvono la nazione. Sono esattamente le due metà del §11.2.

⭐ **Il ritiro è fatto meglio di come era stato chiesto:** `E_STATO_SCONOSCIUTO`
resta a catalogo con `obsoleto_dal` **e** con scritto dentro perché ne conteneva
due e da cosa è sostituito. Chi lo ritroverà fra un anno in un log non dovrà
ricostruire niente.

⭐ **E i due codici nuovi sono stati messi nel registro**, non lasciati fuori: è
il gesto che ha tenuto il cancello verde nell'intervallo fra il giro DB e questo.
È esattamente il protocollo per cui il registro esiste.

### 12.2 ⚠️ Il cancello non è stato eseguito — l'ambiente è rotto, e non per noi

`./manage-test.sh` non parte affatto: il venv ha **Django 6.1** (bump non
committato in `backend/requirements.txt`) e **DRF 3.17.2** importa
`django.utils.cache.cc_delim_re`, che Django 6.1 ha rimosso. L'intero backend non
si importa — non è un rosso di questo lavoro, è la suite che non gira.

I quattro versi sono stati verificati **per via equivalente**: stessa vista,
stesso registro, chiavi di `error_policies.py` estratte per lettura testuale.
Tutti e quattro verdi allo stato del giro DB. Resta da rieseguire il test vero
appena l'ambiente torna:

```bash
ZEROERP_TEST_DB_E2E=1 ./manage-test.sh apps.core.tests.test_error_codes_db_policy_guardrail
```

**Una verifica per via equivalente non è la verifica.** Sta scritto qui perché
non venga scambiata per un verde della CI.

#### ✅ Risolto lo stesso giorno — e la causa non era un aggiornamento sbagliato

**Django 6.1 ha rimosso `django.utils.cache.cc_delim_re`**, che
`rest_framework/views.py` importa a livello di modulo. Non è un test rosso: è
l'intero backend che non si importa. E **djangorestframework 3.17.2 è l'ultima
release esistente** al 2026-08-06, con quell'import ancora dentro: non c'era una
versione di DRF a cui aggiornare.

Quindi l'unica leva era il **tetto**, e sta dove serve:
`backend/requirements.in` passa da `Django>=6.0,<7.0` a `Django>=6.0,<6.1`, con
scritto accanto perché e **come si toglie** (quando esce una DRF che dichiara
6.1: verificare che `cc_delim_re` sia sparito da `rest_framework/`, poi
rialzare). Un pin senza istruzioni di uscita è un pin che resta per anni.

⚠️ Il `requirements.txt` ricompilato è risultato **identico** a quello
committato: il tetto non cambia niente di risolto oggi (Django era già a 6.0.7),
**impedisce il prossimo `pip-compile --upgrade`**. Era solo il venv locale ad
avere 6.1 installato — la CI non era mai stata rotta, e non lo sarà.

**Suite ripristinata: 3580 test, un solo rosso** — le due righe del §12.3.

### 12.3 Ultima richiesta al DB — due righe

Il BE ha dichiarato i due codici nuovi, ognuno con la verità che il taglio ha
reso dicibile:

| Codice | Status | `ui_action` | Perché |
|---|---|---|---|
| `E_STATO_WORKFLOW_NON_TROVATO` | **404** | `show_error_banner` | la destinazione indicata non esiste |
| `E_NAZIONE_NON_TROVATA` | **400** | `highlight_form_fields` | è un errore di compilazione: c'è un campo da correggere e la pagina non deve svuotarsi |

Quindi il verso 2 le segnala: **le due righe vanno tolte** dal CSV e il
`20260805-37` riapplicato. Il registro va a **112**, i `da_trigger` a **61**.

Con questo il §11 è chiuso in entrambi i sensi, e il punto 4 riparte dal lotto 2
(prossimo dominio da scegliere con Tid: `anagrafiche` ha 22 `da_trigger`,
`script` 31).

---

## 13. ✅ Lotto 1 CHIUSO — 2026-08-06

Le due righe sono uscite (`f505d8f12`) e il migrate è stato riapplicato alle
**12:48:49**. Misurato dopo:

| | inizio | fine lotto 1 |
|---|---|---|
| voci del registro | 141 | **112** |
| di cui `da_trigger` | 90 | **60** |
| codici con una policy decisa | 0 | **30** |

**Cancello 4/4 verde. Suite 3580/3580 verde.** È la prima volta che le due sponde
sono misurate insieme e concordano.

⚠️ **Una cosa vista sul campo, e vale più del numero.** Nel mezzo della verifica
il CSV del repo diceva 112 e il database vivo 114: il changeSet non era ancora
stato riapplicato. Chi avesse controllato **dal CSV** avrebbe dichiarato chiuso
un lavoro che nel database non era ancora arrivato. Il cancello no, perché guarda
il database — ed è esattamente la ragione per cui il §11.1 dice «non dal CSV, dal
cancello». Non era un errore di nessuno, solo due minuti di sfasamento: ma è
proprio in quei due minuti che una verifica scritta male dice la cosa sbagliata.

### Cosa vale oltre questo lotto

* **Il registro ha fatto emergere un difetto di modellazione**, non solo del
  debito: `E_STATO_SCONOSCIUTO` ne conteneva due, e nessuno se ne era accorto in
  anni perché il codice «funzionava». Un registro serio non ricorda soltanto —
  fa vedere.
* **Il numero che conta non era 141.** Centoquattro codici prendevano già il 400
  che gli spettava: il lavoro vero erano i ~37 con una verità diversa. Misurare
  *quanto pesa* il debito prima di pagarlo ha risparmiato tre quarti del giro.
* **Il nome del codice non decide.** Tre dei trenta hanno preso uno status
  diverso da quello che il nome suggeriva, e si è visto solo leggendo il punto
  che solleva.

### Il prossimo lotto

`anagrafiche` — **22 `da_trigger` su 28** (scelta di Tid, 2026-08-06). Dominio
chiuso, pagine che l'operatore usa tutto il giorno. `script` (25 `da_trigger`)
viene dopo di proposito: è trasversale, i suoi codici sono sollevati da guard
generiche usate da mezzo database e conterrà altri casi a doppio significato come
`E_STATO_SCONOSCIUTO`. Meglio arrivarci con un lotto di dominio già fatto, che dà
il metro per riconoscerli.

---

## 14. Lotto 2 — `anagrafiche`, i 22 codici da trigger (2026-08-06)

Scritti in `error_policies.py`, **non committati**. Decisioni di Tid sui tre casi
dubbi prese lo stesso giorno (§14.3).

### 14.1 La ripartizione

| Status | Quanti | Codici |
|---|---|---|
| **404** | 2 | `E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO` (`IF NOT FOUND` sul soggetto) · `E_GESTORE_SOGGETTO_RUOLO_MANCANTE` (lookup a vuoto su `soggetti_ruoli`) |
| **409** | 3 | `E_COLONNA_NON_MODIFICABILE` (colonna congelata, 7 guard `protect_update`) · `E_DISSOCIAZIONE_PARENT_CON_ATTIVITA` · `E_GESTORE_SINGLETON_VIOLATO` |
| **500** | 1 | `E_RUOLO_APPLICATIVO_NON_GESTITO` |
| **400** | 16 | 11 con `highlight_form_fields`, 5 con `show_error_banner` |

### 14.2 ⚠️ La regola che sembra contraddire il lotto 1

Nel lotto `vendite` i mismatch articolo/UoM hanno preso **409**; qui i tre
mismatch (`E_ID_FISCALI_DIVERSI`, `E_BA_SOGGETTO_INCOERENTE_ISTANZA`,
`E_RISORSA_UMANA_SOGGETTO_MISMATCH`) prendono **400 con il campo evidenziato**.

Non è un'incoerenza: la differenza è **chi ha scelto il valore in conflitto**.
In `vendite` erano legami DDT↔ordine creati dal sistema, e l'operatore non aveva
un campo da correggere — poteva solo rileggere lo stato. Qui il parent, il
soggetto e il conto li sceglie lui in un form.

> **409 = «rileggi lo stato». 400 + highlight = «correggi quel campo».**
> La regola vale per i lotti successivi ed è il criterio da applicare, non
> l'elenco dei codici già decisi.

### 14.3 Le tre decisioni, e un difetto trovato leggendo

**1. ⚠️ `E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO` — il messaggio a catalogo
descrive un'altra condizione.** Il ramo che solleva è `IF NOT FOUND` sulla SELECT
su `anagrafiche.soggetti` («il soggetto non esiste»), ma il messaggio dice «Il
soggetto richiede dati societari». **Oggi l'operatore legge una frase che non
c'entra con l'errore che ha davanti.** Non è un problema di policy — il 404 è
giusto comunque, e lo status non dipende dal messaggio — ma è un difetto vero e
va corretto: **richiesta al team DB, §14.5.**

**2. `E_SOGGETTI_RUOLI` → 400, candidato allo split ma non ora.** Copre tre
condizioni (parametro nullo o `<= 0`, `NOT FOUND`, ruolo non coerente col tipo
atteso) con un messaggio generico. È la malattia di `E_STATO_SCONOSCIUTO`, ma la
cura è diversa e il motivo va scritto: **là le due metà chiedevano alla pagina
reazioni opposte** (404 che svuota vs 400 che evidenzia), qui nessuna delle tre
chiede qualcosa di diverso da un 400. E il codice è usato anche da
`script.fn_guard_soggetto_ruolo`, cioè da altri domini: lo split costerebbe più
di quanto renda. Decisione Tid: **400**, annotato nella policy.

> La lezione generale: un codice a più significati va spezzato quando i
> significati **portano a reazioni diverse**, non perché sono più d'uno.

**3. `E_RUOLO_APPLICATIVO_NON_GESTITO` → 500.** È il ramo `ELSE` del guard di
`identita_digitali`: scatta quando qualcuno estende l'enum dei ruoli applicativi
senza scrivere la regola, e il guard «non apre per omissione». È **l'unico dei 22
in cui l'operatore non può fare niente** — non ha sbagliato lui, manca una regola
nel sistema. Un 400 lo nasconderebbe fra i 400 di chi compila male.

> ✅ Verificato che il 500 **non** nasconde il messaggio del DB:
> `ErrorTranslator.is_technical_code` è una lista chiusa di tre codici
> (`E_PIPELINE`, `E_DATABASE`, `E_GENERICO`), non dipende dallo status. Era il
> dubbio che rendeva il 500 rischioso, e non lo è.

### 14.4 Stato

**Suite 3580, un solo rosso**: il verso 2 con le 22 righe da togliere — il
cancello che fa il suo mestiere, come nel lotto 1.

### 14.5 Richieste al team DB

**a) Togliere le 22 righe** dal CSV del registro e riapplicare il `20260805-37`:

```
E_BA_SOGGETTO_INCOERENTE_ISTANZA · E_COLONNA_NON_MODIFICABILE · E_CONTO_BANCARIO
E_DATA_APERTURA · E_DATA_CHIUSURA · E_DATA_ERRATA · E_DATA_FINE_NON_MAGGIORE_DI_INIZIO
E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO · E_DATI_SOCIETARI_TIPO_DETTAGLIO_NON_CONFIGURATO
E_DATI_SOCIETARI_TIPO_SOGGETTO_NON_AMMESSO · E_DISSOCIAZIONE_PARENT_CON_ATTIVITA
E_FORMA_GIURIDICA_PAESE · E_GESTORE_SINGLETON_VIOLATO · E_GESTORE_SOGGETTO_RUOLO_MANCANTE
E_ID_FISCALI_DIVERSI · E_PARENT_SELF · E_RISORSA_UMANA_SOGGETTO_MISMATCH
E_RUOLO_APPLICATIVO_NON_GESTITO · E_RUOLO_NATURA_TIPO_DET_NULL · E_RUOLO_RICHIEDE_PIVA
E_SOGGETTI_RUOLI · E_TIPO_INDIRIZZO_NON_PERMESSO
```

Il registro va da **112 a 90**, i `da_trigger` da **61 a 39**.

> ℹ️ Le richieste dei lotti 2, 3 e 4 sono confluite in un **giro solo** (decisione
> di Tid): l'elenco definitivo delle righe da togliere è nel §16.4.

⚠️ **Verificare dal cancello, non dal CSV.** Nel lotto 1 c'è stato un momento in
cui il CSV diceva 112 e il database 114 perché il changeSet non era ancora stato
riapplicato: chi controlla dal CSV dichiara chiuso un lavoro che nel database non
è arrivato.

**b) Correggere il messaggio** di `E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO` in
`config.messaggi_errore`. Oggi: «Il soggetto richiede dati societari. Soggetto_id
%s». La condizione reale è «il soggetto non esiste»: qualcosa come «Soggetto %s
non trovato: impossibile validare i dati societari.»

> ℹ️ Vale la pena chiedersi se altri codici abbiano lo stesso scollamento fra
> messaggio e condizione. Questo è saltato fuori **solo** leggendo il punto che
> solleva, e nessun presidio lo guarda: il guardrail DB verifica che il codice
> sia *a catalogo*, non che il messaggio *descriva* la condizione. È un quarto
> lato, e per ora non lo presidia nessuno.

---

## 15. Lotto 3 — `script`, i 25 codici da trigger (2026-08-06)

Scritti in `error_policies.py`, **non committati**. I codici da trigger che
toccano una funzione `script.` sono 26, ma `E_SOGGETTI_RUOLI` era già del lotto 2
(è condiviso con `anagrafiche`): **25 nuovi**.

### 15.1 ⚠️ Questo lotto ha una fisionomia diversa dagli altri due

`script` non è un dominio: sono **guard generiche montate a mano** sui trigger di
mezzo database. E si vede nel risultato — **sette codici su 25 non nascono da un
dato sbagliato ma da un pezzo montato male**:

| Codice | Cosa è successo davvero |
|---|---|
| `E_SNAPSHOT_ID_NOT_FOUND` | `EXCEPTION WHEN OTHERS` della storicizzazione: non riesce a leggere la chiave |
| `E_SNAPSHOT_CLOSE_ERROR` · `E_SNAPSHOT_INIT_INSERT_ERROR` · `E_SNAPSHOT_FINAL_INSERT_ERROR` | idem, sui tre passi dello snapshot |
| `E_QUERY_FAILED_SCHEMA_TABLE` | SQL dinamico su una tabella che non esiste o non ha le colonne attese |
| `E_ARGOMENTI_A_COPPIE` | trigger dichiarato con un numero **dispari** di argomenti |
| `E_NOTE_CONFIG` | trigger note puntato a una tabella inesistente (`to_regclass` NULL) |

**Fino a oggi prendevano tutti 400.** Un fallimento della storicizzazione
arrivava al client come «hai sbagliato a compilare»: l'operatore non poteva farci
niente e chi guardava i log non aveva modo di distinguerlo dagli errori di chi
compila male. Decisione Tid (2026-08-06): **500 tutti e sette**.

⚠️ `E_SNAPSHOT_ID_NOT_FOUND` è il caso di scuola del perché il nome non decide:
finisce per `NOT_FOUND` e **non è un 404** — non manca un record richiesto,
fallisce la lettura della chiave dentro un handler di eccezione.

### 15.2 Il resto

| Status | Quanti | Codici |
|---|---|---|
| **403** | 2 | `E_SCOPE_EMITTENTE` (`fn_check_user_emittente_scope` nega) · `E_TABELLA_OP_NON_CONSENTITA` (blocca sempre UPDATE/DELETE su `transaction_ids`) |
| **404** | 1 | `E_SORG_NOT_FOUND` |
| **409** | 1 | `E_CANALE_ORIGINE_IMMUTABILE` |
| **400** | 14 | 7 `highlight_form_fields` (quantità, UoM, chiave sorgente, prezzo componente, target nota) · 7 `show_error_banner` (i sei guard BoM/componenti e il mismatch nota↔documento) |

### 15.3 Stato

**Suite 3580, un solo rosso**: 47 righe da togliere (22 del lotto 2 + 25 di
questo). 588 policy dichiarate, nessuna duplicata.

### 15.4 Richieste al team DB — lotti 2 e 3 insieme

Tid le passa in un giro solo.

**a) Togliere 47 righe** dal registro e riapplicare il `20260805-37`: le 22 del
§14.5a più le 25 di questo lotto. Il registro va da **112 a 65**, i `da_trigger`
da **61 a 14**. → **superato dal lotto 4: l'elenco definitivo è nel §16.4.**

L'elenco esatto lo dà il cancello stesso, che è la fonte da usare:

```bash
ZEROERP_TEST_DB_E2E=1 ./manage-test.sh apps.core.tests.test_error_codes_db_policy_guardrail
```

**b) Correggere il messaggio** di `E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO`
(§14.5b): descrive una condizione diversa da quella che solleva.

**c) ⚠️ Il nome fantasma nel diario.**
`script.trgfn_prevent_modification_generic` passa a `fn_log_and_raise_error` il
nome **`trgfn_prevent_parameters_audit_modification`**, una funzione che nel
database **non esiste più** (verificato: zero righe in `pg_proc`). Ogni errore di
quel guard viene registrato in `dbops.error_log` sotto un pezzo fantasma: chi
indagasse partirebbe da un nome che non c'è.

La correzione è una riga — usare `TG_NAME`, come fanno gli altri guard generici.
È lo stesso residuo di rinomina della bonifica riferimenti morti: **un nome
hardcoded sopravvive alla funzione che lo portava**, e nessun presidio lo vede
perché è una stringa, non un riferimento.

---

## 16. Lotto 4 — la coda, e il percorso richiesta arriva a zero (2026-08-06)

Gli ultimi **14** codici da trigger. Non hanno un dominio che li tenga insieme —
`catalogo` 2, `config` 4, `dbops` 5, `shop` 1: li tiene insieme il fatto di
essere gli ultimi.

### 16.1 La ripartizione

| Status | Quanti | Codici |
|---|---|---|
| **500** | 6 | `E_ATTIVO_BLOCK` · `E_ATTIVO_REQUIRE` · `E_ATTIVO_BLOCK_REF_NULL` · `E_SQL_READ_TABLE` · `E_TXID_GENERATION` · `E_PROFILO_ACCESSO_TIPO_NON_GESTITO` |
| **400** | 8 | 5 `highlight_form_fields` (conti IVA acq/ven, binding profilo, esito non verdetto, articolo non composito) · 3 `show_error_banner` (solo-componente, IVA discordante BoM, canale ricevuta shop) |

Nessun 403, 404 o 409: la coda è fatta di anomalie tecniche e di validazioni.

I sei 500 sono la stessa famiglia dei lotti precedenti — `EXCEPTION WHEN OTHERS`
(tx_id), fallimento della **generazione** delle regole di automazione, trigger
dichiarato con troppo pochi argomenti, e il terzo ramo `ELSE` per un enum esteso
senza regola (`E_PROFILO_ACCESSO_TIPO_NON_GESTITO`, gemello esatto di
`E_RUOLO_APPLICATIVO_NON_GESTITO` del lotto 2).

### 16.2 ⚠️ Una scoperta sul registro: contiene codici che non arrivano mai

`E_ATTIVO_BLOCK_REF_NULL` è nominato da **un solo punto**, e quel punto usa
`script.fn_log_error_only` — che scrive in `dbops.error_log` e **non solleva**.
Il codice non raggiunge mai un client: lo status che gli abbiamo dato non lo
legge nessuno.

Non è un errore del registro, ed è utile dirlo bene: **la misura è volutamente
larga** (§7) e raccoglie ogni letterale `E_*` in un corpo PL/pgSQL vivo. Non
può sapere se quel punto solleva o solo registra — né dovrebbe: il giorno in cui
qualcuno cambia `fn_log_error_only` in `fn_log_and_raise_error`, il codice inizia
a viaggiare e la policy c'è già.

> Il costo di una policy in più è **una riga**. Il costo di accorgersi che manca
> è un operatore che riceve un 400 al posto di un 403. La misura larga è
> asimmetrica apposta, e questo è il caso che lo mostra dal lato meno ovvio.

### 16.3 Dove siamo — il percorso di una richiesta è coperto

| | inizio (2026-08-05) | ora |
|---|---|---|
| voci del registro | 141 | **51** (dopo l'applicazione) |
| **`da_trigger` senza policy** | **90** | **0** |
| codici decidi con una policy | 0 | **91** |

**Zero.** Ogni codice `E_*` che una funzione agganciata a un trigger può nominare
— cioè ogni codice che sta sul percorso di una richiesta vera — ha adesso un tipo
di risposta deciso leggendo il punto che lo solleva.

I **51** che restano stanno in funzioni **non** agganciate a un trigger: possono
non essere mai raggiunte dal web, ed è la ragione per cui il DB li aveva messi in
coda fin dall'inizio (§4). Sono il lotto 5, e non hanno fretta.

### 16.4 Richiesta al team DB — l'elenco definitivo (lotti 2+3+4)

**61 righe** da togliere dal CSV del registro e `20260805-37` da riapplicare.
Sono **tutte** le voci `da_trigger` rimaste: dopo l'applicazione il registro va da
**112 a 51** e i `da_trigger` a **zero**.

L'elenco esatto lo stampa il cancello, ed è la fonte da usare (non il CSV):

```bash
ZEROERP_TEST_DB_E2E=1 ./manage-test.sh apps.core.tests.test_error_codes_db_policy_guardrail
```

Restano validi i due difetti da correggere: il **messaggio** di
`E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO` (§14.5b) e il **nome fantasma** in
`script.trgfn_prevent_modification_generic` (§15.4c).

---

## 17. ✅ CHIUSO il fronte del percorso richiesta — 2026-08-06

Il DB ha applicato tutto (`9ed35504d`). Verificato sul database vivo, non dedotto
dal CSV:

| | atteso | trovato |
|---|---|---|
| voci del registro | 51 | **51** |
| **`da_trigger` senza policy** | **0** | **0** |
| codici nella vista | 361 | **361** |

**Cancello 4/4 verde. Suite 3580/3580 verde.**

I due difetti trovati leggendo sono corretti entrambi:

* il messaggio di `E_DATI_SOCIETARI_SOGGETTO_NON_TROVATO` dice ora «Soggetto %s
  non trovato: impossibile validare i dati societari», cioè **la condizione che
  solleva davvero**;
* `script.trgfn_prevent_modification_generic` passa `TG_NAME` invece del nome
  hardcoded: il diario non punta più a una funzione che non esiste. Il changeSet
  porta scritto anche il perché, quindi il residuo non torna per inerzia.

### 17.1 Il bilancio del terzo lato

| | 2026-08-05 | 2026-08-06 |
|---|---|---|
| codici che il DB può nominare | 360 | 361 |
| senza un tipo di risposta deciso | 141 | **51** |
| **sul percorso di una richiesta** | **90** | **0** |
| presidi sul codice errore | 2 lati su 3 | **3 su 3** |

**Novantuno decisioni** prese in un giorno, tutte leggendo il punto che solleva.
Tre volte il nome del codice diceva una cosa diversa dalla verità
(`E_DELETE_NOT_ALLOWED` non era uno stato, `E_FULFILL_NOT_FOUND` era davvero un
404, `E_SNAPSHOT_ID_NOT_FOUND` non lo era affatto), e due volte il codice ne
conteneva due (`E_STATO_SCONOSCIUTO`, spezzato; `E_SOGGETTI_RUOLI`, tenuto
insieme con la ragione scritta).

### 17.2 Cosa resta

**Il lotto 5: i 51 codici in funzioni non agganciate a trigger.** Possono non
essere mai raggiunte dal web — è la ragione per cui il DB li aveva messi in coda
fin dal §4 — e il loro tipo di risposta oggi non lo legge nessuno. Non hanno
fretta, ma il registro deve continuare a calare: il cancello non li lascerà
crescere e il verso 3 toglierà da solo quelli che il database smette di nominare.

⚠️ **Il quarto lato, che nessuno presidia.** Il messaggio corretto oggi era
sbagliato da sempre, ed è saltato fuori solo perché qualcuno stava leggendo il
codice a mano. Nessun controllo verifica che **il messaggio descriva la
condizione che solleva**: il guardrail DB controlla che il codice sia a catalogo,
il cancello che abbia una policy. Se ne trovassimo un secondo, varrebbe la pena
chiedersi come si presidia — un difetto isolato è un caso, due sono una
direzione.

---

## 18. Il quarto lato — misurato dal DB, verificato dal BE (2026-08-06)

Il DB ha girato la misura sul quarto lato: **998 punti di sollevamento, 349
codici distinti**, ~31 candidati dall'euristica, **7 difetti reali**. Precisione
~23%.

### 18.1 Il risultato più utile è la precisione, non i sette

**Con il 23% un cancello verrebbe spento in una settimana.** È la prima volta in
questo cantiere che una classe di difetti risulta **non presidiabile
automaticamente**, e va scritto accanto agli altri tre lati, non nascosto: gli
altri tre hanno una regola meccanica («il codice è a catalogo?», «ha una
policy?»), questo chiede di capire *cosa significa* la condizione. Nessuna
euristica sul testo ci arriva.

Concordo con il DB: **niente cancello.** La misura resta una **lente da
rilanciare quando si apre un lotto**, e lo script va in `scripts/sql/` con il
prefisso `check_` — la convenzione del progetto già distingue `check_*`
(strumento a mano) da `guardrail_*` (passo CI), quindi il nome dice da solo che
non è un cancello.

### 18.2 ⚠️ `E_PARAMETRO_INVALIDO` — la leva non è del BE

Il DB propone di correggere i 2 punti «subito, ma tocca il BE perché passerebbero
da 400 a 404». **L'esito è giusto, la leva no**, e la differenza conta:

> **113 funzioni** nominano `E_PARAMETRO_INVALIDO`. La sua policy — 400 con il
> campo evidenziato — è **corretta in 111 di quei punti**. Portarla a 404 per
> sistemarne due significherebbe rompere gli altri 111: un `IF NOT FOUND` che
> deve dire «non trovato» non si aggiusta cambiando cosa significa la parola.

La correzione è **lato DB**: sollevare un codice diverso in quei due punti. Non
esiste a catalogo un «non trovato» generico né uno specifico per l'offerta
(verificato: zero codici `E_OFFERTA_*_NON_TROVAT*`, zero `E_RECORD_*`), quindi
servono codici nuovi — `E_OFFERTA_NON_TROVATA` starebbe nella famiglia
`E_OFFERTA_*` che già esiste. Fatto quello, il BE dichiara i due codici con 404 e
il registro se li riprende per il tempo di un giro.

⭐ E vale la pena tenere la frase con cui il DB lo racconta: nel secondo punto il
codice **confessa nel commento** di essere stato scelto per quanti `%s` ha il
messaggio. *La forma della stringa di formato ha deciso la semantica*, ed è
arrivata fino allo status HTTP.

### 18.3 ⚠️ I 4 dell'handler `P0001` — la ragione è più forte di quella detta

Il DB propone di lasciarli, perché la correzione vera non è rinominare ma **non
catturare `P0001` genericamente**. Concordo, e c'è un argomento in più che rende
la cosa meno rinviabile di come sembra:

```sql
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_err_msg = MESSAGE_TEXT;
    PERFORM script.fn_log_and_raise_error(..., 'E_DOC_COMPONENTE_LISTINO_MANCANTE', ...)
```

Viene catturato **solo `MESSAGE_TEXT`**. Il codice strutturato dell'errore
originale — quello che il cantiere del codice errore strutturato ha appena finito
di far arrivare fino al backend — **non viene letto e va perso**: al suo posto
parte un codice diverso. Questi quattro punti **disfano il meccanismo appena
costruito**, e lo fanno in silenzio, perché il testo originale finisce in un
campo del payload che l'operatore non legge.

Effetto oggi: qualunque errore di dominio del resolver sottostante arriva al
client come **422 «Listino non configurato per uno dei componenti»** — anche
quando il listino c'entra nulla.

Resta vero che è una **modifica di comportamento**, non di etichetta, e va
decisa: lasciar passare l'errore del resolver significa che il chiamante vedrà
codici che oggi non vede.

### 18.4 Il terzo: la conferma che la lente funziona

`E_SNAPSHOT_ID_NOT_FOUND` la misura lo ritrova **da sola**, partendo da
un'euristica diversa da quella che ha usato il BE (lettura a mano, §15.1). Due
strade indipendenti sullo stesso punto: è la prova che la lente vede quello che
deve vedere, ed è già corretto (500).

### 18.5 Richieste al team DB (decisioni di Tid, 2026-08-06)

**a) Due codici nuovi per i punti di `E_PARAMETRO_INVALIDO`.** Non un generico
riutilizzabile: **i codici generici sono esattamente quelli che accumulano
significati**, ed `E_PARAMETRO_INVALIDO` è diventato così. Proposta:

| Punto | Codice | Perché lì |
|---|---|---|
| `vendite.fn_push_offerta_a_contratto` | `E_OFFERTA_NON_TROVATA` | sta nella famiglia `E_OFFERTA_*` che già esiste |
| `config.trgfn_profili_accesso_bindings_guard_coerenza` | gemello nella famiglia `E_PROFILO_ACCESSO_*` | idem, e il commento del codice dice già che è un fail-fast su caso limite |

Appena esistono, il BE li dichiara a **404** e il registro se li riprende per il
tempo di un giro — stesso schema di `E_STATO_SCONOSCIUTO`, già rodato.

**b) I 4 punti dell'handler `P0001`: il rilievo con la verifica, la correzione da
decidere insieme.** Non è solo un'etichetta imprecisa: **il codice strutturato
originale va perso** perché si cattura solo `MESSAGE_TEXT` (§18.3). Non-catturare
è una modifica di comportamento — i chiamanti vedranno codici che oggi non vedono
— e l'impatto va misurato dal DB prima di muoversi.

**c) Lo script della misura in `scripts/sql/`**, con prefisso `check_` (lente,
non cancello). Sì, è utile: la lente serve a ogni apertura di lotto, e riscriverla
ogni volta è il modo in cui sono nati i tre numeri diversi del §2.

---

## 19. ✅ Risposta del DB al §18 — e la lente ne trova altri cinque (2026-08-06)

> **Chi scrive:** DB (`dev/db-tid`), commit `feca4f935`. Tutto girato sul
> database vivo dopo la migrazione, non dedotto dai CSV.
> ℹ️ *Testo riportato nel brief dal BE: il commit del DB conteneva i changeSet,
> il CSV e la lente, ma non questa sezione — e senza, il §20 rimanderebbe al
> vuoto.*

### 19.1 §18.5a — i due codici, e perché la leva era davvero lì

`E_OFFERTA_NON_TROVATA` (894) e `E_PROFILO_ACCESSO_NON_TROVATO` (895), nelle
famiglie che già esistevano. Entrambi hanno **un solo segnaposto**: il vincolo
pratico che aveva guidato la scelta sbagliata resta soddisfatto, e in più dicono
la verità.

* `20260806-23` → `fn_push_offerta_a_contratto`. Tolto anche il valore variadico
  `'offerta non trovata: ' || id`: il messaggio del codice nuovo lo dice già, e
  ripeterlo era metà della frase autocontraddittoria;
* `20260806-22` → `trgfn_profili_accesso_bindings_guard_coerenza`.

⚠️ La **prima** guardia di `fn_push_offerta_a_contratto` resta
`E_PARAMETRO_INVALIDO`, e lì è corretta. Le due occorrenze si somigliano, ed è il
motivo per cui la prima passata della misura le aveva confuse: **conta il ramo
che solleva, non la funzione.**

Registro 51 → 53, `da_trigger` 0 → 1, per il tempo di un giro. Verificato:
registro 53, vista 363, i due codici a catalogo, `E_STATO_SCONOSCIUTO` ritirato
con `obsoleto_dal = 2026-08-06`.

### 19.2 §18.5b — l'impatto misurato, e perché non-catturare non basta

L'handler avvolge `fn_resolve_prezzo_listino_v2`; seguendo le chiamate a valle, i
codici oggi inghiottiti sono **sette**, e arrivano tutti al client come
`422 show_error_banner`. Dopo la correzione:

| Codice | Diventerebbe |
|---|---|
| `E_ARTICOLO_ESCLUSO_DA_CONTRATTO` | 422 `show_error_banner` (invariato) |
| `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C` | 400 `show_error_banner` |
| `E_PARAMETRO_INVALIDO` | 400 `highlight_form_fields` |
| `E_LISTINO_VERSIONE_NON_ATTIVA` | 404 `show_error_banner` |
| `E_CATEGORIA_LISTINO_NON_MAPPATA` · `E_PREZZO_LISTINO_NON_TROVATO` · `E_PREZZO_LISTINO_RIGA_NON_TROVATA` | 404 `show_empty_state` |

Sei su sette cambiano comportamento, e due meritano una decisione prima di
muoversi: le tre che diventano `show_empty_state` (ui_action pensata per una
lista vuota, non per una scrittura fallita) e `E_PARAMETRO_INVALIDO` con
`highlight_form_fields`, che evidenzierebbe un campo mai compilato dall'operatore.

> Direzione giusta, ma togliere l'handler da solo **sposta** il difetto invece di
> chiuderlo: due o tre policy vanno riviste insieme. È lavoro del BE, e questo è
> il numero per dimensionarlo. → *risposta nel §20.2.*

### 19.3 §18.5c — la lente c'è, gira, e si valida da sola

`scripts/sql/check_messaggio_vs_condizione.sql`, prefisso `check_` come chiesto.
Scritta in SQL invece di riusare il Python della prima passata: legge
`pg_proc.prosrc` **vivo**, quindi non può divergere dalla doc auto-gen. Stampa
una riga di contesto con la base misurata, perché un risultato vuoto non si
confonda con un'euristica rotta.

Eseguita: **978 punti, 344 codici, 31 candidati.**

⭐ Il collaudo migliore è **cosa non stampa più**: `fn_push_offerta_a_contratto` e
il guard dei profili sono spariti dal gruppo B. La stessa lente che li aveva
trovati conferma che sono chiusi, senza che nessuno debba ricordarsi di
ricontrollare.

### 19.4 ⚠️ Ma ne ha trovati altri tre identici, più due di un quarto tipo

Dei sei `E_PARAMETRO_INVALIDO` rimasti nel gruppo B, cinque sono guardie di
parametro legittime. **Tre no**, e sono la fotocopia dei due appena corretti —
`IF NOT FOUND` raccontato come «parametro non valido», 400 dove la verità è 404:

| Funzione | Riga |
|---|---|
| `vendite.fn_chiudi_contratto_per_successione` | 44 |
| `vendite.fn_contratto_riga_componenti_init` | 48 |
| `vendite.fn_offerta_eccezione_componenti_init` | 57 |

E **un quarto tipo, che la lente non cercava e ha trovato lo stesso**: in
`fn_contratto_riga_componenti_init` (riga 93) e `fn_offerta_eccezione_componenti_init`
(riga 122) `E_PARAMETRO_INVALIDO` si solleva su `IF v_prezzo = 0 AND obbligatorio`
— un componente obbligatorio senza prezzo. Non è un parametro e non è un'assenza:
è una **regola di dominio**.

Il §17.2 diceva «un difetto isolato è un caso, due sono una direzione». Sono
cinque più due, tutti nella stessa famiglia di funzioni, e dicono una cosa
precisa: **`E_PARAMETRO_INVALIDO` sta facendo ciò che il §18.5a attribuiva ai
codici generici — accumula significati.** Su 113 funzioni che lo nominano,
almeno cinque lo usano per «non trovato» e due per una regola di prezzo.

---

## 20. Risposta BE al §19 — tre riscontri che cambiano le conclusioni (2026-08-06)

### 20.1 §19.1 · i due codici sono dichiarati

`E_OFFERTA_NON_TROVATA` e `E_PROFILO_ACCESSO_NON_TROVATO` → **404 ·
`show_error_banner`**. Banner e non empty-state: sono scritture che falliscono
(push verso contratto, guard sui binding), non pagine da svuotare.

Verificato sul DB vivo: registro **53**, vista **363**, i due codici a catalogo,
`E_STATO_SCONOSCIUTO` con `obsoleto_dal = 2026-08-06`. Il cancello ora segnala
esattamente **2 righe da togliere** — l'ultimo giro.

⭐ Vale la pena rileggere la frase del §19.1: *«conta il ramo che solleva, non la
funzione»*. La prima guardia di `fn_push_offerta_a_contratto` resta
`E_PARAMETRO_INVALIDO` **ed è corretta**: due punti quasi identici nella stessa
funzione, verità diverse. È la ragione per cui la prima passata li aveva confusi.

### 20.2 §19.2 · la tabella d'impatto è superata di una riga, e il difetto è già vivo

Due correzioni al conto dei sette:

**1. `E_LISTINO_VERSIONE_NON_ATTIVA` non è più 404: è 422** dall'audit di poche
ore prima (§api.md). Quindi dopo la correzione dell'handler arriverebbe **422
`show_error_banner`** — cioè *identico* a quello che il client riceve oggi
dall'handler. **Un cambio di comportamento in meno**: sono cinque su sette, non
sei.

**2. ⚠️ Le tre `show_empty_state` sono un difetto che esiste già oggi, e
l'handler non c'entra.** Quei tre codici li solleva solo
`vendite.fn_resolve_prezzo_listino_v2`, che **l'API pricing chiama per via
diretta**: lì arrivano al client senza passare da nessun handler, con
`show_empty_state` addosso. L'handler non stava causando il difetto — ne stava
nascondendo una parte.

Quindi non era una cosa «da decidere prima di muoversi»: era da correggere
comunque. **Fatto**: i tre passano a `show_error_banner`, status **404
invariato** — la mappa, il prezzo e la riga davvero non ci sono, quello che era
sbagliato è dire a una scrittura fallita di svuotare una pagina.

**3. `E_PARAMETRO_INVALIDO` con `highlight_form_fields` resta.** L'obiezione è
giusta nel merito — nel resolver è il chiamante a passare un parametro sbagliato,
non l'operatore — ma la leva non è nel dizionario: **113 funzioni** lo nominano e
per la grande maggioranza l'evidenziazione del campo è corretta. È esattamente il
§18.2, e la cura è la stessa: correggere i punti che lo usano per dire altro
(§19.4), non rimappare la parola.

> Con questo, **togliere l'handler non sposta più il difetto**: restano cinque
> codici che cambiano comportamento, e tutti e cinque nella direzione giusta.

### 20.3 §19.4 · confermato, e un codice non serve crearlo

**I tre `IF NOT FOUND`: sì**, stessa forma dei due appena chiusi. Servono i tre
codici nelle rispettive famiglie e il BE li dichiara a **404** — tre righe.

**I due sul prezzo zero: il codice esiste già.**
`E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO` è a catalogo, dichiarato nel lotto 3
(**400 · `highlight_form_fields`**) e il suo messaggio è

> «Componente obbligatorio [%s]: il prezzo deve essere diverso da zero.»

cioè **letteralmente** la condizione `v_prezzo = 0 AND obbligatorio`. Non serve
un codice nuovo: serve usare quello. Lo solleva già
`script.trgfn_componenti_check_prezzo_obbligatorio` — le due funzioni
`*_componenti_init` stanno dicendo la stessa cosa con la parola sbagliata.

⭐ **Ed è la conferma migliore della diagnosi del §19.4.** Il codice giusto
esisteva già, nella famiglia giusta, con il messaggio giusto: `E_PARAMETRO_INVALIDO`
non è stato scelto perché mancasse un'alternativa, ma perché era **generico e a
portata di mano**. È il modo in cui i codici generici accumulano significati.

### 20.4 Cosa serve ora

| # | Cosa | Chi |
|---|---|---|
| 1 | togliere **2 righe** dal registro (`E_OFFERTA_NON_TROVATA`, `E_PROFILO_ACCESSO_NON_TROVATO`) e riapplicare il `20260805-37` | DB |
| 2 | i **3 codici nuovi** del §19.4 + far sollevare `E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO` nei due punti sul prezzo | DB |
| 3 | dichiarare i 3 codici a 404 quando esistono | BE |
| 4 | togliere l'handler `P0001` (§19.2) — ora senza effetti collaterali da sanare prima | DB |

**Suite 3580/3580.** L'unico rosso è il verso 2 del cancello con le due righe del
punto 1: il presidio che chiede al DB di completare il giro.

---

## 21. Audit di coerenza degli status — nato da qui, vale oltre (2026-08-06)

Chiuso il percorso richiesta, la domanda naturale è stata: **i 600 status che
abbiamo assegnato sono coerenti fra loro, o abbiamo appena creato una nuova
divergenza?** L'audit è una costola di questo cantiere; il dettaglio operativo
sta in [`api.md` §Tassonomia errori](../api.md), qui resta cosa ha trovato.

### 21.1 Cosa è emerso

| Cosa | Esito |
|---|---|
| `api.md` documentava **4 status**, il dizionario ne usava **11** | censimento completo, con la fonte RFC di ognuno |
| **una sola** divergenza fra le 53 coppie legacy/prefissato: `EMITTENTE_NON_MODIFICABILE` 409 vs `E_EMITTENTE_NON_MODIFICABILE` 400 | la voce senza prefisso era **orfana** (il DB l'aveva già tolta dal catalogo il 2026-08-05): rimossa |
| famiglia «immutabilità»: 29 codici a 409, **3 a 400** | i tre allineati a **409**, `ui_action` invariata |
| tre status con **un solo uso**: 423, 428, 502 | 423 → **403** · 428 **ritirato** · 502 **resta** |
| cinque 404 che erano configurazioni mancanti o non-trovati falsi | quattro → **500**, uno → **422** |

Dopo: **600 policy, nove status, tutti RFC 9110** — nessuno fuori dal nucleo HTTP.

### 21.2 Le tre cose che valgono più delle correzioni

**1. Il suffisso non decide lo status.** `api.md` diceva «il suffisso *determina*
la categoria». Assegnando 91 policy il nome ha mentito tre volte:
`E_SNAPSHOT_ID_NOT_FOUND` è un **500**, `E_DELETE_NOT_ALLOWED` un **403** e non un
409, `E_FULFILL_NOT_FOUND` un 404 ma per un'altra ragione. Ora il documento dice
«suggerisce», con i controesempi.

**2. Il criterio che distingue un 404 da un 500: chi può rimediare.** L'operatore
cambiando la richiesta → 404. Nessuno finché qualcuno non configura → **500**:
«non trovato» detto a chi non può trovarlo lo manda a cercare una cosa che per lui
non esiste.

**3. L'uniformità non è un valore in sé.** Dei tre status con un solo uso, due
sono stati cambiati perché dicevano una cosa falsa e **il terzo è rimasto perché
dice quella vera**: il 502 su `E_AI_PROVIDER_ERROR` è letteralmente la
definizione RFC (gateway verso un server a monte). Normalizzarlo avrebbe perso
l'unica informazione utile nei log.

### 21.3 ⚠️ Due volte la misura ha mentito, e la seconda l'ha presa la suite

* il primo censimento leggeva **570 blocchi su 602** — numeri plausibili e
  sbagliati, finiti in `api.md` prima di accorgersene. Il parser si fermava a un
  terminatore di indentazione che non è costante: ora il documento dice **come
  rifarlo** (delimitare ogni voce con la chiave successiva);
* `E_AI_CONFIRMATION_REQUIRED` è stato dichiarato «non usato da nessuno» sulla
  base di un `grep` il cui filtro `-v error_policies.py` **escludeva il file di
  test omonimo** — cioè proprio la prova cercata. Un test lo pinnava a 428. Se ne
  è accorta la suite, non la misura.

> Terza occorrenza della stessa lezione, dopo il 133/141/137 del §2 e il 23% del
> §18.1: **anche la misura è un programma, e può avere il suo difetto.** Ed è il
> motivo per cui nessuna di queste correzioni è stata applicata senza far girare
> i 3580 test.

### 21.4 Fuori perimetro ma nato qui — l'ambiente

La suite non partiva affatto: nel venv c'era **Django 6.1**, che ha rimosso
`django.utils.cache.cc_delim_re`, importato a livello di modulo da
`rest_framework/views.py`. Non un test rosso: l'intero backend che non si importa.
E **DRF 3.17.2 è l'ultima release esistente**, con quell'import ancora dentro.

Correzione in `backend/requirements.in`: `Django>=6.0,<7.0` → `<6.1`, con scritto
accanto **come si toglie** (quando esce una DRF che dichiara 6.1: verificare che
`cc_delim_re` sia sparito da `rest_framework/`, poi rialzare). Il `requirements.txt`
ricompilato è risultato **identico**: il tetto non cambia niente oggi, impedisce
il prossimo `pip-compile --upgrade`. La CI non era mai stata rotta — era solo il
venv locale.

---

## 22. Il §20.4 è chiuso — DB e BE (2026-08-07)

Il DB ha applicato tutti e quattro i punti (**collaudati prima di scrivere**:
definizioni vive estratte con `pg_get_functiondef`, trasformazioni con un
`assert` su ogni sostituzione, sei changeSet eseguiti interi in una transazione
annullata). Verificato dal BE sul database vivo:

| | atteso | trovato |
|---|---|---|
| voci del registro | 56 | **56** |
| codici nella vista | — | **365** |
| i tre codici nuovi a catalogo | 3 | **3** |
| funzioni con l'handler `P0001` | 0 | **0** |

### 22.1 I tre codici sono dichiarati

`E_CONTRATTO_NON_TROVATO` (896), `E_CONTRATTO_RIGA_NON_TROVATA` (897),
`E_OFFERTA_ECCEZIONE_NON_TROVATA` (898) → **404 · `show_error_banner`**. Banner
e non empty-state: successione contratto e init componenti sono scritture che
falliscono, non pagine da svuotare.

### 22.2 ⭐ Due difetti dentro il primo, che il solo cambio di codice non avrebbe visto

**Il valore variadico del prezzo zero.** Il messaggio è «Componente obbligatorio
[%s]» ma arrivava **l'id del documento**: la frase nominava la riga contratto al
posto del componente. Cambiare solo il codice avrebbe lasciato una frase che
indica l'oggetto sbagliato — e sarebbe stato invisibile, perché il codice ormai
era quello giusto.

⚠️ È la terza volta in questo cantiere che **un secondo difetto vive dentro il
primo**: era già successo con la `VARIADIC` senza `::text` (mismatch di UoM mai
riportato) e con il valore ripetuto in `fn_push_offerta_a_contratto`. Chi corregge
un codice errore deve guardare anche **cosa ci viene passato dentro**.

### 22.3 ⭐ Il collaudo che morde due volte, e la seconda è la più istruttiva

Il primo giro è fallito su un apostrofo non raddoppiato dentro un `COMMENT`: la
correzione non è stata raddoppiarlo a mano — *«farlo a mano è precisamente
l'errore che aveva appena rotto la verifica»* — ma far fare l'escape al
generatore.

Il secondo fallimento è più interessante: **è fallita l'assert, non la
trasformazione.** Il controllo cercava `SQLSTATE 'P0001'` nel risultato e la
trovava — **dentro il commento scritto per spiegarne la rimozione**. Ora il
controllo guarda che non resti una riga *eseguibile*.

> Una verifica che legge il testo non distingue il codice dalla spiegazione del
> codice. È la stessa famiglia del §2 (l'apostrofo dentro un commento SQL che
> inghiottiva le virgole) e del §21.3 (il `grep` che escludeva la propria prova):
> **la misura va scritta sapendo che il documento parla anche di sé stesso.**

### 22.4 La domanda aperta del §19.2: risposta

Il DB chiede se la policy di `E_PARAMETRO_INVALIDO` vada bene ora che, tolto
l'handler, quel codice può arrivare al client **dal resolver** — dove il
parametro sbagliato lo riceve la funzione, non l'operatore, e
`highlight_form_fields` evidenzierebbe un campo mai compilato.

**Verificato: oggi non evidenzia niente.** `ui_action` viaggia nell'envelope JSON
(i test lo asseriscono) ma **nessun file del frontend lo legge** — due ricerche
indipendenti su tutto `frontend/`, zero occorrenze. Il comportamento a video lo
decidono il codice errore e lo status; `ui_action` è oggi una **dichiarazione di
intento**, non un'azione.

Quindi:

1. **nessun rischio immediato**, e non serve toccare la policy per proteggersi;
2. **la leva resta al punto che solleva.** Se quel guard del resolver è davvero
   un errore del chiamante — un parametro che l'operatore non ha mai visto — la
   cura è la stessa dei cinque `IF NOT FOUND` appena chiusi: un codice suo. È
   materiale per il prossimo giro della lente, non una modifica al dizionario che
   113 funzioni condividono;
3. ⚠️ **da sapere per il giorno in cui il frontend leggerà `ui_action`**: quel
   giorno le differenze che abbiamo scritto (banner vs campo evidenziato vs stato
   vuoto) diventano comportamento, e le imprecisioni rimaste si vedranno tutte
   insieme. È un buon motivo per tenerle oneste adesso, che costa una riga.

### 22.5 Stato

**Suite 3580/3580.** Il cancello segnala **5 righe da togliere** dal registro —
i due codici del §19.1 e i tre di questo giro, tutti dichiarati. Registro
**56 → 51** quando il DB riapplica il `20260805-37`.

---

## 23. Le tre gemelle — il perimetro non era la funzione (2026-08-07)

Il DB ha tolto le cinque righe del §22.5 **e ne ha aggiunte tre**: registro
`56 − 5 + 3 = ` **54**, verificato sul DB vivo (vista 368).

Le tre sono `E_DDT_RIGA_NON_TROVATA` (899), `E_ORDINE_RIGA_NON_TROVATA` (900),
`E_PREVENTIVO_RIGA_NON_TROVATA` (901), da
`fn_ddt_riga_componenti_init`, `fn_ordine_riga_componenti_init`,
`fn_preventivo_riga_componenti_init`. **Dichiarate: 404 · `show_error_banner`.**

### 23.1 ⚠️ Perché erano sfuggite, ed è la lezione che resta

`fn_contratto_riga_componenti_init` **non è sola**: ha tre gemelle per dominio, e
tutte e quattro avevano lo stesso `IF NOT FOUND` raccontato come «parametro non
valido». La prima passata della lente ne aveva vista una.

Il dettaglio che rende la cosa istruttiva: **le quattro gemelle erano già state
riconosciute come gruppo** nel §19.2, quando si è misurato l'handler `P0001` — lì
si dice testualmente «`fn_contratto_riga_componenti_init` e le tre gemelle (ddt,
ordine, preventivo)», e l'handler è stato tolto **da tutte e quattro**. Sullo
stesso file, nello stesso giro, il difetto del *codice* è stato corretto su una
sola.

> Due difetti nella stessa funzione, uno visto come famiglia e uno come caso
> isolato. **Quando un difetto sta in una funzione che ha gemelle per dominio, il
> perimetro non è la funzione: sono tutte** — e conviene verificarlo prima di
> chiudere, non al giro dopo.

Il registro ha fatto il suo mestiere anche qui: i tre codici nuovi sono entrati
**nel registro** invece di restare fuori, quindi il cancello è rimasto verde
nell'intervallo fra il loro push e questa dichiarazione.

### 23.2 Stato

**608 policy, suite 3580/3580.** Il cancello segnala **3 righe da togliere** —
le tre appena dichiarate. Registro **54 → 51** quando il DB riapplica il
`20260805-37`, e con quello il quarto lato è chiuso davvero.

### 23.3 ✅ Il testo dei tre codici, corretto (2026-08-07)

Emerso dal cantiere pgTAP runner/RLS, che era arrivato qui perché i tre codici
avevano fatto diventare rossi quattro test. Due difetti nel campo `causa` di
`messaggi_errore.csv` — testo che finisce sotto gli occhi di chi legge l'errore:

1. **`vendite.fn_fn_ddt_riga_componenti_init`** — `fn_fn_`, una funzione che non
   esiste. Su tutte e tre (899, 900, 901); la 897 era scritta bene.
2. **Tutte e tre dicevano «Sesto e ultimo dei punti trovati dalla lente»** — una
   riga copiata su tre, e al massimo una poteva esserlo. Ma **nessuna delle tre
   lo è**: sono le gemelle trovate *insieme* nella seconda passata, come dice il
   §23.1 («la prima passata della lente ne aveva vista una»). Il testo ora lo
   descrive per quello che è, e rimanda a **§19.4 per il difetto** e a **§23 per
   le gemelle**, che sono due cose diverse.

Corretto **nel CSV**, che è la sede: il mirror `20260614-08` è
`runOnChange: true` + `validCheckSums: ANY` e lo rilegge al prossimo migrate.
Nessun changeSet nuovo.

> ℹ️ Il rimando «Brief terzo lato §19.4» nei sei codici **oggi risolve**: la
> sezione è stata scritta dal BE con `e83d44412`, dopo i commit che avevano
> introdotto i codici. Chi guardasse il repo nell'intervallo la troverebbe
> mancante — non era un errore, era un rimando in avanti.

---

## 24. ✅ QUARTO LATO CHIUSO — 2026-08-07

Il DB ha tolto le tre righe. Verificato sul database vivo, non dal CSV:

| | atteso | trovato |
|---|---|---|
| voci del registro | 51 | **51** |
| di cui `da_trigger` | 0 | **0** |
| i tre codici ancora nel registro | 0 | **0** |
| codici nella vista | — | **368** |

**Cancello 4/4 verde. Suite 3580/3580 verde.** Nessuna voce del registro ha una
policy, nessun codice fuori registro ne è privo, nessuna riga orfana.

### 24.1 Il bilancio dei due giorni

| | 2026-08-05 | 2026-08-07 |
|---|---|---|
| codici che il DB può nominare | 360 | **368** |
| senza un tipo di risposta deciso | 141 | **51** |
| **sul percorso di una richiesta** | **90** | **0** |
| policy dichiarate | 511 | **608** |
| lati presidiati | 2 su 3 | **3 su 3**, più una lente sul quarto |

**Novantanove decisioni** — 91 nei quattro lotti, 8 sui codici nati dalle
correzioni — tutte prese leggendo il punto che solleva.

### 24.2 Cosa resta, e non ha fretta

* **il lotto 5**: i 51 codici in funzioni non agganciate a un trigger, e
  ⚠️ **non sono affatto codici che nessuno legge** — vedi §24.4, che corregge
  questa riga come era stata scritta la prima volta;
* **due codici a più significati**, segnati e consapevoli: `E_PARAMETER_NOT_FOUND`
  (configurazione mancante **e** `override_id` nell'URL) e `E_SOGGETTI_RUOLI`
  (tre condizioni). Si spezzano quando i significati chiederanno reazioni
  diverse, non perché sono più d'uno;
* **`E_PARAMETRO_INVALIDO` nel resolver di prezzo** (§22.4): oggi invisibile
  perché il frontend non legge `ui_action`, materiale per il prossimo giro della
  lente;
* **la lente del quarto lato** (`scripts/sql/check_messaggio_vs_condizione.sql`)
  da rilanciare all'apertura di ogni lotto: non è un cancello e non deve
  diventarlo — 23% di precisione (§18.1).

### 24.3 Le cinque cose che valgono oltre questo cantiere

1. **Il nome del codice non decide lo status.** Su 99 decisioni il nome ha mentito
   tre volte, e ogni volta in una direzione diversa.
2. **Un codice si spezza quando i significati chiedono reazioni diverse**, non
   perché sono più d'uno (`E_STATO_SCONOSCIUTO` sì, `E_SOGGETTI_RUOLI` no).
3. **404 o 500 lo decide «chi può rimediare»**: l'operatore cambiando la
   richiesta, oppure nessuno finché qualcuno non configura.
4. **Un secondo difetto vive spesso dentro il primo** — tre volte qui, sempre nel
   valore passato al messaggio, mai nel codice.
5. **Anche la misura è un programma, e può avere il suo difetto**: 133/141/137, il
   parser che leggeva 570 blocchi su 602, il `grep` che escludeva la propria
   prova, l'assert che trovava `P0001` dentro il commento che ne spiegava la
   rimozione. Quattro volte in due giorni, su tre persone diverse.

### 24.4 ⚠️ Correzione — «tanto nessuno li legge» è falso per metà

Domanda di Tid (2026-08-07): se i 51 stanno in funzioni che nessuno legge, non si
chiudono in fretta proprio per quello?

**La premessa non regge, ed è colpa di come è stata scritta la §24.2.** Il flag
`da_trigger` dice *«non lo solleva un trigger»*, **non** *«non lo raggiunge
nessuno»*: il §4 lo aveva messo per dare un **ordine alle decisioni** e diceva
già, testualmente, «non è un criterio di esclusione». Nel riassumere il cantiere
quella sfumatura si è persa, ed è diventata una frase più comoda e sbagliata.

Misurato sui 51:

| | quanti | cosa sono |
|---:|---|---|
| **26** | codice sollevato da una funzione **chiamata direttamente da Django** | user-facing esattamente come i 90 da trigger |
| **23** | funzione chiamata **da altre funzioni SQL** | stanno su una catena che alla radice può benissimo essere una richiesta |
| **2** | `script.fn_disdetta_cliente` e `fn_guard_fornitore_attivo`: il nome non compare né nel backend né in nessun altro corpo PL/pgSQL | da capire se sono **superate o non ancora agganciate** — la distinzione del §3.3 della guida, quella che va fatta **prima** di cancellare qualcosa |

⭐ **La prova che chiude la questione era già in casa**: `E_STATO_WORKFLOW_NON_TROVATO`
ha `da_trigger = false` **ed è uno degli otto che abbiamo appena dichiarato a
404**, perché lo solleva `fn_cambia_stato_commessa` — che il backend chiama a ogni
cambio di stato. Nello stesso registro, con lo stesso flag, c'è
`E_COMMESSA_NON_TROVATA`: **stessa funzione**.

**Conseguenza pratica.** Il lotto 5 non è una pulizia a basso valore da fare in
fretta perché tanto non si vede: sono **26 codici che arrivano all'operatore
quanto i precedenti**, più 23 su catene da risalire. Si fa con lo stesso metodo e
costa quanto uno dei lotti già chiusi — non meno.

> E la lezione di metodo: **un flag nato per dare un ordine non diventa un
> criterio di esclusione** solo perché è comodo leggerlo così. Qui è successo in
> due giorni, sulla stessa persona che aveva letto il §4.

---

## 25. Lotto 5A — i 26 che il backend raggiunge (2026-08-07)

Scritti in `error_policies.py`, **non committati**. Sono i codici del §24.4 con
`da_trigger = false` **ma sollevati da funzioni che Django chiama direttamente**:
arrivano all'operatore quanto quelli da trigger.

### 25.1 La ripartizione

| Status | Quanti | Note |
|---|---|---|
| **404** | 6 | articolo, cliente, commessa, versione template, tipo ruolo (×2) |
| **409** | 8 | già emessa, non modificabile, sorgente già collegata, stato non pubblicabile, fattura senza righe, i due del push preventivo, riconciliazione ambigua |
| **422** | 1 | `E_DOC_COMPOSITO_BOM_VUOTA` |
| **500** | 3 | `E_QUERY_FAILED` · `E_JOB_TYPE_NON_TROVATO` · `E_SOGGETTI_RUOLI_RACE` |
| **501** | 1 | `E_JOB_TYPE_NON_ATTIVO` |
| **400** | 7 | 6 con campo evidenziato, `E_VALIDAZIONE` con banner |

### 25.2 Le quattro decisioni che non erano meccaniche

**1. `E_COMMESSA_NON_TROVATA` → 404, e chiude il §24.4.** Lo solleva
`fn_cambia_stato_commessa`: la **stessa funzione** di
`E_STATO_WORKFLOW_NON_TROVATO`, che sta a 404 dal lotto precedente. Due codici
della stessa funzione, stesso flag `da_trigger = false`, e uno solo era stato
considerato «letto da qualcuno».

**2. I due gemelli del registry job, separati.** `E_JOB_TYPE_NON_TROVATO` →
**500**: il tipo non è registrato in `dbops.coda_lavori_tipi`, cioè un job che il
backend accoda e nessuno ha seminato — gemello esatto di
`E_PIPELINE_TASK_HANDLER_NOT_FOUND`. `E_JOB_TYPE_NON_ATTIVO` → **501**: il tipo
**esiste** ed è stato disattivato di proposito, come `E_AI_DISABLED` e
`E_SHOP_NON_DISPONIBILE`. Due righe adiacenti nella stessa funzione, due verità
diverse: è il §19.1 che si ripete — *conta il ramo che solleva*.

**3. `E_DOC_COMPOSITO_BOM_VUOTA` → 422**, non 404. L'articolo composito c'è; la
sua distinta non ha componenti validi **alla data**. Stessa forma di
`E_LISTINO_VERSIONE_NON_ATTIVA`, corretto ieri per la stessa ragione.

**4. `E_COD_INT_RUOLO` → 404 e non 500.** Sembrava configurazione mancante, ma il
codice ruolo arriva **dal chiamante** (`assign_ruolo(soggetto_id, codice_ruolo)`):
è un riferimento che non risolve, non un seed dimenticato. Letto dal repository
Python, non dedotto dal nome.

### 25.3 ⚠️ Due codici che non arrivano a nessuno, e un secondo accumulatore

* **`E_RECONCILE_AMBIGUO` non viene sollevato**: `fn_reconcile_sorgente` lo
  **scrive** nella colonna `errcode` di `pratiche.reconcile_errori`, e nessun
  codice Python legge quella tabella. È un **codice-dato**, come
  `E_ATTIVO_BLOCK_REF_NULL` (§16.2): la policy esiste perché il cancello la
  pretende, ed è giusto che la pretenda;
* **`E_VALIDAZIONE` è nominato da 10 funzioni** con un messaggio passthrough
  («Validazione fallita: %s»). È il secondo accumulatore dopo
  `E_PARAMETRO_INVALIDO` (113 funzioni). Per questo **banner e non campo
  evidenziato**: non sappiamo quale campo sarebbe. Materiale per la prossima
  passata della lente.

### 25.4 Stato

**634 policy, suite 3580/3580.** Il cancello segnala **26 righe da togliere** —
tutte quelle appena dichiarate. Registro **51 → 25** quando il DB riapplica il
`20260805-37`; i 25 rimasti sono il lotto 5B (23 su catene SQL + le 2 funzioni
che nessuno nomina, §24.4).

---

## 26. Lotto 5B — e il registro arriva a zero (2026-08-07)

Fatto **subito dopo il 5A**, su decisione di Tid: «senza fare tanti giri con il
DB, non c'è produzione». Dimezza i giri e il metodo non cambia.

Gli ultimi **25**: quelli sollevati da funzioni che il backend non chiama
direttamente, ma che stanno su catene SQL.

| Status | Quanti | Chi |
|---|---|---|
| **500** | 9 | il **framework di automazione** (`fn_run_automations_*`, `fn_ensure_storico_table`) più `E_DEFAULT_ERRATO` e `E_SCADENZE_TERMINE_INVALIDO` |
| **409** | 9 | fornitore non attivo/bloccato, cliente non attivo, le due guardie commessa, le tre scadenze, stato lotto incoerente |
| **404** | 2 | fornitore e soggetto non trovati |
| **400** | 5 | 4 con campo evidenziato, `E_AUTH_USER_SOGGETTO_SENZA_CF` con banner |

### 26.1 Tre cose che si sono lette solo aprendo il codice

**1. ⭐ `E_SCADENZE_TERMINE_INVALIDO` si autodenuncia.** Il commento nel DB dice
che quel ramo «si raggiunge **solo aggirando il catalogo**», perché il `CHECK`
ammette una sola ripartizione. È una guardia difensiva contro una configurazione
corrotta — *«un piano rate calcolato con una regola che non esiste sarebbe peggio
di un errore»* — quindi **500**, non un errore dell'operatore. Dal nome
(`_INVALIDO`) si sarebbe scritto 400.

**2. `E_STORICO_PARENT_PK_NOT_FOUND` finisce per `NOT_FOUND` e non è un 404.**
Non manca un record richiesto: il provisioning dello storico non riesce a
determinare la PK della tabella padre. È il terzo `*_NOT_FOUND` che non è un 404,
dopo `E_SNAPSHOT_ID_NOT_FOUND` e `E_AI_TOOL_NOT_FOUND`.

**3. `E_ADMIN_UO_NON_TROVATA` copre due casi in una riga**: il guard è
`NOT EXISTS (... id = %s AND attivo = true)`, quindi scatta sia sull'unità
inesistente sia su quella disattivata. Il 404 sarebbe giusto solo nel primo e
mentirebbe nel secondo: **400 col campo evidenziato**, corretto in entrambi.

### 26.2 ⭐ Il registro arriva a zero

**659 policy. Suite 3580/3580.** Il cancello chiede di togliere **51 righe**:
cioè **tutto il registro**.

| | 2026-08-05 | ora |
|---|---|---|
| voci del registro | 141 | **51 → 0** (all'applicazione) |
| di cui sul percorso di una richiesta | 90 | **0** |
| policy dichiarate | 511 | **659** |

**Centocinquanta decisioni** in tre giorni, tutte prese leggendo il punto che
solleva.

⚠️ **La tabella però non si droppa.** A differenza del registro dei codici
legacy (guida §3.3, «a zero righe la tabella si toglie»), qui il registro vuoto
**serve**: il cancello lo interroga a ogni PR — se sparisse, il guard sullo
schema fallirebbe — ed è il posto dove atterrerà il prossimo codice che il DB
crea prima che il BE lo classifichi. **Un registro vuoto non è un registro
inutile: è un registro in pari.**

Da qui in avanti il verso 1 del cancello diventa il presidio vero: **qualunque
codice nuovo senza policy è rosso il giorno stesso.**

---

## 27. ✅ Il DB ha svuotato il registro — la premessa verificata prima (2026-08-07)

La richiesta del §26.2 era «una cosa sola, meccanica». Lo è, ma la parte che vale
è quella **prima** dell'edit: una richiesta di svuotare un registro va verificata,
altrimenti si svuota un registro che aveva ancora ragione di esistere.

### 27.1 Due controlli, non uno

**a) I 51 hanno tutti una policy?** Confronto fra le righe del CSV e le chiavi di
`backend/apps/core/services/error_policies.py`: **51 su 51 dichiarati, zero
mancanti.** Dice che il registro *può* calare.

**b) Ma il registro deve arrivare a ZERO, che è un'altra affermazione.** Non basta
che i 51 siano coperti: serve che **nessun altro codice** sia rimasto fuori nel
frattempo. Rilanciata la misura canonica citata nel changeset — la vista
`dbops.vw_codici_errore_da_dichiarare` sul DB vivo, meno le chiavi Python:

| | |
|---|---|
| codici nella vista canonica | **368** |
| policy dichiarate in `error_policies.py` | **607** |
| **ancora da dichiarare** | **0** |

> Il secondo controllo è quello che conta. Il primo avrebbe detto «sì» anche se
> nel frattempo fossero nati tre codici nuovi senza policy: avrebbe misurato
> l'elenco da cancellare, non lo stato del mondo.

ℹ️ Le 607 chiavi Python sono più dei 368 codici della vista, e va bene: la vista
elenca ciò che una funzione plpgsql viva *può* nominare, mentre `error_policies`
copre anche codici che nascono altrove. Il verso che presidia è uno solo — nessun
codice della vista senza policy — ed è a zero.

### 27.2 Cosa è stato fatto

`db/changelog/migrations_v2/80_data/sql/dbops/codici_errore_senza_policy.csv`
ridotto alla **sola intestazione**: 51 righe tolte, nessun changeSet nuovo. Il
`20260805-37` è `runOnChange: true` + `validCheckSums: ANY` ed è **`DELETE` +
`loadData`, non un upsert** — apposta perché il registro potesse calare: al
prossimo migrate cancella tutto e ricarica zero righe.

**La tabella `dbops.codici_errore_senza_policy` resta**, come chiede il §26.2.

⚠️ **Non ancora applicato al DB di sviluppo**: il valore è nel repo, serve un
`make db-migrate`. Finché non gira, la tabella contiene ancora le 51 righe e il
cancello continuerà a segnalarle.

⚠️ **Un rischio da guardare al primo migrate, non dopo.** Nessun altro
`loadData` del repo punta oggi a un CSV di sole intestazioni: non c'è un
precedente che dica come si comporta. Il changeSet ha `failOnError: true`, quindi
un eventuale rifiuto è **rumoroso e senza danni** (il `DELETE` sta nella stessa
transazione), ma va visto girare prima di chiamare chiuso il cantiere.

✅ **Aggiornato anche il `20260805-37`**: intestazione e `comment:` dicevano
ancora «Le 141 voci, fotografate il 2026-08-05». Ora raccontano il registro per
quello che è — un mirror vivo azzerato il 2026-08-07 — e tengono dentro la
storia del numero (`141 → 51 → 25 → 0`), che da solo non si spiegherebbe.

> Toccare un changelog mergiato di norma non si fa. **Qui è sicuro per come è
> fatto quel changeSet**: `runOnChange: true` + `validCheckSums: ANY` significa
> che ri-esegue a ogni variazione e accetta qualunque checksum — non c'è
> sequenza da rompere. La regola che protegge i changelog mergiati protegge la
> catena dei checksum, e questo changeSet ne è fuori per progetto.

### 27.3 Le tre cose «per la prossima volta» non sono state toccate

Le due funzioni orfane (`script.fn_disdetta_cliente`,
`anagrafiche.fn_guard_fornitore_attivo`), i due accumulatori
(`E_PARAMETRO_INVALIDO`, `E_VALIDAZIONE`) e la lente da rilanciare a ogni lotto
restano **aperte e non bloccanti**, come scritte dal BE. Nessuna richiede il DB
adesso; la prima — *superate o non ancora agganciate?* — è una domanda per Tid,
non una misura.

---

## 28. ✅ CANTIERE CHIUSO — 2026-08-07

Il registro nasce il 2026-08-05 con **141 voci** e arriva a **zero** in tre
giorni. Non svuotato: **in pari**, verificato sul DB vivo con la misura canonica
(§27.1) — 368 codici nella vista, 659 policy, **0 da dichiarare**.

| | 2026-08-05 | alla chiusura |
|---|---|---|
| voci del registro | 141 | **0** |
| di cui sul percorso di una richiesta (`da_trigger`) | 90 | **0** |
| policy dichiarate | 511 | **659** |
| lati del presidio coperti | 2 su 4 | **4 su 4** |

### 28.1 L'ultimo miglio, e cosa lo tiene aperto

Tutto il contenuto è fatto. Resta **un solo gesto meccanico**: `make db-migrate`,
che applica il `20260805-37` (`DELETE` + `loadData` su CSV di sole intestazioni)
e porta la tabella a zero righe anche sul DB di sviluppo.

⚠️ **Va visto girare.** Nessun altro `loadData` del repo punta oggi a un CSV di
sole intestazioni: non c'è un precedente che dica come si comporta Liquibase 5.
Il changeSet ha `failOnError: true` e il `DELETE` sta nella stessa transazione,
quindi un rifiuto sarebbe rumoroso e senza danni — ma finché non gira, la
chiusura è sulla carta.

### 28.2 ⚠️ Cinque riferimenti che questo spostamento lascia indietro

Spostando il brief in `work-done/`, cinque riferimenti **per path completo**
puntano a una cartella che non esiste più. Aggiornati quelli che si potevano
toccare (`docs/it/dev/api.md`, `scripts/sql/check_messaggio_vs_condizione.sql`,
`brief-db-codice-errore-strutturato.md`, e il `20260805-37` che è
`runOnChange` + `validCheckSums: ANY`). Restano:

| dove | quanti | perché non si tocca |
|---|---|---|
| `backend/apps/core/services/error_policies.py` (§10, §14, §15) | 3 | **perimetro BE** — richiesta al team BE, sotto |
| `20260805-35-create-vw-codici-errore-da-dichiarare` (`20_code`) | 1 | changelog mergiato, `runOnChange: false`: cambiare un commento ne cambia il checksum e rompe il migrate |
| `20260805-36-create-codici-errore-senza-policy` (`00_schema`) | 1 | idem |

**Richiesta al team BE** (una riga, quando capita): in
`error_policies.py` sostituire `docs/it/dev/work-in-progress/` con
`docs/it/dev/work-done/` nei tre commenti che citano questo brief. Non blocca
niente — è un rimando che non risolve più.

I due changelog restano com'erano **di proposito**: il costo di correggerli è un
migrate rotto, il costo di lasciarli è un lettore che cerca il file un livello
più in là. Chi arriva da lì lo trova in `docs/it/dev/work-done/`.

### 28.3 Le tre cose «per la prossima volta», che restano aperte

Non bloccano nulla, e sono scritte qui perché fra un mese nessuno le
ricostruirebbe (§27.3):

1. **Le due funzioni orfane** — `script.fn_disdetta_cliente` e
   `anagrafiche.fn_guard_fornitore_attivo`: nessuno le nomina, né il backend né
   altre funzioni SQL. I loro codici sono dichiarati perché il cancello li vuole,
   ma la domanda vera — **superate o non ancora agganciate?** — non è una misura:
   nessuna query la risponde. Sta nei commenti delle funzioni, o nella memoria di
   chi le ha scritte.
2. **I due accumulatori** — `E_PARAMETRO_INVALIDO` (113 funzioni, almeno 5 usi per
   «non trovato») ed `E_VALIDAZIONE` (10 funzioni, messaggio passthrough). Non
   sono difetti aperti: sono la stessa malattia già curata cinque volte, e si
   vedono con la lente.
3. **La lente** — `scripts/sql/check_messaggio_vs_condizione.sql`, da rilanciare
   a ogni apertura di lotto. **Non è un cancello e non deve diventarlo**: 23% di
   precisione (§18.1).
