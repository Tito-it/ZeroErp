## 📘 Documentazione Concettuale – Tabella `config.termini_pagamento`

> 👀 **Vedi anche**
>
> **Tabelle collegate:**
>
> • [vendite.fatture_scadenze](/dbzero/vendite/tabelle/fatture_scadenze) — le rate che questa tabella fa generare
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture) — porta `termine_pagamento_id` e lo snapshot del termine
> • [config.modalita_pagamento](/dbzero/config/tabelle/modalita_pagamento) — il **come** si paga, tenuto separato dal **quando**
>
> **Funzioni che la usano:**
>
> • [vendite.fn_resolve_termini_pagamento](/dbzero/vendite/funzioni/fn_resolve_termini_pagamento) — sceglie **quale** termine
> • [vendite.fn_genera_scadenze_fattura](/dbzero/vendite/funzioni/fn_genera_scadenze_fattura) — **applica** il termine scelto

---
### 🎯 Scopo Principale
(latest review 02-08-26)

`config.termini_pagamento` è il **catalogo delle condizioni di pagamento**: ogni riga
è una regola parametrica che dice *quando* e *in quante volte* si paga un documento.
La regola non calcola niente da sola — viene letta al momento della fatturazione e
trasformata nelle righe di `vendite.fatture_scadenze`.

Il termine è richiamabile da **cliente, commessa, ordine e preventivo**; la fattura
che ne nasce ne conserva una **fotografia** (vedi *Snapshot in fattura*).

> ⚠️ **Riformata il 31-07-2026.** La tabella aveva due colonne che descrivevano la
> stessa cosa — `tipo_offset` (`G`/`M`/`F`/`N`) e `unita_intervallo` — e i vincoli ne
> controllavano solo una. Entrambe sono state **eliminate** e sostituite da un singolo
> booleano `fine_mese`. Da allora **tutti gli offset sono in giorni**, senza eccezioni:
> il calcolo ha un ramo solo. Se stai leggendo codice o documentazione che nomina
> `tipo_offset`, è anteriore alla riforma.

---

### 🧮 Come si legge una riga: la formula

Una riga di catalogo si traduce in un piano rate così:

```text
data della rata n = data documento + primo_offset_giorni + (n − 1) × intervallo
se fine_mese = true → la data si sposta all'ultimo giorno del proprio mese

importo di ogni rata = totale a pagare ÷ numero_rate, arrotondato
importo dell'ULTIMA rata = totale a pagare − somma delle precedenti
```

Tre cose da notare, perché sono scelte e non dettagli:

* **Un ramo solo.** Non esistono più i mesi come unità: «due mesi» si scrive
  `intervallo = 60`. Una formula sola non può divergere da sé stessa.
* **La quadratura sta sull'ultima rata.** Le prime rate portano la quota
  arrotondata, l'ultima assorbe la differenza — così la somma delle rate è
  **esattamente** il totale del documento, non una sua approssimazione.

  ⚠️ «Assorbe la differenza» **non vuol dire «riceve di più»**: la direzione
  dipende da come arrotonda la divisione, e con i termini di oggi va quasi
  sempre nel verso opposto a quello che ci si aspetta.

  | Base | Rate | Piano | L'ultima riceve |
  | --- | ---: | --- | --- |
  | 10,03 | 2 | 5,02 · **5,01** | **meno** (5,015 arrotonda per eccesso) |
  | 100,00 | 3 | 33,33 · 33,33 · **33,34** | più (33,3333 arrotonda per difetto) |

  Con **2 rate** `base/2` finisce sempre per 0 o 5 al terzo decimale, quindi
  `HALF_UP` arrotonda sempre per eccesso e la prima rata è sempre ≥ dell'ultima:
  il verso opposto si osserva solo **da 3 rate in su**. ℹ️ E il catalogo di oggi
  arriva **al massimo a 2 rate**, quindi la riga con 100,00 illustra la formula
  ma **non è riproducibile** senza aggiungere un termine. L'unico invariante che
  vale sempre è: **Σ rate = totale a pagare, esatta al centesimo**.
* **Il cavallo d'anno non ha codice dedicato.** `20/12/2026 + 30 giorni` dà
  `19/01/2027` perché è PostgreSQL a gestire il calendario: nessuna aritmetica
  scritta a mano, quindi nessun caso limite da ricordare.

---

### Semantica dei campi

L'elenco completo di colonne, tipi e default è nella scheda auto-generata qui sotto.
Questa sezione spiega **cosa significano**, non com'è fatta la tabella.

| Campo | Significato |
| --- | --- |
| `codice` / `codice_interno` | Identificativo esterno e interno. `codice_interno` è **immutabile**: un trigger di lock ne impedisce la modifica, perché è la chiave con cui il resto del sistema nomina il termine |
| `descrizione` | Testo mostrato all'utente |
| `numero_rate` | In quante rate si divide il documento (almeno 1) |
| `primo_offset_giorni` | Giorni fra la data del documento e la **prima** rata |
| `intervallo` | Giorni fra una rata e la successiva. Irrilevante quando `numero_rate = 1` |
| `fine_mese` | Se vero, ogni data calcolata slitta all'ultimo giorno del proprio mese |
| `ripartizione` | Come si divide il totale fra le rate. **Oggi è ammesso solo `UGUALI`** |
| `arrotondamento_metodo` / `arrotondamento_decimali` | Con quale regola e a quante cifre si arrotonda la singola rata |
| `attivo` | Se il termine è utilizzabile. ⚠️ Non è una leva libera: vedi *Ritirare un termine* |

---

### 📋 Il catalogo di oggi

Nove termini a seed, tutti attivi, tutti con ripartizione `UGUALI` e arrotondamento
`HALF_UP` a 2 decimali:

| `codice_interno` | Descrizione | Rate | 1° offset | Intervallo | Fine mese |
| --- | --- | ---: | ---: | ---: | :---: |
| `TP_1RATA` | Unica rata **(default di sistema)** | 1 | 0 | 0 | no |
| `TP_30G_1R` | 30 gg data fattura | 1 | 30 | 0 | no |
| `TP_30G_EOM_1R` | 30 gg data fattura, fine mese | 1 | 30 | 0 | **sì** |
| `TP_60G_1R` | 60 gg data fattura | 1 | 60 | 0 | no |
| `TP_60G_EOM_1R` | 60 gg data fattura, fine mese | 1 | 60 | 0 | **sì** |
| `TP_90G_1R` | 90 gg data fattura | 1 | 90 | 0 | no |
| `TP_90G_EOM_1R` | 90 gg data fattura, fine mese | 1 | 90 | 0 | **sì** |
| `TP_30_60_2R` | Rate a 30/60 giorni | 2 | 30 | 30 | no |
| `TP_30_60_EOM_2R` | Rate a 30/60 giorni, fine mese | 2 | 30 | 30 | **sì** |

Il catalogo si popola **solo da CSV**
(`db/changelog/migrations_v2/80_data/sql/config/termini_pagamento.csv`): aggiungere
un termine significa aggiungere una riga lì, non una `INSERT` a mano.

---

### 🔗 Chi sceglie il termine: la catena

La scelta non è del generatore delle scadenze. Esiste **un'unica** implementazione
della catena, `vendite.fn_resolve_termini_pagamento`, che per ogni attività scende
quattro livelli e si ferma al primo che risponde:

| # | Livello | Nota |
| --- | --- | --- |
| 1 | **Documento sorgente** — ordine o preventivo | L'ordine porta termine *e* modalità, il preventivo il solo termine |
| 2 | **Commessa** | La commessa **possiede** le proprie condizioni |
| 3 | **Cliente** del billing account padre | Costante su tutte le attività che finiscono nella stessa fattura |
| 4 | **Default `TP_1RATA`** | Nessuna fattura resta senza piano rate |

Tre avvertenze che contano più dell'elenco:

* **Termine e modalità scendono separatamente.** Il preventivo porta il termine ma
  non la modalità, quindi i due campi possono fermarsi a livelli diversi. Solo il
  termine ha un default: `config.modalita_pagamento` non ha una riga «predefinita»,
  e sceglierne una a caso finirebbe sulla fattura elettronica.
* **Il livello 1 oggi è dormiente.** `vendite.ordini` e `vendite.preventivi` sono a
  zero righe e tutte le attività arrivano da commessa: quel ramo è una
  predisposizione che si accenderà al primo uso reale.
* **La commessa sta prima del cliente**, ed è deliberato. È il livello più
  specifico, e cambiare le condizioni di un cliente non deve riscrivere quelle
  delle commesse già aperte.

#### Perché il termine si decide alla fonte

Un documento con condizioni diverse **non riusa una commessa esistente: ne apre una
nuova.** Le condizioni di pagamento sono parte della chiave con cui le attività si
raggruppano.

La strada alternativa — lasciar aggregare tutto e poi risalire dalla fattura al
documento che l'ha originata — è stata scartata su una misura: una singola commessa
arriva a **32 sorgenti di 4 tipi diversi**, e fra queste **contratti e DDT non hanno
colonne di pagamento**. Risalire avrebbe spaccato le fatture per *assenza del campo*
invece che per una scelta di qualcuno. Decidendo alla fonte, la divergenza si vede
quando la si crea, invece di comparire mesi dopo come una fattura in più che nessuno
sa spiegare.

---

### 📸 Snapshot in fattura

Quando le rate vengono generate, la fattura riceve in testata
(`vendite.fatture.termine_pagamento_snapshot`) una fotografia del termine usato:
i **valori** — rate, offset, intervallo, fine mese, arrotondamento — con l'`id`
accanto come sola indicazione di provenienza.

La ragione è che uno snapshot di soli id non è uno snapshot: se domani il catalogo
cambia, un documento fiscale già emesso deve continuare a spiegare le rate che ha,
senza dipendere da una tabella che nel frattempo si è mossa.

---

### 🔒 Vincoli, in parole

* **`ripartizione` ammette il solo valore `UGUALI`.** `PROPORZIONALE` e `LIBERA`
  erano un'intenzione mai implementata; il vincolo ora dice la verità. Il generatore
  conserva comunque un rifiuto esplicito per il caso in cui una riga aggiri il
  catalogo: un piano rate calcolato con una regola inesistente sarebbe peggio di un
  errore.
* **`arrotondamento_metodo` ∈ `UP`, `DOWN`, `HALF_UP`, `HALF_DOWN`** — il
  vocabolario unico di tutto il database (prima qui c'era `HALF_EVEN`, che nessuno
  applicava). L'arrotondamento passa da un building block solo,
  `script.fn_arrotonda_importo`.
* **`numero_rate >= 1`**, **`arrotondamento_decimali` fra 0 e 6**,
  **`intervallo` e `primo_offset_giorni` non negativi**.
* **`codice` e `codice_interno` unici**, e `codice_interno` bloccato in modifica dal
  trigger di lock colonne.

---

### ⚠️ Ritirare un termine dal catalogo

**Mettere `attivo = false` non funziona come ci si aspetta.** Sette trigger
`prevent_deactivate_if_children` sorvegliano la disattivazione: il termine non si
disattiva se è referenziato da **clienti, fornitori, commesse, fatture, ordini,
preventivi** o dagli **ambiti di arrotondamento**. È corretto che sia così — un
documento non deve perdere la regola che spiega le sue rate — ma significa che in
pratica un termine entrato in uso **non è più disattivabile**.

Su questa tabella **non esiste** oggi un asse separato per dire «non più
selezionabile per i nuovi documenti, ma valido per quelli esistenti». Il pattern di
riferimento per quel bisogno è descritto in
`docs/it/dev/work-in-progress/brief-db-deprecabilita-catalogo-vs-istanze.md`;
finché non viene esteso qui, l'unica strada praticabile è **non modificare in place**
un termine in uso e aggiungerne uno nuovo con codice diverso.

---

### ✅ Anomalie storiche: tutte chiuse

Le quattro riserve annotate nella revisione di gennaio non sono più aperte.

| Rilievo di gennaio | Esito |
| --- | --- |
| `intervallo` `NOT NULL` ma i CHECK ammettevano `NULL` | Chiuso: la colonna resta `NOT NULL` con default `0`, e il vincolo che ammetteva il `NULL` è stato eliminato |
| Duplicazione `unita_intervallo` / `tipo_offset` | Chiuso: **entrambe eliminate**, sostituite da `fine_mese` |
| Mancavano vincoli di range | Chiuso: `numero_rate >= 1`, decimali `0..6`, offset e intervallo non negativi |
| `codice_interno` dichiarato immutabile ma senza lock | Chiuso: il trigger di lock colonne è montato |

---

### Ruolo nel sistema

`config.termini_pagamento` è il punto in cui la politica di incasso viene **detta una
volta** e poi applicata in modo uniforme. Il valore non sta nella tabella in sé, ma
nella catena che la circonda: una sola regola per scegliere il termine, una sola
formula per applicarlo, una sola fotografia che lo conserva sul documento emesso.
