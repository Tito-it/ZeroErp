## 📘 Documentazione Concettuale – Funzione `catalogo.trgfn_articoli_componenti_guard_un_livello`

> 👀 **Vedi anche**
>
> [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — la tabella su cui il trigger opera
> [catalogo.trgfn_articoli_guard_flags_struttura_bom_attiva](/dbzero/catalogo/manual/trgfn_articoli_guard_flags_struttura_bom_attiva) — lo stesso divieto dal lato articolo (check 3)
> [catalogo.trgfn_articoli_componenti_guard_is_composito](/dbzero/catalogo/manual/trgfn_articoli_componenti_guard_is_composito) — il guard sul padre
> [Modello componenti BoM §9.2](/dev/manual/modello-componenti-bom) — perché la distinta ha un livello

### 🎯 Scopo Principale

(latest review 2026-10-13)

La distinta base ha **un livello solo**: il componente di un legame attivo non è un articolo
composito. Un kit dentro un altro kit finirebbe nei documenti come un articolo semplice, e i
suoi componenti non li scaricherebbe il magazzino né li prezzerebbe nessuno. Con un livello
solo, poi, un ciclo (A dentro B, B dentro A) non si può costruire.

---

### Logica applicata

* Trigger `trg_articoli_componenti_a10_guard_is_un_livello_ins_upd`, **BEFORE INSERT OR UPDATE
  OF attivo** su `catalogo.articoli_componenti`.
* Si giudica il legame che **nasce attivo** e quello che **si riaccende** (`attivo` da falso a
  vero). Un legame spento non è parte della distinta e passa. `componente_id` non si può
  cambiare (lo blocca `trgfn_articoli_componenti_block_modifica_struttura`), quindi non c'è un
  altro UPDATE da guardare.
* Se il componente ha `is_composito = true` → `E_BOM_COMPONENTE_COMPOSITO` (1293), campo
  `componente_id`, con il codice del componente e quello del padre nel messaggio.

---

### L'ordine dei rifiuti

Fra i guard `_a10_` della tabella parla quello col nome minore, e il nome è scelto apposta:

| Trigger | Che cosa dice |
| --- | --- |
| `…_guard_is_composito_…` | il padre non è composito: la distinta non può esistere |
| `…_guard_is_un_livello_…` | il componente è composito: non ci può stare |
| `…_guard_iva_bom_…` | il componente ha un'IVA diversa dal padre |

Prima si dice che la distinta non esiste, poi che quel componente non ci sta, e solo per un
componente ammesso si giudica l'IVA. Lo presidia
`db/pgtap/catalogo/test-distinta-un-livello-e-onere-natura-v1.sql` (test 5 e 6).

---

### Comportamento atteso

* **Consentito**: un componente semplice; un legame spento con un componente composito.
* **Bloccato**: un componente composito in un legame che nasce attivo o che si riaccende.
* I legami scritti prima del guard non si rigiudicano: un guard giudica le scritture.

---
{% include-markdown "signature-core.md" %}
