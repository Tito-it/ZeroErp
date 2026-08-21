### 🎯 A che cosa serve una tabella di `storico`

Ogni tabella di questo schema è l'**archivio temporale** di una tabella di uno schema
principale. Non contiene dati suoi: conserva **com'era** una riga prima di ogni modifica o
cancellazione.

Serve a rispondere a tre domande che sulla tabella viva non hanno risposta:

* *com'era questo record il giorno X?*
* *chi e quando l'ha cambiato?*
* *questa riga è stata cancellata, e cosa conteneva?*

⚠️ **La descrizione del contenuto sta nella tabella di origine.** Qui le colonne di dominio
non sono documentate una per una: sono le stesse della fonte, congelate dentro `snapshot`.
Il rimando in testa a ogni pagina porta al documento giusto.

---

### Come si popola

Non ci scrive nessuno a mano. La alimenta il trigger generico
`script.trgfn_storico_generic('<fonte>_id')`, agganciato **sulla tabella di origine** come
`trg_<tabella>_z90_storico_upd_dlt`, in fase `_z90_`.

⚠️ **`BEFORE UPDATE OR DELETE` — non `INSERT`.** È la conseguenza da tenere a mente: lo storico
registra lo stato **precedente** a ogni modifica, quindi **la nascita di una riga non è
tracciata**. La prima riga di storico compare al primo aggiornamento, e contiene i valori
originali. Una riga creata e mai più toccata non ha storia.

⚠️ **Il flag `storicizza` sulla riga viva decide.** Se è `false`, la modifica non viene
archiviata: lo storico non è totale per costruzione, è totale *per configurazione*. Un buco
nella storia può quindi essere un flag, non una perdita di dati.

---

### La struttura, uguale per tutte

| Colonna | Che cosa contiene |
|---|---|
| `id` | chiave tecnica dello storico (sequenza propria) |
| `<fonte>_id` | la riga di origine a cui la versione si riferisce |
| `snapshot` (`jsonb`) | **la riga com'era**, per intero |
| `change_type` / `tipo_operazione` | che tipo di cambiamento l'ha generata |
| `valid_from` / `valid_to` | l'intervallo in cui quella versione è stata quella corrente |
| `tx_id` | la transazione che ha prodotto il cambiamento |
| `user_insert` / `data_insert` | chi e quando ha archiviato |

⭐ **Il dato di dominio vive dentro `snapshot`, non in colonne proprie.** È ciò che rende lo
storico immune all'evoluzione della tabella viva: se domani la fonte guadagna o perde una
colonna, l'archivio non va migrato — gli snapshot vecchi restano leggibili così com'erano.

Il prezzo è che si interroga con gli operatori JSONB (`snapshot->>'colonna'`), non con SQL
piano, e che **nessun vincolo garantisce che il contenuto di `snapshot` corrisponda alla
struttura attuale** della fonte.

---

### Come si legge

Per ricostruire lo stato a una certa data si cerca la versione il cui intervallo
`[valid_from, valid_to)` contiene quel momento. `valid_to` nullo indica la versione più
recente archiviata — **non** la riga viva, che sta nella tabella di origine.

⚠️ Per la riga **corrente** non si guarda qui: si guarda la fonte. Lo storico contiene solo
ciò che è già stato superato.

---

### Note comuni

* **Append-only per destinazione d'uso.** Le righe non si aggiornano e non si cancellano: un
  archivio riscrivibile non varrebbe come archivio.
* **Lo storico sopravvive alla fonte.** Se la tabella viva viene rimossa, il suo storico resta
  — ed è corretto: i dati archiviati non diventano meno veri perché la struttura che li
  produceva non c'è più.
* **`tx_id` è la chiave di correlazione**: permette di ritrovare *tutte* le righe archiviate
  dalla stessa operazione, anche su tabelle diverse. È il modo per ricostruire un'operazione
  multi-tabella a posteriori.
