## 📘 Documentazione Funzione – `pratiche.trgfn_flussi_guard_prerequisiti`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.fn_guard_prerequisiti_flusso](fn_guard_prerequisiti_flusso.md)
> [pratiche.fn_check_prerequisiti_flusso](fn_check_prerequisiti_flusso.md)
>
Tabelle:
>
[pratiche.flussi](flussi.md)
> [pratiche.template_flussi_prerequisiti](template_flussi_prerequisiti.md)

---

### 🎯 Scopo Principale

Trigger function wrapper per la guard prerequisiti. Si attiva **BEFORE INSERT** su `pratiche.flussi`: se il flusso ha un `template_flusso_id` valorizzato, delega la verifica a `fn_guard_prerequisiti_flusso`.

I flussi manuali (senza template, `template_flusso_id IS NULL`) bypassano il controllo.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_guard_prerequisiti()
RETURNS trigger
LANGUAGE plpgsql
```

---

### Logica

1. Se `NEW.template_flusso_id IS NOT NULL` → chiama `fn_guard_prerequisiti_flusso(NEW.pratica_id, NEW.template_flusso_id)`.
2. Se i prerequisiti non sono soddisfatti, la guard solleva eccezione e blocca l'INSERT.
3. Se `template_flusso_id IS NULL` → nessun controllo, RETURN NEW.

---

### Trigger associato

| Nome | Fase | Evento | Tabella |
|------|------|--------|---------|
| `trg_flussi_a10_guard_prerequisiti_ins` | BEFORE | INSERT | `pratiche.flussi` |

Fase `_a10_`: guard/block — esegue prima di qualsiasi altra logica.
