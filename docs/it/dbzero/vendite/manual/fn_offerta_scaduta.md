## 📘 Documentazione Concettuale – Funzione `vendite.fn_offerta_scaduta`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Chi la usa:
>
> [vendite.vw_offerte_commerciali_lista](/dbzero/vendite/manual/vw_offerte_commerciali_lista) (colonna `is_scaduta`)
>
> Da dove viene il significato dello stato:
>
> [config.stati_doc_offerte](/dbzero/config/manual/stati_doc_offerte) (colonna `esito`)

---

### 🎯 Scopo

**Dice se un'offerta è scaduta.** Un'offerta è scaduta quando valgono insieme due cose:

* il cliente **non ha ancora risposto**: lo stato corrente non ha un esito nel vocabolario
  (`config.stati_doc_offerte.esito` vuoto, oggi bozza ed emessa);
* la **validità è passata**: `validita_al` è prima della data di riferimento.

Un'offerta senza `validita_al` non scade. Un'offerta accettata, rifiutata, superata o annullata ha
un esito, e quindi non è scaduta anche se la validità è passata.

### ⚙️ Come si chiama

```sql
vendite.fn_offerta_scaduta(p_esito, p_validita_al, p_data_riferimento) → boolean
```

La funzione riceve i **valori**, non l'id dell'offerta: l'esito dello stato, la validità e la data
di riferimento. Chi la chiama passa la data operativa dell'azienda, `script.fn_data_operativa()`.

* **La vista della lista** la compone per la colonna `is_scaduta`, e passa la data operativa come
  sottoquery: viene calcolata una volta sola per tutta la lista.
* **Il dettaglio dell'offerta** la chiama sulla riga che sta già leggendo. Non serve leggere la
  vista intera, con la pratica e le altre colonne, per un solo valore.

### ⚠️ Due scelte che reggono la regola

* **È pura** (`IMMUTABLE`, `LANGUAGE sql`). Il pianificatore la incorpora nella query che la usa,
  quindi non costa una chiamata per riga.
* **Non è `STRICT`.** L'esito vuoto è il caso normale, cioè il cliente non ha ancora risposto. Con
  `STRICT` la funzione darebbe NULL proprio quando la risposta giusta è «sì, scaduta».

### 🧪 Verifica

`db/pgtap/vendite/test-offerta-guard-dal-vocabolario-v1.sql`: i casi sui valori, la forma della
funzione, e la scadenza letta dalla lista mentre l'esito si sposta da uno stato all'altro.
