## 📘 Documentazione Concettuale – Funzione `config.trgfn_user_emittenti_fiscali_guard_delete`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali) — la tabella che protegge
>
> Approfondimento funzioni:
>
> * [script.fn_change_user_emittenti_scope](/dbzero/script/funzioni/fn_change_user_emittenti_scope) — il verbo che apre la porta
> * [script.fn_applica_user_emittenti_scope](/dbzero/script/funzioni/fn_applica_user_emittenti_scope) — la primitiva che scrive la GUC
> * [script.fn_is_proprietario_tabella](/dbzero/script/funzioni/fn_is_proprietario_tabella) — chi scrive è il proprietario?
>
> Guide:
>
> * [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — §4.9 l'ambito dell'operatore, §7.4 le porte

---

### 🎯 Scopo Principale

Guard `BEFORE DELETE` (fase `a10`) di `config.user_emittenti_fiscali`. La riga è l'azienda di un
operatore: senza, l'operatore non vede niente. Il guard decide quando la si può togliere.

---

### Le regole

| Caso | Esito |
| --- | --- |
| la porta è aperta per questa riga, e chi scrive è il proprietario | passa |
| l'utente Django è spento | passa: è la cessazione |
| l'utente Django non esiste più | passa: è la cascata da `django.auth_user` |
| l'utente Django è acceso, fuori dalla porta | `E_USER_EMITTENTE_DELETE_VIETATO` |

---

### 🚪 La porta

La GUC `zeroerp.allow_user_emittente_delete_override` apre solo se vale l'`auth_user_id` della riga
**e** chi scrive è il proprietario della tabella (`script.fn_is_proprietario_tabella`). Le due cose
insieme si hanno solo dentro il verbo
[fn_change_user_emittenti_scope](/dbzero/script/funzioni/fn_change_user_emittenti_scope), che è
`SECURITY DEFINER` e scrive la GUC con la sua primitiva. L'applicazione non apre la porta, né con
`'on'` né col valore giusto: la GUC la può accendere da sé, e da sola non basta.

Una correzione a mano dei dati passa anch'essa dal verbo.

Il guard è `SECURITY INVOKER`: è ciò che gli fa vedere chi scrive.

Test: `db/pgtap/config/test-porta-scope-emittenti-v1.sql`, `db/pgtap/config/test-user-emittenti-fiscali-immutable.sql`.
