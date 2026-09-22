# Brief DB — Il mondo si costruisce: il building block della composizione (D7, giro 2)

> **Da leggere per primo: §3 — la forma, e perché non sta nella riga di contesto.**
> Origine: [migliorie-generali-da-test-valutazione.md](migliorie-generali-da-test-valutazione.md)
> §3 D7 («la ricetta per file»), figlio del brief madre
> [brief-db-fixture-che-costruiscono-d7-d6-d4.md](../work-done/brief-db-fixture-che-costruiscono-d7-d6-d4.md)
> (giro 1, chiuso il 12-09) e della rev `20260920-01`, che ha insegnato alla riga
> di contesto a **costruire** il mondo quando non lo trova.
>
> ✏️ **Stato 2026-09-22: il BB è SCRITTO e PROVATO, da applicare.**
> `20_code/dbops/20260922-17-create-fn-pgtap-crea-mondo-cliente-mctit.yaml` più il
> presidio `db/pgtap/dbops/test-fn-pgtap-crea-mondo-cliente-v1.sql` (9 casi).
> Le quattro decisioni di forma sono **prese** (§7, Tid il 22-09); i lotti di §5
> partono dopo l'apply.
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
