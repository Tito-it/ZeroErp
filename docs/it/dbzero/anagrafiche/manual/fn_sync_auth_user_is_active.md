## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_sync_auth_user_is_active`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — le vesti della credenziale
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane) — il rapporto che l'operatore umano pretende
>
> Approfondimento funzioni:
>
> * [script.fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile) — la regola «la veste vale oggi», a cui la funzione delega
> * [anagrafiche.trgfn_identita_digitali_sync_auth_user_active](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_sync_auth_user_active) — la chiama a ogni scrittura su una veste
> * [anagrafiche.trgfn_risorse_umane_sync_auth_user_active](/dbzero/anagrafiche/funzioni/trgfn_risorse_umane_sync_auth_user_active) — la chiama a ogni cambio del rapporto
> * [anagrafiche.fn_sync_auth_user_expired](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_expired) — la chiama ogni ora, per le credenziali rimaste indietro
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — vesti, credenziali e il blocco del login

---

### 🎯 Scopo Principale

`anagrafiche.fn_sync_auth_user_is_active` allinea `django.auth_user.is_active` di una credenziale alle sue vesti:
la accende se almeno una veste è utilizzabile oggi, altrimenti la spegne. Restituisce vero solo se ha cambiato il
flag.

---

### Decide sull'insieme delle vesti, non su una

La funzione non sa quale veste è cambiata e non le serve: guarda tutte le vesti della credenziale e chiede a
`script.fn_veste_utilizzabile` se almeno una vale oggi. Che cosa voglia dire «utilizzabile» lo decide quella
funzione, e qui non è ricopiato: la veste accesa, nelle sue date, col soggetto attivo e, per l'operatore umano,
col rapporto attivo e nelle sue date.

Una credenziale che **non ha nessuna veste** risulta da spegnere: se è accesa, la funzione la spegne. Per questo il
passaggio periodico non la propone, e i trigger non la chiamano mai su una credenziale che non sia quella di una
veste.

---

### Scrive solo se cambia

Il flag si scrive solo quando il suo valore è diverso da quello calcolato: chiamarla due volte di seguito non
cambia niente, e la seconda volta restituisce falso. Il ritorno serve al passaggio periodico per contare le
credenziali riallineate.

Restituisce falso, senza scrivere, anche quando la credenziale non esiste in `django.auth_user` e quando lo schema
Django non c'è (un database di sola integrazione continua): la tabella si raggiunge per nome, a tempo di esecuzione.

---

{% include-markdown "it/dbzero/anagrafiche/_sincronizzazione-accesso.md" %}

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — la credenziale non è passata, o non è un numero positivo.

---

### Test

* `db/pgtap/anagrafiche/test-sync-auth-user-is-active-multi-role.sql` — il rifiuto della credenziale non valida, la
  credenziale senza vesti (che il test si aspetta lasciata com'è: vale solo se è già spenta), le vesti dei portali e dello shop, la veste spenta e quella fuori dalle sue date.
* `db/pgtap/anagrafiche/test-fn-sync-auth-user-is-active-or.sql` — più vesti sulla stessa credenziale: basta una
  utilizzabile.
* `db/pgtap/script/test-fn-veste-utilizzabile-v1.sql` (caso 17) — col rapporto chiuso la credenziale dell'operatore
  si spegne.

I primi due sono **rossi** in baseline.

---

### Note di migrazione

* 2026-04-18 — la funzione riceve la credenziale invece della risorsa umana: alcuni chiamanti del backend le
  passavano già una credenziale.
* 2026-04-20 — con il modello a più vesti la credenziale è accesa se **almeno una** veste è utilizzabile. Cadono la
  lettura del ponte `risorse_umane_auth_user` e il secondo controllo sull'operatore.
* 2026-10-02 — «spenta» si legge solo da `attivo`: `DISABILITATO` non è più un tipo di veste.
* 2026-10-07 — la regola si legge da `script.fn_veste_utilizzabile`, che per l'operatore umano guarda di nuovo il
  rapporto: la fine del rapporto spegne la credenziale se non le resta un'altra veste utilizzabile.

---

{% include-markdown "signature-core.md" %}
