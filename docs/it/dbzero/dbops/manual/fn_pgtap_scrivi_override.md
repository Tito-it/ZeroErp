## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_scrivi_override`

> **Ultimo aggiornamento**: 27 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.user_override_aree](/dbzero/config/tabelle/user_override_aree) / [config.user_override_azioni](/dbzero/config/tabelle/user_override_azioni) / [config.user_override_oggetti](/dbzero/config/tabelle/user_override_oggetti) — le eccezioni che cambia
>
> Approfondimento funzioni:
>
> * [config.fn_imposta_override_aree](/dbzero/config/funzioni/fn_imposta_override_aree) / [config.fn_imposta_override_azioni](/dbzero/config/funzioni/fn_imposta_override_azioni) / [config.fn_imposta_override_oggetti](/dbzero/config/funzioni/fn_imposta_override_oggetti) — i verbi veri che chiama
> * [dbops.fn_pgtap_entra_come_super_admin](/dbzero/dbops/funzioni/fn_pgtap_entra_come_super_admin) / [dbops.fn_pgtap_rimetti_contesto](/dbzero/dbops/funzioni/fn_pgtap_rimetti_contesto) — il SUPER_ADMIN di fixture, e il contesto che torna
> * [dbops.fn_pgtap_concedi_livello_area](/dbzero/dbops/funzioni/fn_pgtap_concedi_livello_area) / [dbops.fn_pgtap_concedi_azione](/dbzero/dbops/funzioni/fn_pgtap_concedi_azione) / [dbops.fn_pgtap_nega_azione](/dbzero/dbops/funzioni/fn_pgtap_nega_azione) / [dbops.fn_pgtap_apri_area_per_nascita](/dbzero/dbops/funzioni/fn_pgtap_apri_area_per_nascita) — i builder che la usano
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — il permesso si costruisce, non si cerca

---

### 🎯 Scopo Principale

In un test, **cambia (o toglie) una sola eccezione** di un utente e lascia le altre. Ritorna
l'eccezione di prima, o niente se non c'era: è il ricordo per rimetterla.

---

### ⭐ Perché esiste

Le eccezioni utente sono in sola lettura per l'applicazione, e le scrivono solo i verbi del
SUPER_ADMIN, che **sostituiscono l'elenco intero** di un utente. Un test vuole invece cambiare
un'eccezione e lasciare le altre. La fixture fa questo passaggio una volta sola:

1. legge l'elenco dell'utente com'è;
2. toglie l'eccezione con la chiave data e, se ci sono i valori nuovi, la rimette coi valori nuovi;
3. entra come SUPER_ADMIN di fixture, chiama il verbo vero della tabella, e rimette il contesto di
   prima, anche se il verbo rifiuta.

Il test passa così dalla stessa strada dell'amministratore, coi suoi controlli.

⚠️ L'elenco si riscrive intero: gli id delle righe dell'utente cambiano, e la colonna `meta`, che il
verbo non scrive, si perde.

---

### Codici errore

Valgono quelli del verbo. Una tabella fuori dalle tre, un utente o una chiave mancanti sono eccezioni
senza codice sollevate dalla fixture: è la fixture a essere chiamata male.

---

### Test

`db/pgtap/config/test-porta-override-permessi-v1.sql`, e i test che la usano per le eccezioni con
valori scelti (per esempio `db/pgtap/vendite/test-porta-ddt-riconsegna-v1.sql`).

---

### Note di migrazione

* 2026-11-27 — nasce quando le eccezioni utente passano in sola lettura per l'applicazione
  (brief-db-porte-aperte-dalla-sola-guc, giro 10-quater).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
