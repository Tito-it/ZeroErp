## 📘 Documentazione Concettuale – Funzione `vendite.fn_cleanup_fatture_by_ids`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture) — il legame lotto-fattura, che si cancella
> * [vendite.fatture](/dbzero/vendite/tabelle/fatture) · [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe) · [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva) — il documento che si cancella
> * [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log) · [vendite.note_fatture](/dbzero/vendite/tabelle/note_fatture) — log e note della fattura
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) · [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — ciò che si ripristina
>
> Approfondimento funzioni:
>
> * [vendite.fn_annulla_lotto_da_draft](/dbzero/vendite/funzioni/fn_annulla_lotto_da_draft) — chiamante: l'annullo del lotto
> * [vendite.fn_elimina_fattura_da_lotto](/dbzero/vendite/funzioni/fn_elimina_fattura_da_lotto) — chiamante: togli una fattura dal lotto
> * [vendite.fn_riporta_lotto_a_draft](/dbzero/vendite/funzioni/fn_riporta_lotto_a_draft) — chiamante: il ritorno in bozza
> * [vendite.fn_reset_fondi_fattura](/dbzero/vendite/funzioni/fn_reset_fondi_fattura) — il reset dei fondi della fattura
> * [vendite.fn_libera_attivita_fatturabili](/dbzero/vendite/funzioni/fn_libera_attivita_fatturabili) — le due scritture del ripristino
> * [vendite.fn_porta_reset_lotto_aperta](/dbzero/vendite/funzioni/fn_porta_reset_lotto_aperta) — la porta del reset, che questa funzione accende
>
> Guide:
>
> * [Fatturazione](/guide/fatturazione) — il reset del lotto

---

### 🎯 Scopo Principale

La funzione **`vendite.fn_cleanup_fatture_by_ids()`** è il **proprietario unico**
del ripristino: cancella le fatture indicate e riporta indietro **tutto** ciò che
avevano consumato.

> **La regola che governa questa pagina.**
> **Cosa si ripulisce** sta qui e **solo** qui. **Come resta il documento** —
> annullato, riaperto, o intatto — appartiene all'operazione che chiama.
> I chiamanti non contengono nessuna riga di pulizia.

---

### ⛔ Due cose che non cancella mai: si ferma prima

Prima di toccare qualunque riga la funzione controlla due casi, e se uno dei due c'è
**rifiuta** con un errore che dice cosa fare, invece di esplodere a metà su una
chiave esterna:

| Caso | Codice | Perché non si cancella |
| --- | --- | --- |
| su una riga è già registrato un **accredito** | `E_FATTURE_RIGHE_RETTIFICATE` | il legame è il tetto dell'accredito e il riferimento della nota di credito |
| la fattura ha già **consumato plafond** (dal 2026-10-04) | `E_FATTURE_PLAFOND_CONSUMATO` | il movimento del plafond è un fatto contabile: il registro non si cancella, e la fattura va portata avanti |

Le tre porte di reset si fermano già prima, nelle loro funzioni di controllo, con gli
stessi motivi: questi due controlli sono la difesa della porta che nessuno ha ancora
scritto.

---

### I tre chiamanti, e perché la divisione conta

| chiamante | come lascia il lotto |
|---|---|
| [`fn_annulla_lotto_da_draft`](/dbzero/vendite/funzioni/fn_annulla_lotto_da_draft) | → **ANNULLATA**: il lotto si chiude |
| [`fn_riporta_lotto_a_draft`](/dbzero/vendite/funzioni/fn_riporta_lotto_a_draft) | → **DRAFT**: il lotto resta vivo e riparte |
| [`fn_elimina_fattura_da_lotto`](/dbzero/vendite/funzioni/fn_elimina_fattura_da_lotto) | **non lo tocca**: agisce su una fattura sola |

Sono tre operazioni diverse che condividono **la stessa** pulizia. È il motivo per
cui la pulizia non può stare dentro nessuna delle tre: la correttezza di ognuna
dipende dal fatto che facciano esattamente la stessa cosa.

⚠️ **Lezione pagata il 03-08-2026.** Il ritorno a DRAFT era nato con un passo in
più scritto **dentro di sé** — il ripristino delle `commesse_attivita`. Risultato:
la stessa pulizia esisteva in due versioni, completa in una funzione e incompleta
nelle altre due. Le altre due cancellavano le fatture lasciando le attività
marcate come **emesse**, cioè righe di commessa **senza fattura e irrecuperabili**:
la selezione di ciò che è da emettere le scartava per sempre. Nessuna orfana si era
ancora formata — il difetto era **latente** e si sarebbe armato al primo
annullamento.

---

### Chi la chiama, e la porta del reset

È **riservata al proprietario**: l'applicazione non la può eseguire. La chiamano solo i tre
verbi qui sopra, che girano come proprietario e all'ingresso controllano il permesso e il
perimetro su lotto e fatture. Questa funzione non ripete quei controlli: chi ci arriva è già
passato da un verbo.

**La porta del reset.** La pulizia scrive su tabelle che i loro guard proteggono: attività già
fatturate, quantità emesse, satelliti della fattura, log. Per farlo accende la GUC
`zeroerp.maintenance_reset_lotto_draft` prima di cominciare, e la **spegne prima di uscire**. I
guard lasciano passare solo se la GUC è accesa **e** chi scrive è il proprietario della tabella
([`vendite.fn_porta_reset_lotto_aperta`](/dbzero/vendite/funzioni/fn_porta_reset_lotto_aperta)).

⭐ Così la porta resta aperta solo mentre la pulizia lavora. Quello che il verbo scrive dopo, come
lo stato del lotto, lo giudicano di nuovo i guard. Per l'applicazione la porta è sempre chiusa:
accendere la GUC da sé e scrivere diretta non apre niente.

---

### Cosa ripristina

> ⛔ **L'ordine è portante, e viene prima dell'elenco.** *Prima si ripristina,
> poi si cancella.* Non è una preferenza di stile: la chiave esterna
> `fk_attivita_fatturabili_fattura_riga` non è differita, quindi la sua azione
> referenziale scatta **a fine istruzione** del `DELETE` sulle righe. Con il
> ripristino a valle di quel `DELETE`, il legame che il ripristino deve leggere
> è già rotto e il filtro non trova più niente: l'attività resta fatturata senza
> fattura e la sua riga di commessa resta emessa, **senza un errore**. È
> successo, fra il 28 luglio e il 26 agosto 2026.
>
> ⚠️ Chi aggiunge un passo qui dentro non lo metta fra il ripristino e le
> cancellazioni.

* **Elimina**: note (dal padre partizionato `vendite.note`), riepiloghi IVA,
  righe, log, collegamento lotto-fattura, testate. ⭐ **Dopo** il ripristino,
  mai prima.
* **Storna** dall'ambito di compensazione l'arrotondamento delle fatture
  cancellate, **prima** di toccarle — in testa alla funzione, così resta corretto
  qualunque passo venga aggiunto dopo.
* **Azzera i fondi** via [`fn_reset_fondi_fattura`](/dbzero/vendite/funzioni/fn_reset_fondi_fattura).
  Quella funzione **cancella** l'atto di fondo che non è stato eseguito: un atto
  mai eseguito è una proposta, e il giro successivo ne fa una nuova sul residuo
  di adesso. Un atto già eseguito, o bloccato per un'altra ragione, non lo tocca:
  lo segnala con un avviso in `fatture_log` e va avanti.
* **Sblocca** le `attivita_fatturabili` (lock, flag `fatturato`, legame alla riga,
  `stato_esecuzione` a NULL).
* **Riporta le `commesse_attivita` a `NON_EMESSA`** (dal 03-08-2026). Senza questo
  passo il ripristino è **inutile**: `fn_emit_attivita_fatturabili_da_commessa`
  filtra su `stato_emissione = 'EMESSA'` e non le riprenderebbe mai più. Lo stesso
  campo decide come il cruscotto competenza classifica la riga.
  Le attività **ANNULLATE** non si toccano: sono state annullate di proposito.
* Accende la porta del reset per le sue scritture, e la spegne prima di uscire
  (sezione qui sopra).

⭐ **Le due popolazioni sono una sola per costruzione** (dal 26-08-2026). Il
perimetro si calcola **una volta** — mentre il legame con la riga è ancora vivo —
e diventa un elenco di identificativi; le due scritture stanno insieme nella
primitiva condivisa
[`fn_libera_attivita_fatturabili`](/dbzero/vendite/funzioni/fn_libera_attivita_fatturabili),
che serve anche il verbo di recupero. Prima erano **due filtri identici scritti
due volte**, «di proposito»: bastava che divergessero per sbloccare un insieme di
attività e rimetterne in coda un altro, in silenzio. Ora quel rischio non esiste.

⚠️ **La primitiva non apre la porta del reset, e non deve.** Il guard di riga
rifiuta di toccare un'attività ancora agganciata a una fattura: è ciò che
impedisce di usare il ripristino per **scollegare una fattura viva**. Ad aprirla
è chi la fattura la sta cancellando — cioè questa funzione, due passi più in su.

⚠️ **Il ramo su `p_lock_batch_id`** prende **tutte** le attività del batch: è
corretto nel reset globale (libera anche quelle agganciate al lotto che non sono
mai diventate riga) ed è il motivo per cui il reset **per-fattura** deve passare
`NULL`.

### 🔴 rev 12-09-2026 — «agganciate al lotto» vuol dire anche EMESSE E NON LOCKATE

Il giro marca le attività **prima** di lockarle: il pull scrive `emit_batch_id`,
la `select` — un task dopo — scrive `lock_batch_id`. Fra i due c'è una finestra,
e un giro che cade lì (o un `select` saltato) lascia attività col **marchio** del
lotto e **nessun lucchetto**, con la riga di commessa `EMESSA`. Il ramo qui sopra
non le vedeva, e nessun giro le avrebbe riprese: il pull le vede `EMESSE`, la
`select` di un lotto nuovo lockа **solo** attività col proprio marchio. Verificato
il 12-09 sul lotto 13338 annullato da Tid: due attività libere col marchio del
lotto morto, righe `EMESSE`, e «Riporta da emettere» che le rifiutava.

Due correzioni, nello stesso changeSet (`20260912-34`):

1. **un terzo ramo nel perimetro**: `emit_batch_id = p_lock_batch_id AND
   lock_batch_id IS NULL AND fattura_riga_id IS NULL` — la stessa identità del
   giro letta dal marchio. `lock_batch_id IS NULL` perché un lucchetto **altrui**
   non si tocca (se è il mio è già nel primo ramo); `fattura_riga_id IS NULL`
   perché una riga già in fattura passa dal secondo ramo o non si libera da qui.
   Vale solo col marchio del giro: il reset **per-fattura** (`NULL`) non cambia;
2. 🔴 **l'uscita anticipata** su «elenco fatture vuoto» vale solo se manca
   **anche** il giro. Prima usciva e basta — e un lotto fermo **prima** di
   `generate_fatture_righe` (un pull fallito) non ha fatture: il reset non
   liberava **nessuna** attività, nemmeno quelle lockate dalla `select`. L'ha
   preso il pgTAP alla prima corsa (`updated_attivita = 0` da
   `fn_annulla_lotto_da_draft` col terzo ramo già dentro): la causa stava sotto
   quella che il brief vedeva. Con fatture assenti e un giro da liberare, i passi
   sulle fatture girano su un insieme vuoto e sono innocui.

Presidio: `db/pgtap/vendite/test-af-emessa-non-lockata-reset-e-riporto-v1.sql`
(3, 4, 8), che costruisce la finestra col **pull vero**. Brief:
`brief-db-rilancio-step-non-rivede-le-proprie-commesse` §10.4.

---

### 🔴 Se aggiungi una tabella figlia di `vendite.fatture`

**O la gestisci qui, o la motivi nel test.** Non c'è una terza strada, e non è una
raccomandazione: c'è un invariante che lo verifica —
`db/pgtap/vendite/test-cleanup-fattura-copertura-figlie-v1.sql`.

Quel test legge da `pg_constraint` **ogni** figlia di `vendite.fatture` e pretende
che sia classificata in una di quattro categorie, con la motivazione scritta:
`GESTITA`, `CASCADE_DB`, `BLOCCO_VOLUTO`, `SCOPERTA_NOTA`. Una tabella nuova lo fa
diventare **rosso, col proprio nome dentro il messaggio**.

Il motivo per cui serve: senza, una figlia nuova fallisce in **due modi opposti** e
nessuno dei due è «continua a funzionare» —

| la figlia nasce con… | cosa succede |
|---|---|
| `ON DELETE CASCADE` | viene cancellata **in silenzio**, anche se doveva sopravvivere |
| `NO ACTION` | la `DELETE` **esplode** con una violazione di FK grezza, davanti all'operatore |

⚠️ **Un rosso non si spegne aggiungendo la voce all'inventario.** Si decide a quale
categoria appartiene la tabella. Il rosso non è il problema: è la domanda.

---

### Output

Ritorna una riga con **quattro** contatori, separati di proposito: un numero unico
direbbe «dieci cose fatte» senza distinguere attività **sbloccate** da attività
**rimesse in coda**, che sono fatti diversi e possono divergere.

* `deleted_fatture`
* `deleted_righe`
* `updated_attivita` — `attivita_fatturabili` sbloccate
* `riemesse_attivita` — `commesse_attivita` tornate emittibili

---

Il cleanup delle note avviene su `vendite.note` (partizione `note_fatture`).

---

### Test

* `db/pgtap/vendite/test-porta-reset-lotto-e-fondo-v1.sql` — gira come l'applicazione: l'app non
  esegue la funzione; la GUC del reset la accende solo lei; dopo il verbo che la chiama la GUC è
  vuota.
* `db/pgtap/vendite/test-cleanup-fattura-copertura-figlie-v1.sql` — ogni figlia di
  `vendite.fatture` è classificata.
* `db/pgtap/vendite/test-af-emessa-non-lockata-reset-e-riporto-v1.sql` — le attività col marchio
  del giro e senza lucchetto.

---

### Note di migrazione

* 2026-11-25 — riservata al proprietario; la GUC del reset si spegne prima di uscire. Prima
  restava accesa fino alla fine della transazione, per il resto del verbo e per ciò che il backend
  faceva dopo, e i guard la onoravano senza chiedere chi scriveva
  (brief-db-porte-aperte-dalla-sola-guc, giro 1-7, D-W a).

---

{% include-markdown "signature-core.md" %}
