# Brief DB — Il permesso controllato nel verbo di scrittura

> **Chi scrive:** team DB (`dev/db-tid`), 2026-09-24. **A chi:** Tid (decisioni,
> §7), poi team DB e backend.
> **Origine:** approfondimento del §8 di
> [brief-db-area-funzionale-assistente-ai.md](brief-db-area-funzionale-assistente-ai.md).
> **Stato al 2026-10-03:** ✅ **CHIUSO e archiviato in `work-done/`.** D-1 → D-5
> decise da Tid il 2026-09-24 (§7); passi 1, 2a e 2b fatti. ⭐ **Il modello non vive
> più qui**: la sua sede è la guida
> [architettura-permessi-e-autorizzazioni.md §7.4-7.5](../../guide/architettura-permessi-e-autorizzazioni.md#74-il-permesso-nel-verbo-di-scrittura),
> più completa di questo brief (quattro guard, con `script.fn_guard_utente_stesso`).
> Il passo 3 non ha una fine e **non tiene aperto il brief**: ogni cantiere che
> porta un dominio al modello lo scrive nel suo brief operativo e nella guida del
> dominio. Questo documento resta come storia delle decisioni.
> **Avanzamento al 2026-10-03** — il percorso del §5, passo per passo:
>
> | Passo | Stato |
> | --- | --- |
> | 1. BB del permesso | ✅ **fatto**: `script.fn_guard_azione` (`20260924-38`) e `script.fn_guard_livello` (D-2, D-5; `20260925-32`, con `fn_area_di_oggetto` `-31`), applicati su dbdev e verdi |
> | 2a. Porta del Lotto 2 (D-4) | ✅ **chiusa, committata, backend allineato e committato** (`0aefe15cd`, PR #1686); brief in `work-done/`. `20260924-38` → `-42` (commit `f2e724b47`, PR #1681); **D-V1 decisa il 2026-09-25 (strada A)**: la porta `POSTED` e le righe in `CONFIRM` si aprono solo con la GUC **e** dentro un verbo, col BB nuovo `script.fn_is_proprietario_tabella` (`20260925-37…-39`, commit `1d92ae6a2`, PR #1684). P-6 (`presidi.csv`) letto su dbdev: arrivato. §6 del brief operativo fatto dal backend il 2026-09-25 (fixture con `registra_magazzino`, test DB e smoke verdi) |
> | 2b. Verbo generico del pannello (D-3) | ✅ **Chiuso il 2026-09-28**: brief operativo [brief-db-pannello-config-verbo-generico.md](brief-db-pannello-config-verbo-generico.md), in `work-done/`. **DB**: `20260925-29…-34`, `20260927-20…-22` e `20260928-30` applicati, con pgTAP verdi. L'ultimo è la D-P9: `config.aree_funzionali` in sola lettura per l'app. **Backend e frontend**: §6 in `e7dbbad73`; §6.1, D-P5 e «Salva» vuoto in `5bd689163`. Guida dei permessi (§4.1, §7.4-7.5) e PROJECT_CONTEXT aggiornati |
> | 3. Domini esistenti | aperto per costruzione, senza data, **fuori da questo brief**. Casi fatti al 2026-10-03 (letti dal loop dei grant `90_end/ci_apply/20260205-41` e dai corpi): **credenziali** — blocco/sblocco con `fn_guard_super_admin` (`20260925-06`), `config.credenziali`, `credenziali_provenienze`, `nomi_tentati`, `nomi_tentati_provenienze` chiuse all'app ([brief](brief-db-blocco-login-per-credenziale.md)); **secondo fattore** — verbi `script.fn_totp_*` e il guard nuovo `script.fn_guard_utente_stesso` (`20260929-14`), `config.auth_totp_device` chiusa (`20260929-24`, [brief](brief-db-secondo-fattore-totp.md)); **magazzino, Lotto 3** — `fn_posta_trasferimento` (`registra_magazzino`), `fn_apri_blocco`/`fn_libera_blocco` (`blocca_merce`), `movimenti_attesi` chiusa ([brief](brief-db-magazzino-lotto-3-scarico-da-ddt.md)); **vendite** — `fn_cambia_stato_ddt` (`emetti_ddt`, `registra_magazzino`) e `fn_conferma_reso`/`fn_annulla_reso` (`conferma_reso`), DEFINER, con la porta **del registro** e non ancora quella del documento (Lotto 3 D-L3-e, [3-bis](brief-db-magazzino-lotto-3-bis-carico-da-reso.md) D-3b-f). ⚠️ **Domini a metà non ancora dichiarati nella loro guida** (§5.3): `magazzino` (aperte, fra le altre, `magazzini` e `ubicazioni`: D-P4 del brief del pannello) — dichiarato nella guida del dominio il 2026-10-03 e affidato a [brief-db-magazzino-tutte-le-scritture-dal-verbo.md](../work-in-progress/brief-db-magazzino-tutte-le-scritture-dal-verbo.md) — e `vendite`, che avrà un brief suo |
>
> **In una riga:** oggi il DB **calcola** i permessi ma non li **applica**:
> qualunque scrittura che il backend autorizza per errore, il DB la esegue. La
> forma che chiude il buco, coerente col DB-first, è **una scrittura = un verbo**:
> una funzione DB che controlla azione o livello di chi agisce, con l'app che
> perde `INSERT`/`UPDATE`/`DELETE` sulle tabelle che il verbo protegge.
>
> ⇒ La proposta è di adottarla come **regola per i domini nuovi** e di portarci
> gli esistenti uno alla volta, **senza data**. Le decisioni del §7 sono prese
> (D-1 → D-5, 2026-09-24).

---

## 1. Il problema che resta dopo la sola lettura

Il [brief-be-letture-in-transazione-sola-lettura.md](brief-be-letture-in-transazione-sola-lettura.md)
fa garantire al DB che **una lettura non scriva**. Non copre il caso opposto: una
richiesta di **scrittura** che il backend autorizza a chi non dovrebbe, per
esempio un endpoint con il `post_permission` sbagliato, o un tool dell'assistente
legato all'endpoint sbagliato. Lì il DB esegue, perché:

* `zeroerp_app` ha i privilegi di scrittura sulle tabelle;
* nessuna policy RLS e nessuna funzione consulta il livello o l'azione di chi
  agisce.

## 2. Cosa c'è oggi — letto dalla struttura

Fatti datati, letti il 2026-09-24 sul catalogo di dbdev e nel codice. Descrivono
il punto di partenza: **non** decidono né la forma né la priorità.

* **Il DB sa chi agisce.** A ogni richiesta il backend imposta nella sessione
  `app.current_user_id`, `app.ruolo_applicativo`, `app.current_identita_id`,
  `app.current_emittente_id` (`core/api/jwt_audit_authentication.py`). Le policy
  RLS le leggono già.
* **Il DB sa decidere.** `script.fn_resolve_livello_area`,
  `script.fn_resolve_livello_oggetto`, `script.fn_check_azione_processo` sono la
  sede della regola: il backend le chiama, non le riscrive.
* **Il DB non applica.** Nessuna policy cita quelle funzioni: le policy esistenti
  decidono il **perimetro** (emittente, ambito), cioè *quali righe*, non *cosa
  ci si può fare*.
* **La RLS è `ENABLE` senza `FORCE`** (postura del progetto): le funzioni
  `SECURITY DEFINER` del proprietario la scavalcano.
* **Le scritture partono quasi tutte dal backend con SQL diretto** (a quella data
  circa 300 istruzioni `INSERT`/`UPDATE`/`DELETE` in 49 file, più un CRUD
  generico sulle tabelle di configurazione e scritture a tabella costruita a
  runtime). Le funzioni DB che scrivono coprono una parte dei casi.
* ⭐ **La forma «porta» esiste già**: Lotto 2 di magazzino, D-L2-b
  ([brief-db-magazzino-lotto-2-motore.md](brief-db-magazzino-lotto-2-motore.md)).
  `zeroerp_app` ha solo `SELECT` su `magazzino.movimenti`; scrive solo la
  primitiva `fn_scrivi_movimento`, `SECURITY DEFINER` del proprietario; il
  perimetro è rimesso dal guard BB `script.trgfn_guard_emittente_scope`.
* ⛔ **E mostra il pezzo che manca.** Verificato il 2026-09-24:
  `zeroerp_app` ha `EXECUTE` **direttamente** su `fn_scrivi_movimento` (e su
  `fn_ricalcola_valore_giacenza`), non solo sulle operazioni
  `fn_posta_inventario` / `fn_posta_rettifica` che la chiamano. E nessuna delle
  quattro controlla un permesso. La porta decide **da dove** si scrive, non
  **chi** può scrivere.

## 3. Perché non una policy RLS sul livello

È la prima idea, ed è sbagliata per il **modello**, non per il costo:

1. **Una tabella non è un'operazione.** Un operatore in `LETTURA` su `pratiche`
   con l'azione `cambia_stato_pratica` concessa **deve** poter scrivere sulle
   tabelle di `pratiche`. Una policy vede «UPDATE su questa tabella», non quale
   azione lo autorizza: blocca proprio il caso legittimo.
2. **Un'area non è uno schema.** Un'operazione di `vendite` scrive anche in
   `pagamenti`, `dbops`, `config`; aree come `core`, `strumenti`,
   `ai_assistant` non hanno uno schema.
3. **Le DEFINER la scavalcano**: la barriera avrebbe buchi per costruzione.

⇒ Il permesso appartiene all'**operazione**. A DB l'operazione ha un nome solo:
la **funzione** che la esegue.

## 4. Il modello proposto

### 4.1 Una scrittura = un verbo

* Ogni operazione di scrittura di un dominio che adotta il modello è una
  **funzione DB** (il *verbo*): `fn_posta_inventario`, `fn_cambia_stato_pratica`, …
* Il verbo **dichiara il suo permesso nella prima riga**, con un building block
  unico, e non con un controllo scritto a mano:
  * `script.fn_guard_azione(p_auth_user_id, p_permission_codename)` — ✅ scritto
    il 2026-09-24 (`20260924-38`), oppure
  * `script.fn_guard_livello(…)`, la forma sull'oggetto (D-5), che nasce con il
    verbo generico del pannello.

  ⭐ Una terza forma è nata il 2026-09-25 per le porte che non sono un'area del
  catalogo: `script.fn_guard_super_admin(p_auth_user_id)` (`20260925-06`), per i
  verbi della gestione accessi (`amm_software`, solo SUPER_ADMIN). Stessa forma
  delle altre: l'utente come parametro, la regola in una funzione che esiste già
  (`script.fn_is_super_admin`). Il perché in
  [brief-db-blocco-login-per-credenziale.md](brief-db-blocco-login-per-credenziale.md)
  §3.3 (D-B1).

  Il verbo passa l'utente letto da `app.current_user_id` con l'espressione delle
  policy (linee-guida-sql §10.4); il BB chiama le funzioni di risoluzione che
  già esistono (sede unica della regola). Il nome è `fn_guard_*` perché blocca
  sollevando (linee-guida-sql §5). Se il permesso manca, solleva un **codice
  registrato**, famiglia autorizzazione.
* ⭐ Per un'azione di processo il verbo **è** l'azione: `cambia_stato_pratica` il
  codename, `fn_cambia_stato_pratica` il verbo. La coppia rende naturale ciò che
  una policy non sa esprimere (§3.1).

### 4.2 La porta: le tabelle del verbo si chiudono all'app

Stessa forma del Lotto 2 (D-L2-b), resa generale:

* `zeroerp_app` perde `INSERT`/`UPDATE`/`DELETE` sulle tabelle che il verbo
  protegge; la postura si dichiara nel loop dei grant di `ci_apply`
  (`v_tabelle_sola_lettura_app`) e in `provision_db_roles.sql`, come fa il
  Lotto 2 — **non** con un `REVOKE` in un changeSet normale;
* chi scrive su una tabella chiusa gira come **proprietario** (DEFINER), e il
  perimetro lo rimette il guard BB `trgfn_guard_emittente_scope`, come in
  magazzino;
* ⛔ **l'app può eseguire solo i verbi**, non le primitive che i verbi usano: su
  una primitiva `REVOKE EXECUTE … FROM zeroerp_app`. Altrimenti il controllo del
  verbo si aggira chiamando la primitiva (§2, ultimo punto).

### 4.3 Il backend chiede, non decide due volte

Il backend **tiene** il suo controllo sugli endpoint: dà un 403 immediato e un
messaggio utile prima di aprire una transazione. Non è una seconda copia della
regola, perché anche il backend chiama le **stesse** funzioni di risoluzione: la
regola ha una sede sola (il DB), i **punti di applicazione** diventano due. Il
verbo è quello che non si può scavalcare.

### 4.4 Cosa NON protegge — da scrivere, non da scoprire

⛔ **L'identità la dichiara il backend.** Le GUC `app.current_user_id` e
`app.ruolo_applicativo` le imposta la connessione dell'app con `set_config`, e
qualunque codice su quella connessione può impostarle a un altro utente. Quindi il
modello protegge da un backend **che sbaglia** (permesso dichiarato male, tool
legato all'endpoint sbagliato, service che scrive dove non dovrebbe), **non** da un
backend **compromesso**. È lo stesso limite che hanno oggi le policy RLS di
perimetro: va scritto nella guida, non lasciato implicito.

## 5. Il percorso

1. **Il BB del permesso** (`fn_guard_azione` / `fn_guard_livello`) e i suoi
   codici di errore: un cantiere piccolo, in `script`.
2. **I domini nuovi nascono così**: `magazzino` e `acquisti` sono il prossimo
   cantiere (decisione di Tid del 2026-09-11), e ogni decisione presa lì vale per
   due domini. Il primo passo è **chiudere la porta già aperta del Lotto 2**:
   verbo che controlla il permesso, `EXECUTE` sulla primitiva tolto all'app.
3. **I domini esistenti, uno alla volta, senza data**: quando un cantiere tocca
   le scritture di un dominio, ne porta i verbi al modello nello stesso giro.
   ⚠️ Un dominio **a metà** — alcune tabelle chiuse, altre no — va dichiarato
   come tale nella sua guida, con l'elenco delle tabelle ancora aperte.

## 6. Cosa non si chiede

* ⛔ Nessuna policy RLS di scrittura sul livello (§3).
* ⛔ Nessun `FORCE ROW LEVEL SECURITY`: la postura resta quella del progetto, il
  perimetro dentro le DEFINER lo rimette il guard BB.
* ⛔ Nessuna migrazione in blocco degli esistenti.

## 7. Decisioni aperte — a Tid

| # | Domanda | Proposta |
| --- | --- | --- |
| **D-1** | Adottare il modello (§4) come direzione? | ✅ **DECISA da Tid il 2026-09-24: sì** — i domini nuovi (`magazzino`, `acquisti`) nascono così; gli esistenti ci passano quando un cantiere tocca le loro scritture, uno alla volta, senza data. Accettato il limite del §4.4 |
| **D-2** | Ogni verbo è legato a **un'azione di processo**, o basta il livello d'area per i verbi CRUD semplici? | ✅ **DECISA da Tid il 2026-09-24: due forme, un BB.** Le operazioni di processo (cambia stato, emetti, genera, annulla…) chiedono la loro azione — verbo e azione coincidono; le operazioni semplici (crea, modifica, cancella) chiedono il livello d'area (`TUTTO`). La forma la sceglie chi scrive il verbo, nella prima riga, con il BB unico. `azioni_processo` non si riempie di azioni che ripetono il livello, e l'amministratore ragiona come oggi |
| **D-3** | Il CRUD generico delle tabelle di configurazione (`config_crud_repository`) | ✅ **DECISA da Tid il 2026-09-24 — verbo generico SUBITO**, all'inizio del cantiere `magazzino`/`acquisti`. Vedi §7.1 |
| **D-4** | Il Lotto 2 chiude subito la porta aperta (§2, ultimo punto)? | ✅ **DECISA da Tid il 2026-09-24: sì, primo cantiere del modello, subito.** `fn_posta_inventario` e `fn_posta_rettifica` diventano i verbi: controllano nella prima riga l'azione **`registra_magazzino`**, che esiste già ed è il gate del backend (non servono azioni nuove), e girano DEFINER del proprietario; l'app perde `EXECUTE` su `fn_scrivi_movimento` e `fn_ricalcola_valore_giacenza`; il perimetro sui documenti lo rimette il verbo, chiamando lo stesso predicato della policy. Il backend non cambia. **Sede del lavoro:** [brief-db-magazzino-verbi-con-permesso.md](brief-db-magazzino-verbi-con-permesso.md); il brief del Lotto 2 ha solo una nota in D-L2-b, per non falsarne lo stato di consegnato |
| **D-5** | Gli override per oggetto (`fn_resolve_livello_oggetto`, `area_model_overrides`) | ✅ **DECISA da Tid il 2026-09-24.** Nella forma semplice il verbo dichiara **l'oggetto** su cui scrive, non l'area: il BB passa da `fn_resolve_livello_oggetto` (override utente, poi livello d'area), e l'area la legge da `area_model_overrides`, senza ripeterla. Vale anche per il verbo generico del pannello (ogni riga della lista ammessa dichiara il suo oggetto). L'oggetto si nomina con la chiave che il catalogo ha già (`app_label` + `model_name`): una seconda nomenclatura sarebbe una seconda sede. Le operazioni di processo restano sull'azione. ⛔ **Difetto trovato**: `fn_resolve_livello_oggetto` non ha il gate di contesto (`app.ruolo_applicativo` ≠ `OPERATORE` ⇒ `BLOCCATO`) che ha `fn_resolve_livello_area`, quindi un override per oggetto vale anche fuori dalla veste operatore. Il BB applica il gate da sé; la funzione si corregge nello stesso lavoro, perché il backend la usa già |

### 7.1 D-3 — il pannello di configurazione passa dal verbo generico

**Il fatto che ha deciso la forma** (letto dal codice il 2026-09-24): il pannello
generico di configurazione (`REL_CONSENTITE` in `core/db/dbops_repository.py`,
scrittura in `core/db/config_crud_repository.py` con il nome della tabella
costruito a runtime) **non gestisce solo `config`**. La sua lista contiene tabelle
di altri domini, fra cui `magazzino.magazzini`, `magazzino.ubicazioni` e
`magazzino.causali`. E le quattro view del pannello dichiarano
`area_funzionale = "config"` per **qualunque** tabella.

Due conseguenze:

* rimandare il pannello farebbe nascere `magazzino` con la porta chiusa sui
  movimenti e **aperta sulle sue anagrafiche**: non sarebbe «nato così» (D-1);
* ⛔ oggi chi ha `TUTTO` su Configurazione e `LETTURA` su Magazzino **crea e
  cancella magazzini**: il permesso guarda l'area del pannello, non quella a cui
  la riga appartiene.

**La decisione:**

1. **Un verbo generico, subito** — per esempio `fn_config_scrivi(tabella,
   operazione, dati)`, `SECURITY DEFINER` del proprietario, perimetro col guard BB
   dove la tabella ne ha uno.
2. **Tutto il pannello passa dal verbo subito.** Lato backend è un repository
   solo: il cambio vale per tutte le tabelle della lista in un colpo.
3. **La lista ammessa diventa un dato del DB**, non più una costante del backend,
   e **ogni riga dichiara l'area a cui la tabella appartiene** (`magazzino.magazzini`
   → Magazzino). Il verbo controlla il livello su **quell'area**, nella forma
   semplice della D-2 (`TUTTO`). La costante `REL_CONSENTITE` si ritira nello
   stesso giro: una sede sola.
4. **La porta si chiude per dominio.** `REVOKE` all'app da subito sulle tabelle di
   `magazzino` e `acquisti`; le altre si chiudono quando passa il loro dominio
   (D-1). Fino ad allora sono scrivibili anche direttamente, e la lista a DB lo
   deve poter dire.

⚠️ **Effetto voluto sul comportamento**: il punto 3 toglie la scrittura sulle
tabelle di un dominio a chi aveva `TUTTO` solo su Configurazione. È corretto per il
modello; qualche profilo andrà rivisto. Non siamo in produzione: niente da
migrare.

---

## Registro

| Data | Chi | Cosa |
| --- | --- | --- |
| 2026-09-24 | DB | Brief scritto dall'approfondimento del §8 del brief dell'assistente AI, su decisione di Tid («3 con brief apposito») |
| 2026-09-24 | Tid | D-1 decisa: sì al modello del verbo come direzione |
| 2026-09-24 | Tid | D-2 decisa: due forme (azione per i processi, livello d'area per il CRUD semplice), un BB |
| 2026-09-24 | Tid | D-3 decisa, **corretta** rispetto alla prima proposta («al primo cantiere che tocca il pannello»): il pannello contiene tabelle di magazzino, quindi verbo generico subito, lista ammessa a DB con l'area di appartenenza, porta chiusa per dominio (§7.1) |
| 2026-09-24 | Tid | D-4 decisa: i due verbi del Lotto 2 con permesso e DEFINER, `EXECUTE` sulla primitiva tolto all'app. Sede del lavoro: brief operativo proprio, non il brief del Lotto 2 (consegnato), che riceve solo una nota in D-L2-b |
| 2026-09-24 | Tid | D-5 decisa: il verbo dichiara l'oggetto, il BB rispetta gli override; correzione del gate in `fn_resolve_livello_oggetto` nel brief operativo di magazzino (§2.4) |
| 2026-09-25 | DB | Stato riscritto in testa: porta del Lotto 2 committata (`f2e724b47`), D-V1 ancora aperta; `fn_guard_livello` e il verbo del pannello (D-3) non iniziati; registrato il secondo caso del modello (credenziali, `fn_guard_super_admin`, §4.1) |
| 2026-09-25 | Tid, DB | D-V1 del brief di magazzino decisa (strada A) e scritta: nasce `script.fn_is_proprietario_tabella`, il modo in cui un guard riconosce di essere attraversato da un verbo |
| 2026-09-25 | DB | Scritto il brief operativo della D-3 (verbo generico del pannello), con cinque decisioni a Tid |
| 2026-09-25 | BE | Stato del passo 2a riscritto: P-7 committato (`1d92ae6a2`), P-6 arrivato al DB, §6 del brief di magazzino fatto dal backend (da committare). Aperti: 1 (`fn_guard_livello`), 2b (D-3), 3 |
| 2026-09-25 | BE | Stato riscritto: passo 1 fatto (`fn_guard_livello`), 2a chiuso e brief in `work-done/`, 2b lato DB chiuso (`7f3208a58`), backend in corso |
| 2026-09-27 | DB | Stato riscritto: backend del 2b committato (`e7dbbad73`), blocco login lato DB committato (`e3d188dc0`). D-P6 del brief del pannello scritta, da applicare: dopo l'apply resta il frontend (D-P5) |
| 2026-09-27 | Tid | D-P6 applicata, pgTAP verdi. Il passo 2b chiude, lato DB, quando si decidono i tre punti aperti del brief del pannello. Poi resta il frontend (D-P5) |
| 2026-09-27 | DB | Passo 2b: D-P8 e le due richieste del backend scritte (`20260927-20…-22`), da applicare. Aperta la D-P9 |
| 2026-09-27 | Tid | `20260927-20…-22` applicati, pgTAP verdi. Passo 2b: lato DB aperta solo la D-P9. Restano il backend (metadata dalla funzione unica) e il frontend (D-P5) |
| 2026-09-28 | BE/FE | Passo 2b: backend (metadata dalla funzione unica) e frontend (D-P5, «Salva» vuoto) fatti, non committati. Guida dei permessi e PROJECT_CONTEXT aggiornati: il modello ora vive nella guida (§7.4). Resta la D-P9 |
| 2026-09-28 | DB | Passo 2b: BE/FE pushati (`5bd689163`); D-P9 scritta e provata (`90_end/20260928-30`), da applicare. È l'ultimo pezzo del brief operativo |
| 2026-09-28 | Tid, DB | `20260928-30` applicato, nessuna regressione nei pgTAP. **Passo 2b chiuso**, e il brief operativo del pannello è in `work-done/`. Aperto resta il passo 3 |
| 2026-10-03 | DB | **Brief chiuso e spostato in `work-done/`**: il modello vive nella guida dei permessi §7.4-7.5, che è più completa (quattro guard); due sedi avrebbero finito per divergere. La tabella in testa registra i casi del passo 3 fatti dopo il 28-09 (secondo fattore, Lotto 3 di magazzino, verbi di bolla e reso). Rilevati due domini a metà mai dichiarati nella loro guida — `magazzino` (D-P4 del brief del pannello, brief a sé mai scritto) e `vendite` — affidati ai brief dei loro cantieri |
