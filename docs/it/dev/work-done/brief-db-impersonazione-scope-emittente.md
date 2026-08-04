# Brief BE → DB — impersonazione di scope emittente per SUPER_ADMIN

> ✅ **CHIUSO il 2026-08-04.** Consegnato su entrambi i lati e validato a video
> da Tid al primo accesso reale: il super admin sceglie l'emittente, la
> combo cambia scope, i dati si restringono.
>
> - **DB**: changeSet `20260804-11` … `-16`, pgTAP **10/10**, sei suite di scope
>   preesistenti invariate, un rosso di baseline rientrato (§8.11);
> - **BE/FE**: claim JWT, sesta GUC, endpoint di switch, `/me/`, combo di
>   topbar, dialog della prima scelta, congelamento dell'emittente nei job —
>   suite **3556 verdi** (§9).
>
> **Due code, entrambe dichiarate e nessuna bloccante:**
> ⏳ `storico.user_emittente_attivo` si materializza col job pgagent delle
> 21:00 — la registrazione in `config.storico_set_storicizza` **c'è**
> (verificata: `config.user_emittente_attivo`, `insert_manuale = true`), manca
> solo la gemella. Da ricontrollare a valle della prima esecuzione.
> 🟠 I verbi di creazione non sono spenti area per area in modalità «Tutti gli
> emittenti»: il DB rifiuta con i messaggi riscritti, ma l'utente lo scopre a
> fine compilazione (§9.4). Richiede prima di decidere quali aree esigono
> davvero un emittente — lavoro a sé, non un residuo di questo.
>
> ---
>
> 🟢 **Stato precedente: ACCOLTO — in sviluppo lato DB (2026-08-04).** L'impianto regge: la
> canonica è davvero la sede unica, e le policy RLS non vanno toccate (verifica in
> §8.1). **Cambiano tre cose**: il §4.3 da solo non basta, perché lo scenario che lo
> giustifica è bloccato a monte da un gate che il brief non nomina (§8.3); il §4.2
> introduce un fail-**open** se preso alla lettera (§8.4); e l'emittente attivo
> diventa **persistente** — scelta obbligatoria al login, salvata, modificabile —
> perché anche il super admin abbia un emittente, solo parametrico (§8.2). Il §4.4.2
> decade: il log dello switch esiste già, è la storicizzazione (§8.8).
>
> **Leggere il §8 prima del resto:** §1–§7 sono il testo originale del BE, lasciato
> integro come richiesta in ingresso. **Il §9 è la chiusura del BE** (2026-08-04):
> cosa è stato costruito sopra il vostro impianto, le tre decisioni prese
> strada facendo e le due cose che restano scoperte.

**Chi scrive:** BE (`dev/backend-tid`), 2026-08-03.
**A chi:** team DB (`dev/db-tid`).
**Cos'è:** oggi un SUPER_ADMIN vede *tutti* gli emittenti e non ha modo di
lavorare «dentro» uno di essi. Vogliamo dargli un **emittente attivo di
sessione**, scelto da una combo in topbar, che restringe l'applicazione
esattamente a ciò che vedrebbe un operatore di quell'emittente — liste, RLS in
lettura e write-guard compresi — con una voce «Tutti gli emittenti» per tornare
onnisciente.
**Decisione presa da Tid** (2026-08-03): impersonazione **di scope**, non
semplice «contesto di lavoro». Motivo: la variante debole (default di creazione
sì, liste no) lascia un'asimmetria silenziosa — lavori «su X» ma i parametri
risolvono sul gestore globale e le liste mostrano tutto. È il tipo di
incoerenza che si scopre su una fattura sbagliata.
**Correlati:** [fn_check_user_emittente_scope](/dbzero/script/funzioni/fn_check_user_emittente_scope) ·
[fn_get_emittenti_scope_pk_ids](/dbzero/script/funzioni/fn_get_emittenti_scope_pk_ids) ·
[fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user) ·
guida [architettura-multi-face-auth](/guide/architettura-multi-face-auth)

---

## 1. Com'è oggi

L'associazione operatore ↔ emittente è `config.user_emittenti_fiscali`
(`UNIQUE(auth_user_id)`, modello 1‑a‑1; zero righe = admin globale). Da lì
scendono **quattro** catene distinte:

| # | Catena | Entry point | Comportamento SUPER_ADMIN |
| --- | --- | --- | --- |
| 1 | Filtri lista (BE) | `fn_get_emittenti_scope_pk_ids` / `_sr_ids` | `NULL` = vede tutto |
| 2 | RLS in lettura | `fn_scope_ef_whitelist` (+ `_via_sr`, `_via_fattura`) → **`fn_check_user_emittente_scope`** | `true` = vede tutto |
| 3 | Write-guard | `trgfn_guard_emittente_scope` → **`fn_check_user_emittente_scope`** | `true` = scrive ovunque |
| 4 | Resolver 1‑a‑1 | `fn_resolve_emittente_for_user` | `NULL` (nessuna riga) |

Il lavoro fatto nel 2026‑06‑01 ci aiuta molto: **`fn_check_user_emittente_scope`
è già la sede unica read+write**, e gli adapter RLS le delegano senza duplicare
la regola. Toccandola si propaga a lettura e scrittura insieme.

---

## 2. Il principio, prima delle richieste

> **La selezione è solo restringente, mai allargante.**

Non esiste percorso in cui l'emittente attivo *aggiunga* visibilità a chi non
ce l'ha. Formalmente, per ogni utente `u` ed emittente `e`:

```text
accesso_effettivo(u, e)  =  accesso_attuale(u, e)  AND  (attivo IS NULL OR attivo = e)
```

Ne discende che un operatore che riuscisse a forzare il valore (via client
malevolo, se il BE avesse un buco) non guadagna nulla: al massimo si
auto‑restringe. Questa è la proprietà che rende accettabile mettere il valore
in una GUC di sessione invece che in una tabella di permessi.

---

## 3. Il contratto: la GUC `app.current_emittente_id`

Il BE la propaga come **sesta** GUC di identità, accanto alle cinque già
esistenti (`app.jwt_user`, `app.current_user_id`, `app.current_identita_id`,
`app.ruolo_applicativo`, `app.soggetto_ruolo_id`), con la stessa meccanica:
`set_config(..., false)`, popolata in `set_jwt_gucs()` e **azzerata dal
middleware a fine richiesta** insieme alle altre.

| Valore GUC | Significato |
| --- | --- |
| assente / stringa vuota | Nessuna impersonazione → comportamento **identico a oggi** |
| `<emittente_fiscale_id>` | Emittente attivo: restringe come da §2 |

Convenzione: **PK reale** (`anagrafiche.emittenti_fiscali.id`), coerente con la
canonica `_pk_ids`. La lettura è sempre
`NULLIF(current_setting('app.current_emittente_id', true), '')::bigint` —
la forma già usata da `trgfn_guard_emittente_scope` per `app.current_user_id`.

**Non chiediamo al DB di validare la GUC contro lo scope reale**: per §2 non
serve, e un check aggiuntivo dentro una funzione chiamata dalla RLS costerebbe
su ogni riga. La validazione «l'emittente scelto esiste ed è attivo» la fa il BE
al momento dello switch, una volta.

---

## 4. Cosa chiediamo

### 4.1 🔴 `fn_check_user_emittente_scope` — l'AND restringente

È la canonica read+write: qui la regola entra una volta sola e copre RLS e
trigger. L'ordine dei rami è la parte delicata, perché **il ramo super admin
oggi ritorna `true` prima di qualunque altra cosa**:

```text
1. p_auth_user_id IS NULL            -> true            (job batch, invariato)
2. v_attivo := GUC emittente attivo
   IF v_attivo IS NOT NULL
      AND p_emittente_fiscale_id IS DISTINCT FROM v_attivo
   THEN RETURN false                                     <-- NUOVO, prima del bypass SA
3. fn_is_super_admin                 -> true            (invariato)
4. no identita OPERATORE attiva      -> false           (invariato)
5. whitelist vuota                   -> true            (invariato)
6. EXISTS match whitelist                               (invariato)
```

Il punto 2 **deve** precedere il 3: è tutto il senso della richiesta. Nota che
si applica a chiunque, non solo al super admin — un operatore con la GUC settata
sul proprio emittente passa comunque dal punto 6, e con la GUC su un altro
emittente si auto‑esclude. Coerente con §2.

⚠️ `IS DISTINCT FROM` e non `<>`: `p_emittente_fiscale_id` può arrivare `NULL`
dagli adapter (`_via_sr` con SR non mappato, `_via_fattura` con fattura
inesistente). Con la GUC attiva quel caso deve restare **fail‑closed**.

### 4.2 🔴 `fn_get_emittenti_scope_pk_ids` — l'intersezione

Stessa regola in versione array, applicata **in coda**, dopo i rami esistenti:

| Caso | Ritorno oggi | Ritorno con GUC = `X` |
| --- | --- | --- |
| No identità OPERATORE | `'{}'` | `'{}'` (invariato: la GUC non allarga) |
| Super admin | `NULL` | `'{X}'` |
| Whitelist `{A,B}` | `{A,B}` | `{A,B} ∩ {X}` → `{X}` se X∈{A,B}, altrimenti `'{}'` |
| Whitelist vuota (→ `NULL`) | `NULL` | `'{X}'` |

Cioè: `NULL ∩ {X} = {X}` (NULL = universo), e l'array vuoto resta vuoto.

`fn_get_emittenti_scope_sr_ids` **eredita gratis** — è un wrapper e il
pass‑through dei sentinel continua a funzionare: con la GUC attiva la canonica
non ritorna più `NULL`, quindi il wrapper entra nella mappatura PK → SR, che è
esattamente ciò che vogliamo.

### 4.3 🟠 `fn_resolve_emittente_for_user` — l'emittente «di lavoro»

Se la GUC è valorizzata, **ritornarla**; altrimenti comportamento attuale
(lookup in `user_emittenti_fiscali`).

Serve perché è la fn che decide a quale emittente si aggancia ciò che si crea:
la chiama `trgfn_billing_account_link_ef` per l'auto‑link del BA alla creazione.
Un super admin che crea un cliente mentre impersona X deve produrre un BA di X,
non del gestore globale. Senza questo pezzo l'impersonazione sarebbe di sola
lettura, e sarebbe peggio del non averla: vedi X, ma crei altrove.

⚠️ Questa fn è chiamata anche da contesti senza GUC (job, trigger in batch): lì
il comportamento resta identico a oggi.

### 4.4 🟠 Audit — «e se il super admin impazzisce?»

Due pezzi, entrambi piccoli:

1. **Colonna `emittente_attivo_id bigint NULL` su `dbops.request_log`.** Il
   middleware BE scrive già una riga per ogni `/api/*` con `auth_user_id`,
   `path`, `status_code`: aggiungendo la colonna otteniamo *cosa ha fatto, e in
   che veste*, senza infrastruttura nuova. FK verso `emittenti_fiscali` a vostra
   discrezione (la tabella è un log ad alto volume con `cleanup_at`).
2. **Log del cambio veste.** Serve una riga append‑only per ogni switch: `chi`,
   `quando`, `da → a`, esito. Non c'è una sede naturale — `vendite.event_log` è
   di dominio, `dbops.audit_log` è per esecuzioni di funzioni SQL. Proponiamo
   una tabella dedicata (`config.user_emittente_attivo_log`, append‑only con lo
   stesso trigger `trgfn_*_append_only` di `event_log`), ma **la sede la
   scegliete voi**: se preferite estendere una tabella esistente, per noi è
   indifferente — l'importante è che l'evento esista e non sia cancellabile.

### 4.5 🟢 pgTAP — i casi che vogliamo vedere verdi

Sono la prova che §2 regge. Sul modello dei test di scope già presenti:

| # | Scenario | Atteso |
| --- | --- | --- |
| 1 | Super admin, **nessuna** GUC | `_pk_ids` = `NULL`, `check(...)` = `true` (nessuna regressione) |
| 2 | Super admin, GUC = X | `_pk_ids` = `{X}`, `check(X)` = `true`, `check(Y)` = **`false`** |
| 3 | Operatore whitelist `{A}`, GUC = **B** | `_pk_ids` = `'{}'`, `check(B)` = `false` — **non allarga** |
| 4 | Operatore whitelist `{A}`, GUC = A | invariato rispetto a oggi |
| 5 | `p_auth_user_id NULL` (batch), GUC = X | `true` — i job non si auto‑bloccano |
| 6 | GUC = X, adapter `_via_sr` con SR non mappato | `false` (fail‑closed, §4.1) |
| 7 | `fn_resolve_emittente_for_user`, super admin, GUC = X | `X` |
| 8 | RLS end‑to‑end: super admin con GUC = X su `vendite.fatture` | vede **solo** le fatture di X |

Il caso **3** è quello che non deve mai diventare rosso: è l'invariante di
sicurezza dell'intera feature.

---

## 5. Cosa NON chiediamo

* **Nessuna modifica alle policy RLS.** Gli adapter delegano già alla canonica:
  cambiando §4.1 lettura e scrittura si allineano insieme. Se scoprite un
  percorso RLS che *non* passa dalla canonica, segnalatecelo — sarebbe un buco
  già oggi, indipendente da questo cantiere.
* **Nessuna riga in `config.user_emittenti_fiscali` per il super admin.** Sarebbe
  la scorciatoia economica, ma renderebbe il super admin `scope_mode='SINGLE'`
  agli occhi di `fn_get_user_emittenti_scope` e del drawer operatori: una
  bugia persistente su una tabella di permessi, per uno stato che è di sessione.
* **Nessun cambio a `fn_get_user_emittenti_scope` / `fn_change_user_emittenti_scope`**:
  restano la configurazione *permanente*, ortogonale all'impersonazione.

---

## 6. Cosa fa il BE (nostra metà)

Inerte finché §4 non atterra — la combo cambierebbe senza che i dati si
restringano, quindi non la esponiamo prima.

1. Claim `emittente_attivo_id` nel JWT + endpoint `/auth/switch-emittente/` che
   riemette access+refresh (validando che l'emittente esista, sia attivo e —
   per un non‑super‑admin — sia nel suo scope).
2. GUC in `set_jwt_gucs()` e, **soprattutto**, nella tupla `JWT_IDENTITY_GUCS`
   di [jwt_audit_authentication.py:40](../../../../backend/apps/core/api/jwt_audit_authentication.py#L40):
   il reset di fine richiesta è derivato da quella tupla. Dimenticarla lì
   lascerebbe la GUC appiccicata alla connessione del pool e la **richiesta
   successiva, di un altro utente, erediterebbe l'impersonazione**. È il rischio
   più serio dell'intero cantiere ed è tutto lato nostro.
3. `/me/` espone l'emittente attivo; il FE aggiunge la combo in topbar
   (`AppTopbar.vue`, dove oggi la ragione sociale è testo fisso), la conferma
   preventiva basata su `tabs.hasDirtyTabs()` e il reset delle schede aperte.
4. **Job in background**: la coda lavori gira con `operator_identity_context()`
   e non ha la GUC. L'emittente attivo va **congelato nel payload del job
   all'accodamento** — altrimenti lo stesso lavoro darebbe risultati diversi a
   seconda di quando parte. Nessuna richiesta al DB su questo punto: è nostro.

---

## 7. Definizione di «fatto»

1. §4.1 + §4.2 + §4.3 applicate, con la doc auto‑gen rigenerata.
2. pgTAP §4.5 verdi, **caso 3 compreso**, e baseline aggiornata.
3. §4.4 in piedi (colonna + sede del log dello switch).
4. BE: switch + GUC + reset simmetrico, con test che dimostrano l'azzeramento
   della GUC a fine richiesta.
5. FE: combo + «Tutti gli emittenti» + reset schede.
6. Validazione a video di Tid: impersonare un emittente e verificare che una
   lista fatture mostri solo le sue.

---

## 8. Risposta DB — verifica critica e impianto definitivo

> **Chi scrive:** team DB (`dev/db-tid`), 2026-08-04. Da qui in avanti il documento
> è la risposta, non più la richiesta.

### 8.1 Cosa è stato verificato, e regge

Le affermazioni del brief sono state ricontrollate sul codice vivo (doc auto-generata
delle funzioni, non gli YAML) e sul database.

| Affermazione | Esito |
| --- | --- |
| `fn_check_user_emittente_scope` è la sede unica read+write | ✅ **tutte** le policy RLS con ruolo `OPERATORE` passano dai cinque adapter `fn_scope_ef_whitelist*` (`_via_sr`, `_via_fattura`, `_via_commessa`, `_via_efba`), e tutti e cinque delegano alla canonica. Le altre 18 policy sono `CLIENTE_PORTALE` / `FORNITORE_PORTALE` / `SHOP_CUSTOMER`: non toccate dall'emittente |
| §5 «nessuna modifica alle policy RLS» | ✅ **confermato**, ed è la ragione per cui il cantiere è piccolo |
| Ordine dei rami in §4.1 | ✅ identico alla funzione viva |
| Le cinque GUC e la tupla `JWT_IDENTITY_GUCS` | ✅ e `JWT_GUC_RESET_SQL` è **derivato dalla tupla**: il §6.2 ha ragione, dimenticarla lì è il rischio più serio dell'intero cantiere |
| `UNIQUE(auth_user_id)`, `dbops.request_log` con `cleanup_at` | ✅ |
| Funzioni `STABLE`, non `IMMUTABLE` | ✅ leggere una GUC lì dentro è legittimo |

Nessun percorso RLS aggira la canonica: la richiesta del §5 («segnalatecelo») non ha
riscontri.

### 8.2 Il modello, dopo la decisione di Tid del 2026-08-04

Il brief tratta l'emittente attivo come **stato di sessione**. Tid ha esteso il
modello: lo stato di sessione resta, ma nasce da una **scelta persistita**.

> **Tutti lavorano dentro un emittente.** Per l'operatore è un **permesso** — la riga
> in `config.user_emittenti_fiscali`, fissata nella sua configurazione. Per il super
> admin è una **scelta** — obbligatoria al primo login, salvata, riproposta alle
> sessioni successive, modificabile dalla combo. Stessa semantica, sorgente diversa.

Due conseguenze, entrambe volute:

1. **Il default del super admin si ribalta**: da «vede tutto salvo scelta» a «vede un
   emittente salvo scelta esplicita di vedere tutto». Dashboard, liste cross-emittente
   e ricerche mostreranno un solo emittente finché non seleziona «Tutti gli emittenti».
   È il tipo di cambiamento che il primo giorno viene segnalato come un bug: va detto
   prima. Confermato da Tid.
2. **«Tutti gli emittenti» è una modalità di sola lettura.** Non è una regola nuova:
   `emittente_fiscale_id` è **NOT NULL** su `contratti`, `ddt`, `ordini` e
   `preventivi`, e senza emittente attivo un super admin non ha nulla con cui
   riempirla. Il vincolo esisteva già; quello che manca è **dirlo bene** (§8.6).

**Dove il DB legge il valore: solo dalla GUC.** La tabella è il *default* — cosa
proporre al prossimo login; la GUC è la *verità della richiesta in corso*. Se le
funzioni ripiegassero sulla tabella quando la GUC è assente, ogni job batch e ogni
trigger senza GUC erediterebbe in silenzio l'emittente preferito dell'ultimo super
admin che ha fatto login, e la coda lavori comincerebbe a filtrare da sola. Il §3
scrive «GUC assente = comportamento identico a oggi» e va tenuto alla lettera: una
sola catena, nessuna deriva possibile.

### 8.3 🔴 A — Il caso d'uso del §4.3 è bloccato da un gate non nominato

Il §4.3 si giustifica così: «un super admin che crea un cliente mentre impersona X
deve produrre un BA di X». **Oggi quel super admin non arriva nemmeno al resolver.**

Su `anagrafiche.billing_account` ci sono due trigger, e conta l'ordine delle fasce:

* `trg_billing_account_a10_guard_admin_globale_ins` → `fn_check_user_can_create_ba`
* `trg_billing_account_z90_link_ef_ins` → `fn_resolve_emittente_for_user` ← quello che il §4.3 vuole cambiare

`fn_check_user_can_create_ba` ragiona così: hai una riga in `user_emittenti_fiscali`?
Allora sì. Altrimenti sì **solo se l'istanza non ha alcun emittente attivo**. Il super
admin non ha righe per definizione — lo ribadisce il §5. Verificato sul database di
sviluppo: un super admin, zero righe, due emittenti attivi, e

```text
script.fn_check_user_can_create_ba(super_admin) → false
```

Fascia `a10`: la creazione muore con `E_BA_ADMIN_GLOBALE_VIETATO` prima che `z90`
risolva alcunché. Modificare solo il resolver lascerebbe la feature esattamente nella
condizione che il brief definisce «peggio del non averla».

**La funzione non va indebolita, va completata.** Oggi dice «puoi creare se
appartieni a un emittente»; con l'impersonazione dirà «se appartieni **o** ci stai
dentro» — che è la stessa frase, applicata al modello del §8.2:

```text
1. input invalido                                   -> false   (invariato)
2. emittente attivo valorizzato
   AND fn_check_user_emittente_scope(user, attivo)  -> true    <-- NUOVO
3. riga in user_emittenti_fiscali                   -> true    (invariato: l'operatore)
4. zero emittenti attivi sull'istanza               -> true    (invariato: bootstrap)
5. altrimenti                                       -> false
```

Il ramo 2 passa **dalla canonica**, non legge il valore e basta. Costa un check per
INSERT, non per riga — l'obiezione di costo del §3 non si applica qui — e mantiene
vero il §2: un operatore di A che si ritrovasse la GUC su B non guadagna il diritto di
creare in B.

### 8.4 🔴 B — `fn_get_emittenti_scope_sr_ids` non «eredita gratis»: eredita un fail-open

Il §4.2 dà per scontato che il wrapper erediti la restrizione. Il suo ramo 3 fa:

```sql
SELECT array_agg(ef.soggetto_ruolo_id) INTO v_sr_ids
  FROM anagrafiche.emittenti_fiscali ef WHERE ef.id = ANY(v_pk_ids);
RETURN v_sr_ids;
```

Su zero righe `array_agg` ritorna **NULL**, e NULL per contratto significa «nessuna
restrizione». Verificato: con `ef.id = ANY('{999999}')` il ritorno è `NULL`, cioè
*vede tutto*.

Oggi è irraggiungibile — i PK vengono da `user_emittenti_fiscali`, che ha la FK. Con
l'emittente attivo il PK diventa un numero che arriva da fuori: un id inesistente
(token stale, bug lato BE) farebbe **allargare** invece di restringere, violando il §2,
cioè il principio su cui poggia la decisione di non validare la GUC nel database.

Fix: `RETURN coalesce(v_sr_ids, '{}'::bigint[])`. Una riga, che chiude anche un
difetto latente di oggi. La regola generale: **una funzione di sicurezza non deve
dipendere da una FK altrove per restare fail-closed** — se domani il valore arriva da
un'altra strada, il buco si riapre da solo e in silenzio.

### 8.5 🟠 C — Il §4.2 non è implementabile «in coda»

«Applicata in coda, dopo i rami esistenti» non funziona: i rami esistenti fanno
`RETURN` anticipato, e il super admin esce al ramo 2 con `NULL` senza mai raggiungere
la coda — proprio il caso che deve cambiare. La funzione va ristrutturata a **uscita
unica**: si calcola lo scope come oggi, poi si applica l'intersezione in un solo punto.
Il §4.1 è chirurgico sull'ordine dei rami; il §4.2 deve esserlo altrettanto.

### 8.6 🟠 D — Il resolver ha cinque chiamanti, non uno

Oltre a `trgfn_billing_account_link_ef`, `fn_resolve_emittente_for_user` è chiamata dai
trigger di default emittente di **contratti, ddt, ordini e preventivi**. È una buona
notizia — l'impersonazione si propaga ai documenti, che è ciò che «lavorare dentro X»
significa — ma il raggio è cinque volte quello dichiarato, e il caso 7 del §4.5 prova
la funzione isolata.

Sul pezzo mancante del §8.2.2 — cosa succede in modalità «Tutti gli emittenti» — la
lettura dei quattro trigger ha corretto un'ipotesi sbagliata di questa stessa risposta:
**non serve alcun codice nuovo, e i trigger non si toccano.** Tre dei quattro
sollevano già un errore di dominio quando il resolver torna NULL:

| Trigger | Comportamento con resolver NULL |
| --- | --- |
| `trgfn_ordini_default_emittente` | solleva `E_ORDINE_EMITTENTE_NON_RISOLTO` |
| `trgfn_contratti_default_emittente` | solleva `E_CONTRATTO_EMITTENTE_NON_RISOLTO` |
| `trgfn_preventivi_default_emittente` | solleva `E_PREV_EMITTENTE_NON_RISOLTO` |
| `trgfn_ddt_default_emittente` | **non** solleva, di proposito: lascia NULL e il fallback-da-BA di `trgfn_ddt_normalize` decide |

Con la nuova regola del resolver il comportamento è già quello voluto senza scrivere
una riga: super admin con emittente attivo → il trigger valorizza e passa; in modalità
globale → il trigger solleva il proprio codice. Quello che non va sono le **parole**:
i tre messaggi sono scritti per chi chiama l'API («specificare emittente
esplicitamente nel payload»), mentre da domani il destinatario abituale è un super
admin davanti a una combo. Si riscrivono i tre testi nel CSV — è un mirror
`runOnChange`, nessun changeSet — mantenendo il `%s` finale che i trigger già
passano:

> «Nessun emittente fiscale attivo: seleziona l'emittente in alto per creare il
> documento, oppure indicalo esplicitamente nella richiesta. %s»

<!-- markdownlint-disable-next-line MD028 -->
> ℹ️ **Difetto collaterale trovato e sanato.** Nelle righe 463 e 467 l'escape SQL
> `''` era finito **dentro** il CSV: l'utente leggeva «l''ordine» e «l''emittente».
> Nel CSV l'apostrofo è un carattere normale — corretto contestualmente alla
> riscrittura.

### 8.7 🟠 E — Il resolver, con una regola sola

Il §4.3 dice «se la GUC è valorizzata, ritornarla», senza condizioni. Nel modello del
§8.2 la formulazione giusta è una sola frase che descrive **entrambi** i ruoli:

> emittente attivo **se valido per l'utente**, altrimenti la riga di configurazione.

Il super admin passa dal primo ramo, l'operatore dal secondo. Così l'invariante «mai
allargante» è vera per costruzione e non per convenzione sul fatto che il BE non setti
mai la GUC a un operatore.

### 8.8 🟢 Dove persiste la scelta — e perché il §4.4.2 decade

**Non in `config.user_emittenti_fiscali`.** Il §5 ha ragione, e con un motivo in più di
quello che dà: una riga lì non sarebbe solo «una bugia persistente», sarebbe **mezza
ignorata**. Sia `fn_check_user_emittente_scope` sia `fn_get_emittenti_scope_pk_ids`
escono al ramo super admin *prima* di leggere la whitelist — quindi la riga non
restringerebbe nulla, ma comparirebbe nel drawer operatori come `scope_mode='SINGLE'`.
Il peggio dei due mondi.

Sede: **`config.user_emittente_attivo`** — `auth_user_id` UNIQUE, FK emittente, colonne
di audit — documentata in testa come **preferenza, non permesso**.

**E qui il §4.4.2 decade.** Il brief chiede una tabella di log append-only perché «non
c'è una sede naturale». C'è, ed esiste già: la **storicizzazione**. Basta la colonna
`storicizza` e il framework provvede al resto, dando esattamente ciò che il §4.4.2
elenca:

| Serve | Lo dà |
| --- | --- |
| il valore **da** | `storico.user_emittente_attivo.snapshot` (jsonb) |
| il valore **a** | la riga corrente |
| chi, quando | `user_insert`, `data_insert` |
| non cancellabile | append-only per costruzione, mantenuto dal framework |
| correlazione | `tx_id`, incrociabile con audit ed error log |

Sull'«esito» che il brief chiede: la storicizzazione registra i cambi **riusciti**; i
tentativi **respinti** — qualcuno che prova a impersonare un emittente non suo — sono
già in `request_log` con lo status 403, e con la colonna del §4.4.1 si leggono nello
stesso posto. Copertura completa, zero tabelle inventate.

> ⚠️ **Due trappole nel copiare la tabella gemella.**
>
> 1. `user_emittenti_fiscali` ha un guard che **impedisce di disattivare** un emittente
>    con righe figlie. Non va replicato: la preferenza di un super admin bloccherebbe
>    un'operazione amministrativa. Per una preferenza il comportamento giusto è
>    l'opposto — emittente disattivato, preferenza decaduta, si torna a scegliere.
> 2. Senza registrazione in `config.storico_set_storicizza` il flag `storicizza` viene
>    **azzerato dopo il primo UPDATE**: si registrerebbe il primo switch e nessuno dei
>    successivi. Il registro va popolato esplicitamente nella migration, non lasciato
>    al job settimanale di sincronizzazione.

### 8.9 🟡 F — La colonna su `request_log`, senza FK

Colonna sì, vincolo no. Precedente in casa: `pratiche.reconcile_errori` è
dichiaratamente senza FK perché «log resiliente». `request_log` è ad alto volume con
purge automatica, e una FK verso `emittenti_fiscali` aggiungerebbe un lookup per riga
e bloccherebbe la disattivazione fisica di un emittente.

### 8.10 🟢 pgTAP — gli otto casi del §4.5, più due

I casi 1–8 del brief sono corretti e vanno tutti. Se ne aggiungono due che nascono
dalla verifica:

| # | Scenario | Atteso |
| --- | --- | --- |
| 9 | Emittente attivo = **id inesistente** | `_pk_ids` = `'{}'`, `_sr_ids` = `'{}'`, `check` = `false` — è il test di regressione di §8.4: se diventa rosso qualcuno ha tolto il `coalesce` |
| 10 | Emittente attivo valorizzato + utente **senza identità OPERATORE attiva** | `'{}'` — la GUC non resuscita un utente disabilitato |

Il caso **3** del brief resta quello che non deve mai diventare rosso: è l'invariante
di sicurezza dell'intera feature.

### 8.11 Piano di lavorazione

Tutto applicato sul database di sviluppo il **2026-08-04**, changeSet `20260804-11`
… `20260804-16`.

| # | Passo | changeSet | Stato |
| --- | --- | --- | --- |
| 1 | `config.user_emittente_attivo` + storicizzazione | `20260804-11` | ✅ applicato |
| 2 | Colonna `emittente_attivo_id` su `dbops.request_log` (§8.9) | `20260804-12` | ✅ applicato |
| 3 | `fn_check_user_emittente_scope` — ramo restringente (§4.1) | `20260804-13` | ✅ applicato |
| 4 | `_pk_ids` uscita unica + `_sr_ids` fail-closed (§8.4, §8.5) | `20260804-14` | ✅ applicato |
| 5 | Resolver unificato + `can_create_ba` (§8.3, §8.7) | `20260804-15` | ✅ applicato |
| 6 | Registro `storico_set_storicizza` (§8.8) | `20260804-16` | ✅ applicato |
| 7 | Riscrittura dei tre messaggi `*_EMITTENTE_NON_RISOLTO` (§8.6) | CSV, nessun changeSet | ✅ applicato |
| 8 | pgTAP: dieci casi (§8.10) | `test-emittente-attivo-impersonazione-scope.sql` | ✅ **10/10 verdi** |

**Non-regressione.** Le sei suite di scope preesistenti girano invariate dopo
l'apply: `_pk_ids-and-parity` 6/6, `permessi-fn-check-emittente-scope` 13/13,
`scope-ef-whitelist` 10/10, `permessi-trigger-guard-emittente` 6/6,
`scope-ba-ownership` 6/6, `scope-cliente-ownership` 6/6.

> ℹ️ **Un rosso di baseline rientrato, per necessità.**
> `test-fn-resolve-emittente-for-user.sql` era rosso da aprile con
> `ERRORE_FIXTURE`: selezionava l'utente da `risorse_umane_auth_user.ruolo_sistema`,
> colonna rimossa dal changeSet `20260429-19a`. Falliva nel setup, quindi non
> eseguiva **nessuna** delle cinque asserzioni — copertura zero proprio sulla
> funzione modificata qui. Fixture riportata all'identità digitale `OPERATORE`
> attiva (la stessa degli altri test di scope) e azzeramento esplicito della GUC,
> perché da oggi il resolver la guarda per primo. Ora 5/5, tolto dalla baseline:
> 103 → 102 righe.

<!-- markdownlint-disable-next-line MD028 -->
> ⏳ **Una cosa che matura da sola stanotte.** La gemella
> `storico.user_emittente_attivo` e i trigger di audit/tx_id/storico sulla tabella
> nuova non esistono ancora: le automazioni girano dentro Liquibase solo nel
> contesto `ci_apply`, non sul migrate manuale di sviluppo. Ci pensano i job
> pgagent `automations_storico_provision` / `_storico` / `_audit_update` /
> `_tx_id`, attivi e schedulati **ogni giorno alle 21:00** (ultima esecuzione
> 2026-08-03). Da verificare domani: `SELECT to_regclass('storico.user_emittente_attivo')`
> non deve più essere NULL. Se qualcuno ha fretta, la scorciatoia è lanciare a
> mano `dbops.fn_run_automations_storico_provision`, ma è un'operazione che tocca
> l'intero database e non vale la fretta.

Restano al BE, invariati rispetto al §6: claim JWT, endpoint di switch, GUC **e la
tupla `JWT_IDENTITY_GUCS`**, `/me/`, congelamento dell'emittente nel payload dei job.
Con in più: caricare il default da `config.user_emittente_attivo` al login e imporre la
scelta quando è vuoto.

---

## 9. Chiusura BE — cosa è stato costruito, e cosa resta

> **Chi scrive:** BE (`dev/backend-tid`), 2026-08-04, dopo l'apply del §8.11.
> Suite backend **3556 verdi**, build frontend pulita, primo accesso reale
> validato da Tid.

### 9.1 Verifica indipendente del vostro impianto

Prima di costruirci sopra, le funzioni sono state provate sul DB vivo con la
GUC settata a mano — non lette, eseguite:

| Caso | Misura |
| --- | --- |
| Super admin, nessuna GUC | `_pk_ids` `NULL`, `check` true su tutti, `can_create_ba` **false** |
| Super admin, GUC = 32 | `_pk_ids` `{32}`, `_sr_ids` `{72}`, `check(44)` **false**, `resolve` 32, `can_create_ba` **true** |
| Operatore (whitelist `{32}`), GUC = 44 | `_pk_ids` **`{}`** — non allarga, si auto-restringe |
| Super admin, GUC = id inesistente | `_pk_ids` `{999999}` (zero righe di fatto), `_sr_ids` **`{}`** |

L'invariante del §2 regge, e il `coalesce` del §8.4 fa il suo lavoro. La
modalità globale in sola lettura (§8.2.2) è confermata dal `can_create_ba`
false: non è una convenzione di UI, è il DB.

### 9.2 Le tre decisioni prese strada facendo

**a) L'endpoint di switch riemette i token, non si limita a salvare.**
`POST /api/v1/core/me/emittente-attivo/` valida, persiste in
`config.user_emittente_attivo` e restituisce access+refresh **nuovi** col claim
aggiornato. Salvare soltanto avrebbe avuto effetto al login successivo: la
combo sarebbe cambiata senza che i dati si restringessero — l'interfaccia che
mente, cioè il difetto peggiore di tutti. Il refresh presentato deve
appartenere all'utente autenticato (guard anti-scambio).

**b) La rivalidazione «emittente ancora attivo» vive nella CTE di
`set_jwt_gucs`, a ogni richiesta.** Il §3 stabilisce che il DB non valida la
GUC, e resta così: il controllo è applicativo. La CTE aggiunge un `ef_row` che
popola `app.current_emittente_id` **solo** se l'emittente è ancora
`attivo = true`. Costa un lookup su PK dentro una query che già facevamo, e
chiude il caso «token emesso ieri, emittente disattivato oggi» — che
altrimenti farebbe lavorare l'utente dentro un emittente spento fino alla
scadenza dell'access token. Lo **scope** invece non si rivalida lì: ci pensate
voi a ogni chiamata, e un claim fuori perimetro produce insieme vuoto.

**c) L'emittente attivo è CONGELATO nei lavori accodati.** Il worker esegue
minuti dopo, su un processo senza browser né token: senza congelamento
girerebbe in modalità globale, e un giro chiesto «dentro A» toccherebbe anche
B, in silenzio. L'emittente viene catturato all'enqueue in
`dbops.coda_lavori.scope` (chiave `emittente_attivo_id`, il CHECK
`chk_coda_lavori_run_as_scope` verifica solo la presenza dello scope) e
rimesso come GUC da `operator_identity_context`. Chiave assente sui job
accodati prima del cantiere → `None` → comportamento storico.

> ⚠️ **Effetto collaterale da conoscere.** Poiché `fn_get_emittenti_scope_pk_ids`
> ora interseca con la GUC, `PermissionResolver.get_emittenti_ids` all'enqueue
> restituisce l'emittente attivo invece di `NULL`. Ne consegue che la
> `scope_key` del job — che governa **dedup dei job vivi e ownership del
> polling** — passa da `ALL` a `32` per un super admin dentro un emittente. È
> coerente (due super admin in emittenti diversi non si contendono più i job),
> ma è un cambio di comportamento che non era stato previsto da nessuna delle
> due metà del brief.

### 9.3 Cosa espone il BE al frontend

`/api/v1/core/me/` porta un blocco `emittente_attivo` con quattro campi:
`emittente_fiscale_id` (dal **claim**, non dalla preferenza: dopo un passaggio
a «Tutti» i due divergono), `modalita_globale`, `puo_scegliere` (falso per
l'operatore: il suo emittente è un permesso, non una scelta) e
`deve_scegliere`.

> 💡 **«Non ha mai scelto» e «ha scelto Tutti» sono due stati diversi che dal
> claim si vedono uguali** — assente in entrambi. A distinguerli è la
> preferenza salvata. Senza questa distinzione il dialog bloccante
> ricomparirebbe a ogni caricamento proprio a chi ha appena deciso di vedere
> tutto. Trovato da un test, non a video.

### 9.4 Due cose che restano scoperte

1. 🟠 **I verbi di creazione non sono spenti area per area** in modalità
   globale. Il punto centrale ci sarebbe (`useReadonlyMode`), ma applicarlo lì
   bloccherebbe anche l'amministrazione del software, che di emittente non ha
   bisogno: il super admin non potrebbe più creare utenti o parametri proprio
   mentre guarda tutto. Oggi la topbar avvisa e il **DB rifiuta** con i vostri
   `*_EMITTENTE_NON_RISOLTO`, i cui testi riscritti (§8.6) rimandano alla combo
   — la catena funziona, ma l'utente lo scopre a fine compilazione. Spegnere i
   verbi richiede prima decidere quali aree esigono davvero un emittente.
2. 🟡 **Lo storico degli switch non esiste ancora.** Verificato:
   `SELECT to_regclass('storico.user_emittente_attivo')` → `NULL`. Il job
   pgagent gira alle 21:00 (§8.11), quindi **fino a quel momento i cambi di
   emittente non vengono registrati da nessuna parte** — ed è proprio la
   tracciabilità che ha motivato il §4.4. Da ricontrollare domattina.
