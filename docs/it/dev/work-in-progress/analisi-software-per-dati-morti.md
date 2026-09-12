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
| 1 | **BE** — prima, perché è il lettore vivo fuori dal DB (lezione del 12-09: il DROP è passato prima della consegna e l'endpoint è andato a 500) | i tre punti su `identita_digitali` (+ `risorse_umane` dove serve `risorsa_umana_id`); ritiro del model `RisorseUmaneAuthUser`; `list_expired_auth_user_ids` **non** ricopiata sul nuovo modello ma **sostituita** da una chiamata alla stessa `WHERE` del DB (una regola, una sede); la chiave del profilo rinominata o tolta |
| 2 | **DB** | le cinque funzioni riscritte sulla madre (`%TYPE` su `identita_digitali`), i nove pgTAP, `DROP VIEW`, manuale **cancellato**; il presidio `vw_riferimenti_morti_da_sanare` fa da rete su ogni `%TYPE` o corpo dimenticato |
| 3 | DB | ~~il ramo legacy di `fn_sync_auth_user_expired`: decisione scritta~~ ✅ deciso (assorbito da `identita_digitali.valido_al`): cade con la copia Python, dentro il passo 2. ⚠️ Prima dello `DROP VIEW`: dove va il guard RU ↔ identità attiva (oggi vive solo attraverso la vista) |
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

### 2.3 🟠 C — Difesa da una chiave che non arriva più

[me_view.py:143](../../../../backend/apps/core/api/me_view.py#L143):
`profile.pop("ruolo_sistema", None)`. `script.fn_get_user_profile` **non
emette** `ruolo_sistema` dalla Fase 7 (29-04-2026; lo dice il suo `COMMENT`).
Codice morto per una chiave morta. **Via** (BE, stesso commit di B).

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

### 2.8 🟡 H — `isAdmin`, alias «legacy» di `isSuperAdmin` (frontend)

[auth.js:436](../../../../frontend/src/stores/auth.js#L436). Il modello
ADMIN/OPERATIVO è morto in Fase 7 e il badge non lo rende più; l'alias tiene
vivo il **vocabolario** vecchio. ⇒ FE: rinomina dei consumatori, via l'alias.

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

---

## 5. Ordine, e di chi

| # | Cosa | Di chi | Dipende da |
| --- | --- | --- | --- |
| 1 | §2.2 + §2.3 — i due ripieghi morti, un commit | BE | — |
| 2 | §2.7 — rinomina dei nove chiamanti, via l'alias | BE | — |
| 3 | §2.1 **strato 2** — cantiere suo: BE prima (tre punti, model, copia Python sostituita dalla chiamata DB, chiave del profilo), poi DB (cinque funzioni, nove pgTAP, `DROP VIEW`, manuale via) | BE → DB | decisione sul ramo legacy di `fn_sync_auth_user_expired` |
| 4 | §2.5 + §2.6 — due `DROP` in `00_schema` | DB, decisione Tid | — |
| 5 | §2.4 + §2.8 — frontend | FE | — |
| 6 | §4 — sette righe di documentazione | chi tocca il file per primo | — |

⛔ **Cosa NON fare**: non «tenere per sicurezza». Ogni voce di questo elenco è
nata così, e il precedente del §1 mostra dove porta: a un endpoint a 500 e a
una policy di perimetro scritta per sei righe di test.

---

*Analisi 12-09-2026 — letture di struttura sul database `zeroerp` (catalogo,
doc auto-gen) e sul repo (grep BE/FE/pgTAP/seed). I numeri sono fatti datati.
Il precedente del §1 è chiuso; il resto è aperto.*
