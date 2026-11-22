## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_identita_digitali_sync_auth_user_active`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.identita_digitali](/dbzero/anagrafiche/tabelle/identita_digitali) — le vesti su cui il trigger scatta
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_sync_auth_user_is_active](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_is_active) — la funzione a cui delega
> * [script.fn_veste_utilizzabile](/dbzero/script/funzioni/fn_veste_utilizzabile) — la regola «la veste vale oggi»
> * [anagrafiche.trgfn_risorse_umane_sync_auth_user_active](/dbzero/anagrafiche/funzioni/trgfn_risorse_umane_sync_auth_user_active) — il gemello sul rapporto
> * [anagrafiche.fn_sync_auth_user_expired](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_expired) — il passaggio periodico che copre ciò che il trigger non vede
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — vesti, credenziali e il blocco del login

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_identita_digitali_sync_auth_user_active` riallinea `django.auth_user.is_active` della credenziale
di una veste ogni volta che la veste nasce o cambia in ciò che decide se è utilizzabile.

---

### Scatta su cinque colonne, senza confrontarle

Il trigger scatta dopo l'inserimento di una veste e dopo ogni modifica che nomina `attivo`, `valido_dal`,
`valido_al`, `ruolo_applicativo` o `auth_user_id`. Non confronta il valore vecchio col nuovo: una modifica che
riscrive una di queste colonne con lo stesso valore lo fa scattare lo stesso. Non costa niente di più che una
lettura, perché `fn_sync_auth_user_is_active` scrive la credenziale solo se il suo stato cambia.

Le altre colonne (`meta`, `invito_inviato_at`, le colonne di audit) non lo fanno scattare.

---

### Guarda solo la credenziale della riga nuova

Il trigger passa a `fn_sync_auth_user_is_active` la credenziale scritta nella riga **nuova** della veste, e non
decide niente da solo: che la credenziale debba essere accesa lo calcola la funzione, sull'insieme di tutte le sue
vesti. Una veste che si spegne spegne la credenziale solo se non le resta un'altra veste utilizzabile.

---

### Arriva dopo i controlli della riga

Il trigger è dell'ultima fase, dopo la scrittura: una veste che i controlli rifiutano (il tipo incoerente col ruolo,
la credenziale che mescolerebbe persona e macchina, l'ultimo amministratore) non arriva fin qui. Gira nella stessa
transazione di chi scrive, coi suoi permessi.

---

### ⚠️ Che cosa oggi non copre

* **La credenziale di prima.** Quando una veste passa a un'altra credenziale, quella di prima resta com'era: se le
  restano altre vesti la riallinea il passaggio periodico, se era la sua ultima veste non la riallinea nessuno.
* **La cancellazione.** Sul `DELETE` il trigger non scatta: la credenziale di una veste cancellata resta com'era,
  con la stessa conseguenza.
* **Il ruolo del soggetto e la natura.** Un cambio di `soggetto_ruolo_id` o di `tecnica` che non nomina nessuna
  delle cinque colonne non lo fa scattare, e per l'operatore sposta il rapporto che la regola guarda.

---

{% include-markdown "it/dbzero/anagrafiche/_sincronizzazione-accesso.md" %}

---

### Codici errore

Il trigger non ne solleva di suoi. `fn_sync_auth_user_is_active` rifiuta una credenziale assente o non positiva con
`E_PARAMETRO_INVALIDO`, ma qui la colonna `auth_user_id` è obbligatoria.

---

### Test

* `db/pgtap/anagrafiche/test-veste-operatore-spenta-v1.sql` — spegnere e riaccendere la veste operatore spegne e
  riaccende la credenziale.
* `db/pgtap/anagrafiche/test-sync-auth-user-is-active-multi-role.sql` e
  `db/pgtap/anagrafiche/test-fn-sync-auth-user-is-active-or.sql` — le vesti dei portali e dello shop, e più vesti
  sulla stessa credenziale. Sono **rossi** in baseline.

Nessun test prova il cambio di credenziale di una veste, la cancellazione o il cambio di `soggetto_ruolo_id`.

---

### Note di migrazione

* 2026-04 — nasce con `identita_digitali`, accanto al trigger del ponte `risorse_umane_auth_user`.
* 2026-09-12 — il ponte è ritirato: le vesti sono l'unica sede del legame fra un ruolo e la credenziale.
* 2026-10-02 — `DISABILITATO` non è più un tipo di veste: una veste si spegne con `attivo = false`.

---

{% include-markdown "signature-core.md" %}
