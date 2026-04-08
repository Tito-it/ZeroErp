# Refactor — Operatore ↔ Emittente fiscale e combo utility per BA

> Documento di pianificazione per la razionalizzazione del legame operatore ↔ emittente
> fiscale e per la combo utility "guidata da emittente" nei billing account.
>
> Data creazione: 2026-04-08
> Stato: **FASE 1 (DB) COMPLETATA il 2026-04-08** — Fase 2 (backend) e successive da avviare
> Branch DB target: `dev/db-tid`
> Branch backend target: `dev/backend-tid`
>
> Doc collegate (lette prima della stesura, vedi [§ Coerenza con doc esistenti](#coerenza-con-documentazione-esistente)):
> - [Architettura permessi e autorizzazioni](/guide/architettura-permessi-e-autorizzazioni)
> - [Risorse umane e accessi](/guide/risorse-umane-e-accessi)
> - [user_emittenti_fiscali (manual)](/dbzero/config/manual/user_emittenti_fiscali)
> - [emittenti_fiscali_billing_account (manual)](/dbzero/anagrafiche/manual/emittenti_fiscali_billing_account)
> - [emittenti_fiscali_utilities (manual)](/dbzero/anagrafiche/manual/emittenti_fiscali_utilities)
> - Memoria progetto: pattern slot/override matrix (`feedback_slot_override_matrix`)
> - Memoria progetto: emittente PK vs soggetto_ruolo_id (`feedback_emittente_pk_vs_soggetto_ruolo`)

---

## 1. Contesto e problema

### 1.1 Stato attuale

Il modello `config.user_emittenti_fiscali` è una **whitelist N-a-N opzionale**:
- Vuota → l'operatore vede tutti gli emittenti (semantica "fail-open").
- Una o più righe → l'operatore vede solo quelli elencati.

Il bridge `anagrafiche.risorse_umane_auth_user.ruolo_sistema` (enum `config.ruolo_sistema`)
classifica l'utente come `ADMIN` / `OPERATIVO` / `DISABILITATO`. `ADMIN` oggi significa
**bypass completo** della catena permessi (vedi [Architettura permessi §13](/guide/architettura-permessi-e-autorizzazioni#13-classificazione-utente-tipo_utente)).

I `billing_account` sono legati agli emittenti via `anagrafiche.emittenti_fiscali_billing_account`:
- 1 riga per `billing_account_id` = mapping specifico
- 1 riga con `billing_account_id NULL` e `is_default = true` = **default globale** (al massimo
  uno per istanza), usato come fallback dalla pipeline di fatturazione quando un BA non ha
  un mapping specifico.

La risoluzione dell'emittente di un BA avviene **al momento della fatturazione** (specifico → fallback default globale).

### 1.2 Problemi rilevati

1. **Ambiguità di "emittente di default per operatore"**: oggi non esiste. La scelta su quale
   emittente attribuire un nuovo BA viene rimandata alla fatturazione e dipende dalla
   configurazione del default globale, non dall'identità di chi crea il record.
2. **Mancanza del livello "admin di emittente"**: oggi `ruolo_sistema=ADMIN` significa
   "amministratore globale". Non è modellato il caso intermedio "amministratore di una
   sola azienda" (admin che configura, gestisce operatori, vede dashboard, ma solo per il
   proprio emittente).
3. **Whitelist N-a-N senza preferito**: un operatore con più di un emittente in whitelist
   non ha modo di indicare il suo "principale". Il modello attuale tollera la condizione
   ma non risolve il problema "su quale opera adesso".
4. **BA scollegati**: un BA appena creato non è legato a nessun emittente specifico finché
   non viene generata una fattura (e solo allora si applica il default globale). Non c'è
   determinismo lato applicazione.
5. **Combo utility globale**: oggi `listUtilitiesManual()` (frontend `ClienteDrawer`,
   `ClientiSearchTable`) ritorna **tutte** le utility ammesse per il ruolo del soggetto,
   senza tenere conto della matrice slot/override `emittenti_fiscali_utilities` configurata
   per l'emittente che governerà la fatturazione di quel BA.

### 1.3 Cosa vogliamo ottenere

- **Razionalizzare il modello operatore → emittente**: ogni operatore non-admin-globale è
  legato a **esattamente un emittente** (1-a-1). Niente più whitelist multipla.
- **Introdurre "admin di emittente"** senza nuovi enum: rinterpretando `ruolo_sistema=ADMIN`
  come "admin nel suo scope" (globale se senza riga in `user_emittenti_fiscali`, locale
  altrimenti).
- **Auto-link BA → emittente**: alla creazione di un `billing_account`, popolare
  automaticamente `emittenti_fiscali_billing_account` con l'emittente dell'operatore corrente.
  Default globale resta come **rete di sicurezza** per casi residui.
- **Combo utility BA-driven**: il lookup utility per BA mostra le utility ammesse per il
  ruolo del soggetto del BA, decorate con i parametri override (`emittenti_fiscali_utilities`)
  dell'emittente associato al BA.

---

## 2. Modello target

### 2.1 Tre livelli operativi (rinterpretazione di `ruolo_sistema`)

| ruolo_sistema | Righe in `user_emittenti_fiscali` | Significato |
| --- | --- | --- |
| `ADMIN` | 0 | **Admin gestore software**: vede tutti gli emittenti, può creare/modificare/cancellare emittenti, può creare admin di emittente, può creare operatori per qualunque emittente. Bypass completo dei permessi. |
| `ADMIN` | 1 | **Admin di emittente**: ha tutti i permessi su quell'unico emittente, può creare operatori per quell'emittente. **Non vede** altri emittenti. **Non può** creare admin globali. **Non può** creare altri admin di emittente. |
| `OPERATIVO` | 1 | **Operatore di emittente**: opera sull'unico emittente associato. Permessi standard via reparto + override. |
| `OPERATIVO` | 0 | **Vietato** se esistono emittenti nel sistema. Ammesso solo nello [scenario edge "0 emittenti" (gestore = emittente)](#23-edge-case-0-emittenti). |
| `DISABILITATO` | qualunque | Nessun accesso. |

> **Decisione (Q1)**: scelta **Strada (c) — reinterpretazione di `ADMIN`**.
> Pro: zero nuovi enum/flag; sfrutta la struttura esistente; il numero di righe in
> `user_emittenti_fiscali` diventa il discriminatore unico tra "globale" e "locale".
> Coerenza con la guida [Architettura permessi §13](/guide/architettura-permessi-e-autorizzazioni#13-classificazione-utente-tipo_utente):
> il significato di `ADMIN` resta "bypass permessi" — ma viene ristretto allo
> **scope emittente** quando esiste una riga in `user_emittenti_fiscali`.
> Contro: cambia retroattivamente la semantica degli `ADMIN` esistenti che eventualmente
> abbiano già righe in `user_emittenti_fiscali`. Verificato in DB: oggi nessun
> `ADMIN` ha più di 1 riga (Q3 ↓), quindi nessun impatto.

### 2.2 Vincolo 1-a-1 su `user_emittenti_fiscali`

> **Decisione (Q2)**: il vincolo `UNIQUE (auth_user_id, emittente_fiscale_id)` viene
> sostituito da `UNIQUE (auth_user_id)`. Ogni utente può avere al massimo una riga.

Pro: il DB diventa garante della regola "operatore = un solo emittente".
Contro: chi vuole davvero scope multi-emittente non può più. La risposta è: non era mai
stato un caso reale richiesto dal business, e per gli admin globali la regola rimane
"0 righe = vede tutto" (caso non penalizzato).

> **Verifica preventiva (Q3)**: query lanciata in DB
> `SELECT auth_user_id, COUNT(*) FROM config.user_emittenti_fiscali GROUP BY auth_user_id HAVING COUNT(*) > 1;`
> → **risultato: vuoto**. La migration può aggiungere il nuovo UNIQUE senza migrazione dati.

### 2.3 Edge case "0 emittenti"

Quando l'istanza non ha alcuna riga in `anagrafiche.emittenti_fiscali`, il gestore software
**è** l'emittente unico (configurazione single-tenant). In questo scenario:

- `user_emittenti_fiscali` resta **vuota** per tutti
- Tutti gli operatori vedono "tutto" perché "tutto" è il gestore stesso
- I BA non hanno bisogno di mapping (non c'è scelta)
- La regola "operatore ha un solo emittente" è **sospesa**: non c'è nulla a cui legarlo

Quando viene creato il **primo** emittente in tabella:

> **Decisione (Q4)**: scelta **(a) conservativa**.
> Tutti gli operatori esistenti restano "ADMIN globale" finché non vengono espressamente
> assegnati a un emittente. Nessuna migrazione automatica, nessun blocco implicito. L'admin
> deciderà manualmente quale operatore appartiene a quale emittente.
> Pro: zero rischio di rompere installazioni esistenti; pattern "fail-open con avviso"
> coerente con la filosofia "whitelist vuota = tutto" già documentata.
> Contro: durante la transizione il sistema è permissivo. Se l'admin si dimentica,
> tutti gli operatori restano globali. Mitigazione: una notifica/banner UI nelle pagine
> di amministrazione operatori.

Quando viene creato un **nuovo** emittente in un'istanza che ne ha già altri:

> **Decisione (Q5)**: nessuna azione automatica sugli operatori. Il nuovo emittente
> è "uno fra tanti", il default globale resta valido. L'admin assegna gli operatori
> manualmente come per Q4.

Quando esiste **un solo** emittente nel sistema:

> **Decisione (Q8)**: tutti gli operatori vengono **automaticamente** legati a esso
> (popolata `user_emittenti_fiscali`). La regola 1-a-1 si applica uniformemente.
> Pro: niente eccezioni. Chi crea il primo emittente attiva automaticamente lo scope.
> Contro: il singleton emittente "sembra" indistinguibile dal caso "0 emittenti", ma
> in realtà è strutturalmente diverso (i permessi vengono filtrati esplicitamente).

### 2.4 Auto-link BA → emittente alla creazione

Alla creazione di una riga in `anagrafiche.billing_account`, il sistema deve **automaticamente**
inserire una riga in `anagrafiche.emittenti_fiscali_billing_account` collegando il BA
all'emittente dell'operatore corrente.

Resolver dell'emittente:

```
fn_resolve_emittente_for_user(p_auth_user_id) RETURNS bigint
  -- ritorna emittenti_fiscali.id, oppure NULL
  IF esistono righe per p_auth_user_id in user_emittenti_fiscali THEN
    RETURN quella riga (sempre 1 dopo la migration UNIQUE)
  ELSE  -- admin globale
    IF cnt_emittenti_attivi() = 0 THEN
      RETURN NULL  -- gestore = emittente, niente da linkare
    ELSE
      -- admin globale + esistono emittenti = ambiguità
      -- comportamento dipende da Q6 (vedi sotto)
      RETURN ... 
```

> **Decisione (Q6)**: scelta **(c)**.
> *L'admin globale non crea BA direttamente. La creazione di BA è ammessa solo agli
> operatori per emittente (operativi o admin di emittente).*
>
> **Pro**:
> - Il modello resta deterministico: ogni BA viene creato con un'identità precisa,
>   l'emittente è univocamente determinato.
> - Elimina la classe di bug "admin globale crea un BA per errore senza scegliere
>   l'emittente, finisce sul default globale, poi serve correzione manuale".
> - Coerente con la separazione delle responsabilità: l'admin globale fa amministrazione
>   di sistema, non operations day-by-day. L'admin di emittente delega operativamente.
> - Semplifica i check di sicurezza nei service: non serve chiedersi "questo utente è
>   admin globale o no, e se sì cosa devo fare?" — il check è uniforme: "deve esistere
>   un emittente associato".
>
> **Contro**:
> - Riduce la flessibilità: un'azienda piccola dove l'admin è anche l'operatore deve
>   creare un secondo account di tipo "operatore di emittente" per sé stesso. Mitigazione:
>   nello scenario Q8 (singolo emittente), tutti gli operatori sono automaticamente legati
>   all'emittente unico, quindi anche l'admin (se passa attraverso il flusso operativo)
>   ha accesso. Per il caso ADMIN globale "puro", deve loggarsi come l'altro account o
>   eccezionalmente promuovere temporaneamente sé stesso a operatore di un emittente.
> - Edge case: durante setup iniziale (prima migrazione di un'istanza esistente verso
>   il nuovo modello), nessun operatore è ancora associato — l'admin globale dovrà
>   creare gli operatori e i BA in due fasi. Mitigazione: documentare il flusso di
>   primo setup; consentire una fase "bootstrap" controllata via flag.
> - Edge case: nello scenario "0 emittenti" (Q4) tutti sono admin globali, eppure devono
>   poter creare BA. La regola va declinata: il blocco "admin globale non crea BA" si
>   applica **solo** se esistono emittenti in sistema. Se non esistono, l'admin globale
>   crea BA senza vincoli, e il trigger di auto-link semplicemente non popola
>   `emittenti_fiscali_billing_account` (ritorna NULL).
>
> **Implementazione del vincolo "admin globale non crea BA"**:
> - **Hard via guard DB**: trigger `BEFORE INSERT ON billing_account` che chiama una
>   funzione `script.fn_check_user_can_create_ba(p_auth_user_id)` che ritorna FALSE se
>   l'utente è admin globale **e** esistono emittenti. Solleva `E_BA_ADMIN_GLOBALE_VIETATO`.
> - **Soft lato applicativo**: il service Django che crea BA verifica preventivamente e
>   ritorna `ServiceError`. Doppia barriera coerente col pattern defense-in-depth.

### 2.5 Q7 — Chi può creare/modificare gli operatori

| Operazione | Admin globale | Admin di emittente | Operatore standard |
| --- | --- | --- | --- |
| Crea operatore standard di qualunque emittente | ✅ | ❌ | ❌ |
| Crea operatore standard del proprio emittente | ✅ | ✅ | ❌ |
| Crea admin di emittente per qualunque emittente | ✅ | ❌ | ❌ |
| Crea admin di emittente per il proprio emittente | ✅ | ❌ | ❌ |
| Crea admin globale | ✅ | ❌ | ❌ |
| Modifica/disattiva operatore del proprio emittente | ✅ | ✅ | ❌ |
| Modifica/disattiva operatore di altro emittente | ✅ | ❌ | ❌ |

> **Decisione (Q7)**: prime due righe sì, ultime due no.
> Riformulato: l'admin di emittente gestisce gli **operatori standard** del suo emittente,
> ma **non promuove altri admin** (né locali né globali). La promozione resta privilegio
> esclusivo dell'admin globale. Pattern di delega "single hop", evita che la gerarchia
> di amministrazione sfugga al controllo.

---

## 3. Combo utility "guidata da emittente"

### 3.1 Stato attuale

- `LookupRepository.list_utilities_per_ruolo(ruolo)` — strict: ritorna utility di
  `config.utilities_tipi_ruolo` filtrate per ruolo.
- `LookupRepository.list_entity_utility_matrix(entity_soggetto_ruolo_id, ruolo, table, fk)` —
  matrice slot/override LEFT JOIN, oggi usata **solo** dentro il drawer Utilities di
  un emittente per popolare la matrice configurabile (vedi memoria
  `feedback_slot_override_matrix`).
- Frontend: `ClienteDrawer`, `ClientiSearchTable`, `FornitoreDrawer` chiamano
  `listUtilitiesManual()` (endpoint `anagrafiche/utilities/manual-lookup/`) che ritorna
  utility globali per il ruolo del soggetto, senza vincolo di emittente.

### 3.2 Cosa vuoi ottenere

Quando l'operatore costruisce o seleziona la utility di un BA, la combo deve mostrare
**l'intersezione**:

1. utility ammesse per il ruolo del soggetto del BA (`CL`, `FO`, `GE`, …) in `config.utilities_tipi_ruolo`
2. utility ammesse per il ruolo `EF` dell'emittente collegato al BA, in `config.utilities_tipi_ruolo`
3. decorate con i parametri override di `anagrafiche.emittenti_fiscali_utilities` quando
   esistono per quella coppia (emittente, utility)

Le righe non personalizzate **rimangono visibili** (politica ibrida): l'app applicherà
i default di sistema. Le utility che mancano in (1) o in (2) sono **escluse**.

> **Decisione (politica filtro)**: politica ibrida (C). Confermata anche dopo verifica
> che la matrice `emittenti_fiscali_utilities` rimane come "override parametri", non
> come "whitelist abilitazione" — coerente con la memoria `feedback_slot_override_matrix`
> e con la doc [`emittenti_fiscali_utilities`](/dbzero/anagrafiche/manual/emittenti_fiscali_utilities).
> Pro: estensibilità (nuove utility ammesse per il ruolo `EF` entrano automaticamente).
> Contro: l'admin di emittente non può "togliere" utility specifiche se non
> rimuovendole dalla matrice base `config.utilities_tipi_ruolo` (azione globale).

### 3.3 Funzione SQL nuova

```text
anagrafiche.fn_lookup_utilities_per_ba(
    p_billing_account_id bigint,
    p_ruolo_codice_soggetto text  -- 'CL', 'FO', 'GE'...
) RETURNS TABLE (
    utility_id bigint,
    codice text,
    descrizione text,
    is_personalizzata_per_ef boolean,
    minimo_soglia_min numeric,
    minimo_soglia_max numeric,
    arrotondamento_importi_dec smallint,
    metodo_arrotondamento_importi text
)
```

Logica:

1. Risolvi `v_emittente_soggetto_ruolo_id` dal BA via `emittenti_fiscali_billing_account`
   (specifico, fallback default globale).
2. JOIN su `config.utilities_tipi_ruolo` per ruolo soggetto **e** per ruolo `EF`.
3. LEFT JOIN su `anagrafiche.emittenti_fiscali_utilities` per ottenere parametri override.
4. Filtra solo righe attive con periodo di validità corrente.

### 3.4 Endpoint backend

`GET /api/v1/anagrafiche/billing-account/{ba_id}/utilities/?ruolo=CL`

- Permission check: `EmittenteFiscaleScopeMixin` deve permettere all'operatore di vedere
  il BA.
- Cache lato server: questa lista cambia raramente per un dato BA — TTL ragionevole.

### 3.5 Frontend

- `ClienteDrawer.vue`: in **modifica** (BA esiste) sostituire `listUtilitiesManual()`
  con il nuovo endpoint. In **creazione** (BA non esiste ancora) usare l'emittente
  dell'operatore corrente per pre-filtrare la combo. Una volta creato il cliente
  (e quindi il BA), lo state si allinea.
- `ClientiSearchTable.vue`: filtro utility allineato all'emittente operatore.
- Stesso pattern per `FornitoreDrawer`, eventuali altri drawer che selezionano una
  utility per un BA.
- Nuovo composable `useEmittenteCorrente()` (frontend) che legge dall'`/api/v1/me/profile/`
  (o equivalente) l'emittente associato all'operatore loggato.

---

## 4. Coerenza con documentazione esistente

Verifiche fatte prima della stesura del WIP per evitare contraddizioni con scelte
architetturali pregresse:

| Doc | Punto verificato | Esito |
| --- | --- | --- |
| [Architettura permessi §4.9](/guide/architettura-permessi-e-autorizzazioni#49-tabella-configuser_emittenti_fiscali) | "Whitelist opzionale" | **Ridefinita**: la semantica "whitelist multipla" viene ridotta a 1-a-1. Aggiornare il §4.9 dopo l'implementazione. |
| [Architettura permessi §13](/guide/architettura-permessi-e-autorizzazioni#13-classificazione-utente-tipo_utente) | `ADMIN = bypass completo permessi` | **Compatibile**: bypass resta, ma viene applicato **nello scope emittente**. La modifica è semantica, non strutturale. Aggiornare il §13 con la nuova nota "ADMIN globale vs ADMIN di emittente". |
| [Risorse umane e accessi §Tabelle](/guide/risorse-umane-e-accessi) | `ruolo_sistema ADMIN/OPERATIVO/DISABILITATO` | **Compatibile**: nessun nuovo enum, solo nuova interpretazione condizionale a `user_emittenti_fiscali`. |
| [user_emittenti_fiscali manual](/dbzero/config/manual/user_emittenti_fiscali) | "fail-open se vuoto = tutti" | **Mantenuto** ma solo per `ADMIN`. Per `OPERATIVO` diventa "vietato se esistono emittenti". Aggiornare il manual dopo l'implementazione. |
| [emittenti_fiscali_billing_account manual](/dbzero/anagrafiche/manual/emittenti_fiscali_billing_account) | "default globale come best practice operativa" | **Compatibile**: il default globale resta come **fallback** e per il caso "0 emittenti" / setup iniziale. Diventa rete di sicurezza, non meccanismo principale. Aggiornare il manual con nota "rete di sicurezza". |
| [emittenti_fiscali_utilities manual](/dbzero/anagrafiche/manual/emittenti_fiscali_utilities) | "matrice slot/override parametri" | **Mantenuto invariato**. La combo BA-driven legge da questa stessa tabella, non cambia la sua semantica. |
| [Permessi v2 wip](/dev/work-in-progress/permessi-e-autorizzazioni-v2) | livello oggetto granulare | **Indipendente**: il refactor operatore-emittenti vive sul piano "scope emittente", la v2 vive sul piano "livello model". Sono ortogonali. |
| Memoria `feedback_emittente_pk_vs_soggetto_ruolo` | `fn_get_emittente_fiscale_id` ritorna `soggetto_ruolo_id`, non PK | **Recepito**: il resolver `fn_resolve_emittente_for_user` deve fare attenzione a quale identificatore ritorna. Convenzione: ritornare `emittenti_fiscali.id` (PK reale). |
| Memoria `feedback_slot_override_matrix` | la matrice utility per emittente è override, non whitelist | **Recepito**: la combo BA-driven adotta la **politica ibrida** (mostra tutte ammesse, decora con override). |

**Nessuna contraddizione individuata.** I cambiamenti alla doc esistente sono solo
*aggiornamenti incrementali* (note e precisazioni), non *invalidazioni*.

---

## 5. Pezzi da costruire

### 5.1 DB (branch `dev/db-tid`)

| # | Migration | Scopo |
| --- | --- | --- |
| 1 | `00_schema/config/AAAAMMGG-NN-alter-user-emittenti-fiscali-uniq-auth-user.yaml` | Sostituisce `UNIQUE(auth_user_id, emittente_fiscale_id)` con `UNIQUE(auth_user_id)`. Sicuro perché Q3 = vuoto. |
| 2 | `20_code/anagrafiche/AAAAMMGG-NN-create-fn-resolve-emittente-for-user.yaml` | Funzione resolver che ritorna l'emittente dell'operatore o NULL. |
| 3 | `20_code/script/AAAAMMGG-NN-create-fn-check-user-can-create-ba.yaml` | Guard "admin globale non crea BA se esistono emittenti". |
| 4 | `20_code/anagrafiche/AAAAMMGG-NN-create-trgfn-billing-account-link-ef.yaml` | Trigger `AFTER INSERT ON billing_account` che chiama il resolver e popola `emittenti_fiscali_billing_account`. |
| 5 | `20_code/anagrafiche/AAAAMMGG-NN-create-trg-billing-account-guard-admin-globale.yaml` | Trigger `BEFORE INSERT ON billing_account` che applica il guard di Q6. |
| 6 | `20_code/anagrafiche/AAAAMMGG-NN-create-fn-lookup-utilities-per-ba.yaml` | Funzione SQL per la combo utility BA-driven. |
| 7 | `db/pgtap/anagrafiche/test-billing-account-auto-link-ef.sql` | Test pgTAP: trigger di auto-link in casi normale, edge case "0 emittenti", fallback default globale. |
| 8 | `db/pgtap/anagrafiche/test-fn-lookup-utilities-per-ba.sql` | Test pgTAP: politica ibrida (utility ammesse per ruolo BA × ruolo EF, decorate con override quando presenti). |
| 9 | `db/pgtap/script/test-fn-check-user-can-create-ba.sql` | Test pgTAP: guard admin globale. |

**Dipendenza prerequisito**: la migration #4 dipende dal middleware GUC `app.current_user_id`
(documentato in [Architettura permessi §6.4](/guide/architettura-permessi-e-autorizzazioni#64-middleware-sessione-postgresql)).
Verificato: il middleware **esiste già** e setta `app.current_user_id`. La trigger function
del punto #4 può leggerlo via `current_setting('app.current_user_id', true)::int`.

### 5.2 Backend (branch `dev/backend-tid`)

| # | Cosa | Dove |
| --- | --- | --- |
| 1 | `PermissionResolver.get_emittente_for_user(user)` | `apps/core/services/permissions_resolver.py` — wrapper Python sulla nuova `fn_resolve_emittente_for_user`. Cached come gli altri metodi. |
| 2 | `LookupRepository.list_utilities_per_billing_account(ba_id, ruolo)` | `apps/core/db/lookup_repository.py` — chiama la nuova `fn_lookup_utilities_per_ba`. |
| 3 | Endpoint `GET /api/v1/anagrafiche/billing-account/{id}/utilities/?ruolo=CL` | `apps/anagrafiche/api/views_billing_account.py` (o nuovo file dedicato) |
| 4 | `BillingAccountCreationService` (consolidamento) | Censire i call site attuali (`clienti_repository.create_billing_account` ecc.) e centralizzarli in un unico service che invoca l'INSERT con il trigger di auto-link che si occupa del resto. |
| 5 | Test mock-based | `apps/anagrafiche/tests/services/`, `apps/core/tests/db/` |

### 5.3 Frontend (branch `dev/backend-tid` o `dev/frontend-*`)

| # | Cosa | Dove |
| --- | --- | --- |
| 1 | Composable `useEmittenteCorrente()` | `frontend/src/core/composables/` — legge l'emittente corrente dal profilo utente. |
| 2 | Sostituire `listUtilitiesManual()` con il nuovo endpoint per i drawer in modalità modifica | `ClienteDrawer.vue`, `FornitoreDrawer.vue`, `ClientiSearchTable.vue` |
| 3 | Banner UI "operatore non assegnato" nei pannelli di gestione operatori per i casi di transizione (Q4) | `frontend/src/amministrazione/views/OperatoriListView.vue` o equivalente |
| 4 | Disabilitare creazione BA per admin globali nel UI quando esistono emittenti | dovunque sia il flusso di creazione BA |

---

## 6. Roadmap e ordine di lavoro

**Fase 1 — DB foundations** (`dev/db-tid`)
1. Migration UNIQUE su `user_emittenti_fiscali`
2. Funzione `fn_resolve_emittente_for_user`
3. Funzione `fn_check_user_can_create_ba` + trigger guard
4. Trigger di auto-link `trgfn_billing_account_link_ef`
5. pgTAP per tutti e tre

**Fase 2 — Backend** (`dev/backend-tid`)
1. `PermissionResolver.get_emittente_for_user`
2. Refactor service "creazione BA" (consolidamento)
3. Endpoint utility per BA + repository method
4. Test mock-based

**Fase 3 — Funzione lookup utility per BA** (DB+backend)
1. `fn_lookup_utilities_per_ba`
2. `LookupRepository.list_utilities_per_billing_account`
3. Endpoint
4. pgTAP + test mock

**Fase 4 — Frontend**
1. `useEmittenteCorrente()`
2. Sostituzione lookup utility nei drawer
3. UX banner "operatore non assegnato"
4. Disable creazione BA per admin globali

**Fase 5 — Documentazione**
1. Aggiornare [Architettura permessi §4.9 e §13](/guide/architettura-permessi-e-autorizzazioni)
2. Aggiornare [user_emittenti_fiscali manual](/dbzero/config/manual/user_emittenti_fiscali)
3. Aggiornare [emittenti_fiscali_billing_account manual](/dbzero/anagrafiche/manual/emittenti_fiscali_billing_account)
4. Spostare questo WIP in `work-done/` con nota di completamento
5. Aggiornare le memorie progetto pertinenti (`feedback_emittente_pk_vs_soggetto_ruolo`,
   `feedback_slot_override_matrix`) con riferimento al refactor

---

## 7. Decisioni operative chiuse

Tutte le decisioni Q1–Q8 sono state risolte (vedi sezioni 2.x). Anche le tre dipendenze
operative D1–D3 sono ora chiuse:

### D1 — Setup iniziale: gestione manuale "advise, don't enforce"

> **Decisione**: nessun wizard guidato, nessuna migrazione di seed automatica.
> L'admin globale gestisce manualmente la prima configurazione: crea l'emittente,
> assegna gli operatori uno per uno tramite la UI di amministrazione operatori.

Per facilitare l'admin senza forzare nulla, vengono aggiunti **due aiuti informativi**.

**Aiuto 1 — Funzione SQL `script.fn_get_setup_status() RETURNS jsonb`**: ritorna in un
colpo solo lo stato dell'istanza. Una sola query, una sola riga risultato. Pensata per
essere chiamata dal frontend ad ogni apertura della pagina di amministrazione operatori.
Esempio di output:

```json
{
  "emittenti_attivi": 3,
  "operatori_totali": 12,
  "operatori_assegnati": 8,
  "operatori_admin_globali": 1,
  "operatori_non_assegnati": 3
}
```

**Aiuto 2 — Banner UI nelle pagine di amministrazione operatori**: legge l'output di
`fn_get_setup_status()` e, se `operatori_non_assegnati > 0`, mostra un banner informativo
"Ci sono N operatori senza emittente assegnato — vuoi configurarli adesso?". **Non blocca
nulla**, è solo un suggerimento.

Pattern: **advise, don't enforce**. L'admin ha sempre visibilità di "cosa manca"
senza che il sistema lo forzi a configurarlo subito. Coerente con la filosofia
"fail-open con avviso" già adottata in altri punti della guida architettura permessi.

### D2 — Rollback: nessuno, "testa bassa"

> **Decisione**: non si pianifica una procedura di rollback. Si va avanti finche'
> il refactor funziona, eventuali regressioni si fixano in avanti. Non c'e' produzione
> da proteggere.

Nota tecnica: le migration Liquibase devono comunque includere il blocco `rollback`
minimo previsto dalla sintassi (es. `DROP CONSTRAINT ...` per la migration UNIQUE,
`DROP FUNCTION ...` per le nuove funzioni). Non e' "preparazione del rollback":
e' rispetto della convenzione Liquibase per evitare warning in CI. Il blocco
non viene mai eseguito in pratica.

### D3 — Cambio operatore tra emittenti: VIETATO

> **Decisione**: un operatore non puo' MAI cambiare emittente. Per "trasferire" un
> dipendente da Emittente A a Emittente B all'interno dello stesso gestore, l'admin
> **disattiva l'utente per Emittente A** (cessazione tipica: `risorse_umane.attivo=false`
> + `risorse_umane_auth_user.ruolo_sistema=DISABILITATO` o disattivazione `auth_user.is_active`)
> e **crea un nuovo utente** legato a Emittente B.

**Pro di questa scelta drastica**:

- **Audit trail naturale**: ogni utente = una sola azienda, sempre. Quando guardi
  uno storico (`risorse_umane_auth_user.user_insert/data_insert`, log fatture, ecc.)
  sai esattamente per quale emittente l'utente ha lavorato. Niente storia da ricostruire.
- **Niente storicizzazione su `user_emittenti_fiscali`**: la tabella resta semplice,
  immutabile dopo l'inserimento, niente bisogno di `valido_dal/valido_al`,
  `storicizza`, o tabella `storico.user_emittenti_fiscali`.
- **Niente edge case di migrazione dati visibili**: non puo' mai succedere
  "l'utente X l'anno scorso era admin di EmittA e oggi di EmittB ma la fattura del
  marzo scorso che ha emesso a quale emittente apparteneva?". Domanda che non si pone
  perche' l'utente di marzo era un altro account.
- **GDPR-friendly**: cessazione di un'entita' lavorativa per un'azienda = chiusura
  account = chiusura traccia per quell'azienda. Pulito.
- **Niente "giochini"** (parole di Tid): nessuna tentazione di patch SQL diretta o
  workaround applicativo per "spostare" un utente.

**Implementazione del vincolo**:

- **Trigger DB `lock_columns`** su `config.user_emittenti_fiscali.emittente_fiscale_id`:
  una volta inserita la riga, `emittente_fiscale_id` diventa **immutabile**. Lo
  UPDATE su questa colonna solleva `E_LOCK_COLUMN`. Pattern gia' usato su
  `emittenti_fiscali.codice` (vedi memoria progetto).
- **Eliminazione della riga** ammessa solo come parte del flusso di disattivazione
  utente (cessazione completa). Per garantirlo si aggiunge un trigger
  `BEFORE DELETE` che verifica che `auth_user.is_active=false` (oppure consente
  la DELETE solo se l'utente sta venendo cancellato in cascata). Implementazione
  precisa da definire al momento della migration.

---

## 7bis. Note di implementazione Fase 1 DB (2026-04-08)

Sezione registrata a posteriori per documentare le scelte operative prese durante l'esecuzione effettiva della Fase 1 e le piccole deviazioni rispetto al piano §5.1.

### 7bis.1 Schema delle nuove funzioni

Il piano §5.1 indicava `anagrafiche` per `fn_resolve_emittente_for_user` e `script` per `fn_check_user_can_create_ba`. **Tutte e tre** le funzioni nuove (resolver, check, setup_status) sono state collocate in **schema `script`** per coerenza con il refactor permessi del 2026-03-08, che ha già spostato 9 resolver cross-dominio da `config` a `script`. La regola applicata: una funzione che legge da più schemi (`config.user_emittenti_fiscali` + `anagrafiche.emittenti_fiscali` + `django.auth_user`) sta in `script`. Solo `fn_lookup_utilities_per_ba` e i due `trgfn_billing_account_*` restano in `anagrafiche`, perché specifici del dominio fatturazione.

### 7bis.2 Bug critico evitato — filtro `ef.attivo` nel resolver

Una prima versione di `fn_resolve_emittente_for_user` filtrava `ef.attivo = true`, mentre `fn_check_user_can_create_ba` no. **Inconsistenza**: un utente con riga su EF disattivato sarebbe passato il check (true) ma il resolver avrebbe ritornato NULL → il guard avrebbe lasciato passare la INSERT del BA, ma il trigger di link non l'avrebbe agganciato → BA scollegato. Il filtro è stato **rimosso** dal resolver. Motivazione: per costruzione l'EF associato a un utente è sempre attivo, garantito da due trigger di guardia esistenti:

- `dbops.trgfn_child_requires_active_parent` su `user_emittenti_fiscali` blocca INSERT/UPDATE su EF non attivo
- `dbops.trgfn_prevent_deactivate_if_children` su `emittenti_fiscali` blocca la disattivazione di un EF con righe figlie in `user_emittenti_fiscali`

Le due funzioni sono ora **coerenti**: entrambe valutano "esiste riga in user_emittenti_fiscali?" senza filtri ulteriori.

### 7bis.3 Pattern unico file per trigger function + trigger

Per ogni nuovo trigger ho usato un singolo file YAML con `runOnChange: true` contenente sia `CREATE OR REPLACE FUNCTION` sia `DROP TRIGGER IF EXISTS` + `CREATE TRIGGER`. Idempotente, evita la proliferazione di file separati. Pattern già usato in altre migration del repo (es. `20260301-14-update-trgfn-billing-account-guard-normalize`).

### 7bis.4 Test pgTAP — lezione "no savepoint"

Il primo draft di `test-billing-account-auto-link-ef.sql` usava `SAVEPOINT ... ROLLBACK TO SAVEPOINT` per isolare gli effetti collaterali tra test. **Non funziona**: pgTAP traccia lo stato dei test in una temp table interna, e un `ROLLBACK TO SAVEPOINT` cancella le righe di stato dei test eseguiti dentro il savepoint, facendo fallire `finish()` con `# No tests run!` (anche se le `is/throws_like` hanno effettivamente girato). **Soluzione adottata**: niente savepoint, tutto in una sola transazione `BEGIN ... ROLLBACK`, e per evitare collisioni su `UNIQUE(istanza_utility_id, utility_id)` si usano N BA template distinti (uno per test). Pattern da seguire per i futuri test pgTAP.

### 7bis.5 Test pgTAP — lezione "throws_like e pattern fragili"

Il primo pattern `'%disattivat%'` in `test-user-emittenti-fiscali-immutable.sql` non matchava il messaggio anche se la sottostringa era presente. Comportamento non spiegato, possibile peculiarità di `throws_like` su frammenti di parola con apostrofi/accenti vicini. **Regola adottata**: usare substring iniziali ASCII puri (es. `'%Eliminazione vietata%'`) come pattern, evitare frammenti di parola in mezzo.

### 7bis.6 Dipendenza backend — GUC `app.current_user_id`

I trigger `trgfn_billing_account_guard_admin_globale` e `trgfn_billing_account_link_ef` dipendono dal GUC `app.current_user_id` settato dal middleware Django `JwtAuditMiddleware` ([backend/apps/core/middleware/jwt_audit_middleware.py](/it/backend/core/manual/jwt_audit_middleware)).

⚠️ **Da verificare lato backend** (non parte dello scope DB): il middleware setta il GUC con `SET LOCAL` / `set_config(..., true)`, che ha **scope transazione**. Django gira in autocommit per default (nessun `ATOMIC_REQUESTS` in `settings.py`), quindi il GUC potrebbe essere perso dopo il `COMMIT` automatico dello statement che lo setta. Se così fosse, anche i trigger del refactor permessi 2026-03-08 (`fn_check_user_emittente_scope`) sarebbero inerti — quindi probabilmente esiste un wrapping `transaction.atomic()` da qualche parte (alcune service esistenti come `clienti_service.py` usano già `with transaction.atomic():`). **La parte DB resta corretta in entrambi gli scenari**: in caso di GUC NULL i trigger fanno skip fail-open, mantenendo il comportamento attuale (BA creato senza mapping specifico, fallback default globale alla fatturazione).

Issue da aprire per il team backend: verificare formalmente che il GUC arrivi ai trigger su tutte le request che fanno INSERT su `billing_account`.

### 7bis.7 Q8 (auto-link operatori a singolo emittente) — non implementato

Il caso edge **Q8** del piano (singolo emittente nel sistema → tutti gli operatori automaticamente legati a esso) **non è implementato in questa tornata DB**. È una operazione di seed/setup che va eseguita una sola volta quando viene creato il primo emittente. Implementazione candidata: funzione utility `script.fn_link_all_operators_to_singleton_ef()` da invocare esplicitamente dal service backend di creazione emittente, oppure trigger `AFTER INSERT` su `anagrafiche.emittenti_fiscali` con conteggio `= 1`. Da definire in fase 2 (backend) o successivo refinement.

### 7bis.8 File creati / modificati — sintesi

**Migration** (`db/changelog/migrations_v2/`):

- `00_schema/config/20260408-11-alter-user-emittenti-fiscali-uniq-auth-user-mctit.yaml`
- `20_code/script/20260408-12-create-fn-resolve-emittente-for-user-mctit.yaml`
- `20_code/script/20260408-13-create-fn-check-user-can-create-ba-mctit.yaml`
- `20_code/anagrafiche/20260408-14-create-trgfn-billing-account-guard-admin-globale-mctit.yaml`
- `20_code/anagrafiche/20260408-15-create-trgfn-billing-account-link-ef-mctit.yaml`
- `20_code/config/20260408-16-create-trg-user-emittenti-fiscali-lock-emittente-mctit.yaml`
- `20_code/config/20260408-17-create-trgfn-user-emittenti-fiscali-guard-delete-mctit.yaml`
- `20_code/anagrafiche/20260408-18-create-fn-lookup-utilities-per-ba-mctit.yaml`
- `20_code/script/20260408-19-create-fn-get-setup-status-mctit.yaml`
- `80_data/sql/config/messaggi_errore.csv` (+3 righe id 358–360)

**pgTAP** (`db/pgtap/`):

- `script/test-fn-resolve-emittente-for-user.sql`
- `script/test-fn-check-user-can-create-ba.sql`
- `script/test-fn-get-setup-status.sql`
- `anagrafiche/test-billing-account-auto-link-ef.sql`
- `anagrafiche/test-fn-lookup-utilities-per-ba.sql`
- `config/test-user-emittenti-fiscali-immutable.sql`

**Manual concettuali** (`docs/it/dbzero/<schema>/manual/`):

- aggiornati: `config/user_emittenti_fiscali.md`, `anagrafiche/billing_account.md`, `anagrafiche/emittenti_fiscali_billing_account.md`
- creati: `script/fn_resolve_emittente_for_user.md`, `script/fn_check_user_can_create_ba.md`, `script/fn_get_setup_status.md`, `anagrafiche/trgfn_billing_account_guard_admin_globale.md`, `anagrafiche/trgfn_billing_account_link_ef.md`, `anagrafiche/fn_lookup_utilities_per_ba.md`, `config/trgfn_user_emittenti_fiscali_guard_delete.md`

---

## 8. Note finali

- **Branch e PR**: ogni fase = PR atomica. Non mischiare DB+backend nello stesso commit.
- **Test pgTAP obbligatori** per tutte le funzioni nuove (sez. 5.1 #7-9).
- **Niente modifiche di facciata sui drawer esistenti** (le modifiche operative al
  refactor del drawer Utilities/BA emittente fiscale fatte negli sprint precedenti
  restano valide e non vanno toccate).
- **Coerenza con `feedback_useapihandler_solo_axios`**: i nuovi store action devono
  ritornare dati già unwrappati e i call site nei drawer devono usare `try/catch`
  diretto, **non** `useApiHandler.execute()`.
- ⚠️ **Prerequisito di funzionamento (post Fase 1 DB)**: i trigger introdotti dalla
  Fase 1 (`trgfn_billing_account_guard_admin_globale`, `trgfn_billing_account_link_ef`)
  leggono il GUC PostgreSQL `app.current_user_id` impostato dal middleware Django
  `JwtAuditMiddleware`. Il middleware usa `SET LOCAL` / `set_config(..., true)`,
  che ha **scope transazione**: in autocommit Django (default attuale, nessun
  `ATOMIC_REQUESTS`) il GUC verrebbe perso al COMMIT automatico dello statement
  che lo setta. **Se così fosse**, i trigger fanno skip fail-open in assenza del GUC
  e il refactor risulta operativamente inerte (BA creato senza mapping specifico,
  fallback default globale alla fatturazione, sistema non si rompe ma il valore
  aggiunto del refactor non è realizzato). La verifica è il task **BE-2.0** in
  cima alla check-list di Fase 2 backend, ed è **bloccante** per dichiarare
  completo il refactor. Vedi anche [§7bis.6](#7bis6-dipendenza-backend--guc-appcurrent_user_id).

---

## 9. Contratti tecnici

> Sezione "interfaccia": nomi, firme, codici errore vincolanti per i 3 layer.
> Una volta fissati qui, DB / backend / frontend possono lavorare in parallelo
> senza ambiguità.

### 9.1 Funzioni SQL nuove

| Funzione | Schema | Input | Output | Volatilità |
| --- | --- | --- | --- | --- |
| `fn_resolve_emittente_for_user` | `anagrafiche` | `p_auth_user_id integer` | `bigint` (PK reale `emittenti_fiscali.id`, oppure NULL) | `STABLE` |
| `fn_check_user_can_create_ba` | `script` | `p_auth_user_id integer` | `boolean` | `STABLE` |
| `fn_lookup_utilities_per_ba` | `anagrafiche` | `p_billing_account_id bigint, p_ruolo_codice_soggetto text` | `TABLE(utility_id bigint, codice text, descrizione text, is_personalizzata_per_ef boolean, minimo_soglia_min numeric, minimo_soglia_max numeric, arrotondamento_importi_dec smallint, metodo_arrotondamento_importi text)` | `STABLE` |
| `fn_get_setup_status` | `script` | nessuno | `jsonb` con chiavi `emittenti_attivi`, `operatori_totali`, `operatori_assegnati`, `operatori_admin_globali`, `operatori_non_assegnati` | `STABLE` |

**Note vincolanti per `fn_resolve_emittente_for_user`**:

- Ritorna **`emittenti_fiscali.id`** (PK reale), MAI `soggetto_ruolo_id`. Vedi memoria
  `feedback_emittente_pk_vs_soggetto_ruolo`. Il nome `id` deve essere chiaro nel
  commento della funzione.
- Logica: se l'utente ha 1 riga in `user_emittenti_fiscali` ritorna l'EF di quella
  riga; se 0 righe e `cnt_emittenti_attivi() = 0` ritorna NULL; se 0 righe e
  `cnt_emittenti_attivi() > 0` ritorna NULL (admin globale: il chiamante deve
  decidere cosa fare con NULL).

### 9.2 Trigger nuovi

| Trigger | Tabella | Fase | Eventi | Funzione | Argomenti TG_ARGV |
| --- | --- | --- | --- | --- | --- |
| `trg_user_emittenti_fiscali_a10_lock_emittente_upd` | `config.user_emittenti_fiscali` | `BEFORE` | `UPDATE OF emittente_fiscale_id` | `script.trgfn_lock_columns` | `'emittente_fiscale_id', 'EMITTENTE_NON_MODIFICABILE'` |
| `trg_user_emittenti_fiscali_a10_guard_delete_dlt` | `config.user_emittenti_fiscali` | `BEFORE` | `DELETE` | nuova `anagrafiche.trgfn_user_emittenti_fiscali_guard_delete` | nessuno |
| `trg_billing_account_a10_guard_admin_globale_ins` | `anagrafiche.billing_account` | `BEFORE` | `INSERT` | nuova `anagrafiche.trgfn_billing_account_guard_admin_globale` | nessuno |
| `trg_billing_account_z90_link_ef_ins` | `anagrafiche.billing_account` | `AFTER` | `INSERT` | nuova `anagrafiche.trgfn_billing_account_link_ef` | nessuno |

**Note vincolanti**:

- Il trigger `lock_emittente` riusa la funzione generica `script.trgfn_lock_columns`
  (pattern già esistente, vedi `emittenti_fiscali.codice`).
- Il trigger `link_ef` legge `app.current_user_id` via `current_setting('app.current_user_id', true)::int`
  (GUC settato dal middleware Django, già operativo).
- Se il resolver `fn_resolve_emittente_for_user` ritorna NULL e
  `cnt_emittenti_attivi() = 0` (caso edge "0 emittenti / gestore = emittente"):
  il trigger `link_ef` fa `RETURN NEW` senza inserire in `emittenti_fiscali_billing_account`.
- Se il resolver ritorna NULL e ci sono emittenti attivi, **non si arriva qui**:
  il trigger `guard_admin_globale` ha già bloccato la INSERT.

### 9.3 Codici errore SQL

Aggiungere a `db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv`:

| Codice | Lingua | Messaggio | HTTP suggerito | Hint |
| --- | --- | --- | --- | --- |
| `E_BA_ADMIN_GLOBALE_VIETATO` | `it` | Un amministratore globale non può creare billing account quando esistono emittenti fiscali. Operare come operatore di un emittente specifico. | `403` | `Crea un operatore di emittente o usa un account già assegnato.` |
| `EMITTENTE_NON_MODIFICABILE` | `it` | L'emittente fiscale di un operatore è immutabile. Per cambiare l'associazione disattivare l'utente e crearne uno nuovo per l'altro emittente. | `400` | `Disattiva l'utente e crea un nuovo account.` |
| `E_USER_EMITTENTE_DELETE_VIETATO` | `it` | Eliminazione vietata: l'associazione utente-emittente può essere rimossa solo come parte della disattivazione utente. | `400` | `Disattivare l'utente per rimuovere l'associazione.` |

Codici già esistenti che vengono riutilizzati:

- `E_LOCK_COLUMN` (generico, sollevato da `trgfn_lock_columns`) — eventualmente
  arricchito con il context `EMITTENTE_NON_MODIFICABILE` come codice secondario.

### 9.4 Endpoint backend nuovi

| Metodo | Path | Permission | Input | Output (envelope `data`) |
| --- | --- | --- | --- | --- |
| `GET` | `/api/v1/anagrafiche/billing-account/{ba_id}/utilities/?ruolo=CL` | `IsAuthenticated` + `EmittenteFiscaleScopeMixin` su `ba_id` | querystring: `ruolo` (`CL`/`FO`/`GE`) | `{results: [...]}` con stessi campi della funzione SQL `fn_lookup_utilities_per_ba` |
| `GET` | `/api/v1/amm-software/setup-status/` | `IsAdmin` | nessuno | output di `fn_get_setup_status()` (5 contatori jsonb) |

L'endpoint `setup-status` è admin-only. Il banner UI lo chiama solo quando è
visibile un admin.

### 9.5 Composable / props frontend

| Composable / Componente | Path | API |
| --- | --- | --- |
| `useEmittenteCorrente()` | `frontend/src/core/composables/useEmittenteCorrente.js` | Ritorna `{ emittenteId, emittenteCodice, emittenteRagioneSociale, isAdminGlobale }` (reactive). Sorgente: profilo utente al login (`/api/v1/me/profile/`). |
| `useSetupStatus()` | `frontend/src/core/composables/useSetupStatus.js` | Ritorna i 5 contatori da `setup-status`. Cache breve, refetch su mount delle pagine admin. |
| Banner `OperatoriNonAssegnatiBanner.vue` | `frontend/src/amministrazione/components/` | Props: `count: number`. Visibile solo se `count > 0`. |

---

## 10. Check-list operativa (DB / Backend / Frontend)

> Spuntare le caselle man mano che si completano. Funziona sia da tracker
> di stato sia da prova di completamento finale (per spostare il WIP in
> `work-done/`). Le righe sono raggruppate per fase della roadmap (§6).

### Fase 1 — DB foundations (`dev/db-tid`)

> **Stato: COMPLETATA il 2026-04-08.** Tutte le migration scritte come `20260408-11..17` e `-19`,
> tutti i pgTAP verdi (vedi note di implementazione qui sotto).

- [x] **DB-1.1** Verifica preventiva: `SELECT auth_user_id, COUNT(*) FROM config.user_emittenti_fiscali GROUP BY auth_user_id HAVING COUNT(*)>1` — confermato vuoto su DB di sviluppo (precondizione `sqlCheck` aggiunta anche nella migration `-11` per blocco automatico in caso di rigenerazione)
- [x] **DB-1.2** Migration [`00_schema/config/20260408-11-alter-user-emittenti-fiscali-uniq-auth-user-mctit.yaml`](/dbzero/config/tabelle/user_emittenti_fiscali): drop UNIQUE `(auth_user_id, emittente_fiscale_id)`, add UNIQUE `(auth_user_id)`, drop indice ridondante `ix_user_emittenti_fiscali_auth_user_id`
- [x] **DB-1.3** Migration [`20_code/script/20260408-12-create-fn-resolve-emittente-for-user-mctit.yaml`](/dbzero/script/funzioni/fn_resolve_emittente_for_user) — **schema `script` invece di `anagrafiche`** per coerenza col refactor permessi 2026-03-08 (resolver cross-dominio). **Senza filtro `ef.attivo`**: la coerenza è garantita per costruzione dai trigger di guardia esistenti su entrambi i lati (`prevent_deactivate_if_children` e `child_requires_active_parent`); aggiungere il filtro creerebbe incoerenza con `fn_check_user_can_create_ba`.
- [x] **DB-1.4** Migration [`20_code/script/20260408-13-create-fn-check-user-can-create-ba-mctit.yaml`](/dbzero/script/funzioni/fn_check_user_can_create_ba): pure check senza raise
- [x] **DB-1.5** Migration `80_data/sql/config/messaggi_errore.csv` aggiornato con i 3 nuovi codici (§9.3): id 358 `E_BA_ADMIN_GLOBALE_VIETATO`, id 359 `EMITTENTE_NON_MODIFICABILE`, id 360 `E_USER_EMITTENTE_DELETE_VIETATO`. Caricamento via il loader esistente `loadUpdateData runOnChange:true`.
- [x] **DB-1.6** Migration [`20_code/anagrafiche/20260408-14-create-trgfn-billing-account-guard-admin-globale-mctit.yaml`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_admin_globale): trigger `BEFORE INSERT` con drop+create idempotente. Skip fail-open in assenza di GUC `app.current_user_id` (seed/bootstrap).
- [x] **DB-1.7** Migration [`20_code/anagrafiche/20260408-15-create-trgfn-billing-account-link-ef-mctit.yaml`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef): trigger `AFTER INSERT` con idempotenza esplicita (skip se mapping già presente) e fail-open senza GUC.
- [x] **DB-1.8** Migration [`20_code/config/20260408-16-create-trg-user-emittenti-fiscali-lock-emittente-mctit.yaml`](/dbzero/config/tabelle/user_emittenti_fiscali): trigger lock_columns che riusa `script.trgfn_lock_columns`
- [x] **DB-1.9** Migration [`20_code/config/20260408-17-create-trgfn-user-emittenti-fiscali-guard-delete-mctit.yaml`](/dbzero/config/funzioni/trgfn_user_emittenti_fiscali_guard_delete): funzione in schema `config` (la tabella protetta sta in `config`), con override manutenzione via GUC `zeroerp.allow_user_emittente_delete_override`. Fail-open se l'utente Django è già stato cancellato (cessazione implicita).
- [x] **DB-1.10** pgTAP [`db/pgtap/script/test-fn-resolve-emittente-for-user.sql`](/dbzero/script/funzioni/fn_resolve_emittente_for_user): **5 casi** (param NULL/<=0 → throws, utente inesistente → NULL, utente con riga → PK, utente senza riga → NULL). Il caso "EF disattivato" del piano originale è stato rimosso perché il refactor del filtro `ef.attivo` lo rende non rappresentativo.
- [x] **DB-1.11** pgTAP [`db/pgtap/script/test-fn-check-user-can-create-ba.sql`](/dbzero/script/funzioni/fn_check_user_can_create_ba): **4 casi** (NULL/-1 → false, user con riga → true, admin globale + emittenti → false). Il caso "0 emittenti → true" è stato rimosso perché la disattivazione totale degli EF è bloccata dai trigger di guardia esistenti e non si può simulare in modo pulito; la logica è coperta a livello di unit di funzione.
- [x] **DB-1.12** pgTAP [`db/pgtap/anagrafiche/test-billing-account-auto-link-ef.sql`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef): 4 casi (GUC assente → 0 mapping; operatore con EF → mapping specifico verso EF atteso; idempotenza → 1 sola riga; admin globale con emittenti → INSERT bloccata). Strategia "4 BA template distinti uno per test" + skip soft se template/FK indisponibili. **Niente savepoint** (rollbackano lo stato della temp table interna di pgTAP).
- [x] **DB-1.13** pgTAP [`db/pgtap/config/test-user-emittenti-fiscali-immutable.sql`](/dbzero/config/tabelle/user_emittenti_fiscali): **3 casi** (UPDATE su `emittente_fiscale_id` blocca, DELETE su utente attivo blocca, DELETE con override GUC consentita).
- [ ] **DB-1.14** Verifica: rilanciare `dbops.fn_run_automations_attivo` — **non necessario** per il refactor in corso (nessuna nuova FK introdotta, solo trigger su tabelle esistenti). Voce mantenuta per memoria; può essere chiusa o rimossa al merge.

### Fase 2 — Backend (`dev/backend-tid`)

- [ ] **BE-2.0 (PREREQUISITO BLOCCANTE)** Verificare che il GUC `app.current_user_id` impostato dal middleware [`JwtAuditMiddleware`](/it/backend/core/manual/jwt_audit_middleware) **arrivi effettivamente** ai trigger DB del refactor (`trgfn_billing_account_guard_admin_globale`, `trgfn_billing_account_link_ef`). Vedi [§7bis.6](#7bis6-dipendenza-backend--guc-appcurrent_user_id). Test concreto: creare un BA come operatore di emittente via API e verificare che venga creata la riga in `anagrafiche.emittenti_fiscali_billing_account` col mapping specifico atteso. Se il test fallisce (mapping assente nonostante il guard non blocchi), il middleware è inerte in autocommit Django (`SET LOCAL` perso al COMMIT automatico) — va aperta una issue separata per spostare il setting del GUC dentro `transaction.atomic()` o abilitare `ATOMIC_REQUESTS` sulle view che inseriscono BA. **Finché questa verifica non è chiusa, l'intero refactor è strutturalmente in piedi ma operativamente inerte** (i trigger fanno skip fail-open, il sistema continua a funzionare come oggi senza auto-link, fallback al default globale).
- [ ] **BE-2.1** `apps/core/services/permissions_resolver.py` → metodo `get_emittente_for_user(user) -> int|None` con cache (pattern `_cached`)
- [ ] **BE-2.2** Censimento call-site `INSERT INTO anagrafiche.billing_account` lato Python (`grep -rn` in `apps/anagrafiche`): elenco completo da centralizzare
- [ ] **BE-2.3** Nuovo service `BillingAccountCreationService` (o estensione di un service esistente) come unico punto di creazione BA
- [ ] **BE-2.4** Refactor di `clienti_repository.create_billing_account` (e altri eventuali) per delegare al service centralizzato
- [ ] **BE-2.5** Estendere `apps/core/services/error_policies.py` con i 3 nuovi codici errore (mapping HTTP)
- [ ] **BE-2.6** Test mock-based: verifica che il service rifiuti la creazione per admin globale quando esistono emittenti
- [ ] **BE-2.7** Test mock-based: verifica che il service trasmetta correttamente le eccezioni del trigger DB

### Fase 3 — Funzione lookup utility per BA (DB + backend)

- [x] **DB-3.1** Migration [`20_code/anagrafiche/20260408-18-create-fn-lookup-utilities-per-ba-mctit.yaml`](/dbzero/anagrafiche/funzioni/fn_lookup_utilities_per_ba): funzione SQL come §9.1, riusa `fn_get_emittente_fiscale_pk` per la risoluzione emittente (catena specifico → default globale, filtro `ef.attivo`).
- [x] **DB-3.2** pgTAP [`db/pgtap/anagrafiche/test-fn-lookup-utilities-per-ba.sql`](/dbzero/anagrafiche/funzioni/fn_lookup_utilities_per_ba): **5 casi** (NULL → throws, <=0 → throws, ruolo NULL → throws, smoke righe ritornate, coerenza `is_personalizzata_per_ef` con `emittenti_fiscali_utilities`). I casi "BA senza mapping" e "ruolo sconosciuto" sono coperti come effetto delle precondizioni (E_EMITTENTE_DEFAULT_MISSING propagato; ruolo sconosciuto → 0 righe silente).
- [ ] **BE-3.1** `apps/core/db/lookup_repository.py` → metodo `list_utilities_per_billing_account(ba_id, ruolo_codice)` che chiama `fn_lookup_utilities_per_ba`
- [ ] **BE-3.2** Endpoint `GET /api/v1/anagrafiche/billing-account/{id}/utilities/?ruolo=CL` (vedi §9.4) in `apps/anagrafiche/api/views_billing_account.py`
- [ ] **BE-3.3** Permission check con `EmittenteFiscaleScopeMixin` sul BA target
- [ ] **BE-3.4** Test API: utente con scope vede / utente senza scope ottiene 403

### Fase 4 — Frontend

- [ ] **FE-4.1** Endpoint `GET /api/v1/me/profile/` (o equivalente già esistente) deve esporre `emittente_id`, `emittente_codice`, `emittente_ragione_sociale`, `is_admin_globale` (verificare se serve aggiornarlo lato backend)
- [ ] **FE-4.2** Composable `useEmittenteCorrente()` (vedi §9.5)
- [ ] **FE-4.3** Endpoint `GET /api/v1/amm-software/setup-status/` lato backend + composable `useSetupStatus()` lato frontend
- [ ] **FE-4.4** Componente `OperatoriNonAssegnatiBanner.vue` integrato nelle pagine di amministrazione operatori
- [ ] **FE-4.5** `ClienteDrawer.vue` modalità modifica: sostituire `listUtilitiesManual()` con il nuovo endpoint BA-driven
- [ ] **FE-4.6** `ClienteDrawer.vue` modalità creazione: pre-filtrare la combo utility usando l'emittente corrente dell'operatore
- [ ] **FE-4.7** `FornitoreDrawer.vue`: stesso pattern (modifica + creazione)
- [ ] **FE-4.8** `ClientiSearchTable.vue`: filtro utility allineato all'emittente corrente
- [ ] **FE-4.9** UI di creazione BA: disabilitare il bottone "Crea BA" se `isAdminGlobale && esistono_emittenti` (verifica preventiva, oltre al guard DB)
- [ ] **FE-4.10** Build vite OK, smoke test manuale dei drawer modificati

### Fase 5 — Documentazione

- [ ] **DOC-5.1** Aggiornare `docs/it/guide/architettura-permessi-e-autorizzazioni.md` §4.9: nota "1-a-1 dopo refactor 2026-04-XX, ADMIN reinterpretato come scope-locale"
- [ ] **DOC-5.2** Aggiornare `docs/it/guide/architettura-permessi-e-autorizzazioni.md` §13: nota su "ADMIN globale vs ADMIN di emittente"
- [x] **DOC-5.3** Aggiornato [`docs/it/dbzero/config/manual/user_emittenti_fiscali.md`](/dbzero/config/tabelle/user_emittenti_fiscali): nuova semantica 1-a-1, immutabilità, regola "no cambio operatore", riferimenti a resolver e trigger
- [x] **DOC-5.4** Aggiornato [`docs/it/dbzero/anagrafiche/manual/emittenti_fiscali_billing_account.md`](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account): nota "rete di sicurezza", best practice operative aggiornate
- [x] **DOC-5.5** Creati 7 manual per le nuove funzioni/trigger:
  - [`script.fn_resolve_emittente_for_user`](/dbzero/script/funzioni/fn_resolve_emittente_for_user)
  - [`script.fn_check_user_can_create_ba`](/dbzero/script/funzioni/fn_check_user_can_create_ba)
  - [`script.fn_get_setup_status`](/dbzero/script/funzioni/fn_get_setup_status)
  - [`anagrafiche.trgfn_billing_account_guard_admin_globale`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_admin_globale)
  - [`anagrafiche.trgfn_billing_account_link_ef`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef)
  - [`anagrafiche.fn_lookup_utilities_per_ba`](/dbzero/anagrafiche/funzioni/fn_lookup_utilities_per_ba)
  - [`config.trgfn_user_emittenti_fiscali_guard_delete`](/dbzero/config/funzioni/trgfn_user_emittenti_fiscali_guard_delete)
  - Inoltre aggiornata la sezione "Trigger e funzioni coinvolte" di [`anagrafiche.billing_account`](/dbzero/anagrafiche/tabelle/billing_account)
- [ ] **DOC-5.6** Aggiungere voci alla guida `docs/it/guide/risorse-umane-e-accessi.md`: ciclo di vita "trasferimento dipendente fra emittenti" (chiusura + apertura nuovo account)
- [ ] **DOC-5.7** Spostare questo WIP in `docs/it/dev/work-done/refactor-operatore-emittenti.md` con nota "completato YYYY-MM-DD"
- [ ] **DOC-5.8** Aggiornare le memorie progetto rilevanti

### Validazione finale di chiusura sprint

- [ ] **FIN-1** Tutti i test pgTAP del refactor passano
- [ ] **FIN-2** Tutti i test backend del refactor passano (`./manage-test.sh apps.anagrafiche apps.core -v 2`)
- [ ] **FIN-3** Vite build OK
- [ ] **FIN-4** Smoke test manuale: creare BA come operatore, verificare riga in `emittenti_fiscali_billing_account` e combo utility filtrata
- [ ] **FIN-5** Smoke test manuale: tentare di creare BA come admin globale → bloccato con messaggio comprensibile
- [ ] **FIN-6** Smoke test manuale: tentare UPDATE su `user_emittenti_fiscali.emittente_fiscale_id` → bloccato
