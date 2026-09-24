# Brief DB — Le date di validità parlano la lingua del dominio

> **Da leggere per primo: §3, la forma (un'automazione) e §6, cosa si ritira.**
> Origine: [brief-db-fixture-che-costruiscono-giro-2.md](../work-done/brief-db-fixture-che-costruiscono-giro-2.md)
> §11, dove `anagrafiche/test-risorse-umane` t.6 ha fatto vedere per la prima
> volta chi rifiuta davvero le date invertite. Tid, 2026-09-23: *«farei il
> controllo per le date come hai suggerito»* — il guard di dominio sì;
> sull'automazione *«potremo pensarci … pensiamoci»*.
>
> ✅ **Stato 2026-09-23 sera: CHIUSO lato DB — applicato, pgTAP verdi** (Tid:
> «migrazione applicata e test verdi»). Piano confermato da Tid con le
> raccomandazioni del §8. Dieci pezzi, §10: nove changeSet (`20260923-40…-48`),
> tre righe di CSV in `80_data`, un pgTAP nuovo e sei aggiornati. Prove in §11.
> ✅ Richiesta al BE (§12) fatta il 23-09 sera, con il ritiro delle copie BE/FE.
> ✅ **Richiesta al team DB (§13): CHIUSA il 24-09 — applicata, nessuna
> regressione** (Tid: «migrazione applicata nessuna regressione»; dbdev 11:33,
> `zeroerp_ci` 11:35). Le due copie rimaste (trigger della BoM, pubblicazione dei
> template) sono ritirate in `20260924-01`/`-02`, con un CSV, un pgTAP nuovo e
> due aggiornati: §14. ⭐ **Lato DB il brief è chiuso**: la regola del periodo ha
> una sede sola, `script.trgfn_guard_date_validita`.
> ⛔ Ritirare la copia della pubblicazione **non bastava**: la ricerca delle
> versioni da chiudere costruiva un `daterange` dai due parametri, e con le date
> invertite rispondeva `22000` prima del guard (§14.1).
> ⏳ **Resta solo il BE** (§14.4): una riga di test e una rigenerazione di
> `genera_error_policies`. Poi il brief va in `work-done/`.
>
> ✅ **Applicato il 23-09 sera** su dbdev (16:43) e sullo scratch `zeroerp_ci`
> (17:06, ricostruito); corsa dei pgTAP verde (Tid). ⚠️ I nove rossi «che la CI non conosce» della corsa
> sullo scratch **non vengono da questo giro** (il guard non solleva nessuna
> delle loro frasi, nessuno dei file è stato toccato qui): sono la finestra
> differita chiusa dalla riga di contesto sul mondo vuoto, e stanno nel
> [brief del giro 2](../work-done/brief-db-fixture-che-costruiscono-giro-2.md), §11 in coda.

---

## 1. Il difetto, sul modello

Una riga con `valido_dal` e `valido_al` dichiara un periodo, e il periodo ha
una regola sola: **`valido_al` non precede `valido_dal`**. Il modello quella
regola la scrive in **tre modi diversi**, e a seconda della tabella l'operatore
che sbaglia le date legge tre cose diverse:

| Chi rifiuta | Che cosa legge l'operatore |
| --- | --- |
| un **guard di dominio** scritto dentro il guard della tabella | `E_DATA_AL_MINORE_DAL` — «Il valore della data al … è inferiore alla data dal …» |
| il **daterange** della colonna generata `validita`, calcolato **prima** dei `CHECK` | `22000` — «il limite inferiore dell'intervallo dev'essere minore o uguale del limite superiore» |
| un **`CHECK`** (dove `validita` non c'è) | `23514` — la violazione di un vincolo |

⛔ Il secondo caso è il più insidioso: la tabella ha anche il suo `CHECK` sulle
date, e sembra presidiata **da lui**. Non lo è: in **ogni** caso in cui il
`CHECK` fallirebbe (entrambe le date presenti e invertite) il `daterange`
solleva prima, e negli altri il `CHECK` passa. Il `CHECK` oggi non parla mai.

⚠️ **Il `CHECK` non è inutile, e resta** (§5). È la regola **dichiarata**,
leggibile nel catalogo e nella doc, e l'ultima difesa se un giorno
l'espressione di `validita` cambia o la colonna sparisce. Il difetto non è che
ci sia: è che l'operatore legga una frase tecnica.

---

## 2. Il censimento — lettura di struttura (2026-09-23, `zeroerp_ci`)

Tabelle con la coppia `valido_dal`/`valido_al` (`pg_attribute`, esclusi
`storico` e `pg_catalog`): **25**. Questa è una lettura del **progetto**
(colonne, vincoli, trigger), non un conteggio di righe: decide il perimetro.

| Forma | Tabelle | Chi parla oggi |
| --- | --- | --- |
| `validita` generata **+** `CHECK` **+** guard inline | `anagrafiche.billing_account` | il guard (i `BEFORE` girano prima della colonna generata) |
| `validita` generata **+** `CHECK` | `vendite.contratti`, `anagrafiche.risorse_umane`, `resellers_billing_account`, `soggetti_titoli_iva`, `tipi_ruolo_tipi_indirizzo`, `tipi_soggetto_dettaglio_tipi_indirizzo`, `utilities_tipi_ruolo`, `tipi_ruoli_nature_ammesse`, `user_override_aree`, `user_override_oggetti`, `user_override_azioni` | il `daterange` (`22000`) |
| `validita` generata, **nessun** `CHECK` | `catalogo.articoli_componenti`, `catalogo.articoli_uom_operativa`, `catalogo.unita_misura_conversioni`, `vendite.listini_versioni`, `vendite.promo_articoli`, `vendite.listini_righe_componenti`, `categorie_clienti_listini`, `documenti.template_documenti_versioni`, `documenti.template_asset` | il `daterange` (`22000`) |
| **niente** `validita`, `CHECK` **+** guard inline | `soggetti_conti_bancari`, `soggetti_ruoli_conti_bancari` | il guard |
| **niente** `validita`, solo `CHECK` | `forme_giuridiche_tipi_soggetto_dettaglio`, `identita_digitali` | il `CHECK` (`23514`) |

(Senza schema: `anagrafiche` o `config`, come da catalogo.)

⚠️ Il `CHECK` non ha sempre la stessa forma: dove `valido_dal` è nullable
porta anche `valido_dal IS NULL OR …`. Il guard deve avere la stessa
semantica: **si giudica solo quando entrambe le date ci sono**.

---

## 3. La forma — un building block montato da un'automazione

### 3.1 La funzione trigger

`script.trgfn_guard_date_validita()` — generica, senza argomenti: le colonne
si chiamano sempre `valido_dal` e `valido_al`.

* `IF NEW.valido_dal IS NOT NULL AND NEW.valido_al IS NOT NULL AND NEW.valido_al < NEW.valido_dal`
  → `script.fn_log_and_raise_error` con **`E_DATA_AL_MINORE_DAL`** (già
  registrato, classe `DATO_ERRATO`, già usato da due delle tre copie — la
  terza usava `E_DATA_FINE_NON_MAGGIORE_DI_INIZIO`, §6);
* contesto: `'campo', 'valido_al'` (il frontend accende quel campo) e la
  tabella da `TG_TABLE_SCHEMA`/`TG_TABLE_NAME`; nella frase le **due date**,
  mai nomi di colonna (linee-guida-sql §5, i tre canali);
* `BEFORE INSERT OR UPDATE OF valido_dal, valido_al`, `FOR EACH ROW`: i
  `BEFORE` girano **prima** del calcolo delle colonne generate (linee-guida-sql
  §7b), quindi parla lui e non il `daterange`.

### 3.2 L'automazione — la regola nasce dalla presenza della coppia

Stesso modello del lock di `codice_interno` (linee-guida-sql §6b: *la sola
presenza della colonna provisiona il lock*): **la sola presenza di
`valido_dal` e `valido_al` monta il guard**. Una tabella nuova con un periodo
nasce presidiata senza che nessuno se ne ricordi — un elenco scritto a mano
invecchierebbe alla prima.

| Pezzo | Dove | Modello da ricalcare |
| --- | --- | --- |
| regola `DATE_VALIDITA` in `dbops.automation_rules_tbl` (`*all`/`*all`, `AUTO`, `name_template` `trg_{table}_a10_date_validita_ins_upd`, `existence_strategy` `BOTH`) | `80_data/sql/dbops/automation_rules_tbl.csv` | riga `LOCK_COLUMNS` |
| `dbops.fn_run_automations_date_validita(p_exec_mode, p_schemas, p_dry_run)` | `20_code/dbops` | `fn_run_automations_lock_columns`: stesso scope (`fn_resolve_scope`, `fn_table_in_scope`), `fn_col_exists` sulle due colonne, dry run, `fn_name_from_template` |
| la parte `DATE_VALIDITA` nel dispatcher `dbops.fn_run_automations` | `20_code/dbops` | le parti `LOCK_COLUMNS`/`ATTIVO` |
| il provisioning **subito**, non alle 21:00 | `90_end` | `20260923-03-provision-lock-iva-e-iva-stati`: un changeSet che chiama la funzione del modulo, così dopo il migrate i trigger ci sono già |
| il giro notturno | `85_pgagent` | il job `automations_lock_columns` (`20260905-08`) — da decidere se un job suo o una parte in più di uno esistente (§8) |

⚠️ **Le regole che valgono per ogni trigger generato**, e che si rompono solo
in CI (linee-guida-sql §11.5, e le schede in memoria):

* nessun `DROP`/`ALTER` incondizionato su questi trigger in `00_schema`/`20_code`:
  li crea l'automazione, su un database da zero ancora non ci sono;
* il nome pieno può superare i 63 caratteri ed essere troncato e hashato: il
  presidio li cerca per **funzione**, mai per nome;
* dopo un `migrate` manuale le automazioni non girano da sole: per questo c'è
  il changeSet di provisioning in `90_end`.

---

## 4. Il presidio — pgTAP

1. **Dinamico, per struttura**: per ogni tabella con la coppia di date esiste un
   trigger che esegue `script.trgfn_guard_date_validita`. Cercato per
   **funzione**, non per nome; e con la lista **letta da `pg_attribute`**, non
   scritta nel test — un presidio che elenca le tabelle è verde anche quando
   ne manca una nuova.
2. **Di comportamento**, su tre tabelle che coprono le tre forme di §2 (una con
   `validita` e `CHECK`, una con `validita` senza `CHECK`, una senza
   `validita`): date invertite → `P0001` con `E_DATA_AL_MINORE_DAL` e campo
   `valido_al`; stesso giorno → passa; una delle due date `NULL` → passa.
3. ⛔ **`anagrafiche/test-risorse-umane` t.6 va aggiornato nello stesso giro.**
   Oggi cattura solo `23514`/`22000` (è il test che ha trovato il difetto); col
   guard l'errore diventa `P0001`, e il suo `EXCEPTION` non lo prenderebbe: il
   file morirebbe. Diventa un `throws_like` sulla frase di `E_DATA_AL_MINORE_DAL`.
4. I pgTAP che oggi aspettano `23514` o `22000` sulle date vanno cercati **tutti**
   prima di scrivere (grep su `valido_al` + `23514`/`22000`/`chk_*_validita`).

---

## 5. Cosa NON entra, e perché

* ⛔ **I `CHECK` restano.** Sono la regola dichiarata e l'ultima difesa (§1).
  Il guard è ciò che parla; il `CHECK` è ciò che tiene se il guard manca.
* ⛔ **«`valido_al` richiede `valido_dal`»** (in `trgfn_billing_account_guard_normalize`)
  resta dov'è: è una regola **di quella tabella** (lì `valido_dal` è
  nullable), non della coppia.
* ⛔ **L'indice unico sul profilo SUPER_ADMIN**: decisione di Tid del
  2026-09-23, *si aspetta*.

---

## 6. Le copie da ritirare — nello STESSO giro

Regola del 2 (`AGENTS.md`): un building block accanto alle copie che
sostituisce è una terza versione della stessa regola. Tre funzioni fanno oggi
il controllo **inline** (due con `E_DATA_AL_MINORE_DAL`, una con
`E_DATA_FINE_NON_MAGGIORE_DI_INIZIO`, sotto):

| Funzione | Che cosa si toglie | Che cosa resta |
| --- | --- | --- |
| `anagrafiche.trgfn_billing_account_guard_normalize` | il ramo `ELSIF NEW.valido_al < NEW.valido_dal` (con `E_DATA_FINE_NON_MAGGIORE_DI_INIZIO`) | il ramo «`valido_al` senza `valido_dal`» |
| `anagrafiche.trgfn_soggetti_conti_bancari_guard` | il blocco «coerenza validità» | il resto del guard |
| `anagrafiche.trgfn_soggetti_ruoli_conti_bancari_guard` | il blocco «coerenza date» | il resto del guard |

⚠️ Corpi **dalla doc auto-gen**, confrontati con il `prosrc` vivo prima di
scrivere: coincidono tutti e tre (stesso md5, dbdev e `zeroerp_ci`).
⛔ **Correzione di una riga scritta in questo brief la mattina**: diceva che la doc
di `trgfn_billing_account_guard_normalize` era indietro. Non lo era: avevo cercato
`E_DATA_AL_MINORE_DAL`, e quella copia usa **un altro codice**,
`E_DATA_FINE_NON_MAGGIORE_DI_INIZIO` — la cui frase («minore **uguale**»)
prometteva una regola più stretta di quella applicata (solo `<`). Dopo il ritiro
nessuna funzione lo solleva più: è marcato `obsoleto_dal = 2026-09-23` nel CSV.

✅ **L'ordine dei rifiuti**: i guard generati si chiamano `trg_<tabella>_a10_…`,
e in ordine alfabetico precedono i trigger delle tre funzioni
(`trg_billing_account_ins_upd_guard_normalize`, `trg_soggetti_conti_bancari_ins_upd_guard`…):
con le date invertite parla il guard comune. ⚠️ **Non vale per ogni
tabella** (correzione del BE, 23-09 sera): su `catalogo.articoli_componenti`
`…_a10_block_modifica_struttura_…` viene **prima** di `…_a10_date_validita_…`
(`b` < `d`), e il suo ramo sulle date risponde per primo — §13. Sulle 25 tabelle **nessun** trigger
`BEFORE` riscrive le date (letto su `pg_trigger`/`prosrc`), quindi giudicare in
`a10` giudica i valori finali.

---

## 7. Debiti trovati per strada

* ✅ `linee-guida-sql.md` §7c punto 7 citava `script.trgfn_set_validita`, che
  **non esiste**: ora cita la colonna generata `validita`.
* ✅ **`script.trgfn_set_validita` ritirata anche dalla documentazione** (Tid,
  23-09: «va ritirata la documentazione manual»). La funzione non esiste dal
  `20260514-33` e nessuna pagina le era dedicata; la citavano come viva **undici
  pagine `manual/`** — 9 in `dbzero` (`categorie_clienti_listini`, `listini`,
  `promo_articoli`, `trgfn_promo_articoli_guard_data_driven`,
  `trgfn_listini_versioni_guard_transizione_stato`,
  `trgfn_contratti_guard_transizione_stato`, `template_documenti_versioni`,
  `fn_pubblica_template_documento_versione`, `trgfn_template_asset_protect_file`)
  e 2 in `backend` (`api_categorie_clienti_listini`, `api_promo_articoli`) —
  con due tabelle che elencavano trigger `…_a20_set_validita_ins_upd` inesistenti.
  Ora dicono che `validita` è una colonna generata e che l'ordine delle date lo
  verifica il guard comune. Corrette anche etichette e commenti di cinque pgTAP
  (esiti identici prima e dopo). ⚠️ Restano, **di proposito**: i changelog
  storici (non si toccano), i brief in `work-done/` (sono storia), la riga
  «istantanea aprile 2026» di `PROJECT_CONTEXT`, e un commento in
  `test-articoli-componenti-immutabilita` che dice cosa c'era «all'epoca».
  ✅ **Corretto anche nel codice** (Tid, 23-09): il corpo di
  `vendite.trgfn_promo_articoli_guard_data_driven` diceva «`valido_al >=
  valido_dal` è garantito da `chk_promo_articoli_date` e dal trigger
  `set_validita`» — **nessuno dei due esiste** (su `promo_articoli` l'unico
  `CHECK` è `chk_promo_articoli_tipo_variazione`). `20260923-48` riscrive solo
  quel commento: provato da owner su `zeroerp_ci`, codice identico (confronto
  senza commenti né spazi), `COMMENT ON` identico, `plpgsql_check` pulito,
  `test-promo-articoli-guard-data-driven-v1` 18/18. ✅ **Applicato il 23-09.**
* ✅ Il messaggio di `E_DATA_AL_MINORE_DAL` aveva un doppio spazio e nessuna
  `causa`/`soluzione`: corretto dal CSV.
* 🔵 `guide/automazione-db.md` §5.4 dice che `fn_name_from_template` «gestisce
  automaticamente abbreviazioni e hash» dei nomi lunghi: lo fa **solo** con il
  segnaposto `{fkhash6_if_long}`. Senza, PostgreSQL tronca il nome — due guard di
  questa automazione ne sono l'esempio. Non corretto qui: tocca tutte le regole.

---

## 8. Decisioni aperte per Tid

| # | Decisione | Raccomandata |
| - | --------- | ------------ |
| 1 | Automazione per presenza della coppia, o elenco esplicito delle 25 | ✅ **decisa il 23-09: automazione** |
| 2 | Codice: riusare `E_DATA_AL_MINORE_DAL` o conirne uno | ✅ **deciso: riusare**: è registrato, è `DATO_ERRATO`, lo usano già le tre copie, e la frase è quella giusta |
| 3 | Fase del trigger: `a10` o `a05` | ✅ **deciso: `a10`**: giudica il valore nuovo; `a05` è per i rifiuti che devono precedere gli altri (immutabilità), e qui non è il caso |
| 4 | Il giro notturno: job pgAgent suo o parte di un job esistente | ✅ **deciso: parte del job del lock** (`automations_lock_columns`): stessa natura (guard da struttura), un job in meno da sorvegliare |
| 5 | Completare `causa`/`soluzione` di `E_DATA_AL_MINORE_DAL` in questo giro | ✅ **deciso: sì, dal CSV** |

---

## 9. Ordine di lavoro

✅ Seguito tutto, il 2026-09-23 sera. Consuntivo in §10–§11.

---

## 10. Cosa è stato scritto

| Pezzo | File | Note |
| --- | --- | --- |
| la funzione trigger | `20_code/script/20260923-40-create-trgfn-guard-date-validita` | `E_DATA_AL_MINORE_DAL`, `campo` = `valido_al`, giudica solo con le due date |
| il modulo | `20_code/dbops/20260923-41-create-fn-run-automations-date-validita` | ricalca `fn_run_automations_lock_columns`; esclude `storico`; errore `E_DATE_VALIDITA` (nuovo, `TECNICO`) |
| l'orchestratore | `20_code/dbops/20260923-42-update-fn-run-automations-parte-date-validita` | parte `DATE_VALIDITA`, anche nel default e sotto `TABLE_RULES`; nessun chiamante usa il default |
| le tre copie ritirate | `20_code/anagrafiche/20260923-43…-45` | §6 |
| il giro notturno | `20_code/maintenance/20260923-46-update-proc-automations-lock-columns-job-date-validita` | una riga in più nel job del lock (§8.4) |
| la rete a ogni migrate | `90_end/20260923-47-converge-guard-date-validita` | sotto |
| la regola | `80_data/sql/dbops/automation_rules_tbl.csv` riga 20 | |
| i codici | `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | `E_DATE_VALIDITA` nuovo (id 1118); `E_DATA_AL_MINORE_DAL` completato; `E_DATA_FINE_NON_MAGGIORE_DI_INIZIO` dismesso |
| il pgTAP | `db/pgtap/script/test-trgfn-guard-date-validita-v1.sql` | 12 asserzioni, §4 |
| i pgTAP aggiornati | `config/test-tipi-ruoli-nature-ammesse`, `config/test-permessi-user-overrides` (×3), `anagrafiche/test-categorie-clienti-listini-v1`, `vendite/test-promo-articoli-v1`, `anagrafiche/test-risorse-umane`, `dbops/test-punti-canale-campo-v1` | i primi cinque si aspettavano `22000`; l'ultimo elencava per nome le tre copie ritirate |
| doc | `linee-guida-sql` §7b/§7c, `guide/automazione-db` §2 e §4.7 | |

⭐ **Una scelta presa scrivendo, e va detta: la rete di `90_end` è `runAlways`**,
non un changeSet che gira una volta come il `20260923-03` del lock. Il master
include `80_data`, `85_pgagent` e `90_end` **dopo** tutto l'autogen, a ogni
invocazione: un `runAlways` lì vede sempre tutte le tabelle, anche quelle di un
changeSet con data successiva, e rende vera «coppia di colonne ⇒ guard» a ogni
migrate invece che alle 21:10. Precedente: `apply_fk_index_policy` (§9 delle
linee guida). A regime non fa DDL. E **si ferma** se, finito il giro, una tabella
con le due colonne ne è ancora senza (regola disabilitata, tolta dal CSV…): un
guard che manca in silenzio è il difetto da cui nasce questo lavoro.
⚠️ Non dipende da oggetti di `ci_apply` (legge solo le colonne), quindi la
trappola «`runAlways` in `90_end` gira prima di `90_end/ci_apply`» non lo riguarda.

---

## 11. Le prove — 2026-09-23 sera

Tutte con l'**SQL estratto** dagli YAML (`yaml.safe_load`), da **owner**, in
transazione ritirata su `zeroerp_ci` (costruito da zero). ⚠️ Le righe dei CSV
sono state **rispecchiate a mano** con `INSERT`/`UPDATE` dentro la transazione:
il loader è il `loadUpdateData` `runOnChange` esistente, e lo prova l'apply.

| Prova | Esito |
| --- | --- |
| i sette changeSet di `20_code` + la rete di `90_end` | ✅ si applicano; la rete non trova tabelle scoperte |
| guard montati | **25**, uno per tabella; un secondo giro del modulo non ne aggiunge (idempotente anche sui **2** nomi troncati a 63 caratteri) |
| `test-trgfn-guard-date-validita-v1` | ✅ **12/12** |
| controprova: tolto il guard da `vendite.listini_versioni` | ✅ il t.1 diventa rosso e **nomina la tabella** |
| **prima/dopo** sui **74** pgTAP che nominano `valido_al` (stesso metro, owner) | **68 identici**, **6 diversi e tutti migliorati** — sono i file aggiornati, rossi prima perché si aspettavano già il comportamento nuovo, verdi dopo |
| `test-categorie-clienti-listini-v1` t.4 | su `zeroerp_ci` non misurabile (il file ha rossi di fixture suoi, lotto 2: pesca la categoria `SILVER` e un listino); **su dbdev**, owner, transazione ritirata: rosso prima, ✅ verde dopo |
| prima/dopo su **27 presìdi** trasversali (riferimenti morti, rubinetto, catalogo errori, automazioni, trigger) | **27 identici** |
| codici dismessi (`test-codici-errore-obsoleto-dal`, catalogo messaggi completo) | ✅ identici prima e dopo |
| cancelli statici (runOnChange, letterali, preCondition su 80_data, DDL su trigger di automazione, GRANT batch, timestamp, preambolo pgTAP, classi, i18n) | ✅ tutti; debito `throws_ok` invariato a 119 |

⛔ **Cosa queste prove NON dicono**: il verso RLS dei pgTAP (girano da owner;
il guard non legge tabelle, quindi non ha una faccia RLS sua, ma i file che lo
attraversano sì) e il giro notturno (la procedura è provata compilando, non
eseguendo il job). Li dice la corsa dopo l'apply.

✅ **La corsa dopo l'apply (Tid, 23-09 sera): verde.** I nove rossi «che la CI
non conosce» usciti sullo scratch nella prima corsa non erano di questo giro
(vedi la nota in testata): sanati nel brief del giro 2, e verdi anche loro.

---

## 12. Richiesta al backend

`E_DATE_VALIDITA` è un codice nuovo, classe `TECNICO`: va rigenerato in
`backend/apps/core/services/error_policies_generated.py` (e nei ripieghi, se il
generatore li produce). Nessun operatore lo vede: lo solleva l'automazione
quando non riesce a montare un trigger. `E_DATA_AL_MINORE_DAL` il BE lo conosce
già (`highlight_form_fields`). `E_DATA_FINE_NON_MAGGIORE_DI_INIZIO` resta nelle
due mappe del BE, ma dal 23-09 il database non lo solleva più.

✅ **Fatto lato BE, 2026-09-23**: `genera_error_policies` rigenerato (`--check`
pulito, nessuna classe cambiata: entrano `E_DATE_VALIDITA` `TECNICO` e il ritiro
di `E_DATA_FINE_NON_MAGGIORE_DI_INIZIO`); ripiego senza `%s` per
`E_DATE_VALIDITA` in `error_messages_fallback.py`. Il ritirato resta nelle mappe
(il diario lo contiene). Corretti due commenti di `vendite/db/listini_repository.py`
che citavano l'errore del `daterange`. Cancelli dei codici verdi con
`ZEROERP_TEST_DB_E2E=1`.

✅ **Ritirate anche le copie del BE e del FE, 2026-09-23 sera** (Tid: «procedi
e prova ogni punto»). La regola la ripetevano, perché il DB rispondeva con la
frase del `daterange`:

| Dove | Copie | Strada dell'errore DB, ora |
| --- | --- | --- |
| `vendite/services/contratti_service.py` | 3 (create, PATCH testata, cessazione) | `raise_from_database_error`: ⚠️ riconosce solo i codici in `_KNOWN_DB_ERROR_MARKERS` — aggiunta la voce, senza sarebbe uscito `E_VENDITE_VALIDATION` |
| `vendite/services/promo_articoli_service.py` | 2 | `P0001` nudo al middleware |
| `anagrafiche/services/categorie_clienti_listini_service.py` | 2 | nudo |
| `documenti/services/template_versioni_admin_service.py` | 3 (clone, pubblica, create/update) | nudo |
| `documenti/services/template_asset_admin_service.py` | 1 (`_guard_date_range`, upload e PATCH) | nudo; l'INSERT precede la scrittura del file |
| FE `useContoBancarioForm.js` | 1 | conti del soggetto e del ruolo: `useSoggettoRuoloCollection` ora espone `campiErrati`, il form li lega |

FE: `campiErrati` legato a `valido_al` anche nel `ContrattoDrawer` (testata e
dialog di cessazione); promo, categorie, asset e pubblicazione lo legavano già.

⭐ **La prova, sul DB vero**: `backend/apps/core/tests/db/test_date_validita_guard_comune_db.py`
— mondo costruito coi BB `dbops.fn_pgtap_crea_*`, transazione annullata, ogni
punto chiamato **dal service** e il rifiuto passato da
`ErrorTranslator.to_api_error` (il traduttore del middleware): codice, campo
`valido_al`, status 400, `highlight_form_fields`. **15 punti, 6 test, verdi.**
Controprova: rinominata la voce dei marker dei contratti, i suoi tre punti
diventano rossi. I test unitari che provavano le copie ora provano il
contrario — che il service **passa** le date invertite al repository.

---

## 13. Richiesta al team DB — le copie rimaste nel database

> 🔢 **Progressivi (2026-09-24):** i changeSet di questa richiesta, se cadono
> il 24-09, stanno in `20260924-01` … `-19`. `-20…-39` sono riservati a
> [brief-db-preventivi-congelamento-pricing.md](brief-db-preventivi-congelamento-pricing.md).

La prova qui sopra ne ha trovata una che il censimento del §2 non poteva vedere
(guardava i trigger, non le funzioni che validano i propri parametri). Letto
poi sulla doc auto-generata, cercando il confronto fra le due date:

| Funzione | Che cosa fa | Proposta |
| --- | --- | --- |
| `documenti.fn_pubblica_template_documento_versione` | `p_valido_al < p_valido_dal` → `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO` (campo `valido_al`), prima dell'UPDATE | ✅ **applicato il 24-09, `20260924-02`** (§14). ⛔ **copia**: ritirare quel ramo — l'UPDATE incontra il guard comune. ⚠️ Non bastava: vedi §14.1. Il codice resta per gli altri rami (id, `valido_dal` nullo). Il test BE asserisce oggi il codice vecchio **dichiarandolo**, e va rosso il giorno del ritiro: si aggiorna togliendo `codice=` |
| `catalogo.trgfn_articoli_componenti_block_modifica_struttura` | su UPDATE, `NEW.valido_al < OLD.valido_dal` → `E_BOM_VALIDO_AL_INVALIDO` (campo `valido_al`) | ✅ **applicato il 24-09, `20260924-01`** (§14). ⛔ **copia — da ritirare (Tid, 23-09: «va risolto»)**. Verificato su `pg_constraint`: `chk_articoli_componenti_valid_dates`, che il commento cita come `CHECK` stretto, **non esiste** (la tabella ha solo `coeff_qta_pos`, `no_selfref`, `note_target_tipo`): la regola è la stessa del guard comune, con un altro codice. ⚠️ E **non è codice morto**: `…_a10_block_modifica_struttura_…` precede in ordine alfabetico `…_a10_date_validita_…`, quindi oggi sulla BoM risponde lui. Da fare: togliere il ramo (e il suo commento), `E_BOM_VALIDO_AL_INVALIDO` → `obsoleto_dal` nel CSV (nessun'altra funzione lo solleva), aggiornare `catalogo/test-articoli-componenti-immutabilita` e `dbops/test-punti-canale-campo-v1` che lo nominano. Lato BE: il codice sta solo nelle mappe, e ritirato ci resta per il diario — ⚠️ ma le **note** del file generato cambiano, quindi serve la rigenerazione (§14.4) |
| `vendite.fn_chiudi_contratto_per_successione` | `v_old.valido_dal > p_nuovo_valido_dal - 1` → `E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA` | ✅ **non è una copia**: giudica una data CALCOLATA e parla della successione (col numero del contratto). Resta |

✅ Nota BE, non per il DB — **risolta il 23-09 sera (Tid: «vai con A»)**.
`ErrorManager.raise_from_database_error` riconosceva un codice del DB solo se il
chiamante lo aveva in lista, e sul riconosciuto metteva il messaggio **del
chiamante**: col guard comune su 25 tabelle, ogni service che lo attraversava
lo trasformava nel suo fallback o in una frase generica. Ora il codice del
catalogo vince sempre, con la **sua** frase; marker e messaggio del chiamante
restano il ripiego dei `RAISE` diretti. Tolta la voce aggiunta ai contratti
(non serve più). Provato: il test sulle date asserisce anche le due date nella
frase, e spegnendo la frase del DB nel BB i tre punti dei contratti vanno rossi.
`pratiche_service._raise_known_db_error` non cambia: un codice non dichiarato lo
rilancia nudo, e il middleware lo traduce già così.

---

## 14. Il giro del §13 — 2026-09-24

### 14.1 ⛔ Togliere il ramo della pubblicazione non bastava

La proposta del §13 diceva *«ritirare quel ramo — l'UPDATE incontra il guard
comune»*. Letto il corpo vivo, **l'UPDATE non ci arrivava**: prima di pubblicare,
la funzione cerca le versioni PUBBLICATE da chiudere con

```text
v.validita && daterange(p_valido_dal, COALESCE(p_valido_al, 'infinity'), '[]')
```

e con le date invertite quel costruttore solleva `22000` («il limite inferiore
dell'intervallo …») — **la frase tecnica da cui è nato questo brief**. Il ramo
tolto la stava coprendo. Provato: con il solo ramo tolto, il t.1 del pgTAP nuovo
esce su quella frase.

La correzione è sul **modello**, non un ripiego: le versioni candidate partono
**prima** di `p_valido_dal`, quindi si sovrappongono alla finestra nuova se e
solo se sono ancora aperte a `p_valido_dal`. `p_valido_al` non entra nel
giudizio, e la condizione diventa `v.validita && daterange(p_valido_dal, NULL, '[)')`.
Con date valide l'insieme chiuso è lo stesso (i t.4–7 del pgTAP nuovo lo fissano,
verdi prima e dopo); con date invertite qui non si solleva niente, l'UPDATE
finale incontra il guard, e le chiusure già fatte si annullano con la
transazione (t.3).

### 14.2 Cosa è stato scritto

| Pezzo | File | Note |
| --- | --- | --- |
| il trigger della BoM | `20_code/catalogo/20260924-01-update-trgfn-articoli-componenti-block-modifica-struttura-date-al-guard-comune` | tolto il ramo `E_BOM_VALIDO_AL_INVALIDO` e il suo commento (citava un `chk_articoli_componenti_valid_dates` che non esiste). È una copia esatta: la stessa funzione vieta di cambiare `valido_dal`, quindi `OLD.valido_dal` = `NEW.valido_dal` |
| la pubblicazione | `20_code/documenti/20260924-02-update-fn-pubblica-template-documento-versione-date-al-guard-comune` | tolto il ramo; ricerca riscritta (§14.1); `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO` resta per `versione_id` e `valido_dal`. Firma, `RETURNS TABLE` e `COMMENT ON` ancorati con `%TYPE` (il corpo vivo li aveva a tipi nudi — rilievo di Tid, 24-09): identità della funzione invariata, verificato in transazione |
| i codici | `codici_errore.csv`, `messaggi_errore.csv` | `E_BOM_VALIDO_AL_INVALIDO` → `obsoleto_dal = 2026-09-24`; nota di `E_BOM_MODIFICA_VIETATA` corretta; `causa`/`soluzione` di `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO` senza più la regola sulle date |
| il pgTAP nuovo | `db/pgtap/documenti/test-fn-pubblica-template-documento-versione-v1.sql` | 7 asserzioni; la funzione **non aveva nessun pgTAP** |
| i pgTAP aggiornati | `catalogo/test-articoli-componenti-immutabilita` t.11, `dbops/test-punti-canale-campo-v1` t.1 | il t.11 era un `throws_ok(NULL, NULL)`: ora pretende la frase del guard comune. Nel t.1 esce la riga del codice ritirato; la pubblicazione **resta** (il codice vive sul ramo di `valido_dal`, con `campo`) |
| il cancello | `scripts/guardrail_pgtap_preambolo.py` | debito `throws_ok` senza discriminante 119 → **118** |
| doc | `manual/` di `trgfn_articoli_componenti_block_modifica_struttura`, `articoli_componenti`, `fn_pubblica_template_documento_versione`, `api_catalogo`; `guide/gestione-listini` | la manual della BoM diceva anche che `validita` la ricalcola «il trigger dedicato»: è una colonna generata (§7) |

Entrambi i changeSet ancorano in `preCondition` l'md5 del `prosrc` letto il 24-09
(uguale su dbdev e `zeroerp_ci`), come `20260921-44`/`-46`.

### 14.3 Le prove — 2026-09-24

SQL **estratto** dagli YAML, da owner, concatenato al corpo di ogni pgTAP in
**una** transazione ritirata su `zeroerp_ci`. Corpi vivi riletti dopo: md5
invariati sui due database.

| Prova | Esito |
| --- | --- |
| `test-fn-pubblica-template-documento-versione-v1` | prima **5/7** (t.1 esce con la frase di `E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO`, t.2 con il suo codice), dopo ✅ **7/7** |
| controprova: solo il ramo tolto, ricerca vecchia | t.1–2 rossi con `22000` — §14.1 |
| `test-articoli-componenti-immutabilita` | prima 17/18 (t.11 esce con la frase del ramo BoM), dopo ✅ **18/18** |
| `test-punti-canale-campo-v1` | ✅ 14/14 prima e dopo; controprova: col file di ieri, dopo l'apply il t.1 è rosso e nomina la riga della BoM |
| prima/dopo su **38** pgTAP (tutto `documenti/`, tutti i file che nominano `articoli_componenti`, guard comune, codici ritirati) | **38 identici**; tre rossi preesistenti, invariati e non di questo giro (`documenti-generati-eventi`, `ddt-componenti-senza-prezzo-v1`, `fn-resolve-prezzo-composito-v1`) |
| `plpgsql_check` sulle due funzioni | pulito |
| `guardrail_codice_errore_strutturato.sql`, con la riga del CSV rispecchiata | ✅ nessun codice ritirato ancora sollevato |
| cancelli statici (runOnChange, preCondition su 80_data, DDL su trigger generati, GRANT batch, letterali, timestamp, preambolo pgTAP) | ✅ |

⛔ **Cosa non dicono**: il verso RLS (da owner) e il loader dei CSV (lo prova
l'apply). Li dice la corsa dopo l'apply.

✅ **La corsa dopo l'apply (Tid, 24-09): nessuna regressione.** Applicato su
dbdev (11:33) e su `zeroerp_ci` (11:35), letto dal `databasechangelog` di
entrambi. Con questo il verso RLS e il loader dei CSV sono provati.

### 14.4 ⏳ Richiesta al BE — l'ultima cosa aperta

Verificato il 24-09 dopo l'apply: nel repository **non è ancora fatta** (il
test dichiara ancora il codice vecchio, il file generato porta ancora la nota
vecchia di `E_BOM_MODIFICA_VIETATA`).
`backend/apps/core/tests/db/test_date_validita_guard_comune_db.py`, punto
`template_versioni.pubblica`: dichiara `codice="E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO"`
e dall'apply è **rosso**. Si toglie `codice=` (torna il default,
`E_DATA_AL_MINORE_DAL`) e il commento `⏳` sopra. E una rigenerazione:
`genera_error_policies` (il file generato riporta le note dei codici, e
cambiano quelle di `E_BOM_VALIDO_AL_INVALIDO` e `E_BOM_MODIFICA_VIETATA`:
senza, il `--check` è rosso). Nessuna classe cambia. `E_BOM_VALIDO_AL_INVALIDO`
resta nelle mappe per il diario, come `E_DATA_FINE_NON_MAGGIORE_DI_INIZIO`.

---
{% include-markdown "signature-core.md" %}
