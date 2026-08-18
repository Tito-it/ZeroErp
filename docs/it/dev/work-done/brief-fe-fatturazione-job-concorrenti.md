# Brief FE — fatturare più gruppi in giri separati senza bloccare la lista

> **Tipo**: brief esecutivo frontend · **Data**: 2026-08-16 ·
> **Approfondimento, piano, decisioni e realizzazione**: 2026-08-17 ·
> **Owner**: Tid · **Branch**: `dev/backend-tid`
>
> ✅ **REALIZZATO E VALIDATO IN APP** (Tid, 2026-08-17): due giri concorrenti,
> ordine di esecuzione corretto, **esiti attribuiti al giro giusto** — che era il
> punto delicato. Esito e residui in §8.12; decisioni in §9.
>
> Realizzato: §8.0..§8.8 (FE) + §8.11 (ordine di esecuzione della coda, BE
> `apps/core`) + il gate permessi di `RowActionsMenu`, trovato nella stessa
> sessione. File: `useJobPolling.js`, `DashboardCompetenzaView.vue`,
> `RowActionsMenu.vue`, `it.json`/`en.json`, `main.css`,
> `coda_lavori/repository.py` (+ test), `frontend-standards.md`, catalogo BB.
> Build, eslint, `check_i18n_keys.py` e suite Django (3678) verdi. **Nessuna
> modifica al DB.**
>
> Validato anche il **rientro nel tab** (§8.2, prova di Tid). Restano tre prove
> non esercitate (§8.12), due delle quali ora difficili da riprodurre da una sola
> sessione proprio perché la §8.4 le previene; la terza è la mutua esclusione col
> verbo di mese (§8.7).
>
> 📁 **CHIUSO e spostato in `work-done` il 2026-08-17** (decisione di Tid): il
> cantiere era svincolato dal DB e non ha lasciato prerequisiti aperti.
> ⛔ **Unica eccezione: la §10** — il cantiere «comporre la selezione» (filtro
> cliente, colonne BA/id fiscale, ricerca) **non è chiuso**, dipende dal DB e vive
> nel brief `brief-db-dash-competenza-gruppi-cliente-e-ricerca*.md` in
> `work-in-progress`. La §10 resta qui come dettaglio FE di quel cantiere, non
> come lavoro fatto.
>
> Nasce da un
> rilievo in-app di Tid (2026-08-16) sulla lista gruppi fatturabili: avviata la
> fatturazione di un gruppo, **tutte** le righe restano spente fino alla fine del
> giro. La domanda era: *«dato che c'è la coda che le gestisce, non si possono
> selezionare le altre?»*.
>
> **Il palliativo è già in repo** (stessa giornata): spinner sulla riga in
> lavorazione + motivo su ogni azione spenta, così il blocco si spiega invece di
> sembrare un guasto. Questo brief descrive il lavoro **vero**, che è un'altra
> cosa e ha un costo diverso.
>
> **Rif.**: `DashboardCompetenzaView.vue` (verbo «Fattura selezionati» e kebab
> «Fattura questo») · `core/composables/useJobPolling.js`.
>
> **Le §1-§6 sono l'analisi del 2026-08-16, lasciata com'era.** La §7 riporta la
> verifica sul codice (FE e BE) del 2026-08-17: due affermazioni delle §3-§4 non
> reggono, e il piano della §8 tiene conto della correzione.

---

## 1. Perché oggi il blocco è globale — e non è una svista

`useJobPolling` segue **un solo job**. `start(jobId)` chiama `stop()` e
sostituisce l'`activeJobId`; i tick del job precedente escono in silenzio
(`if (jobId !== activeJobId) return`). Il commento della funzione lo dichiara:
*«un eventuale polling in corso viene sostituito — l'ultimo giro vince»*.

Ne discende che il blocco su tutte le righe **non protegge dal doppio invio**
(quello sarebbe già coperto da `azioneLoading` durante la POST): protegge
**l'esito del giro in corso**. Avviando un secondo giro, del primo si
perderebbe:

* i **lotti prodotti** (`lottiEmessi`, cioè l'aggancio «vai al lotto» per
  numerare);
* i **gruppi non serviti** con il loro motivo classificato — la parte aggiunta
  il 2026-08-15 proprio perché *«2 su 3 sembrava un successo pieno e il terzo
  restava fermo senza che nessuno lo cercasse»*;
* il conteggio dei **falliti parziali**.

⚠️ **Toglierlo senza fare il resto sarebbe una regressione**, non una
liberalizzazione: si scambierebbe un fastidio di interfaccia con la perdita
silenziosa di un risultato, su un verbo che produce fatture. È esattamente la
classe di difetto che questo cantiere ha già corretto una volta.

## 2. Il bisogno pratico è in gran parte già coperto

La **selezione multipla** manda tutti i gruppi scelti in **un unico job**
(`fatturaGruppi(selezioneGruppi)` → una sola chiamata, un solo `job_id`). Chi
vuole fatturare tre gruppi li spunta e preme una volta: la coda li lavora
insieme e l'esito torna completo.

Quindi il beneficio residuo di questo cantiere è **stretto**: poter avviare un
secondo giro *mentre il primo è in corso*, cioè su gruppi a cui si pensa dopo
aver già premuto. Vale la pena tenerlo presente prima di stimare: non è «poter
fatturare più gruppi», è «poter cambiare idea senza aspettare».

## 3. Cosa serve — quattro pezzi, e il terzo è quello che conta

**3.1 Polling multi-job.** `useJobPolling` deve seguire un **insieme** di job:
una mappa `jobId → stato`, un timer per job (o un tick unico che interroga
tutti), e `stop()` selettivo. Oggi `activeJobId` è uno scalare e `stop()` azzera
tutto. Il `polling` booleano diventa un conteggio o un `Set` non vuoto.

⚠️ Chi consuma `polling` come booleano (tre verbi in
`DashboardCompetenzaView`, più gli altri cruscotti) va verificato: il tipo
cambia, e un `v-if="polling"` su un `Set` sarebbe sempre vero.

> ⚠️ **Verifica 2026-08-17 — questo avviso è più grande del problema reale.**
> Vedi §7.1: il consumer è **uno solo** e il tipo non deve cambiare affatto.

**3.2 `gruppiInCorso` che fonde invece di rimpiazzare.** Oggi è
`new Set(apiOptions.gruppi)`: il secondo lancio cancellerebbe le marcature del
primo. Serve unione all'avvio e **sottrazione dei soli gruppi di quel job** alla
sua conclusione — quindi la mappa `jobId → gruppi` va tenuta, non solo l'insieme
piatto.

**3.3 Esiti accumulati e attribuiti — il pezzo delicato.** `buildEsitoOk`
oggi **sovrascrive**: `lottiEmessi.value = lotti`, `selezioneGruppi.value = []`.
Con più giri concorrenti serve:

* accumulare i lotti invece di rimpiazzarli, senza duplicati;
* azzerare **solo** i gruppi del job concluso, non tutta la selezione;
* riportare i «non serviti» di ciascun giro **dicendo di quale giro sono** — un
  elenco di motivi senza il giro di provenienza, con due giri in volo, non è
  interpretabile;
* decidere cosa fa `reloadDopoAzione()` quando un altro giro è ancora in corso:
  ricaricare la lista sotto i piedi di un job vivo può far sparire righe marcate
  e riapparire righe già consumate.

> ⚠️ **Verifica 2026-08-17**: l'ultimo punto non si concretizza come temuto (le
> marcature sono per chiave di dominio, non per indice) ma nasconde un effetto
> diverso e reale. Vedi §7.1.

**3.4 Un tetto esplicito.** Quanti giri concorrenti si ammettono? Illimitati
significa che l'operatore può accodare venti job con venti click e poi non
capirci più nulla negli esiti. Un tetto basso (2 o 3) con motivo parlante sul
verbo — *«hai già N giri in corso»* — è più onesto di nessun tetto.

> ⚠️ **Decisione D1 (2026-08-17): nessun tetto.** Il ragionamento resta valido
> come descrizione del rischio, ma il rimedio scelto è un altro. Vedi §7.3 e §9.

## 4. Cosa NON serve

* **Nulla lato DB o BE.** La coda gestisce già N job indipendenti e l'endpoint
  è lo stesso: il limite è interamente nel modo in cui il frontend *segue* i
  job, non nella capacità di eseguirli.
* **Nessuna nuova API.** `getFatturazioneRun(jobId)` si interroga già per id:
  chiamarla per N id è la stessa cosa fatta N volte.
* **Nessun cambio al verbo di mese né a «Rendi definitive»**: sono verbi di
  perimetro, uno per volta ha senso. La concorrenza riguarda la sola emissione
  **mirata**.

> ⚠️ **Verifica 2026-08-17 — la prima riga regge, la terza no.** Non serve
> toccare BE o DB, ed è vero che non nasce doppia fatturazione; ma i job **non
> girano in parallelo** e il verbo di mese **non è isolato** dai mirati. Vedi
> §7.2 (b), (e).

## 5. Definizione di «fatto»

* [ ] avviata la fatturazione del gruppo A, il gruppo B resta **selezionabile e
      fatturabile**; la riga A mostra lo spinner, la B no;
* [ ] concluso il giro di A, **solo** la riga A si sblocca e sparisce dalla
      lista: la marcatura di B (se avviata nel frattempo) resta;
* [ ] gli esiti dei due giri sono **entrambi** riportati, con i rispettivi
      lotti e i rispettivi «non serviti» attribuiti al giro giusto;
* [ ] raggiunto il tetto, il verbo si spegne con il **motivo** e non in
      silenzio;
* [ ] un giro andato in timeout di polling non lascia righe marcate per sempre
      (comportamento già corretto oggi, da preservare).

> Alla §8.9 la lista è estesa con i criteri nati dalla verifica (contesa fra
> giri, rientro nel tab, verbo di mese).

## 6. Stima e raccomandazione

Il lavoro è **tutto FE** e non è grande in righe, ma il §3.3 è delicato: si
tocca la contabilità degli esiti di un verbo che produce fatture, e gli errori
in quella zona sono silenziosi per costruzione — un lotto non riportato non dà
errore, semplicemente non compare.

**Raccomandazione: non aprirlo finché la selezione multipla basta.** Il momento
giusto è quando emergerà un caso reale in cui l'operatore deve avviare un
secondo giro senza poter aspettare il primo — allora il beneficio sarà
misurabile e non ipotetico. Se e quando si apre, il §3.3 va fatto **per primo**
e provato con due giri veri: è la parte in cui un errore non si vede.

> **Stato della raccomandazione**: Tid ha chiesto di partire (2026-08-17). La
> raccomandazione resta agli atti come misura del beneficio atteso, non come
> obiezione: la §7.2 (b) la rafforza — il beneficio è più stretto di quanto il
> §2 già dicesse — ma non cambia la decisione, che è di Tid.

---

## Parte II — Verifica sul codice (2026-08-17)

## 7. Cosa regge e cosa cade

### 7.1 Lato frontend

**Cade — «tre verbi in `DashboardCompetenzaView`, più gli altri cruscotti».**
`useJobPolling` ha **un solo consumer** in tutto il repo:
`DashboardCompetenzaView.vue:41`. Gli «altri cruscotti» non lo usano —
`useQueueCountsPolling` è un contatore *ambientale* (badge code in topbar), non
il follow-up di un job, e lo dichiara nel proprio header. I «tre verbi» sono tre
**istanze** dello stesso helper locale `useVerboFatturazione`
(`DashboardCompetenzaView.vue:722`), ciascuna con il **proprio** `useJobPolling`
e il proprio `polling`.

Due conseguenze pratiche, entrambe a favore:

* la concorrenza va abilitata **solo nell'istanza mirata**; i due verbi di
  perimetro (mese, «Rendi definitive») restano a un giro per volta senza che
  serva toccarli;
* il tipo di `polling` **non deve cambiare**. Tenendolo un **booleano computed**
  derivato dal conteggio dei job seguiti, nessun consumer si rompe e il rischio
  descritto nella §3.1 (`v-if` su un `Set` sempre vero) sparisce per
  costruzione. La grana fine si espone a parte (`nGiriInCorso`, `canStart`).

**Cade — «ricaricare la lista può far sparire righe marcate».** Le marcature
sono per `gruppo_key`, cioè una chiave di dominio, e il `data-key` della lista è
la stessa (`DashboardCompetenzaView.vue:1527`): il reload non le perde. L'effetto
reale è un altro e va comunque governato: le righe **consumate** dal giro
concluso spariscono dalla lista, quindi le pagine **scorrono**, e una riga
ancora marcata può finire su una pagina che l'operatore non ha davanti. Il chip
«in corso» non è più sufficiente da solo: serve un indicatore di **testata**, che
non dipenda dalla pagina a video (§8.6).

**Regge — i tre difetti strutturali della §3.** `gruppiInCorso` è un `ref(Set)`
azzerato *per intero* a fine giro (`DashboardCompetenzaView.vue:736,741`);
`buildEsitoOk` sovrascrive `lottiEmessi` e svuota tutta la selezione
(`:832-833`); `activeJobId` è uno scalare (`useJobPolling.js:67`). Tutto
confermato.

**Nuovo — tre punti che il brief non nominava.**

1. **`onDeactivated(stop)`** (`useJobPolling.js:129`): cambiando tab il
   follow-up si spegne e **non riparte**. L'esito è perso. Vale già oggi con un
   giro solo; con un tetto a N la probabilità di perdere un esito si moltiplica
   per N — proprio il difetto che questo cantiere esiste per evitare.
2. **La selezione si libera troppo tardi.** `selezioneGruppi.value = []` sta
   dentro `buildEsitoOk` (`:833`), cioè alla **conclusione** del giro. Finché
   resta lì, «cambiare idea senza aspettare» non funziona nemmeno con il polling
   multi-job: la selezione appena sottomessa resta spuntata e l'operatore non ha
   una lavagna pulita su cui comporre il secondo giro.
3. **Le righe di un giro vivo restano selezionabili.** `gruppiSelezionabili`
   (`:356`) filtra solo su `isGruppoEmittibile`. Con la concorrenza si può
   rispuntare A mentre A è in lavorazione e sottometterlo una seconda volta — ed
   è il caso che il BE **non** intercetta (§7.2 c).

### 7.2 Lato backend — la §4 va corretta in tre punti su cinque

**(a) Vero: non serve nulla lato BE/DB, e non nasce doppia fatturazione.** La
barriera è a livello di riga, non di job: `vendite.fn_select_attivita_fatturabili`
è invocata con `p_lock=true` (seed `fatturazione_pipeline.csv`) e fa
`FOR UPDATE ... SKIP LOCKED` più il re-check
`fatturato IS FALSE AND lock_in_fatturazione IS FALSE` prima di marcare. Una
stessa `attivita_fatturabili` non può essere presa da due giri: il secondo la
salta. Il rischio non è la fattura doppia — è l'**esito parziale**.

**(b) Falso: i job non girano in parallelo.** Il worker è un `Type=oneshot`
(`backend/deploy/systemd/zeroerp-coda-lavori.service`) su timer **al minuto**
(`backend/bin/install-timers.sh`), e la passata claima fino a 200 job e li lavora
in un **ciclo sequenziale** (`coda_lavori/drain_engine.py:105-120`). Il
`registered_job` dichiara esplicitamente *«NESSUN `lock_key`»*
(`draina_coda_lavori.py:11-16`): la serializzazione di oggi è **accidentale**,
non progettata — c'è un solo worker.

Quindi il secondo giro **non parte prima**: si mette in fila dietro il primo. Il
beneficio del cantiere è «poter **comporre e accodare** il secondo giro senza
aspettare», non «due giri che girano insieme». È più stretto di quanto la §2
dicesse, e va scritto perché è ciò che l'operatore vedrà: due spinner accesi, ma
il secondo esito arriva dopo il primo, non insieme.

**(c) Incompleto: la sovrapposizione parziale non è protetta a monte.** La
chiave di idempotenza business è
`FATTURAZIONE_GIRO:<competenza>:<scope>:<digest gruppi>`
(`apps/vendite/api/views.py:1474-1476`), dove il digest è lo sha256 dell'insieme
**ordinato e deduplicato** (`_fatturazione_job_helpers.py:356-360`), presidiato
da un unique parziale sui soli stati vivi
(`uq_coda_lavori_vivo_idem`, PENDING/IN_CORSO). Ne segue:

* insiemi **diversi** → due job distinti, come il brief assumeva;
* insiemi **identici** con job ancora vivo → il BE **non crea** un secondo job:
  restituisce l'**id di quello esistente**, senza errore
  (`fn_accoda_lavoro`, `ON CONFLICT DO NOTHING` + ritorno dell'id vivo). ⚠️ Il FE
  deve saperlo: `start()` sullo stesso `job_id` non deve raddoppiare il timer né
  contare due volte contro il tetto, e il messaggio giusto è «questo giro è già
  in corso», non «avviato»;
* insiemi **parzialmente sovrapposti** (`[A,B]` poi `[B,C]`) → **due job
  distinti**, nessuna deduplicazione, nessun rifiuto. Il gruppo B entra nel
  perimetro di entrambi. Non esiste alcun indice o lock per singolo `gruppo_key`:
  **la difesa deve stare nel frontend** (§8.4).

**(d) Nuovo: il giro mirato a zero lotti non torna «FATTO», solleva.** Se il
perimetro mirato non produce nessun lotto, il handler alza
`E_FATTURAZIONE_GIRO_NESSUN_LOTTO` (`fatturazione_giro_handler.py:126-141`) e
mette `gruppi_non_serviti` dentro `ultimo_errore.context`. Il job va in
**ERRORE**, e il ramo non-FATTO del FE (`DashboardCompetenzaView.vue:727-730`)
mostra `notify.error(ultimo_errore.message)` **scartando il context**.

⚠️ Oggi capita di rado, perché i giri sono uno per volta. Con la concorrenza è
l'esito **tipico** del secondo giro che tocca gli stessi gruppi: le righe se le
è prese il primo. Se si abilita la concorrenza senza leggere quel `context`, il
cantiere produce esattamente il silenzio che è nato per togliere — un «errore»
generico al posto di «quel gruppo l'ha fatturato l'altro giro». Per questo la
§8.0 viene **prima** di tutto il resto.

**(e) Falso: il verbo di mese non è isolato dai mirati.** Il giro di mese non
passa gruppi, quindi il suo digest è vuoto e la sua chiave **non collide** con
quella di nessun giro mirato: può partire mentre due mirati sono vivi, e il suo
perimetro **ingloba** i loro gruppi. L'esito è contesa riga per riga e un
consuntivo che l'operatore non è in grado di leggere. La §4 dice «nessun cambio
al verbo di mese»: va corretta — non cambia il *verbo*, ma va reso **mutuamente
esclusivo** con i mirati (§8.7).

### 7.3 Il tetto — proposto, poi caduto (D1)

La §3.4 proponeva «2 o 3»; l'analisi tecnica spingeva verso il basso (con un
worker sequenziale, §7.2 b, i giri ammessi sono giri **in fila**: il click in
più non anticipa nulla). **Tid ha scelto nessun tetto** (§9, D1), dopo che il
chiarimento ha separato due cose che si confondevano:

* **il tetto non limita l'aggregazione.** Quanti gruppi stanno in **una**
  selezione non ha limite di UI (il solo limite è del BE: **200 gruppi** per
  chiamata, `parse_gruppi`). Il tetto riguardava quante **selezioni distinte**
  possono essere in volo insieme — cosa che con l'aggregazione conservata (D5)
  succede di rado, perché le selezioni diventano più grosse e meno frequenti;
* **due giri diversi non aggregano mai fra loro**, qualunque sia il tetto: chi
  vuole righe sulla stessa fattura le mette nella stessa selezione.

Un tetto che non scatta quasi mai è solo un pulsante che ogni tanto si spegne
senza che nessuno capisca perché. Meglio nessuno.

⚠️ **Cosa resta a carico del piano, avendolo tolto.** I due costi che il tetto
copriva non spariscono, cambiano solo forma:

1. **chiacchiericcio di polling**: la pagina interroga il server ogni 2 secondi
   *per ogni giro seguito*, quindi il carico cresce linearmente. Mitigazione
   nel BB: allargare l'intervallo quando i giri seguiti sono molti (es. oltre 4),
   invece di rifiutare l'avvio;
2. **leggibilità di N resoconti insieme**: con nessun tetto, l'attribuzione
   per giro della §8.5 e l'indicatore di testata della §8.6 **non sono più
   rifiniture** — sono l'unica cosa che tiene in piedi la comprensibilità. Vanno
   fatti bene, non «se avanza tempo».

---

## 8. Piano esecutivo

Otto passi. L'ordine non è negoziabile nei primi due: la §8.0 chiude un buco che
la concorrenza allargherebbe, la §8.1 è l'abilitante e non cambia nulla a video.
Il §3.3 del brief resta il pezzo delicato ed è **§8.5**, provato con due giri
veri come chiede la §6.

### 8.0 — Prerequisito: l'esito che oggi si butta via

**Perché prima di tutto**: §7.2 (d). Senza questo, il secondo giro concorrente
dice «errore» invece di dire «quel gruppo l'ha già preso l'altro giro».

* nel ramo non-FATTO di `useVerboFatturazione.onDone`, leggere
  `stato.ultimo_errore?.context?.gruppi_non_serviti` e renderlo con lo **stesso**
  compositore già usato nel ramo FATTO (`fattura_gruppi_esito_non_serviti`:
  gruppi distinti, primi 3 per esteso, motivo dal BE);
* il fallback resta `ultimo_errore.message` quando il context non c'è.

**Fatto quando**: due giri sullo stesso gruppo → il secondo nomina il gruppo e
il motivo, non un errore generico.
**File**: `DashboardCompetenzaView.vue`.

### 8.1 — `useJobPolling` multi-job, a comportamento invariato

Building block condiviso, unico consumer (§7.1): si **estende in place**, non se
ne crea un secondo.

* stato interno: `Map<jobId, {timer, attempts, context, stato}>` al posto di
  `activeJobId`/`attempts`/`timer` scalari;
* `start(jobId, context) → boolean`. Rifiuta e ritorna `false` se: `jobId`
  nullo, **job già seguito** (§7.2 c — il BE restituisce lo stesso id su chiave
  viva), tetto raggiunto;
* `stop(jobId)` selettivo; `stop()` senza argomenti ferma tutto (firma
  compatibile con `onUnmounted(stop)`/`onDeactivated(stop)`, che Vue invoca
  senza argomenti);
* `polling` **resta un booleano** computed (`jobs.size > 0`) — §7.1;
* nuovi: `nJobsInCorso` (conteggio), `canStart`;
* i callback ricevono il contesto del **loro** job: `onDone(stato, context)`,
  `onTick(stato, context)`, `onTimeout(context)`;
* nuova opzione `maxConcurrent`, **default 1**. I due verbi di perimetro la
  lasciano al default; l'emissione mirata passa `Infinity` (D1, nessun tetto);
* nuova opzione `intervalMs` **scalabile**: oltre una soglia di job seguiti
  (es. 4) l'intervallo si allarga, così il polling non cresce linearmente col
  numero di giri (§7.3, punto 1). Il cap `maxAttempts` va calcolato sul tempo,
  non sul numero di tick, altrimenti allargando l'intervallo si allunga anche
  il timeout senza volerlo.

⚠️ **A tetto raggiunto `start` rifiuta, non sostituisce.** La sostituzione
(«l'ultimo giro vince») è il difetto che questo cantiere corregge, non un
comportamento da conservare a `maxConcurrent: 1`. I due verbi di perimetro non
se ne accorgono: i loro pulsanti sono già spenti durante il polling.

⚠️ `currentStato` diventa ambiguo con più job: va documentato come significativo
solo a `maxConcurrent === 1` (nessun consumer lo usa oggi).

**Fatto quando**: i due verbi di perimetro si comportano esattamente come prima.
**File**: `frontend/src/core/composables/useJobPolling.js`.

### 8.2 — Ripresa del follow-up al rientro nel tab

**Perché**: §7.1 punto 1. Oggi il polling muore in background e non riprende.

* `onDeactivated` **sospende** (ferma i timer) senza dimenticare la mappa;
  `resume()` riprende i job ancora noti;
* la view chiama `resume()` nel proprio `onActivated`, accanto al refresh già
  presente (memoria `feedback_keepalive_onactivated`: idempotente);
* ⚠️ `attempts` **non** si azzera al resume — il cap anti-infinito deve restare
  un cap, non ripartire a ogni rientro.

**Fatto quando**: avvio un giro, cambio tab, torno: lo spinner è ancora lì e
l'esito arriva.
**File**: `useJobPolling.js`, `DashboardCompetenzaView.vue`.

### 8.3 — `gruppiInCorso` per job (§3.2)

* `ref(new Map())` `jobId → gruppo_key[]`;
* computed piatta `Set` per il template: `.has(data.gruppo_key)` resta identico,
  il template non cambia;
* unione all'avvio riuscito, **sottrazione dei soli gruppi di quel job** a
  conclusione **e** a timeout (oggi entrambi azzerano tutto).

**File**: `DashboardCompetenzaView.vue`.

### 8.4 — La selezione si libera all'**avvio**, e le righe vive escono dal giro

**Perché**: §7.1 punti 2-3 e §7.2 (c). È qui che vive la difesa contro la
sovrapposizione parziale, perché il BE non ce l'ha.

* togliere `selezioneGruppi.value = []` da `buildEsitoOk` e, subito **dopo la
  POST riuscita**, rimuovere dalla selezione i soli `gruppo_key` del giro
  appena avviato;
* stringere `gruppiSelezionabili`:
  `isGruppoEmittibile(row) && !gruppiInCorso.has(row.gruppo_key)`;
* estendere il watch di prune (`:383-391`), che oggi toglie dalla selezione le
  sole righe tornate BLOCCATE, alle righe entrate in un giro vivo.

Il BB `useSelezioneToggle` **non si tocca**: il guard di `toggleRow` fa già il
resto (una riga fuori da `selezionabili` non entra in selezione qualunque cosa
faccia il template).

**Fatto quando**: avviato A, la sua checkbox si spegne e A esce dalla selezione;
B resta spuntabile.
**File**: `DashboardCompetenzaView.vue`.

### 8.5 — Esiti accumulati e attribuiti (§3.3 — il pezzo delicato)

* `lottiEmessi` **accumula**, dedup per `lotto_id`;
* ogni giro porta la propria **etichetta** nel `context` del job: i riferimenti
  leggibili troncati (`elencoTroncato(righe, gruppoRiferimento)`), calcolati
  all'avvio quando le righe sono ancora a video — è l'identità del giro, e non
  richiede una tabella di corrispondenza che l'operatore dovrebbe consultare;
* le chiavi i18n dell'esito mirato (`fattura_gruppi_esito`, `_parziale`,
  `_non_serviti`, `_altrove`, `_vuoto`) prendono un parametro `{giro}`, in
  `it.json` **e** `en.json`, con `python3 scripts/check_i18n_keys.py` verde;
* `reloadDopoAzione()` **resta**: le marcature sopravvivono al reload (§7.1) e
  non ricaricare mostrerebbe righe già consumate. L'effetto «pagine che
  scorrono» si copre con l'indicatore di testata della §8.6.

⚠️ **Punto scoperto, da decidere (§9, D4)**: `azzeraStatoGruppi()` svuota
`lottiEmessi` al cambio mese, mentre un giro vivo può concludersi **dopo**. Oggi
il difetto esiste già (i lotti di un mese finiscono sotto un altro mese); la
concorrenza lo rende più probabile. Il rimedio pulito è legare `lottiEmessi` al
mese di competenza del giro e mostrare solo quelli del mese a video.

**Fatto quando**: due giri conclusi mostrano **due** esiti, ciascuno con i
propri lotti e i propri non-serviti, e si capisce di quale giro sono.
**File**: `DashboardCompetenzaView.vue`, `locales/it.json`, `locales/en.json`.

### 8.6 — Il verbo sempre premibile, e l'indicatore che lo rende leggibile

Con D1 (nessun tetto) questo passo non aggiunge un divieto: **toglie** quello
che c'è e mette al suo posto l'informazione. È la contropartita della scelta —
senza indicatore, «nessun tetto» diventa «nessuno sa quanti giri stia
aspettando».

* spariscono `giroMirataInCorso` dal `:disabled` e dal `:loading` del pulsante
  «Fattura selezionati» e dal `disabled` del kebab «Fattura questo»: con un giro
  vivo il verbo resta **premibile**;
* ⚠️ il `:loading` resta legato al solo `azioneLoading` (la POST). Un pulsante in
  caricamento che però si può premere è una contraddizione a video;
* `tooltipFatturaSelezionati` **perde** il caso «giro in corso» e resta a due
  (nessuna selezione / n selezionati). La chiave
  `fattura_selezionati_in_corso_tooltip` e
  `gruppo_attesa_altro_giro_tooltip` vanno **rimosse** da `it.json`/`en.json`:
  descrivono un blocco che non esiste più, e una chiave orfana è una frase che
  prima o poi ricompare;
* resta il tooltip della riga **in lavorazione** (`gruppo_in_corso_tooltip`):
  quello descrive lo stato della riga, non un divieto di contesto;
* **indicatore di testata** accanto al pulsante: «N fatturazioni in corso»,
  indipendente dalla pagina a video (§7.1) e dal numero di righe marcate. Con
  nessun tetto è l'**unica** cosa che dice all'operatore quanto ha in volo.
  Riusa `.app-dash-lotti-emessi` come stile della riga informativa, o una classe
  gemella in `main.css` — nessun CSS scoped, nessun colore hardcodato
  (`--app-in-corso-color` esiste già).

**Fatto quando**: con due giri vivi il pulsante è premibile, e la testata dice
«2 fatturazioni in corso».
**File**: `DashboardCompetenzaView.vue`, `main.css`, `locales/it.json`,
`locales/en.json`.

### 8.7 — Mutua esclusione col verbo di **mese**

**Perché**: §7.2 (e). Fuori dal perimetro dichiarato dalla §4, ma senza questo
il cantiere **aumenta** il rumore invece di ridurlo: un giro di mese avviato
mentre due mirati sono vivi si contende le loro righe e produce un consuntivo
illeggibile.

* «Fattura mese» spento, **col motivo**, finché c'è almeno un giro mirato vivo;
* «Fattura selezionati» / «Fattura questo» spenti, **col motivo**, mentre il giro
  di mese è vivo;
* «Rendi definitive» resta indipendente: numera lotti già emessi, non contende
  attività.

Costo: due predicati e due chiavi i18n.

**File**: `DashboardCompetenzaView.vue`, `locales/it.json`, `locales/en.json`.

### 8.8 — Documentazione

* aggiornare la riga di `useJobPolling` nel
  [catalogo building block frontend](../frontend/catalogo-building-block-frontend.md)
  — oggi dice «Polling di **UN** job asincrono»;
* a validazione in-app fatta, il brief passa in `work-done/`.

### 8.9 — Definizione di «fatto», estesa

Ai cinque criteri della §5 si aggiungono:

* [ ] il secondo giro che tocca gruppi già presi dal primo **nomina il gruppo e
      il motivo**, non un «errore» generico (§8.0);
* [ ] ripremendo «Fattura» sulla **stessa identica** selezione ancora viva, la UI
      dice «giro già in corso» e **non** conta due giri (§7.2 c);
* [ ] una riga in lavorazione **non è più spuntabile** (§8.4);
* [ ] cambiando tab e rientrando, i giri vivi sono ancora seguiti (§8.2);
* [ ] «Fattura mese» e i giri mirati non possono coesistere, e chi è spento dice
      perché (§8.7);
* [ ] con giri vivi il verbo mirato resta **premibile** e la testata dice quanti
      ne sono in corso (§8.6, D1);
* [ ] nessuna chiave i18n orfana: le due frasi del blocco globale sono rimosse
      (§8.6), `python3 scripts/check_i18n_keys.py` verde, parità it/en.

⚠️ Il criterio 4 della §5 («raggiunto il tetto, il verbo si spegne col motivo»)
**decade** con D1: non c'è più un tetto da raggiungere.

### 8.10 — Come si prova (due giri veri, §6)

Senza un secondo worker i job sono sequenziali (§7.2 b): due giri **coesistono**
come follow-up ma il secondo *esegue* dopo. Basta e avanza per esercitare tutto
il piano — anzi, è lo scenario reale.

1. selezionare A, «Fattura selezionati» → spinner su A, A esce dalla selezione;
2. **senza aspettare**, selezionare B e premere → due spinner, testata «2
   fatturazioni in corso», il verbo **ancora premibile** (D1);
3. attendere: due esiti distinti, attribuiti, lotti accumulati;
4. ripetere con B **incluso in entrambi** i giri → il secondo deve dire «già
   fatturato dall'altro giro», non «errore» (§8.0);
5. ripremere la **stessa** selezione ancora viva → «giro già in corso»;
6. cambiare tab a metà giro e rientrare → follow-up ancora vivo.

---

### 8.11 — Fuori piano: l'ordine di esecuzione della coda (trovato in validazione)

Prima prova in app di Tid, 2026-08-17: due giri lanciati a pochi secondi l'uno
dall'altro sono stati eseguiti **al contrario** — il lotto del secondo ha preso
il codice più basso (`LTF-0004019` contro `LTF-0004020`).

**Causa**, in `apps/core/services/coda_lavori/repository.py`: l'`ORDER BY
priorita, id` della CTE di claim decide **quali** item entrano nel batch, non in
che ordine si eseguono. Le righe tornano da un `UPDATE ... RETURNING`, di cui
PostgreSQL non specifica l'ordine (e c'è pure un join al registry, che il
planner materializza come vuole); il drain cicla la lista così com'è.
L'intenzione FIFO era dichiarata e persa una riga dopo.

**Perché non è estetica.** Il codice del lotto conta poco, e la numerazione non
è toccata (`list_lotti_numerabili` ordina per `fl.id`: deterministica e senza
buchi). Ma con **due giri che si contendono le stesse righe** è l'ordine di
esecuzione a decidere chi vince: eseguendo per primo il giro lanciato per
secondo, era il **primo** a tornare con «già fatturato altrove». Nel contesto
della concorrenza appena aperta, è il contrario di ciò che l'operatore si aspetta.

**Fatto**: `c.priorita` nel `RETURNING` e riordino esplicito per `(priorita, id)`
prima del ciclo — stessa chiave della CTE. Più due test di regressione
(`test_coda_lavori_repository.py` 5-6): il driver restituisce righe sparse, la
lista esce ordinata. Suite Django verde (3678).

⚠️ Tocca **tutti** i tipi di job, non solo la fatturazione: l'ordine di
esecuzione della coda è ora deterministico ovunque. Il worker è un `oneshot` su
timer, quindi prende il codice nuovo alla passata successiva senza riavvii.

---

### 8.12 — Esito della validazione in-app (Tid, 2026-08-17)

**Confermato con due giri veri**: i due giri convivono, l'ordine di esecuzione è
quello di lancio (dopo §8.11) e — il punto delicato — **gli esiti sono attribuiti
al giro giusto**, con i riferimenti dei documenti effettivamente selezionati. È
la parte in cui un errore non si vede, e l'unico modo di verificarla era questo.

**Fuori piano, trovato nella stessa sessione**: `RowActionsMenu` **ignorava** il
campo `action` (codename permesso). `useLottoAzioni` lo passava già sui verbi di
governo del lotto, quindi il cancello era scritto e inesistente: un operatore
senza `reset_lotto_draft` vedeva «Riporta in lavorazione» nel kebab della lista
lotti. Corretto nel BB (stesso predicato di `useActionBar`: un solo meccanismo
per le tre barre) e documentato in `frontend-standards.md` §Formato azione, dove
`action` non era nemmeno menzionato. Unico consumer colpito: `useLottoAzioni`
(l'altro caso con `action:` è una `DrawerActionsBar`, già gated).

**Non ancora esercitato** — e per un motivo che vale registrare:

* [ ] §8.0, il secondo giro che trova le righe già prese. ⚠️ La §8.4 lo rende
      **difficile da riprodurre da soli**: le righe di un giro vivo non sono più
      spuntabili, quindi da una sola sessione non si compone più un perimetro
      sovrapposto. Resta raggiungibile da: due operatori in sessioni diverse, il
      cron `run_fatturazione_batch` (canale separato, nessun lock condiviso col
      giro da UI), o righe consumate altrove fra selezione ed esecuzione. Il
      ramo serve: è il caso in cui il BE **solleva** e il motivo sta nel
      `context`.
* [ ] ripremere la **stessa identica** selezione ancora viva → «già in corso»
      (anch'esso ostacolato dalla §8.4, per la stessa ragione);
* [x] cambio tab a metà giro e rientro → follow-up ancora vivo (§8.2).
      **Provato da Tid il 2026-08-17: ok.** Era il caso in cui il difetto è
      invisibile — prima il polling si spegneva e non ripartiva, il job finiva
      lato server e il suo esito non arrivava mai.
* [ ] «Fattura mese» spento col motivo mentre un giro mirato è vivo, e viceversa
      (§8.7).

Il terzo è stato provato (ok). Resta da provare il quarto, che vale un minuto;
i primi due richiedono una seconda sessione o il cron.

---

## 9. Decisioni prese (Tid, 2026-08-17)

| # | Decisione | Esito | Dove impatta |
| --- | --- | --- | --- |
| **D1** | Tetto giri concorrenti | **NESSUN TETTO** (la proposta era 2) | §7.3, §8.1, §8.6 — e §5 perde il suo quarto criterio |
| **D2** | Ripresa del follow-up al rientro nel tab | **SÌ** | §8.2 |
| **D3** | Mutua esclusione col verbo di mese | **SÌ** | §8.7 |
| **D4** | `lottiEmessi` legati al mese di competenza | **SÌ**, stesso giro di lavoro | §8.5 |
| **D5** | Grana del job: per gruppo o per selezione | **UN JOB PER L'INTERA SELEZIONE**, come oggi | nessuna modifica al piano — vedi sotto |

### D5 — perché «un job per ogni gruppo» è stato scartato

Proposta di Tid in corso di analisi, poi ritirata da lui stesso una volta
emersa la conseguenza. Vale la pena lasciarla scritta, perché è la domanda che
tornerà.

Le attività finiscono sulla **stessa fattura** in base a una chiave del DB
(`vendite.fn_build_fattura_key`: cliente di fatturazione — con risalita al
`parent_account_id` —, tipo doc fiscale, valuta, utility, emittente, reseller,
registro, termini e modalità di pagamento). Ma quel raggruppamento avviene
**dentro un lotto**, e **ogni giro crea un lotto nuovo**
(`fn_get_or_create_lotto`, CASO 3: il driver non passa `lock_batch_id`).

Quindi: **fra giri diversi non si aggrega mai.** «Un job per gruppo» avrebbe
significato un lotto per gruppo e, di conseguenza, tre fatture invece di una per
il cliente con tre documenti nello stesso mese — un cambio nei **documenti
emessi**, non nell'interfaccia. Scartato: l'aggregazione per cliente si
conserva.

⚠️ **Corollario operativo, e da qui nasce il cantiere collegato (§10)**: se per
avere righe sulla stessa fattura devono stare nella **stessa selezione**, allora
comporre quella selezione dev'essere facile. Oggi non lo è: manca il filtro per
cliente, e il «seleziona tutti» opera sulla sola pagina corrente.

### Nota di merito, che resta agli atti

La §6 sconsigliava di aprire il cantiere finché la selezione multipla basta, e
la §7.2 (b) rende il beneficio più stretto di quanto la §2 già dicesse (i giri
si **accodano**, non corrono insieme). Tid ha deciso di partire: la nota resta
come misura del beneficio atteso, non come obiezione.

---

## 10. Cantiere collegato — comporre la selezione (filtro cliente, colonne, ricerca)

> ⛔ **QUESTA SEZIONE NON È CHIUSA.** Il resto del documento è archiviato in
> `work-done` perché realizzato e validato; questo paragrafo è l'unica parte
> ancora **aperta**, e vive nel brief al team DB
> `brief-db-dash-competenza-gruppi-cliente-e-ricerca*.md`
> (`work-in-progress`, in attesa del DB). Resta qui perché contiene il dettaglio
> **lato FE** che servirà a valle: il brief DB dice cosa serve al DB, questo dice
> come si comporterà la schermata. Chi riapre il cantiere parte dal brief DB e
> torna qui per il seguito.

Nato dalla D5 (2026-08-17): conservata l'aggregazione, il gesto operativo utile
diventa *«filtro il cliente → seleziono tutto → fatturo»* = una fattura sola per
quel cliente. Oggi quel gesto non esiste.

**Non appartiene a questo brief** e non va infilato qui: è per la maggior parte
lavoro **DB**, e mescolarlo metterebbe la parte delicata di questo piano (la
contabilità degli esiti, §8.5) in attesa dietro una coda di migrazioni. Va
aperto come brief a sé, che comincia con il passaggio al team DB su `dev/db-tid`.

Perimetro, in ordine di dipendenza:

1. **DB — le colonne non esistono.** `vw_dash_competenza_gruppi` espone
   `cliente_display` e basta: **niente** billing account, codice o id fiscale.
   Vanno aggiunte a monte in `vw_dash_competenza_attivita` e portate su nella
   vista dei gruppi (con l'accortezza sul `GROUP BY`), più il seed delle colonne
   della lista `vendite.dash_competenza_gruppi`.
2. **DB/BE — filtro e ricerca**: parametro cliente (id, non testo) e `search`
   secondo la policy ricerca e paginazione (min 3 caratteri, server-side,
   indici).
3. **FE** — controlli e comportamento:
   * **filtro cliente = lookup strutturato** (BB lookup billing account), non
     testo libero: serve a «fatturami tutto di Rossi»;
   * **ricerca libera** su riferimento documento, codice commessa e id fiscale:
     serve a «dov'è finito ORD0005174». Due controlli con ruoli distinti, non
     due modi di fare la stessa cosa;
   * le due colonne nuove a catalogo **non accese di default** (la lista è già
     larga; chi ne ha bisogno le accende, il ritiro dinamico fa il resto);
   * ⚠️ **ogni cambio di filtro o ricerca azzera la selezione**, come già fa il
     filtro tipo (`onGruppiTipoChange`): fatturare righe non a video è
     esattamente l'incidente che quel codice previene;
   * ⚠️ **serve un «seleziona tutti i risultati del filtro»**, altrimenti metà
     del beneficio si perde a spuntare pagina per pagina. Con un limite: il BE
     accetta **200 gruppi** per chiamata (`parse_gruppi`) — sopra la soglia va
     detto, mai troncato in silenzio.

---

## 11. Riferimenti verificati

### 11.1 Frontend

| Cosa | Dove |
| --- | --- |
| Polling a job singolo, `stop()` totale, cleanup su deactivate | `frontend/src/core/composables/useJobPolling.js:67,70-77,115-129` |
| Unico consumer, tre istanze | `frontend/src/vendite/views/DashboardCompetenzaView.vue:41,722,771,793,821` |
| `gruppiInCorso` azzerato per intero | `DashboardCompetenzaView.vue:720,736,741` |
| `buildEsitoOk` sovrascrive lotti e selezione | `DashboardCompetenzaView.vue:830-833` |
| Ramo non-FATTO che scarta il context | `DashboardCompetenzaView.vue:727-730` |
| `gruppiSelezionabili` (solo emittibilità) e watch di prune | `DashboardCompetenzaView.vue:356,383-391` |
| Selezione multipla → un solo job | `DashboardCompetenzaView.vue:903-914`, `vendite/api/lotti.js:116-124` |
| BB selezione (non si tocca) | `vendite/_shared/righe/useSelezioneToggle.js:40-45` |
| Chiave idempotenza HTTP rigenerata a ogni POST | `core/utils/idempotency.js:9-14` |

### 11.2 Backend / DB

| Cosa | Dove |
| --- | --- |
| Chiave idempotenza business `job_type:competenza:scope[:digest]` | `apps/vendite/api/views.py:1474-1476` |
| Digest sha256 dell'insieme ordinato+dedup | `apps/vendite/services/_fatturazione_job_helpers.py:72-113,356-360` |
| Unique parziale sui soli stati vivi | `00_schema/dbops/20260720-08-create-coda-lavori-mctit.yaml:123-126` |
| Chiave viva → ritorna l'id esistente, non errore | `20_code/dbops/20260720-09-create-fn-accoda-lavoro-mctit.yaml:130-146` |
| Nessun `lock_key` sul drain della coda | `apps/core/management/commands/draina_coda_lavori.py:11-16,55` |
| Ciclo **sequenziale** sui job claimati | `apps/core/services/coda_lavori/drain_engine.py:105-120` |
| Worker oneshot su timer al minuto | `backend/deploy/systemd/zeroerp-coda-lavori.service`, `backend/bin/install-timers.sh:94,114` |
| Presa attività con `SKIP LOCKED` + re-check (no doppia fattura) | `docs/it/dbzero/vendite/funzioni/fn_select_attivita_fatturabili.md`, `apps/vendite/db/pipeline_repository.py:1143-1197` |
| Zero lotti sul mirato → solleva, non-serviti nel `context` | `apps/vendite/services/fatturazione_giro_handler.py:126-141` |
| Consuntivo `gruppi_non_serviti` / `_fatturati_altrove` | `fatturazione_giro_handler.py:181-230`, `fn_esito_gruppi_giro` |
| Chiave di aggregazione della fattura (D5) | `docs/it/dbzero/vendite/funzioni/fn_build_fattura_key.md` |
| Ogni giro crea un lotto nuovo (D5) | `docs/it/dbzero/vendite/funzioni/fn_get_or_create_lotto.md` (CASO 3) |
| La vista gruppi non ha BA / codice / id fiscale (§10) | `docs/it/dbzero/vendite/views/vw_dash_competenza_gruppi.md` |
