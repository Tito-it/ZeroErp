## 📘 Documentazione Concettuale – Tabella `magazzino.ubicazioni`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [config.tipi_ubicazione](/dbzero/config/tabelle/tipi_ubicazione)
> • [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**I bin dentro un magazzino**: dove fisicamente sta la merce.

La posizione è descritta da coordinate progressive — `area`, `corsia`, `scaffale` e seguenti —
e il **tipo** viene da `config.tipi_ubicazione` (`PICK`, `STORAGE`, `STAGING`, `BUFFER`,
`IN_TRANSIT`, `DAMAGED`).

⭐ `parent_id` rende le ubicazioni **gerarchiche**: un'area contiene corsie, che contengono
scaffali. Permette di ragionare a qualunque livello senza moltiplicare le tabelle.

---

### ⚠️ Il tipo è obbligatorio, la gerarchia no

`tipo_id` è `NOT NULL`: ogni ubicazione dichiara la propria funzione. `parent_id` è invece
nullable — le ubicazioni di primo livello non hanno padre.

⚠️ Nulla impedisce oggi un **ciclo** nella gerarchia (A padre di B, B padre di A): non c'è un
guard che lo verifichi. È da tenere presente se si scriveranno query ricorsive sulle
ubicazioni.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
