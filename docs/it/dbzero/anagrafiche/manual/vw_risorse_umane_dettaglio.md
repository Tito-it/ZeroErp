## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_risorse_umane_dettaglio`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.risorse_umane](/dbzero/anagrafiche/tabelle/risorse_umane) — il rapporto di lavoro, una riga per riga della vista
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la persona, col suo nome e i suoi dati fiscali
> * [config.qualifiche](/dbzero/config/tabelle/qualifiche) — la qualifica del rapporto
> * [config.unita_organizzative](/dbzero/config/tabelle/unita_organizzative) — il reparto del rapporto
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_risorse_umane_guard_ruolo](/dbzero/anagrafiche/funzioni/trgfn_risorse_umane_guard_ruolo) — chi tiene il soggetto del rapporto uguale a quello del ruolo
>
> Guide:
>
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — il rapporto di lavoro e la veste operatore

---

### 🎯 Scopo Principale

`anagrafiche.vw_risorse_umane_dettaglio` mostra ogni rapporto di lavoro col nome della persona, la sua qualifica e
il suo reparto decodificati: è la sede unica del modo in cui una risorsa umana si chiama.

---

### Una riga per rapporto, il nome dal soggetto

La vista parte da `anagrafiche.risorse_umane` e non filtra: ci sono anche i rapporti spenti o scaduti, con la loro
colonna `risorsa_umana_attivo` e le loro date. Il nome della persona è la `ragione_sociale_completa` del soggetto,
che la vista legge dalla copia del soggetto scritta sul rapporto (`soggetto_id`), senza passare dal ruolo: il guard
di ruolo del rapporto tiene quella copia uguale al soggetto del ruolo, quindi è la stessa persona.

La qualifica e il reparto sono uniti senza pretenderli: un rapporto senza reparto c'è, con le colonne del reparto
vuote. Le colonne prendono il prefisso della tabella da cui vengono (`risorsa_umana_…`, `qualifica_…`,
`unita_organizzativa_…`, `soggetto_…`) quando il nome da solo sarebbe ambiguo.

La vista non guarda la veste né la credenziale: dice chi è la persona e dove lavora, non se entra.

---

### Chi la legge

Nessun oggetto del database la nomina; la legge il backend, in due punti:

* il lookup delle risorse umane, `GET /api/v1/anagrafiche/risorse-umane/lookup/`, che il drawer della commessa usa
  per scegliere il responsabile;
* la testata della commessa, `GET /api/v1/vendite/commesse/{id}/stato/`, per il nome del responsabile.

Tutti e due leggono di qui il nome, perché la stessa persona si chiami allo stesso modo nella scelta e nel
dettaglio.

---

### ⚠️ Che cosa oggi non copre

* **I permessi.** Il ruolo applicativo `zeroerp_app` ha sulla vista anche inserimento, modifica e cancellazione.
  La vista unisce più tabelle e non è aggiornabile: quei permessi non servono a niente, e non andrebbero dati.
* **La forma.** La vista non è `security_invoker`: legge le tabelle coi permessi del proprietario. Oggi è innocuo,
  perché nessuna delle tabelle sotto ha la visibilità per riga. La vista non ha un commento nel database.

---

### Test

Nessun test la presidia: né le colonne su cui il backend conta, né il nome che espone.

---

{% include-markdown "signature-core.md" %}
