## 📘 Documentazione Funzione – `pratiche.fn_stato_sorgente`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente)
> [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti)
> [config.sorgenti](/dbzero/config/tabelle/sorgenti)
> [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche)

---
### 🎯 Scopo Principale

API del **motore pratiche** per il **descrittore normalizzato** dello stato del documento
sorgente collegato (brief-db-proiezione-stato-dominio, deliverable D3). Dato
`(sorgente_tipo_id, sorgente_uid)` ritorna **sempre esattamente 1 riga**:

* la **proiezione del dominio** (`risolto=true`) se il tipo ha un resolver registrato in
  `script.vw_stato_sorgente` e il documento esiste;
* altrimenti la **sentinella `UNKNOWN`** (`risolto=false`, `stato_codice_interno='UNKNOWN'`,
  `stato_descrizione='n/d'`, `fase='APERTO'`, `esito=NULL`, `terminale=false`) **senza
  errore**: degrado con grazia, il milestone resta manuale come prima del roll-out.

Il motore ragiona **solo** su `fase`/`esito`/`terminale` normalizzati: non nomina mai uno
stato di dominio.

---

### Firma

```sql
CREATE FUNCTION pratiche.fn_stato_sorgente(
    p_sorgente_tipo_id config.sorgenti.id%TYPE,
    p_sorgente_uid     pratiche.pratiche_sorgenti.sorgente_uid%TYPE
)
RETURNS TABLE(
    sorgente_tipo_id     config.sorgenti.id%TYPE,
    sorgente_uid         pratiche.pratiche_sorgenti.sorgente_uid%TYPE,
    risolto              boolean,
    stato_codice_interno text,
    stato_codice         text,
    stato_descrizione    text,
    fase                 text,
    esito                text,
    terminale            boolean
)
LANGUAGE plpgsql STABLE
```

| Parametro | Obbligatorio | Descrizione |
|-----------|:---:|-------------|
| `p_sorgente_tipo_id` | SI | Tipo sorgente (`config.sorgenti.id`). Guard: NULL o ≤ 0 → `E_STATO_SORGENTE_PARAM_INVALIDO` (502) |
| `p_sorgente_uid` | SI | Chiave del documento come in `pratiche_sorgenti.sorgente_uid`. Guard: NULL o vuoto → idem |

Output = **descrittore universale** (contratto §4 del brief design). I campi descrittore
sono in `text`/`boolean` piani: il contratto è cross-dominio e il motore non deve dipendere
dai tipi delle tabelle di dominio (layering).

---

### Note operative

* **Un tipo valido ma senza resolver NON è un errore** → `UNKNOWN`. Idem per uid inesistente
  (documento cancellato / non ancora creato). L'errore parametri scatta solo su
  `tipo NULL/≤0` o `uid vuoto`.
* Il flag `risolto` distingue l'`APERTO` **reale** dal fallback: `fase='APERTO'` sulla
  sentinella serve solo al routing del motore; il consumer (BE/FE) usa `risolto` per il
  fallback UI (milestone manuale).
* **Wrapper scalare** su `script.vw_stato_sorgente`: unica superficie di dispatch, nessun
  dynamic SQL, nessun `resolver_key`.
* **Cerca per chiave nativa** (dal 2026-10-05): riconosce se `p_sorgente_uid` è un uuid o
  un intero e filtra su `sorgente_chiave_uuid` / `sorgente_chiave_id` della union, non sulla
  forma testuale. Così, sotto RLS, ogni ramo arriva all'indice invece di leggere l'intera
  tabella. La conversione sta nei building block
  [script.fn_sorgente_chiave_uuid](/dbzero/script/funzioni/fn_sorgente_chiave_uuid) e
  [script.fn_sorgente_chiave_id](/dbzero/script/funzioni/fn_sorgente_chiave_id). I risultati sono gli stessi del confronto testuale: vale solo la **forma
  canonica** della chiave (un uid in maiuscolo o un id con zeri davanti danno `UNKNOWN`,
  come prima) e una chiave malformata dà `UNKNOWN` senza errore.
* **Per le liste** con molte pratiche **non** chiamare questa funzione per-riga (N+1):
  joinare direttamente `script.vw_stato_sorgente`.
* Funzione `STABLE`, read-time: nessuna scrittura, nessun mirror di stato (il documento
  resta l'unica verità).
* Test: `db/pgtap/pratiche/test-proiezione-stato-sorgente.sql`.

---

### Esempio d'uso

```sql
-- Descrittore dello stato del documento collegato a una riga di pratiche_sorgenti.
SELECT d.*
  FROM pratiche.pratiche_sorgenti ps
 CROSS JOIN LATERAL pratiche.fn_stato_sorgente(ps.sorgente_tipo_id, ps.sorgente_uid) d
 WHERE ps.pratica_id = 42;

-- Preventivo EMESSO    -> risolto=t, fase=IN_ATTESA, esito=NULL,     terminale=f
-- Preventivo ACCETTATO -> risolto=t, fase=IN_CORSO,  esito=POSITIVO, terminale=f
-- Preventivo ANNULLATO -> risolto=t, fase=CHIUSO,    esito=NEGATIVO, terminale=t
-- Tipo senza resolver  -> risolto=f, fase=APERTO,    esito=NULL,     stato='UNKNOWN'
```

---

{% include-markdown "signature-core.md" %}
