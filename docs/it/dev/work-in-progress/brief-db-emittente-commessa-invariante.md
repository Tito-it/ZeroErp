# Brief DB — l'emittente della commessa è un invariante, e oggi non lo presidia nessuno

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine.** Tid, 2026-08-26, chiudendo la D-6 di
> [brief-db-registro-e-data-prevista-in-competenza.md](../work-done/brief-db-registro-e-data-prevista-in-competenza.md).
> Avevo segnalato come debito minore che `vendite.commesse.emittente_soggetto_ruolo_id`
> è nullable e non legata al billing account. Risposta di Tid: *«allora hai
> scoperto un bug!! la commessa dovrebbe derivare sempre l'emittente dalla
> cascata delle sorgenti, una commessa non può aggregare diversi emittenti
> insieme e di conseguenza non può avere emittente null»*.
>
> ⭐ **Guardandolo davvero, il ramo peggiore non è quello che avevo segnalato.**
>
> ✅ **Decisioni prese** (Tid, 2026-08-26): **D-1** — nessuna «cascata delle
> sorgenti», l'emittente si prende **dal billing account**, sempre derivato e mai
> passato da fuori. **H1** — la colonna **non può essere NULL**, si corregge.
>
> ⛔ **Separato**: la domanda «un BA può cambiare emittente?» (era H3/D-3) è
> **uscita da qui** ed è diventata
> [brief-db-billing-account-cambio-emittente.md](brief-db-billing-account-cambio-emittente.md)
> — su richiesta di Tid, perché è una riflessione di dominio con implicazioni
> fiscali e mescolarla farebbe rimandare una correzione che invece è chiara.
>
> ⛔ **Stato: nessun file scritto. Restano due decisioni, non quattro.**

---

## 1. Il difetto in una frase

`vendite.commesse.emittente_soggetto_ruolo_id` **non è un attributo della
commessa: è la sua chiave di perimetro**. Ci si appoggiano la row security della
tabella, il filtro di scope delle viste del cruscotto e il giornale degli eventi.
Ma la colonna è **nullable**, **non vincolata al billing account** e **congelata
alla nascita** — tre proprietà che per un attributo qualsiasi sarebbero
irrilevanti, e per una chiave di perimetro sono un difetto.

⚠️ **Questo brief NON dice che oggi ci siano righe sbagliate**, e non è la
domanda giusta: la domanda è *«il modello lo ammette?»*
(`.codex/AGENTS.md` § «Regola zero — le misure non disegnano il progetto»). Tutti gli argomenti qui
sotto sono letti sulla **struttura** — colonne, vincoli, policy, trigger, corpi
di funzione.

---

## 2. ⛔ H1 — con l'emittente a NULL la commessa **sparisce**, e non è un modo di dire

`vendite.commesse` ha la row security accesa, con **una** policy, e vale per
**tutti** i comandi (`polcmd = '*'`, quindi anche `UPDATE` e `DELETE`):

```sql
rls_commesse_ef_whitelist USING (
    current_setting('app.ruolo_applicativo', true) = 'OPERATORE'
    AND script.fn_scope_ef_whitelist_via_sr(
            current_setting('app.current_user_id', true)::integer,
            emittente_soggetto_ruolo_id)
)
```

E il gemello che risolve dalla commessa lo dichiara nel proprio corpo, testuale:

> *«Commessa inesistente / emittente NULL → SR NULL → false (fail-closed se
> whitelist valorizzata)»*

⇒ Per un operatore con perimetro ristretto, una commessa con emittente NULL
**non esiste**: non la legge, non la modifica, non la cancella. E la stessa
condizione è ricopiata nel `WHERE` di `vw_dash_competenza_attivita`
(`co.emittente_soggetto_ruolo_id = ANY(escope.sr_ids)`), quindi sparisce anche
dal cruscotto competenza e da tutto ciò che ci si appoggia.

⭐ **La forma del danno è la peggiore possibile**: non un errore, non una riga
sbagliata a video. **Lavoro che esiste nel database, non compare da nessuna
parte e non viene mai fatturato** — e nessuno se ne accorge, perché una lista che
non mostra una riga ha esattamente lo stesso aspetto di una lista in cui quella
riga non c'è.

⚠️ È la classe di difetto già a registro nel progetto: *uno zero può essere
fail-closed, non un dato*. Qui però non è un conteggio: è la riga intera.

⭐ **E non è un caso isolato: è una famiglia.**
[brief-db-lavoro-che-non-torna-indietro.md](brief-db-lavoro-che-non-torna-indietro.md)
descrive lo stesso tipo di danno per un'altra causa — un'attività che resta
marcata come fatturata dopo che la sua fattura è stata eliminata, e che nessuno
rimette mai in coda. ⚠️ Le due cose **non hanno oggetti in comune** e non vanno
unite; ma chi un giorno cercherà «perché questo lavoro non è stato fatturato»
deve trovarle **entrambe**, perché il sintomo è lo stesso e la causa no.

---

## 3. I quattro buchi, e cosa li lascia aperti

| | Buco | Cosa lo lascerebbe chiuso, e non c'è |
| --- | --- | --- |
| **H1** | La colonna è **nullable** | un `NOT NULL`. Oggi il valore lo garantisce solo il fatto che `anagrafiche.fn_get_emittente_fiscale_id` **solleva** invece di tornare NULL — cioè una proprietà di una funzione, non del dato |
| **H2** | **Nessun vincolo la lega al billing account** | un guard di coerenza. `fn_get_or_create_commessa` accetta `p_emittente_soggetto_ruolo_id` e fa `COALESCE(override, risolto dal BA)`: l'override passa **qualunque** `soggetto_ruolo_id` esista, e la sola FK non guarda il BA |
| **H4** | Le **sorgenti** si collegano senza controllo di omogeneità | un guard su `fn_link_commessa_sorgente`, che dell'emittente non sa nulla. È il «non può aggregare diversi emittenti» detto da Tid, sull'asse dei documenti invece che su quello dei BA |

> ⛔ **H3 è uscito da questo brief.** Era «la colonna è una fotografia scattata
> alla nascita, e se il mapping del BA cambia diventa stantìa». Dietro c'è una
> domanda di dominio — *un billing account può cambiare emittente?* — che ha
> implicazioni fiscali e va **pensata**, non programmata:
> [brief-db-billing-account-cambio-emittente.md](brief-db-billing-account-cambio-emittente.md).
> ⭐ **E questo cantiere non la aspetta**: `NOT NULL` più il vincolo al billing
> account sono giusti qualunque risposta si dia là.

⭐ **Un indizio che il difetto è già stato sfiorato**: dentro
`fn_get_or_create_commessa` la ricerca della commessa esistente confronta
`COALESCE(c.emittente_soggetto_ruolo_id, -1) = COALESCE(v_emittente, -1)`. Quel
`COALESCE` difende da un NULL che **non dovrebbe potere esistere**. Quando il
codice si protegge da uno stato impossibile, di solito è perché impossibile non è.

---

## 4. ✅ Cosa invece è presidiato bene, e non va ridiscusso

L'**albero dei billing account** è omogeneo per emittente, e per davvero:
`anagrafiche.fn_guard_albero_ba_emittente` controlla verso il padre **e verso
tutti i figli**, è agganciata da due trigger `z95` (uno sullo spostamento del BA,
uno sul cambio di mapping), gira `SECURITY DEFINER` perché altrimenti la row
security nasconderebbe proprio il caso da bloccare, è fail-closed sul NULL e non
ha nessuna GUC di override — *«un invariante con l'interruttore non è un
invariante»*.

⇒ **Padre e figlio non possono avere due emittenti diversi.** È il modello di
presidio che manca alla commessa, e la buona notizia è che esiste già in casa: si
tratta di estenderlo di un anello, non di inventarlo.

---

## 5. La forma della soluzione — ⚠️ proposta, non decisione

1. **`NOT NULL` sulla colonna.** È l'unica delle quattro che non richiede
   discussione: una chiave di perimetro nullable è un buco per definizione.
2. **Una sede unica che risolve l'emittente della commessa**, chiamata sia da
   `fn_get_or_create_commessa` sia dal guard — la disciplina «si condivide la
   funzione, non una copia della sua logica», la stessa del cantiere gemello.
3. **Un guard di coerenza** sul modello di `fn_guard_albero_ba_emittente`: la
   commessa deve concordare con il proprio billing account (H2) e con le proprie
   sorgenti (H4).
4. ⛔ **Niente di più.** Il caso «e se il BA cambiasse emittente?» **non si
   progetta qui**: è l'altro brief, e questo cantiere è corretto comunque vada a
   finire là.

---

## 6. ❓ Le decisioni aperte

### ✅ D-1 CHIUSA — non esiste nessuna cascata: la sede è il billing account

> ✅ **Tid, 2026-08-26**: *«hai ragione a correggermi, non esiste una cascata
> delle sorgenti; giusto che l'emittente venga preso dal billing account»*.

⇒ La frase d'origine («derivare dalla cascata delle sorgenti») voleva dire
**sempre derivato, mai passato da fuori**. La catena resta quella che c'è già —
`anagrafiche.fn_get_emittente_fiscale_id`: mapping specifico del BA, poi default
globale — e non se ne inventa una seconda.

⭐ Con questa risposta **D-2 si inclina da sola**: se l'emittente è sempre
derivato, un parametro che permette di passarlo dall'esterno non ha più una
ragione d'essere.

### D-2 — l'override `p_emittente_soggetto_ruolo_id` si toglie o si controlla?

Se l'emittente è **sempre derivato**, quel parametro non ha ragione di esistere e
va tolto — ⚠️ ma è nella firma di una funzione che il backend chiama in due
punti, quindi è una consegna BE, non solo DB. Se invece resta, dev'essere
**verificato** contro il BA invece che accettato.

### ~~D-3 — cambiare l'emittente di un BA che ha già commesse~~ → trasferita

⛔ **Non è più una domanda di questo cantiere.** È diventata un brief suo, perché
la risposta non è tecnica: *«non può scomparire un cliente che ha già delle
fatture con un emittente perché è andato ad un altro»* (Tid).
▶ [brief-db-billing-account-cambio-emittente.md](brief-db-billing-account-cambio-emittente.md).

### D-4 — le sorgenti eterogenee (H4): si bloccano o si tollerano?

Bloccarle è coerente con «una commessa non può aggregare diversi emittenti». ⚠️
Ma un guard restrittivo su `fn_link_commessa_sorgente` va prima misurato contro i
pgTAP esistenti: è il percorso da cui passa la costruzione delle commesse in
tutti i test.

---

## 7. Registro

### 2026-08-26 · Nascita

Nato da una segnalazione che avevo classificato **minore** chiudendo la D-6 del
cantiere «registro e data prevista». Approfondendola su richiamo di Tid è emerso
che la colonna non è un attributo ma la **chiave di perimetro** della commessa —
row security, scope delle viste del cruscotto, giornale degli eventi — e che il
ramo peggiore (**H3**, la fotografia che invecchia) non richiede nessun errore da
parte di nessuno.

⛔ Nessun file scritto, nessuna migrazione. Quattro decisioni aperte, e la prima
(che cos'è la cascata) va chiusa prima delle altre tre.

### 2026-08-26 · Prime decisioni, e una separazione

✅ **D-1 chiusa** (nessuna cascata: la sede è il billing account) e **H1
confermato** da correggere. ⭐ D-1 chiusa inclina D-2: se l'emittente è sempre
derivato, l'override non serve.

⛔ **H3 e D-3 sono usciti da questo brief** su richiesta di Tid — *«dobbiamo
riflettere su questo e non mescolare»*. Sono diventati
[brief-db-billing-account-cambio-emittente.md](brief-db-billing-account-cambio-emittente.md):
là c'è una domanda di dominio con implicazioni fiscali, qui un difetto con un
rimedio chiaro. ⭐ **Separarli serve a non far aspettare il secondo per colpa del
primo**: `NOT NULL` più il vincolo al billing account restano giusti qualunque
risposta si dia là.
