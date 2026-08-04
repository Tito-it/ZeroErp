# Guida – Presidi e registri del debito

> **Cos'è.** Come ZeroErp si accorge da solo che qualcosa si è rotto in silenzio,
> e come tiene il conto di ciò che è rotto e non è ancora stato sistemato.
>
> Riguarda due controlli che oggi esistono — i **riferimenti morti** nelle funzioni
> del database e la **baseline dei test rossi** — e la forma che hanno in comune.
> Il §4 spiega perché uno gira da solo e l'altro va lanciato a mano, che è la
> domanda che si fanno tutti.

---

## 1. Il problema: un promemoria non è un presidio

Il 2026-03-31, durante una campagna di pulizia, due funzioni del database furono
riconosciute **morte** — nominavano una tabella cancellata mesi prima — e lasciate
dov'erano. Non per distrazione: fu scritto nero su bianco, in un changeSet che
esiste solo per dirlo.

> «Dipende da `vendite.attivita_fatturabili_lotti` (tabella rimossa).
> **Da verificare se la funzione va rimossa dal DB.**»

Quella verifica non è mai stata fatta. Cinque mesi dopo, una delle due ha fatto
fallire un aggiornamento del database, ed è così che ci siamo tornati sopra.

**La lezione, che vale ben oltre il caso**: una segnalazione lasciata in un
commento non presidia niente. È un promemoria, e i promemoria non si rileggono.
Perché una cosa sia davvero presidiata serve qualcosa che **protesti da solo**,
al momento giusto, senza che nessuno debba ricordarsene.

Da qui i due controlli descritti sotto. Non sono due strumenti a caso: hanno la
stessa forma, e conviene conoscerla prima dei dettagli.

---

## 2. La forma comune: la misura e il registro

Ogni presidio è fatto di **due pezzi**, e nessuno dei due funziona senza l'altro.

**La misura** dice qual è la situazione adesso. Deve essere ripetibile e non
opinabile: la si lancia oggi e domani e, se nulla è cambiato, dà la stessa
risposta.

**Il registro del debito** dice quali problemi sappiamo già di avere e perché
sono ancora lì. Serve perché la realtà non è mai a zero: c'è sempre qualcosa di
rotto che si è deciso consapevolmente di non sistemare oggi.

⚠️ **Il registro è un debito, non un elenco di eccezioni.** La differenza è tutta
qui, ed è la ragione per cui questi controlli restano utili invece di diventare
rumore di fondo:

* un **elenco di eccezioni** può solo allungarsi. Ogni volta che qualcosa dà
  fastidio, lo si aggiunge. Dopo un anno nessuno lo legge più, e i problemi veri
  ci si nascondono dentro;
* un **registro del debito** deve **calare**. Ha una data, e ogni voce spiega
  perché è ancora aperta e cosa la chiuderebbe.

Per tenerlo onesto servono due regole, e stanno in due posti diversi apposta:

| Regola | Dove vive | Perché lì |
|---|---|---|
| Senza un motivo scritto, la voce non si aggiunge | vincolo del database | non è un controllo che si può dimenticare di lanciare: è il database che rifiuta la riga |
| Una voce che non serve più va tolta | test | per saperlo bisogna ri-misurare, e una misura non può essere un vincolo |

Senza la seconda regola il registro può solo crescere, e torna a essere un elenco
di eccezioni — cioè il changeSet del 2026-03-31 con cui è cominciata questa
storia.

---

## 3. I due presidi che esistono oggi

### 3.1 Riferimenti morti nelle funzioni del database

**Cosa sorveglia.** PostgreSQL non tiene traccia di cosa c'è scritto dentro una
funzione. Se si cancella una tabella o si rinomina una colonna, le funzioni che le
nominavano restano lì, apparentemente sane, e **non vengono più ricontrollate**.
Si scoprono rotte solo quando qualcuno le esegue — che può essere mesi dopo, o
nel momento peggiore.

Non è teoria: al primo giro, il 2026-08-04, ne sono uscite **34**. La più vecchia
era rotta da undici mesi, e una era la ricerca degli indirizzi usata dagli
operatori.

**Come funziona.** L'estensione `plpgsql_check` **compila davvero** il corpo di
ogni funzione, come farebbe la prima esecuzione: vede tabelle e colonne, e vede
anche i pezzi di codice che nessuno ha mai eseguito.

| Pezzo | Dove |
|---|---|
| La misura | `dbops.fn_check_funzioni_riferimenti_morti()` |
| Il registro | `dbops.riferimenti_morti_esenzioni` |
| Le due viste | `dbops.vw_riferimenti_morti_da_sanare` · `..._rientrati` |
| Strumento a mano | `scripts/sql/check_funzioni_riferimenti_morti.sql` |
| Cancello automatico | `scripts/sql/guardrail_riferimenti_morti.sql` (passo CI) |
| Test della suite | `db/pgtap/dbops/test-riferimenti-morti-v1.sql` |

**Quando diventa rosso** si hanno due strade, e nessuna delle due è ignorarlo:
ripararlo — quasi sempre è una riga — oppure registrarlo nel debito **con un
motivo scritto**.

Storia completa del primo giro — le 34 righe una per una, le cause radice e le
trappole pagate — nel brief di lavoro `docs/it/dev/work-done/brief-db-bonifica-riferimenti-morti.md`
(nel repository: i documenti di cantiere non fanno parte del sito pubblicato).

### 3.2 Baseline dei test rossi

**Cosa sorveglia.** Una parte della suite di test del database è rossa da tempo,
quasi sempre perché le fixture sono rimaste indietro rispetto a controlli entrati
dopo. In quella situazione un test rosso non dice più niente: è normale che ce ne
siano, quindi nessuno guarda.

La baseline separa i **rossi già noti** dai **rossi nuovi**. Solo i secondi sono
una notizia.

```bash
scripts/pgtap-baseline.sh vendite            # solo gli schemi toccati
scripts/pgtap-baseline.sh                    # tutta la suite (~7 min)
scripts/pgtap-baseline.sh --update vendite   # dopo aver sanato qualcosa
```

Il registro è `db/pgtap/baseline-rossi.tsv`, con la causa classificata. Lo script
segnala tre cose: le **regressioni** (rosso nuovo, esce con errore), i **rientrati**
(ora verdi, la riga va tolta) e il silenzio sui rossi già noti.

⚠️ **Una classificazione sbagliata nasconde un problema vero.** È successo: un test
era registrato come «errore di fixture» mentre in realtà la funzione che
collaudava non partiva proprio. È rimasto lì mesi, coperto da un'etichetta
rassicurante. Quando si aggiunge una riga alla baseline vale la pena spendere
cinque minuti a capire *perché* è rossa, invece di catalogarla per somiglianza.

⚠️ **Un file che fallisce nella fixture non esegue nessuna verifica.** La sua
copertura vale **zero**, non «parziale» — ed è peggio di un'area scoperta, perché
sembra coperta.

---

## 4. Perché uno gira da solo e l'altro no

Sì: il cancello automatico non va lanciato a mano. Ma i due controlli non sono la
stessa cosa messa in due posti diversi — sono **due controlli di natura diversa**,
e questo paragrafo spiega perché ognuno sta dove sta.

### Cosa dà davvero il controllo automatico

Il vantaggio del cancello in CI non è tanto che «gira da solo»: è che **non si può
dimenticare**. Blocca l'integrazione. Nessuno deve ricordarsi di lanciarlo, e
soprattutto nessuno può decidere di saltarlo perché ha fretta.

Va però saputo **quando** scatta: sui `push` verso il branch di integrazione e
sulle richieste di merge, e solo se sono stati toccati certi percorsi. Sul proprio
branch di lavoro **non parte**. Quindi non è un riscontro immediato: è una rete
che si trova al momento del merge. Il giro lanciato a mano resta il ciclo veloce,
quello che si usa mentre si lavora.

### Cosa può misurare la baseline, e dove

Qui sta la differenza di natura, ed è il punto meno ovvio di questa guida.

Il database della CI è **costruito da zero** a ogni giro: ha la struttura e i dati
di configurazione, ma **nessun dato di lavoro** — nessuna fattura, nessun ordine,
nessuna commessa. Molti test del database, invece, scelgono un caso reale fra i
dati esistenti e ci lavorano sopra: **69 file su 437** contengono un salto
condizionato proprio per questo.

Su un database vuoto quei test **non falliscono: si saltano**. E un test saltato
conta come verde.

⚠️ Un ipotetico giro in CI così com'è darebbe quindi una pipeline verde che ha
misurato molto meno di quanto sembra — cioè il difetto peggiore di tutti, perché
non fa rumore. La baseline vive a mano, sul server di sviluppo, **perché è lì che
può misurare quello che deve**: il comportamento su dati veri.

Il che non vuol dire che i due controlli debbano restare per sempre come sono, ma
che spostare l'uno dove sta l'altro non è una semplificazione: cambia cosa si
misura.

### Il corollario, che vale per tutto il progetto

Il database di sviluppo e un database ricostruito dai changelog **non sono lo
stesso oggetto**, pur partendo dagli stessi file. Verificare solo sul primo
significa verificare lo stato di **una macchina**; verificare sul secondo significa
verificare che le migrazioni sappiano ricostruirla. Sono due proprietà diverse, e
la seconda è quella che conta il giorno in cui si prepara un ambiente nuovo.

Non è un discorso astratto: la prima volta che il controllo sui riferimenti morti
ha girato in CI ha trovato due funzioni che sul server di sviluppo **non
esistevano**, perché i comandi che le cancellavano funzionavano solo su un
database cresciuto nel tempo.

**Servono entrambi**, e per motivi opposti.

---

## 4-bis. ⚠️ Il punto cieco peggiore: una regola che mente

C'è un modo di sbagliare che nessuno dei due presidi può intercettare da solo, ed
è successo davvero — vale la pena raccontarlo perché è il più difficile da vedere.

Il controllo sui riferimenti morti classifica ogni segnalazione, e alcune le
etichetta come **rumore**. Una di quelle etichette poggiava su un'affermazione
tecnica **sbagliata**: si era scritto che una certa forma di chiamata era lecita e
che era lo strumento a non capirla. Non era vero: lo strumento aveva ragione, e
sedici chiamate rotte sono state zittite per due giri di lavoro.

⚠️ **La regola sbagliata è stata perfino affinata due volte.** Ogni giro la
restringeva un po', trovava difetti veri, e con ciò **confermava** l'assunto di
partenza. Nessuno dei due ha chiesto se l'assunto fosse vero.

Da qui tre cose che valgono per qualunque presidio:

* **Un'etichetta rassicurante è più pericolosa di un errore.** Un errore lo si
  guarda; un'etichetta la si legge una volta e poi ci si fida. È lo stesso
  meccanismo per cui un test rosso registrato in baseline con la causa sbagliata è
  rimasto mesi a coprire una funzione che non partiva.
* **Chi scrive la regola non è la persona giusta per verificarla.** Quel difetto
  l'ha trovato un altro team, che aveva un motivo indipendente per guardare — non
  il presidio, e nemmeno chi l'aveva costruito.
* **Le esenzioni vanno scritte con la loro giustificazione tecnica**, non solo con
  il nome della categoria. Se accanto all'etichetta c'è la frase che la motiva,
  quella frase può essere letta e contestata. Se c'è solo l'etichetta, no.

Il presidio ha comunque fatto il suo mestiere: ha tenuto il conto, e quando la
regola è stata corretta i sedici difetti sono comparsi tutti insieme, con nome e
posizione. Quello che un presidio **non** può fare è accorgersi da solo che una
sua regola mente.

---

## 5. Se un cancello della CI diventa rosso

Prima di considerarlo un problema della CI, vale la pena tenere presente l'ordine
delle ipotesi:

1. **il difetto è reale** e la CI l'ha appena trovato — è il caso più frequente;
2. **il controllo misura un database incompleto**, perché è messo nel punto
   sbagliato della sequenza;
3. **il difetto esiste solo su un database costruito da zero** — vedi §4.

⚠️ La prima ipotesi che *non* va fatta è «la CI è rotta». Quando un controllo passa
in locale e fallisce in CI, di solito è il locale che sta nascondendo qualcosa.

Nota di sequenza, che è costata un giro rosso: in ZeroErp lo schema del database
**non ha un solo proprietario**. Liquibase costruisce quasi tutto, ma lo schema
`django` lo crea Django. Un controllo sulle definizioni del database deve girare
**dopo che entrambi hanno finito**, altrimenti misura un database a metà e segnala
problemi che non esistono.

---

## 6. Aggiungere un presidio nuovo

La ricetta, nell'ordine:

1. **Scrivi la misura prima del rimedio.** Serve a sapere quanto è grande il
   problema. Spesso la misura sposta le priorità: al primo giro sui riferimenti
   morti, il difetto più grave non era nemmeno nella lista iniziale.
2. **Classifica il rumore, non filtrarlo.** Un controllo che nasconde le righe che
   crede innocue non è più verificabile. Meglio farle uscire tutte con
   un'etichetta: se una è etichettata male, si vede. È successo — una regola
   troppo larga aveva catalogato come innocuo un difetto vero.
3. **Metti la misura in un posto solo.** Se la usano in due (il cancello e il
   test), devono leggere la stessa. Due copie prima o poi divergono, e da quel
   momento danno risposte diverse sullo stesso problema.
4. **Il registro nasce piccolo.** Se parte con trenta righe, nessuno lo leggerà.
   Meglio sanare prima e registrare solo ciò che è davvero una decisione presa.
5. **Fai fallire il controllo quando non può misurare.** Se manca un prerequisito,
   deve dirlo ad alta voce, non saltare in silenzio. Un cancello che passa perché
   non ha misurato niente è peggio di un cancello assente: dà la sensazione della
   copertura senza averla.
6. **Scrivi i limiti accanto al controllo.** Ogni misura ha punti ciechi. Se non
   sono scritti, il primo che legge un risultato verde crede che copra tutto.
7. **Motiva ogni esenzione con la sua ragione tecnica, non con la categoria.**
   Un'etichetta si legge e ci si fida; una frase che spiega *perché* quella riga è
   rumore può essere contestata da chi passa. Vedi §4-bis: è così che una regola
   fondata su un'affermazione falsa è sopravvissuta a due revisioni.

---

## 7. Limiti noti

Nessuno dei due controlli vede tutto, e conviene saperlo prima di fidarsi di un
risultato verde.

**Il controllo sui riferimenti morti non vede:**

* i riferimenti scritti in un **dato** invece che nel codice — una tabella nominata
  come testo dentro una tabella di configurazione. Per questo esiste una seconda
  misura sui dati di configurazione, ed è nata da un caso reale;
* i riferimenti che si risolvono verso la **cosa sbagliata**: una funzione che
  scrive il dato giusto nella colonna sbagliata compila benissimo. Il significato
  non si compila;
* i rami di codice che dipendono dai **parametri** con cui un controllo viene
  agganciato a una tabella, invece che dalla tabella stessa;
* più di un difetto per volta nello stesso punto: si ferma al primo. Per questo la
  bonifica va **ri-misurata dopo ogni passo**, non eseguita come una lista scritta
  una volta sola.

**La baseline non vede** ciò che i test non collaudano, e i test collaudano solo
ciò che i dati presenti permettono di collaudare.

**Entrambi non distinguono** un residuo da qualcosa lasciato lì di proposito.
Quella differenza sta nell'intenzione di chi l'ha scritto, e nessuna misura la
trova: è esattamente ciò per cui esiste il registro, con il suo motivo scritto.

---

## Riferimenti

* `docs/it/dev/work-done/brief-db-bonifica-riferimenti-morti.md` — la storia del primo giro (solo nel repository)
* [Automazione DB](automazione-db.md) — il framework che applica le regole strutturali
* `.codex/AGENTS.md` §Test — l'uso quotidiano della baseline
