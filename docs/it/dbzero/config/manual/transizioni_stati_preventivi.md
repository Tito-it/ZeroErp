## 📘 Documentazione Concettuale – Tabella `config.transizioni_stati_preventivi`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[config.stati_doc_preventivi](/dbzero/config/tabelle/stati_doc_preventivi)
> [config.transizioni_stati_pratiche](/dbzero/config/tabelle/transizioni_stati_pratiche)
> [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
>
Approfondimento funzioni:
>
[vendite.fn_cambia_stato_preventivo](/dbzero/vendite/funzioni/fn_cambia_stato_preventivo)

---
### 🎯 Scopo Principale
(latest review 03-04-2026)
`config.transizioni_stati_preventivi` definisce la **matrice delle transizioni ammesse**
tra gli stati del preventivo vendita. Pattern identico a `config.transizioni_stati_pratiche`.

La funzione `vendite.fn_cambia_stato_preventivo` consulta questa tabella per validare
ogni transizione di stato, rendendo le regole configurabili senza rilasciare codice.

---

### Matrice transizioni configurata

| id | Da | A | Descrizione |
|----|----|---|-------------|
| 1 | DRAFT (1) | EMESSO (2) | Emissione preventivo |
| 2 | DRAFT (1) | ANNULLATO (9) | Cancellazione bozza |
| 3 | EMESSO (2) | ACCETTATO (4) | Accettazione cliente |
| 4 | EMESSO (2) | RIFIUTATO (5) | Rifiuto cliente |
| 5 | EMESSO (2) | SCADUTO (7) | Scadenza validita' |
| 6 | EMESSO (2) | ANNULLATO (9) | Annullamento operatore |
| 7 | ACCETTATO (4) | ANNULLATO (9) | Annullamento post-accettazione |

```
DRAFT ---------> EMESSO ---------> ACCETTATO ---------> (push commessa / genera pratica)
  |                |                   |
  |                |                   +-> ANNULLATO (guard commessa attiva)
  |                +-> RIFIUTATO
  |                +-> SCADUTO
  |                +-> ANNULLATO
  +-> ANNULLATO
```

---

### Vincoli

| Vincolo | Tipo | Descrizione |
|---------|------|-------------|
| `uq_transizioni_stati_preventivi` | UNIQUE | `(stato_da_id, stato_a_id)` — una sola regola per coppia |
| `ck_transizioni_stati_prev_da_diverso_a` | CHECK | Lo stato di partenza deve essere diverso da quello di arrivo |

---

### Regole operative

* **Attivo**: il flag `attivo` consente di disabilitare una transizione senza eliminarla.
* **Guard aggiuntivi**: la funzione `fn_cambia_stato_preventivo` applica guard supplementari
  non gestibili dalla sola matrice (es. righe attive per emissione, commessa attiva per annullamento).
* **Estensibilita'**: il campo `meta` JSONB consente future estensioni (es. `richiede_conferma`, `note_ui`).

---

### Esempio d'uso

```sql
-- Transizioni ammesse dallo stato corrente di un preventivo
SELECT sdp_a.codice AS stato_destinazione, sdp_a.descrizione
FROM config.transizioni_stati_preventivi t
JOIN config.stati_doc_preventivi sdp_a ON sdp_a.id = t.stato_a_id
WHERE t.stato_da_id = (SELECT stato_doc_preventivo_id FROM vendite.preventivi WHERE id = 42)
  AND t.attivo IS TRUE;
```

---

{% include-markdown "signature-core.md" %}
