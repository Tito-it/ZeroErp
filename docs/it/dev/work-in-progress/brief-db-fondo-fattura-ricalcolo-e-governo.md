# Fondo fattura — un numero ricalcolato che muove denaro

> **Cos'è.** Il brief di un problema **strutturale** del meccanismo dei fondi
> fattura, emerso il **2026-08-09** analizzando gli incassi e messo da parte
> perché è un cantiere suo, in `vendite`, non in `pagamenti`.
>
> **Perché esiste questo file.** L'analisi è già stata fatta, in profondità, e
> sarebbe andata persa dentro il brief di un altro cantiere.
>
> ⭐ **Dal 2026-08-15 non è più solo una diagnosi: c'è il piano di sviluppo**, in
> **§8** — passi DB prima, logica BE poi, su richiesta di Tid. Le cinque domande
> di §6 hanno una risposta proposta in §8.1.
>
> ✅ **Stato al 2026-08-15 (notte)**: **Fase A** (rete di sicurezza), **Fase B**
> (registro degli atti) e la **coda della Fase E** (D-15…D-17) sono **applicate e
> verdi** — 16 changeSet, cinque codici errore, baseline `vendite` senza
> regressioni. Anche la **Fase C** (proposta + elenco) è **applicata e verde** —
> cinque changeSet `-19`…`-23`, §8.2-quinquies. Restano **Fase D** (atto manuale,
> e aspetta il processo rimborsi in `pagamenti`), **Fase F** (dichiarativa) e le
> **richieste al BE** di §8.3 — **R-1 è la sola urgente**.
>
> 🔵 **Lato DB il cantiere è quasi chiuso**: senza il processo rimborsi in
> `pagamenti` la Fase D costruirebbe una porta su una stanza che non c'è.
>
> ~~*«Qui non c'è un piano: c'è la diagnosi e ciò che è già stato deciso a
> tampone altrove.»*~~ — vera fino al 2026-08-14, tenuta per storia.
>
> 🔴 **E non è più vero nemmeno che «lo diventa il giorno del primo incasso».**
> §3 dava il fondo negativo per irraggiungibile finché non esistono movimenti:
> **la conclusione è sbagliata**, e il perché sta in **§8.0**. La finestra la
> apre il primo che scrive una riga contabile, che non è per forza il posting.
>
> **Origine**: [brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md)
> §2-bis D1-bis.

---

## 1. La tesi, in una frase

> **Il fondo fattura è un numero che viene ricalcolato, e che muove denaro.**

Le due cose insieme non stanno in piedi. Un numero **derivato** può essere
ricalcolato quante volte si vuole: se sbaglia, al giro dopo si corregge, e nel
frattempo non è successo niente. Un numero che **muove denaro** — che viene
assegnato a una fattura figlia e ne cambia l'importo — è un **atto**, e un atto
non si ricalcola: si compie, e semmai si annulla con un altro atto.

Oggi il fondo è tutte e due le cose insieme. È da lì che discende il resto.

---

## 2. Come funziona oggi — misurato il 2026-08-09

### Il calcolo

`vendite.fn_genera_fondi_fattura_source(...)` calcola, per le fatture con
`minimo IS TRUE` di un dato billing account / tipo doc / emittente / valuta:

```text
importo_target = pagamenti.fn_get_saldo_fattura(f.id).saldo
               − pagamenti.fn_get_saldo_fattura_contabili(f.id).saldo_contabile
```

e poi:

| Ramo | Condizione | Effetto |
| --- | --- | --- |
| `UPDATE` | il fondo esiste già e il valore è cambiato | `importo = target`; `stato = ANNULLATO` **se e solo se** `target = 0`, altrimenti `DISPONIBILE` |
| `INSERT` | il fondo non esiste e `target <> 0` | crea il fondo `DISPONIBILE` |

⚠️ **`<> 0` è l'unica condizione sull'importo.** Non c'è limite inferiore.

### Il resto della catena

| Pezzo | Cosa fa |
| --- | --- |
| `vendite.fatture_fondi_fattura_source` | stati `DISPONIBILE` → `ASSEGNATO` → `ANNULLATO`. ⚠️ **Nessun CHECK sull'importo**: un fondo negativo è strutturalmente ammesso |
| task `genera_fondi_source_lotto` | `attivo = true` nel registry — **codice vivo** |
| task `applica_fondi_lotto` | `attivo = true` — assegna i fondi `DISPONIBILE` a una fattura figlia |
| `fn_sync_contabili_fondo_fattura(fattura_figlia)` | crea **righe contabili** per il fondo applicato; chiamata da `fn_ricalcola_totali_fattura` |
| `fn_reset_fondi_fattura(fattura)` | riporta `ASSEGNATO` → `DISPONIBILE` |
| centro `FONDI_FATTURA` (id 37, `is_fondo_fattura`) | la corsia contabile dedicata |

### ⚠️ Una funzione il cui nome mente — e nessuno la chiama

`vendite.fn_sync_pagamento_fondo_fattura(p_fattura_figlia_id)` restituisce
`TABLE(inserted_movimenti, updated_movimenti, annullati_source)`.

Il nome e le colonne dicono **movimenti**. Il corpo, letto per intero, è un
guscio: delega **tutto** a `fn_sync_contabili_fondo_fattura` e si limita a
rinominare `inserted_righe` → `inserted_movimenti`. **Non crea nessun
movimento**, e ✅ **nessuna funzione del database la chiama**.

🔴 Va segnalata per due ragioni:

1. chi legge la firma crede che il **posting esista** — ed è probabilmente una
   delle ragioni per cui la guida lo descrive come se ci fosse (non c'è: vedi il
   brief incassi §1-bis);
2. è **codice morto con un nome che promette**, cioè il tipo di residuo che al
   prossimo giro qualcuno chiama pensando di aver trovato il pezzo mancante.

~~Da decidere: rinominarla onestamente o ritirarla.~~ → ✅ **Deciso il
2026-08-15: si ritira** (`DROP`). Il difetto non è il nome, è che la funzione
**esiste**: un nome onesto lascerebbe in piedi un oggetto che nessuno chiama.
Motivi e costo — una sezione di pgTAP — in §8.1 F-4; il passo è **D-15**.

---

## 3. 🔴 Il fatto che rende la cosa non rimandabile all'infinito

> **Il meccanismo dei fondi non ha mai visto un pagamento.**

Il fondo si calcola da `fn_get_saldo_fattura`, che è il residuo *dopo i
movimenti*. Ma **nessuna funzione, in tutto il database, scrive
`pagamenti.vendite_movimenti`**: il posting non è implementato.

Ne segue che finora `fn_get_saldo_fattura` ha sempre restituito, per costruzione,
**l'intero `totale_a_pagare`**. Il fondo è stato progettato, scritto e messo in
pipeline in un mondo in cui **quel termine non si muoveva mai**.

**La slice 1 del cantiere incassi cambia questo per sempre**, e da quel momento
il fondo comincia a oscillare a ogni incasso. Non è un difetto che si manifesta:
è un comportamento che **non è mai stato esercitato**.

### Le due serrature, e chi apre quale

| Serratura | Stato al 2026-08-09 | Chi la apre |
| --- | --- | --- |
| `f.minimo IS TRUE` | **0 fatture a minimo** su 12; **0 fondi** generati | ~~una configurazione, in qualunque momento~~ → 🔴 **non è una configurazione: è un calcolo**, vedi §8.0-b |
| ~~saldo negativo (sovra-incasso)~~ | ~~impossibile: nessun movimento esiste~~ | ~~🔴 **la slice 1 del cantiere incassi**~~ → 🔴 **riga sbagliata**, vedi §8.0-a |

Con entrambe aperte, un sovra-incasso genera un fondo di importo **negativo** in
stato **`DISPONIBILE`**, che `applica_fondi_lotto` assegna a una fattura figlia.
Nessun `CHECK` lo ferma.

> 🔴 **Questa tabella è superata su entrambe le righe** (rimisurato il
> 2026-08-15 leggendo i corpi vivi): la seconda serratura non è «nessun
> movimento» ma **l'assenza di scrittori di righe contabili**, e la prima non è
> un flag che qualcuno accende ma il risultato di un confronto fra il totale
> della fattura e le soglie dell'emittente. Le due correzioni stanno in **§8.0**
> e cambiano *quando* il lavoro è urgente, non *cosa* c'è da fare.

---

## 4. Il difetto strutturale, oltre il caso del segno

Il fondo negativo è il sintomo che si vede per primo. Il problema è più a monte, e
si chiude solo separando due cose che oggi sono una sola:

| | Natura | Regola |
| --- | --- | --- |
| **I fatti** | denaro entrato o uscito, con o senza destinazione | si **aggiungono**, non si aggiornano mai |
| **I saldi** | residuo per fattura, per rata, credito del cliente | si **leggono**, non si conservano — quindi non possono divergere |
| **Le decisioni** | rimborsare, portare avanti, compensare | le prende una **persona**, e ognuna diventa un fatto |

Il fondo oggi sta **in mezzo**: è calcolato come un saldo, ma si comporta come una
decisione. Andrebbe portato **fra le decisioni** — un atto deliberato, non un
numero che un batch riscrive ogni notte.

### ⭐ Perché questo elimina il rischio di rincorsa

Il timore — legittimo — è di *«rincorrere gli incassi»*: un automatismo che
aggiorna un numero, un altro che lo rilegge e ne aggiorna un terzo, all'infinito.

Un ciclo del genere richiede che **un automatismo riscriva un numero che un altro
rilegge**. Se l'unica scrittura è l'aggiunta di un fatto e tutto il resto è
derivato, **non c'è niente che possa rincorrersi**: un saldo non insegue sé
stesso. Non «improbabile» — **impossibile per costruzione**.

---

## 5. Cosa è già stato deciso (a tampone) nel cantiere incassi

Non aspetta questo brief: sta in
[brief-incassi…](brief-incassi-riconciliazione-rate-promemoria.md) §2-bis D1-bis
ed è **dentro la slice 1**, ~~perché è la slice che apre la seconda serratura~~.

> 🔴 **La motivazione è sbagliata, la collocazione no** (2026-08-15). La slice 1
> non è la sola ad aprire la seconda serratura — la apre **chiunque scriva righe
> contabili**, e non serve un movimento: §8.0-a. Quindi i tamponi restano dentro
> la slice 1 *se la slice 1 arriva prima*, ma la scadenza non è la sua: è il
> **primo scrittore**, chiunque sia. Sono la **Fase A** del piano (§8.2), e non
> si fanno due volte.

1. **Limite inferiore alla generazione**: si crea un fondo solo per
   `importo_target > 0`. Il verso opposto **non è un fondo**: è denaro in
   eccesso, un fatto di natura diversa.
2. **Nessun automatismo tocca il fondo in base agli incassi.** Un fondo già
   esistente il cui target diventa negativo **resta com'è**; la fattura compare
   in un **elenco da guardare**, insieme alle rate sovra-incassate.

⭐ La seconda regola chiude anche la domanda *«il fondo va portato ad `ANNULLATO`
quando il target diventa negativo?»* — non scegliendo fra le due strade, ma
osservando che chiuderlo in automatico **sarebbe un automatismo che scrive**, e
sono stati esclusi tutti. Se non ci si fida di un automatismo a **creare** un
fondo, tanto meno a **cancellarlo**.

⚠️ **Sono tamponi, non la soluzione.** Impediscono al meccanismo di peggiorare
quando gli incassi arriveranno; non risolvono il fatto che un numero ricalcolato
muova denaro.

⚠️ **E il primo tampone da solo lascia scoperto un fondo**, cosa che il 2026-08-09
non era stata vista: togliendo l'`ANNULLATO` automatico a target zero, un fondo
non più giustificato **resta `DISPONIBILE`** e `applica_fondi_lotto` lo assegna
comunque. Il pezzo che chiude il buco è il **guard all'applicazione** — D-3 di
§8.2 — e va nello stesso lotto di lavoro, non dopo.

---

## 6. Le domande aperte

> ⭐ **Dal 2026-08-15 tutte e cinque hanno una risposta proposta**, con il perché
> e con ciò che la ribalterebbe: **§8.1**. Le domande restano scritte qui perché
> una risposta senza la domanda che l'ha generata non si sa più valutare.

| | Domanda | Risposta proposta (§8.1) |
| --- | --- | --- |
| **F-1** | Il fondo diventa un **atto** (creato da una decisione, con la sua causale) o resta un numero derivato che qualcuno approva prima che muova denaro? | **Atto** — ma l'atto può nascere da una **regola permanente**, purché crei una volta sola e non riscriva mai |
| **F-2** | Che cosa succede a un fondo `ASSEGNATO` se la fattura sorgente riceve poi un incasso che ne cambia la base? Oggi `fn_reset_fondi_fattura` sa riportarlo a `DISPONIBILE`, ma **chi decide** che vada fatto? | **Non si tocca.** Il doppio pagamento diventa un **credito sulla sorgente** e si governa come qualunque eccedenza (F-3) |
| **F-3** | L'eccedenza di un sovra-incasso: rimborso, compensazione (`pagamenti.compensazioni` esiste ed è il candidato naturale) o applicazione a una fattura futura? Sono tre atti diversi con tre tracce diverse | **Tre strade, e due sono di `pagamenti`.** La terza — applicazione a una fattura futura — **è un fondo di segno opposto**, cioè un atto manuale su questa stessa tabella |
| **F-4** | `fn_sync_pagamento_fondo_fattura` — rinominare o ritirare? | **Ritirare** (`DROP`). Il difetto è che **esiste**, non come si chiama |
| **F-5** | Serve un `CHECK` sull'importo di `fatture_fondi_fattura_source`, o basta il limite inferiore nella funzione? (Un CHECK è una garanzia strutturale; un `WHERE` è una garanzia da ricordare) | **Servono tutti e due, e non sono la stessa regola.** Due CHECK, nessuno dei quali è `> 0` secco |

---

## 7. Dove guardare

| Cosa | Dove |
| --- | --- |
| **Che cosa fare** | **§8 — il piano di sviluppo** (DB in §8.2, BE in §8.3) |
| Il calcolo | `vendite.fn_genera_fondi_fattura_source` |
| Dove `minimo` viene **scritto** | `vendite.fn_ricalcola_totali_fattura` (in coda all'`UPDATE` di testata) + soglie su `anagrafiche.emittenti_fiscali_utilities` |
| La tabella e i suoi stati | [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source) + il suo `manual` |
| L'applicazione alla figlia | task `applica_fondi_lotto` → `fn_applica_fondi_fattura`; le righe contabili le scrive `fn_sync_contabili_fondo_fattura`, chiamata da `fn_ricalcola_totali_fattura` |
| Il giro lato BE | `apps/vendite/db/pipeline_repository.py` (`run_genera_fondi_source_lotto_task`, `run_applica_fondi_lotto_task`) |
| Il reset | `vendite.fn_reset_fondi_fattura` — ⚠️ reset **tecnico** della figlia, non una reazione ai pagamenti |
| Il guscio vuoto | `vendite.fn_sync_pagamento_fondo_fattura` — **da ritirare**, D-15 |
| I due saldi che lo alimentano | `pagamenti.fn_get_saldo_fattura`, `fn_get_saldo_fattura_contabili` |
| I test che ci passano sopra | `db/pgtap/vendite/test-fondi-fattura.sql`, `test-fattura-utils-critical-termini.sql` §6 |
| Il modello contabile intorno | [gestione-dei-pagamenti.md](/guide/gestione-dei-pagamenti) |
| Il cantiere accanto | [brief-incassi…](brief-incassi-riconciliazione-rate-promemoria.md) §2-bis D1-bis (i tamponi), §3-bis (il principio dei tre livelli), §7 (le tre slice) |

---

## 8. Il piano di sviluppo

> ⭐ **Scritto il 2026-08-15 su richiesta di Tid**, per passare dalla diagnosi
> all'implementazione. **Prima tutti i passi DB (§8.2), poi la logica BE che ne
> discende (§8.3).**
>
> Il piano assume risolte le cinque domande di §6: le risposte, col perché e con
> ciò che le ribalterebbe, sono in **§8.1**. Due sono decisioni di dominio (F-1 e
> F-3) e vanno confermate da Tid: se cambiano, cambia la Fase B in avanti. ⭐ **La
> Fase A non dipende da nessuna delle cinque** e si può applicare comunque —
> anzi, va applicata prima delle altre in ogni scenario.

---

### 8.0 🔴 Prima del piano: due misure di §3 non reggono

Il piano parte da qui perché queste due righe cambiano **quando** il lavoro è
urgente, e §3 le dava per acquisite.

#### (a) La seconda serratura non è «nessun movimento»

§3 dice che il fondo negativo è irraggiungibile finché non esistono movimenti,
perché `fn_get_saldo_fattura` non può andare sotto zero senza incassi. **La
premessa è vera, la conclusione no**: il fondo non si genera su `saldo`, si
genera sulla **differenza**

```text
importo_target = fn_get_saldo_fattura(...).saldo            ← movimenti
               − fn_get_saldo_fattura_contabili(...).saldo_contabile   ← righe POSTABILI
```

e il **secondo** termine non ha niente a che vedere coi movimenti. Basta che la
somma delle righe contabili `is_postabile` di una fattura superi il suo residuo
perché `importo_target` vada sotto zero, **con zero movimenti nel database**.

Serve che qualcuno scriva una riga contabile più grande del dovuto, e oggi:

| | Stato |
| --- | --- |
| guard di quadratura sulle righe contabili | **non esiste** — è la slice **2** del cantiere incassi, non la 1 |
| vincolo che leghi `vendite_contabili_righe.importo` alla fattura che nomina | **nessuno** |
| scrittori vivi di righe contabili | **uno solo**: `fn_sync_contabili_fondo_fattura`, che scrive l'importo del fondo — un valore che per costruzione non supera il residuo, e che al giro dopo **si scorpora da sé** (`v_saldo_contabile_source`) |

⭐ **Quindi la seconda serratura non è un vincolo: è l'assenza di scrittori.**
Regge finché l'unico che scrive righe contabili è il circuito del fondo stesso, e
si apre col **primo** altro scrittore — l'import del flusso bancario (D6 del
cantiere incassi), una correzione manuale, la slice 1. Non necessariamente il
posting, e non necessariamente in quest'ordine.

🔴 **Conseguenza operativa**: la Fase A **non si appende alla slice 1** come se
fosse la sola porta. Va applicata prima del primo scrittore di righe contabili,
chiunque sia.

ℹ️ Misurato **leggendo** i corpi vivi (doc auto-generata) e la struttura delle
tabelle, non eseguendo SQL sul DB: formula di `fn_genera_fondi_fattura_source`,
assenza di `CHECK` su `fatture_fondi_fattura_source.importo`, assenza di guard di
quadratura su `vendite_contabili_righe`.

#### (b) `minimo` non è una configurazione: è un calcolo, e si richiude su sé stesso

§3 dice che la prima serratura la apre *«una configurazione, in qualunque
momento»*. Non è un flag che qualcuno accende sulla fattura: `minimo` è
**riscritto a ogni ricalcolo** da `fn_ricalcola_totali_fattura`

```text
minimo = (soglia_min IS NOT NULL AND totale_a_pagare >= soglia_min)
     AND (soglia_max IS NULL OR totale_a_pagare <= soglia_max)
```

con le soglie che stanno su `anagrafiche.emittenti_fiscali_utilities`
(`minimo_soglia_min`, `minimo_soglia_max`), per coppia **emittente × utility**.

#### ⭐ Che cosa significano davvero le due soglie (Tid, 2026-08-15)

Non sono «un minimo e un tetto» nel senso ingenuo. Sono i **due capi di una
banda**, e la banda contiene lo zero:

```text
                −500 €              0              +10 €
    ────────────────┼───────────────┼───────────────┼──────────────
     RIMBORSO       │      F O N D O   F A T T U R A     │  PAGAMENTO
     (troppo        │   il documento non si incassa      │  ordinario
      grande per    │   da solo: si riporta sulla        │  del cliente
      riportarlo)   │   fattura successiva               │
```

| Totale della fattura | Che cosa succede |
| --- | --- |
| **> +10 €** | pagamento ordinario del cliente. Niente fondo |
| **fra +10 e 0** | troppo piccola per essere incassata da sola → **fondo a debito**, riportato avanti |
| **fra 0 e −500** | credito troppo piccolo per un rimborso → **fondo a credito**, riportato avanti |
| **< −500 €** | credito importante → **processo rimborsi** (§8.1 F-3) |

🔴 **Ne discende che un fondo NEGATIVO è normale, non un difetto.** L'intero
capo inferiore della banda esiste per riportare avanti dei **crediti**. È la
correzione più importante di tutta questa sezione, e ribalta il tampone scritto
sia qui sia nel cantiere incassi — vedi F-5.

#### 🔴 «Soglia non impostata = meccanismo spento» oggi vale solo a metà

| Configurazione | Cosa dovrebbe fare | Cosa fa oggi |
| --- | --- | --- |
| nessuna delle due | spento | ✅ spento (`soglia_min IS NOT NULL` è falsa) |
| entrambe | attivo sulla banda | ✅ corretto |
| **solo il minimo** | ⛔ errore di configurazione | 🔴 **`soglia_max IS NULL` rende vera la seconda condizione**: *ogni* fattura sopra il minimo diventa «di minimo» |
| **solo il massimo** | ⛔ errore di configurazione | ✅ spento (per l'altro ramo) |

**Con l'esempio reale**: chi imposta `−500` e dimentica `+10` non ottiene un
meccanismo a metà — ottiene **tutto il fatturato trasformato in fondi
riportati**. Una configurazione incompleta oggi non chiude: **spalanca**.

✅ **Deciso (Tid, 2026-08-15): dev'essere un errore di configurazione**, non un
comportamento. Passo **D-0** in §8.2.

ℹ️ Il vincolo esistente `chk_emittenti_fiscali_utilities_soglie` presidia solo
`min <= max`, e ammette esplicitamente il caso a una sola soglia
(`min IS NULL OR max IS NULL OR min <= max`).

#### ⚠️ E `minimo` si richiude su sé stesso

`totale_a_pagare` **contiene** `fn_get_totale_fondi_fattura`, cioè i fondi già
applicati. Una figlia che riceve un fondo viene ricalcolata, il suo totale
cambia, e con esso può cambiare il proprio `minimo`: la figlia può diventare a
sua volta sorgente di un fondo per la nipote. **È il comportamento voluto** —
nelle utenze il riporto si incatena finché non si esce dalla banda — ed è
leggibile: `fatture_fondi_fattura.riferimento_fattura_id` porta già la fattura di
provenienza, quindi la catena si ricostruisce senza aggiungere niente.

#### ⚠️ Nota di lettura: «BASE» è una utility, non l'assenza di utility

`config.utilities` contiene `BASE` (*Servizio Base*, id 5) accanto a GAS,
ENERGIA, IDRICO, FONIA, e `anagrafiche.billing_account.utility_id` è **NOT
NULL**. Quindi ogni fattura ha una utility e le soglie si trovano **sempre**:
non esiste il caso «fattura senza utility» da gestire a parte. ⚠️ Una riga di
`vendite.fatture` con `utility_id` vuoto (la colonna lì è nullable) non è una
fattura BASE: è un dato incompleto, e va trattata come tale.

---

### 8.1 Le cinque domande, risolte

#### F-1 — Il fondo diventa un **atto**. Ma l'atto può nascere da una regola permanente

⭐ **Non è una scelta nuova: discende da §3-bis del cantiere incassi**, il
principio già fissato con Tid il 2026-08-09 — *i fatti si aggiungono, i saldi si
leggono, le decisioni le prende una persona*. Applicato al fondo dà una sola
risposta: il fondo sta fra le **decisioni**, cioè è un fatto che qualcuno compie.

Ma «qualcuno» non deve per forza essere una persona **per ogni riga**. Nelle
utilities i fondi sono migliaia al mese: un'approvazione che si dà in blocco per
inerzia non è una decisione, è un timbro — e sarebbe un peggioramento, perché
metterebbe una firma umana sotto un numero che nessuno ha guardato.

**La forma che si propone:**

| | Regola |
| --- | --- |
| **Ogni riga del registro è un atto** | ha un'**origine** (`AUTOMATICA` \| `MANUALE`), un **motivo** quando è straordinaria, e un **importo congelato al momento dell'atto** |
| **Nessun atto si aggiorna** | l'`UPDATE … SET importo = target` **sparisce**. Il fondo si crea una volta, con l'importo letto in quel momento, e non si ricalcola più |
| **L'automatismo crea solo dentro la banda** | sorgente **DEFINITIVA**, dentro `[soglia_min, soglia_max]`, e ancora capiente **nell'istante dell'atto**. Fuori da lì non fa niente: **presenta** (§8.2 Fase C) |
| **La regola permanente è la delibera** | la decisione è stata presa quando si sono configurate le due soglie; il giro di fatturazione la **esegue**, non la prende |

⭐ **Perché questo chiude la tesi di §1.** Il fondo smetteva di stare in piedi
perché era *ricalcolato* **e** *muoveva denaro*. Qui il ricalcolo resta — ma
diventa una **lettura** (§8.2 D-9), non una scrittura; e il denaro lo muove solo
un atto, che è scritto una volta e mai riscritto. Le due cose non sono più lo
stesso oggetto.

**Cosa la ribalterebbe.** Se Tid decidesse che *ogni* fondo va approvato a mano
prima di muovere denaro, cade solo la riga «la regola permanente è la delibera»:
la Fase B resta identica, e la Fase D (l'atto manuale) diventa l'**unica** strada
invece che quella straordinaria. Il piano non va riscritto, va accorciato.

**Scartata**: lasciare il fondo com'è e mettergli davanti un'approvazione. Non
risolve niente — approvare un numero che al giro dopo il batch riscrive significa
approvare qualcosa che non c'è più.

#### F-2 — Un fondo `ASSEGNATO` non si tocca

Se la sorgente riceve un incasso **dopo** che il fondo è stato applicato, il
cliente ha pagato due volte lo stesso importo: una sulla sorgente e una dentro la
figlia. Il fatto è reale e va **registrato**, non annullato: diventa un **saldo
negativo sulla sorgente**, cioè un credito, e si governa come qualunque eccedenza
(F-3). Nessun automatismo interviene — è la regola pratica di §5.2, e vale anche
qui.

⚠️ **`fn_reset_fondi_fattura` non è la risposta a questa domanda**, e il nome non
lo dice: è il reset **tecnico della figlia** (ritorno del lotto a DRAFT), non una
reazione ai pagamenti. Va scritto nel suo `COMMENT` — **D-16** — perché è
esattamente il tipo di funzione che al prossimo giro qualcuno chiama pensando di
aver trovato il pezzo giusto (lo stesso difetto di `fn_sync_pagamento_fondo_fattura`).

#### F-3 — Tre strade, e la terza è già questa tabella

✅ **Confermato da Tid il 2026-08-15, con il perimetro**: *«il processo rimborsi
sta nei pagamenti, e le uscite sono tre: rimborso, compensazione, riporto a
fondo fattura»*.

| Strada | Dove vive | Stato |
| --- | --- | --- |
| **Rimborso** | contabile con importi negativi | ✅ **niente da costruire**: D3-d del cantiere incassi ha già deciso che la correzione è un importo di segno opposto, e la guida dice già che il movimento rappresenta «l'incasso **o il rimborso**» |
| **Compensazione** | `pagamenti.compensazioni` | ⏸️ oggi è uno **scheletro** (`id`, `data_esecuzione`, `meta` + audit): è un cantiere suo, in `pagamenti`, non qui |
| **Applicazione a una fattura futura** | ⭐ **è un fondo fattura di segno opposto** | 🔵 la apre la **Fase D** di questo piano |

⭐ **E il passaggio è PASSIVO** (Tid, 2026-08-15): niente meccanismo che «mette in
coda» una fattura sotto la soglia minima. Il processo rimborsi, in `pagamenti`,
**se le va a cercare** — è coerente con «i saldi si leggono» e non aggiunge
nessuna scrittura in `vendite`. Il confine è quindi netto:

> **`vendite` espone un solo punto d'ingresso** (l'atto manuale, D-11), e non sa
> nulla di rimborsi e compensazioni. **`pagamenti` decide** e chiama, quando
> l'operatore sceglie la terza uscita.

⭐ **La terza riga è la scoperta che vale il paragrafo.** «Portare avanti un
credito sulla prossima fattura» non è un meccanismo nuovo da inventare: è
**esattamente** ciò che il fondo fattura fa, col segno invertito. E il vocabolario
c'è già — `tipi_fondi_fattura` id 1 si chiama *«Fondo fattura per
addebiti/**accrediti**»*. Il meccanismo è stato costruito per due versi e ne ha
usato uno solo.

🔴 **Ed è la ragione per cui F-5 non può essere `importo > 0` secco**: un CHECK
così chiuderebbe la terza strada nello stesso changeSet in cui si apre la prima.

**Chi sceglie fra le tre**: una persona, dall'elenco (**D-10**). Non è una
gerarchia: sono tre atti diversi con tre tracce diverse, e la scelta dipende dal
cliente, non dal sistema.

#### F-4 — `fn_sync_pagamento_fondo_fattura` si **ritira**

Verificato il 2026-08-15:

| | Misura |
| --- | --- |
| chiamate da funzioni DB | **zero** — `fn_ricalcola_totali_fattura` chiama direttamente `fn_sync_contabili_fondo_fattura` |
| chiamate da Python | **zero** |
| `COMMENT` vivo | già *«Wrapper deprecato: delega a fn_sync_contabili_fondo_fattura»* |
| unico riferimento vivo | `db/pgtap/vendite/test-fattura-utils-critical-termini.sql` §6 — collauda il guard di parametro **di un guscio** |

**Ritirare batte rinominare** perché il difetto non è il nome: è che la funzione
**esiste**. Un nome onesto lascerebbe in piedi una funzione che nessuno chiama,
cioè un secondo oggetto da mantenere e da spiegare. E non siamo in produzione: il
breaking è secco e costa un `DROP` più una sezione di test.

#### F-5 — Un CHECK e un guard. E 🔴 **non è il segno che va controllato**

> 🔴 **Questa risposta è stata riscritta il 2026-08-15, e la prima versione era
> sbagliata in modo istruttivo.** Diceva: *«l'automatismo crea solo fondi
> positivi»*, con un CHECK a renderlo strutturale. **Con la banda a due capi
> (§8.0-b) è falso**: una fattura fra −500 e 0 *deve* diventare di minimo e
> riportare un **credito** sulla successiva. Il `> 0` avrebbe spento metà del
> meccanismo — e la stessa frase sbagliata sta nel tampone del cantiere incassi,
> dove va corretta.

**Il pericolo non era il segno: era la mancata corrispondenza col documento.**
Una fattura da 8 € su cui qualcuno scrive una riga di lavorazione da 40 €
produce un fondo di −32 su un documento che vale +8. Il fondo non «è negativo»:
**non assomiglia alla sua sorgente**. Ed è quello che va vietato.

```text
regola di corrispondenza (fondo AUTOMATICO)
   l'importo non è zero
   ha lo stesso segno del totale della fattura sorgente
   non lo supera in valore assoluto
```

⚠️ **Va scritta così, mai come «compreso fra 0 e il totale»**: con un totale
negativo gli estremi si invertono e il controllo diventa una porta chiusa. È la
trappola già registrata nel cantiere incassi, e qui si presenterebbe **come caso
ordinario**, non di bordo.

**Dove vive che cosa** — e il confine non è una preferenza, è ciò che un CHECK
può vedere:

| | Strumento | Perché |
| --- | --- | --- |
| `importo <> 0` | **CHECK** di tabella | guarda solo la propria riga: un fondo da zero non è un atto, è rumore |
| corrispondenza col totale della sorgente | **guard trigger** (`_a10_`) | deve **leggere `vendite.fatture`**, e un CHECK non può |
| «l'automatismo non lo fa» | **`WHERE` nella funzione** | il caso è **ordinario**: va *non fatto*, non rifiutato con un'eccezione che ferma il giro di un lotto intero |

🔴 **E qui `origine` torna a servire, per una ragione diversa da quella che
avevo dato.** Non per vietare i fondi negativi all'automatismo, ma per dire
**quale regola si applica**: la corrispondenza vale sulla strada
**automatica**; sulla strada **manuale** no, ed è dimostrabile con il caso
principale di F-3 — l'eccedenza di un sovra-incasso è un fondo **a credito su
una fattura dal totale positivo**, cioè segno opposto per costruzione. Un guard
unico rifiuterebbe proprio l'atto per cui la strada manuale esiste.

Il manuale non resta però senza presidio: è **motivato, gated da un'azione di
processo e originato dal processo rimborsi**, che l'eccedenza la conosce. È la
differenza fra un atto **vincolato** e un atto **governato** — ed è il punto di
F-1.

⚠️ **Un CHECK in più, che §6 non chiedeva e serve comunque**: `stato` è oggi un
`character varying` **senza CHECK e senza FK**. Il vocabolario
`DISPONIBILE`/`ASSEGNATO`/`ANNULLATO` vive solo nelle stringhe letterali di
quattro funzioni.

---

### 8.2 I passi DB

> **Convenzioni** (AGENTS.md + linee-guida-sql, non ripetute passo per passo):
> un changeSet per file, `YYYYMMDD-NN-<tipo>-<descrizione>-mctit.yaml`,
> `logicalFilePath` sempre, `runOnChange: false` in `00_schema`/`20_code`,
> **corpo delle funzioni dalla doc auto-generata** e mai dagli YAML,
> **numerazione `NN` globale per data** fra tutte le cartelle, e mai una modifica
> a un changeSet già mergiato.
>
> ⚠️ **Ordine dei changeSet, che qui morde davvero.** L'autogen mescola
> `00_schema` e `20_code` ordinando per `NN`: ogni funzione che nomina una
> colonna nuova deve avere un numero **più alto** dell'`ALTER TABLE` che la
> aggiunge. Vale per D-8 rispetto a D-5, e per D-9/D-10 rispetto a D-5.

#### Fase A — La rete di sicurezza *(condivisa con la slice 1 del cantiere incassi)*

> ✅ **APPLICATA E VERDE il 2026-08-15.** Sette changeSet (`20260815-03` … `-09`),
> due codici errore a catalogo, un pgTAP nuovo (12/12) e la fixture di quello
> esistente adeguata (19/19). **`pgtap-baseline.sh vendite`: nessuna
> regressione** — 24 rossi, tutti già noti. Cronaca, residui e il difetto
> trovato nel collaudo in **§8.2-bis**.
>
> 🔴 **Chi arriva prima la fa, e non si fa due volte.** Il cantiere incassi la
> dichiara dentro la sua slice 1 (§2-bis D1-bis); §8.0-a dice che la finestra si
> apre anche senza di lei. Se la slice 1 parte prima, questi quattro passi sono
> suoi; altrimenti sono il primo lavoro di questo cantiere.

| | Passo | Dove |
| --- | --- | --- |
| **D-0** | ⛔ **Le due soglie: entrambe o nessuna.** Una configurazione a metà oggi **spalanca** il meccanismo invece di spegnerlo (§8.0-b) | `00_schema/anagrafiche/` |
| **D-1** | **La generazione cambia perimetro**: solo sorgenti **DEFINITIVA**, e il ramo `UPDATE` **sparisce** | `20_code/vendite/` |
| **D-2** | **CHECK** `importo <> 0` + CHECK sul vocabolario di `stato` | `00_schema/vendite/` |
| **D-3** | **Due guard**: corrispondenza col totale della sorgente, e capienza **al momento dell'applicazione** | `20_code/vendite/` |
| **D-4** | **La chiave a nove elementi** al posto dei cinque parametri sciolti | `20_code/vendite/` |

##### D-0 — Un errore di configurazione, non un comportamento

```sql
ALTER TABLE anagrafiche.emittenti_fiscali_utilities
  ADD CONSTRAINT chk_emittenti_fiscali_utilities_soglie_coppia
  CHECK ((minimo_soglia_min IS NULL) = (minimo_soglia_max IS NULL));
```

Entrambe vuote = meccanismo **spento**; entrambe valorizzate = attivo sulla
banda; **una sola = si rifiuta di salvare**. Il vincolo esistente
(`chk_…_soglie`) presidia solo `min <= max` e la coppia incompleta la **ammette**
per costruzione.

⚠️ **Prima di applicarlo, misurare le righe già a metà** e sanarle a mano — su
dev i dati sporchi si correggono così, non con un fix software. Un CHECK che
scatta all'apply su righe preesistenti fa fallire il migrate.

⭐ E l'errore va reso parlante: la violazione arriva al backend come vincolo, e
si mappa a un codice di dominio (`E_FONDO_SOGLIE_INCOMPLETE`, classe
`DATO_ERRATO`) con il campo dichiarato, così l'operatore vede *quale* soglia
manca invece di un messaggio di database.

##### D-1 — Sorgente **DEFINITIVA**, e il ramo `UPDATE` sparisce

Due modifiche, e discendono entrambe dalle regole di Tid (§8.1 F-1):

1. **filtro di stato sulla sorgente**: solo `DEFINITIVA`. Oggi la generazione
   **non filtra nessuno stato** — e non è un dettaglio: `fn_get_saldo_fattura`
   non guarda lo stato, quindi una fattura **`ANNULLATA`** con `minimo = true`
   restituisce il totale intero e **genera un fondo**, che finisce addebitato su
   un altro documento. Non è mai successo perché di fondi non ne è mai stato
   generato nessuno;
2. **niente più `UPDATE`**: il fondo si crea una volta, con l'importo letto in
   quel momento, e non si ricalcola più.

⭐ **Le due cose si tengono a vicenda, ed è il motivo per cui «DEFINITIVA» è la
soglia giusta**: misurato su `config.stati_doc_fiscale_transizioni`, da
`DEFINITIVA` si va **solo a `INVIATA`**, e l'unico ritorno a `DRAFT` parte da
`EMESSA`. Una sorgente definitiva **non torna indietro**: «congelato quando la
sorgente è definitiva» non ha eccezioni da gestire.

⚠️ **Con l'`UPDATE` sparisce anche l'`ANNULLATO` automatico a target zero.** Il
buco che questo apre — un fondo non più dovuto che resta `DISPONIBILE` e viene
comunque applicato — lo chiude **D-3**, non un altro automatismo. 🔴 **D-1 senza
D-3 è peggio di non fare niente.**

##### D-3 — Due guard diversi, e non vanno confusi

**(a) Corrispondenza col documento** — trigger `_a10_` BEFORE INSERT/UPDATE, solo
per `origine = 'AUTOMATICA'`:

```text
l'importo non è zero
ha lo stesso segno del totale_a_pagare della fattura sorgente
non lo supera in valore assoluto
```

⚠️ Scritta così, **mai** come «compreso fra 0 e il totale»: su una sorgente a
credito gli estremi si invertono e il guard diventa una porta chiusa. Qui il caso
non è di bordo — è **metà della banda**.

**(b) Capienza al momento dell'atto** — dentro `fn_applica_fondi_fattura`:

```text
prima di assegnare il fondo s alla figlia, verifica che
    saldo_sorgente_al_netto_del_proprio_contributo(s)  copra ancora  s.importo
altrimenti NON assegnare, e lascia la riga dov'è (finirà nell'elenco)
```

⭐ **È il pezzo che rende inutile qualunque automatismo di allineamento**: invece
di tenere aggiornato un numero perché sia giusto quando servirà, lo si **rilegge
quando serve**. Livello 2 di §3-bis alla lettera — *i saldi si leggono, non si
conservano*. E non è un ricalcolo del fondo: è il controllo che la sorgente non
sia stata pagata nel frattempo.

⚠️ **Trappola del doppio conteggio, già risolta una volta.** Il
`saldo_contabile` della sorgente **contiene già** la riga contabile del fondo, se
il fondo è passato di lì. `fn_sync_contabili_fondo_fattura` la scorpora già, con
`v_saldo_contabile_source`: **quella formula si estrae e si riusa**, non si
riscrive.

> **Regola del 2** → nuova `vendite.fn_saldo_sorgente_fondo(p_fattura_sorgente_id, p_source_id)`
> `STABLE`, che ritorna il saldo della sorgente **al netto del contributo del
> fondo indicato**; la usano D-3(b), `fn_sync_contabili_fondo_fattura` (che
> smette di calcolarlo inline) e D-9. Tre chiamanti, una formula.

##### D-4 — 🔴 La chiave: il fondo ne usa metà, e il progetto ha **già pagato** questo difetto

La chiave con cui si accorpano le attività in una fattura è
`vendite.fn_build_fattura_key`, e ha **nove** elementi:

```text
billing_account · tipo_doc_fiscale · valuta · emittente · reseller
utility · registro · termine_pagamento · modalita_pagamento
```

| Funzione | Elementi usati | Mancano |
| --- | ---: | --- |
| `fn_genera_fondi_fattura_source` | **4** (`utility` scritta ma non filtrata) | utility, reseller, registro, termine, modalità |
| `fn_applica_fondi_fattura` | **5** | reseller, registro, termine, modalità |

**Conseguenza concreta**: un fondo nato da una fattura a 30 giorni può essere
applicato a una figlia a 60 giorni — due documenti che il sistema ha
**deliberatamente tenuti separati**, visto che il termine è nella chiave proprio
per non accorparli.

⭐ **E questo identico difetto è già stato corretto un anello prima.** Il
`COMMENT` di `fn_get_or_create_fattura_header` lo dice:

> *«il WHERE del lookup confronta TUTTI e nove gli elementi della chiave —
> **utility_id (che mancava da sempre)** … Chiave e lookup disallineati **si
> annullano a vicenda**»*

Il fondo è il **terzo specchio**, e nessuno l'ha riallineato.

⭐ **La correzione è anche una semplificazione.** Sorgente e figlia sono
entrambe righe di `vendite.fatture`, e tutti e nove gli elementi sono **colonne
di quella tabella**: il confronto si fa **riga contro riga**, con
`IS NOT DISTINCT FROM` sui quattro nullable. Le funzioni del fondo smettono
quindi di ricevere cinque parametri sciolti dal Python, e con loro spariscono:

* il difetto dell'`utility_id` che si ribalta a ogni giro (era il chiamante a
  passare uno scope incoerente, un giro per utility);
* le **N chiamate in autocommit** del repository (BE-2): resta una chiamata per
  lotto.

⚠️ Sul caso **BASE**: `BASE` è una **utility** (`config.utilities` id 5,
*Servizio Base*) e `billing_account.utility_id` è **NOT NULL** — quindi la
utility c'è sempre e combacia per uguaglianza. Una riga di `vendite.fatture` con
`utility_id` vuoto non è una fattura BASE: è un dato incompleto, e resta fuori
(comparirà nell'elenco di D-10 col suo motivo).

#### Fase B — Il registro degli atti

> ✅ **APPLICATA E VERDE il 2026-08-15.** Sette changeSet (`20260815-12` … `-18`),
> tre codici errore a catalogo, sette asserzioni pgTAP in più (sei sulla Fase B +
> la ragione dell'annullamento **sul dato**). **`pgtap-baseline.sh vendite`:
> nessuna regressione.** Elenco, cronaca e residui in **§8.2-quater**.

| | Passo | Dove |
| --- | --- | --- |
| **D-5** | **Colonne dell'atto** su `fatture_fondi_fattura_source`: `origine` (`varchar` NOT NULL DEFAULT `'AUTOMATICA'`, CHECK `IN ('AUTOMATICA','MANUALE')`) e `motivo` (`text` NULL, obbligatorio per `origine = 'MANUALE'` e per `stato = 'ANNULLATO'`) | `00_schema/vendite/` |
| **D-6** | **Lock delle colonne portanti**: `importo`, `fattura_sorgente_id`, `tipo_fondo_fattura_id`, `origine` immutabili dopo l'INSERT, via `script.trgfn_lock_columns` (già usato su `tipi_fondi_fattura`) | `20_code/vendite/` |
| **D-7** | **Guard di transizione** `trgfn_fondi_source_guard_transizione`, trigger `_a10_` BEFORE UPDATE | `20_code/vendite/` |
| **D-8** | **Un solo atto vivo per sorgente** — indice unico parziale | `00_schema/vendite/` |

> 🔴 **`atto_precedente_id` è stato tolto** (2026-08-15). Serviva alla revoca +
> riemissione, che con la regola «il fondo non si ricalcola mai» **non esiste
> più**. E la catena dei riporti resta comunque leggibile:
> `fatture_fondi_fattura.riferimento_fattura_id` porta già la fattura di
> provenienza. *Una colonna che esiste per un meccanismo che non c'è più è debito
> al primo giorno.*

##### D-5 — ⭐ `origine` non dice «chi l'ha creato»: dice **quale regola si applica**

È la correzione di F-5. La colonna non serve a vietare i fondi negativi
all'automatismo — quelli sono metà del meccanismo — ma a distinguere:

| `origine` | Presidio |
| --- | --- |
| `AUTOMATICA` | **vincolato**: il guard di corrispondenza D-3(a) legge la sorgente e rifiuta ciò che non le assomiglia |
| `MANUALE` | **governato**: motivo obbligatorio, azione di processo, e viene dal processo rimborsi — che l'eccedenza la conosce, mentre il database no |

🔴 **Il caso che dimostra perché il guard non può essere unico**: l'eccedenza di
un sovra-incasso è un fondo **a credito su una fattura dal totale positivo**,
cioè di segno opposto per costruzione. Un guard applicato a tutti rifiuterebbe
proprio l'atto per cui la strada manuale esiste.

##### D-6 — ⭐ È il lock, non la buona volontà, a rendere il fondo un atto

Con `importo` bloccato dopo l'INSERT, *«non si ricalcola mai»* smette di essere
una regola che qualcuno deve ricordare e diventa una cosa che il database non
lascia fare. È la traduzione strutturale della regola di Tid: *una volta che la
fattura è definitiva, il suo fondo resta quello.*

⭐ **Ed è la stessa regola che il progetto applica già agli altri satelliti della
fattura.** `trgfn_fattura_satellite_guard_congelamento` — *«superata la soglia
DRAFT/EMESSA i suoi satelliti sono uno snapshot e non si toccano più»* — è
montato su `fatture_scadenze` e `fatture_indirizzi`. **Sui fondi no.** Il fondo è
l'unico satellite della fattura che non è congelato; la regola non è nuova, è la
regola della casa applicata a un satellite che se n'era dimenticata.

⚠️ **Perché il lock di colonna e non quel trigger.** Sui fondi non si può
congelare la **riga**: l'assegnazione alla figlia avviene dopo, ed è legittima.
Si congelano l'**importo** e la sorgente, non l'assegnazione.

⚠️ **Due trappole note su questo passo.** (1) Le automazioni che montano i trigger
girano **solo in contesto `ci_apply`**: sul migrate manuale il trigger di lock
arriva col pgagent di fine giornata, non subito. (2) Se un domani si aggiungono
colonne all'elenco dei lock su una tabella che ce l'ha già, su DB esistenti serve
**DROP + rigenera**: qui è un montaggio nuovo, quindi il caso non si presenta.

##### D-7 — Le transizioni, e ⚠️ il test che le contraddice già

```text
DISPONIBILE  →  ASSEGNATO | ANNULLATO
ASSEGNATO    →  DISPONIBILE (solo dal reset tecnico) | ANNULLATO
ANNULLATO    →  ∅   (terminale)
```

Tre stati, non quattro: `REVOCATO` è caduto con la revoca+riemissione.

🔴 **Prima di scrivere il guard, leggere `db/pgtap/vendite/test-fondi-fattura.sql`.**
Quel file percorre `ASSEGNATO → DISPONIBILE` (test 9-10) e `→ ANNULLATO` (test
15-16): un guard restrittivo scritto senza guardarlo lo fa diventare rosso, e il
rosso sembrerà una regressione del fondo invece che una fixture da adeguare.

**Perché un CHECK + trigger e non una tabella di stati con le transizioni
dichiarate**: gli stati del fondo non sono un workflow che l'operatore vede — non
hanno etichette, icone, azioni di UI. Sono tre valori interni. Se un domani
servono etichette o transizioni configurabili, la lookup si aggiunge allora.

##### D-8 — Un solo atto vivo per sorgente

Oggi **nulla** impedisce due fondi vivi sulla stessa fattura sorgente: il
`NOT EXISTS` dell'`INSERT` è dentro una funzione, non un vincolo.

```sql
CREATE UNIQUE INDEX uq_fondi_source_atto_vivo_automatico
  ON vendite.fatture_fondi_fattura_source (fattura_sorgente_id, tipo_fondo_fattura_id)
  WHERE stato IN ('DISPONIBILE','ASSEGNATO') AND origine = 'AUTOMATICA';
```

⚠️ **Non è pignoleria**: due fondi vivi sulla stessa sorgente producono **due
righe contabili** su di lei, la cui somma supera il suo residuo — ed è
esattamente il modo in cui `importo_target` va sotto zero senza che esista un
solo movimento (§8.0-a). Il vincolo chiude quella porta dall'interno.

⚠️ **Il predicato è ristretto a `origine = 'AUTOMATICA'` di proposito**: è
l'automatismo che non deve poterne creare due. Un secondo atto **manuale** sulla
stessa sorgente (un accredito accanto a un addebito, F-3) è la scelta di una
persona, ed è visibile nell'elenco.

⚠️ E l'indice **non** ha `NULLS NOT DISTINCT`: le due colonne della chiave sono
`NOT NULL`, quindi non serve — ma va verificato e non dato per scontato, perché è
il punto in cui una chiave con NULL fallisce in silenzio.

#### Fase C — La proposta derivata e l'elenco da guardare

> ✅ **APPLICATA E VERDE il 2026-08-15.** Cinque changeSet (`20260815-19` … `-23`),
> pgTAP del governo da 18 a **29** asserzioni, baseline `vendite` senza
> regressioni. Elenco, scoperte e residui in **§8.2-quinquies**. ⚠️ I passi sono
> **due sulla carta e cinque nei file**: la ragione — la stessa regola non può
> stare in due posti — è la scoperta principale della fase.

| | Passo | Dove |
| --- | --- | --- |
| **D-9** | **`vendite.fn_fondo_fattura_proponibile(p_fattura_sorgente_id, p_tipo_fondo_fattura_id)`** `STABLE` — il numero, **mai conservato**. Costruita su `fn_saldo_sorgente_fondo` (D-3), così proposta e guard non possono divergere | `20_code/vendite/` |
| **D-10** | **`vendite.vw_fondi_fattura_da_decidere`** — l'elenco. ⚠️ `security_invoker = true` **obbligatorio** | `20_code/vendite/` |

##### D-10 — I casi che chiedono una persona

| Caso | Motivo | Azione suggerita |
| --- | --- | --- |
| sorgente nella banda e definitiva, **nessun atto vivo** | `PROPOSTA_SENZA_ATTO` | emettere il fondo (o lasciarlo) |
| sorgente nella banda **senza `utility_id`** (dato incompleto, esclusa da D-4) | `UTILITY_NON_ATTRIBUIBILE` | completare il dato sulla fattura |
| atto `DISPONIBILE` non più capiente (rifiutato da D-3b) | `NON_PIU_CAPIENTE` | annullare l'atto, o gestire il pagamento ricevuto |
| ⭐ **aggiunto scrivendo**: residuo che **non corrisponde** al documento — l'automatismo tace in silenzio | `IMPORTO_NON_CORRISPONDENTE` | capire da dove viene la riga contabile che sfonda il documento |
| ~~soglie configurate **a metà** sull'emittente × utility~~ | ~~`CONFIGURAZIONE_INCOMPLETA`~~ | 🔴 **non esiste**: D-0 è applicato dal 2026-08-15 e rende il caso irraggiungibile (vedi qui sotto — era previsto) |

> 🔴 **Il caso «eccedenza da destinare» è uscito da questo elenco** (2026-08-15).
> Un sovra-incasso è materia del **processo rimborsi**, che sta in `pagamenti` e
> **se le va a cercare da sé** (§8.1 F-3, decisione di Tid): metterlo anche qui
> significherebbe due elenchi che raccontano lo stesso fatto e che divergono al
> primo cambio. `vendite` espone un punto d'ingresso, non un secondo cruscotto.

⚠️ **`CONFIGURAZIONE_INCOMPLETA` ha una data di scadenza**: dopo D-0 quella riga
non può più esistere, perché il vincolo la rende insalvabile. Va tenuta finché il
CHECK non è applicato **e le righe storiche non sono sanate**, poi tolta — una
riga di elenco che non può accadere insegna una cosa falsa a chi la legge.

⚠️ **La vista presenta, non sana.** Nessuna riga di questa vista deve avere un
gemello che la corregge da sola. È la regola pratica di §5.2, e qui è dove si
vede se è stata rispettata.

⚠️ **`security_invoker` non è una rifinitura**: `vendite.fatture` ha la RLS
operatori, `fatture_fondi_fattura_source` **no**. Una vista che le unisce senza
`security_invoker` mostrerebbe a ogni operatore i fondi di **tutti** gli
emittenti. Il progetto ha già pagato questo difetto una volta (fix V-1 della
fatturazione a due lenti).

**Il vocabolario dei motivi** sta in un `CHECK` sulla colonna della vista, non in
una lookup: sono quattro valori chiusi e nessuno li configura. Le etichette le
mette il FE con `labelOrCode` (fail-visible), come per i motivi di fermo del
cruscotto backlog. ℹ️ Oltre i sei-sette valori la scelta si ribalta e diventa una
`config.motivi_fondo_fattura` sul modello di `config.motivi_fermo`.

#### Fase D — L'atto manuale · **è la porta del processo rimborsi**

> ⭐ **Chi chiama non è uno schermo di `vendite`**: è il **processo rimborsi**, in
> `pagamenti`, quando l'operatore sceglie la terza uscita (§8.1 F-3). Questa fase
> costruisce **la porta**, non la stanza dietro.

| | Passo | Dove |
| --- | --- | --- |
| **D-11** | **`vendite.fn_crea_fondo_fattura_manuale(...)`** — madre DB. Crea l'atto `MANUALE`: sorgente, tipo, importo (**segno libero**), motivo **obbligatorio**. Guard: sorgente esistente, scope emittente, `importo <> 0`. ⚠️ **Non** applica la corrispondenza di D-3(a): sarebbe proprio il caso che deve passare | `20_code/vendite/` |
| **D-12** | **`vendite.fn_annulla_fondo_fattura(p_source_id, p_motivo)`** — porta ad `ANNULLATO` con motivo obbligatorio. **Rifiuta** se il fondo è `ASSEGNATO` su una figlia la cui contabile è `CHIUSA` — stesso criterio di `fn_reset_fondi_fattura`, **riusato e non riscritto** | `20_code/vendite/` |
| **D-13** | **Azione di processo** `governa_fondo_fattura` — append a `config/azioni_processo.csv` (area 2 = vendite, id 31, `pericolosa = t`) | `80_data/` |
| **D-14** | **Codici errore a catalogo** — append a `config/codici_errore.csv` (codice + **classe**) e `config/messaggi_errore.csv` (id progressivo: l'ultimo è 902) | `80_data/` |

⚠️ **D-14: solo append ai CSV, mai un loader nuovo.** I loader `runOnChange`
esistenti ripescano il file. Codici proposti, con la classe che ne deriva lo
status lato BE:

| Codice | Classe | Quando |
| --- | --- | --- |
| `E_FONDO_NOT_FOUND` | `NON_TROVATO` | il fondo indicato non esiste |
| `E_FONDO_IMPORTO_NON_VALIDO` | `DATO_ERRATO` | importo zero |
| `E_FONDO_NON_CORRISPONDE_SORGENTE` | `DATO_ERRATO` | guard D-3(a): segno opposto al totale della sorgente, o superiore in valore assoluto |
| `E_FONDO_MOTIVO_OBBLIGATORIO` | `DATO_ERRATO` | atto manuale o annullamento senza motivo |
| `E_FONDO_STATO_NON_AMMESSO` | `CONFLITTO_STATO` | transizione fuori dalla matrice di D-7 |
| `E_FONDO_ANNULLAMENTO_BLOCCATO` | `CONFLITTO_STATO` | annullamento rifiutato: contabile già `CHIUSA` |
| `E_FONDO_SOGLIE_INCOMPLETE` | `DATO_ERRATO` | D-0: una sola delle due soglie valorizzata |

⚠️ **Leggere il ramo che solleva, non il nome del codice.** Il suffisso
*suggerisce* la classe, non la decide: `E_FONDO_ANNULLAMENTO_BLOCCATO` è un 409 e
non un 403 perché non è un diritto che manca, è lo **stato** della contabile a
impedirlo.

⚠️ **`E_FONDO_NON_CORRISPONDE_SORGENTE` non è un errore che l'operatore può
correggere sul giro automatico**: lì il caso non arriva a sollevare, perché il
`WHERE` della generazione non lo produce (§8.1 F-5). Il codice serve al percorso
manuale e ai presidi — un guard che non solleva mai è un guard di cui nessuno si
accorge quando smette di funzionare.

⭐ **Su `E_FONDO_IMPORTO_NON_VALIDO`, `E_FONDO_MOTIVO_OBBLIGATORIO` e
`E_FONDO_SOGLIE_INCOMPLETE` vale la pena usare `RAISE … USING COLUMN = …`**: il
backend legge già `diag.column_name` e lo consegna al client in `error.fields` —
sono campi di form veri, ed è il caso per cui quel canale è stato aperto. Su
D-0 il campo dice **quale delle due soglie** manca, che è l'unica cosa utile.

#### Fase E — Pulizia e verità documentale

> ✅ **D-15, D-16 e D-17 FATTI** (D-17 in due giri: la bonifica il 2026-08-15, la
> riscrittura al presente delle note 🟠 subito dopo l'apply della Fase B).
> **D-18 è aperto per costruzione**: cresce con ogni fase.

| | Passo |
| --- | --- |
| **D-15** | ✅ **FATTO il 2026-08-15** — **`DROP FUNCTION vendite.fn_sync_pagamento_fondo_fattura(bigint)`** (F-4) + rimozione della §6 di `db/pgtap/vendite/test-fattura-utils-critical-termini.sql` e `plan(15)` → `plan(14)`. ⚠️ Le due metà nello **stesso lotto**: il presidio dei riferimenti morti gira dopo il `migrate` e un `DROP` senza il test diventa rosso in CI |
| **D-16** | ✅ **FATTO il 2026-08-15** — `COMMENT` su `fn_reset_fondi_fattura`: è il reset **tecnico della figlia**, non una reazione ai pagamenti (F-2) |
| **D-17** | ✅ **Bonifica documentale — FATTA il 2026-08-15** (ordine di Tid: *«procedi alla correzione di tutti»*). Inventario e stato per documento qui sotto. ⚠️ Solo i `manual/`, le guide e i doc di lavoro: gli auto-gen si rigenerano. ✅ **Secondo giro fatto** dopo l'apply di Fase A e Fase B: le note 🟠 sono state riscritte **al presente**. Resta la stessa regola per le fasi che verranno |
| **D-18** | pgTAP — §8.5 |

##### D-17 — L'inventario, e ⚠️ la distinzione che conta

Ricognizione fatta il **2026-08-15** su tutta `docs/` più il codice, su richiesta
di Tid; **correzioni applicate lo stesso giorno**. ⭐ **La distinzione utile non è
«giusto/sbagliato», è *quando*:**

* 🔴 **sbagliato oggi** — il documento non descrive il codice che gira. Va
  corretto **subito**, indipendentemente dal piano;
* 🟠 **lo diventa con l'implementazione** — oggi è fedele. ⭐ **Non riscritto al
  futuro, ma annotato**: la descrizione di com'è resta, e accanto c'è una tabella
  *«oggi → diventerà, con quale passo»*. Riscriverlo al presente adesso
  racconterebbe un sistema che non esiste; lasciarlo muto lo farebbe progettare
  sopra da chi arriva domani.

###### 🔴 Sbagliato oggi — tre

| Documento | Che cosa dice di falso |
| --- | --- |
| `dbzero/vendite/manual/fn_genera_fondi_fattura_source.md` | *«Seleziona fatture nel perimetro BA/**utility**/tipo_doc/emittente/valuta»* — **la funzione su `utility` non filtra affatto** (D-4). La doc dichiara un perimetro che il codice non applica: è il difetto e la sua smentita nello stesso posto |
| `dev/work-done/fatturazione-attivita-progetto.md` §«Analisi fondi fattura (WIP)» | Un **design mai eseguito** parcheggiato in `work-done/`: policy `riapribile` per tipologia di fondo, *«se arriva uno storno la source torna DISPONIBILE»* — cioè un **automatismo che scrive in reazione a un pagamento**, escluso da §3-bis del cantiere incassi; e *«lo storno»*, che dopo D3-d **non è più un concetto**. In più `SUM(importo) >= totale_a_pagare` come regola di «pagata»: su un documento a credito il confronto si inverte |
| `guide/gestione-dei-pagamenti.md` §Fondi fattura | *«es. importo minimo **non raggiunto**»* — racconta **solo il capo superiore** della banda. Chi legge conclude che un fondo è sempre a debito: è **precisamente l'errore che abbiamo commesso noi** scrivendo il tampone `> 0`. E delle due soglie — la configurazione che accende tutto — non c'è traccia |

###### 🟠 Diventeranno sbagliati — quattro, ognuno legato al suo passo

| Documento | Cosa supera | Con |
| --- | --- | --- |
| `manual/fn_genera_fondi_fattura_source.md` | *«mantiene allineata la source in base al saldo»*, il ramo `UPDATE`, l'`ANNULLATO` a saldo zero, *«idempotente: riallinea i dati»* | **D-1** |
| `manual/fn_applica_fondi_fattura.md` | la chiave a cinque elementi; nessun controllo di capienza | **D-3b**, **D-4** |
| `manual/fatture_fondi_fattura_source.md` | *«In caso di storni, la policy di riapertura va gestita per tipologia fondo»* + *«Reset per tipologie non standard (WIP)»*; `ANNULLATO` = «documento sorgente già saldato» | **D-1**, e D3-d incassi |
| `manual/fn_sync_pagamento_fondo_fattura.md` | **il file intero**: è il manuale di una funzione che si ritira | **D-15** |

> ✅ **Secondo giro fatto il 2026-08-15**, applicate Fase A e Fase B: le quattro
> note sono state **riscritte al presente**, non lasciate al futuro. Le prime due
> con la Fase A; la terza (`manual/fatture_fondi_fattura_source.md`) con la Fase
> B — la tabella *«oggi → diventerà»* è diventata *«prima → adesso, e chi lo fa»*,
> con l'elenco degli otto presidi vivi; la quarta è sparita **col file**.
> Aggiornati nello stesso giro `manual/fn_reset_fondi_fattura.md` e
> `manual/fn_sync_contabili_fondo_fattura.md` (annullamento **con ragione sul
> dato**, saldo letto da `fn_saldo_sorgente_fondo`) e la sezione «perimetro» di
> `manual/trgfn_fondi_source_guard_importo.md`, che dava al futuro il ritiro dalla
> strada manuale ormai applicato dal `-18`. ⭐ **Scritto il `manual/` nuovo** di
> `trgfn_fondi_source_guard_transizione`.

###### ⭐ Due documenti che invece avevano ragione, e che avremmo dovuto leggere prima

| Documento | Cosa dice |
| --- | --- |
| `manual/fn_ricalcola_totali_fattura.md` | *«Imposta `minimo = true` quando `totale_a_pagare` **rientra nella soglia** (`minimo_soglia_min`/`minimo_soglia_max`)»* — è **l'unico posto in tutta la documentazione dove la banda è detta correttamente**. Manca solo l'avvertenza sul fail-open (D-0) |
| `manual/tipi_fondi_fattura.md` | *«addebiti/**accrediti** fatture precedenti»* — il verso a credito era **previsto dall'origine**. Il tampone `> 0` contraddiceva il catalogo, non solo il dominio |

🔴 **La lezione, e vale oltre questo cantiere**: la banda era scritta in due
documenti su venti, e nessuno dei due era quello che descrive il **fondo**. La
regola vive nella funzione che scrive `minimo`, non in quella che legge il flag —
*chi documenta un consumatore non documenta la regola che lo governa.*

###### Rifiniture minori (stesso lotto, costo nullo)

* `manual/fatture.md`: *«opzione "fattura di minimo"»* — non è un'opzione, è un
  **calcolo**. È l'equivoco di §8.0-b in due parole;
* `manual/centri_riscossione.md`: corretto, ma manca la nota **non-cassa** —
  quei centri vanno esclusi da ogni misura di «incassato» (Fase F);
* `mappa-concentrica.md` §406: *«Non urgente oggi, lo diventa col primo incasso
  reale»* — superato da §8.0-a.

⚠️ **Una classificazione da correggere altrove**:
`dev/work-done/analisi-attivazione-rls-operatori.md` archivia
`fatture_fondi_fattura_source` come **«NO — config. Config di fatturazione»**. La
*conclusione* (niente RLS) resta giusta — il perimetro passa dalla fattura — ma
la **ragione** è falsa: non è configurazione, è un registro transazionale che
muove denaro. Una ragione sbagliata produce la decisione sbagliata al giro dopo,
quando la domanda cambia.

**✅ Nessuna azione** su: `readme.md`, `soggetti-e-ruoli-anagrafici.md`,
`api_fattura_dettaglio.md`, i tre brief RLS, `correzione-e-generico.md`,
`fn_cleanup_fatture_by_ids.md` (anzi: la sua nota *«il reset non cancella la
source, ne azzera l'assegnazione»* è **esatta e utile**),
`fn_scope_ba_ownership_via_fattura.md`, `api_lookup_codici.md`. Sono elenchi e
censimenti. **Nel codice** (`backend/`, `frontend/src/`) non esiste una sola
riga che descriva la logica del fondo: due sole occorrenze, entrambe etichette
(`"Tipo fondo fattura non trovato."`, `'Tipi Fondi Fattura'`).

#### Fase F — Il confine col posting: qui si **dichiara**, non si fa

⭐ **Verificato il 2026-08-15, e corregge in meglio un timore del cantiere
incassi.** Il B-1 di quel brief teme che portare una riga a `POSTATA` faccia
rigenerare il fondo. Con un posting **atomico** (D3-b: cambio di stato e
creazione del movimento nella stessa unità) **la bilancia regge da sé**:

```text
prima :  target = totale − 0        − importo      = totale − importo
dopo  :  target = (totale − importo) − 0           = totale − importo
```

I due termini si scambiano lo stesso importo. 🔴 **Il rischio B-1 è tutto nella
non-atomicità**, che D3-b risolve per costruzione — non c'è un secondo lavoro da
fare qui.

⚠️ **Ma resta una cosa da scrivere adesso nel brief incassi, non da scoprire
dopo.** La riga contabile che il fondo crea è `ABBINATA`, cioè **postabile**:
quando il posting esisterà diventerà un `vendite_movimenti` — ed è **giusto**,
perché la sorgente è davvero stata saldata, per **trasferimento** e non per
cassa. Segue che **ogni misura di «incassato» deve escludere i centri non-cassa**
(`is_fondo_fattura`, `is_compensazione`), altrimenti conta come denaro arrivato
ciò che è solo stato spostato da una fattura a un'altra.

---

### 8.2-bis Fase A — applicata il 2026-08-15

> ✅ **Migrazione applicata, suite verde, doc rigenerata.** Resta il **commit**.
>
> | Verifica | Esito |
> | --- | --- |
> | `migrate` dei 7 changeSet | ✅ applicati (i due CHECK e il trigger risultano nell'auto-gen) |
> | `test-fondi-fattura-governo.sql` | ✅ **12/12** (dopo la correzione di §8.2-ter) |
> | `test-fondi-fattura.sql` (fixture adeguata) | ✅ **19/19** |
> | `pgtap-baseline.sh vendite` | ✅ **nessuna regressione** — 24 rossi, tutti noti |
> | guardrail statici CI (`runOnChange`, preambolo pgTAP) | ✅ verdi; il debito `throws_ok` resta a 137 su soglia 137 |
> | doc `dbzero` | ✅ rigenerata: i due `manual/` nuovi sono agganciati alle pagine auto-gen |

| File | Passo | Cosa fa |
| --- | --- | --- |
| `00_schema/anagrafiche/20260815-03-add-check-emittenti-fiscali-utilities-soglie-coppia` | **D-0** | CHECK «entrambe le soglie o nessuna». ✅ Applicabile senza sanatoria: le due righe esistenti hanno entrambe vuote (verificato con Tid) |
| `00_schema/vendite/20260815-04-add-check-fondi-source-importo-e-stato` | **D-2** | `importo <> 0` + vocabolario chiuso di `stato`. Tabella a zero righe |
| `20_code/vendite/20260815-05-create-fn-saldo-sorgente-fondo` | **D-3** | La formula unica «quanto regge ancora la sorgente», estratta dalla copia inline |
| `20_code/vendite/20260815-06-create-trgfn-fondi-source-guard-importo` | **D-3a** | Guard di corrispondenza fondo ↔ sorgente (segno + valore assoluto) |
| `20_code/vendite/20260815-07-update-fn-genera-fondi-fattura-source-atto-unico` | **D-1 + D-4** | Solo sorgenti `DEFINITIVA`; via il ramo `UPDATE` e l'`ANNULLATO` automatico; `utility_id` entra nel filtro |
| `20_code/vendite/20260815-08-update-fn-applica-fondi-fattura-chiave-e-capienza` | **D-3b + D-4** | Chiave a nove elementi riga-contro-riga + rilettura della capienza |
| `20_code/vendite/20260815-09-update-fn-sync-contabili-fondo-adotta-saldo-sorgente` | coda D-3 | La sync adotta la formula estratta (behavior-preserving) |
| `80_data/sql/config/{codici_errore,messaggi_errore}.csv` | **D-14** parziale | `E_FONDO_NON_CORRISPONDE_SORGENTE`, `E_FONDO_SOGLIE_INCOMPLETE` — solo append, nessun loader nuovo |
| `db/pgtap/vendite/test-fondi-fattura-governo.sql` | **D-18** | 12 asserzioni sulla Fase A |
| `db/pgtap/vendite/test-fondi-fattura.sql` | — | ⚠️ **fixture adeguata**: la fattura sorgente nasceva senza stato e senza utility, e con i nuovi filtri non avrebbe più generato niente |
| `dbzero/vendite/manual/fn_saldo_sorgente_fondo.md` · `trgfn_fondi_source_guard_importo.md` | — | Doc concettuale delle due funzioni nuove, nello standard dei `manual/` |

#### ⚠️ Tre scelte fatte scrivendo, che vale la pena conoscere

**1. Le firme non cambiano, e non è pigrizia.** La chiave a nove elementi si
chiude **dentro** `fn_applica_fondi_fattura`, che ha già sotto mano entrambe le
fatture: nessun parametro nuovo, nessun tocco a `backend/` — che è fuori dal
perimetro DB. La madre DB per lotto resta una **richiesta al BE** (§8.3).

**2. I cinque parametri di scope cambiano mestiere.** Da filtro sulla *source* a
verifica sulla *figlia*. Applicati alla source erano ridondanti e potevano far
**saltare in silenzio** un fondo la cui colonna denormalizzata fosse rimasta
indietro; sulla figlia sono una sanity check che non può nascondere niente.

**3. La preCondition sul codice errore è stata tolta dal changeSet -06.** `20_code`
gira **prima** di `80_data`: su un DB ricostruito da zero avrebbe cercato un seed
che arriva due fasi dopo. Trappola già registrata, e già pagata una volta.

### 8.2-ter 🔴 Il difetto trovato nel collaudo: ho collaudato il guard credendo di collaudare il CHECK

La prima corsa ha dato **una regressione**, e il rosso era del test — non del
codice. Vale la pena scriverla per intero, perché è **la trappola che avevo
appena finito di scrivere in §8.5**.

```text
# Failed test 3: "D-2: importo zero rifiutato dal CHECK"
#       caught: P0001: Fondo fattura di importo 0 non coerente con la
#               fattura di origine (totale 100.00).
#       wanted: 23514
```

**Perché.** I trigger `BEFORE ROW` girano **prima** dei CHECK. Su una sorgente
da 100, un `importo = 0` non arriva mai al vincolo: lo intercetta il guard di
corrispondenza, perché `sign(0)` non è il segno di **nessun** totale diverso da
zero. Il test chiedeva `23514` e otteneva `P0001` — cioè misurava il presidio
sbagliato.

**La correzione, ed è più di un cambio di SQLSTATE.** Il CHECK
`importo <> 0` è raggiungibile **solo da una sorgente a totale zero**, dove il
guard passa (0 e 0 hanno lo stesso segno e lo stesso valore assoluto). Il test
ha quindi una quinta fixture, `SRC_ZERO`, e collauda il vincolo dove il vincolo
esiste davvero. ⭐ Che è poi l'unico caso in cui serve: una fattura da zero non
genera fondo, e se qualcuno lo inserisse a mano è lì che il CHECK lo ferma.

> **La lezione, e non è «leggere meglio»**: avevo scritto l'avvertenza,
> l'ho ripetuta nel `COMMENT` della funzione, e ci sono cascato lo stesso —
> perché la trappola non sta nel *sapere* l'ordine di esecuzione, sta nel
> **nominare l'asserzione**. «Rifiutato dal CHECK» descrive il *meccanismo* che
> credo agisca; se avessi scritto «importo zero rifiutato» avrei asserito il
> *fatto*, e il test sarebbe passato dicendo una cosa vera. *Un test che nomina
> il meccanismo invece del comportamento verifica la propria ipotesi, non il
> sistema.*

#### 🔵 Cosa resta scoperto

* **Il caso «sorgente non più capiente» non ha un test runtime.** Per costruirlo
  serve una riga contabile `ABBINATA` sulla sorgente — cioè la fixture pesante
  che `test-fondi-fattura.sql` costruisce già. È l'assenza più importante di
  §8.5: il guard di capienza (D-3b) oggi è **collaudato solo per la via che
  passa**, non per quella che deve fermare;
* **l'`ANNULLATO` automatico dentro `fn_sync_contabili_fondo_fattura` resta.** È
  della stessa specie di quello rimosso dalla generazione, ma opera su fondi
  **già assegnati**: il denaro si è mosso, e toglierlo senza il processo rimborsi
  di `pagamenti` lascerebbe scoperto il doppio conteggio. 🔵 Candidato Fase B;
* **le tre richieste al BE** (§8.3) non sono state fatte: sono fuori perimetro.
  ⚠️ **R-1 è la più urgente** — finché `error_policies_generated.py` non viene
  rigenerato, i due codici nuovi sono a catalogo ma non hanno una classe lato
  backend, e il cancello `test_error_codes_db_policy_guardrail` lo vedrà.

ℹ️ Il dubbio sul test D-0 è risolto: il ruolo applicativo **ha** la scrittura su
`anagrafiche.emittenti_fiscali_utilities`, e il CHECK scatta come previsto
(`23514`). Nessun marcatore `-- pgtap-runner: owner` necessario.

---

### 8.2-quater Fase E (coda) e Fase B — **applicate** il 2026-08-15

> ✅ **Applicate e verdi.** `migrate` dei 9 changeSet `20260815-10`…`-18` (tutti
> `EXECUTED`), `test-fondi-fattura-governo` **18/18**, `test-fondi-fattura`
> **20/20**, `test-fattura-utils-critical-termini` **14/14**,
> `pgtap-baseline.sh vendite` **senza regressioni**. Dettaglio di cosa ha detto
> l'applicazione: più sotto, in *«L'applicazione, e cosa ha detto»*.

#### Coda della Fase E — i due passi facili

| File | Passo | Cosa fa |
| --- | --- | --- |
| `20_code/vendite/20260815-10-drop-fn-sync-pagamento-fondo-fattura` | **D-15** | `DROP` del guscio. ⚠️ Nello **stesso commit**: sezione tolta da `test-fattura-utils-critical-termini.sql` (`plan(15)` → `plan(14)`, indice rinumerato) e `manual/` eliminato |
| `20_code/vendite/20260815-11-comment-fn-reset-fondi-fattura-reset-tecnico` | **D-16** | Solo il `COMMENT`: il reset è **tecnico sulla figlia**, non una reazione ai pagamenti (F-2) |

#### Fase B — il registro degli atti

| File | Passo | Cosa fa |
| --- | --- | --- |
| `00_schema/vendite/20260815-12-add-fondi-source-origine-e-motivo` | **D-5** | Colonne `origine` (`AUTOMATICA`\|`MANUALE`) e `motivo` |
| `20_code/vendite/20260815-13-update-fn-fondi-annullamento-con-motivo` | **D-5** | I due scrittori automatici **valorizzano `motivo`** quando annullano |
| `00_schema/vendite/20260815-14-add-check-fondi-source-motivo-obbligatorio` | **D-5** | `motivo` obbligatorio su `MANUALE` e su `ANNULLATO` |
| `20_code/vendite/20260815-15-create-trg-fondi-source-lock-atto` | **D-6** | Lock di colonna: `importo`, sorgente, tipo, `origine` immutabili |
| `20_code/vendite/20260815-16-create-trgfn-fondi-source-guard-transizione` | **D-7** | Matrice degli stati, `ANNULLATO` terminale |
| `00_schema/vendite/20260815-17-add-uq-fondi-source-atto-vivo` | **D-8** | Indice unico parziale: un solo atto automatico vivo per sorgente |
| `20_code/vendite/20260815-18-update-trgfn-...-solo-automatica` | coda **D-5** | Il guard di corrispondenza si **ritira dalla strada manuale** |
| `80_data/…/{codici_errore,messaggi_errore}.csv` | **D-14** parz. | `E_FONDO_ATTO_IMMUTABILE`, `E_FONDO_STATO_NON_AMMESSO`, `E_FONDO_MOTIVO_OBBLIGATORIO` |
| `db/pgtap/vendite/test-fondi-fattura-governo.sql` | **D-18** | da 12 a **18** asserzioni |
| `db/pgtap/vendite/test-fondi-fattura.sql` | **D-18** | da 19 a **20**: la ragione dell'annullamento verificata **sul dato** |
| `docs/it/dbzero/vendite/manual/` | **D-17** | nuovo `trgfn_fondi_source_guard_transizione`; aggiornate la pagina della tabella, `trgfn_fondi_source_guard_importo`, `fn_reset_fondi_fattura`, `fn_sync_contabili_fondo_fattura` |

#### ⚠️ Tre cose scoperte scrivendo la Fase B

**1. `motivo` obbligatorio impone di toccare due funzioni che il piano non
nominava.** Un fondo passa ad `ANNULLATO` in due punti automatici — la sync
contabili e il reset bloccato — e nessuno dei due scriveva una ragione: nel
secondo la ragione esisteva, ma **in un messaggio di `fatture_log`**, cioè in un
diario invece che sul dato. Da qui il changeSet `-13`, e l'**ordine obbligato**
`-12` → `-13` → `-14`: mettere il vincolo prima degli scrittori lo farebbe
passare sulla tabella vuota di oggi e fallire al primo reset vero — un migrate
verde e un guasto rimandato a quando fa più male.

**2. `origine` senza il changeSet `-18` non governa niente.** Il piano diceva
che il guard di corrispondenza «si restringerà a `AUTOMATICA` con la Fase B», ma
non lo elencava fra i passi. Senza, la colonna esisterebbe e il guard
continuerebbe a rifiutare **proprio** l'atto per cui la strada manuale esiste —
l'eccedenza di un sovra-incasso, che è un credito su una fattura positiva.

**3. `atto_precedente_id` è stato tolto per davvero.** Non c'è nel `-12`: serviva
alla revoca+riemissione, e la catena dei riporti resta leggibile da
`fatture_fondi_fattura.riferimento_fattura_id`.

#### ✅ L'applicazione, e cosa ha detto

Gli oggetti vivi sulla tabella dopo il migrate — verificati sul catalogo, non
dedotti dai file:

| Presidio | Oggetto |
| --- | --- |
| vocabolario `stato` · vocabolario `origine` · `importo <> 0` · `motivo` obbligatorio | `chk_fondi_source_stato`, `chk_fondi_source_origine`, `chk_fondi_source_importo_non_zero`, `chk_fondi_source_motivo_obbligatorio` |
| corrispondenza · cammino degli stati · identità dell'atto | `..._a10_guard_importo_ins_upd`, `..._a10_guard_transizione_upd`, `..._a10_lock_atto_upd` |
| un solo atto automatico vivo | `uq_fondi_source_atto_vivo_automatico` |
| i cinque codici | tutti presenti in `config.codici_errore` con la loro classe |

**⚠️ Ma il migrate verde non è una prova, e qui si vede bene.** La tabella
`fatture_fondi_fattura_source` ha **zero righe**: i cinque presidi nuovi sono
passati senza incontrare un solo dato. Se `motivo` fosse stato reso obbligatorio
su una tabella popolata, il `-14` sarebbe fallito; con la tabella vuota
sarebbe passato **comunque**, e il guasto si sarebbe visto al primo reset vero.
L'unica prova che i presidi funzionano sono i pgTAP.

**⭐ E la prova che l'ordine `-12` → `-13` → `-14` era necessario esisteva già,
senza che nessuno l'avesse chiesta.** `test-fondi-fattura.sql` esercita da mesi
il ramo «reset bloccato da contabile `CHIUSA`» — cioè **l'annullamento
automatico**. Se il `-13` non avesse preceduto il `-14`, quella sezione sarebbe
diventata rossa: il reset avrebbe scritto `ANNULLATO` senza `motivo` e il CHECK
lo avrebbe respinto. Il test era verde **per merito**, ma non lo diceva.

🔵 Da qui l'unica aggiunta di oggi: `test-fondi-fattura.sql` passa da 19 a **20**
asserzioni, e la ventesima verifica che la ragione dell'annullamento stia **sul
dato** (`motivo`) e non solo in `fatture_log`. Non aggiunge copertura — la
aggiungeva già il vincolo — ma **la dichiara**: un verde per sottrazione e un
verde per merito si somigliano troppo perché la differenza resti implicita.

ℹ️ Verificato di conseguenza anche che il **lock di colonna non rompe i percorsi
vivi**: applicazione, reset, sync e annullamento aggiornano `stato`,
`fattura_figlia_id`, `data_assegnazione` e `motivo` — mai le quattro colonne
bloccate. Non è un ragionamento: sono le funzioni che i due pgTAP chiamano
davvero.

#### 🔵 Cosa resta scoperto dopo la Fase B

* il **caso «sorgente non più capiente»** continua a non avere un test runtime
  (serve una riga contabile in fixture) — è il residuo più vecchio;
* l'**`ANNULLATO` automatico** della sync resta: ora almeno **dichiara la sua
  ragione**, ma è ancora uno stato cambiato senza una persona. Si toglie quando
  `pagamenti` avrà il processo rimborsi;
* le **richieste al BE** (§8.3) sono ora **cinque codici errore** da portare in
  `error_policies_generated.py`, non due.

---

### 8.2-quinquies Fase C — **applicata** il 2026-08-15

> ✅ **Applicata e verde.** `migrate` dei 5 changeSet `20260815-19`…`-23`,
> `test-fondi-fattura-governo` **29/29**, `test-fondi-fattura` **20/20** (il
> refactor di generazione e applicazione non sposta niente),
> `test-fattura-utils-critical-termini` **14/14**, `pgtap-baseline.sh vendite`
> **senza regressioni**. Doc `dbzero` rigenerata, tre `manual/` nuovi.
> ⚠️ **Un incidente durante l'applicazione**, per colpa mia: in fondo alla sezione.

| File | Passo | Cosa fa |
| --- | --- | --- |
| `20_code/vendite/20260815-19-create-fn-fondo-fattura-proponibile` | **D-9** | `fn_fondo_fattura_proponibile(sorgente, tipo)`: l'importo che l'automatismo scriverebbe **oggi**, o `NULL` se non farebbe niente |
| `20_code/vendite/20260815-20-update-fn-genera-fondi-consuma-proponibile` | coda **D-9** | La generazione **consuma** la proposta invece di riscrivere l'inviluppo |
| `20_code/vendite/20260815-21-create-fn-check-fondo-fattura-capiente` | serve **D-10** | La regola di capienza estratta in un predicato **puro e `IMMUTABLE`** |
| `20_code/vendite/20260815-22-update-fn-applica-fondi-usa-check-capiente` | coda **D-10** | `fn_applica_fondi_fattura` lo consuma, e legge la capienza **una volta sola** |
| `20_code/vendite/20260815-23-create-vw-fondi-fattura-da-decidere` | **D-10** | L'elenco, `security_invoker=on`, quattro motivi |
| `db/pgtap/vendite/test-fondi-fattura-governo.sql` | **D-18** | da 18 a **29** asserzioni |

#### ⭐ La scoperta della fase: «costruita su» non bastava

Il piano diceva che D-9 andava costruita su `fn_saldo_sorgente_fondo` **«così
proposta e guard non possono divergere»**. È vero e insufficiente: il guard non è
l'unico posto da cui la proposta può divergere. L'**inviluppo** — sorgente
`DEFINITIVA`, dentro la banda, utility attribuita, atto unico, corrispondenza col
documento — viveva nel `WHERE` di `fn_genera_fondi_fattura_source`, e scrivere
D-9 senza toccarlo avrebbe creato la **seconda copia** proprio della regola che
D-9 esiste per condividere.

Il divario avrebbe avuto una forma precisa e silenziosa: un elenco che **propone**
un fondo che il giro notturno non crea, o che **tace** su uno che crea. Nessun
errore, nessun log. Da qui il changeSet `-20`.

**E la stessa cosa, una seconda volta, per la capienza.** Il caso
`NON_PIU_CAPIENTE` dell'elenco è la regola del guard D-3b, negata: due copie
avrebbero detto che un fondo è inapplicabile mentre il giro lo applica. Estratta
in `fn_check_fondo_fattura_capiente` (`-21`) e consumata da entrambi (`-22`).

> ⚠️ **E lì si è visto un difetto che nessuno cercava**: il guard chiamava
> `fn_saldo_sorgente_fondo` **due volte sulla stessa riga** — una per il segno e
> una per il valore assoluto. È una funzione `VOLATILE` che interroga
> `pagamenti`: non è solo il doppio del lavoro, sono **due valutazioni
> indipendenti** che in teoria possono rispondere numeri diversi, accettando
> metà condizione e rifiutando l'altra. Ora si legge una volta, in `LATERAL`.

#### ⚠️ Quattro motivi, e nessuno dei due elenchi è quello del piano

| Motivo | Da dove viene |
| --- | --- |
| `PROPOSTA_SENZA_ATTO` | dal piano |
| `UTILITY_NON_ATTRIBUIBILE` | dal piano |
| `NON_PIU_CAPIENTE` | dal piano |
| **`IMPORTO_NON_CORRISPONDENTE`** | ⭐ **nuovo** |
| ~~`CONFIGURAZIONE_INCOMPLETA`~~ | 🔴 **morto alla nascita** |

🔴 **`CONFIGURAZIONE_INCOMPLETA` non c'è**, e il piano lo aveva previsto: *«ha una
data di scadenza, dopo D-0 quella riga non può più esistere»*. D-0 è stato
applicato **questo pomeriggio** (`20260815-03`): una configurazione a metà non è
più salvabile, quindi il caso è irraggiungibile. *Una riga di elenco che non può
accadere insegna una cosa falsa a chi la legge.*

⭐ **`IMPORTO_NON_CORRISPONDENTE` invece non era previsto.** Quando il residuo
non assomiglia al documento — segno diverso, o più grande in valore assoluto —
la generazione **non fa niente**, ed è giusto: un lotto intero non si ferma per
un caso ordinario. Ma «non fare niente **in silenzio**» è esattamente ciò che
questa vista esiste per rendere visibile. È il caso già disegnato nel manuale
del guard: sorgente da +8, riga contabile da +40, fondo che verrebbe −32 — non
«negativo», **di un'altra fattura**.

#### ⚠️ Tre trappole trovate scrivendo la vista

**1. Il `CHECK` sul vocabolario dei motivi non esiste.** Il piano diceva «sta in
un CHECK sulla colonna della vista»: PostgreSQL **non ha** vincoli `CHECK` sulle
colonne di una vista (`WITH CHECK OPTION` governa le scritture, è un'altra cosa).
Il vocabolario è chiuso **per costruzione** — quattro letterali nei rami della
`UNION`, nessun dato li produce — e il presidio contro un quinto valore aggiunto
di nascosto è **il pgTAP**, che asserisce l'**insieme** dei motivi e non la
presenza dei quattro.

**2. 🔴 Il ramo `NON_PIU_CAPIENTE` parte da una tabella senza RLS.**
`fatture_fondi_fattura_source` non ha politiche: quel ramo è protetto dal **JOIN
`INNER` con `vendite.fatture`**, non da un filtro proprio. `security_invoker=on`
è necessario ma non sufficiente — chi un giorno trasformasse quel join in `LEFT`,
o lo togliesse perché «i dati della fattura non servono», aprirebbe l'elenco a
tutti gli emittenti senza accorgersene. Sta scritto nel `COMMENT` della vista.

**3. ⚠️ L'ordine dei rami della `UNION` non è libero.** Per non scrivere i tipi a
mano, i rami senza valore usano `NULL` nudo e prendono il tipo da chi il valore
ce l'ha; ma PostgreSQL risolve a coppie, da sinistra, e il ramo che **non porta
nessuna colonna propria** deve stare per ultimo. Messo per primo, la `CREATE
VIEW` fallisce — rumorosamente, ed è la ragione per cui la scelta è accettabile.

#### ✅ Chiusa la lacuna più vecchia del cantiere

Il caso **«sorgente non più capiente»** era scritto e mai percorso da Fase A,
perché serviva una **riga contabile postabile** in fixture. Adesso c'è: il pgTAP
crea una testata con `fn_get_or_create_vendite_contabile` e due righe `ABBINATA`,
e da lì escono **due** collaudi che prima non esistevano — il motivo
`NON_PIU_CAPIENTE` dell'elenco **e** il guard D-3b che rifiuta l'applicazione
(test 27).

⚠️ Il test 27 ha un **controllo**: accanto al fondo non capiente ne gira uno
capiente che deve essere applicato. Da solo, «il fondo resta `DISPONIBILE`»
sarebbe passato anche se l'applicazione non avesse fatto **niente**.

#### 🔵 Cosa resta scoperto dopo la Fase C

* nessun **indice** su `vendite.fatture (minimo)`: il pre-filtro della vista è un
  `seq scan` su una tabella che oggi ha 12 righe e domani no. ⚠️ Non è stato
  aggiunto perché su dev **non è misurabile** (zero fatture di minimo), e un
  indice scelto senza una misura è una scommessa;
* la vista non è ancora letta da nessuno: **BE-3** in §8.3;
* restano **Fase D** (l'atto manuale, e aspetta il processo rimborsi in
  `pagamenti`) e **Fase F** (dichiarativa).

#### 🔴 L'incidente: ho droppato oggetti che il migrate aveva appena creato

Va scritto perché la forma dell'errore è generale, e il danno era **peggiore di
quello che sembrava**.

**Cosa è successo.** Le prove del lotto sono state fatte eseguendo il SQL in una
transazione poi annullata. Al termine gli oggetti della Fase C risultavano
**presenti** nel database. Ho concluso che una mia prova avesse lasciato
residui — e li ho tolti, ripristinando anche i corpi pre-Fase C di
`fn_genera_fondi_fattura_source` e `fn_applica_fondi_fattura`.

**Cosa era in realtà.** Il `migrate` di Tid era già girato, **in parallelo al mio
lavoro**:

```text
16:56  scrivo il primo file di prova
16:57  ⭐ il migrate applica -19 … -23   ← non lo sapevo
16:59  eseguo le prove
17:01  🔴 "ripulisco" i residui che residui non erano
```

**Perché era peggio di un DROP.** Le righe di `databasechangelog` restavano —
`EXECUTED`, con la loro data — e gli oggetti no. Un `migrate` successivo **non
li avrebbe ricreati**, perché per Liquibase erano già fatti: il database sarebbe
rimasto senza la Fase C, e il changelog avrebbe giurato il contrario. Il difetto
si sarebbe visto solo al primo test rosso, o al primo consumo della vista.

**Come è stato rimediato.** Ri-applicando **il SQL dei cinque changeSet**, senza
toccare `databasechangelog`: è ciò che Liquibase aveva fatto, quindi lo stato
torna esattamente quello atteso invece di riscrivere la storia. Verificato dopo:
oggetti presenti, `29/29` + `20/20` + `14/14`, `fn_genera` e `fn_applica` di
nuovo sui corpi di Fase C.

> ⭐ **La lezione, e vale oltre questo cantiere.** «I miei oggetti di prova hanno
> lasciato residui» era **un'ipotesi**, non una misura — e c'era un modo
> immediato di verificarla che non ho usato: `databasechangelog.dateexecuted`.
> Su un database condiviso **un DROP non è mai una pulizia**: è la rimozione di
> qualcosa che qualcun altro può avere messo lì un minuto fa. La verifica costa
> una query, il danno costa un disallineamento silenzioso fra codice e
> changelog.

---

### 8.3 La logica BE

> **Regola che vale per tutti i passi**: nessun ricalcolo del fondo in Python,
> nessuna scrittura diretta su `fatture_fondi_fattura_source` da un repository.
> Il BE **chiama** e **legge**. È DB-first, e qui è anche l'unico modo di tenere
> la promessa di F-1: un secondo posto che scrive un importo la annulla.

| | Passo | Perimetro |
| --- | --- | --- |
| **BE-1** | **La firma cambia, e si accorcia**: le due task passano da 6-7 parametri sciolti a **`(lotto_id, tipo_fondo_id)`**. Conseguenza di D-4 | `apps/vendite/db/pipeline_repository.py` |
| **BE-2** | **Atomicità del giro fondi** — difetto esistente, che BE-1 chiude di conseguenza | idem |
| **BE-3** | **L'elenco «fondi da decidere»** — lettura sola su `vendite.vw_fondi_fattura_da_decidere` (scritta, §8.2-quinquies). ⚠️ La vista è `security_invoker`: va letta con la connessione dell'utente, **non** con un ruolo di servizio, o il perimetro emittente salta. Le etichette dei quattro motivi con `labelOrCode` (fail-visible) | repo + service + view |
| **BE-4** | **La porta dell'atto manuale** — D-11 e D-12, chiamate dal processo rimborsi | repo + service + view |
| **BE-5** | **Rigenerare le policy errore** dopo il seed di D-14: `./manage-env.sh genera_error_policies` | comando |

#### 📮 Le tre richieste al BE dalla Fase A *(scritte, non eseguite — perimetro DB)*

| | Richiesta | Perché |
| --- | --- | --- |
| **R-1** | 🔴 **URGENTE — Rigenerare `error_policies_generated.py`** (`./manage-env.sh genera_error_policies`): i codici nuovi a catalogo dal 2026-08-15 sono **cinque**, non due — `E_FONDO_NON_CORRISPONDE_SORGENTE`, `E_FONDO_SOGLIE_INCOMPLETE` (Fase A), `E_FONDO_ATTO_IMMUTABILE`, `E_FONDO_STATO_NON_AMMESSO`, `E_FONDO_MOTIVO_OBBLIGATORIO` (Fase B). Tutti già presenti in `config.codici_errore` sul DB | Senza, il cancello `test_error_codes_db_policy_guardrail` diventa rosso: **ogni codice che il DB può nominare deve avere la sua classe** |
| **R-2** | **Mappare il vincolo `chk_emittenti_fiscali_utilities_soglie_coppia`** su `E_FONDO_SOGLIE_INCOMPLETE` via `map_integrity_error`, con il **campo** dichiarato nella voce. 🔵 Con la Fase B se ne aggiungono due, **non urgenti** perché raggiungibili solo dalla strada manuale che il BE non ha ancora: `chk_fondi_source_motivo_obbligatorio` (`23514`) → `E_FONDO_MOTIVO_OBBLIGATORIO` e `uq_fondi_source_atto_vivo_automatico` (`23505`) | Altrimenti chi configura le soglie a metà legge un messaggio di database invece di *quale* soglia manca. Il canale `error.fields` esiste già |
| **R-3** | **Madre DB per lotto** — `fn_genera_fondi_fattura_lotto(p_lotto_id, p_tipo_fondo_id)` e `fn_applica_fondi_lotto(...)`, con il repository che torna a **una `SELECT` per task** | Oggi `run_genera_fondi_source_lotto_task` / `run_applica_fondi_lotto_task` fanno **N `cursor.execute` in autocommit**: se il quinto fallisce, i primi quattro restano committati. Il DB non può chiuderla da solo — la firma la decide il chiamante |

⚠️ **R-1 e R-2 vanno nello stesso giro del migrate**, R-3 no: è un miglioramento
strutturale che non blocca la Fase A (le firme attuali restano valide).

#### BE-1 + BE-2 — 🔴 Il giro fondi non è una unità atomica, e la chiave lo risolve

`run_genera_fondi_source_lotto_task` e `run_applica_fondi_lotto_task` fanno **N
`cursor.execute` in autocommit**, uno per ogni scope di fattura del lotto. Se il
quinto fallisce, i primi quattro restano committati: il lotto resta a metà, con
dei fondi generati e altri no. È la regola «una azione = una unità atomica»
(api.md §Atomicità), violata dal 2026-02.

⭐ **Con D-4 il difetto non si corregge: sparisce.** Il giro per scope esiste solo
perché la funzione riceve la pseudo-chiave a cinque parametri e va chiamata una
volta per combinazione. Se la chiave la legge il database dalle righe di
`vendite.fatture`, la firma diventa:

```text
vendite.fn_genera_fondi_fattura_lotto(p_lotto_id, p_tipo_fondo_id)
vendite.fn_applica_fondi_lotto(p_lotto_id, p_tipo_fondo_id)
```

e il repository torna a **una `SELECT` sola** per task — atomica per costruzione,
senza `transaction.atomic()` da ricordarsi, e senza il round-trip per scope.

⚠️ Il registry **non cambia**: `pipeline_task_registry_impl` continua a puntare a
`genera_fondi_source_lotto_default` / `applica_fondi_lotto_default`. Cambia il
corpo del metodo, non il cablaggio. ⚠️ E va adeguato
`apps/vendite/tests/services/test_pipeline_step_executor.py`, che oggi nomina le
funzioni con la firma vecchia.

ℹ️ Il ripiego, se la Fase A dovesse uscire prima di D-4: `with transaction.atomic()`
attorno al loop. Chiude l'atomicità e lascia in piedi il round-trip.

#### BE-3 — L'elenco

```text
GET /api/v1/vendite/fondi-fattura/da-decidere/?motivo=&page=&page_size=&order_by=&order_dir=
```

* **view**: `DomainAPIView`, `area_funzionale = "vendite"`, `is_search_endpoint = True`,
  `@extend_schema` con `inline_serializer`;
* **service**: `validate_pagination` + `validate_enum_param` sul filtro `motivo`
  (whitelist ordinata = i quattro motivi di D-10);
* **repository**: `fetch_paged_with_total` (o `query_paged_view` se si vuole la
  pagina **effettiva** nell'envelope), `sql_order_direction` +
  `sql_tiebreak_direction` per l'`ORDER BY`, tiebreak su `id`;
* **scope**: la RLS filtra da sé grazie a `security_invoker` (D-10); il filtro
  applicativo `get_emittenti_sr_ids` resta come **defense-in-depth**, com'è la
  convenzione del progetto.

⭐ **Nessun building block nuovo**: sono tutti già a catalogo. E ⚠️ **nessuna
capability per riga** — le liste non chiamano `fn_available_actions_*` riga per
riga; il gate lo fa il FE sui codici che la vista porta già in riga
(`motivo_codice`, `azione_suggerita`).

#### BE-4 — I due comandi

```text
POST /api/v1/vendite/fondi-fattura/                 → crea atto manuale
POST /api/v1/vendite/fondi-fattura/<id>/annulla/    → annulla con motivo
```

* `handle_post_json` con `require_idempotency_key=True` (modificano stato);
* `post_permission = "governa_fondo_fattura"` (D-13);
* **una sola `SELECT fn_...()`** per comando → atomico per costruzione, **niente**
  `transaction.atomic()`;
* traduzione errori con `translate_db_errors` / `raise_from_database_error`: dal
  2026-08-05 il codice viaggia in `diag.constraint_name` su `P0001`, quindi basta
  che le funzioni DB usino `script.fn_log_and_raise_error` — che è già la regola.

⚠️ **Dove vive il codice, e perché non un file nuovo.** Tre endpoint (una lista e
due comandi) **non** fanno un sottodominio: stanno in `vendite_service.py` e
`vendite_repository.py`. La convenzione di AGENTS.md è esplicita — un file
`<sottodominio>_*` si crea solo quando c'è logica orchestrata autonoma (runner,
executor, saga), non per tre metodi.

#### E il frontend — fuori dalla richiesta, ma il contratto lo prevede

Una riga per non lasciare il contratto monco: l'elenco è una lista sola dentro il
dominio vendite (`useListaConfigurabilePage` + `ListaConfigurabile`), con due
azioni di riga gated su `governa_fondo_fattura` e i motivi decodificati via
`labelOrCode`. Non c'è niente da inventare, e **non fa parte di questo piano**.

---

### 8.4 Ordine, dipendenze e il vincolo esterno

```text
Fase A  ─── indipendente, si applica subito ──────────────┐
   │                                                       │
   ├─→ Fase B (registro)  ─→  Fase C (proposta + elenco)  ─→  Fase D (atto manuale)
   │
Fase E  ─── in qualunque momento, conviene con A
Fase F  ─── dichiarativa: si scrive nel brief incassi
```

| Dipendenza | Perché |
| --- | --- |
| **D-0 per primo** | finché una configurazione a metà spalanca il meccanismo, tutto il resto presidia un cancello con il muro aperto accanto |
| D-1 **con** D-3 | D-1 da solo lascia scoperto un fondo non più dovuto, che verrebbe applicato lo stesso (§8.2 Fase A) |
| D-4 **prima o insieme** a BE-1 | la firma delle funzioni cambia: DB e repository nello stesso lotto, o la pipeline si rompe |
| Fase B **dopo** Fase A | il CHECK sul vocabolario di `stato` viene prima del guard che lo presidia |
| Fase C **dopo** Fase B | l'elenco distingue gli **atti** dalle **proposte**: senza `origine` non sa dirlo |
| Fase D **dopo** Fase C | e comunque **dopo** che `pagamenti` ha un processo rimborsi da cui chiamarla: costruire la porta prima della stanza è lecito, aprirla al pubblico no |

🔴 **Il vincolo esterno, ed è l'unico che ha una scadenza.** La Fase A deve essere
applicata **prima del primo scrittore di righe contabili** — la slice 1 del
cantiere incassi, l'import del flusso bancario (D6), o una correzione manuale,
quello che arriva prima (§8.0-a). Se è la slice 1, la Fase A è dentro di lei e
**non si fa due volte**.

---

### 8.5 Le verifiche

**pgTAP** — file nuovo `db/pgtap/vendite/test-fondi-fattura-governo.sql`, più
l'adeguamento dei due esistenti.

| | Cosa verifica |
| --- | --- |
| 1 | ⛔ una sola soglia valorizzata **non si salva** (D-0) |
| 2 | soglie assenti ⇒ **nessun fondo generato** (meccanismo spento) |
| 3 | ⭐ **una fattura fra `soglia_min` e 0 genera un fondo NEGATIVO** — è il capo inferiore della banda, non un difetto |
| 4 | una fattura fuori banda (sopra il massimo, sotto il minimo) **non genera niente** |
| 5 | sorgente **non `DEFINITIVA`** (DRAFT, EMESSA, **ANNULLATA**) ⇒ nessun fondo (D-1) |
| 6 | un secondo giro **non riscrive** l'importo di un fondo già creato (D-1 + D-6) |
| 7 | un fondo di segno opposto o più grande del totale della sorgente è **rifiutato** su `origine = 'AUTOMATICA'` e **ammesso** su `'MANUALE'` (D-3a, D-5) |
| 8 | `fn_applica_fondi_fattura` **non assegna** un fondo la cui sorgente non è più capiente (D-3b) |
| 9 | il fondo **non passa** a una figlia che differisce anche per **un solo** elemento dei nove (D-4) — almeno `utility`, `termine_pagamento`, `reseller` |
| 10 | i CHECK rifiutano importo zero e stato fuori vocabolario (D-2) |
| 11 | le transizioni fuori matrice sono rifiutate (D-7) |
| 12 | l'indice parziale rifiuta due atti automatici vivi sulla stessa sorgente (D-8) |
| 13 | `vw_fondi_fattura_da_decidere` **non mostra** i fondi di un altro emittente (D-10, RLS) |

⚠️ **Trappole da non ripagare**, tutte già pagate altrove nel progetto:

* **il preambolo è obbligatorio** — `BEGIN;`, riga di contesto operatore,
  `SET CONSTRAINTS ALL IMMEDIATE` **subito dopo**. Senza, il file diventa verde
  per sottrazione;
* **`throws_ok` sempre con lo SQLSTATE** (`'P0001'` per gli errori di dominio):
  senza, accetta anche il crash del guard che doveva verificare. ⚠️ E i trigger
  BEFORE ROW girano **prima** dei CHECK: il test 10 rischia di collaudare il guard
  di D-7 credendo di collaudare un CHECK — asserire il **codice**, non il fatto
  che sollevi;
* **niente `LIMIT 1` senza `ORDER BY`** nelle fixture;
* 🔴 **il fondo NON corrispondente va attraversato dal percorso reale**, non
  fabbricato. Una riga inserita a mano nella source *conferma* un ramo che nessuno
  percorre. Il percorso vero passa dal **secondo termine** della bilancia
  (§8.0-a): una riga contabile `ABBINATA` più grande del residuo porta il target
  sotto zero **senza bisogno di movimenti**, ed è creabile oggi. È così che vanno
  costruiti i test 7 e 8;
* ⚠️ **e non confondere quel caso col fondo negativo legittimo** (test 3), che
  nasce da una fattura a credito dentro la banda. Sono due fondi negativi con due
  cause opposte: uno è il meccanismo che funziona, l'altro è il difetto. Un test
  che asserisse solo «il fondo è negativo» non distingue fra i due;
* **misurare con `ON_ERROR_STOP=1`** e confrontare con
  `scripts/pgtap-baseline.sh vendite` prima di attribuire un rosso a questo
  lavoro.

**Non-pgTAP:**

* `test_transaction_atomicity_guardrail` deve restare verde dopo BE-2;
* `./manage-test.sh apps.vendite.tests -v 2` dopo BE-3/BE-4;
* il presidio dei riferimenti morti gira **dopo** `manage.py migrate`: il `DROP`
  di D-15 e il taglio del pgTAP nello stesso lotto.

---

### 8.6 Cosa il piano **non** fa, e perché

| | Perché |
| --- | --- |
| Nessun automatismo che «sistema» i fondi | è la regola pratica di §5.2: l'elenco **presenta**, non sana. Un automatismo correttivo riaprirebbe la rincorsa che §4 ha chiuso |
| Nessun `ANNULLATO` come effetto di un pagamento | se non ci si fida di un automatismo a **creare** un fondo, tanto meno a **cancellarlo** |
| 🔴 **Nessun limite `> 0` sull'importo**, né CHECK né `WHERE` | **il fondo negativo è metà del meccanismo**: il capo inferiore della banda (`−500`) esiste per riportare avanti i **crediti**. Il limite `> 0` — scritto sia qui sia nel cantiere incassi fino al 2026-08-15 — avrebbe spento quella metà. Si controlla la **corrispondenza col documento**, non il segno |
| Nessuna quadratura per **fattura** | l'intervallo `[0, totale_a_pagare]` si inverte sulle fatture a credito: è una porta chiusa travestita da controllo. Trappola già scritta nel brief incassi, e qui il caso non è di bordo — è ordinario |
| Nessun elenco delle eccedenze in `vendite` | il sovra-incasso è del **processo rimborsi**, in `pagamenti`, che se le va a cercare. Due elenchi sullo stesso fatto divergono al primo cambio |
| Nessuna RLS su `fatture_fondi_fattura_source` | il perimetro passa dalla fattura, che ce l'ha. Una RLS in più su una tabella satellite è un secondo posto dove sbagliare — e `security_invoker` sulla vista (D-10) fa già il lavoro |
| Nessun tocco a `pagamenti` | il posting, la quadratura, il rimborso e la compensazione sono dell'altro cantiere. Qui si dichiara il confine (Fase F) e si costruisce **una porta** (Fase D), non si attraversa |

---

## 9. Registro

| Data | Cosa |
| --- | --- |
| 2026-08-15 (notte, 8) | ✅ **Fase C APPLICATA e verde.** Migrate dei 5 changeSet `20260815-19`…`-23`, `test-fondi-fattura-governo` **29/29**, `test-fondi-fattura` **20/20**, `test-fattura-utils-critical-termini` **14/14**, baseline `vendite` senza regressioni. Doc `dbzero` rigenerata e scritti i tre `manual/` nuovi (`fn_fondo_fattura_proponibile`, `fn_check_fondo_fattura_capiente`, `vw_fondi_fattura_da_decidere`), più la riscrittura al presente di `fn_genera_fondi_fattura_source` e `fn_applica_fondi_fattura` — la prima dichiarava ancora il difetto della utility come «di oggi», la seconda i due presidi come «previsti». 🔴 **Un incidente, mio**: il migrate di Tid è girato **in parallelo** al mio lavoro (16:57) e io alle 17:01 ho droppato gli oggetti credendoli residui di una mia prova, ripristinando anche i corpi pre-Fase C di `fn_genera` e `fn_applica`. ⚠️ **Il danno era peggiore di un DROP**: le righe di `databasechangelog` restavano `EXECUTED`, quindi un migrate successivo **non li avrebbe ricreati** — database senza Fase C e changelog che giura il contrario. Rimediato ri-applicando il SQL dei cinque changeSet senza toccare `databasechangelog`, e verificato. ⭐ La lezione in §8.2-quinquies: *«la mia prova ha lasciato residui» è un'ipotesi, non una misura — e `dateexecuted` costa una query. Su un DB condiviso un DROP non è mai una pulizia* |
| 2026-08-15 (notte, 7) | ⭐ **Scritta la Fase C (D-9, D-10)** — cinque changeSet `20260815-19`…`-23`, pgTAP del governo da 18 a **29** asserzioni. ⚠️ **Da applicare**, ma **provata**: eseguita in transazione annullata dà 29/29, e `test-fondi-fattura` resta 20/20 col refactor. ⭐ **La scoperta della fase**: «costruita su `fn_saldo_sorgente_fondo`» non bastava — l'**inviluppo** (definitiva, banda, utility, atto unico, corrispondenza) viveva nel `WHERE` della generazione, e D-9 da sola ne avrebbe creato la seconda copia: un elenco che propone ciò che il giro non crea, senza nessun errore. Da qui il `-20`. **La stessa cosa una seconda volta per la capienza** (`-21` + `-22`), e lì è saltato fuori che il guard chiamava `fn_saldo_sorgente_fondo` **due volte per riga** — una funzione VOLATILE valutata due volte può accettare metà condizione e rifiutare l'altra. 🔴 **`CONFIGURAZIONE_INCOMPLETA` è morto alla nascita**: D-0, applicato oggi pomeriggio, rende quel caso irraggiungibile — e il piano lo aveva previsto. ⭐ **Motivo nuovo `IMPORTO_NON_CORRISPONDENTE`**: dove l'automatismo tace in silenzio, l'elenco parla. ⚠️ Tre trappole: il `CHECK` sul vocabolario di una vista **non esiste in PostgreSQL** (il presidio è il pgTAP che asserisce l'insieme dei motivi); il ramo `NON_PIU_CAPIENTE` parte da una tabella **senza RLS** ed è protetto dal JOIN, non dalla vista; l'**ordine dei rami** della UNION non è libero. ✅ **Chiusa la lacuna più vecchia**: la fixture con riga contabile esiste, e il guard di capienza D-3b ha finalmente un test runtime — con un controllo accanto, perché da solo sarebbe stato verde anche se l'applicazione non avesse fatto niente. ⚠️ Correzione di Tid in corso d'opera: le firme erano tornate ai tipi espliciti, `%TYPE` ripristinato su parametri e `DECLARE` |
| 2026-08-15 (notte, 6) | ✅ **Coda della Fase E e Fase B APPLICATE e verdi.** Migrate dei 9 changeSet `20260815-10`…`-18`, `test-fondi-fattura-governo` **18/18**, `test-fondi-fattura` **20/20**, `test-fattura-utils-critical-termini` **14/14**, `pgtap-baseline.sh vendite` **senza regressioni**, guardrail statici verdi, doc `dbzero` rigenerata. Verificati sul catalogo gli **otto presidi vivi** sulla tabella e i **cinque codici** in `config.codici_errore`. ⚠️ **Il migrate verde non è una prova, e qui si vede**: `fatture_fondi_fattura_source` ha **zero righe**, quindi i cinque presidi nuovi sono passati senza incontrare un dato — su una tabella popolata il `-14` sarebbe fallito. L'unica prova sono i pgTAP. ⭐ **E la prova che l'ordine `-12` → `-13` → `-14` era necessario esisteva già, senza che nessuno l'avesse chiesta**: `test-fondi-fattura.sql` esercita da mesi il ramo «reset bloccato da contabile CHIUSA», cioè l'annullamento automatico — senza il `-13`, il `-14` avrebbe reso rossa quella sezione. Era verde **per merito** ma non lo diceva, e da qui l'unica aggiunta di oggi: **ventesima asserzione**, la ragione dell'annullamento verificata **sul dato** (`motivo`) e non solo in `fatture_log`. ℹ️ Verificato di conseguenza che il **lock di colonna non rompe i percorsi vivi** — applicazione, reset, sync e annullamento non toccano mai le quattro colonne bloccate, e non è un ragionamento: sono le funzioni che i pgTAP chiamano davvero. 📮 **R-1 al BE ora vale cinque codici** e non due |
| 2026-08-15 (notte, 5) | ⭐ **Scritte la coda della Fase E (D-15, D-16) e la Fase B (D-5…D-8)** — 9 changeSet `20260815-10`…`-18`, tre codici errore, pgTAP da 12 a **18** asserzioni. ⚠️ **Da applicare**: nessun migrate, nessun test su questo lotto. Tre cose scoperte scrivendo: **(1)** `motivo` obbligatorio impone di toccare **due funzioni che il piano non nominava** — un fondo passa ad `ANNULLATO` in due punti automatici e la ragione, dove esisteva, viveva in un **messaggio di `fatture_log`** invece che sul dato; da qui l'ordine obbligato `-12` → `-13` → `-14`, perché il vincolo prima degli scrittori passerebbe sulla tabella vuota di oggi e fallirebbe al primo reset vero. **(2)** 🔴 **`origine` senza il changeSet `-18` non governa niente**: il piano diceva che il guard di corrispondenza «si restringerà ad AUTOMATICA» ma non lo elencava fra i passi, e senza quel passo la colonna esisterebbe mentre il guard continua a rifiutare **proprio** l'atto per cui la strada manuale esiste. **(3)** `atto_precedente_id` è stato tolto per davvero: la catena dei riporti si legge già da `riferimento_fattura_id` |
| 2026-08-15 (notte, 4) | ✅ **Fase A APPLICATA e verde.** Migrate dei 7 changeSet, `test-fondi-fattura-governo` **12/12**, `test-fondi-fattura` **19/19**, `pgtap-baseline.sh vendite` **senza regressioni** (24 rossi, tutti noti), guardrail statici verdi, doc `dbzero` rigenerata. Scritti i due `manual/` delle funzioni nuove (`fn_saldo_sorgente_fondo`, `trgfn_fondi_source_guard_importo`) e agganciati alle pagine auto-gen. 🔴 **La prima corsa era rossa, e il difetto era del test**: chiedevo `23514` sul CHECK `importo <> 0` e ottenevo `P0001` — perché i trigger BEFORE ROW girano **prima** dei CHECK, quindi su una sorgente da 100 lo zero lo intercetta il guard di corrispondenza (`sign(0)` non è il segno di nessun totale non nullo) e il vincolo non entra mai in gioco. È **la trappola che avevo appena scritto in §8.5**. Corretto con una quinta fixture a **totale zero**, l'unico terreno da cui il CHECK è raggiungibile — e la lezione, in §8.2-ter, non è «leggere meglio»: *un test che nomina il MECCANISMO invece del COMPORTAMENTO verifica la propria ipotesi, non il sistema*. 🔵 Resta scoperto il caso «sorgente non più capiente» (serve una riga contabile in fixture) e restano da fare le tre richieste al BE — **R-1 è urgente**: senza rigenerare `error_policies_generated.py` i due codici nuovi non hanno classe lato backend |
| 2026-08-15 (notte, 3) | ⭐ **Fase A scritta** (*«puoi procedere con lo sviluppo»*, con la conferma che le due righe di `emittenti_fiscali_utilities` hanno entrambe le soglie vuote e quindi il CHECK non fallisce all'apply). Sette changeSet `20260815-03`…`-09`, due codici errore in append ai CSV, un pgTAP nuovo da 12 asserzioni, e la **fixture del pgTAP esistente adeguata** — la sua fattura sorgente nasceva senza stato e senza utility, e con i nuovi filtri non avrebbe più generato niente. Dettaglio in **§8.2-bis**. ⚠️ **Nulla è stato applicato né eseguito**: né migrate né test né commit. Tre scelte da conoscere: le **firme non cambiano** (la chiave a nove elementi si chiude dentro `fn_applica_fondi_fattura`, che ha già entrambe le fatture — così il perimetro DB regge senza toccare `backend/`); i cinque parametri di scope passano da filtro sulla *source* a verifica sulla *figlia* (sulla source potevano far saltare un fondo **in silenzio**); e la preCondition sul codice errore è stata tolta dal changeSet -06 perché `20_code` gira **prima** di `80_data`. 🔵 Due assenze dichiarate: manca il test runtime del caso «sorgente non più capiente» (serve una riga contabile in fixture), e l'`ANNULLATO` automatico dentro `fn_sync_contabili_fondo_fattura` resta — è su fondi **già assegnati**, e toglierlo senza il processo rimborsi scoprirebbe il doppio conteggio |
| 2026-08-15 (notte, 2) | ✅ **Bonifica documentale eseguita** (*«procedi alla correzione di tutti»*). **11 documenti** toccati: i tre sbagliati oggi riscritti (il manuale della generazione ha ora la **banda** e la dichiarazione del perimetro corretta; la sezione «Analisi fondi fattura (WIP)» di `fatturazione-attivita-progetto` è **marcata superata** con la tabella di ciò che è stato deciso diversamente; la guida dei pagamenti ha una sezione nuova sulle **due soglie** in linguaggio non tecnico, con lo schema della fascia e l'avvertenza sulla configurazione a metà). I quattro 🟠 **annotati, non riscritti**: la descrizione di oggi resta, accanto c'è «oggi → diventerà, con quale passo». Aggiunte la nota **non-cassa** su `centri_riscossione` (manual + guida) e l'avvertenza sul **fail-open** delle soglie su `fn_ricalcola_totali_fattura`, che è la pagina dove la banda era già detta bene. Corretta la motivazione «è config» su `fatture_fondi_fattura_source` in `analisi-attivazione-rls-operatori` (la conclusione regge, la ragione no) e la riga «non urgente» della mappa concentrica. ⚠️ **Difetto collaterale trovato e sanato**: in due manual la convenzione ASCII degli accenti (`e\``) produceva **code span accidentali** — due «e\`» sulla stessa riga si accoppiano e il testo in mezzo viene renderizzato come codice. Allineati agli accenti veri, come i manual recenti |
| 2026-08-15 (notte) | 🔍 **Ricognizione documentale su richiesta di Tid** (tutta `docs/` + il codice): inventario in **D-17**. **Tre documenti sono sbagliati OGGI**, non domani — il manuale di `fn_genera_fondi_fattura_source` **dichiara un filtro su `utility` che il codice non applica**; `fatturazione-attivita-progetto.md` parcheggia in `work-done/` un design mai eseguito con una policy `riapribile` che è **un automatismo che scrive in reazione a un pagamento**; la guida dei pagamenti racconta **solo il capo superiore** della banda. Altri quattro lo diventeranno con l'implementazione, ognuno legato al suo passo. ⭐ E due avevano ragione: `fn_ricalcola_totali_fattura` è **l'unico posto dove la banda è detta bene**, e `tipi_fondi_fattura` dice «addebiti/**accrediti**» dall'origine — il tampone `> 0` contraddiceva il **catalogo**, non solo il dominio. Lezione: *chi documenta un consumatore non documenta la regola che lo governa* — la banda stava nella funzione che **scrive** `minimo`, non in quelle che leggono il flag. Nel codice BE/FE non c'è **nessuna** descrizione della logica: due sole occorrenze, entrambe etichette |
| 2026-08-15 (sera) | 🔴 **Piano riscritto dopo le decisioni di Tid, e due parti erano sbagliate.** **(1)** Il limite `> 0` sulla generazione — scritto sia qui sia nel cantiere incassi — **spegneva metà del meccanismo**: le due soglie di `emittenti_fiscali_utilities` sono i **due capi di una banda che contiene lo zero** (esempio: `−500 / +10`), e il capo inferiore esiste **apposta** per riportare avanti i *crediti*. Il controllo giusto non è sul segno ma sulla **corrispondenza col documento** (stesso segno del totale della sorgente, non superiore in valore assoluto), e sta in un **guard trigger** perché un CHECK non può leggere `vendite.fatture`. Cadono con esso il CHECK «automatico ⇒ positivo», la revoca+riemissione (D-8 vecchio) e `atto_precedente_id`. **(2)** 🔴 «Soglia non impostata = meccanismo spento» **vale solo a metà**: manca il massimo e la condizione diventa vera per tutti — una configurazione incompleta **spalanca** invece di chiudere. Nuovo passo **D-0** (CHECK «entrambe o nessuna»), su decisione di Tid. ⭐ **Trovata la chiave che mancava**: `fn_build_fattura_key` ha **nove** elementi, il fondo ne usa 4-5 — mancano reseller, registro, termine e modalità di pagamento — e il progetto **ha già corretto lo stesso difetto un anello prima** (*«utility_id, che mancava da sempre… chiave e lookup disallineati si annullano a vicenda»*). Il confronto passa a **riga contro riga**, e con esso spariscono il ribaltamento dell'utility e le N chiamate in autocommit. ⭐ Chiarito che **BASE è una utility** (id 5) e `billing_account.utility_id` è NOT NULL: non esiste il caso «fattura senza utility». ⭐ Verificato che **da DEFINITIVA non si torna indietro** (unica transizione: → INVIATA), quindi è la soglia di congelamento giusta — e che il fondo è **l'unico satellite della fattura non congelato**: `trgfn_fattura_satellite_guard_congelamento` è montato su scadenze e indirizzi, non sui fondi. ✅ Confermato il perimetro del **processo rimborsi** (in `pagamenti`, tre uscite, passaggio **passivo**): l'elenco delle eccedenze esce da `vendite`, che espone **una porta** (Fase D) e non un secondo cruscotto |
| 2026-08-15 | ⭐ **Aggiunto il piano di sviluppo (§8)** su richiesta di Tid: passi DB prima, logica BE poi. Risolte le cinque domande di §6 (§8.1): il fondo diventa un **atto** con importo congelato e lock strutturale, l'automatismo crea una volta sola dentro l'inviluppo `> 0`, l'aggiornamento sparisce e diventa **revoca + riemissione**; `fn_sync_pagamento_fondo_fattura` si **ritira**; due CHECK e nessuno `> 0` secco, perché l'accredito riportato è la terza strada di F-3 e passa da questa stessa tabella. 🔴 **Corrette due misure di §3** (§8.0): la seconda serratura non è «nessun movimento» ma l'**assenza di scrittori di righe contabili** — il target si genera sulla *differenza* dei due saldi, e il secondo termine non dipende dai movimenti; e `minimo` non è una configurazione ma un calcolo che **si richiude su sé stesso** (`totale_a_pagare` contiene i fondi già applicati). 🔴 **Difetto nuovo misurato**: la generazione non filtra su `utility_id` ma lo scrive, e su un BA con due utility **l'attribuzione del fondo si ribalta a ogni giro** (D-4). Altri due rilievi: il giro fondi lato BE è **N scritture in autocommit** (BE-2), e con un posting atomico la bilancia di B-1 **regge da sé** (Fase F) |
| 2026-08-09 | Stesura, estraendo l'analisi dal cantiere incassi su indicazione di Tid — «meglio un brief apposito per non dimenticare, dato che l'analisi è già approfondita». Misurati: l'unico filtro `<> 0`, l'assenza di CHECK sull'importo, i due task `attivo = true`, le due serrature (0 fatture a minimo / nessun movimento), e il guscio vuoto `fn_sync_pagamento_fondo_fattura` che nessuno chiama |
