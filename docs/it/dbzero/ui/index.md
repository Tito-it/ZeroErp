# Schema `ui`

Schema dedicato ai **metadati di presentazione** delle liste configurabili. Contiene esclusivamente strutture dati di UI (catalogo colonne, preset, preferenze utente, permessi a colonna) — zero logica di business.

> Posizionamento: **Anello 1** dello sviluppo concentrico (infrastruttura condivisa trasversale).  
> Dipende da: `config.profili_accesso`, `config.livello_accesso`, `anagrafiche.emittenti_fiscali`, `django.auth_user`.

---

## 📚 Tabelle

- [lista_definizione](tabelle/lista_definizione.md) — Catalogo delle liste configurabili del sistema. Una riga per lista personalizzabile (es. `anagrafiche.clienti`, `vendite.fatture`).
- [lista_colonna](tabelle/lista_colonna.md) — Catalogo delle colonne disponibili per ciascuna lista. Definisce tipo dato, comportamento (filtrabile, ordinabile, esportabile), sensibilità e raggruppamento.
- [lista_preset](tabelle/lista_preset.md) — Configurazioni predefinite per le liste a tre livelli: sistema (globale), emittente_fiscale (per società), ruolo (per profilo di accesso).
- [lista_preset_colonna](tabelle/lista_preset_colonna.md) — Composizione di un preset: quali colonne, in che ordine, con che larghezza e visibilità di default.
- [lista_preferenza_utente](tabelle/lista_preferenza_utente.md) — Preferenza personale dell'utente per una lista. Un record per coppia (utente, lista); sovrascrive la cascata dei preset.
- [lista_colonna_permesso](tabelle/lista_colonna_permesso.md) — Controllo accesso a livello di singola colonna per profilo di accesso. Supporta modello deny-list (non sensibili) e allow-list (sensibili).

---

## ⚙️ Funzioni

- [fn_resolve_lista_config](funzioni/fn_resolve_lista_config.md) — Punto centrale di risoluzione della configurazione lista per un utente: applica cascata preset, merge nuove colonne, normalizzazione obbligatorie e filtro autorizzativo. Ritorna JSONB pronto per il frontend.
- [trgfn_ui_lista_definizione_a10_valida_vista_sql](funzioni/trgfn_ui_lista_definizione_a10_valida_vista_sql.md) — Guard BEFORE INSERT/UPDATE: verifica che `vista_sql` esista come relazione in `pg_catalog.pg_class`.
- [trgfn_ui_lista_colonna_a10_valida_campo_sorgente](funzioni/trgfn_ui_lista_colonna_a10_valida_campo_sorgente.md) — Guard BEFORE INSERT/UPDATE: verifica che `campo_sorgente` esista come attributo della view nella `pg_catalog.pg_attribute`.

---

## 🔡 ENUM di dominio

| ENUM | Valori | Usato in |
|------|--------|----------|
| `ui.ambito_preset` | `sistema`, `emittente_fiscale`, `ruolo` | `lista_preset.ambito` |
| `ui.tipo_colonna` | `identificatore`, `informazione`, `azione` | `lista_colonna.tipo_colonna` |
| `ui.tipo_dato` | `string`, `numeric`, `date`, `datetime`, `boolean`, `enum` | `lista_colonna.tipo_dato` |
| `ui.allineamento_colonna` | `left`, `right`, `center` | `lista_colonna.allineamento` |

---

{% include-markdown "signature-core.md" %}
