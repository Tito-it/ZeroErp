# Brief DB — Le azioni disponibili portano un significato, non un glifo

> **Chi scrive:** sessione backend/frontend (`dev/backend-tid`), 2026-09-27.
> **A chi:** Tid (decisione, §3), poi team DB (§4) e frontend (§5).
> **Origine:** [censimento-icone-per-significato.md](censimento-icone-per-significato.md),
> approvato da Tid il 2026-09-27. Nel frontend ogni icona è ora una costante
> con nome di significato. Il presidio `frontend/src/core/icone.spec.js` fa
> fallire la CI se compare un `'pi pi-...'` scritto a mano.
>
> **In una riga:** le azioni disponibili dei documenti arrivano dal DB con il
> **glifo** già scelto (`'pi pi-...'`). È l'unico punto dell'app in cui il segno
> non passa dalle costanti, e il frontend non può tenerlo coerente.

---

## 1. Il punto di partenza — letto il 2026-09-27

Fatti datati, letti dalla doc `docs/it/dbzero/` e dal codice frontend.

* **Le funzioni `script.fn_available_actions_*`** restituiscono per ogni azione
  un campo `icon`: lotto, ordine, offerta, preventivo, contratto, DDT, reso,
  commessa e documento interno. Il valore arriva:
  * per la maggior parte da `meta->>'icon'` delle matrici di transizione
    (es. `config.stati_doc_fiscale_transizioni.meta`, vedi
    `fn_available_actions_lotto.md:79`);
  * in alcuni casi da letterali scritti nella funzione:
    * `'pi pi-print'`, la ristampa del lotto;
    * `'pi pi-clone'`, `crea_revisione` in offerta e preventivo;
    * i `VALUES` di `fn_available_actions_documento_interno`, per esempio
      `'pi pi-undo'`.
* **Il backend** le passa senza toccarle.
* **Il frontend** le rende così come arrivano: `useDrawerActions.js`,
  `icon: action.icon`.
* ⚠️ **`frontend/src/vendite/composables/useLottoAzioni.js`** (`LOTTO_AZIONE_ICONA`)
  è una **copia a mano** dei valori del DB, e serve al kebab della lista lotti.
  È l'unica eccezione dichiarata nel presidio frontend.

## 2. Perché è un difetto

1. **Lo stesso verbo ha due segni.** Il verbo «numera» del lotto:
   * nella lista lotti porta `MANAGE_ICONS.NUMERA` (`pi-hashtag`, decisione T4
     di Tid);
   * nella barra del drawer e nel kebab porta `pi-verified`, che arriva dal DB.

   Prima del censimento era peggio: nella lista c'era un lucchetto.

   Stesso difetto per `riporta_a_draft`: il DB manda `pi-undo`, cioè
   `MANAGE_ICONS.UNDO` (storna un fatto registrato), mentre il gesto ha già
   la sua costante `MANAGE_ICONS.RIPORTA_A_BOZZA` (`pi-backward`), che il
   frontend usa per l'evento di giornale. Il verbo nel kebab e nel drawer
   porta proprio il segno che la costante esclude. La mappa verbo→icona
   deve coprire anche questo caso.
2. **I glifi del DB non seguono le regole del censimento.** `crea_revisione`
   porta `pi-clone`, che nel frontend è `STATUS_ICONS.MULTIPLI` («più di uno»),
   non «nuova revisione».
3. **Una correzione di segno oggi richiede un changeSet** e non la vede nessun
   test: né il lint né il presidio frontend guardano i dati.

## 3. Decisione per Tid

**D-1 — Che cosa manda il DB al posto del glifo.**

| Opzione | Come funziona | Pro | Contro |
| --- | --- | --- | --- |
| **A (proposta)** | Il DB **non manda l'icona**. Il frontend la ricava dal `codice` dell'azione con una mappa `verbo → MANAGE_ICONS.*` in `core/`. Un verbo senza voce prende un ripiego visibile | Il verbo **è** già il significato: nessun secondo nome da tenere allineato. La presentazione esce dal DB. Il presidio frontend copre tutto | Un verbo nuovo a DB vuole la sua riga nella mappa frontend (altrimenti mostra il ripiego) |
| B | Il DB manda una **chiave di significato** (`'icona': 'NUMERA'`), che il frontend risolve in `MANAGE_ICONS` | Configurabile da DB senza deploy frontend | Due vocabolari da tenere allineati (chiavi DB e costanti frontend). Una chiave sbagliata dà un'icona vuota, senza errore |

Con A, un test frontend può fissare che ogni verbo noto abbia la sua voce.

> ✅ **Decisioni di Tid, 2026-09-27** (sui punti del §6):
>
> * **opzione A**: la mappa è `verbo → icona`, **un segno per verbo** in
>   tutti i domini;
> * **`emetti` = `pi-send`** ovunque, DDT compreso;
> * **`riapri` e `riporta_a_draft` = stesso segno** (`RIPORTA_A_BOZZA`);
> * **`severity` resta a DB**, nel `meta`, insieme a `label_key` (§6.4).

## 4. Richiesta al team DB (dopo D-1)

**Con A:**

1. Togliere `icon` dall'output delle `fn_available_actions_*` e i letterali
   `'pi pi-...'` dalle funzioni.
2. Togliere `icon` da `meta` delle matrici di transizione. Prima va fatto
   l'**inventario completo** dei valori seedati (la doc `dbzero` non li riporta
   tutti), da consegnare al frontend: è la base della mappa.
3. Aggiornare la doc delle funzioni e i pgTAP che verificano `icon`.

**Con B:** stessi punti, ma `icon` diventa `icona_chiave` con valori presi da
`MANAGE_ICONS`. L'elenco delle chiavi valide va dato dal frontend.

## 5. Ricaduta sul frontend (dopo il DB)

* **Mappa `verbo → icona`** in `core/`, per opzione A, e `useDrawerActions` che
  la legge.
* **`LOTTO_AZIONE_ICONA`** in `useLottoAzioni.js` si ritira: legge la stessa
  mappa.
* **Presidio:** si toglie l'eccezione in `icone.spec.js`.

⛔ Fino ad allora il frontend **non** cambia `LOTTO_AZIONE_ICONA` da solo:
separerebbe il kebab della lista dalla barra del drawer.

---

## 6. Verifica del team DB — 2026-09-27

Letta la doc auto-gen `docs/it/dbzero/script/funzioni/`, i CSV di seed in
`80_data` e i `COMMENT` dei changelog. **I fatti di §1 e §2 reggono**, con
tre correzioni e un inventario che il §4.2 chiedeva.

### 6.1 Correzioni a §1

* **Il campo dell'azione è `key`**, non `codice` (§3, opzione A). Nelle matrici
  è `meta->>'action_key'`, nei letterali `'key'`.
* **I letterali nelle funzioni sono più di quelli citati.** Elenco completo:

  | Funzione | `key` | Glifo |
  | --- | --- | --- |
  | `fn_available_actions_lotto` | `ristampa` | `pi-print` |
  | `fn_available_actions_offerta`, `_preventivo` | `crea_revisione` | `pi-clone` |
  | `fn_available_actions_offerta` | `push_contratto` | `pi-arrow-right` |
  | `fn_available_actions_preventivo`, `_ordine`, `_ddt` | `push_commessa` | `pi-arrow-right` |
  | `fn_available_actions_offerta`, `_preventivo` | `genera_ordine` | `pi-shopping-cart` |
  | `fn_available_actions_documento_interno` (`VALUES`) | `conferma` / `riapri` / `annulla` | `pi-check` / `pi-undo` / `pi-times` |

  `fn_available_actions_inventario` e `_rettifica` sono involucri di
  `_documento_interno`: non hanno glifi propri.
* **Nessun'altra sede a DB manda glifi.** Cercato `pi-` in tutta la doc
  auto-gen e nei CSV di seed: fuori dalle funzioni sopra e dalle otto matrici
  sotto non c'è niente (le liste `ui.*` non portano icone).

### 6.2 Inventario dei glifi seedati nelle matrici (§4.2)

Letto dai CSV, che sono la sorgente del seed. Otto matrici:
`config.stati_doc_fiscale_transizioni` (lotto), `config.transizioni_stati_ordini`,
`_ddt`, `_reso`, `_contratti`, `_preventivi`, `config.stati_doc_offerte_transizioni`,
`vendite.transizioni_stati_commessa`.

| `key` | Glifo | Dove |
| --- | --- | --- |
| `annulla` | `pi-times-circle` | tutte e otto |
| `accetta` | `pi-check` | preventivi, offerte |
| `conferma` | `pi-check` | ordini, reso |
| `emetti` | ⚠️ `pi-check` nel DDT, `pi-send` in preventivi e offerte | |
| `spedisci` | `pi-send` | DDT |
| `consegna` | `pi-check-circle` | DDT |
| `reso` | `pi-replay` | DDT (riga `attivo = f`) |
| `rifiuta` | `pi-ban` | preventivi, offerte |
| `attiva` / `cessa` | `pi-play` / `pi-stop` | contratti |
| `rendi_pronta` | `pi-check-circle` | commessa |
| `chiudi` | `pi-lock` | commessa |
| `riapri` | `pi-undo` | commessa (e documento interno, letterale) |
| `numera` | `pi-verified` | lotto |
| `riporta_a_draft` | `pi-undo` | lotto |

⭐ Il verbo come chiave **non è ambiguo**: nessuna `key` ha due significati
diversi fra le matrici. Due punti restavano per la mappa del frontend —
✅ **decisi da Tid il 2026-09-27** (riquadro in §3): `emetti` = `pi-send`
ovunque; `riapri` e `riporta_a_draft` stesso segno.

* **`emetti` ha già due segni oggi** (DDT contro preventivo/offerta): è un
  secondo caso dello stesso difetto di §2.1, che l'opzione A chiude da sé. Se
  invece Tid volesse segni diversi per dominio, la mappa diventa
  `(dominio, verbo) → icona`: va detto prima di scriverla;
* **`riapri` e `riporta_a_draft`** portano lo stesso `pi-undo`. `riapri`
  della commessa va da `PRONTA_FATTURAZIONE` a `IN_ESECUZIONE` (non a
  bozza), quello del documento interno torna a `DRAFT`: la mappa deve decidere se sono lo stesso gesto di
  `RIPORTA_A_BOZZA` o no.

### 6.3 Che cosa tocca a DB, in aggiunta a §4 (con A)

* **I `COMMENT ON COLUMN meta`** di sei matrici nominano `icon` fra i
  metadati UI (`transizioni_stati_reso`, `stati_doc_offerte_transizioni`,
  `transizioni_stati_contratti`, `_ordini`, `_ddt`,
  `vendite.transizioni_stati_commessa`), e il `COMMENT` di
  `fn_available_actions_documento_interno` elenca `icon` fra le chiavi: vanno
  riscritti nello stesso giro.
* **`icon` esce da `meta` dal CSV**, non con un `UPDATE` (linee-guida-sql
  §11.2): otto CSV di `80_data`.
* **pgTAP che fissano il glifo:**
  `db/pgtap/script/test-capability-annulla-aspetto-e-stato-leggibile-v1.sql`
  (righe 132 e 284, `pi-times-circle` su matrice **e** su output). Va riscritto
  per asserire l'**assenza** di `icon`, altrimenti resta un test che pinna il
  vecchio contratto.
* **Ricaduta BE da segnalare** (non la tocca il DB): tre test Django nominano
  `icon` — `magazzino/tests/db/test_documento_interno_db.py:420` (elenco delle
  chiavi dell'output: con A fallisce) e due fixture in
  `vendite/tests/services/test_contratti_service.py:166` e
  `test_preventivi_service.py:1790` (dati finti, non falliscono ma restano
  stantii).

### 6.4 Una domanda che il brief non pone

Con A l'icona esce dal DB, ma **`label_key` e `severity` restano nel `meta`**.
`label_key` ha già la forma dell'opzione B (una chiave che il frontend
risolve); `severity` è presentazione quanto l'icona. Non è un'obiezione ad A —
il verbo basta a dare l'icona, non basta a dare l'etichetta, che cambia per
documento — ma conviene che D-1 dica esplicitamente che **`severity` resta a
DB**, così la stessa domanda non riapre il cantiere fra un mese.

✅ **Deciso da Tid il 2026-09-27: `severity` resta a DB.**

## 7. Consegna DB — 2026-09-27 ✅ applicata, test verdi

> ✅ **Applicata su dbdev da Tid il 2026-09-27 alle 11:09**: `20260927-09` e
> `-10` → `-18` tutti `EXECUTED` nel `databasechangelog`, mirror dei CSV
> ripartiti. Letto dopo l'apply: zero funzioni `script.fn_available_actions_*`
> con `'icon'` o `pi pi-` nel corpo, zero righe con `icon` nel `meta` delle
> matrici. **pgTAP verdi, nessuna regressione** (corsa di Tid).
>
> **Il lato DB è chiuso.** Restano aperte le richieste del §7.3 al BE e al FE:
> la mappa `verbo → icona`, il test Django del documento interno, le pagine
> API. Finché la mappa non è a video, i pulsanti del drawer non hanno icona.

### 7.1 Che cosa c'è

| File | Che cosa fa |
| --- | --- |
| `00_schema/config/20260927-09-comment-meta-transizioni-senza-icona` | `COMMENT` di `meta` sulle sei matrici che nominavano `icon`: testo vivo senza `icon` + una frase su chi sceglie il segno |
| `20_code/script/20260927-10` → `-18` `update-fn-available-actions-<dominio>-senza-icona` | le nove funzioni (lotto, offerta, preventivo, ordine, ddt, reso, commessa, contratto, documento interno) senza `'icon'`: tolte le righe dal `jsonb_build_object` e, nel documento interno, la colonna `icon` della tabella di valori. `COMMENT` vivo + una riga `rev 2026-09-27`; in `documento_interno` tolto `icon` dall'elenco delle chiavi |
| otto CSV di `80_data` | tolta la chiave `icon` da `meta`: 39 righe, nessun'altra modifica. I mirror (`runOnChange` + `ANY`) si risvegliano da soli al migrate: nessun changeSet nuovo in `80_data` (§11.2) |
| `db/pgtap/script/test-capability-annulla-aspetto-e-stato-leggibile-v1.sql` | test 1 e 4 non pretendono più `pi-times-circle`; il 4 ora asserisce che **nessuna** azione emessa porta la chiave `icon`. Nuovi 9 (nessuna riga delle 8 matrici ha `icon` nel meta) e 10 (nessuna `script.fn_available_actions_*` nomina `'icon'` o `pi pi-` nel corpo: non dipende dai dati). `plan(10)` |
| pagine `dbzero/*/manual` (8 matrici/tabelle, 8 funzioni, `vendite/manual/ddt.md`), `guide/gestione-offerte-commerciali.md` | tolto `icon` dai contratti descritti, con la frase «l'icona la sceglie il frontend dal `key`» |

Firme invariate (nomi e tipi risolti uguali al vivo, nessun overload); la
dichiarazione è **ancorata** (`%TYPE`, `SECURITY INVOKER` esplicito) anche
dove l'ultimo YAML l'aveva persa (lotto, reso). Tutte e nove restano INVOKER,
di proprietà del migratore: nessun prestito di owner.

### 7.2 Prove fatte — su dbdev, in transazione chiusa in `ROLLBACK`

* **CSV ↔ DB**: le otto tabelle coincidono col loro CSV su tutte le colonne
  non di audit (nessun mirror stantìo).
* **Riscrivibilità**: l'upsert di **tutte** le righe dei CSV nuovi passa i
  guard; dopo, zero `icon` e nessun'altra differenza. Unica eccezione, già
  presente e solo di audit: `stati_doc_offerte_transizioni` id 6 ha
  `user_insert = titodb` a DB e `mctit` nel CSV, e il mirror la riscriverà.
* **SQL estratto dagli YAML**: le nove funzioni e i `COMMENT` compilano, nessun
  overload, nessuna `'icon'` nei corpi.
* **Comportamento**: uscita di ogni funzione su **tutti** i documenti di dev
  (539, dieci famiglie compresi inventario e rettifica), prima e dopo:
  identica a meno della chiave `icon` (631 chiavi prima, 0 dopo, 0 differenze).
  ⚠️ È una misura sui dati di dev, dichiarata come tale: prova che il taglio non
  ha toccato altro, non sostituisce il pgTAP.
* **Asserzioni nuove 9 e 10**: rosse sullo stato di oggi (39 righe, 9
  funzioni), verdi dopo le modifiche.
* Guardrail statici: runOnChange, preambolo pgTAP, preCondition/seed, DDL su
  trigger, letterali SQL, timestamp — tutti verdi.

✅ **Apply e corsa pgTAP fatti da Tid il 2026-09-27**: verdi, nessuna
regressione. Nota: il file resta nelle baseline dei rossi CI (`ASSERZIONE`)
per il test 8 (DB vuoto, anti-vacuità); la modifica non cambia questa
condizione.

### 7.3 Richieste al BE e al FE

* ⛔ **Ordine di rilascio.** Dal momento dell'apply `useDrawerActions` riceve
  `action.icon = undefined`: i pulsanti del drawer restano **senza icona**
  finché la mappa `verbo → icona` (§5) non è a video. Il kebab dei lotti no
  (`ui?.icon ?? LOTTO_AZIONE_ICONA[key]`). Meglio che le due cose vadano a
  `Tito-dev` **nello stesso merge**.
* **Mappa del frontend**: i verbi sono quelli di §6.1 e §6.2 (15 dalle matrici,
  più `ristampa`, `crea_revisione`, `push_commessa`, `push_contratto`,
  `genera_ordine`), con le decisioni del riquadro in §3.
* **Test Django**: `magazzino/tests/db/test_documento_interno_db.py:420`
  elenca `icon` fra le chiavi dell'output — **fallirà**. Le fixture di
  `vendite/tests/services/test_contratti_service.py:166` e
  `test_preventivi_service.py:1790` non falliscono, ma portano un campo che
  il DB non manda più.
* **Pagine API** (`docs/it/backend/`) che descrivono `icon` nell'output:
  `vendite/manual/api_ordini.md:127`, `api_commessa_stato.md:71,73,121`,
  `api_preventivi.md:142`, `api_offerte.md:342,348`,
  `magazzino/manual/api_magazzino.md:111`.

## 8. Consegna BE/FE — 2026-09-27

Chiude §5 e §7.3. Da portare a `Tito-dev` **insieme** alla consegna DB (§7.3).

* **Mappa `verbo → icona`**: `frontend/src/core/aspettoAzioni.js`
  (`ASPETTO_AZIONE`, `aspettoAzione(key)`; dal §9 porta anche il colore). Tutte le icone sono costanti
  `MANAGE_ICONS`. Se il verbo non è in mappa, l'icona è `RIPIEGO` =
  `CAMBIO_STATO`. La leggono `useDrawerActions`, `useLottoAzioni` (ritirato
  `LOTTO_AZIONE_ICONA`) e la conferma di `DocumentoInternoDrawer`.
  `aspettoAzioni.spec.js` fissa i 20 verbi di §6.1/§6.2 e le decisioni di §3.
  Dal presidio `icone.spec.js` è tolta l'eccezione.
* **Costanti nuove**: `SPEDISCI`, `CONSEGNA`, `RENDI_PRONTA`, `NUOVA_REVISIONE`,
  `INVIA_A_COMMESSA`.

  | `key` | Costante | Glifo | Prima (DB) |
  | --- | --- | --- | --- |
  | `annulla` | `ANNULLA` | `pi-times-circle` | uguale (`pi-times` nel documento interno) |
  | `conferma` | `CONFIRM` | `pi-check` | uguale |
  | `accetta` / `rifiuta` | `APPROVE` / `REJECT` | `pi-check` / `pi-times` | `pi-ban` era `DISATTIVA` |
  | `emetti` | `SEND` | `pi-send` | D-1 (il DDT aveva `pi-check`) |
  | `spedisci` | `SPEDISCI` | `pi-truck` | `pi-send`: sarebbe coinciso con `emetti` nel DDT |
  | `consegna` | `CONSEGNA` | `pi-flag-fill` | `pi-check-circle` era `PUBLISH`/`OK` |
  | `reso` | `CORREZIONE` | `pi-replay` | uguale |
  | `attiva` / `cessa` | `PLAY` / `CLOSE_DATE` | `pi-play` / `pi-calendar-times` | `pi-stop` era `STATUS_ICONS.NO` |
  | `rendi_pronta` | `RENDI_PRONTA` | `pi-thumbs-up` | `pi-check-circle` |
  | `chiudi` | `CLOSE` | `pi-lock` | uguale |
  | `riapri`, `riporta_a_draft` | `RIPORTA_A_BOZZA` | `pi-backward` | D-1 (`pi-undo` era `UNDO`) |
  | `numera` / `ristampa` | `NUMERA` / `STAMPA` | `pi-hashtag` / `pi-print` | T4 (`pi-verified`) |
  | `crea_revisione` | `NUOVA_REVISIONE` | `pi-history` (= `VERSIONI`) | `pi-clone` era `MULTIPLI` |
  | `push_commessa` | `INVIA_A_COMMESSA` | composta: `pi-briefcase` + `pi-arrow-circle-right` | `pi-arrow-right`; supera D7 (`SEND`), vedi sotto |
  | `push_contratto`, `genera_ordine` | `GENERA_DOCUMENTO` | `pi-file-export` | `pi-arrow-right`, `pi-shopping-cart` (= `VENDITE`) |

* ✅ **Confermati da Tid il 2026-09-27** i glifi di `SPEDISCI` (`pi-truck`),
  `CONSEGNA` (`pi-flag-fill`), `RENDI_PRONTA` (`pi-thumbs-up`) e
  `NUOVA_REVISIONE` (`pi-history`).
* ✅ **Push a commessa, deciso da Tid il 2026-09-27.** `emetti` (D-1) e
  `push_commessa` (D7) avevano entrambi `SEND`, e nel preventivo stanno nello
  stesso drawer. Il push ora ha un segno suo: `INVIA_A_COMMESSA`, un'icona
  composta in `main.css` (la valigetta della commessa con la freccia verso
  valle). È diversa da `COMMESSA` nuda, che resta «apri la commessa». La portano
  il verbo `push_commessa`, `AZIONE_PUSH_COMMESSA` (pulsante negato di DDT e
  ordine), lo smistamento del preventivo e le attività di pratica
  `INVIO_COMMESSA` e smistamento. `SEND` resta a `emetti` e all'invio dei
  messaggi. Aggiunti i due codepoint alla baseline di
  `check-primeicons-codepoints`.
* **BE**: `test_documento_interno_db.py` non si aspetta più `icon`. È verde con
  `ZEROERP_TEST_DB_E2E=1` sul dbdev. Tolto `icon` anche dalle fixture di
  contratti e preventivi.
* **Pagine API** di §7.3: tolto `icon` dall'output descritto.

## 9. Anche il colore esce dal DB — §6.4 riaperta, 2026-09-28

> **Chi scrive:** sessione backend/frontend (`dev/backend-tid`).
> **A chi:** team DB (§9.3). Il frontend è già consegnato (§9.2).

### 9.1 Decisione di Tid, 2026-09-27

Il §6.4 aveva lasciato `severity` a DB. Tid lo riapre: **il colore del
pulsante segue la stessa regola dell'icona**. Il verbo lo decide, uguale in
tutti i domini, e il frontend lo ricava dal `key`.

Il motivo è sul modello. `severity` è presentazione quanto l'icona (lo diceva
già il §6.4). E leggendo il contratto (CSV di `80_data` e corpi delle
funzioni, 2026-09-27) lo stesso verbo porta colori diversi, cioè lo stesso
difetto del §2.1:

| `key` | Oggi a DB | Decisione |
| --- | --- | --- |
| `conferma` | `info` negli ordini; `success` nei resi e nel documento interno | ✅ Tid: **`info`** |
| `riapri` / `riporta_a_draft` | `info` in commessa, `secondary` nel documento interno, `warn` nel lotto | ✅ Tid: **`warn`**, tutti e due |
| `push_commessa` | `info` nel preventivo; `success` in ordine e DDT | ✅ Tid: **`success`**, anche il colore del pulsante negato `AZIONE_PUSH_COMMESSA` |

Per gli altri verbi il frontend conserva il colore che il DB già usava,
perché è uno solo.

**Restano a DB** `label_key`, che cambia per documento, e `outlined`, che
cambia per **stato** (l'annulla di una bozza è solo bordato) e non per verbo.

### 9.2 Consegna frontend — 2026-09-28

* `core/iconeAzioni.js` diventa **`core/aspettoAzioni.js`**:
  `ASPETTO_AZIONE = { verbo: { icona, severity } }` e `aspettoAzione(key)`.
  Per un verbo sconosciuto vale `RIPIEGO` = `CAMBIO_STATO` + `secondary`.
* La leggono `useDrawerActions`, il kebab dei lotti e la conferma del
  documento interno (`danger`). Legge la mappa anche `AZIONE_PUSH_COMMESSA`,
  che prima teneva a mano icona e colore.
* **Ritirata `LOTTO_AZIONE_SEVERITY`**, l'ultima copia a mano del seed nel
  frontend.
* Il frontend **ignora già** il `severity` che il DB manda: un test lo fissa
  (`useDrawerActions.spec.js` 1b). ⭐ Quindi, a differenza dell'icona,
  **l'ordine di rilascio è libero**: il pulsante non cambia aspetto né prima
  né dopo il changeSet DB.

### 9.3 Richiesta al team DB

> ✅ **Consegnata e applicata il 2026-09-28, test verdi**: §10. Resta la
> ricaduta BE del §10.4.

Stesso perimetro del §4 e del §6.3, con `severity` al posto di `icon`:

1. Togliere `severity` dall'output delle nove `fn_available_actions_*`. Oggi
   è scritta come letterale per `ristampa`, `crea_revisione`,
   `push_commessa`, `push_contratto`, `genera_ordine` e nei `VALUES` del
   documento interno.
2. Togliere `severity` da `meta` nelle otto matrici, **dal CSV**
   (linee-guida-sql §11.2).
3. Riscrivere i `COMMENT` che la nominano (le sei matrici del §6.3 e
   `fn_available_actions_documento_interno`).
4. pgTAP: `test-capability-annulla-aspetto-e-stato-leggibile-v1.sql` asserisce
   `severity = danger` sull'annulla (riga 155 e il test 1). Va riscritto come
   per `icon` (§7.1): asserire l'**assenza**, e tenere `outlined`, che resta un
   dato. Da censire gli altri pgTAP che leggono `severity` dalle azioni.
   ⚠️ `test-riporta-lotto-a-draft-v1.sql:303` legge la `severity` di un
   **evento**, non di un'azione: non c'entra.
5. Doc `dbzero` delle funzioni e delle matrici.

**Ricaduta BE, dopo il DB** (la fa la sessione BE):
`magazzino/tests/db/test_documento_interno_db.py:420` elenca `severity` fra le
chiavi dell'output, e fallirà. Le fixture di contratti e preventivi portano un
campo stantio. Le pagine API di §7.3 descrivono `severity` nell'output.

## 10. Consegna DB del §9 — 2026-09-28 ✅ applicata, test verdi

> ✅ **Applicata su dbdev da Tid il 2026-09-28 alle 00:23**: `20260928-06` e
> `-07` → `-15` tutti `EXECUTED` nel `databasechangelog`, e i nove mirror dei
> CSV delle otto matrici ripartiti (`RERAN`; per i preventivi sono due). Letto
> dopo l'apply: zero `script.fn_available_actions_*` con `severity` nel corpo,
> zero righe con `severity` nel `meta` delle matrici, nessun overload.
> **pgTAP verdi, nessuna regressione** (corsa di Tid).
>
> **Il lato DB è chiuso.** Resta aperta la ricaduta BE del §10.4: il test Django
> del documento interno (che ora fallisce), la fixture dei contratti, un
> commento in `types.py` e quattro pagine API. L'ordine di rilascio era libero
> (§9.2): il frontend ignorava già la `severity` del DB, quindi a video non
> cambia niente.

### 10.1 Verifica del §9 — fatti che reggono, due precisazioni

Letti i CSV di `80_data`, i corpi e i `COMMENT` in vigore (dbdev, 2026-09-28)
e `core/aspettoAzioni.js`. **Il §9 regge**: i tre conflitti di §9.1 sono quelli,
i letterali di §9.3.1 sono quelli, e per ogni altro verbo il colore del seed è
uno solo e coincide con la mappa del frontend (20 verbi su 20, compresi i tre
decisi da Tid).

* I CHECK `ck_*_meta_ui` pretendono solo `action_key` e `label_key`: togliere
  `severity` non li tocca. Nessun trigger, vista o funzione fuori dalle
  `fn_available_actions_*` legge `meta->>'severity'`.
* pgTAP: la sola asserzione sulla `severity` delle **azioni** è il test 1 di
  `test-capability-annulla-aspetto-e-stato-leggibile-v1.sql` (la riga 155 del
  §9.3.4 è dentro il test 1). Gli altri pgTAP che nominano `severity` parlano
  di `event_log` o del Tag di stato delle liste.
* Ricaduta BE: la fixture con `severity` è solo in
  `test_contratti_service.py:166`; quella dei preventivi non la porta.

### 10.2 Che cosa c'è

| File | Che cosa fa |
| --- | --- |
| `00_schema/config/20260928-06-comment-meta-transizioni-senza-severity` | `COMMENT` di `meta` sulle sei matrici che nominavano `severity`: testo vivo senza `severity`, e la frase sull'icona riscritta per icona **e** colore. `stati_doc_fiscale_transizioni` e `transizioni_stati_preventivi` hanno un COMMENT generico: intatti |
| `20_code/script/20260928-07` → `-15` `update-fn-available-actions-<dominio>-senza-severity` | le nove funzioni (lotto, offerta, preventivo, ordine, ddt, reso, commessa, contratto, documento interno) senza `'severity'`: 18 righe tolte dai `jsonb_build_object` (matrice e letterali) e, nel documento interno, la colonna della tabella di valori. `COMMENT` vivo + riga `rev 2026-09-28`; nel documento interno tolto `severity` dall'elenco delle chiavi |
| otto CSV di `80_data` | tolta la chiave `severity` da `meta`: 39 righe, nessun'altra modifica. I mirror (`runOnChange` + `ANY`) si risvegliano da soli al migrate, come per `icon` (§7.1) |
| `db/pgtap/script/test-capability-annulla-aspetto-e-stato-leggibile-v1.sql` | rev 2026-09-28 in testa. Test 1 solo `outlined`; test 4 e 9 contano la presenza di `icon` **o** `severity` (operatore «any key»), test 10 cerca anche `'severity'` nei corpi. `plan(10)` invariato |
| pagine `dbzero/*/manual`: sette matrici, otto funzioni, `vendite/manual/ddt.md` | tolto `severity` dai contratti descritti; la riga «(icona)» delle tabelle del `meta` diventa «(icona e colore)» |

**Ancoraggio dei tipi.** Corpi presi dal vivo (`prosrc` = corpo degli YAML
`20260927-10` → `-18`, confrontati riga per riga), firme ancorate come allora.
In più: la firma del `COMMENT ON FUNCTION` era `(bigint)` nudo e ora è
`(<tabella>.id%TYPE)` come il parametro. Nel DECLARE una riga dichiara perché i
tipi rimasti espliciti lo sono (valori calcolati: jsonb, flag, chiavi i18n).
Il documento interno resta a tipi espliciti in firma e su `v_stato` /
`v_destinazioni`, perché è **polimorfo**: `p_documento_id` è l'id di
`inventari` **o** di `rettifiche` e `p_famiglia` non ha una colonna-vocabolario.
Il DECLARE ora lo scrive; gli involucri `_inventario` / `_rettifica` sono
ancorati. Tutte e nove restano `SECURITY INVOKER`, di proprietà del migratore.

⚠️ `vendite/manual/transizioni_stati_commessa.md` dice ancora che «tutte le 11
righe hanno `meta = {"manuale": false}`» e che i metadati UI sono «rinviati»: è
stantio da quando esiste `fn_available_actions_commessa`. Qui è tolto solo
`severity`; la riscrittura del paragrafo è un debito documentale a sé.

### 10.3 Prove fatte — dbdev, in transazione chiusa in `ROLLBACK`

* **SQL estratto dagli YAML** (parser, non riscritto): i dieci changeSet
  compilano, compreso il `COMMENT ON FUNCTION` con `%TYPE`. Dopo: una sola
  funzione per nome, firme identiche a prima, zero corpi che nominano
  `severity`, zero `COMMENT` di matrice che la elencano.
* **Comportamento**: uscita delle funzioni su **tutti** i documenti di dev, prima
  e dopo: 539 documenti, dieci famiglie compresi inventario e rettifica.
  Identica a meno della chiave `severity`: 631 chiavi prima, 0 dopo, 0 altre
  differenze. ⚠️ È una misura sui dati di dev, dichiarata come tale: prova che
  il taglio non ha toccato altro, non sostituisce il pgTAP.
* **CSV ↔ DB**: ogni riga degli otto CSV coincide col `meta` a DB tolta la
  `severity` (61 righe, 0 diverse, 0 mancanti); riscrivere il `meta` dal CSV
  passa i guard.
* **Asserzioni toccate**: il 9 conta 39 righe e il 10 nove funzioni sullo stato
  di oggi (rossi), 0 e nessuna dopo (verdi); il 4 va da 631 chiavi a 0. Il test
  1 (solo `outlined`) è verde prima e dopo.
* Guardrail statici: runOnChange, preCondition/seed, DDL su trigger, GRANT
  batch, letterali SQL, timestamp, preambolo pgTAP — tutti verdi.

### 10.4 Richieste al BE (dopo l'apply)

* **Test Django**: `magazzino/tests/db/test_documento_interno_db.py:420`
  elenca `severity` fra le chiavi dell'output: **fallirà**. La fixture di
  `vendite/tests/services/test_contratti_service.py:166` porta un campo che il
  DB non manda più; il commento di `vendite/types.py:1004` lo nomina.
* **Pagine API** che descrivono `severity` nell'output delle azioni:
  `vendite/manual/api_ordini.md:127`, `api_offerte.md:342,348`,
  `api_commessa_stato.md:71,73,121`, `magazzino/manual/api_magazzino.md:111`.
