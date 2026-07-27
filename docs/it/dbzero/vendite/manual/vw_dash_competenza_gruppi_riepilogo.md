## 🔍 Documentazione Concettuale – Vista `vendite.vw_dash_competenza_gruppi_riepilogo`

> **Versione**: 2026-07-27 (brief-db-emissione-fattura-per-documento-sorgente
> PARTE A step A9, requisito A5 · migration `20260727-19`)

> **Vedi anche**
>
[vendite.vw_dash_competenza_gruppi](/dbzero/vendite/views/vw_dash_competenza_gruppi) — la vista di dettaglio che aggrega
> [vendite.vw_dash_competenza_attivita](/dbzero/vendite/views/vw_dash_competenza_attivita) — la base della catena
> [vendite.vw_dash_backlog_riepilogo](/dbzero/vendite/views/vw_dash_backlog_riepilogo) — stesso pattern dettaglio+riepilogo

---

### 🎯 Scopo Principale

I **totali del perimetro** per la riga di riconciliazione sotto la lista dei
gruppi fatturabili:

```text
7 documenti · 29 attività · 12.500 €
```

---

### Perché non è cosmetica

Senza aggregati dal database, il frontend calcolerebbe il totale sommando le
righe della **pagina corrente**: mostrerebbe un numero che *sembra* il totale ma
è il parziale. E nessuno se ne accorgerebbe, perché nessuno somma a mano le
righe di più pagine per verificare.

È anche il modo per rendere evidente che **un filtro di lista sta mostrando un
sottoinsieme**: se il totale della riga non torna con il numero della card,
l'operatore sa che sta guardando una porzione.

---

### Aggrega, non ricalcola

La vista somma `vw_dash_competenza_gruppi` invece di ripartire dai dati. È lo
stesso pattern già in uso per il backlog (`vw_dash_backlog_documenti` +
`vw_dash_backlog_riepilogo`), e la ragione è la stessa: **i due numeri non
possono divergere**. Se cambia la definizione di gruppo o il calcolo del valore,
cambiano insieme.

Una query autonoma partirebbe identica e si separerebbe alla prima modifica di
una delle due. Un pgTAP presidia la coerenza
(`test-vw-dash-competenza-gruppi-v1.sql`, caso 10).

---

### Grana dell'aggregato

`(competenza_mese, stadio, emittente_soggetto_ruolo_id)`.

| Asse | Perché c'è |
|---|---|
| `competenza_mese` | la lista è per mese |
| `stadio` | la lista è per stadio: il consumatore filtra `DA_EMETTERE` |
| `emittente` | il cockpit può essere ristretto a uno solo, e i totali devono seguire |

Il perimetro più fine — cliente, utility — lo applica il **consumatore** in
`WHERE`. Aggregare anche su quelli moltiplicherebbe le righe senza aggiungere
informazione.

---

### Colonne

| Colonna | Note |
|---|---|
| `n_gruppi` | conta i **gruppi**: è l'unico numero che la vista di dettaglio non sa dare da sola |
| `n_attivita` | somma delle righe: riconcilia con il numero della card |
| `valore` | somma degli importi |
| `n_gruppi_oneri` | quanti gruppi sono oneri — distingue «7 documenti» da «7 voci di cui 2 di oneri», che a video è un'informazione diversa |

---

### ⚠️ `security_invoker=on` va ri-specificato

La vista eredita lo scope emittente dalla catena
(`vw_dash_competenza_gruppi` → `vw_dash_competenza_attivita`). Se un
`CREATE OR REPLACE` non ripete la reloption, PostgreSQL la **azzera**: i totali
verrebbero calcolati **fuori dal perimetro dell'operatore**, cioè proprio il
numero che dovrebbe riconciliare diventerebbe quello sbagliato — e con l'aria di
essere giusto.

---

{% include-markdown "signature-core.md" %}
