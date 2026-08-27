# Collaudo in-app · «Rendi definitive» sulla lista Lotti

> **Cos'è.** Il copione della validazione a video: si tiene aperto accanto
> all'applicazione e si spunta. Non è il brief — il *perché* di ogni scelta sta
> in [brief-be-fe-rendi-definitive-sui-lotti.md](brief-be-fe-rendi-definitive-sui-lotti.md);
> qui c'è solo **cosa fare, cosa deve succedere, e cosa fare se non succede**.
>
> **Perché esiste.** È la voce **C-1** del brief, l'unica che tiene aperto il
> cantiere insieme alla guida (C-2). Il codice è scritto, committato
> (`625c743c6`) e l'interfaccia è stata vista. Ma di questi verbi è stato provato
> il **percorso** — endpoint, coda, perimetro, guard — mai l'**esito**:
> ⛔ **nessun numero è stato consumato in collaudo**.
>
> ⭐ **E il primo click vero ha già trovato un difetto**: il 2026-08-27 Tid ha
> spuntato un lotto, ha chiesto «Rendi definitivi i selezionati» e il dialog ha
> risposto *«La finestra di numerazione non è stata letta»*. Causa e correzione
> nella **prova 0**. Il che dice due cose: che questo documento serve, e che il
> verbo su selezione **non era mai stato percorso da una persona**.
>
> **Stato**: in corso — due difetti già trovati e corretti (R-1, R-2 nel verbale).
> **Ambiente**: sviluppo (`dbdev`).
> **Pagina**: `vendite/lotti`.

---

## ⛔ Quattro cose da sapere prima di cominciare

**1 · Questo collaudo NON si rifà.** La numerazione è un **atto fiscale**: i
numeri che consumi sono veri, entrano in una sequenza e non tornano indietro.
Non è un giro da ripetere «per sicurezza» — si fa una volta, su lotti che sei
disposto a numerare davvero.

**2 · ⚠️ La fattura 2263 non va numerata.** È un promemoria che viene
dall'handoff del 2026-08-03 e **va verificato se è ancora valido**. Prima di
lanciare un «Rendi definitivo il mese» — che prende tutto senza chiedere —
controlla che quella fattura non sia nel perimetro. È esattamente il tipo di cosa
che un verbo di massa si porta via in silenzio.

**3 · ⭐ L'ordine delle prove è parte del metodo, non una comodità.** Le prove
**0 → 5** non consumano niente: si spunta, si guarda, si chiude. Le prove
**6 → 9** numerano. Farle in quest'ordine significa che, se qualcosa non torna
nella selezione, lo scopri **prima** di aver bruciato dei numeri — e non dopo.
Su un atto irreversibile è l'unica sequenza che si può permettere un errore.

**4 · Ricarica la pagina prima di cominciare.** Il bundle è stato ricostruito
dopo la correzione della prova 0: senza un ricarico stai collaudando il
frontend di ieri.

---

## La materia

* la pagina è **`vendite/lotti`**, con due schede: **«Lotti del mese»** e
  **«Recuperi»**;
* in barra, accanto ai filtri, i due verbi:
  **«Rendi definitivi i selezionati (N)»** e **«Rendi definitivo il mese»**;
* ⚠️ **serve un mese di competenza con almeno 3-4 lotti `EMESSA`**, e per la
  prova 7 ne servono **due di registri (sezionali) diversi**. Se non ci sono,
  la prova 7 si dichiara `SENZA_MATERIA` invece di essere spuntata a caso.

---

## Prove che NON consumano numeri

### 0 · Il dialog legge la finestra *(la correzione del 2026-08-27)*

1. spunta **un** lotto emesso;
2. clicca **«Rendi definitivi i selezionati (1)»**;
3. **NON confermare**: guarda solo il dialog e chiudilo.

**Cosa deve succedere**: il dialog mostra la data proposta e il perimetro. Non
deve comparire *«La finestra di numerazione non è stata letta»*.

**Se non succede**: apri la console del browser. Se l'errore è di nuovo
`E_VALIDATION_INPUT` con `lotti_ids=None`, la correzione non è arrivata al
browser — ricarica con la cache svuotata.

> **Cos'era.** Il frontend mandava la selezione come `?lotti[]=12` (è così che
> axios serializza un array di default — provato sulla 1.20, la versione in
> `package.json`), mentre il backend legge `getlist('lotti')`, cioè la chiave
> **senza** parentesi. Non trovava niente, e `_query_lotti_ids` traduce la lista
> vuota in `None` di proposito — quindi il servizio riceveva **tutti e tre** i
> perimetri nulli e rispondeva «indicarne esattamente uno» su una richiesta in
> cui uno c'era. Corretto con `paramsSerializer: { indexes: null }`.
>
> ⭐ Accanto a quella riga c'era un commento che **affermava il contrario**
> («axios serializza un array così di default»). Era falso, e ha fatto passare
> la riga per una cosa già verificata. È il motivo per cui è arrivata fin qui.

### 1 · La selezione sopravvive al cambio pagina

Spunta due lotti, vai a **pagina 2**, torna a **pagina 1**.

**Cosa deve succedere**: le spunte ci sono ancora e il contatore del pulsante non
è calato.

**Se non succede**: la selezione è legata all'**indice di riga** invece che
all'id del lotto. È il difetto classico di queste liste, e il brief dice che era
già stato pagato una volta sulla Lente 1.

### 2 · La selezione attraversa le due schede

Spunta un lotto su **«Lotti del mese»**, passa alla scheda **«Recuperi»**, spunta
un lotto anche lì.

**Cosa deve succedere**: il contatore dice **2**. La selezione è **una sola**, e
attraversa le schede di proposito — un lotto di competenza arretrata si numera
insieme agli altri.

**Se non succede** (il contatore torna a 1 cambiando scheda): il seleziona-tutto
sta **sostituendo** invece di aggiungere. È il difetto che il 2026-08-27 ha fatto
estrarre `toggleAllInPagina` nel building block condiviso.

### 3 · Il seleziona-tutto è **di pagina**

Sull'intestazione della colonna delle caselle, spunta «tutti» a **pagina 1**,
poi vai a **pagina 2** e spunta «tutti» anche lì.

**Cosa deve succedere**: il contatore è la **somma** delle due pagine.

**Se non succede** (il contatore diventa quello della sola pagina 2): il
seleziona-tutto sostituisce. Stesso difetto della prova 2, altra porta —
⚠️ e il brief avverte che *«la selezione riga-per-riga compone bene: il difetto
si vede solo passando dall'intestazione»*.

### 4 · Il conteggio è onesto

Prova a spuntare una riga **non numerabile** (stato ≠ emessa): la casella deve
essere **spenta**, e passandoci sopra deve dire **perché**.

Poi, se ne trovi il modo, arriva ad avere una selezione dove non tutto è
numerabile.

**Cosa deve succedere**: il dialog dichiara i due numeri quando divergono —
«5 selezionati, **4 numerabili**». Mai un conteggio che tace ciò che ha scartato.

### 5 · La casella che si spegne sotto i piedi

Spunta un lotto, poi fai qualcosa che lo faccia uscire dallo stato numerabile
(per esempio numeralo dal **kebab della riga**, prova 10) e ricarica la lista.

**Cosa deve succedere**: quella riga **esce dalla selezione** da sola.

**Se non succede**: resta spuntata con la casella disabilitata — non
rimovibile, contata nel pulsante, e **ri-sottomessa a ogni giro**.

---

## Prove che CONSUMANO numeri

> ⛔ Da qui in avanti non si torna indietro. Prima di cominciare rileggi il
> punto **2** delle avvertenze.

### 6 · Numerare una selezione — *l'atto vero*

Spunta **due lotti emessi** → «Rendi definitivi i selezionati (2)» → conferma la
data.

**Cosa deve succedere**:

- [X] il toast dice *«Numerazione messa in lavorazione: l'esito arriva da sé»*;
- [X] poco dopo arriva *«Numerati 2 lotti»*;
- [X] la selezione si **azzera**;
- [X] ⭐ **e qui sta il punto di tutto il collaudo**: riapri quei due lotti e
      **guarda che il numero ci sia davvero**. Fin qui era provato che il tubo è
      collegato; questa è la prima volta che si guarda se l'acqua esce.

**Se l'esito è parziale** — *«Numerati 1 su 2: 1 saltati, 0 falliti»* — non è per
forza un difetto: il dettaglio sta nel **registro del lotto**, e va letto lì
prima di chiamarlo errore.

### 7 · Il limite che si sposta fra sezionali diversi

Spunta lotti di **registri diversi**, apri il dialog, poi **togli e rimetti** una
spunta.

**Cosa deve succedere**: la data minima proposta è la **più alta** fra i limiti
dei sezionali selezionati — sicura per tutti — e **si ricalcola** mentre la
selezione cambia, non una volta all'apertura.
 Ok funziona

### 8 · Stesso perimetro due volte → non parte un secondo giro

Subito dopo la prova 6, con lo **stesso** perimetro ancora in lavorazione,
ri-chiedi l'atto.

**Cosa deve succedere**: *«Questo stesso perimetro è già in numerazione: non è
stato avviato nulla di nuovo»*. Non un secondo giro, e non un silenzio.

### 9 · Due selezioni **diverse** sullo stesso mese → due giri

Spunta un lotto A, numera. Poi spunta un lotto **B diverso**, stesso mese, e
numera.

**Cosa deve succedere**: il secondo atto **parte**.

**Se non succede** (il secondo dice «già in corso»): è la trappola del **§5.1**
del brief — la coda deduplica su `(tipo, competenza, scope)` e senza il digest
del perimetro **mangia la seconda selezione**. L'operatore legge «accodato» e non
succede niente: è il difetto più insidioso della slice, ed è il motivo per cui
questa prova esiste.
Ok funziona 
### 10 · Il verbo per-riga — *non regressione*

Dal **kebab** di una riga emessa, «Rendi definitiva». È il percorso vecchio, che
manda un id scalare e ha sempre funzionato: serve a distinguere «è rotto il
verbo» da «è rotto il perimetro».

### 11 · Numerare il mese

Sulla scheda **«Lotti del mese»**, senza spuntare niente → «Rendi definitivo il
mese».

**Cosa deve succedere**:

- [X] numera **tutti** i lotti emessi di quel mese;
- [X] ⛔ **non tocca i recuperi**, che sono di competenza precedente: quelli si
      numerano solo spuntandoli. Se vedi sparire anche quelli, è un difetto.

### 12 · La selezione **non** si azzera se l'atto fallisce

Se durante le prove un atto va in errore, guarda la selezione.

**Cosa deve succedere**: resta **intatta**. Azzerarla su un fallimento costringe
a ricomporla a mano senza sapere quali righe erano dentro — ed era il rilievo
**C-5** della revisione critica.

### 14 · I verbi si riaccendono dopo il giro *(la correzione del 2026-08-27)*

Subito dopo un atto (prova 6), **esci dalla scheda Lotti** — vai su un'altra
scheda del contenitore — e **rientra**.

**Cosa deve succedere**: quando il giro finisce, i due pulsanti tornano
**cliccabili** e la rotellina sparisce.

**Se non succede**: il polling è rimasto sospeso. Il job resta contato, e
`nGiriNumera` non torna a zero.

> **Cos'era.** `useJobPolling` registrava `onDeactivated(() => suspend())` ma
> lasciava il `resume()` alla view. `DashboardCompetenzaView` lo chiamava,
> `LottiListView` no — quindi bastava uscire dal tab e rientrare con un giro in
> volo perché i tick non ripartissero più: i verbi restavano spenti fino a un
> ricarico di **pagina**. Ricaricare la **lista** non serviva, perché lo stato
> era in memoria.
>
> ⭐ **L'asimmetria era il difetto**: ciò che un BB si prende in carico da sé
> (`suspend`) deve avere il suo contrario nello stesso posto. Ora
> `onActivated(() => resume())` sta nel BB, e nessun consumatore può
> dimenticarlo.

### 15 · La rotellina sui lotti del giro *(aggiunta il 2026-08-27)*

Durante l'atto della prova 6, guarda le righe che avevi spuntato.

**Cosa deve succedere**: accanto al **codice** dei lotti del perimetro compare
una rotellina che gira, e sparisce quando il giro finisce.

**Cosa NON deve succedere**: che resti girando dopo la fine, o dopo un esito
negativo. Si smarca **sempre** — anche su errore e su timeout — perché una riga
marcata da un giro concluso male resterebbe segnata per sempre.

⚠️ Sull'atto di **mese** la rotellina sulle righe **non compare**, ed è
corretto: quel perimetro non ha un elenco di chiavi, e il segno del giro vivo è
la rotellina sul pulsante.

### 13 · Il rimando dalla Lente 1

Dal cruscotto Competenza, card `Fatturate` → **«Vai ai lotti da numerare (N)»**.

**Cosa deve succedere**: porta sulla lista Lotti **col filtro già messo**
(competenza + stato). Un rimando all'elenco nudo sarebbe un passo indietro.
E sulla card **non** deve esserci più il vecchio pulsante «Rendi definitive».

---

## Verbale

**Chiuso il**: ______ · **Da**: ______ · **Ambiente**: ______

| #   | Prova                                        | Consuma numeri | Esito | Note |
| --- | -------------------------------------------- | -------------- | ----- | ---- |
| 0   | Il dialog legge la finestra                  | no             | ⬜     |      |
| 1   | Selezione sopravvive al cambio pagina        | no             | ⬜     |      |
| 2   | Selezione attraversa le due schede           | no             | ⬜     |      |
| 3   | Seleziona-tutto è **di pagina**              | no             | ⬜     |      |
| 4   | Conteggio onesto (selezionati vs numerabili) | no             | ⬜     |      |
| 5   | La casella si spegne sotto i piedi           | no             | ⬜     |      |
| 6   | **Numerare una selezione — il numero c'è**   | **sì**         | ⬜     |      |
| 7   | Il limite fra sezionali diversi              | no             | ⬜     |      |
| 8   | Stesso perimetro → nessun secondo giro       | no             | ⬜     |      |
| 9   | Selezioni diverse → due giri                 | **sì**         | ⬜     |      |
| 10  | Verbo per-riga (non regressione)             | **sì**         | ⬜     |      |
| 11  | Numerare il mese, senza toccare i recuperi   | **sì**         | ⬜     |      |
| 12  | Selezione intatta dopo un fallimento         | no             | ⬜     |      |
| 13  | Il rimando dalla Lente 1 porta il filtro     | no             | ⬜     |      |
| 14  | I verbi si riaccendono dopo il giro          | no             | ⬜     |      |
| 15  | Rotellina sui lotti del giro, e sparisce     | no             | ⬜     |      |

### Che cosa ha trovato il collaudo

> Da riempire strada facendo. Vale più delle spunte: un elenco vuoto accanto a
> tredici verdi si legge come «non abbiamo guardato», non come «era tutto a
> posto».

| #   | Cosa                                                                                                                                                                | Dove è finito                                              |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| R-1 | La selezione viaggiava come `?lotti[]=…` mentre il backend legge `lotti`                                                                                            | ✅ corretto il 2026-08-27 in `api/lotti.js` (prova 0)       |
| R-2 | I due verbi restavano **spenti per sempre** dopo un giro: `useJobPolling` si sospendeva da sé al cambio tab e delegava il `resume()` alla view, che non lo chiamava | ✅ corretto il 2026-08-27 nel BB `useJobPolling` (prova 14) |
|     |                                                                                                                                                                     |                                                            |

---

## Quando questo verbale è chiuso

La voce **C-1** del brief si chiude. Resta **C-2** — la guida
(`cruscotti-fatturazione.md` §7.1 e §6.3), che oggi descrive ancora «Rendi
definitive» sulla card `Fatturate`, cioè il contrario di quello che
l'applicazione fa. ⛔ È bloccata da un **ordine**, non da un dubbio: la stessa
tabella dei verbi la riscrive anche il passo **L5** del cantiere gemello, e farli
in parallelo significa che una delle due mani perde il lavoro dell'altra (§9.1
del brief).

⚠️ **Un difetto trovato qui non riapre il brief da sé**: va guardato dove
appartiene. Quello della prova 0 era di questo cantiere ed è stato corretto qui;
uno che riguardasse la coda, la numerazione a DB o il perimetro emittente ha
altre sedi, e forzarlo dentro questo documento lo trasformerebbe nel contenitore
di tutto ciò che tocca un lotto.
