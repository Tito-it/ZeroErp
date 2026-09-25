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
>
> ✅ **Riordinato il 2026-09-20.** Le voci **chiuse** sono uscite da §3 e sono
> tutte in fondo, in **§7 «Attività svolte»** — comprese le parti chiuse delle
> voci che ne hanno ancora una aperta: quando succede, il numero compare
> **due volte**, in alto il lavoro che resta e in fondo quello fatto (`D6`,
> `D7`, `D11`, `D12`). §3 oggi contiene **solo ciò che è da fare**, e §6 è
> la check-list delle stesse voci: `[ ]` in cima, `[x]` con il loro dettaglio in
> §7.
>
> ✅ **Riordinato il 2026-09-22.** **D14 è chiusa** (otto giri, sette applicati,
> l'ottavo ritirato; brief in `work-done/`, tutto committato fino a
> `8d7f14829`/PR #1646) ed è passata **per intero** in §7. Al suo posto in §3 è
> entrata **D15**, che la sua chiusura ha scoperto: in `vendite` 82 tabelle su 87
> non hanno mai avuto un `ANALYZE`, quindi **ogni misura di piano di questo
> documento è stata presa su stime di default**. ⛔ Non è un residuo di quel
> cantiere: è la condizione in cui si è misurato finora.
>
> ✅ **Numeri rimisurati il 2026-09-20.** I registri che stanno nel repo o nel
> catalogo del database si **rimisurano**, non si citano: `baseline-rossi-ci.tsv`
> è a **361** file al 22-09 (403 al 12-09, 362 al 20-09: col giro 6 di D14 è
> uscita la riga del pgTAP della vista ritirata; **295 attesi** dopo il 21-09,
> misura sullo scratch da certificare in CI), `SOGLIA_THROWS_SENZA_DISCRIMINANTE` a **123**
> (129, e 131 quando questa valutazione è stata scritta), `rls_perimetro_debito`
> a **7**, e `vw_codici_errore_da_dichiarare` a **545** — **salito**, non calato.
> Dove un numero è rimasto quello del giorno in cui è stato preso, la data è
> accanto.
>
> ✅ **Aggiornato il 2026-09-23 sera — chiuso il giro 2 di D7.** Suite a **687**
> file; `SOGLIA_THROWS_SENZA_DISCRIMINANTE` a **119**; `baseline-rossi-ci.tsv`
> ancora a **361**, mentre la baseline sullo scratch `zeroerp_ci` (Tid, 24-09) dà **229 rossi
> su 687**: 132 righe sono rientrate e aspettano di uscire dal registro con la
> corsa CI. Restano **18 rossi** nel lotto 2, da
> guardare uno per uno. Dettaglio in §3 D7 («Conteggi al 2026-09-23 sera»).
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
**nessuno li faceva contare**. Vedi §7 D1 (chiuso il 2026-09-09).

Erano corrette anche: la lode ai trigger generici (oggi il riuso è
strutturalmente più forte di allora), l'error handling centralizzato, la FK index
policy, la disciplina Liquibase.

### 1.2 Cosa non reggeva, già allora

| Diceva febbraio                                                          | Perché non reggeva                                                                                                                                                                                                                                                                                                                               |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| «`contabilita`: **0 test, gap critico, dominio business-critical**»      | ⛔ **Sbagliato allora e sbagliato oggi.** Lo schema `contabilita` è **vuoto**: zero tabelle, zero funzioni, zero viste. La misura «0 test» è stata letta come difetto senza chiedere al modello *cosa* avrebbe dovuto coprire. È il caso da manuale della Regola zero: un conteggio ha disegnato una priorità alta su un perimetro che non esiste |
| «`acquisti`: 0 test, **critico — specchia vendite**»                     | Mezzo giusto. Che *specchi* vendite è un'affermazione sul modello, e vale. Che il rimedio sia «aggiungere test» no: mancano prima **le funzioni** — `acquisti` ha 42 FK e 2 funzioni. Non si collauda un dominio che non è stato scritto                                                                                                         |
| «`clienti` ha 18 trigger → valutare consolidamento (**priorità bassa**)» | Osservazione a livello di **sintomo**. Il numero non è una scelta di stile: è la conseguenza meccanica di un pattern che genera **un trigger per figlia**. Oggi `catalogo.articoli` ne ha **46**. La domanda giusta non era «consolidare?» ma «la forma del pattern regge al crescere delle figlie?» — vedi §3 D9                                |
| «Voto 8.9/10 — design **production-ready**»                              | Nessuna area era pesata per conseguenza, e due delle domande che decidono la frase «production-ready» non erano nella griglia: *chi vede quali righe* (la RLS non esisteva ancora) e *cosa impedisce a una regressione di entrare*                                                                                                               |
| «509 pagine manuali, gap su 3 schemi»                                    | Corretto e **chiuso**: oggi 1.410 pagine manuali su 1.500 auto-generate. `magazzino` 32, `acquisti` 11, viste coperte                                                                                                                                                                                                                            |

### 1.3 Le proposte di automazione di febbraio, sette mesi dopo

| #   | Proposta                           | Stato al 2026-09-08                                                                                                                                                                                                                                                                                                    |
| --- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Scaffolding changelog YAML         | ⛔ non fatto                                                                                                                                                                                                                                                                                                            |
| 2   | Scaffolding pgTAP                  | ⚠️ parziale — `db/pgtap/_TEMPLATE.sql.txt` + `docs/it/guide/pgtap-come-si-scrive-un-test.md`                                                                                                                                                                                                                            |
| 3   | Generatore `loadUpdateData` da CSV | ⛔ non fatto (esiste `scripts/gen_seed_lista.py`, che è un'altra cosa)                                                                                                                                                                                                                                                  |
| 4   | Linter `%TYPE`                     | ⛔ non fatto                                                                                                                                                                                                                                                                                                            |
| 5   | `fn_setup_standard_table`          | ⭐ **superata da qualcosa di meglio.** Il framework automazioni (`dbops.fn_run_automations_*` + `automation_scope`/`automation_rules_tbl`) applica audit, `tx_id`, storico, lock colonne, cleanup e delete-block **per pattern** nella passata `ci_apply`. Non serve chiamarla per tabella: non serve chiamarla affatto |
| 6   | Validatore pre-deploy              | ⭐ **realizzato in forma migliore**: sette cancelli statici in `ci-validate.yaml` (`runOnChange`, preambolo pgTAP, letterali SQL, preCondition su `80_data`, DDL su trigger di automazione, GRANT ai ruoli batch, licenze) più `scripts/ci-local.sh`, che replica la CI in locale                                       |
| 7   | Diff signature funzioni            | ⛔ non fatto                                                                                                                                                                                                                                                                                                            |
| 8   | Report trigger per tabella         | ⚠️ interrogabile (`dbops.vw_trigger_functions`), non confezionato                                                                                                                                                                                                                                                       |
| 9   | Template Liquibase per pattern     | ⛔ non fatto — e in buona parte reso inutile dal #5                                                                                                                                                                                                                                                                     |

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
interamente fuori. ✅ Chiusi entrambi l'11-09-2026 (§7): il dominio documento è
protetto fino ai satelliti e ogni versione di storico porta lo scope congelato.
Resta **D8** — le due policy inerti di `acquisti`, che aspettano il modello, a
registro con la ragione.

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

897 codici a catalogo, 847 messaggi, dieci classi. Il contratto è esplicito:
`codice` → backend (status HTTP e `ui_action`), `context->>'campo'` → frontend,
`VARIADIC valori` → l'operatore. Con il presidio del «terzo lato»
(`dbops.vw_codici_errore_da_dichiarare`) e il «rubinetto» che impedisce a un
codice di allargare il proprio significato.

⚠️ **Il registro non cala: cresce.** 545 codici su 897 risultano non dichiarati
lato applicativo — erano 508 su 852 l'08-09. Vedi §3 D11.

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

## 3. I difetti **aperti**, in ordine di conseguenza

> ✅ **Le voci chiuse non stanno qui**: sono tutte in **§7 «Attività svolte»**,
> con la data e il rimando al brief. E sono di due tipi: quelle chiuse **per
> intero** — D1, D2, D3, D4, D5, D10, D13 e, dal 2026-09-22, **D14** — e le
> **parti** chiuse di voci che hanno ancora un lavoro vivo: `D6` (i pin del
> `search_path`), `D7` (il triage del perimetro), `D11` (registri calati, e uno
> cresciuto), `D12` (la quantità). Quegli ultimi quattro numeri compaiono **in
> tutti e due i posti**, e non è una ripetizione: in alto c'è il lavoro che
> resta, in fondo quello fatto.
>
> ⭐ **D15 è nata dalla chiusura di D14** (2026-09-22): le statistiche che non
> esistono non erano un residuo di quel cantiere, erano la **condizione** in cui
> ogni sua misura è stata presa.
>
> ⚠️ **D16 è nata il 2026-09-23** da un test diventato rosso da solo: una data
> scritta a mano che il passare dei giorni ha portato fuori dalla finestra di
> emissione.
>
> Qui sotto, **solo il lavoro che resta**: D6, D7, D8, D9, D11, D12, D15, D16.

### 🟠 D6 — Tre `SECURITY DEFINER` di `postgres`, eseguibili da chiunque, senza `search_path` — pin chiusi il 12-09 (§7), resta il registro

| Funzione                               | Owner      | `EXECUTE`  | `search_path` |
| -------------------------------------- | ---------- | ---------- | ------------- |
| `dbops.fn_generate_tx_id`              | `postgres` | **PUBLIC** | ⛔ nessuno     |
| `dbops.fn_get_or_create_session_tx_id` | `postgres` | **PUBLIC** | ⛔ nessuno     |
| `dbops.fn_sync_functions_owner`        | `postgres` | **PUBLIC** | ⛔ nessuno     |

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

⭐ **Dal 19-09 il pezzo che resta ha un brief suo**,
`work-in-progress/brief-db-registro-owner-e-sync-riservati-al-migratore.md`,
con due fatti letti dal vivo che cambiano la forma: l'app ha sulla sync anche
un `EXECUTE` **esplicito** (`zeroerp_app=X/postgres`, dal loop dei grant —
quindi la difesa sta nel corpo, non nell'ACL), e dentro una DEFINER
`current_user` è il proprietario: la guardia legge **`session_user`**.

⚠️ Seconda faccia, meno visibile: le `SECURITY DEFINER` proprie sono **38** e il
`search_path` ha **cinque forme diverse**:

| Forma                                                  | Quante |
| ------------------------------------------------------ | ------ |
| `pg_catalog, public`                                   | 16     |
| `pg_catalog, pg_temp`                                  | 8      |
| `public, pg_temp`                                      | 5      |
| `pg_catalog, pratiche, script, config, dbops, pg_temp` | 4      |
| `pg_catalog, anagrafiche, config, script`              | 2      |
| *(nessuno)*                                            | 3      |

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

|                   |                                                                                                      |
| ----------------- | ---------------------------------------------------------------------------------------------------- |
| le scritture      | ✅ continuano, nessun errore                                                                          |
| il `tx_id`        | 🔴 **non viene più registrato** in `dbops.transaction_ids`, e la GUC di sessione non viene pubblicata |
| chi se ne accorge | nessuno: un `WARNING` nel log                                                                        |

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

|              | mai nominato in un pgTAP | totale    |
| ------------ | ------------------------ | --------- |
| **Funzioni** | **315**                  | 829 (38%) |
| **Tabelle**  | **83**                   | 372 (22%) |

*(«mai nominato» è la soglia più generosa possibile: essere nominato non
significa essere collaudato. È un limite inferiore.)*

Per schema, i file di test: `vendite` 253, `script` 69, `anagrafiche` 66,
`pratiche` 43, `config` 33, `dbops` 32, `rls` 22, `pagamenti` 17, `catalogo` 15,
`ui` 13, `documenti` 11, `maintenance` 5, **`magazzino` 1**, **`shop` 1**,
**`acquisti` 0**, **`storico` 0**.

⚠️ E la copertura dichiarata è più alta di quella reale per due motivi già
scritti nella guida sui presidi: **110 file** contengono uno `skip()`
condizionato (su un DB ricostruito da zero si saltano, e un test saltato conta
verde), e il debito `throws_ok` senza discriminante è a **123** (2026-09-20:
129 l'8-09, 131 quando questa valutazione è stata scritta) — un
`throws_ok(sql, NULL, NULL)` accetta *qualunque* errore, compreso quello
sbagliato. ⭐ Sei di quei 123 sono usciti il 20-09 con una sonda sola, e uno dei
sei era **verde per l'errore sbagliato**: §7 D11.

### 🔴 Il numero che conta davvero: la suite fuori dalla macchina di sviluppo

Su un database **ricostruito da zero** — cioè quello di cui si ha bisogno il
giorno in cui si prepara un'installazione nuova — la prima misura della CI
(2026-09-09) ha dato **407 rossi su 601**. Il registro
`db/pgtap/baseline-rossi-ci.tsv` al **2026-09-20** è a **362 righe** (293
`ERRORE_FIXTURE`, 69 `ASSERZIONE`), su **671** file di test nel repo — e a
**361** dal 22-09, quando il giro 6 di D14 ha ritirato `vw_contatore_merce` e con
lei il suo pgTAP:

| Schema        | Rossi |     | Schema        | Rossi   |
| ------------- | ----- | --- | ------------- | ------- |
| `vendite`     | 212   |     | `documenti`   | 6       |
| `anagrafiche` | 39    |     | `catalogo`    | 6       |
| `pratiche`    | 37    |     | `ui`          | 4       |
| `script`      | 31    |     | `dbops`       | 3       |
| `pagamenti`   | 11    |     |               |         |
| `config`      | 13    |     | **Totale**    | **362** |

`rls` e `maintenance` sono **usciti dal registro** — e il calo che li ha portati
fin qui è lavoro vero, non igiene: la fixture che **costruisce** il mondo invece
di cercarlo.

> ⭐ **Conteggi al 2026-09-23 sera — chiuso il giro 2 di D7** (fatto datato:
> misura sullo scratch `zeroerp_ci` ricostruito da zero, confermata dalle corse
> di Tid, **non ancora certificata dalla CI**).
>
> | | File | Verdi da zero | Rossi |
> | --- | --- | --- | --- |
> | suite pgTAP nel repo | **687** (671 al 20-09) | — | — |
> | registro `baseline-rossi-ci.tsv` | — | — | **361** (fermo: cala solo con la corsa CI) |
> | lotto 1 — `config` `pagamenti` `documenti` `catalogo` `ui` `dbops` | 43 | **37** | **3** dichiarati (+3 da riconciliare: 16+21+3 = 40) |
> | lotto 2 — `anagrafiche` `script` | 70 | **51** + 1 verde da owner | **18** |
>
> ⇒ Dei 113 file dei due lotti, **92 sono verdi** sul database da zero (89 se i
> tre non riconciliati sono rossi).
>
> ✅ **La misura vera, 2026-09-24 (Tid, baseline sullo scratch `zeroerp_ci`, ricostruito da zero): 229
> rossi su 687**, contro i **361** noti in baseline. La stima del 23-09 sera
> («circa 270», contando solo i due lotti) era prudente: sono rientrati **132**
> file, non ~90 — il resto viene da fuori dai due lotti (builder e correzioni del
> giro 2 usati anche altrove). Il registro scende a 229 solo con la corsa CI e
> `pgtap-baseline-ci-rientrati.sh` lanciato **il giorno stesso**. **I 18 rossi del lotto 2**
> sono elencati per nome in
> [brief-db-fixture-che-costruiscono-giro-2.md](../work-done/brief-db-fixture-che-costruiscono-giro-2.md)
> §11, «Stato di chiusura» (⚠️ per nome sono 19: scarto di uno da riconciliare).

⛔ **Fuori dalla macchina di sviluppo la suite è verde su poco meno di metà dei
file.** All'8 settembre era «verde per un terzo», e il numero non era mai stato
preso prima: era **sei volte** la stima della guida sui presidi §4 («69 file su
437 contengono un salto condizionato… su un database vuoto non falliscono: si
saltano»).

⚠️ E il difetto vero non è la percentuale: è che quei 362 file **passano sul DB
di sviluppo**. Cioè la suite oggi verifica in larga parte *lo stato di una
macchina*, non che le migrazioni sappiano ricostruirla. Sono due proprietà
diverse, e la seconda è quella che serve al secondo cliente.

⭐ Dal 2026-09-09 il cancello tiene: un rosso **nuovo** ferma il merge (D1). Ma
il registro cala solo se qualcuno lo abbassa, e 293 di quei file muoiono nella
fixture — cioè **non eseguono nessuna asserzione**: sono le aree che *sembrano*
coperte. La domanda che decide il triage è quanti di quei 293 sono «il test
cerca un soggetto nei dati esistenti», un difetto noto e sanabile in blocco, e
quanti sono altro.

#### Il triage delle cause — 2026-09-20

✅ **Risposta: quasi tutti.** Il log della corsa GitHub del 19-09 era già
ritirato (410 a un giorno di distanza), quindi i 362 file sono stati rieseguiti
sullo scratch `zeroerp_ci` (allineato al `20260919-09`, stesso metro della CI)
come `zeroerp_app`, leggendo la **prima riga `ERROR`** di ciascuno — cioè la
causa, non l'etichetta:

| Prima riga `ERROR` della fixture                                                       | File    |
| -------------------------------------------------------------------------------------- | ------- |
| «Nessun emittente fiscale attivo» (`fn_pgtap_emittente_operatore` o contesto vuoto)    | **130** |
| «`p_billing_account_id` obbligatorio» — `SELECT … FROM billing_account … LIMIT 1` → NULL | **45**  |
| «valore nullo nella colonna X» — un lookup su `anagrafiche` torna NULL e l'INSERT lo incassa | **38**  |
| «Emittente fiscale di default mancante»                                                | 13      |
| «Scrittura senza un utente in sessione», `p_tipo_doc_fiscale_id`, `ART_TEST_BASE`, RIS_UMANA… | ~60, a spicchi |

E i 69 `ASSERZIONE` sono la stessa cosa in forma morbida: «Esiste almeno un
cliente con istanza», «Trovato soggetto con partita_iva = …», «Esiste almeno un
Gestore». È **una** malattia con tre sintomi: la fixture *cerca* l'azienda
invece di costruirla (guida pgTAP, §«Il mondo si costruisce, non si cerca»).

⭐ **E la radice è una riga sola.** 352 dei 362 file hanno lo stesso preambolo
`DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;`.
Su un database vuoto quella funzione non trova nessun operatore e imposta un
contesto **vuoto** — l'intestazione della sua rev `20260805-27` diceva che
«fallisce parlando», il corpo non lo ha mai fatto — e tutto il resto muore a
cascata venti righe più in là. Simulato su **copie** dei 352 file (la riga
sostituita dal blocco «costruisci azienda+operatore, poi contesto», quello già
documentato nel COMMENT di `dbops.fn_pgtap_crea_emittente_operatore`):

| Da → a (una sola modifica)                                                     | File   |
| ------------------------------------------------------------------------------ | ------ |
| `ERRORE_FIXTURE` → **verde**                                                   | **50** |
| `ASSERZIONE` → **verde**                                                       | **12** |
| `ERRORE_FIXTURE` → `ASSERZIONE` (copertura da zero a parziale, rosso leggibile) | 16     |
| `ERRORE_FIXTURE` fermi su un **residuo dello scratch** (sotto), non sul test   | 53, probabili verdi in CI |
| restano rossi                                                                  | ~220   |

I verdi sono quasi tutto `pratiche` (29 su 37), `config`, `script`,
`documenti` e i test di registri/`event_log` di `vendite`.

✅ **Misurato da Tid il 21-09, sullo scratch, con `20260920-01` e il mirror di
`tipi_ruoli` applicati (00:29): 66 file da rosso a verde** contro il registro
della CI — dentro la forchetta della simulazione (62 sicuri, fino a ~115), e
senza altri rossi nuovi dopo il rimedio su `entita_tabella`. ⇒ il registro
scende **362 → 296 attesi**; il numero vero lo scrive la CI alla prossima
push su Tito-dev che tocca `db/`, e le righe le toglie
`pgtap-baseline-ci-rientrati.sh` quel giorno stesso.

🔵 **La modifica è scritta, non applicata:** `20_code/script/20260920-01-update-fn-pgtap-set-contesto-operatore-costruisce-se-vuoto`.
Sta **nel BB** e non nei 352 file — 352 copie di sei righe sono il building
block sbagliato: senza argomento, se nessun operatore esiste, la funzione
costruisce azienda+operatore e apre il contesto su quello. Con argomento, o
dove un operatore c'è (dbdev), **niente cambia**. SQL estratto provato in
`BEGIN … ROLLBACK` su `zeroerp_ci`: `plpgsql_check` pulito, ramo vecchio
identico, ramo nuovo costruisce `PGTR0005` e `fn_pgtap_emittente_operatore()`
risponde l'emittente costruito. Caveat dichiarato: l'operatore costruito è un
utente **tecnico**; un test il cui soggetto è l'operatore umano cade in
asserzione invece che in fixture (meglio, non peggio) e deve costruirsi il caso.

**Il resto è una ricetta fissa, un file alla volta** (la stessa dei 21 del
12-09 e dei sei del 17-09), e le cause residue dopo la modifica sono ancora
«cerca invece di costruire», un livello più giù:

* **47** cercano un `billing_account` → `dbops.fn_pgtap_crea_cliente_ba()` nel contesto;
* **35** incassano un NULL da un lookup (12 sono
  `registri_fatturazione.emittente_soggetto_ruolo_id` → `script.fn_pgtap_registro_fattura(sr)`);
* **29** hard-codano `SET LOCAL app.current_user_id = '1'` (l'utente 1 non esiste in CI);
* **7** vogliono `ART_TEST_BASE`/`ART_TEST_FALLBACK`, che non sono a seed → `dbops.fn_pgtap_crea_articolo()`;
* **~15** di `anagrafiche` sono legati a dati di **questa** macchina (gestore,
  CF `TTNMHL…`, PIVA `24551170426`, PDP GAS): si riscrivono, o si dichiarano
  test di macchina.

✅ **Applicato da Tid il 20-09 alle 23:53 su `zeroerp_ci`**, e la prima corsa
ha dato **un rosso che la CI non conosceva**: `script/test-fn-get-entita-ruolo-detail`,
test 9. ⭐ **Non è una regressione della modifica: è un difetto del database da
zero che la modifica ha reso visibile.** `config.tipi_ruoli.entita_tabella` /
`entita_colonna_codice` erano valorizzate **solo** da `00_schema/config/20260311-09`
(quattro `UPDATE … WHERE codice_interno = …`): su un DB ricostruito quella fase
gira **prima** di `80_data`, la tabella è vuota e gli UPDATE toccano zero righe
— su dev le righe c'erano da marzo e nessuno l'ha mai visto. In CI
`fn_get_entita_ruolo_detail` per EF risponde solo `meta`, e
`fn_search_soggetti_universale` non ha la tabella da cui leggere il codice: su
un'installazione nuova la ricerca soggetti per codice è rotta. Il test lo
avrebbe detto dal 12-03, ma fino al 20-09 in CI **saltava** (nessun EF da
guardare): verde per sottrazione, la forma esatta del corollario della regola
zero. 🔵 Rimedio scritto il 21-09, sede giusta (AGENTS.md: «i dati di `80_data`
si cambiano dal CSV»): le due colonne in coda a `tipi_ruoli.csv` + `- column:`
nel mirror `20250812-02` (`nullValue` → `"NULL"` col token scritto, nessuna
cella vuota prima). Provato col **render offline** del mirror in
`BEGIN … ROLLBACK` sullo scratch + corpo del pgTAP: 10/10. La lente su tutto
`config`/`ui` (colonne piene su dev e tutte NULL su `zeroerp_ci` a parità di
righe) trova **solo** queste due — il caso è unico, non una famiglia.

⚠️ **Due cose trovate per strada.**

1. **Cinque file chiudono con `COMMIT`, non `ROLLBACK`** —
   `anagrafiche/create-gestore-conto-soggetto`, `create-gestore-conto-bancario`,
   `test_vw_conti_bancari_per_ruolo_gestore`, `test_fn_get_conto_bancario_predefinito`
   (script di setup del gestore pre-template) e `test-soggetti-indirizzi-required`
   (l'ultimo caso finisce con `commit;` minuscolo). ⚠️ **E in sei file la riga
   di contesto gira in AUTOCOMMIT** (prima del `BEGIN;`, o file a più
   transazioni: i quattro sopra, `test-soggetti-indirizzi-required`,
   `test-soggetti-ruoli-indirizzi-required`): con la rev `20260920-01`, su un
   DB vuoto il primo di loro in ordine alfabetico **costruisce e committa**
   `PGTR0001` — un emittente residuo per corsa (visto sullo scratch alle
   23:54 del 20-09). Non cambia gli esiti (i file dopo lo trovano come su dev)
   ma è un residuo per costruzione: o la riga scende sotto `BEGIN;` (e nei file
   a più casi il mondo si costruisce per caso), o quei file si dichiarano
   setup e escono dalla suite. Il guardrail del preambolo potrebbe pretendere
   «contesto DOPO `BEGIN;`». Non si nota perché quando la
   fixture muore il COMMIT è un rollback; ma **nella simulazione la fixture è
   passata e hanno committato**, lasciando su `zeroerp_ci` quattro emittenti
   `PGTR0001-4` con utenti tecnici, soggetti, identità e venti registri — ed è
   quel residuo che ha fermato i 53 della tabella («non autorizzato per
   emittente 338»). Lo script di pulizia (dry-run verde: 8 soggetti, 4
   emittenti, 4 utenti, 20 registri, tutto e solo di oggi) è pronto e va
   lanciato da Tid. `COMMIT` → `ROLLBACK` è meccanico; **se sono test o
   setup** lo decide Tid. Il guardrail del preambolo non guarda la chiusura.
2. **Quattro file sono già verdi sullo scratch** senza toccare nulla
   (`anagrafiche/test-emittenti-fiscali-codice-forma`,
   `dbops/test-processi-jobname-wrapper`, `vendite/test-af-emit-batch-marchio-v1`,
   `vendite/test-registri-motore-trasloco-v1`): candidati RIENTRATI, ma li
   certifica solo la CI — `pgtap-baseline-ci-rientrati.sh` alla prossima push
   su Tito-dev che tocca `db/`, presa **quel giorno**.

#### La corsa del 21-09: 293 rossi, e UNA regressione che era il PRIMO file

✅ **La CI ha certificato** (corsa `35580357971`, push su Tito-dev dopo
PR #1631): **293 rossi su 674** contro un registro a 362 — i RIENTRATI sono da
togliere con `pgtap-baseline-ci-rientrati.sh` — e **una regressione**,
`anagrafiche/create-cliente.sql`, `ERRORE_FIXTURE`: «Indirizzo obbligatorio
mancante per soggetto … per tipo soggetto dettaglio 1, fallback id 1». Lo
stesso rosso, identico, sullo scratch `zeroerp_ci` la mattina; e **da solo il
file è verde** — è il caso «due volte in due giorni» per cui
`pgtap-baseline.sh` ha imparato quel giorno a conservare il motivo di ogni
`ERRORE_FIXTURE`, non solo del primo.

⭐ **La causa è la rev `20260920-01` stessa, in un modo che la sua intestazione
escludeva.** Sul database vuoto la riga di contesto chiama
`dbops.fn_pgtap_crea_emittente_operatore()`, che come ogni builder apre e
**richiude** la finestra dei differiti (`SET CONSTRAINTS ALL IMMEDIATE`, per
tutta la transazione — non si legge né si ripristina). L'intestazione diceva
«la riga di contesto sta PRIMA di `SET CONSTRAINTS ALL IMMEDIATE`, quindi il
file esce con i vincoli come li ha sempre avuti»: vero per 503 file, falso per
chi mette l'IMMEDIATE «dove l'unità di lavoro è completa», cioè in fondo, e fra
il contesto e quella riga costruisce una saga contando sulla finestra **di
default**. `create-cliente` inserisce il soggetto, poi contatto, indirizzi,
ruolo: con i vincoli già IMMEDIATE il guard `DEFERRABLE INITIALLY DEFERRED`
degli indirizzi scatta all'`INSERT` del soggetto. ⚠️ **E scatta solo sul primo
file della suite**: il secondo, `create-gestore-conto-bancario`, chiama il
contesto in **autocommit** (fuori dal `BEGIN;`) e **committa** `PGTR0001` — da lì
ogni file trova un operatore e percorre il ramo vecchio. Il debito dei «6 col
contesto in autocommit» (punto 1 sopra) **mascherava** questo: il giorno in cui
si chiude, ogni file con quella forma cade. Censiti (script sui 649 file con la
riga di contesto): sono **due** — `create-cliente` e
`test-soggetti-split-payment-cliente-pa` («Il soggetto non ha contatti validi»,
provato sullo scratch forzando il ramo che costruisce).

⚠️ **Erano tre** (2026-09-22, scratch `zeroerp_ci`: `dbops/test-processi-coda-automatica`,
`ASSERZIONE` sul t.5 «la fabbrica serve», rosso che la CI non conosceva).
Il censimento del 21-09 non lo vedeva perché lì la scrittura del soggetto
**non è un `INSERT` nel file**: sta dentro `script.fn_crea_utente_tecnico`,
chiamata da un `DO` della fixture — soggetto in un'istruzione, contatto in
quella dopo, guard differito in mezzo. Un criterio testuale sul file conta le
scritture che vede, e una scrittura che passa per una funzione è invisibile
(stessa classe del «valore che passa per tre funzioni» di C1). Provato in
transazione ritirata su dev nei due modi: con i vincoli IMMEDIATE la fabbrica
è rifiutata, con la finestra riaperta è servita. ✅ Sanato nella stessa forma
degli altri due (`SET CONSTRAINTS ALL DEFERRED` subito dopo la riga di
contesto, dichiarato in testa); nessuna riga di baseline da toccare, il file
torna verde. ⇒ Per il cancello «da decidere» qui sotto: un criterio che guardi
solo gli `INSERT` del file manca proprio questo caso; deve contare anche le
chiamate a funzioni che scrivono (`fn_crea_*`, `fn_pgtap_crea_*`), o dichiarare
di non vederle.

⛔ **Rimedio scritto — e uno ritirato.** Tre strade:

* *ripristinare il modo iniziale* dopo il builder: non si legge, e ricostruirlo
  dal catalogo disarmerebbe i 503 file che mettono l'IMMEDIATE **prima** del
  contesto — sul DB da zero i loro differiti non scatterebbero mai;
* *uscire IMMEDIATE in tutti i rami*, per omogeneità: scritto, provato in
  `BEGIN…ROLLBACK` sullo scratch (plpgsql_check pulito, i due file corretti
  8/8 e 5/5 su entrambi i rami, gli originali rossi anche su dev) e
  **ritirato**: un setter di contesto che chiude i vincoli pendenti li chiude
  *nei panni del nuovo attore*, cioè sotto un'altra RLS — la trappola che
  `rls/test-rls-listini-ef-whitelist-write` documenta — e due file
  (`script/test-fn-scope-ef-whitelist` e quello) aprono `DEFERRED` e poi
  cambiano attore col contesto: sarebbero morti in fixture;
* ✅ **dichiarare il contratto che c'è già e togliere ai file la presunzione**:
  la riga di contesto, *quando costruisce*, esce IMMEDIATE come ogni helper;
  con argomento, o dove un operatore esiste, non tocca i vincoli. È asimmetrico
  per costruzione, quindi la regola per i file è una: **dopo la riga di
  contesto non si conta sulla finestra differita di default** — chi la vuole
  la riapre con `SET CONSTRAINTS ALL DEFERRED` subito dopo.

Nello stesso giro: i due file riaprono la finestra e lo dicono in testa;
`20_code/script/20260921-18` (**solo `COMMENT`**, corpo invariato) scrive il
contratto sull'oggetto; template `_TEMPLATE.sql.txt` §3, guida §«`SET
CONSTRAINTS` non va sempre in testa» e §«Il mondo si costruisce», manual della
funzione. Provato come `zeroerp_app` sullo scratch: i due file **8/8 e 5/5**
sia con operatore presente (runner) sia col ramo che costruisce forzato;
`COMMENT` in `BEGIN…ROLLBACK` ok; guardrail preambolo/runOnChange/preCondition
verdi. Nessuna riga di baseline da toccare: il file non era in nessun
registro, e torna verde.

🔵 **Da decidere (Tid)** — un cancello che renda la regola leggibile da uno
script: `guardrail_pgtap_preambolo.py` potrebbe pretendere che, se il primo
`SET CONSTRAINTS ALL IMMEDIATE` sta **dopo** una scrittura che segue la riga di
contesto, fra le due ci sia un `SET CONSTRAINTS ALL DEFERRED` dichiarato. Il
censimento del 21-09 dà 9 candidati e 7 falsi positivi (quattro col contesto in
autocommit, tre senza differiti in mezzo): con quel tasso il cancello va
disegnato con cura, o resta una lente.
⛔ **Aggiunta del 23-09 sera**: il criterio «`IMMEDIATE` dopo una scrittura»
è cieco sui file che **non hanno nessun** `IMMEDIATE` — i
`pgtap-differiti: escluso` contano sulla finestra per dichiarazione. Nove sono
caduti sullo scratch appena il giro 2 ha tolto il residuo `PGTR0001`, e sono
stati sanati (verdi): un cancello deve contare anche quella forma. Censimento e
dodici candidati in
[brief-db-fixture-che-costruiscono-giro-2.md](../work-done/brief-db-fixture-che-costruiscono-giro-2.md) §11. ⚠️ Residuo del lavoro di prova sullo
scratch: le corse forzate sui quattro file col contesto in autocommit hanno
**committato** dodici `PGTR0002…0013` (emittente + utente tecnico + soggetti)
alle 11:23 — stessa natura del residuo `PGTR0001` del punto 1, stesso script di
pulizia, da lanciare da Tid.

> ⭐ **Incrocio con D11, e cambia l'ordine dei due lavori.** Dei **123**
> `throws_ok` senza discriminante, **102** stanno in file già a registro qui, e
> **94** di quei 102 sono `ERRORE_FIXTURE` — file che su un database ricostruito
> **non eseguono nessuna asserzione**. Sanare il discriminante lì è severità che
> si vede solo su dbdev: in CI è lavoro invisibile finché la fixture non li fa
> partire.

⭐ **Dal 22-09 il pezzo che resta ha un brief suo**,
[brief-db-fixture-che-costruiscono-giro-2.md](../work-done/brief-db-fixture-che-costruiscono-giro-2.md),
con il censimento della **forma** invece che delle cause: dei 361 file a
registro, **205** costruiscono una tabella di riferimenti **pescando** (150
pescano il billing account, 170 lo pescano da qualche parte nel file) e **tre**
usano un builder. ⛔ Il fatto che cambia l'unità di lavoro: la causa misurata è
la **prima** che il file incontra, quindi curarla non chiude il file — un file
che *cerca* va portato a *costruire* tutto insieme. La forma proposta è un **BB
di composizione** (`dbops.fn_pgtap_crea_mondo_cliente()`): i cinque builder
atomici esistono già, e ciò che manca è proprio il pezzo che porta la **regola
d'ordine** fra mondo, legame del BA e contesto — oggi riscritta a mano in ogni
file. ✏️ **Il BB è scritto e provato il 22-09** (`20260922-17`, più il presidio
`dbops/test-fn-pgtap-crea-mondo-cliente-v1.sql`, 9/9 sullo scratch da zero):
decisioni di forma prese, apply a Tid, e i lotti — 43 file su sei schemi che
escono interi dal registro — partono da lì.

---

### 🟠 D8 — `acquisti` e `magazzino`: modellati, non scritti

✅ **Deciso l'11-09-2026 (Tid): sono il PROSSIMO CANTIERE**, non congelati —
scritto in `.codex/PROJECT_CONTEXT.md`, con la conseguenza che questa voce
cercava: *ogni decisione presa su `vendite` è presa anche per `acquisti`*, e
un'asimmetria fra i due si chiude subito, non in una «fase due». ⚠️ `storico`
**non** è coperto dalla decisione come dominio (sul lato RLS l'ha chiuso D3).
Ciò che segue resta vero finché il comportamento non c'è.

| Schema                | Tabelle | FK  | CHECK | Funzioni | Viste | Test  |
| --------------------- | ------- | --- | ----- | -------- | ----- | ----- |
| `magazzino`           | 26      | 57  | 71    | **2**    | 4     | **1** |
| `acquisti`            | 9       | 42  | 25    | **2**    | 0     | **0** |
| `vendite` (confronto) | 88      | 359 | 194   | 292      | 60    | 253   |

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

### 🟡 D11 — I registri di debito non calano

Un registro di debito è una buona invenzione **a condizione che scenda**. Stato
al 2026-09-08, salvo dove è scritta un'altra data:

| Registro                                   | Oggi                                                                                       |
| ------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `dbops.vw_codici_errore_da_dichiarare`     | **545** su 897 codici                                                                      |
| `db/pgtap/baseline-rossi-ci.tsv`           | **361** file al 2026-09-22 (362 al 20-09, 293 `ERRORE_FIXTURE` + 69 `ASSERZIONE`; una riga uscita col ritiro di `vw_contatore_merce`) — nato il 09-09 con 407; **295 attesi** dal 21-09 (66 rientrati sullo scratch, D7) |
| `SOGLIA_THROWS_SENZA_DISCRIMINANTE`        | **123**                                                                                    |
| `dbops.vw_fk_con_indice_missing_policy`    | **57**                                                                                     |
| `db/pgtap/baseline-rossi.tsv`              | **16** file al 2026-09-12 (9 `ERRORE_FIXTURE`, 7 `ASSERZIONE`) — erano 19                  |
| `dbops.rls_perimetro_debito`               | **7** righe (2026-09-20 — era 10, → D2)                                                    |
| `backend/scripts/tests/baseline-smoke.tsv` | 2 su 16 script (2026-09-12)                                                                |
| Header di licenza mancanti                 | 2.042 file (misura 2026-08-26)                                                             |
| `dbops.vw_indici_ridondanti_prefisso`      | 1                                                                                          |
| Codici vivi senza messaggio                | 6 (tutti `W_`, §2.3)                                                                       |
| `dbops.vw_processi_che_bypassano`          | 1 (dichiarato, con data di ritiro)                                                         |

⭐ L'ultima riga è l'unica fatta bene: **una** voce, con il motivo e il momento in
cui sparisce. Le prime quattro sono liste lunghe, e la guida sui presidi dice
esattamente perché è un problema: *«il registro nasce piccolo. Se parte con
trenta righe, nessuno lo leggerà»*. `rls_perimetro_debito` è nato nella forma
giusta — ogni riga con la sua ragione — ed è calato di due terzi nel cantiere
che l'ha aperto.

⚠️ **E uno di questi registri cresce: i codici.** 508 → **545** su 897 (08-09 →
20-09) mentre `rls_perimetro_debito` scendeva. Il motivo è strutturale e sta
nella forma: gli altri hanno una **causa** e un **rimedio** (riscrivere la
fixture, discriminare l'asserzione, armare la RLS), il registro dei codici
misura il *terzo lato* — le dichiarazioni dell'applicativo — che si allarga a
ogni dominio nuovo. Non è un presidio che mente: è un presidio **senza un
verso**, ed è esattamente ciò che D11 chiede di dargli.

⚠️ Le due baseline pgTAP meritano una riga a parte: **293 + 9 file falliscono
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

### 🔴 D15 — Nessuno analizza le tabelle: ogni piano nasce da stime di default

> Emerso il 2026-09-22 chiudendo D14 (brief §15.2 e §16.6). ⛔ Non è un residuo
> di quel cantiere: è la **condizione** in cui sono state prese tutte le misure
> di piano di questo progetto, compresa ogni riga di D14.

In `vendite` **82 tabelle su 87 non hanno mai avuto un `ANALYZE`** — né a mano né
dall'autovacuum. Con le soglie di default (50 righe più il 10%) una tabella
piccola non ci arriva mai da sé, e nello scheduler non c'è nessun job che le
analizzi.

⛔ **La conseguenza non è «dbdev è lento»**: è che il planner sceglie su stime di
default, e il piano **si ribalta da solo**. Fatto datato del 22-09: lo stesso
corpo, senza nessuna modifica in mezzo, misurava 63 ms alle 16:12 e **95–104 ms
alle 17:19**, con lo stesso piano storto. ⇒ Una misura di piano, in qualunque
cantiere, è **rumore** finché le statistiche non ci sono — e un cantiere che
promette un guadagno in millisecondi dichiara un numero che non può difendere.

⭐ Ciò che regge, ed è il modo in cui D14 è stata portata a casa, sono le **forme**
del piano — `loops=1`, `Index Cond`, una lettura invece di N — non i millisecondi
confrontati fra due momenti.

⚠️ **Il perimetro non è `vendite`**: la domanda sul modello è se esista **un**
posto che tiene aggiornate le statistiche del database, e oggi non esiste. Sede
`dbops`/`maintenance`, non un dominio: soglie di autovacuum per le tabelle
piccole, un job nello scheduler, o entrambi — con il presidio che dice quando
l'ultimo `ANALYZE` è più vecchio di quanto si è dichiarato. ⭐ È un
**prerequisito**, non una miglioria: chiunque riapra una famiglia di funzioni per
prestazioni lo trova davanti.

### 🟡 D16 — Test con una data scritta a mano: diventano rossi da soli

> Emerso il 2026-09-23: `vendite/test-nc-rata-unica-v1.sql`, test 6, rosso senza
> che fosse cambiato il codice.

Il test creava la nota di credito con `DATE '2026-09-10'` e poi le assegnava il
numero. La numerazione applica la **finestra di emissione** del registro: un
documento non può essere datato più indietro di N giorni. Quando il test è stato
scritto (17-18 settembre) il 10-09 era dentro la finestra. Il 23-09 la prima data
ammessa era l'11-09, e il test è morto con «la data del documento è troppo
vecchia perché sia ancora emettibile».

⛔ **Non è un caso isolato, è una classe.** Ogni volta che il database applica una
regola che dipende da **oggi** (finestra di emissione, scadenze, congelamenti,
competenze chiuse), un test che scrive a mano una data è una bomba a tempo:
verde il giorno in cui nasce, rosso qualche settimana dopo, senza che nessuno
abbia toccato niente. E il rosso arriva sempre nel momento peggiore, mentre si
sta lavorando ad altro, e sembra una regressione.

**La regola:** in un test, una data che passa da una regola temporale si scrive
**relativa a oggi** (`current_date`, `current_date - 5`, il primo del mese
corrente…), mai come letterale. Le date assolute vanno bene solo quando la regola
non guarda il calendario (per esempio una competenza passata a una funzione pura).

**Sanato:** il test 6 (fixture a `current_date`, e l'atteso del test 3 calcolato
dalla stessa data), con un commento sul perché.

**Che cosa resta:**

* ⏳ **Censimento.** Oggi nei pgTAP ci sono decine di date scritte a mano. Quasi
  tutte sono competenze, attività, ordini o preventivi, e non passano dalla
  finestra di emissione (se ci passassero, sarebbero già rosse). Il censimento
  vero va fatto per **regola temporale** — quali regole del DB leggono
  `current_date` — e poi per test che le attraversano, non per ricerca testuale
  delle date.
* 💡 **Presidio possibile**: un guardrail statico come
  `scripts/guardrail_pgtap_preambolo.py`, che segnali un letterale `DATE '…'`
  nella colonna `data` di un documento fiscale che il test poi numera. Da
  valutare dopo il censimento: senza sapere quali regole sono temporali, il
  presidio sarebbe una ricerca testuale, cioè il criterio sbagliato.

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

## 5. Scorecard — pesata, non mediata (2026-09-08, aggiornata al 2026-09-20)

Il peso è **la conseguenza di un difetto in quell'area**, non la sua estensione.

| Area                                   | Peso    | Voto       | Perché                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| -------------------------------------- | ------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Catena di verifica (CI)**            | 🔴 alto  | **7,5/10** | Dal 2026-09-09 la suite pgTAP è un cancello vero: baseline misurata dalla CI, niente `continue-on-error`, bootstrap che fallisce invece di passare. Resta il registro a 362 — 296 attesi dal 21-09 — che deve calare (D7)                                                                                                                                                                                                                                        |
| **Perimetro dei dati (RLS)**           | 🔴 alto  | **8/10**   | D2 e D3 chiusi l'11-09-2026: dominio documento protetto fino ai satelliti, versioni di storico con scope congelato, e due presidi a criterio (`vw_rls_perimetro_scoperto`, `vw_storico_scope_da_dichiarare`) che vedono le tabelle nuove. Restano le due policy inerti di `acquisti` (D4 → D8), a registro con la ragione; `shop.ricevute` armata il 12-09. D13 (il `RETURNING` del BA per gli operatori non di default) chiuso il 13-09 |
| **Copertura test**                     | 🔴 alto  | **4/10**   | 687 file (23-09), ma su un DB ricostruito da zero la suite è rossa su **229 file su 687** (baseline su `zeroerp_ci` del 24-09; il registro è ancora a 361 finché la corsa CI non certifica i rientrati). Il 38% delle funzioni non è mai nominato (D7)                                                                                                                                                                                                                                                                                          |
| **Postura di sicurezza degli oggetti** | 🟠 medio | **7,5/10** | I tre invarianti di D5 presidiati per criterio (`search_path` dal 12-09, pin applicati). Non di più per i due rubinetti di D6-bis e per il pezzo nuovo: registro `sec_functions_owner` e sync scrivibili/eseguibili da `zeroerp_app`                                                                                                                                                                                                     |
| **Simmetria del dominio**              | 🟠 medio | **4/10**   | `acquisti` e `magazzino` modellati e non scritti (D8). La decisione dell'11-09 («prossimo cantiere») dà al debito un verso, ma il voto misura il comportamento, che ancora non c'è: *una decisione non scrive il codice*                                                                                                                                                                                                                 |
| **Osservabilità dei presidi**          | 🟠 medio | **7/10**   | D10 chiuso l'11-09-2026: le 30 viste hanno un destinatario che ha già riferito, e la classificazione è **dato** (`dbops.presidi`). Non 8+ per il debutto col rumore (processi ritirati in `vw_job_run_da_guardare`)                                                                                                                                                                                                                      |
| **Gestione del debito**                | 🟠 medio | **6/10**   | Registri ben progettati; le liste lunghe restano lunghe, e ne è nata una nuova da 362 (D11)                                                                                                                                                                                                                                                                                                                                              |
| **Pattern trigger e automazioni**      | 🟡 basso | **7,5/10** | Riuso raro (758 trigger da due funzioni), framework `ci_apply` eccellente; la forma per-figlia non scala e la fase è al 66% (D9)                                                                                                                                                                                                                                                                                                         |
| **Error handling / codici errore**     | 🟡 basso | **8,5/10** | Contratto a tre lati esplicito e presidiato; il registro **sale**                                                                                                                                                                                                                                                                                                                                                                        |
| **Disciplina Liquibase**               | 🟡 basso | **9/10**   | 3.354 changeSet, cinque cancelli dedicati, tutti nati da un incidente reale                                                                                                                                                                                                                                                                                                                                                              |
| **Documentazione**                     | 🟡 basso | **8,5/10** | Copertura piena; sottile dove il dominio è sottile                                                                                                                                                                                                                                                                                                                                                                                       |
| **Naming**                             | 🟡 basso | **8/10**   | 94-99% sui vincoli; 66% sulla fase dei trigger, che è la voce con conseguenze                                                                                                                                                                                                                                                                                                                                                            |

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

> `[ ]` = **da fare** — sono le voci di §3. `[x]` = **fatta** — resta qui perché
> una check-list completa serve a chi la scorre, e il **dettaglio** di ognuna è
> in §7 «Attività svolte» (con la data e il brief).

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
      scrivibili/eseguibili da `zeroerp_app`) — dal 19-09 brief suo,
      `work-in-progress/brief-db-registro-owner-e-sync-riservati-al-migratore.md`
      (forma in §2, tre decisioni per Tid in §6), stima ≈ mezza giornata.
      `EXECUTE` a PUBLIC su `fn_sync_functions_owner`: valutato, resta — e
      resta anche la voce esplicita dell'app (loop dei grant): la sync si
      difende da sola, con `session_user`.
      ✅ La «riga obbligatoria» su `public.dblink(...)` in
      `fn_get_or_create_session_tx_id` **non serve più così com'era scritta**:
      il pin applicato il 12-09 include `public`, quindi il `dblink` si
      risolve. Vale ancora come vincolo di D6-bis (sotto): se un giorno quel
      pin si stringesse, prima la qualifica.
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
* [~] **D7** — far calare il registro della CI (362, di cui 293 nella fixture)
      e portare a zero i 9 file della baseline di sviluppo che falliscono nella
      *fixture*. ✅ 12-09: i **21 del perimetro** riscritti (20 verdi sui due
      database, uno in CI con il passo di provisioning nuovo); dal 12-09 al
      20-09 il registro è sceso **403 → 362**.
      ✅ 20-09: **triage delle cause fatto** (§3 D7): una causa sola in tre
      forme, e la radice in una riga di preambolo. ✅ 21-09: `20260920-01`
      applicato (il BB costruisce il mondo se il DB è vuoto) + il rimedio
      da zero su `tipi_ruoli.entita_tabella` (CSV + mirror): **66 file da
      rosso a verde** sullo scratch, 362 → **295 attesi** in CI, da
      certificare con la corsa e `pgtap-baseline-ci-rientrati.sh`. ⚠️ **Al
      2026-09-22 il registro è ancora a 361 file** (l'unica riga uscita è quella
      del pgTAP ritirato con `vw_contatore_merce`): la corsa del 21-09 ha
      misurato **293 rossi su 674**, ma i RIENTRATI non sono stati tolti —
      `pgtap-baseline-ci-rientrati.sh` legge il log della corsa e va lanciato
      **quel giorno**, perché il log scade. ⭐ 22-09: il pezzo che resta ha un
      brief suo — `work-done/brief-db-fixture-che-costruiscono-giro-2.md` (chiuso il 23-09)
      — e parte dal **BB di composizione** (`fn_pgtap_crea_mondo_cliente`), non
      dalla ricetta per file: 205 file su 361 compongono il mondo a mano, e la
      regola d'ordine fra mondo, legame del BA e contesto non sta in nessun
      oggetto. ✏️ BB **scritto e provato** il 22-09 (`20260922-17` +
      `dbops/test-fn-pgtap-crea-mondo-cliente-v1.sql`, 9/9 su `zeroerp_ci`,
      riferimenti morti e rubinetto verdi, cancelli statici verdi): da
      applicare. Poi i lotti del brief §5, dai sei schemi piccoli (43 file, che
      escono interi dal registro). ✅ **Lotto 1 in corso, 23-09**: dei 43 file
      **16 erano già verdi** (il `20260920-01` ha fatto effetto, il registro non
      è stato aggiornato), **12 riscritti e verdi** su entrambi i database (114
      asserzioni), `20260923-01` scritto (il builder degli articoli sceglie la
      UoM) e la soglia `throws_ok` scesa **123 → 121**. ⛔ Due findings: un test
      era **verde per l'errore sbagliato** (super admin) e due sono rossi per un
      **difetto del DB da zero** — `storico.parameters` ha `parameter_id` mentre
      il trigger passa `parameters_id`, quindi su un'installazione nuova ogni
      UPDATE su `config.parameters` fallisce. ✅ *Chiuso il 2026-09-25 da
      [brief-db-storico-colonna-fk-dei-trigger.md](../work-done/brief-db-storico-colonna-fk-dei-trigger.md):
      le madri erano cinque, non una, e quattro rotte anche su dbdev.* ✅ **Lotto 1 CHIUSO il 23-09**:
      i 9 di `pagamenti` chiedevano tutti una fattura, e la decisione è stata
      **un BB, non nove copie** — `20260923-04` (`fn_pgtap_crea_fattura`:
      mondo, coppia emittente/utility, registro coerente, stato alla nascita,
      e il terzo parametro per la seconda fattura dello stesso cliente) e
      `20260923-05` (`fn_pgtap_crea_filiale_bancaria`, perché
      `bank_branches` è dato di macchina). **21 file riscritti** in tutto,
      235 asserzioni verdi sul database da zero. ✅ **Applicato il 23-09 su
      entrambi i database, nessuna regressione, committato** (`9304f209c`,
      PR #1649). ⏳ Il registro però è **ancora a 361 file**: le righe rientrate
      le toglie `pgtap-baseline-ci-rientrati.sh` leggendo il log della corsa CI
      — e il log scade, quindi va lanciato il giorno stesso della push. Il
      ✏️ **Lotto 2 in corso dal 23-09** (`anagrafiche` 39 + `script` 31): il
      debito dei `COMMIT`/autocommit è **chiuso** — nella suite non committa più
      nessun file — ed era più grosso di quanto si vedesse: la `PGTR0001` che
      quei file committavano teneva verdi **altri sei file** del lotto.
      Builder nuovo `fn_pgtap_crea_gestore` (`20260923-06`, applicato). 12 file
      su 70 verdi sul mondo vuoto; restano il cliente da costruire, `pdp_id`,
      `RIS_UMANA`, i registri e l'utente di sessione fissato a `'1'`.
      ✅ **Giro 2 CHIUSO il 23-09** (brief in `work-done/`): lotto 2 da 12 a
      **51 verdi su 70** (+1 verde da owner), **18 rossi** rimasti da guardare
      uno per uno (elenco nel brief, §11 «Stato di chiusura»). Builder nuovi,
      tutti applicati senza regressioni: `fn_pgtap_crea_operatore_umano`
      (`-08`), `fn_pgtap_crea_pdp` (`-09`), `fn_pgtap_crea_listino` (`-50`,
      copia del lotto 1 ritirata). Difetti del **prodotto** trovati costruendo
      invece di pescare: profilo SUPER_ADMIN per id cablato in
      `fn_crea_risorsa_umana_v2` (`-10`); `fn_get_indirizzo` e
      `fn_get_indirizzo_by_soggetto` confrontavano il codice col codice_interno,
      e il dettaglio di ricerca non trovava mai l'indirizzo di ripiego (`-49`);
      il presidio C1 contava le fixture come scrittori (`-51`); i CSV di
      `tipi_utenze`/`classi_utenze` non li caricava nessuno (`-52`/`-53`).
      Tre verdi **finti** smascherati (skip soft che scriveva il valore atteso)
      e sei test che asserivano per la ragione sbagliata. ⏳ Resta: la corsa CI
      che certifica i rientrati (baseline su `zeroerp_ci` del 24-09: **229 rossi su 687**, contro
      361 in baseline) e i 18 rossi.
* [x] **D13** — ✅ chiuso il 2026-09-13: changeSet `20260913-01/02/03`
      applicati, baseline di sviluppo senza regressioni, brief
      `brief-db-ba-riserva-emittente-operatore-d13.md`. ✅ Le tre copie
      Python della regola vecchia sono delegate al check dal 13-09 (team BE,
      brief §6.2). Restano due decisioni di modello in coda (§3.4).
* [~] **D11** — dare a ciascun registro lungo un **verso** (chi lo abbassa, di
      quanto, entro quando), o dichiararlo congelato con il motivo.
      ✅ 20-09: la soglia `throws_ok` è scesa **129 → 123** discriminando le sei
      asserzioni di `catalogo/test-articoli-vincoli-note-uom-overlap.sql` — una
      delle quali era verde per l'errore sbagliato (§7 D11). ⛔ Restano i due
      registri grossi, e sono quelli che non hanno un verso: i **293** rossi
      della CI e i codici da dichiarare, che sono **saliti** (508 → 545).
* [ ] **D11-bis** — scrivere il messaggio dei sei `W_` che non ce l'hanno
      (append al CSV dei messaggi, mai un loader nuovo), oppure dichiarare che
      quei codici non raggiungono mai un operatore — e scriverlo nel `note`.
* [x] **D14** — ✅ chiusa il 2026-09-22, brief archiviato in
      `work-done/brief-db-partita-merce-per-documento.md`: otto giri fra il 17 e
      il 22-09, **sette applicati** e l'ottavo provato e **ritirato** lo stesso
      giorno. La partita di merce si legge **per documento**, l'eleggibilità ha
      **una** implementazione e il classificatore, `af` e i billing account si
      leggono **per chiave** (§7). Residui dichiarati, ciascuno con la sua sede:
      due decisioni **non prese** (la catena del `sospetto`, raccomandato
      lasciar stare; **D8(b)**, che nessuna misura reclama), i tre `LIKE` di
      `fn_accredita_riga_reso` — un changeSet suo —, i preventivi come quarto
      adottante del BB «righe solo in bozza» (dopo il censimento
      dell'approvazione prezzo) e tre voci BE (due commenti che nominano oggetti
      ritirati, la decisione sui pre-check `_STATI_RIGHE_MODIFICABILI`).
      ⛔ La statistica assente **non** è un residuo di questo cantiere: è **D15**.
* [ ] **D15** — dare al database **un** posto che tiene aggiornate le
      statistiche (`dbops`/`maintenance`): in `vendite` 82 tabelle su 87 non
      hanno mai avuto un `ANALYZE`, quindi ogni piano nasce da stime di default
      e si ribalta da solo. ⛔ È un **prerequisito** di qualunque cantiere che
      misuri un piano, non una miglioria — e finché non c'è, un guadagno
      dichiarato in millisecondi non è difendibile.

### 🟡 Struttura

* [ ] **D9** — valutare la primitiva unica «figlie da `pg_constraint`» al posto
      dei guard per-figlia, partendo da `catalogo.articoli` (29 `EXISTS` per
      update).
* [ ] **D9-bis** — portare la fase (`_a10_`/`_z90_`) sul 34% di trigger che non
      ce l'ha, o dichiarare che per quelli l'ordine è indifferente.
* [ ] **D12** — nessuna azione: la documentazione seguirà il dominio.
* [ ] **D16** — censire le regole del DB che leggono `current_date` e i pgTAP
      che le attraversano con una data scritta a mano; poi decidere se serve un
      guardrail statico.

---

## 7. Attività svolte — cosa è stato chiuso, e con che cosa

> Questa sezione è il **rovescio di §3**: qui sta ciò che era un difetto e non lo
> è più. Un numero che compare in **tutti e due** i posti (D4, D5, D6, D7, D11,
> D12) non è una ripetizione: in §3 c'è **il lavoro che resta**, qui **quello
> fatto**. ⭐ **D14 non è più in §3**: è chiusa, e ciò che la sua chiusura ha
> scoperto è una voce nuova: **D15**, le statistiche che non esistono.
>
> Le date sono quelle dichiarate nei brief, e i brief restano la sede del
> dettaglio: qui si dice **che cosa è cambiato nel sistema**, non come ci si è
> arrivati.

### ✅ D1 — Il cancello pgTAP in CI — chiuso il 2026-09-09

Il passo «Suite pgTAP» girava con `continue-on-error: true` e leggeva una
baseline mai committata: **600 file e ~6.183 asserzioni** buttati via a ogni
corsa. Ora il classificatore è bilingue (`ERRORE|ERROR`, il server della CI parla
inglese), `--update` **si rifiuta di scrivere** se non passa nemmeno un file,
`baseline-rossi-ci.tsv` è committato e **misurato dalla CI** (407 rossi su 601
alla prima corsa), `continue-on-error` è tolto e il ramo di bootstrap
**fallisce** invece di passare. ⭐ *Un cancello che passa perché non ha misurato
niente è peggio di un cancello assente.*

### ✅ D2 — Il perimetro emittente, fino a righe e satelliti — chiuso l'11-09-2026

Era protetta **una** famiglia di documento su sei, e le righe delle altre
cinque erano leggibili da qualunque operatore. Ora sono **nove** (più le sette
partizioni di `vendite.note`), il registro del debito è sceso da **33 a 10
righe** e `db/pgtap/rls/` è passato da 30 a 39 file. ⭐ In servizio resta un
**presidio a criterio transitivo** (`dbops.vw_rls_perimetro_scoperto` +
`rls_perimetro_debito` + `test-rls-perimetro-scoperto.sql`): una tabella nuova
con una FK verso una protetta esce `NON_DICHIARATO` e fa rosso il test 2.
Brief `work-done/brief-db-perimetro-emittente-righe-documento.md`.

### ✅ D3 — Lo `storico` porta il proprio perimetro — chiuso l'11-09-2026

120 tabelle senza RLS e 52 leggibili dall'app: chiudere D2 senza D3 avrebbe solo
spostato il punto da cui si legge. Ora lo scope **si cattura alla scrittura e si
congela** (`origine_schema` + `scope_emittente_fiscale_id`, mappa
`storico_scope_policy` con ripiego sull'archivio del padre), le **37 shadow**
delle madri protette hanno policy generata, backfill di **65.751 versioni** senza
residue, `REVOKE DELETE` all'app su tutto lo schema, e
`vw_storico_scope_da_dichiarare` vede quelle che non lo portano. Le tabelle nuove
nascono **armate** dal generatore: il lavoro è stato **uno**, non 120. Nello
stesso giro `dbops.audit_log` prende un **cancello** alla scrittura più il
`REVOKE UPDATE/DELETE` dichiarato nel loop dei grant — *un registro di audit
modificabile da chi è auditato non è un registro*.
Brief `brief-db-rls-storico-scope-congelato.md`.

### ✅ D4 — Le policy inerti — chiusa il 2026-09-12 (il resto è D8)

`acquisti.ddt`, `acquisti.ordini`, `shop.ricevute`: la policy c'era, la RLS era
spenta — il difetto che si auto-nasconde, perché `EXISTS (SELECT 1 FROM
pg_policies …)` legge verde. ✅ L'invariante generale è presidiato dal **criterio
`POLICY_INERTE`** (caso costruito nel test 7), e `shop.ricevute` è stata
**armata** il 2026-09-12 (`20260912-42/43`, registro 10 → **8**). Le due di
`acquisti` sono **D8**: *manca il modello, non l'accensione*.
Brief `brief-db-fixture-che-costruiscono-d7-d6-d4.md` §5.

### ✅ D5 — I tre invarianti di forma hanno un presidio — chiusa il 2026-09-12

Tre proprietà che, se violate, **non producono nessun errore visibile**, ora
hanno un presidio a **criterio** (non un elenco di nomi):

| Invariante                                                | Presidio                                                                                                    |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Una vista che tocca dati in RLS ha `security_invoker`     | criterio transitivo dal 2026-09-07, ha sostituito quattro elenchi a mano. Zero violazioni                   |
| Una tabella con policy ha la RLS **accesa**               | criterio `POLICY_INERTE` dall'11-09 (le 2 violazioni rimaste sono D8)                                       |
| Una funzione `SECURITY DEFINER` ha un `search_path` fisso | `db/pgtap/dbops/test-security-definer-search-path-v1.sql` dal 12-09, con due soglie che possono solo calare |

⭐ **La lezione che resta, ed è la ragione per cui D5 esiste**: il criterio con
cui nasce un presidio è un **indicatore in ritardo** — le prime due righe hanno
morso prima di essere presidiate, la terza è stata presidiata prima di mordere
solo perché le è passato accanto un cantiere. Non è una voce da fare: è il
motivo per cui i presidi si scrivono **quando un cantiere ci passa**.

### ✅ D6 — I pin del `search_path` — chiusi il 2026-09-12

Tre `SECURITY DEFINER` di `postgres` senza `search_path`, una sul percorso di
**305 trigger** (`fn_get_or_create_session_tx_id`), una che cambia il
proprietario di funzioni. Pin applicati (`20260912-39/40/41`) nella timeline
normale, senza superuser: due col **prestito di proprietà** via
`fn_sync_functions_owner`, la terza con una **copia di servizio** della sync —
la sync non può prestarsi a sé stessa. La forma è `pg_catalog, public, pg_temp`
e **non** `pg_catalog, pg_temp`: la catena tocca `dblink`, che vive in `public`.
⚠️ La lezione del giro: la forma «prudente» avrebbe **accecato** `dblink` dentro
un `WHEN OTHERS`, spegnendo il tracciamento delle transazioni **senza un rosso da
nessuna parte** — *una forma canonica uguale per tutte non esiste: si decide per
funzione, guardando ciò che chiama.* Ciò che resta è il registro (§3 D6).

### ✅ D7 — Il triage è partito dal perimetro — 2026-09-12, in CI dal 14-09

Dei rossi sul database ricostruito da zero, i primi **21** erano i test di
`script/fn_scope_*` (12) e di `rls/` (9) — cioè quelli che decidono *chi vede
cosa* — tutti con la stessa causa: la fixture **cercava** i soggetti nei dati
esistenti, e su un database ricostruito `anagrafiche` è a zero. Riscritti con
fixture che **costruiscono** il mondo: **20 verdi** su dbdev e su `zeroerp_ci`,
e il ventunesimo era un'altra classe (in CI il ruolo batch non veniva
provisionato) e ha avuto il suo passo in `ci-validate.yaml`. Sono **usciti dal
registro**, e da allora i rientrati li toglie
`scripts/pgtap-baseline-ci-rientrati.sh` **leggendo il log della corsa**, non una
mano. Il debito che resta è in §3 D7. Brief
`brief-db-fixture-che-costruiscono-d7-d6-d4.md` (in `work-done/` dal 19-09).

### ✅ D10 — I presidi hanno un destinatario — chiuso l'11-09-2026

Trenta viste di presidio che nessuno guardava — e sei lavori falliti da tre
notti in una vista che si chiama `vw_coda_lavori_**da_guardare**`. Ora la
classificazione è **dato** (`dbops.presidi`), il **digest** lo costruisce il
backend, due timer sono in servizio (giornaliero 07:00, settimanale lunedì
07:30), e dal 19-09 il contatore è anche a video, nel **pallino in topbar**,
sullo stesso metro. Il primo giro ha già riferito, e ha insegnato il resto: un
allarme su un processo obsoleto dal 07-09 — *un presidio che comincia col rumore
insegna a non guardarlo*, ed è proprio la proprietà che il cantiere comprava.
Brief `brief-db-un-destinatario-per-i-presidi.md`.

### ✅ D11 — I registri che sono calati (e quello che cresce)

Non tutti i registri di §3 stanno fermi: `dbops.rls_perimetro_debito` è sceso da
**33 a 7 righe** (ogni riga con la sua ragione tecnica, calato nei cantieri D2,
D4 e in quelli passati dopo), `db/pgtap/baseline-rossi.tsv` da **19 a 16** file
sul database di sviluppo, e `db/pgtap/baseline-rossi-ci.tsv` da **403 a 362**
(2026-09-20). ⭐ È la forma che la guida prescrive e che qui ha funzionato:
registro piccolo, ogni voce con il motivo, e un cantiere che lo abbassa mentre
passa. ⚠️ E ce n'è uno che invece **cresce** — `vw_codici_errore_da_dichiarare`,
508 → 545 su 897: è il registro **senza un verso** (§3 D11).

#### La soglia `throws_ok`: 129 → 123, e il test che era verde per l'errore sbagliato

Il 2026-09-20 sei asserzioni di
`db/pgtap/catalogo/test-articoli-vincoli-note-uom-overlap.sql` hanno ricevuto il
loro discriminante — `23505` per i tre casi di unicità (il codice duplicato e i
due `uq_artuomop_*`), `23514` per il CHECK su
`note_target_tipo`, `23503` per la FK su `note_id`, `23P01` per l'`exclusion`
sull'overlap — e la soglia del cancello è scesa a **123**.

⚠️ **Non è stata una passata di cosmetica: una di quelle sei era verde per
l'errore sbagliato.** Il test 11 dichiarava «codice articolo duplicato:
bloccato» e in realtà moriva su **`23502`** — un `NULL` su `uom_id`, che è NOT
NULL — perché l'INSERT ometteva quella colonna *e* il codice «duplicato» era
`'ART…'` mentre l'articolo creato sopra è `'ARC…'`: non duplicava niente. Il
vincolo che il test credeva di collaudare non era mai stato raggiunto, e il test
passava lo stesso.

⭐ **La sonda, ed è tutta qui** — il metodo vale più delle sei righe:

1. su una **copia usa-e-getta** del file, sostituire il secondo argomento con uno
   SQLSTATE impossibile (`'ZZZZZ'`), senza toccare il repository;
2. far girare il file: pgTAP non accetta più qualunque errore, e nel messaggio di
   fallimento stampa `caught: <stato>: <frase>` — cioè il dato che si cercava,
   per **tutte** le asserzioni, in una corsa sola;
3. leggerlo: l'asserzione che dichiarava lo stato giusto resta verde dopo il
   ripristino, quella sbagliata si spiega da sé;
4. **prima** correggere la causa, **poi** scrivere il discriminante — l'ordine
   conta: con `'23505'` e l'INSERT ancora incompleto il test sarebbe diventato
   rosso, e qualcuno avrebbe «aggiustato» il discriminante invece del test.

Costo: una copia temporanea e una corsa, zero modifiche al prodotto.
⭐ Resa: sei occorrenze in meno su 123, **un falso-verde trovato**, e una lista
di lavoro che si ripete su ogni file — i 123 sono elencabili in un comando, e
**21** di loro stanno in file che in CI girano davvero, **102** in file che lì
muoiono nella fixture (§3 D7).

### ✅ D12 — La quantità di documentazione — chiusa (era il gap di febbraio)

1.410 pagine **manuali** contro 1.500 autogenerate: il gap di febbraio («509
pagine, tre schemi scoperti») non c'è più — `magazzino` 32 pagine, `acquisti` 11,
viste coperte. Restano i due residui di **forma** (§3 D12): le pagine-specchio
dello `storico` che gonfiano il conteggio, e le pagine presenti ma sottili dei due
domini non ancora scritti (D8).

### ✅ D13 — Il `RETURNING` del billing account sotto RLS — chiuso il 2026-09-13

Con due emittenti in esercizio, l'operatore del secondo **non apriva clienti**:
il `RETURNING` chiedeva di vedere la riga *prima* che il trigger `AFTER` scrivesse
il legame, e il resolver ricadeva sul default — un'altra azienda. Ora *un BA non
ancora collegato appartiene a chi lo sta creando*: riserva a **tre livelli**
(`20260913-01/02/03`), la seconda copia della regola
(`fn_get_emittente_fiscale_pk`) che **delega**, e un pgTAP che costruisce
l'operatore del secondo emittente e prova l'`INSERT … RETURNING` **come
`zeroerp_app`**. Lato BE le tre copie inline delegano a
`fn_check_ba_visible_for_emittenti`, con un presidio a registro zero sulla forma.
⚠️ Prezzo dichiarato: un BA che *resta* senza legame è, in sessione, di chiunque
lo guardi — dato anomalo che il modello ammette.
Brief `brief-db-ba-riserva-emittente-operatore-d13.md`.

### ✅ D14 — La partita di merce si legge per documento — chiusa il 2026-09-22

Era: `script.fn_available_actions_ddt(id)` — la funzione che alimenta il drawer di
**un** DDT a ogni apertura — ricalcolava le partite di **tutti** i DDT, e sotto
RLS ogni riga scandita pagava la propria policy (~3.500 valutazioni per una
lettura). ⭐ Il difetto era **strutturale, non del planner**: la partita di una
riga dipende dalle spedizioni precedenti della stessa riga d'ordine, quindi
filtrare la CTE per documento avrebbe dato un numero **sbagliato**. La cura non
era un indice: era dare alla partita un **seme**, dopo aver mostrato sul modello
che la dipendenza è *bounded* (le due finestre sono partizionate per
`ordine_riga_id` e `ddt_riga_origine`: la chiusura di un documento è a due salti).

Otto giri fra il 17 e il 22 settembre, **sette applicati** e l'ottavo provato e
**ritirato lo stesso giorno**. Brief
`work-done/brief-db-partita-merce-per-documento.md`; changeSet `20260917-01`,
`20260921-20 → -34`, `20260921-50 → -55`, `20260922-01 → -16`; committato in
`c60f39eaa`, `559dbf351`, `acaaab569`, `e05e3b1e5`, `b40d9de24`, `660bbac59` e
`8d7f14829` (PR #1634, #1635, #1639, #1640, #1646).

**Che cosa è cambiato nel sistema** — le forme, non i millisecondi:

* `vendite.fn_partite_merce` (`BEGIN ATOMIC`) **semina** la partita con il
  documento o con l'ordine e ne calcola la chiusura; le viste diventano sue
  **proiezioni per nome** (un `SELECT *` perdeva `numeric(18,6)` e faceva uscire
  la vista dal presidio `security_invoker`);
* la stessa forma per `fn_situazione_merce_ordine`, `fn_resi_da_accreditare` e i
  due verbi degli accrediti: un seme, non un filtro su una popolazione intera;
* l'**eleggibilità ha una sola implementazione**: `fn_ddt_push_diagnosi` è la
  fonte, il lister ne deriva (`WHERE motivo IS NULL`) e la capability la legge
  **una** volta — prima erano due letture e due regole che potevano dissentire;
* ciò che è un insieme si legge **per chiave**: `vw_af_merce_per_riga` in una CTE
  `af AS MATERIALIZED` invece di quattro volte, il classificatore di segmento in
  forma a **range leakproof** (`~>=~`/`~<~`) con l'indice `varchar_pattern_ops`,
  i billing account seminati;
* `vw_contatore_merce` **ritirata** (censimento dal catalogo: nessun lettore), e
  nasce un BB generico — `trgfn_doc_righe_lock_fuori_bozza`, «le righe di un
  documento si toccano solo in bozza» — su `ddt_righe`, `ordini_righe` (solo
  DELETE) e `contratti_righe`, con le **due copie a DB ritirate** nello stesso
  giro.

| Lettura, come `zeroerp_app` | 17-09 | 22-09 sera |
| --------------------------- | ----- | ---------- |
| capability di un DDT (il drawer) | 290 ms | **39 ms** |
| partita di un DDT                | 120 ms | **27 ms**  |
| lista push senza documento (cockpit) | 214 ms | 73–94 ms |
| diagnosi di tutti i documenti    | 348 ms | 63–104 ms |

⚠️ **Le forcelle non sono un refuso**: sono lo stesso corpo misurato a un'ora di
distanza, ed è il motivo per cui è nata **D15**.

⭐ **Tre lezioni che valgono oltre il cantiere:**

1. *Ciò che è un insieme si legge una volta, e si semina con le chiavi in gioco.*
   ⛔ Col corollario che il giro 7 ha pagato: «una volta sola» **non basta** —
   leggere l'insieme intero è una volta sola, e fa pagare tutta la storia a chi
   chiede **un** documento. Le due forme si somigliano e non sono la stessa cosa.
2. ⛔ **Il banco di prova prova le righe, non il piano.** Il corpo eseguito come
   `SELECT` non predice il piano **dentro** la funzione: qui ha nascosto un
   difetto vero, ne ha **inventato** uno (la «terza occorrenza» che non esisteva)
   e ha promesso un guadagno che era una perdita. ⇒ L'equivalenza si prova sul
   banco, e il confronto **per seme** ha trovato un errore che il confronto
   globale dichiarava equivalente; il **piano** si misura dopo l'apply, sulla
   funzione, come applicazione.
3. ⚠️ **Un presidio verde a vuoto non è un presidio**: il ramo `DDT_SENZA_BA` non
   era esercitato da nessuna riga viva: caso costruito, e rosso per mutazione.

⛔ **Ciò che resta non è lavoro sospeso**, e sta in §6: due decisioni **non prese**
(la catena del `sospetto` — un avviso per una persona che nessuna macchina legge,
17,6 ms su 46, raccomandato lasciar stare; e **D8(b)**, che nessuna misura
reclama), i tre `LIKE` di `fn_accredita_riga_reso`, i preventivi come quarto
adottante del BB delle righe in bozza, e tre voci BE.


---

*Valutazione 2026-09-08 — perimetro DB. Le misure sono letture di struttura sul
database di sviluppo `zeroerp` (PostgreSQL 18.6) e sul repo al commit `89d36ad1b`,
branch `dev/db-tid`. La valutazione di febbraio 2026 resta in §1 come fatto
datato. Sfoltito il 2026-09-12: le voci chiuse sono ridotte a data e rimando; la
versione integrale è nella storia git del file. **Riordinato il 2026-09-20**: §3
contiene solo i difetti aperti, e le attività svolte stanno in §7 — con lo stesso
numero in entrambe le sezioni quando una voce ha due facce. **Riordinato il
2026-09-22**: D14 è chiusa e passata per intero in §7, e al suo posto in §3 è
entrata D15 — le statistiche assenti, che la sua chiusura ha scoperto.*
