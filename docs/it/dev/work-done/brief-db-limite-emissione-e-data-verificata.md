# Brief DB — il limite di emissione, e il documento che nasce già conforme

> **Destinatario:** team DB (`dev/db-tid`). BE e FE **attendono** i prerequisiti
> ([[feedback_be_fe_attende_prerequisiti_db]]).
>
> **Origine.** Tid, 2026-08-26, dopo tre giorni sul cantiere della numerazione e
> un caso reale: un lotto di competenza **luglio** generato il **25 agosto**
> nasceva con un documento datato **31/07**, cioè con una data che non è più
> trasmissibile.
>
> ⭐ **La motivazione, con le sue parole**, ed è la migliore che sia emersa:
> *«quando stiamo emettendo il lotto massivo, quello che fattura mese competenza
> + 15, non siamo mai in ritardo, quindi il controllo lo passerebbe. Se la
> commessa rimane ferma e viene generato il lotto si avrebbe comunque
> l'errore.»*
> Il controllo **non serve a chi lavora in ordine**: serve a impedire che una
> commessa dimenticata produca un documento che non si può più mandare.
>
> **Correlati:** [brief-db-numerazione-data-documento-e-sequenza.md](brief-db-numerazione-data-documento-e-sequenza.md)
> (il cantiere che ha reso la data una decisione del registro) ·
> [brief-db-registro-e-data-prevista-in-competenza.md](brief-db-registro-e-data-prevista-in-competenza.md)
>
> ✅ **CANTIERE DB CHIUSO il 2026-08-26.** Decisioni chiuse (§12), 13 changeSet
> su 13 **applicati e verificati sul `databasechangelog`**, pgTAP nuovo (19 test)
> e bonifica dei due file che il cantiere faceva diventare rossi, **baseline
> `vendite` verde**, doc concettuale scritta.
> ✅ **BE-1 CHIUSO il 2026-08-26** (ripiego + policy rigenerate, 4073 test BE
> verdi) e **BE-2 riverificato**: il backend non tocca nessuna delle firme
> cambiate. Dettaglio in fondo al §9 e nel registro.
>
> ✅ **COLLAUDO IN-APP SUPERATO il 2026-08-26 (Tid).** Il messaggio nuovo è
> stato provato a video sul lotto `LTF-0007385`, l'unica porta che non dipende
> dai dati: la **data dichiarata a mano** nel dialog di numerazione.
>
> 📦 **CANTIERE CHIUSO E ARCHIVIATO il 2026-08-26.** DOC-1 (il giro di auto-gen
> per le cinque pagine `funzioni/` senza `include-markdown` e il link morto in
> `index.ci.md`) è **rinunciato per decisione di Tid** — *«insignificante»*: non
> resta come debito perché non è stato giudicato tale. Se un giorno il guardrail
> dei riferimenti morti girerà su `dbzero/`, lo troverà insieme ai **4 link
> morti preesistenti** che il §9 già nomina.

---

## 1. La misura che dimostra che il cancello è al posto giusto

Su tutti i lotti esistenti, confrontando **quando il lotto è nato** con il 15 del
mese successivo alla sua competenza:

| | lotti | margine |
| --- | ---: | --- |
| **in termine** | **46** | da 14 a 43 giorni di anticipo |
| oltre il termine | 6 | da 7 a 40 giorni di ritardo |

⭐ **46 su 52, e non per un pelo**: chi è in termine lo è di almeno due
settimane. Il giro differito di luglio gira nella prima metà di agosto, il
documento porta il 31/07, il termine è il 15/08 — passa senza accorgersene.

I 6 fuori termine sono i casi patologici: commesse rimaste ferme, lotti nati
tardi. **È lì, e solo lì, che il cancello si accende.**

---

## 2. Due forme, perché le due politiche SONO i due tipi di fattura

`registri_fatturazione.politica_data_documento` distingue già l'immediata dalla
differita. Il termine di emissione segue la stessa distinzione, quindi **non è
un parametro globale con una forma sola**:

| politica | tipo | limite di emissione | quando morde |
| --- | --- | --- | --- |
| `OGGI` | immediata | `data_operativa − 12` giorni | se si numera un documento datato più di 12 giorni fa |
| `FINE_MESE_COMPETENZA` | differita | **15 del mese successivo** alla competenza | **solo se il lotto nasce tardi** (6 casi su 52) |

⚠️ **Le due forme non si approssimano.** Con la finestra mobile un documento di
luglio resterebbe emettibile all'infinito, scorrendo in avanti; con la scadenza
per competenza dal **16 agosto** la strada è chiusa e l'unica data possibile è
quella di oggi. Scegliere una forma per entrambe sarebbe sbagliato in un verso o
nell'altro.

⛔ **Questo brief NON afferma la norma**: riporta la lettura di Tid
(«12 giorni fra data di emissione e invio»), che è la fonte su questo. Il
software non deve incorporare un'interpretazione fiscale in una costante: la
incorpora in un **parametro**, che è il motivo per cui i valori 12 e 15 stanno
a configurazione e non nel codice.

⛔ **La tabella qui sopra è stata SUPERATA dalla verifica del 2026-08-26**
(▶ §10 V-1 e V-2). La distinzione immediata/differita è giusta e resta; è la
sua traduzione in **due pavimenti indipendenti** che non regge — il limite
della differita è una **scadenza**, non un pavimento, e messa in un `GREATEST`
con la data della politica farebbe nascere *ogni* documento differito datato
il 15 del mese successivo. La forma corretta è **una regola sola con la sua
esenzione**.

---

## 3. Dove agisce: tre punti, tre ruoli diversi

Sono gli stessi tre della data documento, e vanno tenuti distinti.

### 3.1 ⭐ Alla NASCITA: il documento nasce già conforme (decisione di Tid)

> *«il lotto deve nascere con la data giusta, con la data verificata già con le
> regole che stabiliamo, e non con data 31/07 fissa nell'esempio di luglio»*

`fn_calcola_data_documento` smette di restituire il risultato grezzo della
politica e restituisce:

```
GREATEST( data_della_politica , pavimento_effettivo )

pavimento_effettivo = GREATEST( ultima_data_del_sezionale ,
                                limite_di_emissione_del_registro )
```

⛔ **La formula qui sopra è SUPERATA** (▶ §10 V-1 e V-4). Resta perché dice
l'intenzione — «il documento nasce già conforme» — che non cambia. Cambia il
modo: il `GREATEST` col limite di emissione fa nascere il documento
**esattamente sul pavimento**, cioè con margine di trasmissione zero. La forma
eseguibile è un `IF` che riparte da **oggi**, più un `GREATEST` sul solo
pavimento di sequenza. ⚠️ E manca un ingrediente: la **serie** (▶ V-7).

⛔ **Solo sulla data CALCOLATA, MAI su quella DICHIARATA.** Se un operatore
scrive 31/07 nel dialog, quella data si **rifiuta** — non si sposta in silenzio.
Spostare senza dirlo una scelta esplicita è la classe di difetto che il cantiere
della numerazione ha passato tre giorni a togliere: il clamp vale per il default,
il cancello vale per la dichiarazione.

✅ **La data di nascita diventa dipendente dal tempo, ed è ACCETTATO** (Tid,
2026-08-26: *«è giusto che sia così»*). Lo stesso lotto generato oggi e domani
nasce con due date diverse, e un lotto annullato e rigenerato cambia data —
caso non teorico, è successo il 25/08 sul `LTF-0007307`. Oggi non succede: il
31/07 è stabile per costruzione.

⚠️ È scritto qui come **decisione**, non come riserva: chi legge non deve
fermarsi a chiedersi se sia un effetto indesiderato da evitare. È il prezzo di
«nascere conforme», è stato guardato, e si paga volentieri.

### 3.2 La TARGA

`fn_get_data_minima_numerabile[_lotto]` torna il **pavimento effettivo**, non
più il solo pavimento di sequenza: il DatePicker propone una data già ammessa e
l'errore resta l'eccezione.

⚠️ ▶ §10 V-6: per **tre giorni al mese** l'insieme delle date ammesse non è un
intervallo, e una `minDate` è un intervallo per costruzione. La targa mente in
un verso qualunque valore si scelga: si sceglie il più permissivo e lo si
dichiara.

### 3.3 Il CANCELLO

`fn_get_next_progressivo` rifiuta sotto il pavimento effettivo.

⛔ **Con un codice errore SUO**, distinto da quello della sequenza. «Il documento
è più vecchio del limite di emissione» e «la data è anteriore all'ultimo numero
emesso» sono due cose diverse, si rimediano in due modi diversi, e dire la
seconda quando è la prima manda a cercare la cosa sbagliata. Classe
`DATO_ERRATO`, `context.campo = data_documento`, bersaglio sul documento.

⚠️ ▶ §10 V-3: **il cancello non riceve la competenza e non può riceverla**
senza diventare fail-open sotto RLS — `vendite.fatture` non ha una colonna di
competenza, e leggerla dal lotto significa leggere una tabella con le policy da
dentro una funzione `SECURITY INVOKER`. La inferisce **dalla data**, che è
l'informazione su cui l'esenzione differita è davvero definita.

⚠️ **Il clamp non rende superfluo il cancello**, e va scritto perché sembra di
sì: il pavimento di sequenza si muove mentre altri numerano, quindi un documento
nato conforme può diventare non numerabile dopo. Targa, cancello e dialog
restano tutti e tre.

---

## 4. Dove vive il parametro: slot globale + override, senza ripetizioni

Tid: *«sul registro, ma richiede una ripetizione per ogni registro»*. Vero —
quindi **slot + override**, il pattern già in uso nel progetto:

| dove | cosa |
| --- | --- |
| `config.parameters` | i due valori di default: `12` (immediata) e `15` (giorno del mese, differita) |
| `registri_fatturazione` | due colonne **nullable**: `NULL` = vale il default globale |

Si scrive il valore **una volta sola**; un registro con un'esigenza propria la
dichiara, gli altri tacciono.

❓ **Domanda al team DB (D-1): una colonna o due?**
Una sola colonna il cui *significato* dipende da `politica_data_documento`
(giorni se `OGGI`, giorno-del-mese se `FINE_MESE_COMPETENZA`) è compatta ma
ambigua: un `12` letto come giorno del mese è un valore plausibile e sbagliato.
Due colonne distinte sono inequivocabili ma permettono di valorizzare quella che
la politica non legge — un valore **inerte**, che sembra una configurazione e non
lo è.

⭐ Propendo per **due colonne + un CHECK** che ammetta valorizzata solo quella
coerente con la politica: così l'ambiguità non c'è e il valore inerte nemmeno.
Ma la scelta è vostra, è casa vostra.

⭐ **D-1 ha una risposta, ed è diversa da questa** (▶ §10 V-5 e §12 D-1): due
colonne sì, ma il CHECK è **a un lato solo**. Sotto la forma corretta del limite
il valore in **giorni vale anche sulla differita** — a esenzione scaduta il
documento differito ricade sul pavimento mobile come tutti — quindi un CHECK
«solo quella coerente con la politica» vieterebbe una configurazione legittima.

---

## 5. ⭐ L'effetto collaterale che chiude un altro cerchio

Il 2026-08-24 Tid segnalava che un lotto di competenza luglio lavorato ad agosto
**non compariva nella scheda «recuperi del mese»**. Il criterio della scheda è
«competenza precedente **e** documento datato nel mese», e con
`FINE_MESE_COMPETENZA` quel documento porta una data di luglio: fuori per
costruzione.

⭐ **Il clamp del §3.1 lo risolve da solo.** Un lotto in ritardo nasce con una
data di oggi, quindi:

* è trasmissibile, perché la sua data è di oggi;
* **compare nei recuperi del mese**, perché porta la data del mese in cui è
  stato lavorato.

Erano la stessa cosa vista da due lati. **Non serve cambiare il criterio della
scheda** — serve che i documenti in ritardo nascano con la data giusta.

⚠️ Vale per i documenti **futuri**: il clamp non retroagisce. I sei già nati con
date arretrate continueranno a non comparire finché non vengono ri-datati dal
dialog.

---

## 6. Le consegne

⛔ **Superate dal §11**, che è la loro forma eseguibile dopo la verifica del
§10. Restano qui perché dicono l'intenzione riga per riga, e perché il §11 si
legge come una correzione di queste, non al posto loro.

| | Cosa |
| --- | --- |
| **DB-1** | `config.parameters`: i due default (12 giorni immediata, 15 giorno-del-mese differita), con `description` che dice **che cosa** misurano e che sono una lettura configurabile, non una costante di legge |
| **DB-2** | `registri_fatturazione`: le colonne di override nullable + il CHECK di coerenza con la politica (▶ D-1) |
| **DB-3** | `vendite.fn_get_limite_emissione(p_registro_id, p_competenza_mese) RETURNS date` — **una sola sede** per le due forme: legge la politica, sceglie la forma, applica override o default. Nessun chiamante deve sapere quale forma si applica |
| **DB-4** | `fn_calcola_data_documento`: clamp con `GREATEST(politica, pavimento_effettivo)`. ⛔ Solo sul ramo calcolato, mai sulla data dichiarata |
| **DB-5** | `fn_get_data_minima_numerabile[_lotto]`: tornano il pavimento **effettivo** |
| **DB-6** | `fn_get_next_progressivo`: il cancello confronta col pavimento effettivo, con **codice errore nuovo** (§3.3) + ripiego senza `%s` + policy rigenerate |
| **DB-7** | pgTAP: il flusso normale **passa** (lotto di luglio nato il 5 agosto → 31/07, nessun rifiuto); il lotto tardivo **nasce con la data di oggi**; una data dichiarata sotto il limite viene **rifiutata** e non spostata; le due forme danno due risultati diversi sullo stesso caso; il pavimento effettivo è il massimo dei due |

---

## 7. ⛔ Ordine di accensione, e i documenti già in coda

Come per il cancello sulla sequenza: acceso sui dati di oggi, il limite blocca
lavoro legittimo. Misurato il 2026-08-26 sui sei documenti `EMESSA` da numerare:

| lotto | data doc | giorni indietro | già fermo per la sequenza? | lo blocca il limite? |
| --- | --- | ---: | --- | --- |
| LTF-0000680 | 31/07 | 26 | no (sezionale senza pavimento) | **sì** |
| LTF-0000579 | 31/07 | 26 | sì | — |
| LTF-0001225 | 02/08 | 24 | sì | — |
| LTF-0001296 | 03/08 | 23 | sì | — |
| LTF-0006585 | 23/08 | 3 | sì | — |
| LTF-0006929 | 24/08 | 2 | no | no, passa |

⭐ **Uno solo in più** rispetto a quelli già fermi. È il momento buono per
accendere: fra un mese sarebbero di più, e ognuno andrà ri-datato a mano dal
dialog.

---

## 8. Cosa NON è in questo cantiere

* **Il criterio della scheda «recuperi del mese»**: lo risolve il clamp (§5), non
  si tocca.
* **Un limite SUPERIORE alla data** (documenti datati nel futuro): con
  `FINE_MESE_COMPETENZA` una fattura di competenza corrente nasce datata a fine
  mese, cioè in avanti, ed è il comportamento voluto. Nominato per non
  riscoprirlo come difetto.
* **La trasmissione allo SDI** e i suoi termini reali: qui si presidia la **data
  del documento**, non l'invio. Se un giorno il sistema trasmetterà davvero, il
  termine andrà misurato su quel momento e non su questo.

---

## 9. Registro

### 2026-08-26 · Analisi, misure e decisioni

Nato dalla discussione sul caso `LTF-0007307`. Misurato: 46 lotti su 52 nascono
in termine con almeno due settimane di margine, quindi il cancello non tocca il
flusso normale. Decise da Tid: **clamp alla nascita** sulla data calcolata, forma
del limite **per politica** (12 giorni l'immediata, 15 del mese successivo la
differita), parametro globale con override sul registro, e **la data di nascita
dipendente dal tempo accettata esplicitamente**. Resta la sola D-1, di
struttura, al team DB.

### 2026-08-26 · Verifica tecnica e piano di sviluppo (team DB)

Rilette le definizioni vive dalla doc auto-gen (non dagli YAML), i sette pgTAP
che attraversano la numerazione e i tre punti del backend che chiamano queste
funzioni. **Quattordici rilievi** (§10), di cui quattro portanti:

* la forma del limite differito nel §2 **rompe il flusso normale** — una scadenza
  e un pavimento non stanno nello stesso `GREATEST` (V-1), e la forma che
  riproduce la tabella del §7 è **una regola con la sua esenzione** (V-2);
* il **cancello non ha la competenza** e non può averla senza diventare
  fail-open sotto RLS: la inferisce dalla data, e nessuna firma cambia (V-3);
* il clamp deve atterrare su **oggi**, non sul pavimento, o il documento nasce
  con margine zero (V-4);
* acceso così, il cancello **fa diventare rosso un pgTAP verde**, con date
  letterali che non si possono togliere (V-11).

Scritti il **piano di sviluppo** (§11: 12 consegne, 5 lotti, 10 file con i nomi,
la lista di verifica) e **sette domande aperte** (§12), tutte con una proposta.
⛔ Nessun file di migrazione scritto, nessuna migrazione eseguita.

### 2026-08-26 · Primo giro di decisioni (Tid)

Chiuse quattro domande su otto.

* **D-1** ✅ due colonne, CHECK a un lato solo — e con essa la premessa: **il
  limite in giorni vale anche sulla differita**, a permesso scaduto.
* **D-5** ✅ CSV nuovo `parameters_fatturazione.csv`, con i due codici per esteso.
* **D-6** ✅ ⛔ **niente tetto a 28**: il giorno del mese si calcola **sul mese**
  (`LEAST(primo + giorno − 1, ultimo del mese)`), CHECK `1..31`, e il `COMMENT`
  della colonna lo dice. Il `LEAST` sta nella funzione, non nel vincolo.
* **D-8** ✅ (nuova) la firma di `fn_calcola_data_documento` si disegna **per
  entrambi i cantieri in una volta sola**: *«il problema non è la rottura, la
  modifica deve essere fatta tenendo conto di entrambe le esigenze»*. `p_serie`
  **senza `DEFAULT`**, così nessun chiamante può dimenticarla.

Restano **D-2, D-3, D-4, D-7**, riscritte in §12 con un esempio concreto
ciascuna: sono le quattro che cambiano ciò che l'operatore **vede**, non ciò che
il codice fa. ⚠️ L'ok a D-1 **inclina già D-2** verso `oggi − giorni`.

Riformulata anche la §10 V-2 secondo la regola nuova di AGENTS.md («le misure sul
DB non progettano»): l'argomento che decide è il **contratto** dichiarato in DB-7,
non la tabella del §7 — che resta come colore, e togliendola l'argomento regge
identico.

### 2026-08-26 · Secondo giro di decisioni (Tid) — tutte chiuse, e ne nasce una

* **D-2** ✅ **B**: a permesso scaduto la differita ricade sulla regola generale
  (`oggi − giorni`), non su una più severa.
* **D-3** ✅ **sì**: il documento nasce datato 31/08, *«come accade ora a video»* —
  la regola che il dialog applica a chi sceglie a mano vale anche per chi nasce.
* **D-4** ✅ **si mostra sempre la data limite**; se dietro c'è un documento
  raggiungibile si dice che **proviene dall'ultima fattura emessa** (col pulsante
  che la apre), altrimenti solo il limite. ⭐ Il pareggio non ha più bisogno di
  una regola: il discriminante è **se c'è un documento**, non quale pavimento è
  più alto.
* **D-7** ✅ **si accetta** la deduzione del mese dalla data, e si scrive nei due
  `COMMENT`.

⛔ **La correzione tecnica che discende da D-4, e che vale più della scelta della
frase**: oggi `fn_get_next_progressivo` mette nel messaggio il **pavimento di
sequenza**. Con due pavimenti deve nominare quello **effettivo**, o dice
all'operatore di scegliere una data che verrà **rifiutata di nuovo**. ▶ DB-10.
Di riflesso, `fn_get_data_minima_numerabile_lotto` smette di essere un
`max(ultima_data)` e compone **per fattura**. ▶ DB-8.

❓ **Nasce D-9**, dall'obiezione di Tid (*«chi scrive a DB dovrebbe poter
modificare solo documenti non numerati»*). Verificato: **quel cancello c'è già**
— `trg_fatture_a10_guard_data_numerata_upd`, dal 2026-08-25, discriminante
`OLD.numero` e non lo stato, e vale anche da `psql`. Il residuo riguarda quindi i
soli documenti **non numerati**, e non lo chiude nessun trigger: la strada pulita
è **portare la competenza sulla riga della fattura**. Proposta del team DB: farlo
qui, nel lotto A, perché le due funzioni che la userebbero sono già da riscrivere.

### 2026-08-26 · D-9 accolta — la competenza passa sulla riga della fattura

⭐ **Ultima domanda chiusa: il piano è completo.** `vendite.fatture.competenza_mese`
(nullable) entra nel **lotto A**, con backfill `MIN(competenza_mese)` da
`fatturazione_lotti_fatture` — il modello ammette una fattura in due lotti e la
più vecchia è la più severa.

Effetto sul piano: **due consegne nuove** (DB-13 colonna+backfill, DB-14
`fn_assign_numero_fattura` che passa la competenza), **tre modificate** (DB-7
scrive la colonna, DB-8 compone con `COALESCE(f.competenza_mese, fl.competenza_mese)`,
DB-10 riceve `p_competenza_mese` obbligatorio in terza posizione). I file passano
da 10 a 13, e il lotto D acquista una seconda coppia inseparabile — `DROP` +
`CREATE` sul cancello e il suo unico chiamante.

⭐ **Costa poco perché arriva adesso**: `fn_assign_numero_fattura` legge già la
riga della fattura (una colonna in più in una `SELECT` che c'è), e
`fn_get_or_create_fattura_header` ha già la competenza in mano per calcolare la
data. Farlo dopo avrebbe voluto dire riaprire tre funzioni per tre righe.

⚠️ **BE e FE non si toccano**, verificato: il backend numera passando da
`fn_numera_fattura_opz_emessa`, la cui firma non cambia; le due firme che cambiano
(`fn_get_next_progressivo`, `fn_calcola_data_documento`) restano interne al
database o toccano il solo cantiere gemello.

⚠️ **Un pgTAP in più da sanare**: `test-registri-progressivi.sql` chiama il
cancello per **nome di parametro**, quindi con `p_competenza_mese` obbligatorio
quelle chiamate non risolvono più.

### 2026-08-26 · Scritti tutti i file · migrate fermo sul 09 (precondition), corretto

**Scritti:** 13 changeSet (`20260826-01..13`), il CSV `parameters_fatturazione.csv`,
l'append del codice errore `E_FATTURA_DATA_OLTRE_LIMITE_EMISSIONE` ai due CSV di
catalogo (id **991**), il pgTAP nuovo `test-limite-emissione-v1.sql` (19 test) e
la bonifica dei due file che il cantiere faceva diventare rossi.
Verdi: `guardrail_sql_letterali`, `guardrail_run_on_change`,
`guardrail_pgtap_preambolo`, il grep di §6c, e il parse YAML di tutti e 13.

**Due cose nate scrivendo, che il piano non aveva previsto:**

* ⭐ `fn_get_data_minima_numerabile` si **rinomina** `fn_get_pavimento_sequenza`
  (▶ §11.1 DB-8). Da quando i pavimenti sono due, «data minima numerabile» e' il
  nome della **composizione**: lasciarlo su una primitiva sarebbe stato un nome
  che mente accanto alla funzione che quel nome merita. Zero chiamanti,
  verificato — il rename non rompe niente. ⛔ La sorella `_lotto` **non** si
  rinomina: quella e' un contratto col backend.
* ⭐ Nasce `fn_get_pavimento_lotto(lotto) RETURNS TABLE(pavimento, origine)`, e
  `fn_get_data_minima_numerabile_lotto` diventa una **lettura sottile** su di
  essa. Serviva perche' la porta di dichiarazione ha bisogno anche dell'`origine`
  per scegliere fra i due codici, ma la firma della seconda e' la `minDate` del
  dialog: cambiarla avrebbe fatto pagare a tutti il bisogno di uno.

⛔ **E una correzione a D-8, che si e' vista solo scrivendo il `CREATE`:**
`p_serie` **non puo' stare in coda** senza `DEFAULT` — in PostgreSQL i parametri
con default stanno per ultimi. Sta in **terza** posizione, prima di
`p_data_dichiarata`. Non e' sintassi: cambia l'ordine posizionale, quindi ogni
chiamata.

#### ⛔ Il migrate si e' fermato sul 09, e la causa era una PRECONDITION

`SQL Precondition failed. Expected '1' got '0'`. Il changeSet 09 chiedeva
«la firma nuova di `fn_calcola_data_documento` c'e' gia'?» confrontando

```sql
pg_get_function_identity_arguments(p.oid) = 'bigint, date, character varying, date'
```

⚠️ **`pg_get_function_identity_arguments()` restituisce anche i NOMI dei
parametri**, non i soli tipi:
`p_registro_id bigint, p_competenza_mese date, p_serie character varying, p_data_dichiarata date`.
Il confronto non combaciava mai. Corretto in 09 e 13 con `p.pronargs = 4` (e `= 5`
sul cancello): la domanda vera e' «il changeSet precedente e' gia' passato?», e a
quella il numero di argomenti risponde senza dipendere da come PostgreSQL rende
una firma.

⭐ **Il difetto era nel PRESIDIO, non nella regola** — ed e' il verso buono in cui
sbagliare: la precondition ha fatto esattamente il suo mestiere, fermare il
migrate prima di scrivere qualcosa di incoerente.

**Stato del database dopo il tentativo** (letto da `databasechangelog`, non dal
brief): applicati **01, 02, 05, 06, 07, 08**. Restano 09, 10, 11, 12, 13 e i due
di `80_data` (03 il seed dei parametri, 04 il backfill).

⛔ **Finestra aperta, ed e' esattamente quella nominata in §11.2 lotto C**: `08`
ha droppato e ricreato `fn_calcola_data_documento` con la firma nuova e `09`, che
la chiama, non e' passato — **la generazione di una bozza adesso non risolve la
funzione**. E `fn_get_pavimento_emissione` solleva `E_CONFIG_MANCANTE` finche'
non gira `80_data`, che sta in coda al migrate.
⇒ **Basta rilanciare il migrate**: riprende dal 09 e chiude la finestra. Nessun
changeSet applicato va toccato.

### 2026-08-26 · ✅ CANTIERE DB CHIUSO — applicato, baseline verde, doc scritta

**Migrate completo.** Letto da `databasechangelog`, non dal brief: **13 changeSet
su 13**, `20260826-01..13`, in due riprese (11:46 il primo giro fino all'08, 11:53
dal 09 in poi dopo la correzione della precondition).

**Verificato sul database, non dedotto dai file:**

| cosa | esito |
| --- | --- |
| i due parametri a catalogo | `..._IMMEDIATA_GIORNI = 12` · `..._DIFFERITA_GIORNO_MESE = 15` |
| backfill della competenza | **19 fatture su 19** valorizzate |
| il codice errore nuovo | `E_FATTURA_DATA_OLTRE_LIMITE_EMISSIONE` a catalogo, classe `DATO_ERRATO` |
| la firma del cancello | `p_registro_id bigint, p_data date, p_competenza_mese date, p_serie text, p_fattura_id bigint` |

**pgTAP: `scripts/pgtap-baseline.sh vendite` VERDE.** ⭐ E vale anche per il file
nuovo: la suite raccoglie i file con `find`, non con un glob a un livello, quindi
`test-limite-emissione-v1.sql` ci è passato dentro e i suoi **19 test** sono
verdi. Nessuna regressione sui due file bonificati
(`test-registri-progressivi.sql`, `test-data-documento-v1.sql`).

#### Doc concettuale (DB-12)

Auto-gen rigenerata da Tid. Scritta la doc manuale in `dbzero/vendite/manual/`:

* **quattro nuove** — `fn_get_pavimento_emissione`,
  `fn_get_pavimento_data_documento`, `fn_get_pavimento_lotto`,
  `fn_get_limite_emissione_default`;
* **una rinominata** con `git mv` (la storia del file resta):
  `fn_get_data_minima_numerabile` → `fn_get_pavimento_sequenza`;
* **sei aggiornate** — `fn_calcola_data_documento`, `fn_get_next_progressivo`,
  `fn_imposta_data_documento_lotto`, `fn_get_data_minima_numerabile_lotto`,
  `fn_get_or_create_fattura_header`, `fn_assign_numero_fattura`.

⭐ **Riparati tre riferimenti al nome vecchio**, di cui uno era un **link a una
pagina che non esiste più**: in `fn_get_next_progressivo`, due in
`fn_get_data_minima_numerabile_lotto`, e una citazione in prosa in
`fn_assign_numero_fattura`. Il nome vecchio sopravvive in un solo posto, ed è
**storia dichiarata**: la riga di `fn_get_pavimento_sequenza` che spiega perché è
stato rinominato.

---

### 2026-08-26 · ✅ BE-1 chiuso e BE-2 riverificato (backend)

Il ripiego di `E_FATTURA_DATA_OLTRE_LIMITE_EMISSIONE` è scritto, le policy
rigenerate, il backend ricaricato (`kill -HUP` sul master gunicorn: senza, in app
non si sarebbe visto niente).

⭐ **La rigenerazione ha aggiunto una voce sola**, 781 → 782. È la verifica che
conta più dell'esito: il diff è stato fatto **prima** di accettare il file, per
sapere se il catalogo del DB fosse avanti rispetto a git. Non lo era —
`--check` ora risponde *allineato*. Rigenerare senza guardare avrebbe potuto
tirare dentro codici di altri cantieri senza che nessuno se ne accorgesse.

**Il ripiego, e perché è scritto così.** Il messaggio a catalogo dice *«la prima
data ammessa è il %s»*: il ripiego esiste **proprio perché** quel `%s` può non
arrivare, quindi non può nominare nessuna data. Dice le tre cose che restano
vere senza argomenti — la data è troppo vecchia, **non è il cancello della
sequenza**, e il calendario del dialog si apre già sul minimo giusto. La
distinzione dal gemello `E_FATTURA_DATA_ANTERIORE_ULTIMO_NUMERO` sopravvive
quindi anche nel ripiego, che è il punto per cui il catalogo insiste che sono
due codici e non uno.

**BE-2 riverificato, non creduto.** Il piano diceva «niente»; l'ho controllato
sulla doc rigenerata dal push. Le tre firme che il backend usa combaciano con i
punti di chiamata, e le tre cambiate — `fn_assign_numero_fattura`,
`fn_get_next_progressivo`, `fn_calcola_data_documento` — nel backend compaiono
**solo dentro commenti e docstring**. ⚠️ Il controllo che serviva davvero era un
altro: `fn_get_data_minima_numerabile` **senza** il suffisso `_lotto` è sparita
col cantiere, e un `grep` sul nome corto trova anche quella lunga. Cercata con il
confine giusto: **nessuna chiamata**. Se ce ne fosse stata una, nessun test
l'avrebbe vista — i mock non conoscono le firme
([[feedback_rinomina_db_binding_mockato]]).

**Misure**: `test_error_policies_classi` 17/17, suite backend **4073 test OK**
(7 skip), `genera_error_policies --check` allineato.

---

### 2026-08-26 · ✅ Collaudo superato — cantiere chiuso

Il messaggio nuovo è stato visto a video da Tid e si comporta come previsto.

⚠️ **La strada per arrivarci non era quella che il §7 lasciava immaginare.** La
tabella dei sei documenti da numerare descriveva casi che *esistevano quel
giorno*: quando il collaudo è partito erano già stati numerati, e non restava
nessun caso spontaneo. Il messaggio si è raggiunto dall'unica porta che **non
dipende dai dati** — la data **dichiarata a mano** nel dialog di numerazione, che
è poi il percorso per cui il codice è nato (⛔ D-2, «il clamp vale per il default,
il cancello vale per la dichiarazione»).

⭐ **È la lezione da portare via**, e vale oltre questo cantiere: un collaudo
appoggiato a righe misurate un giorno preciso **scade**, perché le righe si
muovono. Quello appoggiato al **gesto** — dichiara una data fuori regola — vale
sempre. Le misure servivano a trovare il difetto, non a costruire la prova.

### 2026-08-26 · ⚠️ Due cose trovate durante il collaudo, che NON sono di qui

1. 🟠 **Il drawer del lotto appena generato mostra un pannello senza azioni.**
   Aprendolo mentre la pipeline gira, il drawer si tiene quella fotografia e non
   rilegge la testata quando la generazione finisce: le due azioni ci sono e sono
   abilitate (verificato su tutti e tre gli strati — `fn_available_actions_lotto`,
   `fn_get_lotto`, permessi a catalogo), ma a video non compaiono finché non si
   riapre. ⛔ Non dà nessun segnale di essere una foto vecchia. È il gemello
   rovesciato del pulsante-vicolo-cieco del 2026-07-31 — lì un pulsante di
   troppo, qui due che mancano. **Senza cantiere: da assegnare.**
2. ⚠️ **Un conteggio letto senza contesto operatore.** Cercando i casi vivi,
   `vendite.fatturazione_lotti` ha risposto **zero a tabella piena**: la policy
   pretende `app.ruolo_applicativo = 'OPERATORE'` e con `'SYSTEM'` è fail-closed.
   Lo zero è passato per un dato e ha prodotto la conclusione sbagliata («non c'è
   più niente da provare»). Stessa specie del §45.9.2 del brief nota di credito.
   Nessuna azione: è un promemoria di metodo, non un difetto del software.

---

### ⛔ Cosa resta, e a chi

| | Cosa | Perché non è qui |
| --- | --- | --- |
| **DOC-1** | 🚫 **RINUNCIATO** (Tid, 2026-08-26: *«insignificante»*). **Un altro giro di auto-gen.** Le cinque pagine nuove in `funzioni/` non hanno la riga `include-markdown` verso il loro manuale — l'auto-gen la scrive solo se il manuale **esiste già** quando gira, e sono stati scritti dopo. Stessa ragione per cui `index.ci.md` elenca ancora `fn_get_data_minima_numerabile`, che ora è un **link morto** | ⛔ Non si edita a mano un file auto-generato: si rigenera |
| **BE-1** | ✅ **FATTO il 2026-08-26.** Ripiego senza `%s` scritto in `error_messages_fallback.py` e policy rigenerate: `E_FATTURA_DATA_OLTRE_LIMITE_EMISSIONE` → `DATO_ERRATO`. ⭐ **La rigenerazione ha aggiunto una voce sola** (781 → 782): il catalogo del DB **non era avanti rispetto a git**, verificato col diff prima di committare. `--check` ora dice *allineato*. Presidi verdi: 17/17 su `test_error_policies_classi`, **4073 test BE OK** | |
| **BE-2** | **Niente** — ✅ **riverificato il 2026-08-26 sulla doc rigenerata dal push**, non sulla parola del piano. Le tre firme che il BE usa combaciano coi tre punti di chiamata: `fn_get_data_minima_numerabile_lotto(bigint)` (1977, 2058), `fn_imposta_data_documento_lotto(bigint, date)` (2084) e `fn_numera_fattura_opz_emessa(bigint, …)` (2100, 2246). ⛔ E delle due firme cambiate: `fn_assign_numero_fattura`, `fn_get_next_progressivo` e `fn_calcola_data_documento` compaiono nel backend **solo dentro commenti e docstring** — nessuna chiamata SQL. Verificato anche che nessuno chiami `fn_get_data_minima_numerabile` **senza** il suffisso `_lotto`, che il cantiere ha fatto sparire | |
| **FE-1** | **Niente di obbligato**, e ✅ **il collaudo è stato fatto** (2026-08-26): la `minDate` si è alzata da sola e il messaggio del rifiuto nuovo è stato visto a video, dichiarando una data fuori regola nel dialog di numerazione | |
| **GEMELLO** | `brief-db-registro-e-data-prevista-in-competenza.md` usa la firma nuova di `fn_calcola_data_documento` — **quattro** argomenti, con `p_serie` in terza posizione (▶ ✅ D-8) | La firma è già in servizio: quel cantiere la usa e basta |

⚠️ **Un debito preesistente trovato per strada, e nominato perché non si perda**:
in `dbzero/vendite/manual/` ci sono **4 link morti** verso
`fn_resolve_prezzo_composito`, `fn_resolve_prezzo_listino`,
`trgfn_ordini_guard_transizione_approvazione` e
`trgfn_preventivi_righe_guard_pending`, sparsi su **27 file** che questo cantiere
non ha toccato. Sembrano funzioni rinominate in un cantiere precedente senza
aggiornare i manuali — **la stessa classe che qui è stata chiusa**, e ciò che il
guardrail dei riferimenti morti troverà il giorno in cui girerà su questa
cartella.

---

## 10. Verifica tecnica del piano — 2026-08-26 (team DB)

**Come è stata fatta.** Le definizioni correnti sono state prese dalla doc
auto-generata (`docs/it/dbzero/vendite/funzioni/…`, `…/tabelle/…`), che riflette
l'oggetto vivo nel database, **non dagli YAML** — su `fn_get_next_progressivo` e
`fn_assign_numero_fattura` ci sono sei file che le definiscono e solo l'ultimo
conta. Sono stati riletti i pgTAP che attraversano la numerazione e i punti del
backend che chiamano queste funzioni. **Le misure del §1 e del §7 non sono state
rifatte**: si assumono per buone.

### 10.1 Cosa il piano dice giusto

Verificato, non ricopiato:

* **il cancello è al posto giusto.** 46 lotti su 52 nascono con almeno due
  settimane di margine: il controllo non tocca il flusso normale, e il costo di
  accenderlo è un documento in più fermo (§7);
* **il clamp chiude davvero il cerchio dei «recuperi del mese»** (§5) senza
  toccare il criterio della scheda — ed è la forma giusta: si corregge il dato
  che nasce storto, non il filtro che lo cerca;
* **il valore sta a configurazione e non nel codice**, che è l'unica difesa
  contro un'interpretazione fiscale murata in una costante;
* **slot globale + override sul registro** è il pattern già in casa
  (`config.parameters` + colonna nullable), e non introduce una `config.*`
  nuova per un parametro che ha già una sede;
* **la data di nascita dipendente dal tempo è una decisione, non un effetto**, ed
  è scritta come tale: chi legge non deve rimettersi a discuterla.

### 10.2 I difetti, in ordine di gravità

#### V-1 — ⛔ `fn_get_limite_emissione` come è definita ROMPE il flusso normale

Il §3.1 compone `pavimento_effettivo = GREATEST(ultima_data, limite_di_emissione)`
e il §2 definisce il limite della differita come **«15 del mese successivo alla
competenza»**. Ma quelle due cose vivono in spazi diversi:

| | che cosa è | in che spazio |
| --- | --- | --- |
| `ultima_data` | un **pavimento** sulla data del documento | data del documento |
| «15 del mese successivo» | una **scadenza** su quando stai lavorando | data di oggi |

Messe nello stesso `GREATEST`, il lotto di luglio lavorato il **5 agosto** — cioè
il caso normale, 46 volte su 52 — nascerebbe con
`GREATEST(31/07, 15/08) = 15/08`. **Ogni documento differito nascerebbe datato il
15 del mese successivo**, e il pgTAP che il §6 DB-7 chiede per primo («lotto di
luglio nato il 5 agosto → 31/07, nessun rifiuto») fallirebbe.

⭐ Non è un refuso di formula: è che **una scadenza e un pavimento non si sommano**.

#### V-2 — ⭐ La forma corretta: una regola sola con un'esenzione, non due forme che non si approssimano

Il §2 dice *«le due forme non si approssimano»*. È vero che le due politiche si
comportano diversamente, ma **non sono due regole indipendenti**: sono una regola
generale e la sua esenzione.

* **la regola**: un documento non può essere datato più di *N* giorni fa (12);
* **l'esenzione della differita**: un documento datato l'ultimo giorno del mese
  *M* resta emettibile fino al giorno *G* (15) del mese *M+1*.

Scritta come pavimento sulla data del documento:

```
pavimento_emissione(registro, competenza) =
    LEAST(
        data_operativa() − giorni,                       -- la regola, sempre
        CASE WHEN politica = 'FINE_MESE_COMPETENZA'
              AND data_operativa() <= scadenza(competenza)
             THEN fine_mese(competenza)                  -- l'esenzione, se aperta
        END
    )

scadenza(competenza) = date_trunc('month', competenza) + 1 mese + (giorno_mese − 1) giorni
```

⚠️ **`LEAST` in PostgreSQL ignora i NULL** (torna NULL solo se lo sono tutti):
a esenzione chiusa il secondo ramo sparisce da solo e resta `oggi − giorni`.
Nessun `COALESCE` difensivo — e vale allo specchio per il `GREATEST` del §3.1.

⭐ **L'argomento che decide è di modello, non di misura.** Il §6 DB-7 dichiara
come **contratto** che «il flusso normale passa»: lotto di luglio nato il 5
agosto → 31/07, nessun rifiuto. La forma del §2 viola quel contratto **per
costruzione** — la scadenza dentro il `GREATEST` alza la data di *ogni*
documento differito — questa lo rispetta.

ℹ️ **Come colore**, e togliendolo l'argomento resta in piedi identico: questa
forma riproduce anche la tabella del §7 riga per riga — `LTF-0000680` (31/07)
bloccato, `LTF-0006929` (24/08) passa — mentre la lettura del §2 li
bloccherebbe tutti.

⚠️ Conseguenza su D-1, che cambia risposta: ▶ V-5.

#### V-3 — ⛔ Il cancello non ha la competenza, e non può averla senza diventare fail-open

`fn_get_limite_emissione(p_registro_id, p_competenza_mese)` presuppone che chi
chiama abbia la competenza. Il **cancello** non ce l'ha:

* `vendite.fatture` **non ha nessuna colonna di competenza** — verificato sulla
  doc auto-gen: le sole colonne data sono `data`, `data_contabilizzazione` e le
  due di audit;
* la competenza vive su `vendite.fatturazione_lotti.competenza_mese`, raggiungibile
  solo attraverso `fatturazione_lotti_fatture`, il cui unico vincolo è
  `UNIQUE (lotto_id, fattura_id)` — **non impedisce a una fattura di stare in due
  lotti**, quindi la lettura andrebbe disambiguata;
* e soprattutto **`fatturazione_lotti` ha la RLS**, mentre `fn_get_next_progressivo`
  è `SECURITY INVOKER`: un lotto fuori dal perimetro di chi opera si legge come
  assente, la competenza uscirebbe `NULL`, il ramo differito si spegnerebbe e il
  cancello direbbe **«via libera»**. Un presidio fail-open esattamente nel punto
  che il cantiere della numerazione ha scelto perché è l'**unico non aggirabile**
  — e per la stessa ragione per cui quel cancello legge il contatore e non
  `vendite.fatture`.

⭐ **E la competenza non serve.** L'esenzione è una proprietà **della data**, non
della competenza: *«un documento datato l'ultimo giorno del mese M si emette fino
al giorno G di M+1»*. Il cancello chiama la **stessa** funzione di V-2 passando
`date_trunc('month', p_data)::date` al posto della competenza — sulla data 31/07
la competenza inferita è luglio e il risultato è identico. Nessun parametro nuovo
su `fn_get_next_progressivo`, nessuna lettura del lotto, nessun fail-open, e
**nessuna firma che cambia sotto al backend**.

⭐ **E c'è una terza strada, migliore di entrambe — ✅ PRESA** (D-9, Tid
2026-08-26), aperta da una sua obiezione: la **competenza vive sulla riga della
fattura**. Il cancello la prende da una colonna della riga che sta **già**
numerando — niente deduzione, niente seconda tabella, e la RLS lavora nel verso
giusto (se non vedi la riga non la numeri nemmeno).

⚠️ **La deduzione dalla data resta scritta lo stesso**, come **ripiego** per il
caso in cui la colonna sia `NULL` (una fattura senza lotto è ammessa dal
modello). Fa da rete, non è più la strada principale — e il paragrafo qui sotto
descrive quindi il **ripiego**, non il comportamento normale.

⚠️ **Il prezzo della deduzione, e va scritto**: il cancello **non distingue** un 31/07 dichiarato
su un lotto di competenza luglio da uno dichiarato su un lotto di giugno. Chi la
competenza vera ce l'ha è la **porta di dichiarazione**
(`fn_imposta_data_documento_lotto`, che riceve il lotto): lì il controllo è
**stretto**, al cancello è **per data**. È lo stesso schema anticamera/cancello
già in servizio sul pavimento di sequenza, e la differenza di severità va nel
`COMMENT` di entrambe — o il primo che le confronta la legge come un difetto.

#### V-4 — ⛔ Il clamp non deve atterrare SUL pavimento: deve atterrare su OGGI

`GREATEST(politica, pavimento_effettivo)` fa nascere il documento **esattamente
sul pavimento**, cioè con margine di trasmissione **zero**: un documento nato il
14/08 quando oggi è il 26/08 è già intrasmissibile il giorno dopo. La forma
giusta non è un `GREATEST` fra i due, è un `IF` sul primo e un `GREATEST` sul
secondo:

```sql
v_data := <risultato della politica>;                    -- oggi | fine_mese(competenza)

-- ⭐ Se la politica produce una data non più emettibile, si riparte da OGGI —
--    non dal pavimento: nascere sul pavimento e' nascere gia' scaduti domani.
IF v_data < vendite.fn_get_pavimento_emissione(p_registro_id, p_competenza_mese) THEN
    v_data := script.fn_data_operativa();
END IF;

-- ⭐ Il pavimento di SEQUENZA invece spinge in avanti verso una data ammessa:
--    li' il GREATEST e' giusto.
v_data := GREATEST(v_data, vendite.fn_get_data_minima_numerabile(p_registro_id, p_serie));
```

⚠️ Se D-2 rispondesse «a esenzione chiusa il pavimento è **oggi**», le due forme
coinciderebbero e il `GREATEST` tornerebbe corretto. Le due decisioni sono la
stessa decisione vista da due lati: ▶ §12 D-2.

#### V-5 — ⭐ D-1 ha una risposta, ma diversa da quella proposta, e viene dal modello

Sotto V-2 il parametro **in giorni è la regola generale** e vale **anche sulla
differita**: appena l'esenzione si chiude, il documento differito ricade sul
pavimento mobile come tutti. Quindi un registro `FINE_MESE_COMPETENZA` può
legittimamente valorizzare **entrambe** le colonne, e il CHECK proposto — «solo
quella coerente con la politica» — **vieterebbe una configurazione legittima**.

⭐ Restano **due colonne**, ma il CHECK è **a un lato solo**:

```
politica_data_documento = 'OGGI'  →  limite_emissione_giorno_mese IS NULL
```

Il valore inerte possibile è uno solo, e solo sull'immediata, dove il giorno del
mese non ha nessun significato.

⚠️ **E un CHECK che nomina `politica_data_documento` accoppia l'override alla
politica.** `20260825-05` è un loader `runOnChange` che riscrive quella colonna
**a ogni migrate**: il giorno in cui qualcuno cambia la politica di un registro
nel CSV mentre quel registro porta un override, il migrate muore su un changeSet
che non è suo. È la stessa specie di mina che questo stesso cantiere ha già
pagato una volta su `parameters.csv`. Va scritto nella testata del changeSet
delle colonne, non scoperto da chi cambierà il CSV.

#### V-6 — ⚠️ La targa non può dire tutta la verità, ed è strutturale

Per **tre giorni al mese** (dal 13 al 15, con 12 e 15) l'insieme delle date
ammesse **non è un intervallo**: il 14/08, per un documento di competenza luglio,
è `{31/07} ∪ [02/08, ∞)` — l'esenzione copre una data che sta *sotto* il
pavimento mobile, e in mezzo resta un buco (l'01/08).

Un `minDate` è un intervallo per costruzione, quindi qualunque valore mente in un
verso: `31/07` offre l'01/08 che il cancello rifiuterà, `02/08` vieta il 31/07
che è ammesso. Si sceglie il **LEAST** — permissivo, perché *«se targa e cancello
divergono comanda il cancello»* è già il contratto scritto nel `COMMENT` di
`fn_get_data_minima_numerabile` — e lo si dichiara. ⛔ Non si risolve con una
lista di date disabilitate lato FE: sarebbe una seconda implementazione della
regola, nel livello che per statuto non ne ha nessuna.

#### V-7 — ⚠️ `fn_calcola_data_documento` non conosce la SERIE, e il pavimento di sequenza è per (registro, serie)

`registri_fatturazione_progressivi` ha chiave `(registro_id, anno, mese, serie)`,
e `tipi_doc_fiscale_registri.serie` esiste apposta perché un registro può portare
**due sequenze**. Chiamare `fn_get_data_minima_numerabile(registro, NULL)` dal
clamp risolverebbe sul `serie_default`, cioè leggerebbe **il contatore di
un'altra sequenza** — e la risposta sbagliata è «nessun pavimento», la più
permissiva possibile proprio dove il cancello rifiuterà. È la V-5 del cantiere
della numerazione, identica, un mese dopo.

⇒ `fn_calcola_data_documento` deve ricevere **`p_serie`**, e chi la chiama ce
l'ha già in mano: `fn_get_or_create_fattura_header` calcola `v_serie` dalla
chiave undici elementi prima di usarla.

⛔ Aggiungere un parametro a una funzione esistente **crea un overload**, e con i
`DEFAULT` le chiamate diventano ambigue: serve `DROP FUNCTION` + `CREATE`, e il
chiamante va ricreato **nello stesso giro** con numerazione successiva.

#### V-8 — ⛔ Il clamp può spingere la data di nascita nel FUTURO, e su un registro `OGGI` è sbagliato

`ultima_data` **può essere futura**: un sezionale differito data i documenti a
fine mese, e una data dichiarata in avanti non è vietata da niente (§8 lo dice
esplicitamente). Il `GREATEST` col pavimento di sequenza sposta allora in avanti
la data di un documento **nuovo**.

Su `FINE_MESE_COMPETENZA` è coerente. Su `OGGI` produce un documento «datato
oggi» che porta una data futura — contro il `COMMENT` della sua stessa politica
(*«OGGI = la data odierna nel fuso dell'azienda»*). ▶ §12 D-3.

#### V-9 — ⛔ Tre `GREATEST` in tre punti sono tre implementazioni della stessa regola

Il §3.1, il §3.2 e il §3.3 compongono **ciascuno** il proprio
`pavimento_effettivo`. È la classe di difetto che il brief gemello chiama per
nome nel suo §3: *«ricopiare quella catena sarebbe una seconda implementazione
della stessa regola»* — e che questo mese ha già prodotto due incidenti.

⇒ **una sola sede** che compone i due pavimenti, e tre chiamanti che la leggono.
▶ DB-4 del piano.

#### V-10 — ⛔ Il cancello deve sapere QUALE pavimento ha vinto, o non può scegliere il codice

Il §3.3 chiede giustamente **un codice errore distinto** da quello della
sequenza: «più vecchio del limite di emissione» e «anteriore all'ultimo numero
emesso» si rimediano in due modi diversi. Ma una funzione che torna solo una
`date` ha già perso l'informazione che serve a scegliere la frase.

⇒ la sede composta torna `TABLE(pavimento date, origine text)`, con
`origine ∈ ('SEQUENZA', 'EMISSIONE')`. Il pareggio è una decisione: ▶ §12 D-4.

#### V-11 — ⛔ Acceso così, il cancello fa diventare rosso un pgTAP verde, da solo

`db/pgtap/vendite/test-registri-progressivi.sql` numera con
`date '2025-12-31'` e `date '2026-01-01'`, **letterali nel file** — e non è
pigrizia: i test 2-5 provano il reset d'anno e servono due anni civili. Con il
pavimento a `oggi − 12`, **12 asserzioni su 14 cadono**. Il registro di prova
nasce con `politica_data_documento` al default `OGGI`, quindi il ramo che le
colpisce è quello sempre attivo.

⭐ Rimedio: il registro di prova valorizza `limite_emissione_giorni` a un valore
enorme, **con la ragione scritta accanto**. È il primo uso legittimo della
colonna di override e prova la colonna mentre disinnesca il test — invece di
aggirare il presidio, lo si configura.

⚠️ **E `test-data-documento-v1.sql` è rosso da subito**: il test 7 chiede
`fn_calcola_data_documento(reg_finemese, '2026-07-01') = '2026-07-31'`, con la
competenza **letterale**. Oggi è il 26/08: esenzione chiusa, il clamp risponde
oggi. Quel test va **riscritto sul comportamento nuovo** (e ne servono due: uno
con l'esenzione aperta, uno con l'esenzione chiusa), non allargato finché
ripassa.

⚠️ Gli altri sei file che attraversano la numerazione —
`test-numerazione-guard-coerenza-v1`, `test-numera-nota-credito-riferimento-v1`,
`test-numera-fattura-opz-emessa`, `test-chiave-fattura-tre-specchi-v1`,
`test-fatture-righe-importo-e-kit-v1`, `rls/test-rls-fatture-satelliti-functional`
— vanno passati **con la baseline**, prima e dopo: un rosso lì può essere
preesistente.

#### V-12 — ⚠️ Il parametro NON si legge con `script.fn_get_parameter_full`

Stessa ragione già scritta per `SYSTEM_FUSO_ORARIO` (V-9 del cantiere
numerazione): la cascata di override utente/gruppo/sessione/emittente darebbe
**allo stesso documento** limiti diversi a seconda di chi lo genera, cioè il
difetto che questo cantiere chiude. Si legge il `default_value` nudo, e l'unico
asse di override è il **registro**. ⛔ Se non è scritto nel `COMMENT`, il prossimo
lo «corregge» verso il building block e riapre il buco.

#### V-13 — ⛔ Il seed NON va in append a `parameters.csv`

Mina armata e documentata: la riga `DEFAULT_UTILITY` (id 12) ha
`default_value = ''` e **non è più riscrivibile** (il dispatcher FK-surrogata è
entrato dopo). Un append cambia il checksum, sveglia il mirror `runOnChange`
`20250715-01` e il migrate muore su una riga di qualcun altro — è già successo il
2026-08-25.

⇒ **CSV dedicato**, pattern `parameters_sistema.csv` / `parameters_vendite_defaults.csv`.
⚠️ E se si sceglie di appendere a `parameters_vendite_defaults.csv` invece di
aprirne uno nuovo, la **riesecuzione** di quel loader va provata prima in
`BEGIN; … ROLLBACK;`: la specie «irriscrivibile» non si vede col confronto
CSV↔DB. ▶ §12 D-5.

⚠️ **Gli id di `config.parameters` sono una sequenza a mano**: il massimo nei CSV
del repo è **54**, quindi i primi liberi sono 55 e 56 — **da rileggere sul
database prima di scrivere il file**, perché più cantieri appendono nello stesso
giorno (collisione reale il 2026-08-18 su `messaggi_errore`).

#### V-14 — ⚠️ Quattro `COMMENT` che si ricreano citano un path morto

`fn_calcola_data_documento`, `fn_get_data_minima_numerabile`,
`fn_get_data_minima_numerabile_lotto` e `fn_get_next_progressivo` chiudono con
`Brief: docs/it/dev/work-in-progress/brief-db-numerazione-data-documento-e-sequenza.md`,
e quel brief è in `work-done/` dal giorno in cui il cantiere ha chiuso. Le copie
vivono **nel database** e si correggono solo ricreando la funzione: questo
cantiere le ricrea comunque, ed è l'unico giro in cui costa zero. Si cita il
**nome** del brief, mai il path.

✅ Il link morto in testa a **questo** brief è stato corretto in questa revisione:
il guardrail dei riferimenti morti gira dopo il migrate, e avrebbe fatto fallire
la build della doc senza dire perché.

---

## 11. ⭐ Il piano di sviluppo

⛔ **Sostituisce il §6.** Le consegne del §6 restano leggibili come intenzione;
questa è la loro forma eseguibile dopo la verifica del §10.

### 11.1 Le consegne

> ✅ **Tutte applicate il 2026-08-26** (`20260826-01..13`), verificate sul
> `databasechangelog` e non sul brief. La tabella resta come si legge un piano a
> cose fatte: dice **che cosa** è stato fatto e **perché** in quella forma.

| | Cosa | Dove | Nasce da |
| --- | --- | --- | --- |
| **DB-1** | I due parametri a catalogo: giorni dell'immediata (`12`) e giorno del mese della differita (`15`), con `description` che dice **che cosa misurano**, che sono una lettura configurabile e non una costante di legge, e che **non si leggono con `fn_get_parameter_full`** | CSV dedicato + loader `80_data` | V-12, V-13 · ✅ D-5 |
| **DB-2** | `registri_fatturazione`: `limite_emissione_giorni` e `limite_emissione_giorno_mese`, nullable (`NULL` = vale il default globale), CHECK di dominio (**`giorno_mese BETWEEN 1 AND 31`**, non 1..28) + CHECK a un lato solo sulla politica (`OGGI → giorno_mese IS NULL`) | `00_schema` | V-5 · ✅ D-1, D-6 |
| **DB-13** | ⭐ **`vendite.fatture.competenza_mese`** (`date`, nullable) + `COMMENT` + **backfill** da `fatturazione_lotti_fatture` con `MIN(competenza_mese)`. La competenza smette di essere raggiungibile solo attraverso il lotto | `00_schema` + `80_data` | ✅ D-9 |
| **DB-3** | `vendite.fn_get_pavimento_emissione(p_registro_id, p_competenza_mese) RETURNS date` — **una sola sede** per la regola e la sua esenzione. ⭐ Con lei nasce `vendite.fn_get_limite_emissione_default(p_code)`, che legge un limite dal catalogo: serve due volte (giorni e giorno del mese) con tre modi di sbagliare identici — assente, vuoto, non numerico. `NULL` = nessun pavimento. Nessun chiamante sa quale politica si applica. ⭐ La scadenza si calcola **sul mese** (`LEAST(primo + giorno − 1, ultimo del mese)`): con `31` su un febbraio esce il 28 | `20_code` | V-1, V-2 · ✅ D-2, D-6 |
| **DB-4** | `vendite.fn_get_pavimento_data_documento(p_registro_id, p_serie, p_competenza_mese) RETURNS TABLE(pavimento date, origine text)` — la sede unica che **compone** i due pavimenti e dice quale ha vinto. ⭐ `pavimento` è **sempre** quello **effettivo** (il maggiore), e `origine` serve solo a scegliere la frase | `20_code` | V-9, V-10 · ✅ D-4 |
| **DB-5** | Il codice errore nuovo (`DATO_ERRATO`, `context.campo = data_documento`, bersaglio sul documento) + messaggio con la data in formato italiano + **ripiego senza `%s`** | append ai due CSV, **nessun loader nuovo** | §3.3 |
| **DB-6** | `fn_calcola_data_documento`: **DROP + CREATE** con `p_serie` **senza `DEFAULT`**, clamp `IF … THEN oggi` sul limite e `GREATEST` sulla sequenza. ⛔ Solo sul ramo calcolato. ⛔ La firma si disegna **per entrambi i cantieri in una volta sola** (▶ ✅ D-8) | `20_code` | V-4, V-7, V-8 · ✅ D-2, D-3, D-8 |
| **DB-7** | `fn_get_or_create_fattura_header`: passa `v_serie` alla funzione della data **e scrive `competenza_mese` nella `INSERT`**. ⭐ Il valore ce l'ha già in mano — lo legge dal lotto per calcolare la data | `20_code` | DB-6 · ✅ D-9 |
| **DB-8** | ⭐ In corso d'opera è diventata **due cose**. (a) `fn_get_data_minima_numerabile` si **rinomina** `fn_get_pavimento_sequenza`: da quando i pavimenti sono due, «data minima numerabile» è il nome della *composizione* e non di quella primitiva — e il rename non rompe niente (zero chiamanti, verificato). (b) nasce `fn_get_pavimento_lotto(lotto) RETURNS TABLE(pavimento, origine)`, che compone **per fattura** (registro + serie del documento, `COALESCE(f.competenza_mese, fl.competenza_mese)`) e prende il massimo; `fn_get_data_minima_numerabile_lotto` diventa una **lettura sottile** su di essa. ⛔ Il suo nome NON si rinomina: è un contratto col backend e la `minDate` del dialog | `20_code` | V-6 · ✅ D-4, D-9 |
| **DB-9** | `fn_imposta_data_documento_lotto`: il guard di dichiarazione diventa **stretto** e sceglie fra i **due codici** leggendo `origine` da `fn_get_pavimento_lotto`. ⭐ La regola non si riscrive: arriva già composta | `20_code` | V-3 · ✅ D-4 |
| **DB-10** | `fn_get_next_progressivo`: **DROP + CREATE** con `p_competenza_mese` **obbligatorio, in terza posizione** (dopo i due già obbligatori: in PostgreSQL i parametri con `DEFAULT` stanno in coda). ⛔ **La frase nomina il pavimento EFFETTIVO, non quello di sequenza** — oggi nomina il secondo, e con due pavimenti manderebbe a sbattere due volte (✅ D-4). Il messaggio della sequenza si usa quando dietro c'è un documento raggiungibile, altrimenti quello del limite | `20_code` | V-3, V-10 · ✅ D-4, D-9 |
| **DB-14** | ⭐ `fn_assign_numero_fattura`: legge `f.competenza_mese` e la passa al cancello. **Firma invariata.** Costa **una colonna in più in una `SELECT` che già c'è** (`SELECT f.registro_id, f.data, … FROM vendite.fatture f`) | `20_code` | ✅ D-9 |
| **DB-11** | pgTAP nuovo + **bonifica dei tre file che diventano rossi** | `db/pgtap/vendite` | V-11 · ✅ D-9 |
| **DB-12** | Doc concettuale delle funzioni nuove in `dbzero/vendite/manual/`, e il `COMMENT` delle ricreate che cita il **nome** del brief | `docs/` | V-14 |

⭐ **Perché D-9 costa così poco**, ed è la ragione per cui si fa adesso e non
dopo: le due funzioni che la usano — `fn_get_next_progressivo` e
`fn_assign_numero_fattura` — erano **già** da riscrivere in questo cantiere, la
seconda legge già la riga della fattura, e `fn_get_or_create_fattura_header` ha
già la competenza in mano per calcolare la data. Farlo dopo vorrebbe dire
riaprire tre funzioni per aggiungere tre righe.

### 11.2 L'ordine, e perché è quello

| Lotto | Consegne | Perché sta insieme |
| --- | --- | --- |
| **A** | DB-1, DB-2, **DB-13** | Colonne, parametri e backfill: **nessuno li legge ancora**. Applicabile da solo, non cambia nessun comportamento. ⚠️ Il backfill sta qui e non alla fine: da qui in avanti la colonna è piena, e chi la legge non deve distinguere «non backfillata» da «senza lotto» |
| **B** | DB-3, DB-4, DB-5 | Le due sedi nuove e il codice errore: **nessun consumatore**. Il cancello non è ancora acceso |
| **C** | DB-6 + DB-7 | ⛔ **Inseparabili**: DB-6 cambia la firma, e fra il `DROP` e la ricreazione del chiamante c'è una finestra in cui la generazione di una bozza **non risolve la funzione**. Vanno nello stesso migrate, e DB-7 deve avere numerazione **successiva** — `changelog-autogen.yaml` ordina per NN mescolando `00_schema` e `20_code` |
| **D** | DB-8, DB-9, **DB-10 + DB-14** | ⭐ **Qui si accende il cancello.** Prima la targa (DB-8), poi le porte. ⛔ **DB-10 e DB-14 sono inseparabili come C**, e per la stessa ragione: `fn_get_next_progressivo` cambia firma e il suo **unico** chiamante è `fn_assign_numero_fattura` (verificato su `pg_proc`). Fra i due changeSet la numerazione non funziona — ⚠️ e PostgreSQL non lo impedisce, perché non traccia le dipendenze dentro il corpo di una funzione PL/pgSQL: il `DROP` riesce in silenzio |
| **E** | DB-11, DB-12 | I presidi e la doc. ⚠️ Il pgTAP di V-11 **va scritto insieme al lotto D**, non dopo: senza, il lotto D lascia la suite rossa e non si distingue più una regressione da un rosso noto |

### 11.3 I file, con i nomi

⚠️ La numerazione `NN` è una **sequenza globale per data fra tutte le cartelle**,
non per cartella. Al 2026-08-26 non esiste nessun `20260826-*`: si parte da `01`.
Un changeSet per file, `logicalFilePath` sempre valorizzato.

| # | File | Consegna |
| --- | --- | --- |
| 01 | `00_schema/vendite/20260826-01-alter-registri-limite-emissione-mctit.yaml` | DB-2 |
| 02 | `00_schema/vendite/20260826-02-alter-fatture-competenza-mese-mctit.yaml` | DB-13 |
| 03 | `80_data/sql/config/parameters_fatturazione.csv` + `80_data/changelog/20260826-03-upsert-parameters-limite-emissione-mctit.yaml` | DB-1 |
| 04 | `80_data/changelog/20260826-04-backfill-fatture-competenza-mese-mctit.yaml` | DB-13 |
| 05 | `20_code/vendite/20260826-05-create-fn-get-pavimento-emissione-mctit.yaml` — **due funzioni**: il lettore del parametro e il pavimento | DB-3 |
| 06 | `20_code/vendite/20260826-06-rename-fn-get-data-minima-numerabile-in-pavimento-sequenza-mctit.yaml` | DB-8a |
| 07 | `20_code/vendite/20260826-07-create-fn-get-pavimento-data-documento-mctit.yaml` | DB-4 |
| — | append a `80_data/sql/config/codici_errore.csv` e `messaggi_errore.csv` (**id 991**) | DB-5 |
| 08 | `20_code/vendite/20260826-08-recreate-fn-calcola-data-documento-serie-e-clamp-mctit.yaml` (`DROP` + `CREATE`) | DB-6 |
| 09 | `20_code/vendite/20260826-09-update-fn-get-or-create-fattura-header-serie-e-competenza-mctit.yaml` | DB-7 + DB-13 |
| 10 | `20_code/vendite/20260826-10-recreate-fn-get-pavimento-lotto-e-data-minima-mctit.yaml` — **due funzioni**: la composta per lotto e la lettura sottile | DB-8b |
| 11 | `20_code/vendite/20260826-11-update-fn-imposta-data-documento-lotto-limite-mctit.yaml` | DB-9 |
| 12 | `20_code/vendite/20260826-12-recreate-fn-get-next-progressivo-limite-e-competenza-mctit.yaml` (`DROP` + `CREATE`) | DB-10 |
| 13 | `20_code/vendite/20260826-13-update-fn-assign-numero-fattura-competenza-mctit.yaml` | DB-14 |
| — | `db/pgtap/vendite/test-limite-emissione-v1.sql` (**nuovo, 19 test**) · bonifica di `test-registri-progressivi.sql` e `test-data-documento-v1.sql` | DB-11 |

⚠️ **L'ordine dentro `20_code` non è estetico**: `06` (il rinominato) precede
`07` (chi lo usa); `08` droppa la firma e `09` è il chiamante che la riscrive;
`12` droppa il cancello e `13` è il suo unico chiamante. `changelog-autogen.yaml`
ordina per NN mescolando `00_schema` e `20_code`, quindi il numero **è**
l'ordine.

⚠️ **Nessun loader nuovo per i codici errore**: i mirror `runOnChange` esistenti
ripescano i CSV. Il primo id libero su `messaggi_errore` **oggi** è `991`, e va
riletto prima di scrivere.

⚠️ **Il backfill (04) è `runOnChange: false` e fotografa un minuto** — ed è
corretto **solo perché la sorgente si chiude nello stesso giro**: dal file 08 in
poi `fn_get_or_create_fattura_header` scrive la colonna alla nascita, quindi non
resta nessuno che continui a sporcare. È lo stesso argomento scritto in
`20260825-10` per `ultima_data`, e va ripetuto nella testata: se un domani la
colonna tornasse a riempirsi da sola a metà, il rimedio non sarebbe un secondo
backfill.

⚠️ **`test-registri-progressivi.sql` chiama il cancello per NOME di parametro**
(`p_registro_id => …, p_data => …, p_serie => NULL`): con `p_competenza_mese`
obbligatorio quelle chiamate **non risolvono più**. Va aggiunto l'argomento —
insieme al `limite_emissione_giorni` enorme sul registro di prova (V-11).

### 11.4 Le regole di scrittura, in una lista che si spunta

* corpo delle funzioni esistenti **dalla doc auto-gen**, mai dagli YAML — su
  `fn_get_next_progressivo` ce ne sono sei e solo l'ultimo conta;
* ⚠️ il corpo dell'auto-gen **non è incollabile così**: manca il `;` dopo
  `$function$`;
* `%TYPE` in **firma, `DECLARE` e `RETURNS TABLE`**, e poi verificare con
  `pg_get_function_identity_arguments` che non sia nato un **overload** invece di
  una revisione;
* `SECURITY INVOKER` esplicito; `STABLE` sulle due funzioni nuove (leggono e
  basta, e `now()` è l'istante d'inizio transazione);
* guard di parametro **uno per parametro**, `IS NULL OR <= 0`, codice
  `E_VENDITE_CHIAMATA_NON_VALIDA` (`TECNICO`) — ⛔ mai `E_PARAMETRO_INVALIDO`;
* ⛔ **nessun `ELSE` che ingoia** sulla politica: un valore non gestito solleva,
  come già fa `fn_calcola_data_documento`;
* nel `VARIADIC` va **la data in formato italiano** (`to_char(…, 'DD/MM/YYYY')`),
  mai un nome di parametro o di colonna;
* `runOnChange: false` nello stato committato (i loader CSV restano `true`, è il
  loro mestiere) e `validCheckSums` **al plurale**;
* il `COMMENT` cita il **nome** del brief, mai un path `work-in-progress/`.

### 11.5 Come si verifica, prima di consegnare

1. **l'SQL ESTRATTO dallo YAML** eseguito in `BEGIN; … ROLLBACK;` — non una copia
   riscritta a mano: la copia salta sempre i `COMMENT`, ed è lì che il migrate
   muore su un apostrofo non raddoppiato;
2. `scripts/guardrail_sql_letterali.py` su tutto `migrations_v2`;
3. **riesecuzione del loader CSV** in transazione (V-13): il confronto CSV↔DB non
   vede la specie «irriscrivibile»;
4. `scripts/pgtap-baseline.sh vendite` **prima e dopo**, e
   `scripts/testpgtap.sh` sul file nuovo;
5. un pgTAP che rilegge il CHECK nuovo con `pg_get_constraintdef`: **un vincolo
   non sa chi ci scrive**, e la funzione che valorizzerà quelle colonne avrà un
   guard suo;
6. i segnaposto del messaggio nuovo passati con lo scanner dei `%` (un `%`
   malformato fa sparire l'errore di dominio dietro un `22023`).

⛔ **Nessuna migrazione.** I file si scrivono e si verificano in transazione;
l'`update` lo autorizza Tid **a parole, per quel comando**.

### 11.6 Cosa nasce per BE e FE

| | Cosa | Note |
| --- | --- | --- |
| **BE-1** | Il **ripiego senza `%s`** del codice nuovo in `apps/core/services/error_messages_fallback.py`, poi `manage.py genera_error_policies` | Presidiato da `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`: senza, il test del BE diventa rosso |
| **BE-2** | **Niente**, e vale anche dopo D-9. ⭐ Verificato: i tre punti di `pipeline_repository.py` (1977, 2058, 2084) chiamano `fn_get_data_minima_numerabile_lotto` e `fn_imposta_data_documento_lotto`, **a firma invariata**; e per numerare il backend chiama `fn_numera_fattura_opz_emessa`, la cui firma **non cambia**. ⛔ Nessun punto del backend chiama `fn_assign_numero_fattura` o `fn_get_next_progressivo` direttamente: le due firme che cambiano restano interne al database | |
| **FE-1** | **Niente di obbligato.** La `minDate` che il dialog già legge (`NumerazioneDataDialog.vue`) diventa più alta da sola | ⚠️ Il messaggio del nuovo rifiuto va provato in collaudo: è una frase diversa, e il primo che la incontra deve capire che non è il cancello della sequenza |

⛔ **Il cantiere gemello non è un avviso: è un requisito della firma** (✅ D-8,
Tid 2026-08-26 — *«il problema non è la rottura: la modifica deve essere fatta
tenendo conto di entrambe le esigenze»*).
`brief-db-registro-e-data-prevista-in-competenza.md` chiama la stessa funzione
dalle due viste della dashboard per la colonna `data_documento_prevista`, e le
viste **hanno già la serie** in mano (gliela dà `fn_resolve_registro_documento`).
La firma nuova si disegna quindi **una volta sola per tutti e due**, e il dettaglio
sta in §12 D-8. ⭐ Effetto buono: col clamp, `data_documento_prevista` smette di
promettere il 31/07 su un lotto in ritardo e mostra la data che il documento
prenderà **davvero** — cioè la colonna diventa vera proprio nel caso che l'ha
fatta nascere.

---

## 12. ⭐ Le decisioni

> **Giro 1 — Tid, 2026-08-26.** D-1, D-5, D-6, D-8.
> **Giro 2 — Tid, 2026-08-26.** D-2, D-3, D-4, D-7.
> **Giro 3 — Tid, 2026-08-26.** D-9, nata dall'obiezione sulla scrittura diretta
> al database.
>
> ⭐ **Nessuna domanda aperta: il piano è pronto per essere scritto.**

---

### D-1 — una colonna o due? ✅ **DECISA**

**Due colonne**, con CHECK **a un lato solo**
(`politica_data_documento = 'OGGI' → limite_emissione_giorno_mese IS NULL`).

⭐ Con questa risposta è confermata anche la premessa che ci sta sotto: **il
limite in giorni vale anche sulla differita**, quando il permesso di datare a
fine mese è scaduto. ▶ V-5.

---

### D-2 — a permesso scaduto, quanto indietro può andare una data dichiarata a mano? ✅ **DECISA: B**

⭐ **`oggi − giorni`.** A permesso scaduto la differita ricade sulla **regola
generale**, non su una regola più severa.

**Il caso, in concreto.** Registro Back-office (differita), competenza **luglio**:
il documento porta il **31/07** e va mandato entro il **15/08**. Se lo lavori il
**20/08** sei fuori tempo e il 31/07 non si usa più. Da quel momento l'operatore
può scrivere nel dialog **qualunque data dall'08/08 in poi** — non solo il 20/08.

Perché: i 12 giorni non sono «la regola dell'immediata», sono la regola di
**tutti** i documenti; il «15 del mese dopo» è un **permesso in più** che ha solo
la differita e che scade. Quando un permesso scade torna la regola normale.
⛔ L'alternativa scartata obbligava a spiegare a un operatore perché il sistema
rifiuta una data che la regola generale ammette.

⚠️ **Il documento che nasce da solo prende comunque la data di oggi**: la
differenza vale solo quando è una persona a scegliere una data arretrata.

ℹ️ **Conseguenza tecnica**: il calcolo della data alla nascita **non è un
`GREATEST`** ma un `IF`. Con il `GREATEST` il documento nascerebbe datato 12
giorni fa, cioè con il tempo per mandarlo già finito. ▶ V-4.

---

### D-3 — alla nascita, il documento guarda anche l'ultimo numero già emesso? ✅ **DECISA: sì**

⭐ **Sì: nasce datato 31/08.** Parole di Tid: *«come accade ora a video non si può
scegliere una data inferiore al 31/08, che è la data limite»* — cioè il documento
nasce **sulla stessa regola** che il dialog già applica a chi sceglie a mano. Il
comportamento è uno solo, che la data la scelga una persona o il sistema.

**Il caso.** Sul Back-office è già numerata una fattura datata **31/08**
(competenza agosto: la differita data a fine mese, quindi in avanti). Oggi è il
**26/08** e nasce un documento in ritardo, di competenza giugno → **nasce datato
31/08**, ed è già numerabile. Senza questa regola nascerebbe col 26/08, verrebbe
**rifiutato** al momento di numerare, e servirebbe ridichiarare la data a mano —
esattamente il fastidio che il cantiere toglie.

⚠️ **Conseguenza accettata**: il documento può nascere con una data **futura**
(31/08 mentre oggi è il 26/08). Su un registro differito è la sua politica; su un
registro «data di oggi» si legge strano, ma ci si arriva solo se su quel registro
c'è **già** un documento datato in avanti. ▶ V-8.

---

### D-4 — quale frase mostra il rifiuto? ✅ **DECISA: sempre la data limite, e la provenienza quando c'è**

⭐ **La regola non è «quale dei due codici vince», è: si mostra SEMPRE la data
limite; se dietro quella data c'è un documento, si dice da dove viene.**

| il pavimento effettivo viene da… | cosa dice il messaggio |
| --- | --- |
| l'**ultimo numero emesso** (e quel documento è raggiungibile) | la **data limite** + *«proviene dall'ultima fattura emessa»*, con il pulsante che la apre (bersaglio già in servizio) |
| il **limite di emissione**, o nessun documento raggiungibile | **solo la data limite** |

È la logica che il BE ha già portato a video: il calendario non fa scegliere una
data precedente, e il dialog mostra il limite. Questa decisione la **conferma e la
estende** al limite di emissione, senza cambiarne la forma.

⛔ **E qui c'è la correzione tecnica che vale più della scelta della frase.** Oggi
`fn_get_next_progressivo` mette nel messaggio `to_char(v_pavimento, …)` dove
`v_pavimento` è il **pavimento di sequenza**. Con due pavimenti, la frase deve
nominare il **pavimento EFFETTIVO** — il maggiore dei due. Se nominasse quello di
sequenza mentre a mordere è il limite di emissione, direbbe all'operatore di
scegliere una data **che verrà rifiutata di nuovo**: un messaggio che manda a
sbattere due volte è peggio di un messaggio generico.

⭐ **Il pareggio si risolve da solo**, e non serve più una regola apposta: il
discriminante non è quale pavimento è più alto, è **se dietro c'è un documento
che l'operatore può aprire**. A parità, il documento c'è → messaggio della
sequenza.

⚠️ **Conseguenza sulla targa** (DB-8): `fn_get_data_minima_numerabile_lotto` deve
comporre il pavimento **per fattura** (registro + serie del documento, competenza
del lotto) e poi prendere il massimo — non più il solo `max(ultima_data)`. Un
lotto può toccare più registri, e i registri hanno limiti diversi.

---

### D-5 — dove vive il seed dei due parametri? ✅ **DECISA**

CSV **nuovo** `parameters_fatturazione.csv` con loader dedicato — stessa scelta
presa 24 ore prima per `SYSTEM_FUSO_ORARIO`, e senza il rischio della specie
«irriscrivibile». ▶ V-13. Codici:
`VENDITE_LIMITE_EMISSIONE_IMMEDIATA_GIORNI` (`12`) e
`VENDITE_LIMITE_EMISSIONE_DIFFERITA_GIORNO_MESE` (`15`) — nomi che si trovano con
un `grep`. ⛔ Scartata la forma «componi il codice dalla politica»
(`'VENDITE_LIMITE_EMISSIONE_' || v_politica`): rende il consumatore invisibile a
chi cerca per nome.

---

### D-6 — il giorno del mese ✅ **DECISA: si calcola sul mese**

⛔ **Niente tetto a 28.** Il valore configurato è un giorno del mese, e la
scadenza si calcola **contro il mese in cui cade**: se il mese è più corto del
giorno configurato, la scadenza è **l'ultimo giorno di quel mese**.

```sql
-- primo giorno del mese SUCCESSIVO alla competenza
v_primo_succ := (date_trunc('month', p_competenza_mese) + interval '1 month')::date;
-- ultimo giorno dello stesso mese
v_fine_succ  := (v_primo_succ + interval '1 month - 1 day')::date;

-- ⭐ Il giorno configurato si appoggia al mese, non lo scavalca: con 30 su un
--    febbraio la scadenza e' il 28 (o il 29), non il 2 marzo.
v_scadenza   := LEAST(v_primo_succ + (v_giorno_mese - 1), v_fine_succ);
```

* CHECK di colonna: `BETWEEN 1 AND 31` (non 1..28);
* il `COMMENT` della colonna dice **che la scadenza è calcolata sul mese**, così
  chi configura `31` sa già che a febbraio otterrà il 28.

⚠️ Il `LEAST` è nella funzione, **non** nel CHECK: il vincolo presidia il valore
configurato, la funzione lo traduce in una data. Sono due mestieri diversi, e
metterli insieme farebbe dipendere un CHECK da un mese che non conosce.

---

### D-7 — il controllo finale deduce il mese dalla data ✅ **DECISA: si accetta**

**Come funziona.** Il controllo non aggirabile gira quando si assegna il numero.
Lì il sistema ha in mano **il documento e la sua data**, ma non sa a quale mese di
competenza appartiene: quell'informazione sta sul lotto, e leggerla da lì è
pericoloso — le regole di visibilità possono nasconderla, e un controllo che non
vede risponde «vai pure» proprio quando non sa (▶ V-3). Quindi **deduce il mese
dalla data**: 31/07 → luglio.

**Cosa non distingue:** un 31/07 che è davvero di luglio da un 31/07 che in realtà
è di **giugno**, scritto a mano. Va bene lo stesso perché quella data si scrive
**da un'unica porta** — il dialog del lotto — e lì il sistema la competenza vera
ce l'ha, quindi lì il controllo è **severo**.

| dove | cosa sa | quanto è severo |
| --- | --- | --- |
| **dialog del lotto** (dove si sceglie la data) | il lotto, quindi la competenza vera | severo: confronta con la competenza |
| **assegnazione del numero** (dove non si può aggirare) | il documento e la sua data | deduce il mese dalla data |

#### ⭐ L'obiezione di Tid, ed è giusta: «chi scrive a DB dovrebbe poter toccare solo i documenti non numerati»

**Sì, ed è già così dal 2026-08-25.** Il trigger
`trg_fatture_a10_guard_data_numerata_upd` (funzione
`vendite.trgfn_fatture_guard_data_numerata`) rifiuta **qualunque** cambio di
`vendite.fatture.data` su una fattura che ha già un numero, con
`E_FATTURA_DATA_NON_MODIFICABILE`. Tre cose che lo rendono davvero un cancello:

* è un **trigger**, quindi vale anche per chi scrive da `psql`: non c'è modo di
  passargli accanto restando dentro il database;
* è `BEFORE UPDATE` **senza `UPDATE OF`**, quindi scatta su ogni `UPDATE` della
  riga, non solo su quelli che nominano la data;
* ⭐ il discriminante è **`OLD.numero`, non lo stato** — e non è un dettaglio: la
  fattura viene numerata *mentre* è in `EMESSA`, quindi una soglia scritta sugli
  stati lascerebbe una finestra reale in cui il documento ha già un numero
  fiscale e la data è ancora scrivibile.

*«Se qualcuno modifica una data dopo che è numerata fa un bel casino»* — esatto, e
il casino ha un nome preciso: dalla data dipendono **l'anno del sezionale**, **la
chiave del contatore** e **il piano rate**. È il buco che il cantiere della
numerazione ha trovato con una misura e chiuso con la consegna DB-14.

⇒ **Il residuo di D-7 riguarda quindi i soli documenti NON numerati**, dove la
data deve restare scrivibile perché è il percorso normale del dialog. E per quel
residuo la strada pulita non è un altro trigger — ▶ **D-9**.

✅ **Decisione: si accetta la deduzione dalla data, e si scrive nei due `COMMENT`**
(quello del cancello e quello della porta di dichiarazione), così chi le confronta
non legge la differenza di severità come un difetto.

---

### D-8 — la firma di `fn_calcola_data_documento` ✅ **DECISA**

Il cantiere gemello (`brief-db-registro-e-data-prevista-in-competenza.md`) chiama
la stessa funzione dalle due viste della dashboard per la colonna
`data_documento_prevista`. Questo cantiere le aggiunge la **serie**.

⛔ **Decisione di Tid: il problema non è la rottura.** La firma nuova si disegna
**tenendo conto di entrambe le esigenze**, in una volta sola — non si sceglie la
forma comoda per questo cantiere lasciando all'altro il compito di adattarsi.

| chi chiama | che cosa ha in mano | che cosa deve ottenere |
| --- | --- | --- |
| `fn_get_or_create_fattura_header` | registro, **serie**, competenza del lotto, data dichiarata | la data **definitiva** che il documento porterà |
| le due viste della dashboard | registro e **serie** (`fn_resolve_registro_documento`), competenza del gruppo, nessuna data dichiarata | la **stessa** data, come previsione |

⇒ **una firma sola**:

```sql
vendite.fn_calcola_data_documento(
    p_registro_id     vendite.registri_fatturazione.id%TYPE,
    p_competenza_mese vendite.fatturazione_lotti.competenza_mese%TYPE,
    p_serie           vendite.fatture.serie%TYPE,                    -- ⛔ SENZA default
    p_data_dichiarata vendite.fatturazione_lotti.data_documento%TYPE DEFAULT NULL
) RETURNS date
```

⛔ **`p_serie` sta in TERZA posizione, non in coda**, e la forma scritta sopra
prima della stesura era **illegale**: in PostgreSQL i parametri con `DEFAULT`
stanno per ultimi, quindi un `p_serie` obbligatorio dopo `p_data_dichiarata`
non compila. Non e' un dettaglio di sintassi — cambia l'**ordine posizionale**,
e quindi ogni chiamata esistente. È il genere di cosa che si vede solo
scrivendo il `CREATE`.

* ⛔ **`p_serie` senza `DEFAULT`**: un default farebbe dimenticare il parametro, e
  la funzione leggerebbe il contatore della serie sbagliata rispondendo «nessun
  vincolo» — la risposta più permissiva possibile proprio dove il cancello poi
  rifiuta (▶ V-7). Chi chiama deve **decidere** cosa passare.
* ℹ️ `NULL` resta un valore **legittimo** e significa «la serie di default del
  registro»: si risolve con `COALESCE(p_serie, r.serie_default, '')`, la stessa
  risoluzione che usa chi numera. ⚠️ Se una delle tre risoluzioni diverge, cerca
  una riga di contatore che non esiste.
* ⭐ **Effetto buono per il gemello**: con il clamp la colonna
  `data_documento_prevista` mostra la data che il documento prenderà **davvero** —
  cioè diventa vera proprio nel caso che l'ha fatta nascere.
* ⚠️ **Coordinamento**: i due cantieri condividono `20260826-05`. Chi applica per
  primo scrive la firma nuova; l'altro la usa e basta.

---

### D-9 — la competenza è una proprietà del documento ✅ **DECISA: si fa, nel lotto A**

Nasce dall'obiezione di D-7. Il residuo che restava è **il mese sbagliato su un
documento non numerato**, e non lo chiude nessun trigger: un trigger su
`vendite.fatture.data` userebbe la **stessa deduzione dalla data**, perché su
quella riga la competenza non c'è.

⭐ **Si mette sulla riga**: `vendite.fatture.competenza_mese`, scritta alla
nascita dal lotto.

**Perché è più di una scorciatoia per chiudere D-7:**

* **è modello, non comodità.** La competenza è una proprietà del **documento
  fiscale**; il lotto è l'**attrezzo** che l'ha prodotto. Oggi un dato di dominio
  è raggiungibile solo attraverso un artefatto di lavorazione;
* **il cancello diventa stretto senza diventare fail-open.**
  `fn_assign_numero_fattura` **legge già** la riga della fattura per numerarla
  (`SELECT f.registro_id, f.data, … FROM vendite.fatture f JOIN registri_fatturazione r`):
  la competenza è **una colonna in più in una `SELECT` che c'è già**, e la RLS
  lavora nel verso giusto — se non vedi la riga non la numeri nemmeno;
* **c'è un solo scrittore.** Verificato: `fn_get_or_create_fattura_header` è
  **l'unico `INSERT INTO vendite.fatture` di tutto il repo**, e ha già la
  competenza in mano perché la usa per calcolare la data.

#### Come si scrive

| | |
| --- | --- |
| **colonna** | `competenza_mese date` **nullable**, su `vendite.fatture`. ⛔ Nessun indice: si legge sulla riga che si ha già in mano, per PK — un indice sarebbe una struttura che nessuno interroga |
| **chi la scrive** | `fn_get_or_create_fattura_header`, nella `INSERT` (DB-7). Il valore è già in `v_competenza_mese` |
| **backfill** | da `fatturazione_lotti_fatture` → `fatturazione_lotti.competenza_mese`. ⚠️ Il modello ammette una fattura in **due lotti** (l'unico vincolo è `UNIQUE (lotto_id, fattura_id)`): la regola è **`MIN(competenza_mese)`**, la più vecchia, cioè la più severa — il permesso scade prima |
| **`NULL`** | legittimo (una fattura senza lotto è ammessa dal modello): chi legge **ripiega sulla deduzione dalla data**, che è la risposta di oggi. ⛔ Mai un errore: non c'è niente di rotto |
| **si scrive alla NASCITA e non si insegue** | se più tardi la fattura entra in un secondo lotto con un'altra competenza, la colonna resta quella di nascita. La competenza di un documento è decisa quando il documento nasce, non da chi lo raccoglie dopo |

⛔ **Non è `NOT NULL`, e la tentazione va nominata.** Il modello ammette oggi una
fattura senza riga di ponte, quindi un `NOT NULL` sarebbe un vincolo che il
backfill non sa soddisfare in tutti i casi. Se un domani si dimostrasse che il
ponte è obbligatorio, il `NOT NULL` è un passo separato — non si stringe un
vincolo nello stesso giro in cui si popola una colonna.

#### Che cosa cambia nel piano

* **DB-13** (nuova): colonna + `COMMENT` + backfill → **lotto A**;
* **DB-7**: la `INSERT` scrive anche `competenza_mese`;
* **DB-10**: `fn_get_next_progressivo` riceve `p_competenza_mese`, **obbligatorio
  e in terza posizione** — in PostgreSQL i parametri con `DEFAULT` stanno in
  coda, e `p_serie`/`p_fattura_id` ce l'hanno. ⛔ `DROP` + `CREATE`;
* **DB-14** (nuova): `fn_assign_numero_fattura` legge la colonna e la passa.
  Firma **invariata**;
* **DB-8**: la targa compone con `COALESCE(f.competenza_mese, fl.competenza_mese)`;
* ⭐ **BE e FE: niente.** Verificato: il backend chiama
  `fn_numera_fattura_opz_emessa`, la cui firma **non cambia**; nessun punto del
  backend chiama `fn_assign_numero_fattura` o `fn_get_next_progressivo`
  direttamente.

⚠️ **La deduzione dalla data resta scritta lo stesso**, come ripiego per il
`NULL`, ed è giusto: fa da rete quando la colonna non sa rispondere, senza essere
più la strada principale. ▶ V-3.
