## 📘 Documentazione Concettuale – Funzione `vendite.fn_preventivo_in_smistamento()`

> **Ultimo aggiornamento**: 15 novembre 2026
>
> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi) — da dove viene la colonna `accettazione`
>
Approfondimento funzioni:
> • [vendite.fn_preventivo_proietta_stato_smistamento](/dbzero/vendite/funzioni/fn_preventivo_proietta_stato_smistamento) — la proiezione dello stato, che parte da qui
> • [script.fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo) — la capability, che ne fa `in_smistamento`

---

### 🎯 Scopo Principale

**Il preventivo, in questo stato, è uno che si smista?**

Smistare un preventivo vuol dire mandarne la merce in un ordine e i servizi in una commessa. Si
smista da due stati:

* lo **stato di accettazione**, quello che il vocabolario marca con la colonna `accettazione` di
  `config.stati_doc_preventivi` (oggi `ACCETTATO`);
* **`EVASO`**, la destinazione del processo di smistamento, dove il preventivo resta in
  consultazione e torna indietro se un ordine o una commessa vengono annullati. Questo stato non ha
  una colonna e si nomina col codice, come lo nomina la matrice.

La risposta sta solo qui. La leggono in due: la proiezione dello stato, che parte solo da un
preventivo che si smista, e la capability, che la espone al frontend come `in_smistamento`. Così il
pannello dello smistamento e la proiezione non possono dire cose diverse, e il frontend non deve
tenere una sua lista di stati.

| Argomenti | Risposta |
| --- | --- |
| `p_accettazione` vero | `true` |
| `p_stato = 'EVASO'` | `true` |
| ogni altro caso, anche con un argomento `NULL` | `false` (mai `NULL`) |

⚠️ **Non dice che un invio si possa fare adesso.** Un preventivo accettato con tutte le righe già
smistate si smista ancora (il pannello si vede), ma non ha niente da inviare: quello lo dicono
`can_push_commessa` e `can_genera_ordine` della capability.

---

### Forma

Riceve i **valori** dello stato (la colonna `accettazione` e il `codice_interno`), non l'id del
preventivo: non legge tabelle, è `LANGUAGE sql` e `IMMUTABLE`. Chi la chiama ha già letto lo stato.
Non è `STRICT`: un argomento `NULL` è un caso, e la risposta resta `false`.
