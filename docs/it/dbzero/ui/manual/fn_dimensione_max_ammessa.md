## 📘 Documentazione Concettuale – Funzione `ui.fn_dimensione_max_ammessa`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente) — il numero di card scelto dall'utente
> * [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset) — il numero di card del preset
>
> Approfondimento funzioni:
>
> * [ui.fn_check_forma_configurazione](/dbzero/ui/funzioni/fn_check_forma_configurazione) — la usa per rifiutare la scrittura
> * [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config) — la usa in lettura
> * [ui.fn_intero_da_jsonb](/dbzero/ui/funzioni/fn_intero_da_jsonb) — dice prima se il valore è un intero

---

### 🎯 Scopo Principale

`ui.fn_dimensione_max_ammessa` dice se un numero di card della home è ammesso: vero da 1 a 100,
falso per ogni altro valore e per nessun valore.

---

### Un tetto, una sede

`dimensione_max` dice quante card al più una dashboard mostra. Non è una misura di un catalogo come
le righe per pagina delle liste: è un tetto, e il tetto ha una regola sola, scritta qui. La leggono il
guard di forma della preferenza, che rifiuta alla scrittura un numero fuori dal tetto, il CHECK del
preset ([dashboard_preset](/dbzero/ui/tabelle/dashboard_preset), `chk_ui_dashboard_preset_dimensione_max`,
dove un valore vuoto vuol dire «lo standard»), e il resolver
delle dashboard, che a un valore non ammesso trovato in una riga preferisce quello del preset o del
catalogo.

⛔ «Nessun tetto» non esiste: una dashboard ha sempre un massimo. Zero o un negativo non vogliono dire
«senza limite», sono valori non ammessi.

---

### Codici errore

Nessuno.

---

### Test

* `db/pgtap/ui/test-ui-forma-configurazione-v1.sql` — una preferenza di dashboard con 101 card
  rifiutata.
* `db/pgtap/ui/test-ui-misure-catalogo-e-uso-v1.sql` — un preset a 0 e uno a 101 rifiutati dal CHECK.

---

### Note di migrazione

* 2026-11-21 — nasce: il tetto di 100 stava solo nel backend, e il resolver accettava qualunque
  intero positivo della preferenza. Lo stesso giorno la legge anche il CHECK del preset.

---

{% include-markdown "signature-core.md" %}
