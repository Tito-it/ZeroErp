# Brief DB — Il mondo si costruisce: il building block della composizione (D7, giro 2)

> **Da leggere per primo: §3 — la forma, e perché non sta nella riga di contesto.**
> Origine: [migliorie-generali-da-test-valutazione.md](migliorie-generali-da-test-valutazione.md)
> §3 D7 («la ricetta per file»), figlio del brief madre
> [brief-db-fixture-che-costruiscono-d7-d6-d4.md](../work-done/brief-db-fixture-che-costruiscono-d7-d6-d4.md)
> (giro 1, chiuso il 12-09) e della rev `20260920-01`, che ha insegnato alla riga
> di contesto a **costruire** il mondo quando non lo trova.
>
> ✅ **Stato 2026-09-23: il lotto 1 è CHIUSO e APPLICATO.** Tutti e quattro i
> changeSet sono in servizio su dbdev e su `zeroerp_ci` — `20260922-17`
> (`fn_pgtap_crea_mondo_cliente`, 22-09), `20260923-01` (il builder degli
> articoli sceglie la UoM), `20260923-04` (`fn_pgtap_crea_fattura`) e
> `20260923-05` (`fn_pgtap_crea_filiale_bancaria`) — con **21 file riscritti**,
> tre presidi nuovi e **nessuna regressione** (Tid, 23-09). Committato in
> `9304f209c`, PR #1649. Dettaglio in §10.
>
> ✏️ **Lotto 2 in corso dal 23-09** (`anagrafiche` 39 + `script` 31, §11): il
> debito dei `COMMIT`/autocommit è **chiuso** — nessun file della suite committa
> più — e con lui è caduta la maschera che teneva verdi sei file per un residuo.
> Builder nuovo `fn_pgtap_crea_gestore` (`20260923-06`), **applicato, nessuna
> regressione**. 12 file su 70 verdi sul mondo vuoto.
>
> ✏️ **Ripresa del 23-09 pomeriggio (§11, in coda)**: lotto 2 da 16 a **22
> verdi** sul mondo vuoto, più **11 verdi in attesa** di tre changeSet nuovi
> **da applicare** — `20260923-07` (il codice libero del cliente si leggeva
> sotto RLS), `-08` (`fn_pgtap_crea_operatore_umano`, il super admin senza
> azienda), `-09` (`fn_pgtap_crea_pdp`). Famiglie chiuse: cliente, `RIS_UMANA`,
> `pdp_id`, registri, utente `'1'`. Restano 36 file, elencati per forma in
> fondo al §11. Corretto anche il profilo super admin legato per id cablato
> `9100` (`-10`, da applicare). Il `CHECK` sulle date che oggi non parla (§11 —
> non è inutile, il difetto è la frase che legge l'operatore) ha ora un brief
> suo, in riflessione:
> [brief-db-guard-date-validita.md](brief-db-guard-date-validita.md).
>
> ⏳ **Quello che manca non è lavoro, è una corsa**: il registro
> `baseline-rossi-ci.tsv` è ancora a 361 file. Le righe rientrate le toglie
> `scripts/pgtap-baseline-ci-rientrati.sh` leggendo il **log della corsa CI**,
> e il log scade: va lanciato il giorno stesso della push su `Tito-dev` che
> tocca `db/`. Finché non succede, il registro racconta un debito che in buona
> parte non c'è più.
>
> ⛔ **Fuori perimetro**: i 4 file che chiudono in `COMMIT` e i 6 che chiamano la
> riga di contesto in autocommit. Decisione rinviata da Tid il 22-09 — *prima la
> forma*. ⚠️ Resta vero che quel debito **maschera** il caso dei vincoli
> differiti: il giorno in cui si chiude, ogni file che conta sulla finestra di
> default cade (censiti e sanati: tre).

---

## 1. Il difetto, sul modello

Una fixture **dichiara il mondo** di cui il suo caso ha bisogno. Oggi ogni file
lo **compone da sé**, e nel comporlo deve conoscere una regola d'ordine che nel
file non è scritta da nessuna parte:

* prima il mondo, **poi** `script.fn_pgtap_set_contesto_operatore(...)`;
* con un operatore già in sessione, il legame BA → emittente lo scrive **anche**
  il trigger `z90` del billing account, e i due si scontrano su
  `uq_emittenti_fiscali_ba`;
* gli helper escono con i vincoli **IMMEDIATE**: chi vuole la finestra differita
  la riapre dichiarandolo (rev `20260921-18`).

⭐ **I builder atomici esistono già, e sono buoni** — ognuno sa costruire la sua
entità e dice nel `COMMENT` perché pescarla sarebbe sbagliato:

| Entità | Builder |
| --- | --- |
| azienda + operatore + identità | `dbops.fn_pgtap_crea_emittente_operatore()` |
| cliente fatturabile (soggetto → CL → istanza → BA) | `dbops.fn_pgtap_crea_cliente_ba()` |
| articolo con i flag scelti dal test | `dbops.fn_pgtap_crea_articolo()` |
| soggetto PG / ruolo con i suoi indirizzi | `dbops.fn_pgtap_crea_soggetto_pg()` + `_crea_soggetto_ruolo()` |
| registro di fatturazione coerente | `script.fn_pgtap_registro_fattura()` |

⛔ **Ciò che non esiste è la composizione** — ed è esattamente il pezzo che porta
la regola d'ordine. Quindi la regola non vive in un oggetto: vive **in ogni
file**, riscritta a mano, e un file scritto prima che la regola fosse nota non la
rispetta e nessuno se ne accorge finché non gira su un database vuoto.

⛔ **Corollario, e cambia l'unità di lavoro**: sanare «per prima causa» non chiude
un file. La causa misurata è la **prima** che il file incontra; curata quella, il
file muore sulla seconda. L'unità non è la causa, è la **forma**: un file che
*cerca* va portato a *costruire*, tutto insieme.

---

## 2. Il censimento — fatti datati (2026-09-22, letture sui file del repo)

Registro `db/pgtap/baseline-rossi-ci.tsv`: **361 file** (292 `ERRORE_FIXTURE`,
69 `ASSERZIONE`).

| Forma, dentro i 361 file a registro | File |
| ----------------------------------- | ---- |
| costruiscono una `TEMP TABLE` di riferimenti **pescando** (`… _refs/_ids AS SELECT (SELECT … LIMIT 1)`) | **205** |
| …e dentro quel blocco pescano un **billing account** | 150 |
| pescano un billing account, in qualunque punto del file | **170** |
| pescano un **soggetto** | 35 |
| fissano l'utente di sessione a `'1'` (in CI non esiste) | 28 |
| pescano un **registro di fatturazione** | 9 |
| vogliono `ART_TEST_BASE`/`ART_TEST_FALLBACK`, che non sono a seed | 7 |
| dipendono da dati di **questa macchina** (CF `TTNMHL…`, PIVA `24551170426`, PDP GAS) | 7 |
| usano **un builder** | 3 |

**Che cosa pescano** (occorrenze di `FROM <relazione> … LIMIT 1`, e su quanti
file):

| Relazione | occ | file | | Relazione | occ | file |
| --- | --- | --- | --- | --- | --- | --- |
| `anagrafiche.billing_account` | 337 | 170 | | `config.tipi_doc_fiscale` | 88 | 85 |
| `config.valute` | 134 | 134 | | `config.iva` | 82 | 74 |
| `catalogo.articoli` | 130 | 113 | | `catalogo.unita_misura` | 68 | 67 |
| `anagrafiche.emittenti_fiscali` | 112 | 100 | | `anagrafiche.soggetti_ruoli` | 59 | 52 |
| `config.stati_doc_ddt` | 97 | 35 | | `vendite.listini` | 34 | 31 |
| `config.sorgenti` | 97 | 63 | | `vendite.tipi_doc_fiscale_registri` | 30 | 20 |

⭐ **La riga di lettura è una sola, e divide l'elenco in due.** Le relazioni di
`config`/`catalogo` sono **seed di `80_data`**: su un database ricostruito ci
sono, e pescarle non è il difetto (il difetto lì è `LIMIT 1` senza `ORDER BY`,
che scommette — guida pgTAP). Le relazioni di `anagrafiche` e di `vendite` sono
**vuote da zero**: pescarle è copertura zero, sempre.

⚠️ **Questi numeri sono un superset delle cause misurate in CI** (47 BA, 35
lookup NULL, 29 utente fisso, 7 articolo, ~15 dati di macchina): là è la **prima
causa** di ogni file, qui la **presenza della forma**. Le due misure non si
sommano e non si contraddicono — è la differenza fra «di cosa muore oggi» e
«quanto lavoro contiene».

---

## 3. La forma — `dbops.fn_pgtap_crea_mondo_cliente()`

Un **BB di composizione**: il mondo minimo che un test di dominio pretende, con
la regola d'ordine dentro l'oggetto invece che nella testa di chi scrive.

```sql
dbops.fn_pgtap_crea_mondo_cliente(
    p_etichetta text                                      DEFAULT 'pgTAP',
    p_sigla     anagrafiche.emittenti_fiscali.codice%TYPE DEFAULT NULL
) RETURNS TABLE(
    emittente_fiscale_id, emittente_codice, emittente_soggetto_ruolo_id,
    auth_user_id, identita_id,
    billing_account_id, istanza_utility_id,
    cliente_soggetto_ruolo_id, cliente_soggetto_id, utility_id)
```

Cosa fa, nell'ordine che i file sbagliano:

1. chiede alla GUC che le policy leggono davvero — `app.current_user_id` — se un
   contesto c'è. ⚠️ **Non** a `script.fn_pgtap_emittente_operatore()`, che ha un
   ripiego suo e risponderebbe un emittente anche senza contesto: come
   discriminante sarebbe fail-open;
2. **senza contesto** costruisce azienda + operatore con
   `fn_pgtap_crea_emittente_operatore(p_sigla)` e **apre il contesto** su di lui;
   **con un contesto aperto** riusa l'azienda di chi agisce, e rifiuta `p_sigla`;
3. **poi** crea il cliente con `fn_pgtap_crea_cliente_ba(p_etichetta)`, e senza
   terzo parametro: a contesto aperto il legame lo scrive il trigger `z90` verso
   l'emittente di chi agisce, che a questo punto è quello giusto per costruzione
   (chiederlo anche a mano farebbe sbattere i due su `uq_emittenti_fiscali_ba`);
4. **verifica il legame** prima di tornare: se il BA risulta legato a un'altra
   azienda, solleva invece di consegnare un mondo incoerente;
5. torna gli id, tutti, in una riga.

⚠️ **`p_etichetta` per primo, `p_sigla` dopo** — e lo ha deciso il banco di
prova, non l'estetica: §8.

⭐ **Contratto dichiarato nel `COMMENT`**: esce con i vincoli **IMMEDIATE**, come
ogni helper. Chi vuole la finestra differita la riapre subito dopo con
`SET CONSTRAINTS ALL DEFERRED`, e lo dichiara in testa al file.

⛔ **Perché non basta allargare la riga di contesto**, che sarebbe zero modifiche
ai file: `fn_pgtap_set_contesto_operatore()` è chiamata da **649** file. Costruire
un cliente per tutti cambierebbe il mondo **sotto** i test che i clienti li
contano, e farebbe pagare a ognuno una catena che la maggior parte non usa. Un
mondo si **chiede**: la riga di contesto garantisce *chi agisce*, la composizione
garantisce *su cosa*. Sono due domande diverse, e vanno a due oggetti diversi.

---

## 4. Cosa NON entra nel BB, e perché

Il criterio non è «cosa serve spesso», è **dov'è la trappola d'ordine**:

* ⛔ **il registro di fatturazione**: `script.fn_pgtap_registro_fattura()` si
  semina già da sé dal contesto e crea il registro se manca. Nessuna trappola,
  nessun motivo per duplicarla dentro un altro oggetto;
* ⛔ **l'articolo**: i flag (`gestito_a_magazzino`, `requires_lotto`,
  `requires_serial`) sono **il caso del test**. Un articolo «di default» sarebbe
  la stessa pesca di oggi, scritta meglio;
* ⛔ **i cataloghi seminati** (`config.valute`, `iva`, `stati_doc_*`,
  `tipi_doc_fiscale`, `unita_misura`): non si costruiscono, si **scelgono**. La
  cura lì è un `ORDER BY` su una chiave stabile e una scelta sola per riga
  (guida pgTAP), non un builder;
* ⛔ **due aziende, due clienti, un cliente di un'altra azienda**: sono i casi che
  il test costruisce con i builder atomici, chiamati due volte. Un BB con un
  parametro `quanti` sarebbe un ramo in più per ogni chiamante.

---

## 5. La ricetta per file, e l'ordine dei lotti

La sostituzione, per ogni file che *cerca*:

```sql
-- prima: il blocco refs, da 6 a 40 righe, diverso in ogni file
CREATE TEMP TABLE tmp_xx_refs AS
SELECT (SELECT ba.id FROM anagrafiche.billing_account ba WHERE … LIMIT 1) AS billing_account_id, …

-- dopo: il mondo si chiede, e gli id sono quelli del mondo chiesto
CREATE TEMP TABLE tmp_mondo AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('DASH');
```

⭐ La ricetta **non è nuova**: è quella dei 21 file del 12-09, e
`db/pgtap/script/test-fn-scope-ba-ownership.sql` la porta scritta, con il perché
nei commenti. Quello che cambia è che la composizione smette di essere copiata.

**I lotti, nell'ordine** (rossi a registro per schema, 2026-09-22):

| Lotto | Schemi | File | Perché |
| ----- | ------ | ---- | ------ |
| 1 | `config` 13, `pagamenti` 11, `documenti` 6, `catalogo` 6, `ui` 4, `dbops` 3 | **43** | sei schemi che escono **interi** dal registro: la CI certifica la ricetta su un perimetro chiuso, in una corsa |
| 2 | `anagrafiche` 39, `script` 31 | 70 | è dove sta il mondo: le fixture che costruiscono male qui rompono a cascata altrove |
| 3 | `pratiche` 37 | 37 | già quasi tutto verde nella simulazione del 20-09 |
| 4 | `vendite` 211 | 211 | a famiglie (dash, resi, fatture, ddt, preventivi), un lotto per famiglia |

⚠️ **Ogni lotto finisce in CI, non sullo scratch**: le righe rientrate le toglie
`scripts/pgtap-baseline-ci-rientrati.sh` leggendo il **log della corsa**, e il log
scade — va lanciato **il giorno stesso** della push su `Tito-dev`. Un lotto
provato e non certificato lascia il registro dov'era.

---

## 6. Il verso del registro (D11): il cancello che impedisce di risalire

Un registro che cala mentre qualcuno ci lavora e risale quando smette non è un
registro: è una fotografia. Il cancello che gli dà un verso sta dove stanno già
gli altri, `scripts/guardrail_pgtap_preambolo.py`: **un file pgTAP che pesca in
`anagrafiche.*` o in `vendite.*` con `LIMIT 1` senza passare da un builder** è
rosso, con una soglia che **può solo calare**, come
`SOGLIA_THROWS_SENZA_DISCRIMINANTE`.

⚠️ **Da disegnare con cura, e la lezione è del 21-09**: un criterio testuale conta
le scritture che **vede**, e una scrittura che passa per una funzione è
invisibile (il censimento dei differiti ne mancò uno proprio così). Quindi il
cancello o guarda anche le chiamate a `fn_crea_*`/`fn_pgtap_crea_*`, o **dichiara
di non vederle** — nel messaggio, non in un commento.

---

## 7. Decisioni aperte per Tid

| # | Decisione | Raccomandata |
| - | --------- | ------------ |
| 1 | Il BB **apre il contesto** o lo lascia al file? | ✅ **deciso il 22-09: lo apre**: è la regola d'ordine, ed è il motivo per cui il BB esiste. Chi vuole costruire prima e aprire dopo (i sei `*-satelliti.sql`, da owner) continua coi builder atomici |
| 2 | Il **registro** dentro o fuori dal BB? | ✅ **deciso il 22-09: fuori** (§4): `fn_pgtap_registro_fattura()` si semina già dal contesto |
| 3 | Da quale **lotto** si parte? | ✅ **lotto 1**, 43 file su sei schemi che escono interi dal registro |
| 4 | Il **cancello** di §6 adesso o dopo il primo lotto? | ✅ **dopo**: la soglia si prende su un perimetro già sanato, altrimenti nasce grande e nessuno la guarda |
| 5 | I file che **committano** / col contesto in autocommit | ✅ **decisa il 23-09: si chiude tutto nel lotto 2**, e il censimento vero era 6 + 8 (§11). Oggi nella suite non committa più nessuno |
| 6 | I **9 file di `pagamenti`** chiedono tutti una **fattura** (scadenza, movimenti, conti): un secondo BB di composizione, o nove copie della stessa catena? | ✅ **deciso il 23-09: un BB** — anzi due, perché la filiale bancaria è la stessa storia (`20260923-04` e `-05`). I nove file sono chiusi, §10 |
| 7 | Il ramo specifico «ultimo SUPER_ADMIN» sull'**identità** è raggiungibile, o è codice morto? (§10, punto 1) | 🔵 da guardare: oggi a rifiutare è sempre il guard generico delle figlie, che scatta prima |
| 8 | `storico.parameters` da zero ha `parameter_id`, il trigger passa `parameters_id` (§10, punto 2) | 🔵 changeSet, non fixture: su un'installazione nuova ogni UPDATE su `config.parameters` fallisce |

---

## 8. Le prove — fatte il 2026-09-22, in transazione ritirata

Tutte con l'**SQL estratto** dallo YAML (`yaml.safe_load`, mai riscritto a mano),
in `BEGIN … ROLLBACK` sullo scratch `zeroerp_ci` — il database ricostruito da
zero, cioè lo stesso metro della CI — come **proprietario**:

| Prova | Esito |
| ----- | ----- |
| `plpgsql_check` sul corpo | **pulito** |
| **ramo A** (nessun contesto): costruisce azienda + operatore, apre il contesto, crea il cliente | ✅ `PGTR0002`, contesto su `auth_user_id` tornato, veste `OPERATORE` |
| il legame BA → emittente punta all'azienda del mondo | ✅ |
| l'operatore ha quell'emittente in `config.user_emittenti_fiscali` | ✅ |
| **ramo B** (contesto aperto): stessa azienda, stesso operatore, cliente nuovo | ✅ |
| guard `p_sigla` a contesto aperto / guard «operatore senza emittente» | ✅ sollevano entrambi, col messaggio che rimanda ai builder atomici |
| presidio `test-fn-pgtap-crea-mondo-cliente-v1.sql` | **9/9** |
| presidio trasversale `dbops/test-riferimenti-morti-v1.sql`, con la funzione nuova in transazione | **9/9** (t.8 `SKIP`, com'è da owner) |
| presidio trasversale `script/test-rubinetto-primo-motivo-v1.sql` | **7/7** |
| i sette cancelli statici (`runOnChange`, letterali SQL, preCondition su `80_data`, DDL su trigger di automazione, GRANT ai ruoli batch, timestamp senza fuso, licenze) | ✅ |
| `guardrail_pgtap_preambolo.py` su 682 file | ✅ invarianti rispettate, debito `throws_ok` **invariato a 123** (il presidio usa `throws_like`) |

⚠️ **Le assunzioni del ramo B lette sul vivo di dbdev** (come `zeroerp_app`, sola
lettura): l'operatore che la riga di contesto sceglie risolve **un** emittente e
**una** identità `OPERATORE` attiva, e gli operatori con emittente ma senza
identità attiva sono **zero**. ⇒ il guard non può scattare a vuoto sulla
macchina di sviluppo.

⛔ **Cosa queste prove NON dicono**, e va scritto: girano da **proprietario**,
perché su dbdev lo schema `dbops` è di `titodb` e la funzione, dentro una
transazione, non esiste per nessun'altra sessione. Il verso **RLS** — la stessa
chiamata come `zeroerp_app` — si misura **dopo l'apply**. ⛔ Le migrazioni le
applica Tid; l'autogen changelog lo rigenera il wrapper al primo `db-migrate`,
non si tocca a mano.

⚠️ **Un difetto trovato dal banco, e vale la riga**: la prima stesura aveva
`p_sigla` come primo parametro, e la prima chiamata scritta a mano —
`fn_pgtap_crea_mondo_cliente('secondo cliente')` — è finita nella **sigla**. Col
contesto aperto il guard ha sollevato; senza, avrebbe provato a creare
un'azienda con quel codice e sarebbe morta su `chk_emittenti_fiscali_codice_forma`,
tre passi più in là dalla causa. ⇒ `p_etichetta` per primo: il parametro che il
chiamante scrive sempre non può stare dietro a quello raro.

---

## 9. Cosa resta

* ✅ **Lotto 1 chiuso e applicato** il 23-09 (§10). ⏳ Resta la **corsa CI** che
  certifica i rientrati e abbassa il registro: `pgtap-baseline-ci-rientrati.sh`
  legge il log della corsa, e il log scade — va lanciato il giorno stesso;
* ✏️ **il lotto 2 è in corso** (§11): il debito dei `COMMIT`/autocommit è chiuso,
  12 file su 70 sono verdi sul mondo vuoto. Restano le famiglie del cliente da
  costruire, `pdp_id`, `RIS_UMANA`, i registri e l'utente di sessione fissato;
* i 28 file che fissano `app.current_user_id = '1'`: non li tocca il BB, è una
  ricetta a sé (l'utente di sessione è quello del mondo costruito);
* i 7 file legati a dati di **questa macchina**: o si riscrivono, o si dichiarano
  test di macchina — è una decisione, non un lavoro;
* i 109 file con `pgtap-runner: owner`: quanti di quei motivi siano ancora veri
  dopo la rev `20260912-38` **non è misurato**, e non è questo cantiere.

---

## 10. Lotto 1 — stato al 2026-09-23

⚠️ **Prima misura, e ridimensiona il lotto.** Rieseguiti i 43 file su
`zeroerp_ci` come `zeroerp_app` dopo l'apply del `20260920-01`: **16 erano già
verdi**. Non è lavoro fatto oggi — è il registro che non è stato aggiornato
dalla corsa del 21-09, e sono candidati RIENTRATI da togliere con
`pgtap-baseline-ci-rientrati.sh`. Il lavoro vero del lotto era **27 file**.

### ✅ Riscritti e verdi (12), su `zeroerp_ci` **e** su dbdev

| File | Era | È |
| ---- | --- | -- |
| `catalogo/test-fn-get-uom` | pescava `ART_TEST_*` e asseriva fattori (6, 2, 0.25) di righe che esistono solo qui; in CI `unita_misura_conversioni` è vuota | costruisce due articoli e **scrive le conversioni** coi fattori che dichiara; +2 asserzioni sul ramo `attivo=false`, che nessuno percorreva |
| `catalogo/test-articoli-componenti-immutabilita` | `ART_TEST_*` | due articoli costruiti (18/18) |
| `catalogo/test-vw-articoli-componenti-dettaglio-capabilities-v1` | `ART_TEST_*` | idem (12/12) |
| `catalogo/test-vw-articoli-dettaglio-bom-capability-v1` | `ART_TEST_*` | idem (7/7) |
| `catalogo/test-vw-articoli-note` | `ART_TEST_BASE` → nota con `target_id` NULL | articolo costruito (7/7) |
| `catalogo/test-vw-articoli-uom-operativa-dettaglio-capability-v1` | `ART_TEST_BASE` + «pulizia preventiva» delle righe del seed | articolo costruito: la riga base **c'è già** (la scrive un trigger), la pulizia sparisce (6/6) |
| `ui/test-fn-resolve-dashboard-config` | pescava un `billing_account` → identità senza riga → «binding non coerente col tipo del profilo» | BB del mondo, **e la sessione torna senza veste** com'è dichiarato in testa al file (12/12) |
| `ui/test-fn-resolve-lista-config` | idem | BB del mondo (13/13) |
| `ui/test-fn-resolve-lista-config-contatore-colonne-nuove-v1` | «il primo utente con un profilo applicabile» → in CI **zero** utenti ne hanno uno | profilo AD_HOC + binding costruiti sull'operatore di contesto (5/5) |
| `config/test-stati-doc-fiscale-congela-fiscale` | cercava una coppia (emittente, utility) configurata | BB del mondo + la riga di configurazione scritta dalla fixture (7/7) |
| `config/test-permessi-user-overrides` | «il primo utente attivo», che in CI è l'operatore tecnico e un emittente ce l'ha già | un utente **nuovo**, che è il soggetto vero del file (18/18) |
| `dbops/test-fn-apply-chiusura-scadenze-v1` | **clonava** listino e contratto da righe esistenti: in CI le INSERT … SELECT scrivevano zero righe e i due test rispondevano `NULL` | listino e contratto costruiti sul mondo (6/6) |
| `config/test-profili-accesso-guard-ultimo-super-admin` | cercava identità OPERATORE «vergini» | ogni scenario costruisce la sua azienda+operatore, e il SUPER_ADMIN «preesistente» si costruisce (3/3) |

### ⭐ Tre cose trovate per strada

1. ⛔ **Un test verde per l'errore sbagliato**, e l'ha scoperto il discriminante:
   `config/test-profili-accesso-guard-ultimo-super-admin` t.3 dichiarava
   `E_PROFILO_ULTIMO_SUPER_ADMIN`, ma a rifiutare è il guard **generico** delle
   figlie (`trgfn_prevent_deactivate_if_children`), che scatta prima su
   qualunque identità con un binding attivo. Col `throws_ok(sql, NULL, NULL)` il
   file era verde comunque. ⇒ L'asserzione ora pinna il **rifiuto con errore di
   dominio** (che regge anche dopo un'eventuale riparazione) e un `diag()`
   registra chi parla oggi. 🔵 **Da decidere**: il ramo specifico
   sull'identità è raggiungibile, o è codice morto?
2. ⛔ **Un difetto del database da zero, non della fixture.**
   `config/test-parameter-fk-surrogate-dispatch-v1` e `-vuoto-v1` sono **verdi su
   dbdev e rossi in CI** con `E_SNAPSHOT_CLOSE_ERROR: la colonna "parameters_id"
   non esiste`: su `zeroerp_ci` la shadow `storico.parameters` ha la colonna
   **`parameter_id`**, mentre il trigger `trgfn_storico_generic` riceve
   `'parameters_id'` su entrambi i database. ⇒ Su un'installazione nuova
   **ogni UPDATE/DELETE su `config.parameters` fallisce**. Stessa famiglia del
   caso `tipi_ruoli.entita_tabella` del 21-09; il rimedio è un changeSet, non
   una fixture. ⚠️ Un censimento «argomento del trigger vs colonna della
   shadow» dà **quattro falsi positivi su entrambi i database**
   (`comuni`, `indirizzi`, `indirizzi_dettaglio`,
   `catasto_unita_immobiliari`: l'UPDATE lì riesce) — quindi non è un presidio
   così com'è scritto, ed è una lente, non un criterio.
3. ⚠️ **`config/test-fn-email-sistema` è rosso anche su dbdev** (5 asserzioni):
   non è un file che «cerca invece di costruire», è un rosso che il registro
   della CI nasconde dietro l'etichetta. Fuori dal lotto 1: va guardato per
   quello che è.

### ✅ `pagamenti` — chiuso il 2026-09-23 con due BB nuovi

Decisione presa (§7 #6): **un BB**, non nove copie. I nove file sono riscritti e
verdi sul database da zero.

| ChangeSet | Che cosa compone | Perché un oggetto e non una copia |
| --------- | ---------------- | --------------------------------- |
| `20260923-04` `fn_pgtap_crea_fattura` | mondo → coppia (emittente, utility) → registro coerente → testata nello stato scelto | **quattro anelli d'ordine**: il cliente si lega a chi agisce, la coppia va configurata, il registro dipende dall'azienda, la valuta si risolve lungo «cliente → azienda → gestore». Il terzo parametro è il BA di una fattura già fatta: la **seconda fattura dello stesso cliente**, che tre file volevano e nessuno poteva scrivere |
| `20260923-05` `fn_pgtap_crea_filiale_bancaria` | soggetto della banca → ruolo BANK_B → filiale | `anagrafiche.bank_branches` è **dato di macchina**: da zero è vuota. Tre file morivano sul NOT NULL di `bank_branch_id`, e la catena è una saga con la sua finestra differita |

| File | Era | È |
| ---- | --- | -- |
| `test-vendite-contabili-stato-obbligatorio` | «la prima fattura con un BA» → NULL | fattura costruita (7/7) |
| `test-vendite-movimenti-contabile-riga` | costruiva la fattura ma **pescava i mattoni**: il ramo `ins` inseriva zero righe per via dei suoi stessi `IS NOT NULL` | il BB (8/8) |
| `test-righe-contabili-guard-dati` | il caso «riga ABBINATA **con** fattura e cliente» sbatteva contro il guard che pretende quei due dati: il rosso diceva il vero sul prodotto e il falso su se stesso | fattura costruita (7/7) |
| `test-fn-crea-distinta-correzione` | derivava l'emittente con un `OR is_default IS TRUE` — il ripiego che su un BA senza legame risponde **un'altra azienda** (difetto di D13) | il BB, che il legame lo verifica (15/15) |
| `test-sistemazione-annullo-riporto` | due fatture scritte a mano su mattoni pescati | due fatture, la seconda col terzo parametro (13/13) |
| `test-sistemazioni-registro` | cercava «un cliente con almeno due fatture» con una `GROUP BY … HAVING count(*) >= 2` | tre fatture costruite: la coppia è tale **per costruzione** (12/12) |
| `test-sistemazioni-giro-completo` | idem, più la filiale pescata | due fatture + filiale costruite (14/14) |
| `test-enti-incasso-conto-incasso` | filiale pescata, e un soggetto-ruolo «qualunque» che da zero era **proprio quello dell'azienda del contesto**: il caso negativo diventava positivo in silenzio | filiale costruita, e il ruolo è quello della banca (7/7) |
| `test-enti-incasso-psp` | filiale pescata, titolare = «il primo emittente attivo» | filiale costruita, titolare = l'emittente di chi agisce (12/12) |

⭐ **La lezione del giro, e costa un giro di rosso a chi non la sa**: i due
database si migrano **separatamente**. Il 23-09, con `20260923-04/-05`
applicati su dbdev e lo scratch fermo al `-03` delle 09:36, i nove file più il
presidio della fattura erano rossi **solo su `zeroerp_ci`**, con «la funzione
`dbops.fn_pgtap_crea_fattura(unknown)` non esiste» — non un difetto delle
fixture, il database indietro. ⚠️ E la conseguenza vera è sul registro: una
baseline lanciata sullo scratch **prima** del suo migrate avrebbe scritto quei
dieci in `baseline-rossi-ci.tsv` come debito nuovo, debito che non è. ✅ Chiusa
col migrate dello scratch (Tid, 23-09): nessuno dei dieci è mai entrato nel
registro.

✅ **Le prove, e in che ordine sono arrivate.** Prima dell'apply: SQL estratto
dei changeSet in testa a ogni file, in transazione ritirata su `zeroerp_ci`,
**da owner** — su dbdev lo schema `dbops` è di `titodb`, e una funzione dentro
una transazione non esiste per nessun'altra sessione. Dopo l'apply su dbdev:
i nove più i due presidi come `zeroerp_app`, **112 asserzioni verdi, zero
rosse**. Dopo il migrate dello scratch: nessuna regressione (Tid).

### ⏳ Cosa NON è entrato nel lotto 1, e perché

Tre file restano rossi sul database da zero, e nessuno dei tre per una fixture
che cerca invece di costruire. Sono dichiarati, non dimenticati:

* `ui/test-lista-competenza-gruppi-colonna-emittente-v1`: il suo t.7 è il guard
  «il t.6 non è verde per sottrazione», e su un database senza documenti **dice
  il vero** — il file non ha materia da giudicare. Rientra quando il lotto
  `vendite` gli costruisce un documento;
* i due `parameter-fk-surrogate-*`: aspettano il changeSet di `storico.parameters`
  (§10, punto 2). È un difetto del prodotto sul database da zero, non del test;
* `config/test-fn-email-sistema` è rosso **anche su dbdev** (5 asserzioni): va
  guardato per quello che è, e non è questo cantiere.

### ⭐ Un changeSet nato dal lotto

`20_code/dbops/20260923-01-update-fn-pgtap-crea-articolo-uom-scelta`: il builder
degli articoli prende un quinto parametro **`p_uom_id`** (in coda, con default:
le 23 fixture che lo chiamano non cambiano di una riga). Serve a chi misura le
**conversioni**, che il guard ammette solo fra unità della stessa tipologia — e
`articoli.uom_id` è una colonna loccata, quindi la base si sceglie alla nascita
o non si sceglie più. DROP + CREATE, perché un parametro in più sarebbe un
overload ambiguo. Provato con l'SQL estratto in transazione ritirata:
`plpgsql_check` pulito, `test-fn-get-uom` 9/9.

⭐ E la soglia del cancello: `SOGLIA_THROWS_SENZA_DISCRIMINANTE` **123 → 121**,
perché due `throws_ok(sql, NULL, NULL)` del file dei super admin hanno preso il
loro discriminante (uno dei due ha scoperto il punto 1).

---

## 11. Lotto 2 (`anagrafiche` 39 + `script` 31) — in corso dal 2026-09-23

### ✅ Il debito dei `COMMIT` è chiuso, e ora si sa quanto pesava

Decisione di Tid (23-09): **chiudere tutto in questo lotto**, non solo i file che
si vedono. ⭐ E il censimento andava rifatto: erano **6 file che committano** e
**8 col contesto in autocommit**, non 4 e 6. ⚠️ Due però erano falsi positivi del
mio criterio — un `COMMIT` dentro un `throws_ok` e menzioni in commento: il mio
non mascherava i dollar-quote, quello di `guardrail_pgtap_preambolo.py` sì. I
file veri erano **sei**, tutti in `anagrafiche`.

⛔ **Quanto pesava, misurato.** Simulando il database vuoto — l'identità
dell'operatore residuo spenta, così la riga di contesto percorre il ramo che
costruisce — **sei file del lotto cambiano esito**: tre da verdi a rossi in
fixture, tre da «asserzione rossa» a fixture. Erano verdi grazie alla `PGTR0001`
che i file in autocommit committavano all'inizio della corsa. ⇒ Il debito non era
di sei file: era di sei file **più tutto quello che nascondevano**.

✅ **Oggi nella suite non committa più nessuno** (censito sui 683 file, con i
dollar-quote mascherati).

| File | Che cosa è cambiato |
| ---- | ------------------- |
| `create-gestore-conto-soggetto`, `create-gestore-conto-bancario`, `test_fn_get_conto_bancario_predefinito`, `test_vw_conti_bancari_per_ruolo_gestore` | erano test travestiti da script di setup: transazione aperta tardi, contesto in autocommit, chiusura in `COMMIT`. Ora transazione subito, contesto dentro, `ROLLBACK`, e gestore + filiale **costruiti** (4/4, 6/6, 6/6, 5/5) |
| `test-soggetti-indirizzi-required`, `test-soggetti-ruoli-indirizzi-required` | multi-transazione **per disegno** (ogni caso collauda un guard `DEFERRABLE`): la riga di contesto è scesa **dentro ogni caso**, con la finestra differita riaperta e dichiarata, e il `commit;` finale è diventato `ROLLBACK` (9/9 e 6/6, sul mondo vuoto **e** su dev) |

### ⭐ Un builder nuovo, e la ragione per cui non costruisce sempre

`20_code/dbops/20260923-06-create-fn-pgtap-crea-gestore` — **applicato il 23-09,
nessuna regressione**. `anagrafiche.gestori` è dato di macchina, ma è anche un
**singleton**: un secondo gestore lo rifiuta un guard. ⇒ La funzione **prende**
quello che c'è (dbdev) e **costruisce** solo se non c'è (CI). Un builder che
creasse sempre sarebbe rosso proprio sulla macchina dove oggi il test è verde.

⚠️ Trovato per strada: il vincolo che porta il nome del singleton —
`uq_gestori_singleton`, `EXCLUDE USING gist (id WITH =) WHERE id IS NOT NULL` —
vieta due righe con lo **stesso id**, cioè ripete la primary key. A impedire il
secondo gestore è il guard. Il nome promette ciò che la definizione non fa: §4-bis
della guida sui presidi. Non cambia niente nel comportamento, ma chi cercasse il
vincolo lo troverebbe e si fiderebbe.

### ⛔ «Libera» vuol dire «libera ADESSO» — e sono stati due rossi

`dbops.fn_pgtap_piva_libera()` risponde la prima partita IVA non ancora usata **in
quell'istante**. Non è un generatore: finché nessuno scrive quel soggetto, la
chiamata dopo risponde **lo stesso numero** — anche in un'altra istruzione
(misurato). ⇒ `test-soggetti-indirizzi-required` ne chiedeva due in testa al file
e ne otteneva una sola, e soprattutto le chiedeva **prima** che il mondo esistesse:
la riga di contesto, costruendo l'azienda, si prendeva proprio quella, e il
soggetto del test collideva con il soggetto dell'azienda. Ora ogni caso chiede la
sua, dopo. Regola scritta nella guida pgTAP.

### ⛔ E l'emittente non si pesca, si deriva

Sette file di `script/` prendevano «il primo emittente attivo» — mentre il loro
stesso commento citava `script.fn_pgtap_emittente_operatore()` come il modo
giusto. Con una sola azienda a catalogo i due coincidevano per caso; col mondo
costruito dalla riga di contesto no, e il risultato era «Accesso negato per scope
emittente fiscale». Sostituiti.

### ⚠️ Il banco di prova mente sui file multi-transazione

Il banco che simula il database vuoto avvolge il file in una transazione esterna.
Un file multi-transazione, al suo **primo `ROLLBACK`**, chiude anche quella — e si
porta via le temp table create prima. ⇒ Quei file si misurano **senza banco**,
spegnendo e riaccendendo l'identità residua attorno alla corsa.

⚠️ **E la misura ha lasciato un residuo, che va dichiarato**: le corse fatte
quando i quattro file committavano ancora hanno committato **4 emittenti `PGTR*`**
su `zeroerp_ci` (stessa natura di quelli che lo script di pulizia già conosce, da
lanciare da Tid). Il ripristino delle identità è stato prima troppo largo e poi
corretto: sullo scratch resta **una** identità attiva, com'era.

### ⏳ Stato al 2026-09-23 (mondo vuoto, 70 file)

| | |
| --- | --- |
| verdi | **12** |
| muoiono in fixture | 34 |
| asserzioni rosse | 20 |
| attendevano l'apply del `-06` | 4, ora applicato |

Le famiglie che restano: il **cliente da costruire** (`istanze_utilities` e
`billing_account` a zero, 5 + n file), `pdp_id` (3), `RIS_UMANA` (2), i registri di
fatturazione (2), l'utente di sessione fissato a `'1'` (3 nel lotto), e una coda
di casi singoli.

### ✏️ Ripresa del 2026-09-23 pomeriggio — la famiglia del cliente

**Rimisura di partenza** (stesso banco, `zeroerp_ci` come `zeroerp_app`, identità
residua spenta): **16 verdi** — i quattro in attesa del `-06` sono passati —, 34
in fixture, 20 in asserzione.

**I cinque file che morivano su `istanze_utilities.soggetto_id` NULL**, cioè che
pescavano soggetto, ruolo e utility «da un billing account esistente»:

| File | Com'è adesso | zeroerp_ci | dbdev |
| ---- | ------------ | ---------- | ----- |
| `test-ba-cambio-emittente-storia-v1` | il BA del mondo **è** il caso (un BA appena nato); l'«altro emittente» è un emittente **costruito** (`fn_pgtap_crea_emittente`), non «un soggetto_ruolo qualunque» | ✅ 14/14 | ✅ |
| `test-ba-storia-solo-numerati-v1` | idem, e l'articolo si costruisce non gestito (il caso è la numerazione del DDT, non il suo movimento) | ✅ 7/7 | ✅ |
| `test-billing-account-guard-parent` | soggetto del mondo + articolo costruito | ✅ 7/7 | ✅ |
| `test-billing-account-guard-cf-confrontabile-v1` | due clienti costruiti, e il **BA fuori perimetro del t.5 si costruisce** (cliente di un'altra azienda, costruito agendo per un attimo come il suo operatore): il ramo `skip` è sparito | ⏳ `20260923-07` | ⏳ |
| `test-guard-albero-ba-omogeneo-v1` | mondo + secondo emittente costruito + **super admin umano senza azienda**; anche qui il ramo `skip` del t.5 è sparito | ⏳ `20260923-08` | ⏳ |

I cleanup fuori transazione dei primi due file sono stati tolti: cancellavano
righe con codici che il file non scrive più, e nessuna riga del file sopravvive
al `ROLLBACK`.

#### ⛔ Due difetti trovati per strada, due changeSet (da applicare)

1. **`20260923-07` — il codice «libero» di `fn_pgtap_crea_cliente_ba` si leggeva
   sotto la RLS.** Il prossimo `PGTAPBAnnnnn` era `max(codice)+1` su
   `billing_account`, che è in RLS: il massimo era quello dei BA **di chi
   agisce**. Il cliente di una seconda azienda nella stessa transazione ripartiva
   da `PGTAPBA00001` e moriva su `uq_istanze_utilities_codice`. Misurato come
   `zeroerp_app`: sotto il secondo operatore la lettura vecchia risponde `NULL`,
   la nuova (su `istanze_utilities`, fuori RLS, stesso codice del BA) risponde
   `PGTAPBA00001` già usato. È la trappola di «libera vuol dire libera ADESSO»
   un gradino sotto: *libero vuol dire libero per TUTTI, e sotto RLS «tutti» è
   chi agisce*.
2. **`20260923-08` — `dbops.fn_pgtap_crea_operatore_umano(p_etichetta,
   p_super_admin)`**, builder nuovo. Un super admin **ha** un'azienda se lo si
   costruisce come utente tecnico (`fn_pgtap_crea_emittente_operatore`), e non
   è un dettaglio: `script.fn_get_ba_emittente_sr_id` fa ricadere un BA senza
   legame sull'emittente di **chi agisce** prima che sul gestore globale, quindi
   il t.10 dell'albero si spaccava un passo prima della sua scena. Il super admin
   di dbdev infatti non ha righe in `user_emittenti_fiscali` (multi-emittente per
   modello), e togliergliela dopo non si può: il guard la ammette solo dentro la
   disattivazione dell'utente. ⇒ Il builder chiama la **madre di produzione**
   `anagrafiche.fn_crea_operatore_v2` dentro la finestra differita (il guard
   degli indirizzi del soggetto PF è `DEFERRABLE` e gli indirizzi arrivano
   all'ultimo passo), con CF e username liberi. Nasce **senza azienda**; per
   legarlo c'è già il verbo `script.fn_change_user_emittenti_scope`.
   Regola del 2: tre consumatori nel lotto (l'albero, `test-fn-get-soggetto-dati-and-user-profile`
   che vuole un operatore con risorsa umana, `test-fn-get-user-profile-guc-aware`
   che usava l'utente 1).

**Le prove dei due changeSet.** SQL estratto dallo YAML, in transazione
ritirata su `zeroerp_ci` **da owner** (`db/internal.ci.env`): `plpgsql_check`
pulito su entrambi; `-08` costruisce super admin (✅ `fn_is_super_admin`, zero
righe in `user_emittenti_fiscali`) e operatore semplice. ⚠️ Da owner la RLS non
c'è, quindi il verso RLS si è misurato così: per `-07` l'espressione nuova
eseguita come `zeroerp_app` sotto il secondo operatore; per `-08` una copia della
funzione in `pg_temp` (sostituzione **meccanica** del nome di schema sull'SQL
estratto) e il file dell'albero girato come `zeroerp_app` — **12/12 su
`zeroerp_ci` e 12/12 su dbdev**. La prova vera resta la corsa dopo l'apply.

⚠️ **Una misura falsa, e va scritta**: la prima verifica di `-08` dava il super
admin **non** super admin. Era la prova: `fn_is_super_admin` è `STABLE` e,
chiamata nella **stessa istruzione** del builder, legge la snapshot di prima.
In un'istruzione separata risponde `true`.

#### L'operatore umano e la famiglia `RIS_UMANA`

| File | Com'era | Com'è | zeroerp_ci | dbdev |
| ---- | ------- | ----- | ---------- | ----- |
| `script/test-fn-get-soggetto-dati-and-user-profile` | «il primo operatore con risorsa umana attiva», e il t.12 pescava «un soggetto senza dati societari» | operatore umano costruito; il t.12 usa la **sua** persona fisica, che dati societari non ne ha per costruzione | ⏳ `-08` (26/26 via `pg_temp`) | ⏳ (26/26) |
| `script/test-fn-get-user-profile-guc-aware` | l'**utente 1** («tid») e «un SR-CL libero» con due rami `skip` | operatore umano + due clienti costruiti; i due `skip` spariti; il t.4 ha preso il suo discriminante (`throws_ok(sql, NULL, NULL)` → frase) | ⏳ `-08` (4/4) | ⏳ (4/4) |
| `anagrafiche/test-notify-cambio-reparto` | il soggetto del **gestore** (persona giuridica, dato di macchina) con un ruolo `RIS_UMANA` dato a mano | la risorsa umana dell'operatore costruito, **col suo ponte verso l'utente** — che è ciò che il NOTIFY porta | ⏳ `-08` (10/10) | ⏳ (10/10) |
| `anagrafiche/test-risorse-umane` | il CF e la partita IVA di **questa macchina** | una persona fisica costruita dalle madri di produzione (`fn_crea_soggetto_pf` + `fn_crea_indirizzo_soggetto`, nella finestra differita) **senza** risorsa umana — inserirla è il caso del test; prima occorrenza, quindi sul posto e non in un builder | ✅ 8/8 | ✅ 8/8 |

⚠️ **Una trappola che ha morso due volte in un'ora**, ed è scritta nel `COMMENT`
del builder: ciò che il builder scrive si legge in un'**istruzione separata**.
Un `JOIN` su `risorse_umane` nella stessa istruzione della chiamata faceva
nascere la temp table **vuota** (snapshot di prima), come la
`fn_is_super_admin` `STABLE` della prova.

⛔ **Un `CHECK` che oggi non può parlare, su dodici tabelle** (trovato da
`test-risorse-umane` t.6, la prima volta che il fixture arrivava fin lì da zero:
su dbdev il file moriva prima, perché il soggetto «di macchina» la risorsa umana
ce l'ha già). Il `CHECK` sulle date (`valido_al IS NULL OR valido_al >=
valido_dal`, in alcune tabelle con anche `valido_dal IS NULL`) e la colonna
`validita`, `GENERATED STORED` su `daterange(COALESCE(valido_dal,'-infinity'),
COALESCE(valido_al,'infinity'), '[]')`, stanno insieme su **12 tabelle**
(lettura di struttura: stesse due definizioni su tutte e dodici). PostgreSQL
calcola la colonna generata **prima** dei `CHECK`, e il `daterange` con il limite
inferiore oltre il superiore **solleva** (`22000`, «il limite inferiore
dell'intervallo dev'essere minore o uguale…»). ⇒ In **ogni** caso in cui il
`CHECK` fallirebbe — entrambe le date presenti e invertite — rifiuta prima il
`daterange`; negli altri il `CHECK` passa. Oggi il `CHECK` non scatta mai.

⚠️ **Questo non lo rende inutile** — nel primo resoconto l'avevo chiamato così,
ed era sbagliato. È la regola **dichiarata**, leggibile nel catalogo e nella doc,
e la sola difesa che resta se un giorno l'espressione di `validita` cambia o la
colonna sparisce: allora torna a parlare lui. Toglierlo toglierebbe la regola
scritta e lascerebbe quella implicita in un effetto collaterale del tipo.
Il difetto vero è un altro: **cosa legge l'operatore** — la frase tecnica del
`daterange`, non un errore di dominio. 🔵 Da decidere, non in questo cantiere:
un guard `BEFORE ROW` sulle date (i `BEFORE` girano **prima** del calcolo delle
colonne generate, linee-guida-sql §7b) con un codice di dominio registrato,
tenendo il `CHECK` come ultima difesa. Il test ora asserisce la **regola**
(respinta da uno dei due presìdi) e il `diag` registra chi parla, così regge
anche il giorno in cui quel guard esisterà.

#### La famiglia `pdp_id` — terzo builder, `20260923-09` `fn_pgtap_crea_pdp`

`anagrafiche.pdp` è dato di macchina. Cinque file volevano un PDP: tre lo
pescavano e morivano su «Non è stato fornito un valore per pdp_id»
(`fn_subentro_cliente`), uno sulle precondizioni, e il quinto
(`test-istanza-cliente-chain`) se lo **costruiva già a mano**, su uno stradario
cablato (`stradario_id = 4`). Regola del 2: builder, e la copia di `chain` si
ritira nello stesso giro.

⚠️ **La trappola che il builder porta dentro**: un PDP ha due unicità,
`uq_pdp_codice` e `uq_pdp_addr_utility` (un indirizzo, un PDP per utility). E
`dbops.fn_pgtap_crea_indirizzo_dettaglio` è **idempotente sull'etichetta**, che
entra **troncata a 10 caratteri** in `interno`: due PDP chiesti con etichette che
iniziano uguali finirebbero sullo stesso indirizzo. ⇒ Il builder sceglie **un**
numero libero e da lui deriva sia il codice (`PGTAPPDPnnnnnn`) sia l'etichetta
corta dell'indirizzo (`PDPnnnnnn`, sta intera nei 10). Provato da owner: tre
chiamate, tre codici e tre indirizzi distinti; guard su utility inesistente.

| File | zeroerp_ci | dbdev |
| ---- | ---------- | ----- |
| `anagrafiche/test-clienti-sync-utility-pdp-policy` (+ soggetto costruito al posto della partita IVA di macchina) | ⏳ `-09` (14/14 via `pg_temp`) | ⏳ (14/14) |
| `anagrafiche/test-simula-subentro` (PDP `GAS-PDP-0002` e due partite IVA di macchina) | ⏳ (26/26) | ⏳ (26/26) |
| `script/test-fn-disdetta-cliente` (PDP e soggetto pescati) | ⏳ (12/12) | ⏳ (12/12) |
| `anagrafiche/test-create-istanza-from-pdp` (PDP pescato + soggetto `TST-PR-001` di macchina) | ⏳ (9/9) | ⏳ (9/9) |
| `anagrafiche/test-istanza-cliente-chain` (copia a mano ritirata + due partite IVA di macchina) | ⏳ (26/26) | ⏳ (26/26) |

⚠️ `chain` contava anche sulla finestra differita **di default** dopo la riga di
contesto (il suo commento lo diceva: «non è qui, è più sotto»): con i builder
che escono `IMMEDIATE` l'istanza base moriva sul guard dei satelliti. La finestra
ora si riapre **dichiarandola**, come vuole la guida.

#### I registri di fatturazione e l'utente fissato a `'1'`

| File | Com'era | Com'è | zeroerp_ci | dbdev |
| ---- | ------- | ----- | ---------- | ----- |
| `anagrafiche/test-soggetti-titoli-iva` | fattura scritta a mano su mattoni pescati (registro con emittente `NULL` da zero); titolare del titolo = «il primo soggetto attivo», cioè da zero **l'azienda stessa** | titolare = il cliente del mondo, e la fattura la costruisce `fn_pgtap_crea_fattura` **sul suo BA** (terzo parametro): titolo e fattura parlano dello stesso cliente | ✅ 23/23 | ✅ 23/23 |
| `anagrafiche/test-soggetti-titoli-iva-due-emittenti` (runner owner, dichiarato) | i due emittenti nascevano promuovendo a EF «i primi due soggetti attivi»; fattura come sopra | due emittenti da `fn_pgtap_crea_emittente`, titolare costruito, fattura dal builder | ✅ 5/5 da owner | ✅ 5/5 da owner |
| `anagrafiche/test-stiva-movimenti-annullo-v1` | `SET LOCAL app.current_user_id = '1'` **sovrascriveva** il contesto appena aperto (su dbdev è il super admin, cioè il perimetro che vede tutto; in CI non esiste); titolari = «i primi due soggetti»; il t.3 «costruito, non cercato» pescava «la prima fattura» | sovrascrittura tolta; due clienti costruiti; fattura costruita sul BA del titolare del titolo 2. Il t.11 (la prova del `SECURITY DEFINER`) gira davvero, non nel ramo `skip` | ✅ 12/12 | ✅ 12/12 |

⚠️ **Due trappole del banco, entrambe di snapshot o di planner**: un
`generate_series(1,2)` con `LATERAL dbops.fn_pgtap_crea_emittente()` dà **lo
stesso** emittente due volte — un `LATERAL` che non dipende dalla riga il
planner lo esegue una volta sola. Due emittenti = due istruzioni.

### ⏳ Stato del lotto 2 al 2026-09-23 sera (mondo vuoto, 70 file)

| | Mattina | Sera |
| --- | --- | --- |
| verdi | 16 | **22** |
| verdi in attesa dell'apply di `-07`/`-08`/`-09` (provati con la copia in `pg_temp`) | — | **11** |
| verde da owner, com'è dichiarato (il banco lo misura come app, a torto) | — | 1 |
| ancora rossi | 54 | **36** |

**Da applicare** (nessuno dipende dagli altri): `20260923-07` (codice libero
del cliente fuori RLS), `-08` (`fn_pgtap_crea_operatore_umano`), `-09`
(`fn_pgtap_crea_pdp`), `-10` (`fn_crea_risorsa_umana_v2`: profilo SUPER_ADMIN
per `tipo`, non per id cablato). SQL estratto provato da owner su `zeroerp_ci`:
`plpgsql_check` pulito sui tre; con i tre in transazione i presìdi trasversali
`dbops/test-riferimenti-morti-v1` **9/9** e `script/test-rubinetto-primo-motivo-v1`
**7/7**. Cancelli statici tutti verdi; la soglia di
`SOGLIA_THROWS_SENZA_DISCRIMINANTE` scende **120 → 119** (il t.4 di
`guc-aware`).

**I 36 che restano**, per forma (fotografia del banco, da rileggere dopo
l'apply):

* **gestore** (`create-gestore-indirizzo-res`, `-res-domfisc`,
  `create-soggetto-gestori`, `test_indirizzi_unique_res`): «il primo gestore» →
  `fn_pgtap_crea_gestore`, già in servizio;
* **cliente con istanza / BA** (`test-conti-bancari-istanza-cascata`,
  `test-indirizzi-istanza-cascata`, `test-istanze-dati-precontrattuali`,
  `test-trgfn-billing-account-guard-soggetto-coerenza-istanza-v1`,
  `test-fn-get-evento-stato-corrente-cliente-v1`,
  `test-guard-sorgente-polimorfa-testuale-v1`, i tre `available-actions`
  offerta/preventivo): la ricetta di oggi;
* **super admin e operatori «vergini»** (`test-fn-is-super-admin`,
  `test-permessi-funzioni-risoluzione`, `test-fn-check-ultimo-super-admin-attivo`,
  `test-fn-get-operatore-detail`, `test-fn-get-profili-accesso-applicabili`,
  `test-billing-account-auto-link-ef`): `fn_pgtap_crea_operatore_umano` e
  `fn_pgtap_crea_emittente_operatore`;
* **pool di utenti e ruoli CL liberi** (`test-fn-sync-auth-user-is-active-or`,
  `test-identita-digitali-unique-multi-veste`, `test-sync-auth-user-is-active-multi-role`);
* **contatti/indirizzi obbligatori** (`test-fn-crea-utente-tecnico`,
  `test-identita-tecnica`, `test-identita-digitali-guard-coerenza`) e **dati di
  macchina** (`test-contatti-soggetto-cliente`, CF `TTNMHL…`);
* **casi singoli**: `test-catasto-unita-immobiliare` (colonna
  `istanza_utility_id` che non esiste più: il test è rimasto indietro rispetto al
  refactor del catasto), `test-indirizzi-fallback` (tipo di ritorno di una vista
  cambiato), `test-conto-incasso-un-solo-soggetto` (filiale →
  `fn_pgtap_crea_filiale_bancaria`), `test-categorie-clienti-listini-v1`,
  `test-seed-stati-doc-ordini-evaso-v1`, `test-capability-annulla-…`,
  `test-fn-raise-primo-motivo-se-presente-v1` t.15, `test-search-soggetti-universale`,
  `test-vw-giornale-entita`, `test-fn-available-actions-pdf-v1`,
  `test-fn-available-actions-ordine-v2`.

✅ **Corretto con `20260923-10`** (Tid, 23-09: «va corretta con codice
giusto»): `anagrafiche.fn_crea_risorsa_umana_v2` legava il super admin al
profilo con l'**id cablato `9100`** — vero solo perché il seed porta l'id
esplicito, ed era l'unico caso in `pg_proc` (cercato sul `prosrc`).
`config.profili_accesso` non ha `codice_interno` e `codice` non ha lock ⇒ §6d
punto 1: la chiave stabile è l'enum `tipo = 'SUPER_ADMIN'`, la stessa di
`fn_is_super_admin` e dei guard anti-lockout. Il modello però **non** vieta due
profili di quel tipo, e scegliere il primo per id sarebbe un'ambiguità: la madre
pretende **esattamente un** profilo attivo e altrimenti solleva
`E_CONFIG_MANCANTE`, nel blocco dei guard, prima di ogni scrittura. Corpo dalla
doc auto-gen (stesso md5 del `prosrc` su dbdev e su `zeroerp_ci`), firma con
`%TYPE` che risolve agli stessi tipi (verificato: nessun overload). Provato con
l'SQL estratto, da owner su `zeroerp_ci`: `plpgsql_check` pulito; super admin
costruito → legato al profilo risolto; con un secondo profilo SA attivo →
`E_CONFIG_MANCANTE (trovati 2)`; operatore semplice → nessun binding. Con
`-07…-10` in transazione: riferimenti morti 9/9, rubinetto 7/7, e i sei pgTAP che
toccano la funzione verdi (`test-fn-crea-operatore` 12/12,
`test-fn-crea-risorsa-umana` 9/9, `test-risorse-umane-guard-identita-attiva-v1`
8/8, `test-risorse-umane` 8/8, `test-fn-get-soggetto-dati-and-user-profile`
26/26, `dbops/test-punti-canale-campo-v1` 14/14). `config.profili_accesso` non è
in RLS e `zeroerp_app` ha `SELECT`: il percorso applicativo vede lo stesso
profilo. 🔵 Se «un solo profilo SUPER_ADMIN» è una regola del modello, la sua
sede è un indice unico parziale su `tipo`: decisione a parte.