## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_psp_guard_ruolo_psp`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.psp](/dbzero/anagrafiche/tabelle/psp) — la specializzazione che presidia
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli) — il ruolo `PSP`
>
> Approfondimento funzioni:
>
> * [script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo) — il controllo, a cui delega per intero
> * [pagamenti.trgfn_enti_incasso_guard_psp](/dbzero/pagamenti/funzioni/trgfn_enti_incasso_guard_psp) — lo stesso tipo di ruolo, controllato dal lato degli enti d'incasso

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_psp_guard_ruolo_psp` è il guard di ruolo del PSP: la riga di `anagrafiche.psp` punta solo a
un ruolo `PSP`.

---

### Che cosa ha di proprio il PSP

Il codice del ruolo è `PSP`. Lo stesso tipo di ruolo lo controlla, per conto suo,
anche `pagamenti.trgfn_enti_incasso_guard_psp`, che non passa da `script.fn_guard_soggetto_ruolo`: lì un ruolo
d'altro tipo risponde con un codice proprio degli enti d'incasso, e in più si chiede che il PSP abbia qui una riga
attiva.

---

{% include-markdown "it/dbzero/anagrafiche/_guard-di-ruolo.md" %}

---

### Test

* `db/pgtap/pagamenti/test-enti-incasso-psp.sql` — passa da questo guard quando crea il PSP di prova, con un ruolo
  `PSP`. Nessun test prova il rifiuto di un ruolo d'altro tipo su `anagrafiche.psp`.

---

{% include-markdown "signature-core.md" %}
