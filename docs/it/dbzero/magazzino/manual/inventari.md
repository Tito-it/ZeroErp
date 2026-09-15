## 📘 Documentazione Concettuale – Tabella `magazzino.inventari`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.inventari_righe](/dbzero/magazzino/tabelle/inventari_righe) — il dettaglio
> • [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — l'ancora del perimetro
> • [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — dove il conteggio finisce
>
Guide: brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.7)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

**Il documento di conteggio fisico**: la rilevazione di quanto c'è davvero a scaffale, in un
magazzino, a una data, con uno stato (`DRAFT` → `COUNTING` → `CONFIRM` → `POSTED`, o
`CANCEL`). Il dettaglio per articolo sta nelle righe.

Il conteggio non modifica la giacenza da sé: quando è confermato, le sue righe diventano la
**sorgente** dei movimenti di allineamento (`INVENTARIO_RIGA`), e la giacenza cambia sul
registro. È la catena che tiene il ledger come unica fonte — anche una correzione da
inventario è una scrittura tracciata. L'operazione che lo fa è un lotto successivo.

### La sorgente, come sul registro

`sorgente_tipo_id` (una riga di [config.sorgenti](/dbzero/config/tabelle/sorgenti)) più
**esattamente una** chiave fra `sorgente_riga` e `sorgente_uid`, secondo quanto il catalogo
dichiara per quel tipo; senza tipo, nessuna chiave. Il guard tipizzato
(`script.trgfn_guard_sorgente_polimorfa_tipizzata`) verifica che il record esista. Qui la
sorgente è **facoltativa**: dice da quale documento l'operazione è nata, se ce n'è uno.

### Chi può vedere e scrivere

Un operatore vede e scrive gli inventari dei magazzini del **proprio emittente**
(`rls_inventari_ef_whitelist`, via magazzino); le righe e le note risalgono alla testata.
Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
