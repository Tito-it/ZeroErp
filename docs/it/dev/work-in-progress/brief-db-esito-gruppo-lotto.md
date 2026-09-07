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
> 🔴 Resta **P-3 al backend**: un test sul ramo «tutte fallite» che non mocka il
> repository.
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

### 12.6 🔴 Prima che si veda in applicazione

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
| **P-5** | Il ramo «tutte fallite» torna un esito invece di sollevare, come il parziale | BE | 🔴 da fare |
| **P-3** | Un test su quel ramo che **non mocka** il repository | BE | 🔴 resta |
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
| **P-5** | Il ramo «tutte fallite» torna un esito invece di sollevare |
| **P-3** | Un test su quel ramo che **non mocka** il repository: il limite precedente è sfuggito proprio perché i test provano che la chiamata avvenga, non che la riga resti |

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

| | |
| --- | --- |
| ✅ **DB** | quattro changeSet del 06-09 + sei del 07-09, tutti applicati. pgTAP **12/12** |
| ✅ **Il caso originale** | un documento fallito resta nel lotto e si vede in competenza, con motivo, orario e lotto |
| ✅ **Il §12.4** | chiuso: anche i giri **senza perimetro** hanno dove essere marcati, e il backend non cambia una riga |
| 🔴 **P-5** | il ramo «tutte fallite» torna un esito invece di sollevare | *backend* |
| 🔴 **P-3** | un test su quel ramo che **non mocka** il repository | *backend* |
| ✅ **P-6** | `E_PULL_COMMESSA_ALL_FAILED` ritirato il 07-09 con `obsoleto_dal` — §19 | *DB* |

⚠️ Il debito di collaudo dichiarato resta: il ritrovamento del documento
**partendo dalla commessa** si verifica sul primo giro vero. Se lì il conto
tornasse a zero, il messaggio da cercare nei log è
`pull_commesse.esito_non_appeso`.

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

### Cosa resta

| | |
| --- | --- |
| ✅ **P-6** | fatto |
| 🔴 **P-3** | un test sul ramo «tutte fallite» che **non mocka** il repository — *backend* |
| ⚪ **P-8** | nulla: la separazione del §15 è stata fatta il 07-09 (§17) |

⚠️ Due documenti nominano ancora l'errore come comportamento atteso:
`collaudo-in-app-esito-parziale-pull-commessa.md` (prova 5, *«l'errore è
E_PULL_COMMESSA_ALL_FAILED»*) e `brief-be-fan-out-isolato-e-esito-parziale.md`.
Sono del cantiere del backend e non sono stati toccati qui: una checklist di
collaudo che pretende un errore che non arriva più manda chi collauda a cercare
un guasto che non c'è.
