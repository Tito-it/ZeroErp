## 📘 Documentazione Concettuale – Funzione `script.fn_data_operativa`

> 👀 **Vedi anche**
>
> [vendite.fn_calcola_data_documento](/dbzero/vendite/funzioni/fn_calcola_data_documento)
> [vendite.fn_get_or_create_fattura_header](/dbzero/vendite/funzioni/fn_get_or_create_fattura_header)
> [vendite.fatture](/dbzero/vendite/tabelle/fatture)
> [config.parameters](/dbzero/config/tabelle/parameters)

---

### 🎯 Scopo Principale

Risponde a una domanda sola: **che giorno è, per l'azienda?**

Non «che giorno è per chi sta chiamando». È la differenza che questa funzione
esiste per rendere impossibile.

```sql
SELECT script.fn_data_operativa();   -- → 2026-08-25
```

---

### Il problema che risolve

`current_date` non è una costante: è **il giorno secondo il fuso orario della
sessione**. E le sessioni che scrivono su questo database non hanno tutte lo
stesso fuso:

| chi scrive | fuso della sessione |
|---|---|
| l'applicazione (Django) | **UTC** |
| una console `psql` | `Europe/Rome` |
| i job schedulati (pgAgent) | `Europe/Rome` |

Fra la mezzanotte e le due del mattino ora italiana, UTC è **ancora il giorno
prima**. Lo stesso documento, creato nello stesso istante, prendeva una data
diversa a seconda del canale da cui passava.

⚠️ **Non è un'ipotesi: è stato misurato.** Il 2026-08-25, su 18 fatture in
archivio, **7 portavano la data del giorno precedente**.

⭐ E il danno è particolarmente insidioso perché la data sbagliata è
**plausibile**: è ieri, non il 1970. Su un documento fiscale nessuno la nota — e
quando la si nota, il numero è già stato consumato.

---

### Come decide

Il fuso è **un dato di configurazione**, non una costante nel codice:
`config.parameters`, chiave **`SYSTEM_FUSO_ORARIO`**. La funzione lo legge e
restituisce `now()` convertito in quel fuso, troncato a data.

---

### ⛔ Fail-loud: tre guasti, nessun ripiego

La funzione **si ferma e lo dice** in tre casi, tutti con `E_CONFIG_MANCANTE`:

1. il parametro **non c'è**;
2. il parametro c'è ma è **vuoto** — caso reale, non teorico:
   `config.parameters.default_value` è `NOT NULL` ma non ha nessun vincolo di
   non-vuoto, e a catalogo ci sono già parametri a stringa vuota;
3. il valore c'è ma **non è un fuso orario** (non compare in
   `pg_timezone_names`) — senza questo controllo `AT TIME ZONE` alzerebbe un
   errore grezzo `22023`, e il guasto arriverebbe al backend come 500 non
   tradotto invece che come errore di dominio.

⛔ **Non esiste un ripiego a UTC o a `current_date`.** Sarebbe la scelta
apparentemente prudente, ed è invece esattamente il difetto di partenza: darebbe
una data plausibile e sbagliata, cioè lo stesso guasto in una forma più difficile
da vedere.

---

### ⛔ Perché NON usa `fn_get_parameter_full`

Il lettore canonico dei parametri esiste (`script.fn_get_parameter_full`) e
questa funzione **non lo usa**. È una scelta, non una dimenticanza.

Quel lettore applica una **cascata di override** — utente, gruppo, sessione,
emittente. Applicata qui, farebbe portare **alla stessa fattura date diverse a
seconda di chi la genera**: cioè ricreerebbe, per un'altra strada, il problema
che la funzione chiude. Si legge il `default_value` **nudo**, apposta.

---

### Note operative

* **`STABLE`**, e il motivo è preciso: `now()` è l'istante di *inizio
  transazione*, quindi dentro la stessa transazione la risposta è per costruzione
  identica.
* ⚠️ **Il perimetro è volutamente stretto.** La usano solo
  `fn_calcola_data_documento`, `fn_get_or_create_fattura_header` e il `DEFAULT`
  della colonna `vendite.fatture.data`. `CURRENT_DATE` resta in **25 tabelle e 67
  funzioni**: sostituirlo ovunque è un cantiere a sé, non un effetto collaterale
  di questo.
* Brief: `docs/it/dev/work-in-progress/brief-db-numerazione-data-documento-e-sequenza.md` §4 DB-2.

---

{% include-markdown "signature-core.md" %}
