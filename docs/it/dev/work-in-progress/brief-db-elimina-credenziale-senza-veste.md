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
> **Stato:** ⏳ da fare lato DB.

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
