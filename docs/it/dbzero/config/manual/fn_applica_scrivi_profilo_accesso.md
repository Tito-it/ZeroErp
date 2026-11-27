## 📘 Documentazione Concettuale – Funzione `config.fn_applica_scrivi_profilo_accesso`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.profili_accesso](/dbzero/config/tabelle/profili_accesso) / [config.profili_accesso_aree](/dbzero/config/tabelle/profili_accesso_aree) / [config.profili_accesso_azioni](/dbzero/config/tabelle/profili_accesso_azioni) — le righe che scrive
>
> Approfondimento funzioni:
>
> * [config.fn_scrivi_profilo_accesso](/dbzero/config/funzioni/fn_scrivi_profilo_accesso) — il verbo che la chiama, col permesso
> * [anagrafiche.fn_provisiona_dati_di_sviluppo](/dbzero/anagrafiche/funzioni/fn_provisiona_dati_di_sviluppo) — l'altro chiamante
>
> Guide:
>
> * [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — §4.5 chi scrive profili e legami, §7.4 le primitive che l'app non esegue

---

### 🎯 Scopo Principale

Scrive un profilo di accesso per codice: lo crea, o ne aggiorna descrizione e campi; poi ne sostituisce le aree
e le azioni se il chiamante le indica. Ritorna l'id. Ha le regole del profilo, ma **non chiede permessi**: è la
primitiva sotto il verbo [fn_scrivi_profilo_accesso](/dbzero/config/funzioni/fn_scrivi_profilo_accesso), che
chiede il SUPER_ADMIN.

* `p_aree` è un elenco di `{area_id, livello}`, `p_azioni` di `{azione_id, abilitata}`; `NULL` lascia invariato,
  un elenco sostituisce (`[]` toglie tutto);
* `p_campi` ammette `attivo` e `richiede_secondo_fattore`: assenti valgono il default alla nascita e restano
  invariati dopo; una chiave estranea è `E_CAMPO_NON_AMMESSO`;
* il profilo si cerca col codice normalizzato e si scrive col codice ricevuto, che il trigger normalizza;
* un codice che esiste con un altro tipo, argomenti mancanti o elenchi malformati: `E_SCRIPT_CHIAMATA_NON_VALIDA`.

Non scrive legami.

---

### ⛔ Chi la esegue

Solo il proprietario. L'applicazione non ha `EXECUTE`, e nemmeno `PUBLIC`: se l'avesse, il permesso
del verbo si aggirerebbe chiamando lei. La postura sta nelle tre sedi del loop dei grant (linee guida
SQL §11.8, `v_fn_riservate`).

È `SECURITY INVOKER`: gira dentro una funzione `SECURITY DEFINER` del proprietario.

La chiama, oltre al verbo, il provisioning di sviluppo, che gira senza un utente in sessione.

Test: `db/pgtap/config/test-fn-scrivi-profilo-accesso-v1.sql`, `db/pgtap/script/test-fn-guard-campi-ammessi-v1.sql`.
