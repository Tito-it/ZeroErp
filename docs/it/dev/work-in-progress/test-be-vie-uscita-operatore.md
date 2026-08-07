# Test in-app — le vie d'uscita per l'operatore

> **Cosa si sta provando:** la metà a video di
> [brief-db-vie-uscita-operatore.md](../work-done/brief-db-vie-uscita-operatore.md) +
> [brief-be-fe-vie-uscita-operatore.md](../work-done/brief-be-fe-vie-uscita-operatore.md).
> **Chi prova:** Tid, in app.
> **Preparato da:** BE/FE, 2026-08-05. Documento **vivo**: si spunta e si annota
> mentre si prova.
>
> **La regola che si sta verificando** (R1+R3 del brief DB), ed è l'unica cosa da
> tenere in testa guardando ogni schermata:
>
> > **O la via d'uscita c'è, o c'è scritto perché non c'è.**
>
> Tre esiti possibili per ogni caso: ✅ come atteso · ⚠️ funziona ma non convince
> (decisione di dominio da riguardare) · ❌ non torna (difetto). **Annota anche i
> ⚠️**: la metà del valore di questo giro sta lì.

---

## 0. Prerequisiti — da fare PRIMA, o metà delle prove mente

| #   | Cosa                                                                                  | Perché                                                                                                                                                                                                     | ✔   |
| --- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --- |
| P1  | `sudo systemctl reload zeroerp-gunicorn`                                              | Gunicorn in dev **non ha autoreload**: `error_policies.py` è cambiato e senza reload i 409 nuovi escono come errore generico. Un T4 fallito senza aver fatto questo non è un difetto, è un backend vecchio | ☐   |
| P2  | Frontend aggiornato (`vite build` già fatto il 2026-08-05; se usi il dev server, HMR) | Senza, la nota «nessuna azione» non esiste proprio nel bundle                                                                                                                                              | ☐   |
| P3  | L'operatore con cui entri deve avere **l'emittente fiscale 32** nello scope           | Tutti i documenti qui sotto sono di EF=32. Fuori scope non danno errore: **spariscono** (RLS fail-closed) o rispondono 404. Un «documento non trovato» è quasi sempre questo, non un bug                   | ☐   |
| P4  | Se un drawer è rimasto aperto da prima del reload, **chiudilo e riaprilo**            | Le capability sono lette al caricamento del dettaglio: un drawer aperto mostra lo stato di dieci minuti fa. È anche il meccanismo che T4 sfrutta di proposito                                              | ☐   |

---

## 1. Elenco da spuntare (sintesi)

| #   | Caso                                                    | Dove                    | ✔   | Esito |
| --- | ------------------------------------------------------- | ----------------------- | --- | ----- |
| T1  | «Annulla» **acceso** su preventivo ACCETTATO            | `PRV0000192`            | X   | OK    |
| T2  | «Annulla» **acceso** su preventivo EMESSO               | `PRV0000189`            | ☐   | OK    |
| T3  | «Annulla ordine» **acceso** su ordine CONFERMATO        | `ORD0000610`            | ☐   | OK    |
| T4  | «Annulla» **spento col motivo** (tooltip)               | `PRV0000144`            | ☐   | OK    |
| T5  | Nota «nessuna azione» — ordine EVASO                    | `ORD0005175`            | ☐   | OK    |
| T6  | Nota «nessuna azione» — DDT CONSEGNATO                  | `DDT0000338`            | ☐   |       | consegnato reso permesso la ui lo mostra cosi credo giusto |
| T7  | Nota «nessuna azione» — DDT RESO                        | `DDT0000062`            | ☐   |       |
| T8  | Resa responsive della nota (sidebar / finestra stretta) | uno dei T5–T7           | ☐   |       |
| T9  | Il 409 col messaggio di dominio (forzatura a due tab)   | `PRV0000192`            | ☐   |       |
| T10 | L'annullamento **esegue davvero** (stato → ANNULLATO)   | un preventivo di scarto | ☐   |       |

---

## 2. I casi, in dettaglio

### T1 — «Annulla» acceso su preventivo ACCETTATO ☐

**È il verbo che prima non esisteva**: un preventivo ACCETTATO offriva una sola
azione (`push_commessa`) e nient'altro — non si annullava, non tornava indietro.

1. Vendite → Preventivi → cerca **`PRV0000192`** (id 1816, cliente `BAC/0000042`)
2. Click sulla riga → si apre il drawer

**Cosa devi vedere:** nella barra azioni sotto l'intestazione, un pulsante
**Annulla** rosso *outlined*, accanto alle azioni già note (Genera ordine /
Smistamento). Non grigio, non assente.

Alternativa equivalente: `PRV0000191` (id 1271).

> Esito: _______________________________________________

### T2 — «Annulla» acceso su preventivo EMESSO ☐

Stessa cosa dall'altro stato ripristinato. Cerca **`PRV0000189`** (id 535).
Qui l'Annulla convive con Accetta / Rifiuta / Crea revisione: verifica che
**non abbia spinto le altre fuori** dalla barra o sotto il fold.

> Esito: _______________________________________________

### T3 — «Annulla ordine» acceso su ordine CONFERMATO ☐

Vendite → Ordini → **`ORD0000610`** (id 633). Deve comparire **Annulla ordine**
accanto a «Invia a commessa».

⚠️ Nota: è **l'unico** ordine CONFERMATO annullabile in tutto il database
(vedi §4). Se lo annulli in T10, questo caso non è più ripetibile.

> Esito: _______________________________________________

### T4 — Il bottone spento col motivo ☐

**È la novità vera del cantiere**: fino a ieri qui il bottone era *acceso* e il
rifiuto arrivava dopo il click.

Vendite → Preventivi → **`PRV0000144`** (id 302, ACCETTATO, `BAC/0000053`).
Equivalenti: `PRV0000143` (301), `PRV0000141` (299), `PRV0000140` (298).

**Cosa devi vedere:**

- «Annulla» **c'è**, ed è **grigio** — non nascosto (decisione presa: spento con
  motivo è meglio di assente);
- passandoci sopra il mouse, il tooltip dice:
  > *Il preventivo è già stato inviato a fatturazione: annulla prima le attività in commessa.*
- il click non fa nulla.

**Segnale di difetto da riconoscere:** se al posto della frase leggi
`vendite.preventivi.azione_reason.gia_in_commessa`, è una chiave i18n non
risolta. Il guard automatico è verde, quindi non dovrebbe succedere — ma se
succede, quello è il testo da copiare nell'annotazione.

> Esito: _______________________________________________

### T5 — La nota sull'ordine EVASO ☐

Vendite → Ordini → **`ORD0005175`** (id 5388). Equivalente: `ORD0005174` (5387).

**Cosa devi vedere:** nessun pulsante di stato, e al loro posto una riga muted
con icona ℹ️:

> *L'ordine è evaso: lo stato si ricalcola dai DDT, non si imposta a mano.*

**Perché conta:** prima qui c'era **il vuoto** — nessun pulsante e nessuna
spiegazione, indistinguibile da un caricamento fallito.

> Esito: _______________________________________________

### T6 — La nota sul DDT CONSEGNATO ☐

Vendite → DDT → **`DDT0000338`** (id 518). Equivalente: `DDT0000337` (517).

> *La merce è consegnata: per farla rientrare si registra un reso, non si annulla il DDT.*

Questo è il caso in cui la nota non si limita a spiegare: **indica la strada**
(il reso). Valuta se il testo ti sembra abbastanza esplicito per un operatore
che non conosce il modello.

> Esito: _______________________________________________

### T7 — La nota sul DDT RESO ☐

Vendite → DDT → **`DDT0000062`** (id 140). Equivalente: `DDT0000061` (139).

> *Questo DDT è rientrato con un reso: lo stato segue il reso da solo.*

<!-- markdownlint-disable-next-line MD028 -->
> Esito: _______________________________________________

### T8 — Resa responsive della nota ☐

Su uno qualsiasi fra T5–T7:

- **apri e chiudi la sidebar**: la nota deve andare a capo da sola, **senza**
  stringere o mandare a capo i pulsanti accanto (è `flex: 1 1 12rem`);
- **restringi la finestra sotto 1024px** (o prova su tablet): le azioni
  collassano nel kebab `⋮` — la nota deve restare **leggibile e in chiaro**, non
  finire dentro il menu;
- controlla che il tono sia quello di una **risposta**, non di un allarme (grigio
  muted, non un banner colorato). Se ti sembra troppo poco visibile, è un ⚠️ da
  annotare: è una scelta, non un vincolo.

> Esito: _______________________________________________

### T9 — Il 409 col messaggio di dominio (forzatura) ☐

Dopo T4 il messaggio d'errore **non è più raggiungibile dalla UI normale**: il
bottone è spento prima. Resta la difesa in profondità, e per esercitarla serve
una corsa deliberata:

1. apri **`PRV0000192`** (annullabile) e **lascia il drawer aperto**;
2. in un'altra tab, manda lo **stesso** preventivo in commessa (Smistamento);
3. torna alla prima tab — che ha capability stantie — e clicca **Annulla**.

**Cosa devi vedere:** un banner d'errore con il messaggio di dominio
(*«Il preventivo è già stato inviato a fatturazione…»* o *«Righe già fatturate in
commessa…»*).

**Cosa NON devi vedere:** *«Errore durante l'operazione database»* o *«Errore di
validazione»*. Se leggi una di queste due, il sospetto numero uno è **P1 non
fatto** (backend non ricaricato) — verificalo prima di segnalarlo come difetto.

> Esito: _______________________________________________

### T10 — L'annullamento esegue davvero ☐

Finora abbiamo guardato i bottoni. Qui si preme.

⚠️ **ANNULLATO è terminale**: dalla matrice non esiste transizione in uscita. Il
documento che scegli è **bruciato**. Candidato di scarto suggerito:
**`PRV0000188`** (id 534, EMESSO, `BAC/0000053`) — non il più recente, non uno di
quelli già in commessa.

1. apri il preventivo, click **Annulla**
2. deve comparire il **dialog di conferma** (`requires_confirm` è nel seed)
3. conferma

**Cosa devi vedere:** toast di successo, il drawer si ricarica, il **Tag di stato
diventa ANNULLATO**, e la barra azioni si aggiorna da sola.

**Da guardare subito dopo, ed è la prova più interessante del giro:** dallo stato
ANNULLATO **che cosa offre il drawer?** Se la barra resta vuota e muta, abbiamo
appena creato un settimo stato senza uscita e senza spiegazione — cioè
esattamente il difetto che questo cantiere è nato per chiudere, su uno stato che
prima nessuno raggiungeva. **Annotalo: è il primo posto dove mi aspetto che
qualcosa non torni.**

> Esito: _______________________________________________

---

## 3. Cosa non torna — da compilare mentre provi

Per ogni anomalia, questi quattro dati mi bastano quasi sempre per capire senza
farti riprovare:

| Dato                                   | Dove prenderlo                                                                           |
| -------------------------------------- | ---------------------------------------------------------------------------------------- |
| **Documento**                          | numero + id (es. `PRV0000144` / 302)                                                     |
| **Cosa ti aspettavi / cosa hai visto** | una riga per parte                                                                       |
| **`request_id`**                       | è nel banner d'errore, o nella risposta API (`meta.request_id`) — mi porta dritto al log |
| **Codice errore o chiave grezza**      | il `code` del banner (es. `E_DATABASE`), oppure la chiave i18n se la vedi a video        |

### Registro

| #   | Caso | Documento | Cosa hai visto | Tipo  |
| --- | ---- | --------- | -------------- | ----- |
| A1  |      |           |                | ⚠️ / ❌ |
| A2  |      |           |                | ⚠️ / ❌ |
| A3  |      |           |                | ⚠️ / ❌ |

### Sospetti tipici, per non perdere tempo

| Sintomo                                                         | Prima causa da escludere                                                                       |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Errore generico invece del messaggio di dominio                 | **P1**: backend non ricaricato                                                                 |
| La nota «nessuna azione» non compare da nessuna parte           | **P2**: frontend non aggiornato                                                                |
| Il documento non si trova / 404 aprendolo                       | **P3**: emittente fuori scope (RLS), non un bug                                                |
| Il bottone è acceso quando dovrebbe essere spento (o viceversa) | **P4**: drawer aperto da prima, capability stantie. Chiudi e riapri                            |
| Vedi una chiave (`vendite.…`) al posto del testo                | Chiave i18n mancante nei locales — copiala pari pari                                           |
| Il testo c'è ma è sbagliato/ambiguo                             | **Non è un difetto tecnico**: è un dato (`meta` dello stato). Si cambia il seed, non il codice |

---

## 4. Cosa NON è provabile oggi, e non è un difetto

Scritto qui perché «non l'ho trovato» non diventi una segnalazione.

| Caso                                                                        | Perché                                                                                                                                                                                                                                                                                                |
| --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Ordine con annullamento bloccato** (bottone spento + motivo, lato ordini) | Nel database **non esiste un solo ordine** in questa condizione: il ramo `reasons` dell'ordine non è mai passato per il video. È lo stesso codice del preventivo (che T4 esercita), ma resta non osservato. Se crei un ordine CONFERMATO con un DDT collegato, quello è il caso da guardare per primo |
| **Nota su ordine PARZIALMENTE_EVASO**                                       | La chiave è seminata, ma nessun ordine in quello stato riceve la nota: hanno tutti ancora azioni vive. Coerente con la regola, vedi §5                                                                                                                                                                |

## 5. La decisione lasciata aperta — guardala mentre provi

Il team DB ha dichiarato che **5 ordini EVASO su 32 non ricevono la nota**,
perché hanno ancora «Invia a fatturazione» abilitata: la regola è «la nota
risponde alla lista vuota», e con un bottone vivo la lista vuota non c'è.

Se durante T5 ti capita un ordine EVASO **con** un pulsante acceso e **senza**
spiegazione dello stato, la domanda è:

> «Evaso» è un'informazione che serve all'operatore **anche** quando c'è ancora
> qualcosa da fare, o solo quando non c'è più niente?

Lato frontend **non c'è alcun vincolo**: la nota si affianca già alle azioni vive
(è una riga in coda alla barra, non un rimpiazzo dei pulsanti). Se decidi che la
spiegazione accompagna sempre lo stato chiuso, costa **una riga in tre funzioni
DB e zero righe di frontend**. È una scelta di dominio, ed è tua.

> Decisione: _______________________________________________

---

## 6. Rigenerare l'elenco dei documenti

Gli id/numeri qui sopra sono una **fotografia del 2026-08-05**: se nel frattempo
qualcuno annulla o fattura, cambiano. Per rifare la lista (dal server backend,
canale di sistema — le tabelle hanno RLS e senza contesto si legge zero e si
conclude il falso):

```sql
-- preventivi con l'azione annulla, divisi fra accesi e spenti
SELECT p.id, p.numero, s.codice_interno,
       a->>'enabled' AS acceso,
       (SELECT string_agg(r->>'codice', ',')
          FROM jsonb_array_elements(COALESCE(a->'reasons','[]'::jsonb)) r) AS motivi
  FROM vendite.preventivi p
  JOIN config.stati_doc_preventivi s ON s.id = p.stato_doc_preventivo_id
  CROSS JOIN LATERAL jsonb_array_elements(
        script.fn_available_actions_preventivo(p.id)->'available_actions') a
 WHERE a->>'key' = 'annulla'
 ORDER BY acceso DESC, p.id DESC;

-- documenti in stato chiuso che espongono la nota (ordini e DDT)
SELECT 'ORD' AS tipo, o.id, o.numero, x.nota
  FROM vendite.ordini o
  CROSS JOIN LATERAL (SELECT script.fn_available_actions_ordine(o.id)
                             ->>'nessuna_azione_key' AS nota) x
 WHERE x.nota IS NOT NULL
UNION ALL
SELECT 'DDT', d.id, d.numero, x.nota
  FROM vendite.ddt d
  CROSS JOIN LATERAL (SELECT script.fn_available_actions_ddt(d.id)
                             ->>'nessuna_azione_key' AS nota) x
 WHERE x.nota IS NOT NULL
 ORDER BY 1, 2 DESC;
```

> ⚠️ **Non usare `blob ? 'nessuna_azione_key'`** per filtrare. La chiave è
> **sempre presente** nel blob: quando non si applica il valore è `null`, non è la
> chiave a mancare. Il test di presenza risponde quindi vero per **tutti** i
> documenti (118 invece di 36, misurato). Va guardato il **valore**, non la
> chiave. Nessuna conseguenza lato frontend — `null` è falsy e la nota non viene
> resa — ma è una trappola per chiunque scriva una query o un pgTAP su questo
> campo.
