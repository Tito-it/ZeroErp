## 📘 Documentazione Funzione – `pratiche.fn_check_chiusura_pratica`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi)
> [pratiche.template_flussi_prerequisiti](/dbzero/pratiche/tabelle/template_flussi_prerequisiti)
> [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)
>
Funzioni collegate:
>
[pratiche.fn_check_prerequisiti_flusso](fn_check_prerequisiti_flusso.md)
> [pratiche.trgfn_pratiche_guard_chiusura_flussi](trgfn_pratiche_guard_chiusura_flussi.md)

---
### 🎯 Scopo Principale
La funzione **`pratiche.fn_check_chiusura_pratica`** e' una **pure check** (`fn_check_*`) che fotografa i template flusso della pratica ai fini della **chiusura** (decisione D4, analisi-pratiche-workflow-v2): per ogni template attivo della **definizione pinnata** della pratica (`definizione_id`, **fork-aware**) dice se e' stato eseguito, se e' ancora percorribile e se **blocca** la transizione a `CHIUSA`.

E' anche la fonte BE per la **resa del percorso a bivi**: da `completato`/`percorribile` si deriva lo stato visuale di ogni step (completato / eseguibile / **ramo chiuso**).

---

### Firma della funzione

```sql
CREATE FUNCTION pratiche.fn_check_chiusura_pratica(
  p_pratica_id pratiche.flussi.pratica_id%TYPE
)
RETURNS TABLE(
  template_flusso_id pratiche.template_flussi.id%TYPE,
  codice             pratiche.template_flussi.codice%TYPE,
  obbligatorio       pratiche.template_flussi.obbligatorio%TYPE,
  completato         boolean,
  percorribile       boolean,
  bloccante          boolean
)
LANGUAGE plpgsql
STABLE
```

---

### Colonne ritornate

| Colonna | Descrizione |
|---------|-------------|
| `completato` | Esiste un'istanza `COMPLETATO` (**qualsiasi esito**: uno step eseguito con esito NEGATIVO e' comunque stato fatto) |
| `percorribile` | Tutti i prerequisiti del template sono soddisfatti (esito-aware, via `fn_check_prerequisiti_flusso`). Il **ramo morto** di un bivio (esito del predecessore opposto a quello richiesto) risulta `false` |
| `bloccante` | `obbligatorio AND NOT completato AND percorribile` — blocca la chiusura |

---

### Semantica di chiusura (D4)

* **"Obbligatorio" vincola la chiusura solo se il suo percorso e' attivabile.**
* Il ramo morto di un bivio non blocca mai (`percorribile = false`).
* Uno step a valle di un predecessore non eseguito non blocca: se il predecessore e' a sua volta obbligatorio, blocca gia' lui.

---

### Esempi di utilizzo

```sql
-- Cosa impedisce di chiudere la pratica 100?
SELECT codice FROM pratiche.fn_check_chiusura_pratica(100) WHERE bloccante;

-- Resa del percorso a bivi (BE): stato visuale per step
SELECT codice,
       CASE WHEN completato THEN 'COMPLETATO'
            WHEN percorribile THEN 'ESEGUIBILE'
            ELSE 'RAMO_CHIUSO' END AS stato_visuale
  FROM pratiche.fn_check_chiusura_pratica(100);
```

---

### Note operative

* Consumata da `trgfn_pratiche_guard_chiusura_flussi` (guard sulla transizione a CHIUSA), da `fn_check_pratica_chiudibile` (delega per il predicato "nessun obbligatorio bloccante", quindi anche auto-chiusura e guard pre-completamento) e dal percorso BE.
* **Fork-aware** (`20260703-13`, completamento Fase 1): scopa i template per `definizione_id` pinnata, **non** per `tipo_prestazione_id`. Con i fork (Fase 2) piu' definizioni condividono il tipo: una pratica considera solo gli step della **sua** edizione. Con una definizione per tipo il comportamento e' identico a prima.
* Le istanze `ANNULLATO` non contano come eseguite.
* Test: `db/pgtap/pratiche/test-bivi-condizionali.sql`, `db/pgtap/pratiche/test-fork-chiusura-per-definizione.sql`.
