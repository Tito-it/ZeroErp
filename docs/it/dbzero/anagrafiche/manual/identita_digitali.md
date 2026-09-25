## 📘 Documentazione Concettuale – Tabella `anagrafiche.identita_digitali`

> 👀 **Vedi anche**
>
Architettura di riferimento:
>
[Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici)
> [Risorse umane e accessi](/guide/risorse-umane-e-accessi)
>
Tabelle correlate:
>
[anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane)
> [django.auth_user](/dbzero/django/auth_user)

---
### 🎯 Scopo Principale
(latest revision 20-04-2026 — modello SSO multi-veste)

La tabella **`anagrafiche.identita_digitali`** è il **bridge generico** tra un
`soggetti_ruoli` e l'utente software Django (`django.auth_user`). Generalizza
il ruolo di `risorse_umane_auth_user` (oggi limitato ai soli dipendenti interni)
estendendolo a:

* **Operatori interni** (ruolo applicativo `OPERATORE` – equivalente al bridge storico)
* **Clienti portale B2B** (`CLIENTE_PORTALE`)
* **Fornitori portale** (`FORNITORE_PORTALE`)
* **Clienti shop self-service** (`SHOP_CUSTOMER`)
* **Sistemi terzi integrati** (`API_CLIENT`)
* **Identità disattivate** (`DISABILITATO`)

Ogni record rappresenta **una veste** con cui un soggetto si logga nel sistema.
Post 20-04-2026 (modello SSO multi-veste) un `auth_user` puo' avere **piu'
identita attive contemporaneamente**, una per ogni `ruolo_applicativo`, e
simmetricamente un `soggetto_ruolo` puo' avere **piu' identita attive**, una
per ogni canale self-service (es. un SR-CL puo' avere `CLIENTE_PORTALE` attivo
per il portale B2B + `SHOP_CUSTOMER` attivo per il canale shop B2C).

---

### Collegamenti principali

* `soggetto_ruolo_id` → `anagrafiche.soggetti_ruoli(id)` – ruolo del soggetto che si logga
* `auth_user_id` → `django.auth_user(id)` – utente Django associato (1:N —
  un auth_user puo' avere N identita, una per ruolo_applicativo)

---

### ⭐ Il flag `tecnica` — identità di PERSONE e identità di PROCESSI

*(dal 2026-09-04)* `tecnica` *(boolean NN, default `false`)* distingue le
identità che appartengono a una **persona** da quelle che appartengono a un
**processo automatico**.

⚠️ **Perché un flag e non un ruolo applicativo nuovo.** Un processo che emette
fatture deve attraversare *esattamente* i controlli che attraversa un operatore:
le stesse policy, lo stesso perimetro. Un ruolo dedicato avrebbe voluto dire
riscrivere tutte quelle regole una seconda volta — e due scritture della stessa
regola prima o poi dissentono. ⇒ Il processo **è** un operatore, e il flag dice
soltanto che dietro non c'è nessuno.

⛔ **Il flag non è liberamente assegnabile**, ed è il punto che protegge dal
caso peggiore. Il guard di coerenza
[trgfn_identita_digitali_guard_coerenza](/dbzero/anagrafiche/manual/trgfn_identita_digitali_guard_coerenza)
si biforca:

| `tecnica` | Che cosa pretende                                            |
| --------- | ------------------------------------------------------------ |
| `true`    | un soggetto-ruolo di tipo **`PROC_AUTO`**                    |
| `false`   | un soggetto-ruolo `RIS_UMANA`, **e una persona fisica pura** |

⇒ Marcare «tecnica» l'identità di una persona **non passa**: sarebbe stato il
modo di far sparire un utente vero da tutti i conteggi che riguardano le
persone.

⭐ Il default `false` lascia il pregresso dov'è: tutto ciò che esisteva prima
resta di persone.

⇒ Le identità tecniche le crea
[script.fn_crea_utente_tecnico](/dbzero/script/manual/fn_crea_utente_tecnico),
e il legame col processo vive in
[dbops.processi_identita](/dbzero/dbops/manual/processi_identita).

---

### Regole di dominio

* **Modello SSO multi-veste** (post 20-04-2026): un `auth_user` rappresenta
  una persona autenticabile (email + password unici). Le sue vesti
  applicative vivono su N record di `identita_digitali`, ciascuno con il
  proprio `ruolo_applicativo`.
* **Unicita' (auth_user, ruolo_applicativo)**: indice parziale
  `uq_identita_digitali_auth_user_ruolo_attivo` su
  `(auth_user_id, ruolo_applicativo) WHERE attivo = true`. Un solo
  `CLIENTE_PORTALE` attivo per user, un solo `OPERATORE` attivo per user,
  eccetera. Storicizzate (`attivo = false`) multiple.
* **Unicita' (soggetto_ruolo, ruolo_applicativo)**: indice parziale
  `uq_identita_digitali_sr_ruolo_attivo` su
  `(soggetto_ruolo_id, ruolo_applicativo) WHERE attivo = true`. Abilita
  scenari multi-canale (es. lo stesso SR-CL ha al massimo un
  `CLIENTE_PORTALE` attivo + un `SHOP_CUSTOMER` attivo, ma nessun doppione
  per ruolo).
* **Finestra temporale**: `valido_dal` obbligatorio (default oggi), `valido_al`
  opzionale. CHECK `valido_al >= valido_dal` se entrambi valorizzati.
* **Coerenza ruolo_applicativo ↔ soggetto_ruolo** garantita dal guard
  [trgfn_identita_digitali_guard_coerenza](/dbzero/anagrafiche/funzioni/trgfn_identita_digitali_guard_coerenza):
  * `OPERATORE` → soggetto_ruolo con tipo `RIS_UMANA` + soggetto persona fisica pura
    (CF obbligatorio, P.IVA vietata)
  * `CLIENTE_PORTALE` / `SHOP_CUSTOMER` → tipo `CL` (cliente)
  * `FORNITORE_PORTALE` → tipo `FO` (fornitore)
  * `API_CLIENT` / `DISABILITATO` → nessun vincolo specifico
* **Tentativi sbagliati, blocco e cambio password obbligatorio NON sono della
  veste** (dal 2026-09-25): la password è una sola e vale per tutte le porte,
  quindi quello stato appartiene alla **credenziale** e sta in
  [config.credenziali](/dbzero/config/tabelle/credenziali). Fino a quel giorno
  `tentativi_falliti`, `bloccato_fino_a`, `deve_cambiare_password` e
  `totp_obbligatorio` stavano qui, una copia per veste, e il login contava solo
  la riga `OPERATORE`: chi aveva solo il portale o lo shop non veniva mai frenato.
* **`auth_user.is_active` = OR sulle identita**: l'utente Django resta
  globalmente attivo se esiste almeno un'identita utilizzabile (cfr.
  [fn_sync_auth_user_is_active](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_is_active)).

---

### Campi di gestione autenticazione

| Campo                    | Default        | Scopo                                                                                                                                                       |
| ------------------------ | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `attivo`                 | `true`         | Soft flag. Se `false`, `auth_user.is_active` viene sincronizzato a `false` (gestione tramite `fn_sync_auth_user_is_active`).                                |
| `valido_dal`             | `CURRENT_DATE` | Inizio validità.                                                                                                                                            |
| `valido_al`              | NULL           | Fine validità (NULL = aperto). Scaduto → identità non utilizzabile.                                                                                         |
| `invito_inviato_at`      | NULL           | Timestamp dell'ultimo invito di attivazione inviato (token monouso `INVITO_PORTALE`).                                                                       |
| `storicizza`             | `true`         | Flag opt-out per lo snapshot storico automatico (`trgfn_storico_generic`).                                                                                  |

⚠️ Dal 2026-09-25 (`20260925-25`) `deve_cambiare_password`, `tentativi_falliti`,
`bloccato_fino_a` e `totp_obbligatorio` non sono più qui: i primi tre sono della
credenziale ([config.credenziali](/dbzero/config/tabelle/credenziali)),
`totp_obbligatorio` non l'aveva mai letto nessuno e, quando il secondo fattore si
farà, sarà anch'esso della credenziale.

---

### Super admin via binding profilo

A partire da §4.6.A-B WIP multi-face-auth (decisione 2026-04-19) il
privilegio di **bypass totale dei permessi** (equivalente al vecchio
`risorse_umane_auth_user.ruolo_sistema = 'ADMIN'`) non è più una colonna
speciale ma un **binding** tra l'identità e un profilo con
`tipo = 'SUPER_ADMIN'` (seed id `9100`).

* Il check viene fatto da [script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin).
* Il binding è gestito via [config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings).
* Il binding `SUPER_ADMIN` viene creato ed eliminato esplicitamente dai caller
  (`fn_crea_risorsa_umana`, `amm_software_repository`) su
  `config.profili_accesso_bindings`.

---

### Il bridge storico non esiste piu'

`anagrafiche.risorse_umane_auth_user` — la tabella che teneva il ponte fra una
risorsa umana e un account Django — non esiste in nessuna forma. Era stata
sostituita da una vista read-only con `security_invoker = true` costruita su
`identita_digitali WHERE ruolo_applicativo = 'OPERATORE'`, nata solo per la
retrocompatibilita' del codice non ancora migrato; in seguito e' stata
eliminata anche quella. Il legame risorsa ⇄ utente passa oggi e solo da
`identita_digitali`.

---

### FK condizionale verso Django

La FK `fk_identita_digitali_auth_user` viene creata **solo se lo schema `django`
e la tabella `auth_user` esistono**. In ambienti CI senza Django (test pgTAP
puri) il vincolo non viene installato, permettendo alle migration di applicarsi
comunque.

---

### Note operative

* La presenza del bridge è **opzionale**: non tutti i `soggetti_ruoli` devono
  avere un accesso al software (es. clienti che non usano il portale).
* L'attivazione di una nuova identità triggera la sincronizzazione di
  `auth_user.is_active` tramite automation (trigger `sync_auth_user_active`).
* I trigger framework (audit, tx_id, storico) sono applicati via automation
  sulla tabella; non richiedono intervento manuale.

---

{% include-markdown "signature-core.md" %}
