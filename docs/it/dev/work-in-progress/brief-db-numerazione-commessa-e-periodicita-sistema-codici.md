# Brief DB — il codice commessa diventa leggibile, e il sistema codici impara il periodo

> **Destinatario:** team DB (`dev/db-tid`). Con due code al BE e una al FE (§10).
>
> **Origine.** Richiesta di Tid, 2026-08-29: *«la numerazione attuale del codice
> commessa non mi piace … sarebbe più utile una numerazione umana anche
> `CMM-2026-000000000` (progressivo) … il numero si dovrebbe resettare con il
> nuovo anno … abbiamo il sistema codici, non so se sia personalizzabile e nel
> caso se si possa mettere il programma che determina il calcolo».*
>
> **Stato al 2026-08-30: solo analisi, e le decisioni sono PRESE.** Nessun file
> scritto, nessun changeSet, niente applicato.
>
> ⛔ **Perimetro, deciso da Tid il 2026-08-30 e valido per tutto il cantiere del
> trasloco: cambia SOLO l'algoritmo di assegnazione del numero. Per i documenti
> che traslocano non cambia nient'altro** — stati, colonne, viste e liste restano
> quelli di oggi, e il momento dell'assegnazione pure. Dettaglio al §12.7.
>
> ✅ **2026-08-30 — tutte le decisioni sono prese, e il piano è scritto altrove:**
> [brief-db-registri-di-numerazione-emittente-e-trasloco](brief-db-registri-di-numerazione-emittente-e-trasloco.md).
> Questo documento resta l'**analisi**: le ragioni stanno qui, l'esecuzione là.
>
> ⭐⭐ **E la decisione D-3 ha cambiato il cantiere, non solo il codice: la
> commessa va sul motore dei registri, e quindi il §6 — la periodicità dentro
> `config.sistema_codici` — NON SI FA PIÙ.** Nessuno degli altri codici del
> sistema ha chiesto un reset annuale: senza la commessa, quella colonna e quella
> tabella contatore non hanno più un cliente. `config.sistema_codici` resta
> **esattamente com'è oggi**. Vedi §6, marcato superato.
>
> ⭐ **Dal 2026-08-29 il brief porta anche un difetto che non è suo** (§11): la
> domanda di Tid sull'emittente ha fatto emergere che **due emittenti possono
> condividere lo stesso registro di numerazione fatture**, e che il difetto è
> **muto** — nessun vincolo lo respinge. Da lì è uscita la verifica dell'intera
> famiglia dei documenti numerati (§12).
>
> ✅ **Tre decisioni prese il 2026-08-30, tutte da eseguire in cantieri a parte** —
> qui non si scrive una riga di quelle:
>
> 1. **§11** — `registri_fatturazione.emittente_soggetto_ruolo_id` diventa
>    `NOT NULL`, con il guard di coerenza fattura↔registro. È il **primo**.
> 2. **§12.5** — il **DDT passa al motore dei registri**, con un discriminante
>    `famiglia_documento` sul registro: reset annuale, cancello di monotonia ed
>    emittente arrivano in una volta sola, e i resi possono seguire.
> 3. **§12.5-bis** — il nome `registri_fatturazione` **resta**, e il debito si
>    dichiara in quattro sedi. Il rename è un cantiere suo, che non cambia
>    nessun comportamento.
>
> **Correlati:**
> [config.sistema_codici](/dbzero/config/tabelle/sistema_codici) ·
> [script.fn_generate_codice](/dbzero/script/manual/fn_generate_codice) ·
> [script.trgfn_config_sistema_codici_sync_gen_codice](/dbzero/script/funzioni/trgfn_config_sistema_codici_sync_gen_codice) ·
> [vendite.fn_get_or_create_commessa](/dbzero/vendite/manual/fn_get_or_create_commessa) ·
> [vendite.fn_get_next_progressivo](/dbzero/vendite/manual/fn_get_next_progressivo) ·
> [script.fn_data_operativa](/dbzero/script/manual/fn_data_operativa)

---

## 0. Le quattro domande, tenute separate

Erano tre; il 2026-08-29 ne è arrivata una quarta, e mescolarle è il modo di sbagliare il progetto.

| # | Domanda | Risposta breve |
| --- | --- | --- |
| **A** | Il codice commessa di oggi va bene? | **No**, e le ragioni stanno sul modello, non sul gusto (§2) |
| **B** | `config.sistema_codici` sa fare il reset annuale? | **No, e non può**: il suo contatore è una sequenza, e una sequenza non sa cos'è un anno (§5) |
| **C** | Ci si può mettere «il programma che determina il calcolo»? | **Sì, in una forma sola — e non è quella che serve qui.** Il calcolo di un codice non è un programma: è la **composizione di dimensioni dichiarate**. Vedi §6.2 e §13 |
| **D** | *(Tid, 2026-08-29)* Lo stesso problema c'è sulla numerazione **fatture**, se due emittenti usano lo stesso registro? | **Sì, ed è un buco vero: il modello lo ammette oggi.** Ma ⛔ **la soluzione non è allargare la UNIQUE**. §11 |
| **E** | *(Tid, 2026-08-30)* E se mettessimo **anche la commessa** sui registri, e la facciamo finita? | ✅ **Sì — ed è la risposta che semplifica di più.** Toglie di mezzo tutto il §6: il sistema codici non si allarga per niente, e resta ai soli **codici anagrafici**. §4/D-3 |

---

## 1. Cosa esiste oggi — struttura, non fotografia

Nel DB convivono **quattro** motori di numerazione, più un caso che non ne usa
nessuno. ⭐ Tre dei quattro sono la **stessa idea** ricopiata: le due righe
bespoke lo dichiarano nel proprio commento (§12.4).

| Motore | Formato da | Contatore | Periodo | Momento dell'assegnazione |
| --- | --- | --- | --- | --- |
| **Sistema codici** — `script.fn_generate_codice(tipo)` | `config.sistema_codici` (prefisso, separatore, lunghezza) | sequenza `<schema>.<tabella>_<colonna>_seq` | ⛔ nessuno | `BEFORE INSERT` su un trigger **generato** da `trgfn_config_sistema_codici_sync_gen_codice` |
| **Registri fiscali** — `vendite.fn_get_next_progressivo` | il registro | tabella `vendite.registri_fatturazione_progressivi` (registro, anno, mese, serie) | ✅ annuale | all'**emissione**, sotto advisory lock, con pavimento data |
| **DDT** — `vendite.trgfn_ddt_gen_numero_emesso` | `config.sistema_codici` riga `ddt` (`usa_sequenza = false`) | sequenza propria `vendite.ddt_numero_seq` | ⛔ nessuno | alla transizione a `EMESSO` |
| **Resi** — `vendite.trgfn_resi_gen_numero` | `config.sistema_codici` riga `reso` (`usa_sequenza = false`) | sequenza propria `vendite.resi_numero_seq` | ⛔ nessuno | alla transizione a `CONFERMATO` |
| **Commessa** — dentro `fn_get_or_create_commessa` | ⛔ niente: hardcoded nel corpo della funzione | ⛔ nessuno: `clock_timestamp()` + `md5(random())` | — | `INSERT` |

⭐ **Il DDT ha già detto la cosa importante.** `config.sistema_codici` sembra un
motore unico, ma contiene **tre cose diverse**, e il DDT ne prende una e lascia
le altre due:

1. il **formato** (prefisso, separatore, larghezza) — genuinamente generico, ed è
   quello che il DDT riusa;
2. il **contatore** (una sequenza derivata da schema/tabella/colonna) — generico
   ma rigido: uno per colonna, per sempre, senza periodo;
3. il **momento** (`BEFORE INSERT`, via trigger auto-generato) — una **policy**,
   che va bene al soggetto e non va bene al DDT né alla fattura.

Questo cantiere tocca **solo il punto 2**. Il formato resta dov'è, il momento
della commessa resta l'INSERT.

---

## 2. Perché il codice di oggi è sbagliato — sul modello, non perché è brutto

```sql
v_codice := 'CMM-' || to_char(clock_timestamp(),'YYYYMMDDHH24MISSMS')
                   || '-' || substr(md5(random()::text), 1, 6);
```

**a. Non è un codice, è un identificatore tecnico.** Dice *quando è nata la
riga* — un'informazione che la tabella ha già, in `data_insert`, con il tipo
giusto. Un codice serve a **nominare** una commessa: questo la **timbra**.

**b. La `md5` è un rimedio a un difetto che il modello non ha — e ne introduce
uno che il modello ha.** Quei 6 caratteri servono a evitare la collisione fra
due INSERT nello stesso millisecondo. Ma la collisione **è già impedita**, da
`uq_commesse_codice`: la differenza è che il vincolo la trasforma in un errore,
mentre il random la rende *improbabile*. ⛔ **Un'unicità probabilistica sotto un
vincolo deterministico**: il caso resta possibile, e quando capita esce un
`23505` nudo, senza retry e senza codice di dominio, in mezzo a un fan-out. È
esattamente la forma «oggi non capita mai» che non decide niente.

**c. Non è confrontabile da un umano.** 28 caratteri (`CMM-` + 17 di timestamp +
`-` + 6 di `md5`), di cui 6 di **puro rumore**, e i **primi 12 identici** per
tutte le commesse dello stesso giorno: per distinguerne due bisogna leggere dal
tredicesimo carattere in poi, cioè esattamente dove l'occhio non arriva.

> ⚠️ *(Corretto il 2026-08-30: qui c'era anche «in `ui.lista_colonna` la colonna
> è larga 10 su due liste su tre, quindi in lista si vede `CMM-202608…`». **Era
> sbagliato**: nel CSV il campo letto era `ordine_default`, non
> `larghezza_default` — che è **vuoto** su tutte e tre le righe. La larghezza in
> lista non è configurata, e non c'è nessun taglio da correggere. Resta come
> promemoria: un numero letto in un CSV senza intestazione va contato, non
> stimato.)*

**d. Non si detta al telefono, non si cerca, non si ordina.** Sono i tre usi per
cui un codice esiste.

**e. Il formato non è un dato.** È scritto dentro una funzione di dominio,
quindi non è né configurabile né uniforme con gli altri tredici codici del
sistema — e il pannello di configurazione del FE, che sa mostrare la regola di
ogni codice, per la commessa non ha niente da mostrare.

### ⚠️ Ma una cosa quel codice la fa bene, e va detta prima di toglierla

**Non serializza niente.** `clock_timestamp()` e `md5()` non prendono nessun
lock: mille commesse create in una transazione di fan-out non aspettano nessuno,
e due sessioni concorrenti non si vedono. **Qualunque progressivo un lock ce
l'ha.** È il prezzo del cantiere, ed è quantificato al §5 — non è una ragione
per non farlo, è una cosa che va scritta prima e non scoperta dopo.

---

## 3. ⭐ L'invariante che decide tutto il resto

> **Ogni dimensione del contatore deve comparire nella stringa del codice.**

⚠️ **Formulazione precisa al §11.5**, dopo il caso delle fatture: quello che deve
portare tutte le dimensioni è la **chiave d'identità del numero**. Per la
commessa le due cose coincidono — l'identità *è* la stringa nuda
(`uq_commesse_codice`) — ed è per questo che qui la frase si può dire così.

Se il contatore riparte da 1 a ogni anno e l'anno **non** è nel codice, il
secondo anno riproduce i codici del primo: `uq_commesse_codice` li respinge, e la
creazione commesse si ferma. Non è una convenzione di stile: è la condizione di
esistenza del reset.

Il corollario vale in tutte e due le direzioni, e risponde da solo a una domanda
che altrimenti sembrerebbe estetica (§4, D-3): **se il contatore fosse per
emittente, l'emittente dovrebbe stare nel codice.** Non «sarebbe più chiaro»:
*dovrebbe*, o il vincolo salta.

⭐ È anche la ragione per cui al §6.2 il formato **non diventa un template**: se
il codice si compone per regola, l'invariante è vero **per costruzione** e non
serve nessun guard a difenderlo. Se diventa una stringa che qualcuno scrive in
un campo, serve un parser, un guard, un codice errore e i suoi test — tutti per
riparare una libertà che nessuno ha chiesto.

---

## 4. Le decisioni — ✅ **tutte prese il 2026-08-30**

> Le quattro voci qui sotto sono nate come domande aperte il 2026-08-29 e hanno
> avuto risposta il giorno dopo. **Restano scritte con l'argomento intero**: una
> decisione senza il suo perché è un'opinione con una data.

### D-1 — ✅ **Una regola sola: l'anno è quello della DATA DEL DOCUMENTO**

> ✅ **DECISO (Tid, 2026-08-30):** *«dipende da come fa la fattura; per il DDT
> serve recuperarlo dalla data del documento; le altre non sono fiscali, ma
> possiamo usare la stessa regola per tutti».*
>
> ⭐ **Regola unica, e la fattura è già la sua implementazione:**
> `vendite.fn_get_anno_registro(data documento)`. Per gli oggetti che una data
> documento **non ce l'hanno** — la commessa — la data del documento **è la data
> di creazione**, presa da `script.fn_data_operativa()`.
>
> ⚠️ Non è un'eccezione travestita: è la stessa regola applicata a un oggetto che
> nasce e si data nello stesso istante. ⛔ E il punto pratico che ne discende vale
> per DDT e ordini: l'anno **si ricalcola quando si assegna il numero**, non
> all'`INSERT` — vedi §12.5, condizione 5.

⛔ **Mai `now()` / `current_date`**: `script.fn_data_operativa()` esiste apposta e
dà la data di oggi **nel fuso dell'azienda**, letta da `config.parameters`, con
fail-loud se il parametro manca.

Resta la domanda vera: l'anno è quello **della creazione** o quello di una data
**di dominio**? La fattura usa la data documento (`fn_get_anno_registro(p_data)`),
perché una fattura una data ce l'ha e la sceglie una persona. **La commessa no**:
ha `competenza_dal`, che è nullable, e non ha nessuna data che qualcuno dichiari.

→ **L'anno è quello della creazione**, e `fn_generate_codice` se lo prende da sé.
⭐ Conseguenza pratica non secondaria: **la firma non cambia**, quindi niente
overload — un parametro in più su una funzione con DEFAULT rende ambigue le
chiamate esistenti, e i chiamanti sono quattro (due trigger generati, due service
Django).

### D-2 — ✅ **No, e ora non è più nemmeno una scelta**

> ✅ **Risolta dal motore.** Con tutto sui registri, la risposta la dà il motore
> che si è scelto: i registri i buchi ce li hanno (un rollback consuma il numero e
> non lo restituisce), e la **fattura** li ha sempre avuti. Non c'è una seconda
> semantica da inventare per la commessa.
>
> ⚠️ Resta **da scrivere**, però: nel `COMMENT` della colonna e nella doc
> manuale. Un codice che *sembra* contiguo genera la domanda «dov'è il 7?», e la
> risposta sbagliata a quella domanda è una serializzazione globale.

⛔ **No.** Un rollback consuma il numero e non lo restituisce: il buco resta. Il
progressivo è **ordinabile**, non **contiguo**.

Va scritto nel `COMMENT` della colonna e nella doc manuale, e non è pignoleria:
un codice che *sembra* contiguo genera la domanda «dov'è il numero 7?», e la
risposta sbagliata a quella domanda è una serializzazione globale su tutto l'ERP.
La commessa **non è un documento fiscale**: nessuna norma le chiede la
contiguità.

### D-3 — ✅ **Né l'uno né l'altro: la commessa va sui REGISTRI**

> ✅ **DECISO (Tid, 2026-08-30):** *«tagliamo la testa al toro, mettiamo anche la
> commessa nei registri e la facciamo finita».*
>
> ⭐⭐ **È la decisione che semplifica di più, e la sua conseguenza più grossa è
> una sottrazione: il §6 non si fa.** Tutta la periodicità dentro
> `config.sistema_codici` — la colonna, la tabella contatore, il ramo periodico
> della funzione, il guard di transizione — esisteva per **un solo cliente**, la
> commessa. Spostata quella, nessuno degli altri codici chiede un reset annuale:
> `config.sistema_codici` **resta esattamente com'è**, e il criterio della guida
> (§12.6-bis) diventa netto: *codici anagrafici lì, tutto ciò che ha un anno o un
> emittente sui registri.*
>
> ⭐ **E il cancello di monotonia non va disattivato: si spegne da solo.** Il
> pavimento di sequenza esce da `ultima_data` del contatore e quello di emissione
> dalle colonne `limite_emissione_*`: su un registro di famiglia `COMMESSA`
> nessuno dei due è valorizzato, `fn_get_pavimento_data_documento` risponde
> «nessun vincolo» — che è un caso che quella funzione **documenta già**. Nessun
> ramo nuovo dentro il motore fiscale.

#### ⚠️ Le tre conseguenze da mettere in conto, e nessuna è un ripensamento

1. ⛔ **La commessa non nasce se manca il registro.** Oggi nasce sempre. Con i
   registri, un emittente senza riga di registro `COMMESSA` **ferma il fan-out**
   di fatturazione. È fail-closed, cioè il verso giusto — ma è un comportamento
   **nuovo**, e va nel collaudo prima che in produzione.
2. ⚠️ **`commesse.codice` è `varchar` con `UNIQUE` sulla stringa nuda**, mentre
   il registro consegna un **numero**. Il cantiere deve decidere se la commessa
   prende `registro_id`/`anno`/`numero` come il DDT (e la `UNIQUE` diventa quella
   dei documenti) oppure se tiene il solo `codice` composto. ⛔ È la stessa
   domanda del §12.5 condizione 3, e ha la stessa risposta obbligata: **le
   dimensioni del contatore e quelle della chiave devono coincidere**.
3. ⚠️ **La serializzazione resta quella del §5**, invariata: il fan-out prende il
   lock sul contatore. Non è un costo nuovo del trasloco — è il costo di avere un
   progressivo, e vale con qualunque motore.

#### 📌 Superato — il ragionamento che ha portato qui

*(Le due sezioni che seguono — «globale contro per emittente» e la rev del
2026-08-30 sul prefisso — sono **superate dalla decisione qui sopra**. Restano
perché sono l'argomento che l'ha prodotta: la sigla dell'emittente portava la
commessa fuori dal motore generico, e una volta ammesso questo, la domanda
«dentro o fuori» aveva già una sola risposta sensata.)*

Le commesse hanno la **RLS** attiva (`rls_commesse_ef_whitelist`, FOR ALL, scope
per emittente). Con un contatore **globale**, ogni emittente vede una serie
**piena di buchi**: i numeri consumati dagli altri sono invisibili, non
mancanti. È una conseguenza strutturale di «RLS + progressivo condiviso», non
un'ipotesi sui dati.

| | Globale | Per emittente |
| --- | --- | --- |
| Forma | `CMM-2026-000123` | `CMM-<sigla>-2026-000123` — la sigla **deve** esserci (§3) |
| Serie vista dall'operatore | con buchi | pulita |
| Prerequisito | nessuno | ✅ **nessuno: la sigla esiste già** — `anagrafiche.emittenti_fiscali.codice`, `NOT NULL`, `UNIQUE (uq:codice)`, con `chk_emittenti_fiscali_codice_non_vuoto`; e `uq_emittenti_fiscali_ruolo` rende la relazione con il `soggetto_ruolo` **1:1**, quindi dall'emittente della commessa la sigla si raggiunge in modo deterministico |
| Costo nascosto | — | codice di lunghezza variabile: l'ordinamento lessicografico funziona solo dentro lo stesso emittente |

⚠️ **Aggiornamento 2026-08-30 — questa decisione è quasi presa da un'altra
parte, e va confermata.** Il criterio adottato al §12.6 mette la commessa fra i
codici **anagrafici/interni**, cioè fra quelli il cui numero è un'**etichetta**;
e la §D-3 rev 2026-08-30 mostra che la sigla dell'emittente porterebbe la
commessa **fuori** dal motore generico. Le due cose insieme dicono «globale,
senza sigla». ⛔ Ma la D-3 resta formalmente **aperta**: una decisione presa per
conseguenza da due paragrafi diversi non è una decisione, finché nessuno la
scrive. **Serve un sì esplicito.**

⭐ **Proposta: globale.** Il codice commessa è una **chiave di sistema**, non un
numero di registro: la sua unicità è di installazione, e la serie senza buchi è
una promessa che il §D-2 ha già deciso di non fare a nessuno. Ma è una decisione
di dominio e la prende Tid — e va presa **adesso**, perché al §6 cambia sia la
tabella contatore sia la composizione.

#### ⭐ rev 2026-08-30 — «basta mettere il prefisso dell'emittente, no?»

*(Domanda di Tid. La risposta breve è: **è la scelta meno semplice delle due**, e
la ragione è strutturale.)*

**La sigla è buona**, e meglio di come la descriveva la riga di ieri:
`anagrafiche.emittenti_fiscali.codice` è `VARCHAR(32)`, `NOT NULL`, `UNIQUE`, ed
è **immutabile** — la protegge `trg_emittenti_fiscali_a10_lock_columns_upd`
(`trgfn_lock_columns('codice','CODICE_NON_MODIFICABILE')`). ✅ Quindi il caveat
sulla «fotografia» **cade**: quella sigla non può cambiare sotto ai codici già
scritti.

⚠️ **Ma la sua forma non è vincolata da niente**: nessun CHECK sul contenuto, 32
caratteri disponibili, e nulla vieta un `-` dentro la sigla. Un codice commessa
`CMM-<sigla>-2026-000123` può quindi arrivare a ~51 caratteri (dentro il
`varchar(64)` della colonna, ma al limite) e, con un trattino nella sigla, smette
di essere decomponibile a occhio — cioè perde proprio la proprietà per cui lo si
sta rifacendo. Chi sceglie la sigla deve **vincolarne la forma**, o accettare che
per qualche emittente il codice sia illeggibile.

⛔ **E c'è il vincolo che decide davvero: il sistema codici generico non sa
scoprire l'emittente della riga.** Il trigger che genera il codice chiama
`script.fn_generate_codice('commessa')` e basta: **la riga non gliela passa**.
Per un contatore (o una sigla) per emittente servirebbe che il generatore
generico leggesse `NEW.emittente_soggetto_ruolo_id` **e** traducesse quell'id in
sigla andando a leggere `anagrafiche.emittenti_fiscali` — cioè che il generatore
di codici di *tutto il progetto* imparasse a conoscere una tabella di anagrafica
delle vendite. È la stessa obiezione del §6.2 e del §13: una configurazione che
descrive *come raggiungere un dato* è un mini-ORM scritto dentro una riga di
tabella.

⚠️ **Precisato il 2026-08-30 (§12.6): questa obiezione vale per la SIGLA, non
per lo SCOPE.** Scomporre il *contatore* per emittente **si può** fare
genericamente — basta che nella chiave entri l'**id grezzo**, passato dal trigger
generato, e il generatore resta ignorante. È la **traduzione id → sigla** a
richiedere che conosca l'anagrafica. Il paragrafo qui sopra resta valido per ciò
che dice: la **sigla nel codice** porta la commessa fuori dal motore generico.

⛔ E non si aggira con «una riga di `sistema_codici` per ogni emittente»:
`sistema_codici` è indicizzata su (schema, tabella, colonna) e il trigger
generato è **uno per tabella** (`trgfn_<tabella>_gen_codice`). Due righe sulla
stessa tabella si contenderebbero lo stesso trigger.

**Quindi le strade sono due, e sono queste:**

| | **Globale, senza sigla** | **Per emittente, con sigla** |
| --- | --- | --- |
| Forma | `CMM-2026-000123` | `CMM-ACME-2026-000123` |
| Dove vive il generatore | ✅ dentro il sistema codici: **una colonna** (`reset_periodicita`) e la commessa entra nel motore generico | ⛔ **fuori**: generatore di dominio, come già fa il DDT (formato dal sistema codici, contatore e momento propri) |
| Serie vista dall'operatore | con buchi (gli altri emittenti, invisibili sotto RLS) | pulita |
| Da vincolare | niente | la forma della sigla |

⛔ **La terza combinazione — la sigla nella stringa e il contatore globale — va
scartata**, ed è la più facile da scegliere per sbaglio: **una sigla nel codice è
una promessa sulla serie**. Se `ACME-2026-000123` è seguito da
`ACME-2026-000127`, chi guarda legge «mancano quattro commesse ACME», e invece
quei numeri li ha presi un altro emittente. Un codice che mente è peggio di un
codice anonimo.

### D-4 — ✅ **Nove cifre**

> ✅ **DECISO (Tid, 2026-08-30): nove.**
>
> ⚠️ Con la commessa sui registri, però, **la sede del parametro cambia**: non è
> più `config.sistema_codici.lunghezza_numero` (che non si tocca più), ma il
> **formato con cui si compone la stringa** del codice a partire dal numero che il
> registro consegna. Il motore dei registri restituisce un **numero**, non una
> stringa: chi compone `CMM-2026-000000001` va deciso nel cantiere — ed è la
> stessa domanda che il DDT si porta dietro (§12.5).

`CMM-2026-000000000` sono **nove** cifre. Con il reset annuale, **sei** bastano a
un milione di commesse l'anno. È un parametro (`lunghezza_numero`), quindi la
scelta è libera — ma va detto che ⚠️ **`lunghezza_numero` è un *padding*, non una
*capienza***: `lpad` non tronca, quindi al superamento il codice **si allunga in
silenzio** e l'ordinamento lessicografico — l'unica ragione per cui si mettono
gli zeri — smette di funzionare senza che nessuno se ne accorga. È un difetto
del sistema di **oggi**, non di questo cantiere: registrato al §9.

---

## 5. Il costo, e perché il contatore in tabella vince comunque

Quattro substrati possibili per un progressivo che riparte ogni anno:

| Substrato | Reset periodico | Serializza? | Buchi | Funziona a Capodanno da solo? |
| --- | --- | --- | --- | --- |
| Sequenza unica *(sistema codici di oggi)* | ⛔ no | no | sì | — |
| Una sequenza **per periodo** | sì | no | sì | ⛔ **no**: servirebbe DDL a runtime — **già rifiutato** dal changeSet `20260204-03`, che l'ha tolto proprio da `fn_generate_codice` — oppure un job annuale che, se non gira, il 1° gennaio **ferma la creazione delle commesse** |
| `setval` a Capodanno | «sì» | no | sì | ⛔ **no**, e peggio: `setval` non è transazionale (un rollback non lo annulla) e una transazione aperta a cavallo della mezzanotte lo scavalca |
| **Tabella contatore** *(come `registri_fatturazione_progressivi`)* | ✅ sì | ⚠️ **sì, fino al commit** | sì | ✅ **sì**: la riga del periodo nasce al primo uso |

⭐ **Vince la tabella contatore.** Non perché sia gratis, ma perché è l'unico
substrato che a Capodanno funziona **senza che nessuno abbia acceso una
candela**: un progetto la cui correttezza dipende da un job schedulato che ha
girato è più debole di uno che si provvede da sé.

⛔ **E va detto chiaro, perché è la lettura sbagliata più probabile: si paga la
serializzazione e i buchi restano.** Chi legge «contatore in tabella» e capisce
«numerazione senza buchi» ha capito male. Il lock non serve alla contiguità:
serve al fatto che **una sequenza non sa cos'è un anno**.

⚠️ **Il lock si tiene fino al commit del chiamante**, non fino alla fine della
funzione. Dentro un fan-out che crea molte commesse in una transazione è **una
sola** acquisizione; fra due sessioni concorrenti, la seconda aspetta il commit
della prima. È lo stesso prezzo che il progetto **già paga** su
`registri_fatturazione_progressivi` per le fatture, che sono di più.

*(Se un giorno si misurasse contesa vera su questo punto, quella misura sarebbe
un **controesempio** e giustificherebbe la sequenza-per-periodo con provisioning
anticipato. È l'unico uso legittimo di una misura: smentire, non progettare.)*

---

## 6. 📌 [SUPERATA] La forma proposta per il sistema codici

> 📌 **SUPERATO dalla decisione D-3 del 2026-08-30 — non si esegue.**
> Questa sezione descriveva come insegnare il **periodo** a
> `config.sistema_codici`. Con la commessa spostata sui registri quel motore non
> ha più nessun cliente che chieda un reset: **`config.sistema_codici` non si
> tocca**. Resta scritta per due ragioni: è l'analisi che ha fatto capire *perché*
> una sequenza non può ripartire (§5), e sarebbe la strada da ripercorrere se un
> giorno un codice **anagrafico** — non un documento — chiedesse davvero un
> periodo.


### 6.1 Il modello dato — una colonna e una tabella

**Su `config.sistema_codici`, una colonna sola:**

```
reset_periodicita  text NOT NULL DEFAULT 'NESSUNA'
                   CHECK (reset_periodicita IN ('NESSUNA','ANNUALE'))
```

⚠️ `MENSILE` **non entra**. ✅ **E il dubbio di Tid (2026-08-30) è fondato, con
una ragione più forte di quella che c'era scritta qui**: sui registri `MENSILE`
**non è più ammesso** — il changeSet `20260825-16` ha ristretto
`chk_registri_fatturazione_reset` a **una voce sola, `ANNUALE`**, dopo aver
constatato che `NESSUNA` e `MENSILE` erano *dichiarate e non implementate*
(il contatore porta `mese = 0` fisso e `uq_fatture_numero` il mese non lo
contiene). ⛔ Ammetterlo qui avrebbe creato **due vocabolari divergenti per la
stessa nozione**, in due motori che stanno convergendo.
⚠️ E se un giorno servisse davvero, non basta riaprire un `CHECK`: serve il mese
nel contatore **e** nelle chiavi di unicità.

**Una tabella contatore nuova:**

```
config.sistema_codici_progressivi
  id                bigint  PK
  sistema_codice_id integer NOT NULL  FK -> config.sistema_codici(id)
  periodo_chiave    text    NOT NULL          -- '2026'  (e '-' quando NESSUNA)
  last_numero       bigint  NOT NULL DEFAULT 0
  UNIQUE (sistema_codice_id, periodo_chiave)
```

*(Con la D-3 «per emittente», qui entra una terza colonna nella chiave — ed è
la ragione per cui la D-3 va decisa prima di scrivere.)*

⛔ **Nessuna RLS su questa tabella**, e per la stessa ragione per cui
`fn_get_next_progressivo` legge il pavimento dal contatore e non da
`vendite.fatture`: un contatore letto sotto RLS tornerebbe **vuoto**, e un
contatore vuoto non dice «non lo so», dice **«riparti da 1»**.

⚠️ Tabella nuova ⇒ tre cose che non arrivano da sole:
GRANT ai ruoli applicativi dal loop `ci_apply` di `90_end`; seed **esplicito** in
`dbops.fk_index_policy` (gli indici FK sono opt-in); e i trigger
audit/`tx_id`/storico che non esistono fino al `ci_apply`.

### 6.2 La funzione — stessa firma, un ramo in più

`script.fn_generate_codice(tipo text)` resta **identica nella firma**: nessun
overload, nessun chiamante da toccare (i due trigger generati,
`contratti_service`, `offerte_service`).

* **`reset_periodicita = 'NESSUNA'`** → il comportamento di oggi, riga per riga:
  `nextval` sulla sequenza. ⭐ **Zero effetti sui tredici codici esistenti.**
* **`ANNUALE`** → periodo da `script.fn_data_operativa()`, e il numero da **una
  sola istruzione atomica**:

  ```sql
  INSERT INTO config.sistema_codici_progressivi (sistema_codice_id, periodo_chiave, last_numero)
  VALUES (v_id, v_periodo, 1)
  ON CONFLICT (sistema_codice_id, periodo_chiave)
  DO UPDATE SET last_numero = config.sistema_codici_progressivi.last_numero + 1
  RETURNING last_numero
  ```

  ⭐ Una sola istruzione: crea la riga del periodo la prima volta e la incrementa
  tutte le altre. Nessun `SELECT … FOR UPDATE` preceduto da un `IF NOT FOUND`,
  cioè nessuna corsa fra «cerco» e «creo». ⚠️ Nel `DO UPDATE` si somma sulla
  **tabella**, non su `EXCLUDED` (che vale 1 e riporterebbe il contatore
  indietro).

* **La composizione, per regola e non per template:**
  `prefisso || separatore || [periodo || separatore] || lpad(numero, lunghezza_numero, '0')`

⭐ **Niente colonna `formato`, niente segnaposto.** È la risposta alla domanda C
del §0, ed è la parte del brief su cui vale la pena discutere: il calcolo di un
codice **non è un programma**, è la composizione di dimensioni dichiarate.
Renderlo un template comprerebbe una libertà che nessuno ha chiesto (per esempio
`2026-CMM-000001`, con l'anno davanti) e la pagherebbe con un parser, un
validatore, un codice errore, i suoi test **e** il guard del §3 — che senza
template semplicemente non serve. ⚠️ La perdita è dichiarata: l'ordine dei pezzi
è fisso.

⚠️ **`usa_sequenza` diventa un nome bugiardo** nel ramo periodico: sequenza non
ce n'è. ⛔ Non si rinomina — la colonna è nel CSV, la legge il BE
(`lookup_repository.get_sistema_codici`) e la legge il FE (`useCodiceField`, come
`isAuto`). Si rilegge per quello che il FE già ne fa: **«il codice lo genera il
DB»**. Va scritto nel `COMMENT`, o fra un anno qualcuno cercherà la sequenza che
non esiste.

### 6.3 Il trigger di sync

`script.trgfn_config_sistema_codici_sync_gen_codice` deve **smettere di creare la
sequenza** quando `reset_periodicita ≠ 'NESSUNA'`: una sequenza che nessuno
chiama è un oggetto che il prossimo lettore crede vivo. Il trigger `BEFORE
INSERT` sulla tabella bersaglio resta **identico**: cambia il contatore, non il
momento.

⛔ **E deve reggere il CAMBIO di `reset_periodicita` su una riga viva**, non solo
il valore iniziale. `NESSUNA → ANNUALE` lascia dietro una **sequenza orfana**, che
non va cancellata (è la sola memoria dei numeri già usati) ma va **dichiarata
tale**; `ANNUALE → NESSUNA` è la transizione vietata dal guard del §8. ⚠️ Un
trigger che guarda solo `NEW` e non il passaggio `OLD → NEW` non distingue i due
casi — ed è lo stesso trigger che oggi il passaggio lo guarda già, ma solo su
schema/tabella/colonna.

⚠️ Chi apre quella funzione ci trova dentro **due `DROP TRIGGER … ON
vendite.attivita_fatturabili_lotti` hardcoded**, residuo del ritiro fatto da
`20260804-50`. Non è di questo cantiere; è al §9 perché è impossibile non
vederlo.

### 6.4 La riga di catalogo e il ritiro del codice inline

⛔ **E prima del CSV c'è il LOADER, che è il passo che si dimentica.** Il mirror
`20250813-05-upsert-sistema_codici` elenca le colonne **una per una** (quindici,
in un blocco `columns:`): una colonna nuova nel CSV che non sia anche lì dentro
**non arriva nel database**, e non lo dice nessuno — il migrate passa, il valore
resta al default, e il ramo periodico non si accende mai.
⚠️ Quel changeSet **si può** modificare, ed è l'unico caso in cui modificare un
changelog già mergiato è la procedura giusta: è un mirror `runOnChange: true` con
`validCheckSums: ANY`, cioè fatto apposta per ri-eseguire quando cambia. ⛔ Ma va
fatto **nello stesso passo** in cui la colonna nasce, o si guarda una riga di CSV
che dice `ANNUALE` mentre il DB dice `NESSUNA`.

* **Append a `80_data/sql/config/sistema_codici.csv`**: `id 20`, `commessa`,
  prefisso `CMM`, separatore `-`, `lunghezza_numero` da D-4, `usa_sequenza = t`,
  `reset_periodicita = ANNUALE`, `vendite` / `commesse` / `codice`.
  ⛔ **Append a mano**, mai con `csv.writer`: pianta un CRLF che uccide il
  migrate e non si vede nel diff.
  ⚠️ `uq_sistema_codici_prefisso` è UNIQUE: `CMM` dev'essere libero — nel CSV di
  oggi lo è (i prefissi presi sono PRV, LTF, SGT, BAC, IFO, ORD, DDT, CNT, FORN,
  PRA, OFC, RESO, VET).

* **`fn_get_or_create_commessa`**: sparisce la riga `v_codice := …` e `codice`
  **esce dalla INSERT** — lo mette il trigger generato.
  ⚠️ `commesse.codice` è `NOT NULL`: il `BEFORE INSERT` scatta prima del vincolo,
  quindi regge — ma è esattamente il punto in cui un ordine di trigger sbagliato
  si vede **solo a runtime**, quindi va provato con un pgTAP che inserisce senza
  codice (§8).
  ⚠️ I `BEFORE ROW` scattano in **ordine alfabetico** e su `commesse` ci sono già
  quattro `a10_*`: il nuovo (`trg_commesse_a10_gen_codice_ins_upd`) cade fra
  `a10_default_emittente` e `a10_guard_emittente_ba`. Nessuno dei due legge il
  codice — ma questo va **verificato**, non assunto.
  ⭐ La firma non cambia: **nessun `DROP FUNCTION`**.

### 6.5 ✅ Le commesse che ci sono già — **non si rinumerano**

> ✅ **DECISO (Tid, 2026-08-30): nessuna rinumerazione del pregresso, per
> nessun numeratore** — né commesse, né DDT, né ordini.
>
> ⚠️ **Ne discende che due formati convivono per sempre**, e questo va
> argomentato invece che sperato: i codici vecchi non collidono con i nuovi non
> perché lo dica un vincolo, ma perché **hanno una forma diversa**
> (`CMM-<timestamp>-<md5>` contro `CMM-2026-000000001`; `DDT0000123` contro il
> formato nuovo). ⛔ Chi nel cantiere cambia il **formato** dei numeri nuovi sta
> toccando anche l'unica cosa che impedisce la collisione con i vecchi: se il
> formato nuovo potesse coincidere con uno vecchio, servirebbe il registro nella
> chiave a separarli — ed è di nuovo la condizione 3 del §12.5.
>
> ⚠️ E per il **contatore**: riparte da 1: i numeri già emessi non lo alzano.
> Voluto — ma va scritto, o sembrerà un difetto.

*(Superato: il paragrafo qui sotto proponeva la rinumerazione una tantum. Resta
per le verifiche che conteneva — nessuna FK punta a `commesse.codice`, e la
chiave di gruppo delle rettifiche usa l'**id** — che valgono comunque.)*

#### Il ragionamento superato

Restano con il codice vecchio: due formati convivono, e una lista ordinata per
codice diventa illeggibile. **Non siamo in produzione**, quindi la rinumerazione
una tantum è ammessa — ma prima:

⛔ **Va verificato che il codice non sia una chiave per nessuno.** Dalla lettura
del changelog: `commesse.codice` è UNIQUE ma **nessuna FK lo referenzia** (le
figlie usano `commessa_id`), e la chiave di gruppo delle rettifiche è
`'MAN:' || p_commessa_id`, cioè l'**id**. ⚠️ La verifica definitiva si fa su
`pg_constraint` **al momento di eseguire**, non su questo brief.

⚠️ La rinumerazione ordina per `id`, ricava l'anno da `data_insert`, riallinea
`last_numero` per ogni anno, e sta in **una** transazione — ⚠️ e va fatta **a
rubinetto chiuso**: una bonifica forward-only fotografa il minuto in cui gira.

⚠️ I codici vecchi vivono anche **fuori** dal DB: `test_fatturazione_giro_handler.py:57`
ne ha uno come costante (`CMM-20260610175449872-e059eb`). Il test non si rompe —
è un dato di fixture — ma la costante diventa una bugia storica: §10.

---

## 7. 📌 [SUPERATE] Le fasi del cantiere «periodicità nel sistema codici»

> 📌 **SUPERATE dalla D-3 (2026-08-30).** Le cinque fasi qui sotto costruivano il
> §6, che non si fa più. Il lavoro sulla commessa è confluito nel **cantiere del
> trasloco** (§12.5 / §12.6-bis), insieme a DDT e ordini, e le sue fasi si
> scrivono lì.
> ⚠️ Sopravvivono due voci, e vanno riportate nel cantiere nuovo: la **F4**
> (rinumerazione del pregresso — ✅ **decisa NO**, §6.5) e le **richieste BE/FE**
> del §10, che ora vanno riviste perché `useCodiceField` sul ramo periodico non
> esiste più.


| Fase | Contenuto | changeSet |
| --- | --- | --- |
| **F1** | `reset_periodicita` + `config.sistema_codici_progressivi` + guard di transizione (§8) | 3 |
| **F2** | `fn_generate_codice` con il ramo periodico + `trgfn_…_sync_gen_codice` che non crea la sequenza inutile | 2 |
| **F3** | Colonna nuova nel **loader** `20250813-05` + riga CSV `commessa` + ritiro del codice inline da `fn_get_or_create_commessa` | 2 (+1 se il loader si tocca a parte) |
| **F4** | Rinumerazione una tantum del pregresso — forward-only, a rubinetto chiuso | 1 |
| **F5** | BE/FE (§10) | — |

⚠️ F1 prima di F2 e F2 prima di F3 non è preferenza: `20_code` gira **prima** di
`80_data`, e la riga CSV con `reset_periodicita = ANNUALE` su una
`fn_generate_codice` che non conosce il ramo periodico produce codici **senza
anno** sul contatore nuovo. Le `preCondition` vanno messe.
⚠️ Numerazione `NN` **globale per data**, non per cartella.

---

## 8. 📌 [DA RISCRIVERE] I presidi (pgTAP)

> 📌 **Il bersaglio è cambiato con la D-3.** I presidi qui sotto verificavano
> `script.fn_generate_codice` sul ramo periodico, che non nascerà. Quelli che
> **restano validi**, spostati sul motore dei registri: la forma del codice
> generato, la progressione `N`/`N+1`, il **cambio di periodo** provato seminando
> la riga di contatore dell'anno prima (⚠️ il tempo non si simula), la nascita
> della commessa **senza codice**, `throws_ok` **con** SQLSTATE e il marcatore
> `PGTAP_RUNNER`. ⛔ Decade il guard di transizione `ANNUALE → NESSUNA`: era un
> presidio su una colonna che non si aggiunge più.


* **Forma**: il codice generato per `commessa` è `CMM-<anno di
  `fn_data_operativa()`>-<n cifre>` — l'anno si confronta con la funzione, non
  con una costante scritta nel test.
* **Progressione**: due chiamate consecutive danno `N` e `N+1` nello stesso
  periodo.
* **Il cambio di periodo**, che è il cuore del cantiere: ⚠️ `fn_data_operativa()`
  non è pilotabile da un test, quindi il tempo **non si simula**. Si prova
  **seminando a mano** la riga di contatore dell'anno scorso e verificando che
  l'anno corrente riparta da **1** — è il ramo vero, attraversato dal percorso
  vero.
* **La INSERT senza codice**: `INSERT INTO vendite.commesse (…)` senza `codice`
  passa e il codice arriva. È il test che protegge il §6.4.
* **Il guard di transizione** — ed è l'unico guard che serve davvero:
  `ANNUALE → NESSUNA` su un codice **già in uso** toglie l'anno dalla stringa e
  fa ripartire il contatore ⇒ **collisione garantita** con i codici già emessi.
  Va vietato quando esistono righe di contatore. ⭐ La direzione opposta
  (`NESSUNA → ANNUALE`) è invece **sicura**: l'anno entra nella stringa e i codici
  nuovi non possono somigliare ai vecchi.
* ⚠️ `throws_ok` **con** lo SQLSTATE (`P0001` per il dominio): senza, accetta
  qualunque errore, compreso quello di battitura del test.
* ⚠️ Provati **prima** del migrate girano per forza da owner: marcare
  `PGTAP_RUNNER` e motivarlo.

---

## 9. Difetti trovati per strada — **non** sono di questo cantiere

1. ⚠️ **`lunghezza_numero` è un padding, non una capienza**: superata la
   larghezza, il codice si allunga in silenzio e l'ordinamento lessicografico
   muore. Vale per tutti e tredici i codici, e nessuno se ne accorgerebbe.
2. ⚠️ **Due `DROP TRIGGER … attivita_fatturabili_lotti` hardcoded** dentro
   `trgfn_config_sistema_codici_sync_gen_codice`: residuo di `20260804-50`, si
   trascina a ogni revisione della funzione.
3. ⛔ **L'unicità probabilistica** del §2b: si chiude con questo cantiere, e va
   nominata perché è il modello a essere sbagliato, non il valore.
4. ⚠️ **`ddt.anno` e `ordini.anno` nascono da `CURRENT_DATE`** dentro i trigger
   `normalize`, all'`INSERT`. Sono due difetti in uno: la data non è quella
   dell'azienda (`script.fn_data_operativa()` esiste apposta), e l'anno è quello
   della **creazione** mentre il numero — quando arriverà dai registri — porterà
   quello della **data documento**. Dettaglio e cura al §12.5, condizione 5.

---

## 10. Richieste a BE e FE

*(Perimetro DB: qui si scrivono, non si fanno.)*

| # | Dove | Cosa |
| --- | --- | --- |
| **BE-1** | `apps/core/db/lookup_repository.py` → `get_sistema_codici` | esporre `reset_periodicita` nella SELECT |
| **BE-2** | `apps/vendite/tests/services/test_fatturazione_giro_handler.py:57` | la costante `CMM-20260610175449872-e059eb` diventa un formato che non esiste più |
| **FE-1** | `frontend/src/core/composables/useCodiceField.js` | ⛔ **L'anteprima diventa falsa.** Il composable compone `prefisso + separatore + lunghezza` per mostrare all'operatore la forma del codice: sul ramo periodico direbbe `CMM-000001` mentre il DB scrive `CMM-2026-000001`. O include il periodo, o l'anteprima non si mostra — una frase che il template afferma e il DB smentisce è peggio di nessuna frase |

---

## 11. ⭐ L'emittente e la numerazione delle fatture — la domanda di Tid del 2026-08-29

> *«se diversi emittenti usano lo stesso registro credo che l'univocità di
> numerazione salti, oppure dobbiamo prevedere che le tabelle abbiano
> sull'univocità anche l'id emittente — dico una cavolata?»*

**Non è una cavolata: il buco c'è, ed è esattamente dove dici.** Ma la diagnosi
va fatta fino in fondo, perché il rimedio che viene in mente per primo —
allargare la `UNIQUE` con l'emittente — **non chiude niente**, e da solo apre un
problema nuovo (§11.3).

### 11.1 Cosa dice il modello, letto sulla struttura

| Oggetto | Cosa contiene | L'emittente c'è? |
| --- | --- | --- |
| `vendite.registri_fatturazione.emittente_soggetto_ruolo_id` | il proprietario del sezionale | ⚠️ **c'è ma è NULLABLE** |
| `uq_fatture_numero` | `(registro_id, anno, COALESCE(serie,''), numero) WHERE numero IS NOT NULL` | ⛔ no |
| `uq_regprog_key` *(il contatore)* | `(registro_id, anno, mese, serie)` | ⛔ no |
| `vendite.fatture` | `emittente_soggetto_ruolo_id NOT NULL` | ✅ sì |

E soprattutto — è questo il punto che chiude la questione — la ricerca del
registro (`vendite.fn_lookup_registro_id`) ha una **gerarchia a quattro livelli**
il cui ultimo gradino è, testualmente:

```sql
WHEN r.utility_id IS NULL AND r.emittente_soggetto_ruolo_id IS NULL THEN 4
```

⛔ **Il quarto livello è il registro senza emittente: il sezionale condiviso da
tutti.** Non è un caso limite né un residuo, è un ramo **dichiarato** della
risoluzione. E ci si arriva anche per distrazione: chi chiama con
`p_emittente_soggetto_ruolo_id => NULL` (il parametro ha `DEFAULT NULL`) fa
corrispondere **solo** le righe con `r.emittente IS NULL`, cioè finisce sul
registro generico per costruzione.

⚠️ E non esiste **nessun** guard che leghi `fatture.registro_id` a
`fatture.emittente_soggetto_ruolo_id`: sui trigger di `vendite.fatture` c'è la
RLS (`trgfn_guard_emittente_scope`) e il «genitore attivo», e nient'altro. Il
registro e l'emittente della stessa fattura oggi **non si guardano**.

### 11.2 Cosa salta davvero — e cosa no

⭐ **L'unicità del numero NON salta.** Con il registro condiviso il contatore è
uno solo, quindi due numeri uguali non nascono: `uq_fatture_numero` non ha nulla
da respingere. **Ed è la parte peggiore**: non c'è nessun errore, nessun `23505`,
nessuna riga in `error_log`. Il difetto è **muto**.

⛔ **Salta l'attribuzione.** Due partite IVA diverse pescano dalla stessa serie:
l'emittente A si ritrova numerato 1, 4, 5, 9 — i mancanti li ha consumati B, e A
non li vede nemmeno (la RLS glieli nasconde). Nessuno dei due ha una propria
numerazione progressiva: ne hanno **mezza a testa**. Un sezionale IVA appartiene
a un soggetto passivo: condividerlo fra due non è una funzionalità, è un
incidente che il `NULL` in colonna rende possibile.

⚠️ E c'è un secondo effetto, sullo stesso registro condiviso: il **cancello di
monotonia** e il **limite di emissione** leggono `ultima_data` **del registro**.
Su un registro condiviso, la data dell'ultima fattura di A fa da pavimento a B:
un documento corretto di B viene rifiutato per colpa di una data di A.

### 11.3 ⛔ Perché mettere l'emittente nella `UNIQUE` non è il rimedio

Una `UNIQUE` **rileva** i duplicati, non **produce** la numerazione. Oggi
duplicati non ce ne sono (§11.2), quindi:

* aggiungere l'emittente a `uq_fatture_numero` la rende **più permissiva**, non
  più stretta: comincia ad ammettere lo stesso numero due volte sullo stesso
  registro, purché di emittenti diversi. ⛔ **Un vincolo allargato non può
  scoprire un difetto che quello stretto già non scopriva.**
* da sola non cambia **un solo numero generato**: il contatore resta condiviso,
  perché la chiave che conta è `uq_regprog_key`, non la `UNIQUE` sulle fatture.

⭐ **L'ordine giusto, se si va per questa strada, è l'inverso di quello che
sembra:** prima l'emittente entra nella chiave del **contatore**, e *solo allora*
la `UNIQUE` va allargata — altrimenti i due contatori producono lo stesso numero
e la `UNIQUE` stretta lo respinge. La modifica al vincolo è la metà **pericolosa**
e va per ultima.

### 11.4 Le due strade, e cosa costano davvero

| | **(1) Un registro appartiene a un emittente** | **(2) L'emittente entra nella chiave della numerazione** |
| --- | --- | --- |
| Come | `registri_fatturazione.emittente_soggetto_ruolo_id` → **NOT NULL** | emittente in `uq_regprog_key`, in `uq_fatture_numero`, nella chiave dell'advisory lock, nel pavimento |
| Oggetti da toccare | 1 colonna, 1 guard di coerenza, i livelli 2 e 4 del fallback, i dati dei registri generici | `registri_fatturazione_progressivi`, `uq_fatture_numero`, `fn_get_next_progressivo` (⚠️ **firma**: un parametro in più, e le chiamate posizionali si spostano — è già successo il 2026-08-26), `fn_get_pavimento_data_documento`, `fn_get_pavimento_sequenza`, `fn_assign_numero_fattura` |
| Il pavimento data | resta com'è: per registro **è** per emittente | ⛔ va reso per emittente anche lui, o A continua a bloccare B — cioè si riapre il cantiere chiuso il 2026-08-26 |
| Cosa consente in più | niente | un registro condiviso fra emittenti, con serie separate |
| È ciò che il modello già dichiara? | ✅ sì — la descrizione della tabella dice testualmente *«Registri/serie di numerazione per fatture di vendita (**per emittente/brand**)»*: è la colonna nullable a contraddire la doc | no |

> ✅ **DECISO da Tid il 2026-08-30: si va per la (1)** — `registri_fatturazione.emittente_soggetto_ruolo_id`
> diventa `NOT NULL`. ⛔ Resta un **cantiere a parte**: qui non si scrive niente.
> Da portare in quel cantiere, oltre alla colonna: il **guard di coerenza**
> fattura↔registro, la potatura dei livelli 2 e 4 del fallback di
> `fn_lookup_registro_id` (che senza il registro generico non hanno più un
> risultato possibile) e la **separazione dei registri generici esistenti**, che
> è dato e va fatta a rubinetto chiuso.

⭐ **Perché la (1)** — l'argomento che ha portato alla decisione qui sopra.
L'emittente **è già** una dimensione del registro: reso
obbligatorio, `(registro, anno, serie)` diventa per costruzione una chiave
*dentro un solo emittente*, e tutto il resto — contatore, `UNIQUE`, lock,
pavimento, le quattro funzioni appena stabilizzate — **non si tocca**. La (2)
spende molto per rendere *corretto* un caso (il sezionale condiviso) che non
serve a nessuno, invece di renderlo *impossibile*.

⭐ **E in tutte e due le strade serve comunque la stessa cosa, che oggi manca del
tutto: un guard di coerenza** «l'emittente della fattura è quello del suo
registro». È il pezzo che chiude il buco davvero; la (1) lo rende esprimibile in
una riga, la (2) non lo rende esprimibile affatto (senza emittente sul registro,
non c'è niente da confrontare).

⚠️ **Il prezzo della (1), dichiarato:** sparisce il registro «generico». Ogni
emittente vuole le proprie righe in `tipi_doc_fiscale_registri`, e un emittente
non configurato **non emette** — fail-closed e rumoroso, che è il verso giusto,
ma è configurazione in più e i registri generici esistenti vanno spezzati (dato,
da fare a rubinetto chiuso).

### 11.5 ⭐ E l'invariante del §3 regge, ma va letto giusto

Sembra una contraddizione — per la commessa l'anno **deve** stare nella stringa,
per la fattura l'emittente **no** — e non lo è. L'invariante non parla della
stringa visibile: parla della **chiave d'identità del numero**.

> Ogni dimensione del contatore deve comparire nella chiave che rende unico il
> numero.

* per la **fattura** l'identità è `(registro, anno, serie, numero)`: il registro
  è già dentro, quindi far coincidere registro ed emittente **materializza
  l'emittente nella chiave** senza scrivere una sigla da nessuna parte;
* per la **commessa** l'identità è `uq_commesse_codice`, cioè **la stringa nuda**:
  lì non c'è nessun'altra colonna a portare le dimensioni, e anno ed eventuale
  emittente devono stare **letteralmente nel testo**.

### 11.6 Perimetro

⛔ **Questo paragrafo non appartiene a questo cantiere.** Tocca la numerazione
fiscale, cioè `fn_get_next_progressivo`, `fn_assign_numero_fattura` e i due
pavimenti — roba stabilizzata il 2026-08-25/26 da
`brief-db-numerazione-data-documento-e-sequenza` e
`brief-db-limite-emissione-e-data-verificata`. Qui è **registrato**, con la
diagnosi e la proposta; va aperto come cantiere suo.

⚠️ *(Superata il 2026-08-30: «la decisione (1)/(2) va presa lì, prima di scrivere
una riga». La decisione è stata presa **qui**, il 2026-08-30 — è la (1), vedi il
riquadro nel §11.4. Nel cantiere resta da **eseguirla**, non da prenderla. La
riga resta perché era vera per un giorno, ed è la ragione per cui il §11.4 ha un
riquadro di decisione e non una proposta.)*

---

## 12. ⭐ La famiglia intera, verificata — e il difetto speculare di DDT, resi e ordini

*(Nasce dalla domanda di Tid del 2026-08-30: «lo stesso discorso vale per ordini,
preventivi ecc., tranne per il DDT — a questo punto dobbiamo verificare come
abbiamo fatto».)*

### 12.1 Come numera ciascuno, letto sulla struttura

| Documento | Chiave di unicità del numero | Contatore | `anno` nella chiave? | Il contatore riparte? | Emittente nella chiave? | Momento |
| --- | --- | --- | --- | --- | --- | --- |
| **fatture** | `(registro, anno, serie, numero)` | tabella contatore | ✅ | ✅ **annuale** | ✅ *via registro* — se la colonna diventa `NOT NULL` (§11) | emissione |
| **ddt** | `(anno, serie, numero)` | ⛔ sequenza unica perpetua `vendite.ddt_numero_seq` | ✅ | ⛔ **mai** | ⛔ no | `EMESSO` |
| **resi** | `(anno, numero)` | ⛔ sequenza unica perpetua `vendite.resi_numero_seq` | ✅ | ⛔ **mai** | ⛔ no | `CONFERMATO` |
| **ordini** | `(anno, serie, numero)` | ⛔ sequenza unica perpetua (sistema codici) | ✅ | ⛔ **mai** | ⛔ no | `INSERT` |
| **preventivi** | `(numero, rev)` | sequenza unica (sistema codici) | — | — | — | `INSERT` |
| **contratti** | `(numero)` | sequenza unica (sistema codici) | — | — | — | `INSERT` |
| **offerte** | `(codice)` | sequenza unica (sistema codici) | — | — | — | `INSERT` |
| **commesse** | `(codice)` | ⛔ nessuno: timestamp + `md5` | — | — | — | `INSERT` |

### 12.2 ⛔ Il difetto speculare: la chiave promette l'anno, il contatore non lo mantiene

Su **ddt**, **resi** e **ordini** la `UNIQUE` contiene `anno`, ma il numero
arriva da una sequenza che **non riparte mai**. Ne discendono due cose:

* l'`anno` nella chiave **non fa niente**: i numeri sono già distinti fra loro
  globalmente, quindi non c'è collisione che quella colonna possa evitare;
* ⛔ ma **dichiara** una numerazione per anno che il generatore non produce. Chi
  legge la chiave capisce «DDT 1/2026 e DDT 1/2027 sono due documenti diversi» —
  e invece il DDT n. 1 esiste una volta sola nella storia dell'installazione.

⭐ **È lo specchio esatto del problema della commessa.** Là il contatore
ripartirebbe e l'anno non sarebbe nella chiave; qui l'anno è nella chiave e il
contatore non riparte. **Stessa classe di difetto, verso opposto**, e la stessa
frase li copre entrambi: *le dimensioni del contatore e quelle della chiave
devono essere le stesse* (§3).

✅ La buona notizia: **la chiave è già dimensionata per il reset.** Il giorno in
cui si volesse la numerazione annuale su DDT, resi e ordini, non si tocca nessun
vincolo — si cambia solo il contatore, cioè esattamente il pezzo che questo
cantiere sta costruendo (§6).

### 12.3 L'emittente su DDT e resi è **peggio** che sulle fatture

Sulle fatture la condivisione fra emittenti è un **accidente di configurazione**:
la colonna sul registro esiste, è solo nullable (§11). Su **ddt** e **resi** è
l'**unico comportamento possibile**: c'è una sequenza sola, e la chiave di
unicità l'emittente non ce l'ha — eppure `ddt.emittente_fiscale_id` e
`resi.emittente_fiscale_id` sono entrambi `NOT NULL`. Il documento sa di chi è;
la sua numerazione no.

⚠️ **E qui la distinzione «non è fiscale» non copre il DDT.** La commessa,
l'ordine, il preventivo, il contratto e l'offerta sono documenti **interni**: una
serie condivisa fra emittenti è al più scomoda. Il DDT no — è il documento che
regge la **fattura differita**, deve portare una numerazione progressiva, ed è
riferito al cedente. Va trattato come il fiscale, non come la commessa.
⛔ Quanto sia stringente l'obbligo va confermato da chi lo conosce: qui si
constata solo che **il modello oggi non distingue**, e che il DDT è dalla parte
sbagliata della riga.

### 12.4 ⭐ Una cosa DDT e resi la fanno meglio della commessa: il momento

`trgfn_ddt_gen_numero_emesso` e `trgfn_resi_gen_numero` numerano alla
transizione di stato — `EMESSO` e `CONFERMATO` — e il commento dice perché:
*«no buchi da bozze DRAFT scartate»*. È il pattern giusto per un documento che
il numero lo deve **mostrare**.

⚠️ **Ordini, preventivi, contratti e offerte invece numerano all'`INSERT`**: ogni
bozza aperta e scartata brucia un numero. Non è un difetto di questo cantiere ed
è una **scelta**, ma va vista accanto alla D-2: sono i documenti dove i buchi si
notano di più, ed è lì che il momento dell'assegnazione — il terzo dei tre pezzi
del §1 — meriterebbe la stessa attenzione che ha avuto sul DDT.

### 12.5 ✅ Il DDT passa ai registri, con un discriminante fattura/DDT — **DECISO**

> ✅ **DECISIONE di Tid, 2026-08-30.** Il DDT smette di avere una numerazione
> propria e passa al motore dei registri, con un **discriminante di famiglia** sul
> registro. Il nome della tabella **resta** `registri_fatturazione`, e il debito
> si dichiara (§12.5-bis).
>
> ⛔ **Resta un cantiere a parte, e viene dopo il §11**: qui non si scrive niente.
> Questa sezione è il suo **seme**, non il suo piano: quando il cantiere si apre,
> si apre con un brief suo.
>
> ⛔⛔ **DA LEGGERE PRIMA DI SCRIVERE IL PRIMO CHANGESET DI QUEL CANTIERE:**
> **`uq_ddt_v_anno_serie_numero` deve guadagnare `registro_id` nello STESSO PASSO
> in cui il contatore acquista il registro.** Delle quattro condizioni qui sotto è
> l'unica che, dimenticata, **non degrada: rompe** — `23505` al primo DDT
> dell'anno del secondo emittente. Le altre quattro lasciano il sistema
> funzionante e incompleto; questa lo ferma. Dettaglio al punto **3**.

*(Nasce dalla proposta di Tid: «se per il DDT usassimo `registri_fatturazione`
integrando con un tipo documento? tanto alla fine la logica è la stessa».
**Non è una cavolata: è la direzione giusta**, e la verifica dice che costa molto
meno di quanto sembra.)*

**Il motore è già neutro rispetto al documento, e non per caso.** Verificato:

* `fn_get_pavimento_data_documento` legge **solo** il registro e il contatore —
  `vendite.fatture` non compare (i `%TYPE` su `fatture.data` sono riferimenti di
  tipo, non letture). È nato «sede unica» per **tre** chiamanti: il DDT sarebbe
  il quarto;
* il **limite di emissione** si spegne da sé: su un registro DDT le due colonne
  `limite_emissione_*` restano `NULL`, `fn_get_pavimento_emissione` non ha
  pavimento da dare e il `GREATEST` se la cava — è il caso «nessun vincolo» che
  la funzione **documenta già**;
* di `vendite.fatture`, in tutto il percorso felice di `fn_get_next_progressivo`,
  non si legge **niente**: la competenza arriva come parametro. Le fatture
  compaiono solo nel **ramo d'errore**, per comporre il bersaglio.

Quindi il lavoro vero non è «rifare il motore»: è **allargare il contesto** e
sistemare cinque cose.

#### Le cinque condizioni, e la terza è quella che, dimenticata, fa danni

*(Erano quattro fino al 2026-08-30: la quinta — l'**anno** — è uscita dalla
verifica su `ordini`, e vale per tutti e due.)*

1. **Il discriminante sul registro** — una colonna `famiglia_documento`
   (`FATTURA` | `DDT` | …) su `registri_fatturazione`. ⭐ È la forma buona della
   proposta, e ⛔ **non** quella di far entrare il DDT in
   `config.tipi_doc_fiscale`: verificato che `vendite.ddt` **non ha nessuna
   colonna di tipo documento**, e `tipi_doc_fiscale` è consumata da 83 file di
   `20_code` — chi la itera oggi può assumere «tipo doc fiscale ⇒ finisce in
   fattura». Il discriminante sta sul **registro**, dove è un fatto locale.
   ⚠️ E con lui serve un `CHECK` condizionato: `limite_emissione_*` e
   `politica_data_documento` sono regole **della fattura**, e su una riga `DDT`
   devono essere nulle per vincolo, non per abitudine.
2. **La risoluzione del registro DDT non passa da `tipi_doc_fiscale_registri`**
   — non può: quella mappa parte dal tipo documento fiscale, che il DDT non ha.
   ⭐ E non serve: con l'emittente `NOT NULL` (§11), il registro di un DDT è
   *«quello di famiglia DDT dell'emittente X»*, eventualmente raffinato per
   utility. Una riga per emittente, nessuna mappa.
3. ⛔ **`uq_ddt_v_anno_serie_numero` deve guadagnare `registro_id` — e nello
   STESSO passo del contatore.** È l'invariante del §3 di nuovo: se il contatore
   acquista la dimensione «registro», la chiave di unicità deve acquistarla
   insieme a lui.
   **Cosa succede se si dimentica**, e non è un'ipotesi: due registri DDT di due
   emittenti ripartono entrambi da 1, e la chiave `(anno, serie, numero)` non sa
   distinguerli. Il secondo emittente prende un **`23505` al primo DDT
   dell'anno** — cioè il DDT non si emette, la merce non parte, e l'errore è un
   violation di indice **senza codice di dominio**, che non dice a nessuno cos'è
   successo.
   ⚠️ **E l'ordine dentro il passo conta**: la `UNIQUE` va allargata **prima** che
   il primo numero esca dal contatore nuovo. Allargarla dopo significa dover
   ripulire a mano i duplicati già scritti — e i DDT numerati non si rinumerano.
   ⭐ **È l'unica delle cinque che non degrada: rompe.** Le altre quattro lasciano
   il sistema funzionante e incompleto (niente reset, un registro risolto male, un
   messaggio d'errore che parla di fatture, un anno incoerente); questa lo
   **ferma**. Va nella
   checklist di apertura del cantiere, non fra le rifiniture.
4. **Il ramo d'errore va reso agnostico**: il bersaglio cerca oggi l'ultima
   **fattura** numerata, e i codici si chiamano `E_FATTURA_*`. Servono i gemelli
   per il DDT (append al CSV dei codici errore) e un bersaglio che sappia di che
   documento parla.
5. ⛔ **`ddt.anno` va ri-derivato al momento del numero — oggi è un altro
   anno.** Verificato: la colonna la scrive `trgfn_ddt_normalize` **all'`INSERT`**,
   come `EXTRACT(YEAR FROM CURRENT_DATE)`. Il numero invece arriverà da un
   contatore la cui chiave porta l'anno **della data documento**. Sono **due
   nozioni di «anno» sulla stessa riga**, e la `UNIQUE` userebbe la prima mentre
   il contatore usa la seconda: è di nuovo l'invariante del §3, stavolta non sul
   *nome* della dimensione ma sul suo **valore**.
   Un DDT creato il 30/12 ed emesso il 3/1 lo mostra da solo: `anno = 2026`,
   numero preso dal contatore 2027.
   ⭐ La cura è già scritta altrove: `fn_assign_numero_fattura` calcola
   `v_anno := fn_get_anno_registro(v_data)` e lo scrive **nello stesso statement**
   del numero. Il DDT deve fare lo stesso.
   ⚠️ E già che si tocca: quel `CURRENT_DATE` va sostituito con
   `script.fn_data_operativa()` — è il fuso dell'azienda, ed è la regola stabilita.

#### Cosa si guadagna

Il reset annuale, il cancello di monotonia e l'emittente arrivano al DDT **in una
volta sola**, e la **terza copia** (i resi) può seguire la stessa strada. Oggi ci
sono tre implementazioni della stessa idea — `fn_assign_numero_fattura`,
`trgfn_ddt_gen_numero_emesso`, `trgfn_resi_gen_numero`, e le ultime due lo
dichiarano nel commento («mirror spirito fatture», «mirror ddt/fatture») —
ciascuna con pezzi diversi mancanti. **La duplicazione è già avvenuta**: qui non
si sta unificando per eleganza, si sta riportando indietro una copia che si è
persa dei pezzi per strada.

#### Ordine

⛔ **Dopo il §11.** L'emittente `NOT NULL` sul registro è il **prerequisito**:
senza, si estenderebbe al DDT lo stesso buco che si sta chiudendo sulle fatture.

### 12.5-bis ⚠️ Il debito dichiarato: il nome della tabella

> ✅ **DECISIONE di Tid, 2026-08-30: il nome `registri_fatturazione` NON si tocca,
> e il debito si scrive.** Questa sottosezione è la sede del debito: finché esiste,
> il debito è aperto.

**Cosa diventa falso, esattamente.** Dal momento in cui un registro numera anche
i DDT, il nome `vendite.registri_fatturazione` (e con lui
`registri_fatturazione_progressivi`, `fk_registri_fatturazione_*`, `pk_regfatt`,
`uq_regprog_key`) **nomina il contenuto sbagliato**: quella tabella non contiene
più solo registri di fatturazione, contiene **registri di numerazione**, di cui i
registri di fatturazione sono una famiglia.

**Perché non si rinomina adesso**, e non è pigrizia:

* rinominare una tabella significa rinominare **tutto ciò che ne dipende** —
  trigger, funzioni, viste, vincoli, indici, e i riferimenti nel backend e nel
  frontend. È un cantiere **più grande del miglioramento che accompagna**, e
  soprattutto **scorrelato**: non rende il DDT più numerato di prima;
* un rename mescolato a un cambio di comportamento produce un diff in cui **non
  si distingue più** ciò che è stato spostato da ciò che è stato cambiato. Sono
  due cantieri, e vanno letti separatamente;
* ⭐ e c'è un fatto che rende il debito più piccolo di come suona: **la
  descrizione della tabella dice già «registri/serie di *numerazione*»**. Il
  concetto che si sta allargando era già scritto giusto; è il nome dell'oggetto a
  essere rimasto indietro.

**Dove il debito deve essere visibile** — o non è un debito dichiarato, è un
difetto dimenticato:

1. nel `COMMENT` della tabella `vendite.registri_fatturazione`, in testa: *«il
   nome dice `fatturazione`, il contenuto è più largo — vedi la colonna
   `famiglia_documento`»*;
2. nel `COMMENT` della colonna `famiglia_documento`, che è il punto in cui il
   lettore incontra la contraddizione per la prima volta;
3. nella doc **manuale** della tabella (`dbzero/vendite/manual/`), che è dove si
   scrive il *perché* — l'auto-gen non lo può sapere;
4. qui.

**Quando si paga.** Il rename diventa opportuno quando lo si può fare **da solo**
e non c'è nient'altro in volo sulla stessa tabella. ⛔ E allora si paga per
intero: tabella, tabella dei progressivi, vincoli, indici, trigger e funzioni,
in un cantiere che non cambia **nessun** comportamento. ⚠️ Rinominare la tabella
e lasciare indietro i nomi dei vincoli sarebbe la forma peggiore: due nomi
contraddittori sullo stesso oggetto, invece di uno solo che è onestamente
vecchio.

### 12.6 ⭐ «E se mettessimo `emittente_id` nel sistema codici?» — preventivi, contratti, offerte, ordini

*(Domanda di Tid, 2026-08-30: «sono determinati tutti tramite un unico trigger; e
se nella tabella che gestisce questo standard aggiungessimo `emittente_id`, per
avere numerazioni separate per emittente? visto tra l'altro che viene eseguito
all'INSERT e perde già molti numeri».)*

#### ⚠️ Prima cosa: sono **due** lamentele, e sono indipendenti

I buchi e la condivisione non hanno la stessa causa.

* **I buchi vengono dal MOMENTO.** Il numero si consuma all'`INSERT`, quindi ogni
  bozza aperta e abbandonata ne brucia uno. È il difetto del §12.4.
* **La condivisione riguarda l'ATTRIBUZIONE**: di chi è la serie.

⛔ **Separare il contatore per emittente non toglie un solo buco**: dà *N* serie,
ciascuna con esattamente gli stessi buchi di prima, solo distribuiti. Anzi, li
rende **più visibili**, perché una serie corta con tre buchi si nota più di una
lunga con trenta. ⭐ **Lo scope ripara l'attribuzione, non la continuità** — e la
cosa che dà fastidio è la continuità.

#### ✅ Detto questo: lo scope per emittente **è** esprimibile nel sistema codici

⭐ **E qui correggo quello che avevo scritto al §4/D-3.** L'obiezione «il
generatore non vede la riga» vale per la **sigla**, non per lo **scope**:

* si aggiunge a `config.sistema_codici` una colonna **`colonna_ambito`** (il nome
  della colonna che porta l'emittente sulla riga). ⚠️ E serve davvero
  configurabile, non cablata: su `preventivi`, `contratti`, `offerte_commerciali`
  e `ordini` la colonna si chiama `emittente_fiscale_id`, su `commesse`
  `emittente_soggetto_ruolo_id`;
* il trigger generato — che è costruito con `format()` — passa
  `NEW.<colonna_ambito>::text` a `fn_generate_codice`;
* il contatore (§6.1) guadagna quel valore nella chiave.

✅ Il generatore riceve una **stringa opaca** e non conosce nessuna anagrafica:
la genericità regge. ✅ E il dato c'è già: su tutte e quattro le tabelle
`emittente_fiscale_id` è **`NOT NULL`**.

#### ⛔ Ma poi arriva la stessa trappola, per la terza volta in tre giorni

Se l'emittente scompone il contatore e **non compare nel codice**, due emittenti
generano `PRV0000123` tutti e due, e `uq_preventivi_numero_rev`,
`uq_contratti_numero`, `uq_offerte_commerciali_codice` li respingono: **`23505`**.
È l'invariante del §3, la stessa cosa già vista sul DDT (§12.5, condizione 3).

Le uscite sono due, e nessuna è gratis:

| | **(α) L'emittente entra nella CHIAVE** | **(β) L'emittente entra nella STRINGA** |
| --- | --- | --- |
| Come | `uq_preventivi_numero_rev` → `(emittente, numero, rev)`, e così le altre | il codice diventa `PRV-ACME-0000123` |
| Il codice resta | `PRV0000123` | più lungo, e leggibile |
| Costo | ⛔ **`PRV0000123` non identifica più un preventivo**: per trovarlo serve sapere anche di chi è. Ogni ricerca per numero, ogni link, ogni telefonata diventa ambigua | ⛔ serve la traduzione `id → sigla` **dentro** il generatore generico, cioè il generatore impara a conoscere `anagrafiche.emittenti_fiscali` — il mini-ORM nel dato già rifiutato (§6.2) |

⚠️ La fattura il costo (α) lo paga **perché deve**: il suo numero è unico dentro
il sezionale e basta, per obbligo. Un preventivo quel debito non ce l'ha, e
pagherebbe la stessa perdita senza nessuna contropartita esterna.

#### ⭐ La riga che conviene tracciare: **anagrafiche** contro **documenti**

È la terza volta in tre giorni che spuntano le stesse quattro dimensioni —
emittente, anno, serie, progressivo — e la domanda vera non è «aggiungiamo una
colonna?», è: **quanto si allarga `sistema_codici` prima di essere il motore dei
registri con un altro nome?**

I tredici codici a catalogo si dividono da soli:

| Famiglia | Codici | Cosa serve davvero |
| --- | --- | --- |
| **Anagrafici / interni** | `soggetto`, `billing_account`, `istanze_utilities`, `fornitori`, `vettori`, `pratica`, `lotti_fatturazione` (+ la **commessa**) | un'**etichetta univoca**, stabile e citabile. Nessun anno, nessuna serie, nessun emittente: il contatore unico è la risposta **giusta**, non un ripiego |
| **Documenti** | `preventivo`, `ordine`, `contratto`, `offerta_commerciale`, `ddt`, `reso` (+ `fattura`, che non è mai stata lì) | un **numero**, con emittente, anno, serie e un **momento** che non sia l'INSERT |

⭐ Il criterio non è «fiscale / non fiscale», è: **il numero è una promessa verso
l'esterno?** Se sì, vuole tutte e quattro le dimensioni, ed esiste già un motore
che le sa fare — quello dei registri, dove il DDT sta andando (§12.5). Se no,
`sistema_codici` va benissimo così com'è, più la periodicità del §6.

⚠️ **E si nota che il sistema codici lo dice già da solo**: ogni volta che un
documento ha voluto una dimensione in più se n'è **andato** — il DDT e il reso
sono usciti (numerano a stato, con sequenza propria), la fattura non c'è mai
entrata. Non è un caso: è che quel motore sa fare *una* cosa sola, un contatore
per colonna.

#### ⭐ Il criterio tecnico, in una riga sola

Fra le due dimensioni che sono state chieste al sistema codici in tre giorni —
il **periodo** (§6) e l'**emittente** (qui) — la differenza non è di gusto:

> **Il periodo il generatore se lo calcola da sé; l'emittente gli arriva dalla
> riga.**

E da lì discende tutto:

* il **periodo** è opaco e autosufficiente — `fn_generate_codice` lo prende da
  `fn_data_operativa()`, lo scrive nella stringa **per costruzione**, e
  l'invariante del §3 regge **senza toccare nessuna chiave di unicità di nessuna
  tabella**. Allargare `sistema_codici` di questa dimensione costa **una colonna**;
* l'**emittente** viene dalla riga, e nella stringa non ci finisce da solo: o si
  traduce (e il generatore impara l'anagrafica), o si sposta il peso sulle
  `UNIQUE` delle tabelle documento. In tutti e due i casi la modifica **esce dal
  sistema codici** e va a toccare il dominio.

⭐ **Perciò: chi vuole una dimensione che viene dalla riga — emittente, serie, o
un momento che non sia l'`INSERT` — non sta chiedendo un allargamento di
`sistema_codici`: sta chiedendo il motore dei registri**, e allora ci si sposta.

⚠️ **Aggiornato il 2026-08-30, e il risultato è più netto di come era stato
scritto qui.** La frase originale era *«`sistema_codici` impara il periodo, e si
fermi lì»*: valeva finché la commessa restava dov'era. Con la D-3 la commessa se
n'è andata, **e con lei l'unico cliente del periodo**: `sistema_codici` non
impara niente e **resta esattamente com'è**. Il criterio non cambia — cambia il
fatto che, applicandolo fino in fondo, di allargamenti non ne serve nemmeno uno.

#### La proposta — ✅ **e come è stata decisa il 2026-08-30**

> ✅ **Punto 2 accolto** (lo scope per emittente non entra nel sistema codici).
> ⏳ **Punto 1 rinviato**: sul **momento** di preventivi, contratti e offerte
> *«non modifichiamo nulla rispetto a ora»* — e l'**ordine** trasloca sui registri
> **tenendo** il momento di oggi (§12.6-bis). Quindi i buchi da bozza **restano**,
> su tutti e quattro: è una scelta, non una dimenticanza, e sta scritta qui perché
> il giorno in cui darà fastidio si sappia che era nota.

1. **Il difetto da curare su preventivi/ordini/contratti/offerte è il MOMENTO**,
   non lo scope: è quello che produce i buchi che danno fastidio.
   ⚠️ **E non è un cambio di trigger, è un cambio di modello**: verificato che
   `preventivi.numero`, `contratti.numero` e `offerte_commerciali.codice` sono
   **`NOT NULL`** — un documento non può esistere senza numero, quindi non lo si
   può numerare più tardi finché quella colonna non diventa nullable, con tutto
   ciò che ne segue su liste, ricerche e stampe.
   ⭐ **L'ordine invece è già pronto e non lo sfrutta**: `ordini.numero`, `.anno` e
   `.serie` sono **nullable** e la sua `UNIQUE` è già parziale
   (`WHERE numero IS NOT NULL`) — la struttura del DDT ce l'ha già, gli manca solo
   il generatore. È lo stesso mismatch del §12.2, in un altro punto.
2. **Lo scope per emittente si lascia fuori** da questi quattro, finché il numero
   resta un'etichetta: costa l'univocità globale (α) o la genericità del
   generatore (β), e non ripara ciò che dà fastidio.
3. Se un giorno un documento di questa famiglia dovesse davvero avere una serie
   per emittente, ⭐ **la decisione è già presa e basta estenderla**: esce dal
   sistema codici e va sul motore dei registri, come il DDT (§12.5).

### 12.6-bis ✅ Anche **`ordini`** trasloca sui registri — DECISO, e il motivo non è la simmetria

> ✅ **DECISIONE di Tid, 2026-08-30.** `ordini` va sul motore dei registri
> insieme al DDT — ✅ **e sono UN cantiere solo**, non due. Con loro va anche la
> **commessa** (D-3) e, subito dietro, i **resi** (✅ decisi il 2026-08-30:
> «seguono il DDT»).
> I motori restano **due**: `config.sistema_codici` — che a questo punto **non si
> tocca più** — e i registri.
>
> ⚠️ **Sul MOMENTO dell'ordine la decisione è: resta quello di oggi**
> («lo numeriamo come lo stato attuale»). Ne discende, e va detto chiaro:
> l'ordine guadagna **emittente e anno** ma **non perde i buchi** — ogni bozza
> continuerà a bruciare un numero, che adesso è un numero **di registro**.
> ⛔ E una conseguenza tecnica: sul registro di famiglia `ORDINE` il cancello di
> monotonia deve restare **spento** (nessuna `ultima_data` scritta), o un ordine
> in bozza con una data indietro bloccherebbe tutti gli altri.
> ⚠️ *Se invece intendevi «numeriamo l'ordine allo stato attuale del documento»,
> cioè a conferma, cambia il pacchetto: dimmelo e si riscrive questa riga.*

⭐ **La ragione buona, e conviene scriverla giusta perché «per simmetria» non
sarebbe una ragione**: l'ordine **è già strutturato come un documento numerato a
stato** — `numero`, `anno` e `serie` nullable, `uq_ordini_v_anno_serie_numero`
parziale su `WHERE numero IS NOT NULL`. Il modello dice una cosa e il generatore
ne fa un'altra: il trasloco non aggiunge una forma, **riallinea il generatore a
quello che la tabella dichiara già**.

⚠️ **Ed è un pacchetto: registro *e* momento insieme.** Un ordine che resta
numerato all'`INSERT` non guadagna niente a stare sui registri — pagherebbe la
configurazione (una riga di registro per emittente) senza prendersi né il reset
né la fine dei buchi. Lo stato in cui numerare è una decisione di dominio
(`config.stati_doc_ordini`: il candidato naturale è la conferma) e va presa nel
cantiere.

⚠️ **La coda vera è fuori dal DB**: un ordine in bozza vive **senza numero**. La
colonna è già nullable, quindi il DB regge — ma liste, ricerche, stampe e link
devono avere qualcosa da mostrare al posto del numero. È la stessa coda che il
DDT e i resi hanno già pagato: si guarda come l'hanno risolta invece di
inventarne una terza.

⛔ **E vale anche per l'ordine la condizione 5 del §12.5**: `ordini.anno` oggi lo
scrive `trgfn_ordini_normalize` all'`INSERT` da `CURRENT_DATE`. Se il numero
arriva a conferma, l'anno va **ri-derivato in quel momento**, o la chiave e il
contatore parlano di due anni diversi.

#### 📘 E si scrive nella guida — la parte che sopravvive ai cantieri

> ✅ **DECISIONE di Tid, 2026-08-30**: nella documentazione di
> `config.sistema_codici` (`docs/it/dbzero/config/manual/sistema_codici.md`, che è
> la doc **manuale** e quindi si può scrivere) va una sezione: **quando un
> numeratore va spostato sui registri**.

Deve contenere tre cose, e nient'altro:

1. **Il criterio**, che è quello tecnico del paragrafo precedente: *il periodo il
   generatore se lo calcola da sé; l'emittente, la serie e un momento diverso
   dall'`INSERT` gli arrivano dalla riga.* Chi chiede una dimensione che viene
   dalla riga sta chiedendo i registri.
2. **I tre campanelli**, in parole d'uso: «voglio che l'emittente X abbia la sua
   serie», «voglio che riparta ogni anno **ed** sia separata», «non voglio bruciare
   numeri con le bozze».
3. **La checklist del trasloco**, perché è sempre la stessa e ogni volta si
   riscopre: la colonna del numero dev'essere **nullable**; la `UNIQUE` deve
   guadagnare il **registro** nello **stesso passo** del contatore (⛔ o `23505`);
   l'**anno** va ri-derivato al momento del numero; il FE deve saper mostrare un
   documento **senza numero**.

✅ **DECISO (Tid, 2026-08-30): su `preventivo`, `contratto` e
`offerta_commerciale` non si cambia niente rispetto a oggi.** Restano sul sistema
codici, numerati all'`INSERT`, con il contatore unico.

⚠️ **Onestà sul risultato**: dopo commessa, DDT, ordini e resi, su
`sistema_codici` restano quei tre documenti — il loro numero è `NOT NULL` e
traslocarli comincia con un cambio di modello, non con un cambio di generatore.
**La riga fra anagrafiche e documenti si traccia adesso; si percorre a tappe**, e
la guida serve esattamente a far sì che la prossima tappa non debba ridiscutere
il criterio. ⭐ Il che rende la guida **più** utile, non meno: è l'unico posto in
cui resterà scritto perché tre documenti stanno da una parte e quattro
dall'altra.

### 12.7 Perimetro, e il quadro al 2026-08-30

⛔ **Niente di tutto questo è scritto: il brief resta un documento di analisi.**
Ciò che segue è il quadro delle decisioni, per il cantiere che verrà.

#### I due cantieri, in ordine

| | Cantiere | Contenuto | Stato |
| --- | --- | --- | --- |
| **1º** | **Emittente sul registro** (§11) | `registri_fatturazione.emittente_soggetto_ruolo_id` → `NOT NULL`, guard di coerenza fattura↔registro, potatura dei livelli 2 e 4 del fallback, separazione dei registri generici esistenti | ✅ deciso, **prerequisito di tutto il resto** |
| **2º** | **Il trasloco** (§12.5 · §12.6-bis · §4/D-3) — ✅ **UNO solo** | `famiglia_documento` sul registro + `DDT`, `ordini`, **commessa** e a ruota i **resi** | ✅ deciso |

#### Cosa è deciso, voce per voce

| Voce | Decisione |
| --- | --- |
| **D-1** — da quale data l'anno | ✅ **una regola sola**: la **data del documento** (`fn_get_anno_registro`); per chi non ce l'ha — la commessa — è la data di **creazione**, da `fn_data_operativa()`. E si **ricalcola quando si assegna il numero** |
| **D-2** — buchi | ✅ **ammessi**: lo dice il motore, non una scelta nostra. Da **scrivere** nel `COMMENT` e nella doc |
| **D-3** — commessa | ✅ **sui registri**, e quindi ⭐ **il §6 non si fa**: `config.sistema_codici` non si tocca |
| **D-4** — cifre | ✅ **nove** — ⚠️ ma il parametro cambia sede: è il **formato** che compone la stringa dal numero del registro |
| **F4** — pregresso | ✅ **nessuna rinumerazione**, per nessun numeratore. Due formati convivono; la non-collisione va **argomentata** (§6.5) |
| **ordini** — momento | ✅ **resta quello di oggi** (`INSERT`): guadagna emittente e anno, ⚠️ **non** perde i buchi. Cancello di monotonia **spento** su quel registro |
| **resi** | ✅ **seguono il DDT** |
| **preventivi / contratti / offerte** | ✅ **niente cambia**: restano sul sistema codici, numerati all'`INSERT` |
| **`MENSILE`** | ✅ **non ammesso** — e non per prudenza: sui registri il `CHECK` è già ristretto ad **`ANNUALE`** da `20260825-16` |
| **nome della tabella** | ✅ **resta** `registri_fatturazione`; debito dichiarato in quattro sedi (§12.5-bis) |
| **la guida** | ✅ si scrive in `docs/it/dbzero/config/manual/sistema_codici.md`: criterio, tre campanelli, checklist del trasloco (§12.6-bis) |

#### ⛔ Il perimetro del cantiere, in una riga — **decisione di Tid, 2026-08-30**

> **Cambia SOLO l'algoritmo di assegnazione del numero. Per i documenti che
> traslocano non cambia nient'altro.**

È la regola che chiude da sola quasi tutte le code rimaste, e va tenuta a vista
mentre si scrive, perché un trasloco è il momento in cui è più facile portarsi
dietro «già che ci siamo»:

| Coda | Chiusa dalla regola |
| --- | --- |
| In che stato numerare **DDT** e **resi** dopo il trasloco | ✅ **come oggi**: `EMESSO` e `CONFERMATO`. Non è una domanda |
| Il momento dell'**ordine** | ✅ **come oggi**: all'`INSERT`. ⚠️ Con la conseguenza già scritta al §12.6-bis — guadagna emittente e anno, **non** perde i buchi, e su quel registro il cancello di monotonia resta spento |
| Colonne, stati, viste, liste dei documenti che traslocano | ✅ **non si toccano** |
| Le code **BE/FE** del §10 | ✅ **decadute** con il §6. Resta un solo controllo, ed è lavoro non decisione: che il FE non mostri un'anteprima del codice **commessa**, che ora nasce altrove |

#### ✅ L'ultima domanda ha avuto risposta — **A**, 2026-08-30

> ✅ **DECISO (Tid, 2026-08-30): la sigla dell'emittente entra nel CODICE.**
> `uq_commesse_codice` resta intatta, e il codice continua a bastare da solo per
> trovare una commessa. Forma: `CMM-<sigla>-<anno>-<9 cifre>`.
> ⚠️ Con l'unica cautela che ne discende: **la forma della sigla va vincolata**
> (`emittenti_fiscali.codice` è 32 caratteri senza `CHECK`, e nulla vieta un `-`
> dentro). Il vincolo va messo nel cantiere.
>
> 📄 **Il piano è scritto**, e da qui in poi vive lì:
> [brief-db-registri-di-numerazione-emittente-e-trasloco](brief-db-registri-di-numerazione-emittente-e-trasloco.md).

*(Il ragionamento che ha portato alla A, che resta valido.)*

⛔ **Dove va l'emittente, nel codice della commessa?**

Non è una domanda in più: è la **conseguenza obbligata** di due decisioni già
prese. Il §11 rende il registro di **un solo emittente**; la D-3 mette la commessa
sui registri. Quindi il contatore della commessa è **per emittente**, e per
l'invariante del §3 l'emittente deve stare nella **chiave d'identità del numero**.
Oggi quell'identità è `uq_commesse_codice`, cioè **la stringa nuda**: se due
emittenti generano entrambi `CMM-2026-000000001`, il secondo prende un `23505`.

Le uscite sono due, e una sola lascia intatto tutto il resto:

| | **(A) La sigla entra nel codice** | **(B) L'emittente entra nella `UNIQUE`** |
| --- | --- | --- |
| Forma | `CMM-<sigla>-2026-000000001` | `CMM-2026-000000001`, ripetuto per emittente |
| `uq_commesse_codice` | ✅ **intatta** | ⛔ diventa `(emittente, codice)` |
| Trovare una commessa dal codice | ✅ basta il codice | ⛔ serve sapere anche di chi è |
| Costo | il codice si allunga | una colonna in più nella chiave, e un'ambiguità in ogni ricerca |

⭐ **Proposta: la (A)**, e c'è un motivo per cui adesso si può mentre ieri no:
**l'obiezione che la bloccava è caduta con la D-3**. La sigla richiedeva la
traduzione `id → sigla`, che il generatore *generico* non poteva fare senza
imparare l'anagrafica — ma la commessa dal generatore generico **se n'è andata**.
Sui registri quella traduzione la fa una funzione di dominio, che legge ciò che le
serve senza sporcare niente. E la fonte è solida: `emittenti_fiscali.codice` è
`NOT NULL`, `UNIQUE` e **immutabile**.
⚠️ Con una sola cautela già annotata: la sua **forma** non è vincolata da nessun
`CHECK` (32 caratteri, e nulla vieta un `-` dentro). Se si sceglie la (A), quel
vincolo va messo.

#### Passi che sono lavoro, non decisioni

* le **righe di registro** per gli emittenti esistenti (famiglie `DDT`, `ORDINE`,
  `COMMESSA`, `RESO`): senza, quei documenti non nascono. È dato, e va fatto nel
  cantiere prima di accendere il generatore nuovo;
* il **collaudo** del fail-closed: oggi la commessa nasce sempre, dopo no.

## 13. Cosa **non** si fa, e perché

* ⛔ **Il sistema codici non ASSORBE il motore dei registri.** Quel motore porta
  registro, serie, pavimento data, limite di emissione e monotonia: regole
  **fiscali**. Un generatore di codici che le imparasse diventerebbe il posto
  dove si numerano le fatture, e la prima modifica «innocua» al generico
  romperebbe il fiscale. I motori restano **due**, distinti, con il criterio del
  §12.6 a separarli.
  ⚠️ **Da non confondere con il §12.5/§12.6-bis, che vanno nel verso opposto e
  non contraddicono questa riga**: lì non si fondono i motori, si **spostano dei
  clienti** da uno all'altro. Il DDT e l'ordine cambiano motore; nessuno dei due
  motori impara le regole dell'altro. ⭐ È esattamente la differenza fra
  *unificare* e *smettere di duplicare*.
* ⛔ **Non si mette un nome di funzione in una colonna.**
  `config.sistema_codici` è **editabile dal pannello di configurazione del FE**
  (`frontend/src/core/config-tables.js`, riga 27): una riga di dato che nomina
  codice eseguibile è una via d'esecuzione arbitraria che parte dalla UI, e toglie
  a `pg_depend` e alla doc auto-generata la possibilità di sapere chi chiama chi.
  ⭐ **Se un giorno servisse davvero** un calcolo che il modello non compone, la
  forma esiste già ed è quella dei task: una **registry con FK a implementazioni
  registrate** (`dbops.pipeline_task_registry_impl`), non testo libero in un
  campo. È la risposta alla domanda C: *sì, si può — ma solo in quella forma, e
  per il codice commessa non serve, perché l'anno è una **dimensione**, non un
  **programma**.*
* ⛔ **Non si fa la numerazione senza buchi** (D-2).
