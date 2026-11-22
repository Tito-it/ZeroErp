## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_pdp_a10_guard`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.pdp](/dbzero/anagrafiche/tabelle/pdp) — la tabella protetta
>
> Approfondimento funzioni:
>
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — il blocco di colonna sullo stesso codice
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il rifiuto col diario

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_pdp_a10_guard` impedisce di cambiare il codice di un PDP e il suo indirizzo: un punto
fisico non cambia nome e non si sposta.

---

### Il PDP è un punto reale

Il codice è il riferimento con cui i sistemi esterni conoscono il punto (POD, PDR); l'indirizzo è il luogo
dove il punto sta. Cambiarli romperebbe l'allineamento con fuori e la chiave esterna composta con cui
un'istanza si lega al PDP del suo indirizzo. Un punto in un altro luogo è un PDP nuovo.

Scatta prima di una modifica che nomina il codice o l'indirizzo, e rifiuta se il valore cambia. Le due
colonne sono obbligatorie dalla nascita: non c'è una prima valorizzazione dopo la nascita, e ogni cambio è
rifiutato.

---

### ⚠️ Che cosa oggi non copre

* **Il blocco di colonna sul codice non parla mai.** Sul codice è montato anche il blocco generico di colonna,
  che scatta dopo questo guard: il rifiuto è sempre `E_COLONNA_NON_MODIFICABILE`, mai il suo
  `E_CODICE_NON_MODIFICABILE`, e la sua porta di manutenzione non apre niente perché il guard ha già
  rifiutato.
* **Il rifiuto non nomina il campo.** Il contesto porta la colonna sotto una chiave che il form non legge: il
  campo da evidenziare non arriva.

---

### Codici errore

* `E_COLONNA_NON_MODIFICABILE` — cambio del codice o dell'indirizzo; nella frase la colonna e il valore di
  prima.

---

### Test

* `db/pgtap/anagrafiche/test-trgfn-pdp-a10-guard.sql` — il cambio del codice e quello dell'indirizzo
  rifiutati, e i valori che restano quelli di prima.

---

### Note di migrazione

* Prima si chiamava `anagrafiche.trgfn_pdp_protect_cols`, col trigger `trg_pdp_protect_cols_upd`.

---

{% include-markdown "signature-core.md" %}
