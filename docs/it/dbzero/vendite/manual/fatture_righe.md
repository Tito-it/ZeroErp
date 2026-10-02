## 📘 Documentazione Concettuale – Tabella `vendite.fatture_righe`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)   
> • [config.iva](/dbzero/config/tabelle/iva)   
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)   
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)   
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  

---
### 🎯 Scopo Principale
(latest review **28-07-2026** — revisione sostanziale, vedi ⚠️ in fondo alla sezione)
`vendite.fatture_righe` contiene le **righe economiche** di una fattura: descrizione, articolo (opzionale), UoM, quantità, prezzo, sconti, IVA e **imponibile congelato** (*snapshot*) al momento della generazione. Ogni riga è ordinata tramite `riga_nr` ed è collegata a una testata `vendite.fatture` (FK `fattura_id`). Supporta la **destinazione a BA diverso** dalla testata.

Obiettivi principali:

* Conservare il **valore definitivo** della riga per garantire riproducibilità documentale nel tempo.
* Essere il **dettaglio** della fattura: una riga rappresenta l'**aggregazione di 1..n attività fatturabili**, che vi puntano tramite `attivita_fatturabili.fattura_riga_id`.
* Permettere **override di IVA e attributi fiscali** (esigibilità, split payment) a livello riga.
* Mantenere riferimenti all’**articolo di catalogo** e all’**unità di misura** utilizzata per il calcolo.

> ⚠️ **Questo manuale è stato corretto il 2026-07-28, e vale la pena sapere perché.**
> La versione precedente descriveva tre colonne di importo (`imponibile_riga`,
> `imposta_riga`, `totale_riga`) con le loro formule, e classificava il trigger
> che avrebbe dovuto calcolarle come *«opzionale»* in una sezione di roadmap.
> Quel trigger non è mai stato scritto, mentre il backend dava per fatto che il
> DB calcolasse gli importi: risultato, **ogni fattura del sistema è rimasta a
> 0,00 € fino al 2026-07-28**. Il documento citava inoltre una colonna
> `iva_perc` che sulla riga non esiste.
> Chi legge questa pagina la usa come specifica: da qui in avanti descrive **cosa
> il database fa**, non cosa potrebbe fare.
> Storia completa: `brief-fix-importi-riga-fattura-zero.md`.

---

### Collocazione nel flusso

1. **Popolamento**: lo fa il **backend**, non il DB — `FattureRigheService.generate_fatture_righe` (`apps/vendite/services/fatture_righe_service.py`), invocato dal task `generate_fatture_righe` della pipeline. **Aggrega** le attività fatturabili del lotto per chiave di raggruppamento — `_build_group_key`: articolo · BA destinatario · UoM · **prezzo unitario** · IVA · competenza · istanza di kit — e produce **una riga per gruppo**. Le *n* attività del gruppo vengono collegate alla riga con `fattura_riga_id`.

    ⚠️ Esisteva una funzione SQL gemella (`vendite.fn_generate_fatture_righe`), **ritirata il 2026-07-28** col changeset `20260728-21`: non era in esercizio dal 2026-02-03, e averla lasciata «per compatibilità storica» è costato una giornata di sviluppo su codice morto. Vedi `brief-db-ritiro-generatore-righe-fattura-sql.md`.

2. **Calcolo dell'importo**: NON lo fa chi scrive la riga. Lo calcola il trigger `trg_fatture_righe_a20_importo_ins_upd` a ogni `INSERT`/`UPDATE` — vedi *Logiche di calcolo*.
3. **Ordinamento**: `riga_nr` progressivo per fattura, assegnato con ordinamento **deterministico** dei gruppi; vincolo unico `(fattura_id, riga_nr)`.
4. **Totali testata**: la somma delle righe alimenta i riepiloghi IVA e da lì `imponibile_tot`, `imposta_tot`, `totale_doc`, `totale_a_pagare`.
5. **Congelamento**: da quando il documento e` **congelato** — `config.stati_doc_fiscale.congela_fiscale`, ⛔ non piu` la lista `DRAFT`/`EMESSA` scritta dentro il guard (rev 2026-08-30, `D33`) — il trigger `trg_fatture_righe_a10_guard_congelamento_ins_upd_dlt` respinge `INSERT`, `UPDATE` **e** `DELETE`. La riga diventa uno snapshot fiscale intoccabile. ⭐ Dal 2026-08-30 quel trigger esegue la guardia **generica** `vendite.trgfn_fattura_satellite_guard_congelamento` (`D34`): nome del trigger, codice errore `E_FATTURA_RIGA_CONGELATA` e bypass GUC **non sono cambiati**.
6. **Normalizzazione**: `trg_fatture_righe_guard_normalize_ins_upd` eredita il BA destinatario dalla testata e allinea lo snapshot `iva_natura`.

---

### Campi chiave (semantica)

* **Identità e collegamenti**: `fattura_id` (testata), `riga_nr` (ordine), `articolo_id` (opzionale), `uom_id` (unità misura), `dest_billing_account_id` (attribuzione economica a BA figlio).
* **Dati merce/servizio**: `descrizione`, `qta` , `prezzo_unitario` , `sconto_percentuale` (0–100, default 0). Per q.ta e prezzo leggere le note contenute nel documento
* **IVA e fiscali**: `iva_id` (il codice), `aliquota_iva` (**la percentuale
  congelata**, dal 2026-08-29), `iva_natura` (snapshot), `esigibilita` (`I`|`D`|`S`),
  `split_payment`.
  ⭐ **Nessuno di questi si scrive a mano**: li mette
  `trgfn_fatture_righe_guard_normalize`. Natura e aliquota vengono dal codice IVA;
  esigibilità e split dal soggetto **cliente**. ⚠️ Un valore passato dall'esterno
  su `aliquota_iva` e `split_payment` viene **sovrascritto**; su `esigibilita`
  no — lì una `'D'` (differita) scelta di proposito **sopravvive**, perché è una
  decisione del documento che nessuna colonna sa dedurre.
* **Importo congelato**: `imponibile_riga` — `NOT NULL`, **calcolato dal DB**, mai da chi scrive la riga. Un valore passato dall'esterno viene **sovrascritto**.
* **Periodo di competenza** (dal 2026-10-02): `competenza_dal`, `competenza_al` — `NOT NULL` **senza default**: chi scrive la riga dice il suo periodo, come entra nella chiave di raggruppamento della generazione. `dal <> al` è un periodo (utilities, canoni), che la rappresentazione stampa; `dal = al` è una riga puntuale, e se raggruppa più attività di date diverse porta **la più recente** (mai `min`–`max`, che si stamperebbe come un periodo inesistente). Le righe nate prima portano il giorno del migrate in entrambe (dati di test).
* **Snapshot kit** (`NULL` sulle righe non-kit, valorizzati insieme sulle righe di kit): `kit_key` (identità dell'**istanza** di kit), `kit_esposizione` (fino al 2026-10-01 `kit_esposto_in_fattura`), `kit_articolo_padre_id`, `kit_descrizione_padre`, e dal 2026-10-02 `kit_qta` (obbligatoria) e `kit_uom_id` (nullable come `uom_id`). Vedi *Kit ed esposizione*.
* **Riga spezzata** (dal 2026-08-31): `riga_capofila_id` — vuoto sulle righe
  ordinarie, valorizzato sulle parti. Vedi *Quando una riga si spezza in due*.
* **Riferimento all'atto** (dal 2026-08-31): `fattura_atto_id` — il blocco di
  [vendite.fatture_atti](/dbzero/vendite/tabelle/fatture_atti) da cui questa riga
  prende CIG, CUP e commessa. Vuoto sulle righe che non nascono da un contratto,
  che sono la maggioranza. ⚠️ Il database garantisce che il blocco appartenga
  **alla stessa fattura**: una riga agganciata all'atto di un altro documento non
  darebbe nessun errore, farebbe solo sparire il CIG dalla fattura giusta.
* **Governance**: `meta` (JSONB, NOT NULL), `storicizza`, `tx_id`, audit `data_*`/`user_*`.
* **Tracciabilità di origine**: `sorgente_tipo_id`, `sorgente_uid`, `sorgente_riga` con **unique parziale** su (sorgente_tipo_id, sorgente_uid). ⚠️ Sulle righe prodotte dall'aggregazione sono **NULL**: con *n* attività di sorgenti diverse non esiste una sorgente singola da dichiarare, e sceglierne una sarebbe una bugia. La tracciabilità passa da `attivita_fatturabili.fattura_riga_id`.

> ❌ **`imposta_riga` e `totale_riga` NON esistono più** (rimosse il 2026-07-28).
> L'imposta di riga non esiste nel regime italiano: l'IVA si liquida per aliquota
> in `vendite.fatture_riepiloghi_iva`, ed è così che il modello è nato. Erano
> colonne persistite e mai scritte, e non erano nemmeno calcolabili dalla riga —
> l'aliquota dipende dallo stato dell'emittente, che sulla riga non c'è.
> ⚠️ `totale_riga` resta un nome vivo **altrove**: è la colonna calcolata
> (`imponibile + imposta`) delle viste di riepilogo IVA di ordini, DDT e
> preventivi. Omonimia, non la stessa cosa.
>
> ❌ **`iva_perc` non è mai esistita** su questa tabella: il manuale precedente la
> citava per errore.
>
> ⛔ **Ma la seconda metà di questa nota è a sua volta superata.** Diceva:
> *«l'aliquota si risolve da `iva_id` con `config.fn_get_aliquota_iva`»*. Dal
> **2026-08-29 esiste `aliquota_iva` sulla riga**, ed è **quella** che si legge —
> la funzione ricalcola il valore **di oggi**, e su un documento congelato è la
> risposta sbagliata.
> ⭐ La regola in una frase: **lo snapshot diventa una fotografia quando il
> documento smette di essere scritto**, non perché qualcuno smette di leggerlo.
> Finché il documento è vivo il trigger riallinea la colonna a ogni scrittura;
> una volta congelato, quella colonna è ciò che il documento porta con sé.
> ⚠️ `NULL` significa **«riga anteriore allo snapshot»**: il backfill non ha
> toccato le righe già congelate, e non doveva — scrivere su uno snapshot fiscale
> è ciò che il guard di congelamento esiste per impedire. Per quelle righe
> l'aliquota sta sul riepilogo.

---

### Vincoli, indici e coerenze

* **FK**: fattura, articolo (opz.), UoM, UoM del kit (`fk_fatture_righe_kit_uom`, dal 2026-10-02), IVA, BA destinatario (opz.), sorgente tipo.
* **CHECK**:

  * `chk_fatture_righe_sconto` → `sconto_percentuale` 0..100 (rinominato da `chk_fatture_righe_sconto_perc`, unificazione 2026-06-05).
  * `chk_fatture_righe_competenza_dal_al` → `competenza_dal <= competenza_al` (dal 2026-10-02).
  * `chk_fatture_righe_kit_coerente` → o la riga **non è** di kit (tutte le colonne `kit_*` NULL), o lo è per intero (chiave, esposizione, articolo padre e, dal 2026-10-02, `kit_qta` valorizzati; `kit_uom_id` può restare vuota come `uom_id`). Una riga con metadati a metà sarebbe indistinguibile da una riga normale per la vista di esposizione, e sparirebbe dal raggruppamento senza un fiato.
  * `chk_fatture_righe_kit_articolo` *(dal 2026-10-02, `20261002-43`)* → una riga di kit ha sempre `articolo_id`: è un componente, e un componente è un articolo della distinta. La vista di esposizione conta i kit **componente per componente**, cioè per articolo: due righe di kit senza articolo cadrebbero nello stesso gruppo e sommerebbero le loro quantità (2 kit dove ce n'è uno), senza un errore. Il periodo di competenza non le separa, perché sono dello stesso kit e dello stesso periodo.
  * ~~`chk_fatr_iva_perc`~~ → **non esiste**: il manuale precedente lo citava insieme alla colonna `iva_perc`, che su questa tabella non c'è mai stata.
* **UNIQUE**:

  * `uq_fatture_righe_riga_nr` su `(fattura_id, riga_nr)` (per progressivo di stampa/ordinamento).
  * `uq_fatture_righe_v_sorgente_fk` su `(sorgente_tipo_id, sorgente_uid)` **WHERE `sorgente_tipo_id IS NOT NULL`** (idempotenza).
* **INDICI operativi**: per ricerche su fattura, IVA, BA destinatario.

---

### Logiche di calcolo — **come funziona davvero**

**L'importo lo calcola il database**, con il trigger
`trg_fatture_righe_a20_importo_ins_upd`, a ogni `INSERT` e `UPDATE`:

```
imponibile_riga = arrotonda(
      qta × prezzo_unitario × (1 − COALESCE(sconto_percentuale,0)/100),
      decimali,   ← vendite.articolo_regole_fatturazione.arrotondamento_importi_dec   (default 2)
      metodo      ← vendite.articolo_regole_fatturazione.metodo_arrotondamento_importi (default HALF_UP)
  )
```

**Le regole che tengono in piedi il calcolo**, e cosa succede se saltano:

| Regola | Presidiata da | Se salta |
|---|---|---|
| L'importo lo calcola il DB, mai chi scrive la riga | trigger `a20` | importi arbitrari dall'esterno — è il difetto d'origine |
| L'arrotondamento avviene **una sola volta**, sul risultato | la formula: arrotonda il totale, mai gli addendi | scarti da doppio arrotondamento |
| Decimali e metodo vengono dalle regole **dell'articolo** | trigger + `script.fn_arrotonda_importo` | la fattura ignora la configurazione |
| Un metodo non riconosciuto **solleva** | `script.fn_arrotonda_importo` | default silenzioso: importo sbagliato che sembra giusto |
| La somma delle quantità aggregate è **esatta** | `numeric(18,6)` su addendi a 6 decimali | perdita di precisione a monte dell'importo |
| Oltre `EMESSA` non si tocca nulla | guard `a10` | una fattura emessa cambia valore dopo l'emissione |

⚠️ **`arrotondamento_quantita_dec` non si applica MAI alla quantità aggregata**
di una riga: è una regola della **singola attività**, a monte. Arrotondare la
somma perderebbe precisione dove nessuno la cerca — a monte dell'importo.

**L'arrotondamento è in un punto solo**: `script.fn_arrotonda_importo(valore,
decimali, metodo)`, con vocabolario unico per tutto il modello — `UP` (allontana
da zero), `DOWN` (avvicina a zero), `HALF_UP`, `HALF_DOWN`.

⚠️ **Non confondere con l'arrotondamento del TOTALE A PAGARE**, che segue la
configurazione **emittente-utility** in `fn_ricalcola_totali_fattura` e ha un
saldo riportato fra documenti. Sono **due regole distinte**: quella di riga è
per articolo, quella del totale è per emittente.

**Conseguenza attesa, non un difetto**: con le righe arrotondate al centesimo,
`fatture_riepiloghi_iva.arrotondamento` risulta **sempre zero** — se le righe
sono esatte al centesimo non c'è scarto da conservare.

---

### Kit ed esposizione in fattura

Un articolo composito (kit) **non arriva in fattura come riga unica**: il push lo
espande e in commessa entrano **solo i componenti**, mai il padre. È il modello
unificato componenti BoM del 2026-05-13, ed è voluto.

Di conseguenza `fatture_righe` conserva **sempre tutte le righe componente**, con
articolo, quantità e prezzo propri: è il **dettaglio**. Il raggruppamento per la
presentazione è una **rappresentazione**, prodotta dalla vista
`vendite.vw_fattura_righe_esposte`.

| Colonna | Contenuto |
|---|---|
| `kit_key` | identità dell'**istanza** di kit (prefisso del `segment_key`, senza la parte `#CMP`). Non l'articolo padre: lo stesso kit può comparire due volte sulla stessa fattura da righe sorgente diverse |
| `kit_esposizione` | snapshot di `catalogo.articoli_componenti.esposizione_in_fattura` per **quella** componente: `NASCOSTO` \| `DESCRITTIVO` \| `VALORIZZATO`, FK su `config.esposizioni_componente(codice_interno)` |
| `kit_articolo_padre_id` | dal `meta` dell'attività (`componente_di`), già risolto dal push |
| `kit_descrizione_padre` | congelata per poterla stampare senza risalire a monte |
| `kit_qta` | *(dal 2026-10-02)* quanti kit rappresenta questa riga: la somma delle quantità della **riga padre del documento** sulle attività aggregate. Non si ricava da `qta / coeff_qta`, perché `coeff_qta` può essere zero |
| `kit_uom_id` | *(dal 2026-10-02)* la UoM della riga padre del documento: in un kit di unità diverse è l'unica che la riga del kit può stampare |

**I tre modi**, come li applica la vista di rappresentazione:

| `kit_esposizione` | In fattura | Nel totale del kit |
| --- | --- | --- |
| `NASCOSTO` | il componente non compare | **sì** |
| `DESCRITTIVO` | riga sotto il kit, senza prezzo né importo | **sì** |
| `VALORIZZATO` | riga sotto il kit con quantità, prezzo e importo suoi | **no**: il suo importo è sulla sua riga |

Il componente resta **sempre legato al suo kit**, anche quando è valorizzato: non
diventa mai una riga sciolta. La riga del kit porta la somma dei componenti
nascosti e descrittivi; se il kit non ha resto (tutti i componenti valorizzati)
resta come intestazione **senza importo** (`NULL`, non zero). Il totale del documento non cambia al
variare dell'esposizione: le righe di `fatture_righe` sono sempre le stesse.

Fino al 2026-10-01 la colonna era il booleano `kit_esposto_in_fattura`,
convertito sul posto senza `UPDATE` (le righe emesse sono intoccabili):
`false` → `NASCOSTO`, `true` → `DESCRITTIVO`, `NULL` (riga non di kit) resta `NULL`.

⚠️ **`esposizione_in_fattura` della distinta è la regola**, non
`articolo_regole_fatturazione.visibilita_componenti` — quest'ultima non era
applicata da nessuno ed è stata **rimossa** dal modello il 2026-07-28.

**Congelamento senza meccanismi aggiuntivi**: lo snapshot sta sulla riga, e le
righe oltre `EMESSA` sono già intoccabili per effetto del guard `a10`. Quindi
cambiare la distinta **non tocca** le fatture emesse, mentre rigenerare una
fattura (reset lotto) rilegge l'esposizione corrente — e la rappresentazione
cambia, com'è giusto.

⚠️ **La vista vale per OGNI uscita**: PDF, XML SDI, portale. Non è «la vista di
stampa»: se il PDF mostrasse il kit raggruppato e l'XML trasmettesse i
componenti, avremmo due uscite dello stesso documento con dettagli diversi.

---

### Quando una riga si spezza in due

(dal 2026-08-31)

Un cliente che ha una **dichiarazione d'intento** ha diritto a un certo importo
di acquisti senza IVA — un «plafond». Può succedere che una singola riga di
fattura sia più grande di quello che resta: i primi tot euro sono coperti, il
resto no.

⛔ **Quella riga non può restare una riga sola.** La fattura elettronica ammette
una sola aliquota e una sola natura per linea: due trattamenti fiscali diversi
sullo stesso importo *devono* diventare due linee. Non è una scelta nostra, è il
formato.

Le due parti restano **due righe di fattura collegate fra loro**:

* la prima è la **capofila**, e ha `riga_capofila_id` **vuoto** — è lei stessa la
  prima parte;
* le successive puntano alla capofila con `riga_capofila_id`.

⭐ **Le attività fatturabili non se ne accorgono**: continuano a puntare alla
capofila come prima, e il loro flag «fatturato» resta acceso da sé. Non è stato
necessario toccare niente in `attivita_fatturabili`.

> ⚠️ **La sola cosa da ricordare, e vale la pena scriverla in grande.** Chi parte
> da un'attività per risalire a **quanto è stato fatturato** deve scendere dalla
> capofila alle sue parti e sommare. Fermarsi alla capofila fa vedere **metà
> valore, senza nessun errore** — il numero è semplicemente più basso.

**Due regole che il database non lascia violare**, e sono proprio le due che, se
saltassero, non darebbero nessun segnale:

| Regola | Cosa impedisce |
| --- | --- |
| Una parte deve puntare a una capofila, **mai a un'altra parte** | Una catena di tre righe: chi somma si ferma al primo passaggio e perde il resto |
| Capofila e parti stanno **sulla stessa fattura** | Una parte agganciata a un'altra fattura mette in disordine i totali di due documenti insieme |

📌 **A video** le due parti si vedono come **due righe pari e adiacenti**, non una
sotto l'altra: la vista di esposizione le tiene attaccate e marca la seconda con
un tipo suo. Le loro quantità possono risultare non tonde (per esempio «6,3492»),
perché la divisione segue l'importo coperto dal plafond e non un numero di pezzi:
è legittimo, ed è voluto — il plafond è un diritto del cliente, e arrotondarlo
per avere un numero più bello glielo ridurrebbe.

⚠️ **Non si confonde con le righe di un kit.** Un kit è *un articolo composto*
venduto insieme; una riga spezzata dal plafond è *lo stesso articolo* diviso in
due per ragioni fiscali. Le colonne `kit_*` non c'entrano e non vanno usate: la
vista di esposizione **somma** le righe di un kit in una sola, e farlo qui
cancellerebbe la ragione per cui la riga si è spezzata.

---

### Esempi d’uso (query applicative)

```sql
-- 1) Righe con imponibile > 0 per una fattura
SELECT r.*
FROM vendite.fatture_righe r
WHERE r.fattura_id = :fattura_id
  AND COALESCE(r.imponibile_riga,0) > 0
ORDER BY r.riga_nr;

-- 2) Somma righe. L'IMPOSTA NON SI SOMMA DALLE RIGHE: si liquida per aliquota
--    nei riepiloghi, che sono l'unica fonte corretta per imposta e totale.
SELECT SUM(r.imponibile_riga) AS imponibile
FROM vendite.fatture_righe r
WHERE r.fattura_id = :fattura_id;

SELECT SUM(ri.imponibile) AS imponibile,
       SUM(ri.imposta)    AS imposta
FROM vendite.fatture_riepiloghi_iva ri
WHERE ri.fattura_id = :fattura_id;

-- 3) Il DETTAGLIO di una riga: le attività che la compongono.
--    Con l'aggregazione una riga può nascere da n attività.
SELECT a.id, a.quantita, a.prezzo_unitario, a.commessa_attivita_id
FROM vendite.attivita_fatturabili a
WHERE a.fattura_riga_id = :riga_id
ORDER BY a.id;

-- 4) Il documento COME VA RAPPRESENTATO (PDF, SDI, portale).
--    Mai leggere fatture_righe direttamente per produrre un'uscita: i kit
--    vanno esposti secondo lo snapshot, e questa vista lo fa.
SELECT tipo_riga, riga_nr, descrizione, qta, prezzo_unitario, imponibile
FROM vendite.vw_fattura_righe_esposte
WHERE fattura_id = :fattura_id
ORDER BY ordinamento, livello, riga_nr;
```

---

### Best practice operative

* ⚠️ **NON valorizzare `imponibile_riga`**: lo calcola il trigger, e un valore passato dall'esterno viene sovrascritto in silenzio. Se scrivendo codice o una fixture ti serve fornirlo per far tornare un conto, il calcolo si è rotto — è il segnale, non la soluzione.
* **Progressivo riga**: assegnare `riga_nr` in modo **contiguo** e consolidato prima della numerazione della fattura.
* **Override BA**: usare `dest_billing_account_id` solo quando necessario (es. ripartizioni o refatturazioni intra‑BA).
* **Validazioni**: bloccare quantità negative e prezzi negativi a livello applicativo (qui sono consentiti consetiti tutti i valori).
* **Esigibilità/split**: impostare solo quando differiscono dal default della testata/cliente.

---

### ⚠️ Osservazioni & possibili migliorie

1. ✅ ~~**Calcolo automatico importi**: opzionale trigger `BEFORE INSERT/UPDATE` per calcolare e arrotondare gli importi se non forniti.~~
   **FATTO il 2026-07-28** — e la parola «opzionale» è costata cara: il trigger
   non è mai stato scritto, il backend lo dava per fatto, e ogni fattura del
   sistema è rimasta a 0,00 € per mesi. Una regola scritta come facoltativa in
   un manuale e assunta come presente nel codice a valle è il modo in cui un
   buco sopravvive senza che nessuno menta.
2. ✅ ~~**Gestione bundle/kit**: se servono righe descrittive non valorizzate, usare `qta = 0` e `totali = 0` con tipo riga in `meta`.~~
   **Risolto diversamente**: le righe descrittive non si simulano con quantità e
   importi a zero, che sarebbero dati falsi. I componenti restano righe vere col
   loro valore, e la **rappresentazione** li rende descrittivi sotto il padre —
   vedi *Kit ed esposizione in fattura*.

---

### 📘 Note progettuali

> In `vendite.fatture_righe` **non** sono imposti vincoli `qta >= 0` o `prezzo_unitario >= 0`.
> Questa è una **scelta intenzionale**: nei contesti *utilities* o *servizi a consumo* possono esistere righe con valori negativi, ad esempio per:
>
Conguagli su stime precedenti.
> Restituzioni o accrediti al cliente.
> Rettifiche di acconti o storni tecnici.
> Bilanciamenti tra letture reali e stimate.
> Il segno negativo è quindi parte integrante del modello economico e **non invalida la correttezza fiscale** della riga.

---

### Ruolo nel sistema

Le righe sono il **cuore economico** della fattura: fotografano quantità, prezzi, sconti e IVA **come effettivamente emessi**, garantendo **stabilità fiscale** e ricostruibilità del documento a distanza di tempo. La qualità dei loro snapshot abilita reporting affidabile, controlli IVA corretti e riconciliazioni con le sorgenti.
