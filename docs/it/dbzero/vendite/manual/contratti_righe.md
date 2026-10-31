## 📘 Documentazione Concettuale – Tabella `vendite.contratti_righe`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**   
>
• [vendite.contratti](/dbzero/vendite/tabelle/contratti)   
> • [vendite.note_contratto](/dbzero/vendite/tabelle/note_contratto)  
> • [vendite.regole_fatturazione_articolo](/dbzero/vendite/tabelle/articolo_regole_fatturazione)    
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)   
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)   
> • [anagrafiche.istanze_dati_precontrattuali](/dbzero/anagrafiche/tabelle/istanze_dati_precontrattuali)     

---
### 🎯 Scopo Principale
> **Ultimo aggiornamento**: 31 ottobre 2026

`vendite.contratti_righe` contiene le **eccezioni** del contratto rispetto al suo listino: una
riga non è «un articolo del contratto» ma un **modificatore** di un articolo
(rev 2026-10-31: fino a questa data lo Scopo diceva «ogni riga rappresenta un articolo/servizio»,
del modello precedente alle eccezioni). Il tipo lo dice `tipo_eccezione`:

* `OVERRIDE` — il prezzo del cliente per un articolo del listino;
* `ESCLUSIONE` — un articolo del listino tolto al cliente;
* `AGGIUNTA` — un articolo fuori listino, al prezzo della riga;
* `ADESIONE` — un articolo del listino che il cliente prende, al prezzo del listino.

Ogni riga che non è un'esclusione porta anche **come si eroga** (una tantum, canone, ore,
consumo), con quantità e, per il canone, periodicità. Che cosa il contratto **addebita** da
queste righe (e dalle quote fisse del listino, che non hanno bisogno di una riga) lo dice
[`vendite.fn_contratti_addebiti_maturati`](/dbzero/vendite/manual/fn_contratti_addebiti_maturati);
in parole semplici, la [guida dei contratti §4-bis](/guide/gestione-contratti#4-bis-come-il-contratto-si-addebita-una-tantum-e-canoni).

---

### Collocazione nel flusso

1. **Creazione contratto** → testata in `vendite.contratti`.
2. **Inserimento righe** → articoli e regole di erogazione in `vendite.contratti_righe`.
3. **Push in commessa** → a ogni giro il push dei contratti manda in commessa le una tantum e i periodi di canone maturati, e gli storni ([`fn_list_contratti_da_pushare`](/dbzero/vendite/manual/fn_list_contratti_da_pushare)); dalla commessa alla fattura.

---

### Campi chiave e logiche operative

* **Articolo** (`articolo_id`) → servizio/voce di catalogo.
* **Tipo di eccezione** (`tipo_eccezione`) → OVERRIDE, ESCLUSIONE, AGGIUNTA, ADESIONE (sezione dedicata sotto).
* **Tipo erogazione** (`tipo_erogazione`) → natura della riga: `CANONE`, `UNA_TANTUM`, `ORARIO`, `CONSUMO`.
* **Fonte quantita attesa** (`fonte_quantita_attesa`) → origine della quantita attesa (vedi sezione dedicata).
* **Periodicita** (`periodicita`, FK a `config.periodicita`) → ogni quanti mesi si addebita il canone: mensile, bimestrale, trimestrale, quadrimestrale, semestrale, annuale. Su ADESIONE e OVERRIDE a canone, se vuota, la riempie la riga del listino (`script.trgfn_righe_default_periodicita_da_listino`). Una riga a canone senza periodicità non si addebita: la segnala la dashboard (`CANONE_NON_GENERABILE`).
* **Generazione canone** (`generazione_canone`) → `INIZIO_PERIODO` (anticipato) o `FINE_PERIODO` (normale). **Vuota = segue la testata** (`vendite.contratti.generazione_canone`); valorizzata la forza su questa riga. `PRORATA` è ritirato: il periodo incompleto si paga sempre in proporzione. `competenza_canone` è ritirata (2026-10-29): il periodo lo dicono la testata (mese di partenza) e la periodicità.
* **Prezzo unitario** (`prezzo_unitario`, `numeric(18,6)` dal 2026-10-05) e **quantita** (`quantita`) → base per righe a canone o una‑tantum.
* **Meta** (`meta`) → estensioni specifiche (parametri di tariffa, flag tecnici, mapping esterni). Sempre valorizzato (`NOT NULL`, default `{}`), come `attivo` (default `true`), dal 2026-10-05.

---

### Matrice `tipo_erogazione` × `fonte_quantita_attesa` (dal 2026-05-19)

> **Migrations**: `20260519-05` (backfill + NOT NULL + CHECK), `20260519-06` (trigger normalize).

`fonte_quantita_attesa` e’ **NOT NULL** e deve essere coerente con `tipo_erogazione`.
Il trigger `script.trgfn_righe_default_fonte_qta` (funzione **generica**, condivisa
con `offerte_commerciali_eccezioni` dal refactor 2026-05-31; sostituisce la vecchia
`vendite.trgfn_contratti_righe_default_fonte_qta`) imposta il default automaticamente
su INSERT e resetta la fonte se il cambio di `tipo_erogazione` rende la combinazione vietata.

#### Valori ammessi per `fonte_quantita_attesa`

| Valore | Significato | `quantita` mostrata in UI? |
| --- | --- | --- |
| `FISSA` | Quantita contrattualizzata a corpo | Si’, obbligatoria |
| `MANUALE` | Quantita definita sul documento al momento dell’emissione | No — tag "Definita sul documento" |
| `DURATA` | Solo per il canone: la quantita la conta il sistema dal calendario (giorni o mesi del periodo), nell'unita dell'articolo, che deve avere `conta_dal_calendario` (dal 2026-10-29) | No — la conta il push |
| `TIMESHEET` | Quantita da rendicontazione ore (modulo futuro) | No — tag "Da rendicontazione ore" |
| `LETTURE` | Quantita da letture utility | No — tag "Da letture utility" |

⛔ **`DERIVATA_COMPONENTI` è ritirata** (2026-10-21, decisione I-D1 di Tid,
`brief-db-offerta-emissione-ed-erogazione` §I.1). Prometteva «la quantità del padre la calcola il DB
dai componenti», ma i componenti si calcolano **dal** padre (`coeff_qta × quantita`, negli init e in
`trg_contratti_righe_z90_propaga_qta_componenti_upd`): nessuno la calcolava. Le combinazioni ammesse
sono quelle di `config.erogazioni_fonti`, e quelle di un articolo le dice `vendite.fn_articolo_erogazioni`.

⭐ **Un kit si vende solo a quantità fissa** (I-D6, 2026-10-21): sull'articolo composito
`vendite.fn_articolo_erogazioni` tiene le sole combinazioni FISSA, perché senza quantità sulla riga i
componenti non nascono e il prezzo del padre (la somma dei componenti) resta 0.

⭐ **`quantita` è calcolata** (dal 2026-10-08): con una fonte a valle (MANUALE, LETTURE,
TIMESHEET; `script.fn_fonte_porta_quantita` = false) `script.trgfn_qta_from_operativa` la porta a
NULL a ogni INSERT e UPDATE; il guard `script.trgfn_righe_guard_quantita_per_fonte` rifiuta solo
`qta_operativa` (`E_RIGA_QUANTITA_CON_FONTE_A_VALLE`, campo `qta_operativa`). Rete:
`chk_contrighe_quantita_per_fonte`. Brief `brief-db-offerta-emissione-ed-erogazione` §F.1.

#### Matrice coerenza (legenda: ✅ default · 🟢 secondaria · 🟡 rara/edge · ❌ vietata)

| tipo_erogazione | FISSA | MANUALE | TIMESHEET | LETTURE |
| --- | --- | --- | --- | --- |
| **CANONE** | ✅ | ❌ (ritirata 2026-10-29) | ❌ | ❌ |
| **UNA_TANTUM** | ✅ | 🟢 | ❌ | ❌ |
| **ORARIO** | 🟡 | 🟢 | ✅ (futuro) | ❌ |
| **CONSUMO** | ❌ | 🟢 | ❌ | ✅ |

`DURATA` vale solo per il canone (`CANONE/DURATA`, 🟢). `CANONE/MANUALE` è ritirata il
2026-10-29: nessuno sapeva che cosa caricare a ogni periodo; al suo posto la durata.

Le combinazioni ❌ non sono in `config.erogazioni_fonti`, e la FK composta delle righe le rifiuta
(dal 2026-10-07 ha preso il posto del CHECK `chk_contrighe_coerenza_fonte_erogazione`).
Le combinazioni 🟡 rare sono ammesse e segnalate in UI con tooltip "uso atipico".

#### Default per `tipo_erogazione`

| tipo_erogazione | fonte default |
| --- | --- |
| `CANONE` | `FISSA` |
| `UNA_TANTUM` | `FISSA` |
| `ORARIO` | `MANUALE` (sara’ `TIMESHEET` quando il modulo esistera’) |
| `CONSUMO` | `LETTURE` |
| `NULL` o non riconosciuto | `FISSA` (fallback difensivo) |

---

### 📏 Quantita operative e unita di misura

Per righe che richiedono una UoM operativa:

* **`uom_operativa_id`** identifica la UoM usata in riga.
* **`qta_operativa`** indica la quantita nella UoM operativa (**sorgente**).
* **`factor_to_base`** salva lo snapshot del fattore di conversione verso la UoM base.
  **Nullable** dal refactor 2026-05-31 (prima `NOT NULL DEFAULT 1`): se NULL il trigger
  lo deriva dal mapping `catalogo.articoli_uom_operativa` e lo salva.
* Il trigger `script.trgfn_qta_from_operativa(...)` garantisce la **coerenza della quantita base** (`quantita`, derivata) a partire dalla quantita operativa.
* Vincolo `chk_contrighe_qta_operativa_nonzero` (`qta_operativa IS NULL OR qta_operativa <> 0`): negativi ammessi, zero vietato.

---

### Collegamento con dati precontrattuali

Quando l’istanza e` di tipo utility, i dati di `anagrafiche.istanze_dati_precontrattuali` possono:

* fornire **parametri tecnici** per la valorizzazione di `meta`;
* determinare **regole di fatturazione** (es. tariffe, scaglioni, soglie);
* influenzare `quantita` o la **fonte di quantita**.

Per servizi non‑utility, la riga rimane il punto di verita delle condizioni economiche.

---

### Righe come eccezioni del listino — `tipo_eccezione` (dal 2026-05-15)

> **Refactor Step 2.2** — migration `20260515-11`, `20260515-12`.
> Il modello "modalità A/B/C" è eliminato. Le righe sono ora **eccezioni tipizzate**
> rispetto al listino del contratto padre.

Ogni riga porta un campo `tipo_eccezione vendite.tipo_eccezione_contratto NOT NULL`:

| Valore | Significato | `prezzo_unitario` |
| --- | --- | --- |
| `OVERRIDE` | Prezzo personalizzato per articolo già nel listino | NOT NULL |
| `ESCLUSIONE` | Articolo del listino escluso per questo cliente | NULL |
| `AGGIUNTA` | Articolo non presente nel listino, aggiunto al contratto | NOT NULL |
| `ADESIONE` | Articolo del listino che il cliente prende, al prezzo del listino con la variazione globale (dal 2026-10-29) | NULL |

#### CHECK `chk_contrighe_prezzo_per_tipo_eccezione`

Coerenza strutturale dichiarativa:

```text
ESCLUSIONE, ADESIONE → prezzo_unitario IS NULL
OVERRIDE, AGGIUNTA   → prezzo_unitario IS NOT NULL
```

#### Vincoli di unicità parziale

| Indice | Predicato | Semantica |
| --- | --- | --- |
| `uq_contrighe_one_eccezione_per_articolo` | `WHERE tipo_eccezione IN ('OVERRIDE','ESCLUSIONE','ADESIONE')` | OVERRIDE, ESCLUSIONE e ADESIONE sono mutualmente esclusivi per la stessa coppia `(contratto, articolo)` |
| `uq_contrighe_one_aggiunta_per_articolo` | `WHERE tipo_eccezione = 'AGGIUNTA'` | Al più una AGGIUNTA per coppia `(contratto, articolo)` |

#### Quali articoli ammette la riga (AGGIUNTA, OVERRIDE, ESCLUSIONE)

Dal 2026-10-13 (brief-db-articoli-ammessi-per-documento, Lotto 3b) lo dice una check sola,
[script.fn_check_articolo_riga](/dbzero/script/manual/fn_check_articolo_riga), che il trigger `trg_contratti_righe_a10_guard_articolo_ammesso_ins_upd`
(→ [script.trgfn_righe_guard_articolo_ammesso](/dbzero/script/manual/trgfn_righe_guard_articolo_ammesso), lo stesso dell'offerta e di preventivo, ordine e bolla) solleva
col primo motivo, prima dei guard di riga. Ha preso il posto dei guard «aggiunta fuori
listino» ed «esclusione figlio di bundle», e ha aggiunto la regola opposta: un'OVERRIDE o
un'ESCLUSIONE si fanno solo su un articolo del listino (`E_RIGA_ECCEZIONE_FUORI_LISTINO`,
`E_RIGA_ECCEZIONE_SENZA_LISTINO`). L'AGGIUNTA è per articoli **non** presenti nel listino:

* **Contratto senza listino** (`listino_id IS NULL`): nessun check, AGGIUNTA sempre valida.
* **Contratto DRAFT** (`listino_versione_id IS NULL`): verifica nella versione in vigore oggi.
* **Contratto ATTIVO** (`listino_versione_id IS NOT NULL`): verifica nella versione fissata all'attivazione.

La versione la dice [`vendite.fn_documento_listino_operativo`](/dbzero/vendite/funzioni/fn_documento_listino_operativo), comune a contratto e offerta.

Se l'articolo è già nel listino → `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO` (id 450). L'operatore deve usare `OVERRIDE` invece di `AGGIUNTA`.

#### Righe solo in bozza (era «lock post-attivazione», Step 2.3)

Le righe si aggiungono, modificano e tolgono solo finché il contratto è in
DRAFT: il trigger `trg_contratti_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt`
— il building block
[`trgfn_doc_righe_lock_fuori_bozza`](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza),
lo stesso di `ddt_righe` e `ordini_righe` — blocca **qualsiasi**
INSERT/UPDATE/DELETE in ATTIVO, CESSATO e ANNULLATO → `E_RIGA_DOC_NON_BOZZA`.
La copia dedicata ai contratti (che bloccava il solo ATTIVO) è stata ritirata il
2026-09-22; il codice 452 resta al lock della testata.

#### Un'esclusione non si modifica (2026-10-04)

Una riga `ESCLUSIONE` dice una cosa sola: il contratto non vende quell'articolo
del listino. Si crea (Escludi) e si cancella (Ripristina articolo, `DELETE`), e
basta: prezzo, quantità, UoM, erogazione e fonte non la riguardano. Il trigger
`trg_contratti_righe_a05_guard_esclusione_immutabile_upd`
(→ [`script.trgfn_righe_guard_esclusione_immutabile`](/dbzero/script/funzioni/trgfn_righe_guard_esclusione_immutabile), la stessa dell'offerta)
rifiuta ogni `UPDATE` che cambi qualcosa di diverso dalle colonne tecniche →
`E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE`. Anche `attivo`: un'esclusione spenta
terrebbe occupato il posto dell'articolo in `uq_contrighe_one_eccezione_per_articolo`.

#### Il tipo di una riga non si cambia (2026-10-04)

`tipo_eccezione` è bloccato da un lock di colonna (registro
`dbops.automation_lock_columns`) → `E_CONTRATTO_RIGA_TIPO_ECCEZIONE_IMMUTABILE`.
Ogni tipo ha i suoi dati e i suoi controlli, che valgono quando la riga nasce:
un `OVERRIDE` portato a `ESCLUSIONE` sul posto creerebbe un'esclusione senza
passare da Escludi. Per cambiare tipo si elimina la riga e se ne crea una nuova.

#### Una riga che si fattura dice come si eroga (2026-10-04)

Ogni riga che non è `ESCLUSIONE` (`OVERRIDE`, `AGGIUNTA`, `ADESIONE`) può finire in
fattura (l'OVERRIDE quando il cliente compra, o al posto di una quota fissa), e la fattura deve sapere come conteggiarla: `tipo_erogazione` è
obbligatoria. Sull'esclusione è vuota, perché non si fattura (sezione seguente). Il trigger
`trg_contratti_righe_a10_guard_erogazione_obbligatoria_ins_upd`
(→ [`trgfn_righe_guard_erogazione_obbligatoria`](/dbzero/script/funzioni/trgfn_righe_guard_erogazione_obbligatoria))
rifiuta l'`INSERT` o l'`UPDATE` che la lascia vuota → `E_RIGA_EROGAZIONE_OBBLIGATORIA`,
col campo `tipo_erogazione` da evidenziare. Dietro c'è il vincolo
`chk_contrighe_erogazione_per_tipo_eccezione`. La stessa regola vale sulle righe
dell'offerta, da cui il contratto le copia.

#### Un'esclusione non porta dati di vendita (2026-10-04)

L'esclusione dice solo «questo articolo non si vende». Prezzo, quantità,
quantità operativa, unità di misura, fattore, erogazione, fonte, periodicità e
generazione del canone **restano vuoti**: lo dice il vincolo
`chk_contrighe_esclusione_senza_dati`, e a parlare all'operatore è il trigger
`trg_contratti_righe_a10_guard_esclusione_senza_dati_ins`
(→ [`script.trgfn_righe_guard_esclusione_senza_dati`](/dbzero/script/funzioni/trgfn_righe_guard_esclusione_senza_dati))
→ `E_RIGA_ESCLUSIONE_CON_DATI`, col campo da svuotare.

* `fonte_quantita_attesa` non è più `NOT NULL`: è obbligatoria (vincolo
  `chk_contrighe_fonte_per_tipo_eccezione`) solo sulle righe che non sono
  esclusioni.
* I due trigger che riempiono la riga — fonte di default e quantità dall'unità
  operativa — **saltano l'esclusione** (`WHEN` sul trigger): sono funzioni
  generiche, e chi sa che l'esclusione non ha quantità è la tabella.
* Le stesse regole valgono sulle righe dell'offerta, che il contratto copia.

---

#### Gli stessi tipi della riga dell'offerta (2026-10-05)

Il push copia la riga dell'offerta nel contratto così com'è: un valore valido
sull'offerta non deve poter fallire qui. Dal 2026-10-05 le due tabelle hanno gli
stessi tipi su ogni colonna comune: `prezzo_unitario` è `numeric(18,6)` (era
`(15,6)`: un prezzo oltre il miliardo passava sull'offerta e moriva al push), i
codici di erogazione (`fonte_quantita_attesa`, `periodicita`,
`generazione_canone`; `competenza_canone`, allora la quarta, è ritirata il 2026-10-29) sono `varchar(32)`. Anche
`attivo` e `meta` sono diventati obbligatori, come sull'offerta. Lo presidia
`db/pgtap/vendite/test-righe-gemelle-secondo-giro-v1.sql` (test 1, 3), che
confronta le due tabelle colonna per colonna: una divergenza futura è un rosso.
Brief: `brief-db-righe-esclusione-solo-non-si-vende` §8.2 B2, B4.

### Vincoli e trigger rilevanti

* **FK principali**: contratto, articolo, UoM operativa.
* **Trigger**:
  * `trg_contratti_righe_a05_guard_esclusione_immutabile_upd` — una riga ESCLUSIONE non si modifica (2026-10-04).
  * lock di colonna su `tipo_eccezione` (generato dal registro `dbops.automation_lock_columns`, 2026-10-04).
  * `trg_contratti_righe_a10_guard_erogazione_obbligatoria_ins_upd` — una riga che si fattura vuole `tipo_erogazione` (2026-10-04).
  * `trg_contratti_righe_a10_guard_articolo_ammesso_ins_upd` — quali articoli ammette la riga: solo componente, tipologia, erogazioni, AGGIUNTA fuori listino, OVERRIDE ed ESCLUSIONE solo sul listino, figlio di bundle (2026-10-13; prende il posto dei guard «aggiunta fuori listino» ed «esclusione figlio di bundle»).
  * `trg_contratti_righe_a10_guard_esclusione_senza_dati_ins` — un'esclusione non porta dati di vendita (2026-10-04).
  * `trg_contratti_righe_a10_default_fonte_qta_ins_upd` — normalizza `fonte_quantita_attesa` al default su INSERT e su UPDATE con tipo cambiato (20260519-06; ri-bindato alla funzione generica `script.trgfn_righe_default_fonte_qta` in 20260531-10). Salta l'esclusione dal 2026-10-04.
  * `trg_contratti_righe_a10_qta_from_operativa_ins_upd` — calcolo quantita base da operativa. Salta l'esclusione dal 2026-10-04.
  * `trg_contratti_righe_a10_note_contratto_block_deact_upd` — blocca disattivazioni se presenti note figlie.
  * `trg_contratti_righe_a10_articoli_require_attivo_ins_upd` — articolo attivo obbligatorio.
* **Componenti**: i componenti di una riga composita (`vendite.contratti_righe_componenti`) seguono la regola delle righe — si toccano solo in DRAFT — col loro trigger `_a05_` (dal 2026-10-05).

---

### Best practice

* Impostare `tipo_eccezione` esplicitamente in base all'intento commerciale: **mai** usare AGGIUNTA per articoli già nel listino.
* Impostare `tipo_erogazione` e `fonte_quantita_attesa` in modo coerente con la logica di calcolo.
* Inserire in `meta` i soli parametri non coperti da colonne core.
* Disattivare una riga (`attivo = false`) solo dopo aver gestito le note collegate.
* Un'esclusione non si disattiva e non si modifica: si cancella («Ripristina articolo»).

---

### Ruolo nel sistema

`vendite.contratti_righe` e` il **dettaglio contrattuale operativo**: traduce il contratto in voci fatturabili, collegando catalogo, regole di erogazione e parametri tecnici. E` il ponte tra **accordo commerciale** e **processo di fatturazione**.

{% include-markdown "signature-core.md" %}

---
