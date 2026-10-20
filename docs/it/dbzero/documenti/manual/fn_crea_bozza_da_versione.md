## 📘 Documentazione Concettuale – Funzione `documenti.fn_crea_bozza_da_versione()`

> 👀 **Vedi anche**
>
> [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni)
> [documenti.fn_personalizza_template_standard](/dbzero/documenti/funzioni/fn_personalizza_template_standard)

### 🎯 Scopo

(21-10-2026 — brief `brief-db-modelli-documento-standard`, §10.3 K-6)

Copia una versione in una **bozza nuova** di un modello, con il numero successivo di quel modello,
e ne restituisce l'id. È il punto unico che decide quali campi una copia riprende.

### Che cosa si copia

| Si copia | Non si copia |
|---|---|
| titolo, formato, HTML, CSS, markdown | le date di validità: si fissano alla pubblicazione |
| motore, formato e orientamento della pagina, margini | l'origine (`derivata_da_versione_id`): la dichiara il chiamante |
| forma dei dati (`versione_contesto`), schema del contesto, meta | lo stato: la copia nasce `BOZZA` |

Sostituzioni facoltative: titolo, date, attivo, meta.

### Chi la usa

* `fn_personalizza_template_standard`, che copia la versione dello standard nel modello nuovo
  dell'azienda;
* il clone di una versione del backend, che oggi elenca i campi da sé (`dati_bozza_copiata`).

### Regole

* Il numero è il massimo del modello di destinazione più uno; due chiamate concorrenti le separa
  l'unico (modello, versione).
* I guard della tabella restano in servizio: sola lettura dello standard, origine coerente, date.
