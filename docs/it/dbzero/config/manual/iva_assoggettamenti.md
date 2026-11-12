## 📘 Documentazione Concettuale – Tabella `config.iva_assoggettamenti`

> **Ultimo aggiornamento**: 13 novembre 2026

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [config.iva](/dbzero/config/tabelle/iva)    
> • [config.iva_stati](/dbzero/config/tabelle/iva_stati)   
> • [config.iva_natura](/dbzero/config/tabelle/iva_natura)    

---
### 🎯 Scopo Principale
`config.iva_assoggettamenti` è il **dominio** degli assoggettamenti IVA (causali/fattispecie: esente, non imponibile, reverse charge, fuori campo, ecc.).
Viene referenziato da `config.iva.assoggettamento_id` e, opzionalmente, da `config.iva_stati.assoggettamento_id_override`, consentendo di separare la **motivazione fiscale** dall’aliquota e dalla natura.

Obiettivi:

* Definire un **catalogo univoco e governato** di assoggettamenti.
* Evitare codici liberi nelle tabelle transazionali.
* Abilitare reporting/filtri per assoggettamento.

---

### Collocazione nel flusso

1. **Configurazione**: si censiscono i codici di assoggettamento (campo `codice`) con descrizione e stato `attivo`.
2. **Associazione**: `config.iva` collega un assoggettamento **di default**; `config.iva_stati` può definire un **override** per Paese.
3. **Utilizzo nei documenti**: i documenti **non** duplicano l’assoggettamento; fanno riferimento all’IVA (immutabile su aliquota/assoggettamento) e snapshot- tano **solo la natura** in riga.

---

### Campi chiave (semantica)

* `codice` (UNIQUE) → identificatore breve e stabile (es. `ES_ART10`, `NI_ART8`, `RC_ART17`, `FC`).
* `descrizione` → descrizione estesa del regime.
* `attivo` → abilita/disabilita in selezione.
* `note` → annotazioni operative/normative. Senza nota la colonna è `NULL`, mai la stringa
  vuota: il `CHECK` `chk_iva_assoggettamenti_note_non_vuota` rifiuta `''` e una stringa di
  soli spazi. Nel CSV del seed la cella senza nota porta il token `NULL`: lasciata vuota,
  il caricatore la scriverebbe come stringa vuota (linee-guida-sql §11.2). Dal pannello,
  svuotare la nota la salva `NULL` (`config.fn_pannello_scrivi`, dal 13 novembre 2026): prima
  il salvataggio veniva rifiutato dal `CHECK`.
* **Audit/Governance**: `data_*`, `user_*`, `storicizza`.

---

### Vincoli e indici

* **PK**: `id` (identity).
* **UNIQUE**: `uq_cfg_iva_assoggettamenti_codice` su `codice`.
* **CHECK**: `chk_iva_assoggettamenti_note_non_vuota` → l'assenza della nota è `NULL`.
* **Indici**:

  * `ix_cfg_iva_assoggettamenti_attivo` → filtri per stato attivo.

---

### Esempi d’uso (query applicative)

```sql
SELECT id, codice, descrizione
FROM config.iva_assoggettamenti
WHERE attivo
ORDER BY codice;
```

---

### Best practice operative

* **Codice breve e stabile**: usare sigle significative e non dipendenti dal linguaggio di stampa (che vive in `descrizione`).
* **Immutabilità logica**: se cambia la semantica di un assoggettamento, **inserire un nuovo codice** e disattivare il precedente (evita effetti retroattivi).
* **Allineamento con IVA**: tenere coerente l’uso:

  * `config.iva` con `aliquota_iva = 0` ⇒ richiede almeno **natura** o **assoggettamento**.
  * `config.iva` con `aliquota_iva > 0` ⇒ **nessun** assoggettamento (campo NULL).

---

### 📘 Note progettuali

* Il **dominio** degli assoggettamenti è **indipendente** dalla **natura**: nessun vincolo many-to-many obbligatorio. Se serve coerenza forte, può essere realizzata **a livello regola** (trigger/validazioni) o tramite una colonna facoltativa di “natura suggerita” nel dominio (non presente al momento).
* Gli utenti finali vedono il `codice` in selezione e la `descrizione` in tooltips/stampe; le regole applicative usano l’`id` per le FK.

---

### Ruolo nel sistema

`config.iva_assoggettamenti` fornisce una base solida per governare gli assoggettamenti IVA, riducendo la ridondanza e aumentando la **consistenza fiscale** tra configurazione, calcolo e documenti.
