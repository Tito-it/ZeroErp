# Personalizzazioni liste — sviluppi ancora aperti

> **Scopo**: le sole voci DEF **non realizzate**. Tutto ciò che è atterrato —
> DEF-1, DEF-2, DEF-5b, DEF-6, DEF-8, DEF-10 — vive nel
> [consuntivo in work-done](../work-done/consuntivo-personalizzazioni-liste-def.md),
> con i numeri misurati e le convenzioni da rispettare per ogni lista nuova.
> **Piano madre**: [sviluppo-personalizzazioni-liste.md](../work-done/sviluppo-personalizzazioni-liste.md) (Blocchi A..F).
> **Ultima verifica contro il sistema vivo**: 2026-08-09.

<!-- markdownlint-disable-next-line MD028 -->
> ℹ️ **Perché questo documento si è accorciato.** Fino al 2026-08-09 conteneva
> l'intera roadmap DEF-1..DEF-10 e dichiarava DEF-8 «in corso, 7 liste migrate,
> ~7 residue». Le liste a catalogo erano già **43**, e tutte e sette le
> «residue» erano dentro da tempo. Un documento che descrive come da fare cose
> fatte non è incompleto: è **fuorviante**, perché chi lo apre crede di avere
> davanti un lavoro che non esiste. Le tre voci qui sotto sono invece vere, e
> verificate sul database.

---

## Stato in una tabella

| # | Voce | Stato | Sforzo | Priorità | Prerequisito |
| --- | --- | --- | --- | --- | --- |
| DEF-3 | Viste nominate multiple per utente | 🔴 Todo | L | Bassa | migration `lista_preferenza_utente` |
| DEF-4 | Condivisione viste tra utenti | 🔴 Todo | M | Bassa | DEF-3 (hard) |
| DEF-7 | Colonne calcolate (`tipo_colonna='calcolata'`) | 🔴 Todo | L | Futura | contratto formula stabile |
| — | Le dashboard configurabili seguono questa roadmap? | ❓ Da decidere | — | — | vedi ultima sezione |

**Verificato il 2026-08-09**: `ui.lista_preferenza_utente` ha 7 righe con una sola
preferenza per coppia utente/lista (DEF-3 non c'è); i `tipo_colonna` in uso sono
`informazione` 388, `identificatore` 43, `azione` 26 — **nessuna `calcolata`**
(DEF-7 non c'è).

---

## DEF-3 — Viste nominate multiple per utente

**Stato:** 🔴 Todo · **Sforzo:** L

**Cosa serve**

Oggi `lista_preferenza_utente` ha `UNIQUE (auth_user_id, lista_id)` → una sola
preferenza per lista. Si vogliono viste nominate («Clienti morosi», «Clienti
TOP», «Vista rapida») con switch rapido.

**Decisioni operative aperte**

1. **Schema**: aggiungere `nome VARCHAR(80)` + `is_attiva BOOLEAN`. Sostituire
   l'UNIQUE con `(auth_user_id, lista_id, nome)` più un UNIQUE parziale su
   `is_attiva = TRUE` per coppia `(auth_user_id, lista_id)`. Backfill dei dati
   esistenti: `nome='Default'`, `is_attiva=true`.
2. **Limite viste**: tetto rigido (es. 10 per lista per utente) o avviso morbido?
3. **UX**: selettore viste `<Select>` in toolbar accanto a «Personalizza»?
   «Salva come…» con copia profonda?

**Architettura**

- **DB**: migration su `lista_preferenza_utente` (colonne + UNIQUE + backfill).
  Brief al team DB non banale.
- **BE**: endpoint `GET/POST/PUT/DELETE /api/v1/ui/liste/{codice}/preferenze[/{id}]`;
  l'endpoint config attuale servirebbe la vista attiva.
- **FE**: selettore in toolbar (probabile BB nuovo `ListaViewSelect.vue`) +
  drawer «Salva come…».

### Nota di realtà (2026-08-09)

La tabella ha **7 righe in tutto**. La migration è quindi a rischio quasi nullo —
il documento originale la segnalava come delicata «su tabella popolata in
produzione», ma popolata non è, e in produzione non ci siamo. Se DEF-3 si fa, si
fa adesso che costa poco.

---

## DEF-4 — Condivisione viste tra utenti

**Stato:** 🔴 Todo · **Sforzo:** M · **Prerequisito hard:** DEF-3

**Cosa serve**

Un responsabile crea una vista e la condivide col reparto; i colleghi possono
adottarla (copia personale modificabile).

**Decisioni operative aperte**

1. **Scope**: solo reparto (`unita_organizzativa_id`), o anche per profilo di
   accesso, o entrambi?
2. **Modifica della vista condivisa**: solo l'autore? anche l'amministratore del
   reparto? Quando l'autore modifica, le copie adottate seguono o restano
   fissate al momento dell'adozione?
3. **Autore che lascia il reparto**: le viste condivise restano? passano a chi?

**Architettura**

- **DB**: `autore_auth_user_id`, `visibile_reparto BOOLEAN`,
  `unita_organizzativa_id` (nullable) su `lista_preferenza_utente`.
- **BE**: visibilità in sola lettura sulle viste pubbliche del reparto +
  endpoint «adotta» (copia profonda).
- **FE**: sezione «Viste condivise» nella modale + flag «Condividi col reparto»
  al salvataggio.

---

## DEF-7 — Colonne calcolate lato client (e la fusione con DEF-10)

**Stato:** 🔴 Todo · **Sforzo:** L

**Cosa serve**

Informazioni che non esistono come colonna nella view SQL ma si derivano (es.
«giorni alla scadenza» = `CURRENT_DATE - data_scadenza`). Proposta:
`tipo_colonna='calcolata'` + `formula_client VARCHAR(80)` con chiave di funzione
registrata in un registry Vue.

**Decisioni operative aperte**

1. **Contratto della formula**: registry centralizzato
   (`{ 'giorni_scadenza': (row) => … }`), per dominio o globale?
2. **Esportabilità**: se le calcolate finiscono nell'export, la formula andrebbe
   valutata anche lato BE (replicarla costa e crea due verità). Alternativa:
   non esportabili, come `tipo_colonna='azione'`.
3. **Ordinabilità**: ordinare un valore calcolato lato FE richiede calcolarlo su
   tutte le pagine — non regge con LIMIT/OFFSET. Ipotesi: `ordinabile=false` per
   default.

### ⚠️ La domanda vera è se serve ancora

DEF-10 («colonne composte FE-only») era il gemello di questa voce e **si è
risolto da solo**: `campo_sorgente` vuoto a catalogo + slot `cell-{codice}` nel
caller è oggi un pattern in uso in almeno quattro liste. Quel pattern **compone**
campi esistenti; DEF-7 vuole **calcolare** valori nuovi.

Ma implementativamente finiscono nello stesso posto — lo slot del caller — e una
colonna «giorni alla scadenza» si può già fare oggi, senza `formula_client` e
senza registry, esattamente come si fa `sosp_riatt`.

Quindi prima di progettare DEF-7 va risposto: **che cosa aggiunge un
`tipo_colonna='calcolata'` rispetto a ciò che il pattern composte già consente?**
Le risposte plausibili sono due — poter dichiarare la formula a **dato** invece
che a codice, e renderla esportabile lato BE — ed entrambe hanno un costo alto
(punto 2 qui sopra). Se nessuna delle due serve davvero, DEF-7 **si chiude come
non necessaria**, non come «da fare un giorno».

---

## Le dashboard configurabili — la domanda che questa roadmap non copre

Nello schema `ui` sono comparse sei tabelle che nessuna voce DEF menziona:
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
