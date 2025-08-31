## 📘 Documentazione Concettuale – Corrispettivi (`vendite.doc_commerciali` e correlate)

> 👀 **Vedi anche**
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
> * [config.iva](/dbzero/config/tabelle/iva)
> * [vendite.magazzino\_movimenti](/dbzero/vendite/tabelle/magazzino_movimenti) (scarico contestuale)
> * [vendite.note](/dbzero/vendite/tabelle/note) *(estendibile con una partizione per corrispettivi, se necessario)*

---

### 🎯 Scopo Principale

Gestire i **documenti commerciali** (corrispettivi/scontrini) emessi da punti cassa o registratori telematici (RT), coprendo emissione, pagamenti, scarico magazzino, invio telematico, resi/annulli e **fattura su corrispettivo**.

---

### 🎯 Obiettivi (cosa devono coprire)

* Emissione **documento commerciale** (ex scontrino) con **numero progressivo** e **dati RT**.
* **Invio telematico** e **stati**: `EMESSO → TRASMESSO → ACCETTATO/SCARTATO`.
* **Pagamenti anche misti** (contanti+POS+buoni), **resto**, **incasso immediato**.
* **Scarico magazzino** immediato (per articoli merce).
* **Resi/annulli** con **storno fiscale** coerente (non “note credito” come le fatture).
* **Fattura su corrispettivo** su richiesta, con **riferimento puntuale** al corrispettivo.
* **Riepiloghi giornalieri**: **chiusura/Z**, corrispettivi per **aliquota/natura**, contabilità.

---

### 🧭 Confini con il resto del modello

* **No BA/contratto** per i corrispettivi retail: sono **vendite al banco**.
* Se il cliente chiede **fattura su corrispettivo**, si entra nel mondo **fatture** (**BA richiesto**) ma la fattura **riferisce** il corrispettivo (non rigenera la vendita).
* Gli **articoli** sono quelli di `catalogo.articoli` con **UM/IVA**.

---

### 🗂️ Entità (proposta)

#### 1) `vendite.doc_commerciali` (testata)

* **Chiavi e intestazione**: `id (BIGINT identity)`, `esercizio`, `punto_cassa_id` *(o `rt_id`)*, `numero`, `data`, `ora`.
* **Stati**: `BOZZA | EMESSO | TRASMESSO | ACCETTATO | SCARTATO | ANNULLATO | RESO`.
* **Totali**: `tot_imponibile`, `tot_iva`, `tot_documento`, `arrotondamento` *(cash rounding)*, `valuta`.
* **Trasmissione**: `rt_serial`, `rt_transaction_id` *(ID invio)*, `esito_invio`, `msg_esito`, `data_invio`.
* **Cliente opzionale** *(solo per fattura differita o dati in stampa)*: `codice_fiscale`, `partita_iva`, `denominazione` *(non BA)*.
* **Meta** (`JSONB`): payload RT, info canale, cassiere, postazione.
* **Collegamenti**: `fattura_id` *(se emessa fattura su corrispettivo — univoco)*.
* **Audit** standard.

#### 2) `vendite.doc_commerciali_righe`

* **Chiavi**: `id`, `doc_id`.
* **Contenuto**: `articolo_id (UUID)`, `descrizione`, `um_id`, `quantita`, `prezzo_unit`, `sconti_%/importo_sconto`, `iva_id/natura_iva`.
* **Importi riga**: `importo_riga_imponibile`, `importo_riga_iva`, `importo_riga_tot`.
* **Magazzino**: `magazzino_id` *(da cui scaricare)*, `mov_mag_id` *(link allo scarico)*.
* **Meta**: seriale, lotto, note.
* **Reso/annullo**: `riga_ref_id` *(riga originaria)* + **segno/quantità negativa**.

#### 3) `vendite.doc_commerciali_pagamenti`

* **Chiavi**: `id`, `doc_id`.
* **Metodo**: `CONTANTE | POS | BONIFICO | BUONO | ALTRO`.
* **Dettagli**: `importo`, `riferimento` *(es. autorizzazione POS)*, `meta`.
* **Controllo**: **somma pagamenti = totale documento ± resto**.

#### 4) `vendite.doc_commerciali_iva`

* **Aggregati per aliquota/natura**: `aliquota`, `natura`, `imponibile`, `iva`.
* Popolata da **trigger** o in fase di **chiusura**.

#### 5) `vendite.doc_commerciali_link_fattura`

* Se si emette **fattura su corrispettivo**: relazione `doc_id ↔ fattura_id`, con **numero/data/rt\_serial** per stampa.

#### 6) `vendite.chiusure_cassa` (Z giornaliere)

* **Chiavi**: `id`, `punto_cassa_id/rt_id`, `data`.
* **Dati**: `numeri_da_a`, totali per **aliquota** e **metodo pagamento**, `stato_invio`, `meta`.
* **Coerenza**: tutte le vendite del giorno e del punto confluiscono in **una sola Z** *(o più se multi-turno: aggiungere `turno` come discriminante).*

---

### 🔁 Flussi chiave

**Emissione**

* `BOZZA → EMESSO`: calcoli **imponibili per riga**, **aggregati IVA**, **registri pagamenti** (e resto).
* **EMESSO**: crea **movimento magazzino (scarico)** per ogni riga merce.
* `TRASMESSO → ACCETTATO/SCARTATO`: salvi **id RT/esito**.

**Reso/annullo**

* **Annullo contestuale**: documento di storno che **riferisce** l’originario *(stato originario → ANNULLATO)*; righe con **quantità/importi a segno opposto**, pagamenti **inversi** (o “rimborso”).
* **Reso differito**: nuovo documento con **righe negative** che **referenziano** quelle originarie (tracciabilità), eventuale movimento di **carico** magazzino.

**Fattura su corrispettivo**

* Crea **fattura** (con **BA**), **righe copiate** dal corrispettivo; collega `doc_commerciali_link_fattura`.
* **Nessun doppio scarico** magazzino (già fatto dal corrispettivo).

**Chiusura/Z**

* Accorpa documenti **EMESSO/ACCETTATO** del giorno/punto; calcola totali per **aliquota** e **pagamento**; marca righe/doc come **confluite** nella chiusura (`flag`/`chiusura_id`).
* Gestisce **stato invio Z** e **scarti**.

---

### ✅ Regole/controlli importanti

* **Stati coerenti** (transizioni ammesse) e **immutabilità** di **numero/data** dopo `EMESSO`.
* **Somma pagamenti = totale** *(± resto)*; `resto ≥ 0`.
* **IVA/natura** obbligatoria per riga (allineata ad **articolo/aliquota vigente**).
* **Scarico magazzino**: solo su **righe merce**; **servizi** non scaricano.
* **Univocità progressivo** per `(rt_id, esercizio, numero)`.
* **Resi**: riga deve **referenziare** doc/riga originale; **quantità negative**.
* **Fattura su corrispettivo**: **un solo link** per doc; impedire **doppia fatturazione**.

---

### 🔗 Integrazione con l’ecosistema

* **Articoli**: `catalogo.articoli` (ok). **Regole IVA** da `config.iva` / `config.iva_natura`.
* **Magazzino**: genera **movimenti** (riuso della tabella movimenti prevista).
* **Note**: riusa la partizione **FATTURA** per le note di fattura; per i corrispettivi, potrai creare **`vendite.note_corrispettivo`** come **nuova partizione** (stesse regole di preventivi/contratti).
* **Contabilità**: mappatura **corrispettivi** (no partite clienti). Definire **conti ponte** per metodo pagamento.

---

### ❓ Decisioni da prendere prima del DDL

1. **Identità cassa/RT**: modellare `config.punti_cassa` / `config.rt_device` *(seriale, matricola, stato)*? → **Consigliato**.
2. **Progressivi**: per **punto cassa** o per **RT**? *(di solito per RT)*.
3. **Resi**: consentire **parziali** su singola riga? → **Sì** (con `riga_ref_id` e quantità negativa).
4. **Z giornaliera**: una per **giorno e punto**, oppure gestire anche **turni**? *(se retail vero, aggiungere `turno`)*.
5. **Note sui corrispettivi**: servono **ora**? *(se sì, estendere `vendite.note` con nuova partizione).*
6. **Invio telematico**: salvare solo **esito** e **payload di ritorno**, o anche **payload inviato**? → Salvare **entrambi** in `meta` per audit.

---

> Se la linea ti torna, passo a preparare il **DDL Liquibase** per:
> `vendite.doc_commerciali`, `doc_commerciali_righe`, `doc_commerciali_pagamenti`, `doc_commerciali_iva`, `doc_commerciali_link_fattura`, `vendite.chiusure_cassa`,
>
> * tabelline di base `config.rt_device` / `config.punti_cassa` per ancorare numerazione e Z.
