# Sei richieste al team DB dal lato applicativo · *nota di credito*

> **Cos'è.** Le sei cose che il piano BE/FE di
> [brief-design-note-credito-resi.md](brief-design-note-credito-resi.md)
> (**PARTE IV**, §21 → §26) **non può scrivere da sé**, perché stanno nel
> database. Tutto il resto del piano procede in parallelo e non le aspetta —
> tranne dove è scritto il contrario nella colonna «blocca».
>
> **Origine.** Emerse il **2026-08-18**, scrivendo il piano BE/FE contro il
> codice applicativo vivo e contro l'apply DB dello stesso giorno
> (`06b661061`, changeSet `20260818-24` → `-46`).
>
> **Destinatario**: team DB, branch `dev/db-tid`.
> **Autorizzazione**: Tid, 2026-08-18 — tutte e sei confermate nel merito, con
> tre decisioni di dominio prese in chat (D-NC-11, D-NC-12, P-4) e registrate
> nel §21.4 del brief principale.
>
> ⚠️ **Perimetro dichiarato**: siamo **solo in ambiente di test**. Breaking
> change ammessi, nessuna fase di compatibilità, nessun backfill.
>
> ✅ **Analisi critica e piano di sviluppo del team DB: §7 e §8**, in fondo.
> In due righe: **P-1/P-2/P-3/P-4 reggono** (e la domanda aperta di P-2 ha
> risposta: *no*, ma per un motivo diverso da quello scritto); **P-5 va
> corretto** — un accredito non è una riga, è N; **P-6 è reale ma non è
> «collisione»** — sono buchi nella serie, ed **ha un prerequisito** che il
> cantiere perimetro emittente, **chiuso il 2026-08-18**, ha lasciato **in
> carico a P-6** (§11.11): non è più un'attesa, è lavoro di qui.
>
> ✅ **La misura di P-6 è stata fatta** (C-5) e le **tre decisioni aperte sono
> chiuse** (D-P6-1/2/3, §8 passo 5).

---

## ✅ CHIUSO — 2026-08-19

> Tutti e sette i passi sono applicati e verdi. Il brief è in `work-done`.
>
> Ultimi due: **P-3** (`20260819-02`, il gate della rinuncia si è svegliato) e
> **P-6** (`20260819-03/-04/-05`, i registri sono intestati agli emittenti),
> con `test-rinuncia-gate-accredito-v1` 8/8, `test-registri-per-emittente-v1`
> 6/6 e 12 suite di regressione sulla numerazione. **P-7** era già chiuso
> (`20260818-75`).
>
> Le due richieste al lato applicativo che ne discendevano sono **fatte**
> (2026-08-19): la chiave i18n `vendite.resi.rinuncia_reason.accredito_eseguito`
> in `it.json`/`en.json`, e `error_policies_generated.py` per il codice **929**
> `E_RESO_RINUNCIA_ACCREDITO_ESEGUITO` — quest'ultimo era già rigenerato, con il
> ripiego, nel commit del BE.
>
> ⚠️ **Resta una conseguenza operativa aperta, e non è del cantiere**: da oggi
> non esiste più un registro generico, quindi «aggiungere un emittente» non è
> più una riga di anagrafica. Vedi in fondo.

## ▶ Stato del cantiere — 2026-08-18, fine giornata

> Aggiornato dopo l'apply di Tid. ⚠️ Istantanea: prima di citarla, verificare
> contro il codice.

| Passo | Cosa | Stato |
| --- | --- | --- |
| **1** · P-1 | l'azione di processo `accredita_riga_reso` (id 31) | ✅ **applicato** |
| **2** · P-2 | il task `popola_fatture_rettifiche` a registry, impl, pipeline e task_policy · `20260818-68` (numero esplicito in `fn_check_lotto_annullabile`) · `20260818-69` (il commento che spiega perché `fn_cleanup_fatture_by_ids` **non** si tocca) | ✅ **applicato** |
| **3** · P-5 | `20260818-71` — `fn_annulla_accredito_riga_reso` + 4 codici (924-927) + 18 pgTAP | ✅ **applicato e verde** |
| **§10** | `20260818-73` — il conto della merce smette di contare l'annullato | ✅ **applicato e verde** |
| **4** · P-3 | il gate della rinuncia in `fn_check_rinuncia_reversibile` | ✅ **applicato e verde** (§12) |
| **5** · P-6 | i registri per emittente | ✅ **applicato e verde** (§12). ⭐ Il prerequisito 5b è rientrato qui, come il cantiere perimetro emittente aveva scritto |
| **6** · P-7 | il `meta` kit della rettifica: ereditato per intero + guard 928 · `20260818-75` | ✅ **applicato e verde** — trovato dallo smoke end-to-end del BE, verificato dallo stesso smoke (15/15) |

**Verifica end-to-end** (2026-08-18): sette file pgTAP verdi, compresi i sei che
insistono sul conto della merce — nessuna regressione. Dettaglio in §10.

🔴 **Fuori dal perimetro DB, e bloccanti per il giro end-to-end**: le richieste
**BE-4/BE-5** del §17 del brief principale (il generatore righe non deve
aggregare le rettifiche e deve copiare prezzo/sconto/IVA dalla riga rettificata,
scrivendo `riga_rettificata_id`) e **BE-6** (rigenerare
`error_policies_generated.py` — ora per **sei** codici nuovi: i 4 dell'annullo
più quelli del cantiere).

---

| # | Cosa | Peso | Blocca |
| --- | --- | --- | --- |
| **P-1** | Azione di processo `accredita_riga_reso` | 1 riga di CSV | ⛔ la **consegna** del verbo (B2, F1) |
| **P-2** | Registry del task `popola_fatture_rettifiche` + il task nelle pipeline 4 e 6 | 2 righe di registry + 2 JSON di seed | ⛔ la slice **B6** |
| **P-3** | 🔴 Il gate `fn_check_rinuncia_reversibile`, rimasto dormiente | un ramo dentro una fn esistente + 1 codice a catalogo | 🔵 niente lato BE — è un buco di dominio aperto **adesso** |
| **P-4** | I quattro valori del sezionale NC | ✅ **nessun lavoro**: confermati come seedati | — |
| **P-5** | 🔴 La madre `fn_annulla_accredito_riga_reso` | 1 fn nuova + 2 codici a catalogo | ⛔ la slice **B2-bis**, F1 |
| **P-6** | 🔴 Nessun registro è intestato a un emittente, e gli emittenti che emettono sono **due** | riconfigurazione del seed registri + mapping | ⛔ niente di BE/FE — è un **difetto fiscale in esercizio** |
| **P-7** | ✅ **CHIUSO** (`20260818-75`) — il `meta` della riga rettificata si **eredita** invece di copiarne due chiavi, più il guard `E_ACCREDITO_KIT_SENZA_PADRE` (928) | 1 fn + 1 codice | era ⛔ la nota di credito su **articoli compositi**; smoke B8 ora 15/15 |

---

## Il contesto in tre righe

Il perimetro DB della nota di credito è **chiuso e applicato**: la madre
`fn_accredita_riga_reso` esiste, il ponte `resi_righe_accrediti` esiste, la coda
espone `gia_accreditato`, l'asse `natura` viaggia lungo la catena, il sezionale
NC numera. Il piano BE/FE che ci si appoggia sopra è scritto.

Queste sei sono ciò che quel piano ha **trovato** leggendo il codice: tre sono
prerequisiti operativi (P-1, P-2, P-4), tre sono **buchi di dominio** che
nessuno aveva ancora nominato (P-3, P-5, P-6).

---

## ✅ P-1 — L'azione di processo `accredita_riga_reso`

**Cosa serve.** Una riga in `db/changelog/migrations_v2/80_data/sql/config/azioni_processo.csv`:

```text
id   = 31 (il progressivo si riconta prima di scrivere)
area_id = 2  (vendite)
permission_codename = accredita_riga_reso
descrizione = Accredita riga di reso (genera la rettifica per la nota di credito)
pericolosa  = t
attivo      = t
```

**Perché.** L'endpoint del verbo dichiara `post_permission = "accredita_riga_reso"`
(BE-3 del §17.1): è la porta di un **documento fiscale**, e il presidio sta sul
backend perché la madre deve restare usabile da un processo autorizzato.

⚠️ **Fino al seed il verbo è fail-closed**: `ZeroERPPermission` non risolve un
codename che non è a catalogo, quindi resta accessibile al solo SUPER_ADMIN. È
lo stesso precedente di `code_manage` (area `strumenti`, luglio 2026). Si può
sviluppare, non si può consegnare.

**`pericolosa = t` — la ragione.** Il flag segnala *«le azioni che richiedono
conferma aggiuntiva»*. Precedenti a `t`: `genera_fatture_lotti`,
`numera_fatture_lotti`, `cambia_stato_commessa` — tutte cose che finiscono in un
documento fiscale. Precedenti a `f`: `carica_voce_manuale`,
`approva_attivita_commessa`, che restano dentro la commessa. L'accredito è del
primo gruppo.

---

## ✅ P-2 — Il registry del task `popola_fatture_rettifiche`

**Cosa serve, ~~tre~~ QUATTRO pezzi.**

> ⚠️ **rev 2026-08-18 — erano tre e il quarto mancava.** Il seed è stato scritto
> con i primi tre e ha prodotto **due rossi** che non erano nella baseline:
> `test-pipeline-processi-invariante-v1` (test 7) e
> `test-pipeline-definitiva-numerazione-stampa-v1`. Il pezzo dimenticato è il 4.

1. `dbops.pipeline_task_registry`: il task `popola_fatture_rettifiche` sul
   dominio `vendite`;
2. `dbops.pipeline_task_registry_impl`: `implementation_key = default`,
   **`handler_code = popola_fatture_rettifiche_default`** — è la stringa esatta
   con cui il backend registra l'handler nel `handler_registry` di
   `PipelineStepExecutor`;
3. `vendite/fatturazione_pipeline.csv`, righe **4** (massiva DEFINITIVA) e **6**
   (giornaliera DEFINITIVA): il task nel JSON `processi`, **fra
   `numera_fatture` e `stampa_documenti_lotto`**;
4. ⭐ `vendite/fatturazione_pipeline_task_policy.csv`: **una riga per corsia**
   (id 24 su pipeline 4, id 25 su pipeline 6), `annullabile=f`,
   `resume_mode=RESUME_TASK`.

**Perché il pezzo 4 non è cosmetico, ed è la parte che si vede solo leggendo il
runner.** `PipelineStepExecutor._run_task` apre il tracing dentro un
`if self.repository.task_policy_exists(pipeline_id, task)`. Senza la riga di
policy il task **non si ferma**: gira, e gira **fuori dal tracing**. Nessuna riga
in `vendite.fatturazione_lotti_task_runs`, nessuna risoluzione
`RUN/SKIP/RESUME/RESET_REQUIRED`, nessuno `SKIP` al secondo giro. È fail-**open**
e silenzioso — l'opposto di `fn_resolve_lotto_task_execution_mode`, che con la
riga assente solleverebbe `E_CONFIG_MANCANTE`, ma che senza `task_policy_exists`
non viene mai chiamata.

Su una tappa senza `rollback`, per un task che scrive
`vendite.fatture_rettifiche` su documenti **già numerati**, stare fuori dal
tracing è esattamente il posto dove non si vuole essere.

**I valori, e perché.**

* `resume_mode = RESUME_TASK` — `fn_popola_fatture_rettifiche` è idempotente
  (`ON CONFLICT DO NOTHING`) e non cancella mai: rieseguire il solo task è
  sicuro. Lo stesso valore di `stampa_documenti_lotto`, non quello di
  `numera_fatture` (`RESUME_STEP`: i numeri non si bruciano due volte);
* `annullabile = f` — come `numera_fatture` e a differenza di
  `stampa_documenti_lotto`. La proiezione si scrive su un documento numerato e
  `fn_cleanup_fatture_by_ids` **non** cancella `fatture_rettifiche`: non c'è un
  percorso che la disfi. ⚠️ Oggi il campo è letto in `TaskExecutionMode` e non
  consumato a valle: il valore è una **dichiarazione di semantica**, non ancora
  un comportamento.

**Effetto collaterale, e non è di questo cantiere.** Aggiungendo le due righe si
è visto che la sequenza identity di `fatturazione_pipeline_task_policy` era ferma
a **11** con `MAX(id) = 23`: `loadUpdateData` inserisce gli id del CSV e non
avanza la sequenza. Misurando su tutto il database sono uscite **sei** sequenze
indietro, tutte fuori da `ui` e `config` — cioè fuori dai due soli schemi che
avevano un presidio. Chiuso da `20260818-73` in `90_end`, forward-only e globale.
⚠️ Non è un problema *di questa tabella*: è che il presidio era per-schema e
nasceva ogni volta dopo il danno.

```json
{"task":"popola_fatture_rettifiche",
 "fase":"Legame documentale note di credito",
 "params":{"implementation_key":"default"}}
```

**Perché sta lì e non dopo la generazione righe** — è la parte che il piano ha
dovuto trovare, e vale la pena scriverla:

* **il reset non deve incontrare la proiezione.** `fn_cleanup_fatture_by_ids`
  cancella note, riepiloghi IVA, righe, log, il collegamento al lotto e le
  testate — e **non** `vendite.fatture_rettifiche`. `fk_fatture_ret_fattura` non
  è `ON DELETE CASCADE`: con la proiezione scritta in DRAFT, il primo reset di
  lotto sbatterebbe su una violazione di chiave esterna grezza, su una funzione
  che i suoi tre chiamanti (`fn_annulla_lotto_da_draft`,
  `fn_elimina_fattura_da_lotto_draft`, `fn_riporta_lotto_a_draft`) danno per
  infallibile. Dopo la numerazione il reset non arriva: tutti e tre sono
  `*_da_draft`;
* **la stampa viene dopo.** Una TD04 porta `DatiFattureCollegate`, cioè numero e
  data del documento rettificato: il PDF va costruito quando il legame esiste.

⚠️ Lato backend la dipendenza d'ordine viene **dichiarata** in
`_TASK_ORDER_DEPENDENCIES` (`popola_fatture_rettifiche` → `numera_fatture`), che
la verifica **prima** che il primo task dello step scriva. Non ci si affida al
solo ordine del seed.

⚠️ **Domanda per il team DB, e non è retorica**: esiste un percorso di reset che
possa raggiungere un documento **numerato**? Se sì, `fn_cleanup_fatture_by_ids`
deve cancellare anche la coppia in `fatture_rettifiche` — e la cancellazione va
lì, non aggirata in Python.

---

## 🔴 P-3 — Il gate della rinuncia è rimasto dormiente

**Il fatto.** `script.fn_check_rinuncia_reversibile` ritorna ancora `[]` per
qualunque riga esistente. Il suo commento vivo dice, parola per parola:

> **STATO ATTUALE: ritorna SEMPRE []. È deliberato, non incompleto.** […]
> ⚠️ **QUANDO ARRIVERÀ LA SLICE NC: il divieto va aggiunto QUI, e si attiva da
> sé** — `fn_riapri_riconsegna_reso` solleva già il primo motivo che questa
> funzione produce. Non serve toccare la madre.
> Motivo previsto: la quota rinunciata risulta coperta da una nota di credito
> emessa → riaprirla sfalserebbe un documento fiscale.
> Codice da registrare allora (non oggi, per non lasciare a catalogo un codice
> mai sollevato).

**La slice è arrivata, e il punto d'innesto è ancora un commento vuoto.**
Ne discende che **oggi si può riaprire una rinuncia su una quota già
accreditata**. Il §20 non lo nomina fra i residui.

**✅ La soglia, decisa da Tid il 2026-08-18 (D-NC-12): il divieto scatta AL
VERBO**, cioè appena esiste una riga in `vendite.resi_righe_accrediti` per
quella riga di reso — non alla numerazione della NC.

**Perché al verbo e non all'emissione:** è la stessa soglia che il perimetro DB
ha già scelto altrove. La correzione §20.3 ha fatto in modo che *«la riga esce
dalla coda AL VERBO e non alla generazione della fattura: l'idempotenza smette
di dipendere da una finestra temporale»*. Mettere qui una soglia diversa
aprirebbe una finestra lunga quanto il batch in cui la coda dice «accreditata» e
la rinuncia dice «ancora reversibile» — due macchine coerenti con sé stesse e in
disaccordo fra loro.

**Cosa serve:**

* il motivo nel punto d'innesto della funzione — forma già stabilita dalla
  funzione stessa: `{codice, reason, reason_key, dettaglio}`;
* **un codice errore a catalogo**, che il commento dice esplicitamente di non
  aver registrato prima *«per non lasciare a catalogo un codice mai sollevato»*.
  Ora si solleva;
* ⚠️ una chiave i18n per il `reason_key`, sul modello di
  `vendite.resi.rinuncia_reason.riga_inesistente` che c'è già. Il frontend la
  legge con `labelOrCode` (fail-visible): senza, mostra il codice grezzo.

⭐ **La madre non si tocca**: `fn_riapri_riconsegna_reso` solleva già il primo
motivo prodotto. È il pregio del disegno di luglio, e va usato.

---

## ✅ P-4 — I quattro valori del sezionale NC: nessun lavoro

Confermati da Tid il 2026-08-18 **così come già seedati** (`20260818-44/-45`):

| Valore | Deciso |
| --- | --- |
| `codice` | `NC` |
| `descrizione` | «Note di credito» |
| `serie_default` | vuota — il registro è già distinto |
| `reset_policy` | `ANNUALE`, come le fatture |

⚠️ **Con una riserva, che è P-6**: la conferma riguarda i quattro valori, **non**
il fatto che il registro non sia intestato a un emittente. Quella parte si
riapre qui sotto.

---

## 🔴 P-5 — L'annullo dell'accredito (D-NC-11)

**Il fatto, misurato.** Dopo il verbo **non esiste nessuna strada indietro**:
nessuna funzione cancella da `vendite.resi_righe_accrediti`, e l'endpoint
`ANNULLA riga manuale` delle commesse non copre la rettifica — il suo perimetro
sono le righe **sourceless**, e la rettifica porta `DDT:<uid>:R:<id>#RET:<n>`.
E anche se lo coprisse non toglierebbe la riga di ponte, quindi la coda
resterebbe muta per sempre.

**✅ Decisione di Tid (2026-08-18), in due tempi — il secondo corregge il primo.**

Prima: *«serve l'annullo»*. Subito dopo, la correzione che ne fissa la forma:

> *«anche il fatto che una nota credito possa essere cancellata/annullata:
> valgono le stesse regole della fatturazione, il processo deve finire nella
> pipeline»*

⭐ **Ne discende la distinzione che la prima stesura non faceva: sono DUE cose.**

```text
ANNULLARE IL DOCUMENTO   →  ESISTE GIÀ, ed è la pipeline. Niente da fare.
   reset del lotto in DRAFT → fn_cleanup_fatture_by_ids riporta
   commesse_attivita a NON_EMESSA e sblocca le attivita_fatturabili
   ⭐ quindi la rettifica torna disponibile e il giro dopo RIGENERA la NC.
      Ed è CORRETTO: la merce resa non è cambiata, l'accredito è ancora dovuto.
   ⛔ oltre la numerazione non si annulla niente, come qualunque fattura.

ANNULLARE L'ACCREDITO    →  MANCA. È il caso «ho cliccato la riga sbagliata»,
   sta A MONTE del documento, e non è ciò che il reset fa.
```

**Forma richiesta: `vendite.fn_annulla_accredito_riga_reso(p_resi_riga_id bigint)`**,
con le precondizioni **prese dalla catena, non inventate**:

1. **guard sul parametro** — `NULL` o `<= 0` → errore parlante, mai
   normalizzazione silenziosa (AGENTS.md);
2. ammesso **solo** se la rettifica è `stato_emissione = 'NON_EMESSA'`, non
   `fatturato`, e non agganciata a un lotto vivo (`lock_in_fatturazione` falso).
   Sono le stesse condizioni con cui la catena tratta qualunque attività non
   ancora emessa;
3. **non cancella l'attività**: la porta a `stato_emissione = 'ANNULLATA'` —
   valore che tutte le porte verso fattura e cockpit già filtrano. ⭐ Precedente
   esatto e recente: `ANNULLA riga manuale` sulle commesse (2026-07-28), *«non
   cancella, porta `stato_emissione` ad ANNULLATA con motivo obbligatorio
   tracciato»*;
4. **cancella la riga di `vendite.resi_righe_accrediti`** — l'unico pezzo senza
   precedente, ed è quello indispensabile: è quella riga a far scendere
   l'`accredito_dovuto` della coda (§20.3). Senza cancellarla, la coda resta
   muta per sempre e la merce non è più accreditabile da nessuno;
5. **motivo obbligatorio** e audit su `commesse_attivita_log`, come la madre
   gemella;
6. `SECURITY INVOKER` esplicito, `%TYPE` ovunque, `pg_advisory_xact_lock` a due
   argomenti dopo le guard — il modello resta `fn_aggiungi_onere_commessa`.

**Codici errore da registrare** (nomi indicativi, la classe è la parte che
conta):

| Codice | Classe | Quando |
| --- | --- | --- |
| `E_ACCREDITO_ANNULLO_NON_AMMESSO` | `CONFLITTO_STATO` | la rettifica è già emessa o agganciata a un lotto vivo |
| `E_ACCREDITO_NON_TROVATO` | `NON_TROVATO` | non esiste un accredito per quella riga di reso |

⚠️ **E c'è una cosa da dire agli operatori, non al codice**: dopo un reset di
lotto la nota di credito **ricompare** al giro successivo. Chi resetta
aspettandosi di aver cancellato l'accredito la ritrova il giorno dopo. Le due
strade sono distinte e devono restare distinte — il frontend lo dirà nel
messaggio, ma la ragione nasce qui.

---

## 🔴 P-6 — Nessun registro è intestato a un emittente, e gli emittenti sono due

> **Origine**: rilievo di Tid il 2026-08-18 — *«il numeratore non è collegato
> all'emittente? mi sembra veramente strano»*. Misurato subito. Il sospetto è
> fondato, e **il difetto non è della nota di credito**.

### La misura, presa il 2026-08-18

```text
vendite.registri_fatturazione
  3  Front-office   emittente_soggetto_ruolo_id = NULL   serie_default R2
  4  Back-office    emittente_soggetto_ruolo_id = NULL   serie_default R1
  5  NC             emittente_soggetto_ruolo_id = NULL   serie_default (vuota)

anagrafiche.emittenti_fiscali attivi  →  2      (letti come zeroerp_app;
                                                 la tabella non ha RLS)
```

✅ **E i due emittenti emettono ENTRAMBI documenti verso i clienti** (Tid,
2026-08-18).

🔴 **Ne discende che due aziende condividono lo stesso progressivo di
numerazione** — e non da oggi: vale sui registri **3 e 4**, cioè sulle
**fatture**, da gennaio. La doc concettuale di `registri_fatturazione` dichiara
il contrario da sempre: *«in presenza di più aziende abilitate, la separazione
dei registri evita collisioni di numerazione»*.

### ⭐ La macchina è già pronta — è la configurazione che non la usa

**N2b l'ha appena sistemata**, ed è la stessa slice di questa nota di credito.
`fn_build_fattura_key` passa oggi emittente e utility a `fn_get_registro_id`,
che ha il fallback a quattro livelli e sceglie il registro **più specifico**
disponibile. Prima di `20260818-32` quei registri erano **irraggiungibili**: è
il difetto del §12.4-bis.4, corretto.

E la forma è già prevista: `vendite.tipi_doc_fiscale_registri` ammette **più
registri** per la stessa coppia `(tipo_doc, natura)` — la `UNIQUE` è a tre
colonne — e `fn_get_registro_id` sceglie fra loro proprio con l'emittente.

Oggi il mapping manda entrambi i canali sullo stesso registro:

```text
(tipo_doc 1 FRONTOFFICE, natura FATTURA)      → 3
(tipo_doc 2 BACKOFFICE,  natura FATTURA)      → 4
(tipo_doc 1 FRONTOFFICE, natura NOTA_CREDITO) → 5
(tipo_doc 2 BACKOFFICE,  natura NOTA_CREDITO) → 5
```

### ✅ Come si sana, secondo la decisione di Tid

> *«Non serve un backfill: faremo in modo che l'attuale numeratore venga
> associato all'emittente unico in uso su ambiente di test»* — e, subito dopo:
> *«abbiamo solo ambiente di test, facciamo come vogliamo»*.

Quindi: si **intestano i tre registri esistenti** all'emittente che li ha usati
e si creano quelli del secondo. Nessuna continuità di numerazione da conservare,
nessun dato da spostare — è la regola generale del progetto (*non in produzione:
breaking change ammessi, niente fasi di compatibilità*).

⚠️ **Un solo vincolo, ed è di sequenza dentro l'apply.** Nel momento in cui il
registro 3 diventa intestato, il **livello 4** del fallback di
`fn_get_registro_id` — *«utility NULL **e** emittente NULL»* — non esiste più
per quel tipo documento, e un documento del secondo emittente risponde
`E_CONFIG_MANCANTE`. È il comportamento **giusto** (meglio fermarsi che numerare
sul registro dell'altra azienda), ma intestare i vecchi e creare i nuovi devono
stare **nello stesso changeSet**, mai in due.

⚠️ **Una verifica che io non ho potuto fare, e che va fatta prima di scrivere**:
quante fatture numerate esistono, e su quale emittente. `vendite.fatture` ha la
RLS: leggendo come applicazione senza GUC operatore il conteggio esce **0**, che
è un **fail-closed e non un dato** — la trappola descritta in
`feedback_rls_query_contesto_sistema`. Va letto in contesto di sistema, e serve
a sapere **a quale dei due** intestare i registri esistenti.

### Perché arriva da questo cantiere, e cosa NON è

* **Non è un prerequisito di BE/FE**: nessuna slice del piano lo aspetta;
* **è un difetto fiscale in esercizio**, e la nota di credito è solo il punto da
  cui si vede — perché è il primo documento che pone la domanda «su quale
  registro numero?» in modo non banale (§12.4-bis, che lo aveva previsto);
* ⭐ **sul registro NC costa niente farlo subito**: zero documenti emessi.
  Sui registri 3 e 4 è una riconfigurazione vera, e resta materia di chi tiene i
  registri IVA;
* 📌 è la richiesta **EM-1** del §17.4 del brief principale, e questa misura la
  rende concreta invece che latente. ⚠️ **Aggiornato il 2026-08-18**: il
  cantiere **perimetro emittente è chiuso**
  ([brief-db-perimetro-emittente-liste-e-gerarchia-ba.md](../work-done/brief-db-perimetro-emittente-liste-e-gerarchia-ba.md)),
  quindi EM-1 non «va portato» da nessuna parte — **resta in carico qui**,
  dentro **P-6**, che è il cantiere dei registri per emittente.

---

## 7. Analisi critica del team DB — 2026-08-18

> Sei richieste lette **contro il codice vivo**, non contro sé stesse. Quattro
> reggono, due vanno corrette prima di scrivere una riga, e una domanda aperta
> ha risposta.

| # | Esito | In una riga |
| --- | --- | --- |
| **P-1** | 🟢 **regge, verificato** | id 31 libero, `area_id = 2` giusto, `pericolosa = t` coerente con i precedenti |
| **P-2** | 🟠 **la conclusione regge, il ragionamento è scaduto** | e la domanda aperta ha risposta: **no** — ma per un motivo diverso da quello scritto, e una delle tre porte è chiusa per deduzione |
| **P-3** | 🟢 **regge**, con un legame che il brief non nomina | il gate si auto-ripara **solo perché** P-5 cancella invece di marcare |
| **P-4** | 🟢 nessun lavoro | confermato |
| **P-5** | 🔴 **la firma tratta un insieme come un singolo** | un accredito NON è una riga: è N righe di ponte e N rettifiche |
| **P-6** | 🟠 **il difetto è reale ma non è quello nominato**, e ha un prerequisito | non «collisioni» — **buchi nella serie**, che è peggio; e dipende dal residuo §11.11 del cantiere emittente |

---

### C-1 🟠 P-2 — la domanda aperta ha risposta: **no**. Ma il ragionamento del brief è scaduto di due settimane

**La domanda era**: *«esiste un percorso di reset che possa raggiungere un
documento numerato?»* — perché se sì, `fn_cleanup_fatture_by_ids` deve
cancellare anche la coppia in `vendite.fatture_rettifiche`.

**Risposta: no.** Ma l'argomento del brief — *«tutti e tre sono `*_da_draft`»* —
**non è più vero**. Il 2026-08-04 (RD-7) `fn_elimina_fattura_da_lotto_draft` è
stata **rinominata** `fn_elimina_fattura_da_lotto` e il suo perimetro
**allargato**: il lotto non deve più essere in bozza, basta che sia
*pre-fiscale*. Un argomento fondato sui **nomi** era destinato a scadere, e ha
scaduto.

⭐ **La garanzia vera è altrove, ed è più forte**: due delle tre porte hanno un
cancello **esplicito sul numero**, scritto apposta ridondante rispetto allo
stato.

| Porta | Cancello |
| --- | --- |
| `fn_elimina_fattura_da_lotto` | MOTIVO 4 di `fn_check_fattura_eliminabile_da_lotto`: `E_FATTURA_GIA_NUMERATA` — *«guarda il numero e non lo stato, perché il danno sarebbe irreversibile»* |
| `fn_riporta_lotto_a_draft` | `E_LOTTO_FATTURE_NUMERATE` — *«il controllo guarda il numero e non lo stato»* |
| `fn_annulla_lotto_da_draft` | 🔴 **nessuno.** Stato `DRAFT` del lotto + `fn_check_lotto_fatture_pre_fiscali`, che è **solo sugli stati** |

E siccome `popola_fatture_rettifiche` gira **dopo** `numera_fatture`, la
proiezione esiste solo su documenti numerati: nessuna delle tre la incontra.
**`fn_cleanup_fatture_by_ids` non va toccata.**

#### ⚠️ Ma la terza porta è chiusa per DEDUZIONE, e da domani è portante

`fn_check_lotto_fatture_pre_fiscali` dichiara nel proprio commento che
pre-fiscale *«cioè non ancora numerate»*: **equipara** lo stato al numero. È
esattamente l'equivalenza che le altre due porte si rifiutano di dare per buona
— e non per scrupolo estetico: la ridondanza del MOTIVO 4 è motivata per
iscritto con *«il danno sarebbe irreversibile»*.

Finché non esiste `fatture_rettifiche`, quella deduzione costa poco. Dal momento
in cui esiste, diventa portante su una **FK non `ON DELETE CASCADE`**: il modo in
cui cede non è un errore di dominio, è una violazione di chiave esterna grezza
**dentro una funzione che i suoi tre chiamanti danno per infallibile**.

> ⭐ **Proposta**: aggiungere il motivo esplicito sul numero a
> `script.fn_check_lotto_annullabile`, simmetrico alla sorella. Costa una
> `IF`, e trasforma «probabilmente irraggiungibile» in «dimostrabilmente».
>
> ⚠️ **Non** dentro il delegato condiviso `fn_check_lotto_fatture_pre_fiscali`:
> lo leggono anche le capability e l'altra sorella, e stringere lì cambierebbe
> il comportamento di consumatori che non stiamo esaminando. La sorella
> `fn_check_lotto_riportabile_a_draft` ha già il suo controllo **fuori** dal
> delegato: si copia quella forma.

#### 🟢 Il resto di P-2 è verificato

* `dbops.pipeline_task_registry` arriva a **id 20** → il nuovo è **21**;
  `dominio_id = 1` è quello di tutti i task di fatturazione;
* ⚠️ `pipeline_task_registry_impl` ha una colonna che la richiesta non nomina:
  **`is_default`**, da mettere a `true`. Senza, l'implementazione esiste e non
  viene scelta;
* `numera_fatture` e `stampa_documenti_lotto` sono **adiacenti** nel JSON delle
  righe 4 e 6: l'inserimento in mezzo è meccanico.

---

### C-2 🔴 P-5 — un accredito NON è una riga. La firma proposta tratta un insieme come un singolo

È il rilievo che cambia il lavoro, e viene dalla madre stessa.

`fn_accredita_riga_reso` **non inserisce una riga di ponte**: ne inserisce
**N**. Due ragioni indipendenti, entrambe nel suo commento:

* **consumo LIFO** delle unità fatturanti (D-NC-5): una quota resa può coprire
  più righe di fattura, e ognuna produce la sua coppia;
* **kit**: *«una rettifica per componente, ciascuna specchio della sua riga di
  fattura»*.

Lo conferma il vincolo: `uq_resi_accrediti_pair (resi_riga_id,
fattura_riga_rettificata_id)` — la chiave è **la coppia**, non la riga di reso.
Il plurale è per costruzione.

**Ne discende che le precondizioni 2 e 3 di P-5, così come sono scritte, non
sono applicabili**: parlano de *«la rettifica»* al singolare.

#### ⭐ La forma giusta: tutto-o-niente sull'INSIEME, e la ragione la scrive la madre

```text
NON:  «se la rettifica è NON_EMESSA, annullala»
MA:   «se TUTTE le rettifiche di quella riga di reso sono NON_EMESSA e non
       agganciate a un lotto vivo, annullale tutte e cancella tutte le coppie.
       Altrimenti non si annulla NIENTE.»
```

Non è prudenza generica. È **letteralmente** la dottrina con cui la madre chiude
il proprio giro (`E_ACCREDITO_QUOTA_NON_COPERTA`):

> *«meglio non farlo che farlo a metà, perché un residuo parziale è la riga che
> resta in coda a chiedere per sempre»*

Un annullo **parziale** produce esattamente quel residuo, allo specchio:
`accredito_dovuto` risalirebbe solo in parte, e la coda resterebbe a chiedere una
quota che nessuno può più soddisfare — perché l'altra metà è dentro un documento
fiscale.

#### ⚠️ E l'ordine delle due scritture non è indifferente

`fk_resi_accrediti_commessa_attivita` punta dal ponte alla rettifica. La riga di
ponte si cancella **prima** (o nello stesso statement) di toccare l'attività;
e il guard dei due tetti (`20260818-36`) va attraversato in discesa, il che è il
verso facile — le somme calano.

#### 🟢 Il resto di P-5 regge, e i precedenti citati sono quelli giusti

`stato_emissione = 'ANNULLATA'` invece della cancellazione, motivo obbligatorio,
audit su `commesse_attivita_log`, `SECURITY INVOKER`, `%TYPE`,
`pg_advisory_xact_lock` a due argomenti dopo le guard: tutto verificato contro
`fn_aggiungi_onere_commessa` e contro l'ANNULLA riga manuale del 2026-07-28.

---

### C-3 ⭐ P-3 e P-5 sono **accoppiati**, e il brief li tratta come indipendenti

Il gate della rinuncia (P-3) scatta *«appena esiste una riga in
`vendite.resi_righe_accrediti`»*. L'annullo (P-5) **cancella** quelle righe.

> ⭐ **Quindi il gate si auto-ripara: annullato l'accredito, la rinuncia torna
> reversibile — senza che P-3 sappia nulla di P-5.**

È un pregio del disegno, ma è **fragile a un cambio di P-5**: se l'annullo
scegliesse un *soft-delete* (una colonna `annullato_il`) invece della
cancellazione, il gate di P-3 continuerebbe a vedere la riga e vieterebbe per
sempre una rinuncia ormai reversibile — **in silenzio**, perché nessuno dei due
lati sarebbe sbagliato da solo.

**Conseguenza operativa**: P-3 va scritto **dopo** P-5, e la scelta «cancella,
non marcare» va messa nel commento di entrambe le funzioni come vincolo
reciproco, non come dettaglio implementativo.

---

### C-4 🟠 P-6 — il difetto è reale, ma non è «collisione». È **peggio**

Il brief cita la doc concettuale (*«la separazione dei registri evita collisioni
di numerazione»*) e conclude che le collisioni ci sono. **Non ci sono**, ed è
utile sapere perché:

```sql
uq_fatture_numero ON vendite.fatture (registro_id, anno, COALESCE(serie,''), numero)
                  WHERE numero IS NOT NULL
```

Il numero è unico **per registro**. Due emittenti sullo stesso registro non
ottengono mai lo stesso numero: ottengono numeri **alternati**.

| | Cosa succede | Chi lo blocca |
| --- | --- | --- |
| collisione (stesso numero due volte) | ❌ non accade | l'indice univoco |
| 🔴 **serie con buchi** (A prende 1,3,7 — B prende 2,4,5,6) | ✅ **accade adesso** | **nessuno** |

E il registro sezionale di ciascuna azienda deve essere **continuo**. Il difetto
non è una duplicazione che un vincolo intercetta: è una **discontinuità che
nessun vincolo può vedere**, perché per il database quei numeri sono
perfettamente legittimi.

⭐ Il che **rafforza** la richiesta invece di indebolirla — e sposta il punto:
non è un rischio che potrebbe manifestarsi, è uno stato in cui i registri 3 e 4
si trovano **da gennaio**.

---

### C-5 ✅ P-6 — la misura è stata fatta, ed è il caso buono

Il brief la dava per non eseguibile («`vendite.fatture` ha la RLS, lo zero è
fail-closed»). È vero leggendo come applicazione; letta come **proprietario** la
RLS non si applica, e la misura è questa:

```text
fatture NUMERATE, per registro x emittente          (2026-08-18, come owner)
  registro 3  Front-office   ef_sr 72  «Gestore Test pgTAP»
              6 fatture · anno 2026 · serie R2 · numeri 1 → 6   ← CONTINUI
  registro 4  Back-office    nessuna
  registro 5  NC             nessuna

emittenti fiscali attivi
  ef_sr  72   PGTAP-EF-...   «Gestore Test pgTAP»    41 BA mappati + is_default
  ef_sr 159   EMI-TEST       «Azienda SC REQUIRED»    1 BA mappato · 0 fatture
```

⭐ **È l'esito migliore possibile, e chiude due punti aperti in un colpo:**

| Punto | Esito |
| --- | --- |
| «e se un registro avesse due emittenti?» | **non succede**: un solo emittente per registro. L'intestazione è vera anche del passato |
| «la serie di 72 ha già dei buchi?» | **no**: 1→6 continui. Nessun danno da riparare, solo una porta da chiudere |
| «meglio fare prima la NC e poi i registri 3/4?» | **no, si fa tutto insieme**: 4 e 5 non hanno documenti, e intestare il 3 a 72 non cambia niente per nessuno |

🔵 Ne discende che P-6 **smette di essere «materia di chi tiene i registri IVA»**
e diventa una riconfigurazione di seed pulita. Il secondo emittente non ha mai
numerato: parte da 1 sui propri registri, che è corretto.

⚠️ Resta vero il motivo per cui va fatto: 159 **può** emettere (ha un billing
account mappato) e oggi lo farebbe sul registro di 72. Il difetto è preventivo,
non ancora avvenuto — ed è il momento giusto per chiuderlo, perché costa zero.

---

### C-6 ⭐ P-6 tocca il cantiere **perimetro emittente** in un punto preciso — ed è un **prerequisito**, non un rimando

Il brief chiude dicendo che P-6 «va portato anche al cantiere perimetro
emittente». È vero e c'è di più: **P-6 non è scrivibile in sicurezza finché il
residuo §11.11 non è chiuso.**

> ⚠️ **Aggiornato il 2026-08-18 — cambia il proprietario, non il vincolo.** Il
> cantiere perimetro emittente è **chiuso e archiviato**
> ([brief-db-perimetro-emittente-liste-e-gerarchia-ba.md](../work-done/brief-db-perimetro-emittente-liste-e-gerarchia-ba.md)),
> e nel farlo ha instradato proprio questo residuo al **cantiere numerazione
> (P-6)**, «di cui è prerequisito» — cioè **qui**. Non c'è più un altro
> cantiere che lo chiuderà: o lo fa P-6, o P-6 non parte.

La catena che decide su quale registro numera una fattura è questa:

```text
fn_build_fattura_key
  └─ anagrafiche.fn_get_emittente_fiscale_id(billing_account_id)   ← il residuo §11.11
       └─ vendite.fn_get_registro_id(tipo_doc, natura, utility, EMITTENTE)
            └─ il registro
```

Quella funzione è la **terza copia** della regola a due livelli (mapping
specifico → ripiego sul gestore globale). Le altre due sono state unificate il
2026-08-18 nella Fase E del cantiere emittente:
`script.fn_get_ba_emittente_sr_id` e `fn_check_ba_visible_for_emittenti`, che
ora delega. Le tre rispondono **alla stessa domanda**, e due lo fanno da un
posto solo.

> ⚠️ **Oggi la duplicazione non morde**, e proprio per questo non si è vista:
> tutti i registri hanno `emittente_soggetto_ruolo_id = NULL`, quindi il
> **livello 4** del fallback vince sempre e il parametro emittente **non sceglie
> niente**. È un ramo che esiste e non viene mai percorso.
>
> 🔴 **P-6 lo rende portante per la prima volta.** Dal momento in cui i registri
> sono intestati, *su quale registro numera una fattura* dipende da quella copia
> non unificata.

E c'è un dettaglio che rende la cosa concreta e non teorica — sta scritto nel
commento della funzione stessa:

> *«Non filtra per attivo.»*

Un emittente **disattivato** può quindi essere scelto come intestatario del
registro su cui numerare. Finché il parametro non decideva niente, era
innocuo.

⭐ **Due note di merito**, per non aggiungere lavoro dove non serve:

* la funzione, malgrado il nome, restituisce già un `soggetto_ruolo_id` — non la
  PK di `emittenti_fiscali` — quindi **non c'è nessun disallineamento di tipo**
  con `fn_get_registro_id`. Il sospetto era legittimo e la verifica lo esclude;
* `vendite.tipi_doc_fiscale_registri` ammette davvero **più registri** per la
  stessa coppia `(tipo_doc, natura)`: la `UNIQUE` è a tre colonne. La forma
  prevista dal brief regge.

---

### C-7 🟢 Il vincolo di sequenza di P-6 è corretto, e vale la pena capire perché

Il brief avverte che intestare i vecchi registri e creare i nuovi devono stare
**nello stesso changeSet**. Verificato sul `WHERE` di `fn_get_registro_id`:

```sql
AND (r.emittente_soggetto_ruolo_id IS NULL
     OR r.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id)
```

Nel momento in cui il registro 3 smette di avere `NULL`, per un documento del
**secondo** emittente non resta **nessuna riga**: né il livello 4 (non c'è più)
né il livello 3 (il registro è dell'altro). La funzione risponde
`E_CONFIG_MANCANTE` e la numerazione si ferma.

⭐ **Ed è il comportamento giusto**: meglio fermarsi che numerare sul registro
dell'altra azienda. Ma è anche il motivo per cui i due passi non si separano —
in mezzo c'è una finestra in cui un emittente non può fatturare.

---

## 8. Piano di sviluppo — perimetro DB

> Ordinato per **dipendenza**, non per numero di richiesta. I passi 1 e 2 sono
> meccanici e sbloccano il BE subito; il 3 e il 4 sono accoppiati; il 5 è il
> difetto fiscale e ha un prerequisito fuori da questo brief.
>
> ⛔ **Nessuna migrazione viene applicata dal team DB**: l'apply lo autorizza Tid
> per quel comando.

### Passo 1 — P-1 · l'azione di processo *(sblocca B2, F1)*

| | |
| --- | --- |
| **Cosa** | 1 riga in `80_data/sql/config/azioni_processo.csv` |
| **Valori** | `id = 31`, `area_id = 2`, `permission_codename = accredita_riga_reso`, `pericolosa = t`, `attivo = t` |
| **Verificato** | 30 è l'ultimo id in uso; `pericolosa = t` è coerente con `numera_fatture_lotti` e `cambia_stato_commessa` |
| **Rischio** | nessuno |

Solo append al CSV: il loader `runOnChange` esistente ripesca il file.

### Passo 2 — P-2 · il task a registry e in pipeline *(sblocca B6)*

**2a** — `80_data/sql/dbops/pipeline_task_registry.csv`: `id = 21`,
`dominio_id = 1`, `task_code = popola_fatture_rettifiche`.

**2b** — `pipeline_task_registry_impl.csv`: `id = 21`, `task_registry_id = 21`,
`implementation_key = default`, `handler_code = popola_fatture_rettifiche_default`,
⚠️ **`is_default = true`** (la colonna che la richiesta non nominava).

**2c** — `80_data/sql/vendite/fatturazione_pipeline.csv`, righe **4** e **6**:
il task nel JSON `processi`, fra `numera_fatture` e `stampa_documenti_lotto`
(sono già adiacenti).

**2d** — ⭐ **la simmetria mancante** (C-1): aggiungere a
`script.fn_check_lotto_annullabile` il motivo esplicito *«fattura già
numerata»*, sul modello di `fn_check_lotto_riportabile_a_draft` — **fuori** dal
delegato condiviso.

> ⚠️ Prima di scriverlo: `grep` nei pgTAP dei consumatori. Un guard che stringe
> rompe i test che si aspettavano il vecchio confine, e vanno letti prima —
> non «aggiustati» dopo.

**Non si fa**: nessuna modifica a `fn_cleanup_fatture_by_ids`. La risposta alla
domanda del brief è **no**, e la ragione va scritta nel commento della funzione
perché la prossima persona non debba rifare l'indagine.

### Passo 3 — P-5 · l'annullo dell'accredito *(sblocca B2-bis, F1)* — ✅ **APPLICATO E VERDE** (2026-08-18)

> 🟢 Changeset `20260818-71` + 4 codici a catalogo + 17 pgTAP, **verdi**. La
> cronaca, con i **sei scostamenti dal piano**, è in **§9**. Questo testo resta
> com'era scritto: dove il piano e §9 divergono, vale §9.
> 🔴 Resta aperto il difetto di **§10**.

**La firma resta** `vendite.fn_annulla_accredito_riga_reso(p_resi_riga_id, p_motivo)`,
ma la **semantica è d'insieme** (C-2).

1. guard sul parametro — `NULL`/`<= 0` → errore parlante;
2. raccogliere **tutte** le coppie di `resi_righe_accrediti` per quella riga di
   reso. Nessuna → `E_ACCREDITO_NON_TROVATO` (classe `NON_TROVATO`);
3. ⛔ **cancello tutto-o-niente**: se **una sola** delle rettifiche è emessa,
   fatturata o agganciata a un lotto vivo → `E_ACCREDITO_ANNULLO_NON_AMMESSO`
   (classe `CONFLITTO_STATO`), e **non si tocca niente**;
4. `pg_advisory_xact_lock` a due argomenti **dopo** le guard;
5. cancellare le righe di ponte, **poi** portare le rettifiche a
   `stato_emissione = 'ANNULLATA'` (l'ordine è imposto da
   `fk_resi_accrediti_commessa_attivita`);
6. motivo obbligatorio + audit su `commesse_attivita_log`, come la madre.

**Codici errore**: 2 nuovi a catalogo, con classe registrata — solo append al
CSV, nessun loader nuovo.

**Test pgTAP** — ⭐ l'asserzione che conta non è «la riga è sparita», è **la
coda**:

* `accredito_dovuto` **risale** al valore di prima e `gia_accreditato` torna
  falso — è l'unica prova osservabile che l'annullo ha funzionato;
* un secondo accredito sulla stessa riga **riesce** (la madre non solleva più
  `E_ACCREDITO_GIA_ESEGUITO`);
* ⭐ **il caso plurale**: una riga di reso che ha prodotto **due** rettifiche, di
  cui una emessa → l'annullo rifiuta **entrambe**. Senza questo test la
  semantica d'insieme non è verificata, e una fixture a una sola rettifica
  passerebbe anche con la versione sbagliata.

### Passo 4 — P-3 · il gate della rinuncia · **dopo il passo 3**

Un ramo dentro `script.fn_check_rinuncia_reversibile`, nella forma che la
funzione già usa (`{codice, reason, reason_key, dettaglio}`): *esiste una riga in
`resi_righe_accrediti` per questa riga di reso*.

* 1 codice errore nuovo a catalogo — il commento della funzione dice
  esplicitamente di non averlo registrato prima *«per non lasciare a catalogo un
  codice mai sollevato»*. Ora si solleva;
* 1 chiave i18n per il `reason_key`, sul modello di
  `vendite.resi.rinuncia_reason.riga_inesistente`;
* ⭐ **la madre non si tocca**: `fn_riapri_riconsegna_reso` solleva già il primo
  motivo prodotto;
* ⚠️ scrivere nel commento di **entrambe** le funzioni il vincolo reciproco di
  C-3: *il gate si auto-ripara perché l'annullo CANCELLA. Se un giorno l'annullo
  diventasse un soft-delete, questo ramo va cambiato insieme.*

**Test**: accredito → rinuncia non riapribile; annullo → **riapribile di nuovo**.
Il secondo verso è quello che verifica l'accoppiamento.

### Passo 5 — P-6 · i registri per emittente · *difetto fiscale, non prerequisito BE/FE*

> ✅ **5a è FATTO** (C-5): un solo emittente per registro, serie di 72 continua
> 1→6, registri 4 e 5 vuoti, emittente 159 mai numerato. Nessun backfill,
> nessuna discontinuità da riparare — solo una porta da chiudere prima che serva.

#### ✅ Due decisioni di Tid — 2026-08-18

**D-P6-1 · Emittente disattivato → il cancello va sulla DISATTIVAZIONE, non sulla
numerazione.**

Trigger `dbops.trgfn_prevent_deactivate_if_children` su
`anagrafiche.emittenti_fiscali_billing_account`, esattamente come già esiste per
utilities, contratti, DDT, ordini, resi, preventivi e altri otto.

> ⭐ **Perché lì e non dentro `fn_get_emittente_fiscale_id`**: il problema si
> ferma **dove nasce** — chi disattiva — invece che dove si manifesta, cioè
> davanti a un operatore che sta fatturando e non capisce perché non può. E il
> percorso caldo della numerazione non si tocca.
>
> ⚠️ **Verificato che oggi manca**: zero trigger di questa famiglia su
> `emittenti_fiscali_billing_account`, mentre ce ne sono su tutte le altre
> tabelle figlie. Non è una scelta passata — è una riga saltata.
>
> ⛔ **Scartata la difesa in profondità** (guard + filtro nella funzione): il
> secondo strato non si esercita mai se il primo tiene, e un ramo mai percorso
> sembra coperto senza esserlo.

**D-P6-2 · I registri del secondo emittente riusano le stesse serie per canale:
`R2` front-office, `R1` back-office, vuota per NC.**

> La serie continua a significare **canale**. L'azienda si legge dalla P.IVA sul
> documento e dalla colonna emittente che il cantiere perimetro sta portando
> nelle liste: caricare la serie anche di quell'informazione la duplicherebbe.
>
> ⚠️ Tecnicamente non c'è nessun vincolo da rispettare: `uq_fatture_numero` è su
> `(registro_id, anno, serie, numero)`, quindi due registri diversi possono
> avere la stessa serie senza collidere.

**D-P6-3 · La numerazione attuale si intesta all'emittente «Gestore Test pgTAP»
(`soggetto_ruolo_id = 72`).**

> È l'emittente che le 6 fatture numerate portano già in `vendite.fatture`
> (C-5): l'intestazione non riscrive la storia, la **dichiara**. Registri 4 e 5
> vanno allo stesso, non avendo documenti e appartenendo allo stesso assetto —
> 72 è anche il gestore globale (`is_default`) che copre i 41 billing account
> non mappati esplicitamente.

#### 5b — ⛔ il prerequisito: unificare la terza copia *(§11.11, ereditato dal cantiere perimetro emittente ora chiuso)*

Far delegare `anagrafiche.fn_get_emittente_fiscale_id` a
`script.fn_get_ba_emittente_sr_id`, mantenendo il raise
`E_EMITTENTE_DEFAULT_MISSING` dove oggi c'è (la delegata risponde `NULL`, la
chiamante decide se sollevare).

> 🔴 **Perché è un prerequisito e non igiene**: da 5c in poi è quella funzione a
> decidere su quale registro numera una fattura (C-6). Andarci sopra dopo
> significa cambiare il selettore mentre è in uso.
>
> 🟢 `attivo` **non si tocca qui**: la decisione D-P6-1 mette il cancello altrove.

#### 5c — il guard sulla disattivazione *(D-P6-1)*

Una riga di seed nell'automazione `prevent_deactivate_if_children`:
tabella figlia `anagrafiche.emittenti_fiscali_billing_account`, colonna di
collegamento `emittente_soggetto_ruolo_id` → `soggetto_ruolo_id`, flag `attivo`.

⚠️ Da mettere **prima** di 5d: dopo l'intestazione dei registri la
disattivazione di un emittente diventa una porta aperta su un percorso fiscale,
e il guard deve esserci già.

#### 5d — l'intestazione + i registri nuovi: UN SOLO changeSet (C-7)

Nello stesso file, in quest'ordine:

| | Cosa | Valori |
| --- | --- | --- |
| 1 | `UPDATE` registri **3, 4, 5** | `emittente_soggetto_ruolo_id = 72` |
| 2 | `INSERT` tre registri nuovi | ef **159** — Front-office (`serie_default = R2`), Back-office (`R1`), NC (vuota) |
| 3 | `INSERT` in `tipi_doc_fiscale_registri` | le coppie `(tipo_doc, natura)` → i tre registri nuovi |

⚠️ `registri_fatturazione.codice` è **UNIQUE**: i codici nuovi vanno distinti
(es. `Front-office EMI-TEST`), mentre le **serie** si ripetono — e va bene
(D-P6-2).

⛔ **Mai in due changeSet**: fra il passo 1 e il 3 esiste una finestra in cui
l'emittente 159 non può numerare (`E_CONFIG_MANCANTE`, C-7).

🟢 **Nessun rischio sui documenti esistenti**: le 6 fatture di 72 restano sul
registro 3, che diventa suo. La serie 1→6 continua senza salti.

#### 5e — test pgTAP

* ogni registro attivo ha un `emittente_soggetto_ruolo_id` valorizzato — è il
  presidio che impedisce di tornare indietro;
* per **ciascuno** dei due emittenti, `fn_get_registro_id` risolve un registro
  **diverso** su ogni coppia `(tipo_doc, natura)` in uso;
* ⭐ nessun registro è raggiungibile da due emittenti — l'asserzione che dice che
  i buchi nella serie (C-4) non possono ripresentarsi;
* ⭐ **il guard di D-P6-1 morde**: disattivare un emittente con billing account
  mappati fallisce. Da esercitare su un emittente di prova, non su 72 o 159.

### Cosa NON è nel piano, e perché

* **P-4**: confermato, zero lavoro;
* la **cancellazione di `fatture_rettifiche`** dentro `fn_cleanup_fatture_by_ids`:
  la domanda ha risposta **no** (C-1). Si scrive solo il commento;
* il **backfill** della numerazione: deciso da Tid, non si fa;
* tutto ciò che è già in *«Cosa NON è di questo brief»* qui sotto.

---

## ✅ P-7 — La rettifica di un COMPONENTE di kit non attraversa il generatore — CHIUSO

> **Origine**: smoke end-to-end del lato applicativo (B8), eseguito il
> 2026-08-18 sera — `backend/scripts/tests/smoke-nota-credito-resi.py`. È il
> caso che il brief principale indicava di provare *«sui DATI, sulla riga 24
> della coda»*. Il giro completo è **verde su una riga semplice** e **rosso sul
> kit**, e si ferma prima del documento.

### Il fatto, misurato

```text
riga di coda 24 (articolo composito) → il verbo crea 3 rettifiche, una per componente
  segment_key: DDT:<uid>:R:126#RET:1#CMP:<uuid componente>
  meta:        {"coeff_qta": 1.0, "accredito_da": "RESO",
                "resi_riga_id": 24, "tipo_consumo": "CONGUAGLIO"}

FattureRigheService.generate_fatture_righe
  → E_ATTIVITA_KIT_SENZA_PADRE
    «componente_di assente nel meta dell'attivita»
```

### Perché succede, e perché il rifiuto è **giusto**

Il contratto dello snapshot kit è dichiarato in
`backend/apps/vendite/services/_kit_meta.py` e ha **quattro** chiavi, scritte
dal push (`BoMComponentExpander`) e lette dal generatore:

| chiave `meta` | la scrive il push | la copia `fn_accredita_riga_reso` |
| --- | --- | --- |
| `coeff_qta` | ✅ | ✅ |
| `componente_di` | ✅ | ❌ |
| `esposto_in_fattura` | ✅ | ❌ |
| `segment_key` | ✅ | (la aggiunge il pull, presente) |

Il generatore decide di essere su un componente **dal segment_key** (`#CMP:`) e
poi pretende `componente_di`. Il suo fail-loud è deliberato e va tenuto: senza,
la riga verrebbe trattata come normale e **fatturata due volte** — una dentro il
totale del padre e una per conto suo (R11).

⭐ **Il difetto non è nel generatore: è una copia a metà.** La madre copia
`coeff_qta` dal componente e si ferma, quindi produce un segmento che **dichiara
di essere un componente** senza dire di chi. Qualunque altro consumatore di quel
`meta` sbatterebbe sullo stesso muro.

### La richiesta

Che `vendite.fn_accredita_riga_reso`, quando la partita è un componente di kit,
copi dal `meta` dell'attività rettificata anche **`componente_di`** e
**`esposto_in_fattura`**, accanto al `coeff_qta` che copia già. Nessuna
risoluzione di distinta base: sono valori da **copiare**, come il prezzo (N-1) —
solo il documento sorgente sa quale kit è stato venduto.

### Le due strade valutate, e perché questa

| Strada | Perché no / sì |
| --- | --- |
| **A · la madre completa il `meta`** *(proposta)* | ✅ Il `meta` della rettifica torna coerente con il proprio `segment_key`; il generatore resta con un solo ramo; vale per ogni consumatore futuro |
| **B · il generatore, per le rettifiche, copia le 4 colonne `kit_*` dalla riga di fattura rettificata** | Difendibile — è la stessa dottrina del prezzo — ma introduce nel generatore un **secondo ramo** per un caso particolare, e lascia nel database un segmento di componente orfano del suo padre. Il difetto si sposta, non si chiude |

⚠️ **Fino ad allora il perimetro dell'accredito è di fatto limitato agli
articoli semplici**: sul kit il verbo riesce, la rettifica nasce, e il documento
non si genera — cioè la riga esce dalla coda e la nota di credito non arriva.
È lo stato peggiore fra i tre, e vale la pena dirlo: **non** è «non funziona
ancora», è «la coda dice fatto e il documento non c'è».

### ✅ Esito — `20260818-75`, applicato e verde (team DB, 2026-08-18 sera)

**Verificato dal lato BE lo stesso giorno**: lo smoke `smoke-nota-credito-resi.py`
passa da 14/15 a **15/15**, kit compreso — stesso comando, stessi dati, **nessuna
modifica al backend**.

⭐ **La soluzione scelta è migliore di quella che avevo chiesto, e la ragione va
tenuta.** Avevo chiesto di copiare **due chiavi** (`componente_di`,
`esposto_in_fattura`); il team DB ha fatto **ereditare il `meta` intero** della
riga rettificata (`ca.meta || {coeff_qta, accredito_da, resi_riga_id}`). Parola
loro:

> *«enumerarle avrebbe messo quei letterali in un terzo posto, in SQL, dove
> `_kit_meta.py` non si può importare — cioè esattamente il difetto contro cui
> quel file è nato. Se domani aggiungete un quinto tasto al contratto, viaggia
> da solo.»*

Hanno ragione, e la mia richiesta portava dentro proprio il difetto che il §28
del brief principale descriveva: **un contratto a quattro chiavi trattato una
chiave alla volta**. ⚠️ Le due chiavi che potrebbero mentire sono coperte perché
stanno a **destra** del `||`: `tipo_consumo` lo riscrive
`fn_upsert_commessa_attivita`, `segment_key` lo riscrive
`fn_emit_attivita_fatturabili_da_commessa`.

**E un codice in più che non avevo chiesto**: `E_ACCREDITO_KIT_SENZA_PADRE`
(928, `NON_ESEGUIBILE`). L'ereditarietà ripara i kit **corretti**; un kit che
nasce senza `componente_di` restava nella forma peggiore (verbo ok, riga fuori
dalla coda, niente documento). Ora la madre lo rifiuta **al clic**. È il gemello
di `E_ACCREDITO_KIT_NON_MISURABILE`: *la madre controllava un tasto su quattro
del contratto, ora li tratta come contratto.*

### ✅ BE-7 — verificato, ed è **verifica, non lavoro**

La richiesta era: *«serve che il push garantisca `componente_di` su ogni
componente»*. Misurato contro il codice:

* l'**unico** produttore di un segmento `#CMP:` in tutto `backend/apps/` è
  `BoMComponentExpander._build_componente_pushable_row`, che scrive **tutte e
  tre** le chiavi del contratto senza condizioni;
* il padre non può essere nullo su quel percorso: `expand()` esce prima
  (`if row.articolo_id is None: return [row]`) — quindi il `str(None)` che
  scriverebbe la stringa `"None"` (truthy, e perciò invisibile a **entrambi** i
  guard) **non è raggiungibile**;
* ed è **presidiato da test**, non solo vero oggi:
  `test_caso_a_meta_arricchito_componente_di_e_esposto` asserisce
  `meta["componente_di"] == str(row.articolo_id)`, e la R11 del generatore ha il
  suo test in `test_fatture_righe_service.py`.

🔵 Nessuna riga di backend da scrivere. Il guard 928 resta il presidio giusto per
i dati **già** nati storti, che nessun fix del push può raggiungere.

### 📌 Per F1 (frontend), preso in carico

Nota operativa accolta: se una riga di kit non è accreditabile, **il bottone va
spento in lista** invece di far cliccare per ricevere un errore che l'operatore
non può risolvere da solo — il rimedio è sul documento di origine. Registrato
nel piano FE del brief principale.

### ✅ Dizionario codici — fatto, con una deroga dichiarata

`error_policies_generated.py` **rigenerato** per il codice 928, con il messaggio
di ripiego senza `%s`: la suite è verde anche con `ZEROERP_TEST_DB_E2E=1`.

⚠️ **Deroga autorizzata da Tid**, e va detta perché ha un effetto sul vostro
lato: si è rigenerato pur essendo il DB **avanti rispetto a git** (716 contro
715), cioè con `20260818-75` non ancora pushato. Finché quel commit non atterra,
la CI — che ricostruisce il database dal changelog — **non trova il 928** e il
cancello del terzo lato diventa rosso *al contrario*: un codice dichiarato nel
modulo BE che a catalogo non esiste.

📌 **Si chiude da sé con il vostro push**, e non serve che facciate nulla di
diverso: è la stessa divergenza di prima, vista dall'altra parte.

---

## Cosa NON è di questo brief

* la **rigenerazione di `error_policies_generated.py`** per gli 8 codici già
  seedati: è lavoro backend (BE-6), lo fa il ramo BE;
* il **task Python** `_handle_popola_fatture_rettifiche_task`: backend. Qui
  serve solo la riga a registro che lo rende raggiungibile (P-2);
* il **generatore righe** che non aggrega le rettifiche e copia prezzo, sconto e
  IVA dalla riga rettificata (BE-4/BE-5): interamente Python;
* il **processo rimborsi** per una NC fuori dalla banda del minimo: è la
  richiesta **PG-1** del §17.3, e va al cantiere incassi, non qui.

---

## 9. Cronaca dell'esecuzione — passo 3 (P-5), 2026-08-18

> ✅ **Applicato da Tid il 2026-08-18** e verificato: `20260818-71`, le 4 righe
> di catalogo (i messaggi 924-927 rispondono) e i 17 pgTAP **verdi**
> (`Files=1, Tests=17, Result: PASS`).

### Cosa è stato scritto

| Artefatto | Contenuto |
| --- | --- |
| `80_data/sql/config/codici_errore.csv` | +4 codici (append, nessun loader nuovo) |
| `80_data/sql/config/messaggi_errore.csv` | +4 messaggi, id **924-927** |
| `20_code/vendite/20260818-71-create-fn-annulla-accredito-riga-reso-mctit.yaml` | la madre `vendite.fn_annulla_accredito_riga_reso(resi_riga_id, motivo)` |

### I sei scostamenti dal piano, e perché

**D-9-1 · Il lock: `FOR UPDATE` su `resi_righe`, non l'advisory lock.**
Il piano (punto 4) diceva *«`pg_advisory_xact_lock` a due argomenti dopo le
guard»*, per analogia con `fn_aggiungi_onere_commessa`. Decisione di Tid:
l'appiglio giusto è quello del **guard del ponte**. La verifica conferma, con
una precisazione sul meccanismo che vale la pena fissare:

* `trgfn_resi_accrediti_guard` prende `FOR UPDATE` su `vendite.resi_righe`
  e lo dichiara — *«nessun advisory lock, il FOR UPDATE basta, come nelle due
  sorelle»*;
* ⚠️ la **madre non prende quel lock direttamente**. Il suo
  `pg_advisory_xact_lock` sta sulla **riga di DDT** e serve a un'altra cosa: far
  girare il progressivo `#RET` sul segmento. Sulla riga di reso ci arriva **di
  riflesso**, attraversando il proprio guard alla prima `INSERT` sul ponte.

⭐ Il risultato è quello voluto — chiunque scriva sul ponte passa da lì, quindi
l'esclusione **interseca davvero**. L'advisory intersecherebbe anch'esso, ma
sarebbe l'appiglio sbagliato: più grosso del necessario (più righe di reso
condividono una riga di DDT) e cieco verso il percorso che conta.
⛔ Nessun deadlock: la madre prende advisory→riga, l'annullo solo riga e non
attende mai l'advisory. Manca il secondo verso, quindi manca il ciclo.

**D-9-2 · 🔴 Quattro codici, non due — e il quarto è il vero ritrovamento.**
Il piano ne prevedeva 2 (`E_ACCREDITO_NON_TROVATO`,
`E_ACCREDITO_ANNULLO_NON_AMMESSO`). Il terzo è meccanico
(`E_ACCREDITO_MOTIVO_OBBLIGATORIO`: il piano chiede il motivo obbligatorio ma
non registra il codice; distinto da `E_RIGA_COMMESSA_MOTIVO_OBBLIGATORIO`
perché il messaggio deve nominare l'accredito, non la riga di commessa).

Il **quarto** no, e nessuno l'aveva nominato:

```text
vendite.commesse_attivita     -> HA la RLS   (rls_commesse_attivita_ef_whitelist)
vendite.resi_righe_accrediti  -> NON ce l'ha
```

Il ponte dice sempre la verità su **quante** rettifiche esistono; la `UPDATE` ad
`ANNULLATA` gira sotto RLS e una rettifica fuori perimetro emittente la
salterebbe **in silenzio**. È esattamente l'annullo parziale che la semantica
d'insieme di C-2 vieta, nella forma più difficile da vedere. ⚠️ E il cantiere
perimetro emittente, **chiuso il 2026-08-18**, non toglie il rischio: ha
presidiato **liste ed endpoint**, non la RLS di questa tabella — i due scope
possono divergere lo stesso.
→ `E_ACCREDITO_ANNULLO_INCOMPLETO` (927), sollevato in **tre punti**: un
controllo di visibilità *prima* di scrivere (diagnosi pulita, nessun effetto da
annullare) e un `ROW_COUNT` *dopo* ciascuna delle due scritture (copre la
finestra fra controllo e scrittura). Difesa in profondità gemella di
`E_ACCREDITO_SEGMENT_DUPLICATO`: se scatta è una regressione, non un caso d'uso.

**D-9-3 · ⚠️ Le tre condizioni bloccanti si tengono tutte e tre — «esiste una AF»
sarebbe stato sbagliato.** Il piano dice *«emessa, fatturata o agganciata a un
lotto vivo»*. La scorciatoia «esiste una riga in `attivita_fatturabili` →
bloccato» sembra più prudente ed è invece **un difetto**: dopo un reset di lotto
`fn_cleanup_fatture_by_ids` **non cancella** l'AF, la sblocca e le azzera
`fattura_riga_id`. La scorciatoia vieterebbe per sempre l'annullo dopo un reset
legittimo. Le tre condizioni si scrivono separate:
`stato_emissione <> 'NON_EMESSA'` **oppure** `lock_in_fatturazione` **oppure**
`fattura_riga_id IS NOT NULL`.

**D-9-4 · ⛔ Non si riusa `fn_annulla_commessa_attivita`, benché passerebbe i suoi
guard.** La tentazione è concreta: le rettifiche nascono con
`sorgente_tipo_id NULL` (la madre passa `p_sorgente_tipo_id => NULL`), quindi
supererebbero perfino il guard *«è sourceless»*. Non si riusa perché il suo
**perimetro dichiarato** è la riga MANUALE (le rettifiche sono sourceless per
costruzione, non perché le abbia caricate un operatore: passare quel guard
sarebbe un incidente, non un contratto); perché il suo **evento di log** è
`RIGA_MANUALE_ANNULLATA` e non è parametrizzabile — direbbe il falso proprio
nella riga che serve a ricostruire cosa è successo; e perché è fail-fast **per
riga**, mentre qui la decisione è d'insieme e va presa prima di toccare
qualunque riga. Restano due statement di dominio in linea: non è logica
duplicata, è la stessa scrittura elementare con un contratto diverso.

**D-9-5 · La funzione ritorna le coppie rimosse (`RETURNS TABLE`), non uno
scalare.** Stessa forma con cui la madre le ha create
(`accredito_id, commessa_attivita_id, fattura_riga_rettificata_id, qta,
qta_partita`): il chiamante può dire **cosa** ha disfatto senza rileggere il log.
⚠️ Conseguenza da ricordare: `CREATE OR REPLACE` non cambia un `RETURNS TABLE`,
una modifica futura esige il `DROP` prima.

**D-9-6 · Riga di reso inesistente → `E_VALORE_MANCANTE`**, il codice generico
già usato dalla porta gemella per lo stesso caso. Distinto da
`E_ACCREDITO_NON_TROVATO`, che invece copre insieme *«mai accreditato»* e *«già
annullato»* — indistinguibili **per costruzione**, perché l'annullo cancella. Un
flag per separarle sarebbe il soft-delete che C-3 vieta.

### ⚠️ Due cose viste di passaggio, che non sono di questo passo

* **`trgfn_child_requires_active_parent` rivalida i padri a ogni `UPDATE`.** Se
  un articolo (o una UoM, o un tipo doc) fosse stato disattivato nel frattempo,
  l'annullo fallirebbe con l'errore di quel trigger invece che con un errore di
  dominio. ⚠️ **Non è un difetto nuovo**: vale identico per
  `fn_annulla_commessa_attivita` dal 2026-07-28. Si affronta dove nasce — il
  guard sulla disattivazione — non in una delle due porte ANNULLA.
* **`resi_righe_accrediti` non ha ancora i trigger `z90_storico`/audit/`tx_id`**,
  pur avendone le colonne: è nata il 2026-08-18 e quelle automazioni girano solo
  in contesto `ci_apply`. La sorella `resi_righe_riconsegne` li ha tutti, quindi
  appena l'automazione passa il `DELETE` finirà in storico.
  ⚠️ Da **non** usare come argomento per rilassare il motivo obbligatorio: lo
  storico dirà **cosa** è stato tolto, non **perché**.

### ✅ pgTAP — scritto (2026-08-18)

`db/pgtap/vendite/test-annulla-accredito-riga-reso-v1.sql`, **17 test, verdi**
(`Result: PASS`, 2026-08-18, runner `app` con la RLS attiva).

Due partite, e non è una comodità:

| | Cosa tiene | Perché separata |
| --- | --- | --- |
| **A** (test 1-13) | il percorso pulito: la rettifica non viene **mai emessa** | è l'unico stato in cui **la coda è osservabile**, e la coda è l'unica prova che l'annullo ha funzionato |
| **B** (test 14-17) | la **semantica d'insieme** | il plurale esige rettifiche emesse, e l'emissione lascia `attivita_fatturabili` nel conto della merce |

Le asserzioni che portano il peso: **10)** la coda risale (`accredito_dovuto`
torna 3, `gia_accreditato` a 0); **13)** un secondo accredito **riesce**;
**15)** una sola rettifica emessa rifiuta **l'intero** annullo; **16)** e il
rifiuto **non tocca niente**; **17)** l'`attivita_fatturabili` sopravvissuta al
reset **non blocca** (D-9-3). Più **6)**, che nessuno dei tre guard scriva prima
di rifiutare — un guard che scrive passa inosservato per anni.

⚠️ **La seconda coppia della partita B è costruita nella fixture**, non attesa
dalla madre: il plurale nasce dal consumo LIFO su più righe di fattura o dai
componenti di un kit, e nessuna delle due forme si fissa senza inseguire
l'aritmetica della coda. Ciò che il test collauda è la semantica dell'**annullo**,
il cui ingresso è il ponte — e la seconda rettifica nasce comunque da
`fn_upsert_commessa_attivita`, la stessa che usa la madre. Che la **madre**
produca N coppie resta compito del suo test.

### ⚠️ La trappola che il test ha pagato di persona

La prima stesura del test 17 chiamava
`fn_annulla_accredito_riga_reso` **dentro la stessa `SELECT`** che ne verificava
gli effetti. Esito: `have: 2|2|0` contro `want: 2|0|2` — la funzione risultava
aver restituito due coppie senza averne cancellata nessuna.

⭐ Non era un difetto della funzione. Sotto **READ COMMITTED tutte le sottoquery
di uno stesso statement condividono la snapshot presa al suo inizio**: la
`count(*)` sul ponte leggeva lo stato *prima* della `DELETE`. È la stessa
trappola delle CTE che scrivono, in un'altra veste — e mente nel verso peggiore,
perché **accusa il codice sotto test** invece di segnalare il test.

> **Regola**: in un pgTAP il verbo si chiama in un'**istruzione a parte** (tipico:
> `CREATE TEMP TABLE … AS SELECT * FROM fn_…`), e si asserisce in quella dopo.
> Fa eccezione solo il caso in cui l'asserzione legga *unicamente* il valore di
> ritorno della funzione, senza toccare le tabelle che ha modificato (test 13).

### Cosa resta, in ordine

1. ✅ **§10** — chiuso e applicato lo stesso giorno, vedi in fondo.
2. 🔴 **Passo 4** (P-3, il gate della rinuncia): dipendeva dal passo 3, che ora
   è chiuso. È il prossimo.
3. 🔴 **Passo 5** (P-6, i registri per emittente), con il suo prerequisito nel
   cantiere perimetro emittente (§11.11).

---

## 10. ✅ Il conto della merce smette di contare l'annullato — APPLICATO E VERDE

> Non è un difetto della funzione nuova. È **a valle**, in una vista condivisa,
> e si vede solo mettendo in fila i due meccanismi.
>
> ✅ **Applicato da Tid il 2026-08-18.** Changeset `20260818-73` + **test 18**.
> Il test 18 era rosso prima dell'apply ed è verde dopo: il difetto è stato
> **misurato** in entrambi i versi, non solo argomentato.

### Il fatto

`vendite.vw_af_merce_per_riga` legge `attivita_fatturabili` in join con
`commesse_attivita` e **non filtra `stato_emissione`**:

```sql
FROM vendite.attivita_fatturabili af
  JOIN vendite.commesse_attivita ca ON ca.id = af.commessa_attivita_id
WHERE split_part(ca.segment_key, ':', 1) = ANY (ARRAY['ORD','DDT'])
  AND ca.segment_key ~ ':R:[0-9]+'
```

Da lì `vw_partite_merce` compone
`fatturato = fatturato_merce + fatturato_da_ordine + rettificato`, e
`differenza = tenuti - fatturato`. La coda accrediti mostra la riga solo se
`differenza < 0`.

### Perché mette in crisi proprio la strada consigliata

⚠️ `fn_cleanup_fatture_by_ids` **non cancella** l'`attivita_fatturabili`: la
sblocca e le azzera `fattura_riga_id`. Quindi:

```text
accredito  ->  rettifica -3, nessuna AF          coda: differenza -3  ✅ in coda
emissione  ->  nasce l'AF -3                     coda: differenza  0  (pareggiata)
reset      ->  AF SOPRAVVIVE, ca -> NON_EMESSA   coda: differenza  0
ANNULLO    ->  ponte vuoto, ca -> ANNULLATA
               ⛔ ma l'AF -3 e' ancora li' e continua a valere come «rettificato»
               coda: differenza  0   ->  LA RIGA NON TORNA IN CODA
```

🔴 Il ponte è vuoto, `gia_accreditato` è 0, e **la merce resa non è più
accreditabile da nessuno**: è letteralmente la malattia per cui questo cantiere
esiste, ricreata dal rimedio. E il percorso non è esotico — è quello che il
messaggio di `E_ACCREDITO_ANNULLO_NON_AMMESSO` **consiglia all'operatore**:
*«se il documento non è ancora numerato, la strada è il reset del lotto»*.

⚠️ Sul percorso pulito (rettifica mai emessa) la coda risale correttamente: è il
test 10, ed è verde. Il difetto vive **solo** oltre l'emissione, che è anche il
motivo per cui non si è visto prima.

### Non è solo dell'accredito

Lo stesso vale per `fn_annulla_commessa_attivita` dal 2026-07-28: una riga
manuale emessa, resettata e poi annullata continua a contare come fatturato.
⭐ Il changeset del 2026-07-28 elenca **sei** porte che filtrano già `ANNULLATA`
(`fn_emit_…`, `fn_list_commesse_emittibili`, `fn_list_emittibili_lane`,
`fn_approva_…`, le due dashboard). `vw_af_merce_per_riga` non è nell'elenco
perché legge `attivita_fatturabili`, non `commesse_attivita`: è una **riga
saltata**, non una scelta.

### ⭐ La soluzione — e perché è questa a prescindere dai dati

Aggiungere il filtro alla CTE `base` di `vw_af_merce_per_riga`:

```sql
AND ca.stato_emissione <> 'ANNULLATA'
```

⛔ **La scelta NON dipende da quante righe siano oggi in quello stato.** Il dato
di sviluppo è dato di test: dice se servirà una bonifica, non se il difetto vada
corretto. La domanda è «può succedere?», e la risposta è sì per costruzione.

#### Le tre alternative, e perché cadono tutte

**1. Far cancellare all'annullo le `attivita_fatturabili` delle sue rettifiche.**
⛔ Cade su due fronti: sistemerebbe solo questo percorso, lasciando scoperto ogni
altro modo di arrivare ad `ANNULLATA` (a partire da `fn_annulla_commessa_attivita`,
che ha lo stesso difetto dal 2026-07-28); e romperebbe il vaso. Perché —

**2. Il vaso non si rompe: `attivita_fatturabili` è un mirror DUREVOLE 1:1.**
`fn_emit_attivita_fatturabili_da_commessa` **non inserisce, fa upsert**: cerca la
riga esistente per `(sorgente_tipo_id, sorgente_uid)`, dove `sorgente_uid` è
derivato in modo deterministico dal `segment_key` (md5), e se la trova la
**aggiorna**. È il motivo per cui `fn_cleanup_fatture_by_ids` la lascia in piedi
dopo un reset: è il vaso che il ri-emit riempie di nuovo. ⭐ Ed è anche il motivo
per cui un reset + ri-emit **non** produce due righe che si sommano: quel difetto
non esiste, e la ragione è questa.

**3. Rispecchiare lo stato dentro `attivita_fatturabili`** (una colonna
`annullata`, o riusare `approvato`). ⛔ È l'alternativa che sembra più solida ed è
la peggiore: **il mirror lo aggiorna SOLO l'emit**, e un annullo non chiama
l'emit. Una colonna di stato lì sarebbe **stale per costruzione** — vera il
giorno in cui la si scrive e falsa da subito dopo. Il join al padre è l'unica
cosa che non può invecchiare.

#### E il filtro copre tutto, non un consumatore

⭐ Misurato sul codice, non sui dati: `vw_af_merce_per_riga` è **l'unico** oggetto
in `vendite` che somma `attivita_fatturabili.quantita`. Tutto il conto della
merce passa da lì — `vw_partite_merce`, `vw_contatore_merce_aggregato`,
`vw_situazione_merce_ordine`, `fn_get_stato_push_segment`,
`fn_resi_riga_tetti_accredito` leggono lei, non la tabella. Correggere quella
riga corregge il conto **ovunque**, e non c'è un secondo lettore che domani
ripeta il difetto.

Il che chiude anche la domanda di principio: quel filtro non è una toppa sul
sintomo, è **la definizione stessa** di «quanto ha fatturato questa riga». Una
riga annullata non ha fatturato niente. Che sei porte su sette lo dicessero già
e questa no era una riga saltata.

### Cosa serve per scriverlo

⚠️ Nessuna di queste è una condizione sul *se*: sono il come.

* **leggere i 6 pgTAP che insistono sul confine vecchio** — `test-vw-af-merce-per-riga-v1`,
  `test-vw-partite-merce-v1`, `test-vw-partite-merce-riconsegna-dopo-nc-v1`,
  `test-vw-contatore-merce-v1`, `test-ponte-riconsegna-copre-riga-v1`,
  `test-fn-accredita-riga-reso-v1`. Un filtro che stringe rompe i test scritti
  sul confine di prima, e vanno **letti** prima, non aggiustati dopo;
* ⚠️ **`security_invoker=on` va ri-specificata** nel `CREATE OR REPLACE VIEW`, o
  PostgreSQL la azzera;
* ⭐ **un pgTAP nuovo sul percorso completo**: accredito → emissione → reset →
  annullo → **la coda risale**. È l'unico che dimostra la chiusura, e oggi
  sarebbe rosso;
* **poi**, e solo poi, la bonifica: se esistono righe con un'AF il cui padre è
  già `ANNULLATA`, i loro conti di partita cambiano al primo refresh. Si misura
  come owner (`commesse_attivita` ha la RLS, e come applicazione lo zero è
  fail-closed) e si sistema a mano — non siamo in produzione.

### Il resto della catena, una volta chiuso

* il **test 17** di `test-annulla-accredito-riga-reso-v1` oggi verifica che
  l'annullo **riesca** dopo il reset, ma non che la coda risalga: asserire lì un
  comportamento rotto lo cristallizzerebbe. Dopo la correzione va esteso;
* ⭐ **`fn_annulla_commessa_attivita` guarisce senza essere toccata**: lo stesso
  difetto, la stessa cura, e nessuna modifica alla porta delle righe manuali.

### ✅ Fatto — `20260818-73` + test 18 (2026-08-18)

Tutto dentro questo cantiere, come deciso: niente rimandato.

| | |
| --- | --- |
| `20_code/vendite/20260818-73-update-vw-af-merce-per-riga-esclude-annullate-mctit.yaml` | il filtro, con `security_invoker=on` ri-specificata e il rollback alla definizione del `20260817-06` |
| `test-annulla-accredito-riga-reso-v1.sql` **test 18** | il percorso completo: accredito → emissione → reset → annullo → **la coda risale** |

#### ⭐ La prova che il difetto è reale, non dedotto

Il test 18 è stato eseguito **prima** del changeset, sul database vero:

```text
# Failed test 18: "18) percorso completo … LA CODA RISALE …"
#     (test result was NULL)
Files=1, Tests=18, Failed: 1
```

⭐ `NULL`, non «valore sbagliato»: la riga di reso **non è proprio presente**
nella coda accrediti. È esattamente il sintomo previsto — il ponte è vuoto, la
merce è persa, e nessuno può più accreditarla. Gli altri **17 restano verdi**.

⛔ Il rosso del test 18 sparisce con l'apply di `20260818-73` e **non prima**:
è la definizione stessa di quel changeset.

✅ **E dopo l'apply è verde**: `Files=1, Tests=18, Result: PASS`. Il difetto è
quindi misurato nei **due versi** — rosso senza la correzione, verde con — che è
la sola forma in cui un test dimostra di aver collaudato qualcosa.

#### I sei pgTAP del confine vecchio — letti prima, misurati dopo

**Prima di scrivere**, `grep 'ANNULLATA'` su tutti e sei: **zero occorrenze**.
Nessuno di loro produce mai un'attività annullata — le fixture usano
`NON_EMESSA` e l'emissione. Il filtro **non poteva** cambiarne l'esito, e non
era una previsione ma una misura sul **contenuto dei file**, indipendente dai
dati del database.

✅ **Dopo l'apply, verificato eseguendoli** (2026-08-18):

| Test | Esito |
| --- | --- |
| `test-vw-af-merce-per-riga-v1` | ✅ PASS |
| `test-vw-partite-merce-v1` | ✅ PASS |
| `test-vw-partite-merce-riconsegna-dopo-nc-v1` | ✅ PASS |
| `test-vw-contatore-merce-v1` | ✅ PASS |
| `test-ponte-riconsegna-copre-riga-v1` | ✅ PASS |
| `test-fn-accredita-riga-reso-v1` | ✅ PASS |
| `test-annulla-accredito-riga-reso-v1` | ✅ PASS (18/18) |

Nessuna regressione sul conto della merce.

#### Cosa resta di §10

Solo la **bonifica**, se emergono partite con i conti spostati: si misura come
owner (`commesse_attivita` ha la RLS, come applicazione lo zero è fail-closed) e
si sistema a mano — non siamo in produzione. ⚠️ È un'attività **a valle** e non
una condizione: la soluzione si sceglie sul modello, il dato semmai si bonifica
dopo.

---

---

## 12. ✅ P-3 e P-6 — CHIUSI, APPLICATI E VERDI · 2026-08-19

> Scritto per **chiudere**, non per tracciare. Il rimpallo fra cantieri finisce
> qui.
>
> ✅ **Applicato da Tid il 2026-08-19.** `20260819-02` · `-03` · `-04` · `-05`,
> più i codici 929 a catalogo. **Tutti i test verdi**, comprese 12 suite di
> regressione sulla macchina della numerazione.

### Cosa è stato verificato prima di scriverlo (2026-08-19)

| Verifica | Esito |
| --- | --- |
| `script.fn_check_rinuncia_reversibile` | 🔴 ha **solo** il ramo «riga inesistente», poi `RETURN` con la lista vuota. Il suo commento si autodefinisce *«GATE DORMIENTE … è il PUNTO DI INNESTO»* |
| `anagrafiche.fn_get_emittente_fiscale_id` | 🔴 legge ancora **direttamente** `emittenti_fiscali_billing_account`, due volte (mapping + `is_default`): è la terza copia, intatta |
| trigger `prevent_deactivate` su `emittenti_fiscali_billing_account` | 🔴 assente. Ci sono `default_guard` e `guard_albero_emittente`, entrambi del cantiere emittente |
| `vendite.fn_get_registro_id` | ✅ **la macchina è pronta**: ha già `p_emittente_soggetto_ruolo_id` e il fallback a quattro livelli con l'`ORDER BY` giusto |
| chi la chiama | ✅ `fn_build_fattura_key` passa l'emittente, risolvendolo con `anagrafiche.fn_get_emittente_fiscale_id` |

⭐ **Due conseguenze che cambiano il piano.**

**1. EM-1 è già chiusa.** Il rilievo re-instradato qui dal BE — *«i registri
intestati a un emittente sono irraggiungibili dalla pipeline»* — non è più vero:
la catena `fn_build_fattura_key → fn_get_registro_id` passa l'emittente. Non
serve lavoro, serve **l'asserzione** che lo fissa (5e).

**2. 🔴 5b non è igiene, è chirurgia sul percorso caldo.** `fn_get_emittente_fiscale_id`
è la funzione che `fn_build_fattura_key` usa per **scegliere il registro su cui
numerare**. Cambiarla dopo 5d significherebbe toccare il selettore mentre è in
uso su registri appena intestati. **Va prima**, e da sola.

---

### P-3 · il gate della rinuncia — passo 4

Un ramo dentro `script.fn_check_rinuncia_reversibile`, nella forma che la
funzione già usa (`{codice, reason, reason_key, dettaglio}`): *esiste una riga
in `vendite.resi_righe_accrediti` per questa riga di reso*.

| | Cosa | File |
| --- | --- | --- |
| **A1** | 1 codice errore nuovo a catalogo — il commento della funzione dice esplicitamente di non averlo registrato prima *«per non lasciare a catalogo un codice mai sollevato»*. Ora si solleva | append ai 2 CSV |
| **A2** | il ramo nella funzione + il vincolo reciproco nel commento | `20260819-02` |
| **A3** | il vincolo reciproco anche nel commento di `fn_annulla_accredito_riga_reso` | ✅ **già fatto**: c'è dal `20260818-71`, nessun changeSet |
| **A4** | pgTAP | `test-rinuncia-gate-accredito-v1.sql` |

⚠️ **Ordine dei rami**: il nuovo va **dopo** «riga inesistente», che ritorna
subito — quello è l'**identità** della riga, non una sua condizione.

⚠️ **La funzione è pura e `STABLE`**: produce un motivo, **non solleva**. È
`fn_riapri_riconsegna_reso` a sollevare il primo motivo prodotto, e **non si
tocca**.

⭐ **Il vincolo reciproco di C-3, scritto in ENTRAMBI i commenti**: *il gate si
auto-ripara perché l'annullo **CANCELLA** le righe di ponte. Se un giorno
diventasse un soft-delete, questo ramo va cambiato insieme* — altrimenti
vieterebbe per sempre una rinuncia ormai reversibile, **in silenzio**, perché
nessuno dei due lati sarebbe sbagliato da solo.

🔴 **Richiesta al FE (FE-1), fuori dal perimetro DB**: la chiave i18n
`vendite.resi.rinuncia_reason.accredito_eseguito` in
`frontend/src/locales/it.json` e `en.json`, sul modello di
`…rinuncia_reason.riga_inesistente`. Il DB scrive **solo il `reason_key`**:
senza la chiave, l'utente vede l'identificatore grezzo.

**Test**: accredito → rinuncia **non** riapribile; annullo → **riapribile di
nuovo**. ⭐ Il secondo verso è quello che verifica l'accoppiamento: senza, il
test passerebbe anche con un gate che non si spegne mai.

---

### P-6 · i registri per emittente — passo 5

Quattro changeSet, in **quest'ordine**, e l'ordine è portante.

**B1 · 5b — la terza copia si unifica** → `20260819-03` ✅ **scritto**
`anagrafiche.fn_get_emittente_fiscale_id` delega a
`script.fn_get_ba_emittente_sr_id`, **mantenendo il raise
`E_EMITTENTE_DEFAULT_MISSING` dove è oggi**: la delegata risponde `NULL`, la
chiamante decide se sollevare. ⚠️ È la divergenza di §11.11, e va conservata —
la delegata la usano anche i lettori, che un `NULL` lo sanno gestire.
⭐ Le due logiche sono già identiche: mapping specifico, poi `is_default`. Cambia
**dove vive la regola**, non cosa dice.

**B2 · 5c — il guard sulla disattivazione (D-P6-1)** → ✅ **ESISTE GIÀ, nessun lavoro**
Seed nell'automazione `prevent_deactivate_if_children`: figlia
`anagrafiche.emittenti_fiscali_billing_account`, colonna
`emittente_soggetto_ruolo_id` → `soggetto_ruolo_id`, flag `attivo`.
⚠️ **Prima di B3**: dopo l'intestazione dei registri, disattivare un emittente
diventa una porta aperta su un percorso fiscale, e il guard deve esserci già.

**B3 · 5d — intestazione + registri nuovi, UN SOLO changeSet (C-7)** → `20260819-05` ✅ **scritto**
Nello stesso file e in quest'ordine: `UPDATE` registri **3, 4, 5** →
`emittente_soggetto_ruolo_id = 72`; `INSERT` dei **tre registri** dell'emittente
**159** (Front-office `R2`, Back-office `R1`, NC serie vuota); `INSERT` in
`tipi_doc_fiscale_registri` delle coppie `(tipo_doc, natura)` verso i tre nuovi.
⛔ **Mai in due changeSet**: fra il passo 1 e il 3 esiste una finestra in cui
159 non può numerare (`E_CONFIG_MANCANTE`).
⚠️ `registri_fatturazione.codice` è **UNIQUE** → codici distinti; le **serie** si
ripetono, ed è voluto (D-P6-2: la serie significa **canale**, non azienda).
🟢 Nessun rischio sui documenti esistenti: le 6 fatture di 72 restano sul
registro 3, che diventa suo, e la serie 1→6 continua senza salti.

#### ⭐ B2 non era «far girare l'automazione» — e scoprirlo ha trovato un buco

La domanda era legittima: i trigger `prevent_deactivate_if_children` li genera
`dbops.fn_run_automations_attivo`, quindi basta lanciarla. **No**, e la ragione
è strutturale:

```text
emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id
    --FK--> anagrafiche.soggetti_ruoli (id)      ⛔ non ha la colonna `attivo`
```

L'automazione scopre le figlie da `pg_constraint` partendo dal **padre** della
regola. Il padre giusto — `anagrafiche.emittenti_fiscali`, che `attivo` ce l'ha
e porta già **quindici** trigger di quella famiglia — con questa figlia **non ha
nessuna chiave esterna**. Lanciare l'automazione avrebbe prodotto zero trigger
e **nessun errore**: il tipo di verifica che sembra fatta e non lo è.

⭐ **E la FK mancante non è solo un abilitatore.** Verificato: **nessun presidio**
impone oggi che `emittente_soggetto_ruolo_id` sia davvero un emittente fiscale
— i due guard della tabella parlano di omogeneità dell'albero e di unicità del
default, non dell'identità del bersaglio. Si può mappare un billing account a un
cliente o a un fornitore: la colonna si chiama `emittente_*` e la promessa la
mantiene solo la disciplina di chi scrive.

`20260819-04` **sostituisce** la FK (non ne aggiunge una seconda: quella verso
`soggetti_ruoli` è strettamente più debole, e l'integrità verso `soggetti_ruoli`
sopravvive per transitività). Bersaglio `emittenti_fiscali(soggetto_ruolo_id)`,
che è `UNIQUE` — verificato — e quindi valido.

⚠️ **Se esistono righe che puntano a un non-emittente, l'`ADD` fallisce al
migrate.** Non è un effetto da evitare: è il modo giusto di scoprirle. Si
correggono a mano. ⛔ E non è una condizione per applicare.

#### ⛔ E poi il pgTAP di 5e ha ribaltato la conclusione: il guard c'era già

Il test 6 di `test-registri-per-emittente-v1.sql` è stato scritto per
verificare che il guard *mordesse dopo* l'automazione. È diventato verde
**subito**, e con un messaggio che non avevo previsto:

```
'Disattivazione emittente fiscale non consentita:
 mapping billing_account presente. Soggetto_ruolo_id 159'
```

⭐ Lo solleva `anagrafiche.trgfn_emittenti_fiscali_guard_attivo` — un guard
**scritto a mano**, con codice dedicato `E_EMITTENTE_DISATTIVAZIONE_BLOCCATA`,
che fa **esattamente** ciò che D-P6-1 chiede.

⚠️ Il piano lo dava per mancante perché cercava la famiglia
`prevent_deactivate_if_children` — e in quella famiglia davvero non c'è nulla.
Cercava nel posto sbagliato. **5c non ha lavoro**, e l'automazione non serve.

⭐ **`20260819-04` resta comunque**, ma riqualificato: non è più il prerequisito
di 5c, è la chiusura del difetto che l'indagine ha trovato per strada — nessun
vincolo impone che quel `soggetto_ruolo` sia un emittente. Sono due invarianti
diversi: il guard esistente dice *«non puoi disattivare un emittente mappato»*,
questa FK dice *«non puoi mappare qualcosa che non è un emittente»*.

⚠️ Effetto da tenere d'occhio dopo l'apply: con la FK nuova l'automazione
*potrebbe* generare un sedicesimo trigger, ridondante con quello a mano. Non è
un danno — due guard che dicono la stessa cosa non si contraddicono — ma il
messaggio visto dall'operatore potrebbe cambiare.

#### La misura che serviva a B3 — fatta il 2026-08-19

| Registri | `emittente` | `serie_default` |
| --- | --- | --- |
| Front-office · Back-office · NC | **tutti NULL** | R2 · R1 · (vuota) |

| `tipi_doc_fiscale_registri` (4 righe, `serie` tutte NULL) |
| --- |
| FRONTOFFICE + FATTURA → Front-office · BACKOFFICE + FATTURA → Back-office |
| FRONTOFFICE + NOTA_CREDITO → NC · BACKOFFICE + NOTA_CREDITO → NC |

Emittenti attivi: **sr 72** (42 BA, è il default globale) e **sr 159**
(EMI-TEST, 1 BA). ⭐ La segnalazione del BE era esatta su entrambi i punti.

⭐ **La UNIQUE è su `(tipo_doc, natura, REGISTRO)`** — il registro è nella
chiave, quindi la stessa coppia **può** mappare più registri: è ciò che rende
possibile il disegno di 5d, e andava verificato prima di scriverlo.

⚠️ **La `serie` sul mapping resta `NULL`**: significa «vale il `serie_default`
del registro», e `fn_assign_numero_fattura` lo risolve già. Valorizzarla qui
scriverebbe il default dentro `fatture.serie`.

Nel changeSet **nessun id nudo**: i registri si risolvono per `codice`,
l'emittente principale per il flag `is_default` (che è la definizione di
D-P6-3), il secondo come l'unico altro attivo — ognuno con il suo guard, e i
registri nuovi **clonati** dai vecchi perché `reset_policy` e `serie_default`
arrivino dalla sorgente invece che da una ridigitazione.

**B4 · 5e — pgTAP** → `test-registri-per-emittente-v1.sql`
* ogni registro attivo ha un `emittente_soggetto_ruolo_id` valorizzato — è il
  presidio che impedisce di tornare indietro;
* per **ciascuno** dei due emittenti, `fn_get_registro_id` risolve un registro
  **diverso** su ogni coppia `(tipo_doc, natura)` in uso — ⭐ è anche
  l'asserzione che chiude **EM-1**;
* ⭐ nessun registro è raggiungibile da due emittenti: dice che i buchi nella
  serie (C-4) non possono ripresentarsi;
* ⭐ **il guard di D-P6-1 morde**: disattivare un emittente con billing account
  mappati fallisce. Su un emittente di prova, **non** su 72 o 159.

---

### ✅ Esito — 2026-08-19

| Changeset | Cosa | Esito |
| --- | --- | --- |
| `20260819-02` | il gate della rinuncia si sveglia (+ codice 929) | ✅ `test-rinuncia-gate-accredito-v1` **8/8** |
| `20260819-03` | 5b, la terza copia delega | ✅ coperto dal test 5e e dalle regressioni |
| `20260819-04` | la colonna `emittente_*` diventa un emittente | ✅ applicata **senza righe orfane** |
| `20260819-05` | 5d, intestazione + registri del secondo emittente | ✅ `test-registri-per-emittente-v1` **6/6** |

**La configurazione risultante**, verificata:

```text
registro            serie  reset     emittente   clonato_da
  3 Front-office      R2   ANNUALE      72
  4 Back-office       R1   ANNUALE      72
  5 NC              (vuota) ANNUALE     72
1359 Front-office-159 R2   ANNUALE     159          3
1360 Back-office-159  R1   ANNUALE     159          4
1361 NC-159         (vuota) ANNUALE     159          5
```

8 mappature, quattro per emittente, specchio esatto. ⭐ `serie_default` e
`reset_policy` sono arrivati dalla clonazione, non da una ridigitazione.

⭐ **La FK di `20260819-04` è passata**, e questo è un dato: significa che
**nessuna riga puntava a un non-emittente**. Il difetto era aperto ma non
ancora sfruttato — la cosa migliore che potesse dire quel migrate.

**Regressioni**: 12 suite fra le più esposte — `test-emittenti-fiscali`,
`test-registri-progressivi`, `test-numera-fattura-opz-emessa`,
`test-numerazione-guard-coerenza-v1`, `test-chiave-fattura-tre-specchi-v1`,
`test-fn-accredita-riga-reso-v1`, `test-annulla-accredito-riga-reso-v1`,
`test-accredito-kit-meta-v1`, `test-vw-resi-da-accreditare-contatore-v1`,
`test-vw-partite-merce-v1`, `test-snapshot-intestazione-fattura-v1`,
`test-rls-fatture-satelliti-functional` — **tutte PASS**. Era la verifica che
5b esigeva: `fn_get_emittente_fiscale_id` sta sul percorso caldo della
numerazione.

### ⚠️ Due cose che restano vere dopo la chiusura

* **Non esiste più un registro generico.** Un terzo emittente che comparisse
  prenderebbe `E_CONFIG_MANCANTE` alla prima fattura. È fail-closed e va bene —
  meglio un errore parlante che numerare sul registro di un'altra azienda — ma
  da oggi «aggiungere un emittente» vuol dire anche tre registri e le loro
  mappature.
* 🔴 **FE-1**: la chiave i18n `vendite.resi.rinuncia_reason.accredito_eseguito`
  in `frontend/src/locales/it.json` e `en.json`. Senza, l'operatore a cui il
  gate nega la riapertura vede l'identificatore grezzo.

---

## Riferimenti

* Brief principale e piano BE/FE: [brief-design-note-credito-resi.md](brief-design-note-credito-resi.md)
  — decisioni §21.4, numeratore §21.5, piano §22 → §26
* Partita generalizzata (cantiere 1): [brief-design-partita-merce-generalizzata.md](brief-design-partita-merce-generalizzata.md)
* Pannello situazione merce (cantiere 2): [brief-design-situazione-merce-ordine.md](brief-design-situazione-merce-ordine.md)
* Perimetro emittente (cantiere **chiuso** il 2026-08-18): [brief-db-perimetro-emittente-liste-e-gerarchia-ba.md](../work-done/brief-db-perimetro-emittente-liste-e-gerarchia-ba.md)

---

## ⚠️ Dopo la chiusura: «aggiungere un emittente» non è più una riga di anagrafica

Conseguenza di P-6, verificata dal lato applicativo il 2026-08-19.

Prima i tre registri avevano `emittente_soggetto_ruolo_id = NULL` e facevano da
**fallback per chiunque**: il livello 4 di `fn_get_registro_id` («utility NULL e
emittente NULL») copriva qualunque emittente. Ora ogni registro è intestato,
quindi un **terzo emittente** prenderebbe `E_CONFIG_MANCANTE` alla prima
fattura.

⭐ È fail-closed ed è la scelta giusta — meglio un errore parlante che numerare
sul registro di un'altra azienda. Ma il punto in cui si paga è a **monte**, e
quel punto esiste già nel frontend: `EmittenteFiscaleDrawer.vue` +
`createEmittenteFiscale` (POST `/amministrazione/emittenti-fiscali/`) creano un
emittente in tre click, e nulla dice che servono anche **tre registri e le
quattro mappature** `(tipo_doc, natura)`.

Le tre strade, per chi la prenderà in carico:

| Strada | Costo | Cosa lascia |
| --- | --- | --- |
| **avviso nel drawer** di creazione emittente | FE, piccolo | l'operatore sa cosa manca, ma deve farlo a mano (ed è configurazione DB) |
| **seed automatico** dei registri alla creazione | DB + BE | l'emittente nasce completo. ⚠️ Ma «quali serie» è una decisione fiscale, non un default |
| **niente** | zero | il difetto si scopre alla prima fattura, con un errore parlante e nessun documento sbagliato |

📌 Non è stata presa: **serve una decisione**. La terza è difendibile (il
fail-closed funziona), la prima costa poco. La seconda no: la serie significa
canale, e sceglierla per conto dell'operatore è la cosa che D-P6-2 evita.
