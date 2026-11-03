## 📘 Documentazione Concettuale – Trigger function `pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti) — la tabella su cui il trigger è montato
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — la riga da cui copia i riferimenti
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_posta_contabile](/dbzero/pagamenti/funzioni/fn_posta_contabile) — il posting, che scrive il movimento nominando la riga

---

### 🎯 Scopo Principale

Tiene i riferimenti di un movimento coerenti con la sua riga contabile: quando il movimento
nomina una riga (`contabile_riga_id`), ne copia testata, fattura, billing account e rata, e
rifiuta un valore passato dal chiamante che dica un'altra cosa.

---

### Il movimento non racconta una storia diversa dalla sua riga

Se il movimento porta `contabile_riga_id`, il trigger legge dalla riga i quattro riferimenti
(`contabile_id`, `fattura_id`, `billing_account_id`, `scadenza_id`):

* un riferimento passato dal chiamante e **diverso** da quello della riga è rifiutato;
* un riferimento lasciato vuoto, o uguale, passa;
* in ogni caso, alla fine, i quattro valori sono quelli della riga.

⭐ Per questo i riferimenti del movimento non sono una seconda sorgente di verità: chi scrive il
movimento non li decide, li riceve.

⚠️ La rata segue la stessa regola degli altri tre: se la riga non ha rata, anche il movimento
resta senza, e un chiamante che ne passa una è rifiutato.

---

### ⭐ Da una riga non abbinata non nasce un movimento

È il rifiuto centrale del posting: una riga senza fattura o senza billing account non è ancora
attribuita a un documento, e un movimento è per definizione denaro già attribuito.

---

### ⚠️ Vale solo per i movimenti che nominano una riga

`contabile_riga_id` è facoltativo. Un movimento scritto senza riga non incontra questo trigger:
fattura e billing account deve portarli lui, o lo ferma il `NOT NULL`. Non è il percorso del
posting, è il percorso di chi scrive a mano.

---

### Codici errore

* `E_RIGA_CONTABILE_NON_TROVATA` (`NON_TROVATO`) — la riga nominata non esiste.
* `E_RIGA_CONTABILE_SENZA_ABBINAMENTO` (`CONFLITTO_STATO`) — la riga non ha fattura o billing
  account.
* `E_MOVIMENTO_RIFERIMENTO_INCOERENTE` (`DATO_ERRATO`) — uno dei quattro riferimenti passati è
  diverso da quello della riga; il contesto dice quale.

---

### Test

* `db/pgtap/pagamenti/test-vendite-movimenti-contabile-riga.sql` — la testata derivata dalla
  riga, un valore manuale coerente accettato, uno incoerente rifiutato.
* `db/pgtap/pagamenti/test-abbinamento-rata.sql` — il posting copia la rata sul movimento, e un
  movimento che nomina un'altra rata è rifiutato.

---

### Note di migrazione

* 2026-02-13 — prima stesura, sui tre riferimenti testata, fattura e billing account.
* 2026-08-21 — i rifiuti, fino ad allora `E_GENERICO`, passano ai codici registrati. Nessun
  predicato è cambiato.
* 2026-08-22 — si copia anche `scadenza_id`: da tre riferimenti a quattro, stesso meccanismo e
  stesso rifiuto.

---

{% include-markdown "signature-core.md" %}
