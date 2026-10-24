## 📘 Documentazione Concettuale – Funzione `script.fn_veste_utilizzabile()`

> 👀 **Vedi anche**
>
> [script.fn_has_identita_attiva](/dbzero/script/funzioni/fn_has_identita_attiva) ·
> [script.fn_get_user_profile](/dbzero/script/funzioni/fn_get_user_profile) ·
> [anagrafiche.fn_sync_auth_user_is_active](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_is_active) ·
> [script.fn_veste_di_riferimento](/dbzero/script/funzioni/fn_veste_di_riferimento)

### 🎯 Scopo

(07-10-2026 — brief `brief-db-veste-utilizzabile`, L-6 del piano accessi)

**Una veste vale oggi?** È la sola sede della regola. Ogni punto che deve decidere se una
veste lascia entrare, vede dei dati o tiene accesa la credenziale chiede a questa
funzione, e non riscrive le condizioni.

Una veste è **utilizzabile oggi** se:

| Condizione | Dove si legge |
| --- | --- |
| è accesa | `identita_digitali.attivo` |
| oggi sta nella sua finestra, estremi compresi | `identita_digitali.valido_dal` / `valido_al` |
| il suo soggetto è attivo | `soggetti.attivo`, attraverso il `soggetto_ruolo` della veste |
| **solo per l'operatore umano**: il rapporto è attivo e oggi sta nella sua finestra | la risorsa umana dello stesso `soggetto_ruolo` (`risorse_umane.attivo`, `valido_dal`, `valido_al`) |

Risponde `false` per un id che non esiste e per `NULL`.

### Le scelte, e perché

- **Spenta e fuori date sono la stessa cosa.** Il modello dà a ogni veste un interruttore
  e una finestra, quindi una veste può essere accesa ma scaduta, o non ancora valida. Per
  chi prova a entrare non cambia niente: in tutti i casi chiede all'amministratore, che
  le date le vede nel dettaglio. Per questo la funzione risponde sì o no, senza un
  motivo, e chi rifiuta usa un codice solo (decisione D-4 di Tid).
- **Per l'operatore conta anche il rapporto di lavoro** (D-2, strada (a)). Il drawer
  dell'operatore scrive la fine del **rapporto**, non quella della veste: con questa
  regola quella data chiude davvero l'accesso, senza tenere due copie della stessa data
  in due tabelle. L'accesso finisce al più tardi quando finisce il rapporto.
- **L'identità tecnica di un processo non ha un rapporto.** È `OPERATORE` perché la RLS lo
  pretende, ma per costruzione non ha una risorsa umana (`script.fn_crea_utente_tecnico`
  non la crea). Si riconosce da `identita_digitali.tecnica` e per lei il rapporto non si
  chiede: pretenderlo spegnerebbe i processi.
- **Un operatore umano senza rapporto non è utilizzabile.** Il modello lo ammette (non c'è
  una chiave esterna fra veste e risorsa umana), la madre `fn_crea_operatore_v2` non lo
  produce. Davanti a uno stato che non dovrebbe esistere, la risposta è «no».
- **Il soggetto attivo** era la condizione in più del vecchio sync della credenziale (D-3):
  entra nella regola perché nessuna sede perda una condizione che applicava. ⚠️ Oggi non si
  può costruire una veste accesa con il soggetto spento: un soggetto che ha un
  `soggetto_ruolo` non si disattiva (guard generico «figli prima»). La condizione resta
  come difesa, e il pgTAP lo dichiara invece di provarla.
- **«Oggi» è `CURRENT_DATE` del database**, come in tutte le sedi che leggevano le date.
  Il backend non calcola date.
- **L'appartenenza della veste alla credenziale resta a chi chiama.** La funzione
  risponde sulla veste, non sulla sessione.

### Chi la legge

Nel database, le sedi che prima ricopiavano la regola, ognuna a modo suo:
`fn_has_identita_attiva`, `fn_is_super_admin_account`, `fn_check_ultimo_super_admin_attivo`,
`fn_check_almeno_un_super_admin_attivo`, `fn_get_profili_accesso_applicabili`,
`fn_get_setup_status`, `fn_get_user_profile`, le funzioni di scope sulle vesti
(`fn_scope_fornitore_ownership`, `fn_scope_identita_processo` e, per le vesti di
cliente, `fn_get_identita_sr_perimetro`, da cui passano dal 21-10-2026 le policy di
cliente e shop e `fn_scope_ba_ownership`),
`anagrafiche.fn_sync_auth_user_is_active` e il batch notturno
`anagrafiche.fn_sync_auth_user_expired`.

Prima del 2026-10-07 queste sedi davano risposte diverse: chi guardava le date e chi
no, chi il soggetto e chi no, e solo `/me/` guardava il rapporto. Un utente scaduto
entrava e poi si vedeva negare tutto in modi diversi a seconda della pagina, e un
cliente scaduto vedeva ancora i suoi dati.

Nel backend la leggono il login, ogni richiesta, il refresh, il secondo passo del secondo
fattore e il cambio password (lato BE del brief).

⚠️ **Il tempo non scrive niente.** Una data che passa non fa scattare trigger. Per questo:

* la credenziale (`auth_user.is_active`) si riallinea alla data col **batch notturno**
  [fn_sync_auth_user_expired](/dbzero/anagrafiche/funzioni/fn_sync_auth_user_expired),
  che dal 07-10-2026 spegne gli scaduti **e accende** chi diventa valido quel giorno;
* l'anti-lockout chiede che resti sempre almeno un amministratore **senza scadenza**
  ([fn_identita_super_admin_senza_scadenza](/dbzero/script/funzioni/fn_identita_super_admin_senza_scadenza)):
  la data di fine si ferma quando viene scritta, perché il calendario non si può fermare.

### Forma

`LANGUAGE sql`, `BEGIN ATOMIC`, `STABLE`, `SECURITY INVOKER`. Legge solo tabelle senza
RLS. Non è inlineabile (un `EXISTS` è una sotto-interrogazione): il backend la chiama una
volta per richiesta, le funzioni di scope una volta per riga, come già facevano con le
loro copie.

### Test

`db/pgtap/script/test-fn-veste-utilizzabile-v1.sql`: 28 casi costruiti. Coprono la
regola, le sedi che rispondono come il building block, il ritiro dei due codici delle
date e il presidio «le quattordici sedi la leggono».
