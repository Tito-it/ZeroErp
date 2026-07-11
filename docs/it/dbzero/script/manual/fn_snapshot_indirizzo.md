## 📘 Documentazione Concettuale – `script.fn_snapshot_indirizzo`

Fonte **unica lato server** dello snapshot indirizzo (decisione D-5 del brief
indirizzi-documenti, 2026-07-11). Dato `p_indirizzo_id`
(`anagrafiche.indirizzi.id`), compone il JSONB canonico leggendo il resolver
`anagrafiche.vw_indirizzi_resolved_ruolo`.

### Firma

```sql
script.fn_snapshot_indirizzo(p_indirizzo_id bigint)
RETURNS TABLE (snapshot jsonb, origine_soggetto_ruolo_id bigint)  -- STABLE
```

- `snapshot`: il JSONB canonico (sotto).
- `origine_soggetto_ruolo_id`: il ruolo di provenienza, così l'endpoint BE
  valorizza `origine_*` senza una seconda query.

### Chi la usa

- **Endpoint BE upsert indirizzi** (flusso *picker*): il client manda solo
  `{tipo_indirizzo_id, origine_indirizzo_id}`, il BE chiama questa funzione e
  congela `snapshot` + `origine_*`.
- **NON** la usano le funzioni di push/cascata: quelle copiano lo snapshot
  **1:1 già congelato** (freeze semantico + supporto indirizzo una-tantum).

### Shape canonico

Etichette umane + `display`. Le chiavi nulle vengono omesse
(`jsonb_strip_nulls`).

```json
{
  "intestazione": "ragione sociale completa del soggetto",
  "via":          "via + civico (normalizzato) oppure indirizzo libero",
  "cap":          "…",
  "citta":        "descrizione comune",
  "prov":         "sigla provincia",
  "stato":        "ISO2",
  "display":      "stringa human-readable pronta per la UI/PDF"
}
```

I campi di contatto (`email`, `telefono`, `note`) **non** sono prodotti dalla
funzione: li aggiunge il BE oppure il form indirizzo *una-tantum* (D-4).

### Errori

- `E_VALIDAZIONE` — `p_indirizzo_id` nullo o `<= 0`.
- `E_INDIRIZZO_SNAPSHOT_NOT_FOUND` — indirizzo inesistente o non risolvibile.
