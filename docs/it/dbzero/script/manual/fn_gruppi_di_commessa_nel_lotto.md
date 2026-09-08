## 📘 Documentazione Concettuale – Funzione `script.fn_gruppi_di_commessa_nel_lotto`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> • [vendite.fatturazione_lotti_gruppi](/dbzero/vendite/tabelle/fatturazione_lotti_gruppi)
> • [vendite.fatturazione_lotti_log](/dbzero/vendite/tabelle/fatturazione_lotti_log)
>
**Approfondimento funzioni:**
>
• [vendite.fn_build_gruppo_fatturabile_key](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key)
> • [vendite.fn_segna_esito_gruppo_lotto](/dbzero/vendite/funzioni/fn_segna_esito_gruppo_lotto)
> • [vendite.fn_log_pipeline_fase](/dbzero/vendite/funzioni/fn_log_pipeline_fase)
> • [script.fn_gruppi_trascinati_da_uscita](/dbzero/script/funzioni/fn_gruppi_trascinati_da_uscita)

---

### 🎯 Scopo Principale
(latest review 2026-09-08)

Risponde a: **«questa commessa, dentro questo giro di fatturazione, quali
documenti alimenta?»**

Ritorna l'elenco **ordinato** delle chiavi di gruppo fatturabile — i
«documenti» — che la commessa alimenta e che il lotto sta effettivamente
lavorando. `[]` quando non ne alimenta nessuno.

---

### Perché la domanda esiste, e chi la fa

Quando un giro di fatturazione fallisce su una commessa, **chi se ne accorge ha
in mano la commessa, non il documento**: è il pull che si è rotto, e il
documento sarebbe stato il suo risultato.

Ma la segnalazione che ne nasce deve dire **di quale documento parla**
(`vendite.fatturazione_lotti_log.gruppo_key`), perché è quella dichiarazione che
permette all'operatore di togliere il documento rotto dal giro e far ripartire
il lotto. Senza, la segnalazione risulta *«del giro»* e blocca tutto.

⇒ Serve una conversione, e questa funzione è la sua **sede unica**.

---

### ⛔ La parte fragile non è la chiave: è da dove si legge

La chiave la costruisce già
[`vendite.fn_build_gruppo_fatturabile_key`](/dbzero/vendite/funzioni/fn_build_gruppo_fatturabile_key).
Ciò che si sbaglia — e che non fallisce — è **la tabella di partenza**:

| Si parte da… | Che cosa esce | Aggancia il perimetro? |
| --- | --- | --- |
| `vendite.commesse_attivita` | `PREVENTIVO:<uid>`, `ORDINE_VENDITA:<uid>`, `MAN:<commessa>` | ✅ sì |
| `vendite.attivita_fatturabili` | `COMMESSA:<hash del segment_key>` | ⛔ **no, e in silenzio** |

La seconda riga è un errore vero, misurato il 2026-09-08 scrivendo
[`script.vw_lotto_documento_righe`](/dbzero/script/views/vw_lotto_documento_righe):
**zero corrispondenze su quattro documenti noti**, e nessun messaggio. Una copia
di quella scelta, il giorno che si sposta, produce chiavi che non agganciano
niente senza che nulla diventi rosso.

⇒ È il motivo per cui il backend **non la riscrive in Python**: ciò che
copierebbe non è un calcolo, è una scelta fragile.

---

### ⚠️ È 1:N, e cambia la forma della consegna

Una commessa può alimentare **più** documenti: contiene il preventivo, il
contratto e gli oneri dello stesso cliente. Per questo si torna un **array** e
non uno scalare, ed è la stessa ragione per cui
[`vendite.fn_segna_esito_gruppo_lotto`](/dbzero/vendite/funzioni/fn_segna_esito_gruppo_lotto)
scrive **N** righe di esito e non una.

⇒ Un fallimento di pull produce **una segnalazione per documento**.

⛔ **Scegliere «la prima chiave» è la scorciatoia che rompe**: se la commessa ne
alimenta tre e se ne dichiarasse una sola, le altre due resterebbero a bloccare
il lotto **per sempre**, e nessuno potrebbe toglierle — il verbo lavora sul
documento dichiarato, e quelle non lo sarebbero mai.

---

### ⭐ Il perimetro è parte della domanda

La domanda è «**nel lotto**», non «in generale»:

| Il lotto… | Che cosa torna |
| --- | --- |
| dichiara un perimetro (`fatturazione_lotti_gruppi`) | solo i documenti della commessa che stanno **dentro** quel perimetro |
| non lo dichiara (giri di massa) | **tutti** i documenti della commessa: li stava lavorando tutti |

Un documento fuori dal perimetro il lotto non lo stava lavorando: appendergli
una segnalazione la renderebbe una riga di
[`vendite.vw_segnalazioni_con_documento_ignoto`](/dbzero/vendite/views/vw_segnalazioni_con_documento_ignoto),
cioè un blocco che nessuno potrà mai togliere.

⚠️ Per questo `p_lotto_id` **non è un parametro di comodo**: toglierlo
cambierebbe la risposta, non la sua forma.

---

### ⭐ `[]` è una risposta, e va letta

Vuol dire *«questo fallimento non ha un proprietario dentro questo lotto»*.

⇒ Chi scrive la segnalazione ne mette **una sola**, con `gruppo_key` a `NULL`,
che significa *«è del giro»* e blocca. ⛔ **Non zero righe**: un fallimento che
non si scrive da nessuna parte è un giro che riparte su un guasto.

⭐ È lo stesso fatto che `fn_segna_esito_gruppo_lotto` già segnala dall'altro
lato con *«esito non appeso a niente»*: le due cose vanno lette insieme.

---

### Regole

* Funzione **pura**: non scrive niente. `STABLE`.
* **`SECURITY INVOKER`**: `vendite.commesse_attivita` ha la RLS, quindi chi
  legge vede le commesse dei propri emittenti — lo stesso perimetro della madre
  che la chiama.
* **Fail-loud sui parametri**: un id assente o `<= 0` solleva
  `E_PARAMETRO_INVALIDO`. La chiama anche il backend, e lì un id invalido è un
  **chiamante rotto**, non una condizione di dominio. ⛔ Un `[]` silenzioso
  sarebbe indistinguibile da *«nessun documento»*, che ha la conseguenza
  opposta.
* ⚠️ Chi **non deve poter sollevare** — come
  `vendite.fn_segna_esito_gruppo_lotto`, che gira dentro un gestore d'eccezione
  — tiene il proprio guard **prima** della chiamata.
* L'array è **ordinato** e senza duplicati.

---

### Esempio d'uso

```sql
-- Quali documenti alimenta questa commessa, in questo giro
SELECT script.fn_gruppi_di_commessa_nel_lotto(11221, 34137);
-- ["ORDINE_VENDITA:01a06ce4-35a6-721a-9cd8-9da48bf77626"]

-- Chi scrive la segnalazione: una riga per documento, oppure una «del giro»
SELECT vendite.fn_log_pipeline_fase(
           p_lotto_id   => 11221,
           p_stato_doc_fiscale_id => NULL,
           p_fase       => 'Pull commesse',
           p_status     => 'C',
           p_messaggio  => 'Errore emissione commessa 34137',
           p_meta       => '{}'::jsonb,
           p_error_code => 'E_PULL_COMMESSA',
           p_gruppo_key => g)
  FROM jsonb_array_elements_text(
           script.fn_gruppi_di_commessa_nel_lotto(11221, 34137)) AS g;
```

> Piano e decisioni: `docs/it/dev/work-in-progress/brief-db-uscita-documento-dal-giro.md` §6.1.

---

{% include-markdown "signature-core.md" %}
