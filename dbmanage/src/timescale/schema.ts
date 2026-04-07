import {
  boolean,
  doublePrecision,
  index,
  integer,
  jsonb,
  pgTable,
  text,
  timestamp,
  uniqueIndex,
  uuid,
} from "drizzle-orm/pg-core";

export const apiTelemetry = pgTable(
  "api_telemetry",
  {
    time: timestamp("time", { withTimezone: true }).notNull(),
    orgId: uuid("org_id").notNull(),
    apiId: uuid("api_id"),
    endpoint: text("endpoint").notNull(),
    method: text("method").notNull(),
    status: integer("status").notNull(),
    latencyMs: integer("latency_ms").notNull(),
    requestSize: integer("request_size"),
    responseSize: integer("response_size"),
    schemaHash: text("schema_hash"),
    schemaVersion: text("schema_version"),
  },
  (table) => ({
    timeIdx: index("ix_api_telemetry_time").on(table.time),
    orgIdx: index("ix_api_telemetry_org_id").on(table.orgId),
    orgTimeIdx: index("ix_api_telemetry_org_time").on(table.orgId, table.time),
    apiIdx: index("ix_api_telemetry_api_id").on(table.apiId),
  }),
);

export const apiFailurePredictions = pgTable(
  "api_failure_predictions",
  {
    time: timestamp("time", { withTimezone: true }).notNull(),
    orgId: uuid("org_id").notNull(),
    apiId: uuid("api_id").notNull(),
    endpoint: text("endpoint").notNull(),
    method: text("method").notNull().default("GET"),
    riskScore: doublePrecision("risk_score").notNull(),
    prediction: text("prediction").notNull(),
    confidence: doublePrecision("confidence").notNull(),
    topFeatures: jsonb("top_features").notNull().default([]),
    featureValues: jsonb("feature_values").notNull().default({}),
    modelVersion: text("model_version").notNull().default("1.0"),
    featureSchemaVersion: text("feature_schema_version")
      .notNull()
      .default("2.0"),
    modelHash: text("model_hash").default(""),
    isWarmedUp: boolean("is_warmed_up").default(false),
  },
  (table) => ({
    idempotentUq: uniqueIndex("idx_api_failure_predictions_idempotent").on(
      table.orgId,
      table.apiId,
      table.endpoint,
      table.method,
      table.time,
    ),
    lookupIdx: index("idx_api_failure_predictions_lookup").on(
      table.orgId,
      table.apiId,
      table.endpoint,
      table.time,
    ),
  }),
);
