# Analisi — Software vivo che serve dati morti

> **Destinatari:** Tid, backend, team DB
>
> **Tipo:** censimento + piano. Risponde a una domanda sola: *c'è codice,
> configurazione o documentazione che esiste solo per tenere in vita dati —
> o nomi — che il modello ha già lasciato?*
>
> **Stato al 12-09-2026, sera — CHIUSO su tutti i fronti, in attesa di due code.**
> Censimento scritto la mattina; BE e FE chiusi nel pomeriggio (PR #1570); il
> lato DB **applicato su dev** fra le 13:37 e le 14:06 (quattordici changeSet
> `20260912-17…-30`, tutti `EXECUTED`; i tre giri di CI/presidi che hanno
> corretto il tiro sono nel §6.7). Verificato sul catalogo a fine giornata: la
> vista col nome vecchio **non esiste**, nessuna funzione la legge né ne
> fotografa un `%TYPE`, il guard nuovo è montato e quello vecchio no,
> `_defaults_backup_usercols` e `version_info` sono via con la trigger function
> orfana, `vw_riferimenti_morti_da_sanare` è a **zero**.
> 🔴 **Aggiunta della sera (§6.8)**: la baseline su `zeroerp_ci` ha dato cinque
> regressioni con **una** causa — le 15 shadow di storico create a mano in
> `00_schema` restano senza `origine_schema` su un database da zero, perché la
> convergenza gira prima che `ci_apply` crei i trigger. **Non è di oggi**: la CI
> di GitHub è rossa su quattro di quei file a ogni push DB **da #1563 (11-09
> sera)**. Rimedio scritto e provato: `90_end/ci_apply/20260912-31`.
> ✅ Replica ricostruita e baseline su `zeroerp_ci` pulita (Tid, 12-09 sera).
> **Resta**: (1) la consegna **BE** per il codice nuovo
> `E_RISORSA_UMANA_IDENTITA_ATTIVA` (rigenerare le policy + il ripiego, frase
> pronta in §6.7: il cancello dei codici è rosso in CI finché manca); (2) il
> **commit** dei file del pomeriggio/sera, `-31` compreso (Tid); (3) la
> raccomandazione 6.3-bis, cantiere futuro. Chiuse (1) e (2), il documento
> passa in `work-done/`.
>
> Letture di **struttura** (catalogo `pg_class`/`pg_proc`/`pg_trigger`, doc
> auto-gen, grep su BE/FE/pgTAP/seed). ⛔ I conteggi che compaiono sono **fatti
> datati**, mai motivi: la ragione di ogni voce è scritta sul modello.
>
> **Origine:** domanda di Tid del 12-09, dopo la coda del brief
> [brief-db-rls-storico-scope-congelato.md](../work-done/brief-db-rls-storico-scope-congelato.md)
> §10 — dove si stava per scrivere software che mostrasse la storia di una
> tabella ormai morta. Quel caso è **chiuso** (§1) e resta qui come
> precedente: è il calco con cui ho cercato gli altri.

---

## 0. Il criterio — tre forme, e una quarta famiglia

Non ho cercato «cose vecchie»: ho cercato **software in servizio** il cui
unico lavoro è servire ciò che il modello non produce più. Si presenta in tre
forme, e il precedente le aveva **tutte e tre**:

| Forma | Che cosa | Come si riconosce |
| --- | --- | --- |
| **(a) il lettore** | codice che legge una tabella archiviata, rinominata o di dominio ritirato | il nome della tabella in un `FROM`, in una lista Python, in un `%TYPE` |
| **(b) la registrazione** | una riga di catalogo/policy scritta *per* la tabella morta | seed, `storico_scope_policy`, `audit_sources`, `fk_index_policy` |
| **(c) il ripiego** | un ramo `if` che accetta una **forma di dato** che nessuno scrive più | `meta.get("vecchia_chiave")`, `pop("chiave_rimossa")`, purge di chiavi «pre-fix» |

⭐ E c'è una **quarta famiglia**, che non serve dati morti ma **nomi** morti: un
alias «deprecato» con lettori vivi. Non è una transizione se dura da mesi e i
lettori crescono: è un secondo nome in servizio, e la deprecazione è
un'etichetta che sembra proteggere e non protegge — la stessa lezione di
`context: dati_macchina` (AGENTS §80_data).

⚠️ **Il canale con cui il morto rientra è quasi sempre un documento.** Un
manuale che dice «non va cancellata», una copia Python di un catalogo che già
sa la risposta, un commento che cita l'oggetto per nome: chi legge in buona
fede lo trova «ancora da tenere». Per questo il §4 elenca i documenti, non
solo il codice.

---

## 1. Il precedente — chiuso il 12-09-2026

`anagrafiche.risorse_umane_auth_user` era il ponte fra risorsa umana e utente.
Col cutover multi-face (2026-04-19) è diventata una **vista** su
`identita_digitali`; la tabella è stata rinominata
`_legacy_risorse_umane_auth_user` (6 righe, `storicizza = false`) e tenuta
«per la consultazione storica». Attorno a quelle sei righe, in cinque mesi, si
è formato esattamente il fenomeno che questo documento cerca:

| Forma | Dove stava | Che cosa faceva |
| --- | --- | --- |
| (a) lettore | `permissions_audit_repository._USER_TABLES` | la storia dei permessi leggeva `storico.risorse_umane_auth_user` — la shadow della tabella **rinominata**. Droppata il 12-09 alle 00:30 (`20260912-03`), l'endpoint ha risposto **500** |
| (a) lettore, in progetto | consegna BE del §4d | «ripunta su `storico._legacy_…`»: una shadow con **zero versioni**, cioè un audit **vuoto invece di un errore** — la strada che [test-audit-sources-seed.sql](../../../../db/pgtap/dbops/test-audit-sources-seed.sql) aveva già scartato per `audit_sources` |
| (b) registrazione | `dbops.storico_scope_policy` riga 6 | una policy di **perimetro** seminata per un archivio senza scrittori — dentro il brief che stava chiudendo lo scope congelato |
| (b) registrazione | `dbops.audit_sources` riga 5 (`attivo = f`) | la dichiarazione di dismissione, che puntava a una tabella già eliminata |
| documento | manuale `_legacy_risorse_umane_auth_user.md` | «⚠️ Perché non è stata cancellata»: due ragioni, **entrambe scadute** — i pgTAP la citavano solo in commenti, e i changeSet sono storia |

**Com'è stato chiuso** (Tid, 12-09: *«senza produzione è sporcizia»*):

* **BE prima** — PR #1567: `_USER_TABLES` legge **`storico.identita_digitali`**
  (la shadow del ponte **vivo**, che nella timeline dei permessi **mancava**),
  label `risorse_umane_auth_user` ritirato. Non «via la riga», non «ripunta
  alla legacy»: il **successore**;
* **DB dopo** — `20260912-08` (shadow), `-09` (le quattro registrazioni:
  mappa, `audit_sources`, due righe di `storico_set_storicizza`), `-10`
  (madre + le due trigger function orfane), applicati alle 11:30, pgTAP verdi;
  manuali cancellati, non aggiornati.
* ⚠️ **Prima del DROP, la verifica** (12-09, sola lettura): le 6 coppie
  `(risorsa_umana, auth_user)` esistono **tutte** in `identita_digitali` —
  stessa persona, stesso stato — e la shadow aveva **0 versioni**. Non era un
  argomento per tenere: era la prova che il DROP non perdeva nulla.

⭐ **La lezione, in una riga**: il codice serviva il morto **e ignorava il
vivo**. Non è stato un errore di attenzione — è la conseguenza naturale di
lasciare un oggetto con un nome in un posto dove qualcuno lo può trovare.

---

## 2. Censimento — le voci, e com'è finita ciascuna (tutte chiuse il 12-09)

Legenda: 🟡 nome morto con lettori vivi · 🟠 tenuto per prudenza, senza più
nessuno che lo scriva · ℹ️ dato residuo senza lettori.

### 2.1 🟡 A — La vista col nome vecchio: `anagrafiche.risorse_umane_auth_user` (lo «strato 2»)

È l'unica voce grossa, ed è la **seconda metà** del precedente: la segnalazione
del BE del 12-09 la chiamava *strato 2* e la lasciava da decidere.

✅ **Chiusa il 12-09 sera**: vista ritirata (`90_end/20260912-26`), lettori DB
riscritti sulla madre, guard scritto a mano, BE già senza dal pomeriggio. Il
testo che segue è il censimento **com'era** la mattina, e va letto così.

**Che cos'era.** Una proiezione di `identita_digitali` **filtrata** su
`ruolo_applicativo = 'OPERATORE'`, con `risorsa_umana_id` ricavato da un
`LEFT JOIN` «di compatibilità». Read-only, `security_invoker`. Il nome promette
il modello vecchio (ponte RU↔utente) e **non dice né il filtro né la
proiezione**: un lettore che la usa per «l'utente X» ottiene **zero righe** su
un'identità portale/shop — in silenzio, che è il difetto preferito di questo
progetto. Il catalogo BB la dichiara **deprecata** dal 2026-04-19.

**I lettori vivi** (censiti il 12-09 su `pg_proc`, doc auto-gen, grep):

| Strato | Chi | Come |
| --- | --- | --- |
| DB · 4 funzioni | `anagrafiche.fn_notify_cambio_reparto`, `fn_sync_auth_user_expired`, `trgfn_risorse_umane_sync_auth_user_active`, `script.trgfn_guard_emittente_scope` | `FROM`/`JOIN` sulla vista, e in **quattro** il `%TYPE` di `v_auth_user_id` è ancorato alla vista (un `%TYPE` è una fotografia, presa una volta) |
| DB · contratto | `script.fn_get_user_profile` | emette la chiave `risorse_umane_auth_user_id` con dentro **`v_identita_id`**: un nome che mente sul contenuto. Unico lettore: `test_me_view.py` |
| BE · 3 punti + 1 model | `endpoint_helpers.get_risorsa_umana_id` (`SELECT … FROM anagrafiche.risorse_umane_auth_user`), `anagrafiche_repository.list_expired_auth_user_ids` (`JOIN`), `permissions_cache.invalidate_department` via l'ORM `RisorseUmaneAuthUser` (`managed = False`) | 🔴 **`list_expired_auth_user_ids` è una copia Python del solo «ramo legacy»** di `fn_sync_auth_user_expired` — lo dichiara nel commento (*«stessa logica WHERE»*). Conosce il ponte vecchio e **ignora `identita_digitali`**: la cache dei permessi viene invalidata per gli operatori scaduti via risorsa umana, non per le identità portale/shop scadute che la funzione DB invece disattiva. Due livelli, la stessa regola scritta due volte, e la copia conosce metà del modello |
| pgTAP · 9 file | `config/test-fn-cleanup-token-scaduti`, `config/test-user-emittenti-fiscali-immutable`, `anagrafiche/test-risorse-umane-auth-user-view`, `script/test-fn-get-soggetto-dati-and-user-profile`, `anagrafiche/test-fn-crea-operatore`, `anagrafiche/test-fn-crea-risorsa-umana`, `script/test-fn-check-user-can-create-ba`, `script/test-fn-check-operatore-invitabile`, `dbops/test-audit-sources-seed` | fixture e asserzioni che la leggono per nome |

✅ **Il «ramo legacy» di `fn_sync_auth_user_expired` — deciso da Tid il 12-09:
*«tutto deve entrare in `identita_digitali`»*.** La regola «risorsa umana con
`valido_al` scaduto ⇒ utente spento» è assorbita da `identita_digitali.valido_al`;
il ramo cade, e con lui la copia Python `list_expired_auth_user_ids`.
⭐ E la struttura lo diceva già: `fn_sync_auth_user_is_active` (v4) decide
**solo** su `identita_digitali` (`attivo`, `valido_al`, soggetto attivo) — il ramo
legacy poteva **proporre** un candidato, mai cambiare l'esito. Era morto per
costruzione, non per etichetta.

🔴 **Trovato verificando la decisione (12-09 pomeriggio): il `-10` ha lasciato
una mina sulla MADRE.** Su `anagrafiche.risorse_umane` vivevano **due** guard di
automazione «blocca la disattivazione se ha figli attivi», uno per la figlia
droppata e uno per il nome vecchio:

| Trigger su `risorse_umane` | Figlia nominata | Oggi |
| --- | --- | --- |
| `trg_risorse_umane_a10_legacy_risorse_umane_auth_user_blo_feea48` | `_legacy_risorse_umane_auth_user` (**droppata dal `-10`**) | 🔴 su ogni `attivo` true→false cerca in `pg_attribute` la colonna FK di una tabella che non c'è e **solleva `E_ATTIVO_BLOCK_FKCOL_NOT_FOUND`**: da stamattina alle 11:30 **nessuna risorsa umana si può disattivare su dev**. Provato in ROLLBACK. ⇒ `00_schema/anagrafiche/20260912-11` (`DROP TRIGGER IF EXISTS`, forma §11.5; l'automazione ATTIVO genera dalle FK, quindi in CI non nasce e su dev non rinasce) + test 10 del pgTAP `test-legacy-risorse-umane-auth-user-ritirata-v1`. ✅ **Applicato il 12-09 alle 11:54** (`EXECUTED`), baseline pgTAP verde senza regressioni (Tid); verificato sul catalogo: nessun trigger sulla madre nomina più la figlia |
| `trg_risorse_umane_a10_risorse_umane_auth_user_block_deact_upd` | la **vista** `risorse_umane_auth_user` | funzionava (la vista aveva `risorsa_umana_id` e `attivo`) ed era **l'unico** guard che legava RU ↔ identità OPERATORE attiva: `identita_digitali` non ha un guard suo su `soggetti_ruoli`. ✅ **Sostituito** dal guard scritto a mano (`-18`, decisione Tid) e ritirato (`-19`), nell'ordine giusto |

⭐ La lezione, che il `-10` aveva dichiarato a metà: *cancellare una fonte =
censire i lettori* — e un trigger montato sulla **madre** è un lettore della
figlia che vive addosso a un'altra tabella. Un censimento «chi nomina la tabella»
lo trova solo se guarda anche `pg_trigger` dei padri (`pg_get_triggerdef`), non
solo `pg_proc` e le viste.

**Decisione (12-09, delegata da Tid: «a decidere tu»): via il nome.**

Sul modello, non sul costo:

1. **due nomi per una cosa** — `identita_digitali` è la verità, la vista è un
   secondo nome. Un nome scritto in due posti ne ha sempre uno stantio, e
   quello stantio è già qui: il manuale della vista comincia con «Attenzione:
   dal 19-04 è una vista» — un oggetto la cui prima riga avverte del proprio
   nome è un nome che mente;
2. **nasconde un filtro** — `OPERATORE` non sta nel nome; lo zero silenzioso
   sulle altre vesti è la forma in cui il modello vecchio continua a decidere;
3. **propaga il modello vecchio** — quattro `%TYPE` ancorati a una proiezione
   di compatibilità invece che alla madre, una chiave di profilo col nome
   sbagliato, una copia Python che conosce metà delle identità (riga 🔴
   sopra). Non sono lettori «di passaggio»: sono il vecchio modello che si
   rigenera attraverso il nome;
4. **la deprecazione non protegge** — cinque mesi, tre strati, lettori che
   crescono. Un alias con questa vita non è una transizione.

⛔ **Scartato «resta come alias e non si tocca»**: l'unico argomento a favore
è il costo, e il costo non è un argomento sul modello. Se il cantiere trova
che ≥ 2 lettori hanno bisogno della **stessa** proiezione («operatori con la
loro risorsa umana»), la regola del 2 dice di estrarre una vista con un **nome
vero** (`vw_…` che dica filtro e proiezione); ciò che è escluso è **il nome
vecchio**, non il concetto.

**Forma e ordine — cantiere suo, non in coda a un altro brief:**

| Passo | Di chi | Cosa |
| --- | --- | --- |
| 1 | **BE** ✅ **chiuso il 12-09 pomeriggio** — `get_risorsa_umana_id` legge `identita_digitali` (OPERATORE) → `risorse_umane` per `soggetto_ruolo_id`, lo **stesso JOIN** di `fn_get_user_profile` (provato sul DB vero: i due rispondono lo stesso id); `invalidate_department` via `RisorseUmane` → `IdentitaDigitale`; model ritirato; la chiave `risorse_umane_auth_user_id` del profilo **non ha più lettori** (era la sola fixture di `test_me_view`), il DB può toglierla. Presidio: `core/tests/db/test_risorsa_umana_dalla_madre.py` — 3 test su DB provvisto + il **grep a zero** sul sorgente (`anagrafiche.risorse_umane_auth_user` e il nome del model, fuori dai commenti), con registro del debito **in pari** | i tre punti su `identita_digitali` (+ `risorse_umane` dove serve `risorsa_umana_id`); ritiro del model `RisorseUmaneAuthUser`; `list_expired_auth_user_ids` **non** ricopiata sul nuovo modello ma **sostituita** da una chiamata alla stessa `WHERE` del DB (una regola, una sede); la chiave del profilo rinominata o tolta. ✅ **Il terzo punto è chiuso il 12-09 pomeriggio, e nella forma più stretta**: il DB non espone l'elenco dei candidati (la funzione torna un conteggio), quindi invece di aspettare un oggetto nuovo il BE **non conosce più la regola** — `AnagraficheRepository.sync_auth_user_expired` esegue la funzione e ricava gli utenti toccati dall'**effetto** (`auth_user` attivi prima/dopo nella stessa transazione; dry-run = stessa corsa ritirata). ⭐ Gli id sono quelli **davvero** modificati e non i candidati; e il giorno che il ramo legacy cade dal DB (passo 3) il BE non ha niente da cambiare. Presidio: `test_sync_auth_user_expired_repository.py` (3 unit + 1 su DB provvisto) |
| 2 | **DB** ✅ **applicato il 12-09 (13:37–14:06)** | le **quattro** funzioni riscritte sulla madre (`%TYPE` su `identita_digitali`), i pgTAP, `DROP VIEW` in `90_end`, manuale **cancellato**; `vw_riferimenti_morti_da_sanare` a **zero** dopo l'apply. Com'è andata: §6.7 |
| 3 | DB | ✅ il ramo legacy di `fn_sync_auth_user_expired` è **caduto** (`-21`; assorbito da `identita_digitali.valido_al`, con la copia Python); il guard RU ↔ identità attiva **vive sulla madre, scritto a mano** (`-18`, decisione Tid 12-09 sera, §6.2) |
| 0 | DB | ✅ `20260912-11`: via il guard stantio sulla madre `risorse_umane` (§2.1). Applicato il 12-09 alle 11:54, baseline verde |

### 2.2 🟠 B — Ripiego su una forma di `meta` che nessuno scrive più

[approvazioni_prezzo_service.py:712](../../../../backend/apps/vendite/services/approvazioni_prezzo_service.py#L712):
`riga_id = meta.get("riga_id")  # legacy compat sprint E iniziale`. La chiave
viva è `riga_preventivo_id` / `riga_contratto_id` / `riga_offerta_id`
(`_approvazioni_prezzo_constants.py`), e **nessun writer** scrive più
`riga_id` nel `meta` (i `"riga_id"` che si trovano sono chiavi di *risposta*
API, non di `meta`). Fatto datato 12-09: pratiche `APPROVAZIONE_PREZZO` con la
forma vecchia **0 su 3**.

⇒ Il ramo serve una forma che il modello **non produce più**. Se un giorno
servisse, è un backfill di una chiave; oggi è un `if` che tiene «valida» per
sempre una forma abbandonata. **Via il ripiego** (BE, un commit).
✅ **Tolto il 12-09 pomeriggio**; nessun test dipendeva dal ramo.

### 2.3 🟠 C — Difesa da una chiave che non arriva più

[me_view.py:143](../../../../backend/apps/core/api/me_view.py#L143):
`profile.pop("ruolo_sistema", None)`. `script.fn_get_user_profile` **non
emette** `ruolo_sistema` dalla Fase 7 (29-04-2026; lo dice il suo `COMMENT`).
Codice morto per una chiave morta. **Via** (BE, stesso commit di B).
✅ **Tolto il 12-09 pomeriggio — e non era solo.** Nella stessa `get()`, sopra
il `pop`, c'erano **altri due** ripieghi della stessa specie: `if
"is_super_admin" not in profile` e `if "ruolo_applicativo" not in profile`,
dichiarati «difensivi per funzioni DB pre-cutover» — e `fn_get_user_profile`
li emette **sempre** al top-level dal `20260421-03/-05`. Con loro viveva un
**test** (`test_profile_fallback_resolver_se_campi_assenti`) che presidiava
il ramo morto: sostituito dal suo contrario, «la view **trasporta** ciò che il
DB dice, anche quando è no, e non conosce più il resolver». `me_view` non
importa più `PermissionResolver`.

ℹ️ Diverso il caso di `amm_software_service` (righe 190 e 274), che **rifiuta**
`ruolo_sistema` nel payload con `E_AMM_VALIDAZIONE`: quello è un cancello verso
un client vecchio, e un cancello che rifiuta non tiene in vita niente. Resta.

### 2.4 🟠 D — Purge di chiavi «pre-fix» a ogni login (frontend)

[navigation.js:208](../../../../frontend/src/stores/navigation.js#L208):
`purgeLegacyBaseKeys()` cancella dal `localStorage` le chiavi globali di prima
di un fix già consegnato, a **ogni** `syncUserFavorites`/`clearUserState`.
Client-side, piccolo, ma è la forma (c) tale e quale: un meccanismo «difensivo»
che serve dati che il codice non scrive più. ⚠️ Qui il ripiego ha una ragione
che il BE non ha — il dato vecchio vive nel **browser dell'utente**, dove
nessun backfill arriva. Decisione FE: tenerlo con una **data di scadenza**
scritta nel commento, o toglierlo dichiarando che chi ha un browser pre-fix
perde i preferiti globali (che erano il difetto).
✅ **Tolto il 12-09 pomeriggio** — la seconda strada. `loadFavorites` legge
**solo** le chiavi user-scoped, quindi un residuo globale non può essere
letto da nessuno: cancellarlo a ogni login era un gesto senza lettore. Il
progetto non è in produzione e «non tenere per sicurezza» è la regola di
questo documento.

### 2.5 ℹ️ E — Una tabella di backup che nessuno legge

`dbops._defaults_backup_usercols` (73 righe al 12-09, senza `COMMENT`): creata
dal one-shot `20_code/dbops/20251008-01/02` per fotografare i `DEFAULT` di
`user_insert`/`user_update` **prima** di correggerli. **Zero lettori** nel
repo — la nominano solo l'indice auto-gen e un'analisi di copertura doc. Non è
software: è un dato tenuto «per sicurezza» senza nessuno che possa usarlo. La
correzione che doveva proteggere è consolidata da undici mesi.
⇒ **DROP** in un changeSet suo, `00_schema/dbops`, con la riga di
`rollback` che dice che non c'è ritorno (team DB, decisione Tid).
✅ **Deciso da Tid e applicato il 12-09** (`00_schema/dbops/20260912-27`, 13:37).

### 2.6 ℹ️ F — `public.version_info`

Una riga, **zero lettori** in BE/FE/pgTAP; la nomina solo il resync delle
sequence (`90_end/20260818-72`, per escluderla). PROJECT_CONTEXT la dà per
«da verificare se esiste ancora»: esiste. Va deciso se ha un mestiere (allora
un lettore e un manuale) o no (allora `DROP`). Oggi è la seconda.
✅ **Deciso da Tid e applicato il 12-09** — ma in **due** giri, ed è la parte da
ricordare: il primo `DROP` (`00_schema/boostrap/-28`) è passato su dev e **morto
in CI** («bisogna essere proprietari»), perché su un DB da zero la tabella nasce
nel provisioning **pre** come `postgres`; il `DROP` è tornato nel provisioning
(`90_end/-29`, `context: provision`, 13:54) — e ha lasciato **orfana** la trigger
function del suo audit, presa dal presidio riferimenti morti e ritirata dal `-30`
(14:06). Manuale e riga d'indice cancellati. Dettaglio in §6.7.

### 2.7 🟡 G — `PermissionResolver.get_emittenti_ids`, «DEPRECATO» con 9 chiamanti

Il docstring lo dichiara alias deprecato di `get_emittenti_pk_ids`; i chiamanti
vivi sono **nove** (`ai_assistant` ×2, `vendite/api/views` ×2, `core/mixins`,
`core/api/views`, `coda_lavori/gestione_service`, `documenti` ×2) — più
dell'originale. Stessa famiglia di A: un nome deprecato che non cala è un nome
in servizio. ⇒ BE: rinomina meccanica dei nove, poi l'alias **sparisce**; il
presidio è il grep a zero.
✅ **Fatto il 12-09 pomeriggio**: nove chiamanti e ~50 `patch(...)` nei test
rinominati, alias tolto; i quattro test dell'alias sono diventati i test di
`get_emittenti_pk_ids`, che prima **non ne aveva di suoi**. Doc: `api.md`
§Scope emittente, catalogo BB (riga nuova per `_pk_ids`), i manuali
`permissions_resolver`, `emittente_fiscale_scope_mixin`,
`api_documenti_templates` (che nominava anche una `fn_get_emittenti_for_user`
inesistente).

### 2.8 🟡 H — `isAdmin`, alias «legacy» di `isSuperAdmin` (frontend)

[auth.js:436](../../../../frontend/src/stores/auth.js#L436). Il modello
ADMIN/OPERATIVO è morto in Fase 7 e il badge non lo rende più; l'alias tiene
vivo il **vocabolario** vecchio. ⇒ FE: rinomina dei consumatori, via l'alias.
✅ **Fatto il 12-09 pomeriggio**: dieci consumer (route guard, `bersagli`,
preferiti, tre view, due drawer, uno spec) su `isSuperAdmin`, alias tolto,
vitest e build verdi.

---

## 3. Sospetti che si sono rivelati puliti

Vale la pena scriverli, perché la prossima passata non li rifaccia:

* `ruolo_sistema` nel DB compare solo in **commenti** (cinque funzioni) e
  nessun output lo ricostruisce; `fn_get_operatore_detail` ha tolto la colonna;
* `pr_run_lotto_pipeline`, `script.fn_get_emittenti_scope`,
  `fn_get_ruolo_sistema`, le `fn_*` v1 accanto alle `_v2`, i model
  `ProfiloRepartoArea/Azione`: **rimossi davvero** (pg_proc e `config/models.py`);
* `dbops.messaggi_errore_codici_legacy`: **0 righe** — registro in pari, non
  dato morto; i codici ritirati in `error_policies_generated.py` restano per
  leggere `error_log` (scelta dichiarata, api.md);
* `storico.comune_trasformazioni` / `stradario_trasformazioni`: registri delle
  fusioni, non shadow (deciso l'11-09); debito di **nome**, non di dati;
* le chiavi piatte dallo snapshot emittente in `vendite_repository` **non**
  fanno fallback sulle fatture pre-Fase 1 («NULL, niente fallback»): è la
  forma giusta;
* `attivita_fatturabili_log`, `fatturazione_lotti_attivita`: la prima
  sopravvive in un commento, la seconda è stata droppata il 12-09.

---

## 4. Documenti che tengono in vita cose già morte

Sono il canale del §0. Nessuno di questi è codice, e ciascuno può far
riscrivere codice a chi lo legge:

| Dove | Dice | Stato vero |
| --- | --- | --- |
| [api.md §Routing](../api.md#L877) | «le route legacy sono disabilitate di default (`DJANGO_API_LEGACY_ROUTES_ENABLED=0`)» | il flag **non esiste** nel codice: le route legacy sono state rimosse, non spente |
| [api.md §Identità utente](../api.md#L993) | «la mapping legacy ricostruito da `/permessi-effettivi/`: SUPER_ADMIN → ADMIN …» | nessun punto del BE emette `ADMIN`/`OPERATIVO`: la mapping non viene ricostruita |
| [catalogo BB backend](../backend/catalogo-building-block-backend.md#L485) | «`ProfiloRepartoArea/Azione` (kept per lettura legacy)» | i model **non esistono** (`config/models.py:228`: dismessi) |
| [PROJECT_CONTEXT.md](../../../../.codex/PROJECT_CONTEXT.md#L220) | «`pr_run_lotto_pipeline` è deprecata e in fase di rimozione» | **rimossa** (non in `pg_proc`) |
| [PROJECT_CONTEXT.md](../../../../.codex/PROJECT_CONTEXT.md#L105) | «`version_info` … finché non si verifica se l'oggetto esiste ancora» | esiste, una riga, nessun lettore (§2.6) |
| [amm_software_repository.py:1182](../../../../backend/apps/amm_software/db/amm_software_repository.py#L1182) | la regex ammette il `_` iniziale «apposta: la tabella … si chiama `_legacy_risorse_umane_auth_user`» | quella tabella non esiste più dal 12-09; la regex resta giusta, il commento cita un morto |
| manuale `dbzero/anagrafiche/manual/risorse_umane_auth_user.md` — ✅ **cancellato il 12-09 sera**, con la pagina auto-gen, insieme alla vista | «la tabella originale è stata rinominata in `_legacy_…` e archiviata» + una sezione intera sulla tabella legacy | la tabella è **droppata**; il manuale cade con la vista (§2.1) o si riscrive subito |

⚠️ Il manuale della legacy e i due delle trigger function sono già stati
**cancellati** il 12-09, com'è giusto: un oggetto ritirato non ha un manuale da aggiornare.

✅ **Le prime sei righe sono corrette il 12-09 pomeriggio** (la settima, il
manuale della vista, cade con la vista: DB). E cercando i lettori-documento
della vista ne sono usciti **altri**, che questa prima passata non aveva
visto — tutti manuali del backend che davano il nome vecchio come
**dipendenza viva**:

| Dove | Diceva | Fatto |
| --- | --- | --- |
| [permissions_resolver.md](../../backend/core/manual/permissions_resolver.md) | l'intera pagina: catena **in Python** «`ruolo_sistema → override utente → profilo reparto → BLOCCATO`», `get_ruolo_sistema()`, `ProfiloRepartoArea`, `_resolve_*` interni, tabella dipendenze con `profili_reparto_*` | **riscritto** dal codice: ogni metodo delega a una `script.fn_*`, nessuna catena in Python. Era il manuale del BB centrale dei permessi, e raccontava un modello morto da cinque mesi |
| [jwt_audit_middleware.md](../../backend/core/manual/jwt_audit_middleware.md) | «legge `ruolo_sistema` via `get_ruolo_sistema()`» (×3) | `ruolo_applicativo` via `get_ruolo_applicativo()`, GUC-first |
| `api_coda_lavoro.md` · `api_prendi_in_carico.md` · `permissions_cache.md` · `api_user_profile.md` (×3) · `api_invito_operatore.md` (×3, con `ruolo_sistema <> 'DISABILITATO'`) · `api_token_cambio_password.md` · `api_permessi_effettivi.md` · `api_amm_software.md` (×2) | la vista come dipendenza del backend | `identita_digitali` (+ `risorse_umane`), con la nota datata |
| `api_parameters.md` · `api_parameter_settings.md` | «`risorse_umane_auth_user` — bridge utente → emittente fiscale» e «`risorse_umane` contiene `emittente_fiscale_id`» | il repository legge `config.user_emittenti_fiscali`, e `risorse_umane` **non ha** quella colonna: due dipendenze inventate |
| `catalogo-building-block-backend.md` | riga `RisorseUmaneAuthUser` «DEPRECATO … read-only», riga `IdentitaDigitale` «sostituisce … (ora vista in transizione)», riga `get_emittenti_ids` | riga del model **tolta**, le altre due riscritte, riga nuova per `get_emittenti_pk_ids` |
| `catalogo-building-block-frontend.md` (riga `bersagli`) | «`amm-software` si controlla su `isAdmin`» | `isSuperAdmin` |

⚠️ Restano da toccare **con il `DROP VIEW`** (team DB, brief strato 2) le
guide che descrivono la vista come oggetto **esistente** — non sono lettori
del backend, sono la descrizione del database: `architettura-multi-face-auth`
§3.3 e tabella §761, `architettura-permessi-e-autorizzazioni` righe 22/800,
`soggetti-e-ruoli-anagrafici` riga 32, più il manuale
`anagrafiche/manual/risorse_umane_auth_user.md` (da **cancellare**).

---

## 5. Ordine, e di chi

| # | Cosa | Di chi | Dipende da |
| --- | --- | --- | --- |
| 1 | §2.2 + §2.3 — i due ripieghi morti (più i due gemelli trovati accanto), un commit | BE | ✅ 12-09 |
| 2 | §2.7 — rinomina dei nove chiamanti, via l'alias | BE | ✅ 12-09 |
| 3 | §2.1 **strato 2** — cantiere suo: BE prima (tre punti, model, copia Python sostituita dalla chiamata DB, chiave del profilo), poi DB (quattro funzioni + helper + guard, pgTAP, `DROP VIEW`, manuale via) | BE → DB | **BE ✅ 12-09 pomeriggio** · **DB ✅ applicato il 12-09 (13:37–13:59)** — §6.7 |
| 4 | §2.5 + §2.6 — due `DROP` | DB, decisione Tid | ✅ decisi e applicati il 12-09: `-27` (00_schema) e `-29`+`-30` (provisioning: la tabella era di `postgres` in CI, e il suo trigger aveva una funzione) — §6.7 |
| 5 | §2.4 + §2.8 — frontend | FE | ✅ 12-09 |
| 6 | §4 — sette righe di documentazione (diventate ~20: vedi la tabella aggiunta) | chi tocca il file per primo | ✅ 12-09, guide DB comprese (riscritte col `DROP VIEW`) |

⛔ **Cosa NON fare**: non «tenere per sicurezza». Ogni voce di questo elenco è
nata così, e il precedente del §1 mostra dove porta: a un endpoint a 500 e a
una policy di perimetro scritta per sei righe di test.

---

## 6. Lato DB — la consegna dello strato 2 (chiusa la sera del 12-09)

> Scritto il 12-09 pomeriggio, a BE chiuso; **eseguito e applicato la sera**
> (§6.7). Le due domande ⚪ a Tid sono decise: 6.2 → guard sulla madre a mano,
> 6.5 → DROP di entrambi. Da 6.1 a 6.6 resta il **disegno** com'era stato
> consegnato; il §6.7 dice com'è andata. Il precedente è il §10 di
> [brief-db-rls-storico-scope-congelato.md](../work-done/brief-db-rls-storico-scope-congelato.md):
> stessa materia, un piano più sotto.

### 6.1 Perché il `DROP VIEW` ora è sicuro dal lato BE, e cosa può ancora rompere

Il backend non nomina più la vista né il suo model (§2.1, passo 1 ✅) e lo
presidia in CI con il grep a zero di `test_risorsa_umana_dalla_madre`. ⇒ Un
`DROP VIEW` non può più far cadere un endpoint. **Può ancora far cadere oggetti
del database**, e sono questi — letti dal catalogo il 12-09 (`pg_proc`,
`pg_trigger` dei padri, `db/pgtap`):

| Strato | Oggetto | Come |
| --- | --- | --- |
| funzione | `anagrafiche.fn_notify_cambio_reparto` | `FROM`/`JOIN` + `%TYPE` di `v_auth_user_id` ancorato alla vista |
| funzione | `anagrafiche.fn_sync_auth_user_expired` | il **ramo legacy** dell'`UNION` (`risorse_umane` via la vista) + `%TYPE` |
| trigger fn | `anagrafiche.trgfn_risorse_umane_sync_auth_user_active` | `FROM`/`JOIN` + `%TYPE` |
| trigger fn | `script.trgfn_guard_emittente_scope` | `%TYPE` |
| funzione | `script.fn_get_user_profile` | **non la legge** (JOIN già sulla madre) ma **emette** `risorse_umane_auth_user_id` con dentro `v_identita_id`: un nome che mente sul contenuto |
| trigger su `risorse_umane` | `trg_risorse_umane_a10_risorse_umane_auth_user_block_deact_upd` — `dbops.trgfn_prevent_deactivate_if_children('anagrafiche','risorse_umane_auth_user','risorsa_umana_id','id','attivo')` | **l'unico guard** RU ↔ identità OPERATORE attiva. ⚠️ Lettore montato sulla **madre**: la stessa forma della mina del `-11`, invisibile a un censimento su `pg_proc`. Al `DROP` cerca in `pg_attribute` una relazione che non c'è e solleva `E_ATTIVO_BLOCK_FKCOL_NOT_FOUND` a ogni disattivazione di una risorsa umana |
| solo `COMMENT` | `trgfn_identita_digitali_sync_auth_user_active`, `fn_guard_soggetto_pf_pura`, `vw_audit_sources` | prosa da aggiornare, non lettori |
| pgTAP · 9 | `anagrafiche/test-risorse-umane-auth-user-view` (⚠️ in baseline `ERRORE_FIXTURE`), `test-fn-crea-operatore`, `test-fn-crea-risorsa-umana`, `test-legacy-risorse-umane-auth-user-ritirata-v1` (asserisce che la vista **esista**: va girato al contrario), `config/test-fn-cleanup-token-scaduti`, `config/test-user-emittenti-fiscali-immutable`, `script/test-fn-get-soggetto-dati-and-user-profile`, `script/test-fn-check-user-can-create-ba` — ⚠️ `dbops/test-audit-sources-seed` nomina il `code` della sorgente audit ritirata, **non** la vista: resta | fixture e asserzioni per nome |

⛔ Non è un elenco da prendere per completo: dopo l'apply,
`dbops.vw_riferimenti_morti_da_sanare` a zero è la prova.

### 6.2 D1 · Le quattro funzioni sulla madre — e il guard (✅ deciso: sulla madre, a mano)

`%TYPE` di `v_auth_user_id` su `anagrafiche.identita_digitali.auth_user_id`;
`FROM`/`JOIN` su `identita_digitali (ruolo_applicativo = 'OPERATORE') JOIN
risorse_umane ON soggetto_ruolo_id` — la forma che `fn_get_user_profile` usa
già. In `fn_sync_auth_user_expired` **cade il ramo legacy** dell'`UNION`
(deciso, §2.1 ✅): non è una perdita di regola, `fn_sync_auth_user_is_active`
(v4) decide **solo** su `identita_digitali`; il `COMMENT` «copre risorse_umane
legacy + identita_digitali nuove» va riscritto.

⚪ **Il guard `..._block_deact_upd` sparisce con la vista, e la regola che
portava** — *«una risorsa umana con un'identità OPERATORE attiva non si
disattiva»* — è «figli prima del padre» di tutto il progetto
([api.md §Disattivazione record](../api.md)). `identita_digitali` non ha un
guard suo verso `risorse_umane` perché il legame non è una FK: passa da
`soggetti_ruoli`, e l'automazione ATTIVO non lo vede.

⭐ **Raccomandazione: la regola migra sulla madre, scritta a mano.** Guard
`BEFORE UPDATE OF attivo` su `risorse_umane` (forma `_a10_`, §11.5) che
rifiuta `true → false` se esiste un'`identita_digitali` attiva con veste
`OPERATORE` sullo stesso `soggetto_ruolo_id`, con un codice **suo** (non
`E_ATTIVO_BLOCK_CHILDREN_EXIST`, che è dell'automazione e nomina la FK) e la
via d'uscita nella `soluzione` a catalogo: *«disattivare prima l'identità»*.
L'alternativa — nessun guard, la RU si disattiva e
`trgfn_risorse_umane_sync_auth_user_active` spegne l'utente — cambia il modello
(il padre trascina il figlio invece di rifiutare) e non è coerente con le
altre coppie padre/figlio. **È una decisione, e la parola è di Tid.**
✅ **Decisione (Tid, 12-09 sera): la raccomandazione.** Guard
`trgfn_risorse_umane_guard_identita_attiva` + trigger `_a10_…_upd` (`-18`),
codice `E_RISORSA_UMANA_IDENTITA_ATTIVA` (CONFLITTO_STATO), username nel
`VARIADIC`; il guard di automazione ritirato **dopo** (`-19`). Applicati.

### 6.3 D2 · `DROP VIEW`, manuale, guide (✅ fatto: `-26` in `90_end`, manuale e pagina auto-gen via, quattro guide)

- `DROP VIEW anagrafiche.risorse_umane_auth_user` in un changeSet **dopo** D1
  e il guard di 6.2 nella timeline — e dopo ogni changeSet mergiato che la
  pretende esistente (il `-10` ha insegnato a cercarli nelle fasi successive,
  §10.2 del brief precedente).
- **Cancellare** `docs/it/dbzero/anagrafiche/manual/risorse_umane_auth_user.md`
  (la pagina auto-gen `views/` cade al prossimo giro): un oggetto ritirato non
  ha un manuale da aggiornare.
- Le guide che descrivono la vista come **esistente** — non lettori del
  backend, descrizione del database, vanno col `DROP`:
  `guide/architettura-multi-face-auth.md` §3.3 e la riga «Vista compat» della
  tabella finale, `guide/architettura-permessi-e-autorizzazioni.md` (righe 22
  e 800), `guide/soggetti-e-ruoli-anagrafici.md` (riga 32),
  `guide/risorse-umane-e-accessi.md` (righe 21-31). I tre `COMMENT` di 6.1.
- ⛔ **Non nasce una vista sostitutiva** per simmetria: regola del 2 — se in
  riscrittura due lettori chiedono la **stessa** proiezione, una `vw_` con un
  **nome vero** (che dica filtro e proiezione) è legittima; escluso è il nome
  vecchio, non il concetto.

### 6.3-bis ⭐ La catena «utente → risorsa umana» vive in TRE sedi: una sola

Riscrivendo il BE sulla madre è uscito un fatto di struttura: la catena
`identita_digitali (OPERATORE, attiva) → risorse_umane (attiva) per
soggetto_ruolo_id` è scritta in `script.fn_get_uo_id_for_user`, in
`script.fn_get_user_profile` (senza i filtri `attivo`) e ora — allineata alla
prima — in `endpoint_helpers.get_risorsa_umana_id`. Tre copie della stessa
regola su due livelli, che è ciò che il §0 chiama forma (a) *in fieri*.

⇒ **Raccomandazione (regola del 2, attraverso i livelli):** una
`script.fn_get_risorsa_umana_id_for_user(p_auth_user_id)` gemella di
`fn_get_uo_id_for_user` — stessa forma, `STABLE`, stessi filtri — e le due
funzioni che si appoggiano a **un** helper interno; il BE diventa un wrapper
di una riga, come `get_unita_organizzativa_id`. Non è un prerequisito del
`DROP VIEW`: il BE oggi lega e la copia è dichiarata nel commento dell'helper.

### 6.4 D3 · `fn_get_user_profile`: la chiave che mente

`risorse_umane_auth_user_id` nel blocco `risorse_umane` porta `v_identita_id`.
**Nessun lettore** BE/FE (era la sola fixture di `test_me_view`, corretta).
⇒ **Togliere la chiave**, non rinominarla. ✅ Fatto (`-24`).
⚠️ La motivazione originale diceva *«l'id dell'identità il profilo lo espone già
nel blocco `identita`»*: verificato il 12-09 sera, **quel blocco non esiste**
(chiavi top-level: `utente`, `soggetto`, `risorse_umane`, `emittente`,
`permessi_*`, …). La decisione non cambia — un dato senza lettori non si tiene
sotto un nome che mente — ma se un giorno servirà, si espone col suo nome
(`identita_id`), non si resuscita questo.

### 6.5 D4 · I due `DROP` del §2.5 e §2.6 (✅ decisi da Tid: entrambi)

| | Oggetto | Raccomandazione |
| --- | --- | --- |
| §2.5 | `dbops._defaults_backup_usercols` | `DROP TABLE` in `00_schema/dbops`, con la riga di `rollback` che dice che non c'è ritorno. Non è software: è un dato «per sicurezza» che nessuno può usare |
| §2.6 | `public.version_info` | o un mestiere (un lettore + un manuale) o `DROP`. Oggi è la seconda |

⛔ Entrambi «tenuti per sicurezza», la forma da cui ogni voce di questo
documento è nata. Ma sono `DROP` di tabelle: **la parola è di Tid.**
✅ **Decisione (Tid, 12-09 sera): DROP entrambi.** `-27` per il backup;
`version_info` ha chiesto due giri (§2.6, §6.7).

### 6.6 Presidi

| | Dove | Prova | Il suo contrario |
| --- | --- | --- | --- |
| **P-1** ✅ | `test-legacy-risorse-umane-auth-user-ritirata-v1` (12) | la vista **non** esiste (test 7, rovesciato); nessuna funzione la legge né ne fotografa un `%TYPE` (11 — la mattina ne elencava quattro); nessun trigger su `risorse_umane` la nomina (12). `vw_riferimenti_morti_da_sanare` a zero: verificato sul catalogo dopo l'apply | — |
| **P-2** ✅ | `test-risorse-umane-guard-identita-attiva-v1` (8) — l'operatore lo **costruisce** con `fn_crea_operatore_v2` | RU con identità OPERATORE attiva ⇒ `attivo = false` **rifiutato**, codice nel canale `CONSTRAINT`, username nella frase | identità spenta prima ⇒ passa, e il sync `z90` dalla madre spegne l'utente |
| **P-3** ✅ | `test-fn-get-soggetto-dati-and-user-profile` (26) | il blocco `risorse_umane` **non** contiene `risorse_umane_auth_user_id` | ~~`identita.id` c'è~~ — quel blocco non esiste (§6.4); resta `risorsa_umana_id` |
| BE | `core/tests/db/test_risorsa_umana_dalla_madre` (in CI) | resta verde: il backend non torna a nominarla | — |

⛔ **Cosa non si fa**: tenere la vista «come alias, tanto non costa» (l'unico
argomento è il costo, §2.1); riscrivere il ramo legacy sulla madre (cade);
il `DROP VIEW` **prima** del guard di 6.2 (ogni disattivazione di una RU
fallirebbe, come il `-10` la mattina del 12-09); i due `DROP` di 6.5 senza
l'ok di Tid.

| | |
| --- | --- |
| BE | ✅ chiuso il 12-09 pomeriggio: nessun lettore, presidio in CI |
| DB | ✅ **applicato su dev il 12-09** (13:37 → 14:06): 6.2 · 6.3 · 6.4 · 6.5 · P-1/P-2/P-3. ⭐ 6.3-bis resta raccomandazione |
| Tid | ✅ decisioni 6.2 e 6.5 · ✅ apply, migrate rilanciato dopo i due giri di CI · ⏳ **commit** dei file |
| BE | ⏳ **una consegna nuova**: `./manage-env.sh genera_error_policies` (il codice `E_RISORSA_UMANA_IDENTITA_ATTIVA` entra in `error_policies_generated.py`) + la frase senza segnaposto in `error_messages_fallback.py` — presidi `test_nessun_codice_nuovo_senza_policy` e `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`, **rossi in CI finché manca** |

### 6.7 Com'è andata — quattordici changeSet, applicati il 12-09 fra le 13:37 e le 14:06

> Decisioni di Tid (12-09 sera, su domanda): **guard sulla madre, scritto a
> mano**; **DROP di entrambi** gli oggetti del §6.5. Tutto scritto e provato con
> l'SQL estratto dagli YAML in una transazione annullata, poi **applicato da Tid**
> su dev. ⚠️ Non al primo colpo: la CI locale (`--fresh`) e il presidio dei
> riferimenti morti hanno fermato il giro **tre volte**, e ogni fermata ha
> lasciato una regola scritta (in questa tabella, e nelle schede di memoria):
> il `%TYPE` non si mette mai su una colonna `django.*`; ciò che nasce nel
> provisioning si ritira nel provisioning; un `DROP TABLE` non porta via la
> trigger function del proprio trigger. Stato finale letto dal
> `databasechangelog`: `-17…-27`, `-29`, `-30` `EXECUTED`; `-18` e `-24` `RERAN`
> (corretti dopo il primo giro di CI e rieseguiti su dev cancellandone la riga:
> erano solo locali); `-28` `EXECUTED` su dev e poi **cancellato** dal repo
> (mai committato), la sua riga resta e non disturba.

| ChangeSet | Cosa | Perché lì |
| --- | --- | --- |
| `20_code/script/20260912-17` | `script.fn_get_auth_user_id_for_risorsa_umana` — la catena RU → utente dalla madre, **una sede** (regola del 2: due lettori). `%TYPE` in firma e `RETURNS` | prima di chi la usa |
| `20_code/anagrafiche/20260912-18` | 🔴 **morto in CI al primo giro** (12-09 sera): `v_username django.auth_user.username%TYPE` — in CI Liquibase gira **prima** delle migrazioni Django, lo schema `django` non esiste al `CREATE`, e un `%TYPE` si risolve proprio lì. Stessa svista in **firma** nel `-24` (`p_auth_user_id django.auth_user.id%TYPE`, messo ri-ancorando le firme). ⇒ tipi **espliciti** (`text`, `integer`) con la ragione accanto: *il DB può chiamare dentro `django.*`, non dipenderne* — la regola dei `%TYPE` in firma e DECLARE ha questa eccezione, e ora è scritta in entrambe le schede. Provato: una plpgsql che nomina una relazione inesistente si crea (late binding), i due corpi compilano. Il guard di 6.2: `trgfn_risorse_umane_guard_identita_attiva` + trigger `_a10_…_upd` su `attivo`, codice **`E_RISORSA_UMANA_IDENTITA_ATTIVA`** (CONFLITTO_STATO, seed nei due CSV, id 1062), username nel `VARIADIC`, `campo = attivo` | **prima** del ritiro del guard vecchio: nessuna finestra senza regola |
| `00_schema/anagrafiche/20260912-19` | via il guard di automazione che leggeva la vista (`DROP TRIGGER IF EXISTS`, §11.5) | dopo il `-18` |
| `20_code/anagrafiche/-20`, `-21`, `-22` · `20_code/script/-23` | le quattro funzioni sulla madre: `fn_notify_cambio_reparto` e `trgfn_risorse_umane_sync_auth_user_active` via l'helper; `fn_sync_auth_user_expired` **senza il ramo legacy** (deciso); `trgfn_guard_emittente_scope` il solo `%TYPE` | corpi da `pg_get_functiondef` vivo, **firme ri-ancorate** (`%TYPE` su parametri, `RETURNS`, `COMMENT`) — la riproduzione del vivo le scioglie |
| `20_code/script/-24` | `fn_get_user_profile` senza `risorse_umane_auth_user_id` | ⚠️ il §6.4 diceva «già esposto nel blocco `identita`»: quel blocco **non esiste**. Decisione invariata (nessun lettore), motivazione corretta nel changeSet |
| `20_code/script/-25` | i tre `COMMENT` che davano la vista per esistente | solo prosa |
| **`90_end/20260912-26`** | **`DROP VIEW anagrafiche.risorse_umane_auth_user`** | ⛔ in `90_end` e non in `00_schema`: `80_data/20260309-01` (seed di macchina mergiato) ha una `sqlCheck` sulla vista — su un DB da zero, con la vista già droppata, `onError` = HALT. La lezione del `-10`, di nuovo |
| `00_schema/dbops/-27` · **`90_end/-29` (`context: provision`)** | `DROP TABLE` di `_defaults_backup_usercols` e `public.version_info` | forward-only, `IF EXISTS`. 🔴 Il primo tentativo su `version_info` (`00_schema/boostrap/-28`, mai committato) è **morto in CI**: la tabella nasce nel provisioning **pre** come `postgres` e il migratore `zeroerp` non può droppare ciò che non possiede (su dev era passato: stesso utente per bootstrap e migrazioni). ⇒ *Ciò che nasce nel provisioning si ritira nel provisioning*: il `-29` è incluso in `changelog-provision-post.yaml` e gira come `postgres`; nella passata principale è invisibile. Su dev resta la riga del `-28` in `databasechangelog`, innocua. 🔴 **E il `-29` ha lasciato un'orfana**, trovata dal presidio `dbops/test-riferimenti-morti-v1` (test 3) al primo giro: `internal.trgfn_audit_version_info()`, la trigger function dell'audit di `version_info` — il `DROP TABLE` porta via il trigger, non la sua funzione (la lezione del `-10`, un piano più sotto). Nasceva da un bootstrap ormai `.old_yaml`: in CI non esiste, su dev è un residuo. ⇒ **`90_end/-30`** (provisioning, `IF EXISTS`), provato: presidio a zero. Via anche il manuale `public/manual/version_info.md` |

**Provato in ROLLBACK** (12-09 sera): una sola funzione per nome dopo il
`CREATE OR REPLACE` (`pg_get_function_identity_arguments`: nessun overload);
`plpgsql_check` a **zero** su cinque funzioni a vista droppata (le 10 righe di
`fn_get_user_profile` sono avvisi STABLE/VOLATILE **preesistenti**); il guard
rifiuta con `CONSTRAINT = E_RISORSA_UMANA_IDENTITA_ATTIVA` e la frase *«l'utente
tid ha ancora un'identità operatore attiva»*; un operatore costruito con
`fn_crea_operatore_v2` viene rifiutato a identità attiva e **passa** dopo averla
spenta, e il sync `z90` dalla madre mette `is_active = false`; l'helper,
`fn_sync_auth_user_expired()`, `fn_notify_cambio_reparto` chiamate; il profilo
senza la chiave; vista, backup, `version_info`, guard vecchio **assenti**, guard
nuovo **presente**. Cinque cancelli CI verdi.

**pgTAP** (li lancia Tid): **nuovo** `anagrafiche/test-risorse-umane-guard-identita-attiva-v1`
(8, P-2 — costruisce l'operatore con la madre, non lo cerca);
`anagrafiche/test-legacy-risorse-umane-auth-user-ritirata-v1` a **12** (P-1: il
test 7 **rovesciato** in `hasnt_view`; 11 = nessuna funzione **legge** il nome
vecchio né lo fotografa in un `%TYPE` — oggi ne elenca quattro, dopo nessuna;
12 = nessun trigger su `risorse_umane` lo nomina);
`script/test-fn-get-soggetto-dati-and-user-profile` a 26 (P-3 + fixture sulla
madre); fixture riscritte sulla madre in `config/test-fn-cleanup-token-scaduti`,
`config/test-user-emittenti-fiscali-immutable`, `script/test-fn-check-user-can-create-ba`;
**cancellato** `anagrafiche/test-risorse-umane-auth-user-view` (era in baseline
`ERRORE_FIXTURE` su dev e CI: tolto dalle due baseline).
⚠️ **Non toccati, e sono un debito a parte**: `anagrafiche/test-fn-crea-operatore`
e `test-fn-crea-risorsa-umana` chiamavano `fn_crea_operatore` / `fn_crea_risorsa_umana`
**v1**, con `p_ruolo_sistema config.ruolo_sistema` — funzioni ed enum **rimossi**
in Fase 7. Erano in baseline `ERRORE_FIXTURE` da allora: due test che pinnavano
codice morto (forma (a) del §0, applicata a un test). ✅ **Riscritti sulla v2 la
sera del 12-09** (decisione Tid): vedi «Resta» qui sotto.

**Documenti**: manuali nuovi `script/manual/fn_get_auth_user_id_for_risorsa_umana`,
`anagrafiche/manual/trgfn_risorse_umane_guard_identita_attiva`; aggiornati i
manuali delle quattro funzioni riscritte; **cancellati** manuale e pagina
auto-gen della vista; le quattro guide del §6.3 riscritte nel punto in cui
davano la vista per esistente (`risorse-umane-e-accessi` con la nota di lettura
in testa, `architettura-multi-face-auth` §3 e §3.3, `architettura-permessi-e-autorizzazioni`,
`soggetti-e-ruoli-anagrafici`).

**Resta**:

| | Cosa | Di chi |
| --- | --- | --- |
| ✅ | apply dei changeSet (il mirror dei codici errore ha riletto i CSV: il codice è a catalogo) — `vw_riferimenti_morti_da_sanare` a **zero** dopo il `-30`; baseline pgTAP verde salvo la regressione del presidio riferimenti morti, sanata dal `-30` | fatto (Tid, 12-09) |
| ⏳ | **commit** dei file del pomeriggio/sera: 14 changeSet, 2 CSV, 2 righe in `changelog-provision-post.yaml`, 9 pgTAP (+1 cancellato, 2 baseline), manuali, guide, questo documento | **Tid** |
| ⏳ | **BE**: `./manage-env.sh genera_error_policies` (il codice nuovo entra in `error_policies_generated.py`, classe `CONFLITTO_STATO` → 409) + la frase senza segnaposto in `error_messages_fallback.py` — presidi `test_nessun_codice_nuovo_senza_policy` e `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`, rossi finché manca. ⭐ **La frase, così non c'è niente da decidere** (il catalogo dice *«Non si puo' disattivare la risorsa umana: l'utente %s ha ancora un'identita' operatore attiva.»*): `"E_RISORSA_UMANA_IDENTITA_ATTIVA": "Non si puo' disattivare la risorsa umana: l'utente ha ancora un'identita' operatore attiva."` — apostrofi **non** raddoppiati (è Python), in ordine alfabetico fra `E_RISORSA_UMANA_*`. Nessun override di `ui_action`: il default della classe è il banner, e qui non c'è un campo del form da accendere — la cosa da cambiare è un'**altra** riga (l'identità) | **BE** |
| ✅ | i due test v1 morti: **riscritti sulla v2** (decisione Tid, 12-09 sera) — `test-fn-crea-operatore` (12) e `test-fn-crea-risorsa-umana` (9) su `fn_crea_operatore_v2` / `fn_crea_risorsa_umana_v2`, catene su `identita_digitali`, codici letti dal canale `CONSTRAINT` dove il testo non li porta più; fixture e frasi provate in ROLLBACK; tolti dalle due baseline. ⚠️ Entrambi (e il test del guard) portano l'esenzione `pgtap-differiti: escluso`: la madre passa da `fn_crea_soggetto_pf`, che per contratto crea un soggetto senza indirizzo — con `IMMEDIATE` fallirebbe all'INSERT. È il debito §22.4 già dichiarato dal test RU, non uno nuovo | fatto |
| ⭐ | 6.3-bis (`fn_get_risorsa_umana_id_for_user`, tre copie della catena utente → RU) | raccomandazione, cantiere futuro |

### 6.8 🔴 La baseline su `zeroerp_ci` — cinque rossi, una causa, e non è di oggi (12-09 sera)

> Tid, 12-09 sera, dopo la baseline sulla replica locale
> (`PGTAP_ENV_FILE=db/internal.ci.env`): **cinque regressioni** — il mio
> `anagrafiche/test-risorse-umane-guard-identita-attiva-v1` (`ERRORE_FIXTURE`) più
> `config/test-parameter-overrides-fk-surrogate-dispatch-v1`,
> `dbops/test-trgfn-prevent-deactivate-if-children-pdp`, `dbops/test-vw-processi-roster`
> e `storico/test-storico-scope-congelato-v1`. «Sulla CI è tutto ok» valeva per i
> push **BE**, dove i pgTAP non girano: la corsa di GitHub del merge di **#1569**
> (`dev/db-tid` → Tito-dev, 10:57) è `failure`, e con lei **ogni push DB da #1563**
> — il merge dello scope congelato dello storico, l'11-09 sera. Quattro file rossi
> a ogni build da un giorno, e nessuno li ha letti perché non erano in
> `baseline-rossi-ci.tsv`: regressioni, non rossi noti.

**Una causa sola, letta riproducendo i file su `zeroerp_ci` in transazione
annullata**: `E_SNAPSHOT_CLOSE_ERROR — la colonna "origine_schema" non esiste
(42703)`, sollevato dal trigger di storico (`-28` dell'11-09) su un `UPDATE` di
`identita_digitali` (il mio test 6 e il roster, test 5), di `parameter_overrides`
(test 6) e su un `DELETE` da `pdp` (la pulizia del test). Il presidio dello storico lo **contava**: test 2 *«ogni shadow di una
madre col trigger ha le due colonne» — have: 15, want: 0*.

**Il meccanismo, su un database da zero** (sul modello: chi garantisce l'invariante
«shadow di una madre col trigger ⇒ armata»):

| Garante | Cosa fa | Dove si rompe in CI |
| --- | --- | --- |
| la **nascita** — `fn_ensure_storico_table` (`20260911-34`) | crea la shadow **e la arma** | ⛔ **esce subito se la shadow esiste già** |
| la **convergenza** — `fn_storico_arma_scope_tutte` (`00_schema/-27` una volta, `90_end/-29` `runAlways`) | arma le shadow delle madri **che hanno il trigger** `trgfn_storico_generic` | ⛔ in CI il trigger lo genera `ci_apply`, cioè **dopo**; e dentro la passata `ci_apply` il `-29` gira comunque **prima** di `ci_apply/` (l'`includeAll` ordina per percorso: `90_end/2026…` < `90_end/ci_apply/`). Letto dal `databasechangelog` di `zeroerp_ci`: `-29` RERAN a `orderexecuted` 5603, automazioni a 5604 |

⇒ Le 102 shadow che nascono **durante** le automazioni sono armate alla nascita.
Le **15 che esistono già** — create a mano in `00_schema`: le `20260418-*` del
multi-face (`identita_digitali`, `identita_scope_bindings`, `profili_accesso*`,
`scope_policy`), `pdp`, `catasto_unita_immobiliari`, `comuni`, `dati_societari`,
`indirizzi*`, `parameters`, `parameter_overrides` — nessun passo le raggiunge.
`iva_natura` (`20260829-38`) non è fra loro perché quel changeSet chiama **anche**
`fn_run_automations_storico` in-pass, e al `-27` il trigger c'è. Su dev non si
vede: i trigger ci sono da mesi e il `-29` arma al primo migrate — è la forma esatta
del «verde su dev non dice niente sulla CI».

**Il rimedio — `90_end/ci_apply/20260912-31-run-storico-arma-scope-dopo-automazioni`**:
la stessa chiamata del `-29`, `runAlways` + `context: ci_apply`, in coda alla
passata che crea i trigger (il nome del file la colloca dopo `20250627-31` e
`20260205-41`). Zero DDL dove è già tutto a posto; su un database da zero
`fn_storico_arma_scope` mette `origine_schema NOT NULL` da subito (shadow vuota),
quindi non serve backfill. ⛔ Scartati: toccare `20250627-31` (mergiato, e col
`validCheckSum` al **singolare** che Liquibase ignora — un byte cambiato lo ferma
su dev); rinominare il `-29` per farlo scivolare dopo `ci_apply/` (un changeSet
mergiato non si rinomina, e nella passata principale deve girare dov'è); insegnare
a `ensure` ad armare anche l'esistente (il `-34` ha deciso «arma chi crea», e la
convergenza esiste apposta — il difetto è il suo **momento**, non il suo perimetro).

**Provato su `zeroerp_ci` (12-09 sera), SQL estratto dallo YAML, transazione
annullata**: shadow con madre col trigger e senza `origine_schema` **15 → 0**;
`storico.identita_digitali.origine_schema` `NOT NULL`; i due file che girano come
owner concatenati dopo l'SQL: `test-vw-processi-roster` **7/7**,
`test-storico-scope-congelato-v1` **23/23**; i tre file «app» rigiocati come
`zeroerp` (il migratore non è membro di `zeroerp_app`, e il 42703 non dipende dal
ruolo): guard **8/8**, fk-surrogate **7/7**, pdp **13/13**. Cinque guardrail
statici verdi.

**Resta, e va nell'ordine giusto**:

| | Cosa | Di chi |
| --- | --- | --- |
| ✅ | ricostruita la replica (`scripts/ci-local.sh --fresh --ci-apply`) e rilanciata la baseline su `zeroerp_ci`: i cinque sono usciti dalle regressioni, `baseline-rossi-ci.tsv` intatta (Tid, 12-09 sera: «andata») | fatto |
| ⏳ | commit: il `-31` entra nel tree di oggi (61 file) | **Tid** |
| ⚠️ | il verdetto vero lo dà la corsa di GitHub sul push DB verso Tito-dev — la prima verde da #1563 | CI |

---

*Analisi 12-09-2026 — letture di struttura sul database `zeroerp` (catalogo,
doc auto-gen) e sul repo (grep BE/FE/pgTAP/seed). I numeri sono fatti datati.
Il precedente del §1 è chiuso; BE e FE chiusi il 12-09 pomeriggio; il lato DB
(§6) applicato su dev la sera del 12-09. Restano la consegna BE per il codice
nuovo e il commit: poi in `work-done/`.*
