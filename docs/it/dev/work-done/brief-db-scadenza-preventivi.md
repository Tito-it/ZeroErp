# Brief DB — La scadenza dei preventivi (EMESSO → SCADUTO)

## ⏭️ Chi riparte — aggiornato al 2026-11-01

**Chiuso il 2026-11-01**: collaudo a video di Tid superato, brief archiviato in `work-done/`. Nessuno riparte;
i residui sono in PROJECT_CONTEXT § «Aperto — Media priorità» (§8.10).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB | Il caso, i fatti, le domande | §1-§4 | — |
| 2 | ✅ team DB | Riverifica contro i giri 13-16 del modello (2026-10-31) | §6 | 1 |
| 3 | ✅ Tid | E-1 … E-3, decise il 2026-10-31; via allo sviluppo | §7 | 2 |
| 4 | ✅ team DB | Il giro: changeSet, CSV, pgTAP, doc | §8 | 3 |
| 5 | ✅ Tid | Apply di `-60` … `-66`, pgTAP verdi (2026-10-31) | §8.2, §8.6 | 4 |
| 6 | ✅ team DB | E-4 (decisa da Tid il 2026-10-31): l'emissione con la validità già finita | §8.7 | 5 |
| 7 | ✅ Tid | Apply del `-67`, pgTAP verdi (2026-11-01) | §8.7 | 6 |
| 8 | ✅ team BE/FE | R-1, R-2, e due ricadute non elencate (2026-11-01) | §8.9 | 7 |
| 9 | ✅ Tid | Prova a video (R-3) superata e archiviazione in `work-done/` (2026-11-01) | §8.10 | 8 |

Decisioni aperte di Tid: nessuna in questo brief (una ereditata, §8.10). Lavoro da committare: il lavoro BE/FE
del §8.9 e questo brief; il giro DB è nel merge #1991.

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-25. **A chi:** Tid, poi il team DB.
> **Origine:** W-3 di [brief-modello-documento-vendita](brief-modello-documento-vendita.md) §8.12 (debito X-2,
> dichiarato nel §8.6 del giro 6). Tid, 2026-10-25: «brief separato».
> **Brief vicini verificati:** [brief-modello-documento-vendita](brief-modello-documento-vendita.md) (il
> verbo e i passaggi di processo: questo brief ne usa i pezzi comuni, non li cambia);
> [brief-design-proiezione-stato-dominio](../work-in-progress/brief-design-proiezione-stato-dominio.md) (legge SCADUTO come stato
> chiuso negativo: è un lettore, non uno scrittore). Nessun brief aperto scrive la scadenza.

## 1. Il caso

Il preventivo ha lo stato SCADUTO nel vocabolario (`config.stati_doc_preventivi`, fase CHIUSO) e il passaggio
EMESSO → SCADUTO nella matrice, segnato **di processo** (`manuale = false`): l'operatore non lo chiede, e il
verbo `vendite.fn_cambia_stato_preventivo` lo rifiuta se chiesto a mano (`E_DOC_PASSAGGIO_DI_PROCESSO`).

**Nessuno lo scrive.** La guida dei preventivi (§3.1) parlava di un «job notturno» al superamento di
`validita_al`, che non esiste né nel database né nel backend (verificato il 2026-10-25). Oggi un preventivo
emesso con la validità superata resta EMESSO, e si può ancora accettare.

## 2. Il modello

* La guida del modello (§5) dice chi scrive un passaggio di processo: **il verbo che ne è la causa**, con la
  sola seconda metà del verbo comune (`script.fn_doc_scrivi_stato`), attraverso la porta. Per la scadenza la
  causa è il **tempo**: non c'è un'operazione di un operatore da cui partire, quindi serve un processo.
* La data è sul documento: `vendite.preventivi.validita_al` (nullable: un preventivo senza scadenza non scade
  mai; il NULL è un caso del modello, non un'eccezione).
* I processi del database girano su pgAgent, col giornale dei job e il ruolo `zeroerp_job` (guida dei processi).
  ⚠️ *Superato per un lavoro di DOMINIO, vedi §6.1*: pgAgent fa da sveglia e accoda, il lavoro gira nella coda
  con l'identità tecnica dell'azienda.

## 3. Da verificare prima del giro (DB)

⚠️ *Le tre domande hanno una risposta (o mezza) nel §6.3.*

1. Se l'accettazione di un preventivo con `validita_al` superata oggi è rifiutata da qualche guard: se no, il
   documento scaduto «per data» e quello SCADUTO «per stato» dicono due cose diverse fino al passaggio del job.
2. Chi legge SCADUTO (capability, liste, la proiezione dello stato di dominio): cosa cambia per loro quando lo
   stato comincia a esistere davvero.
3. Il fuso: la scadenza è una data, il job gira a un'ora; quale giorno è «oggi» per un'azienda.

## 4. Decisioni per Tid

⚠️ *La forma di (a) in E-1 e il presupposto di E-3 sono corretti nel §6.2 e nel §6.4. ✅ Decise da Tid il
2026-10-31: §7.*

* **E-1. Chi scrive la scadenza.** (a) un processo del database (job pgAgent giornaliero) che porta in SCADUTO
  i preventivi EMESSI con `validita_al` superata, con un verbo di processo; (b) SCADUTO esce dal modello: la
  scadenza resta una data, letta da chi la mostra, e l'accettazione oltre la data si rifiuta nel guard.
  **Consiglio (a)**: lo stato c'è già nel vocabolario e nella matrice, e lo leggono già capability e
  proiezione dello stato di dominio; (b) è una revoca del modello attuale del preventivo.
* **E-2. L'accettazione oltre la data.** Con (a), fra la scadenza e il passaggio del job un preventivo è
  ancora EMESSO: si rifiuta l'accettazione anche per data (nel guard di transizione), o basta il job?
  Consiglio: anche nel guard, perché la regola non dipenda dall'ora del job.
* **E-3. Riaprire uno scaduto.** Oggi SCADUTO è terminale. Una revisione del preventivo (la funzione
  esiste) è la via per riproporlo, o serve un passaggio SCADUTO → EMESSO con una nuova data?

## 5. Il giro (dopo il via)

Si scrive dopo le decisioni: verbo di processo, job e sua registrazione nel catalogo dei processi, guard
(E-2), pgTAP che costruiscono il caso (un preventivo con `validita_al` passata), guida dei preventivi §3.1.
⚠️ *Con (a) niente job nuovo: il perimetro corretto è nel §6.5.*

## 6. Riverifica del 2026-10-31

Il brief è del 2026-10-25. Nel frattempo il modello del documento di vendita ha chiuso i giri 13-16
([brief-modello-documento-vendita](brief-modello-documento-vendita.md), archiviato il
2026-10-31). Riletti il registro, i verbi e le guide: le §1 e la diagnosi restano vere, alcuni pezzi del
§2, del §4 e del §5 sono stantii.

### 6.1 Cosa resta vero

* SCADUTO nel vocabolario (`config.stati_doc_preventivi`, id 7, fase CHIUSO, `terminale = true`) e la riga 5
  della matrice EMESSO → SCADUTO con `manuale = false`.
* Nessuno scrive SCADUTO: nessun verbo, nessuna riga del registro delle chiusure (§6.2).
* `validita_al` nullable; il FE la scrive come scadenza dell'offerta (`validita_dal` + i giorni del
  parametro `VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG`, etichetta «Valido al (scadenza)»).
* La guida dei preventivi §3.1 è già allineata al fatto («oggi nessuno lo scrive», verificato il 25 ottobre);
  resta stantia la sola riga di SCADUTO nella tabella degli stati («scaduta automaticamente (job notturno)»),
  da correggere nel giro.

### 6.2 Stantio: il job non va scritto, c'è già il framework

Dal 2026-10-26/28 (giri 11 e 16 del modello, Y-2 e L-2) esiste il **framework generico delle chiusure per
scadenza**: il registro `dbops.automazione_chiusura_scadenze`, letto da `dbops.fn_apply_chiusura_scadenze`.
Per una testata **sotto la porta** del modello il framework non fa l'`UPDATE` dinamico: chiama il **verbo di
chiusura** dichiarato nella colonna `verbo_chiusura` (changeSet `20261028-05`). Oggi due righe, entrambe
`classe = DOMINIO`:

| id | testata | da → a | verbo di chiusura |
| --- | --- | --- | --- |
| 1 | `vendite.listini_versioni` | ATTIVA → CHIUSA | `vendite.fn_chiudi_versioni_listino_scadute` |
| 2 | `vendite.contratti` | ATTIVO → CESSATO | `vendite.fn_cessa_contratti_scaduti` |

Quindi l'opzione (a) di E-1 non è più «un job pgAgent giornaliero col suo verbo»: è **la terza riga del
registro** (`vendite.preventivi`, `stato_doc_preventivo_id`, `FK`, `col_valido_al = validita_al`, EMESSO →
SCADUTO) e **il terzo verbo di chiusura**, gemello degli altri due (`vendite.fn_scadi_preventivi_scaduti` o
nome da fissare): senza parametri, nel perimetro della sessione, uno per uno dalla scrittura comune. Il
preventivo è già sotto la porta (`20261025-42`, verbo comune): senza `verbo_chiusura` il framework
risponderebbe `E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA`, non scriverebbe in silenzio.

Il job e la pipeline ci sono già: `chiusura_scadenze_daily` è una **sveglia** che passa dal giornale
(`maintenance.proc_accoda_chiusura_scadenze_job`) e accoda; il lavoro di DOMINIO gira nella coda con il
tesserino tecnico di ogni azienda
([guida dei lavori automatici](../../guide/processi-automatici-classe-e-identita.md)). Niente catalogo dei
processi nuovo, niente identità nuova.

### 6.3 Le domande del §3

1. **Accettazione oltre la data: nessun guard la rifiuta.** `trgfn_preventivi_guard_transizione` non legge
   `validita_al`, né lo fa `fn_cambia_stato_preventivo`. Il fatto del §1 resta.
2. **I lettori di SCADUTO e di `validita_al`.** Oltre a capability e proiezione dello stato di dominio:
   * `fn_crea_revisione_preventivo` ammette la revisione **solo da EMESSO** (letterale, non dal vocabolario).
     Oggi un preventivo con la data superata si può rivedere perché resta EMESSO; con (a), dopo il passaggio
     del job, non più. È un cambio di comportamento da dichiarare, e si lega a E-3 (§6.4).
   * `fn_list_preventivi_da_pushare` legge `validita_dal`/`validita_al` come **ripiego della competenza**
     (`competenza_dal`/`_al`), dietro `competenza_mese` che è autorevole. La stessa colonna dice due cose
     (scadenza dell'offerta e periodo di competenza del pregresso): non blocca il giro, va scritto.
3. **Il fuso: risposto dal framework.** «Oggi» è `script.fn_data_operativa()`, e chiude `validita_al <` oggi
   (stretto): un preventivo che scade oggi è valido fino a domani, come il contratto
   («un contratto che scade oggi resta attivo fino a domani»). Il significato di `validita_al` resta
   «ultimo giorno valido»; E-2, se si sceglie il guard, deve usare lo stesso confronto.

### 6.4 Stantio: E-3 dava per buona una strada che non c'è

E-3 diceva «una revisione del preventivo (la funzione esiste) è la via per riproporlo». La funzione esiste, ma
**rifiuta SCADUTO** (`E_PREV_REVISIONE_STATO_NON_AMMESSO`). E l'alternativa «SCADUTO → EMESSO con una nuova
data» urta il lock: `validita_al` è ferma fuori bozza (`trg_preventivi_a05_lock_fuori_bozza_upd`,
`E_DOC_CONDIZIONI_FUORI_BOZZA`). Quindi E-3 si riformula:

* **(i)** SCADUTO resta terminale, e per riproporre si crea un **preventivo nuovo** (copia, nessuna strada
  dedicata oggi);
* **(ii)** la revisione si apre anche da SCADUTO (cambia il guard della revisione, che oggi legge il
  letterale `'EMESSO'`);
* **(iii)** un passaggio SCADUTO → EMESSO, che chiede di riaprire `validita_al` fuori bozza: rompe il lock
  delle condizioni, **sconsigliato**.

Consiglio (ii) (✅ decisa da Tid il 2026-10-31, §7): è la strada che già esiste per riproporre un EMESSO, e così la scadenza non
toglie all'operatore una strada che il preventivo «scaduto per data» oggi ha.

### 6.5 Il giro, con (a)

Al posto del §5: una riga del CSV `automazione_chiusura_scadenze` (+ il mirror `20260426-03`); il verbo di
chiusura, gemello di `fn_cessa_contratti_scaduti`; il guard di E-2, se deciso; la revisione da SCADUTO, se
E-3 (ii); pgTAP che costruiscono il caso (preventivo EMESSO con `validita_al` di ieri, di oggi, NULL) e il
`dbops/test-fn-apply-chiusura-scadenze-v1` portato alla terza riga; guida dei preventivi §3.1 (tabella degli
stati) e pagine manuali del framework.

## 7. Decisioni di Tid (2026-10-31)

✅ **Decise da Tid il 2026-10-31: E-1 (a), E-2 si rifiuta, E-3 (ii). Il via allo sviluppo non è ancora
dato.**

* **E-1 = (a).** SCADUTO resta uno stato scritto, da un processo del database: la terza riga di
  `dbops.automazione_chiusura_scadenze` (`classe = DOMINIO`) e il verbo di chiusura del preventivo, gemello di
  `fn_cessa_contratti_scaduti` (§6.2). Completa il modello attuale, non lo revoca.
* **E-2 = si rifiuta anche per data.** L'accettazione (EMESSO → ACCETTATO) di un preventivo con
  `validita_al < script.fn_data_operativa()` si rifiuta nel guard di transizione, così la regola non dipende
  dall'ora del job. Stesso confronto del framework (§6.3.3): il giorno di `validita_al` è ancora valido;
  `validita_al` NULL non scade mai. Codice d'errore nuovo, da registrare (nome da fissare nel giro, es.
  `E_PREVENTIVO_VALIDITA_SCADUTA`). Ricaduta BE: il codice nella tassonomia degli errori.
* **E-3 = (ii).** La revisione si apre anche da SCADUTO: `fn_crea_revisione_preventivo` ammette EMESSO e
  SCADUTO. Nel giro si fissa se la regola si legge dal vocabolario invece che dai letterali, e cosa succede
  allo SCADUTO di origine (oggi la revisione da EMESSO lo supera: lo stesso trattamento, da verificare sul
  corpo). La nuova revisione nasce in bozza, con `validita_al` di nuovo modificabile. Ricaduta BE/FE: l'azione
  «Crea revisione» visibile anche su uno SCADUTO.

## 8. Piano di sviluppo (2026-10-31)

Via allo sviluppo di Tid il 2026-10-31 («fai il piano di sviluppo nel brief e poi procedi»). Le migrazioni le
applica Tid, i pgTAP li lancia Tid.

### 8.1 Le scelte del giro

* **D-1. SCADUTO si legge dal vocabolario, non dal letterale.** Colonna nuova `scadenza` su
  `config.stati_doc_preventivi` (boolean NOT NULL DEFAULT false, al più uno per vocabolario, solo su uno stato
  attivo), gemella di `cessazione` e `accettazione` (`20261031-05`), e il lettore `script.fn_stato_scadenza_id`
  sul lettore comune `script.fn_stato_per_colonna_id`. È la regola del giro 17 del modello («gli stati con un
  significato si leggono dal vocabolario»): lo stato di scadenza lo nominano tre punti (il verbo di chiusura, la
  revisione, la capability), e nessuno lo scrive come `'SCADUTO'`. Colonna propria e non `cessazione`: il
  contratto cessato ferma i canoni, il preventivo scaduto non si accetta più; il COMMENT di `20261031-05` vuole
  una colonna per significato. ⚠️ Il verbo gemello del listino legge ancora `'ATTIVA'`/`'CHIUSA'` come letterali:
  non è di questo giro.
* **D-2. La regola dell'accettazione sta in una `fn_check_*`.** «Accetta» si deve spegnere col motivo
  (linee guida SQL §5, «la domanda che viene prima»), quindi il predicato va in
  `script.fn_check_preventivo_accettabile(p_preventivo_id, p_validita_al)`, gemella di
  `fn_check_preventivo_emettibile`: MOTIVO 1 la validità finita (`p_validita_al < fn_data_operativa()`;
  `NULL` = non scade), MOTIVO 2 i prezzi non autorizzati (`fn_check_prezzi_autorizzati`, che oggi guard e
  capability chiamano ciascuno per sé). `p_validita_al` è un **parametro senza default**: il guard è
  `BEFORE ROW` e passa `NEW.validita_al`, la capability `p.validita_al`.
* **D-3. Il codice.** `E_PREV_VALIDITA_SCADUTA`, `CONFLITTO_STATO` (409): il preventivo può essere giusto, è il
  tempo a non ammettere l'accettazione. Frase con numero e data di fine validità; reason `VALIDITA_SCADUTA`,
  reason_key `vendite.preventivi.azione_reason.validita_scaduta` (da seminare nel FE, §8.4).
* **D-4. Nessuna precondizione temporale sul passaggio a SCADUTO nel guard.** Il contratto la ha (verso CESSATO,
  data arrivata) perché il cambio di stato generico ci arriva; EMESSO → SCADUTO è di processo (`manuale =
  false`), il verbo comune lo rifiuta a mano, e l'unico scrittore è il verbo di chiusura, che filtra la data.
* **D-5. La revisione da SCADUTO non tocca l'origine**: oggi la revisione da EMESSO non cambia lo stato della
  rev N (l'attiva la deriva `vw_preventivi`), e così da SCADUTO. La rev N+1 copia `validita_al` della rev N
  (già passata): è in bozza, l'operatore la riscrive. ⚠️ Nessuna regola impedisce oggi di **emettere** con la
  validità già finita: è una domanda nuova, non decisa (§8.5, E-4).

### 8.2 ChangeSet

| # | File | Che cosa |
| --- | --- | --- |
| `00_schema/config/20261031-60` | `alter-stati-doc-preventivi-add-scadenza` | D-1: colonna, CHECK, indice unico parziale |
| `20_code/script/20261031-61` | `create-fn-stato-scadenza-id` | D-1: il lettore |
| `20_code/script/20261031-62` | `create-fn-check-preventivo-accettabile` | D-2: i motivi dell'accettazione |
| `20_code/vendite/20261031-63` | `update-trgfn-preventivi-guard-transizione-accettazione-in-validita` | E-2: la Regola 3 solleva il primo motivo della check nuova |
| `20_code/script/20261031-64` | `update-fn-available-actions-preventivo-scadenza` | «Accetta» spento dalla check nuova; «Crea revisione» anche dallo stato di scadenza |
| `20_code/vendite/20261031-65` | `update-fn-crea-revisione-preventivo-da-scaduto` | E-3 (ii): ammessa dallo stato di emissione e da quello di scadenza, dal vocabolario |
| `20_code/vendite/20261031-66` | `create-fn-chiudi-preventivi-scaduti` | E-1 (a): il verbo di chiusura, gemello di `fn_cessa_contratti_scaduti` |
| CSV `config/stati_doc_preventivi` + mirror `20250917-01` | | `scadenza = t` su SCADUTO (id 7) |
| CSV `dbops/automazione_chiusura_scadenze` (id 3) | | il preventivo nel registro, `DOMINIO`, col verbo |
| CSV `dbops/processi_bersagli` (id 52) | | il bersaglio del processo `chiusura_scadenze_daily`, emittente via `emittente_fiscale_id` |
| CSV `config/messaggi_errore` (1417, 850), `config/codici_errore` | | il codice nuovo; la frase della revisione non dice più «solo da EMESSO» |

### 8.3 pgTAP e presidi

* Nuovo `db/pgtap/vendite/test-preventivo-scadenza-v1.sql`, che costruisce i casi: validità di ieri, di oggi,
  `NULL`; il verbo porta a SCADUTO solo il primo; il guard rifiuta l'accettazione del primo con
  `E_PREV_VALIDITA_SCADUTA` e accetta il secondo; la capability spegne «Accetta» col motivo; la revisione da
  SCADUTO nasce in bozza; il registro e il bersaglio del processo.
* Fixture portate (il preventivo arrivava ad ACCETTATO con una validità del 2026-06/07, già finita):
  `script/test-fn-available-actions-preventivo-v1`, `pratiche/test-reconcile-tie-break-flusso-origine`,
  `pratiche/test-guida-avanza-esito-proiettato`, `pratiche/test-proiezione-stato-sorgente` — `validita_al` a
  `fn_data_operativa() + 30`, come i builder. Le altre fixture che accettano un preventivo hanno validità
  futura (builder a +30, date 2080-2082) o `NULL`.
* Presidi trasversali da rilanciare: `script/test-doc-stati-dal-vocabolario-v1`,
  `script/test-rubinetto-primo-motivo-v1` (il conteggio non cambia: il guard chiamava già l'helper),
  `script/test-catalogo-messaggi-errore-completo`, `dbops/test-vw-codici-errore-motivo-nominato`,
  `dbops/test-riferimenti-morti-v1`, `dbops/test-processi-registro`, `dbops/test-fn-apply-chiusura-scadenze-v1`,
  `vendite/test-fn-crea-revisione-preventivo`, `script/test-fn-check-prezzi-autorizzati-v1`,
  `vendite/test-listino-versione-al-modello-v1` (il test 4 asserisce l'intero registro: portato ai tre verbi il
  2026-11-01, sfuggito al censimento e preso rosso da Tid).
* ⚠️ `vendite/test-preventivo-scadenza-v1`, rosso solo sullo scratch (`ERRORE_FIXTURE`, «riga scritta ma non
  visibile a chi chiama», 2026-11-01): senza un operatore pronto il contesto lo costruisce, e la veste nasce alla
  data operativa del fuso di casa. Il passaggio a ovest portava «oggi» al giorno prima della sua nascita
  (`fn_veste_utilizzabile`), il perimetro si svuotava e il billing account del builder spariva sotto RLS. Su
  dbdev si riusa un operatore vecchio. Corretto nel test: il fuso a ovest si imposta **prima** del contesto. La
  regola della veste è giusta e non cambia. Verificato sullo scratch come app: 19/19.

### 8.4 Ricadute BE/FE (richieste al team)

* **FE**: la chiave `vendite.preventivi.azione_reason.validita_scaduta` nei locales (`check_i18n_keys` la
  troverà nella doc auto-generata, controllo 4).
* **BE**: `E_PREV_VALIDITA_SCADUTA` nelle error policy generate (409). `preventivi_service.crea_revisione`
  non filtra lo stato in Python (letto il 2026-10-31): niente da togliere.
* **FE**: «Crea revisione» su un preventivo SCADUTO arriva dalla capability, nessun codice nuovo atteso.

### 8.5 Domanda nuova per Tid

* **E-4. L'emissione con la validità già finita.** Oggi si emette un preventivo con `validita_al` passata, e il
  job lo porta a SCADUTO la notte dopo. Lo si rifiuta anche all'emissione (motivo in
  `fn_check_preventivo_emettibile`, stesso codice o uno suo)? Consiglio: sì, per la stessa ragione di E-2.
  Non è in questo giro. ✅ **Decisa da Tid il 2026-10-31: sì, come consigliato** (§8.7).

### 8.6 Scritto e provato (2026-10-31)

Scritto come da §8.2 e §8.3, con due precisazioni:

* il letterale `'ACCETTATO'` della Regola 3 del guard **resta**: il giro 17 del modello tiene i letterali
  nei guard di transizione come condizione del passaggio (intestazione di
  `test-doc-stati-dal-vocabolario-v1`). Cambia solo la check che la Regola 3 solleva;
* la revisione e la capability leggono `emissione` e `scadenza` dalla riga del vocabolario che hanno già;
  il lettore `fn_stato_scadenza_id` lo usa il verbo di chiusura. Il `-65` chiude anche il debito del
  letterale `'EMESSO'` nella revisione, dichiarato in `20261031-19`.

Doc: guida dei preventivi §3.1 e §4.1 (stato, accettazione oltre la validità, revisione da SCADUTO,
diagramma), guida del modello §10 (riga del preventivo), linee guida SQL §7c, guida dei processi pgAgent,
pagine manuali del registro e del framework; pagine manuali nuove di `fn_stato_scadenza_id`,
`fn_check_preventivo_accettabile`, `fn_chiudi_preventivi_scaduti`.

**Prova pre-apply** sullo scratch `zeroerp_ruoli`, come `zeroerp_owner`, in transazione annullata: l'SQL
estratto dei sette changeSet più le righe dei CSV, messo dopo la riga `BEGIN;` di ogni pgTAP.

| Che cosa | Esito |
| --- | --- |
| `vendite/test-preventivo-scadenza-v1` (nuovo) | 15/15 |
| le quattro fixture portate, prima e dopo | identiche, tutte verdi; le versioni di HEAD con l'SQL estratto si fermano in errore (la prova che il porting serviva) |
| i presidi del §8.3 e gli altri 26 pgTAP che portano un preventivo ad ACCETTATO, prima e dopo | nessuna differenza. Due rossi uguali prima e dopo: `script/test-doc-lettori-stato-e-preventivo-al-modello-v1` n. 23 (dichiarato «rosso da owner»), `vendite/test-annullo-documento-con-legami-v1` (1 su 30) |
| preCondition, ciascuna dopo i changeSet che la precedono | tutte all'atteso |
| firme ancorate | una sola funzione per nome; il verbo è DEFINER con EXECUTE alla sola applicazione |

⚠️ Non provato qui: il loader dei CSV (il seed è simulato con `INSERT`/`UPDATE`; la colonna nuova del
vocabolario ha solo `t`/`f`, nessuna cella vuota), la corsa come applicazione con la RLS, e il job vero
(sveglia, coda, tesserino). Li prova la corsa di Tid dopo l'apply. Da sapere: alla prima notte dopo
l'apply, su dbdev i preventivi EMESSI con la validità già finita passano a SCADUTO; è il comportamento
voluto.

### 8.7 E-4: l'emissione con la validità già finita (2026-10-31)

Decisa da Tid il 2026-10-31 («procedi come consigliato»), dopo l'apply del §8.2 (pgTAP verdi).

| ChangeSet / file | Che cosa |
| --- | --- |
| `20_code/script/20261031-67-update-fn-check-preventivo-emettibile-validita` | motivo 4 di `fn_check_preventivo_emettibile`: `validita_al < fn_data_operativa()` → `E_PREV_EMISSIONE_VALIDITA_SCADUTA` |
| CSV `codici_errore`, `messaggi_errore` (1418) | il codice, `DATO_ERRATO`, col campo `validita_al` nel dettaglio |
| `vendite/test-preventivo-scadenza-v1` | 15 → 19 test; la fixture del preventivo «emesso e poi scaduto» rifatta (sotto) |
| guida dei preventivi §3.1, pagina manuale della check | la regola |

* **Guard e capability non cambiano**: il primo solleva il primo motivo della check, la seconda spegne
  «Emetti» coi suoi motivi. La reason e la reason_key sono le stesse dell'accettazione
  (`VALIDITA_SCADUTA`, `vendite.preventivi.azione_reason.validita_scaduta`): una chiave sola nel FE.
  Il codice è un altro, perché la classe è un'altra: in bozza la data si corregge (`DATO_ERRATO`, campo
  `validita_al`), all'accettazione è ferma (`CONFLITTO_STATO`, la strada è la revisione).
* **Firma invariata, data letta per id.** La check è letta da un guard `BEFORE ROW`, ma sotto la porta il
  passaggio a EMESSO lo scrive solo `script.fn_doc_scrivi_stato`, con un `UPDATE` della sola colonna di
  stato: in quell'istruzione `validita_al` non cambia. Gli altri motivi della testata (gli indirizzi) si
  leggono già così. La check dell'accettazione (`-62`) prende invece la data come parametro: è nata nuova.
  Asimmetria dichiarata; uniformarla vorrebbe dire cambiare la firma di `fn_check_preventivo_emettibile`
  (sette chiamate in due pgTAP, guard e capability da riscrivere).
* **Il preventivo emesso e poi scaduto, nel pgTAP.** Con E-4 non si costruisce più emettendolo con la data
  passata: ci si arriva solo perché il tempo passa. Il test lo emette con il fuso dell'azienda a
  `Etc/GMT+12` e `validita_al` = oggi, poi sposta `SYSTEM_FUSO_ORARIO` a `Pacific/Kiritimati` (26 ore più
  avanti: la data operativa è sempre almeno il giorno dopo), come già `vendite/test-data-documento-v1`.
* **Censimento**: nessun altro pgTAP emette un preventivo con una validità passata (le date fisse sono
  2080+, i builder a +30, le quattro fixture del §8.3 già portate). Il test Django
  `vendite/tests/db/test_ricerca_liste_db.py` usa il 2083.

**Prova pre-apply** sullo scratch `zeroerp_ruoli` (con `-60` … `-66` già applicati), come `zeroerp_owner`,
in transazione annullata, SQL estratto del `-67` e delle righe dei cataloghi dopo la riga `BEGIN;`:

| Che cosa | Esito |
| --- | --- |
| `vendite/test-preventivo-scadenza-v1` | dopo 19/19; prima 15 ok, i test 16-18 rossi e la correzione della data fermata dal lock (senza la regola il preventivo si era emesso): la prova distingue |
| 49 pgTAP che emettono un preventivo, chiamano la check o sono presidi trasversali (motivi nominati, catalogo dei messaggi, riferimenti morti, rubinetto) | nessuna differenza fra prima e dopo; quattro rossi uguali prima e dopo, non toccati da E-4 (`script/test-doc-lettori-stato-e-preventivo-al-modello-v1`, `script/test-doc-verbo-comune-e-porta-v1`, `vendite/test-esecutivi-ba-coppia-v1`, `vendite/test-ordine-al-modello-v1`: da owner) |

Ricaduta BE: `E_PREV_EMISSIONE_VALIDITA_SCADUTA` nelle error policy generate (400, `DATO_ERRATO`). FE:
nessuna chiave nuova (la stessa del §8.4).

### 8.8 Chiusura del lato DB e richieste al team BE/FE (2026-11-01)

Applicato da Tid: `-60` … `-66` il 2026-10-31, `-67` il 2026-11-01, con i CSV di `80_data`; pgTAP verdi
(corsa di Tid, compreso `vendite/test-preventivo-scadenza-v1`, 19 test). Il lato DB del brief è
chiuso.

Le richieste al team BE/FE, nessuna bloccante per il DB:

| # | Lato | Che cosa | Perché |
| --- | --- | --- | --- |
| R-1 | FE | la chiave `vendite.preventivi.azione_reason.validita_scaduta` nei locales (it, en): «La validità del preventivo è finita» | la reason di «Accetta» (E-2) e di «Emetti» (E-4) spenti; senza la chiave il tooltip è vuoto. `check_i18n_keys` la trova nella doc auto-generata (controllo 4) |
| R-2 | BE | `E_PREV_VALIDITA_SCADUTA` (409, `CONFLITTO_STATO`) e `E_PREV_EMISSIONE_VALIDITA_SCADUTA` (400, `DATO_ERRATO`, campo `validita_al`) nelle error policy generate | i due codici nuovi; il secondo accende il campo «Valido al» del drawer |
| R-3 | BE/FE | prova a video: preventivo emesso con la validità finita (Accetta spento, Crea revisione acceso), lo stesso dopo il job (SCADUTO, Crea revisione acceso), bozza con la validità passata (Emetti spento, campo acceso) | nessun codice nuovo atteso: azioni e motivi arrivano dalla capability. `preventivi_service.crea_revisione` non filtra lo stato (letto il 2026-10-31) |

Da sapere: dalla prima notte dopo l'apply il job porta a SCADUTO, su dbdev, i preventivi EMESSI con la
validità già finita; è il comportamento voluto. Dopo la prova a video di Tid il brief va in `work-done/`.

### 8.9 Fatto dal team BE/FE (2026-11-01)

| # | Che cosa | Dove |
| --- | --- | --- |
| R-1 | `vendite.preventivi.azione_reason.validita_scaduta` in it («La validità del preventivo è finita.») ed en | `frontend/src/locales/*.json`; `check_i18n_keys` pulito |
| R-2 | i due codici in `error_policies_generated.py` (rigenerato: due voci in più, nessuna classe cambiata; `--check` allineato) e i loro ripieghi senza `%s` | `backend/apps/core/services/error_policies_generated.py`, `error_messages_fallback.py` |
| R-2 bis | ⚠️ il campo «Valido al» **non si sarebbe acceso**: `PreventiviForm` non riceveva i `campiErrati` del drawer. Ora li riceve e li lega a `validita_al` | `PreventiviForm.vue`, `PreventiviDrawer.vue` |
| R-2 ter | la giuntura provata sul DB vero: una bozza con la validità di ieri, «Emetti» → `E_PREV_EMISSIONE_VALIDITA_SCADUTA` col campo `validita_al` | `vendite/tests/db/test_preventivo_cambia_stato_db.py`, test 5 |
| fuori lista | la colonna nuova `scadenza` di `config.stati_doc_preventivi` (D-1) compare nel pannello di configurazione e non aveva l'etichetta: `config_panel.campi.scadenza` («Stato di scadenza» / «Expiry state»). L'ha trovata `core/tests/db/test_config_panel_registro_db` | `frontend/src/locales/*.json` |
| fuori lista | il ripiego di `E_PREV_REVISIONE_STATO_NON_AMMESSO` diceva ancora «solo da preventivo EMESSO»: allineato alla frase del catalogo (emesso o scaduto) | `error_messages_fallback.py` |

Test: `apps.core.tests` + `apps.vendite.tests` con `ZEROERP_TEST_DB_E2E=1`. Resta un rosso **non di questo
brief**: `core/tests/db/test_parameter_overrides_db.test_valore_fuori_forma_non_si_salva` (il campo `value` non
arriva), già in carico al team DB nel §7.7.1 di
[brief-db-liste-datatable-grezze-secondo-giro](../work-in-progress/brief-db-liste-datatable-grezze-secondo-giro.md).

Per la prova a video (R-3): il ripiego nuovo è Python, il BE di sviluppo va ricaricato (`kill -HUP` sul master di
gunicorn) e il FE ricompilato.

### 8.10 Collaudo e chiusura (2026-11-01)

Prova a video di Tid superata sui tre casi di R-3: la bozza con la validità passata («Emetti» spento col motivo),
lo SCADUTO portato dal job («Crea revisione» acceso, la revisione nasce in bozza e si riemette con una data
nuova), l'EMESSO con la validità finita prima del job (costruito spostando `SYSTEM_FUSO_ORARIO`: «Accetta»
spento col motivo, «Crea revisione» acceso). Brief archiviato in `work-done/`.

Residui, ereditati in PROJECT_CONTEXT § «Aperto — Media priorità», nessuno bloccante:

* **`validita_al` dice due cose** (§6.3.2): la scadenza dell'offerta e, come ripiego dietro `competenza_mese`,
  il periodo di competenza (`fn_list_preventivi_da_pushare`, `vw_dash_fatturazione_preventivi`). Da decidere,
  di Tid, se la competenza debba avere una sede sua; poi team DB.
* **Il verbo di chiusura del listino legge ancora i letterali** `'ATTIVA'`/`'CHIUSA'` (D-1): il gemello del
  preventivo legge lo stato di scadenza dal vocabolario. Team DB, alla regola del giro 17 del modello.
