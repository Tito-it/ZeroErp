## 📘 Documentazione Concettuale – Funzione `config.fn_get_iva_override`

> 👀 **Vedi anche**      
>   
Approfondimento Tabelle:  
> 
[config.iva](/dbzero/config/tabelle/iva)      
> [config.iva_stati](/dbzero/config/tabelle/iva_stati)      

La funzione **`config.fn_get_iva_override(p_codice_iva TEXT, p_stato_id INTEGER)`** restituisce i dati completi della aliquota IVA (codice, descrizioni, natura, conti) per un determinato codice IVA e Stato, applicando eventuali override specifici per Stato definiti in `config.iva_stati`.

---

### 🎯 Scopo Principale

* **Recupero unificato**
  Ottenere in un’unica chiamata sia i valori base da `config.iva` sia gli override da `config.iva_stati` se presenti.
* **Override per Stato**
  Consentire di modificare aliquota e assoggettamento IVA a livello di Stato senza duplicare righe in `config.iva`.
* **Centralizzazione**
  Incapsulare la logica di join e COALESCE in una funzione riutilizzabile.

---

### Parametri di Input

| Nome           | Tipo   | Descrizione                                            |
| -------------- | ------ | ------------------------------------------------------ |
| `p_codice_iva` | `TEXT` | Codice identificativo dell’IVA (es. 'IVA22', 'IVA10'). |
| `p_stato_id`   | `INT`  | ID dello Stato (chiave esterna su `config.stati.id`).  |

---

### Flusso Logico

1. **Join su tabella base**
   Seleziona i campi da `config.iva` per il record con `codice_iva = p_codice_iva`, e unisce a `config.stati` per validare `p_stato_id`.
2. **Left join per override**
   Unisce `config.iva_stati` su `(iva_id, stato_id)` per recuperare gli eventuali valori di `aliquota_override` e `assoggettamento_override`.
3. **Applicazione override o default**
   Usa `COALESCE` per restituire:

   * `aliquota = COALESCE(s.aliquota_override, i.aliquota_iva)`
   * `assoggettamento = COALESCE(s.assoggettamento_override, i.assoggettamento_iva)`
4. **Restituzione tabella**
   Ritorna la tabella con colonne dettagliate: dati base, override, natura, conti e metadati di audit.

---

### 🔖 Firma SQL

```sql
CREATE OR REPLACE FUNCTION config.fn_get_iva_override(
  p_codice_iva TEXT,
  p_stato_id   INTEGER
)
RETURNS TABLE(
  id_iva                INTEGER,
  codice_iva            CHARACTER,
  desc_iva              VARCHAR,
  desc_breve_iva        VARCHAR,
  aliquota_base         NUMERIC,
  assoggettamento_base  CHAR,
  aliquota              NUMERIC,
  assoggettamento       CHAR,
  id_natura_iva         INTEGER,
  conto_iva_acquisti_id INTEGER,
  conto_iva_vendita_id  INTEGER,
  stato_id              INTEGER,
  stato_sigla           VARCHAR,
  data_insert           TIMESTAMP,
  user_insert           TEXT,
  data_update           TIMESTAMP,
  user_update           TEXT
)
LANGUAGE sql
AS $body$
  /* Implementazione: join su config.iva, config.stati, config.iva_stati; COALESCE per override */
  SELECT ...
$body$;
```

---

### Esempio di Utilizzo

```sql
SELECT *
  FROM config.fn_get_iva_override('IVA22', 1);
-- Restituisce la riga IVA 22% per lo Stato con id=1, applicando eventuali override.
```

---

### Vantaggi Operativi

* **Semplicità**: un’unica funzione per gestire base e override.
* **Manutenibilità**: cambiamenti agli override si propagano automaticamente al risultato.
* **Performance**: il linguaggio SQL nativo con COST=100 e STABLE è ottimizzato per uso frequente.
* **Coerenza**: evita duplicazioni di logica in più punti dell’applicazione.

---

> **“Centralizzare la logica di override IVA in una funzione SQL migliora chiarezza, riuso e governabilità delle regole fiscali.”**
