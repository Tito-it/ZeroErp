## 📘 Documentazione Funzione – `pratiche.fn_reconcile_sorgente`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.fn_stato_sorgente](/dbzero/pratiche/funzioni/fn_stato_sorgente)
> [pratiche.trgfn_documento_reconcile_proiezione](/dbzero/pratiche/funzioni/trgfn_documento_reconcile_proiezione)
> [pratiche.template_flussi_avanzamento_proiezione](/dbzero/pratiche/tabelle/template_flussi_avanzamento_proiezione)
> [pratiche.reconcile_errori](/dbzero/pratiche/tabelle/reconcile_errori)

---
### 🎯 Scopo Principale
(review 06-07-2026 — GUIDA D4, brief-db-guida-avanza-esito-proiettato)

**Motore di avanzamento del milestone su esito proiettato** (`G3a`). Quando il documento
`(tipo, uid)` proietta un **verdetto** (`fn_stato_sorgente.esito` non-null), completa i
milestone della/e pratica/e che lo **attendono** — su **qualsiasi** percorso di scrittura del
documento (BE, batch, SQL diretto e soprattutto **standalone**). Generalizza e rimpiazza
l'handler per-dominio `vendita.accetta_preventivo`.

Replica l'effetto del building block BE `completa_step_pratica` (che, essendo Python, **non è
richiamabile da un trigger DB**): transizione a **COMPLETATO** con il verdetto proiettato →
fa scattare `pratiche.trgfn_flussi_generazione` (generazione a valle) come il completamento
manuale. Ritorna il **numero di milestone avanzati**.

---

### Firma

```sql
CREATE FUNCTION pratiche.fn_reconcile_sorgente(
    p_sorgente_tipo_id pratiche.pratiche_sorgenti.sorgente_tipo_id%TYPE,
    p_sorgente_uid     pratiche.pratiche_sorgenti.sorgente_uid%TYPE
) RETURNS integer
LANGUAGE plpgsql
-- SECURITY INVOKER (default)
```

| Parametro | Obbligatorio | Descrizione |
|-----------|:---:|-------------|
| `p_sorgente_tipo_id` | SI | Tipo sorgente (`config.sorgenti.id`). Guard: NULL o ≤ 0 → `E_PARAMETRO_INVALIDO`. |
| `p_sorgente_uid` | SI | UID del documento. Guard: NULL o vuoto → `E_PARAMETRO_INVALIDO`. |

---

### Comportamento (regole)

* **No-op senza aggancio** (rev 2026-10-05): se il documento non è collegato a nessuna pratica
  (nessuna riga visibile di `pratiche_sorgenti` su tipo e uid) → ritorna 0 **prima** di
  leggerne lo stato. Il risultato sarebbe 0 comunque; il controllo viene prima perché leggere lo
  stato di un documento costa molto più che cercarne gli agganci, e il trigger chiama questa
  funzione a ogni cambio di stato, anche dei documenti che non stanno in nessuna pratica.
* **No-op senza verdetto** (D): se `fn_stato_sorgente.esito IS NULL` (es. EMESSO) → ritorna 0.
* **Due salti** (D-B2): la matrice transizioni **non** ammette `DA_ESEGUIRE→COMPLETATO` diretta;
  se il milestone è `DA_ESEGUIRE` passa da `IN_CORSO`, poi `COMPLETATO` (come il BE
  `avvia_e_completa`).
* **Idempotenza** (D-B11): agisce **solo** sui flussi **non terminali**
  (`stato NOT IN COMPLETATO/ANNULLATO`). Reconcile ripetuti sono innocui.
* **Tie-break multi-istanza** (D-B5): se `pratiche_sorgenti.flusso_id` è valorizzato agisce
  **su quel flusso**; se NULL e i milestone candidati del tipo sono **più di uno** → **skip +
  log** su `pratiche.reconcile_errori` (`E_RECONCILE_AMBIGUO`), non indovina.
* **INVOKER** (D-B4): `pratiche.flussi`/`giornale` non hanno RLS; gira nella transazione
  dell'operatore già scoped sul documento → l'audit resta veritiero (chi ha accettato è chi
  ha innescato l'avanzamento). Nessun contesto SISTEMA.

---

### Note operative

* La funzione **può sollevare** (guard parametri, o un guard di dominio sul completamento): è
  il **trigger** `trgfn_documento_reconcile_proiezione` che la avvolge in `EXCEPTION` per la
  sovranità del documento. Invocata direttamente (BE/batch), gestire l'errore a monte.
* Il giornale del cambio-stato del milestone è scritto automaticamente da
  `pratiche.trgfn_flussi_giornale_stato` (contesto operatore): il reconcile **non** scrive un
  evento `DOMINIO_*` dedicato.
* Test: `db/pgtap/pratiche/test-guida-avanza-esito-proiettato.sql`.

---

### Esempio d'uso

```sql
-- Riconcilia i milestone in attesa del verdetto di un preventivo (tipo 2 = PREVENTIVO).
SELECT pratiche.fn_reconcile_sorgente(2, '550e8400-e29b-41d4-a716-446655440000');
-- Ritorna il numero di milestone portati a COMPLETATO con il verdetto proiettato.
```

---

{% include-markdown "signature-core.md" %}
