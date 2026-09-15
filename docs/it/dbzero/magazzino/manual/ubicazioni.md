## 📘 Documentazione Concettuale – Tabella `magazzino.ubicazioni`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — di chi è l'ubicazione
> • [config.tipi_ubicazione](/dbzero/config/tabelle/tipi_ubicazione)
> • [magazzino.vw_giacenza_ubicazione](/dbzero/magazzino/views/vw_giacenza_ubicazione) — che cosa c'è in ogni posizione
>
Guide: brief `brief-db-magazzino-lotto-1-terreno-vuoto` (§4.10)

---
### 🎯 Scopo Principale

(rev 2026-09-15 — Lotto 1 del magazzino)

**Le posizioni dentro un magazzino**: dove fisicamente sta la merce. La posizione è
descritta da coordinate progressive — `area`, `corsia`, `scaffale` e seguenti — e il **tipo**
viene da `config.tipi_ubicazione` (`PICK`, `STORAGE`, `STAGING`, `BUFFER`, `IN_TRANSIT`,
`DAMAGED`). `parent_id` rende le ubicazioni gerarchiche: un'area contiene corsie, che
contengono scaffali.

`tipo_id` è obbligatorio, `parent_id` no (le ubicazioni di primo livello non hanno padre).
⚠️ Nulla impedisce oggi un ciclo nella gerarchia: da tenere presente scrivendo query
ricorsive.

### Una posizione per movimento

Dal 15-09 un movimento del registro porta **una** ubicazione (`movimenti.ubicazione_id`):
uno spostamento fra due posizioni dello stesso magazzino è una coppia di righe, un'uscita
dall'una e un'entrata nell'altra, e
[vw_giacenza_ubicazione](/dbzero/magazzino/views/vw_giacenza_ubicazione) mostra che cosa c'è
in ciascuna. Che l'ubicazione appartenga al magazzino della riga lo controlla la primitiva
(Lotto 2). Un asset non porta più la propria ubicazione: dove si trova lo dice il registro.

### Chi può vedere e scrivere

Un'ubicazione appartiene all'emittente del suo magazzino (`rls_ubicazioni_ef_whitelist`, via
magazzino). Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
