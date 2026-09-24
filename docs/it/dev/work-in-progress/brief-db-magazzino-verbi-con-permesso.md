# Brief DB — Magazzino: i verbi che controllano il permesso

> **Chi scrive:** team DB (`dev/db-tid`), 2026-09-24. **A chi:** team DB; una
> richiesta minore al backend (§6).
> **Origine:** decisione **D-4** di
> [brief-db-permesso-nel-verbo-di-scrittura.md](brief-db-permesso-nel-verbo-di-scrittura.md)
> — il primo cantiere del modello «una scrittura = un verbo», applicato alla porta
> del Lotto 2
> ([brief-db-magazzino-lotto-2-motore.md](../work-done/brief-db-magazzino-lotto-2-motore.md),
> D-L2-b). Le decisioni D-1 → D-5 sono di Tid, tutte del 2026-09-24.
> **Stato al 2026-09-24 notte:** ✅ **la porta è chiusa — P-0 → P-5 applicati e verdi.**
> * ✅ applicati da Tid su dbdev: `20260924-38` (guard), `-39` (helper pgTAP), `-40`
>   (gate in `fn_resolve_livello_oggetto`), `-41` (i due verbi), `-42` (primitiva e
>   ricalcolo riservati, 23:35). Letto su dbdev: l'app esegue `fn_posta_inventario` e
>   `fn_posta_rettifica`, **non** esegue `fn_scrivi_movimento` né
>   `fn_ricalcola_valore_giacenza`.
> * ✅ pgTAP lanciati da Tid dopo ogni apply: parte A e parte B **verdi**, nessuna
>   regressione.
> * 🔵 **P-6 scritto**: nota del presidio in `presidi.csv` (da applicare: arriva coi
>   mirror `runOnChange`) e il modello in `PROJECT_CONTEXT`.
> * ⏳ Resta la decisione **D-V1** (§4: la porta `POSTED` apribile con una GUC che
>   l'app può impostare da sola).
> * ⚠️ Nulla è committato: changeSet, loop, provisioning, pgTAP e pagine `manual/` sono
>   nel working tree, e vanno in un commit solo (i pgTAP nuovi sono verdi solo coi
>   changeSet, quelli vecchi sono rossi con i changeSet).
>
> **In una riga:** nel Lotto 2 la porta sul registro dei movimenti decide **da
> dove** si scrive, non **chi** può scrivere. L'app può chiamare direttamente la
> primitiva, e nessuna funzione controlla un permesso. Qui le due operazioni
> diventano **verbi**: controllano l'azione `registra_magazzino`, girano come
> proprietario, e diventano l'unica strada verso la primitiva.

---

## 1. Il punto di partenza — letto il 2026-09-24

| Oggetto | Com'è oggi |
| --- | --- |
| `magazzino.movimenti`, `valore_giacenza` | l'app ha solo `SELECT` (porta del Lotto 2) ✅ |
| `magazzino.fn_scrivi_movimento`, `fn_ricalcola_valore_giacenza` | `SECURITY DEFINER` del proprietario; ⛔ **l'app ha `EXECUTE`** |
| `magazzino.fn_posta_inventario`, `fn_posta_rettifica` | `SECURITY INVOKER`: leggono e scrivono il documento sotto RLS come l'operatore, poi chiamano la primitiva. ⛔ **Nessun controllo di permesso** |
| `inventari`, `inventari_righe`, `rettifiche`, `rettifiche_righe` | RLS attiva (policy `…_ef_whitelist`, predicato `fn_scope_ef_whitelist_via_magazzino`); l'app scrive direttamente; **nessun guard di perimetro** (quello è solo sul registro) |
| l'azione | ✅ **esiste già**: `registra_magazzino` (area Magazzino, `pericolosa = t`, R-3 del 2-bis). Il backend la usa come `post_permission` di **entrambi** gli endpoint di registrazione |
| chi chiama cosa | il backend chiama **solo** le due operazioni (`magazzino/db/famiglie.py`); a DB la primitiva la chiamano **solo** le due operazioni |

⇒ Il permesso esiste ed è quello giusto, ma lo controlla solo il backend. Il DB
non lo guarda, e la primitiva si raggiunge anche saltando le operazioni.

## 2. Il disegno

### 2.1 Il building block: `script.fn_guard_azione(p_auth_user_id, p_permission_codename)`

* Riceve l'utente come **parametro** (il verbo lo legge da `app.current_user_id`
  con l'espressione delle policy, linee-guida-sql §10.4) e chiede a
  `script.fn_check_azione_processo`, la
  **stessa** funzione che usa il backend. La regola ha una sede sola; il BB è il
  punto in cui il DB la **applica**.
* Il gate di contesto è già dentro `fn_check_azione_processo`
  (`app.ruolo_applicativo` ≠ `OPERATORE` ⇒ negata).
* Se la risposta è no: `fn_log_and_raise_error` con **`E_PERMESSO_NEGATO`**,
  codice già registrato, classe `NON_PERMESSO`: è lo stesso rifiuto che il backend
  dà con lo stesso codice. Nel contesto va l'azione richiesta.
* ⛔ **Senza identità si rifiuta** (fail-closed): una sessione senza
  `app.current_user_id` non registra movimenti. Oggi nessun job registra
  inventari; quando servirà, il job avrà una sua identità, non un'eccezione nel BB.
* `SECURITY INVOKER`: dentro una DEFINER le GUC sono comunque quelle della
  sessione dell'operatore.
* ⚠️ **Solo la forma «azione».** La forma «livello per oggetto»
  (`fn_guard_livello`, D-2 e D-5) nasce con il suo primo consumatore, il verbo
  generico del pannello (D-3). Un BB senza consumatore non centralizza niente.

### 2.2 I due verbi

`fn_posta_inventario` e `fn_posta_rettifica`, riscritti partendo dal corpo della
**doc auto-generata**:

1. **Prima riga**: `PERFORM script.fn_guard_azione(NULLIF(current_setting('app.current_user_id', true), '')::integer, 'registra_magazzino')`.
2. **`SECURITY DEFINER` del proprietario**, con
   `SET search_path = pg_catalog, public, pg_temp` nella definizione (lo stampo è
   quello della primitiva).
3. ⛔ **Il perimetro si rimette a mano, con la funzione della policy.** Come
   DEFINER il verbo **non vede più la RLS** dei documenti: un inventario di un
   altro emittente, che oggi è «non trovato», diventerebbe leggibile e
   registrabile. Il guard BB del registro non aiuta, perché scatta su
   `INSERT`/`UPDATE OF magazzino_id` del **registro**, non sulla lettura del
   documento. Il predicato della policy,
   `script.fn_scope_ef_whitelist_via_magazzino(<utente>, magazzino_id)`, entra
   **nella stessa `WHERE` del `SELECT … FOR UPDATE`** della testata (passo 2 del
   corpo di oggi), non in un controllo successivo. Così:
   * il `NOT FOUND` resta **lo stesso ramo** di oggi, con lo stesso
     `E_MAG_DOCUMENTO_NON_TROVATO` (404 no-leak);
   * **non si prende il lock** sul documento di un altro emittente (un controllo
     dopo il `FOR UPDATE` lo prenderebbe, e lo terrebbe fino al rollback).

   Il resto della policy, cioè il gate `app.ruolo_applicativo = 'OPERATORE'`, lo
   copre già il passo 1: `fn_check_azione_processo` ha lo stesso gate.
   L'utente si legge dalla GUC con la stessa espressione della policy.
4. **Le letture interne** (`fn_inventario_piano`,
   `fn_check_documento_interno_registrabile`, `fn_check_riga_magazzino`,
   `fn_check_disponibilita_uscita`) sono INVOKER e dentro il verbo leggono **senza
   RLS**. È accettato per la stessa ragione del Lotto 2 (§7-sexies): il documento
   è di **un** magazzino, il magazzino è di **un** emittente, e il perimetro è già
   stato verificato al punto 3.
5. La GUC transazionale della porta `POSTED` (D-L2-h) resta com'è: vedi §4.
6. **Chi resta scritto come autore.** L'audit dei documenti
   (`trgfn_audit_data_user_generic`) usa prima `app.jwt_user`, quindi dentro il
   verbo registra la stessa persona di oggi. Lo **storico**
   (`trgfn_storico_generic`) registra `current_user`: dentro il verbo scriverà
   il **proprietario** al posto di `zeroerp_app`. In nessuno dei due casi è la
   persona, e i movimenti scritti dalla primitiva hanno già questa forma dal
   Lotto 2. Dichiarato, non corretto.

### 2.3 La porta sulla primitiva

`fn_scrivi_movimento` e `fn_ricalcola_valore_giacenza` entrano in
**`v_fn_riservate`**, il meccanismo che esiste già per le porte riservate:
`REVOKE EXECUTE … FROM PUBLIC, zeroerp_app`. Le funzioni hanno `EXECUTE` a
`PUBLIC` per default: revocarlo alla sola app non toglie niente.

Le **tre sedi** della postura, come per il registro:

* il loop `90_end/ci_apply/20260205-41-apply-runtime-grants-ci`
  (`v_fn_riservate`);
* `scripts/sql/provision_db_roles.sql`, blocco «POSTURA DICHIARATA»: gira **dopo**
  `ci_apply` e rifà `GRANT EXECUTE ON ALL FUNCTIONS`; senza l'eccezione riapre la
  porta nello stesso build;
* un changeSet `90_end` forward, che applica subito su dev (`ci_apply` su dev non
  gira da solo).

Si asserisce con `has_function_privilege('zeroerp_app', …, 'EXECUTE') = false`
(risponde anche per `PUBLIC`) in **`db/pgtap/magazzino/test-porta-ledger-v1.sql`**
(test 17-18), che è già il presidio delle tre sedi della porta del ledger. (La
prima stesura indicava il pgTAP dei registri append-only: quello presidia
`dbops`, non il magazzino.)

⚠️ **Fuori da P-4, dichiarato**: il ruolo batch `zeroerp_batch_fatturazione` ha
`EXECUTE` esplicito su primitiva e ricalcolo (e sui verbi). Il loop lascia di
proposito i grant espliciti ai ruoli batch, e i loro privilegi stanno nel
provisioning, mai in un changeSet (linee-guida-sql §11.6). Il ruolo non ha niente
da fare in magazzino: la revoca è una decisione del cantiere dei ruoli batch.

`fn_ricalcola_valore_giacenza` è uno strumento di riparazione della copia del
valore: il backend non la chiama, la usa il proprietario. Riservarla non toglie
niente a nessuno.

### 2.4 La correzione di `fn_resolve_livello_oggetto` (D-5)

Le manca il gate di contesto che ha `fn_resolve_livello_area`
(`app.ruolo_applicativo` valorizzata e ≠ `OPERATORE` ⇒ `BLOCCATO`): un override
per oggetto oggi vale anche fuori dalla veste operatore. Si aggiunge il **passo
0**, uguale a quello della funzione d'area. È un changeSet a sé, indipendente dai
verbi; il backend la usa già, quindi il difetto è vivo oggi.

⚠️ **Emersa scrivendo P-2, e non toccata**: anche
`script.fn_get_user_object_permissions_map` non ha il gate. Ma non decide niente:
restituisce le eccezioni per oggetto così come sono, senza identità né super
admin. E al 2026-09-24 il backend non la chiama: la usa solo un pgTAP. È una
candidata a funzione morta, da verificare in un cantiere di pulizia, non da
correggere qui.

## 3. I pgTAP

### 3.1 Quelli nuovi

Operatori **fabbricati nel test**, non presi dai dati:

1. operatore **con** `registra_magazzino` e nel perimetro ⇒ il verbo registra;
2. operatore **senza** l'azione ⇒ `E_PERMESSO_NEGATO`, nessun movimento;
3. operatore con l'azione ma documento di **un altro emittente** ⇒ lo stesso
   «non trovato» di oggi, nessun movimento;
4. sessione **senza identità** ⇒ rifiuto;
5. l'app che chiama **direttamente** `fn_scrivi_movimento` ⇒ `42501`;
6. contesto non operatore (`app.ruolo_applicativo` = veste portale) ⇒ rifiuto;
7. `fn_resolve_livello_oggetto` con override per oggetto e contesto non
   operatore ⇒ `BLOCCATO`.

### 3.2 Quelli esistenti che cambiano — censimento P-0, 2026-09-24

Il fixture condiviso `dbops.fn_pgtap_crea_emittente_operatore` crea un operatore
**tecnico, non super admin**: oggi non ha `registra_magazzino`, e dopo il cambio
i verbi lo rifiutano. ⇒ **Un helper di fixture nuovo**,
`dbops.fn_pgtap_concedi_azione(p_auth_user_id, p_permission_codename)` (un
`INSERT` in `config.user_override_azioni`, che l'app può scrivere), con **cinque
consumatori** fin dal primo giorno.

| File | Runner | Cosa chiama | Cosa cambia |
| --- | --- | --- | --- |
| `magazzino/test-fn-posta-inventario-v1` | app | il verbo (7) | l'operatore riceve l'azione con l'helper |
| `magazzino/test-fn-posta-rettifica-v1` | app | il verbo (6) | idem |
| `magazzino/test-vw-disponibilita-v1` | app | il verbo (2), per costruire giacenza | idem |
| `magazzino/test-capability-documenti-interni-v1` | app | il verbo (2) | idem |
| `dbops/test-sorgenti-orfane-v1` | **owner** | il verbo (1) | idem: anche da owner il verbo chiede identità e azione (il BB non fa eccezioni per il proprietario) |
| `magazzino/test-fn-scrivi-movimento-controlli-v1` | app | la primitiva (21) | ⇒ **owner**, forma 3. ⚠️ Dice di sé «la RLS filtra le letture del test»: da owner le letture **non** sono filtrate, quindi ogni asserzione che conta righe va riletta |
| `magazzino/test-fn-scrivi-movimento-disponibilita-v1` | app | la primitiva (11) | ⇒ owner, forma 3 |
| `magazzino/test-fn-scrivi-movimento-valore-v1` | app | la primitiva (8) e il ricalcolo (2) | ⇒ owner, forma 3 |
| `magazzino/test-fn-scrivi-movimento-seriali-v1` | app | la primitiva (6) | ⇒ owner, forma 3 |
| `magazzino/test-valore-giacenza-forma-v1` | app | la primitiva (5), per costruire | ✅ fatto (P-5 B): giacenza costruita **coi verbi**, resta app — le sue asserzioni sono sulle **viste**, che hanno senso lette sotto RLS |
| `magazzino/test-porta-ledger-v1` | app | la primitiva (3) e il ricalcolo (1) | **si riscrive**, vedi sotto |
| `magazzino/test-valore-giacenza-divergenza-owner-v1` | owner | primitiva e ricalcolo | invariato: il proprietario esegue sempre |
| `script/test-rubinetto-primo-motivo-v1` | app | nessuna chiamata (solo commenti) | invariato, **se** i verbi riscritti tengono le stesse chiamate a `fn_raise_primo_motivo_se_presente` |
| `script/test-permessi-funzioni-risoluzione`, `script/test-fn-resolve-regression-operatore` | — | `fn_resolve_livello_oggetto` | da rileggere per il passo 0 (§2.4) |

**`test-porta-ledger-v1`, i quattro test che cambiano soggetto:**

| Test | Oggi | Dopo |
| --- | --- | --- |
| 7 | «lo stesso movimento attraverso la primitiva passa» | attraverso il **verbo** passa; la primitiva chiamata dall'app ⇒ `42501` |
| 12 | primitiva su un magazzino di un altro emittente ⇒ `E_SCOPE_EMITTENTE` | verbo su un documento di un altro emittente ⇒ `E_MAG_DOCUMENTO_NON_TROVATO` |
| 13 | primitiva senza identità ⇒ `E_SCOPE_SENZA_UTENTE` | verbo senza identità ⇒ `E_PERMESSO_NEGATO` |
| 14 | ricalcolo senza identità ⇒ `E_SCOPE_SENZA_UTENTE` | ricalcolo chiamato dall'app ⇒ `42501` |

⚠️ **Una prova che si perde, e va dichiarata.** I test 12 e 13 di oggi sono
l'**unica prova di comportamento** del ramo «dentro una DEFINER» del guard BB
(C1 del Lotto 2). Dopo il cambio quel ramo resta **la rete** sotto i verbi, ma
l'app non lo raggiunge più: il verbo ferma prima sia il fuori perimetro sia la
sessione senza identità. E da owner non si esercita, perché lì
`current_user = session_user`. Resta la prova **strutturale** (test 11: il guard
è montato). Il ramo tornerà provabile col primo verbo che scrive su una tabella
col guard **senza** un filtro proprio (il verbo generico del pannello, D-3).

Da riprendere per `fn_guard_azione`: i due presìdi trasversali per le funzioni
plpgsql nuove.

### 3.3 Il presidio della copia del valore

`dbops.vw_magazzino_valore_giacenza_divergente` (`presidi.csv`) indica come
rimedio `fn_ricalcola_valore_giacenza`. Dopo la riserva lo esegue **solo il
proprietario**: il testo del rimedio va aggiornato per dirlo. Nessun pulsante
dell'interfaccia lo chiama (verificato: il backend non la nomina).

## 4. Aperto — decisione a Tid

**D-V1 — La porta `POSTED` si apre con una GUC che l'app può impostare da sola.**
Il documento passa a `POSTED` solo se la GUC transazionale
`zeroerp.magazzino_posting_<tipo>` è valorizzata (D-L2-h), e oggi la imposta
l'operazione. Ma l'app ha `UPDATE` sui documenti e può fare `set_config` da sé:
potrebbe segnare un inventario come registrato **senza movimenti** e senza il
permesso. I verbi non chiudono questo buco. Due strade:

* **A** — il guard di transizione accetta il passaggio a `POSTED` solo **dentro un
  verbo**, cioè quando la scrittura avviene come proprietario, al posto della GUC;
* **B** — la colonna di stato dei documenti si chiude all'app (`REVOKE UPDATE` per
  colonna). ⚠️ Il loop dei grant annulla un `REVOKE` per colonna: va aggiunta la
  forma per colonna in tre sedi.

Raccomandazione: **A**, perché resta tutto nel guard che esiste già. Non blocca
P-1…P-5: si può decidere dopo.

## 5. I passi

| Passo | Cosa |
| --- | --- |
| **P-0** | ✅ **Eseguito il 2026-09-24** — riquadro §5.1 |
| **P-1** | ✅ **Applicato il 2026-09-24 (22:36).** Scritto e provato lo stesso giorno. `20_code/script/20260924-38-create-fn-guard-azione` e `20_code/dbops/20260924-39-create-fn-pgtap-concedi-azione`, con le due pagine `manual/`. Il nome è `fn_guard_azione` e non `fn_require_azione`: le linee guida (§5) chiamano `fn_guard_*` una funzione che blocca sollevando. `%TYPE` in firma, `DECLARE` e `RETURNS`. **Prova dell'SQL estratto** su `zeroerp_ci` come `zeroerp`, in transazione annullata (nessun oggetto rimasto): azione inesistente → `E_CONFIG_MANCANTE`; utente NULL, operatore senza azione, contesto `CLIENTE_PORTALE` → `E_PERMESSO_NEGATO`; azione concessa → passa; seconda concessione idempotente (una riga); helper con azione inesistente → `RAISE`; `plpgsql_check_function` a zero errori su entrambe. Presìdi trasversali: nessuna delle due chiama `fn_raise_primo_motivo_se_presente`, quindi il conteggio di `test-rubinetto-primo-motivo-v1` non si sposta. ⚠️ Non provato **come app**: la DDL vuole il proprietario. Lo diranno i pgTAP di P-5 |
| **P-2** | ✅ **Applicato il 2026-09-24 (22:44).** Scritto e provato lo stesso giorno. `20_code/script/20260924-40-update-fn-resolve-livello-oggetto-gate-contesto`: passo 0 identico a `fn_resolve_livello_area`, firma invariata (nomi e tipi sciolti uguali, `CREATE OR REPLACE` senza DROP), `%TYPE` in firma, `DECLARE` e `RETURNS`, rollback col corpo di prima. **Era una dimenticanza, non una scelta**: `20260421-04` dichiarava «i 4 resolver» e questa non c'era. **Prova dell'SQL estratto** su `zeroerp_ci`, in transazione annullata, con l'impronta della funzione confrontata prima e dopo (invariata). Operatore di fixture con override `LETTURA` su un oggetto: **prima** in veste `CLIENTE_PORTALE` → `LETTURA` (il difetto, riprodotto); **dopo** → `BLOCCATO`; in veste `OPERATORE` → `LETTURA` (override) e fallback uguale al livello d'area; GUC vuota → `LETTURA` (legacy invariato); `plpgsql_check` a zero errori; il rollback dello YAML rimette il comportamento di prima. I due pgTAP della funzione girano in contesto OPERATORE: il passo 0 non li sposta |
| **P-3** | ✅ **Applicato il 2026-09-24 (22:55).** Scritto e provato lo stesso giorno. `20_code/magazzino/20260924-41-update-fn-posta-inventario-e-rettifica-verbi`, un changeSet per le due funzioni (come `20260918-23`, che le creò). Corpi di partenza dalla doc auto-generata, **verificata uguale** a `pg_get_functiondef` su dbdev; il changeSet è **generato** da quei corpi con quattro sostituzioni controllate (guard al passo 0; DEFINER con `search_path = pg_catalog, public, pg_temp`; predicato di perimetro nella `WHERE` del `FOR UPDATE`; `%TYPE` in firma e `RETURNS TABLE`), nient'altro. Firma sciolta invariata (`bigint` → `TABLE(bigint, bigint, numeric)`): `CREATE OR REPLACE`, proprietario e privilegi restano. **Prova dell'SQL estratto dallo YAML** su `zeroerp_ci`, come proprietario, in transazione annullata, impronte delle funzioni prima = dopo: senza azione → `E_PERMESSO_NEGATO`; inventario di un altro emittente → «Documento N non trovato»; inventario e rettifica propri registrati (movimenti scritti, testata `POSTED`); già `POSTED` → il rifiuto di prima; senza identità → `E_PERMESSO_NEGATO`; id 0 → la validazione di prima; `plpgsql_check` a zero errori. ⭐ **Il pin del `search_path` non rompe niente**: i trigger dei documenti e le funzioni chiamate (piano, check condivise, helper di sollevamento) funzionano col percorso bloccato. Il **rollback dello YAML** rimette le due funzioni con l'impronta identica a quella di prima. ⚠️ **Non provato**: come app (lo scratch non consente `SET ROLE`), e l'assenza di lock sul documento altrui, che è argomentata dalla forma (il predicato è nella stessa `WHERE` del `FOR UPDATE`), non misurata. Li coprono i pgTAP di P-5 |
| **P-4** | ✅ **Applicato il 2026-09-24 (23:35), pgTAP verdi.** Scritto e provato lo stesso giorno. Tre sedi: `90_end/20260924-42-revoke-app-execute-primitiva-magazzino` (forward, `REVOKE EXECUTE … FROM PUBLIC, zeroerp_app` su tutti gli overload letti dal catalogo, i verbi ri-concessi; rollback che riapre), le due voci in `v_fn_riservate` del loop `90_end/ci_apply/20260205-41`, il blocco «LA PORTA SULLE FUNZIONI» in `scripts/sql/provision_db_roles.sql`. **Prova** su `zeroerp_ci` in transazione annullata: prima `(t,t)`; dopo il forward primitiva e ricalcolo `(f,f)`, verbi `(t,t)`, ACL senza `PUBLIC` né app; il rollback li riapre; il blocco del provisioning li richiude; il **loop completo** estratto dallo YAML li chiude (e la chiusura dell'audit resta). Scratch intatto |
| **P-5** | ✅ **Parte A verde sul runner di Tid il 2026-09-24, nessuna regressione.** Scritta e provata lo stesso giorno — è la parte che non dipende da P-4:
• **due pgTAP nuovi**: `script/test-fn-guard-azione-v1` (9: il guard e il gate per oggetto, §3.1 punti 1-4, 6, 7) e `magazzino/test-verbi-permesso-v1` (11: permesso, perimetro con due emittenti costruiti, chi agisce, caso felice, forma);
• **cinque pgTAP adeguati** con `dbops.fn_pgtap_concedi_azione` subito dopo il contesto: `test-fn-posta-inventario-v1`, `test-fn-posta-rettifica-v1`, `test-vw-disponibilita-v1`, `test-capability-documenti-interni-v1`, `dbops/test-sorgenti-orfane-v1`. ⚠️ **Nella versione committata questi cinque sono rossi** da quando `-41` è applicato (controprova: la versione `HEAD` di `test-fn-posta-rettifica-v1` muore nel fixture con `E_PERMESSO_NEGATO`). Le versioni nel working tree sono verdi: vanno nello stesso commit dei changeSet, o la CI li vede rossi.
**Prova senza runner** (regola: i pgTAP li lancia Tid): ogni file concatenato all'SQL estratto di `-40` e `-41` (che mancano allo scratch) in **una** transazione annullata su `zeroerp_ci`, come proprietario — **70/70 verdi** (9 + 11 + 17 + 6 + 7 + 14 + 6), scratch intatto. ⚠️ Da proprietario la RLS non filtra: il perimetro dei casi 4-6 lo prova il predicato del verbo, non la policy; la corsa come app è di Tid.
✅ **Parte B verde sul runner di Tid il 2026-09-24, dopo l'apply di P-4.** Scritta e provata lo stesso giorno:
• `test-porta-ledger-v1` (16 → **18**): 7 = primitiva dall'app → `42501`; 12 = verbo su un inventario dell'altro emittente → non trovato; 13 = verbo senza identità → `E_PERMESSO_NEGATO`; 14 = verbo nel perimetro → passa; 17 = primitiva e ricalcolo non eseguibili dall'app; 18 = verbi eseguibili. In testa la prova persa del ramo DEFINER del guard (§3.2);
• `test-valore-giacenza-forma-v1`: la giacenza si costruisce **coi verbi** (stessi movimenti, stessi valori attesi) e il test **resta come app** — la strada preferita in §3.2, fatta;
• `test-fn-scrivi-movimento-{controlli,disponibilita,valore,seriali}-v1` al runner **`owner`** con motivo (forma 3); in `controlli` corretta la frase «la RLS filtra le letture del test».
**Prova** su `zeroerp_ci` come proprietario, concatenati all'SQL estratto di `-40`, `-41`, `-42`: i quattro della primitiva 25 + 9 + 10 + 5 verdi; `test-valore-giacenza-forma-v1` 12/12 coi verbi; `test-porta-ledger-v1` 14/18 — i quattro rossi sono **4, 5, 6, 7**, le asserzioni di comportamento che valgono solo come app (4-6 lo erano già prima). La corsa come app è di Tid |
| **P-6** | ✅ **Scritto il 2026-09-24, CSV NON applicato.** `80_data/sql/dbops/presidi.csv`, riga di `dbops.vw_magazzino_valore_giacenza_divergente`: la nota dice che la primitiva la raggiungono solo i verbi e che il rimedio (`fn_ricalcola_valore_giacenza`) lo esegue il **proprietario**. Una riga cambiata, CSV ricontrollato (47 righe, 11 colonne, LF), nessun test o documento ne fissa il testo; arriva al DB coi due mirror `runOnChange` (`20260910-08`, `-35`, chiave `vista`). Il `COMMENT` della vista («il rimedio è fn_ricalcola_valore_giacenza») resta vero e non si tocca: un changeSet solo per aggiungere chi lo esegue non vale il costo. `PROJECT_CONTEXT`: il modello come regola dei domini nuovi, col primo caso chiuso. Stato nel brief del modello e nota in D-L2-b del Lotto 2: già scritti |

### 5.1 Riquadro P-0 — i censimenti del 2026-09-24

Letti dalla doc auto-generata, dal catalogo di dbdev (come `zeroerp_app`) e dal
repo.

1. **I corpi dei due verbi** (doc auto-generata): prendono la testata con
   `SELECT … FOR UPDATE` «sotto RLS» e ricadono su `E_MAG_DOCUMENTO_NON_TROVATO`
   se non la trovano. È lì che entra il predicato di perimetro (§2.2 punto 3).
   Il resto del corpo non cambia: la check condivisa, la sorgente, la GUC di
   `POSTED`, il ciclo sul piano o sulle righe, la testata a `POSTED`.
2. **Chi chiama la primitiva e il ricalcolo**: a DB solo le due operazioni
   (`pg_proc.prosrc`). Il backend li nomina solo nei commenti e nei cataloghi di
   errore, e chiama solo `fn_posta_*` (`magazzino_repository.py`,
   `famiglie.py`). Nessuno script, nessun job; il presidio della copia li nomina
   come rimedio (§3.3). ⇒ La riserva non rompe nessun chiamante.
3. **L'azione**: `registra_magazzino` esiste (id 36, area Magazzino) ed è il
   `post_permission` di entrambi gli endpoint.
4. **Il perimetro dei documenti**: le quattro tabelle hanno RLS
   (`fn_scope_ef_whitelist_via_magazzino`) e nessun guard di perimetro.
   L'audit usa `app.jwt_user`, lo storico `current_user` (§2.2 punto 6).
5. **Il codice di errore**: `E_PERMESSO_NEGATO` è registrato (classe
   `NON_PERMESSO`) e il backend lo usa già. Nessun codice nuovo.
6. **La postura**: `v_fn_riservate` esiste nel loop dei grant e nel
   provisioning; la revoca va anche a `PUBLIC`.
7. **I pgTAP**: tredici file, §3.2. Quattro test di `test-porta-ledger-v1`
   cambiano soggetto, e la prova di comportamento del ramo DEFINER del guard si
   perde (dichiarato). Serve un helper di fixture per concedere l'azione.

## 6. Ricadute sul backend

* **Nessun cambio di codice**: il backend chiama già solo le due operazioni, con
  `post_permission = "registra_magazzino"`.
* **Richiesta**: censire i test Django che registrano un inventario o una
  rettifica con un utente **senza** l'azione e **non** super admin. Oggi passano
  perché il DB non controlla; dopo ricevono `E_PERMESSO_NEGATO`, ed è giusto così.
  Si correggono i fixture, non il DB.

---

## Registro

| Data | Chi | Cosa |
| --- | --- | --- |
| 2026-09-24 | DB | Brief scritto dalla D-4. Rispetto alla D-4 come era stata esposta: le «azioni nuove» non servono, perché `registra_magazzino` esiste ed è già il gate del backend |
| 2026-09-24 | DB | **P-0 eseguito** (§5.1). Tre correzioni al disegno: il perimetro entra nella `WHERE` del `FOR UPDATE`, non dopo; serve l'helper `fn_pgtap_concedi_azione`; `test-porta-ledger-v1` cambia soggetto in quattro test, e il ramo DEFINER del guard perde la sua prova di comportamento (dichiarato in §3.2). Emersi anche l'autore nello storico (§2.2 punto 6) e il rimedio del presidio (§3.3) |
| 2026-09-24 | DB | **P-1 scritto e provato** (`20260924-38`, `-39`, non applicati). Rinominato il BB in `fn_guard_azione` (linee-guida-sql §5: chi blocca è `fn_guard_*`); `%TYPE` in firma, `DECLARE` e `RETURNS` (regola di Tid, ricordata lo stesso giorno) |
| 2026-09-24 | DB | **P-2 scritto e provato** (`20260924-40`, non applicato): il gate mancava per dimenticanza (`20260421-04`, «i 4 resolver»); difetto riprodotto prima e sparito dopo. Emersa e dichiarata, non toccata: `fn_get_user_object_permissions_map` senza gate e senza consumatori nel backend (§2.4) |
| 2026-09-24 | Tid | P-1 e P-2 applicati su dbdev (`-38`, `-39`, `-40` `EXECUTED`; lo scratch `zeroerp_ci` ha `-38`, `-39`) |
| 2026-09-24 | DB | **P-3 scritto e provato** (`20260924-41`, non applicato): i due verbi, generati dai corpi della doc auto-generata con quattro sostituzioni controllate; scenari e rollback provati con l'SQL estratto dallo YAML |
| 2026-09-24 | Tid | P-3 applicato (`-41` `EXECUTED` alle 22:55). P-4 non era ancora scritto |
| 2026-09-24 | DB | **P-5 parte A**: due pgTAP nuovi (`test-fn-guard-azione-v1`, `test-verbi-permesso-v1`), cinque adeguati con `fn_pgtap_concedi_azione`; 70/70 verdi senza runner, concatenati all'SQL estratto in transazione annullata. Controprova: la versione committata di un test adeguato è rossa con i verbi applicati. Parte B rinviata a dopo P-4 |
| 2026-09-24 (sera) | Tid | `ci_apply` rilanciato; pgTAP della parte A lanciati: **nessuna regressione**. Stato riscritto in testa: P-0 → P-3 applicati, P-5 A verde, P-4 da scrivere |
| 2026-09-24 (notte) | DB | **P-4 e P-5 parte B scritti e provati** (non applicati): forward `-42`, voci nel loop e nel provisioning; porta riscritta (18), viste costruite coi verbi, quattro test della primitiva a `owner`. Il presidio delle funzioni riservate è `test-porta-ledger-v1`, non il pgTAP dei registri (§2.3 corretto). Dichiarato fuori: `EXECUTE` esplicito del ruolo batch di fatturazione |
| 2026-09-24 (notte) | Tid | `-42` applicato (23:35), pgTAP della parte B lanciati: **verdi**. Verificato su dbdev: verbi eseguibili dall'app, primitiva e ricalcolo no. La porta è chiusa; restano P-6 e D-V1 |
| 2026-09-24 (notte) | DB | **P-6 scritto**: nota del presidio in `presidi.csv` (una riga, da applicare coi mirror), il modello in `PROJECT_CONTEXT`. Il `COMMENT` della vista resta com'è, perché è vero. Resta D-V1 |
