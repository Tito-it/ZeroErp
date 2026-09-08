# Guida – Numerazione dei documenti e codici automatici

> **Destinatari:** chiunque debba capire come nasce un numero o un codice in ZeroErp — sviluppatori database, backend, frontend e analisti funzionali
>
> **Prerequisiti:** nessuno. Le parti tecniche stanno in fondo a ogni capitolo.
>
> **Stato:** aggiornata al **31-08-2026 (sera)**, dopo che i quattro documenti traslocati hanno portato sui registri anche la **forma** del numero, e non più solo il contatore. Descrive **come funziona oggi**, non come funzionava prima.

---

## 1. Il problema, in una pagina

Quasi tutto in un gestionale ha un identificativo: il cliente ha un codice, la
fattura ha un numero, la commessa ha il suo. Sembrano tutti la stessa cosa, e
invece si dividono in **due famiglie molto diverse**.

| | Esempio | Che cosa serve garantire |
| --- | --- | --- |
| **Un codice** | Il cliente `BAC/0001234` | Che sia **unico**. Basta. |
| **Un numero di documento** | La fattura numero `123`, anno `2026`, serie `A` | Che sia unico **e** che segua una progressione **per azienda e per anno**, senza salti d'anno e senza mescolarsi con quella di un'altra azienda |

⭐ **Il secondo caso è molto più esigente del primo**, e non per pignoleria: la
progressione dei numeri di un documento è ciò che, davanti a un controllo, dimostra
che non ne sono stati nascosti. Un codice cliente non deve dimostrare niente a
nessuno.

Per questo in ZeroErp ci sono **due meccanismi**, non uno.

---

## 2. Le due aree

### 2.1 Il **catalogo dei formati** — `config.sistema_codici`

È una tabella di configurazione che dice, per ogni tipo di codice, **che aspetto
ha** — prefisso, separatore, quante cifre — e che per ognuno **fa anche il
conteggio**: tiene un contatore che avanza di uno a ogni riga nuova e assegna il
codice **nel momento in cui la riga viene creata**.

```
prefisso = BAC     separatore = /     cifre = 7      →     BAC/0001234
```

**Chi lo usa, oggi** — clienti, soggetti, fornitori, vettori, istanze di utility,
pratiche, preventivi, contratti, offerte commerciali, lotti di fatturazione.
Dieci voci, e nessun documento di vendita.

⭐ **Dal 31 agosto 2026 questa tabella descrive solo cose che genera davvero.**
Fino a quel giorno conteneva anche le righe di documenti di trasporto, ordini,
resi e commesse: righe che non contavano più niente da mesi, ma che restavano
visibili nel pannello di configurazione con un prefisso che **nessuno leggeva
più**. Un amministratore che lo cambiava non otteneva alcun effetto, e non aveva
modo di accorgersene.

### 2.2 Il **motore dei registri** — `vendite.registri_fatturazione`

Un **registro** è un sezionale di numerazione: appartiene a **una** azienda
emittente, tiene il proprio contatore, sa ripartire da 1 a ogni Capodanno e —
dal 31 agosto 2026 — porta anche la **forma** del numero che produce: prefisso,
suffisso e quante cifre.

**Chi lo usa, oggi** — fatture, documenti di trasporto, ordini, commesse, resi.

⚠️ **Il nome della tabella dice meno di quello che fa.** Si chiama
`registri_fatturazione` perché all'inizio numerava solo le fatture; oggi numera
cinque famiglie di documento. Il nome non è stato cambiato di proposito: cambiarlo
significherebbe toccare decine di oggetti collegati senza modificare **nessun**
comportamento, e non è un lavoro da infilare dentro un altro. Il debito è
dichiarato, non dimenticato.

---

## 3. Le tre cose che un numero richiede — e chi le fornisce

Qui sta il punto che chiarisce tutto il resto. Assegnare un numero vuol dire
mettere insieme **tre** cose diverse, e non è detto che vengano dallo stesso posto.

| | Che cos'è | Chi la fornisce |
| --- | --- | --- |
| **Il formato** | prefisso, suffisso, quante cifre | il **registro**, per i cinque documenti; il catalogo dei formati per tutto il resto |
| **Il contatore** | chi tiene il conto e fino a quanto è arrivato | il registro **oppure** il catalogo dei formati |
| **Il momento** | quando il numero viene consegnato | dipende dal documento, e non si centralizza |

### ⚠️ Il trasloco è avvenuto in **due tempi**, e conviene saperlo

Chi ha letto questa guida in una versione precedente ci ha trovato scritto che i
quattro documenti *«hanno cambiato solo il contatore»*. Era vero, ma **solo per
mezza giornata**:

1. **la mattina** del 31 agosto 2026 si è spostato il **contatore**, lasciando la
   forma nel catalogo dei formati;
2. **la sera** si è spostata anche la **forma** — ed è stato spostandola che si è
   visto perché doveva muoversi: finché la forma restava di là, quelle quattro
   righe dovevano restarci anche loro, e restavano **monche**.

⭐ È il caso tipico in cui un lavoro fatto a metà non si vede finché non lo si
guarda da vicino. Le righe non davano errore: davano confusione, che è più
difficile da notare e più lunga da smaltire.

### La forma ha un **default** e un **effettivo**

È la distinzione che regge tutto il capitolo, e vale la pena tenerla a mente:

```
famiglie_documento     →  il DEFAULT   (com'è fatto quel TIPO di documento)
registri_fatturazione  →  l'EFFETTIVO  (com'è fatto QUESTO sezionale)
```

Tutti i documenti di trasporto hanno 7 cifre: questa è una proprietà del **tipo di
documento**, e sta nel catalogo delle famiglie. Un singolo sezionale può però
volere un prefisso suo — è per quello che esistono i sezionali — e allora il
valore che conta è quello scritto sul **registro**.

⭐ Un registro nuovo **nasce copiando il default della sua famiglia**, e da quel
momento vive di vita propria. Nessuno deve ricordarsi di riempirlo.

---

## 4. Come nasce oggi ogni identificativo

*(fotografia al 31-08-2026, sera)*

| Documento / entità | Formato | Contatore | Quando riceve il numero |
| --- | --- | --- | --- |
| **Fattura** | *nessuno* (vedi sotto) | **registro** | all'emissione |
| **DDT** | **registro** | **registro** | quando passa a *emesso* |
| **Ordine** | **registro** | **registro** | alla creazione |
| **Reso** | **registro** | **registro** | quando passa a *confermato* |
| **Commessa** | **registro** | **registro** | alla creazione |
| Preventivo, contratto, offerta | catalogo formati | catalogo formati | alla creazione |
| Lotto di fatturazione | catalogo formati | catalogo formati | alla creazione |
| Cliente, soggetto, fornitore, vettore, istanza, pratica | catalogo formati | catalogo formati | alla creazione |

### ⚠️ Tre modi diversi di *scrivere* l'identità, e conviene saperlo

Non tutti i documenti scrivono la propria identità allo stesso modo, e la differenza
si vede solo guardando le colonne:

* **la fattura la tiene in tre campi separati** — numero, anno, serie — e il campo
  «numero» contiene il progressivo **nudo**, senza prefissi. La stringa che si legge
  su un documento stampato la compone chi stampa, non il database;
* **DDT, ordini e resi** tengono anno e serie in campi propri, ma nel campo «numero»
  scrivono una stringa **già formattata** con prefisso e cifre di riempimento (per
  esempio `DDT0000123`), presa dal registro;
* **la commessa tiene la stringa in un campo solo**, il codice —
  `CMM-ACME-2026-000000001` — e non ha un campo «numero» a parte: quella stringa
  *è* il suo numero. ⭐ **Dal 2 settembre 2026 ha però anche l'anno e il registro
  in due colonne proprie**, come gli altri: prima erano leggibili solo spezzando
  la stringa.

⚠️ Ne discende una cosa pratica: **chi scrive codice che confronta o ordina i numeri
non può trattarli tutti allo stesso modo.** Ed è la ragione per cui il controllo
automatico descritto al §8 non elenca i documenti ma li legge da un catalogo: le
regole sono tre, non una.

⚠️ **Il momento non è un dettaglio.** Un documento che riceve il numero *alla
creazione* consuma un numero anche se poi viene abbandonato: nella progressione
restano dei buchi. È accettato e dichiarato — un ordine annullato non obbliga a
rinumerare gli altri — ma per una fattura sarebbe un problema, ed è il motivo per
cui la fattura si numera solo all'emissione.

---

## 5. Un solo posto che compone il numero

Fino al 31 agosto 2026 i quattro documenti traslocati facevano **gli stessi sei
passi**, ciascuno per conto proprio: trovare il registro, ricavare l'anno dalla
data, chiedere il progressivo, leggere il formato, comporre la stringa, scrivere
le colonne. Quattro copie della stessa cosa.

⛔ **Il difetto di quattro copie non è la lunghezza: è che si può correggerne
tre.** Una modifica al modo di comporre il numero andava fatta in quattro posti, e
chi ne dimenticava uno otteneva un documento formattato diversamente dagli altri —
che **nessun controllo respinge**, perché è un numero valido, solo diverso.

⭐ Oggi i sei passi stanno in una funzione sola, e i quattro generatori conservano
l'unica cosa che li distingue davvero: **il momento**. Il documento di trasporto
numera all'emissione, il reso alla conferma, ordine e commessa alla creazione —
quello resta scritto ciascuno a casa propria, perché è la sola cosa che non hanno
in comune.

### ⭐ Il guadagno che non si vedeva: provare la composizione

La parte che compone la stringa è ora una funzione **pura**: riceve dei valori e
restituisce una stringa, senza leggere niente.

Prima, per verificare che un numero venisse formattato bene, bisognava
**fabbricare un documento intero** — un documento di trasporto con le sue righe,
il suo indirizzo, la sua causale e la sua transizione di stato. Oggi si scrive una
riga di prova con i valori che si vogliono. Il costo di verificare un caso in più è
passato da venti righe a una.

---

## 6. Le scelte fatte, e perché

### 6.1 Ogni azienda ha la sua numerazione, e la garanzia sta nella chiave

Se due aziende emittenti condividessero lo stesso registro, succederebbe una cosa
che **non dà nessun errore**: il contatore è uno solo, quindi i numeri escono tutti
diversi e nessun controllo protesta. A saltare non è l'unicità — è
l'**attribuzione**: nessuna delle due aziende ha più una propria progressione, e
questo è esattamente ciò che un controllo fiscale guarda.

⭐ La soluzione: **un registro appartiene a una sola azienda**, obbligatoriamente, e
il registro entra nella chiave di identità del documento. Così due aziende possono
avere entrambe il documento numero 1 dello stesso anno, senza pestarsi i piedi.

### 6.2 L'anno viene dalla data del documento

Non dalla data in cui qualcuno preme il pulsante. Un documento **datato** dicembre
prende un numero del contatore di dicembre anche se viene emesso a gennaio.

⚠️ È una distinzione che è già costata un difetto: prima di agosto 2026 su alcuni
documenti l'anno lo scriveva un automatismo **alla creazione**, leggendo la data di
quel giorno, mentre il contatore usava la data del documento. Due nozioni di «anno»
sulla stessa riga — e il controllo di unicità usava la prima.

### 6.3 Il numero non torna indietro nel tempo — **solo per le fatture**

Sulle fatture c'è un cancello: non si dà un numero a un documento con data
anteriore all'ultimo già numerato sullo stesso sezionale. È una regola fiscale, e
vive dove c'è il sezionale fiscale.

⛔ Sugli altri documenti **non** si applica, e la ragione è concreta: un documento di
trasporto per la spedizione di ieri, inserito stamattina dopo che ne è già uscito
uno con la data di oggi, è un caso d'uso normale. Applicare lì lo stesso cancello lo
avrebbe reso impossibile.

#### ⭐ E guarda la **sequenza**, non il registro — deciso l'8 settembre 2026

Il cancello confronta la data con l'ultima numerata **sulla stessa sequenza**,
dove una sequenza è la coppia *registro + serie*. Su un registro che emette su
due serie diverse, ciascuna ha il suo calendario e non blocca l'altra.

**Sembra un dettaglio e non lo è.** Se il cancello guardasse il registro intero,
due serie che vanno avanti in parallelo si bloccherebbero a vicenda: emetti sulla
prima con la data di oggi e la seconda — che sta a una data più indietro perché è
un'altra sequenza — non riuscirebbe più a numerare.

⚠️ **Non è teoria**: il registro *Front-office* emette **già** su due serie,
`VX2` e `R2`. E i documenti di trasporto e gli ordini possono portare una serie
**propria**, diversa da quella predefinita del registro: due sequenze parallele
sono una cosa che il modello prevede, non un incidente.

#### La domanda che ne nasce, e la risposta

*«Se cambio la serie predefinita di un registro, riparto senza calendario: non è
un modo per retrodatare un documento?»*

⭐ **No, ed è coperto da un altro cancello.** Cambiare la serie predefinita
significa **aprire una sequenza nuova**, e una sequenza nuova non ha passato: che
riparta anche il calendario è coerente, non è un varco. Contro la retrodatazione
vera esiste il **limite di emissione** (§6.3 sopra e la guida dei limiti), che
guarda il **registro** e la competenza — e che una serie nuova **non azzera**.

⇒ I due cancelli rispondono a due domande diverse, e vanno tenuti distinti:

| Domanda | Chi risponde | Perimetro |
| --- | --- | --- |
| «questa sequenza va avanti?» | il cancello di cronologia | registro **+ serie** |
| «questo documento è ancora emettibile?» | il limite di emissione | **registro** + competenza |

### 6.4 Il codice della commessa contiene la sigla dell'azienda

La **identità** della commessa è la stringa stessa: è il codice a essere unico,
non la coppia registro-numero come negli altri documenti. Quindi la stringa deve
bastare a distinguere due aziende, e la sigla ci entra dentro:

```
CMM-ACME-2026-000000001
 │    │     │      │
 │    │     │      └─ progressivo, riparte da 1 ogni anno — NOVE cifre
 │    │     └──────── anno
 │    └────────────── sigla dell'azienda emittente
 └─────────────────── prefisso, che arriva dal registro
```

⚠️ Ne discende un vincolo sulla **sigla**: solo lettere maiuscole e cifre, da 2 a 10
caratteri, **niente trattino**. Il trattino è il separatore: se comparisse dentro la
sigla, il codice smetterebbe di essere leggibile e nessuno saprebbe più dove finisce
l'azienda e dove comincia l'anno.

⭐ **La commessa è l'unica delle quattro a usare nove cifre**, ed è per questo che è
stata la sola a rivelare un difetto altrimenti invisibile — se ne parla al §9.

> 🔄 **Aggiornamento del 2 settembre 2026.** Fino a quel giorno il fatto che la
> sigla e l'anno fossero *dentro* la stringa era una **convenzione di chi la
> compone**: giusta, e verificabile solo rileggendo il programma. Ora la commessa
> porta l'anno e il registro anche in **due colonne**, e un controllo automatico
> confronta le due cose — se un domani qualcuno cambiasse la composizione senza
> toccare le colonne, o viceversa, se ne accorge un test invece di un cliente.
> ⚠️ L'identità **non è cambiata**: unico resta il codice, e resta unico da solo.

### 6.5 Il separatore non è più un campo a sé

Prima il formato aveva un campo «separatore» accanto al prefisso. Oggi non c'è più:
**se serve un separatore, si scrive dentro il prefisso** (`CMM-`).

⭐ Non è una semplificazione estetica. Con due campi distinti, un prefisso vuoto
lasciava il separatore **orfano in testa** — `-ACME-2026-000000001` — e chi spezzava
quel codice sul trattino si ritrovava un primo pezzo vuoto. Un caso speciale che la
commessa aveva e gli altri no, sparito insieme al campo.

### 6.6 I numeri già assegnati non si rifanno

Nessuna rinumerazione del pregresso, per nessun documento. I documenti numerati
prima di agosto 2026 non hanno il registro e in alcuni casi nemmeno l'anno: **è
storia**, e resta com'è. Non collidono con i nuovi perché **la forma è diversa** —
ed è l'unica cosa che li separa, quindi chi cambia il formato dei numeri nuovi sta
toccando anche la ragione per cui non collidono con i vecchi.

### 6.7 ⛔ I contatori sono stati allineati al massimo già emesso

Il giorno del trasloco è successa una cosa che merita un paragrafo suo: i contatori
dei registri partivano da zero, mentre i documenti vecchi erano arrivati per esempio
a `ORD0040688`. Il primo ordine nuovo ha ricevuto `ORD0000001` — **un numero già
usato anni prima**, con la stessa identica forma.

⛔ E il controllo di unicità non se n'è accorto, per una ragione che vale la pena
capire: le righe vecchie non hanno un registro, le nuove sì, e **due righe che
differiscono per un campo vuoto contro un campo pieno non collidono mai**. Il
vincolo c'era, e taceva.

⭐ La riparazione ha portato ogni contatore **almeno** al massimo progressivo già
emesso dalla stessa azienda in quell'anno, ed è scritta come **regola** e non come
elenco: vale anche per il prossimo contatore che nascesse indietro.

⚠️ **Ne resta una conseguenza da conoscere:** un contatore non torna mai indietro,
quindi allinearlo lascia dei buchi nella progressione — i numeri fra l'ultimo
davvero emesso e il massimo storico. È il prezzo accettato, ed è molto più basso di
un numero doppio.

---

## 7. Quando un numeratore deve **traslocare** sui registri

Il criterio in una frase:

> **Il periodo il generatore se lo calcola da sé; l'azienda, la serie e un momento
> diverso dalla creazione arrivano dalla riga.**

Chi ha bisogno di una di queste tre cose sta chiedendo i **registri**, non un
allargamento del catalogo dei formati. In pratica, **se anche uno solo di questi
campanelli suona**, il numeratore è nel posto sbagliato:

1. *«Ogni azienda deve avere la sua numerazione.»* Il catalogo dei formati non può
   saperlo: il meccanismo che assegna il codice è **uno per tabella** e non riceve la
   riga, quindi non sa di chi sia il documento.
2. *«Il numero deve ripartire da 1 a Capodanno.»* Il contatore del catalogo dei
   formati **non sa cosa sia un anno**. Non è una configurazione mancante: è il
   meccanismo a non prevederlo.
3. *«Il numero non deve uscire alla creazione, ma alla conferma.»* Il catalogo dei
   formati assegna sempre alla creazione.

⚠️ Un quarto campanello, più sottile: se lo stesso documento deve poter girare su
**più serie**, la serie è una dimensione del contatore e nel catalogo dei formati
non c'è.

### ⛔ E il trasloco si finisce, non si lascia a metà

La lezione del 31 agosto 2026, in una riga: **spostare un numeratore vuol dire
spostare il contatore E la forma.** Fermarsi al contatore lascia una riga monca in
una tabella di configurazione, con dei campi che nessuno legge più e che qualcuno
prima o poi proverà a cambiare.

La checklist operativa aggiornata sta nella scheda tecnica di
[`config.sistema_codici`](/dbzero/config/manual/sistema_codici).

---

## 8. ⛔ Un'idea valutata e **scartata**: la colonna che rappresenta l'unicità

*(valutata il 31-08-2026)*

**L'idea.** Aggiungere a ogni documento una colonna che rappresenti la sua identità,
composta automaticamente dai valori delle altre colonne — qualcosa come
`2581/2026/A/DDT0000123` — così che l'unicità stia in **un posto solo, uguale
ovunque**, e ogni azienda possa eventualmente definirsela a modo proprio.

L'idea nasceva da un'osservazione **giusta**: le forme di identità oggi sono tre
diverse su sette documenti, e fino ad agosto 2026 **due di esse non funzionavano
affatto** senza che nessuno se ne accorgesse.

**Perché è stata scartata.** Tre ragioni, in ordine di peso.

**1. L'unicità non può essere una preferenza dell'azienda.** Se due aziende nella
stessa installazione avessero regole di identità diverse sulla stessa tabella, il
controllo dovrebbe valere su entrambe insieme — e un controllo che dipende da *chi
ha scritto la riga* non è più un controllo del database, ma una regola nel
programma, con tutte le fragilità che si era appena finito di togliere.
⭐ E soprattutto: **l'unicità per azienda esiste già**. È il registro. «La mia
azienda vuole la sua numerazione» oggi si traduce in: il mio registro, il mio
contatore, il mio anno, la mia serie — e da fine agosto anche il mio prefisso e il
mio suffisso.

**2. L'uniformità sarebbe stata solo nel nome.** Le tabelle non hanno le stesse
colonne — i resi non hanno la serie, la commessa non ha un campo «numero» perché
il suo numero è il codice. Sotto un nome
uguale ovunque ci sarebbero state **sette formule diverse**. È il tipo di uniformità
che fa più danno di nessuna uniformità: chi legge un nome uguale smette di chiedersi
cosa c'è sotto, e trova una regola sola dove ce ne sono sette.

**3. Il costo era reale e il guadagno indiretto.** Aggiungere una colonna calcolata
comporta la **riscrittura completa** di ogni tabella coinvolta; e ogni documento
nuovo avrebbe dovuto *ricordarsi* di averla — cioè un elenco parallelo da tenere
allineato, esattamente ciò che si era appena finito di eliminare.

**Che cosa si è fatto al posto suo.** Il bisogno vero dietro l'idea era **accorgersi
quando una regola di identità smette di funzionare**. Per quello non serve una
colonna: serve un **controllo automatico** che, per ogni famiglia di documento
registrata a catalogo, verifichi che l'identità distingua l'azienda e che l'anno sia
davvero in chiave.

⭐ È stato scritto, e ha una proprietà che la colonna non avrebbe avuto: **non elenca
i documenti, li legge dal catalogo**. Il giorno in cui si registra una famiglia
nuova, il controllo la copre da solo.

ℹ️ Resta possibile, se un domani servisse **leggere** l'identità completa in un
export o in una ricerca trasversale, esporla con una vista — senza toccare nessuna
tabella. La colonna tornerebbe sul tavolo solo se quell'identità dovesse essere
**indicizzata**, ed è una ragione che oggi non esiste.

---

## 8-bis. ⭐ La chiave del contatore: gli assi si **dichiarano**, non si assumono

*(rev 2026-09-01)*

Il §8 qui sopra si chiude chiedendo *«un controllo automatico che, per ogni
famiglia di documento registrata a catalogo, verifichi che l'identità distingua
l'azienda e che l'anno sia davvero in chiave»*. ⭐ **Quel controllo ora esiste**,
e per scriverlo è venuta fuori la regola che lo governa.

### La regola

> **Tutto ciò che discrimina il CONTATORE deve poter discriminare anche il
> DOCUMENTO.**

Il contatore vive su una chiave — oggi `(registro, anno, serie)` — e ogni
combinazione è un **secchio** che riparte da 1. Se il documento non porta uno di
quegli assi nel proprio vincolo di unicità, il contatore gli consegna un numero
che per lui **è già usato**.

⭐ **E i due versi non sono simmetrici** — è questo che dice quale asse va
dichiarato:

| | Effetto |
| --- | --- |
| il **contatore** ha un asse che il **documento** non ha | ⛔ **collisione** |
| il **documento** ha un asse che il **contatore** non ha | ✅ innocuo — il documento è solo più specifico |

### ⛔ Il difetto che c'era, e il §8 lo aveva già sfiorato

Il §8 osserva che *«i resi non hanno la serie, la commessa non ha un campo
numero»*.
Era vero, ed era **più grave di come suonava**: la serie entra nella chiave del
contatore, quindi cambiare il `serie_default` di un registro `RESO` avrebbe fatto
ripartire il progressivo da 1 su numeri già emessi — con `uq_resi_anno_numero`
che non porta la serie, il vincolo rifiuta, e col rollback torna indietro anche
l'incremento del contatore. ⇒ **Il reso non si numerava più.**

### ✅ La cura: la famiglia dichiara l'asse

Non si è data la colonna `serie` ai resi — sistemava il **sintomo su una
tabella**, e il sesto documento che entra domani avrebbe avuto lo stesso problema
senza che nessuno gliel'avesse chiesto.

⭐ La domanda si fa **dove una famiglia entra nei registri**:
`vendite.famiglie_documento.colonna_serie` — il **nome** della colonna in cui
quella famiglia registra la serie, `NULL` se non ne ha una.

| Cosa | Dove sta | Che natura ha |
| --- | --- | --- |
| `serie` sul documento | `fatture.serie`, `ddt.serie`, `ordini.serie` | **il fatto** |
| `serie_default` | `registri_fatturazione` | **la scelta** del sezionale |
| `colonna_serie` | `famiglie_documento` | **la capacità** della famiglia |

> **Sulla FAMIGLIA si dichiara ciò che il documento PUÒ esprimere. Sul REGISTRO
> si sceglie ciò che quel sezionale FA.**

⭐ **Il nome e non un booleano**, per la stessa ragione di `colonna_numero`: un
flag «gestisce la serie» messo su una famiglia la cui tabella non ce l'ha
riporterebbe il difetto senza che nessuno se ne accorga; col nome, il controllo
verifica che la colonna **esista davvero**.

⛔ E un registro di una famiglia senza serie **non può averne una**: si rifiuta,
non si ignora. Un campo editabile che non fa niente è il difetto che il trasloco
del prefisso ha appena finito di togliere (§7).

### 🔴 Due cose sono sparite dal contatore

**`mese` non c'è più.** Stava nella chiave e **in nessun documento**. Era innocua
solo perché inchiodata: `mese = 0` nella funzione e un `CHECK` che ammetteva il
solo `ANNUALE`.

⛔ **Una dimensione dormiente in una chiave è ARMATA, non inutilizzata**: il
giorno che qualcuno avesse acceso un reset mensile sarebbero collidati **tutti e
cinque** i documenti. E a tenerla chiusa non era un vincolo, era una **rinuncia**
— che si revoca per distrazione. Se un giorno servirà, l'asse torna **insieme**
alla colonna sui documenti, dichiarato come lo è `colonna_serie`.

**E con lei un `UNIQUE` ridondante** che nessuno vedeva: con quattro colonne
`NOT NULL`, i `COALESCE` di `uq_registri_progressivi_scope` erano no-op e la
chiave era la **stessa** di `uq_regprog_key`. ⚠️ Il presidio degli indici
duplicati non lo segnalava, perché confronta colonne e lì una chiave era colonne
e l'altra espressioni.

### ✅ E `reset_policy` adesso funziona davvero

Era **dichiarata e mai letta**: nessuna funzione ci ramificava sopra e l'anno era
inchiodato nel codice. Ora `fn_get_next_progressivo` la legge:

| `reset_policy` | L'anno del secchio | Effetto |
| --- | --- | --- |
| `ANNUALE` | l'anno solare del documento | il numero riparte da 1 a Capodanno |
| `NESSUNA` | `0` — un secchio solo | numerazione **continua** fra gli anni |

⛔ **`MENSILE` non è rientrata**, ed è l'asimmetria della regola: accenderla
sarebbe **pericoloso** (nessun documento porta il mese), mentre `NESSUNA` è
**sicura** perché fa usare al contatore **meno** assi, non di più — e l'anno ce
l'hanno tutti.

⚠️ **E due cose si chiamano «anno»**: quello del **secchio** (`progressivi.anno`,
che vale `0` sotto `NESSUNA`) e quello del **documento** (`fatture.anno`,
`ddt.anno`, …), che è sempre l'anno solare. `fn_get_anno_registro` risponde alla
seconda domanda, e per questo non è stata toccata.

#### ⚠️ E cambiare politica su un registro che ha già numerato

La politica si può cambiare, ma il momento in cui la si cambia conta. Il
contatore vive in un «secchio» identificato dall'anno: passando da `ANNUALE` a
`NESSUNA` (o viceversa) la chiave del secchio cambia, quindi ne nasce uno nuovo —
e un secchio nuovo, fino all'8 settembre 2026, **partiva da zero**.

⛔ **Cosa succedeva davvero**, ed è stato provato prima di ripararlo: il registro
aveva già emesso i numeri 1 e 2; cambiata la politica, il documento successivo
chiedeva il numero **1**. Quel numero, nell'anno del documento, esisteva già: la
scrittura veniva respinta, e con l'annullamento tornava indietro anche il
contatore. Al tentativo dopo ricominciava da 1 e sbatteva di nuovo — cioè **un
numeratore piantato**, con un errore che parlava del numero e non nominava la
causa.

✅ **Ora un secchio nuovo nasce dal numero più alto di quelli con cui potrebbe
scontrarsi**, quindi la numerazione prosegue e il cambio di politica è
un'operazione sicura, nei due versi.

⛔ **E non "dal numero più alto in assoluto"**: sotto `ANNUALE` il primo documento
dell'anno **deve** ripartire da 1, ed è tutto il senso della politica. Si guardano
solo i secchi che possono davvero scontrarsi — cioè quelli i cui documenti
condividono un anno di calendario.

### Il controllo automatico che il §8 chiedeva

Tre verifiche, tutte **derivate** — nessun elenco scritto a mano:

1. ogni famiglia che dichiara una serie ha **davvero** quella colonna;
2. ...e quella colonna sta nel **vincolo di unicità del numero**;
3. nessun registro di una famiglia senza serie porta un `serie_default`.

Una famiglia nuova che entra sui registri senza la chiave completa fa **rosso
prima del merge**, invece che in campo.

### ✅ E il pezzo che restava scoperto è stato chiuso — 2 settembre 2026

Fino al 2 settembre `vendite.commesse` era **l'unica delle cinque** la cui
identità è una stringa nuda: dichiarava di non avere una serie — quindi i
controlli la proteggevano — ma registro e anno stavano solo *dentro* il codice,
per convenzione di chi lo compone.

⛔ **Perché era un debito e non un dettaglio**: quell'invariante nessuno la
imponeva. Il giorno che al contatore si fosse aggiunto un asse senza toccare la
composizione della stringa, il codice sarebbe tornato a ripetersi al primo cambio
di periodo — e sarebbe uscito come un errore di duplicato, in mezzo a
un'elaborazione che con la numerazione non c'entra.

⭐ **La cura, ed è più piccola di come sembrava.** Guardando le altre quattro si è
visto che il loro campo «numero» contiene la **stringa già formattata**, non il
progressivo nudo: sulla commessa quella stringa è il codice, che c'era già.
Mancavano solo **due colonne** — registro e anno — e nessun numero da inventare
per le righe vecchie.

⚠️ **E il riempimento delle righe esistenti non ha ricostruito niente a mano**: il
registro lo ha *chiesto* alla funzione che già risponde a «quale registro per
questo documento», invece di riscriverne la regola. Riscrivendola si sarebbe
sbagliato — le commesse hanno un'utility e i loro registri valgono «per tutte»,
quindi un accostamento ingenuo non avrebbe trovato **nessuna** riga.

⇒ Oggi l'invariante è **verificata da un controllo automatico**, non affidata a
chi rilegge: il codice deve portare la sigla e l'anno che le colonne dichiarano.
L'identità, però, resta il codice — ed è più stretta di quella degli altri
quattro, perché porta la sigla dell'azienda e quindi non si ripete mai fra
registri diversi.

---

## 8-ter. ⭐ L'anno **dentro** il numero — 8 settembre 2026

> Osservazione di Tid: *«gli ordini hanno l'azzeramento annuale ma il numero non
> mostra l'anno: `ORD0036007`»*.

### Il difetto, in una riga

Se la numerazione riparta ogni anno **e** il numero non porta l'anno, allora il
1° gennaio la stessa identica stringa torna su un documento diverso. `ORD0000001`
del 2026 e `ORD0000001` del 2027 sono due ordini diversi con lo stesso numero
scritto sopra.

⚠️ **Il database non se ne accorge**, e questo è il punto: la sua regola di
unicità l'anno ce l'ha in una colonna a parte, quindi nessuna scrittura fallisce.
L'ambiguità non è nei dati — è **nella stringa che una persona legge**: in una
lista, in una ricerca, o al telefono quando un cliente cita un numero.

⭐ È la stessa regola del §8-bis, un piano più su: *tutto ciò che distingue il
contatore deve poter distinguere anche il numero che si legge*.

### La cura: si dichiara, non si assume

Come per la serie, la scelta sta in due posti diversi e complementari:

| Dove | Cosa dice |
| --- | --- |
| **la famiglia** (`anno_nel_numero_default`) | *«i documenti di questo tipo portano l'anno dentro il numero»* — è il default |
| **il registro** (`anno_nel_numero`) | *«questo sezionale lo fa»* — è l'effettivo, come il prefisso |

E alla nascita di un registro il valore **si risolve da solo**: un sezionale che
azzera per anno, di una famiglia che espone l'anno, nasce già con l'anno nel
numero. ⭐ **Non è una domanda che si fa a chi crea il registro**: è una
conseguenza di due cose che ha già scelto — la politica e la famiglia.

Il numero diventa così: `DDT` + `2026-` + `0023456` → **`DDT2026-0023456`**.

### ⛔ Le due famiglie che non lo fanno, e non è una dimenticanza

* **La fattura**: il suo numero è il progressivo **nudo** (`101`), e anno e serie
  viaggiano in colonne a parte — è la convenzione fiscale, ed è la stampa a
  ricomporli (*«N. 101 / Serie VX1 / 2026»*). Mettere l'anno dentro la stringa
  cambierebbe il numero di una fattura.
* ⭐ **La commessa lo fa, ma per una strada diversa da prima.** Il suo codice
  l'anno lo portava già — `CMM-<sigla>-<anno>-<9 cifre>` — solo che glielo
  metteva un pezzo di codice **suo**, diverso da quello di tutti gli altri.
  Decisione di Tid: *«la commessa deve diventare standard, tutti devono avere gli
  stessi parametri»*. Ora l'anno glielo mette lo stesso meccanismo degli altri, e
  **il codice esce identico carattere per carattere** — verificato sui codici già
  esistenti prima di applicare.

### ⚠️ Una cosa da sapere prima di chiederla su un registro vecchio

L'anno nel numero è **forma del numero**, come il prefisso: su un sezionale che
ha già consegnato dei numeri **non si può aggiungere**. Il motivo è lo stesso del
§6.6 — il contatore non riparte quando cambia la forma, prosegue, e sullo stesso
registro convivrebbero due forme con numeri consecutivi, senza modo di
distinguerle.

⇒ La scelta si fa **alla nascita** del registro. Su un sezionale già in uso
l'alternativa è l'altra: se la sua numerazione non riparte (politica `NESSUNA`),
il numero non si ripete e l'anno non serve.

## 9. ⚠️ Un difetto trovato il giorno stesso, e cosa insegna

*(31-08-2026, sera)*

Tolte le quattro righe dal catalogo dei formati, la funzione che compone i numeri
**continuava a cercarle lì** per sapere quante cifre usare. Non trovandole più, si
appoggiava al valore di ripiego: **sette cifre**.

| | quante cifre vuole | quante ne otteneva |
| --- | --- | --- |
| DDT, ordine, reso | 7 | 7 — **giusto per caso** |
| Commessa | 9 | **7** |

⛔ Nessun errore, nessun vincolo violato: solo una commessa con un codice più corto
— `CMM-ACME-2026-0000007` invece di `CMM-ACME-2026-000000007`. E la forma è proprio
ciò che, secondo il §6.6, tiene separati i codici nuovi da quelli vecchi.

**Tre cose che questo caso insegna, e che valgono ben oltre la numerazione:**

1. ⛔ **Prima di cancellare una fonte si censiscono i suoi lettori.** I controlli
   messi a protezione della cancellazione verificavano che la **sede nuova** fosse
   piena — i registri col prefisso, le famiglie coi default — e **nessuno chiedeva
   chi leggesse ancora quella vecchia**. È l'inventario giusto della metà sbagliata.
2. ⚠️ **Il valore di ripiego che coincide col valore giusto nasconde il difetto.**
   Tre famiglie su quattro passavano, perché il ripiego valeva esattamente quanto
   dovevano avere. Il caso che ha parlato è stato l'unico diverso — e il difetto era
   lì da ore.
3. ⚠️ **Le descrizioni superate non sono rumore: sono prove false.** Quattro
   descrizioni nel database dicevano ancora che la lunghezza «resta nel catalogo dei
   formati». Chi indagava le leggeva per prime e ne concludeva che quel pezzo era
   già a posto.

⭐ Il presidio che ne è nato non guarda un documento: guarda il **codice**, e
pretende che nessuna funzione dell'area vendite legga più il catalogo dei formati.
Copre da sola anche il generatore che qualcuno scrivesse domani.

---

## 10. Dove guardare

* [`config.sistema_codici`](/dbzero/config/manual/sistema_codici) — il catalogo dei
  formati, con la checklist del trasloco
* [`vendite.registri_fatturazione`](/dbzero/vendite/manual/registri_fatturazione) —
  i registri di numerazione, con prefisso, suffisso e lunghezza
* [`vendite.famiglie_documento`](/dbzero/vendite/manual/famiglie_documento) — quali
  documenti si numerano su un registro, dove vivono e **con quale forma nascono**
* [`vendite.fn_assegna_numero_documento`](/dbzero/vendite/manual/fn_assegna_numero_documento) —
  i sei passi, in una sede sola
* [`vendite.fn_componi_numero_documento`](/dbzero/vendite/manual/fn_componi_numero_documento) —
  la composizione della stringa, pura e verificabile in una riga
* [`vendite.fn_get_next_progressivo`](/dbzero/vendite/manual/fn_get_next_progressivo) —
  il contatore: la politica di azzeramento e il seme del secchio nuovo

**I cantieri che hanno prodotto queste regole**, per chi cerca il *perché* con
tutte le misure e le strade scartate:

* [brief-db-registri-numerazione-chiave-del-contatore](../dev/work-in-progress/brief-db-registri-numerazione-chiave-del-contatore.md)
  — gli assi dichiarati (§8-bis), il passaggio di politica e l'anno dentro il
  numero (§8-ter)
* [brief-db-prefisso-sul-registro-e-allineamento-contatori](../dev/work-done/brief-db-prefisso-sul-registro-e-allineamento-contatori.md)
  — la forma del numero sul registro
* [brief-be-fe-crud-registri-di-numerazione](../dev/work-done/brief-be-fe-crud-registri-di-numerazione.md)
  — la maschera e le regole di modifica
