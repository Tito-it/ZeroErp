## 📘 Documentazione Concettuale – Funzione `script.fn_check_contratto_sovrapposto`
### 🎯 Scopo Principale
(latest review 20-10-2026)

Dice se il **periodo di un contratto si sovrappone a un contratto vincolante** dello
stesso cliente, punto di fornitura, utility e ambito. Funzione **pura**
(`fn_check_*`): non solleva errori di dominio e non scrive. Ritorna `[]` quando il
periodo è libero.

**Sede unica della regola all'attivazione.** La legge
`vendite.trgfn_contratti_guard_transizione_stato`, che verso ATTIVO solleva il
codice del motivo; e la legge `script.fn_available_actions_contratto`, che spegne
«Attiva» e dice perché, invece di far scoprire il vincolo alla conferma.

> 👀 **Vedi anche**
>
> [vendite.fn_contratto_sovrapposto](/dbzero/vendite/funzioni/fn_contratto_sovrapposto) — il predicato, che questa funzione chiama
> [vendite.trgfn_contratti_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_contratti_guard_transizione_stato)
> [script.fn_available_actions_contratto](/dbzero/script/funzioni/fn_available_actions_contratto)
> [vendite.contratti](/dbzero/vendite/tabelle/contratti) — il vincolo `ex_contratti_no_overlap`
> [script.fn_check_listino_congelabile](/dbzero/script/funzioni/fn_check_listino_congelabile) — il gemello per forma (valori come parametri)

---

### Perché esiste

Richiesta del team BE, 2026-10-19:

> *Un cliente ha già un contratto ATTIVO. Su una seconda bozza con lo stesso cliente,
> punto di fornitura, utility e ambito, e con periodo sovrapposto, «Attiva» è acceso.
> Premuto, si apre il dialog della stampa, e solo alla conferma arriva il rifiuto.*

La regola c'era, ma solo nel vincolo di esclusione (un errore generico, alla
scrittura) e in una copia nel backend (alla conferma). Né il pulsante né il guard di
transizione la conoscevano.

---

### Che cosa vuol dire «vincolante»

Un contratto è vincolante quando **non è in bozza e non è annullato**: attivo, e
anche **cessato**. È lo stesso criterio del vincolo di esclusione
(`partecipa_overlap_snapshot`). Quindi:

* una bozza non blocca nessuno: due bozze sovrapposte sono ammesse, e servono a
  preparare una successione;
* un contratto cessato blocca ancora il periodo che ha coperto.

---

### Il motivo

| Campo | Valore |
| --- | --- |
| `codice` | `E_CONTRATTO_OVERLAP_ESISTENTE` (lo stesso del push offerta → contratto) |
| `reason` | `CONTRATTO_SOVRAPPOSTO` |
| `reason_key` | `vendite.contratti.azione_reason.contratto_sovrapposto` |
| `dettaglio` | `contratto_sovrapposto_id`, `contratto_sovrapposto_numero` |
| `valori` | `[numero]`: il `%s` del messaggio e il `{0}` del testo del pulsante |

---

### Parametri: i valori, non l'id

La funzione riceve la **quintupla** del vincolo (billing account, istanza utility,
utility, ambito, valido dal, valido al), non l'id del contratto. Il guard che la
chiama gira **prima** della scrittura: riletta dal database, la riga avrebbe ancora
le date di prima, e chi attiva spostando le date nella stessa scrittura verrebbe
giudicato sul periodo vecchio. Il guard passa i valori nuovi, il pulsante quelli
salvati.

`valido_al` vuoto è un contratto senza scadenza: è un valore, non «nessun controllo».

Non serve escludere il contratto stesso: la funzione si chiama per un contratto che
va verso ATTIVO, e ci si arriva solo dalla bozza, che non è vincolante.

---

### Limite dichiarato: il perimetro degli emittenti

La funzione legge i contratti con i permessi di chi attiva. Un contratto vincolante
che l'operatore non vede non dà motivo: il pulsante resta acceso e alla conferma
risponde il vincolo di esclusione. È voluto (decisione di Tid, 2026-10-19): il motivo
nominerebbe un contratto fuori dal perimetro dell'operatore.

---

{% include-markdown "signature-core.md" %}
