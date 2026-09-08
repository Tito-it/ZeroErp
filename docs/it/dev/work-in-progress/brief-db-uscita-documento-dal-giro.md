# Brief DB — un documento rotto non tiene in ostaggio il giro

> **Destinatari:** team DB (`dev/db-tid`), backend e frontend.
>
> **Tipo:** brief di cantiere, **scritto prima dello sviluppo**.
>
> **Stato:** 🟢 **il verbo è scritto e funziona end-to-end.**
> ✅ **Applicati** (`migrate` del 2026-09-08 12:21): `20260908-01` (lo stato
> `ESCLUSO` + il timbro), `-02` (`gruppo_key` sul log), `-03` (il trigger che
> governa l'uscita), più i **quattro codici errore** a catalogo.
> ✅ **Applicati** anche `-04` (la vista della catena + chi viene trascinato),
> `-05` (la check), `-06` (**la madre**), `-07` (il conteggio preciso).
> ✅ **Applicati** anche `-08` (la colonna «Documento» sulla scheda Segnalazioni)
> e `-09` (il presidio — §5.6, **non** quello promesso: era vacuo).
> ✅ **pgTAP `test-uscita-documento-dal-giro-v1.sql`: 17 su 17**, e la baseline
> `vendite` non ha regressioni. Una l'aveva trovata — sul test gemello di ieri —
> ed è riparata: §7-bis.
> ✅ **Doc rigenerata** e sei pagine concettuali scritte in `manual/`; le tre
> chiavi i18n nuove sono nei locales e `check_i18n_keys.py` è **tutto pulito**.
> ✅ **D-2b decisa** (Tid): la bozza condivisa si cancella lo stesso e
> **trascina** — §5.4-bis. La proposta opposta era peggiore, e il perché è lì.
>
> 🟢 **Chiuso lato DB il 2026-09-08 — §6.1, da leggere per primo.** Il contratto
> §6 mancava di **due pezzi a database**, chiesti dal backend e consegnati:
> `20260908-18` (`script.fn_gruppi_di_commessa_nel_lotto` — la conversione
> commessa → documenti, estratta dov'era sepolta), `-19` (la madre la **chiama**
> invece di riscriverla) e `-20` (`fn_log_pipeline_fase` accetta `p_gruppo_key`).
> ✅ **pgTAP `test-gruppo-key-segnalazioni-v1.sql`: 15 su 15**, provati
> sull'SQL **estratto** dagli YAML in transazione annullata — e la mutazione
> conferma che i due presidi di §12.5.2 diventano rossi togliendo il `-19`.
> Nessuna regressione su `test-lotti-gruppi-esito`, `test-uscita-documento-dal-giro-v1`,
> `test-fn-list-lotto-segnalazioni`, `test-registri-log-orario-reale`,
> `test-fatture-log-error-code`.
> 🔴 **Correzione al §5.1**, segnalata dal BE: la colonna è **`uscita_quando`**,
> non `uscita_il`.
> ✅ **Fatto dal backend**: le tre righe del §6.1, e la corsia del pull adesso si
> sblocca — catena misurata sul database vero (§9-bis).
> ✅ **Fatte a video** tre superfici del §7 su quattro: la scheda Critiche con la
> colonna del documento e l'azione di riga, la scheda «Presi in carico» con
> l'uscita e il suo timbro, e il gesto di massa con l'esito parziale.
> 🔵 **Resta al DB — §7-ter**, da leggere per primo insieme al §9: tre cose
> piccole senza cui il §7 non è intero (le due righe di catalogo, il riferimento
> leggibile, il conteggio del banner).
> ⛔ Niente è committato, e ⛔ **niente è applicato**: i tre changeSet nuovi
> aspettano il `migrate` dell'utente. Il verde definitivo dei pgTAP si prende
> **dopo**, con `scripts/testpgtap.sh` (che gira come `zeroerp_app`, con la RLS
> attiva): la prova pre-apply gira da **owner** ed è una prova di struttura, non
> di permessi.
>
> **Origine:** Tid, 2026-09-08. ⚠️ **E la formulazione della domanda è parte del
> progetto**: la prima stesura di questo brief era appoggiata a un lotto di
> prova, e Tid l'ha rifiutata — *«tutto quello che vedi è stato simulato per
> vedere il comportamento del programma; qui dobbiamo pensare alla cosa migliore
> da progettare nel caso si verifichino situazioni simili»*. I numeri di quel
> caso restano, ma **in fondo e datati** (§10): non sono il motivo di niente.
>
> **Seguito di:** [brief-db-esito-gruppo-lotto.md](brief-db-esito-gruppo-lotto.md).
> Quello ha dato al lotto la memoria **per documento**; questo le dà una
> **conseguenza**.

---

## 0. In due parole

Un giro di fatturazione prende in carico N documenti. Uno è rotto. Il lotto va
in errore e **si ferma**: gli altri N-1, che hanno già le loro bozze, non vengono
emessi.

⇒ L'operatore deve poter dichiarare che **quel documento esce dal giro**, e il
lotto riprende. Con più documenti rotti si ripete, e il lotto riparte quando esce
l'ultimo.

---

## 1. Il problema, sul modello

**Una segnalazione che riguarda UN documento è registrata come se riguardasse il
LOTTO.**

`vendite.fatturazione_lotti_log` ha `lotto_id`, `messaggio`, `status`,
`disabilitato`, `fase`, `meta` — e **nessuna colonna che dica di quale documento
parla**. Il documento vive dentro il testo del messaggio e, quando c'è, dentro
`meta.context`. La riga stessa lo dichiara: `"scope": "LOTTO"`.

Ne discendono due cose, entrambe strutturali:

1. **Il lotto è colpevole di una colpa che non è sua.** Non ha sbagliato niente:
   ha preso in carico N documenti e uno era rotto. Ma il conteggio che decide se
   può avanzare (`fn_get_lotto_segnalazioni_summary` → `blocks_next_step`) legge
   righe intestate al lotto, quindi il lotto risulta in errore per intero.
2. **Non esiste il gesto che servirebbe.** Un verbo «togli questo documento dal
   giro» ha bisogno di sapere **quale documento**: se l'informazione non è nella
   riga, il verbo non è nemmeno esprimibile. Ed è la ragione per cui l'unica
   azione che il database offre oggi su un lotto in errore è **«Annulla»**:
   buttare via il giro intero, bozze dei documenti sani comprese.

⭐ **È la stessa mossa del cantiere precedente, sull'altra metà.** Là l'**esito**
ha smesso di essere del lotto ed è diventato del documento
(`vendite.fatturazione_lotti_esiti`). Qui deve farlo la **segnalazione**.

---

## 2. L'ipotesi di partenza, e perché cambia oggetto

**L'ipotesi (Tid):** nell'area Critiche si annulla il messaggio, e la
conseguenza è che il documento esce dal lotto.

**Il posto è giusto** — quando succede, l'operatore è lì — e resta nel disegno
(§7). **L'oggetto no**: il gesto va appeso al **documento**, non al messaggio.
Tre ragioni, tutte sul modello:

| | |
| --- | --- |
| **Un documento può avere più critiche** | Toglierlo richiederebbe N gesti, oppure un gesto che fa più di quello che il suo nome dice |
| **Una critica può non avere un documento** | Un emittente non risolto, una configurazione mancante: è del giro. Lì «togli il documento» non ha oggetto ⇒ il verbo non sarebbe definibile su tutte le righe, e un verbo che esiste solo su alcune righe è un verbo che qualcuno chiamerà sulle altre |
| ⛔ **`disabilitato` è già occupato** | È il ritiro che fa **il task** quando si rilancia lo step — la via d'uscita prevista dal cantiere precedente. Due mani sulla stessa colonna, e alla **seconda esecuzione** litigano: il task riscrive la segnalazione, il documento è già fuori, e il lotto torna bloccato per qualcosa che non ha più |

⚠️ L'ultima è quella che pesa: è un difetto che non si vede al primo giro e si
vede al secondo. *Un flag che risponde a due domande non si inverte* — la stessa
forma già pagata altrove nel progetto.

---

## 3. Le decisioni (Tid, 2026-09-08)

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-1** | Il perimetro si tocca? | ⛔ **No.** `fatturazione_lotti_gruppi` è il **criterio** del giro: dice *cosa ho chiesto di fatturare*. Il documento uscito **resta** nel perimetro e acquista uno stato. Si aggiunge un fatto, non si cancella una riga |
| **D-2** | Il documento che ha già una bozza? | Si **compone** `fn_elimina_fattura_da_lotto`, che non si tocca: semantica già decisa (RD-7) — *togliere = cancellare*, le attività tornano `NON_EMESSA`, resta storicizzata la riga di ponte |
| **D-2b** | E se la bozza copre **più** documenti? | ⭐ **Si cancella lo stesso, e li trascina**: i documenti che vengono via tornano «da emettere» e si fatturano al giro dopo. La bozza e' pre-fiscale, quindi non si distrugge niente — si rimanda. ⛔ Rifiutare l'uscita su una bozza condivisa lascerebbe bloccati anche i documenti di un'ALTRA bozza: il sequestro di partenza, in forma piu' stretta. Il loro esito torna a `PENDING`, e la conferma dichiara quanti sono — §5.4-bis |
| **D-3** | Il documento uscito può rientrare? | ⛔ **No, l'uscita è a senso unico.** Se si vuole tutto in un lotto solo, si **annulla il lotto e si rigenera** dopo aver corretto i documenti. ⭐ Questo toglie di mezzo una macchina a stati con ritorno, e lascia un unico modo di ottenere «un lotto solo» |

⭐ **D-3 è la decisione che semplifica di più**, e vale la pena dire perché: un
rientro avrebbe richiesto di decidere *cosa succede alle bozze già emesse degli
altri*, cioè un secondo progetto dentro questo. La via «annulla e rigenera»
esiste già, è già presidiata, e non ha casi di bordo.

**Decisioni prese scrivendo il disegno**, da confermare in revisione:

* **D-4** — il verbo esiste **solo su un documento in `ERRORE`**. Non è un modo
  per togliere dal giro un documento sano: quello si ottiene non mettendocelo
  (perimetro) o annullando e rigenerando. *Un verbo stretto si difende; uno largo
  va spiegato ogni volta.*
* **D-5** — il **motivo è obbligatorio**. Un documento che esce senza motivo è
  una riga che fra un mese nessuno sa spiegare.
* **D-6** — una segnalazione **senza** `gruppo_key` blocca. ⚠️ Non è una cautela
  sul pregresso (Tid, 2026-09-08: *«il pregresso non è un problema, sono solo dati
  di test»*): è **il significato della colonna**. `NULL` vuol dire *«questa
  segnalazione è del giro»*, e una segnalazione del giro deve fermare il giro —
  vale identico su una riga scritta domani.

---

## 4. Il disegno

**La segnalazione dichiara di chi è.** Una riga di
`vendite.fatturazione_lotti_log` porta il documento a cui appartiene — la stessa
`gruppo_key` che il lotto usa già per il perimetro e per l'esito. `NULL` = è del
giro.

Da lì scende tutto, e la parte che convince è che **non c'è da inventare niente**:

* **L'invariante non va scritto.** *«Il lotto avanza quando non ci sono più
  critiche vive»* è già la regola. Se la critica appartiene al documento e il
  documento esce, la critica esce con lui: con più documenti si ripete, e il
  lotto diventa avanzabile quando esce l'ultimo — **per costruzione**, non con un
  contatore da tenere allineato.
* **Non si disabilita niente.** Le critiche restano tutte leggibili, nella storia
  del lotto e del documento. Cambia solo **chi conta** per bloccare.
* **La riesecuzione non rompe più nulla.** Il task riscrive la segnalazione *sul
  documento*; se il documento non è nel giro, il lotto non la conta.
* **Il documento si porta dietro il suo errore** e torna in competenza con
  l'anomalia — che è ciò che deve succedere: non è stato fatturato.
* **La bozza si sistema da sé.** Cancellata dalla primitiva di D-2, sparisce la
  riga di ponte `fatturazione_lotti_fatture` — e con lei **i due conteggi su tre**
  che leggono di lì (§5.3), **senza nessuna modifica**. ⭐ È una conferma che D-2
  è coerente col resto, non una coincidenza.

### 4.1 Le due famiglie di critiche — e le due vie d'uscita

Con il proprietario dichiarato, la scheda Critiche si divide da sola, e le due
metà hanno vie d'uscita **diverse**:

| Critica | Che cosa può fare l'operatore |
| --- | --- |
| **di un documento** (`gruppo_key` valorizzata) | toglierlo dal giro col motivo — oppure correggere e rilanciare lo step |
| **del giro** (`gruppo_key IS NULL`) | solo correggere e rilanciare: non c'è nessun documento da togliere |

⇒ Oggi le due sono indistinguibili, ed è la ragione per cui l'unica proposta a
video è «annulla tutto». **Questa distinzione è metà del valore del cantiere**, e
si vede a schermo prima ancora del verbo nuovo.

---

## 5. Che cosa cambia a database

### 5.1 `vendite.fatturazione_lotti_esiti` — lo stato «uscito dal giro»

⭐ **Il posto c'è già.** La tabella nata ieri è *(lotto, documento, com'è
andato)*, con `UNIQUE (lotto_id, gruppo_key)` e FK **solo verso il lotto** —
quindi vale anche sui giri senza perimetro. *«Uscito dal giro»* è esattamente un
valore di *«com'è andato»*.

* allargare `chk_fatturazione_lotti_esiti_stato` per ammettere **`ESCLUSO`**;
* colonne nuove: `uscita_motivo TEXT`, `uscita_quando TIMESTAMPTZ`,
  `uscita_da TEXT`;
* `CHECK (stato_esecuzione <> 'ESCLUSO' OR uscita_motivo IS NOT NULL)` — gemello
  di `chk_..._errore_parlante` che c'è già;
* ⭐ **`uscita_quando`/`uscita_da` li deriva un trigger dalla GUC**, non il
  chiamante: è il pattern già in servizio su `dbops.coda_lavori`
  (`archiviato_il`/`archiviato_da`). ⚠️ E **non** si usano `data_update` /
  `user_update`: quelli li riscrive qualunque aggiornamento successivo, e il
  momento dell'uscita andrebbe perso in silenzio.

> 🔴 **Correzione del 2026-09-08, segnalata dal backend.** Questa sezione diceva
> `uscita_il`. La colonna vera — quella applicata dal `20260908-01` e quella che
> il backend legge — è **`uscita_quando`**. ⚠️ Non è un refuso innocuo: è la
> prima cosa che legge chi arriva dopo, e un brief che nomina una colonna che
> non esiste manda a cercare un difetto dove non c'è. *Il nome nel disegno
> insegue quello nel database, mai il contrario.*

⚠️ `ESCLUSO` è **terminale** (D-3): il guard di transizione lo rifiuta come stato
di partenza.

### 5.2 `vendite.fatturazione_lotti_log` — la colonna che manca

* `gruppo_key TEXT NULL` — `NULL` = segnalazione del giro;
* ⛔ **nessuna FK** verso `fatturazione_lotti_esiti`: la segnalazione può nascere
  **prima** dell'esito, e una FK renderebbe l'ordine di scrittura un vincolo;
* indice a supporto del join del riepilogo.

⚠️ **`NULL` blocca, e non è una cautela sul pregresso** (D-6): è il significato
della colonna. *«Questa segnalazione è del giro»* ⇒ ferma il giro. Vale identico
su una riga scritta domani da un percorso che non dichiara il proprietario — ed è
la ragione per cui non serve nessun registro del debito: non c'è niente da
sanare, c'è una colonna che vuol dire una cosa sola.

### 5.3 Il conteggio diventa preciso — e i canali che bloccano sono **TRE**

⚠️ **Da guardare prima di scrivere una riga**, perché è il punto in cui un
disegno plausibile copre due casi su tre. `blocks_next_step` è
`critical_count > 0 OR stato_esecuzione_errore_count > 0`, e i numeri vengono
tutti da `vendite.fn_get_lotto_segnalazioni_summary`, che ha **tre** aggregati:

| Aggregato | Legge | Chi ci finisce | Che cosa serve |
| --- | --- | --- | --- |
| `lotto_agg` | `fatturazione_lotti_log` | il documento caduto **prima** di diventare fattura (il pull) | 🔵 **l'unica modifica**: non contare le critiche il cui `gruppo_key` corrisponde, sullo stesso lotto, a un esito `ESCLUSO` |
| `fatture_agg` | `fatture_log` via `fatturazione_lotti_fatture` | il documento caduto **dopo** aver generato la bozza | ✅ niente |
| `ponte_agg` | `fatturazione_lotti_fatture.stato_esecuzione = 'ERRORE'` | idem | ✅ niente |

⭐ **Gli ultimi due si sistemano da soli, e per una ragione sola**: leggono
entrambi attraverso `fatturazione_lotti_fatture`, e la primitiva di **D-2**
cancella la fattura — quindi la riga di ponte sparisce e i due conteggi scendono
senza che nessuno li tocchi. *Una conferma che D-2 è coerente col resto, non una
coincidenza fortunata.*

⛔ **La regola non si duplica**: `blocks_next_step` sta in Python, somma e basta,
e **non deve sapere niente di questo cantiere**. Se un giorno serve toccarlo,
vuol dire che il conto è finito nel posto sbagliato.

### 5.4 La madre e la sua check

**`vendite.fn_escludi_documento_da_giro(p_lotto_id, p_gruppo_key, p_motivo)`**

Una `SELECT` sola, `SECURITY INVOKER`, atomica per costruzione (§5b delle linee
guida). In ordine: chiama la check, solleva il **primo** motivo se ce n'è;
compone `fn_elimina_fattura_da_lotto` **se** per quel gruppo esiste una bozza;
scrive `stato_esecuzione='ESCLUSO'` + motivo.

**`script.fn_check_documento_escludibile_da_giro(p_lotto_id, p_gruppo_key)`**

⭐ **La madre non riscrive il predicato: lo chiama** (§12.5.2 delle linee guida).
Ritorna `[]` se ammesso, altrimenti l'array **ordinato** di
`{codice, reason, reason_key, dettaglio, valori}`. I motivi, come li vedo:

⭐ **Un codice per motivo, non uno generico**, ed è una lezione già pagata dalla
sorella `fn_check_fattura_eliminabile_da_lotto`: *«codici parlanti al posto di
quattro `E_PARAMETRO_INVALIDO` indistinguibili»*.

| `reason` | `codice` | Quando |
| --- | --- | --- |
| `STATO_LOTTO_NON_PRE_FISCALE` | ⭐ `E_LOTTO_NON_PRE_FISCALE` — **riusato** | il lotto è oltre il pre-fiscale |
| `SENZA_ESITO` | `E_LOTTO_DOC_SENZA_ESITO` (409) | il gruppo non ha una riga di esito su questo lotto |
| `GIA_USCITO` | `E_LOTTO_DOC_GIA_USCITO` (409) | è già `ESCLUSO` — doppio clic, o due operatori |
| `DOCUMENTO_NON_IN_ERRORE` | `E_LOTTO_DOC_NON_IN_ERRORE` (409) | l'esito non è `ERRORE` (D-4) |

⭐ **Il primo non si conia**: `E_LOTTO_NON_PRE_FISCALE` e il suo
`STATO_LOTTO_NON_PRE_FISCALE` esistono già sulla sorella, con la stessa
condizione e la stessa via d'uscita. Coniarne un gemello sarebbe un secondo nome
per la stessa cosa.

⭐ **E il confine «pre-fiscale» non è un elenco di stati**: è il flag
`config.stati_doc_fiscale.congela_fiscale`, letto **fail-closed**
(`COALESCE(…, true)`) come fa la sorella. Un elenco scritto a mano sarebbe una
seconda sede della stessa regola, e invecchierebbe al primo stato nuovo.

⚠️ **La bozza condivisa NON è fra i motivi**, ed è una decisione — §5.4-bis.

### 5.4-bis ⭐ La bozza condivisa TRASCINA, e va bene così (D-2b, Tid 2026-09-08)

> **Il caso.** `fn_elimina_fattura_da_lotto` cancella la **fattura intera**, e
> una bozza può coprire **più documenti**: `fn_build_fattura_key` decide come le
> attività si aggregano, e niente dice che un documento fiscale corrisponda a un
> gruppo fatturabile. Lo dichiarava già il brief precedente — *«le due liste non
> sono in corrispondenza 1:1 nemmeno a giro riuscito»*.

**La prima proposta era rifiutare l'uscita su una bozza condivisa. È stata
scartata da Tid, e aveva ragione lui.**

⛔ **Quel rifiuto reintroduceva la malattia.** Se la bozza condivisa impedisce di
togliere A, allora A resta, il lotto resta bloccato — e restano fermi anche C e
D, che stanno in un'**altra** bozza e non c'entrano niente. *Un rifiuto che
lascia tutto bloccato non è una difesa: è il sequestro di partenza, in forma più
stretta.*

⭐ **E non si perde niente.** La bozza è **pre-fiscale**: nessun numero, nessun
effetto. `fn_cleanup_fatture_by_ids` riporta le attività a `NON_EMESSA` e le
libera: i documenti trascinati tornano «da emettere» e si fatturano al giro dopo.
**Rimandati, non distrutti.**
⭐ Ed è una decisione che la casa ha già preso una volta: il perimetro della
primitiva è stato allargato da «lotto in DRAFT» a «lotto pre-fiscale» proprio
perché *«il caso che conta è la fattura critica dentro un lotto EMESSA»*.

#### Che cosa succede ai documenti trascinati

⚠️ **Il loro esito non può restare `COMPLETED`**: direbbe *«B è andato bene»*
mentre B non ha più nessuna fattura. Torna a **`PENDING`** — valore che il
vocabolario ha già e che dice esattamente il vero: *preso in carico da questo
lotto, non ancora concluso*.

⛔ **Non si cancella la loro riga di esito** e **non si conia uno stato nuovo**:
il primo perderebbe il fatto che il lotto li ha presi in carico, il secondo
aggiungerebbe una parola per dire una cosa che `PENDING` dice già.
⛔ **E non diventano `ESCLUSO`**: non sono usciti da niente. Esce **uno**, gli
altri tornano in coda.

#### ⚠️ Quello che resta della preoccupazione, e non è di modello

Chiedi di togliere A e viene via anche B. **Va detto prima, non scoperto dopo.**
⇒ Non un motivo che rifiuta, ma un **avviso sull'azione**: la vista di riga
espone quanti documenti la bozza trascina, e la conferma li nomina.
⭐ È la distinzione del §12: *stato ⇒ disabilita col motivo* vale per ciò che
**non si può** fare; questa si può fare, e ha una conseguenza. Le conseguenze
stanno nella conferma, non in un rifiuto.

⚠️ **Fatto datato (2026-09-08)**, controesempio e non motivo: su 24 fatture di
lotto misurate, **7 coprono più di un gruppo** — una ne copre dieci. Dice che il
caso è raggiungibile, non come vada trattato.

⛔ **Nessun `reason` col prefisso `E_`**: è riservato ai codici a catalogo, e il
guardrail dei codici errore lo leggerebbe come un codice senza policy.

### 5.5 Codici errore — quattro nuovi, tre riusati

**Append ai CSV**, mai un loader nuovo. ✅ Fatto e verificato (§12).

| Codice | Classe | Chi lo solleva |
| --- | --- | --- |
| `E_LOTTO_DOC_USCITA_IRREVERSIBILE` | **TECNICO** (500) | il trigger, su un `UPDATE` diretto |
| `E_LOTTO_DOC_SENZA_ESITO` | `CONFLITTO_STATO` (409) | la madre, dal 1º motivo della check |
| `E_LOTTO_DOC_GIA_USCITO` | `CONFLITTO_STATO` (409) | idem |
| `E_LOTTO_DOC_NON_IN_ERRORE` | `CONFLITTO_STATO` (409) | idem |

⚠️ **Il primo è `TECNICO` e non 409, ed è la scelta che conta**: la madre chiede
prima alla check, quindi al guard ci si arriva **solo** con un `UPDATE` diretto —
un chiamante rotto, non una persona. Un 409 direbbe a un operatore di rileggere
uno stato che non ha nessun modo di cambiare.

⭐ **Riusati e non coniati**: `E_LOTTO_NON_PRE_FISCALE` (§5.4),
`E_LOTTO_NON_TROVATO` e `E_PARAMETRO_INVALIDO` per i guard di parametro.

🔵 **Contratto verso il backend, e va fatto nello stesso giro**: quattro codici
nuovi vogliono `./manage-env.sh genera_error_policies` (o
`test_error_policies_divergenza_db` diventa rosso) **e** una frase di ripiego in
`error_messages_fallback.py` per ciascuno — `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`
è rosso finché manca.

✅ **Le chiavi i18n sono già state aggiunte** (2026-09-08). Non è cortesia verso
il frontend: `check_i18n_keys.py` è diventato rosso **appena rigenerata la doc
auto-gen**, perché è da lì che legge le chiavi emesse dal database. ⇒ Una
`reason_key` nuova si chiede nello stesso giro, o si lascia dietro un cancello
rosso e un pulsante grigio col messaggio vuoto. Le tre nuove stanno sotto la
radice che il verbo usava già (`vendite.lotti.azione_reason.*`); la quarta —
`lotto_non_pre_fiscale` — non è stata coniata perché **esisteva già**.
⚠️ Il suo testo dice ancora *«non si possono più togliere fatture»*: nasce dal
verbo della funzione sorella, ed è la frase che vedrà anche chi tenta di togliere
un **documento**. Va generalizzata — una riga in ciascun locale, lato frontend.

⚠️ **Nota trovata applicando** (2026-09-08): nei CSV l'apostrofo va **semplice**.
Il raddoppio è una regola dei *letterali SQL* e in un campo CSV finisce
**letterale** nel database — `E_EMAIL_LOG_INESISTENTE` porta `l''identificativo`
nella sua `note`. Difetto cosmetico e preesistente, non toccato qui.

### 5.6 Presidio — 🔴 quello promesso era vacuo, e l'ho cambiato

Il brief prometteva una vista dei *«lotti fermi con tutte le critiche attribuite
a documenti usciti»*. Scrivendola è emerso che quella condizione **non è
raggiungibile per costruzione**: se tutte le critiche sono di documenti usciti, il
conteggio del §5.3 risponde zero e il lotto **non è fermo**. Sarebbe stata una
vista vuota per teorema.
⛔ *Un presidio che non può accendersi non è prudenza: è rumore, e chi lo apre due
volte a vuoto la terza non lo apre più.*

⭐ **Quello che vale davvero presidiare** —
`vendite.vw_segnalazioni_con_documento_ignoto`: una segnalazione **viva** il cui
`gruppo_key` non corrisponde a nessun esito di quel lotto. È un difetto vero, con
una conseguenza precisa:

* non si potrà **mai** zittire togliendo il documento dal giro — non c'è niente
  da togliere — quindi resta a bloccare il lotto per sempre;
* e l'operatore legge nella colonna «Documento» il nome di una cosa che
  nell'elenco non c'è.

⚠️ `gruppo_key IS NULL` **non entra**: è la metà sana del vocabolario.
⭐ Oggi la vista è vuota **per assenza di dato** (nessuno valorizza ancora la
colonna), non per teorema — e la differenza conta, perché diventa raggiungibile
esattamente il giorno in cui il backend comincia a dichiarare il proprietario.

---

## 6. Il contratto verso il backend

⚠️ **C'è un ordine, e non è negoziabile**: finché il backend non valorizza
`gruppo_key`, il verbo non ha su che cosa lavorare per i fallimenti di pull.

1. **Chi scrive una segnalazione critica che riguarda un documento ne dichiara la
   `gruppo_key`.** Oggi il fallimento per commessa passa da
   `_PullCommesseRunLogger.item_failed`.
   ⛔ **Il database non la deriva da sé**, e non è pigrizia: la si potrebbe
   ricavare da `meta.context.commessa_id` risalendo alla sorgente ROOT della
   commessa — cioè **proprio il dato che manca** nel fallimento più tipico. Una
   derivazione che smette di funzionare esattamente nel caso per cui serve non è
   una derivazione: è una trappola. **Lo dichiara chi scrive.**
2. **Il verbo si chiama con una `SELECT` sola** sulla madre. Nessuna
   orchestrazione: cancellazione della bozza e marcatura stanno dentro.
3. **Il motivo del rifiuto non si ricalcola in Python**: la check è la stessa che
   la madre usa per rifiutare, e la lista lo espone in riga.

### 6.1 🟢 I due pezzi che mancavano — consegnati il 2026-09-08

> **Origine**: brief BE → DB del 2026-09-08. Il verbo era consumato end-to-end e
> funzionava; sulla corsia del **pull** non sbloccava niente, e il backend non
> poteva chiudere il §6 da solo. Non per pigrizia: gli mancavano **due** cose a
> database, ed entrambe le richieste erano giuste.
>
> **Il fatto datato che l'ha reso visibile** (lotto LTF-0010003, 2026-09-08, in
> transazione annullata): escluso il documento rotto, `lotto_critical_count`
> restava **1**. L'unica segnalazione viva aveva `gruppo_key = NULL`, cioè *«è
> del giro»* — e per la D-6 una segnalazione del giro **deve** fermare il giro.
> ⭐ Il difetto non era la regola: era che **nessuno dichiarava il
> proprietario**, perché non aveva dove.

**Pezzo 1 — il canale** (`20260908-20`). `vendite.fn_log_pipeline_fase` accetta
`p_gruppo_key`, **ottavo parametro, in coda, con `DEFAULT NULL`**, e lo scrive
nella colonna omonima.

* È l'**unico** canale con cui il backend scrive `fatturazione_lotti_log`
  (`PipelineErrorLogger.log_error` → `VenditePipelineRepository.log_pipeline_fase`):
  senza il parametro, la colonna nata col `20260908-02` non poteva riempirsi.
* ⚠️ *In coda e con default* non è cortesia: le **quattro** funzioni DB chiamanti
  e la chiamata **posizionale a sei argomenti** del backend continuano identiche.
  E il `DEFAULT NULL` **dice il vero** — `NULL` è già il valore che significa «è
  del giro».
* ⚠️ **DROP + CREATE**: un parametro nuovo crea un *overload*, e con la vecchia
  firma viva ogni chiamata a sei o sette argomenti sarebbe ambigua.
* ⭐ **In una colonna e non in `meta`**, all'opposto di `error_code`: la
  `gruppo_key` è un **asse di join** — la leggono il conteggio del §5.3 e il
  presidio del §5.6. Un dato su cui si fa `EXISTS` non vive in un jsonb.
* ⛔ **Nessuna verifica che il documento esista**, per la stessa ragione per cui
  non se ne fa una sul codice errore: un log non deve poter fallire dentro il
  ramo `EXCEPTION` di qualcun altro. Il presidio è il §5.6, che guarda e non
  blocca.
* ⚠️ Una `gruppo_key` **vuota o di soli spazi** diventa `NULL` — la colonna ha
  due stati, e un terzo passerebbe per «nomina un documento» lasciando una riga
  che blocca per sempre e che nessuno può togliere. ⛔ Ma **si dichiara** con un
  `WARNING`: qui la conseguenza non è cosmetica come per il codice errore.

**Pezzo 2 — la conoscenza** (`20260908-18` + `20260908-19`).
`script.fn_gruppi_di_commessa_nel_lotto(p_lotto_id, p_commessa_id)` torna
l'array **ordinato** delle `gruppo_key` che quella commessa alimenta **dentro
quel lotto**; `[]` se nessuna. E `vendite.fn_segna_esito_gruppo_lotto`, dove la
conversione era sepolta, adesso la **chiama** (§12.5.2: *la madre non riscrive il
predicato, lo chiama*).

* ⭐ **Il backend aveva ragione a non riscriverla in Python.** Ciò che
  copierebbe non è la costruzione della chiave — quella è già una funzione — ma
  **da quale tabella si legge**: su `attivita_fatturabili` invece che su
  `commesse_attivita` la chiave esce come `COMMESSA:<hash>` e non aggancia
  niente. Misurato scrivendo `script.vw_lotto_documento_righe`: **zero
  corrispondenze su quattro**, e nessun errore.
* ⚠️ **È 1:N, e cambia la forma della consegna**: un fallimento di pull produce
  **una segnalazione per documento**. ⛔ Sceglierne una sola lascerebbe le altre
  a bloccare il lotto per sempre e non togliibili.
* ⭐ **Il perimetro è parte della domanda**, non un filtro in più: un documento
  fuori dal perimetro il lotto non lo stava lavorando, e appendergli una
  segnalazione la renderebbe una riga del presidio §5.6.
* ⚠️ **`[]` è una risposta e va letta**: «questo fallimento non ha un
  proprietario in questo lotto» ⇒ si scrive **una** riga a `gruppo_key` `NULL`.
  ⛔ Non zero righe.
* ⚠️ **Fail-loud sui parametri**, e il perché è la parte non ovvia: la funzione
  estratta **solleva** su un id `<= 0`, perché il backend la chiama diretta e lì
  è un chiamante rotto; la madre invece **non deve sollevare mai**. Le due
  promesse convivono solo perché il guard sulla commessa sta **prima** della
  chiamata. ⭐ E il messaggio ci guadagna: prima un id negativo usciva come
  «nessun documento trovato», cioè la diagnosi sbagliata.

**Che cosa fa il backend adesso** — e sono tre righe, non un cantiere:

1. `PipelineErrorLogger.log_error` prende `gruppo_key` e lo passa alla funzione;
2. `_PullCommesseRunLogger.item_failed` chiede i gruppi della commessa nel lotto
   e scrive **una riga per gruppo**; su `[]`, **una** riga senza `gruppo_key`;
3. niente altro: il conteggio del §5.3 fa il resto da sé.

#### 🔴 Una correzione fatta in corsa, e il meccanismo va scritto

La prima stesura dei tre changeSet aveva le firme a **tipi nudi**, ed è stato
Tid a chiederne conto. Due cause distinte, e la seconda non era ancora
registrata da nessuna parte:

* nel `-19` il corpo viene da `pg_get_functiondef` — la regola di casa — e quel
  corpo **ha già i `%TYPE` sciolti**, perché PostgreSQL li risolve al `CREATE`.
  Copiandolo si eredita il debito **in una forma che sembra corretta perché
  combacia col database**. ⛔ Peggio: `p_lotto_id` era ancorato in `20260906-11`
  e `20260907-13`, quindi non era un'omissione ma una **regressione**;
* nel `-18` — ed è il pezzo nuovo — ho imitato la **funzione sorella**
  `script.fn_gruppi_trascinati_da_uscita`, scritta il giorno prima nello stesso
  cantiere e anche lei a tipi nudi. *Imitare il vicino sembra coerenza ed è
  propagazione del debito: la convenzione si legge dalle linee guida, non dal
  file accanto.*

⭐ **E c'era una terza sede che nessuno guardava**: `DROP FUNCTION` e
`COMMENT ON FUNCTION`, che erano a tipi **risolti**, cioè dedotti. È il difetto
che il 2026-08-31 ha fatto morire un migrate con *«la funzione non esiste»* —
un messaggio che manda a cercare la funzione, non il tipo. Verificato sul
database che PostgreSQL accetti `%TYPE` anche lì: così l'identificatore non può
divergere dai parametri, perché è la stessa espressione. ⚠️ Il caso che si
sbaglia a mano è `p_status`, ancorato a una colonna `character(1)`: nella lista
di un `DROP` il typmod si perde, e scriverlo giusto richiede di saperlo.

⭐ **La prova che toglie il dubbio dell'overload, e costa due query**: prima, in
sola lettura, `atttypid::regtype` sulle colonne da ancorare (il regtype ignora
il typmod); dopo, in transazione annullata, **una sola funzione per nome** e
`pg_get_function_identity_arguments` **byte-identico** al vivo. Fatto:
`fn_segna_esito_gruppo_lotto` esce identica alla firma di partenza, e
`fn_log_pipeline_fase` con i sette parametri storici intatti più `p_gruppo_key`
in coda. ⚠️ Con sei parametri e quattro `DEFAULT`, un overload avrebbe reso
**ambigua ogni chiamata del backend**.

⭐ **E un presidio nasce gratis.** `_marca_esito_gruppi` logga già un avviso
quando `fn_segna_esito_gruppo_lotto` non marca nessun gruppo per una commessa: è
lo **stesso fatto** che `vendite.vw_segnalazioni_con_documento_ignoto` mostra
dall'altro lato. Vanno letti insieme il giorno dell'accensione.

---

## 7. Che cosa si vede

| Superficie | Che cosa cambia |
| --- | --- |
| **Banner del lotto** | Oggi dice *«N segnalazioni bloccanti»*. Diventa *«Il giro è fermo per N documenti su M»* col gesto accanto: la differenza fra dire che c'è un allarme e dire che cosa fare |
| **Scheda Critiche** | Colonna **«Documento»** (finalmente possibile) e azione di riga **«Togli dal giro»**. Sulle critiche del giro l'azione è **spenta col motivo**, mai nascosta |
| **Scheda «Presi in carico»** | La colonna esito c'è già; si aggiunge «Uscito dal giro» con motivo e autore. ⭐ **Stessa azione, seconda superficie, un verbo solo** |
| **Gesto di massa** | Su più documenti si applica alla selezione con **esito parziale** — il pattern già in casa (`run_fan_out` + `useSelezioneLista`), non un secondo meccanismo |
| **Competenza** | Nessun cambiamento: il documento uscito ricompare con la sua anomalia, come già fa |

⛔ **Permesso ⇒ nascondi, stato ⇒ disabilita col motivo** (§12 delle linee
guida): il permesso di escludere non è risolvibile dal kebab, lo stato del lotto
sì. E il motivo viaggia in **una colonna che nomina il verbo**
(`uscita_blocco_reason` / `_reason_key`) — ⛔ mai riusando quella di un altro
verbo (§12.5.4).

⚠️ Ogni `reason_key` nuova va **chiesta al frontend nello stesso giro**:
`check_i18n_keys.py` fallisce su una chiave emessa dal database e assente dai
`locales`, e a video sarebbe un pulsante grigio col tooltip vuoto.

---

## 7-bis. 🔴 Un test gemello si è rotto, e la riparazione è una decisione

Il pgTAP di ieri asseriva che `fatturazione_lotti_esiti.stato_esecuzione` e
`fatturazione_lotti_fatture.stato_esecuzione` ammettessero **gli stessi** valori —
*«è la stessa domanda posta a un documento invece che a una fattura, e due
colonne così non possono parlare due lingue»*. Aggiungendo `ESCLUSO` al solo lato
esito, quel test è diventato rosso. **Giustamente**: la baseline ha fatto il suo
mestiere.

⭐ **E la divergenza è legittima**: `ESCLUSO` dice *«l'operatore ha tolto questo
DOCUMENTO dal giro»*, e una **fattura** quello stato non lo può avere — quando un
documento esce, la sua bozza viene **cancellata** e la riga di ponte sparisce. Non
esiste una fattura «esclusa ma ancora lì».

⛔ **Il test non è stato indebolito a un confronto vago.** L'invariante è passata
da *«identici»* a *«identici a meno del surplus DICHIARATO»*: si sottrae
`ESCLUSO` e si confronta il resto. Così resta rosso in tutti e tre i casi che
contano — il lato fattura acquista uno stato, il lato esito ne acquista uno non
dichiarato, oppure `ESCLUSO` sparisce.
⭐ È la forma già in casa: *l'invariante non è «vuoto», è «nessun
NON_DICHIARATO»*.

⚠️ **La lezione operativa**: prima di montare un trigger o allargare un `CHECK`,
si greppa il pgTAP. Non l'ho fatto, e me l'ha detto la baseline invece del
ragionamento — che è il modo più caro di scoprirlo.

---

## 7-ter. 🔵 Che cosa resta al DB perché il §7 sia intero

> ⚠️ **Trasportate qui il 2026-09-08**, quando il brief figlio
> [brief-be-db-gruppo-key-sulle-segnalazioni](../work-done/brief-be-db-gruppo-key-sulle-segnalazioni.md)
> è stato chiuso: le sue richieste erano soddisfatte, queste no. ⛔ Un cantiere
> che archivia il documento in cui vivono le domande aperte le perde — e nessuno
> le ritrova, perché nessuno rilegge un brief marcato «fatto». Il ragionamento
> per esteso resta lì (§6.1, §6.2, §6.4); qui c'è la domanda.

Delle quattro superfici del §7 ne sono vive **tre**: la scheda Critiche con la
colonna del documento e l'azione di riga, la scheda «Presi in carico» con
l'uscita e il suo timbro, e il gesto di massa con l'esito parziale. Restano
**tre cose piccole**, tutte a database.

### 7-ter.1 🔵 Le due righe di `ui.lista_colonna` per la lista 47

La scheda Critiche fornisce lo slot `#actions` e la colonna del documento, ma il
catalogo di `vendite.lotto_segnalazioni` non ha né la colonna `gruppo_fatturabile`
né quella con `tipo_colonna = 'azione'`.

⛔ **E il building block non fallisce**: senza la riga a catalogo la colonna
semplicemente **non viene resa**, e le azioni di riga spariscono in silenzio.
🔴 Il cancello `test_chi_fornisce_lo_slot_actions_ha_la_colonna_a_catalogo` è
**rosso** e lo resta: legge il **seed in git**, non il database di test — dove le
due righe ci sono già.

🔵 **Chiediamo**: le due righe nel CSV del seed.

### 7-ter.2 🔵 Il riferimento leggibile accanto alla `gruppo_key`

Sulla scheda Critiche il documento si legge come **chiave grezza**
(`ORDINE_VENDITA:01a06ce4-…`), perché `fn_list_lotto_segnalazioni` espone
`gruppo_key` e non il riferimento.

⛔ Non si risolve lato backend: l'identità del gruppo vive in
`vendite.vw_dash_competenza_gruppi` **agganciata al mese del lotto**, e
ricostruirla in un repository sarebbe la seconda sede della stessa regola.

🔵 **Chiediamo**: `riferimento` (e volendo `tipo_gruppo`) nell'output della
funzione. ⚠️ `NULL` resta legittimo — il lavoro può essere uscito dal mese — e il
frontend ripiega sulla chiave, che è il comportamento già in casa.
⚠️ Con quello vale la pena aggiungere **entrambi** alla whitelist di
`p_order_by`: raggruppare le critiche per documento è come si legge quella
scheda, e oggi la colonna è seedata non ordinabile proprio perché la whitelist
non li conosce.

### 7-ter.3 🔵 Il numero del banner

Il §7 vuole *«Il giro è fermo per **N documenti su M**»* al posto di «N
segnalazioni bloccanti». **N non esiste**:
`vendite.fn_get_lotto_segnalazioni_summary` conta le **segnalazioni**, non i
**documenti distinti** che ne hanno almeno una viva.

⛔ Non si deriva a video: la scheda è paginata, e contarli lato frontend darebbe
un numero che cambia scorrendo.

🔵 **Chiediamo**: un aggregato in più sul riepilogo — i documenti distinti con
almeno una critica viva. ⚠️ Con la `gruppo_key` ora valorizzata è un
`count(DISTINCT gruppo_key)` sullo stesso perimetro che il §5.3 già percorre; M
lo ha già il frontend (il totale della scheda Documenti).

⇒ Finché manca, il banner resta quello di oggi: ⛔ **non si mette a video un
numero che non si sa contare**.


---

## 8. pgTAP

* la critica di un documento **escluso** non blocca; quella del **giro** sì;
* con due documenti rotti il lotto riparte **solo** quando esce il secondo — è
  l'invariante di Tid, e va provato **costruendo** il caso, non aspettando che i
  dati lo producano;
* l'uscita **senza motivo** è rifiutata;
* `ESCLUSO` è terminale: non si torna a `ERRORE` né a `COMPLETED` (D-3);
* la bozza esistente viene **cancellata** e le attività tornano `NON_EMESSA`
  (D-2), e la riga di ponte sparisce dal conteggio;
* ⭐ **la madre non contiene più il predicato**: il presidio da scrivere non è
  «gli esiti coincidono» ma «il predicato sta in un posto solo» (§12.5.2);
* `throws_ok` **sempre con lo SQLSTATE**.

### 8.1 ✅ Il secondo file, per i due pezzi del §6.1

`db/pgtap/vendite/test-gruppo-key-segnalazioni-v1.sql` — **15 test**, e tre cose
vale la pena dire di come sono fatti:

* ⭐ **I test 2 e 3 sono il presidio del §12.5.2**, e non è un modo di dire: non
  confrontano gli esiti (proverebbe che *oggi* coincidono), leggono il `prosrc`
  della madre e chiedono che **non nomini più** `commesse_attivita` e che
  **chiami** la funzione estratta. ⚠️ Tolgono i **commenti** prima di cercare:
  il corpo della madre spiega la trappola citandola, e un presidio che legge il
  `prosrc` grezzo accusa chi documenta il difetto invece di chi lo commette.
  ⭐ **Provati per mutazione**: rieseguendo il file senza il `20260908-19`
  diventano rossi loro due e nient'altro.
* ⚠️ **I test 14 e 15 sono data-dependent e lo dichiarano con uno `skip()`
  motivato**: il verso positivo (una commessa con **due** documenti, cioè il caso
  1:N) chiederebbe di fabbricare articolo, istanza di utility, unità di misura e
  commessa — una fixture più grande della cosa da provare. ⛔ Su un database
  ricostruito da zero saltano, e la copertura di quel verso vale **zero**, non
  «parziale»: è un debito dichiarato, non un verde. Il verso costruibile — una
  commessa che non alimenta niente — è il test 4.
* ⭐ **Il test 13 accende il presidio del §5.6 per la prima volta.** Fino a
  ieri `vw_segnalazioni_con_documento_ignoto` era vuota *per assenza di dato*;
  adesso è raggiungibile, e il test prova che accusa il caso giusto — un
  proprietario dichiarato **male**, non uno assente.

⚠️ E in `test-lotti-gruppi-esito.sql` il test 6 è stato corretto: passava
`p_commessa_id => -1`, che dal `20260908-19` prende la strada del **guard di
parametro** invece della risoluzione — sarebbe rimasto verde anche a risoluzione
rotta. Adesso passa un id positivo e inesistente, che percorre la strada vera.

---

## 9. Come si vede che è chiuso

Si costruisce un giro con due documenti rotti su quattro, si escludono uno alla
volta, e si guarda che il lotto riparta **al secondo** e non prima. Poi si
rilancia lo step e si verifica che la segnalazione riscritta dal task **non**
rimetta in errore il lotto per un documento che non ha più.

⛔ Non basta che i test siano verdi: questo cantiere nasce da un comportamento
osservato a video, e lì va riguardato.

⚠️ **E fino al 2026-09-08 quel giro si fermava al primo passo**, per una ragione
che non era del disegno: la segnalazione non aveva padrone, quindi non c'era
niente da toglierle. ⇒ La prova va **rifatta dopo** che il backend ha scritto le
tre righe del §6.1 — prima, misurerebbe l'assenza del contratto e non il verbo.
🔵 È l'ultimo passo aperto di questo cantiere.

---

## 9-bis. Il collaudo fatto — sul database vero, in transazione annullata

> 2026-09-08. Costruito il caso, non aspettato che i dati lo producessero.

**Il trigger dell'uscita (7 prove):** `ERRORE → ESCLUSO` col motivo scrive il
timbro dalla GUC e **conserva l'errore** sulla riga; il rientro è rifiutato
(`P0001`); riassegnare lo stesso valore **non** è rifiutato (direzione, non
menzione); l'uscita senza motivo e col motivo di soli spazi è respinta dal
`CHECK`; una riga non esclusa non può portare un timbro; il timbro è immutabile.

**La check:** il documento in `ERRORE` → **zero motivi**; i tre `COMPLETED` →
`DOCUMENTO_NON_IN_ERRORE`; un documento inesistente → `SENZA_ESITO`; un
documento già uscito → **solo** `GIA_USCITO` e non anche il generico — la
precedenza dichiarata regge.

**La madre, sul lotto vero:** l'uscita del documento rotto scrive `ESCLUSO` +
motivo + timbro, **lascia il perimetro a quattro righe** (D-1), e riporta
`fatture_cancellate: 0` — quel documento una bozza non l'aveva mai avuta,
perché era caduto al pull. Rifarlo → `E_LOTTO_DOC_GIA_USCITO`; su un documento
sano → `E_LOTTO_DOC_NON_IN_ERRORE`; senza motivo → `E_PARAMETRO_INVALIDO`.

**Il trascinamento (D-2b), costruito apposta:** portato in errore uno dei due
documenti che condividono una bozza ed escluso, la madre risponde
`fatture_cancellate: 1`, `attivita_riemesse: 2`, `gruppi_riaperti: [l'altro]` —
e il gemello torna a **`PENDING`**.

⭐ **La catena completa**, che è la prova che conta:

| passo | `lotto_critical_count` |
| --- | --- |
| segnalazione con `gruppo_key` **NULL** | **1** — «è del giro», blocca |
| attribuita al documento rotto | **1** — attribuire non sblocca |
| documento **escluso** | **0** — il lotto riparte |

⭐ E la segnalazione resta a video, `disabilitato = false`: **non è stata
ritirata**, è il suo documento a non essere più in gioco. È l'intero punto del
disegno, misurato.

---

## 10. Fatti datati

> ⚠️ Misure del **2026-09-08**, su dati di **prova** costruiti apposta da Tid per
> osservare il comportamento del programma. Stanno qui, in fondo, perché **non
> sono il motivo di niente**: il progetto dei §1-§7 regge identico senza di loro.
> Servono a una cosa sola — dire che il caso è raggiungibile.

* Un lotto con quattro documenti presi in carico, tre `COMPLETED` e uno `ERRORE`,
  si è fermato in `DRAFT` con due bozze non emesse.
* Il riepilogo diceva `lotto_critical_count = 1`, `fatture_critical_count = 0`,
  `fatture_stato_esecuzione_errore_count = 0`: **una sola** segnalazione, sul
  canale del **lotto**, che nominava la commessa solo dentro il testo e dentro
  `meta.context.commessa_id`. ⇒ Il documento caduto al pull passa dal ramo
  `lotto_agg`, che è l'unico dei tre a non avere un proprietario (§5.3).
* `script.fn_available_actions_lotto` su quel lotto offriva **una sola azione**:
  `annulla`.

⭐ Il terzo punto è quello che vale: non è un'opinione sull'ergonomia, è il
database che dichiara di non avere altro da proporre.

---

## 11. Che cosa NON si fa, e perché

* ⛔ **Un interruttore di lotto** («prosegui comunque»): su un giro da 200
  documenti è una firma in bianco, e non lascia scritto chi è rimasto indietro.
* ⛔ **Far sparire la riga dal perimetro**: «eliminare» suggerisce che il lotto
  non l'abbia mai visto. L'ha preso in carico, ci ha lavorato ed è fallito — e
  fra un mese qualcuno chiederà perché quel documento non è in quella fattura.
* ⛔ **Riusare `disabilitato`**: §2, terza riga.
* ⛔ **Escludere un documento sano**: D-4.
