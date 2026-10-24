## 📘 Documentazione Concettuale – Funzione `vendite.fn_coppie_fattura_scoperte()`

> 👀 **Vedi anche**
>
> [vendite.fn_provision_registri](/dbzero/vendite/manual/fn_provision_registri) — chi la usa per far nascere e collegare il registro standard
> [vendite.fn_lookup_registro_id](/dbzero/vendite/manual/fn_lookup_registro_id) — la ricerca che decide se una coppia è coperta
> [vendite.tipi_doc_fiscale_registri](/dbzero/vendite/manual/tipi_doc_fiscale_registri) — i collegamenti

---

### 🎯 Scopo Principale

(18-10-2026 — R-BE-14, decisioni D-14a … D-14d di Tid,
`brief-db-processi-accensione-per-ambiente` §6.14)

**I documenti fiscali che un emittente non saprebbe numerare.** Per ogni emittente
attivo, o per quello indicato, restituisce le coppie (tipo documento, natura) per
cui non c'è un registro delle fatture: quelle su cui l'emissione si fermerebbe con
«registro non risolto».

| Riga restituita | Che cosa dice |
| --- | --- |
| emittente, tipo documento, natura | quell'emittente non ha un registro per quel documento |
| nessuna riga | l'emittente sa numerare tutti i documenti fiscali attivi |

---

### Quando una coppia è «coperta»

Lo decide la stessa ricerca che userà chi emette:
[`fn_lookup_registro_id`](/dbzero/vendite/manual/fn_lookup_registro_id), chiamata
con utility vuota. Una coppia è coperta se l'emittente ha un registro **valido per
tutte le utility** collegato a lei. La ricerca non è riscritta qui, quindi la
copertura non può dire una cosa diversa da quella che vedrà l'emissione.

* un registro legato a **una** utility non copre le altre;
* contano solo i tipi documento e le nature **attivi**;
* un emittente **spento** non ha coppie scoperte: non emette, quindi non è un
  buco. Quando si riaccende, il provisioning lo sistema.

---

### Chi la usa

* `vendite.fn_provision_registri`, due volte: per decidere a quali emittenti far
  nascere il registro standard e quali coppie collegargli;
* il pgTAP `db/pgtap/vendite/test-registro-fattura-nasce-con-emittente-v1.sql`.

---

{% include-markdown "signature-core.md" %}
