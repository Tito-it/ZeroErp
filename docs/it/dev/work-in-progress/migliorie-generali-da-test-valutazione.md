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
>
> ✅ **Sfoltito il 2026-09-12.** Le voci chiuse fra l'8 e l'11 settembre — D1,
> D2, D3, D10, la decisione di D8 e la metà di D4/D5 — sono ridotte a **data di
> chiusura, stato attuale e rimando al brief**. Il dettaglio di com'erano e di
> come si è arrivati a chiuderle sta nei brief citati e nella storia git di
> questo file: qui avrebbe fatto sembrare il documento vecchio. Le voci aperte
> restano com'erano al 2026-09-08, con i numeri aggiornati dove il registro sta
> nel repo (e allora con la data).

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
esistono, quali GRANT, quale `search_path`, cosa contiene un file di CI o un
registro nel repo — e sono **fatti datati**: 2026-09-08 dove non è scritto
altrimenti.

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
dopo era ancora l'allarme — non perché i test non fossero cresciuti (94 → **600
file**, ~6.183 asserzioni), ma perché il problema non era il numero: era che
**nessuno li faceva contare**. Vedi §3 D1 (chiuso il 2026-09-09).

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

⚠️ **Ed era anche l'area con il difetto peggiore** (D2, D3): costruita bene dove
era finita, ed era finita su **una famiglia di documenti su sei**, con lo storico
interamente fuori. ✅ Chiusi entrambi l'11-09-2026: il dominio documento è
protetto fino ai satelliti e ogni versione di storico porta lo scope congelato.
Resta D4 (tre policy inerti, a registro).

### 2.2 ⭐ I presidi e i registri del debito — un artefatto raro

`docs/it/guide/presidi-e-registri-del-debito.md` non è documentazione: è una
teoria di come un controllo mente. Il §4-bis («una regola che mente», con il caso
delle sedici chiamate rotte zittite da un'etichetta rassicurante) e il §6 punto 5
(«fai fallire il controllo quando non può misurare») sono il genere di cosa che
in un progetto normale non si scrive mai.

⛔ **E il difetto principale di questo documento (D1, chiuso il 2026-09-09) era
la violazione del §6 punto 5 di quella stessa guida.** Il progetto aveva scritto
la regola e non l'aveva applicata al proprio cancello più costoso.

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

Il passo «Suite pgTAP» di `ci-validate.yaml` (nato il 2026-08-07) girava con
`continue-on-error: true` e leggeva una baseline che non era mai stata
committata: l'esito di 600 file e ~6.183 asserzioni veniva buttato via a ogni
corsa. Era il §6 punto 5 della guida sui presidi applicato al contrario — *un
cancello che passa perché non ha misurato niente è peggio di un cancello
assente*.

✅ **Chiuso il 2026-09-09**, tutto nello stesso giorno:

* `scripts/pgtap-baseline.sh` classifica con `grep -qE "(ERRORE|ERROR):"` — il
  server della CI parla inglese, e con la sola stringa italiana nessun rosso
  poteva risultare `ERRORE_FIXTURE`. E in `--update` sulla suite intera **si
  rifiuta di scrivere** se non passa nemmeno un file: una corsa a zero verdi ha
  misurato l'ambiente, non la suite (esattamente ciò che sarebbe successo sullo
  scratch senza `CREATE EXTENSION pgtap`: 600 rossi su 600, committati per
  sempre come debito noto);
* `db/pgtap/baseline-rossi-ci.tsv` committato, **misurato dalla CI** e non in
  locale (407 rossi su 601 alla prima corsa);
* `continue-on-error` tolto dopo una corsa di confronto verde, e il ramo di
  bootstrap ora **fallisce** dopo aver stampato la baseline: un file sparito non
  può spegnere il cancello in silenzio.

⚠️ Quello che resta è il registro, che deve calare: **403 righe al 2026-09-12**
(323 `ERRORE_FIXTURE`, 80 `ASSERZIONE`) → D7.

---

### ✅ D2 — Il perimetro emittente si fermava alla testata — CHIUSO l'11-09-2026

Delle sei famiglie di documento di `vendite`, una sola (`fatture`) era protetta
fino a righe e satelliti; le altre cinque avevano la policy sulla testata e
**nessuna** sulle figlie, con `zeroerp_app` in `SELECT, INSERT, UPDATE, DELETE`
su tutte — e almeno una vista (`vw_preventivi_righe_dettaglio`) le leggeva
senza passare dalla testata. Una riga di documento *ha* un emittente, quello
della sua testata: il modello lo ammetteva per costruzione.

✅ **Chiuso l'11-09-2026** — brief
`work-done/brief-db-perimetro-emittente-righe-documento.md`: **nove famiglie
armate** (non le cinque della voce: un elenco scritto a mano non è un perimetro,
e a quello mancavano sei figlie di `fatture` e le sette partizioni di
`vendite.note`), registro del debito da 33 a **10 righe**, `db/pgtap/rls/` da
30 a 39 file.

⭐ Ne è rimasto in servizio un **presidio a criterio transitivo** —
`dbops.vw_rls_perimetro_scoperto` + `dbops.rls_perimetro_debito` +
`db/pgtap/rls/test-rls-perimetro-scoperto.sql`: una tabella nuova con una FK
verso una protetta esce `NON_DICHIARATO` e fa rosso il test 2.

⚠️ Le 10 righe che restano non sono D2 non finito: sono decisioni di modello su
chiavi nullable, la domanda gemella del legame emittente-BA e i cantieri di
`acquisti`/`shop` (→ D4, D8), ognuna con la ragione scritta nel registro.

---

### ✅ D3 — `storico` era interamente fuori dal perimetro — CHIUSO l'11-09-2026

120 tabelle in `storico`, zero con RLS, 52 con `SELECT` a `zeroerp_app`: il
dato vivo di `vendite.fatture` era protetto da due policy, **ogni sua versione
precedente no**. Chiudere D2 senza D3 avrebbe solo spostato il punto da cui si
legge.

✅ **Chiuso l'11-09-2026** (applicato alle 19:54, pgTAP senza regressioni) —
brief `work-done/brief-db-rls-storico-scope-congelato.md`. Lo scope **non si
deriva a runtime dalla madre: si cattura alla scrittura e si congela** in
`origine_schema` + `scope_emittente_fiscale_id` (mappa
`dbops.storico_scope_policy`, ripiego sull'archivio del padre). Le **37** shadow
delle madri protette hanno policy generate (`FOR SELECT` sull'emittente
congelato, scrittura del trigger libera); backfill di 65.751 versioni, zero
residue; l'applicazione non può cancellare una versione (`REVOKE DELETE` su
tutto lo schema). Le tabelle nuove nascono armate dal generatore, e
`dbops.vw_storico_scope_da_dichiarare` (settimanale, dal 12-09) vede quelle che
non lo sono. Il lavoro è stato **uno**, non 120: la forma delle shadow è
uniforme e generata.

✅ **`dbops.audit_log`** — stessa famiglia, rimedio diverso, chiuso anch'esso
l'11-09 (brief §8). Non è un registro di dominio: ci scrivono solo `dbops` e
`maintenance`. Quindi il presidio non è una policy ma un **cancello** alla
scrittura — `dbops.vw_audit_log_scrittori_fuori_perimetro`, natura CANCELLO a
catalogo — più il **REVOKE di `UPDATE`/`DELETE`** all'app, dichiarato nel loop
dei grant (`v_registri_append_only`, con `dbops.error_log`): *un registro di
audit modificabile da chi è auditato non è un registro.*

---

### ✅ D4 — Tre tabelle avevano una policy e la RLS spenta — CHIUSO il 2026-09-12 (per la parte che era D4)

`acquisti.ddt`, `acquisti.ordini`, `shop.ricevute`: `pg_policy` ha la riga,
`relrowsecurity` è `false`. **La policy non filtra niente.**

⛔ È il difetto che si auto-nasconde: chi verifica con `EXISTS (SELECT 1 FROM
pg_policies …)` legge verde. La policy *esiste*. Non è **accesa**.

✅ **L'invariante generale è presidiato dall'11-09-2026** (cantiere D2): è il
criterio `POLICY_INERTE` di `dbops.vw_rls_perimetro_scoperto`, con il caso
costruito nel test 7 di `test-rls-perimetro-scoperto.sql`. Le tre tabelle sono
le sue tre righe di debito dichiarato, e il registro dice **perché** non si
accendono:

* `acquisti.ddt` e `acquisti.ordini` hanno una policy di **sola veste
  `FORNITORE_PORTALE`** e **nessuna colonna emittente**: la RLS è default-deny,
  accenderla renderebbe le due tabelle invisibili e non scrivibili
  all'**operatore**, che ci ha `SELECT/INSERT/UPDATE/DELETE`. ⇒ *Manca il
  modello, non l'accensione* — è D8, non D4;
* `shop.ricevute` è un caso da un minuto: `zeroerp_app` non ha **nessun** GRANT
  su quella tabella, quindi accendere la RLS non toglie niente a nessuno.
  ✅ **Pagata e applicata il 2026-09-12** (decisione di Tid): changeSet
  `20260912-42` (`ENABLE`) + `-43` (le due righe fuori dal registro, 10 → 8),
  pgTAP senza regressioni — brief `brief-db-fixture-che-costruiscono-d7-d6-d4.md` §5.
  ⇒ Di D4 resta solo ciò che **è D8**: le due di `acquisti`, a registro con la
  ragione.

---

### 🟠 D5 — Il criterio con cui nasce un presidio è un indicatore in ritardo

Tre invarianti della stessa famiglia — «una proprietà strutturale che, se
violata, non produce nessun errore visibile»:

| Invariante | Presidiato? |
| --- | --- |
| Una vista che tocca dati in RLS ha `security_invoker` | ⭐ **sì, e benissimo**: criterio transitivo, casi costruiti, ha sostituito quattro elenchi a mano (2026-09-07). Zero violazioni |
| Una tabella con policy ha la RLS **accesa** | ✅ **sì dall'11-09-2026**: criterio `POLICY_INERTE` di `dbops.vw_rls_perimetro_scoperto`, caso costruito nel test 7. Le 2 violazioni rimaste (`acquisti`, → D8) sono dichiarate a registro con la loro ragione |
| Una funzione `SECURITY DEFINER` ha un `search_path` fisso | ✅ **sì dal 2026-09-12**: `db/pgtap/dbops/test-security-definer-search-path-v1.sql` — invariante generale sul catalogo (estensioni escluse per `pg_depend`), verde con i pin di D6 applicati, più due rubinetti per D6-bis (18 senza `pg_temp`, 5 con `public` prima) che possono solo calare |

⭐ **La differenza fra le righe non è tecnica: è che le prime due hanno morso.**
Il progetto costruisce un presidio quando un difetto si è già manifestato, o
quando ci passa un cantiere che ne ha bisogno (la riga 2 è nata insieme al
criterio `FIGLIA_DI_TABELLA_PROTETTA`, non perché qualcuno fosse tornato a
chiudere D5). È un ottimo riflesso, ma è un criterio che arriva sempre
**dopo**: la riga 3 non ha ancora morso, ed è già violata.

**Rimedio** (scritto il 2026-09-12, vedi la riga 3): un pgTAP «postura di
sicurezza» con il terzo criterio come invariante generale sul catalogo, non un
elenco di nomi, e i debiti a soglia che può solo calare.

---

### 🟠 D6 — Tre `SECURITY DEFINER` di `postgres`, eseguibili da chiunque, senza `search_path` — pin CHIUSI il 2026-09-12, resta il registro

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
diventerebbero una scala.

✅ **Pin applicati il 2026-09-12** (`20260912-39/40/41`, pgTAP senza
regressioni): tutti nella timeline normale, senza superuser — `-39/-40` con il **prestito di
proprietà** via `fn_sync_functions_owner` (precedente `20260722-10`), `-41`
con una **copia di servizio** della sync che fa da secondo DEFINER di
postgres, perché la sync non può prestarsi a sé stessa. 🔴 Quel giro mostra
che `zeroerp_app` — che scrive `dbops.sec_functions_owner` ed esegue la sync
(`=X` a PUBLIC) — può rendersi proprietario delle sei DEFINER indurite: è il
prossimo pezzo di D6 (registro e sync riservati al migratore). ⚠️ La forma
**non** è
`pg_catalog, pg_temp`, che il testo qui sopra proponeva: è `pg_catalog, public,
pg_temp`, perché la catena tocca `dblink` che vive in `public` e il path di una
DEFINER vale per tutto ciò che chiama. L'`EXECUTE` a PUBLIC su
`fn_sync_functions_owner` è **valutato e non ritirato**: il migratore in CI ce
l'ha solo via PUBLIC (brief `brief-db-fixture-che-costruiscono-d7-d6-d4.md` §3).

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

#### 🔴 AVVERTIMENTO — la forma «prudente» rompe una di queste tre, in silenzio

> Trovato il 2026-09-12 chiudendo `brief-db-un-destinatario-per-i-presidi` §13, su
> un difetto della **stessa famiglia** ma preso dal verso opposto: lì un
> `search_path` blindato non ha aperto una porta, ha **accecato** ciò che chiamava.

⛔ **`SET search_path = pg_catalog, pg_temp` su `dbops.fn_get_or_create_session_tx_id`
non si può applicare così com'è.** Quella funzione chiama **`dblink(...)` non
qualificato** (verificato: `prosrc` non contiene `public.dblink`), e `dblink` vive
in **`public`** — come `unaccent`, `postgis` e `plpgsql_check`. Togliendo `public`
dal percorso, la chiamata non si risolve.

🔴 **E non fallirebbe: degraderebbe.** Quel `dblink` sta dentro un
`EXCEPTION WHEN OTHERS` — il «ripiego (c)» — che scrive un `RAISE WARNING` e torna
la sentinella `script.uuid_nil()`. Quindi:

| | |
| --- | --- |
| le scritture | ✅ continuano, nessun errore |
| il `tx_id` | 🔴 **non viene più registrato** in `dbops.transaction_ids`, e la GUC di sessione non viene pubblicata |
| chi se ne accorge | nessuno: un `WARNING` nel log |

⇒ Si spegnerebbe il tracciamento delle transazioni sul percorso di **305 trigger**
— quasi ogni scrittura del sistema — **senza un rosso da nessuna parte**.
⭐ Ed è la firma esatta del difetto del brief §13: *chiamata a un'estensione non
qualificata + `search_path` stretto + `WHEN OTHERS` = una cosa rotta che si
traveste da esito normale.*

✅ **Oggi non è rotto**, e va detto: quelle tre funzioni non hanno **alcun**
`search_path`, quindi `dblink` si risolve e tutto gira. Il rischio nasce nel
momento in cui si chiude D6.

**L'ordine delle operazioni, ed è una riga in più:**

1. qualificare la chiamata nel corpo — `public.dblink(...)` — con un changeSet suo;
2. **poi** il `SET search_path` stretto.

⚠️ **E questo è il vincolo per D6-bis**: una forma canonica **uguale per tutte** non
esiste. Prima di stringere il `search_path` di una funzione va guardato se lei — o
ciò che chiama — tocca un'estensione; se sì, o si qualifica la chiamata o `public`
resta nell'elenco. ⛔ La regola non si può applicare a vista su 38 funzioni: si
decide **per funzione**, guardando i suoi chiamati, e `pg_catalog, pg_temp` è la
scelta *sbagliata* per chi usa un'estensione.
⭐ Il caso già riparato mostra anche la forma giusta quando `public` serve davvero:
`dbops.fn_check_funzioni_riferimenti_morti` pinna `pg_catalog, public, pg_temp`
**e** qualifica la chiamata — i due strati insieme (changeSet `20260912-37`).

---

### 🟠 D7 — La copertura dei test non è bassa: è concentrata

600 file, ~6.183 asserzioni (2026-09-08). Il numero non dice niente; la
distribuzione sì.

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

### 🔴 Il numero che conta davvero: la suite fuori dalla macchina di sviluppo

Su un database **ricostruito da zero** — cioè quello di cui si ha bisogno il
giorno in cui si prepara un'installazione nuova — la prima misura della CI
(2026-09-09) ha dato **407 rossi su 601**. Il registro
`db/pgtap/baseline-rossi-ci.tsv` al 2026-09-12 è a **403 righe** (323
`ERRORE_FIXTURE`, 80 `ASSERZIONE`), su 634 file di test nel repo:

| Schema | Rossi | | Schema | Rossi |
| --- | --- | --- | --- | --- |
| `vendite` | 215 | | `documenti` | 6 |
| `script` | 50 | | `catalogo` | 6 |
| `anagrafiche` | 42 | | `ui` | 5 |
| `pratiche` | 37 | | `dbops` | 3 |
| `pagamenti` | 15 | | `maintenance` | 1 |
| `config` | 14 | | | |
| `rls` | 9 | | **Totale** | **403** |

⛔ **La suite è verde per un terzo fuori dalla macchina di sviluppo.** Non è una
sorpresa concettuale — la guida sui presidi §4 lo dice da mesi («69 file su 437
contengono un salto condizionato… su un database vuoto non falliscono: si
saltano») — ma il numero non era mai stato preso, ed è **sei volte** quella
stima.

⚠️ E il difetto vero non è la percentuale: è che quei 403 file **passano sul DB
di sviluppo**. Cioè la suite oggi verifica in larga parte *lo stato di una
macchina*, non che le migrazioni sappiano ricostruirla. Sono due proprietà
diverse, e la seconda è quella che serve al secondo cliente.

⭐ Dal 2026-09-09 il cancello tiene: un rosso **nuovo** ferma il merge (D1). Ma
il registro cala solo se qualcuno lo abbassa, e 323 di quei file muoiono nella
fixture — cioè **non eseguono nessuna asserzione**: sono le aree che *sembrano*
coperte. La domanda che decide il triage è quanti di quei 323 sono «il test
cerca un soggetto nei dati esistenti», un difetto noto e sanabile in blocco, e
quanti sono altro.

✅ **Il triage è cominciato dalla parte giusta, il 2026-09-12**: nel registro
stavano **21 file del perimetro** (12 `script/test-fn-scope-*` + 9 `rls/`) —
cioè i test delle funzioni che decidono *chi vede cosa* e della proprietà
fail-closed — tutti con la stessa causa (fixture che cerca soggetti in un DB
vuoto). Riscritti: **20 verdi su dbdev e su `zeroerp_ci`**, committati il 12-09 con la
baseline di sviluppo senza regressioni; il ventunesimo
(`test-role-batch-fatturazione-postura`) era un'altra classe — in CI il ruolo
batch non veniva provisionato — e ha avuto il passo in `ci-validate.yaml`.
Brief: `brief-db-fixture-che-costruiscono-d7-d6-d4.md`. Il registro scenderà
alla prima corsa della CI; le righe si tolgono a mano quando lo dice lei.

---

### 🟠 D8 — `acquisti` e `magazzino`: modellati, non scritti

✅ **Deciso l'11-09-2026 (Tid): sono il PROSSIMO CANTIERE**, non congelati —
scritto in `.codex/PROJECT_CONTEXT.md`, con la conseguenza che questa voce
cercava: *ogni decisione presa su `vendite` è presa anche per `acquisti`*, e
un'asimmetria fra i due si chiude subito, non in una «fase due». ⚠️ `storico`
**non** è coperto dalla decisione come dominio (sul lato RLS l'ha chiuso D3).
Ciò che segue resta vero finché il comportamento non c'è.

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

### ✅ D10 — I presidi non avevano un destinatario — CHIUSO l'11-09-2026

30 viste di presidio in `dbops` e nessun canale che le portasse davanti a una
persona su base regolare: sei lavori falliti da tre notti stavano in una vista
che si chiama `vw_coda_lavori_**da_guardare**`, e guardare non era di nessuno.

✅ **Chiuso l'11-09-2026** — catalogo `dbops.presidi` (la classificazione è
**dato**, non un elenco di viste scritto in Python), digest costruito dal
backend, due timer in servizio (giornaliero 07:00, settimanale lunedì 07:30),
e il primo giro ha già riferito. Storia:
`brief-db-un-destinatario-per-i-presidi.md`.

⚠️ Residuo dichiarato: `maintenance.vw_job_run_da_guardare` guarda sette giorni
e **non filtra i processi ritirati** (`obsoleto_dal`), quindi il debutto ha
riferito un allarme su un processo obsoleto dal 07-09. Si è spento da sé con la
finestra; se un processo ritirato debba uscire dalla vista è una decisione del
team DB. *Un presidio che comincia col rumore insegna a non guardarlo*, ed è
proprio la proprietà che il cantiere comprava.

---

### 🟡 D11 — I registri di debito non calano

Un registro di debito è una buona invenzione **a condizione che scenda**. Stato
al 2026-09-08, salvo dove è scritta un'altra data:

| Registro | Oggi |
| --- | --- |
| `dbops.vw_codici_errore_da_dichiarare` | **508** su 852 codici |
| `db/pgtap/baseline-rossi-ci.tsv` | **403** file al 2026-09-12 (323 `ERRORE_FIXTURE`, 80 `ASSERZIONE`) — nato il 09-09 con 407 |
| `SOGLIA_THROWS_SENZA_DISCRIMINANTE` | **131** |
| `dbops.vw_fk_con_indice_missing_policy` | **57** |
| `db/pgtap/baseline-rossi.tsv` | **16** file al 2026-09-12 (9 `ERRORE_FIXTURE`, 7 `ASSERZIONE`) — erano 19 |
| `dbops.rls_perimetro_debito` | **10** righe (nato l'11-09 con 33, → D2) |
| `backend/scripts/tests/baseline-smoke.tsv` | 2 su 16 script (2026-09-12) |
| Header di licenza mancanti | 2.042 file (misura 2026-08-26) |
| `dbops.vw_indici_ridondanti_prefisso` | 1 |
| Codici vivi senza messaggio | 6 (tutti `W_`, §2.3) |
| `dbops.vw_processi_che_bypassano` | 1 (dichiarato, con data di ritiro) |

⭐ L'ultima riga è l'unica fatta bene: **una** voce, con il motivo e il momento in
cui sparisce. Le prime quattro sono liste lunghe, e la guida sui presidi dice
esattamente perché è un problema: *«il registro nasce piccolo. Se parte con
trenta righe, nessuno lo leggerà»*. `rls_perimetro_debito` è nato nella forma
giusta — ogni riga con la sua ragione — ed è calato di due terzi nel cantiere
che l'ha aperto.

⚠️ Le due baseline pgTAP meritano una riga a parte: **323 + 9 file falliscono
nella fixture**, cioè non eseguono **nessuna** asserzione. La loro copertura
vale zero, non «parziale» — e sono aree che *sembrano* coperte.

---

### 🟡 D12 — Documentazione: il problema non è più la quantità

1.410 pagine manuali contro 1.500 auto-generate: copertura sostanzialmente piena,
il gap di febbraio è chiuso. Restano due cose:

* `storico`: 111 pagine, media 15 righe, **98 sotto le 12 righe**. Sono specchi
  auto-generati, e va bene — ma gonfiano il conteggio di copertura del 7%;
* `magazzino` (35 righe/pagina) e `acquisti` (36) hanno pagine **presenti e
  sottili**. Coerente con D8: si documenta poco ciò che fa poco.

---

### ✅ D13 — Come `zeroerp_app`, l'operatore di un emittente non di default non creava un billing account — CHIUSO il 2026-09-13

Trovato il 2026-09-12: `INSERT INTO anagrafiche.billing_account … RETURNING id`
moriva con «la nuova riga viola la regola di sicurezza per riga» (42501) ogni
volta che l'emittente di chi agiva non era quello di default — la policy di
lettura risolve il BA dal legame, il legame lo scrive il trigger **AFTER**
`z90_link_ef` *dopo* il `RETURNING`, e nel frattempo
`script.fn_get_ba_emittente_sr_id` ricadeva sul **default**, un'altra azienda.
Il backend fa lo stesso `RETURNING` (`clienti_repository.create_billing_account`)
⇒ con due emittenti in esercizio gli operatori del secondo non aprivano clienti.

✅ **Deciso da Tid il 2026-09-12 (opzione 1 di tre) e chiuso il 2026-09-13** —
brief `brief-db-ba-riserva-emittente-operatore-d13.md`: *un BA non ancora
collegato appartiene a chi lo sta creando*. La riserva del resolver ha ora
**tre livelli** (mapping specifico; in sessione, l'emittente dell'operatore —
la stessa funzione con cui il trigger scrive il legame; senza sessione, il
default). Tre changeSet `20260913-01/02/03` applicati, baseline di sviluppo
senza regressioni: la decisione (01), l'onestà del `PARALLEL SAFE` che cade
sul resolver e sulla chiamante (02, la mossa già fatta il 18-08 sulla ricerca),
e la **seconda copia** della regola trovata leggendo i chiamanti —
`anagrafiche.fn_get_emittente_fiscale_pk`, usata dai guard dei documenti — che
ora delega (03). Nessuna bonifica dei dati. Presidio: il pgTAP che costruisce
l'operatore del secondo emittente e prova l'`INSERT … RETURNING` come
`zeroerp_app` (rosso sullo scratch senza i changeSet, verde con), più i tre
file che pinnavano «BA senza mapping → default» con il contesto aperto,
spezzati in «in sessione / senza sessione».

⚠️ **Il prezzo, dichiarato**: un BA che *resta* senza legame (seed, migrazione)
è ora, in sessione, di chiunque lo guardi — dato anomalo che il modello ammette.
Restano in coda, come decisioni e non come lavoro: la forma «emittente come
colonna del BA» (opzione 3) e un presidio `ZERO` sui BA senza legame.
✅ **Team BE, chiuso il 2026-09-13**: le tre copie inline della regola vecchia
(`clienti_repository.list_clienti`, `soggetti_repository` ×2) delegano ora a
`fn_check_ba_visible_for_emittenti` — un frammento solo, usato in tre punti —
con un presidio a registro zero sulla forma (`test_scope_ba_delega_alla_fn.py`).
Risultati identici prima/dopo su 5 perimetri × 4 query (oggi tutti i BA sono
collegati, ed è il motivo per cui nessuna lista mentiva).

---

### 🟠 D14 — La capability di UN DDT paga le partite di TUTTI i DDT, e sotto RLS le paga venti volte

Trovato il 2026-09-17 inseguendo un pgTAP lento
(`script/test-capability-motivi-e-nessuna-azione-v1.sql`, oltre i 90 s a cui
`pgtap-baseline.sh` uccide un file). Il test aveva un difetto suo — richiamava
le stesse funzioni `STABLE` fino a quattro volte per documento — ed è stato
riscritto perché il blob si calcoli una volta (36 s). Ma il grosso del tempo
era del **prodotto**, e resta:

* `script.fn_available_actions_ddt(id)` chiama `vendite.fn_list_ddt_da_pushare(p_ddt_id)`
  **e**, nel ramo dei motivi, `vendite.fn_ddt_push_diagnosi(p_ddt_id)`. Entrambe
  fanno `JOIN vendite.vw_partite_merce`, e la vista è a CTE **materializzate**
  (`riga` è letta due volte, `alloc` e `migra` sono finestre sulla popolazione):
  il predicato sul documento **non entra**, quindi ogni chiamata ricalcola le
  partite di tutti i DDT. È strutturale, non un caso del planner: la partita di
  una riga dipende dalle spedizioni **precedenti** della stessa riga d'ordine
  (greedy di `alloc`), quindi filtrare `riga` per DDT darebbe un numero
  sbagliato. ⇒ Una funzione «per documento» — quella che alimenta il drawer del
  DDT a ogni apertura — ha il costo della lista;
* sotto RLS quel costo si moltiplica: la CTE `sospetto` (`sospetto_duplicato_ordine`)
  è un `EXISTS` correlato a quattro tabelle che il planner esegue **riga per
  riga**, e ogni riga scandita paga la sua policy (`fn_scope_ef_whitelist_via_ddt`,
  `…_via_ordine_riga`, `…_via_ordine`): ~3.500 valutazioni per una lettura.

**Misurato il 2026-09-17 su dbdev** (51 DDT, 36 partite), come `zeroerp_app` con
contesto operatore, salvo dove scritto: `vw_partite_merce` intera **18 ms da
owner, 396 ms da app** (di cui 322 nella sola `sospetto`);
`fn_available_actions_ddt` **33 ms da owner, ~850 ms da app**. Per confronto
`fn_available_actions_preventivo` ~10 ms e `_ordine` ~29 ms.

⭐ **La leva provata, ancora da decidere.** `sospetto` riscritta *set-based* —
prima l'insieme delle coppie `(ddt_id, articolo_id)` coperte da un ordine
collegato al DDT (`DISTINCT`, quindi una riga per coppia e nessuna
moltiplicazione), poi il `JOIN` delle righe senza fulfillment su quella coppia —
con **`AS MATERIALIZED`** su entrambe le CTE (senza, il planner la inlina e
torna al ciclo per riga; la forma è già in uso in tre changeSet). Provata come
`SELECT` in transazione ritirata: **375 ms → 88 ms**, e `EXCEPT ALL` nei due
versi a **zero righe**. È equivalente per costruzione, non solo sui dati di
oggi: l'`EXISTS` vecchio è esattamente «la coppia della riga sta in
quell'insieme». Il presidio esiste già (`test-vw-partite-merce-v1.sql`, test 11,
costruisce il caso). Con questa sola mossa la capability del DDT scende a
~200 ms.

⚠️ **La seconda leva è più profonda**: la capability legge la vista **due
volte** (lister + diagnosi), e la diagnosi da sola risponde a entrambe le
domande (`motivo IS NULL` = eleggibile). Va guardata insieme al contratto di
equivalenza fra le due funzioni, «blindato a pgTAP» — non è una riga da
cambiare di straforo.

⛔ Non è un problema del solo test: **ogni pgTAP che itera i DDT vivi paga lo
stesso conto** (`test-capability-annulla-aspetto-e-stato-leggibile-v1.sql`
chiama la capability su tutti gli otto domini una volta) e lo paga il drawer.
Decisione aperta per Tid: changeSet su `vw_partite_merce` (ri-specificando
`security_invoker=on`) con la prima leva, e se aprire un brief per la seconda.

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

## 5. Scorecard — pesata, non mediata (2026-09-08, aggiornata al 2026-09-12)

Il peso è **la conseguenza di un difetto in quell'area**, non la sua estensione.

| Area | Peso | Voto | Perché |
| --- | --- | --- | --- |
| **Catena di verifica (CI)** | 🔴 alto | **7,5/10** | Dal 2026-09-09 la suite pgTAP è un cancello vero: baseline misurata dalla CI, niente `continue-on-error`, bootstrap che fallisce invece di passare. Resta il registro a 403, che deve calare (D7) |
| **Perimetro dei dati (RLS)** | 🔴 alto | **8/10** | D2 e D3 chiusi l'11-09-2026: dominio documento protetto fino ai satelliti, versioni di storico con scope congelato, e due presidi a criterio (`vw_rls_perimetro_scoperto`, `vw_storico_scope_da_dichiarare`) che vedono le tabelle nuove. Restano le due policy inerti di `acquisti` (D4 → D8), a registro con la ragione; `shop.ricevute` armata il 12-09. D13 (il `RETURNING` del BA per gli operatori non di default) chiuso il 13-09 |
| **Copertura test** | 🔴 alto | **4/10** | 634 file, ma su un DB ricostruito da zero la suite è rossa per due terzi (403 rossi noti al 2026-09-12). Il 38% delle funzioni non è mai nominato (D7) |
| **Postura di sicurezza degli oggetti** | 🟠 medio | **7,5/10** | I tre invarianti di D5 presidiati per criterio (`search_path` dal 12-09, pin applicati). Non di più per i due rubinetti di D6-bis e per il pezzo nuovo: registro `sec_functions_owner` e sync scrivibili/eseguibili da `zeroerp_app` |
| **Simmetria del dominio** | 🟠 medio | **4/10** | `acquisti` e `magazzino` modellati e non scritti (D8). La decisione dell'11-09 («prossimo cantiere») dà al debito un verso, ma il voto misura il comportamento, che ancora non c'è: *una decisione non scrive il codice* |
| **Osservabilità dei presidi** | 🟠 medio | **7/10** | D10 chiuso l'11-09-2026: le 30 viste hanno un destinatario che ha già riferito, e la classificazione è **dato** (`dbops.presidi`). Non 8+ per il debutto col rumore (processi ritirati in `vw_job_run_da_guardare`) |
| **Gestione del debito** | 🟠 medio | **6/10** | Registri ben progettati; le liste lunghe restano lunghe, e ne è nata una nuova da 403 (D11) |
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

✅ **E la catena che deve rendere vero tutto questo, dal 2026-09-09, tiene**:
la suite pgTAP ferma un merge su un rosso nuovo (D1). ⚠️ Con una cosa scomoda,
adesso misurata: fuori dalla macchina di sviluppo la suite è rossa per due
terzi. Non è una regressione — è sempre stato così — e la differenza fra «i test
passano» e «le migrazioni sanno ricostruire un sistema che passa i test» è
tutta lì dentro (D7).

⚠️ **«Production-ready»**: all'8 settembre non era la parola giusta, e non per
la qualità del design — per D1, D2 e D3: righe di cinque famiglie di documento
su sei e tutto lo storico leggibili da chiunque. Chiusi tutti e tre fra il 9 e
l'11 settembre, la frase torna difendibile sul perimetro dei dati — e il 13
settembre è caduto anche D13, che su un'installazione a due emittenti avrebbe
impedito al secondo di aprire clienti. Quello che resta sono le due policy
inerti di `acquisti` (D4 → D8, a registro con la ragione), il pezzo nuovo di
D6 e il registro dei rossi in CI.

---

## 6. Checklist, in ordine di ritorno

### 🔴 Prima di tutto il resto

* [x] **D1** — ✅ chiuso il 2026-09-09: classificatore bilingue, baseline della
      CI committata, `continue-on-error` tolto, bootstrap che fallisce. (D1-bis,
      la frase di `.codex/AGENTS.md` su `baseline-rossi-ci.tsv`, è diventata
      vera da sé nel momento in cui il file è stato committato.)

### 🔴 Il perimetro

* [x] **D2** — ✅ chiuso l'11-09-2026, brief
      `work-done/brief-db-perimetro-emittente-righe-documento.md`. Presidio
      transitivo in servizio, 10 righe di debito con la ragione.
* [x] **D3** — ✅ chiuso l'11-09-2026, brief
      `work-done/brief-db-rls-storico-scope-congelato.md` — compreso
      `dbops.audit_log` (cancello sugli scrittori + append-only).
* [x] **D4** — ✅ `shop.ricevute` armata il 2026-09-12 (`20260912-42/43`,
      registro 10 → 8). Per `acquisti.ddt`/`ordini` prima il modello — colonna
      emittente e veste operatore — cioè **D8**: restano a registro con la
      ragione, non sono D4.
* [x] **D5** — ✅ tre invarianti su tre presidiati per criterio
      (`security_invoker` dal 09-07, `relrowsecurity` dall'11-09, `search_path`
      dal 12-09 in `test-security-definer-search-path-v1.sql`).
* [~] **D6** — ✅ pin applicati il 12-09 (`-39/-40/-41`, forma `pg_catalog,
      public, pg_temp`). ⛔ Resta il pezzo nuovo: registro `sec_functions_owner`
      e `fn_sync_functions_owner` riservati al migratore (oggi
      scrivibili/eseguibili da `zeroerp_app`) — brief §3, stima ≈ mezza giornata. `EXECUTE` a PUBLIC su
      `fn_sync_functions_owner`: valutato, resta — il migratore in CI lo ha
      solo via PUBLIC (brief §3).
      🔴 **PRIMA, una riga obbligatoria**: qualificare `public.dblink(...)` in
      `fn_get_or_create_session_tx_id`. Senza, il `search_path` stretto spegne il
      tracciamento `tx_id` su ~305 trigger **in silenzio** — il `dblink` è dentro
      un `EXCEPTION WHEN OTHERS` che torna la sentinella e logga un `WARNING`.
      Vedi l'avvertimento in fondo a D6.
* [ ] **D6-bis** — scegliere **una** forma canonica di `search_path` per le
      `SECURITY DEFINER` (`pg_catalog, <schemi necessari>, pg_temp`, con
      `pg_temp` sempre ultimo ed esplicito) e allineare le 18 che oggi non
      elencano `pg_temp` e le 5 che mettono `public` prima di `pg_catalog`.
      ⛔ **Non applicabile a vista**: `pg_catalog, pg_temp` è la scelta sbagliata
      per chi tocca un'estensione (`dblink`, `unaccent`, `postgis`,
      `plpgsql_check` stanno tutte in `public`). Si decide **per funzione**,
      guardando i suoi chiamati — o si qualifica la chiamata, o `public` resta
      nell'elenco.

### 🟠 La sostanza

* [x] **D8** — ✅ deciso l'11-09-2026 (Tid): prossimo cantiere, scritto in
      `.codex/PROJECT_CONTEXT.md`. ⚠️ `storico` resta senza decisione come
      dominio; sul lato RLS l'ha chiuso D3.
* [x] **D10** — ✅ chiuso l'11-09-2026: digest su catalogo `dbops.presidi`, due
      timer. Residuo: i processi ritirati in `vw_job_run_da_guardare` (decisione
      del team DB).
* [~] **D7** — far calare il registro della CI (403, di cui 323 nella fixture)
      e portare a zero i 9 file della baseline di sviluppo che falliscono nella
      *fixture*. ✅ 12-09: i **21 del perimetro** riscritti (20 verdi sui due
      database, uno in CI con il passo di provisioning nuovo), in attesa di
      apply e della corsa CI.
* [x] **D13** — ✅ chiuso il 2026-09-13: changeSet `20260913-01/02/03`
      applicati, baseline di sviluppo senza regressioni, brief
      `brief-db-ba-riserva-emittente-operatore-d13.md`. ✅ Le tre copie
      Python della regola vecchia sono delegate al check dal 13-09 (team BE,
      brief §6.2). Restano due decisioni di modello in coda (§3.4).
* [ ] **D11** — dare a ciascun registro lungo un **verso** (chi lo abbassa, di
      quanto, entro quando), o dichiararlo congelato con il motivo.
* [ ] **D11-bis** — scrivere il messaggio dei sei `W_` che non ce l'hanno
      (append al CSV dei messaggi, mai un loader nuovo), oppure dichiarare che
      quei codici non raggiungono mai un operatore — e scriverlo nel `note`.
* [ ] **D14** — (aperto il 2026-09-17) `sospetto` di `vw_partite_merce`
      set-based + `AS MATERIALIZED` (provata: 375 → 88 ms da app, righe
      identiche), changeSet con `security_invoker=on` ri-specificato. Poi
      decidere se la capability del DDT debba leggere la vista **una** volta
      invece di due (lister + diagnosi). ✅ Il pgTAP che l'ha fatto emergere è
      già riscritto (blob una volta per documento, >90 s → 36 s).

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
datato. Sfoltito il 2026-09-12: le voci chiuse sono ridotte a data e rimando; la
versione integrale è nella storia git del file.*
