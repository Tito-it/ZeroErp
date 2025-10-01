# ✅ Obiettivo

* Tenere **una sola fonte ufficiale** per lo stock: **`magazzino.movimenti`** (ledger).
* Permettere **posting** da **qualsiasi documento/evento** (DDT, Ordine di Lavoro, Trasferimento, Rettifica, Inventario, Reso, etc.).
* Gestire **asset serializzati** (contatori) con **ciclo di vita** distinto dallo stock “consumabile”.
* Agganciare i movimenti alle **“attività fatturabili”** quando rilevante.

---

# 1) Document-agnostic posting (niente solo DDT)

Introdurre un **meccanismo di posting unico** che scrive su `magazzino.movimenti` a prescindere dal documento sorgente.

**Chiavi di progetto**

* `sorgente_schema`, `sorgente_tabella`, `sorgente_id`, `sorgente_riga_id` (idempotenza, audit, riconciliazione).
* `causale_id` (lookup “Ingresso acquisti”, “Uscita ODL”, “Trasferimento”, “Consumo tecnico”, “Installazione asset”, “Rientro”, “Rettifica”...).
* `magazzino_id` (inclusi magazzini “speciali”: **furgone tecnico**, **WIP**, **in-transit**).
* `articolo_id`, `uom_id`, `qta` (+/−), `lotto`, `seriale` (se applicabile), `costo_unitario`, `valore`, `data_mov`, meta/audit (`tx_id`, `user_*`, `storicizza`).

**Come si usa**

* DDT **vendite/acquisti**: già previsto → postano SCARICO/CARICO.
* **Ordine di Lavoro** (ODL): il “completamento” o un’azione specifica (es. “prelievo materiale”, “consumo su impianto”) invoca il posting con causale “Uscita ODL”.
* **Trasferimenti interni**: documento dedicato → 2 movimenti (+/−).
* **Rettifiche/Inventari**: documento/azione → movimento di differenza.

> Nota: puoi implementarlo via **funzione di servizio** (richiamata dall’app all’evento giusto) oppure via **trigger** su tabelle operative: la funzione unica di posting resta il punto centrale.

---

# 2) Contatori/Asset vs Materiale di consumo

I **contatori** non sono “consumati”, ma **trasformano stato** (da stock a **asset installato**).

## 2.1 Registry Asset (contatori)

Introdurre (o riusare se esiste) uno **schema asset**:

* `asset.contatori` (o `utilities.contatori`): PK (seriale/UUID), modello/articolo collegato a `catalogo.articoli`, stato (`in_stock`, `assegnato`, `installato`, `rimosso`, `guasto`, `scartato`…), dati tecnici (classe, MID, firmware), ubicazione logica (impianto/PDP), date evento, meta/audit.
* `asset.eventi_contatore`: installazione, rimozione, sostituzione, rientro, test, calibrazione, rottamazione (con `sorgente_*` per tracciabilità).

## 2.2 Flusso tipico contatore

1. **Entrata** (acquisto) → `movimenti` **+** con `seriale` → contatore in **stock**.
2. **Prelievo/Assegnazione a ODL** → movimento **−** da magazzino centrale a **magazzino_furgone** o direttamente a **WIP/ODL**.
3. **Installazione** → **uscita** definitiva dallo stock verso lo **stato asset “installato”** (qui non “consumo”, ma **cambio di dominio**: dalla contabilità di magazzino alla **anagrafe asset**).
4. **Rimozione** → evento asset; se rientra fisicamente → **movimento +** in uno **stato/ubicazione** (es. “magazzino resi/guasti”) e stato asset aggiornato.

> Per i contatori, la **rilevanza è la serializzazione**: i movimenti devono **sempre** riportare `seriale`. Se l’articolo ha `requires_serial=true`, vincola il posting a richiedere il seriale.

---

# 3) Ordine di Lavoro (ODL) e magazzino

Per le utilities, il cuore operativo è l’**ODL** (intervento sul campo). Serve modellare **uscite materiali** e **installazioni asset** da ODL senza DDT.

## 3.1 Stati e “when post”

* **Richiesta materiale** → crea **prenotazione** (reservation) ma **non** posta.
* **Picking** per ODL → movimento **−** dal magazzino → **magazzino_furgone/WIP** (tracci la presa in carico).
* **Consumo su impianto** → movimento **−** da furgone/WIP → **consumo** (articoli consumabili) **oppure** “installazione asset” (uscita dal ledger + evento asset).
* **Resi da ODL** (materiale non usato) → movimento **+** di rientro al magazzino.

## 3.2 Magazzini speciali

* **Magazzino_furgone (tecnico)**: un magazzino per ciascun tecnico (o per team).
* **WIP/ODL**: ubicazione temporanea per materiale destinato a un ODL.
* **In-transit**: per trasferimenti intersede.

> Questi “magazzini virtuali” risolvono i buchi temporali e rendono **auditabile** chi ha la custodia del bene.

---

# 4) Prenotazioni (Reservations) e Disponibilità

Per ordini cliente **e** ODL, introduce **prenotazioni**:

* Tabella `magazzino.reservations` con: `articolo_id`, `magazzino_id` (se dedicato), quantità, `sorgente_*` (ordine/ODL), stato (`planned`, `picked`, `fulfilled`, `cancelled`).
* La **Disponibilità** = `Giacenza` − `Impegnato da vendite` − `Prenotato ODL` + `Ordinato`.
* Le viste suggerite:

  * `vw_magazzino_impegnato_vendite`
  * `vw_magazzino_prenotato_odl`
  * `vw_magazzino_ordinato_acquisti`
  * `vw_magazzino_giacenza` (da ledger)
  * `vw_magazzino_disponibile`

---

# 5) Collegamento con **Attività Fatturabili**

Hai già un **aggregatore** che convoglia fatturabili da **preventivi, ordini, contratti, ODL…**
Per **materiali/asset**:

* Ogni movimento da ODL o documento di servizio che comporti **addebito** deve:

  * avere un **flag “billable”** e il **riferimento tariffario** (listino/contratto/canone/voce tariffa),
  * essere **collegato** (1:1 o 1:N) a una riga del file **attività_fatturabili** (o a una staging table da cui lo generi).
* Per i **contatori installati**:

  * spesso l’addebito è una **quota** (nolo/canone) o una **prestazione** d’installazione → registra l’**evento asset** e crea la **riga fatturabile** della prestazione e/o del canone (non “consumo materiale”).
* Per i **consumabili su ODL**:

  * la riga di **consumo** può generare direttamente (o tramite regola) la **riga fatturabile** con quantità/prezzo.

> Suggerimento: una **tabella ponte** `fatturazione.fatturabili_sorgenti` che mappa `{sorgente_schema, sorgente_tabella, sorgente_id/riga}` → `{attivita_fatturabile_id}`, con **stato** (nuovo, consolidato, fatturato) e **idempotenza**.

---

# 6) Causali & Regole (policy)

Definisci **`magazzino.causali`** con attributi che guidano il posting:

* `segno` (+/−), **richiede lotto/seriale**, **richiede magazzino_dest** (per trasferimenti), **abilita billing** (si/no), **ambito** (vendite, acquisti, ODL, inventario), **impatto valorizzazione** (aggiorna CMP? sì sulle entrate).
* Questo ti permette **coerenza** e controlli preventivi (es. contatore senza seriale → errore).

---

# 7) Valorizzazione & Contabilità interna

* **CMP** come fase 1 (aggiornato alle ENTRATE).
* Le **USCITE** (DDT/ODL) prendono il costo corrente e lo fissano in `movimenti.costo_unitario`.
* Traccia **centro di costo** / **commessa** / **impianto** su riga movimento (soprattutto per ODL) per reporting e ribaltamenti.

---

# 8) KPI operativi per utilities

* **Rotazione** per classe materiali MRO.
* **Fill rate ODL**: % ODL completati senza stock-out.
* **Lead time materiale ODL**: richiesta → picking → consumo.
* **Tasso reso da ODL**: prelevato ma non usato.
* **Asset installati per periodo** (per modello/area), **tasso guasto/rientro**.

---

# 9) Riconciliazioni & Qualità dati

* **Idempotenza** rigorosa sui movimenti (chiavi sorgente).
* Report **“documenti senza posting”** (DDT chiusi/ODL completati privi di righe in ledger).
* Report **“posting orfani”** (movimenti privi di sorgente valida).
* **Coerenza seriali**: un seriale **non può** essere “in due posti” contemporaneamente (vincolo lato DB tra `movimenti` e stato asset).

---

# 10) Piccolo “blueprint” dei soli nuovi pezzi (nomi indicativi)

* `magazzino.movimenti` (ledger ufficiale).
* `magazzino.causali` (regole).
* `magazzino.reservations` (prenotazioni vendite/ODL).
* `magazzino.magazzini_tecnici` (o reuse `magazzini` con flag `is_furgone` + relazione tecnico).
* `asset.contatori` + `asset.eventi_contatore`.
* `fatturazione.fatturabili_sorgenti` (ponte verso “attività fatturabili”).
* Viste: `vw_giacenza`, `vw_disponibile`, `vw_impegnato_vendite`, `vw_prenotato_odl`, `vw_ordinato_acquisti`, `vw_kpi_*`.

> Tutti coerenti con i tuoi standard: `tx_id`, `storicizza`, `user_insert/update`, audit, naming.

---

## Conclusione

Con un **posting document-agnostic** verso `magazzino.movimenti`, l’introduzione di **magazzini speciali** (furgoni/WIP), e un **registro asset** per i contatori, riesci a:

* movimentare correttamente **anche senza DDT**,
* distinguere **consumo** da **installazione asset**,
* alimentare **attività fatturabili** in modo tracciabile,
* tenere **una sola verità** per giacenze/valori.

**Prossimi passi (se/quando vorrai):**

1. **mappa causali ↔ sorgenti** (ODL/DDT/Trasferimenti/Rettifiche) con regole operative,
2. **scheletro tabelle nuove** (solo colonne chiave, senza SQL),
3. elenco **eventi ODL** che scatenano posting e creazione delle **righe fatturabili**.
