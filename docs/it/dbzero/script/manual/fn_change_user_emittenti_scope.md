## 📘 Documentazione Concettuale – Funzione `script.fn_change_user_emittenti_scope`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali) — la riga che dà a un operatore la sua azienda
>
> Approfondimento funzioni:
>
> * [script.fn_applica_user_emittenti_scope](/dbzero/script/funzioni/fn_applica_user_emittenti_scope) — la primitiva che sposta la riga
> * [script.fn_guard_super_admin](/dbzero/script/funzioni/fn_guard_super_admin) — il permesso in prima riga
> * [config.trgfn_user_emittenti_fiscali_guard_delete](/dbzero/config/funzioni/trgfn_user_emittenti_fiscali_guard_delete) — il guard del `DELETE`, e la porta del verbo
> * [script.fn_get_user_emittenti_scope](/dbzero/script/funzioni/fn_get_user_emittenti_scope) — lo stato corrente, in lettura
>
> Guide:
>
> * [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — §4.9 l'ambito dell'operatore, §7.4 il permesso nel verbo
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — l'assegnazione dell'emittente dall'interfaccia
> * [Gli emittenti fiscali](/guide/emittenti-fiscali) — Parte 2, il super admin assegna gli operatori

---

### 🎯 Scopo Principale

È il **verbo** con cui il SUPER_ADMIN porta un operatore su un'azienda, o la toglie a un SUPER_ADMIN.
Dietro c'è il riquadro «Scope emittenti fiscali» del drawer Operatore.

Un operatore ha **una** azienda (`UNIQUE (auth_user_id)` su `config.user_emittenti_fiscali`), e senza
non vede niente: scrivere la riga è dare l'accesso a un'azienda, toglierla è toglierlo. Per questo il
verbo chiede il SUPER_ADMIN, lo stesso controllo dell'endpoint di amministrazione.

---

### 🔐 Il permesso

Il verbo è `SECURITY DEFINER` e nella prima riga legge l'utente di sessione
(`script.fn_utente_di_sessione`) e chiede il SUPER_ADMIN con `script.fn_guard_super_admin`. Chi non lo è
riceve `E_PERMESSO_NEGATO`, e la riga non cambia. Lo riceve anche chi chiama senza un utente in
sessione: il guard è fail-closed.

Il lavoro lo fa la primitiva [fn_applica_user_emittenti_scope](/dbzero/script/funzioni/fn_applica_user_emittenti_scope),
che l'applicazione non esegue: chi volesse saltare il permesso chiamando lei riceve `42501`.

---

### Firma e risultato

* `p_auth_user_id`: l'utente Django dell'operatore da spostare.
* `p_emittente_ids`: l'azienda di destinazione. Un elemento porta l'operatore su quell'azienda;
  `NULL` o un array vuoto gliela toglie, ma solo a un SUPER_ADMIN; più di un elemento si rifiuta. Il parametro resta un array
  perché la firma lo è sempre stata: oggi l'azienda è una sola.

Il risultato è un `jsonb` con tre chiavi: `changed` (se qualcosa è cambiato), `scope_mode`
(`SINGLE` con un'azienda, `GLOBAL` senza) ed `emittente_id`.

| Prima | Chiesto | Che cosa succede |
| --- | --- | --- |
| senza azienda | un'azienda | la riga nasce |
| un'azienda | la stessa | niente, `changed = false` |
| un'azienda | un'altra | la riga di prima si toglie, nasce quella nuova |
| un'azienda | nessuna | SUPER_ADMIN: la riga si toglie. Operatore: rifiuto, la riga resta |
| senza azienda | nessuna | SUPER_ADMIN: niente, `changed = false`. Operatore: rifiuto |

---

### ⛔ Rifiuti

| Codice | Quando |
| --- | --- |
| `E_PERMESSO_NEGATO` | chi chiama non è SUPER_ADMIN, o non c'è un utente in sessione |
| `E_OPERATORE_SCOPE_PARAM_NON_VALIDO` | l'utente o l'emittente mancano o non sono positivi |
| `E_OPERATORE_SCOPE_MULTI_NON_AMMESSO` | più di un'azienda |
| `E_OPERATORE_SCOPE_GLOBALE_SOLO_SUPER_ADMIN` | nessuna azienda per un utente che non è SUPER_ADMIN: un operatore non è mai «globale» |
| `E_PROFILO_ULTIMO_SUPER_ADMIN` | lo spostamento toccherebbe l'ultimo SUPER_ADMIN attivo |

Un'azienda spenta o inesistente la ferma il guard della tabella sull'`INSERT`.

---

### 🚪 La porta del `DELETE`

La riga di un utente acceso non si cancella: lo vieta il guard
[trgfn_user_emittenti_fiscali_guard_delete](/dbzero/config/funzioni/trgfn_user_emittenti_fiscali_guard_delete).
Lo spostamento passa da una porta: la primitiva scrive la GUC
`zeroerp.allow_user_emittente_delete_override` con l'`auth_user_id` dell'operatore, e il guard la apre
solo con quel valore **e** se a scrivere è il proprietario della tabella. Dentro il verbo, che è
`SECURITY DEFINER`, lo è; l'applicazione no, nemmeno accendendo la GUC da sé. La GUC si svuota subito
dopo, anche in errore.

---

### Chi la chiama

* Il backend, dall'endpoint dello scope dell'operatore (amministrazione, SUPER_ADMIN).
* Nei pgTAP, il builder [dbops.fn_pgtap_sposta_scope_operatore](/dbzero/dbops/funzioni/fn_pgtap_sposta_scope_operatore),
  che la chiama con un SUPER_ADMIN di fixture.

Il provisioning dei dati di sviluppo non passa da qui: gira senza un utente in sessione, e chiama la
primitiva.

Test: `db/pgtap/script/test-fn-change-user-emittenti-scope.sql` (le regole dello spostamento),
`db/pgtap/config/test-porta-scope-emittenti-v1.sql` (il permesso e la porta).
