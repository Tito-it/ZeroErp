> **Ultimo aggiornamento**: 1 novembre 2026

### 🗒️ Le partizioni di note in `magazzino`

Questa tabella è una **partizione** di [magazzino.note](/dbzero/magazzino/tabelle/note), il
padre delle note del dominio, partizionato per `target_tipo`: una partizione per ciascun
oggetto che si può annotare. Non è una tabella a sé: struttura, ancoraggio (testata o riga),
posizionamento, ordinamento di rendering e regole comuni sono quelli del meccanismo note del
progetto, documentato per intero in **[vendite.note](/dbzero/vendite/tabelle/note)**.

Qui non si documentano le colonne una per una: sono quelle del padre.

---

### Perché una partizione per ciascun bersaglio

Il partizionamento esiste perché ogni partizione possa avere la propria **chiave esterna
forte** verso la tabella che annota. Sul padre `magazzino.note` quella chiave non potrebbe
esistere: il bersaglio cambia natura da una partizione all'altra.

Conseguenza pratica: **le note seguono il ciclo di vita di ciò che annotano**. Se si cancella
l'oggetto annotato, le sue note se ne vanno con lui; una nota di riga se ne va anche quando si
cancella il documento a cui la riga appartiene.

---

### ⚠️ Annotare il documento o la riga non è la stessa cosa

Le partizioni di un documento e delle sue righe (per esempio `note_inventario` e
`note_inventario_riga`) esistono in coppia proprio perché sono due ancoraggi diversi: la nota
di testata vale per l'intero documento, quella di riga per una singola voce. Sceglierne una
per l'altra produce note che compaiono nel posto sbagliato in stampa, ed è l'errore più
comune di questo meccanismo.
