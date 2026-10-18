## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_indirizzo_elemento()`

> 👀 **Vedi anche**
>
[anagrafiche.fn_indirizzo_elemento_dettaglio](/dbzero/anagrafiche/manual/fn_indirizzo_elemento_dettaglio)
> [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/manual/fn_crea_indirizzo_soggetto) · [anagrafiche.fn_crea_indirizzi_ruolo](/dbzero/anagrafiche/manual/fn_crea_indirizzi_ruolo)

---
### 🎯 Scopo Principale
(18-10-2026 — decisione D-4 di Tid, richiesta del backend in `brief-db-processi-accensione-per-ambiente` §6.11)

**Leggere un indirizzo scritto in jsonb**, per le madri che scrivono gli indirizzi. È la
grammatica comune: la madre del soggetto e quella del ruolo la usano entrambe, quindi
accettano le stesse chiavi.

Controlla tre cose e ritorna l'elemento con `tipo_indirizzo_id` risolto:

| Controllo | Rifiuto |
| --- | --- |
| è un oggetto | `E_SCRIPT_CHIAMATA_NON_VALIDA` |
| ha solo chiavi di un indirizzo | `E_CAMPO_NON_AMMESSO`, col nome della chiave |
| il tipo esiste (`tipo_indirizzo_id`, oppure `tipo_indirizzo_codice` = codice interno) | `E_TIPO_INDIRIZZO_NON_TROVATO` |

Le chiavi ammesse sono le colonne della riga (`indirizzo_libero`, `stato_id`, `comune_id`,
`codice_postale_id`, `locality`, `postal_code`, `administrative_area`, `sublocality`,
`indirizzo_dettaglio_id`, il tipo) più i campi di una via da risolvere (`stradario_id`,
`toponomastica_id`, `descrizione_via`, il civico e i suoi dettagli).

---

### Quello che non fa

Non giudica la **completezza** né la **forma** dell'indirizzo libero: lo fa il guard della
tabella, [`trgfn_indirizzi_guard_forma_libera`](/dbzero/anagrafiche/manual/trgfn_indirizzi_guard_forma_libera).

---

### Note di migrazione

Prima del 18-10-2026 la madre del ruolo aveva queste regole scritte nel suo corpo, e la madre
del soggetto non le aveva affatto (firma posizionale, senza i campi della forma estera): due
copie della stessa grammatica, già divergenti.

---

{% include-markdown "signature-core.md" %}
