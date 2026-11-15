## 📘 Documentazione Concettuale – Tabella `ui.lista_definizione`

> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> [ui.lista_colonna](/dbzero/ui/tabelle/lista_colonna)
> [ui.lista_preset](/dbzero/ui/tabelle/lista_preset)
> [ui.lista_preferenza_utente](/dbzero/ui/tabelle/lista_preferenza_utente)
>
> Funzione:
>
> [ui.fn_resolve_lista_config](/dbzero/ui/funzioni/fn_resolve_lista_config)
> [ui.trgfn_ui_lista_definizione_a10_valida_vista_sql](/dbzero/ui/funzioni/trgfn_ui_lista_definizione_a10_valida_vista_sql)

La tabella **`ui.lista_definizione`** è il **catalogo delle liste configurabili** del sistema. Una riga per ogni lista che si vuole rendere personalizzabile dall'operatore (es. `anagrafiche.clienti`, `vendite.fatture`, `catalogo.articoli:picker`).

---

### 🎯 Scopo Principale

* **Registro centralizzato** delle liste che il sistema espone come personalizzabili. Il frontend interroga questa tabella per sapere quali liste supportano la personalizzazione di colonne, filtri e ordinamento.
* **Identificatore stabile** tramite `codice`: stringa nel formato `<schema>.<entità>` (lista principale) o `<schema>.<entità>:<contesto>` per varianti (es. `:picker`, `:dashboard`). Usato da API e frontend senza dipendere dall'`id` numerico.
* **Collegamento alla view sorgente** tramite `vista_sql`: nome della view PostgreSQL da cui la lista legge i dati. Validato a INSERT/UPDATE dal trigger guard `trgfn_ui_lista_definizione_a10_valida_vista_sql`, che impedisce di registrare una lista con una view inesistente.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `codice` | Identificatore stabile cross-environment (es. `anagrafiche.clienti`) |
| `schema_dati` | Schema PostgreSQL cui appartiene la lista (es. `anagrafiche`) |
| `vista_sql` | Nome della view sorgente dati; validato da trigger contro `pg_catalog.pg_class` |
| `attivo` | Disattivazione logica senza cancellazione; il trigger di validazione salta se `FALSE` |
| `ricerca_min_caratteri` | Quanti caratteri servono perché la ricerca libera filtri. È una proprietà della lista: le tabelle di configurazione a codici corti («KG», «FT») cercano da 1, gli archivi dalla soglia di progetto, 3 (il default). Si dichiara nel seed `lista_definizione.csv`; `CHECK >= 1`. La leggono la configurazione della schermata ([`fn_resolve_lista_config`](/dbzero/ui/funzioni/fn_resolve_lista_config)) e la ricerca del backend ([`fn_lista_da_codice`](/dbzero/ui/funzioni/fn_lista_da_codice)), dalla stessa riga |

---

### Relazioni

`ui.lista_definizione` è referenziata da:

| Tabella | Campo | Scopo |
|---------|-------|-------|
| `ui.lista_colonna` | `lista_id` | Colonne disponibili per la lista |
| `ui.lista_preset` | `lista_id` | Preset di configurazione per la lista |
| `ui.lista_preferenza_utente` | `lista_id` | Preferenza personale utente per la lista |

---

### Note operative

* Ogni ambiente (dev, staging, prod) deve avere gli stessi `codice` per garantire che i preset seedati siano applicabili ovunque. L'`id` numerico non è stabile tra ambienti — usare sempre `codice` come riferimento nei seed.
* Tre proprietà di una lista sono presidiate da un **elenco per nome** in un pgTAP: lista globale (`perimetro_emittente = false`, `test-lista-definizione-perimetro-emittente-v1`), `multi_emittente` (`test-lista-definizione-multi-emittente-v1`), ricerca da un carattere (`test-lista-ricerca-min-caratteri-v1`). Chi aggiunge o toglie una riga del seed con una di queste proprietà scrive il nome nell'elenco nello stesso giro, anche quando il lavoro parte dal backend. Sul lato Django la riga nuova accende i test di copertura del perimetro e della ricerca: è il primo passo del backend.
* La colonna `vista_sql` accetta solo view, materialized view o tabelle (`relkind IN ('v','m','r')`). Non è necessario includere lo schema nel nome: il trigger usa il nome grezzo come `pg_catalog.pg_class.relname`.
