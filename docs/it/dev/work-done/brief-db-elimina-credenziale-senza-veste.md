# Brief DB — Una credenziale senza veste si elimina dall'applicazione

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-06. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§6), che **attende** la consegna DB.
> **Origine:** collaudo a video di Tid del 2026-10-06, subito dopo la chiusura di
> [brief-db-presidi-cosa-significa-cosa-fare.md](../work-done/brief-db-presidi-cosa-significa-cosa-fare.md).
> Il presidio `dbops.vw_credenziali_da_sanare` dice ora, in chiaro, «dai una veste alla
> credenziale oppure cancellala» con il badge «Puoi sistemarlo tu». Tid ha aperto
> Accessi → Altri accessi e **nessuna delle due azioni esiste**.
> **Decisione di Tid (2026-10-06):** strada **B**, cioè costruire il gesto che manca
> invece di limitarsi a correggere il testo. **D-1…D-3 (§3) confermate da Tid il
> 2026-10-06**, così come proposte.
> **Stato:** ✅ DB **applicato** su dbdev il 2026-10-07 (`20261006-10 → -15` più tre CSV), pgTAP
> verdi alla corsa di Tid (§7.8). ✅ BE/FE fatti il 2026-10-07 (§8). ✅ Collaudo a video di Tid superato il 2026-10-07 (§8.4).
> **✅ CHIUSO e archiviato il 2026-10-07.** Resta aperto, fuori da questo brief, il ponte django
> che non nasce su un'installazione nuova (D-4: lì nessuna credenziale si elimina), voce ❓ di
> PROJECT_CONTEXT § «Aperto — Media priorità».

## 1. Il difetto, sul modello

Il presidio `vw_credenziali_da_sanare` accende `NESSUNA_VESTE` per ogni credenziale
che non ha **nessuna** veste, nemmeno spenta (`vw_accessi_altri.nessun_accesso`). Il
suo `COMMENT` dà il rimedio: *«dando una veste alla credenziale, o cancellandola
(spegnerla in Django non basta)»*.

Nell'applicazione oggi non esiste nessuno dei due gesti:

* **Cancellare**: nessun verbo DB, nessun endpoint, nessun pulsante. La credenziale
  può uscire dal presidio solo con un `DELETE` a mano sul database.
* **Dare una veste** a una credenziale che c'è già: non è un gesto, perché una
  veste nasce dall'**invito** sulla scheda del soggetto. Il riuso di una credenziale
  esistente c'è già nell'invito operatore (`anagrafiche.fn_crea_operatore_v2`, riuso
  per email con conferma, 2026-09-25) e lo si ottiene da lì. Non va inventato un
  secondo modo.

Quindi il presidio è a catalogo con `chi_agisce = AMMINISTRATORE` e un'azione che
l'amministratore non può compiere. È un presidio che non si spegne: la stessa
classe di difetto contro cui è nato il brief dei testi.

⚠️ Fatto datato, non motivo: il 2026-10-06 le tre righe accese su dbdev erano
`_pgtap_sync_<md5>` (id 2, 3, 10), residui di una versione dei pgTAP di sync di
marzo-aprile 2026 che non annullava le sue scritture. Il verbo serve **a
prescindere** da loro: il modello ammette una credenziale senza veste
(`fn_crea_auth_user` la crea prima della veste, e Django ne crea una con
`createsuperuser`), e il presidio esiste perché il caso c'è.

## 2. Cosa tiene una credenziale, oggi (struttura, letta il 2026-10-06)

Le FK verso `django.auth_user`, per regola di cancellazione. È il **contratto**: la
riga sotto decide cosa fa il verbo, non quante righe ci sono oggi.

| Alla cancellazione | Tabelle | Lettura |
| --- | --- | --- |
| `CASCADE` | `config.credenziali` (`auth_user_id`), `config.auth_totp_device`, `config.token_monouso`, `config.user_emittente_attivo`, `config.user_emittenti_fiscali`, `config.user_override_aree/_azioni/_oggetti`, `ui.lista_preferenza_utente`, `ui.dashboard_preferenza_utente` | **appartengono** alla credenziale: se ne vanno con lei |
| `SET NULL` | `token_blacklist_outstandingtoken` | Django lo prevede |
| `RESTRICT` | `anagrafiche.identita_digitali`, `documenti.documenti_generati`, `config.email_log` (×2), `config.email_outbox` (×2), `vendite.event_log` | **storia** o **veste**: impediscono |
| `NO ACTION` | `config.credenziali.bloccata_da`, `documenti.documenti_generati_eventi`, `config.parameter_overrides`, `django_admin_log`, `auth_user_groups`, `auth_user_user_permissions` | impediscono anche loro, al termine dell'istruzione |

⇒ Un `DELETE` nudo, su una credenziale che ha una storia, muore su una FK con un
`23503` che all'amministratore non dice niente. La regola va scritta **prima**,
come motivo.

## 3. Le decisioni (✅ confermate da Tid, 2026-10-06)

| # | Domanda | Decisione |
| --- | --- | --- |
| D-1 | Quali credenziali si eliminano? | **Solo quelle senza nessuna veste**, nemmeno spenta: è esattamente `NESSUNA_VESTE` del presidio, cioè `vw_accessi_altri.nessun_accesso`, la stessa regola e non una seconda. Una credenziale con sole vesti spente è una persona disattivata (V-3) e **non** si elimina: la sua storia è sua. |
| D-2 | E se ha una storia (le righe `RESTRICT`/`NO ACTION` del §2)? | **Si rifiuta**, con un motivo che nomina **dove** sta la storia. Una credenziale che ha scritto documenti, email o eventi senza aver mai avuto una veste è un'anomalia da far vedere allo sviluppo, non da cancellare. Il presidio resta acceso, ed è giusto: il testo dell'azione (§5) dice cosa fare in quel caso. ⛔ Non si cancella la storia per far passare il `DELETE`. |
| D-3 | Chi può farlo? | **SUPER_ADMIN**, `script.fn_guard_super_admin` nella prima riga, come il blocco (la gestione accessi è `amm_software`, D-B1). |

## 4. Richiesta

### 4.1 La check: `script.fn_check_credenziale_eliminabile(p_auth_user_id integer) → jsonb`

Il gemello di `script.fn_check_credenziale_bloccabile`: l'array **ordinato** dei
motivi per cui la credenziale non si elimina, vuoto se si può. È la regola **unica**
che spegne il pulsante e che il verbo solleva (linee-guida-sql §12.5.2). Il backend
la legge col BB `sql_lateral_primo_motivo`, come fa già con quella del blocco
(`accessi_repository._LATERAL_BLOCCO`).

Motivi proposti, nell'ordine (nomi e chiavi `reason` li sceglie il team DB):

1. `HA_VESTI`: esiste almeno una riga in `anagrafiche.identita_digitali`, anche
   spenta (D-1);
2. `HA_STORIA`: esiste almeno una riga in una delle tabelle `RESTRICT`/`NO ACTION`
   del §2 diverse da `identita_digitali`. Il motivo porta **quali** (per esempio
   `dove: ['config.email_log', 'vendite.event_log']`), così chi legge sa cosa
   riferire (D-2).

⚠️ **L'elenco delle tabelle di storia non si scrive a mano.** Il §2 è una lettura
del 2026-10-06; la prossima tabella con una FK verso `auth_user` deve entrare nella
check senza che nessuno se ne ricordi. Si deriva da `pg_constraint`
(`confrelid = 'django.auth_user'::regclass`, `confdeltype IN ('r','a')`, escluse
`identita_digitali`, che è il motivo 1, e la riga stessa di `config.credenziali`). Se il
team DB preferisce un elenco dichiarato, serve un pgTAP che lo confronti con
`pg_constraint` e diventi rosso alla FK nuova. La forma la sceglie il team DB.

### 4.2 Il verbo: `script.fn_elimina_credenziale(p_auth_user_id integer) → void`

* Prima riga: `script.fn_guard_super_admin(app.current_user_id)` (D-3).
* Parametro non valido → `E_AUTH_CHIAMATA_NON_VALIDA`; credenziale inesistente →
  `E_CREDENZIALE_NON_TROVATA` (gli stessi del blocco).
* Poi `script.fn_raise_primo_motivo_se_presente` sui motivi della check: la regola
  non si riscrive.
* Poi `DELETE FROM django.auth_user WHERE id = p_auth_user_id`. Le tabelle `CASCADE`
  seguono da sole. ⚠️ Il controllo e la cancellazione stanno nella **stessa**
  transazione, ma fra i due può nascere una veste (un invito concorrente). Il
  `RESTRICT` di `identita_digitali` resta la rete: il `23503` che ne esce va
  tradotto nello stesso codice di `HA_VESTI`, non lasciato nudo.
* `SECURITY DEFINER` del proprietario, `search_path` bloccato, come il blocco.
  All'app **niente** `DELETE` diretto su `django.auth_user`.
* Traccia: chi ha eliminato quale credenziale (id e username) deve restare scritto
  da qualche parte, perché la riga sparisce. La sede la sceglie il team DB secondo
  le linee guida (evento di dominio, giornale tecnico, …).

### 4.3 I codici d'errore

Due codici nuovi, uno per motivo (nomi del team DB, per esempio
`E_CREDENZIALE_CON_VESTI`, `E_CREDENZIALE_CON_STORIA`), classe `CONFLITTO_STATO`
come `E_CREDENZIALE_DI_SISTEMA`: chi agisce ha il permesso, il limite sta nello stato
della credenziale. Il messaggio di `HA_STORIA` deve dire *dove*: è l'unica cosa che
l'amministratore può riferire.

### 4.4 Il testo del presidio (CSV `80_data/sql/dbops/presidi_testi.csv`)

**`dbops.vw_credenziali_da_sanare`**, nuova azione proposta (il team DB la verifica,
come nel brief dei testi):

> «Da Amm. Software → Accessi, scheda «Altri accessi», apri la credenziale. Se la
> persona deve entrare, invitala dalla sua scheda con la stessa email: l'invito
> riusa la credenziale. Altrimenti eliminala con «Elimina accesso». Se
> l'eliminazione è rifiutata perché la credenziale ha una storia, o se ha le vesti
> di una persona e di un processo automatico, avvisa lo sviluppo.»

⚠️ Il riuso per email è verificato sull'invito **operatore**
(`fn_crea_operatore_v2`). Per gli inviti portale e shop lo verifichi il team DB: se
non riusano, la frase va ristretta all'operatore.
⚠️ `PERSONA_E_SISTEMA` non ha un gesto nell'applicazione (separare due vesti su due
credenziali), quindi per quel motivo l'azione resta «avvisa lo sviluppo». Non è
chiesto qui.

E, **nello stesso giro e nello stesso CSV**, le due correzioni di nome rimaste dal
brief dei testi (§9.3 di quel brief, oggi in PROJECT_CONTEXT § «Aperto»):

| Vista | Oggi | Diventa |
| --- | --- | --- |
| `vw_fatture_stampa_coda_da_guardare` | «la coda stampe» | «Strumenti → Code di lavoro, scheda «Coda stampa»» |
| `vw_operatori_senza_emittente` | «Dalla lista Operatori» | «Da Amm. Software → Accessi, scheda «Operatori»» |

### 4.5 Test (pgTAP)

I casi si **costruiscono** in transazione annullata, non si cercano in dbdev:

1. credenziale senza vesti né storia → la check torna `[]`, il verbo la elimina, le
   righe `CASCADE` (una `config.credenziali`, una preferenza) se ne vanno con lei;
2. credenziale con una veste **spenta** → `HA_VESTI`, il verbo rifiuta col suo codice;
3. credenziale senza vesti con una riga di storia (per esempio un `config.email_log`)
   → `HA_STORIA`, e il motivo nomina la tabella;
4. chiamante non SUPER_ADMIN → `E_PERMESSO_NEGATO`;
5. (se l'elenco è dichiarato) l'elenco delle tabelle di storia coincide con le FK
   `RESTRICT`/`NO ACTION` verso `django.auth_user` lette da `pg_constraint`;
6. dopo il caso 1, la credenziale non è più in `dbops.vw_credenziali_da_sanare`;
7. `zeroerp_app` può eseguire il verbo e la check, e **non** ha `DELETE` su
   `django.auth_user`.

## 5. Cosa non cambia

* Il presidio e la sua regola: `NESSUNA_VESTE` resta `vw_accessi_altri.nessun_accesso`.
* `chi_agisce` del presidio resta `AMMINISTRATORE`: con il verbo, il caso principale
  torna davvero in mano a chi legge.
* Nessun gesto per «dare una veste» fuori dall'invito.

## 6. Dopo la consegna: BE/FE (dev/backend-tid)

| Dove | Cosa |
| --- | --- |
| `apps/amm_software/db/accessi_repository.py` | capability `can_delete` / `delete_reason` dalla check, col BB `sql_lateral_primo_motivo` come `_LATERAL_BLOCCO`, sulle righe di «Altri accessi»; metodo che chiama il verbo |
| service + view + rotta | `DELETE` sulla credenziale, accanto a blocca/sblocca, solo SUPER_ADMIN; i due codici nuovi nella policy generata **e** nel ripiego |
| `AccessoAltroDrawer.vue` / `AccessiAltriTab.vue` | «Elimina accesso» (conferma, pulsante spento col motivo dalla capability); dopo l'eliminazione il drawer si chiude e la lista si ricarica. Anche nel kebab della riga |
| Test | BE: capability, traduzione dei codici, binding reale del verbo (e2e). FE: pulsante acceso e spento col motivo, conferma, ricarica |
| Collaudo | Tid elimina le tre credenziali `_pgtap_sync_…` dall'applicazione, e il presidio si spegne |

## 7. Consegna DB (2026-10-06, `dev/db-tid`)

> Scritta e provata con l'SQL estratto in transazione annullata su dbdev (da owner), poi
> **applicata da Tid il 2026-10-07** con pgTAP verdi (§7.8).

### 7.1 Due decisioni di Tid prese durante il lavoro (2026-10-06)

| # | Domanda | Decisione |
| --- | --- | --- |
| D-4 | Su un'installazione nuova le FK verso `django.auth_user` **non nascono** (Liquibase gira prima di `manage.py migrate`, i changeSet del ponte finiscono `MARK_RAN`: voce ❓ di PROJECT_CONTEXT). Una check derivata da `pg_constraint` lì troverebbe zero FK e direbbe «eliminabile» a tutti, e il `DELETE` lascerebbe orfani. Che fare? | **Check derivata + fail-closed.** Se manca la FK di `identita_digitali` verso `auth_user`, la check dà `STORIA_NON_VERIFICABILE` e il verbo rifiuta. La causa (il ponte che non nasce) resta la voce aperta, fuori da questo brief. |
| D-5 | Dove sta la traccia di chi ha eliminato quale credenziale? `dbops.audit_log` è chiuso agli schemi diversi da `dbops`/`maintenance` e scade a 30 giorni; `vendite.event_log` vuole un emittente. | **Una tabella registro nuova**, `config.credenziali_eliminate`, append-only: il solo `SELECT` all'app. |

### 7.2 I changeSet

| ChangeSet | Cosa |
| --- | --- |
| `00_schema/config/20261006-10` | `config.credenziali_eliminate` (id, `auth_user_id`, `username`, `email`, `eliminata_at`, `eliminata_da`, audit, `tx_id`). Nessuna FK: la riga descritta non esiste più, e una FK su `eliminata_da` renderebbe il SUPER_ADMIN «storia». `UNIQUE (auth_user_id)`. Nessun `cleanup_at`: la traccia non scade |
| `20_code/script/20261006-11` | ⭐ BB `script.fn_credenziale_ha_vesti(integer) → boolean`: «ha almeno una veste, anche spenta», in un posto solo (`BEGIN ATOMIC`, INVOKER) |
| `20_code/anagrafiche/20261006-12` | `vw_accessi_altri.nessun_accesso` letto dal BB: la regola di D-1 non ha una seconda copia nella check (regola del 2, copia ritirata nello stesso giro). Stesso risultato: `soggetto_ruolo_id` è `NOT NULL` con FK. `security_invoker` ripetuto |
| `20_code/script/20261006-13` | `script.fn_check_credenziale_eliminabile(integer) → jsonb`, **SECURITY DEFINER** (§7.3) |
| `20_code/script/20261006-14` | `script.fn_elimina_credenziale(integer) → void`, SECURITY DEFINER (§7.4) |
| `90_end/20261006-15` | La porta: all'app solo `SELECT` sulla traccia, e **niente `DELETE` su `django.auth_user`** (se la tabella c'è già; in CI ci pensa il provisioning) |
| loop `90_end/ci_apply/20260205-41` | `config.credenziali_eliminate` in `v_tabelle_sola_lettura_app` |
| `scripts/sql/provision_db_roles.sql` | la traccia nel blocco della credenziale; blocco nuovo «UNA CREDENZIALE SI ELIMINA SOLO DAL VERBO» (`REVOKE DELETE ON django.auth_user`) |
| CSV `config/codici_errore.csv`, `config/messaggi_errore.csv` | i tre codici del §7.5 |
| CSV `dbops/presidi_testi.csv` | il testo del §4.4 per `vw_credenziali_da_sanare`, e le due correzioni di nome del brief dei testi (§9.3 di quel brief: chiuse qui) |

### 7.3 La check

Motivi, nell'ordine (il primo è quello che il verbo solleva):

| # | `reason` | Codice | `reason_key` | Quando |
| --- | --- | --- | --- | --- |
| 1 | `CON_VESTI` | `E_CREDENZIALE_CON_VESTI` | `amministrazione.accessi.elimina_reason.con_vesti` | almeno una veste, anche spenta (D-1, il BB) |
| 2 | `STORIA_NON_VERIFICABILE` | `E_CREDENZIALE_STORIA_NON_VERIFICABILE` | `amministrazione.accessi.elimina_reason.storia_non_verificabile` | manca la FK di `identita_digitali` verso `auth_user` (D-4) |
| 3 | `CON_STORIA` | `E_CREDENZIALE_CON_STORIA` | `amministrazione.accessi.elimina_reason.con_storia` | una riga la tiene con una FK `RESTRICT`/`NO ACTION` (D-2) |

* **L'elenco delle tabelle di storia è derivato** da `pg_constraint` (`confdeltype IN ('r','a')`,
  esclusa `identita_digitali`): la prossima FK verso `auth_user` entra da sola. Le righe della
  **stessa** tabella che seguono la credenziale in `CASCADE` non contano (`config.credenziali.
  bloccata_da` sulla riga che la credenziale possiede). `dettaglio.dove` è l'array
  `schema.tabella`; il valore della frase è lo stesso elenco, perché l'amministratore lo possa
  riferire.
* ⚠️ **Con `CON_VESTI` la check esce** senza cercare la storia: una credenziale con vesti non si
  elimina comunque, e la ricerca costa una lettura per FK (alcune colonne non hanno indice). Sulle
  righe di «Altri accessi» quasi tutte hanno vesti. Quindi `motivi` porta **un** motivo, non tutti.
* **SECURITY DEFINER**: la storia sta anche sotto RLS (`email_log`, `email_outbox`, `event_log`,
  `documenti_generati*`). Da INVOKER la risposta dipenderebbe da chi guarda (linee-guida §12.3).
  Restituisce solo nomi di tabelle. Nessun guard di permesso dentro: la check è pura, il permesso
  lo chiede il verbo.
* ⛔ Un «nipote» (una FK `RESTRICT` verso una tabella che segue `auth_user` in `CASCADE`) la check
  non lo vede: oggi non ce n'è, e il pgTAP (test 15) lo pretende.

### 7.4 Il verbo

Guard SUPER_ADMIN in prima riga → id non valido / credenziale inesistente (gli stessi codici
del blocco) → **`SELECT … FOR UPDATE` sulla riga di `auth_user` prima della check** → primo
motivo della check → traccia → `DELETE`.

* ⭐ **Il lock chiude la gara con un invito** meglio della traduzione del `23503` che chiedeva il
  §4.2. L'`INSERT` di una veste verifica la FK con un `FOR KEY SHARE` sulla stessa riga, che col
  `FOR UPDATE` confligge. Quindi o la veste è già scritta, e la check la vede, o aspetta e muore
  sulla FK.
* La rete resta: un `23503` dal `DELETE` si rilegge dalla check e se ne solleva il primo motivo.
  Se la check non lo spiega si rilancia l'errore originale, perché è un difetto della check e non
  un caso da tradurre a caso.
* ⚠️ Le tre FK **differite** di Django (gruppi, permessi, admin log) si verificano al commit,
  fuori dalla funzione. La check le conta, ma una riga scritta da un'altra transazione dopo la
  check arriverebbe come `23503` al commit. L'applicazione non scrive quelle tabelle.

### 7.5 I codici

| Codice | Classe | Frase |
| --- | --- | --- |
| `E_CREDENZIALE_CON_VESTI` | `CONFLITTO_STATO` (409) | «Questa credenziale ha delle vesti: non si elimina.» |
| `E_CREDENZIALE_CON_STORIA` | `CONFLITTO_STATO` (409) | «Questa credenziale ha già lasciato traccia nell'applicazione (%s): non si elimina.» (`%s` = le tabelle) |
| `E_CREDENZIALE_STORIA_NON_VERIFICABILE` | `TECNICO` (500) | «Non è possibile verificare se questa credenziale ha una storia: non si elimina.» |

Il brief ne chiedeva due; il terzo nasce da D-4. È `TECNICO` perché l'amministratore non può
rimediare: serve chi amministra il database.

### 7.6 A BE/FE: cosa cambia rispetto al §6

| Dove | Cosa |
| --- | --- |
| policy dei codici (generata **e** ripiego) | **tre** codici, non due: anche `E_CREDENZIALE_STORIA_NON_VERIFICABILE` (500) |
| capability | `can_delete` / `delete_reason` / `delete_reason_key` dal primo motivo della check (BB `sql_lateral_primo_motivo`). La check è DEFINER: si legge come le altre, nessun contesto speciale |
| locales FE | le tre `reason_key` del §7.3. ⚠️ Finché mancano, `check_i18n_keys.py` (controllo 4) è rosso in CI, dopo l'apply |
| ⛔ **postura nuova** | l'app **non ha più il `DELETE` su `django.auth_user`**: nessun punto del backend lo usava (letto il 2026-10-06). Un test Django che cancellasse un utente con l'ORM ora prende `42501` |
| traccia | `config.credenziali_eliminate` è leggibile dall'app, se un giorno serve a video. Oggi non lo chiede nessuno |
| ⚠️ in CI | il verbo **rifiuta sempre** (`STORIA_NON_VERIFICABILE`: le FK non ci sono). Un e2e BE che elimina davvero è verde solo dove il ponte django esiste, o va scritto sui due rami come il pgTAP |

Verificato per il §4.4: anche gli inviti **portale e shop** riusano la credenziale per email
(`invito_portale_service.py`, righe 55 e 290). La frase del presidio resta generale.

### 7.7 Test e prova

**Nuovo** `db/pgtap/config/test-elimina-credenziale-v1.sql` (18 test). ⭐ Prova **due mondi**:
dove il ponte c'è (dbdev) il verbo elimina; dove non c'è (CI) asserisce il fail-closed. Nessuno
`skip()` muto.

**Toccati:**

* `script/test-rubinetto-primo-motivo-v1` test 5: da 31 a 32 (il verbo nuovo chiama l'helper);
* `dbops/test-app-postura-schema-django-v1` test 6: l'unica eccezione dichiarata è
  `auth_user [DELETE]`;
* `config/test-credenziali-porta-v1` test 10: cancella dal verbo, da SUPER_ADMIN, invece che con
  un `DELETE` dell'app;
* `config/test-fk-auth-user-ponte-django-v1` test 1 (rosso alla corsa di Tid dopo l'apply,
  2026-10-07): l'invariante «ogni `*_user_id` di dominio ha la FK» prendeva
  `config.credenziali_eliminate.auth_user_id`, che è senza FK per progetto. Ora è un'eccezione
  dichiarata nella lente del test. Sfuggito alla prova pre-apply: quel presidio non era nella
  lista dei trasversali lanciati.

**Prova pre-apply** (2026-10-06, SQL estratto in `BEGIN … ROLLBACK` su dbdev, da owner):

* le precondizioni `0` sono verdi su dbdev, quelle `1` dentro la transazione dopo i changeSet
  precedenti;
* `test-elimina-credenziale-v1`: 17/18 col ponte e 17/18 **senza** (FK verso `auth_user` tolte
  nella transazione). Il 18 (`42501` come app) è rosso da owner per costruzione;
* rubinetto, catalogo messaggi (test 7), motivo nominato, postura `django`, riferimenti morti:
  verdi. `plpgsql_check`: nessun errore, un avviso «STABLE ma PERFORM volatile» sul guard di
  parametro, identico alla gemella `fn_check_credenziale_bloccabile`;
* `test-credenziali-porta-v1`: il 10 verde; rossi 3, 4 e 13, dichiarati «rossi da owner»;
* `test-credenziale-di-sistema-v1`: rossi 6 e 7 **anche senza** questa consegna (da owner la
  sessione è quella del migratore, ramo D-1). Non è una regressione.
* Dopo la prova dbdev è intatto: definizione della vista (md5), funzioni, tabella e ACL di
  `auth_user` come prima.

Prima dell'apply restavano fuori dalla prova il caricamento dei tre CSV (simulato con `INSERT`,
non col loader), il `42501` come app (test 18) e `check_i18n_keys`. I primi due li chiude il §7.8;
`check_i18n_keys` resta in carico al FE (§7.6).

### 7.8 Apply e corsa (2026-10-07)

* **Applicato da Tid** su dbdev. Dal `databasechangelog`: `20261006-10 → -15` `EXECUTED`; il mirror
  `20261006-06` (testi dei presidi) e il loop `ci_apply` `20260205-41` `RERAN`, come atteso per i
  CSV e gli elenchi toccati.
* **Letto dopo l'apply sul DB vivo**: i tre codici sono in `config.messaggi_errore` (id
  1198-1200, quindi il loader li ha caricati); l'azione nuova di `vw_credenziali_da_sanare` è in
  `dbops.presidi_testi`; `django.auth_user` per `zeroerp_app` è `arw`, cioè senza `DELETE`.
* **pgTAP verdi** alla corsa di Tid, compreso `test-elimina-credenziale-v1` come app (anche il
  test 18, il `42501`). Un solo rosso intermedio, `test-fk-auth-user-ponte-django-v1` test 1,
  sanato dichiarando l'eccezione nel test (§7.7).
* ⏳ **Resta**: BE/FE secondo §6 e §7.6 (tre codici nella policy, le tre `reason_key` nei
  locales, capability e pulsante «Elimina accesso»), poi il collaudo: Tid elimina dall'applicazione
  le tre credenziali `_pgtap_sync_…`, e il presidio si spegne.

## 8. Consegna BE/FE (2026-10-07, `dev/backend-tid`)

### 8.1 Backend

| Dove | Cosa |
| --- | --- |
| `amm_software/db/accessi_repository.py` | la terna `can_delete` · `delete_reason` · `delete_reason_key` + `delete_dettaglio` (decodificato) col BB `sql_lateral_primo_motivo` su `fn_check_credenziale_eliminabile`, **sulle righe** di «Altri accessi» e sul **dettaglio** della credenziale; `elimina_credenziale` chiama il verbo |
| `amm_software/services/accessi_service.py` | `elimina_credenziale`: 404 `E_CREDENZIALE_NON_TROVATA` prima del verbo, verbo in `transaction.atomic()`, cache dei permessi invalidata al commit. Nessuna sessione da chiudere: senza vesti nessuna porta fa entrare, e il refresh vuole una veste accesa |
| `amm_software/api/accessi_views.py` | `DELETE credenziali/<id>/` sulla view del dettaglio, `Idempotency-Key` obbligatoria (stampo del fondo fattura: il metodo dice il verbo) |
| `core/services/error_policies_generated.py` | **rigenerato** dal catalogo: i tre codici (`CON_VESTI` e `CON_STORIA` 409, `STORIA_NON_VERIFICABILE` 500) |
| `core/services/error_messages_fallback.py` | i tre ripieghi, **senza `%s`** (quello di `CON_STORIA` non nomina le tabelle) |

Famiglia dei nomi: quella della superficie, `can_block`/`block_reason`/`block_reason_key`
(api.md §«Capability di riga»), più il dettaglio perché `CON_STORIA` ha un parametro.

### 8.2 Frontend

| Dove | Cosa |
| --- | --- |
| `amministrazione/composables/useEliminaCredenziale.js` | spento?, frase del motivo, conferma + `DELETE`. Una sede per kebab e drawer, come `useSchedaVeste` (catalogo BB FE) |
| `AccessoAltroDrawer.vue` | «Elimina accesso» sotto la sezione Accesso: spento col motivo (tooltip sull'involucro **e** scritto sotto: dice cosa fare), nascosto in sola lettura; eliminata, il drawer si chiude e la lista si ricarica |
| `AccessiAltriTab.vue` | la stessa voce nel kebab, spenta col motivo reso nel popup |
| `locales/it.json`, `en.json` | le tre `reason_key` del §7.3, etichette e conferma; `nessun_accesso_spiegazione` dice ora i due gesti (invito con la stessa email, o eliminazione) |

⚠️ `delete_dettaglio.dove` è un **array**: `t()` lo renderebbe come JSON, quindi il
composable lo unisce in testo prima di passarlo alla chiave.

### 8.3 Prove

* API (`test_accessi_views`, 16 test, +5): capability di riga che passa com'è,
  `Idempotency-Key`, verbo chiamato, i tre codici col loro status, 404 prima del verbo.
* DB vero (`test_accessi_db`, 13 test, +4), **due mondi** come il pgTAP: capability
  da lista e dettaglio, eliminazione col verbo (traccia con autore e username, uscita
  dalla lista), veste spenta → `CON_VESTI`, storia (un override di parametro) →
  `CON_STORIA` con la tabella nel messaggio. Senza il ponte i rami attesi sono il
  fail-closed. ⚠️ Fatto datato: la corsa del 2026-10-07 su dbdev è girata come
  `zeroerp_app` **col** ponte, quindi il ramo che elimina è provato sul binding vero;
  quello senza ponte lo prova la CI.
* Cancelli: policy dal DB e registro, codici dichiarati, ripiego, schema OpenAPI,
  atomicità, contratto `Idempotency-Key` FE↔BE, `npm run lint`, `npm run guards`,
  `check_i18n_keys.py` (controllo 4 compreso): verdi.
* FE (`AccessoAltroDrawer.spec.js`, 6 test): acceso, spento con `CON_VESTI` e con
  `CON_STORIA` (le tabelle nella frase), sola lettura, conferma → verbo + chiusura +
  ricarica, rifiuto → drawer aperto.

### 8.4 ✅ Collaudo a video (Tid, superato il 2026-10-07)

1. Amm. Software → Accessi → «Altri accessi», filtro «Nessun accesso» = sì: le
   credenziali `_pgtap_sync_…` hanno «Elimina accesso» acceso (kebab e drawer).
2. Una riga con vesti: la voce è spenta, e il popup del kebab dice perché.
3. Eliminare le tre `_pgtap_sync_…`: conferma, toast, la lista si ricarica senza di loro.
4. Il presidio `vw_credenziali_da_sanare` si spegne (pannello dei presidi).
