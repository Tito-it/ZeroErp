## 📘 Documentazione Concettuale – Tabella `pratiche.formule_tempo`

> 👀 **Vedi anche**
>
Tabelle:
>
[pratiche.tipi_prestazione](/dbzero/pratiche/tabelle/tipi_prestazione)
> [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi)
> [pratiche.calcoli_tempo](/dbzero/pratiche/manual/calcoli_tempo)
>
Funzioni:
>
[fn_valuta_tempo_esecuzione_da_a](/dbzero/pratiche/manual/fn_valuta_tempo_esecuzione_da_a)

---
### 🎯 Scopo Principale
Soglie temporali e tempo massimo di esecuzione, configurabili per tipo prestazione con coppia di template flusso **da/a**. Misura il tempo impiegato per passare dal completamento di flusso_da al completamento di flusso_a.

---

### Campi chiave (semantica)

| Colonna                | Note                                                                  |
| ---------------------- | --------------------------------------------------------------------- |
| `tipo_prestazione_id`  | FK a `pratiche.tipi_prestazione`.                                     |
| `template_flusso_da_id`| FK a `pratiche.template_flussi` — flusso di partenza.                 |
| `template_flusso_a_id` | FK a `pratiche.template_flussi` — flusso di arrivo.                   |
| `giorni_esecuzione`    | Tempo massimo previsto in giorni (al netto delle sospensioni).        |
| `giorni_warning`       | Soglia giallo (giorni rimanenti).                                     |
| `giorni_critico`       | Soglia rosso (giorni rimanenti).                                      |

---

### Vincoli

* **UNIQUE** su `(tipo_prestazione_id, template_flusso_da_id, template_flusso_a_id)`.
* **CHECK** `giorni_esecuzione > 0`, `giorni_warning > 0`, `giorni_critico > 0`.
* **CHECK** `giorni_warning > giorni_critico` (warning scatta prima del critico).
* **CHECK** `giorni_warning < giorni_esecuzione` (warning dentro il tempo massimo).
* **CHECK** `template_flusso_da_id <> template_flusso_a_id` (no self-reference).

---

### Note operative

* Le formule sono **configurazione**, non dati operativi. Definiscono le regole, non i calcoli.
* I calcoli effettivi sono in `pratiche.calcoli_tempo`, alimentati dal trigger di completamento.
* Il campo `giorni_esecuzione` viene snapshotato in `calcoli_tempo.giorni_formula` al momento dell'avvio del conteggio.

---

{% include-markdown "signature-core.md" %}
