SELECT
  c.{{calories_subject_col}}::text AS id,
  {{calories_ts_expr}} AS ts,
  (
    c.{{calories_col}}::double precision
    / (
      COALESCE(lw.weight_kg, {{default_weight_kg}})
      * (0.25 * ({{calories_interval_minutes}}::double precision / {{reference_interval_minutes}}::double precision))
    )
  ) AS mets,
  COALESCE(lw.weight_kg, {{default_weight_kg}}) AS weight_kg,
  (lw.weight_kg IS NULL) AS weight_is_default
FROM {{calories_rel}} c
LEFT JOIN LATERAL (
  SELECT w.{{weight_col}}::double precision AS weight_kg
  FROM {{weight_rel}} w
  WHERE w.{{weight_subject_col}}::text = c.{{calories_subject_col}}::text
    AND w.{{weight_col}} IS NOT NULL
    AND (
      {{weight_ts_expr}} IS NULL
      OR {{calories_ts_expr}} IS NULL
      OR {{weight_ts_expr}} <= {{calories_ts_expr}}
    )
  ORDER BY {{weight_ts_expr}} DESC NULLS LAST
  LIMIT 1
) lw ON true
WHERE c.{{calories_col}} IS NOT NULL
