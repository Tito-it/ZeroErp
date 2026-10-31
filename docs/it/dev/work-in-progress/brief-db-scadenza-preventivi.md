# Brief DB — La scadenza dei preventivi (EMESSO → SCADUTO)

## ⏭️ Chi riparte — aggiornato al 2026-10-31

**Riparte: Tid**, con la decisione E-1 (§4): la scadenza la scrive un processo del database, oppure SCADUTO
esce dal modello del preventivo. Nessuno sviluppo prima del via. **Prima di decidere leggere il §6**: il
2026-10-31 il brief è stato riverificato, e il framework delle chiusure per scadenza nato il 2026-10-28 cambia
la forma dell'opzione (a) e la domanda E-3.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB | Il caso, i fatti, le domande | §1-§4 | — |
| 2 | ✅ team DB | Riverifica contro i giri 13-16 del modello (2026-10-31) | §6 | 1 |
| 3 | **Tid** ⏭️ | E-1 … E-3 | §4, §6 | 2 |
| 4 | team DB | Il giro, dopo il via | §5 | 3 |
| 5 | team BE/FE | Solo se E-1 tocca l'interfaccia (lo stato in lista, un filtro) | — | 4 |

Decisioni aperte di Tid: E-1 … E-3. Lavoro da committare: la riverifica del §6 (il brief del 2026-10-25 è
già committato).

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-25. **A chi:** Tid, poi il team DB.
> **Origine:** W-3 di [brief-modello-documento-vendita](../work-done/brief-modello-documento-vendita.md) §8.12 (debito X-2,
> dichiarato nel §8.6 del giro 6). Tid, 2026-10-25: «brief separato».
> **Brief vicini verificati:** [brief-modello-documento-vendita](../work-done/brief-modello-documento-vendita.md) (il
> verbo e i passaggi di processo: questo brief ne usa i pezzi comuni, non li cambia);
> [brief-design-proiezione-stato-dominio](brief-design-proiezione-stato-dominio.md) (legge SCADUTO come stato
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

⚠️ *La forma di (a) in E-1 e il presupposto di E-3 sono corretti nel §6.2 e nel §6.4.*

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
([brief-modello-documento-vendita](../work-done/brief-modello-documento-vendita.md), archiviato il
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

Consiglio (ii), da confermare: è la strada che già esiste per riproporre un EMESSO, e così la scadenza non
toglie all'operatore una strada che il preventivo «scaduto per data» oggi ha.

### 6.5 Il giro, con (a)

Al posto del §5: una riga del CSV `automazione_chiusura_scadenze` (+ il mirror `20260426-03`); il verbo di
chiusura, gemello di `fn_cessa_contratti_scaduti`; il guard di E-2, se deciso; la revisione da SCADUTO, se
E-3 (ii); pgTAP che costruiscono il caso (preventivo EMESSO con `validita_al` di ieri, di oggi, NULL) e il
`dbops/test-fn-apply-chiusura-scadenze-v1` portato alla terza riga; guida dei preventivi §3.1 (tabella degli
stati) e pagine manuali del framework.
