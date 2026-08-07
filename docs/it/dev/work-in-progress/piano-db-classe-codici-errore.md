# Piano DB — classe dei codici errore

**Chi:** team DB (`dev/db-tid`).
**Guida generale e ragioni di ogni scelta:** [brief-db-be-classe-codici-errore](brief-db-be-classe-codici-errore.md) — 20 decisioni, le trappole, i perché. **Questo file non le ripete: le esegue.**
**Piano gemello:** [piano-be-classe-codici-errore](piano-be-classe-codici-errore.md).
**Stato:** 🟡 **in corso** — ✅ D-1 e D-2 fatti (2026-08-07). Prossimo: **D-3** (split `E_VALIDAZIONE`) o **D-4** (le tabelle).
✅ **Vocabolario a 10 valori confermato da Tid** (2026-08-07): `NON_AUTENTICATO` e `ERRORE_ESTERNO` restano.

---

## 0. La premessa che rende possibile questo piano

**Il BE è fermo, e non serve.** Decisione di Tid (2026-08-07): si sviluppa
**tutto il DB per primo**, poi il BE. Verificato prima di accettarla — e la
verifica ha tolto l'unica dipendenza che c'era:

> Il piano originale aveva al punto 3 *«il BE genera il CSV `codice,classe` da
> `error_policies.py`»*. **Non serve il BE**: la mappa status → classe è
> deterministica e il file è nel repo. Misurato: **654 codici su 659** si
> convertono automaticamente, e i 5 che restano sono i `401`×4 e il `502`×1.
> ⚠️ Quei 5 il brief li dava «fuori dal vocabolario»: **non lo erano** — vedi il
> risultato del D-1.

Quindi: **nessun passo di questo piano attende il BE.** Il DB arriva fino in
fondo da solo, e quando il BE riparte trova il catalogo pronto e la vista da cui
generare.

⚠️ **Una conseguenza da mettere in conto, e non è un difetto.** Finché il BE non
ha il generatore, i codici **nuovi** creati qui (lo split di `E_VALIDAZIONE`, D-3)
non hanno una policy e prendono il ripiego 400 di `ErrorPolicyRegistry.resolve`.
Non è una regressione — è il comportamento di oggi per ogni codice nuovo — ma
significa che **lo split non cambia niente di visibile finché il BE non riparte**.
Va detto adesso, non scoperto collaudando.

---

## 1. La sequenza

Ordine per **dipendenza**. Il punto di non ritorno è **D-6**: fino a lì tutto è
additivo e reversibile.

| # | Passo | Dipende da | Perché lì |
|---|---|---|---|
| ✅ **D-1** | ~~Estrarre il CSV~~ **fatto** — 689 righe, 656 classificate, 33 al D-2 | — | ⚠️ ne è uscito il vocabolario a **10 valori** |
| ✅ **D-2** | ~~Le 33 decisioni residue~~ **fatto** — 33 classi, 29 ritiri, **zero righe senza classe** | D-1 | ⚠️ serviva un **terzo asse** al discriminante |
| **D-3** | ⏱ **Spezzare `E_VALIDAZIONE`** — 10 funzioni, 5 domini | — | 🔴 **prima del seed**, o il dato certifica una classe falsa |
| **D-4** | `config.classi_errore` + `config.codici_errore` (`00_schema`) | — | il DDL può nascere quando si vuole, ma serve prima del seed |
| **D-5** | Seed dei due CSV, **dentro `20260614-08`** | D-1 · D-2 · D-3 · D-4 | ⚠️ il passo che rompe la CI se fatto nel modo ovvio |
| **D-6** | 🔴 Migrazione `obsoleto_dal` + riscrittura dei **5 lettori** | D-5 | **punto di non ritorno** |
| **D-7** | FK `messaggi_errore.codice → codici_errore.codice` + seed `fk_index_policy` | D-5 | dopo che il seed regge |
| **D-8** | pgTAP: **4 da adeguare** + i nuovi | D-6 · D-7 | |
| **D-9** | Le **due viste** (`20_code`) | D-4 | ⚠️ numerazione più alta di chi dipende da loro |
| **D-10** | Vista dei **codici multidominio** — la misura | D-9 | può slittare: non blocca il BE |

**Consegna al BE:** dopo **D-9**. È il momento in cui `vw_codici_errore_identita`
esiste, è popolata e ordinata — cioè quando il generatore del BE ha da cui
generare.

---

## 2. I passi, in dettaglio

### D-1 · ✅ **FATTO** — 2026-08-07

**Consegnato:**

* [`scripts/estrai_classi_codici_errore.py`](../../../../scripts/estrai_classi_codici_errore.py)
  — bootstrap una tantum, con in testata il perché è una tantum e la trappola
  del parser;
* [`db/changelog/migrations_v2/80_data/sql/config/codici_errore.csv`](../../../../db/changelog/migrations_v2/80_data/sql/config/codici_errore.csv)
  — **689 righe**, colonne `codice,classe,obsoleto_dal,note`.

⚠️ **Il CSV nasce completo, non solo `codice,classe`** — correzione al piano
originale: `obsoleto_dal` va nel seed, perché i dati di `80_data` si cambiano
**dal CSV** e mai con `UPDATE` diretti. Le 50 date di ritiro sono già dentro,
prese dalla riga `it` del catalogo.

**L'universo è il catalogo, non le policy.** Un codice esiste se il DB può
nominarlo: 689 righe, e `PREV_STATO_NON_MODIFICABILE` (morto) resta fuori da solo,
senza bisogno di una regola apposta.

| Classe | Righe |
|---|---:|
| `DATO_ERRATO` | 234 |
| `CONFLITTO_STATO` | 223 |
| `NON_TROVATO` | 84 |
| `TECNICO` | 60 |
| **`NULL` — il lavoro del D-2** | **33** |
| `NON_PERMESSO` | 23 |
| `NON_ESEGUIBILE` | 22 |
| `NON_DISPONIBILE` | 4 |
| `NON_AUTENTICATO` | 4 |
| `AVVISO` | 1 |
| `ERRORE_ESTERNO` | 1 |
| **totale** | **689** |

#### ⚠️ I 5 «fuori vocabolario» non erano fuori — il vocabolario va a 10

Il brief dichiarava 401 e 502 «fuori dal vocabolario di dominio, da mappare a
mano nel backend». **Falso**: tutti e cinque sono righe del catalogo, quindi con
la FK vogliono un padre e con `classe NOT NULL` vogliono una classe. È lo stesso
identico caso di `AVVISO`, ed è la terza volta che si presenta.

✅ **Confermato da Tid (2026-08-07)**: `NON_AUTENTICATO` (401, 4 codici) e
`ERRORE_ESTERNO` (502, 1). Ragionamento in §4.3 del brief.

⚠️ **Il BE aveva messo quei 5 su `TECNICO`** nel proprio CSV, seguendo una
versione precedente di questo piano. Non è un conflitto: il loro status è scritto
a mano perché quei codici non passano dall'exception handler, quindi la classe a
catalogo non cambia la risposta HTTP. Le due sorgenti restano diverse su 5 righe,
e **fa fede il catalogo**.

#### ✅ Gli scarti di distribuzione, riconciliati

Le policy davano 224 `CONFLITTO_STATO` e 63 `TECNICO`, il CSV ne dà 223 e 60. **I
tre scarti sono spiegati tutti**, e la verifica valeva la pena:

| Scarto | Perché |
|---|---|
| `CONFLITTO_STATO` −1 | `PREV_STATO_NON_MODIFICABILE` (409) è morto e non è a catalogo |
| `TECNICO` −2 | `W_TXID_NOT_REGISTERED` è registrato **due volte** in `error_policies.py` (col e senza prefisso `E_`), entrambe a 500; la sua riga di catalogo è una sola e va ad `AVVISO` |
| `TECNICO` −1 | idem `MESSAGGIO_NON_DEFINITO`: due policy, una riga di catalogo |

⭐ **Scoperta collaterale:** in `error_policies.py` ci sono **tre coppie**
registrate sotto entrambi i nomi — `SEQUENZA_NON_CONFIGURATA`,
`MESSAGGIO_NON_DEFINITO`, `W_TXID_NOT_REGISTERED`. **Non è un difetto**: è la
cintura della campagna di rinomina, che tiene risolvibile il nome vecchio finché
il diario lo contiene. Va saputo perché rende il §7.2 del brief più preciso — il
BE non ha il codice «sotto un altro nome», ce l'ha **sotto tutti e due**.

---

#### 🔴 Come è stato estratto — e perché non si può più rifare

`python3 scripts/estrai_classi_codici_errore.py` legge il catalogo e
`error_policies.py`, incrocia, riscrive il CSV.

⚠️ **Non gira più, e non va riparato.** Poche ore dopo questa estrazione il BE ha
eseguito il proprio B-3: `error_policies.py` è stato diviso in quattro moduli e
**non contiene più nessun `http_status=` per codice**. La sorgente è sparita.

**Conseguenza che vale la pena scrivere:** da questo momento
`codici_errore.csv` **è** il portatore delle 659 decisioni su questo lato — non
c'è più un posto da cui ri-dedurle. Lo script resta come reperto: la mappa
`CLASSE_DA_STATUS` è l'unica forma in cui quella corrispondenza è ancora scritta
qui.

*(La finestra si è chiusa da sola, e per fortuna dopo. Se il D-1 fosse slittato
di mezza giornata, le 659 classi si sarebbero dovute chiedere al BE invece che
estrarle — che è esattamente la dipendenza che il §0 aveva appena tolto.)*

La mappa `http_status → classe` vive nella costante `CLASSE_DA_STATUS` dello
script, ed è la sola cosa da toccare se il vocabolario cambia.

⚠️ **Tre trappole già pagate, tutte e tre nel codice con il commento accanto:**

1. **il parser delimita ogni voce con la chiave successiva**, non con
   l'indentazione — **32 voci sono su una riga sola**, e un parser che cerca
   `http_status=` a inizio riga le perde. Ha già prodotto due misure sbagliate in
   questo cantiere, una delle quali ribaltava una conclusione;
2. **`W_TXID_NOT_REGISTERED` non prende la classe dalla sua policy**: dice 500
   perché nessuno l'aveva mai classificato. È un avviso → `AVVISO`, forzato;
3. **`MESSAGGIO_NON_DEFINITO` e `W_TXID_NOT_REGISTERED` hanno un gemello con
   prefisso `E_`** nelle policy: lo script accetta entrambi i nomi, ma la riga di
   catalogo — e quindi la verità — è una sola.

✅ **Verifica fatta:** 659 policy lette, 689 righe scritte, 33 senza classe (il
D-2), 50 ritirate, e i tre scarti di distribuzione riconciliati uno per uno.

---

### D-2 · 🟡 **Analisi fatta** — 30 ritiri e 3 classificazioni

⚠️ **Il discriminante a due assi del §7.1 del brief NON basta, e ha sbagliato.**
Applicandolo si concludeva che le famiglie `E_BOM_*`, `E_CONTRATTO_MODALITA_C_*`
e `E_COMPETENZA*` fossero *«progettate, non ancora agganciate»* — perché hanno
tracce nel repo e nessuna funzione viva che le solleva.

**È il contrario:** erano agganciate, e sono state **staccate** nel cantiere
«bonifica riferimenti morti» del 4-5 agosto. Le tracce non sono i resti di un
disegno da costruire: sono i resti di un disegno **rimosso**.

#### ⭐ Serve un terzo asse: *è mai stato cablato?*

| Asse | Domanda | Dove si legge |
|---|---|---|
| 1. funzioni vive che lo sollevano | è agganciato **adesso**? | doc auto-gen ⚠️ (vedi sotto) |
| 2. file del repo che lo nominano | qualcuno l'ha **pensato**? | tutto il repo |
| **3. changeSet che l'hanno definito** | è mai stato **cablato**? | `20_code` / `migrations` v1 |

Il terzo separa nettamente:

* **asse 3 > 0 e asse 1 = 0** → era vivo, non lo è più → **superato, si ritira**;
* **asse 3 = 0 e asse 2 > 0** → mai cablato → **progettato, si classifica**;
* **asse 2 = 0 e asse 3 = 0** → mai esistito → **si ritira**.

#### L'esito, 33 su 33

| Verdetto | Quanti | Chi |
|---|---:|---|
| **superati** — erano in `20_code` v2, nessuna funzione viva li solleva più | 22 | `E_BOM_*` (4), `E_CONTRATTO_MODALITA_C_*` (3), `E_COMPETENZA*` (2), `E_TXID_DBLINK_*` (2), `E_ASSOGGETTAMENTO_NO_MOD`, `E_ATTIVO_CASCADE`, `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI`, `E_DBLINK_LOG_CONN_MISSING`, `E_FONTE_QUANTITA_NON_VALIDA`, `E_PARAMETER_DEFAULT_TIPO_SOGGETTO_INVALID`, `E_PERC_IVA_NO_MOD`, `E_REFRESH_LOCK_TIMEOUT`, `E_REGOLA_FATTURAZIONE_MANCANTE`, `E_STATO_SCONOSCIUTO`, `E_TASK_RUNTIME` |
| **superati** — solo nelle migrazioni **v1**, mai portati in v2 | 4 | `E_NUMERAZIONE_IMMUTABILE`, `E_STORICIZZAZIONE`, `E_STORICO_UPD`, `E_STORICO_DLT` |
| **mai esistiti** — zero tracce ovunque | 3 | `E_INVALID_SNAPSHOT`, `E_DRYRUN_CREATE_TRIGGER`, `E_DATA_FINE_INFERIORE_DI_INIZIO` |
| **già ritirato dal BE**, vivo solo a catalogo | 1 | `E_AI_CONFIRMATION_REQUIRED` |
| ✅ **progettati mai cablati → si classificano** | 3 | i tre del push preventivo (sotto) |

**→ 30 ritiri, 3 classificazioni.**

#### I 3 che si classificano, e perché non si ritirano

Sono descritti in `docs/it/backend/vendite/manual/push_preventivo_handler.md`,
che è un documento di **disegno**: nessun Python li solleva, nessun changeSet li
ha mai cablati. Cancellarli romperebbe il lavoro di qualcun altro — è esattamente
il caso da cui mette in guardia la guida dei presidi §3.3.

| Codice | Cosa dice il disegno | Classe |
|---|---|---|
| `E_VENDITA_PARAM_MODALITA_FATTURAZIONE_INVALIDA` | «valida `modalita_fatturazione`» — parametro non valido | `DATO_ERRATO` |
| `E_VENDITA_COMPETENZA_RICHIESTA` | «`meta.competenza_fatturazione`, se assente» — dato obbligatorio mancante | `DATO_ERRATO` |
| `E_VENDITA_PREVENTIVO_GIA_PUSHATO` | «già pushato» — in conflitto con lo stato attuale | `CONFLITTO_STATO` |

#### ✅ **D-2 CHIUSO** — 33 classi assegnate, 29 ritiri, zero residui

Le 30 letture del punto che sollevava sono fatte, sui changeSet che li
definivano. **`codici_errore.csv`: 689 righe, zero senza classe.**

| | prima | dopo |
|---|---:|---:|
| righe senza classe | 33 | **0** |
| ritirati (`obsoleto_dal`) | 50 | **79** |

⚠️ **29 nuovi ritiri e non 30**: `E_STATO_SCONOSCIUTO` era già ritirato dal
cantiere precedente, e la sua data resta quella.

##### Le sette decisioni che non erano meccaniche

1. **`E_BOM_RIGA_NOT_FOUND` ha due punti** — `p_... IS NULL` e `IF NOT FOUND`,
   che chiedono 400 e 404. **Denominatore sicuro: `NON_TROVATO`**, perché il ramo
   NULL è un guard sul chiamante e non arriva da chi usa il programma: un 404 lì
   non fa danno a nessuno. Scritto in `note`.
2. **`E_FONTE_QUANTITA_NON_VALIDA` → `TECNICO`, non `DATO_ERRATO`**, e il nome
   inganna: `v_fonte` **non arriva da chi compila**, esce da
   `vendite.regole_fatturazione_articolo`. Nessuno rimedia finché qualcuno non
   riconfigura. È la quarta volta che il nome mente in questo filone.
3. **`E_REGOLA_FATTURAZIONE_MANCANTE` → `TECNICO`**: stessa lettura di
   `E_PIPELINE_NOT_FOUND`, spostato 404 → 500 nel cantiere del terzo lato. Non è
   una risorsa che manca, è un pezzo che nessuno ha configurato.
4. ⭐ **Tre codici `E_*` che erano in realtà avvisi.** `E_TXID_DBLINK_ERROR`,
   `E_TXID_DBLINK_NULL` e `E_DBLINK_LOG_CONN_MISSING` passavano da
   `fn_log_error_only` **con fallback locale**: loggavano e non sollevavano mai,
   quindi non raggiungevano nessuno. Classe **`AVVISO`**, come
   `W_TXID_NOT_REGISTERED`. Il prefisso `E_` era storico e diceva il falso —
   conferma che *la famiglia non si legge dal prefisso ma dalla funzione di log
   che si usa*.
5. **`E_ASSOGGETTAMENTO_NO_MOD` / `E_PERC_IVA_NO_MOD` / `E_NUMERAZIONE_IMMUTABILE`
   → `CONFLITTO_STATO`**: famiglia «immutabilità», allineati ai 29 che il cantiere
   precedente aveva già portato da 400 a 409.
6. **I due dell'attivazione contratto modalità C → `NON_ESEGUIBILE`**, mentre il
   trigger di riga (`_RIGA_SENZA_PREZZO`) resta `DATO_ERRATO`. La distinzione è
   *dove* si rompe: sul campo che si sta compilando, o sulla configurazione che
   non regge al momento di attivare.
7. **`E_REFRESH_LOCK_TIMEOUT` → `CONFLITTO_STATO`**: un advisory lock non preso è
   «qualcun altro ci sta lavorando», non un guasto. Coerente con
   `E_PIPELINE_LOTTO_IN_ESECUZIONE`.

##### ⚠️ Due cose da sapere, e la seconda va decisa al D-5

* **I 29 ritiri stanno solo in `codici_errore.csv`**, non in `messaggi_errore.csv`.
  Finché il D-6 non sposta la colonna, il guardrail continua a leggere la vecchia
  e **non li vede ritirati**. È voluto: nessun cambio di comportamento prima del
  punto di non ritorno. E semplifica il D-6, che non deve più copiare niente —
  i valori nascono già nel CSV nuovo.
* 🔵 **Gli apostrofi nel CSV.** `messaggi_errore.csv` li scrive **raddoppiati**
  (`e'' un componente`): o è una convenzione del loader, o è un residuo di quando
  quel seed era fatto di `INSERT` SQL. Non l'ho risolto e **ho evitato gli
  apostrofi nelle `note`**, così la domanda non si pone per questo file. Va
  guardata al D-5, perché se è un residuo allora nel catalogo ci sono messaggi che
  mostrano `''` a chi legge.

---

### D-2 (materiale di riferimento)

I codici a catalogo **senza** policy. Il discriminante è il §7.1 del brief —
**due assi**, non uno:

| Tracce nel repo | Cosa fare |
|---|---|
| **0** (`E_INVALID_SNAPSHOT`, `E_DRYRUN_CREATE_TRIGGER`, `E_DATA_FINE_INFERIORE_DI_INIZIO`) | ✅ **ritiro** — `obsoleto_dal` |
| **1-3** (`E_STORICO_*`, `E_TXID_DBLINK_*`, `E_ATTIVO_CASCADE`, `E_DBLINK_LOG_CONN_MISSING`) | verificare il singolo, plausibilmente ritiro |
| **3-10** (famiglie `E_BOM_*`, `E_CONTRATTO_MODALITA_C_*`, `E_COMPETENZA*`) | ⚠️ **classificare**, non ritirare: sono progettate, non superate |

⚠️ **`E_AI_CONFIRMATION_REQUIRED` → ritiro**, non classificazione: il BE l'ha già
tolto dalle policy, a catalogo è rimasto vivo.

⚠️ **Un codice ritirato tiene la classe che aveva da vivo.** Il diario deve
continuare a risolvere: `obsoleto_dal` non è `attivo = false`.

✅ **Verifica:** zero codici a catalogo senza una classe assegnata.

---

### D-3 · ⏱ Spezzare `E_VALIDAZIONE`

🔴 **Prima del seed**, ed è il solo passo con una scadenza. Dieci funzioni, cinque
domini, tutte sotto «Validazione fallita: %s»:

> `fn_resolve_indirizzo_documento` · `fn_snapshot_indirizzo` ·
> `fn_snapshot_indirizzo_soggetto` · `fn_annulla_reso` · `fn_conferma_reso` ·
> `fn_genera_ddt_da_ordine` · `fn_genera_ddt_riconsegna` ·
> `fn_ordine_ha_residuo_evasione` · `fn_ordine_riga_qta_riconsegna` ·
> `fn_push_preventivo_a_ordine`

Il caso che dimostra il problema: **`fn_annulla_reso` che rifiuta un annullamento
è `CONFLITTO_STATO`**, non un dato sbagliato. Con `E_VALIDAZIONE` classificato
`DATO_ERRATO` quella bugia avrebbe un dato che la certifica.

**Cosa fare:** un codice per famiglia di condizione, non uno per funzione — il
criterio è *«i significati chiedono reazioni diverse della pagina?»*
([api.md](../api.md)). I nuovi codici entrano nel catalogo con la loro classe;
`E_VALIDAZIONE` resta per gli usi che sopravvivono, o si ritira.

⚠️ **`E_PARAMETRO_INVALIDO` NON entra qui**: 114 funzioni sono un cantiere suo.
Va nel seed col **denominatore sicuro** e la ragione in `note`.

⚠️ **Leggere il punto che solleva, non il nome** — e verificare i pgTAP esistenti
prima di cambiare il codice sollevato da una funzione: un `throws_ok` che
asserisce il vecchio codice diventa rosso.

---

### D-4 · Le due tabelle (`00_schema`)

```
config.classi_errore    classe PK · descrizione NOT NULL · obsoleto_dal · audit
config.codici_errore    codice PK · classe NOT NULL (FK) · obsoleto_dal · note · audit
```

⛔ **Nessun `DEFAULT` su `classe`**, e la ragione va scritta nel changeSet: un
default è il meccanismo che ha prodotto il difetto (§5.1 del brief).

* `classe` è una **FK a un vocabolario**, non un `CHECK`;
* `classi_errore` nasce con **8 righe**, `AVVISO` incluso (§4.2 del brief);
* `note` **su una riga sola**, senza a capo (D18);
* audit standard: `data_insert`, `user_insert`, `data_update`, `user_update`, `tx_id`.

⚠️ **Le automazioni (audit/`tx_id`/storico) girano solo in contesto `ci_apply`**:
sul migrate manuale le provvede il pgagent di fine giornata. Da sapere quando si
controlla il risultato la sera stessa.

---

### D-5 · 🔴 Il seed — il passo che rompe la CI se fatto nel modo ovvio

⚠️ **Leggere il §10.1 del brief prima di scrivere una riga.** In sintesi: tutto
`00_schema` gira prima di tutto `80_data`, quindi la FK esiste già quando il
mirror del catalogo (`20260614-08`) parte — e su un **DB ricostruito da zero** il
catalogo si carica prima che `codici_errore` sia popolata. **Violazione di FK, e
su dev non si vede.**

**Rimedio:** estendere `20260614-08` **in place** con un secondo
`loadUpdateData` su `codici_errore.csv` messo **prima** di quello del catalogo.
Il changeSet è `runOnChange: true` + `validCheckSums: ANY` — un mirror vivo,
progettato per essere esteso (l'ha già fatto `obsoleto_dal`).

* un solo changeSet = una transazione = ordine garantito;
* il vocabolario `classi_errore` (10 righe) nello stesso changeSet, per primo;
* ⚠️ `nullValue: "NULL"` — **token letterale**, non la cella vuota: su una colonna
  `DATE` la stringa vuota è un errore di cast.

✅ **Verifica:** `make db-migrate` verde, e conteggio `codici_errore` = conteggio
codici distinti del catalogo.

---

### D-6 · 🔴 `obsoleto_dal` migra — punto di non ritorno

Colonna nuova su `codici_errore` popolata dai valori attuali, poi `DROP` su
`messaggi_errore`. Forward-only, breaking secco: non siamo in produzione.

⚠️ **Nello stesso giro i 5 lettori**, o il presidio del ritiro smette di
funzionare in silenzio — che è esattamente il difetto che stiamo curando:

| File | Cosa |
|---|---|
| `scripts/sql/guardrail_codice_errore_strutturato.sql` ~137 | controllo **C** |
| idem ~165-185 | controllo **D** |
| idem ~219-232 | controllo **E** + testo del messaggio |
| idem ~271 | esclusione dei ritirati |
| `scripts/sql/check_messaggio_vs_condizione.sql` ~100 | la lente |

**La migrazione è 1:1 e senza ambiguità**: le 50 righe ritirate sono tutte `it`,
quindi non c'è nessun caso «ritirato in una lingua e non nell'altra» da
risolvere. È il difetto che questo spostamento chiude per sempre.

---

### D-7 · La FK + la policy indici

```sql
ALTER TABLE config.messaggi_errore
  ADD CONSTRAINT fk_cfg_messaggi_errore_codice
  FOREIGN KEY (codice) REFERENCES config.codici_errore (codice);
```

✅ **La stringa regge**: verificato (§3.5 del brief) — nessuno spazio, nessuna
ambiguità di maiuscole, niente fuori da `[A-Z0-9_]`.

⚠️ **Seed `dbops.fk_index_policy` con `consentito = false`** e la ragione:
*«coperto dal prefisso di `uq_messaggi_errore_codice_lingua`»*. Gli indici FK sono
opt-in e non nascerebbe comunque, ma senza seed resta una riga che nessuno sa se
è stata valutata o dimenticata.

---

### D-8 · pgTAP

**Quattro da adeguare** — inseriscono direttamente nel catalogo e con la FK
vogliono un padre:

* `test-messaggi-errore-obsoleto-dal.sql` — ⚠️ **da riscrivere**, non adattare:
  verifica una colonna che cambia casa;
* `test-fn-log-and-raise-error-fallback-lingua.sql`
* `test-fn-log-and-raise-error-constraint-codice.sql`
* `test-fn-get-messaggio-fallback-lingua.sql`

**Nuovi, e sono il collaudo del disegno:**

1. `INSERT` in `codici_errore` **senza classe** → deve fallire (il `NOT NULL` è il
   meccanismo: se non è collaudato, non è un meccanismo);
2. `INSERT` in `messaggi_errore` con un codice **senza padre** → deve fallire;
3. un codice **ritirato** risolve ancora dal diario;
4. `vw_codici_errore_identita` ha **una riga per codice**, compresi i codici
   **senza** messaggio.

⚠️ **`throws_ok` sempre con lo SQLSTATE**: senza, accetta qualunque errore —
compreso il crash del vincolo che doveva verificare.

⚠️ **Baseline prima di attribuirsi un rosso**: `scripts/pgtap-baseline.sh script config`.

---

### D-9 · Le due viste (`20_code`) — la consegna al BE

```sql
-- Revisione: affianca la frase. Una riga per (codice, lingua).
CREATE VIEW config.vw_codici_errore AS
SELECT c.codice, c.classe, c.obsoleto_dal, c.note,
       m.lingua, m.messaggio, m.causa, m.soluzione
  FROM config.codici_errore c
  LEFT JOIN config.messaggi_errore m ON m.codice = c.codice;

-- Identità: la sorgente del generatore BE. Una riga per codice.
CREATE VIEW config.vw_codici_errore_identita AS
SELECT codice, classe, obsoleto_dal, note
  FROM config.codici_errore
 ORDER BY codice;
```

⚠️ **`LEFT JOIN` nella prima**: un codice **può** esistere senza messaggio, e la
vista deve mostrarlo — è uno dei difetti che serve vedere.

⚠️ **`ORDER BY` dentro la seconda**, non solo nella query del generatore: un
requisito che vive in due posti si dimentica in uno dei due. Senza, il generatore
produce diff spurii per riordino, il file diventa illeggibile e da lì a non
accorgersi di una classe cambiata è un passo.

⚠️ **Numerazione più alta** di chiunque dipenda da loro: l'autogen mescola
`00_schema` e `20_code` ordinando per NN.

✅ **È qui che il DB consegna.** Da questo momento il BE può partire col
generatore (piano BE, **B-5**).

---

### D-10 · La misura dei codici multidominio

Una vista accanto a `dbops.vw_codici_errore_da_dichiarare`:

> **un codice sollevato da funzioni di più di un dominio è candidato accumulatore.**

⚠️ **Misura, non cancello** (§9.2 del brief): un codice legittimamente trasversale
esiste, e un cancello che lo bocci verrebbe disattivato. Si guarda all'apertura di
un lotto.

Non blocca il BE: può slittare senza conseguenze.

---

## 3. Fuori piano, ma da non perdere

* **`MESSAGGIO_NON_DEFINITO` → `E_MESSAGGIO_NON_DEFINITO`** — chiude il registro
  `dbops.messaggi_errore_codici_legacy` (**1 → 0**, e a zero la tabella si
  droppa). ⚠️ **Slice sua**: `script.fn_log_error_only` cerca quel codice **per
  nome scritto a mano**, le funzioni vanno nello stesso changeSet. Rinominarlo dal
  solo CSV rompe il ripiego del ripiego, e si vede solo il giorno in cui manca un
  messaggio a catalogo — il peggiore per scoprire un guasto.
* **La regola «niente nuovi codici generici»** — coda del lavoro, insieme al BE.

---

## 4. Convenzioni da rispettare, senza rileggere tutto

* changeSet: `YYYYMMDD-NN-<tipo>-<descrizione>-mctit.yaml`, **uno per file**,
  sempre `logicalFilePath`. **NN è una sequenza globale per data**, non per
  cartella;
* ⛔ **`runOnChange: true` è vietato** in `00_schema` e `20_code` (guardrail CI).
  Lecito solo nei mirror di `80_data` — che è il caso di D-5;
* ⛔ **mai modificare un changelog già mergiato**, salvo i mirror
  `runOnChange` + `validCheckSums: ANY` (di nuovo: D-5, ed è per progetto);
* ⛔ **`validCheckSums` al plurale** — il singolare è una chiave che Liquibase
  ignora;
* i dati di `80_data` si cambiano **dal CSV**, mai con `UPDATE` diretti;
* **DDL e corpi dalla doc auto-gen** (`docs/it/dbzero/…`), mai dagli YAML: un
  singolo YAML è quasi sempre stale;
* ⛔ **niente commit senza «procedi» esplicito**.
