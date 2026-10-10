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
> Piano in §8.
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
| 1 | `fn_documento_lineage_archi(<seme>)` e `fn_documento_lineage_nodi(<seme>)`; le due viste diventano la loro proiezione col seme `NULL` (regola del 2); indice `ordini(documento_origine_tipo, documento_origine_id)` per tutti i tipi (D-3) | DB | ⬜ |
| 2 | `fn_documento_lineage` risale per livelli sulle funzioni seminate (il pannello «Passaggi»); equivalenza su ogni nodo con archi, nelle due direzioni | DB | ⬜ |
| 3 | `fn_documento_lineage_sintesi(<chiavi>)`: le colonne di `vw_documento_lineage` (frontiera, radice, pratica, discendenti, natura) per le sole chiavi chieste; equivalenza contro la vista su tutti i documenti | DB | ⬜ |
| 4 | le sette liste tolgono le colonne della lineage dalla query di pagina e le chiedono con il giro 3 per gli id della pagina | BE (§8.1) | ⬜ |
| 5 | le viste di lista smettono di agganciare `vw_documento_lineage` — **solo dopo** il giro 4, o la lista perde le colonne | DB | ⬜ |

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
