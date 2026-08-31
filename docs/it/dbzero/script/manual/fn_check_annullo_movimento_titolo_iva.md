## 📘 Documentazione Concettuale – Funzione `script.fn_check_annullo_movimento_titolo_iva`

> 👀 **Vedi anche**
>
> **Consumatori:**
>
> • [anagrafiche.fn_annulla_movimento_titolo_iva](/dbzero/anagrafiche/funzioni/fn_annulla_movimento_titolo_iva) — la madre, che solleva il **primo** motivo
> • [anagrafiche.trgfn_stiva_movimenti_guard_annullo](/dbzero/anagrafiche/funzioni/trgfn_stiva_movimenti_guard_annullo) — il guard, idem
> • [anagrafiche.vw_stiva_movimenti_dettaglio](/dbzero/anagrafiche/views/vw_stiva_movimenti_dettaglio) — la superficie, che **spegne il pulsante**
>
> **Sorgente:**
>
> • [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti)

---

### 🎯 Scopo Principale

(rev 2026-08-31 — funzione nata il 2026-08-31)

**Sorgente unica dei motivi per cui l'annullo di un movimento di plafond non si può
fare.** Ritorna `[]` se si può, altrimenti l'array **ordinato** dei motivi
ostativi: `[{codice, reason, reason_key, dettaglio, valori}, …]`.

---

### ⭐ Perché esiste come funzione a sé

Decisione di Tid del 2026-08-30: quando l'annullo non si può fare, l'operatore
deve trovare il pulsante **già spento, col motivo** — non scoprirlo premendo e
prendendo un errore.

Servono quindi **due lettori della stessa regola**: la superficie che spegne il
pulsante, e la madre che rifiuta.

> ⭐ **E la madre CHIAMA questa, non riscrive il predicato.** Un test che
> confrontasse i due esiti proverebbe che **oggi** coincidono; così si prova che
> **non possono divergere**, perché la regola sta scritta in un posto solo.
>
> Il presidio da scrivere non è «gli esiti coincidono», è **«la madre non
> contiene più il predicato»**.

---

### I motivi, in ordine

| # | `reason` | Quando |
| --- | --- | --- |
| 1 | `MOVIMENTO_NON_TROVATO` | il movimento indicato non esiste. ⭐ Qui «non esiste» è davvero «non esiste» — vedi il `SECURITY DEFINER` |
| 2 | `NON_FORZATURA` | è un `FATTURA` o un `NOTA_CREDITO`: è il riflesso di un documento, e si corregge **dal documento** con una nota di credito (`I4`) |
| 3 | `RIGA_DI_ANNULLO` | è esso stesso l'annullo di un'altra riga |
| 4 | `GIA_ANNULLATO` | esiste già una riga che lo annulla |
| 5 | `PLAFOND_NEGATIVO` | annullarlo porterebbe l'usato del titolo **sotto zero** |

⚠️ **Il terzo si chiamava `E_UN_ANNULLO` fino al 2026-08-31** (changeSet
`20260831-35`). Non nasceva come *«E\_ di errore»* ma come **«è un annullo»**, e
quel prefisso lo faceva leggere come un **codice errore** dal cancello che cerca
i letterali `E_*` nei corpi delle funzioni — rosso su un valore che un codice
non è. Regola e caso in [linee-guida-sql §12.5.1](/linee-guida-sql).

⚠️ **L'ordine è il contratto**: la superficie mostra il **primo** motivo e la madre
solleva il **primo** codice. Se divergesse, il tooltip direbbe una cosa e l'errore
un'altra — cioè il difetto di partenza spostato di un passo.

⚠️ I motivi 1 e 2 **interrompono** l'elenco: i successivi leggono il movimento, e
senza movimento (o su un tipo che non si annulla comunque) direbbero il falso.

---

### ⛔ `SECURITY DEFINER`, ed è la ragione per cui questo file esiste

`anagrafiche.soggetti_titoli_iva_movimenti` ha la **RLS attiva** (perimetro
emittente). Questa funzione deve **leggere il movimento indicato** per sapere che
tipo è — cioè legge una riga di una tabella protetta.

Da `SECURITY INVOKER` non distinguerebbe *«la riga non esiste»* da *«non la
vedo»*, e dovrebbe scegliere fra rifiutare con un messaggio fuorviante e passare
su una premessa non verificata.

> ⛔ **E la FK non ha lo stesso problema, ed è questo che li fa divergere.** In
> PostgreSQL i controlli di integrità referenziale **scavalcano sempre la RLS**.
> Quindi la FK accetterebbe un riferimento a una riga che il chiamante non vede,
> mentre una check `INVOKER` la tratterebbe come inesistente: i due
> **divergerebbero in silenzio**.

⚠️ **Il perimetro non si perde**: la **madre resta `INVOKER`**, quindi l'`INSERT`
della riga di annullo passa comunque dalla policy. Qui si scavalca la RLS per una
**lettura di coerenza**, non per una scrittura.

⚠️ `search_path` fissato: una `SECURITY DEFINER` senza `search_path` esplicito
esegue con quello del chiamante, che può anteporre uno schema.

---

### ⭐ Il motivo `PLAFOND_NEGATIVO`, e perché è qui e non fra gli errori

Annullare **riduce** l'usato, quindi di norma passa. Ma se nel frattempo le note di
credito hanno superato le fatture, togliere la forzatura porterebbe la somma sotto
zero — e l'accumulatore rifiuta.

Senza questo motivo l'operatore prenderebbe `E_TITOLO_IVA_UTILIZZATO_NEGATIVO`
dall'accumulatore: **vero, ma in quel momento non spiega né cosa è successo né
cosa può fare**.

⭐ La somma si calcola **senza** quel movimento, che è esattamente ciò che
l'accumulatore troverebbe dopo aver sommato il contro-movimento: `−x` annulla `+x`.

---

### ⚠️ `valori` viaggia col motivo

È il `VARIADIC` che la madre passa a `fn_log_and_raise_error`. Sta **qui**, accanto
al motivo, perché la frase che l'operatore legge non si ricomponga in due posti
diversi. È la stessa forma di `script.fn_check_accredito_annullabile`.

---

### Regole

* **Pura** (convenzione `fn_check_*`): nessun raise di dominio, nessuna scrittura,
  `STABLE`.
* Il **guard di parametro** invece solleva, ed è `TECNICO`: un id assente o non
  positivo non esce da nessuna interfaccia, lo produce un chiamante rotto.
* ⛔ **Non conia codici**: i motivi nominano codici già a catalogo. Se per
  scriverla servisse un codice nuovo, il difetto sarebbe a monte — la madre
  starebbe rifiutando senza saper dire perché.

---

### Test

`db/pgtap/anagrafiche/test-stiva-movimenti-annullo-v1.sql`.

⭐ L'asserzione **12** è quella che presidia il `SECURITY DEFINER`: la riga non si
vede da un perimetro cieco, e la check la vede lo stesso. ⚠️ **Salta** quando gira
da un ruolo a cui la RLS non si applica (owner, `BYPASSRLS`) — e lo **dichiara**,
perché lì il soggetto del test non esiste e asserire sarebbe verde per costruzione.

Cantiere: `brief-db-titoli-iva-movimenti-annullo.md`, decisione `B-3`.

---

{% include-markdown "signature-core.md" %}
