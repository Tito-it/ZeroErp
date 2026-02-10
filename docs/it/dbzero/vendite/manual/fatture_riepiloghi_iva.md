## 📘 Documentazione Concettuale – Tabella `vendite.fatture_riepiloghi_iva`

> 👀 **Vedi anche**  
>
> **Approfondimento tabelle:**  
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)   
> • [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)   
> • [config.iva](/dbzero/config/tabelle/iva)    
> • [config.iva_natura](/dbzero/config/tabelle/iva_natura)   

---

### 🎯 Scopo Principale

`vendite.fatture_riepiloghi_iva` è lo **specchietto fiscale** della fattura: aggrega le righe per **combinazione fiscale** e ne memorizza i totali. Serve per:

* compilare correttamente il **riepilogo IVA** nei layout/stampe e nei flussi elettronici;
* garantire **tracciabilità** tra righe e somme per aliquota/natura/esigibilità/split;
* facilitare esportazioni contabili e controlli di coerenza.

Ogni riga rappresenta una combinazione di:

* `iva_id` (aliquota, opzionale),
* `natura_id` (opzionale),
* `esigibilita` ∈ {`I`,`D`,`S`},
* `split_payment` (boolean),
  con i relativi totali: `imponibile`, `imposta`, `arrotondamento`.

---

### 🧭 Collocazione nel flusso

1. **Calcolo righe** → ogni riga di fattura determina `imponibile_riga` e `imposta_riga`, oltre alla natura snapshot (nel campo `iva_natura` della riga).
2. **Raggruppamento** → il motore di emissione **collassa** le righe per chiavi fiscali e produce le righe di `fatture_riepiloghi_iva`.
3. **Verifica** → la somma dei riepiloghi deve combaciare con i totali della testata (`imponibile_tot`, `imposta_tot`) salvo differenze gestite in `arrotondamento`.
4. **Output** → i riepiloghi alimentano stampe, file elettronici e contabilizzazione.

> Nota: il calcolo dei riepiloghi assume che **`iva_id` sia gia` valorizzato**
> sulle righe fattura. La valorizzazione dell'IVA e` demandata al processo di
> generazione righe (Python).

---

### 🔑 Chiavi di raggruppamento (combinazione fiscale)

La **combinazione unica** per fattura è imposta dall’indice:
`(fattura_id, natura_id?, esigibilita, split_payment, iva_id?)`
(usa `COALESCE` per gestire i campi opzionali). In pratica:

* **Aliquota > 0**: ci si attende `natura_id = NULL` e `iva_id` valorizzato.
* **Aliquota = 0**: `iva_id` può essere NULL; si attende `natura_id` valorizzato (secondo le regole del tuo motore).
* **Esigibilità** e **split** fanno parte della chiave per gestire differimenti/split.

> Nota: la tabella **non impone** queste regole con CHECK; sono gestite a livello di calcolo/motore e dall’univocità della combinazione.

---

### 🧮 Logiche di calcolo (indicative)

* **Aggregazione**:
  `imponibile = Σ imponibile_riga`
  `imposta    = Σ imposta_riga`
  (somma delle righe che ricadono nella stessa combinazione).
* **Arrotondamento**:
  Differenze centesimali tra somma delle righe e importi teorici calcolati sulla base dell’aliquota possono essere riversate in `arrotondamento` **per combinazione**.
* **Allineamento con testata**:
  `Σ imponibile (tutte le combinazioni)` = `fatture.imponibile_tot`
  `Σ imposta (tutte le combinazioni)`    = `fatture.imposta_tot`
  `Σ arrotondamento` contribuisce ad `arrotondamento_attuale` in testata.

Esempio di calcolo (pseudocodice SQL):

```sql
INSERT INTO vendite.fatture_riepiloghi_iva (
  fattura_id, iva_id, natura_id, esigibilita, split_payment,
  imponibile, imposta, arrotondamento
)
SELECT
  r.fattura_id,
  r.iva_id,
  n.id AS natura_id,              -- derivata dal codice natura snapshot della riga
  r.esigibilita,
  r.split_payment,
  SUM(COALESCE(r.imponibile_riga,0)) AS imponibile,
  SUM(COALESCE(r.imposta_riga,0))    AS imposta,
  0::numeric                         AS arrotondamento
FROM vendite.fatture_righe r
LEFT JOIN config.iva_natura n
  ON n.codice = r.iva_natura           -- mapping dal codice snapshot alla dimensione master
WHERE r.fattura_id = :fattura_id
GROUP BY r.fattura_id, r.iva_id, n.id, r.esigibilita, r.split_payment;
```

---

### 🔒 Vincoli e indici

* **PK**: `id` (identity).
* **FK**:

  * `fattura_id` → `vendite.fatture(id)` (CASCADE ON DELETE).
  * `iva_id` → `config.iva(id)` (opzionale).
  * `natura_id` → `config.iva_natura(id)` (opzionale).
* **CHECK**: `esigibilita ∈ {I,D,S}`.
* **UNIQUE**: `uq_fatture_r_iva_key` su `(fattura_id, natura_id?, esigibilita, split, iva_id?)` per evitare duplicati della stessa combinazione.

---

### 🧪 Esempi d’uso (query applicative)

```sql
-- 1) Riepilogo fattura pronto per stampa/trasmissione
SELECT r.*, i.aliquota_iva, n.codice AS natura
FROM vendite.fatture_riepiloghi_iva r
LEFT JOIN config.iva i ON i.id = r.iva_id
LEFT JOIN config.iva_natura n ON n.id = r.natura_id
WHERE r.fattura_id = :fattura_id
ORDER BY COALESCE(n.codice, 'ZZZ'), COALESCE(i.aliquota_iva, 0);

-- 2) Controllo coerenza con testata
SELECT
  SUM(imponibile) AS imponibile_riep,
  SUM(imposta)    AS imposta_riep
FROM vendite.fatture_riepiloghi_iva
WHERE fattura_id = :fattura_id;
```

---

### ✅ Best practice operative

* **Origine dati**: i riepiloghi devono essere **rigenerati** ogni volta che cambiano righe/aliquote/nature, prima della numerazione.
* **Arrotondamenti**: applicare regole coerenti con le **policy di arrotondamento** del sistema (metodo/decimali) e con quanto riportato in testata.
* **Natura**: quando l’aliquota è 0, assicurarsi che la natura sia presente (derivando dal codice snapshot in riga).
* **Esigibilità/Split**: includerle nella chiave per separare correttamente i conteggi differiti o in split payment.

---

### 📘 Note progettuali

* La tabella memorizza **totali** per combinazione; non è pensata per tenere lo **snapshot per-riga** (che risiede in `vendite.fatture_righe`).
* In un modello dove **aliquota e assoggettamento sono immutabili** a livello `config.iva`, è sufficiente referenziare `iva_id`; per la **natura** si consiglia di partire dal **codice snapshot** in riga e risalire all’`id` della dimensione.
* Valuta un **processo idempotente** di “ricostruzione riepilogo” che prima `DELETE` le righe della fattura e poi `INSERT` l’aggregato corrente.

---

### 👓 Ruolo nel sistema

`vendite.fatture_riepiloghi_iva` è il ponte tra **dettaglio** e **fiscalità**: rende esplicite le combinazioni IVA applicate, supporta **stampe, e-billing e contabilità**, e assicura che i totali fiscali siano **ricostruibili e verificabili** rispetto alle righe documento.
