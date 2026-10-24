# Brief DB — Dove si addebita il trasporto di un ordine fatturato alla conferma

## ⏭️ Chi riparte — aggiornato al 2026-10-13

**Riparte: Tid**, con le decisioni del §4. Cantiere aperto, non iniziato.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | decisioni T-1…T-3 | §4 | — |
| 2 | DB | analisi della forma scelta e consegna | — | 1 |
| 3 | BE/FE | da definire dopo la forma | — | 2 |

Decisioni aperte di Tid: §4. Lavoro da committare: solo questo documento.

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-13. **A chi:** Tid, poi il team DB.
> **Origine:** decisione A-9 di Tid (2026-10-12) in
> [brief-db-articoli-ammessi-per-documento](../work-done/brief-db-articoli-ammessi-per-documento.md) §8.6:
> il caso esce da quel brief e si progetta qui.

## 1. Il caso

Un ordine di vendita si fattura in due modi (`vendite.ordini.fatturazione_trigger`):

* **alla consegna**: la bolla porta la merce in una commessa (`vendite.fn_ddt_push_diagnosi`), e
  in commessa si aggiungono servizi e addebiti, compreso il trasporto, con la porta degli oneri
  (`vendite.fn_aggiungi_onere_commessa`);
* **alla conferma**: si fattura dall'ordine, e la commessa non c'è (`DDT_FATTURA_DA_ORDINE`: la
  bolla non transita mai in commessa).

Con le regole del brief d'origine (D-1, D-2) l'ordine e la bolla ammettono **solo merce**. Nel
secondo caso, quindi, un trasporto da far pagare al cliente non ha un posto.

## 2. I fatti di struttura (2026-10-13)

* **Il trasporto sulla bolla è un dato di testata**, non una riga: `vendite.ddt.causale_trasporto_id`,
  `vendite.ddt.modalita_addebito_trasporto_id`.
* **Fra le causali onere non c'è il trasporto** (seed `80_data/sql/config/causali_onere.csv`:
  senza contratto, trasferta, urgenza, spese amministrative, penale).
* **L'articolo-onere** (`catalogo.articoli.causale_onere_id`, 1:1 con la causale) ha la natura di
  default, che è `MERCE` (`natura_vendita_id NOT NULL DEFAULT 1`), con `e_cessione_beni = true`.
  Nessun vincolo lo impedisce. Il vincolo «un articolo-onere non è MERCE» lo introduce il brief
  d'origine (A-9); questo brief lo dà per fatto.

## 3. Le strade (da valutare, nessuna scelta qui)

| | Forma | A favore | Contro |
| --- | --- | --- | --- |
| **a** | articoli-onere ammessi sulle righe d'ordine, come eccezione a «solo merce» | nessun dato nuovo | porta gli oneri su un documento che oggi non li conosce; la riga d'ordine si evade a magazzino, l'onere no |
| **b** | importo (o articolo) di trasporto sulla testata dell'ordine, aggiunto dalla fatturazione | il trasporto è un dato di testata anche sulla bolla | tocca testata, totali e fattura |
| **c** | l'ordine con trasporto si fattura alla consegna (via commessa) | nessuna modifica al modello | è un limite operativo, non una soluzione: va almeno scritto in guida |

## 4. Da decidere (Tid)

| # | Domanda |
| --- | --- |
| **T-1** | Quale delle strade del §3 (o un'altra)? |
| **T-2** | La causale onere «trasporto» va aggiunta al catalogo? |
| **T-3** | La modalità di addebito del trasporto della bolla (franco, assegnato…) deve guidare l'addebito anche sull'ordine? |
