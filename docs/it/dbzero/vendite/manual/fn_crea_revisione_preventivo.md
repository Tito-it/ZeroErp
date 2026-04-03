## 📘 Documentazione Concettuale – Funzione `vendite.fn_crea_revisione_preventivo(...)`

> 👀 **Vedi anche**
>
[vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)
> [vendite.preventivi_indirizzi](/dbzero/vendite/tabelle/preventivi_indirizzi)
> [vendite.fn_ricalcola_totali_preventivo](/dbzero/vendite/funzioni/fn_ricalcola_totali_preventivo)

---
### 🎯 Scopo Principale
(latest review 03-04-2026)
`vendite.fn_crea_revisione_preventivo(p_preventivo_id, p_user)` crea una **nuova revisione**
di un preventivo vendita: copia testata, righe attive e indirizzi, disattivando la
revisione corrente.

---

### Regole principali

* **Stato ammesso**: solo preventivi in stato EMESSO o ACCETTATO.
* **No DRAFT esistente**: non deve esistere gia' una revisione in DRAFT per lo stesso numero.
* **Guard stato DRAFT**: se lo stato DRAFT non e' configurato/attivo in `config.stati_doc_preventivi`,
  errore esplicito `E_CONFIG_MANCANTE` (non fallisce con FK generico).
* La revisione corrente viene disattivata (`is_revision_attiva = false`).
* La nuova revisione ha `rev = max(rev) + 1`, `is_revision_attiva = true`, stato DRAFT.
* **Righe copiate**: solo attive con `quantita > 0`.
* **Indirizzi**: tutti copiati.

---

### Ottimizzazioni

* **Totali a 0**: la nuova testata viene creata con `totale_imponibile = 0, totale_iva = 0,
  totale_documento = 0`. I totali corretti vengono ricalcolati automaticamente dal trigger
  STATEMENT su `preventivi_righe` dopo l'INSERT bulk delle righe copiate.
  Questo evita di copiare totali che verrebbero immediatamente sovrascritti.

---

### Parametri

| Parametro | Tipo | Note |
|-----------|------|------|
| `p_preventivo_id` | `vendite.preventivi.id%TYPE` | ID del preventivo da revisionare. Obbligatorio, > 0. |
| `p_user` | `vendite.preventivi.user_update%TYPE` | Utente che esegue l'operazione. |

---

### 📦 Output

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `nuovo_preventivo_id` | bigint | ID della nuova revisione |
| `numero` | varchar | Numero del preventivo (invariato) |
| `nuova_rev` | integer | Numero di revisione assegnato |

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `PREV_REVISIONE_STATO_NON_AMMESSO` | Stato corrente non e' EMESSO ne' ACCETTATO |
| `PREV_REVISIONE_BOZZA_ESISTENTE` | Esiste gia' una revisione DRAFT per lo stesso numero |
| `PREV_STATO_CORRENTE_NON_TROVATO` | Preventivo non trovato |
| `E_CONFIG_MANCANTE` | Stato DRAFT non configurato/attivo in config.stati_doc_preventivi |
| `E_PARAMETRO_INVALIDO` | p_preventivo_id NULL o <= 0 |

---

### Esempio d'uso

```sql
-- Crea revisione di un preventivo emesso
SELECT * FROM vendite.fn_crea_revisione_preventivo(42, 'operatore1');
-- Restituisce: nuovo_preventivo_id=99, numero='PREV-2026-001', nuova_rev=2
```

---

{% include-markdown "signature-core.md" %}
