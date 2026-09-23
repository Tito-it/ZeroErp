# Brief DB — Il mondo si costruisce: il building block della composizione (D7, giro 2)

> **Da leggere per primo: §3 — la forma, e perché non sta nella riga di contesto.**
> Origine: [migliorie-generali-da-test-valutazione.md](migliorie-generali-da-test-valutazione.md)
> §3 D7 («la ricetta per file»), figlio del brief madre
> [brief-db-fixture-che-costruiscono-d7-d6-d4.md](../work-done/brief-db-fixture-che-costruiscono-d7-d6-d4.md)
> (giro 1, chiuso il 12-09) e della rev `20260920-01`, che ha insegnato alla riga
> di contesto a **costruire** il mondo quando non lo trova.
>
> ✏️ **Stato 2026-09-23: il lotto 1 è CHIUSO, da applicare.**
> Tre changeSet scritti e provati — `20260922-17` (`fn_pgtap_crea_mondo_cliente`,
> **applicato** il 22-09), `20260923-01` (il builder degli articoli sceglie la
> UoM), `20260923-04` (`fn_pgtap_crea_fattura`) e `20260923-05`
> (`fn_pgtap_crea_filiale_bancaria`) — più tre presidi nuovi e **21 file
> riscritti**. Dettaglio in §10.
> 🔵 A Tid: l'apply dei tre changeSet, poi la corsa CI che certifica i rientrati.
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
| 5 | I 4 file che **committano** / i 6 col contesto in autocommit | 🔵 rinviata il 22-09 («prima la forma»), resta in `migliorie-generali` §6 D7 |
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

* **l'apply di `20260922-17`** (Tid), e subito dopo la misura che qui manca: la
  stessa chiamata come `zeroerp_app`, sui due rami;
* poi il **lotto 1** di §5: 43 file su sei schemi, la ricetta di §5 applicata
  file per file, e la corsa CI che li certifica **quel giorno**;
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

⛔ **E i due database si migrano SEPARATAMENTE** (misurato il 23-09): con
`20260923-04/-05` applicati su dbdev e lo scratch fermo al `-03` delle 09:36,
i nove file più il presidio della fattura sono rossi **solo su `zeroerp_ci`**,
con «la funzione `dbops.fn_pgtap_crea_fattura(unknown)` non esiste». Non è un
difetto delle fixture: è il database indietro. ⚠️ E ha una conseguenza sul
registro: una baseline lanciata sullo scratch **prima** del suo migrate
scriverebbe quei dieci in `baseline-rossi-ci.tsv` come debito nuovo — debito che
non è. Oggi nel registro non ci sono, ed è giusto così.

⚠️ **Questi nove girano solo dopo l'apply.** Le prove sono in transazione
ritirata su `zeroerp_ci` con l'SQL estratto dei tre changeSet in testa, **da
owner**: su dbdev lo schema `dbops` è di `titodb` e la funzione, dentro una
transazione, non esiste per nessun'altra sessione. Il verso dev si misura dopo.

### ⏳ Cosa resta del lotto 1
* `ui/test-lista-competenza-gruppi-colonna-emittente-v1`: **eccezione
  dichiarata**. Il suo t.7 è il guard «il t.6 non è verde per sottrazione», e su
  un database senza documenti dice il vero: il file non ha materia da
  giudicare. Rientra quando il lotto `vendite` gli costruisce un documento.
* I due `parameter-fk-surrogate-*`: aspettano il changeSet del punto 2.

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
