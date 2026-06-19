## Documentazione Concettuale – Funzione `vendite.fn_list_emittibili_lane`

> **Vedi anche**
>
**Tabelle correlate:**
>
[vendite.commesse](/dbzero/vendite/tabelle/commesse),
[vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita),
[vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)
>
**Funzioni correlate:**
>
[vendite.fn_list_commesse_emittibili](/dbzero/vendite/funzioni/fn_list_commesse_emittibili),
[vendite.fn_select_attivita_fatturabili](/dbzero/vendite/funzioni/fn_select_attivita_fatturabili),
[vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa)

---
### 🎯 Scopo Principale
(latest review 19-06-2026 — discovery corsie per il driver batch)

La funzione **`vendite.fn_list_emittibili_lane`** è la **discovery delle corsie** per il
driver batch di fatturazione. Risponde a:

> «Per questa corsia/perimetro, quali **coppie distinte
> `(emittente_soggetto_ruolo_id, tipo_doc_fiscale_id)`** hanno lavoro pronto da fatturare,
> e **fino a quale `competenza_mese`** creare il lotto?»

Serve perché un **lotto** è identificato da `(emittente, tipo_doc_fiscale, competenza_mese)`
(tutti NOT NULL): il driver deve aprire **un lotto per ogni coppia** presente, altrimenti
le righe degli altri tipo_doc — pullate ma non catturate — resterebbero orfane
(fatturato perso in silenzio). È **separata** da `fn_list_commesse_emittibili` (che resta
la discovery per-commessa dello step di pull): qui si raggruppa per corsia, non per commessa.

---

### Parametri di input

| Parametro                       | Tipo                                                     | Default | Descrizione                                                        |
| ------------------------------- | -------------------------------------------------------- | ------- | ------------------------------------------------------------------ |
| `p_competenza_mese`             | `vendite.commesse_attivita.competenza_mese%TYPE`         | `NULL`  | **Limite superiore** della competenza (cumulativo, vedi sotto). NULL = nessun limite. |
| `p_billing_account_id`          | `vendite.commesse.billing_account_id%TYPE`               | `NULL`  | Filtro perimetro BA.                                               |
| `p_utility_id`                  | `vendite.commesse.utility_id%TYPE`                        | `NULL`  | Filtro perimetro utility.                                          |
| `p_emittente_soggetto_ruolo_id` | `vendite.commesse.emittente_soggetto_ruolo_id%TYPE`      | `NULL`  | Filtro perimetro emittente.                                       |
| `p_fatturazione_immediata`      | `vendite.commesse.fatturazione_immediata%TYPE`           | `NULL`  | Corsia: true=immediata / false=differita / NULL=indifferente.     |
| `p_limit`                       | `integer`                                                | `1000`  | Normalizzato (default 1000, max 10000); si applica alle **coppie**. |

---

### Output

`RETURNS TABLE(emittente_soggetto_ruolo_id, tipo_doc_fiscale_id, competenza_mese, total_candidate)`:

* **`competenza_mese`** = `max(competenza_mese)` fra le righe candidate della coppia → la
  competenza con cui il driver crea il lotto.
* **`total_candidate`** = numero di righe candidate (per dry-run/diagnostica).

---

### Criteri di inclusione (allineati alla pull e alla select)

1. Commessa in stato **emittibile** (`stati_commessa.emittibile = true`).
2. Righe `commesse_attivita` **`stato_approvazione = 'APPROVATA'` AND `stato_emissione =
   'NON_EMESSA'`** — allineato alla pull (`fn_emit_attivita_fatturabili_da_commessa` con
   `p_only_approved = true`). *Differenza* con `fn_list_commesse_emittibili`, che non filtra
   l'approvazione.
3. **`tipo_doc_fiscale_id IS NOT NULL`** (il lotto lo richiede NOT NULL; le righe con
   tipo_doc NULL sono escluse — il default si risolve all'upsert, non qui).
4. **Competenza cumulativa**: `competenza_mese <= p_competenza_mese` — coerente con
   `fn_select_attivita_fatturabili` (che filtra `<= v_competenza`). Così la discovery
   include gli **arretrati** (mesi precedenti) che la select poi cattura: nessun fatturato
   arretrato perso.
5. Filtri perimetro BA/utility/emittente; corsia `fatturazione_immediata`.

---

### Regole principali

* Funzione **STABLE** (read-only, nessun effetto collaterale).
* `LIMIT` sulle **coppie** (non sulle commesse).
* `fn_list_commesse_emittibili` resta separata e **invariata** (approccio A3).

---

### Esempio d'uso

```sql
-- corsia immediata, competenza fino a luglio 2026, un emittente specifico
SELECT * FROM vendite.fn_list_emittibili_lane(
  p_competenza_mese => DATE '2026-07-01',
  p_emittente_soggetto_ruolo_id => 55,
  p_fatturazione_immediata => true
);
-- -> (emittente, tipo_doc, competenza_mese=max, total_candidate) per ogni coppia
```

---

{% include-markdown "signature-core.md" %}
