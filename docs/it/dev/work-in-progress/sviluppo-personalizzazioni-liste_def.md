# Personalizzazioni liste — sviluppi ancora aperti

> **Scopo**: le sole voci DEF **non realizzate**. Tutto ciò che è atterrato —
> DEF-1, DEF-2, DEF-5b, DEF-6, DEF-8, DEF-10 — vive nel
> [consuntivo in work-done](../work-done/consuntivo-personalizzazioni-liste-def.md),
> con i numeri misurati e le convenzioni da rispettare per ogni lista nuova.
> **Piano madre**: [sviluppo-personalizzazioni-liste.md](../work-done/sviluppo-personalizzazioni-liste.md) (Blocchi A..F).
> **Ultima verifica contro il sistema vivo**: 2026-08-09 (DEF-3/DEF-4);
> revisione del perimetro 2026-08-22.

<!-- markdownlint-disable-next-line MD028 -->
> ⭐ **Dove è finito il lavoro sulle liste (2026-08-22).** Il roll-out non passa
> più da qui. Il binario operativo è **§8-bis del
> [piano-migrazione-primevue-5.md](piano-migrazione-primevue-5.md)**, che ha
> assorbito per intero quello che questo documento chiamava DEF-8: liste
> convertite a `<ListaConfigurabile>` **31/35** file (i 4 residui fermi per la
> «decisione 4», non per debito), **46/46** codici nel presidio, binario
> dichiarato chiuso il 2026-08-03. Da lì in avanti la regola non è più un
> arretrato da consumare: *quando si tocca una lista per altri motivi, la si fa
> passare dal building block*. Chi cerca lo stato delle liste guarda quel piano,
> non questo file.
>
> Anche **DEF-10** (colonne composte FE-only) si è chiuso di là: `campo_sorgente`
> vuoto a catalogo + slot `cell-{codice}` nel caller è oggi una **regola scritta
> nel generatore di seed**, non un'ipotesi (piano PrimeVue §8-bis, riga della
> tabella «cosa il generatore non deve dedurre», e i lotti del 2026-08-02).
> È il precedente che chiude anche DEF-7 — vedi sotto.
>
> **Quello che resta qui è solo ciò che il piano PrimeVue non tocca**: viste
> nominate (DEF-3), condivisione (DEF-4) e la domanda sulle dashboard
> configurabili. Verificato: in tutto il piano PrimeVue non compare una sola
> occorrenza di *vista nominata*, *condivisione*, `lista_preferenza_utente` o
> `tipo_colonna='calcolata'`. Non sono «già fatte altrove»: sono **non fatte**.

<!-- markdownlint-disable-next-line MD028 -->
> ℹ️ **Perché questo documento si è accorciato.** Fino al 2026-08-09 conteneva
> l'intera roadmap DEF-1..DEF-10 e dichiarava DEF-8 «in corso, 7 liste migrate,
> ~7 residue». Le liste a catalogo erano già **43**, e tutte e sette le
> «residue» erano dentro da tempo. Un documento che descrive come da fare cose
> fatte non è incompleto: è **fuorviante**, perché chi lo apre crede di avere
> davanti un lavoro che non esiste. Le voci qui sotto sono invece vere, e
> verificate sul database.

---

## Stato in una tabella

| # | Voce | Stato | Sforzo | Priorità | Prerequisito |
| --- | --- | --- | --- | --- | --- |
| DEF-3 | Viste nominate multiple per utente | 🔴 Todo | L | Bassa | migration `lista_preferenza_utente` |
| DEF-4 | Condivisione viste tra utenti | 🔴 Todo | M | Bassa | DEF-3 (hard) |
| DEF-7 | Colonne calcolate (`tipo_colonna='calcolata'`) | ⚪ **Chiusa — non necessaria** (2026-08-22) | — | — | — |
| — | Le dashboard configurabili seguono questa roadmap? | ❓ Da decidere | — | — | vedi ultima sezione |

**Verificato il 2026-08-09**: `ui.lista_preferenza_utente` ha 7 righe con una sola
preferenza per coppia utente/lista (DEF-3 non c'è); i `tipo_colonna` in uso sono
`informazione` 388, `identificatore` 43, `azione` 26 — **nessuna `calcolata`**
(DEF-7 non c'è, e da oggi non ci deve essere).

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

## DEF-7 — Colonne calcolate lato client ⚪ CHIUSA — non necessaria (2026-08-22)

**Cosa chiedeva.** Informazioni che non esistono come colonna nella view SQL ma
si derivano (es. «giorni alla scadenza» = `CURRENT_DATE - data_scadenza`),
dichiarate a **dato** con `tipo_colonna='calcolata'` + `formula_client` e un
registry di funzioni lato Vue.

**Perché si chiude.** Il gemello DEF-10 («colonne composte FE-only») si è
risolto da solo, e nel frattempo il pattern che lo ha risolto è diventato la
prassi scritta: `campo_sorgente` vuoto a catalogo + slot `cell-{codice}` nel
caller è oggi una **regola del generatore di seed**
([piano-migrazione-primevue-5.md](piano-migrazione-primevue-5.md) §8-bis) ed è
in uso su più liste. Una colonna «giorni alla scadenza» si scrive già oggi così,
senza `formula_client` e senza registry.

Restavano due sole cose che `tipo_colonna='calcolata'` avrebbe aggiunto rispetto
al pattern composte, e nessuna delle due regge il proprio costo:

1. **Dichiarare la formula a dato invece che a codice.** Vantaggio nullo
   nell'uso reale — la formula la scrive comunque uno sviluppatore, e a codice
   è tipizzata, testabile e versionata con il caller. A dato diventa una
   micro-lingua da progettare, validare e mantenere.
2. **Renderla esportabile.** L'export è lato BE: la formula andrebbe valutata
   **anche** in Python, cioè scritta due volte. Due verità sullo stesso valore è
   esattamente il difetto che il progetto evita per regola
   ([[feedback_duplicazione_nasconde_il_bug]]). L'alternativa coerente — non
   esportabili, come `tipo_colonna='azione'` — è già ciò che fa il pattern
   composte, gratis.

A queste si aggiungeva un vincolo mai risolto: **ordinare** un valore calcolato
lato FE richiederebbe calcolarlo su tutte le pagine, incompatibile con
LIMIT/OFFSET.

**Conseguenza operativa.** Nessuna riga con `tipo_colonna='calcolata'` va
seedata. Una colonna derivata si fa con lo slot del caller; se deve essere
**ordinabile o esportabile**, non è una colonna calcolata: è una colonna che
manca nella `vista_sql` e va chiesta al team DB.

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
