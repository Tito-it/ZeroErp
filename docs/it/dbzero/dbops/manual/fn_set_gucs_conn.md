## 📘 Documentazione Concettuale – Funzione `dbops.fn_set_gucs_conn`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.fn_get_parameter_di_sessione](/dbzero/script/funzioni/fn_get_parameter_di_sessione) — l'unico lettore di uno dei tre GUC, `app.session_key`
> * [script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic) — il trigger di audit, che legge invece i GUC scritti dall'autenticazione
>
> Guide:
>
> * [Contratto GUC `app.*`](/guide/contratto-guc-app) — i GUC di contesto che il sistema legge davvero
> * [Audit e tracciabilità](/guide/audit-e-tracciabilita) — i GUC che il backend imposta a ogni richiesta

---

### 🎯 Scopo Principale

Imposta tre GUC custom **per la sessione** corrente: `app.user_id`, `app.session_key` e
`app.group_ids` (gli id dei gruppi, separati da virgola).

⛔ Oggi **nessuno la chiama**: né il backend né una funzione del database. Il contesto della
richiesta il backend lo imposta da sé, all'autenticazione, con altri nomi.

---

### I GUC che scrive non sono quelli che il sistema legge

Il contesto applicativo che le policy RLS, il trigger di audit e gli override dei parametri leggono
oggi è scritto dall'autenticazione del backend a ogni richiesta, con i nomi `app.current_user_id`,
`app.current_emittente_id`, `app.jwt_user` e gli altri `app.current_*`. I gruppi dell'utente li
legge il database dalle tabelle di Django, non da un GUC.

Dei tre GUC di questa funzione, `app.user_id` e `app.group_ids` non li legge nessuno.
`app.session_key` lo legge `script.fn_get_parameter_di_sessione`, per il livello di override legato
alla sessione: ma senza chiamate a questa funzione nessuno lo imposta, e quel livello resta spento.

⚠️ Gli effetti valgono per la **sessione**, non per la transazione: su una connessione riusata da
un pool restano fino al cambio successivo.

---

### Note di migrazione

* 2025-09-27 — nasce come porta unica dei GUC di connessione.

---

{% include-markdown "signature-core.md" %}
