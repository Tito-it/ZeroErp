## 📘 Documentazione Concettuale – Funzione `script.fn_stato_proposto_id()`

> 👀 **Vedi anche**
>
[config.stati](/dbzero/config/manual/stati)
> [script.fn_stato_id_da_iso2](/dbzero/script/manual/fn_stato_id_da_iso2) — la ricerca per codice ISO2
> [script.fn_get_parameter_di_sessione](/dbzero/script/manual/fn_get_parameter_di_sessione) — la cascata degli override, col contesto della sessione
>
**Guide:**
>
[Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — R8

---
### 🎯 Scopo Principale
(18-10-2026 — decisione D-1 di Tid, richiesta del backend in `brief-db-processi-accensione-per-ambiente` §6.11)

**Lo stato che si propone quando chi scrive non lo dice.** Ritorna l'id di `config.stati`
indicato dal parametro `STATO_PROPOSTO_ISO2` (un codice ISO2, oggi `IT`).

È una **proposta**, non «lo stato dell'installazione»: il parametro passa per la cascata
degli override, quindi un utente che lavora con clienti tedeschi può avere `DE`.

Il parametro si legge con
[`script.fn_get_parameter_di_sessione`](/dbzero/script/manual/fn_get_parameter_di_sessione),
che ricava il contesto dalla sessione: valgono gli override per utente, per gruppo, per
azienda attiva, per sessione e per chi chiede (il nome del trigger o della funzione che la
chiama). Fino al 18-10-2026 (R-BE-13) utente, gruppi e azienda arrivavano vuoti, e i loro
override non scattavano.

---

### Chi la chiama

* i trigger normalize che riempiono uno `stato_id` non detto: indirizzi (ruolo e soggetto),
  soggetti, regioni, IVA per stato, toponomastica;
* `anagrafiche.fn_crea_soggetto_pf` e `fn_crea_soggetto_pg`, quando il chiamante non passa lo
  stato;
* `script.fn_crea_utente_tecnico`, per il soggetto dell'utente tecnico.

Il form del backend la usa (attraverso il parametro) per preselezionare la tendina dello stato.

---

### Valida e non ripiega

| Caso | Esito |
| --- | --- |
| parametro assente o vuoto | `E_CONFIG_MANCANTE` |
| il codice non indica nessuno stato | `E_DEFAULT_ERRATO` |
| il codice indica più stati (righe storiche ISTAT) | `E_STATO_ISO2_AMBIGUO` (da `fn_stato_id_da_iso2`) |

Mai un ripiego su `'IT'` o su uno stato «a caso». L'esistenza del codice la controlla anche
il registro `config.parameter_fk_surrogate` quando si scrive il parametro; qui resta come rete.

---

### Quello che non fa

Non decide le **regole di un paese**. Il controllo di codice fiscale e partita IVA, la forma
della sigla di provincia e il motore IVA restano scritti per `'IT'` dove la legge è italiana:
lì `'IT'` vuol dire «la legge italiana», non «lo stato di default».

---

### Note di migrazione

Prende il posto di due parametri che dicevano la stessa cosa in due modi, ritirati lo stesso
giorno:

* `state_code_iso3` (codice ISO3), letto dai cinque trigger normalize con
  `script.fn_get_default_by_param`. Quella funzione non aveva altri chiamanti ed è stata
  ritirata: cercava con un `LIMIT 1` senza ordine, cioè una riga a caso quando il codice ne
  indica più d'una;
* `soggetto_default_stato_iso2` (codice ISO2), letto a mano da `fn_crea_soggetto_pf/pg` con
  un ripiego silenzioso a `'IT'` se il parametro mancava.

---

### Test

`db/pgtap/anagrafiche/test-indirizzo-libero-due-forme-v1.sql` (test 16, 23, 26);
`db/pgtap/script/test-fn-get-parameter-di-sessione-v1.sql` (test 5 e 6: l'override per
utente arriva allo stato proposto e al trigger di un indirizzo).

---

{% include-markdown "signature-core.md" %}
