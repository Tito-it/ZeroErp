## 📘 Documentazione Concettuale – Tabella `config.user_emittenti_fiscali`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — le aziende per cui l'installazione emette
>
> Funzioni e trigger:
>
> * [script.fn_change_user_emittenti_scope](/dbzero/script/funzioni/fn_change_user_emittenti_scope) — il verbo del SUPER_ADMIN che assegna o sposta l'operatore
> * [script.fn_applica_user_emittenti_scope](/dbzero/script/funzioni/fn_applica_user_emittenti_scope) — la primitiva che sposta la riga, senza permesso
> * [script.fn_get_user_emittenti_scope](/dbzero/script/funzioni/fn_get_user_emittenti_scope) — lo stato dell'assegnazione per il drawer dell'operatore
> * [config.trgfn_user_emittenti_fiscali_guard_delete](/dbzero/config/funzioni/trgfn_user_emittenti_fiscali_guard_delete) — la riga di un utente acceso si toglie solo dal verbo
> * [script.fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user) — l'emittente di lavoro di un utente
> * [script.fn_get_emittenti_scope_pk_ids](/dbzero/script/funzioni/fn_get_emittenti_scope_pk_ids) — il perimetro degli emittenti che un utente vede
> * [script.fn_check_user_can_create_ba](/dbzero/script/funzioni/fn_check_user_can_create_ba) — se l'utente può creare un billing account
>
> Guide:
>
> * [Gli emittenti fiscali](/guide/emittenti-fiscali) — gli emittenti, l'assegnazione degli operatori, l'emittente di lavoro
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — l'assegnazione dal drawer dell'operatore
> * [Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — il perimetro degli emittenti fra i permessi

---

### 🎯 Scopo Principale

`config.user_emittenti_fiscali` dice **per quale emittente fiscale lavora un operatore**. La riga è il suo perimetro:
l'operatore vede e scrive solo i dati di quell'azienda.

* **Una riga per operatore** (`uq_user_emittenti_fiscali_auth_user`, `UNIQUE (auth_user_id)`): un operatore lavora per
  un emittente solo; un emittente ha quanti operatori servono.
* **Fail-closed** (dal 2026-08-18): un operatore **senza** riga non vede nessun emittente. La riga mancante è un errore
  di configurazione, non un permesso.
* **Il SUPER_ADMIN non ha bisogno della riga**: vede tutte le aziende passando da `script.fn_is_super_admin`, e sceglie
  l'emittente di lavoro con la GUC `app.current_emittente_id`, che restringe e non allarga mai. Un SUPER_ADMIN **con**
  la riga è l'amministratore di quell'emittente soltanto.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `auth_user_id` | La credenziale Django dell'operatore (riferimento logico a `django.auth_user`). Unica. |
| `emittente_fiscale_id` | L'emittente per cui lavora (FK → `anagrafiche.emittenti_fiscali.id`). Non si riscrive. |

L'emittente deve essere attivo quando la riga nasce (`dbops.trgfn_child_requires_active_parent`, differito).

---

### Che cosa vuol dire avere la riga, o non averla

| Utente | Riga | Che cosa vede |
| --- | --- | --- |
| Operatore | **1** | L'emittente della riga, e solo quello. |
| Operatore | **0** | **Niente**. È il caso che `dbops.vw_operatori_senza_emittente` conta, e che deve restare a zero righe. |
| SUPER_ADMIN | **0** | Tutti gli emittenti; lavora su quello che sceglie dalla barra in alto, oppure in «Tutti gli emittenti», in sola lettura. |
| SUPER_ADMIN | **1** | L'emittente della riga, e solo quello: è l'amministratore di quell'azienda. |

---

### Chi scrive la riga

* **Il verbo** [`script.fn_change_user_emittenti_scope`](/dbzero/script/funzioni/fn_change_user_emittenti_scope),
  riservato al SUPER_ADMIN (`E_PERMESSO_NEGATO`). È la strada dell'endpoint di amministrazione (drawer dell'operatore).
  Cambiare emittente è uno **spostamento**: toglie la riga di prima e scrive la nuova, nella stessa transazione. Più di
  un emittente è rifiutato (`E_OPERATORE_SCOPE_MULTI_NON_AMMESSO`), l'azienda si toglie solo a un SUPER_ADMIN
  (`E_OPERATORE_SCOPE_GLOBALE_SOLO_SUPER_ADMIN`: un operatore non è mai «globale»), e l'ultimo SUPER_ADMIN attivo non si sposta
  (`E_PROFILO_ULTIMO_SUPER_ADMIN`). Le regole stanno nella primitiva
  [`script.fn_applica_user_emittenti_scope`](/dbzero/script/funzioni/fn_applica_user_emittenti_scope), che
  l'applicazione non esegue.
* **La fabbrica degli utenti tecnici** (`script.fn_crea_utente_tecnico`) scrive la riga del processo automatico
  insieme all'utente.

---

### Le regole di immutabilità

* **L'emittente di una riga non si riscrive**: il lock di colonna (`script.trgfn_lock_columns`, registro
  `dbops.automation_lock_columns`) rifiuta l'`UPDATE` di `emittente_fiscale_id` con `E_EMITTENTE_NON_MODIFICABILE`.
  Lo spostamento passa sempre da `DELETE` e `INSERT`, mai da `UPDATE`.
* **La riga di un utente acceso non si cancella** fuori dal verbo
  ([`config.trgfn_user_emittenti_fiscali_guard_delete`](/dbzero/config/funzioni/trgfn_user_emittenti_fiscali_guard_delete),
  `E_USER_EMITTENTE_DELETE_VIETATO`). Il verbo passa dalla porta `zeroerp.allow_user_emittente_delete_override`, che si
  apre solo per la riga dell'operatore che sposta e solo dal proprietario della tabella: l'applicazione non la apre,
  nemmeno accendendo la GUC. Senza porta passano l'utente spento (la cessazione) e quello che non esiste più.
* La tabella è storicizzata: ogni spostamento lascia la riga di prima nello storico.

---

### Chi la legge

| Funzione | Che cosa risponde |
| --- | --- |
| [`script.fn_get_emittenti_scope_pk_ids(auth_user_id)`](/dbzero/script/funzioni/fn_get_emittenti_scope_pk_ids) | Il perimetro: gli emittenti che l'utente vede. È la catena delle policy di scope. |
| [`script.fn_resolve_emittente_for_user(auth_user_id)`](/dbzero/script/funzioni/fn_resolve_emittente_for_user) | L'emittente di lavoro: quello scelto (GUC), se l'utente lo vede, altrimenti la riga. NULL per il SUPER_ADMIN in «Tutti gli emittenti». |
| [`script.fn_check_user_can_create_ba(auth_user_id)`](/dbzero/script/funzioni/fn_check_user_can_create_ba) | Se l'utente può creare un billing account: il controllo del guard `BEFORE INSERT` su `billing_account`. |
| [`script.fn_get_user_emittenti_scope(auth_user_id)`](/dbzero/script/funzioni/fn_get_user_emittenti_scope) | Lo stato dell'assegnazione per il drawer dell'operatore, e se si può cambiare. |

Il backend applica lo stesso perimetro alle sue letture, con la condizione di scope dei repository
(`add_emittente_scope_condition`); il database lo rifà con le policy e i guard di scope, come difesa in profondità.

---

> **«`config.user_emittenti_fiscali` è l'azienda di chi lavora: una riga, un emittente, spostata solo dal verbo.»**
