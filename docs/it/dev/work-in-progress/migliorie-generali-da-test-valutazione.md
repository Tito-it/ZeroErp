# Migliorie generali da test valutazione

## ⏭️ Chi riparte — aggiornato al 2026-11-14

**Riparte: il team DB** sulla CI di `Tito-dev`, che dal 2026-11-11 è **rossa a ogni corsa della
suite** (§3 D7, «La CI di `Tito-dev` dall'11-11»); poi i 21 rossi noti e il brief di Q-2. **Tid**
ha le decisioni che tengono ferme D18, D7 e D31.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | team DB | D7: la regressione `catalogo/test-comment-al-presente-catalogo-v1` (`ASSERZIONE`), rossa in CI a ogni corsa dall'11-11 e verde su dbdev | §3 D7 | — |
| 2 | Tid | committare la riga di contesto di `config/test-stati-raggiungibili-v1` (già nell'albero di `dev/db-tid`): senza, il «Guardrail preambolo pgTAP» tiene rosso `e10c71f1d` (merge della PR #114) | §3 D7 | — |
| 3 | Tid | `pgtap-baseline-ci-rientrati.sh 43577800656`: toglie il rientrato `vendite/test-documento-trattenuto-da-lotto-v1` (22 → 21); la regressione la segnala e non la registra. Il log della corsa scade in pochi giorni | §3 D7 | — |
| 4 | team DB | D7: i 21 rossi noti della CI (16 `ASSERZIONE`, 5 `ERRORE_FIXTURE`), uno per uno | §3 D7 | — |
| 5 | Tid | D18: le cinque decisioni della catena delle istanze (ferma dal 2026-10-05) | `brief-db-catena-istanze-pdp.md` §6 | — |
| 6 | team DB | D17 Q-2: le GUC di bypass legate al proprietario — via di Tid il 2026-11-03; serve un brief suo (decisioni aperte, ~45 pgTAP). Non aperto al 14-11 | §3 D17 | — |
| 7 | Tid | D7: i test legati a dati di macchina; il ramo «ultimo SUPER_ADMIN» | §3 D7 | — |
| 8 | Tid | D31: le sorgenti di orario e consumo (le domande le prepara il team DB) | §3 D31 | le sorgenti |

Decisioni aperte di Tid: righe 5, 7 e 8. Lavoro da committare: questo
riallineamento (con D6-bis, D16 e D24 spostate nell'archivio) e la correzione di
`scripts/indicatori-qualita-db.sh`, che dal 03-11 stampava «? / ?» per D6-bis; le tre righe `SENZA_INDICE` di `80_data/sql/dbops/fk_index_policy.csv` e il changeSet `20261114-21` (D11, applicati e a 0 il 14-11), con le quattro pagine `manual/` che nominavano gli indici tolti. ⚠️ Fuori dal
perimetro di questo documento, ma nella stessa catena: i test Django in CI sono rossi in più corse
dall'11-11 (all'ultima con la suite, `43577800656`: 13 su 7.266, `E_DOCUMENTI_TEMPLATE_NON_RISOLTO`
in `apps.documenti.tests.db`); verdi alla corsa `43584113226` del 14-11.

> **Ultima revisione: 2026-11-14.** Valutazione dello strato DB, aperta il 2026-09-08. Qui sta
> **solo ciò che è vivo**: chi riparte, i difetti aperti (§3), cosa non è un difetto (§4), la
> scorecard (§5) e la checklist delle voci aperte (§6). La valutazione di febbraio (§1), ciò che è
> nato in sette mesi (§2), la valutazione del design del 04-10 (§2-bis), le voci chiuse (§7) e i
> riallineamenti della testata sono nell'**archivio**,
> [migliorie-generali-da-test-valutazione-storia.md](../work-done/migliorie-generali-da-test-valutazione-storia.md), con la stessa numerazione: un
> rimando «§D13» o «§7 D7» da un changeSet o da un brief si legge lì.
>
> **Numeri del 2026-11-14** (repo e catalogo di dbdev con `scripts/indicatori-qualita-db.sh
> --catalogo`; la CI dall'ultima corsa con la suite, `43577800656` su `Tito-dev`, `8e9046041`, letta
> con `pgtap-baseline-ci-rientrati.sh --dry-run`): suite pgTAP a **1.062** file; in CI **22 rossi su
> 1.060** — 21 noti, **1 regressione**, 1 rientrato non ancora tolto; `baseline-rossi-ci.tsv` a **22**
> (5 `ERRORE_FIXTURE`, 17 `ASSERZIONE`: l'11-11 è uscito `test-indirizzi-fallback`);
> `baseline-rossi-scratch.tsv` a **20** (4 / 16); `baseline-rossi.tsv` a **3**;
> `SOGLIA_THROWS_SENZA_DISCRIMINANTE` a **109**; utente `'1'` a zero; smoke non verdi a **0**; 124
> file con `skip()`, 183 con `pgtap-runner: owner`. Gli indicatori vivono in
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

> Solo il lavoro che resta. Le voci chiuse — per intero D1-D6 (con D6-bis), D10, D12-D16,
> D19-D30, D32-D36, D26-2; in parte D7, D11, D17 — sono nell'archivio, §7, con data e brief.
> D6-bis, D16 e D24, chiuse il 2026-11-03, ci sono state spostate il 2026-11-14. Quando una voce ha
> ancora una parte aperta, il numero compare in tutti e due i posti.

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

⏸️ **Al 2026-11-14: via di Tid il 2026-11-03, brief non ancora aperto.** Nessun file in
`work-in-progress/` porta il lavoro; la voce è ferma da sei settimane.

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

⏸️ **Al 2026-11-14: invariata.** Il brief è fermo al 2026-10-16 («proposta da analizzare», niente
in `migrations_v2/`), e `trgfn_clienti_set_parent_istanza` non ha changeSet dopo `20261014-17`.

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

🔴 **La CI di `Tito-dev` dall'11-11: rossa a ogni corsa della suite** (letto il 2026-11-14 dalle
corse di `ci-validate` con `pgtap-baseline-ci-rientrati.sh --dry-run`). Il registro della CI è stato
toccato una volta sola dopo il 01-11 (11-11, `44042d9a8d`: esce `test-indirizzi-fallback`, 23 → 22),
ma da quel giorno nessuna corsa della suite è verde:

| Corsa | Giorno | Rossi | Regressioni |
| --- | --- | --- | --- |
| `43104161131` | 11-11 | 23 su 1.040 | `catalogo/test-comment-al-presente-catalogo-v1` |
| `43500698887` | 13-11 | 23 su 1.057 | la stessa, più `config/test-codici-errore-identita` (`ERRORE_FIXTURE`, poi rientrata) |
| `43577800656` | 14-11 | 22 su 1.060 | la stessa; e `vendite/test-documento-trattenuto-da-lotto-v1` **rientrato** |

* `test-comment-al-presente-catalogo-v1` è nato l'11-11 (`9f2899c8ba`, giro 5-A di
  `brief-db-revisione-catalogo`): è verde su dbdev e rosso su un database ricostruito da zero, e non
  sta in nessuno dei tre registri. È il caso che il cancello deve fermare, e lo ferma: da tre giorni
  ogni merge di `dev/db-tid` su `Tito-dev` porta la CI rossa. La causa non è letta qui: il runner
  della CI stampa solo il nome del file, e quale dei cinque test cade (e su quale `COMMENT`) si vede
  rilanciandolo sullo scratch ricostruito.
* Il rientrato non è stato tolto: la corsa è del 14-11 mattina, e il log scade.
* All'ultimo merge (`e10c71f1d`, PR #114) la suite non è nemmeno partita: il «Guardrail preambolo
  pgTAP» è rosso su `config/test-stati-raggiungibili-v1` senza la riga di contesto. La correzione è
  nell'albero di `dev/db-tid`, non committata (14-11).
* ⚠️ Nelle stesse corse sono rossi anche i **test Django** (13 su 7.266 alla `43577800656`,
  `E_DOCUMENTI_TEMPLATE_NON_RISOLTO` in `apps.documenti.tests.db`), verdi alla `43584113226` del 14-11
  dopo il merge BE: non è lavoro di questo documento, ma un rosso Django fa saltare il segnale della
  suite allo stesso modo.

⛔ La lezione è quella del 01-11 vista dall'altra parte: un cancello che è rosso **per giorni** smette
di essere letto. Il registro certificato vale finché ogni regressione si chiude il giorno in cui la CI
la nomina.

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

* 🔴 **prima di tutto, la regressione** `test-comment-al-presente-catalogo-v1` (sopra): finché c'è,
  la CI non dice niente dei rossi nuovi;
* ⏳ **i rossi noti della CI**, uno per uno: **22** a registro al 14-11, **21** tolto il rientrato —
  16 `ASSERZIONE` (fra cui i file su identità digitali e `auth_user`, il caso dei «due mondi» di
  `django` in CI, e la famiglia 5 del lotto 4 in `vendite`) e 5 `ERRORE_FIXTURE`
  (`test-catasto-unita-immobiliare`, `test-processi-jobname-wrapper`,
  `test-search-soggetti-universale`, `test-vw-giornale-entita`, `test-snapshot-indirizzi-fattura-v1`;
  ✅ `test-indirizzi-fallback` uscito l'11-11). Sostituiscono i residui dei lotti 1 e 2, che si
  contavano sul registro vecchio;
* ✅ **lotto 3** — `pratiche`: chiuso il 2026-10-27 (corsa di Tid). Dettaglio nell'archivio, §7 D7.
* 🟡 **lotto 4** — `vendite`: famiglie 1-4 (commesse e attività, fatture-lotti-registri, preventivi-ordini-
  valuta, listini e prezzi; 77 file) chiuse il 2026-10-27, dettaglio e verdi falsi trovati nell'archivio,
  §7 D7. ⏳ Resta la **famiglia 5**: i rossi `ASSERZIONE` di `vendite` (8 nel registro della CI al
  01-11; 7 al 14-11, tolto il rientrato `test-documento-trattenuto-da-lotto-v1`), uno per uno. Con loro gli altri rossi della CI fuori da `vendite` (`anagrafiche`, `script`,
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
* ⏳ la **baseline di sviluppo** (`baseline-rossi.tsv`): **3** file, ferma dal 01-11 (4 al 27-10, 6 al
  23-10, 7 al 13-10, 12 al 26-09), di cui **2** muoiono nella fixture, tutti e due in `anagrafiche`;
* ⏳ i file con `pgtap-runner: owner`: **183** al 14-11 su 1.062 (147 al 03-11, 145 al 23-10, 109 al
  22-09). Sono cresciuti di 36 in undici giorni, più in fretta della suite (+123 file): quanti di
  quei motivi siano ancora veri dopo la rev `20260912-38` non è misurato, e ogni file in più è un
  test che non prova la postura dell'app;
* ⏳ i file con uno `skip()` condizionato: **124** al 14-11 (119 al 03-11, 122 al 23-10, 110 all'08-09);
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

⏸️ **Al 2026-11-14** (catalogo di dbdev): `magazzino` a **28** file pgTAP. ⛔ `acquisti` resta lo
schema senza nessun pgTAP; 9 tabelle, **nessuna** con la RLS, nessuna colonna emittente (Q-5
sotto, invariata). Lo hanno toccato solo tre changeSet di regole generali, nessuno di comportamento:
la sorgente polimorfa (`20261105-03`, `20261106-06`, `brief-db-sorgente-documento-e-riga`) e la vista
delle note (`20261112-33`, `brief-db-revisione-catalogo`). Una funzione e una vista. Le decisioni di
`vendite` da riportare intanto sono cresciute: gli stati del documento dal vocabolario e la
provenienza del prezzo che segue il prezzo (tutti e due in corso, 13/14-11).

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

⏸️ **Al 2026-11-14 (catalogo di dbdev)**: `catalogo.articoli` a **54** trigger; le due funzioni
per-figlia ne montano **862** su 2.676; la fase nel nome su **1.909**, il **71%**. Stesso verso,
stessa causa: nessun lavoro sulla voce.

---

### 🟡 D11 — I registri di debito non calano

Un registro di debito è una buona invenzione **a condizione che scenda**. Stato
al 2026-09-08, salvo dove è scritta un'altra data:

| Registro | Oggi (2026-11-14: repo, catalogo di dbdev, ultima corsa CI con la suite) |
| --- | --- |
| `dbops.codici_errore_senza_policy` | ✅ **0** dal 2026-08-07 — ⛔ *non* il conteggio di `vw_codici_errore_da_dichiarare` (824 al 14-11, 702 al 23-10), che è la misura: vedi sotto |
| `db/pgtap/baseline-rossi-ci.tsv` | **22** file (5 `ERRORE_FIXTURE`, 17 `ASSERZIONE`), toccato l'11-11 (−`test-indirizzi-fallback`); alla corsa `43577800656` (14-11) **un rientrato da togliere e una regressione** fuori registro, rossa dall'11-11 (D7) — 23 certificati il 01-11 dalla `41326840441`, era 358; nato il 09-09 con 407 |
| `db/pgtap/baseline-rossi-scratch.tsv` | **20** file (4 `ERRORE_FIXTURE`, 16 `ASSERZIONE`) al 13-11 — 22 al 01-11, 24 su 916 al 27-10, 147 su 887 al 20-10 |
| `db/baseline-codici-errore-famiglie.tsv` (B-7) | **220** codici, riallineata il 07-11 (219 al 01-11, 212 al 13-10); la CI del 14-11 ne dà 2 rientrati da togliere |
| `SOGLIA_THROWS_SENZA_DISCRIMINANTE` | **109** al 14-11 (110 al 27-10, 115 al 13-10, 117 al 26-09, 129 all'08-09) |
| `dbops.vw_fk_da_decidere` | **498** al 14-11. ⚠️ Non confrontabile col 57 di prima: il 2026-11-10 (`20261110-49`, `-50`, `brief-db-revisione-dbops` N6-N7) la vista vecchia, `vw_fk_con_indice_missing_policy`, è ritirata perché contava anche FK già coperte; la nuova conta le FK scoperte senza decisione, o decise e non applicate. È il primo numero vero, non una crescita |
| `db/pgtap/baseline-rossi.tsv` | **3** file (2 `ERRORE_FIXTURE`, 1 `ASSERZIONE`), fermo dal 01-11 — 4 al 27-10, 6 al 23-10, 7 al 13-10, 12 al 24-09, erano 19 |
| `dbops.rls_perimetro_debito` | **6** righe nel seed (7 al 20-09, era 10 → D2) |
| `backend/scripts/tests/baseline-smoke.tsv` | ✅ **0** dal 28-10 (2 su 52 script al 23-10, 7 al 13-10) |
| Header di licenza mancanti | 2.042 file (misura 2026-08-26, non rifatta) |
| `dbops.vw_indici_ridondanti_prefisso` | ✅ **0** su dbdev e sullo scratch dal 2026-11-14 (era 4 su dbdev e 21 sullo scratch la mattina; 1 al 23-10). (1) Tre in `ui` (`lista_colonna`, `lista_preset`, `dashboard_preset`), solo su dbdev: indici FK coperti dalla UNIQUE `(…_id, codice)`, con la riga della politica a `CON_INDICE` dal CSV unico del 10-11, visibili da quando la vista confronta il nome per uguaglianza (D23 di `brief-db-revisione-dbops`): le righe sono passate a `SENZA_INDICE` col motivo, e li ha tolti `apply_fk_index_policy()`. (2) **21 storici `MANUALE` su un database da zero**: venti nati nella prima generazione congelata coi nomi di allora (`ix_ordrig_testata`…), più `dbops.ix_processi_bersagli_processo_id` (`20260904-08`). Su dbdev li aveva tolti `20260116-09`, che droppava lo storico solo accanto al gemello canonico, e da zero il gemello non nasce più: dev ≠ installazione nuova. Tolti da `20261114-21`, applicato su dbdev e sullo scratch. ⚠️ Nessun pgTAP tiene la vista a zero: il presidio è una coda di lavoro |
| Codici vivi senza messaggio | 6 (tutti `W_`, §2.3) — gli stessi sei |
| `dbops.vw_processi_che_bypassano` | ✅ **0** dal 2026-10-15 (era 1, dichiarato con la data di ritiro: ritirato nei tempi) |
| `SECURITY DEFINER` senza `pg_temp` / con `public` prima di `pg_catalog` | ✅ **0 / 0** dal 2026-11-03: divieti, non più rubinetti (D6-bis, nell'archivio). 152 DEFINER su dbdev al 14-11 |

⭐ La riga di `vw_processi_che_bypassano` è la meglio fatta: **una** voce, con il motivo e il momento in
cui sparisce — ✅ ed è sparita quando diceva. ✅ Il 01-11 i rossi della CI sono scesi da 358 a 23:
il verso c'era (`pgtap-baseline-ci-rientrati.sh`), mancava la corsa che lo facesse girare. ⚠️ Dal
11-11 il verso c'è ancora ma la corsa verde no (D7): il registro non scende perché la CI non arriva
in fondo pulita. Le due liste lunghe che restano (la soglia `throws_ok`, che cala di uno al mese; le
FK da decidere, 498 al primo conteggio vero del 14-11) non hanno un verso, e la guida sui presidi dice
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
(5 in CI e 2 in sviluppo al 14-11; 6 e 2 al 01-11; 292 e 6 al 13-10) non eseguono **nessuna**
asserzione. La loro copertura vale zero, non «parziale» — e sono aree che
*sembrano* coperte.

---

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
⏸️ Al 2026-11-14: invariata.

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

## 5. Scorecard — pesata, non mediata (2026-09-08; voti rivisti il 2026-10-23, il 2026-10-27, il 2026-11-01 e il 2026-11-14)

Il peso è **la conseguenza di un difetto in quell'area**, non la sua estensione. La colonna
«prima» è il voto del 2026-11-01 (la «Simmetria del dominio» non è votata dal 04-10). Il 14-11
scende la Catena di verifica (la CI di `Tito-dev` è rossa a ogni corsa della suite dall'11-11) e
salgono la Postura di sicurezza (D6-bis chiusa) e l'Error handling (D24 chiusa, DB e BE). I numeri
sono quelli della testata, letti il 14-11.

| Area | Peso | Prima | Voto al 14-11 | Perché |
| --- | --- | --- | --- | --- |
| **Catena di verifica (CI)** | 🔴 alto | 8,5 | **7,5/10** | Il meccanismo tiene, e lo dimostra: la regressione `test-comment-al-presente-catalogo-v1` la CI l'ha nominata alla prima corsa (11-11) e a tutte le successive, e `main` è protetto (nessuna PR verso `main` dopo il 10-11). Scende perché **il segnale non è stato letto**: tre giorni di suite rossa su `Tito-dev` senza una correzione, un rientrato non tolto mentre il log scade, e l'ultimo merge rosso già sul guardrail del preambolo (correzione pronta, non committata). Un cancello rosso per giorni smette di distinguere un rosso nuovo dal vecchio. Torna a 8,5 con la prima corsa verde e il registro allineato |
| **Perimetro dei dati (RLS)** | 🔴 alto | 8 | **8/10** | Fermo, e per le stesse ragioni: la catena delle istanze legge sotto RLS (D18, ferma dal 05-10) e i blocchi si spengono con una GUC (Q-2: via di Tid il 03-11, brief non aperto). `acquisti` ha 9 tabelle e nessuna con la RLS (D8) |
| **Copertura test** | 🔴 alto | 6,5 | **6,5/10** | Ferma. La proprietà che serve resta misurata in CI: 22 rossi su 1.060 (14-11), e la suite è cresciuta di 123 file in undici giorni. La tengono: 5 file `ERRORE_FIXTURE` che non eseguono nessuna asserzione, `acquisti` a zero, gli `skip()` saliti a 124 e soprattutto i runner `owner` a **183** (+36 dal 03-11), più in fretta della suite e senza rilettura dei motivi (D7) |
| **Postura di sicurezza degli oggetti** | 🟠 medio | 8 | **8,5/10** | Sale: D6-bis è chiusa (03-11), tutte le DEFINER (152 su dbdev) elencano `pg_temp` e mettono `pg_catalog` in testa, e i due rubinetti sono diventati divieti. Ruoli di sistema dal 15-10. Non di più finché Q-2 resta aperta |
| **Simmetria del dominio** | 🟠 medio | — | **non votata** | L'ordine di costruzione non si vota (§4). Resta vero, ed è in D8, il punto **sul modello**: le decisioni di `vendite` valgono anche per `acquisti`, e dal 01-11 se ne sono aggiunte altre (gli stati dal vocabolario, la provenienza del prezzo). `acquisti` ha ricevuto solo le regole generali (sorgente polimorfa, vista delle note) |
| **Osservabilità dei presidi** | 🟠 medio | 7,5 | **7,5/10** | Il presidio dei job dice la causa, la spia si spegne su un verdetto completo, le statistiche hanno un job con autoverifica (D15); dal 10-11 le FK da decidere hanno una vista che conta il vero (`vw_fk_da_decidere`, `brief-db-revisione-dbops`). Non 8: il residuo di D10 (i processi ritirati nella vista dei job) non è riletto qui |
| **Gestione del debito** | 🟠 medio | 7 | **7/10** | Fermo, con due spinte opposte. Su: tre voci chiuse in un giro (D6-bis, D16, D24, 03-11), `throws_ok` a 109, B-7 riallineata. Giù: il registro della CI non scende dall'11-11 (D7), D18 e Q-2 sono ferme da sei settimane, gli indici ridondanti per prefisso tornati a 4 (a 0 la sera del 14-11, con i 21 storici di un database da zero) e le FK da decidere sono **498** al primo conteggio vero, senza un verso |
| **Pattern trigger e automazioni** | 🟡 basso | 7,5 | **7,5/10** | Framework `ci_apply` eccellente; la forma per-figlia continua a crescere (862 trigger da due funzioni su 2.676, 54 su `catalogo.articoli`), la fase sale al 71% solo perché i trigger nuovi nascono con lei (D9) |
| **Error handling / codici errore** | 🟡 basso | 8,5 | **9/10** | Sale: D24 è chiusa da tutti e due i lati, e la misura e il presidio C2 leggono anche i codici negli argomenti dei trigger (una sede, `vw_codici_errore_argomenti_trigger`). Codici senza policy a zero, 824 codici nominabili tutti dichiarati. Restano i sei `W_` senza messaggio (D11-bis) |
| **Disciplina Liquibase** | 🟡 basso | 9 | **9/10** | 6.911 changeSet in `migrations_v2`, cancelli nati da incidenti reali (11 guardrail, 10 in CI). ⚠️ 36 file senza `logicalFilePath`, una regola di AGENTS.md senza presidio |
| **Documentazione** | 🟡 basso | 8,5 | **8,5/10** | Copertura piena (1.863 pagine `manual/` su 2.106 auto-generate); sottile dove il dominio è sottile |
| **Naming** | 🟡 basso | 8 | **8/10** | 94-99% sui vincoli; 71% sulla fase dei trigger, che è la voce con conseguenze; un vocabolario solo per i tipi di documento |

### Il giudizio, in una frase

⭐ **Il metodo di ingegneria di questo progetto è sopra la media del settore** —
la guida sui presidi, il contratto a tre lati dei codici errore, il framework
delle automazioni per pattern e il passaggio dei pgTAP al ruolo applicativo sono
cose che in un ERP non si vedono quasi mai. Dal 13-10 vi si è aggiunto il modello dei
ruoli di sistema: il database si installa e si fa girare con i ruoli che avrà in produzione.

✅ **La catena che deve rendere vero tutto questo tiene come meccanismo**: la suite pgTAP ferma
un merge verso `main` su un rosso nuovo (D1), e fuori dalla macchina di sviluppo è rossa per il 2%
(22 su 1.060, 14-11), contro due terzi il 09-09. ⚠️ **Ma dall'11-11 il suo segnale su `Tito-dev`
non è stato ascoltato**: una regressione nominata a ogni corsa per tre giorni, e un rientrato che
aspetta. Non è un difetto tecnico, ed è proprio per questo che costa: il giorno in cui arriva una
seconda regressione, nessuno la distingue dalla prima (D7).

⚠️ **Il rischio di oggi resta di attenzione, e si è allargato.** Il lavoro va a cantieri nuovi e
ben chiusi — il 03-11 ne sono uscite anche tre voci di qui, D6-bis, D16 e D24 — mentre D18 (un
difetto vero, che non dà errore) è ferma dal 05-10 e Q-2, che dal 03-11 ha il via, non ha ancora un
brief. Nessuna peggiora da sola, ma nessuna si chiude passandoci accanto; e alle due si è aggiunta
la CI rossa, che invece peggiora da sola.

⚠️ **«Production-ready»**: all'8 settembre non era la parola giusta, e non per
la qualità del design — per D1, D2 e D3: righe di cinque famiglie di documento
su sei e tutto lo storico leggibili da chiunque. Chiusi tutti e tre fra il 9 e
l'11 settembre, la frase torna difendibile sul perimetro dei dati — e il 13
settembre è caduto anche D13, che su un'installazione a due emittenti avrebbe
impedito al secondo di aprire clienti; il 03-11 D6-bis. Quello che resta sono le due policy
inerti di `acquisti` (D4 → D8, a registro con la ragione), D18, Q-2, la regressione in CI e i 21
rossi noti.

---

## 6. Checklist, in ordine di ritorno

> Solo le voci aperte: `[ ]` = **da fare**, `[~]` = **in parte fatta** — sono le voci di §3. Le
> voci `[x]` e il dettaglio di ciò che è fatto stanno nell'archivio (§6 e §7), con data e brief.

### 🔴 La catena

* [ ] **D7, la CI di `Tito-dev`** — rossa a ogni corsa della suite dall'11-11: la regressione
      `catalogo/test-comment-al-presente-catalogo-v1`, il rientrato da togliere
      (`vendite/test-documento-trattenuto-da-lotto-v1`) e la riga di contesto di
      `config/test-stati-raggiungibili-v1` da committare (§3 D7, «La CI di `Tito-dev`
      dall'11-11»).

### 🔴 Il perimetro

* [ ] **D18** — la catena delle istanze su un PDP: ricalcolo DEFINER della
      catena intera da un trigger `AFTER` senza `OF`; brief
      `work-in-progress/brief-db-catena-istanze-pdp.md`, da analizzare con Tid
      (fermo dal 05-10; il ramo delle istanze fittizie del 14-10 eredita i difetti).
* [ ] **D17** — Q-2: legare le GUC di bypass al proprietario delle tabelle (proposta in
      `work-done/brief-db-esclusioni-implicite.md` §4). Via di Tid il 2026-11-03; il brief suo non è
      ancora aperto (14-11). Il resto di D17 è chiuso (§7), R-1 del BE compresa.

### 🟠 La sostanza

* [ ] **D8** — `acquisti`: il comportamento. Deciso l'11-09-2026 (Tid) che è il prossimo
      cantiere; `magazzino` ha i lotti 1, 2, 3 e 3-bis (14-10). ⛔ `acquisti` è ancora a zero
      pgTAP, senza RLS e senza emittente, e le decisioni prese su `vendite` (grammatica unica,
      modelli standard, emissione dell'offerta, stati dal vocabolario, provenienza del prezzo) lì
      non sono scritte (§3 D8).
* [~] **D7** — far calare il registro della CI e portare a zero la baseline
      di sviluppo nella *fixture*. ✅ Fatto (§7 D7): il perimetro (12-09), il
      triage delle cause e la riga di contesto che costruisce (20/21-09), il BB
      di composizione e i lotti 1 e 2 (22-24/09), il lotto 3 (`pratiche`) e le famiglie 1-4 del
      lotto 4 (`vendite`, 27-10), la corsa CI che certifica i rientrati (01-11, registro 358 → 23) e
      `test-indirizzi-fallback` (11-11, 23 → 22).
      ⏳ Resta (§3 D7): la CI rossa (sopra), poi i 21 rossi noti (la famiglia 5 del lotto 4 e i
      residui fuori da `vendite`), i 2 `ERRORE_FIXTURE` della baseline di sviluppo (3 file), la
      rilettura dei 183 runner `owner`, due decisioni per Tid e due cancelli da disegnare.
* [~] **D11** — dare a ciascun registro lungo un **verso** (chi lo abbassa, di
      quanto, entro quando), o dichiararlo congelato con il motivo.
      ✅ La soglia `throws_ok` è scesa **129 → 117** fra il 20 e il 24-09, poi a 115 (13-10), 110
      (27-10) e **109** (14-11) — più volte con un test verde per l'errore sbagliato (§7 D11, §7 D7).
      ✅ I rossi della CI sono scesi da 358 a 23 il 01-11, col loro verso; ⚠️ dall'11-11 il verso
      c'è ma la corsa verde no (D7).
      ⛔ Restano senza verso la soglia `throws_ok` e le FK da decidere (**498** al 14-11, il primo
      conteggio vero: la vista di prima, a 57, è ritirata il 10-11). ✅ Gli indici ridondanti per
      prefisso a 0 su dbdev e sullo scratch (14-11): tre in `ui` con le righe del CSV a
      `SENZA_INDICE`, 21 storici `MANUALE` con `20261114-21`, applicati.
      I codici da dichiarare (824 al 14-11) non sono un registro ma la misura: il registro, i
      codici senza policy, è a zero (correzione del 27-10, in testa).
      ✅ Il bypass dichiarato è sparito alla data promessa (0 dal 15-10).
* [ ] **D11-bis** — scrivere il messaggio dei sei `W_` che non ce l'hanno
      (append al CSV dei messaggi, mai un loader nuovo), oppure dichiarare che
      quei codici non raggiungono mai un operatore — e scriverlo nel `note`.
      Al 2026-11-14 sono ancora sei.

### 🟡 Struttura

* [ ] **D9** — valutare la primitiva unica «figlie da `pg_constraint`» al posto
      dei guard per-figlia, partendo da `catalogo.articoli` (54 trigger al 14-11).
* [ ] **D9-bis** — portare la fase (`_a10_`/`_z90_`) sul 29% di trigger che non
      ce l'ha (14-11; era il 34% all'08-09), o dichiarare che per quelli l'ordine è indifferente.
* [~] **D31** — canone, orario e consumo del contratto in commessa: brief
      `brief-db-contratto-righe-periodiche-in-commessa` (aperto il 2026-10-13, archiviato in
      `work-done/` il 2026-11-01). ✅ Il canone è fatto lato DB e BE; il collaudo a video è fra i
      residui di PROJECT_CONTEXT.
      ⏳ Orario e consumo aspettano le loro sorgenti.

---
