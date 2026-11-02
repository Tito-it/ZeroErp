-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- Zero ERP — estrazione diagnostica (NON e' un changeSet)
--
-- Tira fuori i corpi dei template documento per poterli LEGGERE.
-- Serve perche' `html_template` vive nel database e non nel repo: senza
-- questo, l'unico modo di verificare un template e' aprirlo a mano.
--
-- USO:
--   set -a; . db/internal.env; set +a
--   psql -X -q -f scripts/sql/dump_template_documenti_pubblicati.sql \
--        -o /tmp/template-dump.txt
--
-- Brief: docs/it/dev/work-in-progress/brief-db-template-preventivo-indirizzi.md
-- ------------------------------------------------------------

\pset pager off
\pset format unaligned
\pset tuples_only on

-- ── 1) Inventario: quante versioni per template, e in che stato ──────
SELECT E'\n===== INVENTARIO =====';

SELECT format('%s | template_id=%s | versione=%s | stato=%s | id_versione=%s | area_indirizzi=%s | context_schema_chiavi=%s',
              rpad(coalesce(t.codice_interno, t.codice, '?'), 22),
              t.id, v.versione, rpad(v.stato, 12), v.id,
              CASE WHEN v.html_template ILIKE '%indirizz%' THEN 'SI' ELSE 'no' END,
              coalesce((SELECT string_agg(k, ',' ORDER BY k)
                          FROM jsonb_object_keys(coalesce(v.context_schema, '{}'::jsonb)) k), '-'))
  FROM documenti.template_documenti_versioni v
  JOIN documenti.template_documenti t ON t.id = v.template_documento_id
 ORDER BY t.id, v.versione;

-- ── 2) I corpi delle versioni PUBBLICATE ────────────────────────────
--    Un marcatore per ciascuno, cosi' il file si taglia senza ambiguita'.
SELECT E'\n\n===== CORPI (solo PUBBLICATA) =====';

SELECT E'\n\n-- ######## TEMPLATE: ' || coalesce(t.codice_interno, t.codice, '?')
       || ' | versione ' || v.versione || ' | id_versione ' || v.id || ' ########\n'
       || coalesce(v.html_template, '(html_template NULL)')
  FROM documenti.template_documenti_versioni v
  JOIN documenti.template_documenti t ON t.id = v.template_documento_id
 WHERE v.stato = 'PUBBLICATA'
 ORDER BY t.id;
