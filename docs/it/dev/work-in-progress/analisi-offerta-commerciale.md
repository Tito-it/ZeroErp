# Analisi — Offerta commerciale come dominio separato

> **Stato**: DECISIONI DI MODELLO §5 CHIUSE (sessione 2026-05-23). Resta da
> scrivere il brief DB operativo. Nessun codice ancora toccato.
>
> **Scope**: introdurre un'entità `offerta_commerciale` (proposta di condizioni
> quadro) come predecessore tracciato del contratto, distinta dal preventivo
> (proposta di transazione puntuale).
>
> **Origine**: sessione 2026-05-15 nel contesto del refactor contratti
> ([`refactor-contratti-modalita.md`](../work-done/refactor-contratti-modalita.md)). Discutendo il
> modello prezzi dei preventivi (snapshot riga-per-riga) vs contratti (snapshot della
> versione listino, decisione §3-bis-A) è emersa la domanda: "ma forse il preventivo più
> che in un contratto dovrebbe andare in un'offerta commerciale o sbaglio?".
>
> **Evoluzione dello stato**:
>
> - 2026-05-15 — prime riflessioni, analisi di opportunità (opzione (c) preferita).
> - 2026-05-23 — chiusura di tutte le decisioni di modello §5 in sessione dedicata.
>   Opzione (c) confermata. Documento promosso da "analisi iniziale aperta" a
>   "modello deciso, pronto per brief DB".
>
> **Riferimento incrociato chiave**: questo dominio è il prerequisito dell'asse
> `OFFERTA_QUADRO` descritto in
> [analisi-pratiche-domini-anello3.md](analisi-pratiche-domini-anello3.md)
> §11.2 (ossatura pratica già predisposta, in attesa di questo dominio). Vedi §9.

---

## 1. Stato attuale ZeroERP

### 1.1 Cosa esiste

- **Preventivo** (`vendite.preventivi` + `preventivi_righe`): proposta puntuale al cliente
  per articoli/prezzi specifici. Stato BOZZA → EMESSO → ACCETTATO. L'accettato genera una
  **commessa** via `push_a_commessa` ([preventivi_service.py:1910](../../../../backend/apps/vendite/services/preventivi_service.py#L1910)),
  che entra nella pipeline fatturazione.
- **Contratto** (`vendite.contratti` + `contratti_righe` + `contratti_utilities`): relazione
  duratura cliente↔listino con eventuali variazioni/eccezioni. Stato DRAFT → ATTIVO →
  CESSATO. **Nasce direttamente dall'operatore**, senza essere preceduto da nessuna
  proposta formalizzata.

### 1.2 Cosa NON esiste

- Entità `offerta_commerciale` — nessuna tabella, service, view, doc.
- Flusso `push_a_contratto` (specchio di `push_a_commessa`) — non esiste perché manca il
  predecessore.
- Relazione tracciata fra preventivo e contratto — il preventivo va a commessa, mai a
  contratto.

### 1.3 Conseguenza operativa attuale

Quando un operatore tratta condizioni quadro con un cliente ("ti propongo listino X con
sconto Y per 12 mesi"), la negoziazione **non è tracciata** nel sistema:

- Niente documento di proposta
- Niente stato "in attesa di accettazione"
- Quando il cliente accetta, l'operatore crea direttamente il contratto in DRAFT
- L'unica traccia documentale è eventualmente un PDF/email allegato fuori sistema

---

## 2. La distinzione concettuale: preventivo vs offerta commerciale

Sotto il profilo del dominio commerciale "classico", i due artefatti hanno **scopo e
contenuto strutturalmente diversi**:

| Aspetto                 | Preventivo (esistente)                                        | Offerta commerciale (decisa)                                                                              |
| ----------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **Cosa propone**        | "Ti vendo questi 5 articoli a questi prezzi totale €X"        | "Ti propongo di essere mio cliente al listino LST-001 con sconto 5% per 12 mesi"                          |
| **Scope temporale**     | Una transazione puntuale                                      | Condizioni quadro durature                                                                                |
| **Cosa contiene**       | Lista articoli + quantità + prezzi snapshottati               | Listino di riferimento + variazione globale + eventuali eccezioni (OVERRIDE/ESCLUSIONE/AGGIUNTA proposte) |
| **Snapshot del prezzo** | Riga-per-riga (`prezzo_unitario` materializzato per articolo) | Versione del listino fissata all'emissione (le righe non-eccezione leggono dinamicamente)                 |
| **Accettato diventa**   | Commessa singola → fattura una tantum                         | Contratto DRAFT → (attivazione operatore) → pipeline fatturazione ricorrente                              |
| **Vita del documento**  | Si chiude all'accettazione/scadenza                           | Resta come traccia storica immutabile della negoziazione del contratto                                    |
| **Revisioni**           | Già supportate (`fn_crea_revisione_preventivo`)               | Stesso bisogno (rinegoziazione/aggiornamento listino prima dell'accettazione)                             |

In altre parole: i **modelli di snapshot** che abbiamo isolato durante il refactor contratti
(§3-bis-A) sono già **specchio** della differenza fra i due artefatti:

- Snapshot riga-per-riga = chiude una transazione → preventivo → commessa
- Snapshot della versione listino = fissa una relazione → offerta commerciale → contratto

Il modello che abbiamo costruito per il contratto **postula implicitamente** l'esistenza di
una "proposta di condizioni" da cui nasce. Questo dominio la formalizza.

### 2.1 La tensione di fondo (chiave di lettura delle decisioni §5)

C'è un punto dove l'analogia "offerta = specchio del preventivo" si rompe, ed è il filo
che lega tra loro quasi tutte le decisioni §5: **il preventivo propone *cose*, l'offerta
propone *un modo di stare in relazione*.**

Conseguenza: il preventivo è autoconsistente (le righe *sono* il preventivo), mentre
l'offerta è un puntatore a qualcosa che vive di vita propria — il listino, che cambia
versione e ha le sue regole. Quasi ogni domanda difficile della §5 (granularità, listino
mobile, eccezioni) è una manifestazione della stessa tensione: **quanto l'offerta congela
vs quanto lascia fluido.** Le decisioni prese in §5 risolvono questa tensione in modo
coerente, sempre dal lato del *congelamento tracciabile* (l'offerta è un documento storico,
non un puntatore fluido), perché è l'unico compatibile con finestre di accettazione di
settimane/mesi.

---

## 3. Tre strade possibili (decisione: opzione c)

### 3.1 Opzione (a) — Restare come oggi

Il contratto nasce direttamente dall'operatore. Nessuna entità nuova, nessun flusso di
proposta. Eventuali documenti di trattativa restano fuori sistema (PDF, email).

**Pro**: zero lavoro.

**Contro**: negoziazione non tracciata; nessuna gestione di proposte rifiutate; asimmetria
nel modello (il preventivo ha il suo flusso tracciato, il contratto no, anche se la
negoziazione di un contratto è in genere più complessa).

### 3.2 Opzione (b) — Allegare il preventivo al contratto

FK opzionale `contratti.preventivo_riferimento_id` per "citare" un preventivo come proposta
di partenza del contratto.

**Contro decisivi**: uso semanticamente improprio del preventivo (proposta di transazione,
non di condizioni); non risolve il problema del *contenuto* (un preventivo lista articoli,
un contratto è un quadro condizioni); introduce un bivio non chiaro nel ciclo di vita del
preventivo. **Scartata** come pezza semantica.

### 3.3 Opzione (c) — `offerta_commerciale` come entità separata — **SCELTA**

Nuovo dominio specchio del preventivo, ma per le condizioni quadro. Decisione presa
2026-05-23. La forma concreta è dettagliata in §5 (tutte le decisioni di modello chiuse).
In sintesi:

- Tabella `vendite.offerte_commerciali` (testata) + `vendite.offerte_commerciali_eccezioni`
- Stati: BOZZA → EMESSA → ACCETTATA / RIFIUTATA (+ marcatura "scaduta" non bloccante)
- All'accettazione: `push_a_contratto` 1:1 → contratto in DRAFT
- Revisioni offerta come per i preventivi (`fn_crea_revisione_*`)

**Motivazione della scelta**:

- Il preventivo è già al posto suo (transazione puntuale → commessa) e non va disturbato.
- Il contratto presuppone una proposta di condizioni: oggi non c'è, va creata.
- Il pattern preventivo è già rodato e riusabile per scaffolding rapido dell'offerta.
- La simmetria del modello rende il sistema più prevedibile per operatori e sviluppatori.

(a) resta ammissibile solo come stato transitorio finché (c) non è implementata.

---

## 4. Riepilogo simmetria dei due assi

Il modello commerciale di ZeroERP tiene **strutturalmente separati** due assi (coerente con
[analisi-pratiche-domini-anello3.md](analisi-pratiche-domini-anello3.md)
§11.0.1):

| Asse                     | Sorgente            | Destinazione      | Snapshot                 | Natura riga ammessa                  |
| ------------------------ | ------------------- | ----------------- | ------------------------ | ------------------------------------ |
| **Transazione puntuale** | Preventivo          | Ordine / Commessa | Prezzo riga-per-riga     | `BENE_FISICO`, `SERVIZIO_UNA_TANTUM` |
| **Condizioni quadro**    | Offerta commerciale | Contratto         | Versione listino fissata | `SERVIZIO_RICORRENTE`                |

La ricorrenza viaggia **solo** sull'asse offerta→contratto, per costruzione: una riga
`SERVIZIO_RICORRENTE` in un preventivo è un errore commerciale (vedi documento pratiche
§11.0.1). I due assi non si incrociano: un preventivo non evolve in offerta (§5.7), e
un'offerta non genera ordini (vedi §4.1).

### 4.1 L'offerta non genera ordini

Chiarimento emerso in sessione 2026-05-22/23. **L'offerta commerciale non ha legame diretto
con gli ordini.** La catena è:

```
offerta → contratto → (nel tempo) → ordini/fatturazioni alle condizioni del contratto
```

L'ordine resta **a sé stante**: è figlio di una transazione concreta, non dell'offerta.
L'offerta stabilisce *condizioni*; il contratto le *incarna* nel tempo; gli ordini
successivi *eseguono* transazioni a quelle condizioni. Il legame, se serve, è
"questo ordine applica le condizioni del contratto X", non "questo ordine nasce
dall'offerta Y".

Distinzione sul *chi origina*: l'offerta e il preventivo sono **proposte dell'azienda** verso
il cliente (il cliente *risponde*, accetta/rifiuta). L'ordine è tendenzialmente **un'azione
del cliente** ("voglio comprare") o un automatismo contrattuale. Questo rafforza
l'autonomia dell'ordine rispetto all'offerta.

> **Da verificare in fase di modello ordini sotto contratto** (fuori scope di questo
> documento): l'"ordine ricorrente" sotto contratto — chi lo emette materialmente (cliente
> dal portale B2B? job di fatturazione periodica del canone? operatore?). Se è un
> automatismo periodico, probabilmente *non* è un ordine ma un ciclo di fatturazione del
> contratto, concetto diverso che non va chiamato "ordine".

---

## 5. Decisioni di modello — TUTTE CHIUSE (2026-05-23)

Le decisioni sono divise in **strutturali** (cambiano la forma dello schema; prese
nell'ordine 5.1 → 5.3 → 5.2 perché ciascuna vincola la successiva) e **di policy**
(configurabili/derivate, a basso rischio di ripensamento). Tutte le decisioni di policy
seguono la stessa postura: **decisione umana ora, automatismo additivo in futuro**, mai
incardinare l'automatismo nello schema v1.

### 5.1 Granularità — offerta 1:1 contratto (grana fine)

**Decisione**: un'offerta commerciale genera **un solo contratto** (legame 1:1). Il caso
"pacchetto multi-condizione" (es. luce+gas+manutenzione per lo stesso cliente) **non** si
modella come offerta 1:N contratti, ma come *raggruppamento* futuro sopra N offerte 1:1
(vedi §5.1-bis).

**Motivazione**: il modello 1:N diretto romperebbe l'idempotenza e la simmetria proprio nel
punto più delicato (`push_a_contratto`). Caso critico: offerta accettata, push genera 3
contratti, il terzo fallisce a metà → l'offerta finisce in uno stato "accettata
parzialmente eseguita" che richiede una macchina a stati di esecuzione parziale dentro
l'offerta. È lo stesso pasticcio che nel documento pratiche è stato evitato per il
preventivo misto. Inoltre `push_a_contratto` perderebbe l'idempotenza "una sorgente → una
destinazione" (pattern A di §6.9.3 dell'analisi pratiche) e dovrebbe passare al pattern B
con chiave di disambiguazione.

Il modello scelto:

```
offerta (BA, scope) ──push 1:1──> contratto

pacchetto_commerciale ──raggruppa──> N offerte ──> N contratti
   (testata leggera, FUTURO)         (1:1 ciascuna)
```

Il legame elementare resta 1:1, idempotente, simmetrico con preventivo→commessa. Coerente
con l'asse `OFFERTA_QUADRO` delle pratiche: una pratica → un'offerta → un contratto, lineare.

### 5.1-bis Estensione futura a pacchetto — vincoli del v1 (grana fine)

> **Sezione introdotta 2026-05-23.** Fissa due discipline a **costo zero oggi** che rendono
> il futuro pacchetto un'aggiunta additiva (mezza giornata) invece di un refactor del
> nucleo (giorni + migrazione dati). È la copertura corretta del "parto mono-contratto ma
> mi tengo aperta la porta" richiesto in sessione.

**Il dimensionamento del refactor futuro dipende interamente da queste due scelte di v1.**

**Disciplina 1 — la FK sta sul contratto, non sull'offerta**:
`contratti.offerta_id` (FK con UNIQUE per l'idempotenza pattern A). Il contratto punta
all'offerta. **Mai** pensare all'offerta come "contenitore" di contratti: l'offerta è la
proposta di *una* singola condizione quadro.

**Disciplina 2 — l'offerta È la condizione, non la trattativa**: in v1 offerta = condizione
= (futuro) contratto coincidono perché c'è una sola offerta per trattativa. Ma il concetto
"trattativa col cliente" **non** è l'offerta: è una coincidenza temporanea del v1. Le
eccezioni proposte (§5.2) si attaccano all'offerta-intesa-come-condizione, quindi sono già
nel posto giusto se domani arriva il pacchetto.

**Dimensionamento del refactor pacchetto con grana fine rispettata** (anello esterno puro):

```
+ tabella pacchetto_commerciale (testata leggera: cliente, data, stato, descrizione)
+ colonna offerte_commerciali.pacchetto_id (FK NULLable)
+ funzione di orchestrazione "accetta pacchetto = accetta le N offerte" (loop sopra push 1:1)
```

`push_a_contratto` **non si tocca**, la macchina a stati dell'offerta **non si tocca**, il
giornale **non si tocca**, nessuna migrazione dati (le offerte esistenti hanno
`pacchetto_id = NULL` = pacchetti impliciti da una sola offerta).

> **Quando fare il pacchetto subito invece che dopo**: solo se si sa *già adesso* che la
> stragrande maggioranza delle trattative reali è multi-condizione. In quel caso non
> sarebbe disciplina concentrica ma rinvio di un pezzo di nucleo. Decisione di sessione:
> si parte mono-contratto (il multi-condizione non è la norma certa), grana fine come
> copertura.

### 5.3 Listino di riferimento — versione fissata all'emissione

**Decisione**: l'offerta **fissa la versione del listino al momento dell'emissione**. Se il
listino cambia versione prima dell'accettazione, l'offerta **si riemette come revisione**
(rev.2 che eredita tutto, aggiorna il riferimento listino e manda in stato SUPERATA la
rev.1, pattern `fn_crea_revisione_*` già usato sui preventivi). La via "listino mobile alla
data di accettazione" è **scartata**.

**Motivazione**: tra emissione e accettazione passano **settimane/mesi** (dato di dominio
confermato in sessione). In quella finestra il listino cambierà spesso versione. La via
mobile significherebbe che il cliente firma una cosa e ne ottiene un'altra (accetta a giugno
condizioni mostrate a marzo, con prezzi diversi): commercialmente insostenibile, legalmente
fragile, e renderebbe l'offerta non tracciabile come documento — annullando il motivo stesso
della sua introduzione. La riemissione-come-revisione dà tracciabilità piena con rilavoro
minimo (il cliente riceve la rev.2 e accetta quella).

Coerente con §3-bis-A dei contratti: contratto = snapshot versione listino; l'offerta fissa
la versione *a monte*, il contratto generato eredita uno snapshot coerente.

### 5.2 Eccezioni proposte — l'offerta porta le eccezioni

**Decisione**: l'offerta porta le proprie eccezioni proposte (OVERRIDE / ESCLUSIONE /
AGGIUNTA) in tabella `vendite.offerte_commerciali_eccezioni`, **specchio di
`contratti_righe`**. Alla `push_a_contratto`, le eccezioni si copiano riga-per-riga in
`contratti_righe` senza reinterpretazione.

**Motivazione (lega §5.2 e §5.3 in un'unica logica)**: dato che l'offerta vive mesi e
**deve congelare cosa è stato proposto** (§5.3), deve avere un corpo che fissa la proposta —
altrimenti non c'è niente da congelare. La trattativa "varia caso per caso": a volte solo
listino + sconto globale, a volte anche eccezioni puntuali. Su una finestra di mesi, le
eccezioni puntuali **sono parte di ciò che il cliente accetta esplicitamente**; non si
possono rimandare al contratto post-creazione.

**Il "varia caso per caso" si gestisce gratis**: un'offerta con **zero eccezioni** *è* il
caso "solo listino + variazione globale"; un'offerta con eccezioni popolate è il caso
complesso. Una struttura sola, due usi. Non si paga nulla in più per supportare entrambi.

**Costo accettato e disciplina di mitigazione**: offerta e contratto avranno entrambi le
eccezioni (duplicazione strutturale). È **strutturalmente necessario** (l'offerta non può
non congelarle) e si tiene sotto controllo con disciplina: **una sola definizione semantica
delle eccezioni**, condivisa come tipo tra offerta e contratto; `push_a_contratto` fa copia
1:1 senza reinterpretare. Mai due semantiche divergenti (anti-pattern `ext_preventivo`,
documento pratiche §2.3).

### 5.4 Workflow di accettazione — contratto sempre in DRAFT

**Decisione**: l'accettazione dell'offerta (registrata dall'**operatore**; nessun
meccanismo cliente-facing in v1, il portale B2C è futuro) genera **sempre un contratto in
DRAFT**. L'operatore lo rifinisce e lo attiva esplicitamente.

**Motivazione**: "creare il contratto" e "attivarlo" sono due transizioni distinte.
L'eventuale algoritmo futuro di auto-attivazione si innesta come passo *dopo* la creazione,
senza toccare `push_a_contratto` (che fa una cosa sola: crea DRAFT). L'algoritmo futuro
decide solo "chiamo o no il passo di attivazione".

**Conseguenza sull'ossatura pratiche**: il parametro `stato_contratto_creato` in
`handler_params` (documento pratiche §11.2.3) resta nello schema come predisposizione ma in
v1 ha un solo valore (`DRAFT`). Configurabilità predisposta, non esercitata, finché non
arriva il caso reale.

### 5.5 Cessazione retroattiva / recesso — offerta immutabile, recesso = cessazione contratto

**Decisione**: l'offerta è uno **storico immutabile post-accettazione**. Un'offerta
ACCETTATA resta ACCETTATA per sempre (ha fatto il suo dovere: ha generato un contratto). Il
recesso del cliente entro N giorni si gestisce come **cessazione del contratto generato**,
con **causale di cessazione dedicata** (es. `RECESSO`) nel flusso contratti già esistente
(DRAFT → ATTIVO → CESSATO). Nessun meccanismo di recesso sull'offerta.

**Motivazione**: il recesso è un evento nella vita del *contratto*, non un ripensamento
sull'offerta. Modellare il recesso come concetto autonomo dell'offerta (es.
`offerta.stato = RECESSA`, o una logica che "riapre" l'offerta) violerebbe l'immutabilità
post-accettazione e sarebbe lavoro nuovo *e* sbagliato. Con la causale di cessazione il
recesso è "gestito" (chi recede, cessa il contratto, la causale lo dichiara) senza aggiungere
complessità all'offerta.

**Unica verifica operativa**: le causali di cessazione del contratto devono includere
`RECESSO` tra i valori. È un **seed**, non un modello.

> **Aggiornamento 2026-05-23 — dipendenza scoperta in fase di brief DB**: la verifica
> diretta su `docs/it/dbzero/config/tabelle/` ha mostrato che la tabella
> `config.causali_cessazione_contratto` **non esiste oggi** in ZeroErp. La cessazione
> contratto è gestita data-driven via `vendite.contratti.validita` daterange +
> `is_abortito_snapshot`, senza tassonomia di causali. Quindi quello che §5.5 chiama
> "un seed" è in realtà l'introduzione di una nuova tassonomia + una colonna
> `contratti.causale_cessazione_id` + il retrofitting del meccanismo di cessazione
> esistente per leggerla. È **scope creep** rispetto al brief offerta (vedi
> [analisi-offerta-commerciale-db.md](../work-done/analisi-offerta-commerciale-db.md) §2.4 nota
> "Causale RECESSO rimossa dal brief offerta").
>
> **Decisione conseguente**: in v1 il recesso si gestisce con i meccanismi di
> cessazione contratto già esistenti (data fine validità), **senza causale dedicata**.
> L'offerta resta immutabile post-accettazione come previsto: il recesso è un evento
> del contratto, non dell'offerta. L'introduzione di `causali_cessazione_contratto` +
> causale `RECESSO` resta valida come decisione di modello, ma diventa un **brief DB
> separato** futuro (es. `brief-db-causali-cessazione-contratto.md`), da pianificare
> indipendentemente dal brief offerta. Nessun blocco per il rilascio offerta v1.
>
> **Predisposizione futura (non v1)**: se servirà che il *sistema* sappia "questo contratto
> è ancora nella finestra di recesso di N giorni" e lo segnali, sarà una feature del
> *contratto* (un campo data + un calcolo), non dell'offerta. Non in v1.

### 5.6 Numerazione e validità — scadenza come avviso non bloccante

**Decisione validità/scadenza**: alla scadenza (es. `validita_al` superata), l'offerta
**non cambia stato in automatico**. Viene **marcata come "scaduta"** a livello di
segnalazione UI/avviso, ma **resta accettabile** finché l'operatore non decide di chiuderla.
Nessun job notturno che cambia stato in v1.

**Motivazione**: due vantaggi. (1) Niente macchinario automatico che muta stato su dati
commerciali delicati: la scadenza è un *attributo calcolato* (`validita_al < oggi` →
"scaduta") più una segnalazione, stesso pattern della marcatura UI delle sorgenti annullate
(documento pratiche §5.7). (2) Disinnesca il conflitto col listino mobile: scadenza-bloccante
e "se il listino cambia si riemette" si pesterebbero i piedi; scadenza-come-avviso li fa
convivere — l'operatore vede "offerta scaduta E listino cambiato" e decide in un colpo solo
se riemettere (rev.2 con listino aggiornato, che resetta anche la validità) o lasciar
perdere. L'umano fa la sintesi, il sistema informa. Porta aperta agli automatismi futuri.

**Decisione numerazione**: serie dedicata `OFC-*`, simmetrica a `PRV-*` dei preventivi,
coerente con la convenzione di naming.

### 5.7 Relazione con preventivo — assi separati, nessuna evoluzione

**Decisione**: un preventivo **non evolve** in offerta commerciale. Sono entità separate per
costruzione (transazione puntuale vs condizioni quadro, vedi §4). Se il cliente vuole
condizioni quadro, si emette una **nuova offerta**; il preventivo resta per la sua vita
transazionale. Conferma di quanto già propendeva l'analisi iniziale, coerente con la
separazione dei due assi ribadita in §2.1 e §4.

---

## 6. Sintesi decisioni (tabella di navigazione)

| §       | Tema                 | Decisione                                                                                                                           | Tipo                     |
| ------- | -------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| 3.3     | Strada               | Opzione (c): `offerta_commerciale` come dominio separato                                                                            | Fondante                 |
| 5.1     | Granularità          | Offerta **1:1** contratto. Pacchetto = raggruppamento futuro additivo                                                               | Strutturale              |
| 5.1-bis | Grana fine           | FK su `contratti.offerta_id` (UNIQUE); eccezioni a grana condizione. Refactor pacchetto = additivo (mezza giornata)                 | Strutturale (vincolo v1) |
| 5.3     | Listino              | Versione **fissata all'emissione**; cambio prima dell'accettazione = revisione (rev.2 supera rev.1). Mobile scartato                | Strutturale              |
| 5.2     | Eccezioni            | Offerta **porta le eccezioni** (`offerte_commerciali_eccezioni`, specchio `contratti_righe`). Zero eccezioni = caso semplice gratis | Strutturale              |
| 5.4     | Accettazione         | Contratto sempre **DRAFT**, attiva l'operatore. Auto-attivazione = futura, additiva                                                 | Policy                   |
| 5.5     | Recesso              | Offerta **immutabile** post-accettazione. Recesso = cessazione contratto con causale `RECESSO` (seed)                               | Policy                   |
| 5.6     | Scadenza/numerazione | Scadenza = **avviso non bloccante** (attributo calcolato + segnalazione). Numerazione `OFC-*`                                       | Policy                   |
| 5.7     | Vs preventivo        | Nessuna evoluzione preventivo→offerta. Assi separati                                                                                | Policy                   |
| 4.1     | Vs ordini            | Offerta **non genera ordini**. Catena offerta→contratto→ordini. Ordine a sé stante                                                  | Chiarimento              |

---

## 7. Stato e prossimi passi

- ✅ **DECISO** — opzione (c) confermata, tutte le decisioni di modello §5 chiuse
  (2026-05-23).
- ⏳ Prossimi passi, nell'ordine:
  1. **Brief DB** `brief-db-offerta-commerciale.md` con schema completo:
     - `vendite.offerte_commerciali` (testata): `billing_account_id`, scope, listino di
       riferimento + versione fissata, variazione globale proposta, validità, stato
       (BOZZA → EMESSA → ACCETTATA / RIFIUTATA), numerazione `OFC-*`, gestione revisioni.
     - `vendite.offerte_commerciali_eccezioni` (specchio `contratti_righe`).
     - `contratti.offerta_id` (FK + UNIQUE, idempotenza pattern A — §5.1-bis).
     - `vendite.fn_push_offerta_a_contratto` (specchio di `push_a_commessa`, crea contratto
       DRAFT, copia eccezioni 1:1, idempotente per costruzione — vedi documento pratiche
       §6.9 e §11.2.4).
     - `fn_crea_revisione_offerta` (pattern preventivi, per il caso listino cambiato — §5.3).
     - Seed causale `RECESSO` nelle causali di cessazione contratto (§5.5).
     - Codice errore `E_OFFERTA_CONTRATTO_GIA_GENERATO` in `config.messaggi_errore.csv`.
     - Seed sorgente `OFFERTA_COMMERCIALE` in `config.sorgenti` (singolare maiuscolo).
     - pgTAP: push 1:1 + idempotenza (doppia invocazione → errore semantico, nessun
       contratto duplicato).
  2. **Piano operativo BE + FE**: `apps/vendite/services/offerte_service.py`, drawer
     `OffertaDrawer.vue` (scaffolding sul pattern preventivo), i18n.
  3. **Doc reference** `modello-offerta-commerciale.md` del nuovo dominio.
  4. **Sblocco asse pratiche**: solo dopo l'esistenza di `vendite.offerte_commerciali` come
     tabella popolabile si può scrivere il runtime end-to-end di `OFFERTA_QUADRO`
     (documento pratiche §11.2.5).

---

## 8. Cosa resta fuori scope di questo documento

- **Brief DB dettagliato**: questo documento chiude il *modello*, non lo schema DDL. Il
  brief è il deliverable successivo (§7).
- **Pacchetto commerciale multi-contratto**: predisposto come additivo (§5.1-bis), non
  costruito in v1.
- **Portale cliente-facing / accettazione B2C**: l'accettazione è dell'operatore in v1 (§5.4).
- **Auto-attivazione contratto e algoritmi di scadenza**: predisposizioni future, non v1
  (§5.4, §5.6).
- **Modello degli ordini sotto contratto**: l'offerta non li tocca (§4.1); chi/come emette
  gli ordini ricorrenti è materia di un'analisi separata.

---

## 9. Riferimenti incrociati

- [analisi-pratiche-domini-anello3.md](analisi-pratiche-domini-anello3.md)
  — asse `OFFERTA_QUADRO` (§11.2, ossatura pratica in attesa di questo dominio); separazione
  dei due assi commerciali (§11.0.1); idempotenza cross-dominio (§6.9).
- [`refactor-contratti-modalita.md`](../work-done/refactor-contratti-modalita.md) — refactor
  contratti corrente; questa analisi è uscita dalla sua §3-bis-A.
- [`recap-contratti-post-componenti.md`](../work-done/recap-contratti-post-componenti.md) — recap
  bug contratti post-componenti, contesto operativo.
- `api_preventivi.md` — modello preventivi esistente, riferimento per pattern riusabile.
- `push_a_commessa` ([preventivi_service.py:1910](../../../../backend/apps/vendite/services/preventivi_service.py#L1910)) —
  flusso accettazione che ispira `push_a_contratto`.

---

*Analisi offerta commerciale — ZeroERP. Decisioni di modello §5 chiuse 2026-05-23.
Prossimo deliverable: brief DB. Documento vivo, da aggiornare alla scrittura del brief.*