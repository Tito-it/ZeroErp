## 📘 Documentazione Concettuale – Funzione `script.fn_applica_crea_utente_tecnico`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_crea_utente_tecnico](/dbzero/script/funzioni/fn_crea_utente_tecnico) — il verbo che la chiama, col permesso
> * [dbops.fn_pgtap_fixture_crea_utente_tecnico](/dbzero/dbops/funzioni/fn_pgtap_fixture_crea_utente_tecnico) — la fixture dei pgTAP
> * [config.fn_applica_lega_profilo_identita](/dbzero/config/funzioni/fn_applica_lega_profilo_identita) — il legame del profilo chiesto
>
> Guide:
>
> * [I lavori automatici](/guide/processi-automatici-classe-e-identita) — il tesserino di un processo
> * [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — §7.4, le primitive che l'app non esegue

---

### 🎯 Scopo Principale

Crea l'utente tecnico di un processo automatico per un emittente: l'utente Django con la password
inutilizzabile, il soggetto col suo contatto, il ruolo `PROC_AUTO`, l'identità `OPERATORE` tecnica, la riga di
perimetro in `config.user_emittenti_fiscali` e il legame del processo. Ha tutte le regole della creazione,
raccontate nella pagina del verbo [fn_crea_utente_tecnico](/dbzero/script/funzioni/fn_crea_utente_tecnico), ma
**non chiede permessi**.

Firma, risultato e rifiuti sono quelli del verbo, tranne `E_PERMESSO_NEGATO`. I testi d'errore e le chiavi della
configurazione proposta (il tipo di contatto, lo stato del soggetto) portano il nome del verbo: sono le righe
della cascata degli override, e cambiarle sposterebbe la configurazione.

---

### ⛔ Chi la esegue

Solo il proprietario. L'applicazione non ha `EXECUTE`, e nemmeno `PUBLIC`: se l'avesse, il permesso
del verbo si aggirerebbe chiamando lei. La postura sta nelle tre sedi del loop dei grant (linee guida
SQL §11.8, `v_fn_riservate`).

È `SECURITY INVOKER`: gira dentro una funzione `SECURITY DEFINER` del proprietario.

La chiamano il verbo, dopo il permesso, e la fixture dei pgTAP, solo dove sono ammessi i dati di sviluppo.

Test: `db/pgtap/script/test-fn-crea-utente-tecnico.sql`.
