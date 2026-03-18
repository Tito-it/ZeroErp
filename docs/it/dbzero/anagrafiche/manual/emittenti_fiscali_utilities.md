## 📘 Documentazione Concettuale – Tabella `anagrafiche.emittenti_fiscali_utilities`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)  
> • [config.utilities](/dbzero/config/tabelle/utilities)  
>
### 🎯 Scopo Principale
La tabella **`anagrafiche.emittenti_fiscali_utilities`** definisce i parametri
specifici di fatturazione per **emittente fiscale** e **utility**:

* soglie per la fattura minima
* regole di arrotondamento importi

---

### Campi chiave (semantica)

* `emittente_soggetto_ruolo_id`: emittente fiscale (soggetto_ruolo).
* `utility_id`: utility di riferimento.
* `minimo_soglia_min` / `minimo_soglia_max`: soglie per definire fattura minimo.
* `arrotondamento_importi_dec`: decimali di arrotondamento (0..2).
* `metodo_arrotondamento_importi`: `UP` | `DOWN` | `HALF_UP` | `HALF_DOWN`.

---

### Regole principali

* Unica riga per coppia **(emittente, utility)**.
* Se entrambe le soglie sono valorizzate: `minimo_soglia_min <= minimo_soglia_max`.
* Arrotondamento importi limitato a **max 2 decimali**.
* Guard utility/ruolo applicata via trigger:
  * risolve il `tipo_ruolo_id` dall'`emittente_soggetto_ruolo_id`;
  * valida con `script.fn_guard_utility_tipo_ruolo(...)`;
  * semantica fail-open se la matrice `config.utilities_tipi_ruolo` non e configurata per la utility.

---

### Esempio d’uso

```sql
SELECT *
FROM anagrafiche.emittenti_fiscali_utilities
WHERE emittente_soggetto_ruolo_id = 10
  AND utility_id = 2;
```

---

{% include-markdown "signature-core.md" %}
