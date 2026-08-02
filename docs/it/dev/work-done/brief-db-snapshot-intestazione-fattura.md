# Brief DB — snapshot dell'intestazione fiscale della fattura

> ## ✅ CHIUSO — 2026-08-02
>
> **Tutte le richieste sono state evase.** `emittente_snapshot` /
> `cliente_snapshot` in testata con guard di congelamento (I.1),
> `fn_snapshot_intestazione_fattura` come funzione **sorella** e non estensione
> (I.2), wrapper rinominato `fn_snapshot_fattura_lotto` col sesto contatore
> (I.3), guard di uscita da DRAFT col criterio allargato — indirizzi **e**
> intestazione (I.4, codice **575**), pgTAP `plan(12)` (I.6).
>
> ✅ **Anche il §3.6 è stato evaso** (I.5, 2026-08-02): la matrice
> `config.tipi_ruolo_tipi_indirizzo` per il ruolo **EF** è seminata con i cinque
> tipi decisi in §10.3 — `SEDE-LEG`, `DOM-FISC`, `SEDE-OP`, `POSTALE`, `RESID`,
> tutti `obbligatorio = false`. Verificato dopo l'apply: `SPED` viene ora
> **respinto** dal guard su un ruolo EF, `SEDE-LEG` e `RESID` passano.
>
> ⚠️ **Due rettifiche a questo documento, da leggere se lo si riusa come
> modello.** (1) La premessa del §3.6 — «gli emittenti hanno oggi `SEDE-LEG` sul
> layer RUOLO grazie al fail-open» — è **falsa**: i ruoli EF non hanno **alcun**
> indirizzo, le sedi stanno tutte sul layer SOGGETTO. Era già rilevato in §10.3 e
> riconfermato il 2026-08-02. Il fail-open non reggeva nulla: era un buco non
> sfruttato, non un puntello — la conclusione «seedare» resta giusta, cade solo
> l'urgenza. (2) Il numero **«42 emittenti su 42»** di §10.3 non conta gli
> emittenti: gli emittenti fiscali sono **2**. Conta le coppie
> `billing_account → emittente` (oggi 43). La metà che importa — **zero sul layer
> RUOLO** — è confermata.
>
> Stato del cantiere: [piano-db-satelliti-fattura.md](../work-in-progress/piano-db-satelliti-fattura.md) §9.

---

> **Chi scrive:** BE (`dev/backend-tid`), 2026-07-31.
> **A chi:** team DB (`dev/db-tid`).
> **Cos'è:** **estensione della Fase 2** («ristampa conforme») del piano
> [piano-be-fe-satelliti-fattura.md](../work-in-progress/piano-be-fe-satelliti-fattura.md). Non è un
> cantiere nuovo: è il completamento della stessa garanzia che la Fase 1 ha
> aperto a metà.
> **Prerequisiti nuovi:** nessuno. Si innesta su 2.0-2.2 già applicate.
> **Impatto sull'armamento in corso (2.3 parte 2 → 2.5): nessun cambio di
> rotta** — vedi §7. La vostra coda di lavoro resta valida così com'è.
> **Origine:** domanda di Tid del 2026-07-31 («per l'indirizzo emittente
> possiamo sfruttare lo storico degli indirizzi?»). La risposta è no, ed è nel
> §2; misurando il perché è emerso che il buco è più largo della sola sede.

---

## 1. Il problema, e la prova che non è teorico

La Fase 1 congela l'**indirizzo del cliente** in `fatture_indirizzi`. Tutto il
resto dell'intestazione della fattura continua a leggersi **live**
dall'anagrafica, al momento della stampa:

| Cosa si stampa | Da dove viene oggi | Dove nel codice |
|---|---|---|
| Denominazione, P.IVA, CF **dell'emittente** | `vw_soggetti_ruoli_dettaglio` (live) | `vendite_repository.py:1593-1595` |
| **Sede legale** dell'emittente | `vw_indirizzi_resolved_ruolo` (live) | `vendite_repository.py:1600-1605` |
| Denominazione, P.IVA/CF **del cliente** | `vw_soggetti_ruoli_dettaglio` (live) | `vendite_repository.py:1614-1615` |
| Indirizzo di fatturazione del cliente | `vw_indirizzi_resolved_ruolo` (live) → **snapshot** con la Fase 2 | `vendite_repository.py:1619-1624` |

Su `vendite.fatture` l'unico snapshot esistente è `termine_pagamento_snapshot`:
**nessuno congela l'intestazione fiscale delle due parti.**

La conseguenza, se ci fermiamo alla Fase 2 come scritta: un cliente che cambia
ragione sociale o partita IVA **cambia la ristampa di tutte le sue fatture
passate**, e lo fa lasciando congelato l'indirizzo nel rigo sotto. Non è
«meno conforme di prima»: è **incoerente dentro lo stesso blocco stampato**,
che è peggio di una intestazione interamente live, perché sembra congelata.

### Un difetto già attivo, trovato misurando

Le viste `vw_indirizzi_resolved_*` espongono **due** colonne di codice:

| Colonna della vista | Contenuto | Esempi |
|---|---|---|
| `tipo_indirizzo_codice` | `config.tipi_indirizzi.codice` | `SEDE-LEG`, `CONS`, `FORN`, `RESID` |
| `tipo_indirizzo_codice_interno` | `codice_interno` | `SEDELEG`, `CON`, `FORNITURA`, `RES` |

`get_fattura_testata` filtra `tipo_indirizzo_codice = 'SEDELEG'`
(`vendite_repository.py:125`), cioè confronta un **codice_interno** con la
colonna che contiene il **codice**. Controprova sul DB:

```
righe con 'SEDELEG'  → 0
righe con 'SEDE-LEG' → 4
righe con 'FATT'     → 11
```

Quindi la **sede legale dell'emittente non è mai stata stampata**: la subquery
non ha mai trovato nulla. L'indirizzo cliente funziona solo perché per il tipo
`FATT` i due codici coincidono per caso. È il terzo esemplare della categoria
che il piano §1 punto 2 cita come motivo di esistere del collaudo end-to-end
(«sembra funzionare e invece è vuoto»).

**La correzione è nostra e sta dentro la Fase 2** (una parola: filtrare su
`tipo_indirizzo_codice_interno`, o meglio non filtrare affatto perché si legge
lo snapshot). Lo scriviamo qui perché è la prova che il blocco emittente non è
mai stato verificato a video da nessuno, e va trattato come territorio nuovo,
non come codice funzionante da preservare.

### Il momento è il più economico possibile

Misurato oggi sul DB di sviluppo:

| Tabella | Righe |
|---|---|
| `vendite.fatture` | **0** |
| `vendite.fatture_indirizzi` | **0** |

Non c'è **niente** da migrare, bonificare o rigenerare: nessuna fattura
esistente, nessun fallback da scrivere, nessuna compatibilità da tenere. Le
«7 fatture storiche» che il piano §9 dichiarava sacrificabili non esistono
nemmeno più. Ogni giorno che passa questo numero può solo crescere.

---

## 2. Perché lo storico degli indirizzi non è la strada

Domanda legittima di Tid, e la macchina esiste davvero: trigger
`_z90_storico_upd_dlt` su tutte e tre le tabelle. Ma la storicizzazione è
**opt-in per riga**, via il flag `storicizza`, e oggi:

| Tabella | Righe | `storicizza` | Righe in `storico.*` |
|---|---|---|---|
| `anagrafiche.indirizzi` (layer **RUOLO**) | 18 | **tutte `false`** | **0** |
| `anagrafiche.indirizzi_dettaglio` (via, civico, CAP) | 74 | **tutte `false`** | **0** |
| `anagrafiche.indirizzi_soggetti` (layer SOGGETTO) | 90 | tutte `true` | 142 |

La sede dell'emittente si risolve sul layer **RUOLO**, cioè esattamente la
tabella con storico vuoto e flag spento; e il contenuto vero dell'indirizzo sta
in `indirizzi_dettaglio`, anch'essa a zero. Accendere i flag oggi non produce
nulla di retroattivo.

Ma anche a storico pieno non lo useremmo, per tre ragioni di merito:

1. **Lo storico registra la riga, non il documento.** Ciò che si stampa è
   l'esito di una catena di risoluzione (quale tipo, quale layer
   RUOLO/SOGGETTO, precedenza istanza, formattazione di `indirizzo_display`)
   che unisce `indirizzi` + `indirizzi_dettaglio` + comuni/CAP/province/stati.
   Ricostruire «com'era il 12 febbraio» è un join temporale su più tabelle, di
   cui alcune **non storicizzate affatto** (comuni, CAP, stati), rieseguendo una
   catena il cui SQL nel frattempo è cambiato. Una ricostruzione così può essere
   plausibile, non dimostrabile — e su un documento fiscale serve la seconda.
2. **Il tempo dello storico è quello della transazione, non del documento.**
   `valid_from` dice quando la riga è cambiata nel DB, non da quando
   l'indirizzo era valido. Correzioni retrodatate, import e i trigger
   `normalize` muovono righe senza rapporto con la data fattura: la ristampa
   seguirebbe la storia della manutenzione anagrafica.
3. **Sarebbe asimmetrico con la scelta già fatta sul cliente.** Se lo storico
   bastasse, `fatture_indirizzi` e la Fase 1 non avrebbero motivo di esistere.

Lo storico resta quello che è: uno strumento di **audit**, che risponde a «chi
ha cambiato cosa e quando». Non è una fonte documentale.

---

## 3. Cosa chiediamo

Un solo criterio, applicato alle due parti: **tutto ciò che il documento stampa
è congelato sul documento, al momento in cui il documento nasce.**

### 3.1 Identità fiscale delle due parti — due colonne in testata

Su `vendite.fatture`, due colonne `jsonb` NULLable, stessa convenzione di nome
di `termine_pagamento_snapshot`:

| Colonna | Contenuto proposto |
|---|---|
| `emittente_snapshot` | `denominazione`, `codice_fiscale`, `id_fiscale` (P.IVA), `regime_fiscale_rf`, `soggetto_ruolo_id`, `emittente_fiscale_id`, `sede` (shape canonico indirizzo) |
| `cliente_snapshot` | `denominazione`, `codice_fiscale`, `id_fiscale`, `soggetto_ruolo_id`, `billing_account_id`, `ba_codice`, `codice_sdi`, `pec_fatturazione` |

Note di perimetro, da decidere consapevolmente:

- **`regime_fiscale_rf`** è già su `anagrafiche.emittenti_fiscali`. Entra ora
  perché è un dato **del documento**, non dell'anagrafica: è il regime con cui
  quella fattura è stata emessa.
- **`codice_sdi` / `pec_fatturazione`** del cliente (da `dati_societari`):
  entrano perché l'instradamento SDI di una fattura inviata **è un fatto del
  documento** — «a chi l'abbiamo trasmessa» non può cambiare retroattivamente.
- **`iscrizione_rea`, `capitale_sociale`, `socio_unico`, `liquidazione`,
  `forma_giuridica_id`** (tutti su `anagrafiche.dati_societari`): servono al
  blocco `IscrizioneREA` / `DatiAnagrafici` del `CedentePrestatore` FatturaPA.
  **Proponiamo di includerli subito** nello snapshot dell'emittente: aggiungerli
  dopo significa rifare il giro su fatture già emesse, e il costo oggi è una
  chiave in più in una `jsonb` che stiamo già scrivendo. Se preferite un
  perimetro minimo ora, va bene lo stesso — ma allora dichiariamolo per
  iscritto come rinvio, non come dimenticanza.

### 3.2 Sede dell'emittente: dentro `emittente_snapshot`, non in `fatture_indirizzi`

Abbiamo valutato l'alternativa di aggiungere `SEDELEG` alla whitelist ambito
`FATTURE` e usare uno slot di `fatture_indirizzi`. **La sconsigliamo**, e la
ragione è di modello, non di comodità:

| | Slot in `fatture_indirizzi` | Dentro `emittente_snapshot` |
|---|---|---|
| Riuso della macchina esistente | ✅ tabella, trigger, funzione, guard | ➖ colonna nuova |
| «Di chi è questo indirizzo?» | ❌ la tabella **non ha il concetto di parte**: oggi ogni slot è del cliente, e `SEDELEG` diventerebbe una convenzione implicita «= emittente» | ✅ esplicito per costruzione |
| Cliente PG con sede legale propria | ❌ la `UNIQUE (fattura_id, tipo_indirizzo_id)` rende **impossibile** avere sia la sede dell'emittente sia quella del cliente | ✅ nessun conflitto |
| Pannello indirizzi FE (§7 del piano) | ❌ `SEDELEG` comparirebbe come slot **proponibile all'operatore sul cliente** | ✅ invisibile: non è uno slot |
| Intestazione fiscale leggibile in un colpo | ❌ sparsa fra testata e satellite | ✅ un campo |

Renderlo corretto nella prima colonna richiederebbe una colonna discriminante
`parte` (`EMITTENTE`/`CLIENTE`), il suo ingresso nella UNIQUE e una whitelist
**per parte**: cioè una modifica di modello del satellite, non una riga di seed.

**L'asimmetria che ne risulta è voluta e non è di garanzia, è di cardinalità.**
Il cliente ha *N* slot indirizzo (`FATT` obbligatorio, `CON`/`FORNITURA`/`RES`
opzionali) perché il documento può usarne più d'uno; l'emittente ne ha **uno**,
che non è uno slot ma una riga della sua intestazione. La simmetria che conta —
*tutto ciò che si stampa è congelato* — resta piena su entrambe le parti.

### 3.3 Chi scrive, e quando: **estendere la funzione esistente, non aggiungerne una**

Richiesta operativa precisa, perché è quella che tiene fermo il vostro lavoro in
volo: **`fn_snapshot_indirizzi_fattura` / `fn_snapshot_indirizzi_lotto` restano
il punto unico**, con nome e firma invariati.

- stessa transazione, stesso step DRAFT, stesso task `snapshot_indirizzi_lotto`;
- **contatori invariati** (`fatture_count, inserted_rows, updated_rows,
  skipped_rows, failed_rows`): il BE li legge già e non cambia una riga;
- **semantica D-Q invariata**: se manca l'obbligatorio la fattura viene marcata
  `'C'` e le altre si lavorano; il conteggio `failed_rows` continua a governare
  il `task_run` in ERRORE lato nostro.

Se preferite un nome che dica la verità (`fn_snapshot_intestazione_fattura`), per
noi va bene, ma allora **serve la rinomina anche in `ALLOWED_TASK_FUNCTIONS`**
(`pipeline_repository.py:176`) e nei test: ditecelo e la facciamo contestualmente,
come per D-L. Se invece l'armamento 2.3 parte 2 è già scritto col nome attuale,
**tenetelo**: il costo di un nome imperfetto è minore del costo di una rinomina
in mezzo a un armamento.

### 3.4 Immutabilità simmetrica

`fatture_indirizzi` è già protetta da
`trgfn_fattura_satellite_guard_congelamento`. Le due colonne nuove **devono
avere la stessa protezione**: dopo il congelamento della fattura non si toccano.
Altrimenti il satellite è blindato e la testata no, e la garanzia si aggira
dalla porta accanto.

### 3.5 Il guard 2.5 va allargato

Il guard «`FATT` obbligatorio» presidia l'indirizzo. Con questo brief il criterio
diventa: **una fattura non lascia DRAFT senza intestazione congelata** —
`emittente_snapshot` e `cliente_snapshot` valorizzati, oltre alla riga `FATT`.
Senza questo, il caso «snapshot mai scritto» resta possibile e silenzioso,
esattamente come la sede legale mai stampata del §1.

### 3.6 Seed della matrice indirizzi per il ruolo `EF` (fail-open oggi)

`config.tipi_ruolo_tipi_indirizzo` **non ha righe per `tipo_ruolo = 7` (EF —
Emittente fiscale)**, e il guard
`trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo` in quel caso passa
(«nessuna matrice definita → indirizzi liberi»). Gli emittenti hanno oggi
`SEDE-LEG` sul layer RUOLO **grazie al fail-open, non per progetto**.

Chiediamo di **seedare esplicitamente `EF → SEDELEG`** (e valutare `FATT`,
`POSTA`). Costo nullo, e chiude un buco a orologeria: il giorno in cui qualcuno
seeda una matrice per il ruolo EF senza `SEDELEG`, la catena dell'emittente
smette di trovare l'indirizzo — e lo scopriremmo, di nuovo, da una stampa vuota.

---

## 4. Cosa **non** chiediamo

| Cosa | Perché no |
|---|---|
| Bonifica o rigenerazione di fatture esistenti | Ce ne sono **zero** (§1) |
| Fallback alla vista live per fatture senza snapshot | Stessa ragione, e il piano §9 l'ha già escluso: sarebbe codice che nasce da rimuovere |
| Accendere `storicizza` sugli indirizzi | Non serve a questo scopo (§2). Se lo si vuole per audit, è una decisione **separata** |
| Una tabella satellite nuova per l'intestazione | L'emittente e il cliente sono **uno** per fattura: due colonne in testata, non una collezione |

---

## 5. Cosa facciamo noi (BE), appena la forma è decisa

Tutto dentro la Fase 2, che a quel punto si scrive **una volta sola** sulla forma
definitiva invece di essere ripuntata due volte:

| File | Cosa |
|---|---|
| `db/vendite_repository.py:1593-1624` | le quattro letture live → snapshot: `emittente_snapshot`, `cliente_snapshot`, riga `FATT` da `fatture_indirizzi`. **Sparisce** la subquery su `vw_indirizzi_resolved_ruolo`, e con essa il difetto `codice`/`codice_interno` del §1 |
| `services/fattura_document_context_builder.py:197-211` | `_shape_cliente` + nuovo `_shape_emittente` leggono lo snapshot. Modello già in casa: `DdtDocumentContextBuilder._shape_indirizzi` |
| `scripts/tests/smoke-fattura-indirizzi-snapshot.py` | asserzione 8 (ristampa conforme) esce dallo SKIP e si estende alle due intestazioni |
| — | nessun impatto su handler, runner, `ALLOWED_TASK_FUNCTIONS` (se vale §3.3) |

---

## 6. Definizione di «fatto»

Le asserzioni si aggiungono allo smoke §3.1 già esistente e verde, che passa
dalla **pipeline reale**:

| # | Asserzione |
|---|---|
| 9 | Dopo un giro DRAFT, ogni fattura ha `emittente_snapshot` e `cliente_snapshot` non vuoti |
| 10 | **Ristampa conforme, emittente**: cambio la ragione sociale e la sede dell'emittente in anagrafica → il PDF ristampato **non cambia** |
| 11 | **Ristampa conforme, cliente**: cambio ragione sociale e P.IVA del cliente → il PDF ristampato **non cambia** |
| 12 | La sede legale dell'emittente **compare** nel PDF (oggi è sempre vuota: §1) |
| 13 | Idempotenza: secondo giro → nessuna riscrittura, nessun duplicato |
| 14 | Guard: una fattura senza intestazione congelata **non** lascia DRAFT (§3.5) |

L'asserzione 12 è quella che vale il brief: è l'unica che oggi fallirebbe
**anche prima** di qualunque modifica anagrafica.

---

## 7. Ordine, e perché non vi cambia la coda di lavoro

Questo brief **non ferma e non riordina** l'armamento in corso:

1. **2.3 parte 2** (nodo nei `processi` DRAFT, corsie 1 e 8) → invariato: il task
   è lo stesso, il nome è lo stesso, i contatori sono gli stessi;
2. **2.5** (guard `FATT`) → qui c'è l'unico innesto: conviene **allargarne il
   criterio** (§3.5) prima di accenderlo, invece di accenderlo e riaprirlo dopo;
3. §3.1-3.4 possono arrivare **in parallelo o subito dopo** 2.3: finché non ci
   sono, la Fase 2 resta ferma — ma è già ferma oggi, in attesa di 2.3.

L'unica cosa che chiediamo **prima** di 2.5 è la decisione sulla forma (§3.1 e
§3.2). Il resto può seguire il vostro ritmo.

---

## 8. Trappole misurate, per i pgTAP di 2.4

Nessuna è un difetto: sono inciampi che abbiamo già pagato noi collaudando, e
che si ripresenteranno scrivendo le vostre fixture.

1. **`codice` ≠ `codice_interno` sulle viste risolte** (§1). Le vostre funzioni
   fanno la cosa giusta — `fn_resolve_indirizzo_documento` dichiara
   esplicitamente «Tipo per codice_interno (immutabile), mai per codice» — ma una
   **fixture** che interroga `vw_indirizzi_resolved_*` filtrando `SEDELEG`,
   `CON`, `RES` o `FORNITURA` non trova nulla e passa in silenzio come «tipo
   assente». I codici da usare sulle viste sono `SEDE-LEG`, `CONS`, `RESID`,
   `FORN`; oppure si filtra `tipo_indirizzo_codice_interno`.
2. **`CON` non è ottenibile dal layer RUOLO di un cliente** — già in §4-ter (a)
   del piano.
3. **Gli indirizzi liberi hanno un CHECK a quattro campi** — già in §4-ter (b).
4. **Il ruolo `EF` non ha matrice** (§3.6): una fixture che inserisce indirizzi
   su un emittente oggi passa per fail-open. Se seedate la matrice, quelle
   fixture cominciano a essere verificate davvero — atteso, ma va saputo prima.
   ℹ️ *Aggiornamento 2026-08-01 (§10.10)*: il ruolo `EF` non ha matrice **e non
   ha indirizzi** — misurato su tutta la popolazione, **42 emittenti su 42**
   hanno la sede sul layer SOGGETTO e **zero** sul RUOLO. Una fixture che
   pretendesse la sede dell'emittente sul ruolo non troverebbe nulla: va cercata
   sul soggetto, oppure risolta con `script.fn_resolve_indirizzo_documento`, che
   scende da sola.

---

## 9. La domanda a cui questo brief risponde davvero

Non «dove mettiamo la sede dell'emittente», ma: **quando qualcuno ristampa una
fattura di due anni fa, cosa gli garantiamo?** Oggi la risposta onesta è «gli
importi, e da domani l'indirizzo del cliente». Con questo brief diventa «il
documento», che è l'unica risposta che regge davanti a un controllo — ed è anche
la fonte da cui nascerà il `CedentePrestatore` del builder XML FatturaPA, oggi
non ancora scritto: `fn_prepare_sdi_payload` porta solo gli **id**
(`billing_account_id`, `emittente_soggetto_ruolo_id`) e risolverà a valle
qualunque fonte gli indichiamo. Deciderlo adesso significa farlo nascere giusto
invece di correggerlo dopo.

---

## 10. 📎 Risposta del team DB (2026-07-31)

> **Chi scrive:** DB (`dev/db-tid`). Terza nota scambiata fra i due piani, dopo
> la vostra §4-ter e la nostra su D-Q. **Esito: brief accolto**, con due
> decisioni di forma e tre rilievi, uno dei quali ribalta una vostra premessa.

### 10.0 Cosa abbiamo riverificato per conto nostro

Non per diffidenza: perché un brief che chiede di cambiare il modello va letto
con le stesse mani con cui si scriverà il codice.

| Vostra affermazione | Esito |
|---|---|
| `get_fattura_testata` confronta un `codice_interno` con la colonna che porta il `codice` | ✅ **confermato** leggendo la query: `ind_em.tipo_indirizzo_codice = %s` con `%s = 'SEDELEG'`, mentre la sede legale ha `codice = 'SEDE-LEG'`. Il cliente funziona per coincidenza (`FATT` ha i due valori identici); `FORNITURA` sarebbe stato `FORN` |
| `config.tipi_ruolo_tipi_indirizzo` non ha righe per il ruolo `EF` | ✅ **confermato**: righe solo per i ruoli 1, 2, 3 |

### 10.1 DECISIONE — funzione **sorella**, non estensione (risposta a §3.3)

`vendite.fn_snapshot_indirizzi_fattura` **resta com'è**. L'intestazione la
scrive una gemella, `vendite.fn_snapshot_intestazione_fattura(p_fattura_id)`,
chiamata **dallo stesso wrapper di lotto**, stesso giro, stessa transazione.

**Perché non l'estensione, che pure chiedevate.** I contatori mentirebbero. La
funzione ritorna `(inserted_rows, updated_rows)` e il wrapper i cinque che voi
leggete: descrivono **righe di indirizzo**. Se la stessa funzione scrivesse
anche due colonne di testata, quel lavoro non comparirebbe in nessun contatore
— `(0,0)` continuerebbe a dire «niente da fare» subito dopo aver riscritto
l'intestazione — e l'idempotenza che i pgTAP 2.4/2.2 hanno appena messo sotto
esame smetterebbe di dire ciò che dice.

**Per voi non cambia nulla**, ed è il punto: il «punto unico» che chiedete è il
**task**, e resta uno solo. Stesso `task_code`, stesso handler, stessi cinque
contatori, stessa semantica D-Q. Nessuna rinomina in
`ALLOWED_TASK_FUNCTIONS`, nessun tocco ai vostri test. Se in futuro serviranno
contatori per l'intestazione si aggiungono **al wrapper**, che è dove li leggete
già.

Ne segue che la vostra domanda sul nome (`fn_snapshot_intestazione_fattura`)
non si pone: ciascuna delle due funzioni si chiama come ciò che fa.

### 10.2 DECISIONE — perimetro §3.1 **completo**, ma shape **non contrattuale**

Accolta la vostra proposta di includere subito `iscrizione_rea`,
`capitale_sociale`, `socio_unico`, `liquidazione`, `forma_giuridica_id`,
oltre a `regime_fiscale_rf`, `codice_sdi` e `pec_fatturazione`. Il vostro
argomento è corretto: aggiungerli dopo significherebbe rifare il giro su
fatture già emesse, e oggi il costo è una chiave in più in una `jsonb` che
stiamo comunque scrivendo.

**Con una clausola, e va scritta ora**: finché il builder XML FatturaPA non
esiste, lo shape di `emittente_snapshot` e `cliente_snapshot` è **interno e non
contrattuale**. Aggiungere, rinominare o annidare una chiave resta lecito senza
migrazioni e senza rigenerare documenti. Una chiave in più costa nulla; un
contratto dichiarato prima di avere il consumatore costa parecchio — ed è
esattamente ciò che il builder, quando nascerà, ci chiederà di cambiare.

### 10.3 🔴 RILIEVO — il censimento del ruolo `EF` dà **zero**, e ribalta la premessa di §3.6

Scrivete che «gli emittenti hanno oggi `SEDE-LEG` sul layer RUOLO grazie al
fail-open». Misurato:

```sql
SELECT ti.codice_interno, count(*)
  FROM anagrafiche.indirizzi i
  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = i.soggetto_ruolo_id
  JOIN config.tipi_indirizzi ti      ON ti.id = i.tipo_indirizzo_id
 WHERE sr.tipo_ruolo_id = 7
 GROUP BY 1;
```

→ **nessuna riga.** I ruoli `EF` non hanno **alcun** indirizzo. Le 4 righe
`SEDE-LEG` che avete contato stanno quindi su **altri ruoli** — e i ruoli 2 e 3
hanno già `SEDELEG` in matrice, come obbligatorio.

**Conseguenza sulla vostra §1: i difetti sono due, non uno** (precisazione di
Tid, 2026-07-31). La regola del modello è la stessa per tutti i ruoli:
*l'indirizzo si prende dal ruolo se c'è, altrimenti da quello del soggetto*.
Quindi la sede dell'emittente **non manca**: sta sul layer SOGGETTO — che è
anche l'unico dei due che nei vostri numeri di §2 ha righe (90) e storico pieno.

| # | Difetto | Chi l'ha trovato |
|---|---|---|
| 1 | confronta `codice_interno` con la colonna che porta il `codice` | voi, §1 |
| 2 | legge **solo** `vw_indirizzi_resolved_ruolo`, che per costruzione contiene il **solo layer RUOLO** (`WHERE scope = 'RUOLO'`) | emerso qui |

È il **secondo** a spiegare la sede vuota: il ruolo `EF` non ha indirizzi, ma la
query non guarda dove l'indirizzo effettivamente sta. E il difetto 2 vale
**identico sulla riga del cliente**, che legge la stessa vista: è la stessa
famiglia di C-14a del piano DB, dove un cliente con l'indirizzo sul solo layer
SOGGETTO farebbe fallire la fattura pur avendone uno.

**Non chiede lavoro nuovo, anzi ne toglie.** L'emittente non è un caso speciale:
è la stessa catena del cliente, e la catena esiste già —
`script.fn_resolve_indirizzo_documento(p_soggetto_ruolo_id, NULL, 'SEDELEG')`.
`fn_snapshot_intestazione_fattura` la chiamerà così, senza una riga di logica
propria; e la vostra §5, che toglie del tutto la subquery su
`vw_indirizzi_resolved_ruolo` leggendo lo snapshot, chiude **entrambi** i
difetti in un colpo. È la terza volta che «una sola implementazione della
catena» (C-14b) si ripaga.

**Due conseguenze sul seed che chiedete:**

1. **niente `obbligatorio = true`.** Verificato: quel flag ha i denti —
   `trgfn_soggetti_ruoli_guard_indirizzi_required` solleva
   `E_INDIRIZZO_OBBLIGATORIO_MANCANTE`. Con zero indirizzi sugli emittenti,
   marcare `SEDELEG` obbligatorio romperebbe ogni emittente esistente al primo
   aggiornamento. E lo farebbe **a torto due volte**: quel guard pretende
   l'indirizzo **sul ruolo**, mentre il modello accetta come valido quello del
   **soggetto** — il suo unico fallback è verso un altro *tipo*
   (`fallback_tipo_indirizzo_id`), non verso l'altro *layer*. L'obbligo «la
   fattura deve avere la sede dell'emittente» appartiene al **documento**
   (guard 2.5 allargato, §3.5), dove la catena a due layer è già quella giusta;
2. **la lista va completa alla prima riga.** Seedare la matrice non aggiunge un
   permesso: **sostituisce l'assenza di regole con una regola**, e da quel
   momento tutto ciò che non è elencato è vietato. Decisi con Tid:
   `SEDELEG`, `DOMFISC`, `SEDEOP`, `POSTA`, `RES`. `SEDEOP` perché il «luogo
   fisico» di una società è la sede operativa e non la residenza; `RES` perché
   un emittente può essere una **ditta individuale o un professionista**, e la
   matrice è per ruolo, non per tipo di soggetto. `SPED` resta fuori: è un fatto
   logistico, e aggiungere un tipo dopo è banale mentre toglierlo non lo è.

### 10.4 🟠 RILIEVO — `cliente_snapshot` e il billing account **padre**

Fra le chiavi proposte ci sono `billing_account_id` e `ba_codice`. Su una
fattura con gerarchia quello è il BA **padre**, non il conto del cliente che ha
consumato: lo stabilisce **D-P** (piano DB §2), ed è la stessa ragione per cui
`fn_snapshot_indirizzi_fattura` risolve gli indirizzi dal BA di testata senza
conoscere la gerarchia. Va scritto nel brief, altrimenti fra sei mesi qualcuno
leggerà quello snapshot come «il conto del cliente» e sarà il conto di un altro.

### 10.5 Una regola che abbiamo ormai incontrato due volte

`fatture_indirizzi` è la collezione degli indirizzi **del cliente**, non «gli
indirizzi della fattura». L'abbiamo dedotto due volte dallo stesso vincolo,
`uq_fatture_indirizzi_uno_per_tipo_`: la prima decidendo dove **non** può stare
il sotto-dettaglio per figlio delle fatture utilities (D-P), la seconda nella
vostra §3.2. Vale la pena scriverla come regola invece di riscoprirla una terza
volta — ed è anche l'argomento più forte della vostra §3.2, più della
leggibilità: con quella `UNIQUE` è **impossibile** avere insieme la sede legale
dell'emittente e quella di un cliente persona giuridica.

### 10.6 Confermato senza riserve

- **§3.2** intestazione in testata e non nel satellite;
- **§3.4** stessa protezione di congelamento sulle due colonne nuove: un
  satellite blindato e una testata aperta sarebbe una porta di servizio;
- **§3.5** allargamento del criterio di 2.5, e il tempismo è fortunato — 2.5
  non è ancora scritta, quindi nasce già completa invece di essere riaperta;
- **§7** l'armamento 2.3 parte 2 non cambia rotta: è stato **scritto e
  applicato** il 2026-07-31, dopo la vostra Fase 1.

### 10.7 Una nota sul vostro smoke, per non perderla

`smoke-fattura-indirizzi-snapshot.py` è verde ma chiama
`run_snapshot_indirizzi_lotto_task` **direttamente** — lo dichiarate voi in
testa al file, e non potevate fare altrimenti: l'armamento era nostro. Ora c'è.
Quello smoke va **rieseguito** passando dalla pipeline: oggi è dimostrata la
catena wrapper → funzione DB → ciclo D-Q, **non** che la pipeline invochi quel
wrapper. È la classe di difetto che il vostro §1 cita due volte come motivo di
esistere degli smoke, e il rischio è che nessuno lo rifaccia proprio perché
«era già verde».

### 10.8 Consegna — cosa c'è già, e la riga che dovete cambiare (2026-07-31)

**Applicato e verde** lo stesso giorno del brief. Tre changeSet:

| # | Cosa | changeSet |
|---|---|---|
| I.1 | `vendite.fatture.emittente_snapshot` e `cliente_snapshot` (`jsonb`, NULLable) + guard di congelamento | `20260731-05` |
| I.2 | `vendite.fn_snapshot_intestazione_fattura(p_fattura_id)` → `(scritta boolean)` | `20260731-06` |
| I.3 | wrapper rinominato in `vendite.fn_snapshot_fattura_lotto`, che chiama le due sorelle | `20260731-07` |

Il guard di §3.4 non è una funzione nuova: è il parametrico dei satelliti montato
con `TG_ARGV = 'id'` e `BEFORE UPDATE OF emittente_snapshot, cliente_snapshot`.
La testata è protetta esattamente come `fatture_indirizzi`.

#### 🔴 La riga che dovete cambiare

Il wrapper si chiama `fn_snapshot_fattura_lotto`: dal momento in cui scrive
anche l'intestazione, il nome vecchio diceva metà della verità (precedente
D-L). Due punti in `db/pipeline_repository.py`:

1. il valore in `ALLOWED_TASK_FUNCTIONS` (`:176`);
2. il nome nella query di `run_snapshot_indirizzi_lotto_task` (`:1523`).

**Il `task_code` resta `snapshot_indirizzi_lotto`**: seed, handler, policy e
registry non si muovono. E i contatori li selezionate **per nome**, quindi il
sesto — `intestazioni_scritte` — non vi tocca finché non vorrete leggerlo.
Fra l'apply e la vostra riga, il task non gira.

#### Lo shape, che è ciò contro cui scriverete `_shape_emittente`

⚠️ **Diverso dal vostro §3.1 su due chiavi**, e per una ragione di merito:
**gli id sono provenienza, non contenuto**. Uno snapshot che porta solo
`forma_giuridica_id` non è uno snapshot — se domani cambia la descrizione di
quella forma giuridica, la ristampa cambia di nuovo: è il difetto che stiamo
chiudendo, spostato di una tabella. Quindi di ogni entità referenziata si
congela il **valore** e si tiene l'id **accanto**. È la stessa coppia già in uso
sugli indirizzi (`snapshot` + `origine_indirizzo_id`).

```jsonc
// emittente_snapshot
{
  "soggetto_ruolo_id": 12, "soggetto_id": "…uuid…",
  "denominazione": "…", "codice_fiscale": "…", "id_fiscale": "…",
  "emittente_fiscale_id": 32, "emittente_codice": "…",
  "regime_fiscale_rf": "RF01",
  "capitale_sociale": 10000.00,
  "socio_unico": "SU", "liquidazione": "LN",
  "rea":             { "numero": "…", "provincia": "AV", "provincia_id": 7 },
  "forma_giuridica": { "id": 3, "codice": "SRL", "descrizione": "…" },
  "sede":            { "intestazione": "…", "via": "…", "cap": "…",
                       "citta": "…", "prov": "AV", "stato": "IT",
                       "display": "…" }
}

// cliente_snapshot
{
  "soggetto_ruolo_id": 45, "soggetto_id": "…uuid…",
  "denominazione": "…", "codice_fiscale": "…", "id_fiscale": "…",
  "billing_account_id": 9, "ba_codice": "…",
  "codice_sdi": "…", "pec_fatturazione": "…", "destinatario_fe": "…"
}
```

`jsonb_strip_nulls` è applicato: **le chiavi assenti non compaiono**, non
compaiono valorizzate a `null`. Lo shape resta **non contrattuale** finché il
builder XML FatturaPA non esiste (§10.2).

⚠️ `cliente_snapshot.billing_account_id` è il BA di **testata**, che in
gerarchia è il **padre** (D-P) — non il conto del figlio che ha consumato.
E l'indirizzo di fatturazione **non è qui**: sta in `fatture_indirizzi` (§10.5).

#### Due cose emerse strada facendo, che vi riguardano

**Un terzo campo a larghezza fissa.** `dati_societari.destinatario_fe` è un
`character`, come `province.sigla`. Nello snapshot è già ripulito; segnalatelo
se lo leggete live da qualche altra parte.

**Il ritiro delle segnalazioni ora filtra su `meta->>'task'`, non su `source`.**
Il source è il nome della funzione, e le funzioni si rinominano — è appena
successo con il wrapper. Con il filtro vecchio, dopo ogni rinomina il task non
riconoscerebbe più le proprie bandiere e smetterebbe di abbassarle, lasciando
fatture in ERRORE per problemi già risolti. Il `task_code` è l'identità stabile
del passo. La vostra `disattiva_segnalazioni_lotto_be` non è toccata (filtra su
`scope` e su un nome di tabella, entrambi stabili), ma il criterio vale anche
per voi: **filtrare sull'identità del passo, mai sul nome di ciò che lo esegue.**

#### Cosa resta a noi

Il guard **2.5 col criterio allargato** (§3.5) — **consegnato lo stesso giorno,
§10.9** — la copertura pgTAP dell'intestazione — **§10.10** — e il seed della
matrice `EF` (§3.6, non urgente: la sede si risolve già dal layer SOGGETTO). Da
qui in avanti la vostra Fase 2 non è più bloccata: la forma è quella qui sopra e
non cambierà sotto di voi.

---

### 10.9 Consegna — il guard §3.5, e **il codice errore non è quello annunciato**

**Applicato e verde** il 2026-07-31, subito dopo I.1-I.3. Due changeSet:

| # | Cosa | changeSet |
|---|---|---|
| I.4 | `vendite.trgfn_fatture_guard_uscita_draft` | `20260731-11` |
| I.4 | montaggio su `vendite.fatture`, `BEFORE UPDATE OF stato_doc_fiscale_id` | `20260731-12` |

pgTAP nuovo `db/pgtap/vendite/test-fattura-guard-uscita-draft-v1.sql`, `plan(11)`
verde; due pgTAP verdi preesistenti adeguati perché attraversano la soglia con
fatture nude (`test-guard-lotto-fatture-stato-coerente.sql`,
`test-fatture-righe-importo-e-kit-v1.sql`).

#### 🔴 La riga che dovete cambiare, la seconda

Il guard **non** solleva `E_INDIRIZZO_DOC_OBBLIGATORIO`, che è ciò che il brief
fratello annunciava (`brief-db-snapshot-indirizzi-fattura.md` §5.3, scritto
quando il criterio era ancora il solo indirizzo). Solleva un codice suo:

```
E_FATTURA_NON_EMETTIBILE_INCOMPLETA   (id 575, seed CSV)
"Fattura %s non emettibile: %s."
```

dove il secondo `%s` è il riassunto di cosa manca — per esempio
`indirizzi obbligatori mancanti: FATT; intestazione non congelata:
emittente_snapshot, cliente_snapshot`. Il payload strutturato porta le due liste
separate (`indirizzi_mancanti`, `intestazione_mancante`) più `stato_da` /
`stato_a`.

**Perché un codice nuovo e non quello del DDT.** `E_INDIRIZZO_DOC_OBBLIGATORIO`
descrive un'assenza di **indirizzi**, ed è corretto per il DDT. Qui il criterio è
allargato: usarlo per segnalare che manca `cliente_snapshot` direbbe una cosa
falsa, non solo imprecisa — e manderebbe l'operatore a cercare un indirizzo che
c'è. Un codice solo e non due perché **chi lo riceve fa la stessa cosa in
entrambi i casi** (rieseguire lo step DRAFT): la distinzione serve alla
diagnosi, che sta nel messaggio e nel payload, non al ramo di codice. È lo stesso
criterio della deviazione già presa su `E_FATTURA_SATELLITE_CONGELATO`.

Da registrare in `error_policies.py`. Categoria: è un **409** (`_INCOMPLETA` non
è nella tabella dei suffissi di `api.md` — decidetelo voi, ma il caso è «lo
stato attuale della risorsa non consente l'azione», non un input malformato).

#### Quattro scelte di montaggio che vi riguardano

1. **Presidia l'uscita dalla bozza, non ogni avanzamento.** Esce in testa se lo
   stato di partenza non è `DRAFT`. Oltre quella soglia il presidio è del guard
   di congelamento: allargarlo darebbe una seconda occasione di fallire su un
   documento già emesso.
2. **Solo `UPDATE`, non `INSERT`.** L'unico creatore applicativo,
   `fn_get_or_create_fattura_header`, inserisce **sempre** in `DRAFT`: la porta è
   chiusa a monte per costruzione, non da questo trigger.
3. **Nessun bypass GUC**, a differenza dei guard di congelamento della famiglia.
   `zeroerp.maintenance_reset_lotto_draft` serve al reset lotto, che *rientra*
   nella bozza invece di uscirne — un bypass qui sarebbe una porta di servizio
   sull'emissione in cambio di nulla.
4. **Il nome ordina dopo `guard_stato`.** Una transizione non ammessa dalla
   matrice deve essere respinta *come transizione illegale*, non come «documento
   incompleto». Il test 11 del pgTAP presidia esattamente quell'ordine.

#### Due cose per la vostra §6

L'asserzione **14** («una fattura senza intestazione congelata non lascia
DRAFT») è ora presidiata anche a livello DB dal pgTAP: il vostro smoke la
verifica **attraverso la pipeline**, che è il pezzo che a noi manca.

Nel comporre le fixture dello smoke, tenete conto che d'ora in poi **qualunque**
percorso che porta una fattura fuori dalla bozza pretende il documento completo —
compresi gli script di appoggio che oggi muovono lo stato con un `UPDATE`
diretto. Ce ne sono già due fra i nostri pgTAP, ed è il motivo per cui li abbiamo
adeguati nello stesso giro invece di scoprirlo alla prossima esecuzione.

---

### 10.10 Consegna — la copertura pgTAP, e la prova che la sede viene dal soggetto

**Verde il 2026-08-01**: `db/pgtap/vendite/test-snapshot-intestazione-fattura-v1.sql`,
`plan(12)`, su `vendite.fn_snapshot_intestazione_fattura` e sul guard di
congelamento della testata (§3.4). Con questo il cantiere intestazione è chiuso
salvo il seed della matrice `EF`, che resta non urgente — e ora sappiamo
*misuratamente* perché.

**Perché arriva dopo, e non è un dettaglio di processo.** Le due colonne erano
applicate da I.1-I.3 e avevano già **tre** consumatori — il vostro contesto di
stampa, il guard I.4, il wrapper di lotto — senza che nessun test ne
descrivesse la **forma**. Il wrapper era coperto, la sorella no: è la classe di
buco che sembra chiusa perché qualcosa vicino a lei lo è.

#### La misura che vi riguarda: §10.3 vale su tutta la popolazione

Il rilievo §10.3 diceva «i ruoli `EF` non hanno alcun indirizzo» su un
censimento. Rimisurato il 2026-08-01 sull'intera popolazione degli emittenti
raggiungibili da un billing account:

| | |
|---|---|
| emittenti con sede sul layer **SOGGETTO** | **42 su 42** |
| emittenti con sede sul layer **RUOLO** | **0** |

Non è un campione e non è un caso: è **strutturale**. Ne seguono due cose per
voi. La prima è che la vostra §5 — che toglie del tutto la subquery su
`vw_indirizzi_resolved_ruolo` — non era un miglioramento marginale: quella
vista, per costruzione, non avrebbe **mai** potuto contenere la sede di un
emittente. La seconda è che il seed §3.6 della matrice `EF` non sblocca nulla
che oggi sia bloccato, e resta la cosa a bassa priorità che avevamo detto.

#### Come è scritto il test, per le due cose che potreste voler riusare

**I casi 8 e 9 sono una coppia e vanno letti insieme.** Il 9 verifica che la
sede ci sia e abbia lo shape canonico; da solo passerebbe anche se l'indirizzo
venisse dal layer RUOLO, cioè dal caso banale. È l'**8** a dimostrare che quel
layer è vuoto per l'emittente della fixture, e quindi che l'unica strada
percorribile era il fallback sul SOGGETTO. Un test di fallback che non prova
l'assenza della via principale non prova il fallback.

**Il caso 7 non guarda una colonna, guarda una proprietà**: che *nessun* valore
testuale dello snapshot sia diverso dal proprio `btrim`. Copre così i
`character(n)` di oggi — `province.sigla`, `stati.codice_iso2`,
`dati_societari.destinatario_fe`, quest'ultimo segnalato a voi in §10.8 — **e
quelli che nessuno ha ancora aggiunto**. Se leggete quei campi live da qualche
altra parte, la stessa forma di controllo è riusabile così com'è.

Il **caso 6** presidia l'unica promessa che lo shape fa pur restando non
contrattuale (§10.2): le chiavi assenti **non compaiono**, invece di comparire a
`null`. Il guard I.4 verifica l'intestazione con `jsonb_typeof` proprio perché
si fida di questo.

#### Una cosa che il test ha reso visibile, e che è vostra

Sull'emittente di test lo snapshot **non contiene** `regime_fiscale_rf`, né
`forma_giuridica`; sul cliente mancano `codice_sdi`, `pec_fatturazione` e
`destinatario_fe`. Non è un difetto della funzione — `jsonb_strip_nulls` sta
facendo il suo lavoro su campi anagrafici non valorizzati — ma sono esattamente
le chiavi che il `CedentePrestatore` e l'instradamento SDI della FatturaPA
pretenderanno. Il perimetro §3.1 l'avevamo accolto **completo** proprio per non
rifare il giro dopo (§10.2): vale la pena che quei campi vengano popolati in
anagrafica **prima** che il builder XML esista, altrimenti la prima fattura
elettronica vera scoprirà il buco al posto nostro.
