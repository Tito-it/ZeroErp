## 📘 Documentazione Concettuale – Tabella `ui.lista_preset`

> 👀 **Vedi anche**
>
> [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione)
> [ui.lista_preset_colonna](/dbzero/ui/tabelle/lista_preset_colonna)
> [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente)
> [config.profili_accesso](/dbzero/config/tabelle/profili_accesso)
>
> Funzione:
>
> [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config)

La tabella **`ui.lista_preset`** contiene le **configurazioni predefinite per le liste** a tre livelli gerarchici. Definisce l'aspetto di default di una lista per l'intero sistema, per una specifica società (emittente fiscale) o per un profilo di accesso.

---

### 🎯 Scopo Principale

* **Configurazione multi-livello**: un preset può essere di sistema (default globale), di emittente fiscale (override per società) o di ruolo (override per profilo di accesso). La cascata di risoluzione è gestita da `fn_resolve_lista_config`.
* **Preset di default**: il flag `is_default = TRUE` indica quale preset applicare automaticamente per un dato livello. Il UNIQUE INDEX parziale su `is_default = TRUE` garantisce un unico preset di default per combinazione `(lista, ambito, profilo, emittente)`.
* **Configurazione completa**: il preset non definisce solo le colonne (in `lista_preset_colonna`) ma anche ordinamento di default (`ordinamento_default` JSONB), filtri preimpostati (`filtri_default` JSONB) e dimensione pagina (`pagina_dimensione`: una misura del catalogo [ui.misure_pagina](/dbzero/ui/tabelle/misure_pagina), o vuota per il default; una misura fuori catalogo viene rifiutata).

---

### Livelli di `ambito`

| Valore | Descrizione | Campo valorizzato |
|--------|-------------|-------------------|
| `sistema` | Default globale per tutti gli utenti | nessuno |
| `emittente_fiscale` | Override per una specifica società | `emittente_fiscale_id` |
| `ruolo` | Override per un profilo di accesso | `profilo_accesso_id` |

Il CHECK constraint `chk_ui_lista_preset_ambito_refs` garantisce la coerenza: solo il campo corrispondente all'ambito può essere valorizzato.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `ambito` | ENUM che determina il livello applicativo del preset |
| `profilo_accesso_id` | FK a `config.profili_accesso` — stessa entità del sistema permessi, risolta via `fn_get_profili_accesso_applicabili` |
| `is_default` | `TRUE` = preset applicato automaticamente nella cascata |
| `ordinamento_default` | JSON `[{"col": "ragione_sociale", "dir": "asc"}]` |
| `filtri_default` | JSON formato condiviso con il componente Vue filtri |

---

### Cascata di risoluzione

La funzione `ui.fn_resolve_lista_config` applica la cascata nell'ordine:

1. Preferenza personale utente (`lista_preferenza_utente`)
2. Preset di ruolo (`ambito='ruolo'` + `profilo_accesso_id = ANY(profili_applicabili)`)
3. Preset di emittente fiscale (`ambito='emittente_fiscale'` + `emittente_fiscale_id`)
4. Preset di sistema (`ambito='sistema'`)
5. Catalogo grezzo (`lista_colonna`, tutte le colonne visibili)
