## 📘 Documentazione Concettuale – Funzione `vendite.fn_riporta_attivita_da_emettere`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
> • [vendite.commesse_attivita_log](/dbzero/vendite/tabelle/commesse_attivita_log)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_libera_attivita_fatturabili](/dbzero/vendite/funzioni/fn_libera_attivita_fatturabili)  
> • [vendite.fn_cleanup_fatture_by_ids](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids)  

---

### 🎯 Scopo Principale
(latest review 26-08-2026)

Il verbo **«Riporta da emettere»**: rimette in coda di fatturazione un elenco di
attività **residue**. Le libera e riporta a `NON_EMESSA` le righe di commessa
che erano passate a `EMESSA` per causa loro.

Il lavoro ricompare in **«Da emettere»** e da lì segue il giro normale:
**nessun lotto viene rigenerato, nessuna fattura viene ricreata.**

> **La regola che governa questa pagina.**
> Il verbo **non inventa logica**: sono le stesse due scritture della pulizia
> delle fatture, e vivono nella primitiva condivisa
> [`fn_libera_attivita_fatturabili`](/dbzero/vendite/funzioni/fn_libera_attivita_fatturabili).
> Se un giorno il ripristino cambia, cambia in **un posto solo**.

---

### A cosa serve, e perché non c'era

Quando una fattura viene eliminata da un lotto, il lavoro che conteneva deve
tornare disponibile. Dal 26 agosto 2026 **succede da solo**. Ma ogni altra causa
che scolleghi un'attività dalla sua riga produrrebbe lo stesso stato — e per
quella non c'era uscita: il rimedio era una scrittura a mano sul database.

Questo verbo è **l'uscita**, e non ne apre altre: non annulla niente, non
scarta niente. Se il riporto era sbagliato si rifattura, e si è al punto di
prima.

---

### ⛔ Il perimetro NON è «ciò che la card mostra»

La casella **`Emesse non fatturate`** del cruscotto competenza contiene **due
popolazioni strutturalmente diverse**:

| Caso | Che cos'è | Il verbo lo tocca? |
| --- | --- | --- |
| attività emessa che aspetta il suo lotto | transito legittimo fra emissione e fatturazione | ⛔ **no** |
| attività rimasta senza la sua fattura | il residuo | ✅ sì |

Un verbo fondato sulla card **disferebbe emissioni corrette**. Le tre condizioni
che discriminano sono:

```text
fattura_riga_id IS NULL          -- non è in nessuna fattura
AND lock_in_fatturazione         -- è ancora lucchettata: nessun giro la riprende
AND stato_esecuzione = COMPLETED -- e il giro che la lucchettava ha finito
```

⭐ È la **terza** a separare l'orfana dal giro **vivo**: `PENDING`/`RUNNING`
vuol dire lotto in corso, e quello non si tocca.

⛔ **E il perimetro non usa `fatturato`, di proposito** — scelto prima, e
confermato dai fatti il **26 agosto 2026**, quando quella colonna è diventata
**generata** (`fattura_riga_id IS NOT NULL`). Da quel giorno un predicato fondato
su `fatturato IS TRUE AND fattura_riga_id IS NULL` è **sempre falso**: il verbo
avrebbe smesso di funzionare **in silenzio**, che è esattamente la famiglia di
difetto da cui nasce.
⭐ Le tre condizioni vere invece **non sono toccate** dal cambio, e per lo stesso
motivo il banco di prova sulle attività orfane è sopravvissuto.

---

### ⛔ Il perimetro di *scope* sta sulla commessa

`vendite.attivita_fatturabili` **non ha row level security**;
`vendite.commesse_attivita` ce l'ha. Per questo
[`fn_check_attivita_riportabile_da_emettere`](/dbzero/script/funzioni/fn_check_attivita_riportabile_da_emettere)
risolve l'attività **passando per la riga di commessa**: quel `JOIN` *è* il
cancello.

⚠️ Leggere la sola `attivita_fatturabili` sarebbe **fail-open**, e il danno non
sarebbe un permesso concesso a vuoto: la mutazione libererebbe l'attività
(tabella senza RLS) e **non** riporterebbe la riga di commessa a `NON_EMESSA`
(tabella con RLS, zero righe toccate). Cioè lo **stato spezzato** — un livello
torna in coda e l'altro no — per impedire il quale esiste la primitiva
condivisa.

---

### ⛔ Non imposta la GUC di manutenzione, ed è il presidio

`trgfn_attivita_fatturabili_guard_fatturato` rifiuta l'`UPDATE` quando
`fattura_riga_id` è valorizzato, salvo GUC
`zeroerp.maintenance_reset_lotto_draft`.

Su un'attività **orfana** quel puntatore è già `NULL`, quindi il guard **lascia
passare da sé** e nessuna GUC serve. Impostarla sarebbe l'unico modo di
trasformare questo verbo in un modo per **scollegare una fattura viva**.

⭐ Il guard di dominio e quello di riga dicono quindi la stessa cosa da due
livelli diversi, senza essersi messi d'accordo: se il primo si rompesse, il
trigger tiene comunque.

---

### I rifiuti, e perché ognuno ha il suo codice

| Situazione | Codice | Il rimedio |
| --- | --- | --- |
| l'elenco è vuoto | `E_ATTIVITA_RIPORTO_SELEZIONE_VUOTA` | è un chiamante rotto: l'insieme vuoto **non deve poter uscire come «zero righe riportate»** |
| l'identificativo non si risolve | `E_ATTIVITA_FATTURABILE_NON_TROVATA` | l'elenco a schermo è invecchiato, oppure la riga è di un emittente fuori perimetro |
| è ancora dentro una fattura | `E_ATTIVITA_ANCORA_IN_FATTURA` | si agisce sulla **fattura** (*Elimina dal lotto* o *Riporta in lavorazione*) |
| non è lucchettata | `E_ATTIVITA_GIA_DA_EMETTERE` | non c'è niente da fare: è già in coda |
| è dentro un giro vivo | `E_ATTIVITA_IN_LAVORAZIONE` | si aspetta che il lotto finisca |

⭐ **I motivi li compone `fn_check_*`, il verbo solleva il primo.** Le due metà
servono due interlocutori: l'interfaccia deve spiegare **prima** del click e
mostrarli tutti, la mutazione deve fermare **dopo** e le basta il primo. Un
pgTAP verifica che non si separino.

---

### La traccia

Evento **`RIGA_RIPORTATA_DA_EMETTERE`** su
[`vendite.commesse_attivita_log`](/dbzero/vendite/tabelle/commesse_attivita_log),
una riga per attività, con il **lotto di provenienza** e lo **stato di
esecuzione precedenti**.

⚠️ Vanno fotografati **prima** di liberare, perché la primitiva li azzera. È la
stessa disciplina che il difetto di agosto 2026 aveva violato un livello più in
giù: *si legge il legame finché è vivo*.

⭐ **Il verbo non chiede un motivo** — a differenza di
`fn_annulla_commessa_attivita`, qui non si distrugge niente. Ma il log è
**obbligatorio** lo stesso: serve il **fatto**, non la **ragione**, perché «il
lavoro è sparito da un lotto» non deve poter essere indistinguibile da un
difetto.

---

### ⚠️ Due cose che sembrano scelte e non lo sono

- **Vale anche sulle attività di `RETTIFICA`**, e non c'è whitelist su
  `tipo_movimento`. ⚠️ La stessa distinzione origine/natura ha morso il dominio
  il 20 agosto 2026 su `fn_annulla_commessa_attivita`, dove la risposta è stata
  **opposta**: lì il verbo **distrugge**, e lasciar passare una riga di nota di
  credito lasciava l'accredito senza documento. Qui il verbo non distrugge, e
  rimettere in coda una rettifica orfana rigenera la nota di credito al giro
  successivo.
- **È sincrono**: due scritture, una transazione, nessun job. *Rendi definitive*
  passa da `dbops.coda_lavori` e si porta dietro il problema della dedup;
  accodare questo per simmetria significherebbe **importare un problema che qui
  non esiste**.

---

### Input / Output

**Input**: `p_attivita_fatturabili_ids bigint[]` — una **lista**, con la singola
attività come caso della lista. Il frontend le mostra per commessa e ne recupera
più d'una insieme; una funzione «una alla volta» costringerebbe il backend a un
ciclo, e un ciclo non è atomico.

**Output**: due contatori separati, perché sono **due fatti diversi** e possono
divergere —

* `riportate` — attività tornate disponibili
* `riemesse_attivita` — righe di commessa tornate emittibili

**Permesso**: `riporta_da_emettere` (`config.azioni_processo` id 33,
`pericolosa = false`: l'azione è recuperativa). Il presidio vive sul backend,
come per gli altri verbi.

---

### Note operative

* **`SECURITY INVOKER`**: RLS e scope emittente restano applicati identici al
  chiamante.
* ⚠️ Il **lock** (`FOR UPDATE`, `ORDER BY id`) viene **prima** dei motivi: due
  riporti concorrenti scriverebbero altrimenti due eventi di registro per un solo
  riporto, e l'`ORDER BY` evita il deadlock fra selezioni che si intersecano in
  ordine opposto.
* 🔴 Le `reason_key` `vendite.attivita.azione_reason.*` vanno presenti nei
  locales: `check_i18n_keys.py` fallisce se ne manca una.
* Test: `db/pgtap/vendite/test-riporta-attivita-da-emettere-v1.sql` (15 test).
  ⭐ Il **13** verifica che la `fn_check_*` e la mutazione **non si separino**; il
  **14** che il verbo non si apra la strada da solo con la GUC.
* Cantiere: `brief-db-lavoro-che-non-torna-indietro.md`, lotto L5 / D-4.

---

{% include-markdown "signature-core.md" %}
