## 📘 Documentazione Concettuale – Funzione `config.fn_applica_lega_profilo_identita`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings) — la riga che scrive
>
> Approfondimento funzioni:
>
> * [config.fn_lega_profilo_identita](/dbzero/config/funzioni/fn_lega_profilo_identita) — il verbo che la chiama, col permesso
> * [anagrafiche.fn_crea_risorsa_umana](/dbzero/anagrafiche/funzioni/fn_crea_risorsa_umana) / [script.fn_applica_crea_utente_tecnico](/dbzero/script/funzioni/fn_applica_crea_utente_tecnico) / [anagrafiche.fn_provisiona_dati_di_sviluppo](/dbzero/anagrafiche/funzioni/fn_provisiona_dati_di_sviluppo) — gli altri chiamanti
>
> Guide:
>
> * [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — §4.5 chi scrive profili e legami, §7.4 le primitive che l'app non esegue

---

### 🎯 Scopo Principale

Lega un'identità digitale a un profilo di accesso e ritorna l'id del legame. Ha le regole del legame, ma
**non chiede permessi**: è la primitiva sotto il verbo
[fn_lega_profilo_identita](/dbzero/config/funzioni/fn_lega_profilo_identita), che chiede il SUPER_ADMIN.

* lo stesso profilo già legato ritorna quel legame: la chiamata si può ripetere;
* un altro profilo già legato lo rifiuta il vincolo `uq_profili_accesso_bindings_identita`: non sostituisce in
  silenzio;
* argomenti `NULL`: `E_SCRIPT_CHIAMATA_NON_VALIDA`.

Coerenza del tipo, ultimo SUPER_ADMIN e notifica dei permessi li fanno i trigger della tabella.

---

### ⛔ Chi la esegue

Solo il proprietario. L'applicazione non ha `EXECUTE`, e nemmeno `PUBLIC`: se l'avesse, il permesso
del verbo si aggirerebbe chiamando lei. La postura sta nelle tre sedi del loop dei grant (linee guida
SQL §11.8, `v_fn_riservate`).

È `SECURITY INVOKER`: gira dentro una funzione `SECURITY DEFINER` del proprietario.

La chiamano, senza un SUPER_ADMIN in sessione, le funzioni che creano un'identità: la risorsa umana (il
legame SUPER_ADMIN di un operatore nuovo, anche sul primo impianto), l'utente tecnico (il profilo chiesto),
il provisioning di sviluppo.

Test: `db/pgtap/config/test-fn-scrivi-profilo-accesso-v1.sql`, `db/pgtap/config/test-porta-tabelle-accesso-v1.sql`.
