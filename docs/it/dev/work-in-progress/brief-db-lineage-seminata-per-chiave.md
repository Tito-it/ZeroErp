# Brief DB — La lineage dei documenti si costruisce per il documento, non per tutto il grafo

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-10. **A chi:** Tid; poi
> il team BE per le liste (§5.3), se la decisione D-2 lo coinvolge.
> **Origine:** D-6 di
> [brief-db-plancache-funzioni-con-query-incorporate](brief-db-plancache-funzioni-con-query-incorporate.md)
> §5.3: dopo `20261010-44` il pannello «Passaggi» costa ~0,18 s, ed è il costo
> di costruire il grafo intero. Censendo chi legge il grafo è emerso che lo
> stesso costo lo paga **ogni pagina di sette liste** (§2), e che la D-5 dello
> stesso brief (lista offerte letta per id) è lo stesso difetto.
> **Stato (2026-10-10):** ⬜ **aperto, non iniziato.** Decisioni di Tid del
> 2026-10-10: **D-1 sì, D-3 sì, D-4 sì** (prima il pannello, poi le liste — §6).
> **D-2 = B** (le liste chiedono la lineage per gli id della pagina, §5.2).
> Piano in §8 (accorciato a giri A e B). **2026-10-11**: ✅ giro 1 chiuso (`20261011-62…-67`); ✅ giro A chiuso (`20261011-92…-94`, §8.5). Prossimo: giro B (DB + BE insieme).
> **Ricadute BE/FE:** dipendono da D-2 (§5.3). Nessuna se si sceglie la forma
> che resta tutta nel DB.

## 1. Il difetto, sul modello

Il grafo della genealogia dei documenti (preventivo → ordine → DDT → commessa →
fattura, offerta → contratto, resi, note di credito: 13 tipi di arco) vive in
due viste e una funzione:

| Oggetto | Cosa fa | Chi lo legge |
| --- | --- | --- |
| `vendite.vw_documento_lineage_nodi` | un nodo per documento di ogni tipo, con stato, fase, natura, codice | le due sotto |
| `vendite.vw_documento_lineage_archi` | **tutti** gli archi del sistema, 13 rami in `UNION ALL`, decorati con i nodi (CTE `MATERIALIZED`) | `fn_documento_lineage`, `vw_documento_lineage`, `script.fn_check_preventivo_annullabile` |
| `vendite.vw_documento_lineage` | per **ogni** documento: frontiera a valle, radice a monte, pratica, discendenti — cioè la chiusura dell'intero grafo | le liste di preventivi, offerte, ordini, DDT, resi, contratti, fatture (colonne della lineage) |
| `vendite.fn_documento_lineage` | la catena di **un** documento (pannello «Passaggi») | backend, `lineage_views.py` |

⛔ **Tutto è costruito «per l'intero grafo»**: chi chiede un documento paga tutti
i documenti. Il recinto `MATERIALIZED` (giusto per una lettura intera,
`20261005-20`) impedisce a qualunque filtro di scendere. Il costo quindi cresce
con il numero di documenti del sistema, non con quelli che servono: oggi è
mezzo secondo, in esercizio sarà ciò che pesa di più sulle liste.

## 2. Le misure — fatti datati

Dbdev, come app (`zeroerp_app` + contesto operatore), 2026-10-10, dopo `20261010-44`.

| Lettura | Tempo |
| --- | --- |
| `vw_documento_lineage_nodi` intera (477 nodi) | ~41 ms |
| archi grezzi dell'intero grafo (231) | ~125-140 ms |
| `vw_documento_lineage_archi` intera | ~190 ms |
| `vw_documento_lineage` intera (chiusura) | **~436 ms** |
| lista preventivi / offerte / ordini / DDT / fatture, una pagina da 25 | **~417-421 ms ciascuna** |
| lista offerte filtrata per **un** id | ~411 ms |
| `fn_documento_lineage`, un documento (anche senza archi) | ~0,18-0,19 s |
| capability del preventivo (legge gli archi in un ramo) | ~26 ms |

Il costo di una pagina di lista **è** il costo della chiusura dell'intero grafo.

## 3. Cosa c'è già per una forma seminata

Ogni passo di una lineage costruita «dal documento» deve essere una ricerca per
indice, nelle due direzioni. Censimento delle colonne di join dei 13 rami
(2026-10-10):

| Ramo | Colonna di partenza | Indice |
| --- | --- | --- |
| A preventivo → ordine | `ordini(documento_origine_tipo, documento_origine_id)` | ⛔ **solo per le offerte** (`uq_ordini_v_documento_origine_offerta`, parziale): manca per il preventivo |
| D offerta → ordine | idem | ✅ |
| B/E/F/U → commessa | `commesse_sorgenti(sorgente_tipo_id, sorgente_uid)` | ✅ `uq_commesse_sorgenti_src_uid` |
| commessa ← | `commesse_sorgenti(commessa_id)` | ✅ |
| C offerta → contratto | `contratti(offerta_id)` | ✅ |
| G commessa → fattura | `attivita_fatturabili(commessa_id)`, `(fattura_riga_id)`, `fatture_righe(fattura_id)` | ✅ |
| H ordine → DDT | `ddt(sorgente_tipo_id, sorgente_uid)` | ✅ `ix_ddt_v_sorgente` |
| R DDT → reso | `resi(sorgente_tipo_id, sorgente_uid)` | ✅ `ix_resi_sorgente` |
| N fattura → nota | `fatture_righe(riga_rettificata_id)` | ✅ |
| S reso → fattura, T reso → DDT | `resi_righe_accrediti`, `resi_righe_riconsegne`, `resi_righe(reso_id)`, `ddt_righe(ddt_id)` | ✅ |
| nodi per chiave | `uid` di preventivi, offerte, ordini, DDT | ✅ |

Un solo indice mancante, e sul modello: un ordine che nasce da un preventivo si
cerca per il preventivo esattamente come uno che nasce da un'offerta.

## 4. La forma proposta per il grafo

Lo schema è quello già usato per la partita merce
(`fn_af_merce_per_riga` / `vw_af_merce_per_riga`, linee-guida-sql §8.5-bis):

* **`vendite.fn_documento_lineage_archi(<seme>)`** — gli archi **incidenti** ai
  nodi del seme (in uscita e in entrata), ogni ramo scritto nella forma che parte
  dalla chiave per indice; seme `NULL` = tutti gli archi, in un ramo `UNION ALL`
  a parte (mai `p IS NULL OR`). Archi **grezzi**: chiavi e tipo d'arco, senza
  decorazione.
* **`vendite.fn_documento_lineage_nodi(<seme>)`** — i nodi del seme, decorati
  (stato, fase, natura, codice), letti per chiave.
* ⭐ **Regola del 2:** le due viste di oggi diventano le **proiezioni** delle due
  funzioni col seme `NULL` (più la decorazione degli archi). Una sola grammatica
  dei 13 archi, non due.
* **`fn_documento_lineage`** risale **per livelli**: frontiera → archi incidenti
  → frontiera successiva (al massimo 10 livelli, guardia dei cicli com'è), poi
  decora i soli nodi visitati. Atteso: millisecondi, proporzionali ai documenti
  della catena.

## 5. Le liste — la parte che decide il costo vero

### 5.1 Il vincolo

Le liste agganciano `vw_documento_lineage` con un `LEFT JOIN` per `(tipo, uid)`,
e il backend legge la pagina con `COUNT(*) OVER ()` sulla stessa query
(`offerte_repository`, e le gemelle): la colonna della lineage si valuta su
**tutte** le righe del filtro, non sulle 25 della pagina. Una lineage per riga,
semplicemente seminata, verrebbe pagata N volte.

### 5.2 Le strade

| | Cosa | Pro | Contro |
| --- | --- | --- | --- |
| **A** | La chiusura resta una vista, ma costruita dalle funzioni seminate col seme `NULL` | nessun cambiamento per BE/FE | il costo resta proporzionale al grafo: guadagna solo il fattore costante |
| **B** | Le colonne della lineage escono dalle viste di lista; il backend le chiede **dopo** la paginazione, per gli id della pagina (`fn_documento_lineage_sintesi(<id della pagina>)`) | costo proporzionale alla pagina; il conteggio non le tocca | lavoro BE su sette liste (§5.3); ordinare o filtrare per una colonna della lineage diventa un caso a parte |
| **C** | La sintesi (frontiera, radice, discendenti) diventa **dato persistito**, aggiornato dai trigger dei documenti quando nasce o cambia stato un arco | lettura di lista gratuita, ordinabile e filtrabile | è un dato derivato da tenere coerente: trigger su 13 tipi di arco, presidio di coerenza, bonifica iniziale |

### 5.3 Ricadute per strada

* **A**: nessuna.
* **B**: le sette liste del backend tolgono le colonne della lineage dalla query
  di pagina e le chiedono per gli id della pagina; il FE non cambia se il
  contratto della riga resta uguale. Da concordare col team BE.
* **C**: nessuna per BE/FE; tutto il peso è nel DB (trigger e presidio).

## 6. Decisioni

**Prese da Tid il 2026-10-10:** D-1 (la forma del §4), D-3 (l'indice per tutti i
tipi d'origine), D-4 (prima il pannello `fn_documento_lineage`, solo DB; poi le
liste); **D-2 = B** (le liste chiedono la lineage dopo la paginazione, per gli id
della pagina). Nessuna decisione aperta.

### 6.1 Il testo delle decisioni

* **D-1** — la forma del grafo del §4 (funzioni seminate + viste come proiezione,
  regola del 2). *Raccomandata.*
* **D-2** — le liste: **A**, **B** o **C** (§5.2). La mia raccomandazione è **B**
  se il backend è d'accordo (è la forma in cui il costo segue la pagina, e il
  dato resta calcolato e non duplicato); **A** come primo passo, se si vuole
  guadagnare subito senza toccare il backend.
* **D-3** — l'indice `ordini(documento_origine_tipo, documento_origine_id)` per
  tutti i tipi d'origine, non solo per le offerte (§3).
* **D-4** — l'ordine dei lavori: prima il pannello (`fn_documento_lineage`, solo
  DB) e poi le liste, o insieme.

## 7. Da sapere prima di cominciare

* La storia della lineage è nei brief archiviati
  `work-done/brief-db-lineage-residui-root-e-sorgente-ddt.md` e nel cantiere del
  2026-10-05 (`20261005-20`, il recinto `MATERIALIZED` delle liste).
* Presìdi che toccano la forma: `vendite/test-documento-lineage-v1` (47 test, su
  grafi costruiti), `vendite/test-colonne-lineage-liste-v1` (47).
* L'equivalenza si prova come oggi: per **ogni** nodo con archi, nelle due
  direzioni, righe della funzione nuova `EXCEPT ALL` quella vecchia, a zero nei
  due versi; e per ogni lista, le colonne della lineage prima/dopo.

## 8. Piano

| Giro | Cosa | Chi | Stato |
| --- | --- | --- | --- |
| 1 | `fn_documento_lineage_archi(<seme>)` e `fn_documento_lineage_nodi(<seme>)`; le due viste diventano la loro proiezione col seme `NULL` (regola del 2); indice `ordini(documento_origine_tipo, documento_origine_id)` per tutti i tipi (D-3) | DB | ✅ `20261011-62…-67` applicati (§8.3, §8.4) |
| **A** | `fn_documento_lineage` risale per livelli sulle funzioni seminate (il pannello «Passaggi», `20261011-93`) **e** `fn_documento_lineage_sintesi(<chiavi>)`, le colonne di `vw_documento_lineage` per le sole chiavi chieste (`20261011-94`), più la correzione degli archi trovata misurando (`20261011-92`); equivalenza su tutti i documenti per tutte e due | DB | ✅ `20261011-92…-94` applicati, pgTAP verdi (§8.5) |
| **B** | le viste di lista smettono di agganciare `vw_documento_lineage` **e insieme** le sette liste del backend chiedono la lineage a `fn_documento_lineage_sintesi` per gli id della pagina (§8.1); seed `ui.lista_colonna` e pgTAP delle colonne decisi insieme | DB + BE insieme | ⬜ |

⭐ **Piano accorciato (Tid, 2026-10-11)**: siamo solo in sviluppo, quindi i
giri 2-5 diventano **A** e **B**. Il 2 e il 3 sono due funzioni DB che non
cambiano contratti; il 4 e il 5 si fanno insieme, accettando qualche ora di
liste rotte in sviluppo invece di far aspettare il DB al backend.
ℹ️ `fn_ddt_legami`, il quarto lettore degli archi, non c'è più: ritirata in
`20261011-91` (brief-db-annullo-documento-con-legami).

### 8.2 Giro 1 — la forma (proposta, 2026-10-11)

Letti dal vivo (doc auto-gen): le due viste, `fn_documento_lineage` (forma
`20261010-44`) e i lettori degli archi. Oltre ai tre noti c'è un lettore nuovo,
`vendite.fn_ddt_legami`, che legge gli archi per **un** DDT: è il primo candidato
a passare alla funzione seminata, ma **non** in questo giro. Indici delle colonne
di join riletti da `pg_indexes`: confermato il §3, manca solo il ramo A.
> ℹ️ Nota del 2026-10-11 (brief-db-annullo-documento-con-legami, D-4): `vendite.fn_ddt_legami`
> si ritira (`20261011-91`), sostituita da `vendite.fn_documento_legami`. Nessuna delle due legge
> gli archi del lineage: leggono i legami riga per riga (fulfillment, ponti di ri-consegna, righe di
> commessa), quindi non sono candidate alla funzione seminata.

**Il seme è la chiave del nodo**: `(p_tipo_ids bigint[], p_uids text[])`, due
array paralleli, la coppia `(tipo_id, uid::text)` che il modello usa già come
identità polimorfa del nodo (`key_selector`: `uid` per preventivo e offerta, `id`
per gli altri). Il chiamante tipico è una **frontiera**, cioè un insieme misto di
tipi: con un array per tipo (la forma della partita merce, otto parametri) ogni
chiamante dovrebbe smistarla da sé.
Dentro, il seme si smista **una volta** in array tipizzati (`uuid[]`, `bigint[]`)
con `array_agg(…) FILTER (WHERE tipo = …)`. Il cast avviene solo sulle righe del
tipo giusto, e ogni ramo cerca per indice con `= ANY(<array tipizzato>)`. Il
confronto `id::text = uid` non entrerebbe nell'indice.
Seme `NULL` = tutto, in rami `UNION ALL` a parte (filtro una tantum), mai
`p IS NULL OR`.

| # | ChangeSet | Cosa |
| --- | --- | --- |
| 1 | `00_schema/vendite` create index | `ix_ordini_documento_origine (documento_origine_tipo, documento_origine_id) WHERE documento_origine_id IS NOT NULL`, **non** unico (D-3). L'unicità per l'offerta resta in `uq_ordini_v_documento_origine_offerta`; quella per il preventivo è una domanda di modello, fuori da qui |
| 2 | `20_code/vendite` create | `fn_documento_lineage_nodi(p_tipo_ids, p_uids)`, SQL `BEGIN ATOMIC`, `STABLE`, INVOKER: gli 8 tipi di nodo, ciascuno in due modi (seme / tutto) |
| 3 | `20_code/vendite` create | `fn_documento_lineage_archi(p_tipo_ids, p_uids)`: archi **grezzi** (`from_tipo_id, from_uid, to_tipo_id, to_uid, ruolo, arco`, più `is_ramo_inverso` e `rango_origine`, che dipendono solo dall'arco: una sede sola). Per ogni ramo, col seme: arco **uscente** da un nodo del seme `UNION ALL` arco **entrante** il cui `from` non sta nel seme. Così il multiinsieme è esattamente quello della vista ristretta agli archi incidenti, senza doppioni né `DISTINCT` nuovi |
| 4 | `20_code/vendite` update | `vw_documento_lineage_nodi` = proiezione di `fn_documento_lineage_nodi(NULL, NULL)`, colonne per nome coi typmod ricastati, `security_invoker=on` ripetuto |
| 5 | `20_code/vendite` update | `vw_documento_lineage_archi` = archi di `fn_documento_lineage_archi(NULL, NULL)` decorati coi nodi; stesse colonne, stessi tipi |

**Presidio**: pgTAP nuovo `vendite/test-documento-lineage-seminata-v1` su un grafo
**costruito** con i 13 archi. Controlla: archi col seme = archi della vista
incidenti al seme (`EXCEPT ALL` nei due versi), per un seme a un nodo, un seme
misto e un seme vuoto; seme `NULL` = vista intera; i tipi delle due viste
(`col_type_is`); le dipendenze in `pg_depend` (`BEGIN ATOMIC`).
**Prova** prima dell'apply, sullo scratch e su dbdev come app: equivalenza delle
viste prima e dopo su tutto il grafo, i 5 pgTAP della lineage identici, i tempi
delle viste intere non peggiori.

I lettori di oggi (`vw_documento_lineage`, `fn_documento_lineage`,
`fn_check_preventivo_annullabile`, `fn_ddt_legami`) **non** cambiano in questo
giro: leggono le viste, che restano uguali. Il guadagno arriva al giro 2.

### 8.3 Giro 1 — scritto, provato e ✅ applicato da Tid (2026-10-11)

| ChangeSet | Cosa |
| --- | --- |
| `00_schema/vendite/20261011-62-create-ix-ordini-documento-origine` | indice D-3 |
| `20_code/vendite/20261011-63-create-fn-documento-lineage-nodi` | nodi per chiave |
| `20_code/vendite/20261011-64-create-fn-documento-lineage-archi` | archi grezzi per chiave |
| `20_code/vendite/20261011-65-update-vw-documento-lineage-nodi-proiezione` | vista = proiezione |
| `20_code/vendite/20261011-66-update-vw-documento-lineage-archi-proiezione` | vista = proiezione decorata |

**pgTAP**: nuovo `vendite/test-documento-lineage-seminata-v1` (plan 16). Grafo
**costruito** con gli archi A, B, E, H, U (due preventivi, un ordine, una
commessa, un DDT); le altre otto lettere si provano su un arco vivo ciascuna,
con `skip()` dichiarato quando mancano (database da zero). Ritoccato
`config/test-costanti-catalogo-citate-dal-codice-v1`: le costanti
`RESO_VENDITA` e `DDT_VENDITA` della lineage ora stanno nella funzione degli archi
e non nella vista, e il test 4 legge anche i corpi `BEGIN ATOMIC` (`prosrc` è
vuoto: il corpo lo dà `pg_get_function_sqlbody`). ⚠️ Prima dell'apply quel
file è **rosso** (cerca la funzione nuova): va applicato insieme al `-64`.

**Una correzione di forma trovata misurando** (2026-10-11, dbdev come app). La
prima versione passava il seme come JOIN, coi nodi del seme in CTE
`MATERIALIZED`. Sotto RLS il planner partiva dal lato sbagliato: leggeva la
tabella dell'altro capo per il solo prefisso del tipo, pagando una policy per
riga, e metteva il seme in fondo. Nella forma adottata una CTE `chiavi` porta il
seme in tutte le forme che i rami cercano, e la prima tabella di ogni metà è
limitata con `= ANY(<chiavi>)` sul suo indice. Con `enable_seqscan = off` ogni
metà col seme parte da un indice (il ramo A dal `-62`).

**Prove**:

* equivalenza (copie `pg_temp`, dbdev come app): `fn(NULL, NULL)` = viste;
  ognuno dei 477 nodi come seme = gli archi della vista incidenti a lui; le due
  estremità di ognuno dei 232 archi = gli archi incidenti alla coppia; seme con
  tutti i nodi = vista; tipi delle colonne delle viste identici (typmod
  compresi);
* scratch `zeroerp_ci`, da owner, SQL estratto dei cinque changeSet: **70 pgTAP**
  (lineage, lettori, presidi su viste, funzioni SQL e `security_invoker`), prima
  e dopo: identici tranne quello delle costanti, ritoccato sopra; il pgTAP nuovo
  16/16 (il 15 è uno `skip()`: lo scratch non ha quelle lettere); su dbdev come
  app 16/16 col 15 eseguito;
* il pgTAP nuovo vede il difetto: togliendo l'esclusione delle entranti dal
  ramo A, il test 11 diventa rosso.

**Fatti datati** (dbdev come app, 2026-10-11): vista degli archi intera
~170 ms di esecuzione contro ~180 di prima, ma **~+30 ms fissi di
pianificazione** (il corpo è più grande). Non crescono coi dati, e dal giro 5 le
liste non leggono più il grafo intero. Un nodo come seme: ~10 ms in piano
generico, dovuti alle tabelle minuscole di dbdev (il planner legge per intero
tabelle da 5-10 righe). Su tabelle grandi conta che ogni ramo parta da un
indice, ed è verificato. ⚠️ Il costo di pianificazione e il JIT li ha risolti
il §8.4.

### 8.4 Il JIT — `20261011-67` (2026-10-11), ✅ applicato da Tid, pgTAP risolto

**Trovato da Tid** dopo l'apply: `test-documento-lineage-seminata-v1` lento,
**anche sullo scratch vuoto**. La causa sono i test 10 e 15, che chiamano la
funzione con un seme preso dalla riga esterna. Quando il seme **non è una
costante** il planner non può togliere i rami dell'altro modo, il costo stimato
del piano supera le soglie del JIT, e la compilazione costa più della query, a
ogni esecuzione. Non dipende dai dati ma dalla grandezza del piano: un chiamante
vero (plpgsql, parametri) lo pagherebbe uguale, e su tabelle grandi di più.
Fatto datato (dbdev come app): ~4,8 s a chiamata col JIT, 25 ms senza.

**Cura**: `ALTER FUNCTION … SET jit = off, SET plan_cache_mode =
force_generic_plan` sulle due funzioni. Una clausola `SET` le rende non
incorporabili: si pianificano dentro di sé, una volta per sessione (in PG18 il
piano di una funzione SQL sta nella plancache). Le viste non si ricreano.
Copie `pg_temp` con le due clausole, dbdev come app: vista degli archi ~155 ms
(prima ~210 compresa la pianificazione), vista dei nodi ~39 ms, un nodo ~11 ms,
equivalenza a zero; il pgTAP nuovo da >40 s a 1,7 s (scratch 0,6 s). COMMENT
vivi conservati, con la nota di revisione davanti; presidio unico della clausola
esteso (`script/test-plan-cache-mode-piano-generico-v1`, test 6-7, plan 7).
⇒ **giro 2**: `fn_documento_lineage` non deve dichiarare niente per la funzione
che chiama.

### 8.5 Giro A — scritto, provato e ✅ applicato da Tid, pgTAP verdi (2026-10-11)

| ChangeSet | Cosa |
| --- | --- |
| `20_code/vendite/20261011-92-update-fn-documento-lineage-archi-join-leakproof` | archi per chiave: nei rami B, E, F, U il join verso il documento diventa leakproof |
| `20_code/vendite/20261011-93-update-fn-documento-lineage-per-livelli` | il pannello risale la catena un livello alla volta |
| `20_code/vendite/20261011-94-create-fn-documento-lineage-sintesi` | le 28 colonne di `vw_documento_lineage` per i soli documenti chiesti |

**Trovato misurando il pannello: il `-92`.** Nei rami polimorfi verso la
commessa (B, E, F, U) la chiave del documento sta come testo in
`commesse_sorgenti.sorgente_uid`, e il join la convertiva
(`p.uid = cs.sorgente_uid::uuid`). Un cast non è leakproof, e sotto RLS entra
nell'indice solo una clausola leakproof (linee-guida-sql §8.5-bis): per ogni
sorgente il planner leggeva l'intera tabella dell'altro capo. Fatto datato: una
commessa con 32 preventivi, ~270 ms; anche con `enable_seqscan = off` l'indice
veniva letto per intero, senza Index Cond. Cresce con le sorgenti per commessa e
con la tabella del documento. Cura: una CTE `cs_semi` legge una volta le sorgenti
delle commesse del seme con la chiave già convertita, e il join diventa un
confronto fra colonne dello stesso tipo (Index Cond `uid = cs.k_uuid`, ~30 ms).
Nelle metà uscenti il nodo si limita anche con `= ANY(<chiavi>)`.

**Il pannello (`-93`)** fa una chiamata agli archi per livello, con seme = i nodi
correnti di tutti i percorsi aperti, e decora una volta sola alla fine. La
semantica è quella di prima: percorsi, guardia dei cicli sul percorso (assente al
livello 1), 10 livelli, stesso `ordine`.

**La sintesi (`-94`)** è la regola di `vw_documento_lineage` costruita per
livelli dai nodi del seme. Il seme è **obbligatorio**: la sintesi di tutti i
documenti resta la vista. ⛔ Fino al giro B la regola sta in due posti: lo dice
l'intestazione della funzione, e il pgTAP le confronta (test 19-20). Il giro B
ritira la vista, quando liste e drawer leggono dalla sintesi. Il drawer la legge
oggi per **un** documento (`vendite_repository`, `WHERE l.tipo_id = %s AND l.uid
= %s`), pagando l'intero grafo.

**Prove** (2026-10-11, dbdev come app, copie `pg_temp`; scratch da owner, SQL
estratto):

* archi riscritti: equivalenza completa come al §8.3, a zero;
* pannello: ognuno dei 477 nodi nelle due direzioni (954 casi, 710 righe per
  parte), `EXCEPT ALL` a zero, `ordine` compreso;
* sintesi contro la vista: i 477 nodi in un seme solo, ognuno da solo, a pagine
  da 25: a zero. Colonne non banali nel campione: 162 frontiere diverse dal nodo,
  153 con sorgenti, 69 con pratica, 147 con discendenti attivi;
* pgTAP `test-documento-lineage-seminata-v1` ora a **plan 22**: 17-18 il pannello
  su un grafo costruito (le catene attese, verificate anche contro la forma di
  prima), 19-22 la sintesi. Scratch 22/22 in 0,6 s, dbdev come app 22/22 in 2,3 s;
* scratch, prima e dopo: 71 pgTAP della regressione larga (col `-92/-93`) e i
  presidi trasversali col `-94` (catalogo errori, rubinetto, costo delle policy,
  `ROWS` delle SRF, RLS delle viste, i due della lineage, plancache):
  identici; `plpgsql_check` a zero errori sulle due funzioni plpgsql;
  riferimenti morti 9/9.

**Fatti datati** (dbdev come app):

| Lettura | Prima | Dopo |
| --- | --- | --- |
| pannello, media su 954 casi | ~154 ms | ~16 ms (max ~88) |
| una pagina da 25, colonne di lineage | ~420 ms (vista) | ~58 ms (max ~108) |
| un documento (drawer) | ~300 ms (vista) | ~17 ms |

⇒ **Giro B**: le sette liste e il drawer chiedono la lineage a
`fn_documento_lineage_sintesi` per le sole chiavi della pagina (o del documento),
le viste di lista smettono di agganciare `vw_documento_lineage`, e la vista si
ritira. Seed `ui.lista_colonna`, ordinamento e filtri per una colonna della
lineage, e i pgTAP che oggi leggono la vista (`test-documento-lineage-v1`,
`test-colonne-lineage-liste-v1`) si decidono insieme (§8.1).

### 8.1 Richiesta al team BE (giro 4) — da consegnare quando il giro 3 è applicato

* Le liste di preventivi, offerte, ordini, DDT, resi, contratti, fatture leggono
  oggi le colonne della lineage dalla vista di lista (che le aggancia da
  `vw_documento_lineage`), e contano il totale con `COUNT(*) OVER ()` sulla
  stessa query: la lineage si calcola per **tutte** le righe del filtro.
* Dopo il giro 3: la query di pagina (e il conteggio) **senza** le colonne della
  lineage; poi una chiamata `fn_documento_lineage_sintesi(<le chiavi della
  pagina>)` e l'unione per `(tipo, uid)`. Il contratto della riga verso il FE
  resta uguale.
* ⚠️ Ordinare o filtrare per una colonna della lineage (frontiera, fase della
  frontiera…) non si può più fare nella query di pagina: va censito quali liste
  lo offrono oggi, e deciso caso per caso.
* Il giro 5 (DB) parte solo a giro 4 consegnato.
