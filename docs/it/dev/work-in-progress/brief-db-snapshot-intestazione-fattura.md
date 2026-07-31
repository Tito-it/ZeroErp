# Brief DB — snapshot dell'intestazione fiscale della fattura

> **Chi scrive:** BE (`dev/backend-tid`), 2026-07-31.
> **A chi:** team DB (`dev/db-tid`).
> **Cos'è:** **estensione della Fase 2** («ristampa conforme») del piano
> [piano-be-fe-satelliti-fattura.md](piano-be-fe-satelliti-fattura.md). Non è un
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
