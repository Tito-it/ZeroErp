## 📘 Documentazione Concettuale – Tabella `ui.lista_preset`

> **Ultimo aggiornamento**: 8 novembre 2026

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
| `contenuto_aggiornato_il` | La data dell'ultimo cambio del **contenuto** del preset (vedi sotto): la confronta con lo snapshot della preferenza il flag `preset_aggiornato` |
| `data_update`, `user_update` | L'audit: chi e quando ha scritto la riga, dal trigger del framework |

---

### Cascata di risoluzione

La funzione `ui.fn_resolve_lista_config` risolve la cascata **per chiave** (dal 1-11-2026): `colonne`, `ordinamento`, `filtri` e `pagina_dimensione` vengono ognuna dal primo livello che la contiene.

1. Preferenza personale utente (`lista_preferenza_utente`), per le sole chiavi che contiene
2. Il **preset di base**: il primo, in quest'ordine, con almeno una colonna attiva — di ruolo (`ambito='ruolo'` + `profilo_accesso_id = ANY(profili_applicabili)`), di emittente fiscale (`ambito='emittente_fiscale'` + `emittente_fiscale_id`), di sistema (`ambito='sistema'`)
3. Catalogo grezzo (`lista_colonna`, tutte le colonne visibili; ordinamento e filtri vuoti; misura di default `PAGINA`)

Il preset è sempre **completo**: dà tutte e quattro le chiavi, colonne comprese. Una `pagina_dimensione` vuota vale il default `PAGINA` del catalogo delle misure.

---

### `contenuto_aggiornato_il`: la data del contenuto

`contenuto_aggiornato_il` dice **quando è cambiato l'ultima volta ciò che il preset mostra**, non quando la riga è stata scritta. La scrivono due trigger, sulle funzioni condivise con i preset di dashboard:

* `trg_ui_lista_preset_a20_contenuto_aggiornato_upd` ([`ui.trgfn_preset_contenuto_aggiornato`](/dbzero/ui/funzioni/trgfn_preset_contenuto_aggiornato)): quando cambiano `ordinamento_default`, `filtri_default` o `pagina_dimensione`;
* `trg_ui_lista_preset_colonna_z10_tocca_preset_ins_upd_dlt` ([`ui.trgfn_preset_riga_tocca_preset`](/dbzero/ui/funzioni/trgfn_preset_riga_tocca_preset)): quando una colonna del preset in [`ui.lista_preset_colonna`](/dbzero/ui/tabelle/lista_preset_colonna) si aggiunge, si toglie o cambia.

Una riscrittura **uguale** non sposta la data: il seed (`loadUpdateData`) riscrive ogni riga del CSV a ogni giro, e se la data fosse l'audit ogni ritocco del CSV accenderebbe il banner «preset aggiornato» a tutti. Per questo la data del contenuto ha una colonna sua, e `data_update` resta l'audit, che invece si sposta a ogni scrittura. Non sono contenuto `codice`, `descrizione`, `ambito`, `is_default`, `attivo`: accendere o spegnere un preset cambia **quale** preset sta sotto una preferenza (`preset_base_id`), non che cosa dice. Un preset appena nato ha come data del contenuto quella di nascita.

---

### Note di migrazione

* 2026-11-08 — la data del contenuto passa da `data_update` a `contenuto_aggiornato_il` (NOT NULL, nasce con la riga); `data_update` e `user_update` diventano l'audit del framework, NOT NULL col default, perché `ui` è entrata nell'ambito delle automazioni (`brief-db-revisione-dbops`, giro 7-bis blocco c). Il guard ATTIVO resta sulla FK verso la lista; quelle verso emittente e profilo sono in eccezione.
