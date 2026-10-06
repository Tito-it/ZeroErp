## 📘 Documentazione Concettuale – Vista `script.vw_override_operatore_area`

> 👀 **Vedi anche**
>
> **Le tre tabelle che riunisce:** [config.user_override_aree](/dbzero/config/tabelle/user_override_aree) · [config.user_override_azioni](/dbzero/config/tabelle/user_override_azioni) · [config.user_override_oggetti](/dbzero/config/tabelle/user_override_oggetti)
>
> **Chi la legge:** [script.fn_get_permessi_riepilogo_aree](/dbzero/script/funzioni/fn_get_permessi_riepilogo_aree) · la lista operatori e il pannello permessi del backend

---

### 🎯 Scopo Principale
(scritta il 06-10-2026)

Risponde a: **quali eccezioni ai permessi ha scritto un operatore, e in quale
area cade ciascuna?**

Un'eccezione (override) può riguardare un'area intera, una singola azione o un
singolo oggetto. Questa vista le mette in fila, **una riga per eccezione**, e a
ognuna dà la sua area:

| Tipo | L'area è… |
| --- | --- |
| `AREA` | l'area dell'eccezione stessa |
| `AZIONE` | l'area a cui appartiene l'azione |
| `OGGETTO` | l'area a cui il catalogo assegna l'oggetto |

È il solo posto da cui si conta quante eccezioni ha un operatore: il totale
nella lista operatori, il numero sulle chip del riepilogo, il numero nel pannello
dei permessi. Tre schermate, un conteggio.

---

### Cosa conta, e cosa no

* Si contano le eccezioni **scritte**, anche quelle scadute o non ancora in
  vigore. È il numero di righe che l'operatore ha nel pannello, non quante
  valgono oggi.
* Non ci sono filtri su aree o azioni spente, né su oggetti riservati, e non
  servono: il database non lascia esistere quei casi. Un'area o un'azione con
  un'eccezione non si può spegnere, e un oggetto con un'eccezione non può
  diventare riservato. Quindi ogni eccezione scritta è una che il pannello
  mostra.

La chiave di una riga è la coppia `tipo` + `override_id`: gli id delle tre
tabelle sono indipendenti.

Presidio: `db/pgtap/script/test-permessi-riepilogo-aree-v1.sql` (test 4-8).

{% include-markdown "signature-core.md" %}
