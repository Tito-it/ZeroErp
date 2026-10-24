## 📘 Documentazione Concettuale – Funzione `script.fn_stato_id_da_iso2()`

> 👀 **Vedi anche**
>
[config.stati](/dbzero/config/manual/stati)
> [script.fn_stato_proposto_id](/dbzero/script/manual/fn_stato_proposto_id)

---
### 🎯 Scopo Principale
(18-10-2026 — decisione D-1 di Tid)

**L'id dell'unico stato con questo codice ISO2.** Il codice si normalizza (maiuscole, spazi
tolti).

| Caso | Esito |
| --- | --- |
| una riga | il suo id |
| nessuna riga, o codice vuoto | `NULL`: il «non trovato» lo giudica il chiamante |
| più righe | `E_STATO_ISO2_AMBIGUO` |

⭐ Il «non trovato» resta al chiamante perché non è lo stesso errore dappertutto: un codice
scelto dall'operatore che non esiste (`E_CODICE`, in `fn_crea_soggetto_pf/pg`) non è un
parametro configurato male (`E_DEFAULT_ERRATO`, in `fn_stato_proposto_id`).

---

### Perché conta le righe

`config.stati.codice_iso2` **non è univoco, e non deve esserlo**: l'elenco ISTAT tiene righe
storiche dello stesso paese con codici catastali diversi (Armenia, Azerbaigian). Un
`SELECT … INTO` su quel codice prenderebbe una riga a caso; qui il caso si dice.

---

### Chi la chiama

`script.fn_stato_proposto_id`, `anagrafiche.fn_crea_soggetto_pf` e `fn_crea_soggetto_pg`
(per lo stato passato dal chiamante).

---

### Test

`db/pgtap/anagrafiche/test-indirizzo-libero-due-forme-v1.sql` (test 21, 22).

---

{% include-markdown "signature-core.md" %}
