# Brief DB — archiviare una riga di coda senza toccarne lo stato

> **Chi scrive:** BE/FE (`dev/backend-tid`), 2026-09-03.
> **A chi:** team DB.
> **Da dove nasce:** richiesta di Tid sulle due liste «Code di lavoro»
> (`CodaLavoriTab`, `CodaStampaTab`): poter togliere righe dall'elenco **senza**
> cancellarle né annullarle, perché i conteggi del pannello **Esiti
> fatturazione** devono restare fermi.
> **Decisioni di Tid (2026-09-03):** si archiviano **solo righe in stato
> terminale**; l'archiviazione ha un **interruttore «mostra archiviate» + il
> conteggio**; vale **per tutti**, non per operatore.
> **Stato:** 🟢 **DB APPLICATO il 2026-09-04** (sei changeSet `EXECUTED`, seed
> caricati, pgTAP verdi, doc rigenerata). Le tre decisioni aperte sono chiuse.
> 🟢 **BE e FE scritti il 2026-09-04**: il debito del §11.4 è chiuso — il
> registro delle attività è la **PARTE BE/FE** in fondo (§12).
> ✅ **E il migrate è passato**: verificato il 2026-09-07, le righe 713/714 di
> `ui.lista_colonna` sono `attivo = t`. Con quello il §14.1 è chiuso, e **lato DB
> non resta niente** — vedi §15.
> **La risposta del team DB — analisi, correzioni, piano e registro delle
> attività — è la PARTE DB in fondo a questo documento.**

---

## 1. Il fatto, verificato

Nessuna delle due code ha oggi un flag di visibilità.

| Tabella (lista) | Stati ammessi | Flag | Verbo «annulla» |
| --- | --- | --- | --- |
| `dbops.coda_lavori` | PENDING · IN_CORSO · FATTO · ERRORE · ANNULLATO | ❌ | sì, **solo** su PENDING |
| `vendite.fatture_stampa_coda` | PENDING · IN_CORSO · FATTO · ERRORE | ❌ | **non esiste** |

⚠️ **E le due strade che l'operatore ha oggi spostano i numeri**, che è la
ragione della richiesta. I conteggi del pannello Esiti vengono da
`VenditePipelineRepository.count_coda_stampa_per_stato` — un `GROUP BY c.stato`
su `fatture_stampa_coda`, ristretto al mese via `lotto_id`, **senza alcun filtro
di visibilità**:

* un `DELETE` fa **calare** il numero;
* un ANNULLA — che sulla coda stampa non esiste, ma che sarebbe la mossa ovvia
  da aggiungere — **sposterebbe** la riga da FATTO/ERRORE a ANNULLATO, cioè
  cambierebbe la ripartizione che l'operatore sta leggendo.

⇒ Serve un flag che la **lista** legge e che **nessun altro** legge.

---

## 2. La richiesta

### 2.1 Due colonne, simmetriche

```sql
ALTER TABLE dbops.coda_lavori
  ADD COLUMN archiviato boolean NOT NULL DEFAULT false;

ALTER TABLE vendite.fatture_stampa_coda
  ADD COLUMN archiviato boolean NOT NULL DEFAULT false;
```

⭐ **Simmetriche dal primo giorno**, non «prima una poi l'altra»: le due code
sono gemelle, hanno lo stesso scheletro di lista (`CodaTabBase`) e la stessa
domanda. Un'asimmetria qui si paga al primo che tocca solo una delle due.

### 2.2 ⛔ Sul NOME — perché non `disabilitato` né `attivo`

In `vendite` la stessa idea esiste già e si chiama **`disabilitato`**
(`fatturazione_lotti_log`, `fatture_log`), con la disciplina già rodata
(nascoste di default + `ritirate_count` che dichiara quante). Riusare quel nome
sarebbe la scelta di default, e **qui è quella sbagliata**:

* là le righe sono **segnali passivi** — `disabilitato` significa «ritirato,
  non lo si mostra più», e non c'è nient'altro che quella riga possa fare;
* qui le righe sono **lavoro** — `disabilitato` su una riga di coda si legge
  come *«non eseguirlo»*, che è l'opposto di ciò che deve fare. Stesso problema
  con `attivo`, che per giunta collide con la famiglia
  `trgfn_prevent_deactivate_if_children`.

**`archiviato`** dice *messo via dall'elenco*, non *spento*. ⚠️ Il nome qui non è
cosmetica: è l'unica cosa che impedisce al prossimo che legge la colonna di
aggiungerla al `WHERE` del claim «per coerenza».

### 2.3 Il guard — solo stati terminali

Trigger `BEFORE UPDATE OF archiviato`, fase `_a10_` (guard):

| Tabella | Terminali (archiviabili) | Vivi (rifiutati) |
| --- | --- | --- |
| `dbops.coda_lavori` | FATTO · ERRORE · ANNULLATO | PENDING · IN_CORSO |
| `vendite.fatture_stampa_coda` | FATTO · ERRORE | PENDING · IN_CORSO |

Nomi proposti (convenzione `linee-guida-trigger`):
`trg_coda_lavori_a10_guard_archiviazione_upd` /
`trg_fatture_stampa_coda_a10_guard_archiviazione_upd`.

**Perché il perimetro è questo, e non è prudenza.** Il badge in topbar conta i
«vivi» (`PENDING|IN_CORSO`, sede unica `STATI_CODA_VIVI`). Archiviare una riga
viva la lascerebbe **nel conteggio** e fuori dall'**elenco**: l'operatore legge
«2 lavori vivi» e apre una lista dove non c'è niente, senza nessun modo di
arrivarci per rimetterla a posto. Sulle terminali il problema non esiste **per
costruzione**: non sono vive, non sono reclamabili, e l'indice unico parziale
`uq_fatture_stampa_coda_vivo` non le vede — quindi ri-accodamento e ristampa
restano intatti.

### 2.4 ⭐ Il pezzo che si scopre solo guardando i verbi vicini: **requeue**

`CodaLavoriRepository.requeue` riporta una riga da IN_CORSO/ERRORE a **PENDING**.
Una riga **archiviata e poi rimessa in coda** sarebbe viva e invisibile — cioè
esattamente il difetto che il §2.3 evita, rientrato dalla porta di servizio.

⇒ Lo stesso trigger, su `UPDATE OF stato`: **se il nuovo stato non è terminale,
`archiviato` torna `false`**. Non un rifiuto — una riga che torna al lavoro deve
tornare nell'elenco, ed è la regola «chi alza la bandiera la abbassa» applicata
qui.

⚠️ È la ragione per cui questo è un brief e non una riga di richiesta: le due
colonne da sole passerebbero ogni verifica e lascerebbero il buco aperto.

### 2.5 Quando l'archiviazione è avvenuta

```sql
ADD COLUMN archiviato_il timestamptz NULL
```

⛔ **`data_update` non è un sostituto affidabile**, e sembra esserlo: è l'istante
dell'**ultimo** update qualunque esso sia. Oggi sulle terminali nessuno scrive
più, quindi coinciderebbe — ma è una coincidenza che regge finché nessuno tocca
il drainer, non una garanzia. Serve alla lista «mostra archiviate» per dire
*quando* è stata messa via.

⚠️ Chi l'ha archiviata resta su `user_update`: lì la coincidenza regge davvero,
perché la scrittura è la stessa.

### 2.6 Codice errore

Il guard del §2.3 deve sollevare un codice **registrato a catalogo con la sua
classe** (`config.codici_errore`), non un `E_GENERICO`:

| Codice | Classe | Perché |
| --- | --- | --- |
| `E_CODA_ARCHIVIAZIONE_NON_AMMESSA` | `CONFLITTO_STATO` (409) | non è un dato sbagliato: è la riga che in questo momento è ancora viva |

Con la sua `soluzione` a catalogo («attendi che il lavoro finisca, oppure
annullalo prima di archiviarlo»): è la frase che arriva all'operatore come
`hint`. Il messaggio nomina **lo stato**, non il nome della colonna.

⚠️ Lato BE, dopo il seed: `./manage-env.sh genera_error_policies` più la voce in
`error_messages_fallback.py`. Lo facciamo noi, ma solo dopo il vostro apply.

---

## 3. Chi legge il flag — e chi NON deve leggerlo

⛔ **Un solo lettore: la lista.** Se lo leggessero anche claim, drainer o reaper,
archiviare diventerebbe **un annullamento silenzioso** — cioè peggio della
cancellazione che questa richiesta esiste per evitare.

| Lettore | Legge `archiviato`? |
| --- | --- |
| `elenca` / `elenca_coda_stampa` (le due liste) | ✅ sì, `= false` di default |
| `count_coda_stampa_per_stato` (**Esiti fatturazione**) | ⛔ **NO** — è il punto della richiesta |
| `count_per_stato` / `get_stato` (badge topbar) | ⛔ NO (e per il §2.3 è indifferente) |
| claim · `reap_stale` · `mark_done` · `mark_error` · drainer | ⛔ **NO, mai** |
| `uq_fatture_stampa_coda_vivo` | ⛔ NO (parziale su PENDING/IN_CORSO) |

⚠️ **Nessun indice nuovo per ora**: entrambe le liste filtrano già per `stato` e
per intervallo di date, e l'archiviazione si somma a quelli. Lo si valuta se e
quando le code cresceranno — un indice adesso sarebbe una previsione, non una
misura.

---

## 4. Quello che resta a noi (dopo il vostro apply)

* filtro `archiviato = false` di default nelle due `elenca`, con parametro per
  chiederle;
* **`archiviate_count`** nell'envelope della lista: senza quel numero «coda
  pulita» e «tre righe messe via» si leggono uguali — è la stessa lezione di
  `ritirate_count` sul giornale della fattura;
* verbo «Archivia» / «Ripristina» nel kebab di riga (`RowActionsMenu`), gated
  come gli altri due verbi di coda (`code_manage`), con `disabled` + `tooltip`
  che porta il motivo quando la riga è ancora viva;
* interruttore «mostra archiviate» nella toolbar di `CodaTabBase` — una sola
  volta, le due schede lo ereditano.

---

## 5. ⚠️ Nota a margine, fuori richiesta ma di vostra competenza

`docs/it/dbzero/vendite/manual/fatture_stampa_coda.md` dice, a proposito della
RLS: *«in G1 la coda non ha superficie di lettura → nessuna policy»*.

**Quella premessa non è più vera**: la coda stampa ha una lista a video dal
brief gestione-code (`elenca_coda_stampa`, scheda «Coda stampa» di Strumenti).
Lo scope oggi è **applicativo** — `add_emittente_scope_condition` sulla fattura
collegata — quindi non c'è un buco aperto adesso; ma la frase che decide se
serve una policy descrive un mondo che non c'è più, ed è il genere di riga che
resta vera in archivio e falsa nel prodotto.

---

# PARTE DB — risposta, correzioni, piano

> **Chi scrive:** team DB (`dev/db-tid`), 2026-09-04.
> **Esito:** richiesta **accolta**. Il disegno regge e il §2.4 è il pezzo che
> giustifica il brief. Sotto: quattro correzioni strutturali, tre decisioni di
> Tid, e il piano.
> **Decisioni di Tid (2026-09-04):** ① c'è anche **`archiviato_da`**;
> ② il verbo è **`code_manage`**, non owner-scoped; ③ sulla coda stampa si arma
> la **policy RLS**, non il solo filtro applicativo.

---

## 6. Correzioni al §2 — cosa cambia rispetto alla richiesta

### 6.1 ⭐ Il perimetro si scrive «non viva», non come elenco dei terminali

Il §2.3 elenca i terminali tabella per tabella (`FATTO · ERRORE · ANNULLATO` di
qua, `FATTO · ERRORE` di là). Ma la ragione che il §2.3 stesso porta non parla
di terminali: parla del **badge che conta i vivi**, e «vivo» ha già **una sola
definizione, dichiarata sede unica**, in
`frontend/src/core/composables/useQueueCountsPolling.js`:

```js
export const STATI_CODA_VIVI = ['PENDING', 'IN_CORSO']
```

con sopra, testualmente: *«La definizione sta QUI e non in tre posti, perché è
la stessa cosa che il badge conta e che la lista deve mostrare — e due letture
della stessa coda che non concordano sono già state un difetto (2026-08-27)»*.
L'enumerazione dei terminali sarebbe la quarta e la quinta copia, in una forma
diversa dalle prime tre.

⛔ **E le due forme non sono equivalenti nel tempo.** `stato NOT IN ('PENDING',
'IN_CORSO')` resta vera se domani nasce uno stato nuovo; l'elenco dei terminali
lo escluderebbe in silenzio — e il badge, che conta i vivi, non lo conterebbe:
riga non archiviabile *e* non contata, cioè un terzo caso che nessuno ha
deciso. ⭐ Scritta in negativo, la regola non ha bisogno di essere aggiornata
quando il `CHECK` degli stati cambia, e la **simmetria del §2.1 smette di
essere una promessa**: le due code non possono divergere perché la regola non è
scritta due volte.

**⇒ Un predicato solo, negativo, identico sulle due tabelle.**

### 6.2 ⛔ L'invariante vuole il suo `CHECK`: il guard copre solo l'UPDATE

*«Una riga archiviata non è viva»* è un **invariante di tabella**, non una
regola di transizione. Un trigger `BEFORE UPDATE` lascia scoperto l'`INSERT`:
una riga che nasce `archiviato = true, stato = 'PENDING'` è esattamente la riga
viva-e-invisibile che il §2.3 esiste per impedire.

Oggi nessuno la scrive — `dbops.fn_accoda_lavoro` e
`vendite.fn_accoda_stampe_lotto` elencano le colonne e non toccano la bandiera.
Ma è il caso della regola zero: *«zero occorrenze non significa che il caso non
esiste: significa che non c'è ancora un controesempio»*.

⇒ **Il `CHECK` è la sede dell'invariante; il trigger è la sede del
messaggio.** Sul percorso dell'operatore il guard `BEFORE ROW` solleva prima
che il `CHECK` sia valutato, quindi la persona legge
`E_CODA_ARCHIVIAZIONE_NON_AMMESSA` e non un `23514` nudo. Il `CHECK` è ciò che
resta quando il percorso non è quello previsto.

### 6.3 ⚠️ La forma del trigger — due difetti nella stessa riga di DDL

**`UPDATE OF archiviato` non vuol dire «archiviato è cambiato»**: scatta se la
colonna compare nella `SET`, anche assegnandole lo stesso valore. Il guard va
scritto sul **cambio e sulla direzione** (`NEW.archiviato AND NOT
OLD.archiviato`), altrimenti un domani un `SET archiviato = false, …` dentro un
altro verbo prende un rifiuto incomprensibile.

**`UPDATE OF stato` (§2.4) è la corsia calda del worker**: ogni claim, ogni
`marca_stampa_fatto`, ogni retry di `marca_stampa_errore`, ogni `reap_stale`
scrive `stato`. Senza filtro, il trigger verrebbe chiamato su **tutte** le
transizioni di **tutte** le righe per servire un caso che riguarda solo quelle
archiviate — e un `BEFORE` sulla corsia del drenaggio è anche una superficie
nuova su cui il drainer può morire.

⇒ **La clausola `WHEN`** (valutata senza entrare nella funzione) riporta il
costo a zero sul percorso normale. Le colonne di `UPDATE OF` sono **quattro**,
non due: dentro ci sono anche `archiviato_il` e `archiviato_da`, che altrimenti
sarebbero scrivibili a mano senza che nulla se ne accorga.

**Sul nome:** il trigger proposto si chiama `_a10_guard_archiviazione_`, ma
**scrive `NEW`** (il reset del §2.4). `fn_guard_*` che torna e `fn_check_*` che
solleva sono l'antipattern nominato in `linee-guida-sql` §5. Il nome perde la
parola `guard`: `trg_<tabella>_a10_archiviazione_upd`. Fase `_a10_` perché
l'unica cosa che può **fermare** un'operazione sta qui.

**Una funzione sola per due tabelle** — `dbops.trgfn_coda_archiviazione()`,
generica, schema e tabella dal `TG_TABLE_*` per il contesto dell'errore.
Precedenti in casa: `script.trgfn_audit_data_user_generic`,
`dbops.trgfn_tx_id_managed`.

### 6.4 ⛔ Il reset del §2.4 dimentica `archiviato_il` — e la colonna non ha uno scrittore

Due cose mancanti nello stesso punto.

* **Il reset è parziale.** Se `archiviato` torna `false` e `archiviato_il` resta
  valorizzato, la riga dice *«non sono archiviata, sono stata archiviata il 3
  settembre»*. La regola «chi alza la bandiera la abbassa» vale anche per la
  data.
* **Il §2.5 dà la colonna e non il suo scrittore.** Se la scrive il BE può
  mentire — archiviare senza datare, o datare senza archiviare — e il database
  non se ne accorge.

⇒ **Le due colonne le deriva il trigger** (`CURRENT_TIMESTAMP` e la GUC
`app.jwt_user` quando la bandiera si alza, `NULL` quando si abbassa) e un
`CHECK` di coerenza chiude il cerchio. Il BE non deve ricordarsi niente:
scrive `archiviato`, il resto viene dietro.

### 6.5 ⚠️ Il §2.5 usa un argomento simmetrico per arrivare a due conclusioni diverse

Il §2.5 rifiuta `data_update` — *«è l'istante dell'ultimo update qualunque esso
sia»* — e nella riga dopo **accetta la stessa coincidenza** per `user_update`.
Non regge: `user_update` è l'utente dell'ultimo update qualunque esso sia,
esattamente come `data_update` ne è l'istante. Stessa famiglia, stesso trigger
(`script.trgfn_audit_data_user_generic` — che, verificato, porta il **vero
utente JWT** e non `zeroerp_app`), stessa esposizione a chiunque scriva dopo.

⇒ **Decisione ① di Tid: entrambe.** `archiviato_da` accanto a `archiviato_il`,
derivata dallo stesso trigger con la stessa GUC.

⭐ E l'argomento buono per `archiviato_il` non è la coincidenza: è che
`data_update` risponde a *«quando è stata toccata»* e `archiviato_il` a *«quando
è stata messa via»*. Sono due domande, e un campo solo che risponde a due
domande in AND è la lezione già pagata con `is_attiva`.

### 6.6 ⭐ L'argomento del §2.3 che manca, ed è più forte del badge

Sulla coda stampa una riga **viva** archiviata occuperebbe lo slot di
`uq_fatture_stampa_coda_vivo`, e quindi **bloccherebbe la ristampa di quella
fattura** restando invisibile. Non «l'operatore legge 2 e vede 0»: l'operatore
chiede una ristampa, non succede niente, e non c'è nessun posto dove guardare.

Vale la pena tenerlo, perché **non dipende dal badge**: sopravvive il giorno in
cui il badge cambia forma. (Verificato: `fn_accoda_stampe_lotto` fa
`ON CONFLICT … WHERE stato IN ('PENDING','IN_CORSO') DO NOTHING`, quindi la
ristampa di una riga **terminale** nasce come riga nuova e non tocca
l'archiviata — il §2.3 è sicuro per costruzione, come dice.)

---

## 7. Correzioni al §1 e al §4 — fatti e perimetri

### 7.1 ⚠️ §1: «le due strade che l'operatore ha oggi» — non esistono

Il paragrafo si intitola **«Il fatto, verificato»**. Verificato invece
(2026-09-04):

* **`DELETE`**: nessun endpoint, nessun metodo di repository, nessuna SQL nel
  repo, su nessuna delle due code. Non è una strada dell'operatore: è `psql`.
* **`ANNULLA` sulla coda stampa**: il brief stesso dice che non esiste — ed è
  infatti al condizionale (*«che sarebbe la mossa ovvia da aggiungere»*) dentro
  una frase che al presente dice *«le due strade che l'operatore ha oggi»*.

**L'argomento non ne ha bisogno, ed è il punto:**
`count_coda_stampa_per_stato` è un `GROUP BY c.stato` senza filtro di
visibilità (verificato, `pipeline_repository.py:2540`), quindi **qualunque**
cosa tocchi lo stato o rimuova una riga sposta i numeri del pannello. È questa
la ragione per cui serve una bandiera e non un cambio di stato — e vale a
prescindere da quali verbi esistano oggi. Un condizionale scritto al presente,
in una sezione che si chiama «verificato», è la riga che qualcuno poi cita come
fatto.

### 7.2 ⛔ §4: «gated come gli altri due verbi (`code_manage`)» — non è come funzionano

Letto il codice: `annulla` e `requeue` sono **owner-scoped** — un operatore
agisce sui **propri** job senza `code_manage`; il permesso serve ad
**allargare** agli altrui (`_owner_filter_per_azione` → `owner_scope_key =
None`).

Ma l'archiviazione, per decisione di Tid, **vale per tutti**: chi archivia
toglie la riga dall'elenco **anche all'amministratore**. È un verbo con effetto
globale calato in un modello di permessi per-proprietario, e le due cose non
compongono da sole.

⇒ **Decisione ② di Tid: `code_manage`.** Effetto globale, permesso globale.
Nessun ramo owner-scoped sull'archiviazione: sarebbe un operatore che nasconde
righe a chi deve vederle tutte.

### 7.3 ⚠️ Il verbo non ha dove attaccarsi: la lista coda stampa non ha la colonna azioni

Le due code sono **liste configurabili** (`ui.lista_definizione` id **34** e
**35**), e le loro colonne stanno in `ui.lista_colonna`:

| lista | colonne | `azioni` |
| --- | --- | --- |
| 34 `dbops.coda_lavori` | id, job_type, stato, proprietario, tentativi, started_at, ended_at, **azioni** | ✅ |
| 35 `vendite.fatture_stampa_coda` | id, fattura, emittente, operatore, lotto_id, stato, tentativi, esito, data_update | ⛔ **assente** |

Il §4 assegna il verbo a BE/FE, ma **la riga che gli fa spazio è seed nostro**.
Senza, sulla coda stampa il kebab non esiste proprio. Entra nel perimetro DB.

⚠️ **E la colonna `archiviato_il` a catalogo nasce `attivo = f`**, non per
prudenza: `apps/core/tests/db/test_lista_proiezione_campo_sorgente.py` è un
cancello trasversale che pretende che ogni `campo_sorgente` **attivo** di una
lista senza vista sia una chiave che il repository consegna davvero — e le due
code sono nel suo registro. Accesa prima che il BE la proietti, quella riga fa
rosso un test che non c'entra niente con questo cantiere. La accende il BE
nello stesso commit in cui la proietta (è il pattern già usato per il binding
handler-evento).

### 7.4 ⚠️ Le azioni di riga: dove sta la terna, e perché qui non la spostiamo

`linee-guida-sql` §12.5 vuole `enabled`/`reason`/`reason_key` **dal database**
(`script.fn_check_<azione>`), col predicato identico a quello del guard. Oggi la
coda non lo fa: `CodaLavoriTab.vue:102` costruisce le azioni in FE e per giunta
con `visible: azionabile && row.stato === 'PENDING'`, cioè **fa sparire
l'azione per uno stato** — la «quarta via» che il §12.1 vieta per nome.

Il §4 del brief **fa meglio dei suoi vicini** (`disabled` + tooltip col motivo:
è la regola). Non chiediamo una `fn_check_*` nuova per il solo verbo nuovo:
sarebbe l'unico dei tre a passare dal database, e l'incoerenza costerebbe più
della regola. ⇒ **Il FE usa `!rigaCodaViva(row.stato)`**, il BB che già esiste,
e **non** scrive un terzo elenco di stati. Portare tutte e tre le azioni sotto
il §12.5 è un cantiere suo, e va aperto come tale.

---

## 8. §5 non è una nota a margine: è un requisito — e si chiude con la RLS

Verificato: su `vendite.fatture_stampa_coda` **non esiste nessun verbo oggi**
(gli endpoint sono `coda-stampa/`, sola lista; `annulla` e `requeue` vivono
solo su `coda-lavori`), e la tabella **non ha RLS attiva né alcuna policy**: lo
scope è applicativo, `add_emittente_scope_condition` sul join alla fattura, **in
lettura**.

Il verbo «Archivia» è quindi la **prima scrittura dell'operatore su quella
tabella**. Il momento in cui la premessa del `manual/` diventa falsa è la
richiesta stessa.

⇒ **Decisione ③ di Tid: si arma la policy RLS**, non il solo `WHERE`
applicativo. `rls_fatture_stampa_coda_ef_whitelist`, `FOR ALL`, scope delegato
alla **testata** via `script.fn_scope_ef_whitelist_via_fattura(auth_user_id,
sorgente_id)` — la stessa funzione di `fatture_righe` e `fatture_scadenze`, mai
un criterio proprio.

**Perché `FOR ALL` e non `FOR SELECT`** (lezione Ondata 2): con la sola SELECT
ogni scrittura operatore — anche in-scope — fallirebbe, e
`fn_accoda_stampe_lotto` gira `SECURITY INVOKER` anche dentro il contesto
operatore della coda lavori.

**I percorsi verificati il 2026-09-04, nessuno richiede modifiche:**

| Percorso | Sotto RLS? | Esito |
| --- | --- | --- |
| drainer stampa (`draina_coda_stampa`) | ⛔ no — `system_process_context` cambia **ruolo**, con guard fail-loud su `BYPASSRLS` | intatto |
| task pipeline `stampa_documenti_lotto` da batch | ⛔ no — stesso canale | intatto |
| stesso task dalla coda lavori (`OPERATORE`) | ✅ sì | passa: lotto, fattura e coda risolvono allo stesso emittente |
| liste e conteggi da web | ✅ sì | passa, e il filtro applicativo resta come difesa in profondità |
| `zeroerp_batch_fatturazione` | ⛔ no — `BYPASSRLS` + grado `'u'` sulla tabella nel provisioning | intatto |
| cancellazione fattura (`ON DELETE CASCADE`) | ⛔ no — azione RI, gira come owner | intatto |

⛔ **Nessuna policy `ba_ownership`**: la coda stampa non è una superficie del
portale cliente, e `linee-guida-sql` §10.1 dice di non armare policy
preventive. Il giorno che lo diventasse, si aggiunge lì.

⚠️ **`NO FORCE`**, a parità con tutta la famiglia fatture: l'owner resta esente,
così migrazioni e job owner non si bloccano. Il runtime è `zeroerp_app`, che
non è owner ed è `NOBYPASSRLS`: **la RLS morde dove deve**.

### 8.1 ⚠️ Il debito documentale è doppio, non singolo

`docs/it/dbzero/vendite/manual/fatture_stampa_coda.md` ha **due** premesse
scadute:

1. quella della RLS, che il §5 segnala — e che questo cantiere rende vera;
2. *«il **no-trigger** di `fatture_stampa_coda` (single-writer)»*, citata anche
   da `manual/coda_lavori.md`. Falsa su entrambi i pezzi: la tabella **ha** i
   trigger di audit e `tx_id` (li generano le automazioni a `ci_apply`), e col
   verbo «Archivia» smette di essere single-writer.

⚠️ **Effetto già in codice** (segnalazione al BE, fuori dal nostro perimetro):
`claim_stampe_pending` e `marca_stampa_fatto` scrivono a mano `data_update =
now(), user_update = CURRENT_USER`. Quelle righe sono **sovrascritte** dal
trigger `BEFORE`, che mette l'utente JWT vero. Innocue, ma sono codice che
crede a una doc scaduta.

---

## 9. Il piano — changeSet del 2026-09-04

| # | File | Cosa |
| --- | --- | --- |
| 1 | `00_schema/dbops/20260904-01-alter-coda-lavori-archiviazione` | `archiviato`, `archiviato_il`, `archiviato_da` + 2 `CHECK` |
| 2 | `00_schema/vendite/20260904-02-alter-fatture-stampa-coda-archiviazione` | speculare, stesso changeSet nella forma |
| 3 | `20_code/dbops/20260904-03-create-trgfn-coda-archiviazione` | la funzione **unica** per le due code |
| 4 | `00_schema/dbops/20260904-04-create-trigger-archiviazione-code` | **i due trigger in un changeSet solo** — armarne uno solo è la prima cosa che il §2.1 vieta |
| 5 | `00_schema/vendite/20260904-05-create-policy-rls-fatture-stampa-coda-ef-whitelist` | la policy, **inerte** finché non si arma |
| 6 | `00_schema/vendite/20260904-06-enable-rls-fatture-stampa-coda` | `ENABLE ROW LEVEL SECURITY` isolato: è il momento in cui il comportamento cambia |
| 7 | `80_data/sql/config/codici_errore.csv` + `messaggi_errore.csv` | append al CSV, nessun loader nuovo — il mirror è `runOnChange` |
| 8 | `80_data/sql/ui/lista_colonna.csv` | `azioni` su lista 35 (attiva) + `archiviato_il` su 34 e 35 (`attivo = f`, §7.3) |
| 9 | `db/pgtap/dbops/test-coda-archiviazione.sql` | guard, reset, `CHECK`, e il **presidio di simmetria** fra le due tabelle |
| 10 | `db/pgtap/rls/test-rls-fatture-stampa-coda.sql` | i cinque casi di `linee-guida-sql` §10.8 |
| 11 | `manual/coda_lavori.md`, `manual/fatture_stampa_coda.md` | l'archiviazione + le due premesse scadute (§8.1) |

⭐ **Il presidio di simmetria (9) è la parte che non si vede.** Il §2.1 dice che
un'asimmetria «si paga al primo che tocca solo una delle due»: un test che
confronta colonne, tipi, vincoli e trigger delle due code trasforma quella
frase in un'asserzione. Finché resta prosa, la prima divergenza passa.

---

## 10. Cosa resta a BE/FE dopo l'apply

Invariato rispetto al §4, con tre precisazioni:

1. filtro `archiviato = false` di default nelle due `elenca`, con parametro per
   chiederle — **e nessun `archiviato` nei conteggi**: il §3 è il contratto;
2. `archiviate_count` nell'envelope;
3. verbo «Archivia»/«Ripristina» nel kebab, **gated `code_manage`** (§7.2), con
   `disabled` + tooltip quando la riga è ancora viva, e il predicato preso da
   `!rigaCodaViva(row.stato)` (§7.4) — nessun terzo elenco di stati;
4. interruttore «mostra archiviate» in `CodaTabBase`;
5. ⭐ **accendere `archiviato_il` in `ui.lista_colonna`** (`attivo = t`) nello
   stesso commit in cui la colonna entra nella proiezione dei due `elenca`, e
   proiettarla — altrimenti il cancello trasversale del §7.3 resta rosso o la
   colonna resta invisibile. Con essa la chiave i18n
   `strumenti.code.col_archiviata_il` nei due `locales` (il seed la nomina, non
   la definisce: il testo non si scrive in SQL);
6. `./manage-env.sh genera_error_policies` + la voce in
   `error_messages_fallback.py`, come da §2.6.

⚠️ **`archiviato` NON va nel `WHERE` di claim, drainer, reaper, `mark_*`,
`count_*`.** Il §3 non è una raccomandazione: è la cosa che distingue
l'archiviazione da un annullamento silenzioso, cioè da qualcosa di peggio della
cancellazione che questa richiesta esiste per evitare.

---

## 11. Registro delle attività — DB APPLICATO il 2026-09-04

> **Applicato da Tid** alle 00:20 del 2026-09-04. I sei changeSet risultano
> `EXECUTED` in `databasechangelog`; i mirror CSV di `config.codici_errore`,
> `config.messaggi_errore` e `ui.lista_colonna` hanno ri-eseguito (`RERAN`,
> sono `runOnChange`) portandosi dietro le righe nuove; la documentazione
> auto-generata è stata rigenerata alle 00:20:28.

### 11.1 Cosa è entrato nel database

| changeSet | Esito | Contenuto |
| --- | --- | --- |
| `20260904-01-alter-coda-lavori-archiviazione` | ✅ EXECUTED | `dbops.coda_lavori`: `archiviato`, `archiviato_il`, `archiviato_da` + `chk_coda_lavori_archiviato_non_vivo` + `chk_coda_lavori_archiviato_coerente` |
| `20260904-02-alter-fatture-stampa-coda-archiviazione` | ✅ EXECUTED | `vendite.fatture_stampa_coda`: le stesse tre colonne e i due `CHECK` gemelli, parola per parola |
| `20260904-03-create-trgfn-coda-archiviazione` | ✅ EXECUTED | `dbops.trgfn_coda_archiviazione()` — guard + reset + derivazione dei due timbri, **una funzione per due code** |
| `20260904-04-create-trigger-archiviazione-code` | ✅ EXECUTED | `trg_coda_lavori_a10_archiviazione_upd` e `trg_fatture_stampa_coda_a10_archiviazione_upd`, in un changeSet solo, con la clausola `WHEN` che tiene fuori la corsia del worker |
| `20260904-05-create-policy-rls-fatture-stampa-coda-ef-whitelist` | ✅ EXECUTED | la policy, creata inerte |
| `20260904-06-enable-rls-fatture-stampa-coda` | ✅ EXECUTED | 🔴 **`ENABLE ROW LEVEL SECURITY` (NO FORCE)**: da qui la coda stampa filtra per emittente anche a database |

**Seed** (append ai CSV, nessun loader nuovo — verificato a database):

* `config.codici_errore`: `E_CODA_ARCHIVIAZIONE_NON_AMMESSA` / `CONFLITTO_STATO`;
* `config.messaggi_errore` id **1043**, con `causa` e `soluzione`;
* `ui.lista_colonna` **712** (`azioni` sulla lista 35 — `attivo = t`, senza la
  quale il kebab della coda stampa non avrebbe dove attaccarsi), **713** e
  **714** (`archiviato_il` sulle liste 34 e 35, **`attivo = f`**: le accende il
  BE quando le proietta, §7.3).

### 11.2 Cosa è stato provato, e come

**Prima dell'apply** — l'SQL **estratto** dagli YAML (non riscritto) eseguito in
transazione con `ROLLBACK`, più otto prove di comportamento sulla stessa
transazione: guard sulla riga viva, archiviazione della terminale, immutabilità
dei timbri, reset da requeue, i due `CHECK` sull'`INSERT`, e la coda stampa che
si comporta allo stesso modo.

**Dopo l'apply** — i due pgTAP nuovi, con il runner **`app`** (cioè come gira
l'applicazione, RLS attiva):

| File | Esito |
| --- | --- |
| `db/pgtap/dbops/test-coda-archiviazione.sql` | ✅ **18/18** |
| `db/pgtap/rls/test-rls-fatture-stampa-coda.sql` | ✅ **10/10** |

E i sei guardrail statici della CI (`runOnChange`, `preCondition`/seed,
DDL su trigger di automazione, GRANT ai ruoli batch, preambolo pgTAP, letterali
SQL): tutti verdi, e il debito `throws_ok` senza discriminante è rimasto a 131 —
i due file nuovi passano sempre lo SQLSTATE.

⚠️ **La suite completa l'ha fatta girare Tid** (verde). Il punto che meritava
quella corsa è l'armamento della RLS: è l'unica modifica di questo cantiere che
cambia il comportamento del database per chi non l'ha chiesta.

### 11.3 Documentazione aggiornata

* `docs/it/dbzero/dbops/manual/coda_lavori.md` — sezione «Archiviare una riga
  senza toccarne lo stato», e la **premessa scaduta corretta**: la frase
  *«non il no-trigger di `fatture_stampa_coda` (single-writer)»* era falsa su
  entrambi i pezzi;
* `docs/it/dbzero/vendite/manual/fatture_stampa_coda.md` — l'archiviazione, la
  **policy RLS che ora esiste** (al posto di *«in G1 la coda non ha superficie
  di lettura → nessuna policy»*), e la fine del single-writer;
* auto-generata: `dbops/tabelle/coda_lavori.md`,
  `vendite/tabelle/fatture_stampa_coda.md` e la nuova
  `dbops/funzioni/trgfn_coda_archiviazione.md` — rigenerate da Tid, **non
  toccate a mano**.

### 11.4 ⛔ Il debito che resta, ed è del backend

Non è una lista di cortesie: finché queste tre cose non ci sono, la colonna
esiste e non serve a niente.

1. **Il filtro nelle due `elenca`** (`archiviato = false` di default, parametro
   per chiedere le archiviate) e **`archiviate_count`** nell'envelope. Senza il
   conteggio, «coda pulita» e «tre righe messe via» si leggono uguali.
2. **Il verbo** «Archivia»/«Ripristina», gated **`code_manage`** (§7.2, e non
   owner-scoped come annulla e requeue: l'effetto è globale), con `disabled` +
   tooltip sulla riga ancora viva e il predicato da `!rigaCodaViva(row.stato)`.
   ⚠️ Sulla coda stampa è la **prima scrittura dell'operatore** su quella
   tabella: ora c'è la policy RLS a difenderla, ma il filtro applicativo va
   messo lo stesso — la RLS si somma ai filtri, non li sostituisce.
3. **`archiviato_il` in proiezione** + `attivo = t` sulle righe 713/714 + la
   chiave `strumenti.code.col_archiviata_il` nei locales, **nello stesso
   commit**: accendere la colonna prima di proiettarla fa rosso
   `apps/core/tests/db/test_lista_proiezione_campo_sorgente.py`.
4. `./manage-env.sh genera_error_policies` + la voce in
   `error_messages_fallback.py` per `E_CODA_ARCHIVIAZIONE_NON_AMMESSA`.

⛔ E la riga che vale più di tutte: **`archiviato` non entra nel `WHERE` di
claim, drainer, reaper, `mark_*` e `count_*`.** Il §3 è il contratto di questo
cantiere, non una raccomandazione.

---

# PARTE BE/FE — registro delle attività, 2026-09-04

> **Chi scrive:** BE/FE (`dev/backend-tid`), 2026-09-04.
> **Esito:** i quattro punti del §11.4 sono chiusi. Sotto: cosa è entrato, cosa
> è stato provato e come, e le due cose che restano fuori con la loro ragione.

## 12. Cosa è entrato

### 12.1 Le due `elenca` — filtro, proiezione, conteggio

| Dove | Cosa |
| --- | --- |
| `CodaLavoriRepository.elenca` | `includi_archiviate` (default `False` → `NOT archiviato` nel `WHERE`), proiezione di `archiviato`/`archiviato_il`/`archiviato_da`, e `archiviate` nel ritorno |
| `VenditePipelineRepository.elenca_coda_stampa` | speculare, parola per parola |
| `gestione_service.elenca_coda_*` | pass-through del flag + **`archiviate_count`** nell'envelope |
| `views_tracciamento` | query param `?archiviate=` (`qp_bool_optional`, strict) su entrambe le liste |

⭐ **Il conteggio ha un perimetro suo, ed è il punto che si sbaglia.** Le righe
archiviate sono escluse dal `WHERE` della lista, quindi non c'è modo di contarle
con un `FILTER` sulla stessa valutazione. Il frammento di `WHERE` **senza la
bandiera** (`base_conditions`) è condiviso fra le due query invece di essere
riscritto: due copie divergerebbero al primo filtro nuovo, e il numero
racconterebbe un perimetro diverso dalla lista sopra di sé.
⚠️ Vale **0** quando le archiviate sono incluse — lì non c'è niente di nascosto
da dichiarare — ed è la stessa semantica di `ritirate_count`.

### 12.2 I due verbi — di COLLEZIONE, con esito parziale

Quattro rotte, `POST`, `Idempotency-Key` obbligatoria, corpo `{"ids": [...]}`:

```text
/core/tracciamento/coda-lavori/archivia/     ·  /ripristina/
/core/tracciamento/coda-stampa/archivia/     ·  /ripristina/
```

* ⭐ **Rotte di collezione anche per una riga sola**: il menu di riga manda un
  elenco di uno. Un verbo di massa e uno singolo sarebbero **due contratti da
  tenere allineati per lo stesso rifiuto**, che è per riga. Tetto **200** (lo
  stesso della paginazione, stessa ragione di `MAX_ATTIVITA_RIPORTO`) e dedup
  con ordine preservato — il database tratterebbe due volte lo stesso id come
  una riga sola, ma il conteggio a video direbbe un numero diverso da quello
  spuntato.
* ⛔ **Esito PARZIALE, non tutto-o-niente**, sul BB `run_fan_out`: un savepoint
  per riga, l'errore isolato, `{esito, richieste, riuscite, falliti[]}`. Il
  rifiuto è **per riga**, quindi una transazione unica farebbe fallire venti
  archiviazioni buone per una riga sola — e chi guarda non saprebbe quale.
  ⚠️ Risponde **200 anche a PARZIALE**: chi legge guarda `esito`.
* ⛔ **E per questo NON un solo `UPDATE … WHERE id = ANY(…)`** col predicato di
  stato nella `WHERE`: sarebbe più veloce, ma scriverebbe la **seconda copia**
  di «riga viva» — che ha una sede sola, il trigger.
* ⚠️ Il codice e la frase del rifiuto si conservano in un dizionario Python
  popolato **dentro** il savepoint e letto **dopo** il rollback: un rollback
  annulla le righe di database, non un assegnamento in memoria. È l'unico modo
  di dare all'operatore la frase del catalogo invece della stringa normalizzata
  del BB, che è buona per un log e non per una persona.

* **Gate `code_manage`** nel **service** (`_guard_archiviazione` →
  `E_PERMESSO_NEGATO`, 403). ⛔ **Nessun ramo owner-scoped**, per la decisione ②
  (§7.2): effetto globale, permesso globale.
  ⛔ **E non un `post_permission` sulla view, che è dove era finito alla prima
  stesura.** `ZeroERPPermission`, trovando un `<metodo>_permission`, ritorna
  l'esito dell'azione di processo e **salta il controllo di area**: un operatore
  con `code_manage` e area `strumenti` in sola `LETTURA` sarebbe passato, mentre
  annulla e requeue — che quel campo non lo dichiarano — cadono su
  `METHOD_REQUIRES['POST']` e pretendono `TUTTO`. ⚠️ Due POST adiacenti **nella
  stessa schermata** con due contratti d'area diversi non danno nessun errore:
  danno un permesso che «funziona» finché qualcuno non lo restringe e non
  capisce perché non ha effetto. Senza `post_permission` valgono entrambi i
  controlli, e c'è un test che lo presidia.
* ⭐ **Due verbi e non un flag nel corpo**: archiviare può essere rifiutato,
  ripristinare no, e un endpoint il cui esito dipende da un booleano nel payload
  nasconde quella differenza a chi legge le rotte.
* ⛔ **Il backend non ricopia il criterio di stato.** `imposta_archiviato*` fa un
  `UPDATE` sulla sola chiave e lascia rifiutare al trigger. C'è un test che lo
  presidia *in negativo* (§12.5, test 22): con una riga dichiarata `PENDING` dal
  repository l'archiviazione passa comunque, perché a decidere è il database.
  Se un domani qualcuno aggiungesse un controllo qui, quel test diventerebbe
  rosso e direbbe perché.
* ⛔ **Né scrive i due timbri**: `archiviato_il`/`archiviato_da` le deriva il
  trigger. Verificato dal vivo: con la GUC `app.jwt_user` valorizzata la riga
  porta `tid`, senza porta `zeroerp_app` (il `COALESCE` del ramo di ripiego).
* ⚠️ **Sulla coda stampa il filtro applicativo di emittente c'è lo stesso**
  (`add_emittente_scope_condition` sul JOIN alla fattura, dentro l'`UPDATE …
  FROM`): la RLS armata il 2026-09-04 **si somma** ai filtri, non li
  sostituisce. Fuori perimetro → 0 righe → 404, indistinguibile da inesistente.
* Il 404 riusa **`E_JOB_NON_TROVATO`** su entrambe le code: la *condizione* è la
  stessa — una riga di coda che non c'è, o che il perimetro non lascia vedere —
  e un codice si spezza quando i significati portano a **reazioni diverse della
  pagina**, non perché le tabelle sono due.

### 12.3 `archiviato_il` a video

`ui.lista_colonna` **713**/**714** passate ad `attivo = t` **nello stesso
commit** in cui la colonna entra nella proiezione dei due `elenca` e nelle due
whitelist di ordinamento (`ELENCA_SORT_SQL`, `CODA_STAMPA_SORT_SQL`, con
`NULLS LAST`: la data è `NULL` su ogni riga non archiviata, e in `DESC`
finirebbe in testa). Più la chiave i18n `strumenti.code.col_archiviata_il` nei
due `locales`.

⚠️ **Sono TRE cancelli e non uno**, e vanno tutti insieme:
`test_lista_proiezione_campo_sorgente` (la colonna attiva dev'essere una chiave
che il repository consegna davvero), `test_liste_configurabili_seed` (seed e
whitelist di ordinamento devono coincidere) e il test che fa **partire** l'SQL
di ogni colonna ordinabile in entrambi i versi. Verdi.

### 12.4 Il codice errore

`./manage-env.sh genera_error_policies` → una voce sola aggiunta
(`E_CODA_ARCHIVIAZIONE_NON_AMMESSA` → `CONFLITTO_STATO`), più la sua frase in
`error_messages_fallback.py` — **senza segnaposto**, mentre quella a catalogo ha
un `%s` con lo stato: è proprio quando gli argomenti non arrivano che il
segnaposto finirebbe a video in chiaro.

### 12.5 Il frontend

* interruttore **«mostra archiviate»** in `CodaFiltriToolbar` — **una volta**,
  le due schede lo ereditano da `CodaTabBase` — con accanto **il conteggio** di
  ciò che resta fuori (`archiviate_count`, letto via l'hook `onPayload` di
  `useListaEmptyStateFetch`: dentro il BB, quindi **dopo** il guard anti-race,
  altrimenti il numero racconterebbe un contesto diverso dalla lista);
* verbi **«Archivia» / «Ripristina»** nel kebab di **entrambe** le code, dal
  composable condiviso `useCodaArchiviazione` — estratto **prima** di scrivere
  la seconda copia;
* ⭐ **selezione multipla** (richiesta di Tid, 2026-09-04): caselle di riga +
  seleziona-tutto **di pagina** e un «Archivia N righe» nella barra delle
  azioni, che compare solo con qualcosa spuntato. `useSelezioneCoda` sopra il
  BB `useSelezioneToggle`. ⛔ La casella spenta è una **comodità, non un
  presidio**: il perimetro lo applica il database. ⚠️ Il **prune** serve qui più
  che altrove — le due schede si ricaricano da sole ogni 15 s, e una riga
  spuntata può smettere di essere archiviabile sotto le mani. ⭐ La selezione
  serve al **solo «Archivia»**: il gesto di massa è ripulire l'elenco, mentre
  «Ripristina» è la correzione su una riga che si sta guardando — una selezione
  per entrambi i verbi ammetterebbe insiemi misti e il pulsante non saprebbe
  più cosa promettere;
* il predicato è **`!rigaCodaViva(row.stato)`** (§7.4): il BB che già esiste, non
  un terzo elenco di stati;
* **il permesso nasconde** (`action: 'code_manage'`), **lo stato disabilita col
  motivo** (`disabled` + `tooltip`, che nel kebab compare come riga sotto la
  label: su touch non c'è hover);
* tag «archiviata» accanto allo stato, col tooltip *chi* e *quando* dai due
  timbri — visibile solo con l'interruttore acceso, perché con l'interruttore
  spento quelle righe non ci sono e un tag che non può mai apparire è rumore.

⚠️ **La coda stampa smette di essere di sola lettura**, e la colonna del kebab su
quella lista è nata col seed **712**: senza quella riga lo slot `#actions` non
avrebbe avuto dove attaccarsi — silenziosamente, senza errore.

## 13. Cosa è stato provato, e come

**Suite Django completa: 4409 test verdi.** Più i cancelli che vogliono il
database vero (`ZEROERP_TEST_DB_E2E=1`): proiezione dei `campo_sorgente`, seed
delle liste configurabili, terzo lato dei codici errore, campi diagnostici — 30
verdi.

**Sette test nuovi** in
`apps/core/tests/services/test_coda_lavori_gestione_service.py` (16→22): il
default nascosto e il flag su entrambe le code, la simmetria delle due,
la direzione che arriva al repository, i due 404, il passaggio di
`auth_user_id`, e il presidio in negativo del §12.2.

⭐ **E una prova dal vivo sul database di sviluppo, in transazione annullata**,
perché ciò che il contratto dichiara ammesso va provato **per intero**: un
binding sbagliato non è un errore educato, è un 500.

| Cosa | Esito |
| --- | --- |
| `elenca` su **ogni** colonna delle due whitelist × 2 versi × 2 valori del flag | tutte partono |
| archivio + ripristino su una riga vera di `coda_lavori` | timbri derivati, poi riazzerati |
| archivio su una riga vera di `fatture_stampa_coda`, **in contesto operatore** | `total` 26 → 25, `archiviate` 0 → 1; con il flag acceso 26 e 0 |
| riga **viva** su entrambe le code | `E_CODA_ARCHIVIAZIONE_NON_AMMESSA`, **409**, messaggio a catalogo con lo stato e `hint` con la soluzione |
| id inesistente, entrambe le code | `False` → 404 |

⚠️ **Il primo giro della coda stampa dava zero righe, e lo zero sembrava un
dato**: con la RLS armata, una connessione senza le GUC `app.*` vede una tabella
vuota. La prova che conta è la seconda, quella con il contesto operatore — senza,
il verbo sulla coda stampa non sarebbe stato esercitato affatto.

## 14. Cosa resta fuori, e perché

1. ✅ **Il migrate — fatto.** Verificato il 2026-09-07: le righe 713/714 di
   `ui.lista_colonna` sono `attivo = t`, quindi la colonna «Archiviata il» c'è.
   Questa voce si chiude.
2. ⚠️ **Le scritture a mano di `data_update`/`user_update`** in
   `claim_stampe_pending`, `marca_stampa_fatto`, `marca_stampa_errore` e
   `reset_stale_stampe_in_corso` — segnalate dal team DB al §8.1. Sono
   **innocue** (il trigger di audit le sovrascrive con lo stesso istante e con
   l'utente JWT vero) ma sono codice che crede a una doc scaduta, e il commento
   che le accompagna dice *«la tabella NON ha trigger audit»*, che oggi è falso.
   ⛔ Non toccate qui: `reset_stale_stampe_in_corso` **ragiona** su `data_update`
   come istante del claim, quindi la pulizia va fatta guardando quel reaper e
   non in coda a un cantiere che parla d'altro.

---

## 15. ✅ Verifica di chiusura lato DB — 2026-09-07

Riletto contro il database, non contro il documento.

| Cosa | Esito |
| --- | --- |
| `archiviato`, `archiviato_il`, `archiviato_da` sulle due code | ✅ presenti e simmetriche |
| `chk_*_archiviato_non_vivo` e `chk_*_archiviato_coerente` | ✅ su entrambe |
| `trg_*_a10_archiviazione_upd` | ✅ su entrambe |
| RLS su `vendite.fatture_stampa_coda` (§8) | ✅ attiva, `rls_fatture_stampa_coda_ef_whitelist` |
| `E_CODA_ARCHIVIAZIONE_NON_AMMESSA` a catalogo | ✅ `CONFLITTO_STATO` |
| `ui.lista_colonna` 713/714 | ✅ `attivo = t` — il migrate è passato |
| Debito documentale del §8.1 | ✅ **pagato**, riletto nei file: entrambi i manual correggono le premesse scadute |
| pgTAP `test-coda-archiviazione`, `test-coda-lavori`, i due `test-rls-fatture-stampa-coda*` | ✅ 4 su 4 PASS |

⇒ **Lato DB questo cantiere non ha più niente da fare.**

### ⚠️ Una cosa che nessuno ha in carico, e vale più delle altre

Il contratto del §3 — **«`archiviato` non entra nel `WHERE` di claim, drainer,
reaper, `mark_*` e `count_*`»** — oggi è **rispettato**: verificato il
2026-09-07, `archiviato` compare in `pipeline_repository` e in
`coda_lavori/repository` solo nel percorso di **elenco** (filtro di default e
conteggio delle archiviate), mai nei percorsi di lavoro.

⛔ **Ma non lo presidia niente.** È una frase in un brief, e i test coprono il
verso positivo («le archiviate sono nascoste di default») non quello negativo
(«nessun altro le nasconde»). Il giorno in cui qualcuno aggiunge `AND NOT
archiviato` a un `claim` per «coerenza», l'archiviazione diventa un
annullamento silenzioso — cioè **peggio della cancellazione che questa richiesta
esiste per evitare** — e nessun test diventa rosso.

⭐ È lo stesso difetto che questa giornata ha incontrato altre tre volte: *una
regola che vive in prosa vale finché qualcuno se la ricorda.* La forma del
presidio è un test del backend che legge l'SQL dei percorsi di lavoro e pretende
che la parola non ci sia — non una revisione a mano.

⚠️ Non è stato scritto: è del backend, e va deciso, non aggiunto di straforo in
coda a una verifica.
