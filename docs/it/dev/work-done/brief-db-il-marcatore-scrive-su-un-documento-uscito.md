# Brief DB — il marcatore del pull scrive su un documento uscito dal giro

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-08. **A chi:** team DB.
> **Cantieri che si incontrano:**
> [uscita-documento-dal-giro](../work-done/brief-db-uscita-documento-dal-giro.md)
> e [esito-gruppo-lotto](../work-done/brief-db-esito-gruppo-lotto.md).
>
> **Stato:** 🟠 **RIAPERTO il 2026-09-09 sera** — §8. Era chiuso: DB consegnato
> (§6), backend adeguato e provato con la chiamata vera (§7), doc auto-gen
> rigenerata (§7.1). Poi i pgTAP hanno segnalato **due code lasciate indietro
> dalla consegna** e **una regressione** che questa consegna ha introdotto in
> un'altra funzione. Due voci aperte, entrambe in §8.4.
>
> **In una riga:** `fn_segna_esito_gruppo_lotto` marca **tutti** i documenti di
> una commessa, compresi quelli `ESCLUSO`. Il trigger dell'uscita rifiuta — e fa
> bene — ma il rifiuto **abbatte il rilancio**. ⇒ Il verbo che esiste per far
> ripartire un lotto lo rende impossibile da rilanciare.

---

## 1. Come è nato

Collaudo a video di Tid, 2026-09-08. Lotto **`LTF-0010263`**: tolto dal giro
`ORDINE_VENDITA:01a06ce4-b46a-…` — **riuscito**, esito `ESCLUSO` con motivo e
timbro — e premuto **«Rilancia step»**.

```
E_PIPELINE · http 400 · request_id 22868c56-a57b-4ebf-9838-c18a2aea1ca9
```

---

## 2. Che cosa abbiamo analizzato

La catena, dai log applicativi:

| # | Chi | Che cosa succede |
| --- | --- | --- |
| 1 | `fn_emit_attivita_fatturabili_da_commessa` | commessa 34137 fallisce — **atteso**, è il guasto del collaudo, e il fan-out lo isola |
| 2 | `_marca_esito_gruppi` (BE) | annota il fallimento: `fn_segna_esito_gruppo_lotto(lotto, 'ERRORE', commessa_id => 34137)` |
| 3 | `fn_segna_esito_gruppo_lotto` | risolve commessa → documenti e fa l'upsert su **tutti**, compreso quello uscito |
| 4 | `trgfn_fatturazione_lotti_esiti_uscita` | rifiuta: `E_LOTTO_DOC_USCITA_IRREVERSIBILE` |
| 5 | — | l'eccezione **esce** dal marcatore e diventa `E_PIPELINE` 400 |

**Tre cose verificate, perché cambiano il perimetro del problema:**

1. ⭐ **Il rifiuto è corretto.** `ESCLUSO` è terminale (D-3). Non chiediamo di
   allentarlo: è il **tentativo** a non doverci essere.
2. ⚠️ **La premessa del codice a catalogo non regge più.**
   `E_LOTTO_DOC_USCITA_IRREVERSIBILE` è `TECNICO` perché *«qui ci arriva solo un
   UPDATE diretto: la madre chiede prima alla sua check»*. Qui a scrivere è il
   percorso normale del backend.
3. ⛔ **Non si aggira ripristinando la ROOT di 34137.** Il trigger guarda la
   **direzione**: se il pull riuscisse, il marcatore scriverebbe `COMPLETED` su
   quel documento e il rifiuto sarebbe identico. Il lotto è fermo nei due versi.

⛔ **Non è un caso di nicchia: è la linea principale.** Si toglie dal giro un
documento *perché* il suo pull fallisce; al rilancio quel pull fallisce ancora,
il marcatore riprova, il giro muore.

⚠️ **E nessun pgTAP poteva vederlo**: i presidi provano le funzioni una per una,
questo nasce dalla **sequenza**.

---

## 3. ⭐ La regola esiste già, in due posti su tre

Il `20260908-07` ha insegnato al **conteggio** a scartare le critiche di un
documento uscito — è la ragione per cui su `LTF-0010263` `evaluate_lotto_status`
dice `critical = 0` mentre la critica è ancora lì. Il **trigger** lo sa. Il
**marcatore** no.

⇒ *Un documento fuori dal giro non si marca, non si conta, non blocca.*

---

## 4. ✅ Che cosa serviva — consegnato il 2026-09-09

> Le richieste qui sotto restano come **erano poste**; la risposta è il §6, e il
> consumo lato backend il §7. ⚠️ Il testo non si riscrive per farlo sembrare
> facile: la forma della domanda è metà del lavoro.

**Che il marcatore non tenti di scrivere su un documento che ha già lasciato il
giro.**

⚠️ **E non lo filtriamo dal backend**: sarebbe la terza sede di una regola che il
database possiede già in due punti, e la terza è quella che diverge.

### Due cose da decidere nello stesso giro, non dopo

1. ✅ **Distinguere i due zeri del marcatore** — e sono risultati **tre** (§6.7). Con lo scarto, una commessa il
   cui unico documento è uscito produrrà **zero righe marcate** — e il backend lì
   ha un avviso in servizio (`pull_commesse.esito_non_appeso`) che diventerebbe
   rumore su un caso legittimo. Ci serve separare «nessun documento appeso a
   questa commessa» (difetto) da «gli unici documenti sono usciti» (normale). La
   forma è vostra.
2. ✅ **La segnalazione critica per documento** — `20260909-21`: su un documento uscito non si scrivono `W` e `C`. Al rilancio il backend ne
   riscrive una per ogni documento della commessa fallita, compreso quello
   uscito. Non blocca — il conteggio la scarta — ma se ne accumula una a ogni
   rilancio su un documento che non è più in gioco. Va scartata anche lì, o è un
   fatto da registrare? È la D-6 vista dal lato di chi scrive.

---

## 5. Dove siamo intanto

`LTF-0010263` **non è rilanciabile**: l'unica via che il modello lascia è
annullare il lotto e rigenerare. ⚠️ Che è anche la misura di quanto pesa — il
verbo «togli dal giro» esiste per non dover annullare il lotto.

---

## 6. Risposta del team DB — 2026-09-09

### 6.1 ✅ La diagnosi regge tutta, verificata sugli oggetti vivi

| Affermazione | Esito |
| --- | --- |
| il marcatore fa l'upsert su **tutti** i documenti | ✅ la CTE `ammesse` filtrava solo per **perimetro**, mai per stato |
| il rifiuto del trigger è corretto | ✅ scatta solo su `OLD = 'ESCLUSO' AND NEW IS DISTINCT FROM OLD` |
| non si aggira ripristinando la ROOT | ✅ e per un motivo più forte: il trigger **non guarda il valore nuovo**, solo che cambi |
| «non è un caso di nicchia» | ✅ argomentato sul modello, non su un conteggio |

### 6.2 🔴 Il danno non era il documento uscito: era **tutta la commessa**

Il guard è `BEFORE ROW` e il marcatore fa **un solo**
`INSERT … ON CONFLICT DO UPDATE`. L'eccezione su una riga saltava l'**intero
statement**: restavano senza esito anche i documenti **sani** della stessa
commessa.

⇒ Ha una conseguenza diretta sulla forma del rimedio, ed è il motivo per cui il
filtro sta **dentro la CTE `ammesse`** e non in un controllo che precede: gli
altri devono passare. Un pre-check che solleva sposta il problema di due righe.

### 6.3 ⛔ `E_LOTTO_DOC_USCITA_IRREVERSIBILE` non si tocca — il §2.2 si chiude così

Il rilievo è giusto: la premessa del `TECNICO` («qui ci arriva solo un `UPDATE`
diretto») era smentita dai fatti. ⭐ Ma il rimedio la **ripristina**: tolto il
tentativo del marcatore, il trigger torna raggiungibile solo da un chiamante
rotto — che è esattamente ciò che `TECNICO` significa. Declassarlo a
`DATO_ERRATO` (400) farebbe sembrare un errore dell'operatore la violazione di
un invariante. **Nessun changeSet sul codice.**

### 6.4 ⛔ «Nessun pgTAP poteva vederlo» — no: nessuno lo **copriva**

La sequenza è scrivibile in pgTAP, e la fixture **esisteva già** in
`test-uscita-documento-dal-giro-v1.sql`: mancava la chiamata. *Un buco
dichiarato inevitabile è un buco che resta aperto.* Adesso c'è, ed è la
giuntura: **test 19 e 20**.

### 6.5 ⚠️ La regola è scritta a mano in quattro punti, e questo è il quinto

`'ESCLUSO'` è un letterale in `trg_…_a10_uscita`, `fn_escludi_documento_da_giro`,
`fn_check_documento_escludibile_da_giro` e `fn_get_lotto_segnalazioni_summary`.
Il §3 dice «in due posti su tre»: sono quattro, e il rimedio ne fa cinque.

⭐ **E lo stesso dominio tratta l'asse gemello nel modo opposto, di proposito**:
il confine pre-fiscale ha un flag (`config.stati_doc_fiscale.congela_fiscale`,
letto fail-closed) e il commento di `fn_check_documento_escludibile_da_giro`
scrive *«mai un elenco di stati scritto a mano»*. Qui non c'è catalogo:
`stato_esecuzione` è un `text` con un `CHECK` a cinque valori.

⇒ Farne un catalogo con un flag «fuori dal giro» tocca il `CHECK` e un seed: è
**un cantiere suo**, e mescolarlo a un difetto che blocca un lotto sarebbe
sbagliato. La quinta copia è **dichiarata nel changeSet**, non nascosta.

### 6.6 Consegnato

| | |
| --- | --- |
| `20260909-18-update-fn-segna-esito-gruppo-lotto-salta-usciti` | il filtro dentro `ammesse` |
| `20260909-20-update-fn-segna-esito-gruppo-lotto-tre-conteggi` | i tre conteggi di ritorno (§4.1) |
| `20260909-21-update-fn-log-pipeline-fase-niente-critiche-sugli-usciti` | su un documento uscito non si scrivono `W` e `C` (§4.2) |
| `20260909-22-update-fn-escludi-documento-da-giro-giornale-uscita` | l'uscita compare nel giornale, col suo motivo |
| `test-uscita-documento-dal-giro-v1.sql` **19-22** | la giuntura, il documento sano, il giornale dell'uscita, la critica che non si scrive |

✅ **Tutti applicati il 2026-09-09, pgTAP verdi.**

⭐ **Ogni test è stato visto diventare ROSSO**, e su una causa diversa:

| Test | Mutazione | Cosa dice |
| --- | --- | --- |
| **19** | senza il filtro | riproduce l'errore di produzione parola per parola: `P0001`, `E_LOTTO_DOC_USCITA_IRREVERSIBILE` |
| **20** | filtro **troppo largo** (smette di marcare tutto) | il 19 resta verde e si accende il 20 — è il rimedio sbagliato che nessun altro test vedrebbe |
| **21** | senza il `-22` | `NULL`: l'uscita non lascia traccia |
| **22** | senza il `-21` | `C,I` invece di `I`: la critica si riscrive |

✅ I tre `rollback` verificati: la firma del marcatore torna `integer`, e le altre due funzioni tornano quelle di prima.

### 6.7 ✅ Le due decisioni del §4, prese il 2026-09-09

⛔ **E i tre conteggi stanno in un changeSet SUO, non dentro il `-18`.** Il
`-18` era già **applicato**: riscriverne l'SQL cambia il checksum e ferma il
migrate con *«Validation Failed: 1 changesets check sum»* — successo davvero il
2026-09-09. *Un changeSet applicato non si riscrive: se ne fa un altro.* Il
`-18` è stato riportato all'SQL esatto che era stato applicato, e
`liquibase validate` conferma **«No validation errors found»**.

**§4.1 — i tre zeri.** `fn_segna_esito_gruppo_lotto` restituisce
`(marcati, usciti, fuori_perimetro)`. Sono **tre** e non due: oltre a «nessun
documento appeso» e «gli unici sono usciti» c'è — **da prima di questo
difetto** — «i documenti ci sono ma nessuno nel perimetro di questo lotto».
Un ritorno che ne distinguesse due su tre lascerebbe l'ambiguità dov'era.

🔴 **Cambia la firma, e il backend va adeguato nello stesso giro**:
`apps/vendite/db/pipeline_repository.py`, `segna_esito_gruppo_lotto()` (changeSet `-20`) —
`SELECT vendite.fn_…` diventa `SELECT * FROM vendite.fn_…` e legge tre colonne.
`if not marcati:` diventa: si avvisa **solo** quando tutti e tre sono zero, o
quando `fuori_perimetro > 0` (che è l'altro caso sospetto). ⚠️ Finché non è
fatto, quella chiamata rompe: `CREATE OR REPLACE` non sposta un `RETURNS`,
quindi il changeSet fa `DROP` e ricrea. Nessun chiamante dentro il database
(verificato su `pg_proc`: zero).

**§4.2 — la critica, e il giornale.** Decisione di Tid: la critica su un
documento uscito **non si scrive**; ma l'uscita, che è un fatto voluto e con
una motivazione obbligatoria, **deve comparire nel giornale**.

⇒ La regola è: **su un documento uscito non si scrivono `W` e `C`; le `I`
restano.**

* `W`/`C` dicono «qualcosa non va su questo documento»: su uno che è uscito è
  rumore, e qui si smette proprio di scriverlo;
* `I` è un **fatto** del giornale, e l'uscita stessa è un fatto.

⛔ **L'alternativa scartata, e vale scriverla**: «si ferma tutto sul documento
uscito» funziona solo se la riga dell'uscita viene scritta **prima** del
passaggio a `ESCLUSO` — cioè appendendo la traccia all'**ordine di due
istruzioni** dentro un'altra funzione. Il giorno che qualcuno le riordina, la
traccia sparisce **in silenzio**. La regola su `I`/`W`/`C` non ha quel punto
fragile.

⚠️ **Chiude il rubinetto, non ripulisce il pregresso**: le critiche già scritte
su documenti usciti restano dove sono, e il conteggio continua a scartarle.
Cancellare righe di giornale è un'altra decisione, e non è stata presa qui.

---

## 7. ✅ Il backend, adeguato lo stesso giorno — 2026-09-09

`segna_esito_gruppo_lotto()` legge tre colonne (`SELECT marcati, usciti,
fuori_perimetro FROM …`) e ritorna un `EsitoMarcaturaGruppi`; `_marca_esito_gruppi`
avvisa **solo** quando tutti e tre sono zero **o** quando `fuori_perimetro > 0`.
⇒ Su un documento uscito l'avviso tace: è il caso normale del verbo.

⭐ **Provato con la chiamata VERA**, sul lotto del difetto e in transazione
annullata — non con un mock, che una firma cambiata non la vede:

| Caso | Esito |
| --- | --- |
| marcare il documento **uscito** — l'errore di produzione | `{marcati: 0, usciti: 1, fuori_perimetro: 0}`, **nessuna eccezione** |
| marcare un documento **sano** della stessa commessa | `{marcati: 1, …}` — il §6.2 regge: gli altri passano |
| una chiave **non del lotto** | `{fuori_perimetro: 1}` — il terzo zero si distingue |

Tre test nuovi: il consuntivo a tre, l'avviso che **non** suona sugli usciti,
l'avviso che suona su `fuori_perimetro`. **4563 verdi.**

### 7.1 🔴 Una cosa che vi chiediamo: la doc auto-gen è rimasta indietro

`docs/it/dbzero/vendite/funzioni/fn_segna_esito_gruppo_lotto.md` dichiara ancora
**`RETURNS integer`**. Il vivo dice
`RETURNS TABLE(marcati, usciti, fuori_perimetro)`.

⚠️ **Non è una svista formale: è la fonte che questa casa dichiara di leggere per
la struttura.** Adeguando il backend l'abbiamo aperta per prima e diceva la firma
VECCHIA — con quella avremmo riscritto la chiamata sbagliata, e `SELECT fn(...)`
su una `RETURNS TABLE` non fallisce: consegna la tupla intera in un campo solo.
Un valore plausibile e falso.

⇒ Ce ne siamo accorti solo perché abbiamo chiesto a `pg_proc`.
✅ **Rigenerata**: verificato il 2026-09-09 dopo il merge, la pagina dichiara
`RETURNS TABLE(marcati, usciti, fuori_perimetro)`. Le altre due funzioni toccate
erano già allineate (verificate tutte e tre).


---

## 8. 🟠 Il seguito, la sera del 2026-09-09 — quello che la consegna ha lasciato indietro

> **Chi scrive:** team DB, `dev/db-tid`. **Come è emerso:** rilanciando i pgTAP
> del cantiere, non da una segnalazione a video.

Quattro file rossi segnalati. Uno era già rientrato da solo, due erano **code
della consegna** e uno era una **regressione vera**, introdotta da un changeSet
di questo stesso cantiere.

| File | Che cos'era |
| --- | --- |
| `vendite/test-lotti-gruppi-esito.sql` | ⚠️ coda della consegna: il `-20` cambia la firma, il test no |
| `vendite/test-gruppo-key-segnalazioni-v1.sql` | ⚠️ idem, **più** una seconda cosa che il primo rosso nascondeva |
| `vendite/test-vw-dash-competenza-v1.sql` | ✅ già verde: la misura era stata presa prima del `20260909-67` |
| `script/test-rubinetto-primo-motivo-v1.sql` | 🔴 **regressione**, e non è di questo file: §8.3 |

### 8.1 ⚠️ La firma cambiata e i due pgTAP che nessuno ha adeguato

Il `-20` porta `fn_segna_esito_gruppo_lotto` da `RETURNS integer` a
`RETURNS TABLE(marcati, usciti, fuori_perimetro)`. Il §6.6 elencava la verifica
su `test-uscita-documento-dal-giro-v1.sql` (test 19-20), che infatti è stato
scritto nella forma nuova. Gli **altri due** file che chiamavano quella
funzione — sei chiamate in tutto — sono rimasti sulla forma vecchia:

```text
ERRORE: la funzione is(record, integer, unknown) non esiste
```

⛔ **E non è un rosso qualunque: è un ERRORE DI ESECUZIONE, quindi il file si
ferma lì.** `test-gruppo-key-segnalazioni-v1.sql` ne dichiarava 15 e ne eseguiva
**6**: i test 7-15 non giravano affatto, e `pg_prove` lo diceva in una riga
(`Bad plan. You planned 15 tests but ran 6`) che in mezzo a un elenco di file si
legge come un rosso solo. *Un test che non compila non è un test che fallisce:
è copertura che sparisce, e ne porta via anche quella dei vicini.*

✅ **Adeguati**: si legge `SELECT … FROM fn(…)` e si asseriscono **tutti e tre**
i conteggi (`'0|0|0'`, `'1|0|0'`), non il solo `marcati`.
⭐ **Perché tutti e tre, ed è la ragione per cui il `-20` esiste**: «zero
marcati» ha tre cause e una sola è un difetto. Asserire il solo `marcati` le
rimetterebbe dentro lo stesso zero, cioè disferebbe nel presidio la distinzione
che il changeSet ha appena introdotto nel codice.
⚠️ E `fn(…)` in lista di select su una `RETURNS TABLE` **non fallisce**:
consegna la tupla intera in un campo solo. È lo stesso inciampo del §7.1, dalla
parte del test invece che da quella del backend.

### 8.2 ⭐ Il rosso che si vedeva solo dopo aver riparato il primo

Riparato il test 7 di `test-gruppo-key-segnalazioni-v1.sql`, il file è arrivato
in fondo e il **12** era rosso: `have 1, want 2`.

La causa non è un difetto: è il `-21` di questo cantiere. La fixture creava il
documento **già `ESCLUSO`** e poi gli scriveva una critica per verificare che il
conteggio la scartasse. Dal `-21` quella critica **non si scrive più** — è
esattamente il rubinetto che abbiamo chiuso.

⛔ **E il test 11 sarebbe rimasto verde per il motivo sbagliato.** Chiede
`lotto_critical_count = 1`, e con la critica mai scritta il conteggio fa 1 **da
solo**: sarebbe passato anche cancellando il filtro del `20260908-07`, cioè
proprio ciò che dichiara di sorvegliare.

✅ **Rimedio: la fixture fa uscire il documento DOPO avergli scritto la
critica** — che è il modo in cui il pregresso è venuto al mondo. Il §6.7 lo
dice già in una riga: *«chiude il rubinetto, non ripulisce il pregresso: le
critiche già scritte restano dove sono, e il conteggio continua a scartarle»*.
Quella riga è l'invariante dei test 11-12, e ora la fixture la costruisce invece
di presupporla.

### 8.3 🔴 La regressione: il `-22` ha disfatto il `-11`

`script/test-rubinetto-primo-motivo-v1.sql`, test **2** (1 invece di 0) e **5**
(15 invece di 16). Il colpevole è `vendite.fn_escludi_documento_da_giro`.

| Ora | ChangeSet | Che cosa fa alla stessa funzione |
| --- | --- | --- |
| 00:27 | `20260909-11` (cantiere «i motivi si fermano dentro la check», C-2) | la porta su `script.fn_raise_primo_motivo_se_presente` |
| 01:30 | `20260909-22` (questo cantiere, §4.2) | la riscrive per la riga di giornale — **e rimette la coda a mano** |

⛔ **Non è una regressione cosmetica: la frase torna falsa.**
`E_LOTTO_NON_PRE_FISCALE` dice «*stato attuale: %s*» e quel `%s` è lo **stato del
lotto**; la coda a mano passa per primo `p_gruppo_key` — giusto per i motivi
2-4, che cominciano con «*Il documento %s*». È **il difetto vivo** che il `-11`
dichiarava di chiudere, tornato dopo un'ora: arità giusta, frase falsa, e nessun
vincolo che se ne accorga.

⚠️ **Com'è successo, e si legge dal file.** Il `-22` dichiara in intestazione
*«il corpo è quello VIVO (`pg_get_functiondef`)»*. Non lo era: anche il suo
`rollback` porta la coda a mano, cioè il corpo di **prima** del `-11`. Le due
metà concordano fra loro e dissentono dal vivo — è la firma di un corpo
**ricostruito da uno YAML** invece che letto dal database, cioè esattamente ciò
che [AGENTS.md §SQL Conventions](../../../../.codex/AGENTS.md) vieta. La
dichiarazione in intestazione non è una prova: si scrive prima di rileggere.

⭐ **Perché l'ha visto il rubinetto e non il pgTAP dell'uscita.** Il test 18 di
`test-uscita-documento-dal-giro-v1.sql` compone la frase dai `valori` che la
**check** emette: verifica la sede del dato, non chi solleva. Il rubinetto
guarda l'altra metà — *chi solleva* — ed è l'unica che si era rotta. Due
presidi, due domande diverse: è il motivo per cui il rubinetto è dichiarato «il
presidio che conta più della bonifica».
⚠️ **E il §6.4 di questo brief va letto insieme**: là si diceva «nessuno lo
*copriva*». Qui qualcuno copriva, e ha parlato il giorno stesso.

✅ **Rimedio**: `20260909-68-update-fn-escludi-documento-da-giro-ripristina-helper`.
Corpo **vivo** (dalla doc auto-gen rigenerata dopo il `-22`, quindi con la riga
di giornale) e la sola coda sostituita dalla chiamata all'helper.
⛔ Il `-22` **non si tocca**: è applicato e pushato su tre rami, riscriverne
l'SQL fermerebbe il migrate sul checksum.
⚠️ Il `rollback` del `-68` riporta al corpo del `-22`, non a quello del `-11`:
tornare al `-11` cancellerebbe la riga di giornale, cioè disferebbe un changeSet
che non è questo.

**Provato in transazione annullata**, eseguendo l'SQL **estratto** dal changeSet
e rifacendo le due misure del rubinetto:

| Misura | Prima | Dopo |
| --- | --- | --- |
| test 2 — punti in perimetro con la coda a mano | **1** | **0** |
| test 4 — debito fuori perimetro (soglia ≤ 6) | 6 | 6 |
| test 5 — funzioni che chiamano l'helper | **15** | **16** |

### 8.4 Le due voci aperte

1. 🔴 **Il `-68` è da applicare** (`make db-migrate`). Finché non lo è, il
   rubinetto resta rosso sui test 2 e 5 **e** la frase di
   `E_LOTTO_NON_PRE_FISCALE` continua a mostrare il documento al posto dello
   stato del lotto. ⛔ Il team DB non applica migrazioni da sé.
2. 🔴 **Un test Django è rimasto sulla firma vecchia**, ed è il gemello del
   §7.1 dall'altra parte: `apps/vendite/tests/db/test_lotto_gruppi_ordine.py`
   fa `SELECT vendite.fn_segna_esito_gruppo_lotto(…)` + `cur.fetchone()[0]` e
   confronta con `1`. Su una `RETURNS TABLE` quella lettura torna la **tupla
   intera** — `'(1,0,0)'` — quindi l'asserzione fallisce. ⚠️ Gira con
   `ZEROERP_TEST_DB_E2E=1`, **accesa in CI**. Il §7 dichiara «4563 verdi»: quel
   file è opt-in e con la flag spenta **salta**, quindi non era fra i 4563.
   ⛔ Fuori dal perimetro DB: la correzione è del backend (`SELECT marcati FROM
   …`, o leggere tutte e tre le colonne come fa `pipeline_repository`).

### 8.5 ⭐ La lezione, e non è «adeguare i test»

Il `-20` **sapeva** di cambiare la firma: lo scrive in intestazione a caratteri
rossi e nomina il chiamante da adeguare (`pipeline_repository.py`). Quello è
stato adeguato. Ciò che è mancato è la stessa domanda fatta ai **presidi**: il
censimento dei chiamanti si era fermato a `pg_proc` («dentro il database non la
chiama nessuno: zero») e al codice applicativo, e i pgTAP non sono né l'uno né
l'altro.

⇒ **Cambiare una firma è censire tre popolazioni, non due**: chi la chiama nel
database, chi la chiama fuori, e **chi la verifica**. La terza è l'unica che, se
la si dimentica, non produce un guasto — produce copertura che smette in
silenzio, e che si scopre solo la volta in cui qualcuno rilancia la suite.
