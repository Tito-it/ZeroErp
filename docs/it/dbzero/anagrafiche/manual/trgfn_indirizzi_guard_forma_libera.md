## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_indirizzi_guard_forma_libera()`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[anagrafiche.indirizzi](/dbzero/anagrafiche/manual/indirizzi)
> [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/manual/indirizzi_soggetti)
> [config.stati](/dbzero/config/manual/stati) — il flag `catalogo_comuni_completo`
>
**Approfondimento funzioni:**
>
[anagrafiche.trgfn_indirizzi_base_normalize](/dbzero/anagrafiche/manual/trgfn_indirizzi_base_normalize) — gira prima
> [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/manual/fn_crea_indirizzo_soggetto) · [anagrafiche.fn_crea_indirizzi_ruolo](/dbzero/anagrafiche/manual/fn_crea_indirizzi_ruolo) — le madri che ci passano
>
**Guide:**
>
[Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — R3

---
### 🎯 Scopo Principale
(18-10-2026 — richiesta del backend in `brief-db-processi-accensione-per-ambiente` §6.11, decisioni D-2 e D-3 di Tid)

**Dire all'operatore che cosa manca, o che cosa non torna, in un indirizzo scritto a mano**
(indirizzo libero), con un codice e il **nome del campo** da correggere. Prima di questo
guard l'indirizzo incompleto arrivava come errore tecnico del database (`E_DATABASE`, il
CHECK), senza dire quale campo mancava.

Un corpo solo per le due tabelle degli indirizzi (ruolo e soggetto), che hanno le stesse
colonne.

---

### Le due forme

Sempre: la via (`indirizzo_libero`) e lo stato (`stato_id`). Poi la forma la decide lo
**stato**, con la sua proprietà `catalogo_comuni_completo`:

| Forma | Quando | Obbligatori | Vuoti |
| --- | --- | --- | --- |
| **del catalogo** | stato col catalogo completo (l'Italia) | `comune_id`, `codice_postale_id`, coerenti fra loro e con lo stato | `locality`, `postal_code`, `administrative_area` (li dice già l'elenco). `sublocality` (frazione, quartiere) è ammessa |
| **estera** | stato senza catalogo completo | `locality` | `comune_id`, `codice_postale_id`. Facoltativi `postal_code` (ci sono paesi senza codice postale), `administrative_area`, `sublocality` |

Uno stato con il catalogo **non ancora completo** accetta anche la forma del catalogo, se
chi scrive sceglie un comune o un CAP: allora vale tutta, coerenza compresa.

---

### I rifiuti

Tutti di classe `DATO_ERRATO`. Il nome della colonna viaggia nel contesto `campo` (canale
`COLUMN`: il frontend accende quel campo); nella frase c'è il campo come lo legge una persona.

| Codice | Quando |
| --- | --- |
| `E_INDIRIZZO_LIBERO_INCOMPLETO` | manca un campo: il primo, nell'ordine via, stato, poi quelli della forma |
| `E_INDIRIZZO_CAMPO_ALTRA_FORMA` | nella forma del catalogo è compilato un campo della forma estera |
| `E_INDIRIZZO_COMUNE_ALTRO_STATO` | il comune non è dello stato. Anche quando l'elenco non sa dirlo (provincia senza regione): non si può affermare che lo sia |
| `E_INDIRIZZO_CAP_ALTRO_COMUNE` | il CAP non è del comune |

Il CHECK `chk_*_free_requirements` resta come **rete** per le scritture che non passano
dai trigger, con la forma minima comune alle due varianti.

---

### Quando scatta, e quando no

* `BEFORE INSERT OR UPDATE`, nella fascia **z10**: **dopo** il normalize, che porta a NULL i
  testi vuoti e scrive lo stato proposto. Un guard in fascia a10 vedrebbe la riga com'era
  prima del normalize, e rifiuterebbe ciò che il CHECK accetta.
* `UPDATE` senza `OF`: il normalize scrive `stato_id`, che è una colonna giudicata. Il corpo
  esce subito se nessuna colonna dell'indirizzo cambia.
* ⭐ Per questo le righe scritte **prima** della regola, o prima che il flag di uno stato si
  accenda, restano valide finché nessuno tocca il loro indirizzo. Quando lo si tocca, vale la
  forma di oggi.
* Indirizzo normalizzato (`indirizzo_dettaglio_id`): niente da giudicare.

---

### La regola sta in un posto solo

Le madri (`fn_crea_indirizzo_soggetto`, `fn_crea_indirizzi_ruolo`) **non** ripetono la
completezza: passano i campi, e il giudizio è qui. Il form legge lo stesso flag dello stato per
scegliere quale variante mostrare.

---

### Test

`db/pgtap/anagrafiche/test-indirizzo-libero-due-forme-v1.sql`: ordine dei trigger, le due
forme, i quattro rifiuti, il canale `COLUMN`, il flag che si accende dopo.

---

{% include-markdown "signature-core.md" %}
