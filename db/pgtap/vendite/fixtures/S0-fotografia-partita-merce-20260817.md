# S0 — Fotografia di riferimento del contatore merce (2026-08-17)

> **Perché esiste**: il §4.2 del brief
> [brief-design-partita-merce-generalizzata.md](../../../docs/it/dev/work-in-progress/brief-design-partita-merce-generalizzata.md)
> chiede la parità **su dati reali, non su fixture**. Dopo la slice S3 il «prima»
> non è più interrogabile: questa è la sua unica copia.
>
> **Come è stata scattata**: `psql` in sola lettura sul DB di **sviluppo**, come
> **owner** — di proposito. Come applicazione la RLS restituirebbe zeri
> fail-closed indistinguibili da un dato.
>
> ⚠️ **Non è un file di test**: è una misura. Nessun pgTAP lo esegue; è il
> riferimento che il test di parità di S3 deve riprodurre.

## 1. Il contatore, tutte le righe

```text
   ordine   |  orr  |  trigger   | ordinato  |  tenuti   | fatturati | differenza 
------------+-------+------------+-----------+-----------+-----------+------------
 ORD0000228 |   235 | CONFERMATO |  5.000000 |  3.000000 |         0 |   3.000000
 ORD0000228 |   236 | CONFERMATO |  5.000000 |  5.000000 |         0 |   5.000000
 ORD0000229 |   237 | CONFERMATO |  5.000000 |  5.000000 |         0 |   5.000000
 ORD0000230 |   238 | CONFERMATO |  5.000000 |  3.000000 |         0 |   3.000000
 ORD0000230 |   239 | CONFERMATO |  5.000000 |  5.000000 |         0 |   5.000000
 ORD0000231 |   240 | CONFERMATO |  5.000000 |  5.000000 |         0 |   5.000000
 ORD0000580 |   588 | CONFERMATO |  1.000000 |  1.000000 |  1.000000 |   0.000000
 ORD0000608 |   607 | CONFERMATO |  1.000000 |  1.000000 |  1.000000 |   0.000000
 ORD0000609 |   609 | CONFERMATO | 10.000000 |  5.000000 |         0 |   5.000000
 ORD0018247 | 18605 | CONFERMATO |  7.000000 |  7.000000 |         0 |   7.000000
 ORD0018586 | 18946 | SPEDITO    | 21.000000 | 13.000000 | 21.000000 |  -8.000000
 ORD0018587 | 18947 | SPEDITO    | 10.000000 |  4.000000 |         0 |   4.000000
(12 righe)

```

## 2. La coda accrediti (non deve cambiare)

```text
 resi_riga_id | reso_numero | ddt_numero |  orr  |  tenuti   | fatturati | accredito_dovuto |  etichetta  
--------------+-------------+------------+-------+-----------+-----------+------------------+-------------
         5797 | RESO0005122 | DDT0010839 | 18946 | 13.000000 | 21.000000 |         5.000000 | DOVUTA
         5799 | RESO0005123 | DDT0010839 | 18946 | 13.000000 | 21.000000 |         3.000000 | FACOLTATIVA
(2 righe)

```

## 3. La coda ri-consegne (non deve cambiare)

```text
 resi_riga_id | reso_numero | qta_resa | qta_riconsegnata | qta_residua | stato_riconsegna |  orr  
--------------+-------------+----------+------------------+-------------+------------------+-------
         5799 | RESO0005123 | 3.000000 |                0 |    3.000000 | DA_RICONSEGNARE  | 18946
(1 riga)

```

## 4. Il dosatore: quantita che oggi finirebbero in fattura

```text
 ddt_id | riga_id |                   segment_key                    | quantita |        qta_operativa         
--------+---------+--------------------------------------------------+----------+------------------------------
     61 |      53 | DDT:019f4e08-f60a-77ea-8a13-9f9c59ec1b3f:R:53    | 3.000000 | 3.00000000000000000000000000
  15855 |   17170 | DDT:01a00f5f-deac-764c-add9-90387e41e713:R:17170 | 4.000000 | 4.00000000000000000000000000
(2 righe)

```

---

## 5. Come si legge questa fotografia dopo S3

### 5.1 Le 10 righe che devono restare IDENTICHE

Tutte tranne **236** e **239**. Su queste dieci, `tenuti` / `fatturati` /
`differenza` devono uscire dalla vista riscritta con gli **stessi identici
valori**. È la parità del §4.2 del brief, ed è ciò che impedisce a questo
cantiere di cambiare importi di documenti fiscali.

### 5.2 Le 2 righe che DEVONO cambiare — decisione D1 (Tid, 2026-08-17)

| Riga | Oggi | Dopo S2/S3 | Perché |
| --- | --- | --- | --- |
| 236 | `tenuti 5` · `differenza 5` | `tenuti 2` · `differenza 2` | 3 pezzi resi e già impegnati su un DDT **in bozza** (righe 117+118): non sono in mano al cliente |
| 239 | `tenuti 5` · `differenza 5` | `tenuti 2` · `differenza 2` | idem (righe 122+123) |

Quei 3 pezzi non spariscono: si leggono nella colonna nuova **`in_riconsegna`**.
Il controllo a occhio è `tenuti + in_riconsegna = 5`, cioè quanto era uscito.

⚠️ **Se dopo S3 cambia una qualunque delle altre dieci, è una regressione** —
non una conseguenza di D1.

### 5.3 Le righe che devono COMPARIRE (oggi assenti)

I **kit order-backed**, oggi tagliati da `WHERE NOT is_composito`. Attesi con
`differenza` **0 o positiva, mai negativa** — se esce un negativo, la
normalizzazione in unità del padre (§9.5) non ha funzionato.

```text
ORD0000163 · orr 172 · consegnato 1 · fatturato (padre) 1 → 0
ORD0000227 · orr 241 · consegnato 1 · fatturato (padre) 1 → 0
ORD0000580 · orr 589 · consegnato 1 · fatturato (padre) 1 → 0
ORD0000608 · orr 608 · consegnato 1 · fatturato (padre) 1 → 0
ORD0000609 · orr 610 · consegnato 9 · fatturato 0         → +9
ORD0018504 · orr 18867 · consegnato 3 · fatturato 0       → +3
```

⚠️ `ORD0005174` / orr **5405** (17 ordinati, 51 fatturati in unità componente,
**0 spediti**) **non deve comparire fra le partite di merce**: non è uscito
niente. Il suo fatturato si legge come `fatturato_anticipato` — **17**, in unità
del padre. Se compare con `differenza −51` o `−34`, il rilievo A non è stato
chiuso.

### 5.4 Il dosatore (§4) — il collaudo di S5

Le **2 righe** che `fn_list_ddt_da_pushare()` restituisce oggi devono restare
due, con le stesse quantità (3 e 4), fino a S5 compresa. È l'unica misura che
tocca direttamente ciò che finisce in una riga di fattura.

⚠️ La riga `DDT:…:R:53` è **standalone** e oggi esce a `dr.quantita` **grezza**:
nessuno tiene il conto di quella merce. Dopo S5 passerà sotto il dosatore come
le altre — e allora quel 3 dovrà venire dalla sua partita, non dalla riga.
