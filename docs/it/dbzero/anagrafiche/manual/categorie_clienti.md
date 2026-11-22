## 📘 Documentazione Concettuale – Tabella `anagrafiche.categorie_clienti`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — porta la categoria del cliente
> * [anagrafiche.categorie_clienti_listini](/dbzero/anagrafiche/tabelle/categorie_clienti_listini) — la matrice categoria → listino
> * [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides) — i parametri che una categoria può ridefinire
> * [vendite.listini](/dbzero/vendite/tabelle/listini) — i listini a cui la matrice porta
>
> Approfondimento funzioni:
>
> * [vendite.fn_resolve_prezzo_listino_v2_esito](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2_esito) — il calcolo del prezzo che legge la categoria
>
> Guide:
>
> * [Gestione listini](/guide/gestione-listini) — come la categoria entra nel prezzo

---

### 🎯 Scopo Principale

`anagrafiche.categorie_clienti` è il catalogo delle fasce commerciali dei clienti (per esempio standard,
silver, gold). Un billing account ha sempre una categoria, e la categoria decide, attraverso la matrice
`anagrafiche.categorie_clienti_listini`, quale listino e quale variazione valgono per lui.

---

### ⭐ Un contenitore, non una politica di prezzo

La categoria non porta prezzi né sconti: dice solo a quale fascia appartiene il cliente. Il listino e la
variazione stanno nella matrice, per categoria, utility, azienda e classe d'utenza; un contratto individuale
viene prima di tutto. L'unica scelta che la categoria fa da sola è `partecipa_promo`: se è falso, i billing
account della categoria non ricevono le promozioni.

Le stesse categorie servono a tutte le aziende dell'installazione: la tabella non ha RLS, e ciò che cambia da
un'azienda all'altra è la matrice.

---

### La categoria del billing account

La colonna `anagrafiche.billing_account.categoria_cliente_id` è obbligatoria e **senza valore predefinito**:
chi crea il billing account sceglie la categoria, e il database non ne mette una al suo posto. Il nome stabile
con cui l'applicazione trova la sua categoria (quella da proporre, per esempio) è `codice_interno`, che dopo
la nascita non si cambia; `codice` è quello che l'operatore vede e può correggere, salvato in maiuscolo e
unico senza distinzione di maiuscole.

La categoria è fotografata anche su contratti, attività fatturabili e attività di commessa, che ricordano con
quale categoria è stato calcolato il prezzo.

---

### Una categoria in uso non si spegne

Finché ci sono billing account, righe della matrice o parametri ridefiniti che la usano, la categoria non si
disattiva: il rifiuto viene dal blocco comune della disattivazione, una volta per ciascuna delle tre tabelle.
Un billing account, una riga della matrice o un parametro ridefinito non possono puntare a una categoria
spenta.

---

### Codici errore

* `E_CODICE_NON_MODIFICABILE` — si cambia `codice_interno`.
* I rifiuti della disattivazione e del riferimento a una categoria spenta sono quelli dei blocchi comuni
  dell'attivo.

---

### Test

* `db/pgtap/anagrafiche/test-categorie-clienti-listini-v1.sql` — la matrice che la categoria alimenta.
* `db/pgtap/config/test-parameter-overrides-categoria-cliente-v1.sql` e
  `db/pgtap/config/test-fn-get-parameter-full-categoria-cliente-v1.sql` — i parametri ridefiniti per categoria.
* `db/pgtap/anagrafiche/test-fn-update-cliente-v1.sql` — la categoria cambiata dal verbo del cliente.

---

### Note di migrazione

* 2026-06-29 — nasce `codice_interno`, perché la logica dell'applicazione non dipenda dal codice che
  l'operatore vede.

---

{% include-markdown "signature-core.md" %}
