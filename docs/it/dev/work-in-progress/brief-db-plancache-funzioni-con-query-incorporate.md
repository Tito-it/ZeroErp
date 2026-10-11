# Brief DB — Le funzioni che ripianificano a ogni chiamata

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-10. **A chi:** Tid.
> **Origine:** il debito residuo di
> [brief-db-segment-base-commesse-attivita](../work-done/brief-db-segment-base-commesse-attivita.md)
> (§8), archiviato il 2026-10-10. Voce nel registro: **D26-2** di
> [migliorie-generali-da-test-valutazione](migliorie-generali-da-test-valutazione.md).
> **Stato (2026-10-10):** 🔎 censimento e misura del §2.1 fatti (§4). **D-4**: primo
> passo `20261010-44` ✅ applicato da Tid, pgTAP `vendite` rilanciati, misurato (§5.2).
> D-6 e D-5 passate al brief figlio `brief-db-lineage-seminata-per-chiave`. **2026-10-11**: D-3
> misurata (§5bis), **D-3a** `20261011-42` ✅ applicato. Aperte **D-2** e **D-3b**. **Cosa resta: §6.**
> **Ricadute BE/FE:** nessuna prevista.

## 1. Cosa ha insegnato il cantiere da cui nasce

Una funzione plpgsql che chiama con un **parametro** una funzione SQL che si
incorpora (`fn_ddt_push_diagnosi` → `fn_partite_merce` → `fn_af_merce_per_riga`)
esegue una query enorme. In modo `auto` la plancache confronta i costi
**stimati**: il piano generico, col parametro sconosciuto, le sembra più caro, e
lei ripianifica a ogni chiamata — ~13-15 ms di sola pianificazione, con piani
personalizzati spesso anche più lenti da eseguire.

La cura applicata lì: `ALTER FUNCTION … SET plan_cache_mode = force_generic_plan`
sulla funzione plpgsql chiamante (`20261010-83` capability del DDT, `-84` lister
dei DDT da spingere), presidiata dal pgTAP
`script/test-fn-available-actions-ddt-piano-generico-v1`. Fatti datati
(2026-10-10, dbdev come app, 56 DDT): capability 1,42 → ~0,6 s; lister per DDT
1,30 → ~0,48 s.

## 2. I due punti aperti

### 2.1 Le altre funzioni con la stessa forma

Il censimento non è stato fatto: le due funzioni curate sono le sole misurate.
Candidate per costruzione: le funzioni plpgsql che chiamano con un parametro una
funzione `LANGUAGE sql` `BEGIN ATOMIC` grande (diagnosi, partite merce,
situazione merce dell'ordine, le capability degli altri documenti, le altre
`fn_list_*_da_pushare`).
Il metodo, già provato: per ciascuna, un ciclo plpgsql di N chiamate come app in
`auto` e con `force_generic_plan` di sessione — se il generico costa molto meno,
la clausola sulla funzione è la cura; se costa uguale, non serve.
⛔ La clausola non si mette «per igiene»: si mette dove la misura mostra il
difetto, e il presidio la pretende solo lì.

### 2.2 Il lister dei DDT senza filtri

`vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL, NULL)` costa ~1,1 s (dbdev
come app, 2026-10-10), uguale in `auto` e in generico: è la diagnosi di tutti i
DDT in una chiamata, non un problema di plancache. Va profilata come query
(`EXPLAIN ANALYZE` del ramo «tutti») prima di dire se e dove si può migliorare.

## 3. Decisioni attese

* **D-1** — fare il censimento del §2.1, e con che perimetro (tutte le capability
  e i lister, o solo le funzioni che il backend chiama in un ciclo).
* **D-2** — profilare il §2.2 ora, o quando il volume dei DDT lo renderà
  visibile.

## 4. Censimento e misura (2026-10-10, dbdev come app)

### 4.1 Il censimento

Funzioni plpgsql che nominano una funzione `LANGUAGE sql` o una **vista** (le
viste sono macro: stessa forma) il cui corpo, sommato a quello delle SQL e viste
annidate, supera ~4.000 caratteri: **43**. Censimento per testo, quindi largo (una
menzione in un commento conta): il criterio vero è la misura.

### 4.2 La misura

Per ciascuna candidata **di sola lettura**: un ciclo plpgsql di N chiamate (max
50) su argomenti veri, seconda corsa, in `auto` e con `force_generic_plan` di
sessione. Le funzioni che scrivono e i trigger non si misurano così su dbdev.

| Funzione | ms/chiamata `auto` | ms/chiamata generico | Rapporto |
| --- | --- | --- | --- |
| `vendite.fn_resi_da_accreditare` (per DDT) | 22,5 | 5,6 | **4,0** |
| `vendite.fn_resi_riga_tetti_accredito` (per riga di reso) | 6,0 | 1,5 | **4,1** |
| `vendite.fn_get_lotto_segnalazioni_summary` | 3,3 | 2,6 | 1,3 |
| `script.fn_check_accredito_annullabile` | 0,63 | 0,51 | 1,2 |
| `pratiche.fn_stato_sorgente` | 0,49 | 0,42 | 1,2 |
| altre 14 (capability preventivo, prezzi autorizzati, saldi, permessi, operatore, totp, sorgenti, indirizzi, commessa, riconsegna ordine…) | 0,1-1,3 | uguale | 1,0 |
| `vendite.fn_documento_lineage` (preventivo / ordine / DDT) | **~600-780** | uguale | 1,0 |
| `vendite.vw_offerte_commerciali_lista` filtrata per un id | **~390** | uguale | 1,0 |

### 4.3 Cosa dice

* **Il difetto di plancache c'è solo sui resi**: le due funzioni SQL della coda
  accrediti, 4× fra `auto` e generico. I chiamanti plpgsql sono
  `vendite.fn_accredita_riga_reso` (chiama `fn_resi_da_accreditare`) e il trigger
  `vendite.trgfn_resi_accrediti_guard` (chiama `fn_resi_riga_tetti_accredito`);
  la vista `vw_resi_da_accreditare` è letta da `fn_annulla_accredito_riga_reso`,
  `fn_chiudi_riconsegna_reso`, `fn_check_accredito_annullabile`. Tutti scrivono
  (o sono trigger): il guadagno reale si misura su un ciclo di accrediti
  costruito, in transazione annullata.
* **Due funzioni lente in sé, non per la plancache** — e sono le più importanti
  trovate: `fn_documento_lineage` (il pannello «Passaggi», ~0,6-0,8 s a
  chiamata) e `vw_offerte_commerciali_lista` letta per un id (~0,4 s: il filtro
  per id non scende dentro la vista). Vanno profilate come query: è un altro
  difetto, e un altro cantiere.
* Le altre 16 misurate non hanno il difetto: la plancache sceglie bene.

### 4.4 Decisioni attese sulla lista

* **D-3** — resi: misurare il ciclo di accredito costruito e, se il 4× regge,
  la clausola `plan_cache_mode` sui chiamanti plpgsql (come `20261010-83/-84`).
* **D-4** — aprire un cantiere sul **pannello «Passaggi»** (`fn_documento_lineage`).
* **D-5** — aprire un cantiere sulla **lista offerte letta per id**
  (`vw_offerte_commerciali_lista`; la legge anche il trigger della revisione).

## 5. D-4 — il pannello «Passaggi» (`vendite.fn_documento_lineage`)

Avviata da Tid il 2026-10-10.

### 5.1 La causa

`vendite.vw_documento_lineage_archi` costruisce **l'intero grafo** decorato: 13
rami in `UNION ALL` per gli archi, e una CTE `MATERIALIZED` con i nodi di tutti i
documenti. La funzione la nominava nel passo iniziale e nel termine ricorsivo,
con un join a `OR` fra le due direzioni: la vista si rivalutava a ogni livello,
e il recinto `MATERIALIZED` impedisce a qualunque filtro di scendere nei rami.

| Fatto datato, dbdev come app | Tempo |
| --- | --- |
| archi grezzi dell'intero grafo (231) | ~125-140 ms |
| nodi di tutti i documenti (474) | ~41 ms |
| vista intera | ~190 ms |
| vista filtrata su un nodo | ~351 ms (peggio dell'intera) |
| funzione, anche su un nodo senza archi | ~0,6-0,8 s |

### 5.2 Primo passo — `20_code/vendite/20261010-44-update-fn-documento-lineage-grafo-una-volta`

La vista si legge una volta in una CTE `MATERIALIZED` `archi` dentro la
funzione, e la ricorsione attraversa la copia. Nient'altro cambia: firma,
`RETURNS TABLE` con i suoi `%TYPE`, controlli dei parametri, guardia dei cicli,
ordinamento. Numero preso nel buco (`-44`): la coda del giorno la usa un'altra
sessione.

Prove (2026-10-10):

* **equivalenza su dbdev come app**, copia `pg_temp` della funzione: tutti i
  **339** casi del grafo (ogni nodo con archi, nelle due direzioni), righe
  identiche — 708 per parte, `EXCEPT ALL` a zero nei due versi; tempo
  **283 s → 60 s** (~836 → ~177 ms a chiamata). Il corpo del changeSet è
  identico (normalizzato) a quello provato;
* il corpo di partenza (`20260829-02`) verificato uguale al corpo vivo;
* **scratch**, SQL estratto: i 5 pgTAP che toccano la lineage identici prima e
  dopo, tutti verdi (`test-documento-lineage-v1` 47/47 sui grafi che costruisce);
  avanti e indietro: definizione identica (md5), `GRANT` all'app conservato.

**Dopo l'apply** (2026-10-10, dbdev come app, sulla funzione vera): nodo senza
archi **~0,8 → ~0,19 s**; 40 nodi con archi 6,7 s, cioè ~0,17 s a chiamata.

### 5.3 Secondo passo, da decidere

~0,18 s è il costo di costruire **l'intero** grafo una volta. Per scendere ai
millisecondi la funzione deve costruire solo gli archi del nodo chiesto: archi
**seminati per chiave** (la forma della partita merce), un cantiere vero —
la vista degli archi è letta anche dalle liste (`vw_documento_lineage`, la
colonna della lineage nelle liste). Decisione attesa: **D-6**.

➡️ **D-6 è diventata un brief suo** (2026-10-10, su richiesta di Tid):
[brief-db-lineage-seminata-per-chiave](brief-db-lineage-seminata-per-chiave.md).
Il censimento ha mostrato che lo stesso costo lo paga **ogni pagina di sette
liste** (~0,42 s), e che la **D-5** di questo brief (lista offerte letta per id)
è lo stesso difetto: anche D-5 passa di là.

## 5bis. D-3 — la misura del ciclo di accredito (2026-10-11, dbdev come app)

Metodo: N chiamate di `vendite.fn_accredita_riga_reso` sulla sola riga in coda
(15922, una riga di ponte per chiamata), ciascuna in sottotransazione annullata;
la plancache della sessione sopravvive al rollback. Script nello scratchpad della
sessione (`misura-d3-*.sql`), tutto in `BEGIN … ROLLBACK`.

| Cosa, ms/chiamata | `auto` | generico | Nota |
| --- | --- | --- | --- |
| guard da solo, `fn_resi_riga_tetti_accredito` | 7,1 | 1,5 | 4,8× |
| la coda letta **come la legge il verbo** (stessa forma plpgsql) | 27 | 12 | 2,2× |
| copia `pg_temp` del guard: la clausola **sulla funzione SQL DEFINER**, sessione in `auto` | 30 | 15,6 | in PG18 la clausola su una SQL non incorporata funziona (la copia gira come app, sotto RLS: conta il rapporto, non il valore) |
| **verbo intero**, generico di sessione (= la clausola sul verbo) | 119-126 | 115-120 | ~5% |

Copia `pg_temp` del verbo (INVOKER, risultato identico alla vera), col generico
acceso **solo** attorno a una istruzione, due corse in ordine mescolato:

| Variante | ms/chiamata |
| --- | --- |
| tutto `auto` | 123-126 |
| generico solo sulla lettura della coda | 117-118,5 |
| generico solo sull'`INSERT` del ponte (guard e trigger della tabella) | **132-137** — peggio |
| generico su coda + `INSERT` | 117-120 |
| tutto generico | 118-119 |

Cosa dice:

* il difetto c'è **su entrambe le istruzioni** prese da sole: nel guard e
  nella lettura della coda;
* il verbo costa ~115 ms **altrove**, non nella pianificazione: le due cure
  insieme ne tolgono ~5-7;
* il generico acceso su tutta la finestra dell'`INSERT` del ponte **peggiora**
  il verbo: qualche istruzione di quel percorso (guard, trigger della tabella)
  sta meglio coi piani personalizzati. ⇒ La clausola non va sul **trigger**.
  La clausola su `fn_resi_riga_tetti_accredito` invece si applica solo alle
  query di quella funzione (il GUC torna com'era all'uscita), e lì il difetto
  è misurato.

**D-3a** ✅ **decisa da Tid (2026-10-11)**: la clausola va **solo** su
`fn_resi_riga_tetti_accredito`, nel changeSet `20261011-42`; sul verbo no.

**D-3a scritta (2026-10-11)**: `20_code/vendite/20261011-42-alter-fn-resi-riga-tetti-accredito-piano-generico`
(`ALTER FUNCTION … SET plan_cache_mode`; rollback `RESET plan_cache_mode`).
Presidio unico `db/pgtap/script/test-plan-cache-mode-piano-generico-v1.sql` (plan 5:
le tre funzioni, più il contratto della capability e il fail-closed dei tetti);
`test-fn-available-actions-ddt-piano-generico-v1` è **ritirato** (i commenti di
`-83/-84`, già applicati, lo nominano ancora: l'intestazione del nuovo dice che lo
sostituisce). Nota nelle pagine `manual/` delle tre funzioni.
Prova sullo scratch `zeroerp_ci`, da owner, SQL estratto: precondition 1; presidio
**senza** il `-42` 4/5 (rosso solo il 4, cioè vede il difetto), **con** il `-42` 5/5;
andata e ritorno: definizione identica (md5), `GRANT` conservati. ✅ **Applicato** da Tid
(2026-10-11, `EXECUTED` nel `databasechangelog` di dbdev). Dopo l'apply, su dbdev come app:
presidio 5/5; la funzione vera in sessione `auto` 1,9 ms a chiamata (prima 7,1). Sul verbo toglierebbe i ~6 ms
della coda, ma imporrebbe il generico a **tutto** il verbo, compresa la finestra
dell'`INSERT` dove la misura lo mostra peggiore: nasconderebbe quel peggioramento
invece di mostrarlo.
**D-3b** (decisione attesa): dove vanno i ~115 ms del verbo, da profilare come
query (nessun `auto_explain` come app: si fa per istruzione, a mano).

## 6. Cosa resta — indice per chi riparte (aggiornato al 2026-10-11)

| Voce | Cosa | Stato | Dove |
| --- | --- | --- | --- |
| D-1 | censimento delle funzioni che ripianificano | ✅ fatto | §4 |
| **D-2** | il lister dei DDT **senza filtri** (~1,1 s, diagnosi di tutti i DDT in una chiamata): profilarlo come query | ⬜ **aperto**, decisione attesa: ora o col volume | §2.2 |
| **D-3** | resi: misurare un ciclo di accredito **costruito** (in transazione annullata) e, clausola `plan_cache_mode` **solo** su `fn_resi_riga_tetti_accredito` (D-3a: non sul verbo né sul trigger, §5bis). Un solo changeSet, **numero riservato `20261011-42`** (in `20_code/vendite/`). Presidio: il pgTAP `test-fn-available-actions-ddt-piano-generico-v1` diventa `test-plan-cache-mode-piano-generico-v1` con le tre funzioni, e il vecchio si ritira nello stesso giro (decisione di Tid, 2026-10-11) | **D-3a** ✅ `20261011-42` applicato, presidio 5/5 su dbdev · **D-3b** ⬜ aperto (dove vanno i ~115 ms del verbo, da profilare per istruzione) | §4.3, §4.4, §5bis |
| D-4 | pannello «Passaggi», primo passo | ✅ `20261010-44` applicato e misurato | §5.2 |
| **D-5 + D-6** | lista offerte per id e lineage seminata (ogni pagina di sette liste paga il grafo intero) | 🔀 **nel brief figlio** — decisioni prese da Tid, giro 1 da iniziare | [brief-db-lineage-seminata-per-chiave](brief-db-lineage-seminata-per-chiave.md) §8 |

Il padre si archivia quando D-2 e D-3 sono chiuse; il figlio vive per conto suo.
