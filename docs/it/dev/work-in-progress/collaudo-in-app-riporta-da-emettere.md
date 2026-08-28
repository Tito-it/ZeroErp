# Collaudo in-app · «Riporta da emettere» e la card che si spezza in due

> **Cos'è.** Il copione della validazione a video: si tiene aperto accanto
> all'applicazione e si spunta. Non è il brief — il *perché* di ogni scelta sta
> in [brief-be-fe-lavoro-che-non-torna-indietro.md](brief-be-fe-lavoro-che-non-torna-indietro.md);
> qui c'è solo **cosa fare, cosa deve succedere, e cosa fare se non succede**.
>
> **Perché esiste.** È l'**unica voce che tiene aperto il cantiere**. Il codice è
> scritto, i presidi sono verdi (4136 test), la catena è stata riprovata sul
> database vero — ma di questo verbo è stato provato il **percorso**, mai
> l'**esito**: ⛔ **nessuna attività è stata davvero riportata da una persona.**
>
> ⭐ **E le 5 righe vere sono il banco di prova.** Sono lì da un errore di
> numerazione di luglio: una fattura eliminata le ha lasciate orfane, timbrate e
> lucchettate, e nessun giro le riprenderà da solo. Il team DB le ha attraversate
> in `BEGIN … ROLLBACK` e le ha **rimesse a posto** apposta: il recupero vero è
> il primo gesto del frontend.
> ⛔ **Se il verbo non le prende, non ha fallito la bonifica — ha fallito il
> perimetro**, ed è un difetto di modello da segnalare subito.
>
> **Stato**: da eseguire. **Ambiente**: sviluppo (`dbdev`).
> **Pagina**: `vendite/dashboard-competenza`, anno **2026**, mese **luglio**.

---

## ⛔ Quattro cose da sapere prima di cominciare

**1 · L'esemplare è UNO SOLO, e si consuma.** Le 5 righe residue sono le sole
esistenti: `1123`, `1130`, `1131`, `1132`, `1133` — luglio 2026, **5.019 €**.
Una volta riportate **spariscono dalla lista dei residui**, e non si ricreano a
mano. Quindi:

> ⭐ **Recupera UNA riga sola nella prova 6**, non tutte e cinque. Le altre
> quattro servono alle prove che vengono dopo.

**2 · ⭐ L'ordine delle prove è parte del metodo, non una comodità.** Le prove
**1 → 5** non toccano niente: si guarda, si spunta, si chiude. Dalla **6** in
poi si scrive. Farle in quest'ordine significa che, se il perimetro non torna,
lo scopri **prima** di aver consumato l'unico esemplare — e non dopo.

**3 · ⚠️ Il verbo NON è distruttivo, e questo cambia come si legge un errore.**
Riportare non cancella niente: se il riporto fosse sbagliato si rifattura e si è
al punto di prima. Quindi un rifiuto qui non è mai «hai rotto qualcosa» — è il
perimetro che parla, e va letto, non aggirato.

**4 · Ricarica la pagina, e sappi che il backend è stato riavviato.** Il
frontend gira su vite con ricarica automatica; il backend di sviluppo **no** —
è stato ricaricato (`kill -HUP`) il 2026-08-27 alle 11:0x, dopo l'ultima
modifica Python. Se durante il collaudo qualcuno tocca codice Python, serve di
nuovo: senza, stai collaudando la versione di prima.

---

## La materia

* la pagina è **`vendite/dashboard-competenza`**, Lente 1, anno **2026**;
* il mese con la materia è **luglio 2026**, card **«Emesse non fatturate»**;
* il permesso del verbo è **`riporta_da_emettere`** (`config.azioni_processo`
  id 33, attivo). ⛔ Non è quello che genera le fatture né quello che le
  cancella: chi può *recuperare* non deve per forza poter *cancellare*;
* ⚠️ **per la prova 7 serve una lista PAGINATA**, che i residui non sono (5
  righe stanno in una pagina sola). Si usa una fra: **«Da emettere»** (gruppi
  fatturabili), la **coda resi**, il **drawer di gestione commessa**. Se nessuna
  ha abbastanza righe, la prova si dichiara `SENZA_MATERIA` invece di essere
  spuntata a caso.

---

## Prove che NON scrivono niente

### 1 · La card dice DUE cose

1. apri la Lente 1 sull'anno **2026**;
2. guarda la card **«Emesse non fatturate»** di **luglio**.

**Cosa deve succedere**: sotto il totale una riga dice
**«di cui 5 da recuperare»** con il valore **5.019,00 €**. Il totale della card
resta il totale — la riga non lo sostituisce, lo **spezza**.

⭐ **Perché conta**: dentro quella casella convivono **quattro** situazioni con
rimedi opposti. Solo il *residuo* chiede un'azione; le altre tre chiedono di
aspettare. Un numero solo per rimedi opposti era il difetto di partenza.

**Se non succede**: se la riga non c'è ma la card ha un numero, il conteggio
`n_residui` non sta arrivando dal backend — guarda la risposta di
`dashboard-competenza/` nella console.

### 2 · Il mese senza residui **tace**, non sparisce

1. sposta il mese su uno **senza** residui (agosto, o un mese vuoto).

**Cosa deve succedere**: la card dice **«nessuno da recuperare»**.

⛔ **Non deve sparire la riga**: «non c'è niente da recuperare» e «non lo
sappiamo» sono due cose diverse, e a video devono restare diverse.

### 3 · Il tooltip non racconta più la storia vecchia

1. passa il mouse sull'icona ℹ️ accanto alla riga dei residui.

**Cosa deve succedere**: il testo distingue i **residui** (si recuperano) dal
**lavoro in transito** (avanza da sé).

⛔ **Non deve dire** *«qui restano solo attività sospese, posticipate o rimaste
indietro; non avanzano da sole»*: è la frase vecchia, ed era diventata **falsa**
per tre situazioni su quattro.

### 4 · La lista è quella dei residui, e si può guardare

1. clicca la card **«Emesse non fatturate»**.

**Cosa deve succedere**: si apre l'elenco dei **residui** — non la lista delle
commesse. **5 righe**, con: commessa, cliente, **articolo** (codice *e*
descrizione), competenza, data, valore, **lotto di provenienza**, motivo
= «Residuo».

⭐ Il **lotto di provenienza** è cliccabile e apre il lotto: risponde a «da dove
viene questo residuo», che prima non si vedeva da nessuna parte. ⚠️ Non è
`lotto_id` — quello nasce dalla catena della fattura, e su un residuo la fattura
non c'è.

**Se non succede**: se compaiono le **commesse**, lo smistamento del drill-down
non riconosce lo stadio — è il ramo `STADIO_RESIDUI` in `loadDrillDown`.

### 5 · 🔴 Le tre prove che fallirebbero **in silenzio**

Sono le più importanti di tutta la sezione: nessuna di queste dà un errore
rosso se è rotta. Danno un risultato **plausibile e sbagliato**.

|        | Cosa premere                                                   | Cosa deve succedere                                                                                                                                                                                                                                                    |
| ------ | -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **5a** | **Esporta** (CSV o XLSX)                                       | il file contiene i **RESIDUI**: 5 righe, le colonne della lista. ⛔ *Era il difetto: scaricava le **commesse**. Un file che non corrisponde a ciò che si ha davanti è peggio di nessun file — chi lo apre crede di avere quel perimetro e non ha modo di accorgersene*  |
| **5b** | **Personalizza colonne**                                       | si apre la configurazione della lista **residui**. ⚠️ *Puntava alla lista commesse, che su questa card non è nemmeno montata*                                                                                                                                           |
| **5c** | ogni **intestazione** di colonna, in **entrambe** le direzioni | l'elenco si riordina, sempre 5 righe, **nessun errore**. ⚠️ *Un valore non ammesso in una clausola SQL non fallisce educatamente: è un **500**. Occhio a **Articolo** e **Lotto di provenienza**, gli unici due dove il nome della colonna e il campo fisico divergono* |

⚠️ Dopo l'export, **apri davvero il file**. Contare le righe dal browser non
prova niente: il difetto stava proprio nel contenuto.

### 6 · Senza permesso, la porta non si vede nemmeno

1. entra con un utente **senza** l'azione `riporta_da_emettere` (o togliti
   l'override, se sei super-admin il gate non si applica);
2. apri la stessa card.

**Cosa deve succedere**: **niente caselle di selezione** e **niente pulsante**.

⛔ Non «pulsante spento»: proprio assente. Una casella che porta a un 403 è un
vicolo cieco che si imbocca prima di vederlo.

---

## Prove che SCRIVONO

### 7 · ⭐ Il gesto — **una riga sola**

> ⛔ Spunta **UNA** riga. Le altre quattro servono dopo.

1. spunta una riga dell'elenco;
2. il pulsante deve dire **«Riporta da emettere (1)»**;
3. premi → leggi il dialog di conferma (dice **quante** righe) → **accetta**.

**Cosa deve succedere**:

* toast **verde**: «Riportate **1** attività (**N** righe di commessa tornate da
  emettere)»;
* la lista dei residui si ricarica e scende a **4**;
* la card scende a **«di cui 4 da recuperare»**;
* ⭐ la card **«Da emettere» SALE**: il lavoro è tornato in coda.

⚠️ **I due numeri del toast possono differire, e non è un difetto**: la seconda
scrittura tocca solo le righe di commessa che erano davvero su `EMESSA`.

**🔴 E qui sta il collaudo del PERIMETRO**: se ne spunti N e il verbo ne riporta
**meno di N**, non ha fallito la bonifica — **ha fallito il perimetro**. Fermati
e segnalalo: è un difetto di modello, non un intoppo.

**Se non succede**: se il toast è **giallo** con «Nessuna attività riportata»,
l'elenco a schermo era invecchiato (vedi prova 9). Se è un errore rosso, leggi
il codice: `E_ATTIVITA_ANCORA_IN_FATTURA` deve offrire **«Apri Fattura …»**.


FINO QUI TUTTO OK 

### 8 · Il recupero è VERO, non cosmetico

1. dopo la prova 7, vai sulla card **«Da emettere»** dello stesso mese;
2. trova il lavoro appena recuperato e **fattura**lo col giro normale.

**Cosa deve succedere**: si fattura come qualunque altro lavoro. Nessun lotto è
stato rigenerato, nessuna fattura ricreata: il lavoro ha semplicemente ripreso
il giro.

⭐ **È l'unica prova che dimostra che il recupero significa qualcosa.** Riportare
una riga che poi non si riesce a fatturare avrebbe spostato il problema, non
risolto.
OK GIUSTO
### 9 · L'elenco invecchiato si riconosce da sé

1. apri il cruscotto in **due schede** del browser, sulla stessa card;
2. nella **prima**, riporta una riga (consuma un esemplare);
3. nella **seconda**, che non lo sa, spunta **quella stessa riga** e premi.

**Cosa deve succedere**: **non** un errore secco, ma un avviso
**«N attività non si possono riportare adesso (…)»** con il **motivo**, la
selezione azzerata e l'elenco **ricaricato**.

⭐ **Perché esiste questo passo**: la mutazione è **atomica**. Senza il
ricontrollo, il rifiuto arriverebbe come **un** errore per l'intero elenco e non
sapresti **quale** riga l'ha fermato né perché — e riproveresti.

### 10 · **ANNULLARE** un documento ritira il lavoro *(§7.7 della guida)*

⛔ **«Chiudere» era la parola sbagliata** — questa prova diceva «chiudi il
documento», e non era eseguibile perché non diceva *quale gesto*. Misurato sul
database il 2026-08-28: il trigger si sveglia **solo** sul passaggio a uno stato
con `is_abortito`, e in tutti e quattro i vocabolari — preventivi, ordini, DDT,
contratti — quello stato è **uno solo: `ANNULLATO`**.
⚠️ **Evadere o completare un documento NON ritira niente.** Il gesto da fare è
**Annulla**.

#### 10.1 · Il documento si annulla, e **si porta via** il lavoro non emesso

⚠️ **Questa prova brucia un documento**: `ANNULLATO` non si disfa, e riaprirlo
non riporta indietro le righe (§7.7). Scegli un preventivo che sei disposto a
perdere.

**Materia misurata il 2026-08-28** — preventivi in stato **`ACCETTATO`** (da cui
l'annullamento è ammesso) con **1 riga di commessa `NON_EMESSA`** da ritirare:

> `PRV0000099` · `PRV0000133`  CMM-20260610194705159-31740c · `PRV0000135` · `PRV0000136` · e altri

1. apri il preventivo (`vendite/preventivi`) e prendi nota della **commessa** che
   ha alimentato;
2. **annullalo**;
3. apri quella commessa e guarda la riga che veniva da lì.

**Cosa deve succedere**: la riga di commessa è passata ad **`ANNULLATA`**, da
sola, e nel **registro della commessa** c'è la traccia col motivo — *«Ritiro
automatico alla chiusura del documento di origine (PREVENTIVO …)»*.

⭐ **Perché conta**: prima, annullare un preventivo fermava i passaggi futuri ma
lasciava fatturabile ciò che era già passato in commessa — e quel lavoro prima o
poi finiva in una fattura che nessuno si aspettava più.

**Se non succede**: se la riga resta `NON_EMESSA`, il trigger `_z90_` non è
scattato. Verifica che il preventivo sia davvero passato ad `ANNULLATO` e non a
un altro stato.

#### 10.2 · Con righe **già emesse** il documento **non si annulla affatto**

🔴 **Un solo esemplare in tutto il database**, misurato il 2026-08-28:

> **`DDT0010839`** — stato `CONSEGNATO`, **1 riga di commessa `EMESSA`**

⛔ **Non ce ne sono altri**, e non è un dettaglio: tutti gli altri documenti con
righe emesse sono in stato `EVASO`, **da cui l'annullamento non è ammesso** — il
rifiuto arriverebbe dal guard delle *transizioni*, che è un altro trigger e dice
un'altra cosa. Provare lì non proverebbe niente.

1. apri `DDT0010839` e prova ad **annullarlo**.

**Cosa deve succedere**: **rifiuta**, e il messaggio nomina la via d'uscita —
si recuperano prima le righe con **«Riporta da emettere»** dalla Lente 1, e
**dopo** il documento si annulla portandosele via.

⚠️ **Il messaggio deve parlare di righe già emesse**, non di transizione non
ammessa: sono due rifiuti di due trigger diversi (`a10_guard_chiusura_sorgente`
contro `a10_guard_transizione`). Se leggi il secondo, la prova è **nulla** — non
hai esercitato il guard che volevi.

⭐ Le due superfici devono dire **la stessa cosa**: il messaggio del database e
la §7.7 della guida. Se divergono, è la guida ad avere torto.

---

## Prova su un'altra lista

### 11 · Il seleziona-tutto è **di pagina** *(la correzione del 2026-08-27)*

⚠️ **Non si prova sui residui**: 5 righe stanno in una pagina sola. Serve una
lista paginata — **«Da emettere»** (gruppi), la **coda resi**, o il **drawer di
gestione commessa**.

1. metti **10 righe per pagina**, su una lista che ne ha almeno 15;
2. a **pagina 1** spunta **2 righe**; guarda il contatore del pulsante: **2**;
3. vai a **pagina 2**;
4. premi il **seleziona-tutto nell'intestazione**.

**Cosa deve succedere**: il pulsante conta **2 + le righe di pagina 2**.

🔴 **Prima del 2026-08-27 le 2 di pagina 1 SPARIVANO**, e te ne accorgevi solo
dal contatore che calava. Il difetto colpiva **tre** liste paginate su cinque.

5. ri-premi il seleziona-tutto: deve togliere **solo** la pagina corrente e
   lasciare le **2** di pagina 1.

**Cosa deve succedere anche**: arrivando a pagina 2 con **niente spuntato lì**,
la casella dell'intestazione **non** deve essere in stato *indeterminato* —
prima si accendeva a sproposito.

**Se non succede**: la lista sta ancora usando `toggleAll` invece di
`toggleAllInPagina` (vedi §13.6 del brief).

---

## Verbale

**Chiuso il**: ______ · **Da**: ______ · **Ambiente**: ______

| #    | Prova                                            | Scrive | Esito | Note                          |
| ---- | ------------------------------------------------ | ------ | ----- | ----------------------------- |
| 1    | La card dice DUE cose                            | no     | ⬜     |                               |
| 2    | Mese senza residui: «nessuno da recuperare»      | no     | ⬜     |                               |
| 3    | Il tooltip non racconta la storia vecchia        | no     | ⬜     |                               |
| 4    | La lista è quella dei residui                    | no     | ⬜     |                               |
| 5a   | 🔴 **Esporta** scarica i RESIDUI                  | no     | ⬜     |                               |
| 5b   | 🔴 **Personalizza colonne** apre la lista giusta  | no     | ⬜     |                               |
| 5c   | 🔴 **Le 10 colonne ordinabili**, in due direzioni | no     | ⬜     |                               |
| 6    | Senza permesso la porta non si vede              | no     | ⬜     |                               |
| 7    | ⭐ **Il gesto — una riga sola** (perimetro)       | **sì** | ⬜     |                               |
| 8    | Il recupero è vero: si rifattura                 | **sì** | ⬜     |                               |
| 9    | L'elenco invecchiato si riconosce da sé          | **sì** | ⬜     |                               |
| 10.1 | **Annullare** un documento ritira il non emesso  | **sì** | ⬜     | brucia il documento           |
| 10.2 | Con righe emesse l'annullamento è **rifiutato**  | no     | ⬜     | unico esemplare: `DDT0010839` |
| 11   | Seleziona-tutto **di pagina** (altra lista)      | no     | ⬜     |                               |

### Che cosa ha trovato il collaudo

> Da riempire strada facendo. Vale più delle spunte: un elenco vuoto accanto a
> undici verdi si legge come «non abbiamo guardato», non come «era tutto a
> posto».

| #       | Cosa                                                                                                                                                                                                                                        | Dove è finito                                                  |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| **R-1** | Alla prova 7 il residuo **sembra già fatturato**: il lotto di provenienza porta a una fattura **numerata e definitiva**. Non lo è — quel documento è di un **altro cliente** dello stesso lotto. Difetto di **leggibilità**, non di modello | ✅ chiarito qui sotto; note in `cruscotti-fatturazione.md` §3.1 |
|         |                                                                                                                                                                                                                                             |                                                                |

#### R-1 · «ma quella fattura ha già un numero» — cosa è emerso davvero

⚠️ **Il dubbio è nato a video ed è legittimo**, e nessun test l'avrebbe trovato:
è un problema di *nomi*, e i nomi si leggono solo guardando la schermata.

Misurato sul database il 2026-08-28. Il lotto **`LTF-0000679`** (COMPLETATO ·
CHIUSO) conteneva **15 attività di DUE clienti**:

| Cliente    | Attività                  | Fattura                                              |
| ---------- | ------------------------- | ---------------------------------------------------- |
| **BA 169** | 10                        | ✅ **2026/R2/11** · DEFINITIVA · 31/07 · **10 righe** |
| **BA 173** | 5 — `1123`, `1130`–`1133` | 🔴 **nessuna**                                        |

⭐ **Un lotto produce una fattura per CLIENTE.** Quella del BA 169 esiste ed è
numerata; quella del BA 173 no. Aprendo il *lotto di provenienza* da un residuo
si arriva quindi a un documento **numerato che non è il suo** — è esattamente
l'inciampo.

⛔ **E «emessa» è sovraccarico**: `stato_emissione = EMESSA` sta sull'**attività
di commessa** e significa *«presa da un lotto, entrata nella pipeline»*, **non**
*«esiste un documento fiscale»*. Sono due «emesse» diverse che si chiamano
uguale. La domanda dell'operatore lo ha dimostrato meglio di qualunque revisione
a tavolino.

**Il riporto della prova 7, verificato riga per riga:**

|                        |                                                                                                                             |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `af 1123`              | `fattura_riga_id=NULL` · `lock=False` · `stato_esecuzione=NULL` · `lock_batch_id=NULL` · **`stato_emissione=NON_EMESSA`** ✅ |
| Fattura **2026/R2/11** | ancora **10 righe**, DEFINITIVA — **non toccata** ✅                                                                         |
| Registro               | `RIGA_RIPORTATA_DA_EMETTERE`, 28/08 08:04, utente `tid`, col `lock_batch_id` precedente ✅                                   |

⛔ **Nessun doppione.** `1123` è un **ONERE da 5.000 €** sulla commessa
`CMM-20260710145604304-c6a64e`; l'altra attività di quella commessa (`886`,
240 €) sta nella fattura **632**, un documento diverso. L'onere non è in nessuna
fattura, né prima né dopo il riporto.

ℹ️ E il verbo non poteva sbagliare nemmeno volendo: il perimetro a DB è
`fattura_riga_id IS NULL`, quindi una riga agganciata a una fattura viva viene
**rifiutata** con `E_ATTIVITA_ANCORA_IN_FATTURA` — che a video offre
«Apri Fattura …».

➡️ **Conseguenza**: nessuna modifica al codice. Due note in guida (§3.1), perché
chi arriva dopo inciampi una volta in meno.

---

## Quando questo verbale è chiuso

Il cantiere **«il lavoro che non torna indietro» si chiude**, e il brief
BE/FE passa in `work-done` insieme ai due brief DB già archiviati.

Restano fuori, e **non** lo tengono aperto:

* **E-3** — il codice errore «rientrato» nella baseline (§9 del brief): è di chi
  possiede quel codice. ⚠️ Finché la baseline non si stringe quel presidio è un
  cancello **mezzo spento**;
* **§11.6** — le due convenzioni di `ordinamento_default` in `ui`: di chi
  possiede quello schema;
* la **§7.1 della guida**, contesa con
  [brief-be-fe-rendi-definitive-sui-lotti.md](../work-done/brief-be-fe-rendi-definitive-sui-lotti.md):
  da **coordinare**, non da fare in parallelo.

⚠️ **Un difetto trovato qui non riapre il brief da sé**: va guardato dove
appartiene. Uno che riguardi il perimetro del verbo, la card o la lista è di
questo cantiere; uno che riguardi la numerazione, la coda o il perimetro
emittente ha altre sedi, e forzarlo dentro questo documento lo trasformerebbe
nel contenitore di tutto ciò che tocca una fattura.
