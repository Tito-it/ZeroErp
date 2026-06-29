# ZeroERP — Analisi Gestione Operativa Attivita

> Anello esterno al nucleo pratiche
> Documento di analisi — non implementativo
> 05-03-2026 (rev. stato 2026-06-29)

---

> ## ⚠️ Stato (rev. 2026-06-29)
>
> Documento **valido come visione, praticamente non realizzato**. Verifica
> effettuata contro il codice attuale:
>
> 1. **La coda lavoro NON sostituisce l'agenda — è complementare.** Ciò che è
>    stato costruito (commit `acec053c2`, pannello "Le mie attività" +
>    `fn_coda_lavoro_operatore`, vedi
>    [brief-design-coda-lavoro-mie-attivita.md](../work-done/brief-design-coda-lavoro-mie-attivita.md))
>    è una **coda *pull-based* per assegnazione** (livelli
>    ASSEGNATO/REPARTO/LIBERO/COMPETENZA), **svincolata dalle date**: la
>    scadenza è solo un attributo mostrato, non l'asse organizzativo.
>    L'**agenda** di questo documento è invece la **vista temporale** (fasce
>    per scadenza, avvisi, posticipazioni) ed è **più ampia**: copre flussi di
>    pratica **+ appuntamenti + altre attività** non-pratica. Le due cose
>    coesistono, nessuna rimpiazza l'altra.
>
> 2. **Tutto il resto è da fare.** Non esiste codice per: agenda a fasce
>    temporali (operatore/responsabile/direzione), sistema avvisi,
>    posticipazione, sospensione del *singolo* flusso (esistono solo le
>    sospensioni di *pratica*), piano ferie/assenze + riallocazione + carico.
>    Nessuna entità `appuntamento`/`calendario` esiste nel codice.
>
> 3. **Punto di modello mancante.** §7.1 assume "agenda legge solo dal nucleo
>    pratiche", ma un **appuntamento non è un flusso**: l'agenda completa
>    richiede una **sorgente di attività non-pratica** (candidata: pattern C
>    `ext_appuntamento` di
>    [analisi-pratiche-domini-anello3.md §2.3-2.4](analisi-pratiche-domini-anello3.md))
>    e un'astrazione "voce d'agenda" che unifichi *flusso con scadenza* +
>    *appuntamento* + *altra attività* su un asse-data comune. Da progettare.
>
> 4. **Query §8 con nomi colonna stale** — corretti in questa revisione:
>    `flusso.operatore_id` → `f.risorsa_umana_id`,
>    `flusso.unita_org_id` → `f.unita_organizzativa_id`,
>    `data_prevista_fine` → `f.data_scadenza` (DATE).
>    Tracker autorevole prossimi passi pratiche:
>    [gestione-pratiche-come-procedere.md](gestione-pratiche-come-procedere.md).

---

## 1. Obiettivo

Fornire a ogni operatore, responsabile di reparto e direzione una visione chiara e aggiornata delle attivita in corso, in scadenza e in ritardo. Il sistema si appoggia interamente sul nucleo pratiche (13 tabelle) senza modificarlo: legge flussi, date, stati e operatori per costruire la vista operativa.

Tutto cio che serve esiste gia nel nucleo:
- `flusso.operatore_id` — chi deve fare
- `flusso.unita_org_id` — quale reparto
- `flusso.data_prevista_inizio / data_prevista_fine` — quando
- `flusso.stato` — a che punto siamo
- `pratica.priorita` — quanto e urgente
- `sospensione` — periodi di fermo
- `formula_tempo` — soglie warning/critico

---

## 2. Agenda Attivita

### 2.1 Concetto

Ogni operatore al login vede la propria agenda: un quadro delle attivita organizzate per urgenza temporale. Non e un calendario classico — e una vista operativa orientata all'azione.

### 2.2 Fasce temporali

Le attivita vengono raggruppate in quattro fasce basate sulla distanza dalla scadenza (`data_prevista_fine`):

| Fascia              | Colore    | Significato                                                         |
| ------------------- | --------- | ------------------------------------------------------------------- |
| **Scadenza oggi**   | Rosso     | Flussi con `data_prevista_fine = oggi`. Azione immediata richiesta  |
| **Entro 5 giorni**  | Arancione | Flussi in scadenza nei prossimi 5 giorni. Pianificazione urgente    |
| **Entro 10 giorni** | Giallo    | Flussi in scadenza nei prossimi 10 giorni. Pianificazione ordinaria |
| **Oltre 10 giorni** | Verde     | Flussi con scadenza oltre 10 giorni. Visibilita per pianificazione  |

I flussi **scaduti** (data_prevista_fine < oggi, stato non COMPLETATO) vengono evidenziati separatamente in testa all'agenda con segnalazione critica.

### 2.3 Livelli di vista

L'agenda si presenta a tre livelli con contenuti diversi:

**Operatore**: vede solo i propri flussi assegnati (filtro su `flusso.operatore_id`). Per ogni flusso vede la pratica di appartenenza, il tipo prestazione, la priorita, la scadenza e lo stato.

**Responsabile reparto**: vede tutti i flussi del proprio reparto (filtro su `flusso.unita_org_id`). Raggruppati per operatore. Vede anche i flussi non assegnati a nessun operatore specifico. Ha visibilita sulle assenze e puo riallocare.

**Direzione**: vista aggregata per reparto. Numeri totali per fascia temporale, percentuale di flussi in ritardo, KPI da formula_tempo. Non il dettaglio del singolo flusso ma l'andamento complessivo.

### 2.4 Informazioni per ogni attivita in agenda

Per ogni flusso nell'agenda:
- Numero e oggetto pratica
- Tipo prestazione
- Descrizione flusso
- Priorita pratica (BASSA / NORMALE / ALTA / URGENTE)
- Data prevista fine (la scadenza)
- Giorni rimanenti o giorni di ritardo
- Stato flusso (DA_ESEGUIRE / IN_CORSO / SOSPESO)
- Semaforo tempo da formula_tempo (se configurato per quel tipo prestazione)
- Eventuale nota di sospensione attiva
- Soggetto della pratica (cliente/fornitore)

---

## 3. Sistema di Avvisi

### 3.1 Avvisi al login

Quando l'operatore si connette, il sistema verifica le attivita in scadenza e presenta un riepilogo immediato. Non e un popup invasivo — e una sezione evidenziata nella dashboard che mostra:

- Numero di attivita scadute (non completate oltre la data prevista)
- Numero di attivita in scadenza oggi
- Numero di attivita in scadenza entro 5 giorni
- Eventuali attivita riallocate da colleghi assenti

### 3.2 Avvisi periodici in sessione

Durante la sessione di lavoro, a intervalli configurabili (proposta: ogni 30 minuti), il sistema verifica se ci sono cambiamenti:

- Nuovi flussi assegnati all'operatore (generati da azioni automatiche o assegnati dal responsabile)
- Flussi che sono passati da una fascia all'altra (es. da "entro 5 giorni" a "scadenza oggi")
- Flussi riallocati per assenza di colleghi
- Pratiche sospese che sono state riattivate

L'intervallo di verifica dovrebbe essere configurabile per non appesantire il sistema ne disturbare l'operatore.

### 3.3 Destinatari degli avvisi

| Evento                                      | Operatore               | Responsabile reparto          |
| ------------------------------------------- | ----------------------- | ----------------------------- |
| Flusso in scadenza oggi                     | Si                      | Si (aggregato per reparto)    |
| Flusso scaduto                              | Si                      | Si (con evidenza critica)     |
| Nuovo flusso assegnato                      | Si                      | No (a meno che non assegnato) |
| Riallocazione per assenza                   | Si (nuovo assegnatario) | Si (per approvazione)         |
| Flusso con semaforo critico (formula_tempo) | Si                      | Si                            |
| Sospensione in scadenza                     | Si                      | Si                            |

### 3.4 Fallback per responsabile assente

Se il responsabile reparto e assente (vedi sezione assenze), gli avvisi di livello responsabile vengono inoltrati al suo fallback designato. La catena di fallback e:

1. Responsabile reparto (destinatario primario)
2. Vice-responsabile o delegato (se configurato)
3. Responsabile del reparto padre nell'organigramma (se esiste gerarchia)
4. Direzione (ultimo livello)

La catena si interrompe al primo destinatario disponibile (non in assenza).

---

## 4. Gestione Posticipazione Attivita

### 4.1 Concetto

Un operatore puo posticipare un flusso assegnato, spostando la data prevista di fine. La posticipazione non e una modifica silenziosa — viene tracciata nel giornale di bordo con motivazione obbligatoria.

### 4.2 Regole

- La posticipazione aggiorna `flusso.data_prevista_fine`
- E obbligatoria una nota di motivazione (registrata come nota_flusso di tipo INTERNA)
- Il giornale registra l'azione con i valori vecchio/nuovo della data
- Il responsabile reparto riceve notifica della posticipazione
- Si possono definire limiti configurabili:
  - Numero massimo di posticipazioni per flusso
  - Giorni massimi di posticipazione totale
  - Posticipazioni oltre soglia richiedono approvazione del responsabile

### 4.3 Dati da tracciare per ogni posticipazione

- Data precedente
- Nuova data
- Motivazione (testo obbligatorio)
- Operatore che posticipa
- Timestamp
- Se richiesta approvazione: stato approvazione e chi ha approvato

---

## 5. Gestione Sospensione Temporanea Attivita

### 5.1 Concetto

Diversa dalla sospensione pratica (che ferma tutta la pratica), qui si parla di sospensione di un singolo flusso con data di riattivazione prevista. Il flusso resta in stato SOSPESO fino alla data indicata, poi torna visibile nell'agenda.

### 5.2 Regole

- Il flusso passa a stato SOSPESO
- E obbligatoria una nota con lo scopo della sospensione
- E obbligatoria una data di riattivazione prevista
- Alla data di riattivazione il flusso torna DA_ESEGUIRE e riappare nell'agenda
- La riattivazione puo essere automatica (job schedulato) o manuale
- Il giornale traccia sia la sospensione che la riattivazione
- Il responsabile viene avvisato delle sospensioni nel proprio reparto

### 5.3 Interazione con le sospensioni pratica

Se la pratica intera viene sospesa (tabella `sospensione`), tutti i flussi attivi di quella pratica passano automaticamente a SOSPESO. Non serve sospenderli uno a uno. Alla riattivazione della pratica, i flussi tornano allo stato precedente.

La sospensione singola del flusso invece e indipendente: puoi sospendere un flusso specifico mentre la pratica resta attiva.

---

## 6. Piano Ferie/Assenze e Riallocazione

### 6.1 Concetto

Se il sistema conosce il piano ferie e assenze degli operatori, puo automaticamente segnalare (e proporre la riallocazione de) le attivita assegnate a operatori che saranno assenti.

### 6.2 Tabella proposta: assenze operatore

Non fa parte del nucleo pratiche — e una tabella di dominio risorse umane o organizzazione. Campi essenziali:

- Operatore
- Data inizio assenza
- Data fine assenza
- Tipo assenza (FERIE, MALATTIA, PERMESSO, FORMAZIONE, ALTRO)
- Sostituto designato (opzionale — l'operatore che copre)
- Approvata (flag — solo le assenze approvate attivano la riallocazione)

### 6.3 Logica di riallocazione

La riallocazione non e automatica — e una **proposta** che il responsabile approva.

Il processo:

1. Il sistema incrocia le assenze approvate con i flussi assegnati
2. Per ogni flusso con scadenza durante il periodo di assenza dell'operatore assegnatario, genera una **proposta di riallocazione**
3. Le proposte vengono presentate al responsabile reparto con:
   - Flusso interessato e sua scadenza
   - Operatore assente e periodo assenza
   - Sostituto designato (se configurato nel piano assenze)
   - Altri operatori del reparto disponibili con il loro carico di lavoro attuale
4. Il responsabile approva, modifica o rifiuta la riallocazione
5. Se approvata, il flusso viene riassegnato (`flusso.operatore_id` aggiornato)
6. Il giornale traccia la riallocazione con motivazione "assenza operatore"
7. Il nuovo assegnatario riceve notifica
8. Il vecchio assegnatario al rientro vede nel giornale cosa e stato riallocato

### 6.4 Avvisi al responsabile

Il responsabile riceve avviso quando:
- Un operatore ha ferie approvate con attivita in scadenza nel periodo (proposta riallocazione)
- Un'assenza improvvisa (es. malattia) viene inserita e ci sono attivita in corso
- La riallocazione proposta non e stata ancora gestita entro N giorni dall'inizio assenza

### 6.5 Carico di lavoro

Per proporre riallocazioni intelligenti, il sistema calcola il carico di lavoro per operatore:
- Numero di flussi attivi assegnati (DA_ESEGUIRE + IN_CORSO)
- Numero di flussi in scadenza entro 5 giorni
- Numero di flussi scaduti

Questo permette al responsabile di riallocare verso l'operatore meno carico, non semplicemente verso il sostituto designato che potrebbe essere gia sovraccarico.

---

## 7. Interazione con i componenti esistenti

### 7.1 Cosa si legge dal nucleo pratiche (nessuna modifica)

| Tabella nucleo  | Dato utilizzato                                                             |
| --------------- | --------------------------------------------------------------------------- |
| `flusso`        | operatore_id, unita_org_id, stato, data_prevista_inizio, data_prevista_fine |
| `pratica`       | tipo_prestazione_id, priorita, stato, soggetto_id, oggetto                  |
| `sospensione`   | periodi sospensione per calcolo tempi netti                                 |
| `formula_tempo` | soglie warning/critico per semafori                                         |
| `giornale`      | registrazione posticipazioni, riallocazioni, sospensioni                    |
| `nota_flusso`   | motivazioni posticipazione e sospensione                                    |

### 7.2 Cosa potrebbe servire in piu (nuove tabelle, anello esterno)

| Tabella nuova            | Schema                    | Scopo                                                              |
| ------------------------ | ------------------------- | ------------------------------------------------------------------ |
| `assenze_operatore`      | risorse_umane             | Piano ferie/assenze con sostituto designato                        |
| `proposta_riallocazione` | pratiche o organizzazione | Proposte generate dal sistema, stato approvazione                  |
| `configurazione_avvisi`  | config                    | Intervalli notifica, soglie fasce temporali, limiti posticipazione |
| `avvisi_operatore`       | pratiche o core           | Coda avvisi per operatore con flag letto/non letto                 |

### 7.3 Cosa si appoggia alla linfa

| Componente linfa | Utilizzo                                                   |
| ---------------- | ---------------------------------------------------------- |
| `dbops` / `core` | Funzioni trasversali, permessi per livello di vista        |
| `config`         | Parametri configurabili (intervalli, soglie, limiti)       |
| Job pgAgent      | Job schedulato per riattivazione flussi sospesi a tempo    |
| Job pgAgent      | Job schedulato per generazione proposte riallocazione      |
| Job pgAgent      | Job schedulato per generazione avvisi scadenza giornalieri |

---

## 8. Query di riferimento

### 8.1 Agenda operatore per fascia

```sql
SELECT
    CASE
        WHEN f.data_scadenza < CURRENT_DATE THEN 'SCADUTO'
        WHEN f.data_scadenza = CURRENT_DATE THEN 'OGGI'
        WHEN f.data_scadenza <= CURRENT_DATE + 5 THEN 'ENTRO_5GG'
        WHEN f.data_scadenza <= CURRENT_DATE + 10 THEN 'ENTRO_10GG'
        ELSE 'OLTRE_10GG'
    END AS fascia,
    f.id AS flusso_id,
    p.numero AS pratica_numero,
    p.oggetto AS pratica_oggetto,
    tp.descrizione AS tipo_prestazione,
    f.descrizione AS flusso_descrizione,
    p.priorita,
    f.data_scadenza,
    (f.data_scadenza - CURRENT_DATE) AS giorni_rimanenti,
    f.stato
FROM pratiche.flusso f
JOIN pratiche.pratica p ON p.id = f.pratica_id
JOIN pratiche.tipo_prestazione tp ON tp.id = p.tipo_prestazione_id
WHERE f.risorsa_umana_id = :risorsa_umana_id
  AND f.stato IN ('DA_ESEGUIRE', 'IN_CORSO')
  AND p.stato IN ('APERTA', 'SOSPESA')
ORDER BY
    CASE
        WHEN f.data_scadenza < CURRENT_DATE THEN 0
        WHEN f.data_scadenza = CURRENT_DATE THEN 1
        WHEN f.data_scadenza <= CURRENT_DATE + 5 THEN 2
        WHEN f.data_scadenza <= CURRENT_DATE + 10 THEN 3
        ELSE 4
    END,
    p.priorita DESC,
    f.data_scadenza ASC;
```

### 8.2 Flussi a rischio per assenza operatore

```sql
SELECT
    f.id AS flusso_id,
    f.descrizione,
    f.data_scadenza,
    f.risorsa_umana_id,
    a.data_inizio AS assenza_da,
    a.data_fine AS assenza_a,
    a.tipo_assenza,
    a.sostituto_id
FROM pratiche.flusso f
JOIN risorse_umane.assenze_operatore a ON a.risorsa_umana_id = f.risorsa_umana_id
WHERE f.stato IN ('DA_ESEGUIRE', 'IN_CORSO')
  AND f.data_scadenza BETWEEN a.data_inizio AND a.data_fine
  AND a.approvata = TRUE
  AND f.unita_organizzativa_id = :reparto_id
ORDER BY f.data_scadenza;
```

### 8.3 Carico di lavoro per reparto

```sql
SELECT
    f.risorsa_umana_id,
    COUNT(*) FILTER (WHERE f.stato IN ('DA_ESEGUIRE','IN_CORSO')) AS flussi_attivi,
    COUNT(*) FILTER (WHERE f.data_scadenza < CURRENT_DATE
                     AND f.stato IN ('DA_ESEGUIRE','IN_CORSO')) AS flussi_scaduti,
    COUNT(*) FILTER (WHERE f.data_scadenza BETWEEN CURRENT_DATE
                     AND CURRENT_DATE + 5
                     AND f.stato IN ('DA_ESEGUIRE','IN_CORSO')) AS in_scadenza_5gg
FROM pratiche.flusso f
JOIN pratiche.pratica p ON p.id = f.pratica_id
WHERE f.unita_organizzativa_id = :reparto_id
  AND p.stato IN ('APERTA')
GROUP BY f.risorsa_umana_id
ORDER BY flussi_scaduti DESC, flussi_attivi DESC;
```

---

## 9. Considerazioni

**Non tocca il nucleo.** Tutta questa analisi si basa su dati che il nucleo pratiche gia produce. L'agenda e una vista, gli avvisi sono query, le posticipazioni aggiornano campi esistenti, le sospensioni usano meccanismi gia previsti. Le uniche tabelle nuove sono nell'anello esterno (assenze, proposte riallocazione, configurazione avvisi).

**Priorita di implementazione suggerita:**
1. Agenda attivita per operatore (query sui flussi esistenti — immediata)
2. Avvisi al login (stessa query, presentata diversamente)
3. Posticipazione con nota (update data + insert nota_flusso + giornale)
4. Sospensione temporanea flusso (update stato + job riattivazione)
5. Vista responsabile reparto (stessa query con filtro reparto)
6. Piano assenze e riallocazione (richiede tabelle nuove e logica piu complessa)

**I job pgAgent della linfa sono gia pronti** per gestire le automazioni periodiche (riattivazione sospensioni, generazione avvisi, proposte riallocazione). Il pattern `fn_run_and_log` documentato nella guida tracciamento processi si applica direttamente.

---

> Questo documento e analisi. L'implementazione seguira lo sviluppo concentrico:
> prima il nucleo (gia fatto), poi questo anello, un passo alla volta.
>
> 🪵