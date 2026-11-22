## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_clienti_lista`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — una riga per cliente
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il codice del cliente
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — l'istanza, da cui si arriva al soggetto
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — l'anagrafica del cliente
> * [ui.lista_definizione](/dbzero/ui/tabelle/lista_definizione) — la lista configurabile che la legge
>
> Approfondimento viste:
>
> * [anagrafiche.vw_clienti_codice_ba](/dbzero/anagrafiche/views/vw_clienti_codice_ba) — il cliente col codice, per la ricerca

---

### 🎯 Scopo Principale

`anagrafiche.vw_clienti_lista` è la sorgente della lista dei clienti: per ogni cliente l'anagrafica del soggetto,
il codice del billing account, la utility, lo stato e le quattro date del ciclo di vita, in una riga sola.

---

### Una riga per cliente, cioè per billing account

La granularità è il cliente, che ha un solo billing account: un soggetto compare una volta per ogni sua
fornitura (gas a casa, luce in ufficio), anche con lo stesso ruolo e la stessa utility su due conti diversi.
La vista non raggruppa e non ordina: lo fa la lista.

Il soggetto si legge dall'istanza del cliente. È lo stesso del ruolo, perché il billing account tiene ruolo e
istanza dello stesso soggetto (`anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza`).

Nessun filtro di stato: chiusi e annullati ci sono, e la lista li filtra se vuole.

---

### Il perimetro è quello di chi legge

La vista è `security_invoker`, e non scrive un filtro di perimetro suo: valgono le policy delle tabelle per chi
interroga. Delle tabelle unite hanno la RLS i clienti e i billing account, e le loro policy guardano la stessa
azienda e lo stesso ruolo: un cliente che chi legge vede ha il suo billing account visibile, e i join interni non
fanno sparire righe per perimetro.

Una colonna nuova della lista si aggiunge qui prima che nella configurazione della lista: la lista non può
mostrare ciò che la vista non espone.

---

### Test

* `db/pgtap/rls/test-rls-viste-security-invoker.sql` — la vista eredita la RLS di chi legge.

---

{% include-markdown "signature-core.md" %}
