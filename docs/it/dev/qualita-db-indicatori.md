# Qualità del database — indicatori e lezioni

> **Ultima rilettura**: 27 ottobre 2026 — corretta la lettura di
> `vw_codici_errore_da_dichiarare` (è la misura, non il debito) e il voto della Gestione del debito
>
> **Destinatari**: chi sviluppa sullo strato database (schema, funzioni, trigger, policy,
> changeSet, pgTAP), e chi ogni tanto si chiede *«il database sta diventando più vero o
> solo più grande?»* e vuole una risposta che non sia un'impressione.
>
> **Vedi anche**:
>
> * [Presidi e registri del debito](../guide/presidi-e-registri-del-debito.md) — la forma
>   comune: la misura, il registro, il verso.
> * [Linee guida SQL](../linee-guida-sql.md) §11 — i divieti nati da un incidente e il loro
>   guardrail; [pgTAP, come si scrive un test](../guide/pgtap-come-si-scrive-un-test.md) — il
>   preambolo, le baseline, la CI.
> * [Trappole: cosa non fare](trappole.md) e [Ricette: dove intervenire](ricette-dove-intervenire.md)
>   — il lato **costruire**: qui si legge se il lavoro sta peggiorando, lì come non sbagliarlo.
> * Il gemello applicativo: [Qualità BE/FE — indicatori e lezioni](qualita-be-fe-indicatori.md).
> * La **lettura zero**: [migliorie generali DB](work-in-progress/migliorie-generali-da-test-valutazione.md)
>   (08-09-2026 →, ancora aperta), con i difetti trovati e come si chiudono.

---

## Come si legge

Questo documento non serve a dare un voto al database: serve a **non dimenticare le lezioni**
e a tenere d'occhio, nel tempo, i parametri che dicono se il lavoro sta peggiorando in silenzio.

Ha tre parti:

1. **le lezioni** (§1), che non scadono;
2. **gli indicatori** (§2): che cosa si legge, in che verso deve andare, chi lo presidia. I
   valori li stampa `scripts/indicatori-qualita-db.sh`, e il comando **è** la definizione
   dell'indicatore;
3. **la scorecard pesata** (§3), riscritta a ogni rilettura.

⛔ **Regola zero** ([AGENTS.md](../../../.codex/AGENTS.md)): questi numeri **trovano gli errori,
non disegnano il progetto**. Un indicatore che peggiora è una domanda («perché?»), mai il motivo
di una scelta di modello. Sono letture di **struttura** — registri, soglie, vincoli, il catalogo
di PostgreSQL — e portano la loro data. Un `count(*)` sulle righe di lavoro non è un indicatore.

---

## 1. Le lezioni

Vengono dalla valutazione del 2026-09/10: ognuna ha un caso vero dietro, nella lettura zero.

* **Si pesa, non si fa la media.** La valutazione di febbraio dava 8,9 su undici aree con lo
  stesso peso: «naming» e «che cosa impedisce a una regressione di entrare» erano due addendi
  uguali. Il peso di un'area è la **conseguenza** di un difetto lì, non la sua estensione.
* **Un conteggio non disegna una priorità.** «`contabilita`: 0 test, gap critico» era vero e
  non voleva dire niente: lo schema era vuoto. Prima di leggere uno zero si chiede al modello
  che cosa avrebbe dovuto esserci.
* **Un cancello che passa senza aver misurato è peggio di un cancello assente** (D1). La suite
  pgTAP girava con `continue-on-error` contro una baseline mai committata: 600 file buttati via
  a ogni corsa, con la spia verde.
* **«I test passano» non è «le migrazioni sanno ricostruire un sistema che passa i test».** Sul
  database di sviluppo la suite era verde; ricostruita da zero era rossa su 407 file su 601
  (D7). Una fixture che **cerca** il mondo verifica una macchina; una che lo **costruisce**
  verifica il modello.
* **Il verde per sottrazione.** Un test che itera su ciò che c'è, o che salta con uno `skip()`
  quando non trova niente, su un database vuoto passa senza aver provato nulla. Si dichiara con
  uno `skip()` motivato, o si riscrive perché il caso se lo fabbrichi.
* **Un'asserzione senza discriminante accetta anche l'errore sbagliato.** Due volte, sanando un
  `throws_ok(sql, NULL, NULL)`, è venuto fuori un test verde per un errore che non era quello
  della regola (D11).
* **Un registro di debito vale se scende**, e scende solo se ogni riga ha causa, rimedio e data.
  `vw_processi_che_bypassano` aveva una riga con la data di ritiro, ed è andato a zero quel
  giorno; anche il registro dei codici senza policy è a zero dal 07-08. ⛔ **Di una vista di presidio si
  conta il registro, mai la misura**: `vw_codici_errore_da_dichiarare` cresce col catalogo perché
  conta ogni codice che il DB può nominare, e contarla come debito è un errore già fatto tre
  volte (correzione del 27-10).
* **Un registro che non si aggiorna dalla misura del giorno mente a favore.** Il registro dei
  rossi della CI fermo a 361 mentre la CI ne vedeva 227: circa 130 file già verdi tollerati
  come rossi, la cui regressione non ferma un merge.
* **Un difetto che non dà errore è il peggiore**, e i più costosi della valutazione erano di
  questa specie: un `search_path` «prudente» che accecava `dblink` (D6), una GUC che spegne un
  blocco (Q-2), «utente NULL = vede tutto» in una funzione di policy (Q-1), un `UPDATE OF` che
  non vede la colonna cambiata da un altro trigger (D17, D18). Come non cascarci sta nelle
  [Trappole](trappole.md), sezione «Database e migrazioni»: qui resta la lezione, cioè che
  questi difetti li trova solo un presidio a criterio o una prova costruita, mai il rosso.
* **Una policy che esiste non è una policy accesa.** `EXISTS (SELECT 1 FROM pg_policies …)` legge
  verde anche con la RLS spenta (D4): l'invariante si presidia per criterio, non per nome.
* **Un presidio nasce sempre in ritardo** (D5): le prime due proprietà di forma hanno morso prima
  di essere presidiate. Per questo i presidi si scrivono quando un cantiere ci passa.
* **Un rosso che arriva da solo non è una regressione finché non lo si è letto** (D16): un
  test con una data scritta a mano è morto tre settimane dopo, senza che nessuno avesse toccato
  niente. La regola per non scriverli è nelle [Trappole](trappole.md), sezione «Test pgTAP».
* **Un numero scritto in due posti ne ha sempre uno vecchio**, e quello senza presidio è il
  documento. La rilettura del 23-10 ha trovato nella lettura zero un conteggio dei pgTAP che
  escludeva per errore i file col nome «template»: per questo qui i valori li stampa lo script.
* **Un lavoro fermo su una decisione costa zero e resta fermo lo stesso**, finché nessuno fa la
  domanda. Al 23-10 D18 era ferma dal 05-10 e Q-2 dal 04-10.
* **Una misura che non si è potuta prendere si scrive.** Lo script lo fa da sé: senza
  `--catalogo`, o se la connessione cade, stampa che il catalogo non è stato letto.

---

## 2. Gli indicatori

Si stampano con:

```bash
scripts/indicatori-qualita-db.sh                  # il repo, tabella leggibile
scripts/indicatori-qualita-db.sh --tsv            # per confrontare due letture con diff
set -a; . db/internal.env; set +a
scripts/indicatori-qualita-db.sh --catalogo       # il repo più il catalogo di dbdev
```

Senza opzioni lo script legge **solo** il repo (niente database, niente rete, un paio di
secondi). Con `--catalogo` legge anche le viste di presidio di `dbops` e `pg_catalog` sul
database delle variabili `PG*`, in una transazione di sola lettura. ⚠️ Il catalogo è quello di
**una** macchina: dbdev non è la CI, e un valore letto lì vale per dbdev. La suite e i guardrail
hanno già un cancello in CI: qui si legge ciò che quei cancelli lasciano nei registri, non si
rilanciano.

La colonna «23-10» è la lettura di quel giorno. Si **sovrascrive** a ogni rilettura: la storia
sta in git.

### Suite pgTAP

| Indicatore | Verso | Chi lo presidia | 23-10 |
| --- | --- | --- | --- |
| file pgTAP | colore | la suite in `ci-validate` | 887 |
| rossi noti in CI (`baseline-rossi-ci.tsv`) | ↓ | cancello in CI; scende **solo** con `pgtap-baseline-ci-rientrati.sh` sul log della corsa, il giorno stesso | 360 (292 `ERRORE_FIXTURE`, 68 `ASSERZIONE`) |
| ultimo commit del registro della CI | non più vecchio dell'ultima corsa CI | ⚠️ nessun presidio | 20-10 (ultima misura CI registrata: 26-09, 227 rossi) |
| rossi noti sullo scratch (`baseline-rossi-scratch.tsv`) | ↓ | `scripts/ci-local.sh` su `zeroerp_ruoli` | 147 (120 / 26 / 1 `SORGENTE_POLIMORFA`) |
| rossi noti in sviluppo (`baseline-rossi.tsv`) | ↓ fino a 0 | la corsa su dbdev | 6 (5 / 1) |
| soglia dei `throws_ok` senza discriminante | ↓, a cricchetto | `guardrail_pgtap_preambolo.py` | 115 |
| file con `pgtap-runner: owner` | si **legge**: ogni motivo dev'essere ancora vero | il motivo scritto nel file | 145 |
| file con uno `skip()` | si **legge**: su un DB vuoto contano verdi | — | 122 |
| file con l'utente `'1'` fisso | = 0 | — ⚠️ nessun presidio | 4 |
| schemi senza nessun file pgTAP | colore: dice dove il comportamento non è ancora scritto | — | `acquisti` |

### Registri e rubinetti

| Indicatore | Verso | Chi lo presidia | 23-10 |
| --- | --- | --- | --- |
| `rls_perimetro_debito` (righe del seed) | ↓ | `test-rls-perimetro-scoperto` + `vw_rls_perimetro_scoperto` | 6 |
| `SECURITY DEFINER` senza `pg_temp` / con `public` prima di `pg_catalog` | ↓, a cricchetto | `test-security-definer-search-path-v1` (test 4 e 5) | 16 / 4 |

### Codici errore

| Indicatore | Verso | Chi lo presidia | 23-10 |
| --- | --- | --- | --- |
| codici a catalogo / con `obsoleto_dal` | colore | — | 1.126 / 120 |
| codici senza messaggio `it` | = 0 | ⚠️ nessun presidio lato DB (il BE ha il ripiego) | 6 (tutti `W_`) |

I messaggi per lingua li legge il gemello BE/FE: un numero, una sede.

### Liquibase e guardrail

| Indicatore | Verso | Chi lo presidia | 23-10 |
| --- | --- | --- | --- |
| changeSet in `migrations_v2` | colore | — | 5.727 |
| file di changeSet senza `logicalFilePath` | = 0 | ⚠️ nessun presidio (la regola è in [AGENTS.md](../../../.codex/AGENTS.md)) | 37 |
| guardrail scritti / chiamati in `ci-validate` | uguali, salvo l'hook locale `guardrail_no_db_migrate` | revisione | 9 / 8 |

### Documentazione

| Indicatore | Verso | Chi lo presidia | 23-10 |
| --- | --- | --- | --- |
| pagine `manual/` / pagine auto-generate | colore: si legge con lo spessore del dominio | — | 1.706 / 1.939 |

### Catalogo (`--catalogo`, dbdev)

| Indicatore | Verso | Chi lo presidia | 23-10 |
| --- | --- | --- | --- |
| codici nominabili dal DB (`vw_codici_errore_da_dichiarare`) — ⛔ **misura, non debito** | colore: cresce col dominio | — (il debito è `codici_errore_senza_policy`, a **0**, presidiato da `test_error_codes_db_policy_guardrail`) | 702 |
| FK senza indice fuori policy | ↓ | `vw_fk_con_indice_missing_policy` | 57 |
| indici ridondanti per prefisso | = 0 | `vw_indici_ridondanti_prefisso` | 1 |
| processi che bypassano la RLS | = 0 | `vw_processi_che_bypassano` | 0 |
| tabelle con RLS / con `FORCE` | `FORCE` = 0 (invariante dell'owner, Q-3) | presidio di postura (D17) | 174 / 0 |
| trigger / con la fase nel nome / dai due guard per-figlia | la fase ↑; il per-figlia è colore (D9) | — | 2.358 / 1.603 / 816 |
| trigger su `catalogo.articoli` | colore: la tabella con più figlie (D9) | — | 50 |

### Che cosa non si misura, e perché

| Cosa | Perché no |
| --- | --- |
| Copertura vera della suite | Non c'è un comando: «funzione nominata in un pgTAP» (62% all'08-09) è un limite superiore, essere nominata non è essere collaudata |
| I rossi della CI di oggi | Stanno nel log della corsa, che scade: si leggono con `pgtap-baseline-ci-rientrati.sh` il giorno stesso, non da qui |
| Prestazioni dei piani | Si misurano nel brief che le tocca, dopo le statistiche (D15), e portano la macchina e la data: un millisecondo non è un indicatore di struttura |
| Rilievi dei guardrail | Sono già un cancello a zero: se ce n'è uno, la CI è rossa |
| Header di licenza mancanti | L'hook guarda solo i file **aggiunti**, per scelta; non c'è un comando sull'intero repo |

---

## 3. La scorecard pesata — rilettura del 2026-10-23

Il **peso** è la conseguenza di un difetto nell'area. Un voto che si muove dice il suo perché;
uno fermo dice che cosa lo tiene fermo. «Era» è il voto della rilettura precedente (26-09,
nella lettura zero).

| Area | Peso | Voto | Era | Che cosa lo tiene dov'è |
| --- | --- | --- | --- | --- |
| Catena di verifica (CI) | 🔴 alto | **7,5** | 7,5 | Cancello vero dal 09-09; dal 15-10 la CI ricostruisce il DB col modello dei ruoli di sistema. Il registro della CI non è stato aggiornato dall'ultima misura: file già verdi tollerati come rossi |
| Perimetro dei dati (RLS) | 🔴 alto | **8** | 8 | Dominio documento e storico protetti, nessun processo che bypassa, perimetro una volta per istruzione. Aperti la catena delle istanze sotto RLS (D18) e le GUC di bypass (Q-2) |
| Copertura test | 🔴 alto | **4,5** | 4 | Scratch col modello nuovo verde all'83%, baseline di sviluppo a 6. Il numero della CI è vecchio di un mese, `acquisti` è a zero, 122 file con `skip()` |
| Postura di sicurezza degli oggetti | 🟠 medio | **8** | 7,5 | Ruoli di sistema: un proprietario, `zeroerp_job`, nessun superuser al lavoro; rubinetti D6-bis a 16 e 4. Aperti Q-2 e D6-bis |
| Simmetria del dominio | 🟠 medio | **non votata** | — | L'ordine di costruzione non si vota. Si presidia la regola: *ogni decisione su `vendite` vale per `acquisti`* — e dal 13-10 `vendite` ne ha prese altre (grammatica unica, modelli standard) |
| Osservabilità dei presidi | 🟠 medio | **7,5** | 7 | Il presidio dei job dice la causa, la spia si spegne solo su un verdetto completo, le statistiche hanno un job che si verifica. Resta il rumore dei processi ritirati nella vista dei job |
| Gestione del debito | 🟠 medio | **6** | 6 | I registri piccoli calano, il bypass è sparito alla data, i codici senza policy sono a zero dal 07-08. Lo tiene fermo il registro della CI, non aggiornato dall'ultima misura. *(⛔ 27-10: il 23-10 era 5,5, contando come debito i 702 codici della misura)* |
| Pattern trigger e automazioni | 🟡 basso | **7,5** | 7,5 | Automazioni dichiarative eccellenti; il guard per-figlia cresce con le figlie (D9) |
| Error handling / codici errore | 🟡 basso | **8,5** | 8,5 | Contratto a tre lati presidiato. Sei `W_` senza messaggio; la misura non vede i codici negli argomenti dei trigger (D24) |
| Disciplina Liquibase | 🟡 basso | **9** | 9 | Divieti nati da incidenti, ognuno col suo guardrail. `logicalFilePath` senza presidio |
| Documentazione | 🟡 basso | **8,5** | 8,5 | Copertura piena; sottile dove il dominio è sottile |
| Naming | 🟡 basso | **8** | 8 | 94-99% sui vincoli; fase dei trigger al 68%; un vocabolario solo per i tipi di documento |

---

## 4. Quando e come si rilegge

* **Quando**: alla chiusura di un cantiere DB grosso, dopo una corsa CI che tocca `db/`, o
  quando un indicatore si muove senza che nessuno sappia perché. Non a calendario: una
  rilettura senza niente di nuovo è rumore.
* **Come**: si lancia lo script (con `--catalogo` su dbdev), si confronta con la colonna della
  rilettura precedente, e per ogni riga che si è mossa ci si chiede **perché**. Poi si
  riscrivono la colonna di §2, la data in testa e i voti di §3 che hanno un motivo per muoversi.
* ⛔ **Un indicatore nuovo** entra nello script **e** nella tabella di §2 nello stesso giro, col
  suo verso e il suo presidio (o col «nessun presidio» scritto). Uno solo dei due non basta.
* ⛔ **Un indicatore del catalogo** legge struttura o un registro di presidio, mai le righe di
  lavoro: «quante fatture ci sono» non è qualità.
* ⭐ Un difetto trovato rileggendo **non si scrive qui**: va nel brief del suo tema (regola «un
  tema, un brief», [AGENTS.md](../../../.codex/AGENTS.md)) o, finché è aperta, nella lettura
  zero. Qui pesa solo sul voto.

---

## 5. Il lato applicativo

Backend e frontend hanno il loro documento gemello,
[qualita-be-fe-indicatori.md](qualita-be-fe-indicatori.md), con lo stesso formato. Un indicatore
che sta sul confine (i messaggi d'errore per lingua, gli smoke) vive in **uno** dei due, e
l'altro lo rimanda. Il punto d'incontro è la [mappa concentrica](../mappa-concentrica.md) §«La
qualità si misura».
