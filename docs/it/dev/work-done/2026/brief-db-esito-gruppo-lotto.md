# Brief DB — un documento che il lotto non riesce a fatturare deve dirlo

> **Destinatari:** team DB (`dev/db-tid`) e backend.
>
> **Tipo:** brief di cantiere. ⚠️ **Scritto dopo lo sviluppo della metà DB**
> (richiesta di Tid, 2026-09-06): serve a fissare il caso, le decisioni e — più
> di tutto — **che cosa resta e a chi**.
>
> **Stato:** 🟢 **DB, BE e FE completi** — vedi **§10** (la chiamata) e **§12**
> (le due superfici). `-10`, `-11` e `-12` applicati: verificato sul DB vivo il
> 2026-09-06, la vista ha le cinque colonne.
> ⚠️ **Il dato è a zero** (44 gruppi, tutti `NULL`): nessun giro è ancora
> passato dalla marcatura, e finché non passa non si vede niente. Il collaudo
> end-to-end è in **§12.5**, fatto in transazione annullata sul caso vero.
> ✅ **Le due domande di modello hanno risposta**: il **§11** nel §13 e §14 (si
> allineano i due rami: niente eccezione, niente rollback, i segni restano), il
> **§12.4** nel **§15** (una tabella sta rispondendo a due domande — si separano).
> ✅ **Il DB ha finito** (aggiornato il 2026-09-07): la separazione del §15 è
> applicata e verde — **§17** —, e **P-6** ha ritirato
> `E_PULL_COMMESSA_ALL_FAILED` con `obsoleto_dal` — **§19**.
> ✅ **E il backend ha finito** (§20): **P-5** — il ramo «tutte fallite» non
> solleva più — e **P-3**, il test che su quel ramo non mocka il repository.
> ✅ **Il `migrate` del seed è passato** (verificato il 2026-09-07 sul DB vivo:
> `ui.lista_definizione` 67/67 e `ui.lista_colonna` 735/735, zero righe del CSV
> mancanti) ⇒ il §12.6 è chiuso, e con esso il presidio del §19 — §21.
>
> 🟢 **CHIUSO e archiviato il 2026-09-08** (decisione di Tid). ⚠️ Le due voci
> che l'intestazione dichiarava aperte erano **già cadute dentro il documento
> stesso**, e l'intestazione era rimasta indietro: è il difetto che il §21
> denuncia — *«un brief che elenca come da fare cose già fatte»* — ripetuto sul
> proprio frontespizio. Riverificate contro il **database**, non contro il testo:
>
> | Voce | Diceva | Misurato il 2026-09-08 |
> | --- | --- | --- |
> | **§6** · il primo giro vero | «`fatturazione_lotti_esiti` ha **zero righe**» | **43 righe** — e il §23.1 lo aveva già chiuso col giro `LTF-0009900` |
> | **§20** · non è nel repo | «16 file + 2 test non committati» | committato (§23.2, push `993cdb91e`) |
> | **§25.5** · applicare `20260907-17` | 🔵 da fare | ✅ applicato: il commento della vista dichiara il criterio del pregresso e l'istante `19:09` |
>
> ✅ **E la coda del §24.5 — quella vera — ha avuto la sua risposta**: il badge
> non era contraddittorio, lo era il **banner**. Vedi §26.
>
> **Origine:** Tid, 2026-09-06, guardando il lotto `LTF-0009578`.

---

## 0. In due parole

Un lotto prende in carico tre documenti e ne fattura due. Il terzo fallisce, e
**sparisce dal racconto**: non è nel lotto (non è mai diventato una fattura) e
nella competenza resta fra quelli da emettere, senza un segno. Sembra
fatturabile.

⇒ Il documento fallito resta **dentro il lotto** e dice **perché** non è andato.

---

## 1. Il caso, misurato

*(fatto datato 2026-09-06, lotto `LTF-0009578` — id 10657, massivo, competenza
09/2026, `stato_lotto = ERRORE`)*

| | |
| --- | --- |
| Documenti presi in carico | **3**: ORD0036006, **ORD0036005**, ORD0036004 |
| Fatture prodotte e agganciate | **2** |
| Il fallito | ORD0036005 → commessa 34137, `E_PULL_COMMESSA`: *«ROOT source mancante»* |
| Dove sta | ancora fra i documenti da emettere, `stadio = DA_EMETTERE`, commessa emittibile |

Chi apre il lotto vede **due documenti** e una segnalazione che ne nomina un
terzo, per giunta chiamandolo con l'identificativo della **commessa**. Sembra
una segnalazione sbagliata; è invece l'unica cosa vera in giro.

---

## 2. La scoperta che ha cambiato il lavoro

⭐ **Il lotto non aveva perso ORD0036005.** La sua riga in
`vendite.fatturazione_lotti_gruppi` c'è — scritta quando il lotto ha deciso cosa
lavorare, insieme alle altre due.

Il legame non manca: manca la **voce**. Quella riga aveva solo la chiave del
documento e un contenitore vuoto, e nessuna colonna poteva dire *«questo è
andato male»*.

⇒ Il lavoro non è costruire un collegamento nuovo. È **dare una voce a quello
che c'è già**, e costa incomparabilmente meno.

### ⚠️ Perché non bastava la tabella delle fatture del lotto

`vendite.fatturazione_lotti_fatture` ha già `stato_esecuzione` ed è il posto
giusto per una fattura andata male. Ma si aggancia a `fattura_id`, e qui il
fallimento arriva **prima** che una fattura esista: non c'è niente a cui
appendersi.

⇒ Non è un difetto di quella tabella: è il piano sbagliato. Il piano giusto è un
gradino più su, ed è il gruppo.

---

## 3. Le decisioni

| # | Decisione | Chi, quando |
| --- | --- | --- |
| **D-1** | L'esito sta sul **gruppo**, non sulla fattura: è l'unico livello che esiste anche quando la fattura non nasce | DB, 06-09 |
| **D-2** | Vocabolario **identico** a quello delle fatture del lotto (`PENDING`, `RUNNING`, `COMPLETED`, `ERRORE`): due colonne che rispondono alla stessa domanda a due livelli non possono parlare due lingue | DB, 06-09 |
| **D-3** | ✅ **Un gruppo in errore resta DA EMETTERE, e la commessa resta emittibile.** Il segno dice *«ci ho provato e non ci sono riuscito»*, non *«non è fatturabile»* | **Tid, 06-09** |
| **D-4** | Le colonne nascono **nullabili**, e `NULL` vuol dire «nessuno l'ha detto» — che è la verità per tutte le righe di prima. Un `PENDING` di default direbbe «in attesa» di lavori chiusi mesi fa | DB, 06-09 |
| **D-5** | A scrivere l'esito è **una funzione**, non `UPDATE` sparsi: il pezzo difficile non è scrivere la riga, è sapere **quale** | DB, 06-09 |
| **D-6** | La funzione **non solleva mai**: la chiama un gestore d'eccezione, e un errore su di sé coprirebbe l'errore vero | DB, 06-09 |

### ⭐ Il perno di D-5

Chi fallisce ha in mano la **commessa**; il lotto ha in mano i **gruppi**. I due
si incontrano solo passando dalla chiave di raggruppamento, che il database sa
già costruire (`vendite.fn_build_gruppo_fatturabile_key`, la stessa usata dalla
dashboard di competenza).

⛔ Se quella derivazione la rifà il backend, diventa una seconda scrittura della
stessa regola — e il giorno in cui la chiave cambia forma le due versioni
dissentono in silenzio.

⇒ Il chiamante passa **ciò che ha** (il lotto e la commessa), e il database
ritrova il gruppo.

---

## 4. Che cosa è stato scritto — metà DB

| ChangeSet | Cosa fa |
| --- | --- |
| `20260906-10` (`00_schema/vendite`) | Le quattro colonne dell'esito su `fatturazione_lotti_gruppi` + due vincoli: il vocabolario, e **un errore non può essere muto** (su `ERRORE` serve almeno la causa o la frase) |
| `20260906-11` (`20_code/vendite`) | `vendite.fn_segna_esito_gruppo_lotto`: scrive l'esito, ritrova il gruppo dalla commessa, torna **quanti gruppi ha marcato** |
| `20260906-12` (`20_code/vendite`) | `vw_dash_competenza_gruppi` espone l'esito dell'**ultimo tentativo**: stato, codice, frase, quando, e **in quale lotto**. ⛔ `stadio` e `commessa_emittibile` non cambiano |
| `db/pgtap/vendite/test-lotti-gruppi-esito.sql` | 8 test, **tutti su casi costruiti** |

### Verifiche fatte

* ✅ **applicati e collaudati il 2026-09-06**: pgTAP **6/6**;
* i quattro cancelli statici della CI sono verdi;
* ⭐ i due `WARNING` che compaiono nell'esecuzione del test **sono la prova che
  il disegno regge**: sono i casi 3 e 6, dove la funzione avverte invece di
  sollevare. Se un giorno sparissero, vorrebbe dire che qualcuno l'ha fatta
  tornare a lanciare eccezioni.
* ⭐ **R-3 provato sul caso vero**, in transazione annullata: marcato il gruppo di
  `ORD0036005` nel lotto `LTF-0009578`, la competenza lo mostra
  **ancora `DA_EMETTERE`, con la commessa emittibile** — e in più
  `ERRORE / E_PULL_COMMESSA / «ROOT source mancante per commessa 34137» /
  LTF-0009578`. È esattamente il comportamento chiesto.
* ⏳ il test 7 (le cinque colonne in competenza) è rosso finché `-12` non è
  applicato: le colonne non esistono ancora sulla vista viva.

### ⚠️ Un debito dichiarato nel test

Il ritrovamento del gruppo **partendo dalla commessa, quando la commessa
alimenta davvero quel gruppo**, non è collaudato: servirebbe una commessa con le
sue attività, cioè una fixture più grande della cosa da provare. È collaudato il
verso opposto (una commessa che non c'entra non marca niente). ⇒ Il verso
positivo si verifica **sul giro vero**, ed è la prima cosa da guardare dopo che
il backend chiama la funzione.

---

## 5. Che cosa resta — e non è del DB

| # | Cosa | Chi |
| --- | --- | --- |
| **R-1** | 🔴 **Chiamare la funzione** dove oggi si scrive la segnalazione di errore del lotto (`pipeline_error_logger` / l'esecutore del passo). Senza questo, le colonne restano vuote e **non cambia niente per chi guarda** | backend |
| **R-2** | Segnare `COMPLETED` sui gruppi che vanno a buon fine. ⚠️ Senza, un gruppo riuscito resta `NULL` e non si distingue da uno mai lavorato | backend |
| **R-3** | ✅ **FATTO — changeSet `20260906-12`, da applicare.** La vista dei documenti da emettere porta l'esito dell'ultimo tentativo. ⚠️ Le colonne restano vuote finché non arriva R-1: la vetrina è pronta, il dato lo scrive il backend | DB |
| **R-4** | La chiave del gruppo accanto alla commessa nella segnalazione del lotto. ⭐ **Diventa molto meno urgente**: se il gruppo porta il proprio esito, il lotto non ha più bisogno del log per dire quale documento è caduto | backend |

⚠️ **R-1 è il collo di bottiglia.** Tutto il resto è già in piedi e non serve a
niente finché nessuno scrive l'esito.

> ✅ **Aggiornamento 2026-09-06 (dopo §10 e §12).** R-1, R-2 e R-3 sono **fatti**.
> ⭐ **R-4 è superato, non rinviato**: la scheda «Presi in carico» del drawer
> lotto nomina il documento caduto *dalla riga del gruppo*, quindi il log non
> deve più farlo. Riaprirlo vorrebbe dire scrivere una seconda volta
> un'informazione che ora ha una sede sua.
> 🔴 Restano il **§11** e il **§12.4**, e sono **entrambi del modello**: nessuno
> dei due si tappa dal backend.

---

## 6. Come si vede che è chiuso

1. Si rifà un giro come quello di `LTF-0009578` (o si riapre quello).
2. Nel lotto compaiono **tre** documenti, non due: due riusciti e uno in errore,
   con la sua frase.
3. In competenza quel documento è **ancora da emettere** — e ha un segno che
   dice che l'ultimo tentativo è fallito.
4. Chi clicca sul segno arriva **alla commessa da correggere**, non a un
   messaggio tecnico.

⚠️ Il punto 4 è quello che decide se il lavoro è servito: nel caso reale la
causa non era un difetto del programma, ma un dato mancante sulla commessa
34137. Se il rosso non porta lì, l'operatore sa di avere un problema e non sa
che farci.

---

## 7. Note per chi ci mette le mani

* ⛔ **Non scrivere le colonne con `UPDATE` diretti.** La regola su *quale* riga
  marcare sta nella funzione, ed è l'unica cosa non banale di tutto il cantiere.
* ⚠️ **Zero è una risposta.** La funzione torna quanti gruppi ha marcato: se
  torna `0` il fallimento non è stato appeso a niente, e il lotto continuerà a
  raccontare un errore su un documento che non mostra. Va guardato, non ignorato.
* ⚠️ **Una commessa può alimentare più di un gruppo** nello stesso lotto: in quel
  caso l'esito va su tutti. Sceglierne uno sarebbe una scommessa travestita da
  regola.
* ⭐ **Un gruppo che ci riprova e riesce non deve restare rosso**: passare a
  `COMPLETED` azzera causa, frase e orario. Un rosso che non scade mai è peggio
  di nessun rosso.

---

## 8. Il contratto per il backend

Questa è la parte che sblocca tutto il resto. Non c'è niente da progettare: gli
ingredienti sono già in mano nel punto in cui serve.

### La funzione

```
vendite.fn_segna_esito_gruppo_lotto(
    p_lotto_id          bigint,            -- obbligatorio
    p_stato             text,              -- 'COMPLETED' oppure 'ERRORE'
    p_gruppo_key        text   = NULL,     -- se lo si ha
    p_commessa_id       bigint = NULL,     -- altrimenti questa
    p_errore_codice     text   = NULL,     -- su ERRORE: almeno uno dei due
    p_errore_messaggio  text   = NULL
) RETURNS integer   -- quanti gruppi ha marcato
```

* Si passa **il gruppo oppure la commessa**. Chi fallisce ha in mano la
  commessa: passi quella e la funzione ritrova il gruppo **dentro quel lotto**.
* **Non solleva mai.** Ogni via d'uscita è un avviso: sta annotando un
  fallimento già avvenuto, e un errore su di sé coprirebbe quello vero.
* ⚠️ **Il valore di ritorno va guardato.** `0` vuol dire *«non l'ho appeso a
  nessun documento»* — cioè il lotto continuerà a raccontare un errore su
  qualcosa che non mostra. È l'unico segnale che il collegamento non ha funzionato.

### Dove va chiamata

In `pipeline_step_executor._handle_pull_attivita_da_commessa_task`, dove il giro
sulle commesse è già finito e l'esito è già in mano:

| Caso | Cosa chiamare |
| --- | --- |
| commessa **fallita** | stato `ERRORE`, con `E_PULL_COMMESSA` e il messaggio già composto |
| commessa **riuscita** | stato `COMPLETED` — sono `commessa_ids` meno quelle fallite |

⚠️ Senza il secondo, un gruppo riuscito resta a `NULL` e **non si distingue da
uno mai lavorato**: la colonna direbbe solo dove è andata male, e non si potrebbe
mai dire «il lotto è a posto».

### 🔴 La trappola: ci sono DUE uscite di fallimento

* **parziale** → `TaskEsitoParziale` (è il caso di `LTF-0009578`);
* **tutte fallite** → `ErrorManager.raise_error("E_PULL_COMMESSA_ALL_FAILED")`,
  che **solleva subito**.

⛔ Se la marcatura si mette solo nel ramo parziale, **il caso peggiore — tutte
fallite — resta senza segni**. È il paradosso classico: funziona quando va male
a metà e tace quando va male del tutto.

⇒ **Marcare prima di sollevare**, in tutti e due i rami.

### Dove mettere il codice

* la chiamata SQL in `pipeline_repository.py`, non nel service: è la convenzione
  del progetto, e serve a poterla mockare nei test;
* ⛔ **niente `UPDATE` diretti sulle colonne.** La regola su *quale* riga marcare
  è l'unica cosa non banale di tutto il cantiere, e sta nella funzione. Rifarla
  in Python vorrebbe dire scrivere due volte la stessa regola.

### I casi di prova che vorrei vedere

1. giro con **una commessa fallita su tre** → un gruppo `ERRORE` con codice e
   frase, due `COMPLETED`;
2. giro con **tutte fallite** → tutti i gruppi `ERRORE`, **e poi** l'eccezione;
3. giro **tutto riuscito** → tutti `COMPLETED`, nessun campo di errore
   valorizzato;
4. la funzione torna **0** → il caso va gestito (almeno un log), non ignorato.

---

## 10. ✅ Il backend ha chiamato (2026-09-06)

* `pipeline_repository.segna_esito_gruppo_lotto(...)` — la chiamata SQL, come da
  convenzione, così i test la possono mockare;
* `pipeline_step_executor._marca_esito_gruppi(...)` — **una volta sola, prima dei
  tre rami**, non dentro ciascuno.

⭐ **Perché prima e non dentro.** Le uscite sono tre e la marcatura serve in
tutte: scriverla nei rami vorrebbe dire scriverla tre volte e dimenticarla una,
e il candidato naturale è proprio quello che solleva — cioè il caso peggiore. È
la trappola che il vostro §8 segnala, e il modo più sicuro di non caderci è non
avere tre punti da ricordare.

⚠️ Il valore di ritorno **si guarda**: `0` finisce in un `warning` con
`lotto_id`, `commessa_id` e stato. Non solleva, come dite voi.

I quattro casi del §8 sono in `test_pipeline_step_executor.py`.

---

## 11. 🔴 «Marcare prima di sollevare» non basta — misurato

Il §8 dice: *«⇒ Marcare prima di sollevare, in tutti e due i rami.»* L'ho fatto,
e **sul ramo che solleva non regge**.

**Perché.** `run_pipeline` tiene un `transaction.atomic()` attorno all'**intero
ciclo degli step**, e `fn_segna_esito_gruppo_lotto` è una funzione plpgsql
normale: scrive nella transazione di chi la chiama. Il `raise` di
`E_PULL_COMMESSA_ALL_FAILED` propaga fuori da lì e fa **rollback**, marcature
comprese.

**La prova, sul database vero:**

```
gruppo 894 (lotto 6034) — stato prima: None
  marcati: 1
  sollevata: come E_PULL_COMMESSA_ALL_FAILED
stato DOPO il raise: None
⛔ LA MARCATURA E' STATA PERSA
```

⚠️ **E nessun test lo vedeva**, perché nei test il repository è mockato: provano
che la chiamata avvenga, non che la riga resti. È il difetto che si scopre solo
guardando i confini di transazione.

⭐ **È la stessa forma che avete già diagnosticato voi** su `fn_run_and_log` —
*«scrive, e poi butta via»* — e per cui avete costruito
`maintenance.fn_job_run_log_failure`. Il paradosso è identico: il verbale del
fallimento muore insieme al fallimento.

### Che cosa serve

Che la marcatura di un gruppo **sopravviva al rollback** di chi l'ha chiesta. La
forma la decidete voi: avete già risolto lo stesso problema una volta.

⇒ **Nel frattempo la copertura è parziale, e dichiarata:** i due rami che non
sollevano — tutto riuscito e **parziale** — funzionano. Il parziale è il caso di
`LTF-0009578`, cioè quello per cui il cantiere è nato: il difetto originale è
chiuso. Resta scoperto il «tutte fallite», che è quello che oggi non si vede.

⛔ La chiamata resta **prima dei rami** e non si sposta: il giorno in cui la
scrittura diventa durevole, il terzo ramo è già coperto senza toccare niente.

---

## 12. ✅ BE + FE — le due superfici (2026-09-06)

> Scritto dopo lo sviluppo, come il resto del documento. `-12` risulta
> **applicato**: la vista viva ha le cinque colonne (verificato sul DB, non
> dedotto dagli YAML). ⚠️ **Il dato è a zero**: 44 righe in
> `fatturazione_lotti_gruppi`, tutte con `stato_esecuzione = NULL`, perché
> nessun giro di fatturazione è ancora passato dalla marcatura scritta ieri.
> Non è un difetto — è che il primo giro deve ancora avvenire.

### 12.1 Cosa si vede adesso, e dove

| Dove | Cosa |
| --- | --- |
| **Competenza → Da emettere** | il documento che ha già fallito porta un'icona rossa **accanto al nome**, col motivo per intero e ⭐ **il pulsante che apre la commessa da correggere** (§6 punto 4) |
| **Drawer del lotto** | scheda nuova **«Presi in carico»**: i documenti che il lotto ha preso, **compreso quello che una fattura non è mai diventata**, con l'esito di ciascuno |

### 12.2 Le decisioni prese scrivendo

| # | Decisione | Perché |
| --- | --- | --- |
| **BF-1** | ⭐ **Il segno in competenza è chrome della cella, non una colonna a catalogo** | Le cinque colonne esistono (disponibili e **spente**, convenzione D-4), ma una colonna che nessuno ha acceso è un segno che non c'è. Il segno deve esserci sempre — sta accanto al nome, dov'è già il lucchetto dell'emittibilità |
| **BF-2** | Il **messaggio** vive in un popover, non in una cella | Cita numeri di documento e via d'uscita: in una colonna sarebbe troncato, cioè presente e inutile. È lo stesso `ErroreRigaInfo` della scheda documenti |
| **BF-3** | ⭐ Il gesto verso la commessa passa dal **resolver dei bersagli** già in servizio (`core/bersagli.js`) | Applica da sé i guard dei permessi e apre l'ospite globale di `App.vue`. ⛔ Il bersaglio si **compone nel frontend** e non arriva dal backend: la commessa è già una colonna della riga, e rispedirla sarebbe lo stesso dato due volte |
| **BF-4** | La scheda del lotto è **una scheda in più**, non colonne dentro «Documenti» | Le due grane sono diverse e non in corrispondenza 1:1 nemmeno a giro riuscito: `fn_build_fattura_key` può raccogliere più gruppi nello stesso documento |
| **BF-5** | L'identità del gruppo si **legge** da `vw_dash_competenza_gruppi`, non si ricostruisce | Spezzare la `gruppo_key` in Python sarebbe la seconda sede della regola: il giorno in cui la chiave cambia forma, le due dissentono in silenzio |
| **BF-6** | L'esito della scheda lotto si legge dalla **tabella**, non dalle colonne `ultimo_*` della vista | Quelle dicono com'è andato l'**ultimo** tentativo su quel gruppo, che può essere di un **altro** lotto. Lì la domanda è «come è andata in *questo* lotto» |
| **BF-7** | `commessa_id` esce **solo quando ce n'è una** (`commesse_n` dice quante sono) | La chiave di un gruppo-documento non contiene la commessa: due commesse sullo stesso documento sono ammesse per costruzione, e sceglierne una sarebbe la scommessa che il §7 vieta |
| **BF-8** | La risposta della scheda porta **`perimetro_dichiarato`** | Vedi §12.4: senza, il caso più frequente racconta una bugia |

### 12.3 🔴 Un difetto trovato di rimbalzo, e non era di questo cantiere

La mappa cromatica del frontend per `stato_esecuzione`
(`core/utils/severity.js`) parlava una lingua che il database **non parla**:
`PRONTA` / `ELABORATA` / `ESCLUSA`, mentre il `CHECK` ammette
`PENDING` / `RUNNING` / `COMPLETED` / `ERRORE`.

⇒ Nel drawer del lotto un documento `COMPLETED` prendeva il ripiego
`secondary` — **grigio, cioè «bozza»** — invece del verde. Nessun errore da
nessuna parte: `resolveSeverity` ripiega di proposito, e un colore sbagliato non
fallisce.

⭐ È emerso aggiungendo il **secondo** consumatore, che per la D-2 parla lo
stesso vocabolario. La mappa è ora **una sola** per i due livelli, con i valori
veri.

### 12.4 ⚠️ Il buco che resta, ed è del modello — non del codice

**Un lotto di massa non ha dove essere marcato.**
`fatturazione_lotti_gruppi` è il perimetro di un lotto **mirato**; la
convenzione portante della tabella dice che *nessuna riga = nessuna
restrizione*, che è il comportamento del giro schedulato (garanzia G1). Un giro
di massa quindi **non scrive nessun gruppo**, e `fn_segna_esito_gruppo_lotto`
non trova niente da marcare: torna `0`, con il warning previsto dal §7.

⇒ **L'esito per giro esiste oggi solo sui lotti nati da emissione mirata.**
Il lotto `LTF-0009578` è uno di quelli — è `MASSIVO` come tipo ma porta un
perimetro, perché nasce da un'emissione mirata — quindi il caso del §1 è
coperto. Un giro schedulato che fallisse una commessa resterebbe **muto come
prima**.

⛔ **Non si tappa dal backend**, e la tentazione c'è: basterebbe far scrivere al
runner i gruppi scoperti anche sui giri di massa. Ma quelle righe **sono** il
criterio di restrizione — scriverle trasformerebbe ogni giro schedulato in un
giro mirato, cioè un cambio di comportamento del motore travestito da
miglioria di diagnostica.

⇒ **È una domanda di modello per il team DB**, accanto al §11: *dove vive
l'esito di un documento quando il lotto non dichiara un perimetro?* Nel
frattempo la scheda **lo dichiara** invece di tacere: su un lotto senza
perimetro non mostra «nessun documento» — che sarebbe falso — ma dice che quel
lotto un perimetro non lo dichiara, e rimanda alla scheda «Documenti».

### 12.5 Come è stato collaudato

⚠️ **Il dato è tutto `NULL`, quindi «non si vede niente» era indistinguibile da
«non funziona».** Il collaudo si è fatto **sul database vero, in transazione
annullata**: marcato il gruppo di `ORD0036005` nel lotto `LTF-0009578` con
`E_PULL_COMMESSA`, e i due gemelli a `COMPLETED`.

```
scheda lotto:  ORD0036005  ERRORE     E_PULL_COMMESSA  «ROOT source mancante…»
               ORD0036004  COMPLETED
               ORD0036006  COMPLETED
competenza:    ORD0036005  stadio=DA_EMETTERE  emittibile=True
                           esito=ERRORE  cod=E_PULL_COMMESSA  lotto=LTF-0009578
dopo rollback: gruppi con esito = 0
```

⭐ La riga in competenza resta **DA EMETTERE con la commessa emittibile**: è la
D-3, ed è la cosa che il collaudo doveva provare più dell'esistenza delle
colonne.

### 12.6 ✅ Prima che si veda in applicazione — *fatto il 2026-09-07 (§21)*

> Il `migrate` del seed è passato: `ui.lista_definizione` **67/67** e
> `ui.lista_colonna` **735/735**, zero righe del CSV mancanti a database.
> ⬇️ Il testo resta perché spiega *perché* serviva, e perché la stessa cosa
> tornerà a servire alla prossima lista.

Le **due liste** prendono le colonne dal catalogo (`ui.lista_colonna`), che è
**dato di seed**: le righe sono nei CSV, ma nel database ci arrivano solo col
prossimo `migrate` — oppure creandole dai pannelli di amministrazione in-app.
Finché non succede, la scheda «Presi in carico» monta una lista **senza
colonne**.

⚠️ Il segno in competenza **non** dipende dal catalogo (BF-1): quello si vede
appena il backend viene ricaricato.

| Cosa | Serve |
| --- | --- |
| icona rossa + gesto in competenza | ricarica del backend (`kill -HUP`) + build FE |
| le cinque colonne opzionali in competenza | `migrate` del seed |
| scheda «Presi in carico» del lotto | `migrate` del seed |

---

## 13. ✅ Risposta del team DB al §11 — **non serve niente dal database**

> Rilettura del 2026-09-06, dopo il push del backend.

### Prima: il lavoro fatto regge, e in due punti va oltre il contratto

* la chiamata è **prima dei tre rami** e non dentro, con il ragionamento giusto
  scritto accanto — *«metterla nei rami vorrebbe dire scriverla tre volte e
  dimenticarla una: il candidato naturale è il ramo che solleva, cioè il caso
  peggiore»*;
* `COMPLETED` sui riusciti, non solo l'errore;
* il valore di ritorno **guardato**, con un avviso che dice la conseguenza e non
  solo il fatto;
* ⭐ gli stati presi da uno **specchio del vincolo di tabella**, non da stringhe
  scritte a mano. Il contratto non lo chiedeva: è meglio di quello che avevamo
  scritto noi;
* ⭐ e il limite è stato **misurato**, non supposto.

### Il limite è vero. La soluzione proposta, secondo noi, no

Il §11 chiede una scrittura che sopravviva al rollback, *«stessa forma di
`maintenance.fn_job_run_log_failure`»*. ⛔ **Sconsigliata, per due motivi.**

**1. Cambierebbe la natura del canale.** Quel canale scrive su `dbops.error_log`
e `maintenance.job_run_log`: due **registri**. Estenderlo a
`vendite.fatturazione_lotti_gruppi` vuol dire dare al ruolo del canale la
scrittura su una tabella di **dominio**, sotto RLS. Per far sopravvivere un
segno si aprirebbe una porta su un'altra tabella — e quella porta poi resta.
⚠️ In più il canale è silenzioso dove non è configurato: su `ci-validate` non
c'era fino a ieri.

**2. ⭐ Il meccanismo esiste già, e sta nello stesso file, tre righe sopra.**
`run_pipeline` ha un `except ServiceError` **fuori** dal `transaction.atomic()`,
e lì fa già tre scritture di compensazione che sopravvivono al rollback:

| | |
| --- | --- |
| `_mark_lotto_error_safely` | mette il lotto in errore |
| `_persist_fattura_error_safely` | *«la testata dice CHE c'è un errore; questa riga dice QUALE documento, e perché»* |
| `_persist_task_run_error_safely` | il diario dei task |

⇒ Serve un **quarto fratello**, non un meccanismo nuovo. E il commento del
secondo descrive già, parola per parola, quello che manca al terzo ramo.

### Il piano

| # | Cosa | Chi |
| --- | --- | --- |
| **P-1** | L'eccezione porta gli **id** delle commesse fallite, non solo le frasi formattate (oggi `context["errors"]` sono stringhe) | BE |
| **P-2** | `_marca_gruppi_falliti_safely(...)` nel `except ServiceError` di `run_pipeline`, accanto ai tre che ci sono già. La transazione lì è chiusa: la scrittura vive | BE |
| **P-3** | 🔴 Un test che su quel ramo **non mocka** il repository. Il difetto è sfuggito proprio perché i test provano che la chiamata avvenga, non che la riga resti | BE |
| **P-4** | **DB: niente.** `fn_segna_esito_gruppo_lotto` funziona da qualsiasi transazione, è idempotente e dice quante righe ha marcato | — |

### ⭐ Una domanda prima di P-1 — e la risposta è già scritta accanto

Quando un giro finisce male il sistema può fare due cose diverse:

| | Che cosa succede | Quando lo fa oggi |
| --- | --- | --- |
| **Annulla tutto** | come strappare il foglio: non resta traccia di niente, nemmeno degli appunti su che cosa è andato storto | quando falliscono **tutte** le commesse |
| **Fermati e lascia scritto** | il lavoro non è riuscito, ma gli appunti restano: si vede quale documento è caduto e perché | quando ne falliscono **alcune** |

⭐ **E la seconda scelta il progetto l'ha già fatta**, con il motivo scritto sopra
`TaskEsitoParziale` in `pipeline_step_executor.py`:

> *«NON sollevare al suo posto: un raise farebbe rollback dell'intero step,
> cancellando anche il lavoro delle fatture sane E la marcatura di quelle rotte
> — il rilancio ripartirebbe da zero, identico, per sempre.»*

È **esattamente** il difetto che il §11 ha misurato, un ramo più in là.

⇒ La domanda diventa molto più semplice di come l'avevamo posta:
**perché quando ne falliscono due su tre teniamo gli appunti, e quando ne
falliscono tre su tre li strappiamo?** La differenza fra i due casi è un numero.

⚠️ **Una ragione per lasciarlo com'è c'è, e va separata dall'altra.** Se
falliscono tutte non c'è niente da fatturare, quindi ha senso **fermare la
catena** invece di far girare a vuoto i passi successivi.
⭐ Ma *«fermare la catena»* e *«strappare gli appunti»* sono due cose diverse, e
oggi le fa lo stesso gesto. Si può fermare **tenendo**.

⇒ Se il seguito della catena regge un esito invece di un'eccezione, questa è la
strada — e P-1/P-2 non servono. Se il `raise` è davvero l'unico modo di fermare
tutto, allora P-1 e P-2 restano.
⛔ **Non la tocchiamo noi**: chi conosce il seguito della catena decide.

### ⚠️ Che cosa resta scoperto nel frattempo, e va detto così

I due rami che non sollevano — tutto riuscito e **parziale** — funzionano, e il
parziale è il caso di `LTF-0009578`: **il difetto per cui il cantiere è nato è
chiuso.** Resta scoperto il «tutte fallite», che è anche il caso in cui oggi non
si vede niente. È un debito con un nome, non una svista.

---

## 14. ✅ Decisione presa: si allineano i due casi (Tid, 2026-09-06)

> **«Trattiamoli tutti come quando ne capita 2 su 3.»**

Il ramo «tutte fallite» smette di sollevare e torna un esito, come fa già il
parziale. Niente rollback ⇒ i segni sui documenti falliti restano.

⇒ **P-1 e P-2 del §13 decadono**: non serve più nessuna scrittura di
compensazione, perché non c'è più niente da compensare. Resta **P-3** — il test
che su quel ramo non mocka il repository.

### Che cosa ho verificato prima di dire di sì

La domanda che conta è: **senza l'eccezione, chi mette il lotto in ERRORE?**

Lo decide `evaluate_lotto_status`, che guarda due cose: fatture in errore e
segnalazioni critiche. ⛔ E con tutte le commesse fallite **le fatture non
nascono**: la prima delle due è zero per costruzione.

✅ Il lotto va comunque in ERRORE, e il motivo è la seconda: il passo scrive una
segnalazione **critica per ogni commessa fallita** *prima* di scegliere il ramo.
Misurato su `LTF-0009578`: una commessa fallita, una riga critica. Con tre su
tre ce ne sarebbero tre.

### 🔴 Ma è una salvezza indiretta, e va sorvegliata

Il lotto si salva perché **un altro pezzo** scrive quelle righe in un certo
modo. Se un giorno cambiassero forma — accorpate, declassate a warning,
spostate — un fallimento totale tornerebbe a presentarsi come *«Pipeline
completata»*.

⭐ È esattamente la classe di difetto per cui questo cantiere è nato: **si
manifesta come silenzio**. Quindi non ci si fida: si mette un presidio.

| | |
| --- | --- |
| **`20260907-11`** | `vendite.vw_lotti_chiusi_con_gruppi_in_errore` — elenca la contraddizione *«un lotto chiuso COMPLETATO che contiene documenti in ERRORE»*, e deve restare vuota |
| **pgTAP 9 e 10** | che è vuota, **e** che si accende su un caso costruito. Senza il secondo, il primo proverebbe solo che oggi non c'è niente |

⚠️ La vista **non** conta i gruppi senza esito (`NULL` = nessuno l'ha detto):
sono tutti i lotti anteriori al 2026-09-06, e contarli darebbe un presidio che
nasce già spento e non arriva mai a zero.

### Il piano aggiornato

| # | Cosa | Chi | Stato |
| --- | --- | --- | --- |
| **P-5** | Il ramo «tutte fallite» torna un esito invece di sollevare, come il parziale | BE | ✅ **fatto (07-09)** — §20 |
| **P-3** | Un test su quel ramo che **non mocka** il repository | BE | ✅ **fatto (07-09)** — §20 |
| **P-6** | `E_PULL_COMMESSA_ALL_FAILED` ritirato con `obsoleto_dal = 2026-09-07` (§19) | DB | ✅ **fatto (07-09)** |
| **P-7** | Il presidio `20260907-11` | DB | ✅ **applicato e verde (07-09)** |
| ~~P-1, P-2~~ | ~~scrittura di compensazione~~ | — | ⛔ **decadute** |

### ⚠️ Il presidio dice una cosa in più di quella per cui è nato

Se un domani qualcuno rimettesse un `raise` su quel ramo, i segni tornerebbero a
sparire — e la vista **non** se ne accorgerebbe (nessun gruppo in ERRORE, quindi
nessuna contraddizione). ⇒ Quel verso lo copre il test 10, che costruisce il
caso: è lì che si vede se la marcatura sopravvive davvero.

---

## 15. ✅ Risposta al §12.4 — una tabella sta rispondendo a due domande

> La domanda era: *«dove vive l'esito di un documento quando il lotto non
> dichiara un perimetro?»*. La diagnosi del §12.4 è giusta, e il rifiuto di
> tappare dal backend anche: scrivere i gruppi sui giri di massa
> trasformerebbe ogni giro schedulato in un giro mirato.

### La causa, in una riga

`fatturazione_lotti_gruppi` oggi risponde a **due domande diverse**:

| | |
| --- | --- |
| *«quali documenti devo lavorare?»* | il **perimetro** — e lì *nessuna riga* vuol dire *nessuna restrizione* |
| *«com'è andato ciascun documento?»* | l'**esito** — che dovrebbe esistere sempre, perimetro o no |

Coincidono sui giri mirati, e divergono su quelli di massa. ⭐ Non è un buco da
tappare: è **una tabella di troppo poco**.

### La strada che proponiamo

Un posto suo per l'esito — *(lotto, documento, com'è andato)* — scritto
**quando c'è qualcosa da dire**, indipendentemente da come è nato il lotto.
`fatturazione_lotti_gruppi` torna a essere solo il perimetro, e la sua
convenzione portante resta intatta.

⭐ **E il contratto verso il backend non cambia di una virgola**:
`fn_segna_esito_gruppo_lotto` mantiene nome e parametri — cambia solo dove
scrive, e su un lotto senza perimetro la riga la **crea** invece di non trovarla.
⇒ Nessuna modifica al codice già scritto: sparisce solo il ritorno `0` sui giri
di massa.

### ⛔ Le due strade scartate

* **Un flag sulla riga** che distingua «questa restringe» da «questa racconta»:
  sarebbe una colonna che risponde a due domande, e la regola portante
  diventerebbe *«nessuna riga **con il flag**»* — un'invariante più sottile, che
  ogni lettore dovrebbe conoscere per non sbagliare.
* **Scrivere i gruppi anche sui giri di massa**: è la tentazione già rifiutata
  nel §12.4, e per il motivo giusto.

### ⚠️ Quanto costa, detto prima

Non è una riga: una tabella nuova, lo spostamento delle quattro colonne, la
funzione che cambia bersaglio, la vista di competenza che cambia join, il
presidio e il pgTAP che seguono. ⇒ **Va deciso, non fatto di slancio.**

⚠️ E finché non si fa, il §12.4 resta vero e va detto così: **l'esito per
documento esiste sui lotti nati da emissione mirata; un giro schedulato che
fallisce una commessa è muto come prima.** È un debito con un nome.

---

## 16. 🏁 Dove siamo il 2026-09-07

### ✅ In esercizio, e verificato

| | |
| --- | --- |
| Le colonne dell'esito sul gruppo | `20260906-10` |
| La funzione che le scrive e ritrova il gruppo dalla commessa | `20260906-11` |
| La competenza che mostra l'ultimo tentativo | `20260906-12` |
| Il presidio della contraddizione | `20260907-11` |
| Il collaudo | `test-lotti-gruppi-esito.sql` — **10/10** |
| La lista che l'operatore guarda | le cinque colonne ci sono **e sono attive** |

⭐ Il difetto per cui il cantiere è nato — un documento fallito che spariva dal
lotto e sembrava sano in competenza — **è chiuso e visibile a video**, sui lotti
con perimetro.

### 🔴 Torna al backend

| # | Cosa |
| --- | --- |
| ~~P-5~~ | ✅ **fatto il 2026-09-07**: il ramo non è stato modificato, è stato **tolto** — §20 |
| ~~P-3~~ | ✅ **fatto il 2026-09-07**: e verificato che si accende rimettendo il  — §20 |

### 🔵 Poi torna al DB

| # | Cosa |
| --- | --- |
| ~~P-6~~ | ✅ **fatto il 2026-09-07**: ritirato con `obsoleto_dal`, una riga di CSV. Il come e il perché nel §19 |
| **P-8** | La separazione del §15, **se e quando** la si decide |

### ⚠️ Il debito di collaudo, dichiarato

Il ritrovamento del gruppo **partendo dalla commessa quando la commessa alimenta
davvero quel gruppo** non è coperto da pgTAP: servirebbe una commessa con le sue
attività. È coperto il verso opposto.
⇒ Si verifica **sul primo giro vero** dopo P-5. Se lì il conto tornasse a zero,
il messaggio da cercare nei log è `pull_commesse.esito_non_appeso`.

### ⚠️ Chi guarda il presidio

`vw_lotti_chiusi_con_gruppi_in_errore` non ha un cruscotto: a sorvegliarla è il
**test 9** della suite, a ogni corsa — ed è il **test 10**, che costruisce il
caso cattivo, a impedirle di diventare verde per sottrazione.

---

## 17. ✅ La separazione — applicata e verde il 2026-09-07

> **Decisione di Tid:** *«fonte unica, e giro mirato e di massa si devono
> comportare alla stessa maniera»*. Più: **niente recupero dei dati vecchi,
> siamo in test.**

### Perché non bastava il consuntivo

Cercando un posto che esistesse già ho trovato `vendite.fn_esito_gruppi_giro` —
il consuntivo di un giro, un documento per riga, SERVITO / NON_SERVITO /
FATTURATO_ALTROVE — che **funziona già anche sui giri di massa**.

⛔ Ma risponde a un'altra domanda: *«com'è andata quella corsa»*, non *«perché
questo documento non è passato»*. E il motivo, oggi, sta nel giornale, legato
alla **commessa** e non al documento.

⇒ Tenere il motivo derivato dal giornale avrebbe reso le colonne sul perimetro
una **seconda copia** dello stesso fatto. Fonte unica vuol dire il contrario:
una scrittura, tutti leggono di lì.

### I cinque changeSet, e l'ordine è portante

| | Cosa |
| --- | --- |
| **`20260907-12`** | `vendite.fatturazione_lotti_esiti` — una riga per (lotto, documento), creata quando c'è qualcosa da dire |
| **`20260907-13`** | `fn_segna_esito_gruppo_lotto` scrive lì. **Stessa firma, stesso valore di ritorno** |
| **`20260907-14`** | la competenza legge l'ultimo tentativo dalla casa nuova |
| **`20260907-15`** | il presidio idem — e così vede anche i lotti **senza perimetro** |
| **`20260907-16`** | il perimetro perde le quattro colonne e torna a rispondere a una domanda sola |

⚠️ Il `-16` ha il numero più alto **apposta**: le due viste dipendono da quelle
colonne, e un `DROP COLUMN` con una vista attaccata non passa. L'autogen ordina
`00_schema` e `20_code` insieme per numero, quindi il `-16` arriva dopo il `-14`
e il `-15`. ⛔ Rinumerarlo più in basso romperebbe il migrate.

### ⭐ Il backend non tocca niente

Chiamava già la funzione per ogni commessa, mirata o di massa. Su un giro di
massa la chiamata partiva, non trovava la riga e tornava `0` con il suo avviso.
Adesso **la riga si crea**: la stessa identica chiamata comincia a funzionare.

⇒ Il §12.4 si chiude senza una riga di codice in più dall'altra parte.

### Due scelte di modello che vale la pena non riscoprire

* ⭐ **`stato_esecuzione` qui è obbligatorio.** Sul perimetro doveva essere
  nullabile («nessuno l'ha detto»); qui la riga *nasce* quando qualcuno lo dice,
  quindi il non-detto è l'**assenza della riga**. Sparisce lo stato di mezzo,
  che è sempre il più difficile da leggere.
* ⚠️ **La chiave è (lotto, documento)**, quindi un secondo tentativo
  **sovrascrive**. La domanda è *«com'è finita»*, non *«quante volte ci abbiamo
  provato»*: lo storico dei tentativi vive nel giornale del lotto, che è fatto
  per quello.

### Il collaudo

`test-lotti-gruppi-esito.sql` sale a **12 test**, con due casi nuovi che prima
non erano nemmeno costruibili:

* **7** — un lotto **senza perimetro** riceve comunque l'esito: è il buco del
  §12.4, provato invece che raccontato;
* **8** — due tentativi sullo stesso documento lasciano **una** riga, non due.

✅ **Applicati tutti e cinque, pgTAP 12/12.** Il test 7 verde è la prova che il
buco del §12.4 è chiuso: un lotto senza perimetro riceve comunque l'esito del
suo documento.

### ⛔ Il dato vecchio non si travasa

Le quattro colonne sul perimetro portano gli esiti dei giri mirati del 6 e 7
settembre. **Decisione di Tid: siamo in test, non si recuperano.** È scritto nel
`-12` e nel `-16` perché su un ambiente con dati veri quel passaggio ci sarebbe
dovuto essere, e chi rilegge deve sapere che è stato **deciso**, non dimenticato.

### ⚠️ Un difetto trovato applicando, e vale come promemoria

Il primo `migrate` si è fermato sul `-14` con *«errore di sintassi a o presso
COMMENT»*: il corpo della vista era stato ripreso dal database vivo, e
`pg_get_viewdef` **non restituisce il punto e virgola finale**. Il
`COMMENT ON VIEW` finiva così dentro la query.

⭐ Nel `-12` non era successo, perché lì il corpo era stato salvato **con** il
`;`. Stessa tecnica, due esiti — la differenza fra un passaggio verificato e uno
dato per fatto.

⇒ Rimedio, oltre alla riga: i changeSet delle viste si fanno **parsare** al
database in transazione annullata. Un `permesso negato` invece di un `errore di
sintassi` è la prova che l'istruzione è intera, perché PostgreSQL analizza prima
e controlla i privilegi dopo.

---

## 18. 🏁 Stato al 2026-09-07, fine giornata

⚠️ Questa tabella aveva **tre** colonne dichiarate come due, quindi la colonna
«chi» — proprio quella che il §16 usa per smistare il lavoro — **non veniva resa**
nella doc pubblicata. Corretta il 2026-09-07.

| | | Chi |
| --- | --- | --- |
| ✅ **DB** | quattro changeSet del 06-09 + sei del 07-09, tutti applicati. pgTAP **12/12** | *DB* |
| ✅ **Il caso originale** | un documento fallito resta nel lotto e si vede in competenza, con motivo, orario e lotto | — |
| ✅ **Il §12.4** | chiuso: anche i giri **senza perimetro** hanno dove essere marcati, e il backend non cambia una riga | *DB* |
| ✅ **P-5** | il ramo «tutte fallite» non solleva più: è stato tolto, non modificato — §20 | *backend* |
| ✅ **P-3** | il test che su quel ramo non mocka il repository, e che si accende — §20 | *backend* |
| ✅ **P-6** | `E_PULL_COMMESSA_ALL_FAILED` ritirato il 07-09 con `obsoleto_dal` — §19 | *DB* |
| ✅ **Il seed** | `migrate` passato: le colonne di catalogo e la scheda «Presi in carico» ci sono — §21 | *Tid* |

✅ **Il debito di collaudo è caduto il 2026-09-07**: il primo giro vero
(`LTF-0009900`) ha risolto il documento partendo dalla commessa, e
`pull_commesse.esito_non_appeso` non è stato scritto — §23.1.
🔴 Resta **una** cosa, ed è del backend: il §23.3.

---

## 19. ✅ P-6 — il codice ritirato, il 2026-09-07

> **Sblocco di Tid:** *«nessuno lo solleva più, e un test lo presidia guardando
> il sorgente»*. Il backend ha già tolto il `raise`; qui si chiude la metà DB.

### Che cosa è cambiato: una riga di CSV

`80_data/sql/config/codici_errore.csv`, riga di `E_PULL_COMMESSA_ALL_FAILED`:
`obsoleto_dal` passa da vuoto a **2026-09-07**, e la colonna `note` si prende il
perché per esteso.

⭐ **Non serve un changeSet nuovo.** Quel CSV è già appeso a un mirror
`runOnChange` (il `20260614-08`): cambiare il file cambia la sua impronta, e il
prossimo `migrate` ri-esegue l'upsert. Un loader in più sarebbe una seconda sede
per la stessa cosa.

### ⛔ Ritirato, non cancellato — e la differenza è concreta

`dbops.error_log` ha una FK **NOT NULL** verso `config.messaggi_errore(id)`, e
sotto questo codice ci sono **4 righe di giornale già scritte** (misurato il
2026-09-07). Cancellarlo vorrebbe dire riscrivere il diario per far tornare i
conti a una decisione presa dopo.

⚠️ E non è `attivo = false`: un codice ritirato **continua a risolversi**.
Provato in transazione annullata — dopo il ritiro `script.fn_get_messaggio`
restituisce ancora *«Tutti i pull commessa falliti.»*. Se un percorso non ancora
bonificato lo sollevasse, l'operatore leggerebbe una frase e non un segnaposto.

### ⭐ Non ha un sostituto, e non è una dimenticanza

Gli altri ritiri di questo catalogo rimandano a un codice nuovo. Qui no: **il
caso ha smesso di essere un errore da sollevare ed è diventato un esito da
registrare.** Sta scritto nella `note`, perché la prima domanda di chi rilegge un
codice ritirato senza erede è «e allora adesso cosa si usa?».

### Le tre verifiche, prima di toccare il CSV

| Cosa poteva rompersi | Esito |
| --- | --- |
| Controllo **(D)** del guardrail — *«una funzione viva solleva un codice ritirato»* | ✅ nessuna funzione plpgsql lo nomina |
| Controllo **(C)** — *«voce di troppo nel registro dei codici legacy»* | ✅ non è nel registro |
| pgTAP che asseriscono su quel codice | ✅ nessuno |

Le prime due girate **con il ritiro già applicato**, dentro un `BEGIN` chiuso in
`ROLLBACK`: un controllo fatto prima della modifica misura il mondo di ieri.

### ⚠️ Chi presidia davvero questo ritiro — e da quando

Il controllo (D) del guardrail legge **solo i corpi plpgsql**, e lo dichiara da
sé. Questo codice lo sollevava il **Python**: (D) non lo avrebbe mai visto, né
prima né adesso.

Il presidio vero è lato backend — `test_nessun_codice_usato_e_ritirato` — e legge
l'elenco dei ritirati **dalla coda di `error_policies_generated.py`**, non dal
database.

⇒ Finché il backend non rigenera quel modulo, il ritiro è vero a catalogo ma
**non ancora presidiato**. Non è un problema di ordine — nessuna CI diventa rossa
per questo, in nessuno dei due versi — ma è la cosa da sapere: la rete si chiude
alla prossima rigenerazione, ed è un passo del backend.

> ✅ **Rigenerato il 2026-09-07** (§20), e la rete è chiusa: il codice è nella
> coda dei ritirati e `test_nessun_codice_usato_e_ritirato` lo copre.
> ⭐ Ricontrollato il 2026-09-07: il codice **continua a risolversi** — la frase
> è ancora in `error_messages_fallback.py`, quindi un percorso non bonificato
> che lo sollevasse darebbe una frase e non un segnaposto.
> 🔴 **Ma la rigenerazione NON è committata**: in `HEAD` il codice compare una
> volta sola, in `CLASSE_PER_CODICE`. La voce in `CODICI_RITIRATI`, la `note` e
> il contatore 88→89 vivono nel working tree. ⇒ La rete è chiusa **su questa
> macchina**, non nel progetto — e vale il vincolo scritto due righe sopra: fra
> il ritiro a catalogo e la rigenerazione la build è rossa, quindi i due passi
> vanno **nello stesso commit**.
> ⚠️ **Ma una CI rossa c'era**, e vale la pena saperlo: non quella del
> guardrail, `test_il_file_generato_e_allineato_al_catalogo` — che confronta il
> modulo generato con `config.vw_codici_errore_identita` **nel database**, dove
> il ritiro era già arrivato. ⇒ Fra il ritiro a catalogo e la rigenerazione la
> build è rossa, quindi i due passi vanno **nello stesso giro**, non uno «alla
> prossima occasione».
> ⭐ Verificato prima di rigenerare che il database **non fosse avanti rispetto
> a git** su nient'altro: il diff del modulo tocca solo questo codice.

### Cosa resta

| | |
| --- | --- |
| ✅ **P-6** | fatto |
| ✅ **P-3** | fatto il 2026-09-07, insieme a **P-5** — §20. Il test esercita il ramo con il repository **vero** e legge la riga scritta |
| ⚪ **P-8** | nulla: la separazione del §15 è stata fatta il 07-09 (§17) |

⚠️ Due documenti nominano ancora l'errore come comportamento atteso:
`collaudo-in-app-esito-parziale-pull-commessa.md` (prova 5, *«l'errore è
E_PULL_COMMESSA_ALL_FAILED»*) e `brief-be-fan-out-isolato-e-esito-parziale.md`.
Sono del cantiere del backend e non sono stati toccati qui: una checklist di
collaudo che pretende un errore che non arriva più manda chi collauda a cercare
un guasto che non c'è.

> ✅ **Raccolto il 2026-09-07** (§20): i due documenti sono stati allineati. Il
> rilievo era giusto — e da quando P-5 è applicato non era più un'imprecisione
> ma un'istruzione sbagliata a chi collauda.

## 20. ✅ BE + FE riallineati, e P-5/P-3 chiusi (2026-09-07)

> Chiude i due punti che il §18 rimandava al backend, e riallinea la lettura
> alla casa nuova dell'esito.

### Che cosa si era rotto, e come si è visto

Suite completa con `ZEROERP_TEST_DB_E2E=1`: **13 errori + 2 fallimenti**, tutti
nostri. ⭐ E tutti dai test che **non mockano**: i test unitari erano verdi al
100%. È la stessa lezione del §11 con un'altra faccia — *un mock non vede un
cambio di schema*.

| | |
| --- | --- |
| `list_lotto_gruppi` leggeva le quattro colonne dal **perimetro** | non esistono più: la scheda era morta |
| il cancello sul vocabolario puntava a `chk_lotti_gruppi_stato_esecuzione` | non esiste più |

⭐ La lista di **competenza** non ha richiesto una riga: la vista ha tenuto i
nomi delle cinque colonne. Il contratto verso il backend ha retto, come il §15
prometteva.

### ⭐ Non era un rename: la scheda legge l'UNIONE

I fatti sono due e indipendenti, e nessuno dei due da solo risponde:

| lotto | col solo perimetro | con l'unione |
| --- | --- | --- |
| mirato, non ancora girato | i suoi documenti, esito vuoto | idem |
| mirato, girato | i documenti con esito | idem |
| **di massa, girato** | 🔴 «nessun documento» | **i documenti che ha tentato** |

⇒ E **`perimetro_dichiarato` è sparito**, col problema che risolveva: esisteva
per rendere onesto lo zero, e zero adesso ha un significato solo. ⚠️ Tolto e non
lasciato «per compatibilità» — un campo che non discrimina più niente è peggio
di un campo assente, perché chi lo legge crede che discrimini.

⛔ E la riga non ha più un `id`: non è una riga di tabella, è l'unione di due
fatti. La chiave è il **documento** (`gruppo_key`).

### ✅ P-5 — il ramo «tutte fallite» non solleva più

⭐ **Non è stato modificato: è stato tolto.** I due rami sono diventati *lo
stesso codice*, quindi il comportamento del «tutte fallite» non va dimostrato a
parte — è quello del parziale, in esercizio da agosto.

**Che cosa ferma la catena, adesso** — la domanda vera, e la risposta era già
scritta in tre punti che non si parlavano:

1. il passo scrive una segnalazione **critica per ogni commessa caduta**, prima
   di scegliere il ramo;
2. al giro successivo `evaluate_lotto_status` risponde `blocks_next_step` e
   `run_pipeline` rifiuta di avanzare con `E_PIPELINE_LOTTO_CRITICAL`;
3. il driver esce con `BLOCCATO_CRITICITA` e `_mark_lotto_error_safely` porta il
   lotto in **ERRORE**.

⇒ *Fermarsi* e *strappare gli appunti* erano due cose che faceva lo stesso
gesto. Ora si ferma **tenendo**. Il rilancio dello stesso step resta ammesso: è
la via d'uscita.

📌 `E_PULL_COMMESSA_ALL_FAILED` non lo solleva più nessuno ⇒ **P-6 è
sbloccata**. Un test lo presidia guardando il **sorgente** (`code="…"`), perché
il ramo non esiste più e un test sul comportamento sarebbe verde per
sottrazione.

### ✅ P-3 — il test che non mocka, e che si accende

`apps/vendite/tests/db/test_pull_tutte_fallite_scrittura_reale.py` (opt-in DB,
acceso in CI). ⭐ **Che cosa è finto e che cosa no**: `commesse_repository` è
finto perché serve a *costruire* il caso; `VenditePipelineRepository` è **vero**,
ed è lui che scrive. Con un mock al suo posto il test tornerebbe a provare
un'intenzione.

⚠️ **E non prova che la scrittura sopravviva a un rollback — perché non
sopravvive, e non deve.** La riga è un `INSERT` normale nella transazione del
chiamante: ciò che protegge i segni è che quel ramo non sollevi. La chiamata è
avvolta nello stesso `atomic()` che tiene `run_pipeline`, cioè nello specchio
esatto del confine che il 06-09 si portava via le marcature.

✅ **Verificato che si accende**: rimettendo il `raise`, entrambi i test
diventano rossi — il primo perché l'eccezione esce, il secondo perché le righe
spariscono. È la riproduzione fedele del difetto originale.

### Il collaudo, sul database vero e in transazione annullata

| | prima | dopo |
| --- | --- | --- |
| lotto **mirato** (`LTF-0009578`) | 3 documenti, esito vuoto | 3, di cui **1 ERRORE** in cima col motivo |
| lotto **di massa** (`LTF-0009398`) | 🔴 0 documenti | **2 documenti** marcati (`marcati: 2`, prima era `0`) |
| ramo **tutte fallite** su lotto senza perimetro | sollevava, rollback | `TaskEsitoParziale`, e la scheda mostra **3 documenti** |

Suite: **4526 test verdi**, anche con `ZEROERP_TEST_DB_E2E=1`.

### 🔵 Che cosa resta

⭐ **P-6 è arrivato nel frattempo** (§19): il codice è ritirato con
`obsoleto_dal`, e il presidio nel backend guarda che nessuno lo sollevi più. Le
due metà si sono incontrate senza doversi aspettare.

### ✅ Raccolti nello stesso giro, dal §19

| | |
| --- | --- |
| **Il modulo generato** | `error_policies_generated.py` rigenerato: il codice entra nella coda dei ritirati, e `test_nessun_codice_usato_e_ritirato` lo copre. ⚠️ Non era «alla prossima occasione»: `test_il_file_generato_e_allineato_al_catalogo` confronta il modulo col **database**, dove il ritiro era già arrivato — quindi fra i due passi la build è rossa. ⭐ Verificato che il DB non fosse avanti su nient'altro: il diff tocca solo questo codice |
| **I due documenti** | il collaudo in-app e il brief del fan-out pretendevano ancora quell'errore. Da quando P-5 è applicato non era più un'imprecisione ma un'**istruzione sbagliata**: la prova 5 diceva di segnalare se lo step *prosegue*, che ora è il comportamento voluto. Riscritta col segnale d'allarme spostato — il difetto è che il lotto **avanzi** |
| **`FanOutEsito.tutti_falliti`** | tolto: era `esito == ESITO_ERRORE` e a leggerlo era solo il ramo che P-5 ha rimosso. ⛔ Un alias con zero lettori su un BB condiviso sembra API in uso e non lo è. Il fatto resta dov'era, e i test lo asseriscono su `esito` |

| # | Cosa | Chi |
| --- | --- | --- |
| ✅ | ~~`migrate` del seed per le colonne di catalogo e la scheda «Presi in carico»~~ — **passato**, verificato il 2026-09-07 (§21) | Tid |
| 🔴 | Il debito di collaudo del §18 — il ritrovamento del documento **partendo dalla commessa** — si chiude sul **primo giro vero**, e finché non si chiude questo brief resta in `work-in-progress` (§21) | — |

---

## 21. ✅ Le due spunte, verificate nel repo il 2026-09-07

> Passaggio di verifica, non di sviluppo: le due voci qui sotto erano **già
> fatte** e il documento non lo diceva. ⚠️ Un brief che elenca come «da fare»
> qualcosa di già fatto manda a rifarlo, ed è il modo in cui una checklist
> smette di essere creduta.

### ✅ Il `migrate` del seed è passato

Confronto CSV ↔ database vivo, 2026-09-07:

| | CSV | DB | mancanti |
| --- | ---: | ---: | ---: |
| `ui.lista_definizione` | 67 | 67 | **0** |
| `ui.lista_colonna` | 735 | 735 | **0** |

⇒ `vendite.lotto_gruppi` (definizione **67**) è a catalogo con le sue **8**
colonne: la scheda «Presi in carico» monta una lista **con** colonne, e le
opzionali della competenza ci sono. Il §12.6 è chiuso.

### ✅ Il presidio del ritiro è armato

`error_policies_generated.py` rigenerato **e committato** (`fe4d31a64`):
`E_PULL_COMMESSA_ALL_FAILED` è dentro `CODICI_RITIRATI`, con la `note` del ritiro
e il marcatore `⚠️ RITIRATO il 2026-09-07` sopra la voce in `CLASSE_PER_CODICE`.
⇒ La riserva del §19 — *«il ritiro è vero a catalogo ma non ancora presidiato»* —
**non vale più**.

### ⚠️ E una verifica che ha dato l'esito opposto

`vendite.fatturazione_lotti_esiti` ha **zero righe** (2026-09-07). Nessun giro è
ancora passato dalla marcatura.

⛔ **Ne discende che il presidio `vw_lotti_chiusi_con_gruppi_in_errore` oggi è
vuoto per SOTTRAZIONE**, non per salute: non ha ancora avuto materia su cui
essere rosso. Il §16 lo sa a metà — dice che a sorvegliarlo sono i test 9 e 10
del pgTAP — ma in **esercizio** quella vista non ha ancora detto niente, e finché
è così «è verde» non è una notizia.

⚠️ Lo zero è stato letto **col contesto operatore**, prima di usarlo come
argomento: `fatturazione_lotti_gruppi` ed `_esiti` non hanno RLS,
`fatturazione_lotti` sì e nello stesso giro mostra **64** righe — quindi il
contesto morde e quello zero è un dato, non un perimetro. ⛔ Su una tabella con
RLS un conteggio senza contesto torna zero **e sembra un dato**.

⇒ È esattamente il debito del §18, guardato da un'altra parte: **il criterio di
chiusura del §6 chiede un giro vero, e il giro vero non c'è ancora stato.**

### ⚠️ Fatto datato: la suite regge, anche dove non mocka

`ZEROERP_TEST_DB_E2E=1 ./manage-test.sh` → **4528 test verdi** (2026-09-07). È il
verso in cui il §20 aveva trovato 13 errori + 2 fallimenti, quindi vale la pena
che il numero resti scritto con la sua data.

⛔ **Ma il lavoro del §20 non è nel repo**: BE, FE, la doc di
`api_lotto_gruppi_list` e i due documenti di collaudo sono **16 file modificati +
2 test nuovi non committati**. Finché restano lì, «fatto» descrive una macchina,
non il progetto — ed è la seconda cosa che tiene aperto questo brief.

---

## 22. 🔴 Il presidio ha parlato, il 2026-09-07 — e non era rumore

Il pgTAP `test-lotti-gruppi-esito.sql` è diventato rosso sul test 11, e la
reazione naturale — *«è un test fragile, si è rotto perché ho rigenerato un
lotto»* — è **sbagliata su tutti e due i pezzi**. Vale la pena scrivere perché.

### 22.1 La riga è vera, e la contraddizione pure

`vendite.vw_lotti_chiusi_con_gruppi_in_errore` ha nominato **`LTF-0009900`**
(lotto 11069, emittente 72, competenza 2026-09). Non è un lotto di fixture
lasciato indietro: è una corsa reale delle 11:25.

Il lotto è **2 su 3** — due documenti `COMPLETED`, uno `ERRORE` con
`E_PULL_COMMESSA` (*«ProgrammingError: Indicare un valore per…»* sulla commessa
34137).

⭐ **E la salvezza indiretta di cui parla il `20260907-11` ha fatto la sua
parte**: la segnalazione critica **c'è**.

| | quando |
| --- | --- |
| segnalazione **critica** (`status = 'C'`) | 11:25:38.294 |
| esito ERRORE del documento | 11:25:38.301 |
| lotto messo **COMPLETATO** (`data_update`) | **11:28:43** |

E `vendite.fn_get_lotto_segnalazioni_summary(11069)` risponde
`lotto_critical_count = 1`. ⇒ `evaluate_lotto_status` calcola
`is_error = critical_count > 0 or …` → **vero**.

⛔ **Il riepilogo diceva ERRORE, e tre minuti dopo il lotto è stato chiuso
COMPLETATO lo stesso.** Non è una corsa fra scritture: il conteggio era già a 1.

⚠️ **Quello che questi dati NON dicono**, e va detto invece di riempirlo di
ipotesi: *chi* ha messo `COMPLETATO` alle 11:28. Può essere un percorso di
chiusura che non consulta `evaluate_lotto_status`, oppure un'azione a mano
durante il collaudo. Il database registra lo stato, non il gesto. ⇒ La domanda è
del backend, ed è **l'unica cosa che questa sezione chiede**.

⭐ Comunque sia andata, la vista ha fatto esattamente ciò per cui è nata il
giorno prima: *«un difetto che si manifesta come SILENZIO è esattamente ciò per
cui questo cantiere è nato. Si mette un presidio, invece di fidarsi.»*

### 22.2 ⛔ E il test 11 era comunque sbagliato — per un'altra ragione

Non era «legato a un lotto»: era legato a **tutti**. Chiedeva che la vista fosse
vuota sull'**intera popolazione**, ed è la forma che la Regola zero vieta:

* su un database ricostruito da zero — cioè **in CI** — la vista è vuota perché
  non c'è niente: il test passava **a vuoto**, verde senza provare nulla;
* su dbdev diventava rosso al primo uso reale che produce quello stato, e **un
  rosso che non è una regressione insegna a ignorare i rossi**.

⚠️ Contraddiceva anche la riga scritta in testa allo stesso file: *«TUTTI I CASI
SONO COSTRUITI… nessuna asserzione si appoggia a un lotto vero»*.

✅ **Riscritto** come **controllo negativo** sullo stesso lotto costruito del
test 12: prima la contraddizione non c'è e la vista tace, poi la si crea e la
vista parla. Provato in entrambi i versi — con la contraddizione anticipata il
test 11 diventa rosso, senza la contraddizione il 12 diventa rosso.

⭐ **La domanda «e il database vero è pulito?» non è sparita**: si risponde
**guardando la vista**, che è ciò per cui un presidio esiste. Un pgTAP che
interroga la popolazione non è un test, è monitoraggio travestito — e con quella
forma la risposta di oggi sarebbe arrivata come un test rotto invece che come un
ritrovamento.

### 22.3 Che cosa resta

* 🔴 **Al backend**: capire chi ha chiuso `LTF-0009900` COMPLETATO con il
  riepilogo che diceva ERRORE. Se è un percorso di codice, è un difetto; se è
  un'azione a mano, allora **un'azione a mano può produrre la contraddizione**, e
  vale la pena sapere se deve poterlo fare.
* ⚠️ La riga resta a database: è un dato di collaudo, e finché c'è la vista la
  nomina — che è corretto. ⛔ Non si «pulisce» per far tacere il presidio.

---

## 23. 🏁 Chiusura — che cosa è caduto oggi, e l'unica cosa che resta

> Rilettura del 2026-09-07 dopo il push del backend (`993cdb91e`).

### 23.1 ✅ Il debito di collaudo del §16 è chiuso — da un giro VERO

Il §16 lo diceva così: *«il ritrovamento del gruppo partendo dalla commessa
quando la commessa alimenta davvero quel gruppo non è coperto da pgTAP… si
verifica sul primo giro vero dopo P-5»*.

**Il primo giro vero c'è stato**: lotto `LTF-0009900`, 2026-09-07 alle 11:25, tre
commesse, una fallita.

⭐ **E la strada percorsa è proprio quella**, verificato sul chiamante:
`_marca_esito_gruppi` invoca `segna_esito_gruppo_lotto(lotto_id, stato,
commessa_id=…)` — passa **solo la commessa**, un `gruppo_key` non lo passa mai.
Quindi la risoluzione commessa → documento è l'unica strada possibile, non una
fra due.

**Esito**: tutti e tre i gruppi hanno una chiave documento reale, compreso quello
fallito —

```
133 | ORDINE_VENDITA:01a06ce4-b46a-7a49-a72f-c07c29de47bb | ERRORE | E_PULL_COMMESSA
```

⇒ La funzione ha restituito un aggancio, quindi **`pull_commesse.esito_non_appeso`
non è stato scritto**: era il segnale che il §16 diceva di cercare se il conto
fosse tornato a zero. Non è tornato a zero.

### 23.2 ✅ E il §20 è nel repo

*«il lavoro del §20 non è nel repo: 16 file modificati + 2 test nuovi non
committati»* — caduto col push `993cdb91e`. «Fatto» adesso descrive il progetto,
non una macchina.

### 23.3 🔴 Resta una cosa sola, ed è del backend

Quella del §22: **`LTF-0009900` è COMPLETATO mentre il riepilogo diceva ERRORE.**

Non è un residuo di collaudo da spazzare: è il punto in cui la decisione P-5
(«trattiamo il 3 su 3 come il 2 su 3») incontra chi decide lo stato finale del
lotto. Il §22 porta i tre orari e il conteggio; la domanda che manca è **chi ha
scritto `COMPLETATO` alle 11:28** con `lotto_critical_count = 1`.

* se è un percorso di codice che chiude senza consultare
  `evaluate_lotto_status` → è un difetto, e sta esattamente dove questo cantiere
  ha messo il presidio;
* se è un'azione a mano → allora **un'azione a mano può produrre la
  contraddizione**, e la domanda diventa se debba poterlo fare.

⛔ In nessuno dei due casi la risposta è cancellare la riga.

### 23.4 Quando questo brief si chiude

✅ **Il §23.3 ha avuto la sua risposta lo stesso giorno: era l'annullo — §24.**
Il changeSet `20260907-08` la chiude, con il presidio sui due versi.

⇒ Lato DB resta solo l'applicazione di `20260907-17` (un `COMMENT`: il presidio
dichiara il proprio pregresso — §25). L'unica coda vera è a video (§24.5): un
lotto annullato che era andato male mostrerà `ERRORE` e «Annullata» insieme, ed
è da guardare che il badge non risulti contraddittorio.

---

## 24. ✅ La risposta al §23.3 — l'ha data Tid, ed era l'annullo

> 2026-09-07. **Domanda chiusa**: *chi ha scritto `COMPLETATO` alle 11:28 con
> `lotto_critical_count = 1`?*

**L'operatore, annullando il lotto.** `vendite.fn_annulla_lotto_da_draft`
scriveva `stato_lotto = 'COMPLETATO'` dentro l'`UPDATE` di chiusura.

⭐ **Verificato dal vivo mentre si indagava**: `LTF-0009931` era in `ERRORE` alle
12:02, Tid l'ha annullato, ed è diventato `COMPLETATO / CHIUSO / ANNULLATA`.
Stessa forma di `LTF-0009900`, riprodotta a comando.

⇒ Non era un percorso di chiusura che salta `evaluate_lotto_status`: era un
`UPDATE` diretto, tre minuti dopo, che passava **dietro** al guardiano.

### 24.1 ⛔ Tre regole infrante dalla stessa riga

1. **La macchina a stati la vieta.** `fn_set_fatturazione_lotto_stato` rifiuta
   `ERRORE → COMPLETATO` — *«da ERRORE solo IN_ESECUZIONE»*. L'`UPDATE` diretto
   non gliel'ha mai chiesto, quindi non è che il guard l'abbia permesso: **non
   l'ha vista**.
2. **La sorella dice di non farlo.** `fn_riporta_lotto_a_draft` porta nel corpo
   la riga *«stato_lotto NON si tocca — ha una macchina a stati cablata»*.
   ⭐ E l'intestazione dell'annullo invoca **proprio quella sorella** come
   principio: *«due sorelle non possono comportarsi diversamente sulla stessa
   cosa»*.
3. **È la cosa che quell'intestazione rifiuta due paragrafi sopra**, parlando di
   `attivo`: *«sono due domande su un flag solo, e il giorno che dissentono non
   c'è scritto da nessuna parte quale vince»*. `stato_lotto` risponde a «com'è
   andata l'elaborazione»; «non è più in lavorazione» lo dicono già
   `stato_operativo = 'CHIUSO'` e `stato_doc_fiscale_id = ANNULLATA`, che quello
   stesso `UPDATE` scrive.

### 24.2 ⭐ E non reggeva niente — verificato, non supposto

Il problema che quella riga sembrava servire — un lotto annullato che resta fra
gli «errori vivi» del cruscotto — l'ha risolto la rev del 2026-09-04 **chiudendo
i task run per esito**. L'intestazione lo dice: *«la vista non si tocca: i run
cadono da soli, PER ESITO»*.

Riletto il 07-09: `vw_dash_competenza_errori` `stato_lotto` lo **proietta**
soltanto, non ci filtra. E nessuna funzione lo usa come cancello pretendendo
`COMPLETATO` su un annullato — le uniche guardie sono su `IN_ESECUZIONE`.

### 24.3 ⚠️ Una cosa detta male, e corretta dal test

Prima stesura della nota: *«era un no-op sul lotto andato bene»*. **Falso**, e a
dirlo è stato il test scritto per provarla:

```
# Failed test 6: "su un lotto mai andato in errore l'annullo lascia lo stato che aveva"
#         have: COMPLETATO   want: IN_ESECUZIONE
```

Un lotto annullato **mentre era in esecuzione** veniva marcato `COMPLETATO`,
cioè *«la corsa è finita bene»* — di un giro che nessuno ha finito, è stato
interrotto.

⇒ Quella scrittura **falsificava in entrambi i casi**. Sul lotto fallito
cancellava l'errore; su quello vivo dichiarava una conclusione mai avvenuta.
Cambia solo quanto è visibile la bugia.

### 24.4 Che cosa è entrato

| Cosa | Dove |
| --- | --- |
| `fn_annulla_lotto_da_draft` non scrive più `stato_lotto` | `20260907-08` |
| Il presidio della regola, sui due versi | `db/pgtap/vendite/test-annulla-lotto-non-riscrive-stato-v1.sql` (plan 7) |
| L'asserzione `stato_lotto = 'COMPLETATO'` tolta da dove era di passaggio | `test-fatturazione-reset-lotto-draft.sql` (test 6) |

⭐ **Il test 4 è quello che tiene onesto il test 2**: da solo, il 2 passerebbe
anche su una funzione che scrive **sempre** `'ERRORE'` — lo stesso difetto
ribaltato. La coppia prova che la colonna non viene *toccata*, non che viene
scritta in un altro modo.

⚠️ E il **test 5** guarda il **testo** della funzione: è l'unico modo di dire
«non la scrive» invece di «oggi non l'ha scritta». Il perimetro è quella
funzione, ed è dichiarato: la regola è sua.

Provato al contrario: contro la funzione **viva** i test 2, 4 e 5 diventano
rossi, con `have: COMPLETATO`.

⚠️ Il corpo è stato preso dalla **doc auto-gen**, non da uno YAML, e modificato
in un punto solo — `stato_lotto` compariva **una volta sola** in tutta la
funzione. ⛔ E la doc auto-gen stampa il corpo **senza** il `;` dopo
`$function$`: aggiunto, perché senza si rompe al primo statement che segue.

### 24.5 ✅ Che cosa restava, ed era a video — risposto il 2026-09-08 (§26)

Un lotto annullato che era andato male ora mostrerà **`ERRORE`** *e*
**«Annullata»**. Sono due informazioni diverse ed entrambe vere, ma il frontend
legge `stato_lotto` in quattro file
(`LottiListView`, `LottiLista`, `LottoDrawer`, `stores/lotti`).

⇒ Vale la pena guardare che il badge non risulti contraddittorio. ⛔ Se lo
fosse, il rimedio **non** è rimettere quella riga: è decidere che cosa mostrare
quando le due cose divergono — e che divergano è il punto, non l'incidente.

---

## 25. ✅ Il pregresso — misurato, e lasciato com'è per decisione

> 2026-09-07, dopo l'applicazione del `20260907-08` (19:09).

### 25.1 ⛔ Prima misura sbagliata, e come si è vista

Chiedendo allo storico *«quali lotti hanno una transizione in cui `COMPLETATO`
ha sovrascritto un altro stato?»* venivano fuori **21** lotti. Sbagliato.

⚠️ Dieci di quei ventuno sono `DEFINITIVA`, cioè **chiusure normali**: un lotto
che finisce bene passa proprio da `IN_ESECUZIONE` a `COMPLETATO`. La query
riconosceva la *forma* della transizione e non la sua *causa*, e senza il
controllo su `stato_doc_fiscale_id` avrei proposto un ripristino su dieci righe
sane.

⭐ Il perimetro vero: **11 lotti**, tutti `ANNULLATA`, tutti in `ERRORE` un
istante prima dell'annullo — lo storico conserva il valore sovrascritto per
ciascuno.

### 25.2 ⚠️ E il presidio vede sei di quegli undici

Gli altri cinque erano in `ERRORE` per le **segnalazioni critiche**, senza avere
nessun gruppo marcato: la vista cerca la coppia «COMPLETATO + gruppo in ERRORE»,
e su di loro il secondo pezzo manca.

⇒ **Questa vista non è il perimetro del difetto.** È la seconda volta in due
giorni che un presidio viene scambiato per la misura di ciò che sorveglia — la
prima è il §22.2, dove il test 11 chiedeva alla vista di essere vuota su tutta la
popolazione.

### 25.3 ✅ La decisione: il pregresso non si corregge

**Tid, 2026-09-07.** Era possibile — lo storico ha il valore vero per tutti e
undici — ma rimetterlo a posto vorrebbe dire un `UPDATE` diretto: la macchina a
stati vieta anche `COMPLETATO → ERRORE`. Cioè la stessa scorciatoia che il
`20260907-08` ha appena tolto di mezzo.

### 25.4 ⛔ E allora l'invariante della vista cambia — `20260907-17`

Una vista che dichiara *«deve restare VUOTA»* e non lo è mai insegna a
ignorarla: chi la apre vede sei righe, non sa perché, e la volta dopo non la
apre. Il changeSet del presidio lo diceva di sé: *«oggi è vuota, e deve
restarci: è la condizione che un presidio deve sapere raggiungere, altrimenti è
rumore»*.

⇒ Il commento della vista ora dichiara:

* l'invariante non è più «vuoto» ma **«nessuna riga non dichiarata»** — la stessa
  forma di `dbops.processi_bersagli.debito_dichiarato`;
* ⭐ **il criterio, non il numero**: sono i lotti **annullati prima del
  2026-09-07 19:09**. «Sei» invecchia — basta che qualcuno ne corregga uno a
  mano — il criterio no;
* che il pregresso **non può crescere**, verificato: zero righe della vista
  aggiornate dopo quell'istante;
* ⇒ **una riga su un lotto annullato dopo quel momento è un allarme vero.**

⛔ **E non si filtrano via.** Nasconderle renderebbe la vista verde su una
falsificazione che c'è davvero, e toglierebbe l'unico posto in cui quei sei
lotti sono nominati. Si vedono, e si sa perché.

### 25.5 Che cosa resta

* ✅ `20260907-17` **applicato**: verificato il 2026-09-08 leggendo il commento
  della vista dal database — dichiara il criterio del pregresso (i lotti
  annullati prima del `2026-09-07 19:09`), non il numero.
* ✅ La coda del §24.5 è stata guardata, e il difetto c'era — ma non dove lo si
  aspettava: **§26**.

---

## 26. ✅ La coda del §24.5 — guardata il 2026-09-08, e il difetto non era il badge

> Il §24.5 chiedeva: *«un lotto annullato che era andato male mostrerà `ERRORE`
> e «Annullata» insieme… vale la pena guardare che il badge non risulti
> contraddittorio»*.

**Il perimetro esiste**: cinque lotti in `stato_lotto = ERRORE` con stato fiscale
`ANNULLATA` — `LTF-0010261`, `LTF-0009971`, `LTF-0010003`, `LTF-0010227`,
`LTF-0010225` (più `LTF-0010162`).

### 26.1 ⭐ I due badge NON sono contraddittori

Rispondono a due domande diverse, e la schermata già le tiene separate: il `Tag`
di `stato_lotto` dice **com'è andato il giro**, quello di
`stato_doc_fiscale_descrizione` dice **dov'è il documento adesso**. Entrambe
vere, nessuna smentisce l'altra. ⇒ Nessun rimedio: la divergenza è il punto, non
l'incidente, esattamente come il §24.5 prevedeva.

### 26.2 🔴 Il difetto era nel BANNER, ed era stato introdotto quel giorno stesso

Sul drawer di `LTF-0010227`, `LTF-0010225` e `LTF-0010162` — annullati, con una
critica viva che nomina un documento — il banner delle segnalazioni diceva:

> «Il giro è fermo per 1 documento su 3: **si toglie dal giro e il lotto riparte
> con quelli che restano**.»

⛔ E **due righe sotto, la stessa schermata rifiutava quel gesto**: l'azione
«Togli dal giro» era spenta con `lotto_non_pre_fiscale` — *«Il lotto è oltre lo
stato pre-fiscale: non se ne può più togliere niente»*.

⚠️ Un rimedio promesso dall'intestazione e negato dalla riga è il **vicolo cieco**
che le linee guida vietano: peggio di nessun suggerimento, perché manda a cercare
un pulsante che non c'è.

⭐ **E la frase vecchia aveva lo stesso vizio in forma più debole** — «N
segnalazioni critiche bloccano l'avanzamento» su un lotto che non avanza più. Il
banner nuovo lo ha reso **visibile** perché nomina un gesto: è la ragione per cui
questa coda andava guardata a video e non dedotta.

### 26.3 Il rimedio

Su un lotto **congelato** le critiche sono **storia**, non lavoro:

* la frase è al passato e **non nomina nessun gesto**;
* il banner non è più rosso — un allarme rosso su un giro chiuso insegna a
  ignorare gli allarmi rossi.

⭐ **La soglia si LEGGE, non si riscrive**: `stato_congela_fiscale` del catalogo,
la stessa che `useLottoAzioni` consulta per proporre i verbi. ⛔ Non
`stato_doc_fiscale_codice !== 'DRAFT'`, che era l'ennesima copia della soglia —
tolta da quello **stesso file** il 2026-08-31.
⚠️ Fail-closed (`=== false`): un dettaglio non ancora arrivato non conta come
«si può rimediare».

### 26.4 ⭐ Che cosa insegna, oltre al caso

Il §24.5 non chiedeva di correggere un badge: chiedeva di **guardare una
divergenza**. Guardandola, i badge erano a posto e il difetto stava in una frase
scritta lo stesso giorno da un altro cantiere.

⇒ *Una coda di collaudo vale anche quando l'ipotesi è sbagliata* — e questa lo
era: cercava un difetto nel posto in cui non c'era, e ha trovato quello vero
accanto.

