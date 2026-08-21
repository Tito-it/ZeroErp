## 📘 Documentazione Concettuale – Funzione `acquisti.trgfn_acq_ordini_only_consegna_tipo_con()`

> 👀 **Vedi anche**
>
> • [acquisti.ordini](/dbzero/acquisti/tabelle/ordini)
> • [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi)
> • [config.tipi_indirizzi](/dbzero/config/tabelle/tipi_indirizzi)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Impone che l'**indirizzo di consegna** di un ordine di acquisto sia davvero un indirizzo di
consegna: `config.tipi_indirizzi.codice_interno` deve valere `'CON'`.

Sembra un controllo superfluo, e non lo è: gli indirizzi di un soggetto stanno **tutti nella
stessa tabella**, distinti solo dal loro tipo. La FK garantisce che l'indirizzo esista, non
che sia quello giusto — nulla impedirebbe di far consegnare la merce alla sede legale o
all'indirizzo di fatturazione.

---

### Aggancio

`BEFORE INSERT OR UPDATE` su `acquisti.ordini`.

---

### Regole applicate

1. Risale `indirizzi → tipi_indirizzi` per l'`indirizzo_consegna_id` della riga;
2. se il codice interno **è distinto da** `'CON'` → `E_TIPO_INDIRIZZO`.

⚠️ Il confronto è `IS DISTINCT FROM`, quindi copre anche il caso in cui l'indirizzo **non
esista** o non abbia tipo: la `SELECT INTO` lascia la variabile a `NULL`, e `NULL` è distinto
da `'CON'`. Il guard è fail-closed — ma il messaggio riporta `codice_interno = null`, che va
letto come «indirizzo non trovato», non come «indirizzo senza tipo».

⚠️ Se `indirizzo_consegna_id` è **nullo**, vale lo stesso: la riga viene rifiutata. Il guard
rende quindi l'indirizzo di consegna **di fatto obbligatorio**, indipendentemente da come è
dichiarata la colonna. È da verificare che sia l'intenzione — un ordine può nascere prima di
sapere dove sarà consegnato.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_TIPO_INDIRIZZO` | `indirizzo_consegna_id` non punta a un indirizzo di tipo `CON` (compresi nullo e inesistente) |

Sollevato via `script.fn_log_and_raise_error`; il context riporta tabella, ordine, indirizzo e
il codice interno trovato.

---

{% include-markdown "it/dbzero/acquisti/_dominio-acquisti.md" %}

---

{% include-markdown "signature-core.md" %}
