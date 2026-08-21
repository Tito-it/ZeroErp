## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_offerte_commerciali_gen_codice()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali)
> • [config.sistema_codici](/dbzero/config/tabelle/sistema_codici)
>
Approfondimento funzioni:
> • [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)
> • [vendite.trgfn_contratti_gen_codice](/dbzero/vendite/funzioni/trgfn_contratti_gen_codice)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Assegna il **codice dell'offerta commerciale** quando non viene fornito, delegando a
`script.fn_generate_codice('offerta_commerciale')`. Stesso pattern dei `gen_codice` di
anagrafiche, pratiche e contratti: riconoscere il campo vuoto e chiedere il valore al
generatore centrale.

Configurazione in `config.sistema_codici`, riga
`codice_interno = 'offerta_commerciale'`: prefisso `OFC`, separatore `-`, numero a 7 cifre
(`OFC-0000123`).

---

### Aggancio

Trigger `trg_offerte_commerciali_a10_gen_codice_ins_upd` — fase `_a10_`,
`BEFORE INSERT OR UPDATE` su `vendite.offerte_commerciali`.

---

### Regole applicate

1. Se `NEW.codice` è `NULL` o vuoto dopo `btrim`, viene valorizzato con
   `script.fn_generate_codice('offerta_commerciale')`.
2. Un codice già presente non viene mai sovrascritto.

---

### ⚠️ Qui il codice **non** è protetto da un lock di colonna

È la differenza che conta rispetto ai `gen_codice` gemelli. Su `anagrafiche.soggetti`,
`vendite.contratti`, `pratiche.pratiche` e compagnia, accanto al `gen_codice` c'è sempre un
`script.trgfn_lock_columns('codice', 'CODICE_NON_MODIFICABILE')` che rende il codice
immutabile dopo la creazione. Su `vendite.offerte_commerciali` **quel trigger non esiste**.

Il trigger di generazione è però agganciato anche in `UPDATE`. Ne segue che:

```sql
UPDATE vendite.offerte_commerciali SET codice = NULL WHERE id = :id;
```

**non fallisce**: il trigger rigenera, la riga si salva con un codice **nuovo**, e l'offerta
cambia identità agli occhi di chiunque la citi per codice. Non serve nessuna GUC di
override, nessuna manutenzione: basta un `UPDATE`.

Lo stesso vale per un `UPDATE` che assegna un codice arbitrario: essendo valorizzato, il
trigger lo lascia passare così com'è.

⚠️ Se l'immutabilità del codice offerta è un requisito — e per un documento commerciale che
il cliente cita di norma lo è — **oggi non è presidiata dal database**. Va aggiunto un
`trgfn_lock_columns`, non dato per acquisito perché «funziona come sui contratti».

---

### Altre note

* **La chiave è `'offerta_commerciale'`** (singolare, con underscore): il legame con
  `config.sistema_codici` è per stringa, non per FK.
* **`usa_sequenza = false` restituisce `NULL`, non un errore.** La colonna `codice` è
  `NOT NULL`, quindi il caso si manifesterebbe come violazione di vincolo (SQLSTATE `23502`),
  senza nessun codice `E_*` a spiegarla.

---

### Codici errore

| Codice | Sollevato da | Quando |
|--------|--------------|--------|
| `E_SEQUENZA_NON_CONFIGURATA` | `script.fn_generate_codice` | Nessuna riga `codice_interno = 'offerta_commerciale'` in `config.sistema_codici` |

La funzione non solleva errori propri.

---

{% include-markdown "signature-core.md" %}
