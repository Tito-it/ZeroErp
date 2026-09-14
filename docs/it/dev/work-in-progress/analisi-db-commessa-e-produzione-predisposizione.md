# Analisi DB — la commessa e la produzione: dove il ciclo si può fermare, e che cosa gli manca per farlo

> **Destinatario:** team DB (`dev/db-tid`), con una parte finale che riguarda
> anche BE/FE quando le colonne esisteranno.
>
> **Origine.** Domanda di Tid, 2026-09-01: *«la commessa è nata pensando al
> software anche per aziende che hanno produzione. Abbiamo l'ordine che va in
> commessa; lì pensavo che se la commessa richiedeva produzione si sarebbe
> fermata e avrebbe attivato le tabelle necessarie alla produzione (ancora non ci
> sono). Mi serve sapere se siamo predisposti, oppure se manca qualcosa».*
>
> **Perché adesso.** Perché la risposta non è «sì» né «no»: è che **il punto in
> cui il ciclo si può fermare non è la commessa**, e finché non lo si sa si
> progetta la produzione agganciandola all'anello sbagliato. ⭐ E perché una
> parte delle cose che mancano **manca comunque**, produzione o no: sono
> dimensioni del ciclo di vendita che oggi non esistono e che pesano già.
>
> **Stato:** 🔵 **APERTO — è un'ANALISI, non un piano.** Nessun changeSet scritto,
> niente applicato, nessuna decisione presa. La §8 elenca ciò che va aggiunto **a
> prescindere** dalla decisione di modello; la §7 è la decisione, ed è **rinviata a
> un'analisi sua** per volontà di Tid: *«poi faremo un'analisi se la commessa
> attuale può essere valida anche per la produzione o se conviene fare una
> specifica»*.
>
> 📌 **Declassato ad analisi il 2026-09-01** (decisione di Tid), e rinominato da
> `brief-db-…` a `analisi-db-…`: ⭐ è la stessa distinzione già usata dal cantiere
> numerazione, dove l'**analisi** dice *perché* e il **brief** dice *cosa si fa*.
> Il piano operativo che ne discende — le sole modifiche **certe**, quelle che
> nessuna decisione aperta cambia — vive in
> [brief-db-modifiche-certe-ciclo-vendita-e-articolo.md](../work-done/brief-db-modifiche-certe-ciclo-vendita-e-articolo.md).
> ⛔ Da qui in avanti **questo documento non si esegue**: si consulta.
>
> ⚠️ **Perimetro:** questa analisi guarda la **commessa e il ciclo di vendita**.
> Il lato magazzino — l'aggancio del movimento al documento di origine, l'ODL come
> sorgente, l'unicità del ledger — è già aperto e non si duplica qui:
> [analisi-db-magazzino-aggancio-documento-e-produzione](analisi-db-magazzino-aggancio-documento-e-produzione.md).
> I due brief sono **gemelli** e le loro decisioni si tengono (vedi §7).

---

## 1. Che cosa è stato letto, e di che natura è

Letto il **2026-09-01** sulla documentazione auto-generata (`docs/it/dbzero/`, che
riflette gli oggetti vivi), sui seed di `db/changelog/migrations_v2/80_data/` e
sui corpi delle funzioni in `20_code/`.

⚠️ **Sono tutte letture di struttura, non di contenuto**: colonne, nullabilità,
CHECK, FK, righe di catalogo, corpi di funzione, e la ricerca di *chi legge* una
colonna. Nessuna affermazione di questo brief poggia su un `count(*)`. Dove si
dice che un flag «non è letto da nessuno» è il risultato di una ricerca sul
**codice** — `20_code/`, `backend/apps/`, `frontend/src/` — cioè sul contratto,
non sui dati.

---

## 2. La commessa di oggi è un contenitore di fatturazione

La catena la dichiara la doc concettuale della tabella:
`sorgente → commessa → commesse_attivita → attivita_fatturabili`.

Le dimensioni di [`vendite.commesse`](/dbzero/vendite/tabelle/commesse) sono
billing account, utility, emittente fiscale, policy di fatturazione, priorità
operativa, competenza (`competenza_dal`/`competenza_al`), termine e modalità di
pagamento, stato.

⛔ **Non ha articolo, non ha quantità, non ha una data di consegna, non ha un
budget, non ha un consuntivo, e non ha nemmeno una descrizione**: `codice` è
l'unico campo parlante.

Due fatti strutturali dicono la sua natura meglio delle colonne:

1. **Si riusa.** [`fn_get_or_create_commessa`](/dbzero/vendite/funzioni/fn_get_or_create_commessa)
   cerca una commessa esistente sullo stesso perimetro BA/utility e la riusa se
   lo stato non è terminale (`stati_commessa.chiude_commessa = false`). ⛔ **Una
   commessa non è «una per ordine»**: è un raccoglitore che vive finché non lo si
   chiude. Una commessa di produzione è l'opposto — nasce per un fabbisogno e
   muore quando quel fabbisogno è soddisfatto.
2. **Ci si arriva quando c'è da fatturare.** L'«ordine che va in commessa» è
   [`fn_list_ordini_da_pushare`](/dbzero/vendite/funzioni/fn_list_ordini_da_pushare),
   che seleziona le righe **solo** per `fatturazione_trigger = 'CONFERMATO'` e le
   scrive in `commesse_attivita` con `prezzo_bloccato = TRUE`. Gli ordini con
   trigger `SPEDITO`/`CONSEGNATO` passano invece da `fn_list_ddt_da_pushare`.
   ⭐ **È il push del ricavo.** La riga entra in commessa perché è diventata
   *fatturabile*, non perché è diventata *da fare*.

`tipo_commessa` ammette `REALE` e `AUTO`, e `REALE` lo scrive soltanto il push da
preventivo. Non c'è, sotto quel nome, una commessa di lavoro: c'è la distinzione
fra una commessa nata da un documento e una nata dalla ricorrenza.

---

## 3. Il modello smista già le righe — e la produzione non è una destinazione

⭐ Questa è la scoperta che riorienta tutto il resto, e va guardata prima di
decidere qualunque cosa.

`config.nature_vendita` è una dimensione **viva**, non un catalogo dormiente:

| `codice_interno` | `destinazione_tipo` | Significato |
| --- | --- | --- |
| `MERCE` | **`ORDINE`** | Bene fisico da evadere (magazzino, DDT) |
| `SERVIZIO_UNA_TANTUM` | **`COMMESSA`** | Servizio una tantum (commessa diretta) |
| `SERVIZIO_RICORRENTE` | **`CONTRATTO`** | Servizio ricorrente (canone) |

`catalogo.articoli.natura_vendita_id` è **NOT NULL**, e `destinazione_tipo` ha un
CHECK su quei tre valori. Lo leggono le viste di smistamento del preventivo
(`vw_preventivi_smistamento`, `vw_preventivi_righe_smistabili_ordine`,
`vw_preventivi_righe_smistabili_commessa`) e `fn_push_preventivo_a_ordine`.

⛔ **Ne discende una cosa che va detta chiaramente: in questo modello la commessa
è dove vanno i SERVIZI.** La merce va in ordine. Una riga di merce **non passa
dalla commessa** per essere prodotta o spedita: ci passa, semmai, dopo, quando
c'è da fatturarla.

⚠️ **E quindi la produzione non è una quarta `destinazione_tipo`.** La
destinazione dice *in quale documento diventa* una riga venduta. La produzione
risponde a un'altra domanda — *da dove arriva la merce che ho promesso* — e le
risposte sono tre (c'è a magazzino / la compro / la faccio), ortogonali alla
destinazione. Metterla lì dentro farebbe rispondere a una colonna sola due
domande diverse, che è la forma di difetto già registrata nel progetto.

---

## 4. Dove il ciclo si può davvero fermare

Il punto esiste già, ed è la **riga d'ordine confermata**.

[`vw_situazione_merce_ordine`](/dbzero/vendite/views/vw_situazione_merce_ordine)
tiene per ogni riga d'ordine `ordinato`, `consegnato`, `reso`, `da_spedire`, e ha
già la **soglia dell'impegno**: sotto lo stato `CONFERMATO`, `da_spedire` è NULL
e lo stato è `NON_IMPEGNATA` — perché su una bozza l'impegno non c'è ancora.
Sopra la soglia, la riga dichiara un arretrato vero.

⭐ **È esattamente il posto in cui manca un ramo.** Oggi la vista sa *quanto*
resta da spedire; non sa **da dove dovrebbe arrivare**. Non c'è nulla, in nessuna
tabella, che sappia rispondere a «questa riga richiede produzione?» — e il §8
dice perché: manca il dato sull'articolo.

Il «si ferma e attiva la produzione» che si aveva in mente, quindi, non si
aggancia alla commessa perché **la commessa entra in scena dopo**. Si aggancia
alla riga d'ordine, nel momento in cui l'impegno diventa reale.

---

## 5. Quello che è già predisposto — e non è poco

| Fondamenta | Che cosa consente |
| --- | --- |
| **Macchina a stati dato-guidata** | [`stati_commessa`](/dbzero/vendite/tabelle/stati_commessa) ha `fase`, `emittibile`, `modificabile`, `chiude_commessa`, `is_abortito`; [`transizioni_stati_commessa`](/dbzero/vendite/tabelle/transizioni_stati_commessa) è il grafo, presidiato da `trgfn_commesse_guard_transizione`. ⭐ Uno stato che **sospende la fatturazione** (`emittibile = false`) è **un seed, non DDL** |
| **Stati d'ordine, stessa forma** | `config.stati_doc_ordini` con `codice_interno` e la soglia già usata per l'impegno |
| **Sorgente polimorfa a catalogo** | `config.sorgenti` con `target_table`, `key_selector`, `scope`: un ODL come sorgente è **una riga di seed** |
| **Motore di processo generico** | Lo schema `pratiche` (template di flusso, definizioni versionate, handler, calcoli tempo, sospensioni, giornale): un **ciclo di lavorazione** è esprimibile lì senza fondare infrastruttura nuova |
| **Coda lavori e registry task** | `dbops.coda_lavori`, `dbops.domini_task`, `pipeline_task_registry`: un ricalcolo dei fabbisogni sarebbe un task, non un programma |
| **Magazzino disegnato** | ledger, causali, riservazioni, costo medio, ubicazioni, lotti/seriali, inventari, trasferimenti |
| **La produzione era stata prevista** | `magazzino.causali.richiede_odl`, le causali `ODL_USCITA_MAT` / `ODL_ENTRATA_MAT`, l'ambito `ODL — Movimenti da Ordini di Lavoro`, e `reservations` descritta *«Prenotazioni stock per ordini e ODL»* |
| **Distinta base versionata** | [`catalogo.articoli_componenti`](/dbzero/catalogo/tabelle/articoli_componenti): validità a `daterange`, exclusion constraint sul non-overlap, immutabilità della struttura |
| **Via d'uscita per il non-utility** | `anagrafiche.istanze_utilities.fittizia` e la utility `BASE — Servizio Base`: l'obbligo di `utility_id` non è un muro per un'azienda che utilities non ne vende |
| **Conversione unità di misura** | `catalogo.unita_misura_conversioni`, `articoli_uom_operativa`, `factor_to_base` presente su tutte le righe documento |

---

## 6. Quello che manca — e sono tre cose di natura diversa

Vanno tenute separate perché **non si risolvono nello stesso modo**: la prima si
scrive, la seconda si costruisce, la terza si aggiunge a ciò che esiste già.

### A. L'oggetto ODL: nominato e mai nato

L'[analisi magazzino](analisi-db-magazzino-aggancio-documento-e-produzione.md) lo
copre (§6 e D-5). Quello che si aggiunge qui, verificato sul codice:

* ⛔ `causali.richiede_odl` e `causali.contabilizza_cdc` sono **flag morti**:
  dichiarati nel DDL, seminati a `true` su due causali, e **non letti da nessuna
  funzione, nessun trigger e nessun modulo backend**;
* ⛔ `causali.ambito_causale_id` è vuoto su **tutte** le righe del seed: il
  vocabolario dei sei ambiti — `ODL` compreso — non è collegato a niente;
* ⛔ **manca la causale del versamento.** Il seed ha *uscita materiali* e *rientro
  materiali*; **non ha il carico del prodotto finito**. Con il vocabolario di
  oggi si possono consumare i componenti e non si può caricare ciò che si è
  prodotto;
* ⛔ `contabilizza_cdc` punta a un **centro di costo che non esiste** in nessuno
  schema.

📌 **Il vocabolario delle causali per intero** — e le due che mancano — è dal
2026-09-02 in [analisi-db-magazzino-carico-e-scarico §2 e §3](analisi-db-magazzino-carico-e-scarico.md). Qui resta il
solo argomento di questa sezione: che la produzione era **nominata** e l'oggetto a
cui punta non esiste.

### B. Il motore del magazzino: la struttura c'è, l'alimentatore no

⚠️ **`magazzino.movimenti` non è scritto da nessuno**, e `vw_giacenza` non sottrae
le prenotazioni: **oggi non esiste una disponibilità**, e senza disponibilità non
c'è niente su cui un fabbisogno possa decidere.

⭐ *(Aggiornato il 2026-09-02: la vista somma `qta` senza guardare la causale, e
questo **non è più un difetto** — il verso sta nella quantità per decisione presa,
[analisi carico e scarico §4](analisi-db-magazzino-carico-e-scarico.md). Il buco che resta è la disponibilità, non il
segno.)*

📌 **Il dettaglio non sta più qui**: dal 2026-09-02 è in
[analisi-db-magazzino-carico-e-scarico.md](analisi-db-magazzino-carico-e-scarico.md) — chi scrive (là §5), il verso
della quantità (§4), la lettura della giacenza e la valorizzazione ferma (§7).
Quello che resta di questa sezione è la conseguenza **per la produzione**: il ledger
è una struttura senza alimentatore, e la produzione ne è il consumatore più pesante
— non c'è dove versare né da dove prelevare.

### C. Le dimensioni che al ciclo di vendita mancano comunque

⭐ **Queste non sono debito della produzione: sono debito dell'ordine.** La
produzione le rende visibili, ma pesano già. Il dettaglio operativo è in **§8**,
che è la parte da leggere per prima se si vuole muovere qualcosa subito.

In sintesi: **non esiste una data di consegna** in nessun punto del ciclo;
**non esiste il modo di approvvigionamento** di un articolo; la **distinta è
dichiarata di vendita** e non ha ciò che serve a fabbricare; **non esiste un
consuntivo** — si registra ciò che si fattura, mai ciò che si consuma.

---

## 7. La decisione di modello — rinviata, e va rinviata bene

> ⛔ **Questo brief NON la prende.** Tid l'ha esplicitamente separata:
> *«poi faremo un'analisi se la commessa attuale può essere valida anche per la
> produzione o se conviene fare una specifica»*. Qui si scrive **che cosa dovrà
> decidere quell'analisi**, perché una domanda mal posta si risponde male.

**La domanda è la gemella della D-5 del brief magazzino** («l'ODL è una sorgente
o un anello proprio?»), vista dal lato di `vendite`:

> **La testata di una commessa di lavoro è `vendite.commesse`, o è un'entità sua?**

Le due strade, con il loro costo dichiarato:

| | La commessa resta il contenitore di fatturazione | La commessa diventa la testata di progetto |
| --- | --- | --- |
| **Dove nasce la produzione** | Un anello 3 nuovo (`produzione`), agganciato alla **riga d'ordine**, che riversa in `magazzino` | Dentro `vendite`, come nuova natura di commessa |
| **Che cosa vede la commessa** | L'ODL come **una sorgente in più** (`config.sorgenti`, +1 riga) | Sé stessa: le servono quantità, date, budget, consuntivo |
| **Costo sul già fatto** | Nessuno: la pipeline di fatturazione non si tocca | ⚠️ `commesse_attivita` cambia natura sotto una pipeline **in esercizio**, e `fn_get_or_create_commessa` riusa le commesse: andrebbe scardinato il riuso |
| **Rischio** | Due entità che si somigliano e vanno tenute distinte a parole | Una entità che risponde a due domande, che è la forma di difetto già registrata |

⚠️ **Elementi che l'analisi dovrà pesare, e che oggi sono fatti:**

* la commessa **si riusa** per BA/utility (§2): una commessa di lavoro non si
  riusa mai;
* la commessa non ha **cliente proprio** — ci arriva attraverso il billing
  account, che è una dimensione di **fatturazione**;
* `competenza_dal`/`competenza_al` sono **competenza fiscale**, non finestra di
  esecuzione: ⛔ non vanno riusate come date di lavorazione, farebbero dissentire
  due domande sulla stessa colonna;
* `utility_id` è **NOT NULL** su `commesse` e `istanza_utility_id` è NOT NULL su
  `commesse_attivita`: sopravvivibile via `BASE` + `istanze_utilities.fittizia`,
  ma su una commessa di produzione resterebbe una dimensione **finta e
  obbligatoria**, ed è un costo da mettere sul piatto della prima colonna;
* la BoM è **immutabile per disegno** (ancorata agli snapshot di
  `commesse_attivita`): una distinta di produzione ha bisogno di **varianti per
  ODL**, che è il requisito opposto (§8.4).

---

## 8. ⭐ Le dimensioni da aggiungere **comunque** — indipendenti dalla decisione

> Questa è la parte richiesta da Tid: *«evidenzia le cose che per prime
> andrebbero modificate, tutte quelle dimensioni del ciclo di vendita che vanno
> comunque aggiunte alle tabelle attuali»*.
>
> ⭐ **Criterio di ammissione a questa sezione:** ci sta solo ciò che serve
> **qualunque risposta** riceva la §7 — e, quasi sempre, ciò che serve **anche se
> la produzione non si facesse mai**. Le voci che invece dipendono dalla
> decisione sono marcate ⏸️ e vanno lasciate lì.

### 8.1 `vendite.ordini_righe` — la data di consegna ⭐ **la prima di tutte**

| Colonna proposta | Tipo | Perché |
| --- | --- | --- |
| `data_consegna_richiesta_cliente` | `date` | Quando il cliente la vuole — ⭐ suffisso da **D-16** (2026-09-02): il nome dice di chi è la data |
| `data_consegna_confermata` | `date` | Quando l'azienda si impegna a darla — non marcata perché è **nostra** — **è un'altra cosa**, e la differenza fra le due è la promessa |

⛔ **Oggi non esiste alcuna data di consegna in tutto il modello.** Cercata su
`vendite`, `acquisti` e `magazzino`, l'unica data di previsione dell'intero
database è `magazzino.reservations.data_prevista` (dal 2026-09-02 decisa come `magazzino.movimenti_attesi`) — in uno schema che non è in
esercizio. `ordini.data` è la data **documento**, e `competenza_*` è competenza
**fiscale**: ⚠️ nessuna delle due va riusata.

**Perché è la prima anche senza produzione:** senza data di consegna non esiste
la nozione di **ritardo**. `vw_situazione_merce_ordine` sa dire *quanto* resta da
spedire e non saprà mai dire *se è tardi*. Nessun sollecito, nessuna priorità di
evasione, nessun indicatore di puntualità — e sono cose che servono a un'azienda
che vende e basta.

⚠️ **Va sulla RIGA, non solo sulla testata.** Una riga può essere pronta e
un'altra no: è esattamente il caso «questa richiede produzione». Una data sulla
sola testata la si può aggiungere come **default che le righe ereditano**
(decisione minore, non blocca).

⚠️ **Da propagare a monte e a valle** perché la data sopravviva ai passaggi:
`preventivi_righe`, `offerte_commerciali` (dove la data è *proposta*),
`acquisti.ordini_righe` (dove è la data **attesa dal fornitore**, ed è
l'informazione che oggi manca per sapere se la merce arriverà in tempo).

### 8.2 `catalogo.articoli` — da dove arriva la merce

| Colonna proposta | Tipo | Perché |
| --- | --- | --- |
| `modo_approvvigionamento` | `varchar` + CHECK (`ACQUISTO` / `PRODUZIONE` / `STOCK` / `NON_APPLICABILE`) | ⭐ **È la colonna che oggi rende impossibile la domanda «questa riga richiede produzione?»** |
| `gestito_a_magazzino` | `boolean` | Se l'articolo movimenta giacenza. Oggi **niente** distingue un bene stoccabile da una prestazione |
| `lead_time_giorni` | `integer` | Quanto tempo passa fra «lo chiedo» e «ce l'ho». Serve a ricavare la data di lancio dalla data di consegna: senza, la data della §8.1 non sa produrre nessuna scadenza a monte |

⛔ **Nessuna colonna esistente risponde già**, e le tre candidate ovvie sono
tutte sbagliate:

* `is_composito` dice che l'articolo **ha componenti da esporre in fattura**
  (pricing v5, `esposto_in_fattura`): è una domanda di fatturazione. Un
  assemblato può essere comprato finito, e un articolo semplice può essere
  prodotto;
* `natura_vendita_id` dice **dove va la riga venduta** (§3), non da dove arriva
  la merce;
* `nature_vendita.e_cessione_beni` è **fiscale** — lo consuma il risolutore IVA
  (`fn_resolve_iva_riga_guscio`). ⚠️ Riusarlo come flag logistico farebbe
  rispondere a un dato due domande in AND, e quel difetto è già registrato.

⏸️ *Secondo anello, quando ci sarà una giacenza vera:* `scorta_minima`,
`lotto_riordino`, `punto_di_riordino`.

### 8.3 `vendite.ordini_righe` — lo stato di copertura

Oggi `ordini_righe.stato_doc_ordine_id` è lo stato **commerciale** della riga.
Manca la risposta a «questa riga è coperta?» — DA_COPRIRE / IN_ACQUISTO /
IN_PRODUZIONE / DISPONIBILE.

⚠️ **Ma qui la colonna non è ovvia, ed è meglio dirlo che deciderlo adesso:**
se un giorno esisteranno l'ODL e l'ordine di acquisto agganciati alla riga,
la copertura è **derivabile** e una colonna memorizzata diventerebbe una
**seconda sorgente di verità**. La forma giusta è probabilmente una vista
accanto a `vw_situazione_merce_ordine`, non una colonna. **Voce da tenere aperta,
non da scrivere.**

### 8.4 `catalogo.articoli_componenti` — la distinta, se dovrà fabbricare

| Colonna proposta | Perché |
| --- | --- |
| `uom_id` del componente | Oggi `coeff_qta` è un numero puro e l'unità è **implicita** nella base del componente. Per un prelievo di materiale l'unità va detta |
| `scarto_percentuale` | Lo sfrido: quanto si consuma in più di quanto entra nel prodotto |

⏸️ **Dipendono dalla §7 e vanno lasciate lì:** componenti alternativi, legame
componente↔fase, e soprattutto **se la distinta di produzione sia questa tabella
o un'altra**. ⚠️ La ragione è dichiarata nella doc: `articoli_componenti` è la
BoM **di vendita** ed è resa **immutabile** apposta, perché `commesse_attivita`
ci ha ancorato sopra i propri `prezzo_snapshot`. Una distinta di produzione ha
bisogno di **varianti e revisioni per ODL**: è il requisito opposto, e
sovrapporli erediterebbe un'immutabilità nata per un altro motivo.

⛔ **E manca del tutto il ciclo di lavorazione** — fasi, risorse, tempi: non è
una colonna, è una struttura, e sta di là dalla decisione.

### 8.5 `vendite.commesse` — le dimensioni che le mancano *come commessa*

Queste servono **anche se la commessa resta solo un contenitore di
fatturazione**: sono ciò che oggi le manca per essere leggibile e governabile.

| Colonna proposta | Perché serve comunque |
| --- | --- |
| `descrizione` (o `oggetto`) | ⛔ Oggi la commessa ha `codice` e **nient'altro di parlante**: in lista non si sa che cos'è. Vale per il contenitore di fatturazione quanto per la commessa di lavoro |
| `data_apertura` | Quando è nata come **fatto operativo**. ⚠️ `competenza_dal` è competenza fiscale e non va riusata |
| `responsabile_soggetto_ruolo_id` | Chi la governa. Oggi una commessa non ha un intestatario interno |

⏸️ **Dipendono dalla §7:** `soggetto_ruolo_id` (il cliente come dimensione
propria e non derivata dal billing account), `data_chiusura_prevista`,
quantità/articolo di testata, budget.

⏸️ **E il consuntivo non è una colonna**: è una struttura (costi materiali, ore,
WIP) che oggi non esiste da nessuna parte — `attivita_fatturabili` registra ciò
che si **fattura**, mai ciò che si **consuma**. Va progettato, non aggiunto.

### 8.6 `magazzino` — le due cose minime

* ⛔ **la causale del versamento del prodotto finito** (segno `+1`), oggi assente;
* ⛔ **valorizzare `causali.ambito_causale_id`**, oggi vuoto su tutte le righe —
  altrimenti il vocabolario `ODL` resta debito che sembra struttura (è la **D-8**
  dell'analisi aggancio).

📌 Entrambe sono ora trattate in
[analisi-db-magazzino-carico-e-scarico §3](analisi-db-magazzino-carico-e-scarico.md), che è la sede del vocabolario.

---

## 9. Ordine di attacco proposto

> ⚠️ È una proposta di sequenza, non un piano approvato. La sequenza segue una
> regola sola: **prima ciò che serve comunque, poi ciò che dipende da una
> decisione.**

| # | Cosa | Dipende dalla §7? |
| --- | --- | --- |
| **1** | La **data di consegna** su riga d'ordine (+ preventivo, + ordine d'acquisto) — §8.1 | ❌ no, serve subito e da sola |
| **2** | **`modo_approvvigionamento`** + `gestito_a_magazzino` + `lead_time_giorni` su `articoli` — §8.2 | ❌ no: è la colonna che *rende ponibile* la domanda della produzione |
| **3** | Le tre colonne parlanti su `commesse` — §8.5 | ❌ no |
| **4** | ✅ **DECISO il 2026-09-02**, non più da fare: il verso sta nella **quantità** (M-1) e «chi scrive» è la **primitiva guidata dalle causali** (M-2) — [analisi carico e scarico §4 e §5-bis](analisi-db-magazzino-carico-e-scarico.md). ⚠️ *Questa riga diceva ancora «da fare» mentre la §6.B era già stata aggiornata lo stesso giorno: il documento è di sola consultazione, ma è **questa tabella** che qualcuno userà come sequenza* | — |
| **5** | Causale di versamento + `ambito_causale_id` valorizzato — §8.6 | ❌ no (è già D-8 del brief gemello) |
| **6** | **L'analisi della §7** — commessa unica o commessa di produzione dedicata | — è *lei* la decisione |
| **7** | ODL, ciclo di lavorazione, consuntivo, fabbisogni | ✅ sì, tutto |

⭐ **I passi 1→5 non anticipano nessuna scelta**: se un domani la produzione non
si facesse, resterebbero comunque migliorie del ciclo di vendita. È il motivo per
cui possono partire prima che la §7 abbia una risposta.

---

## 10. Che cosa NON è di questo brief

* **L'aggancio del movimento al documento**, l'ODL come sorgente o anello,
  l'unicità del ledger, il guard tipizzato: stanno nell'[analisi
  magazzino](analisi-db-magazzino-aggancio-documento-e-produzione.md),
  decisioni D-1 → D-9.
* **La decisione sulla testata** (§7): analisi separata, per volontà di Tid.
* **Valorizzazione, lotti, seriali, ubicazioni, RLS su `magazzino`**: §9 del brief
  gemello.
* **Lato BE/FE non si chiede nulla in questa fase.** Le colonne della §8 sono DB;
  i consumatori applicativi si scrivono quando le colonne esistono.

---

## 11. Riferimenti

* Il gemello sul magazzino:
  [analisi-db-magazzino-aggancio-documento-e-produzione.md](analisi-db-magazzino-aggancio-documento-e-produzione.md)
* Convenzione della sorgente polimorfa: [sorgente-polimorfa.md](../../guide/sorgente-polimorfa.md)
* Stato dei domini: [mappa-concentrica.md](../../mappa-concentrica.md) § Anello 3
* Il punto d'aggancio operativo:
  [vw_situazione_merce_ordine](/dbzero/vendite/views/vw_situazione_merce_ordine)
* Lo smistamento per natura: `vw_preventivi_smistamento`,
  `vw_preventivi_righe_smistabili_ordine`, `fn_push_preventivo_a_ordine`
