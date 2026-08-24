### 🗒️ Le partizioni di note in `magazzino`

Questa tabella è una **partizione** del meccanismo note del progetto, partizionato per
`target_tipo`. Non è una tabella a sé: struttura, ancoraggio (testata/riga), posizionamento,
ordinamento di rendering e regole comuni stanno tutti nel documento principale
**[vendite.note](/dbzero/vendite/tabelle/note)**.

Qui non si documentano le colonne una per una: sono quelle del padre.

---

### Perché una partizione per ciascun bersaglio

Il partizionamento esiste perché ogni partizione possa avere la propria **FK forte** verso la
tabella che annota. Sul padre `vendite.note` quella FK non potrebbe esistere: il bersaglio
cambia natura — e talvolta tipo di chiave — da una partizione all'altra.

Conseguenza pratica: **le note seguono il ciclo di vita di ciò che annotano**. Con
`ON DELETE RESTRICT`, un documento con note non si cancella finché le note ci sono.

---

### ⚠️ Le note di `magazzino` sono tutte vuote

Misurato il 2026-08-21: **zero righe** in tutte le partizioni di questo schema, coerentemente
con lo stato del dominio (nessun movimento, nessun documento). Sono strutture pronte per un
processo che non è ancora partito.

---

### ⚠️ Annotare il documento o la riga non è la stessa cosa

Le partizioni `note_<documento>` e `note_<documento>_riga` esistono in coppia proprio perché
sono due ancoraggi diversi: la nota di testata vale per l'intero documento, quella di riga per
una singola voce. Sceglierne una per l'altra produce note che compaiono nel posto sbagliato in
stampa — ed è l'errore più comune di questo meccanismo.
