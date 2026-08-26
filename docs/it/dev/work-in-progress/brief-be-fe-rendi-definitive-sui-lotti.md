# Brief BE/FE — «Rendi definitive» torna dove stanno i lotti

> **Destinatario:** me stesso (BE/FE), con **un prerequisito DB** (§4).
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
> ⛔ **Stato: decisioni prese, niente scritto.**

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
