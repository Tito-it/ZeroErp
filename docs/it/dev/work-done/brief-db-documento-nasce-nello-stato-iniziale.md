# Brief DB — Un documento nasce nel suo stato iniziale

## ⏭️ Chi riparte — aggiornato al 2026-10-25

✅ **Archiviato il 2026-10-25** (V-3 di Tid, [brief-modello-documento-vendita](brief-modello-documento-vendita.md)
§8.11). Confluito in quel brief il 2026-10-24 (§4-bis, M-6): N-1 … N-3 decise là e costruite nel
primo giro (`20261024-07` … `-25`, §4-quinquies: `script.trgfn_doc_stato_iniziale` montato sulle
testate di vendita e d'acquisto, `E_DOC_STATO_INIZIALE_NON_VALIDO`). Nessuno riparte da qui. La
tabella qui sotto e' superata; il caso e la prova (§1) restano come storia.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | decisioni N-1…N-3 | §4 | — |
| 2 | DB | censimento degli scrittori che inseriscono fuori dallo stato iniziale, poi la consegna | §3 | 1 |
| 3 | BE | solo se il censimento trova un INSERT del backend fuori dallo stato iniziale | — | 2 |

Decisioni aperte di Tid: nessuna. Lavoro da committare: lo spostamento in `work-done/`.

📌 Il tipo di documento si nomina secondo
[brief-db-grammatica-unica-documenti](../work-done/brief-db-grammatica-unica-documenti.md) (§6.1): se questo
cantiere introduce un registro o un parametro per tipo di documento, usa i codici di
`config.sorgenti` (G-1) e parte **dopo il lotto 0** di quel brief (G-4, Tid 2026-10-18).
✅ Il lotto 0 è chiuso (2026-10-19, §8 di quel brief), e dal lotto 2a anche i lettori delle testate
parlano i codici di `config.sorgenti`: da quel lato questo cantiere può partire.

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-13. **A chi:** Tid, poi il team DB.
> **Origine:** trovato verificando `trg_ddt_a10_gen_numero_emesso_upd` nel giro del `20261013-53`
> (la bolla generata da un ordine nasceva senza magazzino). Registro: **D32** di
> [migliorie-generali-da-test-valutazione](../work-in-progress/migliorie-generali-da-test-valutazione.md).

## 1. Il caso

Le regole che un documento deve rispettare per **uscire dalla bozza** stanno tutte sul passaggio di
stato, cioè su un `UPDATE`:

* bolla: `trg_ddt_a10_guard_transizione_upd` (grafo degli stati, `script.fn_check_ddt_emittibile`
  con righe, causale, magazzino e merce, la porta del verbo `vendite.fn_cambia_stato_ddt` che scrive
  lo scarico), `trg_ddt_a10_guard_indirizzi_obbligatori_upd`, `trg_ddt_a10_guard_causale_emissione_upd`;
* le altre famiglie hanno la stessa forma: `trg_<doc>_a10_guard_transizione_upd` è `BEFORE UPDATE`
  su ordini, preventivi, resi, contratti, offerte e commesse (doc auto-generata, 2026-10-13).

**Nessuna regola dice in che stato un documento può NASCERE.** Un `INSERT` con lo stato già avanti
salta il grafo e tutte le condizioni dell'uscita dalla bozza.

### Provato sulla bolla (scratch `zeroerp_ci`, transazione annullata, 2026-10-13)

Una bolla da ordine inserita direttamente in `EMESSO`, senza righe, indirizzi né causale:

* **senza il `20261013-53`** muore con un errore TECNICO (`E_VENDITE_CHIAMATA_NON_VALIDA`): il
  numeratore riceveva l'emittente NULL. Il rifiuto c'era **per caso**, e solo per le bolle con un
  ordine come sorgente;
* **con il `20261013-53`** nasce **EMESSA e numerata** (`DDT2026-0000001`) con zero righe. Dopo non
  si può più correggere: le righe di una bolla fuori bozza non si aggiungono
  (`trgfn_doc_righe_lock_fuori_bozza`). Resta un documento fiscale vuoto, con un numero consumato.

Una bolla senza ordine, con l'emittente esplicito, nasceva emessa già prima del `-53`: il buco non
l'ha aperto il `-53`, ha solo tolto il rifiuto casuale per le bolle da ordine.

## 2. Il modello

Lo stato iniziale di ogni famiglia è scritto nel suo vocabolario (`config.stati_doc_*`: `DRAFT` per
bolla e ordine, …) e nel grafo delle transizioni (`config.transizioni_stati_*`). Un documento che
nasce in uno stato diverso è una transizione dal nulla che nessun grafo ammette.

⚠️ Ci sono nascite legittime fuori dalla bozza? Vanno **censite dagli scrittori** (corpi delle
funzioni, backend, pgTAP), non presunte: per esempio una nota di credito generata, una commessa
creata già attiva, i resi che nascono confermati. Il censimento decide la forma, non il perimetro.

## 3. Censimento da fare (DB)

1. Per ogni famiglia con `guard_transizione`: chi fa `INSERT` con uno stato diverso dall'iniziale
   (funzioni in `pg_proc.prosrc`, `backend/`, `db/pgtap/`).
2. Per le famiglie numerate alla nascita o al passaggio (`gen_numero` su bolla, ordine, reso): il
   trigger del numero, all'INSERT, deve leggere colonne già risolte. Sulla bolla lo è dal `-53`; sul
   reso `trg_resi_a10_gen_numero_ins_upd` viene prima di `trg_resi_normalize_ins_upd` (da verificare
   se il reso eredita lì qualcosa che il numero legge).
3. I pgTAP che oggi inseriscono un documento già avanti per comodità di fixture: con un guard nuovo
   diventerebbero rossi, e vanno portati su `dbops.fn_pgtap_porta_a_stato`.

## 4. Decisioni di Tid

* **N-1 — La regola.** (a) un documento nasce solo nello stato iniziale, e il resto passa dal grafo
  (un guard `BEFORE INSERT` per famiglia, o un building block unico con lo stato iniziale letto dal
  vocabolario); (b) all'INSERT si applicano le stesse condizioni della transizione dall'iniziale
  allo stato chiesto. Consiglio (a): è la forma più stretta, e le eccezioni passano da un verbo.
* **N-2 — Il perimetro del primo giro.** Tutte le famiglie con `guard_transizione`, o la sola bolla
  (l'unica provata) con le altre in un secondo giro. Consiglio tutte: la regola è la stessa
  (regola del 2).
* **N-3 — Il codice.** Un codice nuovo comune (`E_DOC_NASCE_FUORI_BOZZA` o simile, `CONFLITTO_STATO`)
  o i codici di transizione esistenti di ogni famiglia.
