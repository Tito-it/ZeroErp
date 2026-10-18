# Brief DB — La ricerca per segmento non legge più tutte le attività

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-10. **A chi:** Tid.
> **Origine:** la ricerca dei colli di bottiglia partita dai pgTAP lenti di
> `script/` (2026-10-10). Dopo `20261010-77` e `-79` (COST sulle funzioni di
> policy) la capability del DDT costava ancora ~24 ms a documento; il resto
> stava qui.
> **Decisione di Tid (2026-10-10):** strada **A** (§3).
> **Stato:** ✅ **chiuso e archiviato il 2026-10-10.** `20261010-80…-84` applicati da
> Tid, pgTAP rilanciati, misure dopo l'apply in §5.2 e §6. Il debito residuo è il
> brief [brief-db-plancache-funzioni-con-query-incorporate](brief-db-plancache-funzioni-con-query-incorporate.md)
> (D26-2 del registro delle migliorie), §8.
> **Ricadute BE/FE:** nessuna. Colonna nuova solo interna al DB; risultati delle
> funzioni identici.

## 1. Il difetto

`vendite.fn_af_merce_per_riga` (la corsia «attività fatturabili» della partita
merce) e `script.fn_get_stato_push_segment` cercano in
`vendite.commesse_attivita` le attività di un segmento: la chiave esatta **e** le
sue varianti con suffisso (`chiave#CMP:…` per i componenti di kit, `#RET:…`). Il
suffisso si cerca con un **intervallo per prefisso** sull'indice
`ix_commesse_attivita_segment_key` (`varchar_pattern_ops`):
`segment_key ~>=~ 'k#' AND segment_key ~<~ 'k$'` — la forma che
[linee-guida-sql §8.5-bis](../../linee-guida-sql.md) prescrive sotto RLS.

⛔ Quando le chiavi arrivano come **parametro** (piano generico), il
pianificatore non conosce i bordi e stima l'intervallo con la selettività di
default (~11 % della tabella **per chiave**). Allora la scansione intera, con la
policy valutata su ogni riga, gli sembra appena più economica, e la sceglie.

⭐ **Ed è un difetto sul modello, non sulle righe di oggi:** con una stima
proporzionale alla tabella, indice e scansione crescono insieme, e il
pianificatore resta in bilico a qualunque volume. In esercizio ogni DDT
pagherebbe la policy su **tutte** le attività fatturabili.

⚠️ §8.5-bis dice che «nella forma reale la plancache tiene i piani custom finché
il generico costa di più». Dentro la capability del DDT non è così: il modo
`auto` costa quanto il generico forzato (sotto, §2). La riga va corretta (§5).

## 2. Le misure — fatti datati

Dbdev, come app (`zeroerp_app` + contesto operatore), 2026-10-10, dopo `-77/-79`.

| Cosa | Tempo |
| --- | --- |
| capability su 51 DDT (`fn_available_actions_ddt`) | ~1,3 s |
| …di cui la diagnosi del push, piano generico (`auto`) | ~0,95-1,0 s |
| la stessa diagnosi forzata a piano personalizzato | ~3,5 s (il plpgsql sceglie bene) |
| nel piano generico della diagnosi, `fn_af_merce_per_riga` | 20 ms su 29 |
| `fn_af_merce_per_riga` con 2 chiavi **letterali** | 1,6 ms |
| …con le stesse 2 chiavi come **parametro** | ~20 ms (`Seq Scan` su `commesse_attivita`, 116 righe, policy su ognuna) |

Prova della causa, piano generico, stesse 2 chiavi:

| Ricerca | Tempo | Accesso |
| --- | --- | --- |
| solo uguaglianza `segment_key = k` | 3 ms | `Index Cond` |
| solo intervallo `~>=~ k# AND ~<~ k$` | 31 ms | scansione intera + policy |

## 3. La decisione — A: una colonna con la base del segmento

`vendite.commesse_attivita.segment_base varchar(128) GENERATED ALWAYS AS
(split_part(segment_key, '#', 1)) STORED NOT NULL`, con un btree semplice. Le due
funzioni **aggiungono** `ca.segment_base = <base della chiave>` e **tengono** il
predicato di oggi come filtro residuo.

* Il predicato di oggi **implica** l'uguaglianza sulla base (una chiave che
  comincia per `k#…` o vale `k` ha base `split_part(k,'#',1)`): aggiungerla non
  toglie nessuna riga. Risultati identici **per costruzione**, non per misura.
* `segment_base = x` è `texteq` su una colonna: leakproof, sale in `Index Cond`
  sotto la policy anche nel piano generico (provato: 3 ms). Il residuo — con le
  sue concatenazioni leaky — lavora sulle poche righe trovate.
* ⛔ Scartato l'indice su espressione `split_part(segment_key,'#',1)`:
  `split_part` non è leakproof (`pg_proc.proleakproof = f`), sotto RLS
  l'indice non verrebbe usato.
* ⛔ Scartata la strada B (separare uguaglianza e intervallo in due rami): il
  ramo a intervallo resterebbe esposto alla stessa stima.

## 4. Censimento (2026-10-10)

| Domanda | Esito |
| --- | --- |
| chi **scrive** `commesse_attivita` | solo `vendite.fn_upsert_commessa_attivita`, con elenco esplicito di colonne: la colonna generata non la tocca |
| `INSERT … SELECT *` / `VALUES (r.*)` / `%ROWTYPE` / `LIKE` | nessuno (funzioni e pgTAP: 31 fixture, tutte con elenco) |
| backend | nessuna scrittura |
| viste che la leggono | 9, colonne fissate alla creazione: invariate |
| storico (`trg_…_z90_storico_upd_dlt`) | salva `to_jsonb(NEW)`: la colonna entra da sola. ⚠️ Nei BEFORE la generata vale NULL (§7b): lo snapshot porterà `"segment_base": null`. Dato derivato, ricostruibile da `segment_key` che lo snapshot contiene |
| chi usa l'intervallo su `segment_key` | `vendite.fn_af_merce_per_riga`, `script.fn_get_stato_push_segment` — tutti e due in questo cantiere |
| pgTAP che fissano la forma | `script/test-fn-get-stato-push-segment-v1` t.2 (`~>=~` nel corpo), `vendite/test-fn-af-merce-per-riga-chiusura-v1` t.4 (opclass dell'indice): restano veri, la forma si aggiunge |
| dati: `#` diversi da `#CMP:` | zero su dbdev — fatto datato, non motivo: la forma scelta non ne dipende |

## 5. I passi

| Passo | ChangeSet / file | Stato |
| --- | --- | --- |
| P-1 | `00_schema/vendite/20261010-80-alter-commesse-attivita-add-segment-base` — colonna generata + indice | ✍️ scritto |
| P-2 | `20_code/vendite/20261010-81-update-fn-af-merce-per-riga-segment-base` | ✍️ scritto |
| P-3 | `20_code/script/20261010-82-update-fn-get-stato-push-segment-segment-base` | ✍️ scritto |
| P-4 | `db/pgtap/vendite/test-commesse-attivita-segment-base-v1.sql` (plan 6) | ✍️ scritto |
| P-5 | linee-guida-sql §8.5-bis; manual di `fn_af_merce_per_riga`, `fn_get_stato_push_segment`, `commesse_attivita` | ✍️ fatto |
| P-6 | misura dopo l'apply (Tid applica) | ⏳ |

### 5.1 Prove prima dell'apply (2026-10-10, scratch `zeroerp_ci`, SQL estratto, transazione annullata)

* **Equivalenza, 110 pgTAP** che toccano le due funzioni o i loro lettori
  (partita merce, diagnosi, lister del push, capability), ciascuno senza e con
  l'SQL estratto in testa: **nessuna differenza** — 549 `ok` / 37 `not ok` in
  entrambe le corse (i rossi sono dello scratch: da owner e senza anagrafiche,
  identici). I due file che provano l'equivalenza su casi COSTRUITI girano per
  intero: `test-fn-get-stato-push-segment-v1` 11/12 (vicino numerico, suffisso
  ignoto `#FOO`), `test-fn-af-merce-per-riga-chiusura-v1` 12/13 — il rosso di
  ciascuno è lo scope, rosso da owner per costruzione.
* **P-4**: rosso senza i changeSet (la colonna non c'è), 6/6 con. **Mutazione**:
  con il solo `-80` (colonna senza le funzioni riscritte) i pin 5 e 6 diventano
  rossi.
* **Rollback**: `-80/-81/-82` avanti e poi i rollback in ordine inverso — le
  definizioni delle due funzioni tornano identiche (md5), colonna e indice
  spariscono. Prova anche che i corpi di partenza (`-51`, `-55`) coincidevano
  con quelli vivi.
* ⚠️ **Il piano** non si prova sullo scratch (niente dati) né su dbdev prima
  dell'apply (niente DDL da `zeroerp_app`): il fatto è la misura di §2
  (uguaglianza in `Index Cond` nel piano generico, 3 ms), la conferma è P-6.

### 5.2 Dopo l'apply (P-6) — misurato il 2026-10-10

Applicato da Tid, pgTAP rilanciati. Dbdev come app (56 DDT a questa data):

| Cosa | Prima | Dopo |
| --- | --- | --- |
| `fn_af_merce_per_riga`, 2 chiavi come parametro (generico) | ~20 ms | **0,9 ms** |
| diagnosi di un DDT, piano generico | 29 ms | **2,2 ms** |
| `Seq Scan on commesse_attivita` eseguiti nel generico | 1 | **0** (resta solo nel ramo «tutte», `never executed`) |
| diagnosi su tutti i DDT, ciclo plpgsql **forzato generico** | ~0,95 s | **0,42 s** |
| capability su tutti i DDT, **forzato generico** | — | **0,61 s** |
| capability su tutti i DDT, modo `auto` (quello reale) | ~1,3 s | ~1,4 s |

⭐ **Il cantiere ha fatto quello che doveva nel piano generico.** ⛔ Ma nel modo
`auto` la plancache non sceglie stabilmente il generico: confronta i costi
STIMATI, il generico con il parametro sconosciuto le sembra più caro e continua
a ripianificare — e ripianificare la query (le funzioni SQL incorporate la
rendono enorme) costa ~13-15 ms a chiamata, con piani personalizzati che qui
sono anche più lenti da eseguire (forzati: 3,7 s su 56 DDT). Il guadagno c'è ed
è chiuso dietro questa scelta: §6.

## 6. La plancache sceglie il piano personalizzato

**Decisione di Tid (2026-10-10): strada 1**, prima sulla capability del DDT,
poi — misurata — anche sul lister `vendite.fn_list_ddt_da_pushare`, l'altro
chiamante della diagnosi.

| Strada | Cosa | Esito |
| --- | --- | --- |
| **1** ⭐ | `ALTER FUNCTION … SET plan_cache_mode = force_generic_plan` sulla funzione plpgsql che chiama la diagnosi con un parametro: le sue query si pianificano una volta | scelta |
| 2 | rendere buoni i piani personalizzati (costo di pianificazione della query incorporata, stime) | più profonda, esito incerto: se la 1 non basta |

| Passo | File | Stato |
| --- | --- | --- |
| P-7 | `20_code/script/20261010-83-alter-fn-available-actions-ddt-piano-generico` | ✍️ scritto |
| P-8 | `db/pgtap/script/test-fn-available-actions-ddt-piano-generico-v1.sql` (plan 2: la clausola; il contratto invariato) | ✍️ scritto |
| P-9 | misura dopo l'apply di `-83` | ✅ capability su 56 DDT, modo reale: **1,42 → ~0,6 s**; una chiamata a freddo ~10 ms |
| P-10 | `20_code/vendite/20261010-84-alter-fn-list-ddt-da-pushare-piano-generico` + test 3 di P-8 | ✅ applicato; misurato dopo: **56 chiamate per DDT 1,30 → ~0,48 s**, senza filtri ~1,14 s (invariato). Misura prima: 56 chiamate per DDT auto 1,30 s, generico 0,45 s; senza filtri 1,19 / 1,11 s (il generico non peggiora) |

⛔ La clausola è una **proprietà invisibile nel corpo**, come `ROWS` e `COST`: un
`CREATE OR REPLACE` che non la ripete la perde. La presidia P-8.

Prove prima dell'apply (scratch, SQL estratto, transazione annullata): P-8 rosso
senza e 2/2 con; i 10 pgTAP che chiamano la capability del DDT, senza e con
`-83`: identici, salvo P-8. Per `-84`: P-8 test 3 rosso col solo `-83`, 3/3 con
`-83`+`-84`; i 12 pgTAP che chiamano il lister identici salvo P-8 (molti si
fermano presto sullo scratch per mancanza di dati, uguali nei due versi: la
prova vera è la corsa su dbdev).

## 7. Bilancio — fatti datati, dbdev come app, 2026-10-10

| Cosa | Inizio giornata | Chiusura |
| --- | --- | --- |
| capability del DDT su tutti i DDT | ~2,1 s (51 DDT) | ~0,6 s (56 DDT) |
| `fn_partite_merce` su un DDT | 47 ms | ~9 ms |
| lister per DDT, 56 chiamate | 1,30 s (misurato prima di `-84`) | ~0,48 s |

⭐ Più dei millisecondi conta la forma: questi costi dipendono ora dalle righe
del documento, non da quante righe ha `commesse_attivita`. Nella stessa giornata,
fuori da questo brief e nei loro changeSet: `COST 5000` sulle funzioni di policy
(`20261010-77`, `-79`) e il ritiro di `fn_scope_ef_whitelist_via_ente_incasso`
(`-78`).

## 8. Archiviazione e debito residuo

Archiviato il 2026-10-10. Due punti aperti, che non si portano in archivio:
stanno nel brief
[brief-db-plancache-funzioni-con-query-incorporate](brief-db-plancache-funzioni-con-query-incorporate.md)
(D26-2):

* il **censimento** delle altre funzioni plpgsql che chiamano con un parametro
  una funzione SQL grande che si incorpora (stessa misura: `auto` contro
  generico forzato);
* il **lister senza filtri** (~1,1 s), che non è un problema di plancache e va
  profilato come query.
