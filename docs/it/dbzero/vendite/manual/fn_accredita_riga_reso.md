## 📘 Documentazione Concettuale – Funzione `vendite.fn_accredita_riga_reso(...)`

> 👀 **Vedi anche**
>
Tabelle:
>
[vendite.resi_righe_accrediti](/dbzero/vendite/tabelle/resi_righe_accrediti)
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)
> [config.nature_doc_fiscale](/dbzero/config/tabelle/nature_doc_fiscale)
>
Viste e funzioni:
>
[vw_resi_da_accreditare](vw_resi_da_accreditare.md)
> [vw_partite_merce](vw_partite_merce.md)
> [fn_upsert_commessa_attivita](fn_upsert_commessa_attivita.md)
> [fn_aggiungi_onere_commessa](fn_aggiungi_onere_commessa.md) — la porta gemella
> [trgfn_resi_accrediti_guard](trgfn_resi_accrediti_guard.md)
>
> Brief autorevole: `docs/it/dev/work-done/brief-design-note-credito-resi.md` (slice **N8**)

---

### 🎯 Scopo Principale

(rev 2026-09-21 — la coda si legge per documento · rev 2026-08-18)

**Il verbo che mancava.** La coda accrediti esisteva da luglio e non portava da
nessuna parte:

> *«Ho dei resi che ho deciso essere da accreditare, ma così come fatti rimangono
> bloccati, sembrano un ramo morto.»* (Tid, 2026-08-17)

Questa funzione trasforma una riga di quella coda in un **accredito**.

⭐ **E non apre una seconda pipeline.** Crea una riga di **rettifica** in
commessa, a quantità **negativa**, sul segmento della partita di merce. Da lì in
poi è la macchina di sempre — emissione → lotto → righe → numerazione — a
produrre il documento. Il contatore si chiude da sé, perché i «fatturati»
scendono senza che nessuno debba insegnarglielo.

---

### Un parametro solo, e sono due decisioni

```sql
vendite.fn_accredita_riga_reso(p_resi_riga_id)
```

* **L'accredito è sempre PIENO** (decisione D-NC-6). La quantità **non è un
  input**: è `vw_resi_da_accreditare.accredito_dovuto`. Sparisce l'intera classe
  di guard sull'input — non è validazione più severa, è **input che non esiste**.

  ⚠️ Il caso commerciale dietro l'accredito parziale è reale, ma è un
  **addebito**, e ha già la sua porta: le causali onere (`PENALE` fra le cinque
  a catalogo). Accredito pieno 50 € + onere 20 € con causale = stessa cifra
  netta, **due fatti con un nome ciascuno**. Un parziale lascerebbe invece un
  residuo che *nessuno può chiudere*: né una rinuncia (riguarda la ri-consegna,
  e non muove numeri) né un onere (viaggia su segmenti `MAN:` e non entra nel
  conto della merce). Sarebbe la riga che resta in coda a chiedere per sempre —
  cioè la malattia per cui questo cantiere esiste.

* **Il massivo lo fa il backend** (decisione D-NC-7). L'operatore può accreditare
  più righe selezionate fin da subito, ma il fan-out usa il building block
  `run_fan_out`, che isola ogni elemento in un savepoint. L'argomento è di
  merito, non di comodità: **il verbo non è l'atto fiscale** — crea una riga in
  commessa, il documento nasce dopo. Quindi un esito parziale non lascia mai
  mezzo documento, lascia una riga non lavorata che resta in coda e si riprova.
  Con il tutto-o-niente, su una coda condivisa, basterebbe *una* riga
  accreditata da un collega mezz'ora prima per bloccare le altre diciannove.

---

### Cosa fa, in ordine

```text
1. guard sul parametro
2. la riga dev'essere IN CODA          ← è la coda a dire quanto vale l'accredito
3. la partita è la SPEDIZIONE          ← D-NC-1, guard fail-fast
4. advisory lock a 2 argomenti sulla partita, DOPO le guard
5. progressivo del suffisso #RET:<n> da MAX+1, mai da count
6. consumo LIFO delle unità fatturanti (D-NC-5)
7. per ogni unità: una rettifica per riga di fattura + la riga di ponte + audit
8. l'UGUAGLIANZA di D-NC-6: se il consumo non copre tutto, non si fa a metà
```

---

### 🔴 D-NC-1 — la rettifica va sulla PARTITA, non sulla corsia

Il segmento è **sempre** quello della spedizione:

```text
DDT:<uid>:R:<riga>#RET:<n>              e per un kit, #RET:<n>#CMP:<componente>
```

…anche quando a fatturare è stata la **corsia ordine**. Non è un dettaglio di
forma:

```text
Ordine riga 100, fatturato sulla corsia ORD per 10.
  DDT₁ (1 marzo)  consegnato 6  →  fatturato_da_ordine 6
  DDT₂ (5 marzo)  consegnato 4  →  fatturato_da_ordine 4
Reso di 4 pezzi DA DDT₁ → accredito 4.

Se la rettifica abbassasse il SERBATOIO d'ordine a 6:
  DDT₁ → 6   (invariato: la greedy oldest-first lo serve per primo)
  DDT₂ → 0   ← l'accredito è finito sulla spedizione SBAGLIATA
```

⚠️ Il totale tornerebbe **giusto** e nessun test di parità se ne accorgerebbe: è
la **ripartizione** a essere falsa.

#### ⛔ Il ripiego chiesto è diventato un guard, non un `COALESCE`

Era stata chiesta una cintura — *«se il DDT non c'è, prendi il primo»*.
Verificato che la condizione è **impossibile per costruzione**, su tre livelli
indipendenti: `resi_righe.ddt_riga_id` è `NOT NULL`; la partita **è** la riga di
DDT; la coda accrediti è agganciata a `ddt_riga_id`. E c'è la ragione di merito:
*la merce non può tornare indietro se non è mai uscita*.

Un `COALESCE` sarebbe stato un **ramo morto**, cioè la cosa peggiore che si
possa scrivere qui: un ramo che nessun percorso attraversa sembra coperto e non
lo è, e il giorno in cui qualcosa dovesse raggiungerlo farebbe **in silenzio**
proprio ciò che D-NC-1 vieta. La cintura c'è (`E_ACCREDITO_SENZA_SPEDIZIONE`);
smette solo di essere silenziosa.

---

### N-1 — il prezzo si COPIA dalla fattura, mai si ricalcola

> *«Deve sempre reperire i prezzi dalla fattura, non deve fare nessuna operazione
> di ricalcolo prezzo: la nota di credito non può differire da quanto
> fatturato.»* (Tid, 2026-08-18)

La fonte è `attivita_fatturabili.fattura_riga_id` → `vendite.fatture_righe`.
Mai un ricalcolo, mai una rilettura del listino, mai una media.

⚠️ **Sconto e IVA non viaggiano da qui**: `commesse_attivita` non ha una colonna
sconto, e inventarne una per il bisogno di una sola riga toccherebbe la catena di
**tutte** le fatture. Li copia il **generatore righe** (backend), leggendo la
riga rettificata nel momento in cui scrive il documento — che è anche più fedele
alla richiesta: la copia avviene *guardando il documento che si rettifica*, non
sperando che tre tabelle abbiano trasportato i valori senza perderli.

⭐ Ne discende l'invariante che il §2 del brief cercava:

> **Ogni riga di nota di credito ha una riga di fattura gemella**: stesso
> articolo, stesso prezzo, stessa IVA, stesso sconto, quantità non superiore.

---

### D-NC-5 — LIFO, e perché non è una regola di calcolo

Le unità fatturanti della partita si consumano **dall'ultima fatturata a
scalare**. Non è un criterio di *valorizzazione* — il prezzo si copia sempre,
riga per riga — è un criterio di **consumo**: quale riga di fattura si tocca per
prima. *«In proporzione»* è stata scartata perché inventerebbe un prezzo medio
che in fattura non esiste.

#### Il kit: nessuna scelta da fare

Le unità si raggruppano per `kit_key` (il segmento privato del suffisso `#CMP:`)
e la quantità del gruppo si legge in **unità padre** — `max(quantita /
coeff_qta)`, non la somma — esattamente come fa `vw_af_merce_per_riga`. Consumata
un'unità padre nascono **N rettifiche**, una per componente, ciascuna di
`quota × coeff_qta` e ciascuna specchio della **sua** riga di fattura.

⭐ **Quanti kit rende, lo dice la rettifica stessa** (dal 2026-10-03,
`20261003-05`). Il meta della rettifica eredita quello della riga rettificata,
e quella riga porta `qta_padre`: la quantità della riga padre del documento,
che il push scrive su ogni componente. Ereditata, sarebbe positiva e intera, e
la nota di credito direbbe «+10 kit» per un reso di 3. Per questo la madre la
riscrive, sui soli componenti, a `- quota`: unità padre, con lo stesso segno
della quantità del componente. `uom_padre_id` resta quella ereditata, che è
giusta. Sulle righe che non sono di un kit la chiave non nasce.

⚠️ Non è un caso di scuola: la prima riga della coda accrediti *è* un articolo
composito con tre componenti a 1, 2 e 14 euro.

---

### ⭐ L'idempotenza non dipende da una finestra temporale

Fra il verbo e l'emissione la rettifica esiste come attività **NON_EMESSA**:
l'attività fatturabile non c'è ancora, il conto della merce non è cambiato — e
prima di questo cantiere la riga sarebbe rimasta **in coda**, con un secondo
click perfettamente coerente col conto.

Due presidi, e nessuno dei due è un flag da mantenere:

1. l'accredito è registrato **al momento del verbo** in
   `vendite.resi_righe_accrediti`, e la coda (`fn_resi_da_accreditare`, di cui
   `vw_resi_da_accreditare` è la proiezione) sottrae la quota già accreditata →
   **la riga esce dalla coda subito**;
2. la `UNIQUE (resi_riga_id, fattura_riga_rettificata_id)` del ponte ferma
   comunque il doppione esatto.

L'operatore lo scopre **quando clicca**, non a fine batch su un documento
fiscale.

---

### 🔄 rev 2026-09-21 — la coda si legge PER DOCUMENTO (D14, giro 2 — D3)

ChangeSet `20260921-30`. Al passo 2 la madre chiedeva la riga a
`vw_resi_da_accreditare`, cioè alla coda di **tutti** i resi — partite di
tutti, resi di tutti, una funzione per ogni riga confermata — per accreditarne
**una**. Ora legge prima il DDT della riga resa e chiama
[`fn_resi_da_accreditare(ARRAY[ddt], NULL)`](fn_resi_da_accreditare.md): la
coda di quel documento. Il numero è lo stesso (la vista è la proiezione della
funzione); contratto, guard, errori, lock e scritture non cambiano.

⚠️ Se la riga non c'è — o chi agisce non la vede, RLS — il DDT letto è `NULL`,
e `ARRAY[NULL]` semina **zero** righe: si cade nel `NOT FOUND` di prima
(`E_ACCREDITO_NON_IN_CODA` / `E_ACCREDITO_GIA_ESEGUITO`). Un array `NULL`,
invece, sarebbe «tutta la coda»: la differenza fra i due è la ragione della
variabile in più.

---

### ⛔ rev 2026-10-18 — in commessa si entra dalla base del segmento

ChangeSet `20261018-15`. La madre legge `vendite.commesse_attivita` tre volte:
il progressivo `#RET:`, i gruppi da accreditare e le righe di ciascun gruppo.
Tutte e tre filtravano la chiave con `LIKE` o `split_part`, che sotto la policy
della tabella **non arrivano all'indice** (non sono leakproof,
linee-guida-sql §8.5-bis): la tabella si leggeva intera, con la policy pagata
riga per riga, a ogni accredito.

Ora ciascuna entra dall'**uguaglianza su `segment_base`** e tiene il filtro di
prima come residuo. Le righe sono le stesse per costruzione: i segmenti della
partita (`DDT:<uid>:R:<riga>`, `ORD:<uid>:R:<riga>`) non contengono `#`, quindi
ogni chiave che il filtro accetta ha per base il segmento stesso.

⚠️ Una lettura nuova di `commesse_attivita` in questa funzione deve entrare
allo stesso modo: i risultati resterebbero giusti, e solo il tempo se ne
accorgerebbe. Presidio: `db/pgtap/vendite/test-fn-accredita-riga-reso-v1.sql`
test 16 (forma) e test 15 (la corsia ORD, costruita). Misura:
`brief-db-plancache-funzioni-con-query-incorporate` §5quater.

---

### 🔄 rev 2026-11-10 — il fattore si copia, senza «1 se manca»

La rettifica copia il fattore verso la base dall'attività che rettifica, com'è. Prima lo
scriveva con un «1 se manca»; l'1 non scattava, perché l'attività ha sempre il fattore, ma era la
forma che faceva passare 3 cartoni come 3 pezzi. Se il fattore mancasse, lo leggerebbe la
tabella alla data dell'attività
([`trgfn_attivita_fattore_alla_data`](/dbzero/vendite/funzioni/trgfn_attivita_fattore_alla_data)).
(brief-db-revisione-catalogo, giro 2-bis)

---

### I due tetti, e perché non stanno nello stesso posto

```text
Σ unità di merce per riga di reso      =  accredito dovuto   ← QUI, uguaglianza
Σ qta per riga di fattura              ≤  qta della riga     ← nel guard del ponte
```

⚠️ Il piano li metteva entrambi nel guard. **Non regge sul kit**: la merce si
misura in unità *padre*, il documento in unità di *riga di fattura*, e su un
articolo composito tre righe di ponte valgono **una** unità di merce. Un tetto
sommato riga per riga direbbe «3» dove la merce dice «1», e rifiuterebbe il
secondo componente di un accredito legittimo.

Il tetto della merce vive quindi qui, ed è un'**uguaglianza**: la madre è l'unica
a conoscere l'unità padre e a sapere **quando l'operazione è finita**. Un guard
che verifica un'uguaglianza è più forte di uno che verifica una disuguaglianza,
e costa lo stesso.

---

### Modello di riferimento e pedaggi già pagati

`vendite.fn_aggiungi_onere_commessa`, la **porta gemella**: `SECURITY INVOKER`
esplicito, `%TYPE` ovunque, guard sui parametri ID, `pg_advisory_xact_lock` a
**due argomenti** dopo le guard, progressivo del suffisso da `MAX+1`, guard
`is_new`, audit su `commesse_attivita_log`.

* **Advisory lock a due argomenti** (namespace + chiave): lo spazio dei lock a un
  argomento è condiviso con altre feature. La chiave è la **riga di DDT** e non
  la commessa, perché è sul *segmento* che gira il progressivo `#RET`, e un
  segmento può attraversare due commesse.
* **Progressivo dal MASSIMO, non dal `count`**: contare presuppone l'invariante
  «count = max», che nulla garantisce. I buchi nella numerazione sono ammessi e
  non significano nulla.
* **Guard `is_new`**: l'accredito è una **creazione**, mai un aggiornamento.
  Riusa `fn_upsert_commessa_attivita` solo per non duplicarne il mapping a 40
  parametri.

⚠️ **Il presidio permessi vive sul backend** (`post_permission` dedicato), non
qui: la madre deve restare usabile da un processo autorizzato. È il precedente di
`carica_voce_manuale` sulla porta oneri.

---

### Parametri

| Parametro | Tipo | Note |
|---|---|---|
| `p_resi_riga_id` | `vendite.resi_righe.id%TYPE` | la riga di reso da accreditare. Obbligatoria (>0), e **deve essere in coda** |

### 📦 Output

Una riga **per rettifica creata** — sempre almeno una, più d'una quando il
consumo LIFO tocca due righe di fattura o quando l'articolo è composito.

| Colonna | Descrizione |
|---|---|
| `accredito_id` | la riga di `vendite.resi_righe_accrediti` scritta |
| `commessa_attivita_id` | la rettifica creata in commessa |
| `fattura_riga_rettificata_id` | la riga di fattura da cui si è copiato il prezzo |
| `qta` | quantità nell'unità della riga di fattura |
| `qta_partita` | la stessa quota in unità di merce |

⚠️ Chi la modificherà: `CREATE OR REPLACE` **non cambia** una `RETURNS TABLE` —
serve `DROP` + `CREATE`, con numerazione successiva.

---

### Codici errore

| Codice | Quando |
|---|---|
| `E_PARAMETRO_INVALIDO` | `resi_riga_id` `NULL` o `<= 0` |
| `E_ACCREDITO_NON_IN_CODA` | la riga non compare in `vw_resi_da_accreditare`, o il suo accredito dovuto è sceso a zero |
| `E_ACCREDITO_GIA_ESEGUITO` | stesso cancello, messaggio più preciso: esistono già accrediti per questa riga di reso |
| `E_ACCREDITO_SENZA_SPEDIZIONE` | 🔴 guard di D-NC-1. **Non deve mai scattare**: se scatta è una regressione del modello |
| `E_ACCREDITO_ATTIVITA_NON_FATTURATA` | un'attività della partita non è mai finita in una riga di fattura: non c'è un prezzo da cui accreditare |
| `E_ACCREDITO_KIT_NON_MISURABILE` | articolo composito con componenti senza `coeff_qta`: la quantità in unità padre non è calcolabile |
| `E_ACCREDITO_QUOTA_NON_COPERTA` | le righe di fattura non bastano a coprire tutto l'accredito dovuto. Meglio non farlo che farlo a metà |
| `E_ACCREDITO_SEGMENT_DUPLICATO` | guard `is_new`: la scrittura ha aggiornato invece di creare. Non deve mai scattare |
| `E_CONFIG_MANCANTE` | la natura `NOTA_CREDITO` non è a catalogo |

---

### Esempio d'uso

```sql
-- Accredita una riga della coda. La quantità non si passa: la dice la coda.
SELECT * FROM vendite.fn_accredita_riga_reso(5797);

--  accredito_id | commessa_attivita_id | fattura_riga_rettificata_id | qta | qta_partita
--  ------------ | -------------------- | --------------------------- | --- | -----------
--             1 |                26751 |                        5031 |   5 |           5

-- Da qui in poi è il giro normale: al prossimo lotto la rettifica diventa
-- una riga di nota di credito, e la partita pareggia da sola.
```

---

### Importanza nel sistema

È il punto in cui *«questo reso va accreditato»* smette di essere una
constatazione in una lista e diventa un documento fiscale — passando dalla
macchina che già c'era, e lasciando dietro di sé chi, quando, quanto e **a
fronte di cosa**.

---

{% include-markdown "signature-core.md" %}
