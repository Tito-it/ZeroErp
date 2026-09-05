# Piano BE/FE — la UI dei permessi di un operatore

> **Che cos'è questo documento.** Il **piano operativo** della ristrutturazione
> grafica del pannello permessi. Le decisioni sono già prese e motivate in
> [analisi-ui-permessi-operatore.md](analisi-ui-permessi-operatore.md) §7.
> ⛔ **Qui non si riaprono**: si traduce in componente, endpoint, store e i18n.
>
> **Destinatario:** backend e frontend (`dev/backend-tid`).
>
> **Stato:** 🟢 **ESEGUITO (2026-09-05)** — BE, BB e conversione del tab fatti.
> **4434 test backend verdi**, lint e build frontend puliti. Resta il collaudo a
> video (§6), che è l'unica verifica possibile: questo repo non ha una suite FE.
>
> ⚠️ **Uno scostamento dal piano, e vale la pena saperlo**: il §4.2 prevedeva un
> test automatico che confronta l'ereditato con `fn_resolve_livello_area`. Non è
> scrivibile come test Django — in questo repo **nessun test tocca un database
> reale** (vincolo CI). La verifica è stata **eseguita a mano** sul database di
> sviluppo (tutti gli utenti senza override: livelli coincidenti su tutte le
> aree) e in suite è rimasta la forma sorella che questo repo usa per i criteri:
> si legge l'**SQL generato** e si prova che usa `fn_get_profili_accesso_applicabili`
> e che sceglie per `h.priorita`. ⇒ La versione durevole è un **pgTAP**, ed è da
> chiedere al team DB.
>
> ⚠️ **Perimetro**: **nessun cambio di funzionalità dei permessi.** Il tetto
> d'area resta **fuori** — è un difetto segnalato in §3 dell'analisi, non lavoro
> di questo piano. Qui si cambia solo *come si vede e si imposta* ciò che il
> sistema già fa.

---

## 0. In due parole

Oggi il pannello mostra **le eccezioni**: tre tabelle di override che per un
utente appena creato sono **vuote**, da cui non si capisce niente. Si passa a
tre tabelle che mostrano **tutte le voci** — 13 aree, 34 azioni, 12 oggetti —
ognuna con il livello che ha, da dove viene, e un'azione per cambiarlo.

Il grosso è frontend. Il backend aggiunge **una lettura sola**: il valore che
l'utente eredita dal profilo, che oggi nessun endpoint sa dire per utente.

---

## 1. Il pezzo di backend — l'ereditato per utente

### 1.1 Perché serve, e perché quello che c'è non basta

Per non far scrivere un override che ripete il profilo (§7.7 dell'analisi), la
riga deve mostrare **il valore ereditato**. Il solo endpoint che oggi ci somiglia
è `GET /amm-software/reparti/<uo_id>/profilo/`, che legge il binding
**`REPARTO`** e basta. ⛔ Non è la stessa cosa: i bindings sono **tre**
(`AD_HOC` priorità 1, `PORTALE` e `REPARTO` priorità 2) e i resolver prendono
`ORDER BY priorita LIMIT 1`. Con un binding `AD_HOC` quel valore sarebbe
sbagliato — su una schermata di sicurezza.

### 1.2 L'endpoint

```
GET /api/v1/amm-software/operatori/<auth_user_id>/permessi-ereditati/
```

```json
{
  "data": {
    "aree": [
      { "area_id": 3, "codice": "VEN", "livello": "LETTURA",
        "profilo_nome": "Back-office", "profilo_tipo": "REPARTO" }
    ],
    "azioni": [
      { "azione_id": 12, "permission_codename": "genera_fatture_lotti",
        "abilitata": true,
        "profilo_nome": "Back-office", "profilo_tipo": "REPARTO" }
    ]
  }
}
```

- ⛔ **Niente `oggetti`**: `config.profili_accesso_oggetti` non esiste. Per un
  model l'ereditato è il livello dell'**area**, che il frontend ha già dalla
  lista aree — chiederlo al backend sarebbe una seconda risposta alla stessa
  domanda.
- Assenza di una voce = **nessun profilo la copre** ⇒ il default (`BLOCCATO` /
  azione negata). Il frontend lo rende come «default», non come vuoto.

### 1.3 Come si legge, senza rifare la catena

La sorgente è **la stessa funzione dei resolver**,
`script.fn_get_profili_accesso_applicabili(auth_user_id)`, che restituisce già
`(profilo_accesso_id, priorita)`:

```sql
SELECT DISTINCT ON (paa.area_id)
       paa.area_id, af.codice, af.descrizione,
       paa.livello::text, pa.descrizione AS profilo_nome, pa.tipo::text
  FROM script.fn_get_profili_accesso_applicabili(%s) h
  JOIN config.profili_accesso_aree paa ON paa.profilo_accesso_id = h.profilo_accesso_id
  JOIN config.profili_accesso     pa  ON pa.id = h.profilo_accesso_id
  JOIN config.aree_funzionali     af  ON af.id = paa.area_id
 ORDER BY paa.area_id, h.priorita;
```

⚠️ **Ciò che si ripete è il `ORDER BY priorita LIMIT 1`, non la catena** —
l'insieme dei profili e le loro priorità vengono dalla funzione. È il minimo
duplicabile, ma resta una seconda scrittura di un criterio: **si presidia con il
test di §4.2**, che è il modo per accorgersi se un giorno divergono.

### 1.4 Dove si tocca

| File | Cosa |
| --- | --- |
| `backend/apps/amm_software/db/amm_software_repository.py` | `get_permessi_ereditati(auth_user_id)` — le due query sopra |
| `backend/apps/amm_software/services/amm_software_service.py` | passacarte + `get_operatore()` per l'esistenza |
| `backend/apps/amm_software/api/views.py` | `PermessiEreditatiView(AdminAPIView)`, solo `GET` |
| `backend/apps/amm_software/api/urls_v1.py` | la rotta |
| `docs/it/backend/amm_software/manual/api_*.md` | il contratto |

---

## 2. Il building block — `MatriceOverride.vue`

✅ **Estrazione approvata da Tid il 2026-09-05** (regola del 2: secondo uso del
pattern slot/override, il primo è il tab Utilities degli emittenti).

`frontend/src/core/components/MatriceOverride.vue` — **il telaio, non la lista
dei permessi**: non sa cosa sia un'area né un livello.

**Props**

| Prop | Cosa |
| --- | --- |
| `voci` | tutte le righe del catalogo (già caricate — la popolazione è limitata per modello) |
| `overrides` | le righe scritte, indicizzate per chiave |
| `chiave` | funzione `voce → chiave` (`area_id`, `azione_id`, `app_label.model_name`) |
| `readonly` | eredita da `useInjectReadonly` se non passata |

**Slot scoped**: `#ereditato="{ voce }"` (cosa dà il profilo) e
`#override="{ voce, valore, set }"` (il controllo — `Select` di livello o
`ToggleSwitch` per le azioni). ⭐ **Il BB non conosce i livelli**: se li
conoscesse sarebbe il pannello permessi travestito da componente, e il terzo uso
non lo potrebbe riusare.

**Emette** `set(chiave, valore)` e `reset(chiave)` — due verbi distinti, ed è il
punto (§3.2).

⚠️ **Non è una `DataTable` nuda** (indicazione di Tid): CSS `app-*` da
`theme.css`, icone da `MANAGE_ICONS`, `readonly` iniettato, testi da i18n. Il
`paginata: false` non c'entra — qui non si pagina affatto.

📌 Da aggiungere al
[catalogo BB frontend](../frontend/catalogo-building-block-frontend.md),
sezione *Componenti Condivisi → Supporto*.

---

## 3. Il pannello — `OperatorePermessiTab.vue`

### 3.1 Cosa entra e cosa esce

| Esce | Entra |
| --- | --- |
| `addAreaOverride` / `addAzioneOverride` / `addOggettoOverride` | niente: le righe ci sono già tutte |
| `removeXOverride(index)` | `reset(chiave)` — torna all'ereditato |
| la `Select` che sceglie **quale** entità | la colonna «voce», che è dato, non input |

Le tre liste restano tre — aree, azioni, oggetti — perché è la forma che il
drawer regge; il raggruppamento per area di §4.1 dell'analisi resta un'ipotesi
per il giorno in cui questa UI andasse a pagina intera.

### 3.2 ⛔ Il salvataggio manda SOLO le righe con override vero

Il `PUT` **sostituisce l'intera collezione** (`DELETE WHERE auth_user_id` +
reinsert). Quindi:

- una riga senza override **non entra nel payload**;
- «torna all'ereditato» = **togliere** la riga dal payload, non scrivere un
  livello uguale.

🔴 **E un `BLOCCATO` scritto non è «nessun override»**: è un livello esplicito
che **batte il profilo**. Mandare tutte e 59 le righe materializzerebbe 59
override reali e cambierebbe il comportamento di ogni utente con un profilo —
cioè farebbe, per sbaglio, esattamente il cambio di funzionalità che questo
piano esclude.

### 3.3 Lo stato di riga, a video

| Stato | Quando | Come si vede |
| --- | --- | --- |
| **ereditato** | nessuna riga scritta | livello in grigio + «da profilo *Back-office*» (o «default») |
| **override** | riga scritta | livello a colore + `Tag` «Override» + azione «torna al profilo» |
| **override che ripete l'ereditato** | riga scritta = ereditato | ⚠️ `Tag` di avviso: non serve, e **congela** la riga se il profilo cambia |

L'ultima riga della tabella è il guadagno vero di §7.7 dell'analisi, e si ottiene
confrontando due valori che a quel punto sono entrambi in pagina.

### 3.4 Dove si tocca

`OperatorePermessiTab.vue` · `stores/operatori.js` (una action
`fetchPermessiEreditati`) · `api/amministrazione.js` · `locales/it.json` +
`en.json`. La sezione **emittenti scope** del tab non si tocca.

---

## 4. Test

### 4.1 Backend, sull'endpoint nuovo

- utente **senza profili** → `aree: []`, `azioni: []` (e il FE mostra «default»,
  che è la lettura giusta di una lista vuota);
- utente con profilo `REPARTO` → le sue aree e azioni, col nome del profilo;
- ⛔ utente con **due** binding a priorità diversa → vince quello a priorità **1**
  (`AD_HOC`). È il caso per cui l'endpoint esiste, e oggi non esiste in
  database: va **costruito** nella fixture, o il test conferma solo il caso
  facile.

### 4.2 ⭐ Il test che tiene insieme le due letture

Su un utente **senza nessun override**, per ogni area:

```
permessi-ereditati.livello  ==  fn_resolve_livello_area(user, schema_db)
```

Senza override la catena del resolver **è** l'ereditato, quindi i due numeri
devono coincidere per costruzione. È il presidio del `DISTINCT ON` di §1.3: il
giorno che le due letture divergono, questo test è l'unico posto in cui si vede.

### 4.3 Frontend

Non esiste una suite FE in questo repo: la verifica è **a video**, e va scritta
come copione — vedi §6.

---

## 5. Ordine dei passi

1. **BE**: repository → service → view → rotta → doc API. Da solo non cambia
   niente a video, quindi si può fare e pushare senza aspettare il FE.
2. **BB**: `MatriceOverride.vue` + voce nel catalogo.
3. **FE**: conversione del tab, una lista per volta — **aree per prima**: è la
   più corta (13 righe) e la sola con un ereditato di profilo *e* un fallback,
   quindi valida il pattern prima di ripeterlo.
4. **Azioni** (34 righe, con la ricerca locale) e **oggetti** (12 righe, con
   l'ereditato che viene dall'area).
5. **Copione di collaudo** (§6).

⚠️ Il passo 3 non può precedere l'1: senza l'ereditato la colonna resterebbe
vuota e il pannello direbbe meno di quello di oggi.

---

## 6. Il collaudo, in breve

Da scrivere come copione a parte quando il codice c'è. Le prove che contano:

- [ ] un operatore **senza niente** mostra 59 righe tutte in stato «default» —
      oggi mostra tre tabelle vuote;
- [ ] un operatore **con profilo di reparto** mostra i livelli del profilo, col
      nome del profilo, e **nessun** override;
- [ ] impostare un override e salvare scrive **una** riga in
      `config.user_override_*`, non 59. ⛔ Da verificare con un `count(*)` sul
      database, non a video: è il difetto di §3.2, e a video non si vede;
- [ ] «torna al profilo» **cancella** la riga, e il livello torna all'ereditato;
- [ ] un override uguale all'ereditato accende l'avviso di §3.3;
- [ ] in `readonly` nessun controllo è premibile.

---

## 7. Cosa questo piano NON fa

- ⛔ **il tetto d'area** (§3 dell'analisi): un'area bloccata continua a **non**
  bloccare le sue azioni di processo, e un override oggetto continua a poter
  essere più permissivo della sua area. È un difetto di modello, aperto e
  segnalato, e va deciso a parte;
- ⛔ **la provenienza completa** (`OVERRIDE_UTENTE | PROFILO | DEFAULT`
  restituita dai resolver, §5 dell'analisi): qui la si ricostruisce nel
  frontend confrontando due liste, il che basta a questa schermata e non
  cambia niente nel resto del sistema;
- ⛔ **il raggruppamento per area** e la vista a pagina intera (§4.1 e §4.5
  dell'analisi): restano le strade se un giorno il drawer non basterà più.
