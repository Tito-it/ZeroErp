# Guida — Cruscotti fatturazione (le tre lenti)

> **Ultimo aggiornamento**: 31 ottobre 2026
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

| Lente                 | Rotta                           | Domanda a cui risponde                                   | Taglio                                                 | Misura          |
| --------------------- | ------------------------------- | -------------------------------------------------------- | ------------------------------------------------------ | --------------- |
| **Competenza**        | `/vendite/dashboard-competenza` | *Cosa va fatturato per questo mese, e quanto è coperto?* | per **mese di competenza** (funnel commessa → fattura) | euro            |
| **Backlog**           | `/vendite/dashboard-backlog`    | *Cosa è fermo, da quanto, e cosa serve per sbloccarlo?*  | per **anzianità + azionabilità** (solo il non-verde)   | euro / conteggi |
| **Situazione aperta** | `/vendite/situazione-aperta`    | *Dove sono tutti gli aperti, in che fase?*               | per **fase** (fotografia, senza asse temporale)        | euro / conteggi |

Regola pratica: **Competenza** guarda *nel tempo*, **Backlog** guarda *cosa fare
ora*, **Situazione aperta** guarda *dove siamo*.

---

## 2. Il concetto comune: il lavoro aperto

Tutte e tre partono dagli stessi mattoni.

### 2.1 Le aree documento

Il "lavoro aperto" vive in cinque aree del ciclo vendite, nell'ordine del
funnel:

`PREVENTIVI` → `ORDINI` → `DDT` → `OFFERTE` → `CONTRATTI`

Sono i documenti che, una volta conclusi, alimentano la **commessa** e quindi la
**fatturazione**. Il **DDT** sta subito dopo gli ordini perché per una parte
delle vendite è lui il veicolo della fattura: non si fattura alla conferma
dell'ordine ma alla spedizione o alla consegna (vedi §4.1).

A queste se ne aggiungono **due che compaiono solo nel Backlog**, perché non
sono lavoro "in attesa" ma lavoro *fermo*:

| Area       | Dove compare | Perché                                                                                                                                                                                |
| ---------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `COMMESSE` | solo Backlog | la commessa è il **traguardo** del serbatoio, non un documento che lo aspetta. Se però si blocca (attività non approvate o non emesse) è arretrato, e va in coda di lavoro            |
| `RESI`     | solo Backlog | il reso è un flusso **inverso**: non alimenta la commessa, la corregge. Metterlo nel serbatoio significherebbe contarlo due volte, perché il reso riapre da sé il residuo dell'ordine |

Le attività fatturabili e le fatture stanno *a valle*: le guarda la Lente
Competenza.

### 2.2 Le fasi normalizzate

Ogni documento, qualunque sia il suo stato specifico di area, viene proiettato su
un vocabolario **comune di fasi** (da `config.stati_doc_*.fase`), nell'ordine
della maturità verso la commessa:

| Fase        | Significato                                      | Colore  |
| ----------- | ------------------------------------------------ | ------- |
| `APERTO`    | in lavorazione interna (bozza)                   | grigio  |
| `IN_ATTESA` | palla al cliente (emesso, attende risposta)      | azzurro |
| `IN_CORSO`  | avanzato, non ancora concluso                    | arancio |
| `CHIUSO`    | concluso (accettato/evaso o rifiutato/annullato) | verde   |

La proiezione a fase comune è ciò che permette di **confrontare aree diverse**
sulla stessa scala.

### 2.3 Misura mista (euro vs conteggi)

Non tutte le aree si misurano in euro in modo confrontabile: `PREVENTIVI`,
`ORDINI`, `DDT` e `COMMESSE` portano un **valore in euro** sensato; `OFFERTE` e
`CONTRATTI` si leggono meglio a **conteggio di documenti**, e i `RESI` pure —
oggi un reso non porta importi, solo quantità. La scelta della misura è **decisa
dal backend** nel payload (valore assente = area a conteggi): il frontend legge,
non ridecide.

⚠️ Fra ordini e DDT il valore **non si somma**: quando è il DDT a fatturare, la
merce già spedita è contata sul DDT e l'ordine mostra solo ciò che resta da
spedire. È il punto che sorprende di più leggendo le card — spiegato in §5.1.

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

### 3.1 Le quattro caselle non sono quattro passaggi

⚠️ È la domanda che torna più spesso, e le card messe in fila la
alimentano: sembrano un percorso a quattro tappe, ma il percorso vero ne usa
**due**.

| Casella                  | Cosa contiene davvero                                                                                                     |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| **Da approvare**         | lavoro registrato, non ancora dichiarato buono per la fattura                                                             |
| **Da emettere**          | lavoro buono, non ancora in fattura — **è da qui che parte il lotto**                                                     |
| **Emesse non fatturate** | lavoro **in transito o rimasto a metà**: non è un passaggio. Ci convivono quattro situazioni, e solo una chiede un'azione |
| **Fatturate**            | lavoro finito dentro una fattura, numerata o no                                                                           |

Il verbo **Fattura adesso** prende il lavoro e ne fa le righe di fattura **in un
solo passo**: un'attività salta da `Da emettere` dritta a `Fatturate`. Nessuno
transita da `Emesse non fatturate`.

⚠️ **Quella casella non conta una cosa sola, e conviene saperlo prima di
guardarla.** Ci convivono **quattro** situazioni che chiedono rimedi **opposti**:

| Cosa ci trovi                                              | Che cos'è                                                                                                                                            | Cosa devi fare                                                                 |
| ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| lavoro **che aspetta il suo lotto**                        | **transito normale**: succede quando l'emissione e la fatturazione sono due gesti separati, ed è il caso di chi emette in modo mirato e fattura dopo | ⏳ niente: il prossimo giro lo prende da sé                                     |
| lavoro **dentro un giro ancora in corso**                  | il lotto lo sta lavorando **adesso**                                                                                                                 | ⏳ niente: si aspetta che il lotto finisca                                      |
| ⭐ lavoro **rimasto senza la sua fattura**                  | **il residuo**: la fattura c'era ed è stata eliminata                                                                                                | ✅ **«Riporta da emettere»**                                                    |
| 🟠 riga di commessa **senza nessuna attività da fatturare** | **anomalia**: la riga risulta emessa ma non esiste niente da mettere in fattura                                                                      | ⛔ il verbo **non si può proporre** (non c'è niente su cui agire): va segnalata |

**È il terzo caso la spia**, e per un motivo preciso: quel lavoro risulta già
emesso, quindi **nessun giro futuro lo riprenderà**. Resterebbe invisibile per
sempre, se non ci fosse quel contatore.

> ⛔ **«Emessa» qui NON vuol dire «fattura emessa».** È la parola più
> fraintendibile della schermata, e conviene toglierla di mezzo subito:
> **emessa** dice che quel lavoro è stato **preso in carico dalla fatturazione**
> — è entrato in un lotto — non che esista un documento fiscale. Le due cose si
> chiamano uguale e sono diverse: il senso di questa casella è proprio
> *«preso in carico, e un documento non c'è»*.

> 🔴 **E il «lotto di provenienza» può portarti alla fattura di un ALTRO
> cliente.** Un lotto raggruppa il lavoro di più clienti e produce **una fattura
> per ciascuno**: se il tuo residuo è del cliente A e il lotto conteneva anche il
> cliente B, aprendo quel lotto trovi la fattura di B — **numerata e definitiva**,
> e sembra che il tuo lavoro sia già fatturato. Non lo è.
> ⭐ **La verifica che vale un secondo**: guarda il **cliente** sulla riga del
> residuo e confrontalo con l'intestatario della fattura che hai aperto. Se sono
> diversi, quel documento non c'entra col tuo residuo.
> ℹ️ E in ogni caso il programma non ti lascerebbe sbagliare: una riga che sta
> davvero dentro una fattura viva **viene rifiutata**, con un messaggio che ti
> porta ad aprire quella fattura.

> ⚠️ **Un numero in quella casella non è di per sé un allarme.** *Fattura adesso*
> fa emissione e fatturazione in un passo unico, quindi da lì non ci passa mai
> nulla — ma quella è una proprietà del verbo, non della casella: chi emette in
> modo mirato ci vede passare lavoro perfettamente sano. Quello che è un allarme
> è **il numero dei residui**.

**Eliminare una fattura da un lotto rimette in coda il suo lavoro** (§7.6): da quella strada non si creano residui.

⭐ **La casella si legge in chiaro.** Il database distingue le quattro situazioni
una per una, quindi la card **si spezza in due numeri** — quello che chiede
un'azione e quello che chiede solo di aspettare — e l'elenco dei soli **residui**
ha una lista sua, con il lotto da cui ciascuno proviene. Sulla card lo dice una
riga sotto il totale: **«di cui N da recuperare»** con il loro valore, oppure
**«nessuno da recuperare»** quando il lavoro fermo lì è tutto in transito
legittimo.

✅ **E dalla card si recupera.** Cliccando la card si apre l'elenco dei soli
residui: si spuntano le righe da recuperare e si preme **«Riporta da emettere»**
(§7.1).

**Quando usarla**: a fine/inizio mese, per capire quanto della competenza è stato
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

### 4.1 DDT e resi: i motivi da saper leggere

DDT e resi hanno motivi di fermo tutti loro, e alcuni sono **verdi**: compaiono
nell'elenco ma non chiedono niente. Vale la pena sapere quali, perché la
differenza fra «non c'è niente da fare» e «non c'è niente che *tu* possa fare»
non è la stessa cosa.

| Cosa leggi a schermo                                  | Colore | Cosa significa davvero                                                                                                                                                                |
| ----------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| *Fatturazione a carico del DDT (spedizione/consegna)* | 🟢      | L'ordine **non è fermo**: per quella vendita non è lui a fatturare, ma il DDT. Nessuna azione                                                                                         |
| *Merce in viaggio, fatturazione non ancora dovuta*    | 🟢      | Il DDT è partito ma non ha ancora raggiunto lo stato che fa scattare la fattura. Si aspetta, e basta                                                                                  |
| *Push a commessa non eseguito* / *parziale*           | 🟠      | Il DDT **ha superato** quello stato e la fattura non è partita: è in ritardo. Da sbloccare                                                                                            |
| *Ri-consegna da generare*                             | 🟠      | Il cliente ha reso della merce che va rispedita, e finché non la rispedisci la fatturazione resta bloccata. Azione tua                                                                |
| *Merce resa già fatturata — accredito in attesa*      | 🟠      | Il cliente ha reso merce **già fatturata**: gli è dovuto un accredito, che si emette dalla coda accrediti (§8). L'azione suggerita è «Emetti la nota di credito dalla coda accrediti» |

Due domande che nascono guardando l'elenco:

- **Perché un DDT in ritardo sta qui e non nella Situazione aperta?** Perché un
  DDT consegnato è, per il sistema, un documento **concluso**: non sta
  aspettando niente, è in ritardo. La Situazione aperta raccoglie chi aspetta,
  il Backlog chi è fermo.
- **Perché certi DDT non compaiono da nessuna parte?** Perché non tutti i DDT
  fatturano. Quelli emessi a fronte di un ordine che fattura **alla conferma**
  seguono l'ordine — non fattureranno mai loro. E quelli con una causale di
  trasporto non fatturabile (conto visione, riparazione, campionatura,
  omaggio…) sono trasporti, non vendite: restano fuori per costruzione.

### 4.2 Contratti: i due motivi

Un contratto vive a lungo e addebita a ogni periodo (vedi la
[guida dei contratti §4-bis](/guide/gestione-contratti#4-bis-come-il-contratto-si-addebita-una-tantum-e-canoni)):
qui compare solo quando c'è qualcosa da fare **adesso**.

| Cosa leggi a schermo | Colore | Cosa significa davvero |
| --- | --- | --- |
| *Contratto con addebiti maturati non ancora in commessa* | 🟠 | Un canone (o la una tantum, o lo storno di una cessazione) è maturato e non è ancora in commessa. L'azione è «Esegui il push dei canoni»: dopo il push il contratto esce dall'elenco, e ci torna quando matura il periodo dopo |
| *Contratto con un canone che non può partire* | 🔴 | Una riga a canone (o una quota fissa del listino) non ha la periodicità, oppure il listino non ha un prezzo alla data: il push la salta e la salterà sempre. L'azione è «Rivedi il contratto». Le righe di un contratto attivo non si modificano: il rimedio è un contratto nuovo, o il prezzo nel listino quando manca quello |

Se un contratto ha tutte e due le cose, vince il rosso: il push da solo non lo sblocca.
L'anzianità parte dall'addebito più vecchio che aspetta (per il canone che non può partire,
dall'inizio del contratto). Anche un contratto **cessato** compare qui, se ha ancora uno storno
da mandare.

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

Un **contratto** è nel serbatoio finché è in bozza, e da attivo solo quando ha un addebito
maturato da mandare in commessa (o un canone che non può partire, §4.2). Un contratto attivo
con tutto in commessa **non** compare: come un ordine tutto in commessa, non aspetta niente.
Ci torna quando matura il periodo dopo.

### 5.1 L'ordine mostra quello che resta da spedire (non sempre)

È la cosa che più spesso fa pensare a un errore, e non lo è.

Quando una vendita fattura **alla spedizione o alla consegna**, la merce già
partita è in carico al DDT. L'ordine, nel serbatoio, porta allora solo il
**residuo da spedire**:

> Ordine da **1.000 €**, spedita merce per **600 €**.
> Il serbatoio mostra l'ordine a **400 €** — i 600 vivono sul DDT.
> Se li sommassi vedresti 1.600 € per una vendita che ne vale 1.000.

Quando invece la vendita fattura **alla conferma dell'ordine**, il DDT che ne
nasce non fatturerà mai: lì il valore pieno resta sull'ordine.

> Stesso ordine da **1.000 €**, stessa merce spedita.
> Il serbatoio mostra l'ordine a **1.000 €**, e il DDT non compare.

Quindi due card ordini possono comportarsi in modo opposto ed essere **entrambe
giuste**: dipende da quando quella vendita fattura. La card lo ricorda con un
suggerimento in linea; se un numero non torna, la prima cosa da guardare è
questa.

---

## 6. Come si distinguono (e perché tre)

Le tre lenti condividono l'insieme (il lavoro aperto) ma lo tagliano in modo
diverso, e coprono momenti diversi della pipeline:

```text
   preventivi / ordini / DDT / offerte / contratti -->  COMMESSA --> attivita fatturabili --> FATTURA
   |_______________________________________________|    |______________________________________________|
                    |                                                    |
          SITUAZIONE APERTA                                        COMPETENZA
     (serbatoio pre-commessa, per fase)                     (funnel per mese di competenza)

          BACKLOG: attraversa tutta la pipeline, ma tiene solo il non-verde
                   (cio che e fermo e va sbloccato), per anzianita
                   -- e in piu' COMMESSE e RESI, che nel serbatoio non ci sono

          RESI: flusso inverso, correggono cio che e gia stato consegnato
                --> la coda accrediti (§8) vive in Vendite > Resi
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

### 7.1 I verbi

Si procede da sinistra a destra nel funnel. I verbi di massa agiscono
sull'**intero mese** selezionato e chiedono sempre conferma, mostrando quante
attività coinvolgono.

| Verbo                     | Card                                                                                                                            | Cosa fa                                                                                                                                                   | Serve il permesso                    |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| **Approva**               | `Da approvare`                                                                                                                  | Rende le attività **emettibili**: dice che quel lavoro è buono per essere fatturato                                                                       | Approvazione attività commessa       |
| **Fattura adesso**        | `Da emettere`                                                                                                                   | Crea le fatture del mese e le porta fino a **EMESSA**. Si ferma lì: **non numera**                                                                        | Generazione fatture/lotti            |
| **Fattura questo**        | riga dell'elenco `Da emettere`                                                                                                  | Lo stesso verbo, ma **su un documento solo** (o su quelli selezionati) invece che su tutto il mese                                                        | Generazione fatture/lotti            |
| **Rendi definitive**      | ➡️ **sta su Vendite → Lotti**. Sulla card `Fatturate` resta il **rimando** «Vai ai lotti (N)», che ci porta col filtro già messo | **Numera** le fatture (atto fiscale) e le manda in stampa                                                                                                 | Numerazione fatture/lotti (dedicato) |
| ⭐ **Riporta da emettere** | righe dell'elenco `Emesse non fatturate`                                                                                        | Rimette **il lavoro selezionato** fra quello da emettere: torna disponibile per il prossimo giro. Nessun lotto viene rigenerato, nessuna fattura ricreata | Riporta da emettere (dedicato)       |

⭐ **Perché questo verbo non è qui.** Vale per tutti i verbi della guida, ed è la
ragione per cui «Rendi definitive» sta altrove: **un verbo sta dove sta l'elenco
del suo oggetto.** Numerare agisce sui **lotti**, e qui accanto c'è un elenco di
**commesse**: per sapere cosa si sta per rendere definitivo bisognerebbe
andarsene da un'altra parte.

Vive su **Vendite → Lotti**, dove quell'elenco esiste — e dove si può anche
scegliere **quali** numerare invece di prendere tutto il mese.

| Dove                   | Cosa c'è                                                                                                                                                                      |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| card `Fatturate` (qui) | ➡️ il **rimando** «Vai ai lotti (N)», che porta con sé il **filtro** — competenza del mese e stato `EMESSA`. ⛔ Un collegamento all'elenco nudo sarebbe stato un passo indietro |
| **Vendite → Lotti**    | il verbo, in due forme: **«Rendi definitivi i selezionati»** (si spuntano i lotti) e **«Rendi definitivo il mese»**                                                           |

⚠️ **Il rimando compare solo se c'è qualcosa da numerare** e se hai il permesso:
a mese tutto definitivo non c'è nulla da raggiungere, e il pulsante tace.

⚠️ **Cambia *dove si preme*, non *cosa succede*.** Quando l'azione vive su un'altra
schermata, le regole di comportamento di questa guida valgono lo stesso: il verbo
si chiama allo stesso modo e produce lo stesso effetto.

⭐ **«Riporta da emettere» agisce sulle RIGHE spuntate, non sul mese.** È
l'unico verbo di questo cruscotto che non lavora sull'intero mese, e la ragione è
che recuperare è una decisione **riga per riga**: si guarda da quale lotto viene
ogni residuo, e si sceglie. Il pulsante dice sempre **quante** righe sta per
riportare.

⚠️ **E il permesso è suo.** Non è quello che genera le fatture né quello che
cancella i documenti: chi può *recuperare* del lavoro non deve per forza poter
*cancellare* una fattura — sono due mestieri diversi.

ℹ️ **Se l'elenco che hai davanti è invecchiato, il programma se ne accorge da
solo.** Confermato il gesto, prima di toccare qualunque cosa ricontrolla le
righe spuntate: se nel frattempo qualcun altro ha lavorato, non riporta niente,
dice **quante** righe non si possono più riportare e **perché**, e ricarica
l'elenco. ⚠️ Serve perché il riporto è **tutto o niente**: senza quel controllo
il rifiuto arriverebbe come un errore unico sull'intero elenco, e non sapresti
quale riga lo ha fermato.

ℹ️ Se invece risponde «nessuna attività riportata», il senso è lo stesso —
l'elenco era vecchio — e non è un guasto.

Quattro dettagli che non sono ovvi:

- **«Fattura adesso» è cumulativo**: raccoglie l'arretrato dei mesi precedenti,
  non solo il mese a schermo. Se a maggio era rimasto indietro qualcosa, fatturando
  giugno viene preso anche quello. È voluto: evita che il non fatturato si sedimenti.
- **Approvare non fattura niente.** Approvare significa solo «questo lavoro è
  corretto». La fattura nasce col verbo successivo.
- **«Rendi definitive» può dire di no.** Prima di
  consumare il numero fiscale il sistema controlla che il documento **stia in
  piedi da solo**: che i totali siano stati calcolati, che il riepilogo IVA ci
  sia e quadri con la testata, e che le rate esistano e sommino esattamente al
  totale da pagare. Se qualcosa manca, la fattura **non viene numerata** e
  l'errore arriva con **tutti** i motivi insieme, non uno per volta.
  Il documento non è perduto: si corregge ciò che manca — quasi sempre a monte,
  in anagrafica o in commessa — e si riporta il lotto in lavorazione (§7.6).
  L'elenco puntuale dei controlli è in
  [Fatturazione — non si numera un documento incoerente](/guide/fatturazione).
- **Ogni verbo chiede prima la data del documento**, e la
  domanda non è la stessa nei due casi:
  - quando si **crea** (`Fattura adesso`, `Fattura questo`) la data è
    **facoltativa**: lasciarla vuota non vuol dire «oggi», vuol dire «decide il
    registro» — che per alcuni registri significa la fine del mese di
    competenza;
  - quando si **numera** (`Rendi definitive`) la data è quella con cui le
    fatture prenderanno il numero, e il riquadro mostra anche il **limite**: non
    si può numerare con una data precedente all'ultimo numero già emesso su quel
    registro. Se si prova, il sistema rifiuta e dice quale data non va bene.

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

| Chi                      | Quando       | Cosa                                                                                                                |
| ------------------------ | ------------ | ------------------------------------------------------------------------------------------------------------------- |
| **Processo notturno**    | ogni notte   | esegue il giro di fatturazione automatico; per la corsia **giornaliera** arriva **fino alla numerazione**           |
| **Processi di servizio** | ogni minuto  | prendono in carico i lavori avviati dalla dashboard e producono i **PDF** delle fatture numerate                    |
| **Operatore**            | quando serve | **anticipa** il giro senza aspettare la notte, **numera** la fatturazione massiva, **sblocca** ciò che si è fermato |

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
cercare a mano nell'elenco dei lotti.

⚠️ **Dalle righe della card `Fatturate` al lotto non si arriva**: il menu della
riga offre la sola «Apri commessa», e l'elenco non porta né il numero di fattura
né il codice del lotto.

✅ **Ma dalla card sì**: il pulsante **«Vai ai lotti (N)»** porta all'elenco dei
lotti **già filtrato** su competenza e stato `EMESSA` — cioè esattamente quelli
da numerare (§7.1). Quello che manca è l'aggancio **dalla singola riga**.

### 7.6 Tornare indietro: le tre vie d'uscita

Finché le fatture **non sono numerate** si può tornare indietro. I verbi sono
tre, non uno, e la differenza fra loro è cosa resta in piedi dopo. Si trovano
nel **drawer del lotto** e nel menu della riga nell'elenco dei lotti — al lotto
si arriva anche dal pannello errori della Lente 1 (§7.5).

| Verbo                      | Su cosa agisce                                | Cosa resta dopo                                                                                                                                                                                  |
| -------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Riporta in lavorazione** | tutto il lotto, da EMESSA (o da bozza)        | Il lotto **resta aperto** e torna in bozza: le sue fatture vengono eliminate, le righe di commessa tornano «da emettere» e al giro successivo le fatture si **rigenerano**                       |
| **Elimina dal lotto**      | **una** fattura                               | Solo quella fattura sparisce; il lotto e le altre fatture proseguono. Le sue righe **tornano «da emettere»** e rientrano nel giro successivo; quelle delle altre fatture **non vengono toccate** |
| **Annulla lotto**          | tutto il lotto, solo se è ancora in **bozza** | Il lotto è **chiuso e non si riapre**: le righe tornano libere e servirà un lotto nuovo                                                                                                          |

**La regola per scegliere**: se il lavoro va rifatto, *Riporta in lavorazione*;
se il problema è un documento solo, *Elimina dal lotto*; *Annulla lotto* è per
un giro partito per sbaglio, che non deve produrre nulla.

**Chi le può usare.** *Riporta in lavorazione* chiede lo **stesso permesso** di
*Rendi definitive* (Numerazione fatture/lotti): chi può numerare può anche
disfare ciò che non è ancora numerato. *Annulla lotto* chiede solo il permesso
sui lotti, perché su un lotto in bozza non c'è niente di fiscale da disfare. Chi
non ha il permesso **non vede** il pulsante. Il motivo per cui *Elimina dal lotto*
è spento su una fattura compare sulla sua riga.

> ⚠️ **Le due strade rimettono in coda allo stesso modo** — tutto il lotto, oppure
> un documento solo — e la scelta fra loro è quella descritta qui sopra.
>
> ⚠️ **Le attività rimaste indietro non si sbloccano da sole.** Si contano nella
> casella *Emesse non fatturate* della Lente 1 (§3.1), e da lì il verbo **«Riporta
> da emettere»** (§7.1) le rimette in coda: è il gesto per cui quella casella ha
> una lista.

Tre avvertenze, tutte pagate sul campo:

- **Tornare indietro cancella, non congela.** Le fatture toccate vengono
  eliminate per davvero — righe, note e allegati di lavorazione compresi — e
  dopo non è più possibile sapere cosa dicevano. Resta la traccia storica del
  loro passaggio nel lotto, non il loro contenuto. È voluto: un documento che
  qualcuno ha deciso di rifare non serve a nessuno come reperto.
- **Un numero fiscale ferma tutto.** Se anche una sola fattura del lotto è già
  stata resa definitiva, nessuno dei tre verbi è disponibile: cancellarla
  aprirebbe un buco nella numerazione. Da lì in poi la strada è la nota di
  credito.
- **Non tutto si disfa insieme al documento.** Un acconto o un minimo già
  registrato su una contabile chiusa **non viene ripristinato**: l'operazione
  riesce lo stesso e lascia un avviso nel registro del lotto. E un accredito già
  registrato non si annulla da qui: la sua nota di credito viene semplicemente
  rigenerata al giro successivo. Vale la pena leggere gli avvisi, non darli per
  puliti.

### 7.7 **Annullare** un documento ritira il lavoro che aveva spinto

⚠️ **Da sapere prima, non da scoprire dopo.** **Annullare** un documento —
preventivo, ordine, DDT, contratto — **non ferma solo i passaggi futuri**: ritira
anche le righe di commessa che quel documento aveva già prodotto e che nessuno ha
ancora emesso. Quelle righe passano ad **ANNULLATA**.

> ⛔ **È l'ANNULLAMENTO, e nient'altro.** *Evadere*, *completare* o *chiudere* un
> documento in qualunque altro modo **non ritira niente**: quel lavoro resta
> fatturabile, ed è giusto così — è arrivato in fondo, non è stato disdetto.
> Il ritiro è legato all'atto che dice «questo documento non vale più».

⭐ **Perché si arriva fino in fondo.** Fermarsi ai passaggi successivi lascerebbe
fatturabile ciò che è già passato in commessa: quel lavoro resterebbe lì, e prima
o poi finirebbe in una fattura che nessuno si aspetta più. L'annullamento di un
documento è quindi un'operazione **che non si ferma a metà**.

| Stato della riga di commessa | Cosa succede **annullando** il documento                            |
| ---------------------------- | ------------------------------------------------------------------- |
| non ancora emessa            | ⭐ **viene ritirata**: passa ad `ANNULLATA`                          |
| ⛔ già **emessa**             | **il documento non si annulla affatto**, e il messaggio dice perché |
| già annullata                | non si tocca                                                        |

⛔ **Il rifiuto sulle righe già emesse non è un capriccio**: quel lavoro è *in
volo* verso una fattura, e ritirarlo lascerebbe un'attività orfana per strada —
cioè il residuo di cui parla la §3.1. La via d'uscita c'è e il messaggio la
nomina: si **recuperano prima** con «Riporta da emettere» dalla Lente 1, e dopo
il documento si annulla portandosi via anche quelle.

⚠️ **`ANNULLATA` non si disfa.** Riaprire il documento non riporta indietro le
righe: le rifà il push, e solo se il documento è tornato spingibile. Vale la pena
guardare cosa si sta per ritirare **prima** di annullare.

**Come si riconosce una riga ritirata.** Nel drawer della commessa la riga
**resta**, con lo stato emissione a `ANNULLATA`. ⚠️ Se non la vedi, controlla il
**filtro «Stato emissione»**: arrivando da una card del cruscotto il drawer lo
eredita già impostato (es. `NON_EMESSA`), e una riga annullata resta fuori. Con
il filtro su **«Tutte»** ricompare.

✅ **E il motivo si legge.** Dal kebab della riga, voce **«Registro della
riga»**: si apre l'elenco degli eventi in ordine cronologico inverso, con chi,
quando e **con quale motivo** — per un ritiro la frase è *«Ritiro automatico alla
chiusura del documento di origine (PREVENTIVO PRV0000133)»*, col numero del
documento che l'ha causato.

> ℹ️ Il registro non riguarda solo i ritiri: raccoglie tutto ciò che è successo a
> quella riga — oneri aggiunti, annullamenti a mano, riporti «da emettere»,
> accrediti. È la risposta a «perché questa riga è così».

### 7.8 Cosa non si fa ancora da qui

L'**invio allo SDI** non è disponibile dalla dashboard: resta un passo successivo,
gestito fuori da questa schermata. La dashboard copre il percorso
**approvazione → fattura → numerazione → stampa**.

---

## 8. La coda accrediti

Non è una quarta lente: è una **coda di lavoro**, e vive dentro
**Vendite → Resi**, accanto alla coda delle ri-consegne.

### 8.1 Il principio in una riga

**Si fattura la merce che il cliente tiene in mano alla fine.**

Il sistema, per ogni partita di merce, tiene un conto solo: quanto il cliente ha
**tenuto** (consegnato, meno reso, più ri-consegnato) contro quanto gli è stato
**fatturato**. La differenza dice tutto:

| Il conto                            | Cosa vuol dire                                                  |
| ----------------------------------- | --------------------------------------------------------------- |
| tenuto **più** di quanto fatturato  | manca una fattura per la differenza                             |
| tenuto **meno** di quanto fatturato | gli è dovuto un **accredito**: è ciò che finisce in questa coda |
| pari                                | niente da fare                                                  |

Non ci sono regole diverse per i diversi tipi di reso: c'è un conto, e il segno
decide. Un reso conta solo da quando è **confermato** — finché è in bozza non
sposta niente.

### 8.2 Le due etichette

| Etichetta                                          | Quando compare                                                                                                                                                             |
| -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Accredito dovuto**                               | la merce è tornata indietro e lì resta: il cliente ha pagato qualcosa che non ha. È arretrato vero                                                                         |
| **Accredito facoltativo — merce da ri-consegnare** | la merce tornerà al cliente. Puoi accreditare e poi rifatturare, oppure lasciar correre e rispedire: **il conto torna in entrambi i casi**. È una scelta, non un arretrato |

La scelta sulla seconda non si congela al momento del reso: resta aperta fino
alla ri-spedizione. Per questo le facoltative restano visibili in coda invece di
sparire.

### 8.3 Cosa si fa da qui

⭐ **Si accredita da qui.**

Dalla riga della coda, o dal drawer del reso, si registra l'**accredito** della
riga: la merce resa esce dalla coda e nasce una riga di **rettifica** sulla
commessa del cliente. Da lì l'accredito segue la strada normale della
fatturazione — al giro successivo diventa una **nota di credito**, un documento
separato dalla fattura, con il legame riga↔riga verso ciò che corregge.

| Verbo                   | Dove                                   | Cosa fa                                                                                                                                         |
| ----------------------- | -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **Accredita**           | riga della coda · drawer del reso      | registra l'accredito dovuto: la riga esce dalla coda, la rettifica entra in commessa                                                            |
| **Annulla l'accredito** | drawer del reso (riga già accreditata) · riga della coda (accredito parziale) | il caso «ho cliccato la riga sbagliata»: toglie la rettifica, l'accredito torna dovuto. Richiede un **motivo**, ed è l'unica traccia del perché |

⚠️ **«Annulla l'accredito» e «annulla il documento» non sono la stessa cosa**, e
confonderle manda sulla strada sbagliata: il primo agisce **a monte** del
documento; per disfare una nota di credito già emessa si riporta il lotto in
bozza — e la nota **viene rigenerata** al giro successivo, perché la merce resa
non è cambiata.

⛔ **L'accredito si annulla solo finché nessuna delle sue rettifiche è entrata in
fatturazione**: presa da un lotto, agganciata a una riga di fattura o emessa.
Basta una rettifica per bloccarlo tutto, perché un annullo a metà lascerebbe in
coda un residuo che nessuno può più soddisfare. Da quel momento — ed è lo stato
finale di ogni accredito — il pulsante è **spento** e dice perché («L'accredito è
già stato emesso in fattura…»). Se la nota di credito non è ancora numerata, la
strada è riportare il lotto in bozza: le rettifiche escono dalla fatturazione e
l'accredito torna annullabile.

⛔ **Finché il reso ha un accredito registrato, il reso non si annulla**: il
pulsante resta acceso ma spiega il perché. Prima si annulla l'accredito.

📌 Il funzionamento tecnico (natura del documento, legame di riga, guardia sulla
numerazione) sta nella
[guida tecnica alla fatturazione](/guide/fatturazione#il-documento-che-torna-indietro-la-nota-di-credito).

---

## 9. Note tecniche

- **Sorgenti**: ogni lente ha la sua famiglia di viste `vendite.vw_dash_*`
  (competenza / backlog / aperto), esposte da endpoint GET sottili
  (`/api/v1/vendite/dashboard-*`). Nessuna logica di dominio nel frontend: aree,
  fasi, misura, ordinamento e ambito vivono nel database/BE.
- **Ambito emittente**: RLS in modalità invoker sulle viste; il BE non passa
  l'identità utente (vedi §2.5).
- **Misura mista**: decisa dal backend nel payload (valore assente = area a
  conteggi, non una whitelist statica nel frontend) — vedi §2.3.
- **DDT, resi e coda accrediti**: il disegno sta nella guida
  [Fatturazione](/guide/fatturazione). Qui restano le tre scelte che si vedono a
  schermo: la popolazione ristretta dei DDT (solo quelli con un ruolo di
  fatturazione), il valore al residuo degli ordini e la forma a contatore della
  coda accrediti.
- **Revisione attiva**: i cruscotti considerano solo la revisione attiva di
  preventivi e offerte (vedi §2.4).
- **Fotografia vs azione**: le card della Situazione aperta non sono filtrate dal
  ritardo (restano una fotografia completa); la soglia "aperti da oltre N giorni"
  agisce solo sulla lista di drill-down.

---
{% include-markdown "signature-core.md" %}
