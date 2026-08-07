# Piano DB — classe dei codici errore

**Chi:** team DB (`dev/db-tid`).
**Guida generale e ragioni di ogni scelta:** [brief-db-be-classe-codici-errore](brief-db-be-classe-codici-errore.md) — 18 decisioni, le trappole, i perché. **Questo file non le ripete: le esegue.**
**Piano gemello:** [piano-be-classe-codici-errore](piano-be-classe-codici-errore.md).
**Stato:** 🔵 da cominciare.

---

## 0. La premessa che rende possibile questo piano

**Il BE è fermo, e non serve.** Decisione di Tid (2026-08-07): si sviluppa
**tutto il DB per primo**, poi il BE. Verificato prima di accettarla — e la
verifica ha tolto l'unica dipendenza che c'era:

> Il piano originale aveva al punto 3 *«il BE genera il CSV `codice,classe` da
> `error_policies.py`»*. **Non serve il BE**: la mappa status → classe è
> deterministica e il file è nel repo. Misurato: **654 codici su 659** si
> convertono automaticamente, e i 5 che restano sono esattamente i `401`×4 e il
> `502`×1 **già esclusi dal vocabolario** (§4 del brief).

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
| **D-1** | Estrarre il CSV `codice,classe` da `error_policies.py` | — | è la base di tutto e non costa niente: uno script, 654 righe automatiche |
| **D-2** | Le **~32 decisioni residue**: classificare o ritirare | D-1 | il `NOT NULL` le bloccherebbe al primo seed |
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

### D-1 · Estrarre il CSV `codice,classe`

Uno script che legge `backend/apps/core/services/error_policies.py` (in sola
lettura: è perimetro BE) e produce `codice,classe`.

**La mappa, deterministica:**

| `http_status` | `classe` | Quanti |
|---|---|---|
| 400 | `DATO_ERRATO` | 234 |
| 409 | `CONFLITTO_STATO` | 224 |
| 404 | `NON_TROVATO` | 84 |
| 500 | `TECNICO` | 63 |
| 403 | `NON_PERMESSO` | 23 |
| 422 | `NON_ESEGUIBILE` | 22 |
| 501 | `NON_DISPONIBILE` | 4 |

⚠️ **Il parser va scritto delimitando ogni voce con la chiave successiva**, non
con l'indentazione: **32 voci sono su una riga sola** e un parser che cerca
`http_status=` a inizio riga le perde. È il difetto che ha già prodotto due
misure sbagliate in questo cantiere (§4 del brief).

**Da decidere a mano, 5 codici** (fuori dal vocabolario di dominio):

* `E_JWT_SENZA_IDENTITA`, `E_IDENTITA_NON_ATTIVA`, `E_AUTHENTICATION_FAILED`,
  `E_NOT_AUTHENTICATED` — 401, costruiti dal middleware;
* `E_AI_PROVIDER_ERROR` — 502.

⚠️ **Non sono «senza classe»: sono fuori dal percorso che la classe governa.**
Vanno comunque in `codici_errore` (D9 del brief: il catalogo è di tutti) — la
classe più onesta per tutti e 5 è `TECNICO`, con la ragione in `note`. Da
confermare con Tid al momento del seed.

**Escludere** `PREV_STATO_NON_MODIFICABILE`: è morto (§7.2 del brief).

✅ **Verifica:** 659 voci lette, 654 mappate, 5 residue nominate.

---

### D-2 · Le ~32 decisioni residue

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
* il vocabolario `classi_errore` (8 righe) nello stesso changeSet, per primo;
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
