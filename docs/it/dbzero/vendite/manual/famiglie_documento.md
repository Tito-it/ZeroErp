## 📘 Documentazione Concettuale – Tabella `vendite.famiglie_documento`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)
> • [config.sistema_codici](/dbzero/config/tabelle/sistema_codici)
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_registro_documento](/dbzero/vendite/manual/fn_get_registro_documento)
> • [anagrafiche.fn_ba_ha_storia_emittente](/dbzero/anagrafiche/manual/fn_ba_ha_storia_emittente)

---
### 🎯 Scopo Principale
(latest review 31-08-2026)

È l'**elenco dei tipi di documento che prendono il numero da un registro**:
fattura, documento di trasporto, ordine, commessa, reso.

Per ognuno dice **dove vive**: in quale tabella stanno i suoi documenti, come si
chiama la colonna che ne porta il numero, e come si chiama quella che porta il
cliente.

---

### Perché non è un semplice elenco di parole

Sarebbe stato più veloce scrivere quei cinque nomi dentro il campo del registro e
finirla lì. Non basta, e la ragione non è «un domani potrebbero servirne altri».

La ragione è che **un'altra regola deve leggerli**. Un cliente non si sposta da un
emittente a un altro quando ha già un documento numerato: quel numero viene dal
registro di quell'emittente e nessuno lo rifà. Per rispondere «questo cliente ha
già dei documenti numerati?» bisogna guardare in cinque tabelle diverse.

Se quell'elenco di cinque tabelle fosse **ricopiato** dentro la regola, il giorno
in cui un sesto documento entrasse nei registri qualcuno dovrebbe ricordarsi di
aggiungerlo. Chi se ne dimentica non rompe niente: la regola continua a
funzionare, semplicemente **smette di guardare** dove dovrebbe. È il difetto
peggiore, perché non si vede.

⭐ Leggendo l'elenco da qui, il sesto documento entra nella regola **il giorno in
cui si registra la sua famiglia**. Non c'è nessuna copia da tenere allineata,
perché non c'è nessuna copia.

---

### ~~Le due colonne~~ **Le tre colonne** che sembrano ripetute e non lo sono

*(la terza è arrivata il 2026-09-01)*

* **la colonna del numero** non si chiama allo stesso modo dappertutto: è
  *numero* per fattura, documento di trasporto, ordine e reso, ma è *codice* per
  la commessa. È esattamente il genere di dettaglio che non si può indovinare;
* **la colonna del cliente** è obbligatoria su fattura e commessa, mentre su
  documento di trasporto, ordine e reso può mancare. Chi legge deve saperlo, e
  non ha modo di dedurlo;
* ⭐ **la colonna della serie** — `colonna_serie` — che su fattura, documento di
  trasporto e ordine si chiama *serie*, e su reso e commessa **non esiste
  affatto**. Il vuoto qui non è un dato mancante: è la dichiarazione che quella
  famiglia **una serie non ce l'ha**.

#### ⛔ Perché la terza è la più importante delle tre

Le prime due servono a *leggere* il documento. La terza serve a **non
rompere il contatore**.

La serie entra nella chiave del contatore, quindi cambiare la serie di un
registro apre un contenitore nuovo che riparte da 1. Su fattura, documento di
trasporto e ordine è innocuo — la serie è scritta sul documento **e** dentro il
suo vincolo di unicità, quindi i numeri restano distinguibili: è il modo
legittimo di aprire una serie nuova. ⛔ Su reso e commessa no: la serie non la
registrano da nessuna parte, quindi il numero 1 va a sbattere contro uno già
emesso e **il documento non si numera più**.

⇒ Da qui la regola generale, scritta per esteso nella
[guida alla numerazione §8-bis](/guide/numerazione-documenti-e-codici):

> **Tutto ciò che discrimina il contatore deve poter discriminare anche il
> documento.**

⭐ **Ed è il NOME e non un sì/no**, per la stessa ragione delle altre due: un
interruttore «gestisce la serie» acceso su una famiglia la cui tabella non ha la
colonna riporterebbe il difetto senza che nessuno se ne accorga. Col nome, il
controllo automatico verifica che la colonna **esista davvero** e che stia nel
vincolo di unicità del numero.

⚠️ **E un registro di una famiglia senza serie non può averne una**: si rifiuta,
non si ignora. Un campo che si può cambiare e non fa niente è il difetto che il
trasloco del prefisso ha appena finito di togliere.

---

### Cosa qui non c'è, ed è una decisione

Non esiste una casella «questa famiglia blocca lo spostamento del cliente, questa
no». La regola è **categorica**: se un tipo di documento prende il numero da un
registro, quel numero appartiene a un emittente, punto. Una casella che nessuno
avrebbe mai messo a «no» sarebbe una promessa che il resto del programma non
mantiene.

---

### Una famiglia ritirata resta scritta

Si può spegnere una famiglia senza cancellarla, ed è il modo giusto di ritirarla:
la riga resta come traccia del fatto che quel documento è esistito. Una famiglia
spenta può anche nominare una tabella che non c'è più — è storia, non
configurazione — mentre una famiglia accesa **deve** nominare cose che esistono
davvero, e c'è un controllo apposta che se ne accerta.

---

### 🔄 rev 2026-08-31 (sera) — qui vive anche la **forma con cui un registro nasce**

Due colonne nuove, `prefisso_default` e `lunghezza_default`, dicono con che
aspetto nasce un registro di questa famiglia:

| famiglia | prefisso | cifre |
| --- | --- | --- |
| DDT | `DDT` | 7 |
| ORDINE | `ORD` | 7 |
| RESO | `RESO` | 7 |
| COMMESSA | `CMM-` | **9** |
| FATTURA | *nessuno* | 7 |

⭐ **Sono DEFAULT, non il valore effettivo.** Quello vive su
`vendite.registri_fatturazione`, e un sezionale può averlo diverso: è a questo che
serve un sezionale. La divisione è netta — **qui il tipo documento, lì il
sezionale**.

#### ⛔ Perché queste colonne esistono, ed è una storia che vale la pena leggere

Il piano prevedeva di togliere da `config.sistema_codici` le quattro righe dei
documenti traslocati. ⚠️ Ma la funzione che crea i registri di un emittente nuovo
derivava **proprio da lì** prefisso e lunghezza.

⇒ Togliendo le righe, ogni emittente **nuovo** sarebbe nato con registri senza
prefisso e con 7 cifre — la commessa quindi sbagliata, in silenzio. E non si
sarebbe visto quel giorno: si sarebbe visto **al primo emittente creato dopo il
rilascio**, cioè quando nessuno guarda.

⭐ La sede giusta c'era già: questo è il catalogo che dice **cos'è** ogni famiglia,
e prefisso e lunghezza sono proprietà del tipo di documento. Non è stata una
colonna aggiunta per far quadrare un passo: è il posto dove quel dato apparteneva.

⚠️ **Nessun `NOT NULL` sul prefisso:** vuoto è legittimo e significa «nessun
prefisso», come sul registro. La lunghezza invece è `NOT NULL` con default 7, così
non c'è mai un valore assente da interpretare — ed è esattamente l'assenza da
interpretare che ha prodotto il difetto corretto dal changeSet `20260831-55`.

---

### Impatto e Vantaggi

* una sola sede dice quali documenti si numerano sui registri, e tutti la
  leggono;
* aggiungere un tipo di documento è **una riga**, non una caccia ai posti da
  aggiornare;
* il messaggio che spiega perché un cliente non si può spostare usa le parole di
  questa tabella, quindi resta corretto da sé;
* i registri di un emittente nuovo nascono con la forma giusta senza che nessuno
  debba ricordarsene, e **il backfill dei registri monchi legge dalla stessa
  fonte** — così nascita e riparazione non possono divergere.

---

### 🔄 rev 2026-09-01 — questa tabella si può **modificare da dentro il programma**

Fino a oggi in `famiglie_documento` scriveva solo un seed. Da oggi ci scrive una
persona, dall'amministrazione, e tre cose che reggevano **perché nessuno poteva
toccarla** sono diventate presidi veri.

#### 1. Non si spegne una famiglia che è ancora la regola di qualcuno

Spegnere una famiglia **non nasconde una voce di catalogo: spegne un
controllo**. Le due funzioni che rispondono *«questo cliente ha già documenti
numerati?»* scorrono le famiglie **attive**: una famiglia spenta esce dal giro, e
da quel momento i suoi documenti smettono di trattenere il cliente presso
l'emittente che li ha numerati. Nessun errore, nessuna riga di diario — il
controllo guarda semplicemente in un posto in meno.

⇒ Una famiglia si spegne **solo** quando non ha più registri accesi né documenti
numerati. I due motivi hanno un ordine, e non è estetico: prima quello a cui si
può rimediare (spegnere i registri), poi quello a cui non si può — i numeri
usciti non si disfano.

#### 2. Dove vive il documento non si cambia sotto un registro

Le colonne che dicono dove abita il documento — la tabella, la colonna del
numero, quella del cliente, quella della serie — non descrivono la famiglia: **la
fanno funzionare**. Una volta che esiste anche un solo registro, non si toccano
più.

⛔ Il caso peggiore è togliere la colonna della serie a una famiglia che ce
l'aveva: da quel momento i suoi registri hanno una serie che il documento non sa
più distinguere, il contatore continua a contare, e **nessun vincolo se ne
accorge**.

⚠️ Il *codice interno* non è in questo elenco, ed è voluto: quello lo protegge il
blocco automatico che vale per tutte le tabelle di catalogo, e due divieti sulla
stessa colonna con due messaggi diversi confondono e basta.

#### 3. La serie dichiarata deve davvero **distinguere** il documento

Il controllo che verifica i nomi ora guarda anche la colonna della serie, e non
si limita a chiedere se esiste: pretende che **stia nel vincolo di unicità
insieme al numero**. È la regola generale della numerazione — *tutto ciò che
distingue il contatore deve poter distinguere anche il documento* — e finora era
scritta in questa pagina senza che nessuno la eseguisse.

⭐ Sono due difetti diversi e hanno due messaggi diversi: **un nome sbagliato** è
un refuso, **un nome giusto che non basta** è il caso insidioso, perché la
colonna c'è e si legge.

---

### ⭐ Una famiglia nuova nasce **con i suoi registri**

Creare la riga e darle i registri sono due cose, e sono **una cosa sola**: se la
seconda non riesce, non resta una famiglia a metà. Una famiglia senza registri
non fallisce — promette un documento che non si numererà mai, e nessun vincolo lo
dice.

Il programma dà alla famiglia nuova un registro **su ogni emittente**, con il
prefisso e le cifre che la famiglia stessa dichiara. È la stessa cosa che già
succedeva al contrario — un emittente nuovo si prende i registri di tutte le
famiglie — e ora le due strade usano **la stessa regola**, non due copie: il
codice del registro, la sua descrizione e la forma del numero si decidono in un
posto solo.

⚠️ Una famiglia creata **spenta** non prende nessun registro, e non è un errore:
è il caso «si prepara prima, si accende dopo».

⚠️ E una famiglia che nasce **quando non c'è ancora nessun emittente** prende
zero registri: il programma lo dice, perché quel documento non nascerebbe
comunque.

---

### 📋 Cosa vede chi apre l'elenco

L'elenco delle famiglie non mostra solo le colonne: mostra anche **quanti
registri** ha ciascuna e quanti sono accesi, e per ogni riga se si può spegnere e
se se ne può cambiare la struttura — **col motivo**, quando la risposta è no.
Sono le stesse due domande a cui rispondono i divieti qui sopra: chieste prima di
provare, invece che scoperte sbattendoci contro.

⛔ **Cosa il programma non fa, ed è una decisione**: non cancella. Una famiglia
ritirata resta scritta, perché la sua riga è la traccia di documenti che
esistono ancora — ed è lo stesso motivo per cui non si spegne finché quei
documenti ci sono. Le due regole sono la stessa regola, detta due volte.

⚠️ **Una famiglia creata da qui nasce «non fiscale»**: niente limite di
emissione, data del documento sempre di oggi. È un limite del modello, non della
maschera — il registro della fattura si risolve per tipo e natura, per una strada
tutta sua — e va detto nel form, non scoperto da un rifiuto.

---

### ⭐ Una tabella, una famiglia

*(decisione del 2026-09-01)*

Due famiglie **attive** non possono dire di abitare nella stessa tabella. La
famiglia non è un modo di chiamare i documenti: **è il tipo di documento**, e il
tipo di documento è la tabella in cui vive. Un «DDT di reso» non è una famiglia
nuova — fa parte dell'insieme dei DDT.

⛔ **Cosa impedisce davvero.** Il controllo che risponde *«questo cliente ha già
documenti numerati?»* scorre le famiglie e per ognuna conta le righe della sua
tabella. Con due famiglie sulla stessa tabella conterebbe **gli stessi documenti
due volte**, e li elencherebbe sotto due nomi diversi: il blocco reggerebbe —
basta che ce ne sia uno — ma la frase che una persona legge direbbe il falso.

⚠️ **Una famiglia ritirata invece libera la sua tabella**, e serve che sia così:
la riga di una famiglia spenta resta scritta per sempre, quindi un divieto senza
eccezioni le lascerebbe quella tabella occupata **per sempre**, e nessun
successore potrebbe più nascere. Una famiglia spenta, del resto, nessun controllo
la guarda: non è nel conteggio, quindi non è nel problema.

⚠️ Sui **registri** vale il contrario — uno spento continua a occupare il suo
posto — e non è una contraddizione: lì il posto è la chiave del contatore, e un
sezionale spento possiede ancora i numeri che ha consegnato. Qui è solo
un'identità di catalogo, che vale finché la famiglia è accesa.

---

### 🔄 rev 2026-09-02 — la famiglia dice se ammette le **regole fiscali**

Una colonna nuova, `ammette_regole_fiscali`, risponde a una domanda che finora
era scritta a mano **fuori** dal database, in due posti: *questa famiglia
ammette il limite di emissione e una data del documento diversa da oggi?*

Fino a ieri la risposta era il nome «FATTURA», ricopiato nel programma e nella
maschera. Adesso è un dato del catalogo, e chi lo legge non deve più sapere a
memoria quale famiglia sia speciale.

⛔ **Ma non è una casella libera, e la ragione è la parte importante.** La regola
vera vive su un vincolo del registro, che continua a nominare la fattura. Se
questa colonna si potesse accendere su una famiglia qualsiasi, la maschera
offrirebbe tre campi che il database poi **rifiuta al salvataggio** — una
promessa rotta addosso a chi sta compilando. Un vincolo la lega allo stesso
nome: **il posto in cui si decide che cosa è fiscale resta uno**, e questa
colonna lo dichiara invece di duplicarlo.

⚠️ **Non è un doppione di «presidia la data».** Quella dice se la famiglia ha un
pavimento sulla *sequenza* delle date; questa dice quali *campi* il registro
ammette. Oggi hanno la stessa risposta su tutte e cinque le famiglie — e restano
due domande: unirle vorrebbe dire che il giorno in cui una cambia si scopre che
comandava anche l'altra.

⭐ Una famiglia creata dal programma nasce **non fiscale**, ed è il limite già
dichiarato: il registro della fattura si sceglie per tipo documento e natura, per
una strada tutta sua.

### 🔄 rev 2026-09-14 — una famiglia può **non avere** un billing account

`colonna_billing_account` diventa facoltativa (`20260914-07`): il vuoto è la
dichiarazione che **quella famiglia di documenti non ha un cliente** — la
controparte di un ordine d'acquisto è un fornitore, un ruolo di soggetto, non
un billing account. È la stessa forma di `colonna_serie`, due righe sopra.

Chi legge quella colonna lo sa:

* il controllo dei riferimenti (`trgfn_famiglie_documento_guard_riferimenti`)
  verifica che la colonna esista **solo se è dichiarata**; tabella e colonna
  del numero restano obbligatorie;
* le due funzioni della storia dell'emittente
  ([fn_ba_ha_storia_emittente](/dbzero/anagrafiche/funzioni/fn_ba_ha_storia_emittente),
  [fn_get_storia_emittente_ba](/dbzero/anagrafiche/funzioni/fn_get_storia_emittente_ba))
  **saltano** le famiglie senza billing account già quando scelgono su quali
  famiglie girare — una famiglia senza cliente non può contribuire alla storia
  di nessun cliente;
* la funzione che crea una famiglia (`fn_crea_famiglia_documento`) non la
  pretende più e trasforma il campo vuoto in «nessuno».

⚠️ Il controllo di struttura **non cambia**: su una famiglia che ha già dei
registri, passare da «nessuno» a un nome di colonna è un cambio come gli altri,
e viene rifiutato.

ℹ️ Le cinque famiglie in servizio hanno tutte il billing account: questa
revisione **apre la porta** al primo documento che non ce l'ha, non lo
registra. Sarà il cantiere acquisti a farlo. Brief:
`brief-db-modifiche-certe-ciclo-vendita-e-articolo`, sezione 3-bis.
