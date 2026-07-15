## 📘 Documentazione Concettuale – Funzione `vendite.fn_documento_lineage`

> 👀 **Vedi anche**
>
> Approfondimento:
>
> [vendite.vw_documento_lineage_archi](/dbzero/vendite/views/vw_documento_lineage_archi)
> [vendite.vw_documento_lineage](/dbzero/vendite/views/vw_documento_lineage)
> [vendite.vw_documento_lineage_nodi](/dbzero/vendite/views/vw_documento_lineage_nodi)

---

### 🎯 Scopo Principale

`vendite.fn_documento_lineage(p_tipo_id, p_uid, p_direzione)` è il **traversal ricorsivo**
del grafo di genealogia, pensato per il pannello **"Passaggi"** del dettaglio documento:
ritorna la **catena completa** degli archi attraversati, con lo stato di ogni tappa e
`livello`/`ordine` per il rendering a timeline/albero.

Sorgente unica: `vendite.vw_documento_lineage_archi` (tutti gli archi, incluso R).

---

### 📥 Input

| Parametro | Tipo | Significato |
|---|---|---|
| `p_tipo_id` | `bigint` | `config.sorgenti.id` del nodo di partenza (guard: NOT NULL, `> 0`) |
| `p_uid` | `text` | chiave nodo (secondo `key_selector`; guard: NOT NULL / non vuoto) |
| `p_direzione` | `text` | `avanti` (documento → destinazioni) o `indietro` (nodo → sorgenti); default `avanti` (guard: solo questi due valori) |

I guard sui parametri usano `script.fn_log_and_raise_error` con codice registrato
`ERRORE_PARAMETRI`.

---

### 📤 Output (`RETURNS TABLE`, una riga per arco)

* `livello` — profondità dal nodo di partenza (1 = adiacente)
* `ordine` — sequenza stabile per il rendering
* `arco`, `ruolo` — tipo di relazione (`A`..`H`/`R`) e ruolo `ROOT`/`COLLEGATO`
* `from_*`, `to_*` — estremi dell'arco + `to_stato_codice_interno`/`to_fase`/`to_is_abortito`
* `is_ramo_inverso` — `true` per l'arco **R** (DDT→Reso): il reso compare nei "Passaggi"
  come **ramo di ritorno**; il FE lo rende in modo distinto. La frontiera forward della
  summary lo esclude già.

---

### Esempio d'uso

```sql
-- AVANTI: da un preventivo alle sue destinazioni.
SELECT livello, ordine, arco, from_codice, to_codice, to_fase, is_ramo_inverso
FROM vendite.fn_documento_lineage(
     (SELECT id FROM config.sorgenti WHERE codice_interno = 'PREVENTIVO'),
     (SELECT uid::text FROM vendite.preventivi WHERE numero = 'PRV0000185'),
     'avanti')
ORDER BY ordine;

-- INDIETRO: da una commessa alle sue sorgenti (ROOT + COLLEGATO).
SELECT livello, arco, from_codice, to_codice, ruolo
FROM vendite.fn_documento_lineage(
     (SELECT id FROM config.sorgenti WHERE codice_interno = 'COMMESSA'),
     '186', 'indietro')
ORDER BY ordine;
```

---

### Note operative

* **`STABLE` · `SECURITY INVOKER`**: sola lettura; gira come il chiamante → la RLS
  emittente delle viste `security_invoker=on` resta applicata.
* **Cycle guard**: il traversal traccia i nodi visitati sul percorso e limita a
  `livello < 10` (le catene reali sono ≤ ~5 hop).
* **Direzioni**: `avanti` per le liste dei documenti, `indietro` per la lista commesse
  (genealogia inversa, G-11).
* Test: `db/pgtap/vendite/test-documento-lineage-v1.sql`.

---

{% include-markdown "signature-core.md" %}
