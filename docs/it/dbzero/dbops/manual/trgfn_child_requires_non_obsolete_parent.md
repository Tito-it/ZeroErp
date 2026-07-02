## 📘 Documentazione Concettuale – Funzione `dbops.trgfn_child_requires_non_obsolete_parent`

---

> 👀 **Vedi anche**
>
Approfondimento funzioni:
>
[`dbops.trgfn_child_requires_active_parent`](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent)
> [`dbops.fn_get_lookup_codici`](/dbzero/dbops/funzioni/fn_get_lookup_codici)
> [`dbops.trgfn_prevent_deactivate_if_children`](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children)

---

### 🎯 Scopo Principale
*(rev 2026-06-30 — brief-db-obsoleto-dal-filtro-lookup-e-guard, Obiettivo 2)*

La funzione **`dbops.trgfn_child_requires_non_obsolete_parent`** è una **trigger function**
che impedisce di **creare nuove istanze** (o di **ri-collegarle**) verso una voce di catalogo
**obsoleta**, cioè con `obsoleto_dal <= CURRENT_DATE`.

È la **gemella di `trgfn_child_requires_active_parent`** ma opera su un **asse diverso**:
non `attivo` (*"riferimento valido"*) bensì `obsoleto_dal` (*"selezionabile per il nuovo"*).
Serve proprio perché, per design, **una voce obsoleta resta `attivo = true`**: il guard
REQUIRE-ATTIVO non la intercetta, quindi senza questa funzione si potrebbe forzare via API la
creazione di una nuova istanza su un catalogo ormai ritirato.

È la **difesa in profondità** del pattern *"la UI nasconde, il DB rifiuta"*: la selezione la
nasconde (`fn_get_lookup_codici` con `p_includi_obsoleti = false`), questo guard la vieta.

---

### Dettagli

* **Firma**

  ```sql
  CREATE OR REPLACE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent()
  RETURNS trigger
  LANGUAGE plpgsql
  ```

* **Parametri (TG_ARGV)**

  1. `parent_schema` – schema della tabella catalogo (padre)
  2. `parent_table` – tabella catalogo (padre)
  3. `parent_obsoleto_col` – nome colonna `obsoleto_dal` del padre
  4. `fk_col` – colonna FK del figlio verso il padre
  5. *(opzionale)* `parent_ref_col` – colonna del padre referenziata dalla FK (default `id`;
     può essere una `UNIQUE` diversa dalla PK)

* **Logica interna**

  * Valida per `INSERT` e `UPDATE`.
  * Legge il valore della FK da `NEW` via `to_jsonb` (nessun `EXECUTE` per riga).
  * Se la FK è `NULL` → controllo **bypassato** (FK opzionale).
  * Su `UPDATE`, se la FK **non cambia** (`NEW` = `OLD`) → controllo **bypassato**: gli
    avanzamenti di lifecycle delle istanze storiche (cambio stato, ecc.) non ri-puntano il
    catalogo e **non vengono mai bloccati**.
  * Legge `obsoleto_dal` del padre (cast del parametro al tipo della colonna referenziata).
  * Blocca se `obsoleto_dal IS NOT NULL AND obsoleto_dal <= CURRENT_DATE`.
  * `obsoleto_dal NULL` o `> CURRENT_DATE` (ritiro programmato) → **consentito**.

* **Ritorno**: `trigger` → `NEW` (se i controlli sono superati).

* **Errore**: `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA` (id 500), template a un solo `%s`.

---

### Utilizzo tipico

Cablaggio **a mano** con un `CREATE TRIGGER` per relazione (Tier 2: cervello unico, fili
sottili). Timing **AFTER** in parallelo ai gemelli `*_require_attivo_*`, con `UPDATE OF <fk>`
per non scattare sugli update che non toccano la FK del catalogo:

```sql
CREATE TRIGGER trg_pratiche_a10_tipi_prestazione_require_non_obsoleto_ins_upd
AFTER INSERT OR UPDATE OF tipo_prestazione_id
ON pratiche.pratiche
FOR EACH ROW
EXECUTE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent(
  'pratiche', 'tipi_prestazione', 'obsoleto_dal', 'tipo_prestazione_id', 'id'
);
```

**Relazioni cablate** (al 2026-06-30):

| Figlio (istanza) | FK | Padre (catalogo) |
|---|---|---|
| `pratiche.pratiche` | `tipo_prestazione_id` | `pratiche.tipi_prestazione` |
| `pratiche.flussi` | `template_flusso_id` | `pratiche.template_flussi` |

Aggiungere un nuovo catalogo (es. `config.iva`) = **un altro `CREATE TRIGGER`**, zero logica
nuova. La generalizzazione in un framework config-driven (stile regola ATTIVO) è rinviata
finché i punti-guardia non diventano molti.

---

### Differenze rispetto a `trgfn_child_requires_active_parent`

| | `..._active_parent` (ATTIVO) | `..._non_obsolete_parent` (OBSOLETO) |
|---|---|---|
| Asse | `attivo` (riferimento valido) | `obsoleto_dal` (selezionabile per il nuovo) |
| Padre bloccante | `attivo = false` | `obsoleto_dal <= CURRENT_DATE` |
| Generazione | automatica (`fn_run_automations_attivo`) | **cablaggio manuale** per relazione |
| Skip su UPDATE | (controllo legato a `attivo` del figlio) | se la **FK non cambia** |

---

> **In sintesi**: `trgfn_child_requires_non_obsolete_parent` garantisce che **nuove** istanze
> non possano nascere (o essere ri-collegate) su un catalogo **ritirato**, lasciando intatte le
> istanze esistenti e i loro avanzamenti di stato.
