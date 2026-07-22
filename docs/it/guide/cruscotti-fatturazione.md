# Guida — Cruscotti fatturazione (le tre lenti)

> **Ultima revisione**: 22 luglio 2026 — nuova **§7 «Gestire la fatturazione»**:
> la Lente 1 non è più solo una fotografia, da lì si **agisce** (approva →
> fattura → rendi definitive), con il perché la numerazione resta un passo
> separato e cosa fa il sistema da solo. Revisione precedente (8 luglio):
> Situazione aperta v2 (serbatoio pre-commessa), donut per fase, filtro "aperti
> da oltre N giorni" solo-lista, via il concetto *transitato*.
>
> **Destinatari**: analisti funzionali, operatori vendite/amministrazione,
> sviluppatori backend/frontend.
>
> **Vedi anche** — viste DB:
>
> * [vendite.vw_dash_competenza_mensile](/dbzero/vendite/manual/vw_dash_competenza_mensile) / [vw_dash_competenza_attivita](/dbzero/vendite/manual/vw_dash_competenza_attivita) / [vw_dash_competenza_errori](/dbzero/vendite/manual/vw_dash_competenza_errori)
> * [vendite.vw_dash_backlog_riepilogo](/dbzero/vendite/manual/vw_dash_backlog_riepilogo) / [vw_dash_backlog_documenti](/dbzero/vendite/manual/vw_dash_backlog_documenti)
> * [vendite.vw_dash_aperto_riepilogo](/dbzero/vendite/manual/vw_dash_aperto_riepilogo) / [vw_dash_aperto_documenti](/dbzero/vendite/manual/vw_dash_aperto_documenti)
>
> **Vedi anche** — API backend:
>
> * [API Competenza fatturazione](/backend/vendite/manual/api_dashboard_competenza)
> * [API Backlog fatturazione](/backend/vendite/manual/api_dashboard_backlog)
> * [API Situazione aperta](/backend/vendite/manual/api_dashboard_aperto)
>
> **Vedi anche** — guide correlate:
>
> * [Fatturazione end-to-end](/guide/fatturazione) — la pipeline che le lenti osservano
> * [Gestione Commesse](/guide/gestione-commesse) — lo snodo tra il "prima" e il "dopo"
> * [Gestione Preventivi](/guide/gestione-preventivi) / [Offerte commerciali](/guide/gestione-offerte-commerciali) / [Ordini](/guide/gestione-ordini) / [Contratti](/guide/gestione-contratti) — le aree che alimentano gli aperti

---

## 1. Le tre lenti in una riga

I cruscotti fatturazione guardano **lo stesso insieme** — il lavoro di vendita
ancora aperto verso la fatturazione — da **tre angolazioni** complementari. Non
sono tre report ridondanti: ognuna risponde a una domanda che le altre non
risolvono.

| Lente | Rotta | Domanda a cui risponde | Taglio | Misura |
| --- | --- | --- | --- | --- |
| **Competenza** | `/vendite/dashboard-competenza` | *Cosa va fatturato per questo mese, e quanto è coperto?* | per **mese di competenza** (funnel commessa → fattura) | euro |
| **Backlog** | `/vendite/dashboard-backlog` | *Cosa è fermo, da quanto, e cosa serve per sbloccarlo?* | per **anzianità + azionabilità** (solo il non-verde) | euro / conteggi |
| **Situazione aperta** | `/vendite/situazione-aperta` | *Dove sono tutti gli aperti, in che fase?* | per **fase** (fotografia, senza asse temporale) | euro / conteggi |

Regola pratica: **Competenza** guarda *nel tempo*, **Backlog** guarda *cosa fare
ora*, **Situazione aperta** guarda *dove siamo*.

---

## 2. Il concetto comune: il lavoro aperto

Tutte e tre partono dagli stessi mattoni.

### 2.1 Le quattro aree documento

Il "lavoro aperto" vive in quattro aree del ciclo vendite, nell'ordine del
funnel:

`PREVENTIVI` → `ORDINI` → `OFFERTE` → `CONTRATTI`

Sono i documenti che, una volta conclusi, alimentano la **commessa** e quindi la
**fatturazione**. Le commesse e le attività fatturabili stanno *a valle*: le
guarda la Lente Competenza.

### 2.2 Le fasi normalizzate

Ogni documento, qualunque sia il suo stato specifico di area, viene proiettato su
un vocabolario **comune di fasi** (da `config.stati_doc_*.fase`), nell'ordine
della maturità verso la commessa:

| Fase | Significato | Colore |
| --- | --- | --- |
| `APERTO` | in lavorazione interna (bozza) | grigio |
| `IN_ATTESA` | palla al cliente (emesso, attende risposta) | azzurro |
| `IN_CORSO` | avanzato, non ancora concluso | arancio |
| `CHIUSO` | concluso (accettato/evaso o rifiutato/annullato) | verde |

La proiezione a fase comune è ciò che permette di **confrontare aree diverse**
sulla stessa scala.

### 2.3 Misura mista (euro vs conteggi)

Non tutte le aree si misurano in euro in modo confrontabile: `PREVENTIVI` e
`ORDINI` portano un **valore in euro** sensato; `OFFERTE` e `CONTRATTI` si
leggono meglio a **conteggio di documenti**. La scelta della misura è **decisa
dal backend** nel payload (valore assente = area a conteggi): il frontend legge,
non ridecide.

### 2.4 Revisione attiva

Preventivi e offerte possono essere **revisionati**. In ogni cruscotto conta
**solo la revisione attiva** del documento: le revisioni superate non compaiono
come lavoro aperto. Il concetto di revisione attiva è descritto nelle guide di
[Gestione Preventivi](/guide/gestione-preventivi) e
[Offerte commerciali](/guide/gestione-offerte-commerciali).

### 2.5 Ambito emittente (scope)

Ogni operatore vede **solo i documenti degli emittenti fiscali a cui è
abilitato**. Il filtro è applicato interamente dal database (RLS in modalità
invoker sulle viste): i cruscotti non ricevono né passano l'identità utente, e
non c'è modo di aggirare l'ambito dal frontend.

---

## 3. Lente 1 — Competenza

**Rotta**: `/vendite/dashboard-competenza` · **Domanda**: *cosa va fatturato per
il mese, e quanto è già coperto?*

È la lente **temporale**. Parte dalla **commessa** e segue il funnel fino alla
fattura, mese per mese di competenza. Per il mese selezionato mostra:

- una card **Copertura mese**: quota già fatturata rispetto al totale di
  competenza;
- il funnel per **stadio**, nell'ordine commessa → fattura:
  `Da approvare` → `Da emettere` → `Emesse non fatturate` → `Fatturate`;
- l'evidenza degli **errori vivi** di fatturazione nel mese.

**Quando usarla**: a fine/inizio mese, per capire quanto del competenza è stato
fatturato e cosa manca per chiudere il mese.

---

## 4. Lente 2 — Backlog

**Rotta**: `/vendite/dashboard-backlog` · **Domanda**: *cosa è fermo, da quanto
tempo, e cosa serve per sbloccarlo?*

È la lente **dell'azione**. Non fotografa tutto: isola **solo il non-verde** —
ciò che è fermo e richiede un intervento — ordinandolo per **anzianità** (il più
vecchio prima). Ogni voce porta:

- una **classe di azionabilità**, con la relativa azione suggerita:
  - `Da recuperare` (recuperabile con un'azione interna),
  - `Sollecito cliente` (dipende da una risposta del cliente),
  - `Anomalie` (situazione irregolare da investigare);
- il **motivo del fermo** e da **quanti giorni** è in quello stato.

**Quando usarla**: come coda di lavoro quotidiana — cosa sbloccare adesso,
partendo dalle situazioni più vecchie e dalle anomalie.

---

## 5. Situazione aperta — serbatoio pre-commessa

**Rotta**: `/vendite/situazione-aperta` · **Domanda**: *dove sono tutti gli
aperti, in che fase?*

È la lente **di posizione**. Fotografa il **serbatoio pre-commessa**: tutti i
documenti aperti che, se conclusi, andrebbero in commessa/fatturazione ma non ci
sono ancora arrivati — **senza asse temporale** e includendo anche gli aperti
"fisiologici" (che il Backlog esclude perché non richiedono azione). Mostra:

- una **card per area** con un **donut a spicchi per fase** (`APERTO` /
  `IN_ATTESA` / `IN_CORSO`): a colpo d'occhio, quanto lavoro è in ciascuna fase
  di maturità verso la commessa. La fase `CHIUSO` è fuori perimetro (non è più
  "aperto");
- una **lista** dei documenti ordinata per "in essere da" (i più vecchi prima),
  con la colonna **Aperto da N giorni**;
- un filtro **"Aperti da oltre N giorni"** (30/60/90): agisce **solo sulla
  lista** — le card restano la fotografia completa del serbatoio.

**Quando usarla**: per la visione d'insieme — quanti aperti ci sono, in che fase,
quanto sono invecchiati — a prescindere dal mese e dall'urgenza di azione.

---

## 6. Come si distinguono (e perché tre)

Le tre lenti condividono l'insieme (il lavoro aperto) ma lo tagliano in modo
diverso, e coprono momenti diversi della pipeline:

```text
   preventivi / ordini / offerte / contratti  -->  COMMESSA  -->  attivita fatturabili  -->  FATTURA
   |__________________________________________|    |_______________________________________________|
                    |                                                    |
          SITUAZIONE APERTA                                        COMPETENZA
     (serbatoio pre-commessa, per fase)                     (funnel per mese di competenza)

          BACKLOG: attraversa tutta la pipeline, ma tiene solo il non-verde
                   (cio che e fermo e va sbloccato), per anzianita
```

- **Situazione aperta** sta **a monte**: il serbatoio da cui nasce la commessa,
  tutti gli aperti, per fase.
- **Competenza** parte **dalla** commessa: cosa è di competenza del mese e a che
  punto è del funnel verso la fattura.
- **Backlog** **attraversa** la pipeline ma tiene **solo il non-verde**: la coda
  di ciò che è fermo e va sbloccato, per anzianità.

Detto in modo operativo: la stessa fornitura può comparire in **Situazione
aperta** (mentre è un preventivo emesso in attesa), passare in **Competenza**
(quando la commessa entra nel mese) e affacciarsi in **Backlog** (se si blocca e
serve un'azione). Non sono duplicati: sono tre domande diverse sullo stesso
lavoro.

---

## 7. Gestire la fatturazione (agire dalla Lente 1)

Le altre lenti sono **fotografie**: si guardano, poi si va altrove a lavorare. La
**Lente 1 — Competenza** no: da lì si **agisce**. I pulsanti stanno sulle card del
funnel, così l'azione è sempre accanto al numero che la motiva.

### 7.1 I tre verbi

Si procede da sinistra a destra nel funnel. Ogni verbo agisce sull'**intero mese**
selezionato e chiede sempre conferma, mostrando quante attività coinvolge.

| Verbo | Card | Cosa fa | Serve il permesso |
| --- | --- | --- | --- |
| **Approva** | `Da approvare` | Rende le attività **emettibili**: dice che quel lavoro è buono per essere fatturato | Approvazione attività commessa |
| **Fattura adesso** | `Da emettere` | Crea le fatture del mese e le porta fino a **EMESSA**. Si ferma lì: **non numera** | Generazione fatture/lotti |
| **Rendi definitive** | `Emesse non fatturate` | **Numera** le fatture (atto fiscale) e le manda in stampa | Numerazione fatture/lotti (dedicato) |

Due dettagli che non sono ovvi:

- **«Fattura adesso» è cumulativo**: raccoglie l'arretrato dei mesi precedenti,
  non solo il mese a schermo. Se a maggio era rimasto indietro qualcosa, fatturando
  giugno viene preso anche quello. È voluto: evita che il non fatturato si sedimenti.
- **Approvare non fattura niente.** Approvare significa solo «questo lavoro è
  corretto». La fattura nasce col verbo successivo.

### 7.2 Perché la numerazione è un passo separato

È la domanda che ricorre di più, e la risposta è sostanziale: **numerare è un atto
fiscale irreversibile**.

Finché una fattura è **EMESSA** ha tutti i suoi importi ma **non ha un numero**: si
può ancora correggere, rigenerare, annullare senza lasciare tracce nel registro. Nel
momento in cui viene resa **DEFINITIVA** prende un numero progressivo dal registro,
e quel numero non si riusa e non si buca: da lì in poi si può solo emettere una nota
di credito.

Per questo i due verbi sono **separati, con permessi diversi**: chi prepara le
fatture non necessariamente è chi si assume la responsabilità di numerarle. Un solo
pulsante «fattura e numera» renderebbe impossibile fermarsi a controllare nel punto
in cui il controllo conta.

Regola pratica: **fatturare quando il lavoro del mese è finito, numerare quando i
controlli sono finiti.**

### 7.3 Cosa fa il sistema da solo, cosa fa l'operatore

Buona parte del lavoro avviene **senza che nessuno prema niente**:

| Chi | Quando | Cosa |
| --- | --- | --- |
| **Processo notturno** | ogni notte | esegue il giro di fatturazione automatico; per la corsia **giornaliera** arriva **fino alla numerazione** |
| **Processi di servizio** | ogni minuto | prendono in carico i lavori avviati dalla dashboard e producono i **PDF** delle fatture numerate |
| **Operatore** | quando serve | **anticipa** il giro senza aspettare la notte, **numera** la fatturazione massiva, **sblocca** ciò che si è fermato |

Quindi i verbi della dashboard **non sostituiscono** il processo automatico: lo
anticipano quando serve chiudere il mese senza attendere, e coprono i casi che il
processo notturno lascia deliberatamente all'umano — in primo luogo la numerazione
della fatturazione massiva.

### 7.4 Il lavoro non blocca la pagina

Fatturare o numerare un mese intero può richiedere tempo. Per questo l'azione non
congela lo schermo: viene **messa in lavorazione** e si riceve subito conferma
(«elaborazione in corso»). Si continua a lavorare e l'esito arriva da sé.

Per seguire cosa sta succedendo c'è l'**indicatore in alto a destra**, che mostra
quanti processi sono in corso: cliccandolo si apre il riepilogo, e da lì si arriva a
**Strumenti → Code di lavoro** per il dettaglio completo (cosa è in coda, cosa è
fallito e perché, e la possibilità di rimettere in coda un lavoro bloccato).

Se l'indicatore diventa **rosso**, i processi di servizio non stanno girando: i
lavori restano in attesa e nessuno li perde, ma finché non riparte il servizio non
verranno eseguiti. È il caso in cui vale la pena avvisare chi gestisce il sistema.

### 7.5 Quando qualcosa si ferma

Gli errori vivi del mese compaiono nel **pannello errori** della Lente 1. Da lì il
codice del lotto è **cliccabile** e porta direttamente al lotto interessato, dove si
vedono le fatture, i tentativi già fatti e il motivo del blocco — senza doverlo
cercare a mano nell'elenco dei lotti. Lo stesso collegamento esiste sulle righe già
fatturate del drill-down.

### 7.6 Cosa non si fa ancora da qui

L'**invio allo SDI** non è disponibile dalla dashboard: resta un passo successivo,
gestito fuori da questa schermata. La dashboard copre il percorso
**approvazione → fattura → numerazione → stampa**.

---

## 8. Note tecniche

- **Sorgenti**: ogni lente ha la sua famiglia di viste `vendite.vw_dash_*`
  (competenza / backlog / aperto), esposte da endpoint GET sottili
  (`/api/v1/vendite/dashboard-*`). Nessuna logica di dominio nel frontend: aree,
  fasi, misura, ordinamento e ambito vivono nel database/BE.
- **Ambito emittente**: RLS in modalità invoker sulle viste; il BE non passa
  l'identità utente (vedi §2.5).
- **Misura mista**: decisa dal backend nel payload (valore assente = area a
  conteggi, non una whitelist statica nel frontend) — vedi §2.3.
- **Revisione attiva**: i cruscotti considerano solo la revisione attiva di
  preventivi e offerte (vedi §2.4).
- **Fotografia vs azione**: le card della Situazione aperta non sono filtrate dal
  ritardo (restano una fotografia completa); la soglia "aperti da oltre N giorni"
  agisce solo sulla lista di drill-down.
