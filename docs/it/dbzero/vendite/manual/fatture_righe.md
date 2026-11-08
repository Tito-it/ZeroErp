## 📘 Documentazione Concettuale – Tabella `vendite.fatture_righe`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatture](/dbzero/vendite/tabelle/fatture) — la testata
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — le attività aggregate nella riga
> * [vendite.fatture_atti](/dbzero/vendite/tabelle/fatture_atti) — il blocco dell'atto (CIG, CUP, commessa)
> * [config.iva](/dbzero/config/tabelle/iva) — il codice IVA
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento d'origine: la riga di fattura è la riga del tipo `FATTURA`
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — l'articolo
> * [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — l'unità di misura
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il BA destinatario
>
> Approfondimento viste:
>
> * [vendite.vw_fattura_righe_esposte](/dbzero/vendite/views/vw_fattura_righe_esposte) — il documento come va rappresentato
>
> Approfondimento funzioni:
>
> * [vendite.fn_fattura_origini](/dbzero/vendite/funzioni/fn_fattura_origini) — i documenti a monte, letti dalla catena delle attività
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza, di cui la riga di fattura è solo bersaglio

---

### 🎯 Scopo Principale

`vendite.fatture_righe` contiene le **righe economiche** di una fattura: descrizione, articolo (opzionale), UoM, quantità, prezzo, sconti, IVA e **imponibile congelato** (*snapshot*) al momento della generazione. Ogni riga è ordinata tramite `riga_nr` ed è collegata a una testata `vendite.fatture` (FK `fattura_id`). Supporta la **destinazione a BA diverso** dalla testata.

Obiettivi principali:

* Conservare il **valore definitivo** della riga per garantire riproducibilità documentale nel tempo.
* Essere il **dettaglio** della fattura: una riga rappresenta l'**aggregazione di 1..n attività fatturabili**, che vi puntano tramite `attivita_fatturabili.fattura_riga_id`.
* Permettere **override di IVA e attributi fiscali** (esigibilità, split payment) a livello riga.
* Mantenere riferimenti all’**articolo di catalogo** e all’**unità di misura** utilizzata per il calcolo.

> ⚠️ Chi legge questa pagina la usa come specifica: descrive **cosa il database fa**, non cosa
> potrebbe fare.

---

### Collocazione nel flusso

1. **Popolamento**: lo fa il **backend**, non il DB — `FattureRigheService.generate_fatture_righe` (`apps/vendite/services/fatture_righe_service.py`), invocato dal task `generate_fatture_righe` della pipeline. **Aggrega** le attività fatturabili del lotto per chiave di raggruppamento — `_build_group_key`: articolo · BA destinatario · UoM · **prezzo unitario** · IVA · competenza · istanza di kit — e produce **una riga per gruppo**. Le *n* attività del gruppo vengono collegate alla riga con `fattura_riga_id`.

    ⚠️ Non esiste una funzione SQL gemella: la generazione delle righe è solo del backend.

2. **Calcolo dell'importo**: NON lo fa chi scrive la riga. Lo calcola il trigger `trg_fatture_righe_a20_importo_ins_upd` a ogni `INSERT`/`UPDATE` — vedi *Logiche di calcolo*.
3. **Ordinamento**: `riga_nr` progressivo per fattura, assegnato con ordinamento **deterministico** dei gruppi; vincolo unico `(fattura_id, riga_nr)`.
4. **Totali testata**: la somma delle righe alimenta i riepiloghi IVA e da lì `imponibile_tot`, `imposta_tot`, `totale_doc`, `totale_a_pagare`.
5. **Congelamento**: da quando il documento e` **congelato** — `config.stati_doc_fiscale.congela_fiscale`, non una lista di stati scritta dentro il guard — il trigger `trg_fatture_righe_a10_guard_congelamento_ins_upd_dlt` respinge `INSERT`, `UPDATE` **e** `DELETE`. La riga diventa uno snapshot fiscale intoccabile. ⭐ Il trigger esegue la guardia **generica** `vendite.trgfn_fattura_satellite_guard_congelamento` (`E_FATTURA_RIGA_CONGELATA`).
6. **Normalizzazione**: `trg_fatture_righe_guard_normalize_ins_upd` eredita il BA destinatario dalla testata e allinea lo snapshot `iva_natura`.

---

### Campi chiave (semantica)

* **Identità e collegamenti**: `fattura_id` (testata), `riga_nr` (ordine), `articolo_id` (opzionale), `uom_id` (unità misura), `dest_billing_account_id` (attribuzione economica a BA figlio).
* **Dati merce/servizio**: `descrizione`, `qta` , `prezzo_unitario` , `sconto_percentuale` (0–100, default 0). Per q.ta e prezzo leggere le note contenute nel documento
* **IVA e fiscali**: `iva_id` (il codice), `aliquota_iva` (**la percentuale
  congelata**), `iva_natura` (snapshot), `esigibilita` (`I`|`D`|`S`),
  `split_payment`.
  ⭐ **Nessuno di questi si scrive a mano**: li mette
  `trgfn_fatture_righe_guard_normalize`. Natura e aliquota vengono dal codice IVA;
  esigibilità e split dal soggetto **cliente**. ⚠️ Un valore passato dall'esterno
  su `aliquota_iva` e `split_payment` viene **sovrascritto**; su `esigibilita`
  no — lì una `'D'` (differita) scelta di proposito **sopravvive**, perché è una
  decisione del documento che nessuna colonna sa dedurre.
* **Importo congelato**: `imponibile_riga` — `NOT NULL`, **calcolato dal DB**, mai da chi scrive la riga. Un valore passato dall'esterno viene **sovrascritto**.
* **Periodo di competenza**: `competenza_dal`, `competenza_al` — `NOT NULL` **senza default**: chi scrive la riga dice il suo periodo, come entra nella chiave di raggruppamento della generazione. `dal <> al` è un periodo (utilities, canoni), che la rappresentazione stampa; `dal = al` è una riga puntuale, e se raggruppa più attività di date diverse porta **la più recente** (mai `min`–`max`, che si stamperebbe come un periodo inesistente).
* **Snapshot kit** (`NULL` sulle righe non-kit, valorizzati insieme sulle righe di kit): `kit_key` (identità dell'**istanza** di kit), `kit_esposizione`, `kit_articolo_padre_id`, `kit_descrizione_padre`, `kit_qta` (obbligatoria) e `kit_uom_id` (nullable come `uom_id`). Vedi *Kit ed esposizione*.
* **Riga spezzata**: `riga_capofila_id` — vuoto sulle righe
  ordinarie, valorizzato sulle parti. Vedi *Quando una riga si spezza in due*.
* **Riferimento all'atto**: `fattura_atto_id` — il blocco di
  [vendite.fatture_atti](/dbzero/vendite/tabelle/fatture_atti) da cui questa riga
  prende CIG, CUP e commessa. Vuoto sulle righe che non nascono da un contratto,
  che sono la maggioranza. ⚠️ Il database garantisce che il blocco appartenga
  **alla stessa fattura**: una riga agganciata all'atto di un altro documento non
  darebbe nessun errore, farebbe solo sparire il CIG dalla fattura giusta.
* **Governance**: `meta` (JSONB, NOT NULL), `storicizza`, `tx_id`, audit `data_*`/`user_*`.
* **Da dove viene una riga: dalla catena, non da una colonna sua.** La riga di fattura **non
  ha una provenienza propria**, e non ha le colonne `sorgente_*`: aggrega *n* attività
  fatturabili, ognuna con la sua origine, e una provenienza sola non esiste per costruzione.
  L'origine si legge risalendo: dalla riga alle attività che la citano
  (`attivita_fatturabili.fattura_riga_id`), da ciascuna alla sua riga di commessa, e da lì al
  documento e alla riga da cui la riga di commessa nasce. È la strada di
  `vendite.fn_fattura_origini`, che dice i documenti a monte della fattura.
  ⚠️ La riga di fattura resta invece **bersaglio** di una provenienza: è la riga del tipo
  `FATTURA` in `config.sorgenti`, e un altro documento può nascere da lei; finché lo cita, la
  riga non si cancella (il lato «in uscita» del modello).

> ❌ **La riga non ha imposta né totale**: l'imposta di riga non esiste nel regime italiano,
> l'IVA si liquida per aliquota in `vendite.fatture_riepiloghi_iva`.
> ⚠️ `totale_riga` è un nome vivo **altrove**: è la colonna calcolata
> (`imponibile + imposta`) delle viste di riepilogo IVA di ordini, DDT e
> preventivi. Omonimia, non la stessa cosa.
>
> ⛔ **L'aliquota si legge da `aliquota_iva` sulla riga**, non si ricalcola da `iva_id` con
> `config.fn_get_aliquota_iva`: la funzione dà il valore **di oggi**, e su un documento
> congelato è la risposta sbagliata.
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

* **FK**: fattura, articolo (opz.), UoM, UoM del kit (`fk_fatture_righe_kit_uom`), IVA, BA destinatario (opz.).
* **CHECK**:

  * `chk_fatture_righe_sconto` → `sconto_percentuale` 0..100.
  * `chk_fatture_righe_competenza_dal_al` → `competenza_dal <= competenza_al`.
  * `chk_fatture_righe_kit_coerente` → o la riga **non è** di kit (tutte le colonne `kit_*` NULL), o lo è per intero (chiave, esposizione, articolo padre e `kit_qta` valorizzati; `kit_uom_id` può restare vuota come `uom_id`). Una riga con metadati a metà sarebbe indistinguibile da una riga normale per la vista di esposizione, e sparirebbe dal raggruppamento senza un fiato.
  * `chk_fatture_righe_kit_articolo` → una riga di kit ha sempre `articolo_id`: è un componente, e un componente è un articolo della distinta. La vista di esposizione conta i kit **componente per componente**, cioè per articolo: due righe di kit senza articolo cadrebbero nello stesso gruppo e sommerebbero le loro quantità (2 kit dove ce n'è uno), senza un errore. Il periodo di competenza non le separa, perché sono dello stesso kit e dello stesso periodo.
* **UNIQUE**:

  * `uq_fatture_righe_riga_nr` su `(fattura_id, riga_nr)` (per progressivo di stampa/ordinamento).
* **INDICI operativi**: per ricerche su fattura, IVA, BA destinatario.

---

### Logiche di calcolo — **come funziona davvero**

**L'importo lo calcola il database**, con il trigger
`trg_fatture_righe_a20_importo_ins_upd`, a ogni `INSERT` e `UPDATE`:

```text
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
unificato dei componenti BoM, ed è voluto.

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
| `kit_qta` | quanti kit rappresenta questa riga: la somma delle quantità della **riga padre del documento** sulle attività aggregate. Non si ricava da `qta / coeff_qta`, perché `coeff_qta` può essere zero |
| `kit_uom_id` | la UoM della riga padre del documento: in un kit di unità diverse è l'unica che la riga del kit può stampare |

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

⚠️ **`esposizione_in_fattura` della distinta è la regola**: non c'è un'altra impostazione di
visibilità dei componenti.

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

### Come si legge una riga

* La **somma delle righe** dà l'imponibile; **imposta e totale non si sommano dalle righe**: si
  leggono dai riepiloghi IVA, l'unica fonte corretta.
* Il **dettaglio** di una riga sono le attività fatturabili che la puntano con `fattura_riga_id`:
  una riga può nascere da *n* attività.
* Il documento **come va rappresentato** (PDF, SDI, portale) si legge da
  `vendite.vw_fattura_righe_esposte`, mai da `fatture_righe` direttamente: i kit vanno esposti
  secondo lo snapshot, e la vista lo fa.

---

### Best practice operative

* ⚠️ **NON valorizzare `imponibile_riga`**: lo calcola il trigger, e un valore passato dall'esterno viene sovrascritto in silenzio. Se scrivendo codice o una fixture ti serve fornirlo per far tornare un conto, il calcolo si è rotto — è il segnale, non la soluzione.
* **Progressivo riga**: assegnare `riga_nr` in modo **contiguo** e consolidato prima della numerazione della fattura.
* **Override BA**: usare `dest_billing_account_id` solo quando necessario (es. ripartizioni o refatturazioni intra‑BA).
* **Validazioni**: bloccare quantità negative e prezzi negativi a livello applicativo (qui sono consentiti consetiti tutti i valori).
* **Esigibilità/split**: impostare solo quando differiscono dal default della testata/cliente.

---

### 📘 Note progettuali

> In `vendite.fatture_righe` **non** sono imposti vincoli `qta >= 0` o `prezzo_unitario >= 0`.
> Questa è una **scelta intenzionale**: nei contesti *utilities* o *servizi a consumo* possono esistere righe con valori negativi, ad esempio per:
>
> * conguagli su stime precedenti;
> * restituzioni o accrediti al cliente;
> * rettifiche di acconti o storni tecnici;
> * bilanciamenti tra letture reali e stimate.
>
> Il segno negativo è quindi parte integrante del modello economico e **non invalida la correttezza fiscale** della riga.

---

### Ruolo nel sistema

Le righe sono il **cuore economico** della fattura: fotografano quantità, prezzi, sconti e IVA **come effettivamente emessi**, garantendo **stabilità fiscale** e ricostruibilità del documento a distanza di tempo. La qualità dei loro snapshot abilita reporting affidabile, controlli IVA corretti e riconciliazioni con le sorgenti.

---

### Note di migrazione

* 2026-06-05 — `chk_fatture_righe_sconto_perc` diventa `chk_fatture_righe_sconto`.
* 2026-07-28 — arriva il trigger che calcola `imponibile_riga`: la pagina lo descriveva come
  «opzionale», il backend lo dava per fatto, e fino a quel giorno ogni fattura restava a
  0,00 €; si ritirano `imposta_riga`, `totale_riga`, la funzione SQL gemella
  `vendite.fn_generate_fatture_righe` (ferma dal 2026-02-03) e
  `articolo_regole_fatturazione.visibilita_componenti`, che nessuno applicava. La pagina citava
  anche una colonna `iva_perc` e un `chk_fatr_iva_perc` mai esistiti
  (brief-fix-importi-riga-fattura-zero, brief-db-ritiro-generatore-righe-fattura-sql).
* 2026-08-29 — arriva `aliquota_iva`, la percentuale congelata; le righe già congelate restano
  `NULL`, e per loro l'aliquota sta sul riepilogo.
* 2026-08-30 — il congelamento si legge da `congela_fiscale` e passa alla guardia generica dei
  satelliti della fattura.
* 2026-08-31 — arrivano `riga_capofila_id` (riga spezzata dal plafond) e `fattura_atto_id`.
* 2026-10-01 — il booleano `kit_esposto_in_fattura` diventa `kit_esposizione`, convertito sul
  posto: `false` → `NASCOSTO`, `true` → `DESCRITTIVO`.
* 2026-10-02 — arrivano il periodo di competenza (le righe più vecchie portano il giorno della
  migrazione in entrambe le date), `kit_qta`, `kit_uom_id` e `chk_fatture_righe_kit_articolo`.
* 2026-11-06 — si ritirano l'indice univoco `uq_fatture_righe_v_sorgente_fk`, che presentava
  la provenienza come chiave d'idempotenza, e il `DEFAULT 0` di `sorgente_riga`
  (brief-db-sorgente-documento-e-riga).
* 2026-11-07 — la provenienza passa al modello: le righe nate da una riga di commessa, che
  portavano un'impronta in `sorgente_uid`, prendono la commessa in `sorgente_id`; arrivano la
  forma `chk_fatture_righe_sorgente_forma`, gli indici della provenienza e il guard unico
  (brief-db-sorgente-documento-e-riga).
* 2026-11-08 — la riga di fattura perde la provenienza: si ritirano le colonne
  `sorgente_tipo_id`, `sorgente_id`, `sorgente_uid`, `sorgente_riga`, con la FK verso
  `config.sorgenti`, `chk_fatture_righe_sorgente_forma`, i tre indici e il guard unico. Le
  scriveva solo il backend, quasi sempre vuote; le poche righe che le portavano dicevano la
  stessa cosa della catena delle attività (brief-db-sorgente-documento-e-riga, G-4).

---

{% include-markdown "signature-core.md" %}
