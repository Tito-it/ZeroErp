## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la tabella che il guard presidia
> * [dbops.lock_columns_conditional](/dbzero/dbops/tabelle/lock_columns_conditional) — le due righe che spengono CF e P.IVA nel form
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_id_fiscale_bloccato](/dbzero/anagrafiche/funzioni/fn_id_fiscale_bloccato) — la regola, a cui il guard chiede
> * [anagrafiche.fn_soggetto_id_fiscale_bloccato](/dbzero/anagrafiche/funzioni/fn_soggetto_id_fiscale_bloccato) — la stessa regola, per il form
> * [anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_cf_piva_obbligatori) — la presenza di CF e P.IVA
> * [anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch](/dbzero/anagrafiche/funzioni/trgfn_soggetti_valida_cf_piva_dispatch) — il formato di CF e P.IVA

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile` rifiuta il cambio, o lo svuotamento, di un codice
fiscale o di una partita IVA già scritti, salvo che a farlo sia il SUPER_ADMIN.

---

### Il guard chiede alla regola, col valore di prima

Il guard scatta in modifica, quando la scrittura nomina il codice fiscale o la partita IVA; alla nascita non c'è
niente da proteggere. Per ognuno dei due campi, prima il CF e poi la P.IVA:

* se il valore nuovo è uguale a quello di prima, il campo passa: riscrivere lo stesso valore non è un cambio;
* altrimenti chiede a `anagrafiche.fn_id_fiscale_bloccato` se il **valore di prima** è bloccato. Un campo che
  era vuoto non lo è, e si riempie; uno scritto lo è, salvo per il SUPER_ADMIN.

Il guard non ha una regola sua. La stessa funzione decide che cosa il form spegne: form e database non possono
dire due cose diverse.

Il confronto è sul valore scritto: il database non normalizza i due campi.

---

### Codici errore

* `E_SOGGETTO_ID_FISCALE_IMMUTABILE` — un CF o una P.IVA già scritti cambiano o si svuotano. Il campo
  dell'errore è la colonna (`codice_fiscale` o `partita_iva`), così il form sa quale segnare; il messaggio nomina
  il dato.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-id-fiscale-immutabile-v1.sql` — il guard montato sulle due colonne; il
  cambio di un CF o di una P.IVA scritti e lo svuotamento della P.IVA rifiutati col campo giusto; lo stesso
  valore riscritto che passa; il SUPER_ADMIN che corregge; il campo vuoto che si riempie e poi è bloccato; il
  form che spegne gli stessi campi.

---

### Note di migrazione

* 2026-11-09 — nasce, con la regola e le righe del form. Decisione di Tid: CF e P.IVA scritti non si cambiano,
  salvo il SUPER_ADMIN. Prima la regola viveva solo nel form.

---

{% include-markdown "it/dbzero/anagrafiche/_identificativo-fiscale.md" %}

---

{% include-markdown "signature-core.md" %}
