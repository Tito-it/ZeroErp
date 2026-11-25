# Brief DB — l'emittente del super admin: il guard sugli override dei parametri e il profilo senza gestore globale

> **⏭️ Chi riparte — aggiornato al 2026-11-25**
>
> **Chiuso e archiviato il 2026-11-25, su decisione di Tid.** Riparte nessuno. Il lavoro DB è
> applicato, coi pgTAP verdi, e committato su `dev/db-tid`; il lavoro BE/FE (§2, §4.7) è committato
> su `dev/backend-tid`. Nessun debito: il passaggio del super admin in «tutti gli emittenti» (§3,
> §3.1) è il comportamento del modello, lo stesso delle altre tabelle col guard di scope, e non un
> residuo.
>
> | # | Chi | Che cosa | Dove | Aspetta |
> | --- | --- | --- | --- | --- |
> | 1 | team BE/FE | ✅ La regola unica nel BE: override, assistente AI, gate L2, valuta, cascata (2026-11-25) | §2 | — |
> | 2 | team DB | ✅ Analisi di R-DB-1 e R-DB-2 (2026-11-25): il guard generico non basta su una tabella senza RLS, Tid decide (A) | §3.1, §4.5 | — |
> | 3 | team DB | ✅ R-DB-1 (A): il guard di scope dedicato di `config.parameter_overrides`, `20261124-13`, col pgTAP, le guide e le pagine `manual/`; provato con l'estratto (2026-11-25) | §3.2 | — |
> | 4 | team DB | ✅ R-DB-2 (a): il blocco `emittente` di `script.fn_get_user_profile` senza il ripiego sul gestore globale, `20261124-14`, col pgTAP e la pagina `manual/`; provato con l'estratto (2026-11-25) | §4.6 | — |
> | 5 | Tid | ✅ Apply e pgTAP di R-DB-1 e R-DB-2 (2026-11-25) | — | — |
> | 5-bis | Tid, team DB | ✅ La doc auto-generata rigenerata e il commit del giro DB (2026-11-25); resta la PR | — | — |
> | 6 | team BE/FE | ✅ La prova di `/me/` con i tre utenti, verde sul DB vero; la riga morta di `emittenteCorrente` tolta; la doc BE allineata a §2 (2026-11-25) | §4.7 | — |
> | 6-bis | team BE/FE | ✅ Il commit del giro BE/FE su `dev/backend-tid` (2026-11-25) | §4.7 | — |
> | 7 | Tid | ✅ Chiusura e archiviazione in `work-done/` (2026-11-25). La suite pgTAP intera non è stata rilanciata alla chiusura: i pgTAP del giro e quelli vicini sono verdi (§3.2, §4.6), la suite gira in CI sulla PR | — | — |
>
> **Decisioni aperte di Tid:** nessuna. Dove nominare `script.fn_resolve_emittente_for_user` l'ha
> deciso il 2026-11-25: in §7 della guida dei permessi, ed è scritto (§6.1). **Committato** su
> `dev/db-tid` il 2026-11-25: il giro DB intero (R-DB-1 e R-DB-2, guide, pagine `manual/`, doc
> auto-generata rigenerata da Tid) e questo brief. Il lavoro BE di §2 è committato su
> `dev/backend-tid` (`9511ed0f6`), e così il giro BE/FE di §4.7 con l'archiviazione (2026-11-25).
>
> **Brief vicini verificati (2026-11-25):** nessuno. In `work-in-progress/` nominano
> `config.parameter_overrides` solo `brief-db-revisione-anagrafiche` (§ giro 3-bis, i GRANT dell'app
> per un pgTAP) e `valutazione-modello-di-dominio-db` (tipi delle date, FK verso `django`), su altro
> tema; `fn_get_user_profile` compare in `piano-be-fe-accessi-credenziale-e-vesti` per i guard della
> veste, non per il blocco `emittente`.
> **Guide verificate (2026-11-25):** gli esiti sono in §6.
>
> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-11-25. **A chi:** team DB e Tid.
> **Origine:** E1-6 di [brief-be-fe-BB-audit](brief-be-fe-BB-audit.md) (§6.2). L'approfondimento
> completo, con i riferimenti, è in §6.1 di quel brief; qui c'è solo ciò che serve al DB.
> Il lavoro BE descritto in §2 è committato su `dev/backend-tid` (`9511ed0f6`, verificato il
> 2026-11-25).

## 0. Il piano da percorrere

**Fase 1 — analisi (team DB)**

- [x] Lettura del corpo vivo, delle guide e delle linee guida; i tre buchi del guard generico su
  una tabella senza RLS (§3.1) — 2026-11-25
- [x] Decisione di Tid: R-DB-1 nella forma (A), R-DB-2 nella forma (a), in parallelo — 2026-11-25

**Fase 2 — R-DB-1 (team DB)**

- [x] Il guard dedicato e il suo trigger, `20261124-13`, provati con `scripts/prova_changeset.py`
  (§3.2) — 2026-11-25
- [x] Il pgTAP `config/test-parameter-overrides-guard-emittente-scope-v1.sql`, coi casi di §3.1;
  gli otto pgTAP vicini rilanciati con l'estratto, invariati (§3.2) — 2026-11-25
- [x] Le guide `configurazione-e-gestione-parametri` e `architettura-permessi-e-autorizzazioni`
  §7.2, le pagine `manual/` della tabella e del guard, le note dei due codici in `codici_errore.csv`
  (§3.2) — 2026-11-25

**Fase 3 — R-DB-2 (team DB)**

- [x] `script.fn_get_user_profile` senza la priorità 2, `20261124-14`, provata con l'estratto
  (§4.6) — 2026-11-25
- [x] I casi nel pgTAP del profilo, col gestore globale costruito; i cinque pgTAP vicini rilanciati
  con l'estratto, invariati (§4.6) — 2026-11-25
- [x] La pagina `manual/` di `fn_get_user_profile` (§4.6) — 2026-11-25
- [x] `script.fn_resolve_emittente_for_user` nominata in §7.1 della guida dei permessi, come ha
  deciso Tid (§6.1) — 2026-11-25

**Fase 4 — apply e ritorno al BE**

- [x] R-DB-1: apply di Tid (`20261124-13`), pgTAP verdi — 2026-11-25
- [x] R-DB-2: apply di Tid (`20261124-14`), pgTAP verdi — 2026-11-25
- [x] La doc auto-generata rigenerata (Tid) e il commit del giro DB su `dev/db-tid` — 2026-11-25
- [x] Il passaggio al team BE/FE: la prova di `/me/` (§4.4) e la nota su `E_SCOPE_EMITTENTE` (§3.1)
  — 2026-11-25
- [x] La prova di `/me/` del team BE/FE (§4.7) — 2026-11-25
- [x] Archiviazione, su decisione di Tid (la suite pgTAP intera gira in CI sulla PR) — 2026-11-25

## 1. La regola, decisa da Tid il 2026-11-25

L'emittente su cui si legge o si scrive un valore operativo (parametro, soglia, valuta, emittente
di una scrittura) è:

1. quello **del documento**, quando c'è un documento;
2. altrimenti quello **di chi agisce**, cioè `script.fn_resolve_emittente_for_user`: l'emittente
   attivo se valido per l'utente, poi la riga di `config.user_emittenti_fiscali`.

In «tutti gli emittenti» la risposta è NULL: la lettura salta il livello emittente, come fa già
`script.fn_get_parameter_di_sessione`, e la scrittura si rifiuta con `E_EMITTENTE_NON_RISOLTO`,
come fa già `script.trgfn_default_emittente_fiscale`.

Il **gestore globale** non è un ripiego operativo per chi agisce. Il gestore globale è la riga di
`anagrafiche.emittenti_fiscali_billing_account` con `billing_account_id IS NULL` e `is_default`.

Le guide lo dicono già: la scelta dell'emittente restringe e non allarga mai, «tutti» è sola
lettura, e nessun default dell'installazione si usa per attribuire qualcosa. Il ripiego sul gestore
globale stava solo in due commenti di codice e in `fn_get_user_profile`.

## 2. Cosa ha già fatto il BE (2026-11-25)

Il DB deve sapere cosa il BE emette **oggi**, sul ramo:

* **Override dei parametri per emittente**: si scrivono e si cancellano sull'emittente di chi
  agisce, con il BB `emittente_per_scrivere`. In «tutti» il BE risponde 400
  `E_EMITTENTE_NON_RISOLTO` e non scrive. Fino al 2026-11-25 si scrivevano **sempre sul gestore
  globale**, anche con un altro emittente scelto. Il DB non poteva accorgersene: R-DB-1 nasce
  da qui.
* **Cascata dei parametri lato BE**: l'emittente è quello di chi agisce (BB `contesto_cascata`),
  quindi coincide con `fn_get_parameter_di_sessione`.
* **Gate L2 dei prezzi**: l'emittente è quello della testata del documento.
* **Assistente AI**: legge e scrive sull'emittente di chi agisce, e applica il cancello della
  lista del suo endpoint gemello.
* **Ritirati**: `ParameterRepository/ParameterService.get_emittente_fiscale_id_for_user`, unica
  copia Python della query del gestore globale, e `ai_assistant/services/user_context.
  get_emittente_fiscale_id`, che leggeva il blocco `emittente` del profilo. Dal BE nessuno legge
  più il gestore globale come emittente di chi agisce.

## 3. R-DB-1 — Il guard di scope sugli override dei parametri

> ⚠️ **Superata in parte da §3.1 (2026-11-25).** Il guard generico non basta su questa tabella,
> che non ha la RLS. La forma decisa è un guard dedicato, che copre anche il DELETE (la risposta
> alla domanda qui sotto); il pgTAP di riferimento è quello di §3.1. Il resto di questa sezione
> resta la richiesta del BE com'era arrivata.

**Il fatto.** `config.parameter_overrides` ha i guard di forma (`ammette_override`, tipo del
valore), il padre attivo per emittente e categoria, l'audit e lo storico. **Non ha un guard di
scope sull'emittente.** Una riga con `emittente_fiscale_id` fuori dal perimetro di chi scrive
entra senza errore.

**La richiesta.** Montare `script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')`
in BEFORE INSERT e BEFORE UPDATE, come sulle dodici tabelle che lo hanno già in modalità
`'fiscale'`. Il nome e l'ordine del trigger li sceglie il team DB secondo le sue linee guida.

**Cosa ci si aspetta dal guard, e cosa no:**

* gli override per utente, gruppo, categoria e funzione hanno `emittente_fiscale_id` NULL: il
  guard li salta («nessun padrone») ed è corretto;
* un super admin con l'emittente X scelto che scrive un override su Y ≠ X si ferma:
  `fn_check_user_emittente_scope` risponde FALSE prima del bypass;
* un operatore che scrive sul proprio emittente passa;
* ⚠️ **in «tutti» il guard lascia passare** un super admin, per il bypass di
  `fn_check_user_emittente_scope`. La sola lettura di «tutti», su questa tabella, la garantisce
  oggi il BE. Vale anche per le altre dodici tabelle. Se il team DB pensa che vada chiusa a DB,
  è una domanda di modello per Tid e un brief a parte, non questo.

**Una domanda al team DB.** Le dodici tabelle non montano il guard sul DELETE. Il BE cancella un
override per emittente con il filtro sull'emittente di chi agisce, quindi oggi non può cancellare
quello di un'altra azienda. Il team DB decide se per questa tabella il DELETE va coperto, secondo
il suo standard.

**Il pgTAP**, come minimo:

1. super admin con X scelto: INSERT e UPDATE di un override su Y → l'errore del guard;
2. lo stesso super admin su X → passa;
3. operatore sul proprio emittente → passa; su un altro → l'errore;
4. override per utente (emittente NULL) → passa.

**Chi cambia per primo.** Il DB, quando vuole: il BE non scrive più fuori dall'emittente scelto
(§2). Il guard solleva `E_SCOPE_EMITTENTE`, che ha già la sua classe nel registro del BE: non
serve una policy nuova.

### 3.1 L'analisi del team DB, e la forma decisa da Tid (2026-11-25)

⚠️ **La richiesta di §3, così com'è scritta, non dà la protezione che §3 si aspetta.** La
correzione è in questa sezione.

**Il fatto strutturale.** `config.parameter_overrides` **non ha la RLS** (`relrowsecurity` falso,
catalogo dello scratch del 2026-11-25), e per §10.1 delle linee guida SQL non la deve avere: è
configurazione letta da tutti. Le 32 tabelle che montano `script.trgfn_guard_emittente_scope`, le
dodici in modo `'fiscale'` comprese, hanno **tutte** la RLS. Il guard generico è scritto per
lavorare **accanto** a una policy, e da solo lascia tre buchi:

1. **L'UPDATE del valore di un override altrui passa.** Il guard salta l'UPDATE quando la colonna
   dell'emittente non cambia. Sulle altre tabelle è giusto: la riga di Y chi lavora su X non la
   vede, e la policy (`USING`) gliela toglie dall'UPDATE. Qui la vede: un super admin con X scelto,
   o un operatore di X, cambia `overridden_value` sull'override di Y senza errore. Il caso 1 del
   pgTAP di §3 («UPDATE su Y → errore») sarebbe verde solo se scritto come spostamento della riga.
2. **Il DELETE è aperto.** La domanda di §3 ha una risposta di modello: una regola su una colonna
   vale per ogni strada che la scrive (linee guida trigger, «Dove si mette un guard»). Oggi la
   cancellazione di un override altrui la impedisce solo il filtro del BE.
3. **La sessione senza identità passa.** Il ramo «nessun utente» del guard si affida a
   `row_security_active()`, che su una tabella senza RLS risponde falso per chiunque: l'app senza
   `app.current_user_id` esce con `RETURN NEW` invece che con `E_SCOPE_SENZA_UTENTE`.

**Le due strade, e la scelta.**

* **(A) — scelta da Tid il 2026-11-25.** Un guard di scope **dedicato** della tabella, che guarda
  la riga **di prima** e quella **di dopo**.
* (B), scartata: la RLS sulla tabella, con la lettura aperta e le policy di scrittura sul
  perimetro. Avrebbe fatto funzionare il guard generico com'è, ma è un'eccezione a §10.1.

**La forma di (A).**

* **Una funzione dedicata**, `config.trgfn_parameter_overrides_guard_emittente_scope`, e non una
  modalità nuova del BB: è la prima tabella col perimetro emittente senza RLS (regola del 2), e il BB
  è montato su 32 tabelle. Il nome e la fase del trigger seguono le linee guida trigger; la fase va
  prima di `z90_storico`, che è anche `BEFORE DELETE`.
* **Che cosa guarda:** in INSERT la riga di dopo; in UPDATE la riga di prima **e** quella di dopo,
  sempre, anche se l'emittente non cambia; in DELETE la riga di prima. Per ogni riga con
  `emittente_fiscale_id` valorizzato, la domanda è `script.fn_check_user_emittente_scope`; una riga
  con emittente NULL (gli override per utente, gruppo, categoria e funzione) non ha padrone e passa.
* **Senza utente in sessione**, su una riga con padrone, si ferma con `E_SCOPE_SENZA_UTENTE`; passa
  solo la sessione che la RLS non filtrerebbe se ci fosse (proprietario, superuser, `BYPASSRLS`), e
  fuori da una SECURITY DEFINER, come nel BB. Il criterio si scrive in costruzione e si dice nel
  giro: `row_security_active()` qui non risponde, e il criterio del BB non si ricopia senza dirlo.
* **Vagliato e non fatto:** il blocco della colonna in `dbops.automation_lock_columns`. Spostare un
  override su un'altra azienda non lascia niente di incoerente (l'override non ha figli, lo storico
  registra la versione), e il guard chiede lo scope su tutte e due le aziende: la colonna non è
  identità.
* **Resta come in §3:** in «tutti» il super admin passa, per il bypass di
  `fn_check_user_emittente_scope`. Il codice è `E_SCOPE_EMITTENTE`.

**Il pgTAP**, che sostituisce l'elenco minimo di §3:

1. super admin con X scelto: INSERT di un override su Y → `E_SCOPE_EMITTENTE`;
2. lo stesso: UPDATE del **solo valore** di un override di Y → `E_SCOPE_EMITTENTE` (il buco 1);
3. lo stesso: UPDATE che sposta un override da X a Y → `E_SCOPE_EMITTENTE`;
4. lo stesso: DELETE di un override di Y → `E_SCOPE_EMITTENTE` (il buco 2);
5. lo stesso su X: INSERT, UPDATE e DELETE passano;
6. operatore sul proprio emittente passa; su un altro → `E_SCOPE_EMITTENTE`;
7. override per utente (emittente NULL) → passa;
8. sessione dell'app senza utente, su un override per emittente → `E_SCOPE_SENZA_UTENTE` (il buco
   3); su un override per utente → passa.

**Per il BE/FE (nessun lavoro, solo da sapere).** Il BE scrive e cancella già solo sull'emittente di
chi agisce (§2), quindi oggi non incontra l'errore. Dopo l'apply `E_SCOPE_EMITTENTE` può arrivare
anche da un UPDATE del valore o da un DELETE, non solo da un INSERT: la classe nel registro del BE è
la stessa.

### 3.2 Il giro di R-DB-1 (team DB, 2026-11-25)

**Il changeSet:** `20_code/config/20261124-13-create-trgfn-parameter-overrides-guard-emittente-scope`.
La funzione e il trigger stanno nello stesso file, come il guard fratello `20261031-57`: il trigger
è `trg_parameter_overrides_a10_guard_emittente_scope_ins_upd_dlt`, di 61 caratteri, `BEFORE INSERT
OR UPDATE OR DELETE`, per riga, senza `OF`.

**Il criterio senza utente**, lasciato aperto in §3.1: passa la sessione superuser, `BYPASSRLS` o
del proprietario della tabella. Il proprietario conta anche per appartenenza al ruolo
(`pg_has_role … USAGE`), che è come PostgreSQL decide chi la RLS non filtra. Vale solo fuori da una
SECURITY DEFINER: ruolo di sessione uguale a `current_user`, con il parametro `role` come nel BB. È
una seconda scrittura del criterio che il BB lascia dire a `row_security_active()`, ed è dichiarata
tale nell'header del changeSet e nel COMMENT. Su questa tabella quella funzione non risponde.
Valutato in sola lettura sullo scratch: `zeroerp_owner` → passa, `zeroerp_app` → si ferma.

**Le prove (scratch `zeroerp_ruoli`, 2026-11-25):**

* l'estratto gira per intero e poi va in ROLLBACK, col catalogo identico prima e dopo;
* il pgTAP nuovo, con l'estratto: 15 ok e 2 not ok, il 15 e il 16. Sono rossi per costruzione:
  `prova_changeset.py` gira da proprietario, che senza utente passa, e il 15 è l'asserzione che lo
  dice. Il caso dell'app senza utente si prova solo dopo l'apply, col runner applicativo;
* gli otto pgTAP che scrivono override con l'emittente, rilanciati senza e con l'estratto, hanno
  lo stesso conteggio prima e dopo: `test-parameters-uom-defaults-cascade-v1`,
  `test-parameters-vendite-limiti-prezzi`, `test-fn-get-parameter-full-categoria-cliente-v1`,
  `test-fn-get-parameter-di-sessione-v1`, `test-fn-list-parameters-for-user`,
  `test-parameters-emittente-defaults-cascade`, `test-fn-get-parameter-full-emittente`,
  `test-parameters-ammette-override-v1`. Da proprietario le scritture con l'utente in sessione
  passano comunque dal guard: il guard giudica chi agisce, non il ruolo.

**La documentazione dello stesso giro:**

* `configurazione-e-gestione-parametri`: il «Vedi anche» e §«I riferimenti degli ambiti»;
* `architettura-permessi-e-autorizzazioni`: il «Vedi anche» e un paragrafo in §7.2;
* le pagine `manual/` della tabella, con la riga che mancava anche per `a07`, e del guard nuovo;
* in `codici_errore.csv`, la seconda sede nelle note di `E_SCOPE_EMITTENTE` ed
  `E_SCOPE_SENZA_UTENTE`. I campi sono ricontati dopo l'ultima modifica: 1275 righe, tutte da 5
  campi;
* ⚠️ la doc auto-generata va rigenerata dopo l'apply: la guida rimanda già alla pagina
  `config/funzioni/trgfn_parameter_overrides_guard_emittente_scope`.

**Apply (Tid, 2026-11-25):** `20261124-13` applicato, pgTAP verdi, compreso il pgTAP nuovo col
runner applicativo. Sono quindi verdi anche il 15 e il 16, che nella prova da proprietario erano
rossi per costruzione: l'app senza utente si ferma con `E_SCOPE_SENZA_UTENTE`.

## 4. R-DB-2 — Il profilo senza il gestore globale come emittente

### 4.1 Il fatto

Il blocco `emittente` di `script.fn_get_user_profile` è una `UNION ALL` ordinata per priorità:

* priorità 1, la riga di `config.user_emittenti_fiscali`;
* priorità 2, il gestore globale, cioè `emittenti_fiscali_billing_account` con BA NULL,
  `is_default` ed emittente attivo.

Chi non ha una riga di permesso riceve quindi il gestore globale **come se fosse il suo
emittente**. Questo vale per il super admin, con o senza un emittente scelto, e per l'operatore
non ancora configurato.

### 4.2 Chi legge il blocco oggi (verificato sul codice, 2026-11-25)

* **BE, `core/api/me_view.py` `_compute_is_admin_globale`**: legge solo
  `user_emittente_fiscale_id`, che nella riga di priorità 2 è già NULL. Con il blocco NULL il
  risultato non cambia: super admin senza riga = admin globale.
* **FE, `frontend/src/stores/auth.js` `emittenteCorrente`**: per l'admin globale restituisce già
  `null` (il commento spiega che lo fa proprio perché il blocco «riflette il gestore globale»).
  Per l'**operatore senza riga** oggi restituisce il gestore globale. Da lì nasce
  `emittenteScritturaId`, e i form propongono come emittente di scrittura un'azienda che non è
  sua; poi la scrittura la rifiuta il guard di scope (fail-closed). Con il blocco NULL,
  `emittenteCorrente` diventa `null` e i verbi di creazione si spengono, che è lo stato giusto.
* **BE, assistente AI**: leggeva il blocco, ma la lettura è ritirata il 2026-11-25 (§2).

Nessun altro lettore nel BE (`get_user_profile` ha un solo chiamante, `me_view`). Nel FE ci sono
solo due commenti (`pratiche/stores/pratiche.js`, `EmittenteFiscaleField.vue`) che dicono di **non**
usare quel blocco.

### 4.3 La richiesta e la raccomandazione

**Raccomandata (a):** il blocco `emittente` porta **solo** la riga di priorità 1. Senza riga di
permesso è NULL. La priorità 2 si toglie.

**Alternativa (b):** se il team DB vede un lettore che vuole il nome del gestore globale come
etichetta, lo si espone con una chiave **separata**, per esempio `gestore_globale`, mai dentro
`emittente`. La decisione di Tid ammette G «al più come etichetta», non come emittente.

Con (a) non serve nessuna chiave nuova: nessun lettore di §4.2 usa il gestore globale come
etichetta. Se il team DB sceglie (b), lo dice nel brief e la scelta passa da Tid.

### 4.4 Chi cambia per primo, e cosa fa il BE/FE dopo

**Il DB.** Il BE e il FE leggono già il blocco in modo compatibile con il NULL (§4.2). Dopo
l'apply il team BE/FE prova `/me/` con tre utenti:

* il super admin senza riga: `is_admin_globale` resta `true`;
* l'operatore configurato: il blocco resta invariato;
* l'operatore senza riga: blocco NULL, nessun emittente proposto nei form, verbi di creazione
  spenti.

È la riga 6 di «Chi riparte».

### 4.5 La forma scelta dal team DB, confermata da Tid (2026-11-25)

**(a)**, come raccomanda §4.3: il blocco `emittente` porta solo la riga di
`config.user_emittenti_fiscali`, senza riga è NULL. Nessuna chiave `gestore_globale`.

* La `UNION ALL` diventa una lettura semplice. Il vincolo `uq_user_emittenti_fiscali_auth_user`
  ammette al più una riga per utente, quindi l'ordinamento per id non sceglie fra più righe.
* Il blocco resta **l'emittente configurato dell'utente** e non segue l'emittente attivo della
  sessione (`app.current_emittente_id`): il profilo descrive l'utente, ed è ciò che leggono i lettori
  di §4.2. L'emittente di chi agisce resta `script.fn_resolve_emittente_for_user`.
* **Garanzia ritirata:** «il blocco `emittente` non è NULL quando esiste un gestore globale». Lato DB
  non la legge nessuno: `script.fn_get_user_profile` non ha chiamanti nel database (catalogo dello
  scratch, 2026-11-25). Il censimento BE/FE è §4.2.
* **pgTAP:** nessun test fissa oggi il ripiego. In
  `db/pgtap/script/test-fn-get-soggetto-dati-and-user-profile.sql` entrano tre casi: operatore con
  la riga → il blocco con il suo emittente; operatore senza riga → NULL; super admin senza riga →
  NULL.

### 4.6 Il giro di R-DB-2 (team DB, 2026-11-25)

**Il changeSet:**
`20_code/script/20261124-14-update-fn-get-user-profile-emittente-senza-gestore-globale`. Il corpo
vivo (`pg_get_functiondef` sullo scratch) è identico, confrontato, al corpo di `20261007-10`. Ne
riprende la firma e il COMMENT ancorati a `%TYPE`, quindi la firma resta la stessa e non nasce un
overload. È sostituito il solo blocco 3, e la sostituzione è contata: la `UNION ALL` diventa una
lettura della riga di `config.user_emittenti_fiscali`. Il filtro `ef.attivo` resta. Il COMMENT
porta la revisione. Il rollback rimette il corpo e il COMMENT di prima.

**Il pgTAP:** `script/test-fn-get-soggetto-dati-and-user-profile.sql`, da 26 a 30 asserzioni.

* ⭐ Il gestore globale **si costruisce** se manca. Sullo scratch del 2026-11-25 non c'era (fatto
  datato), e senza di lui i casi sarebbero verdi anche col ripiego, perché il ripiego non avrebbe
  niente da restituire. Il caso 28 lo rende un'asserzione.
* Il caso configurato usa un operatore **umano**, legato a un'azienda nuova con
  `dbops.fn_pgtap_sposta_scope_operatore`. L'utente tecnico di `fn_pgtap_crea_emittente_operatore`
  non ha una risorsa umana, e il profilo lo rifiuta (`E_ADMIN_VALIDAZIONE`): il primo tentativo è
  caduto lì.
* I casi: 28, il presupposto; 29, l'operatore configurato, che ha la sua azienda e la sua riga;
  30, l'operatore senza riga, che riceve NULL; 31, il super admin senza riga, che riceve NULL.

**Le prove (scratch, 2026-11-25):**

* l'estratto gira per intero e poi va in ROLLBACK, col catalogo identico;
* il pgTAP del profilo: senza l'estratto 28 ok e 2 not ok, cioè il 30 e il 31, che colgono il
  ripiego; con l'estratto 30 ok e 0 not ok;
* i cinque pgTAP che chiamano `fn_get_user_profile` hanno lo stesso conteggio senza e con
  l'estratto: `config/test-credenziale-login-v1`, `anagrafiche/test-veste-operatore-spenta-v1`,
  `anagrafiche/test-emittente-denominazione-da-soggetto-v1`, `script/test-fn-veste-utilizzabile-v1`,
  `script/test-fn-get-user-profile-guc-aware`.

**Apply (Tid, 2026-11-25):** `20261124-14` applicato, pgTAP verdi.

**La documentazione:** la pagina `manual/` di `fn_get_user_profile` ha la data, il «Vedi anche»
verso `fn_resolve_emittente_for_user`, il blocco `emittente`, il flusso (passo 8) e le
ottimizzazioni. Nessuna guida descriveva il ripiego (§6.1).

### 4.7 Il giro BE/FE della prova di `/me/` (team BE/FE, 2026-11-25)

**La prova.** Un test e2e sul DB vero, in transazione annullata:
`backend/apps/core/tests/db/test_me_emittente_senza_gestore_globale_db.py` (opt-in
`ZEROERP_TEST_DB_E2E=1`). I tre utenti si **costruiscono** con i builder del pgTAP di §4.6
(`fn_pgtap_crea_operatore_umano`, `fn_pgtap_crea_emittente`, `fn_pgtap_sposta_scope_operatore`), e
anche il gestore globale, se manca: senza di lui i casi senza riga sarebbero verdi anche col
ripiego. La view `/me/` è quella vera, col claim dell'emittente attivo che il login emetterebbe
(`EmittenteAttivoService.risolvi_per_login`). Il FE ricava l'emittente di scrittura da `emittente`
**e** da `emittente_attivo`, quindi il test li prova tutti e due.

| Utente | `emittente` | `is_admin_globale` | `emittente_attivo` |
| --- | --- | --- | --- |
| super admin senza riga | NULL | `true` | nessun claim, `puo_scegliere` |
| operatore configurato | la sua azienda, con la sua riga | `false` | la sua azienda, non sceglie |
| operatore senza riga | NULL | `false` | nessun claim, non sceglie e non deve scegliere |

Esito: 4 su 4 verdi (dbdev, 2026-11-25). Il quarto è il presupposto: esiste un gestore globale
attivo, quindi il ripiego avrebbe avuto qualcosa da restituire.

**Il FE.** In `stores/auth.js`, `emittenteCorrente` aveva `if (isAdminGlobale) return null`, per
scartare il gestore globale del blocco. Dopo R-DB-2 non cambia più il risultato: «admin globale» è,
per definizione, il super admin **senza** riga (`me_view._compute_is_admin_globale`), e senza riga il
blocco è NULL. Tolta, col commento corretto; corretto anche il commento di `pratiche/stores/pratiche.js`.
In `auth.spec.js` c'è il caso 8: `emittenteScritturaId` e il ruolo sono null per l'operatore senza
riga e per l'admin in «tutti», e valgono l'emittente scelto per l'admin che ne ha uno.

**La doc BE, che era rimasta indietro rispetto a §2.** Cinque pagine `manual/` descrivevano ancora
il ripiego sul gestore globale come emittente di chi agisce, o nominavano
`get_emittente_fiscale_id_for_user`, che è stata ritirata:

* `core/manual/api_parameter_settings.md`: l'emittente di chi agisce nella lista; il 400
  `E_EMITTENTE_NON_RISOLTO` in «tutti» per POST e DELETE (`emittente_per_scrivere`); il 403
  `E_SCOPE_EMITTENTE` del guard `20261124-13` come rete, anche sul DELETE; le dipendenze DB;
* `vendite/manual/api_vendite_form_defaults.md` e `api_offerte.md`: il livello 3 della valuta è
  l'emittente di chi agisce, vuoto in «tutti»;
* `anagrafiche/manual/api_clienti.md`: lo scope della lista non ha un ripiego `is_default`, come
  il BB `fn_get_emittenti_scope_sr_ids` da cui viene.

Anche nei commenti e negli help_text dei form-defaults (`views_form_defaults.py`,
`vendite_form_defaults_service.py`) «gestore globale» indicava il livello 4 della valuta, che è
`anagrafiche.gestori` (§5), oppure il ripiego dell'«EF utente», che è ritirato. Ora sono corretti.

**Guide (`scripts/guide_coinvolte.py` sui file del giro).** Escono le guide di §6.1, dalle tabelle che
il test legge e dai builder. Sono tutte **coerenti**: il giro non cambia comportamenti, e prova
quello che `risorse-umane-e-accessi` e §7.1 di `architettura-permessi-e-autorizzazioni` descrivono
già. Anche `pgtap-come-si-scrive-un-test` è coerente: il test usa i builder come li descrive la
guida. **Orfani:** `/api/v1/core/me/` (endpoint, documentato in `docs/it/backend/`) e
`dbops.fn_pgtap_sposta_scope_operatore` (builder di test). Sono dettagli interni.

**Test lanciati:** il test e2e nuovo, `core.tests.api.test_me_view`,
`vendite.tests.api.test_form_defaults_api`, `vendite.tests.services.test_vendite_form_defaults_service`,
`core.tests.test_schema_openapi_registro`, e con vitest `stores/auth.spec.js` e `src/pratiche`.
Tutti verdi.

## 5. Esaminati e fuori perimetro

Non fanno parte di questa richiesta, e non vanno letti come «da allineare» per analogia:

* il terzo livello di `script.fn_get_ba_emittente_sr_id` (`is_default`) e il ripiego senza BA di
  `anagrafiche.fn_get_emittente_fiscale_id`. Rispondono a «di quale azienda è questo **billing
  account**» (o un lotto senza BA, `vendite.fn_get_or_create_lotto`), non a «chi agisce». La
  predefinita dell'installazione, lì, è il modello;
* il livello 4 della valuta (`anagrafiche.gestori`) di `vendite.fn_get_valuta_id`. Il BE vi si è
  allineato in «tutti».

## 6. Guide

* [configurazione-e-gestione-parametri](../../../guide/configurazione-e-gestione-parametri.md),
  §«I riferimenti degli ambiti»: dice «con un guard: non si crea un override verso un emittente o
  una categoria **disattivati**». Con R-DB-1 il guard di scope si aggiunge, e la guida va
  aggiornata nello stesso giro.
* [architettura-permessi-e-autorizzazioni](../../../guide/architettura-permessi-e-autorizzazioni.md):
  la regola «restringe, non allarga» di `fn_check_user_emittente_scope` è quella che R-DB-1
  applica. Coerente.
* La pagina manuale di `fn_get_user_profile` (`docs/it/dbzero/script/manual/`, L290-292 e L323)
  descrive la «risoluzione emittente con priorità … fallback gestore globale»: va aggiornata con
  R-DB-2.

### 6.1 Gli esiti del team DB (`scripts/guide_coinvolte.py`, 2026-11-25)

Lanciato su `config.parameter_overrides`, `script.trgfn_guard_emittente_scope`,
`script.fn_get_user_profile`, `script.fn_check_user_emittente_scope`,
`script.fn_resolve_emittente_for_user`.

| Guida | Esito |
| --- | --- |
| configurazione-e-gestione-parametri, §«I riferimenti degli ambiti» | **indietro**: si aggiorna con R-DB-1, nello stesso giro (il guard di scope, su INSERT, UPDATE e DELETE) |
| architettura-permessi-e-autorizzazioni, §7.1-7.2 | **coerente** sulla regola «restringe, non allarga»; **indietro** in §7.2 con R-DB-1: il guard su una tabella senza RLS guarda anche la riga di prima, e la tabella va nominata |
| risorse-umane-e-accessi | **coerente**: R-DB-2 allinea il profilo al fail-closed che la guida descrive già (senza riga nessun emittente; il solo SUPER_ADMIN è multi-emittente) |
| contratto-guc-app, gestione-dei-pagamenti, processi-pgagent-funzionali | **coerenti**, non toccate: citano il guard o lo scope per altre tabelle |

**Orfani:** `script.fn_get_user_profile` è un dettaglio interno. `script.fn_resolve_emittente_for_user`
è invece un concetto del dominio, perché è la sede della regola di §1 («l'emittente di chi
agisce»), e nessuna guida lo nomina: il candidato è §7 di architettura-permessi-e-autorizzazioni.
Se e dove scriverlo lo decide Tid; non blocca il giro.
✅ **Deciso da Tid il 2026-11-25: sì, in §7.** In `architettura-permessi-e-autorizzazioni` c'è ora
il paragrafo «Su quale azienda agisce chi lavora», in coda a §7.1, con la regola di §1: il documento,
poi chi agisce, vuoto in «tutti». Dice anche che il gestore globale non è l'azienda di nessuno che
agisca. La funzione è nel «Vedi anche». L'orfano è chiuso.

**Rilancio sui file del giro di R-DB-1 (2026-11-25).** Ho rilanciato lo script sul changeSet e sul
pgTAP, ed escono 19 guide:

* le quattro di §6.1, con gli esiti già scritti; le due «indietro» sono aggiornate (§3.2);
* `contratto-guc-app` è **coerente**: dice già che i trigger di scope leggono `app.current_user_id`
  con `script.fn_utente_di_sessione`, come fa il guard nuovo;
* `pgtap-come-si-scrive-un-test` è **coerente**: il test usa i builder come la guida li descrive;
* le altre arrivano dagli oggetti comuni che il guard usa senza cambiarli
  (`script.fn_log_and_raise_error`, `anagrafiche.identita_digitali` per il `%TYPE`,
  `config.parameters` del fixture), e non sono toccate.

**Rilancio sul changeSet di R-DB-2 (2026-11-25).** Escono 22 guide, quasi tutte dalle tabelle che il
profilo legge senza cambiarle. Nessuna descrive il ripiego del profilo sul gestore globale: lo
cercano «gestore globale», `fn_get_user_profile` e `/me/`, in `risorse-umane-e-accessi`,
`soggetti-e-ruoli-anagrafici`, `architettura-multi-face-auth` e
`architettura-permessi-e-autorizzazioni`. Sono **coerenti**. `risorse-umane-e-accessi` ne esce
anzi rafforzata: il profilo ora dice ciò che la guida descriveva già (senza riga, nessuna azienda).
