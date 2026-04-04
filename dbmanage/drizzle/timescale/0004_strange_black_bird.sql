CREATE TABLE "api_failure_predictions" (
	"time" timestamp with time zone NOT NULL,
	"org_id" uuid NOT NULL,
	"api_id" uuid NOT NULL,
	"endpoint" text NOT NULL,
	"method" text DEFAULT 'GET' NOT NULL,
	"risk_score" double precision NOT NULL,
	"prediction" text NOT NULL,
	"confidence" double precision NOT NULL,
	"top_features" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"feature_values" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"model_version" text DEFAULT '1.0' NOT NULL,
	"feature_schema_version" text DEFAULT '2.0' NOT NULL,
	"model_hash" text DEFAULT '',
	"is_warmed_up" boolean DEFAULT false
);
--> statement-breakpoint
ALTER TABLE "api_telemetry" ADD COLUMN "schema_hash" text;--> statement-breakpoint
ALTER TABLE "api_telemetry" ADD COLUMN "schema_version" text;--> statement-breakpoint
CREATE UNIQUE INDEX "idx_api_failure_predictions_idempotent" ON "api_failure_predictions" USING btree ("org_id","api_id","endpoint","method","time");--> statement-breakpoint
CREATE INDEX "idx_api_failure_predictions_lookup" ON "api_failure_predictions" USING btree ("org_id","api_id","endpoint","time");--> statement-breakpoint
CREATE INDEX "ix_api_telemetry_org_time" ON "api_telemetry" USING btree ("org_id","time");