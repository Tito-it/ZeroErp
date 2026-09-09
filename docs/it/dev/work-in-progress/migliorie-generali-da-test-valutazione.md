# Migliorie generali da test valutazione

> Due valutazioni dello **strato DB**, a sette mesi di distanza.
>
> * **febbraio 2026** — voto sintetico 8.9/10, «design production-ready». Rimane
>   qui sotto (§1) come **fatto datato**, insieme a ciò che di quel giudizio non
>   reggeva già allora.
> * **2026-09-08** — questa. Perimetro: solo DB. Sorgenti: la **struttura** del
>   database `zeroerp` di sviluppo (catalogo PostgreSQL: policy, GRANT,
>   `proconfig`, `pg_trigger`, `pg_constraint`), il repo al commit `89d36ad1b`
>   su `dev/db-tid`, e i file di CI. Nessun conteggio di righe di lavoro è usato
>   come argomento.

---

## 0. Come si legge, e perché il metodo conta più del voto

⛔ **Un voto medio su undici aree è lo strumento sbagliato**, ed è il primo
difetto della valutazione di febbraio. La media tratta «naming conventions» e
«la catena che impedisce a una regressione di entrare» come due addendi dello
stesso peso. Non lo sono: la prima è cosmesi, la seconda decide se tutto il
resto è vero. Un 9,0 di media che contiene un anello rotto **non descrive un
sistema al 90%**: descrive un sistema di cui non si sa quanto sia vero.

Questa valutazione perciò:

* separa ciò che è **stato costruito** (§2) da ciò che **non tiene** (§3);
* ordina i difetti per **conseguenza**, non per area;
* dichiara esplicitamente ciò che febbraio chiamava difetto **e non lo era** (§4);
* dà una scorecard **pesata**, non una media (§5).

⚠️ Tutte le misure qui dentro sono **letture di struttura** — quali policy
esistono, quali GRANT, quale `search_path`, cosa contiene un file di CI — e sono
**fatti datati 2026-09-08**. Dove compare un conteggio di righe di lavoro (una
sola volta, §3 D8) è come **controesempio**: «questo caso esiste ed è gestito
male». È l'unico uso ammesso.

### Perimetro

Solo **strato DB**: schema, funzioni, trigger, viste, policy, GRANT, seed,
changelog Liquibase, pgTAP e i cancelli di CI che li riguardano. Backend e
frontend compaiono **solo** dove sono il destinatario di un contratto scritto nel
database (la classe di un codice errore, il GUC di identità, la lettura di una
vista). Non sono valutati.

---

## 1. La valutazione di febbraio, riletta

### 1.1 Cosa aveva visto giusto

**L'unico allarme vero era «test coverage 7.0/10, priorità alta»**, e sette mesi
dopo è ancora l'allarme — non perché i test non siano cresciuti (94 → **600
file**, ~6.183 asserzioni), ma perché il problema non era il numero: era che
**nessuno li faceva contare**. Vedi §3 D1.

Erano corrette anche: la lode ai trigger generici (oggi il riuso è
strutturalmente più forte di allora), l'error handling centralizzato, la FK index
policy, la disciplina Liquibase.

### 1.2 Cosa non reggeva, già allora

| Diceva febbraio | Perché non reggeva |
| --- | --- |
| «`contabilita`: **0 test, gap critico, dominio business-critical**» | ⛔ **Sbagliato allora e sbagliato oggi.** Lo schema `contabilita` è **vuoto**: zero tabelle, zero funzioni, zero viste. La misura «0 test» è stata letta come difetto senza chiedere al modello *cosa* avrebbe dovuto coprire. È il caso da manuale della Regola zero: un conteggio ha disegnato una priorità alta su un perimetro che non esiste |
| «`acquisti`: 0 test, **critico — specchia vendite**» | Mezzo giusto. Che *specchi* vendite è un'affermazione sul modello, e vale. Che il rimedio sia «aggiungere test» no: mancano prima **le funzioni** — `acquisti` ha 42 FK e 2 funzioni. Non si collauda un dominio che non è stato scritto |
| «`clienti` ha 18 trigger → valutare consolidamento (**priorità bassa**)» | Osservazione a livello di **sintomo**. Il numero non è una scelta di stile: è la conseguenza meccanica di un pattern che genera **un trigger per figlia**. Oggi `catalogo.articoli` ne ha **46**. La domanda giusta non era «consolidare?» ma «la forma del pattern regge al crescere delle figlie?» — vedi §3 D9 |
| «Voto 8.9/10 — design **production-ready**» | Nessuna area era pesata per conseguenza, e due delle domande che decidono la frase «production-ready» non erano nella griglia: *chi vede quali righe* (la RLS non esisteva ancora) e *cosa impedisce a una regressione di entrare* |
| «509 pagine manuali, gap su 3 schemi» | Corretto e **chiuso**: oggi 1.410 pagine manuali su 1.500 auto-generate. `magazzino` 32, `acquisti` 11, viste coperte |

### 1.3 Le proposte di automazione di febbraio, sette mesi dopo

| # | Proposta | Stato al 2026-09-08 |
| --- | --- | --- |
| 1 | Scaffolding changelog YAML | ⛔ non fatto |
| 2 | Scaffolding pgTAP | ⚠️ parziale — `db/pgtap/_TEMPLATE.sql.txt` + `docs/it/guide/pgtap-come-si-scrive-un-test.md` |
| 3 | Generatore `loadUpdateData` da CSV | ⛔ non fatto (esiste `scripts/gen_seed_lista.py`, che è un'altra cosa) |
| 4 | Linter `%TYPE` | ⛔ non fatto |
| 5 | `fn_setup_standard_table` | ⭐ **superata da qualcosa di meglio.** Il framework automazioni (`dbops.fn_run_automations_*` + `automation_scope`/`automation_rules_tbl`) applica audit, `tx_id`, storico, lock colonne, cleanup e delete-block **per pattern** nella passata `ci_apply`. Non serve chiamarla per tabella: non serve chiamarla affatto |
| 6 | Validatore pre-deploy | ⭐ **realizzato in forma migliore**: sette cancelli statici in `ci-validate.yaml` (`runOnChange`, preambolo pgTAP, letterali SQL, preCondition su `80_data`, DDL su trigger di automazione, GRANT ai ruoli batch, licenze) più `scripts/ci-local.sh`, che replica la CI in locale |
| 7 | Diff signature funzioni | ⛔ non fatto |
| 8 | Report trigger per tabella | ⚠️ interrogabile (`dbops.vw_trigger_functions`), non confezionato |
| 9 | Template Liquibase per pattern | ⛔ non fatto — e in buona parte reso inutile dal #5 |

⭐ Le due proposte che sono state realizzate sono anche le due che hanno cambiato
forma strada facendo. Le sette non fatte sono tutte **acceleratori di scrittura**:
sette mesi senza che siano mancati dice che non erano il collo di bottiglia.

---

## 2. Cosa è nato in questi sette mesi

Sono le aree che febbraio **non poteva** avere in griglia. Non è un elenco di
novità: ognuna porta un giudizio.

### 2.1 ⭐ Il perimetro dei dati (RLS + multi-veste) — l'area nuova più importante

Non esisteva. Oggi: 32 tabelle con RLS attiva, 46 policy, quattro vesti
(`OPERATORE` 33 policy, `CLIENTE_PORTALE` 8, `SHOP_CUSTOMER` 3,
`FORNITORE_PORTALE` 2) e tredici funzioni `script.fn_scope_*` che risolvono
l'ambito. Dal **2026-08-07** i pgTAP girano come l'**applicazione**
(`zeroerp_app`), non più come owner: è il cambiamento singolo di maggior valore
dell'anno, perché prima nessuna policy veniva esercitata da nessun test.

⭐ **Ed è fail-closed per costruzione**, che è la scelta giusta: ogni policy è
permissiva e condizionata a `current_setting('app.ruolo_applicativo')`. Una
sessione senza GUC, o con una veste che nessuna policy nomina, non vede **niente**
— non vede troppo. Il costo è che l'accesso amministrativo deve arrivare da un
meccanismo suo, e non da una policy dimenticata.

⚠️ **Ed è anche l'area con il difetto peggiore** (§3 D2/D3): è costruita bene
dove è finita, ed è finita su **una famiglia di documenti su sei**.

### 2.2 ⭐ I presidi e i registri del debito — un artefatto raro

`docs/it/guide/presidi-e-registri-del-debito.md` non è documentazione: è una
teoria di come un controllo mente. Il §4-bis («una regola che mente», con il caso
delle sedici chiamate rotte zittite da un'etichetta rassicurante) e il §6 punto 5
(«fai fallire il controllo quando non può misurare») sono il genere di cosa che
in un progetto normale non si scrive mai.

⛔ **E il difetto principale di questo documento (§3 D1) è la violazione del §6
punto 5 di quella stessa guida.** Il progetto ha scritto la regola e non l'ha
applicata al proprio cancello più costoso.

Oggi in `dbops` ci sono **30 viste di presidio**. Sono il livello meta del
progetto e vanno considerate un asset, non uno strumento.

### 2.3 Il codice errore come contratto a tre lati

852 codici a catalogo, 847 messaggi, dieci classi. Il contratto è esplicito:
`codice` → backend (status HTTP e `ui_action`), `context->>'campo'` → frontend,
`VARIADIC valori` → l'operatore. Con il presidio del «terzo lato»
(`dbops.vw_codici_errore_da_dichiarare`) e il «rubinetto» che impedisce a un
codice di allargare il proprio significato.

⚠️ Il registro non cala: 508 codici su 852 risultano non dichiarati lato
applicativo. Vedi §3 D11.

⛔ **Sei codici vivi non hanno nessun messaggio.** Tutti `AVVISO`, tutti nominati
da esattamente una funzione: `W_FONDO_ESEGUITO_NON_RESETTABILE`,
`W_FONDO_FIGLIA_CONGELATA`, `W_FONDO_MINIMO_NON_RIPRISTINABILE`,
`W_FONDO_RIGA_CONTABILE_NON_AGGIORNABILE`, `W_FONDO_TRATTENUTO_DA_SISTEMAZIONE`,
`W_SCADENZE_TOTALE_NEGATIVO`. Il `note` a catalogo spiega la condizione allo
sviluppatore; **all'operatore non arriva nessuna frase**. Il verso opposto è
pulito: zero messaggi orfani.

⚠️ **E il «multi-lingua» è una capacità, non un fatto**: 846 messaggi in `it`,
**uno** in `en`. La colonna `lingua` c'è e il modello regge; il catalogo è
monolingue. Febbraio lo elencava fra i punti di forza a 9,5/10 — è il modo tipico
in cui una valutazione diventa ottimista: si dà per fatto ciò che è **possibile**.

### 2.4 I processi automatici hanno un'identità e un emittente

`dbops.processi` + `processi_identita` + `processi_bersagli`, con
`vw_processi_dominio_senza_identita` / `_senza_emittente` / `_senza_difesa` che
misurano l'invariante e oggi sono a **zero**. Un processo notturno non è più «il
DB che scrive»: è un utente con una veste e un perimetro. È la cosa che rende
onesta la RLS — senza, un batch la aggirerebbe e nessuno lo saprebbe.

⚠️ Resta un solo bypass, e **dichiarato**: `zeroerp_batch_fatturazione`
(`vw_processi_che_bypassano`, ritiro previsto alla fase 6-bis).

### 2.5 Domini nuovi

`pratiche` (23 tabelle, 72 funzioni — motore di workflow versionato), `documenti`
(10 tabelle — motore documentale parametrico), `ui` (12 tabelle — liste
configurabili come **dato**, non come DDL), `shop`/portale. Più la coda lavori
generica e il fan-out isolato.

⭐ `ui` merita una nota a sé: aver spostato la configurazione di una lista da
codice a dato — riga in `ui.lista_definizione` + N in `ui.lista_colonna` — è la
decisione che ha tolto di mezzo una classe intera di richieste.

### 2.6 Piattaforma

PostgreSQL 18, Liquibase 5, `daterange`/`tstzrange` nativi su 18 tabelle (con
`EXCLUDE` a presidiare le sovrapposizioni: 12 vincoli), `uuidv7()` come default.

---

## 3. I difetti che pesano oggi, in ordine di conseguenza

### ✅ D1 — Il cancello pgTAP in CI non misurava niente — CHIUSO il 2026-09-09

**Il difetto più grave del progetto**, e ha la forma esatta contro cui la guida
sui presidi mette in guardia.

Il passo «Suite pgTAP» di `.github/workflows/ci-validate.yaml` (nato il
**2026-08-07**, commit `82b6b1108`) ha due proprietà che si sommano:

1. `continue-on-error: true` — un rosso non ferma il merge;
2. legge la baseline da `db/pgtap/baseline-rossi-ci.tsv`. **Quel file non esiste
   e non è mai esistito** — verificato su tutta la storia del repo. Il passo
   prende quindi sempre il ramo «prima corsa»: `pgtap-baseline.sh --update`, la
   stampa nel log, `exit 0`.

⇒ **Da un mese la suite gira in CI e il suo esito viene buttato via.** Il
commento nel workflow dice cosa fare («copiala, committala, poi togli
`continue-on-error`»): è un bootstrap mai chiuso.

⛔ La conseguenza non è «un test rosso può passare». È che **600 file di test,
6.183 asserzioni e tutti i presidi scritti in pgTAP non difendono l'integrazione**.
Fra questi c'è `db/pgtap/rls/test-rls-viste-security-invoker.sql`, che è il
presidio meglio scritto del repo (criterio transitivo, casi costruiti, ha
sostituito quattro elenchi a mano il 2026-09-07) — e in CI non blocca niente.

⭐ **È il §6 punto 5 della guida sui presidi, applicato al contrario**: *«un
cancello che passa perché non ha misurato niente è peggio di un cancello
assente: dà la sensazione della copertura senza averla»*.

⚠️ Il resto della CI è invece **duro**: `continue-on-error` compare in un solo
punto di tutto `ci-validate.yaml`, ed è questo.

### ⭐ Il numero, misurato — e non è quello che sembrava

Il ramo di bootstrap **ha già girato**: la corsa `34259315648` (push su
`Tito-dev`, 2026-09-08 17:53) ha generato la baseline e l'ha stampata nel log.
Tre fatti che cambiano la forma del rimedio:

| | |
| --- | --- |
| Durata del passo pgTAP in CI | **2m09s** — non 7 minuti. Su un DB vuoto la gran parte dei file muore subito nella fixture. Corsa `ci-validate` completa: **7m24s** |
| Perimetro | **599 file** (`find -mindepth 2`, quindi anche le sottocartelle) |
| Esito | **411 rossi su 599** — il **69%** della suite. Verdi: 188 |
| Runner | `app`, cioè quello giusto |

⛔ **Committare quella baseline così com'è significa aprire un registro di debito
con 411 righe.** È la cosa che la guida sui presidi vieta esplicitamente al §6
punto 4: *«il registro nasce piccolo. Se parte con trenta righe, nessuno lo
leggerà»*. E con 411 righe congelate, il cancello proteggerebbe solo il 31%
residuo.

⛔ **E le 411 righe hanno tutte l'etichetta sbagliata.** Il classificatore di
`scripts/pgtap-baseline.sh:157` decide la causa con `grep -q "ERRORE:"` — la
stringa **italiana**. Il DB di sviluppo ha `lc_messages = it_IT.UTF-8` e la
riconosce; il container della CI (`postgis/postgis:18-3.6`) parla inglese e dice
`ERROR:`. Risultato: in CI **nessun rosso viene mai classificato
`ERRORE_FIXTURE`**, e infatti escono 411 `ASSERZIONE` su 411. Un file che non
esegue nemmeno una asserzione viene registrato come se ne avesse fallita una.

⭐ È il §4-bis della guida sui presidi in azione: *«un'etichetta rassicurante è
più pericolosa di un errore»*. La baseline di sviluppo (19 righe, di cui 11
`ERRORE_FIXTURE`) è corretta perché è stata presa su una macchina italiana. Il
metro cambia con la lingua del server.

### 🔴 E lo strumento che misura non falliva quando non poteva misurare

Trovato il **2026-09-09**, alla prima corsa sul database scratch della replica
CI (`scripts/ci-local.sh`, `CI_DB=zeroerp_ci`):

```text
pgTAP baseline — 600 file da eseguire — runner: app
Baseline aggiornata: db/pgtap/baseline-rossi-ci.tsv (600 rossi noti, runner: app)
```

**600 rossi su 600**, scritti come se fossero una misura. La causa era una riga
sola: su quel database non era mai stata eseguita `CREATE EXTENSION pgtap` —
nessun changelog la crea, in CI la fa il passo della suite, su sviluppo fu
installata a mano anni fa. Quindi ogni file moriva sulla prima istruzione, con
`la funzione plan(integer) non esiste`.

⛔ **Il danno sarebbe stato permanente.** Committato quel file, il cancello
della CI sarebbe partito con **l'intera suite dichiarata debito accettato**: da
lì in avanti nessun rosso nuovo può essere una regressione, perché sono già
tutti noti. Verde per sempre, e nessuno che sappia perché.

⭐ È il §6 punto 5 della guida sui presidi rivolto verso lo strumento che quella
guida presidia: *«fai fallire il controllo quando non può misurare»*.

✅ **Chiuso il 2026-09-09**: `pgtap-baseline.sh` in `--update` sulla suite intera
si rifiuta di scrivere quando **non passa nemmeno un file**, stampa le tre cause
tipiche e l'output completo del primo rosso. Non è una soglia arbitraria: se
zero file su 600 passano, la corsa non ha misurato la suite — ha misurato
l'ambiente. Su un sottoinsieme (`--update vendite`) avvisa e prosegue, perché
uno schema piccolo può essere tutto rosso per ragioni sue.
Verificato contro lo scratch ancora rotto: `exit 2`, baseline invariata
(stesso md5, 601 righe).

**Rimedio, in tre passi separati** — non è un'operazione sola:

1. ✅ **Fatto il 2026-09-09**: il classificatore ora legge
   `grep -qE "(ERRORE|ERROR):"`. Su dev le etichette non cambiano (verificato su
   un caso per ramo); in CI il ramo `ERRORE_FIXTURE` diventa raggiungibile per
   la prima volta.
2. Rilanciare, prendere la baseline **con le cause vere**, e a quel punto
   decidere: committare 411 righe, oppure triagiare prima le famiglie più grosse
   (`vendite` 214, `script` 50, `anagrafiche` 45, `pratiche` 37). ⭐ La domanda
   che decide è **quanti di quei 411 sono «il test cerca un soggetto nei dati
   esistenti»** — un difetto noto, sanabile in blocco — e quanti sono altro.
3. Togliere `continue-on-error` **solo dopo** una corsa di confronto verde.
   Prima, si blocca `Tito-dev` sul primo merge.

⚠️ Il passo 1 e il passo 3 sono economici; il passo 2 è un cantiere, e la sua
dimensione la dice il passo 1. **Ma finché non si fa nemmeno il passo 1, la
suite non difende niente**, e il costo di restare fermi cresce con ogni test
scritto.

### ✅ Com'è finita, il 2026-09-09

Tutti e tre i passi fatti in giornata. Il cancello è **armato**: da
`ci-validate.yaml` è sparito `continue-on-error`, e il ramo che generava la
baseline ora la genera, la stampa **e fallisce** — perché con il cancello acceso
un file sparito avrebbe riportato la CI a non misurare niente, in silenzio.

| | |
| --- | --- |
| Baseline della CI | **407 rossi su 601**, misurata dalla CI (corsa `34340793130`) |
| Prima corsa di confronto | **verde**, «nessuna regressione», numeri identici a due corse di distanza |
| Composizione | 344 `ERRORE_FIXTURE`, 63 `ASSERZIONE` |

⭐ **E strada facendo il conto è sceso da 485 a 407 senza sanare quasi nessun
test.** Tre correzioni d'ambiente, tutte della stessa natura — cose che su dbdev
esistevano perché messe a mano, e che su un database ricostruito dai changelog
non c'erano:

* il `GRANT USAGE` su `maintenance` al ruolo applicativo (§D5-bis, ora nel
  provisioning): senza, `plpgsql_check` non risolve `maintenance.*` e otto
  funzioni sane risultano riferimenti morti;
* lo schema `django`, che Liquibase non costruisce e che sul database scratch
  non arrivava affatto;
* il canale di log `dblink`, che sullo scratch puntava al database di **sviluppo**
  senza password: 151 file di `vendite` riportavano `2F003` al posto della
  propria causa. Non un rosso in più — un rosso che **mente**.

⚠️ Il difetto del classificatore (la stringa italiana) andava corretto **prima**
di tutto il resto: senza, quelle tre diagnosi non si sarebbero potute fare, e la
baseline sarebbe nata con 407 etichette sbagliate.

---

### 🔴 D2 — Il perimetro emittente si ferma alla testata

Delle sei famiglie di documento, **una sola è protetta fino in fondo**:

| Famiglia | Testata | Righe / satelliti |
| --- | --- | --- |
| `fatture` | ✅ 2 policy | ✅ `righe`, `scadenze`, `riepiloghi_iva`, `indirizzi`, `fondi_fattura_source` — tutte con 2 policy |
| `ordini` | ✅ 3 policy | ⛔ `ordini_righe`, `_componenti`, `_indirizzi`, `_fulfillment`: **nessuna** |
| `preventivi` | ✅ 1 policy | ⛔ `preventivi_righe`, `_componenti`, `_indirizzi`, `_riepiloghi_iva`: **nessuna** |
| `ddt` | ✅ 1 policy | ⛔ `ddt_righe`, `_componenti`, `_indirizzi`: **nessuna** |
| `contratti` | ✅ 1 policy | ⛔ `contratti_righe`, `_componenti`, `_indirizzi`, `_utilities`: **nessuna** |
| `resi` | ✅ 1 policy | ⛔ `resi_righe`, `_accrediti`, `_riconsegne`, `_rinunce`: **nessuna** |

`zeroerp_app` ha `SELECT, INSERT, UPDATE, DELETE` su tutte le figlie scoperte.

⛔ **Non è un difetto teorico**: `vendite.vw_preventivi_righe_dettaglio` legge
`preventivi_righe` **senza passare dalla testata** (lo si vede dalle sue
dipendenze: `catalogo.articoli`, `unita_misura`, `config.iva`,
`vendite.preventivi_righe` — la tabella `preventivi` non c'è). Quella vista è
concessa in `SELECT` a `zeroerp_app`. Articolo, quantità, prezzo e descrizione
delle righe di preventivo di **ogni** emittente passano da lì.

⭐ **La forma giusta esiste già, scritta e collaudata**: gli helper
`script.fn_scope_ef_whitelist_via_fattura` e i cinque satelliti di `fatture`.
Non c'è niente da progettare: c'è da estendere. Manca l'helper `_via_<testata>`
per le altre cinque famiglie, che è lo stesso `EXISTS` con un `JOIN` diverso.

⭐ **Il dettaglio che chiude il ragionamento**: delle 60 viste di `vendite`, **58
hanno `security_invoker`**. Le due che non ce l'hanno sono
`vw_preventivi_righe_dettaglio` e `vw_preventivi_riepilogo_iva_dettaglio` — cioè
**esattamente le due che leggono i satelliti di `preventivi`**. Il presidio del
`security_invoker` (D5, il migliore del repo) su di esse **tace legittimamente**,
perché il suo criterio è «tocca dati protetti da RLS» e quei dati protetti non
sono. *La difesa di secondo livello si spegne da sola quando manca quella di
primo.*

⚠️ **E il modello lo ammette per costruzione**: una riga di documento *ha* un
emittente — quello della sua testata. Che oggi il frontend passi sempre dalla
testata non è un argomento: è il ramo che non ha ancora un controesempio.

---

### 🔴 D3 — `storico` è interamente fuori dal perimetro

120 tabelle in `storico`, **zero con RLS**, **zero policy**, e **52** con
`SELECT` a `zeroerp_app`. Fra queste `storico.fatture`, `storico.fatture_righe`,
`storico.commesse`, `storico.contratti`, `storico.ordini`, `storico.preventivi`,
`storico.ddt`, `storico.resi`.

⛔ Il dato vivo di `vendite.fatture` è protetto da due policy. **Ogni sua
versione precedente non lo è.** La storicizzazione è automatica e cattura lo
snapshot completo della riga: chi non può vedere una fattura può leggerne tutte
le revisioni.

⭐ La difesa qui non è una policy per tabella (120 sarebbero ingestibili e
nascerebbero disallineate): è che lo **stesso framework** che genera la tabella
storico e il suo trigger generi anche la policy, derivando lo scope dalla tabella
madre. `dbops.fn_run_automations_storico` + `fn_ensure_storico_table` sono già il
posto: l'automazione sa quale madre sta specchiando.

⚠️ **Stessa classe, secondo caso**: `dbops.audit_log` è il registro delle
esecuzioni di funzione, con `params` e `result` in JSONB — cioè, per le funzioni
di dominio, gli **argomenti e l'esito** di operazioni su documenti protetti. È
senza RLS e `zeroerp_app` ha `SELECT, INSERT, UPDATE, DELETE`. Non è grave quanto
`storico` (non contiene lo snapshot completo della riga), ma è la stessa forma:
*il dato è protetto, la sua traccia no*.

⚠️ Corollario: finché `storico` è aperto, chiudere D2 non chiude il buco —
sposta solo il punto da cui si legge.

---

### 🟠 D4 — Tre tabelle hanno una policy e la RLS spenta

`acquisti.ddt`, `acquisti.ordini`, `shop.ricevute`: `pg_policy` ha la riga,
`relrowsecurity` è `false`. **La policy non filtra niente.**

⛔ È il difetto che si auto-nasconde: chi verifica con `EXISTS (SELECT 1 FROM
pg_policies …)` legge verde. La policy *esiste*. Non è **accesa**.

⚠️ E non c'è nessun invariante pgTAP che asserisca `relrowsecurity` in generale:
la colonna compare in cinque file, sempre dentro un test su una tabella
specifica. Vedi D5, che è la stessa cosa detta bene.

---

### 🟠 D5 — Il criterio con cui nasce un presidio è un indicatore in ritardo

Tre invarianti della stessa famiglia — «una proprietà strutturale che, se
violata, non produce nessun errore visibile»:

| Invariante | Presidiato? |
| --- | --- |
| Una vista che tocca dati in RLS ha `security_invoker` | ⭐ **sì, e benissimo**: criterio transitivo, casi costruiti, ha sostituito quattro elenchi a mano (2026-09-07). Oggi è a zero violazioni |
| Una tabella con policy ha la RLS **accesa** | ⛔ no — 3 violazioni (D4) |
| Una funzione `SECURITY DEFINER` ha un `search_path` fisso | ⛔ no in generale — asserito **caso per caso** (`maintenance.fn_job_run_start/_end`, due in `vendite`, una in `script`). 3 violazioni (D6) |

⭐ **La differenza fra la riga 1 e le altre due non è tecnica: è che la prima ha
morso.** Il progetto costruisce un presidio quando un difetto si è già
manifestato — è un ottimo riflesso, ma è un criterio che arriva sempre **dopo**.
Le altre due non hanno ancora morso, e infatti sono già violate.

**Rimedio**: un pgTAP unico «postura di sicurezza», con i tre criteri scritti
come invarianti generali sul catalogo (non elenchi di nomi) e i debiti
**dichiarati** con la loro ragione tecnica — la forma è già quella del file
`security_invoker`, va copiata.

---

### 🟠 D6 — Tre `SECURITY DEFINER` di `postgres`, eseguibili da chiunque, senza `search_path`

| Funzione | Owner | `EXECUTE` | `search_path` |
| --- | --- | --- | --- |
| `dbops.fn_generate_tx_id` | `postgres` | **PUBLIC** | ⛔ nessuno |
| `dbops.fn_get_or_create_session_tx_id` | `postgres` | **PUBLIC** | ⛔ nessuno |
| `dbops.fn_sync_functions_owner` | `postgres` | **PUBLIC** | ⛔ nessuno |

La seconda sta sul percorso di scrittura di **305 trigger `tx_id`**, cioè quasi
ogni scrittura del sistema. La terza **cambia il proprietario di funzioni**.

⚠️ **Onestà sulla gravità**: non è sfruttabile oggi. I corpi qualificano quasi
tutto (`dbops.transaction_ids`, `script.fn_ensure_logconn()`, `script.uuid_nil()`);
l'unica chiamata non qualificata è `dblink(...)`, e per dirottarla servirebbe
`CREATE` su uno schema nel `search_path` del chiamante — che `zeroerp_app` non ha
(solo `USAGE` su `public`). Le funzioni non si risolvono da `pg_temp`.

⛔ **Ma la difesa è tutta in un GRANT che nessun presidio verifica.** Il giorno in
cui a un ruolo servisse `CREATE` da qualche parte, o si installasse un'estensione
in uno schema scrivibile, tre funzioni con i privilegi del superutente
diventerebbero una scala. `SET search_path = pg_catalog, pg_temp` costa una riga
per funzione ed è la postura che il progetto già applica altrove.

⚠️ Seconda faccia, meno visibile: le `SECURITY DEFINER` proprie sono **38** e il
`search_path` ha **cinque forme diverse**:

| Forma | Quante |
| --- | --- |
| `pg_catalog, public` | 16 |
| `pg_catalog, pg_temp` | 8 |
| `public, pg_temp` | 5 |
| `pg_catalog, pratiche, script, config, dbops, pg_temp` | 4 |
| `pg_catalog, anagrafiche, config, script` | 2 |
| *(nessuno)* | 3 |

In **18 su 38** `pg_temp` non è elencato — e quando non è elencato PostgreSQL lo
cerca **per primo** per le relazioni. Non è una preferenza di stile: è un pezzo di
semantica. In altre 5 `public` viene **prima** di `pg_catalog`, che è l'ordine
opposto a quello prudente.

---

### 🟠 D7 — La copertura dei test non è bassa: è concentrata

600 file, ~6.183 asserzioni. Il numero non dice niente; la distribuzione sì.

| | mai nominato in un pgTAP | totale |
| --- | --- | --- |
| **Funzioni** | **315** | 829 (38%) |
| **Tabelle** | **83** | 372 (22%) |

*(«mai nominato» è la soglia più generosa possibile: essere nominato non
significa essere collaudato. È un limite inferiore.)*

Per schema, i file di test: `vendite` 253, `script` 69, `anagrafiche` 66,
`pratiche` 43, `config` 33, `dbops` 32, `rls` 22, `pagamenti` 17, `catalogo` 15,
`ui` 13, `documenti` 11, `maintenance` 5, **`magazzino` 1**, **`shop` 1**,
**`acquisti` 0**, **`storico` 0**.

⚠️ E la copertura dichiarata è più alta di quella reale per due motivi già
scritti nella guida sui presidi: **110 file** contengono uno `skip()`
condizionato (su un DB ricostruito da zero si saltano, e un test saltato conta
verde), e il debito `throws_ok` senza discriminante è a **131** — un
`throws_ok(sql, NULL, NULL)` accetta *qualunque* errore, compreso quello
sbagliato.

### 🔴 Il numero che conta davvero, e adesso è misurato

Su un database **ricostruito da zero** — cioè quello di cui si ha bisogno il
giorno in cui si prepara un'installazione nuova — la corsa in CI del 2026-09-08
dà **411 file rossi su 599**:

| Schema | Rossi | | Schema | Rossi |
| --- | --- | --- | --- | --- |
| `vendite` | 214 | | `documenti` | 6 |
| `script` | 50 | | `dbops` | 6 |
| `anagrafiche` | 45 | | `catalogo` | 6 |
| `pratiche` | 37 | | `ui` | 5 |
| `config` | 16 | | `maintenance` | 2 |
| `pagamenti` | 15 | | | |
| `rls` | 9 | | **Totale** | **411 / 599** |

⛔ **La suite è verde al 31% fuori dalla macchina di sviluppo.** Non è una
sorpresa concettuale — la guida sui presidi §4 lo dice da mesi («69 file su 437
contengono un salto condizionato… su un database vuoto non falliscono: si
saltano») — ma il numero non era mai stato preso, ed è **sei volte** quella
stima.

⚠️ E il difetto vero non è il 69%: è che quei 411 file **passano sul DB di
sviluppo**. Cioè la suite oggi verifica in larga parte *lo stato di una
macchina*, non che le migrazioni sappiano ricostruirla. Sono due proprietà
diverse, e la seconda è quella che serve al secondo cliente.

⭐ Non tutti i 411 sono lo stesso problema, e la ripartizione oggi **non si sa**:
il classificatore delle cause è cieco in CI (§D1). Saperla è il primo passo, e
costa una riga di codice.

⛔ Sommato a D1: la copertura reale è molto più bassa di quella nominale, **e
nessuno dei due numeri ferma un merge**.

---

### 🟠 D8 — `acquisti` e `magazzino`: modellati, non scritti

| Schema | Tabelle | FK | CHECK | Funzioni | Viste | Test |
| --- | --- | --- | --- | --- | --- | --- |
| `magazzino` | 26 | 57 | 71 | **2** | 4 | **1** |
| `acquisti` | 9 | 42 | 25 | **2** | 0 | **0** |
| `vendite` (confronto) | 88 | 359 | 194 | 292 | 60 | 253 |

⭐ Il modello c'è, ed è curato: 71 CHECK su `magazzino` non sono di un abbozzo.
Manca lo **strato di comportamento**. In un progetto DB-first questo è un tipo
preciso di debito: le regole che *non* sono esprimibili come vincolo non hanno
ancora un posto dove stare, e quando arriveranno la pressione sarà di scriverle
nel backend — cioè fuori dal modello architetturale dichiarato.

⚠️ E l'asimmetria con `vendite` non è un accidente di priorità: `acquisti`
specchia il ciclo vendite, quindi ogni decisione presa di là (numerazione, serie,
perimetro emittente, righe senza prezzo, lineage) **è una decisione presa anche
di qua, che qui non è ancora scritta**. Più cresce `vendite`, più cresce il debito
di `acquisti` senza che nessuno lo tocchi.

**Controesempio vivo** (l'unica misura di popolazione di questo documento, e vale
come tale): `dbops.vw_coda_lavori_da_guardare` contiene **6 lavori
`CHIUSURA_SCADENZE` in stato `ERRORE`, tentativi esauriti, da tre notti
consecutive** (7, 8 e 9 settembre), tutti con lo stesso `ValueError` Python. Il
presidio ha fatto il suo mestiere; nessuno l'ha letto. Vedi D10.

---

### 🟡 D9 — Il guard generico non scala per figlia, e il progetto sa già come si fa

`catalogo.articoli` ha **46 trigger**. La rilettura è importante: non sono 46
scelte diverse, sono **due pattern istanziati una volta per figlia** —
`trgfn_prevent_deactivate_if_children` ×29 (BEFORE ROW) e
`trgfn_child_requires_active_parent` ×8 (AFTER ROW), più i 3 di
audit/`tx_id`/storico, 2 `lock_columns` e 4 guard specifici di dominio.

⇒ **Ogni `UPDATE` su una riga di `catalogo.articoli` esegue 29 query `EXISTS`
sequenziali**, una per tabella figlia. In tutto il DB: 2.035 trigger, di cui
**758** sono queste due funzioni.

⭐ **Il progetto ha già la forma alternativa e l'ha già usata**: la primitiva
unica che ricava le figlie da `pg_constraint` invece di essere montata una per
figlia (è il pattern del cleanup). Non è un'invenzione da valutare: è
un'**incoerenza interna** fra due parti dello stesso framework.

⚠️ Effetto collaterale del numero: i nomi arrivano al limite di 63 caratteri e
vengono troncati con un hash (`…_articoli_descrizioni_aggiuntive_block_d_315e77`).
Un nome troncato non dice più cosa fa il trigger — e **l'ordine di scatto è
governato dal nome**.

Che porta al secondo pezzo: la **fase** (`_a10_` / `_z90_`) è presente su
**1.335 trigger su 2.035** — il **66%**. Per un terzo dei trigger l'ordine
relativo è quindi accidentale, deciso dall'alfabeto di una descrizione. Su un
sistema dove due guard `BEFORE ROW` parlano in ordine alfabetico, non è cosmesi.

**Aderenza naming, per completezza** (2026-09-08): prefisso `trg_` 2.030/2.035
(99,8%); suffisso evento 1.745/2.035 (85,8%); `fk_` 822/857 (95,9%); `chk_`
563/599 (94,0%); `uq_` 336/339 (99,1%); `pk_` 316/374 (84,5%); `ix_` 558/612
(91,2%). Il 94% dichiarato a febbraio regge — **tranne la fase**, che era la voce
con più conseguenze e non era misurata.

---

### 🟡 D10 — I presidi non hanno un destinatario

30 viste di presidio in `dbops`. Nessun canale che le porti davanti a una persona
su base regolare: nessun digest, nessun job che le legga e sollevi, nessuna
pagina che le mostri.

⚠️ La prova è D8: sei lavori falliti da tre notti, visibili in una vista fatta
apposta per mostrarli, nome `vw_coda_lavori_**da_guardare**`. Il presidio
funziona. **Guardare non è di nessuno.**

⭐ Il costo del rimedio è basso e la forma esiste già: la coda lavori sa accodare,
`config.fn_accoda_email_sistema` sa spedire. Serve un processo che legga le viste
non-vuote e mandi un digest — e la disciplina di **tenerle a zero**, perché una
lista che è sempre lunga smette di essere letta (è il §4-bis della guida sui
presidi, applicato a sé stessi).

---

### 🟡 D11 — I registri di debito non calano

Un registro di debito è una buona invenzione **a condizione che scenda**. Stato
al 2026-09-08:

| Registro | Oggi |
| --- | --- |
| `dbops.vw_codici_errore_da_dichiarare` | **508** su 852 codici |
| `dbops.vw_fk_con_indice_missing_policy` | **57** |
| `SOGLIA_THROWS_SENZA_DISCRIMINANTE` | **131** |
| `db/pgtap/baseline-rossi.tsv` | **19** file (11 `ERRORE_FIXTURE`, 8 `ASSERZIONE`) |
| `backend/scripts/tests/baseline-smoke.tsv` | 2 su 11 |
| Header di licenza mancanti | 2.042 file (misura 2026-08-26) |
| `dbops.vw_indici_ridondanti_prefisso` | 1 |
| Codici vivi senza messaggio | 6 (tutti `W_`, §2.3) |
| `dbops.vw_processi_che_bypassano` | 1 (dichiarato, con data di ritiro) |

⭐ L'ultima riga è l'unica fatta bene: **una** voce, con il motivo e il momento in
cui sparisce. Le prime quattro sono liste lunghe, e la guida sui presidi dice
esattamente perché è un problema: *«il registro nasce piccolo. Se parte con
trenta righe, nessuno lo leggerà»*.

⚠️ I 19 file in baseline meritano una riga a parte: **11 falliscono nella
fixture**, cioè non eseguono **nessuna** asserzione. La loro copertura vale zero,
non «parziale» — e sono aree che *sembrano* coperte.

---

### 🟡 D12 — Documentazione: il problema non è più la quantità

1.410 pagine manuali contro 1.500 auto-generate: copertura sostanzialmente piena,
il gap di febbraio è chiuso. Restano due cose:

* `storico`: 111 pagine, media 15 righe, **98 sotto le 12 righe**. Sono specchi
  auto-generati, e va bene — ma gonfiano il conteggio di copertura del 7%;
* `magazzino` (35 righe/pagina) e `acquisti` (36) hanno pagine **presenti e
  sottili**. Coerente con D8: si documenta poco ciò che fa poco.

⚠️ E un debito documentale trovato scrivendo questo documento:
`.codex/AGENTS.md` §Test descrive `db/pgtap/baseline-rossi-ci.tsv` come esistente
e in uso («usa una baseline **sua**»). **Non esiste** (D1). È esattamente il caso
in cui il debito documentale si verifica **rileggendo il file**, non fidandosi
della frase.

---

## 4. Cosa NON è un difetto

* ⛔ **`contabilita` vuoto.** Fuori perimetro per decisione: se servirà, sarà un
  aggancio a una contabilità esterna, con la forma dettata dal sistema di
  destinazione. Zero test su zero oggetti non è un gap.
* ⛔ **Il numero di trigger per tabella, di per sé.** È la conseguenza del numero
  di figlie. Il difetto è la *forma* del pattern (D9), non il conteggio.
* ⚠️ **Il mix `VARCHAR + CHECK` vs tabella-lookup.** Febbraio chiedeva una guida:
  il criterio è oggi scritto in `linee-guida-sql.md` §«esiste già una chiave
  stabile per-design?» e in memoria (JSONB vs tabella-vocabolario). Voce chiusa.
* ⚠️ **`relforcerowsecurity = false` ovunque.** È corretto: l'owner deve poter
  fare manutenzione. Il pgTAP che deve esercitare le policy accende `FORCE` da
  sé. Non confondere questo con D4, che è tutt'altro.
* ⚠️ **Il `makefile` locale usa `--contexts="!test AND !provision"`** e quindi
  carica anche `dati_macchina`, mentre la CI usa
  `--contexts="!provision and !dati_macchina"`. È **voluto**: sul DB di sviluppo i
  dati di macchina servono.

---

## 5. Scorecard 2026-09-08 — pesata, non mediata

Il peso è **la conseguenza di un difetto in quell'area**, non la sua estensione.

| Area | Peso | Voto | Perché |
| --- | --- | --- | --- |
| **Catena di verifica (CI)** | 🔴 alto | **7,5/10** ⬆ | ✅ 2026-09-09: la suite è un cancello vero — baseline misurata dalla CI, `continue-on-error` tolto, il ramo di bootstrap fallisce invece di passare. Resta il registro a 407, che deve calare (D1, D7) |
| **Perimetro dei dati (RLS)** | 🔴 alto | **5/10** | Progettato bene, applicato a un sesto del dominio documento e a zero dello storico (D2, D3, D4) |
| **Copertura test** | 🔴 alto | **4/10** | 600 file e ~6.183 asserzioni, ma su un DB ricostruito da zero **la suite è verde al 31%** (411 rossi su 599, misurato). Il 38% delle funzioni non è mai nominato (D7) |
| **Postura di sicurezza degli oggetti** | 🟠 medio | **6,5/10** | `security_invoker` presidiato benissimo; `relrowsecurity` e `search_path` no (D5, D6) |
| **Simmetria del dominio** | 🟠 medio | **4/10** | `acquisti` e `magazzino` modellati e non scritti, e il debito cresce da solo (D8) |
| **Osservabilità dei presidi** | 🟠 medio | **4/10** | 30 viste, nessun destinatario (D10) |
| **Gestione del debito** | 🟠 medio | **6/10** | Registri ben progettati, quattro su otto troppo lunghi per essere letti (D11) |
| **Pattern trigger e automazioni** | 🟡 basso | **7,5/10** | Riuso raro (758 trigger da due funzioni), framework `ci_apply` eccellente; la forma per-figlia non scala e la fase è al 66% (D9) |
| **Error handling / codici errore** | 🟡 basso | **8,5/10** | Contratto a tre lati esplicito e presidiato; il registro non cala |
| **Disciplina Liquibase** | 🟡 basso | **9/10** | 3.354 changeSet, cinque cancelli dedicati, tutti nati da un incidente reale |
| **Documentazione** | 🟡 basso | **8,5/10** | Copertura piena; sottile dove il dominio è sottile |
| **Naming** | 🟡 basso | **8/10** | 94-99% sui vincoli; 66% sulla fase dei trigger, che è la voce con conseguenze |

### Il giudizio, in una frase

⭐ **Il metodo di ingegneria di questo progetto è sopra la media del settore** —
la guida sui presidi, il contratto a tre lati dei codici errore, il framework
delle automazioni per pattern e il passaggio dei pgTAP al ruolo applicativo sono
cose che in un ERP non si vedono quasi mai.

⛔ **E la catena che dovrebbe rendere vero tutto questo è interrotta in un punto
solo.** Finché la suite non blocca un merge (D1), ogni presidio scritto in pgTAP
— compresi i migliori — è una dichiarazione di intenti.

⚠️ **E il primo giro di quella catena dirà una cosa scomoda**: fuori dalla
macchina di sviluppo la suite è verde al **31%**. Non è una regressione — è
sempre stato così, e adesso è misurato. La differenza fra «i test passano» e «le
migrazioni sanno ricostruire un sistema che passa i test» è tutta lì dentro.

⚠️ **«Production-ready» non è la parola giusta oggi**, e non per la qualità del
design: per D1, D2 e D3. Un sistema multi-emittente in cui le righe di cinque
famiglie di documento su sei e tutto lo storico sono leggibili da chiunque non è
pronto per un secondo cliente sulla stessa macchina. Chiusi quei tre, la frase
torna difendibile — e sono tre cantieri delimitati, non una riscrittura.

---

## 6. Checklist, in ordine di ritorno

### 🔴 Prima di tutto il resto

* [x] **D1-a** — ✅ **fatto il 2026-09-09**: `scripts/pgtap-baseline.sh` ora
      classifica con `grep -qE "(ERRORE|ERROR):"`, con il motivo scritto accanto.
      Verificato su dev che nessuna delle due etichette cambia:
      `documenti/test-documenti-template-documenti.sql` resta `ERRORE_FIXTURE`,
      `script/test-seed-stati-doc-ordini-evaso-v1.sql` resta `ASSERZIONE`.
      ⚠️ La baseline di sviluppo **non va rigenerata**: era già corretta, presa
      su una macchina italiana.
* [x] **D1-b** — ✅ **fatto**: baseline della CI committata, **407 rossi su 601**,
      misurata dalla CI e non in locale (lo scratch diverge su 11 file).
      344 `ERRORE_FIXTURE` + 63 `ASSERZIONE`.
* [x] **D1-c** — ✅ **fatto**: `continue-on-error` tolto dopo una corsa di
      confronto verde. E il ramo del bootstrap ora **fallisce** dopo aver
      stampato la baseline: un file sparito non deve poter spegnere il cancello
      in silenzio.
* [x] **D1-bis** — ~~correggere `.codex/AGENTS.md` §Test~~. **Cade da sé**: la
      frase «usa una baseline sua, `db/pgtap/baseline-rossi-ci.tsv`» diventa vera
      nel momento in cui il file è committato (D1-b), e la frase «in CI la suite
      gira» diventa vera davvero con D1-c. Non ha senso correggere il documento:
      ha senso rendere vero ciò che dice. ⚠️ Se D1-b slitta oltre una settimana,
      allora sì — la nota va messa, perché un documento che mente costa più della
      riga che lo corregge.

### 🔴 Il perimetro

* [ ] **D2** — cinque helper `script.fn_scope_ef_whitelist_via_<testata>` +
      policy sulle figlie di `ordini`, `preventivi`, `ddt`, `contratti`, `resi`.
      Modello da copiare: la famiglia `fatture`.
* [ ] **D3** — generare la policy dello storico **dall'automazione**, derivando
      lo scope dalla madre (`fn_run_automations_storico` / `fn_ensure_storico_table`).
* [ ] **D4** — accendere la RLS su `acquisti.ddt`, `acquisti.ordini`,
      `shop.ricevute` (o ritirare le policy, se quelle tabelle non sono nel
      perimetro: ma allora va scritto).
* [ ] **D5** — un pgTAP «postura di sicurezza» con i tre invarianti generali
      (`security_invoker` c'è già; aggiungere `relrowsecurity` e `search_path`
      sui `SECURITY DEFINER`), debiti **dichiarati con la ragione tecnica**.
* [ ] **D6** — `SET search_path` sulle tre `dbops.fn_*` di `postgres`; valutare
      il ritiro di `EXECUTE` a PUBLIC su `fn_sync_functions_owner`.
* [ ] **D6-bis** — scegliere **una** forma canonica di `search_path` per le
      `SECURITY DEFINER` (`pg_catalog, <schemi necessari>, pg_temp`, con
      `pg_temp` sempre ultimo ed esplicito) e allineare le 18 che oggi non
      elencano `pg_temp` e le 5 che mettono `public` prima di `pg_catalog`.

### 🟠 La sostanza

* [ ] **D8** — decidere se `acquisti`/`magazzino` sono un cantiere aperto o
      congelato, e **scriverlo**. Un dominio a metà senza data è il debito che
      cresce senza che nessuno lo tocchi.
* [ ] **D10** — un digest periodico delle viste di presidio non vuote; e come
      prima cosa, guardare i sei `CHIUSURA_SCADENZE` in errore.
* [ ] **D7** — portare a zero gli 11 file in baseline che falliscono nella
      *fixture*: sono le aree che sembrano coperte e non lo sono.
* [ ] **D11** — dare a ciascun registro lungo un **verso** (chi lo abbassa, di
      quanto, entro quando), o dichiararlo congelato con il motivo.
* [ ] **D11-bis** — scrivere il messaggio dei sei `W_` che non ce l'hanno
      (append al CSV dei messaggi, mai un loader nuovo), oppure dichiarare che
      quei codici non raggiungono mai un operatore — e scriverlo nel `note`.

### 🟡 Struttura

* [ ] **D9** — valutare la primitiva unica «figlie da `pg_constraint`» al posto
      dei guard per-figlia, partendo da `catalogo.articoli` (29 `EXISTS` per
      update).
* [ ] **D9-bis** — portare la fase (`_a10_`/`_z90_`) sul 34% di trigger che non
      ce l'ha, o dichiarare che per quelli l'ordine è indifferente.
* [ ] **D12** — nessuna azione: la documentazione seguirà il dominio.

---

*Valutazione 2026-09-08 — perimetro DB. Le misure sono letture di struttura sul
database di sviluppo `zeroerp` (PostgreSQL 18.6) e sul repo al commit `89d36ad1b`,
branch `dev/db-tid`. La valutazione di febbraio 2026 resta in §1 come fatto
datato.*
