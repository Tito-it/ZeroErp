# Analisi — Software vivo che serve dati morti

> **Destinatari:** Tid, backend, team DB
>
> **Tipo:** censimento + piano. Risponde a una domanda sola: *c'è codice,
> configurazione o documentazione che esiste solo per tenere in vita dati —
> o nomi — che il modello ha già lasciato?*
>
> **Stato:** prima passata, **12-09-2026**. Letture di **struttura**
> (catalogo `pg_class`/`pg_proc`, doc auto-gen, grep su BE/FE/pgTAP/seed).
> ⛔ I conteggi che compaiono sono **fatti datati**, mai motivi: la ragione di
> ogni voce è scritta sul modello.
>
> **12-09-2026, pomeriggio — lato BE/FE chiuso** (passi 1, 2, 3-BE, 5, 6 del
> §5): il backend non nomina più la vista né il suo model, i due ripieghi e i
> due alias sono via, i documenti del §4 corretti. Restano al **DB** i passi
> 2 e 4: la consegna è il **§6** di questo documento, con le due domande a Tid.
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

## 2. Censimento — che cosa resta al 12-09

Legenda: 🟡 nome morto con lettori vivi · 🟠 tenuto per prudenza, senza più
nessuno che lo scriva · ℹ️ dato residuo senza lettori.

### 2.1 🟡 A — La vista col nome vecchio: `anagrafiche.risorse_umane_auth_user` (lo «strato 2»)

È l'unica voce grossa, ed è la **seconda metà** del precedente: la segnalazione
del BE del 12-09 la chiamava *strato 2* e la lasciava da decidere.

**Che cos'è oggi.** Una proiezione di `identita_digitali` **filtrata** su
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
| `trg_risorse_umane_a10_risorse_umane_auth_user_block_deact_upd` | la **vista** `risorse_umane_auth_user` | funziona (la vista ha `risorsa_umana_id` e `attivo`) ed è **l'unico** guard che lega RU ↔ identità OPERATORE attiva: `identita_digitali` non ha un guard suo su `soggetti_ruoli`. **Resta**, e sparirà con la vista — lo strato 2 deve prima decidere se la regola migra sul figlio vero |

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
| 2 | **DB** 🔵 | le **quattro** funzioni riscritte sulla madre (`%TYPE` su `identita_digitali`), i nove pgTAP, `DROP VIEW`, manuale **cancellato**; il presidio `vw_riferimenti_morti_da_sanare` fa da rete su ogni `%TYPE` o corpo dimenticato. **Consegna nel §6** (censimento dal catalogo, ordine, presidi) |
| 3 | DB | ~~il ramo legacy di `fn_sync_auth_user_expired`: decisione scritta~~ ✅ deciso (assorbito da `identita_digitali.valido_al`): cade con la copia Python, dentro il passo 2. ⚠️ Prima dello `DROP VIEW`: dove va il guard RU ↔ identità attiva (oggi vive solo attraverso la vista) — **§6.2, domanda a Tid** |
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

### 2.6 ℹ️ F — `public.version_info`

Una riga, **zero lettori** in BE/FE/pgTAP; la nomina solo il resync delle
sequence (`90_end/20260818-72`, per escluderla). PROJECT_CONTEXT la dà per
«da verificare se esiste ancora»: esiste. Va deciso se ha un mestiere (allora
un lettore e un manuale) o no (allora `DROP`). Oggi è la seconda.

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
| manuale [risorse_umane_auth_user.md](../../dbzero/anagrafiche/manual/risorse_umane_auth_user.md) | «la tabella originale è stata rinominata in `_legacy_…` e archiviata» + una sezione intera sulla tabella legacy | la tabella è **droppata**; il manuale cade con la vista (§2.1) o si riscrive subito |

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
| 3 | §2.1 **strato 2** — cantiere suo: BE prima (tre punti, model, copia Python sostituita dalla chiamata DB, chiave del profilo), poi DB (cinque funzioni, nove pgTAP, `DROP VIEW`, manuale via) | BE → DB | **BE ✅ 12-09** · DB 🔵 consegna nel §6 |
| 4 | §2.5 + §2.6 — due `DROP` in `00_schema` | DB, decisione Tid | ⚪ §6.5, la parola è di Tid |
| 5 | §2.4 + §2.8 — frontend | FE | ✅ 12-09 |
| 6 | §4 — sette righe di documentazione (diventate ~20: vedi la tabella aggiunta) | chi tocca il file per primo | ✅ 12-09 (tranne le guide DB, col `DROP`) |

⛔ **Cosa NON fare**: non «tenere per sicurezza». Ogni voce di questo elenco è
nata così, e il precedente del §1 mostra dove porta: a un endpoint a 500 e a
una policy di perimetro scritta per sei righe di test.

---

## 6. Lato DB — la consegna dello strato 2, e le due domande a Tid

> Scritto il 12-09 pomeriggio, a BE chiuso. È il **passo 2** del §2.1 e il
> **passo 4** del §5, per il team DB (`dev/db-tid`). Il precedente è il §10 di
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

### 6.2 D1 · Le quattro funzioni sulla madre — e ⚪ il guard (domanda a Tid)

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

### 6.3 D2 · `DROP VIEW`, manuale, guide

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
⇒ **Togliere la chiave**, non rinominarla: l'id dell'identità del JWT il
profilo lo espone già nel blocco `identita` (§8.3.6), e `identita_id` lì
sarebbe la stessa informazione in due posti.

### 6.5 D4 · ⚪ I due `DROP` del §2.5 e §2.6 — decisione di Tid

| | Oggetto | Raccomandazione |
| --- | --- | --- |
| §2.5 | `dbops._defaults_backup_usercols` | `DROP TABLE` in `00_schema/dbops`, con la riga di `rollback` che dice che non c'è ritorno. Non è software: è un dato «per sicurezza» che nessuno può usare |
| §2.6 | `public.version_info` | o un mestiere (un lettore + un manuale) o `DROP`. Oggi è la seconda |

⛔ Entrambi «tenuti per sicurezza», la forma da cui ogni voce di questo
documento è nata. Ma sono `DROP` di tabelle: **la parola è di Tid.**

### 6.6 Presidi

| | Dove | Prova | Il suo contrario |
| --- | --- | --- | --- |
| **P-1** | `test-legacy-risorse-umane-auth-user-ritirata-v1` (girato) o gemello | la vista **non** esiste; le quattro funzioni compilano sulla madre; `vw_riferimenti_morti_da_sanare` a **zero** | — |
| **P-2** | pgTAP del guard di 6.2 | RU con identità OPERATORE attiva ⇒ `attivo = false` **rifiutato** col codice nuovo | identità disattivata prima ⇒ passa; RU senza identità ⇒ passa |
| **P-3** | `test-fn-get-soggetto-dati-and-user-profile` | il blocco `risorse_umane` **non** contiene `risorse_umane_auth_user_id` | `identita.id` c'è |
| BE | `core/tests/db/test_risorsa_umana_dalla_madre` (in CI) | resta verde: il backend non torna a nominarla | — |

⛔ **Cosa non si fa**: tenere la vista «come alias, tanto non costa» (l'unico
argomento è il costo, §2.1); riscrivere il ramo legacy sulla madre (cade);
il `DROP VIEW` **prima** del guard di 6.2 (ogni disattivazione di una RU
fallirebbe, come il `-10` la mattina del 12-09); i due `DROP` di 6.5 senza
l'ok di Tid.

| | |
| --- | --- |
| BE | ✅ chiuso il 12-09 pomeriggio: nessun lettore, presidio in CI |
| DB | 🔵 in attesa: 6.2 · 6.3 · 6.4 · presidi P-1/P-2/P-3 · ⭐ 6.3-bis (raccomandazione, non prerequisito) |
| Tid | ⚪ 6.2 (forma del guard) · 6.5 (i due `DROP`) |

---

*Analisi 12-09-2026 — letture di struttura sul database `zeroerp` (catalogo,
doc auto-gen) e sul repo (grep BE/FE/pgTAP/seed). I numeri sono fatti datati.
Il precedente del §1 è chiuso; BE e FE sono chiusi il 12-09 pomeriggio; il
lato DB (§6) è aperto.*
