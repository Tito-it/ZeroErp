## 📘 Documentazione Concettuale – Tabella `ui.dashboard_definizione`

> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> [ui.widget](/dbzero/ui/tabelle/widget)
> [ui.dashboard_widget](/dbzero/ui/tabelle/dashboard_widget)
> [ui.dashboard_preset](/dbzero/ui/tabelle/dashboard_preset)
> [ui.dashboard_preferenza_utente](/dbzero/ui/tabelle/dashboard_preferenza_utente)
>
> Funzione:
>
> [ui.fn_resolve_dashboard_config](/dbzero/ui/funzioni/fn_resolve_dashboard_config)

La tabella **`ui.dashboard_definizione`** è il **catalogo delle dashboard configurabili** del sistema. Una riga per ogni dashboard che si vuole rendere personalizzabile per utente (prima e per ora unica: `home`). Ricalca [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione), ma **senza** `vista_sql`.

---

### 🎯 Scopo Principale

* **Registro centralizzato** delle dashboard personalizzabili. Il frontend e la funzione di risoluzione interrogano questa tabella per codice.
* **Identificatore stabile** tramite `codice` (es. `home`): usato da API e frontend senza dipendere dall'`id` numerico.
* **Nessuna view sorgente unica**: a differenza delle liste, una dashboard non legge da un'unica view. I suoi widget deep-linkano a viste diverse e ciascun contatore è calcolato dal backend. Per questo `vista_sql` non esiste in questa tabella.

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `codice` | Identificatore stabile cross-environment (es. `home`) |
| `descrizione` | Etichetta descrittiva della dashboard |
| `attivo` | Disattivazione logica; la funzione di risoluzione salta le dashboard non attive (errore `E_UI_DASHBOARD_NON_TROVATA`) |

---

### Relazioni

`ui.dashboard_definizione` è referenziata da:

| Tabella | Campo | Scopo |
|---------|-------|-------|
| `ui.dashboard_widget` | `dashboard_id` | Pool di widget candidati per la dashboard |
| `ui.dashboard_preset` | `dashboard_id` | Preset di configurazione per la dashboard |
| `ui.dashboard_preferenza_utente` | `dashboard_id` | Preferenza personale utente per la dashboard |

---

### Note operative

* Ogni ambiente deve avere gli stessi `codice` per garantire che i preset seedati siano applicabili ovunque. L'`id` numerico non è stabile tra ambienti — usare sempre `codice` come riferimento.
* La riga `home` è seedata via `loadUpdateData` con id esplicito; la sequenza IDENTITY viene riallineata in `90_end` (evita collisioni pkey sugli INSERT auto-id).
* Dashboard future (backlog, fatturazione) entrano qui **solo** se saranno griglie-card personalizzabili per utente; se resteranno viste analitiche fisse, non usano questa struttura.
