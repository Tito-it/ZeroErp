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

| # | Cosa | Peso | Blocca |
| --- | --- | --- | --- |
| **P-1** | Azione di processo `accredita_riga_reso` | 1 riga di CSV | ⛔ la **consegna** del verbo (B2, F1) |
| **P-2** | Registry del task `popola_fatture_rettifiche` + il task nelle pipeline 4 e 6 | 2 righe di registry + 2 JSON di seed | ⛔ la slice **B6** |
| **P-3** | 🔴 Il gate `fn_check_rinuncia_reversibile`, rimasto dormiente | un ramo dentro una fn esistente + 1 codice a catalogo | 🔵 niente lato BE — è un buco di dominio aperto **adesso** |
| **P-4** | I quattro valori del sezionale NC | ✅ **nessun lavoro**: confermati come seedati | — |
| **P-5** | 🔴 La madre `fn_annulla_accredito_riga_reso` | 1 fn nuova + 2 codici a catalogo | ⛔ la slice **B2-bis**, F1 |
| **P-6** | 🔴 Nessun registro è intestato a un emittente, e gli emittenti che emettono sono **due** | riconfigurazione del seed registri + mapping | ⛔ niente di BE/FE — è un **difetto fiscale in esercizio** |

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

**Cosa serve, tre pezzi.**

1. `dbops.pipeline_task_registry`: il task `popola_fatture_rettifiche` sul
   dominio `vendite`;
2. `dbops.pipeline_task_registry_impl`: `implementation_key = default`,
   **`handler_code = popola_fatture_rettifiche_default`** — è la stringa esatta
   con cui il backend registra l'handler nel `handler_registry` di
   `PipelineStepExecutor`;
3. `vendite/fatturazione_pipeline.csv`, righe **4** (massiva DEFINITIVA) e **6**
   (giornaliera DEFINITIVA): il task nel JSON `processi`, **fra
   `numera_fatture` e `stampa_documenti_lotto`**.

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
* 📌 va portato anche al cantiere **perimetro emittente**, che è aperto: è la
  richiesta **EM-1** del §17.4 del brief principale, e questa misura la rende
  concreta invece che latente.

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

## Riferimenti

* Brief principale e piano BE/FE: [brief-design-note-credito-resi.md](brief-design-note-credito-resi.md)
  — decisioni §21.4, numeratore §21.5, piano §22 → §26
* Partita generalizzata (cantiere 1): [brief-design-partita-merce-generalizzata.md](brief-design-partita-merce-generalizzata.md)
* Pannello situazione merce (cantiere 2): [brief-design-situazione-merce-ordine.md](brief-design-situazione-merce-ordine.md)
* Perimetro emittente (cantiere aperto): [brief-db-perimetro-emittente-liste-e-gerarchia-ba.md](brief-db-perimetro-emittente-liste-e-gerarchia-ba.md)
