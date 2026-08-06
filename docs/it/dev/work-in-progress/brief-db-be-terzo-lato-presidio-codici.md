# Brief DB+BE — il terzo lato: i codici che il database dice e nessuno ha classificato

**Chi scrive:** DB (`dev/db-tid`), 2026-08-05.
**Origine:** rilievo del team BE, §12.5 di
[brief-db-codice-errore-strutturato](../work-done/brief-db-codice-errore-strutturato.md) (chiuso).
**Stato:** 🟢 **fronte del percorso richiesta CHIUSO (§17, 2026-08-06). Cancello 4/4 · suite 3580/3580 · registro 141 → 51 · `da_trigger` senza policy 90 → **0** · 91 codici decisi in quattro lotti. Resta il lotto 5 (i 51 non da trigger), senza fretta.**
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

* [brief-db-codice-errore-strutturato](../work-done/brief-db-codice-errore-strutturato.md)
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
