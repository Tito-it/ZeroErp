## 📘 Documentazione Concettuale – Funzione `vendite.fn_cambia_stato_preventivo(...)`

> 👀 **Vedi anche**
>
[vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi)
> [config.transizioni_stati_preventivi](/dbzero/config/tabelle/transizioni_stati_preventivi)
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)

---
### 🎯 Scopo Principale
(latest review 03-04-2026)
`vendite.fn_cambia_stato_preventivo(p_preventivo_id, p_nuovo_stato, p_user)` esegue
la **transizione di stato** di un preventivo vendita, validando la transizione tramite
la matrice configurabile `config.transizioni_stati_preventivi`.

---

### Regole principali

* La transizione deve essere presente e attiva nella matrice `config.transizioni_stati_preventivi`.
* **Guard DRAFT → EMESSO**: richiede almeno una riga attiva con `quantita > 0` e `totale_documento > 0`.
* **Guard → ANNULLATO**: blocco duro se il preventivo ha righe gia' inviate in commessa
  (`commesse_attivita` con `stato_emissione = 'EMESSA'`).
* Parametri ID validati esplicitamente (NULL e <= 0 rifiutati).

---

### Ottimizzazioni

* **Singola query iniziale**: stato corrente, numero e `uid` caricati in una sola SELECT
  (evita ri-lettura di `preventivi` nel guard ANNULLATO).
* **`starts_with()` (PG 18)**: il guard commessa usa `starts_with(ca.segment_key, 'PREV:' || uid || ':R:')`
  al posto di `LIKE ... '%'`. Piu' index-friendly su B-Tree.

---

### Parametri

| Parametro | Tipo | Note |
|-----------|------|------|
| `p_preventivo_id` | `vendite.preventivi.id%TYPE` | ID del preventivo. Obbligatorio, > 0. |
| `p_nuovo_stato` | `config.stati_doc_preventivi.codice%TYPE` | Codice stato destinazione (es. 'EMESSO'). |
| `p_user` | `vendite.preventivi.user_update%TYPE` | Utente che esegue la transizione. |

---

### 📦 Output

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `preventivo_id` | bigint | ID del preventivo |
| `stato_precedente` | varchar | Codice stato prima della transizione |
| `stato_nuovo` | varchar | Codice stato dopo la transizione |

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `PREV_TRANSIZIONE_NON_AMMESSA` | Transizione non in matrice o non attiva |
| `PREV_NESSUNA_RIGA_ATTIVA` | DRAFT → EMESSO senza righe attive |
| `PREV_TOTALE_NON_POSITIVO` | DRAFT → EMESSO con totale <= 0 |
| `PREV_ANNULLAMENTO_COMMESSA_ATTIVA` | Verso ANNULLATO con righe in commessa |
| `PREV_STATO_CORRENTE_NON_TROVATO` | Preventivo o stato non trovato |
| `E_STATO_SCONOSCIUTO` | Codice stato destinazione non trovato/non attivo |
| `E_PARAMETRO_INVALIDO` | p_preventivo_id NULL o <= 0 |

---

### Esempio d'uso

```sql
-- Emissione preventivo
SELECT * FROM vendite.fn_cambia_stato_preventivo(42, 'EMESSO', 'operatore1');

-- Accettazione
SELECT * FROM vendite.fn_cambia_stato_preventivo(42, 'ACCETTATO', 'operatore1');
```

---

{% include-markdown "signature-core.md" %}
