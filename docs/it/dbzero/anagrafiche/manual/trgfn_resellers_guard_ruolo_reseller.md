## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_resellers_guard_ruolo_reseller`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.resellers](/dbzero/anagrafiche/tabelle/resellers) — la specializzazione che presidia
> * [anagrafiche.resellers_billing_account](/dbzero/anagrafiche/tabelle/resellers_billing_account) — il legame che nomina lo stesso ruolo, senza guard
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli) — il ruolo `RE`
>
> Approfondimento funzioni:
>
> * [script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo) — il controllo, a cui delega per intero

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_resellers_guard_ruolo_reseller` è il guard di ruolo del reseller: la riga di
`anagrafiche.resellers` punta solo a un ruolo `RE`.

---

### Che cosa ha di proprio il reseller

Il codice del ruolo è `RE`. Il commento della tabella dice «RES», che in `config.tipi_ruoli` non c'è: vale il
codice del guard.

Il guard presidia solo la tabella dei reseller. Il legame con i billing account,
`anagrafiche.resellers_billing_account`, nomina il ruolo del reseller direttamente, e su quella tabella nessun
guard di ruolo scatta: lì un ruolo di qualunque tipo è accettato.

---

{% include-markdown "it/dbzero/anagrafiche/_guard-di-ruolo.md" %}

---

{% include-markdown "signature-core.md" %}
