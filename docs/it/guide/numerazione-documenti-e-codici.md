# Guida – Numerazione dei documenti e codici automatici

> **Ultimo aggiornamento:** 14 settembre 2026
>
> **Destinatari:** chiunque debba capire come nasce un numero o un codice in ZeroErp — sviluppatori database, backend, frontend e analisti funzionali
>
> **Prerequisiti:** nessuno. Le parti tecniche stanno in fondo a ogni capitolo. La guida descrive **come funziona oggi**; il *perché*, con le misure e le strade scartate, sta nei brief elencati in fondo (§10).

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

⭐ **Questa tabella descrive solo cose che genera davvero**: nessuna riga per i
documenti che si numerano sui registri. Una riga che non conta più niente
resterebbe visibile nel pannello di configurazione con un prefisso che **nessuno
legge**: un amministratore che lo cambia non ottiene alcun effetto, e non ha
modo di accorgersene. Lo pretende un presidio (§9).

### 2.2 Il **motore dei registri** — `vendite.registri_fatturazione`

Un **registro** è un sezionale di numerazione: appartiene a **una** azienda
emittente, tiene il proprio contatore, sa ripartire da 1 a ogni Capodanno e
porta anche la **forma** del numero che produce: prefisso, suffisso, quante
cifre, e se l'anno sta dentro il numero.

**Chi lo usa, oggi** — fatture, documenti di trasporto, ordini, commesse, resi
e, dal 2026-09-15, le **distinte contabili di incasso** (la prima famiglia
fuori da `vendite`).

⚠️ **Il nome della tabella dice meno di quello che fa.** Si chiama
`registri_fatturazione` perché all'inizio numerava solo le fatture; oggi numera
sei famiglie di documento. Il nome non è stato cambiato di proposito: cambiarlo
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

⚠️ **Formato e contatore stanno nello stesso posto**, per ogni documento: un
numeratore che tenesse il contatore sul registro e la forma nel catalogo dei
formati lascerebbe di là una riga **monca**, che non dà errore ma confusione —
ed è il motivo della regola del §7.

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

| Documento / entità | Formato | Contatore | Quando riceve il numero |
| --- | --- | --- | --- |
| **Fattura** | *nessuno* (vedi sotto) | **registro** | all'emissione |
| **DDT** | **registro** | **registro** | quando passa a *emesso* |
| **Ordine** | **registro** | **registro** | alla creazione |
| **Reso** | **registro** | **registro** | quando passa a *confermato* |
| **Commessa** | **registro** | **registro** | alla creazione |
| **Distinta contabile** *(dal 2026-09-15)* | **registro** | **registro** | alla creazione |
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
  *è* il suo numero. ⭐ Porta però anche l'anno e il registro in **due colonne
  proprie**, come gli altri, e un controllo automatico pretende che il codice e
  le colonne dicano la stessa cosa (§8-bis). **La distinta contabile fa lo
  stesso** (`DIS-ACME-2026-0000001`, sette cifre): è il secondo documento con
  l'identità a stringa, e la ragione è la stessa (§6.4).

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

Assegnare un numero sono **sei passi**: trovare il registro, ricavare l'anno
dalla data, chiedere il progressivo, leggere il formato, comporre la stringa,
scrivere le colonne. Stanno in **una funzione sola**
(`vendite.fn_assegna_numero_documento`), e i generatori dei singoli documenti
conservano l'unica cosa che li distingue davvero: **il momento**. Il documento
di trasporto numera all'emissione, il reso alla conferma, ordine e commessa alla
creazione — quello resta scritto ciascuno a casa propria, perché è la sola cosa
che non hanno in comune.

⛔ **Perché una sede sola, e non una copia per documento**: di quattro copie se
ne possono correggere tre. Una modifica al modo di comporre il numero fatta in
tre posti su quattro produce un documento formattato diversamente dagli altri —
che **nessun controllo respinge**, perché è un numero valido, solo diverso.

### ⭐ La composizione si prova in una riga

La parte che compone la stringa (`vendite.fn_componi_numero_documento`) è una
funzione **pura**: riceve dei valori e restituisce una stringa, senza leggere
niente. Per verificare che un numero venga formattato bene non serve fabbricare
un documento intero — con le sue righe, l'indirizzo, la causale e la transizione
di stato — basta una riga di prova con i valori che si vogliono.

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

⚠️ La colonna `anno` del documento e l'anno del contatore vengono dalla **stessa
data**. Un automatismo che scrivesse l'anno alla creazione leggendo la data di
quel giorno, mentre il contatore usa la data del documento, metterebbe due
nozioni di «anno» sulla stessa riga — e il controllo di unicità userebbe la
prima.

### 6.3 Il numero non torna indietro nel tempo — **solo per le fatture**

Sulle fatture c'è un cancello: non si dà un numero a un documento con data
anteriore all'ultimo già numerato sullo stesso sezionale. È una regola fiscale, e
vive dove c'è il sezionale fiscale.

⛔ Sugli altri documenti **non** si applica, e la ragione è concreta: un documento di
trasporto per la spedizione di ieri, inserito stamattina dopo che ne è già uscito
uno con la data di oggi, è un caso d'uso normale. Applicare lì lo stesso cancello lo
avrebbe reso impossibile.

#### ⭐ E guarda la **sequenza**, non il registro

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

### 6.4 Il codice della commessa contiene la sigla dell'azienda — e quello della distinta pure

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

⭐ **La commessa è l'unica a usare nove cifre**, ed è per questo che è stata la
sola a rivelare un difetto altrimenti invisibile — se ne parla al §9.

⭐ **Dal 2026-09-15 vale anche per la distinta contabile di incasso**
(`DIS-ACME-2026-0000001`, sette cifre): la stessa forma, per la stessa ragione.
Il suo codice era un'etichetta da DEFAULT (`VC_…`) e la distinta era l'unico
documento numerabile che non dichiarava il proprio emittente; oggi lo porta in
colonna, e un registro `DIS-` per azienda le dà il numero alla creazione, come
all'ordine. Come e da chi l'emittente si ricava — dato, canale di incasso,
operatore in sessione, o rifiuto — sta nella scheda di
[pagamenti.vendite_contabili](/dbzero/pagamenti/manual/vendite_contabili).

> ⭐ Che la sigla e l'anno stiano *dentro* la stringa non è solo una convenzione
> di chi la compone: la commessa porta l'anno e il registro anche in **due
> colonne**, e un controllo automatico confronta le due cose — se qualcuno
> cambiasse la composizione senza toccare le colonne, o viceversa, se ne accorge
> un test invece di un cliente. ⚠️ L'identità resta il codice, unico da solo.

### 6.5 Il separatore non è un campo a sé

La forma sul registro non ha un campo «separatore» accanto al prefisso: **se
serve un separatore, si scrive dentro il prefisso** (`CMM-`).

⭐ Non è una semplificazione estetica. Con due campi distinti, un prefisso vuoto
lascerebbe il separatore **orfano in testa** — `-ACME-2026-000000001` — e chi
spezza quel codice sul trattino si ritroverebbe un primo pezzo vuoto.

### 6.6 I numeri già assegnati non si rifanno

Nessuna rinumerazione del pregresso, per nessun documento. I documenti numerati
**prima** che la loro famiglia passasse sui registri non hanno il registro e in
alcuni casi nemmeno l'anno: **è storia**, e resta com'è. Non collidono con i nuovi
perché **la forma è diversa** — ed è l'unica cosa che li separa, quindi chi cambia
il formato dei numeri nuovi sta toccando anche la ragione per cui non collidono
con i vecchi.

### 6.7 ⛔ Un contatore non nasce mai sotto il massimo già emesso

Un contatore che partisse da zero su una famiglia che ha già documenti
consegnerebbe un numero **già usato**, con la stessa identica forma (`ORD0000001`
dopo un `ORD0040688`). ⛔ E il controllo di unicità non se ne accorgerebbe: le
righe vecchie non hanno un registro, le nuove sì, e **due righe che differiscono
per un campo vuoto contro un campo pieno non collidono mai**. Il vincolo c'è, e
tace.

⭐ Per questo ogni contatore nasce **almeno** al massimo progressivo già emesso
dalla stessa azienda in quell'anno — scritto come **regola** e non come elenco:
vale per un registro nuovo, per un contatore rimasto indietro, e per il secchio
nuovo che nasce cambiando politica di azzeramento (§8-bis).

⚠️ **Ne discende una conseguenza da conoscere:** un contatore non torna mai
indietro, quindi allinearlo lascia dei buchi nella progressione — i numeri fra
l'ultimo davvero emesso e il massimo storico. È il prezzo accettato, ed è molto
più basso di un numero doppio.

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

**Spostare un numeratore vuol dire spostare il contatore E la forma.** Fermarsi
al contatore lascia una riga monca in una tabella di configurazione, con dei
campi che nessuno legge più e che qualcuno prima o poi proverà a cambiare.

La checklist operativa aggiornata sta nella scheda tecnica di
[`config.sistema_codici`](/dbzero/config/manual/sistema_codici).

---

## 8. ⛔ Un'idea valutata e **scartata**: la colonna che rappresenta l'unicità

**L'idea.** Aggiungere a ogni documento una colonna che rappresenti la sua identità,
composta automaticamente dai valori delle altre colonne — qualcosa come
`2581/2026/A/DDT0000123` — così che l'unicità stia in **un posto solo, uguale
ovunque**, e ogni azienda possa eventualmente definirsela a modo proprio.

L'idea nasceva da un'osservazione **giusta**: le forme di identità sono tre
diverse su sette documenti, e una forma che smette di funzionare **non dà nessun
errore**.

**Perché è stata scartata.** Tre ragioni, in ordine di peso.

**1. L'unicità non può essere una preferenza dell'azienda.** Se due aziende nella
stessa installazione avessero regole di identità diverse sulla stessa tabella, il
controllo dovrebbe valere su entrambe insieme — e un controllo che dipende da *chi
ha scritto la riga* non è più un controllo del database, ma una regola nel
programma, con tutte le fragilità che si era appena finito di togliere.
⭐ E soprattutto: **l'unicità per azienda esiste già**. È il registro. «La mia
azienda vuole la sua numerazione» oggi si traduce in: il mio registro, il mio
contatore, il mio anno, la mia serie, il mio prefisso e il mio suffisso.

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

⭐ Esiste (§8-bis), e ha una proprietà che la colonna non avrebbe avuto: **non
elenca i documenti, li legge dal catalogo**. Il giorno in cui si registra una famiglia
nuova, il controllo la copre da solo.

ℹ️ Resta possibile, se un domani servisse **leggere** l'identità completa in un
export o in una ricerca trasversale, esporla con una vista — senza toccare nessuna
tabella. La colonna tornerebbe sul tavolo solo se quell'identità dovesse essere
**indicizzata**, ed è una ragione che oggi non esiste.

---

## 8-bis. ⭐ La chiave del contatore: gli assi si **dichiarano**, non si assumono

Il §8 qui sopra chiede *«un controllo automatico che, per ogni famiglia di
documento registrata a catalogo, verifichi che l'identità distingua l'azienda e
che l'anno sia davvero in chiave»*. ⭐ **Quel controllo esiste**, e questa è la
regola che lo governa.

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

### ⛔ Che cosa succede quando un asse non è dichiarato

L'esempio è la **serie sui resi**. La serie entra nella chiave del contatore: se
il vincolo di unicità del reso non la porta, cambiare il `serie_default` del
registro `RESO` fa ripartire il progressivo da 1 su numeri già emessi — il
vincolo rifiuta, col rollback torna indietro anche l'incremento del contatore, e
**il reso non si numera più**.

⛔ Dare la colonna `serie` ai resi sistemerebbe il **sintomo su una tabella**: il
sesto documento che entra domani avrebbe lo stesso problema senza che nessuno
gliel'abbia chiesto.

### La famiglia dichiara l'asse

⭐ La domanda si fa **dove una famiglia entra nei registri**:
`vendite.famiglie_documento` dichiara, per ogni famiglia, il **nome** della
colonna con cui il documento esprime ciascun asse — `NULL` se quel documento non
ce l'ha:

| Cosa | Dove sta | Che natura ha |
| --- | --- | --- |
| `serie` sul documento | `fatture.serie`, `ddt.serie`, `ordini.serie` | **il fatto** |
| `serie_default` | `registri_fatturazione` | **la scelta** del sezionale |
| `colonna_serie` | `famiglie_documento` | **la capacità** della famiglia: `NULL` per resi e commesse |
| `colonna_billing_account` | `famiglie_documento` | **la capacità** di portare un cliente: `NULL` per una famiglia la cui controparte non è un billing account (l'ordine di acquisto, che ha un fornitore) |
| `colonna_numero` | `famiglie_documento` | dove il documento scrive il numero — sempre dichiarata |

> **Sulla FAMIGLIA si dichiara ciò che il documento PUÒ esprimere. Sul REGISTRO
> si sceglie ciò che quel sezionale FA.**

⭐ **Il nome e non un booleano**, per la stessa ragione di `colonna_numero`: un
flag «gestisce la serie» messo su una famiglia la cui tabella non ce l'ha
riporterebbe il difetto senza che nessuno se ne accorga; col nome, il controllo
verifica che la colonna **esista davvero** — e la verifica salta gli assi
dichiarati `NULL`, prima di comporre qualunque query.

⛔ E un registro di una famiglia senza serie **non può averne una**: si rifiuta,
non si ignora. Un campo editabile che non fa niente è esattamente il difetto
della riga monca del §7.

⚠️ **Le famiglie senza billing account saltano** nei lettori che ricostruiscono
la storia di un cliente per emittente (`fn_ba_ha_storia_emittente`,
`fn_get_storia_emittente_ba`): un documento senza cliente non può contribuire
alla storia di nessun cliente. Il CRUD delle famiglie tratta la colonna come
facoltativa, esattamente come la serie
([api_famiglie_documento](/backend/vendite/manual/api_famiglie_documento)).

### La chiave del contatore non ha un asse `mese`, ed è voluto

La chiave è `(registro, anno, serie)`. Un asse `mese` **non c'è**, e non deve
tornare senza la colonna sui documenti: ⛔ **una dimensione dormiente in una
chiave è ARMATA, non inutilizzata** — il giorno che qualcuno accendesse un reset
mensile senza che nessun documento porti il mese, colliderebbero **tutti e
cinque** i documenti. Se un giorno servirà, l'asse torna **insieme** alla colonna
sui documenti, dichiarato come lo è `colonna_serie`.

### `reset_policy` — la politica del contatore

`fn_get_next_progressivo` la legge:

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

La politica si può cambiare anche su un registro che ha già numerato. Il
contatore vive in un «secchio» identificato dall'anno: passando da `ANNUALE` a
`NESSUNA` (o viceversa) la chiave del secchio cambia, quindi ne nasce uno nuovo
— e **un secchio nuovo nasce dal numero più alto di quelli con cui potrebbe
scontrarsi** (§6.7), quindi la numerazione prosegue e il cambio è un'operazione
sicura, nei due versi. Un secchio che partisse da zero chiederebbe un numero che
nell'anno del documento esiste già: scrittura respinta, contatore riportato
indietro dal rollback, e al tentativo dopo di nuovo da capo — un numeratore
piantato, con un errore che parla del numero e non nomina la causa.

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

### La commessa: identità a stringa, assi dichiarati lo stesso

`vendite.commesse` è **l'unica delle cinque** la cui identità è una stringa
nuda, il codice. Dichiara di non avere una serie, e registro e anno — che
stanno *dentro* il codice — li porta anche in **due colonne**, come gli altri
quattro portano la stringa formattata nel campo «numero» accanto alle colonne
di anno e registro. ⇒ L'invariante «il codice porta la sigla e l'anno che le
colonne dichiarano» è **verificata da un controllo automatico**, non affidata a
chi rilegge: se al contatore si aggiungesse un asse senza toccare la
composizione della stringa, lo direbbe un test e non un errore di duplicato in
mezzo a un'elaborazione che con la numerazione non c'entra. L'identità resta il
codice — più stretta di quella degli altri quattro, perché porta la sigla
dell'azienda e non si ripete mai fra registri diversi.

---

## 8-ter. ⭐ L'anno **dentro** il numero

### Perché, in una riga

Se la numerazione riparte ogni anno **e** il numero non porta l'anno, allora il
1° gennaio la stessa identica stringa torna su un documento diverso. `ORD0000001`
del 2026 e `ORD0000001` del 2027 sarebbero due ordini diversi con lo stesso
numero scritto sopra.

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
* ⭐ **La commessa lo fa con lo stesso meccanismo degli altri**:
  `CMM-<sigla>-<anno>-<9 cifre>`, dove l'anno lo mette il registro
  (`anno_nel_numero`) e non un pezzo di codice suo — la commessa è standard, con
  gli stessi parametri degli altri documenti.

### ⚠️ Una cosa da sapere prima di chiederla su un registro vecchio

L'anno nel numero è **forma del numero**, come il prefisso: su un sezionale che
ha già consegnato dei numeri **non si può aggiungere**. Il motivo è lo stesso del
§6.6 — il contatore non riparte quando cambia la forma, prosegue, e sullo stesso
registro convivrebbero due forme con numeri consecutivi, senza modo di
distinguerle.

⇒ La scelta si fa **alla nascita** del registro. Su un sezionale già in uso
l'alternativa è l'altra: se la sua numerazione non riparte (politica `NESSUNA`),
il numero non si ripete e l'anno non serve.

## 9. Il presidio: nessuna funzione di vendite legge il catalogo dei formati

Prefisso, suffisso e cifre dei cinque documenti stanno **sul registro** (§3). Una
funzione che li cercasse ancora nel catalogo dei formati non troverebbe la riga e
cadrebbe sul valore di ripiego — **sette cifre** — senza nessun errore:

| | quante cifre vuole | quante ne otterrebbe |
| --- | --- | --- |
| DDT, ordine, reso | 7 | 7 — **giusto per caso** |
| Commessa | 9 | **7** |

⛔ Nessun vincolo violato: solo una commessa con un codice più corto —
`CMM-ACME-2026-0000007` invece di `CMM-ACME-2026-000000007`. E la forma è proprio
ciò che, secondo il §6.6, tiene separati i codici nuovi da quelli vecchi. ⚠️ Un
valore di ripiego che coincide col valore giusto nasconde il difetto: tre
famiglie su quattro passerebbero.

⭐ Il presidio non guarda un documento: guarda il **codice**, e pretende che
nessuna funzione dell'area vendite legga il catalogo dei formati. Copre da solo
anche il generatore che qualcuno scrivesse domani.

---

## 10. Dove guardare

* [`config.sistema_codici`](/dbzero/config/manual/sistema_codici) — il catalogo dei
  formati, con la checklist del trasloco
* [`vendite.registri_fatturazione`](/dbzero/vendite/manual/registri_fatturazione) —
  i registri di numerazione, con prefisso, suffisso e lunghezza
* [`vendite.famiglie_documento`](/dbzero/vendite/manual/famiglie_documento) — quali
  documenti si numerano su un registro, dove vivono e **con quale forma nascono**;
  il CRUD: [api_famiglie_documento](/backend/vendite/manual/api_famiglie_documento)
* [`vendite.fn_assegna_numero_documento`](/dbzero/vendite/manual/fn_assegna_numero_documento) —
  i sei passi, in una sede sola
* [`vendite.fn_componi_numero_documento`](/dbzero/vendite/manual/fn_componi_numero_documento) —
  la composizione della stringa, pura e verificabile in una riga
* [`vendite.fn_get_next_progressivo`](/dbzero/vendite/manual/fn_get_next_progressivo) —
  il contatore: la politica di azzeramento e il seme del secchio nuovo

**I cantieri che hanno prodotto queste regole**, per chi cerca il *perché* con
tutte le misure e le strade scartate:

* [brief-db-registri-numerazione-chiave-del-contatore](../dev/work-done/brief-db-registri-numerazione-chiave-del-contatore.md)
  — gli assi dichiarati (§8-bis), il passaggio di politica e l'anno dentro il
  numero (§8-ter)
* [brief-db-prefisso-sul-registro-e-allineamento-contatori](../dev/work-done/brief-db-prefisso-sul-registro-e-allineamento-contatori.md)
  — la forma del numero sul registro
* [brief-be-fe-crud-registri-di-numerazione](../dev/work-done/brief-be-fe-crud-registri-di-numerazione.md)
  — la maschera e le regole di modifica

---
{% include-markdown "signature-core.md" %}
