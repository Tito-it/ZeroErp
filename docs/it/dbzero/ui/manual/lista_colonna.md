## 📘 Documentazione Concettuale – Tabella `ui.lista_colonna`

> 👀 **Vedi anche**
>
> [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione)
> [ui.lista_preset_colonna](/dbzero/ui/tabelle/lista_preset_colonna)
> [ui.lista_colonna_permesso](/dbzero/ui/tabelle/lista_colonna_permesso)
>
> Funzione:
>
> [ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente](/dbzero/ui/funzioni/trgfn_ui_lista_colonna_a10_valida_campo_sorgente)

La tabella **`ui.lista_colonna`** è il **catalogo delle colonne disponibili** per ciascuna lista configurabile. Definisce tutto ciò che una lista può mostrare: tipo dato, comportamento (filtrabile, ordinabile, esportabile), raggruppamento per la modale di personalizzazione e flag di sensibilità per il controllo accesso.

---

### 🎯 Scopo Principale

* **Catalogo completo** delle colonne disponibili per ogni lista. Il frontend usa questa tabella per popolare la modale di personalizzazione e per applicare la formattazione corretta (`tipo_dato`, `formato`).
* **Controllo comportamento**: i flag `filtrabile`, `ordinabile`, `esportabile`, `ricercabile_full` determinano quali operazioni sono ammesse su ciascuna colonna, indipendentemente dalla preferenza utente.
* **Modello di accesso a colonna**: il flag `sensibile` inverte il modello permessi per quella colonna. Quando `FALSE` (default) si usa un modello deny-list (accesso totale salvo restrizioni esplicite); quando `TRUE` si usa allow-list (bloccata di default salvo grant esplicito in `lista_colonna_permesso`).
* **Validazione sorgente**: `campo_sorgente` è validato dal trigger guard `trgfn_ui_lista_colonna_a10_valida_campo_sorgente` contro `pg_catalog.pg_attribute`, prevenendo errori runtime alla prima apertura della lista.

---

### Comportamento per `tipo_colonna`

| Valore | Comportamento |
|--------|---------------|
| `identificatore` | Sempre visibile, non nascondibile, fissata di default. Tipicamente la colonna ID o nome dell'entità. |
| `informazione` | Personalizzabile liberamente dall'operatore (visibile/nascosta, ordine, larghezza). |
| `azione` | Pulsanti/icone UI. Non esportabile (`campo_sorgente` = NULL), non nascondibile. |

---

### Colonne chiave

| Colonna | Scopo |
|---------|-------|
| `codice` | Chiave stabile usata nel JSONB delle preferenze (non l'`id`). Cambiarlo invalida tutte le preferenze salvate. |
| `campo_sorgente` | Nome colonna nella view PostgreSQL. NULL per `tipo_colonna='azione'`. Validato da trigger. |
| `gruppo` / `gruppo_ordine` | Raggruppamento nella modale di personalizzazione (es. "Dati anagrafici", "Dati fiscali"). |
| `sensibile` | `TRUE`: deny-list invertita → blocco default. `FALSE`: accesso pieno salvo restrizioni. |
| `formato` | Hint di formattazione per il frontend (es. `currency_eur`, `date_short`, `percent_2`, `yesno`). |
| `larghezza_default` | Larghezza suggerita in pixel. Fa anche da **contributo al packing a somma** del ritiro dinamico (vedi `priorita`). |
| `priorita` | `SMALLINT NOT NULL DEFAULT 50`. Peso di permanenza per il **ritiro dinamico** delle colonne lato FE. |

---

### Ritiro dinamico delle colonne (`priorita`)

Quando lo spazio orizzontale non basta (tipicamente all'apertura della sidebar), il componente `<ListaConfigurabile>` **ritira** le colonne meno prioritarie in una riga di espansione invece di attivare la scrollbar — zero dati persi. La logica è un **packing a somma**: ogni colonna contribuisce con la sua `larghezza_default`; quando la somma supera la larghezza del contenitore si ritirano per prime le colonne a `priorita` più bassa, finché la somma rientra. Non c'è soglia per-colonna e non c'è compressione intermedia.

* **Più alto = resiste più a lungo.** Default `50` (mid-pack): le liste che non valorizzano `priorita` restano neutre e si ritirano da destra (vedi tiebreaker).
* **Tiebreaker**: a parità di `priorita` il FE usa `ordine_default` (si ritira prima la colonna più a destra).
* **Mai ritirate**: `tipo_colonna IN ('identificatore','azione')` e colonne `fissata` hanno priorità implicita infinita lato FE, **indipendente** dal valore stoccato.
* **Attributo globale di catalogo**: `priorita` **non** è overridabile per preset né per preferenza utente. `fn_resolve_lista_config` la legge **fresca** da `ui.lista_colonna` ad ogni risoluzione, così un cambio amministrativo si propaga a tutti senza reset delle preferenze. È esposta per ogni colonna nell'output della funzione (contratto API).

---

### Relazioni

| Tabella | Campo | Scopo |
|---------|-------|-------|
| `ui.lista_preset_colonna` | `colonna_id` | Composizione dei preset |
| `ui.lista_colonna_permesso` | `colonna_id` | Permessi a livello colonna |
