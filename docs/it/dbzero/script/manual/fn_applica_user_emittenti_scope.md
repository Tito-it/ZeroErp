## 📘 Documentazione Concettuale – Funzione `script.fn_applica_user_emittenti_scope`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali) — la riga che sposta
>
> Approfondimento funzioni:
>
> * [script.fn_change_user_emittenti_scope](/dbzero/script/funzioni/fn_change_user_emittenti_scope) — il verbo che la chiama, col permesso
> * [anagrafiche.fn_provisiona_dati_di_sviluppo](/dbzero/anagrafiche/funzioni/fn_provisiona_dati_di_sviluppo) — l'altro chiamante
> * [config.trgfn_user_emittenti_fiscali_guard_delete](/dbzero/config/funzioni/trgfn_user_emittenti_fiscali_guard_delete) — il guard del `DELETE`
> * [script.fn_check_ultimo_super_admin_attivo](/dbzero/script/funzioni/fn_check_ultimo_super_admin_attivo) — l'ultimo SUPER_ADMIN
>
> Guide:
>
> * [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — §7.4, le primitive che l'app non esegue

---

### 🎯 Scopo Principale

Sposta un operatore da un'azienda all'altra, o toglie l'azienda a un SUPER_ADMIN. Ha le regole dello spostamento e
la porta del `DELETE`, ma **non chiede permessi**: è la primitiva sotto il verbo
[fn_change_user_emittenti_scope](/dbzero/script/funzioni/fn_change_user_emittenti_scope), che chiede il
SUPER_ADMIN.

Firma, risultato e rifiuti sono quelli del verbo, tranne `E_PERMESSO_NEGATO`.

⛔ **Un operatore non è mai «globale».** L'array vuoto (o `NULL`) per un utente che non è SUPER_ADMIN si rifiuta
con `E_OPERATORE_SCOPE_GLOBALE_SOLO_SUPER_ADMIN`, anche quando l'operatore non ha già la riga: il controllo viene
prima del no-op. La domanda è [script.fn_is_super_admin_account](/dbzero/script/funzioni/fn_is_super_admin_account)
sull'utente spostato, non `fn_is_super_admin`, che guarda la veste della sessione di chi chiama.

---

### ⛔ Chi la esegue

Solo il proprietario. L'applicazione non ha `EXECUTE`, e nemmeno `PUBLIC`: se l'avesse, il permesso
del verbo si aggirerebbe chiamando lei. La postura sta nelle tre sedi del loop dei grant (linee guida
SQL §11.8, `v_fn_riservate`).

La chiamano due funzioni `SECURITY DEFINER` del proprietario:

* il verbo `script.fn_change_user_emittenti_scope`, dopo il permesso;
* `anagrafiche.fn_provisiona_dati_di_sviluppo`, che dà l'azienda agli utenti di sviluppo. Gira solo in
  un'installazione SVILUPPO e senza un utente in sessione, quindi il verbo la fermerebbe.

---

### 🚪 La porta del `DELETE`

All'ingresso la GUC `zeroerp.allow_user_emittente_delete_override` si spegne: quella che il chiamante
avesse acceso non apre niente. Prima del `DELETE` la funzione la scrive con l'`auth_user_id`
dell'operatore, e la svuota subito dopo, anche in errore. Il guard
[trgfn_user_emittenti_fiscali_guard_delete](/dbzero/config/funzioni/trgfn_user_emittenti_fiscali_guard_delete)
la apre solo con quel valore e col proprietario.

È `SECURITY INVOKER`: gira con l'identità di chi la chiama, che è sempre il proprietario.

Test: `db/pgtap/config/test-porta-scope-emittenti-v1.sql`.
