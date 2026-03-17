## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_next_progressivo`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)  
> • [vendite.registri_fatturazione_progressivi](/dbzero/vendite/tabelle/registri_fatturazione_progressivi)  
> • [vendite.fn_get_anno_registro](/dbzero/vendite/manual/fn_get_anno_registro)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_anno_registro](/dbzero/vendite/funzioni/fn_get_anno_registro)   
>
🎯 Scopo Principale

(latest review 26-01-2026)
La funzione **`vendite.fn_get_next_progressivo`** restituisce il prossimo numero
di registro, con **lock della riga** progressivi per evitare doppioni.

---

### Parametri di input

| Parametro       | Tipo                                    | Descrizione        |
| --------------- | --------------------------------------- | ------------------ |
| `p_registro_id` | `vendite.registri_fatturazione.id%TYPE` | Registro fiscale.  |
| `p_data`        | date                                    | Data documento.    |
| `p_serie`       | text                                    | Serie (opzionale). |

---

### Regola applicata

* Anno ricavato da `vendite.fn_get_anno_registro(p_data)`.
* Mese fisso `0` (reset annuale).
* `pg_advisory_xact_lock` su registro/anno/serie per evitare interleaving.
* `SELECT ... FOR UPDATE` sulla riga progressivo.
* Se la riga non esiste, viene creata con `last_numero = 0`.

---

### Note operative

* La funzione deve essere chiamata **solo in emissione** (non in bozza).
* Evita **doppioni**, ma i buchi possono comparire in caso di rollback.

---

{% include-markdown "signature-core.md" %}
