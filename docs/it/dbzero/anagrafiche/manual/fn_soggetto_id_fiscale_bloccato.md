## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_soggetto_id_fiscale_bloccato`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la riga da cui legge il valore
> * [dbops.lock_columns_conditional](/dbzero/dbops/tabelle/lock_columns_conditional) — le due righe del form che la chiamano
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_id_fiscale_bloccato](/dbzero/anagrafiche/funzioni/fn_id_fiscale_bloccato) — la regola a cui chiede
> * [dbops.fn_non_editable_fields](/dbzero/dbops/funzioni/fn_non_editable_fields) — chi la valuta per il form
> * [anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_id_fiscale_immutabile) — il guard che rifiuta ciò che il form spegne

---

### 🎯 Scopo Principale

`anagrafiche.fn_soggetto_id_fiscale_bloccato` dice se il codice fiscale o la partita IVA di un soggetto, dato il
soggetto e il nome della colonna, sono bloccati. È la regola di `anagrafiche.fn_id_fiscale_bloccato` letta sulla
riga, per il form.

---

### Il form ha l'id, non il valore

Il form sa quale soggetto sta mostrando, non il valore dei campi come il database lo ha. Questa funzione legge
dal soggetto il valore della colonna indicata (`codice_fiscale` o `partita_iva`) e lo passa alla regola: non ne
ha una sua.

È la condizione delle due righe di `dbops.lock_columns_conditional` su `anagrafiche.soggetti`, che
`dbops.fn_non_editable_fields` valuta per dire al form quali campi spegnere. All'operatore il form spegne i campi
già scritti e lascia acceso un campo vuoto; al SUPER_ADMIN li lascia accesi. Poiché il guard chiede alla stessa
regola, il form spegne esattamente ciò che il guard rifiuterebbe.

Un soggetto che non esiste, o una colonna diversa da quelle due, danno falso: niente da spegnere.

---

### Codici errore

Nessuno: risponde vero o falso.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-id-fiscale-immutabile-v1.sql` — il form dell'operatore spegne CF e P.IVA
  scritti e lascia acceso un campo vuoto; quello del SUPER_ADMIN li lascia accesi.

---

### Note di migrazione

* 2026-11-09 — nasce con le due righe del form, insieme al guard.

---

{% include-markdown "it/dbzero/anagrafiche/_identificativo-fiscale.md" %}

---

{% include-markdown "signature-core.md" %}
