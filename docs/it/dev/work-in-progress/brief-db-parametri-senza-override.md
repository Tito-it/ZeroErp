# Brief DB — I parametri che non ammettono override

## ⏭️ Chi riparte — aggiornato al 2026-10-25

**Riparte: il BE**, con la richiesta di §5.2 (BE-1…BE-3, poi FE-1 e FE-2). Il giro DB è applicato
e verde (Tid, 2026-10-25, §6.4).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB | Ricognizione e proposta | §1-§3 | — |
| 2 | ✅ **Tid** | D-1 (la colonna) e D-2 (`login_*`, `tx_id_bypass_enabled`, `attivita_fatturabili_require_commessa` senza override), 2026-10-24 | §4 | 1 |
| 2-bis | ✅ **Tid** | D-2-bis: `dati_societari_default_*` con override per emittente (2026-10-24) | §4 | 1 |
| 2-ter | ✅ team DB | Verifica contro le decisioni già prese e la documentazione (2026-10-25) | §2.4 | 2-bis |
| 2-quater | ✅ **Tid** | D-3 (a: un CSV solo) e D-4 (emittente dalla sessione), 2026-10-25 | §4 | 2-ter |
| 3 | ✅ team DB | ChangeSet, CSV, pgTAP, guida (2026-10-25) | §5, §6 | il via |
| 4 | ✅ **Tid** | Apply e corsa pgTAP: verdi (2026-10-25) | §6.4 | 3 |
| 5 | **BE / FE** | BE-1…BE-3 (lista, codici, i due test Django), FE-1 e FE-2 (form override, default societari) | §5.2 | 4 |
| 6 | **Tid** | Archiviazione in `work-done/` | — | 5 |

Decisioni aperte di Tid: **nessuna** (gli scostamenti di §6.2 sono applicati così). Lavoro da
committare: tutto il giro DB (§6.1), questo brief e la guida
[Configurazione e gestione parametri](../../guide/configurazione-e-gestione-parametri.md).
⚠️ Finché il BE non fa BE-3, due test Django sono rossi per costruzione.

**Brief vicini verificati (2026-10-24):** nessuno sul tema. Nominano le stesse tabelle
[valutazione-modello-di-dominio-db](valutazione-modello-di-dominio-db.md) (i timestamp delle due
tabelle, V-1, già chiuso) e
[analisi-pratiche-valutazione-stato](analisi-pratiche-valutazione-stato.md) (gli override come
modello per le definizioni di workflow): parlano d'altro. Il tema nasce dalla verifica della guida
richiesta da Tid il 2026-10-24.

---

## 1. Il problema

`config.parameters` contiene **due famiglie** di parametri, e il modello ne conosce una sola.

* **Con override**: il valore può cambiare per utente, categoria cliente, gruppo, emittente,
  sessione o funzione. Si legge con `script.fn_get_parameter_full`, che applica la cascata.
* **Senza override**: il valore deve essere **uguale per tutti**, perché un override darebbe allo
  stesso documento valori diversi a seconda di chi lo genera. Lo legge dal default la funzione
  che possiede la regola, e la descrizione del parametro lo dichiara: «NON si legge via
  `script.fn_get_parameter_full` e non si sovrascrive in `config.parameter_overrides`».

La seconda famiglia esiste **solo come testo** nella descrizione. Il database non lo sa, e quindi:

1. **un override su un parametro senza override viene accettato e poi ignorato in silenzio.** Chi
   lo scrive crede di aver cambiato il fuso orario per un'azienda, o la soglia di ripresa per un
   utente; il lettore guarda il default e l'override non agisce. Nessun errore, nessun avviso;
2. **la lista della UI admin mente.** `script.fn_list_parameters_for_user` restituisce **tutti** i
   parametri, e per ognuno calcola `resolved_value` con `fn_get_parameter_full`. Su un parametro
   senza override con un override scritto, la lista mostra come «valore effettivo» l'override,
   cioè un valore che nessuno usa;
3. **la famiglia di un parametro si scopre solo leggendo la funzione che lo legge.** Cinque
   parametri letti dal default non lo dichiarano nemmeno nella descrizione (§2.2).

Il caso esiste sul modello: la tabella degli override ammette qualunque `parameter_id`, e la
lista ne mostra tutti. Che oggi su dbdev non ci sia nessun override su questi parametri è un
fatto datato, non un argomento: il difetto è nella porta aperta.

---

## 2. Ricognizione (struttura, 2026-10-24)

### 2.1 Chi legge `config.parameters` senza la cascata

Funzioni che leggono `config.parameters` direttamente, a parte `fn_get_parameter_full`
(censimento su `pg_get_functiondef`, dbdev):

| Funzione | Parametri | Dichiarato «senza override» nella descrizione? |
| --- | --- | --- |
| `script.fn_fuso_operativo` | `SYSTEM_FUSO_ORARIO` | ✅ sì |
| `dbops.fn_idempotency_prenota` | `SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI` | ✅ sì |
| `vendite.fn_get_limite_emissione_default` | `VENDITE_LIMITE_EMISSIONE_IMMEDIATA_GIORNI`, `VENDITE_LIMITE_EMISSIONE_DIFFERITA_GIORNO_MESE` | ✅ sì |
| `script.fn_login_parametri` | `login_tetto_credenziale`, `login_attesa_base_secondi`, `login_attesa_max_secondi`, `login_blocco_minuti`, `login_max_tentativi_falliti` | ❌ no |
| `dbops.trgfn_tx_id_managed` | `tx_id_bypass_enabled` | ❌ no |
| `anagrafiche.fn_scrivi_dati_societari` | `dati_societari_default_liquidazione`, `dati_societari_default_socio_unico` | ❌ no |
| `vendite.trgfn_attivita_fatturabili_guard_commessa` | `attivita_fatturabili_require_commessa` | ❌ no |
| `config.trgfn_parameter_overrides_fk_surrogate_dispatch` | — (cerca il codice del parametro padre) | non è una lettura di valore |
| `script.fn_list_parameters_for_user` | — (tutti: è la lista) | non è una lettura di valore |

### 2.2 Che cosa dice il modello sui cinque non dichiarati

Leggono il default e ignorano gli override, come i dichiarati, ma nessuno lo ha scritto. Per
ognuno la domanda è di modello: **il valore può dipendere da chi lavora?**

* `login_*`: la protezione del login vale per la **credenziale**, da qualunque provenienza; un
  override per utente o per sessione renderebbe il tetto diverso per chi attacca. A mio avviso
  **senza override**.
* `tx_id_bypass_enabled`: un interruttore di sistema del trigger `tx_id`. **Senza override.**
* `attivita_fatturabili_require_commessa`: una regola di coerenza dei dati di fatturazione.
  **Senza override.**
* `dati_societari_default_*`: i default proposti quando si scrivono i dati societari di un
  soggetto. Qui un override per **emittente** avrebbe senso (ogni azienda propone i suoi
  default), e allora il difetto sarebbe nel lettore, non nel parametro. **Da decidere** (D-2).

### 2.2-bis Il lettore della famiglia «senza override» (2026-10-24)

Da `20261024-03` (brief-be-verifica-documentazione-api §I.11) la regola «intero positivo» dei
parametri di sistema ha una sede: `script.fn_intero_positivo_da_testo`, usata da
`fn_login_parametri` e da `dbops.fn_idempotency_soglia_secondi`. In questo giro va tenuta
presente: è il punto naturale in cui, con la colonna `ammette_override`, un lettore del default
nudo potrà verificare di non essere usato su un parametro che ammette override. Il building block
oggi riceve il testo e non il codice da leggere: se serve, il controllo si mette nei lettori, non
lì.

### 2.3 Altri debiti trovati nella stessa lettura

* La descrizione di `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL`/`_FO` cita una cascata vecchia
  («user → group → emittente → default», senza la categoria) e un guard ritirato
  (`trgfn_parameters_guard_default_tipo_soggetto_dettaglio`, sostituito dal framework
  FK-surrogata in `20260502-07`). Si corregge nel CSV, nello stesso giro.

### 2.4 Verifica contro le decisioni già prese (2026-10-25)

Richiesta da Tid: il giro non deve ripensare decisioni già prese. Ho letto i brief in
`work-done/`, le guide e il `git log -S`.

**Nessuna revoca.** Ogni punto completa una decisione esistente:

| Punto | Decisione esistente | Esito |
| --- | --- | --- |
| La famiglia «senza override» | [guida parametri](../../guide/configurazione-e-gestione-parametri.md) §«Due famiglie» (24-10), che dichiara il difetto («il database non impedisce…») | completa: la regola scritta diventa colonna |
| `SYSTEM_FUSO_ORARIO` | [un-solo-fuso-aziendale](../work-done/brief-be-db-fe-un-solo-fuso-aziendale.md) D-1: «default **nudo**, mai la cascata» | coerente |
| `login_*` | [blocco-login-per-credenziale](../work-done/brief-db-blocco-login-per-credenziale.md) §2.4: parametri «**globali** come oggi» | coerente con D-2 |
| `tx_id_bypass_enabled` | [guida tx_id](../../guide/tx_id_implementation_guide.md): «bypass **globale**»; il bypass per sessione è la GUC `myapp.bypass_tx_id_check`, non un override | coerente con D-2 |
| `attivita_fatturabili_require_commessa` | [gestione-commesse-v2](../work-done/gestione-commesse-v2.md): il parametro a `true`, nessuna parola sugli override | nuovo, non contraddice |
| `dati_societari_default_*` | nessuna decisione sulla famiglia; [dati-societari-in-creazione](../work-done/brief-db-dati-societari-in-creazione.md): «hanno sempre un valore (default dai parametri)» | D-2-bis è nuova e coerente; vedi sotto |
| Lettura di un valore *proposto* con la cascata dal contesto | `script.fn_get_parameter_di_sessione` (D-13a/b, [processi-accensione-per-ambiente](../work-done/brief-db-processi-accensione-per-ambiente.md) §6.12); primo lettore `fn_stato_proposto_id` | è il precedente per D-4 |
| Lista dei parametri | [codici-sfilati-e-lista-parametri](../work-done/brief-db-codici-sfilati-e-lista-parametri.md) R-2: la lista mostra solo override di livello puro | si somma: sulle righe senza override i livelli restano NULL |

**Tre fatti che il brief non vedeva.** Sono struttura, non conteggi.

1. **`config.parameters` ha otto CSV**, con otto mirror `loadUpdateData` `runOnChange: true`:
   `parameters.csv` e sei laterali in `80_data`, più `parameters_sistema.csv` caricato da
   `70_dati_sistema` (`20260825-12`). La regola «una tabella, un CSV» (Tid, 2026-09-18) depreca
   proprio i laterali. Aggiungere la colonna li tocca tutti e li rilancia tutti nello stesso apply →
   **D-3**. Tutti i mirror dichiarano `nullValue: "NULL"`.
2. **`fn_scrivi_dati_societari` non riceve l'emittente**: la firma parte da `p_soggetto_id` e non
   ha altro contesto. I chiamanti sono `fn_scrivi_dati_societari_alla_nascita`,
   `dbops.fn_pgtap_crea_soggetto_pg` e il BE (`soggetti_repository`) → **D-4**.
3. ⚠️ **Il FE scrive i due default nel codice**: `useDatiSocietariForm.js` mette `'SU'`/`'LN'` e il
   form li manda sempre, come dice dati-societari-in-creazione. Dalla UI il parametro, override
   compreso, oggi non agisce: il verbo lo legge solo quando gli arriva `NULL`. È logica duplicata
   fra livelli e la sua ricaduta va in §5.2. Senza questa correzione, D-2-bis vale solo per i
   chiamanti DB.

In più, `config/test-parameter-overrides-fk-surrogate-dispatch-v1.sql` usa
`login_max_tentativi_falliti` come esempio di «parametro fuori registry»: col guard nuovo
risponderebbe `E_PARAMETER_OVERRIDE_NON_AMMESSO` e va spostato su un parametro con override. Gli altri
pgTAP che scrivono override non toccano la famiglia «senza override».

---

## 3. Proposta

**La famiglia diventa una colonna del catalogo**, e il database la fa rispettare.

1. `config.parameters.ammette_override boolean NOT NULL`, seminata nel CSV di ogni parametro.
   Senza `DEFAULT` nel modello: un parametro nuovo dichiara la sua famiglia, come oggi dichiara
   il suo valore (si chiede a Tid se per il backfill basta un `DEFAULT` temporaneo, tolto nello
   stesso giro).
2. **Un guard su `config.parameter_overrides`** (BEFORE INSERT/UPDATE OF `parameter_id`)
   rifiuta un override su un parametro con `ammette_override = false`, con un codice nuovo
   `E_PARAMETRO_SENZA_OVERRIDE` (DATO_ERRATO, 400; scritto poi come `E_PARAMETER_OVERRIDE_NON_AMMESSO`, §6.2): «Questo parametro vale per tutti e non si
   personalizza», con la soluzione «cambia il valore di default».
3. ⚠️ Il guard vale anche **nel verso opposto**: un parametro che passa da «con» a «senza
   override» mentre ha override vivi lascia override che nessuno legge. Il passaggio si rifiuta
   finché ne esistono (guard su `config.parameters`, UPDATE OF `ammette_override`).
4. `script.fn_list_parameters_for_user` restituisce `ammette_override` (colonna **in coda** al
   `RETURNS TABLE`: DROP + CREATE; se il BE legge le colonne per posizione o per nome si
   verifica nel censimento di §5.1, non si presume); per i parametri senza
   override le colonne dei livelli restano NULL e `resolved_value` è il default. Il FE non offre
   il form dell'override su quelle righe.
5. Le descrizioni dei parametri non devono più ripetere la regola: la colonna la dice. Il motivo
   (perché questo parametro vale per tutti) resta nella descrizione.

**Alternativa più leggera, che non propongo:** un pgTAP che presidia «nessun override sui
parametri dichiarati senza override», con l'elenco scritto nel test. Trova il difetto dopo, non
lo impedisce; e l'elenco nel test è una seconda copia della famiglia, che diverge dalla prima.

Nessun lettore cambia: chi legge il default continua a leggerlo, chi usa la cascata continua a
usarla. `fn_get_parameter_full` su un parametro senza override restituisce il default, perché
dal punto 2 in poi non può più esistere un override da trovare.

---

## 4. Decisioni di Tid

* ✅ **D-1 — La forma. Decisa da Tid il 2026-10-24: la colonna.** `ammette_override` sul
  catalogo, guard nei due versi, la lista che espone la colonna (§3). Il solo presidio pgTAP è
  scartato.
* ✅ **D-2 — La famiglia di ogni parametro. Decisa da Tid il 2026-10-24, come proposto in
  §2.2:** `login_*`, `tx_id_bypass_enabled` e `attivita_fatturabili_require_commessa` **senza
  override**, insieme ai quattro già dichiarati (`SYSTEM_FUSO_ORARIO`,
  `SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI`, i due `VENDITE_LIMITE_EMISSIONE_*`). Tutti gli altri
  parametri oggi con override restano tali.
* ✅ **D-2-bis — `dati_societari_default_*`. Decisa da Tid il 2026-10-24: con override per
  emittente.** Sono valori *proposti* a chi compila i dati societari di un soggetto, non regole
  che devono valere uguali per tutti: ogni azienda propone i suoi. Il difetto è quindi nel
  lettore: nello stesso giro `anagrafiche.fn_scrivi_dati_societari` legge i due parametri con
  `script.fn_get_parameter_full`, passando l'emittente del contesto. ⚠️ Da verificare scrivendo:
  da dove la funzione prende l'emittente (parametro, contesto di sessione o soggetto), e che i
  due parametri non siano letti anche dal BE. *(Verificato il 2026-10-25, §2.4: l'emittente non
  arriva da nessuna parte → D-4; il BE non legge i parametri, ma il FE ricopia i valori.)*
* ✅ **D-3 — Gli otto CSV di `config.parameters`** (§2.4 punto 1). **Decisa da Tid il 2026-10-25:
  (a), un CSV solo.** Il team DB verifica scrivendo se `parameters_sistema.csv` deve restare in
  `70_dati_sistema`; se deve restare lì, il motivo va scritto qui prima di procedere.
  *(Verificato il 2026-10-25: resta. Il codice di `20_code` lo legge — `fn_fuso_operativo`,
  `fn_data_operativa` nei trigger e nei DEFAULT — e su un database da zero i seed di `80_data`
  passano da quei trigger: il parametro deve esistere prima. È una ragione d'ordine, non di
  famiglia, ed è scritta nel changeSet `20260825-12`.)*
  (a) *proposta*: un CSV solo. Il principale prende le righe dei laterali, i laterali (YAML + CSV)
  si ritirano nello stesso giro, e si verifica se `SYSTEM_FUSO_ORARIO` deve restare in
  `70_dati_sistema` per un motivo di ordine (il DEFAULT `fn_data_operativa()` delle colonne,
  `20261009-55`). (b) La colonna negli otto file come sono, e l'unificazione in un brief di debito.
  Propongo (a): aggiungere la stessa colonna a otto file è proprio il momento in cui la divergenza
  fra le copie costa di più.
* ✅ **D-4 — Da dove viene l'emittente** di `fn_scrivi_dati_societari` (§2.4 punto 2). **Decisa
  da Tid il 2026-10-25: come proposto**, con `script.fn_get_parameter_di_sessione`.
  *Proposta*: `script.fn_get_parameter_di_sessione`, il BB già deciso per i valori proposti
  (D-13a/b; precedente `fn_stato_proposto_id`). La firma non cambia; senza GUC (job,
  installazione) il livello salta e resta il default. L'alternativa è un parametro emittente in
  coda alla firma: tocca il BE e i chiamanti senza aggiungere significato.

---

## 5. Il giro, dopo il via

### 5.1 DB

* `00_schema/config`: la colonna, il backfill dal CSV, il NOT NULL.
* `20_code/config`: i due guard; `fn_list_parameters_for_user` con la colonna in coda.
* `20_code/anagrafiche`: `fn_scrivi_dati_societari` legge `dati_societari_default_*` con
  `script.fn_get_parameter_di_sessione` (D-2-bis, D-4), senza cambiare firma; pgTAP con un
  override di emittente costruito e la GUC `app.current_emittente_id` impostata, più il caso
  senza GUC, che deve dare il default.
* `80_data`: un CSV solo per `config.parameters` (D-3). Le righe dei laterali passano in
  `parameters.csv`, i laterali si ritirano (YAML + CSV, nello stesso giro) e `ammette_override`
  va in coda, con la sua `- column:` nel mirror `20250715-01`. ⚠️ Prima di scrivere: ogni riga
  degli otto CSV va confrontata col DB, e va verificato che sia ancora **scrivibile** dai guard di
  oggi (il caso `DEFAULT_UTILITY` del 2026-08-25). Il mirror unico le riscrive tutte, e un CSV più
  vecchio del DB regredisce in silenzio quello che un SQL successivo aveva scritto. Il codice nuovo va in
  `codici_errore.csv`
  e `messaggi_errore.csv` (solo `it`, §6.2); le descrizioni di `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_*` (§2.3).
* pgTAP: override rifiutato su un parametro senza override (costruito con un parametro di
  prova); passaggio «con → senza» rifiutato con un override vivo, ammesso senza; la lista
  restituisce la colonna e il default come valore risolto.
* Censimento prima di scrivere: i pgTAP che inseriscono override, i chiamanti di
  `fn_list_parameters_for_user` (BE). Già noto: `test-parameter-overrides-fk-surrogate-dispatch-v1`
  passa da `login_max_tentativi_falliti` a un parametro con override (§2.4).
* Guida: la sezione «Due famiglie di parametri tabellari» passa dalla regola scritta alla
  colonna, e l'avviso «il database non impedisce…» si toglie.

### 5.2 Ricaduta BE / FE (richiesta aperta dal 2026-10-25, dopo l'apply)

* La lista dei parametri della UI admin legge `ammette_override` e non offre l'override dove è
  `false`.
* Il nuovo codice arriva dal DB come ogni errore di dominio; rigenerare policy e ripiego dei
  messaggi.
* `useDatiSocietariForm.js` non scrive più `'SU'`/`'LN'`. Lascia vuoti socio unico e liquidazione
  (il verbo prende il default con la cascata, D-2-bis) oppure li chiede al DB. Va deciso col BE
  quando si scrive la richiesta (§2.4 punto 3).

#### La richiesta, scritta il 2026-10-25 (dopo l'apply)

Elenco chiuso. Il percorso è uno: il DB rifiuta, la lista dice la famiglia, il form non offre ciò
che il DB rifiuta.

| # | Lato | Che cosa | Perché |
| --- | --- | --- | --- |
| BE-1 | BE | `config.parameters` ha la colonna `ammette_override`; `fn_list_parameters_for_user` la restituisce in coda (il repository legge per nome: nessun cambio di codice obbligato) | la lista deve dire la famiglia |
| BE-2 | BE | Due codici nuovi: `E_PARAMETER_OVERRIDE_NON_AMMESSO` (DATO_ERRATO, 400) e `E_PARAMETER_OVERRIDE_PRESENTI` (CONFLITTO_STATO). Rigenerare `error_policies_generated.py` e il ripiego dei messaggi | l'upsert di un override su un parametro che vale per tutti ora riceve un 400 dal DB |
| BE-3 | BE | ⚠️ Due test Django vanno in rosso dopo l'apply: `amm_software/tests/db/test_accessi_db.py:305` (`min(p.id)`) e `core/tests/db/test_parameter_overrides_db.py:59` (`ORDER BY id LIMIT 1`) prendono il primo parametro per id, cioè `tx_id_bypass_enabled`, che vale per tutti. Scelgono il primo con `ammette_override` | il guard rifiuta l'override che scrivono |
| FE-1 | FE | Lista parametri dell'admin: dove `ammette_override = false` niente form dell'override (il valore risolto è il default) | non offrire ciò che il DB rifiuta |
| FE-2 | FE | `useDatiSocietariForm.js`: niente `'SU'`/`'LN'` scritti nel codice; socio unico e liquidazione vuoti in creazione (li propone il DB con l'override dell'emittente), o letti dal DB | logica duplicata fra livelli: oggi dalla UI il parametro, override compreso, non agisce |

---

## 6. Il giro fatto (2026-10-25)

### 6.1 I file

| File | Che cosa |
| --- | --- |
| `00_schema/config/20261025-83-alter-parameters-add-ammette-override` | la colonna, `NOT NULL DEFAULT true` (temporaneo, §6.2) |
| `20_code/config/20261025-84-create-trgfn-parameter-overrides-guard-ammette-override` | guard sugli override, `a05`, `BEFORE INSERT OR UPDATE OF parameter_id`: rifiuta anche la riga spenta |
| `20_code/config/20261025-85-create-trgfn-parameters-guard-ammette-override` | guard inverso, `a10`, `BEFORE UPDATE OF ammette_override`: `true → false` rifiutato con override accesi o spenti |
| `20_code/script/20261025-86-recreate-fn-list-parameters-for-user-ammette-override` | DROP + CREATE, colonna in coda; corpo di partenza = vivo (`-73`) |
| `20_code/anagrafiche/20261025-87-update-fn-scrivi-dati-societari-default-con-cascata` | i due default con `fn_get_parameter_di_sessione`; escono i letterali `'SU'`/`'LN'` |
| `90_end/20261025-88-alter-parameters-ammette-override-drop-default` | via il `DEFAULT` temporaneo |
| `80_data/sql/config/parameters.csv` | le righe dei sei laterali (55 righe in tutto con `parameters_sistema.csv`), `ammette_override` in coda, descrizioni (§3 punto 5, §2.3) |
| `80_data/changelog/20250715-01` · `70_dati_sistema/20260825-12` | `- column: ammette_override` nei due mirror; intestazione e commento aggiornati |
| sei YAML e sei CSV laterali | **ritirati** (D-3): `20250717-23`, `20260429-59`, `20260430-62`, `20260520-03`, `20260826-03`, `20260925-20` |
| `codici_errore.csv`, `messaggi_errore.csv` | i due codici (id messaggi 1397, 1398) |
| pgTAP nuovo `config/test-parameters-ammette-override-v1` (21) | colonna, i due guard nei due versi, ordine col dispatcher, lista, verbo con e senza emittente in sessione |
| pgTAP ritoccati | `config/test-parameter-overrides-fk-surrogate-dispatch-v1` (caso 3 su `VENDITE_MAX_SCONTO_PCT`), `config/test-elimina-credenziale-v1` (primo parametro *con* override), e i sette che inseriscono parametri di prova (dichiarano la famiglia) |
| Guida e `dbzero/config/manual/` | guida parametri (§«Due famiglie» sulla colonna, niente elenco); `parameters`, `parameter_overrides`; pagine nuove dei due guard |

Censimento degli scrittori di `config.parameters` (struttura, 2026-10-25): nessuna funzione
inserisce; nel BE nessun `INSERT`; in `80_data` un solo `INSERT` senza la colonna,
`20260224-38` (mergiato), da cui il `DEFAULT` temporaneo.

### 6.2 Scostamenti dal testo del brief

* **I codici si chiamano `E_PARAMETER_OVERRIDE_NON_AMMESSO` e `E_PARAMETER_OVERRIDE_PRESENTI`**, non
  `E_PARAMETRO_SENZA_OVERRIDE`. `E_PARAMETER_*` è la famiglia dei codici di `config.parameters`
  (`E_PARAMETER_OVERRIDE_VALUE_INVALID`, `E_PARAMETER_DEFAULT_VALUE_INVALID`); `E_PARAMETRO_*` è
  quella degli argomenti di funzione (`E_PARAMETRO_INVALIDO`). Il secondo codice il brief non lo
  nominava, e il guard inverso ne ha bisogno. Rinominarli costa poco finché non sono applicati.
* **Il `DEFAULT` temporaneo si toglie in `90_end`, non nello stesso changeSet** (§3 punto 1
  chiedeva a Tid se bastasse un `DEFAULT` tolto nello stesso giro: resta nello stesso giro, ma in
  un'altra fase). Su un database da zero `80_data/20260224-38`, già mergiato, inserisce
  `attivita_fatturabili_require_commessa` senza la colonna con `ON CONFLICT (code)`. Il `NOT NULL`
  si giudica sulla riga proposta prima del conflitto, quindi senza `DEFAULT` il migrate si
  fermerebbe lì. È la forma di `90_end/20260929-23`.
* **Messaggi solo in `it`**: il catalogo ha l'inglese su 4 codici su 1129, e il motore ripiega su
  `it`. Il brief diceva «it/en».
* **`fn_scrivi_dati_societari` non ha più valori di riserva**: a parametro assente la cascata
  solleva `E_ERRORE_PARAMETRI_TABELLA` (fail-loud, come il fuso). I letterali `'SU'`/`'LN'` erano
  una seconda copia del valore.
* **`storicizza` nel CSV fuso**: sulle righe dei laterali il CSV dice `t` e il DB `f`. Non è
  deriva: il trigger dello storico rimette il flag a `false` dopo la prima modifica. Valori e
  descrizioni coincidevano tutti col DB (55 righe confrontate, dbdev, 2026-10-25).
* **Nessun lettore controlla la famiglia** (§2.2-bis): i guard rendono impossibile un override su
  un parametro senza override, quindi un controllo nei lettori sarebbe una seconda copia.

### 6.3 Prova prima dell'apply (dbdev, come owner, 2026-10-25)

SQL **estratto** dai sei changeSet (`changes[].sql`), inserito dopo l'unica riga `BEGIN;` di ogni
pgTAP; ogni file gira due volte, la versione di HEAD senza preludio e quella nuova col preludio.
Metro: `psql -v ON_ERROR_STOP=1`, exit, `not ok`, piano contro asserzioni eseguite.

* **75 pgTAP** che toccano parametri, override, la lista o il verbo dei dati societari (anche
  attraverso il builder `fn_pgtap_crea_soggetto_pg`): 67 verdi prima e dopo; il nuovo verde 21/21;
  6 rossi **già rossi su HEAD**, con gli stessi `not ok` nome per nome (due li ho letti: sono «rosso
  da owner, verde come app», dichiarati nei loro file). Il file a quattro transazioni
  `anagrafiche/test-soggetti-indirizzi-required` col preludio in ognuna: 9/9.
* **Presidi trasversali**: `dbops/test-riferimenti-morti-v1` (`plpgsql_check` su ogni funzione),
  `script/test-catalogo-messaggi-errore-completo`, `dbops/test-security-definer-search-path-v1`,
  `script/test-rubinetto-primo-motivo-v1`: verdi prima e dopo.
* `liquibase validate`: nessun errore. `status`: in coda i sei changeSet, i mirror di
  `config.parameters` (70 e 80) e dei cataloghi errori, più i `runAlways` soliti.
* Dopo la prova, dbdev è invariato (impronta delle due funzioni, colonna assente).

⚠️ **Che cosa la prova non copre**, e tocca alla corsa di Tid:

* il **loader** dei CSV: nella prova i valori di `ammette_override` e le righe dei cataloghi
  errori sono simulati con un `UPDATE`/`INSERT`; le `preConditions` non girano;
* la corsa **come app** (qui owner, senza RLS) e il **database da zero** (lo scratch
  `zeroerp_ruoli` con `ci-local.sh --ci-apply`): lì passano `20260224-38` col `DEFAULT`
  temporaneo e le righe fuse caricate da `20250715-01` prima del registro FK-surrogata
  (`20260520-02`), che quindi il dispatcher non valida, come già oggi `DEFAULT_IVA`;
* i due test Django di BE-3 vanno in rosso dopo l'apply finché il BE non li corregge.

### 6.4 Apply (2026-10-25)

Applicato da Tid su dbdev; corsa pgTAP verde. Nel `databasechangelog`: `20261025-83`…`-88`
`EXECUTED`, i mirror `20250715-01` e `20260825-12` `RERAN`. Sul DB: 11 parametri su 55 con
`ammette_override = false`, la colonna senza `DEFAULT`.
