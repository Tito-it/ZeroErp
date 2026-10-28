# Brief DB — Pratiche: il giornale delle sospensioni senza `tx_id` inventato

## ⏭️ Chi riparte — aggiornato al 2026-10-26

**Riparte: team DB** (`dev/db-tid`). Nessuna decisione aperta di Tid: è un allineamento al modello già
scritto (§2), con perimetro chiuso (§3).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione BE | Il caso, i fatti, la richiesta | §1-§3 | — |
| 2 | **team DB** ⏭️ | Le due funzioni, il test, la doc | §3-§4 | 1 |
| 3 | team BE/FE | Niente: nessuna ricaduta (§5) | — | — |

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-26. **A chi:** team DB.
> **Origine:** verifica nata da una domanda di Tid sulle novità di Django 6.1 (`UUID7`). Il DB usa già
> `uuidv7()` come default delle colonne; le uniche due generazioni di UUID fuori da quella regola sono
> queste. Tid, 2026-10-26: brief separato.
> **Brief vicini verificati:** [gestione-pratiche-come-procedere](gestione-pratiche-come-procedere.md) riga
> «Part B audit giornale (append-only)», aperta lato team DB: stesso giornale, tema diverso (chi può
> scrivere/modificare le righe, non il loro `tx_id`). Nessun brief aperto tocca il `tx_id` del giornale.

## 1. Il caso

Due funzioni trigger su `pratiche.sospensioni` scrivono nel giornale passando un `tx_id` con ripiego:

| Funzione | Trigger | Evento |
| --- | --- | --- |
| `pratiche.trgfn_sospensioni_giornale_ins` | `AFTER INSERT` | `SOSPENSIONE_REGISTRATA` |
| `pratiche.trgfn_sospensioni_giornale_riattivazione` | `trg_sospensioni_z90_giornale_riattivazione_upd`, `AFTER UPDATE OF data_fine` | `SOSPENSIONE_CHIUSA` |

```sql
INSERT INTO pratiche.giornale (pratica_id, flusso_id, azione, origine, dettaglio, tx_id)
VALUES (..., COALESCE(NEW.tx_id, gen_random_uuid()));
```

Il manuale della prima lo segnala già come difetto latente
([trgfn_sospensioni_giornale_ins](/dbzero/pratiche/manual/trgfn_sospensioni_giornale_ins) § «Il fallback
sul `tx_id` è una rete che non dovrebbe servire»): un id inventato qui non correla niente, e se il `BEFORE`
che valorizza `sospensioni.tx_id` sparisse il difetto si presenterebbe come righe di giornale non
correlabili, **non come errore**.

## 2. Il modello

* `pratiche.giornale` ha il suo trigger `trg_giornale_gen_tx_id_ins_upd`
  (`dbops.trgfn_tx_id_managed`, `BEFORE INSERT OR UPDATE`). Il BB, con `NEW.tx_id` NULL, assegna l'id di
  sessione **registrato** in `dbops.transaction_ids`; con `NEW.tx_id` valorizzato esce subito e lo tiene
  così com'è (uscita anticipata, rev 2026-07-24).
* Quindi il ripiego è peggio che ridondante: un `gen_random_uuid()` arriva al giornale **valorizzato**, il BB
  lo accetta senza verificarlo, e la riga porta un id che non esiste nel registro. Senza il ripiego, la
  stessa riga avrebbe ricevuto dal BB l'id giusto.
* **Simmetria:** le altre 12 funzioni che scrivono in `pratiche.giornale` (`trgfn_pratiche_giornale_*`,
  `trgfn_flussi_giornale_*`, `trgfn_note_*`, `trgfn_allegati_*`, `fn_log_evento_dominio`) non passano
  `tx_id`: lo lascia assegnare al BB. Le due funzioni delle sospensioni sono le sole copie divergenti
  (verificato sulla doc `docs/it/dbzero/pratiche/funzioni/`, 2026-10-26; nessun altro
  `COALESCE(NEW.tx_id, …uuid…)` in tutto `dbzero`).

## 3. La richiesta

1. In entrambe le funzioni **togliere `tx_id` dalla lista colonne e dai `VALUES`** dell'`INSERT INTO
   pratiche.giornale`, come nelle altre 12. Il `tx_id` lo assegna `trg_giornale_gen_tx_id_ins_upd`.
2. Non sostituire `gen_random_uuid()` con `uuidv7()` né con `NEW.tx_id` nudo: il primo lascia il difetto
   (id non registrato), il secondo mantiene una seconda via di assegnazione accanto al BB. La via è una.
3. Aggiornare i due manuali: tabella «Che cosa scrive» (riga `tx_id` → «assegnato da
   `dbops.trgfn_tx_id_managed` sul giornale») e rimuovere la sezione ⚠️ sul ripiego, sostituendola con una
   nota di manutenzione datata.

## 4. Verifiche (pgTAP)

* Con `dbops.tx_id` di sessione registrato: `INSERT` di una sospensione e poi la riattivazione
  (`data_fine` da NULL a valorizzata) → le due righe di giornale hanno `tx_id` uguale all'id di sessione e
  presente in `dbops.transaction_ids`.
* Il `tx_id` della riga di giornale coincide con quello della sospensione che l'ha generata, nello stesso
  giro.
* Il caso che il ripiego copriva: la sospensione con `tx_id` NULL (BEFORE della sospensione in bypass, o
  disabilitato nel test) → la riga di giornale riceve comunque un id dal BB del giornale, **non** un UUID
  fuori registro.

## 5. Cosa NON entra

* **Ricaduta BE/FE: nessuna.** Il backend non legge né scrive `giornale.tx_id` delle sospensioni in modo
  diverso dalle altre righe.
* La «Part B audit giornale» (append-only) del tracker: resta dov'è.
* Le osservazioni sul `WHEN` di `trg_sospensioni_z90_giornale_riattivazione_upd` (correzione di una
  `data_fine` già impostata che non lascia traccia) già scritte nel suo manuale: tema separato, non
  toccato qui.
