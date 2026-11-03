# Migliorie generali da test valutazione

## ⏭️ Chi riparte — aggiornato al 2026-11-03

**Riparte: il team DB** su D7 (i 23 rossi del registro della CI), e **Tid** con le decisioni che
tengono ferme le altre voci aperte di §3.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | D18: le cinque decisioni della catena delle istanze | `brief-db-catena-istanze-pdp.md` §6 | — |
| 2 | Tid | D31: il canone è chiuso (brief archiviato il 2026-11-01, collaudo a video fra i residui di PROJECT_CONTEXT); orario e consumo aspettano le loro sorgenti | `work-done/brief-db-contratto-righe-periodiche-in-commessa.md` §7.14 | le sorgenti |
| 3 | team DB | D17 Q-2: le GUC di bypass legate al proprietario — via di Tid il 2026-11-03; serve un brief suo (decisioni aperte, ~45 pgTAP) | §3 D17 | — |
| 4 | Tid | D7: i test legati a dati di macchina; il ramo «ultimo SUPER_ADMIN» | §3 D7 | — |
| 5 | team BE | D24: togliere `("E_DOC_EMITTENTE_BA_INCOERENTE", 1)` da `_ESENZIONI` (lato DB applicato e verde il 2026-11-03) | §3 D24 | — |
| 5-bis | Tid | D31: le sorgenti di orario e consumo (le domande le prepara il team DB) | §3 D31 | — |
| 6 | Tid | `pgtap-baseline-ci-rientrati.sh` il giorno di ogni push su `Tito-dev` che tocca `db/` (il registro 358 → 23 è committato dal 01-11; ultima corsa utile `41359455206`, nessun rientrato) | §3 D7 | ogni push |
| 7 | team DB | D7: i 23 rossi della CI (17 `ASSERZIONE`, 6 `ERRORE_FIXTURE`), uno per uno | §3 D7 | — |

Decisioni aperte di Tid: righe 1, 2, 4 e 5-bis. Lavoro da committare: il giro del 2026-11-03 (D24,
D6-bis, D16, `test-indirizzi-fallback` e questo riallineamento) — applicato e verde su dbdev.

> **Ultima revisione: 2026-11-03.** Valutazione dello strato DB, aperta il 2026-09-08. Qui sta
> **solo ciò che è vivo**: chi riparte, i difetti aperti (§3), cosa non è un difetto (§4), la
> scorecard (§5) e la checklist delle voci aperte (§6). La valutazione di febbraio (§1), ciò che è
> nato in sette mesi (§2), la valutazione del design del 04-10 (§2-bis), le voci chiuse (§7) e i
> riallineamenti della testata sono nell'**archivio**,
> [migliorie-generali-da-test-valutazione-storia.md](../work-done/migliorie-generali-da-test-valutazione-storia.md), con la stessa numerazione: un
> rimando «§D13» o «§7 D7» da un changeSet o da un brief si legge lì.
>
> **Numeri del 2026-11-03** (ultima corsa CI utile `41359455206` su `Tito-dev`, `855bab60b`, del
> 01-11; la certificazione è della corsa `41326840441`, `84de5e28d`): suite pgTAP a **939** file,
> **23 rossi in CI** (verde al 97,5%; 227 su 714 il 26-09); `baseline-rossi-ci.tsv` **certificato** a
> **23** (6 `ERRORE_FIXTURE`, 17 `ASSERZIONE`; era 358: 335 rientrati), nessun rientrato dopo;
> `baseline-rossi-scratch.tsv` a **21** (4 `ERRORE_FIXTURE`, 17 `ASSERZIONE`; 22 al 01-11); `baseline-rossi.tsv` a
> **3** (dal 01-11); `SOGLIA_THROWS_SENZA_DISCRIMINANTE` a **110**; utente `'1'` a zero; smoke non
> verdi a **0** (dal 28-10); 119 file con `skip()`, 147 con `pgtap-runner: owner`. Gli indicatori vivono in
> [qualita-db-indicatori.md](../qualita-db-indicatori.md).
>
> ⛔ **Di una vista di presidio si conta il registro, mai la misura** (correzione del 2026-10-27,
> nell'archivio): `vw_codici_errore_da_dichiarare` è la misura del terzo lato, il debito è
> `dbops.codici_errore_senza_policy`, a zero dal 2026-08-07.

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

## 3. I difetti **aperti**, in ordine di conseguenza

> Solo il lavoro che resta. Le voci chiuse — per intero D1-D5, D10, D12-D15, D19-D23, D25-D30,
> D32-D36, D26-2; in parte D6, D7, D11, D17 — sono nell'archivio, §7, con data e brief. Quando una
> voce ha ancora una parte aperta, il numero compare in tutti e due i posti.

### 🟠 D17 — Resta Q-2: le GUC di bypass che chiunque può accendere

✅ **Il resto di D17 è chiuso il 2026-10-04** (§7): Q-4, Q-1, Q-3, `UPDATE OF`, v1.
Resta la parte che Tid ha **rimandato** lo stesso giorno: dieci blocchi del DB si
spengono con una GUC che anche l'applicazione può accendere (il lock di colonna,
cioè anche `codice_interno`; il divieto di DELETE su clienti ed emittenti; otto
guard del lotto e delle fatture…). Il backend non ne accende nessuna, ma un blocco
che l'applicazione può spegnere da sola protegge solo finché l'applicazione non
sbaglia. Proposta nel brief
[brief-db-esclusioni-implicite.md](../work-done/brief-db-esclusioni-implicite.md) §4: un
building block che lega il bypass al **proprietario delle tabelle** (la forma di
`zeroerp.ddt_cambio_stato`), i verbi del lotto DEFINER (approvato), circa 45 pgTAP
da riscrivere perché usano quelle GUC come scorciatoia di fixture.

✅ **R-1 del brief chiusa dal BE il 2026-10-04**: i due codici nuovi di Q-4 in
`error_policies_generated.py`, con i ripieghi (`63deeb194`).

⏸️ **Al 2026-10-23: invariata.** Nessun brief aperto, la decisione resta rimandata. Il bisogno non
è cambiato, e nel frattempo è nato il modello dei ruoli di sistema (un proprietario solo,
`zeroerp_owner`, dal 15-10): il «proprietario delle tabelle» su cui legare il bypass oggi è uno
solo, e la forma proposta si scrive più semplice di quanto sarebbe stata il 04-10.

### 🔴 D18 — La catena delle istanze su un PDP si rompe quando un anello esce o entra

Trovata il 2026-10-05 verificando il censimento `UPDATE OF` di D17. Su un PDP i
clienti si succedono, e ogni istanza punta a quella del cliente precedente
(`istanze_utilities.parent_istanza_id`, da cui il subentro clona il catasto). Il
calcolo ha tre difetti, tutti sul modello:

* **annullare un cliente non lo toglie dalla catena**: il trigger è `UPDATE OF
  pdp_id, data_attivazione`, l'annullamento cambia lo stato, e `data_attivazione`
  la azzera un altro trigger `BEFORE`. I due rami scritti per l'annullamento non
  si raggiungono mai da un UPDATE;
* **si ricalcola un anello, non la catena**: annullare, inserire in mezzo,
  spostare una data, cambiare PDP o cancellare lascia sbagliato il **successore**;
* **il calcolo legge sotto RLS**: il subentro attraversa le aziende, e il
  predecessore di un'altra azienda per chi lavora non esiste.

Proposta nel brief
[brief-db-catena-istanze-pdp.md](brief-db-catena-istanze-pdp.md): un ricalcolo
DEFINER della catena intera del PDP, da un trigger `AFTER` senza `OF`. Cinque
decisioni aperte per Tid.

⏸️ **Al 2026-10-23: ferma dal 05-10**, ancora proposta da analizzare. ⚠️ Nel frattempo
`trgfn_clienti_set_parent_istanza` è stata riscritta (`20261014-17`, la catena delle istanze
fittizie di D33): i tre difetti valgono anche per quel ramo, e la riscrittura parte dal corpo
della doc auto-generata (lo dice il brief). 🔴 resta: è un difetto vero, che non dà errore.

### 🟠 D6 — Resta solo D6-bis: i pin e il registro degli owner sono chiusi (§7)

✅ I pin del `search_path` sulle tre DEFINER di `postgres` dal 12-09, e il
registro degli owner con la sync **riservati al migratore** dal 26-09: §7 D6.
Qui resta D6-bis.

#### D6-bis — una forma di `search_path` per le 38 `SECURITY DEFINER`

Le `SECURITY DEFINER` proprie sono **38**, e il `search_path` ha sei forme
(2026-09-08, con i tre pin del 12-09):

| Forma                                                  | Quante |
| ------------------------------------------------------ | ------ |
| `pg_catalog, public`                                   | 16     |
| `pg_catalog, pg_temp`                                  | 8      |
| `public, pg_temp`                                      | 5      |
| `pg_catalog, pratiche, script, config, dbops, pg_temp` | 4      |
| `pg_catalog, public, pg_temp` *(i pin del 12-09)*      | 3      |
| `pg_catalog, anagrafiche, config, script`              | 2      |

In **18 su 38** `pg_temp` non è elencato — e quando non è elencato PostgreSQL lo
cerca **per primo** per le relazioni. In altre 5 `public` viene **prima** di
`pg_catalog`, che è l'ordine opposto a quello prudente.

✅ **Al 2026-10-23 i due rubinetti sono scesi**, per sanatorie fatte di passaggio da altri
cantieri: senza `pg_temp` **16** (era 18: `script.fn_get_stato_testata_documento` il 05-10,
`anagrafiche.fn_guard_albero_ba_gestore_globale` il 10-10), `public` prima di `pg_catalog` **4**
(era 5: `maintenance.fn_job_run_log_failure`, `20261015-03` di `brief-db-ruoli-di-sistema`). Le soglie stanno in
`db/pgtap/dbops/test-security-definer-search-path-v1.sql` (test 4 e 5) e possono solo calare. È
il verso giusto — si sana quando un cantiere ci passa — ma senza un giro suo la voce resta aperta.

✅ **Al 2026-11-03: il giro suo, applicato e verde.** Le DEFINER del progetto sono ora **139**
(dbdev), tutte con il pin; quelle da sanare erano **20** — 16 senza `pg_temp` (14 `pg_catalog,
public`, 2 `pg_catalog, anagrafiche, config, script`) e 4 con `public, pg_temp`.

* `20261103-04` (`20_code`, 19 funzioni di `zeroerp_owner`) e `20261103-05`
  (`script.fn_log_error_only`, che è di `postgres`: la proprietà si prende **in prestito** via
  `dbops.fn_sync_functions_owner` e si restituisce, la forma di `20260807-19`; gira col migrate
  normale): `pg_temp` **in coda**,
  `pg_catalog` **in testa** dove mancava, gli altri schemi invariati. `ALTER FUNCTION schema.nome
  SET search_path` senza firma (nomi unici): il corpo non si tocca e la firma non si deduce.
* ⛔ **`public` non si è tolto**, anche se il censimento statico dei 19 corpi non trova nessuna
  chiamata a qualcosa che sta solo in `public`: il path di una DEFINER lo ereditano le INVOKER che
  chiama e i trigger che le sue scritture fanno scattare, e lì la cecità degrada in silenzio
  (lezione del 12-09). Toglierlo resta possibile funzione per funzione, con la catena dei chiamati.
* I rubinetti 4 e 5 di `test-security-definer-search-path-v1` diventano **divieti** che elencano i
  colpevoli.

Prova (dbdev, SQL estratto del `-04` + presidio, transazione annullata, come `zeroerp_owner`): test
1-4 verdi, test 5 rosso **solo** su `script.fn_log_error_only` — è il `-05`, che serve un superuser e
qui non è provato. ✅ Riscritto il `-05` (la prima stesura, in `context: provision`, è stata
rifiutata dal migrate di Tid: «bisogna essere proprietari») e riprovato come `zeroerp_owner` in
transazione annullata: test 1-5 verdi, proprietà tornata a `postgres` a fine changeSet.
✅ **Chiusa il 2026-11-03**: `-04` e `-05` applicati su dbdev, `test-security-definer-search-path-v1`
verde (corsa di Tid). I due rubinetti sono divieti. Resta, come possibilità e non come debito,
togliere `public` funzione per funzione guardando la catena dei chiamati.

⛔ **Una forma canonica uguale per tutte non esiste** (lezione del 12-09, §7 D6).
`pg_catalog, pg_temp` **accieca** chi chiama un'estensione non qualificata —
`dblink`, `unaccent`, `postgis`, `plpgsql_check` stanno tutte in `public` — e
dentro un `EXCEPTION WHEN OTHERS` la cecità non fa un rosso: degrada in
silenzio. Quindi si decide **per funzione**, guardando i suoi chiamati: o si
qualifica la chiamata, o `public` resta nell'elenco. ⭐ La forma giusta quando
`public` serve davvero è quella di `dbops.fn_check_funzioni_riferimenti_morti`:
pinna `pg_catalog, public, pg_temp` **e** qualifica la chiamata (changeSet
`20260912-37`). ⚠️ Vale anche per `fn_get_or_create_session_tx_id`: se un giorno
il suo pin si stringesse, **prima** `public.dblink(...)` nel corpo, poi il pin.

---

### 🟠 D7 — La copertura dei test non è bassa: è concentrata

600 file, ~6.183 asserzioni (2026-09-08; 714 file al 26-09, e `magazzino` da 1
a 17 coi suoi lotti — D8). Il numero non dice niente; la distribuzione sì.

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

*(2026-10-23, 887 file: `vendite` 352, `anagrafiche` 95, `script` 94, `dbops` 79, `config` 61,
`rls` 43, `pratiche` 43, `magazzino` 25, `pagamenti` 23, `catalogo` 22, `documenti` 18, `ui` 17,
`maintenance` 13, `storico` 1, `shop` 1, **`acquisti` 0**. La forma della distribuzione non è
cambiata: `vendite` da sola è il 40%.)*

⚠️ E la copertura dichiarata è più alta di quella reale per due motivi già
scritti nella guida sui presidi: **110 file** contengono uno `skip()`
condizionato (2026-09-08: su un DB ricostruito da zero si saltano, e un test
saltato conta verde), e il debito `throws_ok` senza discriminante è a **117**
(2026-09-26; 131 quando questa valutazione è stata scritta) — un
`throws_ok(sql, NULL, NULL)` accetta *qualunque* errore, compreso quello
sbagliato. Due volte, sanandone uno, è venuto fuori un test **verde per l'errore
sbagliato** (§7 D11, §7 D7).

### 🔴 Il numero che conta davvero: la suite fuori dalla macchina di sviluppo

Su un database **ricostruito da zero** — quello che serve il giorno in cui si
prepara un'installazione nuova — la prima misura della CI (2026-09-09) ha dato
**407 rossi su 601**. La misura più recente della CI, **227 rossi su 714**
(2026-09-26; lo scratch `zeroerp_ci` dava 229 su 687 il 24-09), dice che
fuori dalla macchina di sviluppo la suite era **verde su due terzi dei file**.
⚠️ È ancora l'ultima misura CI registrata: al 14-10 la suite è a **830** file (corsa di Tid su dev), e il
corsa di Tid sullo scratch `zeroerp_ci` del 14-10 dà **164** rossi su 830, tutti
noti nel suo registro (`baseline-rossi-scratch.tsv`: 133 `ERRORE_FIXTURE`, 30
`ASSERZIONE`, 1 `SORGENTE_POLIMORFA`). Sullo scratch, ricostruito da zero, la suite è
quindi verde su circa **l'80%** dei file.

✅ **Al 2026-10-23** lo scratch non è più `zeroerp_ci` (ritirato il 15-10) ma `zeroerp_ruoli`,
costruito col modello dei ruoli di sistema; il suo registro è a **147** su 887 (120
`ERRORE_FIXTURE`, 26 `ASSERZIONE`, 1 `SORGENTE_POLIMORFA`; ultimo aggiornamento il 20-10):
verde su circa l'**83%**. Anche la CI di GitHub gira ora col modello (owner `zeroerp_owner`), ma
**dopo il 26-09 il repo non registra nessuna sua misura**: il numero che vale è ancora il vecchio. ⛔ *Lo scratch non è
la CI*: il numero che vale resta quello del registro della CI. Il calo è
lavoro vero, non igiene: la fixture che **costruisce** il mondo invece di
cercarlo (§7 D7).

✅ **Al 2026-10-27** (lotti 3 e 4 di D7, corsa di Tid): il registro dello scratch è a **24** su 916
(4 `ERRORE_FIXTURE`, 20 `ASSERZIONE`), cioè verde al **97%**. `pratiche` e `vendite` non hanno più
rossi di fixture: quelli che restano sono asserzioni, più quattro fixture in `anagrafiche` e
`script`.

✅ **Al 2026-11-01 lo dice la CI, e il registro lo sa.** La corsa `41326840441` su `Tito-dev`
(`84de5e28d`, push del merge della PR #5, database ricostruito da zero col modello dei ruoli) dà
**23 rossi su 936**, tutti già noti: verde al **97,5%**, contro 227 su 714 il 26-09 e 407 su 601
il 09-09. Lo stesso giorno `pgtap-baseline-ci-rientrati.sh` ha tolto dal registro i **335
rientrati**: `baseline-rossi-ci.tsv` passa da 358 a **23** righe (6 `ERRORE_FIXTURE`, 17
`ASSERZIONE`). Il verde guadagnato dai lotti 1-4 ora è **protetto**: una regressione su uno di
quei file ferma il merge. La misura della CI e quella dello scratch (22 il 01-11) coincidono quasi
del tutto: la fixture che costruisce funziona anche fuori dalla macchina di sviluppo.

⏸️ **Al 2026-11-03**: l'ultima corsa utile, `41359455206` (`855bab60b`, 01-11 sera), dà **23 rossi su
939**, gli stessi; `pgtap-baseline-ci-rientrati.sh --dry-run` non trova rientrati. ⚠️
`test-indirizzi-fallback` è uscito dalla baseline di sviluppo il 01-11 (`223269431b`) ma restava
rosso in CI e sullo scratch: pescava il gestore (`MIN(id)` su `anagrafiche.gestori`, vuota da zero) e
ogni scrittura lavorava su zero righe. In CI era un rosso di **asserzione** — nessun `ERROR` della
sessione nel log del container — e l'etichetta `ERRORE_FIXTURE` del registro era quella di una corsa
precedente: ⛔ lo script ristampa la causa solo per i rossi **nuovi**, quella dei noti non si rinfresca.
Corretto il 03-11 con `fn_pgtap_crea_gestore` (e l'indirizzo da `fn_pgtap_crea_indirizzo_dettaglio`);
verde alla corsa di Tid del 03-11 e tolto dal registro dello scratch (22 → 21); esce da quello della
CI con lo script dei rientrati, dopo la push.

⛔ **La corsa precedente non era una misura** (corsa `41325095742`, stesso giorno): il B-7 rosso
aveva saltato «Django migrate», la suite era partita lo stesso su un database senza schema
`django`, e ha dato **909 rossi su 936**, tutti `relation "django.auth_user" does not exist`. La
condizione della suite guardava `ci_apply`, che viene **prima** del secondo migratore. Corretto in
`ci-validate.yaml`: la suite parte su `steps.fase_post`, e il migrate e la fase post hanno il loro
`if` su `ci_apply`, così un cancello in mezzo non zittisce la suite. ⚠️ Il log di una corsa scade
in pochi giorni: i rientrati si tolgono **il giorno stesso** della push che tocca `db/`.

⚠️ E il difetto vero non è la percentuale: è che quei file **passano sul DB di
sviluppo**. Cioè la suite verifica in larga parte *lo stato di una macchina*,
non che le migrazioni sappiano ricostruirla — e la seconda è la proprietà che
serve al secondo cliente. Un rosso `ERRORE_FIXTURE` non esegue **nessuna**
asserzione: sono aree che *sembrano* coperte.

#### Che cosa resta

La ricetta è stabilita e i builder ci sono (§7 D7: la riga di contesto che
costruisce se il DB è vuoto, il BB di composizione
`dbops.fn_pgtap_crea_mondo_cliente()`, i builder di fattura, filiale, gestore,
operatore umano, PDP e listino, e dal 2026-10-07 quelli di **ordine, preventivo,
commessa e attività di commessa**). Resta applicarla, e ciò che il giro 2 ha
lasciato
([brief-db-fixture-che-costruiscono-giro-2.md](../work-done/brief-db-fixture-che-costruiscono-giro-2.md)
§5, §7, §9, §11):

* ⏳ **i 23 rossi della CI** (registro certificato il 2026-11-01), uno per uno: 17 `ASSERZIONE`
  (fra cui i file su identità digitali e `auth_user`, il caso dei «due mondi» di `django` in CI, e
  la famiglia 5 del lotto 4 in `vendite`) e 6 `ERRORE_FIXTURE` (`test-catasto-unita-immobiliare`,
  `test-indirizzi-fallback`, `test-processi-jobname-wrapper`, `test-search-soggetti-universale`,
  `test-vw-giornale-entita`, `test-snapshot-indirizzi-fattura-v1`). Sostituiscono i residui dei
  lotti 1 e 2, che si contavano sul registro vecchio;
* ✅ **lotto 3** — `pratiche`: chiuso il 2026-10-27 (corsa di Tid). Dettaglio nell'archivio, §7 D7.
* 🟡 **lotto 4** — `vendite`: famiglie 1-4 (commesse e attività, fatture-lotti-registri, preventivi-ordini-
  valuta, listini e prezzi; 77 file) chiuse il 2026-10-27, dettaglio e verdi falsi trovati nell'archivio,
  §7 D7. ⏳ Resta la **famiglia 5**: i rossi `ASSERZIONE` di `vendite` (8 nel registro della CI al
  01-11), uno per uno. Con loro gli altri rossi della CI fuori da `vendite` (`anagrafiche`, `script`,
  `config`, `dbops`, `ui`): errori di sintassi in SQL dinamico, test stantii sullo schema, dati di
  macchina (decisione di Tid sotto), pesche. ⚠️ Lo scratch da solo non prova un file che pesca ancora:
  ogni famiglia si chiude con la corsa di Tid su dev.
  Da guardare: in `vw-af-merce-per-riga` le asserzioni filtrano per id di riga sintetici (9000xx) senza il
  documento del test; il test 3 di `trgfn-preventivi-default-emittente` non distingue «non sovrascrive»
  (serve un secondo emittente nel perimetro dell'operatore);
* ⏳ **le copie a mano dei documenti di vendita** (2026-10-07): un ordine scritto
  a mano in 54 pgTAP, un preventivo in 40, una commessa in 36, un'attività di
  commessa in 32. Al 2026-10-27, contando i soli `INSERT INTO vendite.<tabella> (` letterali
  fuori dai commenti (metodo diverso da quello del 07-10, quindi non confrontabile), i file sono
  18 per l'ordine, 46 per il preventivo, 16 per la commessa e 21 per l'attività. I builder ci sono (`dbops.fn_pgtap_crea_ordine`, `_preventivo`,
  `_commessa`, `_commessa_attivita`): si migrano con il lotto 4, per famiglia
  ([brief-db-fixture-rls-documenti-costruiti.md](../work-done/brief-db-fixture-rls-documenti-costruiti.md)
  §6);
* ✅ i file che fissano `SET LOCAL app.current_user_id = '1'`: **zero** al 2026-10-27 (4 al 23-10,
  7 al 13-10, 28 al 22-09: l'utente 1 non esiste in CI). Gli ultimi quattro (due della porta
  oneri, `test-vw-af-merce-per-riga-v1`, `test-numera-nota-credito-riferimento-v1`) sono usciti con
  la famiglia 2 del lotto 4: l'utente di sessione è l'operatore del contesto;
* ⏳ la **baseline di sviluppo** (`baseline-rossi.tsv`): **3** file al 01-11 (4 al 27-10, 6 al
  23-10, 7 al 13-10, 12 al 26-09), di cui **2** muoiono nella fixture, tutti e due in `anagrafiche`;
* ⏳ i file con `pgtap-runner: owner` (**147** al 03-11, 146 al 01-11, 145 al 23-10, 130 al 13-10, 109 al 22-09): crescono coi
  file nuovi, e quanti di quei motivi siano ancora veri dopo la rev `20260912-38` non è misurato;
* ⏳ i file con uno `skip()` condizionato: **119** al 03-11, come al 27-10 (122 al 23-10, 110 all'08-09);
* 🔵 **decisione (Tid)**: i file legati a dati di **questa** macchina (gestore,
  CF, PIVA, PDP GAS) — si riscrivono o si dichiarano test di macchina;
* 🔵 **decisione (Tid)**: il ramo «ultimo SUPER_ADMIN» sull'identità è
  raggiungibile o è codice morto? Oggi a rifiutare è sempre il guard generico
  delle figlie, che scatta prima (brief giro 2, §7 punto 7).

#### 🔵 Due cancelli da disegnare (Tid)

1. **Il verso del registro** (brief giro 2, §6): un pgTAP che pesca in
   `anagrafiche.*` o `vendite.*` con `LIMIT 1` senza passare da un builder è
   rosso, con una soglia che può solo calare, come quella dei `throws_ok`.
   Deciso il 22-09: **dopo** il primo lotto, che è chiuso.
2. **La finestra differita dopo la riga di contesto.** La regola è scritta
   (template §3, guida pgTAP, `COMMENT` di `fn_pgtap_set_contesto_operatore`):
   *dopo la riga di contesto non si conta sulla finestra differita di default;
   chi la vuole la riapre con `SET CONSTRAINTS ALL DEFERRED`*. Un cancello in
   `guardrail_pgtap_preambolo.py` la renderebbe leggibile da uno script, ma il
   censimento del 21-09 dà 9 candidati e 7 falsi positivi, e il criterio
   «`IMMEDIATE` dopo una scrittura» è cieco sui file che **non hanno** un
   `IMMEDIATE` (i `pgtap-differiti: escluso`: nove caduti il 23-09).

⛔ Per tutti e due vale la lezione del 21-09: un criterio testuale conta le
scritture che **vede**, e una scrittura che passa per una funzione
(`fn_crea_*`, `fn_pgtap_crea_*`) è invisibile. Il cancello o guarda anche
quelle, o **dichiara di non vederle** — nel messaggio, non in un commento.

> ⭐ **Incrocio con D11, e decide l'ordine dei due lavori** (2026-09-20). Dei
> `throws_ok` senza discriminante, **102** stavano in file a registro qui, e
> **94** di quei 102 in file `ERRORE_FIXTURE` — che su un database ricostruito
> non eseguono nessuna asserzione. Discriminarli lì è severità che si vede solo
> su dbdev: prima la fixture, poi il discriminante.

---

### 🟠 D8 — `acquisti` e `magazzino`: modellati, non scritti

✅ **Deciso l'11-09-2026 (Tid): sono il PROSSIMO CANTIERE**, non congelati —
scritto in `.codex/PROJECT_CONTEXT.md`, con la conseguenza che questa voce
cercava: *ogni decisione presa su `vendite` è presa anche per `acquisti`*, e
un'asimmetria fra i due si chiude subito, non in una «fase due». ⚠️ `storico`
**non** è coperto dalla decisione come dominio (sul lato RLS l'ha chiuso D3).

✅ **Al 2026-09-26 i due schemi non sono più allo stesso punto.** `magazzino` ha
il comportamento dei lotti 1 e 2 — il terreno vuoto
(`work-done/brief-db-magazzino-lotto-1-terreno-vuoto.md`, chiuso il 17-09), il
motore (`work-done/brief-db-magazzino-lotto-2-motore.md`, lato DB chiuso il
18-09) e i verbi con permesso
(`work-done/brief-db-magazzino-verbi-con-permesso.md`, 25-09) — e **17** file
pgTAP; resta aperto come cantiere (collaudo a video). ⛔ `acquisti` è ancora
dove lo descrive la tabella: **zero** test, comportamento da scrivere. La
tabella qui sotto è la fotografia dell'8-09 e per `acquisti` resta vera.

✅ **Al 2026-10-23** `magazzino` ha anche il lotto 3 (scarico da DDT) e il 3-bis (carico da reso),
chiusi il 14-10 (`work-done/brief-db-magazzino-lotto-3-*.md`), e **25** file pgTAP; restano aperti
`brief-db-magazzino-tutte-le-scritture-dal-verbo.md` e i collaudi a video. ⛔ `acquisti` non si è
mosso: zero test, nessun changeSet di comportamento (gli ultimi del 09-10 sono adeguamenti di
regole generali), e `analisi-simmetria-ordini-acquisto.md` è ferma al 14-09. Intanto `vendite`
ha preso altre decisioni — grammatica unica dei documenti, modelli di documento standard,
emissione dell'offerta — che **valgono anche qui** e qui non sono scritte: il debito di
`acquisti` cresce senza che nessuno lo tocchi, come la voce prevedeva.

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

⚠️ Che il comportamento arrivi dopo il modello è l'ordine scelto (§4), non il
difetto. Il difetto possibile è un altro, e sta sul modello: `acquisti`
specchia il ciclo vendite, quindi ogni decisione presa di là (numerazione, serie,
perimetro emittente, righe senza prezzo, lineage) **è una decisione presa anche
di qua, che qui non è ancora scritta**. Più cresce `vendite`, più cresce il debito
di `acquisti` senza che nessuno lo tocchi.

🔴 **Il primo caso, verificato il 2026-10-04 (Q-5 di §2-bis):** `acquisti.ordini`
e `acquisti.ddt` non hanno né emittente né registro; l'unicità
`(anno, serie, numero)` è **globale**, mentre il DDT di un fornitore porta il
numero **del fornitore** (unicità per fornitore, come vuole
`acquisti/manual/ddt.md`), e senza `NULLS NOT DISTINCT` non vincola le righe con
`serie` NULL; nessuna tabella dello schema ha la RLS. È la decisione di `vendite`
(multi-emittente, RLS per emittente) non riportata su `acquisti`: si chiude nel
modello, prima del comportamento. L'emittente si nomina
`emittente_soggetto_ruolo_id` (Q-6, linee-guida-sql §2).

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

⏸️ **Al 2026-10-23 (catalogo di dbdev)**: `catalogo.articoli` ha **50** trigger; le due funzioni
per-figlia ne montano **816** su 2.358; la fase nel nome (`_aNN_`/`_zNN_`) è su **1.603**, il
**68%**. Nessun lavoro sulla voce: il pattern cresce con le figlie, come diceva la diagnosi. I
trigger nuovi nascono con la fase, i vecchi senza restano senza.

---

### 🟡 D11 — I registri di debito non calano

Un registro di debito è una buona invenzione **a condizione che scenda**. Stato
al 2026-09-08, salvo dove è scritta un'altra data:

| Registro                                   | Oggi (2026-10-23; i registri pgTAP e gli smoke al 2026-11-03)                              |
| ------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `dbops.codici_errore_senza_policy`         | ✅ **0** dal 2026-08-07 — ⛔ *non* il conteggio di `vw_codici_errore_da_dichiarare` (702 al 23-10), che è la misura: vedi sotto |
| `db/pgtap/baseline-rossi-ci.tsv`           | ✅ **23** file su 939 (6 `ERRORE_FIXTURE`, 17 `ASSERZIONE`) al 03-11 (ultima corsa utile `41359455206`, nessun rientrato), certificati il 01-11 dalla corsa CI `41326840441` — era 358 (291 `ERRORE_FIXTURE` al 27-10), fermo dal 22-09; nato il 09-09 con 407 (D7) |
| `db/pgtap/baseline-rossi-scratch.tsv`      | **22** file (4 `ERRORE_FIXTURE`, 18 `ASSERZIONE`) al 01-11 — 24 su 916 al 27-10, 147 su 887 al 20-10 (D7, lotti 3 e 4) |
| `db/baseline-codici-errore-famiglie.tsv` (B-7) | **219** codici al 01-11, riallineata dopo i rossi del 01-11 (2 codici nati dopo il 13-10, 2 ristretti, 13 rientrati: 12 non più leggibili dalla misura, uno ritirato) — 212 al 13-10 |
| `SOGLIA_THROWS_SENZA_DISCRIMINANTE`        | **110** al 27-10, e il cancello vede anche `NULL::text` (115 al 13-10, 117 al 26-09, 129 all'08-09) |
| `dbops.vw_fk_con_indice_missing_policy`    | **57**, fermo dall'08-09                                                                   |
| `db/pgtap/baseline-rossi.tsv`              | **3** file (2 `ERRORE_FIXTURE`, 1 `ASSERZIONE`) al 01-11 — 4 al 27-10, 6 al 23-10, 7 al 13-10, 12 al 24-09, 16 al 12-09, erano 19 |
| `dbops.rls_perimetro_debito`               | **6** righe nel seed (7 al 20-09, era 10 → D2)                                             |
| `backend/scripts/tests/baseline-smoke.tsv` | ✅ **0** dal 28-10 (2 su 52 script al 23-10, 7 al 13-10; 2 su 16 al 12-09, prima che il perimetro comprendesse i bash) |
| Header di licenza mancanti                 | 2.042 file (misura 2026-08-26, non rifatta)                                                |
| `dbops.vw_indici_ridondanti_prefisso`      | 1                                                                                          |
| Codici vivi senza messaggio                | 6 (tutti `W_`, §2.3) — gli stessi sei                                                      |
| `dbops.vw_processi_che_bypassano`          | ✅ **0** dal 2026-10-15 (era 1, dichiarato con la data di ritiro: ritirato nei tempi)      |

⭐ L'ultima riga è l'unica fatta bene: **una** voce, con il motivo e il momento in
cui sparisce — ✅ ed è sparita quando diceva. ✅ Il 01-11 i rossi della CI sono scesi da 358 a 23:
il verso c'era (`pgtap-baseline-ci-rientrati.sh`), mancava la corsa che lo facesse girare. Le due
liste lunghe che restano (la soglia `throws_ok`, le FK senza indice) no, e la guida sui presidi dice
esattamente perché è un problema: *«il registro nasce piccolo. Se parte con
trenta righe, nessuno lo leggerà»*. `rls_perimetro_debito` è nato nella forma
giusta — ogni riga con la sua ragione — ed è calato di due terzi nel cantiere
che l'ha aperto.

⛔ **Corretto il 2026-10-27 — i codici non sono un registro che cresce.** Qui stava scritto che
508 → 545 → 702 era «un presidio senza un verso». Era la lettura sbagliata: 702 è il numero di
righe della **misura** `vw_codici_errore_da_dichiarare` (ogni codice che il DB può nominare), non
del debito. Il registro è `dbops.codici_errore_senza_policy`, **a zero dal 2026-08-07**, e il verso
ce l'ha: il cancello `test_error_codes_db_policy_guardrail` è rosso su un codice nuovo senza policy
(verso 1), su una voce del registro che l'ha ottenuta (verso 2) e su una che nessuno nomina più
(verso 3). È, con `vw_processi_che_bypassano`, il secondo registro portato a zero nei tempi.
⛔ **Per non ricadere: di una vista di presidio si conta il registro, mai la misura.** La natura
sta in `dbops.presidi` (questa vista è `CANCELLO`) e nel `COMMENT` della vista.

⚠️ Le due baseline pgTAP meritano una riga a parte: i file `ERRORE_FIXTURE`
(6 in CI e 2 in sviluppo al 01-11; 292 e 6 al 13-10) non eseguono **nessuna**
asserzione. La loro copertura vale zero, non «parziale» — e sono aree che
*sembrano* coperte.

---

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

⏸️ Al 2026-10-23: nessun avanzamento, il censimento non è partito.

✅ **Al 2026-11-03: il censimento, fatto per regola** (dbdev, catalogo; i pgTAP letti come testo).

* **Le regole che leggono «oggi».** «Oggi» è `script.fn_data_operativa()` (il giorno nel fuso
  dell'azienda), non `current_date`. Le funzioni che lo leggono e sollevano errori sono 51, in
  tre famiglie: **(A)** rifiuti che confrontano una data con oggi — la finestra di emissione
  (`vendite.fn_get_pavimento_emissione`, oggi meno N giorni, letta dalla numerazione e da
  `fn_imposta_data_documento_lotto`), preventivo accettabile/emettibile (`validita_al`), il
  passaggio a `CESSATO` di un contratto e la chiusura di una versione di listino (`valido_al`),
  il padre obsoleto (`obsoleto_dal`), l'ultimo super admin (`valido_dal`), la promo che si crea
  solo nel futuro (`valido_dal`), e le validità a intervallo (matrici degli indirizzi, BoM, UoM,
  esclusioni articolo, utility); **(B)** i lavori «scaduti» (`fn_cessa_contratti_scaduti`,
  `fn_chiudi_preventivi_scaduti`, `fn_chiudi_versioni_listino_scadute`,
  `fn_apply_chiusura_scadenze`); **(C)** default «data = oggi», che non rifiutano niente.
* **I pgTAP che le attraversano con una data scritta a mano.** 132 file portano date fra il
  2025 e il 2079 (le 2080+ sono il pattern immune). Incrociati istruzione per istruzione con le
  colonne delle regole A e B, e letti uno per uno i candidati, le bombe vere sono **due**:
  1. ✅ `vendite/test-data-documento-v1` (test 10, 11, 13): date future `2027-…` passate alla
     madre che guarda il pavimento — sarebbero diventate troppo vecchie a metà 2027. Portate a
     `fn_data_operativa() + 60/90/120/150` (distinte: il test 12 vuole un cambio), l'`anno` del
     numero derivato dalla data. ✅ Verde.
  2. ✅ `vendite/test-promo-articoli-v1`: il guard crea una promo solo con `valido_dal` dopo
     oggi, e il file creava promo nel 2030-2032 → rosso dal 2030-01-01. Deciso da Tid il
     2026-11-03: date relative (non anni 2080+, che rimandano soltanto). Tutte da UNA base, il
     primo del mese fra un anno; l'atteso del test 9 calcolato dalla stessa base. ✅ Verde.
  ⛔ **Guardrail statico: no** (2026-11-03). Un controllo che legge il testo non sa se una data
  arriva a una regola che guarda oggi: su 132 file con date ne avrebbe segnalati quasi tutti, e
  non avrebbe visto quelle che passano da un builder. Se servirà una prova completa, la forma è
  la macchina del tempo (la suite con `fn_data_operativa()` a una data futura), non una regex.
  ⭐ Non sono bombe, letti: i titoli IVA (la regola prende la data come PARAMETRO, D14), le
  versioni dei template (nessun lettore di oggi), i contratti in bozza con `valido_al` vicino (il
  guard guarda `valido_al` solo sul passaggio a `CESSATO`), le date passate dei file che numerano
  (≥ 62 giorni e verdi: non passano dalla finestra, e il tempo non le peggiora).
* ⚠️ **Limite dichiarato.** Il censimento legge il testo: una data che arriva alla regola
  attraverso un builder o una variabile non si vede, e «oggi» non si può spostare —
  `fn_data_operativa()` legge `now()` e non ha un'impostazione di prova. Una macchina del tempo
  (la suite con la funzione ridefinita a una data futura, in transazione) sarebbe la prova
  completa: è una proposta, non fatta.

### 🟡 D24 — Il presidio C2 non vede i building block trigger che ricevono il codice negli argomenti

Trovato il 2026-10-10 chiudendo il lato BE di D22 (§9.2 di
[brief-db-guard-emittente-ba-unico](../work-done/brief-db-guard-emittente-ba-unico.md)). Il presidio
C2 (`backend/apps/core/tests/test_ui_action_e_canale_campi.py`, «una promessa
`highlight_form_fields` ha un sito che manda il campo») legge i siti PL/pgSQL da
`dbops.vw_punti_canale_campo`, che trova il codice nel **corpo** della funzione. Un building block
trigger lo riceve invece da `TG_ARGV` (`pg_trigger.tgargs`), e il `'campo'` lo mette nel contesto
per conto suo: per la vista quel sito non esiste.

* **Il caso che l'ha mostrato:** `E_DOC_EMITTENTE_BA_INCOERENTE` (BB
  `script.trgfn_doc_guard_emittente_ba`, sei tabelle) promette il campo, e il campo arriva — provato
  con una chiamata vera il 2026-10-10 su ordine, preventivo e contratto, `fields =
  ('emittente_fiscale_id',)` — ma il verso 1 era rosso con «nessun sito». Lato BE è una riga in
  `_ESENZIONI[("E_DOC_EMITTENTE_BA_INCOERENTE", 1)]`, motivata come esenzione della **misura**, non
  della regola.
* **Perché è un difetto della forma, non di un codice:** la stessa cecità vale per ogni BB che
  prende il codice dagli argomenti. Un override `highlight_form_fields` su uno qualunque di quei
  codici sarebbe rosso allo stesso modo, e un codice di quella forma che **non** manda il campo
  passerebbe inosservato dal verso 2. Fatto datato (dbdev, 2026-10-10): otto funzioni ricevono un
  codice `E_*` da `tgargs` (`trgfn_lock_columns`, `trgfn_doc_testata_lock_fuori_bozza`,
  `trgfn_doc_righe_lock_fuori_bozza`, `trgfn_doc_guard_emittente_ba`,
  `trgfn_doc_guard_chiusura_sorgente`, `trgfn_doc_ritira_commessa_attivita`,
  `trgfn_fattura_satellite_guard_congelamento`, `trgfn_guard_fatturazione_immediata_immutabile`);
  dei 24 codici così passati la vista ne vede due, `E_CODICE_NON_MODIFICABILE` ed
  `E_COLONNA_NON_MODIFICABILE`, probabilmente perché nominati anche altrove.
* **Richiesta al team DB:** insegnare alla vista la forma «BB trigger col codice negli argomenti» —
  per ogni trigger che esegue una funzione con un codice `E_*` fra i `tgargs`, un sito per quel
  codice, col canale campo della funzione (anche quando il `'campo'` dipende da una condizione,
  come la classe del codice in `trgfn_doc_guard_emittente_ba`).
* **Come si chiude:** quando la vista vede il sito, la riga di `_ESENZIONI` va rossa da sola (verso
  di ritiro del presidio) e il BE la toglie.

⏸️ Al 2026-10-23: aperta. La vista non legge ancora `tgargs` (doc auto-generata) e l'esenzione è
ancora in `test_ui_action_e_canale_campi.py`. Ogni BB trigger nuovo col codice negli argomenti
allarga la cecità senza fare rumore.

⚠️ **La stessa cecità tocca il cancello delle policy** (verificato il 2026-10-27 su dbdev,
correggendo D11). `test_error_codes_db_policy_guardrail` legge `vw_codici_errore_da_dichiarare`,
che cerca i letterali nel **corpo**: un codice che arriva solo da `tgargs` non c'è. Fatto datato:
**30** codici `E_*` stanno solo negli argomenti di un trigger e la misura non li vede (la regex ne
trova 32, ma `E_VENDITA` ed `E_EVASO` sono pezzi di `NATURE_VENDITA` e `PARZIALMENTE_EVASO`).
Oggi **tutti e 30 hanno la loro policy**, quindi nessun buco. Ma un codice nuovo passato così a un
BB trigger, senza policy, **non farebbe rosso il verso 1**: è l'unico punto in cui il registro a
zero dei codici può essere ottimista. Insegnare `tgargs` alla misura chiude tutti e due i presidi,
C2 e le policy, con lo stesso lavoro.

✅ **Al 2026-11-03: chiusa lato DB** — applicata su dbdev e `test-punti-canale-campo-v1` verde
(corsa di Tid). Resta solo la riga del BE qui sotto. Tre changeSet in `20_code/dbops`:

* `20261103-01` — **`dbops.vw_codici_errore_argomenti_trigger`**, la sede unica della lettura
  «i codici che un trigger passa alla sua funzione» (regola del 2: la usano tutti e due i
  presidi). Taglia `tgargs` con `dbops.fn_trigger_argomenti`, e un codice è un argomento
  **intero** `^E_[A-Z0-9_]+$`: niente più `E_VENDITA` da `ORDINE_VENDITA`. Riga `INVENTARIO` in
  `dbops.presidi`;
* `20261103-02` — `vw_punti_canale_campo`: i codici degli argomenti entrano fra i codici della
  funzione, e il ramo che c'era (codice in variabile) li attribuisce, al massimo `IN_VARIABILE`;
* `20261103-03` — `vw_codici_errore_da_dichiarare`: seconda sorgente, `da_trigger` per costruzione.

Prova sull'SQL estratto, dbdev, transazione annullata: C2 da 1.786 a 1.818 righe, nessuna sparita;
`E_DOC_EMITTENTE_BA_INCOERENTE` esce `DIRETTO / IN_VARIABILE / campo`; la misura da 734 a 764
codici, tutti e 30 i nuovi con la policy nel BE (il cancello resta verde); costo stimato di C2 da
12.707 a 14.664 (soglia JIT 100.000). `test-punti-canale-campo-v1` a 18 test (17-18 costruiti), 18
su 18 verdi prima dell'apply.

⚠️ Fatto datato, non toccato qui: la misura `vw_codici_errore_da_dichiarare` stima **~1.010.000**
già prima della revisione (+0,2% dopo), sopra la soglia del JIT, e il presidio JIT non la guarda.

**Richiesta al BE, elenco chiuso** — dopo l'apply:

1. togliere la riga `("E_DOC_EMITTENTE_BA_INCOERENTE", 1)` da `_ESENZIONI` in
   `backend/apps/core/tests/test_ui_action_e_canale_campi.py`: il verso di ritiro (test 2) la dà
   rossa, ed è il segnale previsto;
2. nient'altro: il verso 2 è solo misurato, e i 30 codici nuovi della misura hanno tutti la policy.

### 🟠 D31 — Le righe di contratto CANONE, ORARIO e CONSUMO non hanno la loro generazione

Trovato il 2026-10-13 dalla segnalazione BE del push batch CONTRATTO (un contratto senza scadenza
cadeva sul NOT NULL di `competenza_al`). Il lister dei contratti mandava ogni riga una volta sola, con
la competenza di tutto il contratto: un canone diventava un addebito unico. D-2 (a) di Tid: dal
`20261013-24` il push manda solo le UNA_TANTUM; la generazione per periodo del canone e le quantità di
orario e consumo dalle loro fonti si progettano nel brief
[brief-db-contratto-righe-periodiche-in-commessa.md](../work-done/brief-db-contratto-righe-periodiche-in-commessa.md).
✅ **Al 2026-11-01 il canone è fatto**: decisioni G-0 … G-11 (28-10), lotti L1 … L9 e il giro del §7 lato
DB, il passaggio BE/FE (§7.6, §7.11, §7.13.4). Brief archiviato il 2026-11-01: il collaudo a video
(il form della riga a canone, la colonna «Periodicità» della lista 37) è fra i residui di
PROJECT_CONTEXT. ⏳ Orario e consumo aspettano le loro sorgenti: la voce resta aperta per loro.

## 4. Cosa NON è un difetto

* ⛔ **`contabilita` vuoto.** Fuori perimetro per decisione: se servirà, sarà un
  aggancio a una contabilità esterna, con la forma dettata dal sistema di
  destinazione. Zero test su zero oggetti non è un gap.
* ⛔ **Un dominio modellato che aspetta il suo turno** (`acquisti`, e
  `magazzino` prima dei suoi lotti). Il progetto è nato DB-first per scelta
  (Tid, chiarita il 2026-10-04): un anno sul solo DB per fissare nomi,
  trigger e regole, e poi BE e FE. Proprio l'assenza di consumatori ha reso
  economici i refactor pesanti — rinomine di colonne, la ripartenza in
  `migrations_v2` — che con BE e FE già scritti molti non si sarebbero fatti.
  L'ordine di costruzione non si vota (§5); il difetto, se c'è, è una decisione
  di `vendite` non riportata su `acquisti` (D8).
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

## 5. Scorecard — pesata, non mediata (2026-09-08; voti rivisti il 2026-10-23, il 2026-10-27 e il 2026-11-01)

Il peso è **la conseguenza di un difetto in quell'area**, non la sua estensione. La colonna
«prima» è il voto del 2026-10-27 (la «Simmetria del dominio» non è votata dal 04-10). Il 01-11
si muovono Catena di verifica, Copertura test e Gestione del debito: la corsa CI certifica il
verde dei lotti 1-4 (D7).

| Area                                   | Peso    | Prima  | Voto al 01-11 | Perché |
| -------------------------------------- | ------- | ------ | ------------- | ------ |
| **Catena di verifica (CI)**            | 🔴 alto  | 7,5    | **8,5/10**    | Il cancello tiene dal 09-09, la CI ricostruisce il database col modello dei ruoli di sistema (dal 15-10), e dal 01-11 il registro è **certificato**: 23 rossi su 936, tutti noti, quindi una regressione su uno dei 335 file rientrati ferma il merge. Nello stesso giro è stato chiuso un buco della catena: la suite partiva anche col secondo migratore saltato (909 finti rossi alla corsa `41325095742`), e ora parte solo sul database completo (`fase_post`), senza che un cancello in mezzo possa zittirla. Non di più: i rientrati si tolgono a mano, con uno script, prima che il log scada (pochi giorni), e lo script ne riporta male le regressioni quando sono tante |
| **Perimetro dei dati (RLS)**           | 🔴 alto  | 8      | **8/10**      | D2, D3, D13 e Q-1 chiusi; l'ultimo processo che aggirava la RLS (`zeroerp_batch_fatturazione`) è ritirato il 15-10, e il perimetro dell'operatore si calcola una volta per istruzione (D26-2, D36). Non sale per due cose aperte e di sostanza: la catena delle istanze legge sotto RLS (D18) e i blocchi si spengono con una GUC (Q-2). Le due policy inerti di `acquisti` restano a registro (D8) |
| **Copertura test**                     | 🔴 alto  | 5,5    | **6,5/10**    | Sale perché la proprietà che serve — le migrazioni ricostruiscono da zero un sistema che passa i test — è ora **misurata in CI**: 23 rossi su 936 (01-11), contro 227 su 714 il 26-09; lo scratch (22) e la CI coincidono quasi del tutto. Utente `'1'` a zero, baseline di sviluppo a 3. Non di più: 6 file ancora `ERRORE_FIXTURE` non eseguono nessuna asserzione, `acquisti` è a zero, 119 file hanno uno `skip()` e 147 il runner `owner`, nessuno dei due riletto (D7) |
| **Postura di sicurezza degli oggetti** | 🟠 medio | 8      | **8/10**      | I ruoli di sistema (15-10): un solo proprietario, `zeroerp_job` per i processi, presidio «nessun superuser al lavoro», `zeroerp_log` nella fase dei ruoli (D35). I rubinetti di D6-bis scesi a 16 e 4. Non di più finché Q-2 e D6-bis restano aperti |
| **Simmetria del dominio**              | 🟠 medio | —      | **non votata** | Che lo strato di comportamento di `acquisti` arrivi dopo è l'ordine di costruzione (§4). Resta vero, ed è in D8, il punto **sul modello**: le decisioni prese su `vendite` (dal 13-10 anche grammatica unica, modelli di documento standard, emissione dell'offerta) valgono anche per `acquisti`, e lì non sono scritte |
| **Osservabilità dei presidi**          | 🟠 medio | 7,5    | **7,5/10**    | Ogni riga del presidio dei job dice la sua causa (`brief-db-presidio-job-run-a-chi-tocca`), una spia si spegne solo con un verdetto completo (`brief-db-intermittente-e-verdetto-completo`), il giornale registra il ruolo della corsa, le statistiche hanno un job con autoverifica (D15). Non 8 per il residuo di D10: i processi ritirati nella vista dei job |
| **Gestione del debito**                | 🟠 medio | 6,5    | **7/10**      | I registri col verso giusto hanno funzionato (il bypass, ritirato nei tempi; i codici senza policy, a zero dal 07-08) e calano: il registro della CI 358 → 23 (01-11), smoke 2 → 0 (28-10), baseline di sviluppo 7 → 3, soglia `throws_ok` 115 → 110, utente `'1'` 4 → 0; la baseline B-7 è stata stretta (2 ristretti, 13 rientrati) invece di essere rigenerata alla cieca. Non di più: D18 e Q-2 sono ferme dall'inizio di ottobre (§3), e la soglia `throws_ok` e le FK senza indice non hanno un verso |
| **Pattern trigger e automazioni**      | 🟡 basso | 7,5    | **7,5/10**    | Framework `ci_apply` eccellente; la forma per-figlia continua a crescere (816 trigger da due funzioni, 50 su `catalogo.articoli`), la fase sale al 68% solo perché i trigger nuovi nascono con lei (D9) |
| **Error handling / codici errore**     | 🟡 basso | 8,5    | **8,5/10**    | Contratto a tre lati esplicito e presidiato, e la grammatica unica dà un nome solo al tipo di documento anche nelle eccezioni (lotto 1). Il registro dei codici senza policy è a zero; il B-7 ha fatto il suo mestiere il 01-11 (due codici nuovi da giudicare, giudicati legittimi con la ragione nel commit); il guardrail del naming ha trovato una chiave d'ingresso `tipo_indirizzo_codice` che portava il codice interno, ora `tipo_indirizzo_codice_interno`. I sei `W_` sono ancora senza messaggio (D11-bis), e la misura non vede i codici negli argomenti dei trigger (D24) |
| **Disciplina Liquibase**               | 🟡 basso | 9      | **9/10**      | Oltre 5.700 changeSet in `migrations_v2` (23-10; 3.354 all'08-09), cancelli dedicati nati da incidenti reali |
| **Documentazione**                     | 🟡 basso | 8,5    | **8,5/10**    | Copertura piena; sottile dove il dominio è sottile |
| **Naming**                             | 🟡 basso | 8      | **8/10**      | 94-99% sui vincoli; 68% sulla fase dei trigger, che è la voce con conseguenze; un vocabolario solo per i tipi di documento (grammatica unica) |

### Il giudizio, in una frase

⭐ **Il metodo di ingegneria di questo progetto è sopra la media del settore** —
la guida sui presidi, il contratto a tre lati dei codici errore, il framework
delle automazioni per pattern e il passaggio dei pgTAP al ruolo applicativo sono
cose che in un ERP non si vedono quasi mai. Dal 13-10 vi si è aggiunto il modello dei
ruoli di sistema: il database si installa e si fa girare con i ruoli che avrà in produzione.

✅ **E la catena che deve rendere vero tutto questo, dal 2026-09-09, tiene**:
la suite pgTAP ferma un merge su un rosso nuovo (D1). Fuori dalla macchina di sviluppo la suite
era rossa per due terzi (09-09) e per un terzo alla misura della CI del 26-09 (227 file su 714);
✅ **il 01-11 la CI la dà rossa per il 2,5%** (23 su 936), e il registro lo certifica. La
differenza fra «i test passano» e «le migrazioni sanno ricostruire un sistema che passa i test» si
è quasi chiusa (D7).

⚠️ **Il rischio di oggi non è tecnico, è di attenzione.** Dal 13-10 il lavoro è andato a cantieri
nuovi e ben chiusi, mentre due voci aperte qui sono rimaste ferme: D18 (un difetto vero, che non
dà errore) dal 05-10, Q-2 dal 04-10. Nessuna peggiora da sola, ma nessuna si chiude passandoci
accanto. ✅ Il registro della CI, il terzo fermo, si è chiuso il 01-11.

⚠️ **«Production-ready»**: all'8 settembre non era la parola giusta, e non per
la qualità del design — per D1, D2 e D3: righe di cinque famiglie di documento
su sei e tutto lo storico leggibili da chiunque. Chiusi tutti e tre fra il 9 e
l'11 settembre, la frase torna difendibile sul perimetro dei dati — e il 13
settembre è caduto anche D13, che su un'installazione a due emittenti avrebbe
impedito al secondo di aprire clienti. Quello che resta sono le due policy
inerti di `acquisti` (D4 → D8, a registro con la ragione), D18, Q-2, D6-bis e i 23 rossi della
CI.

---

## 6. Checklist, in ordine di ritorno

> Solo le voci aperte: `[ ]` = **da fare**, `[~]` = **in parte fatta** — sono le voci di §3. Le
> voci `[x]` e il dettaglio di ciò che è fatto stanno nell'archivio (§6 e §7), con data e brief.

### 🔴 Il perimetro

* [x] **D6-bis** — ✅ chiusa il 2026-11-03 (`20261103-04`, `-05`: 20 DEFINER con `pg_temp` in
      coda, rubinetti 4-5 diventati divieti; applicati e verdi) (§3 D6-bis).
      Testo originale della voce: scegliere **una** forma canonica di `search_path` per le
      `SECURITY DEFINER` (`pg_catalog, <schemi necessari>, pg_temp`, con
      `pg_temp` sempre ultimo ed esplicito) e allineare le 16 che oggi non
      elencano `pg_temp` e le 4 che mettono `public` prima di `pg_catalog`
      (2026-10-23; erano 18 e 5).
      ⛔ **Non applicabile a vista**: `pg_catalog, pg_temp` è la scelta sbagliata
      per chi tocca un'estensione (`dblink`, `unaccent`, `postgis`,
      `plpgsql_check` stanno tutte in `public`). Si decide **per funzione**,
      guardando i suoi chiamati — o si qualifica la chiamata, o `public` resta
      nell'elenco.

### 🟠 La sostanza

* [ ] **D8** — `acquisti`: il comportamento. Deciso l'11-09-2026 (Tid) che è il prossimo
      cantiere; `magazzino` ha i lotti 1, 2, 3 e 3-bis (14-10). ⛔ `acquisti` è ancora a zero, e le
      decisioni prese su `vendite` (grammatica unica, modelli standard, emissione dell'offerta) lì non
      sono scritte (§3 D8).
* [~] **D7** — far calare il registro della CI e portare a zero la baseline
      di sviluppo nella *fixture*. ✅ Fatto (§7 D7): il perimetro (12-09), il
      triage delle cause e la riga di contesto che costruisce (20/21-09), il BB
      di composizione e i lotti 1 e 2 (22-24/09), il lotto 3 (`pratiche`) e le famiglie 1-4 del
      lotto 4 (`vendite`, 27-10), e la corsa CI che certifica i rientrati (01-11): **23 rossi su
      936** in CI, contro 227 su 714 il 26-09 e 407 su 601 il 09-09; registro 358 → 23.
      ⏳ Resta (§3 D7): i 23 rossi della CI (la famiglia 5 del lotto 4 e i residui fuori da
      `vendite`), i 2 `ERRORE_FIXTURE` della baseline di sviluppo (3 file), due decisioni per Tid e
      due cancelli da disegnare.
* [~] **D11** — dare a ciascun registro lungo un **verso** (chi lo abbassa, di
      quanto, entro quando), o dichiararlo congelato con il motivo.
      ✅ La soglia `throws_ok` è scesa **129 → 117** fra il 20 e il 24-09, a
      **115** al 13-10 e a **110** al 27-10 (e il cancello vede ora anche `NULL::text`) —
      più volte con un test verde per l'errore sbagliato (§7 D11, §7 D7).
      ✅ I rossi della CI sono scesi da 358 a 23 il 01-11, col loro verso (la corsa e
      `pgtap-baseline-ci-rientrati.sh` lo stesso giorno). ⛔ Restano senza verso la soglia
      `throws_ok` e le FK senza indice (57). I codici da dichiarare (508 → 545 → 702
      al 23-10) non sono un registro ma la misura: il registro, i codici senza
      policy, è a zero (correzione del 27-10, in testa).
      ✅ Il bypass dichiarato è sparito alla data promessa (0 dal 15-10).
* [ ] **D11-bis** — scrivere il messaggio dei sei `W_` che non ce l'hanno
      (append al CSV dei messaggi, mai un loader nuovo), oppure dichiarare che
      quei codici non raggiungono mai un operatore — e scriverlo nel `note`.
      Al 2026-10-23 sono ancora gli stessi sei.
* [ ] **D17** — Q-2, rimandata da Tid: legare le GUC di bypass al proprietario
      delle tabelle (proposta in `work-done/brief-db-esclusioni-implicite.md`
      §4). Il resto di D17 è chiuso (§7), R-1 del BE compresa.
* [ ] **D18** — la catena delle istanze su un PDP: ricalcolo DEFINER della
      catena intera da un trigger `AFTER` senza `OF`; brief
      `work-in-progress/brief-db-catena-istanze-pdp.md`, da analizzare con Tid
      (fermo dal 05-10; il ramo delle istanze fittizie del 14-10 eredita i difetti).

### 🟡 Struttura

* [ ] **D9** — valutare la primitiva unica «figlie da `pg_constraint`» al posto
      dei guard per-figlia, partendo da `catalogo.articoli` (29 `EXISTS` per
      update).
* [ ] **D9-bis** — portare la fase (`_a10_`/`_z90_`) sul 34% di trigger che non
      ce l'ha, o dichiarare che per quelli l'ordine è indifferente.
* [x] **D16** — ✅ chiusa il 2026-11-03: censimento per regola (51 regole, due bombe vere; §3
      D16), `test-data-documento-v1` e `test-promo-articoli-v1` con date relative, verdi alla corsa
      di Tid; guardrail statico escluso (Tid).
* [~] **D24** — ✅ lato DB chiuso il 2026-11-03 (`20261103-01..03`, applicati e verdi). ⏳ Il BE
      toglie l'esenzione di `E_DOC_EMITTENTE_BA_INCOERENTE` (§3 D24).
* [~] **D31** — canone, orario e consumo del contratto in commessa: brief
      `brief-db-contratto-righe-periodiche-in-commessa` (aperto il 2026-10-13, archiviato in
      `work-done/` il 2026-11-01). ✅ Il canone è fatto lato DB e BE; il collaudo a video è fra i
      residui di PROJECT_CONTEXT.
      ⏳ Orario e consumo aspettano le loro sorgenti.

---
