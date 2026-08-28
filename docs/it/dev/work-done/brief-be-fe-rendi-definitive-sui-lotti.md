# Brief BE/FE — «Rendi definitive» torna dove stanno i lotti

> **Destinatario:** me stesso (BE/FE). ⚠️ Il «prerequisito DB» annunciato al §4
> **non esisteva**: `SQL_PERIMETRO_LOTTI_NUMERABILI` è una costante **Python**,
> non una funzione del database. Il cantiere è stato interamente BE/FE — zero
> migrazioni, zero attese.
>
> **Origine.** Tid, 2026-08-26. La domanda di partenza era sulla semantica delle
> card della Lente 1; da lì è emersa una contraddizione che Tid ha visto per
> primo e ha risolto lui:
>
> *«Il discorso rendi definitive […] riapre però il discorso che la lista deve
> rimanere perché altrimenti non so cosa rendo definitiva. Allora a questo punto
> è sui lotti che deve nascere un pulsante che rende definitivi tutti i lotti
> insieme. Lasciare una azione che si fa in 2 posti è controintuitivo.»*
>
> e, subito dopo, la forma finale:
>
> *«E se il pulsante rendi definitive funzionasse sullo stile di fatture
> selezionate presente nella card da emettere? A quel punto basterebbe
> selezionare le righe dalla lista lotti e uno è libero di fare quello che
> vuole.»*
>
> **Correlati:**
> [brief-db-numerazione-data-documento-e-sequenza.md](brief-db-numerazione-data-documento-e-sequenza.md)
> (la data dichiarata e il cancello di sequenza — questo brief ne è il seguito
> naturale) ·
> [brief-db-lavoro-che-non-torna-indietro.md](brief-db-lavoro-che-non-torna-indietro.md)
>
> ✅ **Stato al 2026-08-28: CHIUSO.**
> Backend e frontend sono scritti, verificati e in albero; l'interfaccia è stata
> vista in-app da Tid («ora la grafica funziona», «da fatturate il link porta
> correttamente ai lotti»), e il **collaudo dei verbi è stato eseguito per
> intero**: sedici prove verdi, numeri veri consumati e riletti sui lotti.
>
> | | Cosa mancava | Come si è chiusa |
> | --- | --- | --- |
> | ✅ **C-1** | il collaudo dei **verbi**: numerare una selezione, numerare il mese, il limite che si sposta fra sezionali diversi | **Chiuso il 2026-08-28 da Tid**: verbale in [collaudo-in-app-rendi-definitive-sui-lotti.md](collaudo-in-app-rendi-definitive-sui-lotti.md) — 16 prove, tutte verdi, **quattro difetti** trovati e corretti (R-1 → R-4) |
> | ✅ **C-2** | la **guida**, che descriveva ancora «Rendi definitive» sulla card `Fatturate` | **Trasferita e FATTA** il 2026-08-28 dal cantiere gemello [brief-be-fe-lavoro-che-non-torna-indietro.md](../work-in-progress/brief-be-fe-lavoro-che-non-torna-indietro.md) (§12.3), che possiede la stessa §7.1: riscritta da **una mano sola**. ⚠️ Due riferimenti di questa consegna erano sbagliati e sono corretti là: il passo **L5** era **già fatto** (è un lotto del brief DB, chiuso il 2026-08-27), e la guida **non ha un §6.3** — quel numero è una sezione di *questo* brief, e il punto da correggere era la **§7.5** |
>
> ⭐ **C-2 non è stata dichiarata fatta né lasciata cadere con l'archiviazione**:
> è stata **spostata dove sta la mano che la esegue**. La §9.1 vietava di
> riscrivere la §7.1 in parallelo da due cantieri; archiviare questo brief
> lasciandola qui l'avrebbe resa invisibile proprio a chi deve farla.
>
> ⚠️ C-1 non era una formalità: è un **atto fiscale**, e fino al 2026-08-27 ne
> era stato provato il percorso (endpoint, coda, perimetro, guard) ma non
> l'**esito** — nessun numero era stato consumato in collaudo. Ora sì, ed è
> quello che ha chiuso il cantiere.
>
> ⛔ **E il primo click vero, il 2026-08-27, ha trovato subito un difetto**: il
> verbo su **selezione** non aveva mai funzionato. Il frontend mandava
> `?lotti[]=12` (serializzazione di default di axios per gli array, provata sulla
> 1.20 in `package.json`), il backend legge `getlist('lotti')` — chiave senza
> parentesi — e non trovava niente; `_query_lotti_ids` traduce la lista vuota in
> `None`, quindi il servizio riceveva **tutti e tre** i perimetri nulli e
> rispondeva `E_VALIDATION_INPUT` su una richiesta in cui uno c'era. A video:
> «La finestra di numerazione non è stata letta». Corretto in `api/lotti.js` con
> `paramsSerializer: { indexes: null }`.
>
> ⭐ **Il verbo per-riga non era toccato** — manda un id **scalare** — ed è il
> motivo per cui «prima funzionava»: quello che non aveva mai funzionato è il
> perimetro nuovo, cioè proprio ciò che C-1 deve provare.
>
> ⚠️ **Accanto a quella riga c'era un commento che affermava il contrario**
> (*«axios serializza un array così di default»*). Era falso, e ha fatto passare
> la riga per una cosa già verificata. Questa classe di difetti — il frontend
> serializza in un modo, il backend legge in un altro — **non la prende nessun
> test**: non c'è un runner FE e i test Django mockano la request. Si vede solo
> con una chiamata vera.
>
> ⛔ C-2 era bloccata da un ordine, non da un dubbio: la stessa tabella dei verbi
> viene riscritta anche dal cantiere gemello, e fare i due passi in parallelo
> significa che una delle due mani perde il lavoro dell'altra. Per questo, alla
> chiusura, è passata **al gemello** invece di restare qui.

---

## 1. La contraddizione che si chiude

Oggi l'atto fiscale di massa vive sulla card `Fatturate` della Lente 1. Il
problema non è dove sta il pulsante: è che **accanto non c'è l'elenco di ciò su
cui agisce**.

| | |
| --- | --- |
| il pulsante numera | **lotti** |
| la lista sotto elenca | **commesse** |
| il codice del lotto nella lista | **non c'è** (verificato: `ui.lista_colonna` per `vendite.dash_competenza_commesse` non ha né lotto né fattura) |

Tenere il pulsante lì costringe a tenere una lista che non nomina il suo
oggetto. Toglierlo e basta lascia l'operatore senza il verbo di massa. **La via
d'uscita è spostare il verbo dove l'elenco esiste già**: la lista Lotti.

---

## 2. Le decisioni

| # | Decisione | Chi |
| --- | --- | --- |
| **D-1** | «Rendi definitive» **esce** dalla Lente 1 e **nasce sulla lista Lotti** | Tid |
| **D-2** | Sulla card `Fatturate` resta il **rimando** ai lotti (filtrato su competenza + stato emessa) | Tid |
| **D-3** | Il **drill-down per commessa** della card `Fatturate` sparisce | Tid |
| **D-4** | Il perimetro è la **selezione di righe**, sullo stile dell'emissione mirata | Tid |
| **D-5** | Resta **anche** il verbo di massa «tutti i lotti emessi del mese» | mia proposta, §3 |

⭐ **D-5 non contraddice il «controintuitivo» di Tid.** La sua obiezione era la
stessa azione in **due posti**; qui i due verbi vivono **nello stesso posto**,
esattamente come su `Da emettere` convivono «Fattura adesso» (il mese) e
«Fattura questo» (la selezione). È la simmetria del precedente, non una deroga.

---

## 3. Perché il verbo di massa resta

La lista Lotti è **paginata**. Il «seleziona tutto» dell'intestazione opera —
correttamente, ed è già così sull'emissione mirata — **solo sulla pagina
corrente**: il BB `useSelezioneToggle` è nato per liste intere e il suo
`toggleAll` *sostituisce* la selezione, quindi la Lente 1 lo usa solo per riga e
si è scritta un seleziona-tutto di pagina che **aggiunge** senza buttare via le
pagine precedenti.

Conseguenza pratica: un mese con 120 lotti richiederebbe di spuntare pagina per
pagina. Il verbo di massa esiste per non far pagare quel prezzo a chi vuole
semplicemente chiudere il mese.

---

## 4. Il pezzo DB/BE: il perimetro diventa due forme

Oggi il perimetro dell'atto è **una sola forma**, scritta in un punto solo:

```python
# backend/apps/vendite/db/_data_documento_sql.py
SQL_PERIMETRO_LOTTI_NUMERABILI = """
    {lotti}.competenza_mese = %s
    AND {lotti}.stato_doc_fiscale_id = %s
"""
```

ed è consumata da **tre** punti, che devono restare allineati:

| Punto | Cosa fa | Se diverge |
| --- | --- | --- |
| `VenditeRepository.list_lotti_numerabili` | l'elenco che il job percorre | si numera altro |
| `PipelineRepository.get_data_documento_corrente` | la data che il dialog **propone** | si propone la data di un lotto non toccato |
| `PipelineRepository.get_data_minima_numerabile_competenza` | il **limite** che il dialog mostra | limite più alto del necessario, o più basso: il DB rifiuta dopo |

⭐ **È il motivo per cui il frammento era stato estratto**, ed è la prova che
serviva: la seconda forma si aggiunge in un posto e i tre usi la seguono
insieme. ⚠️ Ma [[feedback_bb_legge_non_trasporta]] vale in pieno — **il BB
unifica la lettura, non il trasporto**. Il trasporto è il vero lavoro (§5).

**Forma nuova**: perimetro per **lista di id**, con lo stato emessa comunque
applicato (un lotto non emesso non si numera nemmeno se spuntato).

⚠️ **Guard obbligatorio, esattamente uno dei due perimetri.** È già la regola di
`get_data_documento_corrente`, che sul punto ha un commento esplicito: senza
guard, una chiamata senza argomenti cade nel ramo competenza con `NULL`, non
trova nulla e risponde «niente da numerare» — *«un errore di chiamante non deve
poter uscire come un dato»*. La forma a lista raddoppia quel rischio.

---

## 5. Il trasporto: cinque passaggi, ed è qui che si perde

Gli id selezionati devono attraversare tutta la catena. Ogni anello va toccato,
e **nessuno di questi fallisce rumorosamente se dimenticato** — semplicemente si
numera il mese intero invece della selezione.

| # | Anello | Cosa cambia |
| --- | --- | --- |
| 1 | `LottiListView` (FE) | la selezione e il payload del verbo |
| 2 | `ApiFatturazioneNumera` (`POST /vendite/fatturazione/numera/`) | il body accetta `lotti: [id]` accanto a `competenza_mese` |
| 3 | `_accoda_job_fatturazione` → `dbops.coda_lavori.payload` | la lista entra nel JSON del job |
| 4 | `fatturazione_numera_handler` | legge `lotti` dal payload e lo passa al repository |
| 5 | `VenditeRepository.list_lotti_numerabili` | il ramo id del perimetro |

più il ramo parallelo del dialog: `ApiFatturazioneFinestraNumerazione`
(`GET /vendite/fatturazione/finestra-numerazione/`) deve accettare la stessa
lista, o **il limite mostrato sarà quello del mese e non quello della
selezione**.

### 5.1 ⛔ La trappola della coda: la dedup mangerebbe la seconda selezione

La chiave di **business** della coda per `FATTURAZIONE_NUMERA` è
`(job_type, competenza, scope operatore)` e deduplica i job **vivi**. Con la
selezione, **due selezioni diverse sullo stesso mese diventerebbero un
doppione**: il secondo job viene assorbito, l'operatore legge «accodato» e non
succede niente.

⭐ **Il precedente l'ha già risolto, e la soluzione è a portata**: l'emissione
mirata ha `gruppi_digest()` — digest stabile dell'insieme, ordinato prima
dell'hash (stesso insieme in ordine diverso = stesso lavoro, e va deduplicato
davvero), stringa vuota senza selezione **così la chiave del giro di massa resta
identica a prima**. Il commento di quella funzione la chiama *«il difetto più
insidioso della slice»*.

→ **Seconda occorrenza**: `gruppi_digest` va generalizzata a digest di un
insieme di chiavi ([[feedback_regola_del_2_estrai_bb]]). Da dichiarare a Tid
prima di farlo.

⚠️ E va deciso **esplicitamente** se `data_documento` entra nella chiave: oggi
**non** ci entra, di proposito (*«la dedup difende l'atto fiscale, non il
parametro»*). Con la selezione la scelta resta la stessa, ma va riletta.

---

## 6. Il lavoro FE

### 6.1 Sulla lista Lotti

Da riusare **tale e quale** dal precedente della Lente 1 (`gruppi`), che ha già
pagato i due errori tipici:

- la selezione **sopravvive al cambio pagina** (chiave di dominio, non indice di
  riga);
- un `watch` **toglie la spunta** alle righe che smettono di essere
  selezionabili sotto i piedi. Senza, la riga resta spuntata con la casella
  disabilitata — non rimovibile, contata nel pulsante, e ri-sottomessa a ogni
  giro.

Qui i due motivi di non-selezionabilità sono: **stato ≠ emessa** e **lotto già
dentro un giro di numerazione vivo**.

⚠️ Lo slot della selezione in `<ListaConfigurabile>` è `#selection` (con il
gemello `#selection-header`), non una colonna di catalogo.

**Conferma onesta**: «5 selezionati, **4 numerabili**» quando i due numeri
divergono. Mai un conteggio che tace ciò che è stato scartato.

### 6.2 La data

Il dialog `NumerazioneDataDialog` esiste già ed è nella forma giusta (modo
numerazione, con il limite del sezionale). Due cose da cambiare:

1. il limite va **ricalcolato mentre la selezione cambia**, non una volta
   all'apertura;
2. ⚠️ **il limite è di ogni sezionale, la data è una sola.** Selezionando lotti
   di registri diversi, una data può essere buona per uno e rifiutata
   dall'altro. Il calcolo attuale prende già il **massimo** dei limiti del
   perimetro (`max(fn_get_data_minima_numerabile_lotto)`), quindi la data
   proposta è sicura per tutti — ma se quel massimo è molto più alto del resto,
   l'operatore va avvisato del **perché**, non solo del cosa. Da valutare se il
   dialog debba nominare il registro che alza il limite.

### 6.3 Sulla Lente 1

- via il pulsante «Rendi definitive» dalla card `Fatturate`;
- via il drill-down per commessa di quella card;
- al loro posto un rimando ai Lotti **che porta il filtro** (competenza + stato
  emessa). Un rimando all'elenco nudo sarebbe un passo indietro.

⚠️ Restano da ripulire, se orfane: `nDaNumerare`, `dialogNumeraMese`,
`confermaNumeraMese`, il verbo `onRendiDefinitive` e le chiavi i18n
`numera_mese*`. Il conteggio `nDaNumerare` **serve ancora** se la card continua
a mostrare quante fatture sono da numerare — decisione aperta.

---

## 7. Il residuo di verità da correggere nella documentazione

La guida [cruscotti-fatturazione.md](/guide/cruscotti-fatturazione) è stata
aggiornata il 2026-08-26 con la card **giusta** per «Rendi definitive»
(`Fatturate`). Quando questo brief viene realizzato, quella riga **cambia
ancora**: il verbo non sta più sulla Lente 1. Da non dimenticare — sarebbe la
terza volta che quella riga dice una cosa falsa.

Stessa cosa per `api_dashboard_competenza.md`, dove il verbo è ora descritto
sulla card `FATTURATA`.

---

## 8. Ordine di lavoro proposto

1. **DB/BE** — seconda forma del perimetro + guard «esattamente uno», con i tre
   consumatori allineati insieme.
2. **BE** — trasporto (§5) + digest della selezione nella chiave di coda (§5.1),
   con il presidio che due selezioni diverse sullo stesso mese producano **due**
   job.
3. **FE** — selezione sulla lista Lotti + i due verbi + il dialog che ricalcola.
4. **FE** — smontaggio sulla Lente 1 (§6.3) e rimando filtrato.
5. **Doc** — §7.

⚠️ I passi 3 e 4 vanno **nello stesso giro**: fra l'uno e l'altro l'atto di
massa non esisterebbe da nessuna parte.

---

## 9. Collegamenti con `brief-db-lavoro-che-non-torna-indietro.md`

> Aggiunto il 2026-08-26 dopo l'analisi critica dell'altro brief (che li tratta
> in dettaglio nel suo **§11**). Qui solo ciò che **cambia il lavoro di questo
> cantiere**.

### 9.1 ⛔ La §7.6 della guida è contesa fra i due cantieri

Il §7 di questo brief avverte che la realizzazione sarebbe **la terza volta** che
la riga di «Rendi definitive» in `cruscotti-fatturazione.md` cambia. L'altro
cantiere ne mette **due** sullo stesso file, e vengono prima:

| Ordine | Cantiere | Sezione | Cosa |
| --- | --- | --- | --- |
| 1 | DB, lotto L1 | §7.6 | via l'avvertenza 🔴 su «Elimina dal lotto» |
| 2 | DB, lotto L5 | §3.1 + §7.1 | la card `Emesse non fatturate` prende un verbo |
| 3 | **questo** | §7.1 + §6.3 | «Rendi definitive» lascia la Lente 1 |

⚠️ La tabella dei verbi della §7.1 viene toccata da **entrambi** i passi 2 e 3.
Farli in parallelo significa riscriverla due volte da due mani, e una delle due
perde. Il passo 3 va **dopo** il 2, o va fatto sapendo cosa il 2 ha scritto.

### 9.2 ⭐ Il principio che tiene insieme le due direzioni

Sembrano opposte — questo cantiere **toglie** un verbo dalla Lente 1, l'altro ce
ne **mette** uno — e non lo sono. La regola è una sola:

> **Un verbo sta dove sta l'elenco del suo oggetto.**

«Rendi definitive» agisce su **lotti** e viveva accanto a un elenco di
**commesse**: se ne va perché l'elenco giusto sta altrove (§1). «Riporta da
emettere» agisce su **attività residue**, e la card `Emesse non fatturate` è
l'unico posto dove quell'elenco esiste — nessuna lista di lotti le mostra,
perché il loro lotto non c'è più.

⭐ E la simmetria vale la pena di essere notata: `Emesse non fatturate` è la card
su cui «Rendi definitive» stava **per errore** fino ad agosto 2026 (§7.1 della
guida lo dichiara). Dopo i due cantieri quella card ospiterà **un solo verbo, e
quello giusto**.

### 9.3 La stessa forma, un livello più giù — ma **non** la stessa coda

La D-4 di questo brief (perimetro = selezione di righe) e la Q-1 dell'altro
(perimetro del verbo di recupero) chiedono la stessa cosa: `bigint[]` in
ingresso, con guard esplicito su lista vuota — *«un errore di chiamante non deve
poter uscire come un dato»* vale identico da entrambe le parti.

⚠️ **Ciò che invece non si eredita è la coda.** «Rendi definitive» passa da
`dbops.coda_lavori` e ha il problema di dedup del §5.1 (`gruppi_digest`).
«Riporta da emettere» è **sincrono**: due scritture, una transazione, nessun job.
Da non accodare per simmetria.

⭐ Le due estrazioni «regola del 2» sono **distinte** e non si toccano:
`gruppi_digest` → digest di un insieme di chiavi (qui, §5.1);
`fn_libera_attivita_fatturabili` → la coppia di scritture di ripristino (là, L1).

### 9.4 Il legame causale, che spiega perché i due brief sono nati insieme

Le 5 attività perse dell'altro brief vengono da una fattura che **ha fallito la
numerazione** (`E_FATTURA_NON_NUMERABILE_INCOERENTE`, 24/08) ed è stata poi
eliminata dal lotto.

⭐ Questo cantiere riduce la pressione su quel percorso: **con la selezione, dopo
un fallimento si rinumera il solo lotto sistemato**, invece di agire sul mese o
disfare qualcosa. Meno occasioni di usare «Elimina dal lotto», che è il verbo su
cui vive il difetto.

⚠️ Il che **non** rende meno urgente la correzione DB: la rarità non è una difesa.

---

## 2026-08-26 · ✅ REALIZZATO — backend e frontend

Nessun prerequisito DB: il «pezzo DB» del §4 era una **costante Python**
(`SQL_PERIMETRO_LOTTI_NUMERABILI`), non una funzione del database. Il cantiere
è stato interamente BE/FE.

### Il perimetro, nelle sue due forme

`SQL_PERIMETRO_LOTTI_NUMERABILI` non è più una stringa da formattare: è
`costruisci_perimetro_lotti_numerabili`, che restituisce **SQL e parametri
insieme**. Finché erano due cose separate, l'ordine dei segnaposto e quello dei
valori erano due verità da tenere allineate a mano — ed è l'errore già successo
lo stesso giorno sul cantiere delle facet: invertiti non danno errore,
confrontano il valore sbagliato e tornano numeri plausibili.

⛔ **Lo stato EMESSA si applica anche sulla forma a lista.** Un lotto scelto a
mano non è per questo numerabile: la selezione decide il PERIMETRO, non le
regole, e la casella spenta a video è una comodità, non un presidio. Provato sul
database: selezionando `[1200, 79]` dove il 79 non è emesso, il perimetro ne
restituisce **uno solo**.

### I cinque anelli, tutti percorsi

| # | anello | esito |
| --- | --- | --- |
| 1 | `LottiListView` — selezione e verbi | ✓ |
| 2 | `POST fatturazione/numera/` accetta `lotti: [id]` | ✓ |
| 3 | payload della coda | ✓ |
| 4 | `fatturazione_numera_handler` | ✓ |
| 5 | `list_lotti_numerabili` — ramo id | ✓ |

più il ramo parallelo della finestra della data, che accetta `?lotti=` ripetuto.

### ⛔ La trappola della coda è chiusa — provata sull'HTTP

```
selezione [1200] → job 1268
selezione [1296] → job 1269      ← due job DISTINTI
stessa selezione, due volte → 1268, 1268   ← dedup ancora viva
```

`gruppi_digest` è diventata `insieme_digest` (**regola del 2, dichiarata a
Tid**): serviva identica ai gruppi dell'emissione mirata e ai lotti della
numerazione. Due copie sarebbero divergute sul punto che conta — se ordinano
prima di hashare — e la seconda avrebbe perso job legittimi in silenzio.

### Le decisioni prese realizzando

**D-6. La selezione ATTRAVERSA le due schede**, e questo chiude la trappola del
§3 del brief: un lotto di competenza precedente — quello che sta nei «recuperi»
— si spunta e si numera insieme a quelli del mese. È esattamente il caso che il
verbo di massa non sa fare, perché lavora su una competenza sola.

**D-7. ⛔ NON è stato estratto `useVerboFatturazione`.** Il brief lo dava per
scontato; leggendolo, quella funzione porta con sé concetti che la lista Lotti
non ha — i «gruppi non serviti», le marcature per `gruppo_key` — e riusarla
significherebbe trascinarli dentro per poi ignorarli. ⭐ Ciò che era davvero
condiviso **è già un BB**: `useJobPolling`. La lista Lotti usa quello.

**D-8. Il rimando dalla Lente 1 porta il MESE, non «solo gli emessi»** — e va
saputo: il filtro della lista Lotti è sullo stato del **lavoro**
(bozza/completato/errore), che è un altro asse dallo stato del **documento**.
Quali righe si possano numerare lo dice la casella, riga per riga, col suo
motivo.

### Cosa è sparito dalla Lente 1

Il verbo, il suo dialog, il suo polling e **sette chiavi i18n** — tolti, non
lasciati spenti: un percorso morto accanto a uno vivo non si distingue
leggendo, e il prossimo verbo non saprebbe quale imitare. Restano il conteggio
sulla card e il rimando: la card deve continuare a dire quante fatture aspettano
un numero, ed è l'informazione che manda l'operatore dove il verbo adesso vive.

### Un difetto corretto strada facendo

La validazione della selezione era **dopo** due giri al database. Un payload
malformato deve rompersi prima di pagare lavoro inutile, come già facevano gli
altri due campi del payload. Spostata in testa.

### Verifiche

**2720 test verdi** (12 nuovi), build FE e presidio i18n puliti. Sull'HTTP: i
tre perimetri della finestra rispondono, due insieme → 400, nessuno → 400,
selezione vuota → 400, `["x"]` → 400.

### ⚠️ Cosa resta

- **Collaudo in-app di Tid**: la selezione sulle due schede, i due verbi, il
  limite che si sposta spuntando lotti di sezionali diversi.
- **La guida** (`cruscotti-fatturazione.md` §7.1 e §6.3): è la riga contesa del
  §9.1, e va scritta **dopo** il passo L5 dell'altro cantiere, o una delle due
  mani perde il lavoro dell'altra.

---

## 2026-08-26 · Revisione critica prima del collaudo — 5 rilievi corretti

Richiesta di Tid a consegna avvenuta. **Due erano difetti veri**, e uno di essi
avrebbe detto una falsità proprio nel punto in cui si conferma un atto fiscale.

### 🔴 C-1 — Due porte, due regole sugli id dei lotti

La POST dell'atto rifiutava `lotti: [0]`; la GET della finestra lo **accettava**
e rispondeva `data_minima: null` — cioè «niente da numerare». Un errore di
chiamante travestito da dato tranquillo, misurato su `?lotti=0` e `?lotti=-3`.

Erano due validazioni scritte in due punti. Ora la GET **delega a `parse_lotti`**,
la stessa della POST: una regola sola. ⚠️ Con una distinzione tenuta: un
non-numero è un errore di FORMA (`lotti_invalid`), un id ≤ 0 è un errore di
VALORE — due errori diversi meritano due messaggi diversi.

### 🔴 C-2 — «L'atto numera 0 lotti»

Il dialog riceveva il conteggio come **prop dal chiamante**, e la lista Lotti
sull'atto di mese gli passava `0`: avrebbe annunciato *«L'atto numera 0 lotti»*
mentre stava per numerarli tutti.

⭐ Il numero lo dice ora il **server**, per entrambi i perimetri, e non è la
stessa cosa di «quanti ne ha chiesti il chiamante»: una selezione può contenere
lotti non più numerabili — li ha presi un altro giro, un collega li ha resi
definitivi. Verificato: chiedendo `[1200, 79]` dove il 79 non è emesso, la
risposta dichiara **1**, non 2. E il conteggio viene dalla **stessa discovery**
che l'atto percorrerà, quindi i due numeri non possono divergere.

### 🔴 C-3 — Il predicato «questo lotto si numera», scritto due volte

`useLottoAzioni.verbiPlausibili` decideva già `stato === 'EMESSA' → si numera`,
e il suo commento dice testualmente: *«tenerla qui, in una sede sola, è ciò che
impedisce che ricompaia sparsa nei template»*. La mia selezione l'ha riscritta.

Con due copie, il kebab di una riga potrebbe proporre «Rendi definitive» mentre
la casella della stessa riga è spenta — nessun errore, solo un'interfaccia che
si contraddice da sola. Estratto `lottoNumerabile(row)`, esportato, usato da
entrambi. ⭐ È rimasta **una sola** occorrenza di `'EMESSA'` in tutto il
frontend di questo cantiere, e sta lì dentro.

### ⚠️ C-4 — Un commento che prometteva più di quanto accade

Avevo scritto che il limite si ricalcola «mentre l'operatore spunta». Non
accade: il dialog è **modale** e riceve una copia della selezione presa
all'apertura. Il `watch` resta — il limite dipende dal perimetro, non dal
momento, e se un domani il limite si mostrasse accanto alla lista sarebbe già la
cosa giusta — ma il commento ora dice cosa fa davvero.

### ⚠️ C-5 — La selezione azzerata anche quando l'atto falliva

Si azzera ora **solo** in caso di successo. Azzerarla sul fallimento
costringerebbe a rifare la spunta a mano proprio nel momento in cui serve
riprovare, e su una lista paginata può voler dire ripercorrere le pagine.

### Verifiche

**2724 test verdi** (4 nuovi su `parse_lotti`), build ed eslint puliti.
Sull'HTTP: `n_lotti` = 3 sul mese e 1 sulla selezione mista, `?lotti=0` e
`?lotti=-3` → **400** su entrambe le porte.

---

## 2026-08-26 · 🔴 Pagina Lotti bianca — causa e correzione

Segnalazione di Tid al primo collaudo: il rimando dalla Lente 1 apriva la pagina
Lotti **vuota**, senza un errore leggibile.

### La causa: un'API inventata

```js
const { can } = useActionPermission()          // ⛔ firma inesistente
const canNumerare = computed(() => can('vendite', 'numera_fatture_lotti'))
```

`useActionPermission(codename)` prende l'azione come **argomento** e restituisce
un computed `isAllowed`. Con la firma sbagliata `can` usciva `undefined` e il
computed **sollevava al primo render** — e siccome `canNumerare` governa sia il
`v-if` dei verbi sia le caselle di selezione, l'eccezione arrivava durante il
render della pagina: schermo bianco.

⛔ **Niente lo ha intercettato**: eslint non fa type-check, la build non esegue,
e sul frontend non ci sono test. L'unico modo di accorgersene era **leggere
l'API invece di ricordarsela** — che è la stessa lezione di
[[feedback_slot_actions_lista_configurabile]]: col nome sbagliato la cosa non
compare, e nessuno protesta.

### ⭐ Cercando quella, ne è saltata fuori una PREESISTENTE

`useNotify()` non aveva `info`. Lo chiamavano **quattro** punti — due miei e
**due già in produzione nel cockpit di competenza**: «il giro era già in corso»
e «l'ha fatturato un altro giro». Tutti e quattro sollevavano
`notify.info is not a function` invece di mostrare il messaggio, e un toast che
non compare non si distingue da un toast che non è stato chiesto.

Aggiunta `info` (severità propria, durata propria: un informativo **non** è un
avviso — riusare `warn` avrebbe colorato di giallo messaggi tranquilli,
insegnando a ignorare il giallo).

### Un terzo difetto, silenzioso

`cambiaAnno` prende un **delta**, non l'anno. Il deep-link gli passava `2026`:
`anno + 2026` sfora il range e la funzione fa `return` — si sarebbe atterrati sul
mese giusto **dell'anno sbagliato**, senza un solo errore. Sarebbe emerso solo
rimandando a un anno diverso da quello a schermo.

### Il gate ripetuto

`canNumerare` porta già permesso **e** readonly, e i `:disabled` dei due verbi
lo ripetevano. Seconda copia tolta.

### La verifica che mancava, e che ora c'è

Un controllo sistematico di **ogni** identificatore che il mio codice chiama su
un composable, confrontato con ciò che quel composable restituisce davvero:
`useJobPolling`, `useApiHandler`, `useSelezioneToggle`, `useReadonlyMode`,
`useNotify`, più i due oggetti del mio `useSelezioneLotti` letti dai due
template. ⭐ È così che è emerso il `notify.info` preesistente.

⚠️ Vale come regola per il frontend di questo progetto: **una firma non si
ricorda, si legge** — non c'è nessuno strato che corregga chi sbaglia.

---

## 2026-08-26 · Dove siamo — il quadro

### ✅ Fatto e verificato

| | |
| --- | --- |
| perimetro nelle sue **due forme**, SQL e parametri insieme | `costruisci_perimetro_lotti_numerabili` |
| i **cinque anelli** del trasporto | lista → endpoint → coda → worker → SQL |
| la finestra della data sul **terzo perimetro** | `?lotti=` ripetuto |
| dedup della coda sul perimetro selezionato | `insieme_digest` (regola del 2) |
| selezione sulle **due schede** della lista Lotti | i «recuperi» si numerano insieme al mese |
| i **due verbi** nello stesso posto | selezione + mese |
| smontaggio della Lente 1 | verbo, dialog, polling e 7 chiavi i18n **tolti** |
| rimando filtrato dalla card `Fatturate` | ✔ collaudato da Tid |

**2724 test verdi**, build ed eslint puliti, i18n in parità.

### Le prove che reggono il lavoro

| | Cosa | Esito |
| --- | --- | --- |
| ⛔ | due selezioni diverse sullo stesso mese | **due job distinti** (1268/1269); la stessa selezione due volte resta uno |
| ⛔ | un lotto **non emesso** spuntato a mano | resta fuori: `[1200, 79]` → il perimetro ne prende **uno** |
| ⭐ | il conteggio annunciato | dal **server**, e dalla stessa discovery che l'atto percorrerà |
| | id sbagliati (`0`, `-3`, `abc`, lista vuota) | **400** su entrambe le porte |
| | perimetri ambigui o assenti | **400** |

### I difetti trovati strada facendo, e chi li ha visti

| | Difetto | Come è emerso |
| --- | --- | --- |
| 🔴 | pagina Lotti **bianca**: `useActionPermission` chiamata con una firma inventata | collaudo di Tid |
| 🔴 | `useNotify` senza `info`, con **quattro** chiamanti — due **preesistenti** nel cockpit | cercando la prima |
| 🔴 | GET e POST con regole diverse sugli id: `?lotti=0` rispondeva «niente da numerare» | revisione critica |
| 🔴 | «L'atto numera **0 lotti**» sul perimetro mese | revisione critica |
| 🔴 | il predicato «si numera» scritto **due volte** (kebab e casella potevano contraddirsi) | revisione critica |
| ⚠️ | `cambiaAnno` riceveva l'anno invece del delta: mese giusto, **anno sbagliato**, in silenzio | revisione critica |
| ⚠️ | validazione del payload **dopo** due giri al DB | realizzazione |
| ⚠️ | la selezione azzerata anche quando l'atto falliva | revisione critica |

⭐ **Tre su otto sono emersi solo perché qualcuno ha guardato lo schermo**, e due
di quelli erano difetti che nessun test avrebbe visto: eslint non fa type-check,
la build non esegue, e sul frontend non ci sono test. Da qui la regola scritta
in coda al §«Pagina Lotti bianca»: **una firma non si ricorda, si legge**.

### Cosa NON è stato fatto, e perché

- **`useVerboFatturazione` non è stato estratto** (D-7): porta con sé concetti
  che questa lista non ha, e ciò che era davvero condiviso — `useJobPolling` —
  era già un BB.
- **Il rimando porta il mese, non «solo gli emessi»** (D-8): il filtro della
  lista Lotti è sullo stato del *lavoro*, non del *documento*. Quali righe si
  numerino lo dice la casella, riga per riga, col suo motivo.
- **La guida** (C-2): bloccata dall'ordine col cantiere gemello — alla chiusura
  del brief (2026-08-28) la voce è **passata al gemello**, passo L5.

### ⚠️ Nota per chi committerà

Il cantiere tocca anche **due file di `core/`** — `useNotify.js` e
`constants.js` — per la severità `info` che mancava. È territorio condiviso, e
la correzione ripara **anche due punti preesistenti** del cockpit di competenza:
va detto a chi rilegge il commit, o sembrerà uno sconfinamento.

---

## 10. Rientro del 2026-08-27 — il collaudo C-1, e cosa ha cambiato

> Il collaudo è partito e ha trovato **quattro** difetti in poche prove, due dei
> quali rendevano il verbo su selezione **inutilizzabile**. Copione e verbale:
> [collaudo-in-app-rendi-definitive-sui-lotti.md](collaudo-in-app-rendi-definitive-sui-lotti.md).

### 10.1 I difetti trovati

| # | Cosa | Stato |
| --- | --- | --- |
| **R-1** | La selezione viaggiava come `?lotti[]=12` (serializzazione di default di axios per gli array) mentre il BE legge `getlist('lotti')`, chiave **senza** parentesi. `_query_lotti_ids` traduce la lista vuota in `None` → il servizio riceveva **tutti e tre** i perimetri nulli e rispondeva `E_VALIDATION_INPUT` su una richiesta in cui uno c'era. ⚠️ Accanto alla riga c'era un commento che **affermava il contrario**: la giustificazione era scritta e mai provata | ✅ `paramsSerializer: { indexes: null }` |
| **R-2** | I due verbi restavano **spenti per sempre** dopo un giro: `useJobPolling` si sospendeva su `onDeactivated` e lasciava il `resume()` alla view, che non lo chiamava. Uscire dal tab e rientrare bastava | ✅ `onActivated` nel BB |
| **R-3** | Dopo l'invio la selezione **non si svuotava**: il contatore diceva «(2)» contando lavoro già in volo | ✅ vedi §10.2 |
| **R-4** | La scheda «Recuperi» sopravviveva al **cambio mese**: il mese nuovo si apriva sulla vista di eccezione | ✅ watch su `competenzaParam` — `onActivated` non basta, un cambio filtro non riattiva niente |

### 10.2 ⭐ Decisione di Tid: **giri concorrenti ammessi**

Ricalcando l'emissione mirata del cruscotto competenza (`maxConcurrent: Infinity`,
decisione del 2026-08-17). Prima il tetto era **1** e i due verbi restavano spenti
per tutta la durata: una seconda selezione si poteva comporre ma non inviare.

Forma, e il pezzo che la rende sicura:

* all'invio le righe spedite **escono dalla selezione** e non si ri-spuntano
  finché il giro è vivo (`useRigheInGiro` + prune in `useSelezioneLotti`). Due
  invii **non possono sovrapporsi** per costruzione;
* ⛔ **«Rendi definitivo il mese» resta spento finché c'è un giro vivo**: il suo
  perimetro è **tutto** e si sovrapporrebbe alle righe già in volo — e lì la
  dedup non protegge, perché il digest è diverso. **Questa asimmetria è il pezzo
  che salva il rimedio dal creare il problema che evita**: se un giorno qualcuno
  riaccende quel verbo «per coerenza», è lì che si rompe;
* l'azzeramento della selezione a esito riuscito **è stato tolto**: con i giri
  concorrenti la selezione che c'è quando arriva l'esito è quella **nuova**,
  composta mentre il primo giro viaggiava. Era corretto quando i giri erano uno
  per volta — allora «la selezione» e «il perimetro appena spedito» erano la
  stessa cosa. Non lo sono più.

⚠️ **La prova 9 del collaudo era ineseguibile prima di questa decisione**, e
l'ha scoperto Tid provandola: la trappola del §5.1 si manifesta solo sulla
sovrapposizione di due giri, e l'interfaccia la vietava. Era una prova che
avrebbe preso il verde misurando niente.

### 10.3 Altro, dallo stesso giro

* la **rotellina** sui lotti del perimetro di un giro vivo (`useRigheInGiro`,
  estratto dal cruscotto alla 3ª occorrenza);
* i due verbi finiscono nel **kebab** sotto i 1024px, riusando le classi
  `app-page-actions-desktop`/`-compact` — stesso punto di rottura di tutte le
  liste. ⚠️ **Restano accanto alla lista** e non salgono nella barra azioni di
  pagina: quella è la toolbar di utility, e il principio di questo cantiere è
  che *«un verbo sta dove sta l'elenco del suo oggetto»*;
* il messaggio di esito dice ora anche che **i documenti sono in coda di
  stampa**: la numerazione finisce accodandoli, e senza quella riga «Numerato 1
  lotto» si legge come «è tutto pronto» mentre i PDF arrivano fino a due minuti
  dopo.

### 10.4 Cosa resta

*(scritto il 2026-08-27, superato il giorno dopo)* **C-1 non è chiuso**: il
collaudo è in corso, 15 prove di cui 4 consumano numeri. **C-2** (la guida) è
invariato — sempre in attesa del passo L5 del cantiere gemello (§9.1).

---

## 11. Chiusura — 2026-08-28

**C-1 è chiuso.** Tid ha eseguito il collaudo per intero: 16 prove (0 → 15),
tutte verdi, numeri veri consumati sulle prove 6, 9, 10 e 11 e **riletti sui
lotti** — che era il punto dell'intero copione. Verbale:
[collaudo-in-app-rendi-definitive-sui-lotti.md](collaudo-in-app-rendi-definitive-sui-lotti.md).

**C-2 non muore qui: cambia sede.** La riscrittura di §7.1 e §6.3 di
`cruscotti-fatturazione.md` è una voce esplicita del cantiere gemello
[brief-be-fe-lavoro-che-non-torna-indietro.md](../work-in-progress/brief-be-fe-lavoro-che-non-torna-indietro.md),
passo **L5** — l'unico che può riscrivere quella tabella senza che due mani si
sovrascrivano (§9.1). Finché quella voce è aperta, la guida **dice il falso**
sulla posizione di «Rendi definitive»: è la cosa da guardare per prima, aprendo
il gemello.

⚠️ **Cosa questo cantiere lascia scritto.** Il difetto R-1 — frontend che
serializza in un modo, backend che legge in un altro, con accanto un commento che
affermava il contrario — **non lo prende nessun test**: non c'è un runner FE e i
test Django mockano la request. Si è visto solo con una chiamata vera, fatta da
una persona. È l'argomento a favore di questi copioni di collaudo, non una
scusa per averne avuto bisogno.
