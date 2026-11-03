## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_contabili`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — gli importi della distinta, uno per riga, col riferimento della banca
> * [pagamenti.vendite_contabili_stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati) — il catalogo degli stati della testata
> * [pagamenti.transizioni_stati_contabile](/dbzero/pagamenti/tabelle/transizioni_stati_contabile) — la matrice dei passaggi di stato
> * [pagamenti.centri_riscossione](/dbzero/pagamenti/tabelle/centri_riscossione) — il centro a cui la distinta appartiene
> * [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso) — il canale, facoltativo, da cui il denaro arriva
> * [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti) — dove finiscono le righe registrate
> * [pagamenti.sistemazioni](/dbzero/pagamenti/tabelle/sistemazioni) — l'atto che tiene l'id della distinta che ha generato
> * [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione) — il registro su cui la distinta è numerata
> * [vendite.famiglie_documento](/dbzero/vendite/tabelle/famiglie_documento) — la famiglia `DISTINTA_INCASSO`
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_get_or_create_vendite_contabile](/dbzero/pagamenti/funzioni/fn_get_or_create_vendite_contabile) — la madre che trova o crea la distinta
> * [pagamenti.fn_posta_contabile](/dbzero/pagamenti/funzioni/fn_posta_contabile) — la registrazione della distinta
> * [pagamenti.fn_get_emittente_distinta](/dbzero/pagamenti/funzioni/fn_get_emittente_distinta) — la sede unica che dice di chi è la distinta
> * [pagamenti.trgfn_vendite_contabili_emittente](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_emittente) — applica la sede unica a ogni scrittura
> * [pagamenti.trgfn_vendite_contabili_gen_codice](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_gen_codice) — il numeratore sul registro
> * [pagamenti.trgfn_vendite_contabili_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_transizione) — i passaggi di stato ammessi
> * [pagamenti.trgfn_vendite_contabili_guard_validazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_validazione) — le condizioni che la matrice non porta
> * [pagamenti.trgfn_vendite_contabili_guard_chiusura](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_chiusura) — niente chiusura con righe pronte
> * [pagamenti.trgfn_vendite_contabili_guard_ente_centro](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_ente_centro) — la coerenza fra canale e centro
> * [pagamenti.trgfn_vendite_contabili_lotti_guard_sistemazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_lotti_guard_sistemazione) — una distinta nata da un atto non si aggancia a un lotto
> * [pagamenti.trgfn_sistemazioni_guard_dati](/dbzero/pagamenti/funzioni/trgfn_sistemazioni_guard_dati) — la compensazione sta sul centro dedicato
> * [script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope) — il guard di scrittura sul perimetro dell'emittente
> * [script.fn_check_registro_disattivabile](/dbzero/script/funzioni/fn_check_registro_disattivabile) — anticipa il blocco sul registro col motivo `HA_DISTINTE`
>
> Guide:
>
> * [Numerazione documenti e codici](/guide/numerazione-documenti-e-codici) — il meccanismo dei registri che numera la distinta
> * [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls) — il meccanismo comune del perimetro

---

### 🎯 Scopo Principale

È la testata della distinta contabile: il documento che raccoglie gli importi arrivati
insieme su un centro di riscossione, a una data contabile, eventualmente da un canale
(`ente_incasso_id`), e li prepara per la registrazione.

La testata ha un numero di registro, un emittente a cui appartiene, un'origine e uno stato.
Gli importi stanno nelle righe; i movimenti nascono quando la distinta si registra.

---

### 🎯 È una distinta, non un movimento bancario

Sulla testata non c'è **nessun importo** e **nessun riferimento bancario** (CRO, TRN,
numero operazione): il riferimento della banca sta **sulla riga**. La testata non modella
*un* bonifico: modella il **documento che raccoglie N importi arrivati insieme**.

⭐ È ciò che rende sensata la registrazione «per testata»: le righe dubbie restano
`SOSPESA` e non si registrano, quindi *«registra la distinta»* significa **registra tutto
il pronto, lascia lì il resto**. Con una testata per bonifico non ci sarebbe nessun «resto»
da lasciare.

`data_conferma` e `user_conferma` dicono **quando e da chi la distinta è stata registrata**:
le scrive [fn_posta_contabile](/dbzero/pagamenti/funzioni/fn_posta_contabile), e tengono la
prima volta che è successo.

---

### ⭐ `origine` è il cardine da cui pendono le altre regole

| Valore | Che cos'è | Chi la crea |
| --- | --- | --- |
| `MANUALE` | il **lotto di lavoro di un operatore** | una persona, digitando |
| `AUTOMATICA` | il **file** arrivato dal canale | l'import *(non ancora costruito)* |
| `GENERATA` | la produce **il sistema** | il giro dei fondi fattura, le sistemazioni |

Il terzo valore esiste perché il giro dei fondi **non è né l'uno né l'altro**: non la digita
una persona e non arriva da un file. Con due soli valori le distinte del sistema avrebbero
portato una parola falsa.

Dall'origine pendono tre regole:

* **`importo_dichiarato`** è obbligatorio su `AUTOMATICA`, facoltativo su `MANUALE`,
  **vietato** su `GENERATA` (due vincoli `CHECK`);
* il **raggruppamento per operatore** vale solo su `MANUALE`;
* la **riapertura** `VALIDATA → BOZZA` e l'**annullo** valgono solo su `MANUALE`
  ([trgfn_vendite_contabili_guard_validazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_validazione)).

---

### `importo_dichiarato` non è il totale delle righe

È **ciò che la sorgente dichiara di aver mandato**. Sull'automatica è l'**autocontrollo
dell'import**: se il file è stato letto male la somma non torna e non nasce niente. Sul
manuale è il classico controllo da inserimento dati, e **scatta al passaggio a
`VALIDATA`**, cioè al gesto «ho finito», mentre l'operatore è ancora nel flusso.

⚠️ La quadratura conta **tutte** le righe attive, `SCARTATA` comprese: quel denaro è
arrivato comunque. Dice *«abbiamo letto tutto ciò che c'era»*, non *«tutto è nostro»*.

---

### ⭐ La distinta manuale è per operatore, e il lock non serve

Il riuso della testata, sul ramo manuale, comprende **chi sta lavorando**. Il
raggruppamento «giornata + canale» non ha un referente nel mondo — nessun documento reale
corrisponde a *«tutti gli incassi banca di lunedì digitati a mano»* — mentre il lotto di
lavoro di una persona ce l'ha.

Con questo raggruppamento due operatori non condividono mai una distinta manuale,
quindi **la contesa non esiste**: niente colonne di blocco, scadenze, sblocco d'emergenza. *Il
presidio più economico è quello che il modello rende inutile.* La chiave di riuso la
applica [fn_get_or_create_vendite_contabile](/dbzero/pagamenti/funzioni/fn_get_or_create_vendite_contabile).

---

### `stato_id` è obbligatorio, ed è un cancello

Lo stato divide il **brogliaccio** dal **registro**: prima della registrazione la distinta
si annulla, dopo no. Una testata *senza* stato non sarebbe né l'uno né l'altro e
passerebbe i filtri di entrambi: per questo la colonna è obbligatoria e nasce in `BOZZA`.

Il percorso degli stati lo dice la
[matrice](/dbzero/pagamenti/tabelle/transizioni_stati_contabile); le condizioni che la
matrice non sa esprimere stanno nei guard della testata (sezione in fondo).

---

### 🔢 Il codice viene dal registro dell'emittente

Il `codice` è un **numero di registro**, `DIS-<SIGLA>-<ANNO>-<7 cifre>`, assegnato alla
creazione da
[trgfn_vendite_contabili_gen_codice](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_gen_codice)
con il meccanismo della [guida alla numerazione](/guide/numerazione-documenti-e-codici):
famiglia `DISTINTA_INCASSO`, **un registro per emittente**, prefisso `DIS-`, reset annuale,
anno nel numero. `registro_id` e `anno` dicono su quale sezionale e in quale anno il codice
è stato numerato, e si scrivono insieme al codice.

| Cosa | Com'è |
| --- | --- |
| sigla | `emittenti_fiscali.codice`, passata come corpo del numero, come per la commessa |
| identità | la **stringa nuda**, univoca: con un registro per emittente è la sigla a distinguere due `…-2026-0000001` |
| momento | alla creazione: il codice è la maniglia con cui si lavora la distinta da subito; i buchi da una bozza annullata sono accettati, come per l'ordine |
| anno | da `data_contabile`: una distinta datata 31/12 e inserita il 2/1 è dell'anno vecchio. La data non si presidia: la distinta di ieri inserita oggi è un caso normale |
| codice fornito | rispettato, per le fixture dei test. ⛔ Non è una porta per le madri: nessuna funzione viva passa `codice` |
| pregresso | le distinte numerate prima (`VC_…`, `SIS_…`) restano così, con `registro_id` e `anno` vuoti: forma diversa, non collidono |

⚠️ **Una distinta numerata blocca la disattivazione del suo registro.** Il guard lo monta da
sola l'automazione sulla FK verso il registro; non avendo la distinta una colonna `attivo`,
blocca sull'**esistenza**: una distinta annullata pesa come una registrata, e una distinta
non si cancella. [script.fn_check_registro_disattivabile](/dbzero/script/funzioni/fn_check_registro_disattivabile)
lo anticipa col motivo `HA_DISTINTE`, così il cestino del registro si spegne prima del
click. Il perché sta nella scheda del
[registro](/dbzero/vendite/tabelle/registri_fatturazione).

---

### ⭐ La distinta sa di chi è

Un registro appartiene a un emittente, e la distinta deve dichiarare il proprio:
`emittente_soggetto_ruolo_id` è obbligatorio, è l'input del numeratore e la colonna su cui
passa il perimetro. L'emittente si risolve in **una sede sola**,
[pagamenti.fn_get_emittente_distinta](/dbzero/pagamenti/funzioni/fn_get_emittente_distinta),
che il trigger
[trgfn_vendite_contabili_emittente](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_emittente)
applica a ogni scrittura e che la madre chiama per la chiave di riuso:

| Livello | Se… | Allora |
| --- | --- | --- |
| 0 | l'emittente dato non è un emittente fiscale | `E_PAGAMENTI_CHIAMATA_NON_VALIDA` (tecnico) |
| 1 | è dato; se c'è anche il canale, deve essere il suo | altrimenti `E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE` |
| 2 | c'è solo il canale | il suo emittente (canale → conto → soggetto-ruolo → emittente); un canale che non porta a un emittente è `E_CONFIG_MANCANTE` |
| 3 | c'è un operatore in sessione | l'emittente di chi agisce ([script.fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user)) |
| 4 | niente | `E_CONTABILE_EMITTENTE_OBBLIGATORIO`: il super admin sceglie nel form |

⛔ **Nessun «default dell'installazione»**: dichiarare di un emittente il denaro di un altro
è l'attribuzione che la numerazione per emittente esiste per impedire. Chi crea la distinta
porta l'emittente da dove lo sa: la madre lo deriva dal **lotto** se non le viene dato, la
sistemazione lo prende dall'**atto**, la correzione lo **copia** dalla distinta corretta
(stesso registro, progressivo successivo).

⚠️ Su un aggiornamento che mette l'emittente a vuoto il trigger **non** lo ri-risolve dalla
sessione: parla il vincolo `NOT NULL`. Ri-riempirlo sarebbe un cambio di emittente che
nessuno ha chiesto. Un aggiornamento che sposta la distinta sul canale di un altro emittente
è rifiutato (livello 1).

⚠️ **L'ordine dei trigger `BEFORE ROW` regge sul nome**: `a10_emittente` (risolve) precede
`a10_gen_codice` (numera) e `a10_guard_emittente_scope` (giudica). Chi rinomina uno dei tre
sposta la risoluzione dopo chi la usa.

---

### 🔒 Chi la vede: il perimetro è l'emittente della distinta

La policy `rls_vendite_contabili_perimetro_incasso` vale **per tutte le operazioni**, con il
gate `OPERATORE` fail-closed, e il perimetro è la colonna `emittente_soggetto_ruolo_id`:
un operatore vede e scrive le distinte degli emittenti della propria whitelist. Una distinta
interna (fondo fattura, sistemazione) è del suo emittente, come il lotto o l'atto da cui
nasce; le righe seguono la testata.

🔴 **Perché la policy copre tutte le operazioni e non solo la lettura.** La RLS nega ciò che
nessuna policy permette: con la sola lettura la tabella diventerebbe di sola lettura per
l'applicazione. E un `INSERT … RETURNING` passa dalla condizione di lettura: la madre
restituisce l'id della distinta appena creata proprio con un `RETURNING`. ⭐ Ne segue una
regola che vale oltre questo caso: **ciò che l'applicazione scrive e poi rilegge deve essere
visibile a chi l'ha scritto, nello stesso istante.** Un perimetro che si chiude su una riga
appena creata non nasconde: rompe.

⚠️ La RLS è abilitata ma **non forzata**, come nel resto del database. Qui il `FORCE` non è
solo rimandato: il risolutore dell'emittente che regge il predicato gira con i privilegi del
proprietario, e con il `FORCE` rientrerebbe sotto la policy della tabella che sta leggendo.

⭐ **La policy nasconde, il trigger rifiuta.** Il guard di scrittura
[script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope),
in modo `soggetto_ruolo` sulla colonna dell'emittente, impedisce di scrivere una distinta
fuori dal proprio perimetro e lo **spiega**; il controllo della policy da solo direbbe «la
nuova riga viola la regola di sicurezza per riga», che è vero e inservibile.

I processi automatici non saltano il perimetro: ogni giro corre con un utente tecnico per
processo e azienda, dentro il proprio perimetro, e il livello 3 della sede unica risolve
anche per lui.

---

### Le regole che stanno altrove

* **Canale e centro devono essere coerenti**: se c'è un canale, il suo centro è quello della
  distinta ([trgfn_vendite_contabili_guard_ente_centro](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_ente_centro)).
* ⚠️ **La distinta non sa di essere nata da un atto: lo sa l'atto.** La sistemazione tiene
  l'id della distinta che ha generato. Per questo le due regole delle distinte nate da un
  atto stanno dove quel dato esiste: *«non si aggancia a un lotto di fatturazione»* su
  [trgfn_vendite_contabili_lotti_guard_sistemazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_lotti_guard_sistemazione),
  *«una compensazione sta sul centro dedicato»* su
  [trgfn_sistemazioni_guard_dati](/dbzero/pagamenti/funzioni/trgfn_sistemazioni_guard_dati).
* **Una distinta di correzione** punta a quella che corregge (`contabile_corretta_id`): una
  distinta ha al più una correzione, e non corregge se stessa
  ([pagamenti.fn_crea_distinta_correzione](/dbzero/pagamenti/funzioni/fn_crea_distinta_correzione)).

| Guard della testata | Impedisce |
| --- | --- |
| [trgfn_vendite_contabili_emittente](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_emittente) | che una distinta nasca senza sapere di chi è, o con il canale di un altro emittente |
| [trgfn_vendite_contabili_gen_codice](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_gen_codice) | non è un guard: è il numeratore sul registro dell'emittente |
| [trgfn_vendite_contabili_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_transizione) | i passaggi di stato che la matrice non ammette |
| [trgfn_vendite_contabili_guard_validazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_validazione) | di validare con righe non lavorate o un totale che non quadra; di riaprire o annullare una distinta non manuale |
| [trgfn_vendite_contabili_guard_chiusura](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_chiusura) | di chiudere una distinta che ha ancora righe pronte |
| [trgfn_vendite_contabili_guard_ente_centro](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_ente_centro) | le incoerenze fra centro e canale |
| [script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope) | di scrivere una distinta di un emittente fuori dal proprio perimetro |

---

### Codici errore

* `E_PAGAMENTI_CHIAMATA_NON_VALIDA` — l'emittente dato non è un emittente fiscale (tecnico).
* `E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE` — emittente e canale appartengono a emittenti
  diversi, alla nascita o spostando il canale.
* `E_CONFIG_MANCANTE` — il canale non porta a nessun emittente, o l'emittente non ha il
  registro della distinta.
* `E_CONTABILE_EMITTENTE_OBBLIGATORIO` — né emittente, né canale, né operatore in sessione.

I codici dei guard di stato e di coerenza sono nelle schede dei singoli guard.

---

### Test

* `db/pgtap/pagamenti/test-distinta-numerazione-registro-v1.sql` — il numero dal registro
  dell'emittente, l'anno da `data_contabile`, i livelli della sede unica, il presidio che
  nessuna madre passa `codice`, il perimetro sulla colonna dell'emittente.
* `db/pgtap/pagamenti/test-contabili-origine-e-quadratura.sql` — il vocabolario a tre
  valori, il dichiarato per origine, la quadratura con le scartate, le due distinte di due
  operatori, la riapertura solo della manuale.
* `db/pgtap/pagamenti/test-vendite-contabili-stato-obbligatorio.sql` — lo stato
  obbligatorio, che nasce in `BOZZA`.
* `db/pgtap/rls/test-rls-pagamenti-perimetro.sql` — il perimetro degli incassi.
* `db/pgtap/script/test-fn-check-registro-disattivabile-v1.sql` — il motivo `HA_DISTINTE`
  sul registro.
* `db/pgtap/pagamenti/test-fn-crea-distinta-correzione.sql` — la distinta di correzione.

---

### Note di migrazione

* 2026-08-21 — nasce `origine` a tre valori con `importo_dichiarato` e i suoi vincoli; la
  distinta manuale diventa per operatore; `stato_id` diventa obbligatorio con default
  `BOZZA`.
* 2026-08-22 — `data_conferma` e `user_conferma`, che esistevano vuote, le scrive la
  registrazione. Il legame con le sistemazioni si rovescia: la
  colonna che nominava l'atto sparisce, e le regole delle distinte nate da un atto passano
  ai guard dell'atto e del lotto.
* 2026-08-22 — arriva la RLS: perimetro dal **conto di incasso** del canale, con le
  distinte senza canale visibili a tutti, perché la chiave di riuso non nominava
  l'emittente e le distinte interne raccoglievano i fondi di tutti.
* 2026-09-15 — il codice smette di nascere da un
  default di colonna (`VC_…`, e `SIS_…` sulle sistemazioni) e diventa un numero di
  registro; nascono `emittente_soggetto_ruolo_id`, `registro_id` e `anno`. Il perimetro
  passa alla colonna dell'emittente, e il ramo «senza canale = di tutti» sparisce dalla
  testata e dai satelliti; il guard di scrittura passa dal modo `ente_incasso` al modo
  `soggetto_ruolo`.
* 2026-09-18 — la FK verso il registro porta il blocco sulla disattivazione del registro
  (motivo `HA_DISTINTE`).
* 2026-10-18 — la policy legge l'emittente attraverso il risolutore comune, come le altre
  policy del perimetro.
* 2026-10-20 — la famiglia di numerazione si chiama
  `DISTINTA_INCASSO` (era `DISTINTA`).

---

{% include-markdown "signature-core.md" %}
