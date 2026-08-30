## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_annulla_movimento_titolo_iva`

> 👀 **Vedi anche**
>
> [script.fn_check_annullo_movimento_titolo_iva](/dbzero/script/funzioni/fn_check_annullo_movimento_titolo_iva) — l'ammissibilità, che **chiama** ·
> [anagrafiche.trgfn_stiva_movimenti_guard_annullo](/dbzero/anagrafiche/funzioni/trgfn_stiva_movimenti_guard_annullo) — la difesa contro la scrittura diretta ·
> [anagrafiche.trgfn_soggetti_titoli_iva_movimenti_accumulatore](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_movimenti_accumulatore) — chi riporta il totale ·
> [anagrafiche.vw_stiva_movimenti_dettaglio](/dbzero/anagrafiche/views/vw_stiva_movimenti_dettaglio) — dove si preme il pulsante

---

### 🎯 Scopo Principale

(rev 2026-08-31 — funzione nata il 2026-08-31)

**Funzione madre**: annulla una `FORZATURA` del registro plafond IVA scrivendo il
**contro-movimento di segno opposto**, e ne ritorna l'id.

Firma: `fn_annulla_movimento_titolo_iva(p_movimento_id, p_motivo)`.

Il chiamante passa **due cose sole**: *quale riga* e *perché*.

---

### ⭐ Importo e titolo si DERIVANO, non si ricevono

È la scelta che dà forma a tutto il resto. Il brief originale chiedeva soltanto una
colonna di collegamento, lasciando al backend il compito di comporre la riga. Ma
importo e titolo sono **derivabili** dalla riga annullata — e se li deriva il
database:

* il backend non può sbagliarli;
* i due controlli di coerenza del guard smettono di essere «errori che l'operatore
  può fare» e diventano **difesa contro una scrittura diretta**, che è il posto
  giusto per loro;
* e la firma dice da sola cosa serve sapere per annullare.

⚠️ **I guard restano comunque.** La tabella è scrivibile anche senza passare di
qui: *un guard che esiste solo perché «tanto ci si passa dalla madre» è un guard
che il primo `INSERT` diretto scavalca.*

---

### ⭐ Chiama la check, non riscrive il predicato

L'ammissibilità la decide `script.fn_check_annullo_movimento_titolo_iva` — **la
stessa** che spegne il pulsante nel read-side. Questa madre la interroga e solleva
il codice del **primo** motivo.

> Un test che confrontasse i due esiti proverebbe che **oggi** coincidono; così si
> prova che **non possono divergere**, perché la regola sta in un posto solo.

⚠️ In pratica la check è invocata **due volte** — qui e dal guard — e va bene: è
`STABLE`, e la coerenza vale più di una lettura risparmiata.

---

### La sequenza

1. **Guard di parametro**: `p_movimento_id > 0` e `p_motivo` non vuoto.
   ⚠️ Il motivo lo pretende già un `CHECK` di tabella, ma **lì uscirebbe come
   violazione di vincolo (23514)**, cioè un errore muto per chi legge. Qui esce
   come rifiuto di dominio.
2. **Ammissibilità**: si chiama la check; se torna motivi, si solleva il primo.
3. **La riga da annullare**, per derivarne titolo e importo.
4. **Il contro-movimento**: segno opposto, stesso titolo, tipo `FORZATURA`,
   nessun documento (lo impone già il `CHECK` sulla forzatura), `data_movimento`
   **di oggi**, il motivo ricevuto, e `annulla_movimento_id` che chiude il legame.

---

### ⭐ `data_movimento` è la data dell'ANNULLO

Non quella della forzatura. È il terzo argomento per cui l'annullo è una riga e non
un flag: **quando** qualcuno si è accorto dell'errore. Un flag `annullato` quella
informazione la perde.

---

### ⚠️ La lettura del passo 3 è `INVOKER`, e non è un buco

Se la riga fosse fuori perimetro non si vedrebbe, e la funzione si ferma. Non è una
falla: la check — che è `DEFINER` — l'ha **già dichiarata annullabile**, quindi
arrivare qui e non trovarla significa che **chi opera non ha il perimetro per
farlo**, ed è giusto che si fermi.

---

### Regole

* **`SECURITY INVOKER` esplicito**, convenzione delle madri: gira come il ruolo
  chiamante, quindi RLS e scope emittente restano applicati **sulla scrittura**.
  Sono la check e il guard a essere `DEFINER`, e solo per le **letture di
  coerenza**.
* **Atomica per costruzione**: una sola istruzione su connessione in autocommit —
  PostgreSQL la avvolge in una transazione implicita e qualunque eccezione annulla
  tutto. Nessun `BEGIN`/`EXCEPTION`.
* **Non tocca l'accumulatore**: quello somma senza filtri, quindi il
  contro-movimento riporta `imponibile_utilizzato` al valore giusto **da sé**.

---

### Codici errore

| Codice | Motivo | Classe |
| --- | --- | --- |
| `E_TITOLO_IVA_ANNULLO_NON_AMMESSO` | il primo motivo della check | `CONFLITTO_STATO` (409) |
| `E_TITOLO_IVA_ANNULLO_INCOERENTE` | parametro mancante o non valido | `TECNICO` (500) |

---

### Test

`db/pgtap/anagrafiche/test-stiva-movimenti-annullo-v1.sql`.

⭐ L'asserzione **2** è quella che descrive il contratto: annullata una forzatura, il
registro ha **due righe** e `imponibile_utilizzato` è tornato al valore precedente.
⚠️ Da sola non basterebbe — la rende vera l'asserzione sull'**importo sbagliato**,
senza la quale il numero giusto lo scriverebbe la fixture.

Cantiere: `brief-db-titoli-iva-movimenti-annullo.md`, fase `C`.

---

{% include-markdown "signature-core.md" %}
