# Piano DB — classe dei codici errore

**Chi:** team DB (`dev/db-tid`).
**Guida generale e ragioni di ogni scelta:** [brief-db-be-classe-codici-errore](brief-db-be-classe-codici-errore.md) — 20 decisioni, le trappole, i perché. **Questo file non le ripete: le esegue.**
**Piano gemello:** [piano-be-classe-codici-errore](piano-be-classe-codici-errore.md).
**Stato:** 🟡 **in corso** — ✅ D-1..D-6 applicati, **D-7 scritto** (2026-08-07). Prossimo: **D-8** (pgTAP) e **D-9** (le due viste = 🔴 il cancello del BE).
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
| ✅ **D-3** | ~~Spezzare `E_VALIDAZIONE`~~ **NON SI FA** — misurato: 13 punti, **una sola condizione** | — | ⚠️ la premessa era falsa, e la scadenza sul seed sparisce con lei |
| ✅ **D-4** | ~~Le due tabelle~~ **fatto** — `20260807-11` e `-12` | — | ⚠️ PK **testuale**, deviazione deliberata (3 precedenti su 467) |
| ✅ **D-5** | ~~Seed~~ **fatto** — 3 loader in `20260614-08`, in ordine | D-1 · D-2 · D-4 | ⚠️ la trappola era **al D-7**, non qui: vedi sotto |
| ✅ **D-6** | ~~`obsoleto_dal` migra + i 5 lettori~~ **fatto** — `20260807-13` | D-5 | 🔴 punto di non ritorno **superato** |
| ✅ **D-7** | ~~FK + policy indici~~ **fatto** — `20260807-14` e `-15` | D-5 | ⚠️ **due** FK da registrare, non una |
| **D-8** | pgTAP: **4 da adeguare** + i nuovi | D-6 · D-7 | |
| **D-9** | Le **due viste** (`20_code`) | D-4 | ⚠️ numerazione più alta di chi dipende da loro |
| **D-10** | Vista della **forma della condizione** — la misura | D-9 | ⚠️ **ri-specificata**: l'asse «multidominio» era smentito dal D-3 |

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
* ✅ **Gli apostrofi: risolto, ed era un difetto.** Vedi D-2-bis.

---

### D-2-bis · ✅ Le `note` del BE importate, e due cose trovate importandole

Il BE ha consegnato `docs/it/dev/work-in-progress/allegati/codici-errore-classe-note.csv`
(658 righe, 215 note). **Importate tutte**, con due rimappature e una pulizia.

| | |
|---|---:|
| note del BE | 215 |
| atterrate direttamente | 213 |
| **rimappate** — `E_MESSAGGIO_NON_DEFINITO` e `E_W_TXID_NOT_REGISTERED` puntano a nomi che a catalogo non esistono: la nota va sul gemello senza prefisso | 2 |
| collisioni con le nostre 9 | **0** |
| perse | **0** |

⚠️ **Il CSV del BE non poteva essere il seed**, e non è un errore loro: ha
l'universo delle **policy** (658), non del **catalogo** (689). Come seed
lascerebbe **33 codici senza padre** — violazione di FK al primo migrate su DB
ricostruito — e aggiungerebbe 2 righe che a catalogo non esistono. Serviva la sua
terza colonna, e quella è arrivata intera.

#### ⭐ Gli apostrofi: risolto, ed è un difetto preesistente

La domanda lasciata aperta al D-2 non era più aggirabile: **105 delle 215 note
hanno un apostrofo**. La prova sta nel repo:

> Nei CSV di `80_data` ci sono **1353 celle con apostrofo singolo** (per esempio
> `lista_colonna.csv`: «Fornitore soggetto a ritenuta d'acconto»), tutte caricate
> senza problemi. Se Liquibase inlineasse i valori nell'SQL, una sola di quelle
> celle romperebbe il migrate.

**Liquibase lega i parametri: l'apostrofo singolo è la forma giusta.** Quindi le
note vanno bene così come sono, e **il raddoppio in `messaggi_errore.csv` è un
residuo**, non una convenzione.

🔴 **Conseguenza fuori perimetro ma seria: 35 codici del catalogo mostrano `''` a
chi legge.** 82 celle in `messaggi_errore.csv` più 4 in `email_template.csv`.
⚠️ Non è verificato sul DB vivo (serve una query), ma la catena regge: il mirror
`runOnChange` riscrive quelle celle a ogni migrate. È una slice sua, piccola —
una passata sul CSV — e va aperta.

#### ⚠️ 45 note su 224 non parlavano del loro codice

L'estrattore del BE prende **il blocco di commento immediatamente sopra la
policy**. Quel blocco però, per il primo codice di ogni sezione, è
**l'intestazione del gruppo** — non la motivazione di quel codice:

| | quante |
|---|---:|
| note pulite, motivazione del codice | 179 |
| ✂️ con l'intestazione davanti, tolta | 23 |
| 🔴 **solo** intestazione, zero contenuto sul codice — **azzerate** | 22 |
| **note finali nel CSV** | **202** |

Le 22 azzerate dicevano cose come «`── 409 ──`» su `E_CANALE_ORIGINE_IMMUTABILE`
o «`── Commesse ──`» su `E_COMMESSA_SORGENTE_SCONOSCIUTA`: il titolo del gruppo
appiccicato a chi capitava primo. Non si perde niente — quel testo resta nel
modulo del BE, dove è al posto giusto.

⭐ **La lezione vale oltre le 45**: *«il commento sopra una voce»* non è
*«il commento di quella voce»*. In un file raggruppato per sezioni, il primo
elemento di ogni gruppo eredita il titolo del gruppo — e un estrattore che non lo
sa produce, per ogni sezione, una riga che sembra una motivazione e non lo è.

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

### D-3 · ✅ **NON SI FA** — la premessa era falsa, e lo dice la misura

Il piano diceva: *«10 funzioni, 5 domini, tutte sotto "Validazione fallita: %s";
`DATO_ERRATO` è plausibile per alcuni e falso per altri: `fn_annulla_reso` che
rifiuta un annullamento è `CONFLITTO_STATO`»*. Era il passo con la scadenza, da
fare **prima del seed**.

🔴 **Non regge.** Letti tutti e 13 i punti che lo sollevano, uno per uno:

| Condizione | Punti |
|---|---:|
| `IF p_<id> IS NULL OR p_<id> <= 0` | 10 |
| `IF p_<id> IS NULL` | 1 |
| `IF p_<id> IS NOT NULL AND p_<id> <= 0` | 1 |
| `IF p_tipo_codice IS NULL OR btrim(...) = ''` | 1 |
| **qualunque altra cosa** | **0** |

**Sono tutti e 13 la stessa condizione: un parametro obbligatorio mancante o non
valido.** Ed è la guard che `.codex/AGENTS.md` **prescrive**: *«per parametri
numerici di tipo ID applicare guard di validazione esplicita: errore se NULL o
<= 0, non normalizzare silenziosamente»*. Il `causa` a catalogo lo dice già,
parola per parola.

⚠️ **In `fn_annulla_reso` `E_VALIDAZIONE` non rifiuta nessun annullamento**: è
sollevato su `p_reso_id IS NULL OR p_reso_id <= 0`. Il rifiuto dell'annullamento,
dove c'è, usa un altro codice.

**Quindi `E_VALIDAZIONE` non è un accumulatore: ha un significato solo, usato 13
volte, e `DATO_ERRATO` è giusto per tutti.** Spezzarlo sarebbe stato riscrivere
10 funzioni, adeguare i pgTAP e creare codici nuovi per non cambiare niente.

#### ⭐ Perché la premessa sembrava vera — e la lezione vale oltre

L'eterogeneità era stata dedotta dall'**elenco dei nomi di funzione**: indirizzi,
resi, DDT, residui d'ordine, push preventivo — cinque domini, sembra ovvio che
dietro ci siano cinque condizioni diverse.

> **Le funzioni erano eterogenee, la condizione no.** Un codice è un accumulatore
> quando copre **condizioni** diverse, non quando è usato in **domini** diversi.
> «10 funzioni, 5 domini» misurava la cosa sbagliata, e nessuno se n'è accorto
> perché il numero era vero.

#### ⚠️ E l'altro accumulatore è quasi uniforme anche lui

Stessa lente su `E_PARAMETRO_INVALIDO`, **177 punti**:

| | punti |
|---|---:|
| guard di parametro (`IS NULL`, `<= 0`, `btrim = ''`) | **160** (90%) |
| tutto il resto (`NOT IN (...)`, `v_x IS NULL` dopo un SELECT, …) | 17 |

**`DATO_ERRATO` non è il denominatore sicuro: è la risposta giusta per il 90%
dei punti.** Restano una dozzina di siti da guardare con la lente — non il
«cantiere a sé» che i documenti si erano immaginati. La nota nel CSV resta,
riscritta su questa misura.

---

### D-4 · ✅ **FATTO** — 2026-08-07

| ChangeSet | Cosa |
|---|---|
| [`20260807-11-create-classi-errore`](../../../../db/changelog/migrations_v2/00_schema/config/20260807-11-create-classi-errore-mctit.yaml) | il vocabolario: `classe` PK, `descrizione` NOT NULL, `obsoleto_dal`, audit |
| [`20260807-12-create-codici-errore`](../../../../db/changelog/migrations_v2/00_schema/config/20260807-12-create-codici-errore-mctit.yaml) | l'identità: `codice` PK, `classe` **NOT NULL senza DEFAULT** (FK), `obsoleto_dal`, `note`, audit |

Entrambi `runOnChange: false`, `preConditions` con `onFail: HALT`, e il `-12`
pretende che il `-11` esista. YAML validato. **Non applicati**: serve il tuo
«procedi» per il migrate.

#### ⚠️ PK testuale — deviazione deliberata, e misurata

Le convenzioni vogliono `id` surrogato, e **464 tabelle su 467** ce l'hanno. Le
tre eccezioni sono registri chiavati da una stringa naturale e stabile —
`config.storico_set_storicizza(table_name)`, `dbops.idempotency_keys(idempotency_key)`,
`config.tipi_soggetto(id varchar)` — ed è esattamente questo caso: **il codice
È la sua identità**, ed è la frase su cui poggia tutto il §3.1 del brief.

Un id surrogato qui costerebbe una colonna che nessuno legge e obbligherebbe
`messaggi_errore` a portarsi dietro una FK numerica al posto del valore che si
vuole leggere nella vista e nel CSV. La ragione è scritta nella testata di
entrambi i changeSet, perché una deviazione non documentata a sei mesi sembra
una distrazione.

#### Due `CHECK` che non erano nel piano

* **`codice = btrim(codice) AND codice <> ''`** (e lo stesso su `classe`): la
  chiave è testuale, e due stringhe che differiscono per uno spazio ai bordi
  sarebbero chiavi diverse che a occhio sono uguali. Verificato prima di
  scriverlo: sul catalogo vivo zero spazi ai bordi e zero ambiguità di
  maiuscole, quindi il vincolo nasce già soddisfatto;
* **`note !~ '[\n\r]'`** — la D18 diceva «`note` su una riga sola» e restava una
  raccomandazione. Con questo `CHECK` è un fatto: il seed passa da un CSV, e le
  celle multi-riga in questo repo sono **3 in tutto**. Meglio un vincolo che una
  sorpresa al primo `loadUpdateData`.

#### Cosa non c'è, e di proposito

Nessun `attivo` (una classe non si disattiva: si ritira), nessun `meta`, nessun
`tx_id` — 23 tabelle `config` su 110 ce l'hanno, e le linee guida §7 elencano
solo le quattro colonne di audit.

⚠️ **Le automazioni arrivano dopo.** `config` è in `dbops.automation_scope` con
`*all`, ma il framework gira solo in contesto `ci_apply`: su un migrate manuale
le tabelle nascono **senza** trigger di audit e li ricevono dal pgagent di fine
giornata. Non è un difetto, è da sapere se si controlla il risultato la sera
stessa.

---

### D-5 · ✅ **FATTO** — 2026-08-07

`20260614-08` carica ora **tre** tabelle, in quest'ordine e in **una
transazione**:

| # | Tabella | Righe | File |
|---|---|---:|---|
| 1 | `config.classi_errore` | 10 | `classi_errore.csv` (nuovo) |
| 2 | `config.codici_errore` | 689 | `codici_errore.csv` (nuovo) |
| 3 | `config.messaggi_errore` | 690 | invariato |

Aggiunte anche le `preConditions` sulle due tabelle nuove: se qualcuno arriva
qui senza il D-4 il changeSet si ferma invece di fallire a metà.

#### ⚠️ La trappola c'era, ma era **al D-7** — e la cura è la stessa

Il piano diceva che il seed è «il passo che rompe la CI se fatto nel modo ovvio».
**Non è il seed: è la FK.** Al D-4 la FK verso `messaggi_errore` non è stata
creata (arriva al D-7), quindi *oggi* l'ordine dei loader non vincola nulla.

Ma la FK nascerà in `00_schema`, e lì **tutto `00_schema` gira prima di tutto
`80_data`**. Su un DB ricostruito da zero la FK esisterà già quando parte
`80_data`: se il catalogo dei messaggi si caricasse prima che `codici_errore` sia
popolata, **ogni riga violerebbe la FK**.

Un loader nuovo avrebbe la data di oggi e `includeAll` ordina per nome:
girerebbe **dopo** questo. Da qui l'estensione in place — e va fatta **adesso**,
non al D-7, perché al D-7 sarebbe già tardi per accorgersene.

⚠️ **E su dev non si vedrebbe comunque**: il catalogo è popolato e la FK
troverebbe i padri. Si scoprirebbe in CI.

> ⭐ **Il precedente c'era ed è una regola di casa**: *«nuovi codici errore =
> solo append al CSV, MAI un nuovo loader upsert — i loader `runOnChange`
> esistenti ripescano il CSV»*. Vale identica per una tabella nuova che deve
> caricarsi prima di una vecchia.

#### Verifica post-migrate

```sql
SELECT count(*) FROM config.classi_errore;   -- 10
SELECT count(*) FROM config.codici_errore;   -- 689
-- precondizione della FK del D-7: ogni codice del catalogo ha il suo padre
SELECT count(*) FROM config.messaggi_errore m
  LEFT JOIN config.codici_errore c ON c.codice = m.codice
 WHERE c.codice IS NULL;                     -- 0
```

⚠️ Il changeSet è `runOnChange: true`: al prossimo migrate **ri-esegue tutto**,
compreso il caricamento del catalogo dei messaggi. È il comportamento voluto di
un mirror, ma vuol dire che il migrate del D-5 tocca 1389 righe, non 699.

---

### D-6 · ✅ **FATTO E APPLICATO** — 2026-08-07 · il punto di non ritorno è passato

**Quattro cose in un solo giro**, e non potevano andare separate:

| # | Cosa | Dove |
|---|---|---|
| 1 | `DROP COLUMN config.messaggi_errore.obsoleto_dal` | [`20260807-13`](../../../../db/changelog/migrations_v2/00_schema/config/20260807-13-drop-obsoleto-dal-messaggi-errore-mctit.yaml) |
| 2 | colonna tolta dal CSV del catalogo | `config/messaggi_errore.csv` |
| 3 | colonna tolta dal terzo loader | `20260614-08` |
| 4 | i **5 lettori** riscritti | guardrail (4) + lente (1) |

⚠️ **Il DROP non si può applicare da solo.** Il mirror `20260614-08` dichiara
`obsoleto_dal` fra le colonne del catalogo: se il DROP arriva senza la modifica
al loader, il primo migrate fallisce perché il loader carica una colonna che non
esiste più. La `preCondition` del changeSet **non protegge da questo** — protegge
il verso opposto, che la nuova casa esista.

#### La migrazione dei dati era già fatta, e verificata prima

I valori non si copiano nel changeSet: erano già nella nuova casa, arrivati col
seed del D-5. Confronto riga per riga **prima** di scrivere il DROP:

| | |
|---:|---|
| ritirati in `messaggi_errore` | 50 |
| ritirati in `codici_errore` | **79** (50 + 29 dal D-2) |
| presenti in messaggi ma **non** in codici | **0** |
| con data diversa | **0** |

#### I cinque lettori — e nel piano erano etichettati male

| Dove | Controllo | Cosa cambia |
|---|---|---|
| guardrail | **(B)** codici fuori convenzione | legge il ritiro da `codici_errore` |
| guardrail | **(C)** il registro deve calare | il `LEFT JOIN` passa a `codici_errore`, e la condizione si semplifica: una riga per codice toglie l'`EXISTS` che serviva a scavalcare le lingue |
| guardrail | **(D)** codici ritirati ancora sollevati | idem, più il testo dell'errore che ora indica il CSV giusto |
| guardrail | riepilogo finale | conta i ritirati da `codici_errore` |
| lente | join del messaggio | ⚠️ **due join, non uno** (sotto) |

⚠️ Il piano li chiamava «C, D, E»: sono **B, C, D e il riepilogo**. Etichetta
sbagliata, punti giusti — ma chi cercava (E) non l'avrebbe trovato.

⭐ **Sulla lente la modifica non era meccanica.** Il filtro sul ritiro stava
*dentro* il join della frase (`me.lingua = 'it' AND me.obsoleto_dal ...`).
Spostarlo a `codici_errore` ha richiesto **due join separati**: la frase resta
per lingua, il ritiro no. Tenerli insieme avrebbe rimesso il filtro su un asse
per-lingua — cioè il difetto appena chiuso, ricreato nel codice che lo controlla.

> ⚠️ **Un presidio che legge una colonna sparita non fallisce rumorosamente:
> smette di vedere.** È il motivo per cui i lettori vanno nello stesso commit del
> DROP, e non «subito dopo».

#### ✅ Applicato — cosa resta da guardare

Il migrate è passato. ⚠️ **Due verifiche che non ho potuto fare da qui** (non ho
accesso al DB vivo) e che vale la pena chiudere prima del D-7:

```sql
-- la colonna non c'e' piu'
SELECT count(*) FROM information_schema.columns
 WHERE table_schema='config' AND table_name='messaggi_errore'
   AND column_name='obsoleto_dal';                -- 0
-- il ritiro e' nella nuova casa
SELECT count(*) FROM config.codici_errore WHERE obsoleto_dal IS NOT NULL;  -- 79
```

🔴 **E il guardrail va rilanciato — è la prova che il D-2 era giusto.** Il
controllo (D) dice che nessuna funzione viva solleva un codice ritirato, e al
D-2 ne sono stati ritirati **29** proprio perché nessuna li solleva più:

```bash
psql -v ON_ERROR_STOP=1 -f scripts/sql/guardrail_codice_errore_strutturato.sql
```

Se (D) è verde, la lettura dei 29 era giusta e la loro classe è al posto suo. Se
è rosso, uno di quei 29 è vivo — e il nome che stampa dice quale funzione lo
solleva. **È l'unico controllo di questo cantiere che può ancora smentire una
decisione già presa**, e conviene farlo adesso che il rimedio è una riga di CSV,
non dopo la FK.

---

### D-7 · ✅ **FATTO** — 2026-08-07 (da applicare)

| ChangeSet | Cosa |
|---|---|
| [`20260807-14`](../../../../db/changelog/migrations_v2/00_schema/config/20260807-14-fk-messaggi-errore-codici-errore-mctit.yaml) | `FK messaggi_errore.codice → codici_errore.codice` |
| [`20260807-15`](../../../../db/changelog/migrations_v2/80_data/changelog/20260807-15-upsert-fk-index-policy-codici-errore-mctit.yaml) + CSV | policy indici, **due righe** a `consentito = false` |

#### ⭐ Cosa chiude davvero questa FK

Non è un vincolo di igiene: è **il pezzo che rende vero il meccanismo del §5**.
Con `codici_errore.classe` NOT NULL senza default *più* questa FK, la catena è
completa —

> **una frase non può nascere senza che qualcuno abbia deciso che cosa è
> l'errore che descrive.**

Senza la FK, `codici_errore` sarebbe un elenco parallelo che ci si può
dimenticare di aggiornare: cioè il difetto da cui nasce tutto il cantiere,
ricostruito dentro il rimedio.

#### ⚠️ E cambia il lavoro di tutti i giorni

Aggiungere un codice non è più una riga in `messaggi_errore.csv`: sono **due
righe in due file**, prima `codici_errore.csv` poi il messaggio. **Vale anche per
le rinomine**, che in questo progetto sono frequenti.

Non serve un migrate in due tempi — il mirror `20260614-08` carica le due tabelle
nell'ordine giusto, nella stessa transazione. Ma chi tocca solo il catalogo dei
messaggi **vede fallire il migrate**, ed è esattamente quello che deve succedere.

#### La `preCondition` che vale più del vincolo

```yaml
- sqlCheck:
    expectedResult: 0
    sql: SELECT count(*) FROM config.messaggi_errore m
           LEFT JOIN config.codici_errore c ON c.codice = m.codice
          WHERE c.codice IS NULL
```

Se il seed non ha coperto tutti i codici, il changeSet **si ferma prima** invece
di far fallire l'`ALTER TABLE` a metà. È la stessa verifica del D-5, ma eseguita
dal migrate invece che a mano.

#### ⚠️ Le FK da registrare erano **due**, non una

Il piano ne prevedeva una. Ma al D-4 ne è nata un'altra —
`codici_errore.classe → classi_errore.classe` — e una FK senza riga di policy è
**una decisione non presa**, che a sei mesi non si distingue da una dimenticata.

| FK | `consentito` | Perché |
|---|---|---|
| `fk_messaggi_errore_codici_errore` | `false` | `codice` è già la **colonna di testa** di `uq_messaggi_errore_codice_lingua`: l'indice sarebbe una copia del suo prefisso |
| `fk_codici_errore_classi_errore` | `false` | **10 valori distinti su 689 righe**: il planner non lo sceglierebbe mai |

⚠️ Nessuna delle due è una FK su cui si fa `DELETE` del padre — l'operazione che
di solito giustifica l'indice. I codici non si cancellano, si ritirano; le classi
nemmeno.

#### Una nota sul nome del vincolo

`fk_messaggi_errore_codici_errore`, forma `fk_<base>_<ref>` delle linee guida.
Sulla stessa tabella esiste `fk_cfg_messaggi_errore_lingua` col prefisso di
schema: misurato, sono **3 nomi su 741** nel database — un'eccezione locale, non
una convenzione, e non va propagata.

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

### D-10 · La misura — ⚠️ **ri-specificata**, l'asse era sbagliato

🔴 **Come era scritto, questo passo misurava l'asse che il D-3 ha smentito.**
Diceva: *«un codice sollevato da funzioni di più di un dominio è candidato
accumulatore»*. Ma `E_VALIDAZIONE` è **10 funzioni in 5 domini** ed è il caso su
cui la risposta è **no** — sarebbe stato il primo falso positivo della vista.

Rilievo del BE, e coglie una contraddizione interna ai nostri documenti: il D-3
aveva già scritto *«un codice è accumulatore quando copre **condizioni** diverse,
non **domini** diversi»*, e questo passo restava sull'asse vecchio.

> ⚠️ È una misura, non un cancello, quindi un falso positivo non fa danno. **Ma
> una misura che sbaglia sul suo caso più noto viene guardata due volte e poi mai
> più** — che è il modo in cui i presidi muoiono in silenzio.

#### L'asse giusto, e la macchina esiste già

`check_messaggio_vs_condizione.sql` ha la CTE **`con_guardia`**, che accoppia già
`(codice, funzione, guardia)` risalendo dalla riga che nomina il codice al ramo
che la precede. Si classifica la guardia in famiglie e si segnala chi ne ha più
di una:

| Famiglia | Riconosciuta da |
|---|---|
| `PARAMETRO` | `IS NULL`, `<= 0`, `< 0` su un `p_…` |
| `NOT_FOUND` | `IF NOT FOUND` |
| `ECCEZIONE` | `EXCEPTION WHEN`, `WHEN OTHERS`, `WHEN SQLSTATE` |
| `ENUM` | `NOT IN (…)` |
| `ALTRO` | tutto il resto |

**Provato sui casi noti (2026-08-07):**

| Codice | Punti | Famiglie | Esito |
|---|---:|---|---|
| `E_VALIDAZIONE` | 13 | `PARAMETRO` | ✅ **pulito** — l'asse vecchio lo segnalava |
| `E_PARAMETRO_INVALIDO` | 206 | 3 famiglie | ✅ segnalato |
| `E_SOGGETTI_RUOLI` | 3 | 3 famiglie | ✅ segnalato |
| `E_STATO_SCONOSCIUTO` | 0 | — | ⚠️ **non verificabile**: è ritirato, non ha punti vivi |

#### ⚠️ E la misura deve dichiarare quello che NON vede

Misurato prima di prometterla:

| | |
|---:|---|
| codici con una guardia riconoscibile | 342 |
| **classificati in una famiglia nota** | **75** |
| finiti tutti nel cestino `ALTRO` — invisibili alla misura | **267** |
| segnalati (più di una famiglia) | 22 |
| **di cui per due famiglie NOTE** — il segnale forte | **6** |
| segnalati per «una nota + qualcosa che non so leggere» | 16 |

**Quindi la vista apre con una riga di copertura**, come fa già la lente
(*«se `punti` fosse zero, l'euristica è rotta, non il database sano»*): *su 342
codici ne classifico 75; dei restanti 267 non so dire niente.* Senza quella riga,
un elenco di 6 si legge come «gli accumulatori sono sei», che è falso.

I sei forti, per chi arriva qui: `E_PARAMETRO_INVALIDO`, `E_GENERICO`,
`E_ADMIN_VALIDAZIONE`, `E_ERRORE_PARAMETRI`, `E_ATTIVO_REQUIRE`,
`E_SOGGETTI_RUOLI`.

⚠️ **Se migliorare il classificatore costa più di quanto renda, la strada onesta
è la seconda che indica il BE**: dichiarare cosa la misura non distingue, invece
di lasciarla scritta su un asse che sappiamo falso.

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
