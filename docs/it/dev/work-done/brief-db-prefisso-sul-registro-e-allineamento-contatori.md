# Brief DB — il prefisso passa sul registro, e i contatori si allineano

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine:** Tid, 2026-08-31. Ha creato un ordine e ha visto `ORD0000001`, e ha
> pensato che `ORD` fosse fisso da qualche parte. Lo è — ed è corretto che lo sia.
> ⛔ **Ma la cosa che ha visto è il sintomo di un'altra**, e sono due lavori
> distinti che questo brief tiene separati apposta.
>
> 🎉 **Stato al 2026-08-31 — CHIUSO lato DB.** Quattordici passi
> (`20260831-39` → `-54`), applicati, presidi **verdi**
> (`vendite/test-numero-prefisso-registro-v1.sql`, plan 6).
>
> ⭐ **La forma del numero ha ora UNA sede sola**: `famiglie_documento` tiene i
> **default** (del tipo documento), `registri_fatturazione` l'**effettivo** (del
> sezionale). ⛔ Le quattro righe dei documenti traslocati sono uscite da
> `config.sistema_codici`, dove avevano un prefisso che nessuno leggeva più in
> una tabella editabile dal pannello.

---

## 1. Due cose diverse, e confonderle costa

| | Che cos'è | Natura |
| --- | --- | --- |
| **A** | Il contatore di ordini, DDT e resi è **ripartito da 1** sotto una forma rimasta identica al pregresso | ⛔ **riparazione** |
| **B** | Prefisso e suffisso passano sul **registro**, uno per sezionale | ⭐ **miglioramento** |

⚠️ **B non ripara A.** Se il prefisso resta `ORD`, la forma resta identica e il
problema resta — solo mascherato meglio. E chi un domani guardasse le sole cifre
lo ritroverebbe uguale.

### 1.1 ⛔ Il difetto A, per intero

Il brief del trasloco aveva scritto la premessa che rende sicuro ripartire da 1:

> *«Non collidono con i vecchi perché **la forma è diversa** — ed è l'unica cosa
> che li separa.»*

✅ Per la **commessa** è vera: `CMM-<sigla>-<anno>-<9 cifre>` non somiglia a
`CMM-<timestamp>-<md5>`. Confermato da Tid il 2026-08-31, la commessa è salva.
✅ Per i **preventivi** non si pone: non sono sui registri, usano una sequenza di
database che non riparte mai. Verificato — `PRV0000202`, la vecchia numerazione
prosegue.

⛔ **Per ordini, DDT e resi è FALSA**: la forma è `PREFISSO` + 7 cifre, prima e
dopo il trasloco. Nessuno l'ha verificata documento per documento — **me
compreso**: la premessa è stata scritta una volta e applicata a tutti e quattro.

⚠️ **E il vincolo non se ne accorge, per costruzione.**
`uq_ordini_v_anno_serie_numero` è su `(registro_id, anno, serie, numero)`, e le
righe pregresse hanno **registro `NULL`**. Una riga con registro `NULL` e una con
registro valorizzato **non collidono mai**: due ordini con lo stesso numero
convivono, e non c'è niente da respingere.

📌 **I duplicati eventualmente già presenti: non si tocca nulla.** Decisione di
Tid (2026-08-31), se ne parla dopo. Questo brief impedisce che se ne creino di
nuovi.

---

## 2. Le decisioni prese

| # | Decisione | Chi |
| --- | --- | --- |
| **D-1** | I contatori si allineano al **massimo già emesso**, per registro e anno | Tid |
| **D-2** | `prefisso` e `suffisso` (4 caratteri) stanno su **`vendite.registri_fatturazione`** — *non* sui progressivi | Tid, dopo l'obiezione del §2.1 |
| **D-3** | Sono **univoci per emittente**, sulla **coppia** | Tid |
| **D-4** | ⛔ **Nessun ripiego su `config.sistema_codici`**: il generatore legge **solo** il registro | Tid |
| **D-5** | Seed iniziale: il prefisso di oggi (`ORD`, `DDT`, `RESO`) | Tid |

### 2.1 ⛔ Perché NON sui progressivi — l'obiezione che ha cambiato la sede

La proposta iniziale era `registri_fatturazione_progressivi`. ⛔ Non regge, e la
ragione è meccanica: **la riga di progressivi la crea il generatore stesso**,
quando serve.

```sql
INSERT INTO vendite.registri_fatturazione_progressivi
       (registro_id, anno, mese, serie, last_numero, attivo)
VALUES (p_registro_id, v_anno, v_mese, v_serie, 0, true)
```

⇒ Una riga **nuova per ogni anno e ogni serie**, che nasce con `last_numero = 0`
**e nient'altro**. Con il prefisso lì, ogni **1° gennaio** ne nascerebbe una vuota
e i documenti di quell'anno uscirebbero **senza prefisso**, in silenzio.

⭐ Il registro è la sede giusta: è configurazione, dura nel tempo, e il generatore
la sta già leggendo. **Il contatore conta; la forma la decide il registro.**

### 2.2 ⭐ Perché l'unicità è sulla COPPIA, e a cosa serve davvero

⚠️ **Non serve all'integrità.** Il contatore è per `(registro, anno, serie)` e la
stringa `ORD0000001` non porta né l'anno né il registro — stanno in colonne
separate, ed è lì che l'unicità li guarda. La stringa **si ripete già ogni anno**,
legittimamente.

⇒ Serve alla **leggibilità**: se due registri dello stesso emittente avessero lo
stesso prefisso, due numeri identici provenienti da **contatori diversi** si
presenterebbero uguali a chi legge. Il prefisso è il **nome del sezionale**, e due
sezionali dello stesso emittente non possono chiamarsi uguale.

⚠️ Sulla **coppia** e non su ciascuno separatamente: pretendere il prefisso unico
da solo vieterebbe `ORD…A` / `ORD…B`, che sono già distinguibili.

### 2.3 ⛔ Cosa discende da D-4, ed è la parte che si dimentica

*«Non mescoliamo le cose: chi si ricorderebbe che il prefisso è su un'altra
tabella?»* — la decisione è giusta, e ha tre conseguenze obbligate.

1. **`config.sistema_codici` perde il prefisso per DDT, ordini e resi.** Quelle
   righe restano per `lunghezza_numero`. ⚠️ Il prefisso resta lì per tutti gli
   altri (preventivi, contratti, anagrafiche…), che sui registri non ci sono: **le
   due sedi convivono, divise per motore**, e questo va scritto o si ricrea la
   confusione che D-4 vuole togliere;
2. ⛔ **Ogni via che crea un registro deve dare il prefisso.**
   `vendite.fn_provision_registri_emittente` oggi **non lo valorizza** —
   verificato — quindi un emittente nuovo nascerebbe con registri muti e numeri
   senza prefisso, in silenzio. Va aggiornata **nello stesso giro**;
3. **Prefisso vuoto resta legittimo** e significa «nessun prefisso»: è ciò che
   Tid ha chiesto (*«se non sono vuoti fare il concat»*). ⚠️ Quindi non si può
   presidiare con un `NOT NULL` — il presidio è che chi **crea** un registro dia
   un default sensato, cioè il punto 2.

---

## 3. I passi

| # | Cosa | Dove |
| --- | --- | --- |
| **P-1** | ⛔ **Allineamento dei contatori** al massimo già emesso | `00_schema/vendite/20260831-39` |
| **P-2** | `prefisso` + `suffisso` (**8**) su `registri_fatturazione`, seed e `UNIQUE` sulla coppia — un changeSet solo | `00_schema/vendite/20260831-40` |
| **P-3** | ⭐ **`fn_componi_numero_documento`** (pura) + **`fn_assegna_numero_documento`** (i sei passi) | `20_code/vendite/20260831-41` |
| **P-4** | DDT, ordini e resi **chiamano** la funzione centrale | `…/20260831-42`, `-43`, `-45` |
| **P-5** | Anche la **commessa** la chiama, col `corpo` | `…/20260831-46` |
| **P-6** | `fn_provision_registri_emittente` valorizza il prefisso | `…/20260831-44` |
| **P-8** | ⛔ Il prefisso include il **separatore** — dato (`-47`) e funzione (`-48`) | `00_schema` + `20_code` |
| **P-9** | `lunghezza_numero` sul registro + seed | `00_schema/…/20260831-49` |
| **P-10** | Le funzioni leggono **tutta** la forma dal registro | `20_code/…/-50` |
| **P-11** | ⭐ `prefisso_default` e `lunghezza_default` su **`famiglie_documento`** | `00_schema/…/-51` |
| **P-12** | Il provisioning legge i default **dalle famiglie** | `20_code/…/-52` |
| **P-13** | ⛔ Escono le quattro righe da `config.sistema_codici` (+ CSV) | `80_data/…/-53` |
| **P-14** | Backfill dei registri rimasti senza forma | `00_schema/…/-54` |
| **P-15** | ⛔ **La lunghezza si legge DAVVERO dal registro** — il difetto del P-10 | `20_code/vendite/20260831-55` |
| **P-16** | I quattro generatori smettono di nominare il catalogo | `20_code/vendite/20260831-56` |

### ⭐⭐ La sede unica, e come ci si è arrivati

⛔ **Il nodo**: togliere le righe avrebbe lasciato `fn_provision_registri_emittente`
**senza fonte** — ogni emittente nuovo con prefisso `NULL` e la commessa a 7 cifre
invece di 9. ⚠️ E non si sarebbe visto in un test: i registri di oggi sono già
configurati, il difetto vive solo nella **nascita** di quelli futuri.

⭐ La sede giusta c'era già. `famiglie_documento` **è** il tipo documento:

```
famiglie_documento     →  il DEFAULT   (del tipo documento)
registri_fatturazione  →  l'EFFETTIVO  (del sezionale)
```

⭐ E scioglie il contro dichiarato al P-9: la lunghezza *è* del tipo documento, e
sul registro resta un **override** — che è la ragione per cui un sezionale può
volerla diversa.

### ⛔ P-14 — un errore di processo, non dei dati

La `preCondition` del `-53` ha **fermato il migrate**: due registri `COMMESSA` con
prefisso `NULL`.

⇒ La causa: il seed del `-40` filtrava su tre famiglie, e il filtro è stato esteso
a `COMMESSA` **dopo** che quel changeSet era già stato applicato. ⛔ Con
`runOnChange: false`, **modificare un changeSet applicato non ha alcun effetto**:
il file che si legge oggi dice una cosa, quello che ha girato ne diceva un'altra.

⭐ Due cose imparate, oltre alla riparazione:

* **il backfill non nomina la commessa** — è scritto come regola generale, così
  vale anche per il prossimo registro che nascesse monco per un'altra ragione, e
  legge dalla **stessa** fonte del provisioning: backfill e nascita non possono
  divergere;
* ⭐ **le tre `preCondition` hanno preso un `onFailMessage`**. `Expected '0' got
  '2'` è costato tre giri per capire *quale* controllo fosse: ora ciascuna dice
  cosa non regge, cosa comporta e quale changeSet lo ripara — lo stesso standard
  che pretendiamo dai codici errore di dominio.

### ⭐⭐ La centralizzazione — decisione di Tid, 2026-08-31

*«Abbiamo tutte funzioni diverse? Non possiamo centralizzare?»*

⛔ **Misurato: sì, ed era duplicazione piena.** DDT, ordini, resi e commessa
facevano gli **stessi sei passi**, ognuno per conto proprio — risolvere il
registro, ricavare l'anno, chiedere il progressivo, leggere la lunghezza, leggere
il prefisso, comporre. ⚠️ Una correzione alla composizione andava fatta in
**quattro posti**, e chi ne dimenticava uno produceva un difetto **muto**: un
documento formattato diverso dagli altri, che nessun vincolo respinge.

**Due livelli, entrambi con un precedente in casa:**

* `fn_componi_numero_documento(prefisso, corpo, progressivo, lunghezza, suffisso)`
  — **pura**, `IMMUTABLE`, scritta **sui valori e non sugli id**: si prova in una
  riga di SQL senza costruire un documento;
* `fn_assegna_numero_documento(...)` → `(registro_id, anno, progressivo, numero, serie)`
  — le letture, una volta sola.

⚠️ **Cosa NON è centralizzato, ed è deliberato: il MOMENTO.** DDT a `EMESSO`,
resi a `CONFERMATO`, ordini e commessa alla creazione. È l'unica cosa che
distingue davvero i quattro, e metterla in comune avrebbe messo in una funzione
condivisa la sola cosa che condivisa non è.

⭐ **La serie risolta esce dalla funzione**, e non è un dettaglio: è la stessa che
entra nella chiave del contatore, e risolverla due volte con due `COALESCE`
diversi è precisamente il modo in cui il contatore e la `UNIQUE` cominciano a
guardare sezionali diversi.

⭐ **Il `corpo` non è generalizzazione prematura.** Serve alla sola commessa, il
che di solito è un cattivo segno — ma la ragione l'ha data Tid chiedendo il
**suffisso anche sulla commessa**: con prefisso e suffisso condivisi da tutti e
quattro, la forma è la **stessa** e cambia solo cosa sta in mezzo. Il parametro
non generalizza un caso: **nomina la parte che varia**.

### ⚠️ Il separatore non è più un campo a sé

Se serve, si scrive **dentro il prefisso** (`CMM-`). ⭐ Toglie il caso speciale
che la commessa aveva e gli altri no: un prefisso vuoto le lasciava un
**separatore orfano** in testa — `-ACME-2026-000000001`, che spezzato dava un
primo pezzo vuoto.

⚠️ Ne discende che **quattro caratteri erano stretti**: `RESO-` sono cinque. Le
colonne sono `varchar(8)`.

⚠️ Sulla commessa il separatore **fra i pezzi del corpo** resta, ed è del
dominio: `<sigla>-<anno>-`.

### ⛔⛔ P-15 — il difetto che il P-10 diceva di aver risolto

*(misurato il 2026-08-31, sera, rileggendo la documentazione)*

Il changeSet `20260831-50` si intitola **«il formato viene TUTTO dal registro»** e
dichiara *«una lettura sola al posto di due»*. ⚠️ Ha cambiato l'**ancoraggio
`%TYPE`** della variabile e ha lasciato la **query** dov'era:

```sql
SELECT sc.lunghezza_numero INTO v_len
  FROM config.sistema_codici sc
 WHERE sc.codice_interno = lower(p_famiglia_documento);
```

Poi il `-53` ha cancellato proprio quelle quattro righe. ⇒ Zero righe, `v_len`
resta vuota, e il ripiego della composizione dà **7 cifre a tutti**:

| | cifre volute | cifre ottenute |
| --- | --- | --- |
| DDT, ordine, reso | 7 | 7 — **giusto per caso** |
| **Commessa** | **9** | **7** |

```
CMM-ACME-2026-0000007      ← quello che usciva
CMM-ACME-2026-000000007    ← quello che deve uscire
```

⛔ Nessun errore, nessun vincolo violato. E tocca **proprio la forma**, che è
l'unica cosa che separa i codici nuovi dal pregresso (§5, «i numeri già assegnati
non si rifanno»).

#### ⛔ La causa, e non è nei dati

Le tre `preCondition` del `-53` verificavano che la **sede nuova** fosse popolata —
registri con prefisso e lunghezza, famiglie coi default — e **nessuna chiedeva chi
leggesse ancora quella vecchia**. Era l'inventario giusto della metà sbagliata.

⭐ **La regola che ne esce, e vale ben oltre questo cantiere:** prima di cancellare
una fonte si fa il **censimento dei suoi lettori** — `pg_proc.prosrc` e i file
pgTAP — non solo l'inventario del sostituto.

#### ⚠️ Le tre cose che hanno tenuto il difetto nascosto

1. **il ripiego coincideva col valore giusto** per tre famiglie su quattro: solo la
   commessa, con le sue 9 cifre, era diversa;
2. **il presidio provava la funzione pura passandole `9` a mano**, quindi non
   chiedeva mai *da dove* venga il 9. È il ramo verificato da un percorso che non
   lo attraversa;
3. ⚠️ **quattro `COMMENT` dicevano che era già a posto.** Un commento superato non
   è rumore: è una **prova falsa a favore dell'ipotesi sbagliata**, ed è la ragione
   del P-16.

#### ⚠️ E i tre pgTAP erano ROSSI, non verdi

Tre asserzioni costruivano l'attesa leggendo `config.sistema_codici`: tolte le
righe, il join non trovava niente e l'asserzione diventava **indefinita**. Il file
falliva 3 test su 10.

⛔ **Erano stati dichiarati verdi da una corsa fatta PRIMA del `-53`.** La regola
è la stessa di sempre, applicata ai test: *la suite si rimisura dopo l'ultimo
changeSet*, non dopo il penultimo.

⭐ Le tre attese ora si costruiscono dal **registro che ha numerato quel
documento**, che è la fonte vera — e sul caso commessa l'asserzione è diventata
quella che ha inchiodato il difetto.

---

## 4. I presidi — scritti e verdi il 2026-08-31

#### `db/pgtap/vendite/test-numero-prefisso-registro-v1.sql`, plan 6

| # | Cosa | |
| --- | --- | --- |
| 1 | ⭐⭐ La **composizione**, su una tabella di sei casi | senza fixture |
| 2 | Due registri dello stesso emittente con la stessa coppia: respinti | `23505` |
| 3 | ⭐ ...ma due **senza** prefisso né suffisso convivono | il gemello |
| 4 | Nessun contatore è sotto il massimo già emesso | la riparazione |
| 5 | ⭐ ...e ci sono contatori da controllare | anti-muto |
| 6 | Un emittente **nuovo** nasce coi registri già prefissati | il buco di P-6 |

⭐⭐ **Il test 1 è il guadagno della centralizzazione, e si misura.** Prima la
composizione stava in quattro trigger e per provarla bisognava **fabbricare un
documento** — DDT, riga, indirizzo, causale, transizione di stato. Ora è una
funzione pura: **sei casi in una tabella di `VALUES`**. Il costo di provare un
caso in più è passato da venti righe di fixture a **una riga**.

#### `db/pgtap/vendite/test-documenti-numerazione-trasloco-v1.sql`, plan 11 *(era 10)*

| # | Cosa | |
| --- | --- | --- |
| 3 | La forma del numero DDT è quella del **registro** che l'ha numerato | riscritto |
| 5 | ⭐⭐ Il codice commessa ha la forma del registro — **nove cifre** | riscritto, ed è quello che ha trovato il P-15 |
| 9 | La forma del numero reso è quella del **registro** | riscritto |
| 10 | ⛔ **Nessuna funzione di `vendite` LEGGE più il catalogo dei formati** | nuovo |

⭐ **Il test 10 è il presidio di CLASSE**, ed è l'unico degli undici che non guarda
un documento: guarda il **codice**. Deriva da `pg_proc`, quindi copre da sola anche
il generatore che qualcuno scrivesse domani.

⚠️ **Cerca la LETTURA (`FROM config.sistema_codici`), non la parola** — e la prima
stesura sbagliava proprio qui. Vietare la parola sembrava più severo, ma è una
regola che nessuno può rispettare: le correzioni del P-15 e del P-16 **devono**
poter dire da dove veniva prima la lunghezza, o si perde l'unica spiegazione del
perché la commessa aveva sette cifre. ⇒ Un presidio che vieta di raccontare la
storia si paga in chiarezza, e viene aggirato scrivendo commenti più vaghi.

### ⛔ P-8 — il difetto trovato scrivendo il test, non girando

Il seed del `-40` copiava `sistema_codici.prefisso` sul registro, ma il
**separatore** stava in una colonna a parte. Invisibile su DDT, ordini e resi —
il loro separatore è **vuoto**. Rompeva la commessa:

```
CMMACME-2026-000000007      invece di      CMM-ACME-2026-000000007
```

⇒ Il codice smetteva di essere **decomponibile**, cioè proprio la proprietà per
cui la sigla dell'emittente ha un vincolo di forma che vieta il trattino.

⭐ **La causa è la decisione, che resta corretta** — il separatore si scrive
dentro il prefisso — ma il seed ne aveva copiata **solo metà**.

⚠️ **La lezione generale**: spostando un dato composito da una sede a un'altra, si
sposta *tutto ciò che lo compone*, non il solo campo omonimo. E il difetto è
invisibile **esattamente dove il pezzo mancante è vuoto** — che è il caso più
comune, quindi lo trova solo chi copre anche quello raro.

## 5. Cosa NON entra

* ⛔ **La bonifica dei duplicati già esistenti** — decisione di Tid: se ne parla
  dopo, qui non si tocca nulla;
* ⛔ **I preventivi, i contratti, le offerte**: non sono sui registri e non
  cambiano;
* ⛔ **La fattura**: il suo numero è il progressivo **nudo**, senza formato — non
  ha mai avuto un prefisso, e non ha una riga in `config.sistema_codici`.

⚠️ *(Superata la riga che diceva «la commessa non entra: il prefisso `CMM` viene
dalla composizione di dominio e lì non ha posto».)*

### ⭐ La commessa È entrata — decisione di Tid, 2026-08-31

*«Estraiamo anche il prefisso commessa e lo mettiamo nella tabella registri, così
diventa parametrizzabile anche quello.»* Non c'era ragione di lasciare indietro
l'unica delle cinque famiglie che compone il proprio codice a mano.

⛔ **Ma ha un dettaglio che le altre tre non hanno, ed è il passo P-7.** Su DDT,
ordini e resi il prefisso è l'**ultimo** pezzo prima delle cifre: «nessun
prefisso» produce il numero nudo e finisce lì. Sulla commessa è il **primo di
quattro**, e un prefisso vuoto lascerebbe un **separatore orfano** in testa:

```
-ACME-2026-000000001
```

⇒ Comincia con un trattino, non si legge, e chi lo spezzasse sul separatore
troverebbe un primo pezzo **vuoto**. ⭐ Il separatore accompagna il prefisso:
senza prefisso sparisce con lui.

⚠️ **E qui la decomponibilità conta più che altrove**: il codice commessa è
l'unico dei cinque la cui **identità è la stringa nuda** — `uq_commesse_codice`
guarda quella, non una quadrupla di colonne. È la stessa ragione per cui la sigla
dell'emittente ha un vincolo di forma che vieta il trattino.

---

## 6. La revisione documentale del 2026-08-31 (sera)

Richiesta di Tid: *«aggiorna la guida della numerazione con queste ultime novità,
inoltre ricerca incongruenze nei documenti dopo quest'ultimo aggiornamento ai
numeratori»*. È da questa rilettura che è uscito il **P-15**: la ricerca di
incongruenze nei documenti ha trovato un difetto nel **codice**.

### 6.1 Che cosa è stato corretto

| Documento | Cosa diceva di falso |
| --- | --- |
| `guide/numerazione-documenti-e-codici.md` | il formato dei quattro documenti veniva dal catalogo dei formati; la commessa aveva un «prefisso fisso» |
| `dbzero/config/manual/sistema_codici.md` | ⛔ *«questa tabella non ha perso niente nel trasloco»*; e la checklist si fermava al passo 5, *«la riga resta»* |
| `guide/automazione-db.md` §8 | portava «numero fattura» come esempio del framework che **non** la genera |
| `dbzero/vendite/manual/trgfn_ddt_gen_numero_emesso.md` | formato da `sistema_codici` + sequenza `ddt_numero_seq` |
| `dbzero/vendite/manual/trgfn_resi_gen_numero.md` | idem, con `resi_numero_seq` |
| `dbzero/vendite/manual/trgfn_ordini_gen_codice.md` | ⛔ **descriveva un oggetto che non esiste più** — file rimosso |
| 5 documenti che linkavano `trgfn_ordini_gen_codice` | nome morto dal trasloco della mattina |

### 6.2 Che cosa è stato aggiunto

* `registri_fatturazione` — la revisione su prefisso, suffisso, lunghezza, la
  divisione default/effettivo e l'allineamento dei contatori;
* `famiglie_documento` — le due colonne di default, con la ragione per cui
  esistono;
* `fn_provision_registri_emittente` — i registri nascono già formattati;
* **schede nuove**: `fn_assegna_numero_documento`, `fn_componi_numero_documento`,
  `trgfn_ordini_gen_numero`.

### 6.3 ⚠️ Residui dichiarati, non corretti

1. **Quattro sequenze orfane** — `vendite.ddt_numero_seq` (a 25 786),
   `ordini_numero_seq` (40 689), `resi_numero_seq` (13 055) e `fatture_numero_seq`.
   Verificato il 2026-08-31: **nessuna funzione le nomina, nessuna colonna le usa
   come default, nessuna è di proprietà di una colonna.** Il contatore vero è
   `vendite.registri_fatturazione_progressivi`.
   ⚠️ È una trappola *quieta*: chi le trova con quei valori alti può concluderne
   che siano ancora il contatore. ⛔ Non si cancellano di slancio — la fattura ha
   lasciato la sua nel febbraio 2026 e nessuno l'ha tolta — ma **la rimozione va
   decisa**, non dimenticata.
2. **`vendite.fn_push_preventivo_a_ordine`** porta nel corpo un commento che cita
   `trgfn_ordini_gen_codice`, funzione che non esiste più (changeSet `20260824-02`,
   applicato). Non produce nulla di sbagliato: manda a cercare un nome morto.
   Costa una riscrittura di quella funzione, e non la vale da sola — si fa alla
   prossima occasione in cui la si tocca.
3. **`docs/it/dbzero/vendite/index.ci.md`** elenca ancora il file rimosso: è
   auto-generato scansionando `manual/`, quindi si allinea alla prossima
   generazione. ⛔ Non si edita a mano.
