# Brief DB — la chiave del contatore: gli assi si dichiarano, non si assumono

> **Destinatario:** team DB (`dev/db-tid`). Aperto il 2026-09-01, **chiuso il 2026-09-08**.
>
> **In una riga:** il contatore dei registri distingue i numeri su **quattro**
> assi — `(registro_id, anno, mese, serie)` — ma i documenti che quei numeri li
> ricevono ne portano al massimo tre, e nessuno controlla che li portino. Dove
> il contatore discrimina su un asse che il documento non sa esprimere, consegna
> un numero che il documento non è in grado di ospitare.
>
> **Origine.** Non da un difetto in campo: è emersa il 2026-09-01 scrivendo il
> guard sulla forma del numero ([brief CRUD registri](../work-done/brief-be-fe-crud-registri-di-numerazione.md)
> §8), chiedendosi *perché* `serie_default` potesse restare fuori dal divieto. La
> risposta — «perché la serie distingue i documenti» — vale per tre documenti su
> cinque. Poi le domande di Tid, che hanno spostato il cantiere due volte:
> *«allora tutti i documenti che si numerano sui registri devono avere la chiave
> completa?»* e *«non conviene dichiararlo nella famiglia?»*. Sì a entrambe, e
> la seconda ha cambiato la forma della cura.
>
> ⛔ **Nessuna misura decide niente qui.** I conteggi sono **fatti datati** e
> servono a un uso solo: dire se qualcosa *smentisce* il piano. A decidere è la
> struttura.
>
> ---
>
> ## ✅ CHIUSO il 2026-09-08 — decisione di Tid
>
> Il cantiere è **applicato e verde** su tutti e tre i lati, e non resta niente
> da scrivere: DB (22 changeSet `EXECUTED` + `20260908-10` e `..-11..16`, pgTAP
> del cantiere verdi), backend e frontend (le voci BE-R1 / FE-R1 / BE-L1 del
> §11.7, il §11.8 in maschera e la ragione corretta del §11.9).
>
> **Le due voci che restano NON sono lavoro, e sono dichiarate:**
>
> * ✅ **La firma senza `%TYPE`** su `script.fn_check_registro_forma_modificabile`
>   — **decisione di Tid, 2026-09-08: si lascia com'è, niente changeSet
>   correttivo.** ⭐ E la ragione regge da sé: `%TYPE` si risolve allo stesso
>   `bigint` e la firma non vive in `prosrc`, quindi un changeSet correttivo
>   sarebbe **un no-op sul database** — cambierebbe uno YAML già pushato senza
>   cambiare niente di ciò che gira. ⛔ Non è deprecato e non va deprecato: si
>   paga alla prossima revisione di quella funzione, se e quando ce ne sarà una.
> * 🔭 **L'unicità di `vendite.commesse` su una stringa sola** — **debito
>   dichiarato**, non un residuo di questo cantiere: `registro_id` e `anno` sono
>   colonne popolate su tutte le righe e il pgTAP le presidia (§4). Resta la
>   forma dell'unicità, che è una decisione di modello a sé.
>
> ⚠️ **E una cosa che questo brief NON copre**, per non farla sembrare chiusa:
> i due rossi su `ESCLUSO` (`STATI_ESECUZIONE_LOTTO` e i due `CHECK` divergenti)
> appartengono al cantiere **uscita dal giro**, non a questo.
>
> ---
>
> 🔭 **Da leggere per primo: §11.4 → §11.9.**
> ✅ Del §11.5 è già chiusa la metà visibile: il catalogo della lista, che taceva
> sulle politiche del registro, ora porta le quattro colonne (§11.6).
> ✅ **Il §11.7 è CHIUSO**: cambiare `reset_policy` su un registro che aveva già
> numerato faceva **ripartire il contatore da 1** — provato; ora il secchio nuovo
> nasce dal massimo di quelli con cui può collidere. `20260908-10` applicato il
> 2026-09-08, pgTAP 5/5 verde.
> ✅ **Anche il §11.8 è CHIUSO e APPLICATO** (2026-09-08, 15:34): sotto `ANNUALE` il
> numero esposto di ordini, DDT e resi non portava l'anno e si ripeteva ogni
> gennaio. Sei changeSet `20260908-11..16`, pgTAP nuovo verde e **nove** file
> esistenti riprovati insieme: 73 asserzioni, zero rosse.
> ⭐ Nello stesso giro la **commessa è diventata standard** (decisione di Tid):
> l'anno se lo metteva da sé, ora glielo mette il compositore generico come a
> tutti — e la stringa esce identica byte per byte.
>
> 📌 **Un debito trovato qui è stato RESTITUITO, non archiviato**: la coda che
> solleva il primo motivo di una `fn_check_*` è copiata in **dieci** punti su
> cinque tabelle — domanda di Tid del 2026-09-08, misura fatta per rispondere,
> perimetro suo. Sta in
> [brief-db-coda-primo-motivo-in-un-posto-solo](../work-done/brief-db-coda-primo-motivo-in-un-posto-solo.md).
>
> 📖 **La versione per chi cerca senza sapere che esiste un brief** — le stesse
> regole in linguaggio da guida, e più ricercabili:
> [numerazione-documenti-e-codici](../../guide/numerazione-documenti-e-codici.md)
> §6.3 (il pavimento), §8-bis (gli assi e la politica), §8-ter (l'anno nel numero).
>
> **Correlati:**
> [brief-db-prefisso-sul-registro](../work-done/brief-db-prefisso-sul-registro-e-allineamento-contatori.md) ·
> [brief-db-registri-di-numerazione-emittente-e-trasloco](../work-done/brief-db-registri-di-numerazione-emittente-e-trasloco.md) ·
> [vendite.famiglie_documento](/dbzero/vendite/tabelle/famiglie_documento)

---

## 1. ⭐ L'invariante, e l'asimmetria che la governa

> **Tutto ciò che discrimina il CONTATORE deve poter discriminare anche il
> DOCUMENTO.**

Il contatore vive su `uq_regprog_key`. Ogni combinazione è un **secchio** che
riparte da 1. Se il documento non porta uno di quegli assi nel proprio vincolo di
unicità, il contatore gli può dare un numero che per lui è **già usato**.

⭐ **E i due versi non sono simmetrici** — è la regola che dice quale asse va
dichiarato e quale no:

| | Effetto |
| --- | --- |
| il **contatore** ha un asse che il **documento** non ha | ⛔ **collisione** |
| il **documento** ha un asse che il **contatore** non ha | ✅ **innocuo** — il documento è solo più specifico |

⇒ Un asse va **dichiarato** solo quando può mancare al documento. Un asse che
tutti i documenti portano è sicuro in entrambi i versi, e dichiararlo
creerebbe una seconda sorgente di verità.

⚠️ **E il difetto non si vede finché quell'asse non si muove.** È per questo che
è rimasto invisibile: gli assi che mancano oggi sono fermi.

---

## 2. Come sta oggi — struttura, verificata il 2026-09-01

| Asse del contatore | `fatture` | `ddt` | `ordini` | `resi` | `commesse` |
| --- | --- | --- | --- | --- | --- |
| `registro_id` | ✅ | ✅ | ✅ | ✅ | ⛔ → ✅ **dal 02-09** |
| `anno` | ✅ | ✅ | ✅ | ✅ | ~ dentro la stringa → ✅ **dal 02-09** |
| `serie` | ✅ | ✅ | ✅ | ⛔ | ⛔ |
| `mese` | ⛔ | ⛔ | ⛔ | ⛔ | ⛔ |

```text
fatture   uq_fatture_numero              (registro_id, anno, COALESCE(serie,''), numero)
ddt       uq_ddt_v_anno_serie_numero     (registro_id, anno, serie, numero)
ordini    uq_ordini_v_anno_serie_numero  (registro_id, anno, serie, numero)
resi      uq_resi_anno_numero            (registro_id, anno, numero)          ⛔ senza serie
commesse  uq_commesse_codice             (codice)                             ⚠️ una stringa sola
```

⚠️ **`vendite.commesse` non ha nemmeno `registro_id`**: ha `codice` e
`emittente_soggetto_ruolo_id`. Del registro che l'ha numerata non resta traccia
se non dentro la stringa.

> ✅ **Superato il 2026-09-02** (changeSet `20260902-07`): `registro_id` e `anno`
> sono colonne, con FK e indice, e le 62 righe esistenti sono state riempite
> chiedendo il registro a `fn_lookup_registro_documento`.
> ⚠️ **L'unicità invece è rimasta `uq_commesse_codice`**, e di proposito: il
> codice porta la sigla dell'emittente, quindi è unico **globalmente** — una
> condizione più stretta di quella per registro delle altre quattro. Vedi §4.

---

## 3. ⛔ Il caso `resi`

`vendite.resi` **non ha la colonna `serie`**. `trgfn_resi_gen_numero` non passa
nessuna serie, quindi eredita il `serie_default` del registro — e **non la scrive
da nessuna parte**.

Cambiando `serie_default` su un registro `RESO` **a metà anno**: si apre un
secchio nuovo che riparte da 1 → il primo reso prova a scrivere il numero 1 →
`uq_resi_anno_numero` non ha la serie e quel numero nell'anno esiste già →
**violazione**. La transazione fallisce e col rollback torna indietro **anche
l'incremento del contatore**, quindi al tentativo dopo riparte da 1 e sbatte di
nuovo.

⇒ **Non un dato sporco: un reso che non si numera più**, con un errore che parla
del numero e non nomina la causa.

⭐ **Il morso è confinato all'anno**: `reset_policy` è `ANNUALE` e il reso scrive
`anno` dalla stessa chiamata che gli dà il numero. Cambiare `serie_default` **a
gennaio**, prima del primo reso, non rompe niente — e non lo nota nessuno.

⚠️ Il rollback del contatore è **dedotto dal meccanismo, non provato su un reso
vero**: costruirne uno richiede DDT e partita. Il resto è struttura verificata.

---

## 4. ✅ Il caso `commesse` — CHIUSO il 2026-09-02

> La fotografia qui sotto è del 2026-09-01 e resta com'era scritta. Sotto, cosa
> è successo davvero.

L'unicità è su **una stringa sola**, che incorpora sigla, anno e progressivo —
non la serie, non il registro. Stessa dinamica del §3.

⚠️ **La cura non è la stessa**: sul reso manca *una colonna*, qui manca **tutto
l'aggancio**. Allineare la commessa significa decidere come si aggancia al
registro — modello, non `ALTER TABLE`. **Resta fuori dal piano**, e il presidio
la dichiarerà come debito invece di ignorarla.

### ✅ Com'è andata, ed era più piccola di così

⭐ **La frase «qui manca tutto l'aggancio» era vera a metà.** Guardando le altre
quattro si è visto che il loro campo `numero` contiene la **stringa già
formattata** (`DDT0023454`), non il progressivo nudo — verificato sui dati, non
dedotto. Sulla commessa quella stringa è `codice`, che c'era già.
⇒ Mancavano **due colonne**, non l'aggancio: `registro_id` e `anno`. E nessun
numero da inventare per lo storico, il che ha tolto di mezzo la domanda che
sembrava la più difficile.

⚠️ **Il riempimento delle 62 righe esistenti non ha ricostruito niente a mano**:
il registro si chiede a `vendite.fn_lookup_registro_documento`, la sede unica
della regola «la mia utility, altrimenti quella per tutte». ⛔ Riscrivere quel
predicato con un join su `utility_id` avrebbe risolto **zero righe su 62** — le
commesse hanno un'utility valorizzata e i loro registri valgono «per tutte».
Provato prima di scrivere il changeSet.

⛔ **Le colonne sono NULLABLE, e non è una resa**: una decina di file pgTAP
inserisce in `vendite.commesse` senza passare dalla madre, e un `NOT NULL` li
farebbe rossi insieme senza aggiungere una garanzia che il modello non abbia già
— `codice` è `NOT NULL` e `UNIQUE`, ed è l'identità.

⭐ **Il guadagno vero non è il vincolo: è che l'invariante ora si può
VERIFICARE.** Prima «gli assi stanno dentro la stringa» era una convenzione di
chi compone il codice, controllabile solo rileggendo la funzione. Ora
`db/pgtap/vendite/test-commessa-chiave-numerazione-v1` confronta il codice con
gli assi dichiarati dalle colonne — e se un domani qualcuno cambia la
composizione senza toccare le colonne, o viceversa, diventa rosso.

Dettaglio e decisioni: `brief-be-fe-crud-registri-di-numerazione` §12.6.

### ⚠️ 2026-09-02 — le due colonne hanno fatto diventare rosso un ALTRO presidio

`db/pgtap/vendite/test-identita-documenti-derivata-v1.sql` ha cominciato a
fallire i test 2 e 3 con `have: COMMESSA`. **Non era un difetto dello schema: era
il test.**

Quel file sceglieva fra i due rami dell'identità così:

> «la tabella **ha** la colonna `registro_id`? allora l'unicità deve portarla;
> altrimenti guarda la stringa nuda.»

Era un **proxy**, non la proprietà. Funzionava solo finché *avere* quella colonna
coincideva con l'*avere l'identità sul registro* — e le due cose hanno smesso di
coincidere nel momento esatto in cui questo §4 ha dato a `vendite.commesse`
`registro_id` e `anno` **come dato**, con l'identità che resta la stringa.

⛔ **E il rosso chiedeva un peggioramento.** Preso alla lettera, avrebbe fatto
sostituire `uq_commesse_codice` su `(codice)` con una chiave `(registro_id, anno,
…)`: una chiave più **larga**, cioè meno stretta di quella che c'è. La
`UNIQUE (codice)` da sola è la forma più forte possibile — non lascia collidere
*nessuno*, quindi a maggior ragione non lascia collidere due emittenti.

⭐ **La regola vera è la proprietà, e ora è scritta così**: l'unicità impedisce a
due emittenti di collidere se **o** porta `registro_id` in chiave, **o** è un
indice sulla **sola** colonna del numero. Del secondo ramo il test pretende ora
anche `indnatts = 1`, `NOT NULL` (o `NULLS NOT DISTINCT`) e `indpred IS NULL` —
tre condizioni che tolgono altrettanti modi di non respingere niente, e la
seconda è il difetto del 2026-08-31 in forma generale.
Il test 3 (`anno` in chiave) si applica ora al **solo ramo per-registro**, scritto
dal lato positivo: dove l'identità è la stringa, l'anno è già dentro di essa.

⭐ È nato anche un **test 6, gemello «esiste»**: asserisce che *entrambi* i rami
siano abitati. Senza, il giorno in cui una delle due forme sparisse, metà del
presidio diventerebbe verde per non avere più niente da guardare — e sarebbe
proprio il momento in cui il difetto del §3 potrebbe rientrare.

⚠️ **La lezione va oltre questo file**: il §9 qui sotto dice «tutti derivati», ed
è giusto — ma *derivare dalla cosa sbagliata sembra derivare*. Un presidio che
sceglie un ramo guardando **quali colonne esistono** sta misurando una
coincidenza; deve guardare **la forma del vincolo**, che è dove la proprietà
vive. Verificato per mutazione: annullando il ramo «stringa nuda» tornano rossi
i test 2 e 6, e restringendo `idd_unique_porta` alla prima colonna della chiave
diventa rosso il 3 con `DDT, FATTURA, ORDINE, RESO`.

---

## 5. ✅ La forma della cura — l'asse si DICHIARA sulla famiglia

> **Decisione di Tid, 2026-09-01.**

⛔ **La prima proposta era sbagliata nel bersaglio**: dare la colonna `serie` ai
resi sistemava il **sintomo su una tabella**. Il sesto documento che entra
domani sui registri avrebbe avuto lo stesso problema, e nessuno gliel'avrebbe
chiesto.

⭐ La cura sta dove una famiglia **entra** nei registri: `vendite.famiglie_documento`.

### 5.1 Tre cose diverse che si chiamano «serie»

| Cosa | Dove sta | Che natura ha |
| --- | --- | --- |
| `serie` sul documento | `fatture.serie`, `ddt.serie`, `ordini.serie` | **il fatto**: quale serie è stata usata |
| `serie_default` | `registri_fatturazione` | **la scelta**: cosa usa questo sezionale |
| `colonna_serie` | `famiglie_documento` | **la capacità**: questa famiglia una serie *può* averla, e si chiama così |

> **Sulla FAMIGLIA si dichiara ciò che il documento PUÒ esprimere. Sul REGISTRO
> si sceglie ciò che quel sezionale FA.**

⛔ **`serie_default` non si sposta.** Resta sul registro, dov'è giusto che stia.

### 5.2 ⭐ Il nome della colonna, non un booleano

`famiglie_documento.colonna_serie text NULL` — `NULL` = la famiglia non ha una
serie.

Un `gestisce_serie boolean` messo a `true` su una famiglia la cui tabella non ha
la colonna riporterebbe il difetto di partenza, **e nessuno se ne accorgerebbe**.
Col nome, il presidio verifica che la colonna esista davvero.

⭐ **Ed è già l'idioma della tabella**: `colonna_numero` e
`colonna_billing_account` esistono esattamente per questo — *«il numero si chiama
`numero` su fatture ma `codice` sulla commessa: il predicato derivato deve
saperlo e non può dedurlo»*.

Valori: `FATTURA`/`DDT`/`ORDINE` → `'serie'` · `RESO`/`COMMESSA` → `NULL`.

#### ⛔ E sulla famiglia NON va un default della serie — `prefisso` e `serie` sono opposti

| Famiglia | prefissi distinti | serie distinte |
| --- | ---: | ---: |
| `FATTURA` | **1** | **6** |
| `DDT` · `ORDINE` · `RESO` · `COMMESSA` | 1 | 1 |

Il **prefisso** ha un default sulla famiglia (`prefisso_default`) perché il suo
mestiere è **essere uguale**: tutti i DDT cominciano per `DDT`. La **serie** fa
il mestiere opposto — esiste per **differire**, ed è ciò che separa i sezionali
di una stessa famiglia e di uno stesso emittente (Back-office, Front-office, NC).

⇒ Un `serie_default` sulla famiglia dovrebbe rispondere «quale delle sei?», e non
c'è risposta: collasserebbe proprio la distinzione per cui la serie esiste.

⚠️ Il conteggio è un **fatto datato**: serviva a smentire il ragionamento se le
sei serie fossero risultate uguali. Il motivo sta nel modello.

#### ⚠️ E nemmeno l'OBBLIGATORIETÀ, e non è una dimenticanza

«Questa famiglia **deve** avere una serie» è una domanda diversa da «può
averla», e non entra in questo cantiere:

1. **non serve al difetto** — il difetto è l'opposto, una serie dove il documento
   non sa tenerla. L'obbligatorietà è completezza di dominio, non sicurezza;
2. **nessuna regola di dominio la sostiene**: `uq_fatture_numero` usa
   `COALESCE(serie,'')`, quindi il vuoto è un valore legittimo. Che oggi tutti e
   sei i registri FATTURA ce l'abbiano è **popolazione**, e non decide;
3. ⛔ **sarebbe la quarta** colonna dichiarata e non implementata di questa
   famiglia di tabelle, dopo `mese`, `reset_policy` e i valori tolti dal CHECK.

Se servirà è una decisione sua, col suo guard.

### 5.3 ⛔ Sul registro si RIFIUTA, non si ignora

Se un registro `RESO` accettasse un `serie_default` e il motore lo ignorasse in
silenzio, avremmo ricreato il difetto che il cantiere del prefisso ha appena
tolto da `config.sistema_codici`: *un campo editabile dal pannello che
l'amministratore cambia senza ottenere niente e senza modo di accorgersene*.

⚠️ **Non può essere un `CHECK`**: la condizione attraversa `famiglie_documento`, e
un CHECK non fa sottoquery. Serve un **guard `_a10_`**, in `INSERT` **e**
`UPDATE`: un registro non deve nemmeno *nascere* con una serie che la sua
famiglia non porta.

⭐ **E il motivo passa da una `fn_check_*` che il guard CHIAMA** (§12.5.2), perché
serve anche alla maschera: il campo `serie_default` va disabilitato **col
perché**, non lasciato grigio.

### 5.4 Il terreno è pulito — verificato il 2026-09-01

| | |
| --- | --- |
| registri con `serie_default` valorizzata | **6, tutti `FATTURA`** — DDT, ORDINE, RESO, COMMESSA sono tutti a NULL |
| righe del mirror CSV `registri_fatturazione.csv` | **3, tutte `FATTURA`** (Front-office `R2`, Back-office `R1`, NC vuota) |
| `fn_provision_registri_emittente` | **non** imposta `serie_default` |

⭐ **E questo corregge una mia obiezione precedente.** Avevo scritto che un guard
su `serie_default` non era montabile perché il mirror la riscrive a ogni migrate:
vero per un divieto **secco**, falso per uno **condizionale** — il mirror tocca
solo le fatture, che sono la famiglia dove la serie è legittima.

---

## 6. ✅ `mese` sparisce

> **Decisione di Tid, 2026-09-01.**

`mese` sta nella chiave del contatore e **non compare in nessun vincolo di
unicità di nessun documento**. È innocuo solo perché è **inchiodato** in due
punti: `v_mese := 0` nel corpo vivo di `fn_get_next_progressivo`, e
`chk_registri_fatturazione_reset` che ammette solo `ANNUALE`.

⛔ **Una dimensione dormiente in una chiave non è inutilizzata: è ARMATA.** Un
reset mensile farebbe collidere **tutti e cinque** i documenti, non i due del
§3-§4. E a tenerla chiusa non è un vincolo: è una **rinuncia**, che si revoca per
distrazione.

⭐ E col §5 la revoca ha una strada pulita: se un giorno servisse, `mese` torna
come `colonna_mese` sulla famiglia **insieme** alla colonna sui documenti. Cioè
il lavoro vero. Tenerla adesso non anticipa niente.

### 6.1 Il censimento dei LETTORI — verificato il 2026-09-01

Il censimento si fa sulla **lettura**, non sulla parola: «mese» nel progetto è
quasi sempre `competenza_mese` o «il primo del mese».

| Dove | Chi legge `registri_fatturazione_progressivi.mese` |
| --- | --- |
| funzioni PL/pgSQL | **una sola**: `vendite.fn_get_next_progressivo` |
| viste · backend Python · pgTAP · CSV di seed | **nessuno** |

⚠️ `fn_calcola_data_documento` la nomina **solo in un commento**.

### 6.2 Cosa la tiene attaccata

```text
uq_regprog_key                 UNIQUE (registro_id, anno, mese, serie)
uq_registri_progressivi_scope  UNIQUE INDEX (registro_id, anno, COALESCE(mese,0), COALESCE(serie,''))
chk_regprog_mese_valid         CHECK (mese = 0 OR mese BETWEEN 1 AND 12)
                               NOT NULL
```

### 6.3 ⭐ E si scopre un UNIQUE ridondante che il presidio non vede

Le quattro colonne sono **tutte `NOT NULL`** ⇒ i `COALESCE` di
`uq_registri_progressivi_scope` sono **no-op**, e quell'indice esprime la
**stessa chiave** di `uq_regprog_key`.

⛔ **`dbops.vw_duplicate_indexes` non lo segnala** (verificato: zero righe): il
confronto lavora sulle colonne, e qui una chiave è colonne e l'altra è
**espressioni**.

⭐ *Un duplicato nascosto dietro espressioni che non fanno niente è invisibile
proprio al presidio nato per i duplicati.* Si toglie nello stesso giro, e la
cecità va **dichiarata**.

### 6.4 Il fatto datato che avrebbe potuto smentire il piano

Le righe di `registri_fatturazione_progressivi` sono **10, tutte con `mese = 0`**
⇒ nessuna riga distinta collassa sulla chiave nuova. ⚠️ Serviva a cercare un
controesempio, non a decidere.

---

## 7. ✅ `reset_policy` diventa vera e funzionante

> **Decisione di Tid, 2026-09-01.**

### 7.1 Oggi è dichiarata e mai letta

```text
chk_registri_fatturazione_reset   CHECK (reset_policy = 'ANNUALE')     — un valore solo
fn_get_anno_registro              v_anno := EXTRACT(YEAR FROM p_data)  — hardcoded
```

Censito il 2026-09-01: `fn_numera_fattura_opz_emessa` e `fn_assign_numero_fattura`
la nominano **solo nei commenti**; `fn_provision_registri_emittente` la **scrive**
e basta. **Nessuna funzione ramifica su `reset_policy`.**

⇒ È la **terza** colonna di questa famiglia dichiarata e non letta, dopo `mese` e
i valori tolti dal CHECK.

### 7.2 ⭐ Perché questa si accende invece di sparire, a differenza di `mese`

È l'asimmetria del §1, applicata:

* accendere **`MENSILE`** è **pericoloso** — nessun documento porta il mese ⇒ il
  contatore discriminerebbe su un asse che il documento non ha ⇒ collisione;
* accendere **`NESSUNA`** è **sicuro** — tutti i documenti portano `anno` ⇒ il
  contatore userebbe **meno** assi, non di più, e cade nel verso innocuo.

⭐ E la numerazione continua fra gli anni è una cosa che i gestionali fanno
davvero su DDT e ordini. Il parametro esiste già, sul registro: manca solo che
qualcuno lo legga.

### 7.3 ⛔ Due `anno` che si chiamano uguale, e non vanno confusi

| | Cosa significa | Sotto `NESSUNA` |
| --- | --- | --- |
| `registri_fatturazione_progressivi.anno` | **la chiave del secchio** | diventa `0` — un secchio solo |
| `fatture.anno`, `ddt.anno`, `ordini.anno`, `resi.anno` | **l'anno del documento** | resta **l'anno solare**, sempre |

⇒ **`fn_get_anno_registro` non si tocca**: risponde a *«che anno è il
documento»*, e la risposta non cambia. Ha **quattro** chiamanti
(`fn_assegna_numero_documento`, `fn_assign_numero_fattura`,
`fn_get_next_progressivo`, `fn_get_or_create_commessa`) e cambiarle la firma li
toccherebbe tutti per un motivo che non li riguarda.

⭐ **La politica si legge dove serve, e serve in un punto solo**:
`fn_get_next_progressivo` è **l'unica funzione che legge `progressivi.anno`**
(censito). Lì `v_anno` diventa:

```text
ANNUALE  → vendite.fn_get_anno_registro(p_data)
NESSUNA  → 0
```

⇒ Raggio d'azione: **una funzione**.

### 7.4 ⚠️ Il sentinella `0`, e perché non è il ritorno di `mese = 0`

Sembrano la stessa cosa e non lo sono:

* `mese = 0` significava *«questo asse non è usato da nessuno, mai»* — un
  segnaposto per una funzione non implementata;
* `anno = 0` significherà *«questo registro non azzera per anno»* — un valore con
  un **lettore vivo**, che una politica dichiarata sceglie.

⚠️ **Ma la coerenza fra i due — `anno = 0` ⟺ registro `NESSUNA` — non la può
tenere un `CHECK`**, perché attraversa due tabelle. La tiene la funzione, ed è il
presidio del §9 a verificarla.

### 7.5 Cosa cambia, in concreto

* `chk_registri_fatturazione_reset` riammette **`NESSUNA`** (⛔ non `MENSILE`: quello
  è l'asse che il §6 toglie);
* `fn_get_next_progressivo` legge la politica del registro;
* il **pavimento** non si tocca: `fn_get_pavimento_sequenza` e compagne leggono i
  progressivi **senza filtrare per anno** (censito), quindi guardano già
  attraverso gli anni — che è ciò che `NESSUNA` vuole.

---

## 8. Il piano

> ⛔ Ordine vincolante: **prima il codice, poi lo schema** dove una colonna cade.
> ⚠️ L'autogen ordina per NN mescolando `00_schema` e `20_code`: l'ordine si
> impone con la **numerazione**, non con la cartella.

| Passo | Cosa | Dove |
| --- | --- | --- |
| **M-1** | `fn_get_next_progressivo` senza `mese` **e** che legge `reset_policy` | `20_code/vendite` |
| **M-2** | `chk_regprog_mese_valid` e `uq_registri_progressivi_scope` via; `uq_regprog_key` su `(registro_id, anno, serie)`; `DROP COLUMN mese` | `00_schema/vendite`, NN > M-1 |
| **R-1** | `chk_registri_fatturazione_reset` riammette `NESSUNA` | `00_schema/vendite` |
| **S-1** | `famiglie_documento.colonna_serie` + seed dei cinque valori | `00_schema` + CSV `80_data` |
| **S-2** | `script.fn_check_registro_serie_ammessa` — la pure check §12.5.1 | `20_code/script` |
| **S-3** | Il guard `_a10_` su `registri_fatturazione` (INSERT + UPDATE OF `serie_default`, `famiglia_documento`) che la **chiama** | `20_code/vendite` |
| **P-1** | I presidi del §9 | `db/pgtap/vendite` |

⚠️ **M-1 fa due cose insieme di proposito**: toglie `mese` e accende
`reset_policy` nella **stessa** riscrittura della chiave del secchio. Separarle
significherebbe riscrivere due volte lo stesso `v_anno`/`v_mese`, con una
revisione intermedia che non corrisponde a nessuno stato voluto.

⛔ **Un codice errore nuovo serve** per il rifiuto della serie (§5.3): il rifiuto
non esiste ancora, quindi non c'è nessuna madre muta da sanare — è lo stesso
ragionamento del guard sulla forma del numero.

---

## 9. ⭐⭐ I presidi — l'invariante, non i casi

⛔ **Un test che verificasse «resi non ha la serie» proverebbe l'oggi.** Il
difetto non è una colonna mancante: è che **nessuno controlla** che i documenti
numerati sui registri portino la chiave del contatore. È così che `resi` e
`commesse` sono entrati col trasloco senza che niente diventasse rosso.

Tre controlli, tutti **derivati**:

1. **La dichiarazione è vera** — per ogni famiglia con `colonna_serie`
   valorizzata, quella colonna **esiste** sulla tabella dichiarata **e** compare
   nel vincolo di unicità del numero;
2. **Il registro rispetta la dichiarazione** — nessun registro di una famiglia
   con `colonna_serie NULL` ha `serie_default` valorizzato;
3. **Il secchio rispetta la politica** — `anno = 0` se e solo se il registro è
   `NESSUNA` (§7.4).

Nessun elenco a mano da nessuna parte. Il giorno che una famiglia nuova entra sui
registri senza la chiave completa, il test è **rosso prima del merge**.

> ⚠️ **2026-09-02 — e quel test 6 è diventato l'UNICO presidio, per un motivo
> istruttivo.** `20260831-71` aveva copiato la stessa query in una
> `preCondition` di migrate. In CI il migrate è morto lì: quei guard li genera
> `dbops.fn_run_automations_attivo`, cioè `ci_apply`, che gira **dopo** —
> durante la prima passata non ce n'è nemmeno uno, `string_agg` su zero righe dà
> `NULL` e il conteggio è 0. La preCondition è stata **tolta** (non resa
> condizionale): era un doppione, e il posto giusto per un invariante è il
> pgTAP, che gira a `ci_apply` avvenuto. Regola: `linee-guida-sql.md` §11.5.

⭐ È la forma del test 6 di `test-fn-check-registro-disattivabile-v1.sql` —
*«il giorno che ne compare una quarta diventa rosso»* — che su questa stessa
tabella ha già funzionato una volta.

> ✅ **Non più, dal 2026-09-02**: vedi §4. La riga qui sotto resta come stava.

⚠️ **`commesse` sarà rossa dal primo giorno**, ed è debito **dichiarato**: o si
esclude con un motivo scritto, o il test nasce a fallire. La scelta va fatta
esplicitamente, non per omissione.

---

## 10. ⛔ Cosa non si tocca

* **`serie_default` non si sposta** e non si vieta in blocco: resta sul registro,
  e il divieto è **condizionato** alla dichiarazione della famiglia.
* **`fn_get_anno_registro`** non cambia firma: risponde all'anno del *documento*,
  non a quello del secchio (§7.3).
* **`MENSILE`** non rientra nel CHECK: è l'asse che il §6 toglie.
* **`config.sistema_codici`** non c'entra: la forma del numero è uscita di lì il
  2026-08-31 di proposito.
* **`commesse`** resta fuori dal piano (§4), dentro il presidio come debito.
* **Nessuna migrazione si applica** senza che Tid lo dica, per quel comando.

---

## 11. ✅ Stato dello sviluppo — **APPLICATO** il 2026-09-01

| Passo | Esito | File |
| --- | --- | --- |
| **R-1** | ✅ | `00_schema/vendite/20260901-06` — il CHECK riammette `NESSUNA` |
| **M-1** | ✅ | `20_code/vendite/20260901-07` — via `mese`, e `reset_policy` si legge |
| **M-2** | ✅ | `00_schema/vendite/20260901-08` — via la colonna e l'UNIQUE ridondante |
| **S-1a** | ✅ | `00_schema/vendite/20260901-09` — `famiglie_documento.colonna_serie` |
| **S-2** | ✅ | `20_code/script/20260901-10` — `fn_check_registro_serie_ammessa` |
| **S-3** | ✅ | `20_code/vendite/20260901-11` — il guard che la **chiama** |
| **S-1b** | ✅ | `80_data/20260901-12` + `famiglie_documento_colonna_serie.csv` |
| — | ✅ | codice `E_REGISTRO_SERIE_NON_AMMESSA` (`DATO_ERRATO`) + messaggio, append ai due CSV |
| **P-1** | ✅ **9/9 verdi** | `db/pgtap/vendite/test-chiave-contatore-assi-dichiarati-v1.sql` |

✅ **Applicato da Tid il 2026-09-01, pgTAP verdi.** I nove changeSet del
2026-09-01 risultano `EXECUTED` sul `databasechangelog`, e lo stato strutturale
è quello voluto:

| | |
| --- | --- |
| colonna `mese` | **non esiste più** |
| `uq_registri_progressivi_scope` (il duplicato invisibile) | **non esiste più** |
| chiave del secchio | `UNIQUE (registro_id, anno, serie)` |
| `chk_registri_fatturazione_reset` | ammette `ANNUALE` **e** `NESSUNA` |
| guard della serie | **montato** |
| `E_REGISTRO_SERIE_NON_AMMESSA` | **a catalogo** |

E il seed è quello dichiarato: `FATTURA`/`DDT`/`ORDINE` → `serie`,
`RESO`/`COMMESSA` → `NULL`.

### 11.1 Come è stato provato

L'SQL **estratto dai sei YAML**, eseguito **nell'ordine di numerazione** su una
transazione con `ROLLBACK`, col seed e il codice errore aggiunti dentro. Poi il
pgTAP nella stessa forma.

| Prova | Esito |
| --- | --- |
| `ANNUALE`: il secchio porta l'anno solare | ✅ |
| `NESSUNA`: due documenti di **anni diversi** prendono 1 e 2 | ✅ il contatore non riparte |
| registro `RESO` con serie, in **INSERT** | ✅ rifiutato |
| lo stesso **senza** serie | ✅ passa (il gemello positivo) |
| `UPDATE` che mette una serie su un `RESO` | ✅ rifiutato |
| il mirror CSV che riscrive `serie_default` sulle 6 fatture | ✅ passa — **il migrate non si rompe** |

### 11.2 ⚠️ Tre cose trovate scrivendo, che il piano non prevedeva

**1. Il seed non poteva stare in `00_schema`.** Era la strada che sembrava
ovvia — la colonna nasce lì — ed è quella del precedente `prefisso_default`
(`20260831-51`). ⛔ Ma su un database **ricostruito da zero** `00_schema` gira
quando la tabella è ancora **vuota**: l'`UPDATE` non tocca nessuna riga, le
famiglie arrivano dopo dal mirror, e il valore resta `NULL` in CI mentre su dev
è popolato. ⇒ Il seed vive in `80_data`, con un **CSV dedicato** e la chiave
naturale `codice_interno` — il pattern di `registri_fatturazione_politica_data`.

📌 **E ne discende un sospetto su `prefisso_default`, che non è di questo
brief**: seminata con un `UPDATE` in `00_schema` e assente dal mirror, potrebbe
essere `NULL` su un database ricostruito — e a leggerla è
`fn_provision_registri_emittente`, che darebbe ai registri nuovi un prefisso
vuoto. **Da verificare**, non è un'affermazione.

> ✅ **Il sospetto era fondato, e non è rimasto tale: la CI lo ha trovato il
> 2026-09-02**, con la stessa faccia di un altro difetto («Expected '0' got
> '4'») su una preCondition diversa — la terza di
> `20260831-53`, quella che pretende il `prefisso_default` sulle famiglie
> attive. ⭐ **E il rimedio è quello che questo §11.2 aveva già scritto per la
> serie**: il valore va dove la sua sede dice, cioè un CSV di `80_data` —
> `famiglie_documento_formato.csv` (`prefisso_default` + `lunghezza_default`),
> caricato da `20260902-53-01-seed-famiglie-documento-formato`, forma copiata
> riga per riga da `20260901-12`. Il backfill di `20260831-51` resta e non fa
> danno: su un database nuovo trova zero righe, su uno vecchio i valori giusti.
> ⚠️ Riverificato il 2026-09-08 sul database: le cinque famiglie portano il
> prefisso, e la `FATTURA` lo ha `NULL` **di proposito** — il suo numero è nudo,
> ed è il token `NULL` del CSV a dirlo.

**2. Il guard della serie ha due accorgimenti che tengono in piedi il migrate**,
e sono la ragione per cui non è un `CHECK` né un guard ingenuo:

* in `UPDATE` confronta i **valori**, perché il mirror `20260127-57` riscrive
  `serie_default` a ogni migrate e `UPDATE OF` scatta comunque;
* il ramo «famiglia non trovata» della check **tace** — su un database
  ricostruito il mirror dei registri gira **prima** di quello delle famiglie
  (`includeAll` ordina per nome file), e senza quel ramo il migrate di un DB
  nuovo fallirebbe. ⚠️ Non è fail-open: in esercizio la FK garantisce la riga, e
  lo stato finale lo verifica il test 6.

**3. La trappola dell'auto-gen è scattata.** Il corpo di `fn_get_next_progressivo`
è stato preso dalla funzione **viva** — che è la fonte giusta per il corpo — ma
`pg_get_functiondef` **scioglie i `%TYPE` della firma** in tipi concreti. La
firma è stata ripresa da `20260831-06`, l'ultimo YAML che la dichiara.
⇒ **Il corpo dal vivo, la firma dall'ultimo YAML.**

### 11.3 ⚠️ Un difetto trovato leggendo l'output, non il codice

Il messaggio di `E_REGISTRO_SERIE_NON_AMMESSA` diceva *«Registro %s: la famiglia
%s…»* e riceveva `(serie, famiglia)`: a video usciva **«Registro X1»**, dove `X1`
è la **serie**. Arità giusta — due segnaposto, due valori — e frase **falsa**.

⇒ Corretto in *«La famiglia %s non gestisce le serie: questo sezionale non può
portare la serie %s»*, coi valori riordinati.

⭐ **La lezione, che vale oltre questo caso**: l'ordine dei `VARIADIC` non si
verifica contando i segnaposto, si verifica **leggendo la frase resa**. Un
cancello sull'arità non lo avrebbe visto.

### 11.4 🔭 Cosa resta

> ⭐ **Riverificato il 2026-09-08**, riga per riga e contro il database, non
> contro il ricordo: delle quattro voci qui sotto **due sono chiuse**, una resta
> **decisione di Tid**, una resta **debito dichiarato** — e ne è emersa una
> **quinta**, che questo elenco non prevedeva (§11.5). Le voci superate si
> marcano e non si cancellano: la riverifica successiva deve poter vedere anche
> la spunta di prima.

* ✅ ~~⚠️ **Due `reason_key`** ora emesse dal database e assenti dai `locales`~~ —
  **chiuse.** Le due chiavi ci sono in `it.json` **e** `en.json`,
  `scripts/check_i18n_keys.py` è **verde** (*«nessuna chiave emessa dal DB
  risulta irrisolvibile»*, riverificato il 2026-09-08), e la seconda è **resa a
  video**: `RegistroNumerazioneDrawer.vue` la stampa sul campo `serie_default`
  in sola lettura, che è la sede per cui la check era stata scritta (§5.3).
  ⚠️ **Ed è la spunta che vale meno delle altre se si guarda solo il
  cancello**: `check_i18n_keys.py` verifica che la chiave *esista*, non che
  qualcuno la *chieda* — quello si guarda a video, ed è la regola di
  `linee-guida-sql.md` §12.5.5. Qui è stato guardato il chiamante.
  * ~~`amministrazione.registri_fatturazione.forma_blocco.ha_numerato`~~ ✅
  * ~~`amministrazione.registri_fatturazione.serie_blocco.non_gestita`~~ ✅
* ⚠️ **`script.fn_check_registro_forma_modificabile` ha la firma senza `%TYPE`**
  (`p_registro_id bigint` invece di `vendite.registri_fatturazione.id%TYPE`,
  come fa la gemella). ⛔ È in un changeSet **già pushato**, quindi non si
  modifica. ⭐ E un changeSet correttivo sarebbe **un no-op sul database**:
  `%TYPE` si risolve allo stesso `bigint` e la firma non sta in `prosrc`. ⇒ È un
  **debito di sorgente**, non di comportamento: si paga alla prossima revisione
  di quella funzione, o con un changeSet dedicato se si preferisce la coerenza
  degli YAML. Decisione a Tid.
  ⚠️ La verifica è sullo **YAML**, non sulla doc auto-gen: `20260901-02` è
  l'unico changeSet che dichiara quella funzione e dice ancora
  `p_registro_id bigint`. La doc auto-gen non può fare da prova —
  `pg_get_functiondef` scioglie i `%TYPE` comunque (è la trappola del §11.2/3).
  ✅ **DECISA il 2026-09-08 — si lascia com'è, e non si deprèca niente.**
  Un changeSet correttivo sarebbe un **no-op sul database**: cambierebbe uno YAML
  già pushato senza cambiare una riga di ciò che gira. ⛔ Riscrivere un changeSet
  applicato per ottenere zero è il tipo di lavoro che *sembra* igiene e produce
  solo un secondo changeSet da leggere. ⇒ Il debito resta **di sorgente**,
  dichiarato qui, e si paga alla prossima revisione di quella funzione — se e
  quando ce ne sarà una.
* ✅ ~~⛔ **`commesse` resta scoperta**~~ — **chiusa il 2026-09-02**, vedi §4:
  dichiara `colonna_serie NULL`, quindi i
  presidi la proteggono dal prendere una serie — ma la sua unicità resta su una
  **stringa sola**, senza registro né serie. Debito dichiarato.
  ⚠️ Riverificato il 2026-09-08: `registro_id` e `anno` sono colonne popolate su
  **tutte** le 66 righe, e `test-commessa-chiave-numerazione-v1` è verde (6/6).
  Il debito è quello e solo quello: la forma dell'unicità.

### 11.5 🔴 La quinta voce, che l'elenco non prevedeva — `reset_policy` è accesa e irraggiungibile

> Trovata il 2026-09-08 riverificando §7, e **non è un difetto del lavoro
> consegnato**: è ciò che il §7 lascia sul tavolo, e che nessuno ha raccolto.

Il §7 ha acceso la politica **dove si legge** — `fn_get_next_progressivo`
ramifica davvero su `reset_policy`, e il `CHECK` ammette `NESSUNA`. Ma la
politica **non si può scegliere da nessuna parte**: il backend tiene
`reset_policy` fuori dalla whitelist di **creazione e di modifica**
(`registri_repository.py`, `_CAMPI_CREATE`/`_CAMPI_UPDATE`), quindi un registro
nasce `ANNUALE` per default della colonna e `ANNUALE` resta, salvo un `UPDATE`
scritto a mano in `psql`.

⛔ **E il motivo scritto accanto a quell'esclusione oggi dice il falso**, in due
punti che si citano a vicenda:

| Dove | Cosa dice | Da quando è falso |
| --- | --- | --- |
| `backend/apps/vendite/db/registri_repository.py` | *«`reset_policy` è inchiodata ad ANNUALE dal CHECK `chk_registri_fatturazione_reset` (è un FATTO, non un campo)»* | 2026-09-01, changeSet `20260901-06` |
| `work-done/brief-be-fe-crud-registri-di-numerazione` §2 | *«`reset_policy` non è una scelta: il CHECK la inchioda ad ANNUALE. Va mostrata come fatto, non come campo»* | idem — **stesso giorno** del changeSet |

⭐ **Il difetto è di forma nota, ed è lo specchio del §5.3.** Là il pericolo era
un campo che l'amministratore cambia senza ottenere niente; qui è un parametro
che **ottiene qualcosa** e che nessuno può cambiare. In entrambi i casi la cura
non è il campo: è che **ciò che il documento afferma corrisponda a ciò che il
database ammette**.

⚠️ **Fatto datato, non premessa** (2026-09-08): i 14 registri sono tutti
`ANNUALE` e i 10 secchi portano l'anno solare, zero violazioni dell'invariante
del §7.4. ⛔ Il che non dice *«non serve»*: dice che il ramo `NESSUNA` oggi non
ha un controesempio, perché nessuno ha una strada per produrlo.

**Cosa restava da decidere, ed era di Tid** — le due mosse erano indipendenti:

1. ⚠️ **La riga falsa va tolta comunque**, anche scegliendo di non esporre
   niente: un commento che motiva un'esclusione con un vincolo che non esiste
   più è la cosa che il prossimo legge e crede. ⛔ **Perimetro**: sta in
   `backend/`, quindi non la tocca il DB.
2. 🔭 **Se la politica va scelta**, è lavoro BE+FE: `reset_policy` in
   `_CAMPI_CREATE` (⛔ *non* in update — cambiarla su un registro che ha già
   consegnato numeri sposta il secchio sotto i piedi al contatore, ed è
   esattamente la famiglia di guasti del §3), più il campo in maschera con le
   due voci. ⭐ Il presidio esiste già: `test-chiave-contatore-assi-dichiarati-v1`
   test 9 per il ramo `NESSUNA`, `test-registri-progressivi` test 4 per
   `ANNUALE` — i due rami sono coperti in due file diversi, e il gemello
   positivo c'è.

---

### 11.6 ✅ E il §11.5 aveva una seconda metà: il catalogo della lista taceva sulle POLITICHE

> Osservazione di Tid, 2026-09-08: *«sulla lista csv delle colonne manca come
> minimo `reset_policy`»*. Vero, e più largo di una colonna.

Il catalogo `vendite.registri_numerazione` (`ui.lista_colonna`, lista 54) portava
**dieci** colonne più `azioni`: identità, forma del numero, stato, `data_insert`.
⛔ **Mancava l'intero gruppo delle politiche** — le quattro colonne che dicono
*come il registro si comporta*, tutte già proiettate dal repository e invisibili
in lista:

| campo | cosa governa | perimetro |
| --- | --- | --- |
| `reset_policy` | il **secchio del contatore** | ⭐ **tutte** le famiglie |
| `politica_data_documento` | la **data del documento** (`OGGI` / `FINE_MESE_COMPETENZA`) | di fatto FATTURA — sulle altre il `CHECK` la inchioda a `OGGI` |
| `limite_emissione_giorni` · `limite_emissione_giorno_mese` | il **limite di emissione** | FATTURA (`chk_registri_fatturazione_famiglia_regole_fattura`) |

⭐ **Non è una riga dimenticata, è una natura mancante**: il catalogo raccontava
*identità + forma + stato* e taceva sul comportamento. E su `reset_policy` pesa
il §11.5 — non essendo editabile da nessuna parte, **la lista è l'unico posto in
cui può vedersi**.

**Seminate le quattro** (CSV `80_data/sql/ui/lista_colonna.csv` righe 739-742 +
`lista_preset_colonna.csv`), gruppo nuovo **«Regole»**, `attivo = t`:

* ⭐ `attivo = t` **è ammesso qui**, e di solito non lo è: il cancello
  `apps/core/tests/db/test_lista_proiezione_campo_sorgente.py` pretende che ogni
  `campo_sorgente` attivo sia una chiave che la SELECT consegna davvero — e
  `_PROIEZIONE` le porta già tutte e quattro. ⛔ Su una colonna non proiettata
  sarebbe stato `attivo = f` fino al commit del BE;
* **fuori dal preset standard** (`visibile = f`): la vista di default resta a
  dieci colonne, la politica se la accende chi la cerca in «Personalizza
  colonne». ⚠️ Le due `limite_*` per **modello** sono vuote su quattro famiglie
  su cinque, e una colonna vuota di default sarebbe rumore;
* **`ordinabile = f`, `ricercabile_full = f`** — vedi la richiesta BE qui sotto;
* le **quattro chiavi i18n** in `it.json` e `en.json` nello stesso giro
  (`check_i18n_keys.py`: 609 intestazioni di colonna, tutte tradotte).

#### ⚠️ La prova del mirror, e la trappola che ha fatto scattare

Il CSV ha un mirror `runOnChange: true` (`20260806-15`): **appendere una riga
sveglia il loader, che rilegge tutto il file** (AGENTS §11.2). Rigiocato l'upsert
su **tutte** le righe dei due CSV (741 + 678) in transazione annullata: passano.

⛔ **Ma il primo giro era rosso, e il rosso era della PROVA, non del CSV.** Un
`\copy … FORMAT CSV` rende la cella vuota come `NULL`, e la riga 170
(`reso_id`, `etichetta` vuota) è morta sul `NOT NULL`. Nel database quella riga
ha `''`: il `loadUpdateData` scrive la **stringa vuota** sulle colonne dichiarate
`type: STRING` e `NULL` solo su `NUMERIC`/`BOOLEAN`, e il mirror era **RERAN con
successo il giorno prima**. ⇒ La prova è stata riscritta fedele al loader
(`NULL` su un token impossibile + `NULLIF` sulle sole colonne numeriche).
⭐ È la stessa lezione già in casa sul `campo_sorgente` delle colonne azione:
*una prova che simula un caricamento prova la simulazione*, e qui avrebbe
accusato un CSV sano.

#### ⚠️ Quello che la cella mostrerà, e va detto prima del collaudo

Le due colonne di politica renderanno il **codice nudo** — `ANNUALE`/`NESSUNA`,
`OGGI`/`FINE_MESE_COMPETENZA` — mentre il drawer degli stessi due campi mostra
l'etichetta tradotta (`politica_oggi`, `politica_fine_mese_competenza`).
⛔ **Non è una svista del seed, ed è una cosa che non si inventa qui**: in tutto
il catalogo `ui.lista_colonna` non esiste **nessuna** colonna `tipo_dato = enum`
(482 `string`, 111 `numeric`, 57 `date`, 47 `datetime`, 40 `boolean`), quindi non
c'è un meccanismo di casa che traduca il *valore* di una cella — solo la sua
intestazione. Tradurli vorrebbe dire **inventare quel meccanismo**, che è un
cantiere FE suo e riguarda tutte le liste, non questa.
⭐ Su una lista di amministrazione il codice è anche l'informazione giusta: è la
parola che il `CHECK`, il messaggio d'errore e questo brief usano.

#### 📌 Cosa ricade sul backend (richiesta, non implementazione)

| # | Cosa | Perché |
| --- | --- | --- |
| BE-L1 | ⚠️ **Togliere la riga falsa** su `reset_policy` in `registri_repository.py` (§11.5) | motiva un'esclusione con un `CHECK` che non esiste più |
| BE-L2 | 🔭 *Se* si vuole ordinare per politica: `reset_policy` (e le altre tre) in `_ORDER_COLS` | oggi `ordinabile = f` a catalogo, quindi la freccia non c'è e nessuno prende un 400 |

⛔ **BE-L2 muove DUE cose insieme, o diventa rosso.** `test_liste_configurabili_seed`
lega catalogo e whitelist **nei due versi**: una colonna che il backend sa
ordinare e che il catalogo tiene a `ordinabile = f` è *«capacità irraggiungibile»*
e fallisce. Chi aggiunge la riga al repository edita il CSV nello stesso commit.
✅ Verificato oggi con le stesse due fonti del test — seed e costante: entrambi i
versi puliti, e tutti i `campo_sorgente` attivi sono consegnati dalla proiezione.

---

### 11.7 🔴 Il PASSAGGIO di politica su un registro che ha già numerato — provato il 2026-09-08

> Domanda di Tid: *«molti numeratori non hanno un reset, per esempio gli ordini:
> che valore metto? Oppure c'è un flag che attiva/disattiva il reset?»*

**Non c'è un flag a parte: `reset_policy` È l'interruttore** — `ANNUALE` |
`NESSUNA`, e per «non si azzera» il valore è `NESSUNA`. Ma la domanda ne apre
una che il §7 non aveva guardato: **cosa succede a cambiarla su un registro che
ha già consegnato numeri.**

⛔ **Riparte da 1.** Provato in transazione annullata, non dedotto:

| passo | esito |
| --- | --- |
| due numeri con `ANNUALE`, nel 2026 | 1, 2 — secchio `(anno 2026)` |
| `UPDATE … SET reset_policy = 'NESSUNA'`, poi un numero | ⛔ **1**, in un secchio `(anno 0)` nato a zero |
| innescato `(anno 0)` al massimo già emesso, poi un numero | 3 — e nel 2027 prosegue |

**Il meccanismo**, letto dalla funzione viva: il contatore cerca il secchio
`(registro_id, anno, serie)` e, se non lo trova, lo **crea a `last_numero = 0`**.
Cambiare politica cambia la chiave ⇒ il secchio nuovo non esiste ⇒ zero. Il
documento invece tiene il suo `anno` **solare**, quindi
`uq_ordini_v_anno_serie_numero` trova quel numero già usato: è il guasto del §3,
entrato da un'altra porta.
⚠️ **E il pavimento non para il colpo**: `fn_get_pavimento_data_documento` è un
pavimento di **date**, non di numeri — il `GREATEST` che «non fa mai arretrare la
memoria» protegge `ultima_data`, non `last_numero`.

⭐ **Il verso opposto ha la stessa forma**: da `NESSUNA` ad `ANNUALE` il secchio
dell'anno corrente non esiste e riparte da 1, sopra i numeri appena emessi.

#### ⛔ Il precedente è in casa, ed è a due changeSet di distanza

`prefisso`, `suffisso` e `lunghezza_numero` **non si cambiano** su un registro
che ha già numerato: lo rifiuta `trg_registri_fatturazione_a10_guard_forma_numero_upd`
(`20260901-03`), e la ragione registrata in `E_REGISTRO_FORMA_NON_MODIFICABILE`
dice, parola per parola, *«il contatore non riparte quando cambia la forma,
prosegue — quindi sullo stesso sezionale convivrebbero due forme con numeri
consecutivi»*. ⇒ `reset_policy` è **della stessa specie**: cambia il modo in cui
i numeri nascono su un registro che ne ha già prodotti.

✅ **Decisione di Tid, 2026-09-08: si ripara il MECCANISMO, non si vieta il
cambio** — *«i dati nel db li modifico io, tu predisponi per far funzionare una
policy NESSUNA»*. ⭐ E la regola di casa dice la stessa cosa: davanti a un blocco
su stato persistente la domanda è *«com'è lo stato DOPO l'azione che il guard
impedirebbe?»*. Qui è **recuperabile** — basta innescare il secchio — quindi il
cancello toglierebbe una configurazione legittima invece di impedire un autogol.
Sulla forma del numero è l'opposto, ed è per questo che lì il guard è giusto.

⛔ **Le due cose che Tid chiedeva erano però già fatte, ed è la parte da non
rifare**: il `CHECK` accetta `NESSUNA` dal `20260901-06`, e
`fn_get_next_progressivo` ramifica già sulla politica (`20260901-07`). Mancava
solo il **passaggio**.

### La cura — `20260908-10`, ✅ APPLICATA il 2026-09-08

> `20_code/vendite/20260908-10-update-fn-get-next-progressivo-seme-secchio-nuovo`

**Un secchio appena nato non parte più da zero: parte dal massimo di quelli con
cui i suoi documenti possono COLLIDERE.**

```text
secchio continuo (anno = 0)  → attraversa tutti gli anni  ⇒ max su TUTTI i secchi
secchio d'anno   (anno = Y)  → solo il continuo, se c'è   ⇒ max su quello
```

⛔ **Il criterio NON è «il massimo di sempre»**, e la differenza è tutto: sotto
`ANNUALE` il primo documento dell'anno **deve** ripartire da 1. Un secchio d'anno
guarda il solo secchio continuo, mai gli altri anni.

⭐ **Copre i due versi** del passaggio, e gira già sotto il lock giusto: la chiave
dell'advisory lock non porta l'anno — scelta fatta a suo tempo perché il cancello
di monotonia legge attraverso gli anni — quindi il massimo si legge serializzato.

⚠️ **Raggio d'azione oggi: nessuno.** Il ramo si accende solo dove un secchio
continuo convive con uno d'anno, cioè solo dove una politica è cambiata. Ovunque
altro il massimo è su zero righe, il `COALESCE` rende 0, e il comportamento è
identico a prima riga per riga.

#### ⭐ La commessa diventa standard — decisione di Tid, 2026-09-08

> *«Commessa deve diventare standard, tutti devono avere gli stessi parametri:
> si toglie l'anno interno e lo passa la variabile.»*

La prima stesura dichiarava `COMMESSA → false` con questa motivazione: *«l'anno
nel suo codice ce lo mette il compositore di dominio, dichiararlo qui lo
scriverebbe due volte»*. ⛔ **Vera come meccanismo, e sbagliata come modello**:
quella colonna dice *«il numero di questa famiglia porta l'anno»*, e sulla
commessa la risposta è **sì**. Dire `false` significava **mentire sul contenuto
della stringa** per descrivere chi la compone — cioè tenere in piedi la seconda
sorgente di verità invece di toglierla.

⇒ `fn_get_or_create_commessa` passa ora solo `p_corpo => sigla || '-'`, l'anno lo
aggiunge il compositore generico, e la famiglia dichiara `true` come le altre
tre.

⭐⭐ **E la posizione dell'anno è diventata un fatto misurato, non una
preferenza.** In coda al corpo la stringa esce **identica byte per byte** —
`CMM-PGTAPEF202-2026-000000006`, verificato ricomponendo i codici esistenti;
davanti al corpo sarebbe diventata `CMM-2026-PGTAPEF202-…`, cioè una forma nuova
accanto alla vecchia sullo stesso registro. *Il corpo dice CHI, l'anno dice
QUANDO, il progressivo chiude.*

⛔ **Due conseguenze che il piano non aveva**, ed entrambe sono ordini di
esecuzione:

1. **Le due funzioni stanno nello STESSO changeSet.** Fra il momento in cui il
   generico comincia a scrivere l'anno e quello in cui la commessa smette ci
   sarebbe una finestra con l'anno **doppio** — `CMM-SIGLA-2026-2026-000000001`.
   Due changeSet separati sono due transazioni, e quella finestra sarebbe reale.
2. **I registri COMMESSA esistenti vanno portati a `true` nel `20260908-12`**,
   cioè con la colonna e **prima** che il guard della forma la impari
   (`20260908-15`). ⚠️ Non è un aggiramento del presidio: è il passo che porta lo
   stato dove il presidio lo vuole, prima che il presidio ci sia — dopo, la
   colonna è bloccata per tutti, commessa compresa. ⛔ E senza quel backfill la
   prossima commessa uscirebbe **senza** l'anno, perché il compositore di dominio
   ha smesso e il registro non lo chiede: la forma cambierebbe in silenzio, che è
   il difetto peggiore di tutto questo §11.8.

#### Come è stato provato

L'SQL **estratto dal changeSet** (non riscritto a mano) eseguito in transazione
annullata, e sopra i casi:

| caso | prima | dopo |
| --- | ---: | ---: |
| `ANNUALE`, due numeri nel 2126 | 1, 2 | 1, 2 |
| passo a `NESSUNA`, chiedo un numero | ⛔ **1** | ✅ **3** |
| `NESSUNA` attraversa l'anno | — | 4 |
| torno ad `ANNUALE` l'anno dopo | ⛔ **1** | ✅ **5** |
| ⭐ **controllo**: nessun cambio di politica, 1° gennaio | 1 | ✅ **1** |

pgTAP: `db/pgtap/vendite/test-secchio-nuovo-seme-v1.sql`, **5/5 verde** contro la
funzione del changeSet.
⭐ **E provato per mutazione**: contro la funzione di oggi diventa **rosso su 3**
(`have: 1, want: 3`), mentre i test 4 e 5 restano verdi in entrambi i mondi.
⛔ **Il test 4 è quello che tiene in piedi gli altri tre**: il criterio sbagliato
— «parti sempre dal massimo» — passerebbe 1, 2 e 3 esattamente come quello
giusto, e spegnerebbe l'azzeramento annuale su **tutti** i registri senza che
niente diventi rosso. Sarebbe invisibile fino al 1° gennaio.

✅ **Applicato da Tid il 2026-09-08** (`EXECUTED` sul `databasechangelog`), e il
pgTAP rilanciato contro la funzione viva è **5/5 verde**. ⇒ Il passaggio di
politica non pianta più nessun numeratore, nei due versi.

#### 📌 Cosa resta, e non è DB

⚠️ **«In futuro per i nuovi numeratori si deve poter scegliere la reset policy»**
(Tid, 2026-09-08): lato database **c'è già tutto** — colonna, `CHECK` a due
valori, funzione che ramifica. Manca la strada per sceglierla:

| # | Chi | Cosa |
| --- | --- | --- |
| BE-R1 | backend | `reset_policy` in `_CAMPI_CREATE` (⛔ **non** in update: lì il valore si cambia su un registro che può aver già numerato, ed è il caso di questo §11.7) |
| FE-R1 | frontend | il campo in maschera alla creazione, due voci |
| BE-L1 | backend | togliere la riga che dice ancora *«inchiodata ad ANNUALE dal CHECK»* (§11.5) |

⭐ Con BE-R1 il valore si sceglie **alla nascita**, che è il momento in cui non
c'è nessun secchio da innescare — e il §11.7 diventa la rete, non la strada
principale.

---

### 11.8 ✅ L'invariante del §1 ha un TERZO piano: il numero che si LEGGE

> Osservazione di Tid, 2026-09-08: *«i numeratori, per esempio ordini, pur avendo
> ANNUALE non mettono l'anno nella numerazione esposta. Esempio ORD0036007
> creato ieri. Credo sia giusto che, se si sceglie il reset annuale, sia
> obbligatorio esporre l'anno nel numero.»*

⭐ **È il §1, un piano più su.** Là: *tutto ciò che discrimina il CONTATORE deve
poter discriminare anche il DOCUMENTO*. Qui: **…e anche la stringa che una
persona legge**. Il contatore discrimina su `anno`; `ORD0036007` no. Al primo
gennaio il contatore riparte e quella stringa **torna**: due ordini diversi, lo
stesso numero scritto sopra. ⛔ Il database non se ne accorge — `uq_ordini_v_anno_serie_numero`
porta l'anno, quindi l'`INSERT` passa. È un'ambiguità **muta**, che vive fuori
dal database: liste, ricerche, la telefonata in cui un cliente cita un numero.

#### Il fatto, verificato il 2026-09-08

```text
vendite.fn_componi_numero_documento(prefisso, CORPO, progressivo, lunghezza, suffisso)

trgfn_ordini_gen_numero      p_corpo => NULL   ⇒ ORD + 0036007          ⛔ senza anno
trgfn_ddt_gen_numero_emesso  p_corpo => NULL   ⇒ DDT + 0023455          ⛔ senza anno
trgfn_resi_gen_numero        p_corpo => NULL   ⇒ RESO + 0012132         ⛔ senza anno
fn_get_or_create_commessa    p_corpo => sigla || '-' || anno || '-'     ✅ CMM-<sigla>-<anno>-<9>
FATTURA                      non passa di qui  ⇒ numero = 101, anno e serie in COLONNA
```

> ⭐ **E la commessa è diventata standard il 2026-09-08**, per decisione di
> Tid: *«tutti devono avere gli stessi parametri»*. Vedi in fondo — l'anno se
> lo metteva **da sé**, ed era una seconda sorgente di verità per la stessa
> cosa.

⭐ **Lo slot c'è già, e uno lo usa**: `p_corpo` è il posto dell'anno, e la
commessa ci mette sigla e anno da sempre. Esporre l'anno non è un meccanismo da
inventare — è un argomento da passare.

#### ⚠️ Ma la regola non si scrive come un CHECK secco, e il motivo è la FATTURA

«`ANNUALE` ⇒ l'anno sta nel numero» preso alla lettera colpirebbe i **6 registri
FATTURA**, che sono anche gli unici che resteranno `ANNUALE`: lì il `numero` è il
progressivo **nudo** (`101`), l'anno e la serie viaggiano in **colonna**, e la
stampa li ricompone — `template-ddt-vendita.html` rende già
`N. {{ numero }} / Serie {{ serie }} / {{ anno }}`. È la convenzione fiscale, ed
è giusta: mettere l'anno dentro la stringa cambierebbe il numero di una fattura.

⇒ **Il soggetto dell'invariante è «il numero come lo si legge», e l'anno può
stare in due posti diversi a seconda della famiglia.** È esattamente la forma del
§5: *sulla FAMIGLIA si dichiara ciò che il documento PUÒ esprimere, sul REGISTRO
si sceglie ciò che quel sezionale FA* — come `colonna_serie`. La dichiarazione
naturale è **dove sta l'anno**: dentro la stringa, oppure in colonna.

#### ⚠️ Due conseguenze da tenere in conto prima di aprirlo

1. ⛔ **L'anno nel numero è FORMA DEL NUMERO**, quindi ricade sotto
   `trg_registri_fatturazione_a10_guard_forma_numero_upd`: su un registro che ha
   già consegnato numeri **non si può aggiungere**. ⇒ È una scelta che si fa
   **alla nascita**, come prefisso e lunghezza — e va nella maschera di
   creazione insieme a `reset_policy` (BE-R1/FE-R1 del §11.7).
2. ⭐ **Sui registri di oggi il problema si chiude da solo con il passaggio a
   `NESSUNA`** (decisione di Tid, stessa giornata): un progressivo che non
   riparte non si ripete, e la stringa resta unica senza l'anno. Restano
   `ANNUALE` le sole fatture, che l'anno lo espongono in colonna.
   ⇒ **Non c'è niente che bruci**; il cancello serve a impedire che nasca
   *domani* un registro `ANNUALE` con un numero senza anno.

#### ✅ Cosa è stato scritto — `20260908-11..16`, **applicati il 2026-09-08**

| # | Cosa | Dove |
| --- | --- | --- |
| A-1 | `famiglie_documento.anno_nel_numero_default` — il **default del tipo documento** | `00_schema/vendite/20260908-11` |
| A-2 | `registri_fatturazione.anno_nel_numero` — l'**effettivo del sezionale** | `00_schema/vendite/20260908-12` |
| A-3 | `fn_assegna_numero_documento` mette l'anno **in coda al corpo** — e nello stesso changeSet `fn_get_or_create_commessa` smette di mettercelo da sé | `20_code/vendite/20260908-13` |
| A-4 | il **risolutore** in INSERT: `ANNUALE` + famiglia che espone ⇒ nasce con l'anno | `20_code/vendite/20260908-14` |
| A-5 | il guard della forma impara la **quarta colonna** | `20_code/vendite/20260908-15` |
| A-6 | il seed dei cinque default — **quattro `true`**, la sola fattura `false` | `80_data/20260908-16` + CSV dedicato |
| P | `db/pgtap/vendite/test-anno-nel-numero-v1.sql` — 7 test | `db/pgtap/vendite` |

⭐ **La coppia è quella già in casa**: `prefisso_default`/`prefisso`. Il tipo
documento decide, il sezionale eredita alla nascita, e da lì il valore è suo.

#### ⛔ Il grep dei pgTAP ha cambiato il progetto — e questo è il punto

La prima stesura era un **guard che rifiuta**: `ANNUALE` + famiglia che espone +
colonna a `false` ⇒ rifiuto, con codice errore e `fn_check_*` per la maschera.
È stato scartato **prima di scriverlo**, per due misure:

* **sei** file pgTAP creano registri `DDT`/`ORDINE`/`RESO` `ANNUALE` senza
  nominare la colonna nuova — sarebbero diventati rossi tutti insieme;
* il backend crea i registri con una whitelist di colonne che quella nuova non
  la contiene: **ogni creazione dall'app sarebbe stata rifiutata** finché il BE
  non fosse stato adeguato.

⛔ *Un cancello che spegne sei test e una maschera viene disattivato, e un
presidio spento è peggio di uno assente.*
⭐ **E c'era di meglio**: se non esiste un caso legittimo di «ANNUALE senza
anno» per quelle famiglie, allora non è una scelta da difendere — è un valore da
**derivare**. Il risolutore fa valere l'invariante *per costruzione* invece che
per rifiuto, non chiede niente a nessuno, e non rompe una riga.
⚠️ **E non è il difetto di `config.sistema_codici`** (§5.3, «si rifiuta, non si
ignora»): là un campo cambiava senza ottenere niente; qui il valore viene
risolto e **diventa effettivo** — la stringa del numero cambia davvero.

#### ⛔ E allargare `UPDATE OF` non bastava, l'ha trovato il test 7

Il guard della forma comincia con un confronto sui **valori** — il no-op che
lascia passare un `UPDATE` che nomina una colonna senza cambiarla. Quel
confronto guardava le **tre** colonne storiche: allargata la sola clausola
`UPDATE OF`, un cambio della quarta arrivava al guard, trovava «nessuna delle
tre è cambiata» e **passava**. Il rifiuto non scattava, e non falliva niente.
⇒ Si riscrivono **entrambi**, la funzione e il trigger. ⭐ L'ha trovato la prova
d'insieme, non un ragionamento: a leggerlo, allargare il trigger sembrava fatto.

#### Come è stato provato

L'SQL **estratto** dai cinque changeSet nell'ordine di numerazione, più il seed
applicato come lo applica il loader, poi **dieci** file pgTAP nella stessa
transazione annullata — il nuovo, quello del §11.7, i **sei preesistenti** che
creano registri e i **due presidi della commessa**
(`test-commessa-chiave-numerazione-v1`, che confronta il codice con gli assi
dichiarati, e `test-documenti-numerazione-trasloco-v1`, che ne verifica forma e
sigla). **73 asserzioni, zero rosse.**

⚠️ **Cosa è cambiato all'apply: niente, su niente.** La colonna del registro
nasce `false`, il risolutore lavora solo in `INSERT`, e i registri di allora non
sono stati toccati — i loro numeri restano identici. Cambia ciò che **nasce
dopo**.
⭐ **I due registri COMMESSA sono l'unica eccezione, e per RESTARE come sono**:
il backfill li porta a `true` perché la stringa che consegnano non cambi quando
l'anno passa di mano.

#### ✅ Verificato dopo l'apply — 2026-09-08

I sette changeSet risultano `EXECUTED` sul `databasechangelog`, i **dieci** file
pgTAP girano verdi **contro il database vero** (non più in transazione
simulata), e lo stato è quello voluto:

| | |
| --- | --- |
| default delle famiglie | `FATTURA=f`, le altre quattro `t` |
| registri non fiscali | portati a **`NESSUNA`** da Tid — 8 su 14 |
| registri `FATTURA` | restano `ANNUALE`, senza anno nella stringa (ce l'hanno in colonna) |
| `anno_nel_numero` acceso | **solo i due COMMESSA**, per conservare la forma del loro codice |

⭐ **E la lettura di oggi vale la riga**: con i non fiscali a `NESSUNA`, in questo
momento **nessun sezionale è `ANNUALE` senza l'anno** — non perché il meccanismo
sia intervenuto, ma perché la politica ha tolto l'ambiguità alla radice. Il
meccanismo del §11.8 è la rete per il sezionale `ANNUALE` che nascerà domani.
⚠️ È un **fatto datato**, non una prova che serva o non serva: la regola sta sul
modello.

⭐ **E i registri di oggi si sistemano da soli con la mossa che stai già
facendo**: portati a `NESSUNA`, il progressivo non riparte e la stringa non si
ripete. L'anno nel numero serve ai sezionali che l'azzeramento lo tengono.

#### 📌 Cosa resta al BE, e non è bloccante

`anno_nel_numero` non è nella whitelist di creazione del backend: un registro
creato dall'app prende comunque il valore giusto — **lo mette il risolutore** —
ma la maschera non lo mostra. Mostrarlo in sola lettura accanto a prefisso e
lunghezza è il completamento naturale, insieme a BE-R1/FE-R1 del §11.7.

---

### 11.9 ✅ Il pavimento guarda la SEQUENZA, non il registro — decisione dell'8 settembre

> **Origine:** segnalazione del BE, riportata da Tid il 2026-09-08. *«Sulla serie
> non c'è nessun controllo: `prefisso`, `suffisso` e `lunghezza` li protegge un
> trigger, `serie_default` solo una lista in Python. Chi allarga quella lista, o
> aggiunge un endpoint, o scrive un UPDATE in psql, passa senza che niente lo
> fermi.»*

**Il fatto è esatto**, la conclusione no — e distinguerli è tutto il valore di
questo paragrafo.

#### ⛔ Perché `serie_default` NON si congela come la forma

L'analogia con `prefisso`/`suffisso`/`lunghezza` non regge, e la differenza è
strutturale:

| | cosa cambia | esito |
| --- | --- | --- |
| **forma del numero** | la stringa **dentro la stessa sequenza** — il contatore non riparte | due forme con numeri **consecutivi**, indistinguibili ⇒ si congela |
| **`serie_default`** | apre una **sequenza nuova**, che riparte da 1 | niente collide, e i due numeri restano distinguibili ⇒ non si congela |

Tre fatti la reggono, tutti verificati il 2026-09-08:

1. **la serie non entra nella stringa** — la fattura è `numero = 101` con
   `serie = VX1` in colonna: cambiarla non crea due forme sullo stesso numero;
2. **la serie sta nella chiave di unicità del documento** —
   `uq_fatture_numero (registro_id, anno, COALESCE(serie,''), numero)`, e uguale
   su DDT e ordini: una serie nuova che riparte da 1 non collide con niente. È
   l'asimmetria del §1 **nel verso innocuo**, quello in cui il documento porta
   l'asse;
3. **su resi e commesse non c'è nessun "dopo" da proteggere**: il guard del §5
   vieta di avere una serie del tutto.

⇒ Congelarla vieterebbe un'operazione legittima — spostare un sezionale su una
serie nuova. ⚠️ E il motivo scritto in `registri_repository.py`
(*«`serie_default` fuori dall'update perché il guard non la copre»*) è giusto
nella conclusione e **sbagliato nella ragione**: non manca un presidio, non
serve. 📌 Riga in `backend/`, fuori perimetro DB: segnalata, non toccata.

#### ⭐⭐ La raccomandazione sbagliata, e il controesempio che l'ha ribaltata

La domanda aveva però trovato qualcosa: **il pavimento di monotonia è per
`(registro, serie)`** — `fn_get_pavimento_sequenza` fa
`max(ultima_data) … AND rp.serie = v_serie`, e la serie la risolve da
`serie_default`. Quindi una serie nuova nasce **senza pavimento**.

⛔ **Avevo raccomandato di togliere quel filtro**, appoggiandomi a *«un sezionale
è un registro, la serie è solo l'etichetta che stampa»*. **Il modello dice il
contrario**, e due misure lo hanno smentito prima che scrivessi una riga:

* il registro **Front-office emette già su DUE serie**, `VX2` e `R2`;
* `trgfn_ddt_gen_numero_emesso` e `trgfn_ordini_gen_numero` passano
  `p_serie => NEW.serie`: **un documento può portare una serie propria**, diversa
  dal default del registro.

⇒ Due sequenze parallele sullo stesso registro sono **previste dal modello**. Col
pavimento per registro si bloccherebbero a vicenda sulle date — emetti su `VX2`
il 20 settembre e `R2`, che sta più indietro perché è un'altra sequenza, non
numera più. Sarebbe un difetto nuovo, peggiore di quello da chiudere.

⭐ **E la conferma era già in casa**: il test 11 di `test-registri-progressivi`
asserisce dal 2026-08-25 *«due serie sullo stesso registro non si bloccano a
vicenda»*. Era una decisione **deliberata**, e la raccomandazione l'avrebbe
rovesciata senza accorgersene.

⇒ **Il filtro resta.** Il pavimento risponde a «questa **sequenza** va avanti?»,
e la sequenza è `(registro, serie)`.

#### ✅ E il timore di partenza è già coperto — da un altro cancello

*«Cambio la serie e riapro il passato»* non è un varco del pavimento: cambiare
`serie_default` **apre una sequenza nuova**, e una sequenza nuova non ha passato.
Contro la retrodatazione vera c'è il **limite di emissione**
(`fn_get_pavimento_emissione`), che guarda **registro + competenza**, non la
serie, e che una serie nuova **non azzera** — il risultato è il `GREATEST` dei
due pavimenti.

⚠️ **Misurato**: il pavimento di sequenza si applica alla sola `FATTURA`
(`presidia_data_documento = t`; le altre quattro famiglie sono `f`), ed è proprio
lì che il limite di emissione regge. ⇒ Il presidio contro la retrodatazione
c'è, ed è quello costruito per quella domanda.

⭐ **La lezione, e vale oltre questo caso**: due cancelli che *sembrano*
rispondere alla stessa domanda vanno letti sul **perimetro**, non sul nome. Uno
guarda la sequenza, l'altro il registro — e chi li confonde toglie quello
sbagliato.

📖 **Scritto anche nella guida**, dove si cerca senza sapere che esiste un brief:
[numerazione-documenti-e-codici §6.3](../../guide/numerazione-documenti-e-codici.md).

