# Personalizzazioni liste — viste nominate e condivisione (rimandate)

## ⏭️ Chi riparte — aggiornato al 2026-11-25

**Riparte: nessuno.** DEF-3 e DEF-4 sono **rimandate** per decisione di Tid
(2026-11-25): sviluppo futuro, non iniziato. Il documento resta qui come sede
delle decisioni da prendere quando si riapre il tema.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | Decidere se le viste nominate valgono anche per le dashboard, **prima** di aprire DEF-3 | §«Le dashboard configurabili» | — |
| 2 | Tid | Le decisioni operative di DEF-3 | §DEF-3 | la riapertura del tema |
| 3 | Team DB, poi BE/FE | DEF-3: migration, endpoint, selettore | §DEF-3 | le decisioni del passo 2 |
| 4 | Tid, poi i team | DEF-4: scope, modifica, autore che lascia il reparto | §DEF-4 | DEF-3 fatto |

**Decisioni aperte di Tid**: quelle elencate in DEF-3, DEF-4 e nella sezione
dashboard. **Da committare**: niente di codice; solo questa revisione del
documento.

---

> **Cosa c'è qui.** Le sole voci della roadmap DEF **non realizzate**. Tutto ciò
> che è atterrato — DEF-1, DEF-2, DEF-5b, DEF-6, DEF-8, DEF-10 — e la chiusura di
> DEF-7 («non necessaria», 2026-08-22) vivono nel
> [consuntivo in work-done](../work-done/2026/consuntivo-personalizzazioni-liste-def.md),
> con le convenzioni da rispettare per ogni lista nuova. Lo stato del roll-out
> delle liste su `<ListaConfigurabile>` sta nel
> [piano-migrazione-primevue-5.md](piano-migrazione-primevue-5.md) §8-bis.
> **Piano madre**: [sviluppo-personalizzazioni-liste.md](../work-done/2026/sviluppo-personalizzazioni-liste.md) (Blocchi A..F).

---

## Stato in una tabella

| # | Voce | Stato | Sforzo | Prerequisito |
| --- | --- | --- | --- | --- |
| DEF-3 | Viste nominate multiple per utente | ⏸️ Rimandata (Tid, 2026-11-25) | L | migration `lista_preferenza_utente` |
| DEF-4 | Condivisione viste tra utenti | ⏸️ Rimandata (Tid, 2026-11-25) | M | DEF-3 (hard) |
| — | Le dashboard configurabili seguono questa roadmap? | ❓ Da decidere | — | vedi ultima sezione |

**Verificato il 2026-11-25** sulla doc auto-generata: `ui.lista_preferenza_utente`
ha ancora `UNIQUE (auth_user_id, lista_id)` e nessuna colonna `nome` /
`is_attiva`; nel BE nessun endpoint di viste, nel FE nessun selettore. DEF-3 e
DEF-4 non sono iniziate. Lo stesso vincolo, una preferenza per utente e
dashboard, c'è su `ui.dashboard_preferenza_utente`.

---

## DEF-3 — Viste nominate multiple per utente

**Stato:** ⏸️ Rimandata · **Sforzo:** L

### Cosa serve

Oggi `lista_preferenza_utente` ha `UNIQUE (auth_user_id, lista_id)` → una sola
preferenza per lista. Si vogliono viste nominate («Clienti morosi», «Clienti
TOP», «Vista rapida») con switch rapido.

### Decisioni operative aperte

1. **Schema**: aggiungere `nome VARCHAR(80)` + `is_attiva BOOLEAN`. Sostituire
   l'UNIQUE con `(auth_user_id, lista_id, nome)` più un UNIQUE parziale su
   `is_attiva = TRUE` per coppia `(auth_user_id, lista_id)`. Backfill dei dati
   esistenti: `nome='Default'`, `is_attiva=true`.
2. **Limite viste**: tetto rigido (es. 10 per lista per utente) o avviso morbido?
3. **UX**: selettore viste `<Select>` in toolbar accanto a «Personalizza»?
   «Salva come…» con copia profonda?
4. **Rapporto con i preset**: un preset è già una vista di sistema decisa
   dall'amministratore; la vista nominata è dell'utente. Da chiarire come
   convivono nel selettore (i preset come viste di partenza? elencati a parte?).

### Architettura

- **DB**: migration su `lista_preferenza_utente` (colonne + UNIQUE + backfill).
  Brief al team DB non banale.
- **BE**: endpoint `GET/POST/PUT/DELETE /api/v1/ui/liste/{codice}/preferenze[/{id}]`;
  l'endpoint config attuale servirebbe la vista attiva.
- **FE**: selettore in toolbar (probabile BB nuovo `ListaViewSelect.vue`) +
  drawer «Salva come…».

Non siamo in produzione: la migration su una tabella di preferenze non ha un
vincolo di compatibilità da rispettare, e il backfill a `nome='Default'` copre
ogni riga esistente.

---

## DEF-4 — Condivisione viste tra utenti

**Stato:** ⏸️ Rimandata · **Sforzo:** M · **Prerequisito hard:** DEF-3

### Cosa serve

Un responsabile crea una vista e la condivide col reparto; i colleghi possono
adottarla (copia personale modificabile).

### Decisioni operative aperte

1. **Scope**: solo reparto (`unita_organizzativa_id`), o anche per profilo di
   accesso, o entrambi?
2. **Modifica della vista condivisa**: solo l'autore? anche l'amministratore del
   reparto? Quando l'autore modifica, le copie adottate seguono o restano
   fissate al momento dell'adozione?
3. **Autore che lascia il reparto**: le viste condivise restano? passano a chi?
4. **Rispetto ai preset**: che cosa porta la condivisione d'utente che un preset
   dell'amministratore non porta già?

### Architettura

- **DB**: `autore_auth_user_id`, `visibile_reparto BOOLEAN`,
  `unita_organizzativa_id` (nullable) su `lista_preferenza_utente`.
- **BE**: visibilità in sola lettura sulle viste pubbliche del reparto +
  endpoint «adotta» (copia profonda).
- **FE**: sezione «Viste condivise» nella modale + flag «Condividi col reparto»
  al salvataggio.

---

## Le dashboard configurabili — la domanda che questa roadmap non copre

Nello schema `ui` ci sono sei tabelle che nessuna voce DEF menziona:
`widget`, `dashboard_widget`, `dashboard_definizione`, `dashboard_preset`,
`dashboard_preset_widget`, `dashboard_preferenza_utente`.

Lo stesso pattern di configurabilità — catalogo, preset di sistema, preferenza
utente — è stato esteso alle **dashboard**. Da decidere se le voci ancora aperte
qui sopra valgono anche di là:

- una **vista nominata** (DEF-3) ha senso anche per una dashboard? E la
  **condivisione** (DEF-4)?
- se sì, conviene progettarle una volta sola sui due domini invece di scoprire
  fra sei mesi che le dashboard hanno preso una strada diversa.

Non è una voce di lavoro: è la domanda da porsi **prima** di aprire DEF-3.
