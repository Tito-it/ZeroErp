# Brief DB — un documento che il lotto non riesce a fatturare deve dirlo

> **Destinatari:** team DB (`dev/db-tid`) e backend.
>
> **Tipo:** brief di cantiere. ⚠️ **Scritto dopo lo sviluppo della metà DB**
> (richiesta di Tid, 2026-09-06): serve a fissare il caso, le decisioni e — più
> di tutto — **che cosa resta e a chi**.
>
> **Stato:** 🟢 **metà DB completa.** `-10` e `-11` applicati e verdi;
> ⏳ **`-12` scritto e da applicare** (la vista che mostra l'esito in competenza,
> residuo R-3). pgTAP **7 su 8** — il test 7 diventa verde con il migrate.
> 🔴 **Il backend non è ancora stato toccato**, e finché non chiama la funzione
> non cambia niente per chi guarda: il contratto è nel **§8**.
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
