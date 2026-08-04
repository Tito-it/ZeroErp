# Brief DB — bonifica dei riferimenti morti nelle funzioni

**Chi scrive:** team DB (`dev/db-tid`), 2026-08-04.
**Cos'è:** il piano per sistemare i difetti che `plpgsql_check` ha fatto emergere,
più il presidio che impedisce a queste cose di tornare.
**Strumento:** [`scripts/sql/check_funzioni_riferimenti_morti.sql`](../../../../scripts/sql/check_funzioni_riferimenti_morti.sql)
**Correlati:** [piano-db-ritorno-lotto-a-draft](piano-db-ritorno-lotto-a-draft.md) §7
(misure M4-quater/quinquies/octies, da cui nasce tutto).

> **Stato al 2026-08-04, secondo giro: CHIUSO lato DB.** Le 33 righe del primo
> giro sono state lette una per una contro il DB vivo; sette conclusioni erano
> sbagliate o incomplete e sono corrette qui sotto, ognuna col perché. I 28
> changeSet `20260804-37..65` sono **applicati, verdi e committati**: il presidio
> misura **0 difetti aperti** e **1 sola voce** nel registro del debito, che è una
> decisione già presa (D6). Il §7 è il registro di avanzamento.
>
> ⚠️ **Il presidio in CI è in accensione.** Tre giri rossi, tutti diagnosticati e
> corretti (`-67`, `-68`, include in `changelog-provision-pre.yaml`, guardrail
> spostato dopo il migrate di Django): dettaglio e lezioni al §7. Il guardrail ha
> fatto il suo mestiere in tutti e tre. Finché una pipeline non passa, quella metà
> del presidio è dimostrata a pezzi e non nel suo insieme: è l'unica ragione per
> cui il brief resta qui e non in `work-done`.

---

## 1. Da dove viene

Il 2026-08-04, mentre si toglieva una colonna dormiente, un migrate è fallito su
una funzione che nominava `vendite.attivita_fatturabili_lotti` — una tabella
**droppata di proposito il 2026-02-27**, cinque mesi prima.

Il motivo per cui era ancora lì: PostgreSQL **non traccia** cosa c'è dentro il
corpo di una funzione plpgsql. Il `CASCADE` che droppa una tabella porta via
viste, vincoli e trigger, ma le funzioni le lascia intatte — e non le ri-valida
mai più. Restano mute finché qualcuno non le esegue.

E non è che nessuno se ne fosse accorto. Il **2026-03-31** due di quelle funzioni
erano già state incontrate durante la campagna sugli `E_GENERICO` e **saltate**,
con tanto di changeSet che esiste solo per dirlo:

> «Dipende da `vendite.attivita_fatturabili_lotti` (tabella rimossa).
> **Da verificare se la funzione va rimossa dal DB.**» — `20260331-26`

Quella verifica non è mai stata fatta. È il punto da cui parte questo brief:
**una segnalazione in un commento non è un presidio.**

---

## 2. Lo strumento, e perché non è una regex

L'alternativa era una vista che estraeva con una regex i riferimenti
`schema.tabella` dai corpi e li confrontava con `pg_class`. Sarebbe stata
un'euristica: prende le tabelle nominate dentro le stringhe, non vede i nomi non
qualificati, e soprattutto **non arriva alle colonne** — mentre metà dei difetti
trovati sono colonne, non tabelle.

`plpgsql_check` **compila davvero** il corpo, come farebbe la prima esecuzione:
vede tabelle e colonne, vede i **rami mai eseguiti**, e non prova a validare
l'SQL dinamico (quindi fa anche meno rumore). Estensione creata dal changeSet
`20260804-36`, contesto `provision`.

---

## 3. La classificazione, e dove ha sbagliato

Il primo giro produsse **60 righe**, di cui più della metà rumore. Tre giri di
affinamento dopo, il quadro sembrava questo:

| Classe | Righe (v2) | Righe (v3) | Cos'è |
|---|---|---|---|
| **REALE** | 27 | **28** | La lista di lavoro |
| **ORFANA** | 6 | 6 | Trigger function senza alcun trigger agganciato |
| `FP_VARIADIC` | 17 | **16** | `fn_log_and_raise_error(...)` senza valori variadici |
| `FP_RAMO_ALTRA_TABELLA` | 14 | 14 | Trigger function generica: il ramo di un'altra tabella |
| `FP_TRANSITION_TABLE` | 5 | 5 | `new_rows`/`old_table`: esistono solo allo scatto |
| `FP_SQL_DINAMICO` | 1 | 1 | Segnaposto dentro un `EXECUTE` |

**Nessuna riga viene filtrata via**: escono tutte con la loro etichetta, e il
file stampa apposta anche i falsi positivi, così si controllano a campione invece
di fidarsi della classificazione.

### 3.1 🔴 Il controllo a campione andava fatto davvero: una riga era mal classificata

La regola `FP_VARIADIC` diceva: *«42883 con argomenti tutti testo-compatibili =
variadico omesso, è rumore»*. Ma `jsonb` è nella lista dei testo-compatibili, e
uno **scambio di argomenti** fra un `text` e un `jsonb` produce esattamente la
stessa firma di un variadico omesso. Passava per rumore:

```
dbops.fn_audit_log_once('fn_run_automations_storico','SKIP_EXISTS','STORICO',
                        jsonb_build_object(...), 'Trigger already present')
```

La firma è `(p_function_name text, p_status text, p_params jsonb, p_message text, …)`:
il 3° e il 4° argomento sono **invertiti**. La chiamata non si risolve.

**Rimedio (v3):** l'esenzione vale solo se la funzione chiamata **ha davvero** un
parametro `VARIADIC` (`pg_proc.provariadic <> 0`). Delle 17 righe del primo giro
questa era l'unica a non chiamare `fn_log_and_raise_error`/`fn_log_error_only` —
ed era l'unica sbagliata. Riparata da `20260804-44`.

### 3.2 I tre limiti che restano, e che nessuna regola può togliere

Vanno conosciuti prima di fidarsi di un'etichetta:

* **Un ramo per una tabella non agganciata è invisibile alla regola che lo
  cercherebbe.** `FP_RAMO_ALTRA_TABELLA` confronta le tabelle *agganciate*: un
  ramo scritto per una tabella che non esiste più compare su tutte e passa per
  difetto vero (caso `trgfn_documenti_sync_canali`, ramo `ddt_ordini`). Il
  verdetto è giusto, la motivazione no.
* **Esiste una terza forma di ramo condizionale che nessuna regola vede**: quella
  che dipende da `TG_ARGV`, non dalla tabella. Un BB generico parametrico può
  avere rami irraggiungibili con *tutti* i trigger esistenti (caso
  `trgfn_qta_from_operativa`). Per deciderlo servono gli argomenti dei trigger,
  non le loro tabelle.
* **Un riferimento che si risolve verso la cosa sbagliata non è un errore di
  compilazione.** `fn_admin_merge_stradario` scriveva `comune_id` in colonne
  `via_id_*`: riparando solo i nomi avrebbe girato producendo record falsi ma
  plausibili. La semantica non si compila.

### 3.3 ⚠️ Un difetto si nasconde dietro l'altro: il check è un setaccio, non una lista

`plpgsql_check` si ferma alla **prima** sotto-espressione che non si risolve. Le
quattro guard `anagrafiche` della famiglia F4 avevano tutte un **secondo** difetto
sotto quello segnalato: chiamavano `anagrafiche.fn_log_and_raise_error` o
`dbops.fn_log_and_raise_error`, che **non esistono** — nel DB c'è solo
`script.fn_log_and_raise_error`. Il check non ci arrivava perché si fermava su
`sqlerrm`/`tgname`/argomenti misti.

Conseguenza operativa: **la bonifica va ri-misurata dopo ogni passo**, non
eseguita come lista di lavoro compilata una volta.

---

## 4. La lista di lavoro, per famiglie

Riordinata rispetto al primo giro: prima ciò che è **vivo e rotto ora**.

### F2-vivi — I due difetti su percorso di produzione 🔴

| Funzione | Difetto | changeSet |
|---|---|---|
| `script.fn_search_stradario` | tipi di ritorno scollegati dalle colonne | `-37` |
| `vendite.fn_prepare_sdi_payload` | colonna `tentativo` + numerazione che viola un CHECK | `-39` |

**`fn_search_stradario` è il difetto più grave del cantiere, e il primo giro non
l'aveva visto.** È l'autocomplete delle vie del backend
(`apps/core/db/lookup_repository.py`), e non gira:

```
ERRORE:  structure of query does not match function result type
DETTAGLI: Returned type character varying(50) does not match expected type bpchar
          in column "cap" (position 9).
```

🔴 Il suo pgTAP è in `db/pgtap/baseline-rossi.tsv` con causa **`ERRORE_FIXTURE`**.
La causa è sbagliata: non è la fixture, è la funzione. `plan(8)`, ne esegue 1.
Un difetto vivo si è nascosto dietro un'etichetta del registro di debito — che è
esattamente il modo in cui un registro smette di essere un registro.

#### La causa radice, che vale oltre queste due funzioni

`%TYPE` in **firma** (non nel `DECLARE`) si risolve **una volta sola, al `CREATE`**,
e non si riaggancia mai più. Sembra un link vivo alla colonna; è una fotografia.

```
2026-03-13  20260313-11 crea la funzione: `cap config.codici_postali.codice%TYPE`
            Allora la colonna era char(n): la firma si congela su bpchar.
2026-04-02  20260402-01-alter-config-codice-char-to-varchar la porta a varchar.
            La firma resta bpchar. Nessuno protesta.
da allora   ogni chiamata fallisce.
```

⚠️ È la stessa meccanica che in `piano-db-ritorno-lotto-a-draft` (M4-quater) ci ha
**salvati**: lì il `%TYPE` in firma si risolse al `CREATE` e fece fallire il
migrate a voce alta. Qui, con la `ALTER` arrivata **dopo** il `CREATE`, ha fatto
il danno in silenzio. Stesso meccanismo, esito opposto: decide l'ordine.

Censimento: **cinque** funzioni dichiarano colonne di ritorno `character` nudo.
Oltre alle due dello stradario ci sono `fn_get_indirizzo`, `fn_get_note`,
`fn_get_soggetto_dati_by_ruolo`: oggi funzionano perché le loro colonne sorgente
sono ancora `char(n)`. Sono **esposte, non rotte**. Le romperà la prossima
`ALTER TYPE` — e a quel punto il presidio le prende subito invece che quattro
mesi dopo. È l'argomento principale per portarlo in CI.

**`fn_prepare_sdi_payload`**: il brief la dava per «rinomina di colonna». Non lo è.
È un task **attivo** (registry id 9) su **due pipeline attive** (MASSIVO id 5,
GIORNALIERO id 7), entrambe con `"force_new_tentativo": false`. Riparato il nome,
il calcolo `COALESCE(MAX,0) + CASE WHEN force THEN 1 ELSE 0 END` dà **0** al primo
tentativo — contro `chk_fatture_sdi_tentativo_num CHECK (> 0)`. Si sarebbe
sostituito «la colonna non esiste» con «viola il CHECK». La forma corretta è
`MAX + 1` sempre. Nessun pgTAP copre questa funzione: la copertura del passo SDI
vale zero.

### F2-dormienti — La coda della migrazione colonne stradario/contatti (4)

| Funzione | Difetto | changeSet |
|---|---|---|
| `script.fn_get_stradario` | `cp.codice_postale` (rinominata 2025-08-17) **+** `character` = char(1) | `-38` |
| `dbops.fn_normalize_indirizzo` | `codice_postale` non esiste | `-58` |
| `script.fn_get_tipo_contatto_id` | `cod_int_tipo_contatto` → `codice_interno` | `-59` |
| `dbops.fn_admin_merge_stradario` | colonne **e valori** sbagliati (vedi §3.2) | `-60` |

Nessuna ha consumatori. Si riparano invece di droppare perché le tabelle
sottostanti sono tutte vive e la logica è completa: manca il nome giusto.

### F4 — Guard che falliscono quando servono (4, `anagrafiche`)

`trgfn_sepa_mandati_guard` (`-40`) · `trgfn_soggetti_conti_bancari_guard` (`-41`) ·
`trgfn_soggetti_ruoli_conti_bancari_guard` (`-42`) · `trgfn_gestori_guard` (`-43`).

Tutte agganciate e vive. Ognuna ha **due** difetti (§3.3): lo schema sbagliato
sulla funzione di log, più `sqlerrm` fuori da un handler / `TGNAME` invece di
`TG_NAME` / argomenti con nome mescolati ai posizionali.
`trgfn_soggetti_conti_bancari_guard` ne ha **tre**: usa anche `NEW.data_al` e
`NEW.data_dal`, che sulla tabella si chiamano `valido_al` e `valido_dal` — e sono
già usati con il nome giusto nell'`IF` due righe sopra.

⚠️ Tutti i rami colpiti sono quelli che **sollevano**: nel caso normale non
vengono nemmeno pianificati. Il guard sembra funzionare, e smette di funzionare
esattamente quando c'è qualcosa da bloccare.

### F3 — Variadici non testuali (4)

`dbops.fn_refresh_mv_ddt_ordini` (`-45`, `integer`) ·
`dbops.fn_run_automations_storico` (`-44`, `text[]` senza `VARIADIC`) ·
`script.trgfn_note_validate_generic` (`-46`, `bigint`, su **sette** tabelle `note_*`) ·
`vendite.trgfn_ordini_ful_guard_consistenza` (`-47`, `bigint`).

Rimedio meccanico — `::text` — ma l'effetto non è cosmetico: quei quattro guard,
**proprio quando scattano**, falliscono con «la funzione non esiste» invece del
messaggio di dominio.

### F5 — Non sono «campi che il record non ha» (4)

| Funzione | Cos'è davvero | changeSet |
|---|---|---|
| `anagrafiche.trgfn_soggetti_conti_bancari_guard` | copia-incolla da un'altra tabella | in `-41` |
| `script.trgfn_qta_from_operativa` | **codice morto** parametrico via `TG_ARGV` | `-52` |
| `vendite.trgfn_documenti_sync_canali` | **ramo per una tabella inesistente** | `-53` |
| 🔴 `vendite.trgfn_preventivi_guard_annullamento` | `NEW.codice` → `numero` | `-54` |

`trgfn_qta_from_operativa`: **nessuna** delle sei tabelle agganciate ha `uom_id`,
`quantita_fissa` non esiste in **nessuna tabella del DB**, e tutti e sei i trigger
passano `'false'` e `'quantita'`. I due rami sono irraggiungibili e accenderli
farebbe fallire ogni riga. Tolti insieme ai due parametri che li governavano
(precedente `20260804-29`); ⚠️ gli argomenti scalano, quindi i sei trigger sono
ricreati **nello stesso changeSet**.

`trgfn_documenti_sync_canali`: il ramo `TG_TABLE_NAME = 'ddt_ordini'` è per una
tabella che non esiste. Con lui se ne vanno due variabili che nessun altro usava.

🔴 `trgfn_preventivi_guard_annullamento` è stata creata **oggi** da `20260804-35`
(cantiere *vie d'uscita operatore*) e usa `NEW.codice`, che su `vendite.preventivi`
non esiste (le colonne sono `numero`, `uid`, `rev`). Il difetto è nel ramo che
solleva: un pgTAP che asserisse solo «solleva» lo vedrebbe verde. Distanza fra
introduzione e scoperta: **poche ore**, e solo perché il controllo è nato lo
stesso giorno.

### F6 — Flusso e tipo di ritorno (3)

`script.fn_get_stato_cliente_by_istanza` (`-55`) — `SELECT` nuda senza `INTO` né
`RETURN`: **non ha mai potuto restituire un valore**. ·
`script.trgfn_prevent_modification_generic` (`-56`) — manca il `RETURN`; oggi
innocuo perché la fn di log solleva sempre, ma la correttezza si appoggia a una
proprietà di *un'altra* funzione. · `dbops.fn_run_automations` (`-57`) — alias `n`
non dichiarato, nel ramo fallback che si prende solo se `dbops.automation_scope`
è vuota (oggi ha 14 righe: mai preso).

### F1 — Non è una famiglia sola (3 + 2 residui che il check non vede)

| Oggetto | Come è morto | changeSet |
|---|---|---|
| `vendite.fn_list_attivita_sorgenti_abilitate` | `CASCADE` del 2026-02-27 | `-48` |
| `vendite.trgfn_attivita_fatturabili_lotti_gen_codice` | `CASCADE` del 2026-02-27 | `-48` |
| `vendite.trgfn_attivita_fatturabili_guard_fonte` | 🔴 **riuso del nome di trigger** | `-48` |
| sequenza `attivita_fatturabili_lotti_codice_seq` | sopravvissuta al `CASCADE` | `-49` |
| riga 13 di `config.sistema_codici` | riferimento morto **in un dato** | `-50` |

**Il brief le metteva tutte sotto «coda del drop». La terza no**, e la differenza
conta perché è un modo di morire che nessun presidio sul drop di tabella
intercetta:

```
2025-08-29  20250829-12 crea funzione e trigger su attivita_fatturabili
2025-11-19  20251119-31 rinomina il trigger (giro di allineamento nomi)
2025-10-26  20251026-02 DROP TRIGGER … + CREATE TRIGGER **con lo stesso nome**
                        puntato a script.trgfn_guard_sorgente_polimorfa
                        ^^^ qui la funzione si stacca, e nessuno se ne accorge
2026-02-25  20260225-45 droppa anche quel trigger
```

Ed è morta **tre volte**: nessun trigger la usa · legge
`vendite.regole_fatturazione_articolo`, che non esiste (è
`vendite.articolo_regole_fatturazione`) · valida `fonte_quantita`, colonna che non
esiste **in nessuna tabella del DB**. Nemmeno riagganciandola potrebbe funzionare.

⚠️ **Le regole che dichiarava sono scoperte?** Verificato prima di droppare:
`competenza_dal <= competenza_al` e `competenza_mese` al primo del mese sono
CHECK; il riempimento di `competenza_dal/al` lo fa
`trgfn_attivita_fatturabili_normalize` (vivo); la regola su `fonte_quantita` è
**estinta**. Resta scoperta la sola «`data_attivita` dentro l'intervallo di
competenza» → **decisione aperta n.1**.

⚠️ **Il punto cieco del presidio.** `plpgsql_check` compila i corpi: la sequenza e
la riga di `config.sistema_codici` erano invisibili al primo giro. Da qui la
**seconda misura**, che cerca i riferimenti a tabelle inesistenti nei dati di
configurazione. Al 2026-08-04 trovava una riga: quella.

### F7 — Tre residui, e uno che non si tocca (4)

| Funzione | Verdetto | changeSet |
|---|---|---|
| `trgfn_contratti_guard_modalita_c_activation` | residuo: trigger droppato da `20260515-10` | `-51` |
| `trgfn_contratti_righe_guard_modalita_c` | residuo: idem | `-51` |
| `trgfn_contratti_righe_componenti_guard_pending` | superata dal generico `script.trgfn_componenti_guard_pending` | `-51` |
| 🔴 `script.trgfn_guard_sorgente_polimorfa_tipizzata` | **orfana di proposito, non si tocca** | registro |

Il brief poneva la domanda giusta — *«il problema potrebbe essere il trigger
mancante, non la funzione di troppo»*. Verificato una per una: in tutte e quattro
l'assenza del trigger è **deliberata e documentata nel changeSet che l'ha
causata**. Nessun presidio scoperto: la logica sostitutiva (Step 2.3 del refactor
contratti, e il generico dei componenti) è in servizio.

La quarta è il caso interessante. `20260718-16` la documenta:

> «⚠️ NON agganciata: il trigger su attivita_fatturabili (suo target di progetto)
> fu rimosso DELIBERATAMENTE con 20260225-45. Il riaggancio (D6) è quindi da
> ri-decidere con Tid … la funzione resta disponibile, documentata come NON attiva.»

⚠️ **È il limite strutturale della classe `ORFANA`**: distingue «con trigger» da
«senza trigger», non «residuo» da «parcheggiata». La differenza sta
nell'intenzione, che nessuna query trova. Da qui il **registro delle esenzioni
motivate**: questa funzione ne è la prima e unica voce.

---

## 5. Il presidio, che è il punto

Sistemare i difetti senza presidio significa ritrovarsi qui fra sei mesi.

I pezzi, e nessuno duplica la logica di un altro:

| Pezzo | Dove | Ruolo |
|---|---|---|
| `dbops.fn_check_funzioni_riferimenti_morti()` | `-62` | la misura + classificazione |
| `dbops.riferimenti_morti_esenzioni` | `-63` | il registro del debito |
| `dbops.vw_riferimenti_morti_da_sanare` | `-64` | difetti non registrati → il lavoro |
| `dbops.vw_riferimenti_morti_rientrati` | `-64` | voci di troppo → righe da togliere |
| `check_funzioni_riferimenti_morti.sql` | `scripts/sql/` | lo strumento a mano (stampa anche gli FP) |
| `guardrail_riferimenti_morti.sql` | `scripts/sql/` | il gate della CI |
| `test-riferimenti-morti-v1.sql` | `db/pgtap/dbops/` | il gate della suite |

**La misura sta nel DB** proprio perché la chiamano in tre: se vivesse in un file,
qualcuno dovrebbe ricopiarla, e il giorno in cui le copie divergono CI e sviluppo
danno risposte diverse sullo stesso difetto — che è il modo di fallire da cui
nasce questo cantiere.

### ⚠️ È un debito, non un elenco di eccezioni

Stessa filosofia di `db/pgtap/baseline-rossi.tsv`: **deve calare**. Due presidi lo
tengono onesto, e stanno in due posti diversi apposta:

* **«senza motivo non si registra»** → un `CHECK` sulla tabella. Non è un test che
  si può dimenticare di lanciare: è il DB che rifiuta la riga. La soglia di 40
  caratteri non è arbitraria — è la lunghezza sotto la quale non ci sta una
  spiegazione, ci sta solo un'etichetta («da vedere», «legacy», «poi»).
* **«una voce rientrata va tolta»** → il test 3 del pgTAP e il controllo (B) del
  guardrail, perché per saperlo bisogna ri-misurare e una misura non è un vincolo.
  Senza, il registro può solo allungarsi — e diventa il posto dove i problemi
  vanno a sparire, cioè `20260331-26`.

### Il punto di partenza è zero, non 34

Il brief prevedeva un primo giro rosso su 27, «e va bene: serve a fissare il punto
di partenza». Non serve: i changeSet `-37..-60` sanano **tutto**, e il registro
nasce con **una** voce — che non è un debito da pagare ma una decisione già presa.
Un registro che nasce con 34 righe è un registro che nessuno legge.

### In CI

Deciso il 2026-08-04: **sì**. Due passi in `ci-validate.yaml`:

1. installazione di `postgresql-18-plpgsql-check` nel container del service
   Postgres via `docker exec` (l'immagine `postgis/postgis:18-3.6` ha già il repo
   PGDG). Va **prima** del giro provision: il changeSet `-36` è condizionale su
   `pg_available_extensions` e si riprende da solo appena il pacchetto c'è.
2. il guardrail, accanto a quello del naming `codice_interno` — stesso schema:
   `psql -v ON_ERROR_STOP=1 -f`, un `RAISE` rende rosso il passo.

⚠️ Se l'estensione manca, il guardrail **fallisce** invece di saltare. Un
guardrail che passa perché non ha misurato niente è peggio di uno assente: dà la
sensazione della copertura senza averla, che è esattamente ciò che è successo a
`test-fn-search-stradario.sql` sotto l'etichetta `ERRORE_FIXTURE`.

---

## 6. Decisioni

### Chiuse il 2026-08-04

| # | Domanda | Risposta |
|---|---|---|
| 1 | F1 si droppa o si riscrive? | **Droppa.** Morte tre volte, zero consumatori in sei sedi |
| 2 | F7: manca la funzione o il trigger? | **La funzione è di troppo** in 3 casi su 4; il 4° è parcheggiato di proposito |
| 3 | Il presidio va in CI? | **Sì**, pacchetto nell'immagine + guardrail |
| 4 | `trgfn_qta_from_operativa`: rami morti? | **Tolti**, coi due parametri che li governavano |
| 5 | `fn_admin_merge_stradario`: riparare o droppare? | **Riparare**, nomi **e** valori |

### Aperte

1. **La regola «`data_attivita` dentro l'intervallo di competenza» va rifatta?**
   Era in `trgfn_attivita_fatturabili_guard_fonte`, che si droppa. Le altre regole
   di quel guard sono coperte da CHECK o dal normalize; questa no. Riportarla in
   vita è una decisione di dominio, non una bonifica.
2. **`fn_admin_merge_stradario` deve anche ritirare la via sorgente?** Oggi dopo la
   fusione `p_id_orig` resta selezionabile. Se deve sparire dalle scelte, il modo
   è il pattern `obsoleto_dal`, non `attivo = false`.
3. **`fn_refresh_mv_ddt_ordini` usa `pg_try_advisory_lock` a un argomento**, contro
   la regola di progetto che vuole la forma a due (namespace + chiave). Cambiarla
   vuol dire assegnare un namespace: cantiere a parte.
4. **`trgfn_prevent_modification_generic` logga un `p_function_name` sbagliato**
   (`trgfn_prevent_parameters_audit_modification`, nome di un'altra funzione). Non
   rompe niente, ma sporca i log.

---

## 7. Registro di avanzamento

| Passo | Stato | changeSet |
|---|---|---|
| Analisi critica delle 33 righe contro il DB vivo | ✅ fatta | — |
| Classificatore v3 (regola VARIADIC stretta + 2ª misura sui dati) | ✅ fatto | `scripts/sql/` |
| F2-vivi | ✅ applicato | `-37` `-38` `-39` |
| F4 | ✅ applicato | `-40` `-41` `-42` `-43` |
| F3 | ✅ applicato | `-44` `-45` `-46` `-47` |
| F1 | ✅ applicato | `-48` `-49` `-50` |
| F7 | ✅ applicato | `-51` |
| F5 | ✅ applicato | `-52` `-53` `-54` |
| F6 | ✅ applicato | `-55` `-56` `-57` |
| F2-dormienti | ✅ applicato | `-58` `-59` `-60` |
| Presidio (misura, registro, viste, seed) | ✅ applicato | `-62` `-63` `-64` `-65` |
| pgTAP `test-riferimenti-morti-v1.sql` | ✅ **5/5 verde** | — |
| Guardrail + 2 passi in `ci-validate.yaml` | ✅ guardrail provato a mano (exit 0); i due passi CI vanno esercitati alla prossima pipeline | — |
| Brief per il BE | ✅ [`brief-be-bonifica-riferimenti-morti.md`](brief-be-bonifica-riferimenti-morti.md) | — |

### ✅ Verifiche dopo il migrate (2026-08-04, 20:45)

1. ✅ **Ri-misurato**: `vw_riferimenti_morti_da_sanare` = **0**,
   `vw_riferimenti_morti_rientrati` = **0**, registro = **1** voce.
2. ✅ **Provate davvero** le funzioni su percorso vivo, non solo compilate — ed
   era il punto, perché il secondo difetto di `fn_prepare_sdi_payload` non si
   vedeva alla compilazione:
   * `fn_search_stradario('roma')` → righe, `provincia_sigla = 'FM'` (non più
     paddata a 10), `cap = '63815'`;
   * `fn_get_stradario(<comune>)`, il ramo che era KO → righe;
   * `fn_prepare_sdi_payload(603)` con `force=false` → `tentativo_num = 1`
     (prima 0, cioè violazione del CHECK); con `force=true` → 2.
3. ✅ **pgTAP del presidio**: 5/5 verde. **Guardrail CI** provato a mano: exit 0.
4. ✅ **`test-fn-search-stradario.sql` è rientrato**: 8/8 verde, riga tolta da
   `baseline-rossi.tsv`. La classificazione `ERRORE_FIXTURE` era sbagliata, come
   sostenuto al §4 — se non fosse rientrato, l'analisi sarebbe stata da rifare.

### ⚠️ Tre rossi comparsi nella baseline che NON vengono da qui

`pgtap-baseline.sh script vendite anagrafiche dbops` li segnala come regressioni
perché la baseline è stata aggiornata alle **14:16** e loro sono nati dopo. Non
sono di questo cantiere, e la prova è nei timestamp:

| Test | Causa | Quando |
|---|---|---|
| `script/test-fn-available-actions-preventivo-v1` | `config.transizioni_stati_preventivi` riga ACCETTATO→ANNULLATO attivata | **13:25:58** |
| `script/test-fn-available-actions-ordine-v1` | `config.transizioni_stati_ordini` idem | **13:25:58** |
| `anagrafiche/test-fn-crea-auth-user` | loader `messaggi_errore` ri-eseguito | **16:17** |

Il mio migrate è delle **20:45**, e fra le 14:20 e le 20:40 è girato **un solo
changeSet** (quello dei messaggi). I primi due vengono dal cantiere *vie d'uscita
operatore* (`20260804-33/34/35`), che ha riacceso l'azione `annulla`: i test
dicono ancora *«22-05: annulla solo da DRAFT»*, sono **stale** e vanno adeguati
lì — stesso caso dei «pgTAP di terzi adeguati» del cantiere *ritorno a DRAFT*.

Il terzo è più interessante e va detto a chi tocca `anagrafiche`:
`throws_matching(..., 'E_ADMIN_USERNAME_DUPLICATO')` confronta il **messaggio**,
ma `fn_log_and_raise_error` solleva il messaggio *localizzato* e mette il codice
in `ERRCODE`/`HINT`. Il test passava **solo perché quel messaggio mancava dal
seed**: ora c'è (`Username gia' in uso.`) e il test cade. Il rimedio è asserire
sul **codice**, non togliere la riga dal seed. Dettagli nel brief BE §4.

### ⚠️ Accendere il presidio in CI: tre giri rossi, e cosa hanno insegnato

Il guardrail non è passato al primo colpo, ed è la parte più istruttiva del
cantiere: **un presidio scritto non è un presidio acceso**, e la differenza si
paga tutta la prima volta che gira davvero.

| Giro | Errore | Causa | Fix |
|---|---|---|---|
| 1 | `mislabel: VIEW vendite.vw_dash_competenza_attivita` | non nostro: `20260804-28` esponeva `codice_interno AS commessa_stato_codice` | `-67` (4 viste, no CASCADE) |
| 2 | «Estensione plpgsql_check assente» | `20260804-36` ha `context: provision` e vive in `migrations_v2`: la CI lancia il master con `--contexts="!provision"` e i passi di provision usano changelog **separati** | include esplicito in `changelog-provision-pre.yaml` |
| 3 | 11 `REALE` su `django.auth_user` + 2 `ORFANA` | vedi sotto | passo spostato dopo `manage.py migrate` + `-68` |

**Il guardrail ha fatto il suo mestiere in tutti e tre.** Al giro 2 in particolare:
avendo scelto di **fallire** invece di saltare quando l'estensione manca, ha detto
ad alta voce che non poteva misurare. Con lo `skip` silenzioso — l'alternativa
comoda — la pipeline sarebbe stata verde con copertura zero, e ce ne saremmo
accorti fra sei mesi. È lo stesso modo di fallire da cui nasce questo brief.

#### 🔴 `django.auth_user`: il database è completo solo dopo **due** migratori

Una decina di funzioni DB leggono `django.auth_user`, che crea `manage.py
migrate`, non Liquibase. Il guardrail stava a valle di Liquibase e a monte di
Django: misurava un database a metà e produceva dieci falsi difetti. Spostato
dopo il migrate di Django.

Non è un dettaglio di ordinamento: dice che in questo progetto lo schema non ha
un proprietario solo, e qualunque controllo sulle *definizioni vive* deve girare
quando entrambi hanno finito.

#### 🔴 Incrementale ≠ costruito da zero

Due trigger function orfane comparse **solo in CI**: sul server di sviluppo non
esistono, e i changeSet che le droppano (`20250922-01/02/03`) risultano
`EXECUTED`. Stanno però nel tree legacy `migrations/`, incluso con `includeAll`
alfabetico: l'ordine relativo fra chi crea e chi droppa regge su un database
cresciuto nel tempo e non regge su uno costruito da zero.

⚠️ È la scoperta più scomoda del cantiere, e vale ben oltre queste due funzioni:
**il DB di sviluppo e un DB ricostruito dai changelog non sono lo stesso
oggetto**, anche partendo dagli stessi file. Tutto ciò che verifichiamo solo su
dev — e fin qui era *tutto* — verifica lo stato di una macchina, non la
riproducibilità delle migrazioni. La CI, la prima volta che ha guardato davvero
dentro le funzioni, l'ha vista subito.

Corretto in avanti con `-68` (in `migrations_v2`, che il master include dopo
tutto il legacy), perché toccare changeSet del 2025 già mergiati romperebbe la
sequenza dei checksum. Su dev è un no-op.

### ⬜ Resta da fare

1. ~~Commit~~ ✅ fatto (restano da committare `-67`, `-68`, il riordino CI e il
   pgTAP SDI).
2. ~~pgTAP per `fn_prepare_sdi_payload`~~ ✅ fatto:
   [`db/pgtap/vendite/test-fn-prepare-sdi-payload-v1.sql`](../../../../db/pgtap/vendite/test-fn-prepare-sdi-payload-v1.sql),
   `plan(10)` verde. Il test 7 è quello che tiene chiuso il secondo difetto (il
   tentativo a 0), e **è stato verificato che coglierebbe la regressione**:
   rimettendo la vecchia formula in transazione, l'INSERT viene respinta da
   `chk_fatture_sdi_tentativo_num`. Un test che passa senza saper fallire non
   presidia niente, quindi la prova andava fatta.
   ⚠️ Copertura **condizionata**: la fixture sceglie un lotto con fatture dai dati
   esistenti, quindi su un DB appena migrato i test 7-10 fanno skip — proprio i
   quattro che contano. Dichiarato in testa al file.
3. **Esercitare i due passi CI** alla prossima pipeline: l'installazione di
   `postgresql-18-plpgsql-check` via `docker exec` è l'unico pezzo non ancora
   provato sul campo.
4. **Doc auto-gen dbzero**: la rigenera Tid. I due manuali delle funzioni
   droppate (`trgfn_attivita_fatturabili_guard_fonte`,
   `trgfn_contratti_righe_componenti_guard_pending`) sono già rimossi, e i due
   «Vedi anche» che li linkavano sono stati ripuntati.
5. **Brief BE** da evadere: [brief-be-bonifica-riferimenti-morti](brief-be-bonifica-riferimenti-morti.md).
