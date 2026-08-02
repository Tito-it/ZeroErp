## 📘 Documentazione Concettuale – Funzione `vendite.fn_list_commessa_attivita`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse](/dbzero/vendite/tabelle/commesse)  
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_commessa_stato](/dbzero/vendite/funzioni/fn_get_commessa_stato)  
> • [vendite.fn_list_commesse_emittibili](/dbzero/vendite/funzioni/fn_list_commesse_emittibili)  
>
### 🎯 Scopo Principale
(latest review 26-02-2026)  
Restituisce il dettaglio righe di una commessa (`commesse_attivita`) con filtri opzionali e paginazione, per uso backend in consultazione e pre-validazione dei flussi di emissione.

---

### Regole principali

* Funzione read-only (`STABLE`).
* `p_commessa_id` obbligatorio (`> 0`).
* Errore esplicito se la commessa non esiste.
* Filtri opzionali:
  * `p_stato_emissione`
  * `p_stato_approvazione`
  * `p_competenza_mese` (normalizzato al primo giorno del mese)
* Paginazione:
  * `p_limit` default `1000`, massimo `10000`
  * `p_offset` minimo `0`
* Ordinamento (dal 02-08-2026):
  * `p_order_by` — nome della colonna, **whitelist chiusa** di 7 voci:
    `data_attivita`, `competenza_mese`, `segment_key`, `quantita`,
    `prezzo_snapshot`, `stato_approvazione`, `stato_emissione` (più `id`).
  * `p_order_dir` — `asc` (default) o `desc`.
  * `NULL`/vuoto ⇒ **ordine storico `ca.id`**: chi non chiede niente ottiene
    esattamente il risultato di prima.
  * Un nome fuori whitelist **solleva** `E_PARAMETRO_INVALIDO`: non ripiega sul
    default. Un ripiego silenzioso restituirebbe un ordine che nessuno ha
    chiesto, e a video sembrerebbe funzionare.
  * Tiebreak `ca.id` sempre in coda all'`ORDER BY`: senza, due righe con la
    stessa chiave possono scambiarsi di posto fra una pagina e l'altra, e
    l'operatore vede una riga due volte o mai.
* Include `sorgente_codice` tramite join su `config.sorgenti`, evitando risoluzioni N+1 lato backend.

> ⚠️ **Perché l'ordinamento sta qui e non nel backend.** `ORDER BY` e
> `LIMIT/OFFSET` vivono nella stessa funzione: ordinare a valle ordinerebbe **la
> pagina già estratta**, non la lista. Sarebbe un ordinamento che sembra
> funzionare e mente — peggio di una colonna non ordinabile, perché non ripiega:
> risponde sbagliato. È il motivo per cui `CommessaGestioneDrawer` non era
> convertibile a `<ListaConfigurabile>` prima di questa revisione.
>
> ℹ️ L'`ORDER BY` non è parametrizzabile, quindi la query passa da `format()`.
> È sicuro perché l'espressione **non viene mai dal parametro**: viene da un
> `CASE` chiuso che mappa nome → espressione. I valori restano parametri.
>
> ℹ️ Nessun `NULLS LAST`: tutte e sette le colonne ordinabili sono `NOT NULL`.
> Scriverlo suggerirebbe una nullabilità che non esiste.

---

### Output

Elenco righe `commesse_attivita` della commessa con i principali campi operativi:

* identificativi (`id`, `commessa_id`, `segment_key`)
* dati di competenza/quantita`/prezzo
* stati (`stato_approvazione`, `stato_emissione`)
* classificazione sorgente (`sorgente_tipo_id`, `sorgente_codice`)
* `meta` e `data_update`

---

### Esempio d'uso

```sql
-- Con ordinamento esplicito (la lista attività della commessa apre così:
-- `data_attivita desc`, come dichiara il preset di `ui.lista_preset`).
SELECT *
FROM vendite.fn_list_commessa_attivita(
  p_commessa_id => 12345,
  p_stato_emissione => 'NON_EMESSA',
  p_stato_approvazione => NULL,
  p_competenza_mese => DATE '2026-02-01',
  p_limit => 200,
  p_offset => 0,
  p_order_by => 'data_attivita',
  p_order_dir => 'desc'
);

-- Senza i due parametri il comportamento è quello storico (`ORDER BY ca.id`):
-- i chiamanti che non ordinano non sono stati toccati dalla revisione 08-2026.
SELECT * FROM vendite.fn_list_commessa_attivita(p_commessa_id => 12345);
```

---

{% include-markdown "signature-core.md" %}
