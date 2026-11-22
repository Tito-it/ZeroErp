## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_clienti_codice_ba`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — una riga per cliente
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il codice del cliente
> * [config.stati_cliente](/dbzero/config/tabelle/stati_cliente) — lo stato, nel codice logico e in quello visibile
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli) — il ruolo cliente nomina questa vista come la sua entità
>
> Approfondimento viste:
>
> * [anagrafiche.vw_clienti_lista](/dbzero/anagrafiche/views/vw_clienti_lista) — la lista dei clienti, con l'anagrafica

---

### 🎯 Scopo Principale

`anagrafiche.vw_clienti_codice_ba` espone ogni cliente col codice del suo billing account, il suo stato e le date
del ciclo di vita. È l'entità del ruolo cliente: la ricerca per codice e la scheda del cliente partono da qui.

---

### Il codice del cliente è quello del billing account

Il cliente non ha un codice suo: lo riconosce il codice del suo billing account, che è unico per cliente perché
un billing account ha un solo cliente. Una ricerca per codice trova quindi al più un cliente.

`entita_id` ripete l'identificativo del cliente sotto un nome generico, per chi legge le entità dei ruoli tutte
nello stesso modo senza sapere come si chiama la chiave di ciascuna. Lo stato esce due volte: `stato_codice_interno`
per la logica, `stato_codice` per chi guarda.

---

### Il perimetro è quello di chi legge

La vista è `security_invoker`: le policy dei clienti e dei billing account valgono per chi interroga. Il billing
account è unito con un join esterno, ma le policy delle due tabelle guardano la stessa cosa (l'azienda del billing
account per l'operatore, il ruolo cliente per il portale e lo shop): un cliente visibile ha il suo billing account
visibile, e il codice c'è.

Nessun filtro di stato: i clienti chiusi e annullati ci sono, con il loro stato. Niente anagrafica: ragione
sociale e codice fiscale stanno in `anagrafiche.vw_clienti_lista`.

---

### Test

* `db/pgtap/config/test-tipi-ruoli-guard-entita-ref.sql` — la vista ha le colonne che l'entità del ruolo vuole.
* `db/pgtap/script/test-search-regola-unica-visibile-v1.sql` — la vista come entità della ricerca.
* `db/pgtap/rls/test-rls-viste-security-invoker.sql` — la vista eredita la RLS di chi legge.

---

{% include-markdown "signature-core.md" %}
