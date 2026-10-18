# Brief DB — Una sola grammatica per i tipi di documento

## ⏭️ Chi riparte — aggiornato al 2026-10-18

**Riparte: il team DB, col censimento del §4.** La direzione è decisa (Tid, 2026-10-18: un
vocabolario solo, nessun ponte); la forma la decide Tid sul censimento.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ **Tid** | Direzione: una grammatica sola per tutti i tipi di documento (la strada 3 dell'A-8-ter) | §2 | — |
| 2 | **team DB** | Censimento: i vocabolari, chi li parla, chi traduce, cosa manca a ciascuno | §4 | — |
| 3 | **Tid** | Decisioni G-1 … G-4 sul censimento | §5 | 2 |
| 4 | team DB | Il piano a lotti e i changeSet | — | 3 |
| 5 | sessione BE/FE | Il ritiro delle traduzioni del backend nello stesso giro di ciascun lotto | §3.2 | 4 |
| 6 | chi chiude | Il ritiro del ponte di `fn_articolo_riga_contesto`, l'archiviazione, la riga di PROJECT_CONTEXT | — | 5 |

**Decisioni aperte di Tid:** G-1 … G-4 (§5), dopo il censimento. ✅ Documento committato su `dev/backend-tid` (`22e31580e`, 2026-10-18).

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-18. **A chi:** il team DB, poi Tid.
> **Origine:** l'A-8-ter di
> [brief-db-articoli-ammessi-per-documento §9.8.3](brief-db-articoli-ammessi-per-documento.md).
> Spostare tre funzioni del listino sul vocabolario delle entità moltiplicava i punti di
> traduzione invece di toglierli: il problema non è di tre funzioni, è della grammatica.

## 1. Il caso

Lo stesso concetto, «di che tipo di documento si parla», ha **più nomi** nel database e nel backend,
e chi passa da un vocabolario all'altro traduce. Quello che si vede già dal contratto (seed in
`80_data` e doc auto-generata, 2026-10-18 — struttura, non popolazione):

| Vocabolario | Dove | Esempi | Note |
| --- | --- | --- | --- |
| **entità** | `config.tipi_entita` (`80_data/sql/config/tipi_entita.csv`) | `PREVENTIVO`, `ORDINE_VENDITA`, `DDT_VENDITA`, `OFFERTA_COMMERCIALE`, `CONTRATTO`, `COMMESSA`, `FATTURA`, `LISTINO_VERSIONE`, `ARTICOLO`, `PROMO_ARTICOLO`… | lo parla il picker degli articoli ammessi e la check per tipo di riga. ⚠️ Non ha un reso |
| **sorgenti** | `config.sorgenti` (`sorgenti.csv`) | gli stessi codici delle entità per le testate (`OFFERTA_COMMERCIALE`, `DDT_VENDITA`, `RESO_VENDITA`…), più le righe (`*_RIGA`) e altri (`ATTIVITA`, `EVENTO_ASSET`, `DDT_VENDITA_PRELIEVO`…) | le note dei due cataloghi dicono già «codice identico» dove si intersecano |
| **testate** | `script.fn_get_stato_testata_documento`, `fn_get_testata_id_di_riga`, `fn_get_cliente_testata_documento`, `fn_doc_indirizzi_sede` e altri (27 pagine della doc auto-generata) | `DDT`, `ORDINE`, `CONTRATTO`, `OFFERTA`, `PREVENTIVO`, `RESO`, `COMMESSA`, `EMAIL_BOZZA` | lock fuori bozza, annullo con legami, indirizzi, lineage |
| **documenti con eccezioni** | `vendite.fn_documento_listino_operativo`, `fn_documento_righe_eccezione`, `fn_documento_righe_preview`, `script.fn_check_riga_erogazione`… (la famiglia del §9.8.3) | `OFFERTA`, `CONTRATTO` | un sottoinsieme della grammatica delle testate |
| **partizioni delle note** | `target_tipo` delle note (`varchar(16)`), `backend/apps/vendite/db/note_repositories.py` | `OFFERTA` | il commento del backend dice che `OFFERTA_COMMERCIALE` non ci sta per lunghezza: un vincolo di **colonna** che decide un nome |

Il **ponte** dichiarato oggi è uno: `script.fn_articolo_riga_contesto` traduce dalle entità alle
testate. Gli altri punti di traduzione non sono censiti.

## 2. La decisione presa

**Tid, 2026-10-18:** la soluzione è **una grammatica sola** per i tipi di documento, usata da tutto
il database e dal backend, senza ponti. Non è un debito da tenere: è la direzione. Si apre qui, fuori
dal brief degli articoli ammessi, perché tocca decine di oggetti che con gli articoli non c'entrano e
perché altri brief aperti lavorano sugli stessi oggetti (§6).

## 3. Che cosa si chiede

### 3.1 Al team DB: il censimento (§4), prima di ogni changeSet

Nessun changeSet finché Tid non ha deciso G-1 … G-4 sul censimento.

### 3.2 La ricaduta sul backend (per il piano, non ora)

Le traduzioni del backend vanno ritirate **nello stesso giro** del lotto DB che le rende inutili
(regola del 2). Quelle già note:

* `backend/apps/vendite/db/_documento_eccezioni_repo.py`: `DocumentoEccezioni = Literal["CONTRATTO", "OFFERTA"]`;
* `offerte_service.py`, `contratti_service.py`, che passano quei codici;
* `_annullo_con_legami.py`, che traduce `OFFERTA` nel codice delle sorgenti;
* `backend/apps/config/sorgenti.py` (le costanti `SORGENTE_*`) e `note_repositories.py` (le partizioni).

Il censimento le completa: cercare nel backend ogni letterale di tipo documento usato come chiave.

## 4. Il censimento (team DB)

Da leggere sul **contratto** (seed, doc auto-generata, firme e corpi delle funzioni, CHECK, enum),
mai sulle righe di oggi.

1. **I vocabolari.** Tutti quelli che nominano un tipo di documento (testata o riga): catalogo,
   enum, CHECK, colonne `varchar` con valori ammessi, letterali nei corpi delle funzioni. Per
   ciascuno: dove vive, chi è la fonte, quali codici ha.
2. **La matrice dei codici.** Per ogni tipo di documento, il suo nome in ciascun vocabolario
   (una riga per tipo, una colonna per vocabolario), con i **buchi**: per esempio il reso, che
   `config.tipi_entita` non ha, ed `EMAIL_BOZZA`, che vive solo nella grammatica delle testate.
3. **Chi parla cosa.** Per ogni funzione, trigger, vista e montaggio che riceve o confronta un tipo
   di documento: quale vocabolario usa, e se lo riceve da fuori o lo scrive come letterale.
4. **Chi traduce.** Ogni punto in cui un codice di un vocabolario diventa un codice di un altro (il
   ponte di `fn_articolo_riga_contesto` e gli altri), DB e backend.
5. **I vincoli che decidono un nome.** Colonne troppo corte (`target_tipo varchar(16)`), indici,
   chiavi di partizione, chiavi dei locales: ciò che oggi impedisce di usare il codice lungo.
6. **I confini.** Che cosa è «un tipo di documento» e che cosa no: le entità che non sono documenti
   (`TASK_RUN`, `FLUSSO`, `LOTTO`), le righe (`*_RIGA`), le varianti di un documento
   (`DDT_VENDITA_PRELIEVO`, `RESO_VENDITA_RIENTRO`). La grammatica unica le comprende o le lascia
   fuori?
7. **Gli incroci con i cantieri aperti** (§6): quali oggetti del censimento stanno toccando altri
   brief.

Consegna: una sezione di questo brief con le tabelle, e una **proposta** per G-1 … G-4.

## 5. Le decisioni per Tid (dopo il censimento)

* **G-1 — quale vocabolario vince.** Il catalogo esistente più completo (le entità o le sorgenti),
  allargato a ciò che manca, o un catalogo nuovo? La proposta del censimento deve dire che cosa
  costa ciascuna strada.
* **G-2 — il perimetro.** Le sole testate, o anche righe e varianti (§4 punto 6)?
* **G-3 — i vincoli che decidono un nome.** Si allargano le colonne (le note) o il codice si
  accorcia per tutti?
* **G-4 — l'ordine dei lotti.** Per famiglia (eccezioni, testate, note…) e in che ordine rispetto
  ai cantieri aperti.

## 6. Cantieri che toccano gli stessi oggetti

* [brief-db-indirizzi-documento-seguono-il-cliente](brief-db-indirizzi-documento-seguono-il-cliente.md):
  il §8.7 (lock delle testate, emittente e utility fermi) è appena applicato, e il suo giro BE
  (R-BE-9, R-BE-10) è aperto;
* [brief-db-documento-nasce-nello-stato-iniziale](brief-db-documento-nasce-nello-stato-iniziale.md):
  i guard di transizione delle testate;
* il ponte di [brief-db-articoli-ammessi-per-documento](brief-db-articoli-ammessi-per-documento.md)
  resta fino al lotto che lo rende inutile: lo ritira chi chiude questo brief.
