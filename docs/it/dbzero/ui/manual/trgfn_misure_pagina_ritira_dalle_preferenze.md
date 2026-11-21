## 📘 Documentazione Concettuale – Trigger function `ui.trgfn_misure_pagina_ritira_dalle_preferenze`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina) — il catalogo da cui la misura esce
> * [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente) — le preferenze che la perdono
>
> Approfondimento funzioni:
>
> * [ui.fn_intero_da_jsonb](/dbzero/ui/funzioni/fn_intero_da_jsonb) — legge la misura scritta nella preferenza
> * [ui.trgfn_preferenza_guard_forma](/dbzero/ui/funzioni/trgfn_preferenza_guard_forma) — il guard che giudica ciò che resta

---

### 🎯 Scopo Principale

`ui.trgfn_misure_pagina_ritira_dalle_preferenze` fa uscire una misura ritirata dal catalogo anche
dalle preferenze di lista che la citano. Della preferenza si toglie solo la misura: le colonne
restano, e la persona torna allo standard della lista.

---

### Perché serve

Il preset cita la misura con una FK, e una misura che un preset usa non si toglie. La preferenza
invece porta la misura dentro un campo JSONB, dove una FK non arriva: senza questa funzione la
misura si toglieva, la preferenza restava con un numero che il catalogo non ha più, e il guard di
forma rifiutava ogni salvataggio successivo, anche delle sole colonne.

È montata `AFTER DELETE`, riga per riga, su [misure_pagina](/dbzero/ui/tabelle/misure_pagina). Il
solo DELETE basta: una misura non si riscrive (lucchetto di colonna), e cambiare l'uso di default
non tocca le preferenze, che citano il numero.

La riscrittura delle preferenze passa dai loro trigger, come ogni scrittura di dominio: il guard di
forma giudica la configurazione che resta.

---

### Codici errore

* `E_TRIGGER_ARGOMENTI_INVALIDI` — la funzione montata su un'altra tabella, o non come trigger
  `AFTER DELETE` di riga.
* I codici del guard di forma, se la configurazione che resta non ha la forma ammessa.

---

### Test

* `db/pgtap/ui/test-ui-misure-catalogo-e-uso-v1.sql` — la misura ritirata esce dalla preferenza che
  la cita con le colonne intatte, la preferenza con un'altra misura non cambia, e la preferenza si
  salva di nuovo.

---

### Note di migrazione

* 2026-11-21 — nasce: prima una misura citata solo da preferenze si toglieva, e le preferenze non si
  salvavano più.

---

{% include-markdown "signature-core.md" %}
